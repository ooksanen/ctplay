"""q3_held: the held step's pattern and step as stock's add 0x0804B094 (hook step_add) sees them, both step-entry
routes, both halves (1-16/17-32 = button 21), patterns 0 and 2: p0 / p1 of the recorder's position store [rec + 0x14]
(= step editor + 0x24) and p0 of the Note view's held-step store [view + 0x2C], read while the step pad is held
(step first: before the key pad; pad first: after the step pad's press, when stock's held-step listener has added)."""
from unicorn import UC_HOOK_CODE

from lib import SH, pl18, prepare
from q3_probe import p

IMG, M = pl18()
STEP_ADD = 0x0804B094


def run(pattern, half, route, pad):
    h = SH(IMG)
    prepare(h)
    if pattern:
        h.press(13)
        h.pad(8 * pattern)
        h.track(0)
    if half:
        h.press(21)
    seen = []

    def add(u, a, s, d):
        seen.append(a)
    h.uc.hook_add(UC_HOOK_CODE, add, begin=STEP_ADD, end=STEP_ADD)
    got = []

    def snap():
        pos = h.r32(h.rec() + 0x14)
        got.append((p(h, pos, 0), p(h, pos, 1), p(h, h.r32(h.note_view(0) + 0x2C), 0)))
    if route == "step first":
        h.down(pad); snap(); h.down(24); h.up(24); h.up(pad)
    else:
        h.down(24); h.down(pad); snap(); h.up(pad); h.up(24)
    h.heartbeat(3)
    print(f"pattern {pattern}, {'17-32' if half else '1-16'}, {route}, step pad {pad}: (pattern, step, held) = {got[0]};"
          f" step_add ran {len(seen)}x")


for pattern in (0, 2):
    for half in (0, 1):
        for route in ("step first", "pad first"):
            run(pattern, half, route, 15 if half else 3)
