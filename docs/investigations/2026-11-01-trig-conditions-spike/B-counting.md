# PL20 builder check, part B: playback and counting (emulation, 2026-11-01)

Spec: [`../../specs/2026-10-28-trig-conditions-design.md`](../../specs/2026-10-28-trig-conditions-design.md). Static
reading: [`../2026-10-28-trig-conditions-storage.md`](../2026-10-28-trig-conditions-storage.md). Stock image only, no
slim code. The sequencer runs through the real route: Play (button 17), then the Main task's 1 ms service
(`heartbeat`), 240 BPM. Pattern settings are written raw (stock's getters read them at every pattern change) plus the
playing pattern's settings store; chains through the chain store (write + commit) or the Patterns view; mute through
the player's mute store `[player + 0x28]` (write + commit, not the Mixer pads). Hooks only log, except where a script
says it forces a branch.

Run from `slim/`: `PYTHONPATH=.:tests:../tools:docs/investigations/2026-11-01-trig-conditions-spike ../.venv/bin/python
docs/investigations/2026-11-01-trig-conditions-spike/<script>.py`. Shared code: `b_lib.py`.

Engine `E = 0x20038EC0`, tracks 0-7 (Synth 1, Synth 2, MIDI 1, MIDI 2, Drum 1-4). Stores found or confirmed here:
`[E + 0x30 + 4t]` playing store (p0 pattern, p1 step, p2 tick in step), `[E + 0x50 + 4t]` the playing pattern's settings
(p0 last / first, p1 rate, p2 direction), `[E + 0x70 + 4t]` look-ahead, `[E + 0x90]` p0 song tick, `[E + 0x9C]` chain
store (param t = first / last pattern, **param 8 + t = "chain set by hand, waiting"**), `[E + 0xA0]` scene chain
(p0 first / last scene, **p1 = "scene picked by hand, waiting"**), `[E + 0x2C]` p0 current scene, `[E + 0xC4 + 4t]`
the chain before a hand change (raw), `[E + 0xFC]` tracks that finished their chain (for scene chains).

## 1. A pass at `0x0802CD42`

**Run:** `b_1_pass.py` (5 scenarios, all 8 tracks each): loops; 2- and 3-pattern chains with different lengths per
pattern, first / last not at 1, a wrapping range (first 28, last 3), a 1-step pattern; every direction; every sync rate
(drums each their own); Synth 1 and Drum 1 muted. Each track's played steps (tick 0, `0x0804A6B8`) are split at its pass
events (`0x0802CD42` with `fp = 0` and `r4` or the scene flag) in the global event order, and each piece is checked
against the expected pass.

**Result: exactly one pass event per pass, in every case, before the next pass's first step.** No piece was wrong, no
two events without a step between them.
- Directions: stock has four, `[pattern + 0x383]` / settings p2: 0 forward, 1 reverse, 2 ping-pong, 3 random.
  Ping-pong: one pass = there and back, both end steps played twice (4..11, 11..4: 16 steps). Random: one pass = as many
  random steps (in range) as the pattern has. Reverse: last..first.
- Chains advance by themselves at each pattern end (`sb` = the pattern that ended; the next one chosen after
  `0x0802CD42`, stored at `0x0802CE12`: `[sp + 1]` pattern, `r5` step).
- Rates: one pass event per pass at every rate, Drum 1-4 on their own rates.
- Muted tracks count exactly like the others.
- Order in one tick: `seq_tick` → the step advance of all 8 tracks (`0x0802CD42`) → the look-ahead copy → the players'
  tick (`0x0804A684`). So the next pass's first step already sees the new count.

**Registers at `0x0802CD42`** (checked against each other on every call): track = `[sp + 0xC]` (word) = `[sp]` (byte) =
`(r7 - sl) / 4` (`sl` = E); `sb` = the pattern that just ended (p0 of the playing store); `r4` = "the pattern ends at
this step" (byte, before the `orrs`); `[sp + 0x44]` = scene change; `fp` (r11) = look-ahead (1); `[sp + 0x18]` = the
hand flag the caller passed (below). In slim's mid stub, `ldrb.w r1, [sp, #0x44]` (4 B, accepted by
`hooks.check_mid`) runs first, so a handler sees `r1` = the scene flag and finds the original sp at `regs + 64`.

**Watch:**
- The look-ahead runs every tick for every track and often has `r4 = 1` (e.g. 54 of 701 calls for one track in 700
  ticks): the `fp == 0` filter is essential. The handler runs about 9-16 times per tick (Main task).
- At a scene change `0x0802CD42` is reached with `r4 = 0` and the scene flag set for tracks cut mid-pattern (section
  3). Count a pass on `r4` alone, not on the `orrs` result.
- Ping-pong with a hand change waiting: the change takes over at the turnaround (half a round trip), with `r4 = 1`
  there (`b_3_hand.py` C). Harmless if a hand change starts the counts over.

Confidence: high (emulation). Not checked: external MIDI clock, swing, the device.

## 2. What Play resets

**Run:** `b_2_play.py`, `b_2_order.py`: 8 tracks with chains, directions, first / last; Play, 80 ticks, Stop, Play;
Shift + Play from stop; a hand pick pending at Stop.

**Result:**
- **Play from stop** (`0x0802BBB4` → `0x0802BFE0`): song tick `[E + 0x90]` = 0, then `seq_start`, which places every
  track at position 0 of its chain (`0x0802C240`): the chain's first pattern, at its start step (forward: first step;
  reverse: last; ping-pong: first, `[E + 0x94 + t]` = 0; random: a random step), hand flags cleared, `[E + 0xFC]` = 0,
  scene 0 (the scene chain's first). Every time: Stop then Play again gives the same reset.
- A pattern picked while playing and still waiting at Stop plays from the next Play (the flag is consumed there).
- **Stop** changes nothing (positions, song tick kept).
- **Shift + Play from stop = continue**: no `seq_start`, the song tick and positions are kept, the ticks resume from
  there (after a short wait). Counts would not start over (consistent with the spec, which names `seq_start`; the spec
  could say so).
- `seq_start` runs in the Play press (UI task); the players' tick 0 of the first step runs at the next heartbeat (Main).

Confidence: high (emulation). The count-in's restart (`0x0802C4DC` → `0x0802BFE0`, also `seq_start`) was not run.

## 3. Hand changes, LAST, project load

**Runs:** `b_3_probe.py` (what the views write), `b_3_hand.py`, `b_3_scene.py` (+ `s3`), `b_3_jump.py`,
`b_3_immediate.py`, `b_3_lookahead.py`, `b_3_load.py`.

**Patterns view** (button 13): pad = 8 × pattern + track on this page (patterns 0-3; the other page not traced).
- **Tap** (or hold a first pad and press a last: a chain): chain store param t = (first, last) (`0x08044814`), param
  8 + t = 1 (`0x08044842`). `[E + 0xC4 + 4t]` keeps the old chain.
- **It waits for the end of the pattern playing now** (in a chain too: not the chain's end). Then `0x0802CD42` has
  `[sp + 0x18]` = 1 and the new chain's first pattern is chosen; the flag is cleared at `0x0802C7EE`.
- **Readable during the last pass:** chain store param 8 + t = 1 from the tap until the takeover. The look-ahead store
  shows the new pattern only during the last step (`b_3_lookahead.py`), so it is not enough for LAST.
- **Shift + tap = at once**: no flag; the chain store's byte `store + 0x18 + t` (written at `0x08050542`) makes the
  engine's listener reposition the track at the current song position (`0x0802C240` from `0x0802B948`). It never
  reaches `0x0802CD42` as a hand change; the next pattern end there is an ordinary pass end of a partial pass.

**Mixer view** (button 14), scene pads 16-31 = scenes 0-15:
- **Tap while playing**: scene chain p0 = (s, s), p1 = 1 (`0x080510E0`); the engine's listener loads all 8 chains
  from the scene and sets all 8 hand flags (`0x0802BA3E`-`0x0802BA58`).
- **It takes over at Drum 1's pattern end, for every track at once** (scene written at `0x0802C77E`, p1 cleared at
  `0x0802C794`). Tracks mid-pattern are cut there (`0x0802CD42`: `r4 = 0`, scene flag 1); shorter tracks loop their
  old pattern meanwhile (while p1 is set, `[sp + 0x18]` = the scene-change flag, so their own hand flags are ignored).
  Checked with Drum 1 at 8 and 16 steps against Synth 1 / 2 at 16 / 6 steps.
- **Readable while waiting:** scene chain p1 = 1.
- **Shift + a scene pad** (stopped) saves the scene (scene store `[E + 0x24]`). **Holding two scene pads** = a scene
  chain: it advances by itself when all 8 tracks have finished their chains (`[E + 0xFC]` = 0xFF), cutting tracks
  mid-pattern the same way.
- At `0x0802CD42` an advancing scene chain looks exactly like a hand recall (`[sp + 0x44]` = 1, `[sp + 0x18]` = 1):
  scene chain p1 is already cleared then. To tell them apart, latch p1 before `0x0802C794` (at `seq_tick`'s entry).

**Chain set vs advanced:** set = chain store params 0-7 written (Patterns view `0x08044814`, the scene listener
`0x0802BA3E`, project load `0x0802EF5C`…), taken over at `0x0802CD42` with `[sp + 0x18]` = 1, or at once through
`0x0802C240` (Shift + tap, a load while playing, any pick while stopped: `0x0802B9BA`). Advanced = `0x0802CD42` with
`[sp + 0x18]` = 0.

**Project load** (stock's read-done handler `0x0802FD5C` called directly, as `tests/test_saved.py`): chains from the
record, hand flags 0, scene chain from the record. Stopped: tracks repositioned (`0x0802C240` from `0x0802B9BA`) and
`seq_start`. Playing: tracks repositioned at the current song tick (from `0x0802B948`) and `seq_start` (twice); it keeps
playing from the same position, no `0x0802CD42` hand event. The reliable point for "a project loaded" is slim's
existing `session_applied` (`0x0802F5B4`). Not run: the Projects view route (on the device a load while playing may
wait).

Confidence: high for the Patterns / Mixer behaviour in emulation; medium for the load (direct call); none on the device.

## 4. Tick 0 of a step at `0x0804A6B8`

**Run:** `b_4_tick0.py`: every rate (0-7 = 2, 3, 4, 6, 8, 12, 16, 24 ticks a step) on both classes (rates 0-3 on the
note tracks and 4-7 on the drums, then swapped); then Synth 1 / 2 and Drum 1 / 2 muted at rates 3 and 1.

**Result:**
- `0x0804A6B8` runs **once per step, before every microstep call of that step**, at every rate, for both classes,
  and for muted tracks.
- Order in a tick: `0x0804A684` (tick 0 test, slot 1) for all 8 players, then `0x0804A714` (slot 4 at tick 0, slot 2)
  for the unmuted ones. So an evaluation at tick 0 comes before seq_units_start (slot 1, notes), slot 4 and the hit
  test (slot 2, drums).
- Rates 0-2: several microsteps per tick (`0x0804A2E8`), all after the evaluation in the same call. Rates 4-7: slot 1
  is called every tick, with microstep 0xFF on ticks without one (seq_units_start returns at `cmp r3, #6`); slot 2
  gets only 0-5 (`0x0804A76C`).
- Muted: `0x0804A684` (and tick 0) runs, `0x0804A714` does not (mute test at `0x0804A618`). So the drums' two
  probability tests are not reached; the notes' test (slot 1) is, but nothing plays.
- In `0x0804A684`: `r7` = player, `sb` = pattern, `r8` = step, `r5` = tick in step, `r6` = sync rate; also the
  player's playing store `[r7 + 8]` p0 / p1 / p2. The step's random word is `[r7 + 4]` after `0x0804A6BC`.

**Contradiction (hook mechanics):** `0x0804A6B8` cannot be a slim mid hook: it is `bl 0x0803C7F8`, and the next
instructions (`str r0, [r7, #4]`; `ldr r1, [pc, #0x2d0]`) are PC-relative too (`hooks.check_mid` rejects both). Sites
that pass the check:
- **`0x0804A6C0`** (`add.w r2, r6, r6, lsl #1`, 4 B): every tick of the play pass; `r5 == 0` = tick 0; the fresh
  random word is in `[r7 + 4]`, so the step's own roll result is known there.
- `0x0804A6AC` (`ldr r0, [r7, #0x10]; movs r1, #1`): before the draw (`[r7 + 4]` still holds the previous step's word).
- An entry hook on `0x0804A684`.

Confidence: high (emulation).

## 5. The probability tests

**Run:** `b_5_prob.py`: Synth 1 (8 steps: a tie into step 2, a long note over step 4, a 2-note step with microstep 2)
and Drum 1 (hits on 0-3 and 6; step 2 with flip sample 5 and micro bits 0 + 3). Target steps (Synth 1: 2 and 4;
Drum 1: 2) have probability 6. The roll is set through the random word at `0x0804A6BC`. Three runs of 2 passes:
"pass" (low bits 0), "roll" (low bits 7: stock fails the roll), "force" (low bits 0, the `blo` after the test forced:
`0x08040D8E`, `0x0804AA1E`, `0x080411FC`, as a mid-hook handler would do through APSR). Logged: seq_note_on / off, the
synth endpoints, the drum note-on (`0x08041298`), its two note-offs (`0x08041286`, `0x080411C2`), the sample send
(`0x08041240`), each with its ms.

**Result: "force" == "roll" event for event** (notes 121 events, drums 26, same ms), and both differ from "pass" (the
targets sound there). Ties, the long note and note-offs are unchanged. **Forcing only `0x0804AA1E` still sends the flip
sample** (sample 5 at the target step, without a hit): slot 4's test `0x080411F6` is needed too, as the spec says.

**How often each is reached:**
- Notes `0x08040D8A`: once per **used unit** per microstep call: 6 calls a step × units (a 2-note step: 12 a pass).
  Not for microstep 0xFF.
- Drums `0x0804AA18`: once per microstep call (6 a step) when the step's velocity is not 0; only while unmuted.
- Drums `0x080411F6`: at tick 0, once per k = 0..5 until the first microstep with a hit (1 for micro bit 0, 2 for
  bit 1); 6 times when the roll fails.

**Registers:**
- `0x08040D8A`: `sb` = player, `r5` = the step's address (pattern = `(r5 - [sb + 0x48]) / 0xCA8`), `[sp]` = step
  (pushed `r2`), `[sp + 4]` = microstep, `r3` = microstep, `r8` = unit, `lr` = random & 7. Displacing 4 B (`ldrb`,
  `cmp`) leaves the flags to the handler.
- `0x0804AA18`: `r5` = pattern address, `r1` = step address (step = `r1 - r5`; `r1` alone also gives drum, pattern and
  step), `r2` = microstep, `r3` = random & 7, `[sp + 4]` = player (pushed by the hit test), the caller's `r6` = step.
  Displacing 4 B overwrites `r5` with the probability; 6 B (`ldrb.w`, `cmp`) leaves the flags to the handler.
- `0x080411F6`: `r4` = player, `r1` = pattern address, `r2` = step, `r3` = step address, `r6` = k, `r7` = random & 7.
  Use 6 B (`ldrb.w`, `cmp`): with 4 B a handler would have to change `r7` too.
- All three sites pass `hooks.check_mid` (4 and 6 B).

**PL19's entry hook on `seq_play_step` `0x08040E5A`** (4 B, `push.w`; passes `check_entry`) is in another function and
shares no byte with `0x08040D8A`-`0x08040D8F`, `0x0804AA18`-`0x0804AA1F`, `0x080411F6`-`0x080411FD` or `0x0804A6C0`.
seq_play_step runs later in the same tick (slot 2, `0x0804A714`), only for unmuted tracks.

Confidence: high (emulation).

## Against the spec and the static reading

1. **`0x0804A6B8` as a mid hook is not possible** (section 4). Use `0x0804A6C0` (mid, test `r5 == 0`) or an entry hook
   on `0x0804A684`.
2. **A scene does not wait for each track's pass end**: it takes over for every track at Drum 1's pattern end, cutting
   the others mid-pattern or after several loops. "LAST = the pass before a scene takes over" is clear only for Drum 1.
   For the other tracks, the builder needs a rule, for example: the track's pass that contains Drum 1's pattern end
   (computable from both positions and lengths, not in ping-pong / random), or "every pass while a scene waits".
   Needs a decision.
3. **An advancing scene chain** (scenes chained in the Mixer) also changes every track's chain and cuts tracks
   mid-pattern. The spec does not say whether it starts the counts over. At `0x0802CD42` it looks like a hand recall
   unless scene chain p1 is latched at `seq_tick`'s entry.
4. **Shift + a Patterns pad switches at once** (no wait, no flag), through `0x0802C240`, not `0x0802CD42`. The start-over
   for "a pattern picked by hand" must also hook that path (the engine listener's calls at `0x0802B948` / `0x0802B9BA`).
   The first pass after it is partial and is counted at its end.
5. **Shift + Play from stop continues** without `seq_start`: no start-over (fine, but worth a line in the spec).
6. **Static reading, "LAST needs the look-ahead store"**: the look-ahead refreshes every tick but shows a hand change
   only during the last step. The readable waiting states are chain store param 8 + t (pattern / chain) and scene
   chain p1 (scene).
7. **Static reading, "count at `0x0802CD42`"**: confirmed for every case asked. Count on `r4` and `fp == 0` only: the
   scene flag also reaches it for tracks cut mid-pattern.
8. **Play** restarts at the chain's first pattern and its start step (the static reading left this open).
