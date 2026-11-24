"""Run 3: re-hits without note-offs. Quantise off (Shift + Record), fixed velocity off, expanded view's sink.
A: a repeat at 6 ticks with no note-off ever; B: two note-ons in the same gap, then one more 2 ticks later, no off;
C: a note-on left hanging for a bar, then a repeat with offs; D: the finger holds pad 29 (src 28, real pad route)
while repeats go out with src 0, then the finger lets go."""
from lib2 import *

def setup():
    h = DH()
    p = drum_setup(h, mode=6)
    fixed_velocity(h, False)
    h.press(RECORD, shift=True)
    h.press(RECORD); h.press(PLAY)
    h.heartbeat(1)
    h.until_tick(h.ticks + (6 - h.ticks % 6) % 6)
    h.gate.clear(); h.writes.clear(); h.slot0.clear()
    return h, p

h, p = setup()
n = repeat(h, h.sink("expanded"), 6, 96, vels=[120, 100], off_mode="none")
h.heartbeat(20)
print(f"A no offs, {n} hits: pattern", fmt_hits(h.hits(0, p)))
print("  gate calls (first 6):", [g for g in h.gate if g[2] == 1][:6], " expanded [view+0xC] sounding mask", hex(h.r8(h.expanded_view() + 0xC)))

h, p = setup()
s = h.sink("expanded")
h.on(s, 1, 120); h.on(s, 1, 90)
h.heartbeat(1); t1 = h.ticks
h.until_tick(t1 + 2); h.on(s, 1, 70)
h.heartbeat(30)
print("B two ons in one gap then one 2 ticks later, no offs: pattern", fmt_hits(h.hits(0, p)))
print("  writes with pending:", [w for w in h.writes if w[5]], " gate:", [g for g in h.gate if g[2] == 1])

h, p = setup()
s = h.sink("expanded")
h.on(s, 1, 120)                     # left hanging
h.until_tick(h.ticks + 48)          # 8 steps later
n = repeat(h, s, 6, 48, vels=[90])
h.heartbeat(20)
print("C hanging on, then a repeat with offs from step 8: pattern", fmt_hits(h.hits(0, p)))

h, p = setup()
s = h.sink("expanded")
h.down(28, 127)                     # finger on pad 29 (real route), held
h.heartbeat(1)
n = repeat(h, s, 6, 30, vels=[80], src=0)
h.up(28)                            # finger lets go after the repeat's last off
h.heartbeat(5)
mask = h.r8(h.expanded_view() + 0xC)
leds = h.leds()
h.until_tick(h.ticks + 12)
s2 = h.ticks
repeat(h, s, 6, 12, vels=[60])
h.heartbeat(20)
print("D finger held on pad 29 + repeat src 0: pattern", fmt_hits(h.hits(0, p)))
print("  after both let go: sounding mask", hex(mask), "pad 29-32 LEDs", [hex(x) for x in leds[28:32]])
print("  gate calls:", [g for g in h.gate if g[2] == 1][:12])
