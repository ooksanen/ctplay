# Drum spike scripts (2026-10-25, throwaway)

Emulation scripts behind [the drums research](../2026-10-25-drums.md), "Emulation results". Not tests: they print
what they found. Run from `slim/` with `PYTHONPATH=.:tests:../tools:docs/investigations/2026-10-25-drums-spike
../.venv/bin/python docs/investigations/2026-10-25-drums-spike/<script>.py`.

- `drumlib.py`, `probe*.py`, `q1_*.py`, `q2_*.py`: the write path through the drum editor's step store, the view mode,
  the mirrored pattern (stock image).
- `lib2.py`, `r*.py`: note repeat sent through a live drum sink, recorded by stock (stock image; `r7_pl15.py` builds
  PL15 into `pl15/` beside it, which is not committed).
- `u1_refresh.py`, `u2_override.py` (+ `.out`), `u3_window.py` (+ `.out`): record quantise for the drums (PL16's
  unquantized repeats; stock image and a patched copy). A drum recorder reads only `[rec + 0x35]` (1 = quantise), a
  cache of `!(bit 12 of parameter 2 of the settings store 0x200111CC)` read through `[rec + 0x24]`. Only the constructor
  and the store listener `0x0803FE24` write it (`eor.w r0, r0, #1` at `0x0803FE8C`, `strb r0, [r7, #1]` at
  `0x0803FE90`, r5 = the recorder, r7 = rec + 0x34), once per step at its tick 0 while the clock runs, each drum on its
  own sync; slot 5 runs later in the same listener call and reads the fresh value. Shift + Record flips bit 12 at
  once; the cache follows at the next step boundary. The listener is shared with the note recorders. Writing the byte
  from the 1 ms heartbeat alone puts hits in the tick-0 window one tick late (`u3_window.out`); overriding the value at
  `0x0803FE8C` for the drum recorders, with stock's last value kept and put back at the end, lands every hit exactly as
  stock's own quantise off does (`u2_override.out` S3-S6, `u3_window.out`). Not checked on the device.
