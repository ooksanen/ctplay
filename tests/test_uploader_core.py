"""playbuild/uploader_core.js (the public uploader page's pure core) under Node."""
import hashlib
import json
import shutil
import subprocess
import sys

import pytest

from playbuild import paths, uploader
from playbuild.patch import make_patch

sys.path.insert(0, str(paths.ROOT / "tools"))
import ct_fw  # noqa: E402

CORE = paths.ROOT / "playbuild" / "uploader_core.js"
STOCK_SYX_FILE = paths.ROOT / "stock" / "circuittracks-firmware-4486-STOCK.syx"

HARNESS = r"""
const core = require(process.env.CORE), fs = require('fs'), crypto = require('crypto');
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const job = JSON.parse(fs.readFileSync(0, 'utf8'));
const rd = p => new Uint8Array(fs.readFileSync(p));
const out = {};
if (job.op === 'decode') out.sha = sha(core.decodeSyx(rd(job.file)));
if (job.op === 'reencode') out.sha = sha(core.encodeSyx(core.decodeSyx(rd(job.file))));
if (job.op === 'patch') {
  const img = core.applyPatch(rd(job.stock), JSON.parse(fs.readFileSync(job.ops, 'utf8')));
  out.image = sha(img); out.syx = sha(core.encodeSyx(img));
}
if (job.op === 'check') {
  out.results = job.files.map(f => {
    const u8 = rd(f.path); let s = null;
    try { s = sha(core.imageOf(f.name, u8)); } catch (e) {}
    const r = core.checkFirmware(f.name, u8, s);
    return { ok: r.ok, message: r.message, hasImage: !!r.image };
  });
}
if (job.op === 'send') out.results = job.cases.map(c => core.canSend(c));
if (job.op === 'identity') out.results = job.cases.map(c => core.parseIdentity(new Uint8Array(c)));
console.log(JSON.stringify(out));
"""


def run(job: dict) -> dict:
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")
    r = subprocess.run(["node", "-e", HARNESS], input=json.dumps(job), capture_output=True, text=True, check=True,
                       env={"CORE": str(CORE), "PATH": __import__("os").environ["PATH"]})
    return json.loads(r.stdout)


@pytest.fixture
def stock_syx() -> bytes:
    if not STOCK_SYX_FILE.exists():
        pytest.skip("stock firmware missing")
    return STOCK_SYX_FILE.read_bytes()


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test_stock_syx_decodes_to_stock():
    if not STOCK_SYX_FILE.exists():
        pytest.skip("stock firmware missing")
    assert run({"op": "decode", "file": str(STOCK_SYX_FILE)})["sha"] == ct_fw.STOCK_4486["image_sha256"]


def test_official_reencodes_to_the_stock_syx():
    if not STOCK_SYX_FILE.exists():
        pytest.skip("stock firmware missing")
    assert run({"op": "reencode", "file": str(STOCK_SYX_FILE)})["sha"] == uploader.STOCK_SYX


def test_pl21_from_the_patch(tmp_path, stock_image, pl21_image, pl21_manifest):
    ops = tmp_path / "ops.json"
    ops.write_text(json.dumps(make_patch(stock_image, pl21_image)))
    stock = tmp_path / "stock.bin"
    stock.write_bytes(stock_image)
    got = run({"op": "patch", "stock": str(stock), "ops": str(ops)})
    assert got["image"] == pl21_manifest["image_sha256"]
    assert got["syx"] == pl21_manifest["syx_sha256"]


def files(tmp_path, items):
    out = []
    for i, (name, data) in enumerate(items):
        p = tmp_path / f"f{i}"
        p.write_bytes(data)
        out.append({"name": name, "path": str(p)})
    return out


def test_bin_and_syx_give_the_same_check(tmp_path, stock_image, stock_syx):
    got = run({"op": "check", "files": files(tmp_path, [("a.syx", stock_syx), ("b.BIN", stock_image)])})["results"]
    assert [r["ok"] for r in got] == [True, True]
    assert all(r["hasImage"] for r in got)


def broken_crc(syx: bytes) -> bytes:
    msgs = syx.split(b"\xf7")
    mid = len(msgs) // 2
    m = bytearray(msgs[mid])
    m[12] ^= 1
    msgs[mid] = bytes(m)
    return b"\xf7".join(msgs)


NOT_STOCK = "This is not the official 1.2.1 (build 4486) firmware."


def test_refusals(tmp_path, stock_image, stock_syx, pl21_image):
    changed = bytearray(stock_image)
    changed[1000] ^= 1
    other = ct_fw.encode(stock_image, proto=0x573)
    cases = [
        ("pl21.syx", ct_fw.encode(pl21_image)),
        ("changed.bin", bytes(changed)),
        ("half.syx", stock_syx[:len(stock_syx) // 2]),
        ("crc.syx", broken_crc(stock_syx)),
        ("other.syx", other),
        ("junk.syx", b"hello"),
    ]
    got = run({"op": "check", "files": files(tmp_path, cases)})["results"]
    assert all(not r["ok"] and not r["hasImage"] for r in got), got
    assert got[0]["message"] == NOT_STOCK
    assert got[1]["message"] == NOT_STOCK
    assert "cut short" in got[2]["message"]
    assert "checksum" in got[3]["message"]
    assert got[4]["message"] == NOT_STOCK + " It is Novation firmware with header version 0x573 (1.2.1 build 4486 has 0x572)."
    assert got[5]["message"]


def test_can_send():
    base = dict(fileOk=True, built=True, port=True, mode="bootloader", runningOverride=False, backup=True, risk=True,
                official=False, busy=False)

    def c(**kw):
        return {**base, **kw}

    table = [
        (c(), True),
        (c(official=True, risk=False), True),          # Official: only the backup box
        (c(official=False, risk=False), False),        # CTPlay: needs the risk box too
        (c(backup=False), False),
        (c(fileOk=False), False),
        (c(built=False), False),
        (c(port=False), False),
        (c(busy=True), False),
        (c(mode=None), False),
        (c(mode="firmware"), False),
        (c(mode="firmware", runningOverride=True), True),
        (c(mode="bootloader", runningOverride=True), True),
    ]
    got = run({"op": "send", "cases": [t[0] for t in table]})["results"]
    assert got == [t[1] for t in table]


# Stock's two identity replies (Universal identity request F0 7E 7F 06 01 F7). The firmware's is a constant in the
# app image (offset 0xEE20 of 1.2.1 build 4486; a device reported exactly these bytes, 2026-11-11); the bootloader's
# is a constant at 0x08003A9C (ST-Link flash dump in ext/circuittracksreverseengineering). The mode is d[8]
# (0x01 firmware, 0x11 bootloader); d[9] = 0x64 is the product (Circuit Tracks) in both.
FIRMWARE_ID = bytes.fromhex("F0 7E 00 06 02 00 20 29 01 64 00 00 01 01 23 06 F7")
BOOTLOADER_ID = bytes.fromhex("F0 7E 00 06 02 00 20 29 11 64 00 00 00 04 1B 64 F7")
FLASH_DUMP = paths.ROOT / "ext" / "circuittracksreverseengineering" / "Firmware-Analysis" / "dumpCT_flash_0x08000000.bin"


def test_identity_replies_are_stocks_own():
    if not paths.STOCK_BIN.exists():
        pytest.skip("stock firmware missing")
    assert paths.STOCK_BIN.read_bytes()[0xEE20:0xEE20 + 17] == FIRMWARE_ID
    if FLASH_DUMP.exists():
        assert FLASH_DUMP.read_bytes()[0x3A9C:0x3A9C + 17] == BOOTLOADER_ID


def test_parse_identity():
    other_product = bytearray(FIRMWARE_ID); other_product[9] = 0x63
    other_maker = bytearray(FIRMWARE_ID); other_maker[7] = 0x2A
    cases = [FIRMWARE_ID, BOOTLOADER_ID, bytes(other_product), bytes(other_maker), FIRMWARE_ID[:16],
             bytes([0xF0, 0x7D, 0x53, 0x4C, 0x50, 0xF7])]
    got = run({"op": "identity", "cases": [list(c) for c in cases]})["results"]
    assert got[0] == {"tracks": True, "mode": "firmware", "build": 4486}
    assert got[1] == {"tracks": True, "mode": "bootloader", "build": 3556}
    assert got[2]["tracks"] is False and got[3]["tracks"] is False
    assert got[4] is None and got[5] is None
