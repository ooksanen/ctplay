"""The play pages (spec 2026-10-17-play-pages-design.md section 1): Shift + a track's button opens its last page
(Chords, Arp); ▲ ▼ step pages; Shift held on a page shows the table of contents. PL16 (spec 2026-10-25-drums-design.md):
Shift + Drum 1-4 opens the drum's page (Repeat), from the drums' own page list."""
import pytest
from unicorn.arm_const import UC_ARM_REG_R0

from harness import MGR
from notes import CONT, NOTE_DEFAULT, NOTE_EXPANDED, NoteHarness, pattern_snapshot

pytestmark = pytest.mark.emu
CLOSED = 0xFF
CHORDS, ARP, TOOLS, MELODY, KEYS = 0, 1, 2, 3, 7                                # the page = its pad in the page list (25 + page)
DOWN, UP = 19, 20                                                      # Octave ▼ = next page, ▲ = previous
LED_DOWN, LED_UP = 51, 52
GREEN, GREEN_D, BLUE, BLUE_D, MAG, MAG_D, ORANGE, ORANGE_D, WHITE, WHITE_D = 0x17, 0x18, 0x07, 0x08, 0x32, 0x38, 0x45, 0x46, 0x01, 0x02
YELLOW, YELLOW_D = 0x2D, 0x2E                                         # the Melody page (PL13)
CYAN, CYAN_D = 0x4D, 0x4E                                             # the Repeat page's unquantized toggle (PL16)
TRACK_OF = 0x0805011E                                                 # stock: container -> selected track 0-7


def sym(m, name):
    return int(m["symbols"][name], 16)


def page(h, m):
    return h.r8(sym(m, "chord_page"))


def last(h, m, t):
    return h.r8(sym(m, "page_slot") + t)


def arp(h, m, t):
    a = sym(m, "chord_arp") + 2 * t
    return h.r8(a), h.r8(a + 1)


def open_page(h, t):
    h.press(t, shift=True)


def open_arp(h, t):
    open_page(h, t)
    h.press(DOWN)


def pick(h, pad):
    h.down(pad)
    h.up(pad)


def played(h):
    return h.take("synth_on", "midi_on")


@pytest.mark.parametrize("mode", [NOTE_DEFAULT, NOTE_EXPANDED])
def test_shift_track_opens_its_page_and_the_button_closes_it(pl09_image, pl09_manifest, mode):
    h = NoteHarness(pl09_image)
    h.track(1, mode)
    shape = h.shape()
    open_page(h, 1)
    assert page(h, pl09_manifest) == 1 and h.shape() == shape          # same view, page open
    open_page(h, 1)
    assert page(h, pl09_manifest) == 1                                 # pressed again: stays open
    h.press(1)
    assert page(h, pl09_manifest) == CLOSED


def test_shift_track_opens_its_last_page(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    open_page(h, 0)
    assert last(h, pl09_manifest, 0) == CHORDS                         # power-on: Chords
    h.press(DOWN)
    h.press(0)
    open_page(h, 0)
    assert last(h, pl09_manifest, 0) == ARP and h.leds()[0] == GREEN   # Arp: its pattern row, off selected
    open_page(h, 2)
    assert page(h, pl09_manifest) == 2 and last(h, pl09_manifest, 2) == CHORDS


def test_down_and_up_step_pages(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    h.down(24)
    note = played(h)
    h.up(24)
    snap = pattern_snapshot(h, 0)
    open_page(h, 0)
    leds = h.leds()
    assert (leds[LED_DOWN], leds[LED_UP]) == (BLUE, 0)                  # on Chords: Arp is next
    h.press(DOWN)
    assert last(h, pl09_manifest, 0) == ARP
    leds = h.leds()
    assert (leds[LED_DOWN], leds[LED_UP]) == (ORANGE, GREEN)           # on Arp: Pattern tools next, Chords previous
    h.press(DOWN)
    assert last(h, pl09_manifest, 0) == TOOLS
    leds = h.leds()
    assert (leds[LED_DOWN], leds[LED_UP]) == (ORANGE, BLUE)            # its page 2 next (PL14), then Melody, Phrasing, Keys
    h.press(DOWN)
    assert last(h, pl09_manifest, 0) == TOOLS
    h.press(DOWN)
    assert last(h, pl09_manifest, 0) == MELODY
    h.press(DOWN)
    assert last(h, pl09_manifest, 0) == MELODY                         # Phrasing (PL14)
    h.press(DOWN)
    assert last(h, pl09_manifest, 0) == KEYS                           # the empty pads 29-31 are skipped; no wrap
    leds = h.leds()
    assert (leds[LED_DOWN], leds[LED_UP]) == (0, YELLOW)
    for _ in range(6):
        h.press(UP, shift=True)                                        # taken with Shift too: no pattern transpose
    assert last(h, pl09_manifest, 0) == CHORDS
    h.press(UP)
    assert last(h, pl09_manifest, 0) == CHORDS
    h.press(0)                                                         # close
    assert pattern_snapshot(h, 0) == snap
    h.down(24)
    assert played(h) == note                                           # same octave
    h.up(24)


def test_table_of_contents(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    open_page(h, 0)
    before = (arp(h, pl09_manifest, 0), h.r8(sym(pl09_manifest, "chord_settings")), h.r8(sym(pl09_manifest, "chord_strum")))
    h.shift(True)
    leds = h.leds()
    assert leds[:24] == [0] * 24 and leds[24:32] == [GREEN, BLUE_D, ORANGE_D, YELLOW_D, 0, 0, 0, MAG_D]
    for pad in range(28, 31):                                          # pads 29-31: no page
        pick(h, pad)
    for pad in (0, 16, 30):                                            # no setting with Shift held
        pick(h, pad)
    assert last(h, pl09_manifest, 0) == CHORDS
    pick(h, 25)                                                        # pad 26: Arp
    assert last(h, pl09_manifest, 0) == ARP and h.leds()[24:26] == [GREEN_D, BLUE]
    h.shift(False)
    after = (arp(h, pl09_manifest, 0), h.r8(sym(pl09_manifest, "chord_settings")), h.r8(sym(pl09_manifest, "chord_strum")))
    assert after == before and played(h) == []


def test_keys_page(pl19_image, pl19_manifest):
    """The Keys page is one toggle per setting: pad 1 mono record, pad 2 step-entry chords (PL18); pads 3-4 pattern
    strum, played / written, one of two (PL19)."""
    m = pl19_manifest
    h = NoteHarness(pl19_image)
    ready(h, m)
    h.track(2)
    mono, step, ps = sym(m, "chord_mono"), sym(m, "chord_step"), sym(m, "chord_pstrum")
    open_page(h, 2)
    for _ in range(6):
        h.press(DOWN)                                                  # Arp, Pattern tools 1 / 2, Melody, Phrasing, Keys: the last page
    assert last(h, m, 2) == KEYS
    leds = h.leds()
    assert leds[:32] == [MAG_D, GREEN_D, WHITE_D, WHITE_D] + [0] * 28 and (leds[LED_DOWN], leds[LED_UP]) == (0, YELLOW)   # all off
    pick(h, 0)
    assert (h.r8(mono), h.r8(step)) == (0b100, 0) and h.leds()[:2] == [MAG, GREEN_D]
    pick(h, 0)
    assert (h.r8(mono), h.r8(step)) == (0, 0) and h.leds()[:2] == [MAG_D, GREEN_D]
    pick(h, 1)
    assert (h.r8(mono), h.r8(step)) == (0, 0b100) and h.leds()[:2] == [MAG_D, GREEN]
    pick(h, 1)
    assert (h.r8(mono), h.r8(step)) == (0, 0) and h.leds()[:2] == [MAG_D, GREEN_D]
    pick(h, 0)
    pick(h, 1)
    for pad in range(4, 32):                                           # pads 5-32: nothing
        pick(h, pad)
    assert (h.r8(mono), h.r8(step), h.r8(ps)) == (0b100, 0b100, 0) and h.leds()[4:32] == [0] * 28
    # Pattern strum (PL19): pad 3 played, pad 4 written; a press on the unlit one picks it, on the lit one sets off.
    pick(h, 2)
    assert (h.r8(ps) >> 4) & 3 == 1 and h.leds()[2:4] == [WHITE, WHITE_D]
    pick(h, 3)
    assert (h.r8(ps) >> 4) & 3 == 2 and h.leds()[2:4] == [WHITE_D, WHITE]
    pick(h, 3)
    assert h.r8(ps) == 0 and h.leds()[2:4] == [WHITE_D, WHITE_D]
    pick(h, 2)
    pick(h, 2)
    assert h.r8(ps) == 0 and h.leds()[2:4] == [WHITE_D, WHITE_D]
    assert (h.r8(mono), h.r8(step)) == (0b100, 0b100)               # the other settings kept
    h.shift(True)
    assert h.leds()[24:32] == [GREEN_D, BLUE_D, ORANGE_D, YELLOW_D, 0, 0, 0, MAG]
    pick(h, 24)
    assert last(h, m, 2) == CHORDS
    pick(h, 31)                                                        # pad 32: Keys
    assert last(h, m, 2) == KEYS
    h.shift(False)
    assert (h.r8(mono), h.r8(step)) == (0b100, 0b100) and played(h) == [] and h.sounding == set()


def test_pattern_strum_is_per_track(pl19_image, pl19_manifest):
    """PL19: track 1's pads change only its two bits (PSTRUM_OF(1) = bits 2-3)."""
    m = pl19_manifest
    h = NoteHarness(pl19_image)
    ready(h, m)
    ps = sym(m, "chord_pstrum")
    h.track(1)
    open_page(h, 1)
    for _ in range(6):
        h.press(DOWN)
    assert last(h, m, 1) == KEYS
    assert h.leds()[:4] == [MAG_D, GREEN_D, WHITE_D, WHITE_D] and h.leds()[4:32] == [0] * 28
    pick(h, 2)
    assert h.r8(ps) == 1 << 2 and h.leds()[2:4] == [WHITE, WHITE_D]
    pick(h, 3)
    assert h.r8(ps) == 2 << 2 and h.leds()[2:4] == [WHITE_D, WHITE]
    h.track(0)
    open_page(h, 0)
    for _ in range(6):
        h.press(DOWN)
    assert h.leds()[2:4] == [WHITE_D, WHITE_D]                          # track 1's choice does not show on track 0
    pick(h, 2)
    assert h.r8(ps) == (2 << 2 | 1)


def ready(h, m):
    """slim's power-on init runs at the first LED refresh in the emulator, and resets chord_voice: do it first."""
    h.leds()


def settings(h, m, t=0):
    return h.r8(sym(m, "chord_settings") + t), h.r8(sym(m, "chord_voice") + t)


def test_chords_page_pads(pl15_image, pl15_manifest):
    m = pl15_manifest
    h = NoteHarness(pl15_image)
    h.track(0)
    ready(h, m)
    open_page(h, 0)
    leds = h.leds()[:32]
    assert leds[0] == GREEN and leds[1:13] == [GREEN_D] * 12 and leds[13:16] == [0, 0, 0]   # off is lit (shape 0)
    assert leds[16:20] == [BLUE, BLUE_D, BLUE_D, BLUE_D] and leds[20:23] == [MAG, MAG_D, MAG_D]
    assert leds[23] == ORANGE_D and leds[24:27] == [BLUE_D] * 3 and leds[27:30] == [WHITE_D] * 3
    assert leds[30:32] == [WHITE, WHITE_D]
    for pad in range(8):                                               # row 1: shapes 0-7
        pick(h, pad)
        s, v = settings(h, m)
        assert s & 7 == pad and v & 15 == 0
        want = [GREEN if c == pad else GREEN_D for c in range(13)]
        assert h.leds()[:13] == want, pad
    for pad in range(8, 13):                                           # row 2: only that pad of rows 1-2
        pick(h, pad)
        s, v = settings(h, m)
        assert s & 7 == 0 and v & 15 == pad - 7
        assert h.leds()[:13] == [GREEN if c == pad else GREEN_D for c in range(13)], pad
    pick(h, 3)
    assert settings(h, m)[1] & 15 == 0                                 # a row-1 pick ends the row-2 shape
    before = (settings(h, m), h.leds()[:32])
    for pad in (13, 14, 15):
        pick(h, pad)
    assert (settings(h, m), h.leds()[:32]) == before and h.leds()[13:16] == [0, 0, 0]
    for pad in range(16, 20):
        pick(h, pad)
        assert settings(h, m)[0] >> 3 & 3 == pad - 16
        assert h.leds()[16:20] == [BLUE if c == pad - 16 else BLUE_D for c in range(4)]
    for pad in range(20, 23):
        pick(h, pad)
        assert settings(h, m)[0] >> 5 & 3 == pad - 20
        assert h.leds()[20:23] == [MAG if c == pad - 20 else MAG_D for c in range(3)]
    rootless = sym(m, "chord_rootless")
    for want in [(1, 0, ORANGE), (1, 1, WHITE), (0, 0, ORANGE_D)]:    # bass cycle
        pick(h, 23)
        assert (settings(h, m)[0] >> 7 & 1, h.r8(rootless) & 1, h.leds()[23]) == want
    assert played(h) == [] and h.sounding == set()


def test_chords_page_other_tracks_untouched(pl15_image, pl15_manifest):
    h = NoteHarness(pl15_image)
    h.track(1)
    ready(h, pl15_manifest)
    open_page(h, 1)
    pick(h, 9)
    pick(h, 25)
    assert settings(h, pl15_manifest, 1)[1] == 2 | 2 << 4 and settings(h, pl15_manifest, 0)[1] == 0


def test_voice_leading_pads(pl15_image, pl15_manifest):
    m = pl15_manifest
    h = NoteHarness(pl15_image)
    h.track(0)
    ready(h, m)
    open_page(h, 0)
    pick(h, 17)                                                        # inversion 1
    for n, pad in enumerate((24, 25, 26), 1):
        pick(h, pad)
        assert settings(h, m)[1] >> 4 & 3 == n
        assert h.leds()[24:27] == [BLUE if c + 1 == n else BLUE_D for c in range(3)]
        assert h.leds()[16:20] == [0, BLUE_D, 0, 0]                    # on: the stored inversion dim, the rest dark
    pick(h, 26)                                                        # the lit one again
    assert settings(h, m)[1] >> 4 & 3 == 0 and h.leds()[24:27] == [BLUE_D] * 3
    assert h.leds()[16:20] == [BLUE_D, BLUE, BLUE_D, BLUE_D]
    pick(h, 25)
    pick(h, 19)                                                        # an inversion press: voice leading off, picked
    s, v = settings(h, m)
    assert s >> 3 & 3 == 3 and v >> 4 & 3 == 0
    assert h.leds()[16:20] == [BLUE_D] * 3 + [BLUE]
    assert played(h) == []


def test_strum_none_lit_is_off(pl15_image, pl15_manifest):
    m = pl15_manifest
    h = NoteHarness(pl15_image)
    h.track(0)
    ready(h, m)
    open_page(h, 0)
    strum = sym(m, "chord_strum")
    for pad in (27, 28, 29):
        pick(h, pad)
        assert h.r8(strum) & 3 == pad - 26
        assert h.leds()[27:30] == [WHITE if c == pad - 27 else WHITE_D for c in range(3)]
    pick(h, 29)                                                        # the lit one again
    assert h.r8(strum) & 3 == 0 and h.leds()[27:30] == [WHITE_D] * 3
    pick(h, 28)
    h.press(DOWN)
    pick(h, 1)                                                         # pattern up
    h.press(UP)
    assert h.leds()[27:30] == [0, WHITE_D, 0]                          # ignored with a pattern on: stored speed dim
    pick(h, 28)                                                        # still works: off
    assert h.r8(strum) & 3 == 0 and h.leds()[27:30] == [0, 0, 0]
    assert played(h) == []


def test_strum_direction_pads(pl15_image, pl15_manifest):
    h = NoteHarness(pl15_image)
    h.track(1)
    ready(h, pl15_manifest)
    down = sym(pl15_manifest, "chord_strum_down")
    open_page(h, 1)
    assert h.leds()[30:32] == [WHITE, WHITE_D]                         # rising (the default) bright
    pick(h, 31)
    assert h.r8(down) == 0b10 and h.leds()[30:32] == [WHITE_D, WHITE]
    pick(h, 30)
    assert h.r8(down) == 0 and h.leds()[30:32] == [WHITE, WHITE_D]
    pick(h, 31)
    h.press(DOWN)
    pick(h, 1)                                                         # pattern up
    h.press(UP)
    assert h.leds()[30:32] == [0, WHITE_D]                             # ignored with a pattern on: stored one dim
    assert h.r8(down) == 0b10 and played(h) == []


def test_pads_pick_options_and_play_nothing(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(3)
    open_arp(h, 3)
    h.take()
    for pad, want in [(2, (0x02, 0x08)), (10, (0x12, 0x08)), (12, (0x32, 0x08)), (13, (0x52, 0x08)),
                      (12, (0x32, 0x08)), (12, (0x12, 0x08)), (15, (0x92, 0x08)), (19, (0x92, 0x0B)),
                      (20, (0x92, 0x07)), (22, (0x92, 0x07)), (7, (0x97, 0x07))]:
        pick(h, pad)
        assert arp(h, pl09_manifest, 3) == want, (pad, arp(h, pl09_manifest, 3), want)
    assert played(h) == [] and h.sounding == set()
    assert arp(h, pl09_manifest, 0) == (0, 0x08)                       # other tracks keep theirs (default gate 3/6)


def test_1_32_clears_dotted_and_dotted_does_nothing_with_it(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    open_arp(h, 0)
    pick(h, 13)                                                        # dotted
    pick(h, 11)                                                        # 1/32: dotted goes
    assert arp(h, pl09_manifest, 0)[0] == 3 << 3
    pick(h, 13)
    assert arp(h, pl09_manifest, 0)[0] == 3 << 3


def test_arp_page_leds(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    open_arp(h, 0)
    for pad in (3, 9, 13, 15, 17, 20):                                 # up-down, 1/8, dotted, latch, 2 octaves, gate 2/6
        pick(h, pad)
    lit = h.leds()[:32]
    assert lit[:8] == [GREEN_D] * 3 + [GREEN] + [GREEN_D] * 4
    assert lit[8:16] == [BLUE_D, BLUE, BLUE_D, BLUE_D, MAG_D, MAG, 0x00, ORANGE]
    assert lit[16:24] == [MAG_D, MAG, MAG_D, MAG_D, 0x67, 0, 0, 0]
    assert lit[24:32] == [0] * 8
    pick(h, 11)                                                        # 1/32: the dotted pad goes dark
    assert h.leds()[13] == 0x00


def test_gate_pad_cycles_like_stocks_gate_view(pl09_image, pl09_manifest):
    """Pad 21: one sixth down per press, 1/6 -> 6/6; stock's Gate-view colours 0x68 (1/6) ... 0x63 (6/6)."""
    h = NoteHarness(pl09_image)
    h.track(0)
    open_arp(h, 0)
    for want in (1, 0, 5, 4):
        pick(h, 20)
        assert arp(h, pl09_manifest, 0)[1] >> 2 & 7 == want
        assert h.leds()[20] == 0x68 - want
    before = arp(h, pl09_manifest, 0)
    for pad in (21, 22, 23):
        pick(h, pad)
        assert h.leds()[pad] == 0
    assert arp(h, pl09_manifest, 0) == before


def test_a_pad_held_across_a_page_change_keeps_its_release(pl09_image, pl09_manifest):
    """Review focus: the release of a pad the page took stays the page's, on whichever page is open by then."""
    h = NoteHarness(pl09_image)
    h.track(0)
    open_arp(h, 0)
    h.down(4)                                                          # down-up
    h.press(UP)                                                        # to Chords
    strum = h.r8(sym(pl09_manifest, "chord_strum"))
    h.up(4)
    assert h.r8(sym(pl09_manifest, "chord_strum")) == strum and played(h) == [] and h.sounding == set()


def test_shift_another_track_switches_like_a_plain_press(pl09_image, pl09_manifest, stock_image):
    a, b = NoteHarness(stock_image), NoteHarness(pl09_image)
    for h in (a, b):
        h.track(0)
        h.press(14)                                                    # from the Mixer
    a.press(2)
    open_page(b, 2)
    assert b.shape()[1] == a.shape()[1] and page(b, pl09_manifest) == 2


def test_shift_track_while_pads_are_held_leaves_nothing_on(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    h.uc.mem_write(sym(pl09_manifest, "chord_settings"), bytes([1]))   # triad on Synth 1
    h.down(24)
    assert h.sounding
    open_page(h, 1)                                                    # stock's view switch releases pad 24
    h.up(24)
    assert h.sounding == set()


@pytest.mark.parametrize("button", [9, 14, 15, 8])
def test_note_mixer_fx_preset_close_the_page(pl09_image, pl09_manifest, button):
    h = NoteHarness(pl09_image)
    h.track(0)
    open_page(h, 0)
    h.press(button)
    assert page(h, pl09_manifest) == CLOSED


def test_shift_drum_switches_like_a_plain_press(pl17_image, pl17_manifest, stock_image):
    """PL16: Shift + Drum N opens the drum's page in the view stock's own Drum N press gives (from the Mixer too)."""
    for start in (None, 14):
        for button in (4, 7):
            a, b = NoteHarness(stock_image), NoteHarness(pl17_image)
            for h in (a, b):
                h.track(0)
                if start is not None:
                    h.press(start)
            a.press(button)
            open_page(b, button)
            assert b.shape()[1] == a.shape()[1] and page(b, pl17_manifest) == button, (start, button)
            assert (b.view_mode(), track_of(b)) == (a.view_mode(), track_of(a)) == (1, button), (start, button)


def test_a_pad_held_across_opening_keeps_its_stock_release(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0, NOTE_EXPANDED)
    h.down(30)                                                         # a key: stock plays it
    assert h.sounding
    open_page(h, 0)
    h.up(30)
    assert h.sounding == set()


def test_a_pad_held_across_a_table_of_contents_change_keeps_its_release(pl09_image, pl09_manifest):
    """The table-of-contents half of the review focus: Shift + pad 25 while a page pad is held."""
    h = NoteHarness(pl09_image)
    h.track(0)
    open_arp(h, 0)
    h.down(4)                                                          # down-up
    h.shift(True)
    pick(h, 24)                                                        # pad 25: Chords
    h.shift(False)
    strum = h.r8(sym(pl09_manifest, "chord_strum"))
    h.up(4)
    assert last(h, pl09_manifest, 0) == CHORDS
    assert h.r8(sym(pl09_manifest, "chord_strum")) == strum and played(h) == [] and h.sounding == set()


def test_gate_colours_are_stocks_gate_view(pl09_image, pl09_manifest, stock_image):
    """Stock's Gate view (button 11, a step held) draws a 1-6 tick last pad; the gate pad shows the same code."""
    s = NoteHarness(stock_image)
    s.track(0)
    s.press(11)                                                        # Gate
    step4 = 0x20011B20 + 4 * 28                                        # Synth 1, pattern 0, step 5
    stock = []
    for ticks in range(1, 7):
        s.uc.mem_write(step4, bytes([1, 7, 0, 0, 48, ticks, 0, 96]))
        s.down(4)
        stock.append(s.leds()[16])                                     # the step's first gate pad
        s.up(4)
    h = NoteHarness(pl09_image)
    h.track(0)
    open_arp(h, 0)
    ours = {}
    for _ in range(6):
        pick(h, 20)
        ours[(arp(h, pl09_manifest, 0)[1] >> 2 & 7) + 1] = h.leds()[20]
    assert [ours[k] for k in range(1, 7)] == stock, (ours, stock)


# ---- PL16: drum pages (spec 2026-10-25-drums-design.md, "The drum page frame", "The Repeat page").

def track_of(h):
    h.call(TRACK_OF, CONT)
    return h.uc.reg_read(UC_ARM_REG_R0) & 0xFF


def repeat(h, m):
    a = sym(m, "repeat_cfg")
    return h.r8(a), h.r8(a + 1)


def drum_pages(h, m):
    return bytes(h.uc.mem_read(sym(m, "drum_page"), 4))


DRUMS = [ORANGE, YELLOW, 0x49, CYAN]                                  # pads 28-31: stock's expanded-view drum colours
REPEAT_OFF = [BLUE_D] * 4 + [MAG_D] * 4 + [WHITE] + [WHITE_D] * 3 + [0, 0, CYAN_D, ORANGE_D] + [0] * 12 + DRUMS   # power-on


@pytest.mark.parametrize("start", [[0], [0, 9], [0, 10], [0, 12], [0, 14], [0, 15], [5]],
                         ids=["Synth 1 Note", "expanded", "Velocity", "Pattern Settings", "Mixer", "FX", "Drum 2"])
def test_shift_drum_opens_repeat_from_every_view(pl17_image, pl17_manifest, start):
    m = pl17_manifest
    h = NoteHarness(pl17_image)
    ready(h, m)
    for b in start:
        h.press(b)
    open_page(h, 4)
    assert h.r32(MGR + 0x6C) == CONT and track_of(h) == 4 and h.view_mode() == NOTE_DEFAULT
    assert page(h, m) == 4
    assert h.leds()[:32] == REPEAT_OFF                                  # rate 0: every rate pad dim


def test_shift_drum_on_screen_keeps_its_view(pl17_image, pl17_manifest):
    """Drum 1 already on screen (expanded, mode 6): no stock calls, the page opens over it."""
    h = NoteHarness(pl17_image)
    ready(h, pl17_manifest)
    h.press(4)
    h.press(9)
    assert h.view_mode() == NOTE_EXPANDED
    open_page(h, 4)
    assert h.view_mode() == NOTE_EXPANDED and page(h, pl17_manifest) == 4 and h.leds()[:32] == REPEAT_OFF


def test_repeat_page_picks(pl17_image, pl17_manifest):
    m = pl17_manifest
    h = NoteHarness(pl17_image)
    ready(h, m)
    h.press(5)
    open_page(h, 5)
    h.take()
    pick(h, 2)
    assert repeat(h, m) == (3, 0) and h.leds()[:8] == [BLUE_D, BLUE_D, BLUE, BLUE_D] + [MAG_D] * 4
    pick(h, 2)                                                          # the lit one again: off
    assert repeat(h, m) == (0, 0) and h.leds()[:32] == REPEAT_OFF
    pick(h, 5)
    assert repeat(h, m) == (6, 0)
    for pad in (9, 14, 15):
        pick(h, pad)
    assert repeat(h, m) == (6 | 1 << 4 | 0x80 | 0x40, 0)               # shape fade, unquantized, latch
    want = [BLUE_D] * 4 + [MAG_D, MAG, MAG_D, MAG_D] + [WHITE_D, WHITE, WHITE_D, WHITE_D] + [0, 0, CYAN, ORANGE]
    assert h.leds()[:32] == want + [0] * 12 + DRUMS
    for pad in (12, 13, *range(16, 28)):                               # nothing on these pads (28-31: the drums)
        pick(h, pad)
    assert repeat(h, m) == (6 | 1 << 4 | 0xC0, 0) and h.leds()[:32] == want + [0] * 12 + DRUMS
    pick(h, 11)                                                         # accent the beat
    pick(h, 14)
    pick(h, 15)
    assert repeat(h, m) == (6 | 3 << 4, 0)
    assert h.leds()[8:16] == [WHITE_D] * 3 + [WHITE, 0, 0, CYAN_D, ORANGE_D]
    pick(h, 7)
    assert repeat(h, m) == (8 | 3 << 4, 0) and h.leds()[4:8] == [MAG_D] * 3 + [MAG]
    assert h.take("synth_on", "midi_on") == [] and h.sounding == set()


def test_drum_toc_and_paging(pl17_image, pl17_manifest):
    m = pl17_manifest
    h = NoteHarness(pl17_image)
    ready(h, m)
    h.press(6)
    open_page(h, 6)
    leds = h.leds()
    assert (leds[LED_DOWN], leds[LED_UP]) == (ORANGE, 0)                # PL17: Pattern tools after it
    h.shift(True)
    leds = h.leds()
    assert leds[:24] == [0] * 24 and leds[24:32] == [0, BLUE, ORANGE_D] + [0] * 5   # beta: Repeat on 26, next to Pattern tools
    assert (leds[LED_DOWN], leds[LED_UP]) == (ORANGE, 0)
    before = (drum_pages(h, m), repeat(h, m), page(h, m), h.leds())
    for pad in (24, 27, 31, 0, 15):                                     # dark pads (25: Levels, later); no setting with Shift held
        pick(h, pad)
    assert (drum_pages(h, m), repeat(h, m), page(h, m), h.leds()) == before
    pick(h, 25)                                                         # Repeat, the open page: stored by its slot now
    assert (drum_pages(h, m), repeat(h, m), page(h, m), h.leds()) == (bytes([0, 0, 1, 0]), *before[1:])
    h.shift(False)
    for b in (DOWN, UP):
        h.press(b)
        h.press(b, shift=True)
    assert page(h, m) == 6 and drum_pages(h, m) == bytes([0, 0, 1, 0]) and h.leds()[:32] == REPEAT_OFF   # back on Repeat: slot 1


def test_a_drum_with_no_page_in_its_slot_opens_repeat(pl17_image, pl17_manifest):
    m = pl17_manifest
    h = NoteHarness(pl17_image)
    ready(h, m)
    h.uc.mem_write(sym(m, "drum_page"), bytes([3, 7, 0, 0]))           # slots 3 and 7: no page; 0: an alpha project's Repeat
    for d in (0, 1, 2):
        open_page(h, 4 + d)
        assert page(h, m) == 4 + d and h.leds()[:32] == REPEAT_OFF
        h.shift(True)
        assert h.leds()[24:32] == [0, BLUE, ORANGE_D] + [0] * 5
        h.shift(False)


NOTE_ARRAYS = {"page_slot": 4, "page_sub": 4, "page_quick": 4, "euclid_cfg": 8, "euclid_last": 4, "euclid_undo_at": 1,
               "euclid_undo_steps": 0x380, "melody_cfg": 8, "melody_seed": 8, "melody_draft": 1, "melody_vary": 4,
               "rhythm_cfg": 12, "chord_settings": 4, "chord_voice": 4, "chord_arp": 8, "chord_prev": 24,
               "chord_prev_n": 4, "chord_order": 4}


def note_arrays(h, m):
    return {k: bytes(h.uc.mem_read(sym(m, k), n)) for k, n in NOTE_ARRAYS.items()}


def fill_note_arrays(h, m) -> None:
    """Every note-track array gets distinct values (a stray write of any value shows) and the valid-page bytes; no draft."""
    fill = {"page_slot": bytes([1, 2, 3, 7]), "page_sub": bytes([3, 1, 2, 3]), "page_quick": bytes([1, 1, 1, 1]),
            "melody_draft": b"\x00"}                                    # valid pages; no draft (a drum page ends one)
    for k, n in NOTE_ARRAYS.items():
        h.uc.mem_write(sym(m, k), fill.get(k, bytes((0x5A + 13 * i) & 0xFF | 1 for i in range(n))))


DRUM_PAGE_STATE = {"chord_page", "page_taken", "act", "armed", "repeat_cfg", "drum_page", "sent",   # sent: the link's image
                   "rep_vel", "rep_new", "rep_held", "rep_latched"}   # a drum pad's press (no heartbeat runs here)


def slim_state(h, m):
    """All of slim's RAM and ITCM but the symbols a drum page may change (zeroed): a stray write anywhere shows."""
    syms = sorted((int(v, 16), k) for k, v in m["symbols"].items())
    out = []
    for lo, hi in (("__slim_ram_start", "__slim_ram_end"), ("__slim_itcm_start", "__slim_itcm_end")):
        a, b = sym(m, lo), sym(m, hi)
        mem = bytearray(h.uc.mem_read(a, b - a))
        for addr, k in syms:
            if k in DRUM_PAGE_STATE and a <= addr < b:
                end = min([x for x, _ in syms if x > addr] + [b])
                mem[addr - a:end - a] = bytes(end - addr)
        out.append(bytes(mem))
    return out


def test_drum_pages_keep_note_arrays(pl17_image, pl17_manifest):
    """Review focus: no page.c entry with a drum page open indexes a note-track array with t >= 4, and no Euclid or
    Melody function acts for a drum. The arrays hold distinct values first, so a stray write of any value shows."""
    m = pl17_manifest
    h = NoteHarness(pl17_image)
    ready(h, m)
    fill_note_arrays(h, m)
    before = note_arrays(h, m)
    h.track(0)
    state = slim_state(h, m)
    for d in range(4):
        open_page(h, 4 + d)
        assert page(h, m) == 4 + d
        h.leds()
        for b in (21, DOWN, UP):                                       # 1-16/17-32, ▼, ▲, with and without Shift
            h.press(b, shift=True)
            h.press(b)
        for shift in (False, True):
            h.shift(shift)
            for pad in range(32):
                h.down(pad)
                h.leds()
                h.up(pad)
            h.up(3)                                                     # a release with no page pad down
            h.leds()
        h.shift(False)
        assert page(h, m) == 4 + d and note_arrays(h, m) == before, d
        assert slim_state(h, m) == state, d
    for d in range(4):
        open_page(h, 4 + d)
    h.press(9)                                                          # Note closes it
    assert page(h, m) == CLOSED and note_arrays(h, m) == before


@pytest.mark.parametrize("button", [4, 5, 0, 9, 14, 15, 8])
def test_drum_button_closes(pl17_image, pl17_manifest, button):
    h = NoteHarness(pl17_image)
    ready(h, pl17_manifest)
    open_page(h, 4)
    assert page(h, pl17_manifest) == 4
    h.press(button)
    assert page(h, pl17_manifest) == CLOSED


@pytest.mark.parametrize("view", [[0], [0, 14], [0, 15], [4], [4, 9], [6]], ids=["Synth 1", "Mixer", "FX", "Drum 1",
                                                                                "Drum 1 expanded", "Drum 3"])
def test_shift_leds_36_39(pl17_image, stock_image, view):
    a, b = NoteHarness(stock_image), NoteHarness(pl17_image)
    for h in (a, b):
        for button in view:
            h.press(button)
        h.shift(True)
    la, lb = a.leds(), b.leds()
    for i in range(32, 40):                                            # the tracks and the drums: as stock's Shift functions
        assert lb[i] == (la[i] or 0x2C), (view, i, la[i], lb[i])
    skip = set(range(32, 40)) | {55} | (set(range(16, 32)) | {53} if view == [0] else set())   # the Quick view, Clear
    if view == [4, 9]:                                                 # PL20: FILL's pads 21-24 (off: dim orange)
        assert la[20:24] == [0] * 4 and lb[20:24] == [0x46] * 4
        skip |= set(range(20, 24))
    assert [x for i, x in enumerate(lb) if i not in skip] == [x for i, x in enumerate(la) if i not in skip], view


def test_shift_leds_36_39_on_a_drum_page(pl17_image, pl17_manifest):
    h = NoteHarness(pl17_image)
    ready(h, pl17_manifest)
    open_page(h, 6)
    h.shift(True)
    leds = h.leds()
    assert 0 not in leds[36:40] and leds[36:40].count(0x2C) >= 3          # stock lights the selected drum's own
