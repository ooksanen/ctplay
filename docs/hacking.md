# Hacking the Circuit Tracks

What is known about the Novation Circuit Tracks' firmware 1.2.1 (build 4486) and its hardware, in one place. It is
for anyone who patches the device, with CTPlay or without it.

Each item says who found it. "Upstream" is [CIRCUIT-HACKS-RC](https://github.com/Ghillermo/CIRCUIT-HACKS-RC), with
the build that showed it (`SC…`, `RC…`). "CTPlay" is this project, with its build (`SL…`, `PL…`). Upstream's full
research notes are in Spanish: `docs/NOTAS.md` in
[its repository](https://github.com/Ghillermo/CIRCUIT-HACKS-RC/blob/main/docs/NOTAS.md). The English fork,
[ooksanen/CIRCUITS-HACKS-RC](https://github.com/ooksanen/CIRCUITS-HACKS-RC), translates the version list
([`docs/VERSIONS.en.md`](https://github.com/ooksanen/CIRCUITS-HACKS-RC/blob/main/docs/VERSIONS.en.md)): which builds
were confirmed on the device, and which failed there.

Addresses are those of the official firmware 1.2.1 (build 4486). CTPlay's named addresses, each checked against the
stock image on every build, are in [`stock/symbols.toml`](../stock/symbols.toml). The memory CTPlay may use, and how
each region was confirmed, is in [`stock/memory.toml`](../stock/memory.toml). What CTPlay uses of it today is in
[`resources.md`](resources.md).

## Rules that protect the device

- **Never write the internal flash or the option bytes from patch code.** The bootloader (`0x08000000–0x0800FFFF`)
  is never touched. (Upstream.) CTPlay's build refuses any code that reaches the flash controller's registers, the
  option bytes or the flash unlock keys (`playbuild/checks.py`).
- **Recovery:** switch the Circuit Tracks off. Hold **Scales + Preset + Note** and switch it on: this is the
  bootloader. Send the official firmware. (Upstream.) If it does not switch off or start, unplug it and hold the power
  button for 15–30 s first. (CTPlay.)
- **Never take the DSP-service lock from the DSP service tick.** See [The DSP service tick](#the-dsp-service-tick).
- **No long work while a pad is pressed.** See [A phantom press on the next pad](#a-phantom-press-on-the-next-pad).
- **Emulation passing is not device passing.** Several features worked in emulation and failed on the device.
  Diagnostic builds that report through the LEDs or MIDI are how upstream settled those. (Upstream; the version list
  above names them.)

## The platform

- **ARM:** STM32F745 (Cortex-M7). The application starts at `0x08010000`, with images up to 0x70000 B (upstream's
  limit; not verified against the bootloader). The stock image ends at `0x0805CDDC`, so code caves start at
  `0x0805CDE0`. The stack pointer starts at `0x20050000`. (Upstream.)
- **DSP:** a DSP56724: two DSP56300 cores and a shared external SDRAM, with 16 useful bits in each 24-bit word.
  (Upstream.)
- **Pads:** read one at a time through a 74HC4051 8-channel analog multiplexer into the STM32's ADC. (userx14's
  [circuittracksreverseengineering](https://github.com/userx14/circuittracksreverseengineering), its
  `Documentation/Components.md`.)

## The bootloader and the version marker

- The version marker is 6 bytes at offset 0x20 of the version block (`0x1C8`, 0x26 B).
- The bootloader only installs an image whose version block differs from the installed one. Sending the same build
  again does nothing.
- Names are cut to 6 bytes. Two names that share their first 6 characters do not install over each other. This is why
  upstream has `SC32D2`, not `SC32D.2`. (Upstream.)
- Every `.syx` is made by `tools/ct_fw.py`, which writes and checks the CRC. (Upstream.)

## Memory

- **The block heap:** its limit is at `[0x20002B44]` (`0x20044E58`), its current pointer at `[0x20002B48]`
  (`0x20044D68` on the device after boot: 240 B free). The allocator `0x0801D7D8` hits `bkpt` when it runs out and
  never frees. Stock allocates only at boot, so the heap's tail can be reserved. (Upstream; reserved since SC14.)
- **Free RAM above the heap:** `0x20044E58–0x2004F000` (41,384 B) is never used. Stock's own memory report
  (`0x0801D426`) counts it as remaining. (Upstream SC44.2.) Confirmed on the device: filled with a pattern and never
  changed through heavy use and power cycles; the main stack stayed in the top 512 B. (CTPlay SL01D.) Stay below
  `0x2004F000`. RAM is not cleared on every reset: sign what you keep there, or clear it at power-on.
- **ITCM** (the instruction RAM at `0x00000000`): blocks 1–15 (`0x00000400–0x00004000`) are free. Block 0 is not:
  stock writes it at times, most likely through a null pointer. (CTPlay SL00D.) CTPlay write-tests and zeroes its span
  at every power-on and stays off if the test fails (CTPlay PL09, the first ITCM writes on the device).
- **Saved with the project:** the session record's last 1,000 B are saved and loaded with the project, and stock never
  reads or writes them. (Upstream SC402D / SC403D.) A new project clears them. CTPlay keeps its settings there (CTPlay
  PL10; one block with a CRC since PL21). Novation Components' project validator checks only stock's fields, never
  this tail (CTPlay, 2026-11-11, `tests/test_components_validator.py`). The session blocks also have 65 reserved bytes
  (upstream SC182D / SC183D), and the device settings record has 75 free bytes at its end (upstream, since SC20).

## The controller and its routes

- The controller (`MGR`) is at `0x20040B10` (vtable `0x0805A100`). Routes: button press `0x08033320(ctrl, id)` (a
  `tbh` at `0x080333C4`), button release `0x0803381A`, pad `0x08033282`, knob `0x08033848`. (Upstream.)
- The active view is `[ctrl+0x6C]`. Shift is parameter 0 of the store at `[ctrl+0xC]` (read with `param_get`,
  `0x0803542C`). (Upstream.)
- With Shift held, only the buttons in mask `0x07DBBE00` pass (ids 9–13, 15–17, 19, 20, 22–26, and 0x1B). So
  **Shift + Synth 1/2, MIDI 1/2, Drum 1–4, Preset, Mixer and 1-16/17-32 do nothing in stock**: they are free for new
  views. (Upstream.) CTPlay's Play pages use Shift + a track's button (CTPlay PL06).
- Button ids: 0–7 tracks, 8 Preset, 9 Note, 16 Record, 17 Play, 19 / 20 Octave down / up, 21 1-16/17-32, 22
  Tempo/Swing, 23 Clear, 24 Duplicate, 27 Shift. Buttons 13, 14, 15 open views 1, 2 (Mixer, `0x200447D4`) and 3 (FX,
  `0x200443B4`). (Upstream.)
- Identify views and buttons by what the code does with them, not by guessing. Tests go through the real route (the
  controller's press and pad entries), not the handler you think is called. (Upstream.)
- Project parameters (the sends: type 0x20, 0–7 reverb, 11–18 delay; the master: type 0x21, 0 filter, 1 resonance) are
  set through `0x08034D92(this+4, type, index, value)` with `this = [[[0x200069E4]+0x10]]`, the same path MIDI takes.
  (Upstream.)

## The sequencer clock

- Stock's 1 ms dispatcher (`0x0803C410`) runs in the Main task: slot 0 every 1 ms runs the sequencer clock, slot 1
  every 333 ms. It runs with the transport stopped too, before Main takes the DSP lock. (CTPlay, for the strum, PL02.)
- The sequencer ticks at 24 PPQN (`0x0802C418`), only while playing, from the same 1 ms service. Tick 0 of a start
  comes from the start itself. (CTPlay, the arpeggiator, PL06.)

## LEDs

- The LED task (`0x08034196`) reads 42 entries of the active view: 0–31 pads, 32–33 buttons, 34–41 knobs. The panel
  has 69 LEDs: 48 Record, 49 Play, 51 / 52 Octave, 53 1-16/17-32, 55 Clear, 56 Duplicate, 60–67 knobs, 68 the master
  filter. (Upstream.)
- Colours are Novation palette codes (palette `0x08056464`; the RGB table at `0x20003804` is in B, G, R order). Pick
  them, then confirm them on the device. (Upstream.)
- **Stock reads some colours from a palette in RAM**, not the flash one. Clear's blue is 0x07 there, while the flash
  entry 0x46 shows dim red-orange. Compare a chosen code's RGB in emulation with stock's own LEDs. (Upstream SC37.9.)
- **35 codes animate on the device:** the RAM RGB table changes over time, while the emulator's copy is static. Never
  use them for a steady colour: `03 04 05 06 10 11 15 16 19 1A 1B 1C 1D 27 28 2F 30 39 3A 42 43 47 48 4B 4C 4F 50 56
  57 58 59 5A 5B 61 62` (hex). Families run "steady, dim, blink, pulse" (e.g. `49` / `4A` / `4B` / `4C`). Dim white is
  `0x02`, not `0x03`. (Upstream SC38.8 and SC39.5, measured with a diagnostic build.)

## The DSP service tick

- The DSP service tick's chain starts at `0x080213AA`. The main loop holds a semaphore (`[ptr + 0xC]`, taken through
  `0x08021064`) while it runs.
- **From the tick, never call `MARK_DIRTY` (`0x0803BDCC`) or anything else that takes that semaphore: the device hangs
  at power-on, forever.** This froze upstream's SC19, SC19.1, SC19.2 and SC20D. Mark a group with `0x08021FDC(type,
  index)` instead. Write and read the DSP with `0x080292F8` / `0x08029344`. (Upstream SC19.)
- Emulation does not model the hang. Upstream's tests count the semaphore takes. CTPlay tags every stock function
  that takes the lock (`takes_dsp_lock` in `stock/symbols.toml`), and the build refuses a hook in the tick that can
  reach one. (CTPlay, from the foundation.)

## The DSP

- Core 0's program is relocated to the end of the image (upstream SC16); its load table is at `0x08029700`. Write
  from the ARM with `0x080292F8(core, value << 8, addr)`. Program RAM is `P:$0000–$3FFF`. (Upstream.)
- The voice table `X:$EB–$15A`: never touch it. The current voice's synth is `x:$CC`. (Upstream.)
- The hardware stack has 15 levels; stock uses 6. Never nest new `jsr` or `do` above stock's: SC13 hung. (Upstream
  SC13.)
- Core 1 has 2,048 program words and runs the granular synth and the Glitch. Core 0 waits on it, so keep work there in
  short tasks. (Upstream.)
- **Polyphony is limited by DSP time, not by a fixed count.** About 4–5 notes hold with light patches; a new note
  beyond that takes an older voice, on stock too. A heavy patch plays fewer. (CTPlay PL01–PL03D, with a voice-log diagnostic
  build: [`investigations/2026-10-12-chord-voice-dropouts.md`](investigations/2026-10-12-chord-voice-dropouts.md).)

### DSP56300 assembler traps

Each of these bit upstream (CIRCUIT-HACKS-RC):
- `mpy x0,y0,b` assembles to a long form that treats `y0` as **unsigned**. Write `mpy y0,x0,b`. Use the short-form
  operand orders: `mpy y1,x1`, `mpy y1,y0`, `mpy x1,x0`, `mpy x0,y1`, `mpy y0,x0`. `mpy y1,x0` is not legal.
- `and` on a negative accumulator leaves `a2 = $FF`, and `move a,rN` then saturates. Add a constant first to make it
  positive.
- External memory keeps 16 bits per word (the low byte is 0).
- At upstream's DSP hook `P:$23C`, `M0 = $FFFF`: set `M` to linear before buffer code.

## Rate limits

- At most one message per voice to the DSP every 2 ms, plus the heartbeat. (Upstream.)
- MIDI sent from the UI task is cut at 64 messages per press. (Upstream.)

## A phantom press on the next pad

A pattern write with interrupts masked, inside a pad-press handler, made a second press on the next pad (pad + 1) on
the device. Most likely, a delayed scan of the multiplexer stores the held pad's pressure in the next pad's slot (the
exact mechanism is not traced). Emulation cannot show it: the emulator has no pad scanner.

So: on a press, change the setting and its LED only. Do slow or masked work on that pad's release. Keep masked
sections to a few instructions. (CTPlay: seen on PL11 and PL13, fixed in PL13:
[`investigations/2026-10-20-phantom-pad-press.md`](investigations/2026-10-20-phantom-pad-press.md).)

## Stock bugs

- **CC 27 on the project channel crashes stock 1.2.1.** The main loop's master-group send (`0x08021578`) takes a
  fourth word from a 3-entry table and jumps into code. A Circuit Rhythm sends it when its -12 dB trim is toggled.
  (Upstream RC4.20.) CTPlay fixes it with a 2-byte patch at `0x080215B2` (CTPlay PL22, `features/stockfix/`).

## Emulation

- The emulators run the firmware on device RAM and flash dumps (userx14's). The emulated clock does not advance, so
  `sleep()` (`0x0801BE78`) is skipped. (Upstream.)
- DSP `do` loops run in one interpreter step, so a watched address inside a loop shows the `do`'s. (Upstream.)
- Passing in emulation is where a change starts. A device run is where it is settled.
