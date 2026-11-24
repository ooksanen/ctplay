"""Reference model of features/chord/roll_math.c (pattern strum, PL19)."""
WRITTEN_GAP = [0, 4, 2, 1]                       # ticks between a rolled chord's notes: off, slow, medium, fast
STEP_TICKS = [2, 3, 4, 6, 8, 12, 16, 24]         # stock's ticks a step by a pattern's rate (1/16 = rate 3 = 6)


def roll_sixths(ticks: int, step_ticks: int) -> int:
    return (ticks * 6 + step_ticks // 2) // step_ticks if step_ticks else 0


def roll_step(step: int, add: int, first: int, last: int) -> int:
    """step + add, wrapping within first..last; from a step outside first..last straight on (>= 32: the callers drop
    the note; beta 2)."""
    if last < first:
        return first
    if step < first or step > last:
        return step + add
    n = last - first + 1
    return first + ((step - first) % n + add % n) % n


def roll_order(notes, falling: bool):
    return sorted(notes, reverse=bool(falling))
