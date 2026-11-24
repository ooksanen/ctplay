"""Pattern tools for the drums (PL17, spec 2026-10-25-drums-design.md, "Pattern tools for drums"): Pattern tools and
Pattern tools 2 on a drum's page list (slot 2, pad 27, orange), the rhythm settings per drum (drum_euclid, drum_rhythm,
drum_accent, drum_seed), the roll and accent pads, the preview over the drum's shown pattern, and a latched repeat
across the pages; the Write, Undo and the draft through the drum editor's step store (spec "What a Write writes")."""
import pytest
from unicorn.arm_const import UC_ARM_REG_R0

import melody_model as mm
from drums import BPM, DRUM_PAD, PAT, DrumHarness, drum_setup
from notes import pattern_snapshot, set_tempo
from test_page import fill_note_arrays, note_arrays

pytestmark = pytest.mark.emu
DOWN, UP = 19, 20                                                      # Octave ▼ = next page, ▲ = previous
LED_DOWN, LED_UP = 51, 52
TOC = 24                                                               # the table of contents: pad 25 = slot 0
REPEAT, TOOLS = 1, 2                                                   # the drum page list's slots (beta: Repeat on pad 26)
SUB = 0x08                                                             # drum_page bit 3: Pattern tools 2
ORANGE, ORANGE_D, BLUE, BLUE_D, WHITE, WHITE_D = 0x45, 0x46, 0x07, 0x08, 0x01, 0x02
MAG, MAG_D, CYAN, CYAN_D, VIOLET, VIOLET_D = 0x32, 0x38, 0x4D, 0x4E, 0x49, 0x4A
YELLOW, YELLOW_D = 0x2D, 0x2E
ROLL_COL = [0x68, 0x66, 0x63]                                          # stock's Gate view 1/6, 3/6, 6/6: 1, 2, 3 hits
ACCENT_COL = [YELLOW_D, YELLOW, WHITE, MAG]                            # Melody's accent pad: off, first, beat, 3rd
PULSE = 0x04                                                           # the Repeat page: a latched drum's pad


def sym(m, name):
    return int(m["symbols"][name], 16)


def pick(h, pad):
    h.down(pad)
    h.up(pad)


def drum_page(h, d):
    return h.r8(sym(h.m, "drum_page") + d)


def ecfg(h, d):
    return tuple(h.uc.mem_read(sym(h.m, "drum_euclid") + 2 * d, 2))


def rcfg(h, d):
    return tuple(h.uc.mem_read(sym(h.m, "drum_rhythm") + 3 * d, 3))


def accent(h, d):
    return h.r8(sym(h.m, "drum_accent") + d)


def seed(h, d):
    return h.r8(sym(h.m, "drum_seed") + d)


def drum_fields(h):
    return tuple(bytes(h.uc.mem_read(sym(h.m, k), n)) for k, n in (("drum_euclid", 8), ("drum_rhythm", 12),
                                                                    ("drum_accent", 4), ("drum_seed", 4)))


def shown(h, d):
    """Drum d's shown pattern's address."""
    return h.base(d) + PAT * h.shown_pattern(d)


def span(h, d):
    """(first, n): the shown pattern's steps first .. first + n - 1 (swapped when first > last, as range_of)."""
    a = shown(h, d)
    last, first = h.r8(a + 0x80) % 32, h.r8(a + 0x81) % 32
    first, last = min(first, last), max(first, last)
    return first, last - first + 1


def set_last(h, d, last):
    h.uc.mem_write(shown(h, d) + 0x80, bytes([last]))


def open_drum(h, d):
    h.leds()                                                           # slim's power-on init at the first frame
    h.press(4 + d, shift=True)
    assert h.r8(sym(h.m, "chord_page")) == 4 + d


def open_tools(h, d, sub=0):
    """Drum d's page, then Pattern tools (or Pattern tools 2) through the table of contents."""
    open_drum(h, d)
    h.shift(True)
    pick(h, TOC + TOOLS)                                               # on the page of it used last (power-on: page 1)
    if sub:
        pick(h, TOC + TOOLS)                                           # the open feature's pad: its other page
    h.shift(False)
    assert drum_page(h, d) == TOOLS | (SUB if sub else 0)


def preview(mask, n, on, dim):
    return [on if mask >> s & 1 else dim if s < n else 0 for s in range(16)]


def test_drum_toc_has_pattern_tools(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    open_drum(h, 0)
    leds = h.leds()
    assert (leds[LED_DOWN], leds[LED_UP]) == (ORANGE, 0)               # Repeat: Pattern tools after it
    h.shift(True)
    assert h.leds()[24:32] == [0, BLUE, ORANGE_D, 0, 0, 0, 0, 0]
    pick(h, TOC + TOOLS)
    assert drum_page(h, 0) == TOOLS                                    # its first page (bit 3 clear)
    assert h.leds()[24:32] == [0, BLUE_D, ORANGE, 0, 0, 0, 0, 0]
    pick(h, TOC + TOOLS)                                               # again: Pattern tools 2
    assert drum_page(h, 0) == TOOLS | SUB
    for pad in (24, 27, 28, 31):                                       # no page there (25: Levels, later)
        pick(h, pad)
    assert drum_page(h, 0) == TOOLS | SUB
    pick(h, TOC + REPEAT)
    assert drum_page(h, 0) == REPEAT | SUB                             # Repeat; Pattern tools 2 stays the one used last
    pick(h, TOC + TOOLS)
    assert drum_page(h, 0) == TOOLS | SUB
    pick(h, TOC + REPEAT)
    h.shift(False)
    pages = []
    for _ in range(3):
        h.press(DOWN)                                                  # Pattern tools, Pattern tools 2, stays
        leds = h.leds()
        pages.append((drum_page(h, 0), leds[LED_DOWN], leds[LED_UP]))
    assert pages == [(TOOLS, ORANGE, BLUE), (TOOLS | SUB, 0, ORANGE), (TOOLS | SUB, 0, ORANGE)]
    h.press(UP)
    assert drum_page(h, 0) == TOOLS
    h.press(UP, shift=True)
    assert drum_page(h, 0) == REPEAT
    h.press(UP)
    assert drum_page(h, 0) == REPEAT and h.r8(sym(h.m, "chord_page")) == 4


def test_drum_tools_picks(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    open_tools(h, 1)                                                   # Drum 2
    others = [(ecfg(h, d), rcfg(h, d), accent(h, d), seed(h, d)) for d in (0, 2, 3)]
    pick(h, 4)
    assert ecfg(h, 1) == (0x25, 0x00)                                  # 5 hits, velocity medium
    set_last(h, 1, 11)                                                 # a 12-step pattern
    assert span(h, 1) == (0, 12)
    pick(h, 16)                                                        # earlier
    assert ecfg(h, 1)[1] == 1
    pick(h, 17)
    pick(h, 17)                                                        # later twice: wraps within the 12 steps
    assert ecfg(h, 1)[1] == 11
    pick(h, 16)
    assert ecfg(h, 1)[1] == 0
    pick(h, 16)
    pick(h, 18)                                                        # back to rotation 0
    assert ecfg(h, 1)[1] == 0
    pick(h, 19)
    assert ecfg(h, 1)[0] == 0x80 | 0x25                                # groove
    rolls = []
    for _ in range(3):
        pick(h, 20)
        rolls.append(ecfg(h, 1)[1] >> 5)
    assert rolls == [1, 2, 0]                                          # 2, 3, 1 hits a step
    pick(h, 20)
    pick(h, 17)                                                        # a rotation keeps the roll
    assert ecfg(h, 1)[1] == 1 << 5 | 11
    for pad, vel in ((23, 2), (21, 0), (22, 1)):
        pick(h, pad)
        assert ecfg(h, 1)[0] >> 5 & 3 == vel
    pick(h, 24)
    assert rcfg(h, 1)[2] == 1                                          # cycle 3 steps
    h.press(DOWN)                                                      # Pattern tools 2
    assert drum_page(h, 1) == TOOLS | SUB
    pick(h, 2)
    assert rcfg(h, 1)[0] == 3                                          # second hits 3
    pick(h, 19)
    assert rcfg(h, 1)[0] == 1 << 5 | 3                                 # combine 1 (both)
    pick(h, 24)
    assert rcfg(h, 1)[1] >> 5 & 3 == 1                                 # thinning 1/4
    got = []
    for _ in range(4):
        pick(h, 27)
        got.append(accent(h, 1))
    assert got == [1, 2, 3, 0]                                         # first hit, on the beat, every 3rd, off
    assert [(ecfg(h, d), rcfg(h, d), accent(h, d), seed(h, d)) for d in (0, 2, 3)] == others
    assert h.take("synth_on", "midi_on") == [] and h.sounding == set()


def test_drum_tools_leave_note_arrays(pl17_image, pl17_manifest):
    """Review focus (as PL16's test_drum_pages_keep_note_arrays): every pick of both drum pages, the dice, Undo, Write,
    ▲ ▼ and the table of contents leave every note-track array, and the note tracks' patterns, as they were."""
    m = pl17_manifest
    h = DrumHarness(pl17_image, pl17_manifest)
    h.leds()
    fill_note_arrays(h, m)
    before = note_arrays(h, m)
    patterns = [pattern_snapshot(h, t) for t in range(4)]
    for d in range(4):
        open_tools(h, d)
        for sub in (0, 1):
            for pad in range(28):
                pick(h, pad)
                h.leds()
            pick(h, 4)                                                 # hits again (the last picks may have cleared them)
            for pad in (28, 29, 30, 31, 31, 30):                       # dice, dice notes, Undo, Write twice, Undo
                pick(h, pad)
                h.leds()
            h.press(DOWN)
            h.leds()
        for b in (UP, DOWN, UP, UP):
            h.press(b)
            h.leds()
        h.shift(True)
        for pad in range(TOC, 32):
            pick(h, pad)
            h.leds()
        h.shift(False)
        assert note_arrays(h, m) == before, d
    assert [pattern_snapshot(h, t) for t in range(4)] == patterns


def test_drum_tools_leds(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    open_tools(h, 0)
    first, n = span(h, 0)
    assert n == 16                                                     # the snapshot's drum patterns: 16 steps
    leds = h.leds()
    assert leds[:16] == [ORANGE_D] * 16                                # no hits
    assert leds[16:32] == [WHITE_D] * 4 + [ROLL_COL[0], MAG_D, MAG, MAG_D] + [CYAN_D] * 4 + [WHITE_D, 0, 0, 0]
    pick(h, 4)
    pick(h, 16)
    pick(h, 25)                                                        # 5 hits, rotated 1, cycle 5
    assert h.leds()[31] == ORANGE_D                                    # Write ready: hits to write
    e0, e1 = ecfg(h, 0)
    want = mm.final_hits(e0, e1, seed(h, 0), 16, rcfg(h, 0))
    assert h.leds()[:16] == preview(want, 16, ORANGE, ORANGE_D) and want
    set_last(h, 0, 11)                                                 # 12 steps: pads 12-15 off
    want = mm.final_hits(e0, e1, seed(h, 0), 12, rcfg(h, 0))
    assert h.leds()[:16] == preview(want, 12, ORANGE, ORANGE_D) and h.leds()[12:16] == [0] * 4
    rolls = []
    for _ in range(3):
        pick(h, 20)
        rolls.append(h.leds()[20])
    assert rolls == ROLL_COL[1:] + ROLL_COL[:1]
    leds = h.leds()
    assert (leds[29], leds[30]) == (0, 0)                              # dice notes dark, no Undo
    h.press(DOWN)                                                      # Pattern tools 2
    for pad in (2, 17, 23, 25):                                        # second hits 3, rotate, combine accent, thinning 2
        pick(h, pad)
    e0, e1 = ecfg(h, 0)
    r = rcfg(h, 0)
    leds = h.leds()
    assert leds[:16] == preview(mm.second_rhythm(r, 12), 12, WHITE, WHITE_D)
    assert leds[16:19] == [WHITE_D] * 3 and leds[19:24] == [VIOLET_D] * 4 + [VIOLET]
    assert leds[24:27] == [CYAN_D, CYAN, CYAN_D]
    colours = [leds[27]]
    for _ in range(4):
        pick(h, 27)
        colours.append(h.leds()[27])
    assert colours == ACCENT_COL + ACCENT_COL[:1]
    write = ORANGE_D if mm.final_hits(e0, e1, seed(h, 0), 12, r) else 0
    assert h.leds()[28:32] == [WHITE_D, 0, 0, write]


def test_drum_write_dark_without_hits(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    open_tools(h, 3)
    assert h.leds()[29:32] == [0, 0, 0]                                # k = 0: Write dark
    pick(h, 0)
    assert h.leds()[29:32] == [0, 0, ORANGE_D]
    h.press(DOWN)
    assert h.leds()[29:32] == [0, 0, ORANGE_D]


@pytest.mark.parametrize("groove", [0, 1])
def test_drum_dice_rhythm(pl17_image, pl17_manifest, groove):
    h = DrumHarness(pl17_image, pl17_manifest)
    open_tools(h, 2)
    pick(h, 6)                                                         # 7 hits
    pick(h, 20)                                                        # roll 1: the dice keeps it
    if groove:
        pick(h, 19)
    _, n = span(h, 2)
    s, rot = seed(h, 2), ecfg(h, 2)[1] & 0x1F
    notes = note_arrays(h, h.m)
    pick(h, 28)
    want = mm.dice_rhythm(groove, 7, n, rot, s)
    assert (seed(h, 2), ecfg(h, 2)[1] & 0x1F) == want and want[0] != s
    assert ecfg(h, 2)[1] >> 5 == 1
    fields = drum_fields(h)
    pick(h, 29)                                                        # dice notes: nothing for a drum
    assert drum_fields(h) == fields and note_arrays(h, h.m) == notes
    h.press(DOWN)                                                      # Pattern tools 2: the same pads
    pick(h, 29)
    assert drum_fields(h) == fields
    pick(h, 28)
    assert (seed(h, 2), ecfg(h, 2)[1] & 0x1F) == mm.dice_rhythm(groove, 7, n, *want[::-1])
    assert note_arrays(h, h.m) == notes


def on_ticks(h, d, since=0):
    return [t for ms, t, k, nt, v in h.sent[since:] if k == "on" and nt == d + 1]


def test_repeat_across_drum_pages(pl17_image, pl17_manifest):
    """Review focus: a latched drum keeps repeating while its page list is on Pattern tools or Pattern tools 2 (▲ ▼
    and the table of contents), and pads 28-31 there are actions: they never start, stop or release a drum."""
    h = DrumHarness(pl17_image, pl17_manifest)
    drum_setup(h)                                                      # drum 1's page: Repeat
    pick(h, 2)                                                         # rate 1/16
    pick(h, 15)                                                        # latch
    h.press(17)                                                        # Play; the next heartbeat makes it tick 0
    h.heartbeat(1)
    h.until_tick(12)
    pick(h, DRUM_PAD + 1)                                              # drum 2 latched
    latched = sym(h.m, "rep_latched")
    h.until_tick(40)
    assert h.leds()[DRUM_PAD + 1] == PULSE and h.r8(latched) == 0b10
    h.press(DOWN)                                                      # Pattern tools
    assert drum_page(h, 0) == TOOLS
    since = len(h.sent)
    h.until_tick(70)
    for pad in range(DRUM_PAD, 32):                                    # dice rhythm, dice notes, Undo, Write
        pick(h, pad)
        h.heartbeat(3)
    h.shift(True)
    pick(h, TOC + TOOLS)                                               # the table of contents: Pattern tools 2
    h.shift(False)
    assert drum_page(h, 0) == TOOLS | SUB
    for pad in range(DRUM_PAD, 32):
        h.down(pad, 120)
        h.heartbeat(3)
        h.up(pad)
    h.until_tick(130)
    assert h.r8(latched) == 0b10
    assert [d for d in range(4) if on_ticks(h, d, since)] == [1]       # only drum 2 sounded: no pad started one
    assert on_ticks(h, 1, since) == list(range(42, 130, 6))            # every 1/16, none stopped or doubled
    h.press(UP)
    h.press(UP)                                                        # Pattern tools, Repeat
    assert drum_page(h, 0) == REPEAT
    pick(h, DRUM_PAD + 1)                                              # the next tap stops it
    h.heartbeat(1)
    assert h.sent[-1][2:4] == ("off", 2) and h.r8(latched) == 0
    stopped = len(h.sent)
    h.heartbeat(200)
    assert h.sent[stopped:] == []


# ---- The Write, Undo and the draft (Task 3) ----

UNDO, WRITE, ARMED = 30, 31, 0x47
HARD, GROOVE, ROLL, ACCENT = 23, 19, 20, 27                            # Pattern tools' hard and groove, roll; tools 2's accent
ROLL_MICRO = (0x01, 0x09, 0x15)                                        # 1, 2, 3 hits a step: microsteps 0 · 0, 3 · 0, 2, 4
VEL_BTN, PATTERNS_BTN, PLAY_BTN = 10, 13, 17
FOLLOW = 0x20039DE0                                                    # p0 = 1 after Shift + Patterns: editors stop following
STORE_TOUCH_ALL, STORE_COMMIT = 0x08035456, 0x080353C0
SESSION, RECORD_SIZE = 0x2003D71C, 0x2740C


def write(h):
    pick(h, WRITE)
    pick(h, WRITE)


def img(h, d, p):
    """Drum d's pattern p: the 128 B a Write replaces (velocity, probability, flip, micro)."""
    return bytes(h.uc.mem_read(h.base(d) + PAT * p, 0x80))


def drum_image(hits, n, first, vel, roll, hard):
    """What a Write writes: a hit on step first + i for bit i of `hits` (i < n) at `vel` (127 where `hard`), micro
    `roll`; every step probability 7, flip 0xFF; no hit: velocity 0, micro 0."""
    v, pr, fl, mi = bytearray(32), bytearray([7] * 32), bytearray([0xFF] * 32), bytearray(32)
    for s in range(32):
        i = s - first
        if 0 <= i < n and hits >> i & 1:
            v[s], mi[s] = 127 if hard >> i & 1 else vel, roll
    return bytes(v + pr + fl + mi)


def model(h, d, n):
    e0, e1 = ecfg(h, d)
    return mm.final_hits(e0, e1, seed(h, d), n, rcfg(h, d))


def draft(h):
    return h.r8(sym(h.m, "melody_draft"))


def undo_at(h):
    return bytes(h.uc.mem_read(sym(h.m, "drum_undo_at"), 4))


def drums_but(h, d, p):
    """Every drum pattern, whole, but drum d's pattern p."""
    return {(e, q): bytes(h.uc.mem_read(h.base(e) + PAT * q, PAT)) for e in range(4) for q in range(8) if (e, q) != (d, p)}


def test_drum_write_bytes(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    open_tools(h, 0)
    p, a = h.shown_pattern(0), shown(h, 0)
    rest = bytes(h.uc.mem_read(a + 0x80, PAT - 0x80))                 # settings, upstream's bytes, the lanes
    others, notes = drums_but(h, 0, p), [pattern_snapshot(h, t) for t in range(4)]
    for pad in (4, HARD, ROLL):                                        # 5 hits, hard, two hits a step
        pick(h, pad)
    write(h)
    assert span(h, 0) == (0, 16)
    want = drum_image(model(h, 0, 16), 16, 0, 127, ROLL_MICRO[1], 0)
    assert img(h, 0, p) == want and h.store_bytes(0) == want         # through the store: its read view is the pattern
    assert bytes(h.uc.mem_read(a + 0x80, PAT - 0x80)) == rest
    assert drums_but(h, 0, p) == others and [pattern_snapshot(h, t) for t in range(4)] == notes
    assert undo_at(h) == bytes([1 + p, 0, 0, 0]) and h.r8(sym(h.m, "euclid_undo_at")) == 0
    leds = h.leds()
    assert draft(h) == 0 and (leds[UNDO], leds[WRITE]) == (BLUE, ORANGE_D)   # plain Euclid and the roll: no draft


def test_roll_out_of_range_writes_one_hit(pl18_image, pl18_manifest):
    """A roll past ROLL_MAX (7 here; no load, link write or pad can store it) is read as no roll: one hit a step."""
    h = DrumHarness(pl18_image, pl18_manifest)
    open_tools(h, 0)                                                   # slim's power-on init has run by now
    pick(h, 3)                                                         # 4 hits
    c1 = sym(h.m, "drum_euclid") + 1
    h.uc.mem_write(c1, bytes([h.r8(c1) | 0xE0]))                       # roll bits 7
    p = h.shown_pattern(0)
    write(h)
    micro = bytes(h.uc.mem_read(h.base(0) + PAT * p + 0x60, 32))
    assert sum(1 for x in micro if x) == 4 and set(micro) == {0, 0x01}


@pytest.mark.parametrize("settings", [bytes([11, 4]), bytes([4, 11])], ids=["first 4 last 11", "swapped"])
def test_drum_write_respects_first_and_last(pl17_image, pl17_manifest, settings):
    h = DrumHarness(pl17_image, pl17_manifest)
    open_tools(h, 1)                                                   # Drum 2
    p = h.shown_pattern(1)
    h.uc.mem_write(shown(h, 1) + 0x80, settings)                       # steps 5-12
    assert span(h, 1) == (4, 8)
    pick(h, 2)                                                         # 3 hits
    pick(h, 17)                                                        # rotated one step later
    write(h)
    hits = model(h, 1, 8)
    assert hits and img(h, 1, p) == drum_image(hits, 8, 4, 96, ROLL_MICRO[0], 0)
    assert h.store_bytes(1) == img(h, 1, p)
    assert bytes(h.uc.mem_read(shown(h, 1) + 0x80, 2)) == settings


def drum1_cleared(h):
    """Drum 1's step view (stock's), its shown pattern emptied, 16 steps. Returns the pattern."""
    h.leds()
    h.press(4)
    p = h.shown_pattern(0)
    h.clear_pattern(0, p, last=15)
    return p


def test_drum_write_relights_and_survives_stock_edits(pl17_image, pl17_manifest):
    """Spike 1 A2 and C: after a Write the step pads light as for the same steps entered by stock's own pad presses; a
    stock step press and a Velocity-view edit later keep every other hit of ours (the store holds them)."""
    h = DrumHarness(pl17_image, pl17_manifest)
    p = drum1_cleared(h)
    open_tools(h, 0)
    pick(h, 4)
    pick(h, HARD)
    write(h)
    hits = model(h, 0, 16)
    h.press(4)                                                         # Drum 1: the page closes, stock's step view
    assert h.r8(sym(h.m, "chord_page")) == 0xFF
    ref = DrumHarness(pl17_image, pl17_manifest)
    assert drum1_cleared(ref) == p
    for s in range(16):
        if hits >> s & 1:
            ref.pad(s)
    assert ref.pattern_hits(0, p) == {s: (0x60, 1) for s in range(16) if hits >> s & 1}
    assert h.leds()[:16] == ref.leds()[:16]
    ours = h.pattern_hits(0, p)
    assert ours == {s: (127, 1) for s in range(16) if hits >> s & 1}
    empty = next(s for s in range(16) if not hits >> s & 1)
    h.pad(empty)                                                       # a stock step press: a hit there
    assert h.pattern_hits(0, p) == {**ours, empty: (0x60, 1)}
    h.press(VEL_BTN)                                                   # the Velocity view: step pads on top
    sel = next(s for s in range(16) if hits >> s & 1)
    h.pad(sel)                                                         # selects one of ours
    h.pad(16 + 2)                                                      # a velocity for it
    after = h.pattern_hits(0, p)
    assert after[sel][0] != 127 and after[sel][1] == 1
    assert {s: v for s, v in after.items() if s != sel} == {s: v for s, v in {**ours, empty: (0x60, 1)}.items() if s != sel}
    assert h.store_bytes(0) == img(h, 0, p)


def test_drum_accent_and_combine_accent(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    open_tools(h, 0)
    p = h.shown_pattern(0)
    pick(h, 7)                                                         # 8 hits: every other step
    h.press(DOWN)                                                      # Pattern tools 2
    pick(h, ACCENT)
    pick(h, ACCENT)                                                    # on the beat
    assert accent(h, 0) == 2
    write(h)
    hits = model(h, 0, 16)
    hard = mm.hard_hits(2 << 6, hits, 0, 16)
    assert hard == hits & 0x1111 == 0x1111                              # steps 0, 4, 8, 12
    assert img(h, 0, p) == drum_image(hits, 16, 0, 96, ROLL_MICRO[0], hard)

    h = DrumHarness(pl17_image, pl17_manifest)
    open_tools(h, 0)
    pick(h, 7)
    h.press(DOWN)
    pick(h, 2)                                                         # second rhythm: 3 hits
    pick(h, 23)                                                        # combine accent
    write(h)
    hits, second = model(h, 0, 16), mm.second_rhythm(rcfg(h, 0), 16)
    hard = mm.hard_hits(0, hits, 0, 16, second)
    assert hard and hard != hits
    assert img(h, 0, p) == drum_image(hits, 16, 0, 96, ROLL_MICRO[0], hard)


def test_drum_undo_swaps(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    open_tools(h, 0)
    p = h.shown_pattern(0)
    before = img(h, 0, p)
    assert h.store_bytes(0) == before and h.leds()[UNDO] == 0
    pick(h, 4)
    write(h)
    written = img(h, 0, p)
    assert written != before and h.leds()[UNDO] == BLUE
    pick(h, UNDO)
    assert img(h, 0, p) == before and h.store_bytes(0) == before
    pick(h, UNDO)                                                      # again: redo
    assert img(h, 0, p) == written and h.store_bytes(0) == written
    assert h.r8(sym(h.m, "euclid_undo_at")) == 0 and undo_at(h)[0] == 1 + p


def test_drum_draft(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    open_tools(h, 0)
    p = h.shown_pattern(0)
    before = img(h, 0, p)
    pick(h, 4)
    pick(h, GROOVE)
    write(h)
    assert draft(h) == 5 and h.leds()[WRITE] == ORANGE
    five = img(h, 0, p)
    assert five == drum_image(model(h, 0, 16), 16, 0, 96, ROLL_MICRO[0], 0)
    h.down(6)                                                          # 7 hits: the re-write waits for the release
    assert img(h, 0, p) == five
    h.up(6)
    seven = drum_image(model(h, 0, 16), 16, 0, 96, ROLL_MICRO[0], 0)
    assert img(h, 0, p) == seven != five and h.store_bytes(0) == seven
    assert bytes(h.uc.mem_read(sym(h.m, "drum_undo_steps"), 0x80)) == before   # the copy is the pre-draft pattern
    h.press(DOWN)                                                      # Pattern tools 2: its picks re-write too
    pick(h, ACCENT)                                                    # first hit
    hits = model(h, 0, 16)
    assert img(h, 0, p) == drum_image(hits, 16, 0, 96, ROLL_MICRO[0], mm.hard_hits(1 << 6, hits, 0, 16))
    pick(h, UNDO)
    assert img(h, 0, p) == before and h.store_bytes(0) == before
    assert draft(h) == 0 and h.leds()[WRITE] == ORANGE_D
    write(h)                                                           # a new draft
    assert draft(h) == 5
    h.press(4)                                                         # Drum 1: the page closes, the draft ends
    assert draft(h) == 0


def chain_on(h, follow):
    """Drum 1's step view; Shift + Patterns when not following (stock's editors then stay on their pattern); 240 BPM;
    drum 1 chained from its pattern p to p + 1. Returns p."""
    from notes import param
    h.leds()
    h.press(4)
    if not follow:
        h.press(PATTERNS_BTN, shift=True)
    assert param(h, FOLLOW, 0) == (0 if follow else 1)
    set_tempo(h, bpm=BPM, swing=50)
    p = h.playing_pattern(0)
    assert p < 7 and h.shown_pattern(0) == p
    h.set_chain(0, p, p + 1)
    return p


def play_until_moves(h, p):
    h.press(PLAY_BTN)
    for _ in range(3000):
        h.heartbeat(1)
        if h.playing_pattern(0) != p:
            return
    raise AssertionError("the chain never moved on")


def test_drum_write_targets_the_shown_pattern(pl17_image, pl17_manifest):
    """Stock's editors not following (Shift + Patterns): the chain plays pattern p + 1, the editor still shows p; the
    Write lands in p, through the store, and p + 1 is unchanged."""
    h = DrumHarness(pl17_image, pl17_manifest)
    p = chain_on(h, follow=False)
    open_tools(h, 0)
    pick(h, 4)
    play_until_moves(h, p)
    assert (h.playing_pattern(0), h.shown_pattern(0)) == (p + 1, p)
    nxt = img(h, 0, p + 1)
    first, n = span(h, 0)
    write(h)
    want = drum_image(model(h, 0, n), n, first, 96, ROLL_MICRO[0], 0)
    assert img(h, 0, p) == want and h.store_bytes(0) == want and img(h, 0, p + 1) == nxt
    assert undo_at(h)[0] == 1 + p


def test_note_and_drum_undo_apart(pl17_image, pl17_manifest):
    """Review focus: Write on Synth 1, Write on Drum 1, Undo on Synth 1 -> Synth 1's pattern back, drum 1's still
    written; Undo on Drum 1 -> drum 1's back. A drum Write or Undo never changes euclid_undo_at / euclid_undo_steps."""
    from test_euclid import open_tools as note_tools, steps
    m = pl17_manifest
    h = DrumHarness(pl17_image, m)

    def note_copy():
        return h.r8(sym(m, "euclid_undo_at")), bytes(h.uc.mem_read(sym(m, "euclid_undo_steps"), 0x380))
    note_tools(h, 0)
    note_before = steps(h, 0)
    pick(h, 4)
    write(h)
    assert steps(h, 0) != note_before
    copy = note_copy()
    open_tools(h, 0)
    p = h.shown_pattern(0)
    drum_before = img(h, 0, p)
    pick(h, 4)
    write(h)
    drum_written = img(h, 0, p)
    assert drum_written != drum_before and note_copy() == copy
    note_tools(h, 0)
    pick(h, UNDO)
    assert steps(h, 0) == note_before and img(h, 0, p) == drum_written
    open_drum(h, 0)                                                    # back on its last page: Pattern tools
    assert drum_page(h, 0) == TOOLS and h.leds()[UNDO] == BLUE
    note_copy_after = note_copy()
    pick(h, UNDO)
    assert img(h, 0, p) == drum_before and h.store_bytes(0) == drum_before and steps(h, 0) == note_before
    assert note_copy() == note_copy_after


def test_drum_draft_after_the_shown_pattern_moves(pl17_image, pl17_manifest):
    """Review focus: a draft on pattern p, then the shown pattern moves (a chain with follow on: a Patterns-view pick
    leaves the page's track off screen, and the next pad press there closes the page and ends the draft). A pick
    re-writes p raw; p + 1 and the store, now p + 1's, are unchanged."""
    h = DrumHarness(pl17_image, pl17_manifest)
    p = chain_on(h, follow=True)
    open_tools(h, 0)
    pick(h, 4)
    pick(h, GROOVE)
    write(h)
    assert draft(h) == 5
    play_until_moves(h, p)
    assert h.shown_pattern(0) == p + 1 and h.r8(sym(h.m, "chord_page")) == 4
    nxt, store = img(h, 0, p + 1), h.store_bytes(0)
    assert store == nxt
    pick(h, 6)                                                         # 7 hits
    a = h.base(0) + PAT * p                                            # the draft's pattern and its steps
    last, lo = h.r8(a + 0x80) % 32, h.r8(a + 0x81) % 32
    first, n = min(lo, last), abs(last - lo) + 1
    assert img(h, 0, p) == drum_image(model(h, 0, n), n, first, 96, ROLL_MICRO[0], 0)
    assert img(h, 0, p + 1) == nxt and h.store_bytes(0) == store and draft(h) == 5


def test_link_write_ends_a_drum_draft(pl17_image, pl17_manifest):
    from test_link import DrumLink, write as link_write
    h = DrumLink(pl17_image, pl17_manifest)
    open_tools(h, 1)                                                   # Drum 2
    p = h.shown_pattern(1)
    pick(h, 4)
    pick(h, GROOVE)
    write(h)
    assert draft(h) == 6 and h.leds()[WRITE] == ORANGE
    written = img(h, 1, p)
    h.hello()
    link_write(h, 87 + 2 * 2, [0x27])                                  # drum 3's hits: drum 2's draft stays
    h.frame()
    assert ecfg(h, 2)[0] == 0x27 and draft(h) == 6 and h.leds()[WRITE] == ORANGE
    link_write(h, 87 + 2 * 1, [0xA7])                                  # drum 2's: 7 hits, groove; its draft ends
    h.frame()
    assert ecfg(h, 1)[0] == 0xA7 and draft(h) == 0 and h.leds()[WRITE] == ORANGE_D
    assert img(h, 1, p) == written                                     # ended, not re-written
    pick(h, 5)
    assert img(h, 1, p) == written                                     # a pick no longer re-writes


def test_project_load_drops_drum_undo_and_draft(pl17_image, pl17_manifest):
    """Review focus: a project load with a drum draft live and its re-write pending (the pad held): the draft ends,
    every drum_undo_at is 0, and the pad's release writes nothing."""
    from test_saved import load
    h = DrumHarness(pl17_image, pl17_manifest)
    open_tools(h, 1)
    pick(h, 4)
    write(h)                                                           # drum 2: an Undo copy, no draft
    open_tools(h, 0)
    p = h.shown_pattern(0)
    pick(h, 4)
    pick(h, GROOVE)
    write(h)
    assert draft(h) == 5 and undo_at(h)[:2] == bytes([1 + p, 1 + h.shown_pattern(1)])
    h.down(6)                                                          # 7 hits: the re-write waits for the release
    load(h)
    h.leds()
    loaded = img(h, 0, p)
    h.up(6)
    assert draft(h) == 0 and undo_at(h) == bytes(4) and img(h, 0, p) == loaded
    open_tools(h, 0)
    assert h.leds()[UNDO] == 0
    pick(h, UNDO)
    assert img(h, 0, p) == loaded


def test_unexpected_recorder_writes_nothing(pl17_image, pl17_manifest):
    """Review focus: drum 1's recorder is not a drum recorder (its vtable word overwritten): no preview, Write dark, the
    armed Write's release, Undo, the rotate and dice pads change nothing in the record and divide by nothing."""
    h = DrumHarness(pl17_image, pl17_manifest)
    open_tools(h, 0)
    pick(h, 4)
    pick(h, WRITE)
    assert h.leds()[WRITE] == ARMED
    rec = h.r32(SESSION + 0x14)
    record = bytes(h.uc.mem_read(rec, RECORD_SIZE))
    h.uc.mem_write(h.recorder(0), bytes(4))
    leds = h.leds()
    assert leds[:16] == [0] * 16 and leds[WRITE] == 0
    pick(h, WRITE)                                                     # the armed Write's second press
    pick(h, 6)                                                         # a hits pick still sets the hits
    assert ecfg(h, 0)[0] & 0x1F == 7
    fields = drum_fields(h)
    for pad in (16, 17, 28, UNDO):                                     # rotate, dice: no steps to work over
        pick(h, pad)
    h.press(DOWN)                                                      # Pattern tools 2
    for pad in (16, 17, 28):
        pick(h, pad)
    write(h)
    assert drum_fields(h) == fields and h.leds()[:16] == [0] * 16
    assert bytes(h.uc.mem_read(rec, RECORD_SIZE)) == record and undo_at(h) == bytes(4)


def test_masked_section_is_short(pl17_image, pl17_manifest):
    """As the note tracks' (test_melody's test_the_line_is_worked_out_before_interrupts_are_masked): the rhythm is
    worked out before slim_irq_save; with interrupts masked only the 128 B and the store's 64 words are written; stock's
    store calls (touch all, commit: the listeners redraw views) run after, unmasked, on drum 1's store."""
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_PRIMASK, UC_ARM_REG_R0
    m = pl17_manifest
    h = DrumHarness(pl17_image, m)
    open_tools(h, 0)
    pick(h, 4)
    pick(h, GROOVE)
    calls = []
    for name, a in (("drum_write_to", sym(m, "drum_write_to")), ("euclid_hits", sym(m, "euclid_hits")),
                    ("melody_groove", sym(m, "melody_groove")), ("slim_irq_save", sym(m, "slim_irq_save")),
                    ("slim_irq_restore", sym(m, "slim_irq_restore")), ("store_touch_all", STORE_TOUCH_ALL),
                    ("store_commit", STORE_COMMIT)):
        a &= ~1
        h.uc.hook_add(UC_HOOK_CODE, lambda uc, addr, size, d, name=name: calls.append(
            (name, uc.reg_read(UC_ARM_REG_PRIMASK) & 1, uc.reg_read(UC_ARM_REG_R0))), begin=a, end=a)
    write(h)
    names = [c[0] for c in calls]
    calls = calls[names.index("drum_write_to"):]
    names = [c[0] for c in calls]
    save, restore = names.index("slim_irq_save"), names.index("slim_irq_restore")
    assert {"euclid_hits", "melody_groove"} <= set(names[:save])
    assert names[save + 1:restore] == []                               # nothing hooked runs masked
    assert all(not masked for name, masked, _ in calls if name != "slim_irq_restore"), calls
    store = h.r32(h.recorder(0) + 0x4C)
    stock = [(name, r0) for name, _, r0 in calls[restore:] if name.startswith("store_")]
    assert stock[:2] == [("store_touch_all", store), ("store_commit", store)]
    assert draft(h) == 5


# ---- A Write while recording (Task 4) ----

REC_WRITE = 0x0803FA26                                                 # the drum recorder's write(drec, pattern, step, micro)
PENDING = 0x54                                                         # drec + 0x54: the pending velocity (0 = nothing to record)


def put(h, d=0, keep_undo=0):
    """Steps 1-2 of the Write (drum_put): the step store to refresh, or 0."""
    h.call(sym(h.m, "drum_put"), d, 0xFF, keep_undo)
    return h.uc.reg_read(UC_ARM_REG_R0)


def refresh(h, store):
    h.call(sym(h.m, "drum_refresh"), store)


def rec_hit(h, d, step, vel, micro, p=None):
    """The recorder's write of a hit (what a played pad leaves pending): velocity vel on `step`, micro bit `micro`,
    into pattern p (the shown one). The pending velocity is cleared by the write."""
    dr = h.recorder(d)
    h.uc.mem_write(dr + PENDING, bytes([vel]))
    h.call(REC_WRITE, dr, h.shown_pattern(d) if p is None else p, step, micro)
    assert h.r8(dr + PENDING) == 0


def recording_drum1(h):
    """Record armed, playing, drum 1's page on Pattern tools with 5 hits; the first step no Write of it hits."""
    drum_setup(h)
    h.press(PLAY_BTN)
    h.heartbeat(1)
    assert h.transport()[:2] == (1, 1)
    open_tools(h, 0)
    pick(h, 4)
    want = drum_image(model(h, 0, 32), 32, 0, 96, ROLL_MICRO[0], 0)
    return want, next(s for s in range(32) if not want[s])


def test_recorder_commit_between_put_and_refresh(pl17_image, pl17_manifest):
    h = DrumHarness(pl17_image, pl17_manifest)
    want, step = recording_drum1(h)
    p = h.shown_pattern(0)
    store = put(h)
    assert store == h.r32(h.recorder(0) + 0x4C) and img(h, 0, p) == want   # written and mirrored, not yet committed
    rec_hit(h, 0, step, 90, 2)                                         # the recorder commits in between (Main)
    refresh(h, store)
    hit = bytearray(want)
    hit[step], hit[0x60 + step] = 90, 1 << 2
    assert img(h, 0, p) == bytes(hit) and h.store_bytes(0) == bytes(hit)   # the image plus that hit
    h.press(4)                                                         # stock's step view
    other = next(s for s in range(32) if hit[s] == 0 and s != step)
    h.pad(other)                                                       # a stock step press: its commit writes the store
    after = h.pattern_hits(0, p)
    assert after[step] == (90, 4) and after[other][0] != 0
    assert {s: v for s, v in after.items() if s != other} == {s: (hit[s], hit[0x60 + s]) for s in range(32) if hit[s]}


@pytest.mark.parametrize("before", [True, False], ids=["before the Write", "after the Write"])
def test_recorder_commit_before_and_after_a_write(pl17_image, pl17_manifest, before):
    h = DrumHarness(pl17_image, pl17_manifest)
    want, step = recording_drum1(h)
    p = h.shown_pattern(0)
    if before:
        rec_hit(h, 0, step, 90, 2)
    write(h)
    if not before:
        rec_hit(h, 0, step, 90, 2)
    got = img(h, 0, p)
    if before:
        assert got == want                                             # the Write replaced it
    else:
        hit = bytearray(want)
        hit[step], hit[0x60 + step] = 90, 1 << 2
        assert got == bytes(hit)                                       # the hit was added to the written image
    assert h.store_bytes(0) == got


def test_write_while_recording_repeats(pl17_image, pl17_manifest):
    """Latched drum 1 at 1/16 records a hit a step while a Write rewrites drum 2's pattern."""
    h = DrumHarness(pl17_image, pl17_manifest)
    p1 = drum_setup(h)
    pick(h, 2)                                                         # rate 1/16
    pick(h, 15)                                                        # latch
    h.press(PLAY_BTN)
    h.heartbeat(1)
    h.until_tick(12)                                                   # 6 ticks a step at 1/16: tick 12 = step 2
    pick(h, DRUM_PAD)                                                  # drum 1 latched: it repeats from here on
    h.until_tick(30)                                                   # step 5, the repeat is well under way
    open_tools(h, 1)                                                   # Drum 2's Pattern tools
    pick(h, 3)                                                         # 4 hits
    p2 = h.shown_pattern(1)
    mark = len(h.sent)
    write(h)                                                           # while drum 1 repeats
    h.until_tick(100)                                                  # past tick 96, the end of step 16
    hits = model(h, 1, 32)
    assert img(h, 1, p2) == drum_image(hits, 32, 0, 96, ROLL_MICRO[0], 0) and h.store_bytes(1) == img(h, 1, p2)
    on = on_ticks(h, 0, mark)
    assert on                                                          # drum 1 kept sounding through the Write
    assert on == list(range(on[0], 100, 6))                            # a hit every step, none lost
    rec = h.pattern_hits(0, p1)
    assert all(s in rec for s in range(2, 17))                         # drum 1 recorded each step from the tap on
    assert all(rec[s][1] == 0x01 for s in range(2, 17))                # one hit a step (micro mask 0x01)
    assert all(rec[s][0] == rec[2][0] for s in range(2, 17))           # all with step 2's velocity


# ---- PL20 (trig conditions, Task 9): a Write starts clean -------------------------------------------------------------

def cond_bytes(h, d, p):
    """Drum d's pattern p: its 36 condition bytes (+ 0x84 .. + 0xA7)."""
    return bytes(h.uc.mem_read(h.base(d) + PAT * p + 0x84, 0x24))


@pytest.mark.parametrize("mark", [1, 0], ids=["marked", "unmarked"])
def test_write_clears_conditions_and_undo_restores(pl21_image, pl21_manifest, mark):
    """Marked: Drum 1's Write zeroes the written pattern's 36 condition bytes, Undo brings the old codes back, redo
    zeroes them again; the other patterns keep theirs. Unmarked: the bytes are not conditions and stay (as PL19)."""
    m = pl21_manifest
    h = DrumHarness(pl21_image, m)
    open_tools(h, 0)
    p = h.shown_pattern(0)
    for d in range(2):
        for q in range(8):
            h.uc.mem_write(h.base(d) + PAT * q + 0x84, bytes((0x5A + 3 * k + 7 * q + d) & 0xFF for k in range(0x24)))
    h.uc.mem_write(sym(m, "trig_mark"), bytes([mark]))
    old = cond_bytes(h, 0, p)
    others = {(d, q): cond_bytes(h, d, q) for d in range(2) for q in range(8) if (d, q) != (0, p)}
    pick(h, 4)
    write(h)
    written = img(h, 0, p)
    assert cond_bytes(h, 0, p) == (bytes(0x24) if mark else old)
    pick(h, UNDO)
    assert img(h, 0, p) != written and cond_bytes(h, 0, p) == old
    pick(h, UNDO)                                                      # again: redo
    assert img(h, 0, p) == written and cond_bytes(h, 0, p) == (bytes(0x24) if mark else old)
    assert {k: cond_bytes(h, *k) for k in others} == others
