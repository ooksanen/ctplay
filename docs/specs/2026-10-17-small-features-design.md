# Small features: count-in, falling strum, mono record (PL08) — design

Date: 2026-10-17 · Branch: `slim` · Version: `PL08` (CTPlay) · Status: design suggestion written at the user's request,
agreed 2026-10-17 (falling-strum order confirmed; strum speeds added). Frame: `docs/ui-map.md`.

## Purpose

Three small, user-facing features that fit the PL07 page frame and the 28 B of RAM PL07 leaves:
- **Count-in**: one bar of clicks before recording starts, on stock's own metronome control (as upstream's Beta 1.16),
  so recording a part no longer starts cold.
- **Falling strum**: a strum direction, so a chord can be strummed high to low, not only rising.
- **Mono record**: per track, a recorded note replaces the notes already on its step instead of stacking with them,
  so a mono patch never jumps between stacked notes (requested on Reddit; Volca-style).

Success:
- With all three off, PL08 behaves as PL07.
- Count-in: Shift + Clear steps off → click → count-in → both; with count-in on, Record armed and the transport
  stopped, Play gives four clicks at the project tempo, then the sequencer starts recording on the downbeat.
- Falling strum: a strummed chord's notes sound highest first, the pad's own note in its place.
- Strum speeds 20 / 40 / 80 ms between notes (fast / medium / slow).
- Mono record: after recording over existing notes, each step that got a new note holds only what was recorded
  there in that pass (a chord keeps all its notes).

## Decisions (my calls unless marked; the user reviews this document)

| # | Decision |
|---|---|
| D1 | Count-in on **Shift + Clear**, extending stock's metronome toggle to four states: off · click · count-in only · both (agreed 2026-10-16: as upstream). Clear's LED while Shift is held: red `0x53` · green `0x17` · magenta `0x32` · cyan `0x4D` (upstream's final colours, SC42.3) |
| D2 | The count is **one bar = 4 beats** at the project BPM, stock's own click sound; the Record LED (48) lit red `0x53` for the first half of each beat. Play during the count cancels it (nothing starts); so does a transport started any other way |
| D3 | The click part of the state goes through **stock's setter**, so stock's metronome stays stock's (and saves as stock saves it); the count-in part is RAM only until saved settings exist |
| D4 | **Falling strum** = strum direction **rising · falling** on Chords page pads 5–6 (white, one pad per value, rule 3); default rising (PL07). Falling: **all** the chord's notes high to low, the pad's own note in its place (the press may not sound the pad's note first); the bass, when on, is last |
| D5 | **Mono record** on a new **Keys** page (page 2, ToC pad 27, main colour magenta `0x32` / `0x38`): pads 1–2 **poly · mono** (magenta; default poly = stock). Keys has **no quick half** (a set-once setting; the quick flip stays Chords ↔ Arp) |
| D6 | Mono record replaces only **live recording**: step entry and stock's own editing stay stock |
| D8 | **Strum speeds** fast 20 ms · medium 40 ms · slow 80 ms (were 10 / 25 / 50; the user: the fastest was too close to no strum). Each doubles the last |
| D7 | Notes recorded **together** on a step keep each other (a chord's notes, an arpeggio's chord pattern); a note recorded on a step **later in the pass, or in a later pass**, removes the step's older notes |

## Findings this design rests on

- **Stock's metronome** (upstream `tools/countin.py`, SC41.8; device test of upstream's build still pending):
  Shift + Clear → setter `0x08031608(0x200109D8, 0x64, value)` = parameter 3 of store `[0x200109D8 + 0x38]`
  (`0x20010FAC`). The click: the clock (object `0x20011364`, Main task) calls `0x0802AB0E` on its beats, which calls
  `0x0803BD58(0xFF, 0, 0x60)` (the synth note-on with the pseudo-group `0xFF`: master parameter `0x21:9` into the DSP's
  click trigger). `0x0803BD58` takes the DSP service semaphore: fine from Main's 1 ms service (stock's own click and
  PL06's arpeggio notes go through it there), never from the DSP service tick. Transport `0x20011034`: p0 playing,
  p1 recording / armed. Clear = button 23 (in stock's Shift mask), Play = 17.
- **Stock's recorder** (PL07 work, emulation): a note's step unit is written once, at its note-off, by `0x0803F7BE`
  (called from `0x0803F60C`, `0x0803F6A2`, `0x0803F78C`): it finds a free unit or the unit with the same note and
  microstep, writes (note, length, microstep, velocity), sets the step's mask bit and probability. Held-note list at
  `rec + 0x54` (6 × 12 B).
- **Drum patterns have an editing copy** that stock writes back over raw writes (upstream SC43). Whether note-track
  patterns do too is **not known**: mono record clears units in a note track's step, so the builder checks first
  (a stock edit after a mono recording must keep the result).
- PL02's strum: the press fills a held entry and stock plays the pad's own note; the Main heartbeat sends the others
  rising; a 5-note strum that would not fit leaves out its 5th / 9th (PL04).

## 1. Count-in

State (one byte, UI task): 0 off · 1 click · 2 count-in only · 3 both. Shift + Clear: the next state; the click bit is
set through stock's setter (so the state's click bit always matches stock's metronome parameter; at power-on the state
is read from it: 1 if the metronome is on, else 0). The press is taken (stock's toggle would fight ours).

The count (count-in bit set, transport stopped, Record armed): Play is taken; the Main heartbeat counts 4 beats of
60000 / BPM ms from the press, sends stock's click on each beat (*builder's call*: the accent on beat 1 if the click
call supports it, plain otherwise) and lights Record red for the first half of each beat; at the end of beat 4 the
UI task presses Play through stock's route (`0x08033320` / `0x0803381A`) with a pass flag so the press is not taken
again. *Builder's call* how the Main → UI handover works; the start must land within a few ms of the downbeat (device
check). Play during the count cancels; a transport that starts on its own (external clock, a pattern change) cancels.
Count-in off, or Record not armed: Play is stock.

## 2. Falling strum

Per track direction bit (RAM: 1 B for four tracks), set on the Chords page: pad 5 rising, pad 6 falling (white, the
chosen one bright; with an arp pattern on, as strum's speeds: the stored one dim, the other dark).

Falling: the held entry's notes, the pad's own note included, are sent highest first at the strum's gap; the press
itself sends nothing (*builder's call*: the press takes the pad's note, as the arpeggio's press does, and the release
ends every note the entry sent). Release mid-strum: notes not yet sent never sound (as rising). The voice-room
fallback leaves out the same tone as rising. Recording: as rising (each note on its own step).

## 3. Mono record

Per track mode bit (RAM: 1 B), set on the Keys page. With mono on and live recording running, when stock's recorder
writes a note into a step (`0x0803F7BE`), the step's other units are removed first unless they were written in the
same group (D7). *Builder's call* how a group is told apart; a suggestion: the units written to the same step while
the recorder's position is still on that step in this pass (a per-track "step cleared this pass" marker), so a chord's
notes, written one after another at their note-offs, keep each other, and the next pass clears again.

Tests must show (emulation, through Record and the real recorder):
- a single note recorded onto a step holding other notes: only the new note remains;
- a chord recorded onto an occupied step: all its notes remain, the older ones go;
- an arpeggio at 1/16 over a loop of recorded notes: each step it played holds only the arpeggio's note;
- the next pass over the same steps replaces again;
- a stock edit afterwards (e.g. a step's velocity in the Velocity view) keeps the result;
- mono off: exactly stock (recorded patterns identical to stock's for the same input).

## 4. Pages

PL07's frame gets a third page: Keys (ToC pad 27, magenta). ▲ ▼ step over Chords → Arp → Keys. Keys has no quick
half, so Shift + 1-16/17-32 still flips Chords ↔ Arp.

Keys page: pads 1–2 poly · mono (magenta); pads 3–32 dark (fourths layout and the rest come later).
Chords page: pads 5–6 rising · falling (white) next to strum's speeds; pads 7–16 dark.

## 5. Budgets

RAM: count-in about 6 B (state, beat start, beats done, flags), falling strum 1 B, mono record about 5 B (mode bits
and a per-track marker): about 12 B of the 28 B left. Stack: measured; Main stays inside SL00D's headroom.

## 6. Testing

Emulation through the real routes as PL07 (controller presses, pads, the 1 ms service, the sequencer, Record):
- count-in: the four states and stock's metronome parameter; Clear's LED with Shift; the count (4 click calls at
  the beat spacing from the project BPM, the Record LED, then the transport playing and recording); cancel by Play;
  count-in off and Record not armed = stock;
- falling strum: order and gaps for triad / 7th / 9th with bass modes, release mid-strum, the voice-room fallback,
  page LEDs and the pattern-on rule; rising unchanged;
- mono record: the list in section 3;
- pages: three pages, ToC, ▲ ▼, the quick flip unchanged; transparency with everything off.

Device test plan `firmware/PL08/TEST.md` (count-in by ear and against the metronome, falling strum by ear, mono record
with a mono patch and in the step views).

## Not in scope

**Playback strum** (record the chord, strum it on playback, as upstream's arpeggiator: a separate candidate, likely
after ITCM); count-in length other than one bar; saving any setting (next: saved settings); fourths layout; mono record for step
entry; drum tracks.
