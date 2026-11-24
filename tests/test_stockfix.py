"""Beta 2, feature stockfix (spec docs/specs/2026-11-22-beta2-fixes-design.md, section 1): a CC 27 (or NRPN 1:27) on
the project channel 16 crashed stock 1.2.1. Through stock's real MIDI input (0x08051720) and the main loop's
master-group send (0x08021578), as upstream's RC4.20 tools/emu_cc27.py: stock's image takes the table's fourth word
(code, 0xD0002800); PL22 clears the bit with no call; bits 0-2 still reach their stock handlers."""
import pytest
from emu_sc05 import CTX
from unicorn import UC_HOOK_CODE

from harness import Harness

pytestmark = pytest.mark.emu
MIDI_IN, SENDER, PEND = 0x08051720, 0x08021578, 0x20006A0D     # PEND = [0x20006A0C + 1], the master group's bits
BAD = 0xD0002800                                                 # the table's "fourth entry": code, not a function
HANDLERS = (0x08028F40, 0x08028F62, 0x08028FD4)                  # bits 0-2: stock's three entries
MSG = 0x20060100


def cc(h, number, value, channel=16):
    h.uc.mem_write(MSG, bytes([0xB0 | (channel - 1), number, value, 0]))
    h.call(MIDI_IN, CTX, MSG)


def send(h):
    """The main loop's send once; (the PCs it ran, an error or None)."""
    pcs = []
    hk = h.uc.hook_add(UC_HOOK_CODE, lambda uc, a, s, d: pcs.append(a & ~1))
    try:
        h.call(SENDER, maxins=200_000)
        err = None
    except Exception as e:                       # noqa: BLE001 (stock's image faults here: that is the bug)
        err = e
    h.uc.hook_del(hk)
    return pcs, err


@pytest.fixture(params=["stock", "pl22"])
def harness(request, stock_image, pl22_image):
    return request.param, Harness(stock_image if request.param == "stock" else pl22_image)


def test_cc27_on_channel_16_sets_bit_3_and_only_pl22_survives_the_send(harness):
    which, h = harness
    h.uc.mem_write(PEND - 1, bytes(4))
    cc(h, 27, 127)
    assert h.r8(PEND) & 8, "the CC sets the master group's pending bit 3"
    pcs, err = send(h)
    if which == "stock":
        assert err is not None or BAD in pcs, "stock calls the table's fourth word (the crash)"
    else:
        assert err is None and BAD not in pcs and not h.r8(PEND) & 8, "PL22: bit 3 cleared, nothing called"


@pytest.mark.parametrize("value", [0, 1])
def test_the_rhythms_nrpn_1_27_is_survived(pl22_image, value):
    """What a Circuit Rhythm sends when its -12 dB trim is toggled: NRPN 1:27 = 1 / 0 on channel 16."""
    h = Harness(pl22_image)
    if value == 0:
        cc(h, 27, 127)                           # an unchanged value marks nothing: from 1 to 0
        send(h)
    h.uc.mem_write(PEND - 1, bytes(4))
    for number, v in ((99, 1), (98, 27), (6, value)):
        cc(h, number, v)
    assert h.r8(PEND) & 8
    pcs, err = send(h)
    assert err is None and BAD not in pcs and not h.r8(PEND) & 8


@pytest.mark.parametrize("bit", [0, 1, 2])
def test_bits_0_to_2_still_reach_their_stock_handlers(pl22_image, bit):
    h = Harness(pl22_image)
    h.uc.mem_write(PEND, bytes([1 << bit]))
    hit = []
    hk = h.uc.hook_add(UC_HOOK_CODE, lambda uc, a, s, d: hit.append(a), begin=HANDLERS[bit], end=HANDLERS[bit])
    try:
        h.call(SENDER, maxins=2_000_000)
    except Exception:                            # noqa: BLE001 (the handler's own callees may leave the harness)
        pass
    h.uc.hook_del(hk)
    assert hit
