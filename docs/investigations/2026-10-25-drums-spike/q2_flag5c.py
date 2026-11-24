# Q2c: hunt the writer of the shared store 0x20039DE0 (the editor's [+0x5C]): write-watch its buffers and header,
# drive many real routes (Shift + every button, buttons held + pads, playing, Patterns view while playing).
from unicorn import UC_HOOK_MEM_WRITE, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_LR
from drumlib import *
from harness import BTN_PRESS, BTN_RELEASE
S = 0x20039DE0

def setup():
    h = harness(); log = []
    b0, b1 = h.r32(S + 0xC), h.r32(S + 0x10)
    def w(uc, acc, addr, size, val, d):
        log.append((addr, val, uc.reg_read(UC_ARM_REG_PC)))
    for a in (b0, b1):
        h.uc.hook_add(UC_HOOK_MEM_WRITE, w, begin=a, end=a + 3)
    h.uc.hook_add(UC_HOOK_MEM_WRITE, w, begin=S + 4, end=S + 11)   # read mask, dirty
    return h, log

def run(name, fn):
    h, log = setup()
    try:
        fn(h)
    except AssertionError as e:
        print(name, 'ERR', e); return
    if log:
        print(f'{name}: {len(log)} writes, first {[(hex(a), hex(v), hex(pc)) for a, v, pc in log[:6]]}  p0 now {pget(h, S, 0)}')
    return h

def btn_down(h, b): h.call(BTN_PRESS, MGR, b)
def btn_up(h, b): h.call(BTN_RELEASE, MGR, b)

found = 0
for b in range(28):
    run(f'Shift + button {b} (from Drum 1)', lambda h, b=b: (h.press(4), h.press(b, shift=True)))
for hold in (8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 22, 23, 24, 25, 26, 27):
    for pre in ([4], [4, 13], [0]):
        def f(h, hold=hold, pre=pre):
            for b in pre: h.press(b)
            btn_down(h, hold)
            for p in (0, 5, 16, 28):
                h.pad(p)
            btn_up(h, hold)
        run(f'{pre} hold button {hold} + pads 0,5,16,28', f)
# playing: Play, heartbeats, Patterns view pattern change while playing, held pattern pads
def play(h):
    h.press(4); h.press(17); h.heartbeat(50)
    h.press(13); h.down(12); h.heartbeat(20); h.down(20); h.heartbeat(20); h.up(20); h.up(12); h.heartbeat(200)
run('playing + Patterns view pads 12/20 held', play)
def chain(h):
    h.press(13); h.down(4); h.down(20); h.up(20); h.up(4)
run('Patterns view chain 4..20 (stopped)', chain)
# A knob turn in drum views
for m in ([4], [4, BTN_NOTE], [4, BTN_VEL]):
    run(f'{m} knobs', lambda h, m=m: ([h.press(b) for b in m], [h.knob(k, 5) for k in range(8)]))
