# Pattern strum spike scripts (2026-10-31, throwaway)

Emulation scripts behind [the PL19 spike findings](../2026-10-31-pattern-strum-spike.md). Not tests: they print what
they found; each `.out` beside a script is its output at the spike's commit. Run from `slim/` with
`PYTHONPATH=.:tests:../tools:docs/investigations/2026-10-31-pattern-strum-spike
../.venv/bin/python docs/investigations/2026-10-31-pattern-strum-spike/<script>.py`. `lib.py` builds PL18 from the
current sources into `pl18/` beside it on first use (not committed; at the spike's commit the sources are PL18's).

- `lib.py`: the harness (NoteHarness + the track 0 recorder's placement, note-off, tick pass and commit with task, ms
  and stock call site) and `Route`, a Python model of route (a): the pending word rewritten at the commit's entry.
- `q1_baseline.py`: what PL18 records for a live strum (the recorder's calls in order). `q1_route_a.py`: route (a) over
  Played / Written, quantise on / off, three speeds, both directions, wrap, full step, early release, naive unit,
  mono. `q1_mono_order.py`: mono record against a falling roll with a bass. `q1_route_b.py`: the placement's arguments.
  `q1_tasks.py`: the task, call site and transport state of every commit of a strum's notes (release, tap, Stop,
  Record off, two pads sharing a pitch). `q1_scope.py`: the plan's Task 4 rule (identity at the send; moves at the two
  commit sites: the heartbeat's `inflight`, the pass's tickets) over held, tap, stale-latch, freed-slot, two-pad,
  resound-order, re-press, Stop, ticket-expiry and arpeggiator cases.
- `q3_probe.py`, `q3_held.py`: the Note view's, the recorder's and the step editor's stores; the held step's pattern
  and step. `q3_spill.py`: a raw spill write and the store touches.
- `q4_player.py` (marks, held ties, lengths, resets, batch flag), `q4_batch.py` (the batch flag with the synth note-on
  running: tests/voices.py), `q4_resets.py` (what reaches the player's end-all), `q4_tick0.py` (the task of step 0).
