"""PL12 CTCtrl link (spec docs/specs/2026-10-18-ctctrl-link-design.md): SysEx in through stock's dispatcher entry,
replies and pushes caught at stock's SysEx output."""
import pytest

from drums import DRUM_PAD, DrumHarness, drum_setup
from notes import OUTBUF, NoteHarness
from sysex import BUF, ROUTER_PTR, SysexCapture
from test_saved import DISTINCT, LEN, get, load, make_tail, pick, put, put_settings, set_count_in, settings, sym, write_tail

pytestmark = pytest.mark.emu

TRACK_SELECT = bytes([0xF0, 0x00, 0x20, 0x29, 0x01, 0x64, 0x04, 0x03])


class LinkHarness(SysexCapture, NoteHarness):
    pass


def test_stock_sends_track_select_through_sysex_out_from_the_ui_task(pl21_image):
    """The link pushes from the LED task (UI task). Stock already sends SysEx from that task: choosing a track (the
    controller's button route, as a press on the device) sends the track-select message CTCtrl follows, through
    sysex_out with the router [0x200069F4] and port mask 1 (USB). Confirmed in emulation 2026-10-19 (plan Task 1)."""
    h = LinkHarness(pl21_image)
    h.out.clear()
    h.press(1)                                       # Synth 2
    sent = [o for o in h.out if o[2][:8] == TRACK_SELECT]
    assert len(sent) == 1, h.out
    router, mask, data = sent[0]
    assert data == TRACK_SELECT + bytes([0x01, 0x00, 0xF7])
    assert router == h.r32(ROUTER_PTR)
    assert mask == 1                                 # USB only (finding 2026-10-19: the only SysEx this press sends)


# ---- PL12: hello, read, state, pushes (plan Task 3) ----

HELLO, READ, WRITE = 0x10, 0x11, 0x12
LINKED = [(0, 4, 1), (4, 1, 1), (5, 1, 1), (6, 1, 1), (7, 1, 1), (8, 8, 1), (24, 1, 1), (25, 8, 1), (37, 8, 1),
          (53, 12, 1), (65, 4, 1), (77, 4, 1), (81, 2, 1),
          (87, 8, 1), (95, 12, 1), (107, 4, 1), (115, 1, 1), (116, 1, 1)]            # PL14: rhythm_cfg, melody_vary; PL15: chord_voice; PL16: repeat_cfg; PL17: the drums' Pattern tools (drum_seed not linked); PL18: chord_step; PL19: chord_pstrum (PL20: trig_mark is saved, not linked)
DOWN = 19                                        # Octave ▼: the next Play page


class PL12(LinkHarness):
    def req(self, cmd, body=(), port=0):
        self.sysex(bytes([0xF0, 0x7D, 0x53, 0x4C, cmd, *body, 0xF7]), port)

    def frame(self):
        """One LED frame; what it sent."""
        self.out.clear()
        self.leds()
        return list(self.out)

    def hello(self, port=0):
        self.req(HELLO, port=port)
        return self.frame()


def linked(payload):
    """The payload with the bytes the link does not carry zeroed."""
    keep = {i for o, s, _ in LINKED for i in range(o, o + s)}
    return bytes(b if i in keep else 0 for i, b in enumerate(payload))


# ---- saved2: link protocol 2 (two-byte values, the state in chunks of CHUNK bytes, one message per LED frame) ----

CHUNK = 64
CHUNKS = -(-LEN // CHUNK)                        # 2 at 118 B: bytes 0-63 and 64-117


def two(v):
    """A two-byte value: low 7 bits, then high 7 bits."""
    return [v & 0x7F, v >> 7]


def chunk_of(msg):
    """A chunk message's (payload offset, bytes)."""
    data = msg[2]
    assert data[:5] == bytes([0xF0, 0x7D, 0x53, 0x4C, 0x51]) and data[-1] == 0xF7
    layout, n, off, cnt, nib = data[5], data[6] | data[7] << 7, data[8] | data[9] << 7, data[10], data[11:-1]
    assert (layout, n) == (1, LEN) and 1 <= cnt <= CHUNK and len(nib) == 2 * cnt and max(nib) <= 0x0F
    assert off % CHUNK == 0 and cnt == min(CHUNK, LEN - off)
    return off, bytes(nib[i] << 4 | nib[i + 1] for i in range(0, len(nib), 2))


def drain(h, max_frames=20):
    """LED frames until one sends nothing; every message sent, at most one a frame."""
    msgs = []
    for _ in range(max_frames):
        sent = h.frame()
        assert len(sent) <= 1, sent
        if not sent:
            return msgs
        msgs += sent
    raise AssertionError(f"still sending after {max_frames} frames")


def assemble(msgs):
    """The payload from chunk messages, later copies over earlier ones; every byte must have arrived."""
    out, have = bytearray(LEN), set()
    for msg in msgs:
        off, b = chunk_of(msg)
        out[off:off + len(b)] = b
        have |= set(range(off, off + len(b)))
    assert have == set(range(LEN)), sorted(set(range(LEN)) - have)
    return bytes(out)


def answer(h):
    """The chunk answering a write: the next frame's one message (an answer goes before any push)."""
    sent = h.frame()
    assert len(sent) == 1, sent
    return chunk_of(sent[0])


def unchanged(h, before):
    """A write's answer holds the bytes from before it."""
    off, b = answer(h)
    return b == linked(before)[off:off + len(b)]


def fresh(img):
    h = PL12(img)
    h.leds()                                         # the first frame applies what the record holds (as test_saved)
    return h


def test_hello_reply_bytes(pl21_image):
    h = fresh(pl21_image)
    sent = h.hello(port=0)
    assert len(sent) == 1
    router, mask, data = sent[0]
    want = bytes([0xF0, 0x7D, 0x53, 0x4C, 0x50, 0x02]) + b"PL21  " + bytes([0x01, *two(LEN), len(LINKED)])
    want += bytes(v for o, s, r in LINKED for v in (*two(o), s, r)) + b"\xF7"
    assert (router, mask, data) == (h.r32(ROUTER_PTR), 1, want)
    assert LEN == 118 and data[13:15] == bytes([118, 0])          # the two-byte length


def test_sysex_in_only_hands_over(pl21_image):
    h = fresh(pl21_image)
    for cmd in (HELLO, READ):
        h.req(cmd)
        assert h.out == [] and h.forwarded == 0
    assert [d[4] for _, _, d in drain(h)] == [0x50] + [0x51] * CHUNKS   # the hello reply, then the state's chunks


def test_read_returns_the_linked_bytes(pl21_image, pl21_manifest):
    h = fresh(pl21_image)
    put_settings(h, pl21_manifest, DISTINCT)          # page_quick and page_slot are not 0 in it
    h.req(READ)
    sent = drain(h)                                  # one a frame (drain checks)
    assert len(sent) == CHUNKS == 2 and {m for _, m, _ in sent} == {1}
    assert [chunk_of(s)[0] for s in sent] == [0, CHUNK]          # in order
    assert assemble(sent) == linked(DISTINCT) != DISTINCT


def test_nothing_is_sent_without_a_hello(pl21_image):
    h = fresh(pl21_image)
    h.track(0)
    h.press(0, shift=True)                           # the Chords page
    for pad in (1, 28, 31):
        pick(h, pad)
        assert h.frame() == []


def test_a_pad_press_pushes_one_chunk(pl21_image, pl21_manifest):
    h = fresh(pl21_image)
    h.track(0)
    h.press(0, shift=True)
    h.hello()
    assert h.frame() == []                           # in sync: nothing to push
    pick(h, 28)                                      # strum medium
    sent = drain(h)
    assert len(sent) == 1
    off, b = chunk_of(sent[0])
    assert off == 0 and b[5] == 2                    # the chunk holding offset 5, then nothing
    h.req(READ)
    assert assemble(drain(h))[:CHUNK] == b


def test_a_page_step_pushes_nothing(pl21_image):
    h = fresh(pl21_image)
    h.track(0)
    h.press(0, shift=True)
    h.hello()
    for _ in range(3):
        h.press(DOWN)
        assert h.frame() == []


def test_a_load_pushes_every_changed_chunk(pl21_image, pl21_manifest):
    h = fresh(pl21_image)
    h.hello()
    before = linked(settings(h, pl21_manifest))
    write_tail(h, make_tail(DISTINCT))
    load(h)
    sent = drain(h)                                  # each changed chunk once, one a frame, then nothing
    after = linked(DISTINCT)
    changed = [k * CHUNK for k in range(CHUNKS) if before[k * CHUNK:(k + 1) * CHUNK] != after[k * CHUNK:(k + 1) * CHUNK]]
    assert changed == [0, CHUNK]                     # DISTINCT differs from the defaults in both
    assert [chunk_of(s)[0] for s in sent] == changed
    assert assemble(sent) == after


def test_pushes_go_to_the_hello_port(pl21_image):
    h = fresh(pl21_image)
    h.track(0)
    h.press(0, shift=True)
    assert h.hello(port=1)[0][1] == 2
    pick(h, 3)
    assert [m for _, m, _ in h.frame()] == [2]


def test_chunks_stay_on_the_hello_port_until_a_new_hello(pl21_image):
    """Task 4 review (PL12's rule): once a hello came, a read or a write from another port does not move the link's
    chunks there; a hello from that port takes the link over."""
    h = fresh(pl21_image)
    open_page(h, 0)                              # the Chords page
    assert [m for _, m, _ in h.hello(port=0)] == [1]
    h.req(READ, port=1)
    assert [m for _, m, _ in drain(h)] == [1, 1]          # the read's chunks: to the hello's port
    write(h, 5, [3], port=1)
    assert [m for _, m, _ in drain(h)] == [1]             # the answer too
    h.req(WRITE, [5, 0, 1, 0x10, 0], port=1)              # a malformed write
    assert [m for _, m, _ in drain(h)] == [1]
    pick(h, 28)
    assert [m for _, m, _ in drain(h)] == [1]             # the push
    h.req(HELLO, port=1)
    h.req(READ, port=0)                                   # in the same frame: the hello's port wins
    assert [m for _, m, _ in drain(h)] == [2, 2, 2]       # the reply, then the read's chunks
    pick(h, 29)
    assert [m for _, m, _ in drain(h)] == [2]             # pushes follow the new hello


def test_before_a_hello_chunks_go_to_the_requesters_port(pl21_image):
    h = fresh(pl21_image)
    h.req(READ, port=1)
    assert [m for _, m, _ in drain(h)] == [2, 2]
    write(h, 5, [3], port=0)
    assert [m for _, m, _ in drain(h)] == [1]


@pytest.mark.parametrize("msg", [bytes([0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7]),            # identity request
                                 bytes([0xF0, 0x00, 0x20, 0x29, 0x01, 0x64, 0x40, 0x00, 0x00, 0xF7])])
def test_other_sysex_reaches_stock(pl21_image, msg):
    """The harness stops at stock's dispatcher body (0x0801EB34): reaching it with the message unchanged is the check;
    what stock then sends is stock's (the identity reply is a flash constant)."""
    h = fresh(pl21_image)
    h.sysex(msg)
    assert h.forwarded == 1 and bytes(h.uc.mem_read(BUF, len(msg))) == msg
    assert h.frame() == []


@pytest.mark.parametrize("msg", [bytes([0xF0, 0x7D, 0x53, 0x4C]), bytes([0xF0, 0x7D, 0x53, 0x4C, 0x10]),
                                 bytes([0xF0, 0x7D, 0x53, 0x4C, 0x13, 0xF7]),
                                 bytes([0xF0, 0x7D, 0x53, 0x4C, 0x10, 0x00, 0xF7])])
def test_short_or_broken_messages_pass(pl21_image, msg):
    h = fresh(pl21_image)
    h.sysex(msg)
    assert h.forwarded == 1
    assert h.frame() == []


def test_the_build_refuses_link_with_voice_log(tmp_path):
    from playbuild import features, paths, symbols
    from playbuild.errors import BuildError
    p = tmp_path / "v.toml"
    p.write_text('marker = "SLX1"\nfeatures = ["chord", "countin", "saved", "link", "voice_log"]\n')
    with pytest.raises(BuildError, match="link cannot be built together with voice_log"):
        features.load_version(p, symbols.load(paths.SYMBOLS))


# ---- PL12: writes with the pads' effects (plan Task 4) ----

def write_msg(off, data):
    """A write's body: the offset in two bytes, the count, the bytes as nibbles (high first)."""
    return two(off) + [len(data)] + [n for b in data for n in (b >> 4, b & 0xF)]


def write(h, off, data, port=0):
    h.req(WRITE, write_msg(off, data), port)


def open_page(h, downs, t=0):
    h.track(t)
    h.press(t, shift=True)                       # the Chords page
    for _ in range(downs):
        h.press(DOWN)


def arp_entries(h, m):
    base = sym(m, "held")
    return [i for i in range(6) if h.r8(base + 14 * i) and h.r8(base + 14 * i + 9) & 0x10]


def latched_arp(h, m, t=1):
    h.track(t)
    put(h, m, "chord_arp", get(h, m, "chord_arp", 8)[:2 * t] + bytes([1 | 2 << 3 | 0x80, 5 << 2])
        + get(h, m, "chord_arp", 8)[2 * t + 2:])                 # up, 1/16, latch, legato: always a note
    pick(h, 24)
    h.heartbeat(300)
    assert arp_entries(h, m) and h.sounding


def test_a_write_sets_the_field_and_answers_with_a_state(pl21_image, pl21_manifest):
    h = fresh(pl21_image)
    h.hello()
    write(h, 5, [2 << 2])                        # track 1's strum: medium
    assert h.out == []
    off, b = answer(h)
    assert off == 0 and b[5] == 0x08
    assert get(h, pl21_manifest, "chord_strum", 1) == b"\x08"
    assert h.frame() == []                       # the write's answer was the push


@pytest.mark.parametrize("downs, pre, pad, off", [
    (0, (), 28, 5),           # strum medium
    (0, (), 31, 6),           # strum falling
    (1, (), 10, 8),           # arp rate 1/16
    (1, (1,), 15, 8),         # arp up, then latch on
    (1, (13,), 11, 8),        # dotted, then 1/32: the pad clears dotted, so does the phone's byte
    (6, (), 0, 7),            # Keys: mono (after Pattern tools 2 and Phrasing, PL14)
    (6, (), 1, 115),          # Keys: step-entry chords (PL18)
    (2, (), 4, 25),           # Pattern tools: 5 hits
    (2, (), 20, 26),          # Pattern tools: gate one sixth down
], ids=["strum", "falling", "rate", "latch", "rate-1/32", "mono", "step-chords", "hits", "euclid-gate"])
def test_a_write_shows_on_the_play_page_as_the_pad_does(pl21_image, pl21_manifest, downs, pre, pad, off):
    m = pl21_manifest
    a, b = fresh(pl21_image), fresh(pl21_image)
    for h in (a, b):
        open_page(h, downs)
        for p in pre:
            pick(h, p)
    pick(a, pad)
    b.hello()
    write(b, off, settings(a, m)[off:off + 1])  # the byte the pads made: the phone encodes as they do
    b.frame()
    assert settings(b, m) == settings(a, m)
    assert b.leds() == a.leds()


def test_count_in_from_the_phone_as_shift_clear(pl21_image, pl21_manifest):
    a, b = fresh(pl21_image), fresh(pl21_image)
    set_count_in(a, 2)                           # count-in on, no click
    b.hello()
    write(b, 24, [1])
    b.frame()
    assert get(b, pl21_manifest, "ci_on", 1) == b"\x01"
    for h in (a, b):
        h.shift(True)
    assert b.leds()[55] == a.leds()[55]


@pytest.mark.parametrize("msg", [
    write_msg(0, [0x60 | 1]),                   # spread 3
    write_msg(8, [1 | 3 << 3 | 2 << 5]),        # dotted at 1/32
    write_msg(8, [1 | 3 << 5]),                 # arp modifier 3
    write_msg(9, [6 << 2]),                     # arp gate 6
    write_msg(9, [0x20 | 2 << 2]),              # arp [1] bit 5
    write_msg(25, [0x60 | 1]),                  # Euclid velocity 3
    write_msg(25, [0x20 | 17]),                 # 17 hits
    write_msg(26, [7 << 5]),                    # Euclid gate 7 (6 = "to the next hit" is valid since PL13)
    write_msg(24, [2]),                         # count-in 2
    write_msg(4, [0x01]),                       # rootless without bass
    write_msg(7, [0x10]),                       # mono bit 4
    write_msg(115, [0x10]),                     # step-entry chords bit 4
    write_msg(37, [0x30]),                      # melody_cfg: range - 1 = 3
    write_msg(38, [0x20]),                      # melody_cfg cfg1 bit 5
    write_msg(40, [0xE0 | 3]),                  # cfg1 bits 5-7 on track 1
    write_msg(45, [0]),                         # melody_seed: saved, not linked
    write_msg(16, [0]),                         # the retired page_last
    write_msg(20, [0]),                         # page_quick
    write_msg(33, [1]),                         # page_slot
    write_msg(23, [0, 1]),                      # straddles page_quick and the count-in
    write_msg(LEN - 1, [0, 0]),                 # past the payload
    [5, 0, 0],                                  # count 0
    [0, 0, 9] + [0] * 18,                       # count 9
    write_msg(5, [4])[:-1],                     # one nibble short
    [5, 0, 1, 0x10, 0],                         # a nibble above 0x0F
    [5, 1, 0],                                  # the protocol-1 form (one-byte offset): count 0 here
], ids=["spread3", "dotted1/32", "mod3", "gate6", "a1bit5", "vel3", "hits17", "egate7", "ci2", "rootless", "mono4", "step4",
        "mrange3", "mc1bit5", "mc1bits", "mseed", "tomb", "pquick", "pslot", "straddle", "past", "count0", "count9", "short", "nibble",
        "proto1"])
def test_invalid_writes_change_nothing(pl21_image, pl21_manifest, msg):
    h = fresh(pl21_image)
    open_page(h, 0)
    h.hello()
    before, leds = settings(h, pl21_manifest), h.leds()
    h.req(WRITE, msg)
    assert h.forwarded == 0
    sent = drain(h)
    assert len(sent) == 1
    off, b = chunk_of(sent[0])
    assert b == linked(before)[off:off + len(b)]
    assert settings(h, pl21_manifest) == before and h.leds() == leds


def test_bass_rootless_is_one_write_over_two_fields(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = fresh(pl21_image)
    put(h, m, "chord_settings", [1, 0, 0, 0])   # a triad, no bass
    h.hello()
    write(h, 0, [1 | 0x80, 0, 0, 0, 0x01])      # rootless over bass in one message
    h.frame()
    assert get(h, m, "chord_settings", 4) == bytes([0x81, 0, 0, 0]) and get(h, m, "chord_rootless", 1) == b"\x01"


def test_step_chords_write(pl21_image, pl21_manifest):
    """PL18: chord_step is linked, bit t = track t; bits 4-7 are refused."""
    m = pl21_manifest
    h = fresh(pl21_image)
    h.hello()
    write(h, 115, [0x10])
    h.frame()
    assert get(h, m, "chord_step", 1) == b"\x00"
    write(h, 115, [0x0A])
    h.frame()
    assert get(h, m, "chord_step", 1) == b"\x0a"


def test_pattern_strum_write(pl21_image, pl21_manifest):
    """PL19: chord_pstrum is linked, 2 bits a track; a field at 3 is refused."""
    m = pl21_manifest
    h = fresh(pl21_image)
    h.hello()
    write(h, 116, [0x30])
    h.frame()
    assert get(h, m, "chord_pstrum", 1) == b"\x00"
    write(h, 116, [0x21])
    h.frame()
    assert get(h, m, "chord_pstrum", 1) == b"\x21"


def test_a_strum_write_keeps_a_latched_arpeggio(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = fresh(pl21_image)
    latched_arp(h, m, 1)
    h.hello()
    write(h, 5, [3 << 2])                        # track 1's strum
    h.frame()
    h.heartbeat(300)
    assert arp_entries(h, m) and h.sounding     # a project load here frees it (test_saved), a phone write does not


def test_pattern_off_from_the_phone_frees_the_arpeggio(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = fresh(pl21_image)
    latched_arp(h, m, 1)
    h.hello()
    write(h, 10, [2 << 3 | 0x80])                # pattern off, latch kept
    h.frame()
    h.heartbeat(300)
    assert arp_entries(h, m) == [] and h.sounding == set()


def test_latch_off_from_the_phone_frees_latched_notes(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = fresh(pl21_image)
    latched_arp(h, m, 1)
    h.hello()
    write(h, 10, [1 | 2 << 3])                   # latch off, pattern kept
    h.frame()
    h.heartbeat(300)
    assert arp_entries(h, m) == [] and h.sounding == set()


RECORD = 0x2003D71C + 0x14
PATTERN0, PATTERN_SIZE, SETTINGS = 0x2E4, 0xCA8, 0x380   # track 0's patterns in the record; [0] last, [1] first step


def test_a_euclid_write_disarms_write_and_reduces_rotation(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = fresh(pl21_image)
    h.uc.mem_write(h.r32(RECORD) + PATTERN0 + SETTINGS, bytes([11, 0]))   # pattern 0: steps 1-12
    open_page(h, 2)
    pick(h, 4)                                   # 5 hits
    pick(h, 31)                                  # Write armed (blinks)
    assert h.leds()[31] == 0x47
    h.hello()
    c0 = get(h, m, "euclid_cfg", 1)[0]
    write(h, 25, [c0, 20 | 2 << 5])              # rotation 20, gate 3/6
    h.frame()
    assert get(h, m, "euclid_cfg", 2)[1] == 8 | 2 << 5   # 20 mod 12
    assert h.leds()[31] != 0x47


def test_a_melody_write_disarms_write(pl21_image, pl21_manifest):
    h = fresh(pl21_image)
    open_page(h, 2)
    pick(h, 4)                                   # 5 hits
    pick(h, 31)                                  # Write armed (blinks)
    assert h.leds()[31] == 0x47
    h.hello()
    write(h, 37, [0x02])                         # melody_cfg track 0: order down
    h.frame()
    assert get(h, pl21_manifest, "melody_cfg", 1) == b"\x02"
    assert h.leds()[31] != 0x47


def test_a_second_write_before_the_frame_is_dropped(pl21_image, pl21_manifest):
    h = fresh(pl21_image)
    h.hello()
    write(h, 5, [1])
    write(h, 5, [3])
    off, b = answer(h)                           # the second is answered with the first's chunk
    assert off == 0 and b[5] == 1
    assert get(h, pl21_manifest, "chord_strum", 1) == b"\x01"


def test_a_load_and_a_write_in_one_frame(pl21_image, pl21_manifest):
    """One answer chunk, then the load's other changed chunks."""
    h = fresh(pl21_image)
    h.hello()
    write(h, 5, [0x3F])
    write_tail(h, make_tail(DISTINCT))
    load(h)
    sent = drain(h)
    want = DISTINCT[:5] + b"\x3F" + DISTINCT[6:]
    assert [chunk_of(s)[0] for s in sent] == [0, CHUNK] and assemble(sent) == linked(want)
    assert settings(h, pl21_manifest) == want


def test_a_strum_write_while_a_chord_is_held_leaves_nothing_on(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = fresh(pl21_image)
    h.track(0)
    put(h, m, "chord_settings", [1, 0, 0, 0])
    put(h, m, "chord_strum", [1])                # slow
    h.hello()
    h.down(24)
    h.heartbeat(20)
    write(h, 5, [3])                             # fast, mid-strum
    h.frame()
    h.heartbeat(300)
    h.up(24)
    h.heartbeat(300)
    assert h.sounding == set(), sorted(h.sounding)


def test_a_euclid_gate_write_keeps_the_rotation_as_the_gate_pad_does(pl21_image, pl21_manifest):
    """Final review: a rotation left above a shortened pattern's length stays as stored when only the gate changes,
    as the gate pad leaves it (the rhythm uses r % n either way; it differs once the pattern grows back)."""
    m = pl21_manifest
    a, b = fresh(pl21_image), fresh(pl21_image)
    for h in (a, b):
        put(h, m, "euclid_cfg", bytes([0x25, 10 | 2 << 5]) + get(h, m, "euclid_cfg", 8)[2:])   # 5 hits, rotation 10
        h.uc.mem_write(h.r32(RECORD) + PATTERN0 + SETTINGS, bytes([7, 0]))              # pattern 0: 8 steps
        open_page(h, 2)
    pick(a, 20)                                  # the gate pad: one sixth down
    b.hello()
    write(b, 26, settings(a, m)[26:27])
    b.frame()
    assert get(b, m, "euclid_cfg", 2) == get(a, m, "euclid_cfg", 2) == bytes([0x25, 10 | 1 << 5])


def test_euclid_groove_bit_and_gate_to_the_next_hit_are_valid_writes(pl21_image, pl21_manifest):
    """PL13: euclid_cfg bit 7 (groove) and gate value 6 (to the next hit) are settings the pads make."""
    h = fresh(pl21_image)
    h.hello()
    write(h, 25, [0x80 | 0x20 | 5])
    h.frame()
    write(h, 26, [6 << 5 | 3])
    h.frame()
    assert settings(h, pl21_manifest)[25:27] == bytes([0xA5, 0xC3])


def test_link_accepts_the_new_values_and_refuses_bad_ones(pl21_image, pl21_manifest):
    """PL13: euclid_cfg bit 7 with gate 6 is accepted; a melody_cfg with range - 1 = 3 or cfg1 bits 5-7 is refused;
    melody_seed is saved but not in the hello's linked fields."""
    m = pl21_manifest
    h = fresh(pl21_image)
    h.hello()
    write(h, 25, [0x80 | 5])
    h.frame()
    write(h, 26, [6 << 5])
    h.frame()
    assert settings(h, m)[25:27] == bytes([0x85, 0xC0])
    write(h, 37, [0x10 | 2])                         # melody_cfg track 0: order up-down, range 2
    h.frame()
    write(h, 38, [3 | 3 << 3])
    h.frame()
    assert get(h, m, "melody_cfg", 2) == bytes([0x12, 0x1B])
    before = settings(h, m)
    for off, byte in ((37, 0x30), (38, 0x20), (38, 0x80), (41, 0xC0 | 0x30)):
        write(h, off, [byte])
        assert unchanged(h, before) and settings(h, m) == before, (off, byte)
    write(h, 45, [0x33])                             # melody_seed: a result, not a setting
    h.frame()
    assert settings(h, m) == before


def test_a_load_clears_what_the_pads_never_set_so_phone_writes_go_through(pl21_image, pl21_manifest):
    """PL12 review: a project holding rootless on a track without bass, or arp modifier 3, refused every phone write to
    that track's settings or arp byte. PL14's load clears both (neither changes what plays)."""
    m = pl21_manifest
    h = fresh(pl21_image)
    payload = bytearray(DISTINCT)
    payload[4] |= 0x02                          # rootless on track 1, whose bass is off (0x2B)
    payload[12] |= 3 << 5                       # track 2's arp byte: modifier 3
    write_tail(h, make_tail(bytes(payload)))
    load(h)
    h.leds()
    assert get(h, m, "chord_rootless", 1) == bytes([DISTINCT[4]])          # tracks 0 and 2 have bass: kept
    assert get(h, m, "chord_arp", 8)[4] == payload[12] & ~0x60 == 0x06
    h.hello()
    write(h, 1, [0x2C])                         # track 1: another shape, bass still off
    h.frame()
    write(h, 12, [0x0E])                        # track 2: another rate
    h.frame()
    assert get(h, m, "chord_settings", 4)[1] == 0x2C and get(h, m, "chord_arp", 8)[4] == 0x0E


# ---- PL14: the new fields over the link ----

def test_every_message_fits_stocks_sysex_output(pl21_image, pl21_manifest):
    """saved2: the hello reply and the state's chunks (a write's answer is a chunk too) go to stock's SysEx output from
    the UI task, and stock's output takes each (its own checks: F0 ... F7, data bytes below 0x80, length below 0x169).
    A full chunk is 140 B whatever the payload grows to."""
    h = fresh(pl21_image)
    put_settings(h, pl21_manifest, DISTINCT)
    sent = h.hello()
    h.req(READ)
    chunks = drain(h)
    write(h, 130, [0])                               # past the payload: answered with the last chunk
    sent += chunks + [h.frame()[0]]
    img = linked(DISTINCT)
    want = bytes([0xF0, 0x7D, 0x53, 0x4C, 0x51, 0x01, LEN, 0, 0, 0, CHUNK])
    assert chunks[0][2] == want + bytes(n for b in img[:CHUNK] for n in (b >> 4, b & 0xF)) + b"\xF7"
    assert len(chunks[0][2]) == 140 and len(chunks[1][2]) == 12 + 2 * (LEN - CHUNK)
    assert img[53:69] == DISTINCT[53:69] and img[69:77] == bytes(8)   # page_sub and euclid_last are not linked
    assert img[77:83] == DISTINCT[77:83] and img[83:87] == bytes(4)   # chord_voice and repeat_cfg are linked, drum_page is not
    assert img[87:111] == DISTINCT[87:111] and img[111:115] == bytes(4) and img[115:117] == DISTINCT[115:117] and img[117] == 0   # PL20: trig_mark is saved, not linked; PL18: chord_step is linked; PL17: the drums' Euclid, rhythm and accent are linked, drum_seed is not
    for router, mask, data in sent:
        assert (router, mask) == (h.r32(ROUTER_PTR), 1) and len(data) < 0x169
    for data in {data for _, _, data in sent}:
        assert stock_takes(pl21_image, data), data.hex()


def stock_takes(img, data):
    """Runs stock's SysEx output 0x08020C90 on `data` (no capture): 1 when it gets past its checks to the copy
    (0x08020D46), 0 when it returns 1 from a refusal (0x08020D08)."""
    import struct
    from unicorn import UC_HOOK_CODE
    from sysex import BUF, MSG, SYSEX_OUT
    h = NoteHarness(img)
    got = []

    def stop(u, a, size, d):
        got.append(a)
        u.emu_stop()

    for at in (0x08020D46, 0x08020D08):
        h.uc.hook_add(UC_HOOK_CODE, stop, begin=at, end=at)
    h.uc.mem_write(BUF, data)
    h.uc.mem_write(MSG, struct.pack("<II", BUF, len(data)))
    try:
        h.call(SYSEX_OUT, h.r32(ROUTER_PTR), 1, MSG)
    except AssertionError:
        pass                                      # stopped inside, on purpose
    assert got, "stock's SysEx output reached neither its copy nor a refusal"
    return got[0] == 0x08020D46


def test_vary_writes_valid_and_invalid(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = fresh(pl21_image)
    h.hello()
    write(h, 53, [0xA5, 0x63, 0x04])             # track 0: 5 second hits, accent; rotation 3, thinning 3; cycle 7
    h.frame()
    write(h, 65, [0x0F, 0x06])                   # melody_vary tracks 0-1
    h.frame()
    assert get(h, m, "rhythm_cfg", 3) == bytes([0xA5, 0x63, 0x04]) and get(h, m, "melody_vary", 2) == b"\x0F\x06"
    before = settings(h, m)
    for off, data in ((53, [0xC0 | 4]),           # combine 6
                      (53, [0xE0]),               # combine 7
                      (53, [17]),                 # 17 second hits
                      (54, [0x80]),               # rhythm_cfg [1] bit 7
                      (55, [5]),                  # cycle 5
                      (58, [0x08 | 1]),           # track 1's [2]: bits 3-7
                      (65, [0x10]),               # melody_vary bit 4
                      (68, [0x80 | 3]),           # track 3: bit 7
                      (69, [1]),                  # page_sub: saved, not linked
                      (73, [60]),                 # euclid_last: saved, not linked
                      (64, [0x00, 0x10])):        # straddles rhythm_cfg and melody_vary: one bad byte refuses both
        write(h, off, data)
        assert unchanged(h, before) and settings(h, m) == before, (off, data)
    write(h, 56, [0x30, 0x7F, 0x03])             # track 1: 16 hits, both; rotation 31, thinning 3; cycle 6
    h.frame()
    assert get(h, m, "rhythm_cfg", 6)[3:] == bytes([0x30, 0x60 | 31 % 16, 0x03])   # the rotation below the 16 steps


def test_a_vary_write_disarms_write_and_reduces_the_second_rotation(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = fresh(pl21_image)
    h.uc.mem_write(h.r32(RECORD) + PATTERN0 + SETTINGS, bytes([11, 0]))   # pattern 0: steps 1-12
    open_page(h, 2)
    pick(h, 4)                                   # 5 hits
    pick(h, 31)                                  # Write armed (blinks)
    assert h.leds()[31] == 0x47
    h.hello()
    write(h, 54, [0x20 | 20])                    # track 0: second rotation 20, thinning 1
    h.frame()
    assert get(h, m, "rhythm_cfg", 3)[1] == 0x20 | 8   # 20 mod 12
    assert h.leds()[31] != 0x47
    pick(h, 31)                                  # armed again
    assert h.leds()[31] == 0x47
    write(h, 65, [0x04])                         # melody_vary: jumps 1/4
    h.frame()
    assert h.leds()[31] != 0x47
    put(h, m, "rhythm_cfg", get(h, m, "rhythm_cfg", 1) + bytes([20]) + get(h, m, "rhythm_cfg", 12)[2:])   # a stale rotation
    write(h, 54, [0x40 | 20])                    # thinning only: the stored rotation stays (as euclid's gate write)
    h.frame()
    assert get(h, m, "rhythm_cfg", 3)[1] == 0x40 | 20


# ---- PL15: chord_voice over the link ----

def test_chord_voice_writes(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = fresh(pl21_image)
    h.hello()
    put(h, m, "chord_settings", [0, 0, 0, 0])
    write(h, 77, [0x34, 0x30, 0x05, 0x25])           # row-2 shape 4 with bottom line; lead only; shape 5; shape 5 + top line
    h.frame()
    assert get(h, m, "chord_voice", 4) == bytes([0x34, 0x30, 0x05, 0x25])
    before = settings(h, m)
    for off, data in ((77, [0x06]), (78, [0x0F]), (79, [0x40]), (80, [0x80 | 1]), (77, [0x05, 0xC1])):
        write(h, off, data)
        assert unchanged(h, before) and settings(h, m) == before, (off, data)


def test_a_row1_shape_write_clears_row2(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = fresh(pl21_image)
    h.hello()
    put(h, m, "chord_voice", [0x23, 0x14, 0x05, 0x31])    # row-2 shapes 3, 4, 5, 1 and their voice leading
    put(h, m, "chord_settings", [0, 0, 0, 0])
    write(h, 0, [1, 0, 2, 0])                   # tracks 0 and 2 get a row-1 shape
    h.frame()
    assert get(h, m, "chord_voice", 4) == bytes([0x20, 0x14, 0x00, 0x31])    # bits 0-3 cleared there, lead kept
    assert get(h, m, "chord_settings", 4) == bytes([1, 0, 2, 0])
    write(h, 0, [3, 0, 0, 0])                   # a row-1 shape to another row-1 shape: nothing more to clear
    h.frame()
    write(h, 1, [0x10])                         # track 1: an inversion write, shape still 0
    h.frame()
    assert get(h, m, "chord_voice", 4)[1] == 0x04    # the row-2 shape stays; the inversion ends voice leading


def test_a_row2_write_sets_the_row1_shape_to_single(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = fresh(pl21_image)
    h.hello()
    put(h, m, "chord_settings", [0x0B, 0x0A, 0, 0])     # track 0: shape 3, inversion 1; track 1: shape 2, inversion 1
    write(h, 77, [0x02])                        # track 0 to a row-2 shape
    h.frame()
    assert get(h, m, "chord_voice", 4) == bytes([0x02, 0, 0, 0])
    assert get(h, m, "chord_settings", 4) == bytes([0x08, 0x0A, 0, 0])   # shape bits 0, the rest kept


def test_an_inversion_write_keeps_row2(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = fresh(pl21_image)
    h.hello()
    put(h, m, "chord_voice", [0x03, 0, 0, 0])
    write(h, 0, [0x10])                         # inversion 2, shape still 0
    h.frame()
    assert get(h, m, "chord_voice", 4) == bytes([0x03, 0, 0, 0]) and get(h, m, "chord_settings", 4)[0] == 0x10


def test_an_inversion_write_ends_voice_leading(pl21_image, pl21_manifest):
    """As the inversion pads (page.c pick_chords): a write that changes a track's inversion turns its voice leading off,
    so CTCtrl's inversion edit is heard; a shape, spread or bass write leaves voice leading."""
    m = pl21_manifest
    h = fresh(pl21_image)
    h.hello()
    put(h, m, "chord_settings", [0x02, 0x00, 0x02, 0x82])    # 7th; off (a row-2 shape); 7th; 7th over a bass
    put(h, m, "chord_voice", [0x10, 0x23, 0x30, 0x10])        # close; row-2 shape 3 + top line; bottom line; close
    h.frame()
    write(h, 0, [0x02 | 1 << 3, 2 << 3, 0x02 | 1 << 5, 0x83])  # inversion 1; inversion 2; spread 1; shape 3, bass kept
    h.frame()
    assert get(h, m, "chord_settings", 4) == bytes([0x0A, 0x10, 0x22, 0x83])
    assert get(h, m, "chord_voice", 4) == bytes([0x00, 0x03, 0x30, 0x10])
    write(h, 2, [0xA2])                                        # track 2: bass on
    h.frame()
    assert get(h, m, "chord_voice", 4) == bytes([0x00, 0x03, 0x30, 0x10])
    write(h, 77, [0x10])                                       # voice leading back on: the inversion stays
    h.frame()
    assert get(h, m, "chord_voice", 4)[0] == 0x10 and get(h, m, "chord_settings", 4)[0] == 0x0A


def test_an_inversion_and_voice_leading_changed_together_keep_voice_leading(pl21_image, pl21_manifest):
    """chord_link_apply's rule for a change that sets both: voice leading as written. One write cannot carry both today
    (chord_settings and chord_voice are not adjacent, and a write over bytes 16-23, not linked, is refused), so the
    test calls chord_link_apply with the old image as link_on_leds does."""
    m = pl21_manifest
    h = fresh(pl21_image)
    h.hello()
    h.req(READ)
    old = bytearray(assemble(drain(h)))
    old[0:4], old[77:81] = bytes([0x02, 0x02, 0, 0]), bytes([0x10, 0x10, 0, 0])
    put(h, m, "chord_settings", [0x0A, 0x0A, 0, 0])           # both tracks: inversion 0 -> 1
    put(h, m, "chord_voice", [0x20, 0x10, 0, 0])              # track 0: close -> top line; track 1 unchanged
    h.uc.mem_write(OUTBUF, bytes(old))
    h.call(sym(m, "chord_link_apply"), OUTBUF)
    assert get(h, m, "chord_voice", 4) == bytes([0x20, 0x00, 0, 0])
    assert get(h, m, "chord_settings", 4) == bytes([0x0A, 0x0A, 0, 0])


@pytest.mark.parametrize("index, shape, row2", [(0, 0, 0), (3, 3, 0), (9, 0, 2), (8, 0, 1), (12, 0, 5)])
def test_chord_pick_shape_sets_one_row_and_clears_the_other(pl21_image, pl21_manifest, index, shape, row2):
    """chord_pick_shape (Task 5's pads call it): any row-1 index, 0 (off) included, clears the row-2 shape; a row-2 index
    sets it and the row-1 shape to single. Voice leading and the other settings bits stay."""
    m = pl21_manifest
    h = NoteHarness(pl21_image)
    h.leds()
    put(h, m, "chord_settings", [0xFB, 0, 0, 0])          # shape 3, inversion 3, spread 3 bits, bass
    put(h, m, "chord_voice", [0x23, 0x11, 0, 0])          # track 0: row-2 shape 3, top line
    h.call(sym(m, "chord_pick_shape"), 0, index)
    assert get(h, m, "chord_settings", 4)[0] == (0xFB & ~7) | shape
    assert get(h, m, "chord_voice", 4) == bytes([0x20 | row2, 0x11, 0, 0])


# ---- PL16: repeat_cfg over the link ----

def test_repeat_writes(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = fresh(pl21_image)
    h.hello()
    write(h, 81, [0xF6, 0x00])                       # rate 6, accent, latch, unquantized
    h.frame()
    assert get(h, m, "repeat_cfg", 2) == bytes([0xF6, 0x00])
    write(h, 81, [0x58])                             # the rate alone, 8: kept
    h.frame()
    assert get(h, m, "repeat_cfg", 2) == bytes([0x58, 0x00])
    before = settings(h, m)
    for off, data in ((81, [0x09]), (81, [0x4F]), (82, [0x01]), (81, [0x05, 0x80])):
        write(h, off, data)
        assert unchanged(h, before) and settings(h, m) == before, (off, data)


class DrumLink(DrumHarness, PL12):
    """The drums' harness (tests/drums.py) with the link's requests and frames."""


@pytest.mark.parametrize("data", [[0x03], [0x40]], ids=["latch off", "no rate"])
def test_repeat_write_stops_latched_drums(pl21_image, pl21_manifest, data):
    """A write that turns latch off or takes the rate to 0 stops the latched drums, as the pads do (chord_link_apply;
    final review 1 / 5)."""
    m = pl21_manifest
    h = DrumLink(pl21_image, m)
    drum_setup(h)
    h.hello()
    write(h, 81, [0x43])                             # 1/16, latch
    h.frame()
    assert get(h, m, "repeat_cfg", 1) == bytes([0x43])
    h.down(DRUM_PAD)
    h.up(DRUM_PAD)
    h.heartbeat(100)
    assert len(h.ons(1)) >= 2 and h.r8(sym(m, "rep_latched")) == 1
    write(h, 81, data)
    h.frame()
    assert get(h, m, "repeat_cfg", 1) == bytes(data) and h.r8(sym(m, "rep_latched")) == 0
    h.heartbeat(1)
    assert h.sent[-1][2:4] == ("off", 1)
    gone = len(h.sent)
    h.heartbeat(200)
    assert h.sent[gone:] == []


# ---- PL17: the drums' Pattern tools settings over the link ----

DRUM_POS = 0x14                                  # drum recorder + 0x14: the position store (param 0 = the shown pattern)


def drum_pattern(h, d=0):
    """Drum d's shown pattern: base + 0x6A8 * the position store's pattern."""
    from notes import param
    rec = h.r32(0x2003C174 + 4 * (4 + d))
    return h.r32(rec + 0x48) + 0x6A8 * (param(h, h.r32(rec + DRUM_POS), 0) & 7)


def test_drum_tools_writes(pl21_image, pl21_manifest):
    m = pl21_manifest
    h = fresh(pl21_image)
    h.uc.mem_write(drum_pattern(h) + 0x80, bytes([15, 0]))             # drum 1's shown pattern: 16 steps
    h.hello()
    write(h, 87, [0x4F, 0x21])                       # hits 15, velocity hard; rotation 1, two hits
    h.frame()
    write(h, 95, [0xA5, 0x23, 0x01])                 # drum 1's second rhythm: 5 hits, accent; rotation 3, thinning 1; cycle 3
    h.frame()
    write(h, 107, [0x03])                            # accent every 3rd
    h.frame()
    assert get(h, m, "drum_euclid", 2) == bytes([0x4F, 0x21]) and get(h, m, "drum_rhythm", 3) == bytes([0xA5, 0x23, 0x01])
    assert get(h, m, "drum_accent", 1) == b"\x03"
    before = settings(h, m)
    for off, data in ((87, [0x11]),                  # 17 hits
                      (87, [0x63]),                  # velocity 3
                      (88, [3 << 5]),                # roll 3
                      (95, [0xC0 | 4]),              # combine 6
                      (97, [5]),                     # cycle 5
                      (107, [4]),                    # accent bit 2
                      (111, [7]),                    # drum_seed: saved, not linked
                      (86, [0x08, 0x10])):           # straddles drum_page (not linked) and drum_euclid
        write(h, off, data)
        assert unchanged(h, before) and settings(h, m) == before, (off, data)
    write(h, 88, [20])                               # rotation 20 on 16 steps: kept as 4
    h.frame()
    assert get(h, m, "drum_euclid", 2)[1] == 4
    write(h, 96, [0x40 | 20])                        # second rotation 20, thinning 2
    h.frame()
    assert get(h, m, "drum_rhythm", 3)[1] == 0x40 | 4


def test_a_drum_rotation_is_kept_below_the_shown_patterns_length(pl21_image, pl21_manifest):
    """drum_target: a 12-step shown pattern keeps rotation 20 as 8; with the recorder's vtable corrupted there is no
    target and the link falls back to 16 steps (20 -> 4)."""
    m = pl21_manifest
    for corrupt, want in ((False, 8), (True, 4)):
        h = fresh(pl21_image)
        h.uc.mem_write(drum_pattern(h) + 0x80, bytes([11, 0]))          # steps 1-12
        if corrupt:
            h.uc.mem_write(h.r32(0x2003C174 + 4 * 4), bytes(4))
        h.hello()
        write(h, 88, [20])
        h.frame()
        assert get(h, m, "drum_euclid", 2)[1] == want, corrupt


# ---- saved2: link protocol 2's queue: every write answered first, one message a frame ----

KEYS = 6                                         # Octave down presses from the Chords page to Keys


def test_a_write_is_answered_first(pl21_image, pl21_manifest):
    """A write at offset 5 (chunk 0) and a pad press changing chunk 1 before the same frame: the answer goes first,
    the push next."""
    m = pl21_manifest
    h = fresh(pl21_image)
    open_page(h, KEYS)
    h.hello()
    write(h, 5, [2 << 2])                        # track 1's strum: medium
    pick(h, 1)                                   # Keys: step-entry chords on track 0 (offset 115)
    off, b = answer(h)
    assert off == 0 and b[5] == 0x08
    off, b = answer(h)
    assert off == CHUNK and b[115 - CHUNK] == get(h, m, "chord_step", 1)[0] != 0
    assert h.frame() == []


def _refused(h, m):
    return write_msg(0, [0x60 | 1]), 0           # spread 3


def _not_linked(h, m):
    return write_msg(111, [7]), 1                # drum_seed: saved, not linked


def _current(h, m):
    return write_msg(116, settings(h, m)[116:117]), 1    # chord_pstrum as it is


def _fixed_up(h, m):
    h.uc.mem_write(drum_pattern(h) + 0x80, bytes([11, 0]))          # drum 1's shown pattern: 12 steps
    put(h, m, "drum_euclid", get(h, m, "drum_euclid", 1) + bytes([8]))   # rotation 8
    return write_msg(88, [20]), 1                # rotation 20 on 12 steps: kept as 8, the byte it was


def _malformed(h, m):
    return [5, 0, 1, 0x10, 0], 0                 # a nibble above 0x0F: answered with chunk 0


@pytest.mark.parametrize("case", [_refused, _not_linked, _current, _fixed_up, _malformed],
                         ids=["refused", "not-linked", "current", "fixed-up", "malformed"])
def test_every_write_is_answered(pl21_image, pl21_manifest, case):
    """Review focus: a write the device refuses or that changes nothing gets one chunk, the one its range touches,
    holding the unchanged bytes, and nothing else follows."""
    m = pl21_manifest
    h = fresh(pl21_image)
    msg, k = case(h, m)
    h.hello()
    before = settings(h, m)
    h.req(WRITE, msg)
    sent = drain(h)
    assert len(sent) == 1
    off, b = chunk_of(sent[0])
    assert off == k * CHUNK and b == linked(before)[off:off + len(b)]
    assert settings(h, m) == before


def test_a_write_past_offset_127(pl21_image, pl21_manifest):
    """The two-byte offset: 130 lies past the 118 B payload, so the write is refused and answered with the last chunk.
    Read as its low 7 bits (2) it would set track 2's chord settings and be answered with chunk 0."""
    m = pl21_manifest
    h = fresh(pl21_image)
    put_settings(h, m, DISTINCT)
    h.hello()
    assert DISTINCT[2] != 0
    write(h, 130, [0])
    sent = drain(h)
    assert len(sent) == 1
    off, b = chunk_of(sent[0])
    assert off == CHUNK and b == linked(DISTINCT)[CHUNK:]
    assert settings(h, m) == DISTINCT


def test_a_read_and_a_press_together(pl21_image, pl21_manifest):
    """Review focus: a read sends its chunks one a frame; a press that changes chunk 0 after chunk 0 went sends it
    again, so the last copies of every chunk are the final image."""
    m = pl21_manifest
    h = fresh(pl21_image)
    open_page(h, 0)                              # the Chords page
    h.hello()
    h.req(READ)
    first = h.frame()
    assert [chunk_of(s)[0] for s in first] == [0]
    pick(h, 28)                                  # strum medium: offset 5, chunk 0
    rest = drain(h)
    assert [chunk_of(s)[0] for s in rest] == [0, CHUNK]
    assert chunk_of(first[0])[1][5] != chunk_of(rest[0])[1][5] == 2
    assert assemble(first + rest) == linked(settings(h, m))
