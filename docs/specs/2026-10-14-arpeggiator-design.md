# Arpeggiator and play page (PL06) — design

Date: 2026-10-14 · Branch: `slim` · Version: `PL06` (CTPlay) · Status: design agreed with the user section by section
2026-10-14, spike done (findings below); spec for review

## Purpose

Hold pads in a Note view (Synth 1 / 2, MIDI 1 / 2) and the track plays their notes one after another, in time with the
project: the arpeggiator people buy patch packs to fake. It plays the notes of every held chord (so a chord pad becomes
an arpeggiated chord, and with chords off it is a classic arpeggiator), follows the project tempo and swing whether the
sequencer is playing or stopped, and records like played notes. Its settings, and strum's, move to a **play page**.

Success:
- Every pattern plays its documented order over 1-4 octaves, at every rate, playing (on the sequencer's ticks, swing
  included) and stopped (from the project BPM).
- Recorded arpeggios at 1/4, 1/8, 1/16 and dotted 1/8 play back as they were played, also on the official firmware.
- With the pattern off, everything is as PL05, except that strum is set on the play page (Shift + 1-16/17-32 goes
  back to doing nothing, as in stock).
- Nothing is left sounding after any mix of pads, page, view switches, Play / Stop and latch.

## Decisions

| # | Decision | Reason |
|---|---|---|
| A1 | **Input = every held chord on the track**: each held pad's own note plus its chord notes, merged, duplicates dropped | One pad gives an arpeggiated chord; several pads merge into one arpeggio; chords off gives a classic arpeggiator (user choice) |
| A2 | **Grid-locked** on a 24 PPQN tick count: a note on every tick where `tick % rate_ticks == 0`; the first note waits for the next grid point | As a synced hardware arpeggiator: in time with the pattern, not with the moment of the press |
| A3 | **Playing: the sequencer's own ticks** (hook on the tick); tick 0 at stock's start. **Stopped: an own tick count from the project BPM**, swing included | The sequencer ticks only while playing (spike); its tick timing already carries swing (spike), so counting its ticks swings with the pattern for free |
| A4 | **Rates**: 1/4 · 1/8 · 1/16 · 1/32 plus two exclusive modifiers, **triplet** (×2/3) and **dotted** (×3/2); dotted 1/32 (4.5 ticks) is off the grid: the dotted pad does nothing with 1/32 | All others are whole ticks (table below); 6 pads instead of 11 (user's layout). If the page ever fills, the two modifiers become one pad cycling regular / triplet / dotted |
| A5 | **Patterns** (8 pads): off · up · down · up-down · down-up · random · as played · chord | The usual set; "chord" repeats all held notes at the rate |
| A6 | **Octaves** 1-4 (the notes repeated up to 3 octaves up, out-of-range notes left out); **gate** short 25 % · medium 50 % · long 80 % · legato (the next note-on before the previous note-off) | Pattern a must, octaves and gate close seconds, latch last (user priorities); all four fit (RAM below) |
| A7 | **Latch**: with latch on, releasing every pad of the track keeps the arpeggio going, also while another track or view is on screen, so several tracks can arpeggiate at once; the next press on that track after all its pads were let go replaces the latched notes; latch off or pattern off stops it | The common latch; recording also keeps an arpeggio without latch; play along on another track (user, 2026-10-14) |
| A8 | **Play page** (**Shift + the track's button**: Synth 1 / 2, MIDI 1 / 2; the button alone goes back to the track's normal view): all 32 pads pick that track's play options; strum's speeds move onto it (the Shift + 1-16/17-32 cycle goes) | Every option is per track, so the track's own button opens it (user); the Shift palette is full (pads 17-32); one press per option, LEDs show the settings. Rule for later features: **Shift + any track button = that track's CTPlay page** (drum features would use Shift + Drum N) |
| A9 | **Arpeggio and strum exclude each other**: with a pattern on, the track's strum is ignored and its row shows off | Both drive the same held notes over time |
| A10 | With a pattern on, a key-pad press is **HANDLED**: stock plays nothing; the arpeggiator plays the pad's note in turn | The pad's own note is one of the arpeggio's notes |
| A11 | **Recording** as played; stock snaps live notes to the step grid, so 1/4, 1/8, 1/16 and dotted 1/8 record faithfully, triplets, 1/32 and dotted 1/16 are performance rates | PL02 device test 14 (strums record on steps); user: tuplets as a performance option |
| A12 | **Not saved**: everything off at power-on | As the chord settings (C3); recordings do not depend on them |
| A13 | **In the chord feature**: new sources `arp.c` (engine) and `page.c` (play page), an internal header `chord_held.h` sharing `held[]` | The arpeggiator reads the chord engine's held table; one feature keeps that internal. `PL06`, no diagnostic twin |

**Rate in ticks** (24 per quarter note; a bar of 4/4 = 96):

| | 1/4 | 1/8 | 1/16 | 1/32 |
|---|---|---|---|---|
| straight | 24 | 12 | 6 | 3 |
| triplet | 16 | 8 | 4 | 2 |
| dotted | 36 | 18 | 9 | — |

## Findings this design rests on

Spike 2026-10-14 (emulation on the stock image; throwaway probes, not kept), plus upstream `docs/NOTAS.md` and the
event-queue spike (`specs/2026-10-12-strum-design.md`).

- **Tempo**: project tempo store `0x20011404` (`[[[0x200069E4] + 0x48] + 0x48]`, upstream): `param_get(store, 0)` =
  BPM, a whole number (94 in the RAM dump), `param_get(store, 2)` = swing (50 = straight). The store is double-buffered;
  read it through `param_get` (`0x0803542C`), never a buffer directly (the dump's two buffers hold 120 and 94). A
  committed change (`0x080354FA` + `0x080353C0`, as the Tempo view) takes effect at once: measured ticks every 20.8 ms at
  120 BPM, 41.7 ms at 60 BPM, 26.6 ms at 94 (`2500 / BPM` ms).
- **Stopped, stock keeps no tick phase**: the clock `0x0802A3F8` (object `0x20011364`) only counts milliseconds
  (`[+0x64]`); nothing else in its state moves.
- **The tick**: `0x0802C418(engine)` with engine = `0x20038EC0`, reached by a tail call from the listener
  (`0x0802B8FC`), in the Main task's 1 ms service, after the `main_ms` dispatcher's entry. Its arguments carry no
  position (`r1 = 0, r2 = 1` every time): the arpeggiator counts ticks itself. Entry `2de9f041` (`push.w {r4-r8, lr}`):
  movable, 4 bytes.
- **The start**: every Play press that starts the sequencer calls `0x0802BFE0` then `0x0802C008(engine)` from the Play
  handler (`0x0802BBAA`, UI task); the latter plays tick 0, and the first hooked tick follows one tick period later.
  Each start restarts; stopping (Play again) calls neither. Entry `2de9f34f` (`push.w {r0, r1, r4-r11, lr}`), 4 bytes.
- **Swing is in the tick timing**: at swing 70 a step's 6 ticks were 37 ms apart, the next step's 16 ms (94 BPM; the
  pair of steps keeps its length): the first step of each pair takes `s` % of the pair, the second `100 - s` %.
- **All 32 pads**: the controller's pad press `0x08033282(ctrl, pad, vel)` and release `0x080332CE(ctrl, pad)` see
  every pad (the tests' real route); the Note view's key-pad hooks never see the 2-row view's step pads. Entries
  `70b50646` (`push {r4-r6, lr}; mov r6, r0`, 4 bytes) and `30b4d0f88420` (`push {r4, r5}; ldr.w r2, [r0, #0x84]`,
  6 bytes). The release acts only for a pad whose bit is set in `[ctrl + 0x84]`, which the press sets: a press the page
  takes never reaches stock, so its release is skipped by stock too.
- **External MIDI clock** (open, not testable in emulation): the clock has several source modes (`[+0x56]`); whether
  ticks under external clock still pass through `0x0802C418` is checked on the device (test plan), and stopped mode then
  runs from the project BPM.

## 1. Foundation

New hook points in `stock/symbols.toml` (all `kind = "entry"`):

| Name | Address | Expect | Displace | Args | Context |
|---|---|---|---|---|---|
| `seq_tick` | `0x0802C418` | `2de9f041` | 4 | `void *engine` | `main` |
| `seq_start` | `0x0802C008` | `2de9f34f` | 4 | `void *engine` | `ui` |
| `ctrl_pad_press` | `0x08033282` | `70b50646` | 4 | `void *ctrl, uint32_t pad, uint32_t vel` | `ui` |
| `ctrl_pad_release` | `0x080332CE` | `30b4d0f88420` | 6 | `void *ctrl, uint32_t pad` | `ui` |

Data symbols: `tempo_store` (`0x20011404`), `play_store` (`0x20011034`, p0 = playing). No builder change is expected; the
plan checks the four entries pass slimbuild's hook checks.

## 2. The play page (`page.c`)

- **Open / close**: Shift + Synth 1 / 2 or MIDI 1 / 2 opens that track's page (pressed again, it stays open); the
  track's button without Shift closes it and goes to the track's normal view, as stock's press does (user). Stock drops Shift + track-button presses (the controller's Shift mask) and slim's `button_press` hook runs before
  that mask, as for Shift + 1-16/17-32 in PL02-PL05, so no stock function is lost. A track not on screen: the press switches to that track's Note view and opens its page.
  Stock's track-button case (`0x08033400`, reached from the press handler's `tbh` at `0x080333C4`) is three calls:
  `0x08043448(cont, id)` (the track container selects the track; `cont = [ctrl + 0x2C]` = `0x20040DB8`),
  `v = 0x0804348C(cont, 1)`, `0x0803390C(ctrl, v, id)` (the active view). Made from the hook with Shift held, they
  leave the controller and every LED exactly as a plain press does (spike, from the Mixer and between all four tracks).
- While the page is open, every pad press / release goes to the page (`ctrl_pad_press` returns HANDLED): pads play
  nothing; the page's own pads show it is open. Any track button without Shift, Note, Mixer, FX or Preset closes it
  and does what it does in stock. A pad held when the page opens keeps its stock release.
- Shift + Drum 1-4 and Shift + 1-16/17-32 stay as in stock (nothing).
- **Layout** (pads 1-32 from the top left; LEDs: the chosen option bright, the others dim, in one colour per row; codes
  picked in the plan from the steady palette and confirmed on the device):

| Row | Pads 1-8 / 9-16 / 17-24 / 25-32 |
|---|---|
| 1 | pattern: off · up · down · up-down · down-up · random · as played · chord |
| 2 | rate: 1/4 · 1/8 · 1/16 · 1/32 · triplet · dotted · (spare) · latch |
| 3 | octaves 1 · 2 · 3 · 4 · gate short · medium · long · legato |
| 4 | strum off · slow · medium · fast · (4 spare) |

- Triplet and dotted toggle and exclude each other; latch toggles. Choosing pattern off stops the track's arpeggio.
- **Settings** per track, 2 bytes: pattern (3 bits), base rate (2), modifier (2: none / triplet / dotted), latch (1);
  octaves - 1 (2), gate (2). Strum keeps `chord_strum`. Written by the UI task only, one byte at a time.

## 3. Arpeggiator (`arp.c`)

**Press / release (UI task).** With the track's pattern on, `chord_on_pad` fills a held entry as today (the chord's
other notes, its root, velocity, a new press-order byte) with the flag `HELD_ARP`, sends nothing and returns HANDLED.
Release frees the entry (nothing of its own sounds); with latch on it only marks it released, and it keeps playing,
on screen or not. The next press on the track while all its arpeggio entries are released frees them first (the new
press replaces them). The UI task fills and frees arpeggio entries; the Main task only reads them.

**Ticks.**
- `seq_start` (UI task) sets a start flag. The heartbeat (Main) sees it, sets `tick = 0` and steps every track.
- `seq_tick` (Main): `tick++`, then each track's step if `tick % rate_ticks == 0`.
- Heartbeat (Main, every ms): while the Play store is off, an own clock: `acc += BPM`; at
  `acc >= 2500 × swing_factor` a tick (`acc -=` that, `tick++`, step as above), with `swing_factor` = `s / 50` for ticks
  in even steps (`(tick / 6) % 2 == 0`) and `(100 - s) / 50` in odd ones (all in integers: thresholds `50 × s` and
  `50 × (100 - s)`). Playing to stopped carries on from the last tick.
- Then gate countdowns: each track's sounding note ends when its gate time has passed.

**A step.** Build the track's note list on the stack: every live `HELD_ARP` entry (not freed; latched ones count),
the pad's own note and its chord notes, each with its pad and velocity; drop duplicates (first entry wins); order rising,
or by press order for "as played" (an entry's root first, then its notes rising). With octaves `k`, the list repeats at
+12, +24, +36, dropping notes outside the playable range. Then the pattern picks the next index from the track's
position (`pos`), which advances each step:
- up `pos mod N`; down `N - 1 - pos mod N`; up-down and down-up bounce without repeating the end notes (period
  `2N - 2`, `N > 1`); random: a 16-bit LFSR, a different note than the last when `N > 1`; as played: as up, over the
  press-order list; chord: all notes of one octave of the list, the octave cycling.
- The list can change between steps (pads pressed or released): `pos` carries on, taken modulo the new length.
- Send the note(s) with `send_on` (the voice floor applies) from the note's own pad; end the previous note now when
  its gate passed, after the new note-on for legato.
- **Gate time** = gate % × the rate's period in ms (`rate_ticks × 2500 / BPM`); legato = until the next note.

**Run state** per track (Main only): `pos`, octave / direction bits, the gate countdown (ms, 16 bits: up to 36 ticks
at 40 BPM is 2.25 s) and the **sounding set**: up to 5 (note, pad) pairs (the "chord" pattern sounds up to 5 notes at
once; the others one, two in a legato overlap). Notes are always ended from this set, never recomputed from the list,
which may have changed since: nothing can stick.

**Ending.** Pattern off ends the sounding note(s) at once (the heartbeat); the last entry freed (latch off, or the
last pad let go without latch) ends them at the next step, or at their gate if sooner. Leaving the track's Note view
does not stop a latched arpeggio (A7). Notes are always ended from their own pad.

**With the chord engine.**
- PL05's re-sound and `owned()` skip `HELD_ARP` entries (their notes are not held sounding).
- `draw_chords` lights, for arpeggio entries, the pad(s) of the sounding note(s) only, in white (`0x01`): stock draws
  no pressed colour for a press the arpeggiator takes (HANDLED), so there is no source-pad colour to copy.
- With a pattern on, the track's strum is ignored (A9).

**Task safety** (strum's rule S5): every sink call for an arpeggio comes from the Main task (heartbeat or `seq_tick`,
which run one after another); the UI task writes entries (count last), the released flag, settings bytes and the
start flag. A note-on can follow a release by at most one step and is ended on the next heartbeat; nothing sticks.

## 4. Budgets

| | RAM |
|---|---|
| Settings, 2 B × 4 tracks | 8 B |
| Run state: pos, bits, gate (4 B) + sounding count and 5 (note, pad) pairs (11 B), × 4 tracks | 60 B |
| Tick count (4), clock remainder (2), LFSR (2), page track / flag (1), start flag (1) | 10 B |
| Press-order byte in `held_t`, 1 B × 6 | 6 B |
| **Total** | **about 84 B: PL06 ≈ 188 of 240 B** (a shared sounding pool would save about 30 B if needed) |

Stack: the note list (up to 30 notes + their pads, before octaves are applied on the fly) on the heartbeat / tick path,
about 64 B more; Main has ≥ 1.5 KB free (SL00D). Flash is not a limit (PL05 3,908 B).

A future diagnostic twin with the voice log (236 B in PL04D) would need the log ring shrunk to fit.

## 5. Testing

- **Foundation**: the four hook points build and their stubs run (codegen / emulation); SL00D and PL05 rebuild
  identically.
- **Emulation** (NoteHarness / VoiceHarness, real routes; the emulated clock ticks while playing):
  - page: open / close (and by view switch), every option's bits, its LEDs (dotted off with 1/32, strum row), pads play
    nothing while it is open, a pad held across opening;
  - order: every pattern over 1, 2 and 4 octaves, one chord, two merged chords, chords off, a pad added and released
    mid-arpeggio;
  - timing: stopped at 94 BPM, each rate's period within 1 ms, with swing 50 and 70; playing, notes on the sequencer's
    ticks and tick 0 at the start; a BPM change through the store's commit;
  - gate: each length's note-off time; legato's note-on before note-off;
  - latch: release keeps it going (also on another view), the next press replaces, latch off / pattern off stops it;
    two tracks at once (one latched);
  - recording: arpeggio notes reach the recorder;
  - nothing left on: a fuzz over pads, page, view switches, Play / Stop, latch;
  - transparency: pattern off = PL05, except Shift + 1-16/17-32 (now stock: nothing) and Shift + Synth / MIDI
    buttons (the page);
  - Shift + a track button: opens that track's page (on screen and, if the switch is clean, not on screen); Shift +
    Drum buttons and Shift + 1-16/17-32 as stock.
- **Device** (`firmware/PL06/TEST.md`): each pattern by ear against the metronome, playing and stopped; rates incl.
  triplet / dotted; swing; octaves, gate, latch; an arpeggiated chord; two tracks at once; recording and playback;
  external MIDI clock (if available).

## Not in scope

- Saving the settings; per-step arpeggio editing; arpeggios on drum tracks.
- Recording triplets faithfully (needs the pattern writer and microsteps: "Recorded strum" in `candidates.md`).
- Tempo-synced strum (strum stays in milliseconds).
