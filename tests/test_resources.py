"""docs/resources.md: its table matches the newest published PL build's manifest and the saved block's room."""
import json
import re

from playbuild import paths

DOC = paths.ROOT / "docs" / "resources.md"


def newest_published_pl() -> str:
    markers = [p.name for p in (paths.ROOT / "firmware").iterdir() if re.fullmatch(r"PL\d+", p.name)]
    return max(markers, key=lambda m: int(m[2:]))


def b(n: int) -> str:
    return f"{n:,} B"


def row(name: str, where: str, size: int, used: int) -> str:
    return f"| {name} | {where} | {b(size)} | {b(used)} | {b(size - used)} |"


def test_resources_page_matches_the_newest_manifest():
    doc = DOC.read_text()
    marker = re.search(r"<!-- resources: (\w+) -->", doc).group(1)
    assert marker == newest_published_pl()
    assert f"| Used by {marker} |" in doc
    man = json.loads((paths.ROOT / "firmware" / marker / "manifest.json").read_text())
    saved = man["saved"]
    payload = saved["payload"]
    if saved.get("format") == 2:
        saved_rows = [row("Saved", "session record tail + 0", saved["room"], payload)]
    else:                                         # PL20's two alpha blocks: 56 B at tail + 768, 160 B at tail + 832
        saved_rows = [row("Saved: block 1", "session record tail + 768", 56, min(payload, 56)),
                      row("Saved: block 2", "session record tail + 832", 160, max(payload - 56, 0))]
    flash, ram, itcm = man["flash"], man["ram"], man["itcm"]
    expected = [
        row("Flash", f"`0x{int(flash['start'], 16):08X}–0x{int(flash['start'], 16) + flash['size']:08X}`",
            flash["size"], flash["used"]),
        row("RAM: heap tail", f"`0x{int(ram['end'], 16) - ram['size']:08X}–0x{int(ram['end'], 16):08X}`",
            ram["size"], ram["used"]),
        row("RAM: ITCM", f"`0x{0x4000 - itcm['size']:08X}–0x00004000`", itcm["size"], itcm["used"]),
    ] + saved_rows
    for line in expected:
        assert line in doc, line
