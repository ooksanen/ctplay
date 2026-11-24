# Pattern strum: played and written (PL19) — design

Date: 2026-10-28 · Branch: `slim` · Status: **approved by the user 2026-10-28** (builder check done 2026-10-28 on the
played half: its corrections to the stock reading are in, its three questions settled as my calls; the written half
and the three-value setting added after it, decided with the user the same day). Candidate row: `candidates.md`,
"Playback strum" (the user's interest, 2026-10-17). Builds on PL18 (step-entry chords), which is being built: this
spec assumes PL18's saved layout and step-entry route as its spec gives them.

**As built (PL19, 2026-11-01).** The body below is the approved design; where the build differs, this note wins:
- **Mute** ("Played: playback", Mutes): the Mixer's mute resets the player (`seq_end_all`), so a Played strum's
  waiting notes are dropped on a mute, not played out. A pattern change does not reset: its notes play out unless the
  track's next notes cut them.
- **Device test step 8:** a slow 1/16 roll from step 1 puts C and E on step 1 (E at microstep 4) and G on step 2
  (microstep 2), by this spec's own success rule, not "C, E, G on steps 1, 2, 3" (`firmware/PL19/TEST.md`).
- **Recording route** ("Where it hooks", Recording): two `mid` hooks at stock's commit call sites, `rec_off_commit`
  (the note-off path) and `rec_pass_commit` (the tick pass), move only notes the recorder's own data proves are the
  strum's (`features/chord/pstrum_rec.c`; the spike `investigations/2026-10-31-pattern-strum-spike.md`). While Record
  is on, an active rising strum's first note is sent by CTPlay (up to 1 ms after the press).
- The rest of the as-built differences (step entry corner cases, notes recorded at stock's place) are in the user
  guide's "Pattern strum" limits and `followups.md`, "From the PL19 build".

## Purpose

Today strum is a live effect. A strummed press sounds as a strum, and what the recorder keeps depends on record
quantise: with it on (the default) the notes snap to whole steps, often split over two steps; with it off they keep
their microsteps, rounded and placed wherever they fell. A chord written by step entry (PL18) always plays as a block.

With this build, each track gets a **pattern strum** setting with three values:

- **Off** (stock): as today.
- **Played:** the pattern keeps plain chords and **CTPlay strums them as it plays them**, at the track's strum speed
  and direction, at any tempo. The chord stays editable and the strum can be changed later; stock firmware plays a
  block chord.
- **Written:** recording and step entry **write the strum into the pattern as a roll**: each note on its own
  microstep, spilling into the following steps when the strum is longer than a step. It plays the same on CTPlay and
  on stock firmware; it is fixed at the tempo it was written at.

Both serve a purpose (the user, 2026-10-28): Played for parts that stay on CTPlay and may change tempo, Written for
patterns that must strum anywhere. The guide explains each one's limits.

**Success:**
- Played: a triad on step 1, strum slow and rising: Play sounds C, then E, then G, 80 ms apart, on every pass. A
  strummed C chord recorded in this mode lands on one step as a plain chord.
- Written: the same strum recorded (or entered on a step) lands as C on the step's start, E 4 ticks later, G 8 ticks
  later (at 1/16: microstep 4 of that step, then microstep 2 of the next), and plays that way on stock firmware too.

**Non-goals:**
- A strum speed or direction of its own: both modes use the track's strum settings (Chords page, pads 28–32).
- The drums. Their player is another class; the Repeat page covers the drums' rolls.
- Pattern tools' Write and the melodic generator: they write block chords in every mode (Played strums them on
  playback). *My call:* a written roll there would spill into steps that are hits themselves.
- The arpeggiator's live notes (single notes in time already). A pattern recorded from its "chord" pattern has
  chords in its steps; in Played they strum like any other.
- PL04's voice-room rule (leave out the 5th of a strummed 5-note chord that would not fit) for Played: live only.
- Strumming notes that start at different microsteps. Only notes that start together form a chord.

**Anti-goals:**
- With the setting off, any change to stock's playback, recording or step entry (beyond PL18), byte for byte.
- A note left on: after Stop, a pattern change, a mute, a project load, or a fast tempo where a strum runs into the
  next step.
- Work during a pad press that could make a phantom press on the next pad (CLAUDE.md, "no long work while a pad is
  pressed").
- Anything from the DSP service tick, or anything that takes `MARK_DIRTY`'s semaphore (CLAUDE.md, the SC19 hang).

## How stock plays a step (`re/app.asm`; the builder confirms in emulation)

Per note track, the player (`seq_players + 0x184 t`) is driven once per 24 PPQN tick by its listener `0x0804A5C6`
(through `0x0804A684` and `0x0804A714`); by sync rate a tick holds 0, 1 or several microsteps (at 1/16, a step is 6
ticks and a microstep is one tick):

1. **`seq_units_start(this, pattern, step, microstep, first)` (`0x08040D4C`; `first` on the stack, `[sp + 0x28]`)**
   marks the slots that start now in `[this + 0x13C + microstep]` (each used slot whose probability passes and whose
   microstep `[slot + 6]` is this one) and handles tied notes (`this + 0x54` → held ties `this + 0x128`). Only on the
   tick's first call (`first` set by `0x0804A684`) does it clear the held-tie mask and count down the head of the
   **length list**, calling the player's note-off `seq_note_off` (`0x0804104A`) for each note whose time is up. So
   lengths are in ticks, counted once per tick.
2. **`seq_play_step(this, pattern, step, microstep)` (`0x08040E5A`)** plays the marked slots: it ends any of their
   pitches still sounding (`0x08041078`, `[this + 0x9B + note] != 0xFF`; `seq_note_on` does not), frees the
   length-list entries that end soonest (the head, `[this + 0x7A]`) when the marked slots need more than are free
   (`0x08040EBC–0x08040F2E`), sets the batch flag (`0x0803BDB4`), then for each marked slot in slot order reads the
   note, gate | tie and velocity, turns the gate into a length in ticks (by the track's sync rate, `0x0803542C`),
   calls the **player note-on `seq_note_on(this, note, vel, length, tie)` (`0x08040FA2`; `tie` at `[sp]`)**, and
   clears the batch flag (`0x0803BDBC`, tail call).
3. `seq_note_on` sends the note through the player's note interface `[this + 0x4C]` (skipped for a held tie) and puts
   it in the **length list: 8 entries** (links `this + 0x68`, entries 0–7, free-list head at `+ 0x78`, used-list
   head at `+ 0x7A`; times `this + 0x7C + 4 i`, notes `+ 0x7E + 4 i`; times kept as deltas, sorted). It stores
   `length - 1`, so the note ends at the `length`-th countdown after its own start. **It takes the free head without
   checking** (`0x080410AC`): a call with no free entry corrupts the player.

Tick 0 of a start runs from the Play handler (`seq_start`, UI task); every later tick runs in the Main task's 1 ms
service (`seq_tick`), in the same service as CTPlay's `main_ms` heartbeat. The player's note interface is the class
the Note view's sink has (`0x0805BF54`); it does not record.

**What resets a player** (each ends every length-list entry through slot 3, `0x08040D36`, from `0x0804A79C`): Stop
(`[this + 0x1C]` parameter 0 going to 0, from the UI task), any change of the store at `[this + 0x24]`, and `[this +
0x28]` parameter 0 becoming non-zero. **Mute** is not in `seq_note_on`: the listener skips the play slot
(`0x0804A5F8–0x0804A628`) while `[this + 0x20]` parameter 0 bit 0, `[this + 0x1C]` parameter 2 or `[this + 0x28]`
parameter 0 is set. **The batch flag** is one global byte (`0x20006A50`), also set and cleared by the Note view's pad
note start in the UI task (`0x0804AF86` / `0x0804B008`) and `0x0804D4A2`; its clear also zeroes `0x20006A48`, which
the synth note-on sets during a batch.

**Recording** (`stock/symbols.toml`, `rec_commit`): a note's pending word `[rec + 0x9C + 4 note]` holds its unit,
step, pattern, velocity, start tick and microstep; placement (`0x0803F298`) reads record quantise `[rec + 0x35]`; the
commit writes the unit at the note's end. A direct write into a note track's steps survives (PL08 spike: no editing
copy writes a note track's steps back).

## The behaviour

Applies to Synth 1 / 2 and MIDI 1 / 2 when the track's pattern strum is Played or Written **and** its strum speed is
not off. Otherwise stock, untouched (with strum off, both modes write and play block chords).

### Played: playback

- **What strums:** in one call of the player, the slots that start now and would sound (not held ties). Two or more:
  the first in strum order sounds at stock's moment, the others follow at the strum gap (80 / 40 / 20 ms, the live
  strum's `STRUM_GAP`). One: stock plays it.
- **Order:** rising = lowest first; falling = highest first (the bass last, as the live falling strum). By pitch, not
  slot order.
- **Each note as stock would play it:** its own velocity, length and tie, through `seq_note_on`, so stock's length
  list ends it its full length after it started. A strum shifts the whole note, not just its start.
- **A late note gets one tick more.** It starts between ticks, so stock's whole-tick countdown would end it up to a
  tick early (a 1/6 gate on 1/16 is one tick, about 21 ms at 120 BPM: a late note would last about 1 ms). With one
  tick added it ends at most one tick late, never early. *My call.*
- **A strum is cut short by the track's next notes** (the user, 2026-10-28): when the track's player starts a note
  again (any note: a chord or a single note) while notes of an earlier strum are still waiting, the waiting notes are
  **dropped**, as a quick chord change cuts a guitar strum short. Empty steps and a tie carrying on do not count, so
  a strum followed by empty steps plays out in full. In both directions: a cut-short falling strum loses its lowest
  notes, the bass first. At 120 BPM a step is 125 ms and a slow 5-note strum spans 320 ms, so this happens in normal
  use. Sending the waiting notes at once was rejected: they would sound on top of the next chord as a cluster.
- **Ties:** a strummed note that starts a tie keeps it. A dropped one never started, so its continuation, 96 sixths
  (16 steps) later, starts as a fresh note. Only reachable with 16 steps inside one strum (about 400 ms): the fastest
  sync rates at high tempo. Accepted.
- **Stop drops every waiting note** (they never started; stock ends what sounds). So does every other player reset
  (the list above), a project load included.
- **Stop's guarantee is the live strum's** (`chord.c`, "Exact guarantee"; *my call*): the heartbeat cannot check
  "still playing" and send as one step (the synth note-on takes the `0x08021064` semaphore, so no masking around
  it), and Stop's reset runs in the UI task. So after each late note-on the heartbeat checks again, and if the
  player was reset in between, it ends that note itself at once. A late note can blip right at Stop; nothing sticks.
- **Mutes:** stock's mute skips the player's play slot, so it does not filter a note already waiting: at most the
  rest of one strum (under 400 ms) finishes after a mute. Accepted. Pattern chains, swing and external clock act on
  stock's step timing; late notes follow their step.
- **Live presses are independent:** a pad pressed over the pattern strums by the live rules.

### Played: recording

A live strummed press records as a **plain chord**: every note of the press at the step and microstep its first
note got, record quantise deciding for that first note as stock does. Lengths run from that start to each note's
release. The live sound stays strummed (milliseconds).

### Written: the strum in ticks

On a Written track the strum gaps are **ticks of the sequencer (24 PPQN): slow 4, medium 2, fast 1**. At 120 BPM
that is 83 / 42 / 21 ms, what the millisecond speeds give today; at other tempos the strum scales with the tempo, and
every note falls on a microstep, so nothing is rounded (at 1/16). **The live strum uses the same tick gaps** while
the track is Written, so what is heard while recording is what is written (the user, 2026-10-28). The tick clock is
the arpeggiator's (`arp.c`: the sequencer's ticks while playing, the project BPM while stopped).

At sync rates coarser than 1/16 a microstep is 2 ticks or more, so the fast strum rounds to the nearest microstep
and some notes land together. Finer rates have microsteps shorter than a tick: exact. The guide says so.

### Written: recording

A live strummed press records as a **roll**: the first note where stock places it (record quantise deciding, as
stock does), note k at the first note's position + k × gap ticks, whatever record quantise says for the later notes.
**It works with record quantise on** (the user, 2026-10-28): everything else in the project can stay quantised, with
no switching between recording strums and other parts. With quantise off, stock alone already comes close (each note
in the step its tick falls in, its offset as the microstep, spilling into the next step: re-tested on the device by
the user, 2026-10-28); CTPlay's placement makes it exact (note k at exactly k × gap, not wherever the heartbeat's send
landed) and the same in both quantise settings.
A position past the step's last microstep **spills into the following steps**; past the pattern's last step it
**wraps to the first step** (as stock's recorder does). Lengths run from each note's own position to its release.

### Written: step entry (PL18's step-entry chords on)

Holding a step and pressing a pad writes the pad's chord as a **roll from the step's start**: note k at k × gap
ticks, in strum order. The notes that fall in the held step go in through PL18's route on the press (microsteps set,
one commit); the notes that **spill into later steps are written on the pad's release**, straight into the pattern
(the spike confirms the store touch that shows them), wrapping at the pattern's end. *My call:* the release keeps the
pattern write off the press. A target step with all six units used leaves that note out. Gates and velocity follow
PL18's rule per step (a spilled note into an empty step: one step, its probability set to always, as stock).

Pressing the pad again with the step held **removes the roll**: PL18's removal in the held step, and on the release,
in the steps the roll spilled into, the units at the positions the roll would write that carry the chord's note
names. *My call:* a press again undoes the entry, as for a block chord.

### Played or Written: the trade-offs (for the guide)

| | Played | Written |
|---|---|---|
| Strums on stock firmware | no (a block chord) | yes |
| Follows tempo changes | yes, milliseconds at any tempo | no: fixed at its writing tempo |
| Change the strum later | yes, the speed and direction act at once | no: re-record or re-enter |
| On the step grid | no | yes, ticks (exact at 1/16) |
| The step shows | the chord | the first notes; the rest in later steps |
| Long strums | cut short when the track's next note starts (the rest dropped) | spill into later steps, keeping their timing |

## The control: Keys page, pads 3–4

PL18 makes the Keys page one toggle pad per on/off setting. Pattern strum has three values, so it takes two pads,
read as the strum speed pads are (`ui-map.md` rule 3: one pad per value):

| Row | Pads | Controls |
|---|---|---|
| 1 | 1 | Mono record (PL18) |
| 1 | 2 | Step-entry chords (PL18) |
| 1 | 3–4 | **Pattern strum** (white): played · written. None lit = off (stock); the lit one again = off |
| 1–4 | 5–32 | *free* |

- Per track, **off by default**. A press changes it at once; no draft, no action.
- With the track's strum off, the pads still change and show the setting; nothing strums until a speed is picked.
- **Why not the Chords page:** its row 4 is full (voice leading 25–27, strum 28–30, direction 31–32), and its free
  pads 14–16 are in the Quick view's shape rows. *My call.*
- White, as strum on the Chords page.

## Saved and linked

- `chord_pstrum`: 1 B, 2 bits per track (0 off, 1 played, 2 written). A loaded value with any field at 3 resets to
  0, as `chord_strum`'s checks. **Saved**, appended at payload offset **116** (block 2, after PL18's `chord_step` at
  115; the payload becomes 117 B). **Linked**: CTCtrl reads and writes it, checked the same way. CTCtrl's panel is the
  user's to update.
- Kept in ITCM, as every setting since PL14. The waiting notes (Played) and the pending spill of a step entry
  (Written) live in ITCM too (RAM only, cleared at Stop / release and at power-on). The heap tail is not touched.

## Where it hooks (the plan confirms)

- **`seq_play_step`** (Played): a new entry hook at `0x08040E5A` (`push.w {r3–fp, lr}`, expect `2de9f84f`, displace
  4; args `this, pattern, step, microstep`: four, within slimbuild's limit; context: Main, and UI for tick 0). With
  Played active for the player's track and any slot marked, CTPlay drops the waiting notes of an earlier strum; with
  two or more sounding slots marked it leaves the first note of the new strum to stock (clearing the others' marks, or playing the
  step itself: the plan picks) and queues the rest. Otherwise PASS. **If it clears marks**, stock also skips ending
  those slots' still-sounding pitches at the step's moment: the handler does that ending itself (or leaves it to the
  late note, below), so an old note of the same pitch cannot end the new one.
- **A late note, from C** (the `main_ms` heartbeat, Main task), does what `seq_play_step` does around one slot:
  1. ends its pitch if still sounding (`0x08041078` when `[this + 0x9B + note] != 0xFF`): otherwise the older entry's
     note-off later ends the new note;
  2. makes room: with no free entry (`[this + 0x78] == 0xFF`), frees the head as stock does. **Mandatory**: stock's
     allocator does not check;
  3. calls `seq_note_on` with length + 1 tick (`tie` on the stack: a declared prototype, not a hook).
  Whether a single late note sets the batch flag: the plan settles it from what the flag does. It must never clear a
  batch the UI task has open (the flag is global).
- **Stop and the other resets:** the plan picks how the queue sees them (a hook on slot 3 `0x08040D36` or the
  listener's reset path, or a check of the player's state in the heartbeat), and the after-send check above.
- **The queue** is written by the hook (Main, or UI at tick 0) and read by the heartbeat (Main), the same two-task
  rule as the live strum's `held[]`: one writer per field, the count stored last. **The length list** gets its first
  writer outside stock's own tick: late notes write it only from the Main task, as stock's ticks after tick 0 do;
  the UI task's writers (tick 0, Stop's reset) are stock's own. The plan checks that this holds for every path that
  writes it.
- **The live strum in ticks** (Written): the heartbeat's wait for a Written track's entry counts the arpeggiator's
  ticks, not milliseconds; the rest of the live strum is unchanged.
- **Recording** (both modes): **the plan's first task is an emulation spike** on where to move a strummed note: the
  pending word at `rec_commit` (next to mono record's handler) or the placement (`0x0803F298`), so that a moved note
  never takes a unit another note of its target step holds, and a spilled note can land in a later step. **Fallback
  if no clean route exists:** Played: with Record on, a live press sounds unstrummed (heard = recorded; the pattern
  strums it next pass). Written: **no silent fallback**: Written recording must work with quantise on (the user,
  2026-10-28), so if the spike finds no route for it, the build stops and the question goes back to the user. The
  builder reports what the spike found.
- **Step entry** (Written): PL18's `step_add` writes the held step's notes with their microsteps; the spill is kept
  for the release (`pad_release`, as `euclid_release`'s pending write) and written there into the pattern, then the
  store touch the spike confirms.
- The Keys pads only change a setting on the press.

## Budget

Flash: about 3–4 KB expected (117 KB free). ITCM: 1 B setting + the Played queue (per track up to 5 late notes with
note, velocity, length, tie, plus its wait and count; about 100–130 B) + a step entry's pending spill (about 16 B) +
the recording latch if the spike needs one. Heap tail: 0 B. Saved: 1 B in block 2. Stack: the heartbeat now calls
`seq_note_on` (the player's own depth into the note interface; measured: Main 416 B in PL17), and the pad release
writes the spill (PL17's drum Write used 232 B of it); the manifest's `hook_stack` records them.

## Tests (emulation, through the real routes: Play, the sequencer's ticks, the heartbeat, pad press / release)

Off:
- Playback, recording and step entry byte-identical to PL18, with strum on and chords in the pattern.

Played:
- A triad, a 7th and a 9th with bass (5 notes) on step 1: the first note at stock's tick, the others at 80 / 40 / 20
  ms, rising and falling orders; velocities as stored; the first note's length as stored, each late note's one tick
  more, counted from its own start.
- Strum speed off: stock. Single notes and held ties: stock.
- A strum running into the next step (fast tempo, slow strum, chords on steps 1 and 2): the waiting notes are dropped
  and never sound, step 2's chord strums from its start, nothing stays on; the same with a single note on step 2; with
  step 2 empty (or a tie carrying on), step 1's strum plays out in full.
- A late note whose pitch still sounds from the step before (a long gate): it restarts, and the old entry's expiry
  does not end it.
- Stop during a strum: nothing stays on, including a late note-on placed right after Stop's reset. Start again: the
  first step strums. The same for the other resets (a pattern store change).
- Tick 0 (from the Play handler, UI task): a chord on step 1 strums.
- The length list full (6-note chords on long gates, all 8 entries used): room made as stock does, the player's lists
  intact, nothing stays on.
- Recording: a strummed press records one plain chord (quantise on and off), lengths as specified.
- A semaphore-take count as `emu_sc19_3.py`: the late notes take nothing the DSP service tick holds.

Written:
- The live strum's gaps are 4 / 2 / 1 ticks, playing and stopped (the project BPM).
- Recording, quantise on and off: note k at the first note's position + k × gap; a strum longer than the step spills
  into the next steps; at the pattern's end it wraps; lengths as specified.
- Step entry: a triad, a 9th with bass, slow / medium / fast, rising / falling: the held step's notes on the press
  with their microsteps, the spill on the release; a full target step leaves that note out; the spill wraps at the
  pattern's end; pressing again removes the whole roll; no stuck note in any press / release order.
- Sync 1/8: the fast strum's notes round to microsteps as specified.
- The written pattern plays the roll (the player's notes at their microsteps) and a stock edit of a spilled step keeps
  it.

Both:
- MIDI 1 / 2: the same notes reach the MIDI transmitter.
- Mono record together with each mode.
- Saved: round trip of `chord_pstrum`; a field at 3 resets to 0; the link reads and writes it.
- Keys page: pads 3–4 per track (played · written, none lit = off, the lit one again = off); pads 5–32 dark and doing
  nothing; pads 1–2 as PL18.
- The drums: untouched.

## Device test (`firmware/PL19/TEST.md`)

Starting state: a new empty project, Synth 1 on a Poly patch, 120 BPM. Steps name pads by their note, not their
number (the user plays a keyboard layout). Main steps:

Played:
1. Keys page: pads 3–4 dim (off). Pad 2 on (step-entry chords). Chords page: triad, strum slow, rising.
2. Hold step 1, press C: the chord goes in. Play: a block chord (pattern strum off). Stop.
3. Keys page: pad 3 (played) on. Play: C, E, G one after another, low to high, on every pass. Medium, fast: tighter.
   Falling: high to low. Change the tempo to 80 and 160: the strum keeps its speed. Stop.
4. Chords page: strum off (pad 3 still on). Play: a block chord. Strum back to slow.
5. 9th with bass below on steps 1 and 2, slow strum, 200 BPM: step 2's chord starts on time and step 1's strum is
   cut short (its top notes never sound). Clear step 2: step 1's strum plays out in full. Stop: nothing keeps
   sounding (a held note would ring past the patch's release).
6. Stop in the middle of a slow strum, several times: nothing keeps sounding.
7. Record: quantise on (Record bright with Shift). Record a C chord over an empty step. Stop. Hold that step: C, E
   and G light (one step). Play: it strums. Repeat with quantise off.

Written:
8. Clear the pattern. Keys page: pad 4 (written) on. Strum slow, rising. Hold step 1, press C, release: step 1 holds
   C (hold step 1: C lights), step 2 holds E and step 3 holds G (hold each to check). Play: the strum sounds as the
   live one did at 120 BPM.
9. **Phantom-press check:** after the press in step 8, the pad to the right of C did **not** go into the step.
10. Hold step 1, press C again, release: steps 1–3 are empty.
11. Record a strummed C chord live (quantise on): the same roll as step 8, from the step it was recorded on.
12. Tempo 80: the written roll plays slower with the tempo (expected: fixed to the grid).

Both:
13. MIDI 1 (if a MIDI synth is at hand): each mode's pattern strums on the external synth.
14. Save, power off and on, load: pads 3–4 keep their state per track.

## Docs to update with the build

`ui-map.md` (the Keys table: pads 3–4; the free-pads list: Keys 5–32), `layouts/gen.py`, `candidates.md` (the row;
the "Playback hook" building block: first used), `stock/symbols.toml` (`seq_play_step` becomes a hook, `seq_note_on`
callable, the player's length list and resets), the guide's Keys and Strum sections, a "Played or Written?" section
from the trade-offs table (the fixed tempo of Written explained, the user, 2026-10-28), and "Changes by feature",
`resources.md`, `save_layout.lock`, `slim/README.md` and `CLAUDE.md`'s docs map.

## Decided by the user (2026-10-28)

- Both modes in PL19: Played (playback strum) and Written (a roll in the pattern).
- Written rolls spill into the following steps, keeping their timing.
- Written mode's strum is in ticks (slow 4, medium 2, fast 1), the live strum too while a track is Written; the
  millisecond speeds stay for Off and Played.
- Each mode's limits (Written's fixed tempo among them) are explained in the docs.
- Written recording works with record quantise on too, so the rest of a project can stay quantised.
- Played: a strum still waiting when the track's next note starts is cut short (its rest dropped), in both
  directions, the falling strum's bass included.

## My calls (for the user to check)

1. One strum speed and direction per track for both modes; the new setting only picks off / played / written.
2. The setting on the Keys page, pads 3–4, white.
3. (Settled by the user: a cut-short strum drops its rest; see above.)
4. Played: a live strummed press records as a plain chord (fallback: unstrummed while recording, if the spike finds
   no clean route). Written: as a roll, quantise on or off, with no fallback (it goes back to the user).
5. Played: no voice-room rule (stock's voice stealing applies).
6. Played: Stop's guarantee is the live strum's (a blip possible right at Stop, nothing sticks), not a strict one.
7. Played: late notes get one tick more, so none ends early.
8. Played: a dropped note that started a tie continues as a fresh note (needs 16 steps in about 400 ms).
9. Written: a roll wraps at the pattern's end; a full target step leaves that note out; step entry writes the spill
   on the pad's release; pressing the pad again removes the whole roll.
10. Pattern tools' Write and the melodic generator write block chords in every mode.

## Left to the builder

Hook mechanics and names; whether `seq_play_step`'s handler clears marks or plays the step itself; the stop
detection; the recording route (from the spike); the queue's and the pending spill's layout; test file layout; exact
flash, ITCM and stack figures.
