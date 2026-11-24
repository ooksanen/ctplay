"""Q1 (drums, removals): which view and which press reach drum_step_off 0x0804EC3E (caller 0x0804ECA4 in the toggle
0x0804EC8A) and drum_remove 0x080500B2 (caller 0x0804FFBC in the listener 0x0804FF18), the step each acts on and the
pattern (= the drum's shown one?). Presses and releases are split (h.down / h.up), each through the controller.
Drum 1: hits on steps 1, 4 (flip sample 2), 7, 13, 21 (0-based 0, 3, 6, 12, 20)."""
from q_lib import *

HITS = {0: (100, 1, 7, 0xFF), 3: (90, 3, 5, 2), 6: (80, 0x21, 7, 0xFF), 12: (70, 1, 2, 0xFF), 20: (65, 1, 7, 0xFF)}
WATCH = {0x0804EC8A: "toggle", 0x0804EC18: "step_on", 0x0804EC3E: "drum_step_off", 0x0804FF18: "flip_listener",
         0x08050062: "flip_add_hit", 0x080500B2: "drum_remove"}


def fields(h, r, sp):
    try:
        return _fields(h, r, sp)
    except Exception as e:  # noqa: BLE001  (an exception inside a Unicorn hook breaks the run)
        return dict(err=str(e), vclass=0)


def _fields(h, r, sp):
    """r0's step store ([r0 + 0xC] for the step view, [r0 + 8] for the flip listener) against each drum editor's
    step store [editor + 0x18]; the editor's shown pattern / selected step; the listener's store [r0 + 4] p0 / p1."""
    out = {}
    for off in (0xC, 8):
        st = h.r32(r[0] + off) if r[0] >= 0x20000000 else 0
        for d in range(4):
            if st and st == h.r32(h.deditor(d) + 0x18):
                out["drum"] = d
                out["via"] = f"[r0+{off:#x}]"
                out["shown"] = h.dshown_py(d)
                out["sel"] = h.dselected_py(d)
    if "via" in out and out["via"] == "[r0+0x8]":
        s4 = h.r32(r[0] + 4)
        out["l4"] = (h.store_p(s4, 0, 1)[0], h.store_p(s4, 1, 1)[0])
    out["mode"] = h.view_mode()
    out["vclass"] = h.r32(r[0]) if r[0] >= 0x20000000 else 0
    return out


def fresh(chain=None):
    h = Q()
    h.leds()
    set_tempo(h, bpm=240)
    if chain is not None:
        h.set_chain(4, chain, chain)
    for p in range(8):
        h.set_dcond(0, p, dtag(0, p))
    h.set_dhits(0, 0, HITS, load=False)
    h.set_dhits(0, 2, HITS, load=False)
    h.dload(0)
    for a, n in WATCH.items():
        h.log_at(a, n, fields)
    return h


def vel(h, p=None):
    p = h.dshown(0) if p is None else p
    return [h.dpattern(0, p)[s] for s in range(32)]


def show(h, label):
    for e in h.elog:
        f = {k: e[k] for k in ("drum", "via", "shown", "sel", "l4", "mode", "err") if k in e}
        print(f"   {e['phase']:<8} {e['name']:<14} [{e['ctx']}] r0={e['r'][0]:#x} (class {e['vclass']:#x}) "
              f"r1={e['r'][1]} {f}")
    h.elog.clear()


def tap(h, pad, label):
    b = vel(h)
    h.phase = "press"
    h.down(pad)
    h.phase = "release"
    h.up(pad)
    h.phase = "-"
    a = vel(h)
    print(f"[{label}] pad {pad}: velocities changed at {[(s, b[s], a[s]) for s in range(32) if a[s] != b[s]]}")
    show(h, label)


def open_mode(h, mode):
    h.press(4)
    for btn in (BTN["note"], 10, 11, BTN["pset"]):
        for _ in range(3):
            if h.view_mode() == mode:
                return True
            h.press(btn)
    return h.view_mode() == mode


if __name__ == "__main__":
    print("== drum_step_off: a step pad tapped on a hit / an empty step, per view (drum 1)")
    for mode in (1, 2, 3, 5):
        h = fresh()
        if not open_mode(h, mode):
            print(f"[mode {mode}] not reached")
            continue
        h.elog.clear()
        tap(h, 6, f"mode {mode}, hit")
        tap(h, 6, f"mode {mode}, now empty")
    h = fresh()
    step_view(h, 4)
    h.press(BTN["half"])
    h.elog.clear()
    tap(h, 4, "mode 1, 17-32 shown, hit on step 21")
    h = fresh(chain=2)
    step_view(h, 4)
    h.play(True)
    h.heartbeat(30)
    h.elog.clear()
    tap(h, 3, f"mode 1, playing pattern 3 (shown {h.dshown(0)}), hit on step 4")
    h = fresh()
    step_view(h, 4)
    h.phase = "press"
    h.down(6)
    h.heartbeat(600)
    h.phase = "release"
    h.up(6)
    print(f"[mode 1, hit held 600 ms then released] velocities now step 7 = {vel(h)[6]}")
    show(h, "held")

    print("\n== drum_remove: hold a step pad, press a lower pad (drum 1, step view)")
    for step, label in ((3, "step 4 (hit, flip sample 2)"), (6, "step 7 (hit, no flip)"), (9, "step 10 (empty)")):
        for pad in range(16, 32):
            h = fresh()
            step_view(h, 4)
            b = vel(h)
            fb = h.dpattern(0, 0)[0x40 + step]
            h.elog.clear()
            h.phase = "step down"
            h.down(step)
            h.elog.clear()
            h.phase = "pad"
            h.down(pad)
            h.up(pad)
            h.phase = "step up"
            h.up(step)
            a = vel(h)
            names = [e["name"] for e in h.elog]
            if "drum_remove" in names or "flip_listener" in names:
                fa = h.dpattern(0, 0)[0x40 + step]
                print(f"[{label}] lower pad {pad}: velocity {b[step]} -> {a[step]}, flip {fb:#x} -> {fa:#x}; "
                      f"others changed {[s for s in range(32) if s != step and a[s] != b[s]]}")
                show(h, label)
            h.elog.clear()
    # the same sample pad twice while the step stays held
    h = fresh()
    step_view(h, 4)
    h.phase = "step down"
    h.down(9)
    for k in range(2):
        h.phase = f"pad 16 #{k + 1}"
        h.down(16)
        h.up(16)
    h.phase = "step up"
    h.up(9)
    print(f"[step 10 held, lower pad 16 twice] velocity of step 10 now {vel(h)[9]}, flip {h.dpattern(0, 0)[0x49]:#x}")
    show(h, "twice")

    print("\n== the same on drum 2 (is the view / listener per drum, and does [r0 + 0xC] / [r0 + 8] name the drum?)")
    h = fresh()
    h.set_dhits(1, 0, HITS, load=False)
    h.dload(1)
    step_view(h, 5)
    h.elog.clear()
    b = [h.dpattern(1, 0)[s] for s in range(32)]
    h.phase = "release"
    h.pad(6)
    print(f"[drum 2, step pad 7 tapped] drum 2 velocities changed at "
          f"{[s for s in range(32) if h.dpattern(1, 0)[s] != b[s]]}")
    show(h, "drum 2")
    h.phase = "step down"
    h.down(3)
    h.phase = "pad"
    h.down(18)
    h.up(18)
    h.up(3)
    print(f"[drum 2, step 4 held + lower pad 18 (its flip sample 2)] drum 2 step 4 velocity {h.dpattern(1, 0)[3]}")
    show(h, "drum 2 remove")
