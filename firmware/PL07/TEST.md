# PL07 — device test plan (play pages)

**What it is:** PL06 with its play page split into **pages per track** (spec
`slim/docs/specs/2026-10-17-play-pages-design.md`):
- **Shift + Synth 1 / 2 or MIDI 1 / 2** opens that track's last-used page (at power-on: Chords). **▼** = next page,
  **▲** = previous (Octave buttons, while a page is open). **Hold Shift on a page**: the table of contents on row 4
  (pad 25 Chords, 26 Arp; the open page bright); tap one to go there.
- **Quick view:** Shift in the Note view shows the track's quick view on pads 17–32: the chord palette (as before), or
  after **Shift + 1-16/17-32** the Arp page's top half (pattern, rate, triplet, dotted, latch). Its LED (1-16/17-32)
  shows which: green Chords, blue Arp.
- **Shift lights Synth 1 / 2, MIDI 1 / 2** in the same colour stock gives Note / Gate / Microstep with Shift.
- **Arp gate = one pad** (Arp page pad 21) that cycles like stock's Gate view: each press one sixth shorter, 1/6 → 6/6
  (6/6 = legato). Default 3/6.
- **Recorded arpeggio notes have their full length** (PL06 recorded them 1/6 of a step short).

Writes nothing to flash or the SD card.

Pages (pads 1-32 from the top left):

| Page | Row 1 | Row 2 | Row 3 | Row 4 |
|---|---|---|---|---|
| Chords | strum off · slow · medium · fast | — | inversion 0–3 · spread close / drop-2 / wide · bass | shape off · triad · 7th · 9th · sus2 · sus4 · add9 · 6th |
| Arp | pattern off · up · down · up-down · down-up · random · as played · chord | rate 1/4 · 1/8 · 1/16 · 1/32 · triplet · dotted · — · latch | octaves 1–4 · gate | — |

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL07.toml`: the printed syx sha256 must equal
   `syx_sha256` in `slim/firmware/PL07/manifest.json`.
1. **Stack headroom gate (SL00D):** Main and UI columns with at least 2 green pads. slim now runs 400 B deep in the
   Main task (PL06 368 B), 188 B in the LED task (PL06 136 B) and 232 B on a pad press (`hook_stack` in the manifest).
2. **Back up the SD card.** Way back: power on holding **Scales + Preset + Note**, send the stock `.syx` (or PL06).
3. Flash `slim/build/PL07/circuittracks-4486-PL07.syx` with `slim/build/ct_uploader.html`.
4. Synth 1 on a simple **Poly** patch with a sustained sound; the metronome on to judge timing.

## Steps
| # | Do | Expected | Result |
|---|---|---|---|
| 1 | Synth 1 Note view: Shift + Synth 1 | The **Chords** page: strum off white, the palette on rows 3–4; ▼ lit blue, ▲ off | OK |
| 2 | ▼ | The **Arp** page (pattern off green, 1/4 blue, 1 octave magenta, gate pad 3/6); ▲ lit green, ▼ off; ▼ again: stays | OK |
| 3 | Synth 1 (alone), then Shift + Synth 1 | Back to the Note view, then the Arp page again (last used) | OK |
| 4 | Hold Shift on the page, then tap pad 25 | Rows 1–3 dark; pad 25 green dim, pad 26 blue bright; the tap opens the Chords page | OK |
| 5 | On a page, Shift + ▲ / ▼ | Pages change; the pattern's notes and the octave are as before (close the page and play a pad) | OK |
| 6 | Hold Shift in any view (Note, Mixer, FX, Preset) | Synth 1 / 2, MIDI 1 / 2 lit in the same colour as Note / Gate / Microstep | OK |
| 7 | Chords page: each palette pad; then the Shift palette in the Note view | Both change the same settings, same LEDs | OK |
| 8 | Arp page: gate pad 21, press repeatedly; compare with stock's Gate view colours for a partial step | 3/6 → 2/6 → 1/6 → 6/6 (yellow) → 5/6 …, the same colours as stock's | OK |
| 9 | Pattern up, gate 1/6 … 5/6, hold a pad (stopped) | Shorter to longer | OK |
| 10 | Note view: Shift + 1-16/17-32, then hold Shift | Pads 17–32 = pattern and rate rows, latch; the 1-16/17-32 LED blue; pads 1–16 as stock's with Shift | OK |
| 11 | Quick view: pattern up, 1/8, latch; let Shift go, hold a pad, let go | It plays at 1/8 and keeps going (latched) | OK |
| 12 | Shift + 1-16/17-32 again, hold Shift | The chord palette, LED green | OK |
| 13 | Chords page with a pattern on | The strum row: only the stored speed, dim | OK |
| 14 | Record on, 1/16, each gate 1/6 … 6/6 over a few steps; then 1/4 legato; check steps in the Gate view | 1/16: the step's pad at 1/6 … 6/6 as set; 1/4 legato: 4 full pads; no gap at legato | OK |
| 15 | Record the chord pattern with legato (triad) | Every step holds the triad at full length; plays back as played | OK |
| 16 | After recording, play the same pads again with Record on | They record (nothing is left "held" in stock's recorder) | OK |
| 17 | PL06 regressions: latch on Synth 1 at 1/16 plus a held MIDI 1 arp at 1/8; swing; Stop / Play | Both in time, swing follows; nothing keeps sounding | OK |
| 18 | External MIDI clock (if available) | Note whether the arpeggio follows it playing and stopped | Not tested yet |

## Results
2026-10-17, PL07: **passed.** Step 18 (external MIDI clock) not run yet.
