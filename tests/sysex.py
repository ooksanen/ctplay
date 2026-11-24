"""SysEx in and out for emulation harnesses: requests enter at stock's dispatcher entry 0x0801EB30 (where slim's
sysex_in hook sits); every call of stock's SysEx output 0x08020C90 is caught and skipped. A mixin for NoteHarness
subclasses (VoiceHarness, LinkHarness)."""
from __future__ import annotations

import struct

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2

SYSEX_IN, SYSEX_CONT, SYSEX_OUT, ROUTER_PTR = 0x0801EB30, 0x0801EB34, 0x08020C90, 0x200069F4
SIG = bytes([0xF0, 0x7D, 0x53, 0x4C])
BUF, MSG = 0x2006D800, 0x2006D7F0          # scratch next to notes.OUTBUF (0x2006D000, mapped, unused by the snapshot)


class SysexCapture:
    def __init__(self, image: bytes):
        super().__init__(image)
        self.out: list[tuple[int, int, bytes]] = []    # (router, port mask, bytes) of each sysex_out call
        self.forwarded = 0

        def ret(u):
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR) | 1)

        def sysex_out(u, a, s, d):
            bp, ln = struct.unpack("<II", bytes(u.mem_read(u.reg_read(UC_ARM_REG_R2), 8)))
            self.out.append((u.reg_read(UC_ARM_REG_R0), u.reg_read(UC_ARM_REG_R1), bytes(u.mem_read(bp, ln))))
            ret(u)

        def forwarded(u, a, s, d):                 # reached stock's dispatcher body: not ours (stack left as is)
            self.forwarded += 1
            ret(u)

        self.uc.hook_add(UC_HOOK_CODE, sysex_out, begin=SYSEX_OUT, end=SYSEX_OUT)
        self.uc.hook_add(UC_HOOK_CODE, forwarded, begin=SYSEX_CONT, end=SYSEX_CONT)

    def sysex(self, data: bytes, port: int = 0) -> None:
        self.out.clear()
        self.forwarded = 0
        self.uc.mem_write(BUF, bytes(data))
        self.uc.mem_write(MSG, struct.pack("<II", BUF, len(data)))
        self.call(SYSEX_IN, port, MSG, 0)
