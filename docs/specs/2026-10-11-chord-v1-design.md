# Chord engine v1 — design

Date: 2026-10-11 · Branch: `slim` · Version: `PL01` (CTPlay) · Status: implemented; PL01 passed on the device 2026-10-11 (`slim/firmware/PL01/TEST.md`)

## Purpose

One pad press in the synth / MIDI Note view plays a chord built in the project's scale. It is the first CTPlay feature:
a pure ARM-side note transform with no DSP work, and the first device-verified C feature on the slim foundation.

Chords are expanded **when played**. The extra notes go through the same stock path as a pad note, so the stock
recorder stores them as ordinary notes (up to 6 per step). Patterns therefore need no new format and keep playing on
the official firmware.

## Decisions

| # | Decision | Reason |
|---|---|---|
| C1 | Shapes are **scale-degree offsets** (stacked in the current scale) | Always in key; the router snaps pad notes into the scale, so semitone shapes would be bent (spike P2) |
| C2 | Palette under **Shift + the bottom two rows** of the Note view | Those rows are keys in both the 2-row and the expanded Note view; Shift + key pad has no stock function (it plays the note); Shift + step pad does, so the step rows are left alone |
| C3 | Settings **per track** (Synth 1, Synth 2, MIDI 1, MIDI 2), **not saved** | Saved state is not implemented in slim yet; recorded chords do not depend on it |
| C4 | **Stock plays the pad's own note**; the feature adds the other notes (approach A) | Stock keeps all its bookkeeping for the root (held-pad tables, LEDs, recording, view-switch clean-up) |
| C5 | Inversion and spread move the **other** notes by octaves; the root never moves | Required by C4; same chord, lower register. The bass option covers a low root |
| C6 | Shared notes between held chords follow **stock behaviour** | No stuck notes in any order; improving it later is local to the release handler (see Later) |
| C7 | MIDI tracks and synth tracks are treated alike | One Note-view class serves all four tracks |

## Findings this design rests on

From the emulation spike on `refs/archive/spike-chord-probe` (the branch `spike/chord-probe` until 2026-11-21; `slim/spike/` there), stock image only unless noted:

- **Hook points.** The Note view (vtable `0x0805A064`; Synth 1 / 2, MIDI 1 / 2) starts a pad note in
  `0x0804AEF2(view, pad, vel)` and ends it in `0x0804AF5A(view, pad)`. Each has one caller: the press handler
  `0x0804AB5A` and the release handler `0x0804ACC4`. Not `0x0804B07A`: its second caller (`0x0804B580`) plays the notes
  of a held step.
- **Both Note views.** The default 2-row view (container mode 1) and the expanded view (mode 6) use the same view
  object and the same `0x0804AEF2` for their key pads. Step pads of the 2-row view do not pass through it.
- **Sending notes.** The view's sink `[view + 0x18]` (vtable `0x0805BF54`) takes note-on in slot 0 `0x0801D38E(sink,
  note, vel, pad)` and note-off in slot 1 `0x0801D942(sink, note, pad)`. Notes are root-relative pitch values from
  the keyboard table `[[view + 0x38] + 0x14 + idx]`, `idx = 0x0804B174(view, pad)`.
- **Router ownership.** The router keeps one owner pad per pitch. A note-on of a held pitch from another pad
  re-triggers it and takes it over; note-offs from a pad that no longer owns the pitch are ignored. No release order
  leaves a stuck note; releasing the later of two chords silences the notes it shares with a still-held earlier one.
- **Scale snapping.** Pad notes outside the scale are moved into it, in either direction (e.g. C minor: C♯ → D,
  E → E♭).
- **Recording.** Each note-on becomes its own pending entry in the track recorder (`0x2003C1E8` for Synth 1). The
  write into the step happens on sequencer ticks, which the emulation does not run: **the step contents are confirmed
  on the device** (test plan).
- **View switches.** Leaving the Note view (another track, Mixer, FX, Preset) makes stock release every held pad
  through the release handler `0x0804ACC4` (through the vtable at `0x0804394A` on a track change; Mixer releases pads
  0–31 through the controller's pad release `0x080332CE` at `0x08033A76`), which ends them in `0x0804AF5A`; the later
  physical release sends nothing. Toggling between the 2-row and expanded Note view keeps the
  pad held and the normal release ends it. With the spike's feature the extra notes stop together with the root in
  every case.
- **The release handler does not always end the note** (final review of PL01, reproduced in emulation). The Note
  view's release handler `0x0804ACC4` (vtable `0x0805A064` slot 1) reaches `0x0804AF5A` only when the pad still owns a
  note: it returns at once when `[view + 0x40 + pad] == 0` (`0x0804ACD4`), and with a step held (p0 of
  `[view + 0x2C]`) whose notes contain the pad's pitch it only clears `[view + 0x40 / 0x60 + pad]` (`0x0804AD2A`) and
  leaves the root to the step's own release. Holding a step while a key is held writes that key's root into the step
  (listener `0x0804B1F2` → `0x0804B094`), so that branch is the normal case. `[0x40 + pad]` is also cleared for another
  pad by the note start when a pad takes a pitch another pad holds (`0x0804AF2C`; 2-row view pads 17 and 32,
  expanded view pairs 1 / 16, 9 / 24, 17 / 32) and by the step-edit press path (`0x0804AC74`). A chord ended only at
  `0x0804AF5A` therefore left its other notes on (chord pad released before the held step) or leaked its table entry
  and chord-note LEDs (same-pitch pads). The chord's notes are ended at `0x0804ACC4` instead (hook `pad_release`).
- **Shift.** Shift + a key pad in the Note view plays the note as stock (nothing to lose). Shift + a step pad in the
  2-row view changes stock state differently from a plain step press (not decoded).
- **Cost.** The spike feature (triad on every pad) was 680 B of flash and 36 B of RAM, inside the build checks.

## 1. Architecture

Feature `chord` in `slim/features/chord/`, version `slim/versions/PL01.toml`.

| Hook point | Kind | Address | Handler does |
|---|---|---|---|
| `pad_note_on` | entry | `0x0804AEF2` | Shift held + bottom-two-row pad: select a palette option, `HANDLED`. Otherwise send the chord's other notes, remember them, `PASS` (stock plays the root) |
| `pad_release` | entry | `0x0804ACC4` | Stock's release handler, reached by every release of a Note-view pad (and by stock releasing every held pad when the view is left), before its early returns (see Findings). Consumed palette pad: clear the bit, `HANDLED`. Otherwise send note-offs for the remembered notes of this pad, `PASS` |
| `pad_note_off` | entry | `0x0804AF5A` | Safety net, reached only from `0x0804ACC4`: send note-offs for anything still remembered for this pad (normally nothing), `PASS`. The consumed bit is handled in `pad_release` only |
| `led_task` | call (existing) | `0x08033B46`, `0x0803415A` | Palette under Shift; the chord's other notes while held |

New entries in `slim/stock/symbols.toml` (moved from the spike, with notes and sources): the three hook points,
`note_pad_index` `0x0804B174`, `note_sink_on` `0x0801D38E` and `note_sink_off` `0x0801D942` (both tagged
`takes_dsp_lock`), and a data symbol for the controller `0x20040B10` (Shift = parameter 0 of the store at
`ctrl + 0x0C`, as `diag_ram` reads it).

**Guards.** The handlers pass everything to stock unless the view's vtable is `0x0805A064` and its sink's vtable is
`0x0805BF54` and the sink's key byte `[sink + 0x0C]` is below 4. The track index (0–3) is that key byte (verified 0–3
for the four Note views), not a comparison with the container's sub-views; no other view is touched.

**Context.** UI only. The sink calls take the DSP lock, which is allowed there; the build refuses `takes_dsp_lock`
calls from a `dsp_tick` hook.

**Order.** The other notes are sent just before stock plays the root (microseconds apart). Velocity is the pad's
velocity after stock's fixed-velocity rule, for every note.

## 2. Chord maths

Pitches are in the keyboard table's root-relative space (the router adds the project root later). The scale mask
(`0x2003FA90`, 2 bits per semitone from the root, 0 = in the scale) defines the degrees.

1. **Root** `r` = the stock pitch of the pad.
2. **Chord tones**: for each degree offset `d` of the shape, walk `d` scale degrees up from `r` (count only semitones in
   the scale). Tone 0 is `r`.
3. **Inversion k** (0–3): every tone with index ≥ k (k > 0) moves down 12. Inversion k ≥ the number of tones acts as
   inversion 0.
4. **Spread**: close = unchanged; drop-2 = the second-highest tone after inversion moves down 12, skipping tone 0 (if
   tone 0 is second-highest, the next one down moves; with fewer than 3 tones drop-2 is close); wide = tones with
   index 1 and 3 move up 12.
5. **Bass** (see "Bass modes" below, PL03): bass below adds `r − 12`; rootless over bass adds no bass and moves the
   other tones up 12.
6. Drop tone 0 (stock plays it), drop duplicates of `r` and of each other, drop values outside 0–127. At most 5 other
   notes (shape ≤ 5 tones + bass ≤ 6 notes per chord, the step's limit; since PL03 the bass modes keep a chord to
   5 notes).

**Chromatic scale** (mask 0): a degree walk would stack semitones. In Chromatic the walk uses the **major scale on the
project root** instead, so pads play the chords of the major key; a note outside it walks to the next major-scale
degrees. The router does not snap in Chromatic, so these notes stay as computed. Kept after the device run (2026-10-11).

**5- and 6-note scales** (pentatonic, whole tone, …): the same walk gives wider stacks; accepted as the scale's own
colour.

## 3. Palette, voicing and LEDs

Pads numbered 1–32 from the top left, as on the device (code uses 0–31).

**Bottom row, pads 25–32: shape**

| Pad | 25 | 26 | 27 | 28 | 29 | 30 | 31 | 32 |
|---|---|---|---|---|---|---|---|---|
| Shape | single (chord mode off) | triad | 7th | 9th | sus2 | sus4 | add9 | 6th |
| Degrees | {0} | {0,2,4} | {0,2,4,6} | {0,2,4,6,8} | {0,1,4} | {0,3,4} | {0,2,4,8} | {0,2,4,5} |

**Row above, pads 17–24: voicing**: inversion 0 / 1 / 2 / 3 (pads 17–20), spread close / drop-2 / wide (pads 21–23),
bass (pad 24; since PL03 cycles no bass / bass below / rootless over bass).

Each Shift + pad press sets one option for the selected track. Default for every track at power-on: single, inversion
0, close, bass off.

**Consumed pads.** A Shift press on a palette pad sets the pad's bit in a 32-bit mask; the release of a pad whose bit
is set (at `pad_release`, the only place the bit is read on release) clears it and returns `HANDLED` (no note-off). Any press that is not consumed clears the pad's bit, so a release
lost to a view switch cannot swallow a later normal release.

**LEDs** (handlers run after stock and may overwrite its output):
- Note view active (container active, mode 1 or 6, selected track's sub-view is a Note view) and Shift held: pads
  17–32 show the palette. Each group has its own hue (shape, inversion, spread, bass); the selected option is bright,
  the others dim. Pads 1–16 stay as stock.
- A chord held on the visible track, Shift not held: key pads whose pitch is one of the chord's other notes light in
  the root pad's pressed colour (found by mapping each visible key pad through `note_pad_index` and the keyboard
  table).
- Colours are Novation palette codes, chosen in the implementation and confirmed on the device. Each code's RGB is
  checked in emulation against stock's own LEDs first: stock reads some colours from a palette in RAM, and a code taken
  from the flash palette can render differently (upstream SC37.9: 0x46 showed dim red-orange, stock's blue is 0x07).

## 4. State and budgets

| State | Size |
|---|---|
| Settings: 4 tracks × 1 B (shape 3 bits, inversion 2, spread 2, bass 1); since PL03 plus 1 B `chord_rootless` (bit per track) | 4 B (+1) |
| Held chords: 6 entries × {track, pad, count, 5 notes} | 48 B |
| Consumed palette pads | 4 B |
| **RAM budget** (`feature.toml`) | **64 B** of 240 B |
| Flash (estimate) | ~1–1.5 KB |
| Stack budget (`feature.toml`) | 128 B; measured 128 B for `chord_on_pad` (the other handlers 48 B or less). Real extra depth over stock's own path ≈ 168 B with the entry stub (32 B) and the dispatcher (8 B), which the build does not count; the device gate is in `slim/firmware/PL01/TEST.md` (SL00D's stack page) |

**Table full**: the chord plays as the single stock note (no other notes are sent, so nothing can stick). A pad that
is already held on the same track is released first (cannot happen through stock's press path; guarded anyway).

## 5. Testing

**Build checks**: stack, DSP-lock context, RAM and flash budgets, flash safety, marker (`PL01`).

**Emulation** (`slim/tests/test_chord.py`, `emu` marker), through the real controller route
(`0x08033320` / `0x08033282`) unless noted:
1. **Chord maths vs a Python model** — every shape × inversion × spread × bass, 16 scales × 3 roots × all pads, the C
   function called directly (the only direct call; tests 3–5 cover the same maths through the route).
2. **Transparency** — with every track on "single", `PL01` equals stock (LEDs, controller state, events) over the
   seeded random scripts of `test_transparency.py`.
3. **Notes per track and view** — Synth 1 / 2 and MIDI 1 / 2, 2-row and expanded Note view, each shape: the notes at
   the synth and MIDI-out endpoints equal the model; every note-on has its note-off.
4. **Note-balance fuzz** — seeded random scripts mixing overlapping presses and releases, Shift palette changes while
   chords are held, and track / view switches mid-hold. After each script the set of sounding notes per synth and
   MIDI track, rebuilt from the endpoint events, is empty.
5. **Palette** — Shift + a pad in pads 17–32 changes only the setting (no note events; its release sends nothing);
   Shift + pads 1–16 behave as stock; LEDs show the palette under Shift and the chord's other notes while held.
6. **Recording** — with recording on, every chord note reaches the recorder gate.

**Device** (`slim/firmware/PL01/TEST.md`):
- Boots; with chord mode off the device behaves as stock.
- MIDI 1 into a MIDI monitor on a computer: exact notes and on/off balance for each shape and voicing.
- Synth 1 by ear; stuck-note scenarios: switch track while holding, overlapping chords, change the shape while
  holding.
- Record a progression and play it back: all chord notes are in the steps. Optional: save, flash stock, load the
  project; the chords still play.
- 5–6-note chords overlapping on one synth: voice stealing by ear.
- Palette colours confirmed.

## Bass modes (PL03, 2026-10-12)

Added after the device tests of the chord-note dropouts (`docs/investigations/2026-10-12-chord-voice-dropouts.md`):
the synth holds about 4–5 notes, depending on the patch (DSP time), and a further note takes the lowest / oldest voice,
so 9th + bass (6 notes) always lost its bass. Decided with the user:

| # | Decision | Reason |
|---|---|---|
| B1 | Pad 24 **cycles three states** per track: no bass → **bass below** → **rootless over bass** → no bass. LED under Shift: dim orange / orange / white (`0x01`, stock's playhead white) | Both bass voicings are musically useful; one pad keeps the palette as it is |
| B2 | **Bass below** = PL01's bass, except that a chord that would have 6 notes (only 9th + bass) leaves out its **5th** (shape degree 4): root, bass, 3rd, 7th, 9th. Only when the bass sounds (root ≥ 12) | Other shapes + bass were already ≤ 5 notes and keep the sound tested in PL01 / PL02; dropping the 5th of a triad or sus chord thins it |
| B3 | **Rootless over bass**: the pad's own note is the bass; the chord's other tones move up an octave, and no tone with the root's note name is kept. 9th → bass + 3rd, 5th, 7th, 9th (5 notes). Inversion and spread apply to the upper chord. The player plays an octave lower than without bass (documented) | No doubled root, a voice saved, a common voicing (rootless chord over a bass note) |
| B4 | In both modes the **bass is the lowest note**: a tone below it (inversion + drop-2 can lower a tone twice) is raised by octaves until it is above | Review finding; "the bass is the bass" (user decision) |
| B5 | State: the settings byte's bass bit + `chord_rootless` (1 B, bit per track), passed to `chord_notes()` as bit 8 (`CHORD_ROOTLESS`); "rootless" without the bass bit means no bass | The settings byte is full; the cycle never leaves that state |

Tests: the Python model and the C maths agree over every shape × inversion × spread × the three modes; the model
asserts B2–B4; pads through the real route for both modes (both Note views), the LED cycle, strum in rootless mode
(rises from the pad), a mode change while a chord is held. Chord stack budget 128 → 160 B (`chord_on_pad` 136 B).
Device test plan: `firmware/PL03/TEST.md`.

## Later (not in v1)

- ~~**Re-sound shared notes** (C6)~~: done in PL05 (only the notes the released pad owned, from the router's table).
- ~~**Clamp chord notes to stock's valid range**~~ (done in PL05, out-of-range notes left out): today a chord note must be 0–127 in keyboard space, so the top octave
  plays single notes and the lowest octave loses notes (no stuck notes). Stock's valid range is pitch + root within
  12–139, i.e. `12 − root … 139 − root` using the root byte at `[[kbd + 0x10]]`. Deferred: it changes the maths and
  the model.
- **Chords in step entry**: pads pressed while a step is held go through stock's step-editing loop, not
  `0x0804AEF2`.
- **Semitone shapes** (v2 palette): needs Chromatic or a way past the router's scale snapping.
- **Saved settings**: with slim's saved-state implementation.
- **Strum**: done in PL02 (`specs/2026-10-12-strum-design.md`). **Arpeggiator**: needs a general event queue.

## Not in scope

Drum tracks, MIDI-in notes, sequencer playback (recorded chords play as stock notes), the DSP.
