# PL21 — device test plan (the CTPlay 1.0 beta: every feature)

**The marker will change.** PL21 is the working name of the beta build. Its real marker is not decided yet; this
folder and the names in this plan get the new marker later. Where this plan says PL21, read the beta build.

**What it is:** the beta's full device test. It runs **every CTPlay feature once, on one fresh build**, not only what
changed. The beta adds no features. It changes three things, and one behaviour:
- **Saved format 2:** CTPlay's settings sit in one new block in the project (spec
  `slim/docs/specs/2026-11-10-saved-format-2-design.md`). A project saved on an alpha build (PL10–PL20) loads its
  settings on the beta. A project saved on the beta loads with CTPlay's defaults on an alpha build.
- **Link protocol 2:** the CTCtrl link sends the settings in chunks of up to 64 bytes, with two-byte offsets.
- **Repeat moved:** in the drum page list (Shift held on a drum page), **Repeat is on pad 26 now** (it was on pad 25).
  Pad 25 is dark.
- **Step entry, pad first:** hold a key pad, press a step, and let go of the step before the pad: the whole chord
  now keeps sounding until you let go of the pad (as stock does with a single note).

This plan checks each feature's main behaviours as a user meets them: the gestures, what lights, what sounds, what
records, what saves. The fine details and the edge cases were checked by emulation and by the earlier device runs
(PL01–PL20 all passed); this plan does not repeat them. Two other plans go with this one:
- **`TEST-components.md`** (this folder): Novation Components and the beta. A separate run.
- **`slim/firmware/PL20/TEST-clock.md`**: the external MIDI clock (section N says when).

**Time:** about **3½ hours** in all by the usual estimate: 327 rows at about 30 s each (2¾ h), plus the build,
three flashes, one power cycle and a new project at the start of most sections (about 45 min). PL19's 105 rows took
45 min, so it may go faster. It splits into four sittings of about an hour:
- **Sitting 1, about 50 min:** Before you start: the alpha project on PL20 (5 min), the build and the flash
  (15 min); A. Getting around (13 min); B. Chords (13 min); C. Two pads of one pitch (4 min).
- **Sitting 2, about 50 min:** D. Step entry, pattern strum, mono record, count-in (18 min); E. Arpeggiator
  (10 min); F. Euclidean fills (11 min); G. Melodic generator (7 min).
- **Sitting 3, about 1 hour:** H. Drums (22 min); I. Trig conditions (15 min); J. A stock regression pass (12 min);
  K. The link (7 min).
- **Sitting 4, about 1 hour:** L. The recipes (25 min, a new project for each); M. Saved settings, with the
  flashing (30 min); N. External clock (1 row).
- Each section says how it starts. Sections D, H, I, J, K and L start from a new empty project, so a break between
  sittings needs nothing saved.

## Before you start
### 1. Back up
**Back up the SD card** (or every project with Components). This run writes patterns and saves projects. Use slots
you can lose. Way back: hold **Scales + Preset + Note** at power-on, send the stock `.syx` (or PL20).

### 2. The alpha project (on PL20, before you flash anything)
PL20 is installed now. Make a project on it, with CTPlay settings off their defaults on a synth track and on two
drums. Section M loads it on PL21. Pads as on PL20 (the same as PL21, except the drum page list: on PL20 Repeat is
pad 25).

| # | Do | Expect | Result |
|---|---|---|---|
| P1 | Make a **new empty project** (Projects view, tap an empty slot). **Write down its slot**: "the alpha slot" | Synth 1's Note view. The project is in C natural minor (stock's default) | |
| P2 | Shift + Synth 1 (the Chords page). Press pad 3 (7th), pad 24 once (bass below), pad 25 (close voice leading), pad 29 (medium strum), pad 32 (falling) | Pad 3 bright green. Pad 24 bright orange. Pad 25 bright blue. Pad 29 bright white. Pad 32 bright white, pad 31 dim | |
| P3 | Hold Shift, tap pad 32 (Keys). Release Shift. Press pads 1, 2 and 3 | Pad 1 bright magenta (mono record), pad 2 bright green (chords in step entry), pad 3 bright white (pattern strum: played). Pad 4 dim white. **Leave Synth 1 on its Keys page** | |
| P4 | Shift + Synth 2. Hold Shift, tap pad 26 (Arp). Release Shift. Press pad 2 (up), pad 10 (1/8), pad 18 (2 octaves) | Pad 2 bright green, pad 10 bright blue, pad 18 bright magenta. **Leave Synth 2 on its Arp page** | |
| P5 | Press Synth 2 (its Note view). Hold Shift and press 1-16/17-32 once. Look at the 1-16/17-32 LED, still holding Shift | The LED is **blue**: Synth 2's Quick view is Arp now. Release Shift | |
| P6 | Hold Shift and press Clear until Clear shows **magenta** while Shift is held | Magenta: the count-in is on | |
| P7 | Shift + Drum 1 (its Repeat page). Press pad 2 (1/8), pad 10 (fade), pad 15 (unquantized repeats) | Pad 2 bright blue, pad 10 bright white, pad 15 bright cyan. **Leave Drum 1 on Repeat** | |
| P8 | Shift + Drum 2 (its Repeat page). Hold Shift, tap pad 27 (Pattern tools). Release Shift. Press pad 4 (4 hits), then pad 21 once | Pads 1, 5, 9, 13 bright orange. Pad 21 in the 3/6 gate colour (two hits a step) | |
| P9 | Hold Shift, tap pad 27 again (Pattern tools 2). Release Shift. Press pad 28 twice | Pad 28 white (accent on the beat). **Leave Drum 2 on Pattern tools 2** | |
| P10 | Press Synth 1 (the page closes). Save the project: Save, then Save again | It saves as stock does, in the alpha slot | |

### 3. Build PL21, the uploader, the PL20 file
Everything here runs in the beta checkout (`circuit-hacks-oo-beta`), from `slim/`.
1. **Build:** `../.venv/bin/python -m slimbuild versions/PL21.toml`. The printed syx sha256 must equal `syx_sha256`
   in `slim/firmware/PL21/manifest.json`. Write it in the Results section too.
2. Then `../.venv/bin/python -m slimbuild.uploader` (the uploader learns PL21; it knows PL20 already).
3. **PL20's file, for section M:** `slim/build/PL20/circuittracks-4486-PL20.syx` in the main checkout
   (`circuit-hacks-oo`). The uploader must show it as "slim PL20" (sha256 `a6895113…`; it was there and matched on
   2026-11-11). If it is missing, stop and ask: don't check out the tag in the beta checkout.
4. **Stack headroom** (SL00D's numbers, nothing to do on the device): every hook as in PL20 or less. The LED task is
   488 B (PL20 592 B). One new hook: the end of a held step's preview (`preview_end`), 120 B.

### 4. Flash PL21
1. **Close every other tab that uses MIDI** (CTCtrl, the link page, a MIDI monitor). Chrome keeps a tab's MIDI port
   until the tab is closed; a refresh is not enough.
2. Open `slim/build/ct_uploader.html`. Press **Identify the device**: it names **CTPlay PL20**.
3. Pick `slim/build/PL21/circuittracks-4486-PL21.syx`: the page shows "slim PL21". Send, then press Play on the
   Circuit to confirm. Wait until it has restarted.
4. Press **Identify the device** again: **CTPlay PL21**. Close the uploader's tab.

### 5. How to read this plan
1. **A new empty project:** in the Projects view, tap an empty slot. It starts with every CTPlay setting off, in C
   natural minor, tempo **120 BPM**: a beat is half a second, a 16-step bar is 2 seconds. Step 5 is beat 2, step 9
   beat 3, step 13 beat 4. Its patterns are empty, 16 steps. Drum 1 is the kick.
2. **A major scale on C** where a section says so: Scales, pick major, root C. Then every white key is in the scale.
3. **The click** (stock's metronome): hold Shift and look at Clear. **Green = the click only.** If it is not green,
   press Shift + Clear until it is (red off, green click, magenta count-in, cyan both). A count-in delays every
   recording by a bar. The click stays on when you change project and is off after a power cycle.
4. **Record quantise on** (stock's default): hold Shift and look at Record: bright = on. If dim, press Shift + Record.
5. **Stock's fixed velocity off** (Shift + Velocity toggles it; it is a Setup setting and stays as set). Row H6b
   checks it.
6. **Synth 1 and Synth 2 on a Poly patch** with a clear, **sustained** sound (an organ or a soft pad with a quick
   attack). Check the patch after a new project: a Mono patch drops chord notes.
7. **The Note view** with the steps on rows 1–2 and the keys on rows 3–4. If all four rows play notes, press Note
   until rows 1–2 show the steps. Step pads: steps 1–8 on row 1, steps 9–16 on row 2.
8. **Your keyboard layout:** "the C pad" is **pad 25**, the C at the left end of the bottom row. Then **D 26, E 27,
   F 28, G 29, A 30, B 31**, and pad 32 the C an octave up. The black keys are on row 3: in C minor the E♭, A♭ and
   B♭ pads are the black keys above, between D and E, G and A, A and B. **Section C uses stock's scale layout
   instead** (it says when).
9. **Reading chords:** notes lowest first. While you hold a chord, the pads of its other notes light up too. Holding
   a step pad plays the step's notes and lights their key pads; an empty step plays nothing and lights no key pad.
10. **The phantom-press check:** a slow press can make the Circuit see a press on the next pad too (the pad to the
    right). After a press that writes, a row checks that the next pad did not act.
11. **Colours:** bright = selected (on), dim = not selected (off), dark = nothing there. **Gate colours** = stock's
    Gate view colours for a partial step (3/6 is the default of a gate pad in a new project).
12. **"Shift + Synth 1"** opens Synth 1's page (the one used last). **"Shift-tap 27"** means: hold Shift, tap pad 27,
    release Shift (on a page: the page list). **Press Note** closes a page and shows the Note view.

## Steps
### A. Getting around
Covers: the Play pages, ▲ ▼, the page list (Shift held), a two-page feature's pad, closing, the Quick view and its
flip, the Shift-lit track buttons. Every page's look in a new project.

Start: **a new empty project**, a **major scale on C**. Synth 1's Note view. Sequencer stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| A1 | Shift + Synth 1 | The **Chords page** (a new project opens on it). Pad 1 bright green, pads 2–13 dim green, pads 14–16 dark. **▼ blue, ▲ dark** | |
| A1b | Look at rows 3–4 | Pad 17 bright blue, 18–20 dim blue. Pad 21 bright magenta, 22–23 dim magenta. Pad 24 dim orange. Pads 25–27 dim blue. Pads 28–30 dim white. Pad 31 bright white, pad 32 dim white | |
| A2 | Press ▼ | **Arp:** pad 1 bright green, 2–8 dim green. Pad 9 bright blue, 10–12 dim blue. Pads 13–14 dim magenta, 15 dark, 16 dim orange. Pad 17 bright magenta, 18–20 dim magenta. Pad 21 in the 3/6 gate colour. Pads 22–32 dark. ▲ green, ▼ orange | |
| A3 | Press ▼ | **Pattern tools:** pads 1–16 dim orange. 17–20 dim white. 21 the 3/6 gate colour. 22 dim magenta, 23 bright magenta, 24 dim magenta. 25–28 dim cyan. 29 dim white. 30, 31 and 32 dark. ▲ blue, ▼ orange | |
| A4 | Press ▼ | **Pattern tools 2:** pads 1–19 dim white, 20–24 dim violet, 25–27 dim cyan, 28 dark, 29 dim white, 30–32 dark. ▲ orange, ▼ yellow | |
| A5 | Press ▼ | **Melody:** pad 1 bright yellow, 2–8 dim yellow. 9 bright green, 10 dim green. 11 bright magenta, 12–13 dim magenta. 14 dim yellow. 15–16 dark. 17 bright white, 18–24 dim blue. 25–28 dim magenta. 29 dim white. 30, 31 and 32 dark. ▲ orange, ▼ yellow | |
| A6 | Press ▼ | **Phrasing:** pads 1–3 dim cyan, 4 dark, 5–7 dim magenta, 8–28 dark, 29 dim white, 30–32 dark. ▲ yellow, ▼ magenta | |
| A7 | Press ▼ | **Keys:** pad 1 dim magenta, 2 dim green, 3–4 dim white, 5–32 dark. ▲ yellow, **▼ dark** | |
| A7b | Press ▼ again | Nothing changes (no page after Keys, no octave change) | |
| A8 | Press ▲ six times, looking after each press | Phrasing, Melody, Pattern tools 2, Pattern tools, Arp, Chords. On Chords ▲ is dark | |
| A9 | Hold Shift (keep holding it) | Rows 1–3 dark. Row 4, the page list: **pad 25 bright green**, 26 dim blue, 27 dim orange, 28 dim yellow, 29–31 dark, 32 dim magenta | |
| A9b | Still holding Shift, look at the eight track buttons | All eight lit (Synth 1 / 2, MIDI 1 / 2, Drum 1–4), in the colour Note has with Shift: they all have pages | |
| A10 | Still holding Shift, tap pad 27. Release Shift | Pattern tools | |
| A10b | Shift-tap 27 again | **Pattern tools 2**: the open feature's pad again flips to its other page | |
| A10c | Shift-tap 28. Then Shift-tap 28 again | Melody, then **Phrasing** | |
| A10d | Shift-tap 27 | **Pattern tools 2**: a feature's pad opens the page of it used last | |
| A11 | Press Note | The page closes: Synth 1's Note view | |
| A11b | Shift + Synth 1 | **Pattern tools 2**: the track opens on the page it used last | |
| A12 | Shift + Synth 2 | **Synth 2's** Note view and its **Chords** page: each track has its own pages | |
| A12b | Press Mixer | The page closes: stock's Mixer | |
| A12c | Shift + Synth 1, then press FX. Then Shift + Synth 1, then press Preset | Synth 1's Pattern tools 2, then stock's FX view. Pattern tools 2 again, then stock's Preset view | |
| A13 | Press Synth 1 (its Note view). Hold Shift (keep holding it) | The **Chords Quick view** on pads 17–32: pads 17–29 green, **pad 17 bright** (off), 18–29 dim. Pads 30–32 dark. Pads 1–16 as stock shows them with Shift. **The 1-16/17-32 LED green** | |
| A13b | Still holding Shift, tap pad 18 (triad). Release Shift. Play C | Pad 18 turned bright. **C E G** | |
| A13c | Shift + Synth 1, Shift-tap 25 (Chords) | The Chords page: **pad 2 bright green**: the page shows what the Quick view set. Press Note | |
| A14 | Hold Shift, press 1-16/17-32. Keep holding Shift | **LED blue: the Arp Quick view.** Pads 17–24 the patterns (17 bright green, 18–24 dim green), 25–28 the rates (25 bright blue, 26–28 dim blue), 29–30 dim magenta, 31 dark, 32 dim orange | |
| A14b | Still holding Shift, press 1-16/17-32 again | The Chords Quick view: LED green, **pad 18 bright**. Release Shift | |

### B. Chords
Covers: the shapes (rows 1–2), inversion, spread, the bass modes, voice leading (close, top line), strum speed and
direction, shared notes, a chord on a MIDI track.

Start: as section A left it. Synth 1: triad, everything else at its default. Its Note view, stopped. "Play C" = the
C pad (pad 25). **To change a setting:** Shift + Synth 1 (it opens Chords), press the pad, press Note.

| # | Do | Expect | Result |
|---|---|---|---|
| B1 | Play C and hold it | **C E G.** The E and G pads light in the colour of the C pad. Let go: it stops | |
| B2 | Chords page: pad 3 (7th). Play C, then G | C: **C E G B.** G: **G B D F** | |
| B3 | Pad 4 (9th). Play C | **C E G B D** (five notes; all five sound with an ordinary patch) | |
| B4 | Pad 6 (sus4). Play C. Then pad 8 (6th). Play C | sus4: **C F G**. 6th: **C E G A** | |
| B5 | Pad 9 (power) | **Pad 9 bright green, pads 1–8 all dim**: one shape across both rows. Play C: **C G C** (G above, C an octave up) | |
| B5b | Pad 11 (quartal). Play D | **D G C F** | |
| B6 | Pad 3 (7th), then pad 18 (1st inversion). Play C | **E G B C** (E, G and B below the pad's C) | |
| B6b | Pad 20 (3rd inversion). Play C | **B C E G**. Then on the page press pad 17 (root position) | |
| B7 | Pad 22 (drop-2). Play C. Then pad 23 (wide). Play C. Then press pad 21 (close) | Drop-2: **G C E B**. Wide: **C G E B** | |
| B8 | Pad 24 once | Pad 24 **bright orange** (bass below). Play C: **a C an octave below, then C E G B** | |
| B8b | Pad 24 again | Pad 24 **white** (rootless over bass). Play C: **C, then E G B an octave higher** (no C in the chord above) | |
| B8c | Pad 24 again. Play C | Pad 24 dim orange (no bass). **C E G B** (this is the chord voice leading starts from in B9b) | |
| B9 | **Voice leading.** Pad 25 (close) | Pad 25 bright blue, 26–27 dim blue. **Row 3: pad 17 dim blue, pads 18–20 dark** | |
| B9b | Play C, then F | C: **C E G B**. F: **C E F A** (C and E below the pad's F) | |
| B9c | Play E, then D, then C | E: **B D E G**. D: **A C D F**. C: **G B C E**. The whole chord walks down together | |
| B10 | Chords page: pad 17 (voice leading off, root position). Press Note. Play C | Pads 25–27 were all dim, pad 17 bright. **C E G B** | |
| B10b | Chords page: pad 26 (top line). Play F, then E | F: **E F A C**. E: **D E G B** | |
| B10c | Play D, then C | D: **D F A C**. C: **C E G B**. The highest notes: C, B, C, B | |
| B11 | Chords page: press pad 18 (1st inversion) | **Pads 25–27 all dim** (an inversion pad turns voice leading off). Pad 18 bright blue. Then press pad 17 | |
| B12 | **Strum.** Pad 2 (triad), pad 28 (slow) | Pad 28 bright white, 29–30 dim. Play C: **a slow roll, C, then E, then G** | |
| B12b | Pad 30 (fast). Play C | A fast roll, nearly together | |
| B12c | Pad 32 (falling). Play C | Pad 32 bright. **G, E, C: high to low** | |
| B12d | Pad 31 (rising). Then press pad 30 (the lit speed) | Pads 28–30 all dim: strum off. Play C: **C E G together** | |
| B13 | **Shared notes.** Hold C (C E G). Add E (E G B) and hold both. Let go of E. Listen. Then let go of C | When you let go of E: **E and G start again** (a new attack) and sound on with C. Letting go of C: everything stops | |
| B14 | **A MIDI track** (needs a MIDI monitor on the computer, on the Circuit's USB port, or a synth on MIDI out; else skip to C). Shift + MIDI 1 (its Chords page). Press pad 2 (triad). Press MIDI 1. Play C, let go | **Three note-ons** (C, E, G), all on one channel, then **three note-offs**. Write down the channel. (If the monitor shows nothing, check stock's MIDI settings in the Setup view and MIDI 1's channel in Components) | |

### C. Two pads of one pitch (a regression check)
Covers: stock's own case of two pads that play the same note, held together and released in each order, with and
without a chord. Emulation: stock's router ends the sounding note and sounds it again on the second press, so every
note-on gets its note-off. PL14 passed it on the device.

Start: as section B left it. **Switch the Note view to stock's scale layout** (the scale on each row; the row above is
an octave higher). In C major, **pads 17 and 32 both play C**.

| # | Do | Expect | Result |
|---|---|---|---|
| C1 | Shift + Synth 1 (Chords): pad 1 (shape off). Press Synth 1. Tap pad 17, then pad 32 | **The same note** by ear. Write down whether both pads light while you hold one of them | |
| C2 | Hold pad 17. Hold pad 32 too. Let go of pad 17, then of pad 32 | The note stops when you let go of pad 32. **Nothing keeps sounding** | |
| C2b | Hold pad 17, then pad 32. **Let go of pad 32 first**, then of pad 17 | The note stops at the last release. Nothing keeps sounding | |
| C3 | Shift + Synth 1 (Chords): pad 2 (triad). Press Synth 1. Do C2 again | C E G while you hold. **After both are let go, nothing keeps sounding** | |
| C3b | Do C2b again (triad) | The same: nothing keeps sounding | |
| C4 | *Optional (a MIDI monitor):* Shift + MIDI 1 (its Chords page): pad 1 (shape off). Press MIDI 1 (its Note view, scale layout). Hold pad 17, hold pad 32, let go of 17, let go of 32. Count the monitor's messages for that note | **As many note-offs as note-ons** (emulation: on, then off and on at the second press, then off at the last release). Write down the order | |
| C4b | *Optional:* the same, letting go of pad 32 first | As many note-offs as note-ons. Write down the order | |
| C5 | Switch the Note view back to your keyboard layout. Close the MIDI monitor's tab | | |

**End of sitting 1.**

### D. Step entry, pattern strum, mono record, count-in
Covers: the Keys page; chords in step entry (step first, pad first, the pad again); pattern strum Played and Written;
mono record; the count-in; a note held past 16 steps.

Start: **a new empty project**, a **major scale on C**. Synth 1 on its sustained Poly patch. The click green, record
quantise on. Synth 1's Note view, stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| D1 | Shift + Synth 1 (Chords). Press pad 2 (triad). Shift-tap 32 (Keys) | Keys: pad 1 dim magenta, pad 2 dim green, pads 3–4 dim white | |
| D2 | **Stock's step entry (pad 2 off).** Press Synth 1. Hold step pad 1. Press the C pad and let go. Let go of step pad 1. Hold step pad 1 again | **Only C** sounds, only the C pad lights: with pad 2 off, step entry is stock's | |
| D2b | Still holding step pad 1, press the C pad and let go. Let go of step pad 1. Hold it again | Nothing: the C went out, as in stock. Let go | |
| D3 | Shift + Synth 1 (Keys). Press pad 2 | Pad 2 **bright green**. Pad 3 stays dim white (phantom check) | |
| D4 | Press Synth 1. Hold step pad 1. Press the C pad and let go of it. Keep holding step pad 1 | **At once: C E G together**, sounding while you hold step 1. The C, E and G pads light; **the D pad does not** (phantom check) | |
| D4b | Let go of step pad 1. Press Play, listen for two bars, press Play (stop) | **C E G on beat 1** of each bar, short (one step) | |
| D5 | **Step first, step let go first.** Hold step pad 5. Press the C pad and keep holding it. Let go of step pad 5 (still holding C) | The chord sounds while you hold both. **Every note stops when you let go of step 5**, though you still hold C (stock does the same with one note: step first, the sound ends with the step). Let go of C: still silence | |
| D5b | Hold step pad 5 | C E G: the chord went in. Let go | |
| D6 | **Pad first, step let go first.** Hold the C pad (C E G). Keep holding it. Press step pad 9 and hold it. **Let go of step pad 9.** Keep holding C for two seconds, then let go | **C, E and G all keep sounding until you let go of C** (new in this build, as stock does for a note). Listen for E and G. Then silence | |
| D6b | Hold step pad 9 | **C E G**: step 9 has the chord. Let go. Hold step pad 10: nothing (phantom check) | |
| D7 | **The pad again takes it out.** Hold step pad 9. Press the C pad and let go of it | At once the chord stops. Let go of step 9. Hold it again: nothing. Let go | |
| D8 | **Played.** Shift + Synth 1 (Keys). Press pad 3 | Pad 3 **bright white**. Pad 4 stays dim white (phantom check) | |
| D8b | Shift-tap 25 (Chords). Press pad 28 (slow) | Pad 28 bright white, pad 31 bright white (rising) | |
| D8c | Press Play. Listen for two bars | On beats 1 and 2: **C, E, G one after another**, low to high (steps 1 and 5 hold plain chords; CTPlay strums them). Keep it playing | |
| D8d | Press pad 32 (falling). Listen. Then pad 31 (rising) | From the next pass: **G, E, C**. Then low to high again | |
| D8e | Press pad 28 (the lit speed: strum off). Listen. Then pad 28 again | **C E G together** while the strum is off, though Played is still on. Then strummed again. Press Play (stop) | |
| D9 | **Written.** Shift-tap 32 (Keys). Press pad 4 | **Pad 4 bright white**, pad 3 dim | |
| D9b | Press Synth 1. Hold step pad 9. Press the C pad and let go of it. Keep holding step 9 | **C and E** at once (the notes the roll puts in step 9; the preview plays them together). The C and E pads light; **the G pad does not, nor the D pad**. Let go | |
| D9c | Hold step pad 10 | **G alone** (it went in when you let go of the C pad: 8 ticks after C, step 10). Let go. Hold step 11: nothing | |
| D9d | Press Play. Listen for two bars. Stop | Beats 1 and 2: **C E G together** (plain chords: Written does not strum them). **Beat 3: C, E, G one after another** (the roll) | |
| D10 | Shift + Synth 1 (Keys). Press pad 4 | Pads 3–4 dim: pattern strum off. Shift-tap 25 (Chords): press pad 28 (strum off: pads 28–30 dim) | |
| D11 | **Mono record.** Shift-tap 27 (Pattern tools). Press pad 16 | Pads 1–16 bright orange. Pad 32 dim orange | |
| D11b | Press pad 32, then pad 32 again, and lift | Written when you lift (the last played pad, C, with its triad). Pad 32 dim orange, steady. Pad 31 blue | |
| D11c | Shift-tap 32 (Keys). Press pad 1 | Pad 1 **bright magenta** (mono). Shift-tap 25 (Chords): press pad 1 (shape off) | |
| D11d | Press Synth 1. Press Play: **C E G on every step**. Press Record. During one bar, tap the **G pad** once, short. Press Record (off). Listen for two bars | On every pass **one step plays G alone**; every other step plays C E G. The G replaced that step's chord | |
| D11e | Press Play (stop). Hold the step pads 1–16 one by one | **Exactly one step lights the G pad alone**; every other step lights C, E and G | |
| D11f | Shift + Synth 1 (Chords). Shift-tap 32 (Keys). Press pad 1 | Pad 1 dim magenta (poly, stock) | |
| D12 | **Count-in and a long note.** Press Patterns. Tap pad 9 (Synth 1's pattern 2, empty; stopped: at once). In stock's Pattern Settings set its end step to **32**. Press the Note button | A 32-step pattern: the step pads show steps 1–16 | |
| D12b | Hold Shift, press Clear until it shows **cyan** (count-in and click). Press Record, then Play | **Four clicks**, Record blinking on each. Then the sequencer starts, recording. Press Record (off), Play (stop) | |
| D12c | Press Record, then Play. During the count press Play again | The count stops. **Nothing starts.** Record stays armed. Press Record (off) | |
| D13 | **A note held 20 steps.** Press Record, then Play. On the first beat after the four clicks, press and hold the C pad. Let go on **beat 2 of the second bar** (step 21). Press Record (off). Let it loop | **One long C**, about five beats, with **no new attack 16 steps after it began**. Silence after it until the loop comes round. Stop | |
| D13b | Hold Shift, press Clear until it shows **green** (the click only) | | |

### E. Arpeggiator
Covers: the patterns, rate, triplet, octaves, gate, the strum pads with an arpeggio, the sequencer's grid, latch,
the arpeggio on a track muted in the Mixer, recording an arpeggio.

Start: as section D left it, stopped. The click green. **To change a setting:** Shift + Synth 1 (it opens the Arp
page once E1b is done), press the pad, press Note.

| # | Do | Expect | Result |
|---|---|---|---|
| E1 | Press Patterns. Tap pad 17 (Synth 1's pattern 3, empty: the column's third pad). Press Synth 1 | Synth 1's Note view on an empty pattern | |
| E1b | Shift + Synth 1 (it opens Keys, used last). Shift-tap 25 (Chords): pad 2 (triad). Shift-tap 26 (Arp): pad 2 (up), pad 11 (1/16) | Chords pad 2 bright green. Arp pad 2 bright green, pad 11 bright blue | |
| E2 | Press Synth 1. Hold the C pad two seconds | **C E G C E G …** in sixteenths at 120 BPM. It stops when you let go | |
| E3 | Arp page: pad 3 (down). Hold C | **G E C G E C …** | |
| E3b | Pad 8 (chord). Hold C | **C E G together**, again and again, every sixteenth | |
| E3c | Pad 6 (random). Hold C | C, E and G in a random order, **never the same note twice in a row**. Then pad 2 (up) | |
| E4 | Pad 10 (1/8). Hold C | Half as fast | |
| E4b | Pad 13 (triplet, bright magenta). Hold C | **Three notes a beat.** Then pad 13 again (off), pad 11 (1/16) | |
| E5 | Pad 18 (2 octaves). Hold C | **C E G, then C E G an octave up**, again | |
| E6 | Press pad 21 three times, looking after each | The gate colours of **2/6, 1/6, then 6/6** (legato), as stock's Gate view. Hold C: the notes join. Press pad 21 three more times: 5/6, 4/6, 3/6 | |
| E7 | Shift-tap 25 (Chords). Look at pads 28–32 | **Pads 28–30 dark** (strum off, stored), **pad 31 dim white, pad 32 dark**: with an arpeggio on, strum is ignored. Shift-tap 26 (Arp) | |
| E8 | Press Play. Press Synth 1. Hold C for a bar | **Locked to the click: four notes per click.** It stops when you let go | |
| E9 | Shift + Synth 1 (Arp). Press pad 16 (latch). Press Synth 1. Tap C | Pad 16 was bright orange. **The arpeggio goes on after you let go** | |
| E9b | Tap the E pad | The arpeggio changes to **E G B** (and an octave up) | |
| E10 | **A muted track.** Press Mixer. Press pad 1 (Synth 1's mute, as in stock). Listen for two bars | Write down whether you hear the arpeggio while the track is muted (emulation: it keeps sounding, as stock plays a live pad on a muted track). If you hear it: **every note, in time, not stuck on one note** | |
| E10b | Press pad 1 again (unmute). Listen for a bar | The arpeggio plays: up, in sixteenths, in time | |
| E11 | Shift + Synth 1 (Arp). Press pad 16 (latch off) | **The arpeggio stops** | |
| E12 | **Recording.** Press pad 17 (1 octave). Press Synth 1. Press Record. Hold C for one bar. Press Record (off). Listen for two bars | The recorded arpeggio plays back **as you played it**, on every pass: C E G in sixteenths | |
| E12b | Press Play (stop). Shift + Synth 1 (Arp): pad 1 (pattern off) | Pad 1 bright green | |

**Break here if you like:** sections F and G need section D's project as E left it. Save it (Save, Save) and load it
again after the break.

### F. Euclidean fills
Covers: the hits and their preview, rotate, Write (two presses, on the lift), Undo and Undo again, the cycle, a draft,
the second rhythm and combine, the thinning, dice rhythm.

Start: as section E left it, stopped. **Synth 2** on a short Poly patch (a pluck). Synth 2 has no settings yet.

| # | Do | Expect | Result |
|---|---|---|---|
| F1 | Press Mixer. Press pad 1 (mute Synth 1: its patterns stay quiet). Press Synth 2 (its Note view). Play C once | A single C | |
| F2 | Shift + Synth 2 (Chords). Shift-tap 27 (Pattern tools). Press pad 5 | **Pads 1, 5, 8, 11, 14 bright orange**, the rest of rows 1–2 dim. Pad 32 dim orange | |
| F3 | Press pad 18 (later) | Pads **2, 6, 9, 12, 15**. Then press pad 19 (start): back to 1, 5, 8, 11, 14 | |
| F4 | Press pad 32 once | Pad 32 **blinks**. Nothing is written | |
| F4b | Press pad 32 again, and lift | Written when you lift. Pad 32 dim orange, steady. **Pad 31 blue** (an Undo) | |
| F5 | Press Play | **C on steps 1, 5, 8, 11, 14.** Keep it playing | |
| F6 | Press pad 3 | The preview: **pads 1, 7, 12.** The loop does not change (plain Euclid: no draft) | |
| F6b | Press pad 26 (cycle 5) | Pad 26 bright cyan. The preview: **pads 1, 3, 5, 6, 8, 10, 11, 13, 15, 16**. The loop does not change | |
| F7 | Press pad 32 twice, and lift | The loop plays the ten Cs. **Pad 32 bright orange, steady: a draft** (the cycle is a new setting) | |
| F7b | Press pad 26 (cycle off), and lift | When you lift, the loop changes: **C on 1, 7, 12** (in a draft, a press writes) | |
| F8 | Press pad 31 (Undo), and lift | **Pad 32 dim orange**: the draft ended. The loop: **the five Cs of F5** (the pattern from before the draft's first Write) | |
| F8b | Press pad 31 again | The last draft is back: C on 1, 7, 12 | |
| F9 | Shift-tap 27 (Pattern tools 2). Press pad 4 | **Pads 1, 5, 9, 13 bright white** (the second rhythm). The loop does not change | |
| F9b | Press pad 21 (combine: either) | Pad 21 bright violet. The loop does not change (no draft) | |
| F9c | Press pad 32 twice, and lift | The loop: **C on 1, 5, 7, 9, 12, 13** (either rhythm). Pad 32 bright orange (a draft) | |
| F9d | Press pad 24 (combine: accent) | When you lift: **C on 1, 7, 12; step 1 louder** (it is also on the second rhythm) | |
| F9e | Press pad 24 again (combine off). Press ▲ (Pattern tools), pad 16 | When you lift: **a C on every step** | |
| F10 | Press ▼ (Pattern tools 2), pad 27 (thinning 1 in 2) | When you lift, five notes drop out: **steps 4, 7, 9, 13 and 15 are silent**, 11 Cs are left. Step 1 plays (thinning never drops the first hit) | |
| F10b | Press pad 29 (dice rhythm) | Other notes drop out; step 1 still plays | |
| F10c | Press pad 27 again (thinning off) | A C on every step again | |
| F11 | Press pad 31 (Undo) | Pad 32 dim orange: the draft ended. The loop: **C on 1, 7, 12** (from before F9c's Write). Keep playing | |

### G. Melodic generator
Covers: the Melody page (order, root, range, accent), the draft, dice notes and dice rhythm, Phrasing (ties, octave
jumps), closing the pages ends the draft.

Start: as section F left it. Synth 2's Pattern tools 2, the loop playing C on 1, 7, 12. Synth 1 muted.

| # | Do | Expect | Result |
|---|---|---|---|
| G1 | Press ▲ (Pattern tools). Press pad 8, then pad 19 (rotation back to the start) | **Pads 1, 3, 5 … 15 bright.** The loop does not change (no draft) | |
| G2 | Shift-tap 28 (Melody). Press pad 2 (up), then pad 18 (degree 1) | Pad 2 bright yellow, pad 18 bright blue, pad 17 dim white. Nothing is written | |
| G3 | Press pad 32 twice, and lift | The loop: **C E G C E G C E** on steps 1, 3 … 15 (C4 upwards). Pad 32 bright orange (a draft) | |
| G4 | Press pad 3 (down) | When you lift: **G E C G E C G E** | |
| G5 | Press pad 7 (random) | Random notes of C, E, G, **never the same twice in a row**. The same on every pass | |
| G6 | Press pad 30 (dice notes) | **Other notes, on the same steps** | |
| G7 | Press pad 29 (dice rhythm) | The notes move to **other steps** (Pattern tools' preview has turned too) | |
| G8 | Press pad 12 (range 2) | The notes spread over **two octaves** | |
| G9 | Press ▲ ▲ (Pattern tools). Press pad 22 (soft). Press ▼ ▼ (Melody). Press pad 14 once | Pad 14 bright yellow (accent: first hit). **The first note of the loop is clearly louder** than the rest | |
| G10 | Shift-tap 28 (Phrasing). Press pad 3 (ties 1 in 2) | When you lift: **some notes last longer**, held over the next hit with no new attack | |
| G10b | Press pad 7 (octave jumps 1 in 2) | **Some notes jump an octave** | |
| G11 | Press Note (the pages close). Shift + Synth 2 | Phrasing. **Pad 32 dim orange**: closing the pages ended the draft. Pad 31 blue | |
| G11b | Press pad 1 (ties 1 in 4) | Pad 1 bright cyan. **The loop does not change** (no draft). Press Play (stop) | |
| G12 | Press Mixer. Press pad 1 (unmute Synth 1) | | |

**End of sitting 2.**

### H. Drums
Covers: the drum pages and the drum page list (**Repeat on pad 26 now, pad 25 dark**), note repeat (rates,
triplets, a rate change while held, playing, velocity shapes, latch, recording with and without unquantized repeats),
drum Pattern tools and Pattern tools 2 (Write, the roll, Undo per drum, the accent, combine, groove, a draft), and
that Write writes ordinary steps.

Start: **a new empty project.** Stopped. The click green.

| # | Do | Expect | Result |
|---|---|---|---|
| H1 | Press Synth 1. Then Shift + Drum 1 | Drum 1 is selected and **its Repeat page** opens. Pads 1–4 dim blue, 5–8 dim magenta. Pad 9 bright white, 10–12 dim white. 13–14 dark. Pad 15 dim cyan, 16 dim orange. 17–28 dark. Pads 29–32 orange, yellow, violet, cyan | |
| H1b | Look at ▲ and ▼ | **▼ orange** (Pattern tools comes next). ▲ dark | |
| H2 | Hold Shift (keep holding it). Look at the pads and the eight track buttons | The drum page list: **pad 26 bright blue, pad 27 dim orange. Every other pad dark, pad 25 too.** All eight track buttons lit, Drum 1–4 in the same colour as Synth 1 | |
| H2b | Still holding Shift, tap pad 25. Release Shift | **Nothing changes**: the Repeat page | |
| H3 | Shift-tap 27 | **Pattern tools:** pads 1–16 dim orange. 17–20 dim white. **Pad 21 in the 1/6 gate colour** (one hit a step). 22 and 24 dim magenta, 23 bright magenta. 25–28 dim cyan. 29 dim white. 30, 31, 32 dark. ▲ blue, ▼ orange | |
| H3b | Shift-tap 27 again. Then hold Shift and look; release it | **Pattern tools 2:** pads 1–19 dim white, 20–24 dim violet, 25–27 dim cyan, **28 dim yellow**, 29 dim white, 30–32 dark. ▲ orange, ▼ dark. With Shift: pad 26 dim blue, **pad 27 bright orange** | |
| H4 | Shift-tap 26. Then Shift-tap 27. Then press ▲, ▲ | The Repeat page, then **Pattern tools 2** (the page of it used last). Then Pattern tools, then the Repeat page | |
| H5 | Press Note | The page closes: stock's expanded drum view. Pads 29–32 in the drum colours, **pads 21–24 dim orange** (FILL, section I) | |
| H5b | Shift + Drum 2 | Drum 2 selected, **its Repeat page** (each drum keeps its own page). Press Mixer: the page closes | |
| H6 | **Note repeat.** Shift + Drum 1 (Repeat). Tap pad 29, then pads 30, 31, 32 | Drums 1–4 once each. Each pad white while you hold it | |
| H6b | **Fixed velocity check.** Tap pad 29 softly, then hard | Soft, then loud. If both sound the same, fixed velocity is on: Shift + Velocity once, try again. Write down whether it was on. Leave it off | |
| H7 | Press pad 3 (1/16). Hold pad 29 for two seconds | Pad 3 bright blue. **Drum 1 at once, then 4 hits a beat**, evenly. They stop when you let go | |
| H7b | Press pad 7 (1/16T). Hold pad 29 for two seconds | Pad 7 bright magenta, pad 3 dim. **6 hits a beat** | |
| H7c | Press pad 2 (1/8). Hold pad 29. While holding it, press pad 4 (1/32), then pad 2 again | **2 a beat, then 8, then 2.** No restart, no extra hit at the changes | |
| H7d | Press pad 2 again (the lit rate). Hold pad 29 | Pads 1–8 all dim: no rate. **One hit only** | |
| H8 | Press pad 3 (1/16). Press Play. Hold pad 29 for two bars, pressing it **between two clicks** | The first hit at once, then 4 hits a beat **in time with the click** | |
| H9 | Press pad 10 (fade). Hold pad 29, pressed hard, for two seconds. Then pad 11 (swell), the same | Fade (pad 10 bright white): **loud first, softer over one beat**, then it stays soft. Swell: **soft first, louder over one beat** | |
| H9b | Press pad 12 (accent the beat). Hold pad 29 for a bar | **The hits on the clicks loud**, the others softer. Then press pad 9 (as struck) | |
| H10 | Press Play (stop). Press pad 16 (latch). Tap pad 29 | Pad 16 bright orange. **Drum 1 keeps repeating** after you let go. **Pad 29 pulses white** | |
| H10b | Press Note (the page closes) | **Drum 1 keeps repeating** | |
| H10c | Shift + Drum 1. Tap pad 31 | Pad 29 still pulsing. Drum 3 repeats too; pad 31 pulses | |
| H10d | Press pad 16 (latch off) | **Both stop at once.** Pads 29 and 31 in their drum colours again | |
| H11 | **Drum Pattern tools.** Shift-tap 27 (Pattern tools). Press pad 4 | **Pads 1, 5, 9, 13 bright orange.** Pad 32 dim orange | |
| H11b | Press pad 32 once, then again, and lift | Pad 32 blinked after the first press. After the lift: dim orange, steady; **pad 31 blue** | |
| H11c | Press Play. Listen for two bars | **The kick on every beat.** Keep playing | |
| H12 | Press pad 21 | Pad 21 in the **3/6 colour** (two hits a step) | |
| H12b | Press pad 32 twice, and lift | At once: **a double kick on every beat** | |
| H13 | Press pad 31 (Undo) | **Single kicks again** (the pattern from before the last Write). Press pad 31 again: double kicks | |
| H14 | Shift + Drum 2 (Repeat). Shift-tap 27 (Pattern tools). Press pad 8 | **Pads 1, 3, 5 … 15 bright** | |
| H14b | Shift-tap 27 (Pattern tools 2). Press pad 28, then pad 28 again | Pad 28 bright yellow (first hit), then **white** (on the beat) | |
| H14c | Press pad 32 twice, and lift | **Pad 32 bright orange, steady** (a draft: the accent). Drum 2 on every second step, **the four on the beat louder**. Drum 1's double kicks go on | |
| H15 | Press pad 28 twice | Magenta (every 3rd hit), then dim yellow (off). At once (the draft): **drum 2's hits all equally loud** | |
| H15b | Press pad 3 (second rhythm: 3 hits), then pad 24 (combine: accent) | Pads 1, 7, 12 bright white, pad 24 bright violet. At once: **drum 2's steps 1 and 7 louder** | |
| H16 | Press pad 31 (Undo) | **Pad 32 dim orange**: the draft ended. **Drum 2 silent** (its pattern from before the draft: empty). **Drum 1's double kicks go on**: each drum has its own Undo | |
| H17 | Shift + Drum 3 (Repeat). Shift-tap 27 (Pattern tools). Press pad 4, then pad 20 | Pad 20 bright white (groove). **Pads 1, 9, 13 and 16 bright** | |
| H17b | Press pad 32 twice, and lift | Pad 32 bright orange (a draft: the groove). Drum 3 on steps 1, 9, 13, 16 | |
| H17c | Press Play (stop). Press Drum 1 | The page closes. **Step pads 1, 5, 9, 13 lit**: Write wrote ordinary steps | |
| H18 | **Recording repeats.** Press Patterns. Tap pads 13, 14 and 15 (Drums 1, 2 and 3 on their empty pattern 2) | Drums 1–3 on an empty pattern. Drum 4's pattern 1 is empty | |
| H18b | Shift + Drum 4 (Repeat). Press pad 4 (1/32). Hold Shift and look at Record | Record bright: record quantise on. Release Shift | |
| H18c | Press Record, then Play. Hold pad 31 (Drum 3) for two beats. Listen to the loop | **Drum 3 plays back at half the speed** (4 a beat): quantise put one hit on each step | |
| H18d | Press pad 15 (unquantized repeats). Hold pad 32 (Drum 4) for two beats. Listen. Then hold Shift and look at Record | Pad 15 bright cyan. **Drum 4 plays back as fast as you played it** (8 a beat). Record **still bright** with Shift: CTPlay did not change record quantise | |
| H18e | Press Record (off), Play (stop). Press pad 15 (off) | | |

### I. Trig conditions
Covers: row 4 of stock's probability view (the pass grid, a hold, a tap, clearing), the counts starting over at Play,
the specials (FIRST), FILL on a drum, a condition on a synth track, a condition kept by Duplicate, cleared by Clear,
cleared by a Write and brought back by its Undo.

Start: **a new empty project.** Stopped. The click green. Press and release is a **tap**; a **hold** is about a
second. Row 4 edits the step row 3 shows: stopped, the step you tapped last.

| # | Do | Expect | Result |
|---|---|---|---|
| I1 | Press Drum 1 (its step view). Tap step pads 1 and 9 | Step pads 1 and 9 lit | |
| I1b | Shift + Pattern Settings. Tap step pad 9 | The probability view. **Row 3 all 8 lit** (always). **Row 4 dark** | |
| I2 | **Hold** pad 26 about a second. Watch row 4 while you hold it. Let go | After half a second, while you hold it: **pad 25 bright cyan, pad 26 dim cyan.** The same after you let go. Pad 27 dark (phantom check) | |
| I2b | Tap pad 26, then tap pad 25 | **Pad 25 dim, pad 26 bright**: pass 2 of 2 | |
| I3 | Press Play. Listen for **4 bars** | Beat 1 every bar. **Beat 3 only in bars 2 and 4.** Row 4 lights only while step 9 plays. (If row 4 stays lit, press Shift + Patterns once) | |
| I3b | Press Play (stop), then Play. Listen for 2 bars. Stop | **Bar 1 has no beat 3**, bar 2 has: Play starts the count over | |
| I4 | Tap step pad 9. **Hold** pad 28, let go. Tap pad 27 | After the hold: **pad 26 bright** (the ticked pass that fits is kept), 25, 27 and 28 dim, 29–32 dark. After the tap: **pads 26 and 27 bright**, 25 and 28 dim | |
| I4b | Press Play. Listen for **8 bars**. Stop | **Beat 3 in bars 2, 3, 6 and 7** | |
| I5 | Tap step pad 9. **Hold** pad 28 (the cycle's length) again, let go | **Row 4 dark**: the condition is gone | |
| I6 | Hold Shift (keep holding it) | Row 4: **pads 25–26 dim green, 27–28 dim orange, 29–30 dim violet, 31–32 dim yellow** | |
| I6b | Still holding Shift, tap pad 25 (FIRST). Look. Let go of Shift | With Shift: **pad 25 bright green**, pad 26 dim green (phantom check). Without Shift: **all 8 dim green** | |
| I6c | Press Play. Listen for 3 bars. Stop | **Bar 1: beats 1 and 3. Bars 2 and 3: beat 1 only** | |
| I7 | **FILL.** Tap step pad 9. Hold Shift, tap pad 27 (FILL), let go of Shift | All 8 dim orange | |
| I7b | Press Note (the step view), then Note again | The expanded view. **Pads 21–24 dim orange.** Pads 29–32 the drums | |
| I7c | Press Play. Listen for 2 bars | **Beat 1 only** (FILL off: step 9 silent) | |
| I7d | **Hold** pad 21 for two bars, then let go | While held: **pad 21 bright orange; beats 1 and 3.** After: dim orange, beat 1 only | |
| I7e | **Tap** pad 21 on **beat 2** of a bar. After two more bars press Play (stop) | **Yellow** (armed) for the rest of that bar. **The next bar: bright orange, beats 1 and 3.** Then dim orange, beat 1 only | |
| I8 | **A synth track.** Press Synth 1. Hold step pad 1, press the C pad, let go of both | A single C goes into step 1 | |
| I8b | Shift + Pattern Settings. Tap step pad 1. **Hold** pad 26, let go. Tap pad 26, then pad 25 | **Pad 25 dim, pad 26 bright** (pass 2 of 2) | |
| I8c | Hold Shift | **Pads 27–28 dark** (no FILL on a synth track); 25–26 dim green, 29–30 dim violet, 31–32 dim yellow. Let go of Shift | |
| I8d | Press Play. Listen for 4 bars. Stop | The kick on beat 1 of every bar. **The C only in bars 2 and 4** | |
| I9 | **Duplicate.** Press Patterns. Hold Duplicate, press pad 5 (Drum 1's pattern 1), press pad 13 (its pattern 2), let go of Duplicate | Stock copies pattern 1 into pattern 2 | |
| I9b | Tap pad 13 (pattern 2; stopped: at once). Press Drum 1. Shift + Pattern Settings. Tap step pad 9. Hold Shift | **Pad 27 bright orange**: FILL was copied with the step. Let go of Shift | |
| I10 | **Clear.** Press Drum 1 (the step view). Hold Clear, press step pad 9, let go of both | Step pad 9 unlit. Step pad 10 unlit (phantom check) | |
| I10b | Tap step pad 9 (a new hit). Shift + Pattern Settings. Tap step pad 9. Hold Shift | **No pad bright**: the new hit has no condition. Let go of Shift | |
| I11 | **Write and Undo.** Hold Shift, tap pad 25 (FIRST), let go of Shift. Shift + Drum 1 (Repeat). Shift-tap 27 (Pattern tools). Press pad 4. Press pad 32 twice, and lift | Written: the shown pattern (pattern 2) | |
| I11b | Press Drum 1. Shift + Pattern Settings. Tap step pad 9. Hold Shift | Step pads 1, 5, 9, 13 lit. **No pad bright**: Write cleared the condition. Let go of Shift | |
| I11c | Shift + Drum 1 (Pattern tools). Press pad 31 (Undo). Press Drum 1, Shift + Pattern Settings, tap step pad 9, hold Shift | Step pads 1 and 9 lit (the pattern before the Write). **Pad 25 bright green**: Undo brought FIRST back. Let go of Shift | |

### J. A stock regression pass
Covers: what CTPlay hooks, with every CTPlay setting off: it must work as stock. One row per function.

Start: **a new empty project** (every CTPlay setting off). Synth 1's Note view, stopped. The click green.

| # | Do | Expect | Result |
|---|---|---|---|
| J1 | Play a few key pads | Single notes; each pad lights as in stock | |
| J2 | Press Octave ▼, play a pad; press ▲, play it again | An octave lower, then back (no page is open: the buttons are stock's) | |
| J3 | Press Record, then Play. Play four notes over a bar. Press Record (off). Listen for two bars | **The four notes play back** where you played them | |
| J4 | Stop. Find an empty step: hold step pads 16, 15, 14 … until one plays nothing. Hold it, press the E pad, let go of both. Hold that step pad again | The E sounds and its pad lights: **only E** | |
| J4b | Hold the same step pad, press E again, let go. Hold the step pad again | Nothing: the E went out | |
| J5 | Press Gate. Hold the step pad of a note from J3. Press pad 20 | Its gate: 4 steps (pads 17–20 lit); it plays longer. Press Note | |
| J6 | Press Drum 1. Tap step pads 1, 5, 9, 13. Press Play | A kick on every beat | |
| J7 | Press Note (the expanded view). Tap pads 29–32 | Drums 1–4 sound. Rows 1–2 dark. **Pads 21–24 dim orange** (CTPlay's FILL: the one change to this view) | |
| J8 | Press Drum 1. Shift + Pattern Settings. **Hold** step pad 5, press pad 20, let go of both (while playing, stock takes a row 3 press only with a step pad held) | While you hold step 5, after the press: row 3 pads 17–20 lit (50 %), row 4 dark. **Step 5's kick plays on about half of the bars** | |
| J9 | Hold Shift, press Clear once (from green) | Clear magenta: count-in only. **No click** while playing. Press Shift + Clear three more times, listening: cyan (the click), red (no click), green (the click) | |
| J10 | Press Play (stop). Press Shift + Play | It continues from where it stopped (stock's continue) | |
| J11 | Press Mixer. Press pad 5 (Drum 1's mute) | Drum 1 silent. Press it again: back | |
| J12 | Press FX. Turn up Drum 1's send on the effect the view shows (reverb or delay, as in stock) | The kick gets that effect. Turn it back down | |
| J13 | Press Patterns. Tap pad 13 (Drum 1's pattern 2, empty) | After this bar: no kick. Tap pad 5: the kick comes back after the bar | |
| J13b | Hold pad 5, press pad 13, let go | A chain: a bar of kicks, a bar without. Tap pad 5 (pattern 1 alone) | |
| J14 | Press Mixer. Hold Shift, tap pad 17 (save scene 1: Drum 1 on pattern 1). Press Patterns, tap pad 13 | After the bar: no kick (pattern 2) | |
| J14b | Press Mixer. Tap pad 17 (scene 1) | At the end of the bar the kicks come back: scene 1 recalled | |
| J15 | Press Synth 1, then Preset (Synth 1's patches). Pick another patch. Press Synth 1, play a pad | The new sound | |
| J16 | Press Tempo/Swing; turn the tempo up | Faster. Set it back to 120 | |
| J17 | Press Scales; pick another scale. Press Synth 1 | The key pads follow the new scale | |
| J18 | Press Play (stop). Save the project (Save, Save). Load it (Projects view, its slot). Press Play | It saves and loads as stock. **The kick and Synth 1's notes play as before.** Stop | |

### K. The link (protocol 2, on the test page)
Covers: hello, a read in chunks, a write answered at once, refused writes (a value no pad makes, a field that is not
linked, past the payload), pad presses pushed to the page. **The page's Write offset is in hex.** The page logs each
message, newest on top; the table appears once every chunk of the state has arrived.

Start: **a new empty project.** Stopped. **Close every other MIDI tab** (uploader, CTCtrl, a MIDI monitor). On the
Circuit: Shift + Synth 1 (the Chords page).

| # | Do | Expect | Result |
|---|---|---|---|
| K1 | Open `slim/pages/ctplay_link.html` (the beta checkout's) in Chrome. Press **Allow MIDI access** | "Connected: **PL21, protocol 2, layout 1, 118 B, 18 fields**." The log: `hello: PL21, 18 fields` | |
| K2 | Press **Read** | Two log lines: `chunk: offset 0, …` and `chunk: offset 64, …`. Then the table: **18 rows**, from `chord settings` (offset 0) to `pattern strum` (offset 116). `strum` reads `00`, `arp` `00 08 00 08 00 08 00 08`, `repeat` `00 00` | |
| K3 | **A write.** Offset `5`, Bytes `01`. Press Write | The log: `write: offset 5 (hex), 01`, and **at once** a `chunk: offset 0` line. The `strum` row: `01`. **On the Circuit: pad 28 bright white** (Synth 1: slow strum) | |
| K4 | **A value no pad makes.** Offset `51` (hex: 81, the Repeat settings), Bytes `09` (rate 9). Press Write | At once a `chunk: offset 64` line: the answer. **The `repeat` row stays `00 00`**: refused | |
| K5 | **A field that is not linked.** Offset `21` (hex: 33, the page Synth 1 opens on), Bytes `03`. Press Write | At once a `chunk: offset 0` line. No row changes. On the Circuit press Note, then Shift + Synth 1: **still the Chords page** (refused) | |
| K6 | **Past the payload.** Offset `80` (hex: 128; the payload ends at 117), Bytes `01`. Press Write | At once a `chunk: offset 64` line (the last chunk answers). Nothing changes | |
| K7 | On the Circuit: Shift + Drum 1 (Repeat). On the page: Offset `51`, Bytes `03`. Press Write | At once a `chunk: offset 64` line; `repeat` reads `03 00`. **On the Circuit: pad 3 bright blue** (1/16) | |
| K8 | **A push.** On the Circuit press pad 10 (fade) | **A `chunk: offset 64` line appears by itself.** `repeat` reads `13 00` | |
| K8b | On the Circuit: Shift + Synth 1 (Chords). Press pad 2 (triad) | A `chunk: offset 0` line by itself. The `chord settings` row's first byte is no longer `00` | |
| K9 | Close the page's tab | | |

**End of sitting 3.**

### L. The recipes
Covers: each recipe in `slim/docs/recipes.md` and the three in the user guide's Recipes section, run **as written**.
The recipes are drafts. Write down per row whether you hear what the recipe says. A mismatch is a recipe fix, not a
firmware bug, unless the feature misbehaves (then say what it did).

Start of each recipe: **a new empty project** (C natural minor), then press **Play**, as the recipes say. Pick the
patch each recipe asks for. Open the recipe on the computer and follow its steps. (`recipes.md` already names the
drum page list's pads as this build has them: 26 Repeat, 27 Pattern tools.)

| # | Do | Expect | Result |
|---|---|---|---|
| L0 | In a new empty project, tap the drum pads (expanded view: Drum 1, then Note; pads 29–32) | Write down what Drum 1–4 are (the recipes assume a kick, a snare, a hi-hat). | |
| L1 | `recipes.md`, **A chord progression that moves smoothly**, steps 1–2 | As written: C E♭ G, A♭ C E♭, E♭ G B♭, B♭ D F, C E♭ G; the chords jump | |
| L1b | Steps 3–4 (close) | C E♭ G, **C E♭ A♭**, E♭ G B♭, **D F B♭**, C E♭ G | |
| L1c | Step 5 (top line) | Only the third chord changes: **B♭ E♭ G**. The top notes: G, A♭, G, B♭, G | |
| L1d | Step 6 (record) | The chords record as you hear them | |
| L2 | `recipes.md`, **Off-beat chord stabs**, steps 1–3 | Step 3: **C E♭ G B♭** while you hold step 3; the same on step 7 | |
| L2b | Steps 4–5 | Steps 11 and 15: **A♭ C E♭ G**. The pattern: C minor 7 twice, A♭ major 7 twice, between the beats | |
| L2c | Step 6 | Step 7 empty after the pad again; back after putting it in again | |
| L2d | Steps 7–8 (Played, fast) | Each stab strums up, 20 ms apart; its notes end together | |
| L2e | Step 9 (medium, then falling) | A looser strum; then down, from the highest note | |
| L3 | `recipes.md`, **An arpeggio you can play over**, steps 1–3 | Sixteenths: **C E♭ G B♭, then the same an octave up**, on and on, also after you let go | |
| L3b | Step 4 | **A♭ C E♭ G** and an octave up | |
| L3c | Step 5 | 1-16/17-32 blue with Shift; pad 20 or 22 changes the pattern while it plays | |
| L3d | Steps 6–7 | It goes on while you play another track; latch off stops it | |
| L4 | `recipes.md`, **A beat from four drums**, step 1 | Steps 1, 5, 9, 13 in the preview; four on the floor | |
| L4b | Step 2 | Steps 1 and 9, then 5 and 13 after four presses of pad 18; the snare on beats 2 and 4 | |
| L4c | Step 3 | Eighth-note hi-hats; the ones on the beat hard, the others soft | |
| L4d | Step 4 | Steps 1, 7, 12, then 3, 9, 14; each hit a quick double | |
| L5 | `recipes.md`, **Hi-hats played live**, steps 1–2 | The hi-hat in sixteenths while held, in time; it stops on release | |
| L5b | Steps 3–4 | Accent on the beats; triplets at the next grid point while held; back to 1/16 | |
| L5c | Steps 5–6 | A fade over a beat; with latch, the hi-hat goes on after you let go, and a tap stops it | |
| L6 | User guide, **A melody from a 9th chord**, steps 1–4 (Synth 2) | **C3 E♭3 G3 B♭3 D4** together, held for the whole bar | |
| L6b | Steps 5–6 (Synth 1) | The preview: **steps 1, 5, 8, 9, 12, 13, 16** | |
| L6c | Steps 7–8 | **C4 E♭4 G4 B♭4 C5 D5 E♭5** | |
| L6d | Step 9 | **C4 D5 C4 E♭4 D5 C4 D5** | |
| L6e | Step 10 | C4 D5, then **C4 held from step 8 to step 13**, then E♭4 D5 | |
| L6f | Step 11 | Steps 1, 5 and 13 harder | |
| L6g | Step 12 | Dice: new notes on the same rhythm; a new groove for the same notes. Undo: the empty pattern | |
| L7 | User guide, **A bass line**, steps 1–2 | The preview: **steps 1, 4, 7, 9, 12, 15** | |
| L7b | Steps 3–5 | **C2 G2 C2 C2 C2 G2**; steps 1 and 9 harder | |
| L7c | Steps 6–7 | **C2 G2 C3 C3 C3 G2**; dice notes: another line, step 1 still C | |
| L7d | "A second chord" | **A♭2 E♭3 A♭3 A♭3 A♭3 E♭3**; chained: a bar of C, a bar of A♭ | |
| L8 | User guide, **A riff that drifts against the beat**, steps 1–2 | The preview: **steps 1, 3, 5, 6, 8, 10, 11, 13, 15, 16** | |
| L8b | Steps 3–4 | **C4 E♭4 G4 B♭4 C5 E♭5 G5 B♭5 G5 E♭5**, in groups that do not fit the bar | |
| L8c | Step 5 | Steps 1, 5 and 13 hard | |
| L8d | Step 6 | Thinning: step 13 drops out. Dice rhythm: other groups, other gaps | |

### M. Saved settings (saved format 2), with the flashing
Covers: the alpha project (saved on PL20) loads its settings on PL21, its drums on their pages (Repeat on pad 26
now); settings survive a save, a power cycle and a load; **one round trip to PL20** (allowed here: compatibility
starts with the beta): PL20 loads the beta-saved project with CTPlay's defaults, because the save cleared the alpha
blocks; back on PL21 the settings are there again. All the flashing of this run is here.

Start: PL21 installed. Stopped. **Load the alpha project** (Projects view, the alpha slot of P1).

| # | Do | Expect | Result |
|---|---|---|---|
| M1 | Shift + Synth 1 | **The Keys page** (where P3 left it): **pad 1 bright magenta, pad 2 bright green, pad 3 bright white**, pad 4 dim white | |
| M1b | Shift-tap 25 (Chords) | **Pad 3 bright green** (7th). Pad 17 dim blue, 18–20 dark. Pad 21 bright magenta. **Pad 24 bright orange. Pad 25 bright blue.** Pad 29 bright white. **Pad 32 bright white**, pad 31 dim | |
| M1c | Press Note. Play C | A falling, medium strum: **B♭, G, E♭, C, then a C an octave below** (C minor 7th, bass below; the bass last) | |
| M2 | Shift + Synth 2 | **The Arp page: pad 2 bright green, pad 10 bright blue, pad 18 bright magenta** | |
| M2b | Press Synth 2. Hold Shift | **The 1-16/17-32 LED blue**: the Arp Quick view (pad 18 bright green, pad 26 bright blue). Release Shift | |
| M3 | Hold Shift and look at Clear | **Magenta** (click off) or **cyan** (click on): **the count-in is on**. Release Shift | |
| M4 | Shift + Drum 1 | **The Repeat page: pad 2 bright blue, pad 10 bright white, pad 15 bright cyan**, pad 16 dim orange | |
| M4b | Hold Shift | **Pad 26 bright blue** (Repeat, on its new pad), pad 27 dim orange, **pad 25 dark**. Release Shift | |
| M5 | Shift + Drum 2 | **Pattern tools 2: pad 28 white** (accent on the beat). Pads 1–16 dim white. Pad 32 dim orange | |
| M5b | Press ▲ | Pattern tools: **pads 1, 5, 9, 13 bright orange, pad 21 in the 3/6 colour** | |
| M6 | **More settings, on PL21.** Shift + Synth 1 (Chords). Press pad 11 (quartal) | Pad 11 bright green, pad 3 dim | |
| M6b | Shift + Synth 2 (Arp). Shift-tap 28 (Melody): pad 7 (random). Shift-tap 28 again (Phrasing): pad 2 (ties 1 in 3) | Pad 7 bright yellow; then pad 2 bright cyan. **Leave Synth 2 on Phrasing** | |
| M6c | Shift + Drum 3 (Repeat). Press pad 16 (latch). Shift-tap 27 (Pattern tools): pad 7, then pad 20 | Pad 16 bright orange. Then pads 1, 5, 8, 9, 12, 13, 16 bright, pad 20 bright white (groove). **Leave Drum 3 on Pattern tools** | |
| M6d | Shift + MIDI 1. Shift-tap 32 (Keys). Press pad 4 | Pad 4 bright white (written) | |
| M7 | Press Note. **Save the project** (Save, then Save again: the alpha slot) | It saves as stock does | |
| M8 | **Power off and on.** Load the project (if the Circuit did not open it by itself) | It loads | |
| M8b | Shift + Synth 1 | **Chords** (the page used last): **pad 11 bright green**, pad 25 bright blue, pad 24 bright orange, pad 29 and pad 32 bright white | |
| M8c | Shift-tap 32 (Keys) | Pads 1, 2, 3 bright, pad 4 dim | |
| M8d | Shift + Synth 2 | **Phrasing: pad 2 bright cyan.** Press ▲: Melody, **pad 7 bright yellow** | |
| M8e | Shift + Drum 3 | **Pattern tools**: pads 1, 5, 8, 9, 12, 13, 16 bright, pad 20 bright white | |
| M8f | Shift + Drum 1 | Repeat: **pads 2, 10, 15 and 16 bright** | |
| M8g | Shift + Drum 2. Then Shift + MIDI 1 | Drum 2: Pattern tools (M5b left it there): pads 1, 5, 9, 13 bright. MIDI 1: Keys, pad 4 bright white | |
| M8h | Hold Shift, look at Clear | **Magenta** (click off) or **cyan** (click on): the count-in is on | |
| M9 | **Flash PL20.** Close every MIDI tab. Open the uploader. Pick PL20's `.syx` (Before you start, 3.3): "slim PL20". Send, confirm with Play. Wait for the restart. Identify the device: **CTPlay PL20** | PL20 installed | |
| M9b | Load the project (the alpha slot) | It loads, as stock does | |
| M10 | Shift + Synth 1 | **The Chords page with the defaults:** pad 1 bright green (shape off), pad 17 bright blue, pad 24 dim orange, pads 25–27 dim, pads 28–30 dim, pad 31 bright. (If the alpha settings show, the 7th with its bass and Keys pads lit, the save did not clear the alpha blocks: write it down) | |
| M10b | Shift-tap 32 (Keys) | Pads 1–4 all dim | |
| M10c | Shift + Synth 2 | Its Chords page, defaults (not Phrasing) | |
| M10d | Shift + Drum 1 | PL20's Repeat page (its pad 25): **no rate lit, pad 9 bright**, pads 15 and 16 dim | |
| M10e | Shift + Drum 3 | The Repeat page (not Pattern tools) | |
| M10f | Hold Shift, look at Clear | **Red or green**: no count-in | |
| M10g | Press Play for a bar, then stop. **Do not save on PL20** | Silence (the project has no notes). Nothing hangs; the Circuit works as usual | |
| M11 | **Flash PL21 again** (as in Before you start, 4). Identify the device: **CTPlay PL21**. Load the project | It loads | |
| M11b | Shift + Synth 1. Then Shift + Synth 2. Then Shift + Drum 3 | **The settings are back** (PL20 did not save): Chords pad 11 bright green; Synth 2 on Phrasing, pad 2 bright cyan; Drum 3 on Pattern tools, groove | |

### N. External MIDI clock
| # | Do | Expect | Result |
|---|---|---|---|
| N1 | If `slim/firmware/PL20/TEST-clock.md` has not been run since PL20, run it on this build (about 30 min, its own setup) | As that plan says. Write down here whether it ran, and its result | |

## Results

PL21 syx sha256 (printed by the build): 13b8c9c5a6bbd9b777319913200783b79db4622df0f12bd9483db5f810b3353e  
Date and time taken: 20261111, duration 2:05  

Before you start (P1–P10): Done, no issues  
4: Flashing PL21, uploader didn't return CTPlay for identity. Fixed and working now.  
A: All tests passed  
B: All tests passed  
 B14:  
 TIMESTAMP IN PORT STATUS DATA1 DATA2 CHAN NOTE EVENT               
 00012BD8  16  --     92    40    66    3  E  4 Note On               
 00012BD8  16  --     92    43    66    3  G  4 Note On               
 00012BD8  16  --     92    3C    66    3  C  4 Note On               
 00013B65  16  --     82    40    00    3  E  4 Note Off              
 00013B65  16  --     82    43    00    3  G  4 Note Off              
 00013B65  16  --     82    3C    00    3  C  4 Note Off              

C: Both pads light up when pressing either. C2b note stops sounding on pad 32 release.  
 TIMESTAMP IN PORT STATUS DATA1 DATA2 CHAN NOTE EVENT               
 00043ACF  16  --     90    3C    63    1  C  4 Note On               
 000444D8  16  --     80    3C    00    1  C  4 Note Off              
 000444D8  16  --     90    3C    64    1  C  4 Note On               
 00045F11  16  --     80    3C    00    1  C  4 Note Off              
 000479A5  16  --     90    3C    5F    1  C  4 Note On               
 0004832E  16  --     80    3C    00    1  C  4 Note Off              
 0004832E  16  --     90    3C    65    1  C  4 Note On               
 00048E11  16  --     80    3C    00    1  C  4 Note Off              
C3b chord (pad 17) keeps sounding until released, then stops as expected.  
 TIMESTAMP IN PORT STATUS DATA1 DATA2 CHAN NOTE EVENT               
 0007C9C3  16  --     90    40    61    1  E  4 Note On               
 0007C9C3  16  --     90    43    61    1  G  4 Note On               
 0007C9C3  16  --     90    3C    61    1  C  4 Note On               
 0007CEB7  16  --     80    40    00    1  E  4 Note Off              
 0007CEB7  16  --     90    40    6E    1  E  4 Note On               
 0007CEB7  16  --     80    43    00    1  G  4 Note Off              
 0007CEB7  16  --     90    43    6E    1  G  4 Note On               
 0007CEB7  16  --     80    3C    00    1  C  4 Note Off              
 0007CEB7  16  --     90    3C    6E    1  C  4 Note On               
 0007D8D4  16  --     80    40    00    1  E  4 Note Off              
 0007D8D4  16  --     80    43    00    1  G  4 Note Off              
 0007D8D4  16  --     90    40    61    1  E  4 Note On               
 0007D8D4  16  --     90    43    61    1  G  4 Note On               
 0007D8D4  16  --     80    3C    00    1  C  4 Note Off              
 0007D8D4  16  --     90    3C    61    1  C  4 Note On               
 0007E0B4  16  --     80    40    00    1  E  4 Note Off              
 0007E0B4  16  --     80    43    00    1  G  4 Note Off              
 0007E0B4  16  --     80    3C    00    1  C  4 Note Off              

With single note, the first release always gives the note off. Nothing keeps sounding. C4(b).  
 TIMESTAMP IN PORT STATUS DATA1 DATA2 CHAN NOTE EVENT               
 000B6131  16  --     92    48    62    3  C  5 Note On               
 000B6CFF  16  --     82    48    00    3  C  5 Note Off              
 000B6CFF  16  --     92    48    65    3  C  5 Note On               
 000B85C4  16  --     82    48    00    3  C  5 Note Off              
 000B99E0  16  --     92    48    68    3  C  5 Note On               
 000BA158  16  --     82    48    00    3  C  5 Note Off              
 000BA158  16  --     92    48    6A    3  C  5 Note On               
 000BAB5E  16  --     82    48    00    3  C  5 Note Off              
 000C1456  16  --     92    48    60    3  C  5 Note On               
 000C1B01  16  --     82    48    00    3  C  5 Note Off              
 000C1B01  16  --     92    48    68    3  C  5 Note On               
 000C2CAB  16  --     82    48    00    3  C  5 Note Off              
 000C380E  16  --     92    48    5F    3  C  5 Note On               
 000C3ED3  16  --     82    48    00    3  C  5 Note Off              
 000C3ED3  16  --     92    48    6C    3  C  5 Note On               
 000C4870  16  --     82    48    00    3  C  5 Note Off              

D: All tests passed  
E: All tests passed. E3c wrong pad (7) for Random in test step, correct is 6 and that works. E10 arpeggio keeps playing all notes on muted track.  
F: All tests passed  
G: All tests passed  
H: H6b fixed velocity was off by default. All tests passed.  
I: All tests passed. Step I4 had wrong pad marked as bright, fixed mid run.  
J: All tests passed  
K: All tests passed  
L: L0 - Kick, snare, hi-hat, clap. All recipes work, but might need some minor adjusting to make them (even) easier to follow, possibly some visual help? User guide recipes work, but their instructions aren't as detailed as the main recipes, sometimes refers to pages by their name only. Also could use some visual aids and maybe braking down to smaller steps? For all recipes maybe mention the ▼ ▲ arrows in parenthesis(?) to clarify the option to move using them too?  
M: M8b pad 25 not bright, but I've very likely just missed a step somewhere as everything else was correct throughtout whole section. With that note, all tests passed.  
N: MIDI clock tests done, all tests passed with notes in TEST-clock.md  
