"""build/ct_uploader.html: upstream's Web MIDI uploader in English (fork/ct_uploader.en.html, the fork's translation
of tools/ct_uploader.html; read only), accepting the official firmware and the slim builds published in
firmware/*/manifest.json.

"Identify the device" also sends the CTPlay link's hello (stock's identity reply is the same constant on every build):
the reply's marker names the installed build, and a chosen file with that marker gets a warning (the bootloader drops
an image whose version block, where slim changes only the marker, equals the installed one).

    .venv/bin/python -m playbuild.uploader      (from the repo root)

`--public` writes the public page instead (bring your own firmware): build/site/public/uploader/index.html for the
newest releases and uploader/<MARKER>/index.html for each, from playbuild/public_uploader.html. The person picks their
own official firmware file; the page rebuilds the release from it with COPY / ADD ops (playbuild/patch.py), checks every
hash and sends it. The page holds CTPlay's bytes, offsets and hashes, never Novation's. The site build
(`python -m playbuild.guide`) includes these pages (public_pages) and checks their links with the rest of the site;
`--public` alone writes just them.

    .venv/bin/python -m playbuild.uploader --public
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from .errors import BuildError
from .image import ct_fw
from .patch import apply_patch, make_patch, own_bytes, stock_runs
from .paths import BUILD, ROOT, STOCK_BIN

TEMPLATE = ROOT / "fork" / "ct_uploader.en.html"
PUBLIC_TEMPLATE = ROOT / "playbuild" / "public_uploader.html"
CORE_JS = ROOT / "playbuild" / "uploader_core.js"
STOCK_SYX = "bd2d294bafa88fdec7ae1f5fcaaa13158323969c5a40f83405a72e4ad329a0bd"

# After stock's identity reply: the link's hello (F0 7D 53 4C 10 F7 -> 50, proto, 6-byte marker, ...; PL12 on).
CTPLAY_JS = """// ---------- slim: which CTPlay build is installed
const SLIM_MARKER = %s;
let installed = null, fileSha = null;     // installed: the hello's marker, "" = no reply, null = not asked since a restart
const ctplayNote = document.createElement("div"); ctplayNote.style.marginTop = "8px"; $("fileInfo").after(ctplayNote);
function ctplayCheck() {
  const m = fileSha && SLIM_MARKER[fileSha], same = !!m && m === installed;
  ctplayNote.className = same ? "warn" : "";
  ctplayNote.textContent = same ? `${m} is already installed. The device would take this file and then keep ${m} without installing it again (same version).` : "";
}
function ctplayHello(ask, msg, cls) {
  const p = idPending;
  if (!ask || !p) { installed = null; idDone(msg, cls); ctplayCheck(); return; }
  const done = (m, text) => { installed = m; idDone(`${msg} · ${text}`, cls); ctplayCheck(); };
  clearTimeout(p.t); p.inp.removeEventListener("midimessage", p.h);
  p.h = ev => { const d = ev.data;
    if (d.length >= 16 && d[d.length - 1] === 0xF7 && d[0] === 0xF0 && d[1] === 0x7D && d[2] === 0x53 && d[3] === 0x4C && d[4] === 0x50) {
      const m = String.fromCharCode(...d.slice(6, 12)).trim();
      log("CTPlay hello: " + hex(d)); done(m, `CTPlay ${m}`);
    } };
  p.t = setTimeout(() => done("", "no CTPlay reply (stock, upstream, or CTPlay before PL12)"), 1000);
  p.inp.addEventListener("midimessage", p.h);
  p.out.send([0xF0, 0x7D, 0x53, 0x4C, 0x10, 0xF7]);
}
$("file").addEventListener("change", () => { fileSha = null; ctplayCheck(); });

"""

# (template text, replacement): each must occur exactly once.
EDITS = [
    # stock's identity reply: d[8] is the mode (0x01 firmware, 0x11 bootloader), d[9] the product (0x64); the template
    # (from upstream) read the mode from d[9], so it never saw firmware mode and never asked the link's hello
    ('      const mode = d[9] === 1 ? "firmware" : d[9] === 17 ? "bootloader" : "mode " + d[9];',
     '      const mode = d[8] === 1 ? "firmware" : d[8] === 17 ? "bootloader" : "mode " + d[8];'),
    ('      idDone(`${isTracks ? "Novation" : "?"} · pid ${hex(d.slice(8, 10))} · ${mode} · build ${build}`, isTracks ? "ok" : "warn");',
     '      ctplayHello(isTracks && d[8] === 1, `${isTracks ? "Novation" : "?"} · pid ${hex(d.slice(8, 10))} · ${mode} · build ${build}`, isTracks ? "ok" : "warn");'),
    ('  $("fileInfo").innerHTML = html; updateSend();\n};',
     '  $("fileInfo").innerHTML = html; fileSha = fileOk ? h : null; ctplayCheck(); updateSend();\n};'),
    ("function dropMidi(msg) {\n", "function dropMidi(msg) {\n  installed = null; ctplayCheck();\n"),
    ("// ---------- file\n", None),
]


def published() -> list[dict]:
    return [json.loads(m.read_text()) for m in sorted((ROOT / "firmware").glob("*/manifest.json"))]


def public_name(manifest: dict) -> str:
    """The name a person sees for a build: "CTPlay 1.0 beta 1 (PL21)", or "CTPlay PL21" without a release."""
    if manifest.get("release"):
        return f"CTPlay {manifest['release']} ({manifest['marker']})"
    return f"CTPlay {manifest['marker']}"


def known() -> dict[str, str]:
    k = {STOCK_SYX: "STOCK Circuit Tracks 1.2.1 (build 4486), official Novation firmware"}
    for man in published():
        k[man["syx_sha256"]] = f"slim {man['marker']}: {man['description']}"
    return k


def write(out: Path = BUILD / "ct_uploader.html") -> Path:
    html = TEMPLATE.read_text(encoding="utf-8")
    body = ",\n".join(f'  "{h}": {json.dumps(label)}' for h, label in known().items())
    new, n = re.subn(r"const KNOWN = \{.*?\n\};", lambda _: "const KNOWN = {\n" + body + "\n};", html, count=1, flags=re.S)
    if n != 1:
        raise BuildError(f"{TEMPLATE}: the `const KNOWN = {{` block was not found")
    markers = json.dumps({man["syx_sha256"]: man["marker"] for man in published()}, indent=1)
    for old, rep in EDITS:
        if new.count(old) != 1:
            raise BuildError(f"{TEMPLATE}: expected exactly one {old.strip()[:60]!r}")
        new = new.replace(old, rep if rep is not None else CTPLAY_JS % markers + old)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(new, encoding="utf-8")
    return out


def _release_number(manifest: dict) -> int:
    m = re.fullmatch(r"PL(\d+)", manifest["marker"])
    if not m:
        raise BuildError(f"{manifest['marker']}: a public release must be a PL build")
    return int(m.group(1))


def releases() -> list[dict]:
    """The manifests the public page lists: the newest two with a `release`, newest first (by the number after PL)."""
    return sorted((m for m in published() if m.get("release")), key=_release_number, reverse=True)[:2]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _release_entry(man: dict, stock: bytes, bin_path: Path) -> dict:
    """One release for the page, checked against its committed manifest: BuildError on any mismatch."""
    marker = man["marker"]
    if not Path(bin_path).is_file():
        raise BuildError(f"{marker}: {bin_path} not found (build it: python -m playbuild versions/{marker}.toml)")
    image = Path(bin_path).read_bytes()
    if _sha(image) != man["image_sha256"]:
        raise BuildError(f"{marker}: {bin_path} is not the published image (SHA-256 differs from "
                         f"firmware/{marker}/manifest.json): rebuild it from the tag")
    if _sha(ct_fw.encode(image)) != man["syx_sha256"]:
        raise BuildError(f"{marker}: the encoded .syx differs from firmware/{marker}/manifest.json")
    ops = make_patch(stock, image)
    if apply_patch(stock, ops) != image:
        raise BuildError(f"{marker}: the patch does not rebuild the image")
    if stock_runs(own_bytes(ops), stock):
        raise BuildError(f"{marker}: the patch's own bytes hold an 8-byte run of the stock image")
    return {"marker": marker, "release": man["release"], "name": public_name(man), "description": man["description"],
            "size": len(image), "image_sha256": man["image_sha256"], "syx_sha256": man["syx_sha256"], "ops": ops}


def _public_page(template: str, core: str, entries: list[dict], guide: str) -> str:
    stock = {"image_sha256": ct_fw.STOCK_4486["image_sha256"], "syx_sha256": STOCK_SYX}
    # inside <script>: "<" written as \u003c can't end it, and the JSON reads the same
    rel = json.dumps(entries, separators=(",", ":"), ensure_ascii=True).replace("<", "\\u003c")
    page = template
    for key, value in (("__CORE__", core), ("__RELEASES__", rel), ("__STOCK__", json.dumps(stock)),
                       ("__GUIDE__", guide)):
        if page.count(key) != 1:
            raise BuildError(f"{PUBLIC_TEMPLATE}: expected exactly one {key}")
        page = page.replace(key, value)
    return page


def public_pages(bins: dict[str, Path] | None = None) -> dict[str, str]:
    """The public pages, {file under uploader/: html}: "index.html" (the newest releases) and "<MARKER>/index.html"
    (that release alone). Every check runs first: BuildError on any mismatch."""
    if not STOCK_BIN.exists():
        raise BuildError(f"{STOCK_BIN} not found (python tools/setup_dev.py)")
    stock = STOCK_BIN.read_bytes()
    if _sha(stock) != ct_fw.STOCK_4486["image_sha256"]:
        raise BuildError(f"{STOCK_BIN} is not the official 1.2.1 (build 4486) image")
    if ct_fw.STOCK_4486["syx_sha256"] != STOCK_SYX:
        raise BuildError("tools/ct_fw.py and uploader.STOCK_SYX disagree on the stock .syx")
    core = CORE_JS.read_text(encoding="utf-8")
    if f'"{ct_fw.STOCK_4486["image_sha256"]}"' not in core:
        raise BuildError(f"{CORE_JS}: its STOCK_IMAGE_SHA256 is not tools/ct_fw.py's")
    mans = releases()
    if not mans:
        raise BuildError("no published manifest has a `release`")
    bins = bins or {}
    entries = [_release_entry(m, stock, bins.get(m["marker"], BUILD / m["marker"] / f"circuittracks-4486-{m['marker']}.bin"))
               for m in mans]
    template = PUBLIC_TEMPLATE.read_text(encoding="utf-8")
    pages = {"index.html": _public_page(template, core, entries, "../")}
    for e in entries:
        pages[f"{e['marker']}/index.html"] = _public_page(template, core, [e], "../../")
    return pages


def write_public(out_dir: Path = BUILD / "site" / "public" / "uploader", bins: dict[str, Path] | None = None) -> list[Path]:
    """The public pages written to out_dir (public_pages). Everything is checked before any file is written."""
    pages = public_pages(bins)
    out_dir = Path(out_dir)
    written = []
    for rel, html in pages.items():
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        written.append(path)
    return written


if __name__ == "__main__":
    if sys.argv[1:] == ["--public"]:
        for p in write_public():
            print(p)
    elif sys.argv[1:]:
        sys.exit("usage: python -m playbuild.uploader [--public]")
    else:
        print(write())
