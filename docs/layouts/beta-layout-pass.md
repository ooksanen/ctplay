# The beta layout pass (2026-11-10)

**Why now:** from the beta on, "fixed places" (ui-map rule 2) is a promise to public users. A page or a pad moved after
the beta moves under someone's fingers. So every remaining candidate gets a place now, even if it is built much later,
and the beta build carries the one move this pass makes. Mockups: `layouts-beta-pass.html` (from `gen.py`). Upstream reviewed up to RC4.11 / Beta 5.41 (2026-11-10).

## One slot, one kind of page
The table of contents (Shift held on a page, row 4) gets one meaning per slot on every kind of track:

| Slot | Kind of page | Synth / MIDI | Drums |
|---|---|---|---|
| 25 | what a pad plays | Chords (+ Chords 2) | **Levels** (later) |
| 26 | repeats in time while you hold | Arp | **Repeat** (moves from 25) |
| 27 | write a rhythm | Pattern tools (+ 2) | Pattern tools (+ 2) |
| 28 | write notes | Melody (+ Phrasing) | none (drums have no notes) |
| 29 | rework the pattern | **Vary** (later) | **Vary** (later) |
| 30–31 | free | | |
| 32 | set once | Keys | **Setup** (later) |

**The one move for the beta build: Repeat from drum pad 25 to 26.** Note repeat is the drums' arpeggiator (hold to
repeat at a rate, latch, velocity shapes) and both pages are blue; Repeat then sits next to Pattern tools, and
Pattern tools stays on 27 on every track. Cost: `page.c`'s drum table, the drum page order (▲ ▼: Repeat, Pattern
tools, Pattern tools 2, unchanged), `drum_page`'s slot value for Repeat (0 → 1: an alpha project that saved Repeat
has slot 0, which has no page, so it opens Repeat as today's fallback does; bump the field's `rev`), the guide, the
recipes, `ui-map.md`, CTCtrl if it shows the drum page (it is not linked).

## Every remaining candidate, placed

| Candidate (`candidates.md`) | Place | Notes |
|---|---|---|
| Semitone chord shapes | Chords pads 14–16 | Only if a spike gets past the router's scale snapping |
| Harmonizer / chord-follow, a custom chord | **Chords 2** (pad 25 again) | As the October sketch: which tracks follow, what they follow, a 12-semitone chord builder |
| Strummed release (PL19 idea) | Keys pad 5 | A toggle |
| MIDI in through chords and arp (upstream Beta 3.37: an external keyboard to the arpeggiator) | **Keys pad 7** | Per track: notes arriving on the track's channel play its chord and arp as a pad would. Upstream RC2.08 found where MIDI-in notes reach the input listener |
| MIDI in into a held step (upstream Beta 5.38) | **Keys pad 8** | Per track: hold a step, play an external keyboard, the notes go in (with step-entry chords: the chord) |
| Chord latch (upstream Beta 3.41) | **Arp page latch (pad 16), no new pad** | Today latch acts only with an arp pattern; with the pattern off, latch would hold the plain chord until the next press |
| A held chord follows a shape change (upstream Beta 3.41) | no pad | Behaviour: changing the shape while a chord sounds re-voices it at once. Check what CTPlay does now |
| Scale lock on MIDI in | **Keys pad 6** | Per track: MIDI in arrives per track channel. Check stock first (the router may already do it). Moved from the project page's sketch |
| Fourths layouts; Jankó | Keys row 2 (9–12) | scale (stock) · in-key fourths · chromatic fourths · Jankó (upstream has one) |
| Humanize, ratchets, mutate in key | **Vary** (29), both track kinds | Actions with Draft / Undo / Write, as Pattern tools. On a drum, what means nothing stays dark |
| Quantize | **Vary** | `candidates.md` said "on Pattern tools": it has no free pad, and the drums need it too |
| Nudge the pattern a step (upstream's Nudge) | **Vary** | ◀ ▶ on row 3, next to quantize and reverse |
| Reverse (a time transform) | **Vary** | Pitch transforms (shuffle pitches, mirror, contour shapes, phrase repeat) stay reserved on Phrasing 9–24: they are melody-only |
| Random-mutate per step | **parked** | The probability view's row 4 is trig conditions now; Vary's mutate covers the pattern-wide case |
| 16 levels | **Levels**, drum pad 25 | Repeat row 3 stays reserved for fixed velocity levels |
| GM drum notes | **Setup**, drum pad 32 | One choice for the kit: stock's notes · GM. Per-drum notes later if asked |
| Live transpose, split keyboard | Project page (Shift + Mixer) | As planned |
| USB merge (DIN In → USB) | Project page | A device-wide feel, saved with the project like the rest (the device record stays unused) |
| Note-track FILL | Drum expanded view pads 17–20 (+ 25 every track) | Reserved in PL20 |
| Mute on the next bar; solo (upstream Beta 5.9 / 5.12) | Mixer (upstream's places: Shift + a track pad; pad 16 held + tracks) | Low priority, performance. Check which Mixer presses stock ignores |
| Count-in click flash (upstream Beta 5.9) | no pad | Clear flashes on each click when the click's level is 0 |
| Pad velocity curve (upstream Beta 3.37) | Project page | A feel setting; upstream keeps it in Advanced Setup |
| Save waits until Stop (upstream RC4.05: stock's save while playing stutters the clock) | Project page | A toggle, off = stock's |
| "Shift = the tracks that sound" (upstream Beta 5.0 / 5.4) | **parked** | Clashes with CTPlay's Shift-lit track buttons (they show which tracks have pages) |
| Drum "avoid" (interlock) | **Decision needed** (below) | |
| Euclid mask mode, probability ghosts | **parked** | Pattern tools has no free pad; revisit with Vary |
| More trig conditions | **parked** | Shift + row 4 is full (8 specials) |
| Granular / Glitch, Master FX; upstream's synth work (FM, wavetable, patch morph, categories, stereo drum pairs, global velocity) | not CTPlay | Synth and DSP features, outside CTPlay's playing focus |
| Inverse chord (upstream Beta 5.9: mirrored down from the root) | parked, with "notes below the pad" | The same idea |
| Undo (general), chord recognition, "notes below the pad" | parked | As before |
| Stuck note, build tooling, uploader, CTCtrl | no pads | |

## Decisions (the user, 2026-11-10: all four as recommended)
1. **Repeat to drum pad 26, Levels to 25** (the table above). Decided; built 2026-11-11 (branch `beta`; `drum_page` is
   not linked, so no `rev` bump: an alpha project's 0 opens Repeat by the fallback).
2. **Vary on pad 29, shared by both kinds of track** (humanize, ratchets, mutate, quantize, reverse). Decided:
   it is the one home for pattern actions the drums can reach.
3. **Drum "avoid" (hats skip the kick's steps):** the only free pad that fits is the drums' Pattern tools pad 30,
   kept dark because it is dice notes' place on a note track (rule 2 across track kinds). Drums will never have notes,
   so that reservation protects nothing. Decided: allow it, as "where a control means nothing for a drum, a drum
   control takes its pad" (ui-map, drum Pattern tools) already says.
4. **Scale lock on MIDI in on Keys (per track)**, not the project page. Decided.
