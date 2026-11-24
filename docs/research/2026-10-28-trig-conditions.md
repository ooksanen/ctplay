# Conditional step triggers ("trig conditions") on other sequencers (research, 2026-10-28)

Date: 2026-10-28. Background for a CTPlay feature: a per-step condition picked on one row of 8 pads (row 4 of stock's
probability view; row 3 holds stock's 8 probability levels), stored in a few spare bits per step.

Sources are linked per item. **(unverified)** marks anything from my own memory or from my reading of a source, not
from a page I read this session. Manuals change with firmware.

Blocked or not read:
- **reddit.com is blocked** for this tool (search and fetch). No r/Elektron, r/synthesizers or r/novationcircuit posts
  are quoted. Forum quotes are from Elektronauts, Squarp's forum, ModWiggler, Gearspace and Polyend Backstage.
- YouTube videos were found but not watched (no transcripts).
- Not read in full: Digitakt II manual section 11.2 (TRIG PAGE 1), Bitwig's Voice Stacking text, the Deluge FIRST /
  LAST semantics, the Hapax X:Y range, the Polyend Mess manual, the Five12 Vector fill pages.

## 1. Summary: condition types ranked by how much musicians value them

1. **Probability (%)**. Every product has it. It is the default "variation" tool. Users like it for ghost notes and
   humanising, but several say pure randomness "didn't add much" or "just got weird". The Circuit has it already.
2. **Every n loops (A:B, "1 of 4", Play N / Skip M, Recurrence)**. The most-named condition in user posts:
   "1:2, 2:2, 4:4", "2:2 in almost every pattern for tom fills", "the last of n bars: 2:2, 3:3, 4:4". It makes a
   1-bar pattern sound like 2, 4 or 8 bars. Same result every time, so it is safe live.
3. **FILL / NOT FILL** (Elektron, Hapax, OXI "Flow", Deluge, Bitwig). Called "my favorite trig condition". It gives
   a hands-on variation with one button. The common complaint: people forget to press it, and a fill note needs a
   free step next to the normal note.
4. **FIRST / NOT FIRST**. Simple intro / "every time after the first" tool. Confusing when patterns are chained: the
   count restarts on each pattern change.
5. **PRE / NOT PRE ("with previous") and linked random groups**. Strong when combined with %: one dice roll decides
   a whole fill or phrase. Users praise it ("unexpectedly brilliant bonus") but many find it confusing. Polyend Play's
   "Group with last", Ableton's "Play All" groups and Bitwig's "with Previous" are the same idea in plainer form.
6. **Custom pass masks** (Deluge custom iterance, Bitwig Recurrence, Korg drumlogue ALTER). Pick a cycle of 2–8
   passes and tick the passes that play. A superset of A:B. It maps well to a row of pads.
7. **LAST / NOT LAST** (Elektron, new on Syntakt OS 1.40 and Digitakt II; Deluge LAST). Plays on the pass before a
   pattern change. Useful for transitions in chains. Little user discussion yet.
8. **NEI / NOT NEI** (Elektron only). Follows the previous track's last condition. Niche (layering, call between
   kick and snare) and the most confusing one; even the forum disagrees on its edge case.
9. **Note-count and position conditions** (Hapax NT / PS / PB / SYNC). Niche. No user discussion found.
10. **Fixed (seeded) randomness** (Torso T-1, Bitwig seed). The random choice is made once and repeats, until
    re-rolled. Not a per-step condition, but a frequent answer to "random, but the same every loop".

Not found anywhere: "never twice in a row", "random once per loop" as a per-step condition. The closest are
PRE with %, "Group with last", Ableton "Play One", Hapax Chance effect "Lot".

## 2. Condition × product table

Y = has it, – = not found, ? = not confirmed. "Pass" = one play-through of the pattern (or of the track, if shorter).

| Product | % | A:B (every n) | NOT A:B | Pass mask | FILL / !FILL | 1ST / !1ST | LAST / !LAST | PRE / !PRE | NEI / !NEI | Linked random | Other |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Elektron Octatrack (OS 2017) | Y, 21 values | Y, 1:2–8:8 | ? | – | Y | Y | – | Y | Y | via PRE | 64 settings total |
| Elektron Digitakt (I), Model:Cycles | Y (in COND; overrides track PROB / CHANCE) | Y, to 8:8 | ? | – | Y (in COND) | ? (Cycles list read: no 1ST) | – | Y | Y | via PRE | |
| Elektron Digitakt II | Y, own slot (PROB) | Y | Y | – | Y, own slot (FILL) | Y | Y (LST) | Y | Y | via PRE | PROB, FILL, COND stack on one trig |
| Elektron Syntakt (OS 1.40+) | Y | Y | Y (added 1.40) | – | Y | Y | Y (added 1.40) | Y | Y | via PRE | |
| Elektron Analog Rytm / A4 | Y | Y | ? | – | Y | Y | ? | Y | Y | via PRE | PRE / NEI since OS 1.22B |
| Torso T-1 | Y, bipolar, fixed pattern | – | – | – | – (TEMP hold / latch) | – | – | – | – | fixed seed | Cycles: up to 16 variations played in turn; random skip / repeat of a cycle |
| OXI One MKII | Y | Y, 1:2–8:8 | Y | – | Y ("Flow" / "No Flow") | Y | – | Y | – | via PRE | Fixed, Locked (safe from generators); conditions on repeats and accumulator too |
| Squarp Hapax | Y, own param (CHANCE) | Y (X:Y) | Y | – | Y | Y | – | Y | – | Chance effect "Lot" | SYNC, NT / PS / PB note counts, NO FX, FX IF FILL |
| Squarp Pyramid | Y | – | – | – | – | – | – | – | – | – | chance MIDI effect |
| Polyend Play | Y, 90–10% | Y (Play N / Skip M, Skip N / Play M) | via Skip/Play | – | – | – | – | Y ("Group with last") | – | Y | Chance + Action (random sample, note, repeat, humanize) |
| Polyend Tracker / Tracker+ / Mini | Y (Chance FX) | – (official) | – | – | – | – | – | – | – | – | unofficial CT2 mod adds 1:2–8:8, PR, NE, 1S, Fill |
| Synthstrom Deluge (community fw) | Y | Y (1 of 2 … 8 of 8) | – | Y (custom, divisor 1–8) | Y | Y (FIRST) | Y (LAST, semantics unread) | – | – | – | all three independent since c1.3; Fill clips |
| Bitwig Studio operators | Y (seeded) | via Recurrence | – | Y (Recurrence, 1–8) | Y (Fill on / off) | Y | – | Y (with / without Previous) | – (but Prev Key, Prev Chan.) | Y | Repeats (ratchets) |
| Ableton Live 12 / Push 3 | Y | – | – | – | – | – | – | – | – | Y (Play All / Play One) | velocity range |
| Intellijel Metropolix | Y, per stage | – | – | – | – | – | – | – | – | – | skip; a mod lane can invert skips |
| Five12 Vector | Y (Chance Ops) | partly: even / odd / every 3rd / 4th bar | – | – | per-part Fill Enable | – | – | – | – | – | the op is chosen: skip, mute, jump, ratchet, pitch… |
| Arturia BeatStep Pro | track / project only | – | – | – | – | – | – | – | – | – | Randomness + Probability knobs |
| Arturia KeyStep Pro | Y, per step | – | – | – | – | – | – | – | – | chord all or none (user report) | |
| Roland TR-8S | Y, step and sub step | – | – | – | auto fill every 2–32 bars, manual trig | – | – | – | – | – | 2 fill variations per pattern |
| Novation Circuit Rhythm | Y, 8 levels (12.5%) | – | – | – | – | – | – | – | – | – | micro steps, Mutate |
| Novation Launchpad Pro MK3 | Y, 8 levels on a pad row | – | – | – | – | – | – | – | – | – | Mutation, 8 levels |
| monome Kria | Y, 4 levels, per parameter | – | – | – | – | – | – | – | – | – | |
| Korg drumlogue | Y, 0–100% | via mask | – | Y (ALTER, 2–4 passes) | – | – | – | – | – | – | ratchet, micro offset |
| Korg wavestate / modwave | Y (lane step) | – | – | – | – | – | – | – | – | – | a skipped step pulls later steps earlier |
| 1010music Bento / Blackbox | Y | ? (one review says yes; forum says no) | – | – | – | – | – | – | – | – | |
| norns gridstep (script) | Y | Y | – | – | – | Y | – | Y | – | via PRE | |

Notes:
- Elektron's Octatrack list has 64 settings. 21 % values + 8 (FILL, PRE, NEI, 1ST and their negations) + 35 (A:B
  with B = 2…8) = 64. So A:B runs 1:2 to 8:8 (my arithmetic; the 8:8 end matches OXI's manual).
- Digitakt II: the Sound On Sound review says "separate slots for Probability, Fill and Condition". The example: a snare
  that plays only in Fill, every other bar, 70% of the time. That all three must be true is my reading **(unverified)**.

## 3. Each condition in detail

### 3.1 Probability (%)
- **Semantics.** A fresh dice roll each time the step comes round (Elektron, OXI, Hapax, Live, Polyend). Exceptions:
  Torso T-1 rolls once and keeps the result ("rolling all of the dice once and deciding which pulses are or are not
  fired"); the RANDOM knob re-rolls, and VB8 / VB16 shift the pattern of skips in time. Bitwig's Chance follows the
  clip's Seed.
- **Values.** Elektron: 21 values, 1 2 4 6 9 13 19 25 33 41 50 59 67 75 81 87 91 94 96 98 99 %. Polyend Play: 90 to
  10 in tens. Circuit Rhythm and Launchpad Pro MK3: 8 levels, 12.5% apart. Kria: 4 levels (100 / 50 / 25 / 0).
- **Chords.** Launchpad Pro MK3 rolls each note of a step on its own. A KeyStep Pro user found the whole chord plays
  or none. Live 12 lets the user choose (Play All / Play One groups).
- **UI without a screen.** Launchpad Pro MK3: the top pad row is a slider for the held step (1 pad lit = 13%,
  8 lit = 100%). Kria: the 4 middle rows of each column are a fader.
- Sources: [Elektronauts % values](https://www.elektronauts.com/t/trig-condition-values-solved/108379),
  [T-1 Velocity & Probability](https://docs.torsoelectronics.com/t1/parameter-reference/groove/velocity-probability/),
  [Launchpad Pro MK3 sequencer](https://userguides.novationmusic.com/hc/en-gb/articles/25494505907346-Using-Launchpad-Pro-MK3-s-Sequencer),
  [Kria docs](https://monome.org/docs/ansible/kria/),
  [Ableton Live 12 Editing MIDI](https://www.ableton.com/en/live-manual/12/editing-midi/),
  [Polyend Play manual](https://polyend.com/manuals/play/).

### 3.2 A:B (every n passes)
- **Semantics (Elektron).** "A sets how many times the pattern plays before the condition is true; B sets how many
  times the pattern plays before the count is reset." 1:2 plays on passes 1, 3, 5; 2:2 on 2, 4, 6; 2:4 on 2, 6, 10;
  4:7 on 4, 11, 18. NOT A:B plays on every other pass.
- **What is a pass.** The pattern, or the track if the track is shorter than the pattern (Digitakt II manual). How
  per-track scale or M.LEN = INF changes this was not found (open question).
- **Reset.** The count starts at play. A pattern change resets it: "any trig condition which is dependent on the same
  pattern playing through more than once to achieve will be negated by changing to any other pattern". In song mode
  users could not predict the count; a workaround is a muted 2-step dummy pattern before the section.
- **Values.** Elektron and OXI: 1:2 to 8:8 (35 values; OXI lists 1:2, 2:2, 1:3, 2:3, 3:3 … 8:8). Deluge: 1 of 2 to 8
  of 8. Polyend Play: Play N / Skip M and Skip N / Play M (e.g. Play 3 | Skip 1, then Skip 3 | Play 1 for a fill every
  4th bar). Five12 Vector: even bars, odd bars, every 3rd or 4th bar.
- **Polyend Play quirk.** "When working on a single pattern … Play/Skip values always trigger steps as it was the first
  loop iteration"; it only counts in Pattern mode chains. Users asked for real A:B on the Tracker.
- **UI.** On Elektron, OXI, Hapax and gridstep the A:B values come after the % values on the same knob, so users
  "had to scroll through all the percentages to reach them".
- Sources: [Digitakt II manual p. 48](https://www.manualslib.com/manual/3436437/Elektron-Digitakt-Ii.html?page=48),
  [OXI One MKII manual p. 59–61](https://www.manualslib.com/manual/4203168/Ox-One-Mk-Ii.html?page=60),
  [Trig Conditions and Song mode](https://www.elektronauts.com/t/trig-conditions-and-song-mode/241960),
  [Polyend Play: 10 ways with Chance/Action](https://polyend.com/whats-up/polyend-play-10-ways-to-get-creative-using-chance-action/),
  [Polyend Backstage A:B request](https://backstage.polyend.com/t/a-b-conditions-for-each-sequencer-pass/909).

### 3.3 Pass masks (custom iterance, Recurrence, ALTER)
- **Deluge (community c1.3+).** Hold a note, press Select, NOTE ITERANCE → CUSTOM. "DIVISOR (from 1 to 8)" sets how
  many "ITERATION #" toggles appear; "each ITERATION # allows you to activate or deactivate an iteration step".
  Presets 1 of 2 … 8 of 8 remain, plus FIRST and LAST.
- **Bitwig Recurrence.** "Pick a cycle length (say, every four loops of the clip), and then check-off whether the event
  plays on each of those four passes." Length 1 (off) to 8.
- **Korg drumlogue ALTER.** Values ALWAYS, ■□, □■, ■□□ … ■■□■: "[■□□] means the step is only played on the first of
  three cycles, while [□■■] … on the second and third". Longest shown is 4 passes.
- **Fit.** A mask is the most direct picture on a pad row: one pad per pass, lit = plays. It needs the cycle length
  stored too (open question 1).
- Sources: [Deluge community features](https://delugecommunity.com/features/community_features/),
  [Bitwig operators](https://www.bitwig.com/userguide/latest/operators/),
  [drumlogue manual p. 19](https://www.manualslib.com/manual/2854358/Korg-Drumlogue.html?page=19).

### 3.4 FILL / NOT FILL
- **Semantics.** FILL plays only while fill mode is on; NOT FILL only while it is off. Pairing them on neighbouring
  steps swaps a note for a variation ("put the 4/4 kick on !fill condition to avoid playing both", Hapax forum).
- **Elektron.** Digitakt I / Model:Cycles: FILL is in the COND list, and a condition overrides track PROB / CHANCE.
  Digitakt II: FILL is its own parameter on TRIG PAGE 1. Fill-conditioned trigless locks are popular (a bit-crushed
  hi-hat that only appears in fill).
- **Hapax.** While FILL is held, recorded notes get MATH = FILL; the pads light the FILL notes. FILL is also a
  mod-matrix source, and FX IF FILL / NO FX IF FILL route notes to effects.
- **OXI One MKII.** "Flow" / "No Flow" on the step's Trig parameter; repeats and the accumulator can also follow Flow.
  Sound On Sound calls Flow "a kind of super-fill mode".
- **Deluge.** FILL and NOT FILL sit at the start of the probability range. While the fill button is held, FILL notes
  light blue and NOT FILL notes red.
- How fills are engaged: section 4.
- Sources: [Fill conditioned effects](https://www.elektronauts.com/t/fill-conditioned-effects/41223),
  [Hapax manual, step mode](https://squarp.net/hapax/manual/modestep/),
  [Hapax fill automation thread](https://squarp.community/t/automation-for-the-fill-button/12059),
  [Sound On Sound OXI One MkII](https://www.soundonsound.com/reviews/oxi-one-mkii),
  [Takazudo OXI guide EP.4](https://takazudomodular.com/en/guides/oxi-one-mkii-guide-ep4/).

### 3.5 FIRST / NOT FIRST
- **Semantics.** "1ST is true the first pattern iteration (ie. until the pattern has looped)" (Octatrack notes). NOT
  1ST plays on every pass but the first. OXI, Hapax, Bitwig ("on First / never First", counting clip retriggers) and
  Deluge have it.
- **Confusion.** On the Octatrack in arrangement mode a 1ST cymbal played every time: "once it goes to another pattern,
  and then back to the pattern with this condition, it plays it again" (Gearspace).
- Sources: [Synthtopia, Octatrack trig conditions](https://www.synthtopia.com/content/2017/11/04/elektron-updates-octatrack-os-adds-trig-conditions/),
  [Gearspace, OT conditional lock in arrangement](https://gearspace.com/board/electronic-music-instruments-and-electronic-music-production/1226169-elektron-octatrack-mkii-conditional-lock-not-working-arrangement.html).

### 3.6 LAST / NOT LAST
- **Semantics (Elektron).** LST plays "the last time the pattern plays before changing to another pattern"; NOT LST
  skips that pass. It needs a queued pattern change to know which pass is last. Added on Syntakt in OS 1.40 ("Added
  new trig conditions: LST, Not LST, Not A:B"); in the Digitakt II manual.
- Deluge has a LAST iterance; its meaning (last pass of a section repeat?) was not found **(unverified)**.
- Sources: [Syntakt OS release notes](https://www.elektron.se/release-notes/syntakt-os-release-notes),
  [Deluge PR #4891](https://github.com/SynthstromAudible/DelugeFirmware/pull/4891).

### 3.7 PRE / NOT PRE (previous condition)
- **Semantics (Elektron).** "PRE is true … if the most recently evaluated trig condition on the same track was true."
  PRE and NOT PRE steps are skipped when looking back, so a chain of PRE steps all follow the last real condition.
  Track probability is "not a condition and thus has no influence on pre/nei". Manual example: 50% (true) → NOT PRE
  (false) → NOT PRE (false) → PRE (true).
- **Typical use.** A 50% kick then a PRE kick: both or neither. "If you program a pattern variation using PRE … but
  set the first note of the variation to use a probability condition, then the whole variation will depend on whether
  or not the first note triggered." It works after any condition, not only %.
- **Same idea elsewhere.** OXI PRE ("nearest prior trig condition"), Hapax PRE ("last condition of track was valid"),
  Bitwig "with / without Previous" (plus "Prev Key" for the same pitch, "Prev Chan."), Polyend Play "Group with last"
  ("either none or all are played"), Live 12 "Play All" groups.
- **Limits users hit.** No "pick one of three": "the third trig can't reference the first trig's condition result";
  a user asked for a "group random" condition. On Hapax, Chance 33% plus !PRE on two notes did not give "one of three".
  Live 12's "Play One" group does this.
- What PRE sees on the first conditional step of a pass (the previous pass's last result?) is not documented
  **(unverified)**.
- Sources: [PRE and NEI confusing me](https://www.elektronauts.com/t/pre-and-nei-confusing-me/17252),
  [combined conditions / logic](https://www.elektronauts.com/t/trig-conditions-combined-conditions-logic/47851),
  [Hapax MATH question](https://squarp.community/t/math-condition-question/12084).

### 3.8 NEI / NOT NEI (neighbour track)
- **Semantics.** Same as PRE, but it reads the last condition evaluated on the track before (track 3 for track 4). The
  manuals say it is false when the neighbour has no conditional trigs; one Elektronauts post says true.
- **Use.** Layering one sound from two tracks (set every step of track B to NEI); a snare that plays only when the kick
  did (NEI) or did not (NOT NEI).
- **Confusion.** "these two hurt my head"; the wording "is misleading: it looks at the previous track but affects the
  track the condition sits on". Only Elektron has it.

### 3.9 Other kinds
- **Hapax.** SYNC (note added on the first step of a beat), NT=0 / NT<n (fewer than n other notes play now), PS / PB
  (fewer than n notes on the last step / last beat), NO FX.
- **OXI.** Fixed and Locked: Euclid and random generators do not change the step.
- **Five12 Vector.** The condition chooses an action, not only play / mute: skip, mute, jump, velocity, gate, ratchet,
  pitch, each with a % and a bar filter. MkII has two Chance Ops per step.
- **Polyend Play.** Chance decides *when*, Action decides *what*: random sample, note, octave, cutoff, repeat, start /
  end, humanize.
- **Torso T-1 Cycles.** Up to 16 stored variations of a track played one after another; random modulation can skip the
  next cycle or repeat the current one. Variation by whole passes, not per step.

## 4. How fills are engaged

| Product | How |
|---|---|
| Digitakt II | Hold [PAGE] (momentary). Latch: hold [PAGE] + [YES], release [PAGE] first; press [PAGE] to unlatch. [YES] + [PAGE] = fill for one pattern cycle: starts when the pattern loops, ends at the next loop. |
| Model:Cycles | Hold [PAGE]; [TRACK] + [PAGE] latches. |
| Squarp Hapax | Dedicated FILL button, momentary only. Users asked for a pedal / latch; workaround is a fill pattern. |
| OXI One MKII | Hold [Flow]. MkI: the Play button can be set to act as a FILL modifier. |
| Deluge (community) | The SYNC-SCALING button, re-purposed in settings, or a MIDI command. Fill notes light while held. Fill *clips* start so that they end at the next loop. |
| Bitwig | Global Fill mode (performance control). |
| Roland TR-8S | AUTO FILL IN: on, every 32 / 16 / 12 / 8 / 4 / 2 bars; MANUAL TRIG for a one-off. 2 fill variations per pattern. |
| Polyend Play | No fill mode; "Skip 3 / Play 1" gives a fill every 4th bar. |
| Torso T-1 | No fill. [TEMP]: hold for temporary edits, release to revert; double-tap to latch. |

Sources: [Digitakt II manual p. 49](https://www.manualslib.com/manual/3436437/Elektron-Digitakt-Ii.html?page=49),
[Model:Cycles via search of the manual](https://www.manualslib.com/manual/1790470/Elektron-Cycles.html?page=32),
[Hapax fill automation](https://squarp.community/t/automation-for-the-fill-button/12059),
[OXI MkI beta note, ModWiggler](https://www.modwiggler.com/forum/viewtopic.php?t=240039&start=525),
[TR-8S reference manual](https://static.roland.com/assets/media/pdf/TR-8S_Reference_eng05_W.pdf),
[Roland AU fills guide](https://rolandcorp.com.au/blog/the-ultimate-guide-to-the-tr-8s-rhythm-performer-creating-and-playing-fills),
[T-1 quick commands](https://docs.torsoelectronics.com/t1/appendix/quick-commands/).

What the users say about fills:
- Momentary is the norm; latch is a second gesture (Elektron) or missing (Hapax). "You gotta hold the button."
- "I like the FILL mode too, but forget to press the button a lot" (hotscience).
- Elektron's "one cycle" fill (starts at the loop) avoids a fill that starts mid-bar.
- A fill note needs a free step: fills are "sorta limited to having to have empty trigs next to the original notes"
  (pidgeo); the workaround is a neighbour step micro-timed onto the same spot.

## 5. What users praise and complain about

Praise and uses:
- "The conditions I use the most are 1:2, 2:2, 4:4", for variation and snare ghost notes (Elektronauts, via search).
- "I use 2:2 in almost every pattern for tom fills" (hotscience).
- "Adding variation at the beginning (1/2 or 1/4) or end (2/2, 4/4 etc.) is a great way to extend the length"
  (dustmotes). Future Music's "double and add 1" tip is the same idea.
- Melodic: two adjacent synth-stab trigs on 1:2 and 2:2, micro-timed together, change the pitch every 4 bars without a
  second pattern (AdamJay). A second melody line on 2:2 fakes 128 steps from 64 (Frenzies). Dub chords on 2:7 with
  random filter (ZaBong). Call and response with 1:2 / 2:2 is an obvious use, but no tutorial was found.
- Fill: "My favorite trig condition!" (LyingDalai); fill-conditioned trigless locks for an extra hi-hat.
- PRE / NEI: "an unexpectedly brilliant bonus" (rikrak); % with PRE / NEI "for beat juggling and stuttering" (Flohr).
- Digitakt II stacking: Sound On Sound calls more than one condition per step "a big step forward".

Complaints and confusion:
- Randomness: "random triggering didn't add much to the quality of my music"; overuse makes patterns "random and
  un-musical" (AGP1).
- Notation: users "couldn't parse" A:B; asked how 50% differs from 1:2 (answer: 1:2 is fixed, 50% is a coin).
- PRE / NEI: "these two hurt my head"; NEI's edge case is disputed.
- Chains / song mode: A:B, 1ST counts restart on every pattern change, so 2:2 never plays if the pattern changes after
  one pass.
- Scrolling: A:B values sit after 21 % values on one knob.
- One condition per step (before Digitakt II): users wanted "a 3:4 condition which is then also qualified by a
  percentage".
- No "pick one of n" random group.
- Sources: [How do you use conditional triggers?](https://www.elektronauts.com/t/how-do-you-use-conditional-triggers/42272),
  [A4 trig conditions thread](https://www.elektronauts.com/t/a4-k-mkii-trig-conditions-thread/16997),
  [Probability & Trig Conditions](https://www.elektronauts.com/t/probability-trig-conditions/235508) (search snippet only),
  [Sound On Sound Digitakt II](https://www.soundonsound.com/reviews/elektron-digitakt-ii).

## 6. Fit notes for CTPlay (my reading, not from sources)

- An Elektron-style set fits 4 bits exactly: off, 1:2, 2:2, 1:3, 2:3, 3:3, 1:4, 2:4, 3:4, 4:4, FILL, NOT FILL, 1ST,
  NOT 1ST, PRE, NOT PRE = 16 values. Users' most-named values (1:2, 2:2, 4:4) are inside it. 8:8 is not.
- Upstream's "every n passes, plays on the last pass" (3 bits) is n:n: the "last of n bars" form users name
  (2:2, 3:3, 4:4). It lacks 1:2-style "first of n" and the swaps (1:2 / 2:2 pairs).
- On 8 pads: "one pad per pass" (a mask, as Deluge / Bitwig / drumlogue) is the clearest picture but needs 8 bits plus
  a length. A:B can be shown as "B pads lit dim, pad A lit bright" with one press for B and one for A **(idea)**.
- FILL needs a hold gesture. Elektron's "fill for one cycle, starting at the loop" is a good model for a single press.
- Counts per track vs per pattern, and reset on pattern change, are the main confusion sources elsewhere; whatever
  CTPlay picks should be stated and shown.

## 7. Open questions

1. What does a pass mean with per-track lengths and pattern chains on the Circuit? Elektron counts the track when it is
   shorter than the pattern; behaviour with scale per track or M.LEN = INF was not found.
2. Does the count reset on a pattern change (Elektron: yes, and users dislike it in song mode), or carry on?
3. What does PRE see on the first conditional step of a pass? Not documented anywhere read.
4. Digitakt II: is PROB × FILL × COND an AND? Likely, not stated in text read.
5. Deluge FIRST / LAST semantics; Hapax X:Y range; Polyend Mess condition list.
6. Drums: does a condition apply per drum step only, or also per micro step (Circuit's probability is per step, all
   micro-step hits play or none)?
7. Do Circuit users ask for conditions? No Circuit-forum evidence found (reddit blocked).
