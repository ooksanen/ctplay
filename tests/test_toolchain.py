import subprocess

import pytest

from playbuild import compile as cc
from playbuild import toolchain
from playbuild.errors import BuildError


def test_require_reports_missing_toolchain(tmp_path):
    with pytest.raises(BuildError, match="setup_toolchain.py"):
        toolchain.require(ext=tmp_path)


def test_require_rejects_other_versions(tmp_path):
    fake = tmp_path / toolchain.DIRNAME / "bin" / "arm-none-eabi-gcc"
    fake.parent.mkdir(parents=True)
    fake.write_text("#!/bin/sh\necho 'arm-none-eabi-gcc (GNU Arm Embedded Toolchain 10.3) 10.3.1'\n")
    fake.chmod(0o755)
    with pytest.raises(BuildError, match="not Arm GNU Toolchain 14.2.Rel1"):
        toolchain.require(ext=tmp_path)


def test_pinned_toolchain_compiles_thumb2(tmp_path):
    assert toolchain.VERSION_TAG in toolchain.require()
    src = tmp_path / "probe.c"
    src.write_text("unsigned add1(unsigned x) { return x + 1u; }\n")
    obj = tmp_path / "probe.o"
    subprocess.run([str(toolchain.tool("gcc")), "-mcpu=cortex-m7", "-mthumb", "-mfloat-abi=soft", "-Os",
                    "-c", str(src), "-o", str(obj)], check=True)
    dis = subprocess.run([str(toolchain.tool("objdump")), "-d", str(obj)],
                         capture_output=True, text=True, check=True).stdout
    assert "<add1>:" in dis and "bx\tlr" in dis


def test_c_and_assembly_of_one_name_in_one_feature_get_two_objects(tmp_path):
    (tmp_path / "foo.c").write_text("unsigned foo_c(void) { return 1u; }\n")
    (tmp_path / "foo.S").write_text(".syntax unified\n.thumb\n.global foo_s\n.thumb_func\nfoo_s: bx lr\n")
    objs = cc.compile_sources([("feat", tmp_path / "foo.c"), ("feat", tmp_path / "foo.S")], [], tmp_path / "obj")
    assert [o.relative_to(tmp_path / "obj").as_posix() for o in objs] == ["feat/foo.c.o", "feat/foo.S.o"]
    names = [cc.nm(o) for o in objs]
    assert "foo_c" in names[0] and "foo_s" in names[1]
