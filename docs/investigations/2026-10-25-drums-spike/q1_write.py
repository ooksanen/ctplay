# Q1: CTPlay-style write into Drum 1's mirrored (playing) pattern vs stock pad entry; stock edits after it; raw control;
# non-mirrored pattern; Undo.
from drumlib import *
HITS = [0, 3, 6, 9, 12]
IMG = euclid_img(HITS)

def fresh():
    h = harness(); h.press(4); D = Drum(h, 0)
    assert state(h)['halves'] == ('drum step', 'drum sample/Preset')
    return h, D, D.playing()

def L16(h):
    return ' '.join(f'{x:02x}' for x in h.leds()[:16])

def show(tag, h, D, p):
    a = D.arrays(p)
    print(f'[{tag}] hits {hits_of(a)} store==pattern {D.store_bytes()==a}\n      leds {L16(h)}')
    return a

# --- A. stock pad entry of the same hits (from the snapshot's 0,3,4,7,8,11,12,15)
h, D, p = fresh()
print('pattern', p, 'mirrored', D.mirrored(), 'is_mirrored', D.is_mirrored(p))
orig = D.arrays(p); orig_leds = L16(h)
print('original  ', fmt(orig)); print('orig leds ', orig_leds)
for pad in (4, 7, 8, 11, 15, 6, 9):
    h.pad(pad)
stockA = show('A stock pads', h, D, p); print('      ', fmt(stockA))
ledsA = L16(h)
# same bytes as A, but written by our path into a fresh harness: LEDs must match A's
h2, D2, _ = fresh(); D2.write(p, stockA)
print(f'[A2 our write of A\'s bytes] equal bytes {D2.arrays(p)==stockA} leds equal to A: {L16(h2)==ledsA}')

# --- B. our write, store synced, editor detached
for detach in (True, False):
    h, D, p = fresh()
    how = D.write(p, IMG, sync=True, detach=detach)
    a = show(f'B write ({how}, detach={detach})', h, D, p)
    print('       bytes == IMG', a == IMG)
    h.pad(15)                                    # stock edit through the real route: add step 15
    a = show('  then stock pad 15', h, D, p)
    print('       ours kept:', all(a[s] == 100 and a[0x60+s] == 1 for s in HITS), 'hits == HITS+[15]:', hits_of(a) == HITS + [15])
    print('       ', fmt(a))
    if detach:
        h.pad(3)                                 # remove one of ours by stock
        a = show('  then stock pad 3 (remove)', h, D, p)

# --- B2. LED colours: our hits with the stock velocity 0x60 vs 100, flip 08
for kw in (dict(vel=0x60), dict(flip=8), dict(vel=0x60, flip=8)):
    h, D, p = fresh(); D.write(p, euclid_img(HITS, **kw)); print(f'[B2 {kw}] leds {L16(h)}')

# --- C. Velocity view edit after our write
h, D, p = fresh(); D.write(p, IMG)
h.press(BTN_VEL); print('[C] after Velocity:', state(h))
h.pad(3)                                         # select step 3 on the top half?
print('   after pad 3: hits', hits_of(D.arrays(p)), 'sel step', pget(h, D.pos, 1))
h.pad(16 + 2)                                    # a velocity pad in the bottom half
a = D.arrays(p)
print('   after pad 18: vel', a[:16].hex(), 'micro', a[0x60:0x70].hex(), 'hits', hits_of(a), 'store==pat', D.store_bytes()==a)
print('   ours kept (other than 3):', all(a[s] == 100 and a[0x60+s] == 1 for s in HITS if s != 3))

# --- D. negative control: raw write, no store sync
h, D, p = fresh()
D.write(p, IMG, sync=False)
a = show('D raw only', h, D, p)
h.pad(15)
a = show('  then stock pad 15', h, D, p)
print('       ours undone; result = the store\'s stale copy (the original) with step 15 toggled off:', a[:15] == orig[:15] and a[0x60:0x6F] == orig[0x60:0x6F], '| hits', hits_of(a))
print('       diff vs original', [(hex(o), orig[o], a[o]) for o in range(0x80) if a[o] != orig[o]])

# --- E. non-mirrored pattern: raw write to pattern 5, then a stock edit of the mirrored one
h, D, p = fresh(); q = 5
print('[E] pattern', q, 'is_mirrored', D.is_mirrored(q))
others0 = {r: D.arrays(r) for r in range(8) if r not in (p, q)}
print('   write path', D.write(q, IMG))
h.pad(15); h.pad(1)
print('   after stock pads 15, 1 on pattern', p, ': pattern 5 == IMG', D.arrays(q) == IMG, '| pattern', p, 'hits', hits_of(D.arrays(p)))
print('   patterns other than', p, 'and', q, 'untouched:', all(D.arrays(r) == v for r, v in others0.items()))

# --- F. Write then Undo (swap back the saved 128 B by the same path)
h, D, p = fresh()
saved = D.arrays(p); led0 = L16(h)
D.write(p, IMG)
D.write(p, saved)
print(f'[F undo] bytes restored {D.arrays(p)==saved} store==pat {D.store_bytes()==saved} leds restored {L16(h)==led0}  {L16(h)}')
h.pad(15)
print('   after stock pad 15: hits', hits_of(D.arrays(p)))
