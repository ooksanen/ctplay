"""save_layout.lock: where each saved field sits in CTPlay's saved block (spec 2026-10-17-saved-settings-design.md,
"Versioning and the lock"). A field keeps the payload offset and size it was given the first time a build had it; new
fields go after the last one (`--update-lock`); a retired field stays as a tombstone (its bytes reserved, written 0).
Reusing a tombstone, or changing what a field means, needs a layout-ID bump, after which older blocks load as defaults."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from .errors import BuildError, load_toml, missing_keys
from .features import SavedField

HEADER = """# CTPlay's saved block layout (playbuild/lock.py; spec docs/specs/2026-10-17-saved-settings-design.md).
# Committed. A field keeps its offset forever: new fields are appended by `python -m playbuild VERSION --update-lock`.
# Retire a field by adding `tombstone = true` and `retired_in = <layout_id>`; reusing it needs layout_id + 1.
"""


@dataclass(frozen=True)
class LockEntry:
    feature: str
    symbol: str
    offset: int
    size: int
    tombstone: bool = False
    retired_in: int = 0       # a tombstone: the layout ID it was retired under
    rev: int = 1              # what the bits mean (CTCtrl link); only ever goes up, written when not 1


@dataclass(frozen=True)
class Lock:
    layout_id: int
    entries: tuple[LockEntry, ...]

    @property
    def length(self) -> int:
        return max((e.offset + e.size for e in self.entries), default=0)


Fields = dict[str, tuple[SavedField, ...]]   # feature name -> its saved fields, for every feature in the version


def load(path: Path) -> Lock:
    path = Path(path)
    if not path.exists():
        return Lock(1, ())
    t = load_toml(path)
    with missing_keys(f"{path}: field"):
        return Lock(t.get("layout_id", 1), tuple(LockEntry(e["feature"], e["symbol"], e["offset"], e["size"],
                                                           e.get("tombstone", False), e.get("retired_in", 0),
                                                           e.get("rev", 1))
                                                 for e in t.get("field", [])))


def _errors(lk: Lock, fields: Fields) -> tuple[list[str], list[tuple[str, SavedField]]]:
    """(errors, new fields) of the version's fields against the lock."""
    live = {e.symbol: e for e in lk.entries if not e.tombstone}
    errors, new = [], []
    for feature, fs in fields.items():
        for f in fs:
            e = live.get(f.symbol)
            if e is None:
                if any(t.symbol == f.symbol and t.tombstone and t.retired_in >= lk.layout_id for t in lk.entries):
                    errors.append(f"{feature}: {f.symbol} was retired (a tombstone in layout {lk.layout_id}): "
                                  "reusing it needs layout_id + 1")
                else:
                    new.append((feature, f))
            elif e.feature != feature:
                errors.append(f"{f.symbol}: locked for feature {e.feature}, now declared by {feature}")
            elif e.size != f.size:
                errors.append(f"{feature}: {f.symbol} is locked at {e.size} B, now {f.size} B: a field never changes "
                              "size (retire it and add a new one)")
            elif f.rev < e.rev:
                errors.append(f"{feature}: {f.symbol}: rev {f.rev} is below the locked rev {e.rev}: a rev never goes "
                              "down")
    for e in lk.entries:
        if not e.tombstone and e.feature in fields and e.symbol not in {f.symbol for f in fields[e.feature]}:
            errors.append(f"{e.feature}: {e.symbol} is in the lock but no longer declared: mark it a tombstone "
                          f"(tombstone = true, retired_in = {lk.layout_id})")
    return errors, new


def check(lk: Lock, fields: Fields) -> list[LockEntry]:
    """The lock entries of the version's fields; any field the lock does not place, or places differently, fails."""
    errors, new = _errors(lk, fields)
    errors += [f"{feature}: {f.symbol} is not in save_layout.lock: build once with --update-lock" for feature, f in new]
    locked = {e.symbol: e.rev for e in lk.entries if not e.tombstone}
    errors += [f"{feature}: {f.symbol}: rev changed from {locked[f.symbol]} to {f.rev}: build once with --update-lock"
               for feature, fs in fields.items() for f in fs if f.symbol in locked and f.rev > locked[f.symbol]]
    if errors:
        raise BuildError("save_layout.lock:\n  " + "\n  ".join(errors))
    declared = {f.symbol for fs in fields.values() for f in fs}
    return [e for e in lk.entries if not e.tombstone and e.symbol in declared]


def update(path: Path, fields: Fields) -> Lock:
    """Append the version's new fields after the last entry and write the lock; the other errors still fail."""
    lk = load(path)
    errors, new = _errors(lk, fields)
    if errors:
        raise BuildError("save_layout.lock:\n  " + "\n  ".join(errors))
    revs = {f.symbol: f.rev for fs in fields.values() for f in fs}
    entries = [replace(e, rev=revs[e.symbol]) if not e.tombstone and e.symbol in revs else e for e in lk.entries]
    end = lk.length
    for feature, f in new:
        entries.append(LockEntry(feature, f.symbol, end, f.size, rev=f.rev))
        end += f.size
    out = Lock(lk.layout_id, tuple(entries))
    Path(path).write_text(_dump(out))
    return out


def _dump(lk: Lock) -> str:
    out = [HEADER, f"layout_id = {lk.layout_id}\n"]
    for e in lk.entries:
        out.append(f'\n[[field]]\nfeature = "{e.feature}"\nsymbol = "{e.symbol}"\noffset = {e.offset}\nsize = {e.size}\n')
        if e.rev != 1:
            out.append(f"rev = {e.rev}\n")
        if e.tombstone:
            out.append(f"tombstone = true\nretired_in = {e.retired_in}\n")
    return "".join(out)
