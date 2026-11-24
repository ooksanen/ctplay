# PL16 — device test plan (drum pages, note repeat)

**What it is:** PL15 with pages for the drum tracks and **note repeat** (spec
`slim/docs/specs/2026-10-25-drums-design.md`):
- **Drum pages.** Shift + Drum 1, 2, 3 or 4 opens that drum's page, as Shift + Synth 1 does for a synth. A drum has one
  page so far: **Repeat**. Holding Shift on it shows the page list (pad 25, blue). With Shift held, the Drum 1–4
  buttons light up like Synth 1 / 2 and MIDI 1 / 2.
- **The Repeat page** (one setting for the whole kit: the page is the same whichever drum opened it):

  | Pads | What |
  |---|---|
  | 1–4 | rate (blue): 1/4 · 1/8 · 1/16 · 1/32 |
  | 5–8 | triplet rate (magenta): 1/4T · 1/8T · 1/16T · 1/32T. One rate across pads 1–8; the lit pad again = no rate |
  | 9–12 | velocity (white): as struck · fade · swell · accent the beat |
  | 15 | unquantized repeats (cyan) |
  | 16 | latch (orange) |
  | 29–32 | drums 1–4: play the drum; with a rate lit, it repeats while you hold the pad |

  Pads 13–14 and 17–28 are dark and do nothing.
- **Repeats** follow the sequencer's grid while it plays, and run from your press at the project's tempo while it is
  stopped. Stock records them like finger hits (Record on, playing).
- **Unquantized repeats** (pad 15): with stock's Rec Quantise on, repeats still record at their exact timing.
- **Saved:** the Repeat settings (new field `repeat`, in the second saved block) and each drum's last page.
- **The CTCtrl link:** its last-sent copy of the settings moved to other memory (nothing to see), and it carries
  `repeat`.

With no drum page used, every PL15 feature plays as before (checked in emulation). PL15 passed on the device
(`firmware/PL15/TEST.md`): this run checks what is new.

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL16.toml` (once PL16 is tagged: from the tag).
   The printed syx sha256 must equal `syx_sha256` in `slim/firmware/PL16/manifest.json` (`c814a490…`). Then
   `../.venv/bin/python -m slimbuild.uploader` (the uploader learns PL16).
1. **Stack headroom gate (SL00D):** Main and UI with at least 2 green pads (≥ 1.5 KB free). Hook stacks against PL15:
   the **LED task 464 B** (PL15 448 B: the link's state is 87 B now); **new: the recorders' quantise refresh 128 B**
   (unquantized repeats). Main (`main_ms`, the repeats' hits) 416 B, a page pad press 468 B, a page pad release
   444 B: the same as PL15.
2. **Back up the SD card**: the test records patterns and saves projects. Use a pack you can lose. Way back: Scales +
   Preset + Note at power-on, send the stock `.syx` (or PL15).
3. **For section A:** a MIDI monitor web page open in Chrome on the computer, listening to the Circuit Tracks' USB
   MIDI port, and stock's MIDI **Tx Note on** (Setup view). Close the uploader tab once the flash is done: only one
   program can use the port.
4. Flash `slim/build/PL16/circuittracks-4486-PL16.syx` with `slim/build/ct_uploader.html`. **Do not power off before
   section A is done.**
5. **A new empty project** (in the Projects view, tap an empty slot) at the start of each section that says so. It
   starts with every CTPlay setting off: on the Repeat page no rate, velocity as struck, unquantized repeats off,
   latch off. Tempo 120 BPM: one beat = half a second.
6. **The click** (stock's metronome): hold Shift and look at Clear. **Green = the click only.** If it is not green,
   press Shift + Clear until it is (red off, green click, magenta count-in, cyan both). A count-in (magenta, cyan)
   would delay every Play by a bar. The click stays on across project changes, as in stock.
7. Colours: bright = selected, dim = not selected, dark = nothing there. "Pads 29–32 in the drum colours" = orange,
   yellow, violet, cyan (the colours stock gives them in the expanded drum view).
8. **Stock's fixed velocity must be off** from section C on. With it on, every pad hit is equally loud, and the
   velocity steps (section E) cannot work. Stock's **Shift + Velocity** turns it on and off. It is a Setup setting: it
   stays the same in every project. Step 6c checks it by ear and tells you how to turn it off.

## Steps
### A. Straight after flashing: chord pads (`followups.md`, "Chord pads dark right after flashing")
Start: PL16 just installed, the Circuit restarted, **no power cycle yet**. The MIDI monitor is open.

| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Make a new empty project. Leave the Note view's layout as it comes up. Note which layout it is (stock's default scale rows, or your keyboard layout) | The Synth 1 Note view | |
| 1b | Shift + Synth 1 (the Chords page). Press pad 2 (triad). Press the Note button | Pad 2 was bright green. Now the Note view | |
| 1c | Press the pad that plays C, and hold it | **Sound:** a chord, C E♭ G (the new project is in C minor). **Pads:** the pressed pad lights; the pads of E♭ and G light in the same colour where the layout has them. Write down which pads light, or "none" | |
| 1d | Look at the MIDI monitor | **Three note-ons on channel 1** (C, E♭, G), then three note-offs when you let go | |
| 1e | If the layout was not your keyboard layout: switch to it now, as you did in PL15's run. Play C once more and hold it | The same chord. Write down which pads light, and the notes on the monitor | |
| 1f | Play three other pads, one at a time | Each plays a triad; its other notes' pads light. Write down if the first presses lit nothing and later ones did | |

### B. Opening and closing the drum pages
Start: the project of section A, sequencer stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 2 | Press Synth 1 (its Note view). Then Shift + Drum 1 | Drum 1 is selected and **the Repeat page** opens. Pads 1–4 dim blue, 5–8 dim magenta. Pad 9 bright white, 10–12 dim white. Pads 13–14 dark. Pad 15 dim cyan, pad 16 dim orange. Pads 17–28 dark. Pads 29–32 in the drum colours | |
| 2b | Look at ▲ and ▼ | Both dark (there is no other drum page yet) | |
| 2c | Press ▼, then ▲ | Nothing changes | |
| 3 | Hold Shift (keep holding it) | The page list: **pad 25 bright blue**, every other pad dark. ▲ ▼ dark | |
| 3b | Still holding Shift, look at the eight track buttons | **All eight are lit, Drum 1–4 in the same colour as Synth 1.** (With Shift held, stock leaves the Drum buttons dark. CTPlay lights them as it lights Synth 1.) | |
| 3c | Still holding Shift, tap pads 26, 27 and 32. Release Shift | Nothing changes: the Repeat page as in step 2 | |
| 4 | Press the Note button | The page closes: stock's expanded drum view. Pads 29–32 in the drum colours: **the same colours as the Repeat page's pads 29–32** | |
| 4b | Shift + Drum 1 | The Repeat page opens over it, as in step 2 | |
| 4c | Press Drum 1 (no Shift) | The page closes. Stock's own Drum 1 view, as the button gives it in stock | |
| 5 | Press Mixer. Then Shift + Drum 3 | Drum 3's Repeat page: **the same as step 2** (one setting for the kit) | |
| 5b | Press Mixer | The page closes: stock's Mixer | |
| 5c | Press FX. Then Shift + Drum 2 | Drum 2's Repeat page | |
| 5d | Shift + Drum 4 | Drum 4 is selected; its Repeat page | |
| 5e | Shift + Synth 1 | **Synth 1's Chords page**: pad 2 bright green (the triad from step 1b) | |
| 5f | Shift + Drum 1, then press FX | The Repeat page, then the page closes: stock's FX view | |
| 5g | Shift + Drum 1, then press Preset | The Repeat page, then the page closes: stock's Preset view | |

### C. Playing and the rates, stopped
Start: Shift + Drum 1 (the Repeat page), sequencer stopped, no rate lit.

| # | Do | Expect | Result |
|---|---|---|---|
| 6 | Tap pad 29 | Drum 1 sounds once. Pad 29 lights white while you hold it, then orange again | |
| 6b | Tap pads 30, 31, 32 | Drums 2, 3, 4, once each. Each pad white while held | |
| 6c | **Fixed velocity check.** Tap pad 29 softly, then hard | Soft, then loud: the pads are velocity-sensitive. **If both taps sound the same, stock's fixed velocity is on.** Then hold Shift and press Velocity once (the Repeat page stays open), and tap softly and hard again: now soft, then loud. Write down whether it was on. Leave it off for the rest of the run | Fixed velocity was on |
| 7 | Press pad 3 (1/16) | Pad 3 bright blue. Nothing plays | |
| 7b | Hold pad 29 for about two seconds, then let go | Drum 1 at once, then **4 hits a beat** (8 a second), evenly. Pad 29 white while you hold it. The repeats stop when you let go | |
| 7c | Press pad 3 again | Pads 1–8 all dim: no rate | |
| 7d | Hold pad 29 for two seconds | **One hit only** | |
| 8 | **Every rate, stopped** (one beat = half a second). Press pad 1 (1/4), hold pad 29 for two seconds | Pad 1 bright blue, the other rate pads dim. **1 hit a beat** (2 a second) | |
| 8b | Press pad 2 (1/8), hold pad 29 for two seconds | Pad 2 bright blue. **2 hits a beat** | |
| 8c | Press pad 4 (1/32), hold pad 29 for two seconds | Pad 4 bright blue. **8 hits a beat** | |
| 8d | Press pad 5 (1/4T), hold pad 29 for two seconds | Pad 5 bright magenta. **3 hits in two beats** | |
| 8e | Press pad 6 (1/8T), hold pad 29 for two seconds | Pad 6 bright magenta. **3 hits a beat** | |
| 8f | Press pad 7 (1/16T), hold pad 29 for two seconds | Pad 7 bright magenta. **6 hits a beat** | |
| 8g | Press pad 8 (1/32T), hold pad 29 for two seconds | Pad 8 bright magenta. **12 hits a beat (very fast)** | |
| 9 | **A rate change while you hold.** Press pad 2 (1/8). Hold pad 29. While holding it, press pad 4 (1/32), then pad 2 again | The repeats go from 2 a beat to 8 a beat, then back to 2. **No restart and no extra hit** at either change | |
| 10 | **Two drums.** Hold pad 29, then also hold pad 31 | Both repeat at 1/8, each from its own press. Let go of both: both stop | |

### D. Playing with the sequencer
Start: the Repeat page; press pad 3 (1/16). The click on (step 6 of Before you start). Record off. Press Play: the
pattern is empty, you hear the click.

| # | Do | Expect | Result |
|---|---|---|---|
| 11 | Hold pad 29 for two bars, pressing it **between two clicks** | The first hit at once. Then 4 hits a beat, **in time with the click** (on the sequencer's steps), not timed from your press | |
| 11b | Press pad 1 (1/4) | Pad 1 bright blue, pad 3 dim | |
| 11c | Tap pad 29 briefly, many times, between the clicks (also just before a click) | Each short tap sounds **once**. No quick double hit (a flam) after a tap, not even just before a click: a click less than half a beat after your press is skipped | |
| 12 | **Every rate, playing.** Press pad 1 (1/4), hold pad 29 for a bar | Your first hit at once. **After it, a hit on every click.** If you pressed less than half a beat before a click, that click has no hit (it would be a double hit) | |
| 12b | Press pad 2 (1/8), hold pad 29 for a bar | **2 hits per click**, locked to the click | |
| 12c | Press pad 4 (1/32), hold pad 29 for a bar | **8 hits per click**, locked to the click | |
| 12d | Press pad 5 (1/4T), hold pad 29 for a bar | **3 hits over two clicks**, locked to the click | |
| 12e | Press pad 6 (1/8T), hold pad 29 for a bar | **3 hits per click**, locked to the click | |
| 12f | Press pad 7 (1/16T), hold pad 29 for a bar | **6 hits per click**, locked to the click | |
| 12g | Press pad 8 (1/32T), hold pad 29 for a bar | **12 hits per click**, locked to the click | |
| 13 | **Swing.** Press pad 3 (1/16). In stock's Tempo/Swing view set the swing to about 70 %. Shift + Drum 1. Hold pad 29 for a bar | The repeats swing: every second hit comes late, as the sequencer's steps do | |
| 13b | Stop (Play). Hold pad 29 for two seconds | Repeats, stopped. Write down whether they swing too | Swung |
| 13c | Set the swing back to 50 % | | |

### E. Velocity shapes (by ear)
Start: Shift + Drum 1 (the Repeat page), rate 1/16 (pad 3), sequencer stopped (step 13b). Drum 1 with the sound
the new project gave it.

| # | Do | Expect | Result |
|---|---|---|---|
| 14 | Pad 9 (as struck) is bright. Hold pad 29, pressed hard, for two seconds | Every hit equally loud | |
| 14b | Press pad 10 (fade). Hold pad 29 hard for two seconds | Pad 10 bright white, 9 dim. **Loud first, softer over one beat** (4 hits), then it stays soft | |
| 14c | Press pad 11 (swell). Hold pad 29 hard for two seconds | **Soft first, louder over one beat**, then it stays loud | |
| 14d | Press pad 12 (accent the beat). Hold pad 29 hard for two seconds | Every 4th hit loud (the first one too), the hits between softer: stopped, the beats count from your press | |
| 14e | Press Play (click on). Hold pad 29 for a bar, pressed between two clicks | The hits **on the clicks are loud**, the others softer. Your first hit is soft (off the beat). Stop | |
| 15 | **Fade on a long sample.** Press Drum 4 (its view); on its sample pads pick a long sound (a cymbal or a long tom). Shift + Drum 4. Press pad 10 (fade), pad 4 (1/32). Hold pad 32 hard for two seconds | Write down what you hear. Expected: a fading roll; it may thin out (a hit softer than the sound still ringing does not start it again: the drum engine's rule, not CTPlay's) | Fading roll |
| 15b | Press pad 11 (swell). Hold pad 32 for two seconds | A rising roll, every hit heard | |
| 15c | Press pad 9 (as struck), pad 3 (1/16) | Pad 9 and pad 3 bright | |

### F. Latch, and a lost release
Start: the Repeat page, rate 1/16, velocity as struck, sequencer stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 16 | Press pad 16 (latch) | Pad 16 bright orange | |
| 16b | Tap pad 29 | Drum 1 repeats and **keeps repeating** after you let go. **Pad 29 pulses white** | |
| 16c | Tap pad 31 | Drum 3 repeats too; pad 31 pulses | |
| 16d | Tap pad 29 | Drum 1 stops; pad 29 orange again. Drum 3 goes on | |
| 16e | Press pad 3 (the lit rate: now no rate) | Pads 1–8 all dim. **Drum 3 stops at once**: turning the rate off stops the latched drums. Pad 31 violet again. Pad 16 still bright | |
| 16f | Tap pad 29 a few times (latch on, no rate) | Each tap plays drum 1 **once**, as with latch off. Pad 29 white while you hold it, then orange. It never pulses | |
| 16g | Press pad 3 (1/16). Tap pad 31 | Pad 3 bright blue. Drum 3 repeats, latched; pad 31 pulses | |
| 17 | Press the Note button (the page closes) | Stock's expanded drum view. **Drum 3 keeps repeating** | |
| 17b | Shift + Drum 1 | The Repeat page: pad 31 still pulsing | |
| 17c | Press pad 16 (latch off) | Pad 16 dim. **Drum 3 stops**; pad 31 violet again | |
| 17d | **Latched drums while you play a synth.** Press pad 8 (1/32T), then pad 16 (latch on). Tap pads 29, 30, 31 and 32 | All four drums repeat, latched, 12 hits a beat each. Pads 29–32 pulse white | |
| 17e | Press Play (Record off; the click on) | The four rolls lock to the click and keep time | |
| 17f | Press Synth 1 (its Note view; the page closes). For a bar or two, play chords: press pads one at a time, each for a beat or so | **The drums keep time.** Each chord sounds whole (a triad: step 1b): no note drops out. Nothing keeps sounding after you let go. Write down any dropout | |
| 17g | Shift + Synth 1 (the Chords page). Press ▼ (the Arp page), then pad 2 (up). Press Note (the Note view). Hold a pad for a bar, then let go | An arpeggio of the chord, in time with the click and the drums. It stops when you let go | |
| 17h | Shift + Synth 1 (the Arp page, the last one used). Press pad 1 (pattern off). Press Play (stop) | The arpeggio is off. The four drums go on repeating, stopped. Write down whether anything hung, stuck or lagged in steps 17e–17g | |
| 17i | Shift + Drum 1 (the Repeat page: pads 29–32 pulsing). Press pad 16 (latch off) | **All four drums stop at once.** Pad 16 dim. Pads 29–32 in the drum colours | |
| 17j | Press pad 3 (1/16) | Pad 3 bright blue | |
| 18 | **A lost release.** Hold pad 29 (it repeats). While holding it, press the Note button. Then let go of pad 29 | Drum 1 **stops as soon as you press Note**, not when you let go. Nothing keeps sounding | |
| 18b | Shift + Drum 1 | The Repeat page; pad 29 orange (not white) | |

### G. Recording repeats (Rec Quantise and unquantized repeats)
Start: **a new empty project.** Shift + Drum 1 (the Repeat page). Press pad 4 (1/32). Hold Shift and look at Record:
bright = stock's Rec Quantise on, dim = off; **do not press Record while looking.** Each step records a different
drum, so the takes do not mix. "Two beats" = two clicks: the click on (step 6 of Before you start).

| # | Do | Expect | Result |
|---|---|---|---|
| 19 | If Record is bright with Shift: press Shift + Record once | With Shift held, Record dim: Rec Quantise off | |
| 19b | Press Record, then Play. Hold pad 29 for two beats. Let go | Recording, as stock | |
| 19c | Listen to the loop | **Drum 1 plays back as fast as you played it** (1/32: 8 hits a beat) | |
| 20 | Shift + Record (Rec Quantise on: Record bright with Shift). Hold pad 30 for two beats | Drum 2 repeats at 1/32 while you hold it | |
| 20b | Listen to the loop | **Drum 2 plays back at half the speed** (4 hits a beat): Rec Quantise put one hit on each step | |
| 21 | Press pad 15 (unquantized repeats) | Pad 15 bright cyan | |
| 21b | Hold pad 31 for two beats. Listen to the loop | **Drum 3 plays back as fast as you played it** (8 a beat), although Rec Quantise is on | |
| 21c | Hold Shift and look at Record | **Still bright**: CTPlay did not change Rec Quantise | |
| 22 | Press pad 15 (unquantized repeats off). Hold pad 32 for two beats. Listen | **Drum 4 at half the speed** (4 a beat): after the repeats, Rec Quantise works as before | |
| 23 | Press Play (stop). Press Drum 1, then Drum 2, Drum 3, Drum 4: each its stock drum view, the steps on the top rows | Each drum has hits on about 8 steps in a row (the two beats you held it). No other steps | |

### H. Rec Quantise changed while a repeat runs
Start: **a new empty project.** Shift + Drum 1. Pad 4 (1/32), **pad 15 on (unquantized repeats)**, pad 16 on
(latch). Rec Quantise **on**: hold Shift, Record must be bright (if it is dim, press Shift + Record once). The click
on (step 6 of Before you start).

| # | Do | Expect | Result |
|---|---|---|---|
| 24 | Press Record, then Play. Tap pad 29 | Drum 1 repeats (latched) and records | |
| 24b | While it repeats, press Shift + Record | With Shift held, **Record dims**: Rec Quantise off, as stock shows it | |
| 24c | Tap pad 29 (drum 1 stops). Press pad 15 (unquantized repeats off). Press pad 16 (latch off) | Pads 15 and 16 dim | |
| 25 | Hold pad 30 for two beats. Listen to the loop | Drum 1's roll recorded in step 24 plays in the loop too: **listen for drum 2.** **Drum 2 as fast as you played it** (8 a beat): Rec Quantise is off, as you set it during the repeat | |
| 26 | Shift + Record (Record bright with Shift: on again). Hold pad 31 for two beats. Listen | Drum 1's roll plays too: **listen for drum 3.** **Drum 3 at half the speed** (4 a beat) | |
| 26b | Press the Note button (stock's expanded view). Tap pad 32 a few times, off the click. Listen to the loop | Drum 4 records as stock does with Rec Quantise on: on playback each hit sits on a step (a 16th), not exactly where you tapped | |
| 26c | Stop. Press Record (Record off) | | |

### I. Play and Stop while a drum repeats
Start: **a new empty project** (nothing recorded, so only the held drum sounds). Shift + Drum 1 (the Repeat page).
Press pad 2 (1/8): pad 2 bright blue. Velocity as struck (pad 9 bright), latch off (pad 16 dim), unquantized repeats
off (pad 15 dim). Record off (not lit). The click on (step 6 of Before you start). Sequencer stopped.

| # | Do | Expect | Result |
|---|---|---|---|
| 27 | Hold pad 29 (2 hits a beat, from your press). Keep holding it. Press Play with the other hand | **No two hits close together** (no flam) when Play starts. Within a beat the repeats are on the click. One longer gap when Play starts (up to 1.5 repeats) is expected | |
| 27b | Still holding pad 29, press Play (stop) | The repeats go on evenly, at the same speed: no double hit, no gap | |
| 27c | Press Play again, then stop again, still holding | The same: no flam at Play (one longer gap, up to 1.5 repeats, is expected), no gap at Stop. Let go: drum 1 stops | |
| 28 | Press pad 4 (1/32). Hold pad 29 and press Play | No flam; the repeats lock to the click | |
| 28b | Stop. Let go | | |

### J. Save, load, power cycle
Start: **a new empty project.** Shift + Drum 1.

| # | Do | Expect | Result |
|---|---|---|---|
| 29 | Press pad 3 (1/16), pad 10 (fade), pad 15 (unquantized repeats), pad 16 (latch) | Pads 3, 10, 15, 16 bright | |
| 29b | Tap pad 30 | Drum 2 repeats, latched; pad 30 pulses | |
| 29c | Save the project: Save, then Save again | It saves as stock does. **Write down whether drum 2 keeps repeating** after the save | Latch holds |
| 30 | Load the same project again (Projects view, tap its slot) | It loads. **Drum 2 stops**: a load stops every repeat | |
| 30b | Shift + Drum 1 | The Repeat page: **pads 3, 10, 15, 16 bright** (saved). Pad 30 yellow, not pulsing | |
| 31 | Power off and on. Load the project | It loads as stock does | |
| 31b | Shift + Drum 3 | The Repeat page: pads 3, 10, 15, 16 bright | |
| 31c | Tap pad 29 (latch is on), listen for two seconds, tap it again | 1/16, fading over a beat; the second tap stops it | |
| 32 | (If you kept a project saved on PL15.) Load it. Shift + Drum 1 | The Repeat page with the defaults: no rate, pad 9 bright, 15 and 16 dim. Its chords as saved (Shift + Synth 1) | |

### K. CTCtrl and the link
Start: the project from step 29 loaded (load it again if you did step 32), the Repeat page open (Shift + Drum 1):
1/16, fade, unquantized repeats, latch. No drum repeating.

| # | Do | Expect | Result |
|---|---|---|---|
| 33 | Open `slim/pages/ctplay_link.html`, connect | "Connected: PL16, protocol 1, layout 1, **87 B, 13 fields**." | |
| 33b | Read | A new row **`repeat`**, offset 81, two bytes: **`D3 00`** (1/16, fade, latch, unquantized repeats). No row for the drums' pages | |
| 33c | Write offset 81, bytes `45` (1/4T, as struck, latch on, unquantized off) | One `state` line. **At once** on the Circuit: pad 5 bright magenta, pad 9 bright white, pad 15 dim, pad 16 bright | |
| 33d | Tap pad 29 | Drum 1 repeats at 1/4T, latched; pad 29 pulses | |
| 33e | Write offset 81, bytes `05` (latch off) | **Drum 1 stops**, pad 16 dim: latch off from the link stops latched drums, as the pad does | |
| 33f | Write offset 81, bytes `45` (latch on again). Tap pad 29 | Pad 16 bright. Drum 1 repeats at 1/4T, latched; pad 29 pulses | |
| 33g | Write offset 81, bytes `40` (no rate, latch on) | **Drum 1 stops**. Pads 1–8 dim, pad 16 bright: no rate from the link stops latched drums, as the pad does | |
| 33h | Write offset 81, bytes `05` (1/4T, latch off) | Pad 5 bright magenta, pad 16 dim | |
| 33i | **A refused write.** Write offset 81, bytes `09` (rate 9: no pad makes it) | One `state` line, unchanged: the write is refused. On the Circuit nothing changes (pad 5 still bright) | |
| 33j | Write offset 82, bytes `01` (the spare byte) | Refused the same way | |
| 34 | Close the page. Open CTCtrl (a version with the Repeat tab), connect. Select Drum 1, the Repeat tab | The rate shows **1/4T**, velocity as struck, latch off, unquantized repeats off. No error | |
| 34b | In CTCtrl, set the rate to 1/16 | At once on the Circuit: pad 3 bright blue, pad 5 dim | |
| 34c | On the Circuit, press pad 11 (swell) | CTCtrl shows velocity Swell | |

## Results
2026-10-25, PL16 (`c814a490…`): **passed.** Every section A–K all green.
- **Section A (chord pads straight after flashing):** the chord pads lit from the first press and the notes were
  right. PL15's dark pads were not seen again (`followups.md`, "Chord pads dark right after flashing").
- **Answers the plan asked for:**
  - Step 6c: stock's fixed velocity was on, and was turned off for the run.
  - Step 13b: stopped, the repeats swing too.
  - Step 15: a fading roll.
  - Step 29c: a latched drum keeps repeating through a save.
- **Notes:**
  - **Section E, fade:** the roll stays fairly loud at its end. That is the design: it settles at a quarter of the
    press's velocity (the spec, "Velocity"). A deeper fade is a candidate (`followups.md`, PL16 device run).
  - **Section F:** checked with a synth at 1/16. At 120 BPM, 1/32T is too fast to tell by ear whether it is on the
    beat.
  - **Section I, Play while holding:** sometimes one gap was a little shorter than the rest, not a flam (two hits
    close together). Expected: at Play the first hit on the beat may come as soon as half a repeat after the last
    stopped hit (`repeat.c`, `on_start`). The guide's "no two hits close together" holds.
