# PL01 — device test plan

**What it is:** the first CTPlay build: the chord engine v1 (spec `slim/docs/specs/2026-10-11-chord-v1-design.md`).
In the synth / MIDI Note view a pad plays a chord built in the project's scale. It writes nothing to flash or the SD
card; settings are not saved (every track starts as "single" = stock behaviour).

**Only after SL00D has passed on this device.**

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL01.toml` — the printed syx sha256 must equal
   `syx_sha256` in `slim/firmware/PL01/manifest.json`.
1. **Stack headroom gate (SL00D):** on SL00D, **Shift + Drum 3** (stack page) must show the UI task's column with at
   least **2 green pads** (≥ 512 B unused); if you cannot tell which column is the UI task, at least 2 green pads in
   **every** column. Otherwise do not flash PL01. Why: a pad press runs about 168 B deeper than stock's own path (entry
   stub 32 B + dispatcher 8 B + `chord_on_pad` 128 B, plus what the stock functions it calls use).
2. **Back up the SD card.**
3. Way back: power on holding **Scales + Preset + Note**, send `stock/circuittracks-firmware-4486-STOCK.syx` with the
   uploader, confirm with **Play**. Do not unplug or power off while it receives or installs.
4. Uploader: `cd slim && ../.venv/bin/python -m slimbuild.uploader` → `slim/build/ct_uploader.html`.
5. For the MIDI checks: a computer with a MIDI monitor on the Circuit Tracks' USB MIDI port; MIDI 1 on channel 1
   (any free channel), Tx Note on.

## Flash
6. Open `slim/build/ct_uploader.html` in Chrome or Edge, pick `slim/build/PL01/circuittracks-4486-PL01.syx` (the page
   must show "slim PL01"), Send, confirm with **Play**.

## Palette (hold Shift in the Note view)
Pads numbered 1–32 from the top left. Shift lights pads 17–32:
- **pads 25–32 (green): shape** — 25 single (off), 26 triad, 27 7th, 28 9th, 29 sus2, 30 sus4, 31 add9, 32 6th
- **pads 17–20 (blue): inversion** 0–3
- **pads 21–23 (magenta): spread** — close, drop-2, wide
- **pad 24 (orange): bass** on / off
The selected option of each group is bright, the others dim. Settings are per track.

## Tests
| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Power on | Boots as usual | |
| 2 | Play a pattern, use Synth 1 / MIDI 1 Note views, other views | Exactly as stock (every track starts as single), except that Shift + pads 17–32 in the Note view pick palette options instead of playing | |
| 3 | Synth 1, hold **Shift** | Pads 17–32 show the palette: pad 25 bright green, 17 bright blue, 21 bright magenta, 24 dim orange; pads 1–16 unchanged | |
| 4 | Photograph the palette | Colours as described (note any that look wrong) | photo: |
| 5 | Shift + pad 26 (triad), let go, play pads | Each pad plays a 3-note chord in the scale; the other chord notes' pads light while held | |
| 6 | MIDI 1: first pick the triad there (settings are per track: Shift + pad 26 while MIDI 1 is selected), then play pad 25 (bottom-left) with the MIDI monitor open | 3 note-ons, then exactly 3 note-offs on release; same velocity | |
| 7 | MIDI 1, at the default octave (very low / high octaves can drop notes outside the device's range): each shape (pads 26–32), each inversion, each spread, bass on | Note counts: triad / sus2 / sus4 3, 7th / add9 / 6th 4, 9th 5, +1 with bass; every note-on has its note-off | |
| 8 | Synth 1, 9th + bass, hold two chords that share notes, release them in both orders | Releasing the later chord silences the notes it shares with the still-held earlier one: expected (spec decision C6), not a fault. The fault would be a note that keeps sounding after both are released | |
| 9 | Hold a chord and press Synth 2 / Mixer / FX / Preset, then release the pad | The chord stops when the view changes; nothing keeps sounding | |
| 10 | Hold a chord, change the shape with Shift + pad 28, release | The chord stops completely | |
| 11 | Synth 1, triad, default (2-row) Note view: hold a chord pad, hold a step pad (top two rows), release the chord pad, then the step pad | Nothing keeps sounding. The step receives only the chord's root in v1 (chords in step entry are later work) | |
| 12 | Hold Shift, press a palette pad, let go of Shift first, then the pad | Nothing plays, nothing sticks | |
| 13 | Record: Synth 1 triad, record 4 chords into a pattern, play it back | Every chord plays back in full (all its notes are in the steps) | |
| 14 | Optional: save the project, flash STOCK, load the project | The recorded chords still play | |
| 15 | Synth 1, 9th + bass, play overlapping chords quickly | Voices are stolen audibly but nothing sticks; note what it sounds like | |
| 16 | Scales: Chromatic, triad | Pads play major-key chords of the project root (e.g. root C: pad C = C E G, pad D = D F A) | |

If anything sticks or the device misbehaves: note what you saw, then recover with Scales + Preset + Note and STOCK.

## Results
- **Date:** 2026-10-11. Firmware: PL01, syx sha256 `eda3fb49…1681`, the published manifest; the uploader's display was not
  noted. Stack gate: met by SL00D's run (UI and Main ≥ 1.5 KB free; `slim/firmware/SL00D/TEST.md`).
- **Steps 1–16:** all passed, everything exactly as expected (reported by the user), including:
  - step 14, the optional one: the project with the recorded chords still played after flashing STOCK;
  - steps 6 / 7 on MIDI out, with the MIDI monitor.
- **Palette colours (step 4):** as described.
- **Chromatic behaviour (step 16):** keep.
- **User feedback:** the inversion order (pads 17–20) is fine as it is. The "notes below the pad's note" layout (pad 20 =
  root position, each pad to the left drops one more note) stays an option if it feels odd in use.

### Follow-up 2026-10-12: chord notes that do not sound (open)
- PL01 rebuilt from the same manifest and reinstalled. On a synth with 9th + bass, the bass is often silent, while
  the MIDI out shows all 6 notes, balanced. With 7th + bass it is silent less often. With a light patch it seems not to
  happen. Recorded chords lose it on playback too.
- Stock behaviour: 6-note steps entered by hand on the **stock** firmware drop notes too (mostly the highest by ear).
  Investigation: `slim/docs/investigations/2026-10-12-chord-voice-dropouts.md`.
