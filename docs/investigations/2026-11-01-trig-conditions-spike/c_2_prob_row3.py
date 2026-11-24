"""Q1b: when stock accepts a row-3 press in the probability view, which step it edits, and whether Shift matters.

Synth 2 (track 1: notes on steps 1-16 in the snapshot) and Drum 1 (track 4). Before the case, step pad 6 (index 5)
is pressed and released once (stock's selected step). Cases: stopped / playing x pattern follow (Shift + Patterns,
0x20039DE0 p0) off / on x a step pad held (pad index 2 = step 3) or not x Shift. The row-3 pad index 19 (value 3) is
pressed; reported: accepted (the store commit ran: 0x0804D104 / 0x0804F30C reached), which steps' probability bytes
changed in the playing pattern, the selected step before the press, and the playhead step.
Also: what Shift + Patterns is (the store, its LED), and the selected step following the playhead."""
from itertools import product

from c_lib import BTN_PATTERNS, MGR, SESSION, H, NOTE_PAT, diff, fmt_diff

FOLLOW = 0x20039DE0
ENGINE = 0x20038EC0
SEL_PAD, HELD_PAD, ROW3_PAD = 5, 2, 19


def prob_bytes(h, t):
    p = h.p0(h.r32(ENGINE + 0x30 + 4 * t)) & 7
    if t < 4:
        return [h.r8(NOTE_PAT[t] + 0xCA8 * p + 28 * s + 1) for s in range(32)]
    base = h.r32(SESSION + 0x14) + 0xCD74 + 0x3540 * (t - 4) + 0x6A8 * p
    return list(h.uc.mem_read(base + 0x20, 32))


def selected(h, t):
    """Stock's selected step: the editor's position store [editor + 0x24] p1 (notes) / [[view + 0xC] + 8] p1 (drums)."""
    from notes import param
    v = h.view_for(16)
    if t < 4:
        ed = h.r32(v + 0xC) - 0x18
        return param(h, h.r32(ed + 0x24), 1)
    return param(h, h.r32(h.r32(v + 0xC) + 8), 1)


def playhead(h, t):
    from notes import param
    return param(h, h.r32(ENGINE + 0x30 + 4 * t), 1)


def case(t, playing, follow, held, shift):
    h = H()
    h.press(t)
    if follow:
        h.press(BTN_PATTERNS, shift=True)
    h.open_prob(t)
    h.pad(SEL_PAD)
    if playing:
        h.play(37)
    if held:
        h.down(HELD_PAD)
    before, sel, head = prob_bytes(h, t), selected(h, t), playhead(h, t)
    h.take_all()
    if shift:
        h.shift(True)
    h.down(ROW3_PAD)
    h.up(ROW3_PAD)
    h.shift(False)
    _, hits, _ = h.take_all()
    after = prob_bytes(h, t)
    changed = [s + 1 for s in range(32) if before[s] != after[s]]
    accepted = any(x[0] in ("note_prob_write", "drum_prob_set") for x in hits)
    if held:
        h.up(HELD_PAD)
    return accepted, changed, sel + 1, head + 1, [after[s - 1] for s in changed]


def main():
    print("Shift + Patterns:")
    h = H()
    h.press(1)
    a = h.leds()
    h.press(BTN_PATTERNS, shift=True)
    b = h.leds()
    print("  0x20039DE0 p0 ->", h.p0(FOLLOW), "; LEDs changed:", [(i, f"{a[i]:02x}->{b[i]:02x}") for i in range(69) if a[i] != b[i]])
    h.shift(True)
    c = h.leds()
    h.shift(False)
    print("  with Shift held, LED 45 (Patterns) =", f"{c[45]:02x}" if len(c) > 45 else None,
          "; Shift-held LEDs differing from Shift-held before:", end=" ")
    g = H()
    g.press(1)
    g.shift(True)
    c0 = g.leds()
    print([(i, f"{c0[i]:02x}->{c[i]:02x}") for i in range(69) if c0[i] != c[i]])

    print("Playing with follow on / off, no step held: the selected step and the playhead over 400 ms (every 50 ms):")
    for follow in (0, 1):
        h = H()
        h.press(1)
        if follow:
            h.press(BTN_PATTERNS, shift=True)
        h.open_prob(1)
        h.pad(SEL_PAD)
        h.play(1)
        seq = []
        for _ in range(8):
            h.heartbeat(50)
            seq.append((selected(h, 1) + 1, playhead(h, 1) + 1))
        print(f"  follow {follow}: (selected, playhead) {seq}")

    print("Row 3 (pad index 19 = value 3); selected = step 6, held = step 3:")
    shift_same = True
    for t, playing, follow, held in product((1, 4), (0, 1), (0, 1), (0, 1)):
        r0 = case(t, playing, follow, held, False)
        r1 = case(t, playing, follow, held, True)
        shift_same &= r0 == r1
        print(f"  {'notes' if t < 4 else 'drums'} playing {playing} follow {follow} held {held}: accepted {r0[0]}, "
              f"steps changed {r0[1]} (to {r0[4]}), selected before {r0[2]}, playhead {r0[3]}; "
              f"with Shift: {'same' if r0 == r1 else r1}")
    print("Shift + row 3 = row 3 in every case:", shift_same)


if __name__ == "__main__":
    main()
