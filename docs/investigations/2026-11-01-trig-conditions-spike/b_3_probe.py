"""B3 probe: what the Patterns view (button 13) and the Mixer view (14) write when pads are pressed while playing."""
import sys
from b_lib import *

def fresh():
    h = B()
    h.leds()
    set_tempo(h, bpm=240)
    configure(h, {t: dict(chain=(0, 0), pats={p: (7, 0, 3, 0) for p in range(8)}) for t in range(8)})
    return h

which = sys.argv[1]
h = fresh()
h.play()
h.run_ticks(10)
log = []
watch_writes(h, engine_regions(h), log)
print("before", snapshot(h))
if which == "patterns":
    h.press(13)
    for pad in (int(x) for x in sys.argv[2:]):
        log.clear()
        h.pad(pad)
        print(f"pad {pad} at tick {h.tick}: writes", [(n, hex(o), s, hex(v), hex(pc)) for _, n, o, s, v, pc in log if not n.endswith('hdr')][:20])
        print("   now", snapshot(h))
elif which == "mixer":
    h.press(14)
    for pad in (int(x) for x in sys.argv[2:]):
        log.clear()
        h.pad(pad)
        print(f"pad {pad} at tick {h.tick}: writes", [(n, hex(o), s, hex(v), hex(pc)) for _, n, o, s, v, pc in log if not n.endswith('hdr')][:20])
        print("   now", snapshot(h))
