"""B2: what Play resets. Chains, directions and first/last settings on several tracks; Play, run into the chain's
second pattern, Stop (Play again), Play: where every track starts, and the engine state Play leaves."""
from b_lib import *
from b_3_hand import fresh

CFG = {
    0: dict(chain=(0, 2), pats={p: (7, 0, 3, 0) for p in range(8)}),
    1: dict(chain=(1, 3), pats={p: (11, 4, 3, 1) for p in range(8)}),        # reverse, steps 4..11
    2: dict(chain=(0, 1), pats={p: (7, 2, 3, 2) for p in range(8)}),         # ping-pong 2..7
    3: dict(chain=(0, 1), pats={p: (7, 0, 3, 3) for p in range(8)}),         # random
    4: dict(chain=(2, 4), pats={p: (5, 0, 3, 0) for p in range(8)}),
    5: dict(chain=(0, 0), pats={p: (15, 0, 7, 0) for p in range(8)}),        # 24 ticks a step
    6: dict(chain=(0, 1), pats={p: (3, 30, 3, 0) for p in range(8)}),        # wraps 30..3
    7: dict(chain=(0, 0), pats={p: (7, 0, 3, 0) for p in range(8)}),
}


def state(h):
    return dict(tick=store_bytes(h, h.r32(E + 0x90), 0).hex(), playing=[h.playing(t) for t in range(8)],
                pp=[h.r8(E + 0x94 + t) for t in range(8)], flags=[h.chain_flag(t) for t in range(8)],
                scene=h.scene(), fc=h.r8(E + 0xFC))


def first_steps(h, since):
    out = {}
    for tk, t, p, s in h.t0:
        if tk >= since and t not in out:
            out[t] = (tk, p, s)
    return out


h = fresh(CFG)
h.clear_logs()
h.play()
print("Play 1: transport", h.transport(), "state", state(h))
print("  first tick-0 per track:", first_steps(h, 0))
h.run_ticks(80)
print("after 80 ticks:", state(h))
h.press(PLAY)
print("Stop: transport", h.transport(), "state", state(h))
h.heartbeat(200)
mark = h.tick
n_adv = len(h.adv)
h.play()
print("Play 2: transport", h.transport(), "state", state(h))
print("  first tick-0 per track:", first_steps(h, mark))
print("  track advance entries during Play itself:", h.adv[n_adv:][:4])
h.run_ticks(80)
h.press(PLAY)
h.heartbeat(50)
mark = h.tick
h.press(PLAY, shift=True)
print("Shift + Play from stop: transport", h.transport(), "state", state(h))
print("  first tick-0 per track:", first_steps(h, mark))
# hand flag pending at Stop: picked while playing, then Stop, then Play
h.press(PLAY) if h.transport()[0] else None
h.play(); h.run_ticks(10)
h.press(13); h.pad(8 + 0)                      # Synth 1 pattern 1
print("picked Synth 1 pattern 1 while playing: flag", h.chain_flag(0), "chain", h.chain(0))
h.press(PLAY); h.heartbeat(50)
print("after Stop: flag", h.chain_flag(0), "chain", h.chain(0), "playing", h.playing(0))
mark = h.tick
h.play()
print("Play: flag", h.chain_flag(0), "playing", h.playing(0), "first tick-0:", first_steps(h, mark).get(0))
