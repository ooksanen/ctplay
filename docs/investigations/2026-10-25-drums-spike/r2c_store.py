"""Run 2c: the step store (editing copy) while the recorded pattern is still the mirrored one: 3-tick repeat,
quantise off, 96 ticks (half the pattern), then compare store and pattern 0; and a stock edit afterwards
(clear step via 0x0803E18A on the selected step) must keep the recorded hits (no lost raw write)."""
from lib2 import *
h = DH()
p = drum_setup(h, mode=6)
fixed_velocity(h, False)
h.press(RECORD, shift=True); h.press(RECORD); h.press(PLAY)
h.heartbeat(1); h.until_tick(h.ticks + (6 - h.ticks % 6) % 6)
repeat(h, h.sink("expanded"), 3, 96, vels=[120, 90])
h.heartbeat(5)
print("mirrored", h.mirrored_pattern(0), "playing", h.playing_pattern(0), "store +0x18 == pattern + 0xA8:", h.r32(h.store(0) + 0x18) == h.base(0) + PAT * p + 0xA8)
print("pattern:", fmt_hits(h.hits(0, p)))
print("store == pattern (all 4 arrays):", all(h.arrays(0, p)[k] == h.store_words(0)[k] for k in ("vel", "prob", "micro", "flip")))
# a stock commit of the store (as any stock edit): touch-all + commit -> the editor listener rewrites the pattern
before = h.arrays(0, p)
h.call(0x08035456, h.store(0)); h.call(PARAM_COMMIT, h.store(0))
print("after a stock store commit the pattern is unchanged:", h.arrays(0, p) == before)
