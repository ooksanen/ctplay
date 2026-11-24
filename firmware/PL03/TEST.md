# PL03 — device test plan

**What it is:** PL02 (chord engine + strum) plus **bass modes** (chord spec `slim/docs/specs/2026-10-11-chord-v1-design.md`,
section "Bass modes"). Shift + pad 24 in the Note view now cycles three states per track:

| Pad 24 (under Shift) | Mode | What a pad plays |
|---|---|---|
| dim orange | no bass | the chord as before |
| orange | **bass below** | the chord plus its root an octave below; a 9th leaves out its 5th (root, bass, 3rd, 7th, 9th: 5 notes) |
| white | **rootless over bass** | the pad's note **is** the bass; the chord sits an octave up without its root (9th: bass + 3rd, 5th, 7th, 9th). Play an octave lower than without bass to get the chord in the same place |

In both bass modes the bass is always the lowest note (a tone that inversion + drop-2 would put below it is raised by
octaves). Why five notes: the synth holds about 4–5 notes, depending on the patch; a further note takes the lowest /
oldest voice, on stock too (`slim/docs/investigations/2026-10-12-chord-voice-dropouts.md`). Writes nothing to flash or
the SD card; settings are not saved.

**Only after PL02 has passed on this device.**

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL03.toml` — the printed syx sha256 must equal
   `syx_sha256` in `slim/firmware/PL03/manifest.json`.
1. **Stack headroom gate (SL00D):** as for PL02 — on SL00D, **Shift + Drum 3** must show the Main (column 4) and UI
   (column 5) task columns with at least **2 green pads**. A pad press now runs 176 B deep in slim
   (`hook_stack.pad_note_on`, PL02: 168 B); a strummed note 72 B (`hook_stack.main_ms`).
2. **Back up the SD card.** Way back: power on holding **Scales + Preset + Note**, send the stock `.syx`, confirm with **Play**.
3. Uploader: `cd slim && ../.venv/bin/python -m slimbuild.uploader` → `slim/build/ct_uploader.html`.
4. Use a **Poly** patch on Synth 1 (check after every power cycle: a Mono patch drops and restores notes by itself).

## Flash
5. Open `slim/build/ct_uploader.html` in Chrome or Edge, pick `slim/build/PL03/circuittracks-4486-PL03.syx` (the page
   must show "slim PL03"), Send, confirm with **Play**.

## Tests
| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Power on | Boots as usual | OK |
| 2 | Quick PL02 check: 7th with strum slow, then strum off; Shift + 1-16/17-32 cycles strum | As PL02 | OK |
| 3 | Synth 1 Note view, hold Shift | Pad 24 dim orange (no bass) | OK |
| 4 | Shift + pad 24 three times, looking at pad 24 with Shift held | orange, **white**, dim orange (confirm the white is clearly white, not a tint) | OK |
| 5 | 9th (Shift + pad 28), bass below (orange), strum slow; hold a pad | Root, bass, then 3rd, 7th, 9th rising (5 notes; no 5th). **The bass keeps sounding** to the end | OK |
| 6 | Same, strum off | 5 notes together; the bass holds (patch permitting: note it if a note drops) | OK |
| 7 | 9th, rootless over bass (white), strum slow; hold a pad an octave lower than in 5 | The pad's note first (the bass), then 3rd, 5th, 7th, 9th rising an octave above it; the bass keeps sounding | Bass drops on second(?) note |
| 8 | Triad, inversion 2 (Shift + pad 19), drop-2 (Shift + pad 22), strum slow: in rootless mode, then in bass below | No note below the bass in either mode (the roll always starts at the pad / the bass) | OK |
| 9 | Single (Shift + pad 25), rootless over bass | Only the pad's note (same as no bass; the LED still shows white) | OK |
| 10 | Synth 1 in rootless mode; switch to Synth 2, hold Shift | Synth 2's pad 24 shows its own mode (dim orange if untouched): modes are per track | OK |
| 11 | Hold a 9th in bass below, Shift + pad 24 (to rootless) while holding, release | Everything stops on release; no stuck note | OK |
| 12 | Power-cycle (re-check the patch is Poly), hold Shift on each Note view | Pad 24 dim orange everywhere (not saved) | OK |

## Results
2026-10-13, PL03 (device). Steps 1–6 and 8–12 pass. **Step 7 fails:** in rootless over bass with a 9th and slow
strum, the bass (the pad's own note) drops, by ear at about the second note. The strum-off LED (dim white, `0x03`) pulses
slowly: a palette code that animates on the device (`docs/followups.md`); cosmetic, fixed in a later build.
Step 7 in emulation: slim sends all 5 notes and ends none before the release (`test_bass_modes_end_no_note_before_the_release`),
so the loss is in the synth's voice stealing; analysis in `docs/investigations/2026-10-12-chord-voice-dropouts.md`.
