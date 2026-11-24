# PL17 — device test plan (Pattern tools for the drums)

**What it is:** PL16 with **Pattern tools** and **Pattern tools 2** for the four drum tracks (spec
`slim/docs/specs/2026-10-25-drums-design.md`, "Pattern tools for drums"):
- **The drum page list** (Shift held on a drum page): pad 25 Repeat (blue) and, new, **pad 27 Pattern tools** (orange,
  two pages, as on the synth tracks). ▲ ▼ go Repeat, Pattern tools, Pattern tools 2.
- **The pages** are the synth tracks' Pattern tools and Pattern tools 2, with the same pads, on each drum's own
  settings. Two pads differ:
  - **Pad 21 on Pattern tools = the roll** (where a synth has the gate): 1, 2 or 3 hits in each step, shown in stock's
    Gate view colours for 1/6, 3/6 and 6/6.
  - **Pad 28 on Pattern tools 2 = the accent:** off · first hit · on the beat · every 3rd hit, in the Melody page's
    accent colours. An accented hit is written at 127.
  - Pad 30 (dice notes) is dark: a drum has no notes.
- **Write** writes the drum's **shown pattern** (the one its step pads show) through the drum editor, so the step pads
  and stock's views show it at once and later stock edits keep it. **Undo** is per drum. A **draft** starts when the
  groove, a cycle, a combine, the thinning or an accent is on.
- **Saved:** the new settings per drum, in the second saved block (the saved settings are 115 B in all now; the
  second block holds 59 B of them). The CTCtrl link carries them, but not the dice seed.

With no drum Pattern tools used, every PL16 feature plays as before (checked in emulation). PL16 passed on the device
(`firmware/PL16/TEST.md`): this run checks what is new.

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL17.toml`. The printed syx sha256 must equal
   `syx_sha256` in `slim/firmware/PL17/manifest.json` (`1bd08ff9…`). Then `../.venv/bin/python -m slimbuild.uploader`
   (the uploader learns PL17).
1. **Stack headroom gate (SL00D):** Main and UI with at least 2 green pads (≥ 1.5 KB free). Hook stacks against PL16:
   the **LED task 576 B** (PL16 464 B: the link's copies of the 115 B payload); a page pad press 476 B (PL16 468 B). A
   page pad release 444 B (a drum Write 232 B of it, plus stock's store calls, uncounted), Main (`main_ms`) 416 B: the same as PL16.
2. **Back up the SD card**: the test writes patterns and saves projects. Use a pack you can lose. Way back: Scales +
   Preset + Note at power-on, send the stock `.syx` (or PL16).
3. Flash `slim/build/PL17/circuittracks-4486-PL17.syx` with `slim/build/ct_uploader.html`. Then close the uploader's
   tab (only one program can use the MIDI port; section H needs it).
4. **A new empty project** (in the Projects view, tap an empty slot) at the start of each section that says so. It
   starts with every CTPlay setting off. Each drum opens on its Repeat page. On a drum's Pattern tools: no hits, Euclid,
   one hit a step, velocity medium, no cycle; on Pattern tools 2: no second rhythm, no combine, no thinning, no accent.
   Its drum patterns are empty, 16 steps. Drum 1 is the kick. Tempo 120 BPM: one beat = half a second, one bar = two
   seconds.
5. **The click** (stock's metronome): hold Shift and look at Clear. **Green = the click only.** If it is not green,
   press Shift + Clear until it is. A count-in would delay every Play by a bar.
6. **Stock's fixed velocity off** (Shift + Velocity), as in PL16's run. It is a Setup setting: it stays as set.
7. Colours: bright = selected, dim = not selected, dark = nothing there. **Pad 21 (the roll)** uses stock's Gate view
   colours: the 1/6 colour = one hit, 3/6 = two hits, 6/6 = three hits. To see them once (optional): make a new empty
   project, press Shift + Synth 1 (it opens on the Chords page in a new project), then ▼ (the Arp page). Its gate pad,
   pad 21, shows the 3/6 colour; each press goes one sixth down (2/6, 1/6, then 6/6). Section A starts with another
   new empty project, so this leaves nothing behind.
8. **Rows 1–2 on Pattern tools show the rhythm Write will write**, not which pad you pressed and not what the pattern
   holds now. To see the pattern, press the drum's button (the page closes) and look at the step pads.

## Steps
### A. The drum page list and paging
Start: **a new empty project.** Sequencer stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Press Synth 1. Then Shift + Drum 1 | Drum 1's **Repeat page**: pads 1–4 dim blue, 5–8 dim magenta, pad 9 bright white, pads 29–32 in the drum colours | |
| 1b | Look at ▲ and ▼ | **▼ orange** (Pattern tools comes next). ▲ dark | |
| 2 | Hold Shift (keep holding it) | The drum page list: **pad 25 bright blue, pad 27 dim orange**. Every other pad dark | |
| 2b | Still holding Shift, tap pad 27. Release Shift | **Pattern tools**: pads 1–16 dim orange (no hits). Pads 17–20 dim white. **Pad 21 in the 1/6 colour** (one hit a step). Pads 22 and 24 dim magenta, pad 23 bright magenta (medium). Pads 25–28 dim cyan. Pad 29 dim white. Pads 30, 31 and 32 dark | |
| 2c | Look at ▲ and ▼ | ▼ orange (Pattern tools 2), ▲ blue (Repeat) | |
| 3 | Hold Shift, tap pad 27 again. Release Shift | **Pattern tools 2**: pads 1–19 dim white, pads 20–24 dim violet, pads 25–27 dim cyan, **pad 28 dim yellow** (the accent, off). Pad 29 dim white. Pads 30, 31 and 32 dark | |
| 3b | Look at ▲ and ▼ | ▼ dark, ▲ orange | |
| 3c | Hold Shift and look at the page list. Release Shift | Pad 25 dim blue, **pad 27 bright orange** | |
| 4 | Press ▲ | Pattern tools (pad 21 in the 1/6 colour) | |
| 4b | Press ▲ | The Repeat page. ▲ dark | |
| 4c | Press ▼, then ▼ again | Pattern tools, then Pattern tools 2 | |
| 4d | Press ▼ | Nothing changes | |
| 5 | Press Note. Then Shift + Drum 1 | The page closes (stock's expanded drum view). Then Drum 1 opens on **Pattern tools 2**, the page it used last | |
| 5b | Hold Shift, tap pad 25, release Shift. Then hold Shift, tap pad 27, release Shift | The Repeat page, then **Pattern tools 2** (pad 27 opens the page of it used last) | |
| 6 | Shift + Drum 2 | Drum 2 is selected and its **Repeat page** opens: each drum keeps its own page | |
| 6b | Shift + Drum 1 | Drum 1's Pattern tools 2 | |
| 7 | Press ▲ (Pattern tools). Tap pad 30 | Nothing changes: pad 30 stays dark (a drum has no notes) | |

### B. A Write on Drum 1, the views, a stock edit, Undo
Start: the project of section A, Drum 1 on Pattern tools, sequencer stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 8 | Press pad 4 (4 hits) | **Pads 1, 5, 9 and 13 bright orange**, the other pads of rows 1–2 dim. Pad 32 dim orange (Write is ready) | |
| 8b | Press pad 32 once | Pad 32 **blinks** orange. Nothing plays | |
| 8c | Press pad 32 again, then let go | Pad 32 dim orange and steady (no draft: plain Euclid). **Pad 31 blue** (an Undo) | |
| 9 | Press Play. Listen for two bars. Press Play again (stop) | **The kick on every beat**: four hits a bar | |
| 10 | Press Drum 1 | The page closes: stock's Drum 1 view. **Step pads 1, 5, 9 and 13 lit as hits**, the others as empty steps | |
| 11 | **A stock edit:** tap step pad 3 | Step 3 becomes a hit. **Steps 1, 5, 9 and 13 stay hits** | |
| 12 | Press Velocity (stock's Velocity view). Hold step pad 1 and look at the bottom two rows. (Do not tap the bottom rows: they set the velocity) | **Step 1 shows velocity 96** (medium, the Write's): not the full bar. Write down how many pads light | 12 |
| 12b | Hold step pad 3 | Step 3 shows **how hard you tapped it** in step 11 (fixed velocity is off), so it may differ from step 1. That is not a failure: write down what it shows | 12 |
| 13 | Press Gate (on a drum, stock's micro step view: from our emulation notes, not confirmed). Hold step pad 1, then step pad 3. **If Gate shows something else, write down what it shows and go on: this check is optional** | **The same for both:** one micro step lit, the first | |
| 14 | Press Pattern Settings twice (stock's Probability view). Hold step pad 1, then step pad 3 | **The same for both** (always plays: stock's default) | |
| 15 | Shift + Drum 1 | Pattern tools. Pad 31 blue | |
| 15b | Press pad 31 (Undo), then let go | Pads 1, 5, 9 and 13 stay bright: they show the rhythm, not the pattern | |
| 15c | Press Drum 1 | **No step lit.** Undo put back the whole pattern from before the Write, so **your step 3 went too** | |
| 15d | Shift + Drum 1. Press pad 31 again. Press Drum 1 | **Steps 1, 3, 5, 9 and 13 lit**: Undo again brought back the Write and your step 3 | |

### C. Roll, accent, second rhythm (by ear)
Start: **a new empty project.** Shift + Drum 1 (Repeat), ▼ (Pattern tools). Press pad 4: pads 1, 5, 9, 13 bright.
Press Play: you hear only the click.

| # | Do | Expect | Result |
|---|---|---|---|
| 16 | Press pad 21 | Pad 21 in the **3/6 colour**: two hits a step | |
| 16b | Press pad 32 twice, then let go | At once: **a double kick on every beat** (two quick hits) | |
| 16c | Press pad 21 | Pad 21 in the **6/6 colour**: three hits a step | |
| 16d | Press pad 32 twice, then let go | At once: **three quick hits on every beat** (a short roll) | |
| 17 | Stop (Play). Press Drum 1, then Gate (the micro step view, as in step 13; if Gate showed something else there, skip this step). Hold step pad 1 | **Three micro steps lit: the 1st, 3rd and 5th** | |
| 17b | Shift + Drum 1 (Pattern tools). Press pad 21 | Pad 21 in the 1/6 colour: one hit a step | |
| 18 | Press pad 8 (8 hits) | Pads 1, 3, 5, 7, 9, 11, 13 and 15 bright | |
| 18b | Press ▼ (Pattern tools 2). Press pad 28 | Pad 28 bright yellow (accent on the first hit) | |
| 18c | Press pad 28 | Pad 28 white (accent on the beat) | |
| 18d | Press pad 32 twice, then let go. Press Play | **Pad 32 bright orange, steady**: a draft (the accent is a new setting). The kick on every second step; **the four on the beat (steps 1, 5, 9, 13) louder** | |
| 18e | Press pad 28, then let go | Pad 28 magenta (every 3rd hit). At once, without Write: **steps 1, 7 and 13 louder** | |
| 18f | Press pad 28 | Pad 28 dim yellow (off). At once: all eight hits equally loud | |
| 19 | Press pad 3 (second rhythm: 3 hits) | **Pads 1, 7 and 12 bright white** (the second rhythm's preview). The loop sounds the same (combine is off) | |
| 19b | Press pad 24 (combine accent) | Pad 24 bright violet. At once: **steps 1 and 7 louder** (where both rhythms hit) | |
| 19c | Press ▲ (Pattern tools) | Still pads 1, 3, 5, 7, 9, 11, 13 and 15 bright: the accent does not change the hits | |
| 20 | Press pad 31 (Undo) | **Pad 32 dim orange: the draft ended.** At once: **three quick hits on every beat** again (the pattern from before the draft's first Write, step 16d) | |
| 20b | Stop (Play) | | |

### D. A draft while playing (groove)
Start: **a new empty project.** Shift + Drum 1 (Repeat), ▼ (Pattern tools). Press Play: you hear only the click.

| # | Do | Expect | Result |
|---|---|---|---|
| 21 | Press pad 4 | Pads 1, 5, 9 and 13 bright | |
| 21b | Press pad 20 (groove) | Pad 20 bright white. **Pads 1, 9, 13 and 16 bright** (4 hits of the groove, in a new project) | |
| 21c | Press pad 32 twice, then let go | **Pad 32 bright orange, steady** (a draft: the groove is a new setting). The kick plays steps 1, 9, 13 and 16 | |
| 22 | Press pad 7 (7 hits), then let go | Pads 1, 5, 8, 9, 12, 13 and 16 bright. **The loop plays them at once**, without Write | |
| 22b | Press pad 21 (roll: two hits) | At once: each kick becomes a double hit | |
| 22c | Press pad 29 (dice rhythm) | The preview shows another rhythm of 7 hits; the loop plays it at once | |
| 22d | Press pad 31 (Undo) | **The loop is empty again** (the pattern from before the first Write). Pad 32 dim orange: the draft ended. Pad 31 stays blue | |
| 22e | Press pad 5 | The preview changes. **The loop stays empty**: no draft, nothing is written | |
| 22f | Press pad 31 again | The last draft's pattern comes back: 7 double kicks. Pad 32 stays dim orange | |
| 23 | Press pad 32 twice, then let go | Pad 32 bright orange (a new draft). The loop plays the 5 hits of the preview, doubled | |
| 23b | Press Note (the page closes). Then Shift + Drum 1 | Pattern tools. **Pad 32 dim orange**: closing the page ended the draft | |
| 23c | Press pad 6 | The preview changes. The loop does not change | |
| 23d | Stop (Play) | | |

### E. Shift + Patterns: Write goes to the shown pattern
Start: **a new empty project.** Sequencer stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 24 | Press Drum 1 (its step view). Tap step pad 1 | Step 1 lit: a kick on step 1 of pattern 1 | |
| 24b | In stock's Patterns view, chain Drum 1's patterns 1 and 2 (hold 1, press 2). Press Play | **One kick every second bar** (pattern 1's; pattern 2 is empty) | |
| 24c | Press Drum 1. Watch step pad 1 for a few bars | Step pad 1 lit in one bar, dark in the next: the step view follows the chain. (If it stays lit, follow is off: press Shift + Patterns once and watch again) | |
| 24d | During a bar where step pad 1 is dark (pattern 2), press Shift + Patterns | From now on **step pad 1 stays dark**: the step view stays on pattern 2 while the chain goes on | |
| 24e | Shift + Drum 1 (Repeat), ▼ (Pattern tools). Press pad 4. **Right after you hear the single kick** (pattern 1 is playing), press pad 32 twice and let go | **Pattern 1 keeps its single kick, and pattern 2 now has four kicks**: one bar a single kick, the next four kicks. Write wrote the pattern the step pads show, not the one that was playing | |
| 24f | Press Drum 1 | Steps 1, 5, 9 and 13 lit (pattern 2, still the one shown) | |
| 24g | Press Shift + Patterns (follow on again). Watch a few bars | The step pads follow the chain: step 1 alone in one bar, steps 1, 5, 9 and 13 in the next | |
| 24h | Stop (Play) | | |

### F. A Write while recording, with a latched drum
Start: **a new empty project.** The click on (Before you start, step 5).

| # | Do | Expect | Result |
|---|---|---|---|
| 25 | Shift + Drum 1 (Repeat). Press pad 3 (1/16), then pad 16 (latch) | Pads 3 and 16 bright | |
| 25b | Press Record, then Play. Tap pad 29 | Drum 1 repeats at 1/16, latched, and records. Pad 29 pulses white | |
| 26 | Shift + Drum 2 | Drum 2's Repeat page. Drum 1 keeps repeating | |
| 26b | Press ▼ (Pattern tools). Press pad 4 | Pads 1, 5, 9 and 13 bright. Drum 1 keeps repeating | |
| 26c | Press pad 32 twice, then let go | **Drum 2 plays steps 1, 5, 9 and 13** from now on. **Drum 1 keeps repeating evenly**: no hit lost or doubled when you let go of pad 32 | |
| 26d | Tap pad 29 (dice rhythm), then pad 30 (dice notes: dark on a drum, it does nothing). On the Repeat page these two pads are drum 1's and drum 2's: here they must not reach the repeat | **Drum 1 keeps repeating, drum 2 does not start repeating.** Pad 30 stays dark. Pad 29 moved the preview's hits. **Drum 2's loop does not change** (no draft) | |
| 27 | Press ▲ (drum 2's Repeat page). Tap pad 29 (on every drum's Repeat page, pads 29–32 are drums 1–4) | **Pad 29 stops pulsing**: drum 1's latched repeat is off. You still hear drum 1 on every step: that is its recorded pattern (step 27c), which the sequencer plays now. Not a failure | |
| 27b | Press Play (stop). Press Record (off) | | |
| 27c | Press Drum 1 | **All 16 step pads lit**: drum 1 recorded a hit on every step (it repeated for more than a bar) | |
| 27d | Press Drum 2 | **Steps 1, 5, 9 and 13 lit**, no others | |

### G. Save, load, power cycle
Start: **a new empty project.**

| # | Do | Expect | Result |
|---|---|---|---|
| 28 | Shift + Drum 1 (Repeat), ▼ (Pattern tools) | Pattern tools with the defaults, as in step 2b: pads 1–16 dim orange, pad 21 in the 1/6 colour, pad 23 bright magenta, pads 25–28 dim cyan, pad 32 dark | |
| 28b | Press pad 2 (2 hits) | **Pads 1 and 9 bright.** Pad 32 dim orange | |
| 28c | Press pad 26 (cycle of 5 steps) | Pad 26 bright cyan. **Pads 1, 4, 6, 9, 11, 14 and 16 bright** (2 hits in every 5 steps) | |
| 28d | Press pad 18 (one step later) | **Pads 2, 5, 7, 10, 12 and 15 bright** | |
| 28e | Press pad 21 | Pad 21 in the 3/6 colour (two hits a step). Pads 1–16 do not change | |
| 28f | Press pad 24 (hard) | Pad 24 bright magenta, pad 23 dim | |
| 28g | Press ▼ (Pattern tools 2) | Pattern tools 2 with the defaults, as in step 3: pads 1–19 dim white, 20–24 dim violet, 25–27 dim cyan, pad 28 dim yellow. **Pad 32 dim orange** (there are hits now) | |
| 28h | Press pad 3 (second rhythm: 3 hits) | **Pads 1, 7 and 12 bright white** | |
| 28i | Press pad 24 (combine accent) | Pad 24 bright violet | |
| 28j | Press pad 26 (thinning 1 in 3) | Pad 26 bright cyan | |
| 28k | Press pad 28 | Pad 28 bright yellow (accent on the first hit) | |
| 28l | Press pad 28 | Pad 28 white (on the beat) | |
| 28m | Press pad 28 | Pad 28 magenta (every 3rd hit) | |
| 28n | Press ▲ (Pattern tools) | **Pads 2, 5, 10, 12 and 15 bright**: the thinning took out step 7 | |
| 28o | Press ▼ (Pattern tools 2). Press pad 32 twice, then let go | Pad 32 bright orange (a draft) | |
| 28p | Press Play for two bars. Stop | Drum 1 plays 5 double hits a bar, all hard. Remember how it sounds | |
| 29 | Shift + Drum 3 (Repeat), ▼ (Pattern tools). Press pad 7, then pad 20 | Pads 1, 5, 8, 9, 12, 13 and 16 bright. Pad 20 bright white (groove) | |
| 30 | Save the project (Save, then Save again) | It saves as stock does | |
| 31 | Load the same project again (Projects view, tap its slot) | It loads | |
| 31b | Shift + Drum 1 | **Pattern tools 2** (saved): pads 1, 7 and 12 bright white, pad 24 bright violet, pad 26 bright cyan, pad 28 magenta. **Pad 31 dark** (Undo is not saved). **Pad 32 dim orange** (a draft is not saved) | |
| 31c | Press ▲ | Pattern tools: **pads 2, 5, 10, 12 and 15 bright**. Pad 21 in the 3/6 colour, pad 24 bright magenta, pad 26 bright cyan | |
| 31d | Shift + Drum 3 | Pattern tools: pads 1, 5, 8, 9, 12, 13 and 16 bright, pad 20 bright white | |
| 31e | Shift + Drum 2 | The Repeat page (drum 2 never left it) | |
| 31f | Press Play for two bars. Stop | Drum 1 plays as in step 28p | |
| 32 | Power off and on. Load the project. Do 31b–31f again | The same | |

### H. CTCtrl and the link
Start: the project of section G loaded. Sequencer stopped. Shift + Drum 2 (Repeat), ▼ (Pattern tools).

| # | Do | Expect | Result |
|---|---|---|---|
| 33 | Open `slim/pages/ctplay_link.html`, connect | "Connected: PL17, protocol 1, layout 1, **115 B, 16 fields**." | |
| 33b | Read | Three new rows. **`drum euclid`**, offset 87: `42 24 20 00 A7 00 20 00`. **`drum rhythm`**, offset 95: `A3 40 02 00 00 00 00 00 00 00 00 00`. **`drum accent`**, offset 107: `03 00 00 00`. No row for the drums' seeds or pages | |
| 33c | Write offset 89, bytes `24` (drum 2: 4 hits, medium) | One `state` line. **At once** on the Circuit: pads 1, 5, 9 and 13 bright orange, pad 32 dim orange | |
| 33d | Write offset 90, bytes `40` (drum 2: three hits a step) | Pad 21 in the 6/6 colour | |
| 33e | **A refused write.** Write offset 90, bytes `60` (roll value 3: no pad makes it) | One `state` line, unchanged: the write is refused. Pad 21 stays in the 6/6 colour | |
| 33f | Write offset 108, bytes `02` (drum 2: accent on the beat). Press ▼ | Pattern tools 2: **pad 28 white** | |
| 33g | Write offset 108, bytes `04` | Refused the same way. Pad 28 stays white | |
| 33h | Write offset 111, bytes `05` (drum 1's dice seed: not linked) | Refused the same way | |
| 34 | **A link write ends that drum's draft.** Press ▲ (Pattern tools). Press pad 20 (groove). Press pad 32 twice, then let go | Pad 32 bright orange: a draft | |
| 34b | Write offset 89, bytes `A7` (drum 2: 7 hits, groove) | **Pad 32 dim orange**: the draft ended. Pads 1, 5, 8, 9, 12, 13 and 16 bright | |
| 34c | Press Play for a bar. Stop | Drum 2 plays a short roll (three hits) on steps 1, 9, 13 and 16: the Write of step 34. The link write did not re-write the pattern with 7 hits | |
| 35 | Close the page. Open CTCtrl (1.2.4), connect. Select Drum 1, the Repeat tab | It connects; the Repeat tab shows no rate, as struck, latch off, unquantized repeats off. No error. (CTCtrl 1.2.4 has no tab for the drums' Pattern tools yet) | |

## Results
2026-10-28, PL17 (`1bd08ff9…`): **passed.** Every section A–H all green.
- **Answers the plan asked for:**
  - Steps 12 and 12b: 12 pads lit for step 1 (the Write's velocity 96) and 12 for step 3 (the tap in step 11).
  - Step 13: Gate on a drum is stock's micro step view, as our emulation notes said: one micro step lit, the first,
    for both steps.
- **Plan fixes during the run:** steps 26d and 27 reworded (no firmware change). In 27, stopping drum 1's latched
  repeat cannot be heard, because its recorded hits play on every step: the check is pad 29 no longer pulsing. 26d
  now says why it taps pad 30 (dark on a drum): on the Repeat page, pads 29 and 30 are drums 1 and 2.
