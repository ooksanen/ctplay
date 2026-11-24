# A phantom press on the next pad (PL11 Undo, PL13 draft) — investigation

Date: 2026-10-20 · Builds: `PL11`, `PL13` (first test build) · Status: **fixed in PL13** (commit `92070d6`, passed on
the device 2026-10-20): every pattern write runs on the pad's release, not its press. The exact stock mechanism is not
traced; the fix does not depend on it.

## What was seen on the device

- **PL13, in a draft** (every press on Pattern tools / Melody re-writes the pattern): pressing Melody's order pad 3
  (down) lit pad 3 for a moment, then the selection jumped to pad 4 (up-down), and the line was written as up-down.
  Random, roughly every other press, **always the next pad**. Outside a draft (no write) about 30 presses in random
  order all landed right.
- **Undo** (pad 31), outside a draft: about half of ~15 presses armed the Write (pad 32 started blinking). Undo is
  PL11's code: the user had seen Write blink after Undo on PL11 and read it as "press Write after Undo" (the PL11 test
  plan's wording took the blame then).
- Emulation does not reproduce it: the emulator has no pad scanner (the same press sequence stored the right order).

## Why (working explanation)

- The board reads the pads through a **74HC4051 8-channel analog multiplexer** into the STM32's ADC (ctre
  `Documentation/Components.md`): the pressure of one pad at a time, the channel switched in software.
- The writes that showed it ran **inside the pad-press handler with interrupts masked** (`slim_irq_save`: the Undo swap
  of 0x380 B, a draft re-write of 32 steps), then called stock's `rec_touch`. That is thousands of cycles with the
  scan's interrupts held off while the finger is still on the pad.
- A delayed scan stores the held pad's pressure in the next pad's slot: the firmware sees a second press on pad + 1.
  This matches every observation (next pad only; random; only presses that write; Write on pad 32 never showed it:
  there is no pad 33).
- Every other masked section in slim is a few instructions (a flag, a few bytes); upstream masks interrupts only for a
  4-instruction read-modify-write (`tools/srcview.py`) and writes patterns without masking.

## Fix (PL13)

- The press changes the setting and its LED; the write (Write's second press, Undo, a draft re-write) is pending and
  runs on **that pad's release** (`euclid_release`, from `page_on_release`). With no finger down, a shifted reading is
  zero: nothing can land on another pad.
- One pending action (`act`, 2 B RAM: kind, track, pad); dropped on a page close, another track's pages, a project
  load, a link write, any button press (`euclid_disarm()`).
- Device check: `firmware/PL13/TEST.md` steps 7d (Undo ×15: Write never arms) and 8b2 (order pads in a draft: the
  pressed pad stays lit). Both passed.
- Rule added to `CLAUDE.md`: no long or masked work while a pad is pressed.

## Open

- Not traced: which stock code (the timer / DMA handlers near `0x08057508` look like DMA status handling) sequences the
  multiplexer, and whether `rec_touch` or the masking alone is enough to cause it.
- A second finger still holding another pad during a release-time write could still be misread (not seen).
- Cleaner: keep the sequencer out without masking interrupts (suspend the RTOS scheduler only, if the sequencer never
  runs from an interrupt): needs stock's scheduler entry points first. Then writes could also run on the press again.
