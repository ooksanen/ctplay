"""pages/ctplay_link.html (PL12 device test page): the decoding runs in Node on messages the firmware produced in
emulation."""
import json
import re
import shutil
import subprocess

import pytest

from playbuild import paths
from test_link import CHUNK, LINKED, PL12, assemble, chunk_of, drain, fresh, linked, write_msg
from test_saved import DISTINCT, put_settings

PAGE = paths.ROOT / "pages" / "ctplay_link.html"


def decode_js() -> str:
    m = re.search(r"// <decode>[^\n]*\n(.*?)// </decode>", PAGE.read_text(encoding="utf-8"), re.S)
    assert m, "the page must keep its pure decoding between // <decode> and // </decode>"
    return m.group(1)


def node(script: str, data) -> object:
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")
    code = decode_js() + "\nconst input = JSON.parse(require('fs').readFileSync(0, 'utf8'));\n" + script
    out = subprocess.run(["node", "-e", code], input=json.dumps(data), capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_page_never_writes_html():
    src = PAGE.read_text(encoding="utf-8")
    assert "innerHTML" not in src and "outerHTML" not in src and "insertAdjacentHTML" not in src


def test_requests():
    got = node("console.log(JSON.stringify([clHello(), clRead(), clWrite(5, [0x3C, 0x01])]));", None)
    assert got == [[0xF0, 0x7D, 0x53, 0x4C, 0x10, 0xF7], [0xF0, 0x7D, 0x53, 0x4C, 0x11, 0xF7],
                   [0xF0, 0x7D, 0x53, 0x4C, 0x12, 5, 0, 2, 3, 12, 0, 1, 0xF7]]
    assert got[2][5:-1] == write_msg(5, [0x3C, 0x01])
    big = node("console.log(JSON.stringify(clWrite(130, [0xFF])));", None)
    assert big[5:-1] == write_msg(130, [0xFF])


def test_hex_input_is_read_as_bytes():
    got = node("console.log(JSON.stringify(input.map(clHexBytes)));", ["3c 01", "3C,1", "", "zz", "100"])
    assert got == [[0x3C, 1], [0x3C, 1], None, None, None]


def test_other_sysex_is_not_ours():
    got = node("console.log(JSON.stringify(input.map(clParse)));",
               [[0xF0, 0x7E, 0x7F, 0x06, 0x02, 0xF7], [0xF0, 0x7D, 0x53, 0x4C, 0x43, 0xF7], [0x90, 60, 100]])
    assert got == [None, None, None]


@pytest.mark.emu
def test_page_decodes_what_the_firmware_sends(pl21_image, pl21_manifest):
    h = fresh(pl21_image)
    put_settings(h, pl21_manifest, DISTINCT)
    hello = list(h.hello()[0][2])
    h.req(0x11)
    chunks = [list(m[2]) for m in drain(h)]
    assert len(chunks) == 2
    got = node("console.log(JSON.stringify(input.map(clParse)));", [hello] + chunks)
    assert got[0] == {"kind": "hello", "proto": 2, "marker": "PL21", "layout": 1, "len": len(DISTINCT),
                      "fields": [{"offset": o, "size": s, "rev": r} for o, s, r in LINKED]}
    for c, raw in zip(got[1:], chunks):
        off, b = chunk_of((0, 0, bytes(raw)))
        assert c == {"kind": "chunk", "layout": 1, "len": len(DISTINCT), "offset": off, "payload": list(b)}
    assert [c["offset"] for c in got[1:]] == [0, CHUNK]
    # clAssemble: null before the last chunk, the whole payload after it; a chunk twice counts its bytes once
    res = node("const st = {}; console.log(JSON.stringify([clAssemble(st, input[0]), clAssemble(st, input[0]),"
               " clAssemble(st, input[1]), clAssemble(st, input[0])]));", got[1:])
    assert res[0] is None and res[1] is None
    assert bytes(res[2]) == linked(DISTINCT) == assemble([(0, 0, bytes(c)) for c in chunks])
    rows = node("console.log(JSON.stringify(clRows(input[0].fields, input[1])));", [got[0], res[2]])
    assert [r[0] for r in rows] == ["chord settings", "rootless", "strum", "strum falling", "mono", "arp",
                                    "count-in", "euclid", "melody", "rhythm", "melody vary", "chord voice", "repeat", "drum euclid", "drum rhythm", "drum accent", "step chords", "pattern strum"]
    assert rows[-9][2] == " ".join(f"{b:02X}" for b in DISTINCT[53:65])
    assert rows[-7][1:] == ["77", " ".join(f"{b:02X}" for b in DISTINCT[77:81])]
    assert rows[-6][1:] == ["81", " ".join(f"{b:02X}" for b in DISTINCT[81:83])]
    assert rows[0][2] == "91 2B C5 0E"


def test_assemble_restarts_for_a_new_length():
    a = {"kind": "chunk", "layout": 1, "len": 4, "offset": 0, "payload": [1, 2]}
    b = {"kind": "chunk", "layout": 1, "len": 3, "offset": 0, "payload": [9, 8, 7]}
    got = node("const st = {}; console.log(JSON.stringify([clAssemble(st, input[0]), clAssemble(st, input[1])]));",
               [a, b])
    assert got == [None, [9, 8, 7]]


def test_unknown_fields_are_shown_by_offset():
    rows = node("console.log(JSON.stringify(clRows(input, [1, 2, 3])));", [{"offset": 1, "size": 2, "rev": 9}])
    assert rows == [["offset 1 (rev 9)", "1", "02 03"]]
