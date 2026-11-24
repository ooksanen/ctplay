"""Pattern strum, recording (PL19, spec 2026-10-28-playback-strum-design.md, "Written: the strum in ticks", "Played:
recording", "Written: recording"; features/chord/pstrum_rec.c). A live strummed press on a Played track records as a
plain chord; on a Written track as a roll (note k at the first note's position + k x WRITTEN_GAP ticks, spilling into
later steps, wrapping at the pattern's end), record quantise on or off. On a Written track the live strum's gaps are
sequencer ticks. All through the real route: Play, Record, pads, heartbeats (Main's 1 ms service), stock's recorder.

The reference for each case's outcome is the spike's model of the rule (docs/investigations/2026-10-31-pattern-strum-
spike/q1_scope.py and its .out). Steps here are 0-based (q1_scope prints them 1-based)."""
import pytest
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R4, UC_ARM_REG_R8

import roll_model as rm
from chord_model import settings
from notes import (NoteHarness, PATTERN, PATTERN_BASE, STEP, endpoint_note, pattern_snapshot, recorded_notes,
                   set_tempo, step_addr)
from test_chord import set_chord, set_down, set_strum
from test_mono import quantise_off, set_mono

pytestmark = pytest.mark.emu
RECORDERS = 0x2003C174
OFF_SITE, PASS_SITE, FLUSH_SITE, COMMIT = 0x0803F606, 0x0803F786, 0x0803F6A2, 0x0803F7BE
PLACE = 0x0803F298
SET = 0x380                                      # pattern + 0x380 last step, + 0x381 first, + 0x382 sync rate
PLAY, RECORD = 17, 16
OFF, PLAYED, WRITTEN = 0, 1, 2
GAP_MS = {1: 80, 2: 40, 3: 20}                   # chord.c STRUM_GAP
OLD = [30, 31]                                   # older notes on the steps a strum records over: they must survive
FILL = [70, 71, 72, 73, 74, 75]                  # a full step
C, E, G = 48, 51, 55                             # pad 24's triad in the dump's scale (C minor: E = Eb)


def sym(m, name):
    return int(m["symbols"][name], 16)


def W(w):
    """A converted pending word."""
    return dict(unit=w & 7, step=w >> 3 & 31, pattern=w >> 8 & 7, vel=w >> 11 & 0x7F, start=w >> 18 & 0x7FF,
                micro=w >> 29)


class RH(NoteHarness):
    """NoteHarness + track 0's recorder: every commit of a note (its word at the commit's call site, before slim's
    mid hooks: `pre`; at the commit's entry, after them: `post`), the task (heartbeats: main), placements."""

    def __init__(self, image, m):
        super().__init__(image)
        self.m = m
        self.task, self.ms = "ui", 0
        self.commits, self.places, self._pre = [], [], {}
        uc = self.uc

        def site(name, rn, rr):
            def f(u, a, s, d):
                if u.reg_read(rr) == self.rec():
                    n = u.reg_read(rn)
                    self._pre[n] = (name, self.pending(n))
            return f
        uc.hook_add(UC_HOOK_CODE, site("off", UC_ARM_REG_R0, UC_ARM_REG_R4), begin=OFF_SITE, end=OFF_SITE)
        uc.hook_add(UC_HOOK_CODE, site("pass", UC_ARM_REG_R1, UC_ARM_REG_R8), begin=PASS_SITE, end=PASS_SITE)
        uc.hook_add(UC_HOOK_CODE, site("flush", UC_ARM_REG_R1, UC_ARM_REG_R0), begin=FLUSH_SITE, end=FLUSH_SITE)

        def commit(u, a, s, d):
            if u.reg_read(UC_ARM_REG_R0) != self.rec():
                return
            n, end = u.reg_read(UC_ARM_REG_R1), u.reg_read(UC_ARM_REG_R2) & 0x7FF
            where, pre = self._pre.pop(n, ("?", None))
            post = self.pending(n)
            if (pre if pre is not None else post) & 7 != 7:
                self.commits.append(dict(note=n, end=end, task=self.task, site=where, pre=pre, post=post, ms=self.ms))
        uc.hook_add(UC_HOOK_CODE, commit, begin=COMMIT, end=COMMIT)

        def place(u, a, s, d):
            if u.reg_read(UC_ARM_REG_R0) == self.rec():
                self.places.append((self.ms, self.task, self.r8(self.rec() + 0x9C)))
        uc.hook_add(UC_HOOK_CODE, place, begin=PLACE, end=PLACE)

    def heartbeat(self, n=1):
        self.task = "main"
        for _ in range(n):
            super().heartbeat(1)
            self.ms += 1
        self.task = "ui"

    def rec(self):
        return self.r32(RECORDERS)

    def pending(self, n):
        return self.r32(self.rec() + 0x9C + 4 * n)

    def tick(self):
        return self.r32(sym(self.m, "arp_tick"))

    def moved(self):
        """(note, task, site) of every commit whose word a mid hook changed."""
        return [(c["note"], c["task"], c["site"]) for c in self.commits if c["pre"] is not None and c["pre"] != c["post"]]

    def first_commit(self, note):
        return next(c for c in self.commits if c["note"] == note)


def set_pstrum(h, m, t, mode):
    h.call(sym(m, "slim_ready"))
    a = sym(m, "chord_pstrum")
    h.uc.mem_write(a, bytes([h.r8(a) & ~(3 << 2 * t) | mode << 2 * t]))


def setup(image, m, mode=WRITTEN, speed=1, down=False, quantise=True, shape=1, bass=0, last=31, first=0, rate=3,
          olds=range(4, 12), full=(), mono=False, play=True, record=True, bpm=None):
    """Track 0 in its Note view; every note track's patterns emptied, track 0's pattern 0 with steps first .. last at
    `rate` (3 = 1/16, 5 = 1/8), OLD on `olds`, FILL on `full`; the chord, strum speed / direction and pattern strum;
    Play and Record (stock's quantise on unless `quantise` is False)."""
    h = RH(image, m)
    h.leds()                                         # slim's power-on init
    h.track(0)
    if bpm:
        set_tempo(h, bpm=bpm)
    for t in range(4):
        h.uc.mem_write(PATTERN_BASE[t], bytes(8 * PATTERN))
    h.uc.mem_write(PATTERN_BASE[0] + SET, bytes([last, first, rate]))
    for s in olds:
        put(h, s, OLD)
    for s in full:
        put(h, s, FILL)
    set_chord(h, m, 0, settings(shape, bass=bass))
    set_strum(h, m, 0, speed)
    set_down(h, m, 0, down)
    if "chord_pstrum" in m["symbols"]:
        set_pstrum(h, m, 0, mode)
    if mono:
        set_mono(h, m, 0)
    if play:
        h.press(PLAY)
        if record:
            h.recording(True)
        h.heartbeat(3)
        if not quantise:
            quantise_off(h)
    h.take()
    return h


def put(h, s, notes, p=0):
    body = b"".join(bytes([n, 6, 0, 90]) for n in notes) + bytes(4 * (6 - len(notes)))
    h.uc.mem_write(step_addr(0, p, s), bytes([(1 << len(notes)) - 1, 7, 0, 0]) + body)


def unit_map(h, s, p=0):
    a = step_addr(0, p, s)
    mask = h.r8(a)
    return {u: tuple(h.uc.mem_read(a + 4 + 4 * u, 4)) for u in range(6) if mask >> u & 1}


def snapshot(h):
    return {s: unit_map(h, s) for s in range(32)}


def wait_tick(h, tick):
    while h.tick() < tick:
        h.heartbeat(1)


def hold_until(h, note, extra=0, limit=1000):
    """Heartbeats until track 0's synth plays `note` (a keyboard pitch) from now on, then `extra` more."""
    want = endpoint_note(h, note)
    h.take()
    for _ in range(limit):
        h.heartbeat(1)
        if any(e[1] == 0 and e[2] == want for e in h.take("synth_on")):
            break
    else:
        raise AssertionError(f"note {note} never sounded")
    h.heartbeat(extra)


def strum(h, pad=24, hold=600, after=400, at=40):
    if at is not None:
        wait_tick(h, at)
    h.down(pad)
    h.heartbeat(hold)
    h.up(pad)
    h.heartbeat(after)


def send_order(notes, root, down):
    """Every note of the strum in send order (k = the index): rising, the pad's own note first, then the others
    rising; falling, all by pitch, highest first."""
    others = sorted(n for n in notes if n != root)
    return sorted(notes, reverse=True) if down else [root] + others


def stock_gate(held, per):
    """Stock's commit (0x0803F848-0x0803F884): sixths from the ticks held."""
    steps = held // per
    if steps >= 16:
        return 96
    return max(1, 6 * steps + (held - steps * per) * 6 // per)


def expected(h, order, mode, gap, per, first=0, last=31):
    """note -> (step, micro, gate) by the rule (q1_route_a's model): the first's own word (stock's place) gives the
    position; Played: every note there; Written: + k x gap ticks; the length from each note's own start to its end."""
    F = W(h.first_commit(order[0])["post"])
    out = {}
    for k, n in enumerate(order):
        if mode == PLAYED:
            s, mi, st = F["step"], F["micro"], F["start"]
        else:
            six = F["micro"] + rm.roll_sixths(k * gap, per)
            s, mi, st = rm.roll_step(F["step"], six // 6, first, last), six % 6, (F["start"] + k * gap) & 0x7FF
        end = h.first_commit(n)["end"]
        held = (end - st) & 0x7FF
        if held >= 0x400:
            held = 1                                 # let go before its own position: start = end - 1
        out[n] = (s, mi, stock_gate(held, per))
    return out


def where(h, notes):
    """note -> [(step, micro, gate)] of every unit of pattern 0 holding it."""
    out = {}
    for s in range(32):
        for v in unit_map(h, s).values():
            if v[0] in notes:
                out.setdefault(v[0], []).append((s, v[2], v[1] & 0x7F))
    return out


def ghosts(h):
    """Units with a mask bit and no note (a reservation never committed)."""
    return [(s, u) for s in range(32) for u in range(6)
            if h.r8(step_addr(0, 0, s)) >> u & 1 and h.r8(step_addr(0, 0, s) + 4 + 4 * u) == 0]


def lost(before, h, keep=()):
    """Older units changed or gone (steps in `keep` excepted)."""
    now = snapshot(h)
    return [(s, u, v) for s, units in before.items() if s not in keep for u, v in units.items() if now[s].get(u) != v]


def strum_notes(h):
    return sorted({c["note"] for c in h.commits} - set(OLD))


# ---- the live strum in ticks

def tick_log(h, n, synth=0):
    """n heartbeats: (heartbeat index, arp_tick as chord_on_ms reads it, endpoint note) of every synth note-on, and
    the arp_tick each heartbeat read."""
    out, ticks = [], []
    for i in range(n):
        tk = h.tick()
        ticks.append(tk)
        h.heartbeat(1)
        out += [(i, tk, e[2]) for e in h.take("synth_on") if e[1] == synth]
    return out, ticks


@pytest.mark.parametrize("speed", [1, 2, 3], ids=["slow", "medium", "fast"])
@pytest.mark.parametrize("playing, record", [(True, True), (True, False), (False, False)],
                         ids=["recording", "playing", "stopped"])
def test_written_live_gaps(pl19_image, pl19_manifest, playing, record, speed):
    """Written: note k k x WRITTEN_GAP ticks after the first (the first heartbeat that reads the tick it is due on).
    Recording, the press is taken (HELD_OWN_ROOT): the pad's own note on the first heartbeat after the press. Not
    recording, stock sounds it at the press (PL18's rising path, so pad-first step entry sees its pitch) and the others
    count from the press's tick. Stopped, the clock runs at the project's tempo (90 BPM)."""
    h = setup(pl19_image, pl19_manifest, speed=speed, play=playing, record=record, bpm=90, olds=())
    h.heartbeat(50)
    pressed = h.tick()
    h.down(24)
    at_press = [e[2] for e in h.take("synth_on") if e[1] == 0]
    log, ticks = tick_log(h, 900)
    h.up(24)
    h.heartbeat(5)
    gap = rm.WRITTEN_GAP[speed]
    root = endpoint_note(h, h.pitch(0, 24))
    if record:
        assert at_press == []                                                      # the press is taken: nothing yet
        assert [n for _, _, n in log] == [root, root + 3, root + 7]              # C Eb G, rising
        (i0, t0, _), rest = log[0], log[1:]
        assert i0 == 0                                                             # the first heartbeat
    else:
        assert at_press == [root]                                                  # stock's own note at the press
        assert [n for _, _, n in log] == [root + 3, root + 7]
        t0, rest = pressed, log
    for k, (i, t, n) in enumerate(rest, 1):
        assert t == t0 + k * gap, (k, t, t0)                                       # sent on the tick it is due
        assert i > 0 and ticks[i - 1] < t0 + k * gap                             # ... and not a heartbeat earlier
    assert not [k for k in h.sounding if k[:2] == ("synth", 0)]                # the strum ended (the pattern plays on)


def test_written_strum_across_play(pl19_image, pl19_manifest):
    """Play resets arp_tick to 0 while a Written live strum is held (stopped, slow): the heartbeat counts the ticks from
    the reset, so the strum's next gap is not collapsed. The 3rd follows the press's tick + 4 x 2 ticks, never the
    first heartbeat after Play."""
    h = setup(pl19_image, pl19_manifest, speed=1, play=False, record=False, bpm=90, olds=())
    h.heartbeat(50)
    root = endpoint_note(h, h.pitch(0, 24))
    h.down(24)
    assert [e[2] for e in h.take("synth_on") if e[1] == 0] == [root]
    ms = 0
    while not [e for e in h.take("synth_on") if e[1] == 0 and e[2] == root + 3]:
        h.heartbeat(1)
        ms += 1
        assert ms < 500
    h.heartbeat(2)
    h.press(PLAY)                                      # the next heartbeat resets arp_tick to 0
    after = None
    for i in range(1, 400):
        h.heartbeat(1)
        if [e for e in h.take("synth_on") if e[1] == 0 and e[2] == root + 7]:
            after = i
            break
    h.up(24)
    h.press(PLAY)
    h.heartbeat(300)
    assert after is not None and after > 40, after      # one gap is 4 ticks (~110 ms at 90 BPM), not one heartbeat
    assert not [k for k in h.sounding if k[:2] == ("synth", 0)]


def test_record_on_mid_strum(pl19_image, pl19_manifest):
    """Record goes on while a Written strum pressed before it is under way: the strum has no root identity (no
    HELD_OWN_ROOT), so its later notes record where stock places them; no move, no reservation left behind."""
    h = setup(pl19_image, pl19_manifest, speed=1, record=False, olds=())
    wait_tick(h, 40)
    h.down(24)
    assert [e[2] for e in h.take("synth_on") if e[1] == 0] == [endpoint_note(h, C)]   # stock's root at the press
    h.recording(True)
    h.heartbeat(600)
    h.up(24)
    h.heartbeat(400)
    got = where(h, [C, E, G])
    assert C not in got and len(got.get(E, [])) == 1 and len(got.get(G, [])) == 1, got   # E and G recorded, once each
    assert h.moved() == [] and not ghosts(h)
    assert not [k for k in h.sounding if k[:2] == ("synth", 0)]


@pytest.mark.parametrize("mode", [PLAYED, OFF], ids=["played", "off"])
def test_played_and_off_keep_ms(pl19_image, pl19_manifest, pl18_published_image, pl18_published_manifest, mode):
    """Played and Off keep STRUM_GAP ms. Played, recording (setup turns Record on; only then does Played take the press,
    HELD_OWN_ROOT): the heartbeat sends the pad's own note on the first heartbeat after the press, each later note GAP
    ms after the one before. Off: PL18's own log."""
    logs = []
    for image, m in ((pl18_published_image, pl18_published_manifest), (pl19_image, pl19_manifest)):
        h = setup(image, m, mode=mode, speed=1, olds=())
        wait_tick(h, 40)
        h.down(24)
        ons = [(0, e[2]) for e in h.take("synth_on") if e[1] == 0]
        for i in range(1, 400):
            h.heartbeat(1)
            ons += [(i, e[2]) for e in h.take("synth_on") if e[1] == 0]
        h.up(24)
        logs.append(ons)
    if mode == OFF:
        assert logs[0] and logs[1] == logs[0]
    else:
        root = endpoint_note(h, h.pitch(0, 24))
        assert logs[1] == [(1, root), (81, root + 3), (161, root + 7)], logs[1]
        assert [n for _, n in logs[0]] == [n for _, n in logs[1]]                 # PL18 sent the same notes


# ---- recording

@pytest.mark.parametrize("quantise", [True, False], ids=["quantise", "unquantised"])
def test_played_records_a_plain_chord(pl19_image, pl19_manifest, quantise):
    """A slow strummed triad over a step: one step holds the three notes at the first note's step and microstep;
    each length from that start to the note's own release. Older notes on steps 4-11 survive."""
    h = setup(pl19_image, pl19_manifest, mode=PLAYED, quantise=quantise)
    before = snapshot(h)
    strum(h)
    order = send_order(strum_notes(h), C, False)
    assert order == [C, E, G]
    want = expected(h, order, PLAYED, 0, 6)
    got = where(h, order)
    assert got == {n: [w] for n, w in want.items()}, (got, want)
    assert len({(s, mi) for s, mi, _ in want.values()}) == 1
    assert not lost(before, h) and not ghosts(h)
    assert {n for n, _, _ in h.moved()} <= {E, G} and all(t == "main" for _, t, _ in h.moved())


ROLLS = [(q, sp, dn) for q in (True, False) for sp in (1, 2, 3) for dn in (False, True)]


@pytest.mark.parametrize("rate", [3, 5], ids=["1-16", "1-8"])
@pytest.mark.parametrize("quantise, speed, down", ROLLS,
                         ids=[f"{'q' if q else 'noq'}-{('slow', 'medium', 'fast')[sp - 1]}-{'falling' if dn else 'rising'}"
                              for q, sp, dn in ROLLS])
def test_written_records_a_roll(pl19_image, pl19_manifest, quantise, speed, down, rate):
    """Note k at the first's position + k x gap ticks (roll_model: sixths of a step rounded; 1/8 rounds), spilling
    into the next step; each length from the note's own position. Older notes survive; no unit without its note."""
    h = setup(pl19_image, pl19_manifest, speed=speed, down=down, quantise=quantise, rate=rate)
    before = snapshot(h)
    strum(h, at=40 if rate == 3 else 80)
    order = send_order(strum_notes(h), C, down)
    per = rm.STEP_TICKS[rate]
    want = expected(h, order, WRITTEN, rm.WRITTEN_GAP[speed], per)
    got = where(h, order)
    assert got == {n: [w] for n, w in want.items()}, (got, want)
    assert not lost(before, h) and not ghosts(h)
    assert all(t == "main" for _, t, _ in h.moved())
    if rate == 5 and speed == 3:
        assert want[order[1]][:2] == want[order[2]][:2]                   # 1/8 fast: notes 1 and 2 share sixth 1


@pytest.mark.parametrize("how", ["stop", "record off"])
def test_stop_and_record_off_while_held(pl19_image, pl19_manifest, how):
    """A slow strum still held at Stop or Record off: the flush commits every note where stock placed it; nothing
    moved, nothing overwritten."""
    h = setup(pl19_image, pl19_manifest)
    before = snapshot(h)
    wait_tick(h, 40)
    h.down(24)
    h.heartbeat(600)
    h.press(PLAY if how == "stop" else RECORD)
    h.heartbeat(50)
    h.up(24)
    h.heartbeat(400)
    assert len(h.commits) == 3 and {c["site"] for c in h.commits} == {"flush"}, h.commits
    assert h.moved() == []
    for c in h.commits:
        p = W(c["pre"])
        assert [v[0] for v in unit_map(h, p["step"]).values()].count(c["note"]) == 1
    assert not lost(before, h) and not ghosts(h)


def test_two_pads_share_a_pitch(pl19_image, pl19_manifest):
    """q1_scope "two pads sharing G": pad 28 (root G) pressed 100 ms into a held strum on pad 24: the first roll is
    exact; the second strum's notes stay where stock placed them (its first, G, was cut by the hand-over: its word is
    gone); a third G where resound() gave it back (PL18); nothing overwritten."""
    h = setup(pl19_image, pl19_manifest)
    before = snapshot(h)
    wait_tick(h, 40)
    h.down(24)
    h.heartbeat(100)
    h.down(28)
    h.heartbeat(600)
    h.up(24)
    h.heartbeat(30)
    h.up(28)
    h.heartbeat(400)
    moved = h.moved()
    assert [n for n, _, _ in moved] == [E, G] and {t for _, t, _ in moved} == {"main"}, moved
    got = where(h, [C, E, G, 58, 62])
    assert got[C] == [(7, 0, got[C][0][2])] and (7, 4) in [x[:2] for x in got[E]] and (8, 2) in [x[:2] for x in got[G]]
    for c in h.commits:                              # pad 28's notes: never moved
        if c["note"] in (58, 62):
            assert c["pre"] == c["post"]
    assert len(got[G]) == 3                           # the roll's G, pad 28's G, the re-sounded G
    assert not lost(before, h) and not ghosts(h)


@pytest.mark.parametrize("quantise", [True, False], ids=["quantise", "unquantised"])
def test_resound_order(pl19_image, pl19_manifest, quantise):
    """q1_scope "resound order": a fast strum A on pad 24 (Written: G sent 2 ticks in); pad 28 (root G) pressed 10 ms
    after A's G takes G (the router's hand-over ends A's G), let go 20 ms later (B first): resound() gives G back to A;
    A let go 250 ms later. Quantise on: stock merges the presses of G in the step into one pending G (each placement re-arms the one
    entry), and that G moves as A's k = 2 (one G, at A's 2 ticks). Quantise off: the re-sounded G (a placement of the
    UI's re-send, not a strum send) is not moved."""
    h = setup(pl19_image, pl19_manifest, speed=3, quantise=quantise)
    before = snapshot(h)
    wait_tick(h, 40)
    h.down(24)
    hold_until(h, G, 10)
    h.down(28)
    h.heartbeat(20)
    h.up(28)
    h.heartbeat(230)
    h.up(24)
    h.heartbeat(400)
    moved = [n for n, _, _ in h.moved()]
    assert all(t == "main" for _, t, _ in h.moved())
    got = where(h, [C, E, G, 58])
    F = W(h.first_commit(C)["post"])
    if quantise:
        assert got[G] == [(F["step"], F["micro"] + 2, got[G][0][2])], got           # A's k = 2: 2 ticks
        assert G in moved
    else:
        resounded = [c for c in h.commits if c["note"] == G][-1]
        assert resounded["pre"] == resounded["post"]
        assert len(got[G]) >= 2
    assert not lost(before, h) and not ghosts(h)


@pytest.mark.parametrize("other", [25, 26])
def test_freed_slot(pl19_image, pl19_manifest, other):
    """q1_scope "tap, then pad N takes the freed slot before the pass": a strum tapped just after its Eb (its later
    notes wait in the recorder's list: tickets), 2 ms later another pad's press restarts that held slot's latch. Pad 25 (D F Ab,
    no shared pitch): the tap's Eb moves by its own first and k (at the pass), pad 25's strum rolls too. Pad 26 (root
    Eb, the tap's): stock re-arms the shared Eb, its pass commit matches no ticket: nothing of the tap moves."""
    h = setup(pl19_image, pl19_manifest)
    before = snapshot(h)
    wait_tick(h, 40)
    h.down(24)
    hold_until(h, E, 2)
    h.up(24)
    h.heartbeat(2)
    h.down(other)
    h.heartbeat(300)
    h.up(other)
    h.heartbeat(400)
    moved = h.moved()
    if other == 25:
        assert (E, "main", "pass") in moved
        e = [c for c in h.commits if c["note"] == E][0]
        assert (W(e["post"])["step"], W(e["post"])["micro"]) == (7, 4)
        assert len(moved) == 3, moved                                               # E, and pad 25's two later notes
        d = h.pitch(0, 25)
        order = send_order([n for n in strum_notes(h) if n not in (C, E, G)], d, False)
        assert len(order) == 3 and order[0] == d
        assert where(h, order) == {n: [w] for n, w in expected(h, order, WRITTEN, 4, 6).items()}   # pad 25 rolls
    else:
        assert [c for c in moved if c[0] in (C, E)] == [], moved
    assert all(t == "main" for _, t, _ in moved)
    assert not lost(before, h) and not ghosts(h)


def test_stop_at_release(pl19_image, pl19_manifest):
    """Let go and Stop in the same ms (before the heartbeat's note-offs): the flush commits every note at stock's
    place, the heartbeat's note-offs then read the transport stopped: nothing moved. A tap's ticket (its pass not yet
    run) is gone after Stop."""
    h = setup(pl19_image, pl19_manifest)
    wait_tick(h, 40)
    h.down(24)
    h.heartbeat(600)
    h.up(24)
    h.press(PLAY)
    h.heartbeat(5)
    assert h.moved() == [] and len(h.commits) == 3
    tickets = sym(pl19_manifest, "tickets")
    h.uc.mem_write(PATTERN_BASE[0], bytes(32 * STEP))                 # the first take's Eb would play before ours
    h.press(PLAY)
    h.recording(True)
    h.heartbeat(3)
    wait_tick(h, 40)
    h.down(24)
    hold_until(h, E, 2)
    h.up(24)
    h.heartbeat(2)                                    # the note-offs: E waits in the list for the pass (a ticket)
    live = lambda: [h.r32(tickets + 8 * i) for i in range(16) if h.r32(tickets + 8 * i)]   # word 0 != 0: in use
    assert live()
    h.press(PLAY)
    h.heartbeat(1)
    assert not live()
    assert h.moved() == []                            # the flush's pass (UI, at Stop) read no ticket


def test_stale_latch(pl19_image, pl19_manifest):
    """q1_scope "stale latch": a strum on pad 24, let go; then pad 28 (G B D: root G, the strum's G) tapped under one
    gap: that G stays where stock placed it (only its own strum's notes move, and pad 28's later notes were never
    sent)."""
    h = setup(pl19_image, pl19_manifest)
    before = snapshot(h)
    strum(h, after=5)
    h.down(28)
    h.heartbeat(40)
    h.up(28)
    h.heartbeat(400)
    assert [n for n, _, _ in h.moved()] == [E, G]
    gs = [c for c in h.commits if c["note"] == G]
    assert len(gs) == 2 and gs[1]["pre"] == gs[1]["post"]
    got = where(h, [C, E, G])
    assert got[C] == [(7, 0, got[C][0][2])] and got[E][0][:2] == (7, 4) and (8, 2) in [x[:2] for x in got[G]]
    assert not lost(before, h) and not ghosts(h)


def test_quick_repress(pl19_image, pl19_manifest):
    """q1_scope "quick re-press": pad 24 tapped 100 ms, again 20 ms later (within the step): stock re-arms the
    pitches the second press shares; nothing moved but a strum's own notes, nothing overwritten."""
    h = setup(pl19_image, pl19_manifest)
    before = snapshot(h)
    wait_tick(h, 40)
    h.down(24)
    h.heartbeat(100)
    h.up(24)
    h.heartbeat(20)
    h.down(24)
    h.heartbeat(400)
    h.up(24)
    h.heartbeat(400)
    assert all(t == "main" for _, t, _ in h.moved())
    assert all(n in (E, G) for n, _, _ in h.moved())
    assert not lost(before, h) and not ghosts(h)


def test_arp_after_strum(pl19_image, pl19_manifest):
    """q1_scope "arpeggiator on the track after a strum": the strum's own notes move; the arpeggio's notes (not strum
    sends) stay where stock placed them."""
    from test_arp import set_arp
    h = setup(pl19_image, pl19_manifest)
    before = snapshot(h)
    strum(h, after=50)
    n_strum = len(h.commits)
    set_arp(h, pl19_manifest, 0, 1 | 2 << 3)
    h.down(24)
    h.heartbeat(700)
    h.up(24)
    h.heartbeat(400)
    assert [n for n, _, _ in h.moved()] == [E, G]
    assert all(c["pre"] == c["post"] for c in h.commits[n_strum:])
    assert len(h.commits) > n_strum + 2
    assert not lost(before, h) and not ghosts(h)


@pytest.mark.parametrize("quantise", [True, False], ids=["quantise", "unquantised"])
def test_written_wraps(pl19_image, pl19_manifest, quantise):
    """Steps 0-15 (last 15): a slow roll pressed near the end of step 15 spills into step 0, never past the last."""
    h = setup(pl19_image, pl19_manifest, quantise=quantise, last=15, olds=(0, 1, 14, 15))
    before = snapshot(h)
    wait_tick(h, 15 * 6 + 1 if quantise else 15 * 6 + 3)           # quantise on: rounds to step 15
    strum(h, at=None)
    order = send_order(strum_notes(h), C, False)
    want = expected(h, order, WRITTEN, 4, 6, 0, 15)
    assert W(h.first_commit(C)["post"])["step"] == 15
    assert want[G][0] == 0                                          # the spill wrapped to step 0
    assert where(h, order) == {n: [w] for n, w in want.items()}
    assert not lost(before, h) and not ghosts(h)


@pytest.mark.parametrize("mode", [WRITTEN, PLAYED], ids=["written", "played"])
def test_full_step(pl19_image, pl19_manifest, mode):
    """Written: the roll's G lands on step 8, which holds six units: G is left out, C and Eb land. Played (the 9th
    with bass: five notes over a step holding two older ones): the note that finds no free unit stays where stock
    placed it."""
    if mode == WRITTEN:
        h = setup(pl19_image, pl19_manifest, olds=(7,), full=(8,))
    else:
        h = setup(pl19_image, pl19_manifest, mode=PLAYED, shape=3, bass=1, olds=(7,))
    before = snapshot(h)
    strum(h)
    order = send_order(strum_notes(h), C, False)
    want = expected(h, order, mode, 4 if mode == WRITTEN else 0, 6)
    got = where(h, order)
    if mode == WRITTEN:
        assert got == {C: [want[C]], E: [want[E]]}, got
    else:
        F = W(h.first_commit(C)["post"])
        on7 = [n for n in order if got.get(n) == [want[n]]]
        rest = [n for n in order if n not in on7]
        assert len(on7) == 4 and len(rest) == 1, got                               # 2 older + 4 = 6 units
        c = h.first_commit(rest[0])
        assert c["pre"] == c["post"] and got[rest[0]][0][0] == W(c["pre"])["step"] != F["step"]
    assert not lost(before, h) and not ghosts(h)


def test_written_released_early(pl19_image, pl19_manifest):
    """Quantise on, the first note pressed in step 6's second half (rounded to step 7, its start the step's tick),
    let go just after the last note sounds: the last note's start lies after its end, so it gets start = end - 1:
    gate 1, not 96."""
    h = setup(pl19_image, pl19_manifest)
    wait_tick(h, 40)                                                 # tick 40: step 6's second half
    h.down(24)
    for _ in range(400):
        h.heartbeat(1)
        if any(e[1] == 0 and e[2] == endpoint_note(h, G) for e in h.take("synth_on")):
            break
    h.heartbeat(2)
    h.up(24)
    h.heartbeat(400)
    got = where(h, [G])
    assert got == {G: [(8, 2, 1)]}, got


@pytest.mark.parametrize("case", ["written slow", "written medium falling + bass", "played"])
def test_mono_with_each_mode(pl19_image, pl19_manifest, case):
    """Review focus: mono record on, a roll overdubbed on steps holding older notes: each step the roll reached holds
    the roll's notes only (medium falling triad with bass: the root commits after the bass, one step back: spike
    q1_mono_order). Played: the plain chord replaces the step's older notes."""
    mode = PLAYED if case == "played" else WRITTEN
    speed, down, bass = (2, True, 1) if "medium" in case else (1, False, 0)
    h = setup(pl19_image, pl19_manifest, mode=mode, speed=speed, down=down, bass=bass, mono=True)
    strum(h)
    order = send_order(strum_notes(h), C, down)
    want = expected(h, order, mode, rm.WRITTEN_GAP[speed], 6)
    reached = {s for s, _, _ in want.values()}
    for s in reached:
        assert sorted(v[0] for v in unit_map(h, s).values()) == sorted(n for n in order if want[n][0] == s), (s, unit_map(h, s))
    assert where(h, order) == {n: [w] for n, w in want.items()}
    for s in set(range(4, 12)) - reached:
        assert sorted(v[0] for v in unit_map(h, s).values()) == OLD
    assert not ghosts(h)


def test_recfix_still_works(pl19_image, pl19_manifest):
    """A roll held 20 steps on a Written track: each note is written at its roll position with gate 96, tied, and
    continues 16 steps later with what is left (features/recfix, tests/test_recfix.py)."""
    h = setup(pl19_image, pl19_manifest, olds=())
    wait_tick(h, 40)
    h.down(24)
    h.heartbeat(20 * 160 + 80)
    h.up(24)
    h.heartbeat(400)
    got = where(h, [C, E, G])
    assert got[C][0][:2] == (7, 0) and got[E][0][:2] == (7, 4) and got[G][0][:2] == (8, 2), got
    for n, units in got.items():
        (s0, mi0, g0), (s1, mi1, g1) = sorted(units)
        assert g0 == 96 and s1 == s0 + 16 and mi1 == mi0 and 0 < g1 < 96, (n, units)
        a = step_addr(0, 0, s0)
        tied = [h.r8(a + 5 + 4 * u) for u in range(6) if h.r8(a) >> u & 1 and h.r8(a + 4 + 4 * u) == n]
        assert tied == [96 | 0x80]
    assert not ghosts(h)


@pytest.mark.parametrize("down", [False, True], ids=["rising", "falling"])
def test_off_records_as_pl18(pl19_image, pl19_manifest, pl18_published_image, pl18_published_manifest, down):
    """Pattern strum off, strum slow: the recorded notes are PL18's (the published build). Falling too: its notes are
    all the heartbeat's, as an active strum's."""
    runs = []
    for image, m in ((pl18_published_image, pl18_published_manifest), (pl19_image, pl19_manifest)):
        h = setup(image, m, mode=OFF, down=down)
        before = pattern_snapshot(h, 0)
        strum(h)
        runs.append(recorded_notes(h, 0, before))
    assert runs[0] and runs[1] == runs[0]
