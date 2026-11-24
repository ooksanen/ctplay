"""B3: who writes the chain store's per-track bytes at store + 0x18 (the engine listener 0x0802B926 repositions a
track at once when one is set, instead of waiting for the pattern end). Tries Patterns-view gestures while playing."""
from harness import MGR
from b_lib import *
from b_3_hand import fresh

def attempt(name, fn):
    h = fresh()
    h.play(); h.run_ticks(10)
    st = h.r32(E + 0x9C)
    log = []
    watch_writes(h, {"st+0x18": (st + 0x18, 8)}, log)
    h.clear_logs()
    fn(h)
    h.run_ticks(20)
    print(f"{name}: writes {[(hex(o), hex(v), hex(pc)) for _, _, o, s, v, pc in log]}; Synth 1 playing {h.playing(0)}, chain {h.chain(0)}")

attempt("Patterns tap pad 8", lambda h: (h.press(13), h.pad(8)))
attempt("Patterns Shift + pad 8", lambda h: (h.press(13), h.shift(True), h.pad(8), h.shift(False)))
attempt("Patterns tap pad 8 twice", lambda h: (h.press(13), h.pad(8), h.pad(8)))
attempt("Patterns pad 8 held 300 ms", lambda h: (h.press(13), h.down(8), h.heartbeat(300), h.up(8)))
for b in (16,):                                   # 17 (Play) would stop the clock
    attempt(f"Patterns, button {b} held + pad 8", lambda h, b=b: (h.press(13), h.call(0x08033320, MGR, b), h.pad(8), h.call(0x0803381A, MGR, b)))
