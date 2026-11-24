"""q4_tick0: which task plays a pattern's step 0 at Play: seq_start (0x0802C008, the Play handler, UI task) and the
first seq_play_step calls of player 0, with the task (the harness's heartbeat = Main) and the ms."""
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0

from lib import SEQ_START, SH, pl18, prepare
from notes import step_addr

IMG, M = pl18()
h = SH(IMG)
prepare(h)
h.uc.mem_write(step_addr(0, 0, 0), bytes([7, 7, 0, 0, 48, 6, 0, 100, 52, 6, 0, 100, 55, 6, 0, 100]) + bytes(12))
ev = []
h.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: ev.append(("seq_start", h.task, h.ms)), begin=SEQ_START, end=SEQ_START)
h.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: ev.append(("seq_play_step", h.task, h.ms, u.reg_read(UC_ARM_REG_R0 + 2),
                                                          u.reg_read(UC_ARM_REG_R0 + 3)))
              if u.reg_read(UC_ARM_REG_R0) == 0x20040200 else None, begin=0x08040E5A, end=0x08040E5A)
h.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: ev.append(("seq_note_on", h.task, h.ms, u.reg_read(UC_ARM_REG_R0 + 1)))
              if u.reg_read(UC_ARM_REG_R0) == 0x20040200 else None, begin=0x08040FA2, end=0x08040FA2)
for i in range(2):
    ev.clear()
    h.press(17)
    h.heartbeat(60)
    print(f"Play #{i + 1}:", ev[:8])
    h.press(17)
    h.heartbeat(20)
