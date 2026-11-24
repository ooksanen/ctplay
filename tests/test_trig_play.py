"""PL20 Task 5: conditions at playback. Each step's condition is evaluated once, at its tick 0 (hook player_tick); a
silenced step fails stock's three probability tests (prob_note, prob_drum, prob_drum_first), so it behaves exactly as
a failed probability roll. Plan 2026-11-07-trig-conditions.md, Global Constraints "The code", "Evaluation"; evidence
docs/investigations/2026-11-01-trig-conditions-spike/B-counting.md 4-5 (b_4_tick0.py, b_5_prob.py).

Codes are written raw (`set_code`, trig_model's byte layout) and the project marked (`mark(1)`) unless a test says
otherwise; Play through the real button, the sequencer through the heartbeat (Main's 1 ms service), 240 BPM. A note-on
is credited to the step whose tick 0 came last on its track: drums at the drum player's note-on, note tracks at the
note player's (`TrigHarness.sounded`). Each step's roll is chosen through its random word (`h.rand`)."""
import random

import pytest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R4, \
    UC_ARM_REG_R5, UC_ARM_REG_R9, UC_ARM_REG_SP

import trig_model as tm
from drums import sym
from notes import PATTERN, PATTERN_BASE, STEP, set_tempo
from test_chord import set_strum
from trig import (DRUM_PAT, MIXER, PATTERNS_VIEW, PLAYERS, TIE, TRACKS, TrigHarness, loops, trig_setup)
from voices import VOICE_MODE, VoiceHarness

pytestmark = pytest.mark.emu

FIRST, NOT_FIRST, FILL, NOT_FILL, PRE, NOT_PRE, LAST, NOT_LAST = tm.TRIG_SPECIAL
PROB_NOTE, PROB_DRUM, PROB_DRUM_FIRST = 0x08040D8A, 0x0804AA18, 0x080411F6     # the hook sites (stock's tests)
PASS = 6 * 4                                  # ticks of a 4-step pass at 1/16


def fresh(image, manifest, cfg=None, length=4, mark=1, cls=TrigHarness):
    """slim ready, 240 BPM, every track a `length`-step loop (or cfg), every step empty, the project marked."""
    h = cls(image, manifest)
    trig_setup(h, cfg or loops(length))
    h.clear_steps()
    if mark is not None:
        h.mark(mark)
    return h


def go(h, ticks):
    h.load_editors()
    h.clear_logs()
    h.play()
    h.run_ticks(ticks)


def passes(h, t, length):
    """Track t's completed passes of a `length`-step loop."""
    return len(h.steps[t]) // length


def sounded(h, t, step, length):
    """The completed passes on which track t's `step` sounded."""
    return [k for k in h.passes_sounded(t, step, length) if k < passes(h, t, length)]


# ---- cycles ---------------------------------------------------------------------------------------------------------
CYCLES = {
    "2:2": tm.trig_cycle(2, 0b10),
    "1:4": tm.trig_cycle(4, 0b1),
    "1+3:4": tm.trig_cycle(4, 0b101),
    "not 1:2": tm.trig_cycle(2, 0b10),
    "5:7": tm.trig_cycle(7, 1 << 4),
    "all ticked": tm.trig_cycle(3, 0b111),
}


@pytest.mark.parametrize("name", list(CYCLES))
@pytest.mark.parametrize("t", [4, 0], ids=["drum1", "synth1"])
def test_cycles(pl21_image, pl21_manifest, t, name):
    """The step sounds on exactly the passes trig_model.plays gives, over 2 L passes; a plain step beside it on every
    pass."""
    code = CYCLES[name]
    L = tm.trig_len(code)
    h = fresh(pl21_image, pl21_manifest)
    h.hit(t, 0, 1)
    h.hit(t, 0, 2, code=code)
    go(h, PASS * 2 * L + 2)
    n = passes(h, t, 4)
    assert n >= 2 * L
    assert sounded(h, t, 2, 4) == [k for k in range(n) if tm.plays(code, k, 0, 0, 0)]
    assert sounded(h, t, 1, 4) == list(range(n))


def test_condition_and_roll(pl21_image, pl21_manifest):
    """1:2 at probability 3, the roll chosen per pass: the step plays only when both pass. Beside it (Synth 2, Drum 2)
    the same rolls with no condition."""
    rolls = [0, 0, 7, 7, 3, 3, 4, 4]                  # low bits of the random word: probability 3 passes on <= 3
    h = fresh(pl21_image, pl21_manifest)
    for t in (0, 4):
        h.hit(t, 0, 2, prob=3, code=tm.trig_cycle(2, 1))
        h.hit(t + 1, 0, 2, prob=3)
    h.rand = lambda t, i, s: rolls[i // 4 % 8] if s == 2 else None
    go(h, PASS * 8 + 2)
    for t in (0, 4):
        assert passes(h, t, 4) == 8
        assert sounded(h, t + 1, 2, 4) == [0, 1, 4, 5]                    # the rolls alone
        assert sounded(h, t, 2, 4) == [0, 4], t                           # the rolls and 1:2


# ---- a silenced step is a failed roll (b_5_prob.py) -----------------------------------------------------------------
TARGETS = {(0, 2), (0, 4), (4, 2)}           # (track, step) at probability 6


def b5_patterns(h, code):
    """Synth 1, 8 steps: 0 C4; 1 D4 tied into 2; 2 D4 (target); 3 E4 gate 30 (5 steps); 4 F4 + A4 at microstep 2
    (target, during the long E4); 6 G4 microstep 3; 7 C5. Drum 1: hits on 0-3 and 6; step 2 (target) flip sample 5 and
    micro bits 0 + 3; step 3 micro bit 1."""
    h.note(0, 0, 0, [(60, 6, 0, 100)])
    h.note(0, 0, 1, [(62, 6 | TIE, 0, 100)])
    h.note(0, 0, 2, [(62, 6, 0, 100)], prob=6, code=code)
    h.note(0, 0, 3, [(64, 30, 0, 100)])
    h.note(0, 0, 4, [(65, 6, 2, 100), (69, 6, 2, 100)], prob=6, code=code)
    h.note(0, 0, 6, [(67, 6, 3, 100)])
    h.note(0, 0, 7, [(72, 6, 0, 100)])
    for s, micro in ((0, 1), (1, 1), (3, 0b10), (6, 1)):
        h.hit(4, 0, s, micro=micro)
    h.hit(4, 0, 2, prob=6, flip=5, micro=0b1001, code=code)


def b5_run(image, manifest, mode):
    """mode 'pass' (roll passes), 'roll' (stock fails its roll), 'silenced' (roll passes, the condition fails: a cycle
    of 8 with pass 8 ticked). Two passes; every event with its ms."""
    h = fresh(image, manifest, length=8)
    b5_patterns(h, tm.trig_cycle(8, 0x80) if mode == "silenced" else 0)
    h.rand = lambda t, i, s: (7 if mode == "roll" else 0) if (t, s) in TARGETS else None
    h.load_editors()
    h.clear_logs()
    h.play()
    while h.ticks < 48 * 2 + 2:
        h.run_ms(1)
    return h


def test_silenced_is_a_failed_roll(pl21_image, pl21_manifest):
    runs = {mode: b5_run(pl21_image, pl21_manifest, mode) for mode in ("pass", "roll", "silenced")}
    trace = {mode: h.trace for mode, h in runs.items()}
    assert trace["silenced"] == trace["roll"]                         # ms for ms: notes, drums, endpoints
    assert trace["pass"] != trace["roll"]
    # no flip sample sent: stock sends each hit's sample (r2: 8 here, the target's flip 5)
    flips = {mode: [e for e in tr if e[2] == "d_sample" and e[5] == 5] for mode, tr in trace.items()}
    assert flips["silenced"] == [] and len(flips["pass"]) == 2
    for t, s in TARGETS:
        assert sounded(runs["silenced"], t, s, 8) == [], (t, s)
    for t, s in ((0, 4), (4, 2)):                                     # (Synth 1's step 3 continues a tie: no note-on)
        assert sounded(runs["pass"], t, s, 8) == [0, 1], (t, s)


# ---- FIRST, PRE, LAST, FILL -----------------------------------------------------------------------------------------
def test_first(pl21_image, pl21_manifest):
    """Synth 1 / Drum 1 loop one pattern; Synth 2 / Drum 2 chain patterns 1-2: FIRST on each pattern's first pass only,
    NOT FIRST on the others."""
    cfg = loops(4)
    for t in (1, 5):
        cfg[t]["chain"] = (0, 1)
    h = fresh(pl21_image, pl21_manifest, cfg)
    for t in (0, 1, 4, 5):
        for p in (0, 1):
            h.hit(t, p, 1, code=FIRST)
            h.hit(t, p, 2, code=NOT_FIRST)
    go(h, PASS * 6 + 2)
    for t in (0, 4):
        assert passes(h, t, 4) == 6
        assert sounded(h, t, 1, 4) == [0]
        assert sounded(h, t, 2, 4) == [1, 2, 3, 4, 5]
    for t in (1, 5):
        assert [h.steps[t][4 * k][0] for k in range(6)] == [0, 1] * 3
        assert sounded(h, t, 1, 4) == [0, 1]
        assert sounded(h, t, 2, 4) == [2, 3, 4, 5]


def test_first_once_across_the_wrap(pl21_image, pl21_manifest):
    """Synth 1 / Drum 1's count set to 1677 just after Play (step 1 has read 0): FIRST plays on the first pass only,
    NOT FIRST on every other step's pass, through the count's wrap (1679 -> 840); cycles of 3, 7 and 8 sound as an
    unwrapped count would make them (840 is a multiple of 2-8)."""
    cyc = {2: tm.trig_cycle(7, 0b100), 3: tm.trig_cycle(8, 0b10000001)}
    h = fresh(pl21_image, pl21_manifest)
    for t in (0, 4):
        h.hit(t, 0, 0, code=FIRST)
        h.hit(t, 0, 1, code=NOT_FIRST)
        for s, code in cyc.items():
            h.hit(t, 0, s, code=code)
    go(h, 2)
    for t in (0, 4):
        h.set_count(t, 0, 1677)
    h.run_ticks(PASS * 6)
    for t in (0, 4):
        assert passes(h, t, 4) == 6, t
        assert sounded(h, t, 0, 4) == [0], t
        assert sounded(h, t, 1, 4) == list(range(6)), t
        for s, code in cyc.items():
            assert sounded(h, t, s, 4) == [k for k in range(6) if tm.plays(code, 1677 + k, 0, 0, 0)], (t, s)


def test_pre(pl21_image, pl21_manifest):
    """8-step loops, 6 passes, the rolls chosen per pass.
    - Synth 1 / Drum 1: step 1 at probability 4; step 3 NOT PRE, step 5 PRE: PRE follows step 1 pass by pass, NOT PRE
      the opposite (a PRE step between them changes nothing).
    - Synth 2 / Drum 2: PRE and NOT PRE, no conditional step: PRE silent, NOT PRE plays.
    - MIDI 1 / Drum 3: step 1 PRE, step 7 at probability 4: PRE follows the previous pass's step 7.
    - MIDI 2 / Drum 4, as MIDI 1: MIDI 2 muted through pass 1 (its step 7 passes), Drum 4 muted through pass 2 (its
      step 7 fails): unmuted, the PRE step follows the muted pass."""
    a, b, c = [0, 7, 0, 7, 7, 0], [0, 7, 7, 0, 0, 7], [0, 7, 0, 7, 0, 7]
    rolls = {(0, 0): a, (4, 0): a, (2, 6): b, (6, 6): b, (3, 6): c, (7, 6): c}       # (track, step): per pass
    h = fresh(pl21_image, pl21_manifest, length=8)
    for t in (0, 4):
        h.hit(t, 0, 0, prob=4)
        h.hit(t, 0, 2, code=NOT_PRE)
        h.hit(t, 0, 4, code=PRE)
    for t in (1, 5):
        h.hit(t, 0, 1, code=PRE)
        h.hit(t, 0, 3, code=NOT_PRE)
    for t in (2, 3, 6, 7):
        h.hit(t, 0, 0, code=PRE)
        h.hit(t, 0, 6, prob=4)
    h.rand = lambda t, i, s: rolls[t, s][i // 8] if (t, s) in rolls and i // 8 < 6 else None
    h.mute(3, True)
    go(h, 45)                                          # pass 1, step 8
    h.mute(3, False)
    h.mute(7, True)
    h.run_ticks(48)                                    # pass 2, step 8
    h.mute(7, False)
    h.run_ticks(48 * 4 + 2)
    for t in range(TRACKS):
        assert passes(h, t, 8) == 6, t
    for t in (0, 4):
        assert sounded(h, t, 0, 8) == [0, 2, 5]
        assert sounded(h, t, 4, 8) == [0, 2, 5]
        assert sounded(h, t, 2, 8) == [1, 3, 4]
    for t in (1, 5):
        assert sounded(h, t, 1, 8) == []
        assert sounded(h, t, 3, 8) == list(range(6))
    for t in (2, 6):
        assert sounded(h, t, 6, 8) == [0, 3, 4]
        assert sounded(h, t, 0, 8) == [1, 4, 5]          # pass 1: nothing conditional since Play
    assert sounded(h, 3, 6, 8) == [2, 4]                 # pass 1 muted
    assert sounded(h, 3, 0, 8) == [1, 3, 5]              # pass 2 follows the muted pass's step 7
    assert sounded(h, 7, 6, 8) == [0, 2, 4]
    assert sounded(h, 7, 0, 8) == [3, 5]                 # pass 2 muted; pass 3 follows its failed step 7


@pytest.mark.parametrize("how", ["pick", "scene"])
def test_pre_starts_over_on_a_hand_change(pl21_image, pl21_manifest, how):
    """A waited pick by hand (Patterns view tap) or a scene recalled by hand starts PRE over (spec my call 7), as a
    posted start-over does. Synth 1 / Drum 1, 4-step loops: pattern 1's step 2 a conditional step that plays every pass
    (every pass ticked); the new pattern's step 1 PRE, step 3 NOT PRE, step 4 conditional, every pass ticked. On the
    new pattern's first pass PRE is silent and NOT PRE plays though pattern 1's conditional step played just before;
    on its second pass both follow its own step 4."""
    every = tm.trig_cycle(2, 0b11)
    new = {0: 1, 4: 1} if how == "pick" else {0: 1, 4: 2}               # the pattern each track changes to
    h = fresh(pl21_image, pl21_manifest)
    for t in (0, 4):
        h.hit(t, 0, 1, code=every)
        h.hit(t, new[t], 0, code=PRE)
        h.hit(t, new[t], 2, code=NOT_PRE)
        h.hit(t, new[t], 3, code=every)
    if how == "scene":
        h.save_scene(1, [(1, 1)] * 4 + [(2, 2)] * 4)
        h.save_scene(0, [(0, 0)] * 8)
        h.press(MIXER)
    else:
        h.press(PATTERNS_VIEW)
    go(h, PASS + 10)                                   # pass 2, step 2 (pattern 1's step 2 played again)
    if how == "scene":
        h.pick_scene(1)
        assert h.scene_wait() == 1
    else:
        for t in (0, 4):
            h.pick(t, new[t])
            assert h.hand_flag(t) == 1
    h.run_ticks(PASS * 3 - 10 + 2)
    for t in (0, 4):
        assert passes(h, t, 4) == 4, t
        assert [h.steps[t][4 * k][0] for k in range(4)] == [0, 0, new[t], new[t]], t
        assert sounded(h, t, 1, 4) == [0, 1], t                         # pattern 1's step 2
        assert sounded(h, t, 3, 4) == [2, 3], t                         # the new pattern's step 4
        assert sounded(h, t, 0, 4) == [3], t                            # PRE: silent on the first pass
        assert sounded(h, t, 2, 4) == [2], t                            # NOT PRE: plays on the first pass only


def test_last_patterns_pick_and_chain(pl21_image, pl21_manifest):
    """Synth 1 / Drum 1 picked by hand (Patterns view) in their second pass: LAST plays from the pick to the takeover
    only, NOT LAST the opposite. Synth 2 / Drum 2 chain patterns 1-2 by themselves: LAST never."""
    cfg = loops(8)
    for t in (1, 5):
        cfg[t]["chain"] = (0, 1)
    h = fresh(pl21_image, pl21_manifest, cfg, length=8)
    for t in (0, 1, 4, 5):
        for p in (0, 1):
            h.hit(t, p, 2, code=LAST)
            h.hit(t, p, 5, code=NOT_LAST)
    h.press(PATTERNS_VIEW)
    go(h, 50)                                          # pass 2, step 1
    for t in (0, 4):
        h.pick(t, 1)
        assert h.hand_flag(t) == 1
    h.run_ticks(48 * 3)
    for t in (0, 4):
        assert passes(h, t, 8) == 4
        assert [h.steps[t][8 * k][0] for k in range(4)] == [0, 0, 1, 1]
        assert sounded(h, t, 2, 8) == [1]
        assert sounded(h, t, 5, 8) == [0, 2, 3]
    for t in (1, 5):
        assert [h.steps[t][8 * k][0] for k in range(4)] == [0, 1, 0, 1]
        assert sounded(h, t, 2, 8) == []
        assert sounded(h, t, 5, 8) == [0, 1, 2, 3]


SCENE_LENGTHS = [6, 8, 8, 8, 16, 8, 8, 8]               # Drum 1 16 steps (the scene takes over at its end), Synth 1 6


def test_last_scene_pick(pl21_image, pl21_manifest):
    """A scene picked by hand: every track's LAST steps play from the pick until Drum 1's pattern end, Synth 1 (6
    steps) looping through it; NOT LAST the opposite."""
    h = fresh(pl21_image, pl21_manifest, loops(SCENE_LENGTHS))
    for t in range(TRACKS):
        for p in range(4):
            for s in (1, 4):
                h.hit(t, p, s, code=LAST)
            for s in (3, 5):
                h.hit(t, p, s, code=NOT_LAST)
    h.save_scene(1, [(1, 1)] * 4 + [(2, 3)] * 4)
    h.save_scene(0, [(0, 0)] * 8)
    h.press(MIXER)
    go(h, 110)                                         # Drum 1 in its second pass, step 3 of 16
    pick = h.ticks
    h.pick_scene(1)
    assert h.scene_wait() == 1
    h.run_ticks(120)
    take = min(a[0] for a in h.adv if a[4])
    assert take > pick + 6
    for t in range(TRACKS):
        ticks = [x[0] for x in h.t0 if x[1] == t]
        on = set(h.sounded(t))
        lasts = [(i, pick < ticks[i] < take) for i, (p, s) in enumerate(h.steps[t]) if s in (1, 4)]
        nots = [(i, not pick < ticks[i] < take) for i, (p, s) in enumerate(h.steps[t]) if s in (3, 5)]
        assert [(i, i in on) for i, _ in lasts] == lasts, t
        assert [(i, i in on) for i, _ in nots] == nots, t
        assert any(w for _, w in lasts) and any(not w for _, w in lasts), t
    ticks = [x[0] for x in h.t0 if x[1] == 0]
    assert len([i for i, x in enumerate(ticks) if pick < x < take and h.steps[0][i][1] == 1]) >= 2   # Synth 1 looped


def test_fill_read(pl21_image, pl21_manifest):
    """trig_fill_hold bit 0 (drum 1's FILL on): Drum 1's FILL steps play, NOT FILL silent; Drum 2 unaffected; a note
    track's FILL reads off."""
    h = fresh(pl21_image, pl21_manifest)
    for t in (0, 4, 5):
        h.hit(t, 0, 1, code=FILL)
        h.hit(t, 0, 2, code=NOT_FILL)
    h.uc.mem_write(sym(pl21_manifest, "trig_fill_hold"), bytes([1]))
    go(h, PASS * 2 + 2)
    assert sounded(h, 4, 1, 4) == [0, 1] and sounded(h, 4, 2, 4) == []
    for t in (0, 5):
        assert sounded(h, t, 1, 4) == [] and sounded(h, t, 2, 4) == [0, 1], t


# ---- as PL19 --------------------------------------------------------------------------------------------------------
def dump_run(image, manifest, prep):
    """The dump's own patterns (prep may change them), 240 BPM, 3 s of play: every event with its ms."""
    h = TrigHarness(image, manifest)
    h.leds()
    set_tempo(h, bpm=240, swing=50)
    prep(h)
    h.load_editors()
    h.clear_logs()
    h.play()
    h.run_ms(3000)
    h.play()
    h.run_ms(20)
    return h


def junk(h):
    """Junk in every drum pattern's +0x84..+0xA7 and every note step's bytes 2-3."""
    rng = random.Random(20)
    for d in range(4):
        for p in range(8):
            h.uc.mem_write(h.drum_base(d) + p * DRUM_PAT + 0x84, bytes(rng.randrange(256) for _ in range(0x24)))
    for t in range(4):
        for p in range(8):
            for s in range(32):
                a = PATTERN_BASE[t] + p * PATTERN + s * STEP + 2
                h.uc.mem_write(a, bytes([rng.randrange(256), rng.randrange(256)]))


def low_probabilities(h):
    """Every code 0, every step's probability below 7 (the same draw in both builds)."""
    rng = random.Random(7)
    for d in range(4):
        for p in range(8):
            b = h.drum_base(d) + p * DRUM_PAT
            h.uc.mem_write(b + 0x20, bytes(rng.randrange(7) for _ in range(32)))
            h.uc.mem_write(b + 0x84, bytes(0x24))
    for t in range(4):
        for p in range(8):
            for s in range(32):
                h.uc.mem_write(PATTERN_BASE[t] + p * PATTERN + s * STEP + 1, bytes([rng.randrange(7), 0, 0]))


def test_unmarked_plays_as_pl19(pl21_image, pl21_manifest, pl19_published_image, pl19_published_manifest):
    def prep20(h):
        junk(h)
        h.mark(0)
    old = dump_run(pl19_published_image, pl19_published_manifest, junk).trace
    new = dump_run(pl21_image, pl21_manifest, prep20).trace
    assert {e[2] for e in old} >= {"n_on", "d_on", "synth_on", "midi_on"}
    assert new == old


def test_no_conditions_is_pl19(pl21_image, pl21_manifest, pl19_published_image, pl19_published_manifest):
    def prep20(h):
        low_probabilities(h)
        h.mark(1)
    old = dump_run(pl19_published_image, pl19_published_manifest, low_probabilities).trace
    new = dump_run(pl21_image, pl21_manifest, prep20).trace
    assert {e[2] for e in old} >= {"n_on", "d_on"}
    assert new == old


# ---- a Played track (PL19) ------------------------------------------------------------------------------------------
C, D, E, F, G, A = 48, 50, 51, 53, 55, 56          # the dump's scale, C minor (test_pstrum.py)
TRIAD = [(G, 6, 0, 90), (C, 3, 0, 100), (E, 12, 0, 80)]


def played_run(image, manifest, first, second, mode):
    """Synth 1 Played, strum slow; step 1 `first`, step 2 `second` at probability 6, 8-step loop, two passes. mode
    'silenced' (1:2: pass 2 silenced, the rolls pass) or 'roll' (no condition; pass 2's roll fails)."""
    h = fresh(image, manifest, length=8)
    h.track(0)
    set_strum(h, manifest, 0, 1)
    a = sym(manifest, "chord_pstrum")
    h.uc.mem_write(a, bytes([h.r8(a) & ~3 | 1]))
    h.uc.mem_write(VOICE_MODE[0], bytes([2]))
    h.note(0, 0, 0, first)
    h.note(0, 0, 1, second, prob=6, code=tm.trig_cycle(2, 1) if mode == "silenced" else 0)
    h.rand = lambda t, i, s: (7 if mode == "roll" and i // 8 == 1 else 0) if (t, s) == (0, 1) else None
    h.clear_logs()
    h.play()
    while h.ticks < 48 * 2 + 2:
        h.run_ms(1)
    h.play()
    h.run_ms(400)
    return h


def test_played_silenced_step(pl21_image, pl21_manifest):
    """Step 1 a slow triad, step 2 a triad 1:2 on its silenced pass: step 1's strum plays out, step 2 sounds nothing;
    the same events as step 2's failed roll. A tie from step 1 into a silenced step 2: as the failed roll."""
    second = [(A, 6, 0, 100), (D, 6, 0, 90), (F, 6, 0, 80)]
    runs = {mode: played_run(pl21_image, pl21_manifest, TRIAD, second, mode) for mode in ("silenced", "roll")}
    assert runs["silenced"].trace == runs["roll"].trace
    h = runs["silenced"]
    ons = [e[4] for e in h.trace if e[2] == "n_on" and e[3] == 0]
    at = [i // 8 for t, i in h.hits if t == 0]         # each note-on's pass (late notes too: their step's pass)
    pass1 = [n for n, k in zip(ons, at) if k == 0]
    pass2 = [n for n, k in zip(ons, at) if k == 1]
    assert len(pass1) == 4                             # step 1's first note, cut by step 2's strum (3 notes)
    assert sorted(pass2) == sorted(n for n, *_ in TRIAD), pass2      # step 1's strum plays out, step 2 nothing

    tied = [(C, 6 | TIE, 0, 100), (E, 6, 0, 90), (G, 6, 0, 80)]
    runs = {mode: played_run(pl21_image, pl21_manifest, tied, [(C, 6, 0, 100), (A, 6, 0, 90)], mode)
            for mode in ("silenced", "roll")}
    assert runs["silenced"].trace == runs["roll"].trace


# ---- the hooks ------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("shift", [0, 4], ids=["notes-0-3", "notes-4-7"])
def test_every_rate_evaluates_first(pl21_image, pl21_manifest, shift):
    """Rates 0-7 on both classes (b_4_tick0.py): each step's evaluation (trig_on_step at tick 0) runs before every
    probability test of that step, once per step."""
    cfg = {t: dict(chain=(0, 0), pats={0: (7, 0, (t + shift) % 8, 0)}) for t in range(TRACKS)}
    h = fresh(pl21_image, pl21_manifest, cfg)
    for t in range(TRACKS):
        for s in range(8):
            code = tm.trig_cycle(2, 0b10) if s % 2 else 0
            if t < 4:
                h.note(t, 0, s, [(60, 6, 0, 100), (64, 6, 3, 100)], code=code)
            else:
                h.hit(t, 0, s, micro=0b100000, code=code)
    log = []
    regs_at = {}
    m = pl21_manifest

    def step_eval(u, a, s, d):
        r = u.reg_read(UC_ARM_REG_R0)                   # slim_regs_t: r[5] tick, r[7] player, r[8] step
        if h.r32(r + 20) == 0 and h.r32(r + 28) in PLAYERS:
            log.append(("eval", PLAYERS.index(h.r32(r + 28)), h.r32(r + 32) & 0xFF))

    def test_at(kind):
        def f(u, a, s, d):
            sp = u.reg_read(UC_ARM_REG_SP)
            if a == PROB_NOTE:
                p, step = u.reg_read(UC_ARM_REG_R9), h.r32(sp) & 0xFF
            elif a == PROB_DRUM:
                p, step = h.r32(sp + 4), u.reg_read(UC_ARM_REG_R1) - u.reg_read(UC_ARM_REG_R5)
            else:
                p, step = u.reg_read(UC_ARM_REG_R4), u.reg_read(UC_ARM_REG_R2)
            if p in PLAYERS:
                log.append((kind, PLAYERS.index(p), step))
        return f
    h.uc.hook_add(UC_HOOK_CODE, step_eval, begin=sym(m, "trig_on_step"), end=sym(m, "trig_on_step"))
    for a, kind in ((PROB_NOTE, "note"), (PROB_DRUM, "drum"), (PROB_DRUM_FIRST, "first")):
        h.uc.hook_add(UC_HOOK_CODE, test_at(kind), begin=a, end=a)
    go(h, 24 * 8 * 2 + 5)
    for t in range(TRACKS):
        last, evals, tests = None, 0, set()
        for kind, tr, step in log:
            if tr != t:
                continue
            if kind == "eval":
                last, evals = step, evals + 1
            else:
                assert step == last, (t, kind, step, last)
                tests.add(kind)
        assert evals == len(h.steps[t]) >= 8, t
        assert tests == ({"note"} if t < 4 else {"drum", "first"}), (t, tests)


class VoiceTrig(TrigHarness, VoiceHarness):
    """TrigHarness over the voice-level harness: the synth note-on runs through stock's voice decision, which takes the
    DSP-service lock (0x08021064)."""


def test_no_semaphore_takes(pl21_image, pl21_manifest):
    """No take of the DSP-service lock (0x08021064) from the new handlers, in a run where they silence steps; their
    only stock callee is the parameter getter (a read: param_get, for LAST)."""
    m = pl21_manifest
    h = fresh(pl21_image, m, length=8, cls=VoiceTrig)
    h.set_headroom(0x60000)
    h.rand = lambda t, i, s: 0                         # every roll passes: only the conditions silence
    for t in (0, 1, 4, 5):
        for s in range(8):
            h.hit(t, 0, s, prob=5, code=(tm.trig_cycle(2, 1), FIRST, PRE, 0)[s % 4])
    flash = (int(m["flash"]["start"], 16), int(m["flash"]["end"], 16))
    handlers = ("trig_on_step", "trig_on_prob_note", "trig_on_prob_drum", "trig_on_prob_first")
    st = {"inside": None, "ret": None}
    takes, calls = [], {n: 0 for n in handlers}

    def enter(name):
        def f(u, a, s, d):
            calls[name] += 1
            st["inside"], st["ret"] = name, u.reg_read(UC_ARM_REG_LR) & ~1
        return f

    def slim_code(u, a, s, d):
        if st["inside"] is not None and a == st["ret"]:
            st["inside"] = None

    for n in handlers:
        h.uc.hook_add(UC_HOOK_CODE, enter(n), begin=sym(m, n), end=sym(m, n))
    h.uc.hook_add(UC_HOOK_CODE, slim_code, begin=flash[0], end=flash[1])
    h.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: takes.append(st["inside"]), begin=0x08021064, end=0x08021064)
    go(h, 48 * 3)
    h.play()
    h.heartbeat(20)
    assert all(calls[n] > 10 for n in handlers), calls
    assert takes and set(takes) == {None}, set(takes)
    assert sounded(h, 0, 0, 8) == [0, 2] and sounded(h, 0, 1, 8) == [0]          # the handlers did silence steps
    for n in handlers:
        assert set(pl21_manifest["stack_uncounted_callees"].get(n, ())) <= {"param_get"}, n
