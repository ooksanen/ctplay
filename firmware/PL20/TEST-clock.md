# PL20 — external MIDI clock (device test, written 2026-11-10)

**Why:** CTPlay's timed features have never run with an external MIDI clock (PL06–PL20 all left it open). Under the
Circuit's own clock, the sequencer's ticks run in the Main task's 1 ms service and a start's first tick comes from
the Play handler. Under an external clock the ticks come from wherever the incoming clock is handled, and a MIDI
**Start** may not go through the Play handler. This run finds out what CTPlay does then. The beta adds no features,
so a result here holds for the beta too; anything that fails gets fixed in the beta build.

**Some rows have no known answer** ("Record what happens"): write down what you hear. Every other row says what
should happen if CTPlay follows the external clock as it follows the internal one.

**Time:** about **30 minutes** (setup 10 min, 32 rows at about 30 s each).

## Before you start
1. PL20 or the beta build (PL21) installed. On PL21 every row reads the same: nothing it tests changed there (a drum
   in a new project still opens on its Repeat page, now on pad 26 of the drum page list).
2. **A DAW (or any app) that sends MIDI clock** with Start and Stop to the Circuit Tracks' USB MIDI port. Set its
   tempo to **90 BPM** and turn on its click, so you can hear its beat. Always start it **from bar 1** (it then sends
   Start; starting mid-song sends Continue instead, tested once in row 28).
3. **Close CTCtrl's and the uploader's tabs.** Chrome keeps a tab's MIDI port until the tab is closed, and on Windows a
   MIDI port has one user at a time, so the DAW may not get it.
4. On the Circuit: a **new empty project** (tempo 120: different from the DAW's 90, so you can tell which clock
   plays). In stock's Setup view, turn **Clock Rx on** (Novation's user guide, "Setup view").
5. A short patch on Synth 1 (a pluck); Drum 1 a kick, Drum 2 a snare or a clap.

## Steps

### K. The sequencer follows the DAW (stock; the premise)
| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Press Drum 1. Tap step pads 1, 5, 9 and 13 | Four step pads lit | |
| 2 | Start the DAW (from bar 1) | The kick plays **with the DAW's click, at 90 BPM**: the Circuit follows the DAW | |
| 3 | Stop the DAW | The kick stops | |

### L. Arpeggiator (PL06, PL07)
| # | Do | Expect | Result |
|---|---|---|---|
| 4 | Shift + Synth 1: the Chords page. Pad 2 (triad). Hold Shift, tap pad 26: the Arp page. Pad 2 (up), pad 11 (1/16), pad 16 (latch) | Pads 2, 11 and 16 bright | |
| 5 | Start the DAW. Press Synth 1 (its Note view), tap a C pad once | C E♭ G, C E♭ G… in sixteenths, **four arp notes per kick**, locked to the DAW's click. It goes on after you let go | |
| 6 | Change the DAW's tempo to 110 while it plays | The arp and the kick speed up together, still four notes per kick | |
| 7 | Shift + Synth 1 (the Arp page). Tap pad 21 twice (gate 3/6 → 2/6 → 1/6) | The notes get shorter with each press; still in time | |
| 8 | Stop the DAW | Record what happens: the arp keeps going (at what tempo: the DAW's last, or the project's 120?) or stops | |
| 9 | Start the DAW again | The arp is back on the DAW's grid, in time with the kick | |
| 10 | Press Record on the Circuit. Let the arp play for one bar. Press Record again (off). Shift + Synth 1, pad 16 (latch off): the arp stops | Record lights while recording | |
| 10b | Listen for 2 bars | Synth 1 plays back the recorded sixteenths, in time with the kick | |
| 11 | Stop the DAW | Everything stops. No note keeps sounding | |

### M. Note repeat (PL16)
| # | Do | Expect | Result |
|---|---|---|---|
| 12 | Shift + Drum 2: the Repeat page. Pad 3 (1/16) | Pad 3 bright | |
| 13 | Start the DAW. Hold pad 30 (drum 2) for a bar, let go | Drum 2 repeats in sixteenths, **four per kick**, in time with the DAW. It stops when you let go | |
| 14 | Pad 7 (1/16T). Hold pad 30 for a beat | Triplets: six per kick | |
| 15 | Stop the DAW. Hold pad 30 for a second | Record what happens: repeats at what tempo (the DAW's last or 120), or one hit | |
| 16 | Pad 3 again (1/16). Pad 16 (latch). Start the DAW, tap pad 30 | Drum 2 keeps repeating after you let go, in time | |
| 16b | Stop the DAW. Tap pad 30 | Record whether the latched drum stopped with the DAW. After the tap it is off | |

### N. Count-in (PL08)
| # | Do | Expect | Result |
|---|---|---|---|
| 17 | Hold Shift, press Clear until Clear is magenta (count-in), let go | Clear magenta with Shift | |
| 18 | Press Record (armed, the DAW stopped). Start the DAW | **No count-in**: the sequencer starts with the DAW at once and records (a transport started from outside cancels the count). No clicks from the Circuit | |
| 19 | Stop the DAW. Press Record (off). With Record armed again and the DAW stopped, press **Play** on the Circuit | Record what happens: clicks, nothing, or a start. Then press Play or Record to end it. The Circuit must not hang | |
| 20 | Shift + Clear until Clear is red (off) | Clear red with Shift | |

### O. Trig conditions (PL20)
Drum 1's kick still plays steps 1, 5, 9 and 13.

| # | Do | Expect | Result |
|---|---|---|---|
| 21 | Press Drum 1. Shift + Pattern Settings: the probability view. Tap step pad 9. **Hold** pad 26 about a second, let go. Tap pad 26. Tap pad 25 | Row 4: pad 25 dim, pad 26 bright cyan (pass 2 of 2) | |
| 22 | Start the DAW. Listen for **3 bars**, then stop it | Beat 3 **only in bar 2**: bars 1 and 3 have no beat 3 | |
| 23 | Start the DAW again (from bar 1). Listen for 2 bars, stop | **Bar 1 has no beat 3 again**, bar 2 has: the DAW's Start starts the count over (if the count had gone on, bar 1 would be pass 4 and play beat 3) | |
| 24 | Press Drum 2. Tap step pads 1 and 9 (two hits). Shift + Pattern Settings, tap step pad 1. Hold Shift, tap pad 26 (NOT FIRST), let go of Shift | Row 4 with Shift: pad 26 bright green. Without Shift: all 8 dim green | |
| 25 | Start the DAW. Listen for 3 bars, stop | Drum 2 on step 1 is **silent in bar 1** and plays in bars 2 and 3; its step 9 plays every bar. **This checks the start's first tick under an external Start** | |
| 26 | Start the DAW again, 2 bars, stop | Again silent on bar 1's step 1 only | |
| 27 | Press Drum 2 (the drum view), then Note: the expanded view. Start the DAW. Hold pad 22 (FILL for drum 2) for a bar | While held: nothing changes for Drum 2 (it has no FILL condition), nothing hangs. Let go, stop the DAW | |
| 28 | In the DAW, start from **bar 3** (it sends Continue, maybe a song position). Listen for 2 bars, stop | Record what happens: the Circuit starts or not, where in its pattern, and whether bar 1's rules (NOT FIRST silent, beat 3 on pass 2) look started over or continued | |

### P. Played strum (PL19, PL20)
Synth 2, whose pattern is still empty (Synth 1's holds the arp notes recorded in row 10). Choose a pluck on Synth 2.

| # | Do | Expect | Result |
|---|---|---|---|
| 29 | Shift + Synth 2: the Chords page. Pad 2 (triad), pad 28 (slow). Hold Shift, tap pad 32: the Keys page. Pad 2 (chords in step entry, bright green), pad 3 (Played, white). Press Synth 2 (its Note view). Hold step pad 1, press a C pad, let go of both | You hear C E♭ G while you hold. Step pad 1 lit | |
| 30 | Start the DAW. Listen for 2 bars, stop | Each bar, step 1 strums up slowly (80 ms between notes; the gap is in milliseconds, not the clock's ticks), all three notes ending together | |

## Results
K: All tests passed  
L: L8 arp continues at Circuit project speed (120bpm). All tests passed.  
M: M15 switches to project tempo (120bpm). M16b latched drum didn't stop with DAW, tap on 30 stopped it. All tests passed.  
N: N19 Circuit stops and disarms Rec on DAW stop. On recording start on Circuit, a count-in, recording starts (at 120bpm), stops as usual, no hang. All tests passed.  
O: O28 starts from daw start position, bar 3, with NOT FIRST rule starting over from there. Picks up when the DAW 4 bar loop starts over and beat 1 is not played. All tests passed(?).
P: All tests passed  