"""SL01D in emulation: the fill, the read-back and the checksums at the first hook call."""
import struct

import pytest
from unicorn import UC_HOOK_MEM_WRITE

from harness import HEAP_CUR, HEAP_LIMIT, Harness

pytestmark = pytest.mark.emu
FILL_LO, FILL_HI = 0x20044E58, 0x2004F000
WATCH_LO, WATCH_HI = 0x2004F000, 0x20050000
KEY = 0x5A1A0B5E
DRUM4 = 7
GREEN, MAGENTA, RED, WHITE, DIM_WHITE, CYAN = 0x17, 0x32, 0x53, 0x01, 0x02, 0x4D
RAM_LO, RAM_HI = 0x20000000, 0x20050000


def chunk_range(c):
    """Chunks 0-19 are 2 KB each from 0x20045000; chunk 20 is the short one (FILL_LO..0x20045000)."""
    if c == 20:
        return FILL_LO, 0x20045000
    lo = 0x20045000 + c * 0x800
    return lo, lo + 0x800


def fill_words(h, lo, hi):
    h.uc.mem_write(lo, b"".join(struct.pack("<I", a ^ KEY) for a in range(lo, hi, 4)))


def pattern_ok(h, lo, hi):
    data = bytes(h.uc.mem_read(lo, hi - lo))
    return all(w == a ^ KEY for a, (w,) in zip(range(lo, hi, 4), struct.iter_unpack("<I", data)))


def ram_start(man):
    return int(man["ram"]["start"], 16)


def test_manifest_ram_ends_where_the_fill_starts(sl01d_manifest):
    assert int(sl01d_manifest["ram"]["end"], 16) == 0x20044E58


def test_first_led_refresh_fills_the_region(sl01d_image):
    h = Harness(sl01d_image)
    assert not pattern_ok(h, FILL_LO, FILL_HI)
    h.leds()
    assert pattern_ok(h, FILL_LO, FILL_HI)


def test_first_call_can_be_a_button(sl01d_image, sl01d_manifest, stock_image):
    h, s = Harness(sl01d_image), Harness(stock_image)
    h.press(0)
    s.press(0)
    assert pattern_ok(h, FILL_LO, FILL_HI)
    assert h.r32(HEAP_LIMIT) == ram_start(sl01d_manifest)
    assert h.shape() == s.shape()


def test_nothing_else_changes(sl01d_image, sl01d_manifest, stock_image):
    h, s = Harness(sl01d_image), Harness(stock_image)
    h.leds()
    s.leds()
    a = bytes(h.uc.mem_read(RAM_LO, RAM_HI - RAM_LO))
    b = bytes(s.uc.mem_read(RAM_LO, RAM_HI - RAM_LO))
    skip = [(ram_start(sl01d_manifest), FILL_LO), (HEAP_LIMIT, HEAP_LIMIT + 4), (FILL_LO, FILL_HI)]
    for lo, hi in skip:
        a = a[:lo - RAM_LO] + bytes(hi - lo) + a[hi - RAM_LO:]
        b = b[:lo - RAM_LO] + bytes(hi - lo) + b[hi - RAM_LO:]
    diff = [i + RAM_LO for i in range(len(a)) if a[i] != b[i]]
    assert not diff, [hex(x) for x in diff[:10]]


def test_watched_part_is_never_written(sl01d_image):
    h = Harness(sl01d_image)
    hits = []
    h.uc.hook_add(UC_HOOK_MEM_WRITE, lambda uc, access, addr, size, value, d: hits.append(addr), None,
                  WATCH_LO, WATCH_HI - 1)
    h.leds()
    h.press(DRUM4, shift=True)
    for _ in range(30):
        h.leds()
    assert hits == []
    assert h.r32(0x2004EFFC) == 0x2004EFFC ^ KEY


def test_off_when_heap_reaches_slim_ram_writes_nothing(sl01d_image, sl01d_manifest, stock_image):
    h, s = Harness(sl01d_image), Harness(stock_image)
    for x in (h, s):
        x.w32(HEAP_CUR, ram_start(sl01d_manifest) + 8)
    assert h.leds() == s.leds()
    h.press(DRUM4, shift=True)
    s.press(DRUM4, shift=True)
    assert bytes(h.uc.mem_read(FILL_LO, FILL_HI - FILL_LO)) == bytes(s.uc.mem_read(FILL_LO, FILL_HI - FILL_LO))
    assert h.r32(HEAP_LIMIT) == 0x20044E58


def test_page_on_a_fresh_image(sl01d_image, stock_image):
    h, s = Harness(sl01d_image), Harness(stock_image)
    h.leds()
    s.leds()
    h.press(DRUM4, shift=True)
    s.press(DRUM4, shift=True)
    lit, ref = h.leds(), s.leds()
    assert lit[:32] == [GREEN] * 21 + [0, 0, WHITE] + [GREEN] * 8
    assert lit[32:] == ref[32:]
    assert h.shape() == s.shape() and h.ev == s.ev and h.dsp_writes == s.dsp_writes
    h.press(DRUM4, shift=True)
    s.press(DRUM4, shift=True)
    assert h.leds() == s.leds()


def test_carried_over_all(sl01d_image):
    h = Harness(sl01d_image)
    fill_words(h, FILL_LO, FILL_HI)
    h.leds()
    h.press(DRUM4, shift=True)
    assert h.leds()[22] == CYAN


def test_carried_over_some(sl01d_image):
    h = Harness(sl01d_image)
    fill_words(h, *chunk_range(0))
    h.leds()
    h.press(DRUM4, shift=True)
    assert h.leds()[22] == DIM_WHITE


def test_read_back_failure_is_red(sl01d_image):
    from unicorn import UC_HOOK_MEM_READ
    h = Harness(sl01d_image)
    word = 0x2004A000 + 0x40
    h.uc.hook_add(UC_HOOK_MEM_READ, lambda uc, access, addr, size, value, d: uc.mem_write(word, bytes(4)), None,
                  word, word + 3)
    h.leds()
    h.press(DRUM4, shift=True)
    lit = h.leds()
    assert lit[10] == RED
    assert lit[:10] == [GREEN] * 10 and lit[11:21] == [GREEN] * 10


@pytest.mark.parametrize("steps", [
    [(DRUM4, False)],
    [(14, False), (DRUM4, True), (DRUM4, True)],
    [(15, False), (DRUM4, True), (DRUM4, True)],
    [(6, True)],
])
def test_stock_behaviour_elsewhere(sl01d_image, stock_image, steps):
    h, s = Harness(sl01d_image), Harness(stock_image)
    for button, shift in steps:
        h.press(button, shift=shift)
        s.press(button, shift=shift)
    assert h.shape() == s.shape() and h.leds() == s.leds()


def _open_page(h):
    h.press(DRUM4, shift=True)
    return h.leds()


def test_change_in_a_chunk_shows_within_21_refreshes(sl01d_image):
    h = Harness(sl01d_image)
    h.leds()
    h.w32(0x20047008, 0xFFFFFFFF)
    for _ in range(21):
        h.leds()
    h.w32(0x20047008, 0x20047008 ^ KEY)
    lit = _open_page(h)
    assert lit[4] == MAGENTA
    assert [lit[i] for i in range(21) if i != 4] == [GREEN] * 20


def test_change_in_a_block_shows_within_8_refreshes(sl01d_image):
    h = Harness(sl01d_image)
    h.leds()
    orig = h.r32(0x2004F408)
    h.w32(0x2004F408, 0xFFFFFFFF ^ orig)
    for _ in range(8):
        h.leds()
    h.w32(0x2004F408, orig)
    lit = _open_page(h)
    assert lit[26] == MAGENTA
    assert [lit[24 + b] for b in range(8) if b != 2] == [GREEN] * 7


def test_page_open_finds_a_change_at_once(sl01d_image):
    h = Harness(sl01d_image)
    h.leds()
    addr = chunk_range(12)[0] + 8
    h.w32(addr, 0xFFFFFFFF)
    assert _open_page(h)[12] == MAGENTA


def test_transient_change_is_latched(sl01d_image):
    h = Harness(sl01d_image)
    h.leds()
    h.press(DRUM4, shift=True)
    addr = chunk_range(7)[0] + 4
    h.w32(addr, 0xFFFFFFFF)
    for _ in range(21):
        h.leds()
    h.w32(addr, addr ^ KEY)
    for _ in range(42):
        lit = h.leds()
    assert lit[7] == MAGENTA
