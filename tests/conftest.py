"""Shared pytest fixtures."""
import json
from pathlib import Path

import pytest

from playbuild import build, paths

FIXTURES = Path(__file__).resolve().parent / "fixtures"
NULL_VERSION = FIXTURES / "versions" / "null.toml"


@pytest.fixture(scope="session")
def stock_image() -> bytes:
    return paths.STOCK_BIN.read_bytes()


@pytest.fixture(scope="session")
def null_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("null")
    build.build(NULL_VERSION, out)
    return out


@pytest.fixture(scope="session")
def null_image(null_build) -> bytes:
    return (null_build / "circuittracks-4486-SLT0.bin").read_bytes()


@pytest.fixture(scope="session")
def null_manifest(null_build) -> dict:
    return json.loads((null_build / "manifest.json").read_text())


ITCM_VERSION = FIXTURES / "versions" / "itcm.toml"


@pytest.fixture(scope="session")
def itcm_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("itcm")
    build.build(ITCM_VERSION, out)
    return out


@pytest.fixture(scope="session")
def itcm_image(itcm_build) -> bytes:
    return (itcm_build / "circuittracks-4486-SLT1.bin").read_bytes()


@pytest.fixture(scope="session")
def itcm_manifest(itcm_build) -> dict:
    return json.loads((itcm_build / "manifest.json").read_text())


SL00D_VERSION = paths.VERSIONS / "SL00D.toml"


@pytest.fixture(scope="session")
def sl00d_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("sl00d")
    build.build(SL00D_VERSION, out)
    return out


@pytest.fixture(scope="session")
def sl00d_image(sl00d_build) -> bytes:
    return (sl00d_build / "circuittracks-4486-SL00D.bin").read_bytes()


@pytest.fixture(scope="session")
def sl00d_manifest(sl00d_build) -> dict:
    return json.loads((sl00d_build / "manifest.json").read_text())


SL01D_VERSION = paths.VERSIONS / "SL01D.toml"


@pytest.fixture(scope="session")
def sl01d_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("sl01d")
    build.build(SL01D_VERSION, out)
    return out


@pytest.fixture(scope="session")
def sl01d_image(sl01d_build) -> bytes:
    return (sl01d_build / "circuittracks-4486-SL01D.bin").read_bytes()


@pytest.fixture(scope="session")
def sl01d_manifest(sl01d_build) -> dict:
    return json.loads((sl01d_build / "manifest.json").read_text())


PL05_VERSION = paths.VERSIONS / "PL05.toml"


@pytest.fixture(scope="session")
def pl05_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("pl05")
    build.build(PL05_VERSION, out)
    return out


@pytest.fixture(scope="session")
def pl05_image(pl05_build) -> bytes:
    return (pl05_build / "circuittracks-4486-PL05.bin").read_bytes()


@pytest.fixture(scope="session")
def pl05_manifest(pl05_build) -> dict:
    return json.loads((pl05_build / "manifest.json").read_text())


PL04D_VERSION = paths.VERSIONS / "PL04D.toml"


@pytest.fixture(scope="session")
def pl04d_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("pl04d")
    build.build(PL04D_VERSION, out)
    return out


@pytest.fixture(scope="session")
def pl04d_image(pl04d_build) -> bytes:
    return (pl04d_build / "circuittracks-4486-PL04D.bin").read_bytes()


@pytest.fixture(scope="session")
def pl04d_manifest(pl04d_build) -> dict:
    return json.loads((pl04d_build / "manifest.json").read_text())


PL09_VERSION = paths.VERSIONS / "PL09.toml"


@pytest.fixture(scope="session")
def pl09_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("pl09")
    build.build(PL09_VERSION, out)
    return out


@pytest.fixture(scope="session")
def pl09_image(pl09_build) -> bytes:
    return (pl09_build / "circuittracks-4486-PL09.bin").read_bytes()


@pytest.fixture(scope="session")
def pl09_manifest(pl09_build) -> dict:
    return json.loads((pl09_build / "manifest.json").read_text())


VLOG_VERSION = FIXTURES / "versions" / "voice_log.toml"


@pytest.fixture(scope="session")
def vlog_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("vlog")
    build.build(VLOG_VERSION, out)
    return out


@pytest.fixture(scope="session")
def vlog_image(vlog_build) -> bytes:
    return (vlog_build / "circuittracks-4486-SLT1.bin").read_bytes()


@pytest.fixture(scope="session")
def vlog_manifest(vlog_build) -> dict:
    return json.loads((vlog_build / "manifest.json").read_text())


PL13_VERSION = paths.VERSIONS / "PL13.toml"
PL14_VERSION = paths.VERSIONS / "PL14.toml"
PL15_VERSION = paths.VERSIONS / "PL15.toml"
PL16_VERSION = paths.VERSIONS / "PL16.toml"
PL17_VERSION = paths.VERSIONS / "PL17.toml"
PL18_VERSION = paths.VERSIONS / "PL18.toml"
PL19_VERSION = paths.VERSIONS / "PL19.toml"
PL20_VERSION = paths.VERSIONS / "PL20.toml"
PL21_VERSION = paths.VERSIONS / "PL21.toml"
PL22_VERSION = paths.VERSIONS / "PL22.toml"
PL11_VERSION = paths.VERSIONS / "PL11.toml"


@pytest.fixture(scope="session")
def pl11_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("pl11")
    build.build(PL11_VERSION, out)
    return out


@pytest.fixture(scope="session")
def pl11_image(pl11_build) -> bytes:
    return (pl11_build / "circuittracks-4486-PL11.bin").read_bytes()


@pytest.fixture(scope="session")
def pl11_manifest(pl11_build) -> dict:
    return json.loads((pl11_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl13_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("pl13")
    build.build(PL13_VERSION, out)
    return out


@pytest.fixture(scope="session")
def pl13_image(pl13_build) -> bytes:
    return (pl13_build / "circuittracks-4486-PL13.bin").read_bytes()


@pytest.fixture(scope="session")
def pl13_manifest(pl13_build) -> dict:
    return json.loads((pl13_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl14_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("pl14")
    build.build(PL14_VERSION, out)
    return out


@pytest.fixture(scope="session")
def pl14_image(pl14_build) -> bytes:
    return (pl14_build / "circuittracks-4486-PL14.bin").read_bytes()


@pytest.fixture(scope="session")
def pl14_manifest(pl14_build) -> dict:
    return json.loads((pl14_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl15_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("pl15")
    build.build(PL15_VERSION, out)
    return out


@pytest.fixture(scope="session")
def pl15_image(pl15_build) -> bytes:
    return (pl15_build / "circuittracks-4486-PL15.bin").read_bytes()


@pytest.fixture(scope="session")
def pl15_manifest(pl15_build) -> dict:
    return json.loads((pl15_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl16_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("pl16")
    build.build(PL16_VERSION, out)
    return out


@pytest.fixture(scope="session")
def pl16_image(pl16_build) -> bytes:
    return (pl16_build / "circuittracks-4486-PL16.bin").read_bytes()


@pytest.fixture(scope="session")
def pl16_manifest(pl16_build) -> dict:
    return json.loads((pl16_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl17_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("pl17")
    build.build(PL17_VERSION, out)
    return out


@pytest.fixture(scope="session")
def pl17_image(pl17_build) -> bytes:
    return (pl17_build / "circuittracks-4486-PL17.bin").read_bytes()


@pytest.fixture(scope="session")
def pl17_manifest(pl17_build) -> dict:
    return json.loads((pl17_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl18_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("pl18")
    build.build(PL18_VERSION, out)
    return out


@pytest.fixture(scope="session")
def pl18_image(pl18_build) -> bytes:
    return (pl18_build / "circuittracks-4486-PL18.bin").read_bytes()


@pytest.fixture(scope="session")
def pl18_manifest(pl18_build) -> dict:
    return json.loads((pl18_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl19_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("pl19")
    build.build(PL19_VERSION, out)
    return out


@pytest.fixture(scope="session")
def pl19_image(pl19_build) -> bytes:
    return (pl19_build / "circuittracks-4486-PL19.bin").read_bytes()


@pytest.fixture(scope="session")
def pl19_manifest(pl19_build) -> dict:
    return json.loads((pl19_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl20_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("pl20")
    build.build(PL20_VERSION, out)
    return out


@pytest.fixture(scope="session")
def pl20_image(pl20_build) -> bytes:
    return (pl20_build / "circuittracks-4486-PL20.bin").read_bytes()


@pytest.fixture(scope="session")
def pl20_manifest(pl20_build) -> dict:
    return json.loads((pl20_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl21_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("pl21")
    build.build(PL21_VERSION, out)
    return out


@pytest.fixture(scope="session")
def pl21_image(pl21_build) -> bytes:
    return (pl21_build / "circuittracks-4486-PL21.bin").read_bytes()


@pytest.fixture(scope="session")
def pl21_manifest(pl21_build) -> dict:
    return json.loads((pl21_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl22_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("pl22")
    build.build(PL22_VERSION, out)
    return out


@pytest.fixture(scope="session")
def pl22_image(pl22_build) -> bytes:
    return (pl22_build / "circuittracks-4486-PL22.bin").read_bytes()


@pytest.fixture(scope="session")
def pl22_manifest(pl22_build) -> dict:
    return json.loads((pl22_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl18_published_build(tmp_path_factory):
    """The published PL18, built from git tag PL18 (versions/PL18.toml builds the current sources under its marker)."""
    import subprocess
    from helpers import build_tag
    try:
        tags = subprocess.run(["git", "tag", "-l", "PL18"], cwd=paths.ROOT, capture_output=True, text=True,
                              check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        tags = []
    if "PL18" not in tags:
        pytest.skip("no git tag PL18 (not a git checkout with tags)")
    return build_tag("PL18", tmp_path_factory.mktemp("pl18_published"))


@pytest.fixture(scope="session")
def pl18_published_image(pl18_published_build) -> bytes:
    return (pl18_published_build / "circuittracks-4486-PL18.bin").read_bytes()


@pytest.fixture(scope="session")
def pl18_published_manifest(pl18_published_build) -> dict:
    return json.loads((pl18_published_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl19_published_build(tmp_path_factory):
    """The published PL19, built from git tag PL19 (versions/PL19.toml builds the current sources under its marker)."""
    import subprocess
    from helpers import build_tag
    try:
        tags = subprocess.run(["git", "tag", "-l", "PL19"], cwd=paths.ROOT, capture_output=True, text=True,
                              check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        tags = []
    if "PL19" not in tags:
        pytest.skip("no git tag PL19 (not a git checkout with tags)")
    return build_tag("PL19", tmp_path_factory.mktemp("pl19_published"))


@pytest.fixture(scope="session")
def pl19_published_image(pl19_published_build) -> bytes:
    return (pl19_published_build / "circuittracks-4486-PL19.bin").read_bytes()


@pytest.fixture(scope="session")
def pl19_published_manifest(pl19_published_build) -> dict:
    return json.loads((pl19_published_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl20_published_build(tmp_path_factory):
    """The published PL20, built from git tag PL20 (versions/PL20.toml builds the current sources under its marker)."""
    import subprocess
    from helpers import build_tag
    try:
        tags = subprocess.run(["git", "tag", "-l", "PL20"], cwd=paths.ROOT, capture_output=True, text=True,
                              check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        tags = []
    if "PL20" not in tags:
        pytest.skip("no git tag PL20 (not a git checkout with tags)")
    return build_tag("PL20", tmp_path_factory.mktemp("pl20_published"))


@pytest.fixture(scope="session")
def pl20_published_image(pl20_published_build) -> bytes:
    return (pl20_published_build / "circuittracks-4486-PL20.bin").read_bytes()


@pytest.fixture(scope="session")
def pl20_published_manifest(pl20_published_build) -> dict:
    return json.loads((pl20_published_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl21_published_build(tmp_path_factory):
    """The published PL21 (CTPlay 1.0 beta 1), built from git tag PL21 (versions/PL21.toml builds the current sources
    under its marker: since PL22's roll_step change, not the published image)."""
    import subprocess
    from helpers import build_tag
    try:
        tags = subprocess.run(["git", "tag", "-l", "PL21"], cwd=paths.ROOT, capture_output=True, text=True,
                              check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        tags = []
    if "PL21" not in tags:
        pytest.skip("no git tag PL21 (not a git checkout with tags)")
    return build_tag("PL21", tmp_path_factory.mktemp("pl21_published"))


@pytest.fixture(scope="session")
def pl21_published_image(pl21_published_build) -> bytes:
    return (pl21_published_build / "circuittracks-4486-PL21.bin").read_bytes()


@pytest.fixture(scope="session")
def pl21_published_manifest(pl21_published_build) -> dict:
    return json.loads((pl21_published_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl13_published_build(tmp_path_factory):
    """The published PL13, built from git tag PL13 (versions/PL13.toml builds the current sources under its marker)."""
    import subprocess
    from helpers import build_tag
    try:
        tags = subprocess.run(["git", "tag", "-l", "PL13"], cwd=paths.ROOT, capture_output=True, text=True,
                              check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        tags = []
    if "PL13" not in tags:
        pytest.skip("no git tag PL13 (not a git checkout with tags)")
    return build_tag("PL13", tmp_path_factory.mktemp("pl13_published"))


@pytest.fixture(scope="session")
def pl13_published_image(pl13_published_build) -> bytes:
    return (pl13_published_build / "circuittracks-4486-PL13.bin").read_bytes()


@pytest.fixture(scope="session")
def pl13_published_manifest(pl13_published_build) -> dict:
    return json.loads((pl13_published_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl14_published_build(tmp_path_factory):
    """The published PL14, built from git tag PL14 (versions/PL14.toml builds the current sources under its marker)."""
    import subprocess
    from helpers import build_tag
    try:
        tags = subprocess.run(["git", "tag", "-l", "PL14"], cwd=paths.ROOT, capture_output=True, text=True,
                              check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        tags = []
    if "PL14" not in tags:
        pytest.skip("no git tag PL14 (not a git checkout with tags)")
    return build_tag("PL14", tmp_path_factory.mktemp("pl14_published"))


@pytest.fixture(scope="session")
def pl14_published_image(pl14_published_build) -> bytes:
    return (pl14_published_build / "circuittracks-4486-PL14.bin").read_bytes()


@pytest.fixture(scope="session")
def pl14_published_manifest(pl14_published_build) -> dict:
    return json.loads((pl14_published_build / "manifest.json").read_text())


@pytest.fixture(scope="session")
def pl15_published_build(tmp_path_factory):
    """The published PL15, built from git tag PL15 (versions/PL15.toml builds the current sources under its marker)."""
    import subprocess
    from helpers import build_tag
    try:
        tags = subprocess.run(["git", "tag", "-l", "PL15"], cwd=paths.ROOT, capture_output=True, text=True,
                              check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        tags = []
    if "PL15" not in tags:
        pytest.skip("no git tag PL15 (not a git checkout with tags)")
    return build_tag("PL15", tmp_path_factory.mktemp("pl15_published"))


@pytest.fixture(scope="session")
def pl15_published_image(pl15_published_build) -> bytes:
    return (pl15_published_build / "circuittracks-4486-PL15.bin").read_bytes()


@pytest.fixture(scope="session")
def pl15_published_manifest(pl15_published_build) -> dict:
    return json.loads((pl15_published_build / "manifest.json").read_text())
