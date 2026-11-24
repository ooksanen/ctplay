"""The DSP-mailbox model (approved 2026-10-13): a pad note runs through stock's real voice decision."""
import pytest

from voices import VoiceHarness

pytestmark = pytest.mark.emu


def test_arm_path_with_spare_time(pl09_image):
    h = VoiceHarness(pl09_image)
    h.set_headroom(0x20000)
    h.track(0)
    h.take()
    h.down(24, 100)
    on = h.take("synth_on")
    assert len(on) == 1
    synth, note = on[0][1], on[0][2]
    assert (h.state(4), h.state(0xA), h.state(0xE)) == (synth, note, 0)      # ARM path
    assert h.slot_state(h.state(5)) == 0x8000FFFF                            # the chosen voice is now held


def test_dsp_path_below_the_threshold(pl09_image):
    h = VoiceHarness(pl09_image)
    h.set_headroom(0x10000)
    h.set_dsp_voice(3)
    h.track(0)
    h.down(24, 100)
    assert (h.state(5), h.state(0xE)) == (3, 1)


def test_release_and_a_second_note_complete(pl09_image):
    h = VoiceHarness(pl09_image)
    h.set_headroom(0x20000)
    h.track(0)
    h.down(24, 100)
    h.up(24)                                                   # note-off runs for real, no DSP wait hangs
    h.take()
    h.down(25, 100)
    assert len(h.take("synth_on")) == 1


def test_note_harness_still_stubs_the_synth(pl09_image):
    from notes import NoteHarness
    h = NoteHarness(pl09_image)
    h.track(0)
    h.take()
    h.down(24, 100)
    assert [e[0] for e in h.take("synth_on")] == ["synth_on"] and h.sounding


def test_scripted_readings_and_the_decision_log(pl09_image):
    h = VoiceHarness(pl09_image)
    h.set_headroom(0x20000)
    h.script = [0x20000, 0x10000]
    h.track(0)
    h.down(24, 100)
    h.down(25, 100)
    assert [d["dsp"] for d in h.decisions] == [0, 1]          # 0x10000 < stock's 0x14000: the DSP picks
    assert h.decisions[0]["note"] == h.take("synth_on")[0][2] and h.script == []
    h.up(24)
    assert [e[0] for e in h.take("synth_off")] == ["synth_off"]
