"""q1_route_a: route (a), the pending word rewritten at the commit's entry (lib.Route), on PL18's live strum.
Each case: Play, Record, a press at tick 40 (quantise on: step 7; off: step 6, microstep 4), held, let go.
Steps 4-11 hold two older notes (30, 31: units 0-1) unless said otherwise: they must survive. Checks every strum note
at its model position (Played: the first's step / microstep; Written: + k x gap ticks), lengths from end - start, and
that nothing else changed. naive = the stock unit kept (no re-pick)."""
from lib import GAP_TICKS, PATTERN_BASE, Route, W, pl18, put, setup, unit_map, wait_tick
from notes import step_addr

IMG, M = pl18()
OLD = [30, 31]
FILL = [70, 71, 72, 73, 74, 75]                      # a full step


def case(label, mode, speed=1, quantise=True, down=False, shape=1, bass=0, hold=600, naive=False, last=31,
         olds=range(4, 12), full=(), at=40, mono=False):
    h = setup(IMG, M, shape=shape, speed=speed, down=down, quantise=quantise, last=last, bass=bass)
    if mono:
        from test_mono import set_mono
        set_mono(h, M, 0)
    for s in olds:
        put(h, s, OLD)
    for s in full:
        put(h, s, FILL)
    before = {s: unit_map(h, s) for s in range(32)}
    r = Route(h, mode, GAP_TICKS[speed] if mode == "written" else 0, naive=naive)
    wait_tick(h, at)
    h.strum.clear()
    h.down(24)
    h.heartbeat(hold)
    h.up(24)
    h.heartbeat(400)
    first = next(e for e in r.log if e[0] == "first")[2]
    ends = {c["note"]: c["end"] for c in h.commits}
    per, lastp = 6, last
    expect = {}                                      # note -> (step, micro, gate)
    for k, n in enumerate(h.strum):
        if mode == "played":
            s, mi, st = first["step"], first["micro"], first["start"]
        else:
            six = first["micro"] + k * GAP_TICKS[speed]
            s, mi, st = first["step"] + six // 6, six % 6, first["start"] + k * GAP_TICKS[speed]
            while s > lastp:
                s -= lastp + 1
        held = (ends[n] - st) & 0x7FF
        if held >= 0x400:
            held = 1
        gate = 96 if held // per >= 16 else max(1, held)
        expect[n] = (s, mi, gate)
    got, problems = {}, []
    for s in range(32):
        now = unit_map(h, s)
        for u, v in now.items():
            if v[0] in expect:
                got.setdefault(v[0], []).append((s, v[2], v[1] & 0x7F))
        for u, v in before[s].items():
            if v[0] not in expect and now.get(u) != v and not mono:
                problems.append(f"old unit {u} of step {s} {v} -> {now.get(u)}")
    left_out = []
    for n, e in expect.items():
        g = got.get(n, [])
        if [e] != g:
            if not g and len(unit_map(h, e[0])) == 6:
                left_out.append(n)                    # its target step is full: left out
                continue
            problems.append(f"note {n}: want {e}, got {g}")
    edges = [x for x in r.log if x[0] != "first" and (x[0] == "no first" or x[3] != "latched" or x[-1])]
    print(f"{'OK  ' if not problems else 'FAIL'} {label}: order {h.strum}, first {first['step']}/{first['micro']}"
          f" start {first['start']}; tasks {[c['task'] + ':' + c['site'] for c in h.commits]}"
          + (f"; edges {edges}" if edges else "") + (f"; left out (step full) {left_out}" if left_out else ""))
    for p in problems:
        print("       ", p)
    if mono:
        print("        mono steps:", {s: [v[0] for v in unit_map(h, s).values()] for s in range(4, 12)})
    return h, r


def main():
    print("-- Played")
    for q in (True, False):
        for sp in (1, 2, 3):
            for dn in (False, True):
                case(f"played q{'on' if q else 'off'} speed {sp} {'falling' if dn else 'rising'}", "played", sp, q, dn)
    case("played q on slow, 9th + bass", "played", 1, True, shape=3, bass=1)
    case("played q off slow falling, 9th + bass", "played", 1, False, True, shape=3, bass=1)
    print("-- Written")
    for q in (True, False):
        for sp in (1, 2, 3):
            for dn in (False, True):
                case(f"written q{'on' if q else 'off'} speed {sp} {'falling' if dn else 'rising'}", "written", sp, q, dn)
    case("written q on slow, 9th + bass", "written", 1, True, shape=3, bass=1)
    case("written q off medium falling, 9th + bass", "written", 2, False, True, shape=3, bass=1)
    print("-- Wrap, full step, short release")
    case("written q on slow, last step 7 (spill wraps to step 0)", "written", 1, True, last=7, olds=(0, 1, 7))
    case("written q off slow, last step 7", "written", 1, False, last=7, olds=(0, 1, 6, 7))
    case("written q on slow, step 8 full (G left out)", "written", 1, True, olds=(7,), full=(8,))
    case("written q on slow, pressed at tick 40 (step 7), released at 170 ms", "written", 1, True, hold=170)
    print("-- Naive (stock's unit kept)")
    case("NAIVE played q on slow", "played", 1, True, naive=True)
    case("NAIVE written q on slow", "written", 1, True, naive=True)
    case("NAIVE written q off medium", "written", 2, False, naive=True)
    print("-- Mono record on (older notes cleared: not checked)")
    case("mono written q on medium falling 9th + bass", "written", 2, True, True, shape=3, bass=1, mono=True)
    case("mono written q on slow rising 9th + bass", "written", 1, True, False, shape=3, bass=1, mono=True)
    case("mono played q on slow falling 9th + bass", "played", 1, True, True, shape=3, bass=1, mono=True)


if __name__ == "__main__":
    main()
