"""Mono record (PL08, spec 2026-10-17-small-features-design.md D6, D7, section 3): on a track with its mono bit, a
note stock's recorder writes into a step removes the step's older notes; notes recorded together keep each other. All
through Play, Record and the real recorder (its commit 0x0803F7BE writes a step's unit at the note's end)."""
import pytest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2

from chord_model import settings
from notes import NoteHarness, PATTERN, STEP, fill, pattern_snapshot, set_tempo, units

pytestmark = pytest.mark.emu
OLD = [40, 41]                                   # notes already on a step before recording over it
PLAYER0, PLAY_STEP = 0x20040200, 0x08040E5A      # track 0's pattern player; seq_play_step(this, pattern, step, us)


def sym(m, name):
    return int(m["symbols"][name], 16)


def set_mono(h, m, t, on=True):
    h.call(sym(m, "slim_ready"))
    a = sym(m, "chord_mono")
    h.uc.mem_write(a, bytes([h.r8(a) & ~(1 << t) | int(on) << t]))


def start(h):
    """Play and Record on track 0: the next press lands on pattern 0, step 0."""
    h.track(0)
    h.press(17)
    h.recording(True)
    h.heartbeat(3)


def tap(h, pads, ms=40, after=300):
    for p in pads:
        h.down(p)
    h.heartbeat(ms)
    for p in pads:
        h.up(p)
    h.heartbeat(after)


def changed(h, t, before):
    """(pattern, step) of every step of track t whose bytes changed since `before`."""
    now = pattern_snapshot(h, t)
    return [(p, s) for p in range(8) for s in range(32)
            if now[p * PATTERN + s * STEP:p * PATTERN + (s + 1) * STEP] != before[p * PATTERN + s * STEP:p * PATTERN + (s + 1) * STEP]]


@pytest.mark.parametrize("mono", ["off", "on", "another track"])
def test_mono_replaces_an_older_note(pl09_image, pl09_manifest, mono):
    h = NoteHarness(pl09_image)
    h.track(0)
    if mono != "off":
        set_mono(h, pl09_manifest, 0 if mono == "on" else 1)
    fill(h, 0, 0, 0, OLD)
    start(h)
    tap(h, [24])
    got = units(h, 0, 0, 0)
    if mono == "on":
        assert len(got) == 1 and got[0] not in OLD, got
    else:
        assert len(got) == 3 and set(OLD) < set(got), got                     # stock: stacked


@pytest.mark.parametrize("how", ["chord engine", "pads together", "pads released apart"])
def test_mono_keeps_a_chord_together(pl09_image, pl09_manifest, how):
    from test_chord import set_chord
    h = NoteHarness(pl09_image)
    h.track(0)
    set_mono(h, pl09_manifest, 0)
    fill(h, 0, 0, 0, OLD)
    start(h)
    if how == "chord engine":
        set_chord(h, pl09_manifest, 0, settings(1))
        tap(h, [24])
    elif how == "pads together":
        tap(h, [24, 26, 28])
    else:
        for p in (24, 26, 28):
            h.down(p)
        h.heartbeat(30)
        h.up(24)
        h.heartbeat(150)                                               # into the next step
        h.up(26)
        h.heartbeat(150)
        h.up(28)
        h.heartbeat(300)
    got = units(h, 0, 0, 0)
    assert len(got) == 3 and not set(got) & set(OLD), got


RECORDERS = 0x2003C174


QUANT_STORE = 0x0803FE90                         # strb r0, [r7, #1]: the recorder's quantise flag [rec + 0x35] =
                                                 # !(bit 12 of parameter 2 of a settings store), at each placement


def quantise_off(h, t=0):
    """Stock's record quantise off, as the setting would make it: notes keep their offset in the step (start = step
    tick + offset, and a microstep)."""
    h.uc.mem_write(h.r32(RECORDERS + 4 * t) + 0x35, b"\0")
    h.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: u.reg_write(UC_ARM_REG_R0, 0), begin=QUANT_STORE, end=QUANT_STORE)


def test_mono_unquantised_keeps_a_step_visit_together(pl09_image, pl09_manifest):
    """Final review: with quantise off, pads pressed 25 ms apart into one step start on different ticks; they were
    recorded in the same visit of the step and keep each other."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_mono(h, pl09_manifest, 0)
    fill(h, 0, 0, 0, OLD)
    start(h)
    quantise_off(h)
    for p in (24, 26, 28):
        h.down(p)
        h.heartbeat(25)
    for p in (24, 26, 28):
        h.up(p)
    h.heartbeat(300)
    got = units(h, 0, 0, 0)
    assert len(got) == 3 and not set(got) & set(OLD), got


def test_mono_unquantised_strum_records_every_note(pl09_image, pl09_manifest):
    from test_chord import set_chord, set_strum
    h = NoteHarness(pl09_image)
    h.track(0)
    set_mono(h, pl09_manifest, 0)
    set_chord(h, pl09_manifest, 0, settings(2))
    set_strum(h, pl09_manifest, 0, 1)
    for s in range(4):
        fill(h, 0, 0, s, OLD)
    start(h)
    quantise_off(h)
    before = pattern_snapshot(h, 0)
    tap(h, [24], ms=500)
    got = [n for p, s in changed(h, 0, before) for n in units(h, 0, p, s)]
    assert len(got) == 4 and len(set(got)) == 4 and not set(got) & set(OLD), got


@pytest.mark.parametrize("quantised", [True, False])
def test_mono_unquantised_next_step_still_replaces(pl09_image, pl09_manifest, quantised):
    """A visit is one step: a note on the next step replaces that step's older notes, whatever the quantise."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_mono(h, pl09_manifest, 0)
    fill(h, 0, 0, 1, OLD)
    start(h)
    if not quantised:
        quantise_off(h)
    tap(h, [24], ms=40, after=130)                                     # step 1 (pattern 0)
    tap(h, [26], ms=40)                                                # step 2: 160 ms steps
    assert not set(units(h, 0, 0, 1)) & set(OLD) and len(units(h, 0, 0, 1)) == 1, units(h, 0, 0, 1)


def test_mono_arpeggio_over_a_loop(pl09_image, pl09_manifest):
    from test_chord import set_chord
    h = NoteHarness(pl09_image)
    h.track(0)
    set_mono(h, pl09_manifest, 0)
    set_chord(h, pl09_manifest, 0, settings(1))
    h.uc.mem_write(sym(pl09_manifest, "chord_arp"), bytes([1 | 2 << 3, 5 << 2]))   # up, 1/16, legato
    for s in range(16):
        fill(h, 0, 0, s, OLD)
    start(h)
    before = pattern_snapshot(h, 0)
    h.down(24)
    h.heartbeat(6 * 160)                                               # about 6 steps of the dump's tempo
    h.up(24)
    h.heartbeat(400)
    steps = changed(h, 0, before)
    assert len(steps) >= 5, steps
    for p, s in steps:
        got = units(h, 0, p, s)
        assert len(got) == 1 and got[0] not in OLD, (s, got)           # only the arpeggio's note
    assert all(units(h, 0, 0, s) == OLD for s in range(16) if (0, s) not in steps)


def test_mono_next_pass_replaces_again(pl09_image, pl09_manifest):
    """The same step at the same position a pass later (8 patterns at 240 BPM: 128 steps of 62.5 ms)."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_tempo(h, bpm=240)
    set_mono(h, pl09_manifest, 0)
    head = []
    h.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: head.append((u.reg_read(UC_ARM_REG_R1), u.reg_read(UC_ARM_REG_R2)))
                  if u.reg_read(UC_ARM_REG_R0) == PLAYER0 else None, begin=PLAY_STEP, end=PLAY_STEP)
    start(h)
    tap(h, [24], after=30)
    first = units(h, 0, 0, 0)
    assert len(first) == 1, first
    for _ in range(12000):                                             # back on pattern 0, step 0
        h.heartbeat(1)
        if head and head[-1] == (0, 0) and (0, 1) in head:
            break
    else:
        raise AssertionError("the loop never came back to its first step")
    tap(h, [26], ms=20, after=200)
    got = units(h, 0, 0, 0)
    assert len(got) == 1 and got != first, (first, got)


def test_mono_strummed_chord_replaces_per_step(pl09_image, pl09_manifest):
    """Each step a strummed note lands on loses its older notes. Notes the recorder quantizes to the same position
    (two strummed notes inside one step) are recorded together, as a chord's (D7)."""
    from test_chord import set_chord, set_strum
    h = NoteHarness(pl09_image)
    h.track(0)
    set_mono(h, pl09_manifest, 0)
    set_chord(h, pl09_manifest, 0, settings(2))                        # 7th: 4 notes, 80 ms apart
    set_strum(h, pl09_manifest, 0, 1)
    for s in range(4):
        fill(h, 0, 0, s, OLD)
    start(h)
    before = pattern_snapshot(h, 0)
    tap(h, [24], ms=500)
    steps = changed(h, 0, before)
    assert len(steps) >= 2, steps
    got = [n for p, s in steps for n in units(h, 0, p, s)]
    assert len(got) == 4 and len(set(got)) == 4 and not set(got) & set(OLD), (steps, got)   # each note once


def test_mono_survives_a_stock_edit(pl09_image, pl09_manifest):
    """No editing copy writes the removed notes back: a step edit on the recorded step, a view round trip, playback."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_mono(h, pl09_manifest, 0)
    fill(h, 0, 0, 0, OLD)
    start(h)
    tap(h, [24])
    got = units(h, 0, 0, 0)
    assert len(got) == 1, got
    h.recording(False)
    h.press(17)                                                        # stop
    h.heartbeat(20)
    h.down(0)                                                          # hold step 1 (2-row view) ...
    h.down(30)                                                         # ... and add a key's note to it
    h.up(30)
    h.up(0)
    h.heartbeat(20)
    edited = units(h, 0, 0, 0)
    assert len(edited) == 2 and got[0] in edited and not set(edited) & set(OLD), edited
    h.press(14)
    h.press(0)                                                         # Mixer and back
    h.press(17)
    h.heartbeat(400)
    h.press(17)
    h.heartbeat(20)
    assert units(h, 0, 0, 0) == edited


def test_mono_step_entry_is_stock(pl09_image, pl09_manifest):
    """D6: only live recording; adding a note to a held step stacks as in stock."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_mono(h, pl09_manifest, 0)
    fill(h, 0, 0, 0, OLD)
    h.down(0)
    h.down(30)
    h.up(30)
    h.up(0)
    h.heartbeat(20)
    got = units(h, 0, 0, 0)
    assert len(got) == 3 and set(OLD) < set(got), got


def script(h):
    fill(h, 0, 0, 0, OLD)
    start(h)
    tap(h, [24])
    tap(h, [24, 26, 28])
    for p in (24, 26):
        h.down(p)
    h.heartbeat(30)
    h.up(24)
    h.heartbeat(150)
    h.up(26)
    h.heartbeat(300)


def test_poly_is_stock(stock_image, pl09_image):
    a, b = NoteHarness(stock_image), NoteHarness(pl09_image)
    for h in (a, b):
        h.track(0)
        script(h)
    assert pattern_snapshot(b, 0) == pattern_snapshot(a, 0)
