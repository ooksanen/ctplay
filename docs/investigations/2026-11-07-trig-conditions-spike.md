# PL20 Task 1 spike: hook arguments, tasks, stores, Components (emulation, 2026-11-07)

The first step of building PL20 ([the design](../specs/2026-10-28-trig-conditions-design.md)). Builds on the builder
check [`2026-11-01-trig-conditions-spike/`](2026-11-01-trig-conditions-spike/) (`A-storage.md`, `B-counting.md`,
`C-controls.md`; its `*_lib.py` are reused). Stock image (`stock/circuittracks-firmware-4486-STOCK.bin`) and the device
RAM snapshot, Unicorn; every edit through its real route (controller `0x08033320` / `0x08033282` / `0x080332CE`, the
Play button, the 1 ms Main service). The count-in check uses PL19 built from the current sources
(`../.venv/bin/python -m slimbuild versions/PL19.toml`, `build/PL19/`). Nothing here is checked on a device.

Run from `slim/`: `PYTHONPATH=.:tests:../tools:docs/investigations/2026-11-01-trig-conditions-spike:docs/investigations/2026-11-07-trig-conditions-spike
../.venv/bin/python docs/investigations/2026-11-07-trig-conditions-spike/<script>.py`. Each script's run is beside it
as `<script>.out`. Shared code: `q_lib.py` (a_lib.H plus a calling context per emulated call, entry logs, Python
"handlers" at a PC that do what a slim hook would, a crude backtrace). Seconds each, except `q3_tasks.py` (~6 min) and
`q5_removals.py` (~2 min).

"A simulated handler" below = Python run at the hook's address before stock's instruction there, doing exactly what
Task 8 / 9's C handler would; the result is then read in the pattern after stock finished.

## Summary

| Q | Answer | Plan change |
|---|---|---|
| 1 | Every Task 1 row's arguments found; all reached from the UI task. Duplicate: an entry copy source → target is right in every case. Copy half: 1-16 → 17-32 only. Paste: the source is the shared copy record (any drum). `drum_remove`'s r0 is a listener, not a view. `seq_place`: r1 = track from all three callers. | hook table rows; Tasks 4, 8, 9 |
| 2 | Mutate: mid hook at `0x0803E78E` (`0199019a`, 4 B): r4 / r3 = the two steps, r1 = r2 = the pattern, once per swap. No fallback (G3 not needed). | `drum_mutate` row; Task 8 |
| 3 | `0x0804A6C0` and `0x0802CD42`: Main only in every scenario (Play, count-in, loads, picks, scenes). Each scene takeover reaches every track's `fp == 0` event exactly once with the scene flag; a hand pick has hand 1, scene 0. G2 not triggered. External MIDI clock not covered. | `seq_place` row (args, contexts) |
| 4 | The handler's reading matches the step stock's row 3 edits in every accept case. Two catches for notes: the selected step can move between the row-4 press and its release, and a stale store's word 0 reverts the pattern's `[0]` / `[1]` when committed. | Task 6 behaviour |
| 5 | One route not in the plan: the **drum micro-step view** (Gate on a drum) removes a hit when its last micro bit is turned off. Mid hook `0x0804F104`. Notes: none beyond `note_pad_press` and Clear step. | new row `drum_micro_off`; Task 9 |
| 6 | No string names pattern bytes 4-39 or step bytes 2-3; the only padding / spare / reserved checks are in the header, timing and chain tables. G1 not triggered. | none |

## 1. Arguments (`q1_drums.py`, `q1_toggle.py`, `q1_notes.py`; `seq_place` in `q3_tasks.py`)

**The drum editor.** The pattern-command dispatcher `0x0802DBC0` (ip = r0 - 4 = `0x20039C5C`) passes track t's editor
`[ip + 0x98 + 4 t]` (drums: `[0x20039C5C + 0xA8 + 4 d]`), the same object as `a_lib.deditor(d)` = `[0x200438DC + 0x3C d
+ 0xC] - 0x18` (`q1_drums.out`, "editor table": True for all 4 drums and all 4 note tracks). In every drum function
below r0 is that editor:
- `[editor + 4]` = the drum's 8 patterns (`[recorder + 0x48]`, checked for every call: "[r0+4]=patterns True");
- `[editor + 0x20]` = the position store, p0 = the shown pattern, p1 = the selected step (0-31);
- `[editor + 0x18]` = the drum's step store; `[editor + 0x10]` p0 = the transport (playing);
- `[editor + 0x54]` = `0x20039C8C` = ip + 0x30 for all four drums: the shared **copy-step record** (byte 0 = 2 after a
  copy, 1 = the source track 4 + d, 2 = its pattern, 3 = its step; written by the copy `0x0803DF72`, asm
  `0x0803DF7C`-`0x0803DF96`, and the dispatcher's `strb.w r0, [ip, #0x31]` at `0x0802E11E`).

The drum a handler acts on = the index d with `[0x20039C5C + 0xA8 + 4 d] == r0` (or `[0x200438DC + 0x3C d + 0xC] - 0x18`).

| Point | Registers at entry (measured) | Drum, pattern, step(s) |
|---|---|---|
| `drum_duplicate` `0x0803E2AA` | r0 = target drum's editor, r1 = **source pattern address** (any drum's), r2 = target pattern index | target = `[r0 + 4] + 0x6A8 r2`; source = r1 |
| `drum_clear_step` `0x0803E18A` | r0 = editor only | pattern = `[r0 + 0x20]` p0, step = p1 (stock reads them itself, asm `0x0803E18E`-`0x0803E1A0`) |
| `drum_clear_pattern` `0x0803E3B0` | r0 = editor, r1 = pattern index | `[r0 + 4] + 0x6A8 r1` |
| `drum_copy_half` `0x0803E93A` | r0 = editor only | pattern = `[r0 + 0x20]` p0; steps 0-15 → 16-31, always |
| `drum_paste_step` `0x0803DFAE` | r0 = target editor; r1 = source velocity, r2 = source flip, r3 = source micro, `[sp]` = source probability, `[sp + 4]` = source pattern + 0xA8 (caller `0x0802E12C`-`0x0802E166`) | target = `[r0 + 0x20]` p0 / p1; source = the copy record `[[r0 + 0x54]]`: track `[1]` (4 + d), pattern `[2]`, step `[3]` |
| `note_step_fill` `0x0803D230` | r0 = the note editor, r1 = a 28 B step | Clear step: r1 = the edit store's write buffer (from touch-all `0x08035456`, `0x0803D1DE`); Clear pattern: r1 = pattern + 28 s, 32 calls (`0x0803D354`-`0x0803D364`) |
| `drum_step_off` `0x0804EC3E` | r0 = the drum step view (class `0x0805AD0C`, one object per drum: `0x20043094` drum 1, `0x200431A4` drum 2), r1 = step 0-31 | drum = the editor whose `[+ 0x18]` == `[r0 + 0xC]`; pattern = that drum's shown pattern |
| `drum_remove` `0x080500B2` | r0 = the drum's **flip listener** (class `0x0805C150`, `0x20043FC8` drum 1, `0x20043FE0` drum 2), not a view; r1 = step 0-31 | drum = the editor whose `[+ 0x18]` == `[r0 + 8]`; pattern = the shown one |
| `seq_place` `0x0802C240` | r0 = engine, r1 = track 0-7 (`uxtb` at each caller), r2 = the song tick to place at, r3 = 1 from `seq_start` (it then updates the chain-done bits `[E + 0xFC]`), 0 from the engine listener | — |

Details and cases:

- **Duplicate** (`q1_drums.out`, cases A-I): a simulated entry handler copying the 36 bytes `r1 + 0x84` → `[r0 + 4] +
  0x6A8 r2 + 0x84` leaves the target's `+0x84..+0xA7` equal to the source's in **every** case: stopped (target shown
  or not), playing with the source / the target / neither shown, drum 1 → drum 2 stopped and playing (target shown or
  not), and a pattern onto itself; arrays, lanes and the source are what stock alone gives; no other pattern's bytes
  change. In the non-shown branch stock's memcpy (`0x0803E3AC`) then copies the same bytes again. Stock commits the
  target as the shown pattern first when stopped (`0x0803E2BE`-`0x0803E2CC`), before its test at `0x0803E2DC`; no
  stock writer touches `+0x84..` in between (A-storage.md Q2). So the hook needs no branch test.
- **Clear step**: the step is the pad pressed (stock selects it first): pad 3 → step 3; on the 17-32 page pad 4 →
  step 20; playing (follow on), pad 6 → step 6 (p1 = 6 at entry, the selection moves on afterwards). Only that step's
  arrays change.
- **Clear pattern**: shown (stopped), not shown (playing pattern 3, Clear on pattern 2), shown = playing, drum 2's
  column: r1 is the cleared pattern every time, r0 that column's drum.
- **Copy half**: with 1-16 shown and with **17-32 shown**, stock copies steps 0-15 → 16-31 (16-31 = 0-15 of before,
  0-15 unchanged). There is no 17-32 → 1-16 (asm: the loop `0x0803E944`-`0x0803E9DA` writes step `sl + 16` from the
  store's step `sl`, `sl` 0-15). The source values come from the step store, i.e. the shown pattern.
- **Paste**: same page 4 → 8; 17-32 page 21 → 26; the page switched while Duplicate is held (4 → 26); **another drum**
  (Duplicate held, step 4 of drum 1, Drum 2's button, step 8: drum 2's step 8 gets drum 1's step 4, through drum 2's
  editor); an empty step onto a hit (velocity 0 pasted: a removal, the code goes with it). A simulated handler reading
  the source from the copy record and the target from `[r0 + 0x20]` p0 / p1 leaves the target's code = the source's
  in all five.
- **note_step_fill** (`q1_notes.out`): Clear step 1-16 / 17-32 / playing: one call, r1 = the edit store's write buffer,
  the cleared step = the pad's (3, 20, 6); a simulated handler zeroing `[r1 + 2]`, `[r1 + 3]` leaves `[2]`/`[3]` 0 on
  that step only (stock's commit carries the buffer into the pattern). Clear pattern shown / not shown: 32 calls, r1 =
  each step of the cleared pattern, all 32 zeroed, other patterns kept. Always the UI task.
- **drum_step_off** (`q1_toggle.out`): reached only in the drum step view (mode 1), on the **release** of a step pad
  (the toggle `0x0804EC8A` is called from the release path `0x0804E49E`), when the step had a hit; a step pad in the
  velocity, gate (micro) and probability views (modes 2, 3, 5) only selects. Also reached for a held step pad's
  release after another step pad was pressed (`q5_removals.out`: "step 4 held + pad k" empties step 4). A hold of
  600 ms then release: no toggle. Step = absolute (21 → 20 on 17-32). Playing pattern 3 (shown 2): the shown pattern's
  hit goes.
- **drum_remove**: drum step view, a step pad held and a lower pad (16-31 = the sample pads) pressed: the flip
  listener `0x0804FF18` runs on the press; when the step's flip sample (`0x08052780`) equals the pad's sample, stock
  removes the hit (`0x0804FFB8` → `0x080500B2`: velocity 0, micro 0, probability 7, flip 0xFF); otherwise it sets the
  flip (adding a hit, velocity 96, on an empty step: `0x08050062`). Drum 1, step 4 with flip 2: lower pad 18 removes;
  every other lower pad changes the flip. `[r0 + 4]` p0 = the sample, p1 = the held step (= r1).
- **seq_place**: see section 3 (contexts) — r1 = 0-7 from `seq_start` (`lr 0x0802C1B0`, all 8 tracks), 0 from the
  listener's "at once" call (`0x0802B94C`, Shift + Patterns pad, the picked track) and 0 / all from the stopped call
  (`0x0802B9BE`, a pick while stopped: the picked track; a scene chain / load: all eight).

## 2. Mutate (`q2_mutate.py`)

`hooks.check_mid` over every 4 / 6 B span from the swap's first instruction after `beq.w` (`0x0803E78A` skips a swap
with itself) to the lanes loop (`0x0803E812`): many pass (table in `q2_mutate.out`). Chosen:

**`0x0803E78E`, mid, expect `0199019a` (`ldr r1, [sp, #4]; ldr r2, [sp, #4]`), displace 4.** After the displaced
loads: **r4 = step a** (the position, `0x0803E770`), **r3 = step b** (its random partner, `0x0803E784`), **r1 = r2 =
the pattern address** (`[sp + 4]` = `[editor + 4] + 0x6A8 × shown`, `0x0803E750`). Once per swap: the site is after
the `beq.w` at `0x0803E78A`. The handler swaps the two steps' codes (byte `+0x88 + s` and bit `s & 7` of `+0x84 + (s >>
3)`); before or after stock's own swap makes no difference (it touches neither).

Emulation (drum 1, 9 hits, distinct codes on all 32 steps, six Mutates in a row through Shift + Duplicate): handler
calls = the swaps stock made (26-30 per Mutate), the pattern = the shown one, and after each Mutate every step's
(velocity, probability, flip, micro, code) is one of the tuples before: the codes moved with the hits. The same at
`0x0803E80A` (`ldr.w ip, [sp, #4]`, after the arrays' swap; ip = pattern). Control without a handler: the check fails
(codes stay while hits move). **G3 not triggered**: Mutate gets a real hook, no fallback edit anywhere.

## 3. Tasks (`q3_tasks.py`)

Every emulated call carries its context: `ui` (a controller button / pad call), `ui:led` (the LED frame, where
CTPlay's count-in presses Play), `main` (the 1 ms service), `direct:0x0802FD5C` (the load's read-done handler, called
as `tests/test_saved.py` does). Per scenario, the contexts in which each point was reached (`q3_tasks.out`):

| Scenario | `player_tick` 0x0804A6C0 | `track_advance` 0x0802CD42 | `seq_place` 0x0802C240 (caller) |
|---|---|---|---|
| Play from stop | main | main | ui (`seq_start`, all 8 tracks) |
| Stop, Shift + Play (continue) | main | main | — |
| Patterns tap / a hand chain while playing | main | main | — (waits for the pattern end) |
| Shift + a Patterns pad while playing | main | main | ui (`0x0802B948`, the picked track) |
| A pick while stopped | — | — | ui (`0x0802B9BA`, the picked track) |
| A scene recalled by hand while playing | main | main | — |
| A scene chain advancing by itself | main | main | ui only (the setup's picks and the Play press) |
| A load, stopped / playing | — / main | — / main | the load's handler (`0x0802B9BA` / `0x0802B948` and `seq_start`, all 8) |
| CTPlay's count-in start (PL19) | main (the first tick-0 pass too) | main | ui:led (`seq_start`) |

**`0x0804A6C0` and `0x0802CD42`: Main only, in every scenario.** The Play press, the count-in's Play (from the LED
frame) and the load reach `seq_start` / `seq_place` directly but never the player tick or the track advance; the first
step's tick 0 runs at the next heartbeat. **G2 not triggered.**

**Scene takeovers:** at each takeover tick every track's `0x0802CD42` with `fp == 0` and the scene flag set is reached
**exactly once** (8 / 8): the hand recall (Drum 1 16 steps; Synth 1 at 6 steps cut, the others ended) and four
advances of a scene chain (Synth 2 at 6 steps cut each time). `[sp + 0x18]` (hand) reads 1 at all of them, ended or
cut (as B-counting.md: while a scene changes it carries the scene flag), which is why Task 4 tells them apart with
`scene_wait` latched at `seq_tick`'s entry.

**A pick by hand:** Synth 1 tapped to pattern 2 and Drum 1 given a chain 1..3 by hand (hold pattern 1, press pattern
3), while playing: at the takeover (tick 48) each has one `fp == 0` event with end 1, **hand 1, scene 0**; no other
track had hand 1.

**`seq_place`'s contexts:** the UI task (Play, Shift + a Patterns pad, a pick while stopped, the count-in's Play), the
load's handler, and (static) Main: `seq_tick` itself calls `seq_start` → `seq_place` at `0x0802C4DC` when the engine's
flag `[E + 0xA5]` is set (written by the engine's message handler `0x0802BC10`, vtable entry `0x08059894`; not reached
in these runs). The plan's `context = "any"` and the posted start-over (`trig_restart`) fit all of them.

Not covered: an **external MIDI clock**. `seq_tick` is a tail call of the clock listener `0x0802B8FC`; with the
internal clock that is the Main task's 1 ms service (symbols.toml `seq_tick`), with an external clock it is wherever
the clock store is committed (the same open point as PL06-PL19's "external MIDI clock not tested").

## 4. Stores (`q4_stores.py`)

**The handler's reading = the step stock's row 3 edits**, in every accept case (Synth 2 and Drum 1; step 6 selected
beforehand; row 4 pressed first, its handler's reading logged at the view's pad handler, then row 3 in the same
state):

| Case | Notes: `[editor + 0x24]` p0 / p1, editor = `[view + 0xC]` - 0x18 | Drums: `[[recorders + 4 (4 + d)] + 0x14]` p0 / `[[view + 0xC] + 8]` p1 | Row 3 edits |
|---|---|---|---|
| stopped, not held | (0, 5) | (0, 5) | step 5: match |
| stopped, step 3 held | (0, 2) | (0, 2) | step 2: match |
| playing, step 3 held | (0, 2) | (0, 2) | step 2: match |
| playing, `0x20039DE0` p0 = 1 (not following), not held | (0, 5) | (0, 5) | step 5: match |
| playing, p0 = 0 (following), not held | (0, playhead) | (0, playhead) | refused by stock |

Also: `[[view + 0xC] + 8]` = `[editor + 0x20]` (the note edit store) in every note case, and its word 0 = the
pattern's step word 0 there; for drums `[[view + 0xC] + 8]` p0 = the shown pattern too.

**Stock's write path for bytes 2-3** (`param_wptr(edit store, 0)`, write `[2]`, `[3]`, `store_commit`; as the note
row-3 handler `0x0804D0FA`-`0x0804D10E`): in each accept case it changes exactly bytes 2-3 of (shown, selected) in the
pattern, nothing else in any pattern.

**Two catches for Task 6 (notes):**
1. **The selected step can move between the press and the release.** Playing with the editors following (p0 = 0), step
   3 held, row 4 pressed (latched (0, 2)), the step pad let go first, 150 ms later: the selection is the playhead's
   (0, 1). A write through the store at the release would land on step 1. So at the release: write through the store
   only when `[editor + 0x24]` p0 / p1 is still the latched pattern / step; otherwise write the step raw in the
   pattern (the editor's refresh copies the pattern step into the store when that step is selected again,
   A-storage.md Q3).
2. **A stale store reverts `[0]` / `[1]`.** The commit writes the store's whole word 0 into the pattern's selected
   step. With the pattern step edited raw (as a CTPlay writer does) and the store not refreshed, writing only bytes
   2-3 of the store's word 0 and committing put the store's old `[0]` (0) back over the pattern's (1)
   (`q4_stores.out`, "a stale store"); the units (other parameters, not committed) stayed. So the write must set the
   **whole word 0** = the pattern step's current `[0]`, `[1]` plus the new `[2]`, `[3]`.

**The first write's clear-all** (junk in every note step's `[2]`/`[3]` and in each track's store word 0; the patterns
zeroed raw, then each of the four tracks' edit store word 0 bytes 2-3 → 0 and committed): stopped and playing, no
pattern byte and nothing outside the patterns and the stores changed; the four stores' bytes 2-3 read 0 after. With a
stale store the commit reverted `[0]` as in catch 2: the clear-all needs the same whole-word-0 rule (word 0 = the
pattern's `[0]`, `[1]`, 0, 0 at that track's `[editor + 0x24]` p0 / p1).

## 5. Removals (`q5_removals.py`, `q5_micro.py`)

Sweep (stock, stopped, pattern 1): Drum 1 and Synth 1 with hits / notes on steps 1, 4, 7, 13, 21; every view mode the
track reaches (drums 1-6, notes 1-6 and 8: Note, Velocity, Gate, Pattern Settings, probability, expanded / wide, the
notes' micro-step view), every pad 0-31 as a tap, a tap with step 4 held and a tap with Shift held; Clear held + every
pad in modes 1 and 6; Clear held + each track button; live recording (Play + Record) with Clear held for a pass, alone
and with a pad held. Steps emptied (`[0]` → 0, velocity → 0) and the known functions that ran:

| Route | Empties | Function | In the plan |
|---|---|---|---|
| Drum step view, step pad tap on a hit (also with Shift, and a held step's release after another step pad) | that step | `drum_step_off` | yes |
| Drum step view, step held + the lower pad of its flip sample | that step | `drum_remove` | yes |
| **Drum Gate view (mode 3 = the drum's micro-step view), the pad of the step's last micro bit (pads 16-21 = micro 1-6)**, tap, with the step held, or with Shift | the selected step | `0x0804F036` (vtable `0x0805AA9C` slot 2), no known function | **no** |
| Clear held + step pad (also while recording with Clear held and a step pad held) | that step | `drum_clear_step` / `note_clear_step` | yes |
| Note view, step held + the key of its only note | that step | `note_pad_press` (PL18 / Task 9) | yes |

Nothing else emptied a step: Velocity, Gate (notes), Pattern Settings, probability, the expanded / wide view, the notes'
micro-step view, Shift layers, Clear + track button, Clear + drum / key pads in the expanded view, recording with
Clear held. (Stock's recorder only adds; CTPlay's mono record replaces notes but always leaves the new one.)

**The micro-step removal** (`q5_micro.py`; asm `0x0804F036`-`0x0804F122`): the press toggles micro bit `pad` of the
selected step (`[r7 + 0x10]` p1 = step `sl`); when the result is 0 (`cbnz r5` at `0x0804F0FC` falls through) it
clears the velocity byte (`0x0804F104`-`0x0804F118`) and commits. Hook sites: the entry `0x0804F036` needs 6 B
(`cmp r1, #6` is 2 B; 6 B passes `check_entry`); **mid `0x0804F104`, expect `f8684146` (`ldr r0, [r7, #0xc]; mov r1,
r8`), displace 4, passes `check_mid`**, reached only on that removal path. At it: **r7 = the micro view** (class
`0x0805AAA4`, `0x2004364C` drum 1, `0x20043690` drum 2), **sl (r10) = the step 0-31**, `[r7 + 0xC]` = the drum's step
store (= its editor + 0x18) → the drum; the pattern = the drum's shown one. Emulation: micro 0x01 pad 16, 0x04 pad 18,
drum 2, step 21 on the 17-32 page, playing with follow off → reached once each, the hit gone; micro 0x03 pad 16 (a bit
left) and an empty step (a hit added) → not reached.

## 6. Components (strings of the validator wasm)

`ext/circuittracksreverseengineering/Assets/Novation-Components/circuit-tracks-project-validator-e83caa525f3f586024af78cebcb33ad4.wasm`
(sha256 `e189c056…ec61b`), `strings -n 4` (1 478 strings). Every check reports a field path and a message. The
must-be-zero checks are exactly these: `sessionData.header.featureFlags.reserved` ("Some reserved feature flags are
set"), `sessionData.timing.spare1` / `spare2` ("... not set to zero"), `sessionData.scenes[..].patternChains[..].padding`,
`sessionData.sceneChain.padding`, `sessionData.patternChains[trackIndex].padding` ("... padding not set to 0").

Pattern fields named: synth / MIDI steps `stepInfo.assignedNoteMask` and `stepInfo.probability` (bytes 0-1), then
`notes[noteIndex].noteNumber / gate / delay / velocity`; drum patterns `velocity`, `probabilities`, `drumChoice`,
`drumRhythm` (the four arrays, with "drum rhythm mask of zero when velocity is non-zero" and "non-zero drum rhythm when
velocity is zero"), and for every kind `playbackRange.start / end`, `syncRate`, `playbackDirection` (settings bytes 0-3)
and `automation[..].values[..]`. **Nothing names a note step's bytes 2-3 or a pattern's settings bytes 4-39**, as
padding, spare, reserved or otherwise. **G1 not triggered.** Confidence: medium-high: strings only (a check without
its own field string cannot be ruled out, but every check found carries one); a Components round trip of a marked
project on the device (TEST.md section J) remains the confirmation.
