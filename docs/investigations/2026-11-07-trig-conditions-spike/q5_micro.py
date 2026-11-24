"""Q5 follow-up: the drum micro-step view (Gate on a drum track: mode 3, class vtable 0x0805AA9C, pad handler
0x0804F036 = vtable slot 2, pads 16-21 -> r1 0-5) removes a hit when its last micro bit is turned off
(0x0804F0FC cbnz r5 falls through: 0x0804F104-0x0804F118 clear the velocity byte in the step store).
Checks: hooks.check_entry / check_mid on candidate sites; in emulation, a site at 0x0804F104 is reached only when the
press empties the step, with r7 = the view, sl = the step, [r7 + 0xC] = the drum's step store (its editor + 0x18);
the pattern is the drum's shown one; drums 1 and 2, 1-16 and 17-32, stopped and playing (step selected beforehand)."""
from q_lib import *
from slimbuild import hooks, paths
from slimbuild.symbols import HookPoint

SITES = [(0x0804F036, 4, "entry"), (0x0804F036, 6, "entry"), (0x0804F0FE, 4, "mid"), (0x0804F104, 4, "mid"),
         (0x0804F106, 4, "mid")]
SITE = 0x0804F104


def check(addr, n, kind):
    exp = STOCK[addr - 0x08010000:addr - 0x08010000 + n]
    hp = HookPoint(name=f"s{addr:x}", kind=kind, context="ui", args=(), ret="void", addr=addr, expect=exp, displace=n)
    try:
        if kind == "mid":
            hooks.check_mid(hp, STOCK, hooks.branch_targets(paths.LISTING), hooks.it_covered(paths.LISTING))
        else:
            hooks.check_entry(hp, STOCK, hooks.branch_targets(paths.LISTING))
        return exp.hex(), "PASS"
    except Exception as e:  # noqa: BLE001
        return exp.hex(), f"no: {str(e).split(': ', 1)[1]}"


def case(d, step, micro, pad, page2=False, playing=False):
    h = Q()
    h.leds()
    set_tempo(h, bpm=240)
    hits = {(step + 5) % 32: (80, 1, 7, 0xFF)}
    if micro:
        hits[step] = (90, micro, 7, 0xFF)
    if playing:
        h.set_chain(4 + d, 0, 0)
    h.set_dhits(d, 0, hits, load=False)
    h.dload(d)
    h.press(4 + d)
    h.press(10)                                    # velocity view: select the step without toggling it
    if page2:
        h.press(BTN["half"])
    h.pad(step % 16)
    h.press(11)                                    # Gate: the drum's micro-step view
    assert h.view_mode() == 3
    if playing:
        h.press(BTN_FOLLOW, shift=True)            # follow off (0x20039DE0 p0 = 1): the selection stays
        h.play(True)
        h.heartbeat(30)
    seen = []

    def at(hh, r, sp):
        st = hh.r32(r[7] + 0xC)
        dd = next((k for k in range(4) if hh.r32(hh.deditor(k) + 0x18) == st), None)
        seen.append(dict(view=r[7], view_class=hh.r32(r[7]), step=r[10], drum=dd, shown=hh.dshown_py(dd)))
    h.handler_at(SITE, at)
    b = h.dpattern(d, 0)
    h.down(pad)
    h.up(pad)
    a = h.dpattern(d, 0)
    return b[step], a[step], b[0x60 + step], a[0x60 + step], seen


BTN_FOLLOW = 13

if __name__ == "__main__":
    print("== hook sites")
    for addr, n, kind in SITES:
        exp, ok = check(addr, n, kind)
        print(f"   {kind:<5} {addr:#010x} +{n}: {exp:<12} {ok}")
    print("\n== emulation: the site at 0x0804F104 (mid, after the micro byte is written back, before the velocity clear)")
    for label, args in (("drum 1 step 4, micro 0x01, pad 16 (bit 0 off: empties)", (0, 3, 0x01, 16)),
                        ("drum 1 step 4, micro 0x03, pad 16 (bit 0 off, bit 1 left)", (0, 3, 0x03, 16)),
                        ("drum 1 step 4, micro 0x04, pad 18 (bit 2 off: empties)", (0, 3, 0x04, 18)),
                        ("drum 1 empty step 9, pad 17 (adds a hit, micro 0x02)", (0, 8, 0x00, 17)),
                        ("drum 2 step 4, micro 0x01, pad 16", (1, 3, 0x01, 16)),
                        ("drum 1 step 21 (17-32 shown), micro 0x20, pad 21", (0, 20, 0x20, 21, True)),
                        ("drum 1 step 4, micro 0x01, pad 16, playing (follow off)", (0, 3, 0x01, 16, False, True))):
        vb, va, mb, ma, seen = case(*args)
        print(f"   {label}: velocity {vb} -> {va}, micro {mb:#04x} -> {ma:#04x}; site reached {len(seen)}x "
              + "; ".join(f"view {s['view']:#x} (class {s['view_class']:#x}), sl = step {s['step']}, drum {s['drum']}, "
                          f"shown pattern {s['shown']}" for s in seen))
