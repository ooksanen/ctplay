# Q2b: what writes [editor+0x24] (per drum) and 0x20039DE0 (shared): hook stock's param_wptr for those stores while
# driving the real routes, with the value of p0 while the pad / button is still held.
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_LR
from drumlib import *
from harness import PAD_PRESS, PAD_RELEASE, BTN_PRESS, BTN_RELEASE

def setup():
    h = harness(); D = Drum(h, 0)
    F24, F5C = h.r32(D.editor + 0x24), 0x20039DE0
    log = []
    def hk(uc, a, s, d):
        r0 = uc.reg_read(UC_ARM_REG_R0)
        if r0 in (F24, F5C, D.pos):
            log.append(({F24: 'ed+24', F5C: '39DE0', D.pos: 'pos'}[r0], uc.reg_read(UC_ARM_REG_R1), uc.reg_read(UC_ARM_REG_LR) & ~1))
    h.uc.hook_add(UC_HOOK_CODE, hk, begin=PARAM_WPTR, end=PARAM_WPTR)
    return h, D, F24, F5C, log

def flags(h, D, F24, F5C):
    return f'ed+24 {pget(h, F24, 0)} 39DE0 {pget(h, F5C, 0)} mirrored {D.mirrored()} playing {D.playing()}'

def held(name, pre, kind, x):
    h, D, F24, F5C, log = setup()
    for b in pre:
        h.press(b)
    log.clear()
    if kind == 'pad':
        h.down(x); during = flags(h, D, F24, F5C); w1 = list(log); log.clear(); h.up(x)
    else:
        h.call(BTN_PRESS, MGR, x); during = flags(h, D, F24, F5C); w1 = list(log); log.clear(); h.call(BTN_RELEASE, MGR, x)
    after = flags(h, D, F24, F5C)
    if w1 or log:
        print(f'{name}: held -> {during}  writes {[(n, k, hex(lr)) for n, k, lr in w1]}\n{"":20s}released -> {after} writes {[(n, k, hex(lr)) for n, k, lr in log]}')
    return w1, log

# every button held, from Drum 1's default view
for b in range(28):
    if b in (4,):
        continue
    held(f'Drum 1, button {b}', [4], 'btn', b)
# every pad held, in Drum 1's views
for pre, nm in (([4], 'Drum 1 mode 1'), ([4, BTN_NOTE], 'Drum 1 mode 6'), ([4, BTN_VEL], 'Drum 1 velocity'),
                ([4, BTN_GATE], 'Drum 1 gate'), ([4, BTN_PSET], 'Drum 1 pattern settings'), ([4, BTN_PSET, BTN_PSET], 'Drum 1 probability'),
                ([4, 13], 'Patterns view'), ([0], 'Synth 1 mode 1')):
    for p in range(32):
        held(f'{nm}, pad {p}', pre, 'pad', p)
