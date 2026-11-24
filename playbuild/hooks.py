"""Patch sites: can an entry hook safely displace the stock instructions, and the branch encodings."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from capstone import CS_ARCH_ARM, CS_GRP_BRANCH_RELATIVE, CS_GRP_CALL, CS_GRP_JUMP, CS_MODE_MCLASS, CS_MODE_THUMB, Cs

from .errors import BuildError
from .paths import TOOLS
from .symbols import APP_BASE, HookPoint

sys.path.insert(0, str(TOOLS))
from thumb import b_w, bl  # noqa: E402  (upstream's Thumb encoders)

_CONDS = "eq|ne|hs|cs|lo|cc|mi|pl|vs|vc|hi|ls|ge|lt|gt|le|al"
_BRANCH = re.compile(rf"^([0-9a-f]{{8}}):\s+(?:b|bl|blx|b\.w|b(?:{_CONDS})(?:\.w)?|cbn?z)\s+(?:r\d+, )?#(0x[0-9a-f]+)\s*$")
_PC_MNEMONICS = {"adr", "cbz", "cbnz", "tbb", "tbh"}


def branch_targets(listing: Path) -> frozenset[int]:
    """Every direct branch / call target in upstream's listing of the stock image (re/app.asm)."""
    out = set()
    for line in Path(listing).read_text().splitlines():
        m = _BRANCH.match(line)
        if m:
            out.add(int(m.group(2), 16))
    return frozenset(out)


_INSN = re.compile(r"^([0-9a-f]{8}):\s+(\S+)")
_IT = re.compile(r"^it([te]{0,3})$")


def it_covered(listing: Path) -> frozenset[int]:
    """Every instruction an IT block covers (the 1-4 after each `it`), in upstream's listing of the stock image."""
    out, left = set(), 0
    for line in Path(listing).read_text().splitlines():
        m = _INSN.match(line)
        if not m:
            continue
        if left:
            out.add(int(m.group(1), 16))
            left -= 1
        it = _IT.match(m.group(2))
        if it:
            left = 1 + len(it.group(1))
    return frozenset(out)


def check_mid(hp: HookPoint, image: bytes, targets: frozenset[int], covered: frozenset[int]) -> None:
    """A mid hook: an entry hook's rules for the displaced bytes, and not inside an IT block (its condition would not
    reach the stub's branch, and the displaced instructions run unconditionally there)."""
    if hp.addr in covered:
        raise BuildError(f"hook {hp.name}: {hp.addr:#010x} is inside an IT block")
    check_entry(hp, image, targets)


def check_entry(hp: HookPoint, image: bytes, targets: frozenset[int]) -> None:
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    md.detail = True
    off = hp.addr - APP_BASE
    insns = list(md.disasm(image[off:off + hp.displace], hp.addr))
    if sum(i.size for i in insns) != hp.displace:
        raise BuildError(f"hook {hp.name}: {hp.displace} displaced bytes do not end on an instruction boundary")
    for i in insns:
        pc_dependent = (i.mnemonic in _PC_MNEMONICS or i.mnemonic.startswith("it") or "pc" in i.op_str
                        or any(i.group(g) for g in (CS_GRP_JUMP, CS_GRP_CALL, CS_GRP_BRANCH_RELATIVE)))
        if pc_dependent:
            raise BuildError(f"hook {hp.name}: {i.address:#010x} `{i.mnemonic} {i.op_str}` depends on the program "
                             f"counter and cannot be moved into a stub")
    inside = sorted(t for t in targets if hp.addr < t < hp.addr + hp.displace)
    if inside:
        raise BuildError(f"hook {hp.name}: other code branches into the displaced bytes at "
                         + ", ".join(f"{t:#010x}" for t in inside))


def patch_entry(hp: HookPoint, stub_addr: int) -> tuple[int, bytes]:
    return hp.addr, b_w(hp.addr, stub_addr) + b"\x00\xbf" * ((hp.displace - 4) // 2)   # bf00 = nop


def patch_calls(hp: HookPoint, target_addr: int) -> list[tuple[int, bytes]]:
    return [(site, bl(site, target_addr)) for site in hp.sites]


def _hook_ranges(hp: HookPoint) -> list[tuple[int, int]]:
    if hp.kind in ("entry", "mid"):
        return [(hp.addr, hp.addr + hp.displace)]
    return [(site, site + 4) for site in hp.sites]


def check_patches(patches: list[tuple[str, "BytePatch"]], image: bytes, used: list[HookPoint]) -> None:
    """Byte patches (feature [[patch]], beta 2): inside the stock image, on its expected bytes, and clear of each other
    and of every hook site the version uses (an entry / mid hook's displaced bytes, a call hook's 4-byte sites)."""
    ranges = [(a, b, f"hook {hp.name}") for hp in used for a, b in _hook_ranges(hp)]
    for name, p in patches:
        off, end = p.addr - APP_BASE, p.addr + len(p.new)
        if off < 0 or off + len(p.new) > len(image):
            raise BuildError(f"{name}: patch at {p.addr:#010x} is outside the stock image")
        have = image[off:off + len(p.stock)]
        if have != p.stock:
            raise BuildError(f"{name}: patch at {p.addr:#010x}: stock has {have.hex(' ')}, the patch expects "
                             f"{p.stock.hex(' ')}")
        for a, b, what in ranges:
            if p.addr < b and a < end:
                raise BuildError(f"{name}: patch at {p.addr:#010x} overlaps {what}")
        ranges.append((p.addr, end, f"patch {name}"))
