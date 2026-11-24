"""Novation Components' project validator (its wasm, run under Node through tests/validator.mjs) as a test helper.

`validate(*records)` -> one `(ok, errors)` per record. A record is the session as the save leaves it in RAM (0x2740C
bytes). The validator checks stock's fields only; it never looks at CTPlay's tail (spike 2026-11-11). Skips when Node
or the wasm (`ext/`, from tools/setup_dev.py) is missing."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WASM_DIR = ROOT / "ext" / "circuittracksreverseengineering" / "Assets" / "Novation-Components"


def validate(*records: bytes) -> list[tuple[bool, list[str]]]:
    if shutil.which("node") is None:
        pytest.skip("node is not on PATH")
    if not list(WASM_DIR.glob("circuit-tracks-project-validator-*.wasm")):
        pytest.skip("Components' validator wasm is missing (run tools/setup_dev.py)")
    with tempfile.TemporaryDirectory() as tmp:
        files = []
        for i, rec in enumerate(records):
            f = Path(tmp) / f"{i}.rec"
            f.write_bytes(rec)
            files.append(str(f))
        out = subprocess.run(["node", str(ROOT / "tests" / "validator.mjs"), *files], capture_output=True, text=True,
                             check=True, timeout=120).stdout
    lines = [json.loads(l) for l in out.splitlines() if l.strip()]
    assert [l["file"] for l in lines] == files
    return [(l["ok"], l["errors"]) for l in lines]
