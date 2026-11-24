"""PL03D voice log: the records (spec 2026-10-13-voice-log-design.md, sections 1-2)."""
import struct

import pytest

from voices import THRESHOLD, VoiceHarness

pytestmark = pytest.mark.emu
CAP, REC = 12, struct.Struct("<HBBBBHH")


def sym(man, name):
    return int(man["symbols"][name], 16)


def records(h, man):
    """The stored records, oldest first, as dicts."""
    head, stored = h.r8(sym(man, "vl_head")), h.r8(sym(man, "vl_stored"))
    base = sym(man, "vl_ring")
    out = []
    for i in range(stored):
        k = (head + CAP - stored + i) % CAP
        t, seq, flags, note, voice, before, headroom = REC.unpack(bytes(h.uc.mem_read(base + 10 * k, 10)))
        out.append(dict(t=t, seq=seq, synth=flags & 1, dsp=(flags >> 1) & 1, mode=(flags >> 2) & 7, note=note,
                        voice=voice, before=before, headroom=headroom))
    return out


def test_budget_and_lock_rule(vlog_manifest):
    assert vlog_manifest["ram"]["used"] <= 240
    assert set(vlog_manifest["hook_stack"]) >= {"voice_headroom", "voice_picked", "main_ms"}


def test_one_pad_note_one_record_on_the_arm_path(vlog_image, vlog_manifest):
    h = VoiceHarness(vlog_image)
    h.set_headroom(0x20000)
    h.track(0)
    h.take()
    h.down(24, 100)
    note = h.take("synth_on")[0][2]
    r = records(h, vlog_manifest)
    assert len(r) == 1
    assert (r[0]["synth"], r[0]["dsp"], r[0]["note"], r[0]["voice"]) == (0, 0, note, h.state(5))
    assert r[0]["headroom"] == 0x20000 >> 4
    assert r[0]["before"] == 0                                    # nothing sounding before the first note
    assert r[0]["mode"] == h.state(7)


def test_dsp_path_takes_a_held_voice(vlog_image, vlog_manifest):
    h = VoiceHarness(vlog_image)
    h.set_headroom(0x20000)
    h.track(0)
    h.down(24, 100)                                               # voice A, held
    held = h.state(5)
    h.set_headroom(THRESHOLD - 0x10)
    h.set_dsp_voice(held)
    h.down(26, 100)
    r = records(h, vlog_manifest)[-1]
    assert (r["dsp"], r["voice"]) == (1, held)
    assert (r["before"] >> (2 * held)) & 3 == 2                  # it was held: stolen
    assert r["headroom"] == (THRESHOLD - 0x10) >> 4


def test_synth_2_records_its_own_voices(vlog_image, vlog_manifest):
    h = VoiceHarness(vlog_image)
    h.set_headroom(0x20000)
    h.track(1)
    h.down(24, 100)
    r = records(h, vlog_manifest)[-1]
    assert r["synth"] == 1 and 6 <= r["voice"] <= 11 and r["before"] == 0


def test_reading_saturates(vlog_image, vlog_manifest):
    h = VoiceHarness(vlog_image)
    h.set_headroom(0xFFFFFF)
    h.track(0)
    h.down(24, 100)
    assert records(h, vlog_manifest)[-1]["headroom"] == 0xFFFF


def test_ring_keeps_the_last_12_and_seq_counts_on(vlog_image, vlog_manifest):
    h = VoiceHarness(vlog_image)
    h.set_headroom(0x20000)
    h.track(0)
    for k in range(15):
        pad = 16 + k % 16
        h.down(pad, 100)
        h.up(pad)
    r = records(h, vlog_manifest)
    assert len(r) == CAP and [x["seq"] for x in r] == list(range(3, 15))


def test_time_comes_from_the_heartbeat(vlog_image, vlog_manifest):
    h = VoiceHarness(vlog_image)
    h.set_headroom(0x20000)
    h.track(0)
    h.down(24, 100)
    h.up(24)
    h.heartbeat(37)
    h.down(25, 100)
    r = records(h, vlog_manifest)
    assert (r[1]["t"] - r[0]["t"]) & 0xFFFF == 37


def test_the_log_changes_no_note(stock_image, vlog_image):
    """The log only observes: stock's pads play the same notes and LEDs with it (PL04D's chord-with-log check retired with
    PL06: the chord engine and the log no longer fit together, and PL04D rebuilds from its tag)."""
    def play(img):
        h = VoiceHarness(img)
        h.set_headroom(0x20000)
        h.track(0)
        h.take()
        for pad in (20, 24, 27):
            h.down(pad, 100)
        h.heartbeat(5)
        leds = h.leds()
        for pad in (20, 24, 27):
            h.up(pad)
        return [e[:4] for e in h.take("synth_on")], leds
    assert play(stock_image) == play(vlog_image)


def test_free_and_releasing_follow_stocks_own_test(vlog_image, vlog_manifest):
    """Stock's pickers call a voice free when the high half of its state word is 0 (0x080216F0); a note-off leaves
    0x0001FFFF (releasing), a finished release a zero high half (free) though the low half stays set."""
    h = VoiceHarness(vlog_image)
    h.set_headroom(0x20000)
    h.track(0)
    slots = 0x20005F64
    h.uc.mem_write(slots + 16 * 2 + 4, (0x0000FFFF).to_bytes(4, "little"))   # release finished
    h.uc.mem_write(slots + 16 * 3 + 4, (0x0001FFFF).to_bytes(4, "little"))   # releasing
    h.down(24, 100)
    before = records(h, vlog_manifest)[-1]["before"]
    assert [(before >> (2 * v)) & 3 for v in (2, 3)] == [0, 1]
