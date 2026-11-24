# How other instruments generate melodic and rhythmic ideas (research, 2026-10-19)

Background for a CTPlay feature: a quick way to write melodic ideas (bass lines, arpeggio-like parts) into a pattern,
and better rhythm variation for melodic parts. Today the Euclid writer (`specs/2026-10-17-euclidean-design.md`) gives
every hit the same pitch, and only the density changes.

Sources are linked per device. "Not confirmed" means only a shop page, a forum post or my own memory says it. Web
research on 2026-10-19; manuals change with firmware.

## 1. Summary

The same small set of ideas comes back on almost every device:

- **A note pool, then a rule to walk it.** The user gives the notes (held chord, a scale, a range); the machine picks
  the order. Rules are arp orders (up, down, up-down), "climb" (two up, one back), contour shapes (ramp, triangle,
  sine), or a random pick, often weighted toward some notes. T-1, OXI, Hapax, Live 12, Marbles, Turing Machine.
- **Rhythm and pitch are separate layers.** A rhythm (Euclid, density, learned patterns) decides *when*; a second layer
  decides *which note*. The user can keep one and re-roll the other. T-1, OXI (Order / Pitch shuffle), Live 12, Wavestate.
- **Beat-weighted density.** Notes are more likely on strong beats (step 1, 5, 9, 13) than on off-beats. This gives
  bass-line rhythms that pure Euclid does not. Acid Banger, Grids, Live's Rhythm (accent frequency).
- **Accents, ties and repeats make a line musical**, more than the pitches do: accent curves (T-1), "every N" accents
  and ghost notes (Hapax), tie probability (OXI, Live), ratchets with a velocity ramp (T-1, SQ-64, Hydrasynth).
- **Keep what you like:** Undo (OXI), a seed number (Hapax Curves), a lock / slip knob (Turing Machine, Marbles,
  Deluge Randomizer), editing only a selection (Hapax, Live 12), or "duplicate the pattern first" (Circuit, no Undo).
- **Variation over loops:** conditions (Elektron A:B, Fill), iterance (Deluge), cycles (T-1), per-step probability.

Best fit for CTPlay (output written into a stock pattern, few pads, small RAM): a **"Notes" layer on top of the Euclid
hits** (pitch from the held chord or the scale, walked by an arp-like order or a shape, octave range), **separate
re-roll for rhythm and notes** with a small seed, **accent / length / tie rules**, **beat-weighted density** as a second
rhythm source, and **transforms of the current pattern** (shuffle notes, reverse, mirror). All of these write normal
steps, so they play on official firmware. Live, play-time ideas (slip, deja vu) are the weakest fit.

## 2. Devices

### Torso T-1 (algorithmic sequencer)
- **Controls:** per track Steps, Pulses, Rotate (Euclid), Repeats + Ramp, Pitch (up to 8 notes), Scale, Root,
  Voicing + Style, Range + Phrase, Harmony, Accent + Groove, Velocity, Sustain, Timing, Cycles. Most knobs have a
  second function on CTRL + turn.
- **Pitch:** you enter a small note pool (2-4 notes advised). **Voicing** moves the lowest note up an octave or the
  highest down; **Style** says how that motion runs over time: Fixed, Ramp, Climb (two forward, one back), Up/Down,
  Climb Up/Down, each poly or mono. **Range** sets how much melodic movement; **Phrase** picks its shape: Cadence 1-4,
  Saw, Triangle, Sine, Pulse. **Harmony** moves one chord note at a time inside the scale.
- **Rhythm / length:** Euclid pulses; Repeats add 0-48 extra hits per pulse, Ramp makes them louder or softer.
  **Accent** adds velocity movement around the base velocity; **Groove** picks its curve: Agogo, Timbales, Congas,
  Bongo, Saw, Triangle, Sine, Pulse, over 1-64 bars.
- **Random:** turn a knob while holding RANDOM to set a random range per parameter. Some are rolled once per cycle
  (Steps, Pulses, Pitch, Velocity, Scale), others at a "random rate". The two turn directions differ, e.g. per note of
  the chord vs. the whole chord. Shop pages say randomness "can be locked into loops" (not confirmed in the docs).
- **Keep / vary:** **Cycles** store up to many versions of a track that play in turn (a sparse start, more pulses,
  stronger accent ...).
- **Written or live:** live (generated as it plays); you edit the parameters, not notes.
- **Users:** praised for fast riffs; one owner says it is "bad at" picking an exact note at an exact time.
- **Sources:** https://docs.torsoelectronics.com/t1/core-concepts/pitch-chords/generating-melodies/ ·
  https://docs.torsoelectronics.com/t1/parameter-reference/shape/voicing-style/ ·
  https://docs.torsoelectronics.com/t1/parameter-reference/shape/range-phrase/ ·
  https://docs.torsoelectronics.com/t1/parameter-reference/shape/repeats-ramp/ ·
  https://docs.torsoelectronics.com/t1/parameter-reference/groove/accent-groove/ ·
  https://docs.torsoelectronics.com/t1/appendix/random-behavior/ · https://docs.torsoelectronics.com/t1/core-concepts/cycles/ ·
  https://www.elektronauts.com/t/torso-t1-algorithmic-sequencer/115770?page=53

### OXI One / One MKII (step sequencer)
- **Random Generator** (Shift + Random, in Mono, Poly and Chord modes): **Bias** (centre of the new notes, in scale
  steps), **Range** (spread around Bias, both directions), **Rand** (low = arpeggio-like, high = less repetitive),
  **Dens** (note density). Second page: random scale and root, **Humanize** (timing, gate, velocity), **Ties**
  (chance of tied notes). The MKII adds V&G (velocity and gate) and **Flip** (not described in what I could read).
- **Transform instead of generate:** **Order** shuffles the order of the existing notes; **Pitch** shuffles only the
  pitches of the active steps (rhythm kept). Multitrack mode also has a Euclidean generator on the same button.
- **Stochastic mode:** the grid becomes a settings page: one probability per note of the 12 (a weighted scale),
  trigger probability, chance of a new note vs. replaying the buffer, division randomizer, octave range, and two
  "how much changes" amounts (0 % = loop the same notes / rhythm).
- **Chord mode:** chord keyboard on the grid (chord type from the scale), a chord arpeggiator with octave offset.
- **Keep / re-roll:** the generator is destructive (start to end point) but **Undo** returns the previous sequence.
- **Written or live:** Random Generator writes steps (editable); Stochastic mode is live.
- **Users:** generator praised for jamming and melodies; the arranger is called its weak point.
- **Sources:** https://www.manualslib.com/manual/3391381/Oxi-Instruments-One.html?page=37 (and pages 38, 59, 69) ·
  https://www.matrixsynth.com/2026/02/first-steps-with-oxi-one-mkii-ep-6.html ·
  https://www.elektronauts.com/t/oxi-one-hardware-sequencer/141839?page=75

### Squarp Hapax (sequencer)
- **Algorithms** (offline, applied to the pattern or a selection):
  - **Generator:** grid, note length min / max, velocity min / max, density 0-100 %, polyphony (mono, 2, 3, 4),
    pitch min / max. A Squarp developer said it follows the project scale (older firmware).
  - **Curves:** a wave (sine, triangle, ramp, square, random, Perlin) written to a destination (pitch, velocity,
    length, roll, micro-timing), with repeat, phase, steps and a **seed 0-9999**.
  - **Shuffle** (single notes or whole parts, with a probability), **Symmetry** (flip in time, or flip pitches),
    **Every N** (accent every Nth note, the rest as ghost notes).
- **Effects** (live, not destructive): Arpeggiator (style, rate, gate, human, octave), **Arpoly** (8 steps of
  transpose / tie / random / jump, 3 loops of different lengths), Chance, Echo, Euclid (steps, pulses, rotate, gate),
  Harmonizer (up to 7 extra intervals).
- **Keep / re-roll:** apply to a selection only; the Curves seed makes a result repeatable. Undo not stated on the
  algorithms page (not confirmed).
- **Users:** a user writes notes with Generator, then edits them into variations; another calls generative tools
  "largely gratuitous" for most producers.
- **Sources:** https://squarp.net/hapax/manual/modealgos/ · https://squarp.net/hapax/manual/modefx/ ·
  https://www.elektronauts.com/t/squarp-instruments-hapax-polychronic-performance-sequencer/168655/1615

### Squarp Pyramid
- Live MIDI effects, up to four per track: Arpeggiator, Randomizer (velocity, pitch, octave or length, with low / high
  limits and a % chance), Humanizer, Harmonizer, Swing, Delay, LFO. A separate Euclidean sequencer type per track.
- **Written or live:** live. **Sources:** https://www.soundonsound.com/node/4917023 ·
  https://cdm.link/pyramid-high-end-standalone-midi-analog-sequencer-effects/

### Polyend Play / Play+ (sample / MIDI groovebox)
- **Fill tool** (writes steps): Beat (128 genre presets), Kick / Snare / HiHat, **Chords and Bass** (four chord tracks
  plus one bass track, up to 64 steps), Chords, Bass, Euclidean (1-64 events), Random (density 10-100 %), **Random+**
  (random places plus random notes; "smart melody randomizer" in firmware 1.4). Press Fill again for a new result.
- **Randomize:** a % range plus a type (sample, octave 1 / 2, volume ...). Shown while the screen is open; Save
  "prints" it to the steps, Shift + Save draws again. **Chance / Action** per step: a random change after the step plays
  (note, octave up, repeat ...) or Humanize; live.
- **Perform mode:** Rearrange (playhead shuffler), Repeat (step repeater), live only.
- How Chords and Bass pick notes is not documented (not confirmed).
- **Sources:** https://polyend.com/manuals/play/ · https://polyend.com/whats-up/news/polyend-play-1-4-firmware-update/ ·
  https://backstage.polyend.com/t/polyend-play-how-to-make-a-melodyfill-bass-and-chord-pattern/4289

### Synthstrom Deluge (official and community firmware)
- Per note: **probability** (Select knob left) and **iterance** (right: play on pass 1 of 4, etc.; custom iterance
  picks passes with a divisor 1-8). **Fill** notes play only while Fill is held. Notes at one step with the same
  probability value play together or not at all (useful for chords).
- **Randomizer** (Sound menu): velocity spread, note probability, reverse probability, and **Lock**, which freezes the
  current random values into a repeatable pattern. Probability by row (works well with Euclid rows).
- **Written or live:** probability and iterance are stored per note but rolled live.
- **Sources:** https://delugecommunity.com/features/community_features/ · https://synthtopia.com/?p=94108

### Elektron (Digitakt, Syntakt, Digitone ...)
- **Trig conditions** per step: X % probability, **A:B** (play on pass A of every B passes), FILL / not FILL, PRE
  (same result as the previous condition on this track), NEI (as the neighbour track), 1ST (first pass only).
  **Parameter locks** set any value per step.
- **Euclidean mode** per track (Syntakt OS 1.30, Digitakt II): two pulse generators, each with its own rotation,
  combined by a logic operator (OR and others) (details from memory and a forum post: not confirmed).
- **Written or live:** conditions are stored in the pattern and decided live. Users praise conditions for "fills
  without new patterns"; NEI / PRE are often called hard to understand.
- **Sources:** https://www.elektronauts.com/t/digitakt-unofficial-guide/40705 ·
  https://www.elektronauts.com/t/trying-to-wrap-my-head-around-nei-trig-conditions/173080 ·
  https://www.elektronauts.com/t/euclidean-mode-rhythms/51170?page=2 · https://www.bonedo.de/?p=2387273

### Arturia MicroFreak (Spice & Dice), KeyStep Pro, KeyStep 37 mk2
- **MicroFreak:** tap the touch strip in Dice mode to roll a new random version of the sequence or arp; further right =
  bigger changes. It changes gates, triggers (can mute some), velocity, envelope decay / release, sometimes pitch.
  **Spice** fades between the original and the rolled version. Live; the pattern itself stays.
- **KeyStep Pro:** Shift functions Random Notes and Random Order change a pattern; random play modes; the arp has a
  random setting with fully random, repeating random, or "drunk walk" (not confirmed beyond tutorial / forum text).
- **KeyStep 37 mk2:** Mutate adds randomness to note length, swing, pitch and polyphony; Spice sets the amount
  (support page blocked my fetch; from the search snippet only).
- **Users:** SOS: "took me a fair while to figure out", but praises the live pattern ideas.
- **Sources:** https://www.soundonsound.com/reviews/arturia-microfreak?page=2 ·
  https://support.arturia.com/hc/de/articles/4405748052626-MicroFreak-Allgemeine-Fragen ·
  https://arturia.com/products/hybrid-synths/keystep-pro/resources ·
  https://support.arturia.com/hc/en-us/articles/24773018134684-KeyStep-37-mk2-Mutate-and-Spice ·
  https://www.sequencer.de/synthesizer/goto/post?id=1722880

### Teenage Engineering OP-1 / OP-1 field
- **Endless:** step entry of up to 128 notes; playing a key transposes the whole line; directions forward / reverse /
  random; a dot pattern on top (rotate it with Shift).
- **Tombola:** played notes fall in a spinning hexagon and sound when they hit a wall (harder = louder). Random, live.
- **Arpeggio:** a held-note arp with a trigger pattern of dots (play) and dashes (pause or skip), note length 1-64
  ticks, and "added notes" types: octave up; octave up and down; +7, +9, -5; or the intervals 2, 4, 5, 7, 9.
- Written or live: live. Field details assumed the same as the OP-1 guide (not confirmed).
- **Source:** https://teenage.engineering/guides/op-1/original/sequencers

### Korg SQ-64 and Wavestate
- **SQ-64:** per step length, offset (up to half a step early / late), probability, step division (2-16 repeats, flat
  or with rising / falling velocity). Play modes include **Stochastic**: each next move is chosen at random from
  forward 1, forward 2, back 1, repeat.
- **Wavestate:** separate **lanes** (timing, sample, pitch, shape, gate, step value), each with its own length and
  loop points; steps can be skipped with a probability, the order can be randomised. Different lane lengths give
  constantly shifting combinations. Live.
- **Sources:** https://www.attackmagazine.com/reviews/gear-software/korg-sq-64-poly-sequencer/ ·
  https://musictech.com/reviews/korg-wavestate-synth/

### Music Thing Turing Machine (Eurorack)
- A looping random shift register. **Length** 2-16 steps; **Scale** = output range (a quantizer after it makes notes).
  The **big knob**: noon = always new; 1-4 o'clock = "slips" (notes replaced one by one, faster towards noon); fully
  right = locked loop; fully left = locked, double length. A Write switch puts a 0 or 1 into the loop by hand.
- **Keep:** turn fully right when you hear something you like. Live; nothing is stored once it slips.
- **Users:** fun, but the reviewer was "never fully certain" how he controlled it.
- **Sources:** https://www.soundonsound.com/reviews/music-thing-modular-turing-machine-mkii ·
  https://native-instruments.com/en/reaktor-community/reaktor-user-library/entry/show/10173

### Mutable Instruments Marbles (Eurorack)
- **t section** (rhythm): rate, jitter, bias between two gate outputs with three modes (coin toss, random divide /
  multiply, alternating like kick / snare), gate length.
- **X section** (pitch): **Spread** (constant, bell curve, even, only the extremes), **Bias** (towards low or high),
  **Steps** (smooth to stepped; then quantised to a scale, then removing the least used notes until only the root is
  left). Scales can be "learned" from about 50 played notes; the most played notes stay longest.
- **Deja vu:** left half = chance of reusing past values (noon = locked loop); right half = random jumps inside the
  loop. **Length** = loop length per decision. Double-press reseeds a loop.
- **Written or live:** live. **Source:** https://pichenette.readthedocs.io/en/latest/modules/marbles/manual/

### Mutable Instruments Grids (Eurorack)
- A map of drum patterns learned from real music; **X / Y** pick a point on it. **Fill** per channel adds or removes
  hits in an order that follows that pattern. **Chaos** adds random rolls and ghost notes. Accent outputs fire on
  important steps. Has a hidden Euclidean mode. OXI One uses a Grids-based drum generator (shop page, not confirmed).
- **Source:** https://pichenette.readthedocs.io/en/latest/modules/grids/manual/

### Make Noise René (Eurorack)
- A 4 × 4 note grid walked by separate X and Y clocks (Cartesian), or along one of 16 "snake" paths. Steps can be
  skipped or quantised; up to 64 stored states. Ideas come from the *path*, not from random notes. Live.
- Detail of the Access page not confirmed. **Sources:** https://www.soundonsound.com/reviews/make-noise-rene ·
  https://waveformmagazine.com/waveform-reviews/make-noise-ren-v2/

### Ableton Live 12 (MIDI generators and transformations)
- **Generators** (write notes into the clip): **Rhythm** (one pitch; steps up to 16, pattern, density, step duration,
  split = chance to halve a step, shift, accent velocity, accent frequency and offset); **Seed** (random notes in a
  pitch / length / velocity range, voices, density; scale aware); **Shape** (draw or pick a contour, pitch range, rate,
  **tie** chance, density, jitter); **Stacks** (chord progressions); **Euclidean** (up to 4 voices).
- **Transformations:** **Arpeggiate** (18 styles, distance in scale steps, gate); **Connect** (fills gaps between
  notes with new notes: spread in scale steps, density, rate, tie); **Ornament** (flams, grace notes above / below,
  chance); **Recombine** (shuffle, mirror or rotate *one* dimension: position, pitch, length or velocity); **Span**
  (legato / tenuto / staccato, random variation); **Strum**; **Chop**; Velocity Shaper.
- **Keep / re-roll:** press again for a new result; Live's Undo; unselected (grey) notes stay fixed. No seed control.
- **Users:** "ideas generators rather than finished parts"; "musical but hard to pin down"; Shape praised for
  controlling the contour.
- **Sources:** https://www.ableton.com/en/manual/midi-tools/ ·
  https://www.attackmagazine.com/technique/tutorials/getting-started-with-ableton-lives-generative-midi-tools/ ·
  https://www.musicradar.com/how-to/live-12-midi-tools · https://benjaminwoodling.substack.com/p/ableton-live-12 ·
  https://mixdownmag.com.au/features/first-look-ableton-live-12/

### Bitwig Studio (note FX)
- Arpeggiator (17 patterns, per step length / velocity / pitch offset, a random option for velocity, timing and
  length), Randomize (pitch, velocity, ... at each note), Humanize (chance to pass, timing, velocity), Note Echo,
  Multi-note (up to 8 notes per note, each with a chance), Ricochet (bouncing balls; "Bar Sync" launch repeats the same
  pattern). All live.
- **Source:** https://www.bitwig.com/userguide/latest/note_fx

### ASM Hydrasynth (arpeggiator)
- Arp with up / down / order modes, **Phrase** mode (64 preset phrases), **Ratchet** with a **Chance** of the
  ratchet happening, octave settings; most arp settings can be modulated. Live. Custom phrases not found.
- **Source:** https://www.soundonsound.com/node/4921184?page=2

### Telepathic Instruments Orchid (chord instrument)
- Chords from one button press, a voicing knob that moves the chord across the keyboard, a separate **bass** voice
  (can play only with chords), play modes strum, "slop", arpeggiator, pattern, harp. Live; reviewers miss loop storage.
- **Sources:** https://musictech.com/reviews/hardware-instruments/telepathic-instruments-orchid-review ·
  https://splice.com/blog/telepathic-instruments-orchid-review/

### Novation Circuit Tracks (stock) and Launchpad Pro mk3
- **Circuit Tracks:** per-step probability (8 levels). **Mutate** (Shift + Duplicate) randomises *which steps* the
  existing notes play on; destructive, no Undo. SOS: duplicate the pattern first; "Undo" is the main missing feature.
- **Launchpad Pro mk3:** probability per step and **mutation**, a set amount of random pitch change (live).
- **Sources:** https://userguides.novationmusic.com/hc/en-gb/articles/25494476280850-Circuit-Tracks-hardware-overview ·
  https://www.soundonsound.com/reviews/novation-circuit-tracks · https://musictech.com/reviews/controllers/novation-launchpad-pro-mk3/

### Acid bass generators: Roland TB-303 (2020s) randomize, The Endless Acid Banger
- **TB-303 manual:** RANDOMIZE "generate" makes a new pattern from randomize settings; "modify" changes the playing
  one. Accent, slide and octave change only on steps that already sound, so the rhythm and key stay.
- **Acid Banger** (open source, 16 steps): a root plus one of 8 hand-written note sets (e.g. `0,0,12,24,27`; a repeated
  number makes that note more likely). Chance of a note per step depends on the beat: 0.6 on steps 1, 5, 9, 13; 0.5 on
  every third; 0.3 on other even steps; 0.1 on the rest. Accent 30 %, slide 10 %.
- **Sources:** https://rolandcloud.com/getmedia/b3e2da28-1951-467e-bd79-7aae34481570/TB-303-Manual-E.pdf?ext=.pdf
  (PDF, could not read it in full; from the search snippet) · https://github.com/vitling/acid-banger/blob/main/src/pattern.ts ·
  https://musictech.com/news/randomised-algorithmic-acid-music-vitlings-the-endless-acid-banger-909-303

### Intellijel Metropolix (Eurorack)
- 8 stages; each has a **pulse count** 1-8 (one note can last several clocks) and a **gate mode**: hold (one long
  note), repeat, single, rest. Per stage ratchets, probability, skip, slide, and an **accumulator** that adds a scale
  step each pass (a line that climbs over loops). Strong for bass lines and leads; stored per stage.
- **Sources:** https://www.soundonsound.com/reviews/intellijel-metropolix · https://www.musicradar.com/reviews/intellijel-metropolix

## 3. Recurring techniques

"Pads" = new pads on a CTPlay page. "Cost" = rough code / RAM cost (flash is cheap): S small, M medium, L large.

| Technique | Devices | What it gives musically | Fit for CTPlay | Cost |
|---|---|---|---|---|
| Note pool from a held chord or a scale | T-1, OXI Chord, Orchid, OP-1 arp, arps | Lines that fit the harmony | Written; chord engine and scale exist; 1-2 pads (chord / scale) | S |
| Walk the pool by an order (up, down, up-down, climb, as played) | T-1 Style, arps, Arpoly | Arpeggio-like lines, predictable | Written; reuse the Arp page's orders; ~4 pads | S |
| Random pick, weighted (root and fifth more often) | Acid Banger, Marbles Steps, OXI Stochastic, OXI Rand | Bass lines that stay "home" | Written; a weight table in flash; 1-2 pads | S |
| Pitch contour (ramp, triangle, sine) | T-1 Phrase, Live Shape, Hapax Curves | A shaped phrase: rise and fall | Written; tables; ~3 pads | S |
| Pitch range in octaves / scale steps | OXI Bias + Range, Hapax, Live Seed, Marbles | Narrow = riff, wide = lead | Written; 3 pads (1-3 octaves) | S |
| Beat-weighted density | Acid Banger, Grids, Live Rhythm accents | Off-beats sparser: groovy bass rhythms | Written; a second rhythm source next to Euclid; 1 pad + Hits pads as density | S |
| Euclid with two layers / logic | Elektron Euclid mode | More varied rhythms from two simple ones | Written; more pads, harder to explain | M |
| Accent pattern (first hit, every N, curve) | T-1 Groove, Hapax Every N, Live Rhythm, 303 | Phrasing; ghost notes | Written (velocity); 2-3 pads | S |
| Ties / legato / staccato chance | OXI Ties, Live Shape tie, Span, Metropolix hold | Bass lines that breathe; long notes | Written (length in sixths, up to next hit); 2-3 pads | S |
| Ratchets / repeats with velocity ramp | T-1 Repeats, SQ-64, Hydrasynth, Metropolix | Rolls and energy | Written only if one step can hold same-pitch notes at different microsteps (check); else live | M |
| Grace notes / passing notes between hits | Live Ornament, Live Connect | Movement between chord tones | Written (microstep, extra steps); 1-2 pads | M |
| Separate re-roll of rhythm and pitch | OXI Order / Pitch, Live Recombine, T-1 layers | Keep the groove, try new notes | Written; 2 dice pads + seeds (2-4 B per track) | S |
| Transform current pattern (shuffle pitches, reverse, mirror, rotate notes against rhythm) | Live Recombine, Hapax Shuffle / Symmetry, OXI Flip, Circuit Mutate | Variations of a part you played yourself | Written; works on any pattern; 3-4 pads | S |
| Undo of a write | OXI, Live, (missing on stock Circuit) | Safe to try | Already there (one level) | done |
| Seed number (repeatable result) | Hapax Curves, Ricochet Bar Sync | Get back a result after re-rolls | Written; a small "last 4 seeds" history instead of a number | S |
| Lock / slip / deja vu loop | Turing, Marbles, Deluge Lock, T-1 | Slowly changing loops | Live only (playback hook): does not play on stock | L |
| Per-step probability for extra notes | Elektron, Deluge, SQ-64, Circuit | Loops that vary each pass | Written (stock 0-7 levels); 1-2 pads | S |
| Pass conditions (A:B, fill, iterance) | Elektron, Deluge, T-1 cycles | Fills at the end of 4 bars | Not in stock data; fake it by writing variant patterns 2-8 | M |
| Variant patterns (write a family) | T-1 cycles, Hapax "variations" use | Phrase that develops over bars | Written to the next pattern slots; 1 pad | M |
| Play order modes (stochastic, random, snake) | SQ-64, René, Polyend 35 modes, OP-1 | Re-orders the same steps | Live only (stock has directions) | M |
| Chords + bass generated together | Polyend Fill, Orchid, Live Stacks | Full backing | Two tracks at once; outside one-track write | L |
| Humanize (timing, velocity) | OXI, Bitwig, Polyend, Pyramid | Less mechanical | Written (microstep 0-5, velocity) | S |

## 4. Ideas worth considering for CTPlay (ranked)

1. **Notes for the Euclid hits.** Keep the Euclid rhythm as it is; add a pitch layer. Source: the held chord's notes
   (or the scale when nothing is held). Order: up, down, up-down, climb (2 up, 1 back), random. Range: 1-3 octaves.
   Written by the existing Write, so Undo and the preview work as now. Cheapest big step: every hit stops being the
   same pitch. About 8 pads; the 7 free pads are tight, so this probably needs its own page.
2. **Two dice: re-roll the rhythm or the notes.** Each Write uses two small seeds, one for the rhythm and one for the
   pitches. One pad rolls a new pitch seed with the same rhythm, another rolls a new rhythm with the same pitches (OXI
   Order / Pitch, Live Recombine). The user keeps what works and changes the rest. Small RAM (a few bytes per track).
3. **Bass-line rules.** A "bass" pitch mode: the root on the first hit and on strong beats, then fifth, octave and
   chord notes by weight (Acid Banger's weighted sets, Marbles' Steps). Optional passing note (one scale step)
   before a change. Gives bass lines that sound "right" more often than a plain random pick.
4. **Length and accent rules.** Per write: staccato / normal / legato (each note lasts until the next hit, up to 96
   sixths) and a tie chance (OXI Ties, Live Shape). Accents: on the first hit, every Nth hit, or on strong beats, with
   the rest softer (Hapax Every N, T-1 Groove). These change the feel more than the pitches do, and cost little.
5. **Beat-weighted rhythm as a second source.** Next to Euclid, a "groove" rhythm: the Hits pads set the density, and
   a fixed table decides which steps fill first (downbeats, then every third, then off-beats), as in Acid Banger and
   Grids. Gives syncopated bass rhythms that Euclid's even spread cannot. One pad to switch source.
6. **Transform the current pattern.** Shuffle the pitches (keep the rhythm), reverse in time, mirror the pitches
   around the root, rotate the notes against the rhythm (Live Recombine, Hapax Symmetry). Works on parts the user
   played in by hand, not only on Euclid results. Each is one pad and one Write, with Undo.
7. **Extra notes with low probability.** Write some extra notes (ghost notes, an octave jump, a fill near the end)
   with a stock probability of 2-4 of 7. The loop then changes each pass, and it still plays on official firmware
   (Elektron / Deluge style without new data).
8. **Contour shapes.** Pitch follows a ramp, triangle or sine over the pattern, snapped to the chord or the scale
   (T-1 Phrase, Live Shape, Hapax Curves). Tables are cheap; good for leads and arpeggio sweeps. Could share the
   "order" pads of idea 1.
9. **Write a family of patterns.** One press writes variants into the next pattern slots (same rhythm, new notes; or
   a sparser and a busier version), like T-1 cycles. Chained in stock, they play as a developing phrase. Needs care
   not to overwrite the user's patterns (only empty slots, or a second confirm).
10. **Ratchets and grace notes.** Rolls with a velocity ramp (T-1, SQ-64) and grace notes (Live Ornament) using
   microsteps. First check whether stock plays two notes of the same pitch in one step at different microsteps.
11. **Live slip / deja vu (Turing Machine, Marbles).** A playback hook that slowly replaces notes. Fun, but it does not
   play on official firmware and needs RAM and a hook; a "write the current loop" button could fix that later. Lowest
   priority.

Points users raise again and again, worth keeping in the design: a result you can **undo** (stock Circuit's main
missing feature, per SOS), keeping one layer while changing another, and controls simple enough to understand
without a screen (MicroFreak and Turing Machine reviewers were unsure what they controlled).
