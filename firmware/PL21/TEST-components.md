# PL21 — Components compatibility test (beta)

**The marker:** PL21 is the beta-prep build's working name. The beta's real marker is not chosen yet: this folder and
every "PL21" below get renamed with it.

**What it is:** the beta's promise is that every stock function stays intact with CTPlay installed, **Novation
Components** included. Two Components round trips have passed so far: PL10 (a project with the old block 1 only) and
PL20 (trig conditions in the patterns). Since then CTPlay keeps data in more places that Components' project
validator might check:
- **The saved settings:** from this build on, **one block at the session record's tail + 0** ("saved format 2", up to
  1000 B; spec `slim/docs/specs/2026-11-10-saved-format-2-design.md`). In emulation, Components' own validator never
  reads the tail (`slim/tests/test_components_validator.py`, `slim/docs/investigations/2026-11-11-components-validator.md`).
- **Written patterns:** rolls in microsteps (a drum roll, a pattern strum Written roll), a step with six notes, a note
  held past 16 steps (stock's tie), Melody's ties.
- **Trig conditions:** note steps' bytes [2]–[3], drum pattern settings `+0x84` / `+0x88`.

The same test runs Components' validator on records CTPlay saves in emulation: stock, PL21 with every setting set,
PL21 defaults, a Euclid Write, a drum Write with a roll, a step-entry chord and trig conditions are **all valid**. So
where this plan expects Components to accept a project, a refusal is a surprise: report it at once. The device run is
still needed: it checks Components itself, the transfers and the packs, which emulation cannot.

This plan builds one "full" project with all of these, sends it through Components (projects, a backup, a pack), goes
back to the official firmware and returns, and loads stock-made projects on CTPlay. The full feature test is
`TEST.md` in this folder: this plan checks the features only as far as a Components step needs.

**Components:** this plan names its actions in general words ("download the project to the computer"), not its button
names. Use whatever Components calls them. If Components cannot do an action at all, write that down and go on.

**Rows that say "Write down":** nobody knows the answer yet. Write what you see or hear in Result.

> **If anything goes wrong** (a hang, the Circuit does not start, a firmware install fails): hold **Scales + Preset +
> Note** while you power on (the bootloader), then send the official firmware with the uploader
> (`stock/circuittracks-firmware-4486-STOCK.syx`) or with Components. Your projects, patches and samples stay on the
> SD card. Then restore your backup (Before you start, step 1) if a project was damaged.

**Time:** about **2 h 30 min** in all (an estimate: 107 rows at about 30 s each is 55 min; many rows here hold several
presses or a listen, and Components' transfers, two firmware installs and the backups add about 40 min). Three
sittings:
- **First sitting, about 1 hour:** Before you start (15 min), A. The full project (45 min). Nothing to keep open at
  the break: P1 is saved.
- **Second sitting, about 50 minutes:** B. Connecting (8 min), C. Projects (22 min), D. Packs (10 min), E. Patches and
  samples (8 min).
- **Third sitting, about 40 minutes:** F. Back to stock (20 min), G. The beta again (12 min), H. Stock's projects on
  CTPlay (8 min).
- Each section says how it starts.

## Before you start
0. **PL21 installed.** `TEST.md` in this folder builds and flashes it ("Before you start"). If it is not installed:
   `cd slim && ../.venv/bin/python -m slimbuild versions/PL21.toml`. The printed syx sha256 must equal `syx_sha256`
   in `slim/firmware/PL21/manifest.json`. Then `../.venv/bin/python -m slimbuild.uploader`, open
   `slim/build/ct_uploader.html` and send `slim/build/PL21/circuittracks-4486-PL21.syx` (the uploader must list it as
   PL21: it knows a file by that sha256). Close the uploader's tab after it.
1. **Back up everything.** This test saves over projects, sends packs and installs firmware twice.
   - In Components: back up every project (all 64), your patches and your samples to the computer.
   - The SD card: power off, take the card out, copy all its files to the computer, put it back.
2. **A pack you can lose** (the "test pack"). Load it on the Circuit (stock's Packs view). Pick **four empty slots** in
   it and write down their numbers:
   - **P1**: the full project (section A);
   - **P2**: its copy through Components (section C);
   - **P3**: the full project re-saved on the official firmware (section F);
   - **P4**: a project made on the official firmware (section F).
3. **One MIDI program at a time.** Components (in Chrome), the link page and the uploader all need the Circuit's MIDI
   port. **Chrome keeps a tab's port until you close the tab** (a refresh is not enough). Before you open one of them,
   close the tabs of the others, and CTCtrl's tab. The rows say when.
4. **Synth 1's and Synth 2's Note view** with the steps on rows 1–2 and the keys on rows 3–4 (if all four rows play
   notes, press Note until rows 1–2 show the steps). Your keyboard layout: **the C pad is pad 25**, the C at the left
   end of the bottom row; then **D pad 26, E pad 27, F pad 28, G pad 29, A pad 30, B pad 31, C pad 32**.
5. **Views used** (stock's):
   - **The Patterns view** (Patterns): a column per track, Synth 1 on the left. **Pad 1 = Synth 1's pattern 1, pad 9 =
     its pattern 2; pad 2 = Synth 2's pattern 1, pad 10 = its pattern 2.** Stopped, a tap picks the pattern at once.
   - **Pattern Settings:** a pattern's start and end step.
   - **The probability view** (Shift + Pattern Settings, from a track's Note view or step view): rows 1–2 are the
     steps, a tap **selects** a step. Row 4 is CTPlay's trig conditions of the selected step.
   - **Drum N's step view:** press Drum N. A tap on a step pad adds a hit or takes it out.
6. **Tempo:** a new project is at **120 BPM**. A 16-step pattern is **one bar, 2 seconds**. Step 5 is beat 2, step 9
   beat 3, step 13 beat 4.
7. **How to press:** "Shift + X" = hold Shift, press X, let go of both. On a Play page, "hold Shift, tap pad N" uses
   the page list (row 4). "Hold a pad about a second" = keep it down a full second, then let go.
8. **An arpeggio that keeps going** (from row 34 on, the synth and MIDI tracks get the arpeggiator on with Latch:
   Synth 1 in row 34, the others in rows 40–42): if you play a key pad by mistake, it latches. Stop it: Shift + the
   track's button, hold Shift, tap pad 26 (Arp), press pad 16 twice (Latch off stops it, then on again). Write the
   row number in Results.

## Steps

### A. The full project
Start: **PL21 installed, the test pack loaded.** Sequencer stopped. Rows 1–31 write the patterns; rows 32–47 set every
CTPlay setting off its default on every track; rows 48–50 save it and keep a reference.

| # | Do | Expect | Result |
|---|---|---|---|
| 1 | In the Projects view, tap the empty slot **P1** (a new empty project). Set the scale to **major on C** (Scales). Give Synth 1 and Synth 2 each a **Poly** patch with a clear, **sustained** sound (an organ or a soft pad; Preset view) | A new empty project: every CTPlay setting off | |
| 2 | Press Shift + Clear until Clear shows **cyan** while Shift is held | Clear cyan with Shift: **count-in and click**. The count-in is saved with the project; the click helps you count | |
| 3 | **Synth 1, pattern 2: a note held past 16 steps.** Press Patterns, tap pad 9 (Synth 1's pattern 2). In stock's Pattern Settings, set it to end at step 32 (start at step 1). Press Synth 1 (its Note view) | Synth 1 on pattern 2, 32 steps long: the step pads show steps 1–16 | |
| 4 | Press Record, then Play: one bar of count-in clicks. On the first beat after it (step 1), press and hold the **C pad**. Let go on step 21 (beat 2 of the second bar). Press Record (recording off). Let the loop play once | **One long C of about 20 steps, with no new attack 16 steps after it starts.** Silence after it until the loop starts again. (If the C starts a little after step 1, the quantise moved it: that is fine) | |
| 5 | Stop. Press Patterns, tap pad 1 (Synth 1's pattern 1) | Synth 1 on pattern 1: empty, 16 steps | |
| 6 | **Synth 1, pattern 1: Euclid and a pass condition.** Shift + Synth 1 (the Chords page). Press pad 2 (triad). Press Synth 1 (the page closes). Play the **G pad** once | Pad 2 turned bright green. You hear **G B D** | |
| 7 | Shift + Synth 1 (Chords, used last). Hold Shift, tap pad 27 (Pattern tools), let go of Shift. Press pad 4 (4 hits). Press pad 21 three times | **Pads 1, 5, 9 and 13 bright orange** (the preview). **Pad 21 white** ("to the next hit"). Pad 32 dim orange | |
| 8 | Press pad 32, then pad 32 again, and let go | The pattern is written when you let go. **Pad 32 bright orange, steady**: a draft ("to the next hit" is a new setting) | |
| 9 | Press Synth 1 (the page closes; the draft ends). Press Play. Listen for 2 bars. Stop | **G B D on beats 1, 2, 3 and 4**, each held until the next one (legato) | |
| 10 | Shift + Pattern Settings. Tap step pad 5. **Hold** pad 26 about a second, let go. Tap pad 26. Tap pad 25 | Row 4: **pad 25 dim cyan, pad 26 bright cyan**, pads 27–32 dark: step 5 plays on pass 2 of 2 | |
| 11 | Press Synth 1. Press Play. Listen for 4 bars. Stop | **Bars 1 and 3: chords on beats 1, 3 and 4, silence on beat 2. Bars 2 and 4: all four beats** | |
| 12 | **Synth 2, pattern 1: Melody with ties.** Press Synth 2 (its Note view). Shift + Synth 2 (the Chords page). Hold Shift, tap pad 27 (Pattern tools), let go. Press pad 8 (8 hits) | **Pads 1, 3, 5, 7, 9, 11, 13 and 15 bright orange** | |
| 13 | Hold Shift, tap pad 28 (Melody), let go. Press pad 2 (up), pad 10 (scale), pad 12 (2 octaves), pad 14 **once** (accent: first hit), pad 18 (degree 1), pad 26 (octave −1) | Pad 2 bright yellow. Pad 10 bright green. Pad 12 bright magenta. Pad 14 bright yellow. Pad 18 bright blue, pad 17 dim white. Pad 26 bright magenta | |
| 14 | Press ▼ (Phrasing). Press pad 2 (ties 1 in 3), pad 5 (jumps 1 in 4) | Pad 2 bright cyan. Pad 5 bright magenta | |
| 15 | Press pad 32, then pad 32 again, and let go | Written when you let go. **Pad 32 bright orange, steady** (a draft) | |
| 16 | Press Synth 2 (the page closes; the draft ends). Press Play. Listen for 2 bars. Stop. Look at the step pads (rows 1–2) | A line that rises from a low C through the C major scale, on every other step: some notes held over the next hit (ties), some an octave higher (jumps), the first note louder. **Write down which step pads are lit** and how the line sounds (for sections C and F) | |
| 17 | **Synth 2, pattern 2: six notes in one step.** Press Patterns, tap pad 10 (Synth 2's pattern 2). Press Synth 2. Shift + Synth 2 (Phrasing, used last). Hold Shift, tap pad 32 (Keys), let go. Press pad 2 (chords in step entry) | Pad 2 bright green | |
| 18 | Hold Shift, tap pad 25 (Chords), let go. Press pad 4 (9th). Press Synth 2 (the page closes) | Pad 4 turned bright green before the page closed | |
| 19 | Hold step pad 1. Press the C pad and let go of it. Press the **F pad** and let go of it. Let go of step pad 1 | Notes sound while you hold the step (the synth may not hold them all). The C put in C E G B D; the F adds F: **six notes**, the most a step holds | |
| 20 | Hold step pad 1 again and look at the key pads. Let go | **The C, E, F, G and B pads light up** (pads 25, 27, 28, 29, 31). The D is above pad 32's C, so no pad shows it | |
| 21 | **A Written roll.** Shift + Synth 2 (Chords, used last). Press pad 2 (triad), pad 28 (slow). Hold Shift, tap pad 32 (Keys), let go. Press pad 4 (written) | Keys: pad 2 bright green, **pad 4 bright white**, pad 3 dim white | |
| 22 | Press Synth 2. Hold step pad 9. Press the C pad and let go of it. Let go of step pad 9 | While you hold step 9: **C and E** (the notes the roll puts in step 9). The G goes into step 10 when you let go of the C pad | |
| 23 | Hold step pad 10. Let go | **G alone**, a moment after the hold (step 10, microstep 2): the roll | |
| 24 | Press Patterns, tap pad 2 (Synth 2's pattern 1) | Synth 2 back on pattern 1 | |
| 25 | **Drum 1: a roll and FIRST.** Shift + Drum 1 (its Repeat page). Hold Shift, tap pad 27 (Pattern tools), let go. Press pad 4 (4 hits). Press pad 21 **once** (2 hits a step) | Pads 1, 5, 9 and 13 bright orange. **Pad 21 in stock's Gate-view colour for 3/6** (2 hits a step; before the press: the 1/6 colour). Pad 32 dim orange | |
| 26 | Press pad 32, then pad 32 again, and let go. Press Drum 1 (the page closes) | **Step pads 1, 5, 9 and 13 lit** | |
| 27 | Shift + Pattern Settings. Tap step pad 9. Hold Shift, tap pad 25 (FIRST) and look. Let go of Shift | With Shift held: **pad 25 bright green**, the other specials dim. Without Shift: all 8 pads dim green | |
| 28 | **Drum 2: a cycle of 8.** Shift + Drum 2 (its Repeat page). Hold Shift, tap pad 27 (Pattern tools), let go. Press pad 2 (2 hits). Press pad 18 (later) four times | **Pads 5 and 13 bright orange** (beats 2 and 4) | |
| 29 | Press pad 32, then pad 32 again, and let go. Press Drum 2 (the page closes) | **Step pads 5 and 13 lit** | |
| 30 | Shift + Pattern Settings. Tap step pad 13. **Hold** pad 32 about a second, let go | Row 4: **pad 25 bright cyan, pads 26–32 dim cyan**: step 13 plays on pass 1 of 8 | |
| 31 | Press Play. Listen for 3 bars. Stop | Synth 1 as row 11 (no beat 2 in bars 1 and 3). Synth 2 its line. **Drum 1:** a double hit on every beat in bar 1; in bars 2 and 3 **no hit on beat 3**. **Drum 2:** beats 2 and 4 in bar 1; in bars 2 and 3 **only beat 2** | |
| 32 | **Settings, Synth 1.** Press Synth 1 (its Note view). Play one key pad that is **not a C** (the D pad). Hold Shift, press 1-16/17-32, keep Shift held and look. Let go of Shift | With Shift held: **1-16/17-32 lit blue** (the Quick view is Arp now). Pads 17–32 show the Arp page's rows 1–2 | |
| 33 | Shift + Synth 1 (Pattern tools, used last). Hold Shift, tap pad 25 (Chords), let go. Press pad 3 (7th), pad 18 (1st inversion), pad 22 (drop-2), pad 24 **twice** (rootless over bass), pad 26 (top line), pad 30 (fast), pad 32 (falling) | Pad 3 bright green. **Pad 18 dim blue, pads 17, 19 and 20 dark** (voice leading on). Pad 22 bright magenta. **Pad 24 white.** Pad 26 bright blue. Pad 30 bright white. Pad 32 bright white, pad 31 dim white | |
| 34 | Press ▼ (Arp). Press pad 2 (up), pad 10 (1/8), pad 13 (triplet), pad 16 (latch), pad 18 (2 octaves), pad 21 **once** (gate 2/6). **From now on, do not play this track's key pads** (Before you start, step 8). Row 32's D pad on the next tracks is fine: their arpeggiator is still off then | Pad 2 bright green. Pad 10 bright blue. Pad 13 bright magenta. Pad 16 bright orange. Pad 18 bright magenta. **Pad 21 in stock's Gate-view colour for 2/6** (before the press: the 3/6 colour) | |
| 35 | Press ▼ (Pattern tools). Press pad 5 (5 hits), pad 18 (later) once, pad 20 (groove), pad 22 (soft), pad 26 (cycle 5), pad 29 (dice rhythm) once. Leave pad 21 white (row 7). **Do not press pad 32** | Pad 20 bright white. Pad 21 white. Pad 22 bright magenta. Pad 26 bright cyan. **Pad 32 dim orange, steady:** nothing is written | |
| 36 | Press ▼ (Pattern tools 2). Press pad 3 (3 hits), pad 18 (later) once, pad 21 (either), pad 25 (thinning 1 in 4) | Pads 1–16: the second rhythm in white. Pad 21 bright violet. Pad 25 bright cyan | |
| 37 | Press ▼ (Melody). Press pad 2 (up), pad 10 (scale), pad 12 (2 octaves), pad 14 **once** (first hit), pad 18 (degree 1), pad 26 (octave −1), pad 30 (dice notes) once | As row 13: pad 2 bright yellow, pad 10 bright green, pad 12 bright magenta, pad 14 bright yellow, pad 18 bright blue, pad 26 bright magenta | |
| 38 | Press ▼ (Phrasing). Press pad 2 (ties 1 in 3), pad 5 (jumps 1 in 4) | Pad 2 bright cyan. Pad 5 bright magenta | |
| 39 | Press ▼ (Keys). Press pad 1 (mono), pad 2 (chords in step entry), pad 3 (played). Press Synth 1 (the page closes) | Before you close: pad 1 bright magenta, pad 2 bright green, **pad 3 bright white**, pad 4 dim white | |
| 40 | **Synth 2:** do rows 32–39 on Synth 2 (Synth 2's button instead of Synth 1's; Shift + Synth 2 opens Keys, used last, and the page list works the same), with three changes. Row 35: press pad 21 **three times** (until white). Rows 37–38: Melody and Phrasing are set already (rows 13–14): press **only pad 30** (dice notes) once, and check the rest. Row 39: pads 2 and 4 are on already (rows 17 and 21): press **only pad 1** | Every page as on Synth 1, except Keys: **pad 4 bright white** (written), pad 3 dim white | |
| 41 | **MIDI 1:** do rows 32–39 on MIDI 1 (MIDI 1's button; Shift + MIDI 1 opens Chords, a new track's page). Row 35: press pad 21 **three times**. You hear nothing on a MIDI track unless gear is connected | Every page as on Synth 1 (Keys: pad 3 bright white) | |
| 42 | **MIDI 2:** as row 41 on MIDI 2, but on Keys press **pad 4** (written) instead of pad 3 | Every page as on Synth 1, except Keys: **pad 4 bright white**, pad 3 dim white | |
| 43 | **Drums: the Repeat page** (one setting for the kit). Shift + Drum 1 (Pattern tools, used last). Hold Shift, tap pad 26 (Repeat), let go. Press pad 7 (1/16T), pad 11 (swell), pad 15 (unquantized repeats), pad 16 (latch). **Do not tap pads 29–32:** with latch on, a tap starts a repeat that keeps going (a second tap stops it) | Pad 7 bright magenta. Pad 11 bright white. Pad 15 bright cyan. Pad 16 bright orange | |
| 44 | Press ▼ (Pattern tools). Press pad 3 (3 hits), pad 18 (later) once, pad 20 (groove), pad 24 (hard), pad 28 (cycle 7), pad 29 (dice rhythm) once. Leave pad 21 as row 25 set it (2 hits). **Do not press pad 32** | Pad 20 bright white. Pad 21 in the 3/6 colour. Pad 24 bright magenta. Pad 28 bright cyan. Pad 30 dark. **Pad 32 dim orange, steady** | |
| 45 | Press ▼ (Pattern tools 2). Press pad 2 (2 hits), pad 18 (later) once, pad 24 (accent), pad 27 (thinning 1 in 2), pad 28 **once** (accent: first hit) | Pad 24 bright violet. Pad 27 bright cyan. Pad 28 bright yellow | |
| 46 | **Drums 2, 3 and 4:** for each, Shift + Drum N, then press ▼ or ▲ until **Pattern tools** is open (Drum 2 opens on it; Drums 3 and 4 open on Repeat: press ▼ once). Do row 44 on it, and there press pad 21 **once** too (2 hits a step). Then press ▼ and do row 45. Then press Drum 1 (the page closes) | On both pages, **pads 17–32 as Drum 1's** (pad 21 in the 3/6 colour). Pads 1–16 (the previews) may differ from Drum 1's: Drum 2's rotation started from row 28's | |
| 47 | Press Play. Listen for 3 bars. Stop | As row 31, but **Synth 1's chords are strummed now** (fast, from the top note down: D B G), Played. No setting changed a pattern | |
| 48 | Save the project (Save, then Save again) | It saves as stock does, to P1 | |
| 49 | **The reference.** Close every MIDI tab. Open `slim/pages/ctplay_link.html` from the beta checkout in Chrome. Press Allow MIDI access | "Connected: **PL21, protocol 2, layout 1, 118 B, 18 fields**." | |
| 50 | Press Read. Keep the tab open until you have copied the table | The table fills: 18 rows. Among them: **mono `0F`, strum `FF`, strum falling `0F`, rootless `0F`, count-in `01`, chord voice `20 20 20 20`, drum accent `01 01 01 01`, step chords `0F`, pattern strum `99`**. **Copy the table** (select it, paste it into a text file) or take a photo: sections C and G compare with it. Then close the tab | |

### B. Connecting
Start: **P1 loaded**, as saved. Sequencer stopped. Every MIDI tab closed.

| # | Do | Expect | Result |
|---|---|---|---|
| 51 | Open Novation Components in Chrome and connect the Circuit Tracks | Components finds the device, as on the official firmware. **Write down what it shows about the firmware** (a version number, an offer to update). CTPlay leaves stock's answer to the device's identity question unchanged (the same on every build), so it probably shows 1.2.1, as for the official firmware | |
| 52 | Close Components' tab. Open the link page, press Allow MIDI access. When it says "Connected: PL21, …", close its tab | The link is on now: CTPlay sends its messages when a setting changes | |
| 53 | Open Components again and connect | It connects as in row 51 | |
| 54 | With Components open, on the Circuit: Shift + Synth 1 (its Keys page). Press pad 1 twice (mono off, then on again). Shift + Drum 1 (Pattern tools 2). Press pad 28 four times (the accent goes round, back to first hit). Then, in Components, open the list of the device's projects | Each change sends a CTPlay message out of the USB port the link page's hello came in on (row 52), most likely the one Components uses. **Components shows no error** and keeps working: the project list opens. If Components shows anything else (a message, a disconnect), write it down. Pad 1 and pad 28 end as they were | |
| 55 | In Components, open the synth patch editor for Synth 1's patch (the live editor: it changes the sound the Circuit plays). On the Circuit: Shift + Synth 1 (its Keys page opens). Press Play. In Components, turn the filter cutoff (or any control you can hear) up and down | **Synth 1's strummed chords change sound as you move it**, as on the official firmware. The Keys page stays open and unchanged | |
| 56 | Stop. Close Components' tab. Load P1 (Projects view, tap P1). **Do not save** | The project as saved: the patch edit is gone | |

### C. Projects
Start: **P1 loaded.** Sequencer stopped. Every MIDI tab closed. P2 is empty.

| # | Do | Expect | Result |
|---|---|---|---|
| 57 | Open Components and connect. Download the full project (slot P1) from the device to the computer | It downloads with no error | |
| 58 | Send that project from the computer to the empty slot **P2** | **Components accepts it: no error, no warning.** Its validator checks a project before it sends it; in emulation it accepts every CTPlay project tried, so a refusal here is a surprise: report it at once | |
| 59 | Close Components' tab. On the Circuit, load P2 | It loads | |
| 60 | Open the link page, Allow MIDI access, press Read. Compare the table with row 50's copy. Close the tab | **Every row the same** | |
| 61 | Shift + Synth 1 | **The Keys page opens** (used last): pads 1, 2 and 3 bright | |
| 62 | Hold Shift, tap pad 27. Then hold Shift, tap pad 28 | Pad 27 opens **Pattern tools 2** (used last). Pad 28 opens **Phrasing** (used last) | |
| 63 | Shift + Drum 1 | **Pattern tools 2** opens (used last): pad 28 bright yellow | |
| 64 | Press Synth 1 (its Note view). Hold Shift and look. Let go | **1-16/17-32 lit blue** (the Quick view is Arp). **Clear cyan:** the count-in (saved with the project) and stock's click (on since row 2; nothing in this plan turned it off). If Clear is magenta (count-in only), write it down | |
| 65 | Press Play. Listen for 3 bars. Stop | **As row 47:** Synth 1's chords strummed, no beat 2 in bars 1 and 3. Drum 1's double hits, beat 3 only in bar 1. Drum 2 on beat 4 only in bar 1. Synth 2's line as written down in row 16 | |
| 66 | Shift + Pattern Settings (Synth 1's probability view). Tap step pad 5 | Row 4: **pad 25 dim cyan, pad 26 bright cyan** | |
| 67 | Press Drum 2. Shift + Pattern Settings. Tap step pad 13 | Row 4: **pad 25 bright cyan, pads 26–32 dim cyan** (the cycle of 8) | |
| 68 | Press Patterns, tap pad 9 (Synth 1's pattern 2). Press Play. Listen for 2 bars (one pass of 32 steps). Stop. Tap pad 1 | **The long C, as row 4:** about 20 steps, no new attack 16 steps after it starts | |
| 69 | Tap pad 10 (Synth 2's pattern 2). Press Synth 2 and look at the step pads. Press Play. Listen for 2 bars. Stop. Press Patterns, tap pad 2 | **Step pads 1, 9 and 10 lit.** Beat 1: the six-note chord (as many notes as the synth holds). Beat 3: **C, E, G strummed slowly** (the roll) | |
| 70 | **All 64 projects.** Open Components and connect. Back up every project of the device to the computer | It finishes with no error | |
| 71 | Restore that backup to the device (every project back) | No error. The Circuit shows the same projects as before | |
| 72 | Close Components' tab. Load P1. Shift + Synth 1. Then press Synth 1, press Play, listen for 2 bars, Stop | The Keys page opens. **It plays as row 65** | |

### D. Packs
Start: **P1 loaded.** Sequencer stopped. The backup of row 70 on the computer.

| # | Do | Expect | Result |
|---|---|---|---|
| 73 | Open Components and connect. Make a pack that holds the full project (from the backup of row 70, or the download of row 57). Send the pack to an **empty pack slot** of the device (not the test pack's) | No error | |
| 74 | On the Circuit, load that pack (stock's Packs view). Load the full project in it | It loads | |
| 75 | Shift + Synth 1. Then press Synth 1, press Play, listen for 2 bars, Stop | The Keys page opens. **It plays as row 65** | |
| 76 | In Components, read the pack back from the device (download its projects) | No error. The full project is in it | |
| 77 | Close Components' tab. On the Circuit, load the test pack again (Packs view) | The test pack: P1 and P2 hold the full project | |

### E. Patches and samples
Start: **the test pack, P1 loaded.** Sequencer stopped. Every MIDI tab closed.

| # | Do | Expect | Result |
|---|---|---|---|
| 78 | Open Components and connect. In its synth editor, change a **Poly** patch (so row 79's chords still sound) and save it to an empty patch slot of the device | No error | |
| 79 | On the Circuit: press Preset (Synth 1) and pick that patch. Press Synth 1, press Play, listen. Stop | **Synth 1's strummed chords with the new sound** | |
| 80 | In Components, send a short drum sample (a WAV of your own) to an empty sample slot of the device | No error | |
| 81 | On the Circuit: press Drum 3. Give it that sample (stock's sample pads, rows 3–4) and play it | **You hear the new sample** | |
| 82 | Close Components' tab. Load P1. **Do not save** | The project as saved (Synth 1's patch and Drum 3's sample as before) | |

### F. Back to stock (the recovery path)
Start: **the test pack, P1 loaded.** Sequencer stopped. Every MIDI tab closed. P3 and P4 are empty.

| # | Do | Expect | Result |
|---|---|---|---|
| 83 | Open Components and connect. **Install the official firmware** with its firmware update. If Components says the firmware is up to date and offers no install, write that down, close its tab, and send the official firmware with the uploader instead: open `slim/build/ct_uploader.html`, choose the file `stock/circuittracks-firmware-4486-STOCK.syx` (the uploader names it the official firmware 1.2.1) and send it. If an install stops halfway or the Circuit does not start: the box at the top (Scales + Preset + Note at power-on) | The Circuit restarts on the official firmware. **Write down which way you used** | |
| 84 | Hold Shift and look at the track buttons. Then press Shift + Synth 1 | **Synth 1, Synth 2, MIDI 1, MIDI 2 and Drum 1–4 stay dark** while Shift is held (CTPlay lights them). Shift + Synth 1 opens no page: the official firmware | |
| 85 | Load P1. Press Play. Listen for 3 bars. Stop | **Every step on every pass:** Synth 1 on all four beats in every bar, as **block chords** (Played is CTPlay's). Drum 1's double hits on every beat in every bar. Drum 2 on beats 2 and 4 in every bar. Synth 2's line as row 16. Nothing hangs | |
| 86 | Press Patterns, tap pad 9 (Synth 1's pattern 2). Press Play. Listen for 2 bars. Stop. Tap pad 1 | **Write down** whether the C holds about 20 steps with no new attack, as on CTPlay. It should: the held note is written with stock's own tie | |
| 87 | Tap pad 10 (Synth 2's pattern 2). Press Play. Listen for 1 bar. Stop. Tap pad 2 | Beat 1: the six-note chord. Beat 3: **C, E, G strummed** (a Written roll is ordinary step notes) | |
| 88 | Press Synth 1. Shift + Pattern Settings. Tap step pad 5 | Rows 1–3 as usual. **Row 4 dark** (the official firmware leaves it dark) | |
| 89 | **Re-save on stock.** Press Drum 3, tap step pad 3 (a hit: a stock edit). Save the project **to slot P3** (stock's save to another slot) | It saves | |
| 90 | **A stock project.** In the Projects view, tap the empty slot **P4** (a new project). Press Drum 1, tap step pads 1, 5, 9 and 13. Press Synth 1: hold step pad 1, press the C pad; hold step pad 9, press the G pad. Save (Save, then Save again). Press Play, listen, Stop | Kicks on every beat, a C on beat 1, a G on beat 3. **Write down what you hear** (the reference for H) | |
| 91 | **A Novation pack.** Open Components and connect. Send one of Novation's packs (any factory or artist pack) to the device. Close Components' tab. On the Circuit, load that pack (Packs view), load its first project, press Play for a few bars, Stop | **Write down** the pack, the project and what you hear in a few words (tempo, which tracks play) | |
| 92 | Load the test pack again (Packs view) | The test pack | |

### G. The beta again
Start: **the official firmware, the test pack loaded.** Every MIDI tab closed.

| # | Do | Expect | Result |
|---|---|---|---|
| 93 | Install the beta: `cd slim && ../.venv/bin/python -m slimbuild.uploader`, open `slim/build/ct_uploader.html`, send `slim/build/PL21/circuittracks-4486-PL21.syx` (the uploader lists it as PL21: its sha256 equals `syx_sha256` in `slim/firmware/PL21/manifest.json`). Close the uploader's tab. Hold Shift | The Circuit restarts. With Shift held, **Synth 1, Synth 2, MIDI 1, MIDI 2 and Drum 1–4 light up**: CTPlay | |
| 94 | Load P1 (never saved on stock). Shift + Synth 1 | **The Keys page opens:** the installs left the project alone | |
| 95 | Load **P3** (the re-save on stock). Open the link page, Allow MIDI access, press Read. Compare with row 50's copy. Close the tab | **Write down** whether every row is the same. They should be: the official firmware saves the record's tail without reading it (the guide says so; not yet seen on the device). If rows differ, copy the table | |
| 96 | Shift + Synth 1. Then Shift + Drum 1 | **Write down** which pages open (as saved: Keys, then Pattern tools 2) | |
| 97 | Press Synth 1. Shift + Pattern Settings, tap step pad 5. Then press Drum 1, Shift + Pattern Settings, tap step pad 9, hold Shift. Then press Drum 2, Shift + Pattern Settings, tap step pad 13 | **Write down** what row 4 shows each time. Kept: as rows 66, 27 (pad 25 bright green with Shift) and 67. Lost: dark. Unknown: whether the official firmware keeps the condition bytes in the patterns | |
| 98 | Press Play. Listen for 3 bars. Stop | **Write down** whether it plays as row 65 (the conditions and the strum back) or as row 85 (every step on every pass, block chords). **Drum 3 hits on step 3** in both cases (the stock edit) | |

### H. Stock's projects on CTPlay
Start: **the beta, the test pack loaded.** Sequencer stopped. Every MIDI tab closed.

| # | Do | Expect | Result |
|---|---|---|---|
| 99 | Load **P4** (made on stock). Press Play. Listen. Stop | **As written down in row 90** | |
| 100 | Shift + Synth 1 | **The Chords page with the defaults:** pad 1 bright green (shape off), pad 17 bright blue, pad 21 bright magenta, pad 24 dim orange, pads 25–27 dim blue, pads 28–30 dim white, pad 31 bright white | |
| 101 | Shift + Drum 1 | **The Repeat page with the defaults:** no rate lit (pads 1–8 dim), pad 9 bright white (as struck), pads 15 and 16 dim | |
| 102 | Press Synth 1. Shift + Pattern Settings. Tap step pad 1 | **Row 4 dark** (no condition) | |
| 103 | Open the link page, Allow MIDI access, press Read. Close the tab | **The new-project values:** every row `00`, except **arp `00 08` for each track, euclid `20 40` for each track, melody `00 10` for each track, drum euclid `20 00` for each drum** | |
| 104 | Load the Novation pack of row 91 (Packs view) and its first project. Press Play for a few bars. Stop | **It plays as written down in row 91** | |
| 105 | Shift + Synth 1 | The Chords page with the defaults, as row 100 | |
| 106 | Press Synth 1 (or a track with notes in this project). Shift + Pattern Settings. Tap a step with notes | **Row 4 dark:** CTPlay reads no condition in a project it has not marked | |
| 107 | Load the test pack again. Then go back to your own pack (or restore your backup from Before you start, step 1) | Your own projects | |

## Results
A: A16 C, D, E (octave higher, tied), F (oct+), G, A, B  
A50 table:  
| field | offset | bytes |
|---|---|---|
| chord settings | 0 | AA AA AA AA |
| rootless | 4 | 0F |
| strum | 5 | FF |
| strum falling | 6 | 0F |
| mono | 7 | 0F |
| arp | 8 | A9 05 A9 05 A9 05 A9 05 |
| count-in | 24 | 01 |
| euclid | 25 | 85 CF 85 CF 85 0F 85 4F |
| melody | 37 | 59 09 59 09 59 09 59 09 |
| rhythm | 53 | 43 2F 02 43 2F 02 43 2F 02 43 2F 00 |
| melody vary | 65 | 06 06 06 06 |
| chord voice | 77 | 20 20 20 20 |
| repeat | 81 | E7 00 |
| drum euclid | 87 | C3 2F C3 2B C3 2F C3 2F |
| drum rhythm | 95 | A2 6F 04 00 00 04 00 00 04 00 00 04 |
| drum accent | 107 | 01 00 00 00 |
| step chords | 115 | 0F |
| pattern strum | 116 | 99 |  

B: B51 Connects normally, shows FW as 1.2.1. All tests passed.  
C: All tests passed. Minor differencies to test steps in last page and mixer settings due to checking the Synth 1 strum after section A and changing the last viewed pages in the process.  
D: All tests passed  
E: All tests passed  
F: All tests passed  
F83 Components says device is up to date and no option to install firmware. Flashed with CTPlay uploader.  
F86 Note holds over 16 steps.  
F90 Kicks on every beat, a C on beat 1, a G on beat 3.  
F91 Circuit Tracks Factory Pack, project 9 "Winter Margin". Full drum and bass style song with both synths and all drum tracks playing.  
G: All tests passed  
G95 Rows identical.  
G96 Key, Pattern tools 2  
G97 Synth 1: 25 dim, 26 bright cyan, Drum 1: dim green row, shift -> 25 bright green, Drum 2: 25 bright cyan, 26-32 dim cyan.  
G98 Has the strum and conditions (as row 65)  
H: All tests passed