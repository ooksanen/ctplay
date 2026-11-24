"""q3_probe: which stores the Note view, the recorder and the step editor (0x20039E50 + 0x3A0 t) use for track 0, and
what the held step looks like in them: hold step pad 3 on the 1-16 half, then 1-16/17-32 (button 21) and step pad 3
again (step 19); then select pattern 2 (Patterns view: button 13, pad 16) and hold step pad 5.
Prints parameters 0-3 of each store (the read buffer) at rest and while held."""
from lib import SH, pl18, prepare
from notes import PARAM_GET
from unicorn.arm_const import UC_ARM_REG_R0

IMG, M = pl18()
EDITOR, ED_SZ = 0x20039E50, 0x3A0
ENGINE = 0x20038EC0


def p(h, store, i):
    h.call(PARAM_GET, store, i)
    a = h.uc.reg_read(UC_ARM_REG_R0)
    return h.r32(a)


def stores(h):
    v = h.note_view(0)
    rec = h.rec()
    ed = EDITOR
    out = {f"view+{o:#x}": h.r32(v + o) for o in (0x1C, 0x20, 0x24, 0x28, 0x2C)}
    out |= {f"rec+{o:#x}": h.r32(rec + o) for o in (0x0C, 0x14, 0x1C, 0x20, 0x4C, 0x50)}
    out |= {f"editor+{o:#x}": h.r32(ed + o) for o in range(0, 0x40, 4)}
    out["engine+0x30"] = h.r32(ENGINE + 0x30)
    return out


def show(h, label, names):
    st = stores(h)
    print(label)
    for n in names:
        s = st[n]
        if 0x20000000 <= s < 0x20050000:
            try:
                print(f"   {n:12s} {s:#010x}: p0-3 = {[hex(p(h, s, i)) for i in range(4)]}")
            except AssertionError:
                print(f"   {n:12s} {s:#010x}: (not a store)")



def main():
    h = SH(IMG)
    prepare(h)
    st = stores(h)
    print("pointers:", {k: hex(v) for k, v in st.items()})
    names = ["view+0x1c", "view+0x20", "view+0x24", "view+0x28", "view+0x2c", "rec+0x14", "rec+0x4c", "editor+0x18",
             "engine+0x30"]
    show(h, "at rest (pattern 0, steps 1-16)", names)
    h.down(3)
    show(h, "step pad 3 held (step 4 of 1-16)", names)
    h.up(3)
    h.press(21)
    h.down(3)
    show(h, "1-16/17-32 pressed, step pad 3 held", names)
    h.up(3)
    h.press(21)
    h.press(13)
    h.pad(16)                 # Patterns view: pad 8 r + t = track t, pattern r (stopped: at once)
    h.track(0)
    h.down(5)
    show(h, "Patterns view: pad 16 (pattern 2), back to Synth 1, step pad 5 held", names)
    h.up(5)


if __name__ == "__main__":
    main()
