"""Saved settings (PL10, spec 2026-10-17-saved-settings-design.md): CTPlay's settings travel in a block in the session
record's tail; stock's save writes it (hook session_save), the end of stock's load marks it pending (session_applied)
and the next LED frame copies it back, or the defaults. Format 2 (spec 2026-11-10-saved-format-2-design.md, "The
block"): one block at tail + 0 ("CTPL", format 2, layout ID, n, CRC-16, pending, 0, payload); a save keeps a newer
build's bytes past this build's payload and zeroes the alpha blocks' magics. The alpha blocks (PL10-PL20: block 1 at
tail + 768, "CTPS", CRC-8; PL14: block 2 at tail + 832, "CTP2", CRC-16 over both) are still read when no format-2
block is valid.

The file is not emulated (FatFs / SD): a test models it as a snapshot of the record taken after the save, written back
before stock's read-done handler 0x0802FD5C. One scenario per fresh harness."""
import pytest

from notes import NoteHarness

pytestmark = pytest.mark.emu
SESSION, REC_PTR = 0x2003D71C, 0x14
RECORD_SIZE, BLOCK = 0x2740C, 0x27024 + 768     # BLOCK: the alpha block 1 (tail + 768)
BLOCK2, SPLIT = 0x27024 + 832, 56                # PL14: block 2, and block 1's payload bytes (older builds take <= 56)
TAIL, HDR2, ROOM = 0x27024, 12, 988              # format 2: the block at tail + 0, its header, the payload's room
SAVE = 25                                         # Save: pressed twice stores the project (0x0802FDF8)
PAYLOAD = [("chord_settings", 4), ("chord_rootless", 1), ("chord_strum", 1), ("chord_strum_down", 1),
           ("chord_mono", 1), ("chord_arp", 8), (None, 4), ("page_quick", 4), ("ci_on", 1), ("euclid_cfg", 8),
           ("page_slot", 4), ("melody_cfg", 8), ("melody_seed", 8),                      # None: page_last, retired in PL11 (pages numbered by their pad): written 0
           ("rhythm_cfg", 12), ("melody_vary", 4), ("page_sub", 4), ("euclid_last", 4),  # PL14
           ("chord_voice", 4),                                                              # PL15
           ("repeat_cfg", 2), ("drum_page", 4),                                           # PL16
           ("drum_euclid", 8), ("drum_rhythm", 12), ("drum_accent", 4), ("drum_seed", 4),
           ("chord_step", 1),                                                              # PL18
           ("chord_pstrum", 1),                                                           # PL19
           ("trig_mark", 1)]                                                              # PL20
LEN = sum(n for _, n in PAYLOAD)                  # 118 from PL20 (PL19: 117, PL18: 116, PL17: 115, PL16: 87) (PL15: 81) (PL14: 77) (PL13: 53, PL12: 37, PL10: 25)
PL13_LEN = 53
PL14_LEN = 77
PL15_LEN = 81


def sym(m, name):
    return int(m["symbols"][name], 16)


def record(h):
    return h.r32(SESSION + REC_PTR)


def tail(h):
    """The record's tail (1000 B)."""
    return bytes(h.uc.mem_read(record(h) + TAIL, 1000))


def snapshot(h):
    return bytes(h.uc.mem_read(record(h), RECORD_SIZE))


def other(payload):
    """Other values everywhere: only the blocks or the defaults set them."""
    return bytes(b ^ 0x01 for b in payload)


def crc16(data):
    """CRC-16/CCITT-FALSE: polynomial 0x1021, init 0xFFFF."""
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = (crc << 1 ^ 0x1021) & 0xFFFF if crc & 0x8000 else crc << 1 & 0xFFFF
    return crc


def crc8(data):
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc << 1 ^ 0x07) & 0xFF if crc & 0x80 else crc << 1 & 0xFF
    return crc


def get(h, m, name, n):
    return bytes(h.uc.mem_read(sym(m, name), n))


def put(h, m, name, data):
    h.uc.mem_write(sym(m, name), bytes(data))


def settings(h, m, fields=PAYLOAD):
    """The payload a save writes from the globals (retired bytes 0)."""
    return b"".join(get(h, m, name, n) if name else bytes(n) for name, n in fields)


def save(h):
    h.press(SAVE)
    h.press(SAVE)


# Every field set, every value in range: shapes / inversions / spreads / bass, rootless, strums, falling, mono; per track
# an arpeggio (pattern, rate, triplet, latch, octaves, gate); pages; the count-in on.
DISTINCT = bytes([0x91, 0x2B, 0xC5, 0x0E,  0x05,  0x6C,  0x0A,  0x03,      # rootless 0x05: tracks 0 and 2, both with bass
                  0x81, 0x01, 0x13, 0x0C, 0x26, 0x10, 0x07, 0x04,
                  0x00, 0x00, 0x00, 0x00,  0x00, 0x01, 0x00, 0x01,  0x01,        # retired page_last: 0
                  0x05, 0x4F, 0x2A, 0xA3, 0x50, 0x01, 0x30, 0x1F,                # Euclid: hits | velocity, rotation | gate
                  0x01, 0x07, 0x02, 0x07,                                        # page_slot: Arp, Keys, Pattern tools, Keys
                  0x59, 0x1B, 0xA5, 0x08, 0xCF, 0x1F, 0x02, 0x10,                # melody_cfg (PL13): order | pool | range | accent, root | octave
                  0x05, 0xC3, 0x7E, 0x01, 0xFF, 0x02, 0x80, 0x9A,                # melody_seed: rhythm, notes, never 0
                  0xA5, 0x23, 0x01,  0x30, 0x5F, 0x02,  0x63, 0x67, 0x04,  0x88, 0x0A, 0x03,   # rhythm_cfg (PL14): hits | combine, rotation | thinning, cycle
                  0x01, 0x06, 0x0F, 0x0C,                                        # melody_vary: ties | jumps
                  0x01, 0x02, 0x03, 0x01,                                        # page_sub: tools 2, phrasing, both
                  0x3C, 0x40, 0x43, 0x30,                                        # euclid_last: played pitches
                  0x01, 0x12, 0x25, 0x30,                                        # chord_voice (PL15): row-2 shape | voice leading
                  0xF6, 0x00,                                                    # repeat_cfg (PL16): rate 6, accent, latch, unquantized
                  0x0A, 0x02, 0x09, 0x0A,                                        # drum_page (PL16): slot 1 Repeat (beta), 2 Pattern tools (PL17) | bit 3 (Pattern tools 2)
                  0x43, 0x25, 0x0A, 0x42, 0x30, 0x07, 0x4F, 0x21,                # drum_euclid (PL17): hits | velocity, rotation | roll
                  0xA5, 0x23, 0x01,  0x63, 0x5F, 0x02,  0x30, 0x45, 0x03,  0x4A, 0x0A, 0x04,   # drum_rhythm: as rhythm_cfg
                  0x01, 0x02, 0x03, 0x01,                                        # drum_accent
                  0x5A, 0xC3, 0x7E, 0xFF,                                        # drum_seed: never 0
                  0x05,                                                          # chord_step (PL18): tracks 0 and 2
                  0x24,                                                          # chord_pstrum (PL19): tracks 1 and 2 played, written
                  0x01])                                                         # trig_mark (PL20): marked
assert len(DISTINCT) == LEN


def test_block_layout_after_a_save(pl21_image, pl21_manifest):
    h = NoteHarness(pl21_image)
    h.leds()                                      # the first frame applies what the record holds (init set pending)
    put_settings(h, pl21_manifest, DISTINCT)
    save(h)
    t = tail(h)
    n = int.from_bytes(t[6:8], "little")
    assert (t[:4], t[4], t[5], n, t[10], t[11]) == (b"CTPL", 2, 1, LEN, 0, 0)
    assert t[8:10] == crc16(t[4:8] + t[HDR2:HDR2 + n]).to_bytes(2, "big")
    assert t[HDR2:HDR2 + n] == settings(h, pl21_manifest) == DISTINCT
    assert t[HDR2 + n:] == bytes(1000 - HDR2 - n)


# ---- Behaviour through stock's routes (Task 3) ----

READ_DONE = 0x0802FD5C                            # stock's read-done handler: header check, fix-up or new project, apply
CLEAR = 23
DOWN, UP, FLIP = 19, 20, 21                       # Octave ▼ / ▲ (next / previous page), 1-16/17-32 (Shift: Quick view)
DEFAULTS = (bytes(8) + bytes([0x00, 0x08] * 4) + bytes(9) + bytes([0x20, 0x40] * 4) + bytes(4)
            + bytes([0x00, 0x10] * 4) + bytes([1] * 8)    # + PL13: melody_cfg, melody_seed
            + bytes(12 + 4 + 4) + bytes([72] * 4)        # + PL14: rhythm_cfg, melody_vary, page_sub, euclid_last
            + bytes(4)                                    # + PL15: chord_voice
            + bytes(2 + 4)                                # + PL16: repeat_cfg, drum_page
            + bytes([0x20, 0x00] * 4) + bytes(12 + 4) + bytes([1] * 4)   # + PL17: drum_euclid, drum_rhythm, drum_accent, drum_seed
            + bytes(1)                                    # + PL18: chord_step
            + bytes(1)                                    # + PL19: chord_pstrum
            + bytes(1))                                   # + PL20: trig_mark
assert len(DEFAULTS) == LEN
CI_COLS = [0x53, 0x17, 0x32, 0x4D]                # Clear with Shift: off, click, count-in, both


def make_block(payload, layout=1, n=None, check=None):
    n = len(payload) if n is None else n
    head = bytes([layout, n])
    crc = crc8(head + payload[:n]) if check is None else check
    return b"CTPS" + head + bytes([crc, 0]) + payload


def make_block2(block1, payload2, layout=1, n=None, check=None, magic=b"CTP2"):
    """Block 2 (PL14) for block 1 `block1` (its first 64 B as written): the check covers block 1's ID, n and check, its
    56 payload bytes, then block 2's ID, n2 and payload (not block 1's pending byte)."""
    n = len(payload2) if n is None else n
    head = bytes([layout, n])
    block1 = bytes(block1[:8 + SPLIT]).ljust(8 + SPLIT, b"\0")
    crc = crc16(block1[4:7] + block1[8:] + head + payload2[:n]) if check is None else check
    return magic + head + crc.to_bytes(2, "big") + payload2


def make_blocks(payload):
    """What a PL14 save writes from `payload`, from tail + 768: block 1 (n = 56), then block 2 (tail + 832)."""
    b1 = make_block(payload[:SPLIT])
    return b1 + make_block2(b1, payload[SPLIT:])


def make_tail(payload, n=None, fmt=2, layout=1, magic=b"CTPL", crc=None):
    """A tail (1000 B) holding a format-2 block of `payload` (n defaults to its length), then zeros."""
    n = len(payload) if n is None else n
    head = bytes([fmt, layout]) + n.to_bytes(2, "little")
    crc = crc16(head + payload[:n]) if crc is None else crc
    return (magic + head + crc.to_bytes(2, "big") + bytes(2) + payload).ljust(1000, b"\0")


def write_tail(h, data, at=TAIL):
    """`data` into the record's tail at offset `at`: TAIL (the format-2 block's place, default) or BLOCK (the alpha
    blocks at tail + 768)."""
    h.uc.mem_write(record(h) + at, bytes(data))


def load(h):
    """Stock's load from the file's read-done handler down to the apply's end (the record already holds the file)."""
    h.call(READ_DONE, SESSION, maxins=20_000_000)


def put_settings(h, m, data, fields=PAYLOAD):
    off = 0
    for name, n in fields:
        if name:
            put(h, m, name, data[off:off + n])
        off += n


def pick(h, pad):
    h.down(pad)
    h.up(pad)


def set_count_in(h, want):
    for _ in range(4):
        h.shift(True)
        col = h.leds()[55]
        h.shift(False)
        if CI_COLS.index(col) == want:
            return
        h.press(CLEAR, shift=True)
    raise AssertionError("Shift + Clear never reached the state")


# Bytes no pad moves from their default: repeat_cfg[1] is always 0.
UNMOVED = {("repeat_cfg", 1), ("trig_mark", 0)}      # trig_mark: no route sets it until the first condition is written (PL20, Task 6)


def set_everything(h):
    """Every saved setting away from its default, through the real routes: a Note-view pad, the Shift Quick view, every
    page (Chords, Arp, Pattern tools 1 / 2, Melody, Phrasing, Keys; PL16: a drum's Repeat page; PL17: every drum's
    Pattern tools 1 / 2), the table of contents, the Quick view flip, Shift + Clear."""
    for t in range(4):
        h.track(t)
        pick(h, 26 + t % 2)                       # a Note-view pad: euclid_last (before the Arp latches anything)
        h.shift(True)
        pick(h, 16 + 1 + t)                       # shape: the Quick view (PL15)
        h.shift(False)
        h.press(t, shift=True)                    # the Chords page
        for pad in (16 + (t + 1) % 4, 20 + t % 3, 23, 23):   # inversion, spread, bass twice
            pick(h, pad)
        if t % 2:
            pick(h, 8 + t // 2)                   # a row-2 shape (ends the row-1 shape)
        pick(h, 24 + t % 3)                       # voice leading (after the inversion: an inversion press ends it)
        pick(h, 27 + t % 3)                       # strum speed
        pick(h, 31)                               # falling
        h.press(DOWN)                             # Arp
        pick(h, 1 + t)                            # pattern
        pick(h, 8 + t)                            # rate
        pick(h, 15)                               # latch
        pick(h, 17)                               # octaves 2
        pick(h, 20)                               # gate one sixth down
        h.press(DOWN)                             # Pattern tools
        pick(h, t)                                # hits t + 1
        pick(h, 17)                               # rotate ▶
        pick(h, 20)                               # gate one sixth down
        pick(h, 21 + (t + 2) % 3)                 # velocity
        pick(h, 24 + t)                           # cycle 3 / 5 / 6 / 7 (PL14)
        h.press(DOWN)                             # Pattern tools 2 (PL14): page_sub bit 0
        for pad in (1 + t, 16, 19 + t, 24 + t % 3):   # second hits, rotate ◀, combine, thinning
            pick(h, pad)
        h.press(DOWN)                             # Melody
        for pad in (1 + t, 9, 11, 13, 17 + t, 25, 28, 29):   # order, pool scale, range 2, accent, degree, octave, dice x 2
            pick(h, pad)
        h.press(DOWN)                             # Phrasing (PL14): page_sub bit 1
        pick(h, t % 3)                            # ties
        pick(h, 4 + (t + 1) % 3)                  # octave jumps
        if t % 2:
            h.press(DOWN)                         # Keys, the last page
            pick(h, 0)                            # mono (PL18: a toggle on pad 1)
            if t == 1:
                pick(h, 1)                        # step-entry chords (PL18)
            pick(h, 2 if t == 1 else 3)           # pattern strum (PL19): played on track 1, written on track 3
            h.press(DOWN)                         # no page after it: stays
        else:
            if t:
                h.press(UP)                       # Melody: page_sub bit 1 cleared
            h.shift(True)
            pick(h, 24 + 1)                       # the table of contents: Arp (page_sub kept)
            h.shift(False)
        h.press(t)                                # close: page_slot = Arp or Keys
        h.press(FLIP, shift=True)                 # the quick view: Arp
    h.press(5, shift=True)                        # PL16: Drum 2's Repeat page
    for pad in (2, 10, 14, 15):                   # rate 1/16, swell, unquantized, latch
        pick(h, pad)
    h.press(5)                                    # close
    for d in range(4):                            # PL17: each drum's Pattern tools
        h.press(4 + d, shift=True)                # Repeat (drum_page 0)
        h.press(DOWN)                             # Pattern tools
        for pad in (d, 20, 21 + (d + 2) % 3, 24 + d):   # hits d + 1, roll 2 hits, velocity, cycle
            pick(h, pad)
        if d % 2:
            pick(h, 19)                           # groove
        pick(h, 28)                               # dice rhythm: drum_seed
        h.press(DOWN)                             # Pattern tools 2: drum_page bit 3
        for pad in (1 + d, 16, 19 + d, 24 + d % 3):   # second hits, rotate ◀, combine, thinning
            pick(h, pad)
        for _ in range(1 + d % 3):
            pick(h, 27)                           # accent
        if d == 1:
            h.press(UP)                           # Pattern tools: bit 3 cleared (0x02)
        elif d == 2:
            h.shift(True)
            pick(h, 25)                           # the table of contents: Repeat (pad 26), bit 3 kept (0x09)
            h.shift(False)
        h.press(4 + d)                            # close (0x0A: drums 1 and 4)
    set_count_in(h, 3)


def test_a_pl12_block_gives_melody_defaults(pl21_image, pl21_manifest):
    """A valid layout-1 block with n = 37 (PL12's): its fields are loaded, the two PL13 fields take their defaults."""
    m = pl21_manifest
    h = NoteHarness(pl21_image)
    h.leds()
    put_settings(h, m, bytes(b ^ 0x01 for b in DISTINCT))   # other values everywhere: only the block or the defaults set them
    write_tail(h, make_block(DISTINCT[:37]), at=BLOCK)
    load(h)
    h.leds()
    assert settings(h, m) == DISTINCT[:37] + DEFAULTS[37:]
    assert get(h, m, "melody_cfg", 8) == bytes([0x00, 0x10] * 4)
    assert get(h, m, "melody_seed", 8) == bytes([1] * 8)


def test_melody_settings_round_trip(pl21_image, pl21_manifest):
    """Picks and dice, Save, change, load: all back. Bad values are fixed per field, the others kept."""
    m = pl21_manifest
    h = NoteHarness(pl21_image)
    h.leds()
    h.track(2)
    h.press(2, shift=True)                        # the Chords page
    for _ in range(4):
        h.press(DOWN)                             # Arp, Pattern tools, Pattern tools 2 (PL14), Melody
    for pad in (6, 9, 12, 13, 13, 19, 26, 29, 28):
        pick(h, pad)
    want = (get(h, m, "melody_cfg", 8), get(h, m, "melody_seed", 8))
    assert want[0][4:6] != bytes([0, 0x10]) and want[1][4:6] != b"\x01\x01"
    save(h)
    file = bytes(h.uc.mem_read(record(h), RECORD_SIZE))
    put_settings(h, m, DISTINCT)
    h.uc.mem_write(record(h), file)
    load(h)
    h.leds()
    assert (get(h, m, "melody_cfg", 8), get(h, m, "melody_seed", 8)) == want
    bad = bytearray(DISTINCT)                     # each bad value alone: the neighbours stay
    bad[37] |= 0x30; bad[40] |= 0x40 | 0x20; bad[46] = 0
    write_tail(h, make_tail(bytes(bad)))
    load(h)
    h.leds()
    got = settings(h, m)
    assert got[37] == DISTINCT[37] & ~0x30 and got[40] == DISTINCT[40] and got[39] == DISTINCT[39] and got[41] == DISTINCT[41]
    assert got[46] == 1 and got[45] == DISTINCT[45]


def test_round_trip_through_the_real_routes(pl21_image, pl21_manifest):
    h = NoteHarness(pl21_image)
    h.leds()
    set_everything(h)
    want = settings(h, pl21_manifest)
    assert want[83:87] == bytes([0x0A, 0x02, 0x09, 0x0A])   # drum_page: Pattern tools 2, Pattern tools, Repeat | bit 3 (PL17)
    off = 0
    for name, n in PAYLOAD:                       # every field moved away from its default
        for k in range(n):
            assert not name or (name, k) in UNMOVED or want[off + k] != DEFAULTS[off + k], (name, k)
        off += n
    save(h)
    file = bytes(h.uc.mem_read(record(h), RECORD_SIZE))
    put_settings(h, pl21_manifest, DISTINCT)      # change every setting
    h.uc.mem_write(record(h), file)               # the file read back into the record
    load(h)
    assert tail(h)[10] == 0xA5 and settings(h, pl21_manifest) == DISTINCT   # pending until the next frame
    h.leds()
    assert tail(h)[10] == 0 and settings(h, pl21_manifest) == want


def test_power_on_load_before_the_first_hook_call_applies_at_the_first_frame(pl21_image, pl21_manifest):
    h = NoteHarness(pl21_image)
    write_tail(h, make_tail(DISTINCT))            # what the power-on load left in the record, pending 0
    h.leds()                                      # first hook call: init marks pending, the frame applies it
    assert settings(h, pl21_manifest) == DISTINCT and tail(h)[10] == 0


OUT_OF_RANGE = bytearray(DISTINCT)
OUT_OF_RANGE[1] = 0x60 | 0x02                     # track 1: spread 3
OUT_OF_RANGE[4] = 0x15                            # rootless: bit 4
OUT_OF_RANGE[6] = 0x30                            # falling: bits 4-5
OUT_OF_RANGE[7] = 0x80                            # mono: bit 7
OUT_OF_RANGE[8] = 0x01 | 3 << 3 | 2 << 5          # track 0: dotted 1/32
OUT_OF_RANGE[11] = 6 << 2                         # track 1: gate 7/6
OUT_OF_RANGE[13] = 0x20                           # track 2: bit 5
OUT_OF_RANGE[16] = 3                              # retired page_last: ignored, whatever it holds
OUT_OF_RANGE[21] = 2                              # page_quick[1]: Keys has no quick half
OUT_OF_RANGE[24] = 2                              # ci_on
OUT_OF_RANGE[25] = 0x11                           # Euclid track 0: 17 hits
OUT_OF_RANGE[27] = 0x65                           # track 1: velocity 3
OUT_OF_RANGE[28] = 0xE3                           # track 1: gate value 7 (6, to the next hit, is valid since PL13)
OUT_OF_RANGE[33] = 4                              # page_slot[0]: no page on pad 29
OUT_OF_RANGE[34] = 8                              # page_slot[1]: past the page list
OUT_OF_RANGE[37] |= 0x30                          # melody_cfg track 0: range - 1 = 3
OUT_OF_RANGE[38] |= 0xE0                          # track 0: cfg1 bits 5-7
OUT_OF_RANGE[42] |= 0x20                          # track 2: cfg1 bit 5 only
OUT_OF_RANGE[45] = 0                              # melody_seed track 0: rhythm 0
OUT_OF_RANGE[46] = 0                              # notes 0
OUT_OF_RANGE[53] = 0xB1                           # rhythm_cfg track 0 (block 1): 17 second hits, combine accent
OUT_OF_RANGE[56] = 0xC4                           # track 1 (block 2): combine 6, 4 hits
OUT_OF_RANGE[57] = 0x80 | 0x40 | 3                # track 1: bit 7, thinning 2, rotation 3
OUT_OF_RANGE[58] = 5                              # track 1: cycle 5
OUT_OF_RANGE[61] = 0xF2                           # track 2: bits 3-7, cycle 2
OUT_OF_RANGE[62] = 0xFF                           # track 3: combine 7, 31 hits
OUT_OF_RANGE[65] = 0xF5                           # melody_vary track 0: bits 4-7, ties 1, jumps 1
OUT_OF_RANGE[69] = 0xFD                           # page_sub track 0: bits 2-7, tools 2
OUT_OF_RANGE[75] = 0x7F                           # euclid_last track 2: a pitch (0-139), kept as it is
OUT_OF_RANGE[76] = 0xC8                           # track 3: above 139, no pad's pitch
OUT_OF_RANGE[77] = 0x39                           # chord_voice track 0: row-2 shape 9, voice leading 3 (PL15)
OUT_OF_RANGE[78] = 0xC2                           # track 1: bits 6-7, row-2 shape 2
OUT_OF_RANGE[79] = 0x35                           # track 2: row-2 shape 5, top line: valid, kept
OUT_OF_RANGE[80] = 0x07                           # track 3: row-2 shape 7
OUT_OF_RANGE[81] = 0x59                           # repeat_cfg: rate 9, shape 1 (PL16)
OUT_OF_RANGE[82] = 0x02                           # byte 1 is spare
OUT_OF_RANGE[83] = 0x18                           # drum_page drum 0: bit 4; slot 0 (an alpha project's Repeat) -> 0, bit 3 (Pattern tools 2) kept
OUT_OF_RANGE[84] = 0x03                           # drum 1: slot 3 (no drum page yet)
OUT_OF_RANGE[85] = 0x05                           # drum 2: slot 5
OUT_OF_RANGE[86] = 0x00                           # drum 3: unchanged
OUT_OF_RANGE[87] = 0x11 | 2 << 5                  # drum_euclid drum 0: 17 hits, velocity hard (PL17)
OUT_OF_RANGE[89] = 0x03 | 3 << 5                  # drum 1: velocity 3
OUT_OF_RANGE[92] = 0x05 | 3 << 5                  # drum 2: roll 3, rotation 5
OUT_OF_RANGE[95] = 0xC4                           # drum_rhythm drum 0: combine 6, 4 hits
OUT_OF_RANGE[97] = 5                              # drum 0: cycle 5
OUT_OF_RANGE[98] = 0x20 | 0x11                    # drum 1: 17 second hits, combine 1
OUT_OF_RANGE[102] = 0x80 | 0x45                   # drum 2: spare bit 7
OUT_OF_RANGE[107] = 0x07                          # drum_accent drum 0: bit 2
OUT_OF_RANGE[108] = 0xF6                          # drum 1: bits 2-7
OUT_OF_RANGE[111] = 0                             # drum_seed drum 0: never 0
OUT_OF_RANGE[115] = 0x1F                          # chord_step: bits 4-7 (PL18)
OUT_OF_RANGE[116] = 0x0C                          # chord_pstrum: track 1 field 3 (PL19)
OUT_OF_RANGE[117] = 0x02                          # trig_mark: anything but 1 loads as 0 (PL20)
NEW_BAD = (53, 56, 57, 58, 61, 62, 65, 69, 75, 76, 77, 78, 80, 81, 82, 83, 84, 85, 87, 89, 92, 95, 97, 98, 102, 107, 108, 111, 115, 116, 117)
assert all(OUT_OF_RANGE[i] != DISTINCT[i] for i in (37, 38, 42, 45, 46) + NEW_BAD)
FIXED = bytearray(OUT_OF_RANGE)
for i, d in ((1, 0), (4, 0), (6, 0), (7, 0), (8, 0), (11, 0x08), (13, 0x08), (16, 0), (21, 0), (24, 0),
             (25, 0x00), (27, 0x25), (28, 0x43), (33, 0), (34, 0),
             (37, DISTINCT[37] & ~0x30), (38, DISTINCT[38]), (42, DISTINCT[42]), (45, 1), (46, 1),   # Euclid: each field alone (velocity, rotation kept)
             (53, 0xA0), (56, 0x04), (57, 0x43), (58, 0), (61, 0x02), (62, 0), (65, 0x05), (69, 0x01),   # PL14: each sub-field alone
             (75, 0x7F), (76, 72),
             (77, 0x30), (78, 0x02), (79, 0x35), (80, 0x00),
             (81, 0x50), (82, 0), (83, 0x08), (84, 0), (85, 0),
             (87, 0x40), (89, 0x23), (92, 0x05), (95, 0x04), (97, 0), (98, 0x20), (102, 0x45), (107, 0x03), (108, 0x02),
             (111, 1), (115, 0), (116, 0), (117, 0)):   # PL17: each drum sub-field alone; PL18: chord_step bits 4-7 -> 0                                                                      # euclid_last: above 139 -> 72; chord_voice (PL15): row-2 above 5 -> 0, bits 6-7 cleared
    FIXED[i] = d


GOOD = make_tail(DISTINCT)


@pytest.mark.parametrize("case, data", [
    ("stock", bytes(1000)),
    ("foreign", bytes((i * 151 + 7) * 2654435761 >> 13 & 0xFF for i in range(1000))),
    ("bad CRC", make_tail(DISTINCT, crc=int.from_bytes(GOOD[8:10], "big") ^ 0x0100)),
    ("format 3", make_tail(DISTINCT, fmt=3)),
    ("layout 2", make_tail(DISTINCT, layout=2)),
    ("n = 989", make_tail(DISTINCT + bytes(ROOM - LEN), n=ROOM + 1)),
    ("magic CTPS", make_tail(DISTINCT, magic=b"CTPS")),
], ids=["stock", "foreign", "bad CRC", "format 3", "layout 2", "n = 989", "magic CTPS"])
def test_a_load_without_a_valid_block_gives_defaults(pl21_image, pl21_manifest, case, data):
    h = NoteHarness(pl21_image)
    h.leds()
    put_settings(h, pl21_manifest, DISTINCT)
    write_tail(h, data)
    load(h)
    if case == "n = 989":                         # the CRC an unguarded read would match: 989 B, the last one just past
        past = bytes(h.uc.mem_read(record(h) + RECORD_SIZE, 1))   # the record (tail + 1000): only n <= ROOM refuses it
        crc = crc16(data[4:8] + data[HDR2:] + past)
        h.uc.mem_write(record(h) + TAIL + 8, crc.to_bytes(2, "big"))
    before = snapshot(h)                          # stock's load has done its own writes: slim's frame's are the rest
    h.leds()
    assert settings(h, pl21_manifest) == DEFAULTS, case
    after = snapshot(h)
    assert [i for i in range(RECORD_SIZE) if before[i] != after[i] and not TAIL <= i < TAIL + 1000] == [], case
    assert h.forbidden_writes == []


def test_a_shorter_payload_gives_defaults_past_it(pl21_image, pl21_manifest):
    """A block of 81 B (PL15's length): the fields within it load, the rest take their defaults."""
    h = NoteHarness(pl21_image)
    h.leds()
    put_settings(h, pl21_manifest, other(DISTINCT))
    write_tail(h, make_tail(DISTINCT[:PL15_LEN]))
    load(h)
    h.leds()
    assert settings(h, pl21_manifest) == DISTINCT[:PL15_LEN] + DEFAULTS[PL15_LEN:]


def test_a_longer_payload_loads_the_known_fields_and_a_save_keeps_the_rest(pl21_image, pl21_manifest):
    """A newer build's block (30 B more): this build's fields load; a save rewrites them and keeps the 30 B, n and a
    valid CRC over all of it, so the newer build finds its settings again."""
    m = pl21_manifest
    newer = bytes(range(1, 31))
    h = NoteHarness(pl21_image)
    h.leds()
    put_settings(h, m, other(DISTINCT))
    write_tail(h, make_tail(DISTINCT + newer))
    load(h)
    h.leds()
    assert settings(h, m) == DISTINCT
    h.track(0)
    h.press(0, shift=True)                        # the page track 0 was left on: Arp (page_slot[0] = 1)
    pick(h, 15)                                   # latch toggled: a setting changed with a pad
    h.press(0)                                    # close
    now = settings(h, m)
    assert now != DISTINCT
    save(h)
    t = tail(h)
    n = int.from_bytes(t[6:8], "little")
    assert n == LEN + 30 and t[HDR2 + LEN:HDR2 + n] == newer
    assert t[8:10] == crc16(t[4:8] + t[HDR2:HDR2 + n]).to_bytes(2, "big")
    assert t[HDR2:HDR2 + LEN] == now


def test_a_save_clears_the_alpha_magics(pl21_image, stock_image):
    """An alpha project's blocks at tail + 768 / + 832: a save zeroes their magics (an alpha build then loads defaults);
    the rest of the record as stock's save leaves it, but the format-2 block."""
    from harness import Harness
    a, b = Harness(stock_image), Harness(pl21_image)
    for h in (a, b):
        h.leds()
        write_tail(h, make_blocks(DISTINCT), at=BLOCK)
        save(h)
    ra, rb = snapshot(a), snapshot(b)
    assert rb[BLOCK:BLOCK + 4] == rb[BLOCK2:BLOCK2 + 4] == bytes(4)
    diff = [i for i in range(RECORD_SIZE) if ra[i] != rb[i]]
    block = range(TAIL, TAIL + HDR2 + LEN)
    assert [i for i in diff if i not in block and not BLOCK <= i < BLOCK + 4 and not BLOCK2 <= i < BLOCK2 + 4] == []


def test_new_project_clears_the_block_and_loads_the_defaults(pl21_image, pl21_manifest):
    h = NoteHarness(pl21_image)
    h.leds()
    write_tail(h, make_tail(DISTINCT))            # the previous project's block
    put_settings(h, pl21_manifest, DISTINCT)
    h.uc.mem_write(record(h), bytes(16))          # an empty slot: no valid header, so stock makes a new project
    load(h)
    assert tail(h) == bytes(10) + b"\xA5" + bytes(1000 - 11)   # pending
    h.leds()
    assert settings(h, pl21_manifest) == DEFAULTS


def test_a_save_before_the_frame_keeps_the_loaded_block(pl21_image, pl21_manifest):
    h = NoteHarness(pl21_image)
    h.leds()
    loaded = make_tail(DISTINCT)
    write_tail(h, loaded)
    load(h)
    save(h)                                       # before the next LED frame: the globals are still the old ones
    t = tail(h)
    assert t[:10] + t[11:] == loaded[:10] + loaded[11:]
    h.leds()
    assert settings(h, pl21_manifest) == DISTINCT


@pytest.mark.parametrize("tail", ["stock", "block"])
def test_a_load_with_a_chord_held_and_a_latched_arpeggio_leaves_nothing_on(pl21_image, pl21_manifest, tail):
    m = pl21_manifest
    h = NoteHarness(pl21_image)
    h.leds()
    h.track(1)
    h.uc.mem_write(sym(m, "chord_arp") + 2, bytes([1 | 2 << 3 | 0x80, 5 << 2]))   # latch, legato: always a note
    pick(h, 24)
    h.heartbeat(300)
    h.track(0)
    put(h, m, "chord_settings", [1, 1, 0, 0])    # triads
    h.down(24)                                    # held across the load
    assert h.sounding
    write_tail(h, bytes(1000) if tail == "stock" else make_tail(DISTINCT))
    load(h)
    h.leds()
    h.up(24)
    h.heartbeat(300)
    assert h.sounding == set(), sorted(h.sounding)
    base = sym(m, "held")
    assert [i for i in range(6) if h.r8(base + 14 * i) and h.r8(base + 14 * i + 9) & 0x10] == []   # no arpeggio entry


def test_the_build_refuses_a_lock_taking_call_from_session_applied(tmp_path):
    from helpers import write_feature, write_version
    from playbuild import build
    from playbuild.errors import BuildError
    fd = tmp_path / "f"
    src = ('#include "slim.h"\n#include "stock.h"\n'
           "void t_applied(void *obj, uint32_t what, uint32_t arg)\n{\n    session_refresh(obj, what, arg);\n}\n")
    write_feature(fd, "t", c_source=src, hooks=[("session_applied", "t_applied", 50)])
    with pytest.raises(BuildError, match="slim_call_session_applied -> t_applied -> session_refresh takes the DSP-service "
                                         "lock from a task slim has not identified"):
        build.build_once(write_version(tmp_path, "v", "SLX1", ["t"], fd), tmp_path / "w")


def test_a_save_changes_nothing_in_the_record_but_the_tail(pl21_image, stock_image):
    from harness import Harness
    a, b = Harness(stock_image), Harness(pl21_image)
    for h in (a, b):
        h.leds()
        save(h)
    ra, rb = (bytes(h.uc.mem_read(record(h), RECORD_SIZE)) for h in (a, b))
    diff = [i for i in range(RECORD_SIZE) if ra[i] != rb[i]]
    assert diff and TAIL <= min(diff) and max(diff) < TAIL + HDR2 + LEN


def test_a_load_cancels_a_count_in(pl21_image):
    from notes import PLAY_STORE, param
    h = NoteHarness(pl21_image)
    h.leds()
    h.track(0)
    set_count_in(h, 2)
    h.press(16)                                   # Record armed, stopped
    h.press(17)                                   # Play: the count starts
    h.heartbeat(5)
    assert [e for e in h.take("synth_on") if e[1] == 0xFF]   # the first click
    write_tail(h, make_tail(DISTINCT))            # a project with the count-in on too
    load(h)
    h.leds()
    for _ in range(300):                          # well past the bar at the project tempo
        h.heartbeat(10)
        h.leds()
    assert [e for e in h.take("synth_on") if e[1] == 0xFF] == [] and param(h, PLAY_STORE, 0) == 0


# ---- Alpha migration: PL10-PL20 projects load read-only; the alpha tests below plant alpha blocks and only load ----
# (removed at 1.0 with the alpha reader: followups.md)

# ---- PL14: the second block (spec 2026-10-21-melody-variations-design.md, "A second saved block") ----

def test_alpha_two_blocks_load(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = NoteHarness(pl21_image)
    h.leds()
    put_settings(h, m, other(DISTINCT))
    write_tail(h, make_blocks(DISTINCT), at=BLOCK)          # what PL14-PL20 save: block 1 (n = 56), block 2 (n2 = 62)
    load(h)
    h.leds()
    assert settings(h, m) == DISTINCT


CHANGED2 = bytearray(DISTINCT)
CHANGED2[5] = 0x02                                # another valid strum value


def test_an_alpha_project_loads_its_settings(pl21_image, pl21_manifest):
    """Alpha migration: a project saved by PL10-PL20 (blocks at tail + 768 / + 832, nothing at tail + 0) loads its
    settings once, read-only; the next save writes a format-2 block holding them and clears the alpha magics."""
    m = pl21_manifest
    h = NoteHarness(pl21_image)
    h.leds()
    put_settings(h, m, other(DISTINCT))
    write_tail(h, bytes(1000))
    write_tail(h, make_blocks(DISTINCT), at=BLOCK)
    load(h)
    h.leds()
    assert settings(h, m) == DISTINCT
    save(h)
    t = tail(h)
    assert t[:4] == b"CTPL" and t[HDR2:HDR2 + LEN] == DISTINCT
    assert t[BLOCK - TAIL:BLOCK - TAIL + 4] == t[BLOCK2 - TAIL:BLOCK2 - TAIL + 4] == bytes(4)


def test_a_format2_block_wins_over_alpha_blocks(pl21_image, pl21_manifest):
    """Format-2 block A at tail + 0, alpha blocks B at + 768 (an alpha build re-saving a beta project): A loads."""
    m = pl21_manifest
    a, b = DISTINCT, bytes(CHANGED2)
    h = NoteHarness(pl21_image)
    h.leds()
    put_settings(h, m, other(DISTINCT))
    write_tail(h, make_tail(a))
    write_tail(h, make_blocks(b), at=BLOCK)
    load(h)
    h.leds()
    assert settings(h, m) == a


def test_a_bad_format2_block_falls_back_to_alpha(pl21_image, pl21_manifest):
    """A format-2 block with a bad CRC at tail + 0: the alpha blocks at + 768 load."""
    m = pl21_manifest
    h = NoteHarness(pl21_image)
    h.leds()
    put_settings(h, m, other(DISTINCT))
    write_tail(h, make_tail(bytes(CHANGED2), crc=0x1234))
    write_tail(h, make_blocks(DISTINCT), at=BLOCK)
    load(h)
    h.leds()
    assert settings(h, m) == DISTINCT


def test_a_pl13_block_gives_defaults_for_the_new_fields(pl21_image, pl21_manifest):
    """A valid layout-1 block with n = 53 (PL13's) alone: its fields load, PL14's take their defaults."""
    m = pl21_manifest
    h = NoteHarness(pl21_image)
    h.leds()
    put_settings(h, m, other(DISTINCT))
    write_tail(h, make_block(DISTINCT[:PL13_LEN]), at=BLOCK)
    load(h)
    h.leds()
    assert settings(h, m) == DISTINCT[:PL13_LEN] + DEFAULTS[PL13_LEN:]


CHANGED = bytearray(DISTINCT)
CHANGED[5] = 0x02                                 # strum: another valid value


@pytest.mark.parametrize("case, block1", [
    ("PL13 re-save", make_block(bytes(CHANGED[:PL13_LEN]))),   # n = 53: block 1's bytes 61-63 and block 2 left stale
    ("one byte", make_block(bytes(CHANGED[:SPLIT]))),          # n = 56, a valid block 1, one payload byte changed
], ids=["PL13 re-save", "one byte"])
def test_a_changed_block_1_drops_block_2(pl21_image, pl21_manifest, case, block1):
    m = pl21_manifest
    h = NoteHarness(pl21_image)
    h.leds()
    put_settings(h, m, other(DISTINCT))
    write_tail(h, make_blocks(DISTINCT), at=BLOCK)
    write_tail(h, block1, at=BLOCK)                         # block 1 rewritten, block 2 as it was
    load(h)
    h.leds()
    assert settings(h, m) == bytes(CHANGED[:PL13_LEN]) + DEFAULTS[PL13_LEN:], case


B1 = make_block(DISTINCT[:SPLIT])
B1_PL13 = make_block(DISTINCT[:PL13_LEN])


def block2_for(b1=B1, **kw):
    return make_block2(b1, DISTINCT[SPLIT:], **kw)


@pytest.mark.parametrize("case, tail", [
    ("random", B1 + bytes((i * 151 + 7) * 2654435761 >> 13 & 0xFF for i in range(1000 - 832))),
    ("wrong check", B1 + block2_for(check=int.from_bytes(block2_for()[6:8], "big") ^ 0x0100)),
    ("other layout", B1 + block2_for(layout=2)),
    ("other magic", B1 + block2_for(magic=b"CTPS")),
    ("too long", B1 + make_block2(B1, DISTINCT[SPLIT:] + bytes(111), n=161)),   # 8 + 161 > the tail's last 168 B
    ("block 1 of 53 B", B1_PL13.ljust(64, b"\0") + block2_for(B1_PL13)),       # a matching block 2 needs n = 56
], ids=["random", "wrong check", "other layout", "other magic", "too long", "block 1 of 53 B"])
def test_foreign_bytes_at_832_are_ignored(pl21_image, pl21_manifest, case, tail):
    m = pl21_manifest
    h = NoteHarness(pl21_image)
    h.leds()
    put_settings(h, m, other(DISTINCT))
    write_tail(h, tail, at=BLOCK)
    load(h)
    h.leds()
    assert settings(h, m) == DISTINCT[:PL13_LEN] + DEFAULTS[PL13_LEN:], case
    assert h.forbidden_writes == []


def test_bad_new_values_are_fixed(pl21_image, pl21_manifest):
    """Each sub-field alone back to 0, the rest of its byte kept; spare bits cleared; euclid_last above 139 back to 72,
    a pitch of 0-139 kept."""
    m = pl21_manifest
    h = NoteHarness(pl21_image)
    h.leds()
    put_settings(h, m, DISTINCT)
    write_tail(h, make_tail(bytes(OUT_OF_RANGE)))
    load(h)
    h.leds()
    got = settings(h, m)
    assert got[PL13_LEN:] == bytes(FIXED[PL13_LEN:])
    assert got[75:77] == bytes([0x7F, 72])
    assert got[77:81] == bytes([0x30, 0x02, 0x35, 0x00])    # row-2 9 -> 0 with lead 3 kept; bits 6-7 cleared; 5 kept; 7 -> 0
    assert got[81:87] == bytes([0x50, 0, 0x08, 0, 0, 0])   # PL16: rate 9 -> 0 (shape, latch kept), byte 1 -> 0; drum_page 0x18 -> 0x08 (slot 0 opens Repeat, bit 3 kept), slot 3 and slot 5 -> 0
    d = got[87:]                                  # PL17: each sub-field alone back, the rest of its byte kept
    assert (d[0], d[2], d[5]) == (0x40, 0x23, 0x05) and d[1] == DISTINCT[88] and d[3] == DISTINCT[90]   # hits 17 -> 0 (velocity kept), velocity 3 -> medium, roll 3 -> 0 (rotation kept)
    assert (d[8], d[10], d[11]) == (0x04, 0, 0x20) and d[9] == DISTINCT[96]    # combine 6 -> 0 (hits kept), cycle 5 -> 0, 17 hits -> 0 (combine kept)
    assert (d[15], d[20], d[21], d[24]) == (0x45, 0x03, 0x02, 1)    # spare bit, accent 0x07 -> 0x03 and 0xF6 -> 0x02, seed 0 -> 1
    assert got == bytes(FIXED)


def test_euclid_last_reloads(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = NoteHarness(pl21_image)
    h.leds()
    h.track(1)
    pick(h, 26)                                   # a Note-view pad: track 1's last played pitch
    played = get(h, m, "euclid_last", 4)
    assert played[1] != 72 and played[0] == played[2] == played[3] == 72
    save(h)
    file = snapshot(h)
    put(h, m, "euclid_last", [60, 61, 62, 63])
    h.uc.mem_write(record(h), file)
    load(h)
    h.leds()
    assert get(h, m, "euclid_last", 4) == played


def test_a_pl16_length_block_2_gives_drum_tools_defaults(pl21_image, pl21_manifest):
    """A block 2 of PL16's length (n2 = 31, written here on PL17 itself: no older image, alpha policy) loads PL16's
    fields as saved and the four drum Pattern tools fields at their defaults."""
    m = pl21_manifest
    pl16_len = 87
    h = NoteHarness(pl21_image)
    h.leds()
    put_settings(h, m, other(DISTINCT))
    write_tail(h, make_blocks(DISTINCT[:pl16_len]), at=BLOCK)
    assert bytes(h.uc.mem_read(record(h) + BLOCK2 + 5, 1)) == bytes([pl16_len - SPLIT]) == bytes([31])
    load(h)
    h.leds()
    assert settings(h, m) == DISTINCT[:pl16_len] + DEFAULTS[pl16_len:]
    assert get(h, m, "drum_euclid", 8) == bytes([0x20, 0x00] * 4) and get(h, m, "drum_seed", 4) == bytes([1] * 4)
