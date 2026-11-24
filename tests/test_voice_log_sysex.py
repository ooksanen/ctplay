"""PL03D voice log: the USB SysEx protocol (spec section 3), through stock's real dispatcher entry."""
import pytest

from test_voice_log import REC, records
from voices import BUF, PAD, ROUTER_PTR, SIG, VoiceHarness

pytestmark = pytest.mark.emu


def nibbles(b: bytes) -> list[int]:
    return [(b[i] << 4) | b[i + 1] for i in range(0, len(b) - 1, 2)]


def parse(reply: bytes) -> tuple[int, int, int, list[int]]:
    assert reply[:4] == SIG and reply[-1] == 0xF7
    body = nibbles(reply[6:-1])
    return reply[4], reply[5], body[0], body[1:]


def played(img, n):
    h = VoiceHarness(img)
    h.set_headroom(0x20000)
    h.track(0)
    for k in range(n):
        h.down(16 + k, 100)
        h.up(16 + k)
    return h


def test_ping(vlog_image):
    h = played(vlog_image, 3)
    router, mask, reply = h.req(1)
    assert router == h.r32(ROUTER_PTR) and mask == 1
    cmd, seq, status, data = parse(reply)
    assert (cmd, seq, status) == (0x41, 5, 0)
    assert data == [0, 1, 12, 3, 3]                 # version 1, capacity 12, 3 stored, seq 3


def test_read_returns_the_records_in_two_halves(vlog_image, vlog_manifest):
    h = played(vlog_image, 11)
    want = records(h, vlog_manifest)
    got = []
    for start, count in ((0, 8), (8, 3)):
        _, _, reply = h.req(2, (start, count))
        cmd, _, status, data = parse(reply)
        assert (cmd, status, data[0]) == (0x42, 0, count)
        for i in range(count):
            t, seq, flags, note, voice, before, headroom = REC.unpack(bytes(data[1 + 10 * i:11 + 10 * i]))
            got.append(dict(t=t, seq=seq, synth=flags & 1, dsp=(flags >> 1) & 1, mode=(flags >> 2) & 7, note=note,
                            voice=voice, before=before, headroom=headroom))
    assert got == want
    assert len(reply) <= PAD


def test_clear_empties_the_ring_and_keeps_seq(vlog_image):
    h = played(vlog_image, 4)
    _, _, reply = h.req(3)
    assert parse(reply)[:3] == (0x43, 5, 0)
    assert parse(h.req(1)[2])[3] == [0, 1, 12, 0, 4]
    assert parse(h.req(2, (0, 0))[2])[2:] == (0, [0])            # an empty read is fine


@pytest.mark.parametrize("start,count", [(0, 9), (2, 2), (5, 0)])
def test_read_outside_what_is_stored_is_refused(vlog_image, start, count):
    h = played(vlog_image, 3)
    assert parse(h.req(2, (start, count))[2])[2] == 2


def test_unknown_command(vlog_image):
    h = played(vlog_image, 1)
    assert parse(h.req(9)[2])[:3] == (0x49, 5, 1)


def test_reply_goes_back_to_the_din_port(vlog_image):
    h = played(vlog_image, 1)
    assert h.req(1, port=1)[1] == 1 << 1


def test_short_request_is_swallowed_untouched(vlog_image):
    h = played(vlog_image, 1)
    short = bytes(list(SIG) + [1, 5] + [0] * (PAD - 8) + [0xF7])        # 231 bytes
    h.uc.mem_write(BUF + len(short), b"\xAA" * 16)
    h.sysex(short)
    assert h.out == [] and h.forwarded == 0
    assert bytes(h.uc.mem_read(BUF, len(short) + 16)) == short + b"\xAA" * 16


def test_other_sysex_reaches_stock(vlog_image):
    h = played(vlog_image, 1)
    h.sysex(bytes([0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7]))           # identity request
    assert h.forwarded == 1 and h.out == []
