# RAM above the heap: the SL01D probe — design

Date: 2026-10-20 · Branch: `slim` · Version: `SL01D` (foundation diagnostic) · Status: design, for the user's review.
Settles the first item of `docs/followups.md`, "From upstream RC2–RC2.02 / Beta 3.3".

## Purpose

slim has 240 B of RAM at the end of stock's heap and 15 KB of ITCM. Upstream SC44.2 says the RAM above the heap,
`0x20044E58–0x2004FDFF` (about 44 KB), is free:
- stock's own memory report (`0x0801D426`) counts it as "Remaining", with a 512 B stack above it;
- two RAM dumps of the running firmware still hold the power-on pattern there, up to about `0x2004FC00`;
- no stock literal points inside it (only `0x2004FE00`, in the report).

Nobody has checked this on a device: upstream's builds that use it (RC2.02, Beta 3.3) have not been tested yet. Our
`CLAUDE.md` used to call the range "boot stack". SL01D settles it on the device before CTPlay puts anything there.

The question SL01D answers: **does anything other than slim write to this RAM, at any time, in normal and heavy use?**
And two more that decide how CTPlay would use it:
- **How deep does the main stack (MSP, used by interrupts) reach** from the top of RAM (`0x20050000`)? The dumps
  suggest about 1 KB (to `0x2004FC00`), more than the report's 512 B. This sets the region's top.
- **Does the RAM keep its contents through a power-off, a reset or a firmware install?** If it does, data left from an
  earlier session would look valid, so every block CTPlay keeps there needs a signature, or must be cleared at power-on.

## Goals
- Fill most of the region with a known pattern at the first hook call, and watch it for changes for the whole session.
- Watch the top 4 KB without writing it, to measure the main stack's depth.
- Report everything on the pads, on one page, as SL00D did: the user photographs it after each session.
- Run as stock everywhere else.

## Non-goals
- Using the region in a feature. After a passing run, `stock/memory.toml` gets the region and `CLAUDE.md` is
  corrected; a feature asks for it in a later design.
- The ITCM and stack pages of SL00D: settled already. SL01D has only the new feature.
- Exact addresses over USB SysEx (the `link` feature could carry them). The pad resolution is enough to pick the
  region's top (see Results rule).

## Anti-goals
- **A probe that could corrupt stock.** SL01D writes only where the evidence says nothing ever writes: below
  `0x2004F000`, upstream's own ceiling. Above it, SL01D only reads.
- **A probe that passes by not looking.** A region is free only if SL01D watched it all session, filled with a pattern
  stock would not write by chance. A checksum of the power-on noise alone (as for the ITCM) is not enough here,
  because CTPlay would write the whole region.

## Decisions (my calls; the user reviews this document)

### The two parts of the region
| Part | Range | Size | What SL01D does |
|---|---|---|---|
| Filled | `0x20044E58–0x2004F000` | 41,384 B | Writes a pattern at the first hook call, checks it from then on |
| Watched | `0x2004F000–0x20050000` | 4,096 B | Checksums each 512 B block at the first hook call, re-checks it, never writes |

- `0x20044E58` is the heap's limit after boot (`[0x20002B44]`). slim lowers the limit to reserve its own RAM below it
  (`region.heap_tail`), so the filled part starts right above stock's allocator and above slim's own RAM.
- The filled part crosses into SRAM2 at `0x2004C000` (SRAM1 is `0x20010000–0x2004BFFF`). SRAM2 is a separate bank on
  the STM32F745, a usual place for DMA buffers. The pads show it separately (pads 15–20), so a DMA user there would
  show as a group.
- The MPU is off on the device (PL09's power-on check, `slim_ready`, passed on every boot), so writing cannot fault.

### The pattern
- Each word = its own address XOR a constant (`0x5A1A0B5Eu`, say): stock is very unlikely to write that by chance, and
  it catches aliased or stuck address lines as well as stuck bits (the ITCM write test uses the same idea).
- The pattern does not change between boots, so SL01D can recognise its own fill left over from an earlier session.

### At the first hook call (the feature's `init`)
1. **Carried over?** Count the filled chunks whose words all match the pattern already, before writing anything.
2. **Fill** the filled part.
3. **Read it back.** A chunk with any wrong word is marked failed (red).
4. **Checksum** each block of the watched part.

Timing: 41 KB of writes and reads take well under a millisecond at 216 MHz. Interrupts stay on: nothing in that
range is shared with them, and the watched part is only read.

### While running
- Each LED refresh re-checks **one filled chunk** (2 KB, 512 words) and **one watched block** (512 B), in turn, the
  way SL00D's ITCM page did. A changed chunk or block stays marked (latched) until power-off.
- A filled chunk is "changed" if any word differs from the pattern. A watched block is "changed" if its checksum
  (FNV-1a over the words, as SL00D) differs from the boot value.
- Opening the page re-checks every chunk and block at once, so the photo is current.

### The page: Shift + Drum 4
Shift + Drum 4 toggles the page, as in SL00D (stock ignores Shift + Drum 1–4). Without Shift, Drum 4 is stock's.

| Pads | Show | Colours |
|---|---|---|
| 1–20 | Filled part, 2 KB each from `0x20045000` (pad 1) to `0x2004F000` (pad 20 ends there). Pads 15–20 = SRAM2 | green = pattern intact all session · magenta = changed (something else wrote it) · red = did not read back right after the fill |
| 21 | Filled part, `0x20044E58–0x20045000` (424 B) | as pads 1–20 |
| 22 | off | — |
| 23 | Carried over | cyan = every filled chunk already held the pattern at power-on · dim white = some did · off = none did |
| 24 | slim alive | white = the runtime is initialised (as SL00D's pad 32) |
| 25–32 | Watched part, 512 B each from `0x2004F000` (pad 25) to `0x20050000` (pad 32 ends at the top of RAM) | green = unchanged since boot · magenta = changed (the main stack reached it) |

- Colours: green `0x17`, magenta `0x32`, red `0x53`, white `0x01`, dim white `0x02`, cyan `0x4D`: all steady codes
  already used by slim (`CLAUDE.md`, LEDs; PL08 uses `0x4D`).
- The bottom row reads like a bar: the main stack grows down from pad 32, so a run of magenta pads from pad 32
  leftwards is its depth since boot. Pad 32 is expected magenta (interrupts use it all the time). A magenta pad that
  is not next to the run would mean something other than the stack writes there.

### Budget
About 120 B of slim RAM (20 + 1 chunk states, 8 boot checksums of 4 B, two cursors, the page byte, the carried-over
count), no ITCM, no saved state. SL00D's 104 B shows this fits in the heap tail.

## Build
- New feature `features/diag_upper/` (`diag_upper.c`, `feature.toml`): `init`, a `button_press` hook (Shift + Drum 4)
  and a `led_task` hook, like `diag_ram`.
- `versions/SL01D.toml`: marker `SL01D`, features `["diag_upper"]`. `SL01D` passes `slimbuild/features.py`'s marker
  rule and shares its first 6 bytes with nothing.
- Builds that do not use the feature stay byte-identical (`SL00D`, `PL13`).
- Published as the others: `firmware/SL01D/` (`manifest.json`, `TEST.md`), git tag `SL01D` at the publishing commit
  (pushed with the user's approval), a guard comment in `versions/SL01D.toml`, and `ui-map.md`'s diagnostic row.

## Tests (emulation, `slim/tests/`)
Through the real route (controller `0x08033320` for buttons, the LED task for the pads), as `test_sl00d.py`:
- After the first hook call, every word of the filled part holds the pattern, and nothing outside the two parts
  (and slim's own RAM) changed.
- The page: pads 1–21 green, 22 off, 23 off on a fresh RAM image, 24 white, 25–32 green unless the emulated run
  touched them.
- Change detection: a word written in the filled part by the test turns its pad magenta within 21 LED refreshes and
  at once on opening the page; a write in the watched part does the same for its pad (8 refreshes).
- Read-back failure: a chunk the emulator makes read-only (or a hooked write that drops) shows red.
- Carried over: a RAM image that already holds the pattern in every filled chunk shows cyan; in some chunks, dim
  white.
- Stock behaviour: Drum 4 without Shift selects Drum 4; Shift + Drum 4 in the Synth, Drum, Mixer and FX views toggles
  only the page.
- The DSP-lock check and the stack checks pass (no call takes the DSP lock; the hooks' stack depth is small).

## Device check (`firmware/SL01D/TEST.md`)
Each session ends with a photo of the page (**Shift + Drum 4**). Five sessions, as SL00D:
1. **First boot after flashing.** Expect pads 1–21 green, 24 white, pad 23 off.
2. **Light use:** a pattern plays, a few views.
3. **Heavy use:** load several packs and projects, save a project, play for 10 minutes or more with Master FX and the
   delay, run a Novation Components transfer (back up a pack), send MIDI clock in and out if possible.
4. **Power off and on with the power button.** Note pad 23 before doing anything else.
5. **Unplug, hold the power button for 15–30 s, power on.** Note pad 23.
6. Optional: install the official firmware, power on, then install SL01D again without unplugging; note pad 23 on its
   first boot (cyan = the RAM kept the fill through two installs).
Also note pad 23 on the first boot after installing a firmware.

## Results rule (for `TEST.md`)
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

## Risks and open questions
- **Stock wrote the region only before slim's first hook** (boot). Then the fill overwrites dead data: harmless. Data
  that stock wrote at boot and still reads later would be clobbered; the dumps show the power-on pattern there, so
  stock did not write it at boot either.
- **A DMA buffer at a computed address** (no literal) in SRAM2: the fill would be overwritten (magenta), or, if the
  DMA only reads it, stock would see the pattern instead of its data. The heavy-use session covers the SD card,
  USB and audio paths; a misbehaving device during the run is a result, recovered with the bootloader.
- **The main stack deeper than 4 KB** in some path not exercised: it would reach pad 20 (magenta at its top end). The
  bar's shape tells it apart from a stray write.
- **Emulation does not model interrupts on the MSP**, so the bottom row stays green in emulation; only the device
  measures the stack.
