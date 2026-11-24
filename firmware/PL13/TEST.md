# PL13 — device test plan (melodic generator)

**What it is:** PL12 plus the **melodic generator** (spec `slim/docs/specs/2026-10-19-melodic-generator-design.md`):
- A fifth Play page on every synth and MIDI track, **Melody** (yellow, pad 28 of the page list). It sets *which notes*
  Pattern tools' Write puts on the hits: root, pool (chord or scale), range, order, accents.
- **Pattern tools** gains a rhythm source (pad 20: Euclid or groove), a seventh gate value ("to the next hit", pad 21,
  white) and two dice (pads 29 and 30).
- **Undo (31) and Write (32)** are on both pages, the same two pads.
- **The draft:** with a new setting in use, after the first Write every press on the two pages re-writes the pattern
  when you lift your finger. The Write pad is bright orange (steady) while it lasts.
- **Every pattern write happens when you lift your finger** (Write's second press, Undo, a press in a draft). A write
  while the finger was still down made a phantom press on the next pad (found in this test run, 2026-10-20; PL11's
  Undo had it too: Write started blinking after Undo).
- The new settings are saved with the project (the saved block grows to 53 B, still inside the 64 B older builds read).

Writes nothing to flash or the SD card itself; a written pattern is saved by stock's own Save. Test PL12 first
(`firmware/PL12/TEST.md`): this run checks only what changed.

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL13.toml` (once PL13 is tagged: from the tag).
   The printed syx sha256 must equal `syx_sha256` in `slim/firmware/PL13/manifest.json` (`7e199b90…`).
1. **Stack headroom gate (SL00D):** Main and UI with at least 2 green pads (≥ 1.5 KB free). Hook stack against PL12:
   Main (`main_ms`) 416 B, same. LED task 336 B (PL12 280 B). A pad press (`ctrl_pad_press`) **476 B** (PL12 276 B): the page code. A pad release
   (`ctrl_pad_release`) **452 B**: the pattern writes now run here, on the UI task. A Note-view pad (`pad_note_on`) 256 B (PL12 336 B).
   Everything else is unchanged. The pad press is the deepest path to watch.
2. **Back up the SD card**: the test writes over patterns and loads projects. Use a project you can lose.
   Way back: Scales + Preset + Note at power-on, send the stock `.syx` (or PL12).
3. Flash `slim/build/PL13/circuittracks-4486-PL13.syx` with `slim/build/ct_uploader.html`. **If an earlier PL13 test
   build is installed, flash PL12 (or stock) first:** a build with the same name does not install over itself.
4. Synth 1 on a simple Poly patch (a bass patch is good for steps 8–10). Set the Note view to your keyboard layout. Set
   the project's scale to a major scale on C. In the steps below, "C" and "G" mean those notes in your layout.
5. Start from a **new empty project**: the steps expect the default settings (chord shape off, Arp off, no hit count
   picked). A project from an older build brings back its chord, Arp and Pattern tools settings. Keep one older project
   for step 22. Use a new empty pattern for each track you write to, unless a step says otherwise. Where a step says "play",
   start the sequencer and listen. Where a step says **"at once"** in a draft, it means: when you lift your finger.

## Steps
| # | Do | Expected | Result |
|---|---|---|---|
| 1 | Shift + Synth 1, hold Shift | Page list on row 4: 25 green, 26 blue, 27 dim orange, 28 **dim yellow** (Melody), 29–31 dark, 32 dim magenta. Tap 28 | The Melody page opens. Pad 28 of the list is now bright yellow while Shift is held | OK |
| 2 | Look at the Melody page, Shift released | Pad 1 bright yellow, pads 2–8 dim yellow. Pad 9 bright green, 10 dim green. Pad 11 bright magenta, 12–13 dim magenta. Pad 14 dim yellow. Pads 15–16 dark. Pad 17 bright white, pads 18–24 dim blue. Pads 25–28 dim magenta. Pad 29 dim white, **pad 30 dark**, pad 31 dark. Pad 32 dark if this track has no hit count picked yet, dim orange if it has one (the hit count is saved with the project, also from PL11 / PL12) | OK |
| 3 | Look at the yellow pads on the page (pads 1–8 and 14) for a minute. Then hold Shift and look at pad 28 of the page list (bright yellow) | The yellow is **steady**: no blinking, no pulsing | OK |
| 4 | Press ▼ | Keys opens. ▼ is dark; ▲ is yellow (it leads to Melody) | OK |
| 4b | Press ▲ | Melody opens again. ▲ has the colour of Pattern tools (orange), ▼ the colour of Keys (magenta) | OK |
| 5 | On Melody press pad 3 (down), then pad 1 (same) | Pad 3 bright, pad 1 dim; then pad 1 bright, pad 3 dim. Pad 30 turns dark again with "same" | OK |
| 6 | Pattern tools page: look at pads 17–24 and 29–32 | Pad 20 dim white (Euclid). Pad 21 the gate colour. Pad 29 dim white, pad 30 dark, pad 31 dark. Pad 32 as on the Melody page in step 2 (dark with no hit count, dim orange with one) | OK |
| 7 | Plain Euclid, two presses every time. Melody: order same, root last pad, accent off. Pattern tools: Euclid, gate 3/6. Play the note C in the Note view. On the Pattern tools page press pad 5, then pad 32 once | Pad 32 **blinks**. Nothing is written | OK |
| 7b | Press pad 32 again | The pattern is written (5 hits, all C). Pad 32 is **dim orange, steady** (not bright). Pad 31 turns blue | OK |
| 7c | Press pad 6 (6 hits) | Nothing is written. The preview changes only. Pad 32 stays dim orange. Press pad 32 twice again: the pattern has 6 hits | OK |
| 7d | **No phantom press after Undo.** Press Undo (pad 31) about 15 times, lifting your finger each time. Watch pad 32 | Each lift swaps the pattern (old, written, old …). Pad 32 **never starts blinking** (in the first run it did about half the time) | OK |
| 8 | **A bass line in each order.** Synth 1 on a bass patch. Melody: root = degree 1, octave pad 25 (−2), pool chord, range 2, order up. Then ▲ to Pattern tools: pad 8 (8 hits). Pad 32 twice. Play | The first Write took two presses (it keeps the pattern from before this Write, step 7's, for Undo). A line of single notes goes up through C, E, G and on. No chords | OK |
| 8b | ▼ back to Melody, pad 3 (down) | Pad 3 lights at once. When you lift your finger (a draft: the Write pad is bright orange) the line goes down | OK |
| 8b2 | **No phantom press in a draft.** Press the order pads 2–8 in a random order, about 20 presses, lifting each time | The pad you pressed **stays lit**: the selection never moves to the next pad. The line follows each order (in the first run, about every other press jumped to the next pad) | OK |
| 8c | Pad 4 (up-down), pad 5 (climb), pad 6 (walk), pad 7 (random), pad 8 (bass). One at a time, listen after each | Each press changes the line at once. Up-down goes up then down. Climb goes two up, one back. Walk moves by small steps. Random jumps without repeating. Bass leans on C and G, with C on the first hit | OK I think: from a C Climb plays C E G E G C G C. Walk plays C G G C G G C C. Random sounds randomly generated, but the notes stay the same. Should they be different random on every loop? Likely not. |
| 9 | Melody: pad 10 (scale), pad 2 (up) | The line walks every scale note, not only the chord notes | OK |
| 10 | **Range.** Pad 7 (random): the range is easiest to hear in this order | At once: the notes jump around in a random order, over two octaves (range 2, set in step 8) | OK |
| 10b | Pad 13 (range 3) | At once: the notes jump over three octaves; some are higher than before. Notes beyond the Circuit's range are left out (no error) | OK |
| 10c | Pad 11 (range 1) | At once: the notes stay inside one octave | OK |
| 10d | On the Chords page set a chord shape: triad (pad 26). Back on Melody | Nothing is written by this trip (the Chords page does not write) | OK |
| 11 | **Degree root and octave.** Melody: order same (pad 1), root pad 20 (degree 3) | At once: the pattern plays the triad on E (degree 3 of C major), one chord on every hit | OK |
| 11b | Root pad 18 (degree 1). Octave pads 25, 26, 27, 28 one at a time | The same chord moves one octave per press: pad 25 lowest, pad 28 highest. Pad 27 (octave 0) is the project root C in the middle-C octave (C4); pad 26 is one octave lower, pad 25 two lower, pad 28 one higher | OK |
| 11c | Root pad 17 (last pad) | Pads 25–28 turn dim and do nothing when pressed. The pattern plays the chord on the last pad you played | OK |
| 12 | **Dice keeps the other layer.** Still in the draft; Melody: order up, root degree 1 (pad 18), pool scale (pad 10). On Pattern tools press pad 5 (5 hits). Play and note the notes and the rhythm. Press **dice notes** (pad 30) once | The notes change; the hits stay on the same steps | OK |
| 12b | Press **dice rhythm** (pad 29) once, on Melody | The hits move to other steps (the preview on Pattern tools changes too); the same notes in the same order, on the new steps | OK |
| 12c | Press dice rhythm twice more, then dice notes twice more. Listen after each press | Every press changes something: dice rhythm always gives another rhythm, dice notes always other notes | OK |
| 12d | Dice rhythm in groove: on Pattern tools press pad 20 (bright white) and pad 19 (rotation back to the start; an earlier Euclid dice rotation stays when you switch). Pattern tools still has 5 hits. Then dice rhythm three times | Each press changes the rhythm: a different groove every time. The first beat is always a hit | OK |
| 13 | **Accents at soft velocity.** On Pattern tools press velocity soft (pad 22). On Melody press accent pad 14 once (first hit) | The first hit of the loop is clearly louder than the rest | OK |
| 13b | Pad 14 again (on the beat), then again (every 3rd hit) | Hits on steps 1, 5, 9, 13 are louder. Then every 3rd hit is louder | OK |
| 13c | Velocity hard (pad 24) | The accent is no longer heard: all hits are equally loud | OK |
| 14 | **Legato.** On Pattern tools: 4 hits, gate 3/6. Press the gate pad (21) three times: 2/6, 1/6, then **white** ("to the next hit"). Melody order up | Each note lasts until the next one; there is no gap. The last note lasts until the first hit of the next loop | OK |
| 14b | Gate pad again | 6/6 (the Arp page's colour). Press it twice more: 5/6, then 4/6 | OK |
| 15 | **The draft, while playing.** The sequencer playing, Synth 1, a draft going (step 8). Press pads on both pages for a minute: orders, dice, hits, rotation | Every press changes the loop. No clicks, no stuck or doubled notes. Stop: silence | OK |
| 15b | Look at pad 32 during the draft | Bright orange, steady | OK |
| 16 | **Pages keep the draft.** In the draft, on Melody, press ▲ three times (Pattern tools, Arp, Chords), then ▼ three times back to Melody | The Write pad is still bright orange. Nothing was written by the trip | OK |
| 16b | On Melody set the pool to chord (pad 9). On Chords, change the shape (the Chords page, pads 25–32). Back on Melody press pad 2 (up) | The press writes at once, with the new chord shape | OK |
| 16c | Press the **Note** button | The pages close. Open them again (Shift + Synth 1, Melody). Pad 32 is **dim orange**: the draft is over. One press on pad 3 changes only the settings | OK |
| 16d | Pad 32 once | Pad 32 blinks (armed). Press it again: written. A new draft begins | OK |
| 17 | **Undo after several changes.** Record a few notes into the pattern first. Then Write twice (with order up), so a draft starts. Make several changes (orders, dice, root). Then Undo (pad 31) | The pattern from before the **first** Write is back, not the one before the last change. The Write pad turns dim orange (the draft is over) | OK |
| 17b | Undo again | The last draft is back | OK |
| 17c | Start a draft again: Write twice with a new setting in use (order up). Press the Note button, open the pages again (Shift + Synth 1, Melody), press pad 3 (down) | Nothing is written by the press, and pad 32 is dim orange, not bright: the draft ended when the pages closed | OK |
| 18 | **A chained track.** Patterns view: chain Synth 1's patterns 1 and 2 (hold 1, press 2), give both a note, Play. While pattern 2 plays: start a draft (Write twice with order up) | The Write lands on pattern 2. Wait for pattern 1 to play: it is unchanged | OK |
| 18b | While pattern 1 plays, press a Melody pad (pad 5) | The re-write goes to pattern 2, not to the pattern playing now. Pattern 1 stays as it was | OK |
| 18c | Undo while pattern 1 plays | Pattern 2 is back as before. Pattern 1 never changed | OK |
| 19 | **Save and reload.** Set: Synth 1 order up, pool scale, range 2, root degree 3, octave −1, accent every 3rd hit, groove. Synth 2: a different order. Save the project (Save, Save). Power off and on. Load it | Both tracks' Melody pads and Pattern tools settings are as saved. A "last pad" root starts from the default note until you play a pad (the last pad is not saved). Dice notes and dice rhythm give the same notes as before the save (the seeds are saved) | OK |
| 20 | **A PL13 project on the official firmware.** Flash stock 1.2.1, load the project from step 19, play | The written patterns play the same on stock | OK |
| 20b | Flash PL13 again, load the project | Its Melody and Pattern tools settings are as saved (stock keeps the block and does not read it) | OK |
| 21 | **A PL13 project on PL12.** Flash PL12, load the project from step 19 | Its chord, arpeggiator and Pattern tools settings come back (PL12 accepts the block; it does not read the Melody fields) | OK |
| 21b | On PL12 save the project. Flash PL13, load it | The Melody pads are at their defaults (PL12 did not keep them); the other settings are as saved | OK |
| 22 | **A project load ends the draft.** Start a draft, then load another project (no power cycle). Open the pages again (Shift + Synth 1, Pattern tools) | Pad 32 is dim orange if the loaded project had hits picked on this track, dark if it had none; pad 31 dark. One press only arms the Write (no write) | OK |
| 23 | **CTCtrl still connects.** Close the CTPlay link test page. Open CTCtrl, connect | The CTPlay panel appears, a tap on each tab changes the device, and a pad press on the device shows in the panel. The panel does not show the Melody settings. Change an order on the Melody page: CTCtrl shows no error and keeps working | OK |
| 23b | On Pattern tools set groove (pad 20, bright white) and the gate "to the next hit" (pad 21, white). In CTCtrl open the Euclid tab and change the hit count there | The hit count changes on the device. Pad 20 is still bright white (groove) and pad 21 still white ("to the next hit") | OK |
| 23c | Close CTCtrl. Open `slim/pages/ctplay_link.html`, connect, Read | The field table has a new row **melody** (offset 37, 8 B), `00 10 00 10 00 10 00 10` by default | OK |
| 23d | Start a draft with order up on Synth 1. Write offset 37, bytes `02` (Synth 1: order down, pool chord, range 1: different from the byte Read shows) | One `state` line is logged. The draft ends: pad 32 turns dim orange | OK:
6:36:31 PM  state: 04 28 D3 DC 00 A0 08 0A 00 08 4A 01 00 08 85 16 00 00 00 00 00 00 00 00 01 A8 6E A2 C2 2D 41 20 40 00 00 00 00 02 10 00 10 00 10 00 10 00 00 00 00 00 00 00 00
6:36:31 PM  write: offset 37, 02
6:36:23 PM  state: 04 28 D3 DC 00 A0 08 0A 00 08 4A 01 00 08 85 16 00 00 00 00 00 00 00 00 01 A8 6E A2 C2 2D 41 20 40 00 00 00 00 01 10 00 10 00 10 00 10 00 00 00 00 00 00 00 00 |

## Results
2026-10-20, PL13 (`7e199b90…`): **passed.** Every step OK.
- The first run (an earlier PL13 build) found a phantom press on the next pad whenever a pattern was written during a
  press: in a draft, order pad 3 often landed on pad 4; Undo (pad 31) armed the Write (pad 32) about half the time.
  PL11's Undo had the same bug. Fixed by writing on the pad's release (commit `92070d6`); steps 7d and 8b2 confirm it.
- Step 8c: Climb from C played C E G E G C G C, Walk C G G C G G C C, as designed. Random keeps the same notes on every
  loop: the notes are picked once, at the write (dice notes picks new ones).
