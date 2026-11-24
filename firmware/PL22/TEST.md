# PL22 — CTPlay 1.0 beta 2: device test

**What it is:** PL21 (1.0 beta 1, passed 2026-11-21) with two fixes and nothing else (spec
`slim/docs/specs/2026-11-22-beta2-fixes-design.md`):
1. **A CC 27 on channel 16 no longer crashes the Circuit Tracks.** A stock 1.2.1 bug (found by upstream, RC4.20): a CC
   27, or NRPN 1:27, on the project channel 16 makes stock call a table entry that does not exist, and the device
   hangs. A **Circuit Rhythm** sends it when its −12 dB trim is toggled. PL22 patches the two bytes upstream patched.
2. **A Written roll entered outside the pattern's steps carries straight on.** Until PL21 its later notes wrapped into
   the pattern, onto steps you never touched. Now they go on into the next steps, and a note past step 32 is left out.

**Time:** about **40 min** (an estimate: 31 rows at about 30 s is 16 min, section D's 26 rows about 13 min; the build
and one install add about 10 min).

**Starting state:** PL21 installed and running normally. **One MIDI program at a time:** close Components, CTCtrl and
every MIDI page before you open another (Chrome keeps a tab's port until the tab is closed).

**You need a way to send MIDI control changes from the computer** to the Circuit Tracks: MIDI-OX (Windows), or any MIDI
app that sends a control change on a chosen channel. Write down which you used.

## Before you start
1. Build: `cd slim && ../.venv/bin/python -m slimbuild versions/PL22.toml`. The printed syx sha256 must be
   `c6e07d72ee981a5cfc9d19f89dcf6085ae68b9c07269df4503a4a4b24170d2f2` (= `syx_sha256` in `firmware/PL22/manifest.json`).
2. `../.venv/bin/python -m slimbuild.uploader`, open `slim/build/ct_uploader.html` in Chrome.
3. Switch the Circuit Tracks off. Hold **Scales + Preset + Note** and switch it on (bootloader mode). Allow MIDI,
   Identify: "bootloader mode". Pick `slim/build/PL22/circuittracks-4486-PL22.syx` (the page names it PL22). Send.
   **No Play is needed** in bootloader mode: the bar fills and the Circuit Tracks restarts.
4. When it runs normally: Allow MIDI, Identify: **CTPlay PL22**. Close the uploader's tab.

## Steps

### A. CC 27 on channel 16 (the crash fix)
Start: **a new empty project** (Projects view, an empty slot). Stopped. Give Synth 1 any patch you can hear. Open your
MIDI app with the Circuit Tracks as its output. In every row "CC n = v" means a control change on **channel 16**.

| # | Do | Expect | Result |
|---|---|---|---|
| A1 | Send **CC 27 = 127** | Nothing visible changes. **The Circuit Tracks keeps working** | |
| A1b | Press Synth 1. Play the C pad | The note sounds: no hang | |
| A2 | Send **CC 27 = 0** | Nothing changes; no hang | |
| A3 | Press Drum 1. Tap step pads 1, 5, 9 and 13. Press Play | Kicks on every beat | |
| A3b | While it plays: send **CC 27 = 127** | **It keeps playing**, in time | |
| A3c | Send **CC 27 = 0**, then **CC 27 = 127** again | It keeps playing | |
| A4 | Still playing: send **CC 99 = 1**, then **CC 98 = 27**, then **CC 6 = 0** (NRPN 1:27 = 0) | It keeps playing | |
| A4b | Send **CC 99 = 1**, **CC 98 = 27**, **CC 6 = 1** | It keeps playing | |
| A5 | **A control:** still playing, send **CC 74 = 20**, then **CC 74 = 64** | The master filter closes (duller), then opens again: stock's own CC on channel 16 still works | |
| A5b | Stop | Stopped | |
| A6 | **Only if you have a Circuit Rhythm:** connect it to the Circuit Tracks as when the crash was seen (Rhythm's MIDI out to the Tracks' in, or both on the computer with the Rhythm's output routed to the Tracks). On the Rhythm, open its sample-record view and toggle the −12 dB trim a few times. Then press Play on the Tracks | The Tracks keeps working and plays. **Write down how they were connected** | |

### B. A Written roll from outside the pattern's steps
Start: **a new empty project.** Set the scale to **major on C** (Scales). Give Synth 1 a **Poly patch with a sharp
attack** (a piano or a pluck: a roll's gaps are short). The pattern is 16 steps (stock's default).

A step is outside the pattern when it is before the pattern's start step or after its end step. (Pressing
1-16/17-32 on a 16-step pattern makes stock lengthen it to 32 steps, so steps 17–32 are then inside the pattern.)

| # | Do | Expect | Result |
|---|---|---|---|
| B1 | Shift + Synth 1, hold Shift, tap pad 32 (Keys), let go of Shift. Press pad 2 | Pad 2 bright green (chords in step entry) | |
| B1b | Press pad 4 | Pad 4 bright white (Written) | |
| B2 | Hold Shift, tap pad 25 (Chords), let go. Press pad 2 | Pad 2 bright green (triad) | |
| B2b | Press pad 28 | Pad 28 bright white (slow strum) | |
| B3 | Press Pattern Settings. Hold Shift, tap step pad 5, let go of Shift | Stock shows the pattern starting at step 5 (steps 5–16) | |
| B4 | Press Synth 1. Hold **step pad 2**. Press the C pad and let go of it. Let go of step pad 2 | The chord sounds while you hold the step. **Step pads 5–16 unlit**: nothing went into the pattern. (Pads 2 and 3 may or may not light: they are outside the pattern. B6 checks them by ear) | |
| B5 | Press Play. Listen for 2 bars. Stop | **Silence:** steps 2 and 3 are before the pattern's start. (PL21 put a G on step 6 here) | |
| B6 | Press Pattern Settings. Hold Shift, tap step pad 1, let go of Shift (the start back at step 1). Press Synth 1. Press Play. Listen for 2 bars. Stop | In every bar, just after beat 1: **C and E, then G** (the roll on steps 2–3). Nothing else | |
| B7 | Press 1-16/17-32 | The step pads show steps 17–32. (Stock makes the pattern 32 steps here) | |
| B7b | Press Pattern Settings. Tap step pad 15 (the end at step 31) | Stock shows the pattern ending at step 31 | |
| B8 | Press Synth 1 (steps 17–32 still shown). Hold **step pad 16** (step 32). Press the C pad and let go of it. Let go of step pad 16 | The chord sounds while you hold the step | |
| B8b | Press Pattern Settings. Tap step pad 16 (the end at step 32). Press Synth 1 | The pattern is 32 steps again | |
| B9 | Press Play. Listen for 2 bars (one pass). Stop | Bar 1, just after beat 1: the roll on steps 2–3. Bar 2's last step: **C and E only.** **No lone G on bar 1's first beat**: the G that would fall past step 32 is left out. (PL21 put it on step 2) | |
| B9b | Press 1-16/17-32 (steps 1–16) | **Step pad 1 unlit.** Pads 2 and 3 lit | |

### C. A quick pass over the rest
Start: **the project from B**, stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| C1 | Shift + Synth 1 (Chords, used last). Press pad 28 (slow off: no speed lit). Press Synth 1. Play the C pad | **C E G together** (a block triad) | |
| C2 | Shift + Synth 1, hold Shift, tap pad 26 (Arp), let go. Press pad 2 (up). Press Synth 1. Hold the C pad, then let go | An arpeggio up C E G while you hold it; it stops when you let go | |
| C3 | Shift + Drum 2, hold Shift, tap pad 27 (Pattern tools), let go. Press pad 4 (4 hits) | Pads 1, 5, 9 and 13 bright orange (the preview) | |
| C3b | Press pad 32, then pad 32 again, and let go. Press Drum 2 (the page closes) | **Step pads 1, 5, 9 and 13 lit**: the Write | |
| C4 | Save the project (Save, then Save again) | It saves as stock does | |
| C5 | Load another project, then load this one again. Shift + Synth 1 | The Arp page opens (used last): pad 2 bright green | |
| C6 | Hold Shift and look at the track buttons | Synth 1, Synth 2, MIDI 1, MIDI 2 and Drum 1–4 lit: CTPlay | |

### D. The trig-conditions recipe
Covers: `slim/docs/recipes.md`, **A snare roll every 4th bar, and a fill when you want it** (steps 1–15 and the first
two "To try next" ideas), run **as written**; PL21's run of the recipes (section L) did not include it. A mismatch is a
recipe fix, not a firmware bug, unless the feature misbehaves (then say what it did). Open the recipe on the computer
and follow it beside these rows.

Start: **a new empty project** (C natural minor). The recipe starts from the beat of "A beat from four drums": rows
D0a–D0e build its kick and snare (its hi-hat and percussion steps are not needed here).

| # | Do | Expect | Result |
|---|---|---|---|
| D0a | Press Play. Shift + Drum 1, hold Shift, tap pad 27 (Pattern tools), let go. Press pad 4 (4 hits) | Pads 1, 5, 9 and 13 bright orange (the preview) | |
| D0b | Press pad 32 twice | The kick on every beat | |
| D0c | Shift + Drum 2, hold Shift, tap pad 27, let go. Press pad 2 (2 hits) | Preview: pads 1 and 9 | |
| D0d | Press pad 18 four times | The preview moves one step a press: pads 5 and 13 | |
| D0e | Press pad 32 twice | The snare on beats 2 and 4 | |
| D1 | Recipe step 1: press Play (stop). Press Drum 2 | The sequencer stops. Drum 2's step pads 5 and 13 lit | |
| D1b | Tap step pads 14, 15 and 16 | They light: 5, 13, 14, 15, 16 lit | |
| D2 | Step 2: Shift + Pattern Settings. Tap step pad 14 | The probability view. Row 4 (pads 25–32) dark | |
| D3 | Step 3: hold pad 28 for half a second, then let go | Pad 25 bright cyan, pads 26–28 dim cyan, 29–32 dark | |
| D4 | Step 4: tap pad 28, then pad 25 | Pad 28 bright cyan, pads 25–27 dim cyan | |
| D5 | Step 5: tap step pad 15. Hold pad 28 for half a second, let go | Row 4: pad 25 bright cyan, pads 26–28 dim | |
| D6 | Step 6: tap pad 28, then pad 25 | Pad 28 bright, pads 25–27 dim | |
| D7 | Step 7: tap step pad 16. Hold pad 28 for half a second, let go | Row 4: pad 25 bright cyan, pads 26–28 dim | |
| D8 | Step 8: tap pad 28, then pad 25 | Pad 28 bright, pads 25–27 dim | |
| D9 | Step 9: press Play and listen for five bars | Bars 1–3: kick and snare as before. Bar 4: the snare also on steps 14, 15 and 16 (a roll into the next bar). Bar 5 as bar 1 | |
| D10 | Step 10: press Play (stop). Press Drum 2. Tap step pads 11 and 12 | Step pads 5, 11, 12, 13, 14, 15, 16 lit | |
| D11 | Step 11: Shift + Pattern Settings, tap step pad 11. Hold Shift, tap pad 27 (FILL) | With Shift held, pad 27 bright orange. Let go of Shift: row 4 all 8 pads dim orange | |
| D12 | Step 12: tap step pad 12. Hold Shift, tap pad 27 | The same as D11 | |
| D13 | Step 13: press Drum 1, then Shift + Pattern Settings. Tap step pad 13. Hold Shift, tap pad 28 (NOT FILL) | With Shift held, pad 28 bright orange | |
| D14 | Step 14: press Play and listen for four bars | Steps 11 and 12 silent; the kick plays beat 4. Bar 4: the roll on 14–16 | |
| D15 | Step 15: press Drum 2, then Note | The expanded view: pads 21–24 dim orange (FILL off) | |
| D15b | Hold pads 21 and 22 together for a bar, then let go | While held: pads 21 and 22 bright orange, the snare plays steps 11 and 12, the kick skips beat 4. After: the beat as in D14, pads 21–22 dim orange | |
| D16 | To try next 1: tap pad 22 (press and let go at once) | Pad 22 yellow (armed) until Drum 2's next pass, bright orange through that pass (snare on 11 and 12; the kick still plays beat 4: only Drum 2 fills), then dim orange by itself | |
| D17 | To try next 2: press Play (stop). Press Drum 2, then Shift + Pattern Settings | The probability view | |
| D17b | Tap step pad 14. Hold Shift, tap pad 25 (FIRST) | With Shift held, pad 25 bright green: the special replaces step 14's cycle | |
| D17c | Press Play and listen for five bars | Step 14's snare only in bar 1. Steps 15 and 16 still only in bar 4 | |

## Results

PL22 syx sha256 (printed by the build): c6e07d72ee981a5cfc9d19f89dcf6085ae68b9c07269df4503a4a4b24170d2f2  
Date and time taken: 2026-11-22 / 23  
MIDI app used (A): MIDI-OX  

A: All tests passed. No Circuit Rhythm available.  
B (first version of the rows, superseded: the plan was wrong): B8/9 G from last step's (pad 32) strum gets pushed to step 1 so 1-16 starts with a lone G. (Stock's 1-16/17-32 had made the pattern 32 steps, so step 32 was inside the loop and the roll wrapped, as designed.)  
B Revised: All tests passed
C: All tests passed  
D: All tests passed 
