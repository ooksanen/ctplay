"""q1_baseline: what PL18 records for a live strum (no route): the recorder's calls in order and the pattern.
Triad on pad 24, rising, slow / fast, quantise on / off; held 400 ms, or tapped 30 ms (released before the next tick
pass). Also a 9th with bass, fast, tapped (6 placements between passes: the list index wraps)."""
from lib import PLAY, W, pl18, setup, step_ms, units, written, wait_tick

IMG, M = pl18()


def run(label, speed, quantise, hold, shape=1, bass=0, at=None):
    h = setup(IMG, M, shape=shape, speed=speed, quantise=quantise, bass=bass)
    if at is not None:
        wait_tick(h, at)
    h.places.clear(); h.passes.clear(); h.commits.clear(); h.noteoffs.clear(); h.strum.clear()
    t0 = h.ms
    h.down(24)
    h.heartbeat(hold)
    h.up(24)
    h.heartbeat(400)
    print(f"== {label}: speed {speed}, quantise {'on' if quantise else 'off'}, held {hold} ms; step {step_ms(h):.0f} ms;"
          f" placement order {h.strum}")
    ev = [(p["ms"] - t0, "place", p["task"], f"n{p['note']} s{p['step']} off{p['off']} start{p['start']} idx{p['idx']}")
          for p in h.places]
    ev += [(c["ms"] - t0, "commit", c["task"], f"n{c['note']} end{c['end']} {c['site']} {W(c['word'])}") for c in h.commits]
    ev += [(o[0] - t0, "noteoff", o[1], f"n{o[2]} end{o[3] & 0x7FF}") for o in h.noteoffs]
    first_pass = [p for p in h.passes if p[0] >= t0][:4]
    ev += [(p[0] - t0, "pass", p[1], f"pattern {p[2]} step {p[3]} tick {p[4]}") for p in first_pass]
    for e in sorted(ev, key=lambda e: e[0]):
        print("  ", e)
    print("   written:", written(h))


run("A slow held", 1, True, 400, at=40)
run("B fast held", 3, True, 400, at=40)
run("C slow held, quantise off", 1, False, 400, at=40)
run("D fast tapped", 3, True, 30, at=40)
run("E 9th + bass, fast, tapped", 3, True, 30, shape=3, bass=1, at=40)
run("F 9th + bass, fast, tapped, quantise off", 3, False, 30, shape=3, bass=1, at=40)
