"""Quick view and Shift-lit track buttons (spec 2026-10-17-play-pages-design.md sections 2-3): Shift in the Note view
shows the track's quick view on pads 17-32 (Chords palette or the Arp page's top half), Shift + 1-16/17-32 flips it;
while Shift is held the tracks with pages light in stock's Shift-function colour."""
import pytest

from harness import Harness
from notes import NOTE_DEFAULT, NOTE_EXPANDED, NoteHarness

pytestmark = pytest.mark.emu
FLIP, DOWN = 21, 19
GREEN, GREEN_D, BLUE, SHIFT_FN = 0x17, 0x18, 0x07, 0x2C


def sym(m, name):
    return int(m["symbols"][name], 16)


def quick(h, m, t=0):
    return h.r8(sym(m, "page_quick") + t)


def arp(h, m, t=0):
    a = sym(m, "chord_arp") + 2 * t
    return h.r8(a), h.r8(a + 1)


def pick(h, pad):
    h.down(pad)
    h.up(pad)


def shift_leds(h):
    h.shift(True)
    leds = h.leds()
    h.shift(False)
    return leds


def page_leds(h, t, arp_page):
    """The track's page as drawn on its 32 pads (opened, then closed again)."""
    h.press(t, shift=True)
    h.press(20)
    h.press(20)                                                        # Chords, from any page
    if arp_page:
        h.press(DOWN)
    leds = h.leds()[:32]
    h.press(t)
    return leds


@pytest.mark.parametrize("mode", [NOTE_DEFAULT, NOTE_EXPANDED])
def test_shift_shows_the_shapes_by_default(pl15_image, pl15_manifest, mode):
    h = NoteHarness(pl15_image)
    h.track(0, mode)
    assert quick(h, pl15_manifest) == 0
    h.shift(True)
    pick(h, 17)                                                        # pad 18: triad
    h.shift(False)
    assert h.r8(sym(pl15_manifest, "chord_settings")) & 7 == 1
    assert shift_leds(h)[16:32] == page_leds(h, 0, False)[:16]


@pytest.mark.parametrize("mode", [NOTE_DEFAULT, NOTE_EXPANDED])
def test_quick_view_is_the_shapes(pl15_image, pl15_manifest, mode):
    """Review focus: with a row-2 shape on, flip to Arp and back; voicing is not on the Quick view."""
    m = pl15_manifest
    h = NoteHarness(pl15_image)
    h.track(0, mode)
    h.leds()                                                           # slim's init (resets chord_voice) first
    voice, sett = sym(m, "chord_voice"), sym(m, "chord_settings")
    leds = shift_leds(h)
    assert leds[16:29] == [GREEN] + [GREEN_D] * 12 and leds[29:32] == [0, 0, 0]
    h.take()
    for q in range(16, 29):                                            # Quick pad q (0-based 16-28) = page pad q - 16
        h.shift(True)
        pick(h, q)
        h.shift(False)
        p = q - 16
        assert (h.r8(sett) & 7, h.r8(voice) & 15) == ((p, 0) if p < 8 else (0, p - 7)), q
        assert shift_leds(h)[16:32] == [GREEN if c == p else GREEN_D for c in range(13)] + [0, 0, 0]
    inv = h.r8(sett) >> 3
    for q in (29, 30, 31):                                             # pads 30-32: dark and inert
        h.shift(True)
        pick(h, q)
        h.shift(False)
    assert h.r8(voice) & 15 == 5 and h.r8(sett) >> 3 == inv
    h.press(FLIP, shift=True)                                          # to Arp and back
    h.press(FLIP, shift=True)
    assert quick(h, m) == 0 and shift_leds(h)[16:32] == [GREEN_D] * 12 + [GREEN] + [0, 0, 0]
    assert h.r8(voice) & 15 == 5
    assert shift_leds(h)[16:32] == page_leds(h, 0, False)[:16]
    assert h.take("synth_on", "midi_on") == [] and h.sounding == set()


@pytest.mark.parametrize("mode", [NOTE_DEFAULT, NOTE_EXPANDED])
def test_shift_page_button_flips_the_quick_view(pl09_image, pl09_manifest, stock_image, mode):
    a, h = NoteHarness(stock_image), NoteHarness(pl09_image)
    for x in (a, h):
        x.track(0, mode)
        x.press(FLIP, shift=True)
    assert quick(h, pl09_manifest) == 1
    leds = shift_leds(h)
    assert leds[16:32] == page_leds(h, 0, True)[:16] and leds[53] == BLUE
    assert leds[:16] == shift_leds(a)[:16]                             # pads 1-16: stock's
    h.press(FLIP, shift=True)
    assert quick(h, pl09_manifest) == 0 and shift_leds(h)[53] == GREEN
    assert h.leds()[53] == a.leds()[53]                                # no Shift: stock's LED


def test_flip_skips_keys(pl09_image, pl09_manifest):
    """The Keys page has no quick half: the flip stays Chords <-> Arp."""
    h = NoteHarness(pl09_image)
    h.track(0)
    got = []
    for _ in range(4):
        h.press(FLIP, shift=True)
        got.append(quick(h, pl09_manifest))
    assert got == [1, 0, 1, 0]
    assert shift_leds(h)[53] == GREEN


def test_arp_quick_pads_act_as_the_page(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    h.press(FLIP, shift=True)
    h.take()
    h.shift(True)
    for pad, want in [(17, 0x01), (25, 0x09), (28, 0x29), (31, 0xA9), (16, 0xA8)]:   # up, 1/8, triplet, latch, off
        pick(h, pad)
        assert arp(h, pl09_manifest)[0] == want, (pad, hex(arp(h, pl09_manifest)[0]))
    h.shift(False)
    assert h.take("synth_on", "midi_on") == [] and h.sounding == set()


def test_pattern_off_from_the_quick_view_ends_its_notes(pl09_image, pl09_manifest):
    """Review focus: as from the page."""
    h = NoteHarness(pl09_image)
    h.track(0)
    h.press(FLIP, shift=True)
    h.shift(True)
    pick(h, 17)                                                        # pattern up
    h.shift(False)
    h.uc.mem_write(sym(pl09_manifest, "chord_arp") + 1, bytes([5 << 2]))   # legato: a note always sounds
    h.down(24)
    h.heartbeat(700)
    assert h.sounding
    h.shift(True)
    pick(h, 16)                                                        # pattern off
    h.shift(False)
    h.heartbeat(5)
    assert h.sounding == set()
    h.up(24)
    h.heartbeat(5)
    assert h.sounding == set()


def test_shift_let_go_before_a_quick_release_plays_nothing(pl09_image, pl09_manifest):
    """Review focus: the release of a quick-view or table-of-contents press is never a note."""
    h = NoteHarness(pl09_image)
    h.track(0)
    h.take()
    h.shift(True)
    h.down(20)
    h.shift(False)
    h.up(20)
    h.press(0, shift=True)                                             # a page: its table of contents
    h.shift(True)
    h.down(25)
    h.shift(False)
    h.up(25)
    assert h.take("synth_on", "synth_off", "midi_on", "midi_off") == [] and h.sounding == set()


def test_flip_only_in_the_note_view(pl09_image, pl09_manifest):
    h = NoteHarness(pl09_image)
    h.track(0)
    h.press(14)                                                        # Mixer
    h.press(FLIP, shift=True)
    assert quick(h, pl09_manifest) == 0
    h.track(0)
    h.press(0, shift=True)                                             # a page open
    h.press(FLIP, shift=True)
    assert quick(h, pl09_manifest) == 0


def test_shift_pads_1_16_stay_stock(pl09_image, stock_image):
    for flips in (0, 1):
        a, b = NoteHarness(stock_image), NoteHarness(pl09_image)
        for h in (a, b):
            h.track(0)
            for _ in range(flips):
                h.press(FLIP, shift=True)
            for pad in (0, 5, 15):
                h.shift(True)
                pick(h, pad)
                h.shift(False)
        assert a.outputs() == b.outputs(), flips


@pytest.mark.parametrize("view", [None, 14, 15, 8])
def test_shift_lights_the_track_buttons(pl09_image, stock_image, view):
    a, b = NoteHarness(stock_image), NoteHarness(pl09_image)
    for h in (a, b):
        h.track(0)
        if view is not None:
            h.press(view)
    la, lb = shift_leds(a), shift_leds(b)
    for i in range(32, 40):                                            # PL16: the drums (36-39) too
        assert lb[i] == (la[i] if la[i] else SHIFT_FN), (view, i, la[i], lb[i])
    skip = (set(range(16, 32)) | {53} if view is None else set()) | {55}   # the Note view: the quick view and its LED;
    assert lb[55] == 0x53                                              # every view: Clear = the count-in state (off)
    assert [x for i, x in enumerate(lb) if i not in skip and not 32 <= i < 40] == \
           [x for i, x in enumerate(la) if i not in skip and not 32 <= i < 40], view
