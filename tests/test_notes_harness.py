"""The Note-view symbols and the note-level harness, against the stock image."""
import pytest

from notes import (CONT, NOTE_DEFAULT, NOTE_EXPANDED, NoteHarness, ROOT, SCALE_MASK, endpoint_note)
from playbuild import hooks, paths, symbols


def test_note_view_hook_points_are_safe_to_patch(stock_image):
    sym = symbols.load(paths.SYMBOLS)
    targets = hooks.branch_targets(paths.LISTING)
    for point in ("pad_note_on", "pad_note_off", "pad_release"):
        hooks.check_entry(sym.hooks[point], stock_image, targets)      # raises BuildError if unsafe


@pytest.mark.emu
@pytest.mark.parametrize("mode", [NOTE_DEFAULT, NOTE_EXPANDED])
def test_one_pad_is_one_note_in_stock(stock_image, mode):
    h = NoteHarness(stock_image)
    h.track(0, mode)
    assert h.view_mode() == mode
    view = h.note_view(0)
    kbd = h.r32(view + 0x38)
    assert h.r32(kbd + 0x0C) == SCALE_MASK - 4                       # keyboard -> scale object; mask at +4
    h.take()
    h.down(24, 100)
    on = h.take("pad_on", "synth_on")
    assert on[0][:3] == ("pad_on", view, 24)
    assert [e[0] for e in on] == ["pad_on", "synth_on"]
    assert on[1][1:3] == (0, endpoint_note(h, h.pitch(0, 24)))
    h.up(24)
    assert [e[0] for e in h.take("pad_off", "synth_off")] == ["pad_off", "synth_off"]
    assert h.sounding == set()


@pytest.mark.emu
def test_track_buttons_select_the_four_note_views(stock_image):
    h = NoteHarness(stock_image)
    for t in range(4):
        h.track(t, NOTE_DEFAULT)
        sink = h.r32(h.note_view(t) + 0x18)
        assert h.r32(h.note_view(t)) == 0x0805A064 and h.r32(sink) == 0x0805BF54 and h.r8(sink + 0x0C) == t
    assert h.r32(CONT) != 0 and 0 <= h.r8(ROOT) < 12
