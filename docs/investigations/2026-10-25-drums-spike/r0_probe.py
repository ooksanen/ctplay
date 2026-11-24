"""Run 0: objects in the snapshot, mode, sinks, the playing / mirrored pattern, quantise."""
import time
from lib2 import *
t0 = time.time()
h = DH()
print("mode at start", h.view_mode(), "track", h.r8(CONT + 0x188))
h.press(4)
print("after Drum 1: mode", h.view_mode(), "track", h.r8(CONT + 0x188))
for _ in range(3):
    h.press(NOTE_BTN); print(" Note -> mode", h.view_mode())
for which in ("expanded", "sample", "player"):
    s = h.sink(which); print(which, "sink", hex(s), "vt", hex(h.r32(s)), "adapter", hex(h.r32(s + 8)), "track byte", hex(h.r8(s + 0xC)))
print("expanded view", hex(h.expanded_view()), "vt", hex(h.r32(h.expanded_view())))
print("sample view d0", hex(h.sample_view(0)), "vt", hex(h.r32(h.sample_view(0))))
for d in range(4):
    print(f"drum {d+1}: rec {h.drec(d):#x} vt {h.r32(h.drec(d)):#x} base {h.base(d):#x} store {h.store(d):#x} editor {h.editor(d):#x} vt {h.r32(h.editor(d)):#x} play {h.playing_pattern(d)} mirror {h.mirrored_pattern(d)} q {h.quantise_flag(d)}")
print("quant setting bit12", h.quant_setting(), "transport", h.transport())
p = h.playing_pattern(0)
print("drum1 pattern", p, fmt_hits(h.hits(0, p)), h.arrays(0, p)["set"].hex())
print("store", fmt_hits(h.store_hits(0)))
print("store +0x18", hex(h.r32(h.store(0) + 0x18)), "pattern+0xA8", hex(h.base(0) + PAT * p + 0xA8))
print("mute store p0 drum1", param(h, h.r32(h.player(0) + 0x28), 0))
print("time", time.time() - t0)
