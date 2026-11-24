"""Run 7: the same repeat on the PL15 image (built into this folder) as on stock: 3 ticks, quantise off, 191 ticks;
and 6 ticks with quantise on; patterns compared byte for byte. Also PL15's count-in (Shift + Clear -> count-in,
Record, Play): hits during its count are not recorded."""
import sys
from pathlib import Path
from slimbuild import build, paths
from lib2 import *
from notes import NoteHarness
out = Path(sys.argv[0]).resolve().parent / "pl15"
img = out / "circuittracks-4486-PL15.bin"
if not img.exists():
    build.build(paths.VERSIONS / "PL15.toml", out)
PL15 = img.read_bytes()

def rec(image, rate, quant_off):
    h = DH(image)
    p = drum_setup(h, mode=6)
    fixed_velocity(h, False)
    if quant_off:
        h.press(RECORD, shift=True)
    h.press(RECORD); h.press(PLAY)
    h.heartbeat(1)
    h.until_tick(h.ticks + (6 - h.ticks % 6) % 6)
    repeat(h, h.sink("expanded"), rate, 191, vels=[120, 110, 100, 90, 80, 70])
    h.heartbeat(20)
    return h.arrays(0, p), h.hits(0, p)

for rate, q in ((3, True), (6, False)):
    a, ha = rec(STOCK, rate, q); b, hb = rec(PL15, rate, q)
    print(f"rate {rate} quantise {'off' if q else 'on'}: stock == PL15: {a == b}; {len(ha)} steps;", fmt_hits(hb)[:120])

# PL15 count-in
h = DH(PL15)
p = drum_setup(h, mode=6)
fixed_velocity(h, False)
CLEAR = 23
for _ in range(4):        # Shift + Clear: off -> click -> count-in -> both; read the CTPlay state by its LED
    h.shift(True); led = h.leds()[55]; h.shift(False)
    if led == 0x32:
        break
    h.press(CLEAR, shift=True)
print("PL15 Shift + Clear LED", hex(led), "(0x32 = count-in)")
h.press(RECORD); h.press(PLAY)
print(" transport after Record, Play:", h.transport())
bpm = param(h, TEMPO_STORE, 0)
s = h.sink("expanded")
for _ in range(3):
    h.on(s, 1, 100); h.heartbeat(40); h.leds(); h.off(s, 1); h.heartbeat(40); h.leds()
print(" 3 hits during the count: transport", h.transport(), "pattern", fmt_hits(h.hits(0, p)), " gate on calls", sum(1 for g in h.gate if g[1] == 'on'), "slot0", len(h.slot0))
for i in range(5000):
    h.heartbeat(1)
    if i % 10 == 0:
        h.leds()                      # as test_countin: the LEDs drawn every 10 ms
    if h.transport()[0]:
        break
h.heartbeat(5)
for _ in range(3):
    h.on(s, 1, 100); h.heartbeat(40); h.off(s, 1); h.heartbeat(40)
print(" after the count: transport", h.transport(), "pattern", fmt_hits(h.hits(0, h.playing_pattern(0))))
