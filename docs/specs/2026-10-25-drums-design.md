# Drums: pages, note repeat, Pattern tools per drum (PL16, PL17) — design

Date: 2026-10-25 · Branch: `slim` · Status: **approved 2026-10-25** (PL16 plan `plans/2026-10-25-drums-pl16.md`; builder check done 2026-10-25; its minor questions settled as *my call*s,
the user's calls taken 2026-10-25: an "unquantized repeats" setting, latch keeps running, one Repeat setting for the kit). Built after PL15 is tagged: PL16's saved fields start at PL15's payload end, so
a fix from PL15's run that moves a field moves them too. The user skipped the questions and asked
for a proposal that keeps PL15's page structure. Every choice below not made by the user is marked *my call*. Research:
`investigations/2026-10-25-drums.md` (summary), with its emulation runs and market survey beside it.

## Purpose

Drums are half the instrument, and CTPlay has done nothing for them yet. Two things lead the wish lists: **note
repeat** (Novation lists it as the drum feature Circuit Rhythm has and Tracks lacks) and **generated rhythms per
drum** (Euclid with rotate and an accent; generate, then hand-edit). CTPlay already has the second for note tracks
(Pattern tools, PL11–PL14), so drums get the same pages, and the same draft / Write / Undo.

**Success:**
- Hold a drum pad on the Repeat page and it repeats in time at the chosen rate. You can change the rate while holding,
  and stock records what you heard.
- In a few presses, a drum gets an even rhythm of k hits, rotated, at a velocity, with rolls if wanted. Undo is one
  press away.

**Non-goals (later):**
- fills and trig conditions (they need logic while the pattern plays);
- Levels (one drum over 16 pads);
- hats that avoid the kick;
- a Grids-style density map;
- flam;
- velocity humanize;
- a drum Quick view.

**Anti-goals:**
- **Changing what a stock drum view does.** The pads of the drum's own views stay stock's.
- **Changing a stock setting on the user's behalf.** Rec Quantise and fixed velocity stay as the user set them;
  only the opt-in "unquantized repeats" setting steps around Rec Quantise, for repeats.

## Two builds, one spec

*My call:* the device run of a build this size is long (PL15's is), so this spec ships in two builds:

- **PL16:**
  - the groundwork (the link's image in ITCM);
  - the drum page frame (Shift + Drum 1–4, table of contents, ▲ ▼, Shift LEDs);
  - the **Repeat** page.
- **PL17:** **Pattern tools** and **Pattern tools 2** for drums.

The saved layout and the pads are fixed now for both builds, so PL17 moves nothing PL16 placed.

## The drum page frame (PL16)

Drums follow the synth and MIDI tracks' page rules (`ui-map.md`, Pages) unchanged:

- **Opening and closing:**
  - Shift + Drum N opens that drum's last-used page.
  - The drum's button opens it in its default view first. Emulation: always mode 1, steps on top and sample pads below.
  - A track button, Note, Mixer, FX or Preset closes the page.
- **Navigation:**
  - ▲ ▼ step through the pages.
  - Shift held on a page shows the table of contents on row 4.
  - With Shift held, the drum buttons that have pages light in `0x2C` (panel LEDs 36–39), where stock left them off.
- **The drum table of contents is its own list.** The page slots keep their meaning across track kinds (*my call*):
  the same feature sits on the same pad.

  | Pad | Page | Colour |
  |---|---|---|
  | 25 | **Repeat** (PL16) | blue, the clocked-retrigger colour the Arp uses |
  | 26 | Levels (later), dark | |
  | 27 | **Pattern tools** and **Pattern tools 2** (PL17) | orange |
  | 28–32 | dark | |

  A drum with no page built yet opens Repeat.

Before PL17, pad 27 is dark: rule 2 keeps its place.

## The Repeat page (PL16; pad 25, blue)

The Repeat page is both its settings and the surface you play on: the rate pads and the drum pads are on one page, so
one hand can hold a drum while the other changes the rate, as on an MPC. It shows the same thing whichever drum
opened it, because its settings are shared by all four drums (*my call*: a rate is a feel for the whole kit; on
Circuit Rhythm and the MPC it is one setting).

| Row | Pads | Controls |
|---|---|---|
| 1 | 1–4 | **Rate** (blue): 1/4 · 1/8 · 1/16 · 1/32 |
| 1 | 5–8 | **Triplet rates** (magenta): 1/4T · 1/8T · 1/16T · 1/32T. One rate across pads 1–8; the lit pad again = repeat off (none lit) |
| 2 | 9–12 | **Velocity** (white `0x01` / `0x02`): as struck · fade · swell · accent the beat |
| 2 | 13–14 | *free* |
| 2 | 15 | **Unquantized repeats** (cyan `0x4D` / `0x4E` toggle; user, 2026-10-25): off = repeats record as stock's Rec Quantise says; on = they record unquantized even with Rec Quantise on |
| 2 | 16 | **Latch** (orange toggle) |
| 3 | 17–24 | *free* (reserved: per-drum velocity levels with Levels) |
| 4 | 25–28 | *free* |
| 4 | 29–32 | **Drums 1–4**: play the drum (velocity-sensitive), and repeat it while held when a rate is lit. Lit in stock's own drum colours (the expanded view's), white while sounding |

Pads 29–32 match the expanded drum view (Note pressed twice on a drum), where 29–32 are drums 1–4 too.

### How repeat plays

- **Press:**
  - The drum sounds at once, at the velocity shape's first value (below).
  - The repeats then follow the rate's grid, locked to the sequencer while it plays. Stopped, they run at the
    project's tempo from the press.
  - A grid point closer than half an interval after the press is skipped, so a press never sounds twice (*my call*).
- **Rate change while holding:** the stream goes on at the new rate from the next grid point. It never restarts.
- **Release:** the repeats stop. Pressing another drum pad adds its own repeat; up to four drums repeat at once.
- **Latch:**
  - **On:** a tap starts that drum's repeat and the next tap of it stops it. Latched repeats go on after the page
    closes (*my call*: that is what latch is for, hands free), and the page shows them by their pads pulsing white.
  - **Turning latch off** stops them.
  - So does a project load.
- **No rate lit:** pads 29–32 only play the drum, once per press, latch or not. Turning the rate off (the pad, or a
  CTCtrl write) stops the latched drums, as turning latch off does (final review, 2026-10-25).
- **Timing:** the ticks, at 24 per quarter, are 1/4 24 · 1/8 12 · 1/16 6 · 1/32 3 · 1/4T 16 · 1/8T 8 · 1/16T 4 ·
  1/32T 2. At the usual sync rate 1/16, all of them fall on the step's six microsteps. Swing applies to the repeats,
  as it does to the Arp.
- **Velocity** (row 2), worked out per hit from the strike's velocity v, the press's own hit included:
  - **As struck:** every hit at v.
  - **Fade:** from v down to v/4 over one beat from the press, then it stays there.
  - **Swell:** from v/4 up to v over one beat from the press, then it stays there. Rising hits always retrigger
    (the DSP rule below only swallows softer ones), so swell is the safe ramp.
  - **Accent the beat:** hits on the sequencer's quarter notes at v, the others at 2/3 v (stopped: quarters from the
    press). A press off the beat sounds at 2/3 v.
  - The shapes, and "one beat from the press", are *my call*. Stock's **fixed velocity** setting still forces every live drum hit to
    96, so with it on all four sound the same; the guide says so.
- **What is recorded:** CTPlay records nothing itself. Each hit goes through the drum's live route, the one a finger
  press on the expanded view uses, and **stock's recorder records it as if played**. This only happens while
  playing with Record armed, never in the count-in (emulation, 2026-10-25). Two limits come from the step format:
  - **One velocity per step:** fade and swell record as steps of a stair.
  - **Rec Quantise on** (Shift + Record, stock's) records one hit per step, so 1/32 and the triplets record as 1/16.
    **The user's choice (2026-10-25): a setting, as Keys' poly / mono record.** "Unquantized repeats" (pad 15) is off
    by default, and repeats then follow stock's Rec Quantise. On, repeats record unquantized even with Rec Quantise
    on; stock's setting itself is never changed. *Builder's call* how: keep CTPlay's repeat hits out of the recorder's
    quantise step (best: only repeat hits are affected), or switch the drum recorders' quantise byte off while a
    repeat runs and back after (then a finger press on a drum during a repeat records unquantized too; the guide says
    so). Either way it ends with the last repeat, latch off and a project load. **PL16 takes the second** (Task 6):
    the byte is a cache stock refreshes at each step's tick 0, so the override sits in that refresh (mid hook
    `rec_quant`, `0x0803FE8C`) and puts back stock's own last value at the end (drums spike, `u1_refresh.py` ..
    `u3_window.py`).
- **A muted drum** (Mixer) still sounds and records from the live route, as a finger press does in stock.

### The rules it keeps

- **The phantom-press rule:** the press only records "drum d held, velocity v" and sends the one first hit, as stock
  does. Every repeat comes from the Main task's heartbeat, with PL06's Arp clock (`seq_tick` + `main_ms`). There are
  no loops and no long masked sections on a press.
- **Never from the DSP tick:** each hit takes the DSP lock once.
- **Each drum is one sound voice:** a hit softer than the one still sounding does not retrigger (DSP). So fade at
  fast rates on long samples may thin out. This is a device check, not a design rule.

## Pattern tools for drums (PL17; pad 27, orange, two pages)

These are the note tracks' Pattern tools and Pattern tools 2, with **the same pads for the same things** (rule 2 across
track kinds, *my call*). Where a note-track control means nothing for a drum, a drum control takes its pad or the pad
stays dark:

| Page | Pad(s) | Note tracks | Drums |
|---|---|---|---|
| Pattern tools | 1–16 | hits + preview | same |
| Pattern tools | 17–19 | rotate | same |
| Pattern tools | 20 | rhythm source: Euclid · groove | same (groove: hits on strong beats first, good for kicks) |
| Pattern tools | 21 | gate cycle | **Roll** cycle: 1 · 2 · 3 hits per step (microsteps 0 · 0, 3 · 0, 2, 4), in stock's Gate view colours for 1/6 · 3/6 · 6/6 (`0x68` · `0x66` · `0x63`; user, 2026-10-25) |
| Pattern tools | 22–24 | velocity soft · medium · hard | same |
| Pattern tools | 25–28 | cycle 3 · 5 · 6 · 7 | same |
| Pattern tools | 29 | dice rhythm | same |
| Pattern tools | 30 | dice notes | dark |
| Pattern tools | 31 / 32 | Undo / Write (and the draft) | same |
| Pattern tools 2 | 1–16, 17–19 | second rhythm: hits, preview, rotate | same |
| Pattern tools 2 | 20–24 | combine | same (accent: the first rhythm, hard where the second hits) |
| Pattern tools 2 | 25–27 | thinning | same |
| Pattern tools 2 | 28 | *free* | **Accent** cycle, as Melody's: off · first hit · on the beat · every 3rd hit. An accented hit is played hard |
| Pattern tools 2 | 29–32 | dice rhythm · dice notes · Undo · Write | same, with dice notes dark |

**What a Write writes:**

- **Which pattern:** the drum's **shown pattern**, which the step pads and stock's edits act on (*my call*). It is
  the playing pattern except after Shift + Patterns (stock's pattern-follow toggle), when you are looking at another
  one. Writing what you see is the safe reading. Note tracks write the playing pattern; the two differ only in that
  case.
- **Which steps:** the rhythm fills the pattern's first to last step (stock's Pattern Settings), and the steps
  outside them are written empty, exactly as on note tracks (*my call*: one behaviour; Undo brings them back).
- **A hit:**
  - velocity from the velocity pads, or hard if accented;
  - the roll's microsteps, probability 7 (always);
  - sample flip none, so the drum's chosen sample plays.
- **A step with no hit:** empty (velocity 0, probability 7, no flip, no microsteps).
- **Left as they were:** the knob automation lanes, the pattern settings and the bytes upstream uses past the steps.
- **How it is written:**
  - Through the drum editor's step store, as stock's Nudge does. Emulation confirmed the step pads and the Velocity,
    Gate and Probability views relight, and the hits survive later stock edits.
  - A pattern the editor doesn't show takes a plain write; the store's own pointer tells which.
  - Undo keeps the 128 B the Write replaced, in ITCM, one per drum.
- **When:** as on note tracks, a Write runs on the pad's **release**, as do Undo and every draft re-write.
- **While recording:** a Write is allowed while recording. The recorder (Main) commits the same store; the write
  keeps both of its buffers equal, so either order carries both changes. An emulation test interleaves them; the
  device run checks it.

## Settings and saving

Everything new goes in **saved block 2**, after `chord_voice` (payload offset 81). Block 1 is full.

| Field | Bytes | What |
|---|---|---|
| `repeat_cfg` (PL16) | 2 | [0] rate 0 off, 1–8 (bits 0–3) \| velocity shape (bits 4–5) \| latch (bit 6) \| unquantized repeats (bit 7); [1] spare 0 |
| `drum_page` (PL16) | 4 | per drum: the page slot (bits 0–2) \| Pattern tools 2 last used (bit 3); device navigation, not linked |
| `drum_euclid` (PL17) | 8 | per drum the note tracks' `euclid_cfg` layout, with the gate bits holding the roll (0–2) |
| `drum_rhythm` (PL17) | 12 | per drum the note tracks' `rhythm_cfg` layout |
| `drum_accent` (PL17) | 4 | per drum the accent (bits 0–1) \| spare |
| `drum_seed` (PL17) | 4 | per drum the rhythm seed (dice, never 0), as `melody_seed`'s first byte: groove, thinning and dice come back the same after a reload; not linked |

- **Size:** 34 B, so the payload goes from 81 B to 115 B. That stays under the CTCtrl link's limit of 127 B, and
  block 2 holds 160 B.
- **Fixed now:** the order above is final. Each build declares only its own fields and appends them (the layout
  lock keeps every position), so PL17's land at 87 onwards. A re-save on PL16 of a PL17 project resets its drum
  Pattern tools settings to their defaults, as any older build does with newer fields (*my call*).
- **Defaults:** repeat off, velocity as struck, latch off, unquantized repeats off; Pattern tools as the note tracks' (no hits, velocity
  medium, rotation 0), but **roll 1 hit**: the note tracks' gate default would read as roll 3.
- **The CTCtrl link:** every field except `drum_page` and `drum_seed` is linked (rev 1), from the build that adds it. CTCtrl's panel learns them; the user keeps
  it current.

**Groundwork (PL16, first task):** the link keeps its last-sent image of the payload in the heap tail, and 94 of its
96 B are used. Move that image to ITCM before the payload grows (`followups.md`, PL15 final review). The image's size
then follows the payload, and the heap tail is left as it is.

## Code (the builder's, within these lines)

- **The page frame:**
  - `page.c` learns track kinds. Drum tracks are 4–7, with their own page list.
  - Opening on button ids 4–7 with Shift.
  - A drum visibility test: container active, track 4–7, the drum step / sample views.
  - The Shift LEDs grow to 36–39.
  - SL00D / SL01D's diagnostic Shift + Drum 3 / 4 never share a build with this: `features.py` or a test refuses it.
- **Repeat:** a new feature, `repeat`, beside `arp`. It shares the Arp's clock hooks and sends through the expanded
  drum view's live sink (`[cont + 0xAC]`, sink at `+0x10`; the address is found from the container, never fixed).
- **Pattern tools:** the Euclid, groove, second rhythm, combine, cycle and thinning code, as is, over 32 steps. Plus
  a drum writer that turns the final rhythm into the four arrays. The draft and the actions take a track kind.
- **Stock symbols to add,** with their sources from the research:
  - store write pointer `0x080354FA`;
  - commit `0x080353C0`;
  - set listener `0x08035398`;
  - touch-all `0x08035456`;
  - drum recorders `0x2003C174 + 4 (4 + d)`;
  - the editor's vtable `0x0805C108`;
  - the drum view vtables.

## Docs in the same build

- `ui-map.md`: the drum page list and the Repeat page (PL16), the drum Pattern tools rows (PL17), and Shift + Drum 1–4
  claimed.
- The user guide:
  - a **Drums** section;
  - the Rec Quantise note;
  - the fixed-velocity note;
  - the one-velocity-per-step note.
- `resources.md`, `candidates.md`, `followups.md` (the link-budget item closed).
- Each build's `TEST.md`, starting from a new empty project.

## Testing

**Emulation, through the real routes:**
- **Pages:** Shift + Drum N opens from every view; the table of contents, ▲ ▼ and the LEDs.
- **Repeat timing:** a held pad repeats at each of the 8 rates; a rate change mid-hold; the double-hit skip; latch
  across a page close.
- **Repeat recording:** hits recorded as in the spike, with quantise off and on.
- **Repeat stopped:** the clock runs free.
- **Pattern tools Write:** the bytes, the step LEDs and the views relight, survival of a stock edit; Undo; the shown
  vs playing pattern after Shift + Patterns; a not-mirrored pattern.
- **Pattern tools while recording:** a Write interleaved with a recorder commit.
- **Saving:** the saved block round trip on PL16 itself; a PL15 save loads without harm. No round trips to older
  builds (alpha policy, CLAUDE.md, 2026-10-25).
- **Locks and stack:** no lock is taken from the DSP tick; the stack measured.

**On the device:**
- **Feel:** repeat and swing; a rate change mid-hold.
- **Sound:** fade at fast rates (the softer-hit rule).
- **Display:** the views refresh after a Write.
- **Recording:** recorded repeats sound as played (quantise off); a Write while recording.

## Alternatives considered

- **Repeat inside the expanded drum view, on its free pads 1–28** (upstream's rollers): no page to open. Not chosen,
  because it puts CTPlay controls into a stock view without Shift, and settings live on pages (rule 1).
- **Repeat settings per drum:** costs 6 B more, and the market survey shows one rate for the kit.
- **Hits through the player's route and written into the pattern** (upstream's rollers and drum arpeggiator): not
  recorded by stock, and they met the editing-copy bug. Not chosen.
- **One build:** a single, very long device run. Two builds keep each run shorter.
