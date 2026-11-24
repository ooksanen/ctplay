"""Reference model of features/chord/repeat_math.c (note repeat: rates, velocity shapes, the grid)."""
TICKS = [0, 24, 12, 6, 3, 16, 8, 4, 2]   # rate 0 = off, 1-8 = 1/4 1/8 1/16 1/32, then the triplets 1/4T 1/8T 1/16T 1/32T
AS_STRUCK, FADE, SWELL, ACCENT = 0, 1, 2, 3


def ticks(rate: int) -> int:
    return TICKS[rate] if 0 <= rate <= 8 else 0


def vel(shape: int, v: int, e: int, beat: int) -> int:
    """Velocity of the hit e ticks after the press (v 1-127): integer maths, rounded down, at least 1."""
    m = min(e, 24)
    if shape == FADE:
        r = v * (32 - m) // 32           # v - (3v/4) m/24
    elif shape == SWELL:
        r = v * (8 + m) // 32            # v/4 + (3v/4) m/24
    elif shape == ACCENT:
        r = v if beat else 2 * v // 3
    else:
        r = v
    return max(1, r)


def due(tick: int, press_tick: int, ticks_: int, playing: int) -> int:
    """1 when `tick` is a hit of the repeat. e = ticks since the press (unsigned, wraps); e = 0 never (the press hit
    stands in). Playing: on the sequencer grid (tick % ticks == 0), skipping a point less than ticks / 2 after the
    press (2e >= ticks). Stopped: every `ticks` after the press. Rate off (ticks 0): never."""
    if ticks_ == 0:
        return 0
    e = (tick - press_tick) & 0xFFFFFFFF
    if e == 0:
        return 0
    if playing:
        return int(tick % ticks_ == 0 and 2 * e >= ticks_)
    return int(e % ticks_ == 0)
