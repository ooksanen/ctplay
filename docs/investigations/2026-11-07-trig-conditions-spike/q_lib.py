"""Shared helpers for the PL20 Task 1 spike (2026-11-07; throwaway, stock image). Run from slim/ with
PYTHONPATH=.:tests:../tools:docs/investigations/2026-11-01-trig-conditions-spike:docs/investigations/2026-11-07-trig-conditions-spike
../.venv/bin/python docs/investigations/2026-11-07-trig-conditions-spike/<script>.py

Builds on the 2026-11-01 builder check's a_lib.H (routes, pattern accessors). Adds: the calling context of every
emulated call ("ui" = a controller button / pad call, "main" = the 1 ms service, "direct:<fn>" = a function the script
calls itself), entry logs (registers and the first stack words at a PC), Python "handlers" at a PC (to simulate a slim
hook's effect before stock goes on), and a crude backtrace (return addresses found on the stack)."""
from __future__ import annotations

import struct

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP)

from a_lib import *  # noqa: F401,F403  (H, BTN, DPAT, NPAT, NSTEP, routes and accessors)
from a_lib import H as AH
from harness import BTN_PRESS, BTN_RELEASE, MGR, MS_SERVICE, PAD_PRESS, PAD_RELEASE

CTRL_FNS = {BTN_PRESS: "ui", BTN_RELEASE: "ui", PAD_PRESS: "ui", PAD_RELEASE: "ui", MS_SERVICE: "main"}
DISPATCH = 0x0802DBC0                    # stock's pattern-command dispatcher; ip = r0 - 4 (0x0802DBC0)
DRUM_EDITOR_SLOT = 0xA8                  # [ip + 0x98 + 4 t]: track t's editor; drums at + 0xA8 + 4 d
RECORDERS = 0x2003C174                   # [RECORDERS + 4 t]: track t's recorder (mono.c)
CODE_LO, CODE_HI = 0x08010000, 0x08080000


def regs(u, n=13):
    return [u.reg_read(UC_ARM_REG_R0 + i) for i in range(n)]


class Q(AH):
    """a_lib.H plus contexts, entry logs, Python handlers at a PC, backtraces."""

    def __init__(self, image: bytes = STOCK, watch: bool = False):
        self.ctx = "setup"
        self.depth = 0
        super().__init__(image, watch)
        self.elog: list[dict] = []
        self.named: dict[int, str] = {}

    # every emulated call gets a context; nested calls (none here) keep the outer one
    def call(self, fn, *args, **kw):
        outer = self.ctx
        if self.depth == 0:
            self.ctx = CTRL_FNS.get(fn, f"direct:{fn:#010x}")
        self.depth += 1
        try:
            return super().call(fn, *args, **kw)
        finally:
            self.depth -= 1
            if self.depth == 0:
                self.ctx = outer if outer != "setup" else "setup"

    def r32s(self, a, n):
        return list(struct.unpack(f"<{n}I", bytes(self.uc.mem_read(a, 4 * n))))

    def backtrace(self, depth=48):
        """Return addresses on the stack (odd words in the code range whose previous instruction is a bl / blx)."""
        u = self.uc
        sp = u.reg_read(UC_ARM_REG_SP)
        out = [u.reg_read(UC_ARM_REG_LR)]
        try:
            words = self.r32s(sp, depth)
        except Exception:  # noqa: BLE001  (the stack top: fewer words mapped)
            words = []
            for k in range(depth):
                try:
                    words.append(self.r32(sp + 4 * k))
                except Exception:  # noqa: BLE001
                    break
        for w in words:
            if w & 1 and CODE_LO <= w < CODE_HI:
                out.append(w)
        return [f"{a & ~1:#010x}" for a in out]

    def log_at(self, addr, name, extra=None, nstack=4):
        """Log ctx, registers r0-r12 and nstack stack words at addr; extra(h, regs) adds fields."""
        self.named[addr] = name

        def f(u, a, s, d):
            r = regs(u)
            sp = u.reg_read(UC_ARM_REG_SP)
            e = dict(ctx=self.ctx, name=name, phase=self.phase, r=r, sp=sp, stack=self.r32s(sp, nstack),
                     lr=u.reg_read(UC_ARM_REG_LR))
            if extra:
                e.update(extra(self, r, sp))
            self.elog.append(e)
        self.uc.hook_add(UC_HOOK_CODE, f, begin=addr, end=addr)

    def handler_at(self, addr, fn):
        """Run fn(h, regs, sp) when stock reaches addr (before the instruction there), as a slim hook would."""
        def f(u, a, s, d):
            fn(self, regs(u), u.reg_read(UC_ARM_REG_SP))
        self.uc.hook_add(UC_HOOK_CODE, f, begin=addr, end=addr)

    def entries(self, *names):
        return [e for e in self.elog if not names or e["name"] in names]

    # objects
    def dispatcher_ip(self):
        """ip of the command dispatcher: found from the editors' table, [ip + 0xA8 + 4 d] = drum d's editor."""
        return self._ip

    def drum_of_editor(self, ed):
        for d in range(4):
            if self.deditor(d) == ed:
                return d
        return None

    def note_of_editor(self, ed):
        for t in range(4):
            if self.neditor(t) == ed:
                return t
        return None

    def drum_of_pattern(self, addr):
        """(drum, pattern, offset) of an address inside the drum patterns, else None."""
        for d in range(4):
            b = self.dbase(d)
            if b <= addr < b + 8 * DPAT:
                return d, (addr - b) // DPAT, (addr - b) % DPAT
        return None

    def note_of_pattern(self, addr):
        from notes import PATTERN_BASE
        for t in range(4):
            b = PATTERN_BASE[t]
            if b <= addr < b + 8 * NPAT:
                o = (addr - b) % NPAT
                return t, (addr - b) // NPAT, o // NSTEP, o % NSTEP
        return None

    # Python-only readers (safe inside a Unicorn hook: a_lib's dshown / nshown emulate stock's getter)
    def dshown_py(self, d):
        return self.store_p(self.r32(self.drec(d) + 0x14), 0, 1)[0] & 7

    def dselected_py(self, d):
        return self.store_p(self.r32(self.drec(d) + 0x14), 1, 1)[0]

    def nshown_py(self, t):
        return self.store_p(self.r32(self.neditor(t) + 0x24), 0, 1)[0] & 7

    def nselected_py(self, t):
        return self.store_p(self.r32(self.neditor(t) + 0x24), 1, 1)[0]

    def store_p(self, st, i, n=4):
        from b_lib import store_bytes
        return store_bytes(self, st, i, n)


def code_of(h, d, p, s):
    """The 9-bit code CTPlay will store (Global Constraints): +0x88 + s bits 0-7, bit s & 7 of +0x84 + (s >> 3)."""
    pat = h.dpattern(d, p)
    return pat[0x88 + s] | (pat[0x84 + (s >> 3)] >> (s & 7) & 1) << 8


def hexs(b):
    return b.hex(" ")
