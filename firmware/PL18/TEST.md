# PL18 — device test plan (chords in step entry)

**What it is:** PL17 with **chords in step entry** (spec `slim/docs/specs/2026-10-26-step-entry-chords-design.md`):
- **The Keys page** (Shift held on a Play page, pad 32) has one on / off pad per setting now. **Pad 1 = mono record**
  (bright magenta = mono, dim magenta = poly; it was two pads, poly · mono, until PL17). **Pad 2 = chords in step
  entry** (bright green = on, dim green = off). Pads 3–32 are dark and do nothing. Each track has its own.
- **With pad 2 on** and a chord shape set, step entry writes the pad's whole chord into the step: hold a step and press
  a key pad, or hold a key pad and press a step. The same key pad again (step held) takes the chord out.
- **Not written:** the strum and the arpeggio. **Pad first writes nothing** when the arpeggiator or a falling strum is
  on, or when the pad's own note is already in the step (agreed in the spec). This includes a note that another held
  pad's chord has just put there: with two pads held, one chord may be left out. With the arpeggiator or a falling
  strum on, step first still writes the chord. With the pad's own note already in the step, step first takes the
  chord out, as the same pad again does.
- **Saved:** the new setting, per track, in the second saved block (the saved settings are 116 B now). The CTCtrl
  link carries it.

With pad 2 off (the default), step entry is stock's (checked in emulation, byte for byte), and every PL17 feature plays
as before. PL17 passed on the device (`firmware/PL17/TEST.md`): this run checks what is new.

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL18.toml`. The printed syx sha256 must equal
   `syx_sha256` in `slim/firmware/PL18/manifest.json` (`086eb5df…`). Then `../.venv/bin/python -m slimbuild.uploader`
   (the uploader learns PL18).
1. **Stack headroom gate (SL00D):** Main and UI with at least 2 green pads (≥ 1.5 KB free). Hook stacks against PL17:
   new on the UI task, **a chord written into a step 348 B** (`step_add`) and **a key pad on a held step 220 B**
   (`note_pad_press`), stock's store calls not counted; **a Note-view pad 348 B** (PL17 308 B: the chord's build is a
   function of its own now, shared with step entry). The LED task 576 B, a page pad press 476 B, a page pad release
   444 B, Main (`main_ms`) 416 B: the same as PL17.
2. **Back up the SD card**: the test writes patterns and saves a project. Use a pack you can lose. Way back: Scales +
   Preset + Note at power-on, send the stock `.syx` (or PL17).
3. Flash `slim/build/PL18/circuittracks-4486-PL18.syx` with `slim/build/ct_uploader.html`. Then close the uploader's
   tab (only one program can use the MIDI port; section H needs it).
4. **A new empty project** (in the Projects view, tap an empty slot) at the start of section A. It starts with every
   CTPlay setting off: chord shape off, voice leading off, strum off, arpeggiator off, both Keys pads off. Its patterns
   are empty, 16 steps. Set the project's scale to a **major scale on C** (Scales). Tempo 120 BPM.
5. **Synth 1 on a Poly patch** with a clear, **sustained** sound (an organ or a soft pad with a quick attack), so you
   can hear a chord as long as it is held.
6. **The Note view** with the steps on rows 1–2 and the keys on rows 3–4 (stock's normal Note view; if all four rows
   play notes, press Note until rows 1–2 show the steps). Your keyboard layout. Step pads: steps 1–8 on row 1, steps
   9–16 on row 2. **"The C pad" is the C at the left end of the bottom row**; "the D pad" is the pad to its right, then
   E, F, G and A. Every chord in this plan is on that row.
7. **The click** (stock's metronome): hold Shift and look at Clear. **Green = the click only.** If it is not green,
   press Shift + Clear until it is. A count-in would delay every recording by a bar.
8. **Reading a step:** hold its step pad. Stock then plays the step's notes and lights up their key pads (they change
   colour). Let go: the notes stop. An empty step plays nothing and lights up no key pad.
9. **The phantom-press check:** a slow press can make the Circuit see a press on the next pad too (the pad to the
   right). After each press that writes or takes out a chord, the plan checks that the pad to the right did not go into
   a step: the D pad after C, the G pad after F, the A pad after G, step 6 after step 5, and so on.
10. Colours: bright = on (or selected), dim = off, dark = nothing there.

## Steps
### A. The Keys page
Start: **a new empty project** (Before you start, 4–6). Sequencer stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Press Synth 1 | Synth 1's Note view: steps on rows 1–2, keys on rows 3–4 | |
| 1b | Shift + Synth 1 | The **Chords page** (a new project opens on it): pad 1 bright green (shape off), pads 2–8 dim green | |
| 2 | Hold Shift, tap pad 32 (Keys). Release Shift | The Keys page: **pad 1 dim magenta, pad 2 dim green.** Pads 3–32 dark | |
| 3 | Press pad 1 | Pad 1 **bright magenta** (mono). Pad 2 stays dim green | |
| 3b | Press pad 1 | Pad 1 **dim magenta** (poly) | |
| 4 | Press pad 2 | Pad 2 **bright green** (chords in step entry on). Pad 1 stays dim magenta | |
| 4b | Press pad 2 | Pad 2 dim green (off) | |
| 4c | Press pad 2 | Pad 2 bright green (on). Leave it on | |
| 5 | Tap pad 3, then pad 32. These pads are free: they must do nothing | Nothing changes: pads 3 and 32 stay dark, pads 1 and 2 as they were | |
| 6 | Shift + Synth 2. Hold Shift, tap pad 32 (Keys), release Shift | **Synth 2's Keys page: pad 1 dim magenta, pad 2 dim green.** Each track has its own settings | |
| 6b | Shift + Synth 1 | Synth 1's Keys page (the page it used last): pad 1 dim magenta, **pad 2 bright green** | |
| 7 | Hold Shift, tap pad 25 (Chords), release Shift. Press pad 2 (triad) | Pad 2 bright green, pad 1 dim | |
| 7b | Press Synth 1 | The page closes: Synth 1's Note view | |
| 7c | Play the C pad | C E G, as a live chord. Let go: it stops | |

### B. Hold a step, then press a pad
Start: section A's project, Synth 1's Note view, sequencer stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 8 | Hold step pad 1. Keep holding it | Nothing sounds, no key pad lights up: step 1 is empty | |
| 8b | Press the C pad and let go of it. Keep holding step pad 1 | **At once: C E G together**, and they keep sounding while you hold step 1. The C, E and G pads light up | |
| 8c | Let go of step pad 1 | The chord stops | |
| 8d | **Phantom check.** Hold step pad 1 again | You hear C E G. The C, E and G pads light up. **The D pad does not light up** | |
| 8e | Let go of step pad 1 | The chord stops | |
| 9 | Press Play. Listen for two bars. Press Play again (stop) | **C E G on the first beat of each bar**, short (one step long). The click plays too | |
| 10 | **The pad again takes the chord out.** Hold step pad 1 (you hear C E G). Press the C pad and let go of it | **At once: the chord stops.** The C, E and G pads stop lighting up | |
| 10b | Let go of step pad 1. Hold it again | **Nothing sounds, no key pad lights up**: step 1 is empty. The D pad did not go in either (phantom check) | |
| 10c | Let go of step pad 1 | | |

### C. Hold a pad, then press a step
Start: as section B left it, sequencer stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 11 | Hold the C pad. Keep holding it | C E G (a live chord) | |
| 11b | Keep holding C. Press step pad 5 and hold it | You still hear C E G | |
| 11c | Let go of the C pad. Keep holding step pad 5 | **The chord keeps sounding** | |
| 11d | Let go of step pad 5 | The chord stops. Nothing keeps sounding | |
| 11e | Hold step pad 5 | **C E G**: step 5 has the chord. The C, E and G pads light up. Let go | |
| 11f | **Phantom check.** Hold step pad 6 | Nothing sounds, no key pad lights up: step 6 is empty. Let go | |
| 12 | **The other order.** Hold the C pad. Press step pad 9 and hold it | You still hear C E G | |
| 12b | Let go of step pad 9 first. Keep holding the C pad | **E and G stop at once. C keeps sounding** (found in emulation: letting go of the step ends the notes it wrote, except the note of the pad you hold) | |
| 12c | Let go of the C pad | C stops. Nothing keeps sounding | |
| 12d | Hold step pad 9 | C E G: step 9 has the chord. Let go | |
| 12e | **Phantom check.** Hold step pad 10 | Nothing sounds, no key pad lights up. Let go | |
| 13 | **Pad first writes nothing with the arpeggiator on.** Shift + Synth 1 (the Chords page). Hold Shift, tap pad 26 (Arp), release Shift. Press pad 2 (up) | Pad 2 bright green, pad 1 dim | |
| 13b | Press Synth 1. Hold the C pad | An arpeggio: C, E, G one after another, again and again | |
| 13c | Keep holding C. Press step pad 13, let go of it. Then let go of C | The arpeggio stops when you let go of C | |
| 13d | Hold step pad 13 | **Nothing sounds, no key pad lights up: step 13 is empty.** Expected: pad first writes nothing while the arpeggiator is on (the same with a falling strum, or when the pad's own note is already in the step) | |
| 13e | **Step first still works.** Keep holding step pad 13. Press the C pad and let go of it | **At once: C E G together** (not an arpeggio). The C, E and G pads light up; **the D pad does not** (phantom check) | |
| 13f | Let go of step pad 13 | The chord stops | |
| 13g | Shift + Synth 1 (the Arp page). Press pad 1 (off) | Pad 1 bright green, pad 2 dim | |

### D. Voice leading, step by step
Start: as section C left it (Synth 1 on the Arp page).

| # | Do | Expect | Result |
|---|---|---|---|
| 14 | Hold Shift, tap pad 25 (Chords), release Shift. Press pad 25 (voice leading close) | Pad 25 bright blue, pads 26–27 dim blue | |
| 14b | Press Synth 1. Hold step pad 2. Press the C pad and let go of it | At once: **C E G**. The D pad does not light up (phantom check) | |
| 14c | Let go of step pad 2 | The chord stops | |
| 15 | Hold step pad 6. Press the F pad and let go of it | At once: **C F A** (C below F, A above it: C stays where it was). The C, F and A pads light up; **the G pad does not** (phantom check) | |
| 15b | Let go of step pad 6 | The chord stops | |
| 16 | Hold step pad 10. Press the G pad and let go of it | At once: **B D G**, with the B just below the C. The D and G pads light up (the B is below the C pad: no pad shows it). **The A pad does not light up** (phantom check) | |
| 16b | Let go of step pad 10 | The chord stops | |
| 16c | Hold step pads 2, 6 and 10, one after another | C E G, C F A, B D G: from one chord to the next, each note stays or moves only a little. (With voice leading off they would be C E G, F A C, G B D) | |

### E. Pad 2 off: stock's step entry
Start: as section D left it (Synth 1's Note view).

| # | Do | Expect | Result |
|---|---|---|---|
| 17 | Shift + Synth 1 (the Chords page). Hold Shift, tap pad 32 (Keys), release Shift. Press pad 2 | Pad 2 dim green (off) | |
| 17b | Press Synth 1. Hold step pad 3. Press the C pad and let go of it | **C alone** (stock adds only the pad's note, the chord shape does not matter). Only the C pad lights up | |
| 17c | Let go of step pad 3 | C stops | |
| 17d | Shift + Synth 1 (the Keys page). Press pad 2 | Pad 2 bright green (on again, for section G) | |

### F. Mono record on pad 1
Start: as section E left it. Synth 2 has its chords off (a new project). **Stock's record quantise on:** hold Shift
and look at Record: bright = on. If it is dim, press Shift + Record.

| # | Do | Expect | Result |
|---|---|---|---|
| 18 | Press Synth 2 | Synth 2's Note view: steps on rows 1–2, keys on rows 3–4 (press Note if not) | |
| 18b | Press Record, then Play. Tap the C pad on each beat (with the click) for one bar. Press Play (stop), then Record (off) | About four step pads show notes (near steps 1, 5, 9 and 13) | |
| 19 | Shift + Synth 2 | Synth 2's **Keys page** (the page it used last, step 6) | |
| 19b | Press pad 1 | Pad 1 **bright magenta** (mono) | |
| 20 | Press Synth 2. Press Record, then Play. Tap the **E** pad on the same beats for one bar. Press Play (stop), then Record (off) | | |
| 20b | Press Play. Listen for two bars. Stop | Where you played E: **E alone, no C under it** | |
| 20c | Hold the step pads with notes, one by one | **A step you played E on lights up the E pad only**: its C is gone. A step your E missed keeps its C. No step lights up C and E together | |

### G. Save, load, power cycle
Start: as section F left it.

| # | Do | Expect | Result |
|---|---|---|---|
| 21 | Save the project (Save, then Save again) | It saves as stock does | |
| 21b | Load the same project again (Projects view, tap its slot) | It loads | |
| 21c | Shift + Synth 1 | Synth 1's Keys page: **pad 1 dim magenta, pad 2 bright green** | |
| 21d | Shift + Synth 2 | Synth 2's Keys page: **pad 1 bright magenta, pad 2 dim green** | |
| 21e | Press Synth 1. Hold step pad 6 | C F A: the written chords are ordinary notes, saved with the pattern. Let go | |
| 21f | Hold step pad 16. Press the C pad and let go of it | At once: **C E G**. The D pad does not light up (phantom check). Let go of step 16 | |
| 22 | Power off and on. Load the project. Do 21c–21f again | The same | |

### H. The link
Start: the project of section G loaded. Sequencer stopped. Shift + Synth 2 (its Keys page).

| # | Do | Expect | Result |
|---|---|---|---|
| 23 | Open `slim/pages/ctplay_link.html`, connect | "Connected: PL18, protocol 1, layout 1, **116 B, 17 fields**." | |
| 23b | Read | A new row, **`step chords`**, offset 115: `01` (Synth 1 on) | |
| 23c | Write offset 115, bytes `03` (Synth 1 and Synth 2 on) | One `state` line. **At once** on the Circuit: pad 2 bright green | |
| 23d | **A refused write.** Write offset 115, bytes `13` (bit 4: no track 5) | One `state` line, unchanged: the write is refused. Pad 2 stays bright green | |
| 23e | Close the page | | |

## Results
2026-11-01, PL18 (`086eb5df…`): **passed.** Every section A–H green (the run spanned two days, with a save and a
power-off after F). The user's notes per section:

A: All tests passed  
B: All tests passed  
C: All tests passed  
D: All tests passed  
E: All tests passed  
F: All tests passed  
G: All tests passed with a note: I had saved and turned the device off mid-testing after F as I had to stop for the day, and the status wasn't exactly right (the last chord before save was _very likely_ different) when I resumed, so 21f wasn't exactly those notes, but functionality is working.  
H: All tests passed

- **Step 21f:** the chord written was the shape saved with the project, not exactly C E G: the plan assumed
  section F's state carried on without a break. A test-plan premise, not the firmware.
