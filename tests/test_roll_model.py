"""Pattern strum maths (PL19): the model's own examples (no emulation), and the C functions against the model."""
import pytest
from unicorn.arm_const import UC_ARM_REG_R0

import roll_model as rm
from harness import Harness
from notes import OUTBUF


def sym(m, name):
    return int(m["symbols"][name], 16)


def positions(rate, speed, count=3):
    """Each note's (step offset, microstep) from the first note's step."""
    st = rm.STEP_TICKS[rate]
    out = []
    for k in range(count):
        s = rm.roll_sixths(k * rm.WRITTEN_GAP[speed], st)
        out.append((s // 6, s % 6))
    return out


def test_slow_triad_at_1_16():
    assert positions(3, 1) == [(0, 0), (0, 4), (1, 2)]          # C at (s, 0), E at (s, 4), G at (s + 1, 2)


def test_fast_roll_at_1_8_shares_sixth_1():
    sixths = [rm.roll_sixths(k * rm.WRITTEN_GAP[3], rm.STEP_TICKS[5]) for k in range(3)]
    assert sixths == [0, 1, 1]


def test_sixths_at_1_16_are_the_ticks():
    assert [rm.roll_sixths(t, 6) for t in range(13)] == list(range(13))


def test_roll_step_wraps():
    assert rm.roll_step(31, 1, 0, 31) == 0
    assert rm.roll_step(5, 1, 1, 12) == 6
    for s in range(1, 13):
        for add in range(0, 40):
            assert 1 <= rm.roll_step(s, add, 1, 12) <= 12
    assert rm.roll_step(12, 1, 1, 12) == 1


def test_roll_step_from_outside_the_loop_carries_straight_on():
    """Beta 2 (spec 2026-11-22-beta2-fixes-design.md, section 2): from a step outside first..last the roll goes on as
    the step pads show; past step 32 (>= 32) the callers drop the note."""
    assert rm.roll_step(19, 0, 0, 15) == 19 and rm.roll_step(19, 1, 0, 15) == 20 and rm.roll_step(19, 3, 0, 15) == 22
    assert rm.roll_step(31, 1, 0, 15) == 32                     # past step 32: dropped by the callers
    assert rm.roll_step(2, 1, 4, 15) == 3 and rm.roll_step(2, 3, 4, 15) == 5     # before the start: straight on too
    assert rm.roll_step(15, 1, 0, 15) == 0                      # inside: still wraps within the loop


def test_roll_order():
    assert rm.roll_order([60, 64, 67, 48], True) == [67, 64, 60, 48]
    assert rm.roll_order([60, 64, 67, 48], False) == [48, 60, 64, 67]


@pytest.mark.emu
def test_roll_math_matches_the_model_in_c(pl19_image, pl19_manifest):
    h = Harness(pl19_image)
    m = pl19_manifest
    steps = [int.from_bytes(h.uc.mem_read(0x0805B8B8 + 4 * r, 4), "little") for r in range(8)]
    assert steps == rm.STEP_TICKS
    for r in range(8):
        for ticks in range(41):
            h.call(sym(m, "roll_sixths"), ticks, steps[r])
            assert h.uc.reg_read(UC_ARM_REG_R0) == rm.roll_sixths(ticks, steps[r]), (r, ticks)
    for first, last in ((0, 31), (1, 12), (16, 31), (5, 5)):
        for s in range(32):                      # inside the loop and outside it (beta 2)
            for add in range(0, 9):
                h.call(sym(m, "roll_step"), s, add, first, last)
                assert h.uc.reg_read(UC_ARM_REG_R0) == rm.roll_step(s, add, first, last), (s, add, first, last)
    for falling in (0, 1):
        for notes in ([60, 64, 67, 48], [60], [72, 60, 60, 61, 90]):
            h.uc.mem_write(OUTBUF, bytes(notes))
            h.call(sym(m, "roll_order"), OUTBUF, len(notes), falling)
            assert list(h.uc.mem_read(OUTBUF, len(notes))) == rm.roll_order(notes, falling)
    for speed in range(4):
        assert h.uc.mem_read(sym(m, "WRITTEN_GAP") + speed, 1)[0] == rm.WRITTEN_GAP[speed]
