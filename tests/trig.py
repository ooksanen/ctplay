"""Shared helpers for PL20's trig-condition tests (plan 2026-11-07-trig-conditions.md, "Shared test helpers"): a
DrumHarness with the builder check's routes (docs/investigations/2026-11-01-trig-conditions-spike/b_lib.py,
b_3_scene.py) and the passes' counts read from the build (`trig_count`).

The sequencer runs through the real route: Play (button 17), then the Main task's 1 ms service (`heartbeat`). Pattern
settings are written raw (stock's getters read them at every pattern change) plus the playing pattern's settings store;
chains through the chain store (write + commit) or the Patterns view; scenes through the Mixer view.

Logs (Python code hooks, which run before the instruction at their address, so before any slim stub there):
- `adv`: the track advance 0x0802CD42 (hook point track_advance) with fp == 0 where a pattern ends or a scene changes,
  (ticks, track, pattern that ended, end, scene, hand): stock's pass events (B-counting.md section 1).
- `t0`: each step's tick 0 (0x0804A6B8, once per step, before every microstep), (ticks, track, pattern, step, count):
  `count` = trig_count[track][pattern] as that step sees it.
- `order`: ("adv", track) / ("t0", track) in the global event order.
- `steps[t]`: track t's steps in tick-0 order since `clear_logs` ((pattern, step) each): a note-on is credited to the
  step whose tick 0 came last on its track (`sounded`).
- `trace`: (ms, ticks, kind, track, a, b, c) of the players' note events (Task 5): note players' `n_on` / `n_off`
  (stock's player note-on / off, r1-r3), the drum players' `d_on`, `d_prev_off`, `d_slot1_off`, `d_sample`
  (B-counting.md 5, b_5_prob.py), plus the endpoints' synth / MIDI events when the run goes through `run_ms`.
- `rand`: None, or f(track, step index since clear_logs, step) -> 0-7 / None: the low 3 bits of the step's random word
  (stored at 0x0804A6BC), so a test chooses each probability roll.

The probability view (Task 6; C-controls.md Q1, the 2026-11-07 spike's Q4): `open_prob(t)` (Shift + Pattern Settings),
`selected(t)` (the step stock shows and row 3 edits), `follow(on)` (Shift + Patterns toggles 0x20039DE0 p0: 0 = the
editors follow the playhead), `row4(i, ms, shift)` (a row-4 pad held `ms` heartbeats), `watch_writes()` (a write log
over every pattern and every editor store).

FILL (Task 7; C-controls.md Q2, Q3): `open_wide(d)` (Drum d, then Note again: the drum expanded view, mode 6),
`fill(d, ms)` (pad FILL_PAD + d held `ms` heartbeats), `fill_leds()` (pads 20-23), `fill_state()` (the FILL bytes in
ITCM), `heard(t)` (each tick 0 of track t: its ticks, step and whether it sounded), `pass_starts(t)`, `until_pass(t)`.

Stock's copies, clears and Mutate (Task 8; A-storage.md "Real routes found"): `step_view(t)`, `duplicate_pattern(src,
dst)` and `clear_pattern_pv(t, p)` (the Patterns view), `clear_step(pad)`, `copy_half()`, `paste_step(a, b, half,
track)`, `mutate()` (the step view), `prob_press(t, p, s)` (stopped: pattern p shown, then a row-3 press on step s)."""
from __future__ import annotations

import struct

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R4, \
    UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R11, UC_ARM_REG_SP

import trig_model
from drums import EDITOR_LOAD, ENGINE, PLAY, DrumHarness, sym
from harness import BTN_PRESS, BTN_RELEASE, MGR
from notes import PARAM_COMMIT, PARAM_WPTR, PATTERN, PATTERN_BASE, STEP, set_tempo

E = ENGINE
TRACK_ADVANCE = 0x0802CD42         # hook point track_advance: "the pattern ends or a scene changes"
TICK0 = 0x0804A6B8                 # the players' tick 0 of a step (`bl` to the random draw): logging only
NOTE_PLAYERS = [0x20040200 + 0x184 * t for t in range(4)]
DRUM_PLAYERS = [0x20040810 + 0x90 * d for d in range(4)]
PLAYERS = NOTE_PLAYERS + DRUM_PLAYERS           # index = engine track 0-7 (Synth 1, Synth 2, MIDI 1, MIDI 2, Drum 1-4)
DRUM_PAT = 0x6A8
DREC = 0x2003C184                  # [DREC + 4 d]: drum d's recorder; [+ 0x48] its patterns
PATTERNS_VIEW, MIXER = 13, 14      # buttons: Patterns view (pad = 8 x pattern + track, patterns 0-3), Mixer (scene pads 16-31)
READ_DONE, SESSION = 0x0802FD5C, 0x2003D71C     # stock's load: the read-done handler (as tests/test_saved.py)
TRACKS = 8
RAND_STORE = 0x0804A6BC            # `str r0, [r7, #4]`: the step's random word (drawn at tick 0) is stored
SEQ_NOTE_ON, SEQ_NOTE_OFF = 0x08040FA2, 0x0804104A               # a note player's note-on / off (r0 = the player)
D_NOTE_ON, D_PREV_OFF, D_SLOT1_OFF, D_SAMPLE = 0x08041298, 0x08041286, 0x080411C2, 0x08041240   # b_5_prob.py
DRUM_EVENTS = {D_NOTE_ON: "d_on", D_PREV_OFF: "d_prev_off", D_SLOT1_OFF: "d_slot1_off", D_SAMPLE: "d_sample"}
TIE = 0x80
CONT = 0x20040DB8                  # the track container: [+ 0x18C] the mode (5 = probability), [+ 0x190] the pads it holds
CONT_NOTE_PROB, CONT_DRUM_PROB = 0x68, 0xE0     # + 4 t / + 4 d: the probability views (the bottom view in mode 5)
PSET, BTN_NOTE, RECORD = 12, 9, 16  # buttons: Pattern Settings (with Shift: the probability view), Note, Record
MODE_PROB = 5
PROB_NOTE_VT, PROB_DRUM_VT = 0x0805ACD4, 0x0805AB14   # the probability views' classes
FOLLOW = 0x20039DE0                # p0 0: the editors follow the playhead while playing; 1: the selection stays
ROW3, ROW4 = 16, 24                # the controller's pads of row 3 (probability bar) and row 4
MODE_WIDE = 6                      # [CONT + 0x18C] on a drum: the expanded view (one object for all four drums)
FILL_PAD = 20                      # the expanded view's pads 20-23 (spec 21-24): FILL for drums 1-4
HALF, CLEAR, DUPLICATE = 21, 23, 24  # buttons: 1-16/17-32, Clear, Duplicate (with Shift: Mutate)
PATTERNS_VT = 0x0805A5F0           # the Patterns view's class


class TrigHarness(DrumHarness):
    def __init__(self, image: bytes, manifest: dict):
        super().__init__(image, manifest)
        self.count_at = sym(manifest, "trig_count") if "trig_count" in manifest["symbols"] else None   # PL19: none
        self.adv: list[tuple] = []
        self.t0: list[tuple] = []
        self.order: list[tuple] = []
        self.steps: list[list[tuple]] = [[] for _ in range(TRACKS)]
        self.trace: list[tuple] = []
        self.hits: list[tuple[int, int]] = []           # (track, step index into steps[track]) of each n_on / d_on
        self.rand = None
        uc = self.uc

        def advance(u, a, s, d):
            if u.reg_read(UC_ARM_REG_R11):
                return                                          # the look-ahead's call
            sp = u.reg_read(UC_ARM_REG_SP)
            end, scene = u.reg_read(UC_ARM_REG_R4) & 0xFF, self.r8(sp + 0x44)
            if not (end or scene):
                return
            t = self.r32(sp + 0xC)
            self.adv.append((self.ticks, t, u.reg_read(UC_ARM_REG_R9) & 0xFF, end, scene, self.r8(sp + 0x18)))
            self.order.append(("adv", t))
        uc.hook_add(UC_HOOK_CODE, advance, begin=TRACK_ADVANCE, end=TRACK_ADVANCE)

        def tick0(u, a, s, d):
            p = u.reg_read(UC_ARM_REG_R7)
            if p not in PLAYERS:
                return
            t, pat, step = PLAYERS.index(p), u.reg_read(UC_ARM_REG_R9) & 0xFF, u.reg_read(UC_ARM_REG_R8) & 0xFF
            self.t0.append((self.ticks, t, pat, step, self.count(t, pat)))
            self.order.append(("t0", t))
            self.steps[t].append((pat, step))
        uc.hook_add(UC_HOOK_CODE, tick0, begin=TICK0, end=TICK0)

        def rand(u, a, s, d):
            p = u.reg_read(UC_ARM_REG_R7)
            if self.rand is None or p not in PLAYERS:
                return
            t = PLAYERS.index(p)
            low = self.rand(t, len(self.steps[t]) - 1, u.reg_read(UC_ARM_REG_R8) & 0xFF)
            if low is not None:
                u.reg_write(UC_ARM_REG_R0, u.reg_read(UC_ARM_REG_R0) & ~7 | low)
        uc.hook_add(UC_HOOK_CODE, rand, begin=RAND_STORE, end=RAND_STORE)

        def note_ev(kind):
            def f(u, a, s, d):
                r = [u.reg_read(UC_ARM_REG_R0 + i) for i in range(4)]
                if r[0] in NOTE_PLAYERS:
                    t = NOTE_PLAYERS.index(r[0])
                    self.trace.append((self.ms, self.ticks, kind, t, *r[1:4]))
                    if kind == "n_on":
                        self.hits.append((t, len(self.steps[t]) - 1))
            return f
        uc.hook_add(UC_HOOK_CODE, note_ev("n_on"), begin=SEQ_NOTE_ON, end=SEQ_NOTE_ON)
        uc.hook_add(UC_HOOK_CODE, note_ev("n_off"), begin=SEQ_NOTE_OFF, end=SEQ_NOTE_OFF)

        def drum_ev(u, a, s, d):
            # slot 2's note-on and its previous hit's off: r4 = player + 0x58; slot 1's off: r4 = player + 0x4C;
            # the flip sample: r1 = the drum's own byte [[player + 0x54] + 8]
            r1, r2, r4 = u.reg_read(UC_ARM_REG_R1), u.reg_read(UC_ARM_REG_R2), u.reg_read(UC_ARM_REG_R4)
            if a == D_SAMPLE:
                ds = [d_ for d_ in range(4) if r1 == self.r8(self.r32(DRUM_PLAYERS[d_] + 0x54) + 8)]
                p = DRUM_PLAYERS[ds[0]] if len(ds) == 1 else None
            else:
                p = r4 - (0x4C if a == D_SLOT1_OFF else 0x58)
            if p in DRUM_PLAYERS:
                kind = DRUM_EVENTS[a]
                t = 4 + DRUM_PLAYERS.index(p)
                self.trace.append((self.ms, self.ticks, kind, t, r1, r2, None))
                if kind == "d_on":
                    self.hits.append((t, len(self.steps[t]) - 1))
        for a in DRUM_EVENTS:
            uc.hook_add(UC_HOOK_CODE, drum_ev, begin=a, end=a)

    # ---- the counts -------------------------------------------------------------------------------------------
    def count(self, t: int, p: int) -> int | None:
        if self.count_at is None:
            return None
        return struct.unpack("<H", bytes(self.uc.mem_read(self.count_at + 2 * (8 * t + p), 2)))[0]

    def counts(self) -> list[list[int]]:
        return [[self.count(t, p) for p in range(8)] for t in range(TRACKS)]

    def set_count(self, t: int, p: int, v: int) -> None:
        self.uc.mem_write(self.count_at + 2 * (8 * t + p), struct.pack("<H", v))

    def clear_logs(self) -> None:
        for log in (self.adv, self.t0, self.order, self.trace, self.hits, *self.steps):
            log.clear()

    def run_ms(self, n: int) -> None:
        """n heartbeats, one at a time; the endpoints' events of each go into `trace` with that heartbeat's ms."""
        for _ in range(n):
            ms = self.ms
            self.heartbeat(1)
            self.trace += [(ms, self.ticks, e[0], *e[1:]) for e in self.take()]

    def sounded(self, t: int) -> list[int]:
        """The step indices (into steps[t]) of track t's note-ons (n_on / d_on), in order."""
        return [i for tr, i in self.hits if tr == t]

    def passes_sounded(self, t: int, step: int, length: int) -> list[int]:
        """The passes (0-based) of a `length`-step loop on which track t's `step` sounded."""
        return sorted({i // length for i in self.sounded(t) if self.steps[t][i][1] == step})

    def segments(self, t: int) -> list[list[tuple]]:
        """Track t's tick-0 entries split at its pass events: one list per pass (the last one still running)."""
        segs, cur = [], []
        it = iter([x for x in self.t0 if x[1] == t])
        for tag, tr in self.order:
            if tr != t:
                continue
            if tag == "adv":
                segs.append(cur)
                cur = []
            else:
                cur.append(next(it))
        segs.append(cur)
        return segs

    # ---- stores -----------------------------------------------------------------------------------------------
    def store_ptr(self, st: int, i: int) -> int:
        """Stock's parameter getter 0x0803542C in Python (safe inside a code hook)."""
        b = self.r32(st + 4) >> i & 1
        return self.r32(st + 0xC + 4 * b) + 4 * i

    def param_bytes(self, st: int, i: int, n: int = 4) -> bytes:
        return bytes(self.uc.mem_read(self.store_ptr(st, i), n))

    def param_set(self, st: int, i: int, data: bytes) -> None:
        """Parameter i through the store's write pointer and commit, as stock's own writers."""
        self.call(PARAM_WPTR, st, i)
        self.uc.mem_write(self.uc.reg_read(UC_ARM_REG_R0), data)
        self.call(PARAM_COMMIT, st)

    def playing(self, t: int) -> tuple[int, int]:
        """Track t's playing (pattern, step)."""
        st = self.r32(E + 0x30 + 4 * t)
        return self.param_bytes(st, 0, 1)[0], self.param_bytes(st, 1, 1)[0]

    def track_chain(self, t: int) -> tuple[int, int]:
        b = self.param_bytes(self.r32(E + 0x9C), t, 2)
        return b[0], b[1]

    def set_chain_raw(self, t: int, first: int, last: int) -> None:
        st = self.r32(E + 0x9C)
        self.param_set(st, t, bytes([first, last]) + self.param_bytes(st, t)[2:])

    def hand_flag(self, t: int) -> int:
        """The chain store's parameter 8 + t: a pattern / chain picked by hand, waiting for the pattern end."""
        return self.param_bytes(self.r32(E + 0x9C), 8 + t, 1)[0]

    def scene_wait(self) -> int:
        """The scene chain's parameter 1: a scene picked by hand, waiting."""
        return self.param_bytes(self.r32(E + 0xA0), 1, 1)[0]

    def scene(self) -> int:
        return self.param_bytes(self.r32(E + 0x2C), 0, 1)[0]

    # ---- patterns ---------------------------------------------------------------------------------------------
    def drum_base(self, d: int) -> int:
        return self.r32(self.r32(DREC + 4 * d) + 0x48)

    def settings_addr(self, t: int, p: int) -> int:
        if t < 4:
            return PATTERN_BASE[t] + p * PATTERN + 0x380
        return self.drum_base(t - 4) + p * DRUM_PAT + 0x80

    def settings(self, t: int, p: int) -> tuple[int, int, int, int]:
        """(last, first, rate, direction) of pattern p of track t."""
        return tuple(self.uc.mem_read(self.settings_addr(t, p), 4))

    def note_step_at(self, t: int, p: int, s: int) -> int:
        return PATTERN_BASE[t] + p * PATTERN + s * STEP

    def set_code(self, t: int, p: int, s: int, code: int) -> None:
        """Raw: step s of track t's pattern p gets the condition `code`, in trig_model's byte layout."""
        if t < 4:
            a = self.note_step_at(t, p, s)
            b = bytearray(self.uc.mem_read(a, 4))
            trig_model.trig_note_set(b, code)
            self.uc.mem_write(a, bytes(b))
        else:
            a = self.drum_base(t - 4) + p * DRUM_PAT
            b = bytearray(self.uc.mem_read(a, 0xA8))
            trig_model.trig_drum_set(b, s, code)
            self.uc.mem_write(a + 0x84, bytes(b[0x84:0xA8]))

    def code(self, t: int, p: int, s: int) -> int:
        if t < 4:
            return trig_model.trig_note_get(bytes(self.uc.mem_read(self.note_step_at(t, p, s), 4)))
        return trig_model.trig_drum_get(bytes(self.uc.mem_read(self.drum_base(t - 4) + p * DRUM_PAT, 0xA8)), s)

    def mark(self, on: int) -> None:
        """trig_mark (1 = the project's condition bytes are CTPlay's), raw."""
        self.uc.mem_write(sym(self.m, "trig_mark"), bytes([on]))

    def clear_steps(self) -> None:
        """Raw: every step of every track's 8 patterns empty, condition bytes 0 (settings kept); each drum's editor
        loaded again (its step store in line)."""
        for t in range(4):
            for p in range(8):
                self.uc.mem_write(PATTERN_BASE[t] + p * PATTERN, bytes(32 * STEP))
        for d in range(4):
            for p in range(8):
                b = self.drum_base(d) + p * DRUM_PAT
                self.uc.mem_write(b, bytes(32) + bytes([7] * 32) + bytes([0xFF] * 32) + bytes(32))
                self.uc.mem_write(b + 0x84, bytes(0x24))
        self.load_editors()

    def load_editors(self) -> None:
        """Each drum's editor loaded again: its step store in line with the shown pattern (as a pattern change)."""
        for d in range(4):
            self.call(EDITOR_LOAD, self.editor(d))

    def note(self, t: int, p: int, s: int, units, prob: int = 7, code: int = 0) -> None:
        """Raw note units (note, gate | TIE, microstep, velocity) on step s of note track t's pattern p."""
        body = b"".join(bytes(u) for u in units).ljust(24, b"\0")
        self.uc.mem_write(self.note_step_at(t, p, s), bytes([(1 << len(units)) - 1, prob, 0, 0]) + body)
        self.set_code(t, p, s, code)

    def hit(self, t: int, p: int, s: int, vel: int = 100, prob: int = 7, flip: int = 0xFF, micro: int = 1,
            code: int = 0) -> None:
        """A hit on step s of track t's pattern p: a drum's (t 4-7) raw, on a note track one note (60, one step)."""
        if t < 4:
            self.note(t, p, s, [(60, 6, 0, vel)], prob, code)
            return
        b = self.drum_base(t - 4) + p * DRUM_PAT
        for off, v in ((0, vel), (0x20, prob), (0x40, flip), (0x60, micro)):
            self.uc.mem_write(b + off + s, bytes([v]))
        self.set_code(t, p, s, code)

    def mute(self, t: int, on: bool) -> None:
        """The player's mute store [player + 0x28] p0, through write + commit (b_lib.configure)."""
        st = self.r32(PLAYERS[t] + 0x28)
        self.param_set(st, 0, bytes([int(on)]) + self.param_bytes(st, 0)[1:])

    def configure(self, cfg: dict) -> None:
        """cfg: {track: dict(chain=(first, last), pats={p: (last, first, rate, direction)}, mute=bool)}. Raw pattern
        settings, the playing pattern's settings store [E + 0x50 + 4 t], the chain store and the mute store
        [player + 0x28] through write + commit (b_lib.configure)."""
        for t, c in cfg.items():
            for p, s in c.get("pats", {}).items():
                self.uc.mem_write(self.settings_addr(t, p), bytes(s))
            if "chain" in c:
                self.set_chain_raw(t, *c["chain"])
            if c.get("mute"):
                st = self.r32(PLAYERS[t] + 0x28)
                self.param_set(st, 0, bytes([1]) + self.param_bytes(st, 0)[1:])
            last, first, rate, d = self.settings(t, self.playing(t)[0])
            st = self.r32(E + 0x50 + 4 * t)
            self.param_set(st, 0, bytes([last, first]) + self.param_bytes(st, 0)[2:])
            self.param_set(st, 1, bytes([rate]) + self.param_bytes(st, 1)[1:])
            self.param_set(st, 2, bytes([d]) + self.param_bytes(st, 2)[1:])

    # ---- the probability view (Task 6) ------------------------------------------------------------------------
    def open_prob(self, t: int) -> None:
        """Track t's button, then Shift + Pattern Settings: its probability view (mode 5)."""
        self.press(t)
        self.press(PSET, shift=True)
        assert self.view_mode() == MODE_PROB and self.r32(self.prob_view(t)) == (PROB_NOTE_VT if t < 4 else PROB_DRUM_VT)

    def prob_view(self, t: int) -> int:
        return self.r32(CONT + (CONT_NOTE_PROB + 4 * t if t < 4 else CONT_DRUM_PROB + 4 * (t - 4)))

    def note_editor(self, t: int) -> int:
        return self.r32(self.prob_view(t) + 0xC) - 0x18

    def edit_store(self, t: int) -> int:
        """Note track t's edit store: word 0 = the selected step's bytes 0-3."""
        return self.r32(self.note_editor(t) + 0x20)

    def selected(self, t: int) -> tuple[int, int]:
        """(pattern, step) the probability view shows and row 3 edits: notes the editor's position store [editor +
        0x24] p0 & 7 / p1; drums the recorder's [+ 0x14] p0 & 7 and [[view + 0xC] + 8] p1."""
        if t < 4:
            pos = self.r32(self.note_editor(t) + 0x24)
            return self.param_bytes(pos, 0, 1)[0] & 7, self.param_bytes(pos, 1, 1)[0]
        p = self.param_bytes(self.r32(self.recorder(t - 4) + 0x14), 0, 1)[0] & 7
        return p, self.param_bytes(self.r32(self.r32(self.prob_view(t) + 0xC) + 8), 1, 1)[0]

    def following(self) -> bool:
        return self.param_bytes(FOLLOW, 0, 1)[0] == 0

    def follow(self, on: bool) -> None:
        """Shift + Patterns (the only button that toggles 0x20039DE0) until the editors follow (on) or not."""
        if self.following() != on:
            self.press(PATTERNS_VIEW, shift=True)
        assert self.following() == on

    def row4(self, i: int, ms: int = 0, shift: bool = False) -> None:
        """Row-4 pad i (0-7) pressed, `ms` heartbeats, released; Shift held from before the press to after the release."""
        if shift:
            self.shift(True)
        self.down(ROW4 + i)
        self.heartbeat(ms)
        self.up(ROW4 + i)
        if shift:
            self.shift(False)

    def row4_leds(self) -> list[int]:
        return self.leds()[ROW4:ROW4 + 8]

    def step_word(self, t: int, p: int, s: int) -> bytes:
        """Note step bytes 0-3: unit mask, probability, the condition's two bytes."""
        return bytes(self.uc.mem_read(self.note_step_at(t, p, s), 4))

    def store_regions(self) -> list[tuple[int, int]]:
        """Every pattern of every track, each note editor's edit store and each drum's step store (header and both
        buffers)."""
        r = [(PATTERN_BASE[t], 8 * PATTERN) for t in range(4)] + [(self.drum_base(d), 8 * DRUM_PAT) for d in range(4)]
        for st, n in [(self.edit_store(t), 7 * 4) for t in range(4)] + \
                [(self.r32(self.recorder(d) + 0x4C), 32 * 4) for d in range(4)]:
            r += [(st, 0x14), (self.r32(st + 0xC), n), (self.r32(st + 0x10), n)]
        return r

    def watch_writes(self) -> tuple[list, list]:
        """A write log (address, size, value) over store_regions(); returns (log, hook handles)."""
        log: list[tuple] = []

        def w(u, acc, addr, size, val, d):
            log.append((addr, size, val))
        return log, [self.uc.hook_add(UC_HOOK_MEM_WRITE, w, begin=a, end=a + n - 1) for a, n in self.store_regions()]

    def unwatch(self, hooks: list) -> None:
        for k in hooks:
            self.uc.hook_del(k)

    # ---- FILL (Task 7) ----------------------------------------------------------------------------------------
    def open_wide(self, d: int) -> None:
        """Drum d's button (track 4 + d), then Note until the expanded view (mode 6) is shown."""
        self.press(4 + d)
        for _ in range(3):
            if self.view_mode() == MODE_WIDE:
                break
            self.press(BTN_NOTE)
        assert self.view_mode() == MODE_WIDE and self.r32(MGR + 0x6C) == CONT

    def fill(self, d: int, ms: int) -> None:
        """FILL pad of drum d held `ms` heartbeats (the 1 ms service), then released."""
        self.down(FILL_PAD + d)
        self.heartbeat(ms)
        self.up(FILL_PAD + d)

    def fill_leds(self) -> list[int]:
        return self.leds()[FILL_PAD:FILL_PAD + 4]

    def fill_state(self) -> dict:
        """The FILL bytes: hold and pass (bit per drum), arm, started, done (per drum)."""
        def b(name, n=1):
            return list(self.uc.mem_read(sym(self.m, name), n))
        return dict(hold=b("trig_fill_hold")[0], pass_=b("trig_fill_pass")[0], arm=b("trig_fill_arm", 4),
                    started=b("trig_fill_started", 4), done=b("trig_fill_done", 4))

    def heard(self, t: int) -> list[tuple[int, int, bool]]:
        """(ticks, step, sounded) of each tick 0 of track t since clear_logs."""
        hit = {i for tr, i in self.hits if tr == t}
        return [(x[0], x[3], i in hit) for i, x in enumerate(x for x in self.t0 if x[1] == t)]

    def pass_starts(self, t: int) -> list[int]:
        """The ticks of track t's pass events since clear_logs (a pass runs from one to the next: its first step's
        tick 0 has the same ticks)."""
        return [x[0] for x in self.adv if x[1] == t]

    def until_pass(self, t: int, cap: int = 10_000) -> int:
        """Heartbeats until track t's next pass event; returns its ticks."""
        n = len(self.pass_starts(t))
        for _ in range(cap):
            if len(self.pass_starts(t)) > n:
                return self.pass_starts(t)[n]
            self.heartbeat(1)
        raise AssertionError("no pass end")

    # ---- stock's copies, clears and Mutate (Task 8; A-storage.md "Real routes found") --------------------------
    def btn_down(self, b: int) -> None:
        self.nbusy = 0
        self.call(BTN_PRESS, MGR, b)

    def btn_up(self, b: int) -> None:
        self.nbusy = 0
        self.call(BTN_RELEASE, MGR, b)

    def step_view(self, t: int) -> None:
        """Track t's button, then Note until the step view (mode 1: steps on the top two rows)."""
        self.press(t)
        for _ in range(4):
            if self.view_mode() == 1:
                break
            self.press(BTN_NOTE)
        assert self.view_mode() == 1, self.view_mode()

    def patterns_view(self) -> None:
        self.press(PATTERNS_VIEW)
        assert self.r32(self.r32(MGR + 0x6C)) == PATTERNS_VT

    def duplicate_pattern(self, src: tuple[int, int], dst: tuple[int, int]) -> None:
        """The Patterns view: Duplicate held, the source pad (track, pattern 0-3), the target pad, Duplicate let go."""
        self.patterns_view()
        self.btn_down(DUPLICATE)
        self.pick(*src)
        self.pick(*dst)
        self.btn_up(DUPLICATE)

    def clear_pattern_pv(self, t: int, p: int) -> None:
        """The Patterns view: Clear held + track t's pattern p (0-3)."""
        self.patterns_view()
        self.btn_down(CLEAR)
        self.pick(t, p)
        self.btn_up(CLEAR)

    def clear_step(self, pad: int) -> None:
        """The step view (open): Clear held + a step pad (0-15 of the page shown)."""
        self.btn_down(CLEAR)
        self.pad(pad)
        self.btn_up(CLEAR)

    def copy_half(self) -> None:
        """The step view (open): Duplicate held + 1-16/17-32 (stock copies steps 1-16 to 17-32)."""
        self.btn_down(DUPLICATE)
        self.press(HALF)
        self.btn_up(DUPLICATE)

    def paste_step(self, a: int, b: int, half: bool = False, track: int | None = None) -> None:
        """The step view (open): Duplicate held, step pad a, then (the page switched, another track's button) step pad
        b, Duplicate let go."""
        self.btn_down(DUPLICATE)
        self.pad(a)
        if half:
            self.press(HALF)
        if track is not None:
            self.press(track)
        self.pad(b)
        self.btn_up(DUPLICATE)

    def mutate(self) -> None:
        """Shift + Duplicate (the step view open)."""
        self.press(DUPLICATE, shift=True)

    def prob_press(self, t: int, p: int, s: int, prob: int = 2) -> None:
        """Stopped: the Patterns view's pick of track t's pattern p (0-3: the shown one), then the probability view's
        step pad s (0-15) and row-3 pad `prob`: stock's own edit of that step (it makes a hit on an empty drum step)."""
        self.patterns_view()
        self.pick(t, p)
        self.open_prob(t)
        self.pad(s)
        self.pad(ROW3 + prob)

    # ---- routes -----------------------------------------------------------------------------------------------
    def play(self) -> None:
        """Play / Stop (button 17)."""
        self.press(PLAY)

    def resume(self) -> None:
        """Shift + Play from stop: continue (no seq_start)."""
        self.press(PLAY, shift=True)

    def run_ticks(self, n: int, cap: int = 200_000) -> None:
        """Heartbeats until n more sequencer ticks have run."""
        goal = self.ticks + n
        for _ in range(cap):
            if self.ticks >= goal:
                return
            self.heartbeat(1)
        raise AssertionError("the sequencer did not tick")

    def pick(self, t: int, p: int, shift: bool = False) -> None:
        """The Patterns view (open) tap: track t's pattern p (0-3); with Shift it switches at once."""
        assert p < 4
        if shift:
            self.shift(True)
        self.pad(8 * p + t)
        if shift:
            self.shift(False)

    def pick_chain(self, t: int, first: int, last: int) -> None:
        """The Patterns view (open): hold the first pattern, press the last."""
        self.down(8 * first + t)
        if last != first:
            self.down(8 * last + t)
            self.up(8 * last + t)
        self.up(8 * first + t)

    def save_scene(self, scene: int, chains: list[tuple[int, int]]) -> None:
        """Stopped: every track's chain in the Patterns view, then Mixer, Shift + the scene pad (b_3_scene.save_scene)."""
        self.press(PATTERNS_VIEW)
        for t, (f, l) in enumerate(chains):
            self.pick_chain(t, f, l)
        assert [self.track_chain(t) for t in range(TRACKS)] == list(chains)
        self.press(MIXER)
        self.shift(True)
        self.pad(16 + scene)
        self.shift(False)

    def pick_scene(self, scene: int) -> None:
        """The Mixer view (open): a scene pad."""
        self.pad(16 + scene)

    def scene_chain(self, first: int, last: int) -> None:
        """The Mixer view (open): hold the first scene pad, press the last."""
        self.down(16 + first)
        self.down(16 + last)
        self.up(16 + last)
        self.up(16 + first)

    def load(self) -> None:
        """Stock's load from the file's read-done handler (the record already holds the file), as test_saved.py."""
        self.call(READ_DONE, SESSION, maxins=20_000_000)


def trig_setup(h: TrigHarness, cfg: dict | None = None, length: int = 8) -> None:
    """slim ready, 240 BPM, no swing; every track `length`-step loops of pattern 0 (patterns 0-7 alike) unless cfg."""
    h.leds()
    set_tempo(h, bpm=240, swing=50)
    h.configure(cfg or loops(length))


def loops(lengths, rate: int = 3) -> dict:
    """Every track a loop of pattern 0; patterns 0-7 of track t `lengths[t]` steps (an int: all alike), 1/16, forward."""
    if isinstance(lengths, int):
        lengths = [lengths] * TRACKS
    return {t: dict(chain=(0, 0), pats={p: (lengths[t] - 1, 0, rate, 0) for p in range(8)}) for t in range(TRACKS)}


def expected_pass(last: int, first: int, direction: int) -> list[int] | None:
    """The steps of one pass, forward and reverse (b_lib.expected_pass); ping-pong / random: None."""
    n = (last - first) % 32 + 1
    fwd = [(first + i) % 32 for i in range(n)]
    return fwd if direction == 0 else fwd[::-1] if direction == 1 else None
