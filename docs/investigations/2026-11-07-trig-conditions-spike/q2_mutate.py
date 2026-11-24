"""Q2: a mid-hook site in drum Mutate 0x0803E6F0's swap loop where both swapped steps and the pattern are in registers,
once per swap. (1) hooks.check_mid on every 4 / 6 B span from the swap's first instruction after `beq.w` (0x0803E78E)
to the lanes loop (0x0803E812); (2) the chosen site in emulation: a Python handler swaps the two steps' codes (byte
+0x88 + s and bit s of +0x84..) as Task 8's handler would, through the real route (Shift + Duplicate, drum step view),
several seeds (the random word differs per run through [r7 + 4] ... here: several Mutates in a row), and checks that
every step's (velocity, probability, flip, micro, code) after Mutate is one step's tuple before (a permutation that
carries the codes with the hits)."""
from capstone import CS_ARCH_ARM, CS_MODE_MCLASS, CS_MODE_THUMB, Cs

from q_lib import *
from slimbuild import hooks, paths
from slimbuild.symbols import HookPoint

LO, HI = 0x0803E78E, 0x0803E812
SWAP_TEST = 0x0803E788           # cmp r4, r3 (r4 = position, r3 = the random partner); beq.w skips the swap
HITS = {0: (100, 1, 7, 0xFF), 2: (90, 3, 5, 0xFF), 4: (80, 1, 7, 2), 5: (70, 1, 7, 0xFF), 8: (60, 0x21, 7, 0xFF),
        12: (50, 1, 6, 0xFF), 15: (40, 1, 7, 0xFF), 21: (35, 1, 7, 0xFF), 30: (30, 1, 4, 0xFF)}


def candidates():
    img = STOCK
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    insns = list(md.disasm(img[LO - 0x08010000:HI - 0x08010000], LO))
    targets = hooks.branch_targets(paths.LISTING)
    covered = hooks.it_covered(paths.LISTING)
    out = []
    for i, ins in enumerate(insns):
        for n in (4, 6):
            if sum(x.size for x in insns[i:i + 3]) < n:
                continue
            exp = img[ins.address - 0x08010000:ins.address - 0x08010000 + n]
            hp = HookPoint(name=f"m{ins.address:x}", kind="mid", context="ui", args=(), ret="void",
                           addr=ins.address, expect=exp, displace=n)
            try:
                hooks.check_mid(hp, img, targets, covered)
                ok = "PASS"
            except Exception as e:  # noqa: BLE001
                ok = f"no ({str(e).split(': ', 1)[1][:70]})"
            text = "; ".join(f"{x.mnemonic} {x.op_str}" for x in insns[i:i + 3]
                             if x.address < ins.address + n)
            out.append((ins.address, n, exp.hex(), ok, text))
    return out


def steps(h, p):
    pat = h.dpattern(0, p)
    return [(pat[s], pat[0x20 + s], pat[0x40 + s], pat[0x60 + s], code_of(h, 0, p, s)) for s in range(32)]


def run(site, mutates=6):
    h = Q()
    h.leds()
    for p in range(8):
        h.set_dcond(0, p, dtag(0, p))
    h.set_dhits(0, 0, HITS, load=False)
    h.dload(0)
    step_view(h, 4)
    seen, swaps = [], []

    def test(hh, r, sp):
        swaps.append((r[4], r[3]))

    def handler(hh, r, sp):
        a, b = r[4], r[3]
        pat = hh.r32(sp + 4)                       # the pattern ([sp + 4]; after the displaced ldr: r1 / r2 / ip)
        seen.append((a, b, pat))
        d, p, off = hh.drum_of_pattern(pat)
        ca, cb = code_of(hh, d, p, a), code_of(hh, d, p, b)
        for s, c in ((a, cb), (b, ca)):
            hh.uc.mem_write(pat + 0x88 + s, bytes([c & 0xFF]))
            bb = hh.r8(pat + 0x84 + (s >> 3))
            hh.uc.mem_write(pat + 0x84 + (s >> 3), bytes([(bb & ~(1 << (s & 7)) & 0xFF) | ((c >> 8) << (s & 7))]))
    h.handler_at(SWAP_TEST, test)
    if site is not None:
        h.handler_at(site, handler)
    ok_all = True
    for k in range(mutates):
        before = steps(h, 0)
        seen.clear()
        swaps.clear()
        shown = h.dshown(0)
        h.press(BTN["dup"], shift=True)
        after = steps(h, 0)
        real = [(a, b) for a, b in swaps if a != b]
        perm_ok = sorted(after) == sorted(before) and all(t in before for t in after)
        hits_moved = sum(1 for s in range(32) if after[s][0] and after[s] != before[s])
        pats = {hh for _, _, hh in seen}
        ok = perm_ok and (site is None or ([(a, b) for a, b, _ in seen] == real and pats == {h.dpat(0, shown)}))
        ok_all &= ok
        print(f"   Mutate {k + 1}: swaps {len(real)} (of {len(swaps)} positions), handler calls {len(seen)} = swaps "
              f"{[(a, b) for a, b, _ in seen] == real}; pattern in the handler = the shown pattern {pats == {h.dpat(0, shown)}}; "
              f"hits moved {hits_moved}; every step's tuple (vel, prob, flip, micro, code) is one of before's: {perm_ok}")
    return ok_all


if __name__ == "__main__":
    print("== check_mid on every span in the swap body (once per swap: after beq.w at 0x0803E78A, before the lanes loop)")
    for addr, n, exp, ok, text in candidates():
        print(f"   {addr:#010x} +{n}: {exp:<12} {ok:<5}  {text}")
    for site, regs_after in ((0x0803E78E, "r4 = step a, r3 = step b, r1 = r2 = pattern (displaced ldr r1 / r2, [sp, #4])"),
                             (0x0803E80A, "r4 = step a, r3 = step b, ip = pattern (displaced ldr.w ip, [sp, #4])")):
        print(f"\n== emulation, handler at {site:#010x}: {regs_after}")
        print(f"   all consistent: {run(site)}")
    print("\n== control: no handler (stock alone): the same check must fail (codes stay in place while hits move)")
    print(f"   all consistent: {run(None, mutates=2)}")
