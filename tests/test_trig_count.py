"""PL20 Task 4: the passes' counts (trig_count[track][pattern]): one per pass, counted where a track's pattern ends,
started over by the user's choices (Play from stop, a pick by hand, a scene recalled by hand, a load), kept by
Shift + Play and by a chain advancing by itself. Plan 2026-11-07-trig-conditions.md, Global Constraints "Counting" and
"Two-task rule"; evidence docs/investigations/2026-11-01-trig-conditions-spike/B-counting.md and
2026-11-07-trig-conditions-spike.md (Q1, Q3).

Every project here is unmarked (trig_mark 0): the counts count in marked and unmarked projects alike."""
import pytest
from unicorn import UC_HOOK_MEM_WRITE

from trig import (MIXER, PATTERNS_VIEW, TRACKS, TrigHarness, expected_pass, loops, trig_setup)

pytestmark = pytest.mark.emu

# b_1_pass.py's scenarios: {track: dict(chain=(first, last), pats={p: (last, first, rate, direction)}, mute)}
SCENARIOS = {
    "loops": ({t: dict(chain=(0, 0), pats={0: (15, 0, 3, 0)}) for t in range(8)}, 300),
    "chains": ({
        0: dict(chain=(0, 1), pats={0: (15, 0, 3, 0), 1: (7, 0, 3, 0)}),
        1: dict(chain=(0, 2), pats={0: (15, 0, 3, 0), 1: (7, 0, 3, 0), 2: (4, 0, 3, 0)}),
        2: dict(chain=(2, 4), pats={2: (11, 4, 3, 0), 3: (31, 0, 3, 0), 4: (3, 28, 3, 0)}),   # 4 wraps 28..3
        3: dict(chain=(5, 6), pats={5: (12, 10, 3, 0), 6: (0, 0, 3, 0)}),                  # 6: one step
        4: dict(chain=(0, 1), pats={0: (15, 0, 3, 0), 1: (9, 2, 3, 0)}),
        5: dict(chain=(0, 2), pats={0: (5, 0, 3, 0), 1: (6, 0, 3, 0), 2: (7, 0, 3, 0)}),
        6: dict(chain=(3, 3), pats={3: (31, 0, 3, 0)}),
        7: dict(chain=(1, 2), pats={1: (2, 30, 3, 0), 2: (15, 15, 3, 0)}),
    }, 620),
    "directions": ({                                                                       # 0 fwd, 1 rev, 2 ping-pong, 3 random
        0: dict(chain=(0, 0), pats={0: (11, 4, 3, 1)}),
        1: dict(chain=(0, 0), pats={0: (11, 4, 3, 2)}),
        2: dict(chain=(0, 0), pats={0: (11, 4, 3, 3)}),
        3: dict(chain=(0, 1), pats={0: (5, 0, 3, 2), 1: (3, 0, 3, 1)}),
        4: dict(chain=(0, 0), pats={0: (7, 0, 3, 1)}),
        5: dict(chain=(0, 0), pats={0: (7, 0, 3, 2)}),
        6: dict(chain=(0, 0), pats={0: (7, 0, 3, 3)}),
        7: dict(chain=(0, 1), pats={0: (3, 30, 3, 2), 1: (4, 0, 3, 3)}),                   # ping-pong over the wrap
    }, 400),
    "rates": ({t: dict(chain=(0, 1), pats={0: (7, 0, t, 0), 1: (3, 0, t, 0)}) for t in range(8)}, 900),
    "muted": ({
        0: dict(chain=(0, 1), pats={0: (7, 0, 3, 0), 1: (3, 0, 3, 0)}, mute=True),
        1: dict(chain=(0, 1), pats={0: (7, 0, 3, 0), 1: (3, 0, 3, 0)}),
        4: dict(chain=(0, 1), pats={0: (7, 0, 3, 0), 1: (3, 0, 3, 0)}, mute=True),
        5: dict(chain=(0, 1), pats={0: (7, 0, 3, 0), 1: (3, 0, 3, 0)}),
        **{t: dict(chain=(0, 0), pats={0: (15, 0, 3, 0)}) for t in (2, 3, 6, 7)},
    }, 300),
}


def fresh(image, manifest, cfg=None):
    h = TrigHarness(image, manifest)
    trig_setup(h, cfg)
    return h


def check_counts(h: TrigHarness, t: int, pats: dict | None = None) -> dict[int, int]:
    """Track t's passes since Play (no start-over since): each pass's steps read the count of its pattern = the passes
    of that pattern completed before it; every completed pass is one pass of its pattern (forward / reverse: its exact
    steps; ping-pong: there and back; random: as many steps as the range); trig_count = the completed passes, never
    more. Returns {pattern: completed passes}."""
    segs = h.segments(t)
    done: dict[int, int] = {}
    for i, seg in enumerate(segs):
        complete = i < len(segs) - 1
        assert seg or not complete, f"track {t}: pass {i} has no step"
        if not seg:
            continue
        p = seg[0][2]
        assert all(x[2] == p for x in seg), f"track {t}: pass {i} changes pattern: {seg}"
        want = done.get(p, 0)
        assert [x[4] for x in seg] == [want] * len(seg), f"track {t} pattern {p}: pass {i} reads {[x[4] for x in seg]}, wanted {want}"
        if complete:
            if pats is not None:
                last, first, rate, d = pats[p]
                steps, n = [x[3] for x in seg], (last - first) % 32 + 1
                exact = expected_pass(last, first, d)
                if exact is not None:
                    assert steps == exact, f"track {t}: pass {i}: steps {steps}, wanted {exact}"
                else:
                    assert len(steps) == (2 * n if d == 2 else n), f"track {t}: pass {i} ({d}): {steps}"
                    assert all((s - first) % 32 < n for s in steps), f"track {t}: pass {i} out of range: {steps}"
            done[p] = want + 1
    assert h.counts()[t] == [done.get(p, 0) for p in range(8)], f"track {t}: {h.counts()[t]} vs {done}"
    return done


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_one_count_per_pass(pl21_image, pl21_manifest, name):
    cfg, ticks = SCENARIOS[name]
    h = fresh(pl21_image, pl21_manifest, cfg)
    h.clear_logs()
    h.play()
    h.run_ticks(ticks)
    for t in range(TRACKS):
        done = check_counts(h, t, cfg[t]["pats"])
        assert sum(done.values()) >= len(cfg[t]["pats"]), f"track {t}: too few passes to tell: {done}"


def test_play_starts_over(pl21_image, pl21_manifest):
    h = fresh(pl21_image, pl21_manifest)
    h.play()
    h.run_ticks(110)                                    # 8 steps x 6 ticks: two passes and some
    before = h.counts()
    assert all(before[t][0] == 2 for t in range(TRACKS)), before
    h.play()                                            # Stop
    h.heartbeat(30)
    assert h.counts() == before                         # Stop changes nothing
    h.clear_logs()
    h.play()
    assert h.counts() == before                         # the press only posts the start-over
    h.heartbeat(1)
    assert sorted({x[1] for x in h.t0}) == list(range(TRACKS))   # step 1's tick 0 ran for every track ...
    assert all(x[4] == 0 and x[3] == 0 for x in h.t0), h.t0      # ... reading 0
    assert h.counts() == [[0] * 8] * TRACKS


def test_shift_play_continues(pl21_image, pl21_manifest):
    h = fresh(pl21_image, pl21_manifest)
    h.play()
    h.run_ticks(80)                                     # pass 2, step 6 of 8
    h.play()                                            # Stop
    h.heartbeat(30)
    before = h.counts()
    assert all(before[t][0] == 1 for t in range(TRACKS)), before
    h.clear_logs()
    h.resume()
    h.run_ticks(60)
    for t in range(TRACKS):
        segs = h.segments(t)
        assert segs[0] and all(x[4] == 1 for x in segs[0]), f"track {t}: {segs[0]}"     # the pass goes on, count kept
        assert len(segs) >= 2 and all(x[4] == 2 for x in segs[1]), f"track {t}: {segs[1:]}"   # and counts on
        assert h.count(t, 0) == 1 + len(segs) - 1


def test_hand_pick_starts_over(pl21_image, pl21_manifest):
    # A Patterns view tap mid-pass: nothing until the takeover, then that track only starts over.
    h = fresh(pl21_image, pl21_manifest)
    h.press(PATTERNS_VIEW)
    h.play()
    h.run_ticks(110)                                    # pass 3, step 3 of 8
    h.clear_logs()
    h.pick(0, 2)                                        # Synth 1: pattern 3
    assert h.hand_flag(0) == 1
    h.run_ticks(40)
    take = [a for a in h.adv if a[1] == 0]
    assert take and take[0][3:] == (1, 0, 1), take       # the takeover: end, no scene, hand
    segs = h.segments(0)
    assert [x[2] for x in segs[0]] == [0] * len(segs[0]) and all(x[4] == 2 for x in segs[0]), segs[0]
    assert segs[1] and all(x[2] == 2 and x[4] == 0 for x in segs[1]), segs[1]
    assert h.counts()[0] == [0] * 8                      # pattern 1's count started over too
    for t in range(1, TRACKS):
        assert h.count(t, 0) == 3, (t, h.counts()[t])    # the others counted on
        assert all(x[4] == 3 for x in h.segments(t)[1]), t

    # Shift + a Patterns pad: at once; the partial pass counts at its end.
    h.run_ticks(60)
    assert h.count(0, 2) == 1 and h.count(1, 0) == 4
    before = h.counts()
    h.clear_logs()
    h.pick(1, 3, shift=True)                             # Synth 2: pattern 4, at once
    assert h.counts() == before
    h.heartbeat(1)
    after = h.counts()
    assert after[1] == [0] * 8
    assert after[:1] + after[2:] == before[:1] + before[2:]
    h.run_ticks(60)
    segs = h.segments(1)
    part = [x for x in segs[0] if x[2] == 3]
    assert part and segs[0][-1][2] == 3 and len(part) < 8, segs[0]       # a partial pass of pattern 4, reading 0 ...
    assert all(x[4] == 0 for x in part), part
    assert h.count(1, 3) == 1                            # ... counted at its end

    # A pick while stopped: at once.
    h.play()                                             # Stop
    h.heartbeat(20)
    before = h.counts()
    assert before[4][0] > 0
    h.pick(4, 1)                                         # Drum 1: pattern 2
    h.heartbeat(1)
    after = h.counts()
    assert after[4] == [0] * 8
    assert after[:4] + after[5:] == before[:4] + before[5:]


SCENE_LENGTHS = [6, 8, 8, 8, 16, 8, 8, 8]               # Drum 1 16 steps (the scene takes over at its end), Synth 1 6


def scene_harness(image, manifest, lengths):
    h = fresh(image, manifest, loops(lengths))
    h.save_scene(1, [(1, 1)] * 4 + [(2, 3)] * 4)
    h.save_scene(0, [(0, 0)] * 8)
    h.press(MIXER)
    return h


def test_scene_recall_starts_over(pl21_image, pl21_manifest):
    h = scene_harness(pl21_image, pl21_manifest, SCENE_LENGTHS)
    h.play()
    h.run_ticks(110)                                    # Drum 1 in its second pass, step 3 of 16
    before = h.counts()
    h.clear_logs()
    h.pick_scene(1)
    assert h.scene_wait() == 1
    while not any(a[4] for a in h.adv):                 # until the takeover the counts go on
        want = [row[:] for row in before]
        for a in h.adv:
            want[a[1]][a[2]] += 1
        assert h.counts() == want, h.ticks
        h.run_ticks(1)
        assert h.ticks < 400
    take = h.ticks
    ev = [a for a in h.adv if a[4]]
    assert sorted(a[1] for a in ev) == list(range(TRACKS)), ev        # every track once, Synth 1 cut mid-pattern
    assert any(a[1] == 0 and not a[3] for a in ev), ev
    h.run_ticks(1)
    assert h.counts() == [[0] * 8] * TRACKS
    after = [x for x in h.t0 if x[0] >= take]           # the steps from the takeover on
    assert {x[1] for x in after} == set(range(TRACKS)) and all(x[4] == 0 for x in after), after


def test_scene_chain_keeps_counting(pl21_image, pl21_manifest):
    h = scene_harness(pl21_image, pl21_manifest, [16, 6, 8, 8, 8, 8, 8, 8])
    h.scene_chain(0, 1)
    h.clear_logs()
    h.play()
    h.run_ticks(420)
    scene_events = [a for a in h.adv if a[4]]
    assert len({a[0] for a in scene_events}) >= 3, scene_events     # the chain advanced by itself, more than once
    assert any(a[1] == 1 and not a[3] for a in scene_events)        # Synth 2 (6 steps) cut mid-pattern
    for t in range(TRACKS):
        check_counts(h, t)                              # every pass, the cut ones too, counted once; no start-over


def test_load_starts_over(pl21_image, pl21_manifest):
    for playing in (True, False):
        h = fresh(pl21_image, pl21_manifest)
        h.play()
        h.run_ticks(60)
        if not playing:
            h.play()
            h.heartbeat(20)
        assert all(h.count(t, 0) == 1 for t in range(TRACKS)), h.counts()
        h.load()
        h.heartbeat(1)
        assert h.counts() == [[0] * 8] * TRACKS, playing


def test_pending_pick_at_stop(pl21_image, pl21_manifest):
    # Play: the counts start over once, the waiting pick plays from the start with count 0 on its first pass.
    h = fresh(pl21_image, pl21_manifest)
    h.press(PATTERNS_VIEW)
    h.play()
    h.run_ticks(60)                                     # pass 2, step 3 of 8
    h.pick(0, 2)
    h.play()                                            # Stop before the takeover
    h.heartbeat(20)
    assert h.hand_flag(0) == 1 and h.count(0, 0) == 1
    h.clear_logs()
    h.play()
    h.run_ticks(110)
    segs = h.segments(0)
    assert segs[0] and segs[0][0][2:4] == (2, 0), segs[0]          # pattern 3 from its first step
    assert [[x[4] for x in s] for s in segs[:2]] == [[0] * 8, [1] * 8], segs[:2]
    assert segs[2] and all(x[4] == 2 for x in segs[2]), segs[2]
    assert h.counts()[0] == [0, 0, 2, 0, 0, 0, 0, 0]
    assert not [a for a in h.adv if a[5]]                            # no hand takeover after Play: started over once

    # Shift + Play instead: every count kept; the pick then takes over at its pattern end as a pick by hand.
    h = fresh(pl21_image, pl21_manifest)
    h.press(PATTERNS_VIEW)
    h.play()
    h.run_ticks(60)
    h.pick(0, 2)
    h.play()
    h.heartbeat(20)
    before = h.counts()
    h.clear_logs()
    h.resume()
    h.run_ticks(60)
    segs = h.segments(0)
    assert segs[0] and all(x[2] == 0 and x[4] == 1 for x in segs[0]), segs[0]   # pattern 1's pass goes on, count kept
    take = [a for a in h.adv if a[1] == 0]
    assert take[0][3:] == (1, 0, 1), take                # then the pick takes over at its end, as a pick by hand ...
    assert segs[1] and all(x[2] == 2 and x[4] == 0 for x in segs[1]), segs[1]
    assert h.counts()[0] == [0] * 8
    for t in range(1, TRACKS):                           # ... and the other tracks kept counting from their counts
        assert all(x[4] == before[t][0] for x in h.segments(t)[0]), t
        assert h.count(t, 0) == before[t][0] + 1, (t, h.counts()[t])


def test_counts_wrap_at_840(pl21_image, pl21_manifest):
    # A count reaching 2 x 840 goes back to 840, never to 0 (count 0 = FIRST only once per start-over); 839 counts on.
    h = fresh(pl21_image, pl21_manifest)
    h.play()
    h.run_ticks(10)
    h.set_count(0, 0, 1679)
    h.set_count(4, 0, 839)
    h.set_count(1, 0, 1678)
    h.clear_logs()
    h.run_ticks(48)
    assert (h.count(0, 0), h.count(4, 0), h.count(1, 0)) == (840, 840, 1679)
    h.run_ticks(48)
    assert (h.count(0, 0), h.count(4, 0), h.count(1, 0)) == (841, 841, 840)


def test_only_main_writes_counts(pl21_image, pl21_manifest):
    h = fresh(pl21_image, pl21_manifest)
    m = pl21_manifest["symbols"]
    names = {"trig_count": 128, "trig_restart": 1, "trig_ms": 4, "trig_scene_wait": 1}
    regions = {n: (int(m[n], 16), size) for n, size in names.items()}
    writes: list[tuple[str, str]] = []
    for n, (a, size) in regions.items():
        h.uc.hook_add(UC_HOOK_MEM_WRITE, lambda u, acc, addr, sz, v, d, n=n: writes.append((h.task, n)),
                      begin=a, end=a + size - 1)
    h.press(PATTERNS_VIEW)
    h.play()
    h.run_ticks(60)
    h.pick(0, 2)
    h.pick(1, 3, shift=True)
    h.run_ticks(60)
    h.play()
    h.heartbeat(10)
    h.pick(4, 1)
    h.resume()
    h.heartbeat(10)
    h.play()
    h.heartbeat(10)
    h.load()
    h.leds()
    h.heartbeat(10)
    by_task = {task: {n for t_, n in writes if t_ == task} for task in ("ui", "main")}
    assert by_task["ui"] == {"trig_restart"}, by_task
    assert {"trig_count", "trig_ms", "trig_restart"} <= by_task["main"], by_task
