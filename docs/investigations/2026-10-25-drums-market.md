# Drum features: what users expect (market research, 2026-10-25)

What this rests on: manuals (Circuit Rhythm, Circuit Tracks, TR-8S, BeatStep Pro and MPC were downloaded
and searched as text), reviews, and forum threads (Elektronauts, MIDIbox, NI, Ableton, Polyend, Synthtopia
comments).

**Gaps:** I could not reach Reddit (r/novationcircuit etc.): the search tool refuses reddit.com, and a direct
fetch was blocked. Gearspace thread pages returned 403. So the Circuit Tracks user wishes below come from
Elektronauts, Synthtopia comments, Novation's own comparison table, CTPlay's `candidates.md` (which already
records a Reddit request for trig conditions) and upstream's feature list. Items marked **(unverified)** come
from my own knowledge, not from a page I read this session.

Stock step format, for the "fit" column: one velocity, one probability (8 levels, 12.5 %–100 %), one sample
flip and one 6-bit microstep mask per drum step. "Fits" means a write into the pattern holds the result and
stock plays it back. "Playback" means the result needs logic that runs while the pattern plays.

## 1. Ranked feature table

| # | Feature | Devices | How strongly users want or praise it | Fit on Circuit Tracks |
|---|---|---|---|---|
| 1 | **Note repeat / roll** (hold a pad, pick a rate) | MPC, Circuit Rhythm, Push, Maschine, TR-8S / TR-6S (roll pads), BeatStep Pro (roller strip) | **Strong.** Novation's own comparison table lists Note Repeat as the one drum feature Rhythm has and Tracks lacks ([novationmusic.com/circuit](https://novationmusic.com/circuit)). Gearnews calls Rhythm's pads "a really cool place for banging out 8 tracks of beats and note repeats" ([gearnews](https://www.gearnews.com/novation-circuit-rhythm-the-review/)). People ask for MPC-style repeat in DAWs too ([Steinberg](https://forums.steinberg.net/t/note-repeat-request-mpc-style/1020766), [Renoise](https://forum.renoise.com/t/note-repeat-akai-style/24290)). | Live: plays through a drum view's sink. **Recorded:** all 8 Circuit Rhythm rates fall exactly on the 6-microstep grid (1/32 = microsteps 1 and 4; 1/32T = 1, 3, 5; 1/16T and 1/8T = every 4 or 8 microsteps across steps). Straight 1/64 does not (1.5 microsteps). Velocity is stored **per step**, so a ramp is recorded in step-sized stairs. With stock Rec Quantise on, hits snap to the step, which would turn 1/32 into 1/16 (CT manual p. 63). |
| 2 | **Velocity shaping: accents, ghost notes, velocity variation** | TR-8S accent track + per-step dynamics, Push Accent (all notes at 127), T-1 Accent, Elektron velocity / retrig velocity | **Strong.** TR-8S gives accent its own step lane ([TR-8S manual](https://static.roland.com/assets/media/pdf/TR-8S_Reference_eng04_W.pdf) p. 19). One Elektronauts drummer argues that varying velocity does far more than shifting timing ([thread](https://www.elektronauts.com/t/emulating-a-live-drummer/67490), as summarised by search). Sinesquares calls T-1's Random "one of the most important knobs" and says velocity "gets interesting" once randomised ([review](https://www.sinesquares.net/musicgear/torso-electronics-t-1-review)). | **Fits:** per-step velocity. Can be a write-time pattern (on-beat accent, off-beat ghost, random spread). |
| 3 | **Euclidean generator** (steps, pulses, rotate, plus accent / repeats / timing) | Torso T-1, Elektron Digitakt II / Syntakt / Analog Rytm (two generators combined), Polyend Play Fill, Ableton Live 12 generators, Grids' hidden Euclid mode | **Strong among generative users; mixed among Elektron users.** Torso builds the whole product on it ([docs](https://docs.torsoelectronics.com/t1/core-concepts/euclidean-rhythms/)): "often the starting point, not the finished result", then add / remove hits by hand. Elektron added two combinable generators ([MusicRadar](https://www.musicradar.com/news/elektron-analog-rytm-os-update)). Reactions on Elektronauts were mixed: "Having a ton of fun with the Euclidean sequencer" vs. "As is, I am not seeing the magic", and a complaint that you can't tell which boolean operator is chosen ([thread](https://www.elektronauts.com/t/euclidean-mode-rhythms/51170?page=2)). | **Fits** (PL11 already does it for note tracks). |
| 4 | **Fills and conditions** (FILL mode, A:B "every N loops", auto fill every N bars) | Elektron trig conditions + FILL, TR-8S Auto Fill In (every 32 / 16 / 12 / 8 / 4 / 2 bars) and manual trigger, Polyend Chance "Skip n / Play n" | **Strong on Elektron, and asked for on Circuit Tracks.** The usual answer for "a fill every 8 bars" is trig conditions such as 2:2 / 1:2 ([Elektronauts](https://www.elektronauts.com/t/drum-fills-on-8th-bar/193320)). Users want more: combined conditions ("7 of 8 with /fill"), conditional retrigs, "never twice in a row" ([requests](https://www.elektronauts.com/t/trig-conditions-feature-requests/181602)). TR-8S auto fill: [manual](https://static.roland.com/assets/media/pdf/TR-8S_Reference_eng04_W.pdf) p. 13. CTPlay `candidates.md` records a Reddit request ("every 2nd / 4th loop"), and upstream has step "frequency". | **Playback:** needs a loop counter and per-step bits. A "fill" can also be a second pattern in a stock chain, which needs no new logic but costs a pattern slot. |
| 5 | **Ratchet / retrig per step with a velocity fade** | Elektron retrig (rate, length, velocity curve), T-1 Repeats + Offset (velocity ramps), TR-8S sub steps 1/2, 1/3, 1/4 + SUB PROB | **Medium–strong.** Elektron users mainly want fade-outs ("-128 takes it to zero volume") and learned they must lower the trig's own velocity first ([thread](https://www.elektronauts.com/t/retrig-volume-variation-settings/103750)). T-1's velocity ramps on repeats: "actually pretty cool" ([sinesquares](https://www.sinesquares.net/musicgear/torso-electronics-t-1-review)). A Circuit owner asked Novation for "ratcheting with probability" ([Synthtopia comment](https://www.synthtopia.com/content/2019/03/07/novation-circuit-gets-8th-free-update-adding-non-quantized-recording-more/)). | **Ratchet fits:** the microstep mask already makes 2, 3 or 6 hits per step (CT manual). A **fade inside one step does not fit** (one velocity per step). A fade over several steps does fit. Probability then applies to the whole ratchet. |
| 6 | **Style-aware random fill per drum** (kick / snare / hat aware, density per part) | Polyend Play Fill (Kicks, Snares, Hats, "Beats"), Mutable Grids (pattern map + one density control per part + chaos), Circuit Mutate (shuffles existing hits) | **Medium–strong.** SOS on Polyend: Fill modes "generate patterns that make sense for those sound types"; "Multiple taps of Fill each generate a new pattern" ([SOS](https://www.soundonsound.com/reviews/polyend-play)). Grids is in 10,567 ModularGrid racks, rated 4.19 by 118 voters ([ModularGrid](https://modulargrid.net/e/mutable-instruments-grids)). Its density control adds or removes hits in the order set by the map, up to "ghost notes, rolls and fills" ([manual](https://pichenette.readthedocs.io/en/latest/modules/grids/manual/)). | **Fits** (write-time). A Grids-style map costs flash: about 25 nodes × 96 B ≈ 2.4 KB **(unverified, from memory of the Grids source; check its licence)**. |
| 7 | **Probability per step** | Everyone (Elektron, TR-8S PROB and SUB PROB, BeatStep Pro, Circuit) | Expected as a baseline. Already in stock with 8 levels (CT manual p. 48). Wishes go past it: "never twice in a row", probability on locks ([requests](https://www.elektronauts.com/t/trig-conditions-feature-requests/181602)). | **Fits** (stock). Pattern tools can write it, e.g. "thinning as probability" rather than removing hits. |
| 8 | **Flam** | TR-8S / TR-6S (Shift + SUB, Flam Spacing 0–8) | **Medium**, mostly people coming from Roland. Documented in the [TR-8S manual](https://static.roland.com/assets/media/pdf/TR-8S_Reference_eng04_W.pdf) pp. 17–22. I found little forum demand. | Two hits one microstep apart fit (about 21 ms at 120 BPM), but **both play at the step's velocity**. A real flam has a softer grace note, which needs playback logic. |
| 9 | **Humanize (timing)** | Polyend Chance "humanize" ("a randomized micro-movement", [Polyend](https://polyend.com/whats-up/polyend-play-10-ways-to-get-creative-using-chance-action/)), MPC timing-correct strength | **Medium–weak.** The drummer post in row 2 rates velocity above timing. | Microstep offsets fit, but they are coarse: one microstep is about 21 ms at 120 BPM. Typical humanize is a few ms **(unverified)**. Velocity humanize fits well. |
| 10 | **Complementary / interlocking rhythms** (hats avoid the kick, etc.) | Elektron NEI / PRE conditions, Elektron's Euclid boolean combine, Grids (one shared map makes the parts interlock), Polyend "Beats" | **Niche but valued** by generative users. Polyend users asked for neighbour-track linking with chance ([backstage](https://backstage.polyend.com/t/a-b-conditions-for-each-sequencer-pass/909)). | **Fits** at write time: mask drum B's hits against drum A's steps. NEI-style "only if the neighbour played" needs playback. |
| 11 | **Per-drum pattern length / polymeter** | Circuit (since 1.4), Polyend ("each lane can have an independent length", SOS), Elektron | Valued, but **stock already has it**: per-track start / end points and sync rate (CT manual p. 54–56). | Nothing to build. Pattern tools only need to respect the track's start / end. |
| 12 | **More drum tracks** | Circuit Rhythm 8, Elektron 8–16 | **Weak** for Tracks users. One owner says they rarely need four full drum tracks ([Tao of Mac](https://taoofmac.com/space/blog/2022/02/05/1730)). Gearspace / Elektronauts wishes lean to drum *synthesis*, not more tracks ([Elektronauts](https://www.elektronauts.com/t/novation-circuit-rhythm-and-circuit-tracks/145048?page=52)). | Out of scope (voices, DSP time). Sample flip already gives several sounds per track. |

## 2. Note repeat: the common design

**Rates.**
- Circuit Rhythm has 8 pads: 1/4, 1/8, 1/16, 1/32 and the triplets 1/4T, 1/8T, 1/16T, 1/32T, plus a latch pad. The manual says it is meant for "trap-style hi-hat patterns with a triplet feel" (Circuit Rhythm user guide pp. 45–46, [PDF](https://files.kraftmusic.com/media/ownersmanual/Novation_Circuit_Rhythm_User_Guide.pdf)).
- MPC takes its rate from Timing Correct (straight and T values), with swing 50–75 % ([MPC 2.7 guide](http://www.akai-pro.jp/mpc-one/data/MPC-User-Guide_small-v2.7.2) p. 84).
- TR-8S roll pads give only 1/16, 1/32 and 1/64 (both pads together) (manual p. 22).
- Push has 8 interval buttons ([Push manual](https://www.ableton.com/en/push/manual/)). The values are probably 1/4–1/32 with triplets **(unverified)**.
- **The consensus is 4 straight + 4 triplet rates.**

**Velocity.**
- Pressure-driven: MPC, Push ("Varying your finger pressure on the pad will change the volume of the repeated notes"), BeatStep Pro ("volume swells … during the roll", [manual](https://downloads.arturia.com/products/beatstep-pro/manual/BeatStepPro_Manual_1_0_0_EN.pdf) p. 44). Roger Linn describes recording 16th hats with each note at "your finger pressure at that moment" ([Attack](https://attackmagazine.com/features/interview/roger-linn-swing-groove-magic-mpc-timing/2)). MIDIbox users call pressure "the key feature of note repeat that makes the MPCs so magical" ([MIDIbox](https://forum.midibox.org/t/mpc-style-note-repeat-function/18931)).
- MPC's arp / repeat engine also offers fixed modes: As played, From first note, Accented, Full, 3/4, Half, 1/4 (MPC guide p. 342).
- **Circuit Tracks documents velocity-sensitive pads only, with no aftertouch.** So the realistic choices are the first strike's velocity, a fixed level, or a ramp. The CLAUDE.md pad-mux note mentions held-pad pressure readings, so whether the scan gives continuous pressure is worth one check.

**Latch.** Every device has one:
- Circuit Rhythm: pad 5.
- MPC: Shift + Note Repeat.
- Push: tap the button to latch, hold it for momentary.
- TR-8S: INST PLAY + roll pad.

**What is recorded.**
- What you hear. Circuit Rhythm: "Recording note repeat is destructive and will overwrite any micro steps … what you hear during recording is what the pattern will become."
- Live repeat also overrides the pattern's own hits on that track while held (good for live fills).

**The details that decide how it feels:**
1. **Repeats lock to the grid.** A hit off the beat waits for the next slot of the rate ([MIDIbox](https://forum.midibox.org/t/mpc-style-note-repeat-function/18931)), so a sloppy press still sounds tight. The first hit should sound at once or snap to the grid, never double.
2. **Changing the rate while holding the pad must not break the stream.** Users praise this on the Akai XR20 (MIDIbox thread). Push 3 users report as a bug that switching velocity pads stops the repeat ([Ableton forum](https://forum.ableton.com/viewtopic.php?p=1824173)).
3. **Swing applies to the repeats.** Push puts swing on repeated notes, and MPC users treat 57 % as "the magic number" (MIDIbox). Trouble shows up at extreme swing: an MPC4000 user lost recorded notes at 75 % with timing correct on ([mpc-forums](https://www.mpc-forums.com/viewtopic.php?p=1752884)). On Circuit Tracks, check how stock swing treats microsteps **(unverified)**.
4. **Velocity has to move.** Pressure, a ramp or an accent keeps rolls from sounding like a machine gun. Elektron users mostly want fade-outs. A NI bug where locked note repeat lost velocity sensitivity drew complaints ([NI community](https://community.native-instruments.com/discussion/comment/155603)).
5. **Recording fidelity.** The recorded pattern should match what was heard. On Tracks that means recording the microstep mask even when Rec Quantise is on, or saying clearly that rates above 1/16 need it off. It also means knowing that velocity changes only once per step.

## 3. Pattern tools: what drummers actually use

**The generators people use:**
- **Euclid with rotate** (T-1, Elektron, Polyend, Live 12).
- **A density / thinning control per part** (Grids' fills, T-1 Pulses, Polyend's variable-density Fill).
- **Style-aware random fills** (Polyend's Kicks / Snares / Hats / Beats).
- **Randomise with an amount**: SOS praised "from subtle variation to full mayhem" on Polyend.

**The parameters that matter most, in order:**
1. **Pulses / density** and **rotate**: Torso calls them the core, and its rotate also moves hand-added hits ([Torso docs](https://docs.torsoelectronics.com/t1/core-concepts/euclidean-rhythms/)).
2. **Accent / velocity character**: T-1 Accent and Random on velocity; TR-8S accent lane.
3. **Repeats inside the rhythm with a velocity ramp**: T-1 Repeats + Offset.
4. **Fill / variation every N bars**: Elektron conditions, TR-8S auto fill.
5. **Combining two rhythms**: Elektron's two generators and boolean combine. Note the complaint that users can't see which operator is chosen, so show the operator clearly.

**Workflow habits:**
- Generate, then hand-edit (Torso).
- Re-roll by tapping again (Polyend Fill).
- **A commit / undo safety net.** Polyend prints the random result into the steps. Circuit's Mutate has no undo: Novation's manual tells you to save the project first (CR guide p. 58). CTPlay's draft + Write + Undo already beats both.

## 4. First build vs later

**Must-have for the first build**
- **Note repeat on a drum page: 4 straight + 4 triplet rates, plus latch.** It is the one drum feature Novation itself lists as missing on Tracks, and every rate fits the 6-microstep grid.
- **Note repeat velocity from the strike, with an optional ramp (up / down).** Velocity variation is what users praise most, and CT pads have no aftertouch.
- **Note repeat records what you hear (microstep mask + per-step velocity).** Circuit Rhythm's "what you hear … is what the pattern will become" is the expected model. Handle Rec Quantise.
- **Euclid per drum (pulses, rotate, accent velocity) with draft / Write / Undo.** It is the most-used drum generator, and PL11 already has the code path and UI.
- **Respect each drum track's start / end and sync rate.** Stock already has per-drum length, and users rely on it for polymeter.

**Nice later**
- Fill every N bars / trig conditions: strongly wanted, but needs playback logic (port upstream's step frequency).
- Ratchet / retrig tool with a fade across steps: valued, and fits the format if the fade is per step.
- Second rhythm / combine and complementary masking (hats avoid the kick): PL14's machinery carries over, but demand is niche.
- Style-aware fill or Grids-like density map: well loved, but costs flash and needs licence checks.
- Flam with a soft grace note: needs playback logic, and demand is mostly from Roland users.
- Velocity humanize as a Write option: cheap, and liked by people who programme drums.

**Users don't care (or it already exists)**
- More drum tracks: few ask for them, and the hardware can't give them.
- Per-drum length / polymeter: stock has it.
- A new mutate: stock has Shift + Duplicate.
- 1/64 straight repeat: it does not fit the grid, and only TR-8S offers it.
- Timing humanize: a microstep (about 21 ms) is too coarse, and users rate velocity above timing.
