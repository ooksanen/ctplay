# Chord notes that do not sound (PL01, bass on) — investigation

Date: 2026-10-12 · Builds: `PL01`, `PL02` · Status: **settled on the device: polyphony is limited by DSP time, not a fixed 6 voices.** About 4–5 notes hold with the patches tried; a new note beyond that takes the lowest / oldest voice, on stock too. slim does not affect it (ARM-side only; the DSP program is stock's). Answered by PL03's bass modes ("Decision" below).

## What was seen on the device

Synth track, 9th + bass, C major, Chromatic scale, middle octave, one chord at a time. The bass note was audible on
only a few chords. The same pad sometimes had the bass and sometimes not. The chords seemed to change while going
through the scale.

A MIDI capture of the same playing (channel 2) is clean. Every press sends 6 note-ons (four chord tones, the bass
`r − 12`, then stock's own pad note `r`), every note-on has its note-off, nothing is missing or stuck. **The chord
engine sends the right notes; they are lost later, in the synth.**

Follow-up runs (user, 2026-10-12):

| # | Test | Result |
|---|---|---|
| 1 | 9th + bass (6 notes) vs 7th + bass (5 notes) | Bass sounds ~2/10 with 9th + bass, ~7/10 with 7th + bass |
| 2 | Simple patch without effects (a bass patch switched to polyphonic) | The problem seems to go away |
| 3 | Complex patch: the same pad repeatedly | ~50/50; after a short pause the bass mostly plays |
| 4 | Recorded chords played back by the sequencer | The bass drops out at random there too |

So it is not a fixed voice limit: 5 notes also drop, a light patch does not. It is not tied to the pad path either:
sequencer playback, which sends the same notes as stock step notes, loses them too.

**Stock firmware** (user, 2026-10-12), 6-note chords entered into steps by hand, the same or a similar patch:

- Notes drop on stock too: **the dropouts are stock behaviour**, not something PL01 adds.
- By ear the lost note was never the lowest. More often than not it was the highest, sometimes one in the middle,
  mostly towards the top but not the highest.
- The first play of a chord sounded different from the later plays almost every time.

On PL01 the lost note is the bass, the 5th of 6 notes sent (chord tones, bass, then stock's pad note). On stock it is
mostly the highest. Two readings fit both, if the step plays its notes in the order they were entered:
- **Order:** the notes sent last lose. The order of the hand-entered notes is not recorded yet: entered from low to high,
  the highest is sent last.
- **Pitch or level:** the DSP picker's score depends on something in the voice, not the order. Then PL01's bass would
  be an exception to "never the lowest", unless it was stock's pad note an octave up that was lost (by ear the two are
  hard to tell apart).

**Entry-order test on stock** (user, 2026-10-12), the same chord entered low to high and high to low: in both, **the
lowest note is lost most often**, but not every time: it changes between chords. The missing note is hard to pick out
by ear, so "never the lowest" in the first stock run was probably wrong. **Order is ruled out:** the voice itself
decides, through the score the DSP picker `P:$1BB3` reads from `Y:(voice + $E)` (voice blocks at `Y:$122 + $60 v`
for Synth 1, `Y:$362 + $60 v` for Synth 2). What that word holds (something pitch-dependent would explain the lowest
note) is not identified. The picker only runs when DSP headroom is low, so which note goes still varies.

"First play differs" fits the history effect seen in run 3: on later plays the previous play's voices are still
releasing, so there are released voices to take over, and the same pitches are retriggered.

**With strum (PL02, user, 2026-10-12).** Strum sends the notes one by one, rising (the pad's own note, then the bass,
then the chord tones), so each loss can be heard on its own:
- With **any** chord shape + bass at slow strum (50 ms apart), the **bass** is the note that drops.
- It happens with a **simple patch** too (square + triangle bass), so not only under heavy DSP load.
- The bass sounds briefly and stops as the **next** note comes in: it is already lost when only three voices have
  started, far below the synth's 6 voices.

That fits the open reading below (the youngest held voice, still in its attack, is the one taken) better than a plain
voice-count limit, but it does not separate "youngest" from "lowest": in strum order the bass is both.

**Follow-up tests** (user, 2026-10-12, Poly patch; an earlier octave test was void: a power cycle had reset Synth 1
to a Mono patch, whose last-note priority drops and restores the held note):

| Test | Result |
|---|---|
| Stock pads: hold a low C, then other notes (another C included) a couple of octaves higher | The low C survives |
| Stock pads: press a low pad and immediately roll three high pads (age of the low voice) | Survives: age is not it |
| PL02, slow strum, 7th + drop-2, bass off (a chord tone below the root, sent from the same pad) | Survives |
| PL02, slow strum: single + bass (2 notes), triad + bass (4), 7th + bass (5) | Bass holds |
| PL02, slow strum: 9th + bass (6 notes) | Bass drops, also as the first chord after ~5 s of silence |
| **Stock pads, chords off: C2, C3, E3, G3, B3 held one after another** | **C2 drops at B3 (the 5th note) and does not come back** |
| Emulation (PL02, 9th + bass, slow strum; synth and MIDI tracks) | No early note-off for the bass on the ARM side: router, note handling and MIDI out keep it until the release |

**Conclusion.** The notes are lost inside the synth's voice handling, not in anything slim sends: stock's own pads lose
the 5th of five held notes, and the ARM side never ends the bass. "6 voices per synth" is the size of the voice table,
not a guarantee: how many notes hold depends on the DSP time the voices cost (the headroom switch read from
`X:$36 + synth` below), about 4–5 with the patches tried, varying with register and what is still sounding. When a new
note does not fit, the lowest / oldest voice is taken and does not return. slim runs only on the ARM (the heartbeat is
about a hundred instructions per millisecond when idle) and leaves the DSP program untouched, so it does not change
the limit. Not yet repeated on the stock firmware itself (the five-note test was on PL02 with chords off, i.e. stock's
own pad path); expected to match the earlier stock 6-note-step result.

**Decision (2026-10-12): both, as PL03's bass modes** (chord spec, "Bass modes"; `firmware/PL03/TEST.md`). The
limit itself is documented; pad 24 now cycles no bass / bass below (a 9th leaves out its 5th) / rootless over bass,
and the bass is always the lowest note. The options weighed:
- **Document** it: chords of 5–6 notes can lose notes depending on the patch, as stock steps do; the lowest / oldest
  note goes first.
- **Optionally, a lighter bass voicing** (user proposal, refined): with bass on, the pad is the bass and the chord is
  built an octave above it without its root (9th + bass = bass + 3rd, 5th, 7th, 9th: 5 notes, no doubled root). With
  bass on the player plays an octave lower (documented). A musical improvement that saves a voice, not a guarantee.
- Alternative: with bass on, leave out the 5th (pads keep their pitch; the root stays doubled).

## What stock does with a synth note-on (read from the code, not run)

Path: synth note-on `0x0803BD58` → `0x080497CA(synth, note, vel)` → `0x08021D86` → voice picker `0x080219E8`, which
first calls `0x080217B4`.

- **Voice slots.** 12 voices, 16 B each, at `0x20005F64`: Synth 1 owns 0–5, Synth 2 owns 6–11 (`0x080217B4` sets the
  range in `[0x200067FC + 0x10 / 0x11]`). Slot `+4` = state word; a newly allocated voice gets `0x8000FFFF`, a
  note-off clears its top bits.
- **The switch.** `0x080217B4` sends the DSP a "sync" request (`X:$1B` = `0x80000000`, then waits until the DSP clears
  it, i.e. at least one DSP audio block), then reads `X:$36 + synth`:
  - **≥ `0x14000`: the ARM picks** by polyphony mode (`0x080216C6` / `0x0802161A` / `0x08021706`): a free voice, or
    the slot with the lowest state word (released voices before held ones). The chosen slot is written `0x8000FFFF`
    at once (`0x08021934`), so the notes of one burst never share a voice. **This path is safe for chords.**
  - **< `0x14000`: the DSP picks.** Request `X:$1B` = synth + 1, the answer is in `X:$35`. The DSP handles `$1B` in
    its block routine (`P:$198D`, called from `P:$1FC`); the picker `P:$1BB3` looks only at the synth's voices whose
    `Y:(voice + $E)` is ≥ `$100` (a sounding voice, presumably its envelope level). It scores each by that value `>> 4`
    plus flag bits from `Y:(voice)` (`+$20`, `+$10`) and takes the lowest score. **When no voice qualifies it answers
    the synth's first voice.** The ARM then sets `[0x200067FC + 0xE] = 1` and fast-kills the stolen voice
    (`0x08021246` / `0x08021272`).
- **`X:$36 + synth`** is written by DSP code at `P:$1C01`, which reads the DSP timer (`X:$FFFF88`) against a
  block-start time. **Inferred, not proven:** it is DSP time headroom. Low headroom means a new note steals a
  sounding voice instead of starting one, which would make polyphony depend on DSP load.

Each note-on waits for at least one DSP block, so a chord reaches the DSP one note at a time and the headroom reading
drops as the chord's earlier voices start. The last notes of a burst are the most likely to take the DSP path. In
PL01's order those are the bass (5th) and stock's pad note (6th).

## How the device results fit

- 1 and 2 fit load-limited stealing: more notes and a heavier patch mean less headroom.
- 4 fits it too: stock's sequencer sends a 5–6-note step in one burst, the same as a chord.
- 3 fits only in part. A pause lets the previous chord's release finish, which frees DSP time, so the ARM path is
  used: that fits. The first analysis predicted **more** dropouts after a pause (the DSP picking the youngest held
  voice once the released ones are silent); that prediction was wrong.
- **Open:** why the voice taken is so often the bass. The scoring flags in `P:$1BB3` (which bits of `Y:(voice)`, and
  whether they protect held or released voices) are not decoded. If they protect *released* voices, the youngest
  held voice (the bass, still in its attack) would be taken whenever the DSP picks.

## PL03 device run (2026-10-13)

Step 7 (9th, rootless over bass, slow strum: bass + 3rd, 5th, 7th, 9th = 5 notes) **loses the bass**, by ear at about
the second note. Step 5 (9th, bass below, slow strum: also 5 notes) and step 6 (the same, strum off) **keep the bass**.
Emulation of both on PL03, strum off and slow, a low and a middle pad: the 5 note-ons reach the synth endpoint and no
note-off comes before the release (`test_bass_modes_end_no_note_before_the_release`). The ARM side is clean again.

What differs between the two is the order, not the count:

| | First note (oldest) | Then, 50 ms apart |
|---|---|---|
| Step 5, bass below | the pad's root (stock) | bass, 3rd, 7th, 9th |
| Step 7, rootless | **the bass** = the pad's note (stock) | 3rd, 5th, 7th, 9th |
| Step 6, strum off | slim's 4 notes, then stock's pad note last (the hook runs before stock plays it) | |

In step 7 the bass is both the oldest and the lowest voice; in step 5 the oldest is the root (not listened for). A loss
at the second note fits the DSP picker (`P:$1BB3`): when the headroom switch sends a note-on to the DSP, it takes the
lowest-scoring **sounding** voice even if free voices exist, and with one voice sounding that is the bass. Not yet
known: why the switch would take the DSP path with one or two voices playing. Open questions for the device below.

**Follow-up checks on PL03** (user, 2026-10-13, Synth 1, Poly patch):

| Check | Notes | Order | Bass |
|---|---|---|---|
| a. Step 7 with strum off | 5 | the bass (stock's pad note) **last** | holds |
| b. Rootless **7th**, slow strum | **4** | the bass first | holds |
| c. Step 5 again, listening to the pad's root | 5 | the root first, the bass second | both hold |
| d. Step 7, fast strum (10 ms) | 5 | the bass first | drops after a short "pop" |

The loss needs **both** 5 notes and the bass sounding first: four notes with the bass first hold (b), five with the bass
last hold (a). A loss that depends on how many notes follow is most likely at the **5th** note-on, not the 2nd: at fast
strum the 5th note comes 40 ms after the bass, which also sounds like a pop at the start, and at slow strum (200 ms) the
ear placed it uncertainly. This reads as the 5-note edge seen before (PL02: 7th + bass held, 9th + bass dropped), with
the oldest and lowest voice taken; in step 5 the oldest voice is not the lowest, and whatever was taken there was not
heard. Remedy within slim: keep every bass-mode chord to 4 notes where it can be (rootless 9th = bass + 3rd, 7th, 9th,
the usual rootless voicing; see the chord spec). The DSP-side mechanism stays open (next steps 4 and 5).

## PL03D device run (2026-10-13): the mechanism, measured

Voice log of every synth note-on (`firmware/PL03D/TEST.md`, logs there). Synth 1 on a simple patch (square + saw; #8 / #9
square + square with everything else that costs DSP time at 0). "x thr" = the reading `X:$36 + synth` against stock's
limit `0x14000`.

| Run | x thr at notes 1-5 | 5th note |
|---|---|---|
| #3 rootless 9th, slow strum | 4.10, 3.34, 2.46, 1.73, **0.89** | DSP path, takes **voice 0 = the bass** |
| #4 same, fast strum | 4.14, 3.38, 2.55, 1.81, **0.96** | DSP, voice 0 = the bass |
| #5 bass below 9th, slow strum | 4.15, 3.32, 2.66, 1.75, **0.97** | DSP, voice 0 = **the pad's root C3** (not the bass C2) |
| #6 rootless 9th, strum off | 4.22, 4.06, 3.30, 2.43, 1.69 | ARM, free voice 4: all 5 hold |
| #7 rootless 7th, slow strum | 4.19, 3.43, 2.64, 1.70 | (4 notes) all ARM |
| #8 rootless 9th, slow, simpler patch | 4.94, 4.12, 3.27, 2.59, 1.79 | ARM, free voice 4 |
| #9 as #8 with a Synth 2 note sounding | 5.10, 4.21, 3.39, 2.64, 1.81 | ARM (Synth 2's own reading saturated, 12.80) |

**Settled:**
- `X:$36 + synth` is spare DSP time: each **sounding** voice costs a fixed slice (about 0.8 of the threshold with this
  patch); a voice costs only once it has started, so readings inside a one-burst chord lag (#6: 4.22 then 4.06).
- Below the threshold the DSP picks and takes **voice 0** (the synth's oldest), even with free voices: in a strum that is
  the first note (step 7: the bass; step 5: the pad's root, which is why the bass seemed to survive there).
- Stock's threshold is a **margin**, not the limit: five voices run together without loss when they start in one burst
  (#6; the reading with all five running is about 0.9, still positive).
- The budget is **per synth**: a Synth 2 voice leaves Synth 1's readings unchanged (#9 vs #8).
- The log's `r` / "releasing" label is wrong: held, sounding voices show as `r`; bit 31 of the state word
  (`0x8000FFFF`) marks a voice **allocated but not yet started** (only notes of the same burst show `H`). Read `r` as
  "sounding". Fix the labels in the next diagnostic.

**What the reading means** (stock DSP code at `P:$1C01`, read statically 2026-10-13): at the end of every audio block
the DSP computes, per synth, from that synth's own processing time and its count of processed voices, roughly "spare
time / time per voice": the number of further voices of the current patch that still fit, `0x10000` = one voice. The
logs match (steps of about `0x10000` per sounding voice). Stock's threshold `0x14000` = **1.25 voices**: step 7's 5th
note had 1.11–1.21 voices of room in the three runs and was refused only for stock's quarter-voice margin. A synth
with no processed voice reads the maximum (Synth 2's 12.80 in #9: no per-voice cost to divide by, not more resources).

**Synth 1 vs Synth 2** (user, 2026-10-13, the same patch on both, the same 9th rootless strum): voices that fit at
notes 1 / 3 / 5: Synth 1 6.6 / 5.0 / 2.6, Synth 2 7.1 / 5.0 / 3.0. Close, not identical; earlier runs varied by
0.05–0.2 voices between repeats, so a small systematic difference (e.g. the order the DSP processes the synths in) is
possible but not shown by one run each. The design below uses each synth's own reading, so it does not depend on it.

**Ways to keep the full 9th** (next design): (1) let a chord note that finds a free voice take the ARM path while the
reading is above a floor below stock's threshold (one more voice; evidence: #6); (2) put the bass on Synth 2 (separate
budget); (3) the 4-note rootless 9th as the fallback.

## PL04D device run (2026-10-14)

`firmware/PL04D/TEST.md`. With a simple patch every strummed 5-note chord took free voices on stock's ARM path (5th note
about 3 voices of room): PL04 changes nothing there, and the floor (1.0-1.25 voices) was not exercised; PL03D's square +
saw patch (5th note 1.11) is the one to confirm it with. A heavy patch (density, sync, drive, effects) holds about two
voices: 1.9 voices of room with nothing sounding, about 0.87 with one voice sounding, so every note after the first
takes voice 0 on stock's DSP path, chord or not. The one-tone fallback works as designed there and cannot help; a
"fit-to-room" chord (as many notes as fit, bass or root kept) would be the answer for such patches.

## Next steps

1. ~~Stock test~~ done 2026-10-12: stock drops notes too.
2. ~~Entry-order test~~ done 2026-10-12: order does not decide; the lowest note goes most often.
3. Options for the chord engine (changing the note order is out):
   - fewer notes with bass on (e.g. 9th + bass leaves out the fifth, as in jazz voicings);
   - bass replaces stock's pad note instead of doubling it an octave lower (one voice fewer, but the lowest note is
     still the one at risk);
   - nothing in firmware: document that 5–6-note chords lose notes with heavy patches, as stock steps do.
4. Optional, to know why the lowest: a DSP session (`tools/dsp_session.py`) playing a low and a high note and dumping
   `Y:$122 + $60 v + $E` over a few blocks would show whether the word follows pitch or the envelope.
5. To settle the mechanism on the device: a diagnostic build reporting, per synth note-on, which path `0x080217B4`
   took, the value of `X:$36 + synth` and the voice it chose (through MIDI out, as upstream's diagnostic builds do).
   Decode the `P:$1BB3` flags before choosing a fix. Built as `PL03D` (2026-10-13), run on the device the same day (results above). Answered by `PL04` (one-voice floor for chord notes, 5-note fallback), device test `firmware/PL04D/TEST.md`.

## Gaps in testing

The emulation tests stop at the synth note-on endpoint (`0x0803BD58`) and do not run the DSP, so voice allocation is
not covered anywhere. A DSP session (`tools/dsp_session.py`) could replay a 6-note burst, but it does not model DSP
time, which is what the switch depends on.

## Reproducing the reading

- ARM: `re/app.asm` at the addresses above.
- DSP core 0 program: `tools/dsp_session.dsp_program(stock_image, 0)` (load address 0, `0x2A5E` words), disassembled
  with `ext/bin/dsptool dis core0.bin 0`.
