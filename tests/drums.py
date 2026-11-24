"""Drum helpers for the note-repeat tests (PL16), from the drums spike's lib2.py
(docs/investigations/2026-10-25-drums-spike/): the expanded drum view's live sink and what goes through it, the
drum recorders and their patterns, the transport through the real buttons, the record quantise byte and setting."""
from __future__ import annotations

import struct

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0

from notes import PARAM_COMMIT, PARAM_GET, PARAM_WPTR, PLAY_STORE, NoteHarness, param, set_tempo

CONT = 0x20040DB8                  # track container: [+ 0xAC] the expanded drum view, [+ 0x18C] the views' mode
SINK_ON, SINK_OFF = 0x0801D38E, 0x0801D942    # note_sink_on (sink, note, vel, pad) / note_sink_off (sink, note, pad)
SEQ_TICK = 0x0802C418              # hook seq_tick's site: one sequencer tick
RECORDERS = 0x2003C174             # [RECORDERS + 4 (4 + d)]: drum d's recorder; its quantise byte at + 0x35
ENGINE = 0x20038EC0                # [ENGINE + 0x30 + 4 track]: the track's store, p0 bits 0-2 = its playing pattern;
                                   # [ENGINE + 0x9C]: the chain store, param track = byte 0 first pattern, byte 1 last
SETTINGS = 0x200111CC              # the settings store: param 2 bit 12 set = record quantise off
ROUTER = 0x2003ECDC                # [ROUTER + 0x94] = SETTINGS; its param 2 bit 1 = fixed velocity (live drums at 96)
EDITOR_LOAD, EDITOR_VT = 0x0803F050, 0x0805C108
PAT = 0x6A8                        # a drum pattern: vel[32], prob[32], flip[32], micro[32], last / first step
STORE_ARRAYS = (0x00, 0x20, 0x60, 0x40)   # the step store's parameter k // 8 -> the pattern's array (vel, prob, micro, flip)
PLAY, RECORD, NOTE_BTN = 17, 16, 9
DRUM_PAD = 28                      # the Repeat page's pads 28-31 (0-based) = drums 1-4, as the expanded view's
MODE_DRUM, MODE_EXPANDED = 1, 6
BPM = 240


def sym(m, name):
    return int(m["symbols"][name], 16)


class DrumHarness(NoteHarness):
    """A NoteHarness that counts heartbeats (`ms`) and sequencer ticks (`ticks`) and logs every call on the expanded
    drum view's sink: `sent` = (ms, arp_tick, "on" / "off", note, velocity or None). The UI routes (pads, buttons,
    LEDs) and the heartbeat are tagged so a test can tell which task sent a hit (`sent_by`)."""

    def __init__(self, image: bytes, manifest: dict):
        super().__init__(image)
        self.m = manifest
        self.ms = 0
        self.ticks = 0
        self.task = "ui"
        self.sent: list[tuple] = []
        self.sent_by: list[str] = []
        self.arp_tick_at = sym(manifest, "arp_tick")
        uc = self.uc

        def tick(u, a, s, d):
            self.ticks += 1
        uc.hook_add(UC_HOOK_CODE, tick, begin=SEQ_TICK, end=SEQ_TICK)

        def sink(u, a, s, d):
            r = [u.reg_read(UC_ARM_REG_R0 + i) for i in range(4)]
            if r[0] != self.expanded_sink():
                return
            on = a == SINK_ON
            self.sent.append((self.ms, self.r32(self.arp_tick_at), "on" if on else "off", r[1], r[2] if on else None))
            self.sent_by.append(self.task)
        uc.hook_add(UC_HOOK_CODE, sink, begin=SINK_ON, end=SINK_ON)
        uc.hook_add(UC_HOOK_CODE, sink, begin=SINK_OFF, end=SINK_OFF)

    def heartbeat(self, n: int = 1) -> None:
        self.task = "main"
        for _ in range(n):
            super().heartbeat(1)
            self.ms += 1
        self.task = "ui"

    def arp_tick(self) -> int:
        return self.r32(self.arp_tick_at)

    def until_tick(self, t: int, cap: int = 100_000) -> None:
        """Heartbeats until arp_tick reaches t (the heartbeat that counted it has run)."""
        for _ in range(cap):
            if self.arp_tick() >= t:
                return
            self.heartbeat(1)
        raise AssertionError(f"arp_tick never reached {t}")

    # the sink
    def expanded_view(self) -> int:
        return self.r32(CONT + 0xAC)

    def expanded_sink(self) -> int:
        return self.r32(self.expanded_view() + 0x10)

    def ons(self, note: int | None = None) -> list[tuple]:
        return [e for e in self.sent if e[2] == "on" and (note is None or e[3] == note)]

    # the drum recorders and patterns
    def recorder(self, d: int) -> int:
        return self.r32(RECORDERS + 4 * (4 + d))

    def quantise_byte(self, d: int) -> int:
        return self.r8(self.recorder(d) + 0x35)

    def quantise_off_setting(self) -> int:
        """Bit 12 of parameter 2 of the settings store: 1 = stock's record quantise off (Shift + Record)."""
        self.call(PARAM_GET, SETTINGS, 2)
        return self.r32(self.uc.reg_read(UC_ARM_REG_R0)) >> 12 & 1

    def base(self, d: int) -> int:
        return self.r32(self.recorder(d) + 0x48)

    def shown_pattern(self, d: int) -> int:
        """The pattern drum d's editor shows (its step pads act on it): p0 of the position store [recorder + 0x14]."""
        return param(self, self.r32(self.recorder(d) + 0x14), 0) & 7

    def store_bytes(self, d: int) -> bytes:
        """Drum d's step store (the editor's editing copy) as its read view, 128 B in the pattern's layout: parameter k =
        steps 4 (k % 8) .. + 3 of array k // 8 (velocity, probability, micro, flip), as the spike's drumlib.Drum."""
        store, out = self.r32(self.recorder(d) + 0x4C), bytearray(0x80)
        for k in range(32):
            self.call(PARAM_GET, store, k)
            o = STORE_ARRAYS[k // 8] + 4 * (k % 8)
            out[o:o + 4] = bytes(self.uc.mem_read(self.uc.reg_read(UC_ARM_REG_R0), 4))
        return bytes(out)

    def editor(self, d: int) -> int:
        return self.r32(0x200438DC + 0x3C * d + 0xC) - 0x18

    def playing_pattern(self, d: int) -> int:
        return param(self, self.r32(ENGINE + 0x30 + 4 * (4 + d)), 0) & 7

    def chain(self, d: int) -> tuple[int, int]:
        """Drum d's pattern chain: (first, last)."""
        self.call(PARAM_GET, self.r32(ENGINE + 0x9C), 4 + d)
        a = self.uc.reg_read(UC_ARM_REG_R0)
        return self.r8(a), self.r8(a + 1)

    def set_chain(self, d: int, first: int, last: int) -> None:
        st = self.r32(ENGINE + 0x9C)
        self.call(PARAM_GET, st, 4 + d)
        v = self.r32(self.uc.reg_read(UC_ARM_REG_R0))
        self.call(PARAM_WPTR, st, 4 + d)
        self.uc.mem_write(self.uc.reg_read(UC_ARM_REG_R0), struct.pack("<I", (v & ~0xFFFF) | first | last << 8))
        self.call(PARAM_COMMIT, st)

    def arrays(self, d: int, p: int) -> dict:
        raw = bytes(self.uc.mem_read(self.base(d) + PAT * p, 0x84))
        return dict(vel=raw[0:32], prob=raw[0x20:0x40], flip=raw[0x40:0x60], micro=raw[0x60:0x80])

    def pattern_hits(self, d: int, p: int) -> dict[int, tuple[int, int]]:
        """step -> (velocity, microstep mask) of every step with a hit."""
        a = self.arrays(d, p)
        return {s: (a["vel"][s], a["micro"][s]) for s in range(32) if a["vel"][s] or a["micro"][s]}

    def clear_pattern(self, d: int, p: int, last: int = 31) -> None:
        """Raw: empty steps (vel 0, prob 7, flip FF, micro 0), steps 0..last; then stock's editor load brings the step
        store in line, as a pattern change would."""
        b = self.base(d) + PAT * p
        self.uc.mem_write(b, bytes(32) + bytes([7] * 32) + bytes([0xFF] * 32) + bytes(32))
        self.uc.mem_write(b + 0x80, bytes([last, 0]))
        ed = self.editor(d)
        assert self.r32(ed) == EDITOR_VT, hex(self.r32(ed))
        self.call(EDITOR_LOAD, ed)

    # the transport and settings
    def transport(self) -> tuple[int, int, int]:
        """Play store: playing, Record armed, count-in."""
        return tuple(param(self, PLAY_STORE, i) for i in range(3))

    def fixed_velocity(self, on: bool) -> None:
        st = self.r32(ROUTER + 0x94)
        self.call(PARAM_GET, st, 2)
        v = self.r32(self.uc.reg_read(UC_ARM_REG_R0))
        self.call(PARAM_WPTR, st, 2)
        self.uc.mem_write(self.uc.reg_read(UC_ARM_REG_R0), struct.pack("<I", (v & ~2) | (2 if on else 0)))
        self.call(PARAM_COMMIT, st)


def drum_setup(h: DrumHarness, quantise_off: bool = True, record: bool = True) -> int:
    """slim ready, every drum's playing pattern emptied (32 steps) and made its whole chain (the snapshot chains every
    drum through patterns 0-7: at tick 192 a drum would move on to pattern 1), 240 BPM, fixed velocity off, stock's
    record quantise off (Shift + Record) unless asked, no swing, Record armed (the real button) unless asked, drum 1's
    page open (Shift + Drum 1): the Repeat page. Returns drum 1's playing pattern."""
    h.leds()
    h.press(4)
    set_tempo(h, bpm=BPM, swing=50)
    for d in range(4):
        p = h.playing_pattern(d)
        h.clear_pattern(d, p)
        h.set_chain(d, p, p)
        assert h.chain(d) == (p, p)
    h.fixed_velocity(False)
    if quantise_off:
        h.press(RECORD, shift=True)
        assert h.quantise_off_setting() == 1
    if record:
        h.press(RECORD)
    h.press(4, shift=True)
    return h.playing_pattern(0)


def recorded(sent: list[tuple], note: int) -> dict[int, tuple[int, int]]:
    """What stock records with quantise off from the note-ons sent, the sequencer started at arp_tick 0 (16th steps,
    32 of them): step -> (the step's last velocity, microstep mask of the ticks it was hit on)."""
    out: dict[int, tuple[int, int]] = {}
    for ms, tick, kind, n, vel in sent:
        if kind == "on" and n == note:
            s = tick // 6 % 32
            out[s] = (vel, out.get(s, (0, 0))[1] | 1 << tick % 6)
    return out
