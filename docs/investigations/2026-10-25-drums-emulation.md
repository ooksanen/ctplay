# Drums: emulation spikes (2026-10-25)

Throwaway scripts in [2026-10-25-drums-spike/](2026-10-25-drums-spike/) (how to run: its README). Stock image in slim's `NoteHarness`, real button / pad routes; CTPlay actions imitated from Python with stock's own functions. Summary and what it means: [2026-10-25-drums.md](2026-10-25-drums.md).

Pointers (asserted): drum recorder [0x2003C174 + 4(4+d)] vt 0x0805A578: +0x48 base, +0x4C step store, +0x14 position
store; editor = step store listener 0, vt 0x0805C108; playing store [0x20038EC0 + 0x30 + 4(4+d)]. Drum 1: base
0x2001E5B0, store 0x2003AD30, editor 0x2003ACD0.

## Spike 1: the write path — works
Recipe: raw 128 B; if [store+0x18] == pattern+0xA8, 32 words into both [store+0xC] and [store+0x10]; 0x08035456;
(optional detach 0x08035398(store, editor, 0)); commit 0x080353C0; re-attach (-1).
- Bytes exact, store read view == pattern, with or without detach (q1_write [B]).
- Step LEDs at once: hit 0x13, empty 0x14; identical to the same bytes entered by stock pad presses (A, A2). LED colour
  follows the flip (flip 0x08 -> 0x5F), not velocity (B2).
- Survives stock edits: a step pad press (C: pad 15 adds vel 0x60 micro 1; ours keep vel 100) and a Velocity-view edit.
- Velocity, Gate/micro, Probability views repaint live == painted fresh (q1_views).
- Negative control: raw-only -> LEDs stale, views read the store; one stock pad press rewrites all 128 B from the stale
  store, our hits gone (D).
- Not mirrored (pattern 5): raw only; later stock edits of pattern 0 leave it alone (E).
- Undo by the same path restores bytes, store, LEDs (F).
- Stock step press: empty -> vel 0x60, micro 1, flip 0xFF; hit -> vel 0, micro 0, flip 0xFF; commit inside the press.

## Spike 1: the mode byte — a drum button always gives mode 1
- press(4) and page_open's replay give mode 1, track 4, container active, step view 0x0805AD0C top, sample view
  0x0805ABBC bottom, from every start tried (Synth 1 modes 0-6/8, Drum 2 mode 6, Drum 1 modes 6/2/0, Mixer, FX,
  Patterns). cont_track_view(cont, m) writes m to [cont+0x18C] (0x08043520).
- Mode 6: Note (9) toggles 1 <-> 6; Shift + Note also gives 6. Ids: 9 Note, 10 Velocity, 11 Gate (again 8),
  12 Pattern Settings (again 5 Probability), 13 Patterns (vt 0x0805A5F0).

## Spike 1: mirrored vs playing pattern
- Normally equal, also through chains and Patterns-view picks / queued changes.
- [editor+0x24] = a step pad of that drum is held (press 0x0804E27E writes 1 at 0x0804E2AC, release 0x0804E45C writes
  0 at 0x0804E4E4); the editor catches up after release.
- 0x20039DE0 toggled only by Shift + Patterns (0x080333A0 -> 0x0803354C -> 0x08045D5A([ctrl+0x54])). At 1 the editors
  stop following: the chain plays pattern 1, the store / LEDs / stock edits stay on pattern 0. Guess: stock's
  "pattern follow" setting (name not checked).
- [store+0x18] test stays safe in both cases; the spec must choose "current" = shown or playing.

## Spike 1: not settled
- 0x20039DE0's stock name; [E+0x70+4t] "next" showed no queued pattern; device LED refresh; recorder race while
  recording; emulator hangs: Preset held + pads (0x0801BE72), button 26 held + pads (0x08022AB6).

## Spike 2: note repeat through a live drum sink — stock records it

Setup: stock image, recorder gates running, drum 1 at 240 BPM, its playing pattern emptied raw then reloaded by the
editor load `0x0803F050`; Record, Play, Shift + Record through the real buttons. Each hit sent with `note_sink_on` /
`_off` right after the heartbeat that counted its tick (the arp's place). Notation `sN:vV/mMMMMMM` = step, velocity,
microstep mask (bit 0 right).

- **Baseline finger press (r1):** pad 29 in mode 6 and a sample pad in mode 1 record the same. Quantise on (the
  snapshot's): the write happens at the step's tick 3 (`0x0803F9A2`), offsets 0–2 go to that step, 3–5 to the next
  (step 9 + 4 ticks → step 10, micro bit 0). Quantise off (Shift + Record flips `[rec+0x35]`): micro bit = the hit's
  tick (step 5 + 2 → m000100). The snapshot forces live drum velocity to 96 (bit 1 of p2 of `[0x2003ECDC+0x94]`,
  `0x080325C0`; which panel setting: not settled, guess Shift + Velocity's fixed velocity). Runs 2–7 clear it.
- **Repeats over two bars (r2, r2b, r2c), velocities falling 120 → 70:**

  | Rate (ticks) | Quantise off | Quantise on |
  |---|---|---|
  | 6 (1/16) | 32/32 steps, m000001, each hit's velocity | same |
  | 3 (1/32) | every step m001001 | one hit a step |
  | 2 (1/32T) | every step m010101 | one hit a step |
  | 1 | every step m111111 (192 hits) | one hit a step |

  One velocity per step: the last hit's (quantise on: the last before tick 3). Quantise on, a late hit in the last
  step lands on step 0 of the next pattern in the chain. 1/64 (1.5 ticks) cannot be placed; two note-ons in one tick
  gap make one write with the last velocity. While mirrored, store and pattern stay identical and a later stock commit
  keeps the hits.
- **Re-hits (r3):** a repeat that never sends note-off records every hit (the router ends the held note first); a
  hanging note-on does not block later hits; a finger held on pad 29 while repeats send with another source: every
  repeat records, the finger's same-tick hit is overwritten.
- **Count-in and stopped (r4, r7):** nothing records (PL15's count-in too: the transport stays stopped during it).
- **Sinks (r4):** the expanded view's (`0x200434E8`) and the sample view's (`0x20042D68`) sinks record in mode 1 and
  6; the player's sink (`0x20040870`) does not. A drum muted through its store (`[player+0x28]` p0) still sounds,
  sends MIDI and records from the live sink.
- **Side effects (r6):** each note-on and each note-off takes the DSP lock once (from Main: fine; never from the DSP
  tick); one MIDI note per hit; pad 29 white while sounding, back to its colour after the off. No forbidden writes.
- **PL15 (r7):** its hooks change nothing; patterns byte-identical to stock.

## Spike 2: not settled
Device-only: the DSP's no-softer-retrigger rule; the unlocked router / recorder shared by the finger (UI) and the
repeat (Main), as PL06's arp. Also: swing, external MIDI clock, sync rates other than 1/16, the Mixer mute through its
pad route, the LED after a repeat whose last note-off never comes (expected white).
