"""Q3 + Q4: the drum expanded view (Drum N, then Note again: mode 6) and pads 0-27 (the spec's 1-28).

Q3: stock image and PL18 (no drum page open): for drums 1 and 4, stopped / playing, Shift off / on, two harnesses run
the same route and one presses and releases pads 0-27 in turn (a heartbeat between while playing); RAM
(0x20000000-0x20050000) + ITCM (0x0-0x4000, CTPlay's state) and the 69 LEDs are compared, [ctrl + 0x170] ignored.
Also: the view's press 0x0804ED50 returns at 0x0804ED66 and its release 0x0804ED68 at 0x0804ED6E for pads < 28; no
sink call. LEDs drawn for pads 0-31 in mode 6 (stopped, playing, Shift held, a drum pad held), the view's buffer
[[view + 4]], and the ids that tell this view is on screen. PL18 with a drum page open on the expanded view: who takes
pads 20-23.
Q4: hold drum pad 28 (drum 1), press and release pad 20, release 28; and hold 20, press and release 28, release 20:
compared with the same run without pad 20 (sink calls, RAM)."""
import struct
from itertools import product

from unicorn import UC_HOOK_CODE

from c_lib import CONT, EXPANDED, MGR, H, diff, fmt_diff, hexrow, image_pl18, STOCK

IGNORE = [(MGR + 0x170, MGR + 0x171)]
ITCM = 0x4000


class X(H):
    def __init__(self, image):
        super().__init__(image)
        self.rets = []

        def hook(u, a, s, d):
            self.rets.append(a)
        for a in (0x0804ED66, 0x0804ED6E, 0x0804ED64, 0x0804ED7E):   # press: return / sink call; release: same
            self.uc.hook_add(UC_HOOK_CODE, hook, begin=a, end=a)

    def state(self):
        return self.ram() + bytes(self.uc.mem_read(0, ITCM))


def sdiff(a, b):
    d = diff(a[:0x50000], b[:0x50000], IGNORE)
    di = [(x - 0x20000000, o, n) for x, o, n in diff(a[0x50000:], b[0x50000:])]
    return d + [(x, o, n) for x, o, n in di]


def build(image, d, playing, shift, press, pads=range(28)):
    h = X(image)
    h.leds()
    h.open_expanded(d)
    if playing:
        h.play(30)
    h.take_all()
    h.rets.clear()
    if shift:
        h.shift(True)
    for p in pads:
        if press:
            h.down(p)
        if playing:
            h.heartbeat(1)
        if press:
            h.up(p)
        if playing:
            h.heartbeat(1)
    log = h.take_all()
    if shift:
        h.shift(False)
    if playing:
        h.heartbeat(5)
    return h, log, h.leds()


def q3():
    bad = 0
    for (name, img), d, playing, shift in product((("stock", STOCK), ("PL18", image_pl18())), (0, 3), (0, 1), (0, 1)):
        a, (sa, ha, ea), la = build(img, d, playing, shift, True)
        b, (sb, hb, eb), lb = build(img, d, playing, shift, False)
        dd = sdiff(a.state(), b.state())
        presses = [x[2] for x in ha if x[0] == "exp_pad"]
        rels = [x[2] for x in ha if x[0] == "exp_release"]
        ok = (not dd and la == lb and sa == sb and ea == eb and presses == list(range(28)) and rels == list(range(28))
              and a.rets.count(0x0804ED66) == 28 and a.rets.count(0x0804ED6E) == 28
              and not {0x0804ED64, 0x0804ED7E} & set(a.rets))
        bad += not ok
        print(f"{name} drum {d + 1} playing {playing} shift {shift}: {'NOTHING' if ok else 'DIFFERENT'}; view press "
              f"args 0-27 {presses == list(range(28))}, release args 0-27 {rels == list(range(28))}, early returns "
              f"{a.rets.count(0x0804ED66)} / {a.rets.count(0x0804ED6E)}, sinks {len(sa)} vs {len(sb)}, "
              f"endpoints {len(ea)} vs {len(eb)}, state diff {fmt_diff(dd)}")
    print("cases with a difference:", bad)


def frames():
    for name, img in (("stock", STOCK), ("PL18", image_pl18())):
        h = X(img)
        h.leds()
        h.open_expanded(0)
        v = h.view_for(28)
        print(f"{name}: ids {h.ids()}; expanded view {hex(v)} = [cont + 0xAC] {h.r32(CONT + 0xAC) == v}, "
              f"view for pad 0 = for pad 28 {h.view_for(0) == v}")
        buf = struct.unpack("<32H", bytes(h.uc.mem_read(h.r32(h.r32(v + 4)), 64)))
        print(f"   view buffer [[view+4]] {hex(h.r32(h.r32(v + 4)))}: {hexrow(buf)}")
        print(f"   pads 0-31 stopped     : {hexrow(h.leds()[:32])}")
        h.shift(True)
        print(f"   pads 0-31 Shift held  : {hexrow(h.leds()[:32])}")
        h.shift(False)
        h.down(28)
        print(f"   pads 0-31 pad 28 held : {hexrow(h.leds()[:32])}")
        h.up(28)
        h.play(300)
        print(f"   pads 0-31 playing     : {hexrow(h.leds()[:32])}")
        for d in (1, 2, 3):
            g = X(img)
            g.leds()
            g.open_expanded(d)
            print(f"   drum {d + 1}: ids {g.ids()}, pads 0-31 {hexrow(g.leds()[:32])}")


def page_open():
    """PL18: Shift + Drum 1 opens drum 1's page (the Repeat page); then Note (stock: mode 6) closes it?"""
    h = X(image_pl18())
    h.leds()
    h.open_expanded(0)
    h.press(4, shift=True)
    print("PL18 Shift + Drum 1 on the expanded view:", h.ids())
    h.take_all()
    h.down(20)
    h.up(20)
    sinks, hits, _ = h.take_all()
    print("   pad 20 with the page open: the view's handler reached", [x[0] for x in hits if x[0].startswith("exp")],
          "sinks", sinks, "LEDs 16-31", hexrow(h.leds()[16:32]))
    h.press(9)
    print("   then Note:", h.ids(), "pad 20 reaches the view:", end=" ")
    h.take_all()
    h.down(20)
    h.up(20)
    _, hits, _ = h.take_all()
    print([x[0] for x in hits if x[0].startswith("exp")])


def q4():
    for name, img in (("stock", STOCK), ("PL18", image_pl18())):
        for order in ("28 held, 20 tapped", "20 held, 28 tapped"):
            runs = []
            for with20 in (True, False):
                h = X(img)
                h.leds()
                h.open_expanded(0)
                h.take_all()
                if order.startswith("28"):
                    h.down(28)
                    if with20:
                        h.down(20)
                        h.up(20)
                    h.up(28)
                else:
                    if with20:
                        h.down(20)
                    h.down(28)
                    h.up(28)
                    if with20:
                        h.up(20)
                sinks, hits, ends = h.take_all()
                runs.append((h.state(), [s[0] + str(s[2]) for s in sinks], ends, h.leds()))
            dd = sdiff(runs[0][0], runs[1][0])
            same = not dd and runs[0][1:] == runs[1][1:]
            print(f"Q4 {name} {order}: {'same as without pad 20' if same else 'DIFFERENT'}; sinks {runs[0][1]} "
                  f"vs {runs[1][1]}; state diff {fmt_diff(dd)}")


if __name__ == "__main__":
    frames()
    page_open()
    q3()
    q4()
