"""B3: what the look-ahead store [E + 0x70 + 4 t] shows during the pass before a hand-picked pattern takes over
(Patterns view tap at tick 20, 8-step loops), against the hand flag [E + 0x9C] parameter 8 + t."""
from b_lib import *
from b_3_hand import fresh

h = fresh()
h.press(13)
h.play()
h.run_ticks(20)
h.pad(16)                                   # Synth 1 pattern 2
rows = []
for _ in range(32):
    h.run_ticks(1)
    rows.append((h.tick, h.playing(0)[:2], h.lookahead(0)[:2], h.chain_flag(0)))
print("(tick, playing (pattern, step), look-ahead (pattern, step), hand flag) for Synth 1:")
for r in rows:
    print("  ", r)
