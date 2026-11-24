"""B3: Shift + a Patterns-view pad while playing = the pattern taken over at once (the chain store's byte at
store + 0x18 + t, written at 0x08050542, makes the engine listener reposition the track through 0x0802C240), not at
the pattern end. Logs every 0x0802C240 call (track, position, flag, caller) and the pass events after it."""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
from b_lib import *
from b_3_hand import fresh, pass_events

POS = 0x0802C240
for label, shift in (("tap", False), ("Shift + tap", True)):
    h = fresh()
    calls = []
    h.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: calls.append(
        (h.tick, u.reg_read(UC_ARM_REG_R1), u.reg_read(UC_ARM_REG_R2), u.reg_read(UC_ARM_REG_R3),
         hex(u.reg_read(UC_ARM_REG_LR) & ~1))), begin=POS, end=POS)
    h.press(13)
    h.play()
    print(f"== {label}: Play -> 0x0802C240 calls {calls[:3]}... ({len(calls)})")
    calls.clear()
    h.run_ticks(10)
    h.clear_logs()
    if shift:
        h.shift(True)
    h.pad(8)
    h.shift(False)
    print(f"  at tick {h.tick}: flag {h.chain_flag(0)} chain {h.chain(0)} playing {h.playing(0)}; 0x0802C240 calls {calls}")
    h.run_ticks(100)
    print("  Synth 1 pass events:", [(a[0], a[1]) for a in pass_events(h, 0)])
    print("  Synth 1 steps:", steps_played(h.t0, 0)[:12])
    print("  Synth 2 steps:", steps_played(h.t0, 1)[:3])
