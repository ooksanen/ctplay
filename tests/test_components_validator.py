"""Novation Components' project validator on records saved through stock's real save route (emulation).

Checks stock's fields only (header, timing, scene chains, patterns, patches up to 0x27023): a guard against CTPlay's
stray writes there. Never CTPlay's own tail (the validator ignores it). The record is the one in RAM as the save leaves
it. Spike: docs/investigations/2026-11-11-components-validator.md."""
import pytest

import components
from harness import Harness
from notes import NoteHarness, step_addr
from test_drum_tools import HARD, ROLL, open_tools as open_drum_tools
from test_drum_tools import pick, write as drum_write
from test_euclid import open_tools as open_note_tools, write as note_write
from test_saved import DISTINCT, put_settings, save, snapshot
from test_step_entry import C, ready, step_first
from trig import TrigHarness

pytestmark = pytest.mark.emu
HOLD = 600


def check(record):
    (ok, errors), = components.validate(record)
    assert ok, "\n".join(errors)


def test_stock_new_project_is_valid(stock_image):
    h = Harness(stock_image)
    h.leds()
    save(h)
    check(snapshot(h))


def test_negative_control_names_the_reserved_flags(stock_image):
    """featureFlags.reserved set: the validator must refuse it, or the shim checks nothing."""
    h = Harness(stock_image)
    h.leds()
    save(h)
    rec = bytearray(snapshot(h))
    (ok, _), = components.validate(bytes(rec))
    assert ok
    rec[0x0B] = 0x80
    (ok, errors), = components.validate(bytes(rec))
    assert not ok and any("reserved feature flags" in e for e in errors), errors


def test_pl21_every_setting_off_its_default_is_valid(pl21_image, pl21_manifest):
    h = NoteHarness(pl21_image)
    h.leds()
    put_settings(h, pl21_manifest, DISTINCT)
    save(h)
    check(snapshot(h))


def test_pl21_defaults_are_valid(pl21_image):
    h = NoteHarness(pl21_image)
    h.leds()
    save(h)
    check(snapshot(h))


def test_pl21_after_pattern_writes_is_valid(pl21_image, pl21_manifest):
    """A Euclid Write (Synth 1), a drum Write with a roll, a step-entry chord (Synth 2), a trig condition on a note
    step (Synth 4) and on a drum step: one record."""
    m = pl21_manifest
    h = TrigHarness(pl21_image, m)
    h.leds()
    h.mark(1)
    open_note_tools(h, 0)
    pick(h, 4)                                          # 5 hits
    note_write(h)
    open_drum_tools(h, 0)
    for pad in (4, HARD, ROLL):                         # 5 hits, hard, two hits a step
        pick(h, pad)
    drum_write(h)
    ready(h, m, t=1)                                    # Synth 2's Note view, a triad, step-entry chords on
    step_first(h, 3, C)
    assert h.r8(step_addr(1, 0, 3)) > 1                 # more than one note unit: the chord went in
    h.hit(3, 0, 2)                                      # a note step on Synth 4, a hit on Drum 2
    h.hit(5, 0, 2)
    h.load_editors()
    for t in (3, 5):
        h.open_prob(t)
        h.pad(2)
        h.row4(3, ms=HOLD)                              # a cycle of 4 passes
        assert h.code(t, 0, 2) != 0
    save(h)
    check(snapshot(h))
