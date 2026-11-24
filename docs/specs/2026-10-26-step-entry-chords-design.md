# Chords in step entry (PL18) — design

Date: 2026-10-26 · Branch: `slim` · Status: **draft for the user's review** (builder check done 2026-10-26: the stock
readings hold; its one question, pad first with an arpeggio / falling strum or the note already in the step, answered by
the user: accept the gaps). Candidate row: `candidates.md`, "Chords in
step entry". The user's idea (2026-10-25): a Keys-page setting, as poly / mono record; off = stock.

## Purpose

Today a CTPlay chord only reaches a pattern by live recording. Step entry (hold a step, press a pad) ignores the chord
engine: stock adds just the pad's own note. Many Circuit users program step by step, so the chord engine stops at the
point where they write their parts.

With this build, a track's **step-entry chords** setting makes step entry write the pad's whole chord into the step:
the same notes the pad plays live, with the track's shape, voicing, bass mode and voice leading. The Keys page also
becomes one toggle pad per setting: mono record on pad 1, step-entry chords on pad 2.

**Success:** with a triad set and the setting on, holding step 1 and pressing the C pad puts C, E and G on step 1 in
one press. Pressing the C pad again with step 1 held takes them out. The pattern then plays the chord, on CTPlay and
on stock firmware alike: the notes are ordinary step notes.

**Non-goals:**
- Strummed chords written as microstep rolls. Strum and its direction are ignored here: every note goes in at
  microstep 0. A written roll could come later, as a choice next to this one.
- The arpeggiator. A step gets the chord shape's notes, never an arpeggio.
- Drum tracks (no chords there), and the expanded Note view (mode 6, no step pads).
- Undo of a step entry. Stock has none either.
- Upstream's gate by hold time (`tools/stepgate.py`). Gates follow stock's rule (below).

**Anti-goals:**
- With the setting off, any change to stock's step entry, byte for byte.
- Work during the pad press that could make a phantom press on the next pad (CLAUDE.md, "no long work while a pad is
  pressed").
- A stuck note in any press / release order of a step pad and a chord pad.

## How stock does it (emulation, `re/app.asm`)

Two routes reach one function, **`0x0804B094(view, note, vel)`**, which adds a note to the held step's **edit store**
`[view + 0x24]` (stock's double-buffered parameter store; parameter 0 byte 0 = the mask of used units, byte 1 = the
step's probability; parameters 1–6 = the six units: note, gate | tie << 7, microstep, velocity):

1. **Step first, then pad.** The Note view's pad press `0x0804AB5A(view, pad, vel)` applies the fixed-velocity rule,
   then checks for a held step (`[view + 0x2C]` parameter 0). No step held: on to the note start `0x0804AEF2`
   (CTPlay's `pad_note_on` hook). Step held: it walks the six units. A unit whose note (snapped by `0x080408C6`)
   equals the pad's pitch is **removed**: mask bit cleared, committed (`0x080353C0`), its sound ended, and the pads
   holding that pitch cleared (`[view + 0x40 / 0x60 + pad]`). If nothing was removed, it tail-calls `0x0804B094` with
   the pad's pitch.
2. **Pad first, then step.** A listener on the view (`0x0804B1F2`, called through a thunk at `0x0804B1F0` when the
   held-step parameter changes) calls `0x0804B094` for each held keyboard pad (pads 17–32: `[view + 0x50 + i]` the
   pitch, `[view + 0x70 + i]` the velocity) whose pitch is not in the step yet.

`0x0804B094` finds the longest gate among the step's units, takes the first free unit (all six used: it adds nothing),
writes note, velocity, gate (the longest found, or 6 = one step when the step was empty; then the step's probability
byte becomes 7 = always), microstep 0, sets the mask bit and commits. Unit notes are in the keyboard's pitch space, the
same as `chord_notes()` uses (`[kbd + 0x14 + idx]`, root-relative + 12), so chord notes need no conversion.

The builder confirms these in emulation before relying on them, as with every stock reading.

## The behaviour

Applies to Synth 1 / 2 and MIDI 1 / 2, in the two-row Note view, when the track's setting is on **and** the pad would
play a chord live (a shape set, or the bass mode on: `CHORD_HAS_SHAPE || CHORD_BASS`). Otherwise stock, untouched.

### Adding

- **Which notes:** the notes the pad plays live: `chord_notes()` with the track's settings and the project root,
  notes outside stock's range left out as live.
  - Step first: the chord is built at the press. With voice leading on, it leads from the track's last chord
    (`chord_prev`) and becomes the next one's last chord, as a live press does. So entering a progression step by step
    voice-leads from step to step in the order the steps are entered.
  - Pad first: the notes that are sounding (the pad's held entry), so the step gets what the user hears. No held
    entry for that pad (it cannot normally happen with a shape on): built as above.
  - **Pad first writes nothing in two cases** (the user, 2026-10-26: accepted, no third hook). (a) The arpeggiator or a
    falling strum is on: CTPlay takes the press (`pad_note_on` returns HANDLED), so stock never stores the pad's pitch
    in `[view + 0x40 / 0x60 + pad]` and its listener has nothing to add, not even the pad's own note. (b) The pad's own
    note is already in the step: the listener skips that pad (`0x0804B232`), so `0x0804B094` is never called. Step
    first works in both. TEST.md and the guide say so in one line.
- **Notes already in the step** are not added again.
- **Room:** six notes a step. The pad's own note goes first (as stock), then the chord's other notes from the lowest
  up, until the step is full; the rest are left out. An empty step always takes a whole chord (the bass modes keep
  a chord to 5 notes). *My call.*
- **Gate:** stock's rule. Every added note gets the step's longest gate, or one step when the step was empty. **Velocity:** the
  press's, after stock's fixed-velocity rule, for every note. **Microstep:** 0. **Probability:** stock's (set to
  always only when the step was empty).
- **One commit** for the whole chord: listeners (step LEDs, the held-step preview) run once.
- **Sound:** what stock does for one note after an add, it does for the chord (the commit's listeners preview the
  step's notes). The builder records in emulation what sounds; nothing extra is sent by CTPlay.

### Removing

Step first, the pad's own note already in the step (stock's removal rule): the press removes **the pad's chord**: every
unit whose note name is one of the chord's note names (the chord built as for adding, compared by pitch class, so an
inversion or voice-leading change since the add does not matter). Stock then removes the pad's own note and ends its
sound as it does today; CTPlay ends the sound of the other removed notes the same way.

Known edge, accepted: two chords on one step that share a note name lose the shared notes together, and a single note
entered by hand on that step with one of the chord's note names goes too. *My call:* simple to explain, and a step
holds at most six notes.

### What does not change

- Strum, falling strum, the arpeggiator: ignored for the write (above). The pad-first route leaves the live sound as
  it is today (a strummed or arpeggiated press keeps sounding as it does).
- Releasing pads and steps: stock's and CTPlay's release paths as today. The chord's extra notes were never pad notes
  in stock's tables, so nothing new is held. *Changed for the beta (user, 2026-10-29: match stock):* pad first, the
  step let go first, the whole chord sounds until the pad's release, as stock keeps the pad's own note: at the step's
  release (hook `preview_end`, `0x0804B00C`) the router hands the notes the preview took back to the chord's pad
  (`chord_on_preview_end`, `features/chord/chord.c`).
- LEDs: holding a step lights the step's notes on the keyboard, as stock does. Nothing new on the Note view.

## The controls: Keys page, pads 1–2

The Keys page becomes one toggle pad per on/off setting (the user, 2026-10-26): a lit pad = changed from stock.
Mono record moves from a two-pad row to one toggle on pad 1, and step-entry chords take pad 2.

| Row | Pads | Controls |
|---|---|---|
| 1 | 1 | **Mono record** toggle: magenta `0x32` = mono, dim magenta `0x38` = poly (stock). Was pads 1–2 (poly · mono) since PL08 |
| 1 | 2 | **Step-entry chords** toggle: green `0x17` = on, dim green `0x18` = off (stock) |
| 1–4 | 3–32 | *free* (the fourths layout on row 2 later) |

- Both per track, **off by default** (off = stock). A press flips the setting at once; no draft, no action. Shift held
  on the page: the table of contents, as on every page.
- **Mono record keeps its saved meaning**: `chord_mono` bit t = mono, unchanged, so saved projects, the CTCtrl link
  and its panel need nothing new. Only the pads and LEDs change (`page.c`).
- **A deliberate move of a claimed pad** (rule 2), allowed in alpha as PL15's Chords page was: pad 2 changes from
  "mono" to "step-entry chords". The guide's "Changes by feature" says so.
- Green for step-entry chords, as the chord feature's colour (the agreed rough guide had it on pad 3, green).
- **`ui-map.md` rule 3 gains a line:** a plain on/off setting is one toggle pad, lit = on. "One pad per value" stays
  first for settings with several values, and for two values that are both real choices (strum direction: rising ·
  falling).

## Saved and linked

- `chord_step`: 1 B, bit t = track t on (bits 4–7 always 0). **Saved**, appended at payload offset **115** (block 2;
  the payload becomes 116 B; block 2 has room). Loading a value with bits 4–7 set resets it to 0 (`chord_saved_fix`,
  as `chord_mono`). **Linked** (a setting): CTCtrl can read and write it; a link write checks it as `chord_mono`
  (`mask_ok`). CTCtrl's panel is the user's to update.
- Kept in ITCM, as every setting since PL14 (1 B). The heap tail is not touched.

## Where it hooks (the plan confirms)

- **`step_add`**: an entry hook at `0x0804B094` (`push.w {r3–fp, lr}`, expect `2de9f84f`, displace 4; args
  `view, note, vel`; UI task). With the feature active for the view's track, CTPlay does the whole add itself
  (the pad's note and the chord's, one commit) and returns HANDLED; otherwise PASS. It writes the units as stock
  does, through the store's write pointer `0x080354FA` (a new symbol) and `store_commit`. Covers both routes.
- **`note_pad_press`**: an entry hook at `0x0804AB5A` (same prologue bytes, displace 4; args `view, pad, vel`; UI task)
  for the removal: with a step held, the feature active and the pad's own note in the step, CTPlay removes the
  chord's other notes, then returns PASS so stock removes the pad's own note and does its bookkeeping. Any other
  case: PASS with nothing done.
- The pad-first route needs the pad behind a note: `step_add` finds the track's held entry whose `root` is that note
  and whose pad is still held.
- Both hooks only read and write a few store parameters: no `slim_irq_save()`, no pattern-wide write, no DSP lock
  taken by CTPlay. That is why the work may run on the press. The emulation tests count the hook's instructions, and
  the device run checks the next pad (below).

## Budget

Flash: about 1–1.5 KB expected (117 KB free). ITCM: 1 B. Heap tail: 0 B. Saved: 1 B in block 2. Stack: the add runs
`chord_notes()` / `chord_lead()` on the UI task's stack (the press path measured 476 B in PL17); the manifest's
`hook_stack` records it.

## Tests (emulation, through the real routes: controller pad press / release)

- Off: step entry byte-identical to stock (edit store and pattern), both routes, with a chord shape set.
- On, step first: triad, 7th, 9th with bass below (5 notes), rootless over bass; gates on an empty step and on a step
  with a longer note; velocity with fixed velocity on and off; notes past the range left out; the room rule with 4
  notes already in the step; no duplicate notes.
- On, pad first: the step gets the sounding notes, voice leading included; the release afterwards leaves no note on.
  With the arpeggiator or a falling strum on, and with the pad's own note already in the step: nothing written, no
  note left on.
- Removal: the pad again takes the chord out; after a voicing change it still does; the edge (shared note names)
  as specified.
- Voice leading across steps entered in order.
- MIDI 1 / 2: the same writes.
- The written pattern plays the chord (the player's notes), and a stock edit of the step afterwards keeps it.
- No stuck notes in any order of: step down, pad down, step up, pad up.
- Saved: round trip of `chord_step`; a foreign value resets to 0; the link reads and writes it.
- Keys page: pad 1 flips mono record per track (the same `chord_mono` bits as PL08's pads 1–2 set), pad 2 flips
  step-entry chords; LEDs bright / dim per the table; pads 3–32 dark and doing nothing. The existing mono-record tests
  that press pad 2 for mono move to the toggle.
- The expanded Note view and the drums: untouched.

## Device test (`firmware/PL18/TEST.md`)

Starting state: a new empty project, Synth 1 on a Poly patch. Steps name pads by their note, not their number (the
user plays a keyboard layout). Main steps:
1. Keys page: pad 1 dim magenta, pad 2 dim green (both off). Press pad 1: bright (mono); again: dim (poly). Leave it
   dim. Chords page: triad. Keys page: pad 2 on (bright green).
2. Hold step 1, press C: hold step 1 again, and C, E, G light. Play: the chord sounds on step 1.
3. Hold step 1, press C again: the step is empty.
4. **Phantom-press check:** after each press in steps 2–3, the pad to the right of C did **not** go into the step.
5. Hold the C pad, then press step 5: step 5 gets the chord. Release in both orders: no note stays on. (With the
   arpeggiator or a falling strum on, this order writes nothing: expected.)
6. Voice leading close on: enter C, F, G on steps 1, 5, 9: the chords move by small steps.
7. Pad 2 off: step entry adds single notes again (stock).
8. Mono record on pad 1: on, record a line over existing notes: they are replaced (as PL08's mono).
9. Save the project, power off and on, load it: pads 1 and 2 keep their state per track.

## Docs to update with the build

`ui-map.md` (the Keys table: pads 1 and 2; rule 3's toggle line; drop "chords in step entry" from "No controls"; the
free-pads list: Keys 3–32), `layouts/gen.py`, `candidates.md` (the row), the guide's Keys section and "Changes by
feature" (mono record moved to one pad), `resources.md`, `save_layout.lock`, `slim/README.md` and `CLAUDE.md`'s docs
map.

## My calls (for the user to check)

1. The pad's own note first, then the others from the lowest up, when a step is short of room.
2. Removal by note name (pitch class), with the shared-note edge accepted.
3. Voice leading in step entry leads in the order steps are entered.
4. Strum ignored (all at microstep 0); a written roll is a later option.
5. Step-entry chords in green (the chord colour), on the magenta Keys page.

Decided by the user (2026-10-26): Keys becomes one toggle per setting; mono record on pad 1, step-entry chords on pad 2.

## Left to the builder

Hook mechanics and names; how the removal ends the removed notes' sound (as stock's own removal does); test file
layout; exact flash and stack figures.
