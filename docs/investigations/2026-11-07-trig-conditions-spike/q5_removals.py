"""Q5: every stock route that empties a note step ([0] -> 0) or a drum step (velocity -> 0), besides the ones PL20
already hooks or handles (note_pad_press's removal, Clear step / pattern, drum_step_off 0x0804EC3E, drum_remove
0x080500B2, paste / copy half / Mutate / Duplicate, which carry or clear the code themselves).

Sweep, stock image, Drum 1 (hits on 1, 4, 7, 13, 21) and Synth 1 (notes on 1, 4, 7, 13, 21), stopped, pattern 1:
every view mode a track reaches (drums 1-6, notes 1-6 and 8), every pad 0-31 as (a) a plain tap, (b) a tap with
step 4 (index 3, a hit / a note) held and (c) a tap with Shift held, step 4 selected beforehand in the velocity view. Then button routes: Clear held
+ each pad in modes 1 and 6, Clear held + each track button, live recording (Play + Record) with Clear held for a pass,
with and without a pad held. A route that empties a step is re-run with a memory-write hook on the pattern byte to
name the writer (crude backtrace: the return addresses on the stack)."""
from unicorn import UC_HOOK_MEM_WRITE

from q_lib import *
from notes import PATTERN_BASE, fill

HIT_STEPS = (0, 3, 6, 12, 20)
DHITS = {s: (100 - s, 1, 7, 0xFF) for s in HIT_STEPS}
DHITS[3] = (90, 1, 7, 2)                      # step 4: flip sample 2 (so a lower pad can match it)
KNOWN = {0x0804EC3E: "drum_step_off", 0x080500B2: "drum_remove", 0x0803E18A: "drum_clear_step",
         0x0803E3B0: "drum_clear_pattern", 0x0803DFAE: "drum_paste_step", 0x0803E93A: "drum_copy_half",
         0x0803E6F0: "drum_mutate", 0x0803E2AA: "drum_duplicate", 0x0803D1D4: "note_clear_step",
         0x0803D310: "note_clear_pattern", 0x0804AB5A: "note_pad_press", 0x0803D16E: "note_paste_step",
         0x0803DD24: "note_copy_half", 0x0803D53C: "note_mutate", 0x0803D2B0: "note_duplicate",
         0x0803F7BE: "note_rec_commit", 0x0803FA26: "drum_rec_write", 0x0804B094: "step_add"}
MODES = {"drum": (1, 2, 3, 4, 5, 6), "note": (1, 2, 3, 4, 5, 6, 8)}


def fresh(kind, watch=False):
    h = Q()
    h.leds()
    set_tempo(h, bpm=240)
    if kind == "drum":
        h.set_dhits(0, 0, DHITS, load=False)
        h.dload(0)
    else:
        for s in HIT_STEPS:
            fill(h, 0, 0, s, [60 + s])
        h.sync_nstore(0)
    h.known = []
    for a, n in KNOWN.items():
        def f(hh, r, sp, n=n):
            hh.known.append(n)
        h.handler_at(a, f)
    h.zero_writes = []
    if watch:
        lo, hi = (h.dbase(0), h.dbase(0) + 8 * DPAT) if kind == "drum" else (PATTERN_BASE[0], PATTERN_BASE[0] + 8 * NPAT)

        def w(u, acc, addr, size, value, d):
            o = (addr - lo) % (DPAT if kind == "drum" else NPAT)
            hit = (o < 32) if kind == "drum" else (o < 32 * NSTEP and o % NSTEP == 0)
            if hit and value & 0xFF == 0 and h.r8(addr) != 0:
                h.zero_writes.append((addr, f"{u.reg_read(UC_ARM_REG_PC):#010x}", h.backtrace()[:8]))
        h.uc.hook_add(UC_HOOK_MEM_WRITE, w, begin=lo, end=hi - 1)
    return h


def filled(h, kind):
    if kind == "drum":
        return {(p, s) for p in range(8) for s in range(32) if h.dpattern(0, p)[s]}
    return {(p, s) for p in range(8) for s in range(32) if h.nstep(0, p, s)[0]}


def open_mode(h, kind, mode):
    t = 4 if kind == "drum" else 0
    h.press(t)
    if mode != 1:            # select step 4 in the velocity view first (a tap in mode 1 toggles)
        for _ in range(3):
            if h.view_mode() == 2:
                break
            h.press(10)
        h.pad(3)
    seqs = {1: [9, 9], 2: [10], 3: [11], 4: [12], 5: [12, 12], 6: [9], 8: [11, 11]}
    for _ in range(2):
        if h.view_mode() == mode:
            break
        for b in seqs[mode]:
            h.press(b)
            if h.view_mode() == mode:
                break
    return h.view_mode() == mode


def gesture(h, pad, held):
    if held == "shift":
        h.shift(True)
        h.down(pad)
        h.up(pad)
        h.shift(False)
        return
    if held:
        h.down(3)
    h.down(pad)
    h.up(pad)
    if held:
        h.up(3)


def sweep(kind):
    found = []
    for mode in MODES[kind]:
        for held in (False, True, "shift"):
            for pad in range(32):
                if held is True and pad == 3:
                    continue
                h = fresh(kind)
                if not open_mode(h, kind, mode):
                    print(f"   {kind} mode {mode}: not reached")
                    break
                before = filled(h, kind)
                h.known.clear()
                gesture(h, pad, held)
                gone = sorted(before - filled(h, kind))
                if gone:
                    found.append((mode, held, pad, gone, sorted(set(h.known))))
    return found


def explain(kind, mode, held, pad):
    h = fresh(kind, watch=True)
    open_mode(h, kind, mode)
    h.zero_writes.clear()
    h.known.clear()
    gesture(h, pad, held)
    return h.zero_writes[:2], sorted(set(h.known))


def button_routes(kind):
    t = 4 if kind == "drum" else 0
    out = []

    def run(label, fn):
        h = fresh(kind)
        h.press(t)
        before = filled(h, kind)
        h.known.clear()
        fn(h)
        gone = sorted(before - filled(h, kind))
        zw = []
        if gone and not h.known:      # name the writer (Unicorn's write hook can fail inside stock's memset IT loop)
            try:
                w = fresh(kind, watch=True)
                w.press(t)
                fn(w)
                zw = w.zero_writes[:1]
            except Exception as e:  # noqa: BLE001
                zw = [(0, f"watch failed: {e}", [])]
        out.append((label, gone, sorted(set(h.known)), zw))

    for mode in (1, 6):
        for pad in range(32):
            def f(h, pad=pad, mode=mode):
                open_mode(h, kind, mode)
                h.hold(BTN["clear"])
                h.pad(pad)
                h.let_go(BTN["clear"])
            run(f"Clear held + pad {pad}, mode {mode}", f)
    for b in range(8):
        def f(h, b=b):
            h.hold(BTN["clear"])
            h.press(b)
            h.let_go(BTN["clear"])
        run(f"Clear held + track button {b}", f)
    for pad in (None, 3, 20, 28):
        def f(h, pad=pad):
            open_mode(h, kind, 1 if pad in (None, 3) else 6)
            h.play(True)
            h.press(BTN["record"])
            h.heartbeat(5)
            h.hold(BTN["clear"])
            if pad is not None:
                h.down(pad)
            h.heartbeat(300)
            if pad is not None:
                h.up(pad)
            h.let_go(BTN["clear"])
            h.press(BTN["record"])
            h.play(False)
        run(f"recording, Clear held for a pass{'' if pad is None else f', pad {pad} held'}", f)
    return out


if __name__ == "__main__":
    for kind in ("drum", "note"):
        print(f"== {kind}s: pads in every view mode, tap / tap with step 4 held")
        found = sweep(kind)
        for mode, held, pad, gone, known in found:
            zw, kn = explain(kind, mode, held, pad)
            print(f"   mode {mode} {'Shift + ' if held == 'shift' else 'step 4 held + ' if held else ''}pad {pad}: emptied {gone}; known functions run "
                  f"{known}; zeroing write {[(hex(a), pc, bt[:6]) for a, pc, bt in zw]}")
        if not found:
            print("   none")
        print(f"== {kind}s: button routes")
        for label, gone, known, zw in button_routes(kind):
            if gone:
                print(f"   {label}: emptied {gone}; known {known}; write {[(hex(a), pc, bt[:6]) for a, pc, bt in zw]}")
        print("   (routes not listed emptied nothing)")
