# Drum views, drum pad routes, drum hits, prior art for note repeat (research, 2026-10-25)

Stock = Circuit Tracks 1.2.1 build 4486. Status tags: **[asm]** checked by me in `re/app.asm` / objdump of
`stock/circuittracks-firmware-4486-STOCK.bin`; **[ram]** read by me in the device RAM snapshot
`ctre/Firmware-Analysis/ram_dump_firmware_0x08037988.bin`; **[slim]** slim code / symbols; **[upstream]** upstream claim
(file / NOTAS section at `395d9e6`); **[device]** NOTAS / slim records it on the device; **[guess]**.

## 1. Stock's drum views

### The container decides which view gets a pad
The track container `0x20040DB8` (vt `0x0805A62C`) is the active view `[ctrl+0x6C]` for every track view **[asm, ram]**.
It is a two-half composite:
- Container press `0x080435B0(cont, pad, vel)` / release `0x080435F0(cont, pad)` (its vt slots 0 / 1) **[asm]**: set /
  clear the pad's bit in `[cont+0x190]` (release acts only if set), pick the view with `0x08043B6E(cont, pad)` (pad < 16 →
  top-half lookup `0x08043B2C(cont, track, mode)`, pad >= 16 → bottom / whole lookup `0x08043A84`), remap the pad with
  `0x08043E86(cont, pad, track, mode)`, then call the view's slot 0 (view, pad', vel) / slot 1 (view, pad').
- Pad remap `0x08043E86` **[asm]**: pad >= 16 becomes pad - 16 unless the mode is full-grid (`0x08050146`: mode 4, 6 or 7)
  or (`0x0805015C`) mode 1 on a note track (track < 4). Pads < 16 get + 16 on the 17-32 page when `0x0805016C` says so
  (mode 1 and a drum track, page store `[[cont+0x124+4t]+0x10]` p0).
- Mode = byte `[cont+0x18C]`, **one byte for the whole container** (shared by all tracks) **[asm]**; track =
  `track_of(cont)` `0x0805011E` (`[cont+0x188]` p0, 0-7) **[asm, slim]**.

### Drum view objects (RAM snapshot, d = drum 0-3) **[ram]**, mapped to modes by the two lookups **[asm]**
| Mode `[cont+0x18C]` | Top half (pads 0-15) | Bottom half (pads 16-31, as 0-15) | What it is |
|---|---|---|---|
| 1 (drum track's default) | `[cont+0x9C+4d]` vt `0x0805AD0C` | `[cont+0x8C+4d]` vt `0x0805ABBC` | steps on top; the drum's **sample pads** below |
| 6 (Note pressed again) | `[cont+0xAC]` vt `0x0805AD44`, whole grid, **one object for all four drums** | (same) | expanded drum view: pads 29-32 = drums 1-4 |
| 0 (Preset) | `[cont+0x8C+4d]` whole grid | (same) | drum Preset (sample pages) |
| 2 (Velocity) | step view `+0x9C` | `[cont+0xB0+4d]` vt `0x0805AD7C` | |
| 3 (Gate / micro) | step view | `[cont+0xC0+4d]` vt `0x0805AAA4` | |
| 4 (Pattern Settings) | whole grid `[cont+0xD0+4d]` vt `0x0805AB4C` | | |
| 5 (Probability) | step view | `[cont+0xE0+4d]` vt `0x0805AB14` (upstream: objects `0x200438DC + 0x3C d`) | |
| 7 (Sidechain) | whole grid `[cont+0x88]` vt `0x0805AC2C` (shared) | | |
| 8 | step view | `+0x8C+4d` | |

For comparison, note tracks: `+0x18+4t` Note view (`0x0805A064`, mode 1 bottom and mode 6 whole), `+0x28+4t` step views
(`0x0805ADB4`), `+0x38` velocity (`0x0805ADEC`), `+0x48` gate / micro step (`0x0805AB84`, modes 3 and 8), `+0x58`
Pattern Settings, `+0x68` probability (`0x0805ACD4`), `+0x78/+0x7C` synth Preset (`0x0805AC9C`), `+0x80/+0x84` MIDI
templates (`0x0805AE5C`) **[ram, asm]**. Upstream's subview numbers `[ctrl+0x152]` for drums: Preset 36+8d, Note 37+8d,
Note expanded 42+8d (not 9 apart: the SC42.4 roller bug) **[upstream NOTAS SC42.5]**.

View vtable layout (all classes): slot 0 pad press, 1 pad release, 4 knob, 7 LED buffer getter, 8 LED painter **[asm]**.
| Class | slot 0 | slot 1 | slot 7 / 8 |
|---|---|---|---|
| drum sample / Preset `0x0805ABBC` | `0x0804D934` | `0x0804DA38` | `0x08047592` / `0x0804DB8E` |
| drum expanded `0x0805AD44` | `0x0804ED50` | `0x0804ED68` | `0x08047592` / `0x0804ED84` |
| drum step view `0x0805AD0C` | `0x0804E27E` | `0x0804E45C` | `0x0804EAD4` / `0x0804E7CC` |

### What a drum pad press does
- **Expanded view** `0x0804ED50(view, pad, vel)`: pads < 28 ignored (rows 1-3 and pads 25-28 are free in stock);
  pad 28-31 → `[view+0x10]` slot 0 (sink, note = pad - 27 = drum 1-4, vel, pad) **[asm]**. Release `0x0804ED68`: pad >= 28 →
  slot 1 (sink, pad - 27, pad) **[asm]**. Its painter `0x0804ED84` lights LED entries 28-31 white (palette `+0x148`) while
  the drum's bit is set in `[view+0xC]` (a "sounding" bitmask), else palette `+0x140 + 2d` **[asm]**; upstream: white
  until the note-off **[upstream NOTAS SC43.1, seen on the device]**.
- **Sample view** `0x0804D934(view, pad, vel)`: sample = pad + 32 × page `[view+0x20]` p0, written to `[view+0x3C]`
  p0 (upstream: the pad held) and committed; sets the patch sample through the setter `[view+0xC]` slot 0, ends what the
  view sounded (`0x0804E0E8`), and tail-calls the hit `0x0804E0BA(view, pad, vel)` **[asm]**. The drum's *selected*
  sample is `[view+0x2C]` = the player's `[+0x5C]` (same store `0x2003E8D8` for drum 1 **[ram]**), written at the release
  `0x0804DA38` **[upstream SC42.8]**. A 300 ms timer path (`0x0803C432(7, 0, 300, cb, view)`) runs when `[view+0x3C]` p1
  == 0xFF **[asm; purpose not traced]**.
- **The hit** `0x0804E0BA(view, pad, vel)`: if `[view+0x1C]` p0 == 0 (= the **Shift store** `0x20040A50`, `[ctrl+0xC]`:
  Shift + sample pad = stock's silent selection) → `[view+0x29]` = pad, `[view+0x28]` = 1, then `[view+0x10]` slot 0
  (sink, note = `[view+0x25]` = drum 1-4, vel, 0) **[asm, ram]**. `0x0804E0E8(view)`: if `[view+0x28]`, clear it and
  slot 1 (sink, `[view+0x25]`, 0) **[asm]**.
- **The sinks** are the same class as the Note view's (vt `0x0805BF54`, `note_sink_on` `0x0801D38E` / `note_sink_off`
  `0x0801D942`) with track byte `[sink+0x0C]` = **0x10** for every drum source **[ram]**: sample view sink at
  view + 0x54, expanded view sink at `0x200434E8`. `note_sink_on` calls `[sink+8]` slot 0 (an adapter, vt `0x0805BF84`
  `0x0801A99A`): router index = track + adapter offset, minus 12 when track >= 4 **[asm]**. Live adapter `0x20040100`
  (offset 0) → **router index 4 = live drums**; the players' adapter `0x2004010C` (offset 5) → index 9 = playback drums
  **[asm, ram]**.
- **Router** `0x2003ECDC` (vt `0x0805B840`, slot 0 `0x0803222C`, `tbh` over index 0-29) **[asm]**:
  - index 4 → `0x080325AC(router, source 0, track 16, note, vel, pad)`: live source with fixed-velocity bit (bit 1 of
    p2 of `[router+0x94]` = settings store `0x200111CC`) forces vel 96 **[asm; "= Shift + Velocity" is a guess]**; drums
    skip the scale quantiser; owner table `[router+0xD58+12·4+4·src]` indexed by note; **a note already taken is ended
    first** (live: recorder-gate note-off `[router+0x90]` slot 1, then output note-off), then note-on to output
    `[router+0x44+12·4+4·src]` = `[router+0x74]` **[asm]**. Note-off `0x08032684` acts only when both note and pad match
    **[asm, slim symbols]**.
  - index 9 (playback drums) `0x080322AC`: own table at `[router+0xD8C]`, ends a sounding note via `[router+0x78]`, then
    note-on **[asm]**.
  - Later stages: index 19 → `[router+0x88]` (vt `0x0805BF44`, `0x08031DA4`, the engine side) with track 16 and a bit in
    `[router+0x34]`'s store; index 24 → `[router+0x8C]`; **index 29 → `[router+0x90]` slot 0 = the recorder gate** with
    track 16 **[asm]**. Between them the per-track source mergers (vt `0x0805BF74`, `0x08040ADC` / `0x08040B70`; drums'
    at `0x2003FFB8`, output sink `0x20040000` with track byte 0x18 back into the router) **[ram, asm]**. Which stage feeds
    index 29 was not traced to the end **[open]**.
- **Recorder gate** `0x2003C168` (vt `0x0805B820`: slot 0 `0x0802E56A` note-on, slot 1 `0x0802E5CC` note-off, slot 2
  `0x0802E62C` parameter / automation) **[asm, ram]**: acts only while playing (transport `0x20011034` p0), Record (p1) and
  **not in the count-in** (p2 == 0); track 16 → recorder `[gate + 0xC + 4·(note + 3)]` = drum recorder (note 1-4 →
  recorders 4-7, vt `0x0805A578`, byte +4 = drum 1-4; its slot 0 is `0x0803FC5E`, the same function as the note
  recorders' `0x0805A5B4` slot 0) → slot 0 (rec, note, vel, 0) **[asm, ram]**. So a live drum hit sent through a drum
  sink is recorded by stock's own recorder when playing with Record; stopped with Record it is not **[asm]**.

### Drum players (the sequencer side) **[asm, ram]**
- `0x20040810 + 0x90·d` = `seq_players + 0x610` (right after the four note players; ends at `0x20040A50`), vt `0x0805B72C`.
  `[+0x48]` patterns (0x6A8 B each), `[+0x4C]` its sink (embedded at + 0x60, track byte 0x10, adapter `0x2004010C`),
  `[+0x58]` byte = drum 1-4 (its note), `[+0x59]` sounding, `[+0x5C]` selected-sample store, `[+0x50]` / `[+0x54]`
  sample setter, `[+0x28]` Mixer mute store, `[+0x8]` position store (p0 pattern, p1 step, p2 tick), `[+0x10]` p1 sync
  index.
- Player step `0x0804A714` (from the tick `0x0804A5C6`, slot 0, skipped when muted or in the count-in: `0x0804A618` /
  `0x0804A632`): on tick 0 slot 4 `0x080411CA` (the step's first hit sets the sample: its sample flip `+0x40+step`, or
  the selected one), automation `0x0804A7CA`, then slot 2 for each micro step of the tick (`TICK_TAB` `0x08059218`, 24 B
  a row by sync index; `0x0804A2E8` for rates < sync 3).
- Slot 2 `0x08041252(this, pattern, step, micro)`: hit test `0x0804AA08(base, step, micro, [this+4])` (velocity
  `[base+step]` != 0, probability `[+0x20+step]` >= rnd & 7, micro-step bit in `[+0x60+step]`); on a hit: if `[+0x59]`
  → sink slot 1 (note-off) first, then slot 0 (note `[+0x58]`, vel `[base+step]`), `[+0x59]` = 1.
- Slot 1 `0x080411AC(..., r3)`: note-off when sounding and r3 == 0 (upstream: the next step's micro step 0); slot 3
  `0x08041190`: note-off when sounding.

## 2. Buttons, Shift, and extending slim's pages to drums
- Button ids **0-7 = Synth 1, Synth 2, MIDI 1, MIDI 2, Drum 1-4** **[upstream NOTAS SC08; asm]**. In `0x08033320`, ids 0-7
  share the track case `0x08033400` (`tbh` at `0x080333C4`): `cont_select_track(cont, id)` (`0x08043448`), then
  `cont_track_view(cont, 1)` (`0x0804348C`) and `ctrl_set_view` (`0x080335FC` → `0x0803390C`) **[asm]**: the drum buttons
  take exactly the path `page_open()` already replays.
- Shift: `0x080333A0` reads `[ctrl+0xC]` p0; with Shift and id != 0x1B, the mask at the literal = `0x07DBBE00` lets only
  ids 9-13, 15-17, 19, 20, 22-26 through; ids 4-7 go to `0x08033706` (nothing) **[asm]**. Earlier, `[ctrl+0x7C]` p0 bit 1
  (store `0x2001100C`, also the players' `[+0x20]`) restricts the same way **[asm; meaning unknown]**.
- **slim's hook `button_press` is the entry of `0x08033320`**, before both checks **[slim]**, and already sees Shift +
  Drum 3 / Drum 4 on the device (SL00D / SL01D `diag_ram` / `diag_upper`, ids 6 / 7) **[device, slim]**.
- `page.c`: `page_on_button` opens on `id < TRACKS && chord_shift_held()` (TRACKS = 4), closes on `id < 8`, Preset,
  Note, Mixer, FX. `page_open` = select track + set view, then `page_visible()` → `chord_visible_view()`, which requires
  active == container, mode 1 or 6, `track_of < 4` and the Note-view vtable `0x0805A064` **[slim]**: a drum view always
  fails it, so today a drum track never shows a page. Drum pages need their own visibility test (container active,
  `track_of` 4-7, mode 1 and / or 6, vt `0x0805ABBC` / `0x0805AD44`) and ids 4-7 added to the open rule; diag builds'
  Shift + Drum 3 / 4 must not be in the same build (they are diagnostic-only, ui-map).
- **LEDs:** stock's LED task `0x08034196` fills 69 entries from nine sources through the map `0x08059438` **[asm]**:
  entries 0-31 = the active view's pads, 51 / 52 = its elements 32 / 33, 60-67 = elements 34-41; **32-44 = source 1
  (`[ctrl+0x58]`) elements 0-12** → 32-39 are the eight track buttons in id order, so **Drum 1-4 = panel LEDs 36-39**
  **[asm; naming by id order]**. slim's `led_task` hook runs after stock on both callers (`0x08033B46`, `0x0803415A`) and
  overwrites `out[]` **[slim]**: `page_draw` paints pads 0-31 and 51 / 52 over whatever view is active, so it draws over
  a drum view unchanged; `page_shift_leds` writes 32-35 only (extend to 36-39). Drum views keep a persistent LED buffer
  that stock repaints only on state changes **[upstream drumnote.py]**: irrelevant, slim overwrites the final frame.
- `ctrl_pad_press` / `ctrl_pad_release` (`0x08033282` / `0x080332CE`) see every pad in every view **[slim]**, so a drum
  page can take pads exactly as the note pages do. Note stock's Shift + sample pad = silent selection (above): a
  drum Quick view on Shift + pads 17-32 in mode 1 would take stock's Shift function there.

## 3. Prior art in upstream (395d9e6)
| Tool (build) | Hooks | Timing | Hit / record | Bugs NOTAS reports |
|---|---|---|---|---|
| `rollers.py` (SC42.4 / Beta 1.14; v2 SC42.5, free SC42.7, sync SC43, noteoff SC43.1, mute SC43.7) | vt patch of the expanded view `0x0805AD44` slots 0 / 1 / 7 (rows 1-3 = 24 roller pads: per drum two columns, micro steps 1-3 / 4-6; mask per drum in the record tail + 956); drum players' slot 2 → `c_rlplay` (stock's first); both LED-task calls; mute: branch `0x0804A632` → `c_rlmute` | playing: the player's own micro-step calls (sequencer tick, Main task, the drum's sync-rate grid, swing included); stopped (`use_free`): the **LED task** with its own clock on HAL ms `0x2000081C` (micro step = 40000 tps / (6 BPM) in 1/16 ms, Drum 1's sync rate, ≤ 6 per call) | hit through the **player's** sink `[+0x4C]` (off first if `[+0x59]`, vel = step's or 100): playback route, **not recorded by stock**; v2 writes the micro-step bit (and vel 100 on an empty step) straight into the pattern when Record is armed | SC42.4 on the device: "worked once, not recorded": masks cleared each frame for drums 2-4 (subview ids 8 apart, not 9) → v2 clears after 200 ms without the view drawn **[device report]**; SC43: raw pattern writes undone by the drum **edit store** on the next stock edit → `drumstore` sync; SC43.1: stopped hits got no note-off (boxes white, MIDI note hung, reported on the device) → 100 ms note-off from the LED task; SC43.7: Mixer-muted drum: the player skips the step, rollers silent (device report) → `c_rlmute` |
| `drumarp.py` (SC42.8; rec SC42.9; sync SC43; noteoff SC43.1; rateflip SC43.7) | sample / Preset view `0x0805ABBC` slots 0 / 1 / 7 (2nd+ held sample pads start the arpeggio, not stock's); Pattern Settings `0x0805AB4C` slots 0 / 7 (Shift + pad 25 on, 27-32 order, 17-24 rate; per drum and pattern in tail + 600); players' slot 2 (chained after `c_rlplay`); LED task | playing: on the drum's micro steps when ((6·step + micro) × tps) mod (6 × arp ticks) == 0; stopped: LED task, next time += 2500 × ticks / BPM ms | sample through the player's `[+0x50]` setter, hit through the player's sink; rec: micro-step bit, sample flip `+0x40+step` (one a step), vel + prob 7 on an empty step, only playing with Record and not in count-in | SC43 store sync; SC43.1 no note-off when stopped; SC43.7 rate pad order; ends when the view is not drawn for 200 ms. No device report found |
| `drumnote.py` (SC21.3) | expanded view slots 0 / 1 / 7: pads 25-28 forwarded as 29-32, LEDs copied | — | stock's | (mirror option SC23.4) |
| `drumrep.py` (SC34) | **not note repeat**: drum *replace* (captured sample into a drum), Preset view slots 0 / 7 | — | — | SC37.6 moved Shift → Clear (Shift + pad is stock's silent selection) |
| `scdrum.py` (SC42.5) | Sidechain drum pages, K1-K4 | — | — | not relevant to repeat |
| `drums18.py` (SC18) | automation-recorder hook `0x0803FF02` (chromatic pitch recorded on its step only), drum macro handler vt `0x0805AADC` slot 4 (knobs) | — | — | not relevant; documents drum recorders vt `0x0805A578` |

Device status: rollers worked while playing in SC42.6 ("modo roll ... ahora funciona") and their stopped / muted bugs
were found on the device (SC43.1, SC43.7) **[device, upstream reports]**; the drum arpeggiator has no device report;
every heading from SC39.7 on still says pending (VERSIONS.en.md).

**slim's own clocked retrigger (PL06 arp, `slim/features/chord/arp.c`)** **[slim; device-verified PL06 / PL07, external
MIDI clock untested]**: `seq_tick` (`0x0802C418`, Main, 24 PPQN with swing) counts `arp_tick` and only marks steps / gate
ends as due; the next `main_ms` slot-0 heartbeat (1 ms, Main, before Main takes the DSP lock) sends them, so the
recorder has counted the tick first; `seq_start` resets the grid at tick 0; stopped, a 1 ms accumulator (+BPM per ms,
threshold 50 × swing) makes ticks. Notes go through the track's sink with the held pad as source; note-offs from the
sounding set, never recomputed. This is the right base for note repeat (not upstream's LED-task clock, which runs in the
UI task).

## 4. Voices and retrigger
- **One voice per drum, monophonic.** Stock's DSP drum voice (core 0, `P:$20B3`, per drum trigger `$9F + d`, state
  `$1E8D + $12 d`): envelope starts at the velocity and only decays (no attack); **if the current level is above the new
  velocity, the hit does not retrigger** **[upstream NOTAS SC41.7, DSP code read]**. Note repeat with falling or soft
  velocities at fast rates can be swallowed while the previous hit is still loud.
- ARM side: a new hit of a sounding drum is ended first (player slot 2 note-off then note-on; router `0x080325AC` ends a
  taken note, and for live input also sends the recorder gate a note-off) **[asm]**. Drum note-offs only matter for the
  LEDs (white boxes), MIDI out and the router / recorder bookkeeping; the sample plays out by its decay **[guess]**.
- A drum step holds one velocity, one sample flip and a 6-bit micro-step mask **[asm, 0x0804AA08 / 0x080411CA]**: a
  recorded repeat inside one step shares one velocity and one sample.

## Open questions
1. Which router stage feeds index 29 (the recorder gate) for live drum input, and does a hit sent through the expanded
   view's sink from the **Main** task record like a finger press (emulate: transport playing + Record, `note_sink_on`
   on `0x200434E8`, check the drum pattern's micro-step bits and the edit store)?
2. Does the drum recorder honour record quantise (`[rec+0x35]`) for micro steps (quantise on: every repeat lands on micro
   step 0 and repeats faster than a step collapse into one hit)? Does it record a sample flip for a live hit from a
   non-selected sample pad?
3. Does the drum recorder ignore a re-hit of a note it still holds (the SC43.2 note-track behaviour, same slot-0
   function `0x0803FC5E`)? Repeat must send each note-off before the next note-on to be safe.
4. Mode 0 / 1 / 8 and the sample view: how a 0-15 pad maps to the 32-per-page sample index in mode 1, and what the 300 ms
   timer in `0x0804D934` does.
5. `[ctrl+0x7C]` p0 bit 1 (store `0x2001100C`): which state restricts buttons / pads (and skips players' steps)?
6. Pad pressure: is there a per-pad pressure route (for repeat velocity by pressure, as on Circuit Rhythm)? Not found in
   the controller vtable (slots 5 / 6 `0x08033878` / `0x08033870` not traced).
7. Tempo: upstream's stopped clocks read `param_get(0x20011404, 1)`, slim reads param 0 as BPM; one of them is off (slim's
   is device-tested in PL06, so probably param 1 is something else).
8. Does stock do anything with ▲ ▼ (19 / 20) or 1-16/17-32 (21) on drum views (pages claim ▲ ▼ while open)?

## What CTPlay drum pages + note repeat would need
**Pages (Shift + Drum 1-4):**
- `button_press`: open on ids 4-7 with Shift (same three stock calls; they already cover drums), close as now.
- A drum visibility test (container active, `track_of` 4-7, mode 1 and / or 6, class `0x0805ABBC` / `0x0805AD44`); the
  container mode is one byte for all tracks, so opening a drum page from a note track lands in whatever mode is current
  (decide: accept every drum mode, or set mode 1 / 6 first, e.g. by replaying a Note press: check in emulation).
- `ctrl_pad_press` / `release` and `led_task` handlers as today; `page_shift_leds` → LEDs 36-39; per-drum state for 4
  more "tracks" (RAM, ITCM, saved block: drum fields must go in block 2, the 56 B block 1 is full for older builds).
- ui-map: Drum 1-4 with Shift become claimed; Shift + sample pad stays stock's silent selection.

**Note repeat:**
- *Input (which drum is held):* entry hooks on the drum views' handlers, all 4 bytes, no PC-relative code in them
  **[asm]**: expanded view press `0x0804ED50` (`1c2938b5`) / release `0x0804ED68` (`1c290a46`); sample view press
  `0x0804D934` (`2de9fc41`) / release `0x0804DA38` (`f8b50646`); the sample view's hit `0x0804E0BA` (`70b50446`) and
  its end `0x0804E0E8` (`00f11001`, `add.w r1, r0, #16`); slimbuild's checker must still confirm no branch lands
  inside the displaced bytes. Alternatively watch
  `ctrl_pad_press` with the view test (one hook point, no new symbols) and let stock play the first hit. Releases must
  be caught on every path stock uses to release held pads when the view changes (as `pad_release` notes for the Note
  view): check the container's release-all on track / view change.
- *Clock:* reuse the arp clock: `seq_tick` + `seq_start` + `main_ms` (Main task). Rates in ticks: 1/4 24, 1/8 12,
  1/16 6, 1/32 3, triplets 8 / 4 / 2. Phase: from Play (arp) or from the press (Circuit Rhythm-like); decide.
- *Hit:* `note_sink_on(sink, d + 1, vel, src)` / `note_sink_off(sink, d + 1, src)` on a **live** drum sink (the expanded
  view's `[0x200434D4+0x10]`, or the drum's sample view `[[cont+0x8C+4d]+0x10]`), from the Main heartbeat, off before
  each on. This is the finger-press route: stock's recorder records it (to confirm, Q1-Q3) and writes the pattern through
  its own path, so upstream's edit-store problem (SC43) does not arise. Avoid the player's sink (playback route: not
  recorded, and it shares `[player+0x59]` with the sequencer). `note_sink_on` takes the DSP lock: never from the DSP
  tick; Main's heartbeat is where PL06 already calls it.
- *Muted / count-in:* the player skips muted tracks, but live hits through the router still sound (stock lets you play a
  muted drum? check); the recorder gate drops hits in the count-in.
- *Stopped:* the arp's 1 ms accumulator; every hit needs its note-off (SC43.1's white boxes / hung MIDI note).
- **Phantom-press rule:** the pad press only records "drum d held, velocity v, pad p" and lights LEDs; no pattern write,
  no loop, no `slim_irq_save()` beyond a few instructions on the press. All hits come from Main. A "write the repeats
  into the pattern" action (if any, e.g. a Pattern tools page) runs on the pad's release.
- *Risks:* the DSP voice swallows a softer re-hit (section 4); record quantise may collapse sub-step repeats; the
  router / recorder tables are touched from UI (finger presses) and Main (repeats) without a lock (PL06's arp has the
  same exposure and passed on the device); MIDI out sends a note per hit (fast rates = dense MIDI, but well under the DSP
  rate limit: 1/32T at 180 BPM ≈ 36 hits / s); external MIDI clock untested for the arp clock.
