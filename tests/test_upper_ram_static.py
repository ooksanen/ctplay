"""SL01D static gate: no stock literal points into the RAM that the probe fills."""
import struct

BASE = 0x08010000
FILL_LO, FILL_HI = 0x20044E58, 0x2004F000     # the filled part [LO, HI)
TOP = 0x20050000                              # end of RAM; hits in [HI, TOP] are only reported


def movw_movt_values(img):
    """Yield (offset, value) for every MOVW + MOVT pair on the same register, MOVT within 16 bytes of its MOVW."""
    movw = {}                                  # rd -> (offset, imm16)
    for off in range(0, len(img) - 3, 2):
        hw1, hw2 = struct.unpack_from("<HH", img, off)
        kind = hw1 & 0xFBF0
        if kind not in (0xF240, 0xF2C0):
            continue
        rd = (hw2 >> 8) & 0xF
        imm = (((hw1 & 0xF) << 12) | (((hw1 >> 10) & 1) << 11)
               | (((hw2 >> 12) & 7) << 8) | (hw2 & 0xFF))
        if kind == 0xF240:
            movw[rd] = (off, imm)
        elif rd in movw and off - movw[rd][0] <= 16:
            yield movw[rd][0], (imm << 16) | movw[rd][1]


def literal_targets(img):
    """Map image offset of every word read by a PC-relative load (LDR literal T1 / LDR.W literal T2) -> loading offsets."""
    targets = {}
    for off in range(0, len(img) - 3, 2):
        hw1, hw2 = struct.unpack_from("<HH", img, off)
        base = ((BASE + off + 4) & ~3) - BASE
        if (hw1 & 0xF800) == 0x4800:
            t = base + (hw1 & 0xFF) * 4
        elif hw1 in (0xF8DF, 0xF85F):
            t = base + (hw2 & 0xFFF) * (1 if hw1 == 0xF8DF else -1)
        else:
            continue
        if 0 <= t <= len(img) - 4:
            targets.setdefault(t, []).append(off)
    return targets


def test_no_stock_constant_in_the_filled_part(stock_image):
    # Adjacent Thumb instructions (e.g. `movs r0,#4` = 0x2004) make false aligned-word hits in code, so only words
    # that a PC-relative load actually reads count as literals.
    lits = literal_targets(stock_image)
    hits, unread, upper = [], [], []
    for off in range(0, len(stock_image) - 3, 4):
        (v,) = struct.unpack_from("<I", stock_image, off)
        if FILL_LO <= v < FILL_HI:
            (hits if off in lits else unread).append((off, v))
        elif FILL_HI <= v <= TOP:
            upper.append((off, v))
    pairs = [(o, v) for o, v in movw_movt_values(stock_image) if FILL_LO <= v < FILL_HI]
    print("filled-range words no PC-relative load reads:",
          [f"0x{v:08X}@0x{o:X}" for o, v in unread])
    for label, sel in (("literal-referenced", True), ("not read by a PC-relative load", False)):
        print(f"[0x2004F000, 0x20050000] {label}:",
              [f"0x{v:08X}@0x{o:X}" for o, v in upper if (o in lits) == sel])
    assert not pairs, [(hex(o), hex(v)) for o, v in pairs]
    assert not hits, [(hex(o), hex(v), [hex(BASE + a) for a in lits[o]]) for o, v in hits]


def test_decoders_find_the_known_literal(stock_image):
    # Stock's memory report reads 0x2004FE00 from image offset 0xD70C: proves the literal decoder works.
    assert 0xD70C in literal_targets(stock_image)
