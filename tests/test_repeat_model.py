"""Note repeat's maths model (Global Constraints of plan 2026-10-25-drums-pl16)."""
import repeat_model as r


def test_rate_ticks():
    assert [r.ticks(x) for x in range(9)] == [0, 24, 12, 6, 3, 16, 8, 4, 2]


def test_fade_and_swell_over_one_beat():
    assert [r.vel(r.FADE, 120, e, 0) for e in (0, 12, 24, 48)] == [120, 75, 30, 30]
    assert [r.vel(r.SWELL, 120, e, 0) for e in (0, 12, 24, 48)] == [30, 75, 120, 120]
    assert all(r.vel(s, 1, e, b) == 1 for s in range(4) for e in range(60) for b in (0, 1))


def test_accent():
    assert r.vel(r.ACCENT, 99, 5, 1) == 99
    assert r.vel(r.ACCENT, 99, 5, 0) == 66


def test_due_playing_skips_a_close_grid_point():
    assert not r.due(12, 10, 6, 1) and r.due(18, 10, 6, 1)
    assert r.due(12, 8, 6, 1)


def test_due_stopped_from_the_press():
    assert r.due(11, 7, 4, 0) and r.due(15, 7, 4, 0) and not r.due(12, 7, 4, 0)


def test_never_due_at_the_press_or_with_the_rate_off():
    assert not r.due(12, 12, 6, 1) and not r.due(7, 7, 4, 0)
    assert not r.due(30, 5, 0, 1) and not r.due(30, 5, 0, 0)


def test_triplets_on_the_step_grid():
    d32 = [t for t in range(1, 48) if r.due(t, 0, 2, 1)]
    assert all(t % 6 in (0, 2, 4) for t in d32) and len(d32) == 23
    d16 = [t for t in range(1, 49) if r.due(t, 0, 4, 1)]
    assert d16 == [4 * k for k in range(1, 13)] and all(t % 6 in (0, 2, 4) for t in d16)
