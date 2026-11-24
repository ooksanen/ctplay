# ITCM opt-in: a second RAM region for features — design

Date: 2026-10-17 · Branch: `slim` · Version: first used by the build after `PL08` (`PL09`) · Status: design
suggestion, for the user's review. Closes the ITCM items in `docs/followups.md` (lines 19–22, 122).

## Purpose

PL08 uses 236 of the 240 B slim reserves at the end of stock's heap (`firmware/PL08/manifest.json`, `ram.used`).
Saved settings, a Euclidean generator or more pages each need state. SL00D verified the ITCM blocks 1–15
(`0x0400–0x3FFF`, 15,360 B) on the device: never changed after boot in 3 boots of light and heavy use
(`stock/memory.toml` region `itcm`, `auto = false`; `firmware/SL00D/TEST.md`). This design lets a feature ask for
that region by name and turns slim on only after a power-on write test of the bytes it will use.

Goals:
- A feature declares an ITCM budget in `feature.toml` and marks the variables that live there; the build places,
  counts and checks them.
- slim tests and zeroes its ITCM span at the first hook call. If the test fails, slim stays off and the device runs
  as stock.
- Builds that do not ask for ITCM stay byte-identical (SL00D, PL08).

Non-goals: code in ITCM (it would run faster, but nothing needs that), initialised data in ITCM (zero-init only),
block 0 (`0x0000–0x03FF`, excluded: stock writes it at times), backup SRAM (excluded: USB buffer).

## Decisions (my calls; the user reviews this document)

| # | Decision |
|---|---|
| D1 | **Move the chord engine's three big arrays to ITCM in PL09, and put new features' larger state there by default.** PL08's biggest variables (manifest symbols): `held` 84 B (`features/chord/chord.c:96`), `run` 64 B (`arp.c:31`), `mono_visit` 16 B (`mono.c:35`) = **164 B**. Moving them leaves the pool at ~72 B used, **~168 B free**; ITCM use is 164 of 15,360 B. The rest of chord (≈58 B of small flags and settings) and countin (7 B) stay where they are. A side benefit: chord + the voice log (136 B) fit again in a diagnostic twin (followups, PL06 review). Keeping chord in the pool and using ITCM only for new features would leave 4 B for any chord change |
| D2 | **Zero-init only.** Variables go in sections named `.bss.itcm.<name>`, through a macro in `runtime/slim.h`: `#define SLIM_ITCM(n) __attribute__((section(".bss.itcm." #n)))`. GCC marks such a section NOBITS and **refuses an initialiser** ("only zero initializers are allowed in section '.bss.itcm.c'": checked with the pinned GCC 14.2, scratch spike). Defaults that are not zero are set in `init()`, as `mono.c:40` already does |
| D3 | **Budget**: `[budget] itcm = 164` in `feature.toml`. The key names the `memory.toml` region; the build refuses it unless that region is `kind = "ram"`, `confidence = "verified"`, `auto = false`. Only `itcm` exists today; whether the code is keyed by any region name or by `itcm` alone is the builder's call |
| D4 | **Placement top-down** in `0x0400–0x4000`, like the heap tail (`memory.place_top_down`, two link passes as `build.py:37-42`): PL09's span ≈ `0x3F58–0x4000`, as far as possible from block 0, the block stock's null-pointer-like writes hit |
| D5 | **Write test of slim's own span only**, at the claim in `slim_ready` (`runtime/slim_rt.c:41-62`), after the heap tail is zeroed and before `slim_features_init()`. It does not restore old contents: stock never uses the span (no literal points there; SL00D saw it unchanged), so slim owns it |
| D6 | **Failure = slim off**, the same path as today's "the heap already reaches slim's RAM": `slim_inited` stays 0, so every dispatcher passes to stock for the whole boot. No per-feature gating (would add code to every dispatcher of every opted-in build for a case not expected to happen) |
| D7 | **Opted-out builds unchanged**: every builder / runtime addition is emitted only when some feature in the version has an ITCM budget > 0 |

## Build changes (`slimbuild/`)

- `features.py:56`: `Feature` gains `itcm_budget` (default 0) from `budget.get("itcm", 0)`.
- `memory.py`: a `named(regions, "itcm")` lookup beside `pick` (`memory.py:47`, which skips `auto = false` regions
  and stays as it is) with the D3 checks.
- `codegen.linker_script` (`codegen.py:158`): when ITCM is used, add `ITCM (rw) : ORIGIN = …, LENGTH = …` to
  `MEMORY` and, **before** `.data` (ld assigns an input section to the first statement that matches it, and `.bss`'s
  `*(.bss .bss.* COMMON)` at `codegen.py:191` would otherwise take it):
  `.itcm (NOLOAD) : { __slim_itcm_start = .; *(.bss.itcm.*) . = ALIGN(4); __slim_itcm_end = .; } > ITCM`.
  Without ITCM the script text is exactly today's (unit test on the string).
- `compile.object_ram` (`compile.py:64-70`) counts every `.bss*` section, so it must skip `.bss.itcm.*`; a twin
  `object_itcm` sums them; `checks.check_ram_budget` (`checks.py:201`) checks both budgets.
- A new check refuses any `.bss.itcm.*` section in a feature without an ITCM budget, and in `_runtime` / `_gen`: in a
  build without the `.itcm` statement those sections would silently land in the heap tail via `.bss.*`.
- `build.py`: measure the span in pass 1, place it in pass 2; the manifest gains `itcm = {start, end, used, size}`
  only when used, and the symbol filter (`build.py:63`) also keeps symbols in the ITCM span: the tests look up
  `held` through it (`tests/test_chord.py:37`, `test_arp.py:357`, `test_voice_room.py:241`).
- The runtime is compiled with `-DSLIM_USE_ITCM` only when used (per-group flags in `compile_sources`); `slim_rt.c`
  holds the test under `#if SLIM_USE_ITCM`. slim builds without `-g` and discards `.debug*`, so the added lines do not
  change opted-out objects; `test_published_versions_rebuild_identically` (`tests/test_build.py:60`) proves it.

## Initialisation and the write test

SL00D found every ITCM block non-zero at boot (all yellow, `firmware/SL00D/TEST.md`), so the span must be zeroed;
the heap tail's `.bss` is zeroed in the same claim (`slim_rt.c:55`). In the claim branch, under the existing PRIMASK
section (`slim_rt.c:50`), right after the `memset`:

1. write each word `w` of `[__slim_itcm_start, __slim_itcm_end)` with `addr ^ 0x5A5AA5A5`, then read them all back
   (an address-dependent pattern catches aliasing as well as stuck bits);
2. the same with the complement;
3. write 0 and read back 0.

Volatile word loops, ~41 words in PL09: a few hundred cycles. On any mismatch: return 0 without running
`slim_features_init()` (D6). The span then holds test patterns, which nothing reads. `hook_stack` in the manifest
already counts `slim_ready` (`checks.py`, `hook_stack`).

All hook contexts are tasks (`stock/symbols.toml`: `ui`, `main`, `dsp_locked`), no interrupt handler, and the claim
is single-shot: a second task entering `slim_ready` meanwhile sees `heap_limit == start` and gets `slim_inited` = 0,
so nothing reads the span before it is zeroed. PRIMASK is kept only to make the window short; it does not stop DMA.

## DMA, caches, MPU

- **Can DMA reach ITCM on the STM32F745?** From memory of RM0385 (§2.1, bus matrix; §2.3, embedded SRAM): DMA1 /
  DMA2 / the other bus masters reach the TCMs only through the Cortex-M7 **AHBS** slave port, and RM0385 describes the
  DTCM as reachable that way but the **ITCM-RAM as CPU-only**. I am not certain of that wording: the Cortex-M7's AHBS
  can address both TCMs, and AN4667 may describe ITCM access through AHBS. **Treat DMA into ITCM as possible**; the
  safety argument below does not depend on it.
- **Stock's DMA**: a HAL-style driver: stream table at `0x0801C374–0x0801C3B4` (DMA1 `0x40026010…`, DMA2
  `0x40026410…`); M0AR is written at `0x0801C128` (start helper `0x0801C072`) and `0x0801C2EA` (`0x0801C270`), M1AR
  at `0x0801C36C` (`0x0801C2F0`, double buffer). Their callers (`0x0801B550`, `0x0801EF8A`, `0x0801F026`,
  `0x08025AA2/AC`, `0x08026F64/6C` (USB, next to the backup-SRAM literal `0x08026F18`), `0x08037468–0x08037836`) pass
  memory addresses from handle fields and arguments, never a literal. No literal in the image is in
  `0x0000_0400–0x0000_3FFF` (`memory.toml`, slim analysis 2026-10-10). I did not trace every pointer. An emulation
  spike over the harness routes (stock image, pads, buttons, LEDs, 220 ms of heartbeat) saw **no DMA register write
  and no ITCM write at all**: stock's DMA is set up in tasks and at boot, which the harness does not run.
- **Why that is enough**: a stock DMA into slim's span would also be a stock write there, and SL00D saw none in
  blocks 1–15 over three boots, heavy use included. Block 0 changing once fits a short write through a null
  pointer, CPU or DMA (`M0AR = 0`). A long one would reach `0x0400`, which is why D4 places slim at the top. A DMA write
  during the test fails it (slim off, safe); one after it would corrupt slim's state, the same risk as stock writing the
  heap tail, and the device check below watches for it. The followups' window note (line 122) was about SL00D's probe
  restoring stock-owned words; with D5 slim restores nothing, so it no longer applies.
- **Caches / MPU**: TCM accesses never go through the L1 caches, so there is nothing to clean or invalidate. Stock
  has no literal for the MPU registers (`0xE000ED90–0xE000EDBF`), CCR (`0xE000ED14`) or cache maintenance
  (`0xE000EF50–0xE000EF78`); its SCS literals are NVIC, SysTick, AIRCR, VTOR, CPACR, FPCCR (scan of the stock `.bin`).
  Setting them up via a base register plus an offset is not ruled out. SL00D read every block on the device but
  **never wrote one** (all were non-zero, and its probe writes only zero blocks: `diag_ram.c`, `block_writable`), so
  PL09 is the first ITCM write on the device. An MPU making the ITCM read-only would fault at the first hook; the
  `MPU_CTRL` guard (Risks) keeps slim off instead.

## Tests (emulation, `slim/tests/`)

The upstream emulator maps `0x0–0x100000` as zeroed RAM (`tools/emu_sc05.py:24`), unlike the device, so every ITCM
test first fills `0x0400–0x3FFF` with a non-zero pattern.
- **Builder** (fast): fixture feature with `itcm = 8` (`tests/fixtures/features/`): its variable lands at the top of
  `0x400–0x4000`, the manifest has `itcm`, its RAM budget excludes it; refusals: `.bss.itcm.*` without a budget,
  budget over, region not `auto = false` / not verified, an initialiser (compile error); `linker_script` text without
  ITCM equals today's; SL00D / PL08 rebuild identically (existing test).
- **Runtime** (emu, fixture build): after the first hook call the span is zero and `init()`'s values are there; slim
  is on. A `UC_HOOK_MEM_WRITE` over `0x0–0x3FFF` records no write outside the span.
- **Failure**: a `UC_HOOK_MEM_READ` on one span word that corrupts it before each read (the trick the harness uses for
  SPI2's status, `tests/harness.py:68-71`): slim stays off, `heap_limit` is claimed, and a short script's outputs equal
  the stock image's (as `test_transparency.py`).
- **PL09**: the chord, arp, mono, voice-room suites pass unchanged (they read `held` etc. by symbol).

## Device check (PL09 `TEST.md`, two steps)

1. Power on; on Synth 1 a pad plays a chord, Shift + Synth 1 opens the play page with PL09's defaults (strum off,
   arp off). Pass = the write test passed and the span was zeroed. If CTPlay acts as stock, the test failed: stop
   and report.
2. As SL00D's heavy session: three power cycles, a pack load, a pattern playing with chords and an arpeggio for a few
   minutes, a Components transfer. Pass = no stuck or wrong chord notes, no arpeggio running by itself, mono record
   still mono. Corruption of `held` / `run` would show here.

No diagnostic build is planned. If step 1 fails, the next step is a diagnostic twin whose runtime lights a pad when
the test fails, instead of staying silent.

## Risks and open questions

- **Something writes the span later** (DMA through a stale pointer). Low (SL00D, static scan); shows in step 2.
  An optional guard: a checksum of the span re-checked from `led_task`, as SL00D did. Builder's call; I would not add
  it to a PL build.
- **One failed word turns all of CTPlay off** (D6), not just the chord engine. Same behaviour as the existing heap
  guard; per-feature gating can come later if a feature ever needs to run without ITCM. Builder's call.
- **Generic named regions vs `itcm` only** (D3). Builder's call.
- **Sequencing**: land the builder + runtime first with the fixture feature only (PL08 still pinned and identical),
  then move chord's arrays in the PL09 commit, which drops PL08 from the HEAD pin and rebuilds it from tag `PL08`
  (as PL01–PL07, `tests/test_build.py:57`). Builder's call.
- **The RM0385 / AN4667 wording on DMA → ITCM** is from memory (flagged above); nothing in the design depends on it.
  Builder's call to check the PDF.
- **First ITCM write on the device** (see Caches / MPU): unlikely to fault (no MPU literal; ITCM is Normal memory
  in the default map). **Guard (main session's call, 2026-10-17):** before the write test, `slim_ready` reads
  `MPU_CTRL` (`0xE000ED94`, a read only); with the MPU enabled slim stays off (D6) and writes nothing, so the worst case
  is "CTPlay acts as stock" in step 1, never a fault or a hang. A separate write-only diagnostic first is then not
  needed.
- ~~Review D1~~: **answered (user, 2026-10-17): move chord's arrays now, in PL09.**
