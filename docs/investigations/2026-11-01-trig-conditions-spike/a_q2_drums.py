"""Q2 (drums): which stock edits keep / clear / move the condition bytes (+ 0x88 + step, bit step of + 0x84..+ 0x87),
each through its real route (re/app.asm: the dispatcher 0x0802DBC0 for pattern commands, 0x0802E10C for step
commands), each followed by a stock edit of the same step. Drum 1 (track 4), pattern 1 (0-based 0) shown, stopped
unless said. Hits have distinct velocities, so a moved hit can be traced; every step (hit or not) has a distinct code."""
from a_lib import *

HITS = {0: (100, 1, 7, 0xFF), 2: (90, 3, 5, 0xFF), 4: (80, 1, 7, 2), 5: (70, 1, 7, 0xFF), 8: (60, 0x21, 7, 0xFF),
        12: (50, 1, 6, 0xFF), 15: (40, 1, 7, 0xFF)}
D, T = 0, 4


def fresh(play_chain=None):
    h = H()
    h.leds()
    set_tempo(h, bpm=240)
    if play_chain is not None:
        h.set_chain(T, play_chain, play_chain)
    for p in range(8):
        h.set_dcond(D, p, dtag(D, p))
    h.set_dcond(D, 0, dcond_img())
    h.set_dhits(D, 0, HITS, load=False)
    h.dload(D)
    step_view(h, T)
    h.calls.clear()
    return h


def code_state(st, before, s):
    """What step s's condition is now: kept (its own code), zeroed, or another step's (moved / copied)."""
    code, bit = st[s][4], st[s][5]
    if code == before[s][4]:
        c = "kept"
    elif code == 0:
        c = "zeroed"
    else:
        src = dcode_of(before, code)
        c = f"= step {src}'s" if src is not None else f"junk {code:#x}"
    b = "bit kept" if bit == before[s][5] else f"bit {before[s][5]}->{bit}"
    return f"{c}, {b}"


def hit(st, s):
    v, m, p, f = st[s][:4]
    return f"v{v}/m{m:02x}/p{p}/f{f:02x}" if v or m else "empty"


def show(label, h, before, steps, routes):
    st = dsteps(h, D, 0)
    print(f"[{label}] route: {routes}")
    for s in steps:
        print(f"   step {s:2}: {hit(before, s):>18} -> {hit(st, s):>18}; condition {code_state(st, before, s)}")
    others = [s for s in range(32) if s not in steps and st[s][4:] != before[s][4:]]
    print(f"   other steps' conditions changed: {others or 'none'}; other patterns kept: "
          f"{all(h.dcond(D, p) == dtag(D, p) for p in range(1, 8))}")
    return st


def routes(h):
    seen = []
    for c in h.calls:
        if c[1] not in ("command send",) and c[1] not in seen:
            seen.append(c[1])
    h.calls.clear()
    return seen


if __name__ == "__main__":
    # 1. Clear step (Clear held + step pad), then a hit added on it (step pad)
    h = fresh(); b = dsteps(h, D, 0)
    h.hold(BTN["clear"]); h.pad(2); h.let_go(BTN["clear"])
    b2 = show("Clear step 3 (hit)", h, b, [2], routes(h))
    h.pad(2)
    show("  then step pad 3 (adds a hit)", h, b, [2], routes(h))

    # 2. Clear pattern (Patterns view, Clear held + pattern pad), stopped: the shown-pattern path
    h = fresh(); b = dsteps(h, D, 0)
    h.clear_pattern_pv(T, 0)
    st = dsteps(h, D, 0)
    print(f"[Clear pattern 1, stopped (shown)] route: {routes(h)}")
    print(f"   hits after: {[s for s in range(32) if st[s][0]]}; codes kept {sum(st[s][4] == b[s][4] for s in range(32))}/32,"
          f" zero {sum(st[s][4] == 0 for s in range(32))}/32; bit bytes {hexs(h.dcond(D, 0)[:4])} (before {hexs(DBITS)})")
    step_view(h, T); h.pad(2)
    show("  then step pad 3 (adds a hit)", h, b, [2], routes(h))

    # 2b. Clear pattern 1 while playing pattern 3 (not shown): the raw path
    h = fresh(play_chain=2); h.play(True); h.heartbeat(20); b = dsteps(h, D, 0)
    print(f"   (playing {h.track_playing(T)}, shown {h.dshown(D)})")
    h.clear_pattern_pv(T, 0)
    st = dsteps(h, D, 0)
    print(f"[Clear pattern 1, playing pattern 3 (not shown)] route: {routes(h)}")
    print(f"   hits after: {[s for s in range(32) if st[s][0]]}; codes kept {sum(st[s][4] == b[s][4] for s in range(32))}/32,"
          f" zero {sum(st[s][4] == 0 for s in range(32))}/32; bit bytes {hexs(h.dcond(D, 0)[:4])}")

    # 3. copy 1-16 -> 17-32 (Duplicate held + 1-16/17-32), then step 19 toggled (17-32 shown, step pad 3)
    h = fresh(); b = dsteps(h, D, 0)
    h.hold(BTN["dup"]); h.press(BTN["half"]); h.let_go(BTN["dup"])
    st = dsteps(h, D, 0)
    print(f"[copy 1-16 -> 17-32] route: {routes(h)}")
    print(f"   steps 17-32 arrays = steps 1-16: {all(st[s + 16][:4] == b[s][:4] for s in range(16))}")
    print(f"   steps 17-32 condition: {sorted(set(code_state(st, b, s) for s in range(16, 32)))}")
    print(f"   steps 1-16 condition: {sorted(set(code_state(st, b, s) for s in range(16)))}")
    h.pad(2)
    show("  then step pad 3 (the view shows 17-32 after the copy?)", h, b, [2, 18], routes(h))

    # 4. paste step (Duplicate held + step 3, step 8), then step pad 8 (removes the pasted hit)
    h = fresh(); b = dsteps(h, D, 0)
    h.hold(BTN["dup"]); h.pad(2); h.pad(7); h.let_go(BTN["dup"])
    show("paste step 3 -> 8", h, b, [2, 7], routes(h))
    h.pad(7)
    show("  then step pad 8", h, b, [7], routes(h))

    # 5. Mutate (Shift + Duplicate): hits move; do the codes follow them?
    h = fresh(); b = dsteps(h, D, 0)
    h.press(BTN["dup"], shift=True)
    st = dsteps(h, D, 0)
    print(f"[Mutate] route: {routes(h)}")
    vel_src = {b[s][0]: s for s in HITS}
    moved, follow = [], []
    for s in range(32):
        if st[s][0]:
            src = vel_src.get(st[s][0])
            moved.append((src, s))
            follow.append(f"{src}->{s}: code {code_state(st, b, s)}")
    print(f"   hits moved (from->to): {moved}")
    for f in follow:
        print(f"     {f}")
    print(f"   all codes in place: {all(st[s][4] == b[s][4] for s in range(32))}; bit bytes {hexs(h.dcond(D, 0)[:4])}")
    tgt = next(s for src, s in moved if src != s) if any(src != s for src, s in moved) else 0
    if tgt < 16:
        h.pad(tgt)
        show(f"  then step pad {tgt + 1}", h, b, [tgt], routes(h))

    # 6. add a hit (step pad on an empty step) and remove one (step pad on a hit)
    h = fresh(); b = dsteps(h, D, 0)
    h.pad(6)
    show("add a hit: step pad 7", h, b, [6], routes(h))
    h.pad(4)
    show("remove a hit: step pad 5", h, b, [4], routes(h))

    # 7. a drum editor store commit: the probability view, step 6 selected, row 3 pad 4 (probability 3)
    h = fresh(); b = dsteps(h, D, 0)
    prob_view(h, T); h.pad(5); h.pad(16 + 3)
    show("probability view: step 6, probability pad 4", h, b, [5], routes(h))
    h.pad(6); h.pad(16 + 2)
    show("  probability on empty step 7 (stock makes a hit)", h, b, [6], routes(h))

    # 8. a velocity view press (another store commit) on step 13
    h = fresh(); b = dsteps(h, D, 0)
    h.press(BTN["note"] + 1)                     # Velocity (10)
    h.pad(12); h.pad(16 + 5)
    show("velocity view: step 13, velocity pad 6", h, b, [12], routes(h))

    # 9. live recording: expanded view (Note twice), Play + Record, hits on the expanded view's sink every step
    h = fresh()
    h.press(T)
    for _ in range(4):
        if h.view_mode() == 6:
            break
        h.press(BTN["note"])
    b = dsteps(h, D, 0)
    sink = h.r32(h.r32(0x20040DB8 + 0xAC) + 0x10)
    h.play(True); h.press(BTN["record"]); h.heartbeat(2)
    t0 = h.ticks
    for k in range(32):
        h.until_tick(t0 + 6 * k + 1)
        h.nbusy = 0
        h.call(NOTE_ON, sink, 1, 0x50 + k, 0)
        h.heartbeat(3)
        h.call(NOTE_OFF, sink, 1, 0)
    h.until_tick(t0 + 6 * 33)
    h.press(BTN["record"]); h.play(False)
    st = dsteps(h, D, 0)
    rec_steps = [s for s in range(32) if st[s][0] != b[s][0]]
    print(f"[live recording, 32 hits] route: {routes(h)}")
    print(f"   steps whose hit changed: {rec_steps}")
    print(f"   conditions: {sorted(set(code_state(st, b, s) for s in range(32)))}")
