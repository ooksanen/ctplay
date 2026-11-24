# PL06 — device test plan (arpeggiator and play page)

**What it is:** PL05 plus an **arpeggiator** (spec `slim/docs/specs/2026-10-14-arpeggiator-design.md`): held pads (their
chords included) play one note after another in time with the project. **Shift + Synth 1 / 2 or MIDI 1 / 2** opens the
track's **play page**; the track's button alone goes back. Strum is now set on the page (Shift + 1-16/17-32 does
nothing, as in stock). Writes nothing to flash or the SD card.

Play page (pads 1-32 from the top left):

| Row | Pads |
|---|---|
| 1 | pattern: off · up · down · up-down · down-up · random · as played · chord |
| 2 | rate: 1/4 · 1/8 · 1/16 · 1/32 · triplet · dotted · (spare) · latch |
| 3 | octaves 1 · 2 · 3 · 4 · gate short · medium · long · legato |
| 4 | strum off · slow · medium · fast |

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL06.toml`: the printed syx sha256 must equal
   `syx_sha256` in `slim/firmware/PL06/manifest.json`.
1. **Stack headroom gate (SL00D):** Main and UI columns with at least 2 green pads. slim now runs 368 B deep in the
   Main task (the arpeggio heartbeat; 304 B on the sequencer tick) and 232 B on a pad press (`hook_stack` in the manifest).
2. **Back up the SD card.** Way back: power on holding **Scales + Preset + Note**, send the stock `.syx` (or PL05).
3. Flash `slim/build/PL06/circuittracks-4486-PL06.syx` with `slim/build/ct_uploader.html`.
4. Synth 1 on a simple **Poly** patch; the metronome on to judge timing.

## Steps
| # | Do | Expected | Result |
|---|---|---|---|
| 1 | Synth 1 Note view: Shift + Synth 1 | The page: pattern off green, 1/4 blue, 1 octave magenta, gate short orange, strum off white | OK |
| 2 | Synth 1 (alone) | Back to the Note view, pads as before | OK |
| 3 | From the Mixer: Shift + MIDI 1 | MIDI 1's Note view with its page | OK |
| 4 | Synth 1 page: up, 1/16, close; hold a pad (stopped) | Its note repeats on 1/16 at the project tempo | OK |
| 5 | Chord triad (Shift palette), hold a pad | The triad's notes rising, then again | OK |
| 6 | Each pattern in turn (down, up-down, down-up, random, as played, chord) | As named; random never repeats a note twice in a row | OK |
| 7 | Rates 1/4, 1/8, 1/32; triplet and dotted with 1/8 | Against the metronome: as named | OK |
| 8 | Octaves 2-4 | The notes repeat one to three octaves up | OK |
| 9 | Gates short / medium / long / legato | Shorter to longer; legato joins the notes | OK |
| 10 | Play the sequencer with a drum pattern, hold a pad | The arpeggio locks to the pattern; with swing (Shift + Tempo) it swings with it | OK |
| 11 | Stop, keep holding | It carries on at the same tempo | OK |
| 12 | Latch on: hold two pads, let go | It keeps going; press another pad: it replaces them; latch off: it stops | OK |
| 13 | Latch on, let go, then switch to Synth 2 and play | The latched arpeggio keeps playing; back on Synth 1's page, latch off: it stops | OK |
| 14 | Latch an arpeggio on Synth 1 (1/16), then hold one on MIDI 1 (1/8) | Both, each in time | OK |
| 15 | Record on, 1/16, a few bars; play back | Plays back as played (also on the official firmware) | Plays back as played; gates recorded as set. Legato records one tick short (a 1/4 note = 23 of 24 ticks, the last pad at 5/6 in the Gate view; a small audible gap): `docs/followups.md`. An earlier run looked like all gates at 1/6: a different gate had been set by mistake, and stock's Gate view cycles downwards (6/6 → 5/6 → … → 1/6), so 5/6 read as 1/6 |
| 16 | Pattern off: chords and strum as PL05 (strum set on the page) | As PL05 | OK  |
| 17 | External MIDI clock (if available) | Note whether the arpeggio follows it playing and stopped | External MIDI clock not available right now. Will test later, but the device gets clock without issues so I'd assume it works like with internal tempo. |
| 18 | Leave the page open, press pads, Note / Mixer / FX / Preset | Pads only pick options; those buttons close the page | OK |

## Results
2026-10-16, PL06: **passed.** Step 15: legato records one tick short (the note-off goes out before stock counts
the last tick; `docs/followups.md`). Step 17 (external MIDI clock) not run yet.
