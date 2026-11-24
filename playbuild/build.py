"""Build a version: symbols -> features -> generated sources -> compile -> link twice (RAM top-down) -> image."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import checks, codegen, features, hooks, image, lock, memory, paths, symbols, toolchain
from . import compile as cc
from .errors import BuildError


def _units(version: features.Version, generated: list[Path]) -> list[tuple[str, Path]]:
    units = [("_runtime", paths.RUNTIME / "slim_rt.c")] + [("_gen", p) for p in generated]
    for f in version.features:
        units += [(f.name, s) for s in f.sources]
    return units


SAVED_BLOCK = 0x27024             # CTPlay's saved block (format 2) in the session record: tail + 0 (features/saved/saved.c)
SAVED_ROOM = 988                  # the payload's room: the tail's 1000 B less the 12 B header


def build_once(version_path: Path, work: Path, symbols_path: Path = paths.SYMBOLS,
               memory_path: Path = paths.MEMORY, lock_path: Path | None = None) -> tuple[bytes, bytes, dict]:
    tc = toolchain.require()
    stock = paths.STOCK_BIN.read_bytes()
    sym = symbols.load(symbols_path)
    symbols.verify(sym, stock)
    version = features.load_version(version_path, sym)
    uses = features.handlers(version)
    lk = lock.load(lock_path or paths.SAVE_LOCK)
    saved_fields = {f.name: f.saved for f in version.features}
    placed = lock.check(lk, saved_fields) if any(saved_fields.values()) else []
    targets = hooks.branch_targets(paths.LISTING)
    covered = hooks.it_covered(paths.LISTING) if any(sym.hooks[p].kind == "mid" for p in uses) else frozenset()
    for point in uses:
        if sym.hooks[point].kind == "entry":
            hooks.check_entry(sym.hooks[point], stock, targets)
        elif sym.hooks[point].kind == "mid":
            hooks.check_mid(sym.hooks[point], stock, targets, covered)
    byte_patches = [(f.name, p) for f in version.features for p in f.patches]
    hooks.check_patches(byte_patches, stock, [sym.hooks[p] for p in sorted(uses)])
    regions = memory.load(memory_path)
    flash, ram = memory.pick(regions, "flash"), memory.pick(regions, "ram")
    use_itcm = any(f.itcm_budget for f in version.features)
    itcm = memory.named(regions, "itcm") if use_itcm else None
    gen, obj, elf = work / "gen", work / "obj", work / "slim.elf"
    generated = codegen.write_all(gen, sym, version, flash, ram.start, ram.size, ram.end,
                                  (itcm.start, itcm.size) if itcm else None, lk)
    objs = cc.compile_sources(_units(version, generated), [paths.RUNTIME, gen], obj,
                              {"_runtime": ["-DSLIM_USE_ITCM=1"]} if itcm else None)
    checks.check_itcm_sections(version, obj)
    cc.link(objs, gen / "slim.ld", elf)                                   # pass 1: measure the RAM (and ITCM)
    s = cc.nm(elf)
    ram_used = s["__slim_ram_end"] - s["__slim_ram_start"]
    origin = memory.place_top_down(ram, ram_used)
    itcm_used = s["__slim_itcm_end"] - s["__slim_itcm_start"] if itcm else 0
    itcm_origin = memory.place_top_down(itcm, itcm_used) if itcm else 0
    codegen.write_linker_script(gen, sym, flash, origin, ram.end - origin, ram.end,
                                (itcm_origin, itcm.end - itcm_origin) if itcm else None)
    cc.link(objs, gen / "slim.ld", elf)                                   # pass 2: RAM directly below the heap limit
    s = cc.nm(elf)
    blob = cc.binary(elf, work / "slim.bin")
    store = any(f.name == codegen.SAVED_FEATURE for f in version.features)
    if store:
        checks.check_saved_sizes(placed, cc.nm_sizes(elf))
    stack, edges, dynamic, external = checks.callgraph(sorted(obj.rglob("*.ci")))
    checks.check_calls(stack, edges, dynamic)
    stack_report, uncounted = checks.check_stack(version, stack, edges, external)
    hook_stack = checks.hook_stack(version, sym, stack, edges, external)
    checks.check_dsp_lock(version, sym, edges)
    checks.check_flash_safety(blob, flash.start)
    checks.check_marker(version)
    checks.check_ram_budget(version, obj)
    patches: list[tuple[int, bytes]] = []
    for point in sorted(uses):
        hp = sym.hooks[point]
        if hp.kind in ("entry", "mid"):                                   # the same branch to its stub
            patches.append(hooks.patch_entry(hp, s[f"slim_entry_{point}"] & ~1))
        else:
            patches += hooks.patch_calls(hp, s[f"slim_call_{point}"] & ~1)
    patches += [(p.addr, p.new) for _, p in byte_patches]                 # fixes in stock's code ([[patch]])
    img = image.assemble(stock, flash.start, blob, patches, version.marker)
    syx, info = image.encode(img)
    flash_end = flash.start + len(blob)
    ours = {k: v for k, v in s.items() if flash.start <= v < flash_end or origin <= v <= ram.end
            or (itcm and itcm_origin <= v <= itcm.end)}
    manifest = dict(
        base="circuittracks-firmware-4486 (1.2.1)", slim_version=version.name, marker=version.marker,
        description=version.description, **({"release": version.release} if version.release else {}),
        features=[f.name for f in version.features], toolchain=tc,
        image_size=hex(len(img)), image_sha256=image.sha256(img), syx_sha256=image.sha256(syx), crc32=hex(info["crc"]),
        flash=dict(start=hex(flash.start), end=hex(flash_end), used=len(blob), size=flash.size),
        ram=dict(start=hex(origin), end=hex(ram.end), used=ram_used, size=ram.size),
        stack=stack_report, stack_uncounted_callees=uncounted, entry_stub_stack=checks.ENTRY_STUB_STACK,
        hook_stack=hook_stack, stack_uncounted_libgcc=checks.libgcc_calls(elf.with_suffix(".map")),
        patches=[dict(addr=hex(a), bytes=b.hex()) for a, b in patches],
        symbols={k: hex(v) for k, v in sorted(ours.items())},
    )
    if store:
        manifest["saved"] = dict(layout_id=lk.layout_id, payload=lk.length, format=2, block=f"record + {SAVED_BLOCK:#x}",
                                 room=SAVED_ROOM,
                                 fields=[dict(symbol=e.symbol, offset=e.offset, size=e.size) for e in placed])
    if itcm:                                                              # only when used: older manifests unchanged
        manifest["itcm"] = dict(start=hex(itcm_origin), end=hex(itcm.end), used=itcm_used, size=itcm.size)
    return img, syx, manifest


def build(version_path: Path, outdir: Path | None = None, symbols_path: Path = paths.SYMBOLS,
          memory_path: Path = paths.MEMORY) -> dict:
    version_path = Path(version_path)
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        img, syx, manifest = build_once(version_path, Path(a), symbols_path, memory_path)
        img2, _, _ = build_once(version_path, Path(b), symbols_path, memory_path)
    if img != img2:
        raise BuildError("two builds of the same version differ: the build is not reproducible")
    out = Path(outdir) if outdir else paths.BUILD / version_path.stem
    out.mkdir(parents=True, exist_ok=True)
    stem = f"circuittracks-4486-{manifest['marker']}"
    (out / f"{stem}.bin").write_bytes(img)
    (out / f"{stem}.syx").write_bytes(syx)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
