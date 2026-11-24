# Saved settings — design

Status: built as `PL10` (2026-10-17); passed on the device 2026-10-18 (`firmware/PL10/TEST.md`). Implements the saved-state part of the foundation spec
(`2026-10-10-slim-foundation-design.md` §3 "Saved state"), which was left for the first feature that needs it.

## Intent

Every CTPlay setting starts from "off" at power-on (`docs/user-guide.md:48`, `:282`). With this feature, a project
carries its CTPlay settings: save the project, and loading it again (later, or after a power cycle) brings back its
chords, strum, arpeggiator, mono record, play pages and count-in.

**Goals**
- Settings travel with the project file that stock already writes. CTPlay never writes the flash or the SD card itself.
- A project with no CTPlay data (made by stock, by an older CTPlay or by upstream, a new project, foreign bytes) loads
  the defaults. Nothing CTPlay writes changes how stock firmware plays a project.
- Adding a setting in a later build never moves earlier ones (`save_layout.lock`).
- No new RAM for the settings (they already live in RAM); at most 1 B for the pending flag (none in the recommended form).

**Non-goals**
- Device-wide settings and "defaults for new projects" (the 75 B `settings_tail` region): later, if wanted.
- Saving performance state: held notes, latched notes, strums in progress, the open page, counters (list below).
- Any new button or pad. `docs/ui-map.md` does not change.
- Marking the project as modified when a CTPlay setting changes (stock does not know about them).

## What is saved

25 B, a byte image of the existing globals (no bit packing: space is not short, and a byte image keeps the copy
generic). Positions are relative to the payload start; the lock file fixes them (see Versioning).

| Payload | Field (file) | B | Valid values (else the field's default) | Default |
|---|---|---|---|---|
| 0 | `chord_settings[4]` (`chord.c:86`) | 4 | shape 0-7, inversion 0-3, spread 0-2, bass bit (`chord_math.h:9-12`) | 0 |
| 4 | `chord_rootless` (`chord.c:87`) | 1 | bits 0-3 | 0 |
| 5 | `chord_strum` (`chord.c:88`) | 1 | 2 bits per track, any | 0 |
| 6 | `chord_strum_down` (`chord.c:89`) | 1 | bits 0-3 | 0 |
| 7 | `chord_mono` (`chord.c:90`) | 1 | bits 0-3 | 0 |
| 8 | `chord_arp[4][2]` (`chord.c:92`) | 8 | `[0]`: no dotted at rate 1/32 (`page.c:127-129`); `[1]`: bits 0-4 only, gate ≤ 5 | `[0]` 0, `[1]` `GATE_DEFAULT << 2` (`chord.c:108-109`) |
| 16 | `page_last[4]` (`page.c:36`) | 4 | 0-2 (Chords, Arp, Keys) | 0 |
| | *PL11:* `page_last` retired (a tombstone, written 0); the page is saved as `page_slot[4]` at payload 33, its pad in the page list (Chords 0, Arp 1, Pattern tools 2, Keys 7) | | a page that exists | 0 |
| 20 | `page_quick[4]` (`page.c:37`) | 4 | 0-1 (Keys has no quick half, `page.c:32`) | 0 |
| 24 | `ci_on` (`countin.c:38`) | 1 | 0-1 | 0 |

`chord_arp[t][0]` bit 7 is the Latch *mode*; it is saved like any setting (question Q2). The default of
`chord_arp[t][1]` is not 0: a "no data" load must use the feature's defaults, not zeros.

**Not saved (RAM only):** `held[]` (held chords, strums in progress, latched arpeggio notes), `chord_order`,
`chord_sending`, the voice-room readings, the arpeggiator run state (`arp.c` `run`, clock), `chord_page` (the open
page), `page_taken`, mono record's visit state, the count-in's counting state (`ci_count`, `ci_done`, `ci_beat`,
`ci_pass`, `ci_ms`). The metronome is stock's own parameter (`countin.c:4-6`) and is saved as stock saves it.

## Where: the project's record tail (user, 2026-10-17: project)

**Recommendation: project.** The user's leaning, and the cheapest correct place:

- **The session record** (`[0x2003D71C + 0x14]` = `0x2001183C`, 0x2740C = 160,780 B) is the live project in RAM:
  the pattern players read their patterns from inside it (track 0 = record + 0x2E4 … track 3 = record + 0x207BC;
  checked in emulation, slim harness, 2026-10-17). Stock writes the whole record to `Sessions/NN_*.ncs` on Save and
  reads the whole file back on load (upstream NOTAS "el fichero de sesión", SC402D / SC403D).
- **Its last 1000 B, the tail** (`record + 0x27024 … + 0x2740B`), are not read by stock:
  - the only literal into it in the image is `0x27024` at `0x0802B1E4`, used by the new-project clear (below);
    the others (`0x0802012C`, `0x08020940`, …) are the total size `0x2740C` (slim scan of the stock image 2026-10-17;
    upstream had found the same, `docs/NOTAS.md:496`);
  - **saved and loaded on the device** (upstream SC402D / SC403D, `docs/NOTAS.md:426`: "se guarda y se carga";
    upstream's claim, not re-tested by slim);
  - in emulation, a write-watch on the tail saw **no write** from stock's save route or from its load / apply route
    (verified, see Spike);
  - Components' project validator does not check the tail (from its strings, not run: the userx14 repo,
    `ext/circuittracksreverseengineering/Assets/Novation-Components/circuit-tracks-project-validator-*.wasm`; it checks
    named fields, and must-be-zero only in padding / spare / reserved fields that CTPlay never uses). Confirmed on the
    device 2026-10-18 (PL10 step 9): a CTPlay-saved project went through Components and back with its settings.
- **Correction to upstream's notes:** `docs/NOTAS.md:496` says the `0x27024` literal is "the end of the block that new
  project fills". It is the *start* of a clear: `0x0802AF34-0x0802AF42` calls `0x0801BC58(record + 0x27024, 0x3E8)`
  inside the new-project init `0x0802AD82`. In emulation the whole tail is zero after `0x0802F5BC`. So **a new
  project clears our block** (still to be seen on the device: device check step 3).
- Not the 65 B `project_reserved` region: 44 of its bytes live in the synth patch blobs, which a patch change
  overwrites and a load with the same patch does not restore (`docs/NOTAS.md:2230`), and upstream's `persist19` uses
  all 65.
- Not the device record (`settings_tail`): settings would not follow the song, and stock writes that record only when
  one of its own settings changes; CTPlay would have to call stock's settings save (`0x0802D2AC`, as upstream `vcf21`
  does) to get it written.

Add a region to `stock/memory.toml`: `project_tail`, kind `saved`, 1000 B, confidence `verified` (upstream SC402D /
SC403D device runs; slim emulation 2026-10-17). Foreign bytes are possible there: the 8 projects of the
`02_Shadow Child` pack carry 995 random-looking bytes in it (`docs/NOTAS.md:434`).

### The block

CTPlay's block sits at **tail + 768** (`record + 0x27324`), 64 B reserved; upstream uses tail offsets 0-679, 956-967
and 998 in various builds (`tools/arp.py:52`, `cscale.py:58`, `drumarp.py:46`, `rollers.py:37,84`, `drumpat.py:43`, …),
and 680-955 looked unused on 2026-10-17. **Correction (build time, Q4):** nothing in the tail is free across upstream's
builds: 680-904 is upstream arp's RAM-only state (`tools/arp.py` `EXT_LO` / `EXT_HI`, SC42.3), 904-955 stepgate,
quant and qmute, 956-998 rollers, scdrum, sdpv and drumpat. The block stays at + 768: overlap is never dangerous (both
sides check a magic, and upstream's RAM-only state is zeroed by its own load), it only costs defaults when a project
moves between upstream and CTPlay builds.

| Block | B | |
|---|---|---|
| +0 | 4 | magic `"CTPS"` |
| +4 | 1 | layout ID (1) |
| +5 | 1 | payload length n (25 now) |
| +6 | 1 | check: CRC-8 over +4, +5 and the n payload bytes |
| +7 | 1 | pending: `0xA5` = loaded, not applied yet; written 0 by a save that writes the block (a save while pending leaves the tail as loaded, `0xA5` included: harmless, the next load marks it again); outside the check |
| +8 | n | payload (table above) |

Valid block = magic, layout ID equal to the build's, `8 ≤ 8 + n ≤ 64`, check correct. Otherwise every field takes its
default. Inside a valid block each field is checked against its valid values; a payload shorter than the build's
gives the missing fields their defaults, a longer one's extra bytes are ignored.

## How load and save hook in

Addresses re-verified in `re/app.asm` and emulation on 2026-10-17 (the foundation spec listed upstream's
`0x0802F5B8`, `0x0802F5FA`, `0x0802FE5E`):

- **Save:** `0x0802FDF8(obj, slot, …)` stamps the record header, calls `0x0802F63C(obj)` (the four live blobs into the
  record) at **`0x0802FE5E`**, then posts the write to the storage task (`0x0803C946`): the file is written later, from
  the record (`docs/NOTAS.md:1812`). `0x0802FE5E` is the only caller of `0x0802F63C`. Hook: **`call` hook
  `session_save`, site `0x0802FE5E`, target `0x0802F63C`** (stock first, then the handler).
  Emulation: Save, Save (button 25, through `0x08033320`) → store listener `0x08030502` → `0x0802FDF8(obj, 3, 0)`
  → `0x0802F63C` → `0x0803C946`, synchronously inside the button press: **UI task**, `context = "ui"`.
- **Load:** the storage task reads the file into the record; the completion `0x08030076` (message type 2) calls
  `0x0802FD5C(obj)`: a valid header → `0x0802F5FE` (fix-up), else → `0x0802F5BC` (new-project defaults); then the
  apply `0x0802EEFE(obj, 0)`. The apply's last call is `bl 0x08029A00` at **`0x0802F5B4`**, followed by the `pop` at
  `0x0802F5B8` (upstream's `LOAD_END`). Hook: **`call` hook `session_applied`, site `0x0802F5B4`, target
  `0x08029A00`** (slim has no exit-hook kind; the call is the apply's last action).
  Every new-project path ends in the apply: the four callers of `0x0802F5BC` (`0x0802F8F6`, `0x0802FD98`,
  `0x080306FA`, `0x08030848`) are each followed by `0x0802EEFE`. So **no new-project hook** is needed: stock clears
  the tail and the apply hook then finds no block.

### Flow

1. **`session_applied`** (task not identified): writes `0xA5` to the block's pending byte, if the record pointer is
   not 0. Nothing else: no stock call, no lock, no slim RAM.
2. **Each `init()` at boot** also sets pending, so the first LED frame applies whatever the record holds (covers a
   power-on load that ran before `slim_ready()`, in either order).
3. **`led_task` (UI task)**: if pending, clear it, then copy the block into the globals (or the defaults) and run each
   feature's fix-up: per-field validity; for each track whose loaded pattern is off, `arp_free(t, 0)`; then
   `arp_free(t, 1)` for every track, so latched notes from the previous project end (Q2); a count-in in progress is
   cancelled as Play does (`ci_count = 0`).
4. **`session_save` (UI task)**: if pending (a save before the next LED frame), leave the tail alone: it holds the
   loaded block, which is the right one to save (upstream's `fxsess` rule, `docs/NOTAS.md:379`). Else write the
   block from the globals, pending 0.

All settings keep a single writer (the UI task), as today. RAM: **0 B** (the flag is in the tail). The other way,
a 1-byte RAM flag set by `session_applied`, would need init to run before the power-on load (builder's call).

### Cases

| Case | Result |
|---|---|
| Project saved by this or a later CTPlay with the same layout ID | its settings (missing fields: defaults) |
| Stock project, upstream project, CTPlay ≤ PL08, foreign bytes | defaults (magic / check) |
| New project, empty slot (invalid header) | stock clears the tail → defaults |
| Save as another slot | the copy carries the block (the record is the same) |
| Project change while pads are held | held entries keep their own notes, strum speed and flags (`chord_held.h:54-67`), so releases end what they started; new presses use the new settings |
| Project change with a latched arpeggio | it ends after the load (step 3) |
| CTPlay project loaded on stock 1.2.1 | stock never reads the tail; loading and re-saving it under stock keeps the block, so CTPlay finds it again |
| CTPlay project re-saved by CTPlay ≤ PL08 | the old block is kept as it was (those builds never write it) |

## Versioning and the lock

As the foundation spec §3 (`2026-10-10-slim-foundation-design.md:143-152`), with byte fields instead of bit fields:

- A feature declares its saved fields in `feature.toml`, e.g. `[[saved]] symbol = "chord_arp", bytes = 8,
  store = "project"`, with a default image and a fix-up function (`fix = "chord_saved_fix"`, UI task). The build
  generates the copy table (symbol address, size, payload offset) and the check.
- `slim/save_layout.lock` (committed) records each field's payload offset and size the first time a build has it.
  Later builds keep it; a new field goes after the last one. A field whose size changes fails the build.
- A retired field stays in the lock as a **tombstone**: its bytes stay reserved and are written 0. Reusing them, or
  changing what a field means, needs a **layout ID bump** (the build reports it), after which every older block loads
  as defaults.
- `store = "device"` is refused until a device store exists.

## Context rules

- `session_applied` runs inside stock's load, in a task slim has not identified (`docs/NOTAS.md:541`: the load and
  save hooks "run inside stock's load / save"). Declare it with the most restrictive context (`dsp_locked`, or a new
  `any` that the checks treat the same): the build then refuses any callee tagged `takes_dsp_lock`. It does one byte
  store. **Built (PL10): context `any`** ("from a task slim has not identified"), not `dsp_locked`: the hooked call
  itself (`0x08029A00` -> `0x0803BDF2`) takes the DSP lock, so the load does not run with it held. The check skips only
  the call wrapper's own call of that target.
- `session_save` is UI (verified route above); it copies bytes only.
- The apply runs in `led_task` (UI), where `arp_free` already runs (`page.c:124`, `:139`). Nothing here runs from a
  `dsp_tick` or `dsp_locked` context, and nothing calls `MARK_DIRTY` or takes the DSP lock.

## Tests

**Spike (2026-10-17, slim harness on PL08, no product code).** What runs in Unicorn:
- the real Save route (buttons through `0x08033320`) down to the storage post `0x0803C946`;
- the read-done handler `0x0802FD5C` → fix-up → apply → `0x08029A00` → `0x0802F5B8`, to its return (the harness's
  SPI2 model lets the refresh finish; upstream's emulator had to skip it, `docs/NOTAS.md:297`);
- the new-project path `0x0802F5BC` → apply, from a fresh harness; it clears the tail;
- a tail write-watch: no stock write on save or load, 1000 B zeroed on new project.

What does not: the storage task's file write and read (FatFs, SD). The round trip models the file as a snapshot of
the record taken at `0x0803C946` and written back before `0x0802FD5C`. One chained run (several record rewrites in
one harness) crashed in stock's new-project path (`pc = 0` from `0x0802F5D8`); one scenario per fresh harness worked.

**Emulation tests** (`tests/test_saved.py`, NoteHarness where notes matter):
1. Round trip: set distinct settings through the real routes (Shift + pads, play pages, Shift + Clear), Save twice;
   the block is in the tail (magic, ID, length, check, pending 0); snapshot; change every setting; write the
   snapshot back, `0x0802FD5C`, one LED frame: every setting is back.
2. Stock project (tail zero), random tail, right magic with a wrong check, right check with out-of-range values,
   shorter payload, other layout ID: defaults (gate 3/6), per-field defaults, nothing crashes.
3. New project (`0x0802F5BC` route): defaults.
4. Save between the load and the LED frame: the tail keeps the loaded block.
5. Load with pads held and with a latched arpeggio: after release, `sounding` is empty; latched entries gone.
6. Build checks: the lock keeps positions; a removed field without a tombstone, a resized field, or a reused
   tombstone without an ID bump fail the build; `session_applied` calling a lock-taking function fails.
7. Existing transparency and published-rebuild tests stay green (PL08 rebuilt from its tag stays identical).

**Device check sketch** (`firmware/<MARKER>/TEST.md`, a test pack, SD card backed up):
1. Set different chords / strum / arp (with Latch) / mono / pages on all four tracks, and the count-in. Save. Power
   off and on. Load the project: all back, the count-in too.
2. Load a stock-made project: everything off, gate 3/6.
3. New project (empty slot or Clear in Projects): everything off.
4. Save to another slot; load the copy: settings there.
5. Hold a chord and run a latched arpeggio, load another project: no stuck notes; the latched arpeggio ends.
6. Flash stock 1.2.1; load the CTPlay project: it plays as before (patterns, scenes, patches); save it. Flash CTPlay
   again; load it: the settings are back.
7. Load a `02_Shadow Child` project (foreign tail bytes): defaults, nothing odd.

## CTCtrl later

The block is one self-describing record (magic, layout ID, length, check) at a fixed place in a file CTCtrl can
already reach: a project file read over SysEx (as Components does) holds it at byte `0x27324`. A later `hello`
(`docs/candidates.md:97-98`) could answer a "read settings" request with the same 33 bytes from RAM and accept a
write that goes through the same validation as a load, applied in the UI task. `save_layout.lock` is then the format
CTCtrl reads; an edit made live changes the project in RAM and is kept when the user saves, as any edit.

## Risks and open questions

- **Q1 Project or device?** **Answered (user, 2026-10-17): project.** Recommended: project (above). Consequence to accept: a setting is kept
  only when the project is saved, like stock's own edits; a new project starts from off.
- **Q2 Latch.** **Answered (user, 2026-10-17): save it.** Recommended: save the Latch mode; end latched notes on every project load.
- **Q3 Pages.** **Answered (user, 2026-10-17): save them.** `page_last` / `page_quick` are navigation more than sound; recommended: save them
  (8 B, the page a track opens on comes back with the song). Dropping them later costs a tombstone.
- **Q4 Block offset** (tail + 768). **Decided at build time:** kept; the tail has no free 64 B across upstream's builds (see The block).
- **Q5 New project on the device.** Emulation and the code say stock clears the tail; upstream's SC402D step 5 has
  no recorded answer. If the device keeps it, a new project would inherit the last settings; an `entry` hook on
  `0x0802F5BC` that clears our magic closes it. Builder's call, decided by device step 3.
- **Q6 The load task.** Not identified; the design does not depend on it (one byte store). Builder's call whether to
  look.
- **Q7 Saving settings in the tail directly** (no globals) would free 25 B of slim RAM, but then readers see the
  file's bytes while stock reads a project into the record. Not recommended unless RAM runs out and the ITCM plan
  does not land. Needs the user if it comes to that.
- **Risk: stale block.** A project re-saved under CTPlay ≤ PL08 keeps its older block. Accepted.
- **Risk: emulation.** The SD write and read are not emulated; the round trip trusts upstream's device evidence that
  the file is the record. Device steps 1 and 6 settle it for CTPlay.
- User guide lines to update when built: `user-guide.md:48-49, 162, 192, 209, 220, 233, 282`.
