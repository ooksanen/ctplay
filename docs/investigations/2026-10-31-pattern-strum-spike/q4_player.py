"""q4_player: stock's pattern player (track 0, player 0x20040200) as PL19's Played hook would see it.
1. Marks and held ties: at each seq_play_step(player, pattern, step, micro) entry (0x08040E5A), the byte
   [player + 0x13C + micro] and the held-tie bits [player + 0x128 ..]; then each seq_note_on (0x08040FA2: note, vel,
   length, [sp] tie) and the gate's rate read (param_get at 0x08040F0C: its store and the byte it returns).
   Pattern 0: step 0 C E G (gates 1, 6, 96) at microstep 0 and A (gate 6) at microstep 3; step 1 a tied D (gate
   6 | tie) and step 2 its continuation D (gate 6) beside F; step 3 C with probability byte 0. Rates 1/16 and 1/8.
2. Resets: every call of 0x08040D36 (slot 3 of the player's vtable) with its caller and task: Play, Stop, a pattern
   change in the Patterns view while playing, the Mixer's mute, Shift + Clear? (not tried), a project reload (not run).
3. The batch flag 0x20006A50 and 0x20006A48: every instruction that reads or writes them, while playing that pattern
   and pressing pads (a single note, a chord, a strum)."""
import struct

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

from lib import SH, pl18, prepare
from notes import PATTERN_BASE, step_addr
from q3_probe import p

IMG, M = pl18()
PLAYER = 0x20040200
PLAY_STEP, NOTE_ON, END_ALL, RATE_CALL = 0x08040E5A, 0x08040FA2, 0x08040D36, 0x08040F0C
C, D, E, F, G, A = 48, 50, 52, 53, 55, 57


def pattern(h, rate=3):
    base = PATTERN_BASE[0]
    def step(s, units, prob=7):
        body = b"".join(bytes(u) for u in units) + bytes(4 * (6 - len(units)))
        h.uc.mem_write(step_addr(0, 0, s), bytes([(1 << len(units)) - 1, prob, 0, 0]) + body)
    step(0, [(C, 1, 0, 100), (E, 6, 0, 90), (G, 96, 0, 80), (A, 6, 3, 70)])
    step(1, [(D, 6 | 0x80, 0, 100)])
    step(2, [(D, 6, 0, 100), (F, 6, 0, 100)])
    step(3, [(C, 6, 0, 100)], prob=0)
    h.uc.mem_write(base + 0x382, bytes([rate]))


def watch_player(h):
    ev = []

    def play(u, a, s, d):
        if u.reg_read(UC_ARM_REG_R0) != PLAYER:
            return
        r = [u.reg_read(UC_ARM_REG_R0 + i) for i in range(4)]
        ties = [n for n in range(128) if h.r32(PLAYER + 0x128 + 4 * (n >> 5)) >> (n & 31) & 1]
        cont = [n for n in range(128) if h.r32(PLAYER + 0x54 + 4 * (n >> 5)) >> (n & 31) & 1]
        ev.append(("play", h.ms, h.task, f"pattern {r[1]} step {r[2]} micro {r[3]} mark {h.r8(PLAYER + 0x13C + r[3]):#04x}"
                   f" held-ties {ties} tie-on {cont} free {h.r8(PLAYER + 0x78):#x} used {h.r8(PLAYER + 0x7A):#x}"))

    def note_on(u, a, s, d):
        if u.reg_read(UC_ARM_REG_R0) != PLAYER:
            return
        r = [u.reg_read(UC_ARM_REG_R0 + i) for i in range(4)]
        tie = struct.unpack("<I", bytes(u.mem_read(u.reg_read(UC_ARM_REG_SP), 4)))[0]
        ev.append(("note_on", h.ms, h.task, f"note {r[1]} vel {r[2]} length {r[3]} tie {tie}"))

    def rate(u, a, s, d):
        r0 = u.reg_read(UC_ARM_REG_R0)
        ev.append(("rate", h.ms, h.task, f"param_get({r0:#010x}, {u.reg_read(UC_ARM_REG_R0 + 1)})"))

    h.uc.hook_add(UC_HOOK_CODE, play, begin=PLAY_STEP, end=PLAY_STEP)
    h.uc.hook_add(UC_HOOK_CODE, note_on, begin=NOTE_ON, end=NOTE_ON)
    h.uc.hook_add(UC_HOOK_CODE, rate, begin=RATE_CALL, end=RATE_CALL)
    return ev


def part1(rate):
    h = SH(IMG)
    prepare(h)
    pattern(h, rate)
    ev = watch_player(h)
    print(f"-- 1. marks, ties, lengths at rate {rate} (step_ticks {h.r32(0x0805B8B8 + 4 * rate)});"
          f" [player + 0x10] = {h.r32(PLAYER + 0x10):#010x}: p1 = {p(h, h.r32(PLAYER + 0x10), 1)}")
    h.press(17)
    h.heartbeat(int(4.2 * 160 * (2 if rate == 4 else 1)))
    h.press(17)
    for e in ev:
        print("  ", e)


def part2():
    print("-- 2. resets (0x08040D36): caller and task")
    h = SH(IMG)
    prepare(h)
    pattern(h)
    stores = {o: h.r32(PLAYER + o) for o in range(0x8, 0x2C, 4)}
    print("   player stores:", {hex(o): hex(v) for o, v in stores.items()})
    ev = []

    def end_all(u, a, s, d):
        if u.reg_read(UC_ARM_REG_R0) in (PLAYER + 0x184 * t for t in range(4)):
            ev.append((h.task, hex(u.reg_read(UC_ARM_REG_LR) & ~1), hex(u.reg_read(UC_ARM_REG_R0))))
    h.uc.hook_add(UC_HOOK_CODE, end_all, begin=END_ALL, end=END_ALL)
    for label, act in (("Play", lambda: h.press(17)), ("1 s playing", lambda: h.heartbeat(1000)),
                       ("Stop", lambda: h.press(17)), ("Play again", lambda: h.press(17)),
                       ("Patterns view: pattern 2 for track 0 (pad 16), 2 s", lambda: (h.press(13), h.pad(16), h.heartbeat(2000))),
                       ("Mixer, pad 0 (mute Synth 1?), 0.5 s", lambda: (h.press(14), h.pad(0), h.heartbeat(500))),
                       ("Mixer, pad 0 again", lambda: (h.pad(0), h.heartbeat(300))),
                       ("Stop", lambda: h.press(17))):
        ev.clear()
        act()
        print(f"   {label}: {sorted(set(ev))}")


def part3():
    print("-- 3. batch flag 0x20006A50 / 0x20006A48: every access (pc, read / write, address, task)")
    from test_chord import set_chord, set_strum
    from chord_model import settings
    h = SH(IMG)
    prepare(h)
    pattern(h)
    acc = {}

    def mem(u, access, addr, size, value, d):
        for a in (0x20006A48, 0x20006A50):
            if addr <= a < addr + size:
                k = (hex(u.reg_read(UC_ARM_REG_PC)), "write" if access == UC_HOOK_MEM_WRITE or access == 17 else "read",
                     hex(a), h.task)
                acc[k] = acc.get(k, 0) + 1
    h.uc.hook_add(UC_HOOK_MEM_READ, mem, begin=0x20006A44, end=0x20006A53)
    h.uc.hook_add(UC_HOOK_MEM_WRITE, lambda u, ac, ad, sz, v, d: mem(u, UC_HOOK_MEM_WRITE, ad, sz, v, d),
                  begin=0x20006A44, end=0x20006A53)
    h.press(17)
    h.heartbeat(700)
    h.down(24); h.heartbeat(50); h.up(24); h.heartbeat(50)            # a single note
    set_chord(h, M, 0, settings(1))
    h.down(24); h.heartbeat(50); h.up(24); h.heartbeat(50)            # a chord (chord_send_on)
    set_strum(h, M, 0, 1)
    h.down(24); h.heartbeat(300); h.up(24); h.heartbeat(50)           # a strum (heartbeat sends)
    h.press(17)
    for k, n in sorted(acc.items()):
        print("  ", k, n)


part1(3)
part1(4)
part2()
part3()
