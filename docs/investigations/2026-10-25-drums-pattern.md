# Drum pattern data and how to write it safely (research, 2026-10-25)

Scope: the data a "Pattern tools per drum" writer (Euclid fills, with Undo) would write, and the stock paths that keep it.
Not the drum views or pad routes.

Status tags: **[asm]** I checked it in `re/app.asm` (and the stock `.bin` for literals / vtables); **[dump]** I read it in
the device RAM snapshot `ctre/Firmware-Analysis/ram_dump_firmware_0x08037988.bin` (the one slim's tests use);
**[upstream]** upstream's claim (file / NOTAS section), not re-checked; **[device]** confirmed on the device;
**[guess]** my inference.

Short version: the 4 drum step arrays are 128 B per pattern. Every drum has an **editing copy** of its current pattern:
the drum editor's 32-parameter step store. Any stock commit of that store writes all 128 B back into the pattern, so a
raw write to the mirrored pattern is lost at the next stock edit. Stock's own writers have one rule: **if the target
pattern is the one the editor mirrors, write it through the store and commit; if not, write the pattern raw.**

---

## 1. Where drum patterns live

### Addresses

| What | Address / formula | Status |
|---|---|---|
| Session record | `rec = [0x2003D71C + 0x14]` (`0x2001183C` in the dump) | [dump], slim `SESSION` |
| Drum d (0-3), pattern p (0-7) | `rec + 0xCD74 + 0x3540 × d + 0x6A8 × p` (8 × 0x6A8 = 0x3540 per drum) | [asm] settings getters `0x0803C6D6` / `0x0803C744` / `0x0803C790`, track ≥ 4: `rec + 0x3540 t + 0x6A8 p − 0x70C` = `+0x80` of that; [dump] |
| The same base, from the drum player | `[0x20040810 + 0x90 × d + 0x48] + 0x6A8 × p` (player vtable `0x0805B72C`) | [dump] `0x2001E5B0` = rec + 0xCD74; [asm] `0x08041252` |
| The same base, from the drum recorder | `[[0x2003C184 + 4 d] + 0x48]` (recorders `0x2003C174 + 4 t`, t = 4 + d; drum recorder vtable `0x0805A578`) | [dump] |
| The same base, from the drum editor | `[editor + 4]` | [dump], [asm] `0x0803F050` |
| In the `.ncs` file | the same offsets (the record is the file): drums at file `0x0CD74`, 54 528 B | [upstream] NOTAS "Estudio (2026-10-13): el fichero de sesión" |

8 patterns per drum, 32 steps per pattern, **0x6A8 = 1704 B per pattern**. The engine numbers drum d as **track 4 + d**
(Synth 1, Synth 2, MIDI 1, MIDI 2 = 0-3).

### Layout of one drum pattern (0x6A8 B)

| Offset | Size | Contents | Status |
|---|---|---|---|
| `+0x00 + s` | 32 × 1 | **velocity** of step s. 0 = no hit (stock's empty step) | [asm] hit test `0x0804AA08`, clear step `0x0803E18A` |
| `+0x20 + s` | 32 × 1 | **probability** 0..7; the hit plays when `prob ≥ (rand & 7)` (`[player + 4] & 7`), so 7 = always, 0 = 1 in 8. Empty step = 7 | [asm] `0x0804AA08`, `0x0803E18A` |
| `+0x40 + s` | 32 × 1 | **sample flip**: the sample the step's first hit plays, `0xFF` = none (the drum's chosen sample). Upstream: 64 samples (0..63) | [asm] `0x080411CA` (player slot 4); range [upstream] drumpat MUT |
| `+0x60 + s` | 32 × 1 | **microstep mask**: bit k (0-5) = a hit on microstep k (sixths of a step). Several bits = a roll. 0 = no hit. Bits 6-7: 0 in every file upstream read | [asm] `0x0804AA08` (`1 << micro`), player loops k = 0..5 at `0x080411F4`; bits 6-7 [upstream] NOTAS SC43 |
| `+0x80` | 1 | **last step** (0-31) | [asm] length = `[+0x80] − [+0x81] + 1` (+32 when last < first), `0x0802C206`, `0x0803E6FE`; [dump] `0F 00` = steps 1-16 |
| `+0x81` | 1 | **first step** | same |
| `+0x82` | 1 | **sync rate**, an index into the ticks-per-step table (`0x0805B8B8`; slim `step_ticks`: 2 3 4 6 8 12 16 24). 3 = 1/16 | [asm] `0x0803C744`; [dump] `03` |
| `+0x83` | 1 | **direction** (0..3) | [asm] `0x0803C790` |
| `+0x84..0x87` | 4 | unknown; stock reads only 4 settings bytes | [upstream] NOTAS "cadenas de patrones" |
| `+0x88..0xA7` | 32 | not used by stock, survive its edits (upstream's drumpat keeps one byte a step here, "DQ" projects only) | [upstream] NOTAS SC43 |
| `+0xA8 + 192 × L + 6 × s + k` | 8 × 192 | **automation lanes** L = 0..7, one byte per microstep, `0xFF` = no value. L 0-3 = the drum's knobs (ids 40 + 5d .. 43 + 5d), L 4-7 = the common parameters (ids 64 + d, 72 + d, 81 + d, 89 + d; L 7 = pan) | layout [asm] `0x0803E1D0` (clear step: 8 × memset 6 B at `+0xA8 + 6 s`, stride 0xC0); ids [upstream] NOTAS SC43.6 |

One hit = velocity ≠ 0 **and** a microstep bit set: `0x0804AA08(base, step, micro, rand)` tests velocity, probability,
then the bit [asm]. A step has one velocity, one probability and one sample flip for all its microsteps.

Dump example (drum 1, pattern 1): velocity `7C 00 00 79 78 00 00 75 …`, probability all `07`, flip `08 FF FF 08 …`,
micro `01 00 00 01 …`, settings `0F 00 03 00` [dump].

**Empty step** = velocity 0, probability 7, flip 0xFF, micro 0, its 48 lane bytes 0xFF: what stock's "clear step"
`0x0803E18A` writes [asm]. A newly built store (before it loads a pattern) holds velocity 0x60 instead
(`0x0804A11C`) [asm]. That value is never read: the store loads the pattern over it.

### Compared with a note track (what slim's Euclid writer does)

| | Note track (Synth 1/2, MIDI 1/2) | Drum |
|---|---|---|
| Pattern size | 0xCA8 (rec + 0x2E4 / + 0x1A27C, 8 per track) | 0x6A8 (rec + 0xCD74 + 0x3540 d) |
| Step data | 32 × 28 B, step-major: `[0]` unit mask, `[1]` probability, 6 units (note, length / tie, microstep, velocity) | 4 arrays × 32 B, array-major (velocity, prob, flip, micro) = 0x80 B |
| Settings | `+0x380` (last, first, sync, direction) | `+0x80` (the same 4 bytes) |
| Lanes | 12 × 192 B from `+0x3A8` | 8 × 192 B from `+0xA8` |
| Editing copy written back? | No: slim writes raw (masked) + `rec_touch` for the LEDs (PL08 spike, PL11 on the device) | **Yes**: the drum editor's step store (below) |
| Undo copy (ITCM) | 896 B (`STEPS_SIZE`) | 128 B (or 0x88 with the settings) |

---

## 2. The editing copy

### The objects (one set per drum)

| Object | Address (dump, drum 0; others) | What | Status |
|---|---|---|---|
| **Drum editor** (0x60 B, vtable `0x0805C108`, its store listener `0x0803EA1C`) | `0x2003ACD0`, `0x2003B1BC`, `0x2003B6A8`, `0x2003BB94`. Built at boot by `0x0803DDCC` (callers `0x0802DA6E…0x0802DAFE`, heap). Reach: `[0x200438DC + 0x3C d + 0xC] − 0x18`, or listener 0 of the step store | [asm] [dump] |
| `[editor + 4]` | the drum's pattern base (rec + 0xCD74 + 0x3540 d) | [dump] |
| `[editor + 8]` | the engine's playing store of track 4 + d = `[0x20038EC0 + 0x30 + 4 (4 + d)]` (`0x20039118 …`): p0 pattern, p1 step, p2 tick | [dump], [asm] listener `0x0803EBB0` |
| `[editor + 0x10]` | transport `0x20011034` (p0 playing, p1 Record, p2 count-in) | [dump]; meanings [upstream] |
| **`[editor + 0x18]` = the step store** (the editing copy) | `0x2003AD30`, `0x2003B21C`, `0x2003B708`, `0x2003BBF4`. Also `[drum recorder + 0x4C]` and `[[0x200438DC + 0x3C d + 0xC]]` | [dump] |
| `[editor + 0x1C]` = settings store | p0 halfword ↔ `+0x80/+0x81`, p1 ↔ `+0x82`, p2 ↔ `+0x83` | [asm] `0x0803EB0E`, `0x0803F0CA` |
| `[editor + 0x20]` = **position store** | p0 = **the pattern the editor mirrors**, p1 = the selected step. Also `[drum recorder + 0x14]` | [asm] `0x0803E18A`; [dump] |

**The step store** (stock's generic double-buffered parameter store, functions at `0x08035324…0x080355D4`) [asm]:

- `[0]` = 0x20 parameters (words), `[1]` = 5 listener slots (**all 5 used** in the dump: no room for a listener of
  ours), `[4]` = which buffer each parameter is read from, `[8]` = dirty mask, `[0xC]` / `[0x10]` = the two buffers,
  `[0x14]` = listeners (obj, mask), **`[0x18]` = the pattern + 0xA8** that it mirrors (set by the load; the drum
  store's own extra field).
- Parameter k = 4 steps of one array, step `4k + i` in byte i: **0-7 velocity, 8-15 probability, 16-23 micro, 24-31
  flip** (raw arrays `+0x00`, `+0x20`, `+0x60`, `+0x40`) [asm] setters below; matches upstream drumstore.py.
- `0x0803542C(store, k)` = read pointer. `0x080354FA(store, k)` = write pointer (first write after a commit copies
  read → write and sets the dirty bit). `0x080353C0(store)` = commit (flips the read buffer of the dirty
  parameters, calls each listener whose mask meets the dirty mask, clears it). `0x08035398(store, obj, mask)` = set
  a listener's mask (0 = detach). `0x08035456(store)` = mark every parameter dirty, return the write buffer.
- Byte setters `(store, step, value)`: velocity `0x0804A21C`, micro `0x0804A244`, probability `0x0804A270`, flip
  `0x0804A29C`. Getter `0x0804A2C8(store, step)` = the step's velocity, so stock's views treat "velocity ≠ 0" as
  "has a hit".

Step-store listeners (dump, drum 0) [dump]:

| Listener | vtable → fn | Mask | What it is |
|---|---|---|---|
| `0x2003ACD0` drum editor | `0x0805C108` → `0x0803EA1C` | all | **writes all 32 steps × 4 arrays into the pattern** |
| `0x2004309C` | `0x0805AD38` → `0x0804E7CA` | velocity + flip | drums' Note view (step LEDs) [guess: next to class `0x0805AD44`] |
| `0x20043544` | `0x0805ADA8` → `0x0804EFB0` | velocity | velocity view [guess] |
| `0x20043654` | `0x0805AAD0` → `0x0804F1EE` | velocity + micro | microstep view [guess] |
| `0x200438E4` | `0x0805AB40` → `0x0804F320` | velocity + probability | probability view (Pattern Settings twice), row 3 redraw [upstream] drumpat; [dump] |

### When stock loads and writes back

- **Load** `0x0803F050(editor)` [asm]: for the 32 steps, the four setters from pattern `[editor+4] + 0x6A8 × pos.p0`,
  then `[store + 0x18] = pattern + 0xA8`, **detach the editor** (`0x08035398(store, editor, 0)`), commit (only the
  views refresh), re-attach (mask −1), then the settings store from `+0x80 / +0x82 / +0x83`. Runs when the position
  store's pattern changes (`0x0803ED6E`). A load never writes the pattern.
- **The editor follows the playing pattern**: on a change of `[editor + 8]` (the engine's playing store), unless
  `[editor + 0x24]` p0 or `[editor + 0x5C]` p0 (`0x20039DE0`, shared by every editor) is set, it copies p0 / p1 into the
  position store and loads (`0x0803EBB0…0x0803EBEE`, `0x0803ED2A…0x0803ED62`) [asm]. What those two flags are is not
  traced [guess: a pattern being viewed or held in the Patterns view].
- **Write back**: `0x0803EA1C` (store == `[editor + 0x18]`) copies **every** step of the store's read buffer into all
  four arrays of pattern `pos.p0` [asm]. It runs on **any commit with any dirty bit**, so one stock step edit, a
  probability change or one live-recorded hit puts the whole 128 B back. That is why raw writes are lost (upstream's
  finding in emulation: roller / drum-arp hits and Nudge vanished; NOTAS SC43) [asm] + [upstream].
- Automation lanes and settings are **not** in the step store. Stock writes lanes directly into the pattern
  (memcpy / memset), so raw lane writes stay [asm] `0x0803E1D0`, `0x0803E364`.

### Stock's own pattern writers (all UI-side, on the drum editor)

Dispatcher around `0x0802DC14…0x0802E186`: editor of track t = `[container + 0x98 + 4t]`, so drum editors sit at
`+0xA8 + 4d` [asm].

| Function | What | How it writes | Status |
|---|---|---|---|
| `0x0803E2AA(editor, src, p)` | paste a whole 0x6A8 B pattern image into pattern p (Duplicate) | stopped: first makes p the editor's pattern. **p mirrored**: 32 × store write + commit (the listener writes), lanes memcpy 0x600, settings store. **Not mirrored**: raw memcpy 0x6A8 | [asm] |
| `0x0803E3B0(editor, p)` | clear pattern p | the same two paths (store, or memset of the arrays) | [asm] |
| `0x0803E18A(editor)` | clear the selected step | setters + commit, lanes memset 0xFF | [asm] |
| `0x0803DFAE(editor, step, vel, micro, flip, prob, lanes)` | paste one step | lanes memcpy, setters, `0x08035456`, commit | [asm] |
| `0x0803E6F0(editor, …)` | Mutate: random step shuffle (draws `0x0803C7F8`; called Nudge here until 2026-10-28) | **raw** writes to the arrays and lanes, then reload of the store over the range, `0x08035456`, **detach editor, commit, re-attach** | [asm] |
| `0x0803E93A(editor)` | copy steps 1-16 to 17-32 | setters, lanes memcpy, commit | [asm] |

The Mutate pattern (`0x0803E6F0`) is the one to copy: raw write, then the store brought in line with the editor
detached, so that commit only refreshes the views.

### Upstream's writers

- **`drumstore.py`** (SC43, [upstream], emulation only, not device-confirmed): `emit_sync(player, step, base)` /
  `emit_syncall(drum, base)`: when `[store + 0x18] == base + 0xA8`, for each touched parameter it reads the raw
  word from the pattern and stores it at **both** `0x0803542C(store, k)` and `0x080354FA(store, k)` (both buffers
  equal, dirty bit set, **no commit**). The store is reached as `[[0x200438DC + 0x3C d + 0xC]]` (checked:
  `[view + 0xC]` = editor + 0x18 [dump]). With no commit the views are not refreshed until stock's next commit [guess].
- Users: `rollers.py` (`use_v2` records raw from the player slot 2 = Main task, `use_sync` → `c_rlsync`),
  `drumarp.py` (`use_rec` raw in `c_daplay`, `use_sync` → `c_dasync`), `quant.py` (SC43.7 Shift + Play quantise:
  raw rewrite of first..last, then `emit_syncall`), `playmode.use_dsync` (Nudge rotates upstream's +0x88 bytes too,
  then `emit_syncall`) [upstream].
- **`scpat.use_drums()` (SC43.8) is not a pattern writer**: it is the sidechain source "note-track pattern triggers
  a drum's sidechain" (X:$3BF2…) [upstream] NOTAS SC43.8. The quantiser is `quant.py`.

### Masking, task, dirty marks, saving

- **Task**: stock's editors run from the UI (pad / button handlers). The drum recorder writes the same store from the
  **Main task** (below), and the player reads the arrays in Main. slim's note writer assumes Main can preempt the UI
  task (it masks its 896 B copy); assume the same here [guess, from slim's euclid.c comment].
- **Masking**: the commit runs up to 5 listeners (LED redraws), too long to mask. Mask only the raw write of the 128 B
  plus the copy into both store buffers. Commit afterwards, unmasked.
- **DSP dirty marks / MARK_DIRTY (`0x0803BDCC`)**: not involved. The pattern is ARM-only data the player reads at each
  step. No DSP group, no lock [asm: none of the paths above call it].
- **Saving**: the arrays are part of the session record. Stock's Save writes the record whole. slim's note writer
  marks nothing and PL11's written patterns survived Save / power cycle / load (PL11 TEST.md step 13) [device, for
  notes]; the same holds for drums [guess, same record].

---

## 3. The drum recorder (live hits)

Drum recorder d = `[0x2003C184 + 4d]` (`0x2003CD44`, `0x2003CDB4`, `0x2003CE24`, `0x2003CE94`), vtable `0x0805A578`
[dump]. Fields [dump]: `+0xC` engine playing store, `+0x10` engine "next" store, `+0x14` the editor's position
store, `+0x18` transport, `+0x24` settings store `0x200111CC`, `+0x35` record quantise, `+0x48` pattern base, `+0x4C`
the step store, `+0x50` the sync-rate store, `+0x54` the pending velocity.

| Slot | Fn | Drums | Status |
|---|---|---|---|
| 0 | `0x0803FC5E` | note-on (shared with note recorders): position by `0x0803FD32`, then slot 3 | [asm] |
| 3 | `0x0803F98A` | **only stores the velocity at `[rec + 0x54]`** (pending hit) | [asm] |
| 4 | `0x0803F992` | note-off: `bx lr` (drums have no length) | [asm] |
| 5 | `0x0803F9A2` | from the recorder's store listener `0x0803FE24` (thunk `0x0803FE22`, call at `0x0803FEC2`): the engine's tick → **Main task**. Quantise on (`[rec + 0x35]`, Shift + Record): writes microstep 0 at the step's half tick; off: microstep = `0x0804A314(tick offset, sync rate)` = 0..5 | [asm]; Main task [guess, from symbols.toml "recorder's tick processing, Main task"] |
| 6 | `0x0803F9F8` | the same write from `0x08040074` (flush / lane path) | [asm] |
| — | **`0x0803FA26(rec, pattern, step, micro)`** | the write: nothing if `[rec + 0x54]` = 0. **pattern == editor's pattern** (`[rec + 0x14]` p0): store: velocity = pending (overwrites), micro |= 1 << micro, probability = 7, **commit** (the listener writes the pattern). **Else raw**: the same three bytes in the pattern. Flip and lanes untouched. Then `[rec + 0x54]` = 0 | [asm] |

So live hits **do** keep microsteps when record quantise is off, and a recorded hit is a store commit made from Main
while Record is armed.

Upstream's **rollers / drumarp do not use this recorder**: they write the arrays raw from the player's slot 2
(`0x08041252`, Main) and then `drumstore.emit_sync` (velocity only on an empty step, OR the microstep bit; drumarp
also flip, and probability 7 on an empty step) [upstream] rollers.py `use_v2` / `use_sync`, drumarp.py `use_rec`.

---

## 4. Current pattern, chains, sharing

- **The pattern a drum plays**: `[0x20038EC0 + 0x30 + 4 (4 + d)]` p0 (p1 step, p2 tick). Slim's `ENGINE + ENG_PATTERN
  + 4t` with t = 4 + d. "Next" (what the UI shows) at `+0x70 + 4t`. Chain (first, last pattern) `[E + 0x9C]` p(t).
  The chain advance `0x0802CB3C` can move it at any step end, in Main [upstream] NOTAS "cadenas de patrones"; [dump]
  for the drum stores.
- **The pattern the store mirrors** = `[editor + 0x20]` p0 = `[drum recorder + 0x14]` p0. It is normally the playing
  pattern, but not always (the `[editor + 0x24]` / `[0x20039DE0]` cases, and stopped paste / clear switch it). Test
  "is this pattern mirrored" by `[step store + 0x18] == base + 0xA8` (upstream) or by `[rec + 0x14]` p0 == p
  (stock's recorder); both read stock state [asm].
- **8 independent patterns per drum**, no sharing between drums. Each drum chains on its own (track 4 + d). A write
  must pick its pattern number, its first / last step (`+0x81` / `+0x80`) and read them all in one masked section,
  as slim's `euclid_write_to` does: the chain can move between two reads.
- **Mute** (Mixer) = `[player + 0x28]` p0. The player skips the whole step, but the pattern data are unchanged
  [upstream] NOTAS SC43.8. Not relevant to writing.

---

## Open questions (only a device run or emulation can settle)

1. **Does the store path refresh every drum view on the device?** Write + commit should relight the Note view's step
   pads, the velocity, microstep and probability views. Run it in emulation through the real view routes, then on the
   device (the PL11 step 9 lesson: stale LEDs).
2. **What `[editor + 0x24]` and `[0x20039DE0]` p0 mean**, and when the mirrored pattern is not the playing one
   (Patterns view held, chain edit, stopped with another pattern selected). This decides which pattern "current" means
   for the writer.
3. **Task priorities**: can Main preempt the UI between our store write and the commit, and does the recorder commit
   then (Record armed, playing)? Emulation can count it; only the device shows the timing. It is simplest to refuse
   or defer a Write while Record is armed and playing.
4. **Upstream's drumstore path is emulation-only** (SC43 "pendiente de probar"). No drum-array write of upstream's is
   recorded as device-confirmed.
5. Whether stock clears microstep bits 6-7 or the `+0x84..0x87` settings bytes on its edits (upstream says it clears
   bits 6-7; the setters write whole bytes). This matters only if CTPlay wants to keep its own data there.
6. Sample-flip range (64 samples?) and whether the flip-lane automation (id 44 + 5d, recorder slot 8 `0x08059A2C`)
   writes the `+0x40` array raw. If it does, it has the same lost-write problem, which is stock's business but could
   show up in a test.
7. Whether a drum pattern saved after a CTPlay write loads identically (expected, since it is the same record: one
   Save / power cycle / load step, as PL11's step 13).

## What a CTPlay drum writer would need

**Pointers** (all from objects slim already uses or the same heap layout; add them to `slim/stock/symbols.toml` /
`memory.toml` with these sources):

- drum recorder `drec = [0x2003C174 + 4 (4 + d)]` → `drec + 0x48` base, `drec + 0x4C` step store, `drec + 0x14`
  the editor's position store. The editor itself = listener 0 of the step store, or `[0x200438DC + 0x3C d + 0xC] −
  0x18`. Check `[editor] == 0x0805C108` before use.
- playing pattern: `param_get([0x20038EC0 + 0x30 + 4 (4 + d)], 0) & 7` (as euclid's `current_pattern`, t = 4 + d).

**Functions** (slim stock symbols to add; all [asm]): `0x0803542C` param_get (already used), `0x080354FA`
param_wptr, `0x080353C0` store_commit, `0x08035398` store_set_listener, `0x08035456` store_touch_all. Optional:
`0x0803F050` editor_load (reload store from pattern; it also recommits the settings store), and the byte setters
`0x0804A21C` / `0x0804A244` / `0x0804A270` / `0x0804A29C`.

**Write recipe** (copies stock's drum Mutate `0x0803E6F0`):

1. Before masking: work out the 32 steps (velocity, micro mask, probability, flip) into a 128 B buffer.
2. `slim_irq_save()`. Re-read the target (pattern number, first / last), copy the old 128 B to the ITCM Undo buffer
   with the (drum, pattern) tag, write the 4 arrays raw. If `[store + 0x18] == base + 0xA8`, also write the 32 words
   into **both** buffers (`[store + 0xC]` and `[store + 0x10]`, or param_get + param_wptr per parameter as upstream
   does). Restore.
3. Unmasked, mirrored only: `store_touch_all(store)`, then commit. Either detach the editor around the commit like
   stock (`set_listener(store, editor, 0)` … `(…, −1)`) or let it rewrite the identical bytes. This refreshes the LEDs.
4. Undo = the same steps with the saved 128 B (swap, as euclid's `swap_undo`).

Leave alone: lanes `+0xA8…`, settings `+0x80…` (let the Pattern Settings length decide first..last), upstream's
`+0x88` bytes. For a new hit, write velocity ≥ 1, micro bit 0 (`0x01`), probability 7 and flip 0xFF (or the old
step's flip). An empty step is velocity 0, micro 0, probability 7, flip 0xFF.

**Risks:**

- **A raw write without the store sync is lost** at the next stock edit of that drum (whole 128 B).
- **Writing the store of a pattern it doesn't mirror** would make the listener write it into the *wrong* pattern
  (the editor's `pos.p0`): always test `[store + 0x18]` first.
- **Recorder race** (Main commits the same store while Record is armed): defer or refuse during recording, or accept
  that the recorder's commit carries our values (both buffers equal) [guess].
- **Phantom pad press**: run the write on the pad's release (`euclid_release` rule), never in the press.
- **Mask only the 128 B + 64 words**, not the commit (listeners redraw views).
- **Heap addresses**: editors and stores are heap objects (deterministic at boot, as upstream's fixed `0x200438DC`
  relies on). Go through the recorder pointers, and check the vtables `0x0805A578` (recorder) and `0x0805C108`
  (editor).
- **The step store has no free listener slot** (5 of 5 used): CTPlay cannot listen to drum edits through it. It would
  need a hook (e.g. on `0x0803EA1C`) if it wants to know about them, such as to drop an Undo after a stock edit.
- The Undo buffer must be dropped on a project load (as `euclid_undo_at`), and after a stock edit of that pattern if
  Undo should not undo the user's later edits.
