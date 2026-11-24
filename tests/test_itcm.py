"""ITCM opt-in (spec 2026-10-17-itcm-opt-in-design.md D5-D6): at the first hook call the runtime checks the MPU, then
write-tests and zeroes slim's ITCM span before any init(); any failure leaves slim off. The emulator maps ITCM zeroed,
unlike the device (non-zero at boot): each test first fills it with a pattern."""
import pytest
from unicorn import UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE

from harness import Harness
from test_saved import LEN
from test_transparency import run, script

pytestmark = pytest.mark.emu
ITCM_LO, ITCM_HI = 0x0400, 0x4000
MPU_CTRL = 0xE000ED94
HEAP_LIMIT = 0x20002B44
FILL = 0xA5


def sym(m, name):
    return int(m["symbols"][name], 16)


def span(m):
    return int(m["itcm"]["start"], 16), int(m["itcm"]["end"], 16)


def harness(image):
    h = Harness(image)
    h.uc.mem_write(ITCM_LO, bytes([FILL]) * (ITCM_HI - ITCM_LO))
    return h


def writes_into_itcm(h):
    seen = []
    h.uc.hook_add(UC_HOOK_MEM_WRITE, lambda u, acc, a, s, v, d: seen.append(a), begin=0, end=ITCM_HI - 1)
    return seen


def test_itcm_span_is_zeroed_and_init_runs(itcm_image, itcm_manifest):
    h = harness(itcm_image)
    lo, hi = span(itcm_manifest)
    h.leds()                                                           # the first hook call
    assert h.r32(HEAP_LIMIT) == sym(itcm_manifest, "__slim_ram_start")
    assert h.r8(sym(itcm_manifest, "slim_inited")) == 1
    assert h.r32(sym(itcm_manifest, "probe_itcm")) == 0xC0FFEE01       # init() ran after the zeroing
    assert bytes(h.uc.mem_read(lo + 4, hi - lo - 4)) == bytes(hi - lo - 4)
    assert bytes(h.uc.mem_read(ITCM_LO, lo - ITCM_LO)) == bytes([FILL]) * (lo - ITCM_LO)   # the rest untouched


def test_itcm_writes_stay_in_the_span(itcm_image, itcm_manifest):
    h = harness(itcm_image)
    lo, hi = span(itcm_manifest)
    seen = writes_into_itcm(h)
    h.leds()
    for step in script(1, 10):
        run(h, step)
    assert seen and all(lo <= a < hi for a in seen), sorted({hex(a) for a in seen if not lo <= a < hi})


def test_itcm_failed_word_leaves_slim_off(itcm_image, itcm_manifest, stock_image):
    h, s = harness(itcm_image), Harness(stock_image)
    lo, hi = span(itcm_manifest)
    last = hi - 4

    def corrupt(u, acc, a, size, v, d):                               # a stuck bit: reads differ from what was written
        u.mem_write(last, bytes(b ^ 0x01 for b in u.mem_read(last, 4)))
    h.uc.hook_add(UC_HOOK_MEM_READ, corrupt, begin=last, end=last + 3)
    h.leds()
    assert h.r8(sym(itcm_manifest, "slim_inited")) == 0
    assert h.r32(HEAP_LIMIT) == sym(itcm_manifest, "__slim_ram_start")   # claimed, so it stays off for the boot
    assert h.r32(sym(itcm_manifest, "probe_itcm")) != 0xC0FFEE01        # no init()
    s.leds()
    for step in script(1, 10):
        run(h, step)
        run(s, step)
    assert h.outputs()["leds"] == s.outputs()["leds"]


def test_mpu_on_writes_nothing(itcm_image, itcm_manifest):
    h = harness(itcm_image)
    h.uc.mem_write(MPU_CTRL, (1).to_bytes(4, "little"))
    seen = writes_into_itcm(h)
    h.leds()
    assert seen == []
    assert h.r8(sym(itcm_manifest, "slim_inited")) == 0
    assert bytes(h.uc.mem_read(ITCM_LO, ITCM_HI - ITCM_LO)) == bytes([FILL]) * (ITCM_HI - ITCM_LO)


def test_pl09_starts_clean_from_dirty_itcm(pl09_image, pl09_manifest):
    """The device's ITCM is non-zero at boot: PL09's held chords, arpeggio state and mono visits must start empty."""
    from chord_model import settings
    from notes import NoteHarness
    from test_chord import held_counts, set_chord
    h = NoteHarness(pl09_image)
    h.uc.mem_write(ITCM_LO, bytes([FILL]) * (ITCM_HI - ITCM_LO))
    h.track(0)
    assert held_counts(h, pl09_manifest) == [0] * 6
    set_chord(h, pl09_manifest, 0, settings(1))
    h.down(24)
    assert len([k for k in h.sounding if k[0] == "synth"]) == 3
    h.up(24)
    h.heartbeat(300)
    assert h.sounding == set() and held_counts(h, pl09_manifest) == [0] * 6


def test_write_test_waits_for_its_stores(pl09_image, pl09_manifest):
    """Final review: the M7 store buffer could serve a word's own store back to the read that checks it, so each pass
    ends its writes with a dsb before reading (inside the pass loop, which -Os keeps rolled: one instruction)."""
    start = sym(pl09_manifest, "slim_ready") & ~1
    following = min(int(v, 16) for v in pl09_manifest["symbols"].values() if int(v, 16) > start)
    code = pl09_image[start - 0x08010000:following - 0x08010000]
    assert code.count(bytes.fromhex("bff34f8f")) >= 1                  # dsb sy


def test_link_image_in_itcm(pl16_manifest):
    """PL16: the link's last-sent image lives in ITCM (the link's RAM budget is 16 B)."""
    sent = sym(pl16_manifest, "sent")
    assert ITCM_LO <= sent < ITCM_HI, hex(sent)
    lo, hi = span(pl16_manifest)
    assert lo <= sent and sent + LEN <= hi


def test_link_image_frees_the_heap_tail(pl16_manifest, pl15_published_manifest):
    """Against the published PL15 (skipped without its tag): the image moved out of the heap tail freed its 81 B."""
    assert sym(pl15_published_manifest, "sent") >= 0x20000000        # PL15: in the heap tail
    freed = pl15_published_manifest["ram"]["used"] - pl16_manifest["ram"]["used"]
    assert freed >= 80, freed
