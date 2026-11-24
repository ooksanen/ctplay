# Chord voice room (PL04 / PL04D) — design

Date: 2026-10-13 · Branch: `slim` · Versions: `PL04` (CTPlay), `PL04D` (= PL04 + the voice log) · Status: direction
approved by the user 2026-10-13 (option 1 with option 3 as the fallback); implemented (plan
`slim/docs/plans/2026-10-13-chord-voice-room.md`), device test `firmware/PL04D/TEST.md` pending

## Purpose

A strummed 5-note chord loses its first note: in PL03 step 7 (rootless 9th) the bass, in step 5 (bass below) the pad's
root. PL03D measured why (`docs/investigations/2026-10-12-chord-voice-dropouts.md`, "PL03D device run"): stock starts a
new voice only if its spare-time reading says **1.25** more voices fit; below that the DSP takes the synth's oldest
voice, even with free voices. In step 7 the 5th note had room for 1.11–1.21 voices. PL04 lets **chord-engine notes**
take a free voice when **one** more voice fits, and, when even that will not hold, leaves out the chord's least needed
tone instead of losing the bass.

Success:
- Step 7 and step 5 with the simple patch of the PL03D run: all five notes keep sounding; PL04D's log shows the 5th
  note on the ARM path with a reading between 1.0 and 1.25 voices.
- With a heavier patch, where the 5th note would have under one voice of room: the strummed chord plays four notes
  (the fallback), the bass and root keep sounding, and no stolen note is logged.
- Everything that is not a chord-engine note (stock's pads, the sequencer, MIDI in) behaves exactly as in PL03.

## Decisions

- **Floor `0x10000`** (one voice of the current patch, by the DSP's own estimate) for chord-engine notes, instead of
  stock's `0x14000`. Only stock's quarter-voice margin is given up. Readings vary by about 0.05–0.2 voices between
  repeats; step 7's 5th note measured 1.11–1.21, clear of the floor.
- **Only when a free voice exists** in the synth's range (state word high half 0, stock's own test at `0x080216F0`):
  then stock's ARM picker takes that free voice. Without a free voice nothing changes (stock's DSP path).
- **Only chord-engine notes:** chord.c marks the track while it sends a chord note; the rule applies to a decision for
  that synth only while the mark is set. Stock's pad note (the root, or the bass in rootless mode) keeps stock's rule:
  in a strum it is the first note (plenty of room), in a one-burst chord the readings lag (PL03D #6: all five held).
- **Fallback (option 3), strummed 5-note chords only:** just before the chord engine would send the chord's droppable
  tone, it estimates the reading the chord's last note will see; under the floor, it leaves that tone out. Droppable:
  the 5th (shape degree 4) when the chord has one (rootless 9th: bass + 3rd, 7th, 9th remain), else the 9th (bass-below
  9th, which already has no 5th: root, bass, 3rd, 7th remain). One-burst chords get no fallback (not needed: #6).
- **Strum-off LED** `0x03` (animates on the device) → `0x02` (steady dim white), as agreed in `docs/followups.md`.
- **PL04D** = PL04 + `voice_log`, with the page's labels corrected: `r` = **sounding**, `H` = **starting** (bit 31 of the
  state word marks a voice allocated in this burst and not yet started), plus a column showing when the floor applied.
- **Markers:** `PL04` and `PL04D` differ in their first 6 bytes. PL03 and PL03D keep their tags.

## Findings this design rests on

- Stock's voice decision `0x080217B4` (spec `2026-10-13-voice-log-design.md`): `dsp_read(0, 0x36 + synth)` at
  `0x080217EA`; `>= 0x14000` → the ARM picks by polyphony mode (a free voice when one exists); below → the DSP takes a
  sounding voice (voice 0 in every PL03D run).
- The reading = further voices of the current patch that fit, `0x10000` per voice, computed per synth at the end of each
  DSP block (`P:$1C01`; logs: steps of about `0x10000` per sounding voice).
- A chord note reaches the decision synchronously inside `note_sink_on` (UI task for a press, Main task for a strummed
  note; both seen in emulation).
- Strum order: stock's pad note first, then the chord's other notes rising (chord.c `sort_rising`), `STRUM_GAP` ms apart.

## 1. Foundation: filter handlers on call hooks

A `call` hook on a function that returns a value (PL03D's foundation) gains **filters**: a feature's `[[hook]]` with
`filter = true` gets `uint32_t handler(ARGS, uint32_t result)` and returns the value passed on; observers (no `filter`)
keep `void handler(ARGS, uint32_t result)`. The wrapper runs the handlers in priority order, each seeing the value as it
stands after the handlers before it, and returns the final value to the call site. The build refuses `filter = true` on
an entry hook or a void call hook. Existing builds generate the same code (no feature uses `filter` yet).

`voice_log` observes at priority 40 (the raw reading); the chord engine filters at priority 50.

## 2. Chord engine changes (`features/chord/`)

**Marking chord notes.** `play()` and `chord_on_ms()` set `chord_sending = track + 1` immediately before each
`note_sink_on()` and clear it after. Another task's note-on on the same synth inside that window (a sequencer note
exactly then) would also get the floor: harmless (one voice that fits by the DSP's estimate).

**The filter** (hook `voice_headroom`, `filter = true`), `uint32_t chord_on_headroom(core, addr, result)`:
- always: per synth, keep the last two readings seen at any decision (`room_last[2]`, `room_prev[2]`), for the fallback;
- when `chord_sending == synth + 1` and `0x10000 <= result < 0x14000` and the synth has a free voice: return `0x14000`
  (stock takes the ARM path and picks the free voice); otherwise return `result` unchanged.
- It reads RAM only and calls nothing (context `dsp_locked`).

**The fallback.** At the press, a strummed chord of 5 sounding notes (the pad's own + 4) records which of its `notes[]`
is droppable (the 5th degree, else the 9th). In `chord_on_ms`, before sending `notes[sent]` when it is the droppable
one: with `r` = the synth's last reading (taken at the previous note's decision, before that voice started) and
`step = room_prev - room_last` (at least `0x8000`), counted from the synth's readings since the press: two or more → the measured step (no fall between the last two → no drop); only the pad note's (the droppable tone is the first chord note, e.g. inversion 2 or the wide spread) → one voice per note, the reading's own unit; none (no voice decision, e.g. a MIDI track) → no drop, the last note's reading is estimated as
`r - (notes still to sound, this one included) × step`; under `0x10000`, the note is skipped (counted as sent, never
sounded, so the release sends no note-off for it and its pad does not light). Example, PL03D #3: before the 5th degree (3rd note), r = `0x42E00`,
step = `0xF300`, estimate `0x42E00 - 3 × 0xF300 = 0x15500` ≥ floor → sent; the 5th note then measured `0x11D00` and
takes a free voice.

**State and budgets.** `chord_sending` (1 B), `room_last[2]` / `room_prev[2]` (8 B), `room_n[2]` (2 B), a droppable
index in `held_t` (+1 B × 6; its own byte: the heartbeat never writes `flags`, which the UI task's release sets): about 15 B more RAM (PL03 uses 88 of 240 B; PL04D with the log about 235 B: the plan checks the build fits
and, if not, shrinks the log ring to 10 records for PL04D).

## 3. Testing

- **Foundation:** codegen text for filter and observer handlers; the build refuses `filter` on entry / void hooks;
  SL00D, PL03, PL03D rebuild identically.
- **Emulation** (VoiceHarness, the DSP mailbox model; tests set the reading per decision):
  - a chord note with the reading at 1.1 voices and a free voice: ARM path, a free voice, no voice stolen;
  - the same reading for a **stock pad note** (no chord) or a sequencer-style call without the mark: stock's DSP path;
  - reading 0.9 voices: stock's DSP path (the floor holds);
  - no free voice: stock's path;
  - step 7 with PL03D's measured readings: all five on the ARM path, the bass's voice untouched;
  - a heavy-patch sequence (steps of `0x10000` from `0x40000`): the 5th degree is skipped, four notes sound, release
    leaves nothing on;
  - bass-below 9th heavy: the 9th is skipped;
  - a skipped tone never lights its pad and gets no note-off;
  - one-burst chord: no skipping;
  - transparency: with readings always high, PL04 sends the same notes and LEDs as PL03 (except the strum-off LED).
- **Device** (`firmware/PL04D/TEST.md`): step 7 / step 5 / strum off / rootless 7th with the PL03D simple patch, then
  with a heavy patch (several oscillators, effects up): listen for the bass and for clicks or glitches, paste the log
  after each step. Then PL04 (no log) once, for the normal build.

## Not in scope

- Changing stock's rule for its own pads or the sequencer.
- Choosing which voice the DSP steals; decoding its picker (`P:$1BB3`).
- Spreading chords across Synth 1 and Synth 2 (the user's projects use different patches on them).
- A fallback for one-burst chords or for chords other than 5 notes.
