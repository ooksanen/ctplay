# PL04D — device test plan (chord voice room, with the voice log)

**What it is:** PL04 plus the voice log. PL04 = PL03 + **chord voice room** (spec
`slim/docs/specs/2026-10-13-chord-voice-room-design.md`):
- a chord note takes a free voice when one more voice of the patch fits (stock asks for 1.25), so a strummed 5-note
  chord keeps its first note (the bass in rootless mode, the root in bass-below mode);
- a strummed 5-note chord that would still not fit leaves out its **5th** (rootless 9th: bass + 3rd, 7th, 9th), else its
  **9th** (bass-below 9th: root, bass, 3rd, 7th), instead of losing the bass;
- the strum-off LED is steady dim white.
Stock's own pads and the sequencer keep stock's rule. Writes nothing to flash or the SD card.

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL04D.toml`: the printed syx sha256 must equal
   `syx_sha256` in `slim/firmware/PL04D/manifest.json`.
1. **Stack headroom gate (SL00D):** as for PL03D: Main (column 4) and UI (column 5) with at least **2 green pads**. A pad
   press now runs 196 B deep in slim (`hook_stack.pad_note_on`; PL03 176 B).
2. **Back up the SD card.** Way back: power on holding **Scales + Preset + Note**, send the stock `.syx` (or PL03),
   confirm with **Play**.
3. Flash `slim/build/PL04D/circuittracks-4486-PL04D.syx` with `slim/build/ct_uploader.html`; close the uploader, open
   `slim/pages/voice_log.html`, **Allow MIDI access**. After each step: **Read**, **Copy as text**, paste with the step
   number, **Clear**. In the log `r` = sounding, `H` = starting; `ARM (floor)` = CTPlay let a chord note take a free voice.
4. Synth 1 on the PL03D simple patch (square + square, the rest at 0) for steps 1-5; a **heavy** patch (both
   oscillators, noise, filter and effects up) for steps 6-8; check it is **Poly** after every power cycle.

## Steps
| # | Do | Expected | Result |
|---|---|---|---|
| 1 | Synth 1 Note view, hold Shift, strum off | The 1-16/17-32 LED steady dim white (no pulse) | OK |
| 2 | PL03 step 7: 9th, rootless over bass (white), slow strum, hold | All 5 notes; **the bass keeps sounding**; the 5th row `ARM (floor)` (or ARM), no `DSP` row | Done |
| 3 | Same, fast strum | As 2 | Done |
| 4 | PL03 step 5: 9th, bass below (orange), slow strum | All 5; the pad's root and the bass keep sounding | Done |
| 5 | Rootless 9th, strum off | All 5 (as PL03) | Done |
| 6 | Heavy patch: rootless 9th, slow strum | 4 notes (bass, 3rd, 7th, 9th: no 5th); the bass keeps sounding; no `DSP` row taking a sounding voice | Done - I think the bass dropped off, but quite hard to tell |
| 7 | Heavy patch: bass below 9th, slow strum | 4 notes (root, bass, 3rd, 7th) | Done |
| 8 | Heavy patch: 5 notes strum off, then 4 strummed: listen for clicks or crackle | Note anything odd | Done. Really hard to spot anything as the heavy patch is very glitchy and noisy by itself, but didn't notice any obvious difference to playing 2-3 notes by hand. |
| 9 | Stock pads, chords off: hold 5 notes one after another, low to high | As stock (the floor is for chord notes only): a note may drop | Done. No note drops noticed. |

## Results
2026-10-14, PL04D (device). Reading column in `>> 4` units: voices of room = reading / `0x1000`.
- **Simple patch (steps 2-5): pass, but the floor was not exercised.** All notes on the ARM path with free voices; the
  5th note still had room for about 3 voices (first note 6.9 voices), lighter than PL03D's square + saw patch (5th note
  1.11 voices). No `ARM (floor)` row: the case PL04 is for (1.0-1.25 voices) did not occur. **Still to confirm:** step 2
  with PL03D's square + saw patch (expected `ARM (floor)` on the 5th row, the bass held, no clicks).
- **Heavy patch (steps 6-9): the patch holds about two voices.** First note 1.9 voices of room; with one voice sounding
  every further note reads about 0.87, so stock's DSP takes voice 0 (the sounding note) for each: effectively mono after
  the first note, with chord notes and with stock's own pads (step 9) alike. The fallback left out the 5th (step 6) and
  the 9th (step 7) as designed, but one tone fewer cannot help a two-voice patch: the bass was lost (the user heard it).
  Outside what chords can do on this synth; no clicks were distinguishable in the patch's own noise.

#2 Read
ms	seq	synth	note	reading	x threshold	path	voice	took	voices before
0	98	Synth 1	C3 (48)	0x6EB0	5.53	ARM (mode 0)	0	free	------
50	99	Synth 1	E4 (64)	0x61C0	4.89	ARM (mode 0)	1	free	r-----
100	100	Synth 1	G4 (67)	0x4FA0	3.98	ARM (mode 0)	2	free	rr----
150	101	Synth 1	B4 (71)	0x3F90	3.18	ARM (mode 0)	3	free	rrr---
200	102	Synth 1	D5 (74)	0x2FB0	2.38	ARM (mode 0)	4	free	rrrr--
5140	103	Synth 1	E3 (52)	0x6E80	5.53	ARM (mode 0)	0	free	------
5190	104	Synth 1	G4 (67)	0x5D10	4.65	ARM (mode 0)	1	free	r-----
5240	105	Synth 1	B4 (71)	0x4F90	3.98	ARM (mode 0)	2	free	rr----
5290	106	Synth 1	D5 (74)	0x3DB0	3.08	ARM (mode 0)	3	free	rrr---
5340	107	Synth 1	F5 (77)	0x2F10	2.35	ARM (mode 0)	4	free	rrrr--

#3 Read
ms	seq	synth	note	reading	x threshold	path	voice	took	voices before
0	108	Synth 1	C3 (48)	0x6E50	5.52	ARM (mode 0)	0	free	------
10	109	Synth 1	E4 (64)	0x6160	4.87	ARM (mode 0)	1	free	r-----
20	110	Synth 1	G4 (67)	0x50D0	4.04	ARM (mode 0)	2	free	rr----
30	111	Synth 1	B4 (71)	0x3F30	3.16	ARM (mode 0)	3	free	rrr---
40	112	Synth 1	D5 (74)	0x2FB0	2.38	ARM (mode 0)	4	free	rrrr--
2138	113	Synth 1	E3 (52)	0x6F70	5.57	ARM (mode 0)	0	free	------
2148	114	Synth 1	G4 (67)	0x6050	4.82	ARM (mode 0)	1	free	r-----
2158	115	Synth 1	B4 (71)	0x4D00	3.85	ARM (mode 0)	2	free	rr----
2168	116	Synth 1	D5 (74)	0x3EC0	3.14	ARM (mode 0)	3	free	rrr---
2178	117	Synth 1	F5 (77)	0x2E80	2.33	ARM (mode 0)	4	free	rrrr--

#4 Read
ms	seq	synth	note	reading	x threshold	path	voice	took	voices before
0	133	Synth 1	C4 (60)	0x6DE0	5.49	ARM (mode 0)	0	free	------
50	134	Synth 1	C3 (48)	0x5FE0	4.79	ARM (mode 0)	1	free	r-----
100	135	Synth 1	E4 (64)	0x4D70	3.87	ARM (mode 0)	2	free	rr----
150	136	Synth 1	B4 (71)	0x3F10	3.15	ARM (mode 0)	3	free	rrr---
200	137	Synth 1	D5 (74)	0x2E50	2.32	ARM (mode 0)	4	free	rrrr--

#5 Read
ms	seq	synth	note	reading	x threshold	path	voice	took	voices before
0	148	Synth 1	E4 (64)	0x6BB0	5.38	ARM (mode 0)	0	free	------
0	149	Synth 1	G4 (67)	0x6B20	5.36	ARM (mode 0)	1	free	H-----
0	150	Synth 1	B4 (71)	0x5E00	4.70	ARM (mode 0)	2	free	HH----
0	151	Synth 1	D5 (74)	0x4C90	3.83	ARM (mode 0)	3	free	HHH---
0	152	Synth 1	C3 (48)	0x3E40	3.11	ARM (mode 0)	4	free	HHHH--

#6 Read
ms	seq	synth	note	reading	x threshold	path	voice	took	voices before
0	15	Synth 1	C0 (12)	0x1E60	1.52	ARM (mode 0)	0	free	------
50	16	Synth 1	E1 (28)	0xDE0	0.69	DSP	0	sounding	r-----
100	17	Synth 1	B1 (35)	0xDA0	0.68	DSP	0	sounding	r-----
150	18	Synth 1	D2 (38)	0xDE0	0.69	DSP	0	sounding	r-----

#7 Read
ms	seq	synth	note	reading	x threshold	path	voice	took	voices before
0	29	Synth 1	C0 (12)	0x1E50	1.52	ARM (mode 0)	0	free	------
50	30	Synth 1	C-1 (0)	0xDF0	0.70	DSP	0	sounding	r-----
100	31	Synth 1	E0 (16)	0xE70	0.72	DSP	0	sounding	r-----
150	32	Synth 1	B0 (23)	0xDD0	0.69	DSP	0	sounding	r-----

#8 Read - 5 notes, strum off
ms	seq	synth	note	reading	x threshold	path	voice	took	voices before
0	38	Synth 1	E1 (28)	0x1D80	1.48	ARM (mode 0)	0	free	------
0	39	Synth 1	G1 (31)	0x1DC0	1.49	ARM (mode 0)	1	free	H-----
0	40	Synth 1	B1 (35)	0xE50	0.72	DSP	1	starting	HH----
0	41	Synth 1	D2 (38)	0x0	0.00	DSP	0	starting	HH----
0	42	Synth 1	C0 (12)	0x0	0.00	DSP	1	starting	HH----

#8 Read - 4 notes, slow strum
ms	seq	synth	note	reading	x threshold	path	voice	took	voices before
0	43	Synth 1	C0 (12)	0x1D40	1.46	ARM (mode 0)	0	free	------
50	44	Synth 1	E1 (28)	0xE60	0.72	DSP	0	sounding	r-----
100	45	Synth 1	G1 (31)	0xE40	0.71	DSP	0	sounding	r-----
150	46	Synth 1	B1 (35)	0xD90	0.68	DSP	0	sounding	r-----

#9 read
ms	seq	synth	note	reading	x threshold	path	voice	took	voices before
0	62	Synth 1	C0 (12)	0x1E10	1.50	ARM (mode 0)	0	free	------
1302	63	Synth 1	F0 (17)	0xDA0	0.68	DSP	0	sounding	r-----
2493	64	Synth 1	B0 (23)	0xE40	0.71	DSP	0	sounding	r-----
4115	65	Synth 1	F1 (29)	0xE60	0.72	DSP	0	sounding	r-----
5385	66	Synth 1	B1 (35)	0xE50	0.72	DSP	0	sounding	r-----