"""Run 5c (detail): drum synth_on events by note while drum 1 is muted (player [+0x28] p0 = 1)."""
from unicorn import UC_HOOK_CODE
from lib2 import *
h = DH()
p = drum_setup(h, mode=6)
b = h.base(0) + PAT * p
h.uc.mem_write(b, bytes([100] * 32)); h.uc.mem_write(b + 0x60, bytes([1] * 32)); h.call(0x0803F050, h.editor(0))
h.press(PLAY); h.heartbeat(300)
print("unmuted 300 ms, synth_on (synth, note):", sorted({(e[1], e[2]) for e in h.take("synth_on")}), )
h.set_p0(h.r32(h.player(0) + 0x28), 1); h.take()
ev = []
for t in range(300):
    h.heartbeat(1); ev += [(t, e[1], e[2]) for e in h.take("synth_on")]
print("muted 300 ms, synth_on (ms, synth, note):", ev)
