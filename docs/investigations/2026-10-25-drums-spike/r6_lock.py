"""Run 6b: the drum hit's sound endpoint (0x0803BD58 with synth 16) run for real (not stubbed): lock takes
(semaphore 0x08021064, the base harness's 'dsp' stub) and DSP writes inside one note_sink_on / _off; the same for a
finger press. Run 5c: is [player + 0x28] p0 the mute (player slot 2 0x08041252 calls for drum 1), and what a live hit
of a muted drum sends to the endpoints."""
from unicorn import UC_HOOK_CODE
from lib2 import *
import voices

class DHV(voices.VoiceHarness, DH):
    pass

h = DHV(STOCK)
p = drum_setup(h, mode=6)
fixed_velocity(h, False)
h.press(RECORD); h.press(PLAY); h.heartbeat(3)
s = h.sink("expanded")
h.take(); h.dsp_writes.clear()
r_on = h.on(s, 1, 100); l_on = h.take()
h.heartbeat(1)
r_off = h.off(s, 1); l_off = h.take()
print("live sink on : lock takes", sum(1 for e in r_on[0] if e[0] == "dsp"), " ev", r_on[0], " DSP writes", [(c, hex(v), hex(a)) for c, v, a in r_on[1]], " log", l_on)
print("live sink off: lock takes", sum(1 for e in r_off[0] if e[0] == "dsp"), " ev", r_off[0], " DSP writes", [(c, hex(v), hex(a)) for c, v, a in r_off[1]], " log", l_off)
n0, d0 = len(h.ev), len(h.dsp_writes)
h.down(28, 100); fe = h.ev[n0:]; fd = h.dsp_writes[d0:]
h.heartbeat(1); h.up(28)
print("finger pad 29 on: lock takes", sum(1 for e in fe if e[0] == "dsp"), " DSP writes", [(c, hex(v), hex(a)) for c, v, a in fd])
n0 = len(h.ev); h.heartbeat(1)
print("one bare heartbeat: ev", h.ev[n0:])

print("== 5c mute")
h = DH()
p = drum_setup(h, mode=6)
fixed_velocity(h, False)
h.clear_pattern(0, p)
b = h.base(0) + PAT * p
# a hit on every step of the playing pattern (raw + editor load), so the player plays drum 1 each step
h.uc.mem_write(b, bytes([100] * 32)); h.uc.mem_write(b + 0x60, bytes([1] * 32)); h.call(0x0803F050, h.editor(0))
pl = h.player(0)
slot2 = []
h.uc.hook_add(UC_HOOK_CODE, lambda u, a, sz, d: slot2.append(h.ticks) if u.reg_read(UC_ARM_REG_R0) == pl else None, begin=0x08041252, end=0x08041252)
h.press(PLAY); h.heartbeat(300)
on_unmuted = len([e for e in h.take("synth_on") if e[1] == 16])
print(" unmuted 300 ms: player slot 2 calls", len(slot2), " drum synth_on (synth 16)", on_unmuted)
h.set_p0(h.r32(pl + 0x28), 1); slot2.clear(); h.take()
h.heartbeat(300)
print(" muted (player [+0x28] p0 = 1) 300 ms: player slot 2 calls", len(slot2), " synth_on 16:", len([e for e in h.take('synth_on') if e[1] == 16]))
h.on(h.sink("expanded"), 1, 100); lg = h.take(); h.heartbeat(1); h.off(h.sink("expanded"), 1)
print(" muted, live hit through the expanded sink: endpoint log", lg)
