# PL14 — device test plan (melody variations)

**What it is:** PL13 plus five tools for the Pattern tools Write (spec
`slim/docs/specs/2026-10-21-melody-variations-design.md`). All of them write ordinary stock steps:
- **Cycle** (Pattern tools, pads 25–28, cyan): the first rhythm over 3, 5, 6 or 7 steps, repeated along the pattern.
- **A second rhythm and a combine** (a new page, **Pattern tools 2**: pad 27 of the page list again): its hits on pads
  1–16 (white preview), rotate on 17–19, combine on 20–24 (violet): both · either · one, not both · first without
  second · accent.
- **Thinning** (Pattern tools 2, pads 25–27, cyan): drop about 1 in 4, 1 in 3 or 1 in 2 hits (never the first).
- **Ties** (a new page, **Phrasing**: pad 28 of the page list again; pads 1–3, cyan): some hits hold the note before.
  They are stock's own ties (the Micro Step view shows them).
- **Octave jumps** (Phrasing, pads 5–7, magenta): some notes of the line jump an octave.
- **Pages:** a feature's two pages share its pad in the page list. Tap the pad: the page of it used last. Tap it again
  while that feature is open: its other page. ▲ ▼ walk all seven pages.
- **Saved:** every new setting, which page each track was on, and now the last played pad. A second saved block holds
  them, so PL10–PL13 still read the first block as before.
- **Two small fixes:** (1) a loaded project with rootless and no bass (or arpeggiator modifier 3) no longer blocks
  CTCtrl writes to that track; (2) in a draft, a press that changes nothing (▲ ▼, a dark pad) no longer cancels the
  re-write of a pick you are still holding.

Every pattern write still happens when you lift your finger (PL13). With every new setting off, Write writes exactly
what PL13 wrote (checked in emulation). PL13 passed on the device (`firmware/PL13/TEST.md`): this run checks only what
changed.

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL14.toml` (once PL14 is tagged: from the tag). The
   printed syx sha256 must equal `syx_sha256` in `slim/firmware/PL14/manifest.json` (`0d58e24b…`).
   **Also build PL13** for section D (steps 29–31 flash PL13 and then PL14 again): `git checkout PL13`, then
   `cd slim && ../.venv/bin/python -m slimbuild versions/PL13.toml`, then `git checkout -` (back to where you were).
   Its sha256 must be `7e199b90…` (`slim/firmware/PL13/manifest.json`).
1. **Stack headroom gate (SL00D):** Main and UI with at least 2 green pads (≥ 1.5 KB free). Hook stacks against PL13:
   the LED task **432 B** (PL13 336 B: the CTCtrl link's state is 77 B now, 162 B on the wire); a pad press 468 B
   (PL13 476 B); a pad release 452 B, Main (`main_ms`) 416 B, a Note-view pad 256 B: the same. The LED task is the one
   that grew.
2. **Back up the SD card**: the test writes patterns and saves projects. Use a pack you can lose. Way back: Scales +
   Preset + Note at power-on, send the stock `.syx` (or PL13).
3. Flash `slim/build/PL14/circuittracks-4486-PL14.syx` with `slim/build/ct_uploader.html`. If an earlier PL14 test
   build is installed, flash PL13 first: a build with the same name does not install over itself.
4. **A new empty project:** in the Projects view, tap an empty slot. Every step expects its defaults (all CTPlay
   settings off, no hits picked, pattern 1 of 16 steps). Set the project's scale to a **major scale on C** (Scales).
5. **Synth 1** on a patch with a clear attack and a sustained sound (a saw lead or a synth brass, not a pad): a note
   that is held sounds different from one that is struck again. Your Note view in your keyboard layout. "Play C" means
   any C in your layout; no step depends on which pad plays which note.
6. **Reading the rhythms:** `x... x... x... x...` is the 16 steps of the loop, in four groups of four: `x` a note,
   `X` a loud note, `.` a rest. On the Pattern tools page, pads 1–16 show the same 16 steps (bright = a note).
   "When you lift your finger" means: the pattern changes then, not when you press.
   The exact strings and note lists are what emulation wrote for this plan's presses in this order (the dice and the
   thinning depend on every earlier dice press). If yours differ, check what the row says must hold (how many notes,
   the first step playing) and note the difference in the Results.
7. Colours: bright = selected, dim = not selected, dark = nothing there. **Note in the Results whether violet (the
   combine) and cyan (cycle, thinning, ties) look clearly different on the device.**

## Steps
### A. Pages (Synth 1, sequencer stopped)
| # | Do | Expect | Result |
|---|---|---|---|
| 1 | In the Note view, play C once. Then Shift + Synth 1 | The Chords page opens (a new project). ▼ is blue, ▲ is dark | OK |
| 2 | Hold Shift | Row 4: pad 25 bright green, 26 dim blue, 27 dim orange, 28 dim yellow, 29–31 dark, 32 dim magenta. Rows 1–3 dark | OK |
| 3 | Still holding Shift, tap pad 27 | Pad 27 turns bright orange | OK |
| 3b | Release Shift. Look at rows 1–3 | **Pattern tools** (its first page). Pads 1–16 dim orange. Pads 17–20 dim white. Pad 22 dim magenta, 23 bright magenta, 24 dim magenta | OK |
| 3c | Look at pad 21 (the gate) | The colour of a 3/6 gate (the default): the same colour as pad 21 of this track's Arp page in a new project, and as stock's Gate view gives a 3/6 step | OK |
| 3d | Look at row 4 | **Pads 25–28 dim cyan (new: the cycle).** Pad 29 dim white. Pads 30, 31, 32 dark | OK |
| 3e | Look at ▼ and ▲ | ▼ orange, ▲ blue | OK |
| 4 | Hold Shift, tap pad 27 again | Pad 27 stays bright orange (one pad for both pages) | OK |
| 4b | Release Shift. Look at rows 1–3 | **Pattern tools 2**. Pads 1–16 dim white. Pads 17–19 dim white. **Pads 20–24 dim violet** (combine) | OK |
| 4c | Look at row 4 | **Pads 25–27 dim cyan** (thinning). Pad 28 dark. Pad 29 dim white. Pads 30, 31, 32 dark | OK |
| 4d | Look at ▼ and ▲ | ▼ yellow, ▲ orange | OK |
| 5 | Hold Shift, tap pad 28 | Pad 28 bright yellow, 27 dim orange. Release Shift: **Melody**, as in PL13. ▼ yellow, ▲ orange | OK |
| 6 | Hold Shift, tap pad 28 again | Release Shift: **Phrasing**. Pads 1–3 dim cyan (ties). Pad 4 dark. Pads 5–7 dim magenta (octave jumps). Pads 8–28 dark. 29 dim white. 30, 31, 32 dark. ▼ magenta, ▲ yellow | OK |
| 7 | Hold Shift, tap pad 25. Release Shift | Chords again | OK |
| 8 | Press ▼ | Arp. ▼ orange, ▲ green | OK |
| 9 | Press ▼ | Pattern tools (row 4 left: four cyan pads). ▼ orange, ▲ blue | OK |
| 10 | Press ▼ | Pattern tools 2 (row 3 right: five violet pads). ▼ yellow, ▲ orange | OK |
| 11 | Press ▼ | Melody (row 1 yellow). ▼ yellow, ▲ orange | OK |
| 12 | Press ▼ | Phrasing (pads 1–3 cyan, 5–7 magenta, rows 2–3 dark). ▼ magenta, ▲ yellow | OK |
| 13 | Press ▼ | Keys. ▼ dark, ▲ yellow | OK |
| 13b | Press ▼ once more | Nothing changes (no page after Keys; no octave change either) | OK |
| 14 | Press ▲ six times, looking after each press | Each press goes back one page: Phrasing, Melody, Pattern tools 2, Pattern tools, Arp, Chords. Each page's ▲ ▼ colours are the same as on the way down | OK |
| 15 | Hold Shift, tap 28 | Release Shift: Melody (the ▲ walk left Melody on its first page) | OK |
| 15b | Hold Shift, tap 28 again | Release Shift: Phrasing | OK |
| 15c | Hold Shift, tap 27 | Release Shift: Pattern tools (its first page: the ▲ walk left it there) | OK |
| 15d | Hold Shift, tap 28 | Release Shift: **Phrasing**, not Melody (the page of Melody used last) | OK |
| 16 | Press Note (the pages close). Shift + Synth 1 | Phrasing opens: the track opens on the page it used last | OK |

### B. The tools by ear (Synth 1; press Play now and leave the loop playing)
| # | Do | Expect | Result |
|---|---|---|---|
| 17 | **A second rhythm with no first hits** (a new project has none). Hold Shift, tap 27 twice (Pattern tools 2). Press pad 5 | Pads 1, 5, 8, 11, 14 bright white (5 hits): `x... x..x ..x. .x..`. Pad 32 stays **dark**: with combine off nothing can be written. Silence | OK |
| 17b | Press pad 21 (combine: either) | Pad 21 bright violet. **Pad 32 turns dim orange**: now there is something to write | OK |
| 17c | Press pad 32 | Pad 32 blinks (armed). Still silence | OK |
| 17d | Press pad 32 again | When you lift your finger the loop plays 5 Cs: `x... x..x ..x. .x..` | OK |
| 17d2 | Look at pads 31 and 32 | Pad 32 bright orange, steady: a **draft** (combine is a new setting). Pad 31 blue (Undo) | OK |
| 17e | Press ▲ (Pattern tools) | Pads 1, 5, 8, 11, 14 bright orange: the preview shows what Write wrote. Press ▼ back | OK |
| 17f | Press pad 20 (combine: both) | Pad 20 bright violet, 21 dim. Pad 32 turns **dark**: nothing is in both. The loop **keeps playing** the 5 Cs (nothing is written) | OK |
| 17g | Press pad 21 (either) | Pad 32 bright orange again. The loop is the same 5 Cs | OK |
| 18 | **Each combine.** Press ▲ (Pattern tools), then pad 4 (4 hits) | When you lift pad 4 the loop changes to "either": `x... x..x x.x. xx..` (7 notes) | OK |
| 18a | Press ▼ (back to Pattern tools 2) | Nothing changes in the loop | OK |
| 18b | Press pad 20 (both) | When you lift your finger: `x... x... .... ....` (2 notes) | OK |
| 18c | Press pad 22 (one, not both) | `.... ...x x.x. xx..` (5 notes; nothing on the first beat) | OK |
| 18d | Press pad 23 (first without second) | `.... .... x... x...` (2 notes) | OK |
| 18e | Press pad 24 (accent) | `X... X... x... x...`: the four on the beat, the first two louder | OK |
| 18f | Press ▲ (Pattern tools) | Pads 1, 5, 9 and 13 bright orange: accent keeps the first rhythm. Press ▼ back | OK |
| 18g | Press pad 24 again | Pad 24 dim: combine off. `x... x... x... x...`, all the same loudness | OK |
| 19 | **Cycle.** Press ▲ (Pattern tools), pad 3 (3 hits) | When you lift your finger: `x... ..x. ...x ....` | OK |
| 19b | Press pad 26 (cycle 5) | Pad 26 bright cyan. The loop: `x.x. xx.x .xx. x.xx`: a 3-note group (`x.x.x`) every 5 steps, drifting against the beat. The preview shows the same | OK |
| 19c | Press pad 26 again | Pad 26 dim: cycle off. Back to `x... ..x. ...x ....` | OK |
| 20 | **Thinning, re-rolled.** Press pad 16 (16 hits) | A note on every step | OK |
| 20b | Press ▼ (Pattern tools 2), pad 27 (thinning: 1 in 2) | Pad 27 bright cyan. Each of the 15 notes after the first may go, about 1 in 2; the first always plays. So most often 6 to 11 notes are left. Emulation gave 11: `xxx. xx.x .xxx .x.x` | OK |
| 20c | Press pad 29 (dice rhythm) | Other notes go; the first step still plays. Emulation gave 10: `xxxx x.x. .xx. xx..` | OK |
| 20d | Press pad 29 again | Another set, the first step playing. Emulation gave 8: `xx.x ..xx .xx. ..x.` | OK |
| 20e | Press pad 29 again | Another set, the first step playing. Emulation gave 7: `xx.x x.x. x.x. ....` | OK |
| 20f | Press pad 27 again | Pad 27 dim: thinning off. A note on every step again | OK |
| 21 | **Ties.** Press ▲ (Pattern tools): pad 8 (8 hits), then pad 19 (rotation back to the start: the dice turned it) | `x.x. x.x. x.x. x.x.`, all C, short notes with a gap after each | OK |
| 21b | Press ▼ ▼ (Melody), pad 2 (order up) | The line: C E G C E G C E, one note per hit, with gaps | OK |
| 21c | Press ▼ (Phrasing), pad 3 (ties: 1 in 2) | Pad 3 bright cyan. When you lift your finger: C, E, then **one long G** from step 5 to step 11 (no new attack on steps 7, 9 and 11, no gaps), then C, E | OK |
| 21c2 | Listen to the note after the long G | It is C: the line does not skip ahead over the tied hits (C E G, then C E as the line goes on) | OK |
| 21d | **The ties in stock's Micro Step view.** Press Gate twice (stock's Micro Step view; the pages close). Hold the pad of step 5 (row 1) | Stock's Tie pad is lit (pad 24 in that view, from upstream's notes). The same on steps 7 and 9 | OK |
| 21e | Hold step 11, then step 3 | Tie is not lit on either (step 11 ends the held G, step 3 is a plain note) | OK |
| 21f | Shift + Synth 1 | Phrasing opens (the page used last). Pad 32 **dim orange**: closing the pages ended the draft. Pad 31 blue | OK |
| 21g | Press pad 32 twice | When you lift your finger the second time: written again (the same line). Pad 32 bright orange: a new draft | OK |
| 22 | **Octave jumps.** Press pad 7 (jumps: 1 in 2) | Pad 7 bright magenta | OK |
| 22a | Listen | Some notes jump an octave (up; down only when up is out of the Circuit's range, which these notes are not): C, E, the long G an octave up, C an octave up, E | OK |
| 22b | Press pad 3 (ties off) | Pad 3 dim. 8 short notes again, some an octave up: C E G' C' E' G C' E (`'` = an octave up). The first note never jumps | OK |
| 22c | Press pad 30 (dice notes) | Another set of notes jumps; the line under it is still C E G C E G C E | OK |
| 23 | **Fix 2: a press that changes nothing keeps a held pick.** Press ▲ (Melody). **Hold pad 3** (order down). While you hold it, press ▼ (Phrasing opens). Then lift pad 3 | When you lift pad 3 the line goes **down** (G E C G E C G E, some an octave up). Pad 32 stays bright orange. In PL13 the line stayed as it was until the next press | OK |
| 23b | Press ▲ (Melody) | Pad 3 bright yellow (order down) | OK |

### C. Save, power cycle, reload
| # | Do | Expect | Result |
|---|---|---|---|
| 24 | **Settings to save.** Synth 1: ▼ (Phrasing), pad 1 (ties 1 in 4; jumps stay 1 in 2). ▲ (Melody): pad 2 (up) | Each pad lights as you press it, and each lift re-writes the loop (still the draft) | OK |
| 24b | ▲ (Pattern tools 2): pad 24 (accent), pad 26 (thinning 1 in 3) | Pad 24 bright violet, pad 26 bright cyan, on rows 3 and 4. **Note in the Results whether the two colours are easy to tell apart** | OK: Colors easy to tell apart |
| 24c | ▲ (Pattern tools): pad 28 (cycle 7) | Pad 28 bright cyan (on Pattern tools) | OK |
| 24c2 | Press ▼ ▼ ▼ (Pattern tools 2, Melody, Phrasing) | Phrasing is open. Pad 28 is dark here: Phrasing does not use it | OK |
| 24d | Press Note. In the Note view play **E** once (Synth 1's last played pad). Stop the sequencer | Nothing is written by this | OK |
| 24e | **Synth 2** (and fix 1's setting): Shift + Synth 2 (Chords). Press pad 24 (bass) twice | Pad 24 white: rootless over bass | OK |
| 24f | Hold Shift, tap 27 twice (Pattern tools 2). Press pad 3 | Pads 1, 7 and 12 bright white (3 hits) | OK |
| 25 | Stop the sequencer. Save the project: press Save (it flashes), then Save again (stock saves it in its own slot) | It saves as stock does | OK |
| 25b | Power off and on. Load the project: in the Projects view, tap its slot (the one from Before you start, step 4) | It loads as stock does | OK: Last project (the one I created for testing) is opened on power on |
| 26 | Shift + Synth 1 | **Phrasing** opens (saved). Pad 1 bright cyan, pad 7 bright magenta, pads 2–3 and 5–6 dim | OK |
| 26a | Look at pads 31 and 32 | Pad 32 dim orange (no draft after a load). Pad 31 dark (Undo is not saved) | OK |
| 26b | Press ▲ | Melody: pad 2 bright yellow (up) | OK |
| 26b2 | Look at pad 17 | Bright white: the root is "last pad" | OK |
| 26c | Press ▲ | Pattern tools 2: pads 1, 5, 8, 11, 14 bright white (5 hits), pad 24 bright violet, pad 26 bright cyan | OK |
| 26d | Press ▲ | Pattern tools: pad 28 bright cyan (cycle 7) | OK |
| 26e | Press Play | The loop plays as it did before the save | OK |
| 26f | Press pad 32 twice | When you lift your finger: the first note (step 1, loud) is **E**: the last played pad came back with the project (PL13 would play C here) | OK |
| 27 | Press Note. Shift + Synth 2 | **Pattern tools 2** opens with pads 1, 7, 12 bright white | OK |
| 27b | Press ▲ ▲ ▲ (Chords) | Pad 24 white: rootless over bass is kept at load (fix 1 clears it only without a bass) | OK |
| 28 | Stop the sequencer. Save the project again: Save, then Save again (its own slot) | It saves as stock does (sections D and E use this project) | OK |

### D. The PL14 project on PL13 (flash PL13, then PL14 again)
| # | Do | Expect | Result |
|---|---|---|---|
| 29 | Flash PL13 (`slim/build/PL13/circuittracks-4486-PL13.syx`). Load the project from step 28 | It loads | OK |
| 29b | Shift + Synth 1 | **Melody** opens (PL13 has no Phrasing): pad 2 bright yellow (up). The Melody settings are as saved | OK |
| 29c | Press ▲ (Pattern tools) | PL13's own page: pads 25–28 dark (PL13 has no cycle). Pads 1, 3, 5 … 15 bright orange (its 8 hits, plain Euclid). Gate and velocity as before | OK |
| 29d | Press Play | The loop plays exactly as on PL14 in step 26f (it is stock's steps, ties included) | OK |
| 29e | Shift + Synth 2 | Pattern tools opens (PL13's only Pattern tools page). On Chords (▲ ▲) pad 24 is white | OK |
| 30 | **A re-save on PL13.** Save the project to another, empty slot (save to another slot) | Saves as stock does | OK |
| 31 | Flash PL14 again (`circuittracks-4486-PL14.syx`). Load the copy from step 30 | It loads | OK |
| 31b | Shift + Synth 1 | **Pattern tools** opens (its first page): PL13 saves the page it is on, and step 29c left Synth 1 there. Hold Shift, tap 28: Melody, pad 2 bright yellow (up: PL13 kept the Melody settings) | OK: I might've changed the page before flashing so PL13 opened up pattern page 1, but melody page has right pad selected. |
| 31c | Press ▼ (Phrasing) | Pads 1–3 and 5–7 all dim: PL13's save dropped the ties and jumps, as the user guide says | OK |
| 31d | Press ▲ ▲ (Pattern tools 2) | Pads 1–16 dim white (no second rhythm), 20–24 dim violet, 25–27 dim cyan. ▲ (Pattern tools): pads 25–28 dim cyan | OK |
| 31e | Press pad 32 twice | When you lift your finger: the first note is the default **C**, not E (the last played pad was dropped too) | OK-ish? Something happened to the melody, but first sequencer step shows E. I might've tapped something by accident though. |
| 32 | Load the project from step 28 (the original) | Its pages as in steps 26–26d and 27–27b: nothing was lost by loading it on PL13 | OK |

### E. CTCtrl and the link (PL14 installed, the project from step 28 loaded)
| # | Do | Expect | Result |
|---|---|---|---|
| 33 | Open CTCtrl, connect | The CTPlay panel appears. It does not show the new settings (CTCtrl learns them later). No error | OK |
| 33b | **Fix 1's side you can reach.** On the Circuit open Synth 2's Chords page. In CTCtrl select Synth 2, Chord tab: change the shape | The shape changes on the Chords page at once. Pad 24 stays white (rootless over bass) | OK |
| 33c | Synth 1, Euclid tab: change the hit count | The hit count changes on the device. Pattern tools 2 and Phrasing keep their settings | OK |
| 34 | Close CTCtrl. Open `slim/pages/ctplay_link.html`, connect | "Connected: PL14, protocol 1, layout 1, **77 B, 11 fields**." | OK |
| 34b | Read | The table has two new rows: `offset 53 (rev 1)` with 12 bytes (the rhythm settings) and `offset 65 (rev 1)` with 4 bytes (ties and jumps). For this project: `A5 40 04 03 00 00 …` and `0D 00 00 00` | OK |
| 34c | Shift + Synth 1 (Phrasing). On the page: Write offset 65, bytes `03` | One `state` line. At once: Phrasing pad 3 bright cyan (ties 1 in 2), pads 5–7 all dim (jumps off) | OK |
| 34d | **Fix 1: the state it guards cannot be made.** Write offset 4, bytes `03` (rootless on Synth 1, which has no bass; Synth 2's bit as it is) | One `state` line, unchanged: the write is refused, as every control refuses it. A project holding it comes only from a damaged or hand-edited file; emulation covers that case (`tests/test_link.py`, `test_a_load_clears_what_the_pads_never_set_so_phone_writes_go_through`) | OK |

### F. A stock bug to check (not a PL14 feature; upstream fixed it in RC2.06)
Two pads that play the same note, held together, may leave that note sounding: stock sends two note-ons and one
note-off. PL14 does not change this. The steps only check whether CTPlay has it too, so a fix can go into the next
build.

| # | Do | Expect | Result |
|---|---|---|---|
| 35 | Make a new empty project (as Before you start, step 4). Open Synth 1's Note view; no CTPlay page open, sequencer stopped | The Note view, as stock | OK |
| 35b | Find two pads that play the same note: play pads one at a time and listen (on a keyboard-style layout the last pad of a row and the first of another often share one) | Two pads, the same pitch. Write down which | First pad or row 1 (17) and last one of row 2 (32) |
| 35c | Hold the first pad, then hold the second as well. Release the first, then the second | **Stock's bug:** the note keeps sounding after both are released, until you play that note again. **No bug:** it stops when you release the second. Note which | No bug |
| 35d | The same, but release the second pad first | As step 35c. Note which | No bug |
| 35e | Shift + Synth 1, Chords page: pick a chord shape (e.g. a triad). Back in the Note view, repeat step 35c | Note whether any note keeps sounding (CTPlay plays the chord; the pads' own note is still stock's) | No stuck notes, chords play and stop as expected |

## Results
2026-10-22–23, PL14 (`0d58e24b…`): **passed.** Every step OK.
- **Stuck note with two pads of the same pitch (steps 35c–35e):** none. Pads 17 and 32 (one pitch on the keyboard
  layout), released in either order, and with a chord shape: every note stopped. Stock's bug (upstream RC2.06) did not
  show on this device and layout.
- **Violet against cyan (steps 4, 24b):** easy to tell apart.
- **Anything odd on the device:** nothing in the firmware; two steps of the plan.
  - Step 31b expected Melody, but PL13 keeps the page in its re-save (`page_slot` is in its 53 B): the copy opened on
    Pattern tools, where step 29c left Synth 1. The step now says so.
  - Step 31e gave E, not C, twice on the same copy. A clean re-run on 2026-10-23 settled it: a new project with E as
    the last played pad, saved on PL14 (slot A), re-saved on PL13 (slot B), then on PL14 three hits written from each:
    three Cs from slot B, three Es from slot A. So the late-night E came from a stray press.
