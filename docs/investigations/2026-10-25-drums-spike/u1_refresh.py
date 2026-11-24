"""u1_refresh: what are the drum recorder's stores, when does [rec+0x35] refresh, which value does slot 5 read."""
import time
from lib2 import *
from unicorn.arm_const import UC_ARM_REG_R4, UC_ARM_REG_R9, UC_ARM_REG_R1, UC_ARM_REG_R5

LISTEN = 0x0803FE24
TEST_AT = 0x0803FE74      # r4 = [[rec+0xC] p2], sb(r9) = [[rec+0x20] p0]
REFRESH = 0x0803FE90      # strb r0,[r7,#1]
SLOT5_READ = 0x0803F9BA   # after ldrb r1,[r5,#0x35]

h = DH()
uc = h.uc
log = []
d0 = None


def ev(u, a, s, dd):
    r5 = u.reg_read(UC_ARM_REG_R5)
    if r5 != h.drec(0):
        return
    if a == TEST_AT:
        log.append(("test", h.ticks, u.reg_read(UC_ARM_REG_R4), u.reg_read(UC_ARM_REG_R9)))
    elif a == REFRESH:
        log.append(("refresh", h.ticks, u.reg_read(UC_ARM_REG_R0)))
    elif a == SLOT5_READ:
        log.append(("slot5", h.ticks, u.reg_read(UC_ARM_REG_R1)))
for a in (TEST_AT, REFRESH, SLOT5_READ):
    uc.hook_add(UC_HOOK_CODE, ev, begin=a, end=a)

p = drum_setup(h, mode=6)
for d in range(4):
    r = h.drec(d)
    print(f"drum {d} rec {r:#x} vt {h.r32(r):#x} bytes +0x30..+0x40:", bytes(uc.mem_read(r + 0x30, 0x10)).hex(" "))
r = h.drec(0)
for off in (0xC, 0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x2C, 0x30, 0x4C, 0x50):
    st = h.r32(r + off)
    print(f"  +{off:#x} store {st:#x}  p0..3", [param(h, st, i) for i in range(3)] if 0x20000000 <= st < 0x20050000 else "")
print("PLAY_STORE", hex(PLAY_STORE), "settings bit12", h.quant_setting(), "flag", [h.quantise_flag(d) for d in range(4)])


def show(label):
    print(f"[{label}] tick {h.ticks} bit12 {h.quant_setting()} flags {[h.quantise_flag(d) for d in range(4)]} transport {h.transport()}")


show("start")
h.press(RECORD, shift=True); show("after Shift+Record #1")
h.heartbeat(50); show("stopped, +50 ms")
h.press(RECORD, shift=True); show("after Shift+Record #2")
h.press(RECORD, shift=True); show("after Shift+Record #3 (bit should be 'off')")
log.clear()
h.press(PLAY); show("after Play (not recording)")
h.heartbeat(40); show("+40 ms playing")
print(" log:", [x for x in log if x[0] != "test"][:20])
print(" tests:", sorted(set((x[2], x[3]) for x in log if x[0] == "test")))
log.clear()
h.press(RECORD); show("after Record")
h.heartbeat(40); show("+40 ms recording")
print(" log:", [x for x in log if x[0] != "test"][:20])
print(" tests:", sorted(set((x[2], x[3]) for x in log if x[0] == "test")))
log.clear()
h.press(RECORD, shift=True); show("Shift+Record while recording")
h.heartbeat(40); show("+40 ms")
print(" log:", [x for x in log if x[0] != "test"][:30])
print(" tests:", sorted(set((x[2], x[3]) for x in log if x[0] == "test")))
