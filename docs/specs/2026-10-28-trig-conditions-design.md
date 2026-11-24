# Trig conditions (PL20) — design

Date: 2026-10-28 · Branch: `slim` · Status: **approved by the user 2026-11-01** (open points settled 2026-10-31: the list at
the end); **builder check done 2026-11-01** in emulation (`investigations/2026-11-01-trig-conditions-spike/`:
`A-storage.md`, `B-counting.md`, `C-controls.md`), its results folded in below; LAST settled again the same day; **2026-11-07: Played strums release at once folded in** (section after "Decided by
the user"). Candidate row: `candidates.md`, "Trig conditions". Research:
`research/2026-10-28-trig-conditions.md` (26 products). Storage and hooks: `investigations/2026-10-28-trig-conditions-storage.md`
(static reading; its "Not confirmed" list is the plan's first tasks). Row-4 mockups: `layouts/trig-row4.html` (option C
picked). Builds after PL19 (pattern strum); PL19's plan waits for PL18 to land.

**As built (PL20, 2026-11-08).** The body below is the approved design; where the build differs, this note wins:
- **A cycle with every pass ticked** is kept and plays every pass ("Pass conditions" says "not all").
- **A pass ends** at stock's own track advance (`fp` == 0) where the pattern ends or a scene changes; only that event
  can start a track over (stock flags a waiting pick at every step boundary). Shift + Play with a pick waiting keeps
  the counts, and the pick still starts its track over when it takes over. A waited pick or a scene recalled by hand
  starts PRE over too (my call 7), as every start-over does.
- **The count wraps from 1679 back to 840**, not mod 840 ("Counting"): every cycle stays exact and count 0 (FIRST)
  comes only once per start-over.
- **FILL:** a tap after a finished fill arms again with one tap; Stop disarms with a drum page open too; the pad is
  bright only while the fill pass is still armed. A start-over ends a running fill and keeps which tap it was.
- **Storage hooks, the drum Write's clear and its Undo, and step entry's drop act only in a marked project.** Mutate
  has its hook (no fallback rule); Undo restores a drum Write's conditions.
- **Played strums release at once** with a minimum of two ticks for a late note that starts after its block-chord
  end. The rulings and open minors: `followups.md`, "From the PL20 build"; the device test: `firmware/PL20/TEST.md`.

## Purpose

A pattern goes stale when it plays the same every pass, drums most of all. Trig conditions let a step play only on
some passes of its pattern: the 2nd of every 2, passes 1 and 3 of 4, only the first time, only during a fill. A
1-bar pattern can then sound like 8 bars without more patterns. The user records alone and with friends, mostly in
chained patterns: the "set and forget" conditions (passes) are the core, the live one (FILL) is for performers.

**Success:**
- Drums: a snare step set to pass 4 of a 4-pass cycle plays on every 4th pass of its pattern, in a loop and in a
  chain, and the lit pads in row 4 show exactly that.
- Synth / MIDI: two chord steps micro-timed onto one spot, one on pass 1 of 2 and one on pass 2 of 2, alternate the
  chord every pass.
- Stock firmware plays every step on every pass (the conditions are invisible to it), and stock's own edits keep or
  clear them as they do the step.

**Non-goals:**
- Cycles longer than 8 passes (8 pads; Elektron stops at 8:8 too).
- NEI (a neighbour track's result): niche and the most confusing condition in the research.
- A "random once per loop" or "never twice in a row" condition (no product has them; later if wanted).
- Conditions on parameter locks / automation.

**Anti-goals:**
- Any change to what stock's probability view does on rows 1–3.
- A step that a condition silences behaving unlike a failed probability roll (ties, note-offs).
- Losing or mis-moving a condition through stock's own edits (Clear, Duplicate, copy, Mutate) without saying so.
- Work during a pad press that could make a phantom press on the next pad.

## Decided by the user (2026-10-28)

- **Drums first** (beats go stale fastest), **note tracks too** (rhythmic variation in chords / melody).
- **Recording users first, performers not forgotten.**
- **The place:** row 4 of stock's probability view (Shift + Pattern Settings), which stock ignores.
- **Option C of the mockups:** row 4 is a **pass grid**; **Shift held** swaps row 4 for the **special conditions**
  (one pad per value). Shift as a modifier / layer switch, room left for later conditions.
- **Counting:** each pattern counts its own passes. The counts **start over whenever the user chooses** (Play from
  stop, a pattern or chain picked by hand, a scene recalled, a project loaded) and **keep counting while a chain
  advances by itself** and while a pattern loops.
- **FILL:** hold = fill while held; tap = fill on the next whole pass, then off by itself.
- Upstream compatibility is a bonus, not a constraint: CTPlay's own encoding and UI.

Settled 2026-10-31 (the user):
- **FILL per drum, in the drum expanded view** (Drum N, then Note again): pads 21–24 of row 3, right above the drum
  pads 29–32. The user: a feature for the drums belongs with the drums, not under Mixer, Preset or 1-16/17-32. **No
  FILL for note tracks in PL20**; pads 17–20 (note tracks, in the track buttons' order) and 25 (every track) stay free
  for it. Long or double presses of Drum N were dropped: a track button switches the view on its press.
- **LAST** = while a pattern or scene picked by hand waits to take over: every step from the pick until the
  takeover (2026-11-01, after the builder check: stock switches every track at once when a scene takes over, at Drum
  1's pattern end). Never true while a chain advances by itself.
- **PRE** looks back to the track's last step with a condition (not PRE / NOT PRE) or a probability below always,
  and uses whether it actually played: linked randomness.
- **Plain row 4 with a special condition:** all 8 pads dim in the special's colour.
- **A scene change while playing starts the counts over**, by the "the user chose" rule (a scene is a section).

## Also in this build: Played strums release at once (user, 2026-11-07)

Not a trig condition: folded into PL20 from PL19's device run. On a Played track (PL19's pattern strum) every note of
a strum ends where stock would end it in a block chord (its own length counted from the step), so a chord whose notes
share one gate releases at once, as when a strummed chord is let go live, instead of each late note keeping its full
length from its own late start. No setting (Off and Written unchanged). Detail and the idea of a
"strummed release" setting for later: `followups.md`, "From the PL19 build". The plan adds one task (the queued
length in `features/chord/pstrum.c`, its tests in `tests/test_pstrum.py`, TEST.md rows on a Played track).

## The behaviour

### Pass conditions (the core)

- A step has **no condition** (plays every pass, stock), **a pass cycle**, or **a special condition** (below).
- **A pass cycle** = a length L of 2–8 passes and the passes of it the step plays on (any mix, at least one, not all).
  Pass p of the pattern (counted from 1) is pass ((p − 1) mod L) + 1 of the cycle.
  - Elektron's A:B = cycle B with pass A ticked: 2:2 plays on passes 2, 4, 6; 2:3 on 2, 5, 8; 5:7 on 5, 12, 19.
    "Not A:B" = every pass but A. All 35 Elektron ratios (1:2 … 8:8) and any other mix (passes 1 and 3 of 4).
- **Stock's probability still applies** (row 3): the step must pass its condition **and** its roll ("1:4 at 50 %").
- A silenced step behaves like a failed probability roll: CTPlay answers at stock's probability tests (note tracks
  `0x08040D8A` in `seq_units_start`; drums `0x0804AA18` and `0x080411F6`, the second so a silenced step does not
  switch the drum to its flip sample).

### Special conditions (Shift layer)

| Value | Plays when | Notes |
|---|---|---|
| FIRST / NOT FIRST | the pattern's first pass since its count started over / every pass but that one | In a chain: an intro, the first trip through the song only |
| FILL / NOT FILL | the drum's FILL is on / off | NOT FILL = drop this step during fills. Drums only in PL20: on a note track both pads stay dark |
| PRE / NOT PRE | the track's previous conditional step played / did not | Conditional = a condition other than PRE / NOT PRE, or a probability below always; "played" = it sounded (condition and roll). A PRE step does not update the state. No conditional step since the counts started over: PRE silent, NOT PRE plays. The look-back runs across the pass boundary |
| LAST / NOT LAST | a pattern or scene picked by hand waits to take over / no change waits | From the pick to the takeover: the rest of the current pass for a pattern; for a scene, every track until Drum 1's pattern ends (a short track may loop through it more than once). Never true while a chain advances by itself. Read from stock's waiting flags: the track's chain store parameter 8 + t, the scene chain's parameter 1 |

### Counting

- One counter per (track, pattern): 8 tracks × 8 patterns, counted mod 840 (the LCM of 1–8, so every cycle stays
  exact). RAM only, not saved: ITCM or the RAM above the heap (the builder picks; cleared at power-on).
- **Counts a pass** where a track's pattern ends (`0x0802CD42` in the track advance, all 8 tracks; count only when
  look-ahead `fp` == 0 and `r4` (pattern ends) is set; the track = `[sp + 0xC]`, the pattern that ended = `sb`),
  before the next pass's first step plays. Confirmed for loops, chains, first / last steps (wrapping too), all four
  directions (a ping-pong pass = the round trip; a random pass = as many steps as the pattern has), every sync rate,
  muted tracks. A pass cut short by a scene taking over counts too, as does the partial first pass after an
  immediate switch.
- **Starts over** (the track's counters to 0): Play from stop (`seq_start`), the track's chain set by hand (a pattern
  or chain picked, a scene recalled; a scene that takes over while playing too, unlike upstream, which counts it as a
  pass end), a project load. Where (builder check): a waited hand change at `0x0802CD42` (hand flag `[sp + 0x18]`;
  a scene: the scene chain's parameter 1, latched at `seq_tick`'s entry to tell it from a scene chain advancing by
  itself); the immediate path `0x0802C240` (Shift + a Patterns pad, a pick while stopped, a load while playing; from
  `0x0802B948` / `0x0802B9BA`); a project load at `session_applied`.
- **Keeps counting:** a scene chain advancing by itself (the user's rule: a chain advancing by itself), and **Shift +
  Play** from stop, which continues where it stopped without `seq_start`.
- **Evaluated once a step** at its tick 0, both player classes, muted tracks too, so PRE and the six microstep calls
  see one result. Not at `0x0804A6B8` (a `bl` followed by PC-relative code: slim's mid-hook check refuses it): at
  `0x0804A6C0` (mid, 4 bytes, act when `r5` == 0; pattern `sb`, step `r8`, player `r7`), or `0x0804A6AC`, or an entry
  hook on `0x0804A684`. Every player's tick-0 pass runs before any probability test in the same tick.

### FILL

- **Per drum**, in the drum expanded view (Drum N, then Note again; stock ignores pads 1–28 there,
  `0x0804ED50`): **pads 21–24 = FILL for drums 1–4**, each right above its drum pad (29–32). The view stays as it is
  otherwise: rows 1–2, pads 17–20 and 25–28 dark.
- **Hold:** that drum's FILL is on while held.
- **Tap:** that drum's FILL is armed for its next whole pass (from its next pass start to its end), then off by
  itself. Tapping again while armed disarms. Tap or hold: the builder picks the split (the ½ s of row 4).
- LEDs (steady codes, picked on the device): dim = off, bright = on, a third steady code while armed.
- RAM only, off at Stop.
- Only with no CTPlay drum page open: a page (Shift + Drum N) covers the view, as pages do everywhere.
- The press and release come through the view's own handlers (`0x0804ED50` / `0x0804ED68`), which get exactly one
  release in every case, view changes included.
- **Later:** pads 17–20 for the note tracks (Synth 1 / 2, MIDI 1 / 2, in the track buttons' order) and 25 for every
  track at once; until then a note track has no FILL.

## The control: probability view, row 4 (option C)

Rows 1–2 pick the step and row 3 is stock's probability, as today. Stock accepts a row-3 press when a step pad is
held, the transport is stopped, or `0x20039DE0` p0 = 1 (the step editors do **not** follow the playhead; Shift +
Patterns toggles it; at 0, the default, the selection follows the playhead); row 4 follows the same rules. Stock edits
one step at a time (the held step, else the selected one); so does row 4. Stock does nothing with row 4 (with Shift,
a step held, stopped or playing) and never lights it; Shift changes nothing in this view.

**Plain row 4 = the pass grid** (pads 25–32 = passes 1–8):
- No condition: row 4 dark.
- **Hold a pass pad ½ s:** the cycle length becomes that pad's number, with pass 1 ticked (1:L; from another length,
  the ticks that fit are kept); pads 1..L light dim (available), pads past L dark. Holding the current length's pad
  ½ s again clears the condition.
- **Tap a pass pad** (within the cycle): ticks / unticks that pass; ticked = bright. Unticking the last ticked pass
  clears the condition (user, 2026-11-07: no cycle with nothing ticked; it frees the codes for the specials).
- A step with a special condition: **all 8 pads dim in the special's colour** (hold Shift to see which). A tap does
  nothing; holding a pass pad ½ s replaces the special with a cycle of that length.

**Shift held = the special layer** (pads 25–32, one pad per value): FIRST, NOT FIRST, FILL, NOT FILL, PRE, NOT PRE,
LAST, NOT LAST. Dim = available, bright = the step's condition; pressing the lit one again clears it. Picking a
special replaces a pass cycle and the other way round (one or the other: the drums' 9 bits).

- **Shift + row 3 stays stock's** (a plain probability press: stock does not test Shift).
- Colours (steady codes only, picked on the device): passes cyan, FIRST green, FILL orange, PRE violet, LAST yellow;
  the NOT pads the same hue, told apart by place.
- **The ½ s hold is a new gesture in CTPlay.** No work on the press beyond flags; writes on the pad's release (the
  phantom-press rule). The probability views have no release of their own: an entry hook on the container's release
  `0x080435F0`. On a view change stock releases the pad in the old view first and the controller's release comes
  later, with the new view on screen: a hold remembers the view it took the press in and is dropped if that view is
  gone.
- `ui-map.md` gains the probability view's row 4 (a stock view, rule: values in stock's step views) and the drum
  expanded view's pads 21–24 (planned entries from 2026-10-31).

## Storage

| Track kind | Where | Bits | Encoding |
|---|---|---|---|
| Drums | the pattern's settings bytes: one byte per step at `+0x88 + step`, plus one bit per step from `+0x84..+0x87` | 9 | v = 2^L + mask for L = 2–8 (the all-zero masks unused, user 2026-11-07); 0 = none; 8 of the 10 free codes (1–3 and the empty cycles 4–64) hold the specials |
| Synth / MIDI | step bytes [2] and [3] | 16 | the same 9-bit code (one encoding for both); 7 bits spare (e.g. a special **and** a cycle later) |

- **A project mark** in CTPlay's saved block (payload offset 117, after PL19's `chord_pstrum` at 116; 1 B, saved,
  not linked): the first condition written in a project clears `+0x84..+0xA7` of all 32 drum patterns and bytes
  [2]–[3] of every note step, then sets the mark. An unmarked project reads every condition as none (third-party
  packs carry junk there; upstream builds wrote [2]–[3]).
- **Writes:** drums raw (not in the drum editor's step store); note tracks raw, except the editor's selected step,
  which goes through the step store (`0x080354FA` on parameter 0, commit `0x080353C0`), as upstream's SC39.
- **Keeping conditions with their steps** (hooks; the builder check confirmed each one is needed): note tracks: the
  step fill `0x0803D230` also zeroes [2]–[3] (Clear step / pattern; stock keeps them); everything else already copies
  or keeps whole steps. Drums (stock leaves the bytes in place through every edit): Duplicate `0x0803E2AA` at its
  "target is the shown pattern" branch `0x0803E2DC` (always when stopped; also while playing with the target shown;
  the source may be another drum's pattern; stock leaves the target's old bytes: copy the source's), Clear step `0x0803E18A` / pattern `0x0803E3B0` (zero them), copy 1-16 →
  17-32 `0x0803E93A`, paste step `0x0803DFAE`, Mutate `0x0803E6F0` (move them with the hits). The plan may fall
  back to "a drum condition on a step with no hit is dropped" where a hook proves costly; the guide says so.
- **A step's condition goes when its last hit or note goes** (*my call*, as stock: a new drum hit always starts at
  probability always): drum step toggle off (`0x0804EC3E`, and the other remove path `0x080500B2`), Clear step; a note
  step whose last unit is removed (step entry's removal in the Note view's pad press `0x0804AB5A`, PL18's
  `note_pad_press`; the drum remove path `0x080500B2` is upstream's reading, unchecked). So a hit added later never inherits an
  old condition.
- **The note editor's selected step:** stock's refresh `0x0803DC62` mirrors it into the store about once a step; a raw
  write there must go through the store, or a probability press puts the store's old bytes back (confirmed).
- CTPlay's own writers (Pattern tools Write, Euclid, Melody, the drum tools) **clear** the conditions of the steps
  they rewrite. *My call:* a generated pattern starts clean.
- **Not taken: bits inside the drum step** (upstream `lanex`, SC49.2 / Beta 3.47, 2026-10-29). Upstream patches stock
  so the probability byte's bits 3–7 and the microstep byte's bits 6–7 are free (the hit test compares `probability
  << 29`, the view draws `& 7`, the setter and every fixed-value writer keep the high bits): a 7-bit code a step that
  travels with the step through every copy, with no storage hooks. 7 bits hold the 35 A:B ratios, their NOTs and the
  specials, but not the pass grid's any-mix (L = 8 alone has 254 masks), and about ten patched stock writers plus the
  Components validator's "invalid probability" (unchecked) are risks. Kept as the fallback if the storage hooks above
  prove costly.

## Where it hooks (the plan confirms)

- `0x0802CD42` (mid): count a pass, and start over after a waited hand change. `seq_start`, `0x0802C240` (immediate
  switch) and `session_applied`: start over. `seq_tick`'s entry: latch the scene chain's waiting flag.
- `0x0804A6C0` (mid, tick 0 of a step): evaluate the step's condition once, keep PRE's state, store "silenced" per
  player.
- `0x08040D8A` (notes), `0x0804AA18` and `0x080411F6` (drums, 6-byte mid hooks so the handler sets the flags): apply
  it at stock's probability test. Forcing a fail there sounds exactly as a failed roll (confirmed; both drum sites are
  needed, or the drum switches to its flip sample). PL19 hooks
  `seq_play_step` and calls `seq_note_on`: different instructions; the plan checks that the hooks stack.
- The probability views' pad handlers (`0x0804D0BC` notes, `0x0804F262` drums): row 4 and Shift + row 4.
- Row-4 LEDs: the `led_task` hook draws pads 25–32 while a probability view is the bottom view.
- The storage hooks above.
- FILL: the drum expanded view's pad press / release (`0x0804ED50` / `0x0804ED68`, class `0x0805AD44`: pads < 28 are
  ignored by stock) and its LEDs (`0x08047592` / `0x0804ED84`) for pads 21–24.
- LAST: the waiting flags (chain store parameter 8 + t; the scene chain's parameter 1), read at tick 0.
- The probability views' release: an entry hook on `0x080435F0`.

## Budget (rough)

Flash: 3–5 KB. RAM: 128 B counters + per-player state (silenced flag, PRE state, about 16 B) + FILL state. Saved: 1 B
(the mark). Stack: small handlers on the UI and Main tasks.

## Tests (outline; the plan details them)

- Emulation through the real routes: the probability view's pads (row 4, Shift + row 4, the ½ s hold), playback over
  several passes with the real tick, chains, scene changes, Play / Stop, hand-picked patterns; each condition's
  result per pass; probability and condition together; drums and notes; stock's edits keeping, clearing and moving
  conditions; the project mark and an unmarked project with junk in the bytes; semaphore counts as `emu_sc19_3.py`.
- The storage investigation's "Not confirmed" items 1–8 come first. Item 9 (playback timing on the device) may need a
  diagnostic build before PL20, as upstream's SEQWD.
- Device test (`firmware/PL20/TEST.md`): a new empty project; drums and Synth 1; a loop, a 2-pattern chain, a
  hand switch; FILL both ways; save / load.

## My calls (for the user to check)

1. One 9-bit code for both track kinds (note tracks keep 7 spare bits).
2. ~~Unticking every pass leaves a cycle that plays every pass~~ Changed by the user 2026-11-07 (plan review): the
   9-bit code cannot hold both an empty and a full cycle at every length plus the 8 specials; unticking the last
   ticked pass clears the condition, and a held length starts at pass 1 ticked. Holding the length pad again clears.
3. CTPlay's pattern writers clear the conditions of the steps they rewrite.
4. FILL armed by a tap lasts the drum's next whole pass.
5. Counters live in RAM only (they start over at Play anyway).
6. Note tracks keep the drums' rule (a special **or** a pass cycle, never both), so both track kinds edit the same
   way; their 7 spare bits stay for later.
7. PRE's state after a start-over: no conditional step yet = "did not play" (PRE silent, NOT PRE plays).
8. A step's condition goes when its last hit or note goes (builder check, 2026-11-01).
9. A scene chain advancing by itself keeps counting; a pass cut short by a scene still counts.
10. Shift + Play (continue) keeps the counts.

## Open points, settled 2026-10-31

1. FILL's place: per drum on the drum expanded view's pads 21–24 (the user; "Settled 2026-10-31" above).
2. LAST: while a hand change waits to take over (the user; revised 2026-11-01 after the builder check).
3. PRE: linked randomness, the look-back above (the user).
4. Row 4 with a special: all 8 pads dim in its colour (the user).
5. A scene change while playing: starts the counts over (the user's counting rule).
6. Note tracks, a special and a cycle together: no (my call 6).

## Left to the builder

Hook mechanics and names; the counters' memory region; the LED codes (picked and confirmed on the device); the exact
hold timing; the test file layout.
