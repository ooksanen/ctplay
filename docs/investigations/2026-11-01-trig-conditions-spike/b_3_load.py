"""B3: a project load (stock's read-done handler 0x0802FD5C, the record already holding the file, as
tests/test_saved.py), stopped and playing: what happens to the chains, the hand flags, the scene, the positions."""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
from b_lib import *
from b_3_hand import fresh, pass_events

READ_DONE, SESSION = 0x0802FD5C, 0x2003D71C


def hooks(h):
    calls = []
    h.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: calls.append(
        ("pos", u.reg_read(UC_ARM_REG_R1), u.reg_read(UC_ARM_REG_R2), u.reg_read(UC_ARM_REG_R3),
         hex(u.reg_read(UC_ARM_REG_LR) & ~1))), begin=0x0802C240, end=0x0802C240)
    return calls


for playing in (False, True):
    h = fresh()
    calls = hooks(h)
    h.press(13)
    h.down(8); h.down(24); h.up(24); h.up(8)            # Synth 1 chain 1..3 (stopped: takes it at once)
    if playing:
        h.play()
        h.run_ticks(20)
    print(f"== load, {'playing' if playing else 'stopped'}: before", snapshot(h))
    log = []
    watch_writes(h, engine_regions(h), log)
    h.clear_logs(); calls.clear()
    h.call(READ_DONE, SESSION, maxins=20_000_000)
    print("  after", snapshot(h), "transport", h.transport())
    print("  order during the load:", [o for o in h.order if o[1] in ("seq_start", "tick", "cd42")][:6], "0x0802C240 calls", calls[:9])
    ch = sorted({(n, o) for _, n, o, s, v, pc in log if n.startswith("chain.b")})
    print("  chain-store writes (buffer, offset):", ch[:20], "pcs", sorted({hex(pc) for *_, pc in log if True})[:12])
    if playing:
        h.clear_logs()
        h.run_ticks(60)
        print("  60 ticks later:", snapshot(h))
        print("  Synth 1 pass events:", [(a[0], a[1]) for a in pass_events(h, 0)], "steps", steps_played(h.t0, 0)[:6])
