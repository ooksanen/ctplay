# How a stock step-pad press edits a drum step (mode 1, Drum 1)
from drumlib import *
h = harness(); h.press(4); D = Drum(h, 0); p = D.playing()
before = D.arrays(p)
for pad, vel in ((1, 100), (0, 100), (2, 40)):
    h.pad(pad, vel)
    a = D.arrays(p)
    diff = [(o, before[o], a[o]) for o in range(0x80) if a[o] != before[o]]
    print(f'pad {pad} vel {vel}: changed (off, old, new) {[(hex(o), hex(x), hex(y)) for o, x, y in diff]}  hits {hits_of(a)}  store==pat {D.store_bytes()==a}')
    print('   leds 0-15', [hex(x) for x in h.leds()[:16]])
    before = a
