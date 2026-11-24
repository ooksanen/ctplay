# PL09 — device test plan (ITCM)

**What it is:** PL08 with the chord engine's state (held chords, the arpeggiator's run state, mono record's visits:
164 B) moved from slim's 240 B RAM pool into the chip's ITCM RAM (`0x3F58–0x4000`), which SL00D verified on the device
but never wrote (spec `slim/docs/specs/2026-10-17-itcm-opt-in-design.md`). The pool drops from 236 to 72 B used.
Nothing should look or sound different from PL08.

At power-on slim checks that the MPU is off, then write-tests its ITCM bytes. If either fails, **CTPlay stays off and
the device behaves exactly as stock** (no chords, no play pages): that is the safe failure, not a hang.

Writes nothing to flash or the SD card. Test PL08 first (`firmware/PL08/TEST.md`): this run checks only what changed.

## Before you start
0. **Build from the tag** (PL10 changed the shared sources after PL09): `git checkout PL09`, then
   `cd slim && ../.venv/bin/python -m slimbuild versions/PL09.toml`, then `git checkout slim`. The printed syx sha256
   must equal `syx_sha256` in `slim/firmware/PL09/manifest.json`.
1. **Stack headroom gate (SL00D):** as PL08 (unchanged: 416 B Main, 212 B LED task, 256 B pad press).
2. **Back up the SD card.** Way back: Scales + Preset + Note at power-on, send the stock `.syx` (or PL08).
3. Flash `slim/build/PL09/circuittracks-4486-PL09.syx` with `slim/build/ct_uploader.html`.

## Steps
| # | Do | Expected | Result |
|---|---|---|---|
| 1 | Power on. Synth 1: Shift + pad 26 (triad), play a pad; Shift + Synth 1 | The chord plays; the Chords page opens. **If CTPlay acts as stock** (single notes, no page): the ITCM test failed or the MPU is on: stop and report | OK |
| 2 | Power-cycle twice more, repeat step 1 each time | Same every boot | OK |
| 3 | Heavy session, as SL00D's: load a pack; a pattern playing with chords on two tracks and a latched 1/16 arpeggio for a few minutes; a strummed chord now and then; a Components transfer | No stuck or wrong notes, no arpeggio running by itself after latch off, chords release cleanly | OK |
| 4 | Mono record (Keys pad 2) over a few steps, as PL08 step 10 | Still replaces | OK |
| 5 | Quick PL08 checks: falling strum (Chords pad 6), Shift + Clear count-in | As PL08 | OK |

## Results
2026-10-17, PL09: **passed.** The ITCM write test passed on every boot; the chord engine ran from ITCM through power cycles and a heavy session.
