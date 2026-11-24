"""q3_spill: a spilled note written raw into a later step of the Note view's shown pattern (as the pad's release would,
UI task), then a store touch; does the step pad light at once, and does the unit survive stock edits?
Stopped, track 0, two-row Note view. The held step is step pad 3 (step 4). Steps 5 and 7 (pads 4, 6) hold two older
notes (units 0-1). The spill (note 60, gate 6, microstep 2, velocity 100) goes into unit 2 of step 5 (pad 4, beside the
older notes) and of the empty step 6 (pad 5), pattern 0 or pattern 2.
Touches: none; rec_touch(rec) (0x0803F8D4); store_touch_all + store_commit (0x08035456 + 0x080353C0) on [rec + 0x4C],
which is upstream's [0x20039E50 + 0x3A0 t + 0x18] (q3_probe: the same store).
Then: (A) stock add on the spilled step (hold pad 4, key pad 30); (B) stock add on another step (pad 6); (C) the held
step's own add after the spill (step first: step 3 still held when the pad is let go); (D) Play: the note sounds."""
from unicorn.arm_const import UC_ARM_REG_R0

from lib import SH, pl18, prepare, unit_map
from notes import PATTERN_BASE, PATTERN, step_addr

IMG, M = pl18()
REC_TOUCH, TOUCH_ALL, COMMIT = 0x0803F8D4, 0x08035456, 0x080353C0
SPILL = (60, 6, 2, 100)


def spill(h, pattern, s):
    a = step_addr(0, pattern, s)
    h.uc.mem_write(a + 4 + 4 * 2, bytes(SPILL))
    h.uc.mem_write(a, bytes([h.r8(a) | 4, 7]))


def touch(h, how):
    rec = h.rec()
    if how == "rec_touch":
        h.call(REC_TOUCH, rec)
    elif how == "touch_all":
        st = h.r32(rec + 0x4C)
        h.call(TOUCH_ALL, st)
        h.call(COMMIT, st)


def run(how, pattern=0, order="step first"):
    h = SH(IMG)
    prepare(h)
    if pattern:
        h.press(13)
        h.pad(8 * pattern)                  # Patterns view: pattern r of track 0 = pad 8 r
        h.track(0)
    base = PATTERN_BASE[0] + PATTERN * pattern
    for s in (4, 6):
        h.uc.mem_write(step_addr(0, pattern, s), bytes([3, 7, 0, 0, 40, 6, 0, 90, 41, 6, 0, 90]) + bytes(16))
    touch(h, "rec_touch")                   # the older notes shown (as recorded earlier)
    empty, full = h.leds()[5], h.leds()[4]
    assert h.leds()[4] != empty
    # the spill: the pad's release; step first = step pad 3 still held, pad first = let go before
    h.down(3)
    if order == "pad first":
        h.up(3)
    spill(h, pattern, 4)
    spill(h, pattern, 5)
    touch(h, how)
    lit = h.leds()[5]
    if order == "step first":
        h.up(3)
    after_release = h.leds()[5]
    out = [f"{how:9s} pattern {pattern} {order}: empty step 6 + spill: pad 5 LED {lit:#04x} (a step with notes {full:#04x},"
           f" empty {empty:#04x}); after the step's release {after_release:#04x}"]
    h.down(4); h.down(30); h.up(30); h.up(4)            # (A) stock add on the spilled steps
    h.down(5); h.down(30); h.up(30); h.up(5)
    out.append(f"A: step 5 {sorted(v[0] for v in unit_map(h, 4, pattern).values())},"
               f" step 6 {sorted(v[0] for v in unit_map(h, 5, pattern).values())}")
    h.down(6); h.down(26); h.up(26); h.up(6)            # (B) another step
    out.append(f"B: step 5 {sorted(v[0] for v in unit_map(h, 4, pattern).values())},"
               f" step 6 {sorted(v[0] for v in unit_map(h, 5, pattern).values())}")
    h.log.clear()
    h.press(17)
    h.heartbeat(1200)
    h.press(17)
    on = [e[2] for e in h.take("synth_on")]
    out.append(f"D: 60 sounds {60 in on}")
    print("  ".join(out))


def held_step_add(how):
    """(C) step first: hold step 3, press key pad 24 (the held step's own add), spill into step 4, touch, then press
    key pad 28 on the still-held step 3: the held step's edit store writes step 3 only, the spill stays."""
    h = SH(IMG)
    prepare(h)
    h.down(3)
    h.down(24); h.up(24)
    spill(h, 0, 5)
    touch(h, how)
    lit = h.leds()[5]
    h.down(28); h.up(28)
    h.up(3)
    print(f"C {how:9s}: pad 5 LED {lit:#04x}; step 4 {sorted(v[0] for v in unit_map(h, 3).values())},"
          f" step 6 {unit_map(h, 5)}, LED {h.leds()[5]:#04x}")


for how in ("none", "rec_touch", "touch_all"):
    run(how)
    run(how, order="pad first")
    run(how, pattern=2)
    held_step_add(how)
