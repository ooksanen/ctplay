# PL20 builder check, part C: the controls (emulation, 2026-11-01)

Spec: [`../../specs/2026-10-28-trig-conditions-design.md`](../../specs/2026-10-28-trig-conditions-design.md). Stock image
(`stock/circuittracks-firmware-4486-STOCK.bin`) and PL18 (`versions/PL18.toml`, built, syx sha256 matches
`firmware/PL18/manifest.json`), upstream's Unicorn setup with the device RAM snapshot (`tests/notes.py` NoteHarness).
Every press and release goes through the controller (`0x08033282` / `0x080332CE`); buttons through `0x08033320`; Shift
as the harness sets it (p0 of `[ctrl + 0xC]`); "playing" = the real Play button plus the 1 ms Main service.

Pads below are the controller's 0-31; the spec's pad n is n - 1 (row 3 = 16-23, row 4 = 24-31, FILL pads 21-24 =
20-23, drum pads 29-32 = 28-31).

Run from `slim/`: `PYTHONPATH=.:tests:../tools:docs/investigations/2026-11-01-trig-conditions-spike
../.venv/bin/python docs/investigations/2026-11-01-trig-conditions-spike/c_<n>_<name>.py` (each takes 3-16 s; the
`.out` files are the runs quoted here). "Nothing" below means: two harnesses run the same route, one presses the pads,
the other does not; afterwards their RAM `0x20000000-0x20050000` (plus ITCM `0x0-0x4000` in `c_5`) and their 69 LEDs
are byte-identical, with only `[ctrl + 0x170]` ignored (stock sets it on every pad press, `0x080332A2`). A positive
control (one row-3 press) shows up in the same diff (`c_1_prob_row4.out`, last line).

## Contradictions with the spec

1. **`0x20039DE0` p0 is the reverse of "pattern follow on".** Shift + Patterns toggles it (the only button that
   does). At **0** (the snapshot's state) the editors follow the playhead: while playing, the selected step moves
   with it (`(selected, playhead)` = (1, 1), (2, 2), (3, 3) ...), and a row-3 press without a held step is
   **refused**. At **1** the selected step stays where the user put it (step 6 while the playhead runs 1, 2, 3), and
   a row-3 press while playing **edits that step**. So the accept rule is "a step held, or stopped, or the editors
   not following (p0 = 1)". Whether Novation calls the 1 state "follow off" is not checked; with Shift held, panel LED 45
   is `0x55` at 0 and `0x74` at 1 (`c_2_prob_row3.out`; which button LED 45 is: not checked).
2. **The spec's "Where it hooks" for FILL: the view's release `0x0804ED68` sees the release when the view changes,
   but `ctrl_pad_release` mostly does not** (section Q2). Not a contradiction of a stated rule, but the ½ s hold and
   FILL's hold need it: see Q2.
3. **An open CTPlay drum page covers the expanded view's pads.** `drum_visible` (page.c) accepts mode 6, so with a
   drum page open on the expanded view (Shift + Drum N there) the page takes all 32 pads, pads 20-23 included. The
   spec's "the view stays as it is otherwise" holds only with no page open. Expected by the page rules, worth a line in
   the spec / ui-map.

Nothing else contradicts the spec: row 4, Shift + row 4 and the expanded view's pads 0-27 are free in stock; Shift +
row 3 is stock's plain press.

## Q1. The probability view, both classes

**Route.** Shift + Pattern Settings (12) or Pattern Settings twice gives mode 5 on both kinds (`c_lib.open_prob`).

**Row 4 does nothing** (`c_1_prob_row4.py`, `.out`; PL18: `c_1_prob_row4_pl18.out`). Synth 2 (notes on all 16 steps
in the snapshot) and Drum 1; all 32 cases of stopped / playing x `0x20039DE0` p0 0 / 1 x Shift off / on x a step pad
(step 3) held or not; pads 24-31 pressed and released one after the other: **nothing** in all 32, on stock and on
PL18. The view's handler gets them as 8-15 and returns at its `bge` (`0x0804D112` notes, `0x0804F31C` drums); no
write, no sink call (`note_sink_on / off`), no synth or MIDI endpoint. The release goes to the view's slot 1, which is
the shared no-op `0x0804759A` in both classes. Confidence: high (emulation; the asm agrees).

**When stock accepts a row-3 press, and which step it edits** (`c_2_prob_row3.py`). The handler's test
(`0x0804D0C6`-`0x0804D0EA`, `0x0804F270`-`0x0804F294`): accept when `[[view + 0xC] + 0x10]` p0 (a step pad held) is
set, or `[view + 0x10]` p0 = 0 (the play store `0x20011034`: stopped), or `[view + 0x14]` p0 is set
(`0x20039DE0`). Notes also need notes on the step (`[0] != 0`). Measured (step 6 selected beforehand, step 3 held,
value 3):

| | step held | stopped, not held | playing, p0 = 0, not held | playing, p0 = 1, not held |
|---|---|---|---|---|
| notes and drums | edits the held step (3) | edits the selected step (6) | **refused** (the selection follows the playhead) | edits the selected step (6) |

**Shift** changes nothing in this view: every row-3 case gives the same result with Shift held, and the LEDs of pads
16-31 are the same with and without Shift. Neither the controller nor the container nor the view test it.

**Row-4 LEDs: stock draws them off (0)**, in every state tried (stopped, playing, Shift, p0 = 1, after a row-3 edit).
The view's LED buffer is `[[view + 4]]`, 16 halfwords (0-7 = row 3, 8-15 = row 4); stock's listener (`0x0804D116` /
`0x0804F322`) writes 0-7 only, so 8-15 stay 0 (`c_3_prob_ids.out`). Row 3 is a bar: pads 0..value lit `0x6C`..`0x73`.
(Drums 2-4's buffer is empty in the snapshot until a first edit: stock paints it only on a change.)

**"A probability view is the bottom view"** (`c_3_prob_ids.out`), for CTPlay's `led_task` hook:
- `[ctrl + 0x6C]` = the container `0x20040DB8` (Patterns, Mixer and FX change the active view but leave the mode at 5,
  so this test is needed), **and** `[cont + 0x18C]` = 5, **and** `track_of(cont)` (`0x0805011E`) 0-3 (notes) or 4-7
  (drums).
- Then the bottom view (`0x08043B6E(cont, 16)`) is `[cont + 0x68 + 4t]` (notes, class `0x0805ACD4`) or
  `[cont + 0xE0 + 4d]` (drums, class `0x0805AB14`); the top half is the step view (`0x0805ADB4` / `0x0805AD0C`).
- Also `[ctrl + 0x152]` = 5 + 9t for notes (5, 14, 23, 32), 41 + 8d for drums (41, 49, 57, 65).
- The step to draw: stock's selected step (notes `[editor + 0x24]` p1, editor = `[view + 0xC]` - 0x18; drums
  `[[view + 0xC] + 8]` p1). While playing with p0 = 0 it is the playhead's step, so row 4 would change every step, as
  stock's row 3 does.

## Q2. Pad release, and a held pad when the view changes

(`c_4_release.py`, `.out`; pad 27 in the probability views, pad 20 in the expanded view.)

**Normal release:** `ctrl_pad_release` `0x080332CE` (pad 27) → container release `0x080435F0` → the view's slot 1
(probability views: the no-op `0x0804759A`, pad 27 remapped to 11; expanded view: `0x0804ED68`, pad 20 not remapped).
Press and release both reach CTPlay's `ctrl_pad_press` / `ctrl_pad_release` hooks with the pad, so a ½ s hold can be
timed from press to release there (the emulated clock does not run: the timing itself is not checked; slim has no ms
clock symbol, a counter in the 1 ms `main_ms` heartbeat would do).

**A pad held while the view changes** (both probability views; the expanded view the same):

| Button pressed while the pad is held | What runs at the button | Late release (finger up) |
|---|---|---|
| Inside the container: Note, Velocity, Gate, Pattern Settings, Preset, a track button (same, other track, other kind) | the container's half release-all `0x08043930` → container release → **the old view's slot 1** (before the view changes); `[cont + 0x190]` bit cleared, `[ctrl + 0x84]` bit **kept** | `ctrl_pad_release` runs, now in the **new view** (e.g. mode 1), and the container skips it |
| Leaving the container: Patterns, Mixer, FX | the controller's release-all `0x08033A6C` → `ctrl_pad_release` for pads 0-31 while the container is still active (mode unchanged) → the old view's slot 1; both bits cleared | `ctrl_pad_release` runs with the new active view (`0x200441A8` Patterns, `0x200447D4` Mixer, `0x200443B4` FX) and returns at its bit test |
| Shift + Pattern Settings again, Shift + Patterns, Play | nothing (the view stays) | the normal release |

What this means for the builder:
- A `ctrl_pad_release` hook alone gets **no release at the view change** for the in-container changes: the gesture
  stays "held" until the finger lifts, and that late release arrives in another view. A row-4 hold or a FILL hold must
  remember that it took the press (as `page_taken`) and drop the gesture when its view is no longer on screen (check
  at the release, and in `led_task`), never apply it to the view now shown.
- For Mixer / FX / Patterns the hook sees two releases (the release-all at the button, then the finger).
- **The expanded view's own release `0x0804ED68` (an entry hook, as the spec lists) gets exactly one release per press
  in every case**, at the view change when there is one, and is never reached by the late release. That suits FILL's
  hold. The probability views have no such per-class release (slot 1 is the shared no-op); the nearest equivalent is
  an entry hook on the container release `0x080435F0` (`push {r3-r7, lr}; mov r4, r0`, 4 B, not in `symbols.toml`
  yet), which sees the exit release while the old mode is still set; it runs before its own bit test, so it must test
  `[cont + 0x190]` itself.

## Q3. The drum expanded view (mode 6)

(`c_5_expanded.py`, `.out`.)

**Pads 0-27 do nothing**, press and release, on stock and on PL18 (no page open): drums 1 and 4, stopped / playing,
Shift off / on, every pad 0-27 in turn: **nothing** in all 16 cases (RAM and ITCM, LEDs, sink calls, endpoints). The
press handler `0x0804ED50` returns at `0x0804ED66` and the release `0x0804ED68` at `0x0804ED6E` for each of the 28
pads; the sink call is never reached. CTPlay (PL18) passes them: `page_on_pad` with no page open returns PASS and
leaves no state. Confidence: high.

**LEDs:** pads 0-27 are **off (0)** in every state tried (stopped, playing, Shift held, a drum pad held), on stock and
PL18, for all four drums; pads 28-31 are `45 2D 49 4D` (drums 1-4), white `0x01` while a drum sounds. The view's
buffer `[[view + 4]]` (32 halfwords, `0x200434FC`) holds 0 in 0-27; its painter `0x0804ED84` writes entries 28-31
only.

**"The expanded view is on screen"**, for a `led_task` hook painting pads 20-23 only there:
`[ctrl + 0x6C]` = `0x20040DB8`, `[cont + 0x18C]` = 6, `track_of(cont)` 4-7 (mode 6 on a note track is the wide
Note view); the view for any pad is `[cont + 0xAC]` = `0x200434D4`, class `0x0805AD44` (one object for all four drums;
the track tells which drum's view is shown). `[ctrl + 0x152]` = 42 + 8d. page.c's `drum_visible` accepts mode 1 too,
so FILL needs its own test (mode 6 only), drawn only when `page_draw` drew nothing (chord_on_leds' order).

**CTPlay's drum pages:** with no page open, PL18 does not touch pads 0-27 in this view. With a drum page open on it
(Shift + Drum 1 in mode 6: the mode stays 6), the page takes pad 20 (the view's handler is not reached) and draws the
page; Note then switches to mode 1 (and page.c closes the page on Note). So FILL and the drum pages never share a moment: FILL works
whenever no page is open (contradiction 3).

## Q4. Several pads at once in the expanded view

Hold drum pad 28 and tap pad 20, and hold pad 20 and tap 28: on stock and PL18 the sink calls (`on1` x 8, `off1` x 8:
the hit passes through 8 sink stages) and the whole state are **identical** to the same run without pad 20. Stock's
drum pad handling does not change with pad 20 held or tapped. The container keeps one bit per pad in `[cont + 0x190]`,
so the two pads are independent. Confidence: high (emulation; stopped only).

## Not checked

- The device (pad timing, the LEDs as seen, the Patterns LED meaning).
- Several row-4 pads held at once (the spec's gesture is one pad at a time).
- Q4 while playing (playback hits share the drum's note with the finger; stock's handling is the same function).
