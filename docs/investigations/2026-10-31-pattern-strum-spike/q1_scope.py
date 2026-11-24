"""q1_scope (fix rounds 2-3): a recorded note is moved only if the recorder's own data proves it is its own strum's
pending note; every other commit stays where stock placed it. A Python model of the plan's Task 4 rule, on PL18.

- Identity, at the heartbeat's own strum send (chord_send_on called from chord_on_ms's strum site, Main): c = the
  recorder's list counter [rec + 0x9C] before the send; after it (the placement's exit 0x0803F5AA) the send placed the
  note afresh iff its pending word's bits 0-2 == c and list[c].note == note; then id = (note, list[c].start,
  list[c].unit), else none. Start: the converted word keeps it (q1_baseline: place n48 start42 -> word start 42);
  unit: the pass copies it into bits 0-2 (0x0803F748). (start, unit) is unique among pending placements of a pitch:
  equal starts are the same step, where an earlier one's unit is claimed or committed. The rising root: PL18's stock
  sends it on the press (UI); the plan has the heartbeat send it, so the model checks stock's send with the same rule.
- The latch: per held slot i (as prec[i]), restarted when held[i].order differs; written and read only in the
  heartbeat's hooks.
- At the heartbeat's own note-off of note k >= 1 with an id, transport playing and recording:
  converted word with (start, unit) == id -> `inflight` = (note, id, k, first's id), used by the note-off path's
  commit site 0x0803F606 (a mid hook there: r4 rec, r0 note, r1 end) in the same call; still in the list with the
  entry's (start, unit) == id -> after the note-off a ticket {id, end, k, first's id} (the end the list entry keeps).
- Tickets are used only at the tick pass's commit site 0x0803F786 (a mid hook there: r8 rec, r1 note, r0 the list
  word, end = bits 11-21), transport playing and recording (the flush runs the same pass with p0 or p1 = 0); the
  heartbeat clears every ticket whenever the transport is not both playing and recording.
- The move: the first's position from its word when not in the list and its start == the first's id start; the
  target as lib.Route; the unit: the first free in mask | [rec + 0x9D] | other pending words' claims, its mask bit
  set (the reservation), the word rewritten. Then stock's commit, the next instruction.
Every move logs its task and site; any commit at another site whose word would match a ticket is logged too."""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R4, UC_ARM_REG_R8, UC_ARM_REG_SP

from lib import (GAP_TICKS, PATTERN_BASE, PLAY, SET, STEP_TICKS, W, mkword, pl18, put, setup, sym, unit_map,
                 wait_tick)
from notes import step_addr

IMG, M = pl18()
SEND, ON_MS, ARP_MS = sym(M, "chord_send_on"), sym(M, "chord_on_ms"), sym(M, "arp_on_ms")
HELD = sym(M, "held")
SINK_OFF, PLACE, PLACE_END, REC_OFF = 0x0801D942, 0x0803F298, 0x0803F5AA, 0x0803F5B0
OFF_SITE, PASS_SITE = 0x0803F606, 0x0803F786
TRANSPORT = 0x20011034
OLD = [30, 31]


class Scope:
    def __init__(self, h, mode, gap):
        self.h, self.mode, self.gap = h, mode, gap
        self.in_hb = False
        self.send = None             # (pitch, pad) of the heartbeat's strum send in progress
        self.place = None            # (note, c, send) of the placement in progress
        self.strum_site = None       # chord_on_ms's call site of chord_send_on for a strum's own notes
        self.prec = {}               # held slot i -> {"order", "pitch": [...], "ids": [(note, start, unit) | None]}
        self.tickets = {}            # id -> (end, k, first id, tick stamp)
        self.inflight = None         # (note, id, k, first id)
        self.awaiting = None         # (id, k, first id) of a ticket waiting for the list entry's end
        self.moves, self.diag = [], []
        u = h.uc
        u.hook_add(UC_HOOK_CODE, self.on_ms, begin=ON_MS, end=ON_MS)
        u.hook_add(UC_HOOK_CODE, lambda *a: setattr(self, "in_hb", False), begin=ARP_MS, end=ARP_MS)
        u.hook_add(UC_HOOK_CODE, self.on_send, begin=SEND, end=SEND)
        u.hook_add(UC_HOOK_CODE, self.on_place, begin=PLACE, end=PLACE)
        u.hook_add(UC_HOOK_CODE, self.on_place_end, begin=PLACE_END, end=PLACE_END)
        u.hook_add(UC_HOOK_CODE, self.on_sink_off, begin=SINK_OFF, end=SINK_OFF)
        u.hook_add(UC_HOOK_CODE, self.on_rec_off, begin=REC_OFF, end=REC_OFF)
        u.hook_add(UC_HOOK_CODE, self.on_off_site, begin=OFF_SITE, end=OFF_SITE)
        u.hook_add(UC_HOOK_CODE, self.on_pass_site, begin=PASS_SITE, end=PASS_SITE)
        h.on_commit = self.on_any_commit
        orig = h.heartbeat

        def hb(n=1):
            for _ in range(n):
                orig(1)
                self.in_hb = False
                self.inflight = None                 # the heartbeat clears it after its note_sink_off
        h.heartbeat = hb

    # ---- recorder and transport reads
    def transport_on(self):
        h = self.h
        sel = h.r32(TRANSPORT + 4)
        return all(h.r32(h.r32(TRANSPORT + 0xC + 4 * (sel >> i & 1)) + 4 * i) for i in (0, 1))

    def word_id(self, note):
        """('list' | 'word', (note, start, unit)) of the note's pending word, or (None, None)."""
        h = self.h
        w = h.pending(note)
        if w & 7 == 7:
            return None, None
        if h.in_list(note):
            e = h.list_entry(w & 7)
            return "list", (note, e["start"], e["unit"] & 7)
        return "word", (note, W(w)["start"], w & 7)

    def slot(self, pad=None, root=None):
        for i in range(6):
            b = bytes(self.h.uc.mem_read(HELD + 14 * i, 14))
            if b[0] and b[1] == self.h.t and b[9] & 1 and (b[2] == pad or (root is not None and b[12] == root)):
                return i, b[13], b[12], b[9]
        return None

    def latch(self, i, order):
        lt = self.prec.get(i)
        if not lt or lt["order"] != order:
            lt = self.prec[i] = {"order": order, "pitch": [], "ids": []}   # restart (n = 0, then order)
        return lt

    # ---- the heartbeat
    def on_ms(self, u, a, s, d):
        self.in_hb = True
        if not self.transport_on():
            self.tickets.clear()                     # expiry: no ticket outlives a take ...
        for i, t in list(self.tickets.items()):
            if self.h.ticks - t[3] > 48:             # ... nor two steps at the slowest rate (its pass is due in one)
                del self.tickets[i]

    def on_send(self, u, a, s, d):
        if not self.in_hb:
            return
        lr = u.reg_read(UC_ARM_REG_LR)
        if self.strum_site is None:
            self.strum_site = lr
        if lr != self.strum_site:
            return                                   # resound()'s re-sends: not strum sends
        self.send = (u.reg_read(UC_ARM_REG_R0 + 2), self.h.r32(u.reg_read(UC_ARM_REG_SP)) & 0xFF)

    def on_place(self, u, a, s, d):
        if u.reg_read(UC_ARM_REG_R0) == self.h.rec():
            p = self.h.places[-1]
            self.place = (p["note"], p["idx"], self.send if self.in_hb else None)
            self.send = None

    def on_place_end(self, u, a, s, d):
        if not self.place:
            return
        note, c, send = self.place
        self.place = None
        h = self.h
        e = h.list_entry(c)
        fresh = h.pending(note) & 7 == c and e["note"] == note
        ident = (note, e["start"], e["unit"] & 7) if fresh else None
        if send is None:                             # stock's own send in the UI task: a rising root (model only)
            sl = self.slot(root=note)
            if sl and not sl[3] & 0x20:
                lt = self.latch(sl[0], sl[1])
                if not lt["pitch"]:
                    lt["pitch"].append(note)
                    lt["ids"].append(ident)
            return
        pitch, pad = send
        sl = self.slot(pad=pad)
        if not sl:
            return
        lt = self.latch(sl[0], sl[1])
        lt["pitch"].append(pitch)
        lt["ids"].append(ident)

    def on_sink_off(self, u, a, s, d):
        if not self.in_hb or u.reg_read(UC_ARM_REG_LR) & ~1 < 0x0805D000:
            return                                   # only chord_on_ms's own note-offs
        pitch, pad = u.reg_read(UC_ARM_REG_R0 + 1), u.reg_read(UC_ARM_REG_R0 + 2) & 0xFF
        sl = self.slot(pad=pad)
        if not sl or sl[0] not in self.prec or self.prec[sl[0]]["order"] != sl[1]:
            return
        lt = self.prec[sl[0]]
        if pitch not in lt["pitch"]:
            return
        k = lt["pitch"].index(pitch)
        ident = lt["ids"][k]
        if k == 0 or ident is None or lt["ids"][0] is None or not self.transport_on():
            return
        where, now = self.word_id(ident[0])
        if now != ident:
            return
        if where == "word":
            self.inflight = (ident[0], ident, k, lt["ids"][0])
        else:
            self.awaiting = (ident, k, lt["ids"][0])

    def on_rec_off(self, u, a, s, d):
        if self.awaiting and u.reg_read(UC_ARM_REG_R0 + 2) == self.awaiting[0][0]:
            ident, k, first = self.awaiting
            end = u.reg_read(UC_ARM_REG_R0 + 1) & 0x7FF
            self.tickets[ident] = (max(end, ident[1]), k, first, self.h.ticks)   # end as the entry keeps it; stamp
        self.awaiting = None

    # ---- the two commit sites (mid hooks in the plan)
    def on_off_site(self, u, a, s, d):
        if u.reg_read(UC_ARM_REG_R4) != self.h.rec():
            return
        note, end = u.reg_read(UC_ARM_REG_R0), u.reg_read(UC_ARM_REG_R0 + 1) & 0x7FF
        f = self.inflight
        if not f or f[0] != note:
            return
        self.inflight = None
        if self.transport_on() and self.word_id(note) == ("word", f[1]):
            self.move(f[2], f[3], note, end, "note-off site")

    def on_pass_site(self, u, a, s, d):
        if u.reg_read(UC_ARM_REG_R8) != self.h.rec():
            return
        note, end = u.reg_read(UC_ARM_REG_R0 + 1), u.reg_read(UC_ARM_REG_R0) >> 11 & 0x7FF
        if not self.transport_on():
            if self.tickets:
                self.diag.append((self.h.task, "flush's pass", note, "transport off: no ticket read"))
            return
        where, ident = self.word_id(note)
        t = self.tickets.get(ident)
        if t and t[0] == end:
            del self.tickets[ident]
            self.move(t[1], t[2], note, end, "pass site")

    def on_any_commit(self, h, note, end):
        where, ident = self.word_id(note)
        if ident in self.tickets and h.site != 0x0803F78C:
            self.diag.append((h.task, h.site, note, "a non-pass commit matches a ticket"))

    def move(self, k, first, note, end, how):
        h = self.h
        f = h.pending(first[0])
        F = W(f)
        if h.in_list(first[0]) or F["start"] != first[1]:
            self.moves.append((h.task, how, note, "first's word gone: pass"))
            return
        w = h.pending(note)
        pat = PATTERN_BASE[h.t] + 0xCA8 * F["pattern"]
        rate, last, frst = h.r8(pat + SET + 2), h.r8(pat + SET), h.r8(pat + SET + 1)
        per = h.r32(STEP_TICKS + 4 * rate)
        if self.mode == "played":
            step, micro, start = F["step"], F["micro"], F["start"]
        else:
            six = F["micro"] + (k * self.gap * 6 + per // 2) // per
            step, micro = F["step"] + six // 6, six % 6
            while step > last:
                step -= last - frst + 1
            start = (F["start"] + k * self.gap) & 0x7FF
        if ((end - start) & 0x7FF) >= 0x400:
            start = (end - 1) & 0x7FF
        a = step_addr(h.t, F["pattern"], step)
        taken = h.r8(a) | h.r8(h.rec() + 0x9D)
        for n in range(1, 140):
            x = h.pending(n)
            if n != note and x & 7 != 7 and (x & 0x7F8) == (F["pattern"] << 8 | step << 3):
                taken |= 1 << (x & 7)
        unit = next((u for u in range(6) if not taken >> u & 1), 7)
        if unit < 7:
            h.uc.mem_write(a, bytes([h.r8(a) | 1 << unit]))         # the reservation
        h.set_pending(note, mkword(unit, step, F["pattern"], W(w)["vel"], start, micro))
        self.moves.append((h.task, how, note, k, step, micro))


def case(label, mode="written", speed=1, quantise=True, down=False, script=None, olds=range(4, 12), other=None):
    h = setup(IMG, M, speed=speed, quantise=quantise, down=down)
    for s in olds:
        put(h, s, OLD)
    before = {s: unit_map(h, s) for s in range(32)}
    sc = Scope(h, mode, GAP_TICKS[speed] if mode == "written" else 0)
    sc.other = other
    wait_tick(h, 40)
    h.strum.clear()
    extra = script(h, sc)
    h.heartbeat(400)
    lost = [f"step {s + 1} unit {u} {v[0]}" for s in range(32) for u, v in before[s].items()
            if unit_map(h, s).get(u) != v]
    ghosts = [f"step {s + 1} unit {u}" for s in range(32) for u in range(6)        # a mask bit with no note written
              if h.r8(step_addr(0, 0, s)) >> u & 1 and h.r8(step_addr(0, 0, s) + 4 + 4 * u) == 0]
    got = {s + 1: [(v[0], v[2]) for v in unit_map(h, s).values() if v[0] not in OLD] for s in range(32)}
    got = {s: n for s, n in got.items() if n}
    print(f"{label}: moves {sc.moves}")
    print(f"        steps (1-based: (note, microstep), older notes hidden) {got}")
    print(f"        older units lost: {lost or 'none'}; empty units with a mask bit: {ghosts or 'none'};"
          f" diag {sc.diag or 'none'}; tickets left {len(sc.tickets)}" + (f"; {extra}" if extra else ""))
    return h, sc


def held(ms):
    def f(h, sc):
        h.down(24); h.heartbeat(ms); h.up(24)
    return f


def stale(h, sc):
    """A strum on pad 24 (C E G), let go; then pad 28 (G chord: G B D) tapped 40 ms."""
    h.down(24); h.heartbeat(400); h.up(24); h.heartbeat(5)
    h.down(28); h.heartbeat(40); h.up(28)


def freed_slot(h, sc):
    """A strum tapped 100 ms (its notes wait for the pass); 2 ms later pad `other` takes the freed held slot and the
    heartbeat restarts that slot's latch before the pass: the ticket carries its own k and first. Pad 25 (D F Ab)
    shares no pitch with C Eb G; pad 26's root is the tap's Eb (stock re-arms that entry: one note, PASS)."""
    other = sc.other
    h.down(24); h.heartbeat(100); h.up(24); h.heartbeat(2)
    h.down(other); h.heartbeat(300); h.up(other)
    return f"slot 0's latch now {sc.prec.get(0, {}).get('pitch')}"


def two_pads(h, sc):
    h.down(24); h.heartbeat(100); h.down(28); h.heartbeat(600); h.up(24); h.heartbeat(30); h.up(28)


def resound_order(h, sc):
    """Fast strum A on pad 24 (G sent at ~40 ms); pad 28 (root G) pressed at 50 ms takes G (A's G committed at the
    hand-over), let go at 70 ms (B first): resound() gives G back to A in the same step; A let go at 300 ms."""
    h.down(24); h.heartbeat(50); h.down(28); h.heartbeat(20); h.up(28); h.heartbeat(230); h.up(24)
    return f"G placements {[(p['ms'], p['task'], p['start'], p['idx']) for p in h.places if p['note'] == 55]}"


def repress(h, sc):
    h.down(24); h.heartbeat(100); h.up(24); h.heartbeat(20); h.down(24); h.heartbeat(400); h.up(24)


def stop_held(h, sc):
    h.down(24); h.heartbeat(600); h.press(PLAY); h.heartbeat(50); h.up(24)


def stop_at_release(h, sc):
    """Let go and Stop in the same ms, before the heartbeat's note-offs: the flush commits every note; the heartbeat's
    note-offs then read the transport stopped."""
    h.down(24); h.heartbeat(600); h.up(24); h.press(PLAY); h.heartbeat(5)


def expiry(h, sc):
    """A tap (its ticket waits for the pass), Stop 5 ms later (before the pass), Play and Record again, the same tap:
    the first take's tickets are gone at the first heartbeat after Stop."""
    h.down(24); h.heartbeat(100); h.up(24); h.heartbeat(5)
    waiting = list(sc.tickets)
    h.press(PLAY); h.heartbeat(1)
    gone = len(sc.tickets)
    h.press(PLAY); h.recording(True); h.heartbeat(3)
    wait_tick(h, h.ticks + 40)
    h.down(24); h.heartbeat(100); h.up(24)
    return f"tickets before Stop {waiting}, after its first heartbeat {gone}"


def arp_after(h, sc):
    from test_arp import set_arp
    h.down(24); h.heartbeat(400); h.up(24); h.heartbeat(50)
    set_arp(h, M, 0, 1 | 2 << 3)
    h.down(24); h.heartbeat(700); h.up(24)


def main():
    case("held, rising", script=held(600))
    case("held, falling", down=True, script=held(600))
    case("held, rising, quantise off", quantise=False, script=held(600))
    case("played, held, rising", mode="played", script=held(600))
    case("tapped 100 ms (the pass commits)", script=held(100))
    case("stale latch: strum, then a G chord tapped 40 ms", script=stale)
    for other in (25, 26):
        case(f"tap, then pad {other} takes the freed slot before the pass", script=freed_slot, other=other)
    case("two pads sharing G (pad 28 pressed 100 ms in)", script=two_pads)
    case("resound order: B takes G and is let go first, A gets G back", speed=3, script=resound_order)
    case("resound order, quantise off", speed=3, quantise=False, script=resound_order)
    case("quick re-press of pad 24 (tap 100 ms, again 20 ms later)", script=repress)
    case("Stop while held", script=stop_held)
    case("let go and Stop in the same ms", script=stop_at_release)
    case("ticket expiry across takes", script=expiry)
    case("arpeggiator on the track after a strum", script=arp_after)


if __name__ == "__main__":
    main()
