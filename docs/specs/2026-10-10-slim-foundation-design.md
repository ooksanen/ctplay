# Slim foundation — design

Date: 2026-10-10 · Branch: `slim` · Status: draft for review

## Purpose

`slim` is a focused firmware mod for the Novation Circuit Tracks (official firmware 1.2.1 build 4486), derived from
upstream CIRCUITS-HACKS-RC. Upstream's features are stacked: each later feature asserts that the earlier ones are present
(e.g. the granular synth requires the VA-drum, the step-drummer, CC / NRPN I/O, the dual-oscillator UI and the CC editor),
328 stock addresses are written out by hand across modules, and saved state is packed by hand. Features cannot be
combined freely and almost no resources are left in RC0.2.

This spec covers the **foundation**: the build system, hook mechanism, resource placement, save format and tests that
let features be written in C as independent units, proven end to end by one diagnostic build, `SL00D`. Porting real
features is out of scope; it follows the user's feature list, one feature per later spec.

**Audience:** the user (maintainer, new to C and Thumb) and later contributors. Readability and safety rank above
code size.

## Constraints

- Device safety is non-negotiable: never write the internal flash or option bytes; the bootloader
  (`0x08000000–0x0800FFFF`) is never touched; recovery is Scales + Preset + Note at power-on.
- Nothing reaches the device without passing the build checks and emulation tests. Emulation passing is not device
  passing: every build gets an on-device test plan.
- Builds are byte-reproducible.
- Upstream's builds are the reference for ported behaviour.
- Version markers use the prefix `SL`, so they can never collide with upstream's `SC` / `RC` markers. (2026-10-11: the
  product builds are named CTPlay and use `PL`; `SL` stays for foundation diagnostics such as `SL00D`.)

## Decisions

| # | Decision | Reason |
|---|---|---|
| D1 | ARM side in **C**; DSP side stays DSP56300 assembly | Readability for the maintainer; DSP code is hand-tuned and fits in assembly |
| D2 | Approach A: foundation first, proven by the diagnostic build `SL00D` | Independent of the feature list; one device flash tests the whole pipeline and answers the ITCM question |
| D3 | Everything `slim`-specific lives under `slim/`; upstream's `tools/` is reused, not edited | Keeps the merge from `main` and the boundary clear |
| D4 | Old versions are reproduced from **git tags**, not by never editing code | Lets code improve; `manifest.json` records the inputs |
| D5 | Toolchain: Arm GNU Toolchain release archive pinned by version and SHA-256, fetched into `ext/` | Identical compiler binaries everywhere, so identical bytes; distro packages differ |
| D6 | Integer-only, soft-float C; no C standard library | Stock tasks may not save FPU registers; avoid hidden dependencies |

## 1. Layout and build flow

```
slim/
  stock/symbols.toml        named stock addresses: kind (function / data / hook point / vtable slot), expected bytes,
                            original instructions, C prototype, tags (e.g. takes_dsp_lock, context = dsp_tick),
                            notes, provenance (upstream module / NOTAS section)
  stock/memory.toml         usable regions with size, source and confidence (section 3)
  features/<name>/
    feature.toml            hooks, RAM / DSP needs, saved fields, dependencies, stack limits
    *.c, *.h                ARM side
    *.asm                   DSP side, if any
  versions/<NAME>.toml      a version = marker name + feature list (+ options)
  slimbuild/                the build tool (Python): one tool for every version
  tests/                    harness, per-feature tests, comparison tests, build-check tests
  docs/                     specs, per-version TEST.md
  save_layout.lock          committed record of saved-field positions (section 3)
```

**Build flow** (`python -m slimbuild versions/SL00D.toml`):
1. Load the stock image (`stock/circuittracks-firmware-4486-STOCK.bin`, SHA-256 checked as upstream does).
2. Check every symbol in `symbols.toml` against the stock bytes; fail on any mismatch.
3. Resolve the version's features and dependencies; fail on a missing dependency or a conflicting exclusive hook.
4. Place resources (section 3) and generate: `stock.h` (prototypes + `extern` data), the linker script (stock symbols at
   absolute addresses, Thumb functions with bit 0 set; our sections after the stock image and in the assigned RAM
   regions), the hook stubs (section 2) and the boot code.
5. Compile and link with the pinned GCC; run the build checks (section 4).
6. Assemble DSP code with upstream's `dsp56.py` / `dsptool`, when a feature has any.
7. Write the image: patch sites, appended code, the version block marker. Encode with `tools/ct_fw.py`. Write `.bin`,
   `.syx` and `manifest.json` (marker, image and syx SHA-256, CRC, toolchain version, feature list, resource report).

**Reused from upstream, unchanged:** `tools/ct_fw.py`, the emulator base classes (`tools/emu_sc05.py` `E` and
descendants as needed), `tools/dsp56.py` / `dsptool`, `tools/setup_dev.py` (extended by a `slim` setup step for the
toolchain), `re/app.asm`.

## 2. Hooks and calls between C and stock

### Hook kinds

| Kind | Patched | Handler signature | Notes |
|---|---|---|---|
| `entry` | the first instruction(s) of a stock function → a branch to a generated stub | the function's arguments; returns `PASS` (continue into stock) or `HANDLED` (return to the caller with the handler's result) | Preferred: registers follow the calling convention |
| `vtable` | one function pointer in a stock vtable | the slot's signature plus `orig`, the previous pointer | |
| `call` | one `bl` call site | the callee's signature plus `orig` | |
| `mid` | an instruction inside a function | `struct regs *` (r0–r12, lr, flags), readable and writable | Allowed, flagged as risky in review. An instruction inside an IT block (whose `it` precedes the displaced range) must also be refused, like the PC-dependent ones below: required before `mid` hooks exist. **Built in PL16** (`rec_quant`): `slim_regs_t *` (`slim.h`); the stub runs the displaced instructions first, then every handler (void, in priority order); IT blocks refused from upstream's listing |

- **One stub per hooked location.** When several features hook the same location, `slimbuild` generates a single stub
  that calls their handlers in the order set by each feature's declared `priority` (ties broken by feature name, so the
  order is deterministic) and stops at the first `HANDLED`.
- **Displaced instructions.** For `entry` and `mid` hooks, the instructions overwritten by the branch are re-executed by
  the stub. The build refuses any displaced instruction that depends on the program counter (branches, `ldr [pc]`,
  `adr`, `cbz` / `cbnz`, `tbb` / `tbh`) unless `slimbuild` has an explicit relocation rule for it.
- Patch sites, stub addresses and displaced instructions are listed in `manifest.json`.

### Calling stock from C

`stock.h` is generated from `symbols.toml`: functions get prototypes (`int param_get(void *this, int kind);`), data gets
`extern` declarations. The linker script defines each symbol's address. Prototypes are documented in `symbols.toml`;
the first entries come from upstream's code and notes.

### Compiler settings

`-mcpu=cortex-m7 -mthumb -mfloat-abi=soft -Os -ffreestanding -nostdlib -fno-common -ffunction-sections
-fdata-sections -fstack-usage -fcallgraph-info=su -fno-strict-aliasing -Wdate-time -Wall -Wextra -Werror`, plus `-Wstack-usage=<n>` per hook from
`feature.toml`. `memcpy` / `memset` are our own small implementations (or stock's, once identified in `symbols.toml`). `-fno-strict-aliasing` because we cast into stock structures; `-Wdate-time` because `__DATE__` / `__TIME__` would break reproducible builds.

### Boot

A `boot` hook runs once after stock's start-up allocations:
1. **RAM reservation** (upstream SC14 model): our RAM area is placed at a fixed address directly below the heap limit
   (`[0x20002B44]` = `0x20044E58`). The boot code checks that the heap's current pointer (`[0x20002B48]`) is at or below
   the start of our area, then lowers the limit to that start. If stock has already allocated into it, **all features
   stay disabled** and the device runs as stock.
2. C start-up: zero `.bss`, copy `.data`.
3. Each enabled feature's `init()`, in dependency order.

The exact stock routine to hook for boot is an open item (O1).

## 3. Memory, placement and saved state

### Resource map: `slim/stock/memory.toml`

| Region | Size | Source | Confidence |
|---|---|---|---|
| Flash after the stock image `0x0805CDE0–0x0807FFFF` | ~140 KB | bootloader limit 0x70000 B; no stock literal points there (upstream NOTAS) | verified |
| RAM below the heap limit (reserved at boot, section 2) | 240 B (device value of limit − current) | upstream SC14+ on the device | verified |
| Project reserved bytes in the session blocks | 65 B, saved | upstream SC182D / SC183D diagnostics | verified |
| End of the device settings record | 75 B, saved | upstream SC20+ | verified |
| ITCM `0x00000000–0x00003FFF` | up to 16 KB | — | unknown → `SL00D` |
| Backup SRAM `0x40024000–0x40024FFF` | 4 KB | stock passes it as a USB transfer buffer (literals at `0x08026F18`, `0x0803B788`; 0x1000-byte chunks) | excluded |
| DSP core 0 X / Y / P, core 1 P / X / Y, external SDRAM zones | per upstream `docs/RECURSOS.md` | upstream SC21D, SC35D-series | verified |

Confidence levels: `verified` (tested on a device), `static` (code analysis only), `unknown`, `excluded`. Features are
placed only in `verified` regions unless a feature explicitly opts in to `static`.

### Placement

A feature declares what it needs, e.g. `ram = { state = 24 }`, `flash_data = …`, `dsp = { x = 64, ext = 0x20000 }`.
`slimbuild` assigns addresses, emits linker sections and DSP symbols, and fails the build if a region overflows. Every
build prints and stores (in `manifest.json`) a budget report: used / free per region.

### Saved state

- Fields are declared per feature: `{ name, bits, default, store = "project" | "device" }`.
- `slim/save_layout.lock` (committed) records each field's position the first time a build includes it. Later builds
  keep that position, so adding a feature never moves existing fields. Retired fields stay in `save_layout.lock` as
  tombstones; reusing their bits requires a new layout ID.
- Each store starts with a layout ID and a check value. On mismatch (another layout, upstream data, a blank project)
  every field loads its default. The layout ID changes only on a deliberate incompatible change, which the build reports.
- The stock load / save / new-project hook points come from upstream `persist19` (`0x0802F5B8`, `0x0802F5FA`,
  `0x0802FE5E`) and are re-verified when this part is implemented.

### Staging

`SL00D` uses flash, RAM and boot only. Saved state and DSP placement are designed here but **implemented with the first
feature that needs them**, and tested against that real case.

## RAM: the defining constraint

slim's RAM is 240 B (heap limit − heap current after boot); every feature's state, `.data` and `.bss` share it. Plan B,
decided by SL00D's results:
- (a) **ITCM**, only if no magenta/red on the device and no stock reference.
- (b) **Trim oversized RTOS task stacks.** The RAM dump shows ≈ 8 KB of never-used stack fill (0xA5) in 8 runs. Measure the
  high-water marks on the device (SL00D stack page) under heavy use, then patch the stack sizes where stock creates its
  tasks (0x0801C91C), keeping a margin.
- (c) **Bulk data in the DSP's external SDRAM** (regions in `memory.toml`).
- (d) Otherwise a hard cap on features.

Above the heap limit is not free: the RAM dump shows stock data and the boot stack there, and upstream SC13 hung using it.

## 4. Testing

### Build checks (every build)

| Check | Fails when |
|---|---|
| Symbols | a stock byte sequence in `symbols.toml` does not match the stock image |
| Displaced instructions | a PC-dependent instruction would be displaced without a relocation rule |
| DSP lock | the compiled call graph lets a handler at a `context = dsp_tick` hook point reach a `takes_dsp_lock` function |
| Flash safety | compiled code contains a literal in the flash interface (`0x40023C00–0x40023FFF`) or option-byte (`0x1FFF0000–0x1FFFFFFF`) ranges |
| Stack | a handler exceeds its declared stack limit |
| Budget | a region overflows |
| Marker | the 6-byte marker equals one of upstream's or an earlier `slim` build's markers |
| Reproducibility | two builds of the same version differ |

Each check has a test with a deliberately bad fixture that must make the build fail.

Limit of the DSP-lock check: it sees our call graph, not stock's. A stock function must carry `takes_dsp_lock` if it
takes the lock **directly or through anything it calls**; the first entries (`0x0803BDCC` `MARK_DIRTY`, `0x08021064`)
come from upstream's notes, and the emulation harness's lock count stays as the second line of defence.

### Emulation harness: `slim/tests/harness.py`

Built on upstream's Unicorn setup (stock flash with our image + the device RAM snapshot
`ctre/Firmware-Analysis/ram_dump_firmware_0x08037988.bin`). The snapshot is taken after boot, so the harness runs our
boot routine explicitly. API: `press(button)`, `release(button)`, `pad(n)`, `knob(k, delta)`, `leds()`, plus captured
DSP writes (`0x080292F8`), MIDI output and a count of DSP-lock acquisitions (`0x08021064`). Input goes through the real
controller routes (`0x08033320` press, `0x0803381A` release, `0x08033282` pad, `0x08033848` knob).

### Comparison tests

The same input script runs against two images and the outputs in a declared scope are compared.
- **Transparency test (foundation):** stock vs. a test-only version (`slim/versions/test/null.toml`, never flashed) that
  installs every `SL00D` hook with handlers that always return `PASS`, under a long seeded random script of buttons, pads and knobs: LED output, DSP writes and MIDI must be
  identical.
- Feature ports compare against the upstream build that introduced the behaviour.

Future work: per-hook instruction budgets measured in emulation (Unicorn counts instructions), starting with the first
`dsp_tick` hook.

### On the device

Each build gets `slim/docs/<version>/TEST.md`: steps, expected results, a place for the user's results. Device results
update `memory.toml` and the version's notes.

## 5. The `SL00D` diagnostic build

Marker `SL00D`. Purpose: prove the C pipeline on the device, decide the ITCM's status and measure the RTOS stack headroom. One feature (`diag_ram`), two pages: **Shift + Drum 4** = ITCM page, **Shift + Drum 3** = stack page (read-only; each of 8 columns is a fixed task stack, whose base address is taken from the RAM dump and checked at the first hook call: green pads up to 512 B each, white top > 2 KB, single red < 128 B, off = stack fully used, magenta = layout differs from the dump). Pressing the same combination again turns the page off.

| Part | Hook | Behaviour |
|---|---|---|
| Boot | `boot` | RAM reservation, C start-up, store a checksum of each 1 KB ITCM block (16 × 4 B), set the "C alive" flag |
| Trigger | `entry` on the button handler `0x08033320` | **Shift + Drum 4 / Drum 3** switch the diagnostic pages, return `HANDLED`; everything else `PASS`. Stock discards Shift + Drum 1–4 at the entry of this function, so stock behaviour is unchanged |
| Display | hook on the LED task `0x08034196` (kind decided in O2) | ITCM page: pads 1–16 show the 16 ITCM blocks, pad 32 = C alive; stack page: pads 1–32 are 8 columns of unused stack |
| Probe | — | on each trigger: re-checksum each block, and write-test one word per block with interrupts masked (read, write pattern, read back, restore); non-zero blocks and the vector-table block are never written |

Pad colours (ITCM page): green = zero, unchanged and writable; yellow = non-zero (not write-tested: code, tables or
never-initialised RAM) or the block holding the vector table; magenta = changed since boot (used by stock); red = a zero block whose test word did not read back. Colour codes are picked from the
stock palette and confirmed on the device.

It writes nothing to flash or the SD card and leaves no RAM change outside its own area. The ITCM write test restores
every word it touches.

Device test plan (in `TEST.md`): back up the SD card; flash; check normal boot; trigger and photograph; play a pattern,
load a project, run a Components transfer; trigger again and photograph; reboot to the official firmware if anything
misbehaves.

## Success criteria

1. `SL00D` builds from a fresh clone, twice with identical output.
2. Every build check is implemented, with a passing test and a failing fixture.
3. The transparency test passes.
4. The `SL00D` emulation test passes (boot, trigger, display, probe code path).
5. `slim/docs/SL00D/TEST.md` is written.
6. After the user's device run, `memory.toml` records the ITCM result.

## Open items (resolved during implementation, each with evidence)

| # | Item | Plan |
|---|---|---|
| O1 | Stock routine for the `boot` hook | Candidates: upstream SC14's first-use path and `persist19` load hooks; must run after stock's boot allocations and before any of our handlers |
| O2 | LED-task hook kind (`entry`, `vtable` or `call`) | Read `0x08034196` and upstream `leds18` / `build_sc17` |
| O3 | Button id of Drum 4 and the Shift test | Confirm in emulation (ids 0–8 are track buttons; Shift = p0 of `[ctrl+0xC]`) |
| O4 | Exact Arm GNU Toolchain release and SHA-256 | A release at least two weeks old; recorded in the setup step and `manifest.json` |
| O5 | Palette codes for the four probe colours | From upstream's confirmed codes (e.g. red `0x53`) |

## Not in scope

Porting any upstream feature; saved-state and DSP placement implementation (designed only); changes to upstream's
`tools/`; publishing builds.
