"""u2_override: the drum recorders' quantise cache [rec+0x35] vs the setting, and a temporary unquantised override.

Patch (patched image only): 0x0803FE8C `eor.w r0,r0,#1` (the cache refresh's last step before `strb r0,[r7,#1]`)
-> `bl CAVE`. CAVE: r0 ^= 1 (stock's instruction); if r5 is drum recorder d ([0x2003C184 + 4d]):
shadow[d] = r0 (stock's value); if override[d]: r0 = 0. RAM: override[d] = OVR + d, shadow[d] = OVR + 4 + d.
"""
import struct
import sys
import thumb as T
from lib2 import *

SITE = 0x0803FE8C
CAVE = 0x0805CE00
OVR = 0x2006C000


def build_patched():
    img = bytearray(STOCK)
    off = lambda a: a - 0x08010000
    eor = bytes(img[off(SITE):off(SITE) + 4])
    assert eor.hex() == "80f00100", eor.hex()          # eor.w r0, r0, #1
    a = CAVE
    code = bytearray()

    def emit(b):
        nonlocal a
        code.extend(b); a += len(b)
    emit(eor)
    emit(T.movw(2, 0xC184)); emit(T.movt(2, 0x2003))   # r2 -> drum recorder table
    emit(T.movs_imm(3, 0))
    loop = a
    emit(T.ldr_imm(1, 2, 0))
    emit(T.cmp_reg(1, 5))
    beq_at = a; emit(b"\0\0")                          # beq found (patched below)
    emit(T.adds_imm8(2, 4)); emit(T.adds_imm8(3, 1)); emit(T.cmp_imm(3, 4))
    emit(T.b_cond(a, loop, "ne"))
    emit(T.bx_lr())                                    # not a drum recorder: stock's value
    found = a
    code[beq_at - CAVE:beq_at - CAVE + 2] = T.b_cond(beq_at, found, "eq")
    emit(T.movw(1, OVR & 0xFFFF)); emit(T.movt(1, OVR >> 16))
    emit(T.adds_reg(1, 1, 3))                          # r1 = OVR + d
    emit(T.strb_imm(0, 1, 4))                          # shadow[d] = stock's value
    emit(T.ldrb_imm(2, 1, 0))                          # override[d]
    cbz_at = a; emit(b"\0\0")
    emit(T.movs_imm(0, 0))
    done = a
    emit(T.bx_lr())
    code[cbz_at - CAVE:cbz_at - CAVE + 2] = T.cbz(cbz_at, done, 2)
    img.extend(b"\xFF" * (off(CAVE) - len(img)))
    img.extend(code)
    img[off(SITE):off(SITE) + 4] = T.bl(SITE, CAVE)
    return bytes(img), bytes(code)


PATCHED, CODE = build_patched()


# --- the firmware side of the override (run from the Main task, e.g. the main_ms hook) ---
def override_start(h):
    for d in range(4):
        r = h.drec(d)
        h.uc.mem_write(OVR + 4 + d, bytes([h.r8(r + 0x35)]))   # shadow = stock's current cache
        h.uc.mem_write(r + 0x35, b"\0")
        h.uc.mem_write(OVR + d, b"\1")


def override_end(h):
    for d in range(4):
        h.uc.mem_write(OVR + d, b"\0")
        h.uc.mem_write(h.drec(d) + 0x35, bytes([h.r8(OVR + 4 + d)]))


class Run:
    def __init__(self, image, label):
        self.h = DH(image)
        self.label = label
        self.p = drum_setup(self.h, mode=6)
        self.trace = []                    # (tick, flags) whenever the drum-0 flag changes
        h = self.h
        if image is PATCHED:
            h.uc.mem_write(OVR, bytes(8))

    def start(self):
        h = self.h
        h.press(RECORD); h.press(PLAY)
        h.heartbeat(2)
        self.t0 = h.ticks

    def hit(self, step, off, pad=28):
        h = self.h
        h.until_tick(self.t0 + 6 * step + off)
        h.writes.clear()
        h.down(pad, 90); h.heartbeat(15); h.up(pad); h.heartbeat(5)
        h.until_tick(self.t0 + 6 * (step + 1) + 4)       # past the quantised write of a late hit
        return list(h.writes)

    def state(self):
        h = self.h
        return f"bit12={h.quant_setting()} rec+0x35={[h.quantise_flag(d) for d in range(4)]} tick={h.ticks - getattr(self, 't0', 0)} LED48={h.leds()[48]:#04x}"

    def dump(self):
        h = self.h
        for d in range(4):
            print(f"    drum {d} +0x30..+0x3F:", bytes(h.uc.mem_read(h.drec(d) + 0x30, 0x10)).hex(" "))

    def result(self):
        self.h.heartbeat(150)
        return fmt_hits(self.h.hits(0, self.p))

    def notes_flags(self):
        return [self.h.r8(self.h.r32(0x2003C174 + 4 * t) + 0x35) for t in range(4)]


def outcome(ws):
    return ["s%d/micro%d" % (w[3], w[4]) for w in ws if w[1] == 0 and w[5]]


def main():
    print("cave", CAVE and hex(CAVE), CODE.hex(), len(CODE), "B; site", hex(SITE), T.bl(SITE, CAVE).hex())

    print("\n== S0 stock, quantise on (snapshot) ==")
    r = Run(STOCK, "S0"); print("  ", r.state()); r.dump(); r.start()
    for st, o in ((5, 2), (9, 4)):
        print(f"   hit step {st}+{o}:", outcome(r.hit(st, o)), r.state())
    print("   pattern:", r.result())

    print("\n== S1 stock, Shift+Record while stopped (quantise off) ==")
    r = Run(STOCK, "S1"); r.h.press(RECORD, shift=True); print("   after Shift+Record:", r.state()); r.dump()
    r.start(); print("   after Record, Play:", r.state())
    for st, o in ((5, 2), (9, 4)):
        print(f"   hit step {st}+{o}:", outcome(r.hit(st, o)), r.state())
    print("   pattern:", r.result())

    print("\n== S2 stock, direct write rec+0x35 = 0 mid-step (no patch) ==")
    r = Run(STOCK, "S2"); r.start()
    r.h.until_tick(r.t0 + 6 * 5 + 1)
    for d in range(4):
        r.h.uc.mem_write(r.h.drec(d) + 0x35, b"\0")
    print("   written at step 5+1:", r.state())
    print("   hit step 5+2:", outcome(r.hit(5, 2)), r.state())
    print("   hit step 9+4:", outcome(r.hit(9, 4)), r.state())
    print("   pattern:", r.result())

    print("\n== S3 patched, override never set: same as S0 ==")
    r = Run(PATCHED, "S3"); r.start()
    for st, o in ((5, 2), (9, 4)):
        print(f"   hit step {st}+{o}:", outcome(r.hit(st, o)), r.state())
    print("   pattern:", r.result(), " shadow", bytes(r.h.uc.mem_read(OVR + 4, 4)).hex())

    print("\n== S4 patched: stock quantise on, override, hits, restore, hits ==")
    r = Run(PATCHED, "S4"); r.start(); print("   before:", r.state())
    r.h.until_tick(r.t0 + 6 * 3 + 3)
    override_start(r.h); print("   override at step 3+3:", r.state())
    for st, o in ((5, 2), (9, 4), (12, 0), (14, 5)):
        print(f"   hit step {st}+{o}:", outcome(r.hit(st, o)), r.state())
    r.h.until_tick(r.t0 + 6 * 16 + 2)
    print("   note recorders' rec+0x35 during override:", r.notes_flags(), "(stock value = !bit12)")
    override_end(r.h); print("   restore at step 16+2:", r.state())
    for st, o in ((17, 2), (21, 4)):
        print(f"   hit step {st}+{o}:", outcome(r.hit(st, o)), r.state())
    print("   pattern:", r.result())

    print("\n== S5 patched vs stock: user Shift+Record during the override, restore (a) after a step boundary, (b) mid-step right after ==")
    for case in ("a", "b"):
        rs = Run(STOCK, "S5s"); rp = Run(PATCHED, "S5p")
        for rr in (rs, rp):
            rr.start()
            rr.h.until_tick(rr.t0 + 6 * 3 + 1)
        override_start(rp.h)
        for rr in (rs, rp):
            rr.h.until_tick(rr.t0 + 6 * 5 + 2)
            rr.h.press(RECORD, shift=True)           # user: quantise off
        if case == "a":
            for rr in (rs, rp):
                rr.h.until_tick(rr.t0 + 6 * 7 + 2)
                rr.h.press(RECORD, shift=True)       # user: quantise on again
                rr.h.until_tick(rr.t0 + 6 * 9 + 2)   # past a step boundary
        else:
            for rr in (rs, rp):
                rr.h.until_tick(rr.t0 + 6 * 7 + 2)
                rr.h.press(RECORD, shift=True)       # user: quantise on again, restore in the same step
        override_end(rp.h)
        print(f"  ({case}) after restore: stock {rs.state()}\n                      patched {rp.state()}")
        for st, o in ((11, 2), (13, 4)):
            a, b = outcome(rs.hit(st, o)), outcome(rp.hit(st, o))
            print(f"   hit step {st}+{o}: stock {a}  patched {b}  {'SAME' if a == b else 'DIFF'}")
        print("   flags equal now:", [rs.h.quantise_flag(d) for d in range(4)] == [rp.h.quantise_flag(d) for d in range(4)])

    print("\n== S6 patched: user Shift+Record (quantise off) during override, restore -> stays unquantised (stock's own value) ==")
    rs = Run(STOCK, "S6s"); rp = Run(PATCHED, "S6p")
    for rr in (rs, rp):
        rr.start(); rr.h.until_tick(rr.t0 + 6 * 3 + 1)
    override_start(rp.h)
    for rr in (rs, rp):
        rr.h.until_tick(rr.t0 + 6 * 5 + 2); rr.h.press(RECORD, shift=True)
        rr.h.until_tick(rr.t0 + 6 * 8 + 1)
    override_end(rp.h)
    print("   stock  ", rs.state()); print("   patched", rp.state())
    for st, o in ((10, 2), (13, 4)):
        a, b = outcome(rs.hit(st, o)), outcome(rp.hit(st, o))
        print(f"   hit step {st}+{o}: stock {a}  patched {b}  {'SAME' if a == b else 'DIFF'}")


if __name__ == "__main__":
    main()
