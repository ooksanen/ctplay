# PL20 builder check, part A: storage (emulation, 2026-11-01)

For the spec [`../../specs/2026-10-28-trig-conditions-design.md`](../../specs/2026-10-28-trig-conditions-design.md),
"Storage", and the storage reading [`../2026-10-28-trig-conditions-storage.md`](../2026-10-28-trig-conditions-storage.md)
("Not confirmed" items 1 and 3). Stock image, Unicorn, the device RAM snapshot; every edit through its real route
(controller button / pad calls). Nothing here is checked on a device.

Run from `slim/`: `PYTHONPATH=.:tests:../tools:docs/investigations/2026-11-01-trig-conditions-spike ../.venv/bin/python
docs/investigations/2026-11-01-trig-conditions-spike/a_<name>.py`. Outputs are beside the scripts (`a_*.out`). Shared
helpers: `a_lib.py`. Q1 and Q2 take seconds; Q3 about 2 minutes.

Storage under test: drums = pattern `+0x84..+0xA7` (code byte `+0x88 + step`, one bit a step in `+0x84..+0x87`);
note tracks = step bytes [2] / [3] (`pattern + 28 × step + 2 / 3`). Patterns 1, 2, 3 below are 0-based 0, 1, 2.

## Real routes found

| Edit | Route (stock, by what the code does) | Function reached |
|---|---|---|
| Duplicate a pattern | Patterns view (button 13; columns = tracks 0-7, rows = patterns), Duplicate held + source pad + target pad (`0x080446E6` → command store → dispatcher `0x0802DBC0`) | drums `0x0803E2AA`, notes `0x0803D2B0` |
| Clear a pattern | Patterns view, Clear held + pattern pad | `0x0803E3B0`, `0x0803D310` |
| Clear a step | step view, Clear held + step pad | `0x0803E18A`, `0x0803D1D4` (→ fill `0x0803D230`) |
| Copy / paste a step | step view, Duplicate held + step A, then step B | `0x0803DF72` / `0x0803DFAE`; `0x0803D132` / `0x0803D16E` |
| Copy 1-16 → 17-32 | step view, Duplicate held + 1-16/17-32 | `0x0803E93A`, `0x0803DD24` |
| Mutate | Shift + Duplicate | `0x0803E6F0`, `0x0803D53C` |
| Probability | Pattern Settings twice (or Shift + Pattern Settings) = mode 5; step pad, then row 3 | drum / note step store commit |

No Nudge in stock: the dispatcher's other two per-track ops (`0x0803D3B8` / `0x0803D43E`, `0x0803E52C` /
`0x0803E606`) clear or set automation lanes and the drum flip byte, not step positions.

## Q1. Duplicate and the condition bytes (`a_q1_duplicate.py`)

Drum 1 and Synth 1, pattern 1 → pattern 2, each pattern with its own distinct bytes; stopped and playing, with pattern
1, pattern 2 or neither the track's shown pattern. Also drum 1 → drum 2 and Synth 1 → Synth 2.

| Case | Drums `+0x84..+0xA7` | Notes [2] / [3] |
|---|---|---|
| Stopped (any shown pattern: stock first makes the target the shown one) | **not copied: the target keeps its own old bytes** | copied |
| Playing, the target is the shown (playing) pattern | **not copied: target's own kept** | copied |
| Playing, the source is shown, the target not | copied | copied |
| Playing, neither shown | copied | copied |
| Drum 1 → drum 2, stopped / playing (target not shown) | not copied / copied | — |
| Synth 1 → Synth 2, stopped | — | copied |

The 4 arrays (`+0x00..+0x83`) and lanes (`+0xA8..`) are copied in every case; the source is never changed.

- **Confirms the static reading** (`0x0803E2DC`: target == shown → step store + lane memcpy + settings store, no
  `+0x84..+0xA7`; else one memcpy of 0x6A8). Confidence: high (emulation).
- **Sharper than the spec's wording.** The spec says "Duplicate `0x0803E2AA` (stopped, the target is the shown
  pattern: copy the bytes too)". The drop happens whenever the target is the shown pattern at `0x0803E2DC`: always
  when stopped, and also while playing when the target is the pattern the drum shows. The hook should test that
  branch (target == shown), not "stopped". The source can be another drum's pattern (`r1`).
- **Not copied means stale, not zero:** the new hits get the target's old conditions. So the hook matters even with
  the "drop a condition on a step with no hit" fallback.
- Note tracks: `0x0803D2B0` always copies 0xCA8 B and reloads the store when the target is shown (the store's word 0
  then matches the pattern). Nothing to hook.

## Q2. Which stock edits keep, clear or move the bytes (`a_q2_drums.py`, `a_q2_notes.py`)

Every step had a distinct code (drums: also its bit; notes: a distinct [2] / [3]); hits had distinct velocities so a
moved hit can be traced. Each edit is followed by a stock edit of the same step (a step pad, step entry or a
probability press). "Kept" = the step's own bytes stay at that step position.

**Drums** (drum 1, pattern 1 shown, stopped unless said):

| Edit | Condition bytes | Then a stock edit of the step |
|---|---|---|
| Clear step (a hit) | kept (on the now empty step) | step pad re-adds a hit: it has the old condition |
| Clear pattern, shown (stopped) / not shown (playing pattern 3) | kept, all 32 codes and bits | step pad: kept |
| Copy 1-16 → 17-32 | **not copied**: steps 17-32 keep their own codes (hits copied) | step pad on 17-32 (shown after the copy): kept |
| Paste step 3 → 8 | **not copied**: step 8 keeps its own code (hit copied) | step pad: kept |
| Mutate | **not moved**: all codes stay in place while hits move (e.g. 2 → 14, 5 → 25) | step pad: kept |
| Add a hit / remove a hit (step pad) | kept (a removed hit leaves its condition on the empty step) | — |
| Probability view (row 3) on a hit; on an empty step (stock makes a hit) | kept | — |
| Velocity view press | kept | — |
| Live recording (expanded view, Play + Record, 32 hits; recorder write `0x0803FA26`) | kept on all 32 steps | — |
| Drum editor write-back `0x0803EA1C` (runs on every step-store commit above) | kept: it writes the 4 arrays only | — |

Never zeroed, never junk. **Confirms the static reading** (stock never touches `+0x84..+0xA7` outside Duplicate's
memcpy). Every "kept" for Clear / copy / paste / Mutate is what the spec's hooks must change. Confidence: high.

**Note tracks** (Synth 1, pattern 1 shown, stopped unless said):

| Edit | [2] / [3] | Then a stock edit of the step |
|---|---|---|
| Clear step (selected step or another) | **kept** (not cleared) | step entry, then probability: kept |
| Clear pattern, stopped / playing pattern 3 | **kept**, 32 / 32 | step entry: kept |
| Step entry: add to a step with notes / to an empty step / remove (key again) | kept | probability: kept |
| Recording over a step (Play + Record, key held 1 step; recorder commit) | kept | probability: kept |
| Paste step 3 → 8 | copied (step 8 = step 3's) | probability: kept (still step 3's) |
| Copy 1-16 → 17-32 | copied (17-32 = 1-16; 1-16 kept) | — |
| Mutate | moved with the step's notes (15 steps moved, all consistent) | — |
| Duplicate (Q1) | copied | — |

Never zeroed, never junk. Clear step goes through the step store (`0x08035456` touch-all → fill on the store's write
buffer → commit), so the spec's one hook on the fill `0x0803D230` (zero bytes 2-3 of `r1`) covers Clear step and Clear
pattern both. **Confirms the static reading and the spec.** Confidence: high.

**The selected-step catch, confirmed:** a raw [2] / [3] write to the editor's selected step with the store not synced,
then a probability press without pressing the step pad: [2] / [3] go back to the store's stale word 0 (here zeroed).
With the step pad pressed first, or with the write through the store (write pointer + commit), kept. The spec's rule
(the selected step through the store) is right.

**Not in the spec (gaps to decide):**
- **A removed hit or note leaves its condition.** Drums: a step pad turning a hit off, Clear step, and the probability
  press that makes a hit on an empty step keep the code, so a hit added later inherits the old condition. Notes: step
  entry removing the last note keeps [2] / [3] (Clear step too, until its hook). The spec hooks Clear but not the step
  toggle (`0x0804EC3E` drums) or a note removal. Either clear on removal, or rely on "a condition on a step with no
  hit / note is dropped" when CTPlay writes or reads it.

## Q3. No stock reader of the bytes (`a_q3_readers.py`)

One scenario, three runs: clean (bytes 0), filled (all 32 drum patterns' `+0x84..+0xA7` and every note step's [2] /
[3] of all 32 note patterns), filled with a memory-read watch. Content in every pattern (16 steps, probabilities
below always on some steps), every track chained over patterns 1-2; Play (real button, Main's 1 ms service: 778
ticks in all, 4 + 2 + 2 passes), edits while playing (drum hit, step entry, two probability presses), Stop, edits
stopped (drum and Synth 2 Clear step, MIDI 1 step entry, a drum 4 hit), Play from stop, Stop, Save (Save twice).

| Compared (clean vs filled) | Result |
|---|---|
| Synth / MIDI endpoint note events (1 102), drum player note-ons (187), DSP writes, tick count | identical |
| Every pattern outside the condition bytes; pattern-writer calls | identical |
| Condition bytes after the run (filled) | unchanged, 32 / 32 drum patterns, 32 / 32 note patterns |
| Condition bytes after the run (clean) | still 0 |

**Reads of the condition bytes** (watch on, every phase):
- **Drums: none.** No stock code read `+0x84..+0xA7` during playback, edits, Stop, Play or Save.
- **Notes: one reader, the note editor's refresh `0x0803DC62`**: memcmp of the selected step (28 B) against the step
  store (`lr 0x0803DC91`), then on a difference memcpy of the step into the store (`lr 0x0803DCC1`) and a commit with
  the editor detached. It runs about once a step while playing (~107 compares and ~97 copies a track over 6 passes of 16
  steps; that the selected step follows the playhead is my reading of those counts, not traced) and on a step
  selection. It only mirrors the bytes; nothing acts on them. It is also
  why a raw write to the selected step survives once the step is selected again (Q2).
- Playback itself reads note steps by byte ([0], [1], the slots): no player PC touched [2] / [3].
- Save read none of the bytes: the save (`0x0802FDF8`) stamps the record and posts the write; the patterns are inside
  the session record (drums `record + 0xCD74`, notes `record + 0x2E4`) and the file write runs in a task the harness
  does not run (as `tests/test_saved.py` says). Saving the bytes rests on the record being written whole (upstream
  SC403D on the device).

**Confirms "Not confirmed" item 3** for stock, in emulation. Confidence: high for these routes; a computed-offset
reader on a route not run here (Components / SysEx export, project load, scenes) is not excluded.

Harness note: Unicorn 2.1.4 stops with "invalid instruction" when a memory-read hook fires on a load inside an IT
block. Stock's memcmp `0x08025180` and memcpy `0x0801AA14` / `0x0801AA34` have such loads, so the watch run does those
three in Python and logs their reads against the caller. The watch run's outputs match the plain filled run exactly.

## Summary for the plan

- Drums need every hook the spec lists (Duplicate when the target is shown, Clear step / pattern, copy 1-16 → 17-32,
  paste step, Mutate): stock never copies, clears or moves `+0x84..+0xA7` except Duplicate's whole-pattern memcpy.
- Note tracks need only the fill hook; every copy and move already carries [2] / [3].
- Neither place has a stock reader that changes playback; the only note reader is the editor's mirror refresh.
- Open for the spec: Duplicate's hook condition (target == shown, playing too), and what a removed hit / note does to
  its condition.
