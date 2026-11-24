"""PL04 chord voice room (spec 2026-10-13-chord-voice-room-design.md): the one-voice floor."""
import pytest

from chord_model import chord_notes, degree_class, settings
from notes import NOTE_EXPANDED, ROOT, SCALE_MASK, NoteHarness
from test_chord import GAP, held_counts, pick, set_down, set_strum
from voices import SLOTS, VoiceHarness

pytestmark = pytest.mark.emu
ONE_AND_A_TENTH = 0x11D00            # PL03D #3: the 5th note had room for 1.11 voices
UNDER_ONE = 0xE000                   # 0.875 voices
STEP_7 = [0x52100, 0x42E00, 0x31300, 0x22800, 0x11D00]   # PL03D #3, rootless 9th, slow strum


def triad(h, track=0):
    h.track(track)
    pick(h, 25)                                      # triad (Shift + pad 26: palette pads 24-31 = shapes 0-7)


def test_chord_notes_take_a_free_voice_and_the_pad_note_keeps_stocks_rule(pl09_image):
    h = VoiceHarness(pl09_image)
    triad(h)
    h.script = [ONE_AND_A_TENTH] * 3
    h.down(20, 100)                                  # chord.c sends 2 notes, then stock plays the pad's own
    assert [d["dsp"] for d in h.decisions] == [0, 0, 1]


def test_under_one_voice_stock_steals(pl09_image):
    h = VoiceHarness(pl09_image)
    triad(h)
    h.script = [UNDER_ONE] * 3
    h.down(20, 100)
    assert [d["dsp"] for d in h.decisions] == [1, 1, 1]


def test_no_free_voice_no_change(pl09_image):
    h = VoiceHarness(pl09_image)
    triad(h)
    for v in range(6):
        h.uc.mem_write(SLOTS + 16 * v + 4, (0x0001FFFF).to_bytes(4, "little"))     # all sounding
    h.script = [ONE_AND_A_TENTH] * 3
    h.down(20, 100)
    assert [d["dsp"] for d in h.decisions] == [1, 1, 1]


def test_synth_2_chord_notes_get_the_floor_too(pl09_image):
    h = VoiceHarness(pl09_image)
    triad(h, track=1)
    h.script = [ONE_AND_A_TENTH] * 3
    h.down(20, 100)
    assert [d["dsp"] for d in h.decisions] == [0, 0, 1] and {d["synth"] for d in h.decisions} == {1}


def test_step_7_keeps_the_bass(pl09_image, pl09_manifest):
    h = VoiceHarness(pl09_image)
    h.set_voice_mode(0, 2)                           # Poly, as the device patch (the snapshot's Synth 1 is Mono AG)
    h.track(0)
    pick(h, 27)
    pick(h, 23)
    pick(h, 23)                                      # 9th, rootless over bass
    set_strum(h, pl09_manifest, 0, 1)
    h.script = list(STEP_7)
    h.down(17, 100)
    h.heartbeat(4 * GAP[1])
    d = h.decisions
    assert [x["dsp"] for x in d] == [0, 0, 0, 0, 0]
    assert len({x["voice"] for x in d}) == 5         # five voices: the bass's is never taken


# ---- the 5-note fallback
HEAVY = [0x40000, 0x30000, 0x20000, 0x14000, 0x10000]       # one voice of room less each note


def strum(h, manifest, shape_pad, bass_presses, speed=1, track=0, view=1):
    h.track(track, view)
    pick(h, shape_pad)
    for _ in range(bass_presses):
        pick(h, 23)
    set_strum(h, manifest, track, speed)


def sounded(h):
    return [e[2] for e in h.take("synth_on")]


def classes_of(h, track, pad):
    return h.pitch(track, pad), h.r32(SCALE_MASK)


def endpoint_class(h, cls):
    return (cls + h.r8(ROOT) - 12) % 12


def test_heavy_rootless_9th_leaves_out_its_5th(pl09_image, pl09_manifest):
    h = VoiceHarness(pl09_image)
    strum(h, pl09_manifest, 27, 2)                    # 9th, rootless over bass
    h.script = list(HEAVY)
    root, mask = classes_of(h, 0, 17)
    h.take()
    h.down(17, 100)
    h.heartbeat(5 * GAP[1])
    notes = sounded(h)
    fifth = endpoint_class(h, degree_class(root, mask, 4))
    assert len(notes) == 4 and all(n % 12 != fifth for n in notes[1:])
    h.up(17)
    h.heartbeat()
    assert sorted(e[2] for e in h.take("synth_off")) == sorted(notes)       # each sounded note ends, once


def test_falling_strum_voice_room_fallback(pl09_image, pl09_manifest):
    """PL08: falling, the rootless 9th's left-out 5th is the same tone as rising (the 3rd note: two readings)."""
    h = VoiceHarness(pl09_image)
    strum(h, pl09_manifest, 27, 2)                    # 9th, rootless over bass
    set_down(h, pl09_manifest, 0)
    h.script = list(HEAVY)
    root, mask = classes_of(h, 0, 17)
    h.take()
    h.down(17, 100)
    h.heartbeat(6 * GAP[1])
    notes = sounded(h)
    fifth = endpoint_class(h, degree_class(root, mask, 4))
    assert len(notes) == 4 and all(n % 12 != fifth for n in notes) and notes == sorted(notes, reverse=True)
    h.up(17)
    h.heartbeat()
    assert sorted(e[2] for e in h.take("synth_off")) == sorted(notes)       # each sounded note ends, once
    assert held_counts(h, pl09_manifest) == [0] * 6


def test_heavy_bass_below_9th_leaves_out_its_9th(pl09_image, pl09_manifest):
    h = VoiceHarness(pl09_image)
    strum(h, pl09_manifest, 27, 1)                    # 9th, bass below (already without its 5th)
    h.script = list(HEAVY)
    root, mask = classes_of(h, 0, 17)
    h.take()
    h.down(17, 100)
    h.heartbeat(5 * GAP[1])
    notes = sounded(h)
    ninth = endpoint_class(h, degree_class(root, mask, 8))
    assert len(notes) == 4 and all(n % 12 != ninth for n in notes)


def test_room_for_all_five_keeps_all_five(pl09_image, pl09_manifest):
    h = VoiceHarness(pl09_image)
    strum(h, pl09_manifest, 27, 2)
    h.script = list(STEP_7)
    h.take()
    h.down(17, 100)
    h.heartbeat(5 * GAP[1])
    assert len(sounded(h)) == 5


def test_one_burst_chord_is_never_shortened(pl09_image, pl09_manifest):
    h = VoiceHarness(pl09_image)
    strum(h, pl09_manifest, 27, 2, speed=0)
    h.script = list(HEAVY)
    h.take()
    h.down(17, 100)
    assert len(sounded(h)) == 5


def test_synth_2_heavy_drops_too(pl09_image, pl09_manifest):
    h = VoiceHarness(pl09_image)
    strum(h, pl09_manifest, 27, 2, track=1)
    h.script = list(HEAVY)
    h.take()
    h.down(17, 100)
    h.heartbeat(5 * GAP[1])
    assert len(sounded(h)) == 4


def test_rising_readings_never_drop(pl09_image, pl09_manifest):
    h = VoiceHarness(pl09_image)
    strum(h, pl09_manifest, 27, 2)
    h.script = [0x20000, 0x28000, 0x30000, 0x38000, 0x40000]
    h.take()
    h.down(17, 100)
    h.heartbeat(5 * GAP[1])
    assert len(sounded(h)) == 5


def test_released_before_the_droppable_tone(pl09_image, pl09_manifest):
    h = VoiceHarness(pl09_image)
    strum(h, pl09_manifest, 27, 2)
    h.script = list(HEAVY)
    h.take()
    h.down(17, 100)
    h.heartbeat(GAP[1])                              # the pad note and the 3rd
    h.up(17)
    h.heartbeat(5 * GAP[1])
    ev = h.take("synth_on", "synth_off")                         # one take: it clears the whole log
    on = [e[2] for e in ev if e[0] == "synth_on"]
    off = [e[2] for e in ev if e[0] == "synth_off"]
    assert len(on) == 2 and sorted(off) == sorted(on)


def test_no_readings_no_drop(pl09_image, pl09_manifest):
    """NoteHarness stubs the synth: no voice decision runs, so there is nothing to estimate from."""
    h = NoteHarness(pl09_image)
    strum(h, pl09_manifest, 27, 2)
    h.take()
    h.down(17, 100)
    h.heartbeat(5 * GAP[1])
    assert len(h.take("synth_on")) == 5


def test_midi_track_chord_is_unchanged(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    strum(h, pl09_manifest, 27, 2, track=2)
    h.take()
    h.down(17, 100)
    h.heartbeat(5 * GAP[1])
    assert len(h.take("midi_on")) == 5


def test_a_left_out_tone_never_lights(pl09_image, pl09_manifest):
    h = VoiceHarness(pl09_image)
    strum(h, pl09_manifest, 27, 2, view=NOTE_EXPANDED)
    h.script = list(HEAVY)
    root, mask = classes_of(h, 0, 24)                   # pad 25, bottom left: the lowest key, the chord above it
    fifth = [n for n in chord_notes(root, mask, settings(3, bass=1, rootless=1)) if n % 12 == degree_class(root, mask, 4)]
    h.down(24, 100)
    h.heartbeat(5 * GAP[1])
    lit = h.leds()
    pads = [p for p in range(32) if h.pitch(0, p) in fifth]
    assert pads, "the left-out 5th must be on screen for this test to mean anything"
    assert all(lit[p] != lit[24] for p in pads)
    h.up(24)
    h.heartbeat()


def test_release_during_a_drop_is_not_lost(pl09_image, pl09_manifest):
    """Final review: the heartbeat must not write back `flags` (a read-modify-write across calls) while the UI task's
    release() may set HELD_RELEASED in it. The release is simulated inside the drop's shift loop."""
    from unicorn import UC_HOOK_MEM_READ
    h = VoiceHarness(pl09_image)
    strum(h, pl09_manifest, 27, 2)
    h.script = list(HEAVY)
    h.take()
    h.down(17, 100)
    h.heartbeat(GAP[1] - 1)                          # the 3rd is due on the next beat, the 5th (left out) one gap later
    held = int(pl09_manifest["symbols"]["held"], 16)
    fired = []

    def release_now(u, acc, a, s, v, d):             # held[0]: count, track, pad, notes[4] (+3), sent, vel, flags (+9)
        fired.append(a)
        u.mem_write(held + 9, bytes([u.mem_read(held + 9, 1)[0] | 0x02]))
    hk = h.uc.hook_add(UC_HOOK_MEM_READ, release_now, begin=held + 3 + 2, end=held + 3 + 2)   # notes[2]: the shift
    h.heartbeat(GAP[1] + 1)
    h.uc.hook_del(hk)
    h.heartbeat(3)
    assert fired, "the shift loop must have run (the drop) for this test to mean anything"
    assert held_counts(h, pl09_manifest)[0] == 0                     # the release was seen: the entry is free
    ev = h.take("synth_on", "synth_off")
    on = [e[2] for e in ev if e[0] == "synth_on"][1:]                 # the strummed notes (not stock's pad note)
    off = [e[2] for e in ev if e[0] == "synth_off"]
    assert on and all(n in off for n in on)


@pytest.mark.parametrize("voicing", [(18,), (22,), (18, 22)])     # inversion 2, wide spread, both (Shift + pads 19 / 23)
def test_heavy_left_out_5th_when_it_is_the_first_chord_note(pl09_image, pl09_manifest, voicing):
    """Final review: sorted rising, the 5th can be the first chord note; then only the pad note's reading is in the
    chord, and the estimate takes one voice per note (the reading's own unit)."""
    h = VoiceHarness(pl09_image)
    strum(h, pl09_manifest, 27, 2)                    # 9th, rootless over bass
    for pad in voicing:
        pick(h, pad)
    h.script = [0x40000, 0x30000, 0x20000, 0x10000, 0x8000]
    root, mask = classes_of(h, 0, 17)
    h.take()
    h.down(17, 100)
    h.heartbeat(5 * GAP[1])
    notes = sounded(h)
    fifth = endpoint_class(h, degree_class(root, mask, 4))
    assert len(notes) == 4 and all(n % 12 != fifth for n in notes[1:])
    assert all(d["dsp"] == 0 for d in h.decisions)                  # no sounding voice stolen
