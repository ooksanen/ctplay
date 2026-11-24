"""The arpeggiator (spec 2026-10-14-arpeggiator-design.md section 3) in emulation."""
import struct

import pytest
from unicorn.arm_const import UC_ARM_REG_R0

import arp_model
from harness import Harness
from notes import OUTBUF

pytestmark = pytest.mark.emu


def sym(m, name):
    return int(m["symbols"][name], 16)


def test_rate_ticks_match_the_model(pl09_image, pl09_manifest):
    h = Harness(pl09_image)
    for a0 in range(256):
        h.call(sym(pl09_manifest, "arp_rate_ticks"), a0)
        assert h.uc.reg_read(UC_ARM_REG_R0) == arp_model.rate_ticks(a0), hex(a0)


RATES = [r << 3 | mod << 5 for r in range(4) for mod in range(3)]


def test_gate_ticks_match_the_model(pl09_image, pl09_manifest):
    assert [arp_model.gate_ticks(2 << 3, g << 2) for g in range(6)] == [1, 2, 3, 4, 5, 0]     # 1/16
    assert [arp_model.gate_ticks(1 << 3, g << 2) for g in range(6)] == [2, 4, 6, 8, 10, 0]    # 1/8
    assert [arp_model.gate_ticks(3 << 3, g << 2) for g in range(6)] == [1, 1, 2, 2, 2, 0]     # 1/32


def test_gate_ticks_match_the_model_in_c(pl09_image, pl09_manifest):
    h = Harness(pl09_image)
    for a0 in RATES:
        for g in range(6):
            h.call(sym(pl09_manifest, "arp_gate_ticks"), a0, g << 2 | 3)                    # octaves bits ignored
            assert h.uc.reg_read(UC_ARM_REG_R0) == arp_model.gate_ticks(a0, g << 2), (hex(a0), g)


def test_gate_ms_match_the_model(pl09_image, pl09_manifest):
    h = Harness(pl09_image)
    for a0 in RATES:
        for g in range(6):
            for bpm in (60, 94, 120, 240):
                h.call(sym(pl09_manifest, "arp_gate_ms"), a0, g << 2, bpm)
                assert h.uc.reg_read(UC_ARM_REG_R0) == arp_model.gate_ms(a0, g << 2, bpm), (hex(a0), g, bpm)


def test_index_matches_the_model(pl09_image, pl09_manifest):
    h = Harness(pl09_image)
    bad = []
    for pattern in range(1, 7):
        for n in (1, 2, 3, 5, 16, 64):
            rng, last = 0xACE1, 0
            for pos in range(140):
                h.uc.mem_write(OUTBUF, struct.pack("<H", rng))
                h.call(sym(pl09_manifest, "arp_index"), pattern, pos, n | last << 8, OUTBUF)   # 4 register args
                got = h.uc.reg_read(UC_ARM_REG_R0)
                want, rng = arp_model.index(pattern, pos, n, last, rng)
                if got != want or struct.unpack("<H", h.uc.mem_read(OUTBUF, 2))[0] != rng:
                    bad.append((pattern, n, pos, got, want))
                last = want
    assert not bad, bad[:5]


from chord_model import chord_notes, settings
from notes import NOTE_EXPANDED, ROOT, SCALE_MASK, NoteHarness, endpoint_note, ms_log, param, set_tempo, TEMPO_STORE

BPM = 94                                                       # the RAM dump's tempo


def set_arp(h, m, t, a0, a1=0):
    h.call(sym(m, "slim_ready"))
    h.uc.mem_write(sym(m, "chord_arp") + 2 * t, bytes([a0, a1]))


def set_chord(h, m, t, value):
    h.call(sym(m, "slim_ready"))
    h.uc.mem_write(sym(m, "chord_settings") + t, bytes([value]))


def clock(h, m):
    return h.r32(sym(m, "arp_tick")), struct.unpack("<H", h.uc.mem_read(sym(m, "arp_acc"), 2))[0]


def due(h, m, rate, ms):
    """The ms (1-based) of the next `ms` milliseconds at which a note of `rate` ticks is due, from the clock now."""
    tick, acc = clock(h, m)
    return [t for t, k in arp_model.stopped_ticks(tick, acc, param(h, TEMPO_STORE, 0), param(h, TEMPO_STORE, 2), ms)
            if k % rate == 0]


def triad(h, track=0, pad=24):
    root = h.pitch(track, pad)
    return sorted(endpoint_note(h, p) for p in [root] + chord_notes(root, h.r32(SCALE_MASK), settings(1, key=h.r8(ROOT))))


def ons(log):
    return [(t, n) for t, k, n in log if k == "synth_on"]


@pytest.mark.parametrize("pattern, order", [(1, [0, 1, 2, 0, 1, 2]), (2, [2, 1, 0, 2, 1, 0]),
                                            (3, [0, 1, 2, 1, 0, 1]), (4, [2, 1, 0, 1, 2, 1]),
                                            (6, [0, 1, 2, 0, 1, 2])])
def test_stopped_triad_plays_the_pattern_on_the_grid(pl09_image, pl09_manifest, pattern, order):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(1))
    set_arp(h, pl09_manifest, 0, pattern | 2 << 3)                 # 1/16: 6 ticks
    notes = triad(h)
    h.take()
    h.down(24)
    assert h.take("synth_on", "midi_on") == []                     # the press plays nothing itself
    times = due(h, pl09_manifest, 6, 1100)[:6]
    got = ons(ms_log(h, times[-1]))
    assert got == [(t, notes[i]) for t, i in zip(times, order)]
    h.up(24)
    h.heartbeat(200)
    assert h.sounding == set()


def test_the_gate_lengths(pl09_image, pl09_manifest):
    """Stopped: 1/6 ... 5/6 of the step in ms from the project BPM."""
    for g in range(5):
        h = NoteHarness(pl09_image)
        h.track(0)
        set_arp(h, pl09_manifest, 0, 1 | 2 << 3, g << 2)            # chords off: one note
        h.down(24)
        t0 = due(h, pl09_manifest, 6, 400)[0]
        log = ms_log(h, t0 + 160)
        on = [t for t, k, _ in log if k == "synth_on"][0]
        off = [t for t, k, _ in log if k == "synth_off"][0]
        assert off - on == arp_model.gate_ms(2 << 3, g << 2, BPM), (g, off - on)
        h.up(24)


def test_default_gate_is_three_sixths(pl09_image, pl09_manifest):
    h = Harness(pl09_image)
    h.call(sym(pl09_manifest, "slim_ready"))
    assert [h.r8(sym(pl09_manifest, "chord_arp") + 2 * t + 1) >> 2 & 7 for t in range(4)] == [2] * 4


def test_legato_reattacks_a_repeated_pitch(pl09_image, pl09_manifest):
    """D10: an arpeggio plays separate notes; at 6/6 a pitch that sounds again is ended, then started."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3, 5 << 2)                # one note, up, legato
    h.down(24)
    times = due(h, pl09_manifest, 6, 800)[:4]
    log = ms_log(h, times[-1])
    note = endpoint_note(h, h.pitch(0, 24))
    for t in times[1:]:
        assert [(k, n) for u, k, n in log if u == t] == [("synth_off", note), ("synth_on", note)], t
    assert len([k for k in h.sounding if k[0] == "synth"]) == 1
    h.up(24)
    h.heartbeat(200)
    assert h.sounding == set()


def test_legato_overlaps_new_pitches(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(1))
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3, 5 << 2)
    h.down(24)
    times = due(h, pl09_manifest, 6, 800)[:4]
    log = ms_log(h, times[-1])
    for t in times[1:]:
        at = [(k, n) for u, k, n in log if u == t]
        assert at[0][0] == "synth_on" and at[1][0] == "synth_off"  # on before off
    assert len([k for k in h.sounding if k[0] == "synth"]) == 1
    h.up(24)
    h.heartbeat(200)
    assert h.sounding == set()


def test_octaves_and_the_chord_pattern(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(1))
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3, 1)                     # up, 2 octaves
    notes = triad(h)
    h.down(24)
    times = due(h, pl09_manifest, 6, 1200)[:6]
    assert [n for _, n in ons(ms_log(h, times[-1]))] == notes + [n + 12 for n in notes]
    h.up(24)
    h.heartbeat(200)
    set_arp(h, pl09_manifest, 0, 7 | 2 << 3, 1)                     # chord, 2 octaves
    h.take()
    h.down(24)
    times = due(h, pl09_manifest, 6, 600)[:2]
    log = ons(ms_log(h, times[-1]))
    assert sorted(n for t, n in log if t == times[0]) == notes
    assert sorted(n for t, n in log if t == times[1]) == [n + 12 for n in notes]
    h.up(24)
    h.heartbeat(200)
    assert h.sounding == set()


def test_two_tracks_keep_their_own_rates(pl09_image, pl09_manifest):
    """Synth 1 latched (it keeps playing on another view), MIDI 1 held: each on its own grid. Synth tracks also send MIDI
    out, so MIDI 1's notes are the midi_on events of track 2 (e[2])."""
    h = NoteHarness(pl09_image)
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3 | 0x80)                 # Synth 1: up, 1/16, latch
    set_arp(h, pl09_manifest, 2, 1 | 1 << 3)                        # MIDI 1: up, 1/8
    h.track(0)
    h.down(24)
    h.up(24)                                                        # latched
    h.track(2)
    h.down(24)
    t16, t8 = due(h, pl09_manifest, 6, 1000), due(h, pl09_manifest, 12, 1000)
    synth, midi = [], []
    for t in range(1, 1001):
        h.heartbeat(1)
        for e in h.take("synth_on", "midi_on"):
            (synth if e[0] == "synth_on" else midi if e[2] == 2 else []).append(t)
    assert synth == t16 and midi == t8 and len(t8) >= 3
    h.up(24)
    set_arp(h, pl09_manifest, 0, 0)                                 # pattern off: the latched one stops
    h.heartbeat(200)
    assert h.sounding == set()


def test_full_table_with_a_pattern_plays_nothing_more(pl09_image, pl09_manifest):
    """Seven presses, six entries: the seventh pad sounds nothing, the arpeggio plays the first six."""
    h = NoteHarness(pl09_image)
    h.track(0, NOTE_EXPANDED)
    set_arp(h, pl09_manifest, 0, 1 | 3 << 3)                        # up, 1/32
    pads = [24, 25, 26, 27, 28, 29, 30]
    for p in pads:
        h.down(p)
    h.take()
    h.heartbeat(1200)
    played = {e[2] for e in h.take("synth_on")}
    assert played == {endpoint_note(h, h.pitch(0, p)) for p in pads[:6]}
    for p in pads:
        h.up(p)
    h.heartbeat(200)
    assert h.sounding == set()


def test_strum_is_ignored_with_a_pattern_on(pl09_image, pl09_manifest):
    """A9: the arpeggio, not the strum, plays the held chord."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(1))
    h.call(sym(pl09_manifest, "slim_ready"))
    h.uc.mem_write(sym(pl09_manifest, "chord_strum"), bytes([3]))  # Synth 1: fast strum
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3)
    notes = triad(h)
    h.down(24)
    times = due(h, pl09_manifest, 6, 600)[:3]
    assert ons(ms_log(h, times[-1])) == list(zip(times, notes))      # one note per step, not a 10 ms roll
    h.up(24)
    h.heartbeat(200)
    assert h.sounding == set()


def test_the_sounding_note_lights_white(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3, 5 << 2)                # legato: always one note sounding
    h.down(24)
    h.heartbeat(due(h, pl09_manifest, 6, 400)[0])
    assert h.leds()[24] == 0x01
    h.up(24)
    h.heartbeat(200)


from unicorn import UC_HOOK_CODE

TICK = 0x0802C418


def test_playing_notes_land_on_the_sequencers_ticks(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3)                        # 1/16
    ticks = []
    t = [0]
    h.uc.hook_add(UC_HOOK_CODE, lambda uc, a, s, d: ticks.append(t[0]), begin=TICK, end=TICK)
    note = endpoint_note(h, h.pitch(0, 24))                        # the dump's patterns play too: count this note only
    h.down(24)
    h.press(17)                                                     # Play: tick 0 now
    h.take()
    got = []
    for t[0] in range(1, 500):
        h.heartbeat(1)
        got += [t[0] for e in h.take("synth_on") if e[2] == note]
    grid = [1] + [ms + 1 for k, ms in enumerate(ticks, start=1) if k % 6 == 0]   # tick 0 on the first heartbeat; the
                                                                    # others in the service after stock's tick
    assert got == grid[:len(got)] and len(got) >= 3
    h.press(17)                                                     # stop
    h.up(24)
    h.heartbeat(200)
    assert h.sounding == set()


def test_stopping_carries_on_from_the_last_tick(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3)
    h.down(24)
    h.press(17)
    h.heartbeat(300)
    h.press(17)                                                     # stopped
    tick = clock(h, pl09_manifest)[0]
    h.heartbeat(100)
    assert clock(h, pl09_manifest)[0] > tick                        # the own clock runs on
    h.up(24)
    h.heartbeat(200)
    assert h.sounding == set()


@pytest.mark.parametrize("swing", [50, 70, 30])
def test_stopped_swing_matches_the_sequencers(pl09_image, pl09_manifest, swing):
    """Stopped, the own clock splits each pair of steps s / (100 - s) %, as the sequencer's ticks do."""
    h = NoteHarness(pl09_image)
    set_tempo(h, swing=swing)
    h.track(0)
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3)
    h.down(24)
    times = due(h, pl09_manifest, 6, 1600)[:8]
    got = [t for t, _ in ons(ms_log(h, times[-1]))]
    assert got == times
    gaps = [b - a for a, b in zip(got, got[1:])]
    if swing == 50:
        assert max(gaps) - min(gaps) <= 1
    else:
        assert abs(gaps[0] + gaps[1] - 2 * 6 * 2500 / BPM) <= 2 and abs(gaps[0] - gaps[1]) > 20
    h.up(24)


def test_a_tempo_change_while_stopped_takes_effect(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3, 2 << 2)                # 3/6 gate
    h.down(24)
    h.heartbeat(400)
    set_tempo(h, bpm=150)
    h.take()
    times = due(h, pl09_manifest, 6, 600)[:3]
    log = ms_log(h, times[-1] + 60)
    assert [t for t, _ in ons(log)] == times
    on = [t for t, k, _ in log if k == "synth_on"][0]
    off = [t for t, k, _ in log if k == "synth_off" and t > on][0]
    assert off - on == arp_model.gate_ms(2 << 3, 2 << 2, 150)
    h.up(24)
    h.heartbeat(200)
    assert h.sounding == set()


def arp_entries(h, m, track=0):
    """held_t: count +0, track +1, pad +2, notes +3..6, sent +7, vel +8, flags +9, wait +10, drop +11, root +12, order +13."""
    base = sym(m, "held")
    return [i for i in range(6) if h.r8(base + 14 * i) and h.r8(base + 14 * i + 9) & 0x10 and h.r8(base + 14 * i + 1) == track]


def page_pick(h, track, pad):
    """A pad on the track's Arp page (▲ ▲ ▼: from any of the three pages; no wrap)."""
    h.press(track, shift=True)
    h.press(20)
    h.press(20)
    h.press(19)
    h.down(pad)
    h.up(pad)
    h.press(track)


def test_latch_keeps_going_and_the_next_press_replaces(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3 | 0x80)
    h.down(24)
    h.up(24)
    h.take()
    h.heartbeat(400)
    assert {e[2] for e in h.take("synth_on")} == {endpoint_note(h, h.pitch(0, 24))}   # latched: still playing
    h.down(26)
    h.take()
    h.heartbeat(400)
    assert {e[2] for e in h.take("synth_on")} == {endpoint_note(h, h.pitch(0, 26))}   # replaced
    h.up(26)
    assert len(arp_entries(h, pl09_manifest)) == 1


def test_an_arpeggio_on_a_muted_track_keeps_stepping(pl21_image, pl21_manifest):
    """Upstream RC4.02 (`tools/arpmute.py`): with the track muted in the Mixer and the transport running, their
    arpeggio stuck on its first note, because stock's player tick skips a muted track's step (0x0804A632) and their
    arpeggio stepped there. CTPlay's steps from seq_tick (every track's tick, before the players) and the heartbeat.
    Stock plays a live pad on a muted track (the mute silences the sequence only), so the held arpeggio keeps sounding
    and stepping on the grid while muted, and after the unmute. The mute goes through the player's mute store, write
    and commit, as the Mixer does (trig.py)."""
    from trig import TrigHarness
    m = pl21_manifest
    h = TrigHarness(pl21_image, m)
    h.track(0)
    set_chord(h, m, 0, settings(1))
    set_arp(h, m, 0, 1 | 2 << 3)                                    # up, 1/16: 6 ticks
    notes = triad(h)

    def run(ms):
        out = []
        for _ in range(ms):
            h.heartbeat(1)
            out += [(h.r32(sym(m, "arp_tick")), e[2]) for e in h.take("synth_on") if e[1] == 0 and e[2] in notes]
        return out

    h.down(24)
    h.press(17)                                                     # Play
    h.take()
    got = run(400)
    h.mute(0, True)
    muted = run(600)
    got += muted
    h.mute(0, False)
    got += run(300)
    assert len(muted) >= 3 and len(got) >= 8                        # 1/16 at the dump's 94 BPM: 160 ms a step
    assert [n for _, n in got] == [notes[i % 3] for i in range(len(got))]        # up, never stuck on one note
    assert [t for t, _ in got] == [6 * i for i in range(len(got))]                # every 1/16, none missed or doubled
    h.press(17)
    h.up(24)
    h.heartbeat(300)
    assert h.sounding == set()


def test_a_latched_arpeggio_keeps_playing_on_another_view(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3 | 0x80)
    h.down(24)
    h.up(24)
    for button in (1, 14):                                          # Synth 2, then the Mixer
        h.press(button)
        h.take()
        h.heartbeat(400)
        assert h.take("synth_on"), button
    h.track(0)
    page_pick(h, 0, 0)                                              # pattern off
    h.heartbeat(2)
    assert h.sounding == set() and arp_entries(h, pl09_manifest) == []


@pytest.mark.parametrize("how", ["latch_off", "pattern_off"])
def test_latch_off_and_pattern_off_stop_it(pl09_image, pl09_manifest, how):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3 | 0x80, 5 << 2)         # legato: a note always sounds
    h.down(24)
    h.up(24)
    h.heartbeat(400)
    assert h.sounding
    page_pick(h, 0, 15 if how == "latch_off" else 0)
    h.track(0)
    h.heartbeat(200)                                                # latch off: ends at the next step at most
    assert h.sounding == set(), (how, sorted(h.sounding))
    assert arp_entries(h, pl09_manifest) == [], how


def test_pattern_change_while_sounding_ends_the_notes(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(1))
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3, 5 << 2)                # up, legato
    h.down(24)
    h.heartbeat(400)
    set_arp(h, pl09_manifest, 0, 7 | 2 << 3, 5 << 2)                # chord, legato
    h.heartbeat(400)
    assert len([k for k in h.sounding if k[0] == "synth"]) == 3
    set_arp(h, pl09_manifest, 0, 0, 5 << 2)                         # off
    h.heartbeat(2)
    assert h.sounding == set()
    h.up(24)


import random

from test_transparency import page_free, run as run_step, script


def test_recording_receives_every_arpeggio_note(pl09_image, pl09_manifest):
    """Recording runs with the sequencer playing (the store 0x20011034: p0 = playing, p1 = recording; the emulator's
    recording() sets both, so Play is pressed first for real ticks). The dump's patterns play too: count the pad's
    note only."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3)
    note = endpoint_note(h, h.pitch(0, 24))
    h.press(17)
    h.recording(True)
    h.down(24)
    h.take()
    h.heartbeat(500)
    log = h.take("rec_on", "synth_on")
    played = [e for e in log if e[0] == "synth_on" and e[2] == note]
    recorded = [e for e in log if e[0] == "rec_on"]
    assert len(played) >= 3 and len(recorded) == len(played), (len(played), len(recorded))
    h.up(24)


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_pattern_off_is_stock(seed, stock_image, pl09_image):
    a, b = Harness(stock_image), Harness(pl09_image)
    for step in page_free(script(seed, 10)):
        run_step(a, step)
        run_step(b, step)
    assert a.outputs() == b.outputs()


def arp_fuzz(seed: int, n: int = 30) -> list[tuple]:
    rnd = random.Random(seed)
    steps = [("down", 24), ("ms", 400), ("up",)]           # one arpeggio first: every script sounds notes
    for _ in range(n):
        r = rnd.random()
        if r < 0.30:
            steps.append(("down", rnd.randrange(16, 32)))
        elif r < 0.55:
            steps.append(("up",))
        elif r < 0.70:
            steps.append(("ms", rnd.choice([5, 40, 120, 300])))
        elif r < 0.76:
            steps.append(("page", rnd.randrange(32)))
        elif r < 0.80:
            steps.append(("pages", rnd.choice([19, 20]), rnd.randrange(24, 32), rnd.randrange(32)))
        elif r < 0.83:
            steps.append(("flip",))
        elif r < 0.87:
            steps.append(("quick", rnd.randrange(16, 32)))
        elif r < 0.91:
            steps.append(("play",))
        elif r < 0.96:
            steps.append(("track", rnd.randrange(4)))
        else:
            steps.append(("view", rnd.choice([14, 15])))
    return steps


@pytest.mark.parametrize("seed", range(1, 25))
def test_no_note_is_left_on(seed, pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    for t in range(4):
        set_arp(h, pl09_manifest, t, 1 | 2 << 3)
    track, held, playing = 0, [], False
    h.track(0)
    recording = seed % 3 == 0                                       # every third script records throughout
    if recording:
        h.press(17)
        h.recording(True)
        playing = True
    for step in arp_fuzz(seed):
        if step[0] == "down":
            if step[1] not in held:
                h.down(step[1])
                held.append(step[1])
        elif step[0] == "up":
            if held:
                h.up(held.pop(0))
        elif step[0] == "ms":
            h.heartbeat(step[1])
        elif step[0] in ("page", "pages", "quick") and any(p in held for p in step[2 if step[0] == "pages" else 1:]):
            continue                                                # a held pad cannot be pressed again on the device
        elif step[0] == "page":
            h.press(track, shift=True)
            h.down(step[1])
            h.up(step[1])
            h.press(track)
            h.track(track)
        elif step[0] == "pages":                                    # ▲ / ▼, a table-of-contents tap, a pad
            h.press(track, shift=True)
            h.press(step[1])
            h.shift(True)
            h.down(step[2])
            h.up(step[2])
            h.shift(False)
            h.down(step[3])
            h.up(step[3])
            h.press(track)
            h.track(track)
        elif step[0] == "flip":
            h.press(21, shift=True)
        elif step[0] == "quick":
            h.shift(True)
            h.down(step[1])
            h.up(step[1])
            h.shift(False)
        elif step[0] == "play":
            if recording:
                continue                                            # keep the recording running
            h.press(17)
            playing = not playing
        elif step[0] == "track":
            h.track(step[1])
            track = step[1]
        else:
            h.press(step[1])
            h.track(track)
    if playing:
        h.press(17)
    for pad in held:
        h.up(pad)
    sounded = sum(1 for e in h.log if e[0] in ("synth_on", "midi_on"))
    h.heartbeat(400)
    for t in range(4):                                              # every pad is up: without latch nothing may remain
        if not h.r8(sym(pl09_manifest, "chord_arp") + 2 * t) & 0x80:
            assert arp_entries(h, pl09_manifest, t) == [], (seed, t)
    for t in range(4):                                              # patterns off: latched arpeggios stop too
        set_arp(h, pl09_manifest, t, 0)
    h.heartbeat(400)
    assert sounded > 0, f"seed {seed}: nothing sounded, the script proves nothing"
    assert h.sounding == set(), (seed, sorted(h.sounding))
    if recording:
        assert [recorder_held(h, t) for t in range(4)] == [[]] * 4, seed


def test_latch_off_while_a_pad_is_held_frees_the_latched_notes_at_the_last_release(pl09_image, pl09_manifest):
    """Final review #1: latch off with a pad still held must not leave the latched notes playing after every pad is up."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3 | 0x80)
    h.down(24)
    h.down(26)
    h.up(24)                                                        # latched
    page_pick(h, 0, 15)                                             # latch off, pad 26 still held
    h.track(0)
    h.up(26)
    h.heartbeat(400)
    h.take()
    h.heartbeat(600)
    assert h.take("synth_on") == [] and h.sounding == set()
    assert arp_entries(h, pl09_manifest) == []


@pytest.mark.parametrize("pattern", [1, 2, 3, 5])
def test_no_note_in_range_after_a_key_change_plays_nothing(pl09_image, pl09_manifest, pattern):
    """Final review #2: a latched arpeggio at the top of the range, then the project key goes up so none of its notes
    is playable (pitch + key > 139): the step must play nothing, not a note read from an empty list."""
    from chord_model import in_scale
    from test_chord import set_pitch
    h = NoteHarness(pl09_image)
    h.track(0, NOTE_EXPANDED)
    key, mask = h.r8(ROOT), h.r32(SCALE_MASK)
    pitch = next(p for p in range(139 - key, 0, -1) if in_scale(mask, p))
    assert pitch + 11 > 139
    set_pitch(h, 0, 0, pitch)
    set_arp(h, pl09_manifest, 0, pattern | 2 << 3 | 0x80)
    h.down(0)
    h.up(0)                                                         # latched
    h.heartbeat(400)
    h.uc.mem_write(ROOT, bytes([11]))                               # the project root goes up
    h.take()
    h.heartbeat(600)
    assert h.take("synth_on", "midi_on") == []
    assert h.sounding == set()


def test_as_played_order_survives_presses_on_another_track(pl09_image, pl09_manifest):
    """Final review #3: a latched "as played" arpeggio on Synth 1 while chords are played on MIDI 1; the press counter
    must not flip its order when it wraps (one counter per track)."""
    h = NoteHarness(pl09_image)
    set_arp(h, pl09_manifest, 0, 6 | 2 << 3 | 0x80)                 # as played, 1/16, latch
    set_chord(h, pl09_manifest, 2, settings(1))                     # MIDI 1: triads
    h.track(0)
    h.down(26)                                                      # pressed first: plays first
    h.down(24)
    h.up(26)
    h.up(24)
    times = due(h, pl09_manifest, 6, 800)[:2]
    before = [n for _, n in ons(ms_log(h, times[-1]))]
    h.track(2)
    for _ in range(255):
        h.down(24)
        h.up(24)
    times = due(h, pl09_manifest, 6, 800)[:2]
    after = [n for _, n in ons(ms_log(h, times[-1]))]
    assert after == before, (before, after)
    set_arp(h, pl09_manifest, 0, 0)
    h.heartbeat(200)


from notes import pattern_snapshot, recorded_notes, recorder_held


def record(h, m, a0, a1, ms, chord=0):
    """Play, Record, hold pad 24 for `ms` with the arpeggio a0 / a1 (Synth 1), let go: the recorded units."""
    h.track(0)
    set_arp(h, m, 0, a0, a1)
    if chord:
        set_chord(h, m, 0, settings(chord))
    h.press(17)
    h.recording(True)
    h.heartbeat(5)
    before = pattern_snapshot(h, 0)
    h.down(24)
    h.heartbeat(ms)
    h.up(24)
    h.heartbeat(300)
    return recorded_notes(h, 0, before)


def spacing(units):
    """Steps between consecutive recorded notes (16-step patterns)."""
    idx = [16 * p + s for p, s, *_ in units]
    return [(b - a) % 16 for a, b in zip(idx, idx[1:])]


@pytest.mark.parametrize("rate, g, length", [(2, g, g + 1) for g in range(6)] + [(1, 5, 12), (0, 5, 24)])
def test_recorded_lengths_are_exact(pl09_image, pl09_manifest, rate, g, length):
    """D7: at 1/16 k sixths record as k ticks; legato as the whole step (1/8: 12, 1/4: 24)."""
    h = NoteHarness(pl09_image)
    units = record(h, pl09_manifest, 1 | rate << 3, g << 2, max(700, 4 * 27 * [24, 12, 6][rate]))
    assert len(units) >= 3, units
    assert [u[3] for u in units[:-1]] == [length] * (len(units) - 1), units      # the last one is cut by the release
    assert {u[4] for u in units} == {0}                                          # microstep 0: on its tick's step
    assert set(spacing(units)) == {[24, 12, 6][rate] // 6}, units
    assert recorder_held(h, 0) == []


def test_recorded_lengths_with_swing(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    set_tempo(h, swing=60)
    units = record(h, pl09_manifest, 1 | 2 << 3, 5 << 2, 900)
    assert len(units) >= 4 and [u[3] for u in units[:-1]] == [6] * (len(units) - 1), units


def test_chord_pattern_legato_records_every_step(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    units = record(h, pl09_manifest, 7 | 2 << 3, 5 << 2, 800, chord=1)
    steps = sorted({(p, s) for p, s, *_ in units})
    assert len(steps) >= 3, units
    for st in steps[:-1]:
        assert sorted(u[3] for u in units if u[:2] == st) == [6, 6, 6], (st, units)
    assert recorder_held(h, 0) == []


def test_recording_leaves_nothing_held(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    record(h, pl09_manifest, 1 | 2 << 3, 5 << 2, 600, chord=1)
    assert recorder_held(h, 0) == []
    h.press(17)                                                     # stop: the dump's patterns stop sounding too
    h.heartbeat(300)
    assert h.sounding == set()


def first_on(h, note, ms):
    for t in range(1, ms + 1):
        h.heartbeat(1)
        if any(e[2] == note for e in h.take("synth_on")):
            return t
    raise AssertionError("no note-on")


def test_stop_during_a_tick_gate_ends_the_note(pl09_image, pl09_manifest):
    """Review focus: a tick-counted gate still ends once the stopped clock takes over."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_arp(h, pl09_manifest, 0, 1, 4 << 2)                         # up, 1/4, 5/6: 20 ticks
    note = endpoint_note(h, h.pitch(0, 24))
    h.down(24)
    h.press(17)
    first_on(h, note, 100)
    h.press(17)                                                     # stop
    log = ms_log(h, 20 * 2500 // BPM + 5)
    assert ("synth_off", note) in [(k, n) for _, k, n in log]
    h.up(24)
    h.heartbeat(800)
    assert h.sounding == set()


def test_faster_rate_while_a_tick_gate_counts(pl09_image, pl09_manifest):
    """Review focus: the next step ends the old notes first; nothing sticks."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(1))
    set_arp(h, pl09_manifest, 0, 1, 4 << 2)                         # up, 1/4, 5/6
    h.down(24)
    h.press(17)
    h.heartbeat(30)
    h.take()
    set_arp(h, pl09_manifest, 0, 1 | 3 << 3, 4 << 2)                # 1/32
    mine = set(triad(h))                                            # the dump's patterns play too
    log = [e for e in ms_log(h, 300) if e[2] in mine]
    assert len([k for k in h.sounding if k[0] == "synth" and k[1] == 0 and k[2] in mine]) <= 1
    ons_ = [t for t, k, _ in log if k == "synth_on"]
    offs = [t for t, k, _ in log if k == "synth_off"]
    assert ons_ and offs and offs[0] <= ons_[0], log[:6]
    h.press(17)
    h.up(24)
    h.heartbeat(300)
    assert h.sounding == set()


def test_shift_another_track_with_pads_held_and_a_pattern_on(pl09_image, pl09_manifest):
    """PL06 follow-up: stock's view switch releases the held pads; the arpeggio's notes end."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_chord(h, pl09_manifest, 0, settings(1))
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3, 5 << 2)                # legato: a note always sounds
    h.down(24)
    h.heartbeat(300)
    assert h.sounding
    h.press(1, shift=True)                                          # Synth 2's page
    h.up(24)
    h.heartbeat(300)
    assert h.sounding == set() and arp_entries(h, pl09_manifest, 0) == []


def test_pattern_off_on_the_page_while_notes_sound(pl09_image, pl09_manifest):
    """PL06 follow-up: through the Arp page's pad 1, not set_arp."""
    h = NoteHarness(pl09_image)
    h.track(0)
    set_arp(h, pl09_manifest, 0, 1 | 2 << 3, 5 << 2)
    h.down(24)
    h.heartbeat(300)
    assert h.sounding
    h.press(0, shift=True)
    h.press(19)                                                     # the Arp page
    h.down(0)
    h.up(0)
    h.heartbeat(5)
    assert h.sounding == set()
    h.press(0)
    h.up(24)
    h.heartbeat(300)
    assert h.sounding == set()


def test_legato_reattacks_a_repeated_pitch_on_a_midi_track(pl09_image, pl09_manifest):
    """The Task 3 ruling's other route: MIDI 1's sink also ends a sounding pitch before sending it again."""
    h = NoteHarness(pl09_image)
    h.track(2)
    set_arp(h, pl09_manifest, 2, 1 | 2 << 3, 5 << 2)                # one note, up, legato
    h.down(24)
    log = ms_log(h, 800, kinds=("midi_on", "midi_off"))
    ons_ = [t for t, k, _ in log if k == "midi_on"]
    assert len(ons_) >= 3, log
    for t in ons_[1:]:
        assert [k for u, k, _ in log if u == t] == ["midi_off", "midi_on"], (t, log)
    h.up(24)
    h.heartbeat(300)
    assert h.sounding == set()

