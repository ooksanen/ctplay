"""Run 2b: detail of run 2 — engine position (pattern, step, tick) of drum 1 at each hit sent, and every recorder
write that carried a pending velocity; why step 0's first hit is missing; store vs pattern."""
from lib2 import *

def pos(h, d=0):
    st = h.r32(ENGINE + 0x30 + 4 * (4 + d))
    return tuple(param(h, st, i) for i in range(3))

for rate, quant_off in ((6, True), (3, False), (6, False)):
    h = DH()
    p = drum_setup(h, mode=6)
    fixed_velocity(h, False)
    if quant_off:
        h.press(RECORD, shift=True)
    h.press(RECORD); h.press(PLAY)
    h.heartbeat(1)
    t0 = h.ticks
    h.until_tick(t0 + (6 - t0 % 6) % 6)
    h.writes.clear(); h.slot0.clear()
    log = []
    sink = h.sink("expanded")
    # same clock as lib.repeat, with the position at each hit
    start, last, n, sounding = h.ticks, h.ticks, 0, False
    vels = [120, 110, 100, 90, 80, 70]
    while h.ticks - start < 192:
        h.heartbeat(1)
        if h.ticks == last:
            continue
        last = h.ticks
        if (h.ticks - start) % rate == 0:
            if sounding:
                h.off(sink, 1)
            h.on(sink, 1, vels[n % 6]); n += 1; sounding = True
            log.append((h.ticks - start, pos(h)))
    h.off(sink, 1)
    h.heartbeat(100)
    print(f"--- rate {rate} quantise {'off' if quant_off else 'on'}")
    print(" first hits (rel tick, engine (pattern, step, tick)):", log[:5], "... last", log[-2:])
    wr = [w for w in h.writes if w[1] == 0 and w[5]]
    print(" writes with pending (abs tick, drum, pattern, step, micro, vel): first", wr[:5], "last", wr[-3:])
    print(" start abs tick", start)
    print(" pattern:", fmt_hits(h.hits(0, p))[:200])
    a, s = h.arrays(0, p), h.store_words(0)
    for k in ("vel", "prob", "micro", "flip"):
        if a[k] != s[k]:
            print("  store differs in", k, "pattern", a[k].hex(), "store", s[k].hex())
