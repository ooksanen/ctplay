# PL03D — device test plan (voice log)

**What it is:** PL03 (chord engine, strum, bass modes) plus a **voice log**: for each synth note, how stock picked the
voice. Spec `slim/docs/specs/2026-10-13-voice-log-design.md`. Nothing is sent while you play; the page
`slim/pages/voice_log.html` reads the last 12 notes over USB when you press Read. It changes no sound and saves
nothing. Purpose: why PL03 step 7 (rootless 9th, slow strum) loses the bass
(`slim/docs/investigations/2026-10-12-chord-voice-dropouts.md`).

## Before you start
0. **Build:** `cd slim && ../.venv/bin/python -m slimbuild versions/PL03D.toml`: the printed syx sha256 must equal
   `syx_sha256` in `slim/firmware/PL03D/manifest.json`.
1. **Stack headroom gate (SL00D):** as for PL03: on SL00D, **Shift + Drum 3** must show the Main (column 4) and UI
   (column 5) task columns with at least **2 green pads**. PL03D adds 40–48 B inside stock's voice decision
   (`hook_stack.voice_headroom` / `voice_picked`), 112 B for a SysEx request (`sysex_in`) and 8 B to the 1 ms
   heartbeat (`main_ms`: 80 B, PL03 72 B); pad presses are unchanged (176 B).
2. **Back up the SD card.** Way back: power on holding **Scales + Preset + Note**, send the stock `.syx` (or PL03),
   confirm with **Play**. PL03D hooks stock's incoming SysEx; the bootloader's own update path is separate.
3. Uploader: `cd slim && ../.venv/bin/python -m slimbuild.uploader` → `slim/build/ct_uploader.html`; flash
   `slim/build/PL03D/circuittracks-4486-PL03D.syx`.
4. Synth 1 on a **Poly** patch; note which patch (name / number) for each run.

## Reading the log
Open `slim/pages/voice_log.html` in Chrome or Edge (close the uploader first: one page at a time can own the port),
press **Allow MIDI access** (it should say "Connected (port names): voice log v1, 0 of 12 records stored"; if it says "No reply on …", note the port names it shows). After each step: **Read**,
**Copy as text**, paste it into the conversation with the step number, then **Clear**.

Columns: `reading` = stock's spare-time value, `x threshold` = that value against stock's limit (below 1.00 the DSP
picks the voice and takes a **sounding** one), `path` = ARM or DSP, `took` = what the chosen voice was doing (`free`,
`releasing` = a fading voice cut short, as stock does routinely, `HELD` = a note you still hold), `voices before` =
the synth's 6 voices just before (`-` free, `r` releasing, `H` held).

## Steps
| # | Do | Paste the log | Result |
|---|---|---|---|
| 1 | Connect the page, then Read with nothing played | Says 0 records | OK |
| 2 | One pad, chords off, release | 1 row, ARM | OK |
| 3 | PL03 step 7: 9th, rootless over bass (white), slow strum; hold until all 5 notes, listen for the bass | 5 rows | Done, result below |
| 4 | Same with fast strum | 5 rows | Done |
| 5 | PL03 step 5: 9th, bass below (orange), slow strum | 5 rows | Done |
| 6 | Step 3 again, **strum off** (the bass held in PL03 check 1a) | 5 rows | Done |
| 7 | Rootless **7th** (Shift + pad 27), slow strum (held in check 1b) | 4 rows | Done |
| 8 | Step 3 with a **simple** patch (e.g. a single-oscillator sine / square) | 5 rows | Done |
| 9 | Put a long held note on **Synth 2** in a pattern, press Play, then step 3 on Synth 1 while it sounds | Synth 1 rows (and Synth 2's note, if within the last 12) | Done |
| 10 | Uploader again: flash PL03 back (or keep PL03D until the next build) | — | |

## Results
2026-10-13, PL03D (device), Synth 1 on a simple patch (#8 / #9: square + square, everything else that costs DSP
time at 0). Analysis: `slim/docs/investigations/2026-10-12-chord-voice-dropouts.md`, "PL03D device run". Note: in these
logs `r` / "releasing" means **sounding** (held voices show as `r`); `H` = allocated in the same burst, not started yet.

#3 Read
0	33	Synth 1	C3 (48)	0x5210	4.10	ARM (mode 0)	0	free	------
50	34	Synth 1	E4 (64)	0x42E0	3.34	ARM (mode 0)	1	free	r-----
100	35	Synth 1	G4 (67)	0x3130	2.46	ARM (mode 0)	2	free	rr----
150	36	Synth 1	B4 (71)	0x2280	1.73	ARM (mode 0)	3	free	rrr---
200	37	Synth 1	D5 (74)	0x11D0	0.89	DSP	0	releasing	rrrr--

#4 Read
0	38	Synth 1	C3 (48)	0x52E0	4.14	ARM (mode 0)	0	free	------
10	39	Synth 1	E4 (64)	0x4390	3.38	ARM (mode 0)	1	free	r-----
20	40	Synth 1	G4 (67)	0x3310	2.55	ARM (mode 0)	2	free	rr----
30	41	Synth 1	B4 (71)	0x2440	1.81	ARM (mode 0)	3	free	rrr---
40	42	Synth 1	D5 (74)	0x1330	0.96	DSP	0	releasing	rrrr--

#5 Read
27908	43	Synth 1	C3 (48)	0x5300	4.15	ARM (mode 0)	0	free	------
27958	44	Synth 1	C2 (36)	0x4260	3.32	ARM (mode 0)	1	free	r-----
28008	45	Synth 1	E3 (52)	0x3540	2.66	ARM (mode 0)	2	free	rr----
28058	46	Synth 1	B3 (59)	0x2300	1.75	ARM (mode 0)	3	free	rrr---
28108	47	Synth 1	D4 (62)	0x1360	0.97	DSP	0	releasing	rrrr--

#6 Read
19064	48	Synth 1	E4 (64)	0x5460	4.22	ARM (mode 0)	0	free	------
19064	49	Synth 1	G4 (67)	0x5130	4.06	ARM (mode 0)	1	free	H-----
19064	50	Synth 1	B4 (71)	0x41F0	3.30	ARM (mode 0)	2	free	HH----
19064	51	Synth 1	D5 (74)	0x30B0	2.43	ARM (mode 0)	3	free	HHH---
19064	52	Synth 1	C3 (48)	0x21D0	1.69	ARM (mode 0)	4	free	HHHH--

#7 Read
38571	53	Synth 1	C3 (48)	0x53D0	4.19	ARM (mode 0)	0	free	------
38621	54	Synth 1	E4 (64)	0x4490	3.43	ARM (mode 0)	1	free	r-----
38671	55	Synth 1	G4 (67)	0x34E0	2.64	ARM (mode 0)	2	free	rr----
38721	56	Synth 1	B4 (71)	0x21F0	1.70	ARM (mode 0)	3	free	rrr---

#8 Read
0	69	Synth 1	C3 (48)	0x62C0	4.94	ARM (mode 0)	0	free	------
50	70	Synth 1	E4 (64)	0x5260	4.12	ARM (mode 0)	1	free	r-----
100	71	Synth 1	G4 (67)	0x4170	3.27	ARM (mode 0)	2	free	rr----
150	72	Synth 1	B4 (71)	0x33D0	2.59	ARM (mode 0)	3	free	rrr---
200	73	Synth 1	D5 (74)	0x23D0	1.79	ARM (mode 0)	4	free	rrrr--

#9 Read
0	98	Synth 2	C3 (48)	0xFFFF	12.80	ARM (mode 0)	6	free	------
484	99	Synth 1	C3 (48)	0x65F0	5.10	ARM (mode 0)	0	free	------
534	100	Synth 1	E4 (64)	0x5420	4.21	ARM (mode 0)	1	free	r-----
584	101	Synth 1	G4 (67)	0x43C0	3.39	ARM (mode 0)	2	free	rr----
634	102	Synth 1	B4 (71)	0x34E0	2.64	ARM (mode 0)	3	free	rrr---
684	103	Synth 1	D5 (74)	0x2420	1.81	ARM (mode 0)	4	free	rrrr--