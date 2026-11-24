# SL01D — device test plan

**What it is:** a diagnostic build. It asks one question: is the RAM above the stock heap (`0x20044E58–0x20050000`,
about 45 KB) really unused? At the first LED refresh it fills `0x20044E58–0x2004F000` (41,384 B) with a known pattern and
then watches it. The top 4 KB (`0x2004F000–0x20050000`) is never written: it is only watched, to show how deep the
main stack reaches. It writes nothing to flash or the SD card. Outside its own 52 B of RAM, the only thing it changes
is the pattern in that region.

It lowers the stock heap limit by slim's RAM, as SL00D. If the heap already reaches slim's RAM at boot, slim stays off.
Then Shift + Drum 4 does nothing (no page opens) and the device runs as stock. That is safe; note it.

## Before you start
0. **Build the firmware:** `cd slim && ../.venv/bin/python -m slimbuild versions/SL01D.toml`. The printed syx sha256 must
   equal `syx_sha256` in `slim/firmware/SL01D/manifest.json`.
1. **Back up the SD card** (projects, packs, samples).
2. Know the way back: unplug the device and hold the power button for 15–30 s. If it still misbehaves, power on holding
   **Scales + Preset + Note**, send `stock/circuittracks-firmware-4486-STOCK.syx` with the uploader (it labels it
   "STOCK Circuit Tracks 1.2.1 (build 4486)"), and confirm with **Play** on the device. Do not unplug or power off while
   it is receiving or installing.
3. Build the uploader: `cd slim && ../.venv/bin/python -m slimbuild.uploader` → `slim/build/ct_uploader.html`.

## Flash
4. Open `slim/build/ct_uploader.html` in Chrome or Edge, pick `slim/build/SL01D/circuittracks-4486-SL01D.syx` (the page
   must show "slim SL01D"), connect the Circuit Tracks, Send, confirm with **Play** on the device.

## Tests
Each session ends with a photo of the page (**Shift + Drum 4**). The page shows at once when you press the combination.
Nothing else on the device changes.

| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Power on normally (first boot after flashing). Before anything else, **Shift + Drum 4** | Boots as usual. Pads 1–21 green, 22 off, **24 white**, 25–32 green except pad 32 (and maybe 31) magenta. Pad 23 should be off (it is off if the RAM was not holding the pattern); note it | 1-21 green, 22-23 off, 24 white, 25-31 green, 32 magenta |
| 1b | Photograph the pads | — | photo: `20261028_211405044.JPG` |
| 2 | **Shift + Drum 4** again | The page closes; the view's own pads come back | |
| 3 | Press **Drum 4** without Shift | Drum 4 is selected, as stock | |
| 3b | In the Mixer and FX views, press **Shift + Drum 4** twice | Only the page toggles; no track selection, no view change, no sound change. Also try it in the Synth and Drum views | |
| 4 | **Light use:** play a pattern, open a few views. **Shift + Drum 4**, photograph | Pads 1–21 still green | photo: `20261028_211639284.JPG` |
| 5 | **Heavy use:** load several packs and projects, save a project, play for 10 minutes or more with Master FX and the delay, run a Novation Components transfer (back up a pack), send MIDI clock in and out if you can. **Shift + Drum 4**, photograph | Pads 1–21 still green; the bottom row shows the stack depth | photo: `20261028_212930605.JPG` |
| 6 | **Power off and on with the power button.** Before anything else, **Shift + Drum 4**. Note pad 23, photograph | Pad 23 is cyan, dim white or off (see below) | photo: `20261028_213028423.JPG` |
| 7 | **Unplug, hold the power button for 15–30 s, power on.** Before anything else, **Shift + Drum 4**. Note pad 23, photograph | As step 6 | photo: `20261028_213208077.JPG` |
| 8 | After step 7, use the device normally for a minute, then **Shift + Drum 4** and photograph | Pads 1–21 green | photo: `20261028_213715406.JPG` |
| 9 | Optional: install the official firmware, power on, then install SL01D again without unplugging. Note pad 23 on its first boot | Cyan = the RAM kept the fill through two installs | |

What the LEDs show and do not show:
- The colours are steady. They show a state, not activity. A change is **latched**: once a pad is magenta or red it
  stays so until power-off, even if the memory was put back.
- Opening the page re-checks every chunk and block first, so the photo is current. While the page is closed, slim
  checks one chunk and one block per LED refresh.
- The LEDs do not tell you what wrote to a magenta pad. They only say it was not slim.

Pad 1 is top left; rows are pads 1–8, 9–16, 17–24, 25–32 (the bottom row).

Pad legend (pads 1–20 = chunks of 2 KB, pad 21 = 424 B, pads 25–32 = blocks of 512 B):

| Pads | Show | Colours |
|---|---|---|
| 1–20 | Filled part, 2 KB each from `0x20045000` (pad 1 = `0x20045000–0x200457FF`) to `0x2004F000` (pad 20 ends there). Pads 15–20 are SRAM2 (from `0x2004C000`) | **green** = the pattern is intact all session; **magenta** = changed since (something else wrote it); **red** = did not read back right after the fill |
| 21 | Filled part, `0x20044E58–0x20044FFF` (424 B) | as pads 1–20 |
| 22 | off | — |
| 23 | Carried over: what the RAM held at power-on, before the fill | **cyan** = all 21 chunks already held the pattern; **dim white** = 1–20 of them did; **off** = none did |
| 24 | slim alive | **white** = the runtime is initialised |
| 25–32 | Watched part, 512 B each from `0x2004F000` (pad 25) to `0x20050000` (pad 32 ends at the top of RAM). Never written by slim | **green** = unchanged since boot; **magenta** = changed (the main stack reached it) |

- The bottom row reads like a bar. The main stack grows down from pad 32, so a run of magenta pads from pad 32 to the
  left is its depth since boot. Pad 32 is expected magenta (interrupts use it all the time). A magenta pad that is not
  next to the run means something other than the stack writes there.
- Pad 23 cyan after a power-off means the RAM kept its data through that power-off. Dim white is partial: note it.

If the device misbehaves at any step: note what you saw, then recover as in step 2 of "Before you start".

## Results (fill in)
Rule:
- **The filled part is free** if pads 1–21 were green in every photo (never magenta or red) and slim's own scan of
  the stock image finds no literal into `0x20044E58–0x2004F000` (see `tests/test_upper_ram_static.py` and the "found
  before the run" paragraph), and nothing odd happened on the device in any session (sound, SD card, USB, views). A
  clobbered stock buffer would only show as misbehaviour.
- **The region's top:** the start of the leftmost magenta pad of the bottom row (it starts at `0x2004F000 + 512 × (pad − 25)`), minus 1 KB of margin, and never above
  `0x2004F000`. With the dumps' 1 KB stack (pads 31–32 magenta) the top stays `0x2004F000`.
- **Signatures:** pad 23 cyan in session 4 or 5 = the RAM keeps data through that kind of power-off. Dim white =
  partial: note it. It can mean partial retention, or stock writing part of the region at boot; it leads to a
  follow-up, not to "keeps data". A feature that uses the region signs its block or clears it at power-on in every
  case (as `slim_ready` zeroes the ITCM span), because RAM is not cleared at power-on.
- **Pad 23 off in sessions 4 and 5 does not mean the RAM is cleared.** A reset without power loss is not tested by
  them, so a feature that uses the region still signs its block or clears it at power-on.
- **If any of pads 1–21 is magenta:** that chunk is excluded, with its neighbours, until a second run explains it.
- A passing run adds `region.above_heap` (`kind = "ram"`, `confidence = "verified"`, `auto = false`) to
  `stock/memory.toml` and marks the line in `CLAUDE.md` (Platform summary, block heap) confirmed.

("Session 4 or 5" in the rule means the power-off sessions: steps 6 and 7 above.)

Found before the run (static scan of the stock image, Task 1): no PC-relative `LDR` literal and no `MOVW` / `MOVT`
pair points into `0x20044E58–0x2004F000`. In `0x2004F000–0x20050000` only two addresses are read by PC-relative
loads: `0x2004FE00` (literal at image offset `0xD70C`, stock's memory report) and `0x20050000` (the initial stack
pointer, offset `0x29458`).

- **Date:** 2026-10-28. **Passed.**
- **Firmware:** SL01D, syx sha256 `80435440…da44b` (the published manifest); the uploader showed: slim SL01D.
- **Photos:** six, in `firmware/SL01D/photos/` (gitignored, local only); all six show the same page:
  - step 1b: `20261028_211405044.JPG`
  - step 4: `20261028_211639284.JPG`
  - step 5: `20261028_212930605.JPG`
  - step 6: `20261028_213028423.JPG`
  - step 7: `20261028_213208077.JPG`
  - step 8: `20261028_213715406.JPG`
- **Pads 1–21 (all photos):** green in every photo. Never magenta or red.
- **Bottom row (pads 25–32) per session:** pads 25–31 green, pad 32 magenta in every photo. The main stack stayed in
  the top 512 B (`0x2004FE00–0x20050000`) all the time: stock's own memory report allows a 512 B stack there too.
- **Pad 23 per session (first boot, step 6, step 7, optional step 9):** off, off, off; step 9 not run. The RAM did
  not keep the fill through a power-off with the power button or through unplugging. That does not mean it is
  cleared on every reset (see the rule), so a block kept there still needs a signature or a clear at power-on.
- **Anything odd on the device:** nothing. Pad 22 off and pad 24 white in every photo.
- **Conclusion for `slim/stock/memory.toml`:** `region.above_heap` = `0x20044E58–0x2004F000` (41,384 B),
  `kind = "ram"`, `confidence = "verified"`, `auto = false`. The top stays `0x2004F000`: the leftmost magenta pad is
  32, so the rule gives `0x2004FE00` − 1 KB = `0x2004FA00`, capped at `0x2004F000`.
