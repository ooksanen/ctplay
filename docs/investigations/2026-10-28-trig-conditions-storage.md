# Trig conditions: where to store them and where to check them (research, 2026-10-28)

Date: 2026-10-28 · Builds: none (static reading of `re/app.asm`, the stock image, the device RAM snapshot, the
Components validator's strings, upstream's `docs/NOTAS.md` and tools) · Background: what other sequencers offer is in
[`../research/2026-10-28-trig-conditions.md`](../research/2026-10-28-trig-conditions.md).

Status tags, as in [2026-10-25-drums-pattern.md](2026-10-25-drums-pattern.md): **[asm]** read in the disassembly;
**[dump]** read in the RAM snapshot `ctre/Firmware-Analysis/ram_dump_firmware_0x08037988.bin`; **[upstream]**
upstream's claim, not re-checked; **[device]** confirmed on a device; **[guess]** my inference. Anything not
**[asm]** / **[device]** says what would confirm it.

## Short answer

| Track kind | Recommended storage | Bits a step | Travels with stock's copies | Cleared by stock's Clear |
|---|---|---|---|---|
| **Drums** | one byte a step at **pattern + 0x88 + step** (+ optionally one more bit a step from the 4 B at + 0x84..+ 0x87) | 8 (9) | Duplicate: **only when the target is not the drum's shown pattern** (never when stopped); Mutate, copy 1-16 → 17-32, paste step: **no** | no |
| **Note tracks** | **step bytes [2] and [3]** (a 16-bit word) | 16 | yes: Duplicate, Mutate, paste step, copy 1-16 → 17-32 copy whole steps | no (Clear step and Clear pattern leave them) |

- A drum step has **no spare bits stock ignores everywhere**, except microstep bits 6-7 (2 bits, with a catch). So
  drum conditions must live outside the 4 step arrays, in the unused pattern-settings bytes. They are not in the drum
  editor's step store, so raw writes there are safe, but stock's own copies do not carry them: CTPlay needs small hooks
  on Duplicate, Clear and Mutate to keep them with their hits.
- Note steps have 16 unused bits that stock never reads or writes, and every whole-step copy carries them. The one
  catch: the step the editor has selected is mirrored in a step store; write it through that store.
- Both places need a **project mark** (in CTPlay's saved block): one third-party pack has junk in pattern-settings bytes
  8..39, and upstream builds used step bytes [2] / [3] for their own data.
- **Check at playback** where stock checks probability: make a failed condition look like a failed probability roll.
  Evaluate once a step at the step's tick 0 (`0x0804A6B8`, shared by both player classes). **Count passes** at
  `0x0802CD42` in the track advance, which runs for all 8 tracks.

---

## 1. Drum step arrays: which bits are spare

Drum pattern d, p = `rec + 0xCD74 + 0x3540 d + 0x6A8 p`; steps are 4 arrays of 32 B (velocity `+0x00`, probability
`+0x20`, sample flip `+0x40`, microstep mask `+0x60`). Details: [2026-10-25-drums-pattern.md](2026-10-25-drums-pattern.md).

### What playback reads [asm]

- Hit test `0x0804AA08(base, step, micro, rand)` (from player slot 2 `0x08041252`): `velocity != 0` (whole byte), then
  `probability >= rand & 7` (whole byte, `0x0804AA18`), then `micro & (1 << micro)` with micro 0..5.
- Player slot 4 `0x080411CA` (the sample for the step's first hit) repeats the same three tests inline
  (`0x080411F4`–`0x08041206`, k = 0..5), then sends the flip byte as the sample when it is not `0xFF`.
- On a hit, the **whole velocity byte** goes to the drum's note-on (`0x08041290`).

### Each candidate bit

| Bits | Playback | Stock edits | Components validator | Verdict |
|---|---|---|---|---|
| Velocity bit 7 | **Misbehaves**: the byte is the note-on velocity (128-255), and a step with only bit 7 is a hit | Velocity view writes the whole byte (`0x0804EEEC`, values 8..127); recorder overwrites it (`0x0803FA26`); step toggle sets 0x60 / 0 (`0x0804EC18` / `0x0804EC3E`) | "out of range velocity" | **Not spare** |
| Probability bits 3-7 | **Misbehaves**: compared as a whole byte, so any of them set = always plays | Probability view writes the whole byte = pad 0..7 (`0x0804F300`, setter `0x0804A270`); recorder, toggle, clear write 7 | "invalid probability" [guess: a range check] | **Not spare** |
| Flip bits 6-7 | **Misbehaves**: the byte is the sample number (`0xFF` = none uses every bit); 64..254 would select a sample that does not exist [guess] | Clear / toggle-off write `0xFF` | "invalid drum choice value" | **Not spare** |
| **Micro bits 6-7** | **Ignored** (only bits 0-5 are tested) | **Kept** by: every store commit (whole bytes), the microstep view (XOR of one bit, `0x0804F0D2`), the recorder (`|=`), Duplicate (both paths), copy 1-16 → 17-32, paste step (`0x0803DFAE`, whole byte), Mutate (whole-byte swaps). **Cleared** by: Clear step (`0x0803E1B2`), Clear pattern, step toggle on / off (`0x0804EC2C`, `0x0804EC50`), a probability or velocity press on an empty step | "non-zero drum rhythm when velocity is zero"; a range check on it is not visible in the strings | **2 bits, with a catch** |

The catch with micro bits 6-7: the microstep view decides "the step is now empty" by the whole byte
(`0x0804F0FC`, `cbnz r5`). Turning off the last microstep of a step that has bit 6 or 7 set leaves a silent hit: the
velocity stays, the step pad stays lit, nothing plays. A hook could fix it, but 2 bits are too few for any of the
encodings below anyway. **Not recommended.**

Summary: inside the 128 B of step arrays, only micro bits 6-7 are spare, and they are not enough.

## 2. Pattern-settings bytes

Layout of the settings block (both kinds): `[0]` last step, `[1]` first step, `[2]` sync rate, `[3]` direction, then
36 bytes stock does not use, up to the automation lanes. Drums: `+0x80..+0xA7` (lanes from `+0xA8`). Note tracks:
`+0x380..+0x3A7` (lanes from `+0x3A8`). **Room: 36 B per pattern, 8 patterns per track, on every track.**

### What I could confirm

| Claim | Note tracks | Drums |
|---|---|---|
| Stock reads only bytes 0-3 | [asm] getters `0x0803C6D6` / `0x0803C744` / `0x0803C790`, load `0x0803DC16`, listener `0x0803D6A0`; no immediate offset into bytes 4..39 found (a computed offset cannot be ruled out by grep) | [asm] load `0x0803F050`, settings store `+0x80..+0x83`; same caveat |
| Saved and loaded with the project | [upstream] [device] SC403D (part of the session record) | [upstream] [device] SC403D wrote marks to all 64 patterns of the project, drums included |
| **Duplicate** copies them | **Yes** [asm]: `0x0803D2B0` always copies the whole 0xCA8 B. [upstream] [device] SC403D: "Synth 1 pattern 2 carries the mark of Synth 1 pattern 1" | **Only when the target is not the drum's shown pattern** [asm]. `0x0803E2AA`: stopped, it first makes the target the shown pattern (`0x0803E2BE`–`0x0803E2CC`); a shown target is written through the step store (4 arrays), lanes `memcpy 0x600` from `+0xA8`, settings bytes 0-3 through the settings store. **Bytes `+0x84..+0xA7` are not copied.** Only a target that is not shown (playing, another pattern) gets the whole `memcpy 0x6A8`. Not seen on a device |
| Clear pattern leaves them | **Yes** [asm] `0x0803D310` writes steps, lanes, bytes 0-3 only. [upstream] [device] SC403D | **Yes** [asm] `0x0803E3B0` writes arrays, bytes 0-3, lanes only |
| Clear step leaves them | yes [asm] | yes [asm] `0x0803E18A` |
| Mutate (random step shuffle) | carries nothing here (bytes are per pattern, not per step) | **does not move them with the hits** [asm] `0x0803E6F0` swaps the 4 array bytes and the lanes only |
| Zero in other people's projects | **Bytes 4..7: zero in all 14 080 patterns** of 220 sessions (18 packs) [upstream] audit 2026-10-13. **Bytes 8..39: junk** in the 8 sessions of pack `02_Shadow Child` (the same 32 B in every pattern of a track) | same audit (all 8 tracks) |
| Components validator | names no field for these bytes (it checks `playbackRange`, `syncRate`, `playbackDirection`, steps, automation) [asm-level: wasm strings]. Likely unchecked; unconfirmed until a Components round trip | same |

**Correction to [2026-10-25-drums-pattern.md](2026-10-25-drums-pattern.md):** `0x0803E6F0` is not a Nudge. It draws
stock's random number `0x0803C7F8` for each step and swaps steps between first and last: it is the drums' **Mutate**,
the twin of the note tracks' `0x0803D53C` (same dispatcher branch, `[r7 + 0x18]` at `0x0802DDDA`; upstream SEQWD calls
`0x0803D5xx` / `0x0803E7xx` stock's Mutate). Its recipe (raw write, store brought in line, commit with the editor
detached) is still the right one to copy.

Upstream's `drumpat.py` (SC43, emulation only) put one byte a step at `+0x88 + step`, read only in a project marked
`DQ` at the record tail + 998; the first value set marks the project and clears bytes 8..39 of all 32 drum patterns.
It hooked Nudge (its own) but not stock's Duplicate, Clear or Mutate.

## 3. Note-track step bytes [2] and [3]

A note step is 28 B: `[0]` slot mask (bits 0-5), `[1]` probability, `[2]`, `[3]`, then 6 slots of (note, length | tie
<< 7, microstep, velocity). The note editor's step store (`[editor + 0x20]`, Synth 1 `0x20039F28`) holds the selected
step as **7 words**; word 0 = bytes 0-3 [asm] `0x0804A06C` (7 parameters), [dump].

### Playback ignores them [asm]

- `seq_units_start` `0x08040D4C` reads `[0]` (mask), `[1]` (probability, whole byte against `rand & 7`), and each
  slot's microstep `[slot + 6]` and note.
- `seq_play_step` `0x08040E5A` reads slot bytes only.
- [upstream] [device] SC39 kept a mutate level in `[2]` and passed on the device ("funciona"). Byte `[3]` was used by
  upstream's SC40.3 / SC40.4 / autorel, none confirmed on a device.

### Stock's writers keep them [asm]

| Writer | What it writes | [2] / [3] |
|---|---|---|
| Step store → pattern (editor listener `0x0803D996`) | each dirty word whole; word 0 from the store's read buffer | kept: the buffer was loaded from the pattern (`0x0803DC62`, memcpy 28 B) |
| Probability view `0x0804D0BC` | `strb pad, [word0 + 1]` | kept |
| Add a note to a step `0x0804B116` | slot word bytes; word 0: `[0] |=` bit, `[1] = 7` on the first note | kept |
| Velocity / gate / micro views (`0x0804C640`, `0x0804C92A`, `0x0804C9B0`) | slot words; `[0]` and `[1]` bits | kept |
| Recorder commit `0x0803F7BE` | slot bytes `+4..+7`, `[0] |=`, `[1]` | kept |
| **Clear step** `0x0803D1D4` → fill `0x0803D230` | bytes 0, 1, 4..27 | **kept (not cleared)** |
| **Clear pattern** `0x0803D310` → the same fill for 32 steps | as above | **kept (not cleared)** |
| Duplicate `0x0803D2B0` | memcpy 0xCA8 | copied |
| Paste step `0x0803D16E` | memcpy 28 B | copied |
| Copy 1-16 → 17-32 `0x0803DD24` | memcpy 0x1C0 | copied |
| Mutate `0x0803D53C` | swaps whole 28 B steps | moved with the step |

Upstream's audit: bytes [2] and [3] are zero in all 220 sessions (225 280 steps) [upstream].
The Components validator names only `assignedNoteMask` and `probability` in `stepInfo`, so [2] / [3] are likely
unchecked (unconfirmed until a Components round trip).

### Catches

- **Clear does not clear them.** A cleared step keeps its condition, and the next note put there inherits it. Fix:
  one hook on the fill `0x0803D230` (used by both Clear step and Clear pattern) that also zeroes bytes 2-3.
- **The selected step is mirrored.** The step store holds word 0 of the editor's selected step (`[editor + 0x24]`
  p1). A raw write of [2] / [3] to that step is undone by the next stock edit of it (a probability press writes the
  stale word 0 back). Write that step through the store (write pointer `0x080354FA` on parameter 0, then commit
  `0x080353C0`), as upstream's SC39 did; other steps can be written raw. A test must end with a stock edit of the
  same step.
- **Other bits are not spare:** mask bits 6-7 and probability bits 3-7 change playback or fail the validator
  ("invalid assigned note mask", "invalid probability"); slot bytes are per note and validated.
- Projects made on upstream builds may carry mutate / frequency / dynamics data in [2] / [3]: the project mark covers it.

## 4. The probability view

| | Note tracks | Drums |
|---|---|---|
| Class (vtable) | `0x0805ACD4`; second vtable `0x0805AD00` | `0x0805AB14`; second `0x0805AB40` |
| Instances [dump] | `0x20042890 + 0x3C t` | `0x200438DC + 0x3C d` |
| `[view + 0xC]` | editor + 0x18 (`0x20039E68`; note editor `0x20039E50`, vtable `0x0805C114`) | editor + 0x18 (`0x2003ACE8`; drum editor `0x2003ACD0`) |
| Pad handler (slot 0) | `0x0804D0BC` | `0x0804F262` |
| Selected step | the step store's word 0 (`[[view + 0xC] + 8]`), which mirrors `[editor + 0x24]` p1 | position store `[[view + 0xC] + 8]` p1 |
| LED listener (redraws row 3) | `0x0804D116` (thunk `0x0804D114`) | `0x0804F322` (thunk `0x0804F320`) |
| LED buffer (slot 7) | `0x08047592` returns `[[view + 4]]`: 16 halfwords, 0-7 = row 3, 8-15 = row 4 | same |

- **Row 4** arrives as pads 8..15 and both handlers return at once (`cmp r1, #8; bge`) [asm]. Stock never writes
  LEDs 8..15 of the buffer [asm] (both listeners fill 0..7 only).
- **Shift:** neither the controller's pad press `0x08033282` nor the track container's `0x080435B0` tests Shift, and
  the view does not either [asm]. So **Shift + row 4 = nothing** (free), and **Shift + row 3 = a plain probability
  press** (a Shift layer there would override stock).
- **When stock accepts a row-3 press** [asm, dump]: a step pad is held (note `[editor + 0x28]` p0, drum
  `[editor + 0x24]` p0), or the transport is stopped (`0x20011034` p0 = 0), or `0x20039DE0` p0 is set (shared by all
  editors; likely stock's pattern-follow toggle on Shift + Patterns, see the drums research). Then: note tracks only
  when the step has notes (`[0] != 0`); drums on an empty step first make a hit (velocity 0x60, micro bit 0). Then
  write and commit. A condition editor on row 4 should use the same rules.
- **One step at a time:** stock edits the single selected step (the last step pad pressed, or the playhead when
  playing with follow on). Holding several step pads does not edit several steps.
- **Drawing row 4:** two routes. (a) slim's `led_task` hook overwrites pads 25-32 when this view is the bottom view
  (a visibility test like `chord_visible_view`; not traced which container field holds the bottom view). (b) As
  upstream (SC39 `c_mutled` / `c_mutbuf`, SC43 `drumpat`): an entry hook on the listener, plus the LED-buffer slot 7.
  Slot 7 `0x08047592` is shared by many classes, so (b) needs a vtable entry change, which slim's hook kinds do not
  cover today. **(a) is the simpler route.**
- Upstream used this view's row 4 for note "frequency" (SC40.3, a mode toggled by Pattern Settings pad 25) and for
  drum frequency / dynamics / mutate (SC43).

## 5. Counting passes and checking a step

### Where a pass ends [asm]

- Engine `E = 0x20038EC0`. Each tick, `0x0802C6xx` runs the step advance `0x0802C90C(E, track, …)` for **all 8
  tracks** (loop at `0x0802C7A4`–`0x0802C7FC`, tracks 0-7). At a step's last tick it calls the track advance
  `0x0802CB3C`. A look-ahead copy (`0x0802CA14`, 8 call sites) runs the same code with `fp = 1` to fill the "next"
  store `[E + 0x70 + 4t]`.
- **`0x0802CD42`** (`ldrb.w r1, [sp, #0x44]; orrs r4, r1; beq`): `r4` = "the pattern ends at this step" (per track,
  from `0x0802C4E4` through `0x0802C5F8`, direction-aware), `[sp + 0x44]` = a scene change. When either is set, the
  next pattern of the chain and its first step are chosen. Track = `[sp + 0xC]`, the pattern that just ended = `sb`
  (p0 of the playing store), look-ahead = `fp` (count only when `fp == 0`). Upstream's SC40.4 hooked exactly here
  (`c_rfpass`, tracks < 4 only; emulation: pattern ends and scene changes count, mid-pattern steps, look-ahead and
  drums did not because of its own filter).
- The count happens before the next pass's first step plays, so that step already sees the new count [upstream].
- `[E + 0x94 + t]` is stock's own per-track byte, but it is the ping-pong / random-direction step state, not a pass
  counter (`0x0802CC5E`, `0x0802CD3C`, cleared at `0x0802CE0E`) [asm].

### Play, Stop, pattern change, chain, scene

- **Play:** tick 0 runs from the Play handler (hook `seq_start`, UI task). Reset the counters there, so FIRST means
  "first pass since Play". Whether Play always restarts at the chain's first pattern and step: not traced.
- **Stop:** nothing to do (counters can stay until the next Play).
- **Pattern change / chain advance while playing:** stock switches at the pattern's end, through `0x0802CD42` (the
  `r4` path). Counters per track reset to 0 at every change make A:B useless in a chain (upstream's SC40.3 lesson:
  "every 2" in a 2-pattern chain never played in one pattern). Upstream's fix: **one counter per (track, pattern)**.
  For 8 tracks × 8 patterns, counted mod 840 (the LCM of 1..8, 10 bits): 64 × 2 B = 128 B of RAM (`above_heap` or
  ITCM; not saved).
- **Scene change:** `[sp + 0x44]`; upstream counted it as a pass end. Whether to reset instead is a design choice.
- **LAST** needs to know the next pass is another pattern: the look-ahead store `[E + 0x70 + 4t]` p0 against the
  playing one. When the look-ahead refreshes it during a pass: not traced [guess: every tick].

### Where to check a step [asm]

Both player classes (notes vtable `0x0805B750`, drums `0x0805B72C`) share the tick listener `0x0804A5C6` →
`0x0804A684`, which reads the playing store (`[this + 8]`: `sb` = pattern, `r8` = step, `r5` = tick) and **at tick 0
of each step draws the random word** (`0x0804A6B8` `bl 0x0803C7F8`, `str r0, [r7, #4]`). It runs for muted tracks too
(mute skips only the play pass `0x0804A714`).

1. **Evaluate once a step** at `0x0804A6B8` (a `mid` hook: `r7` = player, `sb` / `r8` = pattern / step): read the
   step's condition, the pass count, the fill state, update PRE / NEI state, and store "this step fails" per player.
   Once a step matters for PRE (one roll a step) and keeps the 6 microstep calls consistent.
2. **Apply it where stock tests probability,** so a failed condition behaves exactly like a failed roll (ties and
   note-offs as stock):
   - note tracks: `0x08040D8A` (`ldrb r0, [r5, #1]; cmp r0, lr; blo`) in `seq_units_start` (upstream's `c_rfmask`
     site, 14 B);
   - drums: `0x0804AA18`–`0x0804AA1E` in the hit test, **and** `0x080411F6`–`0x080411FC` in slot 4 (else a
     suppressed step still switches the drum to its flip sample).
3. Upstream's drum version (`c_dqplay`) instead wrapped the stock hit call `0x08041252` from its rollers' code.

PL19 (playback strum) plans entry hooks on `seq_play_step` and nearby; these sites are different instructions, but the
plan should check that the hooks stack.

## Budget: which encodings fit where

| Place | Bits a step | Elektron fixed set (A:B, !A:B, FILL, !FILL, FIRST, !FIRST, PRE, !PRE, NEI, !NEI, LAST, !LAST ≈ 80 codes) | Pass mask, cycle 2-8 (≈ 11 bits; 508 distinct masks) |
|---|---|---|---|
| Drum micro bits 6-7 | 2 | no (4 states) | no |
| Drum `+0x88 + s` | 8 | **yes** (one code byte) | cycles 2-7 only (a leading-one code: v = 2^L + mask, L = 2..7, 252 codes, plus a few specials) |
| Drum `+0x88 + s` + 1 bit from `+0x84..+0x87` | 9 | yes | **yes**: v = 2^L + mask, L = 2..8; the all-zero and all-one mask of each length are redundant, so 14 codes are free for FILL / FIRST / PRE / NEI / LAST and their negations |
| Note `[2]` + `[3]` | 16 | yes | **yes, with room**: e.g. bits 0-7 pass mask, 8-10 cycle length, 11-13 type, 14 negate, 15 spare |

A:B and NOT A:B are special cases of a pass mask (one bit set, or all but one), so the mask codes cover them.

## What CTPlay would need

**Drums (first):**
- A project mark in CTPlay's saved block. On the first condition written in a project, clear `+0x84..+0xA7` of all 32
  drum patterns (upstream's rule); in an unmarked project read every condition as "none".
- Writes: raw, to `+0x88 + s` (and `+0x84` bits). Not in the step store, so no store sync and no lost writes; still
  on the pad's release.
- Hooks to keep conditions with their hits: Duplicate `0x0803E2AA` (shown-target path: copy `+0x84..+0xA7` from the
  source image too), Clear step `0x0803E18A` and Clear pattern `0x0803E3B0` (zero them), copy 1-16 → 17-32
  `0x0803E93A`, paste step `0x0803DFAE`, Mutate `0x0803E6F0` (swap the condition bytes with the steps; a mid hook in
  its swap loop `0x0803E7A4`–`0x0803E806`, registers not traced). PL17's own writers (Euclid etc.) decide whether a
  Write keeps or drops conditions.
- Cheaper fallback for the copies: drop a condition whose step has no hit (velocity 0) when CTPlay meets it.

**Note tracks (second):**
- The same project mark (upstream builds wrote [2] / [3]).
- Writes: raw for other steps; through the step store for the editor's selected step.
- One hook: the step fill `0x0803D230` zeroes bytes 2-3 too (Clear step and Clear pattern).

**Both:** pass counters (128 B RAM) at `0x0802CD42`, reset at `seq_start`; the per-step evaluation at `0x0804A6B8`;
the probability-test hooks; a fill state (a held control: not in stock; needs a pad by the UI rules); row-4 LEDs
through `led_task`.

## Not confirmed (and what would confirm it)

**Builder check 2026-11-01** (emulation, `2026-11-01-trig-conditions-spike/`): items 1, 3, 5, 6, 7 and 8 are
settled there (`A-storage.md`, `B-counting.md`, `C-controls.md`; the spec has the results). In short: 1 confirmed,
and the drop happens whenever the target is the shown pattern, playing too; 3 confirmed (no reader; the note editor's
refresh only mirrors the selected step); 5 confirmed with the filter `fp == 0` and `r4`; 6 found (Play resets, the
waiting flags, the immediate path `0x0802C240`); 7 confirmed, but the hook moves to `0x0804A6C0`; 8 found
(`0x20039DE0` p0 = 1 means the editors do not follow the playhead). Item 2 no longer matters (the micro bits are not
used). Items 4 (Components) and 9 (playback on the device) remain.

1. **Drum Duplicate drops `+0x84..+0xA7` when stopped.** Emulation: write a mark in drum pattern 1, Duplicate it to 2
   stopped and playing through the real route, read pattern 2. Then the device.
2. **Micro bits 6-7 survive every stock edit** (table in section 1): emulation through the views, ending with a stock
   edit of the same step.
3. **No stock code reads pattern bytes 4..39 or step bytes [2] / [3] by a computed offset.** Emulation: fill them with
   a pattern, play a few passes, edit, save; compare the audio-path calls and the bytes against a clean run.
   Upstream's device runs (SC39, SC403D) cover part of it.
4. **Components accepts non-zero [2] / [3] and bytes 4..39** (and micro bits 6-7, if used): a Components backup and
   restore of a marked project.
5. **Counting at `0x0802CD42` matches a pass** for every direction, first / last step setting, chains and scenes, and
   per drum: emulation with the real tick (upstream counted only note tracks, emulation only; "the sequencer running"
   was not checked).
6. **What Play resets** (chain start, step 1) and when the look-ahead store changes (for LAST): emulation of Play /
   Stop / queued pattern changes.
7. **The tick-0 hook at `0x0804A6B8` runs before the step's first microstep for both classes, at every sync rate**
   (rates below 1/16 go through `0x0804A2E8`): emulation.
8. **What `0x20039DE0` p0 is** (assumed pattern follow): emulation of Shift + Patterns.
9. All of it on the device: a diagnostic build that reports the pass counter and the per-step result over LEDs or
   MIDI would settle playback timing, as upstream's SEQWD did for the player.
