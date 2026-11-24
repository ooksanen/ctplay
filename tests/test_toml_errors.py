"""A missing key or a TOML syntax error in any file playbuild reads is a BuildError that names the file (and the
table), never a KeyError or TOMLDecodeError traceback (followups, tooling polish)."""
import re

import pytest

from helpers import write_feature, write_version
from playbuild import features, lock, memory, paths, symbols
try:
    from playbuild import vote
except ImportError:                               # the public tree has no vote page
    vote = None
from playbuild.errors import BuildError

SYM = symbols.load(paths.SYMBOLS)


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return p


@pytest.mark.parametrize("load, text, match", [
    (symbols.load, '[function.f]\naddr = 0x08033320\n', "function f: missing key 'expect'"),
    (symbols.load, '[data.d]\naddr = 0x20000000\n', "data d: missing key 'ctype'"),
    (symbols.load, '[hook.h]\nkind = "entry"\ncontext = "ui"\nargs = []\nret = "void"\n', "hook h: missing key 'addr'"),
    (memory.load, '[region.r]\nkind = "ram"\nstart = 0\nend = 4\nsource = "x"\n', "region r: missing key 'confidence'"),
    (lock.load, '[[field]]\nfeature = "a"\nsymbol = "a_x"\noffset = 0\n', "field: missing key 'size'"),
], ids=["function", "data", "hook", "region", "lock"])
def test_a_missing_key_names_the_table(tmp_path, load, text, match):
    p = write(tmp_path, "x.toml", text)
    with pytest.raises(BuildError, match=re.escape(f"{p}: {match}")):
        load(p)


_LOADERS = [symbols.load, memory.load, lock.load] + ([vote.load] if vote else [])
_IDS = ["symbols", "memory", "lock"] + (["vote"] if vote else [])


@pytest.mark.parametrize("load", _LOADERS, ids=_IDS)
def test_a_syntax_error_names_the_file_and_line(tmp_path, load):
    p = write(tmp_path, "x.toml", 'a = 1\nb = "unterminated\n')
    with pytest.raises(BuildError, match=re.escape(str(p)) + r".*line 2"):
        load(p)


def test_version_missing_features(tmp_path):
    p = write(tmp_path, "v.toml", 'marker = "SLX1"\n')
    with pytest.raises(BuildError, match=re.escape(f"{p}: missing key 'features'")):
        features.load_version(p, SYM)


def test_version_syntax_error(tmp_path):
    p = write(tmp_path, "v.toml", 'marker = "SLX1"\nfeatures = [\n')
    with pytest.raises(BuildError, match=re.escape(str(p))):
        features.load_version(p, SYM)


@pytest.mark.parametrize("drop, key", [("budget", "budget"), ("sources", "sources"), ("description", "description")])
def test_feature_missing_key(tmp_path, drop, key):
    fd = tmp_path / "f"
    d = write_feature(fd, "a")
    toml = d / "feature.toml"
    toml.write_text("\n".join(l for l in toml.read_text().splitlines() if not l.startswith(drop)
                              and not (drop == "budget" and l.startswith(("ram", "stack", "[budget]")))) + "\n")
    with pytest.raises(BuildError, match=re.escape(f"{toml}: missing key '{key}'")):
        features.load_version(write_version(tmp_path, "v", "SLX1", ["a"], fd), SYM)


def test_saved_field_missing_symbol(tmp_path):
    d = write_feature(tmp_path / "f", "a")
    (d / "feature.toml").write_text((d / "feature.toml").read_text() + '\n[[saved]]\nbytes = 1\n')
    with pytest.raises(BuildError, match="saved field None: missing key 'symbol'"):
        features.load_feature(d)


def test_another_version_file_with_a_syntax_error_is_named(tmp_path):
    """check_marker reads every other version file for marker clashes."""
    from playbuild import checks
    (tmp_path / "broken.toml").write_text("marker = \n")
    v = features.Version("v", tmp_path / "v.toml", "SLX1", "", ())
    with pytest.raises(BuildError, match="broken.toml"):
        checks.check_marker(v, versions=tmp_path)
