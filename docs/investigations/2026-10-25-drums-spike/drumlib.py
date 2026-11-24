"""Shared helpers for the drum spike (throwaway). Run from slim/ with PYTHONPATH=.:tests:../tools."""
import struct, sys
from pathlib import Path
from unicorn.arm_const import UC_ARM_REG_R0
sys.path[:0] = [str(Path(__file__).resolve().parents[3]), str(Path(__file__).resolve().parents[3] / 'tests'),
                str(Path(__file__).resolve().parents[4] / 'tools')]
from notes import NoteHarness, CONT
from harness import MGR

STOCK = (Path(__file__).resolve().parents[4] / 'stock' / 'circuittracks-firmware-4486-STOCK.bin').read_bytes()
ENGINE = 0x20038EC0
PARAM_GET, PARAM_WPTR, COMMIT, SET_LISTENER, TOUCH_ALL = 0x0803542C, 0x080354FA, 0x080353C0, 0x08035398, 0x08035456
TRACK_OF = 0x0805011E
BTN_NOTE, BTN_VEL, BTN_GATE, BTN_PSET, BTN_PATTERNS = 9, 10, 11, 12, 13
VT = {0x0805AD0C: 'drum step', 0x0805ABBC: 'drum sample/Preset', 0x0805AD44: 'drum expanded', 0x0805AD7C: 'drum velocity',
      0x0805AAA4: 'drum gate/micro', 0x0805AB4C: 'drum pattern settings', 0x0805AB14: 'drum probability',
      0x0805AC2C: 'sidechain', 0x0805A064: 'note Note view', 0x0805ADB4: 'note step', 0x0805ADEC: 'note velocity',
      0x0805AB84: 'note gate/micro', 0x0805ACD4: 'note probability', 0x0805AC9C: 'synth Preset', 0x0805AE5C: 'MIDI tmpl',
      0x0805A62C: 'container', 0x0805A668: 'Mixer'}
OFFS = {0: 0x00, 1: 0x20, 2: 0x60, 3: 0x40}   # param k // 8 -> raw array offset (vel, prob, micro, flip)


def harness():
    return NoteHarness(STOCK)


def pget(h, store, i):
    h.call(PARAM_GET, store, i)
    return h.r8(h.uc.reg_read(UC_ARM_REG_R0))


def ret(h):
    return h.uc.reg_read(UC_ARM_REG_R0)


def track_of(h):
    h.call(TRACK_OF, CONT)
    return ret(h) & 0xFF


def mode(h):
    return h.r8(CONT + 0x18C)


def vname(a):
    return VT.get(a, hex(a))


def views(h):
    """(class of the top-half view, class of the bottom-half view) through stock's own lookups."""
    t, m = track_of(h), mode(h)
    h.call(0x08043B6E, CONT, 0); top = ret(h)
    h.call(0x08043B6E, CONT, 16); bot = ret(h)
    return vname(h.r32(top)) if top else None, vname(h.r32(bot)) if bot else None


def state(h):
    act = h.r32(MGR + 0x6C)
    return dict(mode=mode(h), track=track_of(h), active=vname(h.r32(act)), halves=views(h))


class Drum:
    def __init__(self, h, d):
        self.h, self.d = h, d
        rec = h.r32(0x2003D71C + 0x14)
        self.base = rec + 0xCD74 + 0x3540 * d
        self.drec = h.r32(0x2003C174 + 4 * (4 + d))
        assert h.r32(self.drec) == 0x0805A578, hex(h.r32(self.drec))
        assert h.r32(self.drec + 0x48) == self.base
        self.store = h.r32(self.drec + 0x4C)
        self.pos = h.r32(self.drec + 0x14)
        self.editor = h.r32(h.r32(self.store + 0x14))          # listener 0
        assert h.r32(self.editor) == 0x0805C108, hex(h.r32(self.editor))
        assert h.r32(self.editor + 0x18) == self.store and h.r32(self.editor + 0x20) == self.pos
        self.play = h.r32(ENGINE + 0x30 + 4 * (4 + d))

    def playing(self):
        return pget(self.h, self.play, 0) & 7

    def mirrored(self):
        return pget(self.h, self.pos, 0)

    def flag24(self):
        return pget(self.h, self.h.r32(self.editor + 0x24), 0)

    def flag5c(self):
        return pget(self.h, self.h.r32(self.editor + 0x5C), 0)

    def pat(self, p):
        return self.base + 0x6A8 * p

    def arrays(self, p):
        return bytes(self.h.uc.mem_read(self.pat(p), 0x80))

    def is_mirrored(self, p):
        return self.h.r32(self.store + 0x18) == self.pat(p) + 0xA8

    def store_bytes(self):
        """The store's read view as 128 B in the pattern's layout."""
        out = bytearray(0x80)
        for k in range(32):
            self.h.call(PARAM_GET, self.store, k)
            w = self.h.r32(ret(self.h))
            o = OFFS[k // 8] + 4 * (k % 8)
            out[o:o + 4] = w.to_bytes(4, 'little')
        return bytes(out)

    def write(self, p, img, sync=True, detach=True):
        """CTPlay-style write of 128 B `img` (pattern layout) into pattern p."""
        h = self.h
        h.uc.mem_write(self.pat(p), img)
        if not sync or not self.is_mirrored(p):
            return 'raw'
        b0, b1 = h.r32(self.store + 0xC), h.r32(self.store + 0x10)
        for k in range(32):
            o = OFFS[k // 8] + 4 * (k % 8)
            for b in (b0, b1):
                h.uc.mem_write(b + 4 * k, img[o:o + 4])
        h.call(TOUCH_ALL, self.store)
        if detach:
            h.call(SET_LISTENER, self.store, self.editor, 0)
        h.call(COMMIT, self.store)
        if detach:
            h.call(SET_LISTENER, self.store, self.editor, 0xFFFFFFFF)
        return 'store'


def euclid_img(hits, vel=100, micro=1, prob=7, flip=0xFF):
    v, pr, fl, mi = bytearray(32), bytearray([7] * 32), bytearray([0xFF] * 32), bytearray(32)
    for s in hits:
        v[s], pr[s], fl[s], mi[s] = vel, prob, flip, micro
    return bytes(v + pr + fl + mi)


def hits_of(arr):
    return [s for s in range(32) if arr[s] and arr[0x60 + s]]


def fmt(arr):
    return ' '.join(f'{n}:{arr[o:o+32].hex()}' for n, o in (('vel', 0), ('prob', 0x20), ('flip', 0x40), ('micro', 0x60)))
