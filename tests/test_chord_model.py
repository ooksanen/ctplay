"""The chord model against the spec's worked examples (C natural minor, as in the RAM dump; pitch 48 = the root)."""
from chord_model import chord_notes, settings

MINOR = 0x00441108              # the dump's scale: C D Eb F G Ab Bb


def test_shapes():
    assert chord_notes(48, MINOR, settings(0)) == []
    assert chord_notes(48, MINOR, settings(1)) == [51, 55]                  # Cm
    assert chord_notes(48, MINOR, settings(2)) == [51, 55, 58]              # Cm7
    assert chord_notes(48, MINOR, settings(3)) == [51, 55, 58, 62]          # Cm9
    assert chord_notes(48, MINOR, settings(4)) == [50, 55]                  # Csus2
    assert chord_notes(48, MINOR, settings(5)) == [53, 55]                  # Csus4
    assert chord_notes(48, MINOR, settings(6)) == [51, 55, 62]              # Cm add9
    assert chord_notes(48, MINOR, settings(7)) == [51, 55, 56]              # C, Eb, G, Ab
    assert chord_notes(58, MINOR, settings(1)) == [62, 65]                  # Bb triad across the octave: Bb D F


def test_inversions_move_the_upper_notes_down():
    assert chord_notes(48, MINOR, settings(1, inv=1)) == [39, 43]           # Eb G | C
    assert chord_notes(48, MINOR, settings(1, inv=2)) == [51, 43]           # G | C Eb
    assert chord_notes(48, MINOR, settings(2, inv=3)) == [51, 55, 46]       # Bb | C Eb G
    assert chord_notes(48, MINOR, settings(1, inv=3)) == [51, 55]           # inversion >= tones: as inversion 0


def test_spread():
    assert chord_notes(48, MINOR, settings(2, spread=1)) == [51, 43, 58]    # drop-2: G down
    assert chord_notes(48, MINOR, settings(1, inv=2, spread=1)) == [51, 31] # root second-highest: the G below moves
    assert chord_notes(48, MINOR, settings(4, spread=1)) == [38, 55]        # sus2, 3 tones: D (second-highest) drops
    assert chord_notes(48, MINOR, settings(2, spread=2)) == [63, 55, 70]    # wide: tones 1 and 3 up
    assert chord_notes(48, MINOR, settings(1, spread=3)) == [51, 55]        # unused value: close


def test_bass_and_limits():
    assert chord_notes(48, MINOR, settings(1, bass=1)) == [51, 55, 36]
    assert chord_notes(48, MINOR, settings(2, bass=1)) == [51, 55, 58, 36]       # 5 notes with the root: all kept
    assert chord_notes(48, MINOR, settings(6, bass=1)) == [51, 55, 62, 36]       # add9 + bass: 5 notes, all kept
    assert chord_notes(48, MINOR, settings(3, bass=1)) == [51, 58, 62, 36]       # 9th + bass: the 5th (G) left out
    assert chord_notes(48, MINOR, settings(3, inv=2, bass=1)) == [51, 46, 50, 36]   # with an inversion too
    assert chord_notes(17, MINOR, settings(1, bass=1)) == chord_notes(17, MINOR, settings(1))   # bass unplayable: dropped
    assert chord_notes(17, MINOR, settings(1, bass=1, key=7))[-1] == 5          # with key 7, 5 + 7 = 12 plays
    assert all(12 <= v <= 139 for v in chord_notes(130, MINOR, settings(3)))    # stock's range: pitch + key 12-139
    assert all(v + 5 <= 139 for v in chord_notes(130, MINOR, settings(3, key=5)))


def test_chromatic_uses_the_major_scale():
    assert chord_notes(48, 0, settings(1)) == [52, 55]                      # C E G
    assert chord_notes(50, 0, settings(1)) == [53, 57]                      # D F A
    assert chord_notes(49, 0, settings(1)) == [52, 55]                      # C#: walks to E, G


def test_pentatonic_root_duplicate_is_dropped():
    minor_penta = sum(1 << 2 * n for n in range(12) if n not in (0, 3, 5, 7, 10))
    assert 48 not in chord_notes(48, minor_penta, settings(7, inv=3))       # degree 5 = the octave, moved down = root


def test_rootless_over_bass():
    """The pad is the bass; the chord sits an octave up without its root (and without the bass below)."""
    assert chord_notes(48, MINOR, settings(1, bass=1, rootless=1)) == [63, 67]              # Eb G over C
    assert chord_notes(48, MINOR, settings(3, bass=1, rootless=1)) == [63, 67, 70, 74]      # Cm9: 5 notes
    assert chord_notes(48, MINOR, settings(1, inv=1, bass=1, rootless=1)) == [51, 55]       # upper chord inverted
    assert chord_notes(48, MINOR, settings(0, bass=1, rootless=1)) == []                    # single: the pad only
    assert chord_notes(48, MINOR, settings(2, rootless=1)) == chord_notes(48, MINOR, settings(2))   # needs bass on


def test_rootless_never_doubles_the_root():
    minor_penta = sum(1 << 2 * n for n in range(12) if n not in (0, 3, 5, 7, 10))
    for s in (settings(7, inv=i, spread=sp, bass=1, rootless=1) for i in range(4) for sp in range(3)):
        notes = chord_notes(48, minor_penta, s)
        assert all((v - 48) % 12 for v in notes), (hex(s), notes)       # no C in any octave: the pad is the only one


def test_the_bass_is_always_the_lowest_note():
    """Inversion + drop-2 can lower a tone twice: in both bass modes it is raised by octaves back above the bass."""
    assert chord_notes(48, MINOR, settings(1, inv=2, spread=1, bass=1, rootless=1)) == [63, 55]   # G back above C
    assert chord_notes(48, MINOR, settings(1, inv=2, spread=1, bass=1)) == [51, 43, 36]           # G above the bass
    for sh in range(8):
        for inv in range(4):
            for sp in range(3):
                assert all(v > 48 for v in chord_notes(48, MINOR, settings(sh, inv, sp, bass=1, rootless=1)))
                notes = chord_notes(48, MINOR, settings(sh, inv, sp, bass=1))
                assert all(v > 36 for v in notes if v != 36), (sh, inv, sp, notes)


def test_the_fifth_stays_when_the_bass_is_out_of_range():
    assert chord_notes(5, MINOR, settings(3, bass=1)) == chord_notes(5, MINOR, settings(3))    # no bass below 0


# --- PL15: five more shapes, voice leading ---
import random

from chord_model import lead, shape_index

MAJOR = 0        # mask 0 = Chromatic, which uses the major scale


def chord_notes_pl14(root, mask, s):
    """PL14's chord_notes, copied before PL15 touched the model: the row-1 shapes must not change."""
    import chord_model as m
    shape, inv, spread, bass = m.SHAPES[s & 7], (s >> 3) & 3, (s >> 5) & 3, (s >> 7) & 1
    key = (s >> 16) & 0xFF
    rootless = bass and (s >> 8) & 1
    if mask == 0:
        mask = m.MAJOR_MASK
    tones = [m.degrees_up(mask, root, d) for d in shape]
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
        tones = [root] + [m.lift(v + 12, root) for v in tones[1:] if (v - root) % 12]
    elif bass:
        if n >= 5 and m.playable(root - 12, key):
            tones = [v for d, v in zip(shape, tones) if d != 4]
        tones = [root] + [m.lift(v, root - 12) for v in tones[1:]] + [root - 12]
    out = []
    for v in tones[1:]:
        if m.playable(v, key) and v != root and v not in out and len(out) < 4:
            out.append(v)
    return out


def test_new_shapes_in_c_major():
    assert chord_notes(60, MAJOR, settings(0, shape2=1)) == [67, 72]                 # power
    assert chord_notes(60, MAJOR, settings(0, shape2=2)) == [64, 71]                 # shell 7
    assert chord_notes(62, MAJOR, settings(0, shape2=3)) == [67, 72, 77]             # quartal on D
    assert chord_notes(67, MAJOR, settings(0, shape2=4)) == [72, 74, 77]             # 7sus4 on G
    assert sorted(chord_notes(60, MAJOR, settings(0, shape2=5))) == [64, 67, 69, 74]  # 6/9


def test_row1_wins_over_row2():
    assert chord_notes(60, 0, settings(2, shape2=1)) == chord_notes(60, 0, settings(2))
    assert shape_index(settings(2, shape2=1)) == 2 and shape_index(settings(0, shape2=5)) == 12
    assert shape_index(settings(0, shape2=6)) == 0                                  # unused value: single


def test_row1_shapes_unchanged():
    for shape in range(8):
        for inv in range(4):
            for spread in range(3):
                for bass, rootless in ((0, 0), (1, 0), (1, 1)):
                    for root in range(30, 101):
                        s = settings(shape, inv, spread, bass, rootless)
                        assert chord_notes(root, 0, s) == chord_notes_pl14(root, 0, s), (shape, inv, spread, bass, root)


def test_lead_close():
    s = settings(1)
    assert lead(65, 0, s, [60, 64, 67], 1) == 2


def test_lead_top_line_differs():
    s, prev = settings(2), [60, 64, 67, 71]
    assert lead(62, 0, s, prev, 1) == 3
    assert lead(62, 0, s, prev, 2) == 0


def test_lead_bottom_line_differs():
    s, prev = settings(1), [60, 64, 67, 71]
    assert lead(64, 0, s, prev, 1) == 0
    assert lead(64, 0, s, prev, 3) == 2


def test_lead_full_candidates_only():
    assert lead(60, 0, settings(0, shape2=1), [60, 67, 72], 1) == 0
    key = 11                                     # a pad near the top: the low inversions lose their top note
    s = settings(2, key=key)
    root = 139 - key - 2
    counts = {}
    for inv in range(4):
        counts[inv] = len(chord_notes(root, 0, settings(2, inv=inv, key=key)))
    assert len(set(counts.values())) > 1, counts           # the premise: the candidates differ in size
    got = lead(root, 0, s, [root - 5, root - 1], 1)
    assert counts[got] == max(counts.values())


def test_lead_stays_near_the_pad():
    rng = random.Random(15)
    for _ in range(200):
        root = rng.randint(48, 84)
        spread, rootless = rng.randint(0, 2), rng.randint(0, 1)
        s = settings(rng.randint(0, 12), rng.randint(0, 3), spread, rng.randint(0, 1), rootless)
        prev = [rng.randint(40, 100) for _ in range(rng.randint(1, 5))]
        for kind in (1, 2, 3):
            inv = lead(root, 0, s, prev, kind)
            assert 0 <= inv <= 3
            for v in chord_notes(root, 0, s & ~(3 << 3) | inv << 3):
                # rootless over bass lifts every tone an octave or a wide spread lifts a tone (a 9th reaches +26): chord_notes' own reach
                assert root - 24 <= v <= root + (36 if spread == 2 or rootless and (s >> 7) & 1 else 24), (root, hex(s), inv, v)


def test_lead_without_previous_uses_the_stored_inversion():
    for inv in range(4):
        for kind in (1, 2, 3):
            assert lead(60, 0, settings(2, inv=inv), [], kind) == inv
