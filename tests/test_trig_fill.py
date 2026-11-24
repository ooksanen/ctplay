"""PL20 Task 7: FILL per drum on the drum expanded view (Drum N, then Note again): pads 21-24 (the controller's 20-23)
= FILL for drums 1-4. Hold = FILL on while held; a tap (< ½ s) while playing arms it for the drum's next whole pass,
a tap while armed (or during that pass) disarms, Stop ends it, a tap while stopped does nothing. LEDs: bright orange
on, yellow armed, dim orange otherwise; only in the expanded view and only with no CTPlay page over it. The press and
release come through the view's own handlers (hooks wide_drum_press / wide_drum_release), which get exactly one
release per press, view changes included. Plan 2026-11-07-trig-conditions.md, Task 7 and Global Constraints
"Two-task rule", "Timing", "Colours"; evidence docs/investigations/2026-11-01-trig-conditions-spike/C-controls.md
(Q2, Q3, Q4).

Everything through the controller (pads, buttons, Play) and the Main task's 1 ms service (`heartbeat`, which counts
trig_ms). Every test: 240 BPM, every track an 8-step loop of pattern 0 (a pass = 48 ticks = 500 ms), the project
marked; Drum 1 (and Drum 2 where named): a plain hit on step 0, FILL on steps 1 and 5, NOT FILL on steps 2 and 6."""
import pytest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R1

import trig_model as tm
from drums import sym
from harness import MGR
from trig import BTN_NOTE, CONT, FILL_PAD, MIXER, PATTERNS_VIEW, TrigHarness, loops, trig_setup

pytestmark = pytest.mark.emu

FILL, NOT_FILL = tm.TRIG_SPECIAL[2], tm.TRIG_SPECIAL[3]
DRUM1, DRUM2 = 4, 5
PLAIN, FILL_STEPS, NOT_STEPS = 0, (1, 5), (2, 6)
ON, DIM, ARMED = tm.COL_ORANGE, tm.COL_ORANGE_DIM, tm.COL_YELLOW
PASS = 48                                          # ticks of an 8-step pass at 1/16
WIDE_RELEASE = 0x0804ED68                          # the expanded view's release (hook wide_drum_release)


def fresh(image, m, drums=(0,)):
    h = TrigHarness(image, m)
    trig_setup(h, loops(8))
    h.clear_steps()
    for d in drums:
        h.hit(4 + d, 0, PLAIN)
        for s in FILL_STEPS:
            h.hit(4 + d, 0, s, code=FILL)
        for s in NOT_STEPS:
            h.hit(4 + d, 0, s, code=NOT_FILL)
    h.load_editors()
    h.mark(1)
    h.open_wide(0)
    return h


def start(h, ticks=PASS + 4):
    """Play from stop; `ticks` in (default: 4 ticks into the second pass, past its step 0)."""
    h.clear_logs()
    h.play()
    h.run_ticks(ticks)


def check(h, t, on):
    """Every tick 0 of track t so far: the plain step sounded; a FILL step iff on(ticks), a NOT FILL step iff not."""
    seen = {True: 0, False: 0}
    for ticks, s, sounded in h.heard(t):
        if s == PLAIN:
            assert sounded, (t, ticks, s)
        elif s in FILL_STEPS + NOT_STEPS:
            want = on(ticks) == (s in FILL_STEPS)
            assert sounded == want, (t, ticks, s, sounded)
            seen[on(ticks)] += 1
    return seen


def never(ticks):
    return False


def tap(h, d=0, ms=100):
    """FILL pad of drum d held `ms` (a tap below 500): returns the ticks it was down over, (a, b]: FILL is on there
    too, as for any press."""
    a = h.ticks
    h.fill(d, ms)
    return a, h.ticks


def within(x, *spans):
    """x in one of the half-open tick spans (a, b] (a press) given as ("p", a, b), or [a, b) (a pass) as ("s", a, b)."""
    return any(a < x <= b if k == "p" else a <= x < b for k, a, b in spans)


# ---- hold and tap ---------------------------------------------------------------------------------------------------

def test_hold(pl21_image, pl21_manifest):
    """Pad 21 held 1 s mid-pattern: Drum 1's FILL steps sound only while it is held, its NOT FILL steps only when not;
    the LED bright while held, dim after."""
    h = fresh(pl21_image, pl21_manifest)
    start(h, PASS + 20)
    assert h.fill_leds() == [DIM] * 4
    a = h.ticks
    h.down(FILL_PAD)
    h.heartbeat(1)
    assert h.fill_leds() == [ON, DIM, DIM, DIM]
    h.heartbeat(999)
    assert h.fill_leds() == [ON, DIM, DIM, DIM]
    b = h.ticks
    h.up(FILL_PAD)
    assert h.fill_leds() == [DIM] * 4
    h.run_ticks(2 * PASS)
    seen = check(h, DRUM1, lambda x: a < x <= b)
    assert seen[True] >= 6 and seen[False] >= 6
    assert h.fill_state()["arm"] == [0] * 4         # a hold arms nothing


def test_tap_arms_the_next_whole_pass(pl21_image, pl21_manifest):
    """A 100 ms tap mid-pass: yellow; the next pass fills (bright) from its start to its end, the one after not (dim).
    A tap after that arms again."""
    h = fresh(pl21_image, pl21_manifest)
    start(h)
    t1 = tap(h)
    assert h.fill_leds() == [ARMED, DIM, DIM, DIM]
    a = h.until_pass(DRUM1)
    h.run_ticks(10)
    assert h.fill_leds() == [ON, DIM, DIM, DIM]
    b = h.until_pass(DRUM1)
    h.run_ticks(10)
    assert h.fill_leds() == [DIM] * 4
    t2 = tap(h)                                      # again, after the fill ended: armed again
    assert h.fill_leds() == [ARMED, DIM, DIM, DIM]
    c = h.until_pass(DRUM1)
    h.run_ticks(10)
    assert h.fill_leds() == [ON, DIM, DIM, DIM]
    e = h.until_pass(DRUM1)
    h.run_ticks(PASS)
    assert h.fill_leds() == [DIM] * 4
    check(h, DRUM1, lambda x: within(x, ("p", *t1), ("p", *t2), ("s", a, b), ("s", c, e)))
    fills = [s for x, s, _ in h.heard(DRUM1) if within(x, ("s", a, b), ("s", c, e)) and s in FILL_STEPS + NOT_STEPS]
    assert sorted(fills) == [1, 1, 2, 2, 5, 5, 6, 6]      # two whole passes: every FILL / NOT FILL step of each


@pytest.mark.parametrize("when", ["armed", "running"])
def test_tap_again_disarms(pl21_image, pl21_manifest, when):
    """A second tap while armed: dim, nothing fills. During the fill pass: dim, the fill ends at the next step."""
    h = fresh(pl21_image, pl21_manifest)
    start(h)
    t1 = tap(h)
    assert h.fill_leds() == [ARMED, DIM, DIM, DIM]
    if when == "armed":
        t2 = tap(h)
        assert h.fill_leds() == [DIM] * 4
        h.run_ticks(3 * PASS)
        seen = check(h, DRUM1, lambda x: within(x, ("p", *t1), ("p", *t2)))
        assert h.fill_leds() == [DIM] * 4
    else:
        a = h.until_pass(DRUM1)
        h.run_ticks(14)                              # past steps 1 and 2 (ticks 6, 12)
        _, b = tap(h)                                # ~10 ticks: released before step 5 (tick 30)
        assert h.fill_leds() == [DIM] * 4
        h.run_ticks(2 * PASS)
        seen = check(h, DRUM1, lambda x: within(x, ("p", *t1), ("s", a, b + 1)))
        fills = [s for x, s, _ in h.heard(DRUM1) if a <= x <= b and s in FILL_STEPS + NOT_STEPS]
        assert fills == [1, 2]                       # the fill pass's steps 1 and 2, then off from step 5
    assert seen[False] >= 8


@pytest.mark.parametrize("when", ["armed", "running"])
def test_stop_ends_it(pl21_image, pl21_manifest, when):
    """Armed (or during its fill pass), Stop: dim; Play again: no fill."""
    h = fresh(pl21_image, pl21_manifest)
    start(h)
    tap(h)
    if when == "running":
        h.until_pass(DRUM1)
        h.run_ticks(10)
        assert h.fill_leds() == [ON, DIM, DIM, DIM]
    else:
        assert h.fill_leds() == [ARMED, DIM, DIM, DIM]
    h.play()                                         # Stop
    h.heartbeat(5)
    assert h.fill_leds() == [DIM] * 4
    h.heartbeat(200)
    start(h, 3 * PASS)
    assert h.fill_leds() == [DIM] * 4
    seen = check(h, DRUM1, never)
    assert seen[False] >= 12


def test_tap_while_stopped_does_nothing(pl21_image, pl21_manifest):
    """Stopped: a tap leaves every FILL byte as it was and the LED dim; Play: no fill."""
    h = fresh(pl21_image, pl21_manifest)
    before = h.fill_state()
    h.fill(0, 100)
    assert h.fill_state() == before and h.fill_leds() == [DIM] * 4
    start(h, 3 * PASS)
    seen = check(h, DRUM1, never)
    assert seen[False] >= 12


def test_per_drum(pl21_image, pl21_manifest):
    """Pad 22 acts on Drum 2 only: held, then tapped."""
    h = fresh(pl21_image, pl21_manifest, drums=(0, 1))
    start(h, PASS + 20)
    a = h.ticks
    h.down(FILL_PAD + 1)
    h.heartbeat(700)
    assert h.fill_leds() == [DIM, ON, DIM, DIM]
    b = h.ticks
    h.up(FILL_PAD + 1)
    h.run_ticks(10)
    t1 = tap(h, 1)
    assert h.fill_leds() == [DIM, ARMED, DIM, DIM]
    c = h.until_pass(DRUM2)
    h.run_ticks(10)
    assert h.fill_leds() == [DIM, ON, DIM, DIM]
    e = h.until_pass(DRUM2)
    h.run_ticks(PASS)
    assert h.fill_leds() == [DIM] * 4
    assert check(h, DRUM2, lambda x: within(x, ("p", a, b), ("p", *t1), ("s", c, e)))[True] >= 8
    assert check(h, DRUM1, never)[False] >= 16
    st = h.fill_state()
    assert st["arm"][0] == st["arm"][2] == st["arm"][3] == 0 and st["started"][0] == st["done"][0] == 0


@pytest.mark.parametrize("ms, tap", [(499, True), (500, False), (501, False)])
def test_split(pl21_image, pl21_manifest, ms, tap):
    """Held 499 ms: a tap (armed, the next pass fills); 500 or 501 ms: a hold (nothing armed after it)."""
    h = fresh(pl21_image, pl21_manifest)
    start(h, PASS + 2)
    a = h.ticks
    h.fill(0, ms)
    b = h.ticks
    assert h.fill_leds() == [ARMED if tap else DIM, DIM, DIM, DIM]
    c = h.until_pass(DRUM1)
    e = h.until_pass(DRUM1)
    h.run_ticks(4)
    check(h, DRUM1, lambda x: a < x <= b or (tap and c <= x < e))


@pytest.mark.parametrize("ms, armed", [(600, False), (100, True)])
def test_view_change_while_held(pl21_image, pl21_manifest, ms, armed):
    """Pad 21 held, then Note: the view's release comes at the view change (the hold ends there: fill off; held 100 ms
    it is a tap there); the late finger release does nothing."""
    h = fresh(pl21_image, pl21_manifest)
    releases = []

    def rel(u, a, s, d):
        releases.append(u.reg_read(UC_ARM_REG_R1))
    h.uc.hook_add(UC_HOOK_CODE, rel, begin=WIDE_RELEASE, end=WIDE_RELEASE)
    start(h, PASS + 2)
    a = h.ticks
    h.down(FILL_PAD)
    h.heartbeat(ms)
    b = h.ticks
    h.press(BTN_NOTE)
    assert h.view_mode() != 6
    assert releases == [FILL_PAD]
    st = h.fill_state()
    assert st["hold"] == 0 and (st["arm"][0] & 1) == armed
    itcm = bytes(h.uc.mem_read(sym(h.m, "trig_fill_hold"), 1)) + bytes(h.uc.mem_read(sym(h.m, "trig_fill_arm"), 4))
    h.up(FILL_PAD)
    assert releases == [FILL_PAD]
    assert bytes(h.uc.mem_read(sym(h.m, "trig_fill_hold"), 1)) + bytes(h.uc.mem_read(sym(h.m, "trig_fill_arm"), 4)) \
        == itcm
    c = h.until_pass(DRUM1)
    e = h.until_pass(DRUM1)
    h.run_ticks(4)
    check(h, DRUM1, lambda x: a < x <= b or (armed and c <= x < e))


# ---- stock and the pages --------------------------------------------------------------------------------------------

def test_drum_page_covers(pl21_image, pl21_manifest, pl19_published_image, pl19_published_manifest):
    """Shift + Drum 1 on the expanded view: drum 1's page covers it; pads 21-24 are the page's (LEDs as PL19's, a
    press there is the page's: no FILL)."""
    out = {}
    for name, img, m in (("pl19", pl19_published_image, pl19_published_manifest),
                         ("pl20", pl21_image, pl21_manifest)):
        h = TrigHarness(img, m)
        trig_setup(h, loops(8))
        h.clear_steps()
        for s in range(8):
            h.hit(DRUM1, 0, s)
        h.load_editors()
        h.open_wide(0)
        h.press(4, shift=True)
        assert h.view_mode() == 6
        frames = [h.leds()[:32]]
        h.play()
        h.heartbeat(30)
        h.down(FILL_PAD)
        h.heartbeat(600)
        frames.append(h.leds()[:32])
        if name == "pl20":
            assert h.fill_state()["hold"] == 0
        h.up(FILL_PAD)
        h.fill(1, 100)
        frames.append(h.leds()[:32])
        if name == "pl20":
            st = h.fill_state()
            assert st["hold"] == 0 and st["arm"] == [0] * 4
        out[name] = frames
    assert out["pl20"] == out["pl19"]


@pytest.mark.parametrize("playing", [False, True], ids=["stopped", "playing"])
def test_drum_pads_unchanged(pl21_image, pl21_manifest, pl19_published_image, pl19_published_manifest, playing):
    """Drum pads 29-32 with pad 21 held (and pad 21 tapped while drum pad 29 is held): the same sink calls, endpoint
    events and RAM as the published PL19 (C-controls.md Q4)."""
    out = {}
    for name, img, m in (("pl19", pl19_published_image, pl19_published_manifest),
                         ("pl20", pl21_image, pl21_manifest)):
        h = TrigHarness(img, m)
        trig_setup(h, loops(8))
        h.open_wide(0)
        if playing:
            h.play()
            h.heartbeat(30)
        h.take()
        h.sent.clear()
        h.down(FILL_PAD)
        h.heartbeat(1)
        for p in range(28, 32):
            h.down(p)
            h.heartbeat(2)
            h.up(p)
            h.heartbeat(2)
        h.up(FILL_PAD)
        h.down(28)
        h.heartbeat(2)
        h.fill(0, 50)
        h.up(28)
        h.heartbeat(5)
        lo, hi = int(m["ram"]["start"], 16), int(m["ram"]["end"], 16)
        ram = bytearray(h.uc.mem_read(0x20000000, 0x50000))
        ram[lo - 0x20000000:hi - 0x20000000] = bytes(hi - lo)      # slim's own RAM (its layout is the build's)
        out[name] = list(h.sent), h.take(), bytes(ram)
    assert out["pl20"][0] == out["pl19"][0] and len(out["pl20"][0]) >= 10
    assert out["pl20"][1] == out["pl19"][1]
    assert out["pl20"][2] == out["pl19"][2]


def test_fill_leds_only_in_the_expanded_view(pl21_image, pl21_manifest, pl19_published_image,
                                             pl19_published_manifest):
    """Every FILL held (raw): pads 21-24 lit in the expanded view only; Drum 1's own view (mode 1), its probability
    view, the note tracks' views (Note, the expanded Note view) and Patterns / Mixer over the expanded view keep pads
    21-24 as PL19's."""
    out = {}
    for name, img, m in (("pl19", pl19_published_image, pl19_published_manifest),
                         ("pl20", pl21_image, pl21_manifest)):
        h = TrigHarness(img, m)
        trig_setup(h, loops(8))
        if name == "pl20":
            h.uc.mem_write(sym(m, "trig_fill_hold"), bytes([0x0F]))
        frames = []
        h.press(4)
        for _ in range(3):
            if h.view_mode() == 1:
                break
            h.press(BTN_NOTE)
        assert h.view_mode() == 1
        frames.append(h.leds()[:32])
        h.open_prob(DRUM1)
        frames.append(h.leds()[:32])
        h.track(0)
        frames.append(h.leds()[:32])
        h.track(0, mode=6)
        frames.append(h.leds()[:32])
        h.open_wide(0)
        wide = h.leds()[:32]
        h.press(PATTERNS_VIEW)
        frames.append(h.leds()[:32])
        h.open_wide(0)
        h.press(MIXER)
        assert h.r32(MGR + 0x6C) != CONT
        frames.append(h.leds()[:32])
        out[name] = frames, wide
    assert out["pl20"][0] == out["pl19"][0]
    assert out["pl20"][1][FILL_PAD:FILL_PAD + 4] == [ON] * 4
    assert out["pl19"][1][FILL_PAD:FILL_PAD + 4] == [0] * 4
    assert out["pl20"][1][:FILL_PAD] + out["pl20"][1][FILL_PAD + 4:] == \
        out["pl19"][1][:FILL_PAD] + out["pl19"][1][FILL_PAD + 4:]
