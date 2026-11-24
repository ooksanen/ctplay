# Q2a: the shared mode byte. From each note-track view, open Drum 1 by the real route (button 4) and by slim's page_open
# replay (cont_select_track, cont_track_view(cont, 1), ctrl_set_view); then how Note (9) moves a drum between 1 and 6.
from drumlib import *
CONT_SELECT, CONT_VIEW, CTRL_SET_VIEW = 0x08043448, 0x0804348C, 0x0803390C

STARTS = {
    'Synth 1 Note (1)': [0],
    'Synth 1 expanded (6)': [0, BTN_NOTE],
    'Synth 1 Velocity': [0, BTN_VEL],
    'Synth 1 Gate': [0, BTN_GATE],
    'Synth 1 Gate x2': [0, BTN_GATE, BTN_GATE],
    'Synth 1 Pattern Settings': [0, BTN_PSET],
    'Synth 1 Pattern Settings x2': [0, BTN_PSET, BTN_PSET],
    'Synth 1 Preset': [0, 8],
    'Drum 2 expanded (6)': [5, BTN_NOTE],
    'Drum 1 expanded (6)': [4, BTN_NOTE],
    'Drum 1 Velocity': [4, BTN_VEL],
    'Drum 1 Preset': [4, 8],
    'Mixer': [0, 14],
    'FX': [0, 15],
    'Patterns (13)': [0, 13],
}

def page_open(h, track):
    h.set_p0(h.r32(MGR + 0xC), 1)              # Shift held, as in the hook
    h.call(CONT_SELECT, CONT, track)
    h.call(CONT_VIEW, CONT, 1); v = ret(h)
    h.call(CTRL_SET_VIEW, MGR, v, track)
    h.set_p0(h.r32(MGR + 0xC), 0)

for name, seq in STARTS.items():
    h = harness()
    for b in seq:
        h.press(b)
    s0 = state(h)
    h.press(4); s1 = state(h)
    g = harness()
    for b in seq:
        g.press(b)
    page_open(g, 4); s2 = state(g)
    print(f'{name:30s} start {s0}\n{"":30s} Drum 1 press -> {s1}\n{"":30s} page_open(4)  -> {s2}  same as press: {s1 == s2}')

# Note button on a drum: 1 -> 6 -> 1?
h = harness(); h.press(4)
for i in range(3):
    h.press(BTN_NOTE); print('Drum 1, Note press', i + 1, '->', state(h))
# From Velocity on a drum, Note once
h = harness(); h.press(4); h.press(BTN_VEL); h.press(BTN_NOTE); print('Drum 1 Velocity, Note ->', state(h))
# Shift + Note: what does it do?
h = harness(); h.press(4); h.press(BTN_NOTE, shift=True); print('Drum 1, Shift+Note ->', state(h))
# Direct cont_track_view(cont, 6) + set_view as a page_open variant for mode 6
h = harness(); h.press(0)
h.call(CONT_SELECT, CONT, 4); h.call(CONT_VIEW, CONT, 6); v = ret(h); h.call(CTRL_SET_VIEW, MGR, v, BTN_NOTE)
print('page_open variant cont_track_view(6) ->', state(h))
