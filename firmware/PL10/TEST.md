# PL10 — device test plan (saved settings)

**What it is:** PL09 plus saved settings (spec `slim/docs/specs/2026-10-17-saved-settings-design.md`): every CTPlay
setting (chords, bass modes, strum speed and direction, arpeggiator with Latch, mono record, each track's last page and
Quick view, the count-in) is saved **with the project**, in a 33-byte block in the project's last 1000 bytes (which
stock saves and loads but never reads). Save the project and its settings come back when it is loaded, also after a
power cycle. A project without CTPlay data (stock, upstream, older CTPlay, a new project) loads everything off.
A setting is kept only when the project is saved, like stock's own edits.

CTPlay still writes nothing to flash or the SD card itself: stock's own Save writes the project file. Test PL09 first
(`firmware/PL09/TEST.md`): this run checks only what changed.

## Before you start
0. **Build from the tag** (PL11 changed the shared sources after PL10): `git checkout PL10`, then
   `cd slim && ../.venv/bin/python -m slimbuild versions/PL10.toml`, then `git checkout slim`. The printed syx sha256
   must equal `syx_sha256` in `slim/firmware/PL10/manifest.json` (`5b43839c…`).
1. **Stack headroom gate (SL00D):** as PL09 (unchanged: 416 B Main, 212 B LED task, 256 B pad press). The load hook
   adds 64 B on a task not identified, the save hook 56 B on the UI task.
2. **Back up the SD card** (or every project with Components): the test saves over projects. Use a pack you can lose.
   Way back: Scales + Preset + Note at power-on, send the stock `.syx` (or PL09).
3. Flash `slim/build/PL10/circuittracks-4486-PL10.syx` with `slim/build/ct_uploader.html`.
4. Pick three slots: **A** (a project of yours, re-saved here), **B** (an empty slot), **C** (a stock-made project you
   have not saved under PL10). Keep a `02_Shadow Child` project at hand for step 8 if you have that pack.

## Steps
| # | Do | Expected | Result |
|---|---|---|---|
| 1 | Load A. Set something different on all four tracks (Synth 1 / 2, MIDI 1 / 2): a chord shape + inversion + bass (Shift palette), strum speed and falling (Chords page), an arpeggio with Latch on and a non-default gate (Arp page), mono on two tracks (Keys page); leave each track on a different last page and flip one Quick view (Shift + 1-16/17-32). Shift + Clear: count-in (magenta). Note it all down. Save A (Save, Save) | Saves as stock does | OK |
| 2 | Power off and on. Load A | Every setting of step 1 is back on every track (chords, bass, strum, arp with Latch and gate, mono, the page Shift + track opens, the Quick view, Clear's colour with Shift = magenta). Patterns, patches and scenes as saved | OK |
| 3 | Load C (stock-made) | Everything off: single notes, strum off, arp off with gate 3/6, poly record, Chords page, count-in off | OK |
| 4 | Load A, then go to B (empty slot) to start a new project | Everything off (if A's settings show up here: report, design question Q5) | OK |
| 5 | Load A, Save it to slot B (save to another slot). Load C, then load B | A's settings, on B | OK |
| 6 | Load A. Hold a chord pad on Synth 1 and start a latched arpeggio on Synth 2 (press and let go). While the pad is still held, load C | No stuck notes when you let go of the pad; the latched arpeggio stops after the load | OK: Held chord always stops immediately when navicating away from a synth. Latched arp stops when switching project.  |
| 7 | Load A, start a count-in (Record, Play) and load C during the clicks | The clicks stop, nothing starts recording | OK: Count-in stops, record stays armed on selected project |
| 8 | Load a `02_Shadow Child` project (random bytes where CTPlay keeps its block), play it | Everything off, nothing odd; it plays as on stock | OK: Not 100% sure how the project(s) sound on stock, but everything was off as expected, and seems to play without issues and sounds correct. |
| 9 | Components: download A from the device, then send it back to another slot; load that slot | Components accepts the project (its validator does not check the last 1000 bytes: from its strings, not run). The settings are there | OK |
| 10 | Flash stock 1.2.1 (way back above). Load A: it plays as before (patterns, scenes, patches). Save it. Flash PL10 again, load A | On stock: nothing different. Back on PL10: step 1's settings are back | OK: Tested with a very simple test project, but after re-flashing PL10 all the settings were as before. |

## Results
2026-10-18, PL10: **passed.** Settings came back after a power cycle, from another slot, through Components and
after a round trip through stock 1.2.1; stock-made, new and `02_Shadow Child` projects loaded everything off.
