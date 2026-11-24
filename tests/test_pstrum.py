"""Pattern strum, Played (PL19, spec 2026-10-28-playback-strum-design.md, "Played: playback"): with a track's pattern
strum on Played and its strum speed on, a pattern's plain chords strum as the sequencer plays them. Stock plays the
first note in strum order at its tick; the 1 ms heartbeat sends the others late through stock's player note-on
(features/chord/pstrum.c). Chords are written raw into the track's playing pattern, Play goes through the real button
and the ticks through the heartbeat (Main's 1 ms service)."""
import pytest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

from emu_sc05 import STOP
from harness import BUDGET, MS_SERVICE
from notes import (PARAM_COMMIT, PARAM_WPTR, PATTERN, PATTERN_BASE, PLAY_STORE, STEP, NoteHarness, param,
                   pattern_snapshot, set_tempo, step_addr)
from test_chord import set_down, set_strum
from test_page import DOWN, open_page, pick
from voices import VOICE_MODE, VoiceHarness

pytestmark = pytest.mark.emu
PLAY, MIXER, PATTERNS_VIEW = 17, 14, 13
PLAYED = 1
KEYS_PLAYED = 2                                  # the Keys page's pad 3 (0-based 2): pattern strum played
PLAYERS = tuple(0x20040200 + 0x184 * t for t in range(4))
ENGINE = 0x20038EC0                              # [ENGINE + 0x30 + 4 t]: track t's store, p0 bits 0-2 = its playing pattern
SET = 0x380                                      # pattern + 0x382: sync rate (3 = 1/16)
UNITS_START, NOTE_ON, END_ENTRY = 0x08040D4C, 0x08040FA2, 0x08041078
STOCK_NOTE_ON_RETURN = 0x08040F5E                # seq_play_step's own `bl seq_note_on` returns here
TRAP = 0x0807FFE0                                # erased flash past the image: a return address that stops emulation
NESTED_SP = 0x2006C000                           # a stack for a "UI task" call nested in a heartbeat, below the harness's
GAP = {1: 80, 2: 40, 3: 20}                      # chord.c STRUM_GAP: ms between strummed notes
TIE = 0x80
C, D, E, F, G, A, B = 48, 50, 51, 53, 55, 56, 58  # in the dump's scale, C minor (E = Eb, A = Ab, B = Bb): the router
                                                   # snaps a pattern's notes to the scale


def sym(m, name):
    return int(m["symbols"][name], 16)


class PH(NoteHarness):
    """NoteHarness with a clock: `ms` counts heartbeats (events during heartbeat k carry ms k; events of a UI action
    after it carry the same ms), `ticks` the ms of each of the track's ticks (seq_units_start of its player: one per
    tick at 1/16), `events` (ms, kind, channel, note, velocity) of every endpoint event (channel = the synth for
    synth_*, the track for midi_*)."""

    def __init__(self, image, track=0, cls=NoteHarness):
        cls.__init__(self, image)
        self.t = track
        self.ms = 0
        self.ticks = []
        self.events = []
        self.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: self.ticks.append(self.ms)
                         if u.reg_read(UC_ARM_REG_R0) == PLAYERS[self.t] else None, begin=UNITS_START, end=UNITS_START)

    def collect(self):
        for e in self.log:
            if e[0] in ("synth_on", "synth_off"):          # the voice harness logs (synth, note[, velocity])
                self.events.append((self.ms, e[0], e[1], e[2], e[3] if len(e) > 3 else None))
            elif e[0] in ("midi_on", "midi_off"):
                self.events.append((self.ms, e[0], e[2], e[3], e[4]))
        self.log.clear()

    def heartbeat(self, n=1):
        for _ in range(n):
            self.ms += 1
            NoteHarness.heartbeat(self, 1)
            self.collect()

    def press(self, *a, **k):
        NoteHarness.press(self, *a, **k)
        self.collect()

    def pad(self, *a, **k):
        NoteHarness.pad(self, *a, **k)
        self.collect()

    def down(self, *a, **k):
        NoteHarness.down(self, *a, **k)
        self.collect()

    def up(self, *a, **k):
        NoteHarness.up(self, *a, **k)
        self.collect()

    def ons(self, since=0, kind=None):
        """(ms, note, velocity) of the track's note-ons from ms `since`: synth tracks at their synth, MIDI tracks at
        the MIDI transmitter."""
        kind = kind or ("synth_on" if self.t < 2 else "midi_on")
        return [(ms, n, v) for ms, k, ch, n, v in self.events if k == kind and ch == self.t and ms >= since]

    def offs(self, since=0, kind=None):
        kind = kind or ("synth_off" if self.t < 2 else "midi_off")
        return [(ms, n) for ms, k, ch, n, v in self.events if k == kind and ch == self.t and ms >= since]

    def track_sounding(self):
        return {k for k in self.sounding if k[1] == self.t}


class VPH(PH, VoiceHarness):
    """PH over the voice-level harness: the synth note-on runs through stock's voice decision (tests/voices.py)."""

    def __init__(self, image, track=0):
        PH.__init__(self, image, track, cls=VoiceHarness)


def playing_pattern(h, t):
    return param(h, h.r32(ENGINE + 0x30 + 4 * t), 0) & 7


def put(h, s, units, prob=7):
    """Raw units (note, gate | tie, microstep, velocity) on step s of the track's playing pattern."""
    body = b"".join(bytes(u) for u in units) + bytes(4 * (6 - len(units)))
    h.uc.mem_write(step_addr(h.t, playing_pattern(h, h.t), s), bytes([(1 << len(units)) - 1, prob, 0, 0]) + body)


def set_pstrum(h, m, t, mode):
    h.call(sym(m, "slim_ready"))
    a = sym(m, "chord_pstrum")
    h.uc.mem_write(a, bytes([h.r8(a) & ~(3 << 2 * t) | mode << 2 * t]))


def setup(image, m, steps, track=0, speed=1, down=False, played=True, bpm=None, cls=PH):
    """Track `track` in its Note view; every note track's patterns emptied (the dump's own would play too), the
    track's playing pattern at 1/16 (32 steps) with `steps` ({step: units}) on it; its strum speed and
    direction, its pattern strum Played (PL19 images only; played=None leaves it). Synth 1 on a Poly patch."""
    h = cls(image, track)
    h.leds()                                         # slim's power-on init (test_page.ready)
    h.track(track)
    if bpm:
        set_tempo(h, bpm=bpm)
    for t in range(4):
        for p in range(8):
            h.uc.mem_write(PATTERN_BASE[t] + p * PATTERN, bytes(32 * STEP))
    h.uc.mem_write(PATTERN_BASE[track] + playing_pattern(h, track) * PATTERN + SET + 2, bytes([3]))
    for s, units in steps.items():
        put(h, s, units)
    set_strum(h, m, track, speed)
    set_down(h, m, track, down)
    if played is not None and "chord_pstrum" in m["symbols"]:
        set_pstrum(h, m, track, PLAYED if played else 0)
    h.uc.mem_write(VOICE_MODE[0], bytes([2]))
    h.take()
    h.events.clear()
    return h


def endpoint(units, got):
    """The endpoint transposes the pattern's notes (the dump's octave): stored note -> endpoint note."""
    off = min(n for _, n, _ in got) - min(u[0] for u in units)
    return lambda n: n + off


def lists_ok(h, player):
    """The player's length list: every entry 0-7 once in the free list (head 8) or the used list (head 9), links at
    + 0x68 + 2 i; each sounding note's [+ 0x9B + note] names a used entry holding that note."""
    def walk(head):
        out, i = [], h.r8(player + 0x68 + 2 * head)
        while i != 0xFF:
            assert i < 8 and len(out) < 8, (head, out, i)
            out.append(i)
            i = h.r8(player + 0x68 + 2 * i)
        return out
    free, used = walk(8), walk(9)
    assert sorted(free + used) == list(range(8)), (free, used)
    for n in range(1, 128):                          # [+ 0x9B + 0] is entry 7's last byte (stock's layout)
        e = h.r8(player + 0x9B + n)
        assert e == 0xFF or (e in used and h.r8(player + 0x7E + 4 * e) == n), (n, e, used)
    return used


def gate_ticks(gate):
    """Stock's length at 1/16 (6 ticks a step): gate & 0x7F sixths, 0 -> 1, over 96 -> 96."""
    g = gate & 0x7F
    return min(max(g, 1), 96)


CHORDS = {                                       # units in slot order (not pitch order): note, gate, microstep, velocity
    "triad": [(G, 6, 0, 90), (C, 3, 0, 100), (E, 12, 0, 80)],
    "7th": [(B, 4, 0, 70), (E, 6, 0, 90), (C, 2, 0, 100), (G, 12, 0, 60)],
    "9th+bass": [(G, 6, 0, 90), (36, 12, 0, 110), (62, 1, 0, 50), (C, 3, 0, 100), (B, 4, 0, 70), (E, 2, 0, 80)],
}


@pytest.mark.parametrize("down", [False, True], ids=["rising", "falling"])
@pytest.mark.parametrize("speed", [1, 2, 3], ids=["slow", "medium", "fast"])
@pytest.mark.parametrize("chord", list(CHORDS))
def test_played_strums(pl19_image, pl19_manifest, chord, speed, down):
    """Notes in strum order at the strum gaps; the first ends at stock's tick, every late note on its own block-chord end
    (step tick + its own length) when that is at least two ticks after its send, else the second tick after the send."""
    units = CHORDS[chord]
    h = setup(pl19_image, pl19_manifest, {0: units, 8: units}, speed=speed, down=down)
    h.press(PLAY)
    h.heartbeat(2 * 8 * 160 + 100)                   # the chord twice, on steps 1 and 9 (a step = 160 ms)
    h.press(PLAY)
    h.heartbeat(5)
    assert h.track_sounding() == set()
    to = endpoint(units, h.ons())
    order = sorted(units, key=lambda u: u[0], reverse=down)
    passes = []
    for p in range(2):                               # each time the chord plays: 8 steps = 48 ticks apart
        start, end = h.ticks[48 * p], h.ticks[48 * (p + 1)]
        ons = [e for e in h.ons(start) if e[0] < end]
        assert [n for _, n, _ in ons] == [to(u[0]) for u in order], (p, ons)        # by pitch, never slot order
        assert [v for _, _, v in ons] == [u[3] for u in order]                      # each its own velocity
        assert ons[0][0] == start                                                    # the first at stock's tick
        rel = [ms - start for ms, _, _ in ons]
        assert all(abs(r - k * GAP[speed]) <= 1 for k, r in enumerate(rel)), rel
        lengths = []
        for k, ((on, n, _), u) in enumerate(zip(ons, order)):
            off = next(ms for ms, x in h.offs(on) if x == n)
            L = gate_ticks(u[1])
            if k == 0:
                want = h.ticks[48 * p + L]                           # stock's: the L-th tick after its own
            else:                                                    # PL20: its own block-chord end ...
                want = h.ticks[48 * p + L]
                want = max(want, [t for t in h.ticks if t >= on][1])   # at least the second tick after its send
                assert off > on, (p, k, n, on, off)               # never in the on's ms
            assert off == want, (p, k, n, on, off, want)
            lengths.append(h.ticks.index(off) - next(i for i, t in enumerate(h.ticks) if t >= on))
        passes.append((rel, lengths))                                # lengths in ticks (ticks fall between ms)
    assert passes[0] == passes[1]


def play_script(h):
    h.press(PLAY)
    h.heartbeat(1400)
    h.press(PLAY)
    h.heartbeat(50)


OFF_PATTERN = {0: CHORDS["7th"], 2: [(D, 6, 0, 100)], 3: CHORDS["triad"], 5: CHORDS["9th+bass"]}


@pytest.mark.parametrize("speed, played", [(1, False), (0, True)], ids=["pattern-strum-off", "played-strum-off"])
def test_off_is_pl18(pl19_image, pl19_manifest, pl18_published_image, pl18_published_manifest, speed, played):
    runs = []
    for image, m in ((pl18_published_image, pl18_published_manifest), (pl19_image, pl19_manifest)):
        h = setup(image, m, OFF_PATTERN, speed=speed, played=played)
        play_script(h)
        runs.append(([e for e in h.events if e[1].startswith("synth")], pattern_snapshot(h, 0)))
    assert runs[0][0] and runs[0] == runs[1]


def test_single_notes_and_ties_are_stock(pl19_image, pl19_manifest, pl18_published_image, pl18_published_manifest):
    """A one-note step, a tie and its continuation beside one other note (a held tie does not sound: one sounding
    note), on a Played track with strum slow: as PL18."""
    steps = {0: [(C, 6, 0, 100)], 1: [(D, 6 | TIE, 0, 90)], 2: [(D, 6, 0, 90), (F, 6, 0, 80)],
             4: [(E, 6 | TIE, 0, 70)], 5: [(E, 6, 0, 70), (A, 6, 0, 50)]}
    runs = []
    for image, m in ((pl18_published_image, pl18_published_manifest), (pl19_image, pl19_manifest)):
        h = setup(image, m, steps, speed=1, played=True)
        play_script(h)
        runs.append([e for e in h.events if e[1].startswith("synth")])
    assert runs[0] == runs[1]
    ons = [n for ms, k, ch, n, v in runs[1] if k == "synth_on" and ch == 0 and ms < 8 * 160]
    assert len(ons) == len(set(ons)) == 5            # D and E sound once each: the continuations were held ties


def test_drums_untouched(pl19_image, pl19_manifest, pl18_published_image, pl18_published_manifest):
    """The dump's drum patterns play as on PL18 with every note track Played, strum slow, chords on track 0."""
    runs = []
    for image, m in ((pl18_published_image, pl18_published_manifest), (pl19_image, pl19_manifest)):
        h = setup(image, m, {0: CHORDS["triad"], 4: CHORDS["7th"]}, speed=1, played=True)
        for t in range(1, 4):
            set_strum(h, m, t, 1)
            if "chord_pstrum" in m["symbols"]:
                set_pstrum(h, m, t, PLAYED)
        play_script(h)
        runs.append([e for e in h.events if e[2] >= 4])          # the drums: synth / MIDI channel 0x10 +
    assert runs[0] and runs[0] == runs[1]


FIVE = [(C, 12, 0, 100), (E, 12, 0, 90), (G, 12, 0, 80), (B, 12, 0, 70), (62, 12, 0, 60)]   # slow: 320 ms


@pytest.mark.parametrize("nxt", ["chord", "single", "empty", "tie"])
def test_cut_short(pl19_image, pl19_manifest, nxt):
    """200 BPM (a step = 75 ms), a slow 5-note strum on step 1 (late notes due at 80 .. 320 ms)."""
    first = list(FIVE)
    steps = {0: first}
    if nxt == "chord":
        steps[1] = [(A, 6, 0, 100), (D, 6, 0, 90), (F, 6, 0, 80)]
    elif nxt == "single":
        steps[1] = [(A, 6, 0, 100)]
    elif nxt == "tie":
        first[0] = (C, 6 | TIE, 0, 100)              # the first note (lowest: stock's) ties into step 2
        steps[1] = [(C, 6, 0, 100)]
    h = setup(pl19_image, pl19_manifest, steps, speed=1, bpm=200)
    h.press(PLAY)
    h.heartbeat(600)
    to = endpoint(first, h.ons())
    s1, s2 = h.ticks[0], h.ticks[6]
    step1 = [n for ms, n, v in h.ons() if n in {to(u[0]) for u in first}]
    if nxt in ("chord", "single"):
        assert step1 == [to(C)]                      # the waiting notes never sound
        ons2 = [(ms, n) for ms, n, v in h.ons(s2)]
        assert ons2[0] == (s2, to(A if nxt == "single" else D))     # step 2 on time
        if nxt == "chord":
            assert [(ms - s2, n) for ms, n in ons2] == [(0, to(D)), (80, to(F)), (160, to(A))]   # a chord strums
        else:
            assert len(ons2) == 1
    else:
        assert [(ms - s1, n) for ms, n, v in h.ons()] == [(80 * k, to(u[0])) for k, u in enumerate(first)]
    h.press(PLAY)
    h.heartbeat(1)
    assert h.track_sounding() == set()
    stop = h.ms
    h.heartbeat(400)
    assert h.ons(stop + 1) == [] and h.track_sounding() == set()


def test_same_pitch_restarts(pl19_image, pl19_manifest):
    """Step 1: a 6-note chord on gate 96 (fast: its notes by 100 ms); step 2: E alone, gate 96 (7 entries); step 3: a
    triad C E G on gate 96, E late (20 ms): C fills the list; E ends step 2's E (not the head) and starts again; G finds
    the list full and stock's head (step 1's first note) is ended for it. E then ends where C does (PL20: its block-chord
    end, step 3's tick 96): step 2's E entry, which would have ended at step 2's tick 96, ends nothing."""
    big = [(36, 96, 0, 100), (38, 96, 0, 100), (39, 96, 0, 100), (41, 96, 0, 100), (43, 96, 0, 100), (44, 96, 0, 100)]
    steps = {0: big, 1: [(E, 96, 0, 90)], 2: [(C, 96, 0, 80), (E, 96, 0, 70), (G, 96, 0, 60)]}
    h = setup(pl19_image, pl19_manifest, steps, speed=3)
    h.press(PLAY)
    full = []
    for _ in range(3100):
        h.heartbeat(1)
        full.append(len(lists_ok(h, PLAYERS[0])))
    to = endpoint(big, h.ons())
    s3 = h.ticks[12]
    e_ons = [ms for ms, n, v in h.ons() if n == to(E)]
    assert e_ons == [h.ticks[6], s3 + 20]             # step 2's E, then the late E of step 3
    e_offs = [ms for ms, n in h.offs() if n == to(E)]
    assert e_offs[0] == s3 + 20                       # the old E ended at the late moment, before the new one
    assert e_offs[1] == h.ticks[12 + 96]              # the new E: with C, its block-chord end
    assert max(full) == 8                             # the list was full ...
    assert (s3 + 40, to(36)) in h.offs()              # ... and G's room came from stock's head
    assert (s3 + 40, to(G), 60) in h.ons()
    h.press(PLAY)
    h.heartbeat(5)
    assert h.track_sounding() == set()
    lists_ok(h, PLAYERS[0])


def test_stop_during_strum(pl19_image, pl19_manifest):
    """Stop at each ms of a slow triad's strum (late notes at 80 and 160 ms): nothing sounds after, no late note comes;
    Play again: step 1 strums."""
    units = CHORDS["triad"]
    h = setup(pl19_image, pl19_manifest, {0: units}, speed=1)
    for d in range(0, 166):
        h.press(PLAY)
        h.heartbeat(d)
        h.press(PLAY)
        stop = h.ms
        h.heartbeat(1)
        assert h.track_sounding() == set(), d
        h.heartbeat(GAP[1] + 5)
        assert h.ons(stop + 1) == [] and h.track_sounding() == set(), d
        lists_ok(h, PLAYERS[0])
    h.press(PLAY)
    start = h.ms + 1
    h.heartbeat(200)
    to = endpoint(units, h.ons())
    assert [(ms - start, n) for ms, n, v in h.ons(start)] == [(0, to(C)), (80, to(E)), (160, to(G))]
    h.press(PLAY)
    h.heartbeat(5)
    assert h.track_sounding() == set()


def nested(h, fn, *args):
    """Call fn on its own stack below the interrupted one (a UI-task call preempting the heartbeat)."""
    uc = h.uc
    uc.reg_write(UC_ARM_REG_SP, NESTED_SP)
    for i, v in enumerate(args):
        uc.reg_write(UC_ARM_REG_R0 + i, v)
    uc.reg_write(UC_ARM_REG_LR, STOP | 1)
    uc.emu_start(fn | 1, 0xFFFFFFFF, count=BUDGET)
    assert uc.reg_read(UC_ARM_REG_PC) & ~1 == STOP & ~1
    return uc.reg_read(UC_ARM_REG_R0)


def stock_stop(h):
    """Stock's Stop: the play store's parameter 0 to 0 through its write pointer and commit (the Play button's own
    route; its listeners reset every player)."""
    h.nbusy = 0
    ptr = nested(h, PARAM_WPTR, PLAY_STORE, 0)
    h.uc.mem_write(ptr, bytes([0]))
    nested(h, PARAM_COMMIT, PLAY_STORE)


def racing_heartbeat(h, when):
    """One heartbeat in which stock's Stop runs once, at the heartbeat's own seq_note_on (a late note): at its entry
    (`before`) or at its return (`after`). Returns whether it ran."""
    uc = h.uc
    st = {}
    h.nbusy = 0

    def at_note_on(u, a, s, d):
        lr = u.reg_read(UC_ARM_REG_LR)
        if st or lr & ~1 == STOCK_NOTE_ON_RETURN or u.reg_read(UC_ARM_REG_R0) != PLAYERS[h.t]:
            return
        st["lr"] = lr
        if when == "after":
            u.reg_write(UC_ARM_REG_LR, TRAP | 1)
        else:
            st["resume"] = NOTE_ON
            u.emu_stop()

    def at_trap(u, a, s, d):
        st["resume"] = st["lr"] & ~1
        u.emu_stop()

    hooks = [uc.hook_add(UC_HOOK_CODE, at_note_on, begin=NOTE_ON, end=NOTE_ON),
             uc.hook_add(UC_HOOK_CODE, at_trap, begin=TRAP, end=TRAP)]
    h.ms += 1
    uc.reg_write(UC_ARM_REG_SP, 0x2006F000)
    uc.reg_write(UC_ARM_REG_LR, STOP | 1)
    uc.emu_start(MS_SERVICE | 1, 0xFFFFFFFF, count=BUDGET)
    ran = "resume" in st
    if ran:
        ctx = uc.context_save()
        stock_stop(h)
        uc.context_restore(ctx)
        uc.emu_start(st["resume"] | 1, 0xFFFFFFFF, count=BUDGET)
    assert uc.reg_read(UC_ARM_REG_PC) & ~1 == STOP & ~1
    for k in hooks:
        uc.hook_del(k)
    h.collect()
    return ran


@pytest.mark.parametrize("when", ["after", "before"])
def test_stop_races_a_late_note(pl19_image, pl19_manifest, when):
    """Review focus: the UI task's Stop resets the player between the heartbeat's seq_note_on and its generation
    check (`after`), or just before the note-on (`before`): the late note ends within the same heartbeat, nothing
    sounds after, the length list stays well formed."""
    units = CHORDS["triad"]
    h = setup(pl19_image, pl19_manifest, {0: units}, speed=1)
    assert h.r32(PLAYERS[0] + 0x1C) == PLAY_STORE     # the store Stop resets the players through
    h.press(PLAY)
    h.heartbeat(GAP[1] - 2)
    for _ in range(4):
        if racing_heartbeat(h, when):
            break
    else:
        raise AssertionError("no late note-on from the heartbeat")
    at = h.ms
    assert param(h, PLAY_STORE, 0) == 0               # stopped
    to = endpoint(units, h.ons())
    assert (at, to(E)) in [(ms, n) for ms, n, v in h.ons()]          # the late note went out ...
    assert (at, to(E)) in h.offs()                                    # ... and ended in the same heartbeat
    assert h.track_sounding() == set()
    lists_ok(h, PLAYERS[0])
    h.heartbeat(300)
    assert h.ons(at + 1) == [] and h.track_sounding() == set()
    lists_ok(h, PLAYERS[0])
    h.press(PLAY)                                     # and Play strums again (after this store-level Stop the first
    start = h.ms + 1                                  # step comes a little later than after the button's: gaps only)
    h.heartbeat(300)
    again = h.ons(start)
    assert [(ms - again[0][0], n) for ms, n, v in again] == [(0, to(C)), (80, to(E)), (160, to(G))]
    h.press(PLAY)
    h.heartbeat(5)
    assert h.track_sounding() == set()


@pytest.mark.parametrize("how", ["mute", "pattern"])
def test_other_resets(pl19_image, pl19_manifest, how):
    """The Mixer's mute resets the player (stock ends what sounds): the waiting notes are dropped. A pattern change
    does not reset: the strum plays out (only the track's next notes cut it short)."""
    units = FIVE
    h = setup(pl19_image, pl19_manifest, {0: units}, speed=1)
    h.press(PLAY)
    h.heartbeat(100)                                  # the first note and the late one at 80 ms have sounded
    if how == "mute":
        h.press(MIXER)
        h.pad(0)                                      # track 0 mute on
    else:
        h.press(PATTERNS_VIEW)
        h.pad(8)                                      # another pattern for track 0 (taken at the pattern's end)
    at = h.ms
    h.heartbeat(400)
    to = endpoint(units, h.ons())
    if how == "mute":
        assert h.ons(at + 1) == [] and h.track_sounding() == set()
        h.pad(0)                                      # mute off
    else:
        assert [(ms - 1, n) for ms, n, v in h.ons()] == [(80 * k, to(u[0])) for k, u in enumerate(units)]
    h.press(PLAY)
    h.heartbeat(5)
    assert h.track_sounding() == set()
    lists_ok(h, PLAYERS[0])


def test_tick_zero(pl19_image, pl19_manifest):
    """A chord on step 1: Play strums it from tick 0, played on the first heartbeat after Play (Task 1's finding)."""
    units = CHORDS["7th"]
    h = setup(pl19_image, pl19_manifest, {0: units}, speed=2)
    h.press(PLAY)
    h.heartbeat(200)
    to = endpoint(units, h.ons())
    assert h.ticks[0] == 1
    assert [(ms, n) for ms, n, v in h.ons()] == [(1 + 40 * k, to(n)) for k, n in enumerate((C, E, G, B))]
    h.press(PLAY)
    h.heartbeat(5)
    assert h.track_sounding() == set()


@pytest.mark.parametrize("how", ["keys", "speed"])
def test_mode_change_mid_strum(pl19_image, pl19_manifest, how):
    """Review focus: the pattern strum set to off on the Keys page, or the strum speed to off, while notes wait:
    nothing stays on, and the next chord (step 3) plays as PL18: every note at its tick."""
    m = pl19_manifest
    units = FIVE
    h = setup(pl19_image, m, {0: units, 2: CHORDS["triad"]}, speed=1, played=False)
    open_page(h, 0)
    for _ in range(6):
        h.press(DOWN)                                 # the Keys page
    pick(h, KEYS_PLAYED)
    assert h.r8(sym(m, "chord_pstrum")) & 3 == PLAYED
    h.press(PLAY)
    h.heartbeat(100)                                  # two notes have sounded, three wait
    if how == "keys":
        pick(h, KEYS_PLAYED)
        assert h.r8(sym(m, "chord_pstrum")) & 3 == 0
    else:
        set_strum(h, m, 0, 0)
    at = h.ms
    h.heartbeat(250)
    s3 = h.ticks[12]
    to = endpoint(units, h.ons())
    assert [n for ms, n, v in h.ons(at + 1) if ms < s3] == []        # the waiting notes were dropped
    step3 = h.ons(s3)
    assert sorted(n for _, n, _ in step3) == [to(C), to(E), to(G)] and {ms for ms, _, _ in step3} == {s3}
    h.heartbeat(1200 - h.ms)                          # every note has ended by its length
    assert h.track_sounding() == set()
    h.press(PLAY)
    h.heartbeat(5)
    assert h.track_sounding() == set()
    lists_ok(h, PLAYERS[0])


def test_midi_track(pl19_image, pl19_manifest):
    """Track 2 (MIDI 1): the same strum reaches the MIDI transmitter."""
    units = CHORDS["7th"]
    h = setup(pl19_image, pl19_manifest, {0: units}, track=2, speed=1, down=True)
    h.press(PLAY)
    h.heartbeat(400)
    to = endpoint(units, h.ons())
    start = h.ticks[0]
    assert [(ms - start, n, v) for ms, n, v in h.ons()] == [(80 * k, to(u[0]), u[3]) for k, u in
                                                            enumerate(sorted(units, reverse=True))]
    h.press(PLAY)
    h.heartbeat(5)
    assert h.track_sounding() == set()
    lists_ok(h, PLAYERS[2])


def test_no_semaphore_from_late_notes(pl19_image, pl19_manifest):
    """The late notes take the DSP-service lock (0x08021064, through the synth note-on) only in the Main task's
    heartbeat: never inside the context-"any" handlers (seq_play_step, seq_end_all), never from a UI action; the
    build's lock check holds them to that (seq_note_on and seq_end_entry are tagged takes_dsp_lock), and their callees
    take no lock."""
    m = pl19_manifest
    units = CHORDS["9th+bass"]
    h = setup(pl19_image, m, {0: units}, speed=2, cls=VPH)
    h.set_headroom(0x60000)
    flash = (int(m["flash"]["start"], 16), int(m["flash"]["end"], 16))
    st = {"inside": None, "ret": None, "task": "ui"}
    takes, late = [], []

    def enter(u, a, s, d):
        st["inside"], st["ret"] = a, u.reg_read(UC_ARM_REG_LR) & ~1

    def slim_code(u, a, s, d):
        if st["inside"] is not None and a == st["ret"]:
            st["inside"] = None

    def lock(u, a, s, d):
        takes.append((st["task"], st["inside"]))

    def note_on(u, a, s, d):
        if u.reg_read(UC_ARM_REG_LR) & ~1 != STOCK_NOTE_ON_RETURN:
            late.append((st["task"], st["inside"]))

    for name in ("pstrum_on_play_step", "pstrum_on_reset"):
        h.uc.hook_add(UC_HOOK_CODE, enter, begin=sym(m, name), end=sym(m, name))
    h.uc.hook_add(UC_HOOK_CODE, slim_code, begin=flash[0], end=flash[1])
    h.uc.hook_add(UC_HOOK_CODE, lock, begin=0x08021064, end=0x08021064)
    h.uc.hook_add(UC_HOOK_CODE, note_on, begin=NOTE_ON, end=NOTE_ON)

    def beat(n):
        st["task"] = "main"
        h.heartbeat(n)
        st["task"] = "ui"
    h.press(PLAY)
    beat(150)                                        # mid-strum
    h.press(PLAY)                                    # Stop: the reset hook runs in the UI task
    beat(100)
    h.press(PLAY)
    beat(300)
    h.press(PLAY)
    beat(5)
    assert len(late) >= 5 + 3 and set(late) == {("main", None)}
    assert takes and all(inside is None for _, inside in takes)
    callees = m["stack_uncounted_callees"]
    for handler in ("pstrum_on_play_step", "pstrum_on_reset"):
        assert not {"seq_note_on", "seq_end_entry", "note_sink_on", "note_sink_off"} & set(callees.get(handler, ()))
    assert {"seq_note_on", "seq_end_entry"} <= set(callees["chord_on_ms"])
    assert h.track_sounding() == set()


LATE_ENDS = {                                    # PL20: (name, units, speed); every late note ends at step tick + its length
    "longer": ([(C, 6, 0, 100), (E, 24, 0, 90), (G, 48, 0, 80)], 1),
    "shorter": ([(C, 24, 0, 100), (E, 6, 0, 90), (G, 3, 0, 80)], 1),
    "edge": ([(C, 6, 0, 100), (E, 6, 0, 90), (G, 6, 0, 80), (B, 6, 0, 70)], 1),   # late notes at 81, 161, 241 ms: G
    # is sent in the tick of its block-chord end (160 ms), B after it; both last two ticks
    "first-gate-1-slow-five": ([(C, 1, 0, 100), (E, 12, 0, 90), (G, 12, 0, 80), (B, 12, 0, 70), (62, 12, 0, 60)], 1),
}


@pytest.mark.parametrize("case", list(LATE_ENDS))
def test_played_release_at_once(pl21_image, pl21_manifest, case):
    """Every late note ends on its own block-chord end tick (the step's tick + its own length in ticks) when that is at
    least two ticks after its send, else on the second tick after the send; its off is always after its on."""
    units, speed = LATE_ENDS[case]
    h = setup(pl21_image, pl21_manifest, {0: units}, speed=speed)
    h.press(PLAY)
    h.heartbeat(8 * 160 + 100)
    h.press(PLAY)
    h.heartbeat(5)
    assert h.track_sounding() == set()
    to = endpoint(units, h.ons())
    order = sorted(units, key=lambda u: u[0])
    ons = h.ons()
    assert [n for _, n, _ in ons] == [to(u[0]) for u in order]
    start = h.ticks[0]
    for k, ((on, n, _), u) in enumerate(zip(ons, order)):
        off = next(ms for ms, x in h.offs(on) if x == n)
        want = h.ticks[gate_ticks(u[1])]
        if k:
            want = max(want, [t for t in h.ticks if t >= on][1])   # at least the second tick after its send
            assert off > on, (k, n, on, off)                         # never in the on's ms
        assert off == want, (k, n, on, off, want)
        assert k == 0 or on > start


def test_written_and_off_lengths_unchanged(pl21_image, pl21_manifest, pl19_published_image, pl19_published_manifest):
    """Off (strum slow) and Written: the same synth log as the published PL19."""
    for played in (False, 2):
        runs = []
        for image, m in ((pl19_published_image, pl19_published_manifest), (pl21_image, pl21_manifest)):
            h = setup(image, m, OFF_PATTERN, speed=1, played=None)
            set_pstrum(h, m, 0, 0 if played is False else played)
            play_script(h)
            runs.append([e for e in h.events if e[1].startswith("synth")])
        assert runs[0] and runs[0] == runs[1], played
