# PL20 — device test plan (trig conditions)

**What it is:** PL19 with **trig conditions** (spec `slim/docs/specs/2026-10-28-trig-conditions-design.md`): a step
can play only on some passes of its pattern. Drums and synth / MIDI tracks alike.
- **The place:** row 4 of stock's **probability view** (Shift + Pattern Settings), which stock leaves dark and unused.
  Row 4 shows the condition of the step that row 3 shows. Rows 1–3 stay stock's.
- **Plain row 4 = the pass grid** (pads 25–32 = passes 1–8, cyan). **Hold** a pad about a second: a cycle of that many
  passes, pass 1 ticked. **Tap** a pad: ticks or unticks that pass (bright = it plays on that pass). Unticking the last
  ticked pass clears the condition. Holding the length's pad again clears it too.
- **Shift + row 4 = the specials:** FIRST, NOT FIRST (green), FILL, NOT FILL (orange, drums only), PRE, NOT PRE
  (violet), LAST, NOT LAST (yellow). The lit one again clears it. With a special set, plain row 4 shows all 8 pads dim
  in its colour.
- **FILL** per drum on the drum expanded view (Drum N, then Note): **pads 21–24 = FILL for drums 1–4**. Hold = fill
  while held. Tap (while playing) = fill the drum's next whole pass. Stop ends it.
- **Counting:** each pattern of each track counts its own passes. The counts start over at Play (from stop), at a
  pattern picked by hand, a scene recalled, a project loaded. They go on while a chain advances by itself and after
  Shift + Play.
- **Stock's edits** keep a condition with its step: Duplicate, copy 1-16 → 17-32, paste and Mutate carry it; Clear and
  taking the step's last hit or note out clear it. CTPlay's Pattern tools Write clears the conditions of what it writes;
  its Undo brings them back.
- **Saved:** the conditions are in the pattern, saved with it. One new saved byte (the project's mark, not linked: the
  saved settings are 118 B now). An older project plays as before until you write its first condition.
- **Also new: Played strums release at once** (PL19's pattern strum, Played): each late note of a strum ends where the
  block chord would end, so a chord with one gate stops together instead of note after note.

With no condition set, everything plays as PL19 (checked in emulation). PL19 passed on the device
(`firmware/PL19/TEST.md`): this run checks what is new.

**Time:** about **2 hours** in all (an estimate: 182 rows at about 30 s each, the build and setup 15–20 min, one power
cycle a few minutes; PL19's 105 rows took about 45 min, so it may go faster). It splits into two sittings:
- **First sitting, about 1 hour:** Before you start (15–20 min), A. Counting (10 min), B. Row 4's gestures (13 min),
  C. The specials (14 min), D. FILL (10 min). Sections A–D use one project; nothing needs saving at the break.
- **Second sitting, about 1 hour:** E. Synth 1 (15 min), F. Start-overs (6 min), G. Stock's edits (13 min), H. Save,
  load, power cycle (12 min), I. Played strums release at once (4 min), J. Components (optional, 5 min).
- The natural break is after D. Each later section says how it starts.

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL20.toml`. The printed syx sha256 must equal
   `syx_sha256` in `slim/firmware/PL20/manifest.json` (`a6895113…`). Then `../.venv/bin/python -m slimbuild.uploader`
   (the uploader learns PL20).
1. **Stack headroom gate (SL00D):** Main and UI with at least 2 green pads (≥ 1.5 KB free). Hook stacks against PL19:
   **Main (`main_ms`) 432 B and the LED task 592 B: as PL19.** New, on Main: a step's tick 0 (`player_tick`) 160 B,
   the pass end (`track_advance`) 152 B, stock's three probability tests (`prob_note`, `prob_drum`,
   `prob_drum_first`) 152 B each; `seq_tick` 336 B (PL19 328 B). New, on the UI task: the probability views' pads
   (`prob_view_note`, `prob_view_drum`) 120 B, the container's pad release (`cont_release`) 128 B, the expanded view's
   press / release 120 B, stock's edits (Duplicate, Clear step / pattern, copy 1-16 → 17-32, a step's hit off, the
   flip removal) 120 B, paste 128 B, Mutate and the micro-step removal 152 B; `seq_place` 128 B (any task). Step entry
   (`step_add` 396 B, `note_pad_press` 316 B), a page pad press 476 B and release 444 B: as PL19. Stock's own calls are
   not counted.
2. **Back up the SD card**: the test writes patterns and saves a project. Use a pack you can lose. Way back: Scales +
   Preset + Note at power-on, send the stock `.syx` (or PL19).
3. Flash `slim/build/PL20/circuittracks-4486-PL20.syx` with `slim/build/ct_uploader.html`. Then close the uploader's
   tab (only one program can use the MIDI port; section H opens the link page).
4. **A new empty project** (in the Projects view, tap an empty slot) where a section says so. It starts with every
   CTPlay setting off and **no conditions**. Its patterns are empty, 16 steps, sync rate 1/16. Drum 1 is the kick.
   Tempo **120 BPM**: a beat is half a second; a 16-step pattern is **one bar, 2 seconds**. Step 5 is beat 2, step 9
   beat 3, step 13 beat 4.
5. **The click** (stock's metronome): hold Shift and look at Clear. **Green = the click only.** If it is not green,
   press Shift + Clear until it is. The click helps you find beats 1–4; a count-in would delay every Play by a bar.
   **Record quantise** as stock's default (hold Shift: Record bright). Nothing in this plan records.
6. **Synth 1 on a Poly patch** with a clear, **sustained** sound (an organ or a soft pad with a quick attack), for
   sections E, H and I.
7. **Synth 1's Note view** with the steps on rows 1–2 and the keys on rows 3–4 (if all four rows play notes, press
   Note until rows 1–2 show the steps). Your keyboard layout: **"the C pad" is pad 25**, the C at the left end of the
   bottom row; then **D pad 26, E pad 27, F pad 28, G pad 29**.
8. **Views used** (stock's, checked in emulation):
   - **Drum 1's step view:** press **Drum 1**. The steps on rows 1–2 (a hit is lit), the samples on rows 3–4. A tap on
     a step pad adds a hit or takes it out.
   - **The probability view:** **Shift + Pattern Settings** (from the track's step view or Note view). Rows 1–2 are the
     steps; a tap on a step pad **selects** it (it adds or takes out nothing). **Row 3** is stock's probability of the
     selected step: a bar of lit pads, all 8 lit = always (a new hit or note), 4 lit = 50 %. **Row 4** is CTPlay's.
   - **The drum expanded view:** press Drum 1, then **Note**. Rows 1–2 dark, **pads 29–32 play drums 1–4** (orange,
     yellow, violet, cyan). Note again goes back to the step view.
   - **Stock's Gate view** (Gate): hold a step pad; rows 3–4 are its gate bar, one pad a step (pad 17 = 1 step,
     pad 20 = 4 steps, pad 24 = 8 steps). Press a pad of the bar to set the gate.
   - **The Patterns view** (Patterns): a column per track, Synth 1 on the left; **Drum 1 is column 5: pad 5 =
     pattern 1, pad 13 = pattern 2.** A tap picks a pattern (playing: it takes over at the end of the current pass;
     stopped: at once). Hold one pattern and press another for a chain.
   - **Scenes** (Mixer): pads 17–32 are scenes 1–16. **Shift + a scene pad saves** every track's patterns into it; a
     tap recalls it (playing: it takes over at the end of Drum 1's pattern).
9. **Row 4, how to press:**
   - **A tap:** press and let go at once (well under half a second).
   - **A hold:** keep the pad down **about a second**. After half a second, **while you still hold it**, row 4 already
     shows what the hold will write. It is written when you let go.
   - **Shift** is read when you press the pad: Shift held at the press = a special.
   - Row 4 edits **the step row 3 shows**: stopped, the step you tapped last; with a step pad held, that step. **While
     playing, stock's selection follows the playing step**: rows 3 and 4 change with every step, and a row-4 press
     without a held step does nothing (stock's row 3 is the same). After every Stop, **tap the step pad again** before
     an edit.
   - **Check the follow state** the first time you play (step 4): rows 3 and 4 must change with every step. If row 4
     stays lit the whole time, stock's step views are not following the playing step (stock's Shift + Patterns
     toggle, which this plan uses in B19c–19e): **press Shift + Patterns once** and listen again.
10. **Colours on row 4:** passes **cyan** (bright = ticked, dim = in the cycle, not ticked, dark = past the cycle);
    FIRST / NOT FIRST **green**, FILL / NOT FILL **orange**, PRE / NOT PRE **violet**, LAST / NOT LAST **yellow**
    (bright = the step's special, dim = the others). FILL pads: **dim orange** off, **bright orange** on, **yellow**
    armed.
11. **Counting passes by ear:** pass 1 is the first bar after Play. Drum 1's kick on step 1 (beat 1) marks every bar.
    "Beat 3 in bars 2 and 4" means: the bar after Play has no kick on beat 3, the next one has, and so on. Listen to
    the number of bars a row says.
12. **The phantom-press check:** a slow press can make the Circuit see a press on the next pad too (the pad to the
    right). After each press that writes (a row-4 release, Clear, Duplicate, paste, a hit off), the plan checks that
    the next pad did not act: its LED as it was.

## Steps
### A. Counting on Drum 1
Start: **a new empty project** (Before you start, 4). Sequencer stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Press Drum 1 (its step view). Tap step pads 1 and 9 | Step pads 1 and 9 lit: two hits | |
| 1b | Press Play. Listen for two bars. Press Play (stop) | A kick on beats 1 and 3 of every bar | |
| 2 | Shift + Pattern Settings | Drum 1's probability view. Step pads 1 and 9 lit. **Row 4 dark** | |
| 2b | Tap step pad 9 | Row 3: **all 8 pads lit** (always). Row 4 dark: no condition | |
| 3 | **Hold** pad 26 about a second. Watch row 4 while you hold it, then let go | After about half a second, while you still hold it: **pad 25 bright cyan, pad 26 dim cyan.** The same after you let go: a cycle of 2 passes, pass 1 ticked. **Pad 27 stays dark** (phantom check) | |
| 3b | Tap pad 26 | **Pads 25 and 26 bright cyan**: every pass ticked. Pad 27 dark | |
| 3c | Tap pad 25 | **Pad 25 dim, pad 26 bright**: pass 2 of 2 ("2:2"). Pad 26 stays bright (phantom check) | |
| 4 | Press Play. Listen for **4 bars** | Beat 1 every bar. **Beat 3 only in bars 2 and 4.** Row 4 lights (25 dim, 26 bright) only for a moment each bar, while step 9 plays: the view follows the playing step. (If row 4 stays lit all the time, press Shift + Patterns once: Before you start, 9) | |
| 4b | Press Play (stop). Press Play again. Listen for 2 bars | **Bar 1 has no beat 3 again**, bar 2 has: Play from stop starts the count over | |
| 4c | Press Play (stop). Tap step pad 9 | Row 4: pad 25 dim, pad 26 bright | |
| 5 | **Hold** pad 26 (the cycle's length) about a second, let go | **Row 4 dark**: the condition is gone | |
| 5b | Press Play. Listen for 2 bars. Stop | Beat 3 in every bar again | |
| 6 | Tap step pad 9. **Hold** pad 28 about a second, let go | **Pad 25 bright cyan, pads 26–28 dim cyan, pads 29–32 dark** (1 of 4). Pad 29 dark (phantom check) | |
| 6b | Press Play. Listen for **8 bars**. Stop | **Beat 3 only in bars 1 and 5** | |
| 7 | Tap step pad 9. Tap pad 27 | **Pads 25 and 27 bright, pads 26 and 28 dim** (passes 1 and 3 of 4). Pad 28 stays dim (phantom check) | |
| 7b | Press Play. Listen for 8 bars. Stop | **Beat 3 in bars 1, 3, 5 and 7** | |
| 8 | Tap step pad 9. Tap pad 25 | **Only pad 27 bright**, pads 25, 26, 28 dim (pass 3 of 4) | |
| 8b | Press Play. Listen for 8 bars. Stop | **Beat 3 only in bars 3 and 7** | |
| 9 | Tap step pad 9. Tap pad 27 (the last ticked pass) | **Row 4 dark**: unticking the last pass clears the condition | |
| 9b | Press Play. Listen for 2 bars. Stop | Beat 3 in every bar | |

### B. Row 4's gestures and LEDs
Start: as section A left it. Drum 1: hits on steps 1 and 9, no condition. Its probability view, stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 10 | Tap step pad 9. Tap pad 25 | Row 4 stays dark: a tap with no condition does nothing | |
| 10b | **Hold** pad 25 about a second, let go | Row 4 stays dark (pass 1 held, no condition: nothing) | |
| 11 | **Hold** pad 28, let go | Pad 25 bright cyan, pads 26–28 dim (1 of 4). Pad 29 dark | |
| 11b | Tap pad 30 (past the cycle) | Nothing changes: pads 29–32 dark | |
| 11c | Tap pad 26, then tap pad 25 | **Only pad 26 bright** (pass 2 of 4), pads 25, 27, 28 dim | |
| 12 | **Hold** pad 30 about a second. Watch row 4 while you hold it | After half a second, while held: **pad 26 bright, pads 25 and 27–30 dim, pads 31–32 dark**. The same after you let go: 6 passes, pass 2 kept. Pad 31 dark (phantom check) | |
| 12b | Tap pad 29, then tap pad 26 | **Only pad 29 bright** (pass 5 of 6) | |
| 12c | **Hold** pad 27, let go | **Pad 25 bright, pads 26–27 dim**, pads 28–32 dark: 3 passes, and pass 5 did not fit, so pass 1 | |
| 13 | **Hold** pad 25 (pass 1), let go | **Row 4 dark**: pass 1 held clears | |
| 14 | Hold Shift (keep holding it) | Row 4: **pads 25–26 dim green, 27–28 dim orange, 29–30 dim violet, 31–32 dim yellow** | |
| 14b | Still holding Shift, tap pad 31 (LAST) | **Pad 31 bright yellow**, the other seven dim as before. Pad 32 stays dim yellow (phantom check) | |
| 14c | Let go of Shift | **All 8 pads dim yellow**: a special is set | |
| 15 | Tap pad 26 (no Shift) | Nothing changes: all 8 dim yellow (a tap does nothing on a special) | |
| 15b | Hold Shift. Tap pad 25 (FIRST). Look, then let go of Shift | With Shift: **pad 25 bright green, pad 26 dim green** (phantom check), **pad 31 dim yellow** (FIRST replaced LAST). Without Shift: **all 8 dim green** | |
| 16 | **Hold** pad 27 (no Shift), let go | **Pad 25 bright cyan, pads 26–27 dim cyan**: a cycle of 3 replaced FIRST | |
| 16b | Hold Shift. Tap pad 29 (PRE). Look, then let go of Shift | With Shift: **pad 29 bright violet**, the others dim. Without: **all 8 dim violet** (PRE replaced the cycle) | |
| 16c | Hold Shift. Tap pad 29 again. Let go of Shift | **Row 4 dark** (with Shift held: all dim, none bright): the lit special again clears | |
| 17 | **Shift at the press:** hold Shift, press pad 25 and keep it down, let go of Shift, then let go of pad 25 | **All 8 dim green**: FIRST was set (Shift was held when you pressed) | |
| 17b | Hold Shift. Tap pad 25. Let go of Shift | Row 4 dark (FIRST cleared) | |
| 18 | **An empty step:** tap step pad 3 (no hit). **Hold** pad 26, let go. Hold Shift, tap pad 25, let go of Shift | **Row 4 stays dark**, and **step pad 3 stays unlit**: no hit was made (stock's row 3 would make one; row 4 does not) | |
| 19 | **Playing, no step held:** press Play. Check that rows 3–4 change with every step (follow on; else Shift + Patterns once). Hold Shift. Tap pad 25 once right on beat 1 of a bar and once right on beat 3 of the same bar. Let go of Shift. Listen for 3 bars | **Beats 1 and 3 keep playing in every bar**: nothing was written (stock refuses a row press while its selection follows the playing step; a FIRST written on step 1 or 9 would silence it from the next bar) | |
| 19b | **Playing, a step held:** keep playing. Hold step pad 9; with another finger **hold** pad 26 about a second; let go of pad 26, then of step pad 9. Listen for 4 bars | **Beat 3 now every second bar** (1 of 2 on the held step 9). Beat 1 every bar | |
| 19c | **Playing, follow off:** press Shift + Patterns (stock: the step views stop following the playing step). Tap step pad 9. If rows 3–4 still change with every step, press Shift + Patterns once more and tap step pad 9 again | Rows 3 and 4 **stop changing** with the playing step: they show step 9 (row 4: pad 25 bright, 26 dim) | |
| 19d | **Hold** pad 26, let go. Listen for 2 bars | **Row 4 dark, and beat 3 in every bar again**: the selected step was written while playing | |
| 19e | Press Shift + Patterns again (follow on). Watch a bar, then press Play (stop) | Before the Stop, rows 3–4 change with the playing step again (if not, press Shift + Patterns once more) | |

### C. The specials
Start: as section B left it. Drum 1: hits on steps 1 and 9, no condition. Its probability view, stopped, follow on.

| # | Do | Expect | Result |
|---|---|---|---|
| 20 | Tap step pad 9. Hold Shift, tap pad 25 (FIRST) and look. Let go of Shift | With Shift held: **pad 25 bright green, pad 26 dim green** (phantom check). Without Shift: all 8 dim green | |
| 20b | Press Play. Listen for 3 bars. Stop | **Bar 1: beats 1 and 3. Bars 2 and 3: beat 1 only** | |
| 20c | Press Play. Listen for 2 bars. Stop | Again bar 1 has beat 3, bar 2 not (the count started over) | |
| 21 | Tap step pad 9. Hold Shift, tap pad 26 (NOT FIRST) and look. Let go of Shift | With Shift held: **pad 26 bright green**, pad 25 dim green, **pad 27 dim orange** (phantom check) | |
| 21b | Press Play. Listen for 3 bars. Stop | **Bar 1: beat 1 only. Bars 2 and 3: beats 1 and 3** | |
| 22 | **FIRST in a chain.** Tap step pad 9. Hold Shift, tap pad 25 (FIRST) and look. Let go of Shift | With Shift held: **pad 25 bright green, pad 26 dim green** (phantom check). Without Shift: all 8 dim green | |
| 22b | Press Patterns. Hold pad 5 (Drum 1's pattern 1), press pad 13 (its pattern 2), let go of both | A chain: Drum 1's patterns 1–2 | |
| 22c | Press Play. Listen for 6 bars. Stop | **Bar 1: beats 1 and 3. Bar 2: silent** (pattern 2 is empty). **Bar 3: beat 1 only. Bar 4 silent. Bar 5: beat 1 only. Bar 6 silent**: the chain advancing by itself keeps counting, so FIRST plays on the first time round only | |
| 22d | Tap pad 5 (pattern 1 alone; stopped, so at once) | The chain is pattern 1 only again | |
| 23 | **PRE.** Press Drum 1 (its step view). Tap step pad 5 | Step pads 1, 5 and 9 lit | |
| 23b | Shift + Pattern Settings. Tap step pad 5. Press pad 20 (row 3's 4th pad) | Row 3: **pads 17–20 lit, 21–24 dark**: step 5 at 50 %. Pad 21 stays dark (phantom check) | |
| 23c | Tap step pad 9. Hold Shift, tap pad 29 (PRE) and look. Let go of Shift | With Shift held: **pad 29 bright violet, pad 30 dim violet** (phantom check). Without Shift: all 8 dim violet | |
| 23d | Press Play. Listen for **8 bars**. Stop | Beat 1 every bar. **Beats 2 and 3 come and go together**: in each bar both or neither (step 9 plays only when step 5 played) | |
| 24 | Tap step pad 9. Hold Shift, tap pad 30 (NOT PRE) and look. Let go of Shift | With Shift held: **pad 30 bright violet**, pad 29 dim violet, **pad 31 dim yellow** (phantom check) | |
| 24b | Press Play. Listen for 8 bars. Stop | **In each bar exactly one of beats 2 and 3** | |
| 25 | Press Drum 1 (its step view). Tap step pad 5 (the hit goes). Tap step pad 13 | Step pads 1, 9 and 13 lit. Step pad 6 stays unlit (phantom check) | |
| 25b | Shift + Pattern Settings. Tap step pad 9. Hold Shift, tap pad 31 (LAST) and look; let go of Shift. Tap step pad 13. Hold Shift, tap pad 32 (NOT LAST) and look; let go of Shift | With Shift held on step 9: **pad 31 bright yellow, pad 32 dim yellow** (phantom check). With Shift held on step 13: **pad 32 bright yellow**, pad 31 dim | |
| 25c | Press Play. Listen for 2 bars | **Beats 1 and 4** every bar (NOT LAST plays, LAST does not) | |
| 26 | **LAST with a pick.** Press Patterns. On **beat 1 of a bar**, tap pad 13 (Drum 1's pattern 2). Listen | **That bar: beats 1 and 3, no beat 4** (a pick waits: LAST plays, NOT LAST not). **The next bars are silent**: pattern 2 took over | |
| 26b | Tap pad 5 (pattern 1) | After the silent bar: **beats 1 and 4** again (nothing waits) | |
| 26c | Press Play (stop) | | |
| 27 | **Save two scenes** (stopped, still in the Patterns view). Press Mixer. Hold Shift, tap pad 17, let go of Shift | Scene 1 saved: Drum 1 on pattern 1 | |
| 27b | Press Patterns. Tap pad 13. Press Mixer. Hold Shift, tap pad 18, let go of Shift | Scene 2 saved: Drum 1 on pattern 2 | |
| 27c | Tap pad 17 (scene 1; stopped, so at once) | Drum 1 on pattern 1 again | |
| 28 | **LAST with a scene.** Press Play (the Mixer stays). Listen for a bar | Beats 1 and 4 | |
| 28b | On **beat 1 of a bar**, tap pad 18 (scene 2). Listen | **That bar: beats 1 and 3, no beat 4. Then silent bars** (scene 2 took over at Drum 1's pattern end) | |
| 28c | Tap pad 17 (scene 1). Listen for 2 bars. Stop | After the silent bar: **beats 1 and 4** | |

### D. FILL
Start: as section C left it. Drum 1 on pattern 1: hits on steps 1, 9 (LAST) and 13 (NOT LAST). Stopped.
**Tap the FILL pad on beat 2** where a row says so (steps 5–8, no FILL step there): a tap is also a short hold, so a
FILL step that starts during it fills.

| # | Do | Expect | Result |
|---|---|---|---|
| 29 | Press Drum 1, then Shift + Pattern Settings. Tap step pad 9. Hold Shift, tap pad 27 (FILL), let go of Shift. Tap step pad 13. Hold Shift, tap pad 28 (NOT FILL) and look | With Shift held on step 13: **pad 28 bright orange**, pad 27 dim orange. Let go of Shift | |
| 29b | Press Note (the step view), then Note again | **The expanded view:** pads 29–32 the four drums. **Pads 21–24 dim orange** (FILL off). Every other pad dark | |
| 30 | Press Play. Listen for 2 bars | **Beats 1 and 4** (FILL off: step 9 silent, step 13 plays) | |
| 30b | **Hold** pad 21 for two bars, then let go | While held: **pad 21 bright orange; beats 1 and 3, no beat 4.** After you let go: pad 21 dim orange, beats 1 and 4 | |
| 31 | **Another drum's pad:** hold pad 22 for a bar, then let go | Pad 22 bright orange while held, **pad 21 stays dim**. Drum 1 unchanged: beats 1 and 4 (pad 22 is Drum 2's FILL) | |
| 32 | **Tap** pad 21 on **beat 2** of a bar | **Pad 21 yellow** (armed) for the rest of that bar. **The next bar: pad 21 bright orange, beats 1 and 3, no beat 4. Then dim orange**, beats 1 and 4 again: one whole bar of fill | |
| 32b | Tap pad 21 again on beat 2 of a later bar | Yellow, then the next bar fills, then dim orange: **one tap arms again** after a fill | |
| 33 | **Tap again disarms:** on beat 2 of a bar tap pad 21, and tap it again before beat 3 | Yellow, then **dim orange at once. The next bar: beats 1 and 4** (no fill) | |
| 34 | **Disarm during the fill:** tap pad 21 on beat 2. In the next bar (pad 21 bright orange), tap pad 21 on its beat 2 | **Dim orange at once. That bar: beats 1 and 4**, no beat 3: the fill ended at your tap | |
| 35 | **Stop while armed:** tap pad 21 on beat 2 (yellow). Before the bar ends, press Play (stop) | **Pad 21 dim orange at once** | |
| 35b | Press Play. Listen for 2 bars | Beats 1 and 4: **no fill** | |
| 35c | **Stop during a fill:** tap pad 21 on beat 2. In the next bar (bright orange) press Play (stop) | Pad 21 dim orange at once | |
| 35d | Press Play. Listen for 2 bars. Stop | Beats 1 and 4: no fill | |
| 36 | **Stopped:** tap pad 21. Then press Play and listen for 2 bars | Pad 21 bright orange while you touch it, then dim orange. **No fill**: beats 1 and 4 (a tap while stopped does nothing). Keep playing | |
| 37 | **A drum page covers the view:** Shift + Drum 1 | Drum 1's **Repeat page** opens over the expanded view: **pads 21–24 dark** | |
| 37b | Tap pad 21. Then hold it for a bar | Nothing: beats 1 and 4 go on. Pad 21 stays dark (the page's pad, a free one) | |
| 37c | Press Drum 1 (the page closes: the step view), then Note | The expanded view: pads 21–24 dim orange | |
| 38 | **Stop with a page open:** tap pad 21 on beat 2 (yellow). At once press Shift + Drum 1 (the Repeat page), let go of Shift, then press Play (stop) | The sequencer stops | |
| 38b | Press Drum 1, then Note | The expanded view: **pad 21 dim orange** (Stop disarmed it, though the page covered it) | |
| 38c | Press Play. Listen for 2 bars. Stop | Beats 1 and 4: no fill | |

**Break here if you like.** Sections A–D need nothing saved.

### E. Synth 1
Start: **a new empty project.** Synth 1 on its Poly patch (Before you start, 6). Set the project's scale to a **major
scale on C** (Scales), as in PL19. Sequencer stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 39 | Press Drum 1. Tap step pad 1 | A kick on beat 1 of each bar, to mark the bars | |
| 39b | Shift + Synth 1 | Synth 1's **Chords page**: pad 1 bright green (shape off), pads 2–8 dim green | |
| 39c | Press pad 2 (triad) | Pad 2 bright green | |
| 39d | Hold Shift, tap pad 32 (Keys). Let go of Shift. Press pad 2 | The Keys page: **pad 2 bright green** (chords in step entry). Pad 3 stays dim white (phantom check) | |
| 40 | Press Synth 1 (its Note view). Hold step pad 1. Press the C pad and let go of it. Let go of step pad 1 | **C E G together** while you hold step 1 (the step's preview). The D pad does not light up (phantom check) | |
| 40b | Hold step pad 2. Press the **F pad** (pad 28) and let go of it. Let go of step pad 2 | **F A C together.** The G pad does not light up (phantom check) | |
| 40c | Press Gate. Hold step pad 1. Press pad 20, let go of it. Let go of step pad 1. Do the same on step pad 2 | While you hold each step: **pads 17–20 lit**: both chords last 4 steps (a new step's gate is one step: a late strum note would be cut very short, section I). Press Note (back to the Note view) | |
| 41 | Press Play. Listen for 2 bars. Stop | Every bar: **the C chord on beat 1, the F chord a sixteenth later**, both ringing about half a second. The two chords overlap with 6 notes, more than a synth holds (about 4–5, Device limitations in the guide): a note of the C chord may stop when the F chord starts. That still passes: what counts is that both chords start, a sixteenth apart | |
| 42 | Shift + Pattern Settings (Synth 1's probability view). Tap step pad 1 | Row 3 all 8 lit. **Row 4 dark** | |
| 42b | **Hold** pad 26, let go | Pad 25 bright cyan, pad 26 dim cyan: step 1 on pass 1 of 2. Pad 27 dark | |
| 42c | Tap step pad 2. **Hold** pad 26, let go. Tap pad 26. Tap pad 25 | After the hold: 25 bright, 26 dim. After the taps: **pad 25 dim, pad 26 bright**: step 2 on pass 2 of 2 | |
| 42d | **Row 3 keeps the condition** (optional; step 2 still shown). Press pad 20 (row 3's 4th pad). Then press pad 24 | After pad 20: row 3 **pads 17–20 lit, 21–24 dark** (step 2 at 50 %); pad 21 stays dark (phantom check); **row 4 unchanged: pad 25 dim, pad 26 bright**. After pad 24: row 3 all 8 lit again (always), and row 4 still **pad 25 dim, pad 26 bright** (pad 25 not bright: phantom check) | |
| 43 | Press Play. Listen for 4 bars. Stop | **Bar 1: the C chord only. Bar 2: the F chord only. Bars 3 and 4 the same**: the chord alternates every pass | |
| 44 | **No FILL on a note track:** tap step pad 1. Hold Shift (keep holding it) | **Pads 25–26 dim green, pads 27–28 dark, 29–30 dim violet, 31–32 dim yellow** | |
| 44b | Still holding Shift, tap pad 27. Let go of Shift | Nothing: pads 27–28 stay dark with Shift; without Shift row 4 shows step 1's cycle again (25 bright, 26 dim) | |
| 45 | **A step with no notes:** tap step pad 3. **Hold** pad 26, let go. Hold Shift, tap pad 25, let go of Shift | Row 4 stays dark. Step 3 stays empty | |
| 46 | **Played.** Shift + Synth 1 (its Keys page, used last). Press pad 3 | Pad 3 bright white (played). Pad 4 stays dim white (phantom check) | |
| 46b | Hold Shift, tap pad 25 (Chords). Let go of Shift. Press pad 28 (slow) | Pad 28 bright white. Pad 31 bright white (rising) | |
| 47 | Press Play. Listen for 4 bars | **Bar 1: C, E, G strummed, all three**: step 2 is silent on this pass, so it does not cut the strum. **Bar 2: F, A, C strummed.** Keep it playing | |
| 47b | Shift + Pattern Settings. Hold step pad 2 and, with another finger, **hold** pad 26 about a second; let go of pad 26, then of step pad 2 | Step 2 has no condition now (it plays every pass) | |
| 47c | Listen for 4 bars | **In the bars with the C chord: C, E, then the F chord's strum: no G** (step 2 cuts step 1's strum, as in PL19). In the other bars: F, A, C. **Compare with 47: there the C bars had the G.** (A held C-chord note may also stop at the voice limit; what counts is that no G starts) | |
| 47d | Press Play (stop) | | |
| 48 | **Clear takes the condition.** Tap step pad 1 | Row 4: pad 25 bright, pad 26 dim (1 of 2) | |
| 48b | Press Note (the Note view). Hold Clear, press step pad 1, let go of both | Step 1's chord is gone. Hold step pad 1: nothing sounds. Let go. Hold step pad 2: F, A and C sound (phantom check: step 2 untouched) | |
| 48c | Hold step pad 1. Press the C pad and let go. Let go of step pad 1 | C E G back in step 1 | |
| 48d | Shift + Pattern Settings. Tap step pad 1 | **Row 4 dark**: the new chord has no condition (Clear took the old one) | |
| 49 | **The last note out takes the condition.** **Hold** pad 26, let go | Pad 25 bright, pad 26 dim | |
| 49b | Press Note. Hold step pad 1. Press the C pad and let go of it (PL18: the pad again takes the chord out). Let go of step pad 1 | The chord stops. Hold step pad 1 again: nothing. Let go. The D pad never lit (phantom check) | |
| 49c | Hold step pad 1. Press the C pad and let go. Let go of step pad 1. Shift + Pattern Settings. Tap step pad 1 | C E G back in step 1. **Row 4 dark**: no condition | |

### F. Start-overs
Start: **a new empty project.** Sequencer stopped. (A chain advancing by itself was checked in step 22c.)

| # | Do | Expect | Result |
|---|---|---|---|
| 50 | Press Drum 1. Tap step pads 1 and 9. Shift + Pattern Settings. Tap step pad 9. Hold Shift, tap pad 25 (FIRST) and look. Let go of Shift | With Shift held: **pad 25 bright green, pad 26 dim green** (phantom check). Without Shift: all 8 dim green | |
| 51 | **Play from stop.** Press Play. Listen for 3 bars | **Bar 1: beats 1 and 3. Then beat 1 only.** Keep it playing past bar 3 | |
| 51b | Press Play (stop). **Shift + Play** (stock: continue where it stopped). Listen for 2 bars | It goes on from where it stopped. **No beat 3**: the counts went on | |
| 52 | **A pick by hand.** Press Patterns. Tap pad 13 (Drum 1's pattern 2) | After this bar: **silent bars** (pattern 2) | |
| 52b | Tap pad 5 (pattern 1) | After the silent bar: **beats 1 and 3 in the first bar back**, then beat 1 only: a pattern picked by hand starts its track over | |
| 53 | **At once (Shift + a pattern pad).** Hold Shift, tap pad 13, let go of Shift | **Silence at once** (pattern 2, switched at once) | |
| 53b | On **beat 1 of a bar**, hold Shift, tap pad 5, let go of Shift | Pattern 1 at once: **beat 3 plays in that same bar**, then beat 1 only | |
| 53c | Press Play (stop) | | |
| 54 | **A scene.** Press Mixer. Hold Shift, tap pad 17, let go of Shift (scene 1: Drum 1 on pattern 1). Press Patterns, tap pad 13. Press Mixer, Shift + pad 18 (scene 2). Tap pad 17 | Scene 1 recalled (stopped: at once): Drum 1 on pattern 1 | |
| 54b | Press Play. Listen for 2 bars | Bar 1: beats 1 and 3. Bar 2: beat 1 only | |
| 54c | Tap pad 18 (scene 2) | After this bar: silent bars | |
| 54d | Tap pad 17 (scene 1). Listen for 2 bars after the silent bar. Stop | **The first bar back: beats 1 and 3**, then beat 1 only: a scene recalled by hand starts every track over | |

### G. Stock's edits
Start: as section F left it. Drum 1 on pattern 1 (scene 1): hits on steps 1 and 9, step 9 FIRST. Stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 55 | Press Drum 1 (its step view) | Step pads 1 and 9 lit | |
| 55b | **Clear step:** hold Clear, press step pad 9, let go of both | **Step pad 9 unlit**: the hit is gone. Step pad 10 stays unlit (phantom check) | |
| 55c | Tap step pad 9 (a new hit). Shift + Pattern Settings. Tap step pad 9 | **Row 4 dark**; with Shift held, all dim: the new hit has no condition | |
| 56 | **A hit off and on.** Hold Shift, tap pad 25 (FIRST) and look. Let go of Shift | With Shift held: **pad 25 bright green, pad 26 dim green** (phantom check). Without Shift: all 8 dim green | |
| 56b | Press Drum 1. Tap step pad 9 | Step pad 9 unlit (the hit is off). Step pad 10 unlit (phantom check) | |
| 56c | Tap step pad 9 again. Shift + Pattern Settings. Tap step pad 9 | **Row 4 dark**: the condition went with the hit | |
| 57 | **Duplicate.** Hold Shift, tap pad 25 (FIRST) and look. Let go of Shift | With Shift held: **pad 25 bright green, pad 26 dim green** (phantom check). Without Shift: all 8 dim green | |
| 57b | Press Patterns. Note pad 14's colour (Drum 2's pattern 2). Hold Duplicate, press pad 5 (Drum 1's pattern 1), press pad 13 (its pattern 2), let go of Duplicate | Stock copies pattern 1 into pattern 2. **Pad 14 as before** (phantom check) | |
| 57c | Tap pad 13 (pattern 2; stopped, at once). Press Drum 1 | Step pads 1 and 9 lit: the copy | |
| 57d | Shift + Pattern Settings. Tap step pad 9. Hold Shift | **Pad 25 bright green**: FIRST was copied with the step | |
| 58 | **Copy 1-16 → 17-32** (on pattern 2). Let go of Shift. Press Drum 1. Hold Duplicate, press 1-16/17-32, let go of both | Stock copies steps 1–16 to 17–32 | |
| 58b | Shift + Pattern Settings. Press 1-16/17-32 (rows 1–2 show steps 17–32). **Not checked in emulation:** if rows 1–2 stay on steps 1–16 here, press Drum 1 (its step view), press 1-16/17-32 there, check step pads 1 and 9 lit (steps 17 and 25), note "58b: no 17–32 in the probability view" in Results, then press 1-16/17-32 once more (steps 1–16) and skip 58c–58d | Step pads 1 and 9 lit: steps 17 and 25 hold the copied hits | |
| 58c | Tap step pad 9 (step 25). Hold Shift | **Pad 25 bright green**: step 25 is FIRST. Let go of Shift | |
| 58d | Tap step pad 1 (step 17). Hold Shift | All dim: step 17 has no condition (as step 1). Let go of Shift. Press 1-16/17-32 (back to steps 1–16) | |
| 59 | **Paste** (back on pattern 1). Press Patterns, tap pad 5. Press Drum 1. Hold Duplicate, press step pad 9, then step pad 11, let go of Duplicate | **Step pad 11 lit**: the hit was pasted. Step pad 12 stays unlit (phantom check) | |
| 59b | Shift + Pattern Settings. Tap step pad 11. Hold Shift | **Pad 25 bright green**: the paste carried FIRST. Let go of Shift | |
| 60 | **Mutate.** Press Drum 1. Shift + Duplicate (stock's Mutate). Look at both halves (1-16/17-32 shows steps 17–32, again goes back): stock's Mutate may move a hit into 17–32. If no hit moved, do it again | Three hits in all (steps 1, 9 and 11 before), at least one on another step | |
| 60b | Shift + Pattern Settings. Tap each hit's step pad in turn (on its half) and hold Shift on each. **Note which steps show FIRST** | **Exactly two of the three hits show FIRST** (pad 25 bright green with Shift), the third none: the conditions moved with the hits | |
| 60c | Tap step pads 9 and 11 if they are unlit now, holding Shift on each | No pad bright: an empty step keeps no condition | |
| 61 | **Write clears, Undo restores.** Shift + Drum 1 (its Repeat page). Hold Shift, tap pad 27 (Pattern tools), let go of Shift. Press pad 4 | Pattern tools: **pads 1, 5, 9 and 13 bright** (the preview). Pad 32 dim orange | |
| 61b | Press pad 32 twice, then let go | The pattern is written. Press Drum 1: **step pads 1, 5, 9 and 13 lit**, steps 17–32 empty | |
| 61c | Shift + Pattern Settings. Tap step pad 9, then 13, holding Shift on each | **No condition** on any of them (Write starts clean) | |
| 61d | Shift + Drum 1 (Pattern tools, used last). Press pad 31 (Undo, blue) | **Pad 32 (Write) stays steady dim orange**, not blinking: Write was not armed (phantom check) | |
| 61e | Press Drum 1 (both halves) | **The three hits of step 60 are back** where Mutate put them | |
| 61f | Shift + Pattern Settings. Tap the two steps noted in 60b, holding Shift on each | **Pad 25 bright green on both**: Undo brought the conditions back | |

### H. Save, load, power cycle
Start: **a new empty project**, in a slot you can save over. Sequencer stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 62 | Press Drum 1. Tap step pads 1 and 9. Shift + Pattern Settings. Tap step pad 9. Hold Shift, tap pad 25 (FIRST) and look. Let go of Shift | With Shift held: **pad 25 bright green, pad 26 dim green** (phantom check). Without Shift: all 8 dim green | |
| 62b | Press Synth 1 (its Note view). Hold step pad 1. Press the C pad and let go. Let go of step pad 1 | A single C (no chord shape in a new project) | |
| 62c | Shift + Pattern Settings. Tap step pad 1. **Hold** pad 26, let go. Tap pad 26. Tap pad 25 | After each: pad 27 stays dark (phantom check). At the end: **pad 25 dim, pad 26 bright**: step 1 on pass 2 of 2 | |
| 62d | Press Play. Listen for 4 bars. Stop | **Bar 1: kicks on beats 1 and 3, no C. Bar 2: kick on beat 1 and the C. Bar 3: kick on beat 1, no C. Bar 4: kick and C** | |
| 63 | Save the project (Save, then Save again) | It saves as stock does | |
| 63b | Load the same project (Projects view, tap its slot) | It loads | |
| 63c | Press Drum 1, Shift + Pattern Settings. Tap step pad 9. Hold Shift | **Pad 25 bright green** (FIRST kept). Let go of Shift | |
| 63d | Press Synth 1, Shift + Pattern Settings. Tap step pad 1 | **Pad 25 dim, pad 26 bright** (2 of 2 kept) | |
| 63e | Press Play. Listen for 4 bars. Stop | **As step 62d**: bar 1 has the beat-3 kick and no C, bar 2 the C. The conditions survived the load | |
| 64 | Power off and on. Load the project. Do 63c–63e again | The same | |
| 65 | **An older project** (optional): load a project made on PL19, an older CTPlay or the official firmware, ideally one with drums. **Do not save it** | It plays as before. In its probability views, **row 4 is dark on every step** | |
| 66 | **The link:** open `slim/pages/ctplay_link.html` **from the PL20 checkout** in Chrome, connect | "Connected: **PL20**, protocol 1, layout 1, **118 B, 18 fields**." | |
| 66b | Read | The rows as in PL19, the last one `pattern strum` at offset 116 (the new byte 117, the project's mark, is not linked) | |
| 66c | Close the page's tab | | |

### I. Played strums release at once
Start: **a new empty project.** Synth 1 on its Poly patch. The project's scale **major on C** (Scales). Sequencer
stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 67 | Shift + Synth 1 (the Chords page). Press pad 2 (triad), then pad 28 (slow) | Pad 2 bright green, pad 28 bright white, pad 31 bright white (rising) | |
| 67b | Hold Shift, tap pad 32 (Keys). Let go of Shift. Press pad 2, then pad 3 | Pad 2 bright green, **pad 3 bright white** (played). Pad 4 stays dim white (phantom check) | |
| 68 | Press Synth 1. Hold step pad 1. Press the C pad and let go. Let go of step pad 1 | C E G together (the preview). Step 1's chord has stock's gate for a new step: **one step** | |
| 68b | Press Play. Listen for 2 bars. Stop | **C, E, G strummed, and the chord stops almost at once:** C sounds for the step, E only briefly, and **G, which starts after the step's end, is a very short blip.** Nothing rings on (PL19 kept each note its full length from its own late start) | |
| 69 | Shift + Synth 1 (its Keys page, used last). Hold Shift, tap pad 25 (Chords), let go of Shift. Press pad 29 (medium) | The Chords page. **Pad 29 bright white**, pads 28 and 30 dim white. Pad 30 stays dim (phantom check) | |
| 69b | Press Play. Listen for 2 bars. Stop (the Chords page stays open) | A quicker strum, and **all three notes end together** at the end of the step | |
| 70 | On the Chords page, press pad 28 (slow) again. Press Synth 1 (the page closes). Press Gate. Hold step pad 1, press pad 24, let go of both | While you hold step 1: **pads 17–24 lit**: an 8-step gate (a second) | |
| 70b | Press Play. Listen for 2 bars. Stop | C, E, G strummed slowly, then **all three stop at the same moment**, about a second later (in PL19 they stopped one after another, low to high) | |

### J. Components (optional)
Start: the project of section H saved. Novation Components at hand.

| # | Do | Expect | Result |
|---|---|---|---|
| 71 | Close every MIDI tab. Components: download the project of section H from the device, then send it back to another slot | Components accepts it (its validator's strings name no byte the conditions use; not run) | |
| 71b | On the Circuit, load that slot. Do 63c–63e | The conditions are there and play as before | |

## Results

A: All tests passed  
B: All tests passed  
C: All tests passed  
D: All tests passed - Time 1h 1min  
E: All tests passed  
F: All tests passed  
G: All tests passed  
H: All tests passed, including 65  
I: All tests passed  
J: All tests passed - Time 1h 9min, 2h 10min total  