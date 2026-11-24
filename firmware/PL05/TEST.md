# PL05 — device test plan (chord clean-up)

**What it is:** PL04 plus two chord fixes:
- **shared notes re-sound:** hold two chords that share notes and release the one you pressed second; the notes the
  first chord still holds start again (a new attack) instead of stopping. Releasing the first chord changes nothing
  for the second;
- **full range:** chord notes follow the device's note range (as stock's own pads, with the project's root note), so
  pads in the top octave play chords instead of single notes.

Everything else as PL04. Writes nothing to flash or the SD card.

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL05.toml`: the printed syx sha256 must equal
   `syx_sha256` in `slim/firmware/PL05/manifest.json`.
1. **Stack headroom gate (SL00D):** Main and UI columns with at least 2 green pads (a pad press now runs 204 B deep in
   slim, `hook_stack.pad_note_on`; PL04 196 B).
2. **Back up the SD card.** Way back: power on holding **Scales + Preset + Note**, send the stock `.syx` (or PL04),
   confirm with **Play**.
3. Flash `slim/build/PL05/circuittracks-4486-PL05.syx` with `slim/build/ct_uploader.html`.
4. Synth 1 on a simple **Poly** patch with a sustained sound (a pad-like envelope makes re-attacks easy to hear).

Pads are numbered 1-32 from the top left. In the Note view, pads 25-32 are the keys from the scale's root up; pad 27 is
two scale degrees above pad 25, pad 29 four.

## Steps
| # | Do | Expected | Result |
|---|---|---|---|
| 1 | Triad (Shift + pad 26), strum off. Hold pad 25, add pad 27, release **27** | Pad 25's chord keeps sounding in full: the two notes it shares with 27's chord start again | OK |
| 2 | Release pad 25 | Silence | OK |
| 3 | Hold pad 25, add pad 27, release **25** first | Pad 27's chord keeps sounding, **no** new attack; release 27: silence | OK |
| 4 | Hold pad 29, add pad 27, release **27** | Pad 29's chord keeps sounding in full (its own pad's note included); release 29: silence | OK |
| 5 | Steps 1-2 with slow strum (Shift + 1-16/17-32 once) | As 1-2; nothing keeps sounding at the end | OK |
| 6 | Strum off. Hold pad 17, add pad 32 (the same note), release 32, then 17 | The chord keeps sounding until 17 is released, then silence | OK with the assumption this meant same note an octave apart. Pad 17 is not used in synth layout that mimics a keyboard, note C is on pads 9, 16, 25, and 32. Tested on pads 25 and 32. |
| 7 | Octave ▲ to the top; triad, then 7th, on the top pads | Chords, not single notes (a note beyond the top of the range may be left out) | I have to assume it's working. The notes played at the top are so high I need to go down 2-3 ocataves before I start to hear a faint sound. Highest ones I hear are chords. |
| 8 | Octave ▼ to the bottom; triad and 9th + bass below on the lowest pads | Chords play; nothing keeps sounding after release | So low that it's just rumble so again, assuming it works. Nothing keeps sounding after release. |
| 9 | Record on: repeat step 1 over a pattern, then play it back | Plays back as it sounded (the re-started notes are recorded); nothing hangs | OK-ish. Tried several times to record holding a C triad, then play E triad for a while, release it and have the C play continuously the whole time. Only got the recording sound as smooth as played a couple of times. Most of the times there seems to be an ever-so-slight gap between chords. I suspect this might be due to the way CT records the steps. |
| 10 | PL04 regression: 9th, rootless over bass (white), slow strum, hold | All 5 notes; the bass keeps sounding | OK |
| 11 | Chords off (single, no bass): play pads, hold several | As stock | OK |

## Results
2026-10-14, PL05: **passed.** Step 6 was not exercised: the layout used has no two pads with the same pitch
(pads 25 and 32 are an octave apart; emulation covers the same-pitch case). Steps 7-8: the extreme octaves are barely
audible; nothing kept sounding. Step 9: small gaps between the recorded chords come from the recorder's step grid (a
re-sound is a note-off then a note-on, and stock snaps each to its step), a known limitation.
