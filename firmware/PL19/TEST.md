# PL19 — device test plan (pattern strum)

**What it is:** PL18 with **pattern strum** (spec `slim/docs/specs/2026-10-28-playback-strum-design.md`):
- **The Keys page** (Shift held on a Play page, pad 32) has two new pads. **Pad 3 = played, pad 4 = written** (bright
  white = the track's setting, dim white = not). None lit = off (stock, the default). A press on the dim one picks it;
  a press on the lit one sets off. Each track has its own. Pads 1–2 are PL18's (mono record, chords in step entry).
  Pads 5–32 are dark and do nothing.
- Pattern strum acts only when the track's **strum speed** is on (Chords page pads 28–30). It uses the track's strum
  speed and direction.
- **Played:** the pattern keeps plain chords. CTPlay strums each chord as the sequencer plays it: the first note on
  the step, the others 80 / 40 / 20 ms apart, at any tempo. The track's next notes cut a strum short (its waiting
  notes do not sound). Stop and a mute drop the waiting notes too. A strummed chord you record goes in as a plain
  chord.
- **Written:** a strum goes into the pattern as a **roll**: each note on its own microstep, the gap in sequencer ticks
  (slow 4, medium 2, fast 1; at 1/16 a microstep is a tick). A roll longer than a step continues into the next steps.
  Step entry (with chords in step entry on) writes the notes in the held step at once and the rest when you let go of
  the pad. Recording writes the same roll, with record quantise on or off. The roll is ordinary notes: it plays the
  same on the official firmware.
- **Saved:** the new setting, per track, in the second saved block (the saved settings are 117 B now). The CTCtrl
  link carries it.

With pads 3–4 off (the default), playback, recording and step entry are PL18's (checked in emulation), and every PL18
feature plays as before. PL18 passed on the device (`firmware/PL18/TEST.md`): this run checks what is new.

**Time:** about **2 to 2¼ hours** in all (an estimate; 105 rows). It splits well into two sittings:
- **First sitting, about 1 hour to 1¼ hours:** Before you start (build, flash, set up: 15–20 min), A. Keys page
  (10 min), B. Played (15 min), C. Cut short, Stop, mute (10–15 min), D. Recording on Played (10–15 min).
- **Second sitting, about 1 hour:** E. Written (25–30 min, the longest), F. Recording on Written (5–10 min),
  G. MIDI 1 (10 min, skip it without an external synth), H. Save, load, power cycle (10 min), I. The link (5 min).
- To stop after D: save the project and note it in Results. Before E, load it again (item 12 below).

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL19.toml`. The printed syx sha256 must equal
   `syx_sha256` in `slim/firmware/PL19/manifest.json` (`e6ccb977…`). Then `../.venv/bin/python -m slimbuild.uploader`
   (the uploader learns PL19).
1. **Stack headroom gate (SL00D):** Main and UI with at least 2 green pads (≥ 1.5 KB free). Hook stacks against PL18:
   **Main (`main_ms`) 432 B** (PL18 416 B: the heartbeat now sends Played's late notes through stock's player);
   new: the player's step (`seq_play_step`) 136 B and its reset (`seq_end_all`) 120 B, the recorders' commits
   (`rec_off_commit` 200 B, `rec_pass_commit` 208 B); step entry **`step_add` 396 B** (PL18 348 B) and
   **`note_pad_press` 316 B** (PL18 220 B); a Note-view pad 356 B (PL18 348 B); the LED task 592 B (PL18 576 B: the
   link's copies of the 117 B payload). A page pad press 476 B and release 444 B, a Note-view pad release 192 B: as
   PL18. Stock's own calls are not counted.
2. **Back up the SD card**: the test writes patterns and saves a project. Use a pack you can lose. Way back: Scales +
   Preset + Note at power-on, send the stock `.syx` (or PL18).
3. Flash `slim/build/PL19/circuittracks-4486-PL19.syx` with `slim/build/ct_uploader.html`. Then close the uploader's
   tab (only one program can use the MIDI port; section I needs it).
4. **A new empty project** (in the Projects view, tap an empty slot) at the start of section A. It starts with every
   CTPlay setting off: chord shape off, strum off, arpeggiator off, every Keys pad off. Its patterns are empty, 16
   steps, sync rate 1/16. Set the project's scale to a **major scale on C** (Scales). Tempo **120 BPM**.
5. **Synth 1 and Synth 2 on a Poly patch** with a clear, **sustained** sound (an organ or a soft pad with a quick
   attack), so you can hear each note of a strum.
6. **The Note view** with the steps on rows 1–2 and the keys on rows 3–4 (stock's normal Note view; if all four rows
   play notes, press Note until rows 1–2 show the steps). Your keyboard layout. Step pads: steps 1–8 on row 1, steps
   9–16 on row 2. **"The C pad" is the C at the left end of the bottom row**; "the D pad" is the pad to its right, then
   E, F and G. Every chord in this plan is played from the C pad: with a triad it is **C E G**.
7. **The click** (stock's metronome): hold Shift and look at Clear. **Green = the click only.** If it is not green,
   press Shift + Clear until it is. A count-in would delay every recording by a bar.
8. **Record quantise on** (stock's default): hold Shift and look at Record: bright = on. If it is dim, press
   Shift + Record.
9. **Reading a step:** hold its step pad. Stock then plays the step's notes and lights up their key pads. Let go: the
   notes stop. An empty step plays nothing and lights up no key pad. **Stock plays each note at its microstep**: in a
   roll, a later note sounds a moment after the hold (E 4 microsteps, about 80 ms, after C), while all the step's key
   pads light up at once (checked in emulation). The preview when a chord **goes in** (a pad pressed with the step
   held) plays the step's notes together.
10. **The phantom-press check:** a slow press can make the Circuit see a press on the next pad too (the pad to the
    right). After each press that writes or takes out notes, the plan checks that the pad to the right did not act:
    the D pad after C, step 6 after step 5, pad 4 after pad 3, and so on.
11. **Listening to a strum:** slow is 80 ms between notes, a quick "brrm" from low to high. At 120 BPM a step is
    125 ms and a bar is 2 s.
12. Run the sections in order. If you stop in between (after D is the natural place), save the project and note where
    you stopped: later sections rely on the state the earlier ones leave. To go on, load the project again.

## Steps
### A. The Keys page
Start: **a new empty project** (Before you start, 4–6). Sequencer stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Press Synth 1 | Synth 1's Note view: steps on rows 1–2, keys on rows 3–4 | |
| 1b | Shift + Synth 1 | The **Chords page** (a new project opens on it): pad 1 bright green (shape off), pads 2–8 dim green | |
| 1c | Press pad 2 (triad) | Pad 2 bright green, pad 1 dim green | |
| 1d | Press pad 28 (slow) | Pad 28 **bright white**, pads 29–30 dim white. Pad 31 bright white (rising), pad 32 dim white | |
| 2 | Hold Shift, tap pad 32 (Keys). Release Shift | The Keys page: pad 1 dim magenta, pad 2 dim green, **pads 3 and 4 dim white.** Pads 5–32 dark | |
| 3 | Press pad 2 | Pad 2 bright green (chords in step entry on). **Pad 3 stays dim white** (phantom check). Leave it on | |
| 4 | Press pad 3 | Pad 3 **bright white** (played). **Pad 4 stays dim white** (phantom check) | |
| 4b | Press pad 3 | Pad 3 dim white (off). Pad 4 dim white | |
| 4c | Press pad 4 | Pad 4 **bright white** (written). Pad 3 dim white | |
| 4d | Press pad 3 | Pad 3 bright white, **pad 4 dim white**: one of the two at a time | |
| 4e | Press pad 3 | Pads 3 and 4 dim white: off. Leave it off | |
| 5 | Tap pad 5, then pad 32. These pads are free: they must do nothing | Nothing changes: pads 5 and 32 stay dark, pads 1–4 as they were (2 bright green, 1, 3, 4 dim) | |
| 6 | Shift + Synth 2 | Synth 2's Chords page (a new project opens on it) | |
| 6b | Hold Shift, tap pad 32 (Keys), release Shift | **Synth 2's Keys page: pad 1 dim magenta, pad 2 dim green, pads 3–4 dim white.** Each track has its own settings | |
| 6c | Shift + Synth 1 | Synth 1's Keys page (the page it used last): **pad 2 bright green**, pads 3–4 dim white | |

### B. Played
Start: as section A left it. Synth 1: triad, strum slow and rising, chords in step entry on, pattern strum off.

| # | Do | Expect | Result |
|---|---|---|---|
| 7 | Press Synth 1. Hold step pad 1. Press the C pad and let go of it. Keep holding step pad 1 | At once: **C E G together**, sounding while you hold step 1. The C, E and G pads light up | |
| 7b | Let go of step pad 1 | The chord stops | |
| 7c | **Phantom check.** Hold step pad 1 again | C E G. **The D pad does not light up.** Let go | |
| 8 | Press Play. Listen for two bars | **C E G together** (a block chord) on the first beat of each bar: pattern strum is off, so the pattern plays as stock. Keep it playing | |
| 9 | Shift + Synth 1 (its Keys page, used last). Press pad 3 | Pad 3 bright white (played). **From the next bar: C, E, G one after another, low to high**, a quick slow strum on each bar's first beat. The same on every pass | |
| 10 | Hold Shift, tap pad 25 (Chords), release Shift. Press pad 29 (medium) | Pad 29 bright white. The strum is tighter (40 ms) | |
| 10b | Press pad 30 (fast) | Tighter still (20 ms): nearly together, but still a roll | |
| 10c | Press pad 28 (slow) | Back to the slow strum | |
| 11 | Press pad 32 (falling) | Pad 32 bright white. **G, E, C: high to low** | |
| 11b | Press pad 31 (rising) | C, E, G again, low to high | |
| 12 | Set the tempo to **80 BPM** (Tempo/Swing and knob 1, as in stock). Listen | The bars are slower, but **the strum itself keeps its speed**: the same quick roll as at 120 | |
| 12b | Set the tempo to **160 BPM** | The bars are faster; the strum keeps its speed | |
| 12c | Set the tempo back to **120 BPM** | | |
| 13 | Shift + Synth 1 (the Chords page). Press pad 28 (the lit slow pad) | Pads 28–30 all dim: strum off. **From the next bar: C E G together** (a block chord), though pad 3 on the Keys page is still on | |
| 13b | Press pad 28 | Pad 28 bright white: slow. From the next bar the chord strums again | |
| 13c | Press Play (stop) | Silence | |

### C. Cut short, Stop, mute
Start: as section B left it. Sequencer stopped. Synth 1 on Played, slow, rising; step 1 holds C E G.

| # | Do | Expect | Result |
|---|---|---|---|
| 14 | Press Synth 1. Hold step pad 2. Press the C pad and let go of it | At once: C E G together. The D pad does not light up (phantom check) | |
| 14b | Let go of step pad 2 | The chord stops | |
| 15 | Press Play. Listen for a few bars | Step 1's strum is **cut short**: it stops after **C, E**; step 2's strum (C, E, G) starts 125 ms after the beat, before step 1's G (160 ms in) would sound. Hard to hear on its own: **step 16c is the real check** (step 2 empty, the strum plays in full) | |
| 15b | Press Play (stop) | Silence: nothing keeps sounding | |
| 16 | **Take step 2 out** (PL18's "pad again"). Hold step pad 2. Press the C pad and let go of it | At once: the chord stops. The C, E and G pads stop lighting up | |
| 16b | Let go of step pad 2. Hold it again | Nothing sounds, no key pad lights up: step 2 is empty (no D either). Let go | |
| 16c | Press Play. Listen for two bars | **C, E, G in full** on each bar's first beat: with step 2 empty, the strum plays out | |
| 17 | **Stop in the middle of a strum.** Press Play (stop), then press Play and at once Play again (as fast as you can, so the stop comes during the first strum). Do it five times | **After each stop, nothing keeps sounding.** A short note right at the stop is fine; a note that rings on is not | |
| 18 | **Mute.** Press Play. Press Mixer. Press pad 1 (Synth 1's mute, as in stock) on a bar's first beat, while the strum plays | **At once: silence. No note of the strum sounds after the mute** | |
| 18b | Press pad 1 again (unmute) | From the next bar: the strum again, C, E, G | |
| 18c | Mute and unmute two more times, at different moments | Each mute: silence at once. Each unmute: the strum comes back. Nothing keeps sounding while muted | |
| 18d | Press Play (stop). Press Synth 1 | Synth 1's Note view | |

### D. Recording on Played
Start: as section C left it. Synth 1's step 1 holds C E G; the rest of its pattern is empty. Record quantise on.

| # | Do | Expect | Result |
|---|---|---|---|
| 19 | **Empty the pattern.** Hold step pad 1. Press the C pad and let go of it | At once: the chord stops | |
| 19b | Let go of step pad 1. Hold it again | Nothing sounds: step 1 is empty. Let go. Synth 1's pattern is empty now | |
| 20 | Press Record, then Play. On the **second beat** of a bar (with the click), press the C pad, **hold it about half a second**, let go. Press Play (stop), then Record (off) | While you play: a strum, C, E, G | |
| 20b | Hold the step pads 1–16 one by one | **Exactly one step has notes** (about step 5): it lights up **C, E and G** together, and plays C E G. **No D.** Every other step is empty | |
| 20c | Press Play. Listen for two bars. Stop | On that step: **C, E, G strummed** (the pattern holds a plain chord; Played strums it) | |
| 21 | Take it out: hold that step, press the C pad and let go of it, let go of the step | The chord stops. Hold the step again: empty | |
| 21b | **Record quantise off:** Shift + Record | Record dims (with Shift held) | |
| 21c | Do step 20 again | While you play: a strum | |
| 21d | Hold the step pads 1–16 one by one | Again **exactly one step has notes: C, E and G** (with quantise off, stock alone can spread a strum over two steps) | |
| 21e | Press Play. Listen. Stop | That step strums: C, E, G | |
| 21f | **Record quantise back on:** Shift + Record | Record bright (with Shift held) | |
| 21g | **Empty Synth 1's pattern** (so it stays quiet in the next sections): hold the step with the chord, press the C pad and let go of it, let go of the step | The chord stops. Hold the step again: empty | |

### E. Written
Start: as section D left it. Sequencer stopped. Synth 1's pattern empty (21g). Synth 2: everything off, its pattern
empty, its Keys page used last (6b).

| # | Do | Expect | Result |
|---|---|---|---|
| 22 | Shift + Synth 2 | **Synth 2's Keys page:** pads 2, 3 and 4 dim | |
| 22b | Press pad 2 | Pad 2 bright green (chords in step entry). **Pad 3 stays dim white** (phantom check) | |
| 22c | Press pad 4 | **Pad 4 bright white** (written), pad 3 dim white | |
| 22d | Hold Shift, tap pad 25 (Chords), release Shift. Press pad 2 (triad), then pad 28 (slow) | Pad 2 bright green. Pad 28 bright white; pad 31 bright white (rising) | |
| 23 | Press Synth 2 (press Note if the keys are not on rows 3–4). Hold step pad 1. Press the C pad and let go of it. Keep holding step pad 1 | **C and E at once** (the notes the roll puts in step 1: the press's preview plays them together; only holding the step later plays E at its microstep), sounding while you hold step 1. **The C and E pads light up; the G pad does not; the D pad does not** (phantom check) | |
| 23b | Let go of step pad 1 | The notes stop | |
| 23c | Hold step pad 1 again | C, and **E a moment later** (its microstep 4). The C and E pads light up at once. Let go | |
| 23d | Hold step pad 2 | **G alone** (a moment after the hold: its microstep 2); only the G pad lights up. The G went in when you let go of the C pad (step 1 holds C at its start and E 4 microsteps later; G is 8 ticks after C: step 2, microstep 2). Let go | |
| 23e | Hold step pad 3 | Nothing: step 3 is empty. Let go | |
| 24 | Press Play. Listen for two bars. Stop | **C, E, G one after another, low to high**, on each bar's first beat: the same strum you hear when you hold the C pad (try it: hold C, let go) | |
| 25 | **The pad again takes the roll out.** Hold step pad 1. Press the C pad and let go of it | At once: C and E stop. The C and E pads stop lighting up | |
| 25b | Let go of step pad 1. Hold step pad 1, then step pad 2 | **Both empty**: nothing sounds, no key pad lights up (step 2's G went out when you let go of the C pad; no D either) | |
| 26 | **Pad first.** Hold the C pad (you hear the strum, C E G). Keep holding it, press step pad 5 and hold it. Let go of the C pad, then of step pad 5 | After both are let go, nothing keeps sounding | |
| 26b | Hold step pad 5 | **C, then E**: the C and E pads light up. Let go | |
| 26c | Hold step pad 6 | **G alone** (phantom check: step 6 did not get a chord of its own: no C or E here). Let go | |
| 26d | Hold step pad 7 | Nothing. Let go | |
| 27 | **Pad first writes nothing on a falling strum.** Shift + Synth 2 (the Chords page). Press pad 32 (falling) | Pad 32 bright white, pad 31 dim | |
| 27b | Press Synth 2. Hold the C pad (you hear G, E, C, high to low). Keep holding it, press step pad 9 and hold it. Let go of the C pad, then of step pad 9 | Nothing keeps sounding | |
| 27c | Hold step pad 9, then step pad 10 | **Both empty.** Expected: pad first writes nothing while the strum is falling (PL18's rule). Let go | |
| 28 | **Step first, falling.** Hold step pad 9. Press the C pad and let go of it. Keep holding step pad 9 | **G and E at once** (the falling roll starts from the top; the press's preview plays them together). The G and E pads light up; **the C pad does not**, nor the D pad | |
| 28b | Let go of step pad 9. Hold step pad 10 | **C alone** (the roll's last note, in step 10, microstep 2). Let go | |
| 29 | **The pad again on the falling roll** (C is not in step 9: CTPlay finds the roll by its notes). Hold step pad 9. Press the C pad and let go of it | At once: G and E stop. The G and E pads stop lighting up | |
| 29b | Let go of step pad 9. Hold step pad 9, then step pad 10 | **Both empty** (no D either). Let go | |
| 29c | Shift + Synth 2 (the Chords page). Press pad 31 (rising) | Pad 31 bright white | |
| 30 | **Clear the pad-first roll:** press Synth 2. Hold step pad 5. Press the C pad and let go of it. Let go of step pad 5 | C and E stop at once | |
| 30b | Hold step pad 5, then step pad 6 | **Both empty**: Synth 2's pattern is empty again. Let go | |

### F. Recording on Written, tempo
Start: as section E left it. Synth 2's Note view, its pattern empty, Written, slow, rising. Record quantise on.

| # | Do | Expect | Result |
|---|---|---|---|
| 31 | Press Record, then Play. On the **second or third beat** of a bar, press the C pad, **hold it about half a second**, let go. Press Play (stop), then Record (off) | While you play: a strum, C, E, G | |
| 31b | Hold the step pads 1–16 one by one | **One step lights up C and E** (about step 5 or 9; you hear C, then E), and **the step after it lights up G alone**. No D. Every other step is empty | |
| 32 | Press Play. Listen for two bars | On that step: **C, E, G one after another**, as you played it. Keep it playing | |
| 33 | Set the tempo to **60 BPM** | **The strum is slower**: written in ticks, it stretches with the tempo (at 60 BPM each gap is 167 ms, twice the slow gap) | |
| 33b | Set the tempo back to **120 BPM**. Press Play (stop) | The strum as before; then silence | |

### G. MIDI 1 (only if an external synth is at hand)
Start: an external synth on MIDI out, channel as MIDI 1 sends (stock's setting). Skip this section without one.

| # | Do | Expect | Result |
|---|---|---|---|
| 34 | Shift + MIDI 1 (its Chords page). Press pad 2 (triad), then pad 28 (slow) | Pad 2 bright green, pad 28 bright white | |
| 34b | Hold Shift, tap pad 32 (Keys), release Shift. Press pad 2, then pad 3 | Pad 2 bright green, pad 3 bright white (played) | |
| 34c | Press MIDI 1. Hold step pad 1, press the C pad, let go of it, let go of step pad 1 | (Only playback is checked on MIDI) | |
| 34d | Press Play. Listen. Stop | **The external synth strums C, E, G**, low to high | |
| 35 | Shift + MIDI 1 (the Keys page). Press pad 4 | Pad 4 bright white (written), pad 3 dim | |
| 35b | Press MIDI 1. Hold step pad 1. Press the C pad and let go of it (takes the chord out). Press the C pad again and let go of it (the roll goes in). Let go of step pad 1 | (Only playback is checked on MIDI) | |
| 35c | Press Play. Listen. Stop | The external synth plays the roll: C, E, G | |
| 35d | Shift + MIDI 1 (the Keys page). Press pad 4 | Pads 3–4 dim: MIDI 1 back to off (section I counts on it) | |

### H. Save, load, power cycle
Start: as section F (or G) left it. Synth 1 on Played, Synth 2 on Written.

| # | Do | Expect | Result |
|---|---|---|---|
| 36 | Save the project (Save, then Save again) | It saves as stock does | |
| 36b | Load the same project again (Projects view, tap its slot) | It loads | |
| 36c | Shift + Synth 1. Hold Shift, tap pad 32 (Keys), release Shift | Synth 1's Keys page: **pad 2 bright green, pad 3 bright white, pad 4 dim** | |
| 36d | Shift + Synth 2. Hold Shift, tap pad 32 (Keys), release Shift | Synth 2's Keys page: **pad 2 bright green, pad 4 bright white, pad 3 dim** | |
| 36e | Press Synth 2. Hold the step that lit up C and E in step 31b, then the step after it | The C and E pads, then the G pad light up: the roll is ordinary notes, saved with the pattern | |
| 37 | Power off and on. Load the project. Do 36c–36e again | The same | |

### I. The link
Start: the project of section H loaded. Sequencer stopped. Shift + Synth 1, then Shift-tap pad 32: Synth 1's Keys page.

| # | Do | Expect | Result |
|---|---|---|---|
| 38 | Open `slim/pages/ctplay_link.html` **from the PL19 checkout** (an older checkout's page does not know the new field's name), connect | "Connected: PL19, protocol 1, layout 1, **117 B, 18 fields**." | |
| 38b | Read | A new row, **`pattern strum`**, offset 116: `09` (Synth 1 played = `01`, Synth 2 written = `08`) | |
| 38c | Write offset 116, bytes `0A` (Synth 1 and Synth 2 written) | One `state` line. **At once** on the Circuit: pad 4 bright white, pad 3 dim | |
| 38d | **A refused write.** Write offset 116, bytes `0B` (Synth 1's 2 bits = 3, which means nothing) | One `state` line, unchanged: the write is refused. Pad 4 stays bright white | |
| 38e | Close the page | | |

## Results

A: All tests passed  
B: All tests passed  
C: All tests passed  
D: All tests passed with a note: With recorded strum the release is also strummed from low to high, much like a guitar. Not sure if that's a bug or a feature.  
E: All tests passed with note: 23-23e C and E sound at the same time when hitting C, otherwise the whole section 23 as expected.  
F: All tests passed  
G: Skipped  
H: All tests passed
I: All tests passed with note: 38b field name is "offset 116 (rev 1)", not "pattern_strum"

**Follow-up on the notes (2026-11-07):** D: as designed (a Played strum shifts each whole note, so the release is
strummed too); whether to release together instead is in `docs/followups.md`. E 23: a plan error, not the firmware:
the preview when a chord goes in plays the step's notes together (only holding the step later plays them at their
microsteps); rows 9, 23 and 28 now say so. I 38b: a plan error: the page was opened from the PL18 checkout, whose
`ctplay_link.html` does not know offset 116; PL19's names it "pattern strum"; row 38 now says which checkout. Time: about
45 min (G skipped), against the 2–2¼ h estimated.
