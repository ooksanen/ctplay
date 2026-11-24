"""Q1 (notes): note_step_fill 0x0803D230 (r0 = the note editor, r1 = a 28 B step image), reached from note Clear step
0x0803D1D4 (r1 = the editor's edit store [editor + 0x20] write buffer, from touch-all 0x08035456) and note Clear pattern
0x0803D310 (r1 = pattern + 28 s, 32 calls). A simulated entry handler zeroes [r1 + 2] and [r1 + 3] (Task 8); the
result is read in the pattern. Synth 1, every step with distinct [2] / [3] (a_lib.ntag) and notes on some steps."""
from q_lib import *
from b_lib import store_bufs
from notes import fill

STEPS = (0, 3, 6, 12, 20)


def fresh(chain=None):
    h = Q()
    h.leds()
    set_tempo(h, bpm=240)
    if chain is not None:
        h.set_chain(0, chain, chain)
    for p in range(8):
        for s in STEPS:
            fill(h, 0, p, s, [60 + s])
        h.set_nb23(0, p, ntag(0, p))
    h.sync_nstore(0)
    h.fills = []

    def fill_handler(hh, r, sp):
        ed = r[0]
        st = hh.r32(ed + 0x20)
        where = hh.note_of_pattern(r[1])
        hh.fills.append(dict(ctx=hh.ctx, editor_track=hh.note_of_editor(ed), r1=r[1],
                             store_buf=r[1] in store_bufs(hh, st), pattern=where))
        hh.uc.mem_write(r[1] + 2, b"\0\0")
    h.handler_at(0x0803D230, fill_handler)
    return h


def summary(h, label):
    kinds = {}
    for f in h.fills:
        k = "edit store buffer" if f["store_buf"] else (f"pattern {f['pattern'][1]} step" if f["pattern"] else hex(f["r1"]))
        kinds.setdefault(k, []).append(f["pattern"][2] if f["pattern"] else None)
    print(f"[{label}] fill calls {len(h.fills)} [{', '.join(sorted({f['ctx'] for f in h.fills}))}], r0 = Synth "
          f"{sorted({f['editor_track'] for f in h.fills})}'s editor; r1: "
          + "; ".join(f"{k} x{len(v)}" + (f" (steps {v[0]}..{v[-1]})" if v[0] is not None else "") for k, v in kinds.items()))


def nonzero23(h, p):
    b = h.nb23(0, p)
    return [s for s in range(32) if b[2 * s:2 * s + 2] != b"\0\0"]


if __name__ == "__main__":
    for label, page2, playing, pad in (("1-16 shown, stopped", False, False, 3), ("17-32 shown, stopped", True, False, 4),
                                       ("playing (follow)", False, True, 6)):
        h = fresh(0 if playing else None)
        step_view(h, 0)
        if page2:
            h.press(BTN["half"])
        if playing:
            h.play(True)
            h.heartbeat(30)
        p = h.nshown(0)
        h.hold(BTN["clear"])
        h.pad(pad)
        h.let_go(BTN["clear"])
        summary(h, f"Clear step: {label}, pad {pad}")
        st = pad + (16 if page2 else 0)
        print(f"   shown {p}; selected now {h.nselected(0)}; step {st}: [0] = {h.nstep(0, p, st)[0]}, [2]/[3] = "
              f"{hexs(h.nstep(0, p, st)[2:4])}; steps with [2]/[3] != 0 in pattern {p}: {32 - len(nonzero23(h, p))} "
              f"zero (others kept: {[s for s in range(32) if s != st and s not in nonzero23(h, p)] == []})")
    for label, chain, pat in (("shown, stopped", None, 0), ("not shown, playing P3", 2, 1)):
        h = fresh(chain)
        if chain is not None:
            h.play(True)
            h.heartbeat(30)
        h.clear_pattern_pv(0, pat)
        summary(h, f"Clear pattern: {label} (pattern {pat})")
        print(f"   pattern {pat}: steps with [2]/[3] != 0: {nonzero23(h, pat)}; notes left "
              f"{[s for s in range(32) if h.nstep(0, pat, s)[0]]}; other patterns kept "
              f"{all(h.nb23(0, q) == ntag(0, q) for q in range(8) if q != pat)}")
