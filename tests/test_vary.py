"""PL14's variation maths (features/chord/melody_math.c) in emulation against tests/melody_model.py. Pure functions,
arguments in r0-r3, result in r0."""
import random

import pytest
from unicorn.arm_const import UC_ARM_REG_R0

import melody_model as mm
from harness import Harness

pytestmark = pytest.mark.emu


def sym(m, name):
    return int(m["symbols"][name], 16)


def call(h, m, name, *args):
    h.call(sym(m, name), *args)
    return h.uc.reg_read(UC_ARM_REG_R0)


def test_draw_matches_the_model(pl14_image, pl14_manifest):
    h, rng = Harness(pl14_image), random.Random(14)
    cases = [(s, salt, i) for s in (1, 2, 128, 255) for salt in (1, 2, 3) for i in (0, 31)]
    cases += [(rng.randint(1, 255), rng.randint(1, 3), rng.randint(0, 31)) for _ in range(2000)]
    for s, salt, i in cases:
        assert call(h, pl14_manifest, "melody_draw", s, salt, i) == mm.draw(s, salt, i), (s, salt, i)


def test_tables_match_the_model(pl14_image, pl14_manifest):
    h = Harness(pl14_image)
    for c in range(5):
        assert call(h, pl14_manifest, "melody_cycle_len", c) == mm.cycle_len(c)
    for a in range(4):
        assert call(h, pl14_manifest, "melody_amount_limit", a) == mm.amount_limit(a)


def test_repeat_combine_thin_ties_jumps_match_the_model(pl14_image, pl14_manifest):
    h, rng, m = Harness(pl14_image), random.Random(77), pl14_manifest
    fn = {k: sym(m, "melody_" + k) for k in ("repeat", "combine", "thin", "ties", "jumps")}

    def c(name, *args):
        h.call(fn[name], *args)
        return h.uc.reg_read(UC_ARM_REG_R0)

    for n in range(1, 33):
        full = (1 << n) - 1 if n < 32 else 0xFFFFFFFF
        for _ in range(50):
            base, b, seed = rng.getrandbits(32) & full, rng.getrandbits(32) & full, rng.randint(1, 255)
            for code in range(5):
                cl = mm.cycle_len(code)
                assert c("repeat", base, cl, n) == mm.repeat(base, cl, n), (base, cl, n)
            for mode in range(1, 6):
                assert c("combine", base, b, mode) == mm.combine(base, b, mode), (base, b, mode)
            for a in range(4):
                assert c("thin", base, a, seed) == mm.thin(base, a, seed), (base, a, seed)
                assert c("ties", base, a, seed) == mm.ties(base, a, seed), (base, a, seed)
                assert c("jumps", base, a, seed) == mm.jumps(base, a, seed), (base, a, seed)


def test_jump_matches_the_model(pl14_image, pl14_manifest):
    h = Harness(pl14_image)
    for note in range(140):
        for key in range(12):
            assert call(h, pl14_manifest, "melody_jump", note, key) == mm.jump(note, key), (note, key)


# ---- The Write: the final rhythm, ties, octave jumps (Task 3) ----

from notes import NoteHarness, PATTERN_BASE, ROOT, SCALE_MASK, TEMPO_STORE, param   # noqa: E402
from chord_model import chord_notes, settings as chord_settings_word   # noqa: E402
from test_euclid import UNDO, WRITE, open_tools, pick, preview, set_range, steps, write   # noqa: E402
from test_euclid import expected as euclid_preview   # noqa: E402
from test_melody import T, configure, draft_of, hit_steps, mseed, units_steps   # noqa: E402

STEP, TIE = 28, 0x80
EMPTY = bytes([0, 7, 0, 0]) + bytes([0, 0, 0, 0x60]) * 6
WHITE_D = 0x02
BOTH, EITHER, ONE, FIRST, ACCENT = 1, 2, 3, 4, 5           # rhythm_cfg[t][0] bits 5-7
HALF = 3                                                   # an amount: 1/2


def vary(h, m, rc=(0, 0, 0), mv=0, t=T):
    """Track t's PL14 settings straight in RAM: rhythm_cfg (3 bytes) and melody_vary."""
    h.uc.mem_write(sym(m, "rhythm_cfg") + 3 * t, bytes(rc))
    h.uc.mem_write(sym(m, "melody_vary") + t, bytes([mv]))


def hit_mask(st: bytes, first=0, n=16) -> int:
    return sum(1 << i for i in range(n) if st[STEP * (first + i)])


def write_units(hits, tied, n, notes, gate, vel, hard):
    """Per hit the (note, length byte, velocity) of its units, `notes` = per hit its note list: a hit whose next hit is
    tied (within 96 sixths) ties into it (tie bit, length up to it), else its gate (6: to the next hit)."""
    st, out = hit_steps(hits, n), []
    for h_, i in enumerate(st):
        nxt = st[h_ + 1] if h_ + 1 < len(st) else None
        if nxt is not None and tied >> nxt & 1 and 6 * (nxt - i) <= mm.NEXT_MAX:
            ln = 6 * (nxt - i) | TIE
        else:
            ln = mm.next_len(hits, n, i) if gate == 6 else gate + 1
        out.append([(nt, ln, 127 if hard >> i & 1 else vel) for nt in notes[h_]])
    return out


def pool_of(h, c0, c1=0x10, last=60, shape=1):
    mask = h.r32(SCALE_MASK)
    return mm.pool(c0, mm.root(c1, last, mask), mask, chord_settings_word(shape) | h.r8(ROOT) << 16)


def line_expected(h, c0, seed, hits, mv, n=16, gate=2, vel=96, c1=0x10, last=60, shape=1, second=0):
    """The steps a Write of a line order leaves, per the model."""
    pl, at, fc = pool_of(h, c0, c1, last, shape)
    notes, tied = mm.written_line(c0, seed, n, pl, at, fc, hits, mv, h.r8(ROOT))
    hard = mm.hard_hits(c0, hits, tied, n, second)
    return units_steps(hits, write_units(hits, tied, n, [[nt] for nt in notes], gate, vel, hard), n=n), notes, tied


def chord_expected(h, c0, seed, hits, mv, n=16, gate=2, vel=96, last=60, shape=1, second=0):
    """The steps a Write of order "same" leaves (root = the last pad), per the model."""
    notes = [last] + (chord_notes(last, h.r32(SCALE_MASK), chord_settings_word(shape, key=h.r8(ROOT))) if shape else [])
    tied = mm.ties(hits, mv & 3, seed)
    hard = mm.hard_hits(c0, hits, tied, n, second)
    return units_steps(hits, write_units(hits, tied, n, [notes] * bin(hits).count("1"), gate, vel, hard), n=n), tied


def play(h, t, n_steps):
    """Stock plays the track from the start for n_steps steps: (sixths, 'on' / 'off', note) of its MIDI notes."""
    h.press(t)
    h.take()
    h.press(17)                                                    # Play
    step_ms = 60000 / param(h, TEMPO_STORE, 0) / 4
    ev = []
    for ms in range(1, int(n_steps * step_ms) + 2):
        h.heartbeat(1)
        for e in h.take("midi_on", "midi_off"):
            if e[2] == t:
                ev.append((round((ms - 1) / step_ms * 6), e[0][5:], e[3]))
    return ev


def stop(h):
    h.press(17)
    h.heartbeat(300)


def unit_step(units):
    body = b"".join(bytes(u) for u in units)
    return bytes([(1 << len(units)) - 1, 7, 0, 0]) + body + bytes([0, 0, 0, 0x60]) * (6 - len(units))


@pytest.mark.parametrize("case, want", [
    ("neighbours", [(0, "on"), (9, "off")]),                    # step 0 tie, length 6; step 1 length 3: one note
    ("distant", [(0, "on"), (27, "off")]),                      # step 0 tie, length 24 up to step 4; step 4 length 3
    ("distant-short", [(0, "on"), (6, "off"), (24, "on"), (27, "off")]),   # tie, length 6 only: two notes
    ("chain", [(0, "on"), (27, "off")]),                        # 0 -> 2 -> 4, each tie up to the next
])
def test_stock_ties(pl14_image, case, want):
    """Step 1: stock's own tie through stock's player, no CTPlay setting. The tie bit holds a note into the next unit of
    the same pitch when its length reaches that unit's step, neighbouring or several steps away; a length short of it
    ends the note there and strikes the next one again."""
    v = 96
    pat = {"neighbours": {0: [(60, 6 | TIE, 0, v)], 1: [(60, 3, 0, v)]},
           "distant": {0: [(60, 24 | TIE, 0, v)], 4: [(60, 3, 0, v)]},
           "distant-short": {0: [(60, 6 | TIE, 0, v)], 4: [(60, 3, 0, v)]},
           "chain": {0: [(60, 12 | TIE, 0, v)], 2: [(60, 12 | TIE, 0, v)], 4: [(60, 3, 0, v)]}}[case]
    h = NoteHarness(pl14_image)
    h.leds()
    h.uc.mem_write(PATTERN_BASE[T], b"".join(unit_step(pat[s]) if s in pat else EMPTY for s in range(32)))
    ev = play(h, T, 15)
    note = 60 - 12 + h.r8(ROOT)
    assert ev == [(s, k, note) for s, k in want], ev
    stop(h)
    assert h.sounding == set()


# Settings for the parity cases: the PL13 pads' own bytes (test_melody.configure's arguments).
SHAPES = (0, 1, 2, 3 | 0x80, 1 | 1 << 3 | 1 << 5, 0x80)


def parity_cases():
    rng, cases = random.Random(1313), []
    for i in range(48):
        k = rng.randint(1, 16)
        e0 = k | rng.randint(0, 2) << 5 | (0x80 if rng.random() < 0.35 else 0)
        c0 = (i % 8) | rng.randint(0, 1) << 3 | rng.randint(0, 2) << 4 | rng.randint(0, 3) << 6
        c1 = 0 if rng.random() < 0.5 else rng.randint(1, 7) | rng.randint(0, 3) << 3
        cases.append(dict(k=k, e0=e0, gate=rng.randint(0, 6), rot=rng.randint(0, 15), c0=c0, c1=c1,
                          last=rng.choice((48, 60, 61, 72, 95)), shape=rng.choice(SHAPES),
                          seed=(rng.randint(1, 255), rng.randint(1, 255)),
                          first_last=rng.choice(((0, 15), (0, 15), (2, 13), (0, 31), (5, 9))),
                          key=rng.choice((0, 0, 5, 11))))
    return cases


def parity_steps(img, m):
    h = NoteHarness(img)
    open_tools(h, T)
    out = []
    for c in parity_cases():
        c = dict(c)
        first, last = c.pop("first_last")
        h.uc.mem_write(ROOT, bytes([c.pop("key")]))
        set_range(h, T, first, last)
        configure(h, m, **c)
        write(h)
        out.append(steps(h, T))
    return out


def test_pl13_parity(pl14_image, pl14_manifest, pl13_published_image, pl13_published_manifest):
    """With every new setting 0, the same Writes (orders, groove, gates incl. "to the next hit", accents, degree roots,
    pool, range, chord shapes, pattern ranges, keys) leave the same steps as the published PL13."""
    got = parity_steps(pl14_image, pl14_manifest)
    want = parity_steps(pl13_published_image, pl13_published_manifest)
    assert len(got) >= 40
    bad = [i for i, (g, w) in enumerate(zip(got, want)) if g != w]
    assert not bad, (len(bad), bad[:5], parity_cases()[bad[0]])
    assert len({bytes(g) for g in got}) > 30                       # the cases differ


FINAL_CASES = [  # (e0, e1, rc, n): cycles, each combine, thinning
    (2, 0, (0, 0, 1), 16), (3, 2, (0, 0, 2), 16), (4, 7, (0, 0, 3), 16), (3, 12, (0, 0, 4), 12), (4 | 0x80, 1, (0, 0, 2), 16),
    (2, 0, (0, 0, 4), 6), (3, 0, (0, 0, 2), 1),                                              # the cycle as "whole"
    (8, 0, (5 | BOTH << 5, 1, 0), 16), (8, 0, (5 | EITHER << 5, 3, 0), 16), (6, 1, (6 | ONE << 5, 0, 0), 16),
    (8, 0, (4 | FIRST << 5, 2, 0), 16), (9, 0, (5 | BOTH << 5, 20, 0), 12), (5 | 0x80, 0, (3 | EITHER << 5, 1, 3), 16),
    (12, 0, (0, 1 << 5, 0), 16), (12, 0, (0, 2 << 5, 0), 16), (16, 0, (0, 3 << 5, 0), 16),
    (9, 3, (4 | ONE << 5, 2 | 3 << 5, 1), 32),
]


def test_final_hits_written(pl14_image, pl14_manifest):
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    open_tools(h, T)
    for e0, e1, rc, n in FINAL_CASES:
        set_range(h, T, 0, n - 1)
        configure(h, m, k=e0 & 0x1F, e0=e0 | 1 << 5, rot=e1, seed=(77, 1))
        vary(h, m, rc)
        hits = mm.final_hits(e0, e1, 77, n, rc)
        assert hits, (e0, e1, rc, n)
        assert preview(h) == euclid_preview(hits, n), (e0, e1, rc, n)
        write(h)
        st = steps(h, T)
        assert hit_mask(st, 0, n) == hits, (e0, e1, rc, n, hex(hit_mask(st, 0, n)), hex(hits))
        assert st == units_steps(hits, [[(60, 3, 96)]] * bin(hits).count("1"), n=n), (e0, e1, rc, n)
    # Combine "accent": the first rhythm's hits, hard where the second hits; with the Melody accent both apply.
    set_range(h, T, 0, 15)
    rc = (5 | ACCENT << 5, 1, 0)
    first, second = mm.first_rhythm(8, 0, 77, 16), mm.second_rhythm(rc, 16)
    assert first & second and first & ~second
    for c0 in (0, 1 << 6, 2 << 6):                                 # accent off, first hit, on the beat
        configure(h, m, k=8, e0=8, c0=c0, seed=(77, 1))                # velocity soft: 48
        vary(h, m, rc)
        write(h)
        want, _ = chord_expected(h, c0, 1, first, 0, vel=48, shape=0, second=second & first)
        assert steps(h, T) == want, c0
        if c0 == 2 << 6:
            assert any(not second >> i & 1 and i % 4 == 0 for i in hit_steps(first))   # a beat the second misses


def tie_seed(hits, amount, want):
    """The first notes seed whose ties satisfy `want`."""
    return next(s for s in range(1, 256) if want(mm.ties(hits, amount, s)))


def test_ties_written(pl14_image, pl14_manifest):
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    open_tools(h, T)
    hits = mm.first_rhythm(8, 0, 1, 16)                            # steps 0, 2, ... 14
    seed = tie_seed(hits, HALF, lambda t: bin(t).count("1") >= 3 and t & t >> 2)   # a run of two tied hits
    c0 = 1 | 2 << 6                                                # order up, accent on the beat
    configure(h, m, k=8, c0=c0, shape=1, seed=(1, seed))
    vary(h, m, mv=HALF)
    write(h)
    want, notes, tied = line_expected(h, c0, seed, hits, HALF)
    st = steps(h, T)
    assert st == want
    pl, at, fc = pool_of(h, c0)
    struck = hits & ~tied
    idx = hit_steps(hits)
    assert [notes[k] for k, i in enumerate(idx) if struck >> i & 1] == mm.line(c0, seed, 16, pl, at, struck, fc)
    for k, i in enumerate(idx):
        if tied >> i & 1:
            assert notes[k] == notes[k - 1] and st[STEP * i + 7] != 127, i     # the previous pitch, never hard
            assert st[STEP * idx[k - 1] + 5] == 6 * (i - idx[k - 1]) | TIE      # the unit before ties into it
    ev = play(h, T, 16)
    assert len([e for e in ev if e[1] == "on"]) == bin(struck).count("1"), ev   # one note-on per tied run
    stop(h)
    assert h.sounding == set()
    # Order "same": a tied hit repeats the chord.
    open_tools(h, T)
    configure(h, m, k=8, c0=2 << 6, shape=1, seed=(1, seed))
    write(h)
    want, tied2 = chord_expected(h, 2 << 6, seed, hits, HALF)
    assert tied2 == tied and steps(h, T) == want
    ev = play(h, T, 16)
    assert len([e for e in ev if e[1] == "on"]) == 3 * bin(struck).count("1"), ev
    stop(h)
    assert h.sounding == set()


def test_accent_every_third_counts_struck_notes(pl14_image, pl14_manifest):
    """Melody accent "every 3rd hit" with ties on: the hard (127) hits are every 3rd STRUCK note (tied hits are not
    counted), not every 3rd hit, the only accent mode where the two differ."""
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    open_tools(h, T)
    hits = mm.first_rhythm(12, 0, 1, 16)

    def differs(t):
        struck = [i for i in hit_steps(hits) if not t >> i & 1]
        return t and {i for k, i in enumerate(struck) if k % 3 == 0} != \
            {i for k, i in enumerate(hit_steps(hits)) if k % 3 == 0 and not t >> i & 1}
    seed = tie_seed(hits, HALF, differs)
    c0 = 1 | 3 << 6                                                # order up, accent every 3rd hit
    configure(h, m, k=12, c0=c0, shape=1, seed=(1, seed))
    vary(h, m, mv=HALF)
    write(h)
    want, _, tied = line_expected(h, c0, seed, hits, HALF)
    st = steps(h, T)
    assert st == want
    struck = [i for i in hit_steps(hits) if not tied >> i & 1]
    hard = [i for i in hit_steps(hits) if st[STEP * i + 7] == 127]
    assert hard == struck[::3], (hard, struck)
    assert hard != [i for k, i in enumerate(hit_steps(hits)) if k % 3 == 0 and not tied >> i & 1]


def test_jumps_written(pl14_image, pl14_manifest):
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    open_tools(h, T)
    hits = mm.first_rhythm(8, 0, 1, 16)
    for mv, c0, c1, key in ((HALF << 2, 1, 0x10, 0), (HALF << 2 | HALF, 1, 0x10, 0),
                            (HALF << 2, 1 | 1 << 3 | 2 << 4, 7 | 3 << 3, 11)):          # high: some jump down
        h.uc.mem_write(ROOT, bytes([key]))
        pl, at, fc = pool_of(h, c0, c1)

        def enough(s, mv=mv, c0=c0, key=key, pl=pl, at=at, fc=fc):
            struck = hits & ~mm.ties(hits, mv & 3, s)
            jm, ln = mm.jumps(struck, HALF, s), mm.line(c0, s, 16, pl, at, struck, fc)
            down = [nt for nt, i in zip(ln, hit_steps(struck)) if jm >> i & 1 and nt + 12 + key > 139]
            return bin(jm).count("1") >= 3 and (key != 11 or down) and (mv & 3 == 0 or struck != hits)
        seed = next(s for s in range(1, 256) if enough(s))
        configure(h, m, k=8, c0=c0, c1=c1, shape=1, seed=(1, seed))
        vary(h, m, mv=mv)
        write(h)
        want, notes, tied = line_expected(h, c0, seed, hits, mv, c1=c1)
        assert steps(h, T) == want, (mv, c0, key)
        struck = hits & ~tied
        plain = mm.line(c0, seed, 16, pl, at, struck, fc)
        jm = mm.jumps(struck, HALF, seed)
        assert not jm & 1                                              # never the first hit
        got = [nt for k, nt in enumerate(notes) if struck >> hit_steps(hits)[k] & 1]
        moved = [g - p for g, p in zip(got, plain)]
        assert set(moved) - {0} and set(moved) <= {0, 12, -12}
        if key == 11:
            assert -12 in moved
    h.uc.mem_write(ROOT, bytes([0]))
    configure(h, m, k=8, c0=0, shape=1)                                # order "same": no jumps
    vary(h, m, mv=HALF << 2)
    write(h)
    want, _ = chord_expected(h, 0, 1, hits, HALF << 2)
    assert steps(h, T) == want


def notes_played(ev):
    """Per MIDI note its [on, off] in sixths from play()'s events, off None while it still sounds at the end. Every
    note-on of a pitch must be closed by a note-off before the next note-on of that pitch, and a note-off must close
    one: a note stock holds on fails here."""
    out = {}
    for s, kind, nt in ev:
        notes = out.setdefault(nt, [])
        if kind == "on":
            assert not notes or notes[-1][1] is not None, ("a note-on over a sounding note", nt, s, ev)
            notes.append([s, None])
        else:
            assert notes and notes[-1][1] is None, ("a note-off with nothing sounding", nt, s, ev)
            notes[-1][1] = s
    return out


def notes_written(st, hits, n, notes, key, loops, end):
    """What stock should play of the written steps over `loops` loops of n steps, cut at `end` sixths: per MIDI note
    its [on, off] (None past the end) and its units. A tied run is one note, from its struck hit to its last unit's
    end."""
    runs = []
    for k, i in enumerate(hit_steps(hits, n)):
        ln = st[STEP * i + 5]
        if runs and runs[-1][3]:
            runs[-1][1:4] = [6 * i + (ln & 0x7F), runs[-1][2] + 1, ln & TIE]
        else:
            runs.append([6 * i, 6 * i + (ln & 0x7F), 1, ln & TIE, notes[k] - 12 + key])
    out = {}
    for lp in range(loops):
        for on, off, units, _, nt in runs:
            on, off = on + 6 * n * lp, off + 6 * n * lp
            if on < end:
                out.setdefault(nt, []).append(([on, off if off <= end else None], units))
    return out


def test_long_tie_chains_stay_within_96(pl14_image, pl14_manifest):
    """Review Focus: ties 1/2, gate "to the next hit", 32 steps: a run of tied hits 8 steps apart, a tie 16 steps
    apart, and one 24 steps apart (thinning): no length above 96 sixths, a tie only where its length reaches, every
    note closed before its pitch strikes again, across the loop's end, each one as long as its units (none held on)."""
    m = pl14_manifest
    for k, thin, want in ((4, 0, lambda t, hits: t == hits & ~1),               # 0 -> 8 -> 16 -> 24, one held note
                          (2, 0, lambda t, hits: t == 1 << 16),                 # 0 -> 16: 96 sixths, still a tie
                          (4, HALF, None)):                                     # 0 -> 24: too far, struck again
        h = NoteHarness(pl14_image)
        open_tools(h, T)
        set_range(h, T, 0, 31)
        if thin:
            rs = next(s for s in range(1, 256) if mm.final_hits(4, 0, s, 32, (0, thin << 5, 0)) == 1 | 1 << 24)
            hits = 1 | 1 << 24
            seed = tie_seed(hits, HALF, lambda t: t == 1 << 24)
        else:
            rs, hits = 1, mm.first_rhythm(k, 0, 1, 32)
            seed = tie_seed(hits, HALF, lambda t, hits=hits: want(t, hits))
        configure(h, m, k=k, gate=6, c0=1, shape=1, seed=(rs, seed))
        vary(h, m, rc=(0, thin << 5, 0), mv=HALF)
        write(h)
        st = steps(h, T)
        exp, notes, tied = line_expected(h, 1, seed, hits, HALF, n=32, gate=6)
        assert st == exp, (k, thin)
        lens = [st[STEP * i + 5] for i in hit_steps(hits, 32)]
        assert all(1 <= ln & 0x7F <= 96 for ln in lens), lens
        if thin:
            assert lens[0] == 96 and not lens[0] & TIE                # 24 steps: no tie, its own (capped) gate
        ev = play(h, T, 40)                                           # past the loop's end
        got = notes_played(ev)
        exp = notes_written(st, hits, 32, notes, h.r8(ROOT), 2, 6 * 40)
        assert got == {nt: [n for n, _ in v] for nt, v in exp.items()}, (k, thin, ev)
        for nt, v in exp.items():
            for (on, off), units in v:
                assert off is None or off - on <= 96 * units, (k, thin, nt, on, off, units)
        ons = [e for e in ev if e[1] == "on" and e[0] < 192]
        assert len(ons) == bin(hits & ~tied).count("1") + (1 if thin else 0), ev        # thin: the far tie strikes again
        assert max(on for v in got.values() for on, _ in v) >= 192                     # the run crosses the loop's end
        stop(h)
        assert h.sounding == set(), (k, thin, sorted(h.sounding))


def test_no_hits_left_in_a_draft_writes_nothing(pl14_image, pl14_manifest):
    """Review Focus: in a draft, combine "both" with rhythms that share no step: the release writes nothing (the last
    draft write stays), Write is dark, Undo still returns the pre-draft pattern."""
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    open_tools(h, T)
    before = steps(h, T)
    configure(h, m, k=8, c0=6, shape=1)                            # order random: a draft
    write(h)
    assert draft_of(h, m) == T + 1
    pick(h, 3)                                                     # 4 hits: the draft re-writes
    last = steps(h, T)
    assert hit_mask(last) == 0x1111
    vary(h, m, rc=(8 | BOTH << 5, 1, 0))                           # the odd steps: none in common with 8 hits
    pick(h, 7)                                                     # 8 hits: the even steps
    assert mm.final_hits(8, 0, 1, 16, (8 | BOTH << 5, 1, 0)) == 0
    assert steps(h, T) == last and h.leds()[WRITE] == 0
    pick(h, WRITE)                                                 # nothing to write: still nothing
    assert steps(h, T) == last and h.leds()[WRITE] == 0
    pick(h, UNDO)
    assert steps(h, T) == before and draft_of(h, m) == 0
    pick(h, WRITE)                                                 # outside a draft: no hits, Write does not arm
    assert h.leds()[WRITE] == 0
    pick(h, WRITE)
    assert steps(h, T) == before


def test_no_first_hits_writes_the_final_rhythm(pl14_image, pl14_manifest):
    """Final review: first-rhythm hits 0 (a new project's default) with combine "either" or "one, not both" leaves the
    second rhythm as the final one: the preview, Write's LED and the Write all follow it, and the combine (a new
    setting) starts a draft. With combine "both" nothing is left: Write dark, nothing written."""
    m = pl14_manifest
    for mode in (EITHER, ONE):
        h = NoteHarness(pl14_image)
        open_tools(h, T)
        configure(h, m, k=0, c0=0, shape=0)                        # velocity medium, order "same", no chord
        rc = (5 | mode << 5, 1, 0)
        vary(h, m, rc)
        hits = mm.final_hits(1 << 5, 0, 1, 16, rc)
        assert hits == mm.second_rhythm(rc, 16) and hits, mode
        assert preview(h) == euclid_preview(hits, 16) and h.leds()[WRITE] == ORANGE_D, mode
        write(h)
        assert steps(h, T) == units_steps(hits, [[(60, 3, 96)]] * bin(hits).count("1")), mode
        assert draft_of(h, m) == T + 1, mode
    h = NoteHarness(pl14_image)
    open_tools(h, T)
    before = steps(h, T)
    configure(h, m, k=0, c0=0, shape=0)
    vary(h, m, (5 | BOTH << 5, 1, 0))
    assert h.leds()[WRITE] == 0
    write(h)
    assert steps(h, T) == before and draft_of(h, m) == 0 and h.leds()[WRITE] == 0


def test_dice_notes_in_same_with_ties(pl14_image, pl14_manifest):
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    open_tools(h, T)
    hits = mm.first_rhythm(8, 0, 1, 16)
    configure(h, m, k=8, c0=0, shape=1)                            # order "same", ties off: dark, rolls nothing
    assert h.leds()[29] == 0
    pick(h, 29)
    assert mseed(h, m, T) == (1, 1)
    vary(h, m, mv=HALF)
    assert h.leds()[29] == WHITE_D
    seed = 1
    for _ in range(6):
        pick(h, 29)
        new = mm.dice_notes_written(0, seed, 16, [], 0, 0, hits, HALF, 0)
        assert mseed(h, m, T) == (1, new) and mm.ties(hits, HALF, new) != mm.ties(hits, HALF, seed)
        seed = new
    write(h)
    want, _ = chord_expected(h, 0, seed, hits, HALF)
    assert steps(h, T) == want


def test_dice_notes_compares_the_written_result(pl14_image, pl14_manifest):
    """Dice notes with ties and jumps on: each press steps the seed until the notes, the ties or the jumps written
    differ (order up over a triad: the line alone repeats every third seed)."""
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    open_tools(h, T)
    hits = mm.first_rhythm(8, 0, 1, 16)
    mv = 1 | 1 << 2                                                # ties 1/4, jumps 1/4
    configure(h, m, k=8, c0=1, shape=1)
    vary(h, m, mv=mv)
    write(h)                                                       # order up: a draft, each press writes
    assert draft_of(h, m) == T + 1
    pl, at, fc = pool_of(h, 1)
    seed = 1
    for _ in range(12):
        was = steps(h, T)
        pick(h, 29)
        seed = mm.dice_notes_written(1, seed, 16, pl, at, fc, hits, mv, h.r8(ROOT))
        assert mseed(h, m, T)[1] == seed
        want, _, _ = line_expected(h, 1, seed, hits, mv)
        assert steps(h, T) == want != was


# ---- The pages: Pattern tools 2, Phrasing, the cycle row; features on two pages (Task 4) ----

from test_euclid import pattern_at   # noqa: E402
from test_melody import ANIMATED, RGB_TABLE, ecfg, mcfg, open_melody   # noqa: E402
import euclid_model   # noqa: E402

TOOLS, MELODY, KEYS = 2, 3, 7
DOWN, UP, LED_DOWN, LED_UP = 19, 20, 51, 52
WHITE = 0x01
GREEN, GREEN_D, BLUE, BLUE_D, MAG, MAG_D = 0x17, 0x18, 0x07, 0x08, 0x32, 0x38
ORANGE, ORANGE_D, YELLOW, YELLOW_D = 0x45, 0x46, 0x2D, 0x2E
CYAN, CYAN_D, VIOLET, VIOLET_D = 0x4D, 0x4E, 0x49, 0x4A        # cycle / thinning / ties, combine (PL14)
GATE_CODES = set(range(0x63, 0x69))
PAD_CYCLE, PAD_ROT, PAD_COMBINE, PAD_THIN = 24, 16, 19, 24
WALK = [(0, 0, "chords"), (1, 0, "arp"), (2, 0, "tools"), (2, 1, "tools2"), (3, 0, "melody"), (3, 1, "phrasing"),
        (7, 0, "keys")]
SLOT_COL = {0: GREEN, 1: BLUE, 2: ORANGE, 3: YELLOW, 7: MAG}


def rcfg(h, m, t=T):
    return tuple(h.uc.mem_read(sym(m, "rhythm_cfg") + 3 * t, 3))


def mvary(h, m, t=T):
    return h.r8(sym(m, "melody_vary") + t)


def where(h, m, t=T):
    """(page_slot, the sub-page of that slot) of track t."""
    slot, sub = h.r8(sym(m, "page_slot") + t), h.r8(sym(m, "page_sub") + t)
    return slot, (sub >> (slot - TOOLS) & 1) if slot in (TOOLS, MELODY) else 0


def shown(leds):
    """Which page the pad LEDs show."""
    if all(c in (VIOLET, VIOLET_D) for c in leds[19:24]):
        return "tools2"
    if all(c in (CYAN, CYAN_D) for c in leds[24:28]) and leds[16:19] == [WHITE_D] * 3:
        return "tools"
    if all(c in (CYAN, CYAN_D) for c in leds[0:3]) and all(c in (MAG, MAG_D) for c in leds[4:7]):
        return "phrasing"
    if leds[0] in (YELLOW, YELLOW_D) and leds[8] in (GREEN, GREEN_D):
        return "melody"
    if leds[0] in (GREEN, GREEN_D) and leds[8] in (BLUE, BLUE_D):
        return "arp"
    if leds[0] in (GREEN, GREEN_D) and leds[8] in (GREEN, GREEN_D) and leds[24] in (BLUE, BLUE_D):
        return "chords"
    if (leds[0] in (MAG, MAG_D) and leds[1] in (GREEN, GREEN_D) and all(c in (WHITE, WHITE_D) for c in leds[2:4])
            and leds[4:32] == [0] * 28):                           # PL18: two toggles; PL19: pattern strum pads 3-4
        return "keys"
    return None


def toc(h, slot):
    """Shift held on an open page: the table of contents' pad of `slot`."""
    h.shift(True)
    pick(h, 24 + slot)
    h.shift(False)


def go(h, t, opener, slot, want):
    """Open the feature on `slot` (on its remembered page), then its page `want` (the re-tap flips it)."""
    opener(h, t)
    if shown(h.leds()) != want:
        toc(h, slot)
    assert shown(h.leds()) == want


def open_tools1(h, t=T):
    go(h, t, open_tools, TOOLS, "tools")


def open_tools2(h, t=T):
    go(h, t, open_tools, TOOLS, "tools2")


def open_phrasing(h, t=T):
    go(h, t, open_melody, MELODY, "phrasing")


def test_new_colours_are_steady_and_distinct(pl14_image, pl14_manifest):
    h = NoteHarness(pl14_image)
    h.leds()
    rgb = {}
    for code in (CYAN, CYAN_D, VIOLET, VIOLET_D, MAG, MAG_D):
        b, g, r, _ = h.uc.mem_read(RGB_TABLE + 4 * code, 4)
        rgb[code] = (r, g, b)
        assert code not in ANIMATED, hex(code)
    for code in (CYAN, CYAN_D):                                    # cyan: green and blue, no red
        r, g, b = rgb[code]
        assert g > 4 * max(r, 1) and b > 4 * max(r, 1), (hex(code), rgb[code])
    for code in (VIOLET, VIOLET_D):                                # violet: blue first, then red over green
        r, g, b = rgb[code]
        assert b > r > g, (hex(code), rgb[code])
    for code in (MAG, MAG_D):
        r, g, b = rgb[code]
        assert r == b and r > 3 * g, (hex(code), rgb[code])
    for bright, dim in ((CYAN, CYAN_D), (VIOLET, VIOLET_D), (MAG, MAG_D)):
        assert sum(rgb[dim]) < sum(rgb[bright]) / 3
    # On every page the new rows' codes are their own: no other control of that page uses them.
    open_tools(h, T)
    configure(h, pl14_manifest, k=8)
    pick(h, PAD_CYCLE)                                             # a cycle lit
    leds = h.leds()
    assert leds[24:28] == [CYAN, CYAN_D, CYAN_D, CYAN_D]
    assert not {CYAN, CYAN_D} & set(leds[:24] + leds[28:32])
    toc(h, TOOLS)
    pick(h, PAD_COMBINE)
    pick(h, PAD_THIN)
    leds = h.leds()
    assert leds[19:24] == [VIOLET] + [VIOLET_D] * 4 and leds[24:27] == [CYAN] + [CYAN_D] * 2
    others = leds[:19] + leds[27:32]
    assert not {CYAN, CYAN_D, VIOLET, VIOLET_D} & set(others)
    open_phrasing(h, T)
    pick(h, 0)
    pick(h, 4)
    leds = h.leds()
    assert leds[0:3] == [CYAN, CYAN_D, CYAN_D] and leds[4:7] == [MAG, MAG_D, MAG_D]
    assert not {CYAN, CYAN_D, MAG, MAG_D} & set(leds[3:4] + leds[7:32])


def test_table_of_contents_flips_a_features_pages(pl14_image, pl14_manifest):
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    h.leds()
    h.track(T)
    h.press(T, shift=True)                                         # power-on: Chords
    assert where(h, m) == (0, 0) and shown(h.leds()) == "chords"
    h.shift(True)
    pick(h, 24 + TOOLS)                                            # another feature's pad: its page 1 (bit 0 clear)
    assert where(h, m) == (TOOLS, 0) and h.leds()[24:32] == [GREEN_D, BLUE_D, ORANGE, YELLOW_D, 0, 0, 0, MAG_D]
    pick(h, 24 + TOOLS)                                            # the open feature's pad: its other page
    assert where(h, m) == (TOOLS, 1) and h.r8(sym(m, "page_sub") + T) == 1
    assert h.leds()[24:32] == [GREEN_D, BLUE_D, ORANGE, YELLOW_D, 0, 0, 0, MAG_D]   # one pad per feature
    pick(h, 24 + TOOLS)
    assert where(h, m) == (TOOLS, 0) and h.r8(sym(m, "page_sub") + T) == 0
    pick(h, 24 + TOOLS)
    h.shift(False)
    assert shown(h.leds()) == "tools2"
    toc(h, MELODY)                                                 # Melody on its bit: page 1
    assert where(h, m) == (MELODY, 0) and shown(h.leds()) == "melody"
    toc(h, MELODY)
    assert where(h, m) == (MELODY, 1) and shown(h.leds()) == "phrasing" and h.r8(sym(m, "page_sub") + T) == 3
    toc(h, TOOLS)                                                  # remembered: Pattern tools 2
    assert where(h, m) == (TOOLS, 1) and shown(h.leds()) == "tools2"
    toc(h, MELODY)                                                 # remembered: Phrasing
    assert where(h, m) == (MELODY, 1) and shown(h.leds()) == "phrasing"
    for slot, name in ((0, "chords"), (KEYS, "keys"), (1, "arp")):  # one-page features: the re-tap stays
        toc(h, slot)
        toc(h, slot)
        assert where(h, m) == (slot, 0) and shown(h.leds()) == name and h.r8(sym(m, "page_sub") + T) == 3
    toc(h, 4)                                                      # a dark pad: nothing
    assert where(h, m) == (1, 0)
    h.press(T)                                                     # closed; Shift + the track opens Arp
    h.press(T, shift=True)
    toc(h, MELODY)
    assert shown(h.leds()) == "phrasing"
    h.press(T)
    h.track(0)                                                     # another track: its own bits
    h.press(0, shift=True)
    toc(h, MELODY)
    assert where(h, m, 0) == (MELODY, 0) and shown(h.leds()) == "melody"
    assert h.r8(sym(m, "page_sub") + T) == 3


def test_up_down_walk_all_pages(pl14_image, pl14_manifest):
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    h.leds()
    h.track(T)
    h.press(T, shift=True)
    for i, (slot, sub, name) in enumerate(WALK):                   # ▼ through the seven
        leds = h.leds()
        assert where(h, m) == (slot, sub) and shown(leds) == name, (i, name, where(h, m))
        assert leds[LED_DOWN] == (SLOT_COL[WALK[i + 1][0]] if i + 1 < len(WALK) else 0), name
        assert leds[LED_UP] == (SLOT_COL[WALK[i - 1][0]] if i else 0), name
        h.press(DOWN)
    assert where(h, m) == (KEYS, 0)                                # no page after Keys: stays
    for i in reversed(range(len(WALK))):                           # and ▲ back
        slot, sub, name = WALK[i]
        assert where(h, m) == (slot, sub) and shown(h.leds()) == name, (i, name, where(h, m))
        h.press(UP)
    assert where(h, m) == (0, 0) and h.r8(sym(m, "page_sub") + T) == 0
    toc(h, MELODY)                                                 # ▲ from Melody: Pattern tools 2; ▼ from it: Melody
    h.press(UP)
    assert where(h, m) == (TOOLS, 1)
    h.press(DOWN)
    assert where(h, m) == (MELODY, 0)


def second_preview(hits, n):
    return [WHITE if hits >> s & 1 else WHITE_D if s < n else 0 for s in range(16)]


def test_tools2_pads_set_rhythm_cfg(pl14_image, pl14_manifest):
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    open_tools2(h)
    leds = h.leds()
    assert leds[:16] == [WHITE_D] * 16 and leds[16:19] == [WHITE_D] * 3
    assert leds[19:24] == [VIOLET_D] * 5 and leds[24:27] == [CYAN_D] * 3 and leds[27] == 0
    assert leds[28] == WHITE_D and leds[29:32] == [0, 0, 0]      # dice; dice notes dark ("same"); no Undo; no hits
    for pad in range(16):                                          # second rhythm: pad k = k + 1 hits, white preview
        pick(h, pad)
        assert rcfg(h, m) == (pad + 1, 0, 0)
        assert h.leds()[:16] == second_preview(euclid_model.mask(pad + 1, 16, 0), 16), pad
    pick(h, 2)                                                     # 3 hits
    set_range(h, T, 0, 11)                                         # 12 steps: dark past them
    assert h.leds()[:16] == second_preview(euclid_model.mask(3, 12, 0), 12)
    pick(h, PAD_ROT)                                               # earlier
    assert rcfg(h, m)[1] == 1 and h.leds()[:16] == second_preview(euclid_model.mask(3, 12, 1), 12)
    pick(h, PAD_ROT + 1)                                           # later
    pick(h, PAD_ROT + 1)                                           # later from 0: wraps at n
    assert rcfg(h, m)[1] == 11 and h.leds()[:16] == second_preview(euclid_model.mask(3, 12, 11), 12)
    pick(h, PAD_ROT + 2)                                           # back to the start
    assert rcfg(h, m) == (3, 0, 0)
    for v in range(1, 6):                                          # combine: one pad per value
        pick(h, PAD_COMBINE + v - 1)
        assert rcfg(h, m) == (3 | v << 5, 0, 0)
        assert h.leds()[19:24] == [VIOLET if i == v - 1 else VIOLET_D for i in range(5)]
    pick(h, PAD_COMBINE + 4)                                       # the lit pad: off
    assert rcfg(h, m) == (3, 0, 0) and h.leds()[19:24] == [VIOLET_D] * 5
    pick(h, PAD_ROT)
    for v in range(1, 4):                                          # thinning, the rotation kept
        pick(h, PAD_THIN + v - 1)
        assert rcfg(h, m) == (3, 1 | v << 5, 0)
        assert h.leds()[24:27] == [CYAN if i == v - 1 else CYAN_D for i in range(3)]
    pick(h, PAD_THIN + 2)
    assert rcfg(h, m) == (3, 1, 0) and h.leds()[24:27] == [CYAN_D] * 3
    pick(h, PAD_COMBINE + 1)                                       # either: the first rhythm's preview on page 1 follows
    configure(h, m, k=2)
    pick(h, 27)                                                    # pad 28: dark, nothing
    assert rcfg(h, m) == (3 | 2 << 5, 1, 0) and h.leds()[27] == 0 and ecfg(h, m, T) == (2 | 1 << 5, 2 << 5)
    toc(h, TOOLS)
    want = mm.final_hits(2 | 1 << 5, 0, 1, 12, (3 | 2 << 5, 1, 0))
    assert want == mm.first_rhythm(2, 0, 1, 12) | euclid_model.mask(3, 12, 1)
    assert preview(h) == euclid_preview(want, 12)


def test_phrasing_pads_set_melody_vary(pl14_image, pl14_manifest):
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    open_phrasing(h)
    leds = h.leds()
    assert leds[0:3] == [CYAN_D] * 3 and leds[4:7] == [MAG_D] * 3
    assert leds[3] == leds[7] == 0 and leds[8:28] == [0] * 20 and leds[28] == WHITE_D
    for v in range(1, 4):
        pick(h, v - 1)                                             # ties
        assert mvary(h, m) == v and h.leds()[0:3] == [CYAN if i == v - 1 else CYAN_D for i in range(3)]
    for v in range(1, 4):
        pick(h, 4 + v - 1)                                         # jumps, the ties kept
        assert mvary(h, m) == 3 | v << 2 and h.leds()[4:7] == [MAG if i == v - 1 else MAG_D for i in range(3)]
    assert h.leds()[29] == WHITE_D                                 # ties on: dice notes lit in "same"
    pick(h, 2)                                                     # the lit pad: off
    assert mvary(h, m) == 3 << 2 and h.leds()[0:3] == [CYAN_D] * 3
    pick(h, 6)
    assert mvary(h, m) == 0 and h.leds()[4:7] == [MAG_D] * 3
    before = (mvary(h, m), rcfg(h, m), ecfg(h, m, T), mcfg(h, m, T))
    for pad in [3, 7] + list(range(8, 28)):                        # dark, nothing
        pick(h, pad)
        assert (mvary(h, m), rcfg(h, m), ecfg(h, m, T), mcfg(h, m, T)) == before, pad
        assert h.leds()[pad] == 0


def test_cycle_pads_and_rotation_mod_c(pl14_image, pl14_manifest):
    """Review Focus: a stored rotation beyond the cycle (12, cycle 5) is applied mod c; the rotate pads move from there
    and wrap at c; dice rhythm's rotation stays within the cycle."""
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    open_tools(h, T)
    for v in range(1, 5):                                          # cycle 3 · 5 · 6 · 7
        pick(h, PAD_CYCLE + v - 1)
        assert rcfg(h, m) == (0, 0, v)
        assert h.leds()[24:28] == [CYAN if i == v - 1 else CYAN_D for i in range(4)]
    pick(h, PAD_CYCLE + 3)                                         # the lit pad: the whole pattern
    assert rcfg(h, m) == (0, 0, 0) and h.leds()[24:28] == [CYAN_D] * 4
    configure(h, m, k=2, rot=12)
    pick(h, PAD_CYCLE + 1)                                         # cycle 5
    want = mm.final_hits(2 | 1 << 5, 12, 1, 16, (0, 0, 2))
    assert want == mm.repeat(euclid_model.mask(2, 5, 12 % 5), 5, 16)
    assert preview(h) == euclid_preview(want, 16)
    pick(h, PAD_ROT)                                               # earlier: from 12 % 5 = 2
    assert ecfg(h, m, T)[1] & 0x1F == 3
    for r in (2, 1, 0, 4):                                         # later, wrapping at 5
        pick(h, PAD_ROT + 1)
        assert ecfg(h, m, T)[1] & 0x1F == r
        assert preview(h) == euclid_preview(mm.repeat(euclid_model.mask(2, 5, r), 5, 16), 16)
    pick(h, PAD_ROT)                                               # earlier from 4: 0
    assert ecfg(h, m, T)[1] & 0x1F == 0
    for _ in range(12):                                            # dice rhythm: the rotation within the cycle
        pick(h, 28)
        rot, seed = ecfg(h, m, T)[1] & 0x1F, mseed(h, m, T)[0]
        assert rot == seed % 5 and rot < 5, (rot, seed)


def test_second_rotation_mod_n_after_shortening(pl14_image, pl14_manifest):
    """Review Focus: the second rhythm's rotation stored past a shortened pattern's length is applied mod n; the rotate
    pads move from there."""
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    open_tools2(h)
    pick(h, 2)                                                     # 3 hits
    for _ in range(4):
        pick(h, PAD_ROT + 1)                                       # later x 4 over 16: 12
    assert rcfg(h, m)[1] == 12
    set_range(h, T, 0, 7)                                          # 8 steps
    assert h.leds()[:16] == second_preview(euclid_model.mask(3, 8, 12 % 8), 8)
    pick(h, PAD_ROT)                                               # earlier: from 4
    assert rcfg(h, m)[1] == 5
    vary(h, m, rc=(3, 12 | 1 << 5, 0))                             # 12 again, thinning 1/4
    pick(h, PAD_ROT + 1)                                           # later: from 4, the thinning kept
    assert rcfg(h, m)[1] == 3 | 1 << 5
    assert h.leds()[:16] == second_preview(euclid_model.mask(3, 8, 3), 8)


NEW_SETTINGS = [  # (name, the presses that set it alone: (page, pad)...)
    ("combine", [("tools2", 15), ("tools2", PAD_COMBINE)]),       # 16 second hits, then "both": the first rhythm
    ("thinning", [("tools2", PAD_THIN)]),
    ("cycle", [("tools", PAD_CYCLE)]),
    ("ties", [("phrasing", 0)]),
    ("jumps", [("phrasing", 4)]),
]
GO = {"tools": open_tools1, "tools2": open_tools2, "phrasing": open_phrasing}


@pytest.mark.parametrize("name, presses", NEW_SETTINGS, ids=[s[0] for s in NEW_SETTINGS])
def test_new_settings_start_a_draft(pl14_image, pl14_manifest, name, presses):
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    open_tools(h, T)
    configure(h, m, k=8, c0=0, shape=1)                            # plain Euclid: no draft by itself
    before = steps(h, T)
    for page, pad in presses:
        GO[page](h, T)
        pick(h, pad)
    open_tools1(h, T)
    pick(h, WRITE)                                                 # the first press arms
    assert h.leds()[WRITE] == 0x47 and steps(h, T) == before and draft_of(h, m) == 0
    pick(h, WRITE)
    assert draft_of(h, m) == T + 1 and steps(h, T) != before
    for move, page, pad in ((None, "tools", 4), (TOOLS, "tools2", 2), (DOWN, "melody", 2), (DOWN, "phrasing", 6)):
        if move == DOWN:                                           # a pick on each page (closing would end the draft)
            h.press(DOWN)
        elif move is not None:
            toc(h, move)
        assert shown(h.leds()) == page and draft_of(h, m) == T + 1, page
        h.uc.mem_write(pattern_at(h, T), bytes(0x380))             # scribble: the release re-writes
        h.down(pad)
        assert steps(h, T) == bytes(0x380), page                   # not during the press
        h.up(pad)
        assert steps(h, T) != bytes(0x380) and hit_mask(steps(h, T)), page


def test_second_rhythm_alone_does_not_draft(pl14_image, pl14_manifest):
    m = pl14_manifest
    h = NoteHarness(pl14_image)
    open_tools2(h)
    configure(h, m, k=8, c0=0, shape=1)
    pick(h, 4)                                                     # second hits, rotation: combine off, no effect
    pick(h, PAD_ROT)
    toc(h, TOOLS)
    write(h)
    assert draft_of(h, m) == 0 and hit_mask(steps(h, T)) == mm.first_rhythm(8, 0, 1, 16)


def test_page_sub_saved(pl14_image, pl14_manifest):
    """A project left on Phrasing reopens on Phrasing. (The published PL13's side went with saved format 2: PL13 reads
    only the alpha blocks; alpha policy, no cross-version checks.)"""
    from test_saved import TAIL, load, record, save, write_tail
    m = pl14_manifest
    a = NoteHarness(pl14_image)
    open_phrasing(a)
    a.press(T)                                                     # closed
    save(a)
    tail = bytes(a.uc.mem_read(record(a) + TAIL, 1000))
    a.uc.mem_write(sym(m, "page_slot") + T, b"\0")
    a.uc.mem_write(sym(m, "page_sub") + T, b"\0")
    write_tail(a, tail)
    load(a)
    a.leds()
    assert where(a, m) == (MELODY, 1)
    a.press(T, shift=True)
    assert shown(a.leds()) == "phrasing"
