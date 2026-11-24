"""u3_window: no patch, rewrite rec+0x35 = 0 after every 1 ms heartbeat (a main_ms-style hook) vs the patched cave.
Hits sent just before a step boundary (step N + 5, +0..4 ms later) to land in the tick-0 window."""
import u2_override
from u2_override import *

class EveryMs(Run):
    pass

def run(image, label, everyms):
    r = Run(image, label); r.start()
    h = r.h
    if image is PATCHED:
        override_start(h)
    orig = h.heartbeat
    def hb(n=1):
        for _ in range(n):
            orig(1)
            if everyms:
                for d in range(4):
                    h.uc.mem_write(h.drec(d) + 0x35, b"\0")
    h.heartbeat = hb
    out = []
    for st, o, extra in ((4, 5, 0), (8, 5, 3), (12, 5, 6), (16, 5, 8), (20, 2, 0)):
        h.until_tick(r.t0 + 6 * st + o); h.heartbeat(extra)
        h.writes.clear()
        h.down(28, 90); h.heartbeat(15); h.up(28); h.heartbeat(5)
        h.until_tick(r.t0 + 6 * (st + 1) + 5)
        out.append((f"{st}+{o}+{extra}ms", outcome(h.writes)))
    print(label, out)
    print("   pattern:", r.result())

run(STOCK, "stock, quantise off by Shift+Record (reference)", False) if False else None
r = Run(STOCK, "ref"); r.h.press(RECORD, shift=True)
# reference: stock with quantise really off
def ref():
    rr = Run(STOCK, "ref"); rr.h.press(RECORD, shift=True); rr.start(); h = rr.h; out = []
    for st, o, extra in ((4, 5, 0), (8, 5, 3), (12, 5, 6), (16, 5, 8), (20, 2, 0)):
        h.until_tick(rr.t0 + 6 * st + o); h.heartbeat(extra)
        h.writes.clear(); h.down(28, 90); h.heartbeat(15); h.up(28); h.heartbeat(5)
        h.until_tick(rr.t0 + 6 * (st + 1) + 5)
        out.append((f"{st}+{o}+{extra}ms", outcome(h.writes)))
    print("stock, Shift+Record off (reference)", out); print("   pattern:", rr.result())
ref()
run(PATCHED, "patched cave + override", False)
run(STOCK, "no patch, rewrite 0 every ms", True)
