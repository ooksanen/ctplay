"""The melodic generator's reference model (tests/melody_model.py): shapes the spec asks for."""
import chord_model
import melody_model


def test_seed_has_period_255():
    seen, s = set(), 1
    for _ in range(255):
        seen.add(s); s = melody_model.seed_next(s)
    assert s == 1 and len(seen) == 255 and 0 not in seen


W = [20, 3, 6, 9, 12, 3, 6, 9, 12, 3, 6, 9, 12, 3, 6, 9]          # the Global Constraints' weights, one bar


def test_groove_puts_the_downbeat_first_and_counts_k():
    for seed in range(1, 256):
        for k in range(17):
            m = melody_model.groove(k, 16, 0, seed)
            assert bin(m).count("1") == k
            if k: assert m & 1                               # step 1 always first
            for i in range(16):                              # jitter (0-4) swaps neighbouring ranks only
                if m >> i & 1:
                    assert all(m >> j & 1 for j in range(16) if W[j] >= W[i] + 6)
    m0 = melody_model.groove(3, 16, 0, 7)
    assert melody_model.groove(3, 16, 15, 7) == ((m0 << 1) | (m0 >> 15)) & 0xFFFF   # r = 15: one step later


def test_root_degrees():
    major = 0x00111044
    assert melody_model.root(0x10, 61, major) == 61               # last pad
    assert melody_model.root(1 | 2 << 3, 0, major) == 72          # degree 1, octave 0
    assert melody_model.root(5 | 0 << 3, 0, major) == 72 - 24 + 7 # degree 5, octave -2
    assert melody_model.root(3 | 2 << 3, 0, 0) == 76              # chromatic -> major: E


def test_pools():
    major = 0x00111044
    assert melody_model.pool(0x00, 72, major, chord_model.settings(0)) == ([72, 76, 79], 0, 7)        # shape off: triad
    assert melody_model.pool(0x08 | 1 << 4, 72, major, 0)[0] == [72, 74, 76, 77, 79, 81, 83, 84, 86, 88, 89, 91, 93, 95, 96]
    assert melody_model.pool(0x07, 72, major, chord_model.settings(1, bass=1)) == ([60, 72, 76, 79], 0, 7)  # bass below
    nine_bass = chord_model.settings(3, bass=1)                  # a 9th over a bass leaves out its 5th (chord_notes)
    assert 79 not in melody_model.pool(0x01, 72, major, nine_bass)[0]   # order up: the chord as it plays
    assert 79 in melody_model.pool(0x07, 72, major, nine_bass)[0]       # order bass: the fifth added back


def test_climb_and_walk_shapes():
    pool = list(range(60, 66))
    assert melody_model.line(4, 1, 16, pool, 0, 0x1FF, 7) == [60, 61, 62, 61, 62, 63, 62, 63, 64]
    w = melody_model.line(5, 9, 32, pool, 2, 0xFFFFFFFF, 7)
    assert w[0] == 62 and all(abs(pool.index(a) - pool.index(b)) <= 2 for a, b in zip(w, w[1:]))


def test_bass_starts_on_the_root_and_favours_it():
    pool, ra, fc = melody_model.pool(0x07, 60, 0x00111044, chord_model.settings(1))
    for seed in (1, 3, 200):                         # one root-class note in the pool: every quarter is the root
        notes = melody_model.line(0x07, seed, 16, pool, ra, 0xFFFF, fc)
        assert notes[0] == 60 and [notes[j] for j in (0, 4, 8, 12)] == [60] * 4
        assert set(notes) <= set(pool)


def test_accent_and_next_len():
    assert [melody_model.accent(3, j, 0) for j in range(7)] == [1, 0, 0, 1, 0, 0, 1]
    assert melody_model.next_len(0b1001, 4, 0) == 18 and melody_model.next_len(0b1001, 4, 3) == 6
    assert melody_model.next_len(0b1, 32, 0) == 96


def scale(*notes):
    """A scale mask from its notes (semitones above the project root): 2 bits per semitone, 0 = in the scale."""
    return sum(1 << (2 * n) for n in range(12) if n not in notes)


MAJOR = 0x00111044
PENTA = scale(0, 2, 4, 7, 9)                 # major pentatonic
MINOR_PENTA = scale(0, 3, 5, 7, 10)
WHOLE = scale(0, 2, 4, 6, 8, 10)
LOCRIAN = scale(0, 1, 3, 5, 6, 8, 10)


def steps(s, k):
    for _ in range(k):
        s = melody_model.seed_next(s)
    return s


def test_degree_roots_count_octaves_in_short_scales():
    oct0 = 2 << 3
    assert [melody_model.root(d | oct0, 0, PENTA) for d in range(1, 8)] == [72, 74, 76, 79, 81, 84, 86]
    assert [melody_model.root(d | oct0, 0, WHOLE) for d in range(1, 8)] == [72, 74, 76, 78, 80, 82, 84]
    assert [melody_model.root(d | oct0, 0, MAJOR) for d in range(1, 8)] == [72, 74, 76, 77, 79, 81, 83]
    assert melody_model.root(6 | 0 << 3, 0, PENTA) == 84 - 24


def test_the_scale_pool_includes_a_root_outside_the_scale():
    pl, at, _ = melody_model.pool(0x08, 66, MAJOR, 0)            # F# in C major, scale pool, range 1
    assert pl == [66, 67, 69, 71, 72, 74, 76, 77] and at == 0
    pl, at, _ = melody_model.pool(0x08, 72, MAJOR, 0)            # a root in the scale: as before
    assert pl == [72, 74, 76, 77, 79, 81, 83, 84] and at == 0


def test_the_bass_fifth():
    pl, at, fc = melody_model.pool(0x07, 72, MAJOR, chord_model.settings(1))
    assert fc == 7 and pl == [72, 76, 79]                         # the perfect fifth, in the chord already
    pl, at, fc = melody_model.pool(0x07, 72, MINOR_PENTA, chord_model.settings(1))
    assert fc == 7 and pl == [72, 77, 79, 82]                     # the triad C F Bb; G (in the scale) added, not Bb
    pl, at, fc = melody_model.pool(0x07, 72, LOCRIAN, chord_model.settings(1))
    assert fc == 6 and pl == [72, 75, 78]                         # no G in locrian: the 5th degree, Gb (in the chord)
    hits = 0xEEEE                                                 # every hit but the first off the quarters: by weight
    notes = [v for seed in range(1, 256) for v in melody_model.line(0x07, seed, 16, pl, at, hits, fc)[1:]]
    share = {v: notes.count(v) / len(notes) for v in pl}          # weights 4 : 1 : 2 (root, minor 3rd, fifth)
    assert share[78] > 1.5 * share[75] and share[72] > 1.5 * share[78], share


def test_next_len_caps_at_96():
    assert melody_model.next_len(0b1, 32, 0) == 96 and melody_model.next_len(0b1, 17, 0) == 96
    assert melody_model.next_len(0b1, 16, 0) == 96 and melody_model.next_len(0b1, 15, 0) == 90
    assert melody_model.next_len(0b11, 32, 1) == 96 and melody_model.next_len(0b11, 32, 0) == 6


def test_dice_rhythm_always_changes_the_rhythm():
    import euclid_model
    seed, rot = 1, 0
    for _ in range(200):                                          # Euclid, 8 hits in 16: rotations 8 apart are equal
        was = euclid_model.mask(8, 16, rot)
        seed, rot = melody_model.dice_rhythm(0, 8, 16, rot, seed)
        assert euclid_model.mask(8, 16, rot) != was and rot == seed % 16
    seed = 1
    for _ in range(200):                                          # groove, 5 hits: the rotation stays
        was = melody_model.groove(5, 16, 3, seed)
        seed, rot = melody_model.dice_rhythm(1, 5, 16, 3, seed)
        assert melody_model.groove(5, 16, 3, seed) != was and rot == 3
    assert melody_model.dice_rhythm(0, 4, 12, 5, 1) == (steps(1, 1), steps(1, 1) % 12)    # one step was enough
    assert melody_model.dice_rhythm(0, 0, 16, 0, 1) == (steps(1, 16), steps(1, 16) % 16)  # nothing can change:
    assert melody_model.dice_rhythm(1, 16, 16, 0, 1) == (steps(1, 16), 0)                 # the last step is kept


def test_dice_notes_always_changes_the_line():
    import euclid_model
    hits = euclid_model.mask(8, 16, 0)
    for order in (1, 3, 6, 7):                                    # up, up-down, random, bass over a triad
        pl, at, fc = melody_model.pool(order, 60, MAJOR, chord_model.settings(1))
        seed = 1
        for _ in range(100):
            was = melody_model.line(order, seed, 16, pl, at, hits, fc)
            seed = melody_model.dice_notes(order, seed, 16, pl, at, fc, hits)
            assert melody_model.line(order, seed, 16, pl, at, hits, fc) != was, (order, seed)
    assert melody_model.dice_notes(1, 1, 16, [60], 0, 7, hits) == steps(1, 16)   # a pool of one note
    assert melody_model.dice_notes(1, 1, 16, [60, 64], 0, 7, 0) == steps(1, 16)  # no hits
    assert melody_model.dice_notes(1, 1, 16, [], 0, 7, hits) == steps(1, 16)     # no pool (an unplayable root)


# --- PL14 variations ---
def test_draw_is_spread_and_salted():
    vals = [melody_model.draw(s, 1, i) for s in range(1, 256) for i in range(32)]
    assert min(vals) == 0 and max(vals) == 255
    for q in range(4):
        share = sum(1 for v in vals if q * 64 <= v < q * 64 + 64) / len(vals)
        assert 0.20 <= share <= 0.30, (q, share)
    differ = sum(melody_model.draw(s, 1, i) != melody_model.draw(s, 2, i) for s in range(1, 256) for i in range(32))
    assert differ >= 0.95 * 255 * 32


def test_repeat():
    assert melody_model.repeat(0b101, 3, 16) == 0b1101101101101101      # bit i = base bit (i % 3)
    for m in (0, 0b1011, 0xFFFF):
        assert melody_model.repeat(m, 0, 16) == m
        assert melody_model.repeat(m, 7, 4) == m


def test_combine():
    a, b = 0b1111_0000, 0b1010_1010
    for mode, want in ((1, 0b1010_0000), (2, 0b1111_1010), (3, 0b0101_1010), (4, 0b0101_0000), (5, a)):
        assert melody_model.combine(a, b, mode) == want, mode


def test_thin_keeps_the_lowest_hit_and_scales():
    for amount, frac in ((1, 0.25), (2, 1 / 3), (3, 0.5)):
        dropped = 0
        for seed in range(1, 256):
            t = melody_model.thin(0xFFFF, amount, seed)
            assert t & 1 and t & ~0xFFFF == 0
            dropped += 16 - bin(t).count("1")
        assert abs(dropped / 255 / 16 - frac * 15 / 16) <= 0.05, amount
    for seed in range(1, 256):
        assert melody_model.thin(0xFFFF, 0, seed) == 0xFFFF


def test_ties_and_jumps_never_take_the_lowest_hit():
    for seed in range(1, 256):
        for amount in range(4):
            for h in (0xFFFF, 0xF0F0, 0x8001, 1):
                for f in (melody_model.ties, melody_model.jumps):
                    got = f(h, amount, seed)
                    assert got & h == got and not got & (h & -h)
        assert melody_model.ties(0xFFFF, 0, seed) == 0


def test_streams_are_independent():
    for seed in range(1, 256):
        th = melody_model.thin(0xFFFF, 2, seed)
        for amount in range(4):
            t = melody_model.ties(th, amount, seed)
            assert melody_model.thin(0xFFFF, 2, seed) == th        # the tie amount cannot move the thinning
            struck = th & ~t
            assert melody_model.jumps(struck, 3, seed) == melody_model.jumps(th, 3, seed) & struck   # keyed by step


def test_jump_range():
    j = melody_model.jump
    assert j(60, 0) == 72 and j(130, 0) == 118
    assert j(116, 11) == 128 and j(117, 11) == 105 and j(129, 11) == 117
    for key in range(12):
        for note in range(140):
            assert j(note, key) != note


def test_tables():
    assert [melody_model.cycle_len(c) for c in range(5)] == [0, 3, 5, 6, 7]
    assert [melody_model.amount_limit(a) for a in range(4)] == [0, 64, 85, 128]
