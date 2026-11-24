"""B3: hand changes while playing. Patterns view (13): a tap (pattern), a held range (chain); Mixer (14): a scene pad
(rows 3-4). When each takes over, what 0x0802CD42 sees then, and what is readable during the last pass before it."""
import sys
from harness import MGR, PAD_PRESS, PAD_RELEASE
from b_lib import *


def fresh(cfg=None, bpm=240):
    h = B()
    h.leds()
    set_tempo(h, bpm=bpm)
    configure(h, cfg or {t: dict(chain=(0, 0), pats={p: (7, 0, 3, 0) for p in range(8)}) for t in range(8)})
    return h


def timeline(h, tracks, ticks, every=1):
    """Run `ticks` ticks; print, per tick where something changes, the tracks' (playing pattern, step, flag)."""
    prev = None
    out = []
    for _ in range(ticks):
        h.run_ticks(1)
        cur = tuple((h.playing(t)[0], h.playing(t)[1], h.chain_flag(t)) for t in tracks)
        if cur != prev:
            out.append((h.tick, cur))
        prev = cur
    return out


def pass_events(h, t):
    return [(a[0], dict(old=a[2], r4=a[5], scene=a[6], hand=a[7])) for a in h.adv if a[1] == t and a[4] == 0 and (a[5] or a[6])]


def show(h, tracks):
    for t in tracks:
        print(f"  track {t} pass events (tick, ...):", pass_events(h, t))
        print(f"  track {t} chosen after them:", [(c[0], c[2], c[3]) for c in h.chosen if c[1] == t and c[4] == 0
                                                 and any(a[0] == c[0] for a in h.adv if a[1] == t and a[4] == 0 and (a[5] or a[6]))])


def a_tap():
    print("== A: Patterns view, tap pattern 2 of Synth 1 (pad 16) and of Drum 1 (pad 20) at tick 20, 8-step loops")
    h = fresh()
    h.press(13)
    h.play()
    h.run_ticks(20)
    h.clear_logs()
    h.pad(16); h.pad(20)
    print("  right after the taps:", snapshot(h)["chains"][:5], "flags", snapshot(h)["flags"], "queued", snapshot(h)["queued"][:5])
    tl = timeline(h, (0, 4), 120)
    print("  timeline (tick, [(pattern, step, flag) for Synth 1, Drum 1]):", [x for x in tl if x[1][0][1] in (0, 7) or x[1][0][2] == 0][:12])
    show(h, (0, 4))


def b_range():
    print("== B: Patterns view, hold pad 8 then pad 24 (Synth 1 patterns 1..3), release, at tick 20")
    h = fresh()
    h.press(13)
    h.play()
    h.run_ticks(20)
    h.clear_logs()
    h.down(8); h.down(24); h.up(24); h.up(8)
    print("  after:", snapshot(h)["chains"][:2], "flags", snapshot(h)["flags"][:2])
    h.run_ticks(200)
    show(h, (0,))


def c_pingpong():
    print("== C: ping-pong Synth 1 (8 steps, round trip 16), forward Synth 2; tap pattern 1 for both at tick 8")
    cfg = {t: dict(chain=(0, 0), pats={p: (7, 0, 3, 2 if t == 0 else 0) for p in range(8)}) for t in range(8)}
    h = fresh(cfg)
    h.press(13)
    h.play()
    h.run_ticks(8)
    h.clear_logs()
    h.pad(8); h.pad(9)
    h.run_ticks(150)
    show(h, (0, 1))
    print("  Synth 1 steps (tick, pattern, step):", steps_played(h.t0, 0)[:20])


def c2_random():
    print("== C2: random Synth 1 (8 steps); tap pattern 1 at tick 8")
    cfg = {t: dict(chain=(0, 0), pats={p: (7, 0, 3, 3 if t == 0 else 0) for p in range(8)}) for t in range(8)}
    h = fresh(cfg)
    h.press(13)
    h.play()
    h.run_ticks(8)
    h.clear_logs()
    h.pad(8)
    h.run_ticks(150)
    show(h, (0,))


def c3_chain_tap():
    print("== C3: Synth 1 in a chain 0..2 (8 steps each), tap pattern 3 during pattern 1 (a chain pass mid-way)")
    cfg = {t: dict(chain=(0, 2) if t == 0 else (0, 0), pats={p: (7, 0, 3, 0) for p in range(8)}) for t in range(8)}
    h = fresh(cfg)
    h.press(13)
    h.play()
    h.run_ticks(48 + 20)
    h.clear_logs()
    h.pad(24)
    print("  flag", h.chain_flag(0), "chain", h.chain(0), "queued", h.queued(0)[:2].hex(), "playing", h.playing(0))
    h.run_ticks(150)
    show(h, (0,))


if __name__ == "__main__":
    for n in sys.argv[1:] or ["a_tap", "b_range", "c_pingpong", "c2_random", "c3_chain_tap"]:
        globals()[n]()
