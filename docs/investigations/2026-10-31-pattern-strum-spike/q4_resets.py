"""q4_resets: what reaches the player's end-all 0x08040D36 (slot 3 of the note players' vtable 0x0805B750), with
the task, and which of the listener's stores changed (0x0804A5C6: [p + 0x24] any change, [p + 0x1C] p0 -> 0,
[p + 0x28] p0 != 0). Static: the only call is the listener's reset 0x0804A79C (blx [vt + 0xC] at 0x0804A7A4); no
literal or other vtable holds 0x08040D37. Actions: Play / Stop; a pattern change in the Patterns view while playing,
waited past the loop's end (32 steps); the same while stopped; Mixer mute on / off (pad 0); Shift + Play? not tried.
Commits of the listener's stores are logged (store_commit 0x080353C0 with r0 = the store)."""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0

from lib import SH, pl18, prepare
from q3_probe import p

IMG, M = pl18()
PLAYERS = tuple(0x20040200 + 0x184 * t for t in range(4))
END_ALL, COMMIT = 0x08040D36, 0x080353C0
ENGINE = 0x20038EC0

h = SH(IMG)
prepare(h)
P = PLAYERS[0]
names = {h.r32(P + 0x1C): "play store [p+0x1C]", h.r32(P + 0x24): "[p+0x24]", h.r32(P + 0x28): "track 0 [p+0x28]"}
ev = []


def end_all(u, a, s, d):
    if u.reg_read(UC_ARM_REG_R0) in PLAYERS:
        ev.append(("end-all", h.task, hex(u.reg_read(UC_ARM_REG_LR) & ~1), PLAYERS.index(u.reg_read(UC_ARM_REG_R0))))


def commit(u, a, s, d):
    st = u.reg_read(UC_ARM_REG_R0)
    if st in names:
        ev.append(("commit", h.task, names[st]))


h.uc.hook_add(UC_HOOK_CODE, end_all, begin=END_ALL, end=END_ALL)
h.uc.hook_add(UC_HOOK_CODE, commit, begin=COMMIT, end=COMMIT)
steps_ms = 32 * 160 + 400
for label, act in (
        ("Play", lambda: h.press(17)),
        ("Patterns view, pattern 1 for track 0 (pad 8), one loop", lambda: (h.press(13), h.pad(8), h.heartbeat(steps_ms))),
        ("Mixer pad 0 (track 0 mute on)", lambda: (h.press(14), h.pad(0), h.heartbeat(200))),
        ("Mixer pad 0 again (off)", lambda: (h.pad(0), h.heartbeat(200))),
        ("Stop", lambda: h.press(17)),
        ("stopped: Patterns view, pattern 2 (pad 16)", lambda: (h.press(13), h.pad(16), h.heartbeat(50)))):
    ev.clear()
    act()
    seen = sorted(set(ev), key=str)
    print(f"{label}: playing pattern {p(h, h.r32(ENGINE + 0x30), 0)}; {seen}")
