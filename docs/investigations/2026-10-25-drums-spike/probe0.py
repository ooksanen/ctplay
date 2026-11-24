import time
from drumlib import *
t0 = time.time()
h = harness()
print('build', round(time.time() - t0, 1), 's')
print('initial', state(h))
for d in range(4):
    D = Drum(h, d)
    print(f'drum {d}: base {D.base:#x} store {D.store:#x} editor {D.editor:#x} playing {D.playing()} mirrored {D.mirrored()} '
          f'f24 {D.flag24()} f5c {D.flag5c()} st+18 {h.r32(D.store+0x18):#x} [ed+24]={h.r32(D.editor+0x24):#x} [ed+5c]={h.r32(D.editor+0x5c):#x}')
h.press(4)
print('after Drum 1', state(h))
D = Drum(h, 0)
p = D.playing()
print('playing', p, 'mirrored', D.mirrored(), 'is_mirrored', D.is_mirrored(p))
for q in range(8):
    print(q, hits_of(D.arrays(q)))
print(fmt(D.arrays(p)))
print('store==pattern', D.store_bytes() == D.arrays(p))
L = h.leds()
print('leds 0-31', [hex(x) for x in L[:32]])
print('time', round(time.time() - t0, 1))
