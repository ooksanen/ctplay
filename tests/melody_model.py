"""Reference model of features/chord/melody_math.c (spec 2026-10-19-melodic-generator-design.md)."""
import arp_model
import chord_model
import euclid_model

POOL_MAX = 24
NEXT_MAX = 96                      # sixths: stock's longest note (its step gate / mutate clamp to 1-96)
DICE_TRIES = 16                    # a dice press steps its seed until the result changes, at most this often (Euclid: n)
WALK = [-2, -1, -1, -1, 0, 0, 1, 1, 1, 2]
SAME, UP, DOWN, UPDN, CLIMB, WALKING, RANDOM, BASS = range(8)


def seed_next(s: int) -> int:
    return (s >> 1) ^ (0xB8 if s & 1 else 0)


def weight(i: int) -> int:
    q = i % 16
    if q == 0:
        return 20 if i == 0 else 16
    return {0: 12, 3: 9, 2: 6}.get(q & 3, 3)


def groove(k: int, n: int, r: int, seed: int) -> int:
    if n == 0 or n > 32 or k == 0:
        return 0
    if k >= n:
        return (1 << n) - 1
    state, score = (seed << 8) | 0xA5, []
    for i in range(n):
        state = arp_model.lfsr(state)
        score.append(weight(i) + state % 5)
    order = sorted(range(n), key=lambda i: (-score[i], i))
    base = sum(1 << i for i in order[:k])
    return sum(1 << i for i in range(n) if base >> ((i + r) % n) & 1)


def root(cfg1: int, last: int, mask: int) -> int:
    d = cfg1 & 7
    if d == 0:
        return last
    return 12 * (((cfg1 >> 3) & 3) - 2) + chord_model.degrees_up(mask or chord_model.MAJOR_MASK, 72, d - 1)


def fifth(rt: int, mask: int) -> int:
    """The bass's fifth (a pitch class): the perfect fifth when the scale has it, else the scale's 5th degree."""
    if chord_model.in_scale(mask or chord_model.MAJOR_MASK, rt + 7):
        return (rt + 7) % 12
    return chord_model.degree_class(rt, mask, 4)


def pool(cfg0: int, rt: int, mask: int, s: int) -> tuple[list, int, int]:
    """The pool, the index of its root and the fifth's pitch class."""
    order, rng = cfg0 & 7, min(((cfg0 >> 4) & 3) + 1, 3)
    key, cand = (s >> 16) & 0xFF, set()
    if cfg0 >> 3 & 1:
        m = mask or chord_model.MAJOR_MASK
        cand |= {v for v in range(rt, rt + 12 * rng + 1) if chord_model.in_scale(m, v) and chord_model.playable(v, key)}
        if chord_model.playable(rt, key):
            cand.add(rt)                                   # a root outside the scale too
    else:
        if chord_model.shape_index(s) == 0:
            s = (s & ~7) | 1
        notes = [rt] + chord_model.chord_notes(rt, mask, s)
        cand |= {v + 12 * o for o in range(rng) for v in notes if chord_model.playable(v + 12 * o, key)}
    fc = fifth(rt, mask)
    if order == BASS:
        if not any(v % 12 == fc for v in cand):
            v = rt + (fc - rt % 12) % 12
            if chord_model.playable(v, key):
                cand.add(v)
    p = sorted(cand)[:POOL_MAX]
    at = next((i for i, v in enumerate(p) if v % 12 == rt % 12), 0)
    return p, at, fc


def line(cfg0: int, seed: int, n: int, pl: list, root_at: int, hits: int, fc: int) -> list:
    order, pn, s = cfg0 & 7, len(pl), seed - 1
    rng, last, pos, out, j = (seed << 8) | 0xA5, 0xFF, root_at, [], 0
    rc = pl[root_at] % 12
    for i in range(min(n, 32)):
        if not hits >> i & 1:
            continue
        if order == UP:
            idx = (s + j) % pn
        elif order == DOWN:
            idx = pn - 1 - (s + j) % pn
        elif order == UPDN:
            idx = arp_model.index(arp_model.UPDOWN, s + j, pn, 0, 0)[0]
        elif order == CLIMB:
            idx = (s + j // 3 + j % 3) % pn
        elif order == WALKING:
            if j:
                rng = arp_model.lfsr(rng)
                pos += WALK[rng % 10]
                if pos < 0:
                    pos = -pos
                if pos > pn - 1:
                    pos = 2 * (pn - 1) - pos
                pos = max(pos, 0)
            idx = pos
        elif order == RANDOM:
            idx, rng = arp_model.index(arp_model.RANDOM, j, pn, last, rng)
            last = idx
        else:
            idx = root_at
            if j:
                rng = arp_model.lfsr(rng)
                if i % 4 == 0:
                    others = [q for q in range(pn) if q != root_at and pl[q] % 12 == rc]
                    if rng % 4 == 0 and others:
                        rng = arp_model.lfsr(rng)
                        idx = others[rng % len(others)]
                else:
                    w = [4 if v % 12 == rc else 2 if v % 12 == fc else 1 for v in pl]
                    r = rng % sum(w)
                    for q, wq in enumerate(w):
                        if r < wq:
                            idx = q
                            break
                        r -= wq
        out.append(pl[idx])
        j += 1
    return out


def accent(a: int, j: int, i: int) -> int:
    return int({1: j == 0, 2: i % 4 == 0, 3: j % 3 == 0}.get(a, False))


def next_len(hits: int, n: int, i: int) -> int:
    d = 1
    while d < n and not hits >> ((i + d) % n) & 1:
        d += 1
    return min(NEXT_MAX, 6 * d)


def dice_rhythm(groove_on: int, k: int, n: int, rot: int, seed: int) -> tuple[int, int]:
    """Dice rhythm: (rhythm seed, rotation) after the press. The seed steps until the rhythm differs (Euclid: the
    rotation = seed % n, at most n tries; groove: the new seed, at most 16); when nothing can change, the last step."""
    def hits(r, sd):
        return groove(k, n, r % n, sd) if groove_on else euclid_model.mask(k, n, r)
    was = hits(rot, seed)
    for _ in range(DICE_TRIES if groove_on else n):
        seed = seed_next(seed)
        if not groove_on:
            rot = seed % n
        if hits(rot, seed) != was:
            break
    return seed, rot


def dice_notes(cfg0: int, seed: int, n: int, pl: list, root_at: int, fc: int, hits: int) -> int:
    """Dice notes: the notes seed after the press, stepped until the line differs (at most 16 tries)."""
    was = line(cfg0, seed, n, pl, root_at, hits, fc) if pl else []
    for _ in range(DICE_TRIES):
        seed = seed_next(seed)
        if was and line(cfg0, seed, n, pl, root_at, hits, fc) != was:
            break
    return seed


# --- PL14 variations (spec 2026-10-21-melody-variations-design.md, "What gets written") ---
AMOUNT_LIMIT = [0, 64, 85, 128]    # a draw (0-255) under this picks the item: off, 1/4, 1/3, 1/2
CYCLE_LEN = [0, 3, 5, 6, 7]        # cycle code -> steps (0 = the whole pattern)
M32 = 0xFFFFFFFF


def draw(seed: int, salt: int, i: int) -> int:
    x = ((seed << 16 | salt << 8 | i) * 0x9E3779B1) & M32
    x ^= x >> 15
    x = (x * 0x85EBCA6B) & M32
    x ^= x >> 13
    return x >> 24


def amount_limit(a: int) -> int:
    return AMOUNT_LIMIT[a]


def cycle_len(code: int) -> int:
    return CYCLE_LEN[code]


def repeat(base: int, c: int, n: int) -> int:
    """Bit i (i < n) = base bit (i % c); c = 0 or c >= n leaves the base unchanged."""
    if c == 0 or c >= n:
        return base
    return sum(1 << i for i in range(n) if base >> (i % c) & 1)


def combine(a: int, b: int, mode: int) -> int:
    return {1: a & b, 2: a | b, 3: a ^ b, 4: a & ~b & M32}.get(mode, a)


def _pick(hits: int, amount: int, seed: int, salt: int) -> int:
    """The hits (not the lowest) whose draw is under the amount's limit."""
    out = 0
    for i in range(32):
        if hits >> i & 1 and draw(seed, salt, i) < AMOUNT_LIMIT[amount]:
            out |= 1 << i
    return out & ~(hits & -hits) & M32


def thin(hits: int, amount: int, seed: int) -> int:
    return hits & ~_pick(hits, amount, seed, 1) & M32


def ties(hits: int, amount: int, seed: int) -> int:
    return _pick(hits, amount, seed, 2)


def jumps(struck: int, amount: int, seed: int) -> int:
    return _pick(struck, amount, seed, 3)


def jump(note: int, key: int) -> int:
    if note + 12 + key <= 139:
        return note + 12
    if note - 12 + key >= 12:
        return note - 12
    return note


# --- PL14: the Write's rhythm and line (spec 2026-10-21-melody-variations-design.md, "What gets written") ---
def cycle_steps(code: int, n: int) -> int:
    """The cycle's length c over n steps: n when there is no cycle or c >= n."""
    c = cycle_len(code)
    return c if 1 <= c < n else n


def first_rhythm(e0: int, e1: int, seed0: int, n: int, r2: int = 0) -> int:
    """Euclid or groove (euclid_cfg e0 / e1, the rhythm seed) over the cycle, its rotation mod c, repeated over n."""
    k, rot, c = e0 & 0x1F, e1 & 0x1F, cycle_steps(r2 & 7, n)
    base = groove(k, c, rot % c, seed0) if e0 & 0x80 else euclid_model.mask(k, c, rot % c)
    return repeat(base, c, n)


def second_rhythm(rc, n: int) -> int:
    return euclid_model.mask(rc[0] & 0x1F, n, (rc[1] & 0x1F) % n)


def final_hits(e0: int, e1: int, seed0: int, n: int, rc=(0, 0, 0)) -> int:
    """The hits a Write writes: the first rhythm, combined with the second (rhythm_cfg rc), then thinned."""
    a, mode = first_rhythm(e0, e1, seed0, n, rc[2]), rc[0] >> 5 & 7
    hits = combine(a, second_rhythm(rc, n), mode) if mode else a
    return thin(hits, rc[1] >> 5 & 3, seed0)


def written_line(cfg0: int, seed: int, n: int, pl: list, root_at: int, fc: int, hits: int, vary: int,
                 key: int) -> tuple[list, int]:
    """(the note of every hit, the tied hits): the line walks the struck hits only, a struck hit may jump an octave, a
    tied hit repeats the struck note before it. Order "same": ([], the tied hits)."""
    tied = ties(hits, vary & 3, seed)
    if cfg0 & 7 == SAME:
        return [], tied
    struck = hits & ~tied
    ln, jm = line(cfg0, seed, n, pl, root_at, struck, fc), jumps(struck, vary >> 2 & 3, seed)
    out, j, note = [], 0, 0
    for i in range(n):
        if not hits >> i & 1:
            continue
        if not tied >> i & 1:
            note = ln[j]
            j += 1
            if jm >> i & 1:
                note = jump(note, key)
        out.append(note)
    return out, tied


def hard_hits(cfg0: int, hits: int, tied: int, n: int, second: int = 0) -> int:
    """The hits written at 127: struck hits accented by the Melody accent (j = the struck index) or where the second
    rhythm hits (combine "accent"; pass 0 otherwise). A tied hit never."""
    out, j = 0, 0
    for i in range(n):
        if hits >> i & 1 and not tied >> i & 1:
            if accent(cfg0 >> 6 & 3, j, i) or second >> i & 1:
                out |= 1 << i
            j += 1
    return out


def dice_notes_written(cfg0: int, seed: int, n: int, pl: list, root_at: int, fc: int, hits: int, vary: int,
                       key: int) -> int:
    """Dice notes with the variations: the seed steps until the written result (notes, ties, jumps) differs, at most
    16 tries; nothing can change without a pool (a line order) or without hits."""
    can = (cfg0 & 7) == SAME or bool(pl)
    was = written_line(cfg0, seed, n, pl, root_at, fc, hits, vary, key) if can else None
    for _ in range(DICE_TRIES):
        seed = seed_next(seed)
        if can and written_line(cfg0, seed, n, pl, root_at, fc, hits, vary, key) != was:
            break
    return seed
