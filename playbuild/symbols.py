"""Named stock firmware symbols (stock/symbols.toml) and their check against the stock image."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from capstone import CS_ARCH_ARM, CS_MODE_MCLASS, CS_MODE_THUMB, Cs

from .errors import BuildError, load_toml, missing_keys

APP_BASE = 0x08010000
KINDS = ("entry", "call", "mid")   # mid (PL16): an instruction inside a function; the handlers get the registers
CONTEXTS = ("ui", "dsp_tick", "main", "dsp_locked", "any")   # dsp_locked: reached with the DSP lock held (synth note-on);
                                                             # any: task not identified (checked as the locked ones)


@dataclass(frozen=True)
class Function:
    name: str
    addr: int
    expect: bytes
    proto: str | None
    tags: frozenset[str]


@dataclass(frozen=True)
class Data:
    name: str
    addr: int
    ctype: str


@dataclass(frozen=True)
class HookPoint:
    name: str
    kind: str
    context: str
    args: tuple[str, ...]
    ret: str
    addr: int = 0
    expect: bytes = b""
    displace: int = 0
    target: str = ""
    sites: tuple[int, ...] = ()


@dataclass(frozen=True)
class Symbols:
    functions: dict[str, Function]
    data: dict[str, Data]
    hooks: dict[str, HookPoint]


def load(path: Path) -> Symbols:
    path = Path(path)
    t = load_toml(path)
    functions: dict[str, Function] = {}
    for name, f in t.get("function", {}).items():
        proto = f.get("proto")
        if proto is not None and f"{name}(" not in proto:
            raise BuildError(f"{path}: function {name}: proto must declare `{name}(`: {proto}")
        with missing_keys(f"{path}: function {name}"):
            functions[name] = Function(name, f["addr"], bytes.fromhex(f["expect"]), proto,
                                       frozenset(f.get("tags", [])))
    data = {}
    for n, d in t.get("data", {}).items():
        with missing_keys(f"{path}: data {n}"):
            data[n] = Data(n, d["addr"], d["ctype"])
    hooks: dict[str, HookPoint] = {}
    for name, h in t.get("hook", {}).items():
        with missing_keys(f"{path}: hook {name}"):
            hooks[name] = _hook(path, name, h, functions)
    return Symbols(functions, data, hooks)


def _hook(path: Path, name: str, h: dict, functions: dict[str, Function]) -> HookPoint:
    kind, context = h["kind"], h["context"]
    if kind == "mid":                   # the handlers get the registers (slim_regs_t), not arguments, and return nothing
        if tuple(h.get("args", ())) or h.get("ret", "void") != "void":
            raise BuildError(f"{path}: hook {name}: mid hook: the handlers get the registers (slim_regs_t *), "
                             "so no args and ret = \"void\"")
        h = {**h, "args": [], "ret": "void"}
    args = tuple(h["args"])
    if kind not in KINDS:
        raise BuildError(f"{path}: hook {name}: kind {kind!r} is not one of {KINDS}")
    if context not in CONTEXTS:
        raise BuildError(f"{path}: hook {name}: context {context!r} is not one of {CONTEXTS}")
    if len(args) > 4:
        raise BuildError(f"{path}: hook {name}: at most 4 arguments (r0-r3), got {len(args)}")
    if kind in ("entry", "mid"):
        hp = HookPoint(name, kind, context, args, h["ret"], addr=h["addr"],
                       expect=bytes.fromhex(h["expect"]), displace=h["displace"])
        if hp.displace < 4 or hp.displace % 2 or len(hp.expect) < hp.displace:
            raise BuildError(f"{path}: hook {name}: displace must be even, >= 4 and covered by expect")
    else:
        if h["target"] not in functions or functions[h["target"]].proto is None:
            raise BuildError(f"{path}: hook {name}: target {h['target']!r} must be a function with a proto")
        hp = HookPoint(name, kind, context, args, h["ret"], target=h["target"], sites=tuple(h["sites"]))
    return hp


def _at(image: bytes, addr: int, n: int) -> bytes:
    off = addr - APP_BASE
    if off < 0 or off + n > len(image):
        raise BuildError(f"{addr:#010x} is outside the stock image")
    return image[off:off + n]


def verify(sym: Symbols, image: bytes) -> None:
    errors = []
    for f in sym.functions.values():
        got = _at(image, f.addr, len(f.expect))
        if got != f.expect:
            errors.append(f"function {f.name} at {f.addr:#010x}: expected {f.expect.hex()}, image has {got.hex()}")
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    for h in sym.hooks.values():
        if h.kind in ("entry", "mid"):
            got = _at(image, h.addr, len(h.expect))
            if got != h.expect:
                errors.append(f"hook {h.name} at {h.addr:#010x}: expected {h.expect.hex()}, image has {got.hex()}")
            continue
        target = sym.functions[h.target].addr
        for site in h.sites:
            ins = next(md.disasm(_at(image, site, 4), site), None)
            text = f"{ins.mnemonic} {ins.op_str}" if ins else "undecodable"
            if ins is None or ins.mnemonic != "bl" or ins.op_str != f"#{target:#x}":
                errors.append(f"hook {h.name}: site {site:#010x} is not `bl {target:#x}`: {text}")
    if errors:
        raise BuildError("stock image does not match the symbols:\n  " + "\n  ".join(errors))
