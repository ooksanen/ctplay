# Euclidean generator — design draft

Date: 2026-10-17 · Branch: `slim` · Status: **built as `PL11`** (2026-10-18, `docs/plans/2026-10-18-euclidean.md`), passed on the device 2026-10-18; Q1-Q3 answered by the user 2026-10-17 (note tracks
first; a hit plays the last pad; Write replaces the current pattern after a confirm). Frame: `docs/ui-map.md` (planned Pattern tools page), `docs/candidates.md` ("Euclidean fills").

## Purpose

Fast rhythm sketching: pick how many hits a pattern has and the Circuit Tracks spreads them as evenly as possible over
the pattern's steps (the Euclidean rhythm: 3 in 8 = the tresillo, 5 in 16, 7 in 16 …), rotate it, and write it into a
pattern. What comes out is ordinary steps, so it plays, edits and saves as stock's, and plays the same on the official
firmware.

Success: in a few presses, from any synth or MIDI track, a new pattern with an even rhythm of k hits, rotated where you
want, with the notes you chose; the pattern you were in is untouched.

## Proposal

### Where: the Pattern tools page

The fourth page of a synth or MIDI track (table-of-contents pad 27 since the page slots of 2026-10-18, first planned at 28, **orange** `0x45` / `0x46`, my call), as
`ui-map.md` planned. It holds pattern actions; humanize and mutate join it later (bottom half). No quick half.

| Pads | Control |
|---|---|
| 1–16 | **Hits and preview.** Pad k = k hits (one pad per value, rule 3). The pads show the rhythm that would be written: hit steps bright, the other steps dim, steps past the pattern's length dark. So pressing pad 5 lights five pads, spread out |
| 17 · 18 | **Rotate** ◀ · ▶ (one step per press; the preview moves) |
| 19 | **Rotate to the first hit**: back to rotation 0 |
| 21 | **Gate** of the written notes: a cycle pad as the Arp page's (1/6 … 6/6, stock's Gate-view colours) |
| 22–24 | **Velocity**: soft · medium · hard (or "accent the first hit": open) |
| 31 | **Undo**: the pattern as it was before the last Write (lit while there is one) |
| 32 | **Write**: press once, it blinks; press again, the rhythm replaces the current pattern (ui-map: actions take two presses) |
| 20, 25–30 | free (humanize, mutate later) |

### What it writes

- **Length:** the pattern's own length, from stock's Pattern Settings (start / end points; pattern tail `+0x380`, to be
  confirmed), so a 12-step pattern gets k hits in 12 steps. Polymeters come from stock's own control: different
  lengths on different tracks. 32-step patterns: the preview shows the page stock's 1-16/17-32 shows (*builder's
  call*).
- **Notes** (user, Q2: the last pad): **the last pad you played on the track**, as it sounds now: with
  the chord engine on, every hit is that chord (Euclidean chord stabs), with chords off a single note. Before any pad
  was played, the project's root note.
- **Where** (user, Q3): **Write replaces the current pattern, with a confirm** (two presses: "to minimize accidental
  overwrites"), and **Undo** restores what it replaced (one copy, until the next Write; my call, kept in ITCM). Live
  draft was considered and set aside. Background: With ITCM (about
  15 KB, `specs/2026-10-17-itcm-opt-in-design.md`) one copy of a pattern (0xCA8 = 3,240 B) fits, so replace can have an
  undo. Two ways on the table:
  - **live draft**: on the page, every change (hits, rotate, gate, velocity) rewrites the current pattern at once, so
    it is heard while it plays; the first change keeps a copy of the pattern as it was; a **Revert** pad brings it back;
    leaving the page keeps the result (the next visit takes a new copy). No Write pad;
  - **Write + Undo**: Write (two presses) replaces the current pattern; Undo restores what it replaced.
  The earlier "next empty pattern" rule of ui-map stays possible as a later option.
- **Steps:** each hit step gets the notes at the chosen velocity and gate, microstep 0, probability as stock's
  default; non-hit steps stay empty.

### The rhythm

Hit at step i (0 ≤ i < n, rotation r) when `((i + r) · k) mod n < k`: the Bresenham form (the same rhythms as
Bjorklund's algorithm, up to rotation), a few lines of C and no tables. k = 0 writes an empty pattern (or is refused:
*builder's call*); k ≥ n fills every step.

### Settings

Per track, RAM only: hits (5 bits), rotation (5 bits), gate (3 bits), velocity (2 bits), the last played pad's note
(1 B): about 3 B per track, 12 B. **PL08 has 4 B of RAM left**, so this comes after the ITCM opt-in (being designed:
`specs/2026-10-17-itcm-opt-in-design.md`). Saved with the other settings once saved settings exist.

## Findings (spike 2026-10-18, stock image in the slim harness; no product code)

- **The current pattern** of note track t (0-3) = parameter 0 of the store `[0x20038EC0 + 0x30 + 4 t]` (the engine):
  it follows the Patterns view (a pad, Shift + pad) and playback (upstream `tools/playmode.py` `c_pmtp`).
- **Where a pattern is:** in the session record, so stock saves it as it is: Synth 1 / 2 at record + 0x2E4 + (8 t + p)
  × 0xCA8, MIDI 1 / 2 at record + 0x1A27C + (8 (t − 2) + p) × 0xCA8 (upstream `tools/patchain.py`; `tests/notes.py`
  `PATTERN_BASE`). 32 steps × 28 B (0x380 B), then 40 settings bytes at + 0x380: **byte 0 = last step, byte 1 = first
  step** (0x0F / 0x00 in a new pattern), byte 2 = 3 (not used here); bytes 4-7 zero in stock (upstream's chain rules).
  The rest of the 0xCA8 (automation) is not touched.
- **A step:** [0] mask of the 6 units, [1] probability (**7** in every empty step = stock's default), [2-3] 0, then 6
  units of 4 B: note, length | tie << 7, microstep, velocity. An unused unit is `00 00 00 60`.
- **Note values** are keyboard pitches (root-relative + 12), the space the chord engine computes in: pad 24 = 72,
  recorded as 72, sent as MIDI 60 with root C.
- **Length is in sixths of a step:** a 3 played 80 ms at 94 BPM (a 1/16 step 160 ms); stock's own 2 → 53 ms; a 0x3C =
  ten steps.
- **Raw step writes play** through stock's sequencer with no notification (as PL08's spike and upstream's quantise,
  `tools/quant.py`, which writes note-track steps raw), and stock's Patterns view lights a slot the same with or without
  notes. **Correction (PL11 device step 9, 2026-10-18):** the Note view keeps its own copy of which steps hold notes,
  so after a raw write its step pads stay stale until a project load. A Write and an Undo now call the recorder's store
  touch (`rec_touch`, `0x0803F8D4`), as the recorder does after each commit.

## Decided at planning (2026-10-18, builder's calls; the user reviews them with the plan)

- **Length n** = last − first + 1 (first and last swapped if first > last), from the target pattern's settings, read
  at every frame; hits on steps first … last. **Write replaces all 32 steps**: hits inside the range, every other step
  empty. Settings bytes and automation stay.
- **k = 0** (nothing picked yet) leaves Write dark and doing nothing; pads 1-16 give k = 1-16; k ≥ n fills every step.
- **Preview of a pattern longer than 16 steps:** pads 1-16 show its first 16 steps (no page flip on the Tools page).
- **Rotate:** ▶ (pad 18) moves the hits one step later, ◀ (pad 17) one earlier, pad 19 back to rotation 0
  (step `first` is a hit); stored 0-31, used mod n.
- **Velocity** soft · medium · hard = 48 · 96 · 127 (96 = stock's fixed velocity); default medium. **Gate** default 3/6.
- **Notes:** the track's last played pad (its keyboard pitch, remembered by the chord engine's pad hook, chords on or
  off; RAM only, 72 before any pad) with the track's chord settings at the Write: the pad and its chord_notes(), at most
  5 units. Microstep 0, no tie, probability 7.
- **Write** targets the pattern the track plays at the second press. First press arms (pad 32 blinks, orange blink
  `0x47`: an animated code, on purpose); any other pad of the page, or leaving the page, disarms. The copy and the
  write run with interrupts masked (about 1.8 K byte moves), so the Main task's sequencer never reads a half-written
  pattern.
- **Undo** (pad 31) keeps the replaced 32 steps (0x380 B, not the whole 0xCA8) and where they came from, in ITCM; it
  swaps them back, so a second press redoes. Lit (blue) on the page of the track it belongs to; a project load or a new
  project drops it.
- **Writes run on the pad's release** (PL13, device finding 2026-10-20). A pattern write during a press, finger still
  down, often made a phantom press on the next pad (PL11's Undo armed the Write about half the time). The pads are
  read through a 74HC4051 analog multiplexer into the ADC; the long masked write probably delays the scan, so pad
  p's pressure is read into pad p + 1's slot. Write's second press and Undo now set a pending action; the pad's
  release runs it (the arming press writes nothing and stays on the press). See the melodic generator spec, Draft.
- **Settings saved** with the project (saved settings exist since PL10): 2 B per track, `euclid_cfg[4][2]` = [0] hits
  (bits 0-4) | velocity (bits 5-6), [1] rotation (bits 0-4) | gate (bits 5-7, sixths − 1), appended to
  `save_layout.lock` (payload 25 → 33 B). The last played pad and Undo are not saved.
- **Code:** inside the chord feature (the pages live there): `euclid_math.c` (the rhythm, pure) and `euclid.c` (the
  page, the write, Undo).

## Alternatives considered

- **Euclid as a mask on the current pattern** (keep only the steps on the hits): keeps the pattern's notes, but it is
  destructive in place, and on a sparse pattern most hits fall on empty steps. Possible later as a second action.
- **Live Euclid** (generated at playback, not written): needs the playback hook and changes what the pattern holds vs
  what plays; it would not play on stock and needs saved settings for every track. The writer is simpler and
  stock-compatible.
- **Drum tracks first** (user, Q1: **note tracks first**): Euclidean rhythms are at home on drums. But drum pages (Shift + Drum
  1–4) do not exist yet, the drum pattern format is another, and drum patterns have an editing copy that overwrites raw
  writes (upstream SC43: writes must go through upstream's `drumstore` route). Note tracks reuse everything PL06–PL08
  built (pages, the pattern format, PL08's spike: raw step writes on note tracks stick). My proposal: note tracks
  first, drums as the second step with the drum pages.

## Left to the builder

*Answered by the spike and the planning decisions above (2026-10-18).*

- How stock is told a pattern changed (so it saves it, and the Patterns view shows the slot as used): PL08's spike saw
  the recorder's commit touch its pattern store (`0x0803F8D4`); a pattern writer needs the same.
- Writing while the target pattern plays (it is a free slot, so normally not: check chained patterns).
- The preview when the pattern is longer than 16 steps; the Write blink code (an animated code on purpose).

## Testing

Emulation: the rhythm against a Python model for every n ≤ 32, k ≤ n, r < n; the page (LEDs, presses, the two-press
write); the written pattern through stock's own playback (notes at the right ticks) and a stock edit afterwards;
no free slot; the source pattern unchanged. Device: write a few rhythms, play them, save and reload the project, load
it on stock firmware.

## Open questions for the user

1. ~~Note tracks or drums first~~: note tracks (user, 2026-10-17).
2. ~~What a hit plays~~: the last played pad, with its chord (user, 2026-10-17).
3. ~~Where Write puts it~~: replaces the current pattern after a confirm (two presses); Undo restores it (user,
   2026-10-17; Undo my call).
