"""Q3: no stock reader of the condition bytes. One scenario run three times on stock: clean (bytes as the content
leaves them, 0), filled (drum + 0x84..+ 0xA7 of all 32 drum patterns, note [2] / [3] of every step of all 32 note
patterns), and filled with a read watch on those bytes. The scenario: content in every pattern, 16 steps, every track
chained over patterns 1-2; Play (real tick: the Play button and the Main 1 ms service), edits while playing, Stop,
edits stopped, Play again from stop, Stop, Save (the session save route: Save twice). Compares the notes / hits sent,
the DSP writes, the patterns outside the condition bytes and the condition bytes themselves."""
from collections import Counter

from a_lib import *

EMPTY_NOTE = bytes([0, 7, 0, 0]) + bytes([0, 0, 0, 0x60]) * 6
NOTE_EDITOR_LOAD = 0x0803DC16


def content(h):
    for t in range(4):
        for p in range(8):
            base = h.npat(t, p)
            for s in range(32):
                h.uc.mem_write(base + NSTEP * s, EMPTY_NOTE)
            for s, prob in ((0, 7), (3 + p % 4, 7), (8, 3), (11, 7)):
                n = 48 + 3 * t + p + s
                h.uc.mem_write(base + NSTEP * s, bytes([1, prob, 0, 0, n, 6, 0, 100]))
            h.uc.mem_write(base + 0x380, bytes([15, 0]))
    for d in range(4):
        for p in range(8):
            hits = {0: (100 - 5 * d, 1, 7, 0xFF), 4 + p % 3: (90, 1, 7, 1), 8: (80, 1, 7, 0xFF),
                    12: (70, 0x21, 7, 0xFF), 14: (60, 1, 4, 0xFF)}
            h.set_dhits(d, p, hits, load=False)
            h.uc.mem_write(h.dpat(d, p) + 0x80, bytes([15, 0]))
    for t in range(8):
        h.set_chain(t, 0, 1)


def scenario(filled, watch):
    h = H(watch=watch)
    h.leds()
    set_tempo(h, bpm=240)
    content(h)
    if filled:
        for d in range(4):
            for p in range(8):
                h.set_dcond(d, p, dtag(d, p))
        for t in range(4):
            for p in range(8):
                h.set_nb23(t, p, ntag(t, p))
    for d in range(4):
        h.dload(d)
    for t in range(4):
        h.call(NOTE_EDITOR_LOAD, h.neditor(t), h.npat(t, h.nshown(t)))
        h.sync_nstore(t)
    step_view(h, 4)
    h.log.clear(); h.hits.clear(); h.dsp_writes.clear(); h.calls.clear()
    h.watching = watch
    t0 = h.ticks

    h.phase = "play"
    h.play(True)
    h.until_tick(t0 + 4 * 96 + 10)
    h.phase = "edit while playing"
    step_view(h, 4); h.pad(6)                           # drum 1: a hit on step 7 of the playing pattern
    step_view(h, 0); h.down(5); h.down(24); h.up(24); h.up(5)   # Synth 1: step entry, key C on step 6
    prob_view(h, 0); h.pad(0); h.pad(16 + 2)            # Synth 1: probability 3 on step 1
    prob_view(h, 5); h.pad(4); h.pad(16 + 5)            # drum 2: probability 6 on step 5
    h.phase = "play"
    h.until_tick(h.ticks + 2 * 96)
    h.phase = "stop"
    h.play(False)
    h.heartbeat(20)
    h.phase = "edit stopped"
    step_view(h, 4); h.hold(BTN["clear"]); h.pad(8); h.let_go(BTN["clear"])     # drum 1: Clear step 9
    step_view(h, 1); h.hold(BTN["clear"]); h.pad(0); h.let_go(BTN["clear"])     # Synth 2: Clear step 1
    step_view(h, 2); h.down(2); h.down(24); h.up(24); h.up(2)                  # MIDI 1: step entry on step 3
    step_view(h, 7); h.pad(1)                                                   # drum 4: a hit on step 2
    h.phase = "play from stop"
    h.play(True)
    h.until_tick(h.ticks + 2 * 96)
    h.phase = "stop"
    h.play(False)
    h.heartbeat(20)
    h.phase = "save"
    h.press(BTN["save"]); h.press(BTN["save"])
    h.heartbeat(50)
    h.watching = False
    return h


def patterns_outside(h):
    out = bytearray()
    for d in range(4):
        for p in range(8):
            img = bytearray(h.dpattern(d, p))
            img[COND_LO:COND_HI] = bytes(COND_HI - COND_LO)
            out += img
    for t in range(4):
        for p in range(8):
            img = bytearray(h.uc.mem_read(h.npat(t, p), NPAT))
            for s in range(32):
                img[NSTEP * s + 2:NSTEP * s + 4] = b"\0\0"
            out += img
    return bytes(out)


def conds(h):
    return [h.dcond(d, p) for d in range(4) for p in range(8)], [h.nb23(t, p) for t in range(4) for p in range(8)]


if __name__ == "__main__":
    runs = {}
    for name, filled, watch in (("clean", False, False), ("filled", True, False), ("filled+watch", True, True)):
        h = scenario(filled, watch)
        runs[name] = h
        notes = [e for e in h.log if e[0] in ("synth_on", "synth_off", "midi_on", "midi_off")]
        print(f"[{name}] ticks {h.ticks}; endpoint note events {len(notes)}; drum player hits "
              f"{sum(1 for x in h.hits if x[2] == 'on')}; DSP writes {len(h.dsp_writes)}; forbidden {h.forbidden_writes}")
    c, f, w = runs["clean"], runs["filled"], runs["filled+watch"]
    for a, b, label in ((c, f, "clean vs filled"), (f, w, "filled vs filled+watch")):
        print(f"== {label}")
        print(f"   endpoint log equal: {a.log == b.log}; drum hits equal: {a.hits == b.hits}; "
              f"DSP writes equal: {a.dsp_writes == b.dsp_writes}; ticks equal: {a.ticks == b.ticks}")
        print(f"   patterns outside the condition bytes equal: {patterns_outside(a) == patterns_outside(b)}")
        print(f"   pattern-writer calls equal: {[x[:2] for x in a.calls] == [x[:2] for x in b.calls]}")
    dset = [dtag(d, p) for d in range(4) for p in range(8)]
    nset = [ntag(t, p) for t in range(4) for p in range(8)]
    for name in ("filled", "filled+watch"):
        dc, nc = conds(runs[name])
        print(f"[{name}] condition bytes unchanged: drums {sum(x == y for x, y in zip(dc, dset))}/32 patterns, "
              f"notes {sum(x == y for x, y in zip(nc, nset))}/32 patterns")
    dc, nc = conds(c)
    print(f"[clean] condition bytes still 0: drums {all(x == bytes(36) for x in dc)}, notes {all(x == bytes(64) for x in nc)}")
    print(f"   writer calls seen: {sorted(Counter(x[1] for x in c.calls).items())}")
    print("== reads of the condition bytes (filled+watch): phase, pc, lr, kind -> count, bytes")
    g = Counter()
    for phase, pc, lr, addr, size, kind in w.reads:
        g[(phase, pc, lr, kind)] += 1
    for (phase, pc, lr, kind), n in sorted(g.items(), key=lambda x: (x[0][0], x[0][1])):
        print(f"   {phase:20} pc {pc:#010x} lr {lr:#010x} {kind:6} x{n}")
    if not w.reads:
        print("   none")
