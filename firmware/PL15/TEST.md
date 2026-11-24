# PL15 — device test plan (Chords page, voice leading, recording past 16 steps)

**What it is:** PL14 with the Chords page reworked (spec `slim/docs/specs/2026-10-23-chords-page-design.md`), two
small fixes and a recording fix:
- **Shapes on top.** Row 1 (pads 1–8): off · triad · 7th · 9th · sus2 · sus4 · add9 · 6th, as before. **Row 2
  (pads 9–13), new:** power · shell 7 · quartal · 7sus4 · 6/9. One shape choice across both rows. Pads 14–16 dark.
- **Row 3 (pads 17–24):** the voicing, as before: inversion 17–20, spread 21–23, bass 24.
- **Row 4:** **voice leading (pads 25–27, new):** close · top line · bottom line, blue, one at a time. **Strum speed
  (28–30):** slow · medium · fast; none lit = off (no "off" pad any more). **Direction (31–32):** rising · falling.
- **The Quick view** (Shift in the Note view) now shows the page's rows 1–2: all 13 shapes on pads 17–29. Voicing,
  voice leading and strum are on the page only.
- **Voice leading:** each chord you play takes the inversion that sits best against the chord before it on that track.
  While it is on, the inversion pads show the stored inversion dim. Pressing an inversion pad turns it off.
- **Saved:** the row 2 shape and voice leading (a new field, `chord_voice`, in the second saved block).
- **Fix 1:** in a draft, the re-write waits until every pad of the page is up (PL14 wrote when the latest pad was
  lifted, even with another pad still down).
- **Fix 2:** the CTCtrl link stores a write in one go, so two messages arriving together cannot mix (nothing to see;
  section I checks that a write still works).
- **Recording:** a note held for more than 16 steps is recorded whole on a pattern longer than 16 steps: stock cut it at
  16 steps, PL15 ties it on 16 steps later. Patterns of 16 steps or less are as before.

With voice leading off and a row 1 shape, every chord plays the same notes as on PL14 (checked in emulation against
the published PL14). PL14 passed on the device (`firmware/PL14/TEST.md`): this run checks what changed.

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL15.toml` (once PL15 is tagged: from the tag). The
   printed syx sha256 must equal `syx_sha256` in `slim/firmware/PL15/manifest.json` (`cd47c377…`).
   **Also build PL14** for section H (it flashes PL14 and then PL15 again): `git checkout PL14`, then
   `cd slim && ../.venv/bin/python -m slimbuild versions/PL14.toml`, then `git checkout -` (back to where you were).
   Its sha256 must be `0d58e24b…` (`slim/firmware/PL14/manifest.json`).
1. **Stack headroom gate (SL00D):** Main and UI with at least 2 green pads (≥ 1.5 KB free). Hook stacks against
   PL14: a **Note-view pad 308 B** (PL14 256 B: the voice-leading search); the **LED task 448 B** (PL14 432 B: the
   CTCtrl link's state is 81 B now); the recorder's commit 104 B (PL14 96 B) and the new step after it 96 B (the
   recording fix). A page pad press 468 B, Main (`main_ms`) 416 B: the same. A page pad release 444 B (PL14 452 B).
2. **Back up the SD card**: the test writes patterns and saves projects. Use a pack you can lose. Way back: Scales +
   Preset + Note at power-on, send the stock `.syx` (or PL14).
3. Flash `slim/build/PL15/circuittracks-4486-PL15.syx` with `slim/build/ct_uploader.html`. If an earlier PL15 test
   build is installed, flash PL14 first: a build with the same name does not install over itself.
4. **A new empty project:** in the Projects view, tap an empty slot. Every step expects its defaults (every CTPlay
   setting off: Chords shape off, root position, close spread, no bass, voice leading off, strum off, rising). Set the
   project's scale to a **major scale on C** (Scales). Then every white key is in the scale.
5. **Synth 1** on a Poly patch with a clear, **sustained** sound (an organ or a soft pad with a quick attack): a held
   note keeps sounding, so you can hear chords and long notes. Your Note view in your keyboard layout.
   "Play C" means any C. **Sections D and G use one octave for every chord:** the C of the bottom row (pad 25) and the
   white keys to its right (D, E, F, G, A, B).
6. **Reading the chords:** the notes are listed **lowest first**, for example "C E F A" for F with C and E below it.
   Check them by ear. While you hold a chord, the pads of its other notes also light up where your layout shows them.
7. Colours: bright = selected, dim = not selected, dark = nothing there. "Blue" = the inversion blue (pads 17–20).

## Steps
### A. The Chords page (Synth 1, sequencer stopped)
| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Shift + Synth 1 | The Chords page opens (a new project). ▼ is blue, ▲ is dark | OK |
| 1b | Look at row 1 | Pad 1 bright green (shape off), pads 2–8 dim green | OK |
| 1c | Look at row 2 | **Pads 9–13 dim green. Pads 14–16 dark** | OK |
| 1d | Look at row 3 | Pad 17 bright blue, 18–20 dim blue. Pad 21 bright magenta, 22–23 dim magenta. Pad 24 dim orange | OK |
| 1e | Look at row 4 | **Pads 25–27 dim blue** (voice leading off). **Pads 28–30 dim white: none lit** (strum off). Pad 31 bright white (rising), pad 32 dim white | OK |
| 2 | Hold Shift (then release it) | While Shift is held, row 4: pad 25 bright green, 26 dim blue, 27 dim orange, 28 dim yellow, 29–31 dark, 32 dim magenta. Rows 1–3 dark | OK |
| 3 | Press pad 2 (triad) | Pad 2 bright green, pad 1 dim | OK |
| 3b | Press pad 10 (shell 7) | **Pad 10 bright green. Every other shape pad dim, pad 1 and pad 2 too**: one choice across both rows | OK |
| 3c | Press pad 3 (7th) | Pad 3 bright, pad 10 dim | OK |
| 3d | Press pads 14, 15 and 16 | Nothing changes (they are dark and do nothing) | OK |
| 3e | Press pad 1 | Pad 1 bright (shape off again) | OK |
| 4 | Press pad 24 three times, looking after each press | Bright orange (bass below), white (rootless over bass), dim orange (off) | OK |
| 4b | Press pad 22, then pad 21 | Pad 22 bright magenta, 21 dim; then 21 bright again | OK |
| 4c | Press pad 19, then pad 17 | Pad 19 bright blue, 17 dim; then 17 bright again | OK |
| 5 | **Voice leading.** Press pad 25 (close) | Pad 25 bright blue, 26 and 27 dim blue. **Row 3: pad 17 dim blue (the stored inversion), pads 18–20 dark** | OK |
| 5b | Press pad 26 (top line) | Pad 26 bright, 25 dim: one kind at a time. Pad 17 still dim, 18–20 still dark | OK |
| 5c | Press pad 26 again | Pads 25–27 all dim: voice leading off. Pad 17 bright blue, 18–20 dim blue again | OK |
| 5d | Press pad 19 (2nd inversion), then pad 25 (close) | Pad 25 bright. **Pad 19 dim, pads 17, 18 and 20 dark** | OK |
| 5e | Press pad 25 again | Voice leading off: pads 25–27 dim. **Pad 19 bright again**: turning voice leading off brings back the inversion you set | OK |
| 5f | Press pad 27 (bottom line), then pad 18 (1st inversion) | After pad 27: pad 27 bright. **After pad 18: pads 25–27 all dim** (an inversion pad turns voice leading off), pad 18 bright blue, 17, 19 and 20 dim | OK |
| 5g | Press pad 17 | Pad 17 bright (root position again) | OK |
| 6 | **Strum.** Press pad 29 (medium) | Pad 29 bright white, 28 and 30 dim | OK |
| 6b | Press pad 29 again | Pads 28–30 all dim: strum off | OK |
| 6c | Press pad 32, then pad 31 | Pad 32 bright, 31 dim (falling); then 31 bright again (rising) | OK |
| 7 | Press ▼ | The Arp page. Press ▲: the Chords page, as you left it (every setting at its default) | OK |

### B. The Quick view (Synth 1, sequencer stopped)
| # | Do | Expect | Result |
|---|---|---|---|
| 8 | Press Note (the page closes). Hold Shift | **Pads 17–29 green:** pad 17 bright (off), 18–29 dim. **Pads 30–32 dark.** The 1-16/17-32 LED green. No inversion or strum pads | OK |
| 8b | Still holding Shift, tap pad 18 (triad). Release Shift. Play C | Pad 18 turned bright, 17 dim. C plays **C E G** | Took a couple of presses across the keyboard before the chords started to show on the pads. Not sure if it was due to me changing the scale/layout. Had the stock default (C min with two full rows) first. |
| 8c | Shift + pad 25 (power). Release Shift. Play C | Pad 25 bright, 18 dim. C plays **C G C**: C, G above it, and C an octave up | OK |
| 8d | Shift + pad 18 (triad) again. Play C | Pad 18 bright, 25 dim: a row 1 pick replaces the row 2 shape. C E G | OK |
| 8e | Hold Shift, tap pads 30, 31 and 32 | Nothing changes, nothing plays | OK |
| 8f | Shift + Synth 1 (the Chords page). Look at rows 1–2 | Pad 2 bright green (triad), the others dim: the page shows what the Quick view set. Press Note | OK |
| 9 | Hold Shift, press 1-16/17-32 | The Arp Quick view: LED blue. Pads 17–24 the patterns (17 bright green), 25–28 the rates (25 bright blue), 29–30 dim magenta, 31 dark, 32 dim orange | OK |
| 9b | Still holding Shift, press 1-16/17-32 again | The Chords Quick view again: LED green, pad 18 bright | OK |

### C. The new shapes by ear (Synth 1, Note view; pick with Shift + the pad, then release Shift)
| # | Do | Expect | Result |
|---|---|---|---|
| 10 | Shift + pad 25 (power). Play C, then G | C: **C G C**. G: **G D G** (the fifth and the octave above the pad's note) | OK |
| 11 | Shift + pad 26 (shell 7). Play C, then G | C: **C E B**. G: **G B F**. No fifth | OK |
| 12 | Shift + pad 27 (quartal). Play D, then C | D: **D G C F**. C: **C F B E**. Notes a fourth apart | OK |
| 13 | Shift + pad 28 (7sus4). Play G, then C | G: **G C D F**. C: **C F G B** | OK |
| 14 | Shift + pad 29 (6/9). Play C, then G | C: **C E G A D** (five notes, D above the next C). G: **G B D E A** | OK |
| 15 | **Bass on a new shape.** Shift + Synth 1 (Chords page), press pad 24 once (bright orange). Press Note. Play C | 6/9 with bass below: **C (an octave below), then C E A D**. The G is left out: a chord with a bass stays at 5 notes | OK |
| 15b | Shift + Synth 1, press pad 24 two more times (white, then dim orange) | Pad 24 dim orange: no bass | OK |
| 16 | **An inversion on a new shape.** On the page: pad 10 (shell 7), pad 18 (1st inversion). Press Note. Play C | **E B C**: E and B below the pad's C | OK |
| 16b | Shift + Synth 1: pad 17 (root position), pad 2 (triad). Press Note. Play C | C E G, as on PL14 | OK |

### D. Voice leading by ear (Synth 1; every chord from the one octave of Before you start, step 5)
Each kind starts from the same chord: C in root position, played with voice leading off. Then F, E, D, C.

| # | Do | Expect | Result |
|---|---|---|---|
| 17 | Shift + Synth 1 (Chords page): pad 3 (7th). Pad 17 is bright (root position), pads 25–27 dim. Press Note. Play C | **C E G B** | OK |
| 17b | Shift + Synth 1: pad 25 (close). Press Note. Play F | **C E F A** (C and E below the pad's F) | OK |
| 17c | Play E | **B D E G** | OK |
| 17d | Play D | **A C D F** | OK |
| 17e | Play C | **G B C E** | OK |
| 17f | Listen back over 17b–17e | Close: every note moves down by one or two semitones from chord to chord; the whole chord walks down together. The highest notes: A, G, F, E | OK |
| 18 | Shift + Synth 1: pad 17 (voice leading off, root position). Press Note. Play C | **C E G B** (the same start) | OK |
| 18b | Shift + Synth 1: pad 26 (top line). Press Note. Play F | **E F A C** (E below the pad's F; A and C above) | OK |
| 18c | Play E | **D E G B** | OK |
| 18d | Play D | **D F A C** | OK |
| 18e | Play C | **C E G B** | OK |
| 18f | Listen back over 18b–18e | Top line: the highest note stays near the top of the first chord: **C, B, C, B** | OK |
| 19 | Shift + Synth 1: pad 17. Press Note. Play C | **C E G B** | OK |
| 19b | Shift + Synth 1: pad 27 (bottom line). Press Note. Play F | **C E F A** | OK |
| 19c | Play E | **B D E G** | OK |
| 19d | Play D | **C D F A** (C below the pad's D: not A C D F as with close) | OK |
| 19e | Play C | **C E G B** | OK |
| 19f | Listen back over 19b–19e | Bottom line: the lowest note: **C, B, C, C** | OK |
| 20 | **A power chord keeps its notes.** Shift + Synth 1: pad 9 (power), pad 18 (1st inversion: voice leading off). Press Note. Play C | Two notes only: **G C** (G below the pad's C). The power chord's octave would land on the pad's own C, so the 1st inversion has one note less | OK |
| 20b | Shift + Synth 1: pad 25 (close). Press Note. Play C, then G | C: **C G C**, G: **G D G**: three notes each, as in step 10. Voice leading never takes an inversion with fewer notes | OK |
| 20c | Shift + Synth 1: pad 17 (voice leading off, root position) | Pad 17 bright, pads 25–27 dim | OK |

### E. Strum (Synth 1)
| # | Do | Expect | Result |
|---|---|---|---|
| 21 | Chords page: pad 2 (triad), then pad 28 (slow) | Pad 28 bright white, 29–30 dim | OK |
| 21b | Press Note. Play C | A slow roll, rising: C, then E, then G | OK |
| 21c | Shift + Synth 1: pad 30 (fast). Press Note. Play C | Pad 30 was bright, 28 dim. A fast roll | OK |
| 21d | Shift + Synth 1: pad 30 again. Press Note. Play C | Pads 28–30 were all dim: strum off. C E G together | OK |
| 21e | Shift + Synth 1: pad 29 (medium), pad 32 (falling). Press Note. Play C | Pad 29 and pad 32 were bright. A roll from the top down: G, E, then C | OK |
| 22 | **With an arpeggio.** Shift + Synth 1, press ▼ (Arp): pad 2 (up). Press ▲ (Chords) | **Pads 28–30: only pad 29 lit, dim white; 28 and 30 dark. Pads 31–32: only pad 32 lit, dim white; 31 dark** (strum is ignored while an arpeggio plays) | OK |
| 22b | ▼ (Arp): pad 1 (pattern off). ▲ (Chords) | Pad 29 bright white, 28 and 30 dim. Pad 32 bright, 31 dim | OK |
| 22c | Press pad 29 again (strum off), then pad 31 (rising) | Pads 28–30 all dim. Pad 31 bright | OK |
| 22d | ▼ (Arp): pad 2 (up). ▲ (Chords) | **Pads 28–30 all dark** (a stored "off" shows no speed). Pad 31 dim white, 32 dark | OK |
| 22e | ▼ (Arp): pad 1 (pattern off). ▲ (Chords) | Pads 28–30 dim, 31 bright, 32 dim | OK |

### F. Fix 1: two pads in a draft (Synth 1)
| # | Do | Expect | Result |
|---|---|---|---|
| 23 | Press Note. Play C once (the last played pad; the shape is the triad) | C E G | OK |
| 23b | Shift + Synth 1, hold Shift, tap pad 27. Release Shift: Pattern tools. Press pad 4 (4 hits) | Pads 1, 5, 9 and 13 bright orange (the preview) | OK |
| 23c | Press ▼ ▼ (Pattern tools 2, Melody). Press pad 2 (order up) | Pad 2 bright yellow | OK |
| 23d | Press Play (the pattern is empty: silence). Press pad 32, then pad 32 again | After the first press pad 32 blinks. When you lift your finger the second time, the loop plays **C E G C** on steps 1, 5, 9, 13. Pad 32 bright orange: a draft (order up is a new setting) | OK |
| 24 | Press ▲ ▲ (Pattern tools). **Press pad 6 and keep holding it** | The preview shows 6 hits at once: pads 1, 4, 7, 9, 12, 15. **The loop still plays the 4 notes** (nothing is written while a pad is down) | OK |
| 24b | Still holding pad 6, **press pad 8 and keep holding it too** | The preview shows 8 hits: pads 1, 3, 5, 7, 9, 11, 13, 15. The loop still plays the 4 notes | OK |
| 24c | **Lift pad 8. Keep holding pad 6** | **The loop does not change: still 4 notes.** (PL14 re-wrote here, with pad 6 still down) | OK |
| 24d | Lift pad 6 | Now the loop changes: **8 notes, C E G C E G C E** on steps 1, 3, 5 … 15 (the latest press's 8 hits) | OK |
| 25 | **Undo waits too.** Press pad 3 and keep holding it | The preview shows 3 hits (pads 1, 7, 12). The loop still plays the 8 notes | OK |
| 25b | Still holding pad 3, press pad 31 (Undo) and lift it. Keep holding pad 3 | Nothing changes yet: the loop still plays the 8 notes | OK |
| 25c | Lift pad 3 | **Silence:** Undo ran, the pattern is back as it was before the first Write (empty). Pad 32 dim orange (the draft ended). Pad 31 blue | OK |

### G. Save, power cycle, reload
| # | Do | Expect | Result |
|---|---|---|---|
| 26 | **Settings to save.** Shift + Synth 1, hold Shift, tap pad 25 (Chords). Release Shift. Press pad 3 (7th) | Pad 3 bright green, pad 17 bright blue, pads 25–27 dim | OK |
| 26b | Press Note. Play C | **C E G B** | OK |
| 26c | Shift + Synth 1: pad 25 (close). Press Note. Play F, then E | F: **C E F A**. E: **B D E G** | OK |
| 26d | **Synth 2:** Shift + Synth 2 (its Chords page). Press pad 11 (quartal) | Pad 11 bright green, pad 1 dim | OK |
| 26e | Stop the sequencer. Save the project: press Save (it flashes), then Save again (stock saves it in its own slot) | It saves as stock does | OK |
| 27 | Power off and on. Load the project: in the Projects view, tap its slot (the one from Before you start, step 4), if the Circuit did not open it by itself | It loads as stock does | OK |
| 27b | Shift + Synth 1 | The Chords page (saved): pad 3 bright green, **pad 25 bright blue** (close), 26–27 dim. Pad 17 dim blue, 18–20 dark | OK |
| 27c | Press Note. Play C (the first chord since the load) | **C E G B**: root position, the inversion you set. A load forgets the chord before. (If it had led from step 26c's E chord, you would hear B C E G) | OK |
| 27d | Play F | **C E F A**: voice leading works after a load | OK |
| 27e | Shift + Synth 2 | Its Chords page: **pad 11 bright green**, the other shapes dim; pads 25–27 dim | OK |
| 27f | Press Note (Synth 2's Note view). Play C | **C F B E** (quartal) | OK |

### H. The PL15 project on PL14 (flash PL14, then PL15 again)
| # | Do | Expect | Result |
|---|---|---|---|
| 28 | Flash PL14 (`slim/build/PL14/circuittracks-4486-PL14.syx`). Load the project from step 26e | It loads | Skipped (alpha policy) |
| 28b | Shift + Synth 1 | **PL14's Chords page** (its own layout): row 1 strum (pad 1 bright white: off; pad 5 bright: rising). Rows 3–4: pad 17 bright blue, pad 21 bright magenta, pad 24 dim orange, **pad 27 bright green (7th)**. No voice-leading pads | Skipped (alpha policy) |
| 28c | Press Note. Play C, then F | C: **C E G B**. F: **F A C E** (root position: PL14 has no voice leading) | Skipped (alpha policy) |
| 28d | Shift + Synth 2 | PL14's Chords page: **pad 25 bright green: shape off.** PL14 does not know the row 2 shapes | Skipped (alpha policy) |
| 28e | Press Note. Play C | **C alone** (no wrong chord) | Skipped (alpha policy) |
| 29 | **A re-save on PL14.** Save the project to another, empty slot (save to another slot) | Saves as stock does | Skipped (alpha policy) |
| 30 | Flash PL15 again (`circuittracks-4486-PL15.syx`). Load the copy from step 29 | It loads | Skipped (alpha policy) |
| 30b | Shift + Synth 1 | Chords: pad 3 bright green (7th kept). **Pads 25–27 dim: PL14's save dropped voice leading.** Pad 17 bright blue | Skipped (alpha policy) |
| 30c | Shift + Synth 2 | Chords: **pad 1 bright green (shape off): the quartal was dropped too.** Pad 11 dim | Skipped (alpha policy) |
| 31 | Load the project from step 26e (the original). Shift + Synth 1 | Chords: pad 3 bright green, pad 25 bright blue (close) | Skipped (alpha policy) |
| 31b | Shift + Synth 2 | Chords: pad 11 bright green. Nothing was lost by loading it on PL14 | Skipped (alpha policy) |

### I. CTCtrl and the link (PL15 installed, the project from step 26e loaded)
| # | Do | Expect | Result |
|---|---|---|---|
| 32 | On the Circuit: Shift + Synth 2 (its Chords page, pad 11 bright). Open CTCtrl, connect. Select Synth 2, Chord tab | The CTPlay panel appears. **The shape shows "Single"** (CTCtrl's name for shape off: today's CTCtrl does not know the row 2 shapes). No error | OK |
| 32b | In CTCtrl, set the inversion to the 1st | At once on the Circuit: pad 18 bright blue, 17 dim. **Pad 11 stays bright green** (the quartal stays) | OK |
| 32c | Press Note (Synth 2's Note view). Play C | **F B C E** (quartal, 1st inversion: F and B below the pad's C) | OK |
| 32d | In CTCtrl, set the bass to "below". On the Circuit: Shift + Synth 2 | Pad 24 bright orange. Pad 11 still bright | OK |
| 32e | Press Note. Play C | **C (an octave below), then F B C E** | OK |
| 32f | In CTCtrl, pick the triad. On the Circuit: Shift + Synth 2 | **Pad 2 bright green, pad 11 dim**: a row 1 pick from CTCtrl replaces the row 2 shape | OK |
| 32g | Press Note. Play C | **C (an octave below), then E G C** (triad, 1st inversion, bass below) | OK |
| 32h | **An inversion from CTCtrl ends voice leading.** On the Circuit: Shift + Synth 1 | Chords: pad 3 bright green, **pad 25 bright blue** (close), pad 17 dim blue, 18–20 dark | OK |
| 32i | Press Note (Synth 1's Note view). Play the C of pad 25, then the F to its right (the one octave of Before you start, step 5) | C: **C E G B**. F: **C E F A** (close, as in step 26c) | OK |
| 32j | In CTCtrl, select Synth 1, Chord tab. Set the inversion to the 2nd. On the Circuit: Shift + Synth 1 | **Pads 25–27 all dim**: voice leading off, as an inversion pad does. Pad 19 bright blue, 17, 18 and 20 dim | OK |
| 32k | Press Note. Play the C of pad 25 again | **G B C E** (7th, 2nd inversion: G and B below the pad's C). With voice leading still on you would hear B C E G (led from the F) | OK |
| 32l | Shift + Synth 1: pad 17 (root position), then pad 25 (close) | Pad 25 bright blue, pad 17 dim, 18–20 dark: as loaded, for step 33b | OK |
| 33 | Close CTCtrl. Open `slim/pages/ctplay_link.html`, connect | "Connected: PL15, protocol 1, layout 1, **81 B, 12 fields**." | OK |
| 33b | Read | The table has a new row **`chord voice`**, offset 77, with 4 bytes: **`10 00 00 00`** (Synth 1: close; Synth 2: no row 2 shape since step 32f) | OK |
| 33c | **A link write (fix 2).** Write offset 77, bytes `01` | One `state` line. At once: Synth 1 has the power chord (row 2 shape 1) and voice leading off | OK |
| 33d | On the Circuit: Shift + Synth 1 | Chords: **pad 9 bright green, pad 3 dim. Pads 25–27 dim.** Pad 17 bright blue | OK |
| 33e | Press Note. Play C | **C G C** | OK |
| 33f | **A refused write.** On the page: Write offset 77, bytes `06` (row 2 shape 6: no pad makes it) | One `state` line, unchanged: the write is refused. On the Circuit nothing changes (pad 9 still bright) | OK |

### J. Recording a note held past 16 steps
Stock's record quantise stays on (the default: Shift + Record shows Record bright). Count the steps by the beat: a
32-step pattern is two bars of 16 steps; step 1 = beat 1 of the first bar, step 17 = beat 1 of the second bar, step 21
= beat 2 of the second bar. Holding from step 1 to step 21 is 20 steps (five beats).

**The lead-in:** set the metronome to click and count-in: Shift + Clear until Clear shows **cyan** while Shift is held
(off, click, count-in, both). Then, with the sequencer stopped and Record on, Play counts one bar of clicks first, and
the loop starts on step 1 right after it. Press C on the first beat after the count.

**Where a note starts:** in stock's Gate view, the first step pad with a note. If a C below starts on step N instead
of step 1 (the quantise moved it), check steps N and N + 16 wherever a row says steps 1 and 17.

| # | Do | Expect | Result |
|---|---|---|---|
| 34 | Make a new empty project and set its scale to C major again (as Before you start, step 4). Give Synth 1 the sustained patch of Before you start, step 5. Set the metronome to cyan (the lead-in above) | The Note view, every CTPlay setting off | OK |
| 34b | In stock's Pattern Settings, set Synth 1's pattern 1 to end at step 32 (start at step 1). Press Note | A 32-step pattern: the playhead runs through steps 1–32 | OK |
| 35 | **A note held 20 steps.** Press Record, then Play: one bar of count-in. On the first beat after it (step 1), press and hold C. Let go on step 21 (beat 2 of the second bar). Press Record (recording off). Let the loop play | **One long C from step 1 to about step 21, with no new attack on step 17.** Silence after it until the loop starts again. (PL14 and stock stopped it at the end of step 16) | OK |
| 35b | Stop the sequencer. Stock's Gate view. Hold the first step pad that has a note | A C. Its gate bar is either **full** (16 steps) or **about 4 steps**. Note which | OK |
| 35c | Press 1-16/17-32 (the other half of the steps). Hold the first step pad that has a note | A C with the other gate: full or about 4 steps. **One half has the full gate, the other about 4 steps.** The full one is where the C starts (step 1, or N), the short one 16 steps later (what was left after 16 steps) | OK: I held longer, but gate length is as played |
| 35d | Stock's Micro Step view (press Gate twice; as in PL14's step 21d). Hold the first step pad that has a note. Look at the Tie pad (pad 24 in that view) | Lit or not lit. Note which | Lit |
| 35e | Press 1-16/17-32 (the other half). Hold the first step pad that has a note. Look at the Tie pad | The other case. **The Tie pad is lit on exactly one of the two halves** (the C that starts the note: it is tied on to the note 16 steps later), not on the other (the note ends there) | OK |
| 36 | **Stop while you still hold the note.** (The sequencer is stopped since step 35b.) In stock's Patterns view select Synth 1's pattern 2 (empty) and set it to 32 steps in Pattern Settings. Press the Note button (the Note view). Press Record, then Play (the count-in). On step 1 press and hold C. On about step 21, still holding C, press Play (stop). Then let go | The sequencer stops | OK |
| 36b | Press Play (stopping ended recording too) | **One long C from where it started to about where you stopped, with no new attack 16 steps after it began.** At Stop the held note is written as if you had let go there: tied on, and its last part 16 steps later (checked in emulation: `test_stop_while_held_writes_the_whole_note`). Letting go after Stop adds nothing | OK. |
| 37 | **Mono record.** Stop. Select Synth 1's pattern 3 (empty), set it to 32 steps. Press Note. Play G once. Shift + Synth 1, hold Shift, tap pad 27 (Pattern tools). Press pad 2 (2 hits) | The preview: pad 1 bright orange, pads 2–16 dim (the second hit is on step 17, past the preview) | OK |
| 37b | Press pad 32, then pad 32 again (written when you lift your finger). Press Play | A short G on step 1 and one on step 17 (beat 1 of each bar) | OK |
| 37c | Hold Shift, tap pad 32 (Keys). Release Shift. Press pad 2 (mono) | Pad 2 bright magenta | OK |
| 37d | Stop. Press Note. Press Record, then Play (the count-in). On step 1 press and hold C, let go on step 21. Press Record (recording off) | Recording as usual | OK |
| 37e | In stock's Gate view, find the step pad with a **full gate bar** (press 1-16/17-32 to look at both halves): that is where the C starts. It should be the **first** pad of its half (step 1). **If it is not, redo the take:** press Note, play G once (Write writes the last played pad), Shift + Synth 1 (it opens Keys), hold Shift, tap pad 27 (Pattern tools), release Shift, press pad 32 twice (the pattern is the two Gs again, the C gone). Then repeat step 37d | The full gate bar is on the first pad of its half: the C starts on step 1 | OK |
| 37f | Listen to the loop | **Step 1: C alone** (mono replaced the G there). **The C holds to about step 21. On step 17 the G still plays, under the held C**, and the C has no new attack: the part of a held note after step 16 does not clear its step | OK |
| 37g | Shift + Synth 1: hold Shift, tap pad 32 (Keys). Release Shift. Press pad 1 (poly) | Pad 1 bright magenta | OK |
| 38 | **An arpeggio held 20 steps (as PL14).** Stop. Select Synth 1's pattern 4 (empty), set it to 32 steps. Shift + Synth 1, hold Shift, tap pad 25 (Chords). Release Shift. Press pad 2 (triad). Press ▼ (Arp): pad 2 (up), pad 11 (1/16) | Pad 2 bright green on Arp, pad 11 bright blue | OK |
| 38b | Press Note. Press Record, then Play (the count-in). On step 1 hold C, let go on step 21. Press Record (recording off) | The arpeggio plays while you hold: C E G C E G … (C major) | OK |
| 38c | Listen to the loop | The arpeggio plays back as you played it: short notes, each with its own attack, on steps 1 to 20 (steps 17–20 too). No long note. As PL14 | OK |
| 38d | Shift + Synth 1 (Arp): pad 1 (pattern off). Stop | The arpeggio is off | OK |

## Results
2026-10-24–25, PL15 (`cd47c377…`): **passed.** Every step OK except section H, skipped.
- **Section H (the round trip to PL14, steps 28–31b):** skipped by the alpha policy (CLAUDE.md, 2026-10-25): no round
  trips to older builds until beta.
- **Anything odd on the device:** one, cosmetic, not seen again.
  - **Step 8b:** the first chords did not light their pads; after a few presses across the keyboard they did. This
    was right after flashing, and the user had just changed the Note view from stock's default (C minor, two full
    rows of the scale) to the keyboard layout. `followups.md`, "Chord pads dark right after flashing": PL16's TEST.md
    checks it first.
  - **Step 35c:** the hold was longer than 20 steps; the gates matched the hold.
- **Two steps of the plan, reworded here:**
  - Step 36's "Press Note" meant the Note button, and was read as "press a note". The step now says "the Note
    button".
  - Step 36b's "Press Record (recording off)" is not needed: Stop ends recording too.
