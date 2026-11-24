"""Voice-level emulation: the synth note-on runs through stock's voice decision with a modelled DSP mailbox.

Approved by the user 2026-10-13 (spec 2026-10-13-voice-log-design.md). The DSP side of the host-port exchange is a dict
of X words: dsp_write (0x080292F8) stores value >> 8 at its address, dsp_read (0x08029344) returns the stored word, and
the wait 0x08029362 (poll dsp_read until a word is zero / non-zero) returns at once, i.e. the DSP acknowledges every
request immediately. Tests set the spare-time reading X:$36 + synth and the DSP's pick X:$35."""
from __future__ import annotations

import struct

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2

from notes import SYNTH_OFF, SYNTH_ON, NoteHarness
from sysex import BUF, ROUTER_PTR, SIG, SysexCapture  # noqa: F401 (BUF, ROUTER_PTR: re-exported for the tests)

DSP_READ, DSP_WRITE, DSP_WAIT = 0x08029344, 0x080292F8, 0x08029362
S, SLOTS = 0x200067FC, 0x20005F64
THRESHOLD = 0x14000
VOICE_MODE = {0: 0x20010064, 1: 0x200101BC}   # each synth's patch voice mode in RAM (0 Mono, 1 Mono AG, 2 Poly); the
                                             # snapshot has Synth 1 on Mono AG (stock's mono picker: voice 0 every time)
DECIDED = 0x080219F4                       # the instruction after `bl voice_decide` (0x080219F0)
PAD = 232


class VoiceHarness(SysexCapture, NoteHarness):
    STUB_SYNTH = False

    def __init__(self, image: bytes):
        super().__init__(image)
        self.x: dict[int, int] = {}
        self.script: list[int] = []
        self.decisions: list[dict] = []
        uc = self.uc

        def ret(u, value=None):
            if value is not None:
                u.reg_write(UC_ARM_REG_R0, value)
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR) | 1)

        def write(u, a, s, d):
            self.x[u.reg_read(UC_ARM_REG_R2)] = u.reg_read(UC_ARM_REG_R1) >> 8

        def read(u, a, s, d):
            addr = u.reg_read(UC_ARM_REG_R1)
            if addr in (0x36, 0x37) and self.script:      # the spare-time read of voice_decide
                self.x[addr] = self.script.pop(0)
            ret(u, self.x.get(addr, 0))

        def wait(u, a, s, d):
            ret(u)

        def synth_on(u, a, s, d):
            self.log.append(("synth_on", *(u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))))

        uc.hook_add(UC_HOOK_CODE, write, begin=DSP_WRITE, end=DSP_WRITE)
        uc.hook_add(UC_HOOK_CODE, read, begin=DSP_READ, end=DSP_READ)
        uc.hook_add(UC_HOOK_CODE, wait, begin=DSP_WAIT, end=DSP_WAIT)
        uc.hook_add(UC_HOOK_CODE, synth_on, begin=SYNTH_ON, end=SYNTH_ON)

        def decided(u, a, s, d):
            self.decisions.append(dict(synth=self.state(4), note=self.state(0xA), voice=self.state(5),
                                       dsp=self.state(0xE)))

        def synth_off(u, a, s, d):
            self.log.append(("synth_off", u.reg_read(UC_ARM_REG_R0), u.reg_read(UC_ARM_REG_R1)))

        uc.hook_add(UC_HOOK_CODE, decided, begin=DECIDED, end=DECIDED)
        uc.hook_add(UC_HOOK_CODE, synth_off, begin=SYNTH_OFF, end=SYNTH_OFF)

    def set_headroom(self, value: int, synth: int | None = None) -> None:
        for s in ((0, 1) if synth is None else (synth,)):
            self.x[0x36 + s] = value

    def set_voice_mode(self, synth: int, mode: int) -> None:
        """The synth's patch voice mode as 0x08036188(synth, 2) reads it: 2 = Poly (the user's device patches)."""
        self.uc.mem_write(VOICE_MODE[synth], bytes([mode]))

    def set_dsp_voice(self, v: int) -> None:
        self.x[0x35] = v << 8

    def state(self, off: int) -> int:
        return self.r8(S + off)

    def slot_state(self, v: int) -> int:
        return struct.unpack("<I", bytes(self.uc.mem_read(SLOTS + 16 * v + 4, 4)))[0]

    def req(self, cmd: int, payload=(), seq: int = 5, port: int = 0, pad: int = PAD):
        body = list(SIG) + [cmd, seq] + list(payload)
        body += [0] * max(0, pad - 1 - len(body))
        self.sysex(bytes(body + [0xF7]), port)
        return self.out[0] if len(self.out) == 1 else None
