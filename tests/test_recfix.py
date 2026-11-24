"""Notes held past 16 steps while recording (PL15, spec 2026-10-23-chords-page-design.md, "The three fixes", item 3):
stock's commit 0x0803F7BE writes a note held 16 steps or more with a flat gate of 96 sixths; features/recfix ties it
and writes the rest 16 steps later (wrapping within the pattern's first .. last step), as upstream's SC45.3 / RC2.04
tools/recfix.py. All through Play, Record, a held pad and the real recorder."""
import pytest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R12

from notes import NoteHarness, PATTERN, PATTERN_BASE, STEP, TEMPO_STORE, param, pattern_snapshot, set_tempo
from notes import fill, step_addr
from test_mono import set_mono

pytestmark = pytest.mark.emu
SET = 0x380                      # pattern + 0x380: last step, + 0x381 first step, + 0x382 sync rate
STEP_TICKS = 0x0805B8B8          # stock's ticks a step by sync rate (the commit's literal 0x0803F8D0)
UDIV = 0x0803F856                # the commit's udiv lr, r2, ip: r2 = ticks held, ip = ticks a step
PLAY_STEP = 0x08040E5A           # seq_play_step(player, pattern, step, us)
PLAYERS = (0x20040200,)          # track 0's pattern player (test_mono)
TIE, GATE_MAX = 0x80, 96


def units(h, t, s, p=0):
    """(note, gate byte, microstep, velocity) of the step's units with their mask bit, in unit order."""
    a = step_addr(t, p, s)
    mask = h.r8(a)
    return [tuple(h.uc.mem_read(a + 4 + 4 * u, 4)) for u in range(6) if mask >> u & 1]


def prepare(h, t=0, last=31, first=0, bpm=None):
    """Track t's Note view; pattern 0 empty with steps first .. last."""
    h.track(t)
    if bpm:
        set_tempo(h, bpm=bpm)
    base = PATTERN_BASE[t]
    h.uc.mem_write(base, bytes(32 * STEP))
    h.uc.mem_write(base + SET, bytes([last, first]))


def watch_div(h):
    """(ticks held, ticks a step) of every commit that reaches stock's udiv (a note written)."""
    out = []
    h.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: out.append((u.reg_read(UC_ARM_REG_R2), u.reg_read(UC_ARM_REG_R12))),
                  begin=UDIV, end=UDIV)
    return out


def watch_head(h, player=PLAYERS[0]):
    out = []
    h.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: out.append((u.reg_read(UC_ARM_REG_R1), u.reg_read(UC_ARM_REG_R2)))
                  if u.reg_read(UC_ARM_REG_R0) == player else None, begin=PLAY_STEP, end=PLAY_STEP)
    return out


def step_ms(h):
    return 60000 / param(h, TEMPO_STORE, 0) / 4


def record(h, steps, t=0, pad=24, at=None, head=None):
    """Play, Record, (wait for pattern 0's step `at`), hold `pad` for `steps` and a half steps, let go."""
    h.track(t)
    h.press(17)
    h.recording(True)
    h.heartbeat(3)
    if at is not None:
        for _ in range(20000):
            h.heartbeat(1)
            if head and head[-1] == (0, at):
                break
        else:
            raise AssertionError(f"the player never reached step {at}")
    h.down(pad)
    h.heartbeat(int((steps + 0.5) * step_ms(h)))
    h.up(pad)
    h.heartbeat(300)


def written(h, t=0):
    """{step: units} of pattern 0's steps with any unit."""
    return {s: units(h, t, s) for s in range(32) if units(h, t, s)}


def left_of(div):
    """Sixths left after the first 96, from stock's own udiv operands."""
    (ticks, per), = div
    return ticks * 6 // per - GATE_MAX


def test_stock_cuts_at_16_steps(stock_image):
    """Step 1 (before any code): stock writes gate 96 and nothing 16 steps later; the commit's ticks a step is the
    word table 0x0805B8B8 indexed by the pattern's sync rate [base + 0x382], 6 ticks (6 sixths x 1 tick) at 1/16."""
    h = NoteHarness(stock_image)
    prepare(h)
    div, head = watch_div(h), watch_head(h)
    record(h, 20)
    base = PATTERN_BASE[0]
    rate = h.r8(base + SET + 2)
    (ticks, per), = div
    assert rate == 3 and per == h.r32(STEP_TICKS + 4 * rate) == 6
    steps = sorted({s for p, s in head if p == 0})
    assert ticks // per == 20 and set(range(21)) <= set(steps), (ticks, steps)     # last step 31: 32 steps play
    got = written(h)
    assert list(got) == [0] and len(got[0]) == 1 and got[0][0][1] == GATE_MAX, got   # cut at 96, no tie, step 16 empty


def test_held_20_steps_continues(pl15_image):
    h = NoteHarness(pl15_image)
    prepare(h)
    div = watch_div(h)
    record(h, 20)
    got = written(h)
    assert list(got) == [0, 16], got
    (note, gate, micro, vel), = got[0]
    assert gate == GATE_MAX | TIE
    assert got[16] == [(note, left_of(div), micro, vel)] and 0 < left_of(div) < GATE_MAX
    assert h.r8(step_addr(0, 0, 16) + 1) == 7                                        # probability, as stock writes


def test_held_40_steps_chains(pl15_image):
    """24 steps (last 23): 0 -> 16 -> 8 (16 + 16 - 24); ties on all but the last."""
    h = NoteHarness(pl15_image)
    prepare(h, last=23)
    div = watch_div(h)
    record(h, 40)
    got = written(h)
    assert list(got) == [0, 8, 16], got
    (note, gate, micro, vel), = got[0]
    assert gate == GATE_MAX | TIE
    assert got[16] == [(note, GATE_MAX | TIE, micro, vel)]
    assert got[8] == [(note, left_of(div) - GATE_MAX, micro, vel)] and 0 < left_of(div) - GATE_MAX < GATE_MAX


@pytest.mark.parametrize("last, steps", [(15, 20), (31, 10), (31, 15)])
def test_16_step_pattern_unchanged(pl15_image, pl14_published_image, last, steps):
    """A pattern of 16 steps, or a note held less than 16 steps: what PL14 records."""
    got = []
    for img in (pl15_image, pl14_published_image):
        h = NoteHarness(img)
        prepare(h, last=last)
        record(h, steps)
        got.append([pattern_snapshot(h, t) for t in range(4)])
    assert got[0] == got[1]


@pytest.mark.parametrize("there", ["the note", "full"])
def test_reuses_or_frees_a_unit(pl15_image, there):
    h = NoteHarness(pl15_image)
    prepare(h)
    probe = NoteHarness(pl15_image)                                       # the pad's note, from a plain recording
    prepare(probe)
    record(probe, 1)
    note = written(probe)[0][0][0]
    others = [40, 41, 42, 43, 44, 45]
    fill(h, 0, 0, 16, [40, note, 41] if there == "the note" else others)
    div = watch_div(h)
    record(h, 20)
    got = written(h)
    (n, gate, micro, vel), = got[0]
    assert n == note
    if there == "the note":
        assert gate == GATE_MAX | TIE
        assert got[16] == [(40, 6, 0, 100), (note, left_of(div), micro, vel), (41, 6, 0, 100)], got[16]
    else:
        assert gate == GATE_MAX                                            # none free: no tie
        assert got[16] == [(m, 6, 0, 100) for m in others]


def test_wraps_within_first_last(pl15_image):
    """First step 4, last 31 (28 steps): a note from step 20 goes on at 20 + 16 - 28 = 8; nothing outside 4 .. 31."""
    h = NoteHarness(pl15_image)
    prepare(h, first=4)
    head = watch_head(h)
    div = watch_div(h)
    record(h, 20, at=20, head=head)
    got = written(h)
    (s0,) = [s for s, us in got.items() if us[0][1] & TIE]
    assert 4 <= s0 - 12 and list(got) == sorted([s0 - 12, s0]), got
    note, _, micro, vel = got[s0][0]
    assert got[s0 - 12] == [(note, left_of(div), micro, vel)]


def test_17_step_pattern_stops_at_the_start(pl15_image):
    """17 steps (last 16): 16 steps on is one step back, so a long note walks 16, 15 .. 1 and stops before its own
    start step; the last one untied, nothing past step 16. 240 BPM, held 300 steps (1800 sixths: more than 17 x 96)."""
    h = NoteHarness(pl15_image)
    prepare(h, last=16, bpm=240)
    div = watch_div(h)
    record(h, 300)
    assert left_of(div) > 17 * GATE_MAX
    got = written(h)
    assert list(got) == list(range(17)), got
    note, gate, micro, vel = got[0][0]
    assert all(len(got[s]) == 1 for s in got)
    assert [got[s][0][1] for s in [0] + list(range(16, 0, -1))] == [GATE_MAX | TIE] * 16 + [GATE_MAX]
    assert {got[s][0][::2] for s in got} == {(note, micro)} and {got[s][0][3] for s in got} == {vel}


def test_flush_after_stop_writes_nothing_more(pl15_image):
    """Stop runs the recorder's flush of notes 1-139 (0x0803F6A2) on every track: their pending words are stale
    (bits 0-2 = 7 after a commit, the rest left over), so nothing more is written."""
    h = NoteHarness(pl15_image)
    prepare(h)
    flushed = []
    h.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: flushed.append(u.reg_read(UC_ARM_REG_R1)), begin=0x0803F6A2,
                  end=0x0803F6A2)
    record(h, 20)
    assert list(written(h)) == [0, 16]
    before = [pattern_snapshot(h, t) for t in range(4)]
    h.press(17)                                                            # stop, Record still on
    h.heartbeat(100)
    assert len(flushed) >= 139
    assert [pattern_snapshot(h, t) for t in range(4)] == before


@pytest.mark.parametrize("t", [1, 2, 3])
def test_every_note_track(pl15_image, t):
    """Synth 2, MIDI 1, MIDI 2."""
    h = NoteHarness(pl15_image)
    prepare(h, t=t)
    div = watch_div(h)
    record(h, 20, t=t)
    got = written(h, t)
    assert list(got) == [0, 16], got
    (note, gate, micro, vel), = got[0]
    assert gate == GATE_MAX | TIE and got[16] == [(note, left_of(div), micro, vel)]


def test_mono_continuation_keeps_other_notes(pl15_image, pl15_manifest):
    """Mono record on: the continuation is the held note going on; the older note at step 16 stays."""
    h = NoteHarness(pl15_image)
    prepare(h)
    set_mono(h, pl15_manifest, 0)
    fill(h, 0, 0, 16, [40])
    div = watch_div(h)
    record(h, 20)
    got = written(h)
    (note, gate, micro, vel), = got[0]
    assert gate == GATE_MAX | TIE
    assert got[16] == [(40, 6, 0, 100), (note, left_of(div), micro, vel)], got[16]


def test_arpeggio_held_20_steps_keeps_playing(pl15_image, pl15_manifest):
    """A chord's arpeggio (up, 1/16, legato) held 20 steps on a 32-step pattern, recorded: its notes go on past step
    16 (each its own short note: nothing tied, nothing at 96)."""
    from test_arp import set_arp, set_chord
    from chord_model import settings
    h = NoteHarness(pl15_image)
    prepare(h)
    set_chord(h, pl15_manifest, 0, settings(1))
    set_arp(h, pl15_manifest, 0, 1 | 2 << 3, 5 << 2)
    record(h, 20)
    got = written(h)
    assert {16, 17, 18, 19} <= set(got), sorted(got)
    assert all(len(us) == 1 and us[0][1] == 6 for s, us in got.items() if s < 19), got


def test_continuation_skips_a_unit_a_pending_note_claimed(pl15_image):
    """Review fix: note B pressed on step 16 while A (from step 0) is held claims a free unit at its note-on (stock's
    placement 0x0803F38C, the pending word's bits 0-2) but sets its mask bit only at its commit. A released first must
    not put its continuation there: B's commit would write over it."""
    h = NoteHarness(pl15_image)
    prepare(h)
    head = watch_head(h)
    div = watch_div(h)
    h.press(17)
    h.recording(True)
    h.heartbeat(3)
    h.down(24)                                                             # A, step 0
    for _ in range(20000):
        h.heartbeat(1)
        if head[-1] == (0, 16):
            break
    h.heartbeat(40)
    h.down(26)                                                             # B, step 16
    for _ in range(20000):
        h.heartbeat(1)
        if head[-1] == (0, 20):
            break
    h.heartbeat(80)
    h.up(24)                                                               # A: 20 steps and a half
    h.heartbeat(int(3 * step_ms(h)))
    h.up(26)                                                               # B: about 7 steps
    h.heartbeat(300)
    got = written(h)
    assert list(got) == [0, 16], got
    (a, gate, micro, vel), = got[0]
    assert gate == GATE_MAX | TIE
    left = div[0][0] * 6 // div[0][1] - GATE_MAX                          # A's commit comes first
    b = [u for u in got[16] if u[0] != a]
    assert len(got[16]) == 2 and (a, left, micro, vel) in got[16], got[16]
    assert len(b) == 1 and b[0][1] == div[1][0] * 6 // div[1][1] and not b[0][1] & TIE, (b, div)


def test_stop_while_held_writes_the_whole_note(pl15_image):
    """Stop (Play) pressed while the note is still held, 20 steps in, then the pad let go: stock's flush at Stop commits
    the held note with the current tick, so it is written up to the Stop: the first unit tied, the rest 16 steps on
    (never a tie without its continuation); the release after Stop writes nothing more."""
    h = NoteHarness(pl15_image)
    prepare(h)
    div = watch_div(h)
    h.track(0)
    h.press(17)
    h.recording(True)
    h.heartbeat(3)
    h.down(24)
    h.heartbeat(int(20.5 * step_ms(h)))
    h.press(17)                                                            # stop, the pad still down, Record still on
    h.heartbeat(100)
    at_stop = written(h)
    h.up(24)
    h.heartbeat(300)
    got = written(h)
    assert got == at_stop                                                  # the release adds nothing
    assert list(got) == [0, 16], got
    (note, gate, micro, vel), = got[0]
    assert gate == GATE_MAX | TIE
    assert got[16] == [(note, left_of(div), micro, vel)] and 0 < left_of(div) < GATE_MAX
