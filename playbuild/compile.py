"""Thin wrappers over the pinned arm-none-eabi tools."""
from __future__ import annotations

import subprocess
from pathlib import Path

from . import toolchain
from .errors import BuildError

ARCH = ["-mcpu=cortex-m7", "-mthumb", "-mfloat-abi=soft"]
CFLAGS = ARCH + [
    "-std=c11", "-Os", "-ffreestanding", "-fno-builtin", "-fno-common",
    "-fno-tree-loop-distribute-patterns",        # never turn our memset / memcpy loops into calls to themselves
    "-fno-delete-null-pointer-checks",           # the ITCM starts at address 0
    "--param=min-pagesize=0",                    # no -Warray-bounds on fixed low addresses (GCC >= 12)
    "-ffunction-sections", "-fdata-sections", "-fstack-usage", "-fcallgraph-info=su",
    "-fno-strict-aliasing",                       # we cast into stock structures
    "-Wdate-time",                               # __DATE__ / __TIME__ would break reproducible builds (error under -Werror)
    "-Wall", "-Wextra", "-Werror",
]
ASFLAGS = ARCH
LDFLAGS = ["-nostdlib", "-nostartfiles", "-Wl,--gc-sections", "-Wl,--build-id=none", "-Wl,--no-warn-rwx-segments",
           "-Wl,--orphan-handling=error"]              # a section the script does not place would escape the RAM budget


def _run(cmd: list) -> str:
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        raise BuildError(f"{Path(str(cmd[0])).name} failed:\n{(r.stderr or r.stdout).strip()}")
    return r.stdout


def compile_sources(units: list[tuple[str, Path]], include_dirs: list[Path], objdir: Path,
                    defines: dict[str, list[str]] | None = None) -> list[Path]:
    """units = (group, source); objects go to objdir/<group>/<name>.o, the source's name kept whole (foo.c.o,
    foo.S.o: a feature may hold both). group = feature name, _runtime or _gen.
    defines: extra flags per group (e.g. {"_runtime": ["-DSLIM_USE_ITCM=1"]})."""
    objs = []
    for group, src in units:
        out = Path(objdir) / group / (Path(src).name + ".o")
        out.parent.mkdir(parents=True, exist_ok=True)
        flags = ASFLAGS if Path(src).suffix == ".S" else CFLAGS + (defines or {}).get(group, [])
        _run([toolchain.tool("gcc"), *flags, *[f"-I{d}" for d in include_dirs], "-c", src, "-o", out])
        objs.append(out)
    return objs


def link(objects: list[Path], ldscript: Path, elf: Path) -> None:
    _run([toolchain.tool("gcc"), *ARCH, *LDFLAGS, f"-Wl,-T,{ldscript}", f"-Wl,-Map,{Path(elf).with_suffix('.map')}",
          *objects, "-lgcc", "-o", elf])


def nm(elf: Path) -> dict[str, int]:
    out = {}
    for line in _run([toolchain.tool("nm"), elf]).splitlines():
        parts = line.split()
        if len(parts) == 3:
            out[parts[2]] = int(parts[0], 16)
    return out


def nm_sizes(elf: Path) -> dict[str, int]:
    """Symbol -> size, for the symbols that have one."""
    out = {}
    for line in _run([toolchain.tool("nm"), "-S", elf]).splitlines():
        parts = line.split()
        if len(parts) == 4:
            out[parts[3]] = int(parts[1], 16)
    return out


def binary(elf: Path, out: Path) -> bytes:
    _run([toolchain.tool("objcopy"), "-O", "binary", "-j", ".text", "-j", ".data", elf, out])
    return Path(out).read_bytes()


def _sections(obj: Path) -> list[tuple[str, int]]:
    out = []
    for line in _run([toolchain.tool("size"), "-A", obj]).splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            out.append((parts[0], int(parts[1])))
    return out


def object_ram(obj: Path) -> int:
    """Bytes of .data* and .bss* sections in one object file (ITCM data, .bss.itcm.*, not included)."""
    return sum(n for name, n in _sections(obj)
               if name.startswith((".data", ".bss")) and not name.startswith(".bss.itcm."))


def object_itcm(obj: Path) -> dict[str, int]:
    """The .bss.itcm.* sections of one object file: name -> bytes."""
    return {name: n for name, n in _sections(obj) if name.startswith(".bss.itcm.")}
