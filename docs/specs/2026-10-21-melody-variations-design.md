# Melody variations (PL14) — design

Date: 2026-10-21 · Branch: `slim` · Status: **built as `PL14`** (2026-10-21; plan `plans/2026-10-21-melody-variations.md`; **passed on the device 2026-10-23**, `firmware/PL14/TEST.md`). Builder check done 2026-10-21; its four questions settled as *my call*s below. Builds on PL13's melodic generator
(`specs/2026-10-19-melodic-generator-design.md`) and PL11's Euclid writer (`specs/2026-10-17-euclidean-design.md`).
Research: `research/2026-10-19-melodic-generators.md`. Goes into `versions/PL14.toml` (which already holds two small
fixes, commit `1e54bc8`).

## Purpose

PL13 writes a line from a rhythm and a note rule. The user (2026-10-21) wants more varied results from it, and note
ties: "things that would give the user more options for more varied melody generation", for example random masking, or
stacking two rhythms and keeping the hits present in both. Pattern tools' Euclid works well for drums as it is, so
melody-specific controls stay off it; rhythm controls may join it.

This build adds five tools, all written into the pattern as ordinary stock steps (they play the same on official
firmware):

1. **A second rhythm, combined with the first**: keep the hits in both, in either, in one but not both, the first
   rhythm without the second, or the first rhythm accented where the second hits.
2. **A short cycle**: the first rhythm over 3, 5, 6 or 7 steps, repeated across the pattern, so it drifts against the
   bar (riffs).
3. **Thinning**: drop about a quarter, a third or half of the hits at random (the rhythm dice re-rolls which).
4. **Ties**: some hits hold the previous note instead of striking a new one, so notes last two or more hits.
5. **Octave jumps**: some notes of the line jump an octave.

And the groundwork they need: **a second saved block** (the 64 B block is full) and **pages that span two screens**
(the rules below).

**Success:** from a plain PL13 line, a few presses give clearly different lines that still fit the chord and the
groove: sparser, syncopated, riff-like, with long notes and jumps. Any of it undoes with Undo, and a project saved
with it reloads with it.

**Non-goals:** transforms of the current pattern (shuffle, reverse, mirror: later, on Melody's second page), contour
shapes, phrase repeat, ghost notes at a stock probability, slides (different pitches joined: stock's tie joins only
the same pitch; an overlap trick would depend on the patch), drum tracks (PL15: drum pages and their own rhythm tools).

**Anti-goals:** any change to what a PL13 Write writes while every new setting is off (byte for byte); losing a
project's CTPlay settings in a build that does not know the new block; a control you cannot read without a screen;
moving a control a PL11-PL13 user has learned, unless this spec says why.

## Layout review: split, and what moves

The user asked whether the controls should be extended or split now, while moving them is cheap (one user). The five
tools need about 25 pads. Free today: Pattern tools 25-28, Melody 15-16. So:

- **Split:** Pattern tools and Melody each get a **second page**. Pattern tools' second page is the second rhythm and
  how it combines (rhythm controls, fine for drums later); Melody's second page is **Phrasing** (ties, octave jumps;
  later transforms, contours, phrase repeat).
- **Moves:** only one reservation. Pattern tools pads 25-28 were kept for transforms; they become the **cycle** row.
  Transforms (pitch shuffle, mirror) are melodic, so under the user's rule they belong on a Melody page: their
  reserved place moves to Phrasing rows 2-3. No built control moves.
- **Kept where they are (considered and left):** dice notes on Pattern tools pad 30 (the action row is the same on
  every page of the group: rule 2); accent on Melody pad 14 (a velocity rule, but PL15's drum pages will have their
  own); gate "to the next hit" and the rhythm source on Pattern tools (they are rhythm and length, not pitch).

### Pages that span two screens (new rule for `ui-map.md`)

A feature that outgrows its page gets one more page (at most two per feature in this build; the rule allows more
later), not overflow by rows: scrolling would move every control and break rule 2, and with no screen the user could
not tell how far it had scrolled.

- **Same table-of-contents pad.** A feature's pages share its one pad in the table of contents. Tapping a feature's
  pad opens the page of it used last; tapping the pad of the page already open steps to its other page. (Pad 27 =
  Pattern tools 1 / 2, pad 28 = Melody / Phrasing.) The table of contents keeps one pad per feature, so its eight pads
  last longer.
- **▲ ▼ walk every page in order:** Chords, Arp, Pattern tools, Pattern tools 2, Melody, Phrasing, Keys (dark ones
  skipped).
- **Same main colour, same action row.** Both pages of a feature use its colour; pads 29-32 stay the four actions on
  all four writing pages.
- **Saved:** the feature a track was on stays `page_slot[t]`, unchanged (the table-of-contents slot 0-7). Which page
  of each feature was used last is a new saved field, **`page_sub[4]`** (1 B per track: bit 0 = Pattern tools on its
  second page, bit 1 = Melody on Phrasing, bits 2-7 spare, 0). So a project left on Phrasing reopens on Phrasing in
  PL14, and on Melody in PL11-PL13 (they ignore the new field) (*my call*: keeping `page_slot`'s values as they are
  means an older build never lands on Chords because of a page it does not have).
- The draft (PL13) lives while the track's pages stay open, as now: the new pages are pages of the same track.

## UI

### Pattern tools (pad 27, orange), page 1 — changed pads only

| Pad | Was | Becomes |
|---|---|---|
| 1–16 | hits, and the preview of the rhythm | unchanged, but the **preview shows the final rhythm**: what Write writes, after the cycle, the combine and the thinning. With every new setting off that is PL13's preview |
| 25–28 | free (transforms reserved) | **Cycle** (one pad per value, none lit = the whole pattern): 3 · 5 · 6 · 7 steps. Tapping the lit pad turns it off (as the Arp's triplet / dotted) |

### Pattern tools page 2 (pad 27 again, orange): the second rhythm

| Row | Pads | Control |
|---|---|---|
| 1–2 | 1–16 | **Second rhythm: hits** (pad k = k hits) and **its own preview**, in white (hit `0x01`, no hit `0x02`, past the pattern's length dark), so the two pages do not look alike |
| 3 | 17–19 | **Rotate** the second rhythm: earlier · later · back to the start (as page 1) |
| 3 | 20–24 | **Combine** (one pad per value, none lit = off, tapping the lit pad turns it off): **both** (only the hits in both) · **either** (the hits of either) · **one, not both** · **first without second** (the first rhythm, except where the second hits) · **accent** (the first rhythm as it is, played hard where the second hits) |
| 4 | 25–27 | **Thinning** (none lit = off): drop about 1 in 4 · 1 in 3 · 1 in 2 hits |
| 4 | 28 | *free* |
| 4 | 29–32 | Dice rhythm · dice notes · Undo · Write (as page 1) |

With Combine off the second rhythm does nothing (its pads still set it). The second rhythm is always Euclid, over
the whole pattern (*my call*: one source and one cycle keep it readable; the first rhythm has both).

### Melody (pad 28, yellow): unchanged.

### Phrasing (pad 28 again, yellow): Melody's second page

| Row | Pads | Control |
|---|---|---|
| 1 | 1–3 | **Ties** (none lit = off): about 1 in 4 · 1 in 3 · 1 in 2 hits tie to the note before |
| 1 | 4 | *free* |
| 1 | 5–7 | **Octave jumps** (none lit = off): about 1 in 4 · 1 in 3 · 1 in 2 notes of the line jump an octave |
| 1 | 8 | *free* |
| 2–3 | 9–24 | *free* (reserved: transforms, contour shapes, phrase repeat) |
| 4 | 25–28 | *free* |
| 4 | 29–32 | Dice rhythm · dice notes · Undo · Write |

The amounts are the same three on every row ("about 1 in 4 · 1 in 3 · 1 in 2"), so they read alike. Colours of the
new rows: the builder's, steady codes (not one of the 35 animated codes, CLAUDE.md), checked in emulation against
stock's LEDs; bright = selected, dim = not.

## What gets written

PL13's Write with three steps added. Order of work: **the rhythm** (first rhythm with its cycle → combine with the
second → thinning) → **the line** (PL13's orders over the final hits, with ties and octave jumps) → **the steps**
(PL13's step writing, with the tie flag).

### Rhythm

- **First rhythm**, as PL13 (Euclid or groove, k hits, rotation, the rhythm seed), but over the **cycle** c when one
  is set: worked out over c steps (k hits; k ≥ c fills all c), rotated within the cycle, and repeated from the
  pattern's first step to its end (the last repeat cut off). A cycle of c ≥ n is the whole pattern. Groove over a
  cycle uses its weight table's first c steps (*my call*).
- **Second rhythm:** Euclid, k₂ hits over the whole pattern, its own rotation.
- **Combine:** both = first AND second; either = OR; one, not both = XOR; first without second = first AND NOT
  second; accent = the first rhythm unchanged, its hits on the second's steps accented. Accent from Melody's accent
  setting and from Combine add up (either one makes a hit hard).
- **Thinning:** each hit is dropped by chance (about 1 in 4, 1 in 3, 1 in 2), drawn from the rhythm seed. The first
  hit of the pattern is never dropped, so at least one stays (*my call*).
- **Dice rhythm** rolls the rhythm seed, as PL13: in Euclid it also picks the first rhythm's rotation; it re-draws the
  thinning. The second rhythm is set by hand only (*my call*). PL13's rule stays: a dice press always changes
  something audible when anything can change (the seed steps on until the final rhythm differs).
- **No hits left** (e.g. "both" with nothing in common): Write writes nothing and its pad is dark, as with k = 0.

### The line

- PL13's orders walk the pool over the final hits, as now.
- **Ties:** each hit after the first may tie (chance from the row, drawn from the notes seed). A tied hit **holds the
  note before it**: same pitch (or the same chord in order "same"), not struck again, so the note sounds from the
  earlier hit to the end of the tied hit's gate. **The line does not advance on a tied hit**: the next untied hit plays
  the note the order would have played next, so ties change the rhythm you hear, not the tune (*my call*). A tied hit
  is never accented (it has no attack), and **Melody's accent rules count struck notes only**: "first hit" is the first
  struck note, "every 3rd hit" every 3rd struck note, so the accents follow what you hear (*my call*; "on the beat"
  is by step, as PL13, and a tied hit on a beat stays unaccented). Ties work in every order, "same" included.
- **Dice notes in order "same"**: dark and rolling nothing, as PL13, while ties are off. With ties on it lights and
  rolls the notes seed, which re-draws the ties (*my call*: otherwise ties in "same" could never be re-rolled). The
  PL14 fix of commit `1e54bc8` (a press that changes nothing keeps a draft's pending re-write) still covers dice notes
  in "same" with ties off.
- **Octave jumps:** each untied hit of a line order (not "same", not the first hit) may jump: its note + 12; when that
  is outside stock's playable range, − 12; when both are, unchanged. Chance from the row, drawn from the notes seed.
- **Dice notes** rolls the notes seed, as PL13; it re-draws ties and jumps too, and still steps on until the written
  result (notes, ties, jumps) differs.
- The three random draws (thinning, ties, jumps) must not move each other: changing the tie amount must not change
  which hits were thinned or which notes jump. The builder derives separate streams from the two seeds.

### The steps, and how a tie is written

Stock's step format (`docs/NOTAS.md`, "Formato del patrón"): each note unit is (note, length | tie << 7, microstep,
velocity). Stock's player passes the tie bit to its note-on (`0x08040FA2`), which does not strike a note that is
continuing a tie (its mask at `this + 0x128`); stock's Micro Step view sets the bit with its Tie pad.

- **Wanted sound:** a tied pair is one note: struck once at the first hit, ending where the tied hit's gate ends.
- **Preferred way:** the earlier unit gets the tie bit, the tied hit's unit the same pitch; so stock shows and edits
  the tie as its own (Micro Step view). The builder confirms in emulation, through stock's player, that this gives one
  note-on and one note-off at the right ticks, for hits on neighbouring steps and hits several steps apart, and decides
  the earlier unit's length (up to the tied hit, or its own gate).
- **Fallback** if stock's tie does not reach across empty steps: the earlier unit becomes one long note up to the end
  of the tied hit (capped at 96 sixths, stock's longest), and the tied hit's step stays empty. If the tie bit works
  for neighbouring steps but not across a gap, **one Write may use both** (*my call*: the sound comes first; the Micro
  Step view then shows some ties as ties and others as long notes, which the user guide says). Record in the plan
  what emulation showed.
- With every new setting off the steps are PL13's, byte for byte.

## Settings and saving

### New fields (per track, saved with the project, sent over the CTCtrl link)

- **`rhythm_cfg[4][3]`** (12 B): [0] second rhythm's hits 0-16 (bits 0-4) | combine (bits 5-7: 0 off, 1 both,
  2 either, 3 one-not-both, 4 first-without-second, 5 accent); [1] second rhythm's rotation (bits 0-4) | thinning
  (bits 5-6: 0 off, 1 ¼, 2 ⅓, 3 ½) | bit 7 spare (0); [2] cycle (bits 0-2: 0 whole, 1-4 = 3, 5, 6, 7) | bits 3-7
  spare (0).
- **`melody_vary[4]`** (4 B): ties (bits 0-1: 0 off, 1-3 the amounts) | octave jumps (bits 2-3) | bits 4-7 spare (0).
- **`page_sub[4]`** (4 B): which page of each feature the track used last (see "Pages that span two screens").
- **`euclid_last[4]`** (4 B, PL11's last played pad): **now saved**. PL13 left it in RAM only because the block was
  full; with the second block a "last pad" root reloads with the project.
- Defaults 0 (everything off); `euclid_last` 72, as now. `saved_fix` sends any value out of range back to its default,
  field by field, as PL13 does. Payload 53 → 77 B (the lock assigns offsets; this assumes the order above).
- RAM: 16 B more of globals (68 B of the heap tail are free after PL13); ITCM if the saved block can point at it
  (builder's call).
- The draft: any of the new settings counts as "a new setting in use" (PL13's rule: the first Write takes two presses,
  then every change re-writes).

### A second saved block

PL10-PL13 accept a block of at most 64 B (8 B header + 56 B payload) and drop every CTPlay setting of the project when
it is longer. So the payload is split:

- **Block 1** stays where it is (record tail + 768) and as it is: header, then the payload's first 56 B. PL14 always
  writes it full (n = 56; bytes past the last field 0). PL10-PL13 read it as now and take the fields they know.
- **Block 2** follows it at **tail + 832** (the tail's last 168 B; stock never reads the tail, CTPlay uses only +768
  so far): its own magic (e.g. "CTP2"), layout ID, length, check, then the payload from byte 56 on (up to 160 B).
- **Block 2 belongs to one block 1.** Its check covers block 1's header (without the pending byte) and payload as well
  as its own payload, at least 16 bits in all (block 1's CRC-8 alone would miss 1 change in 256). So when an older
  build re-saves the project (it rewrites block 1 only, with n < 56), or anything else changes block 1, block 2 no
  longer matches and its fields take their defaults. Re-saving on an older build drops PL14's extra settings; loading
  alone loses nothing. (The user guide's downgrade note says so.)
- Block 2 counts only when block 1 is valid with n = 56. A project from PL13 or earlier: block 1 loads as now, the new
  fields take their defaults. A new project: stock's init clears the whole tail, both blocks with it.
- One pending flag (block 1's) covers both; save and load handle them together, in the same hooks and task as now.
- **The build:** `saved.c`'s 64 B assert becomes "block 1 ≤ 64 B, block 2 ≤ 168 B"; the lock and its rules
  (`slimbuild/lock.py`) are unchanged: offsets are one logical payload, split at 56. A field may straddle the split.
- **The link:** offsets are the same logical payload, so the CTCtrl link needs no new message; its state grows to
  77 B. New fields at rev 1; `link_valid` checks the new values as `saved_fix` does. `euclid_last` is not linked
  (*my call*: it is the last played pad, not a setting). CTCtrl's panel learns the fields later (repo `ctctrl`);
  the builder checks that today's CTCtrl panel tolerates a longer state.

## Code

- `melody_math.c` (pure, with its Python model `tests/melody_model.py`): the cycle, the combine, the thinning, the tie
  and jump draws. `euclid.c`'s `plan()` and `euclid_write_to()` call them; the masked section stays as short as PL13's
  (all worked out before interrupts are masked).
- `page.c`: second pages, the table of contents' re-tap, ▲ ▼ order, `page_sub`, LED of the new pages.
- `euclid.c` / `melody.c`: the new pads, picks and LEDs; `melody_new_in_use` covers the new settings.
- `features/saved/saved.c`: block 2. `chord_saved_fix` / `chord_link_valid`: the new fields.
- `ui-map.md` (pages rule, the new pages, free pads), user guide (the new tools, the downgrade note), `resources.md`
  at publish.

## Testing

**Emulation:**
- The pure functions against the Python model: cycles 3-7 on patterns of 1-32 steps, every combine with every k, k₂,
  rotation; thinning (first hit kept, streams independent); ties (line does not advance, never accented); jumps
  (range edges).
- **PL13 parity:** every new setting off → byte-identical steps to PL13's Write, over the PL13 parity cases.
- Ties through stock's player: the preferred way gives one note-on and one note-off per tied run at the right ticks,
  neighbouring and distant hits, across the loop's end; a stock edit afterwards (Micro Step view shows the tie).
- Pages through the real route (controller `0x08033282`): the table of contents' re-tap between a feature's pages, ▲ ▼
  through all pages, the LEDs, the page of each feature remembered per track and after a save and load (`page_sub`; a PL14 project left on Phrasing opens Melody on PL13); PL13's draft rules across the
  new pages.
- Saved blocks: PL14 save → PL14 load (round trip, `euclid_last` included); a PL13 block → defaults for the new
  fields; a PL14 project loaded on PL13 (its own fields, nothing dropped); a PL14 project re-saved by PL13 then loaded
  on PL14 (new fields default); a changed block 1 with a stale block 2; foreign bytes at tail + 832; bad values fixed.
  The Components validator (`components-ncs-validator` memory) does not check the record tail.
- The link: the longer state, writes to the new fields, invalid values refused.

**Device** (`firmware/PL14/TEST.md`, plain steps from a new empty project): each tool by ear on a playing loop (both,
either, cycle 5, thinning re-rolled, ties at ½, jumps at ½); the table of contents' re-tap and ▲ ▼ through the pages;
save, power-cycle, reload; load the project on PL13 (its settings intact); PL14's two fixes (commit `1e54bc8`).

## Later

Transforms (Phrasing rows 2-3), contour shapes, phrase repeat, ghost notes, slides on mono patches, a source and
cycle for the second rhythm, drum tracks with their own rhythm tools (PL15).

## Alternatives considered

- **Rows that scroll under ▲ ▼** (the user's other idea): rejected for now, see "Pages that span two screens".
- **Everything new on one new page:** the rhythm tools would sit away from the rhythm's preview; splitting by
  layer (rhythm pages / note pages) keeps PL13's "rhythm and pitch are separate layers".
- **Packing into the 3 free bytes and PL13's spare bits:** 22 bits per track do not fit, and drums will need more.
- **A bigger block 1:** every older build would drop all CTPlay settings of such a project.
