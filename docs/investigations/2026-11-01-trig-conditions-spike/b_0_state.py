"""B0: the snapshot's sequencer state, and how fast the real route runs."""
import time
from b_lib import *

h = B()
h.leds()
print("transport", h.transport(), "tempo", param(h, TEMPO_STORE, 0))
print("scene", h.scene(), "scene chain (first, last, pending)", h.scene_chain())
for t in range(8):
    p = h.playing(t)
    print(f"track {t}: playing {p} lookahead {h.lookahead(t)} chain {h.chain(t)} flag {h.chain_flag(t)} "
          f"queued {h.queued(t).hex()} settings(p) {h.settings(t, p[0])} 0x94 {h.r8(E + 0x94 + t)}")
print("E+0xFC", h.r8(E + 0xFC))
t0 = time.time()
h.play()
print("after Play: transport", h.transport(), "ticks", h.tick)
n0 = h.tick
t1 = time.time()
h.heartbeat(500)
dt = time.time() - t1
print(f"500 heartbeats: {dt:.1f}s, ticks {h.tick - n0}")
for t in range(8):
    print(t, h.playing(t))
