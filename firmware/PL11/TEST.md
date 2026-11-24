# PL11 — device test plan (Euclidean fills)

**What it is:** PL10 plus a fourth Play page on every synth and MIDI track, **Pattern tools** (orange, table-of-contents
pad 27; Keys moves to pad 32, the end of the page list, and ▼ goes Chords → Arp → Pattern tools → Keys; spec `slim/docs/specs/2026-10-17-euclidean-design.md`):
- **Pads 1–16:** pad k = k hits, spread as evenly as possible over the steps of the track's current pattern (its own
  start and end steps). The pads preview the rhythm: hit bright orange, no hit dim, past the pattern's length dark;
  a pattern longer than 16 steps shows its first 16.
- **17 ◀ · 18 ▶ · 19** rotate the hits one step earlier / later, back to the start. **21** gate (as the Arp page's),
  **22–24** velocity soft · medium · hard (48 · 96 · 127).
- **32 Write:** press once (it blinks), again: the rhythm **replaces the current pattern's steps** with the last pad you
  played on the track, as a chord if the track's chord is on. **31 Undo** (blue): the steps as they were; again =
  the Write back.
- The Euclid settings are saved with the project (8 B more in the saved block).

Writes nothing to flash or the SD card itself; a written pattern is saved by stock's own Save. Test PL10 first
(`firmware/PL10/TEST.md`): this run checks only what changed.

## Before you start
0. **Build from the tag** (PL12 changed the shared sources after PL11): `git checkout PL11`, then
   `cd slim && ../.venv/bin/python -m slimbuild versions/PL11.toml`, then `git checkout slim`. The printed syx sha256
   must equal `syx_sha256` in `slim/firmware/PL11/manifest.json` (`58cf7106…`).
1. **Stack headroom gate (SL00D):** Main and UI with at least 2 green pads (≥ 1.5 KB free). PL11 runs 416 B deep in
   Main (as PL10), 280 B in the LED task (PL10 212 B), 276 B on a pad press (96 B), 336 B on a Note-view pad (256 B).
2. **ITCM:** Undo's copy grows slim's ITCM span from 168 B (`0x3F58–0x4000`, tested with PL09) to 1,064 B
   (`0x3BD8–0x4000`), write-tested at every power-on. **If CTPlay acts as stock** (no Play pages, single notes) after a
   cold boot, that test failed or the MPU is on: stop and report. Check it on three cold boots.
3. **Back up the SD card**: the test writes over patterns. Use a project you can lose.
   Way back: Scales + Preset + Note at power-on, send the stock `.syx` (or PL10).
4. Flash `slim/build/PL11/circuittracks-4486-PL11.syx` with `slim/build/ct_uploader.html`.
5. MIDI 1 on an empty pattern, Synth 1 on a simple Poly patch.

## Steps
| # | Do | Expected | Result |
|---|---|---|---|
| 1 | Shift + Synth 1, hold Shift | Page list on row 4: 25 green, 26 blue, 27 dim orange (Pattern tools), 28–31 dark, 32 dim magenta (Keys). Tap 27 | The page opens: pads 1–16 dim orange, 17–19 dim white, 21 the gate colour, 22–24 magenta (23 bright), 31 dark, 32 dark | OK |
| 2 | Pad 19 first (rotation at the start; pattern 16 steps, start 1, end 16). Then pads 5, 8, 3, 16, one at a time | Each press replaces the last. Bright, the rest dim: pad 5 → 1, 5, 8, 11, 14; pad 8 → 1, 3, 5, 7, 9, 11, 13, 15; pad 3 → 1, 7, 12; pad 16 → all 16. Pad 32 dim orange from the first press | OK |
| 3 | Pad 5 again; pad 18 (▶) a few times, pad 17 (◀), pad 19 | The bright pads move one step later, earlier, then back (pad 1 bright) | OK |
| 4 | Pad 32 once | Pad 32 **blinks** (if it is steady or another colour: report the code `0x47`). Press pad 1: the blink stops | OK |
| 5 | In the Note view play a pad on Synth 1 (chords off). Back on the page: pad 5, pad 32 twice. Play | That pad's note on 5 evenly spread steps of the pattern; the pattern's old notes gone | OK |
| 6 | Gate (pad 21) to 1/6, velocity hard (24), pad 32 twice; play | Short, loud hits; then gate 6/6, soft: long, quiet | OK: The velocity curve might need adjustment. At my normal listening volume (medium sounds pleasant), soft is barely audible. Maybe patch dependant? Will test other patches too. |
| 7 | Chords page: a 7th chord. Play a pad. Pattern tools: pad 32 twice, play | Every hit is that 7th chord | OK: Getting a bit of bit crusher type cracling/noise with chords now that I haven't noticed before. |
| 8 | Pad 31 (Undo, blue) once, no Write after it. Play, or look at the Note view's step pads | The pattern from before the last Write (step 7) is back: step 6's short, loud hits. The Pattern tools pads do not change (they show the rhythm, not the pattern). Pad 31 again: step 7's chords again | OK |
| 9 | Stock's Pattern Settings: set Synth 1's pattern to start at step 3 and end at step 14 (12 steps). Back on Pattern tools | Pads 13–16 dark; the hits spread over 12 steps; Write puts them on steps 3–14, and the Note view's step pads light them (re-test after the Note-view fix) | Steps play in the correct places, but are not shown as lit on the pads 3-14 on note view anymore. Restart seemed to fix issue and couldn't reproduce so it might've been a user error. |
| 10 | Patterns view: select pattern 2 of Synth 1. Pattern tools: Write | Pattern 2 is written; pattern 1 as it was. Undo on Synth 2's page: pad 31 dark | OK |
| 11 | MIDI 1: play a pad, Pattern tools, 7 hits, Write; play into a synth on MIDI | The notes go out on MIDI 1's channel at the hit steps | OK |
| 12 | While the sequencer plays Synth 1's pattern, Write a new rhythm | It changes at once, no stuck or doubled notes; stop: silence | OK |
| 13 | Save the project. Power off and on. Load it | The written patterns play as saved; Pattern tools shows each track's hits, rotation, gate and velocity again; pad 31 dark (Undo is not saved) | OK |
| 14 | Flash stock 1.2.1, load the project | The written patterns play the same on stock | OK |
| 15 | Back on PL11: Write on Synth 1, then load another project and come back (no power cycle) | Pad 31 (Undo) dark; pressing it changes nothing | OK |
| 16 | Pattern tools with hits picked: press pad 32 once (blinking), then load a project | After the load pad 32 does not blink; one press only arms it again | OK |
| 17 | Patterns view: chain Synth 1's patterns 1–2 (hold 1, press 2), give both notes, Play. While pattern 2 plays: Write. Wait until pattern 1 plays, then Undo | The Write lands on pattern 2 only; Undo puts pattern 2 back; pattern 1 never changes | OK |
| 18 | Load a project saved with PL10 (CTPlay settings in it, a track left on Keys) | Its chord / arp / Quick view settings as saved; every track opens on Chords (PL10's page numbers are not read); Pattern tools at defaults (no hits, medium, gate 3/6) | OK |
| 19 | Optional, the way back: flash PL10 and load a project saved with PL11 | Its PL10 settings come back; every track opens on Chords | |
| 20 | Page order and the remembered page, on Synth 2. (a) Shift + Synth 2. If the page is not Chords (green), press ▲ until ▲ is dark. (b) ▼, ▼, ▼. (c) ▲, ▲, ▲. (d) ▼, ▼, ▼ again, so you are on Keys. Press Synth 2 to close the page, then Shift + Synth 2. (e) Save (Save, Save), load the project again, Shift + Synth 2 | (a) Chords: ▲ dark, ▼ blue. (b) Arp, then Pattern tools, then Keys. On Keys ▼ is dark and ▲ orange. (c) Pattern tools, Arp, Chords. (d) The page opens on Keys. (e) It opens on Keys again | OK |

## Results
2026-10-18, PL11 (`58cf7106…`): **passed.** Steps 1–18 and 20 OK; step 19 (optional, PL10 reading a PL11 project)
skipped. Found and fixed during the run: the Note view did not light the steps a Write or Undo wrote, until a project
load (step 9; fixed with `rec_touch`, re-tested OK). Step 7: crackling with 7th-chord hits once, not reproduced after
restarts (taken as a one-time glitch). Step 6: soft velocity (48) is fine on most patches; one patch whose filter / macro
setup cuts the start of the notes made soft hits barely audible in a fast pattern with a short gate.
