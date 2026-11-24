"""q1_route_b: route (b), the placement 0x0803F298(rec, pattern, step, offset, [sp] start, [sp+4] note, [sp+8] vel)
changed at its entry for the strum's later notes. The list entry it makes (rec + 0x54 + 12 i) keeps note, velocity,
unit, start and offset but no step: the tick pass 0x0803F6C6(rec, pattern, step, step tick) writes the pending word
with the pass's own pattern and step. So a step given to the placement only picks which step's units it checks.
Cases (Synth 1, triad, slow, press at tick 40): step + 1; step - 1; offset + 6 (quantise off); start + 8."""
import struct

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP

from lib import PLACE, W, pl18, setup, wait_tick, written

IMG, M = pl18()


def case(label, quantise, change):
    h = setup(IMG, M, speed=1, quantise=quantise)
    n = [0]

    def hook(u, a, s, d):
        if h.rec() != u.reg_read(UC_ARM_REG_R0):
            return
        n[0] += 1
        if n[0] < 2:
            return                                                    # the first note as stock places it
        sp = u.reg_read(UC_ARM_REG_SP)
        if change == "step+1":
            u.reg_write(UC_ARM_REG_R2, u.reg_read(UC_ARM_REG_R2) + 1)
        elif change == "step-1":
            u.reg_write(UC_ARM_REG_R2, u.reg_read(UC_ARM_REG_R2) - 1)
        elif change == "offset+6":
            u.reg_write(UC_ARM_REG_R3, (u.reg_read(UC_ARM_REG_R3) + 6) & 0xFFFFFFFF)
        elif change == "start+8":
            st = struct.unpack("<I", bytes(u.mem_read(sp, 4)))[0]
            u.mem_write(sp, struct.pack("<I", (st + 8) & 0x7FF))
    h.uc.hook_add(UC_HOOK_CODE, hook, begin=PLACE, end=PLACE)
    wait_tick(h, 40)
    h.strum.clear()
    h.down(24)
    h.heartbeat(600)
    h.up(24)
    h.heartbeat(400)
    print(f"{label}: placed (before the change: note, step, offset, start) {[(p['note'], p['step'], p['off'], p['start']) for p in h.places]}")
    print(f"        words {[(c['note'], W(c['word'])['step'], W(c['word'])['micro'], W(c['word'])['start']) for c in h.commits]}")
    print(f"        written {written(h)}")


for q in (True, False):
    case(f"quantise {'on' if q else 'off'}, stock", q, None)
    case(f"quantise {'on' if q else 'off'}, step + 1", q, "step+1")
    case(f"quantise {'on' if q else 'off'}, step - 1", q, "step-1")
    case(f"quantise {'on' if q else 'off'}, start + 8", q, "start+8")
case("quantise off, offset + 6", False, "offset+6")
