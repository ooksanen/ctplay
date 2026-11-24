"""Note-level emulation for the chord tests.

The stock note endpoints are logged and stubbed (no DSP traffic): the synth note on / off (0x0803BD58 / 0x0803BD94,
which take the DSP lock) and the MIDI-out note on / off (0x08029EFE / 0x08029F2A). Unlike the base harness, the
router's sound / MIDI path (0x08031DA4) and the recorder gates run for real. `sounding` is the set of notes that are on
at the endpoints: ("synth", synth, note) and ("midi", track, note)."""
from __future__ import annotations

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3

from harness import MGR, PAD_PRESS, PAD_RELEASE, Harness

SYNTH_ON, SYNTH_OFF = 0x0803BD58, 0x0803BD94
MIDI_ON, MIDI_OFF = 0x08029EFE, 0x08029F2A
REC_ON, REC_OFF = 0x0802E56A, 0x0802E5CC
PAD_NOTE_ON, PAD_NOTE_OFF = 0x0804AEF2, 0x0804AF5A
PAD_INDEX = 0x0804B174
CONT = 0x20040DB8                  # track-view container
NOTE_DEFAULT, NOTE_EXPANDED = 1, 6 # [CONT + 0x18C]
BTN_NOTE = 9
SCALE_MASK, ROOT = 0x2003FA90, 0x2003FA94
OUTBUF = 0x2006D000                # scratch for direct calls (mapped by the base emulator, unused by the snapshot)
ENDPOINTS = {SYNTH_ON: "synth_on", SYNTH_OFF: "synth_off", MIDI_ON: "midi_on", MIDI_OFF: "midi_off"}
WATCHED = {REC_ON: "rec_on", REC_OFF: "rec_off", PAD_NOTE_ON: "pad_on", PAD_NOTE_OFF: "pad_off"}


class NoteHarness(Harness):
    STUB_SYNTH = True    # VoiceHarness lets the synth note-on / note-off run (tests/voices.py)

    def __init__(self, image: bytes):
        super().__init__(image)
        self.stubs.pop(0x08031DA4, None)
        self.marks.clear()
        self.log: list[tuple] = []
        self.sounding: set[tuple] = set()
        self.endpoints = {a: k for a, k in ENDPOINTS.items() if self.STUB_SYNTH or not k.startswith("synth")}

        def hook(uc, address, size, data):
            regs = tuple(uc.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
            if address in self.endpoints:
                kind = self.endpoints[address]
                self.log.append((kind, *regs))
                key = ("synth", regs[0], regs[1]) if kind.startswith("synth") else ("midi", regs[1], regs[2])
                if kind.endswith("_on"):
                    self.sounding.add(key)
                else:
                    self.sounding.discard(key)
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR) | 1)
            else:
                self.log.append((WATCHED[address], *regs))

        for a in (*self.endpoints, *WATCHED):
            self.uc.hook_add(UC_HOOK_CODE, hook, begin=a, end=a)

    def view_mode(self) -> int:
        return self.r8(CONT + 0x18C)

    def note_view(self, t: int) -> int:
        return self.r32(CONT + 0x18 + 4 * t)

    def track(self, t: int, mode: int = NOTE_DEFAULT) -> None:
        self.cur = t
        self.press(t)
        for _ in range(3):
            if self.view_mode() == mode:
                break
            self.press(BTN_NOTE)
        assert self.view_mode() == mode, f"track {t}: Note view mode {self.view_mode()}, wanted {mode}"

    def shift(self, on: bool) -> None:
        self.set_p0(self.r32(MGR + 0xC), 1 if on else 0)

    def down(self, pad: int, vel: int = 100) -> None:
        self.nbusy = 0
        self.call(PAD_PRESS, MGR, pad, vel)

    def up(self, pad: int) -> None:
        self.nbusy = 0
        self.call(PAD_RELEASE, MGR, pad)

    def pitch(self, t: int, pad: int) -> int:
        view = self.note_view(t)
        self.call(PAD_INDEX, view, pad)
        idx = self.uc.reg_read(UC_ARM_REG_R0)
        return self.r8(self.r32(view + 0x38) + 0x14 + idx)

    def take(self, *kinds: str) -> list[tuple]:
        out = [e for e in self.log if not kinds or e[0] in kinds]
        self.log.clear()
        return out


def endpoint_note(h: NoteHarness, pitch: int) -> int:
    """Keyboard pitch (root-relative, +12) -> the note at the synth / MIDI-out endpoints."""
    return pitch + h.r8(ROOT) - 12


TEMPO_STORE, PLAY_STORE = 0x20011404, 0x20011034
PARAM_GET, PARAM_WPTR, PARAM_COMMIT = 0x0803542C, 0x080354FA, 0x080353C0


def param(h, store: int, i: int) -> int:
    h.call(PARAM_GET, store, i)
    return h.r8(h.uc.reg_read(UC_ARM_REG_R0))


def set_tempo(h, bpm: int | None = None, swing: int | None = None) -> None:
    """Through the store's write and commit, as stock's Tempo view does: the clock takes the change at once."""
    for i, v in ((0, bpm), (2, swing)):
        if v is None:
            continue
        h.call(PARAM_WPTR, TEMPO_STORE, i)
        h.uc.mem_write(h.uc.reg_read(UC_ARM_REG_R0), v.to_bytes(4, "little"))
        h.call(PARAM_COMMIT, TEMPO_STORE)


def ms_log(h, n: int, kinds=("synth_on", "synth_off")) -> list[tuple]:
    """n heartbeats; (ms 1-based, kind, note) of every endpoint event of `kinds`."""
    out = []
    for t in range(1, n + 1):
        h.heartbeat(1)
        out += [(t, e[0], e[2] if e[0].startswith("synth") else e[3]) for e in h.take(*kinds)]
    return out


PATTERN_BASE = (0x20011B20, 0x20018060, 0x2002BAB8, 0x20031FF8)   # each note track's 8 patterns (upstream NOTAS)
PATTERN, STEP = 0xCA8, 28
RECORDERS = 0x2003C168 + 0xC                                       # [RECORDERS + 4 t]: track t's recorder


def pattern_snapshot(h, t: int) -> bytes:
    return bytes(h.uc.mem_read(PATTERN_BASE[t], 8 * PATTERN))


def recorded_notes(h, t: int, before: bytes) -> list[tuple[int, int, int, int, int]]:
    """(pattern, step, note, length in ticks, microstep) of every note unit of track t that changed since `before`, in
    pattern / step order. A step: byte 0 = mask of its 6 units, units of 4 B from + 4 (note, length | tie << 7,
    microstep, velocity)."""
    now, out = pattern_snapshot(h, t), []
    for p in range(8):
        for s in range(32):
            o = p * PATTERN + s * STEP
            for u in range(6):
                a = o + 4 + 4 * u
                if now[o] >> u & 1 and (now[a:a + 4] != before[a:a + 4] or not before[o] >> u & 1):
                    out.append((p, s, now[a], now[a + 1] & 0x7F, now[a + 2]))
    return out


def recorder_held(h, t: int) -> list[int]:
    """The notes track t's recorder still takes as held: its list at + 0x54, 6 entries of 12 B (the loop at 0x0803F6D6:
    `movs r5, #6`, `sb += 0xC`); byte 0 = note (0 = empty, the commit at 0x0803F77E clears it), bit 0 of byte 3 =
    released."""
    base = h.r32(RECORDERS + 4 * t) + 0x54
    out = []
    for i in range(6):
        e = bytes(h.uc.mem_read(base + 12 * i, 4))
        if e[0] and not e[3] & 1:
            out.append(e[0])
    return out



def step_addr(t, p, s):
    return PATTERN_BASE[t] + p * PATTERN + s * STEP


def units(h, t, p, s):
    """The notes of the step's units (mask bits set), sorted."""
    a = step_addr(t, p, s)
    mask = h.r8(a)
    return sorted(h.r8(a + 4 + 4 * u) for u in range(6) if mask >> u & 1)


def step_units(h, t, p, s) -> list[tuple[int, int, int, int]]:
    """(note, gate | tie << 7, microstep, velocity) of each used unit of the step, in unit order."""
    a = step_addr(t, p, s)
    mask = h.r8(a)
    return [tuple(h.uc.mem_read(a + 4 + 4 * u, 4)) for u in range(6) if mask >> u & 1]


def fill(h, t, p, s, notes):
    """Raw notes on a step (as if recorded earlier): units (note, length 6, microstep 0, velocity 100)."""
    body = b"".join(bytes([n, 6, 0, 100]) for n in notes) + bytes(4 * (6 - len(notes)))
    h.uc.mem_write(step_addr(t, p, s), bytes([(1 << len(notes)) - 1, 7, 0, 0]) + body)


def fixed_velocity(h, t: int, on: bool) -> None:
    """Stock's fixed velocity (96 for every pad): bit 1 of parameter 2 of the Note view's settings store
    [note_view(t) + 0x28], through the store's write and commit as set_tempo. The dump has it on."""
    store = h.r32(h.note_view(t) + 0x28)
    h.call(PARAM_GET, store, 2)
    v = h.r32(h.uc.reg_read(UC_ARM_REG_R0))
    h.call(PARAM_WPTR, store, 2)
    h.uc.mem_write(h.uc.reg_read(UC_ARM_REG_R0), ((v & ~2) | (2 if on else 0)).to_bytes(4, "little"))
    h.call(PARAM_COMMIT, store)
