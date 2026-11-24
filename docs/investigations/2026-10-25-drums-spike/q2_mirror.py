# Q2d: when does the editor's mirrored pattern ([editor+0x20] p0) differ from the playing one?
import time
from drumlib import *
S = 0x20039DE0
def st(h, D):
    nxt = pget(h, h.r32(ENGINE + 0x70 + 4 * 4), 0)
    return (f'playing {D.playing()} next {nxt} mirrored {D.mirrored()} store-mirrors-pattern '
            f'{[q for q in range(8) if D.is_mirrored(q)]} step {pget(h, D.play, 1)} ed+24 {D.flag24()} 39DE0 {pget(h, S, 0)}')

def chain(h):                        # Patterns view: hold pattern 1's pad, press pattern 2's -> chain 1-2 for Drum 1
    h.press(13); h.down(4); h.down(12); h.up(12); h.up(4); h.press(4)

def until_change(h, D, ms=6000):
    p0 = D.playing()
    for t in range(ms):
        h.heartbeat(1)
        if D.playing() != p0:
            return t + 1
    return None

for toggle in (False, True):
    h = harness(); D = Drum(h, 0); h.press(4)
    if toggle:
        h.press(13, shift=True)
    print(f'--- Shift+Patterns pressed: {toggle}:', st(h, D))
    chain(h); print('after chain 1-2 (stopped):', st(h, D))
    h.press(17); t0 = time.time()
    t = until_change(h, D); print(f'playing, pattern changed after {t} ms ({time.time()-t0:.0f} s real):', st(h, D))
    print('   LEDs 0-15', ' '.join(f'{x:02x}' for x in h.leds()[:16]))
    # write path check in this state: which pattern would the store path hit?
    t = until_change(h, D); print(f'next change after {t} ms:', st(h, D))
    if toggle:
        # a stock step edit now: which pattern gets it?
        a0, a1 = D.arrays(0), D.arrays(1)
        h.pad(1)
        print('   stock pad 1 changed pattern 0:', D.arrays(0) != a0, 'pattern 1:', D.arrays(1) != a1)

# step pad held across a pattern change
h = harness(); D = Drum(h, 0); h.press(4); chain(h); h.press(17)
h.heartbeat(1000); print('--- step held: before', st(h, D))
h.down(5); t = until_change(h, D); print(f'pad 5 held, pattern changed after {t} ms:', st(h, D))
h.up(5); print('released:', st(h, D)); h.heartbeat(5); print('5 ms later:', st(h, D))

# playing, pattern chosen in the Patterns view (queued: next != playing until the loop end)
h = harness(); D = Drum(h, 0); h.press(4); h.press(17); h.heartbeat(300)
h.press(13); h.pad(20); print('--- playing, Patterns pad 20 (pattern 3):', st(h, D))
t = until_change(h, D); print(f'changed after {t} ms:', st(h, D))
