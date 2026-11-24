"""B4: tick 0 of a step at 0x0804A6B8, for both player classes, every sync rate (0-7 = 2 3 4 6 8 12 16 24 ticks a
step), muted tracks too: once a step, before the step's first microstep call (slot 1 in 0x0804A684, slots 4 / 2 in
0x0804A714), with the step's pattern / step in sb / r8 and the player in r7."""
import collections
from b_lib import *
from b_3_hand import fresh


def streams(h):
    """Per track: list of steps, each = dict(t0=(pattern, step), ev=[(kind, pattern, step, micro), ...])."""
    mi = iter(h.micro)
    t0i = iter(h.t0)
    out = collections.defaultdict(list)
    pre = collections.defaultdict(list)
    for tick, tag, t in h.order:
        if tag == "a6b8":
            x = next(t0i)
            out[t].append(dict(tick=tick, t0=(x[2], x[3]), ev=[]))
        elif tag in ("n1", "n2", "d1", "d2", "d4"):
            m = next(mi)
            rec = (tag, m[3], m[4], m[5])
            (out[t][-1]["ev"] if out[t] else pre[t]).append(rec)
        elif tag in ("a684", "a714"):
            (out[t][-1]["ev"] if out[t] else pre[t]).append((tag,))
    return out, pre


def check(h, muted=()):
    out, pre = streams(h)
    for t in range(8):
        steps = out[t][:-1]           # the last step may be cut by the end of the run
        rate = h.settings(t, 0)[2]
        bad = []
        s1 = "n1" if t < 4 else "d1"
        s2 = "n2" if t < 4 else "d2"
        n714 = 0
        for st in steps:
            ev = st["ev"]
            m1 = [e[3] for e in ev if e[0] == s1]
            m2 = [e[3] for e in ev if e[0] == s2]
            n4 = [e for e in ev if e[0] == "d4"]
            n714 += sum(1 for e in ev if e[0] == "a714")
            same = all((e[1], e[2]) == st["t0"] for e in ev if len(e) == 4)
            want2 = [] if t in muted else list(range(6))
            if m1 != list(range(6)) or m2 != want2 or not same or (t >= 4 and len(n4) != (0 if t in muted else 1)):
                bad.append((st["tick"], st["t0"], m1, m2, len(n4), same))
        print(f" track {t} rate {rate} ({STEP_TICKS[rate]} ticks){' MUTED' if t in muted else ''}: steps {len(steps)}, "
              f"bad {bad[:3] or '-'}; events before the first tick-0: {pre[t][:4] or '-'}; a714 calls {n714}")


print("== every rate, Synth 1..MIDI 2 = rates 0..3, Drum 1..4 = rates 4..7; then the same shifted (notes 4..7, drums 0..3)")
for shift in (0, 4):
    cfg = {t: dict(chain=(0, 0), pats={0: (7, 0, (t + shift) % 8, 0)}) for t in range(8)}
    h = fresh(cfg)
    h.clear_logs()
    h.play()
    h.run_ticks(24 * 8 * 2 + 5)
    check(h)
print("== muted: Synth 1 and Drum 1 muted (rate 3), Synth 2 / Drum 2 at rate 1 muted")
cfg = {t: dict(chain=(0, 0), pats={0: (7, 0, 1 if t in (1, 5) else 3, 0)}, mute=t in (0, 1, 4, 5)) for t in range(8)}
h = fresh(cfg)
h.clear_logs()
h.play()
h.run_ticks(120)
check(h, muted=(0, 1, 4, 5))
