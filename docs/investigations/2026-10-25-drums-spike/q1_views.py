# Q1 extra: does the store write refresh the velocity / gate-micro / probability views' LEDs?  L_live = write while the
# view is open (step 3 selected); L_fresh = write first, then open the view and select step 3 (painted from scratch).
from drumlib import *
IMG = bytearray(euclid_img([0, 3, 6, 9, 12]))
IMG[3] = 40; IMG[0x20 + 3] = 2; IMG[0x60 + 3] = 0b100101      # step 3: vel 40, prob 2, micro 0/2/5 (a roll)
IMG = bytes(IMG)
for name, btns in (('mode 1', []), ('velocity', [BTN_VEL]), ('gate/micro', [BTN_GATE]), ('probability', [BTN_PSET, BTN_PSET])):
    a = harness(); a.press(4); [a.press(b) for b in btns]; a.pad(3); D = Drum(a, 0)
    before = a.leds()[:32]
    D.write(D.playing(), IMG); live = a.leds()[:32]
    for sync in (False,):
        r = harness(); r.press(4); R = Drum(r, 0); R.write(R.playing(), IMG, sync=False); [r.press(b) for b in btns]; r.pad(3); rawv = r.leds()[:32]
    f = harness(); f.press(4); F = Drum(f, 0); F.write(F.playing(), IMG); [f.press(b) for b in btns]; f.pad(3); fresh = f.leds()[:32]
    print(f'{name:12s} mode {mode(a)} {state(a)["halves"]}: live==fresh {live == fresh}; changed by the write {live != before}')
    print('   before', ' '.join(f'{x:02x}' for x in before)); print('   live  ', ' '.join(f'{x:02x}' for x in live))
    print('   fresh ', ' '.join(f'{x:02x}' for x in fresh))
    print('   raw-only then open (store stale)', ' '.join(f'{x:02x}' for x in rawv))
