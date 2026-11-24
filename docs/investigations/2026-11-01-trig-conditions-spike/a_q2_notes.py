"""Q2 (note tracks): which stock edits keep / clear / move step bytes [2] / [3], each through its real route, each
followed by a stock edit of the same step. Synth 1 (track 0), pattern 1 (0-based 0) shown, stopped unless said, the
two-row Note view (pads 0-15 = steps, 16-31 = keys; pad 24 = C). Every step has a distinct [2] / [3] tag (ntag)."""
from a_lib import *
from notes import fill

T = 0
NOTES = {0: [60], 2: [62, 65], 4: [64], 8: [67], 12: [69, 72, 76]}
KEY, KEY2 = 24, 30


def fresh(play_chain=None, sync=True):
    h = H()
    h.leds()
    set_tempo(h, bpm=240)
    if play_chain is not None:
        h.set_chain(T, play_chain, play_chain)
    for s, n in NOTES.items():
        fill(h, T, 0, s, n)
    for p in range(8):
        h.set_nb23(T, p, ntag(T, p))
    if sync:
        h.sync_nstore(T)
    step_view(h, T)
    from notes import fixed_velocity
    h.calls.clear()
    return h


def tag_state(h, before, s):
    now = h.nb23(T, 0)[2 * s:2 * s + 2]
    if now == before[2 * s:2 * s + 2]:
        return "kept"
    if now == b"\0\0":
        return "zeroed"
    for k in range(32):
        if now == before[2 * k:2 * k + 2]:
            return f"= step {k}'s"
    for p in range(8):
        tg = ntag(T, p)
        for k in range(32):
            if now == tg[2 * k:2 * k + 2]:
                return f"= pattern {p} step {k}'s"
    return f"junk {now.hex()}"


def notes_of(h, s):
    st = h.nstep(T, 0, s)
    return [st[4 + 4 * u] for u in range(6) if st[0] >> u & 1]


def routes(h):
    seen = []
    for c in h.calls:
        if c[1] != "command send" and c[1] not in seen:
            seen.append(c[1])
    h.calls.clear()
    return seen


def show(label, h, before, steps, rt):
    print(f"[{label}] route: {rt}")
    for s in steps:
        print(f"   step {s:2}: notes {notes_of(h, s)} prob {h.nstep(T, 0, s)[1]}; [2]/[3] {tag_state(h, before, s)}")
    others = [s for s in range(32) if s not in steps and tag_state(h, before, s) != "kept"]
    print(f"   other steps changed: {[(s, tag_state(h, before, s)) for s in others] or 'none'}; other patterns kept: "
          f"{all(h.nb23(T, p) == ntag(T, p) for p in range(1, 8))}")


def step_entry(h, step, key):
    h.down(step); h.down(key); h.up(key); h.up(step); h.heartbeat(3)


def prob_press(h, step, value, select=True):
    prob_view(h, T)
    if select:
        h.pad(step)
    h.pad(16 + value)
    step_view(h, T)


if __name__ == "__main__":
    # 1. Clear step (Clear held + step pad); the store's selected step is step 1 (not the cleared one)
    h = fresh(); b = h.nb23(T, 0)
    print(f"(selected step before: {h.nselected(T)}, store word 0 {hexs(h.nstore_word0(T))})")
    h.hold(BTN["clear"]); h.pad(2); h.let_go(BTN["clear"])
    show("Clear step 3 (notes)", h, b, [2], routes(h))
    print(f"   (selected step now {h.nselected(T)}, store word 0 {hexs(h.nstore_word0(T))})")
    step_entry(h, 2, KEY)
    show("  then step entry: step 3 + key C", h, b, [2], routes(h))
    prob_press(h, 2, 3)
    show("  then probability view: step 3, probability 4", h, b, [2], routes(h))

    # 1b. Clear step of the selected step itself
    h = fresh(); b = h.nb23(T, 0)
    h.hold(BTN["clear"]); h.pad(0); h.let_go(BTN["clear"])
    show("Clear step 1 (the selected step)", h, b, [0], routes(h))

    # 2. Clear pattern (Patterns view), stopped (shown)
    h = fresh(); b = h.nb23(T, 0)
    h.clear_pattern_pv(T, 0)
    kept = sum(tag_state(h, b, s) == "kept" for s in range(32))
    print(f"[Clear pattern 1, stopped] route: {routes(h)}; [2]/[3] kept {kept}/32; "
          f"notes left {[s for s in range(32) if notes_of(h, s)]}; store word 0 {hexs(h.nstore_word0(T))}")
    step_view(h, T); step_entry(h, 2, KEY)
    show("  then step entry: step 3 + key C", h, b, [2], routes(h))

    # 2b. Clear pattern 1 while playing pattern 3 (not shown)
    h = fresh(play_chain=2); h.play(True); h.heartbeat(20); b = h.nb23(T, 0)
    h.clear_pattern_pv(T, 0)
    kept = sum(tag_state(h, b, s) == "kept" for s in range(32))
    print(f"[Clear pattern 1, playing 3] route: {routes(h)}; [2]/[3] kept {kept}/32; "
          f"notes left {[s for s in range(32) if notes_of(h, s)]}")

    # 3. step entry: add to a step with notes, add to an empty step, remove a note
    h = fresh(); b = h.nb23(T, 0)
    step_entry(h, 4, KEY2)
    show("step entry: add key 31 to step 5 (has a note)", h, b, [4], routes(h))
    step_entry(h, 6, KEY)
    show("step entry: add key C to empty step 7", h, b, [6], routes(h))
    step_entry(h, 6, KEY)
    show("step entry: key C again on step 7 (removes it)", h, b, [6], routes(h))
    prob_press(h, 4, 2)
    show("  then probability view: step 5, probability 3", h, b, [4], routes(h))

    # 4. recording over a step: Play + Record armed, key C held over steps 5 and 6 (pattern 1 playing)
    h = fresh(play_chain=0); h.play(True); h.press(BTN["record"]); h.heartbeat(2); b = h.nb23(T, 0)
    t0 = h.ticks
    h.until_tick(t0 + 6 * 4 + 1); h.down(KEY)
    h.until_tick(t0 + 6 * 5 + 3); h.up(KEY)
    h.until_tick(t0 + 6 * 12)
    h.press(BTN["record"]); h.play(False)
    ch = [s for s in range(32) if notes_of(h, s) != NOTES.get(s, [])]
    print(f"   (steps whose notes changed: {ch}; started at tick {t0})")
    show("recording key C over the playhead", h, b, ch, routes(h))
    if ch:
        prob_press(h, ch[0], 4)
        show(f"  then probability view: step {ch[0] + 1}, probability 5", h, b, [ch[0]], routes(h))

    # 5. paste step (Duplicate held + step 3, step 8)
    h = fresh(); b = h.nb23(T, 0)
    h.hold(BTN["dup"]); h.pad(2); h.pad(7); h.let_go(BTN["dup"])
    show("paste step 3 -> 8", h, b, [2, 7], routes(h))
    prob_press(h, 7, 1)
    show("  then probability view: step 8, probability 2", h, b, [7], routes(h))

    # 6. copy 1-16 -> 17-32
    h = fresh(); b = h.nb23(T, 0)
    h.hold(BTN["dup"]); h.press(BTN["half"]); h.let_go(BTN["dup"])
    print(f"[copy 1-16 -> 17-32] route: {routes(h)}")
    print(f"   steps 17-32: {sorted(set(tag_state(h, b, s) for s in range(16, 32)))[:4]} ...; all = steps 1-16: "
          f"{all(h.nb23(T, 0)[2 * (s + 16):2 * (s + 17)] == b[2 * s:2 * s + 2] for s in range(16))}")
    print(f"   steps 1-16 kept: {all(tag_state(h, b, s) == 'kept' for s in range(16))}")

    # 7. Mutate (Shift + Duplicate): do [2] / [3] move with the step's notes?
    h = fresh(); b = h.nb23(T, 0)
    before_notes = {s: NOTES.get(s, []) for s in range(32)}
    h.press(BTN["dup"], shift=True)
    print(f"[Mutate] route: {routes(h)}")
    moved, ok = [], True
    for s in range(32):
        st = tag_state(h, b, s)
        src = int(st.split()[2][:-2]) if st.startswith("= step") else (s if st == "kept" else None)
        if src is None or notes_of(h, s) != before_notes[src]:
            ok = False
        if src != s:
            moved.append((src, s))
    print(f"   steps moved (from->to, by their [2]/[3]): {moved}")
    print(f"   [2]/[3] travel with the step's notes everywhere: {ok}")

    # 8. the mirrored selected step: a raw [2]/[3] write to it, no store sync, then a probability press
    for select in (False, True):
        h = fresh(sync=False); b = h.nb23(T, 0)
        print(f"[raw write, store not synced] selected step {h.nselected(T)}, store word 0 {hexs(h.nstore_word0(T))}, "
              f"pattern {hexs(h.nstep(T, 0, 0)[:4])}")
        prob_press(h, 0, 4, select=select)
        show(f"  probability view{' (step pad 1 pressed first)' if select else ' (no step pad)'}: probability 5",
             h, b, [0], routes(h))
    h = fresh(sync=True); b = h.nb23(T, 0)
    prob_press(h, 0, 4, select=False)
    show("[raw write + store synced] probability view (no step pad): probability 5", h, b, [0], routes(h))
