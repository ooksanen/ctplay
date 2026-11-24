"""save_layout.lock (spec 2026-10-17-saved-settings-design.md, "Versioning and the lock"): each saved field keeps the
payload offset and size it was first given; new fields go after the last; a removed field needs a tombstone; reusing a
tombstone needs a layout-ID bump."""
import re

import pytest

from playbuild import lock, paths
from playbuild.errors import BuildError
from playbuild.features import SavedField


def f(symbol, size):
    return SavedField(symbol, size, bytes(size))


def write(tmp_path, text):
    p = tmp_path / "save_layout.lock"
    p.write_text(text)
    return p


BASE = """layout_id = 1

[[field]]
feature = "a"
symbol = "a_x"
offset = 0
size = 4

[[field]]
feature = "b"
symbol = "b_y"
offset = 4
size = 1
"""


def test_missing_lock_file_is_empty(tmp_path):
    lk = lock.load(tmp_path / "none.lock")
    assert (lk.layout_id, lk.entries, lk.length) == (1, (), 0)


def test_update_appends_and_keeps_offsets(tmp_path):
    p = write(tmp_path, BASE)
    lk = lock.update(p, {"a": (f("a_new", 2), f("a_x", 4)), "b": (f("b_y", 1),)})
    assert [(e.symbol, e.offset, e.size) for e in lk.entries] == [("a_x", 0, 4), ("b_y", 4, 1), ("a_new", 5, 2)]
    assert lk.length == 7
    assert lock.load(p) == lk                                           # written back, read the same
    lock.check(lk, {"a": (f("a_x", 4), f("a_new", 2)), "b": (f("b_y", 1),)})


def test_check_places_fields_by_the_lock(tmp_path):
    lk = lock.load(write(tmp_path, BASE))
    placed = lock.check(lk, {"b": (f("b_y", 1),), "a": (f("a_x", 4),)})
    assert {e.symbol: e.offset for e in placed} == {"a_x": 0, "b_y": 4}


def test_a_feature_not_in_the_version_is_not_missing(tmp_path):
    lock.check(lock.load(write(tmp_path, BASE)), {"a": (f("a_x", 4),)})


def test_new_field_needs_update_lock(tmp_path):
    with pytest.raises(BuildError, match="a_new.*--update-lock"):
        lock.check(lock.load(write(tmp_path, BASE)), {"a": (f("a_x", 4), f("a_new", 1)), "b": (f("b_y", 1),)})


def test_resize_fails(tmp_path):
    p = write(tmp_path, BASE)
    for fn in (lambda fields: lock.check(lock.load(p), fields), lambda fields: lock.update(p, fields)):
        with pytest.raises(BuildError, match="a_x.*4 B.*now 5 B"):
            fn({"a": (f("a_x", 5),), "b": (f("b_y", 1),)})


def test_removed_field_without_a_tombstone_fails(tmp_path):
    p = write(tmp_path, BASE)
    with pytest.raises(BuildError, match="b_y.*tombstone"):
        lock.check(lock.load(p), {"a": (f("a_x", 4),), "b": ()})
    with pytest.raises(BuildError, match="b_y.*tombstone"):
        lock.update(p, {"a": (f("a_x", 4),), "b": ()})


def test_tombstone_keeps_its_bytes(tmp_path):
    p = write(tmp_path, BASE.replace('size = 1\n', 'size = 1\ntombstone = true\nretired_in = 1\n'))
    lk = lock.update(p, {"a": (f("a_x", 4),), "b": (f("b_z", 2),)})
    assert [(e.symbol, e.offset, e.tombstone) for e in lk.entries] == [("a_x", 0, False), ("b_y", 4, True),
                                                                        ("b_z", 5, False)]


def test_tombstone_reuse_needs_a_layout_id_bump(tmp_path):
    retired = BASE.replace('size = 1\n', 'size = 1\ntombstone = true\nretired_in = 1\n')
    p = write(tmp_path, retired)
    fields = {"a": (f("a_x", 4),), "b": (f("b_y", 1),)}
    with pytest.raises(BuildError, match="b_y.*retired.*layout_id"):
        lock.check(lock.load(p), fields)
    with pytest.raises(BuildError, match="b_y.*retired.*layout_id"):
        lock.update(p, fields)
    p = write(tmp_path, retired.replace("layout_id = 1", "layout_id = 2"))
    lk = lock.update(p, fields)
    assert [(e.symbol, e.offset, e.tombstone) for e in lk.entries][-1] == ("b_y", 5, False)
    lock.check(lk, fields)


def test_field_moved_to_another_feature_fails(tmp_path):
    with pytest.raises(BuildError, match="a_x.*feature a.*declared by b"):
        lock.check(lock.load(write(tmp_path, BASE)), {"b": (f("b_y", 1), f("a_x", 4)), "a": ()})


def test_real_lock_matches_the_spec_payload():
    lk = lock.load(paths.SAVE_LOCK)
    assert lk.layout_id == 1
    assert [(e.symbol, e.offset, e.size) for e in lk.entries] == [
        ("chord_settings", 0, 4), ("chord_rootless", 4, 1), ("chord_strum", 5, 1), ("chord_strum_down", 6, 1),
        ("chord_mono", 7, 1), ("chord_arp", 8, 8), ("page_last", 16, 4), ("page_quick", 20, 4), ("ci_on", 24, 1),
        ("euclid_cfg", 25, 8), ("page_slot", 33, 4), ("melody_cfg", 37, 8), ("melody_seed", 45, 8),                                       # PL13
        ("rhythm_cfg", 53, 12), ("melody_vary", 65, 4), ("page_sub", 69, 4), ("euclid_last", 73, 4),
        ("chord_voice", 77, 4), ("repeat_cfg", 81, 2), ("drum_page", 83, 4),
        ("drum_euclid", 87, 8), ("drum_rhythm", 95, 12), ("drum_accent", 107, 4), ("drum_seed", 111, 4), ("chord_step", 115, 1),
        ("chord_pstrum", 116, 1), ("trig_mark", 117, 1)]   # PL14, PL15, PL16, PL17, PL18, PL19, PL20
    assert [e.symbol for e in lk.entries if e.tombstone] == ["page_last"]   # PL11: pages numbered by their pad
    assert lk.length == 118


# ---- rev (PL12, spec 2026-10-18-ctctrl-link-design.md "Protocol"): what a field's bits mean, pinned by the lock

def fr(symbol, size, rev):
    return SavedField(symbol, size, bytes(size), rev)


def test_rev_is_recorded_and_pinned(tmp_path):
    p = write(tmp_path, BASE)
    with pytest.raises(BuildError, match="a_x: rev changed from 1 to 2: build once with --update-lock"):
        lock.check(lock.load(p), {"a": (fr("a_x", 4, 2),)})
    lk = lock.update(p, {"a": (fr("a_x", 4, 2),)})
    assert [e.rev for e in lk.entries] == [2, 1]
    assert lock.load(p) == lk
    lock.check(lk, {"a": (fr("a_x", 4, 2),)})


def test_rev_never_goes_down(tmp_path):
    p = write(tmp_path, BASE.replace("size = 4\n", "size = 4\nrev = 3\n"))
    for go in (lambda: lock.check(lock.load(p), {"a": (fr("a_x", 4, 2),)}),
               lambda: lock.update(p, {"a": (fr("a_x", 4, 2),)})):
        with pytest.raises(BuildError, match="a_x: rev 2 is below the locked rev 3"):
            go()


def test_update_never_places_a_new_field_over_a_tombstone(tmp_path):
    p = write(tmp_path, BASE.replace('symbol = "b_y"\noffset = 4\nsize = 1\n',
                                     'symbol = "b_y"\noffset = 4\nsize = 1\ntombstone = true\nretired_in = 1\n'))
    lk = lock.update(p, {"b": (f("b_z", 1),)})
    assert [(e.symbol, e.offset) for e in lk.entries] == [("a_x", 0), ("b_y", 4), ("b_z", 5)]


def test_lock_text_unchanged_for_rev_1(tmp_path):
    p = write(tmp_path, BASE)
    lock.update(p, {"a": (f("a_x", 4),), "b": (f("b_y", 1),)})
    assert not re.search(r"^rev =", p.read_text(), re.M)
    assert lock._dump(lock.load(paths.SAVE_LOCK)) == paths.SAVE_LOCK.read_text()
