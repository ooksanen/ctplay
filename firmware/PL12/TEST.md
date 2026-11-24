# PL12 — device test plan (CTCtrl link)

**What it is:** PL11 plus the **CTCtrl link** (spec `slim/docs/specs/2026-10-18-ctctrl-link-design.md`): over USB
SysEx, an app can ask which CTPlay build this is and which settings it has, read every CTPlay setting, change any of
them with the same effect as the pads, and is told about every change made on the device. Nothing changes on the
device itself: no new pad, button or page. Until CTCtrl's CTPlay panel exists, the test uses a small page,
`slim/pages/ctplay_link.html` (open the file in Chrome or Edge).

Writes nothing to flash or the SD card itself. Test PL11 first (`firmware/PL11/TEST.md`): this run checks only what
changed.

## Before you start
0. **Build from the tag** (PL13 changed the shared sources after PL12): `git checkout PL12`, then
   `cd slim && ../.venv/bin/python -m slimbuild versions/PL12.toml`, then `git checkout slim`. The printed syx sha256
   must equal `syx_sha256` in `slim/firmware/PL12/manifest.json` (`2ad0b5fc…`).
1. **Stack headroom gate (SL00D):** Main and UI with at least 2 green pads (≥ 1.5 KB free). PL12 runs as PL11 on Main
   (416 B), the LED task (280 B) and pad presses; the link adds 256 B on the LED task (not deeper than chord's 264 B)
   and 92 B on incoming SysEx (task not identified; PL03D's voice log used 112 B there).
2. **Back up the SD card**: step 6 loads projects. Way back: Scales + Preset + Note at power-on, send the stock `.syx`
   (or PL11).
3. Flash `slim/build/PL12/circuittracks-4486-PL12.syx` with `slim/build/ct_uploader.html`.
4. Synth 1 on a simple Poly patch. Close Components and CTCtrl (one app at a time holds the port on some systems).

## Steps
Track numbers in the page's writes: 0 Synth 1, 1 Synth 2, 2 MIDI 1, 3 MIDI 2. Offsets and bits: the spec's payload
table (strum: offset 5, 2 bits per track; arp of track t: offset 8 + 2t).

| # | Do | Expected | Result |
|---|---|---|---|
| 1 | Open `ctplay_link.html`, Allow MIDI access | "Connected: PL12, protocol 1, layout 1, 37 B, 8 fields." The log shows `hello: PL12, 8 fields` | OK |
| 2 | Read | The table: chord settings, rootless, strum, strum falling, mono, arp, count-in, euclid, with the current project's CTPlay settings (a new project: all 00, arp `00 08` per track, euclid `20 40` per track) | OK: 
field	offset	bytes
chord settings	0	01 2A D3 DC
rootless	4	00
strum	5	A0
strum falling	6	08
mono	7	0A
arp	8	00 08 CB 00 00 08 85 16
count-in	24	01
euclid	25	2B 43 20 40 2D 41 20 40 |
| 3 | On the Circuit: Shift + Synth 1 (Chords page). On the page: Write offset 5, bytes `02` | At once, without touching the Circuit: the Chords page shows strum medium on Synth 1. The log shows one state with strum `02` | OK |
| 4 | On the Circuit: tap strum pads 1–4 on the Chords page, one at a time | One `state` line per tap in the log, strum changing each time | OK |
| 5 | ▼ to the Arp page, ▲ back, ▼ ▼ ▼ through every page | **Nothing** logged: changing page sends nothing | OK |
| 6 | Load another project whose CTPlay settings differ from the current ones (saved under PL10 or later) | One `state` line with that project's settings (a project with the same linked settings sends nothing) | OK |
| 7 | Synth 2: Arp page, pattern Up, Latch on, play a chord pad and let go (it keeps arpeggiating). On the page: Write offset 5, bytes `0C` (Synth 2 strum fast; a write is a whole byte, so Synth 1's strum goes off) | The arpeggio **keeps playing**; one state logged | OK |
| 8 | Same arpeggio: Write offset 10, bytes `01` (Synth 2: pattern Up, rate 1/4, latch off; if you changed Synth 2's rate in step 7, use the arp byte the last state shows minus `80`) | The arpeggio stops (latched notes freed); the Arp page shows latch off | OK |
| 9 | Write offset 0, bytes `60` (spread 3: not a value the pads make) | Nothing changes on the device; one state logged, unchanged | OK |
| 10 | Write offset 33, bytes `01` (the saved page: not linked) | Nothing changes; one state logged, unchanged | OK |
| 11 | Open Components (close the page first if your system shares the port badly). Connect, look at the packs, save a project from the Circuit | Components connects and works as with PL11 | OK |
| 12 | Close the page. Press pads on a Chords page for a minute, with Components open | No error in Components; the Circuit behaves as usual | OK |
| 13 | Once CTCtrl's CTPlay panel exists (CTCtrl's plan): connect CTCtrl | It shows the CTPlay panel; a tap on each tab changes the device; a pad press on the device shows in the panel; CTCtrl's packs read and track follow still work | OK |

## Results
2026-10-19, PL12 (`2ad0b5fc…`): **passed.** Steps 1–13 OK, including CTCtrl's CTPlay panel (step 13).
