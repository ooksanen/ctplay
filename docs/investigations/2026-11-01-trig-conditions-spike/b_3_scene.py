"""B3 scenes: save scenes through the Mixer view (Shift + a scene pad, stopped), then recall one while playing (a
scene pad) and see when each track takes it over, and what 0x0802CD42 sees then."""
import sys
from b_lib import *
from b_3_hand import fresh, pass_events

SCENE_OBJ = E + 0x24


def scene_words(h):
    st = h.r32(SCENE_OBJ)
    return [store_bytes(h, st, i).hex() for i in range(32)]


def save_scene(h, scene, chains):
    """Stopped: set every track's chain in the Patterns view (hold first, press last), then Mixer, Shift + the
    scene pad (16 + scene)."""
    h.press(13)
    for t, (f, l) in enumerate(chains):
        assert f < 4 and l < 4
        h.down(8 * f + t)
        if l != f:
            h.down(8 * l + t); h.up(8 * l + t)
        h.up(8 * f + t)
    got = [h.chain(t) for t in range(8)]
    assert got == list(chains), got
    h.press(14)
    h.shift(True)
    h.pad(16 + scene)
    h.shift(False)


def run(lengths, scene_tap_tick=10, ticks=260, which=1):
    cfg = {t: dict(chain=(0, 0), pats={p: (lengths[t] - 1, 0, 3, 0) for p in range(8)}) for t in range(8)}
    h = fresh(cfg)
    before = scene_words(h)
    save_scene(h, 1, [(1, 1)] * 4 + [(2, 3)] * 4)
    save_scene(h, 0, [(0, 0)] * 8)
    after = scene_words(h)
    print("  scene store words changed:", [(i, before[i], after[i]) for i in range(32) if before[i] != after[i]])
    print("  chains now", [h.chain(t) for t in range(8)], "flags", [h.chain_flag(t) for t in range(8)])
    h.press(14)
    h.clear_logs()
    h.play()
    h.run_ticks(scene_tap_tick)
    h.pad(16 + which)
    print(f"  tick {h.tick}: tapped scene {which}: scene chain {h.scene_chain()} scene {h.scene()} chains",
          [h.chain(t) for t in range(8)], "flags", [h.chain_flag(t) for t in range(8)], "queued",
          [h.queued(t)[:2].hex() for t in range(8)])
    seen = []
    for _ in range(ticks):
        h.run_ticks(1)
        s = (h.scene(), h.scene_chain(), tuple(h.chain_flag(t) for t in range(8)))
        if not seen or seen[-1][1] != s:
            seen.append((h.tick, s))
    print("  (tick, (scene, scene chain, flags)) changes:", seen)
    for t in range(8):
        print(f"  track {t} (len {lengths[t]}): pass events", [(a[0], a[1]['old'], a[1]['r4'], a[1]['scene'], a[1]['hand']) for a in pass_events(h, t)][:6])
        print(f"      chosen:", [(c[0], c[2], c[3]) for c in h.chosen if c[1] == t and c[4] == 0 and c[2] != h.playing(t)[0] or (c[1] == t and c[4] == 0 and c[3] == 0)][:6])
    return h


if __name__ == "__main__" and "s3" not in sys.argv:
    print("== S1: Drum 1 8 steps, Synth 1 16, Synth 2 6, others 8; scene 1 tapped at tick 10")
    run([16, 6, 8, 8, 8, 8, 8, 8])
    print("== S2: Drum 1 16 steps, Synth 1 6, others 8")
    run([6, 8, 8, 8, 16, 8, 8, 8])


def s3_scene_chain():
    """A scene chain 0..1 (Mixer: hold scene pad 16, press 17), Play: the scenes advance by themselves."""
    print("== S3: scene chain 0..1 advancing by itself (scene 0: all (0,0); scene 1: synths (1,1), drums (2,3))")
    lengths = [16, 6, 8, 8, 8, 8, 8, 8]
    cfg = {t: dict(chain=(0, 0), pats={p: (lengths[t] - 1, 0, 3, 0) for p in range(8)}) for t in range(8)}
    h = fresh(cfg)
    save_scene(h, 1, [(1, 1)] * 4 + [(2, 3)] * 4)
    save_scene(h, 0, [(0, 0)] * 8)
    h.press(14)
    h.down(16); h.down(17); h.up(17); h.up(16)
    print("  scene chain", h.scene_chain(), "scene", h.scene(), "chains", [h.chain(t) for t in range(8)],
          "flags", [h.chain_flag(t) for t in range(8)])
    h.clear_logs()
    h.play()
    print("  after Play: scene chain", h.scene_chain(), "scene", h.scene(), "flags", [h.chain_flag(t) for t in range(8)])
    seen = []
    for _ in range(500):
        h.run_ticks(1)
        s = (h.scene(), h.scene_chain(), tuple(h.chain_flag(t) for t in range(8)), h.r8(E + 0xFC))
        if not seen or seen[-1][1] != s:
            seen.append((h.tick, s))
    print("  (tick, (scene, scene chain, flags, E+0xFC)) changes:", seen)
    for t in (0, 1, 4):
        print(f"  track {t} (len {lengths[t]}): pass events", [(a[0], a[1]['old'], a[1]['r4'], a[1]['scene'], a[1]['hand']) for a in pass_events(h, t)][:10])


if __name__ == "__main__" and "s3" in sys.argv:
    s3_scene_chain()
