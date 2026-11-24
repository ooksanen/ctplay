# CTPlay 1.0 beta 2 (PL22): two fixes, no features

Approved by the user 2026-11-22 (beta 2 before the public launch; both fixes and the Written ruling below).
PL22 = PL21 + the two fixes. Nothing else changes in the image; no saved field, no link change, no new control.

## 1. CC 27 on channel 16 crashes stock (new feature `stockfix`)

**The bug** (stock 1.2.1; found by upstream, RC4.20 / Alpha 7.14 `tools/cc27fix.py`, 2026-11-20, the crash reproduced
in emulation on stock and on the device): a CC 27, or NRPN 1:27, on the project channel (16) makes `0x08022094` set
bit 3 of `[0x20006A0C + 1]` (type `0x21`, index 12; descriptor `0x080598E8` entry `0x14`). The main loop's master-group
send `0x08021578` handles one set bit per call through the table `0x080215B8`, which has three entries; bit 3 takes a
fourth word that is code (`0xD0002800`): MemManage fault, the device hangs. A **Circuit Rhythm** sends NRPN 1:27 on
channel 16 when its −12 dB trim is toggled in the sample-record view, so a Rhythm wired to a Tracks can crash it.

**The fix:** upstream's, two bytes. The bit-3 test's `bmi 0x0802158A` at `0x080215B2` (`EA D4`) becomes
`bmi 0x08021594` (`EF D4`): the code that clears the handled bit and returns, without the call. Bits 0–2 are unchanged.

**Why a byte patch:** an entry hook at `0x08021578` cannot work (its second instruction, `ldr.w r4, [pc, #0xa50]`, is
PC-relative) and a hook anywhere else costs more than the fix. slimbuild gets a small byte-patch mechanism:

- `feature.toml` gets `[[patch]]` tables: `addr` (int), `stock` and `new` (hex strings, same length, 2–16 bytes),
  `why` (one line). A feature may have no sources (`sources = []`, budgets 0).
- The build refuses: `stock` not equal to the official image's bytes at `addr`; `addr` odd, outside the stock image or
  below the app base; `stock` / `new` of different lengths or empty; a patch that overlaps another patch or any hook
  site the version uses (entry / mid: `[addr, addr + displace)`; call: `[site, site + 4)`).
- The patches join the hooks' list, so `image.assemble` writes them and the manifest's `patches` lists them.
- Feature `stockfix` (`features/stockfix/`, no sources): the one patch above. Later stock fixes join it.
- Earlier version files do not list `stockfix`: every tag and pinned build rebuilds unchanged.

**Tests:** the loader and every refusal (unit); the PL22 image has `EF D4` at `0x080215B2` and differs from the same
build without `stockfix` only there; **emulation through the real MIDI route**: CC 27 = 127 on channel 16 delivered
the way stock receives MIDI, then the main loop's send: on PL21 the call to the fourth table word happens (the bug is
reproduced in emulation), on PL22 the bit is cleared with no call and the loop goes on; a CC on an index that stock
handles (bits 0–2) still reaches its handler.

## 2. A Written roll from a step outside the pattern lands inside the loop (`roll_step`)

**The bug** (followups "From the PL19 build"): pattern strum Written; a chord entered on a step outside the pattern's
first..last (e.g. before a later start step, or step 32 of a pattern that ends at step 31; not steps 17–32 of a
16-step pattern: pressing 1-16/17-32 makes stock lengthen it to 32 steps, found in PL22's device run). The chord's first
note goes into the held step, which never plays, and `roll_step` (`roll_math.c`) wraps the rest of the roll by modulo
into the loop: the user hears notes on steps they never touched.

**Ruling (user, 2026-11-22):** from a step outside first..last the roll **carries straight on**: step + 1, + 2, … as
the step pads show; a note past step 32 is dropped. Inside first..last nothing changes (it wraps within the loop, as
the guide says).

**The fix:** `roll_step`: `step < first || step > last` → `step + add`; the callers already skip a target `>= STEPS`
(`step_entry.c` x2, `pstrum_rec.c`). Live recording records at the playing step, which is inside first..last, so it
does not change.

**Tests:** `roll_model.py` (the reference) and the C comparison; emulation, through stock's own presses (Pattern Settings,
1-16/17-32): Written step entry on step 2 before a start at step 5 puts the roll on 2, 3 (none inside 5–16), a roll
from step 32 with the end at step 31 drops what passes step 32, and 1-16/17-32 on a 16-step pattern makes it 32 steps.

## Device test (PL22 `TEST.md`, short rows, one press group each)
CC 27 from the computer on channel 16 while playing and stopped (no hang); a CC that stock handles still works; a Circuit
Rhythm's trim toggle if the user has one; the Written roll from step 2 before a start at step 5 and from step 32 with the end at 31; a short
smoke pass (a chord, the arp, a drum Write, a save and load) on PL22. Estimated time stated.

## Docs
The guide's version table (PL22 = 1.0 beta 2), the pattern strum section (a roll from outside the loop carries on),
candidates.md (CC 27: done), followups.md (the Written item: done), README, CLAUDE.md.
