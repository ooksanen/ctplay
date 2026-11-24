# PL08 — device test plan (small features)

**What it is:** PL07 plus (spec `slim/docs/specs/2026-10-17-small-features-design.md`):
- **Strum speeds** 20 / 40 / 80 ms between notes (fast / medium / slow; PL07: 10 / 25 / 50).
- **Falling strum:** Chords page pads 5–6 = rising · falling. Falling plays every note of the chord from the highest
  down, the pad's own note in its place, the bass last.
- **Keys page** (page 3, magenta, table-of-contents pad 27): pads 1–2 = record poly (stock) · **mono**. Mono: a
  recorded note replaces the notes already on its step; notes recorded together (a chord) keep each other. Keys has no
  quick view (Shift + 1-16/17-32 still flips Chords ↔ Arp).
- **Count-in on Shift + Clear:** four states, Clear's LED with Shift: red off · green metronome · magenta count-in ·
  cyan both. With the count-in on, Record armed and stopped, Play gives four clicks, then recording starts.

Writes nothing to flash or the SD card (the metronome part is stock's own setting).

## Before you start
0. **Build from the tag** (PL09 changed the shared sources after PL08): `git checkout PL08`, then
   `cd slim && ../.venv/bin/python -m slimbuild versions/PL08.toml`, then `git checkout slim`. The printed syx sha256
   must equal `syx_sha256` in `slim/firmware/PL08/manifest.json` (`624e2404…`).
1. **Stack headroom gate (SL00D):** Main and UI columns with at least 2 green pads. slim now runs 416 B deep in the
   Main task (PL07 400 B), 212 B in the LED task (PL07 188 B) and 256 B on a pad press (`hook_stack` in the manifest).
2. **Back up the SD card.** Way back: power on holding **Scales + Preset + Note**, send the stock `.syx` (or PL07).
3. Flash `slim/build/PL08/circuittracks-4486-PL08.syx` with `slim/build/ct_uploader.html`.
4. Synth 1 on a simple **Poly** patch with a sustained sound; Synth 2 on a **Mono** patch (steps 9–14).

## Steps
| # | Do | Expected | Result |
|---|---|---|---|
| 1 | Synth 1, Chords page: triad, strum fast; play a key pad; then medium, slow | Fast is a clear strum now (20 ms), medium 40, slow 80 ms between notes | OK |
| 2 | Chords page | Pads 5–6: pad 5 bright white (rising), pad 6 dim | OK |
| 3 | Pad 6, strum slow, a 7th; play a key pad | Highest note first, falling, the pad's own note in its place among them; pad 6 bright | OK |
| 4 | Falling, bass below, then rootless over bass (Shift + pad 24) | The bass is always the last note | OK |
| 5 | Falling, slow, a 9th: release the pad after two notes; then right after pressing | The notes not yet sounded never sound; nothing keeps sounding | OK |
| 6 | Arp page: pattern up; back to Chords | Pads 1–6: only the stored speed and direction, dim | OK |
| 7 | Pattern off. Open Synth 1's page, ▼ ▼ | The **Keys** page: pad 1 bright magenta (poly), pad 2 dim, the rest dark; ▲ lit blue, ▼ off | OK |
| 8 | On a page, hold Shift | Table of contents: pads 25 green, 26 blue, 27 magenta (the open page bright) | OK |
| 9 | Note view: Shift + 1-16/17-32 twice, holding Shift after each | The 1-16/17-32 LED blue, then green (Keys skipped) | OK |
| 10 | Synth 2 (Mono patch), Keys page **poly**: record a few notes over one loop; then Keys pad 2 (**mono**) and record other notes over the same steps | In the Note view's steps (or Velocity view) each step you recorded on in mono holds only the new note; steps you did not play over keep theirs. Playback does not jump between notes | OK |
| 11 | Mono: record a triad (chord engine) onto a step that holds notes | The step holds the whole triad, none of the old notes | OK |
| 12 | Mono: arpeggio up 1/16, record it over steps with notes | Each step it played holds only the arpeggio's note | OK |
| 12b | Mono: a hand chord (three key pads at once), then a slow strum (Chords page), each over steps with notes | The hand chord's step holds its three notes; each step the strum reached holds only strummed notes, every strummed note recorded once | OK |
| 12c | Stock's record quantise off (**Shift + Record**: Record dims with Shift held), mono: play a quick run of notes into one step, and a hand chord | Every note of the run and the chord stays on its step (with its microstep); a pass later the step is replaced again | OK |
| 12d | Quantise still off, Keys pad 1 (**poly**), 120 BPM: record a few slow strummed 7ths (rising) on empty steps; play back; check a step in stock's Microstep view. Then **Shift + Record** again (Record bright = quantise on) | Recorded strum (candidate, not a PL08 feature): the notes play back as a roll; the root on its step, the others on later microsteps (80 ms ≈ 4 microsteps), a note past the step's end on the next step | OK |
| 13 | After step 10: hold a recorded step and add a key; change a step's velocity in the Velocity view; then save the project, power-cycle and load it | The replaced notes never come back | OK: the mono note and the added key both kept through the edit, velocity change, save and reload; the replaced poly notes never returned (a Mono patch sounds one of the two). |
| 14 | Keys pad 1 (poly), record over notes | Notes stack as in stock | OK |
| 15 | Hold Shift in any view; press Clear four times with Shift | Clear's LED: red → green → magenta → cyan → red. Green and cyan: stock's metronome clicks while playing; red and magenta: no metronome | OK |
| 16 | Magenta (count-in only). Stopped, press Record, then Play | Four clicks at the project tempo, Record blinking red on each beat; then the sequencer starts recording on the next downbeat | OK |
| 17 | Cyan (both): as 16, listening to where the start falls against the clicks | The start falls where a fifth click would; note any lateness | OK |
| 18 | Count-in on: press Play during the count; then Play again | The first cancels (nothing starts, Record stays armed); the second starts a new count | OK |
| 19 | Count-in on: press Record during the count | Record disarms, the count stops, no click after | OK |
| 20 | Count-in on, Record not armed: Play | Plays at once, as stock | OK |
| 21 | Green (metronome on); power-cycle, or load another project; hold Shift | Clear's LED shows whatever stock kept (green if the metronome stayed on, red if not), and matches whether it clicks | OK: switching project kept the metronome on (green), power cycle cleared it to off (red) as I think it should. |
| 22 | PL07 regressions: arpeggio latch, quick views, recorded arpeggio at 1/4 legato | As PL07 | OK |
| 23 | External MIDI clock (if available): count-in, arpeggio | Note what happens | Not available |

## Results
2026-10-17, PL08: **passed.** Step 23 (external MIDI clock) not run: no clock source. Recorded strum with record quantise off plays back as a roll (12d); no count-in lateness heard (17).
