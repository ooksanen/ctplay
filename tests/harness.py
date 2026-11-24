"""Emulation harness for slim builds: upstream's Unicorn setup (stock flash with the image + the device RAM snapshot),
driven through the real controller routes, with the outputs a comparison needs.

sleep() (0x0801BE78) is stubbed to return at once (the emulated clock never advances), and every `call()` and `leds()`
asserts that it reached its return address, so a handler can never be silently truncated by the instruction budget.
The SPI2 status register is modelled as always ready (TXE and RXNE set on every read), so the stock SPI transfer
routine at 0x08037960 runs to completion; no stock code is skipped.
A write-watch on the flash interface (0x40023C00-0x40023FFF, mapped) and option bytes / system memory
(0x1FFF0000-0x1FFFFFFF, unmapped: UC_HOOK_MEM_WRITE_UNMAPPED) records any write in `forbidden_writes` and stops
emulation; `outputs()` includes it."""
from __future__ import annotations

import gc
import struct

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_WRITE_UNMAPPED
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R4, UC_ARM_REG_SP

from emu_sc05 import STOP
from emu_sc08 import E8, MGR  # noqa: F401  (upstream tools/, on pytest's pythonpath)

BTN_PRESS, BTN_RELEASE = 0x08033320, 0x0803381A
PAD_PRESS, PAD_RELEASE = 0x08033282, 0x080332CE
KNOB = 0x08033848
MS_SERVICE = 0x080234EC      # Main's 1 ms soft timer: runs stock's 1 ms dispatcher 0x0803C410 (hook point main_ms)
LED_SITE = 0x0803415A        # `bl led_task` in the UI refresh (r0 = controller, r1 = output); slim retargets it
DSP_WRITE = 0x080292F8
HEAP_LIMIT, HEAP_CUR = 0x20002B44, 0x20002B48
OUT = 0x2006E000             # scratch for the 69 panel LEDs (mapped by the harness, unused by the snapshot)
SPI_BASE = 0x40003800        # SPI2 (found by probing r0 -> handle -> base at 0x08037960)
SPI_SR = SPI_BASE + 8
SPI_SR_READY = 0x3           # TXE (bit 1) | RXNE (bit 0): models the peripheral; nothing in stock is bypassed
N_LEDS = 69
BUDGET = 900_000


class Harness(E8):
    def __init__(self, image: bytes):
        gc.collect()
        super().__init__(image)
        self.dsp_writes: list[tuple[int, int, int]] = []
        self.forbidden_writes: list[tuple[int, int, int]] = []
        self.nbusy = 0
        uc = self.uc

        def dsp_write(u, a, s, d):
            self.dsp_writes.append(tuple(u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)))

        def drain(u, a, s, d):                       # mailbox wait 0x080359E0: drained by a task that does not run here
            u.mem_write(self.r32(u.reg_read(UC_ARM_REG_R4) + 0x10), bytes(4))

        def busy(u, a, s, d):                        # "busy" poll 0x08023172: acknowledged after three polls
            self.nbusy += 1
            if self.nbusy > 3:
                u.mem_write(u.reg_read(UC_ARM_REG_R0) + 0xC, b"\x01")

        def forbidden(u, access, addr, size, value, d):
            self.forbidden_writes.append((addr, size, value))
            u.emu_stop()

        def forbidden_unmapped(u, access, addr, size, value, d):
            forbidden(u, access, addr, size, value, d)
            return False

        def sleep(u, a, s, d):                       # 0x0801BE78 sleep(ms): the emulated clock never advances
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR) | 1)

        def spi_ready(u, access, addr, size, value, d):
            u.mem_write(SPI_SR, (self.r32(SPI_SR) | SPI_SR_READY).to_bytes(4, "little"))

        uc.hook_add(UC_HOOK_MEM_READ, spi_ready, begin=SPI_SR, end=SPI_SR + 3)
        uc.hook_add(UC_HOOK_CODE, sleep, begin=0x0801BE78, end=0x0801BE78)
        uc.hook_add(UC_HOOK_CODE, dsp_write, begin=DSP_WRITE, end=DSP_WRITE)
        uc.hook_add(UC_HOOK_CODE, drain, begin=0x080359E0, end=0x080359E0)
        uc.hook_add(UC_HOOK_CODE, busy, begin=0x08023178, end=0x08023178)
        uc.hook_add(UC_HOOK_MEM_WRITE, forbidden, begin=0x40023C00, end=0x40023FFF)
        uc.hook_add(UC_HOOK_MEM_WRITE_UNMAPPED, forbidden_unmapped, begin=0x1FFF0000, end=0x1FFFFFFF)

    def call(self, fn, *args, maxins=BUDGET):
        if len(args) > 4:                  # AAPCS: arguments 5+ on the stack, at the SP super().call sets
            self.uc.mem_write(0x2006F000, b"".join(struct.pack("<I", a) for a in args[4:]))
            args = args[:4]
        ev = super().call(fn, *args, maxins=maxins)
        pc = self.uc.reg_read(UC_ARM_REG_PC)
        if pc & ~1 != STOP & ~1:
            raise AssertionError(f"call {fn:#010x} did not return: pc={pc:#010x} (budget {maxins} or forbidden write)")
        return ev

    def press(self, button: int, shift: bool = False) -> None:
        self.nbusy = 0
        if shift:
            self.set_p0(self.r32(MGR + 0xC), 1)
        self.call(BTN_PRESS, MGR, button, maxins=BUDGET)
        self.call(BTN_RELEASE, MGR, button, maxins=BUDGET)
        if shift:
            self.set_p0(self.r32(MGR + 0xC), 0)

    def pad(self, pad: int, velocity: int = 100) -> None:
        self.nbusy = 0
        self.call(PAD_PRESS, MGR, pad, velocity, maxins=BUDGET)
        self.call(PAD_RELEASE, MGR, pad, maxins=BUDGET)

    def knob(self, knob: int, delta: int) -> None:
        self.call(KNOB, MGR, knob, delta & 0xFFFFFFFF, maxins=BUDGET)

    def heartbeat(self, n: int = 1) -> None:
        """n milliseconds of the Main task's 1 ms service (the real route to the main_ms hook point)."""
        for _ in range(n):
            self.call(MS_SERVICE, maxins=BUDGET)

    def leds(self) -> list[int]:
        uc = self.uc
        uc.mem_write(OUT, bytes(2 * N_LEDS))
        uc.reg_write(UC_ARM_REG_SP, 0x2006F000)
        uc.reg_write(UC_ARM_REG_R0, MGR)
        uc.reg_write(UC_ARM_REG_R1, OUT)
        uc.emu_start(LED_SITE | 1, LED_SITE + 4, count=BUDGET)
        pc = uc.reg_read(UC_ARM_REG_PC)
        if pc & ~1 != (LED_SITE + 4) & ~1:
            raise AssertionError(f"led refresh did not complete: pc={pc:#010x}")
        return list(struct.unpack(f"<{N_LEDS}H", bytes(uc.mem_read(OUT, 2 * N_LEDS))))

    def shape(self) -> tuple:
        return self.r8(MGR + 0x152), self.r32(MGR + 0x6C), self.store_p0(self.r32(MGR + 0x14))

    def lock_takes(self) -> int:
        return sum(1 for e in self.ev if e[0] == "dsp")

    def outputs(self) -> dict:
        return dict(shape=self.shape(), leds=self.leds(), ev=list(self.ev), dsp=list(self.dsp_writes),
                    forbidden_writes=list(self.forbidden_writes))
