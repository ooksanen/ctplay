"""Shared helpers for the PL20 builder check, part C (the controls). Throwaway spike, not tests.

Run from slim/ with PYTHONPATH=.:tests:../tools:docs/investigations/2026-11-01-trig-conditions-spike.
Pads are the controller's 0-31 (the spec's pad n = n - 1): row 3 = 16-23, row 4 = 24-31, drum pads 28-31."""
from __future__ import annotations

import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2

from harness import MGR
from notes import PARAM_GET, PLAY_STORE, NoteHarness, param

SLIM = Path(__file__).resolve().parents[3]
STOCK = (SLIM.parent / "stock/circuittracks-firmware-4486-STOCK.bin").read_bytes()
PL18 = SLIM / "build/PL18"

CONT = 0x20040DB8
TRACK_OF, VIEW_OF = 0x0805011E, 0x08043B6E         # track_of(cont); the view a pad goes to: (cont, pad)
SINK_ON, SINK_OFF = 0x0801D38E, 0x0801D942
SYNTH_ON, MIDI_ON = 0x0803BD58, 0x08029EFE
BTN_NOTE, BTN_VEL, BTN_GATE, BTN_PSET, BTN_PATTERNS, BTN_MIXER = 9, 10, 11, 12, 13, 14
BTN_PLAY, BTN_SHIFT = 17, 27
PROB_NOTE, PROB_DRUM, EXPANDED = 0x0805ACD4, 0x0805AB14, 0x0805AD44
MODE_PROB, MODE_EXPANDED = 5, 6
RAM0, RAM1 = 0x20000000, 0x20050000
NOTE_PAT = (0x20011B20, 0x20018060, 0x2002BAB8, 0x20031FF8)   # + 0xCA8 p + 28 s
SESSION = 0x2003D71C


def image_pl18() -> bytes:
    return (PL18 / "circuittracks-4486-PL18.bin").read_bytes()


class H(NoteHarness):
    """NoteHarness (stock's note endpoints logged and stubbed) that also logs every call to note_sink_on / off on any
    sink (`sinks`: (kind, sink, note, vel)), the pad handlers reached (`hits`: pc -> count) and lets a test watch PCs."""

    WATCH = {0x0804D0BC: "note_prob_pad", 0x0804D112: "note_prob_ret", 0x0804D104: "note_prob_write",
             0x0804F262: "drum_prob_pad", 0x0804F31C: "drum_prob_ret", 0x0804F30C: "drum_prob_set",
             0x0804ED50: "exp_pad", 0x0804ED68: "exp_release", 0x0804759A: "noop_release",
             0x080435B0: "cont_press", 0x080435F0: "cont_release", 0x080332CE: "ctrl_release",
             0x08043930: "cont_release_half", 0x0804D116: "note_prob_leds", 0x0804F322: "drum_prob_leds"}

    def __init__(self, image: bytes = STOCK):
        super().__init__(image)
        self.sinks: list[tuple] = []
        self.hits: list[tuple] = []
        uc = self.uc

        def sink(u, a, s, d):
            r = [u.reg_read(UC_ARM_REG_R0 + i) for i in range(4)]
            self.sinks.append(("on" if a == SINK_ON else "off", r[0], r[1], r[2]))
        uc.hook_add(UC_HOOK_CODE, sink, begin=SINK_ON, end=SINK_ON)
        uc.hook_add(UC_HOOK_CODE, sink, begin=SINK_OFF, end=SINK_OFF)

        def watch(u, a, s, d):
            self.hits.append((self.WATCH[a], u.reg_read(UC_ARM_REG_R0), u.reg_read(UC_ARM_REG_R1),
                              u.reg_read(UC_ARM_REG_R2)))
        for a in self.WATCH:
            uc.hook_add(UC_HOOK_CODE, watch, begin=a, end=a)

    # state
    def ret(self) -> int:
        return self.uc.reg_read(UC_ARM_REG_R0)

    def mode(self) -> int:
        return self.r8(CONT + 0x18C)

    def track_of(self) -> int:
        self.call(TRACK_OF, CONT)
        return self.ret() & 0xFF

    def view_for(self, pad: int) -> int:
        self.call(VIEW_OF, CONT, pad)
        return self.ret()

    def bottom_class(self) -> int:
        v = self.view_for(16)
        return self.r32(v) if v else 0

    def ids(self) -> dict:
        return dict(active=hex(self.r32(MGR + 0x6C)), mode=self.mode(), track=self.track_of(),
                    sub152=self.r8(MGR + 0x152), bottom=hex(self.view_for(16)), bottom_class=hex(self.bottom_class()),
                    top_class=hex(self.r32(self.view_for(0))))

    def p0(self, store: int) -> int:
        return param(self, store, 0)

    def transport(self) -> tuple:
        return tuple(param(self, PLAY_STORE, i) for i in range(3))

    def ram(self) -> bytes:
        return bytes(self.uc.mem_read(RAM0, RAM1 - RAM0))

    def take_all(self):
        out = (list(self.sinks), list(self.hits), self.take())
        self.sinks.clear()
        self.hits.clear()
        return out

    # routes
    def shift(self, on: bool) -> None:
        self.set_p0(self.r32(MGR + 0xC), 1 if on else 0)

    def open_prob(self, t: int, shift_route: bool = True) -> None:
        """Track t, then its probability view: Shift + Pattern Settings (or Pattern Settings twice)."""
        self.press(t)
        if shift_route:
            self.press(BTN_PSET, shift=True)
        else:
            self.press(BTN_PSET)
            self.press(BTN_PSET)
        want = PROB_NOTE if t < 4 else PROB_DRUM
        assert self.mode() == MODE_PROB and self.bottom_class() == want, self.ids()

    def open_expanded(self, d: int) -> None:
        """Drum d (0-3), then Note again: the expanded view (mode 6)."""
        self.press(4 + d)
        for _ in range(3):
            if self.mode() == MODE_EXPANDED:
                break
            self.press(BTN_NOTE)
        assert self.mode() == MODE_EXPANDED and self.r32(self.view_for(28)) == EXPANDED, self.ids()

    def play(self, ms: int = 30) -> None:
        self.press(BTN_PLAY)
        self.heartbeat(ms)
        assert self.transport()[0] == 1


def diff(a: bytes, b: bytes, ignore=()) -> list[tuple[int, str, str]]:
    """Changed byte runs (address, old hex, new hex), runs merged when closer than 4 B; addresses in `ignore` ranges
    ((lo, hi) inclusive-exclusive) dropped."""
    out, i, n = [], 0, len(a)
    while i < n:
        if a[i] != b[i]:
            j = i
            while j < n and (a[j] != b[j] or any(a[k] != b[k] for k in range(j, min(n, j + 4)))):
                j += 1
            addr = RAM0 + i
            if not any(lo <= addr < hi for lo, hi in ignore):
                out.append((addr, a[i:j].hex(), b[i:j].hex()))
            i = j
        else:
            i += 1
    return out


def fmt_diff(d) -> str:
    return "none" if not d else "; ".join(f"{a:#010x}: {o} -> {n}" for a, o, n in d[:12]) + (" ..." if len(d) > 12 else "")


def hexrow(xs) -> str:
    return " ".join(f"{x:02x}" for x in xs)
