# CTPlay UI map

Every control CTPlay claims, and the rules new features follow. Each spec that adds or moves a control updates this
file in the same change; its review checks it. Pads are numbered 1–32 from the top left.

**Mockups** (a rough guide, agreed with the user 2026-10-25): `layouts/layouts-after-pl17.html` (every page once
the drums spec's PL16 and PL17 are built, and the stock views PL20 adds to) and `layouts/layouts-pl18-candidates.html`
(where later candidates could go; sketches, nothing designed). `layouts/gen.py` makes both; update it when a spec moves
a pad.

## Rules
1. **A track's play settings live on its Play page** (Shift + the track's button). A new feature looks for room there
   before claiming anything else.
2. **Fixed places.** A control sits on the same pad in every build. A build without the feature leaves its pads dark
   and doing nothing: the layout never shifts with the feature set.
3. **Prefer, in order:** one pad per value (a row of choices, as stock does), a cycle pad (each press steps on, as the
   bass pad), a toggle. Combine values under one pad only when a row is full. A plain on/off setting is one toggle
   pad, lit = on (PL18); two values that are both real choices (strum direction: rising · falling) stay a row.
4. **Never change what a stock control does.** Only presses stock ignores are claimed (with Shift, stock passes only
   the buttons in its mask: CLAUDE.md, Controller). Shift + a track button = that track's CTPlay page. Stock's own
   Shift functions stay stock's, e.g. **Shift + Record = record quantise** (Record bright = on, dim = off).
5. **Colours:** bright = selected, dim = an option not selected, dark = no option. Steady codes only (`COL_*` in
   `features/chord/chord_held.h`).
6. **A feature that outgrows its page gets one more page** (PL14; at most two per feature for now), never rows that
   scroll: scrolling would move every control (rule 2) and, with no screen, nobody could tell how far it went. Both
   pages share the feature's one table-of-contents pad, its colour and its action row; ▲ ▼ walk every page in order.

## Claimed controls
| Control | Where | What | Since |
|---|---|---|---|
| Shift + Synth 1 / 2, MIDI 1 / 2 | any view | Open that track's last-used page (switches to its Note view first) | PL06 (pages PL07) |
| Shift + Drum 1–4 | any view | Open that drum's last-used page (switches to the drum first: its drum view, mode 1; a drum view already on screen, mode 1 or the expanded 6, stays) | PL16 |
| Any track button, Note, Mixer, FX, Preset | a page open | Close the page; the button then does what it does in stock | PL06 |
| ▲ ▼ (Octave), with or without Shift | a page open | Previous / next page, both pages of a two-page feature included; their LEDs (51 / 52) show the colour of the page that way | PL07 (two-page features PL14) |
| Shift + pads | a page open | The table of contents (row 4); no setting. A feature's pad opens the page of it used last; the open feature's pad again: its other page. A drum page: the drum page list | PL07 (re-tap PL14; drums PL16) |
| Shift + pads 17–32 | Note view (both layouts) | The track's Quick view: a page's top half: Chords' shapes (rows 1–2) or Arp's pattern / rate rows | PL01 (Quick view PL07; Chords' shapes from PL15) |
| Shift + 1-16/17-32 | Note view, no page open | Flip the Quick view (Chords ↔ Arp; Keys has none); its LED (53) shows which while Shift is held | PL07 |
| Shift + Clear | any view | Stock's metronome toggle, extended: off · click · count-in · both; Clear's LED (55) with Shift: red `0x53` · green `0x17` · magenta `0x32` · cyan `0x4D` | PL08 |
| Play | count-in on, Record armed, stopped | Starts the count (one bar of stock's click, Record LED 48 blinking `0x53`), then Play; Play again during it cancels (agreed D1-D2, as upstream) | PL08 |
| LEDs 32–39 with Shift | any view | Synth 1 / 2, MIDI 1 / 2 (32–35) and Drum 1–4 (36–39, PL16) in `0x2C` where stock left them off | PL07 (drums PL16) |
| Shift + Drum 4 / Drum 3 | SL00D only (diagnostic) | ITCM map / free stack. Never in a build with the chord feature (`conflicts`) | SL00D |
| Shift + Drum 4 | SL01D only (diagnostic) | RAM above the heap: filled chunks, main-stack depth, carried over (`specs/2026-10-20-ram-above-heap-probe-design.md`). Never with chord | SL01D |
| SysEx on USB | PL03D / PL04D only (diagnostic) | Voice log page | PL03D |
| Step pad + key pad (either first) | Note view (2-row), the track's step-entry chords on (Keys pad 2) and a chord shape or bass mode set | The key's chord into the held step; the key again on that step takes the chord out. Off: stock's step entry | PL18 |
| Row 4 (pads 25–32) | stock's probability view (Shift + Pattern Settings), any track | **Trig conditions: the pass grid** of the step row 3 shows (cyan; bright = ticked, dim = in the cycle). A hold of ½ s = a cycle of the pad's number of passes, pass 1 ticked (from another cycle the ticks that fit are kept; the length's pad again or pass 1 held clears). A tap ticks / unticks a pass (the last untick clears; past the cycle or on a special: nothing). With a special set: all 8 dim in its colour. Accepted as stock's row 3: a step pad held, or stopped, or the step views not following the playhead; a step with notes / a hit only. Written on the pad's release; while held ½ s the row shows what the hold will write | PL20 |
| Shift + row 4 (pads 25–32) | stock's probability view, any track | **The special conditions**, one pad each: 25 FIRST · 26 NOT FIRST (green) · 27 FILL · 28 NOT FILL (orange; dark and inert on a note track) · 29 PRE · 30 NOT PRE (violet) · 31 LAST · 32 NOT LAST (yellow). Bright = the step's, dim = the others; the lit one again clears. Shift is read at the press. Shift + row 3 stays stock's plain press | PL20 |
| Pads 21–24 | the drum expanded view (Drum N, then Note), no drum page open | **FILL for drums 1–4**, each above its drum pad (29–32): held = on; a tap while playing arms the drum's next whole pass, a tap while armed disarms, a tap after a finished fill arms again; stopped, a tap does nothing; Stop disarms (a drum page open or not). Dim orange `0x46` off, bright orange `0x45` on, yellow `0x2D` armed. A drum page (Shift + Drum N) covers them, as pages do everywhere | PL20 |

Shift + pads 1–16 in the Note view stay stock's. Rows 1–3 of the probability view stay stock's: PL20's row 4 follows
the rule "per-step values in stock's step views" (Planned page structure, below).

## Pages (PL07, Keys PL08, Pattern tools PL11, Melody PL13, second pages PL14; Shift + a synth or MIDI track's button)
Table of contents (Shift held on a page): pad 25 Chords (green), 26 Arp (blue), 27 Pattern tools (orange `0x45` /
`0x46`), 28 Melody (yellow `0x2D` / `0x2E`, PL13), 32 Keys (magenta); 29–31 dark. ▲ ▼ step through the pages in pad order, skipping the dark pads.

**Features on two pages** (PL14, rule 6; spec `specs/2026-10-21-melody-variations-design.md`): Pattern tools (pad 27)
= Pattern tools 1 and Pattern tools 2; Melody (pad 28) = Melody and Phrasing. Tapping a feature's pad opens the page of
it used last; tapping the pad of the feature already open steps to its other page. ▲ ▼ order: Chords, Arp, Pattern
tools, Pattern tools 2, Melody, Phrasing, Keys; their LEDs show the colour of the page that way (both pages of a
feature in its colour). `page_slot` keeps the feature (0–7, as before); which page of each feature was used last is
`page_sub` (saved; bit 0 Pattern tools 2, bit 1 Phrasing). PL13 and older ignore it and open Melody.

**Page slots** (user, 2026-10-18; built in PL11): a page's pad in the list is its home for good, and its number in code
and in saved projects (`page_slot`). **Main pages** (what people play with most) fill the row from the left in the order
they arrive: 25 Chords, 26 Arp, 27 Pattern tools, then 28, 29, … **Setup pages** (set once, used less) fill it from the
right: 32 Keys, then 31, … Adding a page never moves one. A feature gets a main pad only once it has outgrown its page
(e.g. the harmonizer, planned on the Chords page). Past about six main pages, a second row (two rows of six or so) is
the way out; not before it is needed.

**Chords** (green):

| Row | Pads | Controls |
|---|---|---|
| 1 | 1–8 | **Shape** (green): off · triad · 7th · 9th · sus2 · sus4 · add9 · 6th |
| 2 | 9–13 | **More shapes** (green, PL15): power · shell 7 · quartal · 7sus4 · 6/9. One shape choice across rows 1–2 |
| 2 | 14–16 | *free* (semitone shapes, if their spike finds a way past the scale snapping) |
| 3 | 17–20 | **Inversion** 0–3 (blue). While voice leading is on: the stored one dim, the others dark; a press turns voice leading off and picks it |
| 3 | 21–23 | **Spread** (magenta): close · drop-2 · wide |
| 3 | 24 | **Bass** cycle (orange): off (dim) · below (bright) · rootless over bass (white) |
| 4 | 25–27 | **Voice leading** (blue, PL15; one at a time, the lit one again = off): close · top line · bottom line |
| 4 | 28–30 | **Strum** (white; none lit = off, the lit one again = off): slow · medium · fast (with a pattern on: only the stored speed, dim) |
| 4 | 31–32 | **Strum direction** (white): rising · falling (with a pattern on: only the stored one, dim) |

Rows 1–2 are the Chords page's quick half. PL15 moved the page (spec `specs/2026-10-23-chords-page-design.md`): until
PL14 strum sat on pads 1–6 and the palette on 17–32 (voicing 17–24, shapes 25–32, the Shift palette too); the shapes
moved to the top, as every other page's main control, a deliberate break of rule 2 decided by the user.

**Arp** (blue):

| Row | Pads | Controls |
|---|---|---|
| 1 | 1–8 | **Pattern** (green): off · up · down · up-down · down-up · random · as played · chord |
| 2 | 9–12 | **Rate** (blue): 1/4 · 1/8 · 1/16 · 1/32 |
| 2 | 13, 14 | **Triplet**, **dotted** (magenta toggles, one at a time; dotted is dark at 1/32) |
| 2 | 15 | *free* |
| 2 | 16 | **Latch** (orange toggle) |
| 3 | 17–20 | **Octaves** 1–4 (magenta) |
| 3 | 21 | **Gate** cycle: 6/6 `0x63` … 1/6 `0x68` (stock's Gate view), one sixth down per press, 1/6 → 6/6 |
| 3–4 | 22–32 | *free* |

Rows 1–2 are the Arp page's quick half.

**Keys** (magenta, PL08; one toggle per setting from PL18; no quick half; specs
`specs/2026-10-26-step-entry-chords-design.md`, `specs/2026-10-28-playback-strum-design.md`):

| Row | Pads | Controls |
|---|---|---|
| 1 | 1 | **Mono record** toggle: magenta `0x32` = mono, dim magenta `0x38` = poly (stock). PL08–PL17: pads 1–2 (poly · mono) |
| 1 | 2 | **Step-entry chords** toggle (PL18): green `0x17` = on, dim green `0x18` = off (stock) |
| 1 | 3–4 | **Pattern strum** (PL19): played · written, white `0x01` = the track's mode, dim white `0x02` = not; none lit = off (stock). A press on the unlit one picks it, on the lit one sets off. Acts only with the track's strum speed on (Chords page 28–30) |
| 1–4 | 5–32 | *free* (the fourths layout on row 2 later) |

**Pattern tools** (orange, PL11; no quick half; spec `specs/2026-10-17-euclidean-design.md`):

| Row | Pads | Controls |
|---|---|---|
| 1–2 | 1–16 | **Hits**: pad k = k hits, and the **preview** of the current pattern's steps: hit orange, no hit dim, past its length dark (its first 16 steps). From PL14 the preview is the final rhythm (what Write writes: after the cycle, the combine and the thinning) |
| 3 | 17–19 | **Rotate** (dim white): one step earlier · one step later · back to the start (with a cycle set: within the cycle, from the rotation mod its length) |
| 3 | 20 | **Rhythm source** toggle (PL13): Euclid (dim white `0x02`) · groove (white `0x01`) |
| 3 | 21 | **Gate** cycle, as the Arp page's: 6/6 `0x63` … 1/6 `0x68`; PL13 adds a 7th value, "to the next hit" (white `0x01`), after 1/6 and before 6/6 |
| 3 | 22–24 | **Velocity** (magenta): soft · medium · hard |
| 4 | 25–28 | **Cycle** (PL14, cyan `0x4D` / `0x4E`): 3 · 5 · 6 · 7 steps; none lit = the whole pattern; the lit pad turns it off. The first rhythm is worked out over the cycle and repeated |
| 4 | 29–30 | **Dice** rhythm · notes (PL13, dim white `0x02`; same pads on all four pages of Pattern tools and Melody; notes dark while the order is "same" and ties are off) |
| 4 | 31 | **Undo** (blue while this track has one): the steps the last Write replaced; again = the Write back. In a draft: back to the pattern from before the first Write, and the draft ends |
| 4 | 32 | **Write** (action, two presses): dim orange, `0x47` (blinking) once armed; dark with no hits picked. In a **draft** (PL13): bright orange `0x45`, steady, and every press on the page re-writes at once |

**Pattern tools 2** (orange, PL14, pad 27 again; the second rhythm; no quick half). A second Euclidean rhythm and how it
combines with the first; with combine off it does nothing:

| Row | Pads | Controls |
|---|---|---|
| 1–2 | 1–16 | **Second rhythm: hits** (pad k = k hits) and **its own preview** in white: hit `0x01`, no hit `0x02`, past the pattern's length dark |
| 3 | 17–19 | **Rotate** the second rhythm (dim white): earlier · later · back to the start (a rotation stored past a shortened pattern: from the rotation mod its length) |
| 3 | 20–24 | **Combine** (violet `0x49` / `0x4A`; none lit = off, the lit pad turns it off): both · either · one, not both · first without second · accent (the first rhythm, played hard where the second hits) |
| 4 | 25–27 | **Thinning** (cyan `0x4D` / `0x4E`; none lit = off): drop about 1 in 4 · 1 in 3 · 1 in 2 hits (never the first) |
| 4 | 28 | *free* (a drum's accent, PL17) |
| 4 | 29–32 | **Dice** rhythm · **dice** notes · **Undo** · **Write** (as on Pattern tools) |

**Melody** (yellow `0x2D` / `0x2E`, PL13, pad 28; spec `specs/2026-10-19-melodic-generator-design.md`; no quick half).
The pitch layer of Pattern tools' Write; pads 29–32 are the same actions as on Pattern tools:

| Row | Pads | Controls |
|---|---|---|
| 1 | 1–8 | **Order** (yellow): same · up · down · up-down · climb · walk · random · bass |
| 2 | 9–10 | **Pool** (green `0x17` / `0x18`): chord · scale |
| 2 | 11–13 | **Range** (magenta `0x32` / `0x38`): 1 · 2 · 3 octaves |
| 2 | 14 | **Accent** cycle: off `0x2E` · first hit `0x2D` · on the beat `0x01` · every 3rd hit `0x32` |
| 2 | 15–16 | *free* |
| 3 | 17 | **Root: last pad** (white `0x01` / `0x02`) |
| 3 | 18–24 | **Root: scale degree** 1–7 (blue `0x07` / `0x08`) |
| 4 | 25–28 | **Octave** of a degree root (magenta): −2 · −1 · 0 · +1; all dim and ignored while the root is "last pad" |
| 4 | 29–32 | **Dice** rhythm · **dice** notes · **Undo** · **Write** (as on Pattern tools) |

**Phrasing** (yellow, PL14, pad 28 again; Melody's second page; no quick half). The amounts are the same three on every
row (about 1 in 4 · 1 in 3 · 1 in 2); none lit = off, the lit pad turns its row off:

| Row | Pads | Controls |
|---|---|---|
| 1 | 1–3 | **Ties** (cyan `0x4D` / `0x4E`): hits (never the first) tie to the note before: held, not struck again |
| 1 | 4 | *free* |
| 1 | 5–7 | **Octave jumps** (magenta `0x32` / `0x38`): notes of a line order (not "same") jump an octave |
| 1 | 8 | *free* |
| 2–3 | 9–24 | *free* (reserved: transforms (shuffle pitches, reverse, mirror; moved here from Pattern tools 25–28 in PL14), contour shapes, phrase repeat) |
| 4 | 25–28 | *free* |
| 4 | 29–32 | **Dice** rhythm · **dice** notes · **Undo** · **Write** (as on Pattern tools) |

## Drum pages (PL16, Pattern tools PL17; Shift + Drum 1–4; spec `specs/2026-10-25-drums-design.md`)
The drums (tracks 4–7) follow the page rules above with **their own page list**; a page slot means the same feature
for every track kind, so a feature keeps its pad. `drum_page[d]` (saved, not linked): bits 0–2 the slot, bit 3
Pattern tools 2 (PL17). A drum whose stored slot has no page opens Repeat. No drum Quick view; LED 53 stays the note
tracks'.

Drum page list (Shift held on a drum page): pad 25 Levels (later, dark), 26 **Repeat** (blue `0x07` / `0x08`), 27
**Pattern tools** and Pattern tools 2 (PL17, orange `0x45` / `0x46`; dark in PL16); 28–32 dark. One table in `page.c`
(`DRUM_COL`) gives both the colours and which slots hold a page. ▲ ▼ step through the drum pages: Repeat, Pattern
tools, Pattern tools 2 (PL16: one page, both dark, a press does nothing).
**Moved in the beta build** (layout pass 2026-11-10, `layouts/beta-layout-pass.md`; decided by the user; PL16–PL20:
Repeat on 25): **Repeat on pad 26** (the slot of the note tracks' Arp: notes repeated in time while held), **Levels
on 25** (later; the slot of Chords: what a pad plays), Pattern tools stays on 27, **Vary on 29** (later, shared with
the note tracks), **Setup on 32** (later: GM drum notes; the slot of Keys: set once). `drum_page`'s value for Repeat
is 1 (PL16–PL20: 0); a stored slot with no page, an alpha project's 0 included, opens Repeat, and the load's check
clears such a slot but keeps bit 3 (Pattern tools 2 used last).

**Repeat** (blue, PL16; pad 26, PL16–PL20 pad 25; one setting for the kit, `repeat_cfg`; no quick half):

| Row | Pads | Controls |
|---|---|---|
| 1 | 1–4 | **Rate** (blue): 1/4 · 1/8 · 1/16 · 1/32 |
| 1 | 5–8 | **Triplet rates** (magenta): 1/4T · 1/8T · 1/16T · 1/32T. One rate across pads 1–8; the lit pad again = no rate |
| 2 | 9–12 | **Velocity** (white `0x01` / `0x02`): as struck · fade · swell · accent the beat |
| 2 | 13–14 | *free* |
| 2 | 15 | **Unquantized repeats** toggle (cyan `0x4D` / `0x4E`) |
| 2 | 16 | **Latch** toggle (orange) |
| 3 | 17–24 | *free* (reserved: per-drum velocity levels, with Levels) |
| 4 | 25–28 | *free* |
| 4 | 29–32 | **Drums 1–4**: play the drum, repeat it while held when a rate is lit (a tap toggles it with latch on and a rate lit; no rate: once per press, latch or not). Stock's expanded-view colours `0x45` `0x2D` `0x49` `0x4D` (orange, yellow, violet, cyan, measured), white `0x01` while a hit sounds, **pulsing white `0x04`** while latched (an animated code on purpose) |

**Pattern tools** (orange, PL17, pad 27; per drum: `drum_euclid`, `drum_rhythm`, `drum_seed`; no quick half). The note
tracks' page with the same pads for the same things (rule 2 across track kinds); where a control means nothing for a
drum, a drum control takes its pad or it stays dark:

| Row | Pads | Controls |
|---|---|---|
| 1–2 | 1–16 | **Hits** and the **preview**, as the note tracks': over the drum's **shown pattern** (the one its step pads show; it differs from the playing one only after Shift + Patterns, stock's pattern-follow toggle). No drum recorder where one is expected: no preview, Write dark |
| 3 | 17–19 | **Rotate** (dim white), as the note tracks' |
| 3 | 20 | **Rhythm source** toggle: Euclid · groove, as the note tracks' |
| 3 | 21 | **Roll** cycle (instead of the gate): 1 · 2 · 3 hits a step (microsteps 0 · 0, 3 · 0, 2, 4), in stock's Gate view colours for 1/6 `0x68` · 3/6 `0x66` · 6/6 `0x63` (user, 2026-10-25) |
| 3 | 22–24 | **Velocity** (magenta): soft 48 · medium 96 · hard 127 |
| 4 | 25–28 | **Cycle** (cyan), as the note tracks' |
| 4 | 29 | **Dice** rhythm (dim white) |
| 4 | 30 | dark (dice notes: a drum has no notes); reserved for **avoid** (layout pass, 2026-11-10) |
| 4 | 31 | **Undo** (blue while this drum has one): one copy per drum (128 B), apart from the note tracks' |
| 4 | 32 | **Write**, as the note tracks' (two presses, on the release; dark with no hits). Writes the shown pattern's steps first .. last: a hit = the velocity (127 when accented), probability always, no sample flip, the roll's microsteps; every other step empty; through the drum editor's step store. A **draft** when the groove, a combine, the thinning, a cycle or an accent is on (the roll is not one) |

**Pattern tools 2** (orange, PL17, pad 27 again): the note tracks' page on the drum's own settings, and:

| Row | Pads | Controls |
|---|---|---|
| 4 | 28 | **Accent** cycle (`drum_accent`), Melody's colours: off `0x2E` · first hit `0x2D` · on the beat `0x01` · every 3rd hit `0x32`. An accented hit is written at 127 |
| 4 | 30 | dark (dice notes) |

## Chords Quick view (Shift held in the Note view, PL15)
| Pads | Controls |
|---|---|
| 17–24 | **Shape**: the page's row 1 |
| 25–29 | **More shapes**: the page's row 2 (30–32 dark) |

Until PL14 this was the chord palette: inversion 17–20, spread 21–23, bass 24, shape 25–32.

## Planned page structure (agreed 2026-10-16; PL07 built the frame, Chords and Arp)
The rules every later page follows. PL07 built: pages, last-used page, table of contents, ▲ ▼, Quick view (the flip
on Shift + 1-16/17-32), Shift-lit track buttons.
- **Pages.** Each feature gets its own page on Shift + the track's button, in a fixed order with its own main colour.
  Each page is two 16-pad halves. Shift + a track button opens that track's last-used page (1 B per track; back
  to the first page at power-on until CTPlay has saved settings).
- **Table of contents:** Shift held on a page. Row 4 (pads 25–32) shows one pad per page in its colour: the open page
  bright, the others dim, pages this build lacks dark (each keeps its pad: rule 2). Tapping one opens that page.
  Rows 1–3 are dark while Shift is held. So Shift + track button, then a pad, goes straight to any page. Shift + pad no
  longer picks a setting on a page.
- **▲ ▼ (Octave, ids 19 / 20)** step to the next and previous page while a page is open, as in Preset view. Their LEDs
  show whether there is a page that way (panel LEDs 51 / 52 = the active view's elements 32 / 33, stock's LED map
  `0x08059438`). Once the page closes they are octave buttons again.
- **Track-button LEDs with Shift** (agreed 2026-10-16): stock turns the track buttons off while Shift is held and lights
  only the buttons that have a Shift function (Note, Gate, Microstep `0x2C`, Velocity `0x74`). The tracks that have
  pages light in the same `0x2C` (panel LEDs 32–35 = Synth 1, Synth 2, MIDI 1, MIDI 2; 36–39 = Drum 1–4, once drum
  pages exist). Written only where stock left the LED off. No RAM.
- **Quick access** (agreed 2026-10-17, built in PL07): Shift in the Note view shows a page's *quick half* on pads
  17–32 (the only Shift pads stock leaves free there; pads 1–16 stay stock's). Each page declares one quick half, or
  none. **Shift + 1-16/17-32** (stock ignores it) steps to the next page's quick half; its LED (53) shows that page's
  colour while Shift is held. It changes only when the user changes it (default Chords, so Shift behaves as now);
  1 byte per track. Shift + ▲ ▼ is not available: in the Note view stock lights them `0x2C` with Shift and uses them
  (it changes the pattern's notes, most likely a transpose; emulation, stock image).
- **Actions** (humanize, mutate, Euclidean write) change the pattern: the first press makes the pad blink (an animated
  code, on purpose), the second applies; any other press disarms. An action that writes the pattern runs on the
  pad's **release**, never while it is held (PL13: a write during a press made a phantom press on the next pad). Euclidean Write (PL11) replaces the current
  pattern's steps and has an Undo pad (user, 2026-10-17); mutate's place is open. Actions have no quick half.
- **Drum tracks** get their own pages on Shift + Drum 1–4, in the same structure (built in PL16: Drum pages above).
- **Project page: Shift + Mixer** (stock ignores it): project-wide settings. One page, no table of contents.
- **Per-step values do not go on pages**: they go where stock edits steps. Stock's Probability view (Shift + button 12)
  ignores its row 4 (it arrives as 8–15; upstream SC39 put its mutate levels there). PL20 claims it for trig
  conditions.

Where each kind of control goes: settings on the track's pages, pattern actions on its Pattern tools page (actions
that rework existing notes on Vary, slot 29, from the layout pass), per-step values in stock's step views, project
settings on the project page.

**One slot, one kind of page** (layout pass 2026-11-10, `layouts/beta-layout-pass.md`, decided by the user): 25 what a
pad plays (Chords · drums: Levels), 26 repeats in time while held (Arp · Repeat), 27 write a rhythm (Pattern tools),
28 write notes (Melody · none on drums), 29 rework the pattern (Vary, both), 30–31 free, 32 set once (Keys · drums:
Setup). Every remaining candidate's place is in that file.

Planned pages for synth and MIDI tracks (the table-of-contents pad in brackets):

| Page | Colour | Top half (pads 1–16) | Bottom half (pads 17–32) | Quick half |
|---|---|---|---|---|
| Chords (25) | green | shapes, more shapes (PL15); semitone shapes on the free pads 14–16 if they come | inversion · spread · bass; voice leading (PL15) · strum · direction (PL08) | top (PL15; bottom until PL14) |
| Arp (26) | blue | pattern · rate · triplet · dotted · latch (as now) | octaves 1–4 · gate (one cycling pad, stock's Gate-view colours) · 3 free | top |
| Pattern tools (27) | orange (PL11) | Euclidean fills: hits 1–16 and the preview (PL11) | Euclidean rotate, gate, velocity, Undo, Write (PL11); rhythm source, dice (PL13); cycle (PL14); humanize later | none |
| Pattern tools 2 (27, PL14) | orange | the second rhythm's hits and preview | rotate, combine, thinning; dice, Undo, Write | none |
| Melody (28, PL13) | yellow | order, pool, range, accent | root, octave; dice, Undo, Write | none |
| Vary (29, layout pass) | magenta | humanize velocity / timing, ratchets, mutate in key | quantize, reverse, nudge ◀ ▶; dice, Undo, Write (both track kinds; dark on a drum where meaningless) | none |
| Phrasing (28, PL14) | yellow | ties, octave jumps; transforms, contour shapes, phrase repeat later | dice, Undo, Write | none |
| Keys (32) | magenta | one toggle per setting (PL18): mono record pad 1 (PL08–PL17: pads 1–2), step-entry chords pad 2 (green); pattern strum pads 3–4 (PL19, white: played · written); strummed release pad 5, scale lock on MIDI in pad 6, MIDI in through chords and arp pad 7, MIDI in into a held step pad 8 (layout pass); layout: scale (stock) · in-key fourths · chromatic fourths · Jankó on row 2 | split keyboard, if it comes | none (PL08) |

Planned pages for drum tracks: **Levels** (25; 16 levels: velocity / pitch / decay), **Repeat** (built in PL16; on 26
since the beta build), **Pattern tools** (built in PL17, as above), **Vary** (29, shared), **Setup** (32: MIDI out
notes stock · GM).

Project page (a settings page visited rarely; kept small): live transpose; if needed, scale lock on MIDI in (check
stock first: the router may already quantise MIDI in) and a split-keyboard toggle (Synth 1 on pads 1–16, Synth 2 on
17–32; upstream starts it with a gesture, holding one Synth button and pressing the other); later, CTPlay settings
housekeeping (keep them with the project, reset to defaults: an action, two presses) and build info (one pad per
feature in this build, lit or dark). Metronome count-in is on **Shift + Clear** instead (PL08), as upstream does
(stock's own metronome toggle, extended to off / click / count-in / both): a feature CTPlay shares with upstream keeps
upstream's control where it fits these rules.

Per-step values: trig conditions in the Probability view's row 4 (built in PL20: the pass grid, Shift = the specials;
not upstream's step-frequency layout); ratchets may exist in stock's Microstep view already (check stock first). No controls: saved settings, recorded strum (stock's record quantise
decides: off keeps each note's microstep; PL19's pattern strum, Keys pads 3–4, records a strum as a plain chord or a roll). Chords in step entry has its toggle on Keys pad 2 (PL18).

## Free, and planned
- **Free on the pages:** Chords 14–16 (PL15; harmonizer and custom chord: a second Chords page); Arp 15, 22–32; Keys 9–32 (5–8 and row 2 reserved by the layout pass); Pattern tools 2 28 (note tracks; a drum's accent); Melody 15–16; Phrasing 4, 8,
  9–24 (reserved: transforms, contour shapes, phrase repeat), 25–28; Repeat 13–14, 17–24 (reserved: velocity levels),
  25–28. A drum's pad 30 on Pattern tools: reserved for **avoid** (hats skip the kick's steps; layout pass, decided: a drum
  never has dice notes, so their reservation there protects nothing). On Pattern tools 2 it stays dark.
- **Free buttons with Shift (stock ignores them):** Preset, Mixer; 1-16/17-32 outside the Note view (on a drum page it
  goes to stock, which ignores it: button 21 is not in stock's Shift mask).
- **Free in stock views:** the drum expanded view's pads 17–20 and 25–28 (stock ignores pads 1–28 there; rows 1–2 are
  stock's dark pads too).
- **Planned:** Shift + Mixer (project page). FILL for the note tracks on the drum expanded view's pads 17–20 (Synth 1 /
  2, MIDI 1 / 2, in the track buttons' order) and an every-track FILL on pad 25 (spec
  `specs/2026-10-28-trig-conditions-design.md`, "FILL", Later); until then a note track has no FILL.
