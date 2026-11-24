# Play pages (PL07) — design

Date: 2026-10-17 · Branch: `slim` · Version: `PL07` (CTPlay) · Status: agreed with the user in conversation 2026-10-16 /
17; spec for review. Frame: `docs/ui-map.md`, "Planned page structure".

## Purpose

PL06's single play page becomes **a set of pages per track**, so every later feature has a place to live and the UI
stays the same whatever a build contains. PL07 builds the frame with two real pages (Chords, Arp), a **quick access**
view on Shift in the Note view, Shift-lit track buttons, and fixes the one PL06 device finding: recorded arpeggio
notes are one tick short. Settings change during play; nothing is saved (as PL06).

The user's workflow (2026-10-16): while playing they adjust all chord options (inversions keep a progression smooth,
shapes set the colour), and the arp's pattern, rate and latch while sketching; strum and the arp's octaves / gate are
set less often. They have not played PL06 long enough to be sure, so quick access must be easy to change after use.

Success:
- Shift + Synth 1 / 2, MIDI 1 / 2 opens that track's last-used page; ▲ ▼ step pages; Shift held on a page shows a
  table of contents; every PL06 setting is reachable, in the places below.
- Shift in the Note view shows the track's quick view; Shift + 1-16/17-32 flips Chords ↔ Arp.
- Recorded arpeggio notes have exactly their gate's length: at 1/16, k sixths = k ticks; 6/6 (legato) = the full step.
- With no page open and the default quick view, everything is as PL06 except the lit LEDs while Shift is held.
- Nothing is left sounding, and nothing is left held in stock's recorder, after any mix of pads, pages, views,
  Play / Stop, Record and latch.

## Decisions (with the user)

| # | Decision |
|---|---|
| D1 | Pages per synth / MIDI track, in a fixed order, each with a main colour: **Chords** (green), **Arp** (blue). Later pages (Keys, Pattern tools; drum and project pages) come with their features, not in PL07 |
| D2 | Shift + the track's button opens that track's **last-used page**. Track button alone, Note, Mixer, FX, Preset close it (as PL06) |
| D3 | **Table of contents**: Shift held on a page shows row 4 (pads 25–32), one pad per page: open page bright, other pages dim, pages this build lacks dark. Tapping one opens it. Rows 1–3 are dark while Shift is held. Shift + pad no longer picks a setting on a page |
| D4 | **▲ ▼** (Octave, ids 19 / 20) step to the previous / next page while a page is open; their LEDs show whether a page exists that way. Closed page: octave buttons as stock |
| D5 | **Quick access**: Shift in the Note view shows the track's quick view on pads 17–32 (pads 1–16 stay stock's). **Chords quick view = the palette** as today (strum not in it); **Arp quick view = the arp page's top half** (pattern row; rate · triplet · dotted · latch). **Shift + 1-16/17-32 flips** to the next quick view ("like switching sequencer pages", the user); its LED shows the view's page colour. Default Chords. Which rows are quick is one small table in the code |
| D6 | **Arp gate = one cycling pad, like stock's Gate view**: six lengths 1/6 … 6/6 of the arpeggio's step, 6/6 = legato; stock's colours (`0x63` full · `0x64` 5/6 · `0x65` · `0x66` · `0x67` · `0x68` 1/6), each press one sixth down, 1/6 → 6/6 |
| D7 | Recorded gates exact (the legato fix): note-offs reach the recorder after stock has counted the tick |
| D8 | **Shift-lit track buttons**: while Shift is held, Synth 1 / 2, MIDI 1 / 2 light in stock's Shift-function colour `0x2C`, as stock lights Note / Gate / Microstep |
| D9 | Strum moves to the Chords page. With an arp pattern on, strum's stored value shows dim and the other three strum pads dark (it is ignored); presses still store (rule 5; *my call*: dark, not dim, so the stored value stays visible) |
| D10 | **An arpeggio plays separate notes** (the user: "an arp is expected to play individual notes unless there's a specific control to tie arp notes together"): at 6/6 a pitch that sounds again on the next step is re-attacked, not tied (PL06 tied it) |

## Findings this design rests on (emulation, stock image, 2026-10-16)

- **Recorder:** a note's step unit is written once, at its note-off (`0x0803F88C`): length = ticks between note-on and
  note-off, as steps × 6 + sixths (6 ticks per 1/16 step at the default sync rate; capped at 16 steps; minimum 1).
  No snapping. Held stock pads: 15 / 40 / 80 / 170 / 330 ms at 94 BPM → 1 / 2 / 3 / 7 / 13 ticks.
- **PL06 records one tick short** (1/16 short / medium / long / legato → 1 / 3 / 5 / 5 ticks; 1/4 legato 23 of 24,
  confirmed on the device): `seq_tick` is an **entry** hook (`0x0802C418`), so the arpeggio's note-off goes out before
  stock counts that tick. Within one 1 ms service the `main_ms` dispatcher runs before the clock listener's tail call
  to the tick, so anything sent from the next `main_ms` is after the tick.
- **Recorder held-note list** (upstream SC43.2): `[0x2003C168 + 0xC + 4 t] + 0x54`, 12 B per note, byte 0 = note,
  byte 3 = 1 released. A note-on without its note-off leaves it held, and the recorder then ignores that pitch until
  Record is pressed again.
- **Stock's Gate view**: a partial last pad is `0x63` (6/6) … `0x68` (1/6); a press on it goes 6/6 → 5/6 → … → 1/6
  → 6/6.
- **Panel LEDs** (stock's map `0x08059438`): 32–39 = Synth 1, Synth 2, MIDI 1, MIDI 2, Drum 1–4; 40 = Preset;
  51 / 52 = Octave ▼ / ▲ (the active view's elements 32 / 33); 53 = 1-16/17-32. With Shift held stock turns 32–40
  off and lights Note / Gate / Microstep `0x2C`, Velocity `0x74`, and in the Note view Octave 51 / 52 `0x2C`.
- **Shift + Octave in the Note view is stock's**: it changes the pattern's notes (most likely a transpose). Shift +
  1-16/17-32 (id 21) never reaches stock (its Shift mask).
- `led_task`'s handlers get all 69 panel LEDs after stock (`out[0..68]`).

## 1. Pages

State (UI task): the open page's track (as PL06's `chord_page`), each track's **last page** and **quick view**
(2 bits each are enough: 1–2 B). Power-on: page Chords, quick view Chords.

Opening (Shift + track button) works as PL06's `page_open` (switches to the track's Note view first, from any view)
and shows the track's last page. Closing as PL06.

**Chords page** (green):

| Pads | Controls |
|---|---|
| 1–4 | **Strum** off · slow · medium · fast (white; D9) |
| 5–16 | dark |
| 17–32 | **The chord palette**: inversion 17–20, spread 21–23, bass 24, shape 25–32, same functions and colours as the Shift palette |

**Arp page** (blue):

| Pads | Controls |
|---|---|
| 1–8 | **Pattern**: off · up · down · up-down · down-up · random · as played · chord (as PL06) |
| 9–12, 13, 14, 15, 16 | **Rate** 1/4 · 1/8 · 1/16 · 1/32; **triplet**; **dotted**; dark; **latch** (as PL06) |
| 17–20 | **Octaves** 1–4 |
| 21 | **Gate** (D6) |
| 22–32 | dark |

**Table of contents** (D3): pad 25 Chords, 26 Arp, 27 Keys, 28 Pattern tools (dark in PL07), 29–32 dark. A press
on a dark pad does nothing.

**▲ ▼** (D4): ▼ = next page, ▲ = previous, no wrap (as stock's Preset view, upstream SC20+ `use_octleds`: LED 51
lights when there is a next one, 52 when there is a previous one). LED colour = the main colour of the page that way;
off when there is none. While a page is open the page takes ▲ ▼ with or without Shift, so a press meant for paging
never transposes the pattern underneath. Absent pages are skipped.

## 2. Quick access

With Shift held in the Note view (both Note-view layouts) and no page open, pads 17–32 show the track's quick view:
- **Chords**: the palette, exactly as PL06.
- **Arp**: the arp page's top half, drawn on pads 17–32 (pattern on 17–24, rate · triplet · dotted · dark · latch on
  25–32). Presses act as on the page.

Shift + 1-16/17-32 in the Note view flips the track's quick view to the next page that has one (Chords → Arp →
Chords). While Shift is held in the Note view, LED 53 shows the quick view's page colour. Elsewhere, and without
Shift, LED 53 is stock's. The quick rows per page are one table, so changing them later moves nothing on the pages.

## 3. Shift-lit track buttons

While Shift is held, in every view, the LED handler writes `0x2C` to panel LEDs 32–35 where stock left them off.
Drum buttons (36–39) stay off until drum pages exist. No RAM.

## 4. Arp gate and recorded lengths

Gate value: six steps, 1/6 … 6/6 (it fits the arp settings' second byte next to octaves). Default **3/6** (*my call*:
PL06's default was 25 %, closest to 2/6; half reads clearly as "the middle" on a downward cycle). PL06's 4 values are
replaced, not kept.

**Length** of each arpeggio note: k sixths of the arpeggio's step.
- Playing: counted in sequencer ticks: `k × rate_ticks / 6`, at least 1 and less than the step for k < 6 (*builder's
  call* how to round where that is not a whole number: 1/32 = 3 ticks, triplets). 6/6 = legato: a new pitch's
  note-on before the old note's note-off (PL06's order). **A pitch that sounds again on the next step is re-attacked**
  (D10): its note-off first, then its new note-on, so the recorder gets the full step and live matches playback
  (stock's player re-attacks each step).
- Stopped: the same fraction of the step in ms, from the project BPM (as PL06).

**Exact recording** (D7): while playing, everything an arpeggio sends on a tick (the step's note-ons, the note-offs
of the notes it replaces, a gate's end) goes out in the first `main_ms` service after stock has counted that tick
(≤ 1 ms later, inaudible), so the recorder counts every tick of a note and still places its note-on on the tick's step
(checked in emulation). Stopped, nothing records: steps and gates stay as PL06 (no delay). It must hold for every
rate, swing and latch, and never leave a note sounding (PL06's guarantees).

## 5. PL06 follow-ups taken in

- Strum's stored value shown dim while a pattern is on (D9).
- `page_on_pad` clears a stale `page_taken` bit for a press it passes on (as `chord_on_pad` does for `consumed`).
- User guide: the chord pattern plays at most the lowest 5 held notes.
- Tests: Shift + another track with pads held while a pattern is on; pattern off on the page while notes sound
  (through the page, not `set_arp`); after recording, nothing left on and nothing held in the recorder's list.

## 6. Budgets

RAM: PL06 uses 204 of 240 B; PL07 adds 1–2 B of page state plus any note-off queue. Stack: no handler deeper than
PL06's per context (Main 368 B, pad press 232 B) unless measured and shown against SL00D's headroom. Flash is not a
limit.

## 7. Testing

Emulation through the real routes (controller press / release, pads, the 1 ms service, the sequencer tick, Record):
- pages: open on the last page per track, ▲ ▼ (and their LEDs), the table of contents (bright / dim / dark, taps),
  Shift + pad on a page picks nothing, closing buttons; ▲ ▼ never reach stock while a page is open;
- every page control sets what PL06's control set (pattern, rate, triplet / dotted rules, latch, octaves, strum,
  palette);
- gate cycle: colours and order as stock's Gate view;
- quick access: both views on pads 17–32 in both Note-view layouts, the flip, LED 53, pads 1–16 untouched;
- Shift LEDs: 32–35 `0x2C` in several views, never overwriting a lit stock LED;
- **recorded lengths**: at 1/16 every k → k ticks; 1/8 and 1/4 legato → the full step; with swing; single note,
  triad, and the chord pattern (repeated pitches re-attacked, each on its own step at full length); then the
  recorder's held list empty;
- transparency against stock with CTPlay unused: as PL06's, now also allowing the Shift-held LEDs (32–35, 53) and
  treating Shift + 1-16/17-32 as claimed;
- the PL06 suite stays green where behaviour is unchanged (tests that used Shift + pad on the page or the old gate
  values move to the new controls).

Device test plan `firmware/PL07/TEST.md`, as PL06's (page frame, quick access, Shift LEDs, gate cycle against
stock's Gate view, recorded lengths in the Gate view).

## Not in scope

Keys, Pattern tools, drum and project pages; saving settings; choosing quick rows on the device; build-time quick
access options; the feature split; ITCM.
