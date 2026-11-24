# Melodic generator — design draft

Date: 2026-10-19 · Branch: `slim` · Status: **built as `PL13`** (2026-10-19; plan `plans/2026-10-19-melodic-generator.md`; **passed on the device 2026-10-20**, `firmware/PL13/TEST.md`). Began as a draft the user asked for as a base, 2026-10-19; the builder check's questions were answered by the user the same day. Builds on PL11's Euclid writer (`specs/2026-10-17-euclidean-design.md`). Research:
`research/2026-10-19-melodic-generators.md` (section 4, ideas 1-5). Candidates: "Euclid for melodic parts" and
"Melodic idea generator" (`candidates.md`), both answered by this spec.

## Purpose

Write a bass line or an arpeggio-like part into a pattern in a few presses. Today the Euclid writer puts the same
note (or chord) on every hit, so on a synth track it gives a rhythm, not a line. This adds:

- a **pitch layer**: each hit gets its own note, from the last played pad's chord or from the scale, walked in an
  order (up, down, climb, a random walk, bass rules ...);
- a **second rhythm source**, "groove": the hits fall on strong beats first, as in a bass line, where Euclid spreads
  them evenly;
- **accents** and a **"to the next hit"** note length;
- **two dice**: one rolls new notes on the same rhythm, one rolls a new rhythm with the same note rule.

What comes out is still ordinary stock steps: it plays, edits and saves as stock's, and plays the same on official
firmware.

**Success:** from any synth or MIDI track, a bass line that sounds "right" (root on the downbeat, chord notes, no
wrong notes) in under ten presses. Pressing a dice pad keeps the parts you like and changes the rest, and you can
always get the pattern back as it was before you started.

**Non-goals (this spec):** drum tracks (no drum pages yet); playing a line live without writing it (Turing Machine /
Marbles style: does not play on stock); transforming a part you played in by hand (shuffle, reverse, mirror: its own
spec, on Pattern tools pads 25-28); per-step probability ghosts; contour shapes; writing a family of patterns.
Each is in "Later" below.

**Anti-goals:** a control you cannot understand without a screen (the MicroFreak and Turing Machine reviewers' main
complaint); any change to what PL11's pages do unless the user turns on a new setting (old projects write the same
patterns as before); losing the user's pattern (a Write must stay undoable).

## The idea in one paragraph

**Rhythm and pitch are separate layers.** The Pattern tools page (PL11) decides *when*: Euclid or groove, the hit
count, rotation, gate, velocity. A new **Melody** page decides *which note* each hit plays: the root, the note pool
(chord or scale), the range (1-3 octaves), the order, and the accents. Write (on either page) combines the two into the current
pattern. A dice pad on each page re-rolls one layer and keeps the other. The default order is **"same"**: every hit
plays the last pad and its chord, exactly as PL11. A user who never opens the Melody page sees no change.

## UI

### Pages

- **Pattern tools** (pad 27, orange, PL11) keeps its layout and gains three controls: rhythm source on pad 20, and
  the two dice on pads 29 / 30 (below).
- **Melody** (new main page, **pad 28** in the page list, the next main slot from the left: `ui-map.md` "Page
  slots"). Colour: **yellow** (*my call*; the builder picks a steady code, checks its RGB in emulation against
  stock's LEDs, and keeps it off the 35 animated codes). No quick half: like Pattern tools, it is a writing page.
  ▲ ▼ step between Pattern tools and Melody, so the two read as one tool over two pages.
- **The action group sits on the same four pads on both pages** (rule 2: fixed places): 29 dice rhythm, 30 dice
  notes, 31 Undo, 32 Write. Write and Undo are the same action on both pages (one armed state, one Undo copy).

**Melody page** (yellow):

| Row | Pads | Control |
|---|---|---|
| 1 | 1–8 | **Order** (one pad per value): same · up · down · up-down · climb · walk · random · bass |
| 2 | 9–10 | **Pool**: chord · scale |
| 2 | 11–13 | **Range**: 1 · 2 · 3 octaves |
| 2 | 14 | **Accent** cycle: off · first hit · on the beat · every 3rd hit |
| 2 | 15–16 | *free* (later: ties, ghosts, contour shapes) |
| 3 | 17 | **Root: last pad** (default): the pool starts on the last pad played on the track, as PL11 |
| 3 | 18–24 | **Root: scale degree** 1 … 7 of the project's scale (user, 2026-10-19: root pads on the Melody page, so a new root needs no trip to the Note view) |
| 4 | 25–28 | **Octave** of a degree root: −2 · −1 · 0 · +1 (0 = pad 24's octave, keyboard pitch 72; −2 for bass). Dim, not selectable, while the root is "last pad" (the pad's own octave) |
| 4 | 29 | **Dice: rhythm** (as on Pattern tools) |
| 4 | 30 | **Dice: notes** |
| 4 | 31 | **Undo** (as on Pattern tools) |
| 4 | 32 | **Write** (as on Pattern tools) |

**Pattern tools, changed pads:**

| Pad | Was | Becomes |
|---|---|---|
| 20 | free | **Rhythm source** toggle: Euclid (dim) · groove (bright). The Hits pads keep their meaning: k hits |
| 21 | Gate cycle 6/6 … 1/6 | the same cycle plus a 7th value, **"to the next hit"**: each note lasts until the next hit (legato line). After 1/6 comes "to the next hit", then 6/6 (*my call* on the order; colour: the builder's, a steady code distinct from stock's Gate-view colours) |
| 25–28 | free | still free (transforms later) |
| 29 | free | **Dice: rhythm** |
| 30 | free | **Dice: notes** |

The preview on pads 1–16 shows whichever rhythm source is chosen, with the rotation and the rhythm seed. It shows
*when* only: there is no pitch display (*my call*: 16 pads cannot show a melody readably; hearing it is the preview,
see "Draft" below).

### Draft: hearing it while you shape it

The pads cannot show pitches, so a melody is judged by ear. That needs quick re-writes. **Decided** (user,
2026-10-19: a draft, but only with the new settings):

- **Plain Euclid stays PL11.** With the order "same", the Euclid rhythm, the root "last pad", accent off and a gate
  of 6/6 … 1/6, every Write takes two presses, as in PL11, and nothing writes at once.
- **With any new setting in use** (another order, groove, a degree root, an accent, or the gate "to the next hit"),
  the first Write still takes two presses (first press arms, pad 32 blinks; second press writes). It keeps the
  pattern's old steps for Undo.
- After that Write the pattern is a **draft**. In a draft, **every change on Pattern tools or Melody re-writes at
  once** (one press): a dice pad, any setting on either page (hits, rotation, order, pool, root ...). The loop
  changes while it plays. A draft that started stays a draft until it ends, even if the settings go back to plain
  Euclid (*my call*).
- The draft lasts while **the track's pages stay open**: ▲ ▼ and the table of contents move between pages without
  ending it. So the chord shape can change on the Chords page; the next press on Pattern tools or Melody re-writes
  with it (*my call*: a Chords-page press itself does not write).
- **Undo** always returns to the pattern as it was **before the first Write** of the draft, and ends the draft. Undo
  again puts the last draft back (Undo swaps, as in PL11).
- The draft belongs to **the pattern its first Write went to** (the one Undo names), not to whichever pattern plays
  now: on a chained track the current pattern moves on every bar, and the re-writes keep going to the draft's
  pattern (*my call*, from the builder check).
- The draft **ends** when the track's pages close (a track button, Note, Mixer, FX, Preset: `ui-map.md`), Undo is
  pressed, or a project loads. The next Write takes two presses again.
- **Outside a draft**, a dice pad only rolls its seed (the Pattern tools preview shows a new rhythm at once; new
  notes are heard after the Write).

So: two presses protect the user's pattern once, then it is a sketch pad. Write pad LED in a draft: bright orange
(steady) instead of dim (*my call*), so the user can see that changes now write at once.

**Writes run on the pad's release (device finding 2026-10-20).** On the device, a press that wrote a pattern while the
finger was still down often made a phantom press on the next pad (a draft order pad 3 jumped to pad 4; Undo armed
the Write about half the time; PL11's Undo had it too). Picks that write nothing never did it. Emulation has no pad
scanner and cannot show it. The pads are read through a 74HC4051 analog multiplexer into the ADC: the long write
(interrupts masked, then stock's `rec_touch`) probably delays the scan while the finger is down, so pad p's pressure
lands in pad p + 1's slot. The fix: do no pattern write during a press. Write's second press, Undo and a draft's
re-write set one pending action `{track, pad, kind}`; the pad's release runs it. The settings and LEDs still change on
the press. The latest press replaces the pending action; closing the pages, a button press, a project load and a link
write drop it.

### What the user sees, in short

- Nothing written, no draft: the pads show settings and the rhythm preview; nothing changes the pattern until Write is
  pressed twice.
- Draft: Write lit bright; every press on the two pages changes what plays.
- Undo lit blue while this track has one (as PL11).

## What gets written

The Write of PL11, with two functions swapped in: the **rhythm** (which steps are hits) and the **pitch of each hit**.
Gate, velocity, probability and microstep rules stay as PL11 except where stated.

### Rhythm sources

- **Euclid** (PL11): `euclid_mask(k, n, rotation)`. Dice rhythm in Euclid mode picks a **random rotation** (0 … n−1;
  the rotation pads then move on from there). Euclid itself has nothing random.
- **Groove** (new): each step of the pattern gets a fixed weight by its place in the bar, plus a small random amount
  from the rhythm seed; the **k steps with the highest scores** are the hits. So the Hits pads still mean "k hits",
  and a low k gives the strong beats. Weight order (*my call*, after Acid Banger and Grids): the bar's downbeat
  (step 1), then the other quarter notes (5, 9, 13), then the steps just before a quarter (4, 8, 12, 16: they push
  into the beat, a bass-line habit), then the 8th off-beats (3, 7, 11, 15), then the rest. The random part is large
  enough to swap neighbouring ranks, not to put an off-beat ahead of a downbeat. Patterns longer than 16 steps repeat
  the bar weights; the second bar's downbeat weighs a little less than the first. Rotation applies to groove too.
  The builder sets the table and the jitter, and checks them in the Python model (below).
- **A dice press always changes something** (final review): the seed steps on until the result differs from the
  current one. Dice rhythm: until the rhythm differs (Euclid: the rotation = the new seed mod n, at most n tries, so
  8 hits over 16 steps never lands on a rotation 8 apart; groove: the new seed, at most 16 tries). Dice notes: until
  the line written on the current hits differs (at most 16 tries). When nothing can change (k = 0, k ≥ n, every
  rotation alike, a pool of one note), the seed keeps the last step and nothing audible changes.

### Pitch: the pool

The **pool** is the list of notes the order walks, sorted low to high, built at Write time from the **root** the
Melody page picks: the track's **last played pad** (PL11's `euclid_last`, its keyboard pitch; 72 before any pad), or
a **scale degree** in the chosen octave (degree d counted in scale steps up from keyboard pitch 72 + 12 × octave,
octaves included, as the chord engine counts degrees: in a 5-note scale degree 6 is the root an octave up and degree 7
the 2nd an octave up).
The root acts as a pad would: in "same" order a degree root writes that degree's chord on every hit.

- **chord:** the root and its chord with the track's chord settings, as `chord_notes()` makes it (what that pad plays
  now, bass mode included). With the chord shape off, a **triad** on the root, in the scale (user, 2026-10-19: a
  one-note pool cannot make a line).
- **scale:** every scale note from the pad up (the project's scale and root; Chromatic uses the major scale, as the
  chord engine does), and the root itself even when it is outside the scale (a pad off the scale): the line's root is
  always the root played.
- **range** 1 / 2 / 3 octaves: the chord pool repeated one, two or three octaves up from the pad; the scale pool to
  the pad + 12, + 24 or + 36. Notes outside stock's playable range are left out (as `chord_notes()` does).

### Pitch: the orders

`i` = the hit's number from the first hit (0, 1, 2 …), `P` = the pool size. The notes seed changes where each order
starts or what it picks; the same seed and settings always write the same notes.

| Order | Each hit plays | Dice notes changes |
|---|---|---|
| same | the pad and its chord on every hit (PL11, byte for byte) | nothing (dark) |
| up | pool[(s + i) mod P] | the start s |
| down | from the top down | the start |
| up-down | up then down, ends not repeated (as the Arp's) | the start |
| climb | two up, one back (T-1's "climb"): 0, 1, 2, 1, 2, 3, 2, 3, 4 … wrapping at the top | the start |
| walk | a random walk: each hit moves −2 … +2 places in the pool (±1 most often, 0 = repeat), turning back at the ends; starts on the pad | the walk |
| random | a random pool note, never the same as the one before (as the Arp's random) | the picks |
| bass | the root on the first hit and on most hits that fall on a quarter; the other hits by weight: root and its octaves most, then the fifth, then the other pool notes (Acid Banger's weighted sets) | the picks |

- Up, down, up-down and random reuse the Arp's order maths (`arp_index`, *my call*: the Arp and Melody pages then
  agree on what "up-down" means).
- In every order but "same", each hit is **one note** (a line, not chords).
- **Bass:** "root" = the pad's note name at the lowest place it has in the pool (with chord bass mode on, the bass
  note). The fifth is the perfect fifth (root + 7) when the scale has it, else the scale's 5th degree above the root
  (`chord_degree_class(root, mask, 4)`, e.g. the diminished 5th in locrian); it is added to the pool when no pool note
  has its pitch class (*my call*), and its pitch class is the one weighted 2 (`melody_pool_t.fifth`). The builder sets
  the weights in the model.

### Accent

Accented hits play **hard** (127); the others play at the Pattern tools velocity (soft or medium makes the accent
heard; with hard, the accent changes nothing). Cycle: **off** · **first hit** · **on the beat** (hits on steps 1, 5,
9, 13 …) · **every 3rd hit** (hits 1, 4, 7 …: across the 4/4 grid, as Hapax's Every N). Accents work in every order,
"same" included.

### Length: "to the next hit"

The 7th gate value: each note lasts from its hit to the next hit, in sixths (the last hit to the first one of the next
loop), capped at 96 sixths (16 steps), stock's own longest note (its step-gate and mutate code clamp to 1-96; final
review). The builder checks on the pattern format whether the tie bit (bit 7 of the length byte) is needed for a note that crosses the loop's end, or
whether a long length is enough.

## Settings

All per track, saved with the project (saved settings, PL10), sent over the CTCtrl link (PL12) as the other saved
fields are:

- `euclid_cfg[t][0]` **bit 7 = rhythm source** (0 Euclid, 1 groove): the free bit of the existing byte. `[1]` bits
  5-7 = gate, now 0-6 (6 = to the next hit). Both stay in the existing 8 B, so a project saved by the new build and
  loaded on PL11 / PL12 plays Euclid at the gate PL12's `saved_fix` resets to: safe.
- **`melody_cfg[4][2]`** (new, 8 B): [0] order (bits 0-2) | pool (bit 3) | range − 1 (bits 4-5) | accent (bits 6-7);
  [1] root (bits 0-2: 0 last pad, 1-7 degree) | octave + 2 (bits 3-4: 0-3 = −2 … +1) | spare bits 5-7 (0).
- **`melody_seed[4][2]`** (new, 8 B): [0] rhythm seed, [1] notes seed. Saved, so a project reloads with the same
  Write result (*my call*).
- **`euclid_last[4]`** (PL11's last played pad) **stays RAM only**: saving it makes the payload 57 B, above the 64 B
  block (8 B header + payload) that PL10-PL12 accept, and they would drop every CTPlay setting. A degree root
  reproduces after a reload; a "last pad" root does once a pad is played.
- Defaults: order same, pool chord, range 1 octave, accent off, root last pad, octave 0, seeds 1 (any non-zero
  LFSR start).
- RAM: 16 B more (PL12 uses 136 of 240 B) plus the draft state (1 B: track + 1, 0 = none) and the armed Write (PL11's).
  Or ITCM, if the saved block can point at it (builder's call). Flash: a few KB.
- **Saved block:** two new fields, appended to `save_layout.lock` (payload 37 → 53 B). A payload above 56 B makes
  PL10-PL12 ignore the block (64 B limit), so a later feature needs a decision.
  `saved_fix` and `link_valid` check the new values: order 0-7, range 0-2, root 0-7, gate 0-6; anything else back to the default. PL12's `euclid_link_valid` rejects bit 7 of `euclid_cfg[t][0]` and
  gate 6: the new build accepts both.
- **Link:** the field revision of `euclid_cfg` stays 1: the byte only gains values, and an older reader keeps them.
  CTCtrl's `withBits` preserves bit 7 (groove) when it writes the hits or the velocity, and gate 6 ("to the next hit")
  shows no gate chip there.

## Code

Inside the chord feature, as Euclid: `melody_math.c` (pure: the groove mask, the pool, the orders, the accents, the
length to the next hit; no stock calls) and `melody.c` (the Melody page, the dice, the draft). `euclid.c`'s `write()`
calls them for the mask and for the units of each hit. It works out the rhythm and the line before interrupts are
masked, for the target read then; with interrupts masked it reads the target again (and works them out again only if
a chain moved on in between), then keeps PL11's order: the Undo copy, the steps, each step's unit mask last (final
review: a shorter masked section). Python model in `slim/tests/` for the pure parts, as `arp_model.py`.

## Testing

**Emulation:**
- The pure functions against the Python model: every order, pool, range and seed on a few scales and pattern lengths
  (1-32); the groove mask for every k ≤ n, n ≤ 32; same seed → same result.
- **PL11 parity:** order "same", Euclid, any gate 0-5: the Write produces byte-identical steps to PL11's.
- The pages through the real route (controller `0x08033282`): LEDs, presses, ▲ ▼ between the two pages, the action
  pads on both.
- The draft: plain Euclid never starts one (every Write two presses, as PL11); with a new setting the first Write
  takes two presses, then each setting and dice press re-writes once; Undo returns the pre-draft steps and ends the
  draft; ▲ ▼ to the Chords page and back keeps it; closing the pages ends it; on a chained track the re-writes go to
  the draft's pattern.
- The written pattern through stock's own playback (notes at the right ticks, lengths, velocities) and a stock edit
  afterwards. Saved fields: save, load, a PL12 project loaded (defaults), bad values fixed.

**Device** (`firmware/PL13/TEST.md`, plain steps, one expectation per press): write a bass line in each order and
listen; dice notes keeps the rhythm, dice rhythm keeps the order; the draft re-writes while playing without clicks or
stuck notes; Undo after several draft changes returns the original; save, reload, and load the project on stock.

## Later (own specs, same pages)

- **Transforms of the current pattern** on Pattern tools pads 25-28: shuffle the pitches (keep the rhythm), reverse,
  mirror around the root, rotate the notes against the rhythm (research idea 6). They work on hand-played parts and
  share Undo and the draft.
- **Probability ghosts**: soft notes on some gaps at a stock probability, so the loop varies each pass (idea 7).
- **Ties / passing notes**: a tie chance; a scale step before a change of root (bass).
- **Contour shapes** (ramp, triangle, sine) as more orders (idea 8; Melody pads 17-28 have room).
- **Write a family** into the next empty patterns (idea 9). **Ratchets / grace notes** (idea 10, check stock's
  microsteps first). **Drum tracks**, with the drum pages.
- **CTCtrl panel** for the Melody settings (repo `ctctrl`): the link carries the fields from PL13; the panel is
  separate work.

## Alternatives considered

- **Everything on the Pattern tools page** with cycle pads: 7 free pads cannot hold order (8 values), pool, range,
  accent and two dice without combining most of them under cycles you cannot read at a glance (rule 3). A page of its
  own keeps one pad per value.
- **The pool from the arpeggiator's held notes** (latched chord): richer, but only while something is latched, and
  the Pattern tools pages already use "the last pad and its chord". Possible later as a third pool.
- **Every re-roll needs two presses** (no draft): safer, but four presses per idea makes judging by ear slow.
- **A draft for plain Euclid too**: faster, but changes what PL11's page does (the user chose two presses there,
  2026-10-17).
- **Root from the Note view only** (leave the page, play a pad, come back): ends the draft each time; root pads on
  the Melody page keep the loop on one page (user, 2026-10-19).
- **A live generator** (notes made at playback): does not play on stock firmware, needs a playback hook and saved
  per-track state. Writing keeps CTPlay's rule that what you make plays anywhere.

## Questions for the user (answered 2026-10-19)

1. ~~The draft~~: yes, but only with the new settings; plain Euclid stays PL11's two presses.
2. ~~Chord pool with chords off~~: a triad on the root.
3. ~~A Melody page of its own~~: yes, pad 28, next to Pattern tools.
4. ~~A new root without leaving the page~~: root pads on the Melody page (degree and octave); chord shapes stay on
   the Chords page (*my call*), reachable with ▲ ▼ without ending the draft.
