"""Trig conditions' maths (PL20): the model's own examples (no emulation), and the C functions against the model.

Spec: docs/specs/ (trig conditions); plan Task 2. The model is tests/trig_model.py."""
import itertools

import pytest
from unicorn.arm_const import UC_ARM_REG_R0

import trig_model as tm
from harness import Harness
from notes import OUTBUF

ALL = range(512)


def sym(m, name):
    return int(m["symbols"][name], 16)


def pass_list(code, passes=24, pre=0, fill=0, last=0):
    """The 1-based passes on which the condition lets the step play."""
    return [c + 1 for c in range(passes) if tm.trig_plays(code, c, pre, fill, last)]


def test_every_code_is_none_a_cycle_or_a_special():
    for code in ALL:
        kinds = [tm.trig_len(code) > 0, tm.trig_special(code) < 8]
        assert sum(kinds) <= 1, code
        assert tm.trig_kind(code) == (tm.TRIG_CYCLE if kinds[0] else tm.TRIG_SPECIAL_KIND if kinds[1] else tm.TRIG_NONE)
        if kinds[0]:
            assert 2 <= tm.trig_len(code) <= 8 and 0 < tm.trig_mask(code) < 1 << tm.trig_len(code)
            assert tm.trig_cycle(tm.trig_len(code), tm.trig_mask(code)) == code
        else:
            assert tm.trig_len(code) == tm.trig_mask(code) == 0
    for length in range(2, 9):
        for mask in range(1, 1 << length):
            code = tm.trig_cycle(length, mask)
            assert (tm.trig_len(code), tm.trig_mask(code)) == (length, mask) or tm.trig_special(code) < 8
    # the only cycles a special takes the place of are the empty ones (mask 0), so a real cycle never collides
    assert all(tm.trig_kind(tm.trig_cycle(L, k)) == tm.TRIG_CYCLE
               for L in range(2, 9) for k in range(1, 1 << L))


def test_empty_cycles_and_out_of_range_codes_read_as_none():
    assert tm.trig_kind(0) == tm.trig_kind(128) == tm.trig_kind(256) == tm.TRIG_NONE
    assert tm.trig_kind(511) == tm.TRIG_CYCLE and tm.trig_cycle(8, 0xFF) == 511
    assert tm.trig_cycle(8, 0) == tm.trig_cycle(1, 1) == tm.trig_cycle(9, 1) == tm.trig_cycle(3, 8) == 0


def test_elektron_cycles():
    assert pass_list(tm.trig_cycle(2, 0b10), 8) == [2, 4, 6, 8]                    # 2:2
    assert pass_list(tm.trig_cycle(3, 0b010), 9) == [2, 5, 8]                      # 2:3
    assert pass_list(tm.trig_cycle(7, 1 << 4), 20) == [5, 12, 19]                  # 5:7
    assert pass_list(tm.trig_cycle(2, 0b10), 6) == [2, 4, 6]                       # "not 1:2" = 2:2
    assert pass_list(tm.trig_cycle(4, 0b1111), 10) == list(range(1, 11))           # every pass ticked plays every pass
    assert pass_list(tm.trig_cycle(3, 0b101), 6) == [1, 3, 4, 6]


def test_the_count_wraps_at_840():
    # 840 is the least common multiple of 1..8: a count reaching 1680 goes back to 840, so every cycle sees the same
    # sequence as an unwrapped count, and count 0 (FIRST) comes only once
    for L in range(2, 9):
        assert tm.TRIG_COUNT_MOD % L == 0
    assert (tm.trig_next_count(839), tm.trig_next_count(1678), tm.trig_next_count(1679)) == (840, 1679, 840)
    c, seen = 0, []
    for u in range(4 * tm.TRIG_COUNT_MOD):
        seen.append(c)
        for code in (tm.trig_cycle(L, m) for L in range(2, 9) for m in (1, (1 << L) - 2, 0b101 & ((1 << L) - 1))):
            assert tm.plays(code, c, 0, 0, 0) == tm.plays(code, u, 0, 0, 0), (code, u, c)
        assert tm.plays(tm.TRIG_SPECIAL[tm.TRIG_FIRST], c, 0, 0, 0) == (u == 0)
        c = tm.trig_next_count(c)
    assert max(seen) == 2 * tm.TRIG_COUNT_MOD - 1 and seen.count(0) == 1


def test_specials_by_context():
    for count, pre, fill, last in itertools.product((0, 1, 7), (0, 1), (0, 1), (0, 1)):
        for s, want in enumerate((count == 0, count != 0, fill, not fill, pre, not pre, last, not last)):
            assert tm.trig_plays(tm.TRIG_SPECIAL[s], count, pre, fill, last) == int(bool(want)), (s, count, pre, fill, last)
        assert tm.trig_plays(0, count, pre, fill, last) == 1


def test_conditional():
    for prob in range(8):
        assert tm.trig_conditional(0, prob) == (prob < 7)
        for s in (tm.TRIG_PRE, tm.TRIG_NOT_PRE):
            assert tm.trig_conditional(tm.TRIG_SPECIAL[s], prob) == 0
        for s in (0, 1, 2, 3, 6, 7):
            assert tm.trig_conditional(tm.TRIG_SPECIAL[s], prob) == 1
        assert tm.trig_conditional(tm.trig_cycle(3, 1), prob) == 1


def test_edit_shift():
    for drum in (0, 1):
        for pad in range(8):
            sp = tm.TRIG_SPECIAL[pad]
            blocked = not drum and pad in (tm.TRIG_FILL, tm.TRIG_NOT_FILL)
            for code in (0, tm.trig_cycle(4, 0b0101), tm.TRIG_SPECIAL[(pad + 1) % 8], sp):
                got = tm.trig_edit(code, pad, tm.TRIG_SHIFT, drum)
                if blocked:
                    assert got == code
                elif code == sp:
                    assert got == 0
                else:
                    assert got == sp


def test_edit_hold():
    for drum in (0, 1):
        assert tm.trig_edit(tm.trig_cycle(4, 0b0110), 0, tm.TRIG_HOLD, drum) == 0       # pad 1: a cycle of 1 is no condition
        assert tm.trig_edit(0, 0, tm.TRIG_HOLD, drum) == 0
    assert tm.trig_edit(0, 3, tm.TRIG_HOLD, 1) == tm.trig_cycle(4, 1)                   # none: 1:4
    assert tm.trig_edit(tm.TRIG_SPECIAL[2], 5, tm.TRIG_HOLD, 1) == tm.trig_cycle(6, 1)  # a special: 1:6
    assert tm.trig_edit(tm.trig_cycle(4, 0b0110), 3, tm.TRIG_HOLD, 0) == 0               # the same length: off
    assert tm.trig_edit(tm.trig_cycle(4, 0b0110), 5, tm.TRIG_HOLD, 0) == tm.trig_cycle(6, 0b0110)   # longer: ticks kept
    assert tm.trig_edit(tm.trig_cycle(6, 0b101100), 2, tm.TRIG_HOLD, 0) == tm.trig_cycle(3, 0b100)   # shorter: those that fit
    assert tm.trig_edit(tm.trig_cycle(6, 0b100000), 2, tm.TRIG_HOLD, 0) == tm.trig_cycle(3, 1)       # none fit: pass 1


def test_edit_tap():
    c = tm.trig_cycle(4, 0b0101)
    assert tm.trig_edit(c, 1, tm.TRIG_TAP, 0) == tm.trig_cycle(4, 0b0111)
    assert tm.trig_edit(c, 0, tm.TRIG_TAP, 0) == tm.trig_cycle(4, 0b0100)
    assert tm.trig_edit(c, 4, tm.TRIG_TAP, 0) == c                                       # past the length
    assert tm.trig_edit(tm.trig_cycle(3, 0b010), 1, tm.TRIG_TAP, 1) == 0                # the last ticked pass: the condition goes
    for code in (0, tm.TRIG_SPECIAL[3], tm.TRIG_SPECIAL[0]):
        assert all(tm.trig_edit(code, p, tm.TRIG_TAP, 1) == code for p in range(8))


def test_edit_walk():
    code = tm.trig_edit(0, 3, tm.TRIG_HOLD, 1)
    assert code == tm.trig_cycle(4, 0b0001)
    for pad in (2, 1, 3):
        code = tm.trig_edit(code, pad, tm.TRIG_TAP, 1)
    assert code == tm.trig_cycle(4, 0b1111) and pass_list(code, 8) == list(range(1, 9))   # every pass ticked
    for pad in (0, 1, 2):
        code = tm.trig_edit(code, pad, tm.TRIG_TAP, 1)
        assert tm.trig_kind(code) == tm.TRIG_CYCLE
    assert tm.trig_edit(code, 3, tm.TRIG_TAP, 1) == 0
    assert tm.trig_edit(tm.trig_edit(0, 3, tm.TRIG_HOLD, 1), 3, tm.TRIG_HOLD, 1) == 0


def test_every_edit_gives_a_valid_code():
    for code in ALL:
        for pad, g, drum in itertools.product(range(8), (0, 1, 2), (0, 1)):
            new = tm.trig_edit(code, pad, g, drum)
            assert 0 <= new < 512
            assert tm.trig_kind(new) != tm.TRIG_NONE or new == 0 or new == code      # a stray code (128, 256) is left alone


def test_row4():
    O, D, B = tm.COL_OFF, tm.COL_CYAN_DIM, tm.COL_CYAN
    assert tm.trig_row4(0, 0, 1) == [O] * 8
    assert tm.trig_row4(tm.trig_cycle(4, 0b0101), 0, 0) == [B, D, B, D, O, O, O, O]
    for s in range(8):
        dim = tm.SPECIAL_COL[s][1]
        assert tm.trig_row4(tm.TRIG_SPECIAL[s], 0, 1) == [dim] * 8
    drums_none = tm.trig_row4(0, 1, 1)
    assert drums_none == [tm.COL_GREEN_DIM] * 2 + [tm.COL_ORANGE_DIM] * 2 + [tm.COL_VIOLET_DIM] * 2 + [tm.COL_YELLOW_DIM] * 2
    notes_fill = tm.trig_row4(tm.TRIG_SPECIAL[tm.TRIG_PRE], 1, 0)
    assert notes_fill == [tm.COL_GREEN_DIM] * 2 + [O, O] + [tm.COL_VIOLET, tm.COL_VIOLET_DIM] + [tm.COL_YELLOW_DIM] * 2
    assert tm.trig_row4(tm.TRIG_SPECIAL[7], 1, 1)[7] == tm.COL_YELLOW


def test_byte_layout():
    pat = bytearray(0x6A8)
    tm.trig_drum_set(pat, 13, 0x1A5)
    assert pat[0x88 + 13] == 0xA5 and pat[0x85] == 0x20 and tm.trig_drum_get(pat, 13) == 0x1A5
    assert not any(pat[:0x84]) and not any(pat[0x84:0x85]) and not any(pat[0x86:0x88])
    tm.trig_drum_set(pat, 13, 0x0A5)
    assert pat[0x85] == 0 and tm.trig_drum_get(pat, 13) == 0xA5
    for s in range(32):
        tm.trig_drum_set(pat, s, 0x100 | s)
    assert all(tm.trig_drum_get(pat, s) == 0x100 | s for s in range(32)) and pat[0x84:0x88] == b"\xff" * 4
    step = bytearray([0x3F, 0x11, 0x77, 0xFF] + [0x22] * 24)
    tm.trig_note_set(step, 0x1A5)
    assert step[2] == 0xA5 and step[3] == 1 and step[:2] == b"\x3f\x11" and tm.trig_note_get(step) == 0x1A5
    tm.trig_note_set(step, 0x05)
    assert step[3] == 0 and tm.trig_note_get(step) == 5


# ---- the C functions against the model (emulation)

CTX = [(0, 0, 0, 0), (1, 1, 0, 0), (2, 0, 1, 1), (3, 1, 1, 0), (4, 0, 0, 1), (5, 1, 0, 1), (6, 0, 1, 0), (7, 1, 1, 1),
       (8, 1, 0, 0), (9, 0, 0, 0), (839, 1, 1, 1)]


@pytest.mark.emu
def test_trig_math_matches_the_model(pl21_image, pl21_manifest):
    h = Harness(pl21_image)
    m = pl21_manifest
    h.uc.mem_write(OUTBUF, bytes(8))

    def call(name, *args):
        h.call(sym(m, name), *args)
        return h.uc.reg_read(UC_ARM_REG_R0)

    assert [int.from_bytes(h.uc.mem_read(sym(m, "TRIG_SPECIAL") + 2 * i, 2), "little") for i in range(8)] == tm.TRIG_SPECIAL
    CTXP = OUTBUF + 0x40                                   # trig_ctx_t: uint16 count, uint8 pre, fill, last
    for code in ALL:
        assert call("trig_kind", code) == tm.trig_kind(code), code
        assert call("trig_len", code) == tm.trig_len(code), code
        assert call("trig_mask", code) == tm.trig_mask(code), code
        assert call("trig_special", code) == tm.trig_special(code), code
        for count, pre, fill, last in CTX:
            h.uc.mem_write(CTXP, count.to_bytes(2, "little") + bytes([pre, fill, last]))
            assert call("trig_plays", code, CTXP) == tm.trig_plays(code, count, pre, fill, last), (code, count, pre, fill, last)
        for prob in range(8):
            assert call("trig_conditional", code, prob) == tm.trig_conditional(code, prob), (code, prob)
        for pad, g, drum in itertools.product(range(8), (0, 1, 2), (0, 1)):
            assert call("trig_edit", code, pad, g, drum) == tm.trig_edit(code, pad, g, drum), (code, pad, g, drum)
        for shift, drum in itertools.product((0, 1), (0, 1)):
            h.uc.mem_write(OUTBUF + 0x80, b"\xee" * 18)
            h.call(sym(m, "trig_row4"), code, shift, drum, OUTBUF + 0x80)
            got = [int.from_bytes(h.uc.mem_read(OUTBUF + 0x80 + 2 * i, 2), "little") for i in range(8)]
            assert got == tm.trig_row4(code, shift, drum), (code, shift, drum)
            assert bytes(h.uc.mem_read(OUTBUF + 0x90, 2)) == b"\xee\xee"                   # nothing past the eighth
    for length in range(0, 10):
        for mask in range(0, 520):
            assert call("trig_cycle", length, mask) == tm.trig_cycle(length, mask), (length, mask)
    for step in (0, 5, 13, 31):
        for code in (0, 0x1A5, 0x100, 0xFF, 0x1FF):
            image = bytearray(b"\x5a" * 0x100)
            h.uc.mem_write(OUTBUF + 0x100, bytes(image))
            ref = bytearray(image)
            tm.trig_drum_set(ref, step, code)
            h.call(sym(m, "trig_drum_set"), OUTBUF + 0x100, step, code)
            assert bytes(h.uc.mem_read(OUTBUF + 0x100, 0x100)) == bytes(ref), (step, code)
            assert call("trig_drum_get", OUTBUF + 0x100, step) == tm.trig_drum_get(ref, step)
            nref = bytearray(b"\x5a" * 0x100)
            h.uc.mem_write(OUTBUF + 0x100, bytes(nref))
            tm.trig_note_set(nref, code)
            h.call(sym(m, "trig_note_set"), OUTBUF + 0x100, code)
            assert bytes(h.uc.mem_read(OUTBUF + 0x100, 0x100)) == bytes(nref), code
            assert call("trig_note_get", OUTBUF + 0x100) == tm.trig_note_get(nref)
