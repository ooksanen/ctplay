# Pattern strum (PL19): the recording route, the spill's store touch, the player's readings — spike

Date: 2026-10-31 · Build: PL18's sources (`lib.pl18()`, the `pl18_image` sources) · Status: **done; the first step of
building PL19 ([the design](../specs/2026-10-28-playback-strum-design.md)).** Decision gate passed: route (a) records **Written** exactly with
record quantise on and off, and **Played** too (no fallback needed).

Scripts and their outputs: [2026-10-31-pattern-strum-spike/](2026-10-31-pattern-strum-spike/) (how to run: its README).
Every answer below names its script and quotes its `.out`; "asm" marks a reading of `re/app.asm` alone. All emulation:
Synth 1, the dump's tempo (a step = 160 ms, a tick = 26.7 ms), pattern 0 cleared, steps 0–31, a triad on pad 24
(C 48, E 51, G 55 in the dump's scale) unless said otherwise; quantise off as `tests/test_mono.py::quantise_off`.

## The recorder, as the spike found it (asm, confirmed by `q1_baseline.out`)

Note recorder vtable `0x0805A5B4` (slots: 0 note-on `0x0803FC5E`, 2 sync rate `0x0803F61C`, 3 **placement**
`0x0803F298`, 4 note-off `0x0803F5B0`, 5 tick `0x0803F62A`, 6 flush `0x0803F67C`).
- **Placement** `(rec, pattern, step, offset, [sp] start, [sp+4] note, [sp+8] vel)`: from note-on's nearest step
  (`0x0803FD32`: quantise on, a press in a step's second half goes to the next step with a negative offset). It picks a
  unit free in the step's mask | `[rec + 0x9D]`, fills a **list entry** `rec + 0x54 + 12 i` (note, vel, unit,
  released bit; word + 4: start bits 0–10, end 11–21, offset 24–29) and sets the pending word's bits 0–2 to the list
  index `i` (counter `[rec + 0x9C]`, reset each pass). **No step is kept.**
- **Tick pass** `0x0803F6C6(rec, pattern, step, step tick)` (from slot 5, Main task): once a step (quantise on: its
  middle tick; off: its last tick). For every list entry (released ones first) it writes the **pending word** with the
  **pass's** pattern and step, start = step tick (quantise off: + offset), microstep 0 (off: from the offset,
  `0x0804A314`), and empties the entry; a released one is committed at once (site `0x0803F78C`).
- **Note-off** `0x0803F5B0`: still in the list (`[list[w & 7]] == note`) → end and released bit kept for the pass;
  else commits at once (site `0x0803F60C`) and calls `rec_touch`.

```
q1_baseline A slow held, quantise on:  place n48 s7 off-2 (ui); place n51 s7 off1 (main); pass step 7;
  place n55 s8 off-2; pass step 8; release: commit n48 note-off (ui), n51 note-off (main), n55 note-off (main)
  written: {7: [(48, 13, 0, 96), (51, 13, 0, 96)], 8: [(55, 7, 0, 96)]}
```

## 1. The recording route: **(a), the pending word at `rec_commit`**

**(a) works, both modes, quantise on and off** (`q1_route_a.py`, `lib.Route`: the word rewritten at the commit's entry,
before slim's `rec_commit` handlers, as a priority-40 handler would). Played: note k gets the first note's step,
microstep and start; Written: sixths = first's microstep + `roll_sixths(k × gap)`, step + sixths / 6 (wrapping from
last to first), microstep sixths % 6, start = first's start + k × gap. The commit then writes the unit there and
takes the length from that start (`end − start`).

```
OK   played qon speed 1 rising: order [48, 51, 55], first 7/0 start 42; tasks ['ui:note-off', 'main:note-off', 'main:note-off']
OK   played qoff speed 1 falling: order [55, 51, 48], first 6/4 start 40; ...
OK   written qon speed 1 rising ... OK written qoff speed 3 falling ...      (all 24 triad cases OK)
OK   written q on slow, last step 7 (spill wraps to step 0)
OK   written q on slow, step 8 full (G left out): ...; left out (step full) [55]
OK   written q on slow, pressed at tick 40 (step 7), released at 170 ms: ...; edges [('moved', 55, 2, ..., 'guard')]
```
- **Units: a moved note must get a new unit.** It carries the unit claimed in its *original* step; kept as is, it
  overwrites a note of the target step: `FAIL NAIVE played q on slow: note 48: want (7, 0, 21), got []` (G, placed on
  step 8 unit 2, wrote over C in step 7 unit 2). Re-picked as the first unit free in the target step's mask |
  `[rec + 0x9D]` | the units other pending words claim there (recfix.c `claimed()`), with stock's own preference for a
  unit holding the same note and microstep, **no moved note ever took another's unit**: in every OK case steps 4–11
  held two older notes in units 0–1 and all survived (the script checks every unit).
- **Later steps: yes.** Written spills into the next steps and wraps (`last step 7 → step 0`).
- **A full target step:** none free → bits 0–2 = 7, the commit writes nothing (Written: the note is left out, as the
  plan says). Played lost one too (`played q on slow, 9th + bass: left out (step full) [62]`: 2 older + 5 notes):
  better to leave a Played note where stock placed it (the handler passes) than to drop it.
- **Released before its own position** (Written: the first note rounded to a later step, a quick release): end −
  start wraps to ~2047 = a 16-step note. Guard: start = end − 1 (1 tick); the `guard` edge above.
- **Hook:** the existing `rec_commit` (entry, `0x0803F7BE`, args `rec, note, end`), handler `pstrum_on_record` at
  priority 40: mono (`mono_on_commit`, 50) and recfix (`recfix_on_commit`, 60) then see the moved word. **Tasks:** UI
  (a rising strum's first note: stock's own pad note-off at the release) and Main (the heartbeat's note-offs, the
  tick pass): `tasks [...]` in every line above; the flush at Stop (`0x0803F6A2`) too. No new hook.
- **Which task commits what** (`q1_tasks.py`, added in fix round 1): every k > 0 commit is Main (the heartbeat's
  note-offs; a quick tap's in the tick pass) except the flush at Stop and Record off, which commits every note in the
  UI task. The transport store `0x20011034` read as `param_get` does tells the flush apart: (playing, recording) =
  `(0, 0)` at Stop's flush, `(1, 0)` at Record off's, `(1, 1)` at every other commit. Two pads on one track sharing a
  pitch (pad 28's root = the first strum's G) put that pitch through the UI note-off too:
```
rising, released: commits (note, task, site, (playing, recording)) [(48, 'ui', 'note-off', (1, 1)), (51, 'main', 'note-off', (1, 1)), (55, 'main', 'note-off', (1, 1))]
rising, tapped 100 ms: ... [(48, 'main', 'pass', (1, 1)), (51, 'main', 'pass', (1, 1))]
rising, Stop while held: ... [(48, 'ui', 'flush', (0, 0)), (51, 'ui', 'flush', (0, 0)), (55, 'ui', 'flush', (0, 0))]
rising, Record off while held: ... [(48, 'ui', 'flush', (1, 0)), (51, 'ui', 'flush', (1, 0)), (55, 'ui', 'flush', (1, 0))]
rising, a second pad (28) ...: placed [(48, 'ui'), (51, 'main'), (55, 'ui'), (55, 'main'), ...]
```
  So the plan (Task 4) lets only Main move notes: the flush and an ambiguous pitch pass; the unit is re-checked and
  reserved (the step's mask bit) in a few masked instructions after an unmasked claims scan.

**(b) the placement cannot move a note** (`q1_route_b.py`): its step and start arguments change nothing (the pass
writes its own); an offset beyond the step writes an impossible microstep.
```
quantise on, step + 1: ... words [(48, 7, 0, 42), (51, 7, 0, 42), (55, 8, 0, 48)]   (= stock)
quantise off, offset + 6: ... written {6: [(48, 23, 4, 96)], 7: [(51, 14, 7, 96), (55, 11, 2, 96)]}   (microstep 7)
```

**Mono record with Written** (`q1_mono_order.py`): mono's one visit per track loses roll notes when a commit returns
to an earlier step. A falling triad with bass, medium: send order G E C(root) bass; the heartbeat's note-offs end
`notes[]` first and the root last (`commit order: [55, 51, 36, 48]`); C lands on step 7, the bass on step 8, so C's
commit is not in the visit (step 8) and clears step 7's other units, the roll's G and E:
```
FAIL mono written q on medium falling triad + bass: ... mono steps: {..., 7: [48], 8: [36], ...}
OK   mono written q on slow falling triad + bass: ... 7: [51, 55], 8: [48], 9: [36]
```
Task 4 must keep a roll's steps for mono (e.g. per track the steps the current roll has already cleared). Played
with mono is fine (one step: `mono played q on slow falling 9th + bass: 7: [58, 51, 62, 36, 48]`).

**Fix round 2: a note is moved only if it is its own strum's pending note** (`q1_scope.py`, a model of the plan's
Task 4 rule). The identity is proved at the send: c = `[rec + 0x9C]` before it; after it the pending word's bits 0–2
== c and `list[c].note == note` ⇔ a fresh placement, id = `list[c].start` (= the converted word's start: q1_baseline
`place n48 start42` → word start 42, quantise off `n51 start43` → 43). The heartbeat moves its own sent note at its own
note-off (converted word: rewritten before `note_sink_off`) or leaves a ticket (note, start, end) that the tick pass's
commit uses (in the list: the tap). No other commit is touched:
```
held, rising: moves [('main', 'heartbeat note-off', 51, 1, 7, 4), ('main', 'heartbeat note-off', 55, 2, 8, 2)]
tapped 100 ms (the pass commits): moves [('main', 'tick pass', 51, 1, 7, 4)]
stale latch: strum, then a G chord tapped 40 ms: ... steps {8: [(48, 0), (51, 4)], 9: [(55, 2)], 10: [(55, 0)]}
two pads sharing G: ... ('main', 'heartbeat note-off', 58, "first's word gone: pass"), ...; older units lost: none
quick re-press of pad 24: moves [('main', 'tick pass', 51, "first's word gone: pass")]
Stop while held: moves []
arpeggiator on the track after a strum: moves [(..51..), (..55..)]   (the strum's own only; arp notes at stock's)
```
Every move in every case ran in Main. The model runs `resound()`'s sends as not strum sends (two pads: a re-sound of
G landed as a third note of the second strum before that rule) and takes a rising root's identity from stock's own UI
send with the same rule; the plan has the heartbeat send that root (as a falling strum's), so the rule runs in Main.

**Fix round 3: moves at the commit sites, tickets that carry their strum** (`q1_scope.py`, rewritten). Two mid
hooks right before a commit's `bl` (`0x0803F606`: the note-off path, r4 rec, r1 note, r2 end; `0x0803F786`: the
tick pass and the flush's pass, r8 rec, r1 note, r2 end) do every move, so the reservation sits next to stock's
commit. Identity = (note, start, unit). The heartbeat arms `inflight` for its own note-off of a converted note, or
leaves a two-word ticket (id + end; k + the first's id + a tick stamp) for an in-list note; tickets are read only
at the pass site after the transport check, cleared while the transport is off, dropped 48 ticks after their stamp.
```
tap, then pad 25 takes the freed slot before the pass: moves [('main', 'pass site', 51, 1, 7, 4), ('main', 'note-off site', 53, 1, 7, 4), ('main', 'note-off site', 56, 2, 8, 2)] ... slot 0's latch now [50, 53, 56]
tap, then pad 26 takes the freed slot before the pass: moves []; diag [('ui', ..., 51, 'a non-pass commit matches a ticket')]   (stock re-armed the shared Eb; not acted on)
resound order, quantise off: moves [('main', 'pass site', 58, 1, 7, 1), ('main', 'note-off site', 51, 1, 6, 5)]; G placements [(1104, 'main', 41, 2), (1115, 'ui', 42, 0), (1135, 'ui', 43, 2)]   (A's G committed unmoved at the hand-over; the re-sounded G not moved)
let go and Stop in the same ms: moves []
ticket expiry across takes: ... tickets before Stop [(51, 42, 3)], after its first heartbeat 0
```
Every case: all moves Main, no older unit lost, no mask bit without its note. The model's hooks act only in the
heartbeat and at the pass site by construction; the `diag` column is the evidence that no other commit matched a
ticket except the re-armed Eb above. Not emulated: a UI flush preempting a move between the reservation and the commit
(the plan re-reads the transport inside the masked section).

## 2. Which strum a recorded note belongs to

- **Order = send order.** Every send places a note at once (the root in the UI task at the press, the others in the
  heartbeat): `q1_baseline` places at the ms of each send, and `h.strum` (placement order) is the live strum's order
  in every `q1_route_a` line (rising `[48, 51, 55]`, rising with bass `[48, 36, 51, 58, 62]`: root first, then
  `notes[]` rising; falling `[62, 58, 51, 48, 36]`: the root at its place among them).
- **Latch it at send time, not from `held[]` at the commit.** A strum tapped shorter than the time to the next pass is
  committed by the pass (`D fast tapped`: `commit ... (main) pass`), after the heartbeat has freed the entry. And a
  tight strum's dropped tone shifts the later indices. So per track: the notes of the latest strummed press in send
  order, appended as each is sent (`play()` for the rising root, the heartbeat for the rest; a press starts anew).
  Then k = the note's index there; not found = not a strum note (PASS).
- **The first note's position** = its pending word at its own commit (step, pattern, start, microstep: where stock
  put it, record quantise deciding). It committed first in every run (`first ... latched`, no other edge), as the
  first sent is the first ended in both directions. If a later note commits first, the first's pending word is still
  there (converted: `list[w & 7].note != note`, stock's own test, `lib.SH.in_list`); if it is still in the list (only
  possible within one pass after more than 6 placements, where stock itself steals list entries), pass.
- With quantise on, the first's start is the step's tick and its microstep 0 (`first 7/0 start 42`); off, the press's
  tick and its microstep (`first 6/4 start 40`).

## 3. The spill's write and store touch: **`rec_touch(rec)`**

- **Stores** (`q3_probe.out`): `[rec + 0x4C]` **is** the step editor's `[0x20039E50 + 0x3A0 t + 0x18]` (both
  `0x20039ea8` for track 0; p0 = the shown pattern's address). So `rec_touch` and upstream's `latchstep` touch the same
  store: `rec_touch` rewrites p0 and commits, upstream marks every parameter (`0x08035456`) and commits.
- **Touch** (`q3_spill.out`): a raw spill into an empty step stays dark with no touch (`none ...: pad 5 LED 0x14`, the
  empty colour) and lights at once with either touch (`rec_touch ...: pad 5 LED 0x13`, `touch_all ...: 0x13`), step
  first or pad first, pattern 0 or 2. The unit survived in every case (even untouched): a stock add on the spilled step
  and on another step (`A: step 6 [58, 60]`, `B: ... [58, 60]`), the held step's own add after the spill
  (`C rec_touch: step 4 [48, 55], step 6 {2: (60, 6, 2, 100)}`), and Play sounds it (`D: 60 sounds True`). Pick
  `rec_touch` (already a function; what stock's recorder does after each commit; PL11 uses it): one call after all
  spilled steps are written.
- **The held step** (`q3_held.out`): the recorder's position store `[rec + 0x14]` (= step editor + 0x24): **p0 = the
  shown pattern, p1 = the held step 0–31** (the half included); p0 of `[view + 0x2C]` = 1 while a step is held. Both
  routes, both halves, patterns 0 and 2: `pattern 2, 17-32, pad first, step pad 15: (pattern, step, held) = (2, 31, 1)`.
  Latch them in the pending spill on the press (the release may come after the step's).

## 4. Stock readings the plan left to the builder

- **Marks** (`q4_player.out`; asm `0x08040D80–0x08040DAA`): `[player + 0x13C + micro]` is a **unit mask** (bit u =
  unit u of the step), set for each used unit whose microstep is `micro` and whose probability byte ≥ `[player + 4] & 7`
  (a random draw each step). `step 0 micro 0 mark 0x07` (C E G), `micro 3 mark 0x08` (A, unit 3), a probability-0 step
  `mark 0x00`.
- **Held tie** (`q4_player.out`; asm `0x08040DC8–0x08040E22`, `0x08040FB6`): at `seq_play_step`'s entry, a marked unit
  whose note's bit is set in **`[player + 0x128 + 4 (note >> 5)]`** (bit `note & 31`) continues a tie: it stays marked,
  `seq_note_on` gives it a new length-list entry and no sound. `seq_units_start` moves the bit there from the tie-on
  mask `[player + 0x54 ..]` (set by `seq_note_on` with tie) and frees the old entry; the first call of a tick clears
  `+ 0x128` (20 bytes, `0x0801BC58`). `step 2 micro 0 mark 0x03 held-ties [50]` then `note_on note 50 ... tie 0`.
- **`0x0803542C` is `param_get`, not a gate converter** (asm `0x08040F02–0x08040F58`, `q4_player.out`): the call reads
  **`param_get([player + 0x10], 1)` = the track's sync rate** (`[player + 0x10]` = `[rec + 0x50]`, `0x20039238` for
  track 0; it follows the pattern's `+ 0x382`: p1 read 3 before Play in the rate-4 run, the lengths used 4). Length inline: g = gate & 0x7F, 0 → 1, > 96 → 96; rate > 7 →
  7; **ticks = g × step_ticks[rate] / 6, 0 → 1**. Rate 3: gates 1 / 6 / 96 → `length 1 / 6 / 96`; rate 4 →
  `length 1 / 8 / 128`.
- **`0x08040D36` (end-all)** (asm: only `0x0805B75C`, slot 3 of the note players' vtable, holds it; the only call is
  the listener's reset `0x0804A79C`, `blx` at `0x0804A7A4`; `q4_resets.out`): **every call came from `0x0804A7A6`, in the
  UI task**: Stop (all four players, the play store `[p + 0x1C]` p0 → 0) and **the Mixer's mute on** (that player:
  `[p + 0x28]` = the track's mute store, `0x20039a5c` for track 0, p0 set). **A pattern change does not reset**
  (Patterns view while playing, past the loop's end: `playing pattern 1; []`). `[p + 0x24]` = `0x20040124`, one store
  every player shares: no action tried committed it (a project load is the likely trigger; not run).
- **Batch flag** (`q4_batch.out`, synth note-on running; static scan in its docstring): `0x20006A50` is read only by
  the synth note-on (`0x0803BD82`), which then sets `0x20006A48` (`0x0803BD8A`); **nothing reads `0x20006A48`**
  (statically, nor at run time in the Main 1 ms service and the UI routes; the DSP service tick and other tasks are
  not emulated). A note-on with the flag 0 differs only by skipping that write: `seq_note_on with the flag 1: ...
  0x20006A48 after = 1`. **So late notes never touch the flag** (the plan's rule).
- **Step 0's task** (`q4_tick0.out`): `seq_start` runs in the UI task, but the player's first `seq_play_step` (step 0)
  came from the first heartbeat after Play, in Main: `('seq_start', 'ui', 0), ('seq_play_step', 'main', 0, 0, 0)`.
  Every `seq_play_step` seen was in Main (emulation only; keep the hook's context "any").

## What changes in the plan (Tasks 3–5)

- Task 3: `[function.gate_ticks]` dropped (`0x0803542C` is `param_get`); the length is computed inline as stock does.
  `seq_end_all`'s notes: the callers above. `test_other_resets` = the Mixer's mute (a pattern change does not reset);
  `test_tick_zero` = the first heartbeat after Play. The mark and held-tie readings, the batch rule.
- Task 4: route (a) on `rec_commit`; the send-order latch (heartbeat-owned, per held entry) and the masked unit
  reservation (fix round 1); a full step (Written: left out; Played:
  stock's place); the early-release guard; mono keeps a roll's steps.
- Task 5: `rec_touch(rec)` once after the spill; the held step from `[rec + 0x14]` p0 / p1, latched on the press.
