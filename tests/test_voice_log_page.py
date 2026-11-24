"""pages/voice_log.html: the decoding runs in Node on replies the firmware produced in emulation."""
import json
import re
import shutil
import subprocess

import pytest

from playbuild import paths
from test_voice_log import records
from test_voice_log_sysex import played
from voices import THRESHOLD

PAGE = paths.ROOT / "pages" / "voice_log.html"


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


def test_request_is_padded():
    req = node("console.log(JSON.stringify(vlRequest(2, 9, [0, 8])));", None)
    assert len(req) == 232 and req[:8] == [0xF0, 0x7D, 0x53, 0x4C, 2, 9, 0, 8] and req[-1] == 0xF7


@pytest.mark.emu
def test_page_decodes_what_the_firmware_sends(vlog_image, vlog_manifest):
    h = played(vlog_image, 3)
    h.down(29, 100)                                   # held
    h.set_headroom(THRESHOLD - 0x10)
    h.set_dsp_voice(h.state(5))                       # the DSP takes the held voice of pad 29
    h.down(30, 100)
    want = records(h, vlog_manifest)
    reply = list(h.req(2, (0, len(want)))[2])
    got = node("const r = vlReply(input); const recs = vlRecords(r.data);"
               "console.log(JSON.stringify({status: r.status, recs, rows: vlRows(recs), text: vlText(vlRows(recs))}));",
               reply)
    assert got["status"] == 0
    assert [(r["t"], r["seq"], r["synth"], r["dsp"], r["note"], r["voice"], r["headroom"]) for r in got["recs"]] == \
           [(w["t"], w["seq"], w["synth"], w["dsp"], w["note"], w["voice"], w["headroom"]) for w in want]
    took = ["free", "sounding", "starting", "?"]
    assert [r["took"] for r in got["recs"]] == [took[(w["before"] >> (2 * w["voice"])) & 3] for w in want]
    assert got["recs"][-1]["took"] == "starting" and got["rows"][-1][6] == "DSP" and got["rows"][-1][8] == "starting"
    lines = got["text"].split("\n")
    assert lines[0].split("\t")[:3] == ["ms", "seq", "synth"] and len(lines) == 1 + len(want)


def test_synth_2_stolen_is_relative_to_its_first_voice():
    # one record: synth 2 (flags 1 | DSP 2), voice 8 = the synth's third voice, held before
    rec = [0, 0, 0, 3, 60, 8] + [2 << 4, 0] + [0x00, 0x10]
    got = node("console.log(JSON.stringify(vlRecords(input)));", [1] + rec)
    assert got[0]["synth"] == 1 and got[0]["took"] == "starting" and got[0]["before"][2] == 2


def test_empty_read():
    got = node("console.log(JSON.stringify(vlRows(vlRecords(input))));", [0])
    assert got == []


def test_port_choice_prefers_the_main_circuit_tracks_port():
    """As the uploader's score(): the device shows more ports; MIDI 2 / 3, DIN and DAW ones are not the SysEx port."""
    got = node("console.log(JSON.stringify(input.map(vlPickPort)));",
               [["Circuit Tracks MIDI 2", "Circuit Tracks", "Other synth"],
                ["MIDIOUT2 (Circuit Tracks)", "Circuit Tracks"],
                ["Circuit Tracks DIN"],
                ["Other synth"]])
    assert got == [1, 1, 0, -1]


def test_floor_is_shown_when_the_arm_picked_below_the_threshold():
    rec = [0, 0, 0, 0, 74, 4, 0x55, 0x00, 0x10, 0x12]     # ARM, reading 0x1210 (< 0x1400), voices 0-3 sounding
    rows = node("console.log(JSON.stringify(vlRows(vlRecords(input))));", [1] + rec)
    assert rows[0][6] == "ARM (floor)" and rows[0][9] == "rrrr--"
