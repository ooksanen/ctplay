"""B1: a pass at 0x0802CD42 with the real tick. Each scenario configures all 8 tracks (raw pattern settings + the
playing pattern's settings store + the chain store), presses Play, runs with heartbeats, and splits each track's
played steps (tick 0, 0x0804A6B8) at its pass events (0x0802CD42 with fp = 0 and r4 or the scene flag)."""
import collections
import sys
from b_lib import *

SCEN = {
    # 1: a looping single pattern on every track, 1/16, forward, 16 steps
    "loop": {t: dict(chain=(0, 0), pats={0: (15, 0, 3, 0)}) for t in range(8)},
    # 2: chains advancing by themselves, different lengths per pattern; first/last not at 1
    "chains": {
        0: dict(chain=(0, 1), pats={0: (15, 0, 3, 0), 1: (7, 0, 3, 0)}),
        1: dict(chain=(0, 2), pats={0: (15, 0, 3, 0), 1: (7, 0, 3, 0), 2: (4, 0, 3, 0)}),
        2: dict(chain=(2, 4), pats={2: (11, 4, 3, 0), 3: (31, 0, 3, 0), 4: (3, 28, 3, 0)}),   # 4: wraps 28..3
        3: dict(chain=(5, 6), pats={5: (12, 10, 3, 0), 6: (0, 0, 3, 0)}),                  # 6: one step
        4: dict(chain=(0, 1), pats={0: (15, 0, 3, 0), 1: (9, 2, 3, 0)}),
        5: dict(chain=(0, 2), pats={0: (5, 0, 3, 0), 1: (6, 0, 3, 0), 2: (7, 0, 3, 0)}),
        6: dict(chain=(3, 3), pats={3: (31, 0, 3, 0)}),
        7: dict(chain=(1, 2), pats={1: (2, 30, 3, 0), 2: (15, 15, 3, 0)}),
    },
    # 3: every direction (0 fwd, 1 rev, 2 ping-pong, 3 random), with first/last set, in loops and a chain
    "dirs": {
        0: dict(chain=(0, 0), pats={0: (11, 4, 3, 1)}),
        1: dict(chain=(0, 0), pats={0: (11, 4, 3, 2)}),
        2: dict(chain=(0, 0), pats={0: (11, 4, 3, 3)}),
        3: dict(chain=(0, 1), pats={0: (5, 0, 3, 2), 1: (3, 0, 3, 1)}),
        4: dict(chain=(0, 0), pats={0: (7, 0, 3, 1)}),
        5: dict(chain=(0, 0), pats={0: (7, 0, 3, 2)}),
        6: dict(chain=(0, 0), pats={0: (7, 0, 3, 3)}),
        7: dict(chain=(0, 1), pats={0: (3, 30, 3, 2), 1: (4, 0, 3, 3)}),                   # ping-pong over the wrap
    },
    # 4: every sync rate (0-7 = 2 3 4 6 8 12 16 24 ticks a step), drums each their own; chains of 2
    "rates": {t: dict(chain=(0, 1), pats={0: (7, 0, t, 0), 1: (3, 0, t, 0)}) for t in range(8)},
    # 5: muted tracks (Synth 1 and Drum 1 muted, Synth 2 / Drum 2 as controls), 2-pattern chains
    "mute": {
        0: dict(chain=(0, 1), pats={0: (7, 0, 3, 0), 1: (3, 0, 3, 0)}, mute=True),
        1: dict(chain=(0, 1), pats={0: (7, 0, 3, 0), 1: (3, 0, 3, 0)}),
        4: dict(chain=(0, 1), pats={0: (7, 0, 3, 0), 1: (3, 0, 3, 0)}, mute=True),
        5: dict(chain=(0, 1), pats={0: (7, 0, 3, 0), 1: (3, 0, 3, 0)}),
        2: dict(chain=(0, 0), pats={0: (15, 0, 3, 0)}), 3: dict(chain=(0, 0), pats={0: (15, 0, 3, 0)}),
        6: dict(chain=(0, 0), pats={0: (15, 0, 3, 0)}), 7: dict(chain=(0, 0), pats={0: (15, 0, 3, 0)}),
    },
}


def check_track(h, t, c):
    segs, problems = split_passes(h, t)
    first_seg, rest = segs[0], segs[1:]
    if rest and not rest[-1]:
        rest = rest[:-1]
    complete = rest[:-1]          # the last one is cut by the end of the run
    bad = []
    # pattern order of the chain
    ch = c["chain"]
    order = list(range(ch[0], ch[1] + 1))
    pats = [s[0][0] for s in [first_seg] + complete if s]
    for i, p in enumerate(pats):
        if p != order[i % len(order)]:
            bad.append(("chain order", i, p, order))
            break
    for i, seg in enumerate([first_seg] + complete):
        if not seg:
            bad.append(("empty segment", i))
            continue
        ps = {p for p, s in seg}
        if len(ps) != 1:
            bad.append(("pattern changes inside a pass", i, seg))
            continue
        p = seg[0][0]
        last, first, rate, d = c["pats"][p]
        steps = [s for _, s in seg]
        want = expected_pass(last, first, d)
        if want is not None and steps != want:
            bad.append(("steps", i, p, steps, want))
        if d == 3:
            n = (last - first) % 32 + 1
            inrange = all(((s - first) % 32) < n for s in steps)
            if len(steps) != n or not inrange:
                bad.append(("random pass", i, p, steps, n))
    # the registers at 0x0802CD42: sb = the pattern that just ended, track = [sp + 0xC] = (r7 - E) / 4
    ev = passes_from_adv(h.adv, t)
    for a, seg in zip(ev, segs):
        if seg and a[2] != seg[-1][0]:
            bad.append(("sb is not the ended pattern", a, seg[-1]))
        if a[6] or a[7]:
            bad.append(("scene / hand flag set without a scene or hand change", a))
    return segs, problems, bad


def run(name, ticks):
    cfg = SCEN[name]
    h = B()
    h.leds()
    set_tempo(h, bpm=240)
    configure(h, cfg)
    h.clear_logs()
    h.play()
    h.run_ticks(ticks)
    print(f"== {name}: {h.tick} ticks")
    kinds = collections.Counter((a[1], a[4], bool(a[5]), bool(a[6])) for a in h.adv)
    for t in sorted(cfg):
        c = cfg[t]
        segs, problems, bad = check_track(h, t, c)
        npass = len([a for a in passes_from_adv(h.adv, t)])
        la_end = sum(v for k, v in kinds.items() if k[0] == t and k[1] == 1 and k[2])
        la_all = sum(v for k, v in kinds.items() if k[0] == t and k[1] == 1)
        mid = kinds.get((t, 0, False, False), 0)
        print(f" track {t}: passes counted {npass}; fp=0 steps not ending {mid}; look-ahead entries {la_all} (with r4 {la_end}); "
              f"tick-0 calls {len([x for x in h.t0 if x[1] == t])}; problems {problems or '-'}; bad {bad or '-'}")
        show = [(s[0][0], [x for _, x in s]) if s else None for s in segs[:6]]
        print("   passes:", show)
    # global order: a684 vs a714 in a tick, and cd42 before a6b8
    return h


if __name__ == "__main__":
    names = sys.argv[1:] or list(SCEN)
    ticks = {"loop": 400, "chains": 700, "dirs": 500, "rates": 1300, "mute": 400}
    for n in names:
        run(n, ticks[n])
