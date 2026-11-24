"""PL20 Task 8: conditions follow stock's own edits (features/chord/trig_keep.c). A drum's conditions live in its
pattern's settings bytes + 0x84..+ 0xA7, which stock never copies, clears or moves (A-storage.md Q2), so CTPlay hooks
Duplicate, Clear step, Clear pattern, copy 1-16 -> 17-32, paste step and Mutate; a note step's bytes [2]-[3] travel
with stock's copies already, and only stock's empty-step fill (Clear step, Clear pattern) must zero them. In a marked
project only: an unmarked one edits exactly as the published PL19. Plan 2026-11-07-trig-conditions.md, Task 8; hook
arguments 2026-11-07-trig-conditions-spike.md Q1 (q1_drums.py, q1_notes.py) and Q2 (q2_mutate.py).

Everything through the controller (A-storage.md "Real routes found"): the Patterns view (Duplicate / Clear held + a
pattern pad), the step view (Clear held + a step pad, Duplicate held + step pads or 1-16/17-32, Shift + Duplicate),
the probability view's row 3 and step entry as the stock edits that follow. Drum 1 = track 4, Drum 2 = track 5, Synth 1
= track 0; patterns and steps 0-based. Every step of patterns 0-3 of the three tracks has its own code (CODE)."""
import pytest

from trig import DRUM_PAT, HALF, TrigHarness, loops, trig_setup

pytestmark = pytest.mark.emu

SYNTH1, DRUM1, DRUM2 = 0, 4, 5
TRACKS = (SYNTH1, DRUM1, DRUM2)
KEY = 24                                         # a key pad of a note track's step view (the lower two rows)
SRC = {0: (100, 7, 0xFF, 1), 3: (90, 5, 2, 3), 6: (80, 7, 0xFF, 0x21), 12: (70, 2, 0xFF, 1), 20: (65, 7, 0xFF, 1)}
DST = {1: (60, 7, 0xFF, 1), 9: (50, 7, 0xFF, 1), 17: (45, 7, 0xFF, 1)}   # (velocity, probability, flip, micro)
NOTES = {0: 60, 3: 62, 6: 64, 12: 65, 20: 67}    # Synth 1's pattern 0: step -> note
MUTATE_HITS = {0: 100, 2: 90, 4: 80, 5: 70, 8: 60, 12: 50, 15: 40, 21: 35, 30: 30}


def CODE(t, p, s):
    """A distinct 9-bit code (1-509, bit 8 on about half) for step s of track t's pattern p (0-3)."""
    return ((TRACKS.index(t) * 4 + p) * 32 + s) * 7 % 509 + 1


def fresh(image, m, mark=1, chain=None):
    """slim ready, 240 BPM, 16-step loops of pattern 0 (Drum 1's chain `chain` instead), every step empty but SRC on
    Drum 1's pattern 0, DST on its pattern 1 and on Drum 2's pattern 1, NOTES on Synth 1's pattern 0 and step 1 / 9 of
    its pattern 1; CODE on every step of patterns 0-3 of the three tracks; the project marked (`mark`; None: PL19,
    which has no mark)."""
    h = TrigHarness(image, m)
    cfg = loops(16)
    if chain is not None:
        cfg[DRUM1]["chain"] = (chain, chain)
    trig_setup(h, cfg)
    h.clear_steps()
    for s, (vel, prob, flip, micro) in SRC.items():
        h.hit(DRUM1, 0, s, vel, prob, flip, micro)
    for t in (DRUM1, DRUM2):
        for s, (vel, prob, flip, micro) in DST.items():
            h.hit(t, 1, s, vel, prob, flip, micro)
    for s, n in NOTES.items():
        h.note(SYNTH1, 0, s, [(n, 6, 0, 100)])
    for s in (1, 9):
        h.note(SYNTH1, 1, s, [(70 + s, 6, 0, 90)])
    for t in TRACKS:
        for p in range(4):
            for s in range(32):
                h.set_code(t, p, s, CODE(t, p, s))
    h.load_editors()
    if mark is not None:
        h.mark(mark)
    return h


def codes(h, t, p):
    return [h.code(t, p, s) for s in range(32)]


def all_codes(h):
    return {(t, p): codes(h, t, p) for t in TRACKS for p in range(4)}


def drum_pat(h, t, p):
    return bytes(h.uc.mem_read(h.drum_base(t - 4) + DRUM_PAT * p, DRUM_PAT))


def cond_bytes(h, t, p):
    return drum_pat(h, t, p)[0x84:0xA8]


def changed_only(before, after, keys):
    """Every (track, pattern) but `keys` kept its codes."""
    return {k: v for k, v in after.items() if k not in keys} == {k: v for k, v in before.items() if k not in keys}


def start(h):
    h.play()
    h.heartbeat(30)


# ---- drums: Duplicate ------------------------------------------------------------------------------------------------

DUP_CASES = {                                    # (chain of Drum 1 or None, playing, source, target, Drum 1's shown)
    "stopped": (None, False, (DRUM1, 0), (DRUM1, 1), None),
    "target_shown": (1, True, (DRUM1, 0), (DRUM1, 1), 1),
    "source_shown": (0, True, (DRUM1, 0), (DRUM1, 1), 0),
    "neither_shown": (2, True, (DRUM1, 0), (DRUM1, 1), 2),
    "drum1_to_drum2": (None, False, (DRUM1, 0), (DRUM2, 1), None),
}


@pytest.mark.parametrize("case", list(DUP_CASES))
def test_drum_duplicate(pl21_image, pl21_manifest, case):
    """The Patterns view's Duplicate: the target's 32 codes are the source's (q1_drums.py cases A-H: stock drops them
    when the target is the shown pattern and copies them otherwise; the handler copies at the entry, in every case);
    nothing else changes; a probability press on the target's step 3 keeps them."""
    chain, playing, src, dst, shown = DUP_CASES[case]
    h = fresh(pl21_image, pl21_manifest, chain=chain)
    if playing:
        start(h)
        assert h.shown_pattern(0) == shown
    before = all_codes(h)
    src_pat = drum_pat(h, *src)
    h.duplicate_pattern(src, dst)
    after = all_codes(h)
    assert drum_pat(h, *dst)[:0x84] == src_pat[:0x84]          # stock: the hits
    assert after[dst] == before[src]
    assert changed_only(before, after, {dst})
    if playing:
        h.play()
    h.prob_press(*dst, 3)
    assert drum_pat(h, *dst)[0x20 + 3] == 2 and codes(h, *dst) == before[src]


# ---- drums: Clear step, Clear pattern --------------------------------------------------------------------------------

def test_drum_clears(pl21_image, pl21_manifest):
    """Clear step: that step's code 0 (on the 17-32 page too), the rest kept; the pad again makes a hit with no
    condition. Clear pattern, shown (stopped) and not shown (playing another): its 36 condition bytes 0, nothing else;
    a probability press there keeps them 0."""
    h = fresh(pl21_image, pl21_manifest)
    before = all_codes(h)
    h.step_view(DRUM1)
    h.clear_step(3)
    h.press(HALF)
    h.clear_step(4)                              # step 20
    h.press(HALF)
    want = dict(before)
    want[(DRUM1, 0)] = [0 if s in (3, 20) else c for s, c in enumerate(before[(DRUM1, 0)])]
    pat = drum_pat(h, DRUM1, 0)
    assert pat[3] == 0 and pat[20] == 0                        # stock: the hits are gone
    assert all_codes(h) == want
    h.pad(3)                                     # a hit again
    assert drum_pat(h, DRUM1, 0)[3] and all_codes(h) == want

    h.clear_pattern_pv(DRUM1, 0)
    assert not any(drum_pat(h, DRUM1, 0)[:32])
    assert cond_bytes(h, DRUM1, 0) == bytes(0x24)
    want[(DRUM1, 0)] = [0] * 32
    assert all_codes(h) == want
    h.prob_press(DRUM1, 0, 3)
    assert drum_pat(h, DRUM1, 0)[3] and cond_bytes(h, DRUM1, 0) == bytes(0x24)

    h = fresh(pl21_image, pl21_manifest, chain=2)
    before = all_codes(h)
    start(h)
    h.clear_pattern_pv(DRUM1, 1)
    assert h.shown_pattern(0) == 2
    assert cond_bytes(h, DRUM1, 1) == bytes(0x24)
    assert changed_only(before, all_codes(h), {(DRUM1, 1)})
    h.play()
    h.prob_press(DRUM1, 1, 1)
    assert drum_pat(h, DRUM1, 1)[1] and cond_bytes(h, DRUM1, 1) == bytes(0x24)


# ---- drums: copy 1-16 -> 17-32, paste step ---------------------------------------------------------------------------

@pytest.mark.parametrize("page2", [False, True], ids=["1-16_shown", "17-32_shown"])
def test_drum_copy_half(pl21_image, pl21_manifest, page2):
    """Duplicate held + 1-16/17-32 (stock always copies steps 1-16 to 17-32, Q1): steps 17-32 get the codes of 1-16,
    1-16 keep theirs; a probability press on step 1 keeps them."""
    h = fresh(pl21_image, pl21_manifest)
    before = all_codes(h)
    h.step_view(DRUM1)
    if page2:
        h.press(HALF)
    h.copy_half()
    pat = drum_pat(h, DRUM1, 0)
    assert pat[16:32] == pat[:16]                              # stock: the hits
    want = before[(DRUM1, 0)][:16] * 2
    assert codes(h, DRUM1, 0) == want and changed_only(before, all_codes(h), {(DRUM1, 0)})
    h.prob_press(DRUM1, 0, 0)
    assert drum_pat(h, DRUM1, 0)[0x20] == 2 and codes(h, DRUM1, 0) == want


PASTE_CASES = {                                  # pad a, pad b, page switched, track pressed between; target (t, s)
    "same_page": (3, 7, False, None, (DRUM1, 7)),
    "across_pages": (3, 9, True, None, (DRUM1, 25)),
    "drum1_to_drum2": (3, 7, False, DRUM2, (DRUM2, 7)),
    "empty_onto_hit": (2, 0, False, None, (DRUM1, 0)),
}


@pytest.mark.parametrize("case", list(PASTE_CASES))
def test_drum_paste_step(pl21_image, pl21_manifest, case):
    """Duplicate held, step A, step B (the page switched, Drum 2's button between): the target step's code is the
    source's, an empty source's (a removal) 0; nothing else changes; a probability press on the target keeps it."""
    a, b, half, track, (tt, ts) = PASTE_CASES[case]
    h = fresh(pl21_image, pl21_manifest)
    before = all_codes(h)
    h.step_view(DRUM1)
    h.paste_step(a, b, half=half, track=track)
    src_vel = drum_pat(h, DRUM1, 0)[a]
    assert drum_pat(h, tt, 0)[ts] == src_vel                   # stock: the hit (or its removal)
    code = before[(DRUM1, 0)][a] if src_vel else 0
    want = dict(before)
    want[(tt, 0)] = [code if s == ts else c for s, c in enumerate(before[(tt, 0)])]
    assert all_codes(h) == want
    if ts < 16:
        h.prob_press(tt, 0, ts)
        assert drum_pat(h, tt, 0)[0x20 + ts] == 2 and all_codes(h) == want


# ---- drums: Mutate ---------------------------------------------------------------------------------------------------

def test_drum_mutate(pl21_image, pl21_manifest):
    """Shift + Duplicate, several times: each step's (velocity, probability, flip, micro, code) is one step's before,
    so every moved hit keeps its code; the other patterns keep theirs; a probability press on a hit keeps it."""
    h = fresh(pl21_image, pl21_manifest)
    for s in range(32):
        h.hit(DRUM1, 0, s, MUTATE_HITS.get(s, 0), prob=7 - s % 3, micro=1 if s in MUTATE_HITS else 0,
              code=CODE(DRUM1, 0, s))
    h.load_editors()
    before_all = all_codes(h)
    h.step_view(DRUM1)

    def tuples():
        pat = drum_pat(h, DRUM1, 0)
        return [(pat[s], pat[0x20 + s], pat[0x40 + s], pat[0x60 + s], h.code(DRUM1, 0, s)) for s in range(32)]
    moved = 0
    for _ in range(4):
        before = tuples()
        h.mutate()
        after = tuples()
        assert sorted(after) == sorted(before)
        moved += sum(1 for s in range(32) if after[s][0] and after[s] != before[s])
    assert moved                                                # stock moved hits
    assert changed_only(before_all, all_codes(h), {(DRUM1, 0)})
    last = tuples()
    s = next(k for k in range(16) if last[k][0])
    h.prob_press(DRUM1, 0, s)
    assert drum_pat(h, DRUM1, 0)[0x20 + s] == 2 and h.code(DRUM1, 0, s) == last[s][4]


# ---- note tracks -----------------------------------------------------------------------------------------------------

def test_note_clears(pl21_image, pl21_manifest):
    """Clear step on the selected step and on another: their [2]-[3] 0 (the fill's write buffer goes through the edit
    store), the rest kept; Clear pattern: [2]-[3] 0 on all 32 steps of the pattern. Then a step entry into a
    cleared step and a row-3 press on it keep 0."""
    h = fresh(pl21_image, pl21_manifest)
    before = all_codes(h)
    h.open_prob(SYNTH1)
    h.pad(3)                                     # step 3 selected
    assert h.selected(SYNTH1) == (0, 3)
    h.step_view(SYNTH1)
    h.clear_step(3)
    h.clear_step(6)                              # another step
    assert h.step_word(SYNTH1, 0, 3)[0] == 0 and h.step_word(SYNTH1, 0, 6)[0] == 0     # stock: the notes are gone
    want = dict(before)
    want[(SYNTH1, 0)] = [0 if s in (3, 6) else c for s, c in enumerate(before[(SYNTH1, 0)])]
    assert all_codes(h) == want

    def entry_and_prob(s):
        h.step_view(SYNTH1)
        h.down(s)
        h.down(KEY)
        h.up(KEY)
        h.up(s)
        h.heartbeat(5)
        assert h.step_word(SYNTH1, h.selected(SYNTH1)[0], s)[0]                  # stock: a note entered
        h.open_prob(SYNTH1)
        h.pad(s)
        h.pad(16 + 2)
    entry_and_prob(3)
    assert h.step_word(SYNTH1, 0, 3)[1] == 2 and all_codes(h) == want

    h.clear_pattern_pv(SYNTH1, 1)
    h.clear_pattern_pv(SYNTH1, 0)
    assert all(h.step_word(SYNTH1, p, s) == bytes([0, 7, 0, 0]) for p in (0, 1) for s in range(32))
    want[(SYNTH1, 0)] = want[(SYNTH1, 1)] = [0] * 32
    assert all_codes(h) == want
    entry_and_prob(5)
    assert h.step_word(SYNTH1, 0, 5)[1:] == bytes([2, 0, 0]) and all_codes(h) == want


def test_note_copies_still_carry(pl21_image, pl21_manifest):
    """Pinned (no hook): stock's Duplicate, paste step, copy 1-16 -> 17-32 and Mutate carry a note step's [2]-[3] with
    it, as in PL19 (A-storage.md Q2)."""
    h = fresh(pl21_image, pl21_manifest)
    before = all_codes(h)
    h.duplicate_pattern((SYNTH1, 0), (SYNTH1, 1))
    want = dict(before)
    want[(SYNTH1, 1)] = before[(SYNTH1, 0)]
    assert all_codes(h) == want
    h.step_view(SYNTH1)
    h.paste_step(3, 7)
    want[(SYNTH1, 1)] = [want[(SYNTH1, 1)][3] if s == 7 else c for s, c in enumerate(want[(SYNTH1, 1)])]
    assert all_codes(h) == want                  # the shown pattern is 1 now (Duplicate showed the target)
    h.copy_half()
    want[(SYNTH1, 1)] = want[(SYNTH1, 1)][:16] * 2
    assert all_codes(h) == want
    steps = [bytes(h.uc.mem_read(h.note_step_at(SYNTH1, 1, s), 28)) for s in range(32)]
    h.mutate()
    after = [bytes(h.uc.mem_read(h.note_step_at(SYNTH1, 1, s), 28)) for s in range(32)]
    assert sorted(after) == sorted(steps) and after != steps
    assert changed_only(want, all_codes(h), {(SYNTH1, 1)})


# ---- an unmarked project ---------------------------------------------------------------------------------------------

def edit_script(h):
    """Every edit above, stopped; the three tracks' patterns 0-3 after each."""
    snaps = []

    def snap():
        snaps.append([drum_pat(h, t, p) for t in (DRUM1, DRUM2) for p in range(4)] +
                     [bytes(h.uc.mem_read(h.note_step_at(SYNTH1, p, 0), 32 * 28)) for p in range(4)])
    h.duplicate_pattern((DRUM1, 0), (DRUM1, 1))
    snap()
    h.duplicate_pattern((DRUM1, 0), (DRUM2, 2))
    snap()
    h.step_view(DRUM1)
    h.clear_step(3)
    snap()
    h.copy_half()
    snap()
    h.paste_step(0, 7)
    h.paste_step(2, 0)
    h.paste_step(6, 4, track=DRUM2)
    snap()
    h.step_view(DRUM1)
    for _ in range(2):
        h.mutate()
    snap()
    h.clear_pattern_pv(DRUM1, 2)
    h.clear_pattern_pv(DRUM1, 1)
    snap()
    h.duplicate_pattern((SYNTH1, 0), (SYNTH1, 2))
    h.step_view(SYNTH1)
    h.clear_step(3)
    h.paste_step(0, 7)
    h.copy_half()
    h.mutate()
    snap()
    h.clear_pattern_pv(SYNTH1, 1)
    h.clear_pattern_pv(SYNTH1, 2)
    snap()
    return snaps


def test_unmarked_edits_as_pl19(pl21_image, pl21_manifest, pl19_published_image, pl19_published_manifest):
    """Mark 0, junk (CODE) in every condition byte: every edit above leaves the same pattern bytes as the published
    PL19 (no hook writes)."""
    pl20 = edit_script(fresh(pl21_image, pl21_manifest, mark=0))
    pl19 = edit_script(fresh(pl19_published_image, pl19_published_manifest, mark=None))
    assert len(pl20) == len(pl19)
    for k, (a, b) in enumerate(zip(pl20, pl19)):
        assert a == b, k


# ---- drums: a hit removed (Task 9) -----------------------------------------------------------------------------------

FLIP = 2                                         # the step's flip sample: the lower pad 16 + 2 removes it (drum_remove);
                                                 # drum d's lower pads are its samples 16 d + 0-15 (measured: Drum 2 16-31)
VEL_VIEW, GATE_VIEW = 10, 11                     # buttons: Velocity; Gate (on a drum: the micro-step view, mode 3)
MICRO_PAD = 16                                   # the micro-step view's pads 16-21 = micro bits 0-5
HIT_OFF = {                                      # (pattern shown and written, step, playing, marked)
    "stopped": (0, 3, False, 1),
    "playing_17-32": (1, 20, True, 1),
    "unmarked": (0, 3, False, 0),
}


def hit_off_setup(image, m, case, drum=DRUM1):
    """The drum (Drum 1 unless given): 32-step loops; a hit (flip FLIP on its sample page, micro 0x01) on step s of
    pattern p and one (micro 0x03) on step s + 2; CODE on every step of patterns 0-1 of the three tracks; marked or
    not. Playing: pattern 1 plays and is shown, the editors do not follow the playhead (the page and the selection
    stay)."""
    p, s, playing, mark = HIT_OFF[case]
    h = TrigHarness(image, m)
    cfg = loops(32)
    cfg[drum]["chain"] = (p, p)
    trig_setup(h, cfg)
    h.clear_steps()
    h.hit(drum, p, s, 90, flip=FLIP + 16 * (drum - DRUM1), micro=0x01)
    h.hit(drum, p, s + 2, 80, micro=0x03)
    for t in TRACKS:
        for q in range(2):
            for k in range(32):
                h.set_code(t, q, k, CODE(t, q, k))
    h.load_editors()
    h.mark(mark)
    if playing:
        start(h)
        h.follow(False)
    assert h.shown_pattern(drum - DRUM1) == p
    return h, p, s


def open_step(h, how, s, page_pressed=False, drum=DRUM1):
    """The view `how` acts in, on step s's page: the drum step view, or the micro-step view (Gate) with step s selected
    in the velocity view first (a tap there selects, it does not toggle)."""
    if how == "micro_off":
        h.press(drum)
        h.press(VEL_VIEW)
        assert h.view_mode() == 2
        if s >= 16 and not page_pressed:
            h.press(HALF)
        h.pad(s % 16)
        h.press(GATE_VIEW)
        assert h.view_mode() == 3
        return
    h.step_view(drum)
    if s >= 16 and not page_pressed:
        h.press(HALF)


def toggle(h, how, s):
    """Step s's hit off (or, on an empty step, on): a step pad tap (drum_step_off); the step held + the lower pad of
    its flip sample (drum_remove; on an empty step it adds a hit with that flip); its micro pad 0 (drum_micro_off)."""
    if how == "step_off":
        h.pad(s % 16)
    elif how == "remove":
        h.down(s % 16)
        h.pad(16 + FLIP)
        h.up(s % 16)
    else:
        h.pad(MICRO_PAD)


@pytest.mark.parametrize("drum", [DRUM1, DRUM2], ids=["drum1", "drum2"])
@pytest.mark.parametrize("case", list(HIT_OFF))
@pytest.mark.parametrize("how", ["step_off", "remove", "micro_off"])
def test_drum_hit_off_drops_its_condition(pl21_image, pl21_manifest, how, case, drum):
    """The three routes that empty a drum step (2026-11-07 spike Q5): a step pad tapped off, a step held + the lower
    pad of its flip sample, the micro-step view's last micro bit off. The step's code goes (in the drum's shown
    pattern: pattern 1 playing on the 17-32 page), nothing else changes; the pad again makes a hit with no condition.
    In the micro-step view a pad that leaves a bit set keeps the code. Unmarked: nothing changes (as PL19). Drum 1 and
    Drum 2: the drum editor table (0x20039D04 + 4 d) is read per drum."""
    h, p, s = hit_off_setup(pl21_image, pl21_manifest, case, drum)
    marked = HIT_OFF[case][3]
    before = all_codes(h)
    open_step(h, how, s, drum=drum)
    toggle(h, how, s)
    assert drum_pat(h, drum, p)[s] == 0                        # stock: the hit is gone
    want = dict(before)
    if marked:
        want[(drum, p)] = [0 if k == s else c for k, c in enumerate(before[(drum, p)])]
    assert all_codes(h) == want
    toggle(h, how, s)                                          # the pad again: a hit, no condition
    assert drum_pat(h, drum, p)[s] and all_codes(h) == want
    if how == "micro_off":                                     # step s + 2: micro 0x03, bit 0 off leaves bit 1
        open_step(h, how, s + 2, page_pressed=True, drum=drum)
        h.pad(MICRO_PAD)
        pat = drum_pat(h, drum, p)
        assert pat[s + 2] == 80 and pat[0x60 + s + 2] == 0x02 and all_codes(h) == want
