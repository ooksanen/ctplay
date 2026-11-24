"""The patched image: stock + slim's code after it + patch sites + marker, encoded by upstream's ct_fw."""
from __future__ import annotations

import sys

from .errors import BuildError
from .paths import TOOLS
from .symbols import APP_BASE

sys.path.insert(0, str(TOOLS))
import ct_fw  # noqa: E402

MAX_IMAGE = 0x70000
MARK_OFF = 0x1E8          # 6-byte marker inside the version block (0x1C8, 0x26 B); the bootloader installs only if it changes


def assemble(stock: bytes, flash_origin: int, blob: bytes, patches: list[tuple[int, bytes]], marker: str) -> bytes:
    img = bytearray(stock)
    gap = flash_origin - APP_BASE - len(img)
    if gap < 0:
        raise BuildError(f"flash origin {flash_origin:#010x} overlaps the stock image")
    img += b"\xFF" * gap + blob
    while len(img) % 4:
        img += b"\xFF"
    if len(img) > MAX_IMAGE:
        raise BuildError(f"image is {len(img):#x} B, the bootloader accepts at most {MAX_IMAGE:#x}")
    for addr, data in patches:
        off = addr - APP_BASE
        img[off:off + len(data)] = data
    img[MARK_OFF:MARK_OFF + 6] = marker.encode("ascii").ljust(6, b"\0")
    return bytes(img)


def encode(img: bytes) -> tuple[bytes, dict]:
    syx = ct_fw.encode(img)
    info = ct_fw.decode(syx)
    if info["image"] != img:
        raise BuildError("ct_fw round trip changed the image")
    return syx, info


sha256 = ct_fw.sha256
