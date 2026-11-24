"""q4_batch: who reads the batch flag 0x20006A50 and 0x20006A48, with the synth note-on running for real
(tests/voices.py VoiceHarness: stock's voice decision, the DSP mailbox modelled). Track 0: pattern 0 with a triad on
step 0; Play 700 ms; a live pad; a held step with notes (stock's step preview, 0x0804AF7E: sets the flag in the UI
task); a single note-on through seq_note_on outside any batch (the flag 0) vs one inside (the flag set by hand), with
the calls the synth note-on makes after 0x0803BD8A compared.
Static scan (re/app.asm, literal loads and [reg, #imm] after them): 0x20006A50 is read only at 0x0803BD82 (the synth
note-on 0x0803BD58: vel != 0, synth < 2 and the flag set -> 0x20006A48 = 1); 0x20006A48 is written at 0x0803BD8A and
cleared at 0x0803BDC4 (with the flag), read nowhere."""
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_PC

from lib import pl18, prepare
from notes import step_addr
from voices import VoiceHarness

IMG, M = pl18()
PLAYER, NOTE_ON = 0x20040200, 0x08040FA2


class VH(VoiceHarness):
    def __init__(self, image):
        super().__init__(image)
        self.t, self.task = 0, "ui"
        self.acc = {}

        def mem(u, access, addr, size, value, d):
            for a in (0x20006A48, 0x20006A50):
                if addr <= a < addr + size:
                    k = (hex(u.reg_read(UC_ARM_REG_PC)), "write" if access == 17 else "read", hex(a), self.task)
                    self.acc[k] = self.acc.get(k, 0) + 1
        self.uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, mem, begin=0x20006A44, end=0x20006A53)

    def heartbeat(self, n=1):
        self.task = "main"
        super().heartbeat(n)
        self.task = "ui"

    def rec(self):
        return self.r32(0x2003C174)


def report(h, label):
    print(f"  {label}: {sorted(h.acc.items())}")
    h.acc.clear()


h = VH(IMG)
h.track(0)
prepare(h)
h.uc.mem_write(step_addr(0, 0, 0), bytes([7, 7, 0, 0, 48, 6, 0, 100, 52, 6, 0, 100, 55, 6, 0, 100]) + bytes(12))
h.uc.mem_write(step_addr(0, 0, 2), bytes([1, 7, 0, 0, 60, 6, 0, 100]) + bytes(20))
h.acc.clear()
h.press(17)
h.heartbeat(700)
report(h, "playback (Main task)")
h.press(17)
h.heartbeat(50)
h.acc.clear()
h.down(24); h.heartbeat(30); h.up(24); h.heartbeat(30)
report(h, "a live pad (UI task)")
h.down(2); h.heartbeat(30); h.up(2); h.heartbeat(30)
report(h, "step 3 held: stock's step preview")

# one note-on through seq_note_on from outside a batch, then inside one; what the synth note-on does after its test
trace = []
h.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: trace.append(a), begin=0x0803BD7A, end=0x0803BD92)
for flag in (0, 1):
    trace.clear()
    h.uc.mem_write(0x20006A50, bytes([flag]))
    h.uc.mem_write(0x20006A48, b"\0")
    h.call(NOTE_ON, PLAYER, 64, 100, 6, 0)              # tie (the 5th argument) on the stack: 0
    a48 = h.r8(0x20006A48)
    h.uc.mem_write(0x20006A50, b"\0")
    h.uc.mem_write(0x20006A48, b"\0")
    print(f"  seq_note_on with the flag {flag}: synth note-on path {[hex(a) for a in sorted(set(trace))]};"
          f" 0x20006A48 after = {a48}")
    report(h, f"   accesses (flag {flag})")
    h.call(0x08040D36, PLAYER)                          # end it again (the player's end-all)
