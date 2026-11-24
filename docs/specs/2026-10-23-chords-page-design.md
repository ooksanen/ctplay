# Chords page rework, voice leading (PL15) — design

Date: 2026-10-23 · Branch: `slim` · Status: **draft for the user's review** (builder check done 2026-10-23; its three questions settled as *my call*s below). Goes into `versions/PL15.toml` with three
fixes that also change the image: the two from the Gemini audit (`followups.md`, "From the Gemini audit") and the
recording of notes held past 16 steps (`candidates.md`, "Recorded notes past 16 steps").

## Purpose

After using CTPlay the user found the Chords page the odd one out: every other page has its main control on top (Arp
the pattern, Pattern tools the hits, Melody the order), Chords has its shapes on row 4. The user uses the Quick view
(Shift in the Note view) **while arranging, to audition shapes**: usually going back and forth between a couple of
candidates for the feeling a part needs. Inversions matter to the user for **voice leading**, mostly keeping the notes
close (a mellow, jazzy sound); someone else may want a particular note on top.

So this build:
1. Puts the **shapes on top** (rows 1–2) and makes the **Quick view all shapes**: any two shapes one tap apart.
2. Adds **five shapes** on row 2 that work with the scale as today's do.
3. Adds **voice leading** in three kinds, close, top line and bottom line: the engine picks each chord's inversion from the previous
   one, which is what makes taking voicing off the Quick view acceptable.

**Success:** auditioning shapes from the Quick view is one tap per shape, all 13 of them; with voice leading on, a
progression played on the pads moves smoothly without touching an inversion pad.

**Non-goals:** semitone (fixed-quality) shapes, so no forced dim / aug (the router snaps notes into the scale:
`candidates.md`, "Semitone shapes"); the harmonizer and a custom chord (a second Chords page, later); an alternating
strum (no pad left; the user agreed to drop it); drum pages.

**Anti-goals:** with voice leading off and a row-1 shape, any change to the notes a chord plays (byte for byte as
PL14, same settings); losing or mangling a project's CTPlay settings on PL10–PL14; anything "too dramatic" beyond
this layout (the user: the work so far is solid).

## The Chords page (pad 25 of the table of contents, green)

| Row | Pads | Controls |
|---|---|---|
| 1 | 1–8 | **Shape**: off · triad · 7th · 9th · sus2 · sus4 · add9 · 6th (today's eight, today's order) |
| 2 | 9–13 | **More shapes**: power · shell 7 · quartal · 7sus4 · 6/9 |
| 2 | 14–16 | *free* (semitone shapes, if their spike finds a way past the snapping) |
| 3 | 17–24 | **Voicing**, exactly today's palette row: inversion root · 1st · 2nd · 3rd (17–20) · spread close · drop-2 · wide (21–23) · bass cycle (24) |
| 4 | 25–27 | **Voice leading**: close · top line · bottom line |
| 4 | 28–30 | **Strum**: slow · medium · fast (none lit = off) |
| 4 | 31–32 | **Strum direction**: rising · falling |

- **Shapes are one choice across rows 1 and 2**: the selected one bright green, every other dim green, as today.
  Picking any shape (either row) replaces the previous one.
- **Voice leading** (the user's placement: under the inversions, so the blue reads as one group). The three pads work
  as Arp's triplet / dotted: one at a time, the lit one again = off. Colours: the inversion's blue, bright = on, dim =
  off. While one is on, the inversion pads show the stored inversion **dim** and the other three dark (as the strum
  pads do while an arpeggio pattern is on). Pressing an inversion pad turns voice leading off and picks that
  inversion (*my call*, accepted in the playback).
- **Strum** and its direction: today's colours, moved from pads 1–6. Strum's "off" pad goes (the user, 2026-10-23, to
  make room for a third voice-leading kind): **none lit = off, the lit speed again turns it off**, as every amount row
  since PL13 (cycle, combine, thinning, ties, octave jumps). The saved value is unchanged (`chord_strum` 0 = off).
  With an arpeggio pattern on they show only the stored values, dim, as today; a stored off shows no speed lit.
- **Shift held on the page:** row 4 is the table of contents, as on every page.
- **Mockup** the user approved: `.superpowers/brainstorm/…/content/chords-layout-v2.html` (local, not in git; row 4 changed after it: three voice-leading pads, strum off = none lit): the
  tables above are the record.

### The Quick view (Shift in the Note view)

Pads 17–32 show the Chords page's **rows 1–2** (all 13 shapes; 14–16 dark). Voicing, voice leading and strum are set
on the page only. With this the Quick view always shows a page's **top half** (Arp did already), so `QUICK_ROW`
becomes 0 for Chords and the rule in `ui-map.md` reads without an exception. Shift + 1-16/17-32 (the flip) and LED 53
are unchanged.

**This moves the Shift palette for the first time since PL01** (voicing on 17–24 and shapes on 25–32 become shapes on
17–29): a deliberate break of rule 2, decided by the user (one user so far; the guide's "Changes by feature" says so).

## The new shapes

Scale-degree offsets, as today's (`SHAPES` in `chord_math.c`), so they stay in key and follow the scale:

| Shape | Degrees (offsets) | In C major |
|---|---|---|
| power | 1 5 8 (0, 4, 7) | C G C |
| shell 7 | 1 3 7 (0, 2, 6) | C E B |
| quartal | 1 4 ♭7 10 (0, 3, 6, 9) | on D: D G C F |
| 7sus4 | 1 4 5 7 (0, 3, 4, 6) | on G: G C D F |
| 6/9 | 1 3 5 6 9 (0, 2, 4, 5, 8) | C E G A D |

All fit today's limits (at most 5 tones, so at most 4 notes beside the pad's own, `CHORD_MAX_OTHER`). Everything that
takes the track's chord uses them: playing, the arpeggiator, strum, Pattern tools' Write (the last pad with its
chord), Melody's chord pool. Inversion, spread and bass apply to them as to today's shapes. A duplicate of the pad's
own pitch is left out, as today (power's octave: the pad and one note above).

## Voice leading

With voice leading on, each chord the engine builds from a press takes, of its inversions, the one that sits best
against the **previous chord**:

- **Candidates:** the chord's inversions 0 … min(tones, 4) − 1, each built with today's maths (spread, bass,
  rootless, range rules included). They all contain the pad's own note and stay within about an octave of it, so the
  chords **cannot drift** away from where the user plays (the user asked; this answers it).
- **Only full candidates compete:** of the candidates, only those with the most notes (an inversion can lose one:
  power's octave lands on the pad's own pitch, a note can fall outside the range) are compared, so voice leading never
  changes how many notes a chord sounds (*my call*: a plain sum would favour the thinner inversion). For a power chord
  that keeps its plain form.
- **Close:** the candidate whose notes move least: the sum, over its notes, of the distance to the nearest note of the
  previous chord. **Top line:** the candidate whose highest note is nearest the previous chord's highest; ties go to
  the close measure. **Bottom line:** the same with the lowest note (a smooth left-hand line; with the bass mode on,
  the lowest note is always the bass, so it plays as close). Remaining ties: the lowest inversion number (*my call*).
  Other kinds considered (common tones, contrary motion, a chosen top note) were judged too close to close or too
  niche (2026-10-23).
- **The previous chord** is the notes (the pad's own included) of the last chord the engine built **on that track
  from a pad press** (live play, arpeggio presses included). The sequencer never goes through the engine: a chord is
  recorded as its notes, voice-led as heard, and plays back exactly so. A press that builds no chord (shape off and no
  bass) leaves it as it was. None yet (power-on, a project load): the stored inversion (*my call*).
- **Writes** (Pattern tools' Write, Melody) use the stored inversion, not voice leading: a write should not depend on
  what was played before it (*my call*).
- The stored inversion is not changed by voice leading: turning it off brings back the inversion that was set.
- The previous chord is RAM only (per track, at most 6 notes), not saved.

## Settings and saving

- **New field `chord_voice`** (4 B, 1 per track, block 2; linked over CTCtrl, rev 1): bits 0–3 the row-2 shape (0 =
  none, 1–5 = power … 6/9; 6–8 kept for pads 14–16, refused until they exist), bits 4–5 voice leading (0 off · 1
  close · 2 top line · 3 bottom line), bits 6–7 spare, 0 (a fourth kind would need one of them). Payload 77 → 81 B (link limit 127 B: `link.c`'s assert).
- **A row-2 shape counts only while `chord_settings`' shape is 0 (off).** Picking a row-2 shape writes it and sets
  the row-1 shape to 0; picking a row-1 shape clears the row-2 shape. A CTCtrl write does the same as the pad (the
  link applies a pick's side effects, as PL12's `link_apply` does).
- **Older builds:** a row-2 shape reads as "off" there, so PL10–PL14 play the pad alone (no wrong chord). PL14 reads
  PL15's longer block 2 (its check covers what is there); a re-save on PL14 writes its own 21 B of block 2, so back on
  PL15 the row-2 shape and voice leading take their defaults (off), as PL14's design intends for fields past an older
  build's payload. On PL13 or older the whole block 2 goes, as today.
- **Load fix-up:** values no pad sets (row-2 shape 6–15, spare bits) go to 0, field by field (the
  rule of PL14's fix 1, so CTCtrl's writes are never blocked by a loaded value).
- **CTCtrl:** `chord_settings` keeps rev 1 and today's CTCtrl keeps working: it shows a row-2 shape as "Single" (its label for shape 0), its
  inversion, spread and bass edits apply, and a row-1 shape it picks replaces the row-2 one (the pad's side effect).
  A write that leaves the shape at 0 leaves the row-2 shape (CTCtrl writes the whole byte for an inversion change).
  A write that changes the inversion turns voice leading off, as the inversion pad does, unless the same write changes
  voice leading too (final review; shape, spread and bass writes leave it).
  CTCtrl's panel learns `chord_voice` later, as with PL14's fields (*my call*: rev 2 would hide every chord control
  in today's CTCtrl until it is updated). `pages/ctplay_link.html` gets the field's name.
- RAM: the new field and the previous chords go to ITCM (the heap tail has 44 B free); `resources.md` gets PL15's
  figures when published.

## The three fixes in this build

1. **Two pads in a draft** (`followups.md`): the pending action runs only when no page pad is held
   (`page_taken == 0` after the release), so a write never runs while a pad is down. Test: down 4, down 7, up 7 (the
   write waits for up 4); Undo with a draft pad held.
2. **The link's write mailbox in one critical section** (`followups.md`): `take_write` sets `REQ_WRITE | REQ_STATE` and
   `req_port` inside its own masked section; `post` stays for hello / read.
3. **Notes held past 16 steps while recording** (`candidates.md`): stock's recorder writes a note held 16 steps or
   more with a flat gate of 96 sixths and loses the rest (`0x0803F85A`). The fix, as upstream's SC45.3 / RC2.04
   `tools/recfix.py`: when the written unit's gate is 96 and the note was held longer, the unit gets the tie bit and
   the same note (microstep, velocity) is written 16 steps later with what is left (at most 96, tied again while more
   is left), wrapping within the pattern's first … last step; a unit of that note there is reused, else a free one;
   none free, or back at the start step, it stops (the last tie taken back). Patterns of 16 steps or less: nothing
   changes. All four note tracks; it covers CTPlay's chord, arpeggio and mono recordings as well as plain notes.
   Upstream's source: `git show 395d9e6:tools/recfix.py` (see "Upstream moved" below); its two patch sites
   `0x0803F856` (the `udiv` that gives the steps held) and `0x0803F89E` (after the unit is written) are inside
   stock's commit `0x0803F7BE`, which slim already hooks at its entry (`rec_commit`, mono record). How slim reaches
   them (a new hook point, or a call hook) is the builder's, following slim's hook rules; the result must be the
   behaviour above, checked in emulation against stock's tie (PL14 showed the tie bit holds across steps). With mono
   record on, a continuation is a held note going on, not a new one: it does not clear the other notes of its step,
   as mono already leaves the steps a held note crosses (*my call*).

**Upstream moved** (found 2026-10-23): `Ghillermo/CIRCUITS-HACKS-RC`'s `main` is now a stub README ("Moved to
Circuit-Hacks-RC"); the last full history fetched here is `395d9e6` (local reflog of `upstream/main`). The `upstream`
remote needs the new URL before the next upstream review; until then `395d9e6` is the reference.

## Code (the builder's, within these lines)

- `features/chord/page.c`: the Chords page's drawing and picks for the new rows; `QUICK_ROW` Chords = 0;
  `page_quick_pad` maps Quick view pads to rows 1–2.
- `features/chord/chord.c` / `chord_math.c`: the five shapes; one accessor for the effective shape (row 1 or row 2)
  used everywhere `CHORD_SHAPE` is read today (play, arp, `euclid.c`, `melody_math.c`); voice leading in the chord
  build on a press; the previous chord per track.
- `features/chord/chord_link.c`: `chord_voice` validity and the pick side effects.
- `features/chord/euclid.c`, `features/link/link.c`: fixes 1 and 2. The recording fix where the builder sees fit
  (its own small feature or the chord feature; it changes nothing in CTPlay's settings).
- `versions/PL15.toml` (marker `PL15`); `versions/PL14.toml` gets its guard comment (PL13's wording).

## Docs in the same build

`ui-map.md` (this spec's tables; the Quick view rule; free pads: Chords 14–16), the user guide (Chords section, Quick
view, Recipes' Chords pad numbers: 9th = pad 4, 7th = pad 3, off = pad 1; "Changes by feature": the palette moved in
PL15), `candidates.md` (this row and the recording fix: built in PL15), `followups.md` (fixes 1–2 done),
`resources.md`, `firmware/PL15/TEST.md`.

## Testing

- **Unchanged sound:** voice leading off, every row-1 shape × inversion × spread × bass: the notes PL14 plays (compare
  with the published PL14 image, as PL14 did against PL13).
- **New shapes:** each one's notes on several degrees and scales, with inversion, spread, bass and rootless; the
  arpeggiator, strum, Write and Melody's chord pool use them.
- **Strum:** the lit speed again turns it off; off shows no speed lit (also with an arpeggio pattern on).
- **Voice leading:** only full candidates (power chord, a chord at the range edge); close, top line and bottom line
  (with and without bass) over a few progressions (e.g. I–vi–IV–V, ii–V–I) against hand-worked
  answers; no drift over a long random progression; the first chord after a load uses the stored inversion; pressing
  an inversion pad turns it off.
- **Pages and Quick view:** every pad of the page and of the Quick view through the real routes (`0x08033282`,
  Shift + Note-view pads), LEDs included (dim stored inversion while leading).
- **Saving:** round trip of `chord_voice`; a PL15 project on the published PL14 and back (re-save drops it to off);
  load fix-ups; CTCtrl writes (link tests) including a row-1 shape write clearing row 2 and an inversion write
  keeping it. Device: today's CTCtrl against a row-2 shape (shows off, inversion edits apply, a row-1 pick replaces).
- **Fixes:** the two-pad draft orders; the link mailbox; recording a note held 20 and 40 steps on a 32-step pattern
  (tie + continuation, units reused / free / none), 16-step patterns unchanged, every note track; with mono record on
  the continuation leaves its step's other notes.
- Device test plan `firmware/PL15/TEST.md` from a new empty project (the user's keyboard-style layout).

## Alternatives considered

- **Keep the layout** (shapes on row 4): rejected by the user, the page stays the odd one out.
- **Quick view = rows 1 and 3** (first-row shapes and voicing): row-2 shapes unreachable while auditioning, and the
  user compares shapes across rows (triad / power, 7th / shell 7).
- **Quick view follows the row of the active shape** (the user's idea): a row-1 shape becomes unreachable from the
  Quick view once a row-2 one is on, and a pad's meaning depends on state you cannot see.
- **Voice leading inside the inversion choices** (one row of six): needed "nothing lit" for spread close and strum
  off and moved bass to row 4; the user keeps bass as the voicing row's last pad.
- **Voice leading on pads 31–32** (the first mockup): the user moved it under the inversions.
- **Voice leading as one 3-way cycle pad**, keeping strum's off pad: rule 3 prefers one pad per value, and the kinds
  are not ordered (close to bottom line would take two presses); strum is an amount, like the rows that already use
  "none lit = off".
