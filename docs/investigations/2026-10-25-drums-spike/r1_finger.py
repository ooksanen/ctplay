"""Run 1: baseline, real finger presses through the pad route while playing with Record armed (real Record + Play
buttons). Expanded view (mode 6) pad id 28 = pad 29 = drum 1; and the sample view (mode 1) pad id 16. Quantise as in
the dump (on), then off through Shift + Record if that is stock's route."""
import time
from lib2 import *

def run(mode, pad, label, quant_off=False):
    h = DH()
    p = drum_setup(h, mode=mode)
    if quant_off:
        b = h.quant_setting(); h.press(RECORD, shift=True); print("  Shift+Record: setting bit12", b, "->", h.quant_setting(), "transport", h.transport())
    h.press(RECORD); h.press(PLAY)
    print(f"[{label}] transport after Record, Play: {h.transport()}  pattern {p}")
    h.heartbeat(2)
    t_start = h.ticks
    out = []
    # press at tick offsets inside steps: step 2 tick 0 (on the step), step 5 tick 2, step 9 tick 4 (late half)
    for step, off in ((2, 0), (5, 2), (9, 4)):
        h.until_tick(t_start + 6 * step + off)
        tk = h.ticks - t_start
        h.slot0.clear(); h.writes.clear()
        h.down(pad, 90)
        h.heartbeat(15)
        h.up(pad)
        h.heartbeat(80)
        out.append((step, off, tk, list(h.slot0), list(h.writes)))
    h.heartbeat(200)
    for step, off, tk, s0, w in out:
        print(f"  press at tick {tk} (step {step} + {off}): slot0 {s0}  write(tick, drum, pattern, step, micro, pending) {w}")
    print("  quantise flag [rec+0x35]", h.quantise_flag(), " pattern:", fmt_hits(h.hits(0, p)))
    print("  store  :", fmt_hits(h.store_hits(0)))
    return h

t0 = time.time()
run(6, 28, "expanded pad 29, quantise on")
run(6, 28, "expanded pad 29, quantise off", quant_off=True)
run(1, 16, "sample view pad 17, quantise on")
print("time", round(time.time() - t0))
