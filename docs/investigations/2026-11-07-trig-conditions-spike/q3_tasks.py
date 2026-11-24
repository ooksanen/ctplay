"""Q3: the tasks that reach the player tick pass 0x0804A6C0 (player_tick) and the track advance 0x0802CD42
(track_advance), and what seq_place 0x0802C240 gets from its three callers. Every emulated call carries a context:
"ui" (a controller button / pad call), "ui:led" (the LED frame, where CTPlay's count-in presses Play), "main" (the
1 ms service), "direct:<fn>" (the project load's read-done handler called as tests/test_saved.py does).

Scenarios (stock unless said; 240 BPM; 8-step loops unless said): Play from stop; Stop and Shift + Play (continue);
a Patterns tap and a hand-set chain while playing; Shift + a Patterns pad while playing (at once); a pick while
stopped; a scene recalled by hand while playing; a scene chain advancing by itself; a load stopped and playing;
CTPlay's count-in start (PL19 image, built from the current sources). Then, from the same runs: at a scene takeover each
track's 0x0802CD42 with fp == 0 and the scene flag set, counted per track at the takeover tick; at a hand pick the
picked track's event with hand ([sp + 0x18]) and scene ([sp + 0x44])."""
from collections import Counter
from pathlib import Path

from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_R11, UC_ARM_REG_R5, UC_ARM_REG_R7

from b_lib import *
from b_lib import B as BB
from b_3_scene import save_scene
from harness import BTN_PRESS, BTN_RELEASE, MS_SERVICE, PAD_PRESS, PAD_RELEASE

CTRL = {BTN_PRESS: "ui", BTN_RELEASE: "ui", PAD_PRESS: "ui", PAD_RELEASE: "ui", MS_SERVICE: "main"}
READ_DONE, SESSION = 0x0802FD5C, 0x2003D71C
PL19 = Path(__file__).resolve().parents[3] / "build/PL19/circuittracks-4486-PL19.bin"


class T(BB):
    def __init__(self, image=STOCK):
        self.ctx, self.depth = "setup", 0
        super().__init__(image)
        self.hits = []          # (ctx, what, tick, details)
        uc = self.uc

        def a6c0(u, a, s, d):
            p = u.reg_read(UC_ARM_REG_R7)
            t = PLAYERS.index(p) if p in PLAYERS else None
            self.hits.append((self.ctx, "player_tick", self.tick, (t, u.reg_read(UC_ARM_REG_R5))))
        uc.hook_add(UC_HOOK_CODE, a6c0, begin=0x0804A6C0, end=0x0804A6C0)

        def cd42(u, a, s, d):
            sp = u.reg_read(UC_ARM_REG_SP)
            self.hits.append((self.ctx, "track_advance", self.tick,
                              dict(track=self.r32(sp + 0xC), fp=u.reg_read(UC_ARM_REG_R11), end=u.reg_read(UC_ARM_REG_R4) & 0xFF,
                                   scene=self.r8(sp + 0x44), hand=self.r8(sp + 0x18), pattern=u.reg_read(UC_ARM_REG_R9) & 0xFF)))
        uc.hook_add(UC_HOOK_CODE, cd42, begin=0x0802CD42, end=0x0802CD42)

        def place(u, a, s, d):
            self.hits.append((self.ctx, "seq_place", self.tick,
                              (u.reg_read(UC_ARM_REG_R1), f"{u.reg_read(UC_ARM_REG_LR) & ~1:#010x}")))
        uc.hook_add(UC_HOOK_CODE, place, begin=0x0802C240, end=0x0802C240)

    def call(self, fn, *args, **kw):
        outer = self.ctx
        if self.depth == 0:
            self.ctx = CTRL.get(fn, f"direct:{fn:#010x}")
        self.depth += 1
        try:
            return super().call(fn, *args, **kw)
        finally:
            self.depth -= 1
            if self.depth == 0:
                self.ctx = outer

    def led_frame(self):
        outer = self.ctx
        self.ctx = "ui:led"
        try:
            return self.leds()
        finally:
            self.ctx = outer


def fresh(lengths=None, image=STOCK):
    h = T(image)
    h.leds()
    set_tempo(h, bpm=240)
    lengths = lengths or [8] * 8
    configure(h, {t: dict(chain=(0, 0), pats={p: (lengths[t] - 1, 0, 3, 0) for p in range(8)}) for t in range(8)})
    return h


def ctx_table(h, label):
    c = Counter((x[0], x[1]) for x in h.hits)
    by = {}
    for (ctx, what), n in c.items():
        by.setdefault(what, []).append(f"{ctx} x{n}")
    print(f"[{label}] " + "; ".join(f"{w}: {', '.join(sorted(v))}" for w, v in sorted(by.items())))
    places = sorted({(x[0], x[3][1]) for x in h.hits if x[1] == "seq_place"})
    if places:
        tracks = sorted({x[3][0] for x in h.hits if x[1] == "seq_place"})
        print(f"    seq_place callers (ctx, lr): {places}; r1 values {tracks}")
    return {(ctx, what) for ctx, what in c}


ALL = set()


def scen(label, fn, lengths=None, image=STOCK):
    h = fresh(lengths, image)
    h.hits.clear()               # the setup's own store commits (configure) are not part of the scenario
    fn(h)
    ALL.update(ctx_table(h, label))
    return h


def play_from_stop(h):
    h.play()
    h.run_ticks(40)


def shift_play(h):
    h.play()
    h.run_ticks(20)
    h.play()                     # Stop
    h.heartbeat(20)
    h.hits.clear()
    h.press(17, shift=True)      # continue
    h.heartbeat(60)


def pattern_tap(h):
    h.press(13)
    h.play()
    h.run_ticks(10)
    h.hits.clear()
    h.pad(16)                    # Synth 1 pattern 2
    h.down(4)                    # Drum 1: hold pattern 1, press pattern 3: a chain 1..3
    h.down(20)
    h.up(20)
    h.up(4)
    h.tap_tick = h.tick
    h.run_ticks(60)


def shift_pattern(h):
    h.press(13)
    h.play()
    h.run_ticks(10)
    h.hits.clear()
    h.shift(True)
    h.pad(16)
    h.shift(False)
    h.run_ticks(40)


def stopped_pick(h):
    h.press(13)
    h.pad(16)
    h.heartbeat(20)


def scene_recall(h):
    save_scene(h, 1, [(1, 1)] * 4 + [(2, 3)] * 4)
    save_scene(h, 0, [(0, 0)] * 8)
    h.press(14)
    h.play()
    h.run_ticks(10)
    h.hits.clear()
    h.pad(17)                    # scene 1
    h.run_ticks(160)


def scene_chain(h):
    save_scene(h, 1, [(1, 1)] * 4 + [(2, 3)] * 4)
    save_scene(h, 0, [(0, 0)] * 8)
    h.press(14)
    h.down(16)
    h.down(17)
    h.up(17)
    h.up(16)
    h.hits.clear()
    h.play()
    h.run_ticks(400)


def load(playing):
    def f(h):
        if playing:
            h.play()
            h.run_ticks(20)
        h.hits.clear()
        h.call(READ_DONE, SESSION, maxins=20_000_000)
        if playing:
            h.run_ticks(30)
        else:
            h.heartbeat(30)
    return f


def countin(h):
    from notes import param, PLAY_STORE
    h.press(0)
    for _ in range(4):                  # Shift + Clear to state 2 (count-in): Clear's LED with Shift held
        h.shift(True)
        led = h.led_frame()[55]
        h.shift(False)
        if led == 0x32:
            break
        h.press(23, shift=True)
    h.press(16)                         # Record armed
    h.hits.clear()
    h.press(17)                         # Play: taken, the count starts
    for t in range(1, 1200):
        h.heartbeat()
        if t % 10 == 0:
            h.led_frame()
            if param(h, PLAY_STORE, 0):
                break
    h.started = h.tick
    h.run_ticks(30)


def takeover_counts(h, label):
    """At each tick where some track's fp == 0 event has the scene flag, the events per track at that tick."""
    ev = [x for x in h.hits if x[1] == "track_advance" and x[3]["fp"] == 0 and x[3]["scene"]]
    ticks = sorted({x[2] for x in ev})
    for tk in ticks:
        per = Counter(x[3]["track"] for x in ev if x[2] == tk)
        kinds = {x[3]["track"]: ("ended" if x[3]["end"] else "cut") + f"/hand {x[3]['hand']}" for x in ev if x[2] == tk}
        print(f"    {label}: takeover tick {tk}: events per track {dict(sorted(per.items()))} "
              f"(every track exactly once: {sorted(per) == list(range(8)) and set(per.values()) == {1}}); {kinds}")
    if not ticks:
        print(f"    {label}: no scene event")


if __name__ == "__main__":
    print("== contexts")
    scen("Play from stop", play_from_stop)
    scen("Stop, Shift + Play (continue)", shift_play)
    hp = scen("Patterns tap (Synth 1 P2) and a hand chain (Drum 1 P1..P3) while playing", pattern_tap)
    scen("Shift + Patterns pad (Synth 1 P2) while playing", shift_pattern)
    scen("a pick while stopped", stopped_pick)
    hs = scen("a scene recalled by hand while playing (Drum 1 16 steps, Synth 1 6)", scene_recall,
              lengths=[6, 8, 8, 8, 16, 8, 8, 8])
    hc = scen("a scene chain 0..1 advancing by itself", scene_chain, lengths=[16, 6, 8, 8, 8, 8, 8, 8])
    scen("a load, stopped", load(False))
    scen("a load, playing", load(True))
    if PL19.exists():
        hi = scen("CTPlay's count-in start (PL19 image)", countin, image=PL19.read_bytes())
        first = [x for x in hi.hits if x[1] == "player_tick" and x[3][1] == 0]
        print(f"    count-in: transport started at tick {hi.started}; first tick-0 pass in {first[0][0] if first else None}")
    else:
        print("[count-in] skipped: build PL19 first (../.venv/bin/python -m slimbuild versions/PL19.toml)")
    others = sorted(x for x in ALL if x[1] in ("player_tick", "track_advance") and x[0] != "main")
    print(f"\n== player_tick / track_advance outside main: {others or 'none'}")

    print("\n== scene takeovers (fp == 0, scene flag set)")
    takeover_counts(hs, "hand recall")
    takeover_counts(hc, "scene chain")

    print("\n== hand picks: the picked tracks' fp == 0 pass events after the tap")
    for t, label in ((0, "Synth 1 tap P2"), (4, "Drum 1 chain P1..P3")):
        ev = [(x[2], x[3]["pattern"], x[3]["end"], x[3]["hand"], x[3]["scene"]) for x in hp.hits
              if x[1] == "track_advance" and x[3]["track"] == t and x[3]["fp"] == 0 and (x[3]["end"] or x[3]["scene"])]
        print(f"    {label}: (tick, old pattern, end, hand, scene) {ev[:4]}")
    ev = [(x[2], x[3]["track"]) for x in hp.hits if x[1] == "track_advance" and x[3]["fp"] == 0 and x[3]["hand"]
          and x[3]["track"] not in (0, 4)]
    print(f"    other tracks with hand == 1: {ev or 'none'}")
