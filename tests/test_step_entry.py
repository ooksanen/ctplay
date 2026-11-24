"""Chords in step entry (PL18, spec 2026-10-26-step-entry-chords-design.md, "Adding"): with the track's chord_step bit
and a chord to play, holding a step and pressing a pad (or the pad, then the step) writes the pad's whole chord into
the step, through stock's add 0x0804B094 (hook step_add). All through the controller's pad route; track 0, the two-row
Note view (pads 0-15 = steps 1-16 of the shown half, 16-31 = keys), pattern 0."""
import pytest
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE

import roll_model as rm
from chord_model import chord_notes, in_scale, lead, settings
from notes import (NOTE_EXPANDED, PATTERN, PATTERN_BASE, ROOT, SCALE_MASK, STEP as STEP_SIZE, NoteHarness,
                   endpoint_note, fill, fixed_velocity, pattern_snapshot, recorded_notes, step_addr, step_units, units)
from test_arp import set_arp
from test_pstrum import set_pstrum
from test_chord import (HELD, fuzz_run, fuzz_script, held_counts, lead_chord, pads_for_classes, set_chord, set_down,
                        set_pitch, set_strum, set_voice)

pytestmark = pytest.mark.emu
C = 24                                          # a key pad: pitch 48 in the dump (the project root, C)
OTHER = 30                                      # another key pad
PLAY, NEXT_HALF, DRUM1 = 17, 21, 4
TIE = 0x80
DRUM_RECORDER, DRUM_PATTERN = 0x2003C184, 0x6A8  # tests/drums.py: drum 1's recorder; [+ 0x48] its 8 patterns


def sym(m, name):
    return int(m["symbols"][name], 16)


def set_step(h, m, t, on=True):
    """chord_step bit t, straight in RAM after slim's start-up (as test_mono.set_mono)."""
    h.call(sym(m, "slim_ready"))
    a = sym(m, "chord_step")
    h.uc.mem_write(a, bytes([h.r8(a) & ~(1 << t) | int(on) << t]))


def set_rootless(h, m, t, on):
    h.call(sym(m, "slim_ready"))
    a = sym(m, "chord_rootless")
    h.uc.mem_write(a, bytes([h.r8(a) & ~(1 << t) | int(on) << t]))


def clear(h, t, s, p=0, prob=3):
    """An empty step whose probability byte is not stock's "always" (7), so the add's 7 shows."""
    h.uc.mem_write(step_addr(t, p, s), bytes([0, prob, 0, 0]) + bytes(24))


def ready(h, m, t=0, s=settings(1), step=True):
    """Track t's Note view (two rows), its chord settings s (with rootless), chord_step, fixed velocity off."""
    h.track(t)
    set_chord(h, m, t, s & 0xFF)
    set_rootless(h, m, t, s >> 8 & 1)
    set_step(h, m, t, step)
    fixed_velocity(h, t, False)


def chord(h, t, pad, s):
    """The pad's pitch and its chord's other notes (the model), as a live press builds them without voice leading."""
    root = h.pitch(t, pad)
    return [root] + chord_notes(root, h.r32(SCALE_MASK), s | h.r8(ROOT) << 16)


def step_first(h, step, pad, vel=100):
    h.down(step)
    h.down(pad, vel)
    h.up(pad)
    h.up(step)
    h.heartbeat(5)


def pad_first(h, step, pad, vel=100):
    h.down(pad, vel)
    h.down(step)
    h.up(step)
    h.up(pad)
    h.heartbeat(5)


def pitch_of(h, note):
    """An endpoint note -> the keyboard pitch (endpoint_note's inverse)."""
    return note - h.r8(ROOT) + 12


def drum_steps(h):
    return bytes(h.uc.mem_read(h.r32(h.r32(DRUM_RECORDER) + 0x48), 8 * DRUM_PATTERN))


# ---- off = stock

def stock_script(h, route):
    for step, pad in ((0, C), (1, OTHER), (2, C), (2, C)):                   # the last: stock's removal
        (step_first if route == "step first" else pad_first)(h, step, pad)


@pytest.mark.parametrize("route", ["step first", "pad first"])
@pytest.mark.parametrize("how", ["setting off", "single, no bass"])
def test_off_is_stock(stock_image, pl18_image, pl18_manifest, route, how):
    a, b = NoteHarness(stock_image), NoteHarness(pl18_image)
    a.track(0)
    b.track(0)
    if how == "setting off":
        set_chord(b, pl18_manifest, 0, settings(1))
        set_step(b, pl18_manifest, 0, False)
    else:
        set_chord(b, pl18_manifest, 0, settings(0))
        set_step(b, pl18_manifest, 0, True)
    for h in (a, b):
        stock_script(h, route)
    assert pattern_snapshot(b, 0) == pattern_snapshot(a, 0)
    assert b.sounding == set()


def test_expanded_view_and_drums_untouched(stock_image, pl18_image, pl18_manifest):
    h = NoteHarness(pl18_image)
    h.track(0, NOTE_EXPANDED)
    set_chord(h, pl18_manifest, 0, settings(1))
    h.call(sym(pl18_manifest, "slim_ready"))
    h.uc.mem_write(sym(pl18_manifest, "chord_step"), b"\x0f")
    before = pattern_snapshot(h, 0)
    for pad in (0, C, 31):
        h.down(pad)
        h.up(pad)
    assert pattern_snapshot(h, 0) == before and h.sounding == set()
    a = NoteHarness(stock_image)
    for x in (a, h):
        x.press(DRUM1)
        x.down(0)
        x.down(C)
        x.up(C)
        x.up(0)
        x.heartbeat(5)
    assert drum_steps(h) == drum_steps(a)


# ---- adding

@pytest.mark.parametrize("s", [settings(1), settings(2), settings(3, bass=1), settings(1, bass=1, rootless=1)],
                         ids=["triad", "7th", "9th bass below", "triad rootless over bass"])
def test_step_first_writes_the_chord(pl18_image, pl18_manifest, s):
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest, s=s)
    clear(h, 0, 0)
    want = chord(h, 0, C, s)
    assert len(want) >= 3
    step_first(h, 0, C)
    assert units(h, 0, 0, 0) == sorted(want)
    assert all(u[1:] == (6, 0, 100) for u in step_units(h, 0, 0, 0)), step_units(h, 0, 0, 0)
    assert h.r8(step_addr(0, 0, 0) + 1) == 7
    assert h.sounding == set()


def test_pad_first_writes_the_sounding_chord(pl18_image, pl18_manifest):
    h = NoteHarness(pl18_image)
    s = settings(2)                                                         # 7th: four inversions to lead between
    ready(h, pl18_manifest, s=s)
    clear(h, 0, 0)
    pad_first(h, 0, C)
    assert units(h, 0, 0, 0) == sorted(chord(h, 0, C, s))
    assert all(u[1:] == (6, 0, 100) for u in step_units(h, 0, 0, 0))
    assert h.sounding == set()
    # voice leading close, from a chord played before: the step gets what sounded
    c, f = pads_for_classes(h, 0, (0, 5))
    set_voice(h, pl18_manifest, 0, 1 << 4)
    full = settings(2, key=h.r8(ROOT))
    prev = lead_chord(h, f, full, chord(h, 0, C, s), 1)                     # F leads from the chord pad-first played
    h.down(f)
    h.up(f)
    assert lead(h.pitch(0, c), h.r32(SCALE_MASK), full, prev, 1) != 0       # the leading moves the next chord
    clear(h, 0, 1)
    h.take()
    h.down(c)
    sounded = sorted(pitch_of(h, e[2]) for e in h.take("synth_on"))
    h.down(1)
    h.up(1)
    h.up(c)
    h.heartbeat(5)
    assert sounded == sorted(lead_chord(h, c, full, prev, 1))
    assert units(h, 0, 0, 1) == sounded
    assert h.sounding == set()


def test_gate_velocity_room(pl18_image, pl18_manifest):
    h = NoteHarness(pl18_image)
    s = settings(1)
    ready(h, pl18_manifest, s=s)
    want = chord(h, 0, C, s)
    outside = [n for n in range(36, 80) if n % 12 not in {w % 12 for w in want}]
    # a longer gate with a tie: the added notes take the gate, not the tie; the old unit stays as it was
    old = bytes([outside[0], 20 | TIE, 3, 90])
    h.uc.mem_write(step_addr(0, 0, 0), bytes([1, 5, 0, 0]) + old + bytes(20))
    step_first(h, 0, C)
    got = step_units(h, 0, 0, 0)
    assert bytes(got[0]) == old and h.r8(step_addr(0, 0, 0) + 1) == 5
    assert sorted(u[0] for u in got[1:]) == sorted(want) and all(u[1:] == (20, 0, 100) for u in got[1:]), got
    # fixed velocity: 96 for every note
    fixed_velocity(h, 0, True)
    clear(h, 0, 1)
    step_first(h, 1, C)
    assert [u[3] for u in step_units(h, 0, 0, 1)] == [96] * len(want)
    # room: 4 notes there, the pad's own note and the chord's lowest other note fit
    fill(h, 0, 0, 2, outside[:4])
    step_first(h, 2, C)
    assert units(h, 0, 0, 2) == sorted(outside[:4] + [want[0], min(want[1:])])
    # a chord note already in the step is not written twice
    fill(h, 0, 0, 3, [want[1]])
    step_first(h, 3, C)
    assert units(h, 0, 0, 3) == sorted(want)
    assert h.sounding == set()


@pytest.mark.parametrize("where", ["top notes above 127", "notes past the range"])
def test_top_octave_pad(pl18_image, pl18_manifest, where):
    """The setup of test_chord.py::test_top_octave_pad_plays_its_chord: a step gets what the pad plays live."""
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest)
    key, mask = h.r8(ROOT), h.r32(SCALE_MASK)
    top = 126 if where == "top notes above 127" else 139
    pitch = next(p for p in range(top - key, 0, -1) if in_scale(mask, p))
    set_pitch(h, 0, C, pitch)
    others = chord_notes(pitch, mask, settings(1, key=key))
    if where == "top notes above 127":
        assert len(others) == 2 and max(others) > 127
    else:
        assert len(others) < 2                                              # left out, as live
    clear(h, 0, 0)
    step_first(h, 0, C)
    assert units(h, 0, 0, 0) == sorted([pitch] + others)
    assert h.sounding == set()


@pytest.mark.parametrize("where", ["above 139", "below 12"])
def test_ignored_pad_is_stock(stock_image, pl18_image, pl18_manifest, where):
    """A pad stock ignores (kbd_pad_ignored 0x080523E8: pitch + key, as a byte, outside 12-139) plays nothing live, but
    step first stock's press still adds its note (0x0804AC8C: only pitch 0 is left out). CTPlay adds no chord for it:
    the add and the pad again are stock's. A chord whose other notes are in range (1st inversion at the top: the 3rd and
    5th an octave down; a triad's 3rd and 5th from 12 up at the bottom), so a chord would show. Stock's pad again at the
    top adds the note a second time: its removal test snaps the step's note into the scale's range (scale_snap
    0x080408C6 clamps to the bytes at scale + 0 / + 1), so 140 never matches the pad's pitch."""
    a, h = NoteHarness(stock_image), NoteHarness(pl18_image)
    a.track(0)
    fixed_velocity(a, 0, False)
    s = settings(1, inv=1) if where == "above 139" else settings(1)
    ready(h, pl18_manifest, s=s)
    key, mask = h.r8(ROOT), h.r32(SCALE_MASK)
    if where == "above 139":
        pitch = next(p for p in range(140 - key, 256 - key) if in_scale(mask, p))
    else:
        pitch = next(p for p in range(11 - key, 0, -1) if in_scale(mask, p))
    assert not 12 <= pitch + key <= 139
    assert chord_notes(pitch, mask, s | key << 16)                          # in-range chord notes there to leave out
    for x in (a, h):
        set_pitch(x, 0, C, pitch)
        clear(x, 0, 0)
        step_first(x, 0, C)
    assert units(h, 0, 0, 0) == [pitch]
    assert used_steps(h, 0) == used_steps(a, 0)
    for x in (a, h):
        step_again(x, 0, C)
    assert units(a, 0, 0, 0) == ([pitch] * 2 if where == "above 139" else [])   # stock's own, found 2026-10-29
    assert used_steps(h, 0) == used_steps(a, 0)
    assert h.sounding == set() and a.sounding == set()


def test_voice_leading_across_steps(pl18_image, pl18_manifest):
    h = NoteHarness(pl18_image)
    s = settings(2)
    ready(h, pl18_manifest, s=s)
    set_voice(h, pl18_manifest, 0, 1 << 4)                                  # close
    full = settings(2, key=h.r8(ROOT))
    prev, moved = [], 0
    for step, pad in zip((0, 4, 8), pads_for_classes(h, 0, (0, 5, 7))):
        clear(h, 0, step)
        want = lead_chord(h, pad, full, prev, 1)
        moved += want != chord(h, 0, pad, s)
        step_first(h, step, pad)
        assert units(h, 0, 0, step) == sorted(want), step
        prev = want
    assert moved                                                            # the leading changed a chord
    assert h.sounding == set()


def test_midi_track(pl18_image, pl18_manifest):
    got = []
    for t in (0, 2):
        h = NoteHarness(pl18_image)
        ready(h, pl18_manifest, t=t)
        clear(h, t, 0)
        step_first(h, 0, C)
        assert units(h, t, 0, 0) == sorted(chord(h, t, C, settings(1)))
        assert h.sounding == set()
        got.append([(u[0] - h.pitch(t, C), *u[1:]) for u in step_units(h, t, 0, 0)])
    assert got[0] == got[1]                                                 # the dump's tracks sit octaves apart


def test_playback_and_a_stock_edit(pl18_image, pl18_manifest):
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest)
    clear(h, 0, 0)
    want = chord(h, 0, C, settings(1))
    step_first(h, 0, C)
    h.take()
    h.press(PLAY)
    h.heartbeat(20)
    assert sorted(pitch_of(h, e[2]) for e in h.take("synth_on") if e[1] == 0) == sorted(want)
    h.press(PLAY)                                                           # stop
    h.heartbeat(300)
    set_step(h, pl18_manifest, 0, False)
    step_first(h, 0, OTHER)
    assert units(h, 0, 0, 0) == sorted(want + [h.pitch(0, OTHER)])
    assert h.sounding == set()


def test_while_playing(pl18_image, pl18_manifest):
    """Review Focus: an entry while the sequencer plays writes the whole chord; nothing stays on after the stop."""
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest)
    clear(h, 0, 4)
    h.press(PLAY)
    h.heartbeat(50)
    h.down(4)
    h.down(C)
    h.heartbeat(20)
    h.up(C)
    h.up(4)
    h.heartbeat(400)
    h.press(PLAY)
    h.heartbeat(300)
    assert units(h, 0, 0, 4) == sorted(chord(h, 0, C, settings(1)))
    assert h.sounding == set()


def test_second_half(pl18_image, pl18_manifest):
    """Review Focus: with 17-32 shown, step pad 0 is step 17 (index 16): the chord goes there, never into step 1."""
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest)
    clear(h, 0, 16)
    first = bytes(h.uc.mem_read(step_addr(0, 0, 0), 28))
    h.press(NEXT_HALF)
    step_first(h, 0, C)
    assert units(h, 0, 0, 16) == sorted(chord(h, 0, C, settings(1)))
    assert bytes(h.uc.mem_read(step_addr(0, 0, 0), 28)) == first
    assert h.sounding == set()


def added_sound(h, pad):
    """Step 1 (empty) held, then the pad: the synth notes that start while both are down; then the releases."""
    clear(h, 0, 0)
    h.down(0)
    h.take()
    h.down(pad)
    on = sorted(pitch_of(h, e[2]) for e in h.take("synth_on") if e[1] == 0)
    h.up(pad)
    h.up(0)
    h.heartbeat(5)
    return on


def test_sound_follows_stock(stock_image, pl18_image, pl18_manifest):
    """Found in emulation: stock sounds the step's notes when a note is added to a held step (the edit store's commit
    previews the step: with an empty step, the added note alone); with a chord the commit previews the whole chord, and
    the step's release ends it. CTPlay sends nothing of its own."""
    a = NoteHarness(stock_image)
    a.track(0)
    fixed_velocity(a, 0, False)
    stock = added_sound(a, C)
    assert a.sounding == set()
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest)
    got = added_sound(h, C)
    want = sorted(chord(h, 0, C, settings(1)))
    assert got == (want if stock == [h.pitch(0, C)] else [])
    assert stock == [h.pitch(0, C)]                                         # what was found (docstring)
    assert h.sounding == set()


def heard(h):
    """The track's synth notes on now, as keyboard pitches."""
    return sorted(pitch_of(h, k[2]) for k in h.sounding if k[0] == "synth" and k[1] == 0)


def test_release_orders(pl18_image, pl18_manifest):
    """What TEST.md's device steps 8b, 10, 11c and 12b expect to hear, a triad with the setting on, through the
    controller's pad route: step first, the chord sounds while the step is held; pad first, the pad let go first, the
    chord sounds until the step's release; pad first, the step let go first, the whole chord sounds until the pad's
    release (match stock: stock keeps the pad's note, decided 2026-10-29); the pad again on the held step ends the
    chord at once."""
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest)
    want = sorted(chord(h, 0, C, settings(1)))
    assert len(want) == 3
    clear(h, 0, 0)                                                          # 8b: step first
    h.down(0)
    h.down(C)
    h.up(C)
    assert heard(h) == want
    h.up(0)
    h.heartbeat(5)
    assert h.sounding == set()
    clear(h, 0, 4)                                                          # 11c: pad first, the pad let go first
    h.down(C)
    h.down(4)
    assert heard(h) == want
    h.up(C)
    assert heard(h) == want
    h.up(4)
    h.heartbeat(5)
    assert h.sounding == set()
    clear(h, 0, 8)                                                          # 12b: pad first, the step let go first
    h.down(C)
    h.down(8)
    assert heard(h) == want
    h.up(8)
    assert heard(h) == want
    h.up(C)
    h.heartbeat(5)
    assert h.sounding == set() and held_counts(h, pl18_manifest) == [0] * HELD
    h.down(0)                                                               # 10: the pad again ends the chord
    assert heard(h) == want
    h.down(C)
    assert h.sounding == set()
    h.up(C)
    h.up(0)
    h.heartbeat(5)
    assert h.sounding == set() and units(h, 0, 0, 0) == []


@pytest.mark.parametrize("how", ["setting off", "strum", "strum cut short"])
def test_pad_first_step_let_go_first(pl18_image, pl18_manifest, how):
    """12b's order (pad down, step down, step up, pad up) beside the block chord: with the setting off (the pad's note
    in the step, its chord live) and with a rising strum (whole, or the step let go before the strum's end), the chord
    sounds until the pad's release, then nothing is left on and no chord entry stays."""
    h = NoteHarness(pl18_image)
    m = pl18_manifest
    ready(h, m, step=how != "setting off")
    if how != "setting off":
        set_strum(h, m, 0, 1)
    want = sorted(chord(h, 0, C, settings(1)))
    clear(h, 0, 8)
    h.down(C)
    if how != "strum cut short":
        h.heartbeat(300)                                                    # the strum has sounded every note
    h.down(8)
    h.up(8)
    if how != "strum cut short":
        assert heard(h) == want
    h.heartbeat(300)
    assert heard(h) == want
    h.up(C)
    h.heartbeat(300)
    assert h.sounding == set() and held_counts(h, m) == [0] * HELD
    assert units(h, 0, 0, 8) == ([h.pitch(0, C)] if how == "setting off" else want)


def step_let_go_first(h):
    """Step 9 (empty) held, then C; the step let go first, then C: what sounds with both down, after the step's
    release, after C's release."""
    clear(h, 0, 8)
    h.down(8)
    h.down(C)
    both = heard(h)
    h.up(8)
    h.heartbeat(5)
    after_step = heard(h)
    h.up(C)
    h.heartbeat(5)
    return both, after_step, heard(h)


def test_step_first_step_let_go_first(stock_image, pl18_image, pl18_manifest):
    """Step down, pad down, step up, pad up. With a step held, stock sends the pad's press to its add (no live note,
    so CTPlay keeps no chord entry); found 2026-11-11: stock's note stops at the step's release, though the pad is
    still held. CTPlay matches it, the setting off (the pad's note) and on (the chord)."""
    a = NoteHarness(stock_image)
    a.track(0)
    fixed_velocity(a, 0, False)
    pitch = a.pitch(0, C)
    assert step_let_go_first(a) == ([pitch], [], [])                         # stock (docstring)
    assert a.sounding == set()
    for on in (False, True):
        h = NoteHarness(pl18_image)
        ready(h, pl18_manifest, step=on)
        want = sorted(chord(h, 0, C, settings(1))) if on else [pitch]
        assert step_let_go_first(h) == (want, [], [])
        assert h.sounding == set() and held_counts(h, pl18_manifest) == [0] * HELD


def test_play_started_over_a_held_chord(pl18_image, pl18_manifest):
    """Play pressed while a chord pad and a step are held (pad first): the step's notes stop sounding as a preview
    (stock's listener ends the preview, hook preview_end), the chord stays with its pad; after the pad's release only
    the pattern's notes (the chord just written) can sound; after Stop nothing, no chord entry left."""
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest)
    for s in range(32):
        clear(h, 0, s)
    want = sorted(chord(h, 0, C, settings(1)))
    h.down(C)
    h.down(8)
    assert heard(h) == want
    h.press(PLAY)
    h.heartbeat(5)
    assert heard(h) == want
    h.up(8)
    h.heartbeat(5)
    assert heard(h) == want
    h.up(C)
    h.heartbeat(50)
    assert set(heard(h)) <= set(want)
    h.press(PLAY)
    h.heartbeat(300)
    assert h.sounding == set() and held_counts(h, pl18_manifest) == [0] * HELD
    assert units(h, 0, 0, 8) == want


def test_setting_off_a_chord_tone_in_the_step(pl18_image, pl18_manifest):
    """The setting off, the step already holding one of the pad's chord tones: pad first, the step let go first. The
    step's press previews that tone (taking it from the pad); at the step's release it stays with the chord, until the
    pad's release ends everything."""
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest, step=False)
    want = sorted(chord(h, 0, C, settings(1)))
    tone = want[1]
    clear(h, 0, 8)
    fill(h, 0, 0, 8, [tone])
    h.down(C)
    h.down(8)
    assert heard(h) == want
    h.up(8)
    h.heartbeat(5)
    assert heard(h) == want
    h.up(C)
    h.heartbeat(5)
    assert h.sounding == set() and held_counts(h, pl18_manifest) == [0] * HELD
    assert units(h, 0, 0, 8) == sorted({tone, h.pitch(0, C)})


@pytest.mark.parametrize("first", ["A", "B"], ids=["A let go first", "B let go first"])
def test_two_chords_sharing_a_pitch(pl18_image, pl18_manifest, first):
    """Two chord pads held (sharing a pitch), then a step pressed and let go: both chords still sound; either release
    order leaves nothing on and no chord entry."""
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest)
    s = settings(1)
    a = C
    ca = set(chord(h, 0, a, s))
    b = next(p for p in range(16, 32) if h.pitch(0, p) != h.pitch(0, a) and ca & set(chord(h, 0, p, s)))
    clear(h, 0, 8)
    h.down(a)
    h.down(b)
    both = heard(h)
    assert set(ca) <= set(both)
    h.down(8)
    h.up(8)
    h.heartbeat(5)
    assert heard(h) == both
    for p in ((a, b) if first == "A" else (b, a)):
        h.up(p)
        h.heartbeat(5)
    assert h.sounding == set() and held_counts(h, pl18_manifest) == [0] * HELD


def test_arpeggio_over_a_step_release(pl18_image, pl18_manifest):
    """An arpeggio held while a step holding one of its chord's tones is pressed and let go: the arpeggio's entry is
    not handed the step's preview (stock ends it as before); pad first writes nothing; nothing stays on."""
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest)
    set_arp(h, pl18_manifest, 0, 1 | 2 << 3, 5 << 2)                        # up, 1/16, legato
    want = sorted(chord(h, 0, C, settings(1)))
    clear(h, 0, 8)
    fill(h, 0, 0, 8, [want[1]])
    before = step_units(h, 0, 0, 8)
    h.down(C)
    h.heartbeat(100)
    h.down(8)
    h.heartbeat(20)
    h.up(8)
    h.heartbeat(100)
    h.up(C)
    h.heartbeat(300)
    assert h.sounding == set() and held_counts(h, pl18_manifest) == [0] * HELD
    assert step_units(h, 0, 0, 8) == before


# ---- removing (spec "Removing"): the pad again, its own note in the step, takes the chord out by note name

def step_again(h, step, pad):
    """The add's press order again (step down, pad down, pad up, step up): stock's removal route."""
    h.down(step)
    h.down(pad)
    h.up(pad)
    h.up(step)
    h.heartbeat(5)


@pytest.mark.parametrize("s", [settings(1), settings(2), settings(3, bass=1), settings(1, bass=1, rootless=1)],
                         ids=["triad", "7th", "9th bass below", "triad rootless over bass"])
def test_the_pad_again_removes_the_chord(pl18_image, pl18_manifest, s):
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest, s=s)
    clear(h, 0, 0)
    step_first(h, 0, C)
    assert units(h, 0, 0, 0) == sorted(chord(h, 0, C, s))
    step_again(h, 0, C)
    assert units(h, 0, 0, 0) == []
    assert h.sounding == set()
    assert held_counts(h, pl18_manifest) == [0] * HELD


def test_removal_after_a_voicing_change(pl18_image, pl18_manifest):
    h = NoteHarness(pl18_image)
    s = settings(1)
    ready(h, pl18_manifest, s=s)
    clear(h, 0, 0)
    step_first(h, 0, C)
    added = units(h, 0, 0, 0)
    set_chord(h, pl18_manifest, 0, settings(1, inv=2))
    assert sorted(chord(h, 0, C, settings(1, inv=2))) != added              # the 2nd inversion: other octaves
    step_again(h, 0, C)
    assert units(h, 0, 0, 0) == []
    assert h.sounding == set()


def test_removal_by_note_name(pl18_image, pl18_manifest):
    """The spec's accepted edge: a hand-entered note with one of the chord's note names goes with the chord."""
    h = NoteHarness(pl18_image)
    s = settings(1)
    ready(h, pl18_manifest, s=s)
    want = chord(h, 0, C, s)
    third = sorted(want)[1]
    outside = next(n for n in range(36, 80) if n % 12 not in {w % 12 for w in want})
    fill(h, 0, 0, 0, [third + 12, outside])
    step_first(h, 0, C)
    assert units(h, 0, 0, 0) == sorted(want + [third + 12, outside])
    step_again(h, 0, C)
    assert units(h, 0, 0, 0) == [outside]
    assert h.sounding == set()


def used_steps(h, t):
    """Per step of the 8 patterns: parameter 0's 4 bytes (mask, probability, ...) and the bytes of the used units only.
    Stock's removal only clears the mask bit (0x0804ABD6), so an unused unit keeps stale bytes."""
    snap, out = pattern_snapshot(h, t), []
    for p in range(8):
        for s in range(32):
            o = p * PATTERN + s * STEP_SIZE
            out.append(snap[o:o + 4] + b"".join(snap[o + 4 + 4 * u:o + 8 + 4 * u] for u in range(6) if snap[o] >> u & 1))
    return out


def test_add_then_remove_is_stock(stock_image, pl18_image, pl18_manifest):
    """Review Focus: on an empty step a chord added and taken out ends as stock adding and removing one note
    (the probability byte left at stock's 7)."""
    a = NoteHarness(stock_image)
    a.track(0)
    fixed_velocity(a, 0, False)
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest)
    for x in (a, h):
        clear(x, 0, 0)
        step_first(x, 0, C)
    assert len(units(h, 0, 0, 0)) == 3 and len(units(a, 0, 0, 0)) == 1
    for x in (a, h):
        step_again(x, 0, C)
    assert h.r8(step_addr(0, 0, 0)) == 0 and h.r8(step_addr(0, 0, 0) + 1) == 7
    assert used_steps(h, 0) == used_steps(a, 0)
    assert h.sounding == set() and a.sounding == set()


@pytest.mark.parametrize("how", ["arpeggio", "falling strum", "own note in the step"])
def test_pad_first_gaps(pl18_image, pl18_manifest, how):
    """The spec's accepted gaps: pad first writes nothing when CTPlay takes the press (arpeggio, falling strum), and
    stock's listener skips a pad whose note is in the step already. Nothing is left on."""
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest)
    clear(h, 0, 0)
    if how == "arpeggio":
        set_arp(h, pl18_manifest, 0, 1 | 2 << 3, 5 << 2)                    # up, 1/16, legato
    elif how == "falling strum":
        set_strum(h, pl18_manifest, 0, 1)
        set_down(h, pl18_manifest, 0)
    else:
        fill(h, 0, 0, 0, [h.pitch(0, C)])
    before = step_units(h, 0, 0, 0)
    pad_first(h, 0, C)
    h.heartbeat(300)
    assert step_units(h, 0, 0, 0) == before
    assert h.sounding == set()
    assert held_counts(h, pl18_manifest) == [0] * HELD


@pytest.mark.parametrize("button", [14, 1], ids=["Mixer", "track button"])
def test_leaving_the_view(pl18_image, pl18_manifest, button):
    """Review Focus: a chord pad and a step held when the view changes: stock releases the held pads; nothing is left
    on, no chord entry stays, the step keeps what pad first wrote."""
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest)
    clear(h, 0, 0)
    want = sorted(chord(h, 0, C, settings(1)))
    h.down(C)
    h.down(0)
    h.press(button)
    h.heartbeat(5)
    assert h.sounding == set(), h.sounding
    assert held_counts(h, pl18_manifest) == [0] * HELD
    assert units(h, 0, 0, 0) == want
    h.up(0)                                                                 # stale releases, in the new view
    h.up(C)
    h.heartbeat(5)
    assert h.sounding == set() and held_counts(h, pl18_manifest) == [0] * HELD
    assert units(h, 0, 0, 0) == want


def test_pad_first_uses_the_held_entry(pl18_image, pl18_manifest):
    """Ruling 4: two key pads held before the step, voice leading close. Stock's listener adds both; A's notes are the
    ones A sounded (its held entry), not A rebuilt leading from B's chord (chord_prev), and the step press leaves
    chord_prev as B's press set it. Pads picked so that the rebuilt A differs from the sounded A."""
    h = NoteHarness(pl18_image)
    m = pl18_manifest
    s = settings(1)
    ready(h, m, s=s)
    set_voice(h, m, 0, 1 << 4)
    full, mask = settings(1, key=h.r8(ROOT)), h.r32(SCALE_MASK)
    pit = {p: h.pitch(0, p) for p in range(16, 32)}

    def built(pad, prev):
        inv = lead(pit[pad], mask, full, prev, 1)
        return [pit[pad]] + chord_notes(pit[pad], mask, full & ~(3 << 3) | inv << 3)

    def picks():
        for p in pit:
            cp = built(p, [])
            for a in pit:
                ca = built(a, cp)
                for b in pit:
                    cb = built(b, ca)
                    if (a < b and pit[a] != pit[p] and pit[b] not in ca and len(set(ca) | set(cb)) <= 6
                            and sorted(built(a, cb)) != sorted(ca)):
                        return p, a, b, ca, cb
    p, a, b, ca, cb = picks()
    clear(h, 0, 0)
    h.down(p)
    h.up(p)
    h.heartbeat(5)
    h.take()
    h.down(a)
    sa = sorted(pitch_of(h, e[2]) for e in h.take("synth_on"))
    h.down(b)
    sb = sorted(pitch_of(h, e[2]) for e in h.take("synth_on"))
    assert sa == sorted(ca) and sb == sorted(cb)                            # the model's picks sounded
    prev = bytes(h.uc.mem_read(sym(m, "chord_prev"), 6)), h.r8(sym(m, "chord_prev_n"))
    h.down(0)
    assert (bytes(h.uc.mem_read(sym(m, "chord_prev"), 6)), h.r8(sym(m, "chord_prev_n"))) == prev
    h.up(0)
    h.up(b)
    h.up(a)
    h.heartbeat(5)
    assert units(h, 0, 0, 0) == sorted(set(sa) | set(sb))
    assert h.sounding == set()
    assert held_counts(h, m) == [0] * HELD


def test_removal_frees_a_held_pad(pl18_image, pl18_manifest):
    """Stock's removal frees the key pad holding the removed pitch ([view + 0x40 / 0x60 + pad] = 0, 0x0804AC74): the
    chord's other notes do the same. C and E held, then the step (the listener adds C's chord; E's pitch is in it);
    C let go and pressed again: the chord goes, E's slot is freed, nothing stays on."""
    h = NoteHarness(pl18_image)
    ready(h, pl18_manifest)
    clear(h, 0, 0)
    want = chord(h, 0, C, settings(1))
    e = next(p for p in range(16, 32) if h.pitch(0, p) == want[1])
    view = h.note_view(0)
    h.down(C)
    h.down(e)
    h.down(0)
    assert units(h, 0, 0, 0) == sorted(want) and h.r8(view + 0x40 + e) == want[1]
    h.up(C)
    h.down(C)
    assert units(h, 0, 0, 0) == []
    assert h.r8(view + 0x40 + e) == 0 and h.r8(view + 0x60 + e) == 0
    h.up(C)
    h.up(e)
    h.up(0)
    h.heartbeat(5)
    assert h.sounding == set()
    assert held_counts(h, pl18_manifest) == [0] * HELD


# ---- the press cost (spec "Where it hooks"): the work on the press stays per press, no interrupts masked

def press_cost(h, pad, own=None, irq=None):
    """Instructions from the controller's pad press until it returns, those inside `own` (slim's code), and whether
    `irq` (slim_irq_save) was reached."""
    n, mine, hit = [0], [0], []

    def count(uc, address, size, data):
        n[0] += 1
        if own and own[0] <= address < own[1]:
            mine[0] += 1

    hooks = [h.uc.hook_add(UC_HOOK_CODE, count)]
    if irq is not None:
        hooks.append(h.uc.hook_add(UC_HOOK_CODE, lambda *x: hit.append(1), begin=irq, end=irq))
    h.down(pad)
    for k in hooks:
        h.uc.hook_del(k)
    return n[0], mine[0], bool(hit)


def test_press_cost(stock_image, pl18_image, pl18_manifest):
    """A 5-note chord (9th, bass below) added to an empty held step and taken out again, against stock's one note.
    Measured 2026-10-28: stock 3,426 / 3,250 instructions (add / removal); PL18 10,321 / 11,376, of which CTPlay's own
    code about 1.9 k / 1.5 k: the rest is stock's listeners and router handling 5 units and 5 note-offs (stock adding
    a 5th note to a step of 4 costs 4,242 alone). The bound guards against the phantom press on the next pad, which
    comes from masked work delaying the pad scan; nothing in this press is masked. So the checks are: slim_irq_save
    never reached, CTPlay's own share at most one stock one-note press, the whole press at most 4 x that press. The
    device's next-pad check (TEST.md) is the real gate."""
    a = NoteHarness(stock_image)
    a.track(0)
    fixed_velocity(a, 0, False)
    h = NoteHarness(pl18_image)
    s = settings(3, bass=1)                                                 # 9th, bass below: 5 notes
    ready(h, pl18_manifest, s=s)
    irq = sym(pl18_manifest, "slim_irq_save") & ~1
    own = tuple(int(pl18_manifest["flash"][k], 16) for k in ("start", "end"))
    cost = {}
    for name, x in (("stock", a), ("pl18", h)):
        clear(x, 0, 0)
        x.down(0)
        add = press_cost(x, C, own, irq if x is h else None)
        x.up(C)
        assert len(units(x, 0, 0, 0)) == (5 if x is h else 1)
        rem = press_cost(x, C, own, irq if x is h else None)
        x.up(C)
        x.up(0)
        x.heartbeat(5)
        assert units(x, 0, 0, 0) == [] and x.sounding == set()
        cost[name] = add, rem
    print(f"press cost (instructions): stock add {cost['stock'][0][0]}, removal {cost['stock'][1][0]}; pl18 add "
          f"{cost['pl18'][0][0]} (CTPlay {cost['pl18'][0][1]}), removal {cost['pl18'][1][0]} (CTPlay {cost['pl18'][1][1]})")
    for i in (0, 1):                                                        # the add, the removal
        total, mine, masked = cost["pl18"][i]
        assert not masked                                                   # no interrupts masked on either press
        assert cost["stock"][i][1] == 0
        assert mine <= cost["stock"][i][0]                                  # CTPlay's own work: under one stock press
        assert total <= 4 * cost["stock"][i][0]


# ---- PL19: Written step entry (spec 2026-10-28-playback-strum-design.md, "Written: step entry"): with the track's
# pattern strum Written and its strum on, the chord goes in as a roll from the held step's start (note k at k x
# WRITTEN_GAP ticks, strum order): the notes in the held step on the press, the rest (the spill) on the release of the
# pad that made the entry, straight into the pattern, then one rec_touch.

WRITTEN = 2
REC_TOUCH = 0x0803F8D4
SPILLS, SPILL_SIZE = 16, 16                             # step_entry.c spill_t: track + 1 first


def written(h, m, s=settings(1), speed=1, down=False, rate=3, first=0, last=31, mode=WRITTEN):
    """ready() + track 0's strum speed / direction and pattern strum; pattern 0 at `rate` (3 = 1/16, 5 = 1/8,
    1 = 1/32) over steps first..last, every step emptied (probability 3: an add's 7 shows)."""
    ready(h, m, s=s)
    set_strum(h, m, 0, speed)
    set_down(h, m, 0, down)
    set_pstrum(h, m, 0, mode)
    h.uc.mem_write(PATTERN_BASE[0] + 0x380, bytes([last, first, rate]))
    for st in range(32):
        clear(h, 0, st)


def roll(h, s, speed, down, rate, step=0, pad=C, first=0, last=31):
    """The model: {step: {(note, microstep)}} of the pad's chord rolled from `step`."""
    notes = rm.roll_order(chord(h, 0, pad, s), down)
    per, gap = rm.STEP_TICKS[rate], rm.WRITTEN_GAP[speed]
    out = {}
    for k, n in enumerate(notes):
        six = rm.roll_sixths(k * gap, per)
        out.setdefault(rm.roll_step(step, six // 6, first, last), set()).add((n, six % 6))
    return out


def rolled(h):
    """{step: {(note, microstep)}} of pattern 0's used steps."""
    out = {}
    for st in range(32):
        got = {(u[0], u[2]) for u in step_units(h, 0, 0, st)}
        if got:
            out[st] = got
    return out


def pending(h, m):
    """The pending spills' track bytes (0 = free)."""
    return [h.r8(sym(m, "spill") + SPILL_SIZE * i) for i in range(SPILLS)]


SHAPES = {"triad": settings(1), "9th bass": settings(3, bass=1)}
ROLL_CASES = [(sh, sp, dn, rt, ro) for sh in SHAPES for sp in (1, 2, 3) for rt in (3, 5) for dn in (False, True)
              for ro in ("step first", "pad first") if not (dn and ro == "pad first")]


@pytest.mark.parametrize("shape, speed, down, rate, route", ROLL_CASES,
                         ids=[f"{sh}-{('slow', 'medium', 'fast')[sp - 1]}-{'falling' if dn else 'rising'}-"
                              f"{'1-16' if rt == 3 else '1-8'}-{ro.split()[0]}" for sh, sp, dn, rt, ro in ROLL_CASES])
def test_written_entry_roll(pl19_image, pl19_manifest, shape, speed, down, rate, route):
    """After the press (step first) or the step's press (pad first) the held step holds exactly the roll's in-step
    notes, at their microsteps; the spill lands on the pad's release, at the model's positions (gate 6, probability 7,
    the press's velocity); nothing sounds after the releases, no record waits."""
    h = NoteHarness(pl19_image)
    m = pl19_manifest
    s = SHAPES[shape]
    written(h, m, s=s, speed=speed, down=down, rate=rate)
    want = roll(h, s, speed, down, rate)
    assert len(want) > 1 or rate == 5 or speed > 1      # slow at 1/16 spills
    if rate == 5 and speed == 3:
        notes = rm.roll_order(chord(h, 0, C, s), down)
        assert rm.roll_sixths(1, 12) == rm.roll_sixths(2, 12) and len({mi for _, mi in want[0]}) < len(notes)
    if route == "step first":
        h.down(0)
        h.down(C)
        assert rolled(h) == {0: want[0]}
        h.up(C)
        assert rolled(h) == want
        h.up(0)
    else:
        h.down(C)
        h.heartbeat(400)                                 # the live strum plays out (ticks at the project's tempo)
        h.down(0)
        assert rolled(h) == {0: want[0]}
        h.up(0)
        assert rolled(h) == {0: want[0]}                 # the spill waits for the pad
        h.up(C)
        assert rolled(h) == want
    h.heartbeat(5)
    for st in want:
        assert all(u[1] == 6 and u[3] == 100 for u in step_units(h, 0, 0, st)), (st, step_units(h, 0, 0, st))
        assert h.r8(step_addr(0, 0, st) + 1) == 7
    assert h.sounding == set()
    assert held_counts(h, m) == [0] * HELD and pending(h, m) == [0] * SPILLS


@pytest.mark.parametrize("order", ["step let go first", "pad let go first"])
def test_written_entry_release_orders(pl19_image, pl19_manifest, order):
    """The spill goes in on the release of the pad that made the entry, whichever is let go first."""
    h = NoteHarness(pl19_image)
    written(h, pl19_manifest)
    want = roll(h, settings(1), 1, False, 3)
    h.down(0)
    h.down(C)
    if order == "step let go first":
        h.up(0)
        h.heartbeat(5)
        assert rolled(h) == {0: want[0]}
        h.up(C)
    else:
        h.up(C)
        assert rolled(h) == want
        h.up(0)
    h.heartbeat(5)
    assert rolled(h) == want
    assert h.sounding == set() and pending(h, pl19_manifest) == [0] * SPILLS


def test_written_pad_first_falling_is_the_gap(pl19_image, pl19_manifest, pl18_published_image,
                                              pl18_published_manifest):
    """Pad first on an active falling Written track: CTPlay takes the press (the falling strum), so stock's listener
    has nothing to add: PL18's accepted gap (a). The same script on the published PL18 (falling strum): the same."""
    for image, m in ((pl18_published_image, pl18_published_manifest), (pl19_image, pl19_manifest)):
        h = NoteHarness(image)
        if image is pl19_image:
            written(h, m, down=True)
        else:
            ready(h, m)
            set_strum(h, m, 0, 1)
            set_down(h, m, 0)
            clear(h, 0, 0)
        pad_first(h, 0, C)
        h.heartbeat(400)
        assert step_units(h, 0, 0, 0) == []
        assert h.sounding == set() and held_counts(h, m) == [0] * HELD


def test_written_entry_full_step(pl19_image, pl19_manifest):
    """A later step with six units: the note due there is left out (the step unchanged), the others land."""
    h = NoteHarness(pl19_image)
    s = settings(3, bass=1)
    written(h, pl19_manifest, s=s)
    want = roll(h, s, 1, False, 3)
    assert sorted(want) == [0, 1, 2]
    full = [n for n in range(70, 90) if n % 12 not in {x % 12 for x, _ in set().union(*want.values())}][:6]
    fill(h, 0, 0, 1, full)
    before = step_units(h, 0, 0, 1)
    step_first(h, 0, C)
    got = rolled(h)
    assert got[0] == want[0] and got[2] == want[2]
    assert step_units(h, 0, 0, 1) == before
    assert h.sounding == set() and pending(h, pl19_manifest) == [0] * SPILLS


@pytest.mark.parametrize("first", [0, 4])
def test_written_entry_second_half_wraps(pl19_image, pl19_manifest, first):
    """Review Focus: 17-32 shown, the last step 31 held (step pad 15), a slow triad: step 31 holds the first notes, the
    spill wraps to the pattern's first step; step 16 untouched, nothing past the last."""
    h = NoteHarness(pl19_image)
    written(h, pl19_manifest, first=first)
    want = roll(h, settings(1), 1, False, 3, step=31, first=first)
    assert sorted(want) == sorted({31, first})
    h.press(NEXT_HALF)                                   # (it sets the pattern's first step to 0: set it again)
    h.uc.mem_write(PATTERN_BASE[0] + 0x380, bytes([31, first, 3]))
    step_first(h, 15, C)
    assert rolled(h) == want
    assert step_units(h, 0, 0, 16) == []
    assert h.sounding == set()


def test_written_entry_wraps_at_the_last_step(pl19_image, pl19_manifest):
    """A pattern over steps 3-8 (first 2, last 7, 0-based), the last step held: the spill goes to the first step, never
    past the last (step 8 untouched)."""
    h = NoteHarness(pl19_image)
    written(h, pl19_manifest, s=settings(3, bass=1), first=2, last=7)
    want = roll(h, settings(3, bass=1), 1, False, 3, step=7, first=2, last=7)
    assert sorted(want) == [2, 3, 7]
    step_first(h, 7, C)
    assert rolled(h) == want
    assert h.sounding == set() and pending(h, pl19_manifest) == [0] * SPILLS


PSET = 12                                               # Pattern Settings: a step pad = the end step, Shift + one = the start


def pattern_steps(h) -> tuple[int, int]:
    """Pattern 0's (first, last) step, 0-based."""
    last, first = h.uc.mem_read(PATTERN_BASE[0] + 0x380, 2)
    return first, last


def test_second_half_makes_a_16_step_pattern_32(pl22_image, pl22_manifest):
    """Stock: 1-16/17-32 on a 16-step pattern makes it steps 1-32 (and back to 1-16 keeps that), so a step on the
    17-32 half is inside the loop (PL22's TEST.md B first assumed it was outside)."""
    h = NoteHarness(pl22_image)
    written(h, pl22_manifest, first=0, last=15)
    h.press(NEXT_HALF)
    assert pattern_steps(h) == (0, 31)
    h.press(NEXT_HALF)
    assert pattern_steps(h) == (0, 31)


@pytest.mark.parametrize("case", ["before a start at 5", "step 32, the end at 31"])
def test_written_entry_outside_the_loop_carries_straight_on(pl22_image, pl22_manifest, case):
    """Beta 2 (spec 2026-11-22-beta2-fixes-design.md, section 2), through stock's own presses (PL22's TEST.md B): a slow
    triad entered on a step outside first..last, step 2 before a start at step 5 (Shift + step pad 5 in Pattern
    Settings), or step 32 after the end is set to 31 on the 17-32 half: the roll goes on from the held step as the step
    pads show, a note past step 32 is dropped, and no note lands in the loop that was not put there (PL21 wrapped the
    spill into it)."""
    h = NoteHarness(pl22_image)
    written(h, pl22_manifest, first=0, last=15)
    if case == "before a start at 5":
        h.press(PSET)
        h.shift(True)
        h.down(4)
        h.up(4)
        h.shift(False)
        held, loop = 1, (4, 15)
    else:
        h.press(NEXT_HALF)                               # steps 1-32 (stock), the 17-32 half shown
        h.press(PSET)
        h.down(14)                                       # step pad 15 of the 17-32 half: the end at step 31
        h.up(14)
        held, loop = 31, (0, 30)
    assert pattern_steps(h) == loop
    h.track(0)
    want = {st: n for st, n in roll(h, settings(1), 1, False, 3, step=held, first=loop[0], last=loop[1]).items()
            if st < 32}
    step_first(h, held % 16, C)
    got = rolled(h)
    assert got == want
    assert all(st == held or not loop[0] <= st <= loop[1] for st in got), "nothing put into the loop but the held step"
    assert sorted(got) == ([1, 2] if held == 1 else [31])  # step 32's third note (past step 32) dropped
    assert h.sounding == set()


REMOVE_CASES = {"rising triad 1-16": (settings(1), False, 3), "falling triad 1-16": (settings(1), True, 3),
                "rising 9th bass 1-32": (settings(3, bass=1), False, 1)}


@pytest.mark.parametrize("case", list(REMOVE_CASES))
def test_written_entry_removed(pl19_image, pl19_manifest, case):
    """The pad again with the step held takes the roll out: the held step on the press, the spilled steps on the
    release; other notes there are kept. Falling slow at 1/16 (C spilled) and rising with bass at 1/32 (the root
    spilled) go through the roll's signature (the pad's pitch is not in the held step)."""
    s, down, rate = REMOVE_CASES[case]
    h = NoteHarness(pl19_image)
    m = pl19_manifest
    written(h, m, s=s, down=down, rate=rate)
    want = roll(h, s, 1, down, rate)
    pitch = h.pitch(0, C)
    if case != "rising triad 1-16":
        assert (pitch, 0) not in want[0] and all(n != pitch for n, _ in want[0])   # the pad's note spilled
    names = {n % 12 for n, _ in set().union(*want.values())}
    outside = next(n for n in range(60, 90) if n % 12 not in names)
    for st in range(8):
        fill(h, 0, 0, st, [outside])
    step_first(h, 0, C)
    got = rolled(h)
    assert all(want[st] <= got[st] for st in want), (got, want)
    step_again(h, 0, C)
    assert rolled(h) == {st: {(outside, 0)} for st in range(8)}
    assert h.sounding == set()
    assert held_counts(h, m) == [0] * HELD and pending(h, m) == [0] * SPILLS


NOT_REMOVAL = {"another chord's roll": (True, 3), "one note of the chord": (True, 3),
               "a single chord note at 1-32": (False, 1), "Eb's roll at 1-16": (False, 3)}


@pytest.mark.parametrize("what", list(NOT_REMOVAL))
def test_written_entry_not_a_removal(pl19_image, pl19_manifest, what):
    """The pad's note not in the held step, and the pad's own roll not there exactly (each note at its pitch and
    microstep): the press takes the roll in, nothing is removed. Falling slow at 1/16: another chord's roll (F), one
    note of the chord at microstep 0 alone. Rising slow at 1/32 (only the first note in the held step): a stock single
    3rd at microstep 0. Rising slow at 1/16: Eb's roll (Eb at 0, G at 4: the C chord's note names at its positions)."""
    down, rate = NOT_REMOVAL[what]
    h = NoteHarness(pl19_image)
    m = pl19_manifest
    written(h, m, down=down, rate=rate)
    want = roll(h, settings(1), 1, down, rate)
    ch = chord(h, 0, C, settings(1))
    if what == "another chord's roll":
        step_first(h, 0, pads_for_classes(h, 0, (5,))[0])
    elif what == "one note of the chord":
        fill(h, 0, 0, 0, [max(ch)])
    elif what == "a single chord note at 1-32":
        fill(h, 0, 0, 0, [sorted(ch)[1]])
    else:
        step_first(h, 0, pads_for_classes(h, 0, (3,))[0])
    before = rolled(h)
    assert before
    step_first(h, 0, C)
    got = rolled(h)
    assert all(before[st] <= got.get(st, set()) for st in before), (before, got)
    assert all(n in {x for x, _ in got.get(st, set())} for st in want for n, _ in want[st]), (got, want)
    assert h.sounding == set() and pending(h, m) == [0] * SPILLS


def test_written_pad_first_several_steps(pl19_image, pl19_manifest):
    """Stock's "hold a note, tap steps": a key pad held, steps 1 and 5 tapped, one release: both rolls whole (one
    pending record per step)."""
    h = NoteHarness(pl19_image)
    m = pl19_manifest
    s = settings(3, bass=1)
    written(h, m, s=s)
    want = {}
    for st in (0, 4):
        for k, v in roll(h, s, 1, False, 3, step=st).items():
            want.setdefault(k, set()).update(v)
    h.down(C)
    h.heartbeat(400)
    for st in (0, 4):
        h.down(st)
        h.up(st)
    assert set(rolled(h)) == {0, 4}                     # the in-step notes only, until the pad's release
    h.up(C)
    h.heartbeat(5)
    assert rolled(h) == want
    assert h.sounding == set() and pending(h, m) == [0] * SPILLS


@pytest.mark.parametrize("how", ["played block chord", "roll entered fast"])
def test_written_pad_again_without_its_exact_roll(pl19_image, pl19_manifest, how):
    """The pad's pitch in the held step but not its exact roll: a block chord entered while the track was Played (TEST.md
    34c-35c), or a roll entered at another strum speed (fast, then the speed set to slow). The pad again on Written takes
    the whole chord out of the held step by note name (PL18's removal), nothing is pended; the pad once more writes
    exactly the roll."""
    h = NoteHarness(pl19_image)
    m = pl19_manifest
    if how == "played block chord":
        written(h, m, mode=1)
        step_first(h, 0, C)
        assert rolled(h) == {0: {(n, 0) for n in chord(h, 0, C, settings(1))}}
        set_pstrum(h, m, 0, WRITTEN)
    else:
        written(h, m, speed=3)
        step_first(h, 0, C)
        assert rolled(h) == roll(h, settings(1), 3, False, 3)
        set_strum(h, m, 0, 1)
    step_again(h, 0, C)
    assert rolled(h) == {}
    assert pending(h, m) == [0] * SPILLS
    step_first(h, 0, C)
    assert rolled(h) == roll(h, settings(1), 1, False, 3)
    assert h.sounding == set() and pending(h, m) == [0] * SPILLS


def test_written_entry_survives_a_stock_edit(pl19_image, pl19_manifest):
    """After a roll, stock's single-note add on a spilled step keeps the spilled unit."""
    h = NoteHarness(pl19_image)
    m = pl19_manifest
    written(h, m)
    want = roll(h, settings(1), 1, False, 3)
    step_first(h, 0, C)
    assert rolled(h) == want
    set_step(h, m, 0, False)
    step_first(h, 1, OTHER)
    assert rolled(h)[1] == want[1] | {(h.pitch(0, OTHER), 0)}
    assert h.sounding == set()


def test_written_entry_plays_the_roll(pl19_image, pl19_manifest):
    """Play: the synth plays the roll's notes at their microsteps (1/16, slow: 0, 4 and 8 ticks)."""
    h = NoteHarness(pl19_image)
    m = pl19_manifest
    written(h, m)
    step_first(h, 0, C)
    notes = rm.roll_order(chord(h, 0, C, settings(1)), False)
    h.take()
    h.press(PLAY)
    first = {}
    for _ in range(400):
        h.heartbeat(1)
        tk = h.r32(sym(m, "arp_tick"))
        for e in h.take("synth_on"):
            if e[1] == 0:
                first.setdefault(pitch_of(h, e[2]), tk)
    h.press(PLAY)
    h.heartbeat(300)
    assert sorted(first) == sorted(notes)
    t0 = first[notes[0]]
    assert [first[n] - t0 for n in notes] == [0, 4, 8]
    assert h.sounding == set()


def test_no_pattern_write_on_the_press(pl19_image, pl19_manifest):
    """The phantom-press rule: the controller's pad press writes nothing into the spilled steps, touches no store
    (rec_touch) and masks no interrupts; the release writes them (each unit's bytes and mask bit in a few masked
    instructions, which the release may do) and touches once."""
    h = NoteHarness(pl19_image)
    m = pl19_manifest
    s = settings(3, bass=1)
    written(h, m, s=s)
    want = roll(h, s, 1, False, 3)
    lo, hi = step_addr(0, 0, 1), step_addr(0, 0, 3) - 1
    writes, touches, masked = [], [], []
    hooks = [h.uc.hook_add(UC_HOOK_MEM_WRITE, lambda u, a, *x: writes.append(a), begin=lo, end=hi),
             h.uc.hook_add(UC_HOOK_CODE, lambda *x: touches.append(1), begin=REC_TOUCH, end=REC_TOUCH),
             h.uc.hook_add(UC_HOOK_CODE, lambda *x: masked.append(1), begin=sym(m, "slim_irq_save") & ~1,
                           end=sym(m, "slim_irq_save") & ~1)]
    h.down(0)
    h.down(C)
    assert (writes, touches, masked) == ([], [], [])
    h.up(C)
    assert writes and touches == [1] and masked                              # the release: masked unit writes
    for k in hooks:
        h.uc.hook_del(k)
    h.up(0)
    h.heartbeat(5)
    assert rolled(h) == want
    assert h.sounding == set()


def test_written_spill_takes_another_unit_when_raced(pl19_image, pl19_manifest):
    """A Main-task commit taking the spill's unit between the release's scan and its masked write (simulated at the
    masked section's entry): the spilled note goes into the next free unit, the other note keeps its unit."""
    h = NoteHarness(pl19_image)
    m = pl19_manifest
    written(h, m)
    want = roll(h, settings(1), 1, False, 3)
    assert sorted(want) == [0, 1]
    other = next(n for n in range(70, 90) if n % 12 not in {x % 12 for x, _ in want[1]})
    taken = []

    def race(uc, address, size, data):
        if not taken:                                   # the first masked section of the release: step 2's unit 0
            a = step_addr(0, 0, 1)
            uc.mem_write(a + 4, bytes([other, 6, 0, 90]))
            uc.mem_write(a, bytes([h.r8(a) | 1]))
            taken.append(1)
    irq = sym(m, "slim_irq_save") & ~1
    h.down(0)
    h.down(C)
    k = h.uc.hook_add(UC_HOOK_CODE, race, begin=irq, end=irq)
    h.up(C)
    h.uc.hook_del(k)
    h.up(0)
    h.heartbeat(5)
    assert taken
    assert step_units(h, 0, 0, 1)[0] == (other, 6, 0, 90)
    assert rolled(h) == {0: want[0], 1: want[1] | {(other, 0)}}
    assert h.sounding == set()


def test_written_spill_dropped_by_a_project_load(pl19_image, pl19_manifest):
    """A project load while an entry's pad is still held drops its pending spill (chord_saved_fix): the pad's release
    afterwards writes nothing into the loaded project's pattern."""
    from test_saved import load, write_tail
    h = NoteHarness(pl19_image)
    m = pl19_manifest
    h.leds()
    written(h, m)
    want = roll(h, settings(1), 1, False, 3)
    h.down(0)
    h.down(C)
    assert pending(h, m) != [0] * SPILLS
    write_tail(h, bytes(1000))                           # a project without CTPlay's block
    load(h)
    h.leds()                                             # the frame that applies it
    assert pending(h, m) == [0] * SPILLS
    clear(h, 0, 1)
    h.up(C)
    h.up(0)
    h.heartbeat(5)
    assert not {x for x in want[1]} & {(u[0], u[2]) for u in step_units(h, 0, 0, 1)}
    assert h.sounding == set()


def neighbour_pads(h):
    """The reviewer's probe: per pitch class the highest key pad at 60 or above."""
    return {h.pitch(0, q) % 12: q for q in range(16, 32) if h.pitch(0, q) >= 60}


def flat(r):
    return {(st, x) for st, v in r.items() for x in v}


NEIGHBOURS = {"C then Eb triads slow": (settings(1), 1, 0, 3, False),
              "Cm7 then Ebmaj7 medium": (settings(2), 2, 0, 3, False),
              "F then C triads slow": (settings(1), 1, 5, 0, False),
              "G entered first, then C triads slow": (settings(1), 1, 0, 7, True)}
STOCK_CASE = ("G entered first, then C triads slow", "second")   # stock's own-pitch removal: its own test below


def neighbours(image, m, case):
    """Rolls A (step 1) and B (step 2), 1/16, rising, step first, A entered first unless the case says B: the harness
    and both models. (B first matters when A's tail holds B's pad pitch: entering B onto it would be stock's removal.)"""
    s, speed, a, b, b_first = NEIGHBOURS[case]
    h = NoteHarness(image)
    written(h, m, s=s, speed=speed)
    pads = neighbour_pads(h)
    pa, pb = pads[a], pads[b]
    ra, rb = roll(h, s, speed, False, 3, step=0, pad=pa), roll(h, s, speed, False, 3, step=1, pad=pb)
    for st, pad in ((1, pb), (0, pa)) if b_first else ((0, pa), (1, pb)):
        step_first(h, st, pad)
    return h, pa, pb, flat(ra), flat(rb)


@pytest.mark.parametrize("case", list(NEIGHBOURS))
def test_written_neighbour_rolls_enter_whole(pl19_image, pl19_manifest, case):
    """Review finding: a roll's tail in the next step shares pitches with that step's own roll. Both go in whole: a
    duplicate is the same note at the same microstep (scale C minor, 1/16)."""
    h, pa, pb, ra, rb = neighbours(pl19_image, pl19_manifest, case)
    assert {n % 12 for _, (n, _) in ra} & {n % 12 for _, (n, _) in rb}, "the case must share a note name"
    assert flat(rolled(h)) == ra | rb
    assert h.sounding == set() and pending(h, pl19_manifest) == [0] * SPILLS


REMOVALS = [(c, w) for c in NEIGHBOURS for w in ("first", "second") if (c, w) != STOCK_CASE]


@pytest.mark.parametrize("case, which", REMOVALS, ids=[f"{c}-remove {w}" for c, w in REMOVALS])
def test_written_neighbour_removal_keeps_the_other(pl19_image, pl19_manifest, case, which):
    """Removing one of two neighbour rolls (its pad again on its step) leaves the other whole: CTPlay removes only the
    roll's own positions with their exact notes. F then C: F's spilled C (72) shares its note name, not its pitch, with
    the C pad (60), so it stays (the reviewer's probe saw CTPlay's old by-name removal take it)."""
    h, pa, pb, ra, rb = neighbours(pl19_image, pl19_manifest, case)
    assert not ra & rb
    if which == "first":
        step_again(h, 0, pa)
        assert flat(rolled(h)) == rb
    else:
        step_again(h, 1, pb)
        assert flat(rolled(h)) == ra
    assert h.sounding == set() and pending(h, pl19_manifest) == [0] * SPILLS


def test_written_neighbour_stock_own_pitch_removal(pl19_image, pl19_manifest):
    """Stock's own removal stays stock's: G's roll on step 2, then C's on step 1, which spills its G (67) into step 2 at
    microstep 2 (beside G's own 67 at microstep 0: both go in). The G pad's pitch is 67, so G's pad again on step 2 makes
    stock remove every unit of the held step holding 67, C's spilled G included (any microstep). The rest of C's roll
    stays. The guide says so (Written limits)."""
    h, pc, pg, rc, rg = neighbours(pl19_image, pl19_manifest, STOCK_CASE[0])
    pitch = h.pitch(0, pg)
    lost = {(st, x) for st, x in rc if st == 1 and x[0] == pitch}
    assert lost and all(x[1] != 0 for _, x in lost)                           # C's G, at another microstep
    step_again(h, 1, pg)
    assert flat(rolled(h)) == rc - lost
    assert h.sounding == set() and pending(h, pl19_manifest) == [0] * SPILLS


@pytest.mark.parametrize("seed", range(1, 9))
def test_written_fuzz(seed, pl19_image, pl19_manifest):
    """Every track Written with step-entry chords and a slow strum: the fuzz's step pads and key pads in every order
    leave nothing sounding, no chord entry and no pending spill."""
    m = pl19_manifest
    steps = fuzz_script(seed)
    h = NoteHarness(pl19_image)
    h.call(sym(m, "slim_ready"))
    h.uc.mem_write(sym(m, "chord_step"), b"\x0f")
    h.uc.mem_write(sym(m, "chord_pstrum"), b"\xaa")
    h.uc.mem_write(sym(m, "chord_strum"), b"\x55")
    before = pattern_snapshot(h, 0)
    fuzz_run(h, steps)
    h.heartbeat(300)
    print(f"written seed {seed}: {len(recorded_notes(h, 0, before))} track 0 units written")
    assert h.sounding == set(), f"seed {seed}: {sorted(h.sounding)} left on; script {steps}"
    assert held_counts(h, m) == [0] * HELD, f"seed {seed}: chord entries left; script {steps}"
    assert pending(h, m) == [0] * SPILLS, f"seed {seed}: a pending spill left; script {steps}"


OFF_CASES = ["off, strum on", "written, strum off"]


@pytest.mark.parametrize("case", OFF_CASES)
@pytest.mark.parametrize("route", ["step first", "pad first"])
def test_off_step_entry_is_pl18(pl19_image, pl19_manifest, pl18_published_image, pl18_published_manifest, case,
                                route):
    """Pattern strum off (or Written with the strum off: not active): PL18's step entry, add and removal, byte for
    byte against the published PL18 (a rising slow strum on there, as on here)."""
    snaps = []
    for image, m in ((pl18_published_image, pl18_published_manifest), (pl19_image, pl19_manifest)):
        h = NoteHarness(image)
        ready(h, m)
        set_strum(h, m, 0, 0 if case == "written, strum off" else 1)
        if image is pl19_image and case == "written, strum off":
            set_pstrum(h, m, 0, WRITTEN)
        stock_script(h, route)
        h.heartbeat(400)
        assert h.sounding == set()
        snaps.append(used_steps(h, 0))
    assert snaps[1] == snaps[0]


# ---- PL20 (trig conditions, Task 9): a note step's condition (bytes [2]-[3]) goes with its last note, in a marked
# project: stock's removal, PL18's chord removal and PL19's Written roll removal (the held step on the press, a spilled
# step on the pad's release). A step that keeps a note keeps it; an entry back into an emptied step has none.

COND_A, COND_B = 0x1A5, 0x0C3                           # 9-bit codes, bit 8 on / off


def set_cond(h, s, code, p=0):
    h.uc.mem_write(step_addr(0, p, s) + 2, bytes([code & 0xFF, code >> 8]))


def cond(h, s, p=0):
    """Step s's bytes [2]-[3] as the code (bit 8 in [3] bit 0; [3]'s other bits must be 0)."""
    lo, hi = h.uc.mem_read(step_addr(0, p, s) + 2, 2)
    return lo | hi << 8


def set_mark(h, m, on):
    h.uc.mem_write(sym(m, "trig_mark"), bytes([on]))


@pytest.mark.parametrize("chord_on", [False, True], ids=["chord step off", "chord step on"])
def test_last_note_removed_drops_its_condition(pl21_image, pl21_manifest, chord_on):
    """Stock's removal of the key's only note empties the step: its condition goes; a step of two notes, one removed,
    keeps it; an entry back into the emptied step has none. With the chord step on, PL18's chord removal emptying a
    step does the same. Unmarked: nothing changes."""
    m = pl21_manifest
    h = NoteHarness(pl21_image)
    ready(h, m, step=chord_on)
    set_mark(h, m, 1)
    c = h.pitch(0, C)
    names = {n % 12 for n in chord(h, 0, C, settings(1))}
    other = next(n for n in range(c + 1, c + 12) if n % 12 not in names)
    fill(h, 0, 0, 0, [c])
    fill(h, 0, 0, 1, [c, other])
    set_cond(h, 0, COND_A)
    set_cond(h, 1, COND_B)
    step_again(h, 0, C)
    assert units(h, 0, 0, 0) == [] and cond(h, 0) == 0
    step_again(h, 1, C)
    assert units(h, 0, 0, 1) == [other] and cond(h, 1) == COND_B
    step_first(h, 0, C)                                 # back in
    assert units(h, 0, 0, 0) and cond(h, 0) == 0
    if chord_on:                                        # PL18: the pad again takes its whole chord out
        clear(h, 0, 2)
        step_first(h, 2, C)
        assert len(units(h, 0, 0, 2)) == 3
        set_cond(h, 2, COND_A)
        step_again(h, 2, C)
        assert units(h, 0, 0, 2) == [] and cond(h, 2) == 0
        step_first(h, 2, C)
        assert len(units(h, 0, 0, 2)) == 3 and cond(h, 2) == 0
    set_mark(h, m, 0)                                   # unmarked: as PL19
    fill(h, 0, 0, 3, [c])
    set_cond(h, 3, COND_A)
    step_again(h, 3, C)
    assert units(h, 0, 0, 3) == [] and cond(h, 3) == COND_A
    assert h.sounding == set()


@pytest.mark.parametrize("down", [False, True], ids=["rising", "falling"])
def test_last_note_removed_drops_its_condition_written(pl21_image, pl21_manifest, down):
    """PL19's Written roll removal at 1/16 (rising: the pad's note in the held step, stock removes it; falling: it
    spilled, CTPlay removes the whole roll): the held step (on the press) and the spilled step (on the release) lose
    their conditions; a step with another note keeps its; the roll entered again has none."""
    m = pl21_manifest
    h = NoteHarness(pl21_image)
    written(h, m, down=down, rate=3)
    set_mark(h, m, 1)
    want = roll(h, settings(1), 1, down, 3)
    assert sorted(want) == [0, 1]                       # the held step and one spilled step
    names = {n % 12 for n, _ in set().union(*want.values())}
    outside = next(n for n in range(60, 90) if n % 12 not in names)
    fill(h, 0, 0, 6, [outside])
    step_first(h, 0, C)
    assert rolled(h) == {**want, 6: {(outside, 0)}}
    for st in (0, 1):
        set_cond(h, st, COND_A)
    set_cond(h, 6, COND_B)
    step_again(h, 0, C)
    assert rolled(h) == {6: {(outside, 0)}}
    assert [cond(h, st) for st in (0, 1, 6)] == [0, 0, COND_B]
    step_first(h, 0, C)
    assert rolled(h) == {**want, 6: {(outside, 0)}}
    assert [cond(h, st) for st in (0, 1, 6)] == [0, 0, COND_B]
    assert h.sounding == set() and pending(h, m) == [0] * SPILLS
