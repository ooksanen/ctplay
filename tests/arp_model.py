"""Reference model of features/chord/arp_math.c and of the arpeggiator's stopped clock (arp.c arp_on_ms)."""
BASE = [24, 12, 6, 3]                  # 1/4, 1/8, 1/16, 1/32 in ticks (24 per quarter note)
UP, DOWN, UPDOWN, DOWNUP, RANDOM, PLAYED, CHORD = 1, 2, 3, 4, 5, 6, 7


def rate_ticks(a0: int) -> int:
    base, mod = BASE[(a0 >> 3) & 3], (a0 >> 5) & 3
    if mod == 1:
        return base * 2 // 3
    if mod == 2 and base != 3:
        return base * 3 // 2
    return base


def gate_ticks(a0: int, a1: int) -> int:
    """Playing: ticks a note of the gate in a1 (bits 2-4: sixths - 1) sounds; 0 = legato (6/6)."""
    k, rt = ((a1 >> 2) & 7) + 1, rate_ticks(a0)
    if k >= 6:
        return 0
    return max(1, min((k * rt + 3) // 6, rt - 1))


def gate_ms(a0: int, a1: int, bpm: int) -> int:
    """Stopped: the same fraction of the step in ms (at least 1); 0 = legato."""
    k, rt = ((a1 >> 2) & 7) + 1, rate_ticks(a0)
    if k >= 6:
        return 0
    return max(1, k * rt * 2500 // (6 * bpm))


def lfsr(r: int) -> int:
    return (r >> 1) ^ (0xB400 if r & 1 else 0)


def bounce(pos: int, n: int) -> int:
    if n == 1:
        return 0
    p = pos % (2 * n - 2)
    return p if p < n else 2 * n - 2 - p


def index(pattern: int, pos: int, n: int, last: int, rng: int) -> tuple[int, int]:
    if pattern in (UP, PLAYED):
        return pos % n, rng
    if pattern == DOWN:
        return n - 1 - pos % n, rng
    if pattern == UPDOWN:
        return bounce(pos, n), rng
    if pattern == DOWNUP:
        return n - 1 - bounce(pos, n), rng
    rng = lfsr(rng)
    j = rng % n
    if n > 1 and j == last:
        j = (j + 1) % n
    return j, rng


def stopped_ticks(tick: int, acc: int, bpm: int, swing: int, ms: int) -> list[tuple[int, int]]:
    """(ms 1-based, tick) for each tick the stopped clock makes in the next `ms` milliseconds."""
    swing = min(max(swing, 1), 99)
    bpm = bpm or 120
    out = []
    for t in range(1, ms + 1):
        thr = 50 * ((100 - swing) if (tick // 6) & 1 else swing)
        acc += bpm
        if acc >= thr:
            acc -= thr
            tick = (tick + 1) & 0xFFFFFFFF
            out.append((t, tick))
    return out
