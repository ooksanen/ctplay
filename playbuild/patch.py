"""COPY / ADD patch ops: rebuild a CTPlay image from the user's own stock image, so a public page carries only
CTPlay's bytes, never Novation's.

Ported from CIRCUIT-HACKS-RC's tools/make_rc_uploader.py by Ghillermo (MIT licence).

An op is [0, offset, length] (COPY from the source image) or [1, base64] (ADD: bytes of the new image, standard
base64 so a page can decode them with atob).
"""
from __future__ import annotations

import base64


def make_patch(src: bytes, dst: bytes, min_run: int = 8) -> list[list]:
    """Greedy: at each position of `dst` take the longest COPY of at least `min_run` bytes, else add a byte.
    Candidates: where the last copy ended, the same place, and up to 64 places sharing the next `min_run` bytes."""
    idx: dict[bytes, list[int]] = {}
    for i in range(len(src) - min_run + 1):
        idx.setdefault(src[i:i + min_run], []).append(i)
    ops: list[list] = []
    lit = bytearray()
    i, last = 0, -1

    def flush():
        if lit:
            ops.append([1, base64.b64encode(bytes(lit)).decode()])
            lit.clear()

    while i < len(dst):
        key = dst[i:i + min_run]
        best_len, best_off = 0, -1
        cands = []
        if last >= 0:
            cands.append(last)      # the copy goes on where the previous one ended
        if i < len(src):
            cands.append(i)         # the same place
        cands += idx.get(key, [])[:64]
        for o in cands:
            if o < 0 or o >= len(src) or src[o:o + min_run] != key:
                continue
            n = min_run
            while i + n < len(dst) and o + n < len(src) and src[o + n] == dst[i + n]:
                n += 1
            if n > best_len:
                best_len, best_off = n, o
        if best_len >= min_run:
            flush()
            ops.append([0, best_off, best_len])
            i += best_len
            last = best_off + best_len
        else:
            lit.append(dst[i])
            i += 1
            last = -1
    flush()
    return ops


def apply_patch(src: bytes, ops: list[list]) -> bytes:
    out = bytearray()
    for op in ops:
        out += src[op[1]:op[1] + op[2]] if op[0] == 0 else base64.b64decode(op[1])
    return bytes(out)


def own_bytes(ops: list[list]) -> bytes:
    """Every ADD's bytes, concatenated: what the patch carries of its own."""
    return b"".join(base64.b64decode(op[1]) for op in ops if op[0] == 1)


def stock_runs(data: bytes, src: bytes, n: int = 8) -> list[int]:
    """Offsets in `data` where `n` bytes equal some run of `src`."""
    keys = {src[i:i + n] for i in range(len(src) - n + 1)}
    return [i for i in range(len(data) - n + 1) if data[i:i + n] in keys]
