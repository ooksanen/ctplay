"""Q2: the release route of a row-4 pad in both probability views, and a row-4 pad held while the view changes.

Logged: the controller's pad release 0x080332CE (r1 = pad), its release-all 0x08033A6C (pads 0-31 through 0x080332CE),
the container's release 0x080435F0, its half release-all 0x08043930, and the view slot 1 the container tail-calls
(0x08043632 `bx r3`: the view's class and the remapped pad). Case 1: press / release pad 27 (the spec's pad 28) in the
view. Case 2: hold pad 27, press a button (press + release), then release pad 27: what ran during the button, the bits
([ctrl + 0x84], [cont + 0x190]) after it, and what the late release reaches."""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1

from c_lib import CONT, MGR, H

PAD = 27
EXP_PAD = 20            # the expanded view: the spec's pad 21 (FILL for drum 1)
LOG = {0x080332CE: "ctrl_release", 0x08033A6C: "ctrl_release_all", 0x080435F0: "cont_release",
       0x08043930: "cont_release_half", 0x08043632: "view_slot1"}
BUTTONS = [("Note", 9, False), ("Velocity", 10, False), ("Gate", 11, False), ("Pattern Settings", 12, False),
           ("Shift + Pattern Settings", 12, True), ("Patterns", 13, False), ("Shift + Patterns", 13, True),
           ("Preset", 8, False), ("Mixer", 14, False), ("FX", 15, False), ("Play", 17, False),
           ("same track", None, False), ("next track same kind", "next", False), ("other kind", "other", False)]


class R(H):
    def __init__(self, *a):
        super().__init__(*a)
        self.rel = []

        def hook(u, a, s, d):
            r0, r1 = u.reg_read(UC_ARM_REG_R0), u.reg_read(UC_ARM_REG_R1)
            if a == 0x08043632:
                self.rel.append(("view_slot1", hex(self.r32(r0)), r1))
            elif a in (0x08033A6C,):
                self.rel.append((LOG[a],))
            elif a == 0x080332CE:
                self.rel.append((LOG[a], r1, "active " + hex(self.r32(MGR + 0x6C)), "mode %d" % self.r8(CONT + 0x18C)))
            else:
                self.rel.append((LOG[a], r1))
        for a in LOG:
            self.uc.hook_add(UC_HOOK_CODE, hook, begin=a, end=a)

    def bits(self, pad=PAD):
        return (self.r32(MGR + 0x84) >> pad & 1, self.r32(CONT + 0x190) >> pad & 1)


def squash(log, pad=PAD):
    """Release-alls log 32 / 16 entries: keep only the ones for the pad and the alls themselves."""
    return [e for e in log if e[0] in ("ctrl_release_all", "cont_release_half") or
            (e[0] in ("ctrl_release", "cont_release") and e[1] == pad) or (e[0] == "view_slot1" and e[2] == pad)]


def expanded():
    h = R()
    h.open_expanded(0)
    h.rel.clear()
    h.down(EXP_PAD)
    h.up(EXP_PAD)
    print(f"expanded view, drum 1: press / release pad {EXP_PAD}: {squash(h.rel, EXP_PAD)}")
    for name, b, sh in (("Note", 9, False), ("Drum 2", 5, False), ("Drum 1 again", 4, False), ("Synth 1", 0, False),
                        ("Velocity", 10, False), ("Shift + Pattern Settings", 12, True), ("Mixer", 14, False),
                        ("Patterns", 13, False), ("Play", 17, False)):
        h = R()
        h.open_expanded(0)
        h.down(EXP_PAD)
        h.rel.clear()
        h.press(b, shift=sh)
        during, ids, bits = squash(h.rel, EXP_PAD), h.ids(), h.bits(EXP_PAD)
        h.rel.clear()
        h.up(EXP_PAD)
        print(f"  hold {EXP_PAD}, {name:24s} -> active {ids['active']} mode {ids['mode']} track {ids['track']}: "
              f"during {during}; bits ctrl/cont after {bits}; late release {squash(h.rel, EXP_PAD)}")


def main():
    for t in (1, 4):
        kind = "notes" if t < 4 else "drums"
        h = R()
        h.open_prob(t)
        h.rel.clear()
        h.down(PAD)
        h.up(PAD)
        print(f"{kind} track {t}: press / release pad {PAD}: {h.rel}")
        for name, b, sh in BUTTONS:
            h = R()
            h.open_prob(t)
            h.down(PAD)
            h.rel.clear()
            if b is None:
                h.press(t)
            elif b == "next":
                h.press(t + 1)
            elif b == "other":
                h.press(4 if t < 4 else 1)
            else:
                h.press(b, shift=sh)
            during = squash(h.rel)
            ids = h.ids()
            bits = h.bits()
            h.rel.clear()
            h.up(PAD)
            late = squash(h.rel)
            print(f"  hold {PAD}, {name:24s} -> mode {ids['mode']} track {ids['track']} bottom {ids['bottom_class']}: "
                  f"during {during}; bits ctrl/cont after {bits}; late release {late}")


if __name__ == "__main__":
    main()
    expanded()
