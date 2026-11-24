import hashlib
import json
import subprocess
import sys

import pytest
from capstone import CS_ARCH_ARM, CS_MODE_MCLASS, CS_MODE_THUMB, Cs
from conftest import NULL_VERSION

from playbuild import __main__ as cli
from playbuild import build, features, image, paths
from playbuild.errors import BuildError

B = 0x08010000
MD = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)


def sym(man, name):
    return int(man["symbols"][name], 16) & ~1


def test_image_is_stock_except_patches_marker_and_appended_code(stock_image, null_image, null_manifest):
    allowed = set(range(image.MARK_OFF, image.MARK_OFF + 6))
    for p in null_manifest["patches"]:
        a = int(p["addr"], 16) - B
        allowed |= set(range(a, a + len(bytes.fromhex(p["bytes"]))))
    changed = {i for i in range(len(stock_image)) if null_image[i] != stock_image[i]}
    assert changed and changed <= allowed
    assert null_image[image.MARK_OFF:image.MARK_OFF + 6] == b"SLT0\0\0"
    assert null_image[0x4CDDC:0x4CDE0] == b"\xff" * 4            # gap before slim's code at 0x0805CDE0


def test_patch_sites_branch_into_slim(null_image, null_manifest):
    ins = next(MD.disasm(null_image[0x08033320 - B:0x08033324 - B], 0x08033320))
    assert (ins.mnemonic, ins.op_str) == ("b.w", f"#{sym(null_manifest, 'slim_entry_button_press'):#x}")
    for site in (0x08033B46, 0x0803415A):
        ins = next(MD.disasm(null_image[site - B:site - B + 4], site))
        assert (ins.mnemonic, ins.op_str) == ("bl", f"#{sym(null_manifest, 'slim_call_led_task'):#x}")


def test_entry_stub_contains_displaced_instructions_and_return(null_image, null_manifest):
    stub = sym(null_manifest, "slim_entry_button_press") - B
    window = null_image[stub:stub + 64]
    assert bytes.fromhex("38b50446") in window
    assert (0x08033325).to_bytes(4, "little") in window


def test_ram_sits_directly_below_the_heap_limit(null_manifest):
    ram = null_manifest["ram"]
    assert int(ram["end"], 16) == 0x20044E58
    assert int(ram["start"], 16) == (0x20044E58 - ram["used"]) & ~7
    assert int(ram["start"], 16) >= 0x20044D68


def test_outputs_match_manifest(null_build, null_manifest):
    syx = (null_build / "circuittracks-4486-SLT0.syx").read_bytes()
    assert hashlib.sha256(syx).hexdigest() == null_manifest["syx_sha256"]


# PL01-PL22 rebuild from their git tags: tests/test_tags.py. PL22 (1.0 beta 2), the newest published build, is pinned
# against the current sources until a working build follows it.
@pytest.mark.parametrize("marker", ["SL00D", "SL01D", "PL22"])
def test_published_versions_rebuild_identically(marker, request):
    """A builder change must not change what was flashed and tested on the device."""
    published = json.loads((paths.ROOT / "firmware" / marker / "manifest.json").read_text())
    rebuilt = request.getfixturevalue(f"{marker.lower()}_manifest")
    assert (rebuilt["image_sha256"], rebuilt["syx_sha256"]) == (published["image_sha256"], published["syx_sha256"])


def test_image_up_to_the_bootloader_limit_is_accepted_and_one_word_more_refused(stock_image):
    room = image.MAX_IMAGE - (0x0805CDE0 - B)
    assert len(image.assemble(stock_image, 0x0805CDE0, b"\0" * room, [], "SLT0")) == image.MAX_IMAGE
    with pytest.raises(BuildError, match="the bootloader accepts at most 0x70000"):
        image.assemble(stock_image, 0x0805CDE0, b"\0" * (room + 4), [], "SLT0")


def test_cli_reports_build_errors(tmp_path, capsys):
    bad = tmp_path / "bad.toml"
    bad.write_text('marker = "SLBAD"\nfeatures = ["no_such_feature"]\n')
    assert cli.main([str(bad), "-o", str(tmp_path / "out")]) == 1
    assert "playbuild: " in capsys.readouterr().err


def test_non_reproducible_build_is_refused(tmp_path, monkeypatch):
    images = iter([b"first", b"second"])
    monkeypatch.setattr(build, "build_once", lambda *a, **k: (next(images), b"", {"marker": "SLT0"}))
    with pytest.raises(BuildError, match="not reproducible"):
        build.build(NULL_VERSION, tmp_path)


def test_itcm_feature_is_placed_at_the_top_of_the_itcm(itcm_manifest, null_manifest):
    assert itcm_manifest["itcm"] == {"start": "0x3ff8", "end": "0x4000", "used": 8, "size": 0x3C00}
    assert itcm_manifest["symbols"]["probe_itcm"] == "0x3ff8"
    assert itcm_manifest["ram"]["used"] == null_manifest["ram"]["used"]      # not in the heap tail
    assert "itcm" not in null_manifest


def _itcm_copy(tmp_path, feature_edit=None, memory_edit=None, source_edit=None):
    import shutil
    feats = tmp_path / "features"
    shutil.copytree(paths.ROOT / "tests" / "fixtures" / "features" / "itcm_probe", feats / "itcm_probe")
    (tmp_path / "versions").mkdir()
    (tmp_path / "versions" / "itcm.toml").write_text(
        (paths.ROOT / "tests" / "fixtures" / "versions" / "itcm.toml").read_text())
    ft = feats / "itcm_probe" / "feature.toml"
    if feature_edit:
        ft.write_text(feature_edit(ft.read_text()))
    if source_edit:
        src = feats / "itcm_probe" / "itcm_probe.c"
        src.write_text(source_edit(src.read_text()))
    mem = paths.MEMORY
    if memory_edit:
        mem = tmp_path / "memory.toml"
        mem.write_text(memory_edit(paths.MEMORY.read_text()))
    return tmp_path / "versions" / "itcm.toml", mem


@pytest.mark.parametrize("case, match", [
    ("no budget", "ITCM data .* without an ITCM budget"),
    ("budget too small", "ITCM budget exceeded"),
    ("region auto", "usable ram region|region itcm: an ITCM budget needs"),   # auto: the RAM pick refuses first
    ("region static", "region itcm: an ITCM budget needs"),
])
def test_itcm_refusals(tmp_path, case, match):
    itcm_region = 'confidence = "verified"\nauto = false'
    edits = {
        "no budget": dict(feature_edit=lambda t: t.replace("itcm = 8", "itcm = 0")),
        "budget too small": dict(feature_edit=lambda t: t.replace("itcm = 8", "itcm = 4")),
        "region auto": dict(memory_edit=lambda t: t.replace(itcm_region, 'confidence = "verified"\nauto = true')),
        "region static": dict(memory_edit=lambda t: t.replace(itcm_region, 'confidence = "static"\nauto = false')),
    }
    version, mem = _itcm_copy(tmp_path, **edits[case])
    if case.startswith("region"):
        assert mem.read_text() != paths.MEMORY.read_text(), "the region edit must apply"
    with pytest.raises(BuildError, match=match):
        build.build(version, tmp_path / "out", memory_path=mem)


def test_chord_state_is_in_itcm(pl11_manifest):
    """PL09 (user 2026-10-17: move chord's arrays now): held, run, mono_visit in ITCM, the heap tail pool freed; PL11
    adds Euclid's 12 B of RAM, PL13 the melody settings' 16 (the newest build: PL09's own manifest is in firmware/PL09)."""
    itcm = pl11_manifest["itcm"]
    assert itcm["used"] >= 164 and itcm["end"] == "0x4000"
    lo = int(itcm["start"], 16)
    for name in ("held", "run", "mono_visit"):
        assert lo <= int(pl11_manifest["symbols"][name], 16) < 0x4000, name
    assert pl11_manifest["ram"]["used"] <= 104


def test_cli_update_lock_appends_the_versions_new_fields(tmp_path, monkeypatch):
    from helpers import write_feature, write_version
    from playbuild import lock
    d = write_feature(tmp_path / "f", "a")
    (d / "feature.toml").write_text((d / "feature.toml").read_text() + '\n[[saved]]\nsymbol = "a_x"\nbytes = 2\n')
    (d / "a.c").write_text('#include <stdint.h>\nuint8_t a_x[2];\n')
    v = write_version(tmp_path, "v", "SLX1", ["a"], tmp_path / "f")
    monkeypatch.setattr(paths, "SAVE_LOCK", tmp_path / "save_layout.lock")
    monkeypatch.setattr(build, "build", lambda *a, **k: {"marker": "SLX1", "image_size": 0, "syx_sha256": "",
                                                          "flash": {"used": 0}, "ram": {"used": 0, "start": 0}})
    assert cli.main([str(v), "--update-lock"]) == 0
    assert [(e.feature, e.symbol, e.offset, e.size) for e in lock.load(tmp_path / "save_layout.lock").entries] == [
        ("a", "a_x", 0, 2)]


def _saved_version(tmp_path, decl_size, real_size):
    from helpers import write_feature
    d = write_feature(tmp_path / "f", "a")
    (d / "feature.toml").write_text((d / "feature.toml").read_text() + f'\n[[saved]]\nsymbol = "a_x"\nbytes = {decl_size}\n')
    (d / "a.c").write_text(f'#include <stdint.h>\nuint8_t a_x[{real_size}];\n')
    v = tmp_path / "v.toml"
    v.write_text(f'marker = "SLX1"\nfeature_dirs = ["{(tmp_path / "f").resolve()}", "{paths.FEATURES}"]\n'
                 'features = ["a", "saved"]\n')
    return v


def test_build_refuses_a_saved_field_the_lock_does_not_place(tmp_path):
    with pytest.raises(BuildError, match="a_x is not in save_layout.lock"):
        build.build_once(_saved_version(tmp_path, 2, 2), tmp_path / "w", lock_path=tmp_path / "none.lock")


def test_build_refuses_a_saved_field_whose_symbol_has_another_size(tmp_path):
    from playbuild import lock
    v = _saved_version(tmp_path, 2, 3)
    lk = tmp_path / "save_layout.lock"
    lock.update(lk, {"a": features.load_feature(tmp_path / "f" / "a").saved})
    with pytest.raises(BuildError, match="a_x: declared 2 B, the build's symbol has 3 B"):
        build.build_once(v, tmp_path / "w", lock_path=lk)


def test_pl11_manifest_reports_the_saved_layout(pl11_manifest):
    s = pl11_manifest["saved"]
    assert (s["layout_id"], s["payload"], s["block"]) == (1, 118, "record + 0x27024")   # the lock grew in PL20: every build over the current chord sources has 118
    assert (s["format"], s["room"]) == (2, 988) and "block2" not in s     # format 2: one block at the tail + 0
    assert s["fields"][0] == {"symbol": "chord_settings", "offset": 0, "size": 4}
    by = {f["symbol"]: f for f in s["fields"]}
    for symbol, offset, size in (("euclid_cfg", 25, 8), ("page_slot", 33, 4), ("melody_cfg", 37, 8), ("melody_seed", 45, 8),
                                 ("rhythm_cfg", 53, 12), ("melody_vary", 65, 4), ("page_sub", 69, 4),
                                 ("euclid_last", 73, 4), ("chord_voice", 77, 4), ("repeat_cfg", 81, 2),
                                 ("drum_page", 83, 4), ("drum_euclid", 87, 8), ("drum_rhythm", 95, 12),
                                 ("drum_accent", 107, 4), ("drum_seed", 111, 4)):
        assert by[symbol] == {"symbol": symbol, "offset": offset, "size": size}, symbol
    assert "page_last" not in {f["symbol"] for f in s["fields"]}          # retired (a tombstone in the lock)


def test_pl21_manifest_has_its_release(pl21_published_manifest):
    assert pl21_published_manifest["release"] == "1.0 beta 1"
    committed = json.loads((paths.ROOT / "firmware" / "PL21" / "manifest.json").read_text())
    assert pl21_published_manifest["syx_sha256"] == committed["syx_sha256"]


def test_pl22_manifest_has_its_release_and_the_cc27_patch(pl22_manifest):
    assert pl22_manifest["release"] == "1.0 beta 2" and "stockfix" in pl22_manifest["features"]
    assert {"addr": "0x80215b2", "bytes": "efd4"} in pl22_manifest["patches"]


def test_a_patch_only_feature_changes_only_its_bytes(tmp_path, null_image):
    """Beta 2: stockfix (no code) on top of the null test version: the image differs from SLT0's only in the marker and
    the CC 27 patch, and the manifest lists the patch."""
    v = tmp_path / "patched.toml"
    v.write_text(f'marker = "SLT1"\ndescription = "test: null hooks + stockfix"\n'
                 f'feature_dirs = ["{(paths.ROOT / "tests" / "fixtures" / "features").resolve()}", "{paths.FEATURES.resolve()}"]\n'
                 f'features = ["null_hooks", "stockfix"]\n')
    build.build(v, tmp_path / "out")
    img = (tmp_path / "out" / "circuittracks-4486-SLT1.bin").read_bytes()
    man = json.loads((tmp_path / "out" / "manifest.json").read_text())
    changed = {i for i in range(len(img)) if img[i] != null_image[i]}
    assert changed <= set(range(image.MARK_OFF, image.MARK_OFF + 6)) | {0x080215B2 - B}
    assert img[0x080215B2 - B:0x080215B4 - B] == b"\xef\xd4" and null_image[0x080215B2 - B:0x080215B4 - B] == b"\xea\xd4"
    assert {"addr": "0x80215b2", "bytes": "efd4"} in man["patches"]


def test_pytest_collects_only_tests():
    """pytest from the root collects tests/ only, never the records (docs/investigations/**/*.py, spike/)."""
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-m", "not emu and not tags"],
                       cwd=paths.ROOT, capture_output=True, text=True)
    ids = [line for line in r.stdout.splitlines() if "::" in line]
    assert ids and all(line.startswith("tests/") for line in ids)
