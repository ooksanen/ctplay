"""Shared helpers for the PL20 trig-conditions storage spike, part A (throwaway; stock image). Run from slim/ with
PYTHONPATH=.:tests:../tools:docs/investigations/2026-11-01-trig-conditions-spike ../.venv/bin/python <script>.

Storage under test (spec 2026-10-28-trig-conditions-design.md, "Storage"): drums: pattern + 0x84..+0xA7 (one byte a
step at + 0x88 + step, one bit a step at + 0x84..+0x87); note tracks: step bytes [2] / [3] (pattern + 28 step + 2)."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_LR

HERE = Path(__file__).resolve().parent
SLIM = HERE.parents[2]
sys.path[:0] = [str(SLIM), str(SLIM / "tests"), str(SLIM.parent / "tools")]

from harness import BTN_PRESS, BTN_RELEASE, MGR  # noqa: E402
from notes import (PARAM_COMMIT, PARAM_GET, PARAM_WPTR, PATTERN_BASE, PLAY_STORE, NoteHarness, param,  # noqa: E402
                   set_tempo)

STOCK = (SLIM.parent / "stock" / "circuittracks-firmware-4486-STOCK.bin").read_bytes()

ENGINE = 0x20038EC0
SESSION = 0x2003D71C
SEQ_TICK = 0x0802C418
DREC = 0x2003C184                     # [DREC + 4 d]: drum d's recorder; [+ 0x48] its patterns
PLAYER = 0x20040810                   # drum d's player at + 0x90 d; [+ 0x4C] its note interface (sink)
NOTE_ON, NOTE_OFF = 0x0801D38E, 0x0801D942
DPAT, NPAT, NSTEP = 0x6A8, 0xCA8, 28
COND_LO, COND_HI = 0x84, 0xA8         # drum settings bytes under test
BTN = dict(patterns=13, clear=23, dup=24, play=17, record=16, note=9, pset=12, half=21, save=25, shift=27)

# stock pattern writers, by what the code does (re/app.asm; the dispatcher 0x0802DBC0 / 0x0802DDDA / 0x0802E074)
FUNCS = {
    0x0803E2AA: "drum Duplicate paste", 0x0803E272: "drum Duplicate source", 0x0803E3B0: "drum Clear pattern",
    0x0803E18A: "drum Clear step", 0x0803E93A: "drum copy 1-16>17-32", 0x0803DF72: "drum copy step (source)",
    0x0803DFAE: "drum paste step", 0x0803E6F0: "drum Mutate",
    0x0803D2B0: "note Duplicate paste", 0x0803D27C: "note Duplicate source", 0x0803D310: "note Clear pattern",
    0x0803D1D4: "note Clear step", 0x0803D230: "note step fill", 0x0803D16E: "note paste step",
    0x0803D132: "note copy step (source)", 0x0803DD24: "note copy 1-16>17-32", 0x0803D53C: "note Mutate",
    0x0803EA1C: "drum editor write-back (store listener)", 0x0803FA26: "drum recorder write",
    0x0803F7BE: "note recorder commit", 0x0804B094: "note step add", 0x0803C68C: "command send",
}


class H(NoteHarness):
    """NoteHarness on stock + a tick counter, a call log of FUNCS, the drum players' note-ons and an optional
    memory-read watch over the condition bytes (pc, address, size, phase)."""

    def __init__(self, image: bytes = STOCK, watch: bool = False):
        super().__init__(image)
        self.ticks = 0
        self.calls: list[tuple] = []
        self.hits: list[tuple] = []          # (tick, drum, note, vel) at the drum players' sinks
        self.reads: list[tuple] = []         # (phase, pc, lr, addr, size)
        self.phase = "setup"
        self.watching = False
        uc = self.uc

        def tick(u, a, s, d):
            self.ticks += 1
        uc.hook_add(UC_HOOK_CODE, tick, begin=SEQ_TICK, end=SEQ_TICK)

        def fn(u, a, s, d):
            self.calls.append((self.phase, FUNCS[a], tuple(u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1,
                                                                                  UC_ARM_REG_R2, UC_ARM_REG_R3))))
        for a in FUNCS:
            uc.hook_add(UC_HOOK_CODE, fn, begin=a, end=a)

        sinks = [self.r32(PLAYER + 0x90 * d + 0x4C) for d in range(4)]

        def hit(u, a, s, d):
            r0 = u.reg_read(UC_ARM_REG_R0)
            if r0 in sinks:
                self.hits.append((self.ticks, sinks.index(r0), "on" if a == NOTE_ON else "off",
                                  u.reg_read(UC_ARM_REG_R1), u.reg_read(UC_ARM_REG_R2) if a == NOTE_ON else None))
        uc.hook_add(UC_HOOK_CODE, hit, begin=NOTE_ON, end=NOTE_ON)
        uc.hook_add(UC_HOOK_CODE, hit, begin=NOTE_OFF, end=NOTE_OFF)

        if watch:
            self._watch()

    def watched(self, addr, size):
        """'drum' / 'note<t>' when [addr, addr + size) meets a condition byte, else None."""
        b0 = self.dbase(0)
        if b0 <= addr + size and addr < b0 + 4 * 8 * DPAT:
            for a in range(max(addr, b0), min(addr + size, b0 + 4 * 8 * DPAT)):
                if COND_LO <= (a - b0) % DPAT < COND_HI:
                    return "drum"
        for t in range(4):
            lo = PATTERN_BASE[t]
            if lo <= addr + size and addr < lo + 8 * NPAT:
                for a in range(max(addr, lo), min(addr + size, lo + 8 * NPAT)):
                    o = (a - lo) % NPAT
                    if o < 32 * NSTEP and o % NSTEP in (2, 3):
                        return f"note{t}"
        return None

    def _watch(self):
        """A read hook over the drum and note patterns. Unicorn 2.1.4 raises 'invalid instruction' when a memory hook
        fires on a load inside an IT block (stock's memcmp 0x08025180 and memcpy 0x0801AA14 / 0x0801AA34 have them):
        those three are run in Python here, with their reads logged against the caller (lr)."""
        uc = self.uc
        b0 = self.dbase(0)
        dlo, dhi = b0, b0 + 4 * 8 * DPAT

        def lib(u, a, s, d):
            r0, r1, r2, lr = (u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_LR))
            if self.watching:
                for base, n in ((r1, r2),) + (((r0, r2),) if a == 0x08025180 else ()):
                    w = self.watched(base, n) if n else None
                    if w:
                        self.reads.append((self.phase, a, lr, base, n, w))
            if a == 0x08025180:
                x, y = bytes(u.mem_read(r0, r2)), bytes(u.mem_read(r1, r2))
                res = 0
                for i in range(r2):
                    if x[i] != y[i]:
                        res = (x[i] - y[i]) & 0xFFFFFFFF
                        break
                u.reg_write(UC_ARM_REG_R0, res)
            else:
                if r2:
                    u.mem_write(r0, bytes(u.mem_read(r1, r2)))
                u.reg_write(UC_ARM_REG_R0, r0 + r2)
                u.reg_write(UC_ARM_REG_R1, r1 + r2)
            u.reg_write(UC_ARM_REG_PC, lr | 1)
        for a in (0x08025180, 0x0801AA14, 0x0801AA34):
            uc.hook_add(UC_HOOK_CODE, lib, begin=a, end=a)

        def rd(u, access, addr, size, value, d):
            if not self.watching:
                return
            if dlo <= addr < dhi:
                o = (addr - b0) % DPAT
                if o < COND_HI and o + size > COND_LO:
                    self.reads.append((self.phase, u.reg_read(UC_ARM_REG_PC), u.reg_read(UC_ARM_REG_LR), addr, size,
                                       "drum"))
                return
            for t in range(4):
                lo = PATTERN_BASE[t]
                if lo <= addr < lo + 8 * NPAT:
                    o = (addr - lo) % NPAT
                    if o < 32 * NSTEP:
                        so = o % NSTEP
                        if so < 4 and so + size > 2 or (so + size > NSTEP + 2):
                            self.reads.append((self.phase, u.reg_read(UC_ARM_REG_PC), u.reg_read(UC_ARM_REG_LR),
                                               addr, size, f"note{t}"))
                    return
        uc.hook_add(UC_HOOK_MEM_READ, rd, begin=dlo, end=dhi - 1)
        for t in range(4):
            uc.hook_add(UC_HOOK_MEM_READ, rd, begin=PATTERN_BASE[t], end=PATTERN_BASE[t] + 8 * NPAT - 1)

    # buttons
    def hold(self, b):
        self.nbusy = 0
        self.call(BTN_PRESS, MGR, b)

    def let_go(self, b):
        self.nbusy = 0
        self.call(BTN_RELEASE, MGR, b)

    def until_tick(self, t, cap=200_000):
        for _ in range(cap):
            if self.ticks >= t:
                return
            self.heartbeat(1)
        raise AssertionError("no tick")

    def playing(self):
        return param(self, PLAY_STORE, 0)

    def play(self, on=True):
        if bool(self.playing()) != on:
            self.press(BTN["play"])
        assert bool(self.playing()) == on

    def fcalls(self, *names):
        return [c for c in self.calls if not names or c[1] in names]

    # drums
    def drec(self, d):
        return self.r32(DREC + 4 * d)

    def dbase(self, d):
        return self.r32(self.drec(d) + 0x48)

    def dpat(self, d, p):
        return self.dbase(d) + DPAT * p

    def deditor(self, d):
        return self.r32(0x200438DC + 0x3C * d + 0xC) - 0x18

    def dshown(self, d):
        return param(self, self.r32(self.drec(d) + 0x14), 0) & 7

    def dselected(self, d):
        return param(self, self.r32(self.drec(d) + 0x14), 1)

    def track_playing(self, t):
        return param(self, self.r32(ENGINE + 0x30 + 4 * t), 0) & 7

    def set_chain(self, t, first, last):
        st = self.r32(ENGINE + 0x9C)
        self.call(PARAM_GET, st, t)
        v = self.r32(self.uc.reg_read(UC_ARM_REG_R0))
        self.call(PARAM_WPTR, st, t)
        self.uc.mem_write(self.uc.reg_read(UC_ARM_REG_R0), struct.pack("<I", (v & ~0xFFFF) | first | last << 8))
        self.call(PARAM_COMMIT, st)

    def dcond(self, d, p):
        return bytes(self.uc.mem_read(self.dpat(d, p) + COND_LO, COND_HI - COND_LO))

    def set_dcond(self, d, p, data):
        assert len(data) == COND_HI - COND_LO
        self.uc.mem_write(self.dpat(d, p) + COND_LO, bytes(data))

    def darrays(self, d, p):
        raw = bytes(self.uc.mem_read(self.dpat(d, p), 0x80))
        return raw[0:32], raw[0x20:0x40], raw[0x40:0x60], raw[0x60:0x80]   # vel, prob, flip, micro

    def dpattern(self, d, p):
        return bytes(self.uc.mem_read(self.dpat(d, p), DPAT))

    def dload(self, d):
        """Stock's drum editor load (0x0803F050): the step store from the shown pattern (as a pattern change)."""
        self.call(0x0803F050, self.deditor(d))

    def set_dhits(self, d, p, hits, load=True):
        """Raw: hits {step: (vel, micro, prob, flip)}, other steps empty; steps 1-32; then stock's editor load."""
        v, pr, fl, mi = bytearray(32), bytearray([7] * 32), bytearray([0xFF] * 32), bytearray(32)
        for s, (vel, micro, prob, flip) in hits.items():
            v[s], mi[s], pr[s], fl[s] = vel, micro, prob, flip
        self.uc.mem_write(self.dpat(d, p), bytes(v + pr + fl + mi))
        self.uc.mem_write(self.dpat(d, p) + 0x80, bytes([31, 0]))
        if load and self.dshown(d) == p:
            self.dload(d)

    # note tracks
    def npat(self, t, p):
        return PATTERN_BASE[t] + NPAT * p

    def neditor(self, t):
        return self.r32(0x20042890 + 0x3C * t + 0xC) - 0x18

    def nshown(self, t):
        return param(self, self.r32(self.neditor(t) + 0x24), 0) & 7

    def nselected(self, t):
        return param(self, self.r32(self.neditor(t) + 0x24), 1)

    def nb23(self, t, p):
        """Bytes [2] and [3] of the 32 steps of track t's pattern p (64 B)."""
        base = self.npat(t, p)
        return b"".join(bytes(self.uc.mem_read(base + NSTEP * s + 2, 2)) for s in range(32))

    def set_nb23(self, t, p, data):
        base = self.npat(t, p)
        for s in range(32):
            self.uc.mem_write(base + NSTEP * s + 2, bytes(data[2 * s:2 * s + 2]))

    def nstep(self, t, p, s):
        return bytes(self.uc.mem_read(self.npat(t, p) + NSTEP * s, NSTEP))

    def nstore_word0(self, t):
        """Word 0 of the note editor's step store (the selected step's bytes 0-3), read view."""
        st = self.r32(self.neditor(t) + 0x20)
        self.call(PARAM_GET, st, 0)
        return bytes(self.uc.mem_read(self.uc.reg_read(UC_ARM_REG_R0), 4))

    def sync_nstore(self, t):
        """Bring the selected step's word 0 in the note step store in line with the pattern (write pointer, commit),
        as the spec's write for the editor's selected step."""
        ed = self.r32(self.neditor(t) + 0x20)
        p, s = self.nshown(t), self.nselected(t)
        w0 = bytes(self.uc.mem_read(self.npat(t, p) + NSTEP * s, 4))
        self.call(PARAM_WPTR, ed, 0)
        self.uc.mem_write(self.uc.reg_read(UC_ARM_REG_R0), w0)
        self.call(PARAM_COMMIT, ed)

    # Patterns view
    def patterns_view(self):
        self.press(BTN["patterns"])
        v = self.r32(MGR + 0x6C)
        assert self.r32(v) == 0x0805A5F0, hex(self.r32(v))
        return v

    def pv_pad(self, t, p):
        """The Patterns view's pad of track t's pattern p (columns = tracks 0-7, rows = patterns page * 4 + row;
        0x080446E6, 0x0804423C), on page 0 only."""
        v = self.r32(MGR + 0x6C)
        assert self.r8(v + 0x78) == p // 4, ("page", self.r8(v + 0x78))
        return 8 * (p % 4) + t

    def duplicate(self, t, src, dst):
        """Patterns view, Duplicate held, source pad, target pad, Duplicate let go (as stock does it)."""
        self.patterns_view()
        self.hold(BTN["dup"])
        self.pad(self.pv_pad(t, src))
        self.pad(self.pv_pad(t, dst))
        self.let_go(BTN["dup"])

    def clear_pattern_pv(self, t, p):
        self.patterns_view()
        self.hold(BTN["clear"])
        self.pad(self.pv_pad(t, p))
        self.let_go(BTN["clear"])


def dtag(d, p):
    """36 distinct bytes for drum d's pattern p (+0x84..+0xA7): 4 bit bytes, then 0x88 + s = a per-step code."""
    bits = bytes([(0x5A + 0x11 * d + 0x22 * p) & 0xFF, (0xC3 + 0x07 * p) & 0xFF, (0x96 + d) & 0xFF,
                  (0x3C + 0x13 * p) & 0xFF])
    return bits + bytes([((p * 32 + s) * 7 + d * 3 + 1) & 0xFF or 0xEE for s in range(32)])


def ntag(t, p):
    """64 distinct bytes for track t's pattern p: [2], [3] of each step."""
    return b"".join(bytes([0x80 | (p << 3) | t, s + 1 + 0x40 * (t & 1)]) for s in range(32))


def hexs(b):
    return b.hex(" ")


# ---- Q2 helpers
DCODE = [(0x40 + 5 * s) & 0xFF for s in range(32)]          # per-step code at + 0x88 + s
DBITS = bytes([0x35, 0x9C, 0xA5, 0x0F])                     # + 0x84..+ 0x87, bit s = byte s >> 3, bit s & 7


def dcond_img():
    return DBITS + bytes(DCODE)


def dsteps(h, d, p):
    """Per step: (vel, micro, prob, flip, code at + 0x88 + s, bit s of + 0x84..)."""
    raw = h.dpattern(d, p)
    return [(raw[s], raw[0x60 + s], raw[0x20 + s], raw[0x40 + s], raw[0x88 + s], raw[0x84 + (s >> 3)] >> (s & 7) & 1)
            for s in range(32)]


def dcode_of(before_steps, code):
    """The step whose code (before) this is, or None."""
    for s, st in enumerate(before_steps):
        if st[4] == code:
            return s
    return None


def prob_view(h, track):
    """Pattern Settings twice: the probability view (mode 5): top half = steps, row 3 = pads 16-23."""
    h.press(track)
    for _ in range(3):
        if h.view_mode() == 5:
            break
        h.press(BTN["pset"])
    assert h.view_mode() == 5, h.view_mode()


def step_view(h, track):
    h.press(track)
    for _ in range(4):
        if h.view_mode() == 1:
            break
        h.press(BTN["note"])
    assert h.view_mode() == 1, h.view_mode()
