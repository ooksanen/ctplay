"""Shared helpers for the drum note-repeat recording spike (throwaway). Run from slim/ with
PYTHONPATH=.:tests:../tools:<this dir>."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0

from notes import NoteHarness, PLAY_STORE, TEMPO_STORE, param, set_tempo, PARAM_GET, PARAM_WPTR, PARAM_COMMIT

ROOT = Path(__file__).resolve().parents[4]
STOCK = (ROOT / "stock/circuittracks-firmware-4486-STOCK.bin").read_bytes()

CONT = 0x20040DB8
NOTE_ON, NOTE_OFF = 0x0801D38E, 0x0801D942
SEQ_TICK = 0x0802C418
DREC = 0x2003C184            # [DREC + 4d] drum recorder d
PLAYER = 0x20040810          # + 0x90 d
ENGINE = 0x20038EC0
SESSION = 0x2003D71C
PLAY, RECORD, NOTE_BTN = 17, 16, 9
PAT = 0x6A8
REC_SLOT0 = 0x0803FC5E       # drum (and note) recorder slot 0
REC_WRITE = 0x0803FA26       # drum recorder write (rec, pattern, step, micro)
GATE_ON, GATE_OFF = 0x0802E56A, 0x0802E5CC


class DH(NoteHarness):
    def __init__(self, image=STOCK):
        super().__init__(image)
        self.ticks = 0
        self.writes = []      # (tick, pattern, step, micro, pending vel) at 0x0803FA26 for drum recorders
        self.slot0 = []       # (tick, rec, note, vel) at the recorder slot 0
        self.gate = []        # (tick, kind, r1, r2, r3) recorder-gate calls
        uc = self.uc

        def tick(u, a, s, d):
            self.ticks += 1
        uc.hook_add(UC_HOOK_CODE, tick, begin=SEQ_TICK, end=SEQ_TICK)

        def wr(u, a, s, d):
            r = [u.reg_read(UC_ARM_REG_R0 + i) for i in range(4)]
            if r[0] in self.drecs():
                self.writes.append((self.ticks, self.drecs().index(r[0]), r[1], r[2], r[3], self.r8(r[0] + 0x54)))
        uc.hook_add(UC_HOOK_CODE, wr, begin=REC_WRITE, end=REC_WRITE)

        def s0(u, a, s, d):
            r = [u.reg_read(UC_ARM_REG_R0 + i) for i in range(4)]
            if r[0] in self.drecs():
                self.slot0.append((self.ticks, self.drecs().index(r[0]), r[1], r[2]))
        uc.hook_add(UC_HOOK_CODE, s0, begin=REC_SLOT0, end=REC_SLOT0)

        def g(u, a, s, d):
            r = [u.reg_read(UC_ARM_REG_R0 + i) for i in range(4)]
            self.gate.append((self.ticks, "on" if a == GATE_ON else "off", r[1], r[2], r[3]))
        uc.hook_add(UC_HOOK_CODE, g, begin=GATE_ON, end=GATE_ON)
        uc.hook_add(UC_HOOK_CODE, g, begin=GATE_OFF, end=GATE_OFF)

    # objects
    def drecs(self):
        return [self.r32(DREC + 4 * d) for d in range(4)]

    def drec(self, d):
        return self.r32(DREC + 4 * d)

    def player(self, d):
        return PLAYER + 0x90 * d

    def expanded_view(self):
        return self.r32(CONT + 0xAC)

    def sample_view(self, d):
        return self.r32(CONT + 0x8C + 4 * d)

    def sink(self, which, d=0):
        if which == "expanded":
            return self.r32(self.expanded_view() + 0x10)
        if which == "sample":
            return self.r32(self.sample_view(d) + 0x10)
        if which == "player":
            return self.r32(self.player(d) + 0x4C)
        raise ValueError(which)

    def store(self, d):
        return self.r32(self.drec(d) + 0x4C)

    def editor(self, d):
        return self.r32(0x200438DC + 0x3C * d + 0xC) - 0x18

    def base(self, d):
        return self.r32(self.drec(d) + 0x48)

    def playing_pattern(self, d):
        return param(self, self.r32(ENGINE + 0x30 + 4 * (4 + d)), 0) & 7

    def mirrored_pattern(self, d):
        return param(self, self.r32(self.drec(d) + 0x14), 0)

    def transport(self):
        return tuple(param(self, PLAY_STORE, i) for i in range(3))

    def quantise_flag(self, d=0):
        return self.r8(self.drec(d) + 0x35)

    def quant_setting(self):
        """settings store 0x200111CC param 2 bit 12 (recorder: quantise = !bit)."""
        self.call(PARAM_GET, 0x200111CC, 2)
        return self.r32(self.uc.reg_read(UC_ARM_REG_R0)) >> 12 & 1

    # pattern
    def arrays(self, d, p):
        b = self.base(d) + PAT * p
        raw = bytes(self.uc.mem_read(b, 0x84))
        return dict(vel=raw[0:32], prob=raw[0x20:0x40], flip=raw[0x40:0x60], micro=raw[0x60:0x80], set=raw[0x80:0x84])

    def store_words(self, d):
        st = self.store(d)
        out = []
        for k in range(32):
            self.call(PARAM_GET, st, k)
            out.append(self.r32(self.uc.reg_read(UC_ARM_REG_R0)))
        b = b"".join(struct.pack("<I", w) for w in out)
        return dict(vel=b[0:32], prob=b[32:64], micro=b[64:96], flip=b[96:128])

    def clear_pattern(self, d, p, last=31, first=0):
        """Raw: empty arrays (vel 0, prob 7, flip FF, micro 0), steps first..last; then stock's editor load
        0x0803F050 brings the step store (and settings store) in line, as a pattern change would."""
        b = self.base(d) + PAT * p
        self.uc.mem_write(b, bytes(32) + bytes([7] * 32) + bytes([0xFF] * 32) + bytes(32))
        self.uc.mem_write(b + 0x80, bytes([last, first]))
        ed = self.editor(d)
        assert self.r32(ed) == 0x0805C108, hex(self.r32(ed))
        self.call(0x0803F050, ed)

    def hits(self, d, p):
        a = self.arrays(d, p)
        return [(s, a["vel"][s], a["micro"][s], a["prob"][s], a["flip"][s]) for s in range(32)
                if a["vel"][s] or a["micro"][s]]

    def store_hits(self, d):
        a = self.store_words(d)
        return [(s, a["vel"][s], a["micro"][s], a["prob"][s], a["flip"][s]) for s in range(32)
                if a["vel"][s] or a["micro"][s]]

    # hits
    def on(self, sink, note=1, vel=100, src=0):
        n0, d0 = len(self.ev), len(self.dsp_writes)
        self.nbusy = 0
        self.call(NOTE_ON, sink, note, vel, src)
        return self.ev[n0:], self.dsp_writes[d0:]

    def off(self, sink, note=1, src=0):
        n0, d0 = len(self.ev), len(self.dsp_writes)
        self.nbusy = 0
        self.call(NOTE_OFF, sink, note, src)
        return self.ev[n0:], self.dsp_writes[d0:]

    def until_tick(self, t, cap=100000):
        """Heartbeats until the sequencer tick counter reaches t."""
        for _ in range(cap):
            if self.ticks >= t:
                return
            self.heartbeat(1)
        raise AssertionError("no tick")


def fmt_hits(hs):
    return " ".join(f"s{s}:v{v}/m{m:06b}/p{p}" + (f"/f{f}" if f != 0xFF else "") for s, v, m, p, f in hs) or "(none)"


def drum_setup(h, mode=6, d=0, bpm=240, last=31):
    """Drum d+1 selected, container mode `mode`; its playing pattern emptied (32 steps)."""
    h.press(4 + d)
    for _ in range(4):
        if h.view_mode() == mode:
            break
        h.press(NOTE_BTN)
    assert h.view_mode() == mode, h.view_mode()
    if bpm:
        set_tempo(h, bpm=bpm)
    p = h.playing_pattern(d)
    assert h.mirrored_pattern(d) == p, (h.mirrored_pattern(d), p)
    h.clear_pattern(d, p, last=last)
    return p


def start_recording(h, settle=2):
    """Play (real button), Record armed as the other slim tests do (transport store p1), count-in p2 = 0."""
    h.press(PLAY)
    h.recording(True)
    h.heartbeat(settle)


ROUTER = 0x2003ECDC


def fixed_velocity(h, on):
    """Bit 1 of parameter 2 of the router's settings store [ROUTER + 0x94] (0x200111CC): forces live drum vel 0x60."""
    st = h.r32(ROUTER + 0x94)
    h.call(PARAM_GET, st, 2)
    v = h.r32(h.uc.reg_read(UC_ARM_REG_R0))
    h.call(PARAM_WPTR, st, 2)
    h.uc.mem_write(h.uc.reg_read(UC_ARM_REG_R0), struct.pack("<I", (v & ~2) | (2 if on else 0)))
    h.call(PARAM_COMMIT, st)
    return v >> 1 & 1


def repeat(h, sink, rate, nticks, note=1, vels=None, src=0, off_mode="before", start=None, log=None):
    """Arp-style clock: after each heartbeat, if the sequencer counted a tick that is a multiple of `rate` since
    `start`, send note-off (of the previous hit) then note-on; off_mode 'half' sends the off rate//2 ticks after the
    on instead; 'none' never sends offs. Returns the number of hits sent."""
    start = h.ticks if start is None else start
    last_tick, n, sounding, off_at = h.ticks, 0, False, None
    first = True                       # the tick  was counted by the last heartbeat: its hit goes now
    while h.ticks - start < nticks:
        if not first:
            h.heartbeat(1)
            if h.ticks == last_tick:
                continue
        first = False
        last_tick = h.ticks
        rel = h.ticks - start
        if sounding and off_mode == "half" and off_at is not None and rel >= off_at:
            h.off(sink, note, src); sounding = False
        if rel % rate == 0:
            if sounding and off_mode == "before":
                h.off(sink, note, src); sounding = False
            v = vels[n % len(vels)] if vels else 100
            r = h.on(sink, note, v, src)
            if log is not None:
                log.append((rel, r))
            sounding, n = True, n + 1
            off_at = rel + max(1, rate // 2)
    if sounding and off_mode != "none":
        h.off(sink, note, src)
    return n
