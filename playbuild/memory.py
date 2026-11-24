"""The resource map (stock/memory.toml): usable regions, their confidence, top-down placement."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import BuildError, load_toml, missing_keys

KINDS = ("flash", "ram", "saved", "dsp")
CONFIDENCE = ("verified", "static", "unknown", "excluded")


@dataclass(frozen=True)
class Region:
    name: str
    kind: str
    confidence: str
    source: str
    start: int | None = None
    end: int | None = None
    fixed_size: int | None = None
    space: str = ""
    auto: bool = True               # False: never picked automatically; a feature must ask for it by name

    @property
    def size(self) -> int:
        return self.fixed_size if self.fixed_size is not None else self.end - self.start


def load(path: Path) -> dict[str, Region]:
    path = Path(path)
    regions = {}
    for name, r in load_toml(path).get("region", {}).items():
        with missing_keys(f"{path}: region {name}"):
            reg = Region(name, r["kind"], r["confidence"], r["source"], r.get("start"), r.get("end"),
                         r.get("fixed_size"), r.get("space", ""), r.get("auto", True))
        if reg.kind not in KINDS:
            raise BuildError(f"{path}: region {name}: kind {reg.kind!r} is not one of {KINDS}")
        if reg.confidence not in CONFIDENCE:
            raise BuildError(f"{path}: region {name}: confidence {reg.confidence!r} is not one of {CONFIDENCE}")
        if reg.fixed_size is None and (reg.start is None or reg.end is None or reg.end <= reg.start):
            raise BuildError(f"{path}: region {name}: needs start < end, or fixed_size")
        regions[name] = reg
    return regions


def pick(regions: dict[str, Region], kind: str, allow_static: bool = False) -> Region:
    ok = ("verified", "static") if allow_static else ("verified",)
    found = [r for r in regions.values() if r.kind == kind and r.confidence in ok and r.auto]
    if len(found) != 1:
        raise BuildError(f"expected exactly one usable {kind} region, found {[r.name for r in found]}")
    return found[0]


def named(regions: dict[str, Region], name: str) -> Region:
    """A region a feature asks for by name (never picked automatically)."""
    r = regions.get(name)
    if r is None or r.kind != "ram" or r.confidence != "verified" or r.auto or r.start is None:
        raise BuildError(f"region {name}: an ITCM budget needs kind ram, confidence verified, auto = false "
                         f"(memory.toml has {r})")
    return r


def place_top_down(region: Region, size: int, align: int = 8) -> int:
    start = (region.end - size) & ~(align - 1)
    if start < region.start:
        raise BuildError(f"{size} B do not fit in {region.name} "
                         f"({region.size} B, {region.start:#010x}-{region.end:#010x})")
    return start
