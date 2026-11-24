"""Shared helpers for the PL19 pattern-strum spike (throwaway). Run from slim/ with
PYTHONPATH=.:tests:../tools:docs/investigations/2026-10-31-pattern-strum-spike (README).

PL18 is built into pl18/ beside this file on first use (not committed): at the spike's commit the sources are PL18's.
Track 0 (Synth 1), its Note view (two rows), pattern 0 cleared with steps 0 .. last."""
from __future__ import annotations

import json
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP

from chord_model import settings
from notes import PATTERN_BASE, STEP, TEMPO_STORE, NoteHarness, param, set_tempo, step_addr
from test_mono import quantise_off

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RECORDERS = 0x2003C174
PLACE, NOTE_OFF, TICK, FLUSH, PASS = 0x0803F298, 0x0803F5B0, 0x0803F62A, 0x0803F67C, 0x0803F6C6
COMMIT = 0x0803F7BE
SITES = (0x0803F60C, 0x0803F6A2, 0x0803F78C)   # hook rec_committed: note-off path, flush, tick pass
SITE_NAMES = dict(zip(SITES, ("note-off", "flush", "pass")))
SEQ_TICK, SEQ_START = 0x0802C418, 0x0802C008
SET = 0x380                       # pattern + 0x380 last step, + 0x381 first, + 0x382 sync rate
STEP_TICKS = 0x0805B8B8
GAP_MS = {1: 80, 2: 40, 3: 20}
GAP_TICKS = {1: 4, 2: 2, 3: 1}    # the plan's WRITTEN_GAP
PLAY, RECORD = 17, 16


def pl18():
    d = HERE / "pl18"
    if not (d / "manifest.json").exists():
        from slimbuild import build
        d.mkdir(exist_ok=True)
        build.build(ROOT / "slim/versions/PL18.toml", d)
    return (d / "circuittracks-4486-PL18.bin").read_bytes(), json.loads((d / "manifest.json").read_text())


def sym(m, name):
    return int(m["symbols"][name], 16)


def W(w):
    """A converted pending word: unit, step, pattern, vel, start, micro."""
    return dict(unit=w & 7, step=w >> 3 & 31, pattern=w >> 8 & 7, vel=w >> 11 & 0x7F, start=w >> 18 & 0x7FF, micro=w >> 29)


def mkword(unit, step, pattern, vel, start, micro):
    return (unit & 7) | (step & 31) << 3 | (pattern & 7) << 8 | (vel & 0x7F) << 11 | (start & 0x7FF) << 18 | (micro & 7) << 29


class SH(NoteHarness):
    """NoteHarness + the recorder's calls on track 0 (placement, note-off, tick pass, commit) with the task and ms."""

    def __init__(self, image, track=0):
        super().__init__(image)
        self.t = track
        self.task, self.ms, self.ticks = "ui", 0, 0
        self.places, self.commits, self.passes, self.noteoffs = [], [], [], []
        self.strum = []           # the recorder's notes of the current press, in placement (= send) order
        self.on_commit = None     # callback(h, note, end) at the commit's entry (before slim's rec_commit handlers)
        self.site = None          # the stock call site of the commit in progress (hook rec_committed's sites)
        uc = self.uc

        def site(u, a, s, d):
            self.site = a
        for a in SITES:
            uc.hook_add(UC_HOOK_CODE, site, begin=a, end=a)

        def tick(u, a, s, d):
            self.ticks += 1
        uc.hook_add(UC_HOOK_CODE, tick, begin=SEQ_TICK, end=SEQ_TICK)

        def place(u, a, s, d):
            r = [u.reg_read(UC_ARM_REG_R0 + i) for i in range(4)]
            if r[0] != self.rec():
                return
            sp = u.reg_read(UC_ARM_REG_SP)
            start, note, vel = struct.unpack("<III", bytes(u.mem_read(sp, 12)))
            off = r[3] if r[3] < 0x80000000 else r[3] - (1 << 32)
            self.places.append(dict(ms=self.ms, task=self.task, pattern=r[1], step=r[2], off=off, start=start & 0x7FF,
                                    note=note & 0xFF, vel=vel & 0xFF, idx=self.r8(self.rec() + 0x9C),
                                    claims=self.r8(self.rec() + 0x9D)))
            self.strum.append(note & 0xFF)
        uc.hook_add(UC_HOOK_CODE, place, begin=PLACE, end=PLACE)

        def noteoff(u, a, s, d):
            r = [u.reg_read(UC_ARM_REG_R0 + i) for i in range(3)]
            if r[0] == self.rec():
                self.noteoffs.append((self.ms, self.task, r[2], r[1]))
        uc.hook_add(UC_HOOK_CODE, noteoff, begin=NOTE_OFF, end=NOTE_OFF)

        def pss(u, a, s, d):
            r = [u.reg_read(UC_ARM_REG_R0 + i) for i in range(4)]
            if r[0] == self.rec():
                self.passes.append((self.ms, self.task, r[1], r[2], r[3] & 0x7FF))
        uc.hook_add(UC_HOOK_CODE, pss, begin=PASS, end=PASS)

        def commit(u, a, s, d):
            r = [u.reg_read(UC_ARM_REG_R0 + i) for i in range(3)]
            if r[0] != self.rec():
                return
            note, end = r[1], r[2] & 0x7FF
            w = self.pending(note)
            if w & 7 == 7:
                return                                       # nothing pending: stock writes nothing
            e = dict(ms=self.ms, task=self.task, site=SITE_NAMES.get(self.site, "?"), note=note, end=end, word=w,
                     claims=self.r8(self.rec() + 0x9D))
            if self.on_commit:
                self.on_commit(self, note, end)
                e["moved"] = self.pending(note)
            self.commits.append(e)
        uc.hook_add(UC_HOOK_CODE, commit, begin=COMMIT, end=COMMIT)

    def heartbeat(self, n=1):
        self.task = "main"
        for _ in range(n):
            super().heartbeat(1)
            self.ms += 1
        self.task = "ui"

    def rec(self):
        return self.r32(RECORDERS + 4 * self.t)

    def pending(self, note):
        return self.r32(self.rec() + 0x9C + 4 * note)

    def set_pending(self, note, w):
        self.uc.mem_write(self.rec() + 0x9C + 4 * note, struct.pack("<I", w))

    def list_entry(self, i):
        """The recorder's note list rec + 0x54 + 12 i: note, vel, unit, released, start, end, off."""
        b = bytes(self.uc.mem_read(self.rec() + 0x54 + 12 * i, 12))
        w = struct.unpack_from("<I", b, 4)[0]
        off = w >> 24 & 0x3F
        return dict(note=b[0], vel=b[1], unit=b[2], released=b[3] & 1, start=w & 0x7FF, end=w >> 11 & 0x7FF,
                    off=off - 64 if off & 0x20 else off)

    def in_list(self, note):
        """Is the note's pending word still a list index (placed, not yet converted by a tick pass)? Stock's own test
        in the note-off path 0x0803F5D2."""
        w = self.pending(note)
        return w & 7 != 7 and self.list_entry(w & 7)["note"] == note

    def quant(self):
        return self.r8(self.rec() + 0x35)


def prepare(h, last=31, first=0, bpm=None):
    h.track(h.t)
    if bpm:
        set_tempo(h, bpm=bpm)
    base = PATTERN_BASE[h.t]
    h.uc.mem_write(base, bytes(32 * STEP))
    h.uc.mem_write(base + SET, bytes([last, first]))


def setup(image, m, shape=1, speed=1, down=False, quantise=True, last=31, bpm=None, bass=0):
    from test_chord import set_chord, set_down, set_strum
    h = SH(image)
    prepare(h, last=last, bpm=bpm)
    set_chord(h, m, 0, settings(shape, bass=bass))
    set_strum(h, m, 0, speed)
    set_down(h, m, 0, down)
    h.press(PLAY)
    h.recording(True)
    h.heartbeat(3)
    if not quantise:
        quantise_off(h)
    return h


def step_ms(h):
    return 60000 / param(h, TEMPO_STORE, 0) / 4


def wait_tick(h, tick):
    """Heartbeats until h.ticks >= tick (h.ticks counts seq_tick calls since the harness started)."""
    while h.ticks < tick:
        h.heartbeat(1)


def units(h, s, p=0):
    a = step_addr(h.t, p, s)
    mask = h.r8(a)
    return [tuple(h.uc.mem_read(a + 4 + 4 * u, 4)) for u in range(6) if mask >> u & 1]


def unit_map(h, s, p=0):
    """{unit: (note, gate, micro, vel)} of the step's used units."""
    a = step_addr(h.t, p, s)
    mask = h.r8(a)
    return {u: tuple(h.uc.mem_read(a + 4 + 4 * u, 4)) for u in range(6) if mask >> u & 1}


def written(h, p=0):
    return {s: units(h, s, p) for s in range(32) if units(h, s, p)}


def put(h, s, notes, p=0, micro=0):
    """Raw notes in units 0.. of step s (others already on the step: they must survive)."""
    body = b"".join(bytes([n, 6, micro, 90]) for n in notes) + bytes(4 * (6 - len(notes)))
    h.uc.mem_write(step_addr(h.t, p, s), bytes([(1 << len(notes)) - 1, 7, 0, 0]) + body)


# ---- Route (a): rewrite the note's pending word at the commit's entry (a model of an entry hook on rec_commit at
#      priority 40, before mono's and recfix's handlers; the Unicorn hook runs before slim's patched entry).

class Route:
    """mode "played": every note of the strum at the first note's step, microstep and start (length from that start).
    mode "written": note k at the first's position + k x gap ticks (sixths by the pattern's rate), spilling into the
    next steps, wrapping from last to first; start = the first's start + k x gap (length from its own position).
    The unit: the first one free in the target step's mask | [rec + 0x9D] | the units other pending words claim for that
    pattern and step (recfix.c claimed()); none free = bits 0-2 = 7 (the note is left out). naive=True keeps stock's unit
    (the one claimed in the note's original step)."""

    def __init__(self, h, mode, gap=0, naive=False):
        self.h, self.mode, self.gap, self.naive = h, mode, gap, naive
        self.first_w = None        # the first note's word, latched at its own commit
        self.log = []
        h.on_commit = self

    def first_word(self, first, w_k):
        h = self.h
        if self.first_w is not None:
            return self.first_w, "latched"
        if h.in_list(first):
            # not converted yet (only in the same tick pass, a later list index): same pass, so the same step and
            # start; quantise on: microstep 0 (quantise off would need its own offset: not modelled)
            return w_k & ~(7 << 29) | 0, "in list"
        w = h.pending(first)
        if w & 7 == 7:
            return None, "gone"
        return w, "pending"

    def claimed(self, pattern, step, note):
        h = self.h
        rec = h.rec()
        mask = h.r8(rec + 0x9D)
        for n in range(1, 140):
            if n == note:
                continue
            w = h.pending(n)
            if w & 7 != 7 and (w & 0x7F8) == (pattern << 8 | step << 3):
                mask |= 1 << (w & 7)
        return mask

    def __call__(self, h, note, end):
        if note not in h.strum:
            return
        k = h.strum.index(note)
        w = h.pending(note)
        if k == 0:
            self.first_w = w
            self.log.append(("first", note, W(w)))
            return
        f, how = self.first_word(h.strum[0], w)
        if f is None:
            self.log.append(("no first", note, how))
            return
        F = W(f)
        pat = PATTERN_BASE[h.t] + 0xCA8 * F["pattern"]
        rate, last, first = h.r8(pat + SET + 2), h.r8(pat + SET), h.r8(pat + SET + 1)
        per = h.r32(STEP_TICKS + 4 * rate)
        if self.mode == "played":
            step, micro, start = F["step"], F["micro"], F["start"]
        else:
            sixths = F["micro"] + (k * self.gap * 6 + per // 2) // per
            step, micro = F["step"] + sixths // 6, sixths % 6
            while step > last:
                step -= last - first + 1
            start = (F["start"] + k * self.gap) & 0x7FF
        guard = ((end - start) & 0x7FF) >= 0x400
        if guard:
            start = (end - 1) & 0x7FF                    # released before its own position: the shortest note
        if self.naive:
            unit = w & 7
        else:
            a = step_addr(h.t, F["pattern"], step)
            taken = h.r8(a) | self.claimed(F["pattern"], step, note)
            unit = next((u for u in range(6) if not taken >> u & 1), 7)
            for u in range(6):                           # stock's own search: the unit with this note and microstep
                if h.r8(a) >> u & 1 and h.r8(a + 4 + 4 * u) == note and h.r8(a + 6 + 4 * u) == micro:
                    unit = u
                    break
        nw = mkword(unit, step, F["pattern"], W(w)["vel"], start, micro)
        h.set_pending(note, nw)
        self.log.append(("moved", note, k, how, W(w), W(nw), "guard" if guard else ""))
