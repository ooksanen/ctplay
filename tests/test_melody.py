"""The melodic generator's maths (PL13, features/chord/melody_math.c) in emulation against tests/melody_model.py. Pure
functions called directly: the pool struct is written raw at OUTBUF, the line at OUTBUF + 0x40."""
import pytest
from unicorn.arm_const import UC_ARM_REG_R0

import chord_model
import melody_model
from harness import Harness
from notes import OUTBUF

pytestmark = pytest.mark.emu
MAJOR = 0x00111044
MINOR = sum(1 << (2 * n) for n in range(12) if n not in (0, 2, 3, 5, 7, 8, 10))   # natural minor
PENTA = sum(1 << (2 * n) for n in range(12) if n not in (0, 2, 4, 7, 9))          # major pentatonic: 5 notes
MINOR_PENTA = sum(1 << (2 * n) for n in range(12) if n not in (0, 3, 5, 7, 10))
WHOLE = sum(1 << (2 * n) for n in range(12) if n not in (0, 2, 4, 6, 8, 10))       # whole tone: 6 notes
LOCRIAN = sum(1 << (2 * n) for n in range(12) if n not in (0, 1, 3, 5, 6, 8, 10))  # no perfect fifth
FIFTH = 5 + 24                                     # melody_pool_t: the fifth's pitch class after pool[]
LINE = OUTBUF + 0x40


def sym(m, name):
    return int(m["symbols"][name], 16)


def call(h, m, name, *args):
    h.call(sym(m, name), *args)
    return h.uc.reg_read(UC_ARM_REG_R0)


def test_seed_and_groove_match_the_model(pl13_image, pl13_manifest):
    h = Harness(pl13_image)
    for s in range(1, 256):
        assert call(h, pl13_manifest, "melody_seed_next", s) == melody_model.seed_next(s), s
    fn = sym(pl13_manifest, "melody_groove")
    for n in range(1, 33):
        for k in range(n + 2):
            for r in sorted({0, 1, n - 1}):
                for seed in (1, 77, 255):
                    h.call(fn, k, n, r, seed)
                    got = h.uc.reg_read(UC_ARM_REG_R0)
                    assert got == melody_model.groove(k, n, r, seed), (k, n, r, seed)


def test_root_matches_the_model(pl13_image, pl13_manifest):
    h = Harness(pl13_image)
    for root in range(8):
        for octv in range(4):
            for last in (48, 61, 95):
                for mask in (MAJOR, MINOR, 0, PENTA, WHOLE):
                    cfg1 = root | octv << 3
                    got = call(h, pl13_manifest, "melody_root", cfg1, last, mask)
                    assert got == melody_model.root(cfg1, last, mask), (cfg1, last, hex(mask))


CHORD_SETTINGS = [chord_model.settings(0), chord_model.settings(1), chord_model.settings(2),
                  chord_model.settings(3, bass=1), chord_model.settings(1, bass=1, rootless=1),
                  chord_model.settings(2, inv=1, spread=1)]


def read_pool(h):
    pn, at = h.uc.mem_read(OUTBUF + 3, 2)
    return list(h.uc.mem_read(OUTBUF + 5, pn)), at, h.uc.mem_read(OUTBUF + FIFTH, 1)[0]


def test_pool_matches_the_model(pl13_image, pl13_manifest):
    h = Harness(pl13_image)
    fn = sym(pl13_manifest, "melody_pool")
    bad = []
    for pool_kind in (0, 1):
        for rng in range(3):
            for order in (1, 7):
                cfg0 = order | pool_kind << 3 | rng << 4
                for root in range(48, 96, 5):
                    for key in (0, 11):
                        for mask in (MAJOR, MINOR, 0, MINOR_PENTA, LOCRIAN):
                            for st in CHORD_SETTINGS:
                                s = st | key << 16
                                h.uc.mem_write(OUTBUF, bytes([cfg0, 1, 16, 0, 0]) + bytes(24) + b"\xEE")
                                h.call(fn, OUTBUF, root, mask, s)
                                got = read_pool(h)
                                want = melody_model.pool(cfg0, root, mask, s)
                                if got != want:
                                    bad.append((hex(cfg0), root, hex(mask), hex(s), got, want))
    assert not bad, f"{len(bad)} mismatches, first: {bad[:3]}"


def test_line_matches_the_model_for_every_pool_size(pl13_image, pl13_manifest):
    h = Harness(pl13_image)
    fn = sym(pl13_manifest, "melody_line")
    bad = []
    for pn in range(1, 25):
        pool = [40 + 3 * i + i % 2 for i in range(pn)]
        for root_at in sorted({0, pn // 2, pn - 1}):
            for order in range(1, 8):
                fc = pool[(root_at + 2) % pn] % 12           # the fifth: a class in the pool (weight 2)
                for seed in (1, 2, 200):
                    for n, hits in ((16, 0xFFFFFFFF), (16, 0x8A51), (32, 0xFFFFFFFF), (32, 0x9249A5C3)):
                        h.uc.mem_write(OUTBUF, bytes([order, seed, n, pn, root_at]) + bytes(pool) + bytes(24 - pn)
                                       + bytes([fc]))
                        h.uc.mem_write(LINE, bytes(40))
                        h.call(fn, OUTBUF, hits, LINE)
                        cnt = h.uc.reg_read(UC_ARM_REG_R0)
                        got = list(h.uc.mem_read(LINE, cnt))
                        want = melody_model.line(order, seed, n, pool, root_at, hits, fc)
                        if got != want:
                            bad.append((pn, root_at, order, seed, n, hex(hits), got, want))
    assert not bad, f"{len(bad)} mismatches, first: {bad[:3]}"


def test_order_same_counts_and_writes_nothing(pl13_image, pl13_manifest):
    h = Harness(pl13_image)
    h.uc.mem_write(OUTBUF, bytes([0, 1, 16, 3, 0, 60, 64, 67]) + bytes(21))
    h.uc.mem_write(LINE, bytes([0xEE] * 8))
    assert call(h, pl13_manifest, "melody_line", OUTBUF, 0x1111 | 0xF0000, LINE) == 4   # bits above n do not count
    assert bytes(h.uc.mem_read(LINE, 8)) == bytes([0xEE] * 8)


def test_accent_and_next_len_match_the_model(pl13_image, pl13_manifest):
    h = Harness(pl13_image)
    for a in range(4):
        for j in range(7):
            for i in range(9):
                assert call(h, pl13_manifest, "melody_accent", a, j, i) == melody_model.accent(a, j, i)
    for n in (1, 4, 16, 17, 32):
        for hits in (1, 0b1001, 0x8000, 0x80000001, 0xFFFFFFFF, 0x10001):
            hits &= 0xFFFFFFFF if n == 32 else (1 << n) - 1
            if not hits:
                continue
            for i in range(n):
                got = call(h, pl13_manifest, "melody_next_len", hits, n, i)
                assert got == melody_model.next_len(hits, n, i), (hits, n, i)


# ---- The Melody page and the new Pattern tools pads (Task 2) ----

from notes import NoteHarness   # noqa: E402
from test_euclid import expected as euclid_preview, open_tools, pick, preview, set_range   # noqa: E402
import euclid_model   # noqa: E402

MELODY = 3
RGB_TABLE = 0x20003804                      # 4 bytes per code: B, G, R, 0
ANIMATED = {0x03, 0x04, 0x05, 0x06, 0x10, 0x11, 0x15, 0x16, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x27, 0x28, 0x2F, 0x30, 0x39,
            0x3A, 0x42, 0x43, 0x47, 0x48, 0x4B, 0x4C, 0x4F, 0x50, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x5B, 0x61, 0x62}
YELLOW, YELLOW_D, WHITE, WHITE_D = 0x2D, 0x2E, 0x01, 0x02
GREEN, GREEN_D, BLUE, BLUE_D, MAG, MAG_D, ORANGE, ORANGE_D = 0x17, 0x18, 0x07, 0x08, 0x32, 0x38, 0x45, 0x46


def open_melody(h, t):
    h.leds()
    h.track(t)
    h.press(t, shift=True)
    h.shift(True)
    pick(h, 24)                               # Chords first: from PL14 the open feature's pad flips its two pages
    pick(h, 24 + MELODY)                      # the table of contents: pad 28 (its page used last)
    h.shift(False)


def mcfg(h, m, t):
    return tuple(h.uc.mem_read(sym(m, "melody_cfg") + 2 * t, 2))


def mseed(h, m, t):
    return tuple(h.uc.mem_read(sym(m, "melody_seed") + 2 * t, 2))


def ecfg(h, m, t):
    return tuple(h.uc.mem_read(sym(m, "euclid_cfg") + 2 * t, 2))


def test_yellow_codes_are_steady_and_yellow(pl13_image):
    h = NoteHarness(pl13_image)
    h.leds()
    rgb = {}
    for code in (YELLOW, YELLOW_D):
        b, g, r, _ = h.uc.mem_read(RGB_TABLE + 4 * code, 4)
        rgb[code] = (r, g, b)
        assert r > 4 * b and g > 4 * b and abs(r - g) <= 16, (hex(code), r, g, b)
        assert code not in ANIMATED
    assert sum(rgb[YELLOW_D]) < sum(rgb[YELLOW]) / 3


def test_table_of_contents_and_paging(pl13_image, pl13_manifest):
    h = NoteHarness(pl13_image)
    h.track(0)
    h.press(0, shift=True)
    h.shift(True)
    assert h.leds()[24:32] == [GREEN, BLUE_D, ORANGE_D, YELLOW_D, 0, 0, 0, MAG_D]
    pick(h, 27)
    assert h.r8(sym(pl13_manifest, "page_slot")) == MELODY
    assert h.leds()[24:32] == [GREEN_D, BLUE_D, ORANGE_D, YELLOW, 0, 0, 0, MAG_D]
    h.shift(False)
    leds = h.leds()
    assert (leds[51], leds[52]) == (YELLOW, ORANGE)          # Phrasing after it (PL14), Pattern tools 2 before
    h.press(19)                                              # ▼: Phrasing
    assert h.r8(sym(pl13_manifest, "page_slot")) == MELODY and h.leds()[51] == MAG   # Keys after it
    h.press(19)
    assert h.r8(sym(pl13_manifest, "page_slot")) == 7 and h.leds()[51] == 0
    h.press(20)
    assert h.r8(sym(pl13_manifest, "page_slot")) == MELODY
    h.press(20)
    h.press(20)                                              # ▲ twice: Phrasing, Melody, then Pattern tools 2
    assert h.r8(sym(pl13_manifest, "page_slot")) == 2
    h.press(19)                                              # ▼ from Pattern tools 2: Melody, not Keys
    assert h.r8(sym(pl13_manifest, "page_slot")) == MELODY


def test_melody_page_leds_before_any_pick(pl13_image, pl13_manifest):
    h = NoteHarness(pl13_image)
    open_melody(h, 2)
    leds = h.leds()
    assert leds[:8] == [YELLOW] + [YELLOW_D] * 7
    assert leds[8:16] == [GREEN, GREEN_D, MAG, MAG_D, MAG_D, YELLOW_D, 0, 0]
    assert leds[16:24] == [WHITE] + [BLUE_D] * 7
    assert leds[24:28] == [MAG_D] * 4
    assert leds[28:32] == [WHITE_D, 0, 0, 0]
    assert mcfg(h, pl13_manifest, 2) == (0x00, 0x10) and mseed(h, pl13_manifest, 2) == (1, 1)


def test_melody_picks_set_the_bytes(pl13_image, pl13_manifest):
    h = NoteHarness(pl13_image)
    open_melody(h, 2)
    for pad in (6, 9, 12, 13, 13):
        pick(h, pad)
    assert mcfg(h, pl13_manifest, 2)[0] == 6 | 8 | 2 << 4 | 2 << 6
    leds = h.leds()
    assert leds[:8] == [YELLOW_D] * 6 + [YELLOW, YELLOW_D] and leds[8:10] == [GREEN_D, GREEN]
    assert leds[10:13] == [MAG_D, MAG_D, MAG] and leds[13] == WHITE
    pick(h, 21)                                               # degree 5
    assert mcfg(h, pl13_manifest, 2)[1] == 5 | 2 << 3
    assert h.leds()[16:24] == [WHITE_D, BLUE_D, BLUE_D, BLUE_D, BLUE_D, BLUE, BLUE_D, BLUE_D]
    assert h.leds()[24:28] == [MAG_D, MAG_D, MAG, MAG_D]
    pick(h, 24)                                               # octave -2
    assert mcfg(h, pl13_manifest, 2)[1] == 5 | 0 << 3 and h.leds()[24:28] == [MAG, MAG_D, MAG_D, MAG_D]
    pick(h, 16)                                               # root: the last pad
    assert mcfg(h, pl13_manifest, 2)[1] == 0
    assert h.leds()[24:28] == [MAG_D] * 4
    pick(h, 25)                                               # ignored while the root is the last pad
    assert mcfg(h, pl13_manifest, 2)[1] == 0
    pick(h, 13)
    assert mcfg(h, pl13_manifest, 2)[0] >> 6 == 3 and h.leds()[13] == MAG
    pick(h, 13)
    assert mcfg(h, pl13_manifest, 2)[0] >> 6 == 0 and h.leds()[13] == YELLOW_D
    for t in (0, 1, 3):
        assert mcfg(h, pl13_manifest, t) == (0x00, 0x10)


def seed_steps(s, k):
    for _ in range(k):
        s = melody_model.seed_next(s)
    return s


def test_dice(pl13_image, pl13_manifest):
    h = NoteHarness(pl13_image)
    open_melody(h, 2)
    pick(h, 29)                                               # order same: dice notes dark, ignored
    assert h.leds()[29] == 0 and mseed(h, pl13_manifest, 2) == (1, 1)
    pick(h, 1)                                                # up
    assert h.leds()[29] == WHITE_D
    pick(h, 29)                                               # no hits: no line can change, 16 steps
    assert mseed(h, pl13_manifest, 2) == (1, seed_steps(1, 16))
    pick(h, 28)                                               # Euclid, no hits: n = 16 steps, rotation = seed % n
    s = seed_steps(1, 16)
    assert mseed(h, pl13_manifest, 2)[0] == s and ecfg(h, pl13_manifest, 2)[1] & 0x1F == s % 16
    h.press(20)
    h.press(20)                                               # ▲ to Pattern tools (through its page 2, PL14)
    pick(h, 4)
    assert preview(h) == euclid_preview(euclid_model.mask(5, 16, s % 16), 16)
    set_range(h, 2, 0, 11)                                    # 12 steps: the rotation is seed % 12
    pick(h, 28)
    s2, r = melody_model.dice_rhythm(0, 5, 12, s % 16, s)
    assert mseed(h, pl13_manifest, 2)[0] == s2 and ecfg(h, pl13_manifest, 2)[1] & 0x1F == r == s2 % 12
    pick(h, 19)                                               # groove: the seed only
    pick(h, 28)
    s3, _ = melody_model.dice_rhythm(1, 5, 12, r, s2)
    assert mseed(h, pl13_manifest, 2)[0] == s3 and ecfg(h, pl13_manifest, 2)[1] & 0x1F == r
    assert preview(h) == euclid_preview(melody_model.groove(5, 12, r % 12, s3), 12)
    notes = mseed(h, pl13_manifest, 2)[1]
    pick(h, 29)                                               # also on Pattern tools
    assert mseed(h, pl13_manifest, 2)[1] != notes


def test_every_dice_rhythm_press_changes_the_rhythm(pl13_image, pl13_manifest):
    """From the default seed: Euclid 8 in 16 (rotations 8 apart are the same rhythm) and groove with 5 hits (seeds 92
    and 46 give the same groove): each press shows another rhythm."""
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    pick(h, 7)
    seed, rot = 1, 0
    for _ in range(24):
        was = preview(h)
        pick(h, 28)
        seed, rot = melody_model.dice_rhythm(0, 8, 16, rot, seed)
        assert mseed(h, m, T)[0] == seed and ecfg(h, m, T)[1] & 0x1F == rot
        assert preview(h) == euclid_preview(euclid_model.mask(8, 16, rot), 16) != was
    h.uc.mem_write(sym(m, "melody_seed") + 2 * T, bytes([1, 1]))
    pick(h, 19)                                               # groove
    pick(h, 4)                                                # 5 hits
    seed = 1
    for _ in range(24):
        was = preview(h)
        pick(h, 28)
        seed, _ = melody_model.dice_rhythm(1, 5, 16, rot, seed)
        assert mseed(h, m, T)[0] == seed and ecfg(h, m, T)[1] & 0x1F == rot
        assert preview(h) == euclid_preview(melody_model.groove(5, 16, rot, seed), 16) != was


@pytest.mark.parametrize("order", [1, 6])                  # up (over a triad: every third seed the same line), random
def test_every_dice_notes_press_changes_the_line(pl13_image, pl13_manifest, order):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    configure(h, m, k=8, c0=order, shape=1)
    write(h)                                                  # a draft: each press writes
    assert draft_of(h, m) == T + 1
    seed = 1
    for _ in range(16):
        was = steps(h, T)
        pick(h, 29)
        seed = rolled(h, order, seed)
        assert mseed(h, m, T)[1] == seed
        assert steps(h, T) == line_steps(h, order, seed) != was


def test_tools_source_and_gate_pads(pl13_image, pl13_manifest):
    h = NoteHarness(pl13_image)
    open_tools(h, 1)
    assert h.leds()[19] == WHITE_D and h.leds()[28] == WHITE_D and h.leds()[29] == 0
    pick(h, 4)
    pick(h, 19)
    c0 = ecfg(h, pl13_manifest, 1)[0]
    assert h.leds()[19] == WHITE and c0 & 0x80 and c0 & 0x1F == 5
    assert preview(h) == euclid_preview(melody_model.groove(5, 16, 0, 1), 16)
    for pad in (16, 17, 18):                                  # rotate pads keep the groove bit
        pick(h, pad)
        assert ecfg(h, pl13_manifest, 1)[0] & 0x80
    for pad in (21, 22, 23):                                  # velocity keeps it too
        pick(h, pad)
        assert ecfg(h, pl13_manifest, 1)[0] & 0x80
    pick(h, 19)
    assert h.leds()[19] == WHITE_D and not ecfg(h, pl13_manifest, 1)[0] & 0x80
    assert h.leds()[20] == 0x66
    for colour, g in ((0x67, 1), (0x68, 0), (0x01, 6), (0x63, 5)):
        pick(h, 20)
        assert h.leds()[20] == colour and ecfg(h, pl13_manifest, 1)[1] >> 5 == g
    pick(h, 20)                                               # 6/6 -> 5/6
    assert h.leds()[20] == 0x64


def test_other_pads_disarm_a_write_on_both_pages(pl13_image, pl13_manifest):
    h = NoteHarness(pl13_image)
    open_tools(h, 2)
    pick(h, 4)
    for pad in (19, 28, 29):
        pick(h, 31)
        assert h.leds()[31] == 0x47
        pick(h, pad)
        assert h.leds()[31] == ORANGE_D
    h.press(19)                                               # ▼: Melody
    for pad in (3, 28, 29, 16, 30):
        pick(h, 31)
        assert h.leds()[31] == 0x47
        pick(h, pad)
        assert h.leds()[31] == ORANGE_D
    pick(h, 31)
    assert h.leds()[31] == 0x47                               # shared: Write arms from the Melody page too


def test_pattern_tools_without_new_settings_is_pl11(pl13_image, pl13_manifest):
    """With every melody default each pad is PL11's (the euclid tests' LED rules), the new controls aside: 19 (0x02),
    28 (0x02), and 29 dark (order same). The pl11_* fixtures build the current sources, so this is spelled out."""
    h = NoteHarness(pl13_image)
    open_tools(h, 2)
    for pad in (4, 17, 17, 21, 20, 23, 31):       # 5 hits, rotated twice, soft, gate 2/6, hard, Write armed
        pick(h, pad)
    leds = h.leds()[:32]
    assert leds[:16] == euclid_preview(euclid_model.mask(5, 16, 14), 16)
    assert leds[16:19] == [WHITE_D] * 3 and leds[19] == WHITE_D
    assert leds[20:24] == [0x67, MAG_D, MAG_D, MAG]
    assert leds[24:28] == [0x4E] * 4 and leds[28:31] == [WHITE_D, 0, 0] and leds[31] == 0x47   # 24-27: no cycle (PL14)
    assert mcfg(h, pl13_manifest, 2) == (0x00, 0x10) and ecfg(h, pl13_manifest, 2)[0] == 5 | 2 << 5


# ---- The melodic Write (Task 4) ----

from chord_model import chord_notes, settings as chord_settings_word   # noqa: E402
from notes import ROOT, SCALE_MASK, TEMPO_STORE, param   # noqa: E402
from test_euclid import EMPTY, VELOCITY, expected_steps, open_tools, steps, write   # noqa: E402

T = 2                                          # MIDI 1


def configure(h, m, k=8, e0=None, gate=2, rot=0, c0=0, c1=0x10, last=60, shape=0, seed=(1, 1), t=T):
    """Set track t's settings straight in RAM (the pads' own bytes), after the page is open."""
    e0 = k | 1 << 5 if e0 is None else e0
    h.uc.mem_write(sym(m, "euclid_cfg") + 2 * t, bytes([e0, rot | gate << 5]))
    h.uc.mem_write(sym(m, "melody_cfg") + 2 * t, bytes([c0, c1]))
    h.uc.mem_write(sym(m, "melody_seed") + 2 * t, bytes(seed))
    h.uc.mem_write(sym(m, "euclid_last") + t, bytes([last]))
    h.uc.mem_write(sym(m, "chord_settings") + t, bytes([shape]))


def hit_steps(hits, n=16):
    return [i for i in range(n) if hits >> i & 1]


def units_steps(hits, units, n=16, first=0):
    """The 32 steps for `units`: a list per hit of (note, sixths, velocity)."""
    out, j = b"", 0
    for s in range(32):
        i = s - first
        if 0 <= i < n and hits >> i & 1:
            u = units[j]
            j += 1
            body = b"".join(bytes([nt, ln, 0, v]) for nt, ln, v in u)
            out += bytes([(1 << len(u)) - 1, 7, 0, 0]) + body + bytes([0, 0, 0, 0x60]) * (6 - len(u))
        else:
            out += EMPTY
    return out


def test_plain_euclid_writes_pl11_bytes(pl13_image, pl13_manifest):
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    for k in (1, 5, 16):
        for shape in (0, 1):
            for gate in range(6):
                for v in range(3):
                    configure(h, pl13_manifest, k=k, e0=k | v << 5, gate=gate, last=64, shape=shape)
                    write(h)
                    notes = [64] + (chord_notes(64, h.r32(SCALE_MASK), chord_settings_word(shape, key=h.r8(ROOT)))
                                    if shape else [])
                    want = expected_steps(euclid_model.mask(k, 16, 0), 16, 0, notes, gate, VELOCITY[v])
                    assert steps(h, T) == want, (k, shape, gate, v)


def test_each_order_writes_its_line(pl13_image, pl13_manifest):
    h = NoteHarness(pl13_image)
    h.leds()
    h.track(T)
    root = h.pitch(T, 24)
    open_tools(h, T)
    hits = euclid_model.mask(8, 16, 0)
    for pool_kind in (0, 1):
        for order in range(1, 8):
            for seed in (1, 37):
                c0 = order | pool_kind << 3 | 1 << 4
                configure(h, pl13_manifest, k=8, c0=c0, last=root, shape=1, seed=(1, seed))
                write(h)
                pl, at, fc = melody_model.pool(c0, root, h.r32(SCALE_MASK), 1 | h.r8(ROOT) << 16)
                line = melody_model.line(c0, seed, 16, pl, at, hits, fc)
                assert steps(h, T) == units_steps(hits, [[(nt, 3, 96)] for nt in line]), (pool_kind, order, seed)


def test_groove_write(pl13_image, pl13_manifest):
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    for rot in (0, 3):
        configure(h, pl13_manifest, k=5, e0=5 | 0x80 | 1 << 5, rot=rot, seed=(9, 1))
        write(h)
        hits = melody_model.groove(5, 16, rot, 9)
        assert bin(hits).count("1") == 5
        assert steps(h, T) == expected_steps(hits, 16, 0, [60], 2, 96)


def test_degree_root_and_octave(pl13_image, pl13_manifest):
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    for degree, octave in ((4, -1), (1, 0), (7, 1)):
        c1 = degree | (octave + 2) << 3
        configure(h, pl13_manifest, k=4, c1=c1, last=60, shape=1)
        write(h)
        mask = h.r32(SCALE_MASK)
        root = melody_model.root(c1, 60, mask)
        assert root != 60 or (degree, octave) == (1, 0)
        notes = [root] + chord_notes(root, mask, chord_settings_word(1, key=h.r8(ROOT)))
        assert steps(h, T) == expected_steps(euclid_model.mask(4, 16, 0), 16, 0, notes, 2, 96)


def test_accents(pl13_image, pl13_manifest):
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    hits = euclid_model.mask(8, 16, 0)
    for accent in (1, 2, 3):
        configure(h, pl13_manifest, k=8, e0=8, c0=accent << 6)          # velocity soft: 48
        write(h)
        units = [[(60, 3, 127 if melody_model.accent(accent, j, i) else 48)] for j, i in enumerate(hit_steps(hits))]
        assert steps(h, T) == units_steps(hits, units), accent
        if accent == 2:
            assert hit_steps(hits)[:4] == [0, 2, 4, 6] and [u[0][2] for u in units[:3]] == [127, 48, 127]


def test_to_the_next_hit_lengths_and_playback(pl13_image, pl13_manifest):
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    configure(h, pl13_manifest, k=3, gate=6)
    write(h)
    hits = euclid_model.mask(3, 16, 0)
    st = hit_steps(hits)
    units = [[(60, melody_model.next_len(hits, 16, i), 96)] for i in st]
    assert steps(h, T) == units_steps(hits, units)
    assert [u[0][1] for u in units] == [6 * (b - a) for a, b in zip(st, st[1:] + [st[0] + 16])]
    h.press(2)
    h.take()
    h.press(17)                                                    # Play
    step_ms = 60000 / param(h, TEMPO_STORE, 0) / 4
    ons, offs = [], []
    for ms in range(1, int(17 * step_ms) + 2):
        h.heartbeat(1)
        for e in h.take("midi_on", "midi_off"):
            if e[2] == 2:
                (ons if e[0] == "midi_on" else offs).append((ms, e[3]))
    assert len(ons) >= 4 and len(offs) >= 3, (ons, offs)
    for k in range(3):                                             # each off at the next hit's on, the last at the loop's first
        assert abs(offs[k][0] - ons[k + 1][0]) <= 1, (ons, offs)


def test_high_range_drops_unplayable_notes(pl13_image, pl13_manifest):
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    h.uc.mem_write(ROOT, bytes([11]))
    c0 = 1 | 1 << 3 | 2 << 4                                       # up, scale, range 3
    c1 = 7 | 3 << 3
    configure(h, pl13_manifest, k=16, c0=c0, c1=c1, last=60)
    write(h)
    got = steps(h, T)
    notes = [got[28 * s + 4] for s in range(16)]
    assert all(12 <= nt + 11 <= 139 for nt in notes), notes
    root = melody_model.root(c1, 60, h.r32(SCALE_MASK))
    pl, at, fc = melody_model.pool(c0, root, h.r32(SCALE_MASK), 11 << 16)
    assert max(pl) + 11 <= 139 and notes == melody_model.line(c0, 1, 16, pl, at, 0xFFFF, fc)


def test_unplayable_root_writes_nothing(pl13_image, pl13_manifest):
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    before = steps(h, T)
    configure(h, pl13_manifest, k=5, c0=1, last=2, shape=0)      # order up, root = the last pad, pitch 2 + key < 12
    h.uc.mem_write(ROOT, bytes([0]))
    write(h)
    assert steps(h, T) == before and h.r8(sym(pl13_manifest, "euclid_undo_at")) == 0


def watch_masked(h, m, names):
    """Record (name, PRIMASK) at each entry of the named functions."""
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_PRIMASK
    calls = []
    for name in names:
        a = sym(m, name) & ~1
        h.uc.hook_add(UC_HOOK_CODE, lambda uc, addr, size, d, name=name:
                      calls.append((name, uc.reg_read(UC_ARM_REG_PRIMASK) & 1)), begin=a, end=a)
    return calls


def test_the_line_is_worked_out_before_interrupts_are_masked(pl13_image, pl13_manifest):
    """The rhythm, the pool and the line are worked out before slim_irq_save; with interrupts masked the Write only
    copies the old steps and writes the new ones (final review: a shorter masked section)."""
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    configure(h, m, k=5, e0=5 | 0x80 | 1 << 5, c0=1, shape=1, seed=(9, 1))     # groove, order up
    calls = watch_masked(h, m, ("melody_groove", "melody_pool", "melody_line", "slim_irq_save", "euclid_write_to"))
    write(h)
    names = [c[0] for c in calls]
    names = names[names.index("euclid_write_to"):]       # the Write's (PL16: the drums' heartbeat masks a swap too)
    assert {"melody_groove", "melody_pool", "melody_line"} <= set(names[:names.index("slim_irq_save")])
    assert all(not masked for name, masked in calls), calls
    mask = h.r32(SCALE_MASK)
    pl, at, fc = melody_model.pool(1, 60, mask, chord_settings_word(1) | h.r8(ROOT) << 16)
    hits = melody_model.groove(5, 16, 0, 9)
    assert steps(h, T) == units_steps(hits, [[(nt, 3, 96)] for nt in melody_model.line(1, 1, 16, pl, at, hits, fc)])


def test_a_chain_moving_on_before_the_mask_gets_its_own_rhythm(pl13_image, pl13_manifest):
    """The target is read before the masked section and again inside it: the Main task moving a chain on in between
    (here at slim_irq_save, to a 12-step pattern) gets that pattern's rhythm and line, worked out again inside."""
    from unicorn import UC_HOOK_CODE
    from test_euclid import ENG
    from notes import PATTERN_BASE
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    configure(h, m, k=5, e0=5 | 0x80 | 1 << 5, c0=1, shape=1, seed=(9, 1))
    h.uc.mem_write(PATTERN_BASE[T] + 0xCA8 + 0x380, bytes([11, 0]))             # pattern 2: 12 steps
    originals = [steps(h, T, p) for p in range(2)]
    h.call(0x0803542C, h.r32(ENG + 0x30 + 4 * T), 0)                             # param_get: the pattern byte
    pattern_byte = h.uc.reg_read(UC_ARM_REG_R0)
    fired = []

    def chain_moves_on(uc, address, size, data):
        if not fired:
            fired.append(address)
            uc.mem_write(pattern_byte, b"\x01")

    pick(h, WRITE)
    a = sym(m, "slim_irq_save") & ~1
    h.uc.hook_add(UC_HOOK_CODE, chain_moves_on, begin=a, end=a)
    pick(h, WRITE)
    assert fired and steps(h, T, 0) == originals[0]
    mask = h.r32(SCALE_MASK)
    pl, at, fc = melody_model.pool(1, 60, mask, chord_settings_word(1) | h.r8(ROOT) << 16)
    hits = melody_model.groove(5, 12, 0, 9)
    assert steps(h, T, 1) == units_steps(hits, [[(nt, 3, 96)] for nt in melody_model.line(1, 1, 12, pl, at, hits, fc)],
                                         n=12)
    assert h.r8(sym(m, "euclid_undo_at")) == 1 + (T << 3 | 1)


# ---- The draft (Task 5) ----

from test_euclid import UNDO, WRITE, current, pattern_at, whole   # noqa: E402

WRITE_DRAFT = 0x45                                  # COL_ORANGE: a draft is live; 0x46 ready, 0x47 armed
DRAFT_ORDER = 6                                     # melody_cfg[0]: order random, chord pool, range 1
DOWN_BTN = 19


def line_steps(h, c0, seed, k=8, c1=0x10, last=60, shape=1, gate=2, vel=96):
    """The steps a Write of order c0 with the notes seed `seed` leaves (16 steps, no accent)."""
    mask = h.r32(SCALE_MASK)
    root = melody_model.root(c1, last, mask)
    pl, at, fc = melody_model.pool(c0, root, mask, chord_settings_word(shape) | h.r8(ROOT) << 16)
    hits = euclid_model.mask(k, 16, 0)
    line = melody_model.line(c0, seed, 16, pl, at, hits, fc)
    return units_steps(hits, [[(nt, gate + 1, vel)] for nt in line])


def rolled(h, c0, seed, k=8, c1=0x10, last=60, shape=1):
    """The notes seed after a dice notes press for line_steps' settings (melody_model.dice_notes)."""
    mask = h.r32(SCALE_MASK)
    root = melody_model.root(c1, last, mask)
    pl, at, fc = melody_model.pool(c0, root, mask, chord_settings_word(shape) | h.r8(ROOT) << 16)
    return melody_model.dice_notes(c0, seed, 16, pl, at, fc, euclid_model.mask(k, 16, 0))


def undo_copy(h, m):
    return bytes(h.uc.mem_read(sym(m, "euclid_undo_steps"), 0x380))


def draft_of(h, m):
    return h.r8(sym(m, "melody_draft"))


def test_plain_euclid_never_drafts(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    pick(h, 4)
    write(h)
    written = steps(h, T)
    assert written == expected_steps(euclid_model.mask(5, 16, 0), 16, 0, [72], 2, 96)
    assert h.leds()[WRITE] == ORANGE_D and draft_of(h, m) == 0
    for pad in (7, 16, 17, 20, 22, 28, 29):               # hits, rotate, gate, velocity, dice: only the settings move
        pick(h, pad)
        assert h.leds()[WRITE] == ORANGE_D
    assert steps(h, T) == written and draft_of(h, m) == 0


def test_a_new_setting_starts_a_draft(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    before = steps(h, T)
    configure(h, m, k=8, c0=DRAFT_ORDER, shape=1)
    pick(h, WRITE)
    assert h.leds()[WRITE] == 0x47 and draft_of(h, m) == 0
    pick(h, WRITE)
    assert h.leds()[WRITE] == WRITE_DRAFT and draft_of(h, m) == T + 1
    assert steps(h, T) == line_steps(h, DRAFT_ORDER, 1)
    copy = undo_copy(h, m)
    assert copy == before
    pick(h, 29)                                           # dice notes: the new seed's line, at once
    seed = rolled(h, DRAFT_ORDER, 1)
    assert mseed(h, m, T)[1] == seed
    assert steps(h, T) == line_steps(h, DRAFT_ORDER, seed)
    pick(h, 4)                                            # a hits pick
    assert steps(h, T) == line_steps(h, DRAFT_ORDER, seed, k=5)
    h.press(DOWN_BTN)
    h.press(DOWN_BTN)                                     # Melody (after Pattern tools 2, PL14): a pick there
    pick(h, 2)
    assert h.leds()[WRITE] == WRITE_DRAFT
    assert steps(h, T) == line_steps(h, 2, seed, k=5)
    h.uc.mem_write(pattern_at(h, T), bytes(0x380))        # scribble: Write once puts the draft back, no arming
    pick(h, WRITE)
    assert h.leds()[WRITE] == WRITE_DRAFT and steps(h, T) == line_steps(h, 2, seed, k=5)
    assert undo_copy(h, m) == copy


def test_a_draft_pick_that_is_ignored_writes_nothing(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    configure(h, m, k=8, c0=0, c1=0x10, e0=8 | 0x80 | 1 << 5, shape=0)   # groove starts the draft; order same
    write(h)
    assert h.leds()[WRITE] == WRITE_DRAFT
    written = steps(h, T)
    h.uc.mem_write(pattern_at(h, T), bytes(0x380))
    pick(h, 29)                                           # dice notes with order same: dark, ignored
    assert steps(h, T) == bytes(0x380)
    h.press(DOWN_BTN)
    h.press(DOWN_BTN)                                     # Melody (after Pattern tools 2, PL14)
    pick(h, 25)                                           # an octave pick while the root is the last pad: ignored
    assert steps(h, T) == bytes(0x380)
    pick(h, 28)                                           # dice rhythm: handled
    assert steps(h, T) != bytes(0x380)


def test_undo_returns_the_pre_draft_pattern_and_ends_it(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    before = steps(h, T)
    configure(h, m, k=8, c0=DRAFT_ORDER, shape=1)
    write(h)
    pick(h, 29)
    pick(h, 4)
    pick(h, 29)
    last = steps(h, T)
    assert last != before
    pick(h, UNDO)
    assert steps(h, T) == before and h.leds()[WRITE] == ORANGE_D and draft_of(h, m) == 0
    pick(h, 29)                                           # a pick writes nothing now
    pick(h, 7)
    assert steps(h, T) == before
    pick(h, UNDO)                                         # PL11's redo
    assert steps(h, T) == last and draft_of(h, m) == 0


def test_paging_keeps_the_draft_closing_ends_it(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    configure(h, m, k=8, c0=DRAFT_ORDER, shape=1)
    write(h)
    h.press(20)
    h.press(20)                                           # Chords page
    assert draft_of(h, m) == T + 1
    drafted0 = steps(h, T)
    pick(h, 2)                                            # the real route: shape pad 3 (7th) on the Chords page
    assert h.r8(sym(m, "chord_settings") + T) & 7 == 2 and steps(h, T) == drafted0   # a Chords pick writes nothing
    h.press(19)
    h.press(19)                                           # Pattern tools again
    assert steps(h, T) == drafted0
    assert draft_of(h, m) == T + 1 and h.leds()[WRITE] == WRITE_DRAFT
    pick(h, 29)
    assert steps(h, T) == line_steps(h, DRAFT_ORDER, rolled(h, DRAFT_ORDER, 1, shape=2), shape=2)
    drafted = steps(h, T)
    h.press(9)                                            # Note: the page closes
    assert draft_of(h, m) == 0
    open_tools(h, T)
    assert h.leds()[WRITE] == ORANGE_D
    pick(h, 29)
    pick(h, 4)
    assert steps(h, T) == drafted


def test_another_tracks_pages_end_the_draft(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    configure(h, m, k=8, c0=DRAFT_ORDER, shape=1)
    write(h)
    assert draft_of(h, m) == T + 1
    h.press(3, shift=True)                                # MIDI 2's pages
    assert draft_of(h, m) == 0


def test_draft_in_a_playing_chain_writes_its_own_pattern(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    h.leds()
    h.press(13)
    h.down(2)
    h.down(10)                                            # Patterns view: hold pattern 1, press pattern 2
    h.up(10)
    h.up(2)
    open_tools(h, T)
    configure(h, m, k=8, c0=6, shape=1)
    write(h)
    assert current(h, T) == 0
    h.press(17)
    step_ms = 60000 / param(h, TEMPO_STORE, 0) / 4
    for _ in range(int(20 * step_ms)):
        h.heartbeat(1)
    assert current(h, T) == 1
    other = whole(h, T, 1)
    before = steps(h, T, 0)
    pick(h, 29)
    want = line_steps(h, 6, rolled(h, 6, 1))
    got = steps(h, T, 0)
    assert got == want != before
    assert whole(h, T, 1) == other


def test_draft_rewrites_while_playing_leave_nothing_on(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    h.leds()
    h.press(17)
    h.heartbeat(200)
    open_tools(h, 0)
    configure(h, m, k=8, gate=6, c0=6, t=0)               # order random, gate to the next hit
    write(h)
    assert h.leds()[WRITE] == WRITE_DRAFT
    h.take()
    depth = {}                                            # note-ons minus note-offs per note: never two on at once
    for _ in range(20):
        pick(h, 29)
        h.heartbeat(200)
        for e in h.take("midi_on", "midi_off", "synth_on", "synth_off"):
            key = (e[0].split("_")[0], e[2], e[3]) if e[0].startswith("midi") else (e[0].split("_")[0], e[1], e[2])
            depth[key] = max(0, depth.get(key, 0) + (1 if e[0].endswith("_on") else -1))
            assert depth[key] <= 1, ("note-on twice without its off", key)
    h.press(17)
    h.heartbeat(300)
    assert h.sounding == set(), sorted(h.sounding)
    for e in h.take("midi_on", "midi_off", "synth_on", "synth_off"):
        key = (e[0].split("_")[0], e[2], e[3]) if e[0].startswith("midi") else (e[0].split("_")[0], e[1], e[2])
        depth[key] = max(0, depth.get(key, 0) + (1 if e[0].endswith("_on") else -1))
    assert not any(depth.values()), depth


def test_link_write_ends_the_draft(pl13_image, pl13_manifest):
    from test_link import fresh, open_page, write as link_write
    m = pl13_manifest
    h = fresh(pl13_image)
    open_page(h, 2)
    h.uc.mem_write(sym(m, "melody_cfg"), bytes([DRAFT_ORDER, 0x10]))
    h.uc.mem_write(sym(m, "euclid_cfg"), bytes([8 | 1 << 5, 2 << 5]))
    h.uc.mem_write(sym(m, "euclid_last"), bytes([60]))
    write(h)
    assert h.leds()[WRITE] == WRITE_DRAFT
    written = steps(h, 0)
    h.hello()
    link_write(h, 37, [0x02])                             # melody_cfg track 0: order down
    h.frame()
    assert steps(h, 0) == written and draft_of(h, m) == 0 and h.leds()[WRITE] == ORANGE_D


def test_a_project_load_ends_the_draft(pl13_image, pl13_manifest):
    from test_saved import load
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    configure(h, m, k=8, c0=DRAFT_ORDER, shape=1)
    write(h)
    assert draft_of(h, m) == T + 1
    written = steps(h, T)
    load(h)
    h.leds()
    assert draft_of(h, m) == 0
    open_tools(h, T)
    assert h.leds()[WRITE] != WRITE_DRAFT
    h.uc.mem_write(sym(m, "euclid_cfg") + 2 * T, bytes([8 | 1 << 5, 2 << 5]))
    pick(h, 4)
    pick(h, 29)
    assert steps(h, T) == written                         # a page pick writes nothing


def test_unused_melody_pads_do_nothing_in_a_draft(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    configure(h, m, k=8, c0=DRAFT_ORDER, shape=1)
    write(h)
    h.press(DOWN_BTN)
    h.press(DOWN_BTN)                                     # Melody (after Pattern tools 2, PL14)
    h.uc.mem_write(pattern_at(h, T), bytes(0x380))
    for pad in (14, 15):
        pick(h, pad)
        assert steps(h, T) == bytes(0x380) and draft_of(h, m) == T + 1
    pick(h, 1)                                            # a used pad still re-writes
    assert steps(h, T) != bytes(0x380)


def test_a_link_write_to_euclid_cfg_ends_the_draft(pl13_image, pl13_manifest):
    from test_link import fresh, open_page, write as link_write
    m = pl13_manifest
    h = fresh(pl13_image)
    open_page(h, 2)
    h.uc.mem_write(sym(m, "melody_cfg"), bytes([DRAFT_ORDER, 0x10]))
    h.uc.mem_write(sym(m, "euclid_cfg"), bytes([8 | 1 << 5, 2 << 5]))
    h.uc.mem_write(sym(m, "euclid_last"), bytes([60]))
    write(h)
    assert h.leds()[WRITE] == WRITE_DRAFT
    written = steps(h, 0)
    h.hello()
    link_write(h, 25, [9 | 1 << 5])                       # euclid_cfg track 0: 9 hits
    h.frame()
    assert steps(h, 0) == written and draft_of(h, m) == 0 and h.leds()[WRITE] == ORANGE_D
    pick(h, 29)
    assert steps(h, 0) == written


# ---- Writes run on the pad's release (device finding 2026-10-20: a write during the press made a phantom press) ----

def in_draft(h, m, order=DRAFT_ORDER):
    """Pattern tools open on T with a draft live (order `order`, 8 hits, chord shape 1)."""
    open_tools(h, T)
    configure(h, m, k=8, c0=order, shape=1)
    write(h)
    assert draft_of(h, m) == T + 1
    return steps(h, T)


def test_write_second_press_writes_on_the_release(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    before = steps(h, T)
    configure(h, m, k=8, c0=DRAFT_ORDER, shape=1)
    pick(h, WRITE)                                        # the arming press stays on the press
    assert h.leds()[WRITE] == 0x47
    h.down(WRITE)                                         # the second press, finger still down
    assert steps(h, T) == before and draft_of(h, m) == 0
    h.up(WRITE)
    assert steps(h, T) == line_steps(h, DRAFT_ORDER, 1) and draft_of(h, m) == T + 1
    assert h.leds()[WRITE] == WRITE_DRAFT


def test_undo_swaps_on_the_release_and_never_arms_write(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    before = steps(h, T)
    pick(h, 4)
    write(h)
    written = steps(h, T)
    assert written != before
    for want in (before, written, before):
        h.down(UNDO)
        assert steps(h, T) != want and h.leds()[WRITE] != 0x47
        h.up(UNDO)
        assert steps(h, T) == want and h.leds()[WRITE] != 0x47


def test_a_draft_pick_writes_on_the_release(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    drafted = in_draft(h, m)
    h.press(DOWN_BTN)
    h.press(DOWN_BTN)                                     # Melody (after Pattern tools 2, PL14)
    h.down(2)                                             # order pad 3: down
    assert mcfg(h, m, T)[0] & 7 == 2 and h.leds()[2] == YELLOW      # the setting and its LED follow at once
    assert steps(h, T) == drafted
    h.up(2)
    assert steps(h, T) == line_steps(h, 2, 1) and draft_of(h, m) == T + 1


def test_dice_and_pattern_tools_picks_write_on_the_release(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    drafted = in_draft(h, m)
    h.down(29)                                            # dice notes
    seed = rolled(h, DRAFT_ORDER, 1)
    assert mseed(h, m, T)[1] == seed and steps(h, T) == drafted
    h.up(29)
    assert steps(h, T) == line_steps(h, DRAFT_ORDER, seed)
    after = steps(h, T)
    h.down(4)                                             # hits
    assert ecfg(h, m, T)[0] & 0x1F == 5 and steps(h, T) == after
    h.up(4)
    assert steps(h, T) == line_steps(h, DRAFT_ORDER, seed, k=5)
    after = steps(h, T)
    h.uc.mem_write(pattern_at(h, T), bytes(0x380))
    h.down(WRITE)                                         # Write in a draft: no arming, a re-write
    assert steps(h, T) == bytes(0x380)
    h.up(WRITE)
    assert steps(h, T) == after


def test_two_pads_one_write_on_the_last_release(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    drafted = in_draft(h, m)
    h.down(4)                                             # hits 5
    h.down(7)                                             # hits 8 (the latest press wins the pending action)
    h.up(4)
    assert steps(h, T) == drafted
    h.up(7)
    assert ecfg(h, m, T)[0] & 0x1F == 8 and steps(h, T) == line_steps(h, DRAFT_ORDER, 1, k=8)
    h.down(4)
    h.down(29)
    h.up(4)
    assert steps(h, T) == line_steps(h, DRAFT_ORDER, 1, k=8)
    h.up(29)
    seed = rolled(h, DRAFT_ORDER, 1, k=5)
    assert steps(h, T) == line_steps(h, DRAFT_ORDER, seed, k=5)       # both changes in one write


def test_a_release_after_the_pages_close_writes_nothing(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    drafted = in_draft(h, m)
    h.down(4)
    h.press(9)                                            # Note: the pages close
    h.up(4)
    assert steps(h, T) == drafted
    open_tools(h, T)                                      # a Write's second press, closed before its release
    pick(h, WRITE)
    h.uc.mem_write(pattern_at(h, T), bytes(0x380))
    h.down(WRITE)
    h.press(9)
    h.up(WRITE)
    assert steps(h, T) == bytes(0x380) and draft_of(h, m) == 0
    open_tools(h, T)                                      # Undo likewise
    pick(h, WRITE)
    pick(h, WRITE)
    now = steps(h, T)
    h.down(UNDO)
    h.press(9)
    h.up(UNDO)
    assert steps(h, T) == now


def test_a_release_after_a_project_load_writes_nothing(pl13_image, pl13_manifest):
    from test_saved import load
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    drafted = in_draft(h, m)
    h.down(4)
    load(h)
    h.leds()
    h.up(4)
    assert steps(h, T) == drafted


def test_a_release_with_nothing_pending_writes_nothing(pl13_image, pl13_manifest):
    m = pl13_manifest
    h = NoteHarness(pl13_image)
    open_tools(h, T)
    configure(h, m, k=8, c0=DRAFT_ORDER, shape=1)
    before = steps(h, T)
    for pad in (4, 29, 17, 20):                           # outside a draft: picks only move settings
        h.down(pad)
        h.up(pad)
    assert steps(h, T) == before
    pick(h, WRITE)                                        # arms only: nothing pending
    h.up(WRITE)
    h.up(UNDO)                                            # a release never pressed: nothing
    h.up(5)
    h.leds()
    assert steps(h, T) == before


# ---- PL14: a press that changes nothing keeps a draft's pending re-write (PL13 review) ----

UP_BTN = 20


def held_pick(img, m, setup, held, noop):
    """In a draft: the presses in `setup`, then pad `held` down, the press `noop` (or none), `held` up. The steps
    before `held` and after its release."""
    h = NoteHarness(img)
    in_draft(h, m)
    for kind, x in setup:
        h.press(x) if kind == "btn" else pick(h, x)
    before = steps(h, T)
    h.down(held)
    if noop:
        kind, x = noop
        h.press(x) if kind == "btn" else pick(h, x)
    h.up(held)
    return before, steps(h, T)


@pytest.mark.parametrize("setup, held, noop", [
    ((), 4, ("btn", DOWN_BTN)),                                          # hits 5, then ▼ to Pattern tools 2
    ((("btn", DOWN_BTN),) * 2, 2, ("pad", 14)),                          # order down, then an unused Melody pad
    ((("btn", DOWN_BTN),) * 2 + (("pad", 0),) + (("btn", UP_BTN),) * 2, 4, ("pad", 29)),   # order same: hits 5, then dice notes
], ids=["page-step", "unused-pad", "dice-notes-same"])
def test_a_press_that_changes_nothing_keeps_the_pending_rewrite(pl14_image, pl14_manifest, setup, held, noop):
    before, got = held_pick(pl14_image, pl14_manifest, setup, held, noop)
    _, want = held_pick(pl14_image, pl14_manifest, setup, held, None)
    assert got == want != before


def test_a_draft_write_waits_for_every_pad(pl15_image, pl15_manifest):
    m = pl15_manifest
    h = NoteHarness(pl15_image)
    open_tools(h, T)
    configure(h, m, k=6, c0=DRAFT_ORDER, shape=1)
    write(h)
    drafted = steps(h, T)
    h.down(4)                                             # hits 5
    h.down(7)                                             # hits 8 (the latest press's pick)
    h.up(7)                                               # pad 4 is still down: nothing is written
    assert steps(h, T) == drafted
    h.up(4)
    assert ecfg(h, m, T)[0] & 0x1F == 8 and steps(h, T) == line_steps(h, DRAFT_ORDER, 1, k=8)


def test_undo_waits_for_a_held_draft_pad(pl15_image, pl15_manifest):
    m = pl15_manifest
    h = NoteHarness(pl15_image)
    open_tools(h, T)
    before = steps(h, T)
    configure(h, m, k=8, c0=DRAFT_ORDER, shape=1)
    write(h)
    drafted = steps(h, T)
    assert drafted != before
    h.down(4)
    h.down(UNDO)
    h.up(UNDO)                                            # pad 4 is still down
    assert steps(h, T) == drafted
    h.up(4)
    assert steps(h, T) == before


def test_a_page_open_clears_a_lost_release(pl15_image, pl15_manifest):
    m = pl15_manifest
    h = NoteHarness(pl15_image)
    open_tools(h, T)
    h.down(4)
    h.press(9)                                            # Note: the pages close and pad 4's release is lost
    before = steps(h, T)
    open_tools(h, T)
    configure(h, m, k=8, c0=DRAFT_ORDER, shape=1)
    write(h)                                              # a stale bit would hold the write back for ever
    assert steps(h, T) != before and draft_of(h, m) == T + 1
