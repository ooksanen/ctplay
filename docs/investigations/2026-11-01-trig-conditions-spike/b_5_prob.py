"""B5: stock's probability tests (notes 0x08040D8A in seq_units_start; drums 0x0804AA18 in the hit test, 0x080411F6
in slot 4): how often each is reached, what the registers hold, and whether forcing "fail" there (taking the `blo`
at 0x08040D8E / 0x0804AA1E / 0x080411FC, what a mid hook's handler would do through APSR) silences a step exactly as
a failed roll. The roll's random word is drawn at tick 0 (0x0804A6B8, stored at 0x0804A6BC); a hook there sets its
low 3 bits so the roll's outcome is chosen."""
import collections
import sys
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R10
from b_lib import *
from b_3_hand import fresh

RAND_STORE = 0x0804A6BC
N_BLO, D_BLO_HIT, D_BLO_S4 = 0x08040D8E, 0x0804AA1E, 0x080411FC
N_FAIL, D_FAIL_HIT, D_FAIL_S4 = 0x08040D98, 0x0804AA30, 0x08041208
SEQ_NOTE_ON, SEQ_NOTE_OFF = 0x08040FA2, 0x0804104A
D_NOTE_ON, D_PREV_OFF, D_SLOT1_OFF, D_SAMPLE = 0x08041298, 0x08041286, 0x080411C2, 0x08041240


def note_pattern(h):
    """Synth 1 pattern 0, 8 steps: 0 C4; 1 D4 tied (gate 6 | tie); 2 D4 (the tie's continuation; target);
    3 E4 gate 30 (5 steps); 4 F4 + A4 micro 2 (target, during the long E4); 5 empty; 6 G4 micro 3; 7 C5."""
    base = PATTERN_BASE[0]
    h.uc.mem_write(base, bytes(32 * STEP))
    def put(s, units, prob=7):
        body = b"".join(bytes(u) for u in units).ljust(24, b"\0")
        h.uc.mem_write(base + s * STEP, bytes([(1 << len(units)) - 1, prob, 0, 0]) + body)
    put(0, [(60, 6, 0, 100)])
    put(1, [(62, 6 | 0x80, 0, 100)])
    put(2, [(62, 6, 0, 100)], prob=6)
    put(3, [(64, 30, 0, 100)])
    put(4, [(65, 6, 2, 100), (69, 6, 2, 100)], prob=6)
    put(6, [(67, 6, 3, 100)])
    put(7, [(72, 6, 0, 100)])


def drum_pattern(h):
    """Drum 1 pattern 0, 8 steps: hits on 0-3 and 6; step 2 (target) has a flip sample 5 and micro bits 0 + 3,
    probability 6; step 3 micro bit 1."""
    b = h.drum_base(0)
    vel = [100, 100, 100, 100, 0, 0, 100, 0] + [0] * 24
    prob = [7, 7, 6, 7, 7, 7, 7, 7] + [7] * 24
    flip = [0xFF, 0xFF, 5, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF] + [0xFF] * 24
    micro = [1, 1, 0b1001, 0b10, 0, 0, 1, 0] + [0] * 24
    h.uc.mem_write(b, bytes(vel + prob + flip + micro))


TARGET = {0: {2, 4}, 4: {2}}           # track -> target steps


def run(mode, drums=False, force_hit=True, force_s4=True, passes=2):
    """mode: 'pass' (rand low bits 0 on the targets), 'roll' (rand low bits 7: stock fails its roll, prob 6),
    'force' (rand 0 as 'pass', the blo forced on the targets)."""
    cfg = {t: dict(chain=(0, 0), pats={0: (7, 0, 3, 0)}) for t in range(8)}
    h = fresh(cfg)
    note_pattern(h)
    drum_pattern(h)
    h.call(0x0803F050, h.r32(0x200438DC + 0xC) - 0x18)       # drum 1's editor load (step store in line)
    ms = [0]
    log = []
    cur = {}                                                   # player -> (pattern, step) at its last tick 0
    reach = collections.Counter()
    regs = {}
    uc = h.uc

    def rnd(u, a, s, d):
        p = u.reg_read(UC_ARM_REG_R7)
        if p not in PLAYERS:
            return
        t = PLAYERS.index(p)
        step = u.reg_read(UC_ARM_REG_R8) & 0xFF
        cur[t] = step
        if step in TARGET.get(t, ()):
            r0 = u.reg_read(UC_ARM_REG_R0)
            u.reg_write(UC_ARM_REG_R0, (r0 & ~7) | (7 if mode == "roll" else 0))
    uc.hook_add(UC_HOOK_CODE, rnd, begin=RAND_STORE, end=RAND_STORE)

    def n_test(u, a, s, d):
        sb = u.reg_read(UC_ARM_REG_R9)
        if sb != PLAYERS[0]:
            return
        sp = u.reg_read(UC_ARM_REG_SP)
        step, micro, unit = h.r32(sp) & 0xFF, u.reg_read(UC_ARM_REG_R3), u.reg_read(UC_ARM_REG_R8)
        reach[("n", step, micro)] += 1
        regs.setdefault("n", dict(sb=hex(sb), r5_step_addr=hex(u.reg_read(UC_ARM_REG_R5)), sp0_step=step, r3_micro=micro,
                                  r8_unit=unit, lr_rand7=u.reg_read(UC_ARM_REG_LR), pattern_from_r5=(u.reg_read(UC_ARM_REG_R5) - h.r32(sb + 0x48)) // PATTERN))
    uc.hook_add(UC_HOOK_CODE, n_test, begin=N_PROB, end=N_PROB)

    def n_blo(u, a, s, d):
        if mode == "force" and u.reg_read(UC_ARM_REG_R9) == PLAYERS[0] and h.r32(u.reg_read(UC_ARM_REG_SP)) & 0xFF in TARGET[0]:
            u.reg_write(UC_ARM_REG_PC, N_FAIL | 1)
    uc.hook_add(UC_HOOK_CODE, n_blo, begin=N_BLO, end=N_BLO)

    def d_test(u, a, s, d):
        sp = u.reg_read(UC_ARM_REG_SP)
        player = h.r32(sp + 4)                         # the hit test pushed {r4, r5}: [sp + 4] = slot 2's r5 = player
        if player != PLAYERS[4]:
            return
        base, addr = u.reg_read(UC_ARM_REG_R5), u.reg_read(UC_ARM_REG_R1)
        reach[("d", addr - base, u.reg_read(UC_ARM_REG_R2))] += 1
        regs.setdefault("d_hit", dict(r5_pattern_base=hex(base), r1_step_addr=hex(addr), step=addr - base,
                                      r2_micro=u.reg_read(UC_ARM_REG_R2), r3_rand7=u.reg_read(UC_ARM_REG_R3),
                                      sp4_player=hex(player), caller_r6_step=u.reg_read(UC_ARM_REG_R6)))
    uc.hook_add(UC_HOOK_CODE, d_test, begin=D_PROB_HIT, end=D_PROB_HIT)

    def d_blo(u, a, s, d):
        if mode == "force" and force_hit and h.r32(u.reg_read(UC_ARM_REG_SP) + 4) == PLAYERS[4] \
                and u.reg_read(UC_ARM_REG_R6) & 0xFF in TARGET[4]:
            u.reg_write(UC_ARM_REG_PC, D_FAIL_HIT | 1)
    uc.hook_add(UC_HOOK_CODE, d_blo, begin=D_BLO_HIT, end=D_BLO_HIT)

    def s4_test(u, a, s, d):
        if u.reg_read(UC_ARM_REG_R4) != PLAYERS[4]:
            return
        reach[("s4", u.reg_read(UC_ARM_REG_R2), u.reg_read(UC_ARM_REG_R6))] += 1
        regs.setdefault("d_s4", dict(r4_player=hex(u.reg_read(UC_ARM_REG_R4)), r1_pattern_base=hex(u.reg_read(UC_ARM_REG_R1)),
                                     r2_step=u.reg_read(UC_ARM_REG_R2), r3_step_addr=hex(u.reg_read(UC_ARM_REG_R3)),
                                     r6_micro=u.reg_read(UC_ARM_REG_R6), r7_rand7=u.reg_read(UC_ARM_REG_R7)))
    uc.hook_add(UC_HOOK_CODE, s4_test, begin=D_PROB_S4, end=D_PROB_S4)

    def s4_blo(u, a, s, d):
        if mode == "force" and force_s4 and u.reg_read(UC_ARM_REG_R4) == PLAYERS[4] and u.reg_read(UC_ARM_REG_R2) in TARGET[4]:
            u.reg_write(UC_ARM_REG_PC, D_FAIL_S4 | 1)
    uc.hook_add(UC_HOOK_CODE, s4_blo, begin=D_BLO_S4, end=D_BLO_S4)

    def ev(kind):
        def f(u, a, s, d):
            r = [u.reg_read(UC_ARM_REG_R0 + i) for i in range(4)]
            if kind.startswith("n_") and r[0] != PLAYERS[0]:
                return
            log.append((ms[0], h.tick, kind, *r[1:4]))
        return f
    uc.hook_add(UC_HOOK_CODE, ev("n_on"), begin=SEQ_NOTE_ON, end=SEQ_NOTE_ON)
    uc.hook_add(UC_HOOK_CODE, ev("n_off"), begin=SEQ_NOTE_OFF, end=SEQ_NOTE_OFF)

    def dev(kind):
        def f(u, a, s, d):
            # drum player call sites: r4 / r5 hold the player (slot 2: r5 = player until the hit test; at 0x08041286 /
            # 0x08041298 r4 = player + 0x58); slot 1: r4 = player + 0x4C; slot 4: r4 = player
            r4 = u.reg_read(UC_ARM_REG_R4)
            pl = {D_NOTE_ON: r4 - 0x58, D_PREV_OFF: r4 - 0x58, D_SLOT1_OFF: r4 - 0x4C, D_SAMPLE: None}[a]
            if a == D_SAMPLE:
                pl = PLAYERS[4] if u.reg_read(UC_ARM_REG_R1) == h.r8(h.r32(PLAYERS[4] + 0x54) + 8) else None
            if pl != PLAYERS[4]:
                return
            log.append((ms[0], h.tick, kind, u.reg_read(UC_ARM_REG_R1), u.reg_read(UC_ARM_REG_R2)))
        return f
    for a, k in ((D_NOTE_ON, "d_on"), (D_PREV_OFF, "d_prev_off"), (D_SLOT1_OFF, "d_slot1_off"), (D_SAMPLE, "d_sample")):
        uc.hook_add(UC_HOOK_CODE, dev(k), begin=a, end=a)

    h.take()
    h.play()
    goal = 48 * passes + 2
    while h.tick < goal:
        h.heartbeat(1)
        ms[0] += 1
        for e in h.take("synth_on", "synth_off"):
            log.append((ms[0], h.tick, e[0], e[2]))
    return h, log, reach, regs


def sig(log, kinds):
    return [e for e in log if e[2] in kinds]


if __name__ == "__main__":
    out = {}
    for mode in ("pass", "roll", "force"):
        h, log, reach, regs = run(mode)
        out[mode] = log
        if mode == "pass":
            print("== reach counts, mode 'pass' (two passes):")
            nsteps = collections.Counter()
            for (k, step, micro), c in sorted(reach.items()):
                nsteps[(k, step)] += c
            print("  notes 0x08040D8A per step (units x microsteps x passes):", {s: c for (k, s), c in nsteps.items() if k == "n"})
            print("  notes per (step, micro) for step 4:", {m: c for (k, s, m), c in reach.items() if k == "n" and s == 4})
            print("  drums 0x0804AA18 per step:", {s: c for (k, s), c in nsteps.items() if k == "d"})
            print("  drums 0x080411F6 per step:", {s: c for (k, s), c in nsteps.items() if k == "s4"})
            print("  drums 0x080411F6 per (step, k):", sorted((s, m, c) for (k, s, m), c in reach.items() if k == "s4"))
            print("  registers (first reach):", regs)
    for kinds, name in ((("n_on", "n_off", "synth_on", "synth_off"), "notes"), (("d_on", "d_prev_off", "d_slot1_off", "d_sample"), "drums")):
        a, b, c = (sig(out[m], kinds) for m in ("roll", "force", "pass"))
        print(f"== {name}: roll == force: {a == b}; roll == pass: {a == c}; events roll {len(a)} force {len(b)} pass {len(c)}")
        if a != b:
            for i, (x, y) in enumerate(zip(a, b)):
                if x != y:
                    print("   first difference", i, x, y)
                    break
        print("   roll:", a[:40])
        print("   pass - roll:", [e for e in c if e not in a][:20])
    # the slot-4 forcing alone matters for the flip sample
    h, log, _, _ = run("force", force_s4=False)
    print("== drums forced at 0x0804AA1E only (not slot 4):", [e for e in sig(log, ("d_sample",))][:10],
          "vs roll:", sig(out["roll"], ("d_sample",))[:10])
