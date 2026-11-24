"""SL00D in emulation: initialisation, the display, the probe states, and stock behaviour everywhere else."""
import pytest
import struct
from pathlib import Path

from unicorn import UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE

from harness import HEAP_CUR, HEAP_LIMIT, Harness

pytestmark = pytest.mark.emu
GREEN, YELLOW, MAGENTA, RED, WHITE = 0x17, 0x2D, 0x32, 0x53, 0x01
DRUM4, DRUM3 = 7, 6
VTOR = 0xE000ED08
DUMP = Path(__file__).resolve().parents[1] / "ctre" / "Firmware-Analysis" / "ram_dump_firmware_0x08037988.bin"


def device_like(h):
    h.w32(VTOR, 0x08010000)                    # as the device sets it; the emulator's VTOR reads 0 otherwise
    return h


def ram_start(man):
    return int(man["ram"]["start"], 16)


def test_first_led_refresh_initialises_once(sl00d_image, sl00d_manifest):
    h = Harness(sl00d_image)
    assert h.r32(HEAP_LIMIT) == 0x20044E58
    h.leds()
    assert h.r32(HEAP_LIMIT) == ram_start(sl00d_manifest)
    h.leds()
    assert h.r32(HEAP_LIMIT) == ram_start(sl00d_manifest)


def test_first_call_can_be_a_button(sl00d_image, sl00d_manifest, stock_image):
    h, s = Harness(sl00d_image), Harness(stock_image)
    h.press(0)
    s.press(0)
    assert h.r32(HEAP_LIMIT) == ram_start(sl00d_manifest)
    assert h.shape() == s.shape()


def test_display_is_off_until_triggered(sl00d_image, stock_image):
    assert Harness(sl00d_image).leds() == Harness(stock_image).leds()


def test_shift_drum4_shows_a_free_itcm(sl00d_image, stock_image):
    h, s = device_like(Harness(sl00d_image)), Harness(stock_image)
    h.leds()
    s.leds()
    h.press(DRUM4, shift=True)
    s.press(DRUM4, shift=True)
    lit, ref = h.leds(), s.leds()
    assert lit[:16] == [GREEN] * 16            # the emulator's ITCM is zeroed RAM
    assert lit[16:31] == [0] * 15 and lit[31] == WHITE
    assert lit[32:] == ref[32:]                # buttons and knobs untouched
    assert h.shape() == s.shape() and h.ev == s.ev and h.dsp_writes == s.dsp_writes
    h.press(DRUM4, shift=True)                 # toggle off: stock pads again
    s.press(DRUM4, shift=True)
    assert h.leds() == s.leds()


def test_drum4_without_shift_and_shift_other_buttons_are_stock(sl00d_image, stock_image):
    h, s = Harness(sl00d_image), Harness(stock_image)
    for button, shift in ((DRUM4, False), (DRUM3, False), (5, True), (4, True), (DRUM4, False)):
        h.press(button, shift=shift)
        s.press(button, shift=shift)
        assert h.shape() == s.shape() and h.leds() == s.leds(), (button, shift)


def test_probe_states(sl00d_image):
    h = device_like(Harness(sl00d_image))
    h.uc.mem_write(3 * 1024, b"\x01\x02\x03\x04")                 # data present at boot -> yellow
    h.leds()                                                      # first call: boot checksums
    h.uc.mem_write(5 * 1024 + 8, b"\xff")                         # changed after boot -> magenta
    stuck = 9 * 1024 + 512                                        # the probe's test word of block 9

    def writes_do_not_stick(uc, access, address, size, value, data):
        uc.mem_write(stuck, bytes(4))                             # every read sees 0 -> red

    h.uc.hook_add(UC_HOOK_MEM_READ, writes_do_not_stick, begin=stuck, end=stuck + 3)
    word = 3 * 1024 + 512
    n_writes = []
    h.uc.hook_add(UC_HOOK_MEM_WRITE, lambda *a: n_writes.append(a[2]), begin=word, end=word + 3)
    h.press(DRUM4, shift=True)
    assert n_writes == []                                         # a non-zero block is never write-tested
    expect = [GREEN] * 16
    expect[3], expect[5], expect[9] = YELLOW, MAGENTA, RED
    assert h.leds()[:16] == expect
    assert bytes(h.uc.mem_read(3 * 1024, 4)) == b"\x01\x02\x03\x04"   # the write test restored the data


def test_transient_change_is_latched(sl00d_image):
    h = device_like(Harness(sl00d_image))
    h.leds()
    addr = 6 * 1024 + 16
    orig = bytes(h.uc.mem_read(addr, 1))
    h.uc.mem_write(addr, b"\xff")
    for _ in range(16):                                           # one full scan of the 16 blocks
        h.leds()
    h.uc.mem_write(addr, orig)                                    # restored: the checksum matches again
    h.press(DRUM4, shift=True)
    expect = [GREEN] * 16
    expect[6] = MAGENTA
    assert h.leds()[:16] == expect


def test_disabled_when_heap_reaches_our_ram(sl00d_image, sl00d_manifest, stock_image):
    h, s = Harness(sl00d_image), Harness(stock_image)
    for x in (h, s):
        x.w32(HEAP_CUR, ram_start(sl00d_manifest) + 8)              # stock allocated into slim's RAM at boot
    assert h.leds() == s.leds()
    h.press(DRUM4, shift=True)
    s.press(DRUM4, shift=True)
    assert h.leds() == s.leds() and h.shape() == s.shape()
    assert h.r32(HEAP_LIMIT) == 0x20044E58                          # never reserved


def test_vector_table_block_is_never_written(sl00d_image):
    h = Harness(sl00d_image)                                      # VTOR reads 0: the vector table is in block 0
    writes = []
    h.uc.hook_add(UC_HOOK_MEM_WRITE, lambda *a: writes.append(a[2]), begin=0x200, end=0x203)
    h.press(DRUM4, shift=True)
    assert h.leds()[:16] == [YELLOW] + [GREEN] * 15
    assert writes == []


BASES = [0x20006A58, 0x20006AA4, 0x20006E70, 0x2000775C, 0x200084DC, 0x20008D44, 0x200092B8, 0x2000AD7C]
MAGENTA_PAD = 0x32


def dump_u32(a):
    return struct.unpack_from("<I", DUMP.read_bytes(), a - 0x20000000)[0]


def fill_run(read, base, limit):
    n = 0
    while base + 4 * n < limit and read(base + 4 * n) == 0xA5A5A5A5:
        n += 1
    return n * 4


def pads_for(sizes):
    """sizes[c] = bytes, or None for a layout-mismatch column. Per-pad rule, written independently of the C loops."""
    pads = [0] * 32
    for p in range(32):
        row, col = p // 8, p % 8
        size = sizes[col]
        if size is None:
            pads[p] = MAGENTA_PAD if row == 3 else 0
        elif size == 0:
            pads[p] = 0
        elif size < 128:
            pads[p] = RED if row == 3 else 0
        else:
            height = min(4, -(-size // 512))
            if 3 - row < height:
                pads[p] = WHITE if (size > 2048 and row == 0) else GREEN
    return pads


def expected_stack_sizes():
    end = dump_u32(0x20002B48) & ~3
    return [fill_run(dump_u32, b, end) for b in BASES]


def test_stack_page_matches_an_independent_scan(sl00d_image, stock_image):
    sizes = expected_stack_sizes()
    assert all(sz >= 64 for sz in sizes)                          # sanity of the dump: every base starts a fill run
    # the bases are the starts of the dump's runs, found without them
    end, a, starts = dump_u32(0x20002B48) & ~3, (dump_u32(0x20002B40) + 3) & ~3, []
    while a < end:
        if dump_u32(a) == 0xA5A5A5A5 and (a == (dump_u32(0x20002B40) + 3) & ~3 or dump_u32(a - 4) != 0xA5A5A5A5):
            if fill_run(dump_u32, a, end) >= 64:
                starts.append(a)
        a += 4
    assert starts == BASES
    h, s = Harness(sl00d_image), Harness(stock_image)
    h.leds()
    s.leds()
    h.press(DRUM3, shift=True)
    s.press(DRUM3, shift=True)
    lit, ref = h.leds(), s.leds()
    assert lit[:32] == pads_for(sizes)
    assert lit[32:] == ref[32:]
    assert h.shape() == s.shape() and h.ev == s.ev and h.dsp_writes == s.dsp_writes


def live_sizes(h):
    end = h.r32(HEAP_CUR) & ~3
    return [fill_run(h.r32, b, end) for b in BASES]


def test_stack_columns_are_fixed_and_checked(sl00d_image):
    h = Harness(sl00d_image)
    fill = struct.pack("<I", 0xA5A5A5A5)
    h.uc.mem_write(BASES[3], fill * 75 + bytes(4))                # 300 B of fill, then a non-fill word
    h.uc.mem_write(BASES[0], fill * 513 + bytes(4))               # 2052 B -> 4 pads, white top
    h.uc.mem_write(BASES[6], bytes(4))                            # not fill before the first hook call -> mismatch
    h.leds()                                                      # first hook call: layout check
    h.w32(BASES[5], 0)                                            # fully used after init -> column off
    h.press(DRUM3, shift=True)
    sizes = live_sizes(h)
    assert sizes[0] == 2052 and sizes[3] == 300 and sizes[5] == 0
    sizes[6] = None
    lit = h.leds()[:32]
    assert lit == pads_for(sizes)
    assert [lit[r * 8 + 0] for r in range(4)] == [WHITE, GREEN, GREEN, GREEN]
    assert [lit[r * 8 + 3] for r in range(4)] == [0, 0, 0, GREEN]
    assert [lit[r * 8 + 5] for r in range(4)] == [0] * 4
    assert [lit[r * 8 + 6] for r in range(4)] == [0, 0, 0, MAGENTA_PAD]


def test_just_over_2048_bytes_is_white_topped(sl00d_image):
    h = Harness(sl00d_image)
    fill = struct.pack("<I", 0xA5A5A5A5)
    h.uc.mem_write(BASES[0], fill * 512 + b"\xa5" + bytes(3))     # 2048 B of fill words, then a word that is not fill
    h.leds()
    h.press(DRUM3, shift=True)
    assert live_sizes(h)[0] == 2048
    assert h.leds()[:32] == pads_for(live_sizes(h))   # 2048 B: four green pads, no white
    h2 = Harness(sl00d_image)
    h2.uc.mem_write(BASES[0], fill * 513 + bytes(4))
    h2.leds()
    h2.press(DRUM3, shift=True)
    lit = h2.leds()[:32]
    assert lit[0] == WHITE and lit[8] == GREEN


def test_pages_switch_and_turn_off(sl00d_image, stock_image):
    pads = pads_for(expected_stack_sizes())
    h, s = device_like(Harness(sl00d_image)), Harness(stock_image)
    h.leds()
    s.leds()
    h.press(DRUM4, shift=True)
    assert h.leds()[:16] == [GREEN] * 16 and h.leds()[31] == WHITE
    h.press(DRUM3, shift=True)
    assert h.leds()[:32] == pads
    h.press(DRUM4, shift=True)                                    # back to the ITCM page
    assert h.leds()[31] == WHITE
    h.press(DRUM3, shift=True)
    h.press(DRUM3, shift=True)                                    # off
    s.press(DRUM3, shift=True)
    s.press(DRUM3, shift=True)
    assert h.leds() == s.leds()
