# PL04 — device test plan (chord voice room)

**What it is:** PL03 + **chord voice room** (spec `slim/docs/specs/2026-10-13-chord-voice-room-design.md`): a chord note
takes a free voice when one more voice of the patch fits; a strummed 5-note chord that would still not fit leaves out
its 5th (else its 9th) instead of losing the bass; the strum-off LED is steady. The same build as `PL04D` without the
voice log: run `firmware/PL04D/TEST.md` first, then this as the normal build. Writes nothing to flash or the SD card.

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL04.toml`: the printed syx sha256 must equal
   `syx_sha256` in `slim/firmware/PL04/manifest.json`.
1. **Stack headroom gate (SL00D):** Main and UI columns with at least 2 green pads (a pad press runs 196 B deep).
2. **Back up the SD card**; way back as for PL04D.
3. Flash `slim/build/PL04/circuittracks-4486-PL04.syx` with `slim/build/ct_uploader.html`.
4. Synth 1 on a **Poly** patch.

## Steps
| # | Do | Expected | Result |
|---|---|---|---|
| 1 | Shift held in the Note view, strum off | The 1-16/17-32 LED steady dim white | |
| 2 | 9th, rootless over bass, slow strum (simple patch) | All 5 notes; the bass keeps sounding | |
| 3 | 9th, bass below, slow strum (simple patch) | All 5 | |
| 4 | Heavy patch: rootless 9th, slow strum | 4 notes, no 5th; the bass keeps sounding | |
| 5 | Stock pads, chords off, 5 notes one after another | As stock | |

## Results
(date, firmware, notes)
