"""The chord feature (PL03: chord engine, strum, bass modes) in emulation: chord maths, notes through the real pad route, releases, strum, transparency."""
import random

import pytest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1

import emu_sc08
from chord_model import chord_notes, degree_class, in_scale, lead, settings
from harness import Harness
from notes import (NOTE_DEFAULT, NOTE_EXPANDED, OUTBUF, ROOT, SYNTH_ON, NoteHarness, SCALE_MASK, endpoint_note,
                   pattern_snapshot, recorded_notes)
from test_transparency import page_free, run, script

pytestmark = pytest.mark.emu
PARAM_GET = 0x0803542C
VIEW_BUTTONS = [14, 15]                         # Mixer, FX; no Preset: it stalls the emulator on the next pad press (covered by test_leaving_the_view_while_holding[8])
SETTINGS_ALL = [settings(sh, i, sp, b, r) for sh in range(8) for i in range(4) for sp in range(3)
                for b, r in ((0, 0), (1, 0), (1, 1))]   # no bass, bass below, rootless over bass


def sym(manifest, name):
    return int(manifest["symbols"][name], 16)


HELD, HELD_SIZE = 6, 14                         # chord_held.h: held_t {count, track, pad, notes[4], sent, vel, flags, wait, drop, root, order}
GAP = {1: 80, 2: 40, 3: 20}                     # chord.c STRUM_GAP: heartbeats (ms) between strummed notes


HEAP_LIMIT = 0x20002B44                         # stock's block-heap limit: slim_ready() lowers it to slim's RAM


def held_counts(h, manifest):
    """The chord table's counts. Until a hook first runs, slim's RAM is not reserved and holds stock's bytes: no chord
    can be held then."""
    if h.r32(HEAP_LIMIT) != sym(manifest, "__slim_ram_start"):
        return [0] * HELD
    base = sym(manifest, "held")
    return [h.r8(base + HELD_SIZE * i) for i in range(HELD)]


def set_chord(h, manifest, track, value):
    """Before the palette exists (Task 3), tests set a track's chord settings directly. The slim runtime zeroes its
    RAM on the first hook call, so run that start-up first or it would wipe the value."""
    h.call(sym(manifest, "slim_ready"))
    h.uc.mem_write(sym(manifest, "chord_settings") + track, bytes([value]))


def set_strum(h, manifest, track, speed):
    """Tests set a track's strum directly until the control exists (Task 4); same start-up rule as set_chord."""
    h.call(sym(manifest, "slim_ready"))
    a = sym(manifest, "chord_strum")
    h.uc.mem_write(a, bytes([h.r8(a) & ~(3 << 2 * track) | speed << 2 * track]))


def set_down(h, manifest, track, on=True):
    """The strum direction (PL08): bit t of chord_strum_down = falling; same start-up rule as set_chord."""
    h.call(sym(manifest, "slim_ready"))
    a = sym(manifest, "chord_strum_down")
    h.uc.mem_write(a, bytes([h.r8(a) & ~(1 << track) | int(on) << track]))


def strum_byte(h, manifest):
    return h.r8(sym(manifest, "chord_strum"))


def c_chord_notes(h, manifest, root, mask, s):
    h.call(sym(manifest, "chord_notes"), root, mask, s, OUTBUF)
    n = h.uc.reg_read(UC_ARM_REG_R0)
    return list(h.uc.mem_read(OUTBUF, n))


def test_math_matches_the_model(pl09_image, pl09_manifest):
    h = Harness(pl09_image)
    bad = []
    for mask in emu_sc08.MASKS:
        for root in range(48, 60):
            for s in SETTINGS_ALL:
                got, want = c_chord_notes(h, pl09_manifest, root, mask, s), chord_notes(root, mask, s)
                if got != want:
                    bad.append((hex(mask), root, hex(s), got, want))
    for key in (0, 7, 11):                      # the edges move with the project root: pitch + key within 12-139
        for root in (0, 1, 2, 11, 12, 13, 23, 24, 125, 127, 128, 132, 139):
            for mask in (0, emu_sc08.MASKS[0], emu_sc08.MASKS[1]):
                for s in SETTINGS_ALL:
                    s |= key << 16
                    got, want = c_chord_notes(h, pl09_manifest, root, mask, s), chord_notes(root, mask, s)
                    if got != want:
                        bad.append((hex(mask), root, hex(s), got, want))
    assert not bad, f"{len(bad)} mismatches, first: {bad[:5]}"


def test_chord_notes_new_shapes_match_the_model(pl15_image, pl15_manifest):
    h = Harness(pl15_image)
    rng = random.Random(1501)
    bad = []
    for shape in range(8, 13):                  # a row-2 shape is shape 7 + r with row 1 on single
        for inv in range(4):
            for spread in range(3):
                for b, r in ((0, 0), (1, 0), (1, 1)):
                    for _ in range(12):
                        root, mask = rng.randint(0, 139), rng.choice((*emu_sc08.MASKS, 0))
                        s = settings(0, inv, spread, b, r, rng.choice((0, 5, 11)), shape2=shape - 7)
                        got, want = c_chord_notes(h, pl15_manifest, root, mask, s), chord_notes(root, mask, s)
                        if got != want:
                            bad.append((hex(mask), root, hex(s), got, want))
    for s in (settings(2, shape2=3), settings(0, shape2=6), settings(0, shape2=15), settings(5, shape2=1)):
        for root in (48, 60):                   # row 1 wins; an unused row-2 value is single
            got, want = c_chord_notes(h, pl15_manifest, root, 0, s), chord_notes(root, 0, s)
            if got != want:
                bad.append((root, hex(s), got, want))
    assert not bad, f"{len(bad)} mismatches, first: {bad[:5]}"


def test_chord_lead_matches_the_model(pl15_image, pl15_manifest):
    h = Harness(pl15_image)
    rng = random.Random(1502)
    prev_at = 0x20060200
    bad = []
    for i in range(2400):
        root, mask = rng.randint(0, 139), rng.choice((*emu_sc08.MASKS, 0))
        shape, shape2 = rng.randint(0, 7), rng.randint(0, 5)
        s = settings(shape, rng.randint(0, 3), rng.randint(0, 2), rng.randint(0, 1), rng.randint(0, 1),
                     rng.choice((0, 5, 11)), shape2=shape2)
        prev = [rng.randint(0, 139) for _ in range(rng.randint(0, 6))]
        kind = 1 + i % 3
        h.uc.mem_write(prev_at, bytes(prev) + b"\0")
        h.call(sym(pl15_manifest, "chord_lead"), root, mask, s, prev_at, len(prev), kind)
        got, want = h.uc.reg_read(UC_ARM_REG_R0), lead(root, mask, s, prev, kind)
        if got != want:
            bad.append((root, hex(mask), hex(s), prev, kind, got, want))
    assert not bad, f"{len(bad)} mismatches, first: {bad[:5]}"


def test_math_terminates_on_a_mask_without_notes(pl09_image, pl09_manifest):
    h = Harness(pl09_image)
    got = c_chord_notes(h, pl09_manifest, 48, 0x00FFFFFF, settings(3, bass=1))   # Harness.call asserts it returned
    assert got == chord_notes(48, 0x00FFFFFF, settings(3, bass=1))


@pytest.mark.parametrize("mode", [NOTE_DEFAULT, NOTE_EXPANDED])
def test_chord_notes_per_track_and_view(pl09_image, pl09_manifest, mode):
    for track in range(4):
        h = NoteHarness(pl09_image)
        h.track(track, mode)
        mask = h.r32(SCALE_MASK)
        for shape in range(1, 8):
            set_chord(h, pl09_manifest, track, settings(shape))
            root = h.pitch(track, 24)
            want = sorted(endpoint_note(h, p) for p in [root] + chord_notes(root, mask, settings(shape)))
            h.take()
            h.down(24, 100)
            kind = "synth_on" if track < 2 else "midi_on"
            on = h.take(kind)
            notes = sorted(e[2] if kind == "synth_on" else e[3] for e in on)
            vels = {e[3] if kind == "synth_on" else e[4] for e in on}
            assert notes == want, (track, mode, shape, notes, want)
            assert len(vels) == 1, (track, shape, vels)                    # every note has the root's velocity
            h.up(24)
            assert h.sounding == set(), (track, mode, shape, h.sounding)


def test_chord_notes_take_the_pad_velocity(pl09_image, pl09_manifest):
    """The RAM dump has fixed velocity on (every note arrives as 96): turn it off, as the press handler 0x0804AB5A reads
    it (bit 1 of parameter 2 of the store at view + 0x28), so the pad's own velocity reaches every chord note."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(2))
    h.call(PARAM_GET, h.r32(h.note_view(0) + 0x28), 2)
    flags = h.uc.reg_read(UC_ARM_REG_R0)
    assert h.r8(flags) & 2, "fixed velocity is expected on in the dump"
    h.uc.mem_write(flags, bytes([h.r8(flags) & ~2]))
    h.take()
    h.down(24, 70)
    on = h.take("synth_on", "midi_on")
    assert len(on) == 8                                                     # 7th: 4 notes, synth and MIDI
    assert {e[3] if e[0] == "synth_on" else e[4] for e in on} == {70}
    h.up(24)
    assert h.sounding == set()


def test_single_plays_one_note(pl09_image):
    h = NoteHarness(pl09_image)
    h.track(0)
    h.take()
    h.down(24)
    assert len(h.take("synth_on")) == 1
    h.up(24)
    assert h.sounding == set()


def test_ignored_pad_plays_nothing(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0, NOTE_EXPANDED)
    set_chord(h, pl09_manifest, 0, settings(1))
    view = h.note_view(0)
    h.call(0x0804B174, view, 0)
    idx = h.uc.reg_read(UC_ARM_REG_R0)
    h.uc.mem_write(h.r32(view + 0x38) + 0x14 + idx, bytes([0x8C]))      # pad 1's pitch out of range: stock ignores it
    h.take()
    h.down(0)
    h.up(0)
    assert h.take("synth_on", "midi_on") == [] and h.sounding == set()


def set_pitch(h, track, pad, pitch):
    view = h.note_view(track)
    h.call(0x0804B174, view, pad)
    h.uc.mem_write(h.r32(view + 0x38) + 0x14 + h.uc.reg_read(UC_ARM_REG_R0), bytes([pitch]))


def test_top_octave_pad_plays_its_chord(pl09_image, pl09_manifest):
    """Stock plays keyboard pitches up to 139 - key: a chord's notes above 127 sound (PL01-PL04 dropped them)."""
    h = NoteHarness(pl09_image)
    h.track(0, NOTE_EXPANDED)
    set_chord(h, pl09_manifest, 0, settings(1))
    key, mask = h.r8(ROOT), h.r32(SCALE_MASK)
    pitch = next(p for p in range(126 - key, 0, -1) if in_scale(mask, p))   # the router snaps pads into the scale
    set_pitch(h, 0, 0, pitch)
    others = chord_notes(pitch, mask, settings(1, key=key))
    assert len(others) == 2 and max(others) > 127          # the triad's top notes lie above 127, below 139 - key
    want = sorted(endpoint_note(h, p) for p in [pitch] + others)
    h.take()
    h.down(0)
    assert sorted(e[2] for e in h.take("synth_on")) == want
    h.up(0)
    assert h.sounding == set()


def test_overlapping_chords_and_order_of_release(pl09_image, pl09_manifest):
    for first_up, second_up in ((24, 29), (29, 24)):
        h = NoteHarness(pl09_image)
        h.track(0)
        set_chord(h, pl09_manifest, 0, settings(2))
        h.down(24)
        h.down(29)
        h.up(first_up)
        h.up(second_up)
        assert h.sounding == set(), (first_up, h.sounding)


@pytest.mark.parametrize("button", [1, 9, 14, 15, 8])     # Synth 2, Note (mode toggle), Mixer, FX, Preset
def test_leaving_the_view_while_holding(pl09_image, pl09_manifest, button):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(3, bass=1))
    h.down(24)
    assert len(h.sounding) > 1
    h.press(button)                             # stock ends the held pad when the view changes (not for Note)
    h.up(24)
    assert h.sounding == set(), (button, h.sounding)
    h.track(0)
    h.up(24)                                    # a second, stale release does nothing
    assert h.sounding == set(), (button, h.sounding)


def test_table_full_plays_single_notes(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0, NOTE_EXPANDED)
    set_chord(h, pl09_manifest, 0, settings(1))
    pads = [24, 25, 26, 27, 28, 29, 30]                     # 7 held chords, the table holds 6
    for p in pads:
        h.take()
        h.down(p)
    assert len(h.take("synth_on")) == 1                     # the 7th press: the pad's own note only
    for p in pads:
        h.up(p)
    assert h.sounding == set()


def test_recording_receives_every_chord_note(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.recording(True)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(2))
    h.take()
    h.down(24)
    assert len(h.take("rec_on")) == 4
    h.up(24)


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_all_single_is_stock(seed, stock_image, pl09_image):
    a, b = Harness(stock_image), Harness(pl09_image)
    for i, step in enumerate(page_free(script(seed, 10))):
        run(a, step)
        run(b, step)
        assert a.outputs() == b.outputs(), f"seed {seed}, step {i} {step}"


GREEN, GREEN_DIM, BLUE, BLUE_DIM, MAGENTA, MAGENTA_DIM, ORANGE, ORANGE_DIM = 0x17, 0x18, 0x07, 0x08, 0x32, 0x38, 0x45, 0x46
WHITE = 0x01                                    # pad 24: rootless over bass (stock's playhead white)


def pick(h, pad):
    """A chord option by its PL09-PL14 palette number (pads 16-31): shapes 24-31 are Shift + Quick pads 16-23 now;
    inversion 16-19, spread 20-22 and bass 23 are on the Chords page (pads 16-23), opened and closed around the press."""
    if pad >= 24 or h.view_mode() not in (NOTE_DEFAULT, NOTE_EXPANDED):   # the Shift route (anywhere but a Note view: nothing)
        pad = pad - 8 if pad >= 24 else pad
        h.shift(True)
        h.down(pad)
        h.up(pad)
        h.shift(False)
        return
    mode = h.view_mode()
    h.press(h.cur, shift=True)
    h.down(pad)
    h.up(pad)
    h.press(h.cur)
    h.track(h.cur, mode)


def chord_byte(h, manifest, track):
    return h.r8(sym(manifest, "chord_settings") + track)


def rootless_bit(h, manifest, track):
    return h.r8(sym(manifest, "chord_rootless")) >> track & 1


@pytest.mark.parametrize("mode", [NOTE_DEFAULT, NOTE_EXPANDED])
def test_palette_sets_the_track_and_plays_nothing(pl09_image, pl09_manifest, mode):
    h = NoteHarness(pl09_image)
    h.track(1, mode)
    h.take()
    pick(h, 26)                                 # pad 27: 7th
    pick(h, 17)                                 # pad 18: inversion 1
    pick(h, 21)                                 # pad 22: drop-2
    pick(h, 23)                                 # pad 24: bass on
    assert h.take("synth_on", "synth_off", "midi_on", "midi_off") == []
    assert chord_byte(h, pl09_manifest, 1) == settings(2, inv=1, spread=1, bass=1)
    assert chord_byte(h, pl09_manifest, 0) == 0
    assert rootless_bit(h, pl09_manifest, 1) == 0
    pick(h, 23)                                 # bass below -> rootless over bass
    assert chord_byte(h, pl09_manifest, 1) == settings(2, inv=1, spread=1, bass=1)
    assert rootless_bit(h, pl09_manifest, 1) == 1 and rootless_bit(h, pl09_manifest, 0) == 0
    pick(h, 23)                                 # rootless -> no bass
    pick(h, 24)                                 # pad 25: single
    assert chord_byte(h, pl09_manifest, 1) == settings(0, inv=1, spread=1)
    assert rootless_bit(h, pl09_manifest, 1) == 0


def test_shift_on_the_top_rows_is_stock(pl09_image, stock_image):
    a, b = NoteHarness(stock_image), NoteHarness(pl09_image)
    for h in (a, b):
        h.track(0, NOTE_EXPANDED)
        h.take()
        h.shift(True)
        h.down(3)
        h.up(3)
        h.shift(False)
    assert [e[:3] for e in a.take("synth_on", "synth_off")] == [e[:3] for e in b.take("synth_on", "synth_off")]


def test_shift_released_before_the_pad(pl09_image):
    h = NoteHarness(pl09_image)
    h.track(0)
    h.take()
    h.shift(True)
    h.down(25)
    h.shift(False)
    h.up(25)                                    # a consumed pad: its release sends nothing
    assert h.take("synth_on", "synth_off") == []
    h.down(25)                                  # the next normal press plays again
    assert len(h.take("synth_on")) == 3         # triad
    h.up(25)
    assert h.sounding == set()


def test_shape_change_while_held_releases_what_was_played(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0, NOTE_EXPANDED)
    pick(h, 27)                                 # 9th: 5 notes
    h.down(0)                                   # top-left pad (not a palette pad), held
    assert len([k for k in h.sounding if k[0] == "synth"]) == 5
    pick(h, 25)                                 # triad while the 9th is held
    h.up(0)
    assert h.sounding == set()


def test_palette_leds_under_shift(pl09_image, pl09_manifest, stock_image):
    h, s = NoteHarness(pl09_image), NoteHarness(stock_image)
    for x in (h, s):
        x.track(0)
    pick(h, 26)
    pick(h, 18)
    h.shift(True)
    lit = h.leds()
    h.shift(False)
    assert lit[16:32] == [GREEN_DIM, GREEN_DIM, GREEN] + [GREEN_DIM] * 10 + [0, 0, 0]   # PL15: the shapes (the Quick view)
    h.press(0, shift=True)                      # voicing is on the Chords page, rows 3 (inversion, spread, bass)
    page = h.leds()
    h.press(0)
    assert page[16:20] == [BLUE_DIM, BLUE_DIM, BLUE, BLUE_DIM]
    assert page[20:23] == [MAGENTA, MAGENTA_DIM, MAGENTA_DIM]
    assert page[23] == ORANGE_DIM
    s.shift(True)
    ref = s.leds()
    s.shift(False)
    ours = set(range(32, 40)) | {53, 55}        # PL07: Shift-lit track buttons (PL16: and drums), the quick view's LED; PL08: Clear
    assert lit[:16] == ref[:16] and [x for i, x in enumerate(lit) if i >= 32 and i not in ours] == \
           [x for i, x in enumerate(ref) if i >= 32 and i not in ours]
    assert [lit[i] for i in range(32, 40)] == [x or 0x2C for x in ref[32:40]] and lit[53] == GREEN
    assert h.leds() == s.leds()                 # Shift released, nothing held: stock


def test_chord_notes_light_while_held(pl09_image, pl09_manifest, stock_image):
    s = NoteHarness(stock_image)
    s.track(0, NOTE_EXPANDED)
    s.down(8)
    ref = s.leds()
    assert ref[10] != ref[8] and ref[12] != ref[8]  # in stock only the pressed pad takes the pressed colour
    h = NoteHarness(pl09_image)
    h.track(0, NOTE_EXPANDED)
    pick(h, 25)                                 # triad
    h.down(8)                                   # second row, first pad: its triad's other notes are 2 and 4 pads right
    lit = h.leds()
    assert lit[10] == lit[8] and lit[12] == lit[8]
    assert [lit[p] for p in range(32) if p not in (8, 10, 12)] == [ref[p] for p in range(32) if p not in (8, 10, 12)]
    h.up(8)


def fuzz_script(seed: int, n: int = 24, strum: bool = False) -> list[tuple]:
    """Starts on a chord shape; `up` mostly lets go of a pad the script holds (fuzz_run skips the rest), so pads are
    released in every order, keys before steps included. With `strum`, Shift + 1-16/17-32 presses and heartbeats are
    mixed in; without it the scripts are the ones PL01 was tested with."""
    rnd = random.Random(seed)
    steps = [("pick", rnd.randrange(25, 32))]
    held = []
    if strum:                                   # one chord strummed in full on track 0 first: every strum script sounds notes
        key = rnd.randrange(16, 32)
        steps += [("down", key), ("ms", 120), ("up", key)]
    for _ in range(n):
        if strum and rnd.random() < 0.45:     # mostly heartbeats, long enough for slow gaps (80 ms) to pass
            steps.append(("strum",) if rnd.random() < 0.35 else ("ms", rnd.choice([1, 10, 30, 60, 120, 200])))
            continue
        r = rnd.random()
        if r < 0.15:
            steps.append(("track", rnd.randrange(4), rnd.choice([NOTE_DEFAULT, NOTE_EXPANDED])))
            if strum:                           # a new track has no chord shape yet: give it one
                steps.append(("pick", rnd.randrange(25, 32)))
        elif r < 0.30:
            steps.append(("pick", rnd.randrange(16, 32)))
        elif r < 0.65:
            pad = rnd.randrange(32)                     # all pads: in the 2-row view pads 1-16 are steps
            steps.append(("down", pad))
            if pad not in held:
                held.append(pad)
        elif r < 0.90:
            pad = rnd.choice(held) if held and rnd.random() < 0.8 else rnd.randrange(32)
            steps.append(("up", pad))
            if pad in held:
                held.remove(pad)
        else:
            steps.append(("view", rnd.choice(VIEW_BUTTONS)))
    return steps


def fuzz_run(h: NoteHarness, steps: list[tuple], strum: bool = False, stock: bool = False) -> int:
    """Runs the script; returns the number of note-ons that sounded during heartbeats (strummed notes). With `strum`,
    every track starts with strum slow, through the real control, so presses in the script cycle it on from there."""
    held = []                                   # in press order
    ons = 0
    speeds = [1, 1, 1, 1]
    track_now = 0

    def beat(n: int = 1) -> None:
        nonlocal ons
        start = len(h.log)
        h.heartbeat(n)
        ons += sum(1 for e in h.log[start:] if e[0].endswith("_on"))

    if strum:
        for t in range(4):
            h.track(t)
            set_strum_page(h, t, 1)
    h.track(0)
    for step in steps:
        if step[0] == "track":
            h.track(step[1], step[2])
            track_now = step[1]
        elif step[0] == "pick" and step[1] not in held:   # a held pad cannot go down a second time
            if stock:                           # stock has no page: the same Shift + pad press
                h.shift(True)
                h.down(step[1])
                h.up(step[1])
                h.shift(False)
            else:
                pick(h, step[1])
        elif step[0] == "down" and step[1] not in held:
            h.down(step[1])
            held.append(step[1])
        elif step[0] == "up" and step[1] in held:
            h.up(step[1])
            held.remove(step[1])
        elif step[0] == "strum":
            speeds[track_now] = (speeds[track_now] + 1) & 3
            if not stock:                       # stock has no page: the speed pad would only be one more stock pad press
                set_strum_page(h, track_now, speeds[track_now])
        elif step[0] == "ms":
            beat(step[1])
        elif step[0] == "view":
            h.press(step[1])
    for pad in held:                            # let go of everything in press order, wherever the device now is
        h.up(pad)
    beat()                                      # strummed chords end on the next heartbeat
    return ons


@pytest.mark.parametrize("seed", range(1, 33))     # seeds 1 and 25 caught the F1 stuck notes on the first PL01
def test_no_note_is_left_on(seed, pl09_image, pl09_manifest, stock_image):
    steps = fuzz_script(seed)
    s = NoteHarness(stock_image)
    fuzz_run(s, steps, stock=True)
    assert s.sounding == set(), f"stock itself leaves notes on for seed {seed}: the script is invalid"
    h = NoteHarness(pl09_image)
    fuzz_run(h, steps)
    assert h.sounding == set(), f"seed {seed}: {sorted(h.sounding)} left on; script {steps}"
    assert held_counts(h, pl09_manifest) == [0] * HELD, f"seed {seed}: chord entries left; script {steps}"


@pytest.mark.parametrize("seed", range(1, 25))
def test_no_note_is_left_on_with_strum(seed, pl09_image, pl09_manifest, stock_image):
    steps = fuzz_script(seed, strum=True)
    assert any(s[0] == "strum" for s in steps) and any(s[0] == "ms" for s in steps), steps
    s = NoteHarness(stock_image)
    fuzz_run(s, steps, strum=True, stock=True)
    assert s.sounding == set(), f"stock itself leaves notes on for seed {seed}: the script is invalid"
    h = NoteHarness(pl09_image)
    ons = fuzz_run(h, steps, strum=True)
    assert ons > 0, f"seed {seed}: no strummed note sounded, the script proves nothing; script {steps}"
    print(f"strum seed {seed}: {ons} heartbeat note-ons")
    assert h.sounding == set(), f"seed {seed}: {sorted(h.sounding)} left on; script {steps}"
    assert held_counts(h, pl09_manifest) == [0] * HELD, f"seed {seed}: chord entries left; script {steps}"


@pytest.mark.parametrize("seed", range(1, 9))
def test_no_note_is_left_on_with_falling_strum(seed, pl09_image, pl09_manifest):
    """The strum fuzz with every track strumming falling (PL08; the stock check is the rising fuzz's)."""
    steps = fuzz_script(seed, strum=True)
    h = NoteHarness(pl09_image)
    for t in range(4):
        set_down(h, pl09_manifest, t)
    ons = fuzz_run(h, steps, strum=True)
    assert ons > 0, f"seed {seed}: no strummed note sounded; script {steps}"
    assert h.r8(sym(pl09_manifest, "chord_strum_down")) == 0xF
    assert h.sounding == set(), f"seed {seed}: {sorted(h.sounding)} left on; script {steps}"
    assert held_counts(h, pl09_manifest) == [0] * HELD, f"seed {seed}: chord entries left; script {steps}"


@pytest.mark.parametrize("seed", range(1, 17))
def test_no_note_is_left_on_with_step_chords(seed, pl18_image, pl18_manifest):
    """PL18: every track writes chords in step entry (chord_step = 0xF): the fuzz's step pads (0-15 in the two-row
    view) and key pads go down and up in every order, so chords are added to held steps and taken out again. Stock's
    run of the same scripts is test_no_note_is_left_on's."""
    steps = fuzz_script(seed)
    h = NoteHarness(pl18_image)
    h.call(sym(pl18_manifest, "slim_ready"))
    h.uc.mem_write(sym(pl18_manifest, "chord_step"), b"\x0f")
    before = pattern_snapshot(h, 0)
    fuzz_run(h, steps)
    print(f"step chords seed {seed}: {len(recorded_notes(h, 0, before))} track 0 units written")
    assert h.sounding == set(), f"seed {seed}: {sorted(h.sounding)} left on; script {steps}"
    assert held_counts(h, pl18_manifest) == [0] * HELD, f"seed {seed}: chord entries left; script {steps}"


@pytest.mark.parametrize("order", ["chord_first", "step_first"])
def test_chord_released_while_a_step_is_held(pl09_image, pl09_manifest, order):
    """Stock's release handler 0x0804ACC4 only clears a key's slot when a held step contains its pitch (the step's
    release ends the root), so the chord's other notes must be ended at the release handler itself."""
    h = NoteHarness(pl09_image)
    h.track(0)                                  # 2-row view: pads 0-15 are steps
    set_chord(h, pl09_manifest, 0, settings(1))
    h.down(24)
    h.down(0)                                   # hold a step: it takes the held key's root
    assert len([k for k in h.sounding if k[0] == "synth"]) >= 3   # the triad (and whatever the step previews)
    for pad in ((24, 0) if order == "chord_first" else (0, 24)):
        h.up(pad)
    assert h.sounding == set(), (order, sorted(h.sounding))
    assert held_counts(h, pl09_manifest) == [0] * HELD


@pytest.mark.parametrize("mode, pads", [(NOTE_DEFAULT, (16, 31)), (NOTE_EXPANDED, (8, 23))])
@pytest.mark.parametrize("first_up", [0, 1])
def test_same_pitch_pads(pl09_image, pl09_manifest, mode, pads, first_up):
    """Two pads with one pitch: stock's note start clears the first pad's slot (0x0804AF2C), so its release never
    reaches the note-off; the chord feature must still end that pad's chord and free its entry."""
    h = NoteHarness(pl09_image)
    h.track(0, mode)
    set_chord(h, pl09_manifest, 0, settings(1))
    assert h.pitch(0, pads[0]) == h.pitch(0, pads[1])
    before = h.leds()
    h.down(pads[0])
    h.down(pads[1])
    h.up(pads[first_up])
    h.up(pads[1 - first_up])
    assert h.sounding == set(), (mode, pads, first_up, sorted(h.sounding))
    assert held_counts(h, pl09_manifest) == [0] * HELD
    assert h.leds() == before


SAME_PITCH = [(NOTE_DEFAULT, (16, 31)), (NOTE_EXPANDED, (8, 23))]


def unbalanced(events):
    """{note key: note-ons minus note-offs} for every key that is not even. Counts, not `sounding` (a set): two note-ons
    of one pitch and one note-off leave a set empty but a voice or an external synth's note hanging."""
    count = {}
    for e in events:
        key = ("synth", e[1], e[2]) if e[0].startswith("synth") else ("midi", e[2], e[3])
        count[key] = count.get(key, 0) + (1 if e[0].endswith("_on") else -1)
    return {k: n for k, n in count.items() if n}


ENDS = ("synth_on", "synth_off", "midi_on", "midi_off")


@pytest.mark.parametrize("image", ["stock_image", "pl21_image"])
@pytest.mark.parametrize("track", [0, 2])
@pytest.mark.parametrize("mode, pads", SAME_PITCH)
@pytest.mark.parametrize("first_up", [0, 1])
def test_same_pitch_pads_without_a_chord_end_every_note(request, image, track, mode, pads, first_up):
    """The stuck note of upstream RC2.06 (`tools/dupnote.py`; their user, on the device: pads 17 and 32 held together,
    the note did not stop). Upstream's reading: the second press clears the first pad's slot without a note-off, so
    two note-ons meet one note-off. With stock's real router (0x08031DA4) the endpoints say otherwise: the second
    press ends the sounding note and sounds it again (off, then on), the first pad's release then sends nothing, the
    last release ends it. Every note-on at the synth and MIDI-out endpoints gets its note-off, in stock and in CTPlay
    with no chord shape. So MIDI out cannot hang here; a stuck voice could only come from the DSP side of an off and an
    on of one note sent together, which emulation does not run (a device question). Counts, not `sounding`."""
    h = NoteHarness(request.getfixturevalue(image))
    h.track(track, mode)
    assert h.pitch(track, pads[0]) == h.pitch(track, pads[1])
    h.take()
    h.down(pads[0])
    first = h.take(*ENDS)
    assert [e[0] for e in first] == (["synth_on", "midi_on"] if track < 2 else ["midi_on"])
    h.down(pads[1])
    second = h.take(*ENDS)
    assert [e[0] for e in second] == (["synth_off", "midi_off", "synth_on", "midi_on"] if track < 2
                                      else ["midi_off", "midi_on"])
    h.up(pads[first_up])
    h.up(pads[1 - first_up])
    releases = h.take(*ENDS)
    assert len(releases) == (2 if track < 2 else 1)
    assert unbalanced(first + second + releases) == {} and h.sounding == set()


# ---- re-sound shared notes (PL05)

def free_velocity(h, track):
    """The dump has fixed velocity on: turn it off (as in test_chord_notes_take_the_pad_velocity)."""
    h.call(PARAM_GET, h.r32(h.note_view(track) + 0x28), 2)
    flags = h.uc.reg_read(UC_ARM_REG_R0)
    h.uc.mem_write(flags, bytes([h.r8(flags) & ~2]))


def overlapping_pad(h, track, s, shared, first=24):
    """Another key pad (17-32) whose triad overlaps pad `first`'s: "later_root" = its own note is in the first chord,
    "earlier_root" = its chord holds the first pad's own note. Returns (pad, first notes, its notes) at the endpoints."""
    mask = h.r32(SCALE_MASK)
    a = h.pitch(track, first)
    ca = chord_notes(a, mask, s | h.r8(ROOT) << 16)
    for q in (p for p in range(16, 32) if p != first):
        b = h.pitch(track, q)
        cb = chord_notes(b, mask, s | h.r8(ROOT) << 16)
        if (b in ca) if shared == "later_root" else (a in cb):
            return q, {endpoint_note(h, p) for p in [a, *ca]}, {endpoint_note(h, p) for p in [b, *cb]}
    raise AssertionError(f"no pad overlaps pad {first} ({shared})")


def synth_notes(h):
    return {k[2] for k in h.sounding if k[0] == "synth"}


@pytest.mark.parametrize("shared", ["later_root", "earlier_root"])
@pytest.mark.parametrize("speed", [0, 3])
def test_releasing_the_later_chord_re_sounds_the_shared_notes(pl09_image, pl09_manifest, shared, speed):
    """The router keeps one owner pad per pitch: the later chord took the shared notes, so its release ended them.
    PL05 sends them again from the earlier pad, at its velocity, and the earlier release still ends everything."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(1))
    set_strum(h, pl09_manifest, 0, speed)
    free_velocity(h, 0)
    a = 24 if shared == "later_root" else 28              # pad 24 is the lowest key: no other triad holds its note
    q, first, second = overlapping_pad(h, 0, settings(1), shared, a)
    h.down(a, 70)
    h.heartbeat(5 * GAP[3])
    h.down(q, 110)
    h.heartbeat(5 * GAP[3])
    assert synth_notes(h) == first | second
    h.take()
    h.up(q)
    h.heartbeat(2)
    assert synth_notes(h) == first, (shared, speed, sorted(synth_notes(h)), sorted(first))
    again = h.take("synth_on")
    assert {e[2] for e in again} == first & second and {e[3] for e in again} == {70}
    h.up(a)
    h.heartbeat(2)
    assert h.sounding == set(), sorted(h.sounding)
    assert held_counts(h, pl09_manifest) == [0] * HELD


@pytest.mark.parametrize("speed", [0, 3])
def test_releasing_the_earlier_chord_keeps_the_later_one(pl09_image, pl09_manifest, speed):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(1))
    set_strum(h, pl09_manifest, 0, speed)
    q, first, second = overlapping_pad(h, 0, settings(1), "later_root")
    h.down(24)
    h.heartbeat(5 * GAP[3])
    h.down(q)
    h.heartbeat(5 * GAP[3])
    h.up(24)
    h.heartbeat(2)
    assert synth_notes(h) == second
    h.up(q)
    h.heartbeat(2)
    assert h.sounding == set(), sorted(h.sounding)


def test_same_pitch_pads_re_sound_the_first_pads_note(pl09_image, pl09_manifest):
    """Pads 17 and 32 share a pitch: the later press takes it (stock clears the first pad's slot, so stock will not end
    the first pad's note). PL05 re-sounds it on the later release and ends it itself on the first pad's release."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(1))
    assert h.pitch(0, 16) == h.pitch(0, 31)
    h.down(16)
    chord = synth_notes(h)
    h.down(31)
    h.up(31)
    assert synth_notes(h) == chord
    h.up(16)
    assert h.sounding == set(), sorted(h.sounding)
    assert held_counts(h, pl09_manifest) == [0] * HELD


def test_heartbeat_re_sound_undone_when_the_owner_went_meanwhile(pl09_image, pl09_manifest):
    """A strummed chord's release re-sounds in the Main task while the UI task may be releasing the owner: here the
    owner (a one-burst chord, pressed before strum was turned on) is freed between the heartbeat's check and its
    note-on. The heartbeat must see that and end the note it just sent."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(1))
    q, first, second = overlapping_pad(h, 0, settings(1), "later_root")
    h.down(24)                                                         # one burst
    set_strum(h, pl09_manifest, 0, 3)
    h.down(q)                                                          # strummed
    h.heartbeat(5 * GAP[3])
    base = sym(pl09_manifest, "held")
    owner = next(base + HELD_SIZE * i for i in range(HELD) if h.r8(base + HELD_SIZE * i) and h.r8(base + HELD_SIZE * i + 2) == 24)
    h.up(q)                                                            # stock ends q's own note now; the heartbeat the rest
    caught = []

    def ui_release(uc, address, size, data):                           # "the UI task" frees the owner mid-re-sound
        if not caught:
            caught.append(uc.reg_read(UC_ARM_REG_R1))                  # the re-sent note
            uc.mem_write(owner, b"\0")
    hook = h.uc.hook_add(UC_HOOK_CODE, ui_release, begin=SYNTH_ON, end=SYNTH_ON)
    h.take()
    h.heartbeat(2)
    h.uc.hook_del(hook)
    assert caught and caught[0] in first & second, ("the heartbeat re-sounded nothing shared", caught)
    assert caught[0] not in synth_notes(h), sorted(synth_notes(h))
    assert caught[0] in {e[2] for e in h.take("synth_off")}


# ---- strum (spec 2026-10-12-strum-design.md)

@pytest.mark.parametrize("speed", [1, 2, 3])
@pytest.mark.parametrize("shape, bass", [(3, 1), (0, 1), (1, 0)])   # 9th + bass (5 other notes), single + bass (1), triad (2)
def test_strum_order_and_timing(pl09_image, pl09_manifest, speed, shape, bass):
    h = NoteHarness(pl09_image)
    h.track(0)
    s = settings(shape, bass=bass)
    set_chord(h, pl09_manifest, 0, s)
    set_strum(h, pl09_manifest, 0, speed)
    root = h.pitch(0, 24)
    others = sorted(endpoint_note(h, p) for p in chord_notes(root, h.r32(SCALE_MASK), s))
    h.take()
    h.down(24, 100)
    first = h.take("synth_on")
    assert [e[2] for e in first] == [endpoint_note(h, root)]          # the press: the pad's own note only
    got = []
    for t in range(1, GAP[speed] * len(others) + 1):
        h.heartbeat()
        got += [(t, e[2], e[3]) for e in h.take("synth_on")]
    assert got == [(GAP[speed] * (k + 1), n, first[0][3]) for k, n in enumerate(others)]   # rising, the root's velocity
    h.heartbeat(3 * GAP[speed])
    assert h.take("synth_on") == []                                    # nothing more
    h.up(24)
    h.heartbeat()
    assert h.sounding == set()
    assert held_counts(h, pl09_manifest) == [0] * HELD


@pytest.mark.parametrize("speed, gap", [(1, 80), (2, 40), (3, 20)])   # slow, medium, fast (PL08; were 50 / 25 / 10)
def test_strum_gaps_are_20_40_80(pl09_image, pl09_manifest, speed, gap):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(1, bass=0))
    set_strum(h, pl09_manifest, 0, speed)
    h.take()
    h.down(24, 100)
    times = [0] * len(h.take("synth_on"))
    for t in range(1, 3 * gap + 1):
        h.heartbeat()
        times += [t] * len(h.take("synth_on"))
    assert times == [0, gap, 2 * gap]
    h.up(24)
    h.heartbeat()
    assert h.sounding == set()


# ---- falling strum (spec 2026-10-17-small-features-design.md D4, section 2)

def falling(h, manifest, shape, bass=0, rootless=0, speed=1, track=0):
    """Track `track` strums falling; returns every note of pad 24's chord (the pad's own included), highest first."""
    h.track(track)
    set_chord(h, manifest, track, settings(shape, bass=bass))
    if rootless:
        h.uc.mem_write(sym(manifest, "chord_rootless"), bytes([1 << track]))
    set_strum(h, manifest, track, speed)
    set_down(h, manifest, track)
    root = h.pitch(track, 24)
    others = chord_notes(root, h.r32(SCALE_MASK), settings(shape, bass=bass, rootless=rootless))
    return sorted((endpoint_note(h, p) for p in others + [root]), reverse=True)


@pytest.mark.parametrize("speed", [1, 3])
@pytest.mark.parametrize("shape, bass, rootless", [(1, 0, 0), (2, 0, 0), (3, 0, 0), (1, 1, 0), (3, 1, 0), (3, 1, 1)])
def test_falling_strum_plays_highest_first(pl09_image, pl09_manifest, speed, shape, bass, rootless):
    h = NoteHarness(pl09_image)
    every = falling(h, pl09_manifest, shape, bass, rootless, speed)
    h.take()
    h.down(24, 100)
    assert h.take("synth_on") == []                                    # the press sends nothing: the heartbeat does
    got = []
    for t in range(1, GAP[speed] * len(every) + 1):
        h.heartbeat()
        got += [(t, e[2], e[3]) for e in h.take("synth_on")]
    assert [n for _, n, _ in got] == every                             # each once, highest first, the bass last
    assert [t for t, _, _ in got] == [1 + GAP[speed] * k for k in range(len(every))]
    assert len({v for _, _, v in got}) == 1                            # the pad's velocity
    h.heartbeat(3 * GAP[speed])
    assert h.take("synth_on") == []
    h.up(24)
    h.heartbeat()
    assert h.sounding == set()
    assert held_counts(h, pl09_manifest) == [0] * HELD


@pytest.mark.parametrize("sounded", [0, 1, 2, 4])                    # 9th + bass below: 9th, 7th, 3rd, the pad, bass
def test_falling_strum_release_mid_strum(pl09_image, pl09_manifest, sounded):
    h = NoteHarness(pl09_image)
    every = falling(h, pl09_manifest, 3, bass=1)
    assert len(every) == 5
    h.down(24)
    if sounded:
        h.heartbeat(1 + GAP[1] * (sounded - 1))
    assert sorted(k[2] for k in h.sounding if k[0] == "synth") == sorted(every[:sounded])
    h.take()
    h.up(24)
    h.heartbeat()
    assert h.sounding == set(), sorted(h.sounding)
    h.heartbeat(6 * GAP[1])
    assert h.take("synth_on") == [] and h.sounding == set()           # unsent notes never sound
    assert held_counts(h, pl09_manifest) == [0] * HELD


def test_falling_strum_repressed_and_rising_again(pl09_image, pl09_manifest):
    """A falling chord cut by a press of the same pad, then the direction set back: rising as PL07."""
    h = NoteHarness(pl09_image)
    every = falling(h, pl09_manifest, 1)
    h.down(24)
    h.heartbeat(1 + GAP[1])
    h.up(24)
    h.down(24)                                                         # before any heartbeat
    h.heartbeat(3 * GAP[1] + 1)
    assert sorted(k[2] for k in h.sounding if k[0] == "synth") == sorted(every)
    h.up(24)
    h.heartbeat()
    assert h.sounding == set()
    set_down(h, pl09_manifest, 0, False)
    h.take()
    h.down(24)
    assert [e[2] for e in h.take("synth_on")] == [endpoint_note(h, h.pitch(0, 24))]   # rising: the pad's own first
    h.up(24)
    h.heartbeat()
    assert h.sounding == set()


@pytest.mark.parametrize("how", ["release", "repress", 1, 9, 14, 15, 8])   # pad up, up + down again, view switches
def test_strum_cut_short(pl09_image, pl09_manifest, how):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(3, bass=1))
    set_strum(h, pl09_manifest, 0, 1)
    h.down(24)
    h.heartbeat(2 * GAP[1])                                            # the root and two other notes sound
    assert len([k for k in h.sounding if k[0] == "synth"]) == 3
    h.take()
    if how == "release":
        h.up(24)
    elif how == "repress":
        h.up(24)
        h.down(24)                                                     # before any heartbeat
        assert len(h.take("synth_on")) == 1                            # the new press's root (stock)
    else:
        h.press(how)                                                   # stock releases the held pad (not for Note)
    h.heartbeat()                                                      # the heartbeat ends the sounded notes
    ons = [e[2] for e in h.take("synth_on")]
    if how == "repress":
        assert ons == [] and len([k for k in h.sounding if k[0] == "synth"]) == 1     # only the new press's root
        h.up(24)
        h.heartbeat()
    elif how == 9:
        h.up(24)                                                       # Note toggles the view mode: stock keeps the pad
        h.heartbeat()
    assert h.sounding == set(), (how, sorted(h.sounding))
    h.heartbeat(5 * GAP[1])
    assert h.take("synth_on") == [] and h.sounding == set(), how       # no note of the cut chord comes later
    if how not in ("release", "repress", 9):
        h.track(0)
        h.up(24)                                                       # a second, stale release does nothing
        h.heartbeat()
        assert h.sounding == set(), how
    assert held_counts(h, pl09_manifest) == [0] * HELD


def test_strummed_chords_released_and_pressed_between_heartbeats(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(1))
    set_strum(h, pl09_manifest, 0, 3)
    pads = [24, 25, 26, 27, 28, 29]                                    # fills the table
    for p in pads:
        h.down(p)
    h.heartbeat(3 * GAP[3])
    for p in pads:
        h.up(p)                                                        # released, not yet freed
    for p in pads:
        h.down(p)                                                      # the table is still full: roots only
    h.heartbeat(3 * GAP[3])
    for p in pads:
        h.up(p)
    h.heartbeat()
    assert h.sounding == set(), sorted(h.sounding)
    assert held_counts(h, pl09_manifest) == [0] * HELD


def test_recording_receives_every_strummed_note(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.recording(True)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(2))                        # 7th: the root + 3 other notes
    set_strum(h, pl09_manifest, 0, 3)
    h.take()
    h.down(24)
    assert len(h.take("rec_on")) == 1                                  # the root, on the press
    h.heartbeat(3 * GAP[3])
    assert len(h.take("rec_on")) == 3                                  # each strummed note, from the Main task
    h.up(24)
    h.heartbeat()


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_heartbeat_without_strum_is_stock(seed, stock_image, pl09_image):
    a, b = Harness(stock_image), Harness(pl09_image)
    for i, step in enumerate(page_free(script(seed, 8))):
        for x in (a, b):
            run(x, step)
            x.heartbeat(5)
        assert a.outputs() == b.outputs(), f"seed {seed}, step {i} {step}"


BTN_PAGE, LED_PAGE = 21, 53


def set_strum_page(h, track, speed):
    """Strum through the Chords page (PL07): Shift + the track's button, ▲, the strum row's pad, the track's button.
    Harmless on stock (Shift + a track button does nothing there; the pad plays and ends a note)."""
    mode = h.view_mode()
    h.press(track, shift=True)
    h.press(20)
    h.press(20)                                                        # ▲ ▲ to the Chords page, from any page (no wrap)
    pad = 26 + speed if speed else 29                                  # PL15: pads 28-30; the lit one again = off (the fuzz goes 3 -> 0)
    h.down(pad)
    h.up(pad)
    h.press(track)
    if mode in (NOTE_DEFAULT, NOTE_EXPANDED):                          # another track view: no page opened, nothing to restore
        h.track(track, mode)


def test_stock_ignores_shift_page(stock_image):
    """Spec section 3: the press slim takes is one stock drops (Shift mask), and its release does nothing either."""
    h = Harness(stock_image)
    before = h.outputs()
    h.press(BTN_PAGE, shift=True)
    assert h.outputs() == before


def test_page_button_without_shift_is_stock(pl09_image, stock_image):
    a, b = NoteHarness(stock_image), NoteHarness(pl09_image)
    for h in (a, b):
        h.track(0)
        h.press(BTN_PAGE)
    assert a.outputs() == b.outputs()


def test_page_button_outside_the_note_view_is_stock(pl09_image, pl09_manifest, stock_image):
    a, b = NoteHarness(stock_image), NoteHarness(pl09_image)
    for h in (a, b):
        h.press(14)                                                    # Mixer
        h.press(BTN_PAGE, shift=True)
    assert a.outputs() == b.outputs()
    assert strum_byte(b, pl09_manifest) == 0


def test_strummed_chord_lights_only_sounded_notes(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0, NOTE_EXPANDED)
    set_chord(h, pl09_manifest, 0, settings(1))
    set_strum(h, pl09_manifest, 0, 1)                                  # slow
    h.down(8)                                                          # its triad's other notes: 2 and 4 pads right
    lit = h.leds()
    assert lit[10] != lit[8] and lit[12] != lit[8]
    h.heartbeat(GAP[1])
    lit = h.leds()
    assert lit[10] == lit[8] and lit[12] != lit[8]
    h.heartbeat(GAP[1])
    lit = h.leds()
    assert lit[10] == lit[8] and lit[12] == lit[8]
    h.up(8)
    h.heartbeat()


def test_strum_setting_change_while_held(pl09_image, pl09_manifest):
    """The held chord keeps its own speed and release path: the setting is read at the press only."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(3, bass=1))
    set_strum(h, pl09_manifest, 0, 1)                                  # slow
    h.take()
    h.down(24)
    h.heartbeat(GAP[1])
    assert len(h.take("synth_on")) == 2                                # the root and the first other note
    set_strum(h, pl09_manifest, 0, 0)                                  # off while the chord is held
    h.heartbeat(GAP[1] - 1)
    assert h.take("synth_on") == []                                    # still the slow gap
    h.heartbeat()
    assert len(h.take("synth_on")) == 1
    h.up(24)
    h.heartbeat()
    assert h.sounding == set()
    assert held_counts(h, pl09_manifest) == [0] * HELD


# ---- bass modes (pad 24: no bass / bass below / rootless over bass)

def test_bass_pad_led_shows_the_three_modes(pl09_image):
    h = NoteHarness(pl09_image)
    h.track(0)
    got = []
    for _ in range(3):
        h.press(0, shift=True)                  # PL15: the bass pad is on the Chords page
        got.append(h.leds()[23])
        h.press(0)
        h.track(0)
        pick(h, 23)
    assert got == [ORANGE_DIM, ORANGE, WHITE]


@pytest.mark.parametrize("mode", [NOTE_DEFAULT, NOTE_EXPANDED])
def test_rootless_over_bass_through_the_pads(pl09_image, pl09_manifest, mode):
    """The pad's own note is the bass; the chord sits an octave up without its root; nothing is left on."""
    h = NoteHarness(pl09_image)
    h.track(0, mode)
    pick(h, 27)                                 # 9th
    pick(h, 23)
    pick(h, 23)                                 # rootless over bass
    root = h.pitch(0, 24)
    want = sorted(endpoint_note(h, p) for p in [root] + chord_notes(root, h.r32(SCALE_MASK), settings(3, bass=1, rootless=1)))
    h.take()
    h.down(24)
    got = sorted(e[2] for e in h.take("synth_on"))
    assert got == want and len(got) == 5, (got, want)
    assert all((n - endpoint_note(h, root)) % 12 for n in got if n != endpoint_note(h, root))
    h.up(24)
    assert h.sounding == set()


def test_bass_below_leaves_out_the_fifth_of_a_ninth(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    pick(h, 27)                                 # 9th
    pick(h, 23)                                 # bass below
    h.take()
    h.down(24)
    assert len(h.take("synth_on")) == 5         # root, bass, 3rd, 7th, 9th
    h.up(24)
    assert h.sounding == set()


def test_rootless_strum_rises_from_the_pad(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    pick(h, 26)                                 # 7th
    pick(h, 23)
    pick(h, 23)                                 # rootless over bass
    set_strum(h, pl09_manifest, 0, 3)
    h.take()
    h.down(24)
    pad_note = [e[2] for e in h.take("synth_on")]
    h.heartbeat(3 * GAP[3])
    rest = [e[2] for e in h.take("synth_on")]
    assert len(pad_note) == 1 and len(rest) == 3 and rest == sorted(rest) and rest[0] > pad_note[0], (pad_note, rest)
    h.up(24)
    h.heartbeat()
    assert h.sounding == set()


def test_bass_mode_change_while_held(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0, NOTE_EXPANDED)
    pick(h, 27)                                 # 9th
    pick(h, 23)                                 # bass below
    h.down(0)                                   # top-left pad (not a palette pad), held
    assert len([k for k in h.sounding if k[0] == "synth"]) == 5
    pick(h, 23)                                 # rootless over bass while the chord is held
    h.up(0)
    assert h.sounding == set()
    assert held_counts(h, pl09_manifest) == [0] * HELD


@pytest.mark.parametrize("rootless", [False, True])
@pytest.mark.parametrize("speed", [0, 1])
@pytest.mark.parametrize("pad", [17, 24])
def test_bass_modes_end_no_note_before_the_release(pl09_image, pl09_manifest, rootless, speed, pad):
    """PL03 device step 7 (rootless, slow strum: the bass dropped): slim's side sends all 5 notes and ends none until
    the release, so a lost note is the synth's voice stealing (investigations/2026-10-12-chord-voice-dropouts.md)."""
    h = NoteHarness(pl09_image)
    h.track(0)
    pick(h, 27)                                 # 9th
    pick(h, 23)                                 # bass below
    if rootless:
        pick(h, 23)
    set_strum(h, pl09_manifest, 0, speed)
    h.take()
    h.down(pad)
    h.heartbeat(5 * GAP[1])
    log = h.take("synth_on", "synth_off")
    assert [e[0] for e in log] == ["synth_on"] * 5, log
    h.up(pad)
    h.heartbeat()
    assert h.sounding == set()


def test_degree_class_matches_the_model(pl09_image, pl09_manifest):
    h = Harness(pl09_image)
    bad = []
    for mask in (0, *emu_sc08.MASKS):
        for root in range(48, 60):
            for degree in range(9):
                h.call(sym(pl09_manifest, "chord_degree_class"), root, mask, degree)
                got = h.uc.reg_read(UC_ARM_REG_R0)
                if got != degree_class(root, mask, degree):
                    bad.append((hex(mask), root, degree, got))
    assert not bad, bad[:5]


# ---- PL15 Task 4: the new shapes everywhere, voice leading on a press ----

def set_voice(h, manifest, track, value):
    """chord_voice (row-2 shape | voice leading << 4) straight in RAM, until the Chords page's pads exist."""
    h.call(sym(manifest, "slim_ready"))
    h.uc.mem_write(sym(manifest, "chord_voice") + track, bytes([value]))


def press_notes(h, pad, vel=100):
    """The pad's note-ons (synth) in order, as (note, velocity)."""
    h.take()
    h.down(pad, vel)
    return [(e[2], e[3]) for e in h.take("synth_on")]


def test_row1_chords_play_as_pl14(pl15_image, pl15_manifest, pl14_published_image, pl14_published_manifest):
    """The anti-goal: voice leading off and a row-1 shape, every setting and several pads play exactly as PL14."""
    rng = random.Random(1504)
    runs = []
    for image, manifest in ((pl15_image, pl15_manifest), (pl14_published_image, pl14_published_manifest)):
        h = NoteHarness(image)
        h.track(0)
        out = []
        for i, s in enumerate(SETTINGS_ALL):
            set_chord(h, manifest, 0, s & 0xFF)
            h.uc.mem_write(sym(manifest, "chord_rootless"), bytes([s >> 8 & 1]))
            for pad in (24, 17 + (i * 5) % 15):
                out.append((s, pad, press_notes(h, pad)))
                h.up(pad)
            assert h.sounding == set()
        runs.append(out)
    assert runs[0] == runs[1]
    assert any(len(n) > 1 for _, _, n in runs[0])


@pytest.mark.parametrize("shape2", [1, 2, 3, 4, 5])
def test_new_shapes_play(pl15_image, pl15_manifest, shape2):
    h = NoteHarness(pl15_image)
    h.track(0)
    set_voice(h, pl15_manifest, 0, shape2)
    root, key, mask = h.pitch(0, 24), h.r8(ROOT), h.r32(SCALE_MASK)
    for inv, bass in ((0, 0), (1, 1)):
        set_chord(h, pl15_manifest, 0, settings(0, inv, 1, bass) & 0xFF)
        want = [endpoint_note(h, p) for p in [root] + chord_notes(root, mask, settings(0, inv, 1, bass, 0, key, shape2))]
        got = [n for n, _ in press_notes(h, 24)]
        assert sorted(got) == sorted(want) and len(got) > 1, (shape2, inv, bass, got, want)
        h.up(24)
        assert h.sounding == set()


def test_new_shapes_in_the_arpeggio_and_strum(pl15_image, pl15_manifest):
    from test_arp import due, set_arp
    h = NoteHarness(pl15_image)
    h.track(0)
    set_voice(h, pl15_manifest, 0, 1)                                    # power: root, 5th, octave
    root, key, mask = h.pitch(0, 24), h.r8(ROOT), h.r32(SCALE_MASK)
    want = sorted(endpoint_note(h, p) for p in [root] + chord_notes(root, mask, settings(0, key=key, shape2=1)))
    assert len(want) == 3
    set_arp(h, pl15_manifest, 0, 1 | 2 << 3)                             # up, 1/16
    h.take()
    h.down(24)
    times = due(h, pl15_manifest, 6, 1100)[:6]
    from notes import ms_log
    got = [n for _, k, n in ms_log(h, times[-1]) if k == "synth_on"]
    assert got == want * 2
    h.up(24)
    h.heartbeat(200)
    assert h.sounding == set()
    set_arp(h, pl15_manifest, 0, 0)
    set_strum(h, pl15_manifest, 0, 3)
    h.take()
    h.down(24)
    got = [e[2] for e in h.take("synth_on")]
    for _ in range(3 * 20):
        h.heartbeat()
        got += [e[2] for e in h.take("synth_on")]
    assert got == want
    h.up(24)
    h.heartbeat()
    assert h.sounding == set()


def test_pattern_tools_write_and_the_melody_pool_use_the_new_shapes(pl15_image, pl15_manifest):
    import euclid_model
    import melody_model
    from test_melody import T, configure
    from test_euclid import expected_steps, open_tools, steps, write
    h = NoteHarness(pl15_image)
    h.leds()
    h.track(T)
    root = h.pitch(T, 24)
    open_tools(h, T)
    mask, key = h.r32(SCALE_MASK), h.r8(ROOT)
    for shape2 in (1, 3, 5):
        configure(h, pl15_manifest, k=8, last=root, shape=0)
        h.uc.mem_write(sym(pl15_manifest, "chord_voice") + T, bytes([shape2]))
        write(h)
        notes = [root] + chord_notes(root, mask, settings(0, key=key, shape2=shape2))
        assert steps(h, T) == expected_steps(euclid_model.mask(8, 16, 0), 16, 0, notes, 2, 96), shape2
        # the melody's chord pool (order "up", pool kind chord)
        h.uc.mem_write(OUTBUF, bytes([1 | 1 << 4, 1, 16, 0, 0]) + bytes(24) + b"\xEE")
        h.call(sym(pl15_manifest, "melody_pool"), OUTBUF, root, mask, settings(0, key=key, shape2=shape2))
        pn, at = h.uc.mem_read(OUTBUF + 3, 2)
        want = melody_model.pool(1 | 1 << 4, root, mask, settings(0, key=key, shape2=shape2))
        assert (list(h.uc.mem_read(OUTBUF + 5, pn)), at) == want[:2], shape2


def pads_for_classes(h, track, classes):
    """For each pitch class (relative to the key) the pad whose pitch is the lowest at or above 60."""
    out = []
    for c in classes:
        cands = [(h.pitch(track, p), p) for p in range(16, 32) if h.pitch(track, p) % 12 == c and h.pitch(track, p) >= 60]
        out.append(min(cands)[1])
    return out


def lead_chord(h, pad, s, prev, kind):
    root, mask = h.pitch(0, pad), h.r32(SCALE_MASK)
    inv = lead(root, mask, s, prev, kind) if kind else (s >> 3) & 3
    return [root] + chord_notes(root, mask, s & ~(3 << 3) | inv << 3)


def test_voice_leading_progression(pl15_image, pl15_manifest):
    h = NoteHarness(pl15_image)
    h.track(0)
    key = h.r8(ROOT)
    s = settings(2, key=key)                                             # 7th: four inversions to choose from
    set_chord(h, pl15_manifest, 0, 2)
    pads = pads_for_classes(h, 0, (0, 8, 5, 7))                          # i VI iv v (the dump is in a minor scale)
    prev, kinds = [], (0, 1, 2, 3, 1, 2)                                 # the first chord: no leading, but it is remembered
    for step, kind in enumerate(kinds):
        pad = pads[step % 4]
        set_voice(h, pl15_manifest, 0, kind << 4)
        want = lead_chord(h, pad, s, prev, kind)
        got = press_notes(h, pad)
        assert sorted(n for n, _ in got) == sorted(endpoint_note(h, p) for p in want), (step, kind, got, want)
        h.up(pad)
        prev = want
    assert h.sounding == set()


def test_two_pads_lead_from_the_latest(pl15_image, pl15_manifest):
    h = NoteHarness(pl15_image)
    h.track(0)
    s = settings(2, key=h.r8(ROOT))
    set_chord(h, pl15_manifest, 0, 2)
    c, f, g = pads_for_classes(h, 0, (0, 5, 7))
    set_voice(h, pl15_manifest, 0, 1 << 4)
    cc = lead_chord(h, c, s, [], 1)
    assert sorted(n for n, _ in press_notes(h, c)) == sorted(endpoint_note(h, p) for p in cc)
    ff = lead_chord(h, f, s, cc, 1)
    assert sorted(n for n, _ in press_notes(h, f)) == sorted(endpoint_note(h, p) for p in ff)
    h.up(c)
    gg = lead_chord(h, g, s, ff, 1)
    assert sorted(n for n, _ in press_notes(h, g)) == sorted(endpoint_note(h, p) for p in gg)
    h.up(f)
    h.up(g)
    assert h.sounding == set()


def test_load_forgets_the_previous_chord(pl15_image, pl15_manifest):
    from test_saved import DEFAULTS, load, make_tail, write_tail
    h = NoteHarness(pl15_image)
    h.leds()
    h.track(0)
    key, mask = h.r8(ROOT), h.r32(SCALE_MASK)
    byte = 2 | 1 << 3                                                    # 7th, stored inversion 1
    s = settings(2, 1, key=key)
    set_chord(h, pl15_manifest, 0, byte)
    set_voice(h, pl15_manifest, 0, 1 << 4)
    c, f = pads_for_classes(h, 0, (0, 5))
    pad = None
    cc = lead_chord(h, c, s, [], 1)
    for cand in range(16, 32):                                           # a root whose lead from C is not the stored inversion
        root = h.pitch(0, cand)
        if lead(root, mask, s, cc, 1) != 1:
            pad = cand
            break
    assert pad is not None
    press_notes(h, c)
    h.up(c)
    payload = bytearray(DEFAULTS)
    payload[0:4] = bytes([byte] * 4)
    payload[-4:] = bytes([1 << 4] * 4)
    write_tail(h, make_tail(bytes(payload)))
    load(h)
    h.leds()
    h.take()
    want = lead_chord(h, pad, s, [], 0)                                  # the stored inversion
    assert sorted(n for n, _ in press_notes(h, pad)) == sorted(endpoint_note(h, p) for p in want)
    h.up(pad)


def test_writes_use_the_stored_inversion(pl15_image, pl15_manifest):
    """Pattern tools' Write builds the chord with the stored inversion, not voice leading's pick: a 7th stored at
    inversion 3 with voice leading close, after a chord whose lead to the Write's root is another inversion."""
    import euclid_model
    from test_melody import T, configure
    from test_euclid import expected_steps, open_tools, steps, write
    h = NoteHarness(pl15_image)
    h.leds()
    h.track(T)
    mask, key = h.r32(SCALE_MASK), h.r8(ROOT)
    byte = 2 | 3 << 3                                                    # 7th, stored inversion 3
    s = settings(2, 3, key=key)
    set_voice(h, pl15_manifest, T, 1 << 4)                               # close
    h.uc.mem_write(sym(pl15_manifest, "chord_settings") + T, bytes([byte]))
    c = pads_for_classes(h, T, (0,))[0]
    cc = [h.pitch(T, c)] + chord_notes(h.pitch(T, c), mask, s)           # the first chord: the stored inversion
    root = next(r for r in (h.pitch(T, p) for p in range(16, 32)) if lead(r, mask, s, cc, 1) != 3)
    h.down(c)
    h.up(c)
    open_tools(h, T)
    configure(h, pl15_manifest, k=8, last=root, shape=byte)
    write(h)
    hits = euclid_model.mask(8, 16, 0)
    stored = expected_steps(hits, 16, 0, [root] + chord_notes(root, mask, s), 2, 96)
    led = s & ~(3 << 3) | lead(root, mask, s, cc, 1) << 3
    assert stored != expected_steps(hits, 16, 0, [root] + chord_notes(root, mask, led), 2, 96)   # voice leading would differ
    assert steps(h, T) == stored
