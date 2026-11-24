"""PL20 Task 6: row 4 of stock's probability view (Shift + Pattern Settings) is the pass grid, Shift + row 4 the eight
special conditions (features/chord/trig_ui.c). The gesture is latched on the press (tap, a ½ s hold, Shift) and written
on the container's release (hook cont_release), never on the press; the LEDs come from chord_on_leds (trig_draw). Plan
2026-11-07-trig-conditions.md, Task 6 and Global Constraints "The code", "Timing", "Colours", "Device rules kept";
evidence docs/investigations/2026-11-01-trig-conditions-spike/C-controls.md (Q1, Q2) and
2026-11-07-trig-conditions-spike.md Q4 (the edited step, the store path, its two catches).

Everything through the controller: buttons (Shift + Pattern Settings, Note, track buttons, Mixer, Play, Record, Save),
pads (step pads 0-15, row 3 = 16-23, row 4 = 24-31), the Main task's 1 ms service (`heartbeat`, which counts trig_ms).
Drum 1 (track 4) and Synth 1 (track 0); every test starts from an 8-step loop with a hit / a note (60) on each step of
pattern 0, the project marked unless the test says otherwise. Steps are 0-based (pad k = step k + 1)."""
import random

import pytest
from unicorn import UC_HOOK_CODE

import trig_model as tm
from drums import sym
from test_saved import RECORD_SIZE, record, save
from trig import BTN_NOTE, DRUM_PAT, MIXER, PSET, RECORD, ROW3, ROW4, TrigHarness, loops, trig_setup

pytestmark = pytest.mark.emu

SYNTH1, SYNTH2, DRUM1 = 0, 1, 4
CYAN, CYAN_D = tm.COL_CYAN, tm.COL_CYAN_DIM
FIRST, NOT_FIRST, FILL, NOT_FILL, PRE, NOT_PRE, LAST, NOT_LAST = tm.TRIG_SPECIAL
KINDS = pytest.mark.parametrize("t", [DRUM1, SYNTH1], ids=["drum1", "synth1"])
HOLD = 600                                       # ms: a hold (TRIG_HOLD_MS = 500)


def fresh(image, m, t, mark=1, steps=range(8)):
    """slim ready, 240 BPM, every track an 8-step loop of pattern 0, every step empty but `steps` of track t (a hit /
    note 60), the project marked (`mark`), track t's probability view open."""
    h = TrigHarness(image, m)
    trig_setup(h, loops(8))
    h.clear_steps()
    for s in steps:
        h.hit(t, 0, s)
    h.load_editors()
    if mark is not None:
        h.mark(mark)
    h.open_prob(t)
    return h


def codes(h, t, p=0):
    return [h.code(t, p, s) for s in range(32)]


def only(s, code):
    return [code if k == s else 0 for k in range(32)]


def drum(t):
    return int(t >= 4)


# ---- the gestures ----------------------------------------------------------------------------------------------------

@KINDS
def test_hold_sets_the_length(pl21_image, pl21_manifest, t):
    """A row-4 pad held ½ s sets a cycle of its length (pad L = L passes), pass 1 ticked: pad 1 bright cyan, pads 2..L
    dim cyan, the rest dark. 499 ms is a tap (nothing without a condition), 500 ms a hold."""
    h = fresh(pl21_image, pl21_manifest, t)
    h.pad(2)
    h.row4(3, ms=499)
    assert codes(h, t) == [0] * 32 and h.row4_leds() == [0] * 8
    h.row4(3, ms=500)
    assert codes(h, t) == only(2, tm.trig_cycle(4, 1))
    for length in range(2, 9):
        h.row4(length - 1, ms=HOLD)                  # (the first from length 4: pass 1 is the tick that fits)
        c = tm.trig_cycle(length, 1)
        assert codes(h, t) == only(2, c), length
        assert h.row4_leds() == [CYAN] + [CYAN_D] * (length - 1) + [0] * (8 - length)
        h.row4(length - 1, ms=HOLD)                  # the length's pad again: cleared
        assert codes(h, t) == [0] * 32 and h.row4_leds() == [0] * 8


@KINDS
def test_taps(pl21_image, pl21_manifest, t):
    """A tap ticks / unticks its pass; every pass ticked is stored; the last untick clears the condition (row 4 dark);
    a tap past L or with no condition does nothing."""
    h = fresh(pl21_image, pl21_manifest, t)
    h.pad(2)
    h.row4(0)                                        # no condition: nothing
    assert codes(h, t) == [0] * 32
    h.row4(3, ms=HOLD)
    assert h.code(t, 0, 2) == tm.trig_cycle(4, 0b0001)
    for pad, mask in ((2, 0b0101), (1, 0b0111), (3, 0b1111), (0, 0b1110), (1, 0b1100), (3, 0b0100)):
        h.row4(pad)
        assert codes(h, t) == only(2, tm.trig_cycle(4, mask)), pad
        assert h.row4_leds() == tm.trig_row4(tm.trig_cycle(4, mask), 0, drum(t))
    h.row4(5)                                        # past L
    h.row4(7)
    assert codes(h, t) == only(2, tm.trig_cycle(4, 0b0100))
    h.row4(2)                                        # the last ticked pass: the condition goes
    assert codes(h, t) == [0] * 32 and h.row4_leds() == [0] * 8
    h.row4(2)
    assert codes(h, t) == [0] * 32


@KINDS
def test_holds(pl21_image, pl21_manifest, t):
    """The length's pad held again clears; pass 1 held clears; another length keeps the ticks that fit (none fit:
    pass 1)."""
    h = fresh(pl21_image, pl21_manifest, t)
    h.pad(2)
    h.row4(3, ms=HOLD)
    h.row4(3, ms=HOLD)
    assert codes(h, t) == [0] * 32
    h.row4(3, ms=HOLD)
    h.row4(0, ms=HOLD)                               # pass 1 held
    assert codes(h, t) == [0] * 32
    h.row4(3, ms=HOLD)
    h.row4(1)
    h.row4(0)                                        # 4 passes, pass 2 ticked
    h.row4(3)                                        # and pass 4
    assert h.code(t, 0, 2) == tm.trig_cycle(4, 0b1010)
    h.row4(2, ms=HOLD)                               # 3 passes: pass 2 fits, pass 4 does not
    assert h.code(t, 0, 2) == tm.trig_cycle(3, 0b010)
    h.row4(5, ms=HOLD)                               # 6 passes: pass 2 kept
    assert h.code(t, 0, 2) == tm.trig_cycle(6, 0b010)
    h.row4(4)
    h.row4(1)                                        # pass 5 only
    assert h.code(t, 0, 2) == tm.trig_cycle(6, 0b10000)
    h.row4(1, ms=HOLD)                               # 2 passes: nothing fits, pass 1
    assert codes(h, t) == only(2, tm.trig_cycle(2, 1))


def test_specials(pl21_image, pl21_manifest):
    """Shift + row 4 on Drum 1: each of the eight specials, the same pad again clears; a special replaces a cycle and a
    hold replaces a special; plain row 4 with a special = 8 pads dim in its colour, a tap there nothing. On Synth 1 the
    FILL pads (27-28) are dark and inert."""
    h = fresh(pl21_image, pl21_manifest, DRUM1)
    h.pad(2)
    for i, sp in enumerate(tm.TRIG_SPECIAL):
        h.row4(i, shift=True)
        assert codes(h, DRUM1) == only(2, sp), i
        h.shift(True)
        assert h.row4_leds() == tm.trig_row4(sp, 1, 1)
        h.shift(False)
        dim = tm.SPECIAL_COL[i][1]
        assert h.row4_leds() == [dim] * 8
        h.row4(0)
        h.row4(i)                                    # plain taps: nothing
        assert codes(h, DRUM1) == only(2, sp)
        h.row4(i, shift=True)                        # again: cleared
        assert codes(h, DRUM1) == [0] * 32 and h.row4_leds() == [0] * 8
    h.row4(3, ms=HOLD)
    h.row4(6, shift=True)                            # a special replaces a cycle
    assert h.code(DRUM1, 0, 2) == LAST
    h.row4(4, ms=HOLD)                               # a hold replaces a special
    assert h.code(DRUM1, 0, 2) == tm.trig_cycle(5, 1)

    h = fresh(pl21_image, pl21_manifest, SYNTH1)
    h.pad(2)
    h.shift(True)
    leds = h.row4_leds()
    h.shift(False)
    assert leds == tm.trig_row4(0, 1, 0) and leds[2:4] == [0, 0] and all(leds[k] for k in (0, 1, 4, 5, 6, 7))
    h.row4(2, shift=True)
    h.row4(3, shift=True)
    assert codes(h, SYNTH1) == [0] * 32
    h.row4(4, shift=True)
    h.row4(2, shift=True)                            # FILL on a note track: PRE stays
    assert codes(h, SYNTH1) == only(2, PRE)


# ---- what the press accepts ------------------------------------------------------------------------------------------

def accept_case(image, m, t, case):
    """Step 6 (index 5) selected beforehand; Shift + row-4 pad 1 (FIRST) in the case's state."""
    h = fresh(image, m, t)
    if case == "not following":
        h.follow(False)
    h.pad(5)
    if case != "stopped":
        h.play()
        h.heartbeat(37)
    if case == "held":
        h.down(2)
    playhead = h.selected(t)
    h.row4(0, shift=True)
    if case == "held":
        h.up(2)
    return h, playhead


@KINDS
@pytest.mark.parametrize("case,want", [("held", 2), ("stopped", 5), ("following", None), ("not following", 5)])
def test_accept_rules(pl21_image, pl21_manifest, t, case, want):
    """Stock's own accept rule for row 3 (C-controls.md Q1): a step held (that step), stopped (the selected step), the
    editors not following the playhead (0x20039DE0 p0 = 1: the selected step); playing with the editors following and
    no step held: refused."""
    h, playhead = accept_case(pl21_image, pl21_manifest, t, case)
    if case == "following":
        assert playhead != (0, 5)                    # the selection followed the playhead
    assert codes(h, t) == (only(want, FIRST) if want is not None else [0] * 32)


@KINDS
def test_accept_needs_a_step(pl21_image, pl21_manifest, t):
    """A Synth 1 step without notes is refused (stock tests the edit store's unit mask); a Drum 1 step without a hit:
    nothing, and no hit is made."""
    h = fresh(pl21_image, pl21_manifest, t, steps=[0, 1])
    h.pad(5)
    h.row4(0, shift=True)
    h.row4(3, ms=HOLD)
    assert codes(h, t) == [0] * 32
    if t >= 4:
        assert h.r8(h.drum_base(0) + 5) == 0
    else:
        assert h.step_word(t, 0, 5) == bytes(4)
    h.pad(1)
    h.row4(0, shift=True)
    assert codes(h, t) == only(1, FIRST)


@KINDS
def test_no_write_on_the_press(pl21_image, pl21_manifest, t):
    """The press only latches: a write watch on every pattern and store sees nothing during the controller's press
    (Shift + pad, and a plain pad), slim_irq_save is never reached; the release writes (here the project's first
    condition, so the release also clears the old bytes)."""
    h = fresh(pl21_image, pl21_manifest, t, mark=0)
    h.pad(2)
    irq = sym(pl21_manifest, "slim_irq_save") & ~1
    masked = []
    hk = h.uc.hook_add(UC_HOOK_CODE, lambda *a: masked.append(1), begin=irq, end=irq)
    log, hooks = h.watch_writes()
    h.shift(True)
    h.down(ROW4 + 0)
    assert log == [] and masked == []
    h.up(ROW4 + 0)
    h.shift(False)
    assert log and codes(h, t) == only(2, FIRST) and h.r8(sym(pl21_manifest, "trig_mark")) == 1
    log.clear()
    h.down(ROW4 + 3)
    assert log == [] and masked == []
    h.heartbeat(HOLD)
    h.up(ROW4 + 3)
    assert log and codes(h, t) == only(2, tm.trig_cycle(4, 1))
    h.unwatch(hooks)
    h.uc.hook_del(hk)


# ---- the edited step (Review Focus; Task 1 Q4) ---------------------------------------------------------------------

@KINDS
def test_selected_step_mirror(pl21_image, pl21_manifest, t):
    """A row-4 write, then a row-3 press without the step pad (stock writes the selected step's word 0 back from the
    editor's store): the condition is kept, the probability set."""
    h = fresh(pl21_image, pl21_manifest, t)
    h.pad(2)
    h.row4(2, ms=HOLD)
    h.pad(ROW3 + 3)
    assert codes(h, t) == only(2, tm.trig_cycle(3, 1))
    if t < 4:
        assert h.step_word(t, 0, 2)[:2] == bytes([1, 3])
    else:
        assert h.r8(h.drum_base(0) + 0x20 + 2) == 3


def test_selection_moved_before_the_release(pl21_image, pl21_manifest):
    """Synth 1 playing with the editors following: step 3 held, row 4 pressed, the step pad let go first; at the
    release the selection is the playhead's: the condition goes on step 3 (raw), the step selected then is unchanged."""
    h = fresh(pl21_image, pl21_manifest, SYNTH1)
    h.play()
    h.heartbeat(37)
    h.down(2)
    h.down(ROW4 + 2)
    h.up(2)
    h.heartbeat(HOLD + 150)                          # the playhead (8 steps of 62.5 ms) away from step 3
    assert h.selected(SYNTH1) != (0, 2)
    before = [h.step_word(SYNTH1, 0, s) for s in range(32)]
    h.up(ROW4 + 2)
    after = [h.step_word(SYNTH1, 0, s) for s in range(32)]
    assert codes(h, SYNTH1) == only(2, tm.trig_cycle(3, 1))
    assert [s for s in range(32) if before[s] != after[s]] == [2] and after[2][:2] == before[2][:2]


def test_stale_store_keeps_the_pattern(pl21_image, pl21_manifest):
    """The selected step's notes changed raw (a CTPlay writer; the editor's store still holds the old word 0): the
    write through the store keeps the pattern's [0], [1] and its units."""
    h = fresh(pl21_image, pl21_manifest, SYNTH1)
    h.pad(2)
    st = h.edit_store(SYNTH1)
    assert h.param_bytes(st, 0) == bytes([1, 7, 0, 0])
    a = h.note_step_at(SYNTH1, 0, 2)
    h.uc.mem_write(a, bytes([3, 5]))
    h.uc.mem_write(a + 8, bytes([64, 6, 0, 90]))     # unit 1
    step = bytes(h.uc.mem_read(a, 28))
    h.row4(0, shift=True)
    assert bytes(h.uc.mem_read(a, 28)) == step[:2] + bytes([FIRST, 0]) + step[4:]
    assert h.param_bytes(st, 0) == bytes([3, 5, FIRST, 0])


def test_live_recording_into_the_selected_step(pl21_image, pl21_manifest):
    """The controller's ruling (Task 6): live recording into the editor's selected step (Record on, playing, the
    editors not following: 0x20039DE0 p0 = 1), then a row-4 release on that step: the step keeps the recorded notes
    ([0], [1] and the units) and gets the condition."""
    h = fresh(pl21_image, pl21_manifest, SYNTH1)
    h.follow(False)
    h.pad(2)                                         # step 3 selected
    h.track(SYNTH1)                                  # its Note view
    h.press(RECORD)
    h.play()
    for _ in range(2000):
        if h.playing(SYNTH1)[1] == 2:
            break
        h.heartbeat(1)
    h.down(28)                                       # a key pad, while the playhead is on step 3
    h.heartbeat(20)
    h.up(28)
    a = h.note_step_at(SYNTH1, 0, 2)
    for _ in range(600):                             # the recorder commits the note at a later tick
        if h.r8(a) != 1:
            break
        h.heartbeat(1)
    recorded = bytes(h.uc.mem_read(a, 28))
    assert recorded[0] == 0b11, recorded.hex()      # note 60 and the recorded note
    store = h.param_bytes(h.edit_store(SYNTH1), 0)
    print(f"step 3 after recording {recorded[:4].hex()}, the edit store's word 0 {store.hex()}")
    h.press(PSET, shift=True)                        # its probability view, still playing and recording
    assert h.selected(SYNTH1) == (0, 2)
    h.row4(6, shift=True)
    h.press(RECORD)
    step = bytes(h.uc.mem_read(a, 28))
    assert step[:2] == recorded[:2] and step[4:] == recorded[4:], (recorded.hex(), step.hex())
    assert codes(h, SYNTH1) == only(2, LAST)


# ---- the first write (Review Focus: a project from another build) --------------------------------------------------

def test_first_write_marks_and_clears(pl21_image, pl21_manifest):
    """Junk in every drum pattern's +0x84..+0xA7, every note step's [2]-[3] and each note editor's store (word 0 bytes
    2-3), mark 0: the first release clears all of it but the written step and marks the project; a row-3 press on
    each note track brings no junk back; a save and load keeps the mark and the condition."""
    h = fresh(pl21_image, pl21_manifest, DRUM1, mark=0)
    rng = random.Random(20)
    sel = [h.selected(t) for t in range(4)]
    for t in range(4):                               # a note on each note editor's selected step (row 3 needs one)
        h.hit(t, *sel[t])
        h.param_set(h.edit_store(t), 0, bytes([1, 7, 0xA5, 0x5B]))
    for t in range(4):
        for p in range(8):
            for s in range(32):
                h.uc.mem_write(h.note_step_at(t, p, s) + 2, bytes([rng.randrange(1, 256), rng.randrange(1, 256)]))
    for d in range(4):
        for p in range(8):
            h.uc.mem_write(h.drum_base(d) + DRUM_PAT * p + 0x84, bytes(rng.randrange(1, 256) for _ in range(0x24)))
    h.pad(2)
    h.row4(6, shift=True)                            # LAST on Drum 1's step 3
    mark = sym(pl21_manifest, "trig_mark")
    assert h.r8(mark) == 1

    def clean():
        for d in range(4):
            for p in range(8):
                want = bytes(0x24) if (d, p) != (0, 0) else bytes(4) + bytes([0, 0, LAST]) + bytes(0x24 - 7)
                assert bytes(h.uc.mem_read(h.drum_base(d) + DRUM_PAT * p + 0x84, 0x24)) == want, (d, p)
        for t in range(4):
            assert all(h.step_word(t, p, s)[2:] == bytes(2) for p in range(8) for s in range(32)), t
    clean()
    for t in range(4):
        assert h.param_bytes(h.edit_store(t), 0)[2:] == bytes(2), t
    for t in range(4):
        h.open_prob(t)
        assert h.selected(t) == sel[t]
        h.pad(ROW3 + 2)                              # stock commits the store's word 0 into the selected step
        assert h.step_word(t, *sel[t])[:2] == bytes([1, 2]), t
    clean()
    save(h)
    file = bytes(h.uc.mem_read(record(h), RECORD_SIZE))
    h.mark(0)
    h.set_code(DRUM1, 0, 2, 0)
    h.uc.mem_write(record(h), file)
    h.load()
    h.leds()
    assert h.r8(mark) == 1 and h.code(DRUM1, 0, 2) == LAST


# ---- a view change while a row-4 pad is held (Review Focus; C-controls.md Q2) ----------------------------------------

@pytest.mark.parametrize("button", [BTN_NOTE, SYNTH2, MIXER], ids=["note", "synth2", "mixer"])
def test_view_change_while_held(pl21_image, pl21_manifest, button):
    """A pass pad held 600 ms, then another view: stock's release-all reaches cont_release while the probability view
    is still shown, so the hold applies there once; the finger's late release (in the new view) writes nothing. Held
    100 ms: a tap."""
    h = fresh(pl21_image, pl21_manifest, SYNTH1)
    h.pad(2)
    h.down(ROW4 + 2)
    h.heartbeat(HOLD)
    shown = h.shape()
    h.press(button)
    assert h.shape() != shown                        # another view (or track) is shown
    assert codes(h, SYNTH1) == only(2, tm.trig_cycle(3, 1))
    log, hooks = h.watch_writes()
    h.up(ROW4 + 2)
    h.heartbeat(HOLD)
    assert log == [] and codes(h, SYNTH1) == only(2, tm.trig_cycle(3, 1))
    h.unwatch(hooks)
    h.open_prob(SYNTH1)
    h.pad(2)
    h.down(ROW4 + 1)
    h.heartbeat(100)
    h.press(button)
    assert codes(h, SYNTH1) == only(2, tm.trig_cycle(3, 0b011))
    log, hooks = h.watch_writes()
    h.up(ROW4 + 1)
    assert log == [] and codes(h, SYNTH1) == only(2, tm.trig_cycle(3, 0b011))
    h.unwatch(hooks)


# ---- the LEDs --------------------------------------------------------------------------------------------------------

@KINDS
def test_row4_leds(pl21_image, pl21_manifest, t):
    """Row 4 shows the selected step's condition (following the playhead while playing); after ½ s of a plain hold the
    row the hold will write; with Shift the specials."""
    h = fresh(pl21_image, pl21_manifest, t)
    cs = {0: tm.trig_cycle(2, 1), 1: FIRST, 2: tm.trig_cycle(4, 0b1010), 3: LAST, 5: tm.trig_cycle(8, 0b10000001)}
    for s, c in cs.items():
        h.set_code(t, 0, s, c)
    for s in range(8):
        h.pad(s)
        assert h.row4_leds() == tm.trig_row4(cs.get(s, 0), 0, drum(t)), s
        h.shift(True)
        assert h.row4_leds() == tm.trig_row4(cs.get(s, 0), 1, drum(t)), s
        h.shift(False)
    h.pad(2)
    h.down(ROW4 + 5)
    h.heartbeat(499)
    assert h.row4_leds() == tm.trig_row4(cs[2], 0, drum(t))
    h.heartbeat(1)
    preview = tm.trig_edit(cs[2], 5, tm.TRIG_HOLD, drum(t))
    assert preview == tm.trig_cycle(6, 0b1010)
    assert h.row4_leds() == tm.trig_row4(preview, 0, drum(t))
    h.up(ROW4 + 5)
    assert h.code(t, 0, 2) == preview and h.row4_leds() == tm.trig_row4(preview, 0, drum(t))
    cs[2] = preview
    h.play()
    seen = set()
    for _ in range(40):
        h.heartbeat(13)
        p, s = h.selected(t)
        assert h.row4_leds() == tm.trig_row4(cs.get(s, 0), 0, drum(t)), s
        seen.add(s)
    assert len(seen) >= 6


# ---- stock's rows and the other views ------------------------------------------------------------------------------

def test_stock_rows_unchanged(pl21_image, pl21_manifest, pl19_published_image, pl19_published_manifest):
    """Shift + row 3 is stock's plain row-3 press; rows 1-3 of the probability view and pads 25-32 of every other view
    (with and without Shift) light as on the published PL19."""
    out = {}
    for name, img, m in (("pl19", pl19_published_image, pl19_published_manifest),
                         ("pl20", pl21_image, pl21_manifest)):
        h = TrigHarness(img, m)
        trig_setup(h, loops(8))
        h.clear_steps()
        for t in (SYNTH1, DRUM1):
            for s in range(8):
                h.hit(t, 0, s)
        h.load_editors()
        rows, row4 = [], []
        for t in (SYNTH1, DRUM1):
            h.open_prob(t)
            h.pad(2)
            if name == "pl20":
                h.shift(True)
            h.pad(ROW3 + 4)
            h.shift(False)
            rows.append(h.leds()[:24])
            for btns, shift in (([BTN_NOTE], False), ([BTN_NOTE], True), ([10], False), ([11], False),
                                ([PSET], False), ([BTN_NOTE, BTN_NOTE], False), ([13], False), ([MIXER], False),
                                ([15], False)):           # Note, Velocity, Gate, Pattern Settings, expanded, Patterns,
                for b in btns:                            # Mixer, FX
                    h.press(b)
                if shift:
                    h.shift(True)
                row4.append((btns, h.view_mode(), h.leds()[ROW4:ROW4 + 8]))
                h.shift(False)
                h.press(t)
        pats = [bytes(h.uc.mem_read(h.note_step_at(SYNTH1, 0, s), 4)) for s in range(8)] + \
               [bytes(h.uc.mem_read(h.drum_base(0), 0x80))]
        out[name] = rows, row4, pats
    assert out["pl20"] == out["pl19"]
    assert out["pl20"][2][2][1] == 4                 # Synth 1's step 3: probability 4 (pad 21)
