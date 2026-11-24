"""Count-in (PL08, spec 2026-10-17-small-features-design.md D1-D3, section 1): Shift + Clear steps off -> click ->
count-in -> both; with the count-in on, Record armed and the transport stopped, Play gives one bar of stock's click at
the project tempo, then starts the sequencer recording."""
import pytest

from notes import NoteHarness, PLAY_STORE, TEMPO_STORE, param

pytestmark = pytest.mark.emu
CLEAR, PLAY, RECORD = 23, 17, 16
LED_REC, LED_CLEAR = 48, 55
COLS = [0x53, 0x17, 0x32, 0x4D]                  # Clear with Shift: off, click, count-in, both (upstream SC42.3)
REC_RED = 0x53
METRO_OBJ, METRO_ID, METRO_SET = 0x200109D8, 0x64, 0x08031608
FRAME = 10                                       # the tests draw the LEDs every 10 ms


def sym(m, name):
    return int(m["symbols"][name], 16)


def metro(h):
    return param(h, h.r32(METRO_OBJ + 0x38), 3)


def transport(h):
    return param(h, PLAY_STORE, 0), param(h, PLAY_STORE, 1)


def beat_ms(h):
    return 60000 // param(h, TEMPO_STORE, 0)


def shift_leds(h):
    h.shift(True)
    leds = h.leds()
    h.shift(False)
    return leds


def state(h):
    return COLS.index(shift_leds(h)[LED_CLEAR])


def set_state(h, want):
    for _ in range(4):
        if state(h) == want:
            return
        h.press(CLEAR, shift=True)
    raise AssertionError("Shift + Clear never reached the state")


def clicks(h):
    return [e for e in h.take("synth_on") if e[1] == 0xFF]


def run(h, ms):
    """ms heartbeats, the LEDs drawn every FRAME ms: (ms 1-based of each click, [(ms, Record LED)], ms the transport
    started or None)."""
    got, rec, started = [], [], None
    for t in range(1, ms + 1):
        h.heartbeat()
        got += [t] * len(clicks(h))
        if t % FRAME == 0:
            rec.append((t, h.leds()[LED_REC]))
            if started is None and transport(h)[0]:
                started = t
    return got, rec, started


def armed_count(h, want=2):
    h.track(0)
    set_state(h, want)
    h.press(RECORD)
    assert transport(h) == (0, 1)
    h.take()
    h.press(PLAY)


def test_shift_clear_steps_four_states(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    assert metro(h) == 0 and state(h) == 0                             # the dump: metronome off, no count-in
    got = []
    for _ in range(5):
        h.press(CLEAR, shift=True)
        got.append((state(h), metro(h), h.r8(sym(pl09_manifest, "ci_on"))))
    assert got == [(1, 1, 0), (2, 0, 1), (3, 1, 1), (0, 0, 0), (1, 1, 0)]
    assert h.leds()[LED_CLEAR] == NoteHarness(pl09_image).leds()[LED_CLEAR]     # without Shift: stock's LED


def test_power_on_state_follows_the_metronome(pl09_image):
    h = NoteHarness(pl09_image)
    h.call(METRO_SET, METRO_OBJ, METRO_ID, 1)                          # as a project load or stock's own toggle
    assert state(h) == 1


def test_the_count(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    armed_count(h)
    assert transport(h) == (0, 1)                                      # Play taken: nothing starts yet
    b = beat_ms(h)
    got, rec, started = run(h, 4 * b + 3 * FRAME)
    assert got == [1, 1 + b, 1 + 2 * b, 1 + 3 * b]                     # stock's click on each beat, from the press
    assert started is not None and 4 * b < started <= 4 * b + FRAME + 1, (started, 4 * b)
    assert transport(h) == (1, 1)                                      # playing and recording
    for t, led in rec:
        if t <= 4 * b:
            assert led == (REC_RED if (t - 1) % b < b // 2 else 0), (t, led)
    h.take()
    more, _, _ = run(h, 2 * b)
    assert more == []                                                  # the metronome is off: no click after


def test_both_count_then_stocks_metronome(pl09_image):
    h = NoteHarness(pl09_image)
    armed_count(h, 3)
    b = beat_ms(h)
    got, _, started = run(h, 4 * b + 2 * FRAME)
    assert got[:4] == [1, 1 + b, 1 + 2 * b, 1 + 3 * b] and started
    after, _, _ = run(h, 2 * b + 20)
    assert len(after) >= 2                                             # stock's metronome clicks while recording


def test_play_during_the_count_cancels(pl09_image):
    h = NoteHarness(pl09_image)
    armed_count(h)
    b = beat_ms(h)
    got, _, _ = run(h, b + b // 2)
    assert got == [1, 1 + b]
    h.press(PLAY)                                                      # cancel
    got, rec, started = run(h, 5 * b)
    assert got == [] and started is None and transport(h) == (0, 1)    # nothing starts; Record still armed
    assert [led for _, led in rec] == [h.leds()[LED_REC]] * len(rec)   # Record's LED: stock's armed colour again
    h.press(PLAY)                                                      # Play again: a new count from its press
    got, _, started = run(h, 4 * b + 2 * FRAME)
    assert got == [1, 1 + b, 1 + 2 * b, 1 + 3 * b] and started


def test_play_twice_quickly(pl09_image):
    h = NoteHarness(pl09_image)
    armed_count(h)
    h.heartbeat(5)
    h.press(PLAY)                                                      # cancels
    h.press(PLAY)                                                      # a new count
    b = beat_ms(h)
    h.take()
    got, _, started = run(h, 4 * b + 2 * FRAME)
    assert got == [1, 1 + b, 1 + 2 * b, 1 + 3 * b] and started and transport(h) == (1, 1)


def test_record_during_the_count_cancels(pl09_image):
    h = NoteHarness(pl09_image)
    armed_count(h)
    b = beat_ms(h)
    run(h, b // 2)
    h.press(RECORD)                                                    # disarmed: no count
    got, rec, started = run(h, 5 * b)
    assert got == [] and started is None and transport(h) == (0, 0)
    assert REC_RED not in [led for _, led in rec]


def test_a_transport_started_otherwise_cancels(pl09_image):
    """External clock or anything else starts the sequencer: no click after, and no Play press of ours (it would stop
    the transport)."""
    h = NoteHarness(pl09_image)
    armed_count(h)
    b = beat_ms(h)
    run(h, b // 2)
    h.press(PLAY)                                                      # cancel ...
    h.press(PLAY)                                                      # ... count again, then start it otherwise:
    h.heartbeat(3)
    h.uc.mem_write(h.r32(PLAY_STORE + 0xC), (1).to_bytes(4, "little"))     # p0 = playing (both copies)
    h.uc.mem_write(h.r32(PLAY_STORE + 0x10), (1).to_bytes(4, "little"))
    h.take()
    got, _, _ = run(h, 5 * b)
    assert got == [] and transport(h)[0] == 1


def test_metronome_changed_elsewhere(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    set_state(h, 2)
    h.call(METRO_SET, METRO_OBJ, METRO_ID, 1)                          # stock's parameter changed under us
    assert state(h) == 3
    h.press(CLEAR, shift=True)
    assert (state(h), metro(h)) == (0, 0)


@pytest.mark.parametrize("case", ["count-in off", "record not armed"])
def test_play_is_stock_without_a_count(stock_image, pl09_image, case):
    a, h = NoteHarness(stock_image), NoteHarness(pl09_image)
    for x in (a, h):
        x.track(0)
    if case == "count-in off":
        for x in (a, h):
            x.press(CLEAR, shift=True)                                 # click only (stock: metronome on)
            x.press(RECORD)
    else:
        h.press(CLEAR, shift=True)
        h.press(CLEAR, shift=True)                                     # count-in only; Record not armed
        a.press(CLEAR, shift=True)
        a.press(CLEAR, shift=True)                                     # stock: metronome off again
    for x in (a, h):
        x.take()
        x.press(PLAY)
        x.heartbeat(50)
    assert transport(h) == transport(a) and transport(h)[0] == 1
    assert h.take("synth_on") == a.take("synth_on")
