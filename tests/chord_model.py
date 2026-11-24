"""Reference model of chord_notes() in features/chord/chord_math.c (spec section 2). Pitches are keyboard
pitches (root-relative, +12); `mask` has 2 bits per semitone from the project root, 0 = in the scale; the project root
(key, 0-11) rides in bits 16-23 of the settings: a note plays only when pitch + key is within 12-139, as stock's pad check
(0x080523E8)."""
MAJOR_MASK = 0x00111044          # C#, D#, F#, G#, A# outside the scale: the major scale on the root
SHAPES = [(0,), (0, 2, 4), (0, 2, 4, 6), (0, 2, 4, 6, 8), (0, 1, 4), (0, 3, 4), (0, 2, 4, 8), (0, 2, 4, 5),
          (0, 4, 7), (0, 2, 6), (0, 3, 6, 9), (0, 3, 4, 6), (0, 2, 4, 5, 8)]   # 8-12: PL15, the row-2 shapes
SHAPE_NAMES = ["single", "triad", "7th", "9th", "sus2", "sus4", "add9", "6th",
               "power", "shell 7", "quartal", "7sus4", "6/9"]
WALK_LIMIT = 12 * 9


def settings(shape: int, inv: int = 0, spread: int = 0, bass: int = 0, rootless: int = 0, key: int = 0,
             shape2: int = 0) -> int:
    return shape | inv << 3 | spread << 5 | bass << 7 | rootless << 8 | shape2 << 9 | key << 16


def shape_index(s: int) -> int:
    """The effective shape: row 1 wins; with row 1 on single, the row-2 shape r (1-5) is shape 7 + r."""
    r = (s >> 9) & 0xF
    return 7 + r if (s & 7) == 0 and 1 <= r <= 5 else s & 7


def playable(v: int, key: int) -> bool:
    return 12 <= v + key <= 139


def in_scale(mask: int, note: int) -> bool:
    return (mask >> (2 * (note % 12))) & 3 == 0


def degrees_up(mask: int, note: int, steps: int) -> int:
    n = 0
    while steps and n < WALK_LIMIT:
        note += 1
        n += 1
        if in_scale(mask, note):
            steps -= 1
    return note


def lift(v: int, floor: int) -> int:
    """Raise v by octaves until it is above floor: the bass stays the lowest note."""
    while v <= floor:
        v += 12
    return v


def chord_notes(root: int, mask: int, s: int) -> list[int]:
    shape, inv, spread, bass = SHAPES[shape_index(s)], (s >> 3) & 3, (s >> 5) & 3, (s >> 7) & 1
    key = (s >> 16) & 0xFF
    rootless = bass and (s >> 8) & 1       # with bass: the pad is the bass, the chord an octave up without its root
    if mask == 0:
        mask = MAJOR_MASK
    tones = [degrees_up(mask, root, d) for d in shape]
    n = len(tones)
    if 0 < inv < n:
        for i in range(inv, n):
            tones[i] -= 12
    if spread == 1 and n >= 3:
        top = 0
        for i in range(1, n):
            if tones[i] > tones[top]:
                top = i
        pick = None
        for i in range(1, n):
            if i != top and (pick is None or tones[i] > tones[pick]):
                pick = i
        tones[pick] -= 12
    elif spread == 2:
        if n > 1:
            tones[1] += 12
        if n > 3:
            tones[3] += 12
    if rootless:
        tones = [root] + [lift(v + 12, root) for v in tones[1:] if (v - root) % 12]
    elif bass:
        if n >= 5 and playable(root - 12, key):   # 6 notes with the bass: leave out the 5th (shape degree 4)
            tones = [v for d, v in zip(shape, tones) if d != 4]
        tones = [root] + [lift(v, root - 12) for v in tones[1:]] + [root - 12]
    out: list[int] = []
    for v in tones[1:]:
        if playable(v, key) and v != root and v not in out and len(out) < 4:
            out.append(v)
    return out


def degree_class(root: int, mask: int, degree: int) -> int:
    return degrees_up(mask or MAJOR_MASK, root, degree) % 12


def lead(root: int, mask: int, s: int, prev: list[int], kind: int) -> int:
    """The inversion (0-3) whose chord on `root` moves least from `prev`: kind 1 close, 2 top line, 3 bottom line."""
    inv0 = (s >> 3) & 3
    if not prev:
        return inv0
    cands = []
    for inv in range(min(len(SHAPES[shape_index(s)]), 4)):
        notes = [root] + chord_notes(root, mask, s & ~(3 << 3) | inv << 3)
        close = sum(min(abs(v - p) for p in prev) for v in notes)
        top = abs(max(notes) - max(prev))
        bottom = abs(min(notes) - min(prev))
        cands.append((len(notes), close, top, bottom, inv))
    full = max(c[0] for c in cands)
    cands = [c for c in cands if c[0] == full]
    key = {1: lambda c: (c[1], c[4]), 2: lambda c: (c[2], c[1], c[4]), 3: lambda c: (c[3], c[1], c[4])}[kind]
    return min(cands, key=key)[4]
