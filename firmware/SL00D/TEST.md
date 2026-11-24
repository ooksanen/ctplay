# SL00D — device test plan

**What it is:** a diagnostic build. It proves that slim's C code runs on the device, maps the 16 KB ITCM
(`0x00000000–0x00003FFF`) and shows how much of the RTOS task stacks is unused. It writes nothing to flash or the SD card and lowers the stock heap limit by the size of slim's RAM (104 B); that is the only change outside its own area.

## Before you start
0. **Build the firmware:** `cd slim && ../.venv/bin/python -m slimbuild versions/SL00D.toml` — the printed syx sha256 must equal
   `syx_sha256` in `slim/firmware/SL00D/manifest.json`.
1. **Back up the SD card** (projects, packs, samples).
2. Know the way back: power on holding **Scales + Preset + Note**, then send `stock/circuittracks-firmware-4486-STOCK.syx`
   with the uploader (it labels it "STOCK Circuit Tracks 1.2.1 (build 4486)"); after Send the device asks for confirmation:
   press **Play** on the device. Do not unplug or power off the device while it is receiving or installing.
3. Build the uploader: `cd slim && ../.venv/bin/python -m slimbuild.uploader` → `slim/build/ct_uploader.html`.

## Flash
4. Open `slim/build/ct_uploader.html` in Chrome or Edge, pick `slim/build/SL00D/circuittracks-4486-SL00D.syx`
   (the page must show "slim SL00D"), connect the Circuit Tracks, Send, confirm with **Play** on the device.

## Tests
| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Power on normally | Boots as usual, no hang | |
| 2 | Play a pattern, open a few views | Everything as with the official firmware | |
| 3 | Hold **Shift**, press **Drum 4** | Pads 1–16 coloured, pads 17–31 off, **pad 32 white** | |
| 4 | Photograph the pads | — | photo: |
| 4b | Hold **Shift**, press **Drum 3** | Stack page: up to 8 columns of pads from the bottom (green bars, a column may be a single red pad); pad 32 is not the white 'alive' pad on this page | |
| 4c | Photograph the pads | — | photo: |
| 5 | **Shift + Drum 3** again | The view's own pads come back (pressing the combination of the page that is showing turns it off; the other combination switches pages) | |
| 6 | Press **Drum 4** without Shift | Drum 4 is selected, as stock | |
| 6b | In the Synth, Drum, Mixer (Master FX) and FX views, press **Shift + Drum 4** twice, then **Shift + Drum 3** twice | Only the diagnostic display toggles; nothing else changes (no track selection, no view change, no sound) | |
| 7 | Load a project, play for a minute, connect Novation Components and run a transfer (e.g. back up a pack) | Works as stock | |
| 8 | **Shift + Drum 4**, photograph | Compare with step 4 | photo: |
| 8b | **Shift + Drum 3** again, photograph | Compare with step 4c: a column that got shorter = that task needed more stack | photo: |
| 9 | Power off and on, **Shift + Drum 4** and **Shift + Drum 3** | Same patterns as steps 4 and 4c | |

ITCM page, pad colours (pads 1–16 = ITCM blocks of 1 KB from `0x0000`):
- **green**: zero at every check since boot, unchanged, writable — not observed in use
- **yellow**: non-zero (not write-tested): stock code/tables OR never-initialised RAM (power-on noise), or the block that holds the vector table: not decisive on its own
  (data that stock wrote before slim's first hook call — within milliseconds of boot — and never changed also shows yellow, not magenta)
- **magenta**: changed at any time since boot (checked continuously, one block per LED refresh) — stock uses it
- **red**: a zero block whose test word did not read back → not RAM

Stack page legend (pads: top row = 1–8, bottom row = 25–32; column = the same task stack in every photo, left to right):
- **green pads from the bottom**: each pad = up to 512 B of unused stack (1 pad = 128–512 B, 4 pads = 1.5–2 KB); small changes may not show
- **white top pad**: more than 2 KB unused
- **single red pad at the bottom**: under 128 B unused
- **column off**: that stack has used everything down to its bottom (no free stack left!)
- **single magenta pad at the bottom**: this device's memory layout differs from the RAM dump — this column cannot be measured
The reading is the high-water mark since boot (the unused fill is only ever overwritten).

If pad 32 never lights or the device misbehaves at any step: note what you saw, power on with
Scales + Preset + Note and send `stock/circuittracks-firmware-4486-STOCK.syx` (press **Play** on the device to confirm;
do not unplug or power off while it is receiving or installing).
(pad 32 dark can mean either that slim's code did not run or that slim stayed off because the heap already
reached its RAM — both are safe; note it and recover)

## Results (fill in)
Rule: record the ITCM (or a block) as usable for slim only if it shows no magenta and no red in steps 3, 8 and 9, AND the static
analysis of the stock image finds no reference to it; a green or yellow result alone does not make it verified.
- **Date:** 2026-10-11. Firmware: SL00D (syx sha256 `0b1679bb…bf3`, the published manifest; the uploader's display was not
  noted). Photos (not in git, kept by the user): `photos/20261011_*.JPG`, five ITCM / stack pairs.
- **Steps 1–9:** run as five sessions rather than in table order; all needed readings were taken.
  - 1, 2, 7: booted normally every time. It worked as stock through pattern playback, view changes, loading several
    packs, playing through projects and fetching a pack with Novation Components. No issues noticed.
  - 3–4b, 5: both pages showed and toggled in every session; pad 32 was white on the ITCM page every time.
  - 6 / 6b were not reported separately.
  - 8 / 9: two power cycles gave the same patterns as the first boot.
- **Sessions:**

  | Photos (ITCM, stack) | When | ITCM pads 1–16 | Stack columns 1–8 (green pads; R = single red, 0 = off) |
  |---|---|---|---|
  | 213007215, 213042219 | first boot after flashing, a pattern played | 1 magenta, 2–16 yellow | R 2 3 4 4 2 1 2 |
  | 213747235, 213807110 | power cycle, nothing done | all yellow | R 2 3 4 4 2 2 2 |
  | 214221821, 214235090 | light use | all yellow | R 2 3 4 4 2 1 2 |
  | 214948135, 215002028 | heavy use: packs loaded, projects played, Components pack fetch | all yellow | R 0 0 4 4 2 1 2 |
  | 215233607, 215241198 | power cycle | all yellow | R 2 3 4 4 2 2 2 |

- **Stack columns, identified afterwards** from the task control blocks in the RAM dump (their stack bottoms and
  names):
  - **Columns 4–8 are the five RTOS tasks:**

    | Column | Task | Free stack |
    |---|---|---|
    | 4 | Main | ≥ 1.5 KB throughout |
    | 5 | UI | ≥ 1.5 KB throughout |
    | 6 | Storage | 512 B–1 KB |
    | 7 | Content | 512 B–1 KB; 128–512 B after a pattern played: the tightest real task |
    | 8 | IDLE | 512 B–1 KB |

  - **Columns 1–3 are not task stacks.** No task points at them; they are blocks of the fill value in the heap.
    - Column 1 is a 64 B block at the heap start, hence its permanent red pad.
    - Columns 2 and 3 were overwritten under heavy use, so that memory is used at run time: it is **not** spare RAM.
- **Conclusion for `slim/stock/memory.toml`:**
  - ITCM block 0 (`0x0000–0x03FF`) is **excluded**: magenta once, so stock writes it at times.
  - Blocks 1–15 (`0x0400–0x3FFF`) are **verified** by the rule above: never magenta or red, and no stock literal uses
    them. Their contents are non-zero, so they were never write-tested on the device. Recorded as opt-in
    (`auto = false`): a feature that uses them asks for them by name and write-tests its block at power-on.
- **For PL01:** the UI task (column 5) has ≥ 1.5 KB free after heavy use, against PL01's ≈ 168 B extra depth. The
  stack gate in PL01's TEST.md is met. Main (column 4) is the same, in case pad handling runs there.
