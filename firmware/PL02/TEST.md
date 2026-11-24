# PL02 — device test plan

**What it is:** CTPlay chord engine with **strum** (spec `slim/docs/specs/2026-10-12-strum-design.md`). Everything of
PL01 (chords, Shift palette on pads 17–32) plus: with a track's strum on, a chord's other notes follow the pad's own
note one by one, rising, 50 / 25 / 10 ms apart (slow / medium / fast). Strum runs in the Main task's 1 ms timer, the
first CTPlay code outside the UI task. It writes nothing to flash or the SD card; settings are not saved (every track
starts with chords off and strum off).

**Only after SL00D and PL01 have passed on this device.**

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL02.toml` — the printed syx sha256 must equal
   `syx_sha256` in `slim/firmware/PL02/manifest.json`.
1. **Stack headroom gate (SL00D):** on SL00D, **Shift + Drum 3** (stack page) must show the **Main task's column
   (column 4)** and the UI task's (column 5) with at least **2 green pads** (≥ 512 B unused). Why: a strummed note is
   sent from Main's 1 ms timer, 72 bytes (`hook_stack.main_ms.bytes` in the manifest) deeper than stock's own timer path, plus stock's
   note path (which stock's own playback already uses from there).
2. **Back up the SD card.**
3. Way back: power on holding **Scales + Preset + Note**, send `stock/circuittracks-firmware-4486-STOCK.syx` with the
   uploader, confirm with **Play**. Do not unplug or power off while it receives or installs.
4. Uploader: `cd slim && ../.venv/bin/python -m slimbuild.uploader` → `slim/build/ct_uploader.html`.
5. For the MIDI checks: a MIDI monitor on the Circuit Tracks' USB MIDI port; MIDI 1 on a free channel, Tx Note on.

## Flash
6. Open `slim/build/ct_uploader.html` in Chrome or Edge, pick `slim/build/PL02/circuittracks-4486-PL02.syx` (the page
   must show "slim PL02"), Send, confirm with **Play**.

## Controls
- PL01's palette: **Shift + pads 17–32** in the Note view (shape, inversion, spread, bass).
- Strum only affects chords: with shape "single" (Shift + pad 25) and bass off there is nothing to strum.
- **Strum: Shift + 1-16/17-32** in the Note view cycles the track's strum: off → slow → medium → fast → off. While
  Shift is held, the 1-16/17-32 LED shows it: dim white = off, blue = slow, green = medium, orange = fast.

## Tests
| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Power on | Boots as usual (the 1 ms timer hook is now the first slim code to run) | pass |
| 2 | Play a pattern, use the Note views and other views without touching Shift + 1-16/17-32 | Exactly as PL01 | pass |
| 3 | Synth 1 Note view, hold Shift | Palette as PL01; 1-16/17-32 LED dim white | pass |
| 4 | Shift + 1-16/17-32 four times, looking at its LED with Shift held | blue, green, orange, dim white | pass |
| 5 | Without Shift, 1-16/17-32 | Switches the page as stock | pass |
| 6 | Mixer view, Shift + 1-16/17-32 | Nothing (as stock); back in the Note view the strum setting is unchanged | pass |
| 7 | Synth 1: 7th (Shift + pad 27), strum slow; play pad 25 and hold | Root at once, then the three other notes rising, about 50 ms apart (a clearly audible roll) | pass |
| 8 | Same with medium, fast | Faster rolls; fast is close to a chord but still rolled | pass |
| 9 | Slow, 9th (Shift + pad 28) + bass (Shift + pad 24), hold until all sound | Root, then bass, then the other notes rising | pass |
| 10 | Slow, 9th: tap the pad very briefly | Only the notes that sounded before the release; nothing keeps sounding | pass |
| 11 | Slow, 9th: hold, switch to Mixer mid-roll, come back, release | Every note stops at the switch; no stuck note | pass |
| 12 | While a slow roll plays, Shift + 1-16/17-32 (change speed) | The roll keeps its speed; the next press uses the new one | pass |
| 13 | Pad LEDs during a slow roll (expanded Note view) | The other notes' pads light one by one as they sound | pass |
| 14 | Record (Synth 1, slow, 7th): record a few strummed chords, play back | A visible / audible roll in the recorded steps (notes on later microsteps) | **not as expected, by design of stock's recorder:** a slow strum at 120 BPM recorded onto 3 consecutive steps, not one step with microstep offsets. Strum is a performance feature; see Results |
| 15 | Save the project, flash the stock firmware, load it | The recorded rolls play as recorded | skipped (same as 14) |
| 16 | MIDI 1 track: strum medium, triad; MIDI monitor | Note-ons spaced ~25 ms, rising; every note-on has its note-off | pass: C4 / E4 / G4 at 0xA284 / 0xA29D / 0xA2B6 ms (25 ms apart), all three offs within 1 ms on release, channel 3, velocity 96 |
| 17 | **Stress:** sequencer playing a busy pattern on all tracks; on Synth 1 and Synth 2 (switching tracks) play fast strummed 9th chords quickly for a minute, overlapping | No stuck notes; afterwards stop: silence | pass (on top of a busy demo song) |
| 17b | **Recording stress:** Record on, sequencer playing a busy pattern; for about a minute play overlapping **fast** strummed 9th chords on Synth 1 and Synth 2 (switching tracks); then stop recording and the sequencer. Why: strummed notes reach the stock recorder from the Main task, which stock never does; recording is the one state the two tasks now share | Silence after stop (no stuck notes); the recorded steps hold plausible chord notes (no garbage steps, nothing missing that clearly sounded); the recorded pattern plays back | pass: no stuck notes, hang or lag; recorded steps plausible (hard to judge over the demo song's drums); other tracks untouched; playback works |
| 18 | Chord-note dropouts (observation, spec section 2): heavy patch, 9th + bass, strum off vs slow | observed: the **bass** drops, with any chord shape + bass at slow strum, even with a simple patch (square + triangle bass); it sounds briefly, then stops as the next strummed note comes in. Recorded in `docs/investigations/2026-10-12-chord-voice-dropouts.md` |
| 19 | Power-cycle, then Shift held on each of the four tracks' Note views | Strum is off on every track (1-16/17-32 LED dim white): settings are not saved (spec S7) | pass |
| 20 | Drum 1 (a drum track), Shift + 1-16/17-32; then back on Synth 1 | Nothing on the drum track (as stock); on Synth 1 the strum setting is unchanged | pass |

## Results
**2026-10-12, PL02 (syx `6ed13b06…3e21`): passed.** Everything the build controls works on the device: the three speeds,
the control and LED 53, cut-short strums (release, view switch), LEDs during a roll, settings reset at power-on, the
drum track, MIDI-out timing (25 ms measured at medium), and both stress runs (playing, and recording) with no stuck
notes, hang or lag.

- **Recording (14, 15):** stock's recorder puts each note on its own step, so a recorded strum comes back spread over
  consecutive steps, not as one step with microstep offsets. Strum is documented as a **performance feature**. A real
  recorded strum would need the notes written into the root's step with microsteps (pattern writer; candidate
  "Recorded strum" in `docs/candidates.md`). Recording with strum on is safe (17b).
  *Later finding (2026-10-17, code):* stock's recorder keeps microsteps when its record quantise is off (Shift +
  Record); this run had it on (the default). Re-checked as `firmware/PL08/TEST.md` step 12d.
- **Dropouts (18):** with strum the dropped note is clearly the bass (see the investigation).
