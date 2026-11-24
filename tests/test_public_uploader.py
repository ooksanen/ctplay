"""The public uploader page (bring your own firmware): uploader.write_public, playbuild/public_uploader.html."""
import base64
import json
import re

import pytest

from playbuild import paths, uploader
from playbuild.errors import BuildError
from playbuild.image import ct_fw
from playbuild.patch import stock_runs

BACKUP_BOX = "I have backed up my projects and my SD card."
RISK_BOX = ("I understand that CTPlay is unofficial firmware and I install it at my own risk. If something goes wrong, my "
            "Circuit Tracks may need the recovery steps below, and Novation does not support CTPlay.")
NO_MIDI = "This browser has no Web MIDI with SysEx. Use desktop Chrome or Edge."
UNKNOWN_BUILD = ("The page doesn't know which build is installed. If it is already this version, the Circuit Tracks keeps it "
                 "unchanged. To check, Identify the device while it runs normally.")
RECEIVED = ("The Circuit Tracks received the file and restarts. It installs the file only if it is a different version from "
            "the one installed. When it runs normally again, press Allow MIDI and Identify the device to check.")
NO_CTPLAY_AFTER_OFFICIAL = "No CTPlay answered: the official firmware or another firmware is running."
PORT_BUSY = "Close Components, any DAW and other MIDI pages, then press Allow MIDI again."
NOVATION_LINK = "https://components.novationmusic.com/api/v2/firmwares/168/file"
# The coarse net's allow-list: the page's words (its text, the core's messages and comments) that also occur in the
# stock image, as 8 or more bytes with a space beside them. A stock run in the HTML must lie inside one of these, a
# character on either side included, or inside a run of 8 or more spaces (the scripts' indentation).
ALLOWED_WORDS = ["Circuit Tracks", "Circuit Rhythm", "Novation", "Focusrite Audio", "Could not", "not valid", "expected", "message",
                 "progress", "changed", "failed", "loading", "transfer", "Starting", "Received"]


@pytest.fixture(scope="module")
def stock() -> bytes:
    if not paths.STOCK_BIN.exists():
        pytest.skip("stock firmware image missing")
    return paths.STOCK_BIN.read_bytes()


@pytest.fixture(scope="module")
def pages(tmp_path_factory, stock, pl21_published_build, pl22_build):
    out = tmp_path_factory.mktemp("public") / "uploader"
    files = uploader.write_public(out, bins={"PL21": pl21_published_build / "circuittracks-4486-PL21.bin",
                                             "PL22": pl22_build / "circuittracks-4486-PL22.bin"})
    return out, files


def releases_of(html: str) -> list[dict]:
    m = re.search(r"const RELEASES = (\[.*?\]);\n", html)
    assert m, "the page must hold `const RELEASES = [...];` on one line"
    return json.loads(m.group(1))


def test_public_page_lists_the_releases(pages, pl21_published_manifest, pl22_manifest):
    """The newest two releases, newest first: PL22 (1.0 beta 2) and PL21 (1.0 beta 1), both published."""
    out, files = pages
    assert sorted(files) == sorted([out / "index.html", out / "PL21" / "index.html", out / "PL22" / "index.html"])
    want = {"PL22": (pl22_manifest, "1.0 beta 2"), "PL21": (pl21_published_manifest, "1.0 beta 1")}
    for f in files:
        html = f.read_text(encoding="utf-8")
        rel = releases_of(html)
        markers = ["PL22", "PL21"] if f == out / "index.html" else [f.parent.name]   # a release's own page: just it
        assert [r["marker"] for r in rel] == markers
        assert [r["name"] for r in rel] == [f"CTPlay {want[m][1]} ({m})" for m in markers]
        for r in rel:
            man, release = want[r["marker"]]
            assert r["image_sha256"] == man["image_sha256"] and r["syx_sha256"] == man["syx_sha256"]
            assert r["marker"] == man["marker"] and r["release"] == release
            assert r["description"] == man["description"]
        assert "Official 1.2.1" in html
        assert ct_fw.STOCK_4486["image_sha256"] in html and uploader.STOCK_SYX in html
        assert "__CORE__" not in html and "__RELEASES__" not in html and "__STOCK__" not in html
    assert [m["marker"] for m in uploader.releases()] == ["PL22", "PL21"]

def test_public_page_holds_no_stock_bytes(pages, stock):
    out, files = pages
    for f in files:
        html = f.read_text(encoding="utf-8")
        # the strict net: every ADD's bytes, no 8-byte run of stock
        for rel in releases_of(html):
            own = b"".join(base64.b64decode(op[1]) for op in rel["ops"] if op[0] == 1)
            assert stock_runs(own, stock) == [], rel["marker"]
        # the coarse net: no 8-byte window of the whole page equals stock, but inside a visible allow-listed word
        data = html.encode("utf-8")
        spans = [(m.start() - 1, m.end() + 1) for w in ALLOWED_WORDS for m in re.finditer(re.escape(w.encode()), data)]
        spans += [(m.start(), m.end()) for m in re.finditer(rb" {8,}", data)]
        bad = [i for i in stock_runs(data, stock) if not any(s <= i and i + 8 <= e for s, e in spans)]
        assert bad == [], [data[i - 8:i + 16] for i in bad[:10]]


def test_public_page_texts(pages):
    _, files = pages
    for f in files:
        html = f.read_text(encoding="utf-8")
        assert '<html lang="en">' in html
        assert BACKUP_BOX in html and RISK_BOX in html
        assert "I know what I&#39;m doing: send to the running firmware." in html or \
            "I know what I'm doing: send to the running firmware." in html
        assert "Scales + Preset + Note" in html
        assert NOVATION_LINK in html
        assert "Chrome or Edge" in html and NO_MIDI in html and "navigator.requestMIDIAccess" in html
        assert "CTPlay is not affiliated with Novation." in html
        assert "Circuit Tracks, Components and Novation are trademarks of Focusrite Audio Engineering Ltd." in html
        assert "based on CIRCUIT-HACKS-RC&#39;s uploader by Ghillermo" in html or \
            "based on CIRCUIT-HACKS-RC's uploader by Ghillermo" in html
        assert "Copyright (c) 2026 Ghillermo" in html
        assert "Permitir" not in html and "index.json" not in html and "fetch(" not in html
        assert "<script src" not in html and "<link " not in html          # one self-contained file
        assert "canSend(" in html and "checkFirmware(" in html
        # the installed build: Identify while it runs normally first; never claim an install the page can't see
        assert "switch it on as usual" in html and "Press Identify\n      the device again." in html
        assert UNKNOWN_BUILD in html and RECEIVED in html and NO_CTPLAY_AFTER_OFFICIAL in html
        assert "Installed: ${s.name}." in html and "the firmware was not changed." in html
        assert "restarts and installs the firmware" not in html
        # a port that can't be opened says why; Abort goes grey once every block is sent
        assert PORT_BUSY in html and "openFailed(e)" in html and "Could not open the port: " in html
        assert '$("btnAbort").disabled = true; say("phase", "Everything sent.' in html
        # Identify's mode comes from the core's parseIdentity (d[8]; tested on stock's real replies), not d[9]
        assert "id = parseIdentity(d)" in html and "mode = id.mode;" in html
        assert "d[9] === 17" not in html and "d[9] === 1 " not in html
        # device run 2026-11-21: the running firmware asks for Play without status 1, so the hint shows from the start
        # of such a send; each status says how much was sent; unknown messages are logged
        assert '"Starting… Press Play on the Circuit Tracks when it asks."' in html
        assert "(after ${xfer.next} of ${packets.length} messages)" in html
        assert 'log("← device (not known to the page): " + hx(d))' in html


def test_stale_build_is_refused(tmp_path, stock, pl21_image, pl22_build):
    bad = bytearray(pl21_image)
    bad[0x50000] ^= 1
    bin_ = tmp_path / "stale.bin"
    bin_.write_bytes(bytes(bad))
    out = tmp_path / "site" / "uploader"
    with pytest.raises(BuildError, match="PL21"):
        uploader.write_public(out, bins={"PL21": bin_, "PL22": pl22_build / "circuittracks-4486-PL22.bin"})
    assert not out.exists()


def test_missing_build_is_refused(tmp_path, stock, pl22_build):
    out = tmp_path / "uploader"
    with pytest.raises(BuildError, match="PL21"):
        uploader.write_public(out, bins={"PL21": tmp_path / "nothing.bin",
                                       "PL22": pl22_build / "circuittracks-4486-PL22.bin"})
    assert not out.exists()


def test_write_site_builds_the_whole_site(tmp_path, stock, pl21_published_build, pl22_build):
    from playbuild import guide
    bins = {"PL21": pl21_published_build / "circuittracks-4486-PL21.bin",
            "PL22": pl22_build / "circuittracks-4486-PL22.bin"}
    guide.write_site(tmp_path, bins=bins)
    files = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    assert files == ["public/index.html", "public/recipes/index.html", "public/uploader/PL21/index.html",
                     "public/uploader/PL22/index.html", "public/uploader/index.html"]


def test_public_pages_are_what_write_public_writes(pages, pl21_published_build, pl22_build):
    out, files = pages
    got = uploader.public_pages(bins={"PL21": pl21_published_build / "circuittracks-4486-PL21.bin",
                                      "PL22": pl22_build / "circuittracks-4486-PL22.bin"})
    assert {p.relative_to(out).as_posix(): p.read_text(encoding="utf-8") for p in files} == got
