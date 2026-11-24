"""Run 4: count-in (transport p2) and stopped with Record armed; run 5: which sink records, and a Mixer-muted drum;
run 6: side effects of one note_sink_on / _off (DSP lock takes, DSP writes, MIDI out, the expanded view's LEDs)."""
from lib2 import *

def setp(h, store, i, v):
    h.call(PARAM_WPTR, store, i)
    h.uc.mem_write(h.uc.reg_read(UC_ARM_REG_R0), struct.pack("<I", v))
    h.call(PARAM_COMMIT, store)

def go(mode=6, play=True, rec=True, quant_off=True):
    h = DH()
    p = drum_setup(h, mode=mode)
    fixed_velocity(h, False)
    if quant_off:
        h.press(RECORD, shift=True)
    if rec:
        h.press(RECORD)
    if play:
        h.press(PLAY)
    h.heartbeat(1)
    h.until_tick(h.ticks + (6 - h.ticks % 6) % 6)
    h.gate.clear(); h.writes.clear(); h.slot0.clear()
    return h, p

print("== 4: count-in / stopped")
h, p = go()
setp(h, PLAY_STORE, 2, 1)
print(" transport with p2 = 1:", h.transport())
n = repeat(h, h.sink("expanded"), 6, 24, vels=[100])
print(f" count-in (p2 = 1), {n} hits: pattern", fmt_hits(h.hits(0, p)), " gate calls", len(h.gate), " slot0", len(h.slot0))
setp(h, PLAY_STORE, 2, 0)
n = repeat(h, h.sink("expanded"), 6, 24, vels=[100])
h.heartbeat(10)
print(f" then p2 = 0, {n} more hits: pattern", fmt_hits(h.hits(0, p)))

h, p = go(play=False)
print(" stopped, Record armed: transport", h.transport())
for _ in range(4):
    h.on(h.sink("expanded"), 1, 100); h.heartbeat(30); h.off(h.sink("expanded"), 1); h.heartbeat(30)
print("  4 hits: pattern", fmt_hits(h.hits(0, p)), " gate calls", len(h.gate), " slot0", len(h.slot0))

print("== 5: which sink records")
for mode in (6, 1):
    for which in ("expanded", "sample", "player"):
        h, p = go(mode=mode)
        n = repeat(h, h.sink(which, 0), 6, 24, vels=[100])
        h.heartbeat(10)
        print(f" mode {mode}, {which} sink {h.sink(which, 0):#x}: {n} hits -> pattern", fmt_hits(h.hits(0, p)),
              " gate on calls", sum(1 for g in h.gate if g[1] == 'on'))

print("== 5b: drum 1 muted (player [+0x28] p0 = 1)")
h, p = go()
mute = h.r32(h.player(0) + 0x28)
h.set_p0(mute, 1)
# the player's own hits of drum 1: write one hit at step 4 in the pattern, see if the player sink fires
psink = h.sink("player")
calls = []
from unicorn import UC_HOOK_CODE
h.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: calls.append(h.ticks) if u.reg_read(UC_ARM_REG_R0) == psink else None,
              begin=NOTE_ON, end=NOTE_ON)
n0 = len(h.dsp_writes); h.take()
r = h.on(h.sink("expanded"), 1, 100)
midi = h.take("midi_on", "midi_off")
h.heartbeat(1)
h.off(h.sink("expanded"), 1)
print(" muted: one live hit: lock takes", sum(1 for e in r[0] if e[0] == 'dsp'), " DSP writes", r[1], " MIDI", midi)
n = repeat(h, h.sink("expanded"), 6, 24, vels=[100])
h.heartbeat(10)
print(f" muted, {n} live hits: pattern", fmt_hits(h.hits(0, p)), "| player-sink note-ons while muted:", len(calls))
h.set_p0(mute, 0)
calls.clear()
h.heartbeat(400)
print(" unmuted, 400 ms of playback: player-sink note-ons:", len(calls), "(the recorded hits play back)")

print("== 6: side effects of one hit (stock, playing, Record armed)")
h, p = go()
s = h.sink("expanded")
base = h.leds()[28:32]
h.take()
r_on = h.on(s, 1, 100)
log_on = h.take()
during = h.leds()[28:32]
mask_on = h.r32(h.expanded_view() + 0xC)
h.heartbeat(1)
h.take()
r_off = h.off(s, 1)
log_off = h.take()
after = h.leds()[28:32]
print(" on : ev", r_on[0], " DSP writes", [tuple(hex(x) for x in w) for w in r_on[1]], " endpoint log", log_on)
print(" off: ev", r_off[0], " DSP writes", [tuple(hex(x) for x in w) for w in r_off[1]], " endpoint log", log_off)
print(" pads 29-32 LEDs before", [hex(x) for x in base], "sounding", [hex(x) for x in during], "after off", [hex(x) for x in after])
print(" [view+0xC]", hex(mask_on), " forbidden writes", h.forbidden_writes)
# the finger press for comparison
h.take(); n0 = len(h.ev)
h.down(28, 100); fl_on = h.take(); fd = h.leds()[28:32]
h.heartbeat(1); h.up(28); fl_off = h.take(); fa = h.leds()[28:32]
print(" finger pad 29 for comparison: on log", fl_on, "off log", fl_off, " LEDs held", [hex(x) for x in fd], "released", [hex(x) for x in fa])
