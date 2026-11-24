"""Shared helpers for the PL20 builder check, part B (playback and counting; throwaway, stock image only).
Run from slim/ with PYTHONPATH=.:tests:../tools:docs/investigations/2026-11-01-trig-conditions-spike.

The sequencer runs through the real route: Play (button 17), then the Main task's 1 ms service (heartbeat) drives the
clock and seq_tick. Code hooks only log (registers / memory) unless a script asks to force a branch."""
from __future__ import annotations

import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6,
                               UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R11, UC_ARM_REG_SP,
                               UC_ARM_REG_LR, UC_ARM_REG_R12)

from notes import (NoteHarness, PARAM_COMMIT, PARAM_GET, PARAM_WPTR, PATTERN, PATTERN_BASE, PLAY_STORE, STEP,
                   TEMPO_STORE, param, set_tempo)

ROOT = Path(__file__).resolve().parents[4]
STOCK = (ROOT / "stock/circuittracks-firmware-4486-STOCK.bin").read_bytes()

E = 0x20038EC0                 # sequencer engine
SEQ_TICK, SEQ_START = 0x0802C418, 0x0802C008
CD42 = 0x0802CD42              # track advance: "pattern ends or scene change" test
CE12 = 0x0802CE12              # track advance: the next pattern / step chosen, about to be stored
TRACK_ADV = 0x0802CB3C
A684, A6B8, A714 = 0x0804A684, 0x0804A6B8, 0x0804A714
NOTE_PLAYERS = [0x20040200 + 0x184 * t for t in range(4)]
DRUM_PLAYERS = [0x20040810 + 0x90 * d for d in range(4)]
PLAYERS = NOTE_PLAYERS + DRUM_PLAYERS          # index = engine track 0-7
UNITS_START, PLAY_STEP = 0x08040D4C, 0x08040E5A
D_SLOT1, D_SLOT2, D_SLOT4 = 0x080411AC, 0x08041252, 0x080411CA
HIT_TEST = 0x0804AA08
N_PROB, D_PROB_HIT, D_PROB_S4 = 0x08040D8A, 0x0804AA18, 0x080411F6
DRUM_PAT = 0x6A8
DREC = 0x2003C184              # [DREC + 4 d]: drum d's recorder; [+ 0x48] its patterns
PLAY = 17


def r32(h, a):
    return h.r32(a)


def store_ptr(h, st, i):
    """Stock's parameter getter 0x0803542C in Python (safe inside a code hook): [st + 0xC + 4 b] + 4 i, b = bit i
    of [st + 4] (which of the two buffers is current)."""
    b = h.r32(st + 4) >> i & 1
    return h.r32(st + 0xC + 4 * b) + 4 * i


def store_bytes(h, st, i, n=4):
    return bytes(h.uc.mem_read(store_ptr(h, st, i), n))


def store_set(h, st, i, data: bytes):
    """Write parameter i through the store's write pointer and commit (as stock's own writers)."""
    h.call(PARAM_WPTR, st, i)
    h.uc.mem_write(h.uc.reg_read(UC_ARM_REG_R0), data)
    h.call(PARAM_COMMIT, st)


class B(NoteHarness):
    """Stock image; logs the tick, the track advance, the players' tick-0 and microstep calls."""

    def __init__(self, image=STOCK):
        super().__init__(image)
        self.tick = 0
        self.adv = []        # (tick, track, old pattern, old step, look-ahead fp, ends r4, scene [sp+44], hand [sp+18])
        self.chosen = []     # (tick, track, new pattern, new step, fp)
        self.t0 = []         # (tick, track, pattern, step)                     at 0x0804A6B8
        self.pass684 = []    # (tick, track, pattern, step, tick-in-step)       at 0x0804A684
        self.pass714 = []    # (tick, track, pattern, step, tick-in-step)       at 0x0804A714
        self.micro = []      # (tick, track, kind, pattern, step, micro)        slot 1 / slot 2 / slot 4
        self.order = []      # (tick, tag, track) every hooked event in order
        uc = self.uc
        self._hooks = []

        def at(addr, fn):
            self._hooks.append(uc.hook_add(UC_HOOK_CODE, fn, begin=addr, end=addr))

        def tk(u, a, s, d):
            self.tick += 1
            self.order.append((self.tick, "tick", None))
        at(SEQ_TICK, tk)

        def st(u, a, s, d):
            self.order.append((self.tick, "seq_start", None))
        at(SEQ_START, st)

        def cd42(u, a, s, d):
            sp = u.reg_read(UC_ARM_REG_SP)
            track = self.r32(sp + 0xC)
            assert track == (u.reg_read(UC_ARM_REG_R7) - E - 0) // 4 == self.r8(sp), "track registers disagree"
            rec = (self.tick, track, u.reg_read(UC_ARM_REG_R9) & 0xFF, u.reg_read(UC_ARM_REG_R6) & 0xFF,
                   u.reg_read(UC_ARM_REG_R11), u.reg_read(UC_ARM_REG_R4) & 0xFF, self.r8(sp + 0x44), self.r8(sp + 0x18))
            self.adv.append(rec)
            self.order.append((self.tick, "cd42", track))
        at(CD42, cd42)

        def ce12(u, a, s, d):
            sp = u.reg_read(UC_ARM_REG_SP)
            self.chosen.append((self.tick, self.r32(sp + 0xC), self.r8(sp + 1), u.reg_read(UC_ARM_REG_R5) & 0xFF,
                                u.reg_read(UC_ARM_REG_R11)))
        at(CE12, ce12)

        def p_of(r):
            return PLAYERS.index(r) if r in PLAYERS else None


        def h684(u, a, s, d):
            p = u.reg_read(UC_ARM_REG_R0)
            t = p_of(p)
            if t is None:
                return
            st_ = self.r32(p + 8)
            self.pass684.append((self.tick, t, *self.pstate(st_)))
            self.order.append((self.tick, "a684", t))
        at(A684, h684)

        def h714(u, a, s, d):
            p = u.reg_read(UC_ARM_REG_R0)
            t = p_of(p)
            if t is None:
                return
            self.pass714.append((self.tick, t, *self.pstate(self.r32(p + 8))))
            self.order.append((self.tick, "a714", t))
        at(A714, h714)

        def h6b8(u, a, s, d):
            p = u.reg_read(UC_ARM_REG_R7)
            t = p_of(p)
            self.t0.append((self.tick, t, u.reg_read(UC_ARM_REG_R9) & 0xFF, u.reg_read(UC_ARM_REG_R8) & 0xFF))
            self.order.append((self.tick, "a6b8", t))
        at(A6B8, h6b8)

        def slot(kind):
            def f(u, a, s, d):
                r = [u.reg_read(UC_ARM_REG_R0 + i) for i in range(4)]
                t = p_of(r[0])
                self.micro.append((self.tick, t, kind, r[1], r[2], r[3]))
                self.order.append((self.tick, kind, t))
            return f
        at(UNITS_START, slot("n1"))
        at(PLAY_STEP, slot("n2"))
        at(D_SLOT1, slot("d1"))
        at(D_SLOT2, slot("d2"))
        at(D_SLOT4, slot("d4"))

    # state ----------------------------------------------------------------------------------------------------
    def pstate(self, st):
        """(pattern, step, tick-in-step) of a playing store."""
        return (store_bytes(self, st, 0, 1)[0], store_bytes(self, st, 1, 1)[0],
                struct.unpack("<I", store_bytes(self, st, 2))[0])

    def playing(self, t):
        return self.pstate(self.r32(E + 0x30 + 4 * t))

    def lookahead(self, t):
        return self.pstate(self.r32(E + 0x70 + 4 * t))

    def chain(self, t):
        b = store_bytes(self, self.r32(E + 0x9C), t, 2)
        return b[0], b[1]

    def set_chain_raw(self, t, first, last):
        st = self.r32(E + 0x9C)
        v = store_bytes(self, st, t)
        store_set(self, st, t, bytes([first, last]) + v[2:])

    def chain_flag(self, t):
        return store_bytes(self, self.r32(E + 0x9C), 8 + t, 1)[0]

    def scene(self):
        return store_bytes(self, self.r32(E + 0x2C), 0, 1)[0]

    def scene_chain(self):
        b0 = store_bytes(self, self.r32(E + 0xA0), 0, 2)
        b1 = store_bytes(self, self.r32(E + 0xA0), 1, 1)[0]
        return b0[0], b0[1], b1

    def queued(self, t):
        return bytes(self.uc.mem_read(E + 0xC4 + 4 * t, 4))

    # patterns -------------------------------------------------------------------------------------------------
    def drum_base(self, d):
        return self.r32(self.r32(DREC + 4 * d) + 0x48)

    def settings_addr(self, t, p):
        if t < 4:
            return PATTERN_BASE[t] + p * PATTERN + 0x380
        return self.drum_base(t - 4) + p * DRUM_PAT + 0x80

    def settings(self, t, p):
        return tuple(self.uc.mem_read(self.settings_addr(t, p), 4))   # last, first, rate, direction

    def set_settings(self, t, p, last=None, first=None, rate=None, direction=None):
        a = self.settings_addr(t, p)
        cur = list(self.uc.mem_read(a, 4))
        for i, v in enumerate((last, first, rate, direction)):
            if v is not None:
                cur[i] = v
        self.uc.mem_write(a, bytes(cur))

    def note_fill_all(self, t, p, steps=32):
        """One note (60) on every step of note pattern p of track t, probability 7."""
        for s in range(steps):
            a = PATTERN_BASE[t] + p * PATTERN + s * STEP
            self.uc.mem_write(a, bytes([1, 7, 0, 0, 60, 6, 0, 100]) + bytes(20))

    def drum_fill_all(self, d, p):
        b = self.drum_base(d) + p * DRUM_PAT
        self.uc.mem_write(b, bytes([100] * 32) + bytes([7] * 32) + bytes([0xFF] * 32) + bytes([1] * 32))

    # transport ------------------------------------------------------------------------------------------------
    def transport(self):
        return tuple(param(self, PLAY_STORE, i) for i in range(3))

    def play(self):
        self.press(PLAY)

    def run_ticks(self, n, cap=200_000):
        """Heartbeats until n more sequencer ticks have run."""
        goal = self.tick + n
        for _ in range(cap):
            if self.tick >= goal:
                return
            self.heartbeat(1)
        raise AssertionError("ticks did not advance")

    def clear_logs(self):
        for l in (self.adv, self.chosen, self.t0, self.pass684, self.pass714, self.micro, self.order):
            l.clear()


def passes_from_adv(adv, track, fp=0):
    """The track advance entries at 0x0802CD42 for a track where the pattern ends (r4) or a scene changes."""
    return [a for a in adv if a[1] == track and a[4] == fp and (a[5] or a[6])]


def steps_played(t0, track):
    return [(tk, p, s) for tk, t, p, s in t0 if t == track]


# ---- scenario runner (Q1) ------------------------------------------------------------------------------------
STEP_TICKS = [2, 3, 4, 6, 8, 12, 16, 24]


def configure(h, cfg):
    """cfg: {track: dict(chain=(first, last), pats={p: (last, first, rate, dir)}, mute=bool)}. Raw pattern bytes
    (stock's getters read them at every pattern change), the playing pattern's settings store [E + 0x50 + 4 t]
    and the chain store through write + commit, the mute store [player + 0x28] p0 through write + commit."""
    for t, c in cfg.items():
        for p, (last, first, rate, d) in c.get("pats", {}).items():
            h.set_settings(t, p, last, first, rate, d)
        if "chain" in c:
            h.set_chain_raw(t, *c["chain"])
        if c.get("mute"):
            st = h.r32(PLAYERS[t] + 0x28)
            store_set(h, st, 0, bytes([1]) + store_bytes(h, st, 0)[1:])
        p0 = h.playing(t)[0]
        last, first, rate, d = h.settings(t, p0)
        st = h.r32(E + 0x50 + 4 * t)
        store_set(h, st, 0, bytes([last, first]) + store_bytes(h, st, 0)[2:])
        store_set(h, st, 1, bytes([rate]) + store_bytes(h, st, 1)[1:])
        store_set(h, st, 2, bytes([d]) + store_bytes(h, st, 2)[1:])


def expected_pass(last, first, d):
    n = (last - first) % 32 + 1
    fwd = [(first + i) % 32 for i in range(n)]
    if d == 0:
        return fwd
    if d == 1:
        return fwd[::-1]
    return None   # ping-pong / random: checked separately


def split_passes(h, t):
    """Track t's tick-0 steps split at its pass events (0x0802CD42, fp = 0, pattern end or scene), using the
    global event order. Returns (segments, problems): each segment = (pattern, [steps]); problems lists any
    pass event not followed, before the next tick-0 of the track, by nothing else of that track."""
    segs, cur, problems, pending = [], [], [], None
    adv_iter = iter([a for a in h.adv if a[1] == t])
    t0_iter = iter([x for x in h.t0 if x[1] == t])
    for tick, tag, tr in h.order:
        if tr != t:
            continue
        if tag == "cd42":
            a = next(adv_iter)
            if a[4] == 0 and (a[5] or a[6]):
                if pending is not None:
                    problems.append(("two pass events without a step between", pending, a))
                pending = a
                segs.append(cur)
                cur = []
        elif tag == "a6b8":
            x = next(t0_iter)
            cur.append((x[2], x[3]))
            pending = None
    segs.append(cur)
    return segs, problems


# ---- write watches (Q2 / Q3) ---------------------------------------------------------------------------------
from unicorn import UC_HOOK_MEM_WRITE


def store_bufs(h, st):
    return h.r32(st + 0xC), h.r32(st + 0x10)


def watch_writes(h, regions, log):
    """regions: {name: (start, length)}; log gets (tick, name, offset, size, value, pc)."""
    for name, (a, n) in regions.items():
        def w(u, acc, addr, size, val, d, name=name, a=a):
            log.append((h.tick, name, addr - a, size, val, u.reg_read(UC_ARM_REG_PC)))
        h.uc.hook_add(UC_HOOK_MEM_WRITE, w, begin=a, end=a + n - 1)


def engine_regions(h):
    r = {}
    for nm, off, n in (("chain", 0x9C, 0x40), ("scenechain", 0xA0, 0x8), ("scene", 0x2C, 0x4)):
        b0, b1 = store_bufs(h, h.r32(E + off))
        r[nm + ".b0"] = (b0, n)
        r[nm + ".b1"] = (b1, n)
        r[nm + ".hdr"] = (h.r32(E + off) + 4, 8)
    r["queued"] = (E + 0xC4, 0x20)
    r["E+0x94"] = (E + 0x94, 8)
    r["E+0xFC"] = (E + 0xFC, 1)
    return r


def snapshot(h):
    return dict(scene=h.scene(), scene_chain=h.scene_chain(),
                chains=[h.chain(t) for t in range(8)], flags=[h.chain_flag(t) for t in range(8)],
                queued=[tuple(h.queued(t)[:2]) for t in range(8)], playing=[h.playing(t)[:2] for t in range(8)])
