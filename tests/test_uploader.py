import json

from playbuild import paths, uploader


def test_uploader_accepts_stock_and_published_slim_builds_only(tmp_path):
    out = uploader.write(tmp_path / "ct_uploader.html")
    html = out.read_text()
    sl00d = json.loads((paths.ROOT / "firmware" / "SL00D" / "manifest.json").read_text())["syx_sha256"]
    assert uploader.STOCK_SYX in html and sl00d in html
    assert "0f663591bd2d8093546ce834a8b2b6df4db34e2c3eb628dab9aa850ef966a8e8" not in html   # upstream SC02
    assert html.count("const KNOWN = {") == 1
    assert '<html lang="en">' in html and "Allow MIDI access" in html and "Permitir" not in html


def test_uploader_asks_the_link_which_build_is_installed(tmp_path):
    html = uploader.write(tmp_path / "ct_uploader.html").read_text()
    pl17 = json.loads((paths.ROOT / "firmware" / "PL17" / "manifest.json").read_text())["syx_sha256"]
    assert "out.send([0xF0, 0x7D, 0x53, 0x4C, 0x10, 0xF7])" in html
    assert f'"{pl17}": "PL17"' in html
    assert "ctplayHello(isTracks && d[8] === 1," in html and "idDone(`${isTracks" not in html
    # the mode is d[8] (0x01 firmware, 0x11 bootloader); d[9] is the product, 0x64 (tests/test_uploader_core.py)
    assert 'const mode = d[8] === 1 ? "firmware" : d[8] === 17 ? "bootloader" : "mode " + d[8];' in html
    assert "d[9] === 1" not in html and "d[9] === 17" not in html
    assert "fileSha = fileOk ? h : null; ctplayCheck();" in html
    assert html.index("const SLIM_MARKER") < html.index('$("file").onchange')


def test_public_name():
    assert uploader.public_name({"marker": "PL21", "release": "1.0 beta 1"}) == "CTPlay 1.0 beta 1 (PL21)"
    assert uploader.public_name({"marker": "PL21"}) == "CTPlay PL21"
