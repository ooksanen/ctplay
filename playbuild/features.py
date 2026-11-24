"""Feature units (features/<name>/feature.toml) and versions (versions/<NAME>.toml)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .errors import BuildError, load_toml, missing_keys
from .paths import FEATURES
from .symbols import Symbols

RELEASE = re.compile(r"\d+\.\d+(\.\d+)?( beta \d+)?")
MARKER = re.compile(r"(?:SL|PL)[0-9A-Z.]{1,4}")   # SL = foundation diagnostics (SL00D), PL = CTPlay builds


@dataclass(frozen=True)
class HookUse:
    point: str
    handler: str
    priority: int
    filter: bool = False      # call hooks on non-void functions: the handler returns the value passed on


@dataclass(frozen=True)
class SavedField:
    symbol: str               # a global of the feature, saved as its byte image
    size: int
    default: bytes            # what a load without (valid) data gives it; len == size
    rev: int = 1              # what the field's bits mean, for the CTCtrl link: bumped when that changes (the lock pins it)
    link: bool = True         # readable and writable over the CTCtrl link (false: device navigation, e.g. the open page)


@dataclass(frozen=True)
class BytePatch:
    """[[patch]]: a fix in stock's own code (beta 2: the CC 27 crash). The build checks `stock` against the official
    image and refuses an overlap with another patch or a hook site the version uses (hooks.check_patches)."""
    addr: int
    stock: bytes
    new: bytes
    why: str


@dataclass(frozen=True)
class Feature:
    name: str
    path: Path
    description: str
    depends: tuple[str, ...]
    sources: tuple[Path, ...]
    init: str | None
    hooks: tuple[HookUse, ...]
    ram_budget: int
    stack_budget: int
    itcm_budget: int = 0      # bytes of ITCM (region `itcm` of memory.toml); 0 = none
    saved: tuple[SavedField, ...] = ()   # [[saved]]: saved with the project (save_layout.lock fixes their places)
    saved_fix: str | None = None         # run (UI task) after a load wrote the saved fields: per-field validity, tidy-up
    link_valid: str | None = None        # CTCtrl link: int f(cand, old): did the write make any part odd?
    link_apply: str | None = None        # CTCtrl link: void f(const uint8_t *old): the pads' side effects of a write
    conflicts: tuple[str, ...] = ()      # features this one is never built with
    patches: tuple[BytePatch, ...] = ()  # [[patch]]: bytes of stock's code replaced (checked in build.py)


@dataclass(frozen=True)
class Version:
    name: str
    path: Path
    marker: str
    description: str
    features: tuple[Feature, ...]
    release: str = ""   # the public version ("1.0 beta 1"), empty for builds that have none


def load_feature(directory: Path) -> Feature:
    directory = Path(directory)
    with missing_keys(f"{directory}/feature.toml"):
        return _feature(directory, load_toml(directory / "feature.toml"))


def _feature(directory: Path, t: dict) -> Feature:
    if t["name"] != directory.name:
        raise BuildError(f"{directory}/feature.toml: name {t['name']!r} must equal the directory name")
    hooks = tuple(HookUse(h["point"], h["handler"], h["priority"], bool(h.get("filter", False)))
                  for h in t.get("hook", []))
    budget = t["budget"]
    return Feature(t["name"], directory, t["description"], tuple(t.get("depends", [])),
                   tuple(directory / s for s in t["sources"]), t.get("init"), hooks,
                   budget["ram"], budget["stack"], budget.get("itcm", 0),
                   tuple(_saved_field(directory, s) for s in t.get("saved", [])), t.get("saved_fix"),
                   t.get("link_valid"), t.get("link_apply"), tuple(t.get("conflicts", [])),
                   tuple(_byte_patch(directory, p) for p in t.get("patch", [])))


def _byte_patch(directory: Path, p: dict) -> BytePatch:
    where = f"{directory}/feature.toml: patch at {p.get('addr', 0):#010x}"
    with missing_keys(where):
        addr, why = p["addr"], p["why"]
        try:
            stock, new = bytes.fromhex(p["stock"]), bytes.fromhex(p["new"])
        except ValueError as e:
            raise BuildError(f"{where}: stock / new must be hex bytes ({e})") from None
    if addr % 2:
        raise BuildError(f"{where}: the address must be even (Thumb code)")
    if len(stock) != len(new):
        raise BuildError(f"{where}: stock and new must have the same length ({len(stock)} / {len(new)} B)")
    if not 2 <= len(new) <= 16:
        raise BuildError(f"{where}: a patch has 2-16 bytes, got {len(new)}")
    if stock == new:
        raise BuildError(f"{where}: the patch changes nothing")
    return BytePatch(addr, stock, new, why)


def _saved_field(directory: Path, s: dict) -> SavedField:
    where = f"{directory}/feature.toml: saved field {s.get('symbol')!r}"
    with missing_keys(where):
        size, symbol = s["bytes"], s["symbol"]
    if not 1 <= size <= 64:
        raise BuildError(f"{where}: bytes must be 1-64, got {size}")
    if s.get("store", "project") != "project":
        raise BuildError(f"{where}: store {s['store']!r}: only \"project\" exists (no device store yet)")
    default = bytes.fromhex(s.get("default", "00" * size))
    if len(default) != size:
        raise BuildError(f"{where}: default has {len(default)} B, the field {size}")
    rev = s.get("rev", 1)
    if not 1 <= rev <= 127:
        raise BuildError(f"{where}: rev must be 1-127, got {rev}")
    return SavedField(symbol, size, default, rev, bool(s.get("link", True)))


def load_version(path: Path, sym: Symbols) -> Version:
    path = Path(path)
    t = load_toml(path)
    with missing_keys(str(path)):
        marker, names = t["marker"], t["features"]
    if not MARKER.fullmatch(marker):
        raise BuildError(f"{path}: marker {marker!r} must be SL or PL + 1-4 of 0-9 A-Z . (at most 6 bytes)")
    release = t.get("release", "")
    if release and not RELEASE.fullmatch(release):
        raise BuildError(f"{path}: release {release!r} must look like 1.0, 1.0.1 or 1.0 beta 1")
    dirs = [path.parent / d for d in t.get("feature_dirs", [])] or [FEATURES]
    loaded = {}
    for name in names:
        found = [d / name for d in dirs if (d / name / "feature.toml").exists()]
        if not found:
            raise BuildError(f"{path}: feature {name} not found in {[str(d) for d in dirs]}")
        loaded[name] = load_feature(found[0])
    for f in loaded.values():
        for dep in f.depends:
            if dep not in loaded:
                raise BuildError(f"{path}: {f.name} depends on {dep}, which this version does not include")
        for other in f.conflicts:
            if other in loaded:
                raise BuildError(f"{path}: {f.name} cannot be built together with {other}")
        for use in f.hooks:
            if use.point not in sym.hooks:
                raise BuildError(f"{f.name}: unknown hook point {use.point}")
            hp = sym.hooks[use.point]
            if use.filter and (hp.kind != "call" or hp.ret == "void"):
                raise BuildError(f"{f.name}: {use.handler}: filter = true needs a call hook on a function that returns "
                                 f"a value ({use.point} is {hp.kind}, {hp.ret})")
    seen: dict[str, str] = {}
    for f in loaded.values():
        named = (f.init, f.saved_fix, f.link_valid, f.link_apply)
        for c_name in [u.handler for u in f.hooks] + [n for n in named if n]:
            if c_name in seen:
                raise BuildError(f"handler {c_name} is defined by both {seen[c_name]} and {f.name}")
            seen[c_name] = f.name
    order: list[Feature] = []
    pending = dict(loaded)
    while pending:
        ready = sorted(n for n, f in pending.items() if all(d in {o.name for o in order} for d in f.depends))
        if not ready:
            raise BuildError(f"{path}: dependency cycle among {sorted(pending)}")
        for n in ready:
            order.append(pending.pop(n))
    return Version(path.stem, path, marker, t.get("description", ""), tuple(order), release)


def handlers(version: Version) -> dict[str, list[tuple[Feature, HookUse]]]:
    out: dict[str, list[tuple[Feature, HookUse]]] = {}
    for f in version.features:
        for use in f.hooks:
            out.setdefault(use.point, []).append((f, use))
    for uses in out.values():
        uses.sort(key=lambda fu: (fu[1].priority, fu[0].name))
    return out
