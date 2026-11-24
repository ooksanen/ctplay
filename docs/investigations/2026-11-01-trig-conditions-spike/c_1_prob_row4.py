"""Q1a: stock's probability view does nothing with row 4 (pads 24-31), both classes.

For every case (track kind x stopped / playing x pattern follow off / on x Shift off / on x a step pad held or not), two
harnesses run the same route; one also presses and releases each row-4 pad in turn (with a heartbeat between press
and release while playing), the other does not. Then both run the same heartbeats and LED refresh, and the RAM
(0x20000000-0x20050000) and the 69 LEDs are compared. Only [ctrl + 0x170] (stock's "a pad was pressed" byte, set by
every press at 0x080332A2) is ignored. `--pl18` runs it on the PL18 image. Also: the view's pad handler sees row 4 as 8-15 and returns at its bge
(0x0804D112 / 0x0804F31C); no sink call, no synth / MIDI endpoint."""
import sys
from itertools import product

from c_lib import BTN_PATTERNS, MGR, STOCK, H, diff, fmt_diff, hexrow, image_pl18

IMAGE = image_pl18() if "--pl18" in sys.argv else STOCK   # --pl18: the same check on the PL18 image (RAM only, not ITCM)

FOLLOW = 0x20039DE0
STEP_PAD = 2            # step 3 (top half: the step view)
IGNORE = [(MGR + 0x170, MGR + 0x171)]


def build(t, playing, follow, held, shift, press):
    h = H(IMAGE)
    h.leds()
    h.press(t)
    if follow:
        h.press(BTN_PATTERNS, shift=True)
        assert h.p0(FOLLOW) == 1
    h.open_prob(t)
    if playing:
        h.play(30)
    if held:
        h.down(STEP_PAD)
    h.take_all()
    if shift:
        h.shift(True)
    during = None
    if press:
        for p in range(24, 32):
            h.down(p)
            if playing:
                h.heartbeat(1)
            if p == 27:
                during = h.leds()
            h.up(p)
            if playing:
                h.heartbeat(1)
    else:
        for p in range(24, 32):
            if playing:
                h.heartbeat(1)
            if p == 27:
                during = h.leds()
            if playing:
                h.heartbeat(1)
    log = h.take_all()
    if shift:
        h.shift(False)
    if held:
        h.up(STEP_PAD)
    if playing:
        h.heartbeat(5)
    leds = h.leds()
    return h, log, during, leds


def main():
    bad = 0
    for t, playing, follow, held, shift in product((1, 4), (0, 1), (0, 1), (0, 1), (0, 1)):
        a, (sinks, hits, ends), during_a, leds_a = build(t, playing, follow, held, shift, True)
        b, (sinks_b, _, ends_b), during_b, leds_b = build(t, playing, follow, held, shift, False)
        d = diff(a.ram(), b.ram(), IGNORE)
        pad_calls = [x for x in hits if x[0] in ("note_prob_pad", "drum_prob_pad")]
        rets = [x for x in hits if x[0] in ("note_prob_ret", "drum_prob_ret")]
        writes = [x for x in hits if x[0] in ("note_prob_write", "drum_prob_set")]
        rel = [x for x in hits if x[0] == "noop_release"]
        ok = (not d and leds_a == leds_b and during_a == during_b and sinks == sinks_b and ends == ends_b
              and not writes and len(rets) == 8 and [x[2] for x in pad_calls] == list(range(8, 16)))
        bad += not ok
        print(f"{'notes' if t < 4 else 'drums'} track {t} playing {playing} follow {follow} step held {held} "
              f"shift {shift}: {'NOTHING' if ok else 'DIFFERENT'}; view pad args {[x[2] for x in pad_calls]}, "
              f"returns {len(rets)}, writes {len(writes)}, view releases (no-op 0x0804759A) {len(rel)}, "
              f"sinks {len(sinks)} vs {len(sinks_b)}, endpoints {len(ends)} vs {len(ends_b)}, RAM diff {fmt_diff(d)}")
        if not ok:
            print("   leds a", hexrow(leds_a[:32]))
            print("   leds b", hexrow(leds_b[:32]))
        if t in (1, 4) and not playing and not follow and not held and not shift:
            print("   row 3 / row 4 LEDs (pads 16-31) while pad 27 is held:", hexrow(during_a[16:32]))
    print("cases with a difference:", bad)
    runs = []
    for press in (True, False):                     # positive control: a row-3 press (pad 19) is seen by the diff
        h = H(IMAGE)
        h.leds()
        h.open_prob(4)
        if press:
            h.down(19)
            h.up(19)
        runs.append(h.ram())
    print("control, drums, one row-3 press vs none (B -> A):", fmt_diff(diff(runs[1], runs[0], IGNORE)))


if __name__ == "__main__":
    main()
