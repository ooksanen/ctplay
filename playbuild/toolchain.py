"""The pinned Arm GNU Toolchain: identical compiler binaries everywhere, so identical images."""
from __future__ import annotations

import hashlib
import subprocess
import tarfile
import urllib.request
from pathlib import Path

from .errors import BuildError
from .paths import EXT

RELEASE = "14.2.rel1"
ARCHIVE = f"arm-gnu-toolchain-{RELEASE}-x86_64-arm-none-eabi.tar.xz"
URL = f"https://developer.arm.com/-/media/Files/downloads/gnu/{RELEASE}/binrel/{ARCHIVE}"
SHA256 = "62a63b981fe391a9cbad7ef51b17e49aeaa3e7b0d029b36ca1e9c3b2a9b78823"
DIRNAME = f"arm-gnu-toolchain-{RELEASE}-x86_64-arm-none-eabi"
VERSION_TAG = "14.2.Rel1"


def bindir(ext: Path = EXT) -> Path:
    return ext / DIRNAME / "bin"


def tool(name: str, ext: Path = EXT) -> Path:
    return bindir(ext) / f"arm-none-eabi-{name}"


def require(ext: Path = EXT) -> str:
    """The first line of `gcc --version` of the pinned toolchain; BuildError if it is missing or another version."""
    gcc = tool("gcc", ext)
    if not gcc.exists():
        raise BuildError(f"Arm GNU Toolchain {RELEASE} not found at {gcc.parent}: "
                         f"run `.venv/bin/python setup_toolchain.py`")
    first = subprocess.run([str(gcc), "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    if VERSION_TAG not in first:
        raise BuildError(f"{gcc} is not Arm GNU Toolchain {VERSION_TAG}: {first}")
    return first


def install(ext: Path = EXT) -> Path:
    """Download the archive from Arm, check its SHA-256, extract it into ext/. Returns the bin directory."""
    if tool("gcc", ext).exists():
        return bindir(ext)
    ext.mkdir(parents=True, exist_ok=True)
    part = ext / (ARCHIVE + ".part")
    digest = hashlib.sha256()
    with urllib.request.urlopen(URL) as r, part.open("wb") as f:
        while chunk := r.read(1 << 20):
            digest.update(chunk)
            f.write(chunk)
    if digest.hexdigest() != SHA256:
        part.unlink()
        raise BuildError(f"{ARCHIVE}: SHA-256 {digest.hexdigest()} is not the pinned {SHA256}")
    with tarfile.open(part) as t:
        t.extractall(ext, filter="data")
    part.unlink()
    return bindir(ext)
