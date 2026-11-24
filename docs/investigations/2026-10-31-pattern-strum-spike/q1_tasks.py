"""q1_tasks: the task and stock call site of every commit of a strum's notes, for each way a strum's notes reach the
commit: released (rising: the root's note-off is stock's, UI; the others the heartbeat's), a quick tap (the tick
pass), Stop while held (Play button), Record off while held (Record button), and a second pad on the same track held
over the first (two strums interleaved in the heartbeat). Triad, slow, quantise on, press at tick 40.
Each commit also shows the transport store 0x20011034's parameters 0 (playing) and 1 (recording) as param_get reads
them (0x0803542C: bit i of [store + 4] picks buffer [store + 0xC] or [+ 0x10], parameter at + 4 i) at the commit's
entry: can a handler tell the flush (Stop / Record off) by them?"""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0

from lib import COMMIT, PLAY, RECORD, pl18, setup, wait_tick

TRANSPORT = 0x20011034

IMG, M = pl18()


def run(label, act, hold=600, down=False):
    h = setup(IMG, M, speed=1, down=down)
    tr = []

    def commit(u, a, s, d):
        if u.reg_read(UC_ARM_REG_R0) == h.rec() and h.pending(u.reg_read(UC_ARM_REG_R0 + 1)) & 7 != 7:
            sel = h.r32(TRANSPORT + 4)
            tr.append(tuple(h.r32(h.r32(TRANSPORT + 0xC + 4 * (sel >> i & 1)) + 4 * i) for i in (0, 1)))
    h.uc.hook_add(UC_HOOK_CODE, commit, begin=COMMIT, end=COMMIT)
    wait_tick(h, 40)
    h.strum.clear()
    h.down(24)
    act(h, hold)
    h.heartbeat(400)
    print(f"{label}: placed {[(p['note'], p['task']) for p in h.places]}")
    print(f"        commits (note, task, site, (playing, recording)) {[(c['note'], c['task'], c['site'], t) for c, t in zip(h.commits, tr)]}")


def release(h, hold):
    h.heartbeat(hold); h.up(24)


def tap(h, hold):
    h.heartbeat(100); h.up(24)


def stop(h, hold):
    h.heartbeat(hold); h.press(PLAY); h.heartbeat(50); h.up(24)


def record_off(h, hold):
    h.heartbeat(hold); h.press(RECORD); h.heartbeat(50); h.up(24)


def two_pads(h, hold):
    h.heartbeat(100); h.down(28); h.heartbeat(hold); h.up(24); h.heartbeat(30); h.up(28)


run("rising, released", release)
run("falling, released", release, down=True)
run("rising, tapped 100 ms", tap)
run("rising, Stop while held", stop)
run("rising, Record off while held", record_off)
run("rising, a second pad (28) pressed 100 ms in, both held", two_pads)
