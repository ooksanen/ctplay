# Strum — design

Date: 2026-10-12 · Branch: `slim` · Version: `PL02` (bass modes added in `PL03`) · Status: implemented; PL02 passed on
the device 2026-10-12 (`slim/firmware/PL02/TEST.md`); plan `slim/docs/plans/2026-10-12-strum.md`

## Purpose

A chord from the chord engine (`PL01`) can be **strummed**: the pad's own note sounds on the press and the chord's
other notes follow one by one, a few milliseconds apart, in rising pitch. The speed is set per track.

Strum is the first CTPlay feature that sends notes **later** than the press that caused them. The pieces that make that
possible (a hook in the Main task every millisecond, a time base, the rule for sharing note sending between the UI and
Main tasks) are built so the arpeggiator and other timed features can reuse them. The queue's data structure is not:
strum keeps its pending notes in the chord engine's own table (approach A below), and a general queue waits until the
arpeggiator shows what it needs.

## Decisions

| # | Decision | Reason |
|---|---|---|
| S1 | **Millisecond timing** in v1 (fixed gap between notes, the same at any tempo) | Easiest: runs from the 1 ms heartbeat, playing or stopped, no tempo maths. Tempo-synced speeds can be added later on the same heartbeat (see Later) |
| S2 | Order: **the pad's own note first, then the other notes rising** | Stock plays the pad's note on the press (PL01 decision C4), so it is always first. Exact low-to-high in root position; with an inversion or a bass note, notes below the root come after it. Down strum is a later candidate |
| S3 | Control: **Shift + 1-16/17-32** cycles the visible track's strum: off → slow → medium → fast; LED 53 shows it while Shift is held | Shift + that button does nothing in stock (the controller's Shift mask drops it); slim's `button_press` hook sees it first, as SL00D's Shift + Drum 3 did. PL01's palette is full |
| S4 | Pending notes live in the **chord engine's held-chord entries** (approach A), not in a general queue | The entries already hold the notes; a separate queue would duplicate them in slim's 240 B of RAM and guess at the arpeggiator's needs |
| S5 | **Single writer:** every sink call for a strummed chord is made by the Main task; the UI task only changes entry state, in short `slim_irq_save` sections | A note-on can never follow its note-off; at most one note-on can follow the pad's release (when the release lands between the heartbeat's flags read and its send), and it is ended on the next heartbeat (corrected 2026-10-12 after the final review) |
| S6 | Heartbeat = an entry hook on the 1 ms dispatcher `0x0803C410`, slot 0 (the `main_ms` hook point, context `main`) | Runs in the Main task every millisecond, transport running or not, before Main takes the DSP lock (spike below) |
| S7 | Strum settings are **not saved** | As PL01's settings (C3); recorded strums do not depend on them |
| S8 | Once the strum version is published, **PL01 is reproduced from its git tag** (`PL01` at its publishing commit), not from the current sources | Strum changes `features/chord`, which `versions/PL01.toml` builds; the pinning test moves to the latest published version of each feature |

## Findings this design rests on

From the event-queue spike (2026-10-12, emulation and static analysis on the stock image; probes on
`refs/archive/spike-event-queue` (the branch `spike/event-queue` until 2026-11-21), `slim/spike/seqclock_*.py`). Confirmed on the device by PL02 (2026-10-12): the heartbeat runs playing and stopped, and the stress runs left no stuck
notes.

- **Main runs the clock.** The Main task's loop (`0x0801D5A4`) runs its soft-timer service
  `0x0801E4BE(0x20000354)` (driven by TIM5, millisecond units) and only then takes the DSP lock (`0x0801D5D4`) for the
  DSP service `0x08021392`. Soft timer 11 of that service, `0x080234EC`, runs every 1 ms and services a second timer
  set (`0x2000036C`) whose callbacks go through the dispatcher **`0x0803C410(slot)`**: slot 0 every 1 ms, slot 1 every
  333 ms. Slot 0 runs the sequencer clock `0x0802A3F8`.
- **The dispatcher as a hook point.** Entry bytes `10b50446` (`push {r4, lr}; mov r4, r0`): movable, no branch target
  inside, no PC-relative instruction. Its only reference is the callback word that `0x0803C432` registers for that
  timer set (`0x0803C490`); no direct callers.
- **Sequencer ticks only while playing.** Every millisecond the clock runs; while the Play store `0x20011034` is on, it
  publishes the tick store `0x20038D88` (`0x0802B43E`), whose listener `0x0802B886` (object `0x20038EC0`; upstream's
  "engine" `0x20038ECC` is its interface at `+0xC`) calls the sequencer tick `0x0802C418` (24 PPQN, 6 ticks per step).
  Stopped, the clock still runs and nothing is published. At the RAM dump's 94 BPM the emulation measured a tick every
  26–27 calls (37.6 ticks/s expected).
- **Notes from Main are normal.** Stock's own playback notes are sent from that point and take the DSP lock there
  (20 times in 400 ms of playback), up to 552 B of stack below the 1 ms service. The Main task has ≥ 1.5 KB of stack
  free (`firmware/SL00D/TEST.md`).
- **All tasks have priority 0** (task control blocks in the RAM dump: Main, UI, Storage, Content, IDLE). Stock already
  has two tasks feeding the router: playback from Main, pads from UI. New with strum: the **Note view's pad sink**
  (`note_sink_on` / `note_sink_off`) called from Main; stock calls it only from UI. Upstream observed on the device
  that a busy-waiting UI task kept another task's MIDI queue from draining (`docs/NOTAS.md`, SC32D.1), which suggests
  task switches happen at yields rather than anywhere; not verified, so S5 does not rely on it.
- Task entries (for reference): Main `0x0801D4B0`, UI `0x0801D680`, Storage `0x0805767C`, and the task named
  "Content" `0x08022ACC`, which is the file-operations task (its switch `0x08022B24`).

## 1. Architecture

**Foundation (shared)**
- `stock/symbols.toml`: hook point `main_ms`: `kind = "entry"`, `addr = 0x0803C410`, `expect = "10b50446"`,
  `displace = 4`, `args = ["uint32_t slot"]`, `ret = "void"`, `context = "main"`.
- slimbuild accepts the context `main`. `check_dsp_lock` keeps forbidding the DSP lock only from `dsp_tick`; `main` is
  allowed (the soft timers run before Main takes the lock, and stock sends notes from there).

**Chord engine (`features/chord`)**
- New hook: `main_ms` → `chord_on_ms(slot, ret)`: returns at once unless `slot == 0`.
- New hook use: `button_press` → `chord_on_button(ctrl, id, ret)` (section 3).
- A per-track strum setting (2 bits × 4 tracks, its own byte: PL01's settings byte is full).
- Held entry, new fields: `sent` (other notes already sounded), `vel`, `due` (16-bit millisecond time of the next
  note), a `released` flag, and a `strum` flag (the entry is driven by the heartbeat).
- **Press (UI):** strum off → PL01's path, unchanged. Strum on → the entry is filled with the other notes sorted
  rising, `sent = 0`, `due = now + gap`, `vel` = the pad's velocity; the entry becomes visible to the heartbeat last,
  inside a critical section. Nothing is sent to the sink from the UI task; stock plays the pad's own note.
- **Heartbeat (Main), every 1 ms:** `now += 1`; for each strummed entry: if `released`, send note-offs for
  `notes[0 .. sent)` and free the entry; otherwise, while `sent < count` and `now − due ≥ 0` (signed 16-bit), send
  `note_sink_on(notes[sent])`, `sent += 1`, `due += gap`. The sink is found from the entry's track through the track
  container (`0x20040DB8 + 0x18 + 4 t`) and checked with the same `note_sink()` test as the UI path; an entry whose
  view no longer passes the test is freed without sending.
- **Release (UI):** decided by the **entry's own `strum` flag**, not the track's current setting (which can change
  while a chord is held): an entry without it → PL01's path; with it → set `released` (critical section), return; Main
  ends the notes within 1 ms. The safety net at stock's note-off (`chord_off_pad`) follows the same rule. This covers the pad release, a re-press of the same pad (PL01 releases first) and the view switch (stock
  releases held pads through the same release handler `0x0804ACC4`).
- The state change and the sink calls never overlap: Main reads and updates an entry's fields in a critical section
  and calls the sink outside it, with the entry still marked as its own (`strum` set, not free), so the UI never reuses
  it mid-send.

## 2. Timing and order

| Setting | Gap between notes | 9th + bass (5 other notes) spans |
|---|---|---|
| off | — | PL01 behaviour |
| slow | 50 ms | 250 ms |
| medium | 25 ms | 125 ms |
| fast | 10 ms | 50 ms |

The gaps are constants, tuned on the device. All notes use the pad's velocity.

- **Order:** the pad's own note on the press; the other notes in rising pitch, including a bass note below the root
  (it comes right after the root).
- **Time base:** the heartbeat's own call count, 16 bits; due times compared by signed difference, so wrap-around is
  harmless. The emulation advances it by running the real 1 ms service.
- **Catch-up:** when Main is late (e.g. an SD-card load), stock's soft timers run several calls in a row; overdue notes
  then sound together, as stock's own timers do.
- **Edge cases:** release mid-strum: the notes not yet sounded never sound, the sounded ones end within 1 ms. Re-press
  of a pad mid-strum: the old chord is released first (PL01), then a new entry starts. Table full: the pad's own note
  only (PL01). Shape single with bass off: nothing to strum.
- **Recording:** each strummed note reaches the stock recorder through the pad sink, as in PL01, when it sounds.
  **Corrected after the device test (2026-10-12):** the recorder puts each note on its own step, so a strum does not
  record as a roll: a slow strum at 120 BPM landed on 3 consecutive steps. Strum is a performance feature; recording
  with strum on is safe (`firmware/PL02/TEST.md`, 14 and 17b). A recorded roll needs the notes written into one step
  with microstep offsets (pattern writer; candidate "Recorded strum").
- **Chord-note dropouts** (`docs/investigations/2026-10-12-chord-voice-dropouts.md`): notes of a 5–6-note burst can be
  lost to the synth's voice handling under DSP load, on stock too. Strum spreads the burst over time (and a recorded
  slow strum over several microsteps); whether that changes the dropouts is to be **observed on the device**, not
  assumed. Strum does not change the number of notes.

## 3. Control and LEDs

- **Shift + 1-16/17-32** (button id 21) through the `button_press` hook: with a Note view on screen (the same test as
  the palette's LEDs: container active, mode 1 or 6, the track's sub-view a Note view) and Shift held, each press
  cycles **the visible track's** strum off → slow → medium → fast → off and returns `HANDLED`. Any other view, or no
  Shift: `PASS`; plain 1-16/17-32 keeps switching pages. The release of the button goes to stock untouched; a test
  shows that Shift + button 21 press and release change nothing in stock (view, LEDs, stores).
- **LED 53** (the button's LED) shows the setting while Shift is held in a Note view: off = dim; slow / medium / fast
  = three distinct codes. Without Shift it shows what stock shows. Before choosing the codes: find out whether LED 53 is
  one of the RGB LEDs or a single-colour one (upstream counts 60 RGB and 9 single-colour of the 69; the conversion is
  `0x0803423C`); single-colour → brightness levels. Each code's colour is checked in emulation against stock's own
  LEDs (stock reads some colours from a palette in RAM: upstream SC37.9) and confirmed on the device.
- **During a strum** the key pads light only for notes that have sounded (PL01's chord highlighting, limited to
  `notes[0 .. sent)`), so the strum is visible on the pads. PL01's Shift palette on pads 17–32 is unchanged.

## 4. State and budgets

| State | Size |
|---|---|
| PL01: settings 4 B, held chords 6 × 8 B, consumed pads 4 B | 56 B (60 B measured) |
| Per held entry: `sent`, `vel`, `due` (16 bit), flags (`strum`, `released`) | + 4–5 B × 6 |
| Strum settings, 4 tracks × 2 bits | 1 B |
| Millisecond counter | 2 B |
| **Total (estimate)** | ≈ 87–93 B |
| **RAM budget** (`feature.toml`) | **96 B** (was 64) of slim's 240 B |
| Flash (estimate) | + ~0.5 KB (PL01: 1.9 KB) |
| Stack budget | 128 B per handler as in PL01; the manifest's `hook_stack` gives the real depth per hook point, including `main_ms` |

The device test plan has a stack gate for the Main task (as PL01's for UI), read from SL00D's stack page figures.

## 5. Testing

**Fast tests (no emulation)**
- `main_ms` verifies against the stock image (`symbols.verify`, `hooks.check_entry`).
- The context `main` is accepted; `check_dsp_lock` still rejects a `dsp_tick` path to the lock and accepts a `main` one.
- The pinning test covers the latest published version of each feature (S8); PL01 stays covered by its tag.

**Emulation (`tests/test_chord.py`, `NoteHarness`)**, through the real routes: pads and buttons through the controller,
the heartbeat through Main's real 1 ms service **`0x080234EC`** (never by calling `chord_on_ms` directly):
1. Strum off: every PL01 test passes unchanged.
2. Timing and order: the press sounds only the pad's own note; each other note follows exactly `gap` heartbeats after
   the previous one, in rising pitch, at the pad's velocity; for each speed and for 9th + bass.
3. Release mid-strum: no note-on after the release; note-offs only for the sounded notes, sent from the heartbeat;
   nothing left on in the router. The same for a view switch and a re-press of the pad.
4. Note-balance fuzz (PL01's), with random heartbeat advances and random strum settings: every note-on has its
   note-off, whatever the order of presses, releases and heartbeats.
5. Recording: each heartbeat-sent note becomes its own pending entry in the track recorder.
6. Control: Shift + button 21 cycles the visible track's setting; LED 53 shows it while Shift is held; on the stock
   image Shift + button 21 press and release change nothing.
7. LEDs: during a strum only the sounded notes light.
8. Transparency: the stock-vs-build comparison still passes; the heartbeat changes nothing while no strum is pending.

**Device test plan** (`firmware/<marker>/TEST.md`): the three speeds by feel; release and view switch mid-strum (no
stuck notes); a slow roll recorded, then played back on the stock firmware; LED 53's colours; the Main-task stack gate;
a **stress run** (fast strummed chords on two tracks while the sequencer plays a busy pattern: a Main/UI collision on
the router would show as stuck notes); chord-note dropouts with and without strum (observation, section 2).

## Later (not in v1)

- **Down strum** (the pad's own note, then the other notes falling).
- **Tempo-synced speeds** (gaps in microsteps or ticks), on the same heartbeat; needs the tempo while stopped (the clock
  `0x0802A3F8` runs then too).
- **True pitch order** (hold back the pad's own note when notes lie below it): changes PL01's C4.
- **Strum in the palette**, if the palette is reworked (e.g. after the chord-size decision in the dropout
  investigation).
- A **general event queue** when the arpeggiator (or note repeat, latch) needs one; the heartbeat, the time base and
  the single-writer rule carry over.

## Not in scope

Drum tracks; step entry (chords in step entry are a separate candidate); MIDI-in notes; the context of the sequencer
tick under external MIDI clock (not needed: strum does not use the tick); the DSP.
