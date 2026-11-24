"""Note repeat (PL16, spec 2026-10-25-drums-design.md, "How repeat plays"): its maths (repeat_math.c) against
tests/repeat_model.py, through the built image; the engine (repeat.c) through the real routes, its hits counted at the
expanded drum view's sink and in what stock records (tests/drums.py)."""
import random

import pytest
from unicorn.arm_const import UC_ARM_REG_R0

import repeat_model
from drums import BPM, DRUM_PAD, MODE_EXPANDED, NOTE_BTN, PLAY, DrumHarness, drum_setup, recorded
from harness import Harness

pytestmark = pytest.mark.emu


def sym(m, name):
    return int(m["symbols"][name], 16)


def test_repeat_math_matches_the_model(pl17_image, pl17_manifest):
    h = Harness(pl17_image)

    def call(name, *args):
        h.call(sym(pl17_manifest, name), *args)
        return h.uc.reg_read(UC_ARM_REG_R0)

    for rate in range(9):
        assert call("repeat_ticks", rate) == repeat_model.ticks(rate), rate
    bad = []
    for shape in range(4):
        for v in range(1, 128):
            for e in range(61):
                for beat in (0, 1):
                    if call("repeat_vel", shape, v, e, beat) != repeat_model.vel(shape, v, e, beat):
                        bad.append((shape, v, e, beat))
    assert not bad, bad[:5]
    rnd = random.Random(16)
    for _ in range(200):
        ticks, press = rnd.choice(repeat_model.TICKS), rnd.randrange(0, 200)
        tick, playing = rnd.randrange(0, 260), rnd.randrange(2)
        if rnd.random() < 0.1:
            tick = press
        got = call("repeat_due", tick, press, ticks, playing)
        assert got == repeat_model.due(tick, press, ticks, playing), (tick, press, ticks, playing)
    assert call("repeat_due", 3, 5, 4, 0) == repeat_model.due(3, 5, 4, 0)    # a tick before the press: wraps, as e does


# ---- The engine (repeat.c): hits through the expanded drum view's sink, from the Main task, recorded by stock ----

WHITE, PULSE = 0x01, 0x04
DRUM_COLS = [0x45, 0x2D, 0x49, 0x4D]        # stock's expanded view, pads 29-32 (measured on the stock image)
TICK_MS = 60000 / BPM / 24                   # 10.4 ms a tick at 240 BPM
RATE_PAD = {r: r - 1 for r in range(1, 9)}   # the Repeat page: pads 0-7 = rates 1-8
SHAPE_PAD, LATCH_PAD = 8, 15
CLEAR = 23


def cfg(h):
    return h.r8(sym(h.m, "repeat_cfg"))


def tap(h, pad, vel=100):
    h.down(pad, vel)
    h.up(pad)


def set_rate(h, rate):
    if cfg(h) & 0xF != rate:
        tap(h, RATE_PAD[rate or cfg(h) & 0xF])
    assert cfg(h) & 0xF == rate


def toggle_latch(h):
    tap(h, LATCH_PAD)


def play(h):
    """Play (the real button); the next heartbeat makes it arp_tick 0."""
    h.press(PLAY)
    h.heartbeat(1)
    assert h.transport()[0] == 1 and h.arp_tick() == 0


def on_ticks(h, d, since=0):
    return [t for ms, t, k, n, v in h.sent[since:] if k == "on" and n == d + 1]


def kinds(h, d):
    return [k for ms, t, k, n, v in h.sent if n == d + 1]


def drums_sounding(h):
    return sorted(k for k in h.sounding if k[0] == "synth" and k[1] == 16)


def model_hits(press, release, ticks, playing):
    """The ticks a drum held from `press` (the arp_tick its press was taken at) to `release` sounds on: the press, then
    every tick repeat_due gives before the release's (that tick's hit would go out after the release)."""
    return [press] + [t for t in range(press + 1, release) if repeat_model.due(t, press, ticks, playing)]


def hold(h, d, press, release, vel=100):
    """Press drum d's pad at arp_tick `press` and let go once the heartbeat counting `release` has run."""
    h.until_tick(press)
    h.down(DRUM_PAD + d, vel)
    h.until_tick(release)
    h.up(DRUM_PAD + d)
    h.heartbeat(2)


@pytest.mark.parametrize("rate", range(1, 9))
def test_held_pad_repeats_at_every_rate_playing(pl17_image, pl17_manifest, rate):
    h = DrumHarness(pl17_image, pl17_manifest)
    p = drum_setup(h)
    set_rate(h, rate)
    play(h)
    hold(h, 0, 13, 13 + 178)                                            # two bars less a step: no step hit twice
    want = model_hits(13, 13 + 178, repeat_model.ticks(rate), 1)
    assert on_ticks(h, 0) == want
    assert kinds(h, 0) == ["on", "off"] * len(want)                      # each hit ends the one before; the last ends at the release
    assert {v for ms, t, k, n, v in h.ons(1)} == {100}
    assert h.pattern_hits(0, p) == recorded(h.sent, 1) and len(h.pattern_hits(0, p)) == len({t // 6 for t in want})
    assert drums_sounding(h) == []


def test_repeat_across_the_pattern_wrap(pl17_image, pl17_manifest):
    """A 1/16 repeat held across the pattern's loop point (tick 192, 32 steps) records every hit in the one pattern:
    the last steps of one pass and the first steps of the next."""
    h = DrumHarness(pl17_image, pl17_manifest)
    p = drum_setup(h)
    set_rate(h, 3)
    play(h)
    hold(h, 0, 150, 230)
    want = model_hits(150, 230, 6, 1)
    assert on_ticks(h, 0) == want and 192 in want
    assert h.playing_pattern(0) == p and h.chain(0) == (p, p)
    hits = h.pattern_hits(0, p)
    assert hits == recorded(h.sent, 1)
    assert sorted(hits) == list(range(7)) + list(range(25, 32))
    assert drums_sounding(h) == []


@pytest.mark.parametrize("rate", [3, 5])
def test_stopped_repeats_from_the_press(pl17_image, pl17_manifest, rate):
    h = DrumHarness(pl17_image, pl17_manifest)
    p = drum_setup(h)
    set_rate(h, rate)
    assert h.transport() == (0, 1, 0)                                   # stopped, Record armed
    t0 = h.arp_tick()
    h.heartbeat(30)
    assert h.arp_tick() > t0                                            # the own clock runs
    press = h.arp_tick() + 1
    h.until_tick(press)
    h.down(DRUM_PAD)
    h.until_tick(press + 100)
    h.up(DRUM_PAD)
    h.heartbeat(2)
    ticks = repeat_model.ticks(rate)
    assert on_ticks(h, 0) == [t for t in range(press, press + 101) if (t - press) % ticks == 0]
    assert h.pattern_hits(0, p) == {}                                   # stopped: nothing is recorded
    assert kinds(h, 0)[-1] == "off" and drums_sounding(h) == []


def test_rate_change_mid_hold(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    p = drum_setup(h)
    set_rate(h, 3)                                                      # 1/16
    play(h)
    h.until_tick(30)
    h.down(DRUM_PAD)
    h.until_tick(126)                                                   # a bar later
    tap(h, RATE_PAD[4])                                                 # 1/32 while the drum is held
    assert cfg(h) & 0xF == 4
    h.until_tick(174)
    h.up(DRUM_PAD)
    h.heartbeat(2)
    want = [30] + [t for t in range(31, 127) if t % 6 == 0] + [t for t in range(127, 174) if t % 3 == 0]
    assert on_ticks(h, 0) == want                                       # no restart, no extra hit at the change
    assert h.pattern_hits(0, p) == recorded(h.sent, 1)


def test_close_grid_point_skipped(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    drum_setup(h)
    set_rate(h, 3)
    play(h)
    hold(h, 0, 40, 60)                                                  # 42 is 2 ticks after the press: < 6 / 2
    first = len(h.sent)
    hold(h, 0, 63, 80)                                                  # 66 is 3 after: kept
    assert on_ticks(h, 0)[:3] == [40, 48, 54] and on_ticks(h, 0, first) == [63, 66, 72, 78]


@pytest.mark.parametrize("shape", [1, 3])
def test_velocity_shapes_recorded(pl17_image, pl17_manifest, shape):
    """Fade: from the strike down over a beat, the press's hit included; accent: the sequencer's quarters at the strike,
    the rest at 2/3. One velocity per step (1/16: one hit a step)."""
    h = DrumHarness(pl17_image, pl17_manifest)
    p = drum_setup(h)
    set_rate(h, 3)
    tap(h, SHAPE_PAD + shape)
    play(h)
    hold(h, 0, 50, 50 + 96, vel=120)                                    # the press 2 ticks into step 8, off the beat
    hits = model_hits(50, 146, 6, 1)
    want = {t // 6: (repeat_model.vel(shape, 120, t - 50, t % 24 == 0), 1 << t % 6) for t in hits}
    assert h.pattern_hits(0, p) == want
    if shape == 1:
        assert want[8][0] == 120 and want[24][0] == 120 * 8 // 32       # from v down to v/4 a beat later
    else:
        assert want[8][0] == 80 and want[12][0] == 120 and want[13][0] == 80   # the press off the beat: 2/3; tick 72: v


def test_latch_survives_page_close(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    drum_setup(h)
    set_rate(h, 3)
    toggle_latch(h)
    play(h)
    h.until_tick(12)
    tap(h, DRUM_PAD + 1)                                                # drum 2 latched
    h.until_tick(40)
    assert h.leds()[DRUM_PAD + 1] == PULSE
    h.press(NOTE_BTN)                                                   # the page closes: drum 1's expanded view
    assert h.view_mode() == MODE_EXPANDED and h.r8(sym(h.m, "chord_page")) == 0xFF
    closed = len(h.sent)
    h.until_tick(100)
    assert on_ticks(h, 1, closed) == list(range(42, 100, 6))            # it keeps going
    p2 = h.playing_pattern(1)
    assert h.pattern_hits(1, p2) == recorded(h.sent, 2) and 15 in h.pattern_hits(1, p2)   # and recording
    h.press(4, shift=True)                                              # the page again
    tap(h, DRUM_PAD + 1)                                                # the next tap stops it
    h.heartbeat(1)
    assert h.sent[-1][2:4] == ("off", 2)
    stopped = len(h.sent)
    h.heartbeat(200)
    assert h.sent[stopped:] == [] and drums_sounding(h) == []
    tap(h, DRUM_PAD)
    tap(h, DRUM_PAD + 2)                                                # drums 1 and 3 latched
    h.heartbeat(200)
    assert on_ticks(h, 0, stopped) and on_ticks(h, 2, stopped)
    toggle_latch(h)                                                     # latch off stops them all
    h.heartbeat(1)
    off = len(h.sent)
    assert sorted(e[3] for e in h.sent[off - 2:off] if e[2] == "off") == [1, 3]
    h.heartbeat(200)
    assert h.sent[off:] == [] and drums_sounding(h) == []
    assert [h.leds()[DRUM_PAD + d] for d in range(4)] == DRUM_COLS


def latched(h):
    return h.r8(sym(h.m, "rep_latched"))


def test_latch_without_a_rate_is_a_one_shot(pl17_image, pl17_manifest):
    """Final review 1: latch on, no rate lit: a drum pad plays once per press (spec "No rate lit"), its note-off on the
    release; nothing latches, the next tap sounds again, and the kit's quantise override ends with the hit."""
    h = DrumHarness(pl17_image, pl17_manifest)
    unquant_setup(h, rate=0)
    toggle_latch(h)
    assert cfg(h) & 0x40 and cfg(h) & 0xF == 0
    h.down(DRUM_PAD, 90)
    h.heartbeat(1)
    assert [e[2:] for e in h.sent] == [("on", 1, 90)] and h.leds()[DRUM_PAD] == WHITE
    h.heartbeat(100)
    assert len(h.sent) == 1 and latched(h) == 0                         # no repeat, nothing latched
    h.up(DRUM_PAD)
    h.heartbeat(1)
    assert [e[2:4] for e in h.sent] == [("on", 1), ("off", 1)] and drums_sounding(h) == []
    h.heartbeat(10)
    assert h.leds()[DRUM_PAD] == DRUM_COLS[0] and quantise_bytes(h) == [1, 1, 1, 1]
    tap(h, DRUM_PAD)                                                    # the next tap sounds again, once
    h.heartbeat(100)
    assert [e[2:4] for e in h.sent[2:]] == [("on", 1), ("off", 1)] and latched(h) == 0


def test_rate_off_stops_latched_drums(pl17_image, pl17_manifest):
    """Final review 1: the lit rate pad again (no rate) stops the latched drums, with their note-offs, and ends the
    kit's quantise override; a rate lit again restarts nothing."""
    h = DrumHarness(pl17_image, pl17_manifest)
    unquant_setup(h, rate=3)
    toggle_latch(h)
    tap(h, DRUM_PAD)
    tap(h, DRUM_PAD + 2)                                                # drums 1 and 3 latched
    h.heartbeat(100)
    assert on_ticks(h, 0) and on_ticks(h, 2) and latched(h) == 0b101 and quantise_bytes(h) == [0, 0, 0, 0]
    set_rate(h, 0)
    assert latched(h) == 0
    h.heartbeat(1)
    off = len(h.sent)
    assert sorted(e[3] for e in h.sent[off - 2:off] if e[2] == "off") == [1, 3]
    h.heartbeat(200)
    assert h.sent[off:] == [] and drums_sounding(h) == [] and quantise_bytes(h) == [1, 1, 1, 1]
    assert [h.leds()[DRUM_PAD + d] for d in range(4)] == DRUM_COLS
    set_rate(h, 3)
    h.heartbeat(200)
    assert h.sent[off:] == []


@pytest.mark.parametrize("how", ["Note", "Shift + Drum 2"])
def test_lost_release_stops(pl17_image, pl17_manifest, how):
    """Review focus: a drum pad's release lost to a view change ends its repeat, its last hit and its white LED."""
    h = DrumHarness(pl17_image, pl17_manifest)
    drum_setup(h)
    set_rate(h, 3)
    h.down(DRUM_PAD)
    h.heartbeat(100)
    assert len(h.ons(1)) >= 2 and h.leds()[DRUM_PAD] == WHITE           # sounding: white
    if how == "Note":
        h.press(NOTE_BTN)
        assert h.view_mode() == MODE_EXPANDED
    else:
        h.press(5, shift=True)
        assert h.r8(sym(h.m, "chord_page")) == 5
    h.heartbeat(1)
    assert h.sent[-1][2:4] == ("off", 1)
    gone = len(h.sent)
    h.heartbeat(200)
    h.up(DRUM_PAD)                                                      # the release comes after the change
    h.heartbeat(100)
    assert h.sent[gone:] == [] and drums_sounding(h) == []
    assert h.leds()[DRUM_PAD] == DRUM_COLS[0]                           # stock's expanded view, or the Repeat page


def gaps(ticks):
    return [b - a for a, b in zip(ticks, ticks[1:])]


@pytest.mark.parametrize("rate", [3, 5])                                # 1/16; 1/4T (16 ticks: 24 is no multiple)
def test_two_drums_and_play_stop(pl17_image, pl17_manifest, rate):
    """Review focus: Play makes the grid the sequencer's from tick 0; Stop goes on with the stopped clock on the same
    grid: no double hit, no gap longer than one interval."""
    h = DrumHarness(pl17_image, pl17_manifest)
    drum_setup(h)
    set_rate(h, rate)
    ticks = repeat_model.ticks(rate)
    h.down(DRUM_PAD)
    h.heartbeat(37)
    h.down(DRUM_PAD + 2)
    h.heartbeat(400)
    before = len(h.sent)
    h.press(PLAY)
    h.heartbeat(1)
    assert h.arp_tick() == 0
    h.until_tick(5 * ticks + 7)
    playing = len(h.sent)
    h.press(PLAY)                                                       # Stop
    h.heartbeat(600)
    h.up(DRUM_PAD)
    h.up(DRUM_PAD + 2)
    h.heartbeat(2)
    for d in (0, 2):
        ons = [(ms, t) for ms, t, k, n, v in h.sent if k == "on" and n == d + 1]
        stopped_before = [t for ms, t, k, n, v in h.sent[:before] if k == "on" and n == d + 1]
        on_play = [t for ms, t, k, n, v in h.sent[before:playing] if k == "on" and n == d + 1]
        after = [t for ms, t, k, n, v in h.sent[playing:] if k == "on" and n == d + 1]
        assert set(gaps(stopped_before)) == {ticks}, d                  # from the press
        assert on_play[0] in (0, ticks) and on_play == list(range(on_play[0], on_play[-1] + 1, ticks)), d   # the
                                                                        # sequencer's grid (tick 0 unless a hit was just before)
        assert gaps(on_play[-1:] + after) == [ticks] * len(after), d    # Stop: the same grid, on the stopped clock
        ms_gaps = gaps([ms for ms, t in ons])
        at_play = len(stopped_before) - 1                               # the gap from the last stopped hit
        assert min(ms_gaps) >= ticks / 2 * TICK_MS - 1, (d, ms_gaps)   # no flam, at Play either
        assert ms_gaps[at_play] <= 1.5 * ticks * TICK_MS + 2, (d, ms_gaps)   # Play: tick 0 skipped at most
        others = ms_gaps[:at_play] + ms_gaps[at_play + 1:]
        assert max(others) <= ticks * TICK_MS + TICK_MS + 2, (d, ms_gaps)   # Stop: no longer than one interval
        assert kinds(h, d) == ["on", "off"] * len(ons)
    assert drums_sounding(h) == []


def wait_for_hit(h, d=0, cap=200):
    """Heartbeats until drum d's next hit goes out; its (ms, arp_tick)."""
    n = len(h.ons(d + 1))
    for _ in range(cap):
        h.heartbeat(1)
        if len(h.ons(d + 1)) > n:
            return h.ons(d + 1)[-1][:2]
    raise AssertionError("no hit")


def test_play_right_after_a_stopped_hit_skips_tick_0(pl17_image, pl17_manifest):
    """Play less than half an interval after a hit: tick 0 is skipped, the next hit is the grid's at 6 ticks."""
    h = DrumHarness(pl17_image, pl17_manifest)
    drum_setup(h)
    set_rate(h, 3)
    h.down(DRUM_PAD)
    h.heartbeat(100)
    ms, _ = wait_for_hit(h)
    h.press(PLAY)                                                       # the next heartbeat makes it tick 0
    nxt = wait_for_hit(h)
    assert nxt[1] == 6 and nxt[0] - ms >= 3 * TICK_MS                   # not a flam: at least half an interval
    h.up(DRUM_PAD)
    h.heartbeat(2)
    assert drums_sounding(h) == []


def test_play_long_after_a_stopped_hit_hits_tick_0(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    drum_setup(h)
    set_rate(h, 3)
    h.down(DRUM_PAD)
    h.heartbeat(100)
    _, t = wait_for_hit(h)
    h.until_tick(t + 4)                                                 # 4 of 6 ticks later: half an interval or more
    h.press(PLAY)
    h.heartbeat(1)
    assert h.sent[-2:][-1][1:4] == (0, "on", 1) and h.arp_tick() == 0   # tick 0 hits
    h.up(DRUM_PAD)
    h.heartbeat(2)


def test_a_press_in_the_play_heartbeat_hits_tick_0_on_the_beat(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    drum_setup(h)
    set_rate(h, 3)
    tap(h, SHAPE_PAD + 3)                                               # accent the beat
    for _ in range(200):                                                # the stopped clock off the beat
        if h.arp_tick() % 24 == 5:
            break
        h.heartbeat(1)
    h.press(PLAY)
    h.down(DRUM_PAD, 120)                                               # before the heartbeat that makes it tick 0
    h.heartbeat(1)
    assert [e[1:] for e in h.sent] == [(0, "on", 1, 120)]               # one hit, at tick 0, at v
    h.until_tick(7)
    assert [e[1:] for e in h.ons(1)] == [(0, "on", 1, 120), (6, "on", 1, 80)]
    h.up(DRUM_PAD)
    h.heartbeat(2)
    assert drums_sounding(h) == []


def test_stop_after_presses_while_playing(pl17_image, pl17_manifest):
    """Review focus: a drum pressed while playing goes on on the sequencer's grid after Stop; one pressed since the last
    grid point (the close one skipped) goes on from its press."""
    h = DrumHarness(pl17_image, pl17_manifest)
    drum_setup(h)
    set_rate(h, 3)
    play(h)
    h.until_tick(13)
    h.down(DRUM_PAD)                                                    # off the grid
    h.until_tick(52)
    h.down(DRUM_PAD + 1)                                                # 54 is too close: skipped
    h.until_tick(53)
    stop = len(h.sent)
    h.press(PLAY)                                                       # Stop
    h.until_tick(90)
    h.up(DRUM_PAD)
    h.up(DRUM_PAD + 1)
    h.heartbeat(2)
    assert on_ticks(h, 0) == [13] + list(range(18, 91, 6))              # 48, then 54 on the stopped clock
    assert on_ticks(h, 1) == [52] + list(range(58, 91, 6))              # from its press
    assert on_ticks(h, 0, stop)[0] == 54 and drums_sounding(h) == []


def test_no_rate_one_hit(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    drum_setup(h)
    assert cfg(h) & 0xF == 0
    h.down(DRUM_PAD + 3, 90)
    assert h.sent == []                                                 # the press only sets flags
    h.heartbeat(1)
    assert [e[2:] for e in h.sent] == [("on", 4, 90)]                   # the next heartbeat sends it
    assert h.leds()[DRUM_PAD + 3] == WHITE
    h.heartbeat(300)
    h.up(DRUM_PAD + 3)
    h.heartbeat(1)
    assert [e[2:4] for e in h.sent] == [("on", 4), ("off", 4)] and drums_sounding(h) == []
    assert h.leds()[DRUM_PAD + 3] == DRUM_COLS[3]
    tap(h, DRUM_PAD + 1)                                                # a tap shorter than a heartbeat: both in it
    h.heartbeat(1)
    assert [e[2:4] for e in h.sent[2:]] == [("on", 2), ("off", 2)]


def test_drum_pad_leds(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    drum_setup(h)
    assert h.leds()[DRUM_PAD:DRUM_PAD + 4] == DRUM_COLS                 # stock's expanded-view colours
    set_rate(h, 3)
    h.down(DRUM_PAD + 2)
    h.heartbeat(1)
    assert h.leds()[DRUM_PAD:DRUM_PAD + 4] == DRUM_COLS[:2] + [WHITE] + DRUM_COLS[3:]
    h.up(DRUM_PAD + 2)
    h.heartbeat(1)
    toggle_latch(h)
    tap(h, DRUM_PAD + 1)
    h.heartbeat(50)
    assert h.leds()[DRUM_PAD:DRUM_PAD + 4] == [DRUM_COLS[0], PULSE] + DRUM_COLS[2:]   # latched: pulsing white


def test_project_load_stops_everything(pl17_image, pl17_manifest):
    from test_saved import load, write_tail
    h = DrumHarness(pl17_image, pl17_manifest)
    drum_setup(h)
    set_rate(h, 3)
    h.down(DRUM_PAD)                                                    # drum 1 held
    toggle_latch(h)
    tap(h, DRUM_PAD + 3)                                                # drum 4 latched
    h.heartbeat(200)
    assert on_ticks(h, 0) and on_ticks(h, 3) and drums_sounding(h)
    write_tail(h, bytes(1000))                                          # a project without a CTPlay block
    load(h)
    h.leds()                                                            # the frame that applies it
    h.heartbeat(1)
    assert sorted(e[3] for e in h.sent[-2:] if e[2] == "off") == [1, 4]
    gone = len(h.sent)
    h.heartbeat(300)
    h.up(DRUM_PAD)
    h.heartbeat(100)
    assert h.sent[gone:] == [] and drums_sounding(h) == []


def test_count_in_records_nothing(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    p = drum_setup(h, record=False)
    for _ in range(2):                                                  # Shift + Clear: off -> click -> count-in
        h.press(CLEAR, shift=True)
    h.press(16)                                                         # Record armed
    set_rate(h, 3)
    h.press(PLAY)                                                       # the count starts: one bar at 240 BPM
    h.down(DRUM_PAD)
    for t in range(800):
        h.heartbeat(1)
        if t % 10 == 0:
            h.leds()
        assert h.transport()[0] == 0 or t > 700
    h.up(DRUM_PAD)
    h.heartbeat(2)
    assert len(h.ons(1)) > 10 and h.pattern_hits(0, p) == {}


def test_no_send_from_the_dsp_tick(pl17_image, pl17_manifest):
    """Every hit goes out from the Main task's heartbeat: none from a pad, a button or an LED frame (UI task); none of
    the UI or project-load handlers that reach the engine can reach a lock-taking sink call (the DSP tick runs no slim
    code that does: the build's own check, tests/test_checks.py)."""
    h = DrumHarness(pl17_image, pl17_manifest)
    drum_setup(h)
    set_rate(h, 6)
    play(h)
    h.down(DRUM_PAD)
    h.heartbeat(200)
    toggle_latch(h)
    tap(h, DRUM_PAD + 1)
    h.heartbeat(200)
    h.press(NOTE_BTN)
    h.leds()
    h.up(DRUM_PAD)
    h.heartbeat(100)
    h.press(PLAY)
    h.heartbeat(100)
    assert len(h.sent) > 20 and set(h.sent_by) == {"main"}
    callees = pl17_manifest["stack_uncounted_callees"]
    for handler in ("page_on_pad", "page_on_release", "chord_on_button", "chord_on_leds", "saved_on_applied"):
        assert not {"note_sink_on", "note_sink_off"} & set(callees[handler]), handler


# ---- Unquantized repeats (repeat_cfg bit 7): the drum recorders' quantise held off while a drum repeats or sounds ----
# Stock's [rec + 0x35] (1 = quantise) is a cache that its store listener refreshes at each step's tick 0 (0x0803FE8C,
# the mid hook rec_quant); the override keeps it 0 there for the drums alone and puts back stock's own last value.

UNQUANT_PAD, RECORD_BTN, RECORD_LED = 14, 16, 48
NOTE_RECORDERS = 0x2003C174                  # [+ 4 t]: note track t's recorder


def quantise_bytes(h):
    return [h.quantise_byte(d) for d in range(4)]


def note_quantise_bytes(h):
    return [h.r8(h.r32(NOTE_RECORDERS + 4 * t) + 0x35) for t in range(4)]


def unquant_setup(h, quantise_off=False, unquant=True, rate=0):
    """drum_setup with stock's record quantise on (the snapshot's), Unquantized repeats on, the rate set."""
    p = drum_setup(h, quantise_off=quantise_off)
    assert h.quantise_off_setting() == int(quantise_off)
    if unquant:
        tap(h, UNQUANT_PAD)
    assert bool(cfg(h) & 0x80) == unquant
    set_rate(h, rate)
    return p


@pytest.mark.parametrize("unquant", [True, False])
def test_unquantized_repeats_with_quantise_on(pl17_image, pl17_manifest, unquant):
    """1/32 for four bars' worth of steps: two hits a step, at its ticks 0 and 3 (micro mask 001001); with the setting
    off stock quantises them: one hit a step, on its tick 0. The user sees nothing: Shift + Record's setting and the
    Record LED stay as they were."""
    h = DrumHarness(pl17_image, pl17_manifest)
    p = unquant_setup(h, unquant=unquant, rate=4)
    play(h)
    led = h.leds()[RECORD_LED]
    hold(h, 0, 24, 24 + 96)
    hits = h.pattern_hits(0, p)
    if unquant:
        assert hits == recorded(h.sent, 1)
        assert sorted(hits) == list(range(4, 20)) and {m for v, m in hits.values()} == {0b001001}
    else:
        assert set(range(4, 20)) <= set(hits) and {m for v, m in hits.values()} == {0b000001}
    assert h.quantise_off_setting() == 0 and h.leds()[RECORD_LED] == led


def test_quantise_restored(pl17_image, pl17_manifest):
    """While a drum is held every drum recorder's byte is 0; once it ends they are stock's again (1: quantise on, as
    stock gives them in a harness that never repeated). The note recorders' bytes never change."""
    h = DrumHarness(pl17_image, pl17_manifest)
    unquant_setup(h, rate=3)
    play(h)
    ref = DrumHarness(pl17_image, pl17_manifest)
    unquant_setup(ref, rate=3)
    play(ref)
    h.until_tick(30)
    assert quantise_bytes(h) == [1, 1, 1, 1]
    h.down(DRUM_PAD)
    for _ in range(3):
        h.heartbeat(1)
        assert quantise_bytes(h) == [0, 0, 0, 0] and note_quantise_bytes(h) == [1, 1, 1, 1]
    h.until_tick(77)                                                     # past several steps' refreshes
    assert quantise_bytes(h) == [0, 0, 0, 0] and note_quantise_bytes(h) == [1, 1, 1, 1]
    h.up(DRUM_PAD)
    h.heartbeat(2)
    ref.until_tick(h.arp_tick())
    assert quantise_bytes(h) == quantise_bytes(ref) == [1, 1, 1, 1] and note_quantise_bytes(h) == [1, 1, 1, 1]
    h.until_tick(130)
    ref.until_tick(130)
    assert quantise_bytes(h) == quantise_bytes(ref)


@pytest.mark.parametrize("toggles, release", [((50,), 80), ((50, 70), 90), ((50, 70), 70)])
def test_shift_record_during_unquantized_repeat(pl17_image, pl17_manifest, toggles, release):
    """Review focus: Shift + Record toggled while an unquantized repeat runs. When it ends every drum recorder's byte is
    what stock's own gives, in a harness that never repeated (the same toggles at the same ticks); a release in the
    step of the last toggle gets stock's not yet refreshed value, as stock has it."""
    h = DrumHarness(pl17_image, pl17_manifest)
    ref = DrumHarness(pl17_image, pl17_manifest)
    for x in (h, ref):
        unquant_setup(x, rate=3)
        play(x)
    h.until_tick(30)
    h.down(DRUM_PAD)
    for t in toggles:
        for x in (h, ref):
            x.until_tick(t)
            x.press(RECORD_BTN, shift=True)
        assert quantise_bytes(h) == [0, 0, 0, 0]
    assert h.quantise_off_setting() == ref.quantise_off_setting() == len(toggles) % 2
    h.until_tick(release)
    h.up(DRUM_PAD)
    h.heartbeat(2)
    ref.until_tick(h.arp_tick())
    assert quantise_bytes(h) == quantise_bytes(ref)
    for t in (release + 7, release + 30):                               # and at the next refreshes
        h.until_tick(t)
        ref.until_tick(t)
        assert quantise_bytes(h) == quantise_bytes(ref) == [1 - len(toggles) % 2] * 4
    assert h.leds()[RECORD_LED] == ref.leds()[RECORD_LED]


def test_project_load_restores_quantise(pl17_image, pl17_manifest):
    from test_saved import load, write_tail
    h = DrumHarness(pl17_image, pl17_manifest)
    unquant_setup(h, rate=3)
    play(h)
    h.until_tick(20)
    h.down(DRUM_PAD)                                                     # drum 1 held
    toggle_latch(h)
    tap(h, DRUM_PAD + 3)                                                 # drum 4 latched
    h.until_tick(60)
    assert quantise_bytes(h) == [0, 0, 0, 0]
    write_tail(h, bytes(1000))                                           # a project without a CTPlay block
    load(h)
    h.leds()
    h.heartbeat(3)
    assert quantise_bytes(h) == [1, 1, 1, 1] and h.quantise_off_setting() == 0
    h.until_tick(100)
    assert quantise_bytes(h) == [1, 1, 1, 1]


Q3_HITS = ((4, 5, 0), (8, 5, 3), (12, 5, 6), (16, 5, 8), (20, 2, 0))   # (step, tick in it, ms after): the tick-0 window


def single_hits(h):
    for st, o, extra in Q3_HITS:
        h.until_tick(6 * st + o)
        h.heartbeat(extra)
        h.down(DRUM_PAD, 90)
        h.heartbeat(15)
        h.up(DRUM_PAD)
        h.heartbeat(5)
    h.until_tick(6 * 24)


def test_tick0_window_lands_as_stock_quantise_off(pl17_image, pl17_manifest):
    """A hit sent in the heartbeat after a step's tick 0 was counted (the refresh and the hit's placement in one stock
    call): with the override it lands exactly as stock's own quantise off puts it (Shift + Record), not a tick late.
    Single hits (no rate) and 1/16 repeats, whose every hit is sent in that window."""
    h = DrumHarness(pl17_image, pl17_manifest)
    p = unquant_setup(h)
    ref = DrumHarness(pl17_image, pl17_manifest)
    unquant_setup(ref, quantise_off=True, unquant=False)
    for x in (h, ref):
        play(x)
        single_hits(x)
    assert h.pattern_hits(0, p) == ref.pattern_hits(0, p)              # stock's own placement (u3_window.out)
    assert {s: m for s, (v, m) in h.pattern_hits(0, p).items()} == {4: 0b100000, 8: 0b100000, 13: 1, 17: 1, 20: 0b100}
    for x in (h, ref):
        set_rate(x, 3)
        hold(x, 1, 150, 186)                                            # before the pattern wraps (tick 192)
    assert h.pattern_hits(1, h.playing_pattern(1)) == ref.pattern_hits(1, ref.playing_pattern(1))
    assert h.pattern_hits(1, h.playing_pattern(1)) == recorded(h.sent, 2)
    assert {m for v, m in h.pattern_hits(1, h.playing_pattern(1)).values()} == {1}


def test_note_recorders_keep_quantise(pl17_image, pl17_manifest):
    """A Synth 1 recording with quantise on stays quantised while a latched drum's override runs (the note recorders
    share the refresh): its notes are the ones a harness without the drum records."""
    from notes import pattern_snapshot, recorded_notes
    h = DrumHarness(pl17_image, pl17_manifest)
    ref = DrumHarness(pl17_image, pl17_manifest)
    for x in (h, ref):
        unquant_setup(x, rate=3)
    toggle_latch(h)
    tap(h, DRUM_PAD + 1)                                                 # drum 2 latched, on in h alone
    out = []
    for x in (h, ref):
        play(x)
        x.until_tick(20)
        x.track(0)                                                       # Synth 1's Note view
        before = pattern_snapshot(x, 0)
        for t in (32, 51, 74):                                           # off the steps' tick 0
            x.until_tick(t)
            x.down(24)
            x.heartbeat(30)
            x.up(24)
        x.until_tick(110)
        out.append(recorded_notes(x, 0, before))
    assert quantise_bytes(h) == [0, 0, 0, 0] and note_quantise_bytes(h) == [1, 1, 1, 1]
    assert out[0] == out[1] and len(out[0]) == 3 and {n[4] for n in out[0]} == {0}   # whole steps, microstep 0
    p2 = h.playing_pattern(1)
    assert h.pattern_hits(1, p2) == recorded(h.sent, 2) and len(h.pattern_hits(1, p2)) > 10
