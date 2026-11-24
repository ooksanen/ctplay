"""Run 2: repeats through the expanded view's live sink from between heartbeats (the arp clock's place), Record
armed and playing (real Record + Play), 2 bars (192 ticks) over a 32-step pattern, at 6 / 3 / 2 / 1 ticks; quantise
on (the dump) and off (Shift + Record); fixed velocity off so velocities can be read (falling 120..)."""
import time
from lib2 import *

def run(rate, quant_off, off_mode="before"):
    h = DH()
    p = drum_setup(h, mode=6)
    fixed_velocity(h, False)
    if quant_off:
        h.press(RECORD, shift=True)
    h.press(RECORD); h.press(PLAY)
    assert h.transport() == (1, 1, 0), h.transport()
    # start the clock on a step boundary: wait until the player's next tick that is a step start
    h.heartbeat(1)
    t0 = h.ticks
    h.until_tick(t0 + (6 - t0 % 6) % 6)  # ticks counted from Play: tick 0 = Play
    h.writes.clear(); h.slot0.clear(); assert h.ticks % 6 == 0
    vels = [120, 110, 100, 90, 80, 70]
    n = repeat(h, h.sink("expanded"), rate, 191, vels=vels, off_mode=off_mode, start=h.ticks)
    h.heartbeat(100)
    got = h.hits(0, p)
    mp = h.mirrored_pattern(0); st = (h.store_hits(0) == h.hits(0, mp))
    wr = [w for w in h.writes if w[1] == 0 and w[5]]
    print(f"rate {rate} ticks, quantise {'off' if quant_off else 'on'}, offs {off_mode}: {n} hits sent, {len(h.slot0)} reached the recorder slot 0, {len(wr)} recorder writes with a pending velocity, {len(got)} steps hit")
    print("   pattern:", fmt_hits(got))
    print("   other drums / patterns written:", sorted({(w[1], w[2]) for w in h.writes if w[5]}), " store mirrors pattern", mp, "and equals it:", st)
    return h

t = time.time()
for q in (False, True):
    for rate in (6, 3, 2, 1):
        run(rate, q)
run(6, False, "half")
run(3, True, "half")
print("time", round(time.time() - t))
