"""Euclidean fills (PL11, spec 2026-10-17-euclidean-design.md, "Decided at planning"): the Pattern tools page (page 4 of a
synth or MIDI track): hits 1-16 on pads 1-16 with the rhythm previewed there, rotate, gate, velocity; Write (two presses)
and Undo."""
import pytest
from unicorn.arm_const import UC_ARM_REG_R0

import euclid_model
from harness import Harness
from notes import NoteHarness, PATTERN_BASE, param

pytestmark = pytest.mark.emu
ENG, PATTERN = 0x20038EC0, 0xCA8
TOOLS, KEYS = 2, 7                                 # the page = its pad in the page list (25 + page)
GREEN, GREEN_D, BLUE, BLUE_D, MAG, MAG_D = 0x17, 0x18, 0x07, 0x08, 0x32, 0x38
ORANGE, ORANGE_D, WHITE_D = 0x45, 0x46, 0x02
YELLOW, YELLOW_D = 0x2D, 0x2E                      # the Melody page (PL13) sits at pad 28
LED_DOWN, LED_UP = 51, 52
DEFAULT_CFG = bytes([0x20, 0x40] * 4)


def sym(m, name):
    return int(m["symbols"][name], 16)


def cfg(h, m, t):
    return tuple(h.uc.mem_read(sym(m, "euclid_cfg") + 2 * t, 2))


def current(h, t):
    return param(h, h.r32(ENG + 0x30 + 4 * t), 0)


def pattern_at(h, t, p=None):
    return PATTERN_BASE[t] + (current(h, t) if p is None else p) * PATTERN


def set_range(h, t, first, last):
    h.uc.mem_write(pattern_at(h, t) + 0x380, bytes([last, first]))


def pick(h, pad):
    h.down(pad)
    h.up(pad)


def open_tools(h, t):
    h.leds()                                      # the first frame applies the record's (empty) settings first
    h.track(t)
    h.press(t, shift=True)
    h.shift(True)
    pick(h, 24)                                   # Chords first: from PL14 the open feature's pad flips its two pages
    pick(h, 24 + TOOLS)                           # the table of contents: pad 27 (its page used last)
    h.shift(False)


def preview(h):
    return h.leds()[:16]


def expected(mask, n):
    return [ORANGE if mask >> s & 1 else ORANGE_D if s < n else 0 for s in range(16)]


def test_mask_matches_the_model(pl11_image, pl11_manifest):
    h = Harness(pl11_image)
    fn = sym(pl11_manifest, "euclid_mask")
    for n in range(1, 33):
        for k in range(0, n + 2):
            for r in range(n):
                h.call(fn, k, n, r)
                assert h.uc.reg_read(UC_ARM_REG_R0) == euclid_model.mask(k, n, r), (k, n, r)


def test_table_of_contents_has_pattern_tools(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    h.track(0)
    h.press(0, shift=True)
    h.shift(True)
    assert h.leds()[24:32] == [GREEN, BLUE_D, ORANGE_D, YELLOW_D, 0, 0, 0, MAG_D]   # main pages left, Keys (setup) at pad 32
    pick(h, 26)
    assert h.r8(sym(pl11_manifest, "page_slot")) == TOOLS
    assert h.leds()[24:32] == [GREEN_D, BLUE_D, ORANGE, YELLOW_D, 0, 0, 0, MAG_D]
    h.shift(False)
    leds = h.leds()
    assert (leds[LED_DOWN], leds[LED_UP]) == (ORANGE, BLUE)            # its page 2 after it (PL14), Arp before
    for _ in range(4):
        h.press(19)                                                # ▼: Pattern tools 2, Melody, Phrasing, Keys (the last)
    assert h.r8(sym(pl11_manifest, "page_slot")) == KEYS and h.leds()[LED_DOWN] == 0


def test_page_leds_before_any_pick(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    open_tools(h, 2)
    leds = h.leds()
    assert leds[:16] == [ORANGE_D] * 16                            # k = 0: no hit, a 16-step pattern
    assert leds[16:19] == [WHITE_D] * 3 and leds[19] == WHITE_D   # 19: the source (PL13)
    assert leds[20] == 0x66 and leds[21:24] == [MAG_D, MAG, MAG_D]   # gate 3/6, velocity medium
    assert leds[24:32] == [0x4E] * 4 + [WHITE_D, 0, 0, 0]       # 24-27: the cycle, none (PL14); 28: dice rhythm (PL13); dice notes dark (order same), Undo none, Write dark at k = 0


def test_hits_preview(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    open_tools(h, 2)
    pick(h, 4)                                                     # 5 hits
    assert preview(h) == expected(euclid_model.mask(5, 16, 0), 16)
    assert cfg(h, pl11_manifest, 2)[0] & 0x1F == 5 and h.leds()[31] == ORANGE_D
    pick(h, 15)
    assert preview(h) == [ORANGE] * 16


def test_preview_follows_the_pattern_length(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    open_tools(h, 2)
    pick(h, 4)
    set_range(h, 2, 0, 11)
    assert preview(h) == expected(euclid_model.mask(5, 12, 0), 12)
    set_range(h, 2, 4, 11)
    assert preview(h) == expected(euclid_model.mask(5, 8, 0), 8)
    set_range(h, 2, 11, 4)                                         # swapped: the same range
    assert preview(h) == expected(euclid_model.mask(5, 8, 0), 8)
    set_range(h, 2, 0, 31)                                         # 32 steps: the first 16
    assert preview(h) == expected(euclid_model.mask(5, 32, 0) & 0xFFFF, 16)


def test_rotate_pads(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    open_tools(h, 2)
    pick(h, 4)
    pick(h, 17)                                                    # ▶: the hits one step later
    assert preview(h) == expected(euclid_model.mask(5, 16, 15), 16)
    pick(h, 16)
    pick(h, 16)                                                    # ◀ twice
    assert preview(h) == expected(euclid_model.mask(5, 16, 1), 16)
    pick(h, 18)                                                    # back to rotation 0
    assert preview(h) == expected(euclid_model.mask(5, 16, 0), 16)


def test_gate_and_velocity_pads(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    open_tools(h, 1)
    assert h.leds()[20] == 0x66                                    # 3/6
    for colour, g in ((0x67, 1), (0x68, 0), (0x01, 6), (0x63, 5)):    # one sixth down, 1/6 -> to the next hit (PL13) -> 6/6
        pick(h, 20)
        assert h.leds()[20] == colour and cfg(h, pl11_manifest, 1)[1] >> 5 == g
    for pad, v in ((23, 2), (21, 0), (22, 1)):
        pick(h, pad)
        assert h.leds()[21:24] == [MAG if 21 + i == pad else MAG_D for i in range(3)]
        assert cfg(h, pl11_manifest, 1)[0] >> 5 == v


def test_pages_play_nothing_and_are_per_track(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    open_tools(h, 0)
    h.take()
    for pad in (4, 17, 20, 23, 19, 25):
        pick(h, pad)
    assert cfg(h, pl11_manifest, 0) != (0x20, 0x40)
    assert bytes(h.uc.mem_read(sym(pl11_manifest, "euclid_cfg") + 2, 6)) == DEFAULT_CFG[2:]
    assert h.take("synth_on", "midi_on") == [] and h.sounding == set()


def test_last_played_pad_is_remembered(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    h.leds()
    last = sym(pl11_manifest, "euclid_last")
    assert bytes(h.uc.mem_read(last, 4)) == bytes([72] * 4)
    h.track(2)
    pick(h, 26)                                                    # chords off
    assert h.r8(last + 2) == h.pitch(2, 26)
    h.uc.mem_write(sym(pl11_manifest, "chord_settings") + 2, bytes([1]))
    pick(h, 24)                                                    # a triad
    assert h.r8(last + 2) == h.pitch(2, 24) and h.r8(last) == 72


def test_quick_view_flip_skips_pattern_tools(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    h.track(0)
    quick = sym(pl11_manifest, "page_quick")
    h.press(21, shift=True)
    assert h.r8(quick) == 1                                        # Arp
    h.press(21, shift=True)
    assert h.r8(quick) == 0                                        # Keys and Pattern tools have no quick half


def test_a_short_format2_payload_gives_euclid_defaults(pl11_image, pl11_manifest):
    from test_saved import DISTINCT, load, make_tail, settings, write_tail
    h = NoteHarness(pl11_image)
    h.leds()
    h.uc.mem_write(sym(pl11_manifest, "euclid_cfg"), bytes([0x05, 0x4F] * 4))
    h.uc.mem_write(sym(pl11_manifest, "page_slot"), bytes([1, 2, 7, 1]))
    pl10 = DISTINCT[:16] + bytes([1, 2, 2, 0]) + DISTINCT[20:25]  # a 25 B format-2 payload: later fields take defaults
    write_tail(h, make_tail(pl10))
    load(h)
    h.leds()
    assert settings(h, pl11_manifest)[:25] == DISTINCT[:16] + bytes(4) + DISTINCT[20:25]
    assert bytes(h.uc.mem_read(sym(pl11_manifest, "euclid_cfg"), 8)) == DEFAULT_CFG
    assert bytes(h.uc.mem_read(sym(pl11_manifest, "page_slot"), 4)) == bytes(4)    # every track opens on Chords once


# ---- Write and Undo (Task 2) ----

from chord_model import chord_notes, settings as chord_settings_word   # noqa: E402
from notes import ROOT, SCALE_MASK, TEMPO_STORE, pattern_snapshot, recorded_notes   # noqa: E402

UNDO, WRITE = 30, 31
VELOCITY = (48, 96, 127)
EMPTY = bytes([0, 7, 0, 0]) + bytes([0, 0, 0, 0x60]) * 6


def steps(h, t, p=None):
    return bytes(h.uc.mem_read(pattern_at(h, t, p), 0x380))


def whole(h, t, p):
    return bytes(h.uc.mem_read(pattern_at(h, t, p), PATTERN))


def expected_steps(mask, n, first, notes, gate, vel):
    """The 32 steps a Write leaves: hits on steps first .. first + n - 1, every other step empty."""
    out = b""
    for s in range(32):
        i = s - first
        if 0 <= i < n and mask >> i & 1:
            units = b"".join(bytes([note, gate + 1, 0, vel]) for note in notes)
            out += bytes([(1 << len(notes)) - 1, 7, 0, 0]) + units + bytes([0, 0, 0, 0x60]) * (6 - len(notes))
        else:
            out += EMPTY
    return out


def write(h):
    pick(h, WRITE)
    pick(h, WRITE)


def test_write_takes_two_presses(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    open_tools(h, 2)
    before = steps(h, 2)
    pick(h, 4)
    pick(h, WRITE)
    assert steps(h, 2) == before and h.leds()[WRITE] == 0x47      # armed: blinking
    pick(h, WRITE)
    assert steps(h, 2) == expected_steps(euclid_model.mask(5, 16, 0), 16, 0, [72], 2, 96)
    assert h.leds()[WRITE] == ORANGE_D


def test_another_pad_or_leaving_disarms(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    open_tools(h, 2)
    before = steps(h, 2)
    pick(h, 4)
    pick(h, WRITE)
    pick(h, 4)                                                     # another pad: disarmed
    assert h.leds()[WRITE] == ORANGE_D
    pick(h, WRITE)                                                 # arms again, writes nothing
    assert steps(h, 2) == before and h.leds()[WRITE] == 0x47
    h.press(2)                                                     # leave the page
    h.press(2, shift=True)                                         # and back (its last page: Pattern tools)
    pick(h, WRITE)
    assert steps(h, 2) == before and h.leds()[WRITE] == 0x47


def test_written_steps(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    h.leds()
    h.track(2)
    h.uc.mem_write(sym(pl11_manifest, "chord_settings") + 2, bytes([1]))      # triad
    pick(h, 24)
    root = h.pitch(2, 24)
    notes = [root] + chord_notes(root, h.r32(SCALE_MASK), chord_settings_word(1, key=h.r8(ROOT)))
    others = {(t, p): whole(h, t, p) for t in range(4) for p in range(8) if (t, p) != (2, 0)}
    tail = whole(h, 2, 0)[0x380:]
    open_tools(h, 2)
    pick(h, 6)                                                     # 7 hits
    pick(h, 23)                                                    # hard
    pick(h, 20)                                                    # gate 2/6
    set_range(h, 2, 2, 13)                                         # 12 steps from step 3
    tail = bytes([13, 2]) + tail[2:]
    write(h)
    assert steps(h, 2) == expected_steps(euclid_model.mask(7, 12, 0), 12, 2, notes, 1, 127)
    assert whole(h, 2, 0)[0x380:] == tail                          # settings and automation kept
    assert all(whole(h, t, p) == b for (t, p), b in others.items())


def test_written_pattern_plays_through_stock(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    open_tools(h, 2)
    pick(h, 3)                                                     # 4 hits: steps 1, 5, 9, 13
    write(h)
    h.press(2)
    h.take()
    h.press(17)                                                    # Play
    step_ms = 60000 / param(h, TEMPO_STORE, 0) / 4
    ons, offs = [], []
    for ms in range(1, int(16 * step_ms) + 2):
        h.heartbeat(1)
        for e in h.take("midi_on", "midi_off"):
            if e[2] == 2:                                          # MIDI 1's channel
                (ons if e[0] == "midi_on" else offs).append((ms, e[3]))
    assert [n for _, n in ons] == [72 - 12 + h.r8(ROOT)] * 4
    for k, (ms, _) in enumerate(ons):
        assert abs(ms - 1 - 4 * k * step_ms) <= 2, ons
        assert abs(offs[k][0] - ms - 3 * step_ms / 6) <= 2, (ons, offs)


def test_k0_writes_nothing_and_k_ge_n_fills(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    open_tools(h, 3)
    before = steps(h, 3)
    assert h.leds()[WRITE] == 0
    write(h)
    assert steps(h, 3) == before
    set_range(h, 3, 0, 7)
    pick(h, 15)                                                    # 16 hits in 8 steps
    write(h)
    assert steps(h, 3) == expected_steps(0xFF, 8, 0, [72], 2, 96)


def test_write_targets_the_selected_pattern(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    h.leds()
    h.press(13)
    h.pad(16 + 2)                                                  # Patterns view: MIDI 1 pattern 3
    assert current(h, 2) == 2
    first = whole(h, 2, 0)
    open_tools(h, 2)
    pick(h, 2)
    write(h)
    assert steps(h, 2, 2) == expected_steps(euclid_model.mask(3, 16, 0), 16, 0, [72], 2, 96)
    assert whole(h, 2, 0) == first


def test_write_while_playing_leaves_nothing_on(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    h.leds()
    h.press(17)                                                    # Synth 1's pattern plays (a 10-step note at step 1)
    h.heartbeat(200)
    assert h.sounding
    open_tools(h, 0)
    pick(h, 2)
    write(h)
    assert steps(h, 0) == expected_steps(euclid_model.mask(3, 16, 0), 16, 0, [72], 2, 96)
    h.heartbeat(2000)
    h.press(17)                                                    # stop
    h.heartbeat(300)
    assert h.sounding == set(), sorted(h.sounding)


def test_undo_swaps(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    open_tools(h, 1)
    before = steps(h, 1)
    assert h.leds()[UNDO] == 0
    pick(h, 4)
    write(h)
    written = steps(h, 1)
    assert written != before and h.leds()[UNDO] == BLUE
    pick(h, UNDO)
    assert steps(h, 1) == before and h.leds()[UNDO] == BLUE
    pick(h, UNDO)                                                  # again: the write back (redo)
    assert steps(h, 1) == written


def test_undo_restores_its_own_pattern(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    open_tools(h, 2)
    before = steps(h, 2, 0)
    pick(h, 4)
    write(h)
    h.press(13)
    h.pad(8 + 2)                                                   # MIDI 1 pattern 2
    second = whole(h, 2, 1)
    h.press(3, shift=True)                                         # MIDI 2's page: no Undo of its own
    h.shift(True)
    pick(h, 24 + TOOLS)
    h.shift(False)
    assert h.leds()[UNDO] == 0
    pick(h, UNDO)
    assert steps(h, 2, 0) != before
    h.press(2, shift=True)                                         # MIDI 1's page (now on pattern 2)
    assert h.leds()[UNDO] == BLUE
    pick(h, UNDO)
    assert steps(h, 2, 0) == before and whole(h, 2, 1) == second


def test_a_project_load_drops_undo_and_the_armed_write(pl11_image, pl11_manifest):
    from test_saved import load
    h = NoteHarness(pl11_image)
    open_tools(h, 2)
    pick(h, 4)
    write(h)
    written = steps(h, 2)
    pick(h, WRITE)                                                 # armed
    load(h)
    h.leds()                                                       # applied: no CTPlay block, so defaults (Chords page)
    h.uc.mem_write(sym(pl11_manifest, "euclid_cfg") + 4, bytes([0x05]))     # k = 5 again on MIDI 1
    open_tools(h, 2)
    assert h.leds()[UNDO] == 0 and h.leds()[WRITE] == ORANGE_D
    pick(h, UNDO)
    pick(h, WRITE)                                                 # one press: arms only
    assert steps(h, 2) == written


def test_a_stock_recording_over_a_written_pattern_works(pl11_image, pl11_manifest):
    h = NoteHarness(pl11_image)
    open_tools(h, 2)
    pick(h, 3)                                                     # steps 1, 5, 9, 13
    write(h)
    h.press(2)                                                     # the Note view
    snap = pattern_snapshot(h, 2)
    assert snap[:0x380] == expected_steps(euclid_model.mask(4, 16, 0), 16, 0, [72], 2, 96)
    h.press(16)                                                    # Record
    h.press(17)                                                    # Play
    step_ms = 60000 / param(h, TEMPO_STORE, 0) / 4
    h.heartbeat(int(2 * step_ms) + 20)                             # into step 3
    h.down(26)
    h.heartbeat(60)
    h.up(26)
    h.heartbeat(400)
    got = recorded_notes(h, 2, snap)
    assert [(p, s, note) for p, s, note, *_ in got] == [(0, 2, h.pitch(2, 26))]
    assert steps(h, 2)[0:28] == snap[0:28]                         # the hits stay


def test_undo_names_the_pattern_the_write_replaced(pl11_image, pl11_manifest):
    """The target is read once, inside the masked section: the Main task (time-sliced) moving a chain on between reading
    the target and copying it must not leave Undo pointing at another pattern (final review, 2026-10-18)."""
    from unicorn import UC_HOOK_CODE
    h = NoteHarness(pl11_image)
    open_tools(h, 2)
    pick(h, 4)
    originals = [steps(h, 2, p) for p in range(2)]
    h.call(0x0803542C, h.r32(ENG + 0x30 + 4 * 2), 0)              # param_get: the pattern byte of MIDI 1's store
    pattern_byte = h.uc.reg_read(UC_ARM_REG_R0)
    fired = []

    def chain_moves_on(uc, address, size, data):                  # at the Write's slim_irq_save: pattern 1 -> 2
        if not fired:
            fired.append(address)
            uc.mem_write(pattern_byte, b"\x01")

    pick(h, WRITE)                                                 # armed
    a = sym(pl11_manifest, "slim_irq_save") & ~1
    h.uc.hook_add(UC_HOOK_CODE, chain_moves_on, begin=a, end=a)
    pick(h, WRITE)                                                 # the Write
    assert fired
    written = [p for p in range(2) if steps(h, 2, p) != originals[p]]
    assert len(written) == 1
    pick(h, UNDO)
    assert [steps(h, 2, p) for p in range(2)] == originals          # Undo restored the pattern it replaced, nothing else


def test_write_and_undo_in_a_playing_chain(pl11_image, pl11_manifest):
    """MIDI 1 chains patterns 1-2 and plays: a Write during pattern 2 writes pattern 2 only; Undo after playback is back
    on pattern 1 restores pattern 2 and leaves pattern 1 alone (final review, 2026-10-18)."""
    h = NoteHarness(pl11_image)
    h.leds()
    h.press(13)
    h.down(2)
    h.down(10)                                                     # Patterns view: hold pattern 1, press pattern 2
    h.up(10)
    h.up(2)
    open_tools(h, 2)
    pick(h, 4)
    h.press(17)                                                    # Play
    step_ms = 60000 / param(h, TEMPO_STORE, 0) / 4
    for _ in range(int(20 * step_ms)):                             # into the chain's second pattern
        h.heartbeat(1)
    assert current(h, 2) == 1
    first, second = whole(h, 2, 0), steps(h, 2, 1)
    write(h)
    assert steps(h, 2, 1) == expected_steps(euclid_model.mask(5, 16, 0), 16, 0, [72], 2, 96)
    assert whole(h, 2, 0) == first
    for _ in range(int(16 * step_ms)):
        h.heartbeat(1)
    assert current(h, 2) == 0                                      # playback back on pattern 1
    pick(h, UNDO)
    assert steps(h, 2, 1) == second and whole(h, 2, 0) == first


def test_the_note_view_shows_written_and_undone_steps(pl11_image, pl11_manifest):
    """The Note view keeps its own copy of which steps hold notes: a Write and an Undo tell stock the pattern changed, as
    the recorder's commit does (0x0803F8D4), or its step pads stay stale until a project load (device, PL11 step 9)."""
    EMPTY_STEP = 20                                                # the Note view's colour of a step without notes
    h = NoteHarness(pl11_image)
    open_tools(h, 2)
    h.press(2)
    before = h.leds()[1:16]                                        # pad 1 is the playhead
    assert before == [EMPTY_STEP] * 15
    open_tools(h, 2)
    pick(h, 3)                                                     # 4 hits: steps 1, 5, 9, 13
    write(h)
    h.press(2)
    lit = h.leds()[1:16]
    assert [s + 1 for s in range(15) if lit[s] != EMPTY_STEP] == [4, 8, 12]
    h.press(2, shift=True)                                         # back on Pattern tools
    pick(h, UNDO)
    h.press(2)
    assert h.leds()[1:16] == before


# ---- PL20 (trig conditions, Task 9): a note Write starts clean -------------------------------------------------------

@pytest.mark.parametrize("melody", [False, True], ids=["Euclid", "Melody"])
def test_write_clears_note_conditions(pl21_image, pl21_manifest, melody):
    """A marked project, a code on every step of Synth 1's pattern and step 1 selected in the probability view (its
    word 0 in the editor's edit store): a Write (Euclid, or a Melody line) leaves [2]-[3] 0 on all 32 steps; Undo
    brings them back; redo clears them; then a row-3 press on the selected step, without pressing it again, keeps 0."""
    from test_melody import configure
    from trig import ROW3, TrigHarness
    m = pl21_manifest
    h = TrigHarness(pl21_image, m)
    h.leds()
    codes = [(97 * s + 5) % 511 + 1 for s in range(32)]
    for s in range(32):
        h.set_code(0, 0, s, codes[s])
    h.mark(1)
    h.open_prob(0)
    h.pad(0)                                                       # step 1 selected
    assert h.selected(0) == (0, 0)
    open_tools(h, 0)
    if melody:
        configure(h, m, k=8, c0=1, shape=1, t=0)                   # up over a triad: a line, a draft
    else:
        pick(h, 4)                                                 # 5 hits, step 1 among them
    write(h)
    got = [h.code(0, 0, s) for s in range(32)]
    assert got == [0] * 32
    pick(h, UNDO)
    assert [h.code(0, 0, s) for s in range(32)] == codes
    pick(h, UNDO)                                                  # again: redo
    assert [h.code(0, 0, s) for s in range(32)] == [0] * 32
    assert h.r8(pattern_at(h, 0, 0)) & 0x3F                        # step 1 has a note: row 3 acts on it
    h.open_prob(0)
    h.pad(ROW3 + 2)
    assert h.r8(pattern_at(h, 0, 0) + 1) == 2                      # the row-3 press landed
    assert [h.code(0, 0, s) for s in range(32)] == [0] * 32
