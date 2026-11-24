import pytest

from helpers import write_feature, write_version
from playbuild import features, paths, symbols
from playbuild.errors import BuildError

SYM = symbols.load(paths.SYMBOLS)


def test_dependency_order_and_handler_priority(tmp_path):
    fd = tmp_path / "f"
    write_feature(fd, "base", hooks=[("button_press", "base_btn", 50)])
    write_feature(fd, "top", depends=["base"], init="top_init",
                  hooks=[("button_press", "top_btn", 10), ("led_task", "top_leds", 50)])
    v = features.load_version(write_version(tmp_path, "v", "SLX1", ["top", "base"], fd), SYM)
    assert [f.name for f in v.features] == ["base", "top"]
    h = features.handlers(v)
    assert [u.handler for _, u in h["button_press"]] == ["top_btn", "base_btn"]
    assert [u.handler for _, u in h["led_task"]] == ["top_leds"]
    assert v.features[1].init == "top_init" and v.features[1].sources[0].name == "top.c"


def test_missing_dependency_is_an_error(tmp_path):
    fd = tmp_path / "f"
    write_feature(fd, "base")
    write_feature(fd, "top", depends=["base"])
    with pytest.raises(BuildError, match="top depends on base"):
        features.load_version(write_version(tmp_path, "v", "SLX1", ["top"], fd), SYM)


def test_unknown_hook_point_is_an_error(tmp_path):
    fd = tmp_path / "f"
    write_feature(fd, "a", hooks=[("no_such_point", "a_h", 50)])
    with pytest.raises(BuildError, match="unknown hook point no_such_point"):
        features.load_version(write_version(tmp_path, "v", "SLX1", ["a"], fd), SYM)


def test_duplicate_handler_names_are_an_error(tmp_path):
    fd = tmp_path / "f"
    write_feature(fd, "a", hooks=[("button_press", "same", 50)])
    write_feature(fd, "b", hooks=[("led_task", "same", 50)])
    with pytest.raises(BuildError, match="handler same"):
        features.load_version(write_version(tmp_path, "v", "SLX1", ["a", "b"], fd), SYM)


@pytest.mark.parametrize("marker", ["SL00D", "PL01", "PL01D", "PL1.2D"])
def test_marker_prefixes_accepted(tmp_path, marker):
    fd = tmp_path / "f"
    write_feature(fd, "a")
    assert features.load_version(write_version(tmp_path, "v", marker, ["a"], fd), SYM).marker == marker


@pytest.mark.parametrize("marker", ["RC9", "SC01", "PX01", "sl01", "pl01", "SL00000", "PL00000", "SL 1", "PL", ""])
def test_marker_format(tmp_path, marker):
    fd = tmp_path / "f"
    write_feature(fd, "a")
    with pytest.raises(BuildError, match="marker"):
        features.load_version(write_version(tmp_path, "v", marker, ["a"], fd), SYM)


def test_feature_name_must_match_directory(tmp_path):
    d = write_feature(tmp_path / "f", "a")
    (d / "feature.toml").write_text((d / "feature.toml").read_text().replace('name = "a"', 'name = "b"'))
    with pytest.raises(BuildError, match="name"):
        features.load_feature(d)


@pytest.mark.parametrize("point", ["button_press", "led_task"])          # an entry hook, a void call hook
def test_filter_needs_a_call_hook_with_a_result(tmp_path, point):
    fd = tmp_path / "f"
    write_feature(fd, "a", hooks=[(point, "a_h", 50, True)])
    with pytest.raises(BuildError, match="filter = true needs a call hook on a function that returns a value"):
        features.load_version(write_version(tmp_path, "v", "SLX1", ["a"], fd), SYM)


def _saved(tmp_path, entries):
    d = write_feature(tmp_path / "f", "a")
    (d / "feature.toml").write_text((d / "feature.toml").read_text() + entries)
    return d


def test_saved_fields_are_read_with_their_defaults(tmp_path):
    d = _saved(tmp_path, '\n[[saved]]\nsymbol = "a_x"\nbytes = 2\ndefault = "0008"\n\n'
                         '[[saved]]\nsymbol = "a_y"\nbytes = 1\nstore = "project"\n')
    f = features.load_feature(d)
    assert f.saved == (features.SavedField("a_x", 2, b"\x00\x08"), features.SavedField("a_y", 1, b"\x00"))
    assert features.load_feature(write_feature(tmp_path / "g", "b")).saved == ()


def test_saved_fields_read_rev_and_link(tmp_path):
    d = _saved(tmp_path, '\n[[saved]]\nsymbol = "a_x"\nbytes = 1\nrev = 2\n\n[[saved]]\nsymbol = "a_y"\nbytes = 1\nlink = false\n')
    x, y = features.load_feature(d).saved
    assert (x.rev, x.link, y.rev, y.link) == (2, True, 1, False)


def test_link_functions_are_read(tmp_path):
    d = write_feature(tmp_path / "f", "a")
    (d / "feature.toml").write_text('link_valid = "a_valid"\nlink_apply = "a_apply"\n' + (d / "feature.toml").read_text())
    f = features.load_feature(d)
    assert (f.link_valid, f.link_apply) == ("a_valid", "a_apply")


def test_conflicting_features_are_refused(tmp_path):
    fd = tmp_path / "f"
    d = write_feature(fd, "a")
    (d / "feature.toml").write_text('conflicts = ["b"]\n' + (d / "feature.toml").read_text())
    write_feature(fd, "b")
    with pytest.raises(BuildError, match="a cannot be built together with b"):
        features.load_version(write_version(tmp_path, "v", "SLX1", ["a", "b"], fd), SYM)
    features.load_version(write_version(tmp_path, "w", "SLX2", ["a"], fd), SYM)


@pytest.mark.parametrize("entry, match", [
    ('symbol = "a_x"\nbytes = 1\nrev = 0', "rev"),
    ('symbol = "a_x"\nbytes = 2\ndefault = "00"', "default"),
    ('symbol = "a_x"\nbytes = 0', "bytes"),
    ('symbol = "a_x"\nbytes = 1\nstore = "device"', "store"),
])
def test_bad_saved_fields_are_refused(tmp_path, entry, match):
    with pytest.raises(BuildError, match=match):
        features.load_feature(_saved(tmp_path, f"\n[[saved]]\n{entry}\n"))


@pytest.mark.parametrize("diag", ["diag_ram", "diag_upper"])
def test_chord_conflicts_with_drum_diagnostics(tmp_path, diag):
    """PL16: the drum pages claim Shift + Drum 1-4; SL00D / SL01D's diagnostics use Shift + Drum 3 / 4."""
    with pytest.raises(BuildError, match=f"chord cannot be built together with {diag}"):
        features.load_version(write_version(tmp_path, "v", "PL99", ["chord", diag], paths.FEATURES), SYM)


def test_release_is_read_and_checked(tmp_path):
    fd = tmp_path / "f"
    write_feature(fd, "a")
    p = write_version(tmp_path, "v", "SLX1", ["a"], fd)
    assert features.load_version(p, SYM).release == ""
    base = p.read_text()
    p.write_text(base + 'release = "1.0 beta 1"\n')
    assert features.load_version(p, SYM).release == "1.0 beta 1"
    p.write_text(base + 'release = "1.0-beta"\n')
    with pytest.raises(BuildError, match="release"):
        features.load_version(p, SYM)


# Byte patches (beta 2, spec docs/specs/2026-11-22-beta2-fixes-design.md): fixes in stock's own code, checked at load
# for their form here and against the stock image and the hooks in test_hooks.py.
def _patched(tmp_path, entries, sources=None):
    d = write_feature(tmp_path / "f", "a")
    text = (d / "feature.toml").read_text()
    if sources is not None:
        text = text.replace('sources = ["a.c"]', f"sources = {sources}")
    (d / "feature.toml").write_text(text + entries)
    return d


def test_byte_patches_are_read(tmp_path):
    d = _patched(tmp_path, '\n[[patch]]\naddr = 0x080215B2\nstock = "EA D4"\nnew = "EF D4"\nwhy = "CC 27"\n', "[]")
    f = features.load_feature(d)
    assert f.patches == (features.BytePatch(0x080215B2, b"\xea\xd4", b"\xef\xd4", "CC 27"),)
    assert f.sources == ()
    assert features.load_feature(write_feature(tmp_path / "g", "b")).patches == ()


@pytest.mark.parametrize("entry, match", [
    ('addr = 0x080215B3\nstock = "EAD4"\nnew = "EFD4"\nwhy = "x"', "even"),
    ('addr = 0x080215B2\nstock = "EAD4"\nnew = "EF"\nwhy = "x"', "same length"),
    ('addr = 0x080215B2\nstock = ""\nnew = ""\nwhy = "x"', "2-16"),
    ('addr = 0x080215B2\nstock = "' + "00" * 18 + '"\nnew = "' + "00" * 18 + '"\nwhy = "x"', "2-16"),
    ('addr = 0x080215B2\nstock = "EAD4"\nnew = "EAD4"\nwhy = "x"', "changes nothing"),
    ('addr = 0x080215B2\nstock = "EAZZ"\nnew = "EFD4"\nwhy = "x"', "hex"),
    ('addr = 0x080215B2\nstock = "EAD4"\nnew = "EFD4"', "why"),
])
def test_bad_byte_patches_are_refused(tmp_path, entry, match):
    with pytest.raises(BuildError, match=match):
        features.load_feature(_patched(tmp_path, f"\n[[patch]]\n{entry}\n"))
