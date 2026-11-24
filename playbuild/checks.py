"""Build checks: the rules that keep a slim build safe to flash."""
from __future__ import annotations

import re
import struct
from pathlib import Path

from capstone import CS_ARCH_ARM, CS_MODE_MCLASS, CS_MODE_THUMB, Cs

from . import compile as cc
from .errors import BuildError, load_toml
from .features import Version, handlers
from .paths import VERSIONS
from .symbols import Symbols

ENTRY_STUB_STACK = 32      # push {r4, lr} + 8 + push {r0-r3} in the generated entry stubs
MID_STUB_STACK = 64        # 8 + push {r0-r12, lr} in the generated mid stubs (codegen._mid_stub)
STUB_STACK = {"entry": ENTRY_STUB_STACK, "mid": MID_STUB_STACK}
_NODE = re.compile(r'node:\s*\{\s*title:\s*"([^"]+)"\s*label:\s*"([^"]*)"')
_EDGE = re.compile(r'edge:\s*\{\s*sourcename:\s*"([^"]+)"\s*targetname:\s*"([^"]+)"')
_STACK = re.compile(r"(\d+) bytes \((static|dynamic|dynamic,bounded)\)")
_LIBGCC = re.compile(r"libgcc\.a\([^)]+\)\n\s+\S+ \(([^)]+)\)")      # map: archive member, then "file (symbol)"
# The range is wider than the register block (0x40023C00-0x40023FFF): the compiler may load a base pointer and add an
# imm12 (positive) or imm8 (negative) offset, so the literal itself can sit up to 4 KiB below / 256 B above the block.
# The unlock keys are checked too: the flash controller ignores writes until it has been unlocked with them.
FORBIDDEN = ((0x40022C00, 0x40024100, "flash interface registers, or a base pointer that reaches them with an offset"),
             (0x1FFF0000, 0x20000000, "option bytes / system memory"))
UNLOCK_KEYS = {0x45670123: "flash unlock key 1", 0xCDEF89AB: "flash unlock key 2",
               0x08192A3B: "option-byte unlock key 1", 0x4C5D6E7F: "option-byte unlock key 2"}


def callgraph(ci_files: list[Path]) -> tuple[dict[str, int], dict[str, set[str]], set[str], set[str]]:
    """Stack per function, call edges, dynamic-stack functions, and external callees (nodes never given a stack line)."""
    stack: dict[str, int] = {}
    edges: dict[str, set[str]] = {}
    dynamic: set[str] = set()
    bare: set[str] = set()
    defined: set[str] = set()
    for f in ci_files:
        text = Path(f).read_text()
        for title, label in _NODE.findall(text):
            m = _STACK.search(label.replace("\\n", "\n"))
            if m:
                defined.add(title)
                stack[title] = int(m.group(1))
                if m.group(2) != "static":
                    dynamic.add(title)
            else:
                bare.add(title)
                stack.setdefault(title, 0)
        for src, dst in _EDGE.findall(text):
            edges.setdefault(src, set()).add(dst)
    return stack, edges, dynamic, bare - defined


def check_calls(stack: dict[str, int], edges: dict[str, set[str]], dynamic: set[str]) -> None:
    indirect = sorted(src for src, dsts in edges.items() if "__indirect_call" in dsts)
    if indirect:
        raise BuildError("indirect calls (function pointers) are not allowed in slim code: " + ", ".join(indirect))
    if dynamic:
        raise BuildError("dynamic stack allocation (VLA / alloca) is not allowed: " + ", ".join(sorted(dynamic)))


def _worst(fn: str, stack: dict[str, int], edges: dict[str, set[str]], path: tuple[str, ...] = ()) -> int:
    if fn in path:
        raise BuildError("recursion is not allowed: " + " -> ".join(path + (fn,)))
    callees = edges.get(fn, ())
    return stack.get(fn, 0) + max((_worst(c, stack, edges, path + (fn,)) for c in callees), default=0)


def _external_reachable(fn: str, edges: dict[str, set[str]], external: set[str]) -> set[str]:
    seen, todo = set(), [fn]
    while todo:
        cur = todo.pop()
        if cur in seen:
            continue
        seen.add(cur)
        todo.extend(edges.get(cur, ()))
    return seen & external


def check_stack(version: Version, stack: dict[str, int], edges: dict[str, set[str]], external: set[str]) -> tuple[dict[str, int], dict[str, list[str]]]:
    report, uncounted, errors = {}, {}, []
    for f in version.features:
        for fn in [u.handler for u in f.hooks] + ([f.init] if f.init else []):
            worst = report[fn] = _worst(fn, stack, edges)
            uncounted[fn] = sorted(_external_reachable(fn, edges, external))
            if worst > f.stack_budget:
                errors.append(f"{f.name}: {fn} needs {worst} B of stack (slim code only; not counted: "
                              f"{', '.join(uncounted[fn]) or 'none'}), budget {f.stack_budget} B")
    if errors:
        raise BuildError("stack budget exceeded:\n  " + "\n  ".join(errors))
    return report, uncounted


def _root(point: str, kind: str) -> str:
    """The slim function a hook point enters: the dispatcher behind an entry or mid stub, or the call wrapper."""
    return f"slim_dispatch_{point}" if kind in ("entry", "mid") else f"slim_call_{point}"


def hook_stack(version: Version, sym: Symbols, stack: dict[str, int], edges: dict[str, set[str]],
               external: set[str]) -> dict[str, dict]:
    """Worst case per hook point: entry stub + dispatcher or call wrapper + the larger of slim_ready() (which runs
    every init() on the first call) and the handlers. Stock callees and libgcc are listed, not counted."""
    report = {}
    for point in sorted(handlers(version)):
        hp = sym.hooks[point]
        root = _root(point, hp.kind)
        stub = STUB_STACK.get(hp.kind, 0)
        report[point] = dict(bytes=stub + _worst(root, stack, edges),
                             uncounted=sorted(_external_reachable(root, edges, external)))
    return report


def libgcc_calls(map_file: Path) -> list[str]:
    """libgcc functions the link pulled in: GCC's call graph does not show calls to them, so no stack count has them."""
    return sorted(set(_LIBGCC.findall(Path(map_file).read_text())))


def _path_to(fn: str, goal: str, edges: dict[str, set[str]], seen: frozenset = frozenset()) -> list[str] | None:
    if fn == goal:
        return [fn]
    if fn in seen:
        return None
    for c in sorted(edges.get(fn, ())):
        p = _path_to(c, goal, edges, seen | {fn})
        if p:
            return [fn] + p
    return None


LOCKED = {"dsp_tick": "from the DSP tick",                       # the main loop holds the lock (SC19)
          "dsp_locked": "while the synth note-on holds it",       # stock's voice decision runs inside the note-on
          "any": "from a task slim has not identified"}           # it may hold the lock


def check_dsp_lock(version: Version, sym: Symbols, edges: dict[str, set[str]]) -> None:
    lock = sorted(n for n, f in sym.functions.items() if "takes_dsp_lock" in f.tags)
    errors = []
    for point in sorted(handlers(version)):
        hp = sym.hooks[point]
        if hp.context not in LOCKED:
            continue
        root = _root(point, hp.kind)
        # A call wrapper's own call of the hooked stock function is stock's (made whatever slim does): not counted.
        own = {root: edges.get(root, set()) - {hp.target}} if hp.kind == "call" else {}
        for goal in lock:
            p = _path_to(root, goal, {**edges, **own})
            if p:
                errors.append(f"{' -> '.join(p)} takes the DSP-service lock {LOCKED[hp.context]}: the device would hang")
    if errors:
        raise BuildError("\n".join(errors))


def check_flash_safety(blob: bytes, base: int) -> None:
    hits = []

    def test(addr: int, value: int) -> None:
        for lo, hi, what in FORBIDDEN:
            if lo <= value < hi:
                hits.append(f"{addr:#010x}: {value:#010x} ({what})")
        if value in UNLOCK_KEYS:
            hits.append(f"{addr:#010x}: {value:#010x} ({UNLOCK_KEYS[value]})")

    for off in range(0, len(blob) - 3, 4):
        test(base + off, struct.unpack_from("<I", blob, off)[0])
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    md.skipdata = True
    low: dict[str, int] = {}
    for i in md.disasm(blob, base):
        m = re.fullmatch(r"(\w+), #(0x[0-9a-f]+|\d+)", i.op_str)
        if not m:
            continue
        reg, imm = m.group(1), int(m.group(2), 0)
        if i.mnemonic == "movw":
            low[reg] = imm
        elif i.mnemonic == "movt" and reg in low:
            test(i.address, imm << 16 | low[reg])
    if hits:
        raise BuildError("slim code must never touch the flash controller or the option bytes:\n  " + "\n  ".join(hits))


def _key(marker: str) -> bytes:
    return marker.encode("ascii").ljust(6, b"\0")[:6]


def check_marker(version: Version, versions: Path = VERSIONS) -> None:
    """No other version file may share the marker's first 6 bytes. Upstream's SC / RC markers cannot clash: CTPlay's
    are SL / PL only (features.py)."""
    mine, clashes = _key(version.marker), []
    for v in sorted(Path(versions).rglob("*.toml")):
        if v.resolve() == Path(version.path).resolve():
            continue
        m = load_toml(v).get("marker")
        if m and _key(m) == mine:
            clashes.append(f"slim {v.relative_to(versions)}")
    if clashes:
        raise BuildError(f"marker {version.marker} is already used by {', '.join(clashes)}: "
                         "the bootloader would not install one over the other")


def check_ram_budget(version: Version, objdir: Path) -> None:
    errors, itcm_errors = [], []
    for f in version.features:
        objs = sorted((Path(objdir) / f.name).glob("*.o"))
        used = sum(cc.object_ram(o) for o in objs)
        if used > f.ram_budget:
            errors.append(f"{f.name} uses {used} B of RAM, budget {f.ram_budget} B")
        itcm = sum(n for o in objs for n in cc.object_itcm(o).values())
        if f.itcm_budget and itcm > f.itcm_budget:
            itcm_errors.append(f"{f.name} uses {itcm} B of ITCM, budget {f.itcm_budget} B")
    if errors:
        raise BuildError("RAM budget exceeded:\n  " + "\n  ".join(errors))
    if itcm_errors:
        raise BuildError("ITCM budget exceeded:\n  " + "\n  ".join(itcm_errors))


def check_itcm_sections(version: Version, objdir: Path) -> None:
    """ITCM data only in features with an ITCM budget: without the .itcm statement (no budget in the version) the
    linker's *(.bss.*) would put it in the heap tail silently. The runtime and the generated code never have any."""
    budget = {f.name: f.itcm_budget for f in version.features}
    errors = []
    for group in sorted(p.name for p in Path(objdir).iterdir() if p.is_dir()):
        names = sorted(n for o in sorted((Path(objdir) / group).glob("*.o")) for n in cc.object_itcm(o))
        if names and not budget.get(group):
            errors.append(f"{group}: ITCM data ({', '.join(names)}) without an ITCM budget")
    if errors:
        raise BuildError("\n".join(errors))


def check_saved_sizes(placed, sizes: dict[str, int]) -> None:
    """A saved field's declared size is the size of its global in the build: a load must never write past it."""
    errors = [f"{e.symbol}: declared {e.size} B, the build's symbol has {sizes.get(e.symbol)} B"
              for e in placed if sizes.get(e.symbol) != e.size]
    if errors:
        raise BuildError("saved fields:\n  " + "\n  ".join(errors))
