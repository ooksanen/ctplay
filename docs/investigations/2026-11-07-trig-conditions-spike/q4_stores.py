"""Q4: the step a row-3 press edits in each accept case, read the way Task 6's row-4 handler will read it at its entry
(notes: the edit store [[view + 0xC] + 8], word 0, and the editor's position store [editor + 0x24] p0 / p1, editor =
[view + 0xC] - 0x18; drums: pattern = [[RECORDERS + 4 (4 + d)] + 0x14] p0, step = [[view + 0xC] + 8] p1); stock's
row-3 write path (param_wptr on parameter 0, commit) used for bytes 2-3; the selected step moving between a row-4
press and its release; and the first write's clear-all through each note track's edit store.

Row 4 is pressed first (the handler's reading is logged at the view's pad handler, pad 8-15), then row 3 in the same
state (which step stock edits, from the pattern diff). Synth 2 (track 1, notes on steps 1-16 in the snapshot) and
Drum 1 (track 4); step 6 selected beforehand, step 3 held where said (C-controls.md's cases)."""
from q_lib import *
from b_lib import store_bufs, store_bytes
from notes import PATTERN_BASE

FOLLOW = 0x20039DE0
BTN_PATTERNS = 13
ENGINE = 0x20038EC0
SEL_PAD, HELD_PAD, ROW3_PAD, ROW4_PAD = 5, 2, 19, 26
NOTE_PROB, DRUM_PROB = 0x0804D0BC, 0x0804F262


class P(Q):
    """Q plus the row-4 entry readers; c_lib's open_prob / play(ms) routes."""

    def __init__(self):
        super().__init__()
        self.reads = []

        def note_entry(u, a, s, d):
            r = regs(u)
            if r[1] < 8:
                return
            view = r[0]
            x = self.r32(view + 0xC)
            ed = x - 0x18
            t = next((k for k in range(4) if self.r32(0x20042890 + 0x3C * k + 0xC) - 0x18 == ed), None)
            st8 = self.r32(x + 8)
            pos = self.r32(ed + 0x24)
            p, s_ = store_bytes(self, pos, 0, 1)[0] & 7, store_bytes(self, pos, 1, 1)[0]
            w0 = store_bytes(self, st8, 0, 4)
            self.reads.append(dict(kind="note", track=t, x_is_ed18=(st8 == self.r32(ed + 0x20)), pattern=p, step=s_,
                                   store_w0=w0, pat_w0=bytes(self.uc.mem_read(PATTERN_BASE[t] + 0xCA8 * p + 28 * s_, 4)),
                                   held=store_bytes(self, self.r32(x + 0x10), 0, 1)[0]))
        self.uc.hook_add(UC_HOOK_CODE, note_entry, begin=NOTE_PROB, end=NOTE_PROB)

        def drum_entry(u, a, s, d):
            r = regs(u)
            if r[1] < 8:
                return
            view = r[0]
            y = self.r32(view + 0xC)
            d_ = next((k for k in range(4) if self.r32(0x200438DC + 0x3C * k + 0xC) - 0x18 + 0x18 == y), None)
            rec = self.r32(RECORDERS + 4 * (4 + d_))
            p = store_bytes(self, self.r32(rec + 0x14), 0, 1)[0] & 7
            s_ = store_bytes(self, self.r32(y + 8), 1, 1)[0]
            p8 = store_bytes(self, self.r32(y + 8), 0, 1)[0] & 7
            self.reads.append(dict(kind="drum", drum=d_, pattern=p, step=s_, p0_of_y8=p8,
                                   held=store_bytes(self, self.r32(y + 0xC), 0, 1)[0]))
        self.uc.hook_add(UC_HOOK_CODE, drum_entry, begin=DRUM_PROB, end=DRUM_PROB)

    def open_prob(self, t):
        prob_view(self, t)

    def play(self, ms=30):
        self.press(17)
        self.heartbeat(ms)


def prob_bytes(h, t):
    p = param(h, h.r32(ENGINE + 0x30 + 4 * t), 0) & 7
    if t < 4:
        return p, [h.r8(PATTERN_BASE[t] + 0xCA8 * p + 28 * s + 1) for s in range(32)]
    base = h.r32(h.r32(RECORDERS + 4 * t) + 0x48) + 0x6A8 * p
    return p, list(h.uc.mem_read(base + 0x20, 32))


def case(t, playing, follow, held):
    h = P()
    h.press(t)
    if follow:
        h.press(BTN_PATTERNS, shift=True)
    h.open_prob(t)
    h.pad(SEL_PAD)
    if playing:
        h.play(37)
    if held:
        h.down(HELD_PAD)
    h.reads.clear()
    h.down(ROW4_PAD)
    h.up(ROW4_PAD)
    rd = h.reads[-1]
    p, before = prob_bytes(h, t)
    h.down(ROW3_PAD)
    h.up(ROW3_PAD)
    _, after = prob_bytes(h, t)
    changed = [s for s in range(32) if before[s] != after[s]]
    if held:
        h.up(HELD_PAD)
    return rd, p, changed


def write23(h, t, b2, b3):
    """Stock's row-3 path for bytes 2-3: param_wptr(edit store, 0), write, commit."""
    st = h.r32(h.neditor(t) + 0x20)
    h.call(PARAM_WPTR, st, 0)
    a = h.uc.reg_read(UC_ARM_REG_R0)
    h.uc.mem_write(a + 2, bytes([b2, b3]))
    h.call(PARAM_COMMIT, st)


def note_pos(h, t):
    return h.nshown(t), h.nselected(t)


def ram(h):
    return bytes(h.uc.mem_read(0x20000000, 0x50000))


def runs(a, b, base=0x20000000):
    out, i, n = [], 0, len(a)
    while i < n:
        if a[i] != b[i]:
            j = i
            while j < n and a[j] != b[j]:
                j += 1
            out.append((base + i, j - i))
            i = j
        else:
            i += 1
    return out


def classify(h, addr, n):
    w = h.note_of_pattern(addr)
    if w:
        return f"note track {w[0]} pattern {w[1]} step {w[2]} byte {w[3]}"
    for t in range(4):
        st = h.r32(h.neditor(t) + 0x20)
        for k, b in enumerate(store_bufs(h, st)):
            if b <= addr < b + 28:
                return f"track {t} edit store buffer {k} + {addr - b}"
        if st <= addr < st + 0xC:
            return f"track {t} edit store header + {addr - st}"
    return f"{addr:#x}"


if __name__ == "__main__":
    print("== the step a row-3 press edits, and the handler's reading at a row-4 press in the same state")
    for t in (1, 4):
        for playing, follow, held in ((0, 0, 0), (0, 0, 1), (1, 0, 1), (1, 1, 0), (1, 0, 0)):
            rd, p, changed = case(t, playing, follow, held)
            kind = "notes" if t < 4 else "drums"
            extra = (f"store word 0 {hexs(rd['store_w0'])} = pattern step's word 0 {rd['store_w0'] == rd['pat_w0']}; "
                     f"[[view+0xC]+8] = [editor + 0x20] {rd['x_is_ed18']}") if t < 4 else \
                    f"[[view+0xC]+8] p0 = {rd['p0_of_y8']}"
            print(f"  {kind} playing {playing} follow-off(p0=1) {follow} held {held}: handler reads pattern {rd['pattern']} "
                  f"step {rd['step']} (held flag {rd['held']}); row 3 edited pattern {p} steps {changed} -> "
                  f"{'MATCH' if changed == [rd['step']] else ('refused by stock' if not changed else 'DIFFER')}; {extra}")

    print("\n== bytes 2-3 through the store (param_wptr p0 + commit), Synth 2, each accept case")
    for playing, follow, held in ((0, 0, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1)):
        h = P()
        h.press(1)
        if follow:
            h.press(BTN_PATTERNS, shift=True)
        h.open_prob(1)
        h.pad(SEL_PAD)
        if playing:
            h.play(37)
        if held:
            h.down(HELD_PAD)
        p, s = note_pos(h, 1)
        r0 = ram(h)
        write23(h, 1, 0xA5, 0x01)
        r1 = ram(h)
        ch = [classify(h, a, n) for a, n in runs(r0, r1)]
        pat_changes = [c for c in ch if c.startswith("note track")]
        print(f"  playing {playing} follow-off {follow} held {held}: selected (pattern {p}, step {s}); pattern bytes changed: "
              f"{pat_changes}; step now {hexs(h.nstep(1, p, s)[:4])}")
        if held:
            h.up(HELD_PAD)

    print("\n== the selected step moving between a row-4 press and its release (Synth 2, playing, follow on = p0 0)")
    h = P()
    h.open_prob(1)
    h.play(37)
    h.down(HELD_PAD)
    h.reads.clear()
    h.down(ROW4_PAD)
    latched = (h.reads[-1]["pattern"], h.reads[-1]["step"])
    h.up(HELD_PAD)
    h.heartbeat(150)
    now = note_pos(h, 1)
    print(f"  latched at the press (step 3 held): {latched}; at the release 150 ms later (step pad let go first): "
          f"selected {now}: a write through the store would land on step {now[1]}, not {latched[1]}")
    h.up(ROW4_PAD)

    print("\n== the first write's clear-all: bytes 2-3 of each note track's edit store word 0 -> 0, commit")
    for label, prep in (("stopped, synced stores", None), ("playing", "play"), ("stopped, a stale store (pattern edited raw)", "stale")):
        h = P()
        h.open_prob(1)
        # junk in every note step's [2]/[3] and in each store's word 0
        for t in range(4):
            for p in range(8):
                base = PATTERN_BASE[t] + 0xCA8 * p
                for s in range(32):
                    h.uc.mem_write(base + 28 * s + 2, bytes([0x80 | s, 0xFE]))
            write23(h, t, 0x77, 0x66)
        if prep == "play":
            h.play(37)
        stale = None
        if prep == "stale":
            t = 2
            p, s = note_pos(h, t)
            a = PATTERN_BASE[t] + 0xCA8 * p + 28 * s
            h.uc.mem_write(a + 4, bytes([0x3C, 6, 0, 99]))          # unit 0 changed raw (as a CTPlay raw writer would)
            h.uc.mem_write(a, bytes([h.r8(a) | 1]))
            stale = (t, p, s, bytes(h.uc.mem_read(a, 28)))
        # the raw zeroing of every pattern's [2]/[3] (Task 6's first step), then the stores
        for t in range(4):
            for p in range(8):
                base = PATTERN_BASE[t] + 0xCA8 * p
                for s in range(32):
                    h.uc.mem_write(base + 28 * s + 2, b"\0\0")
        r0 = ram(h)
        for t in range(4):
            write23(h, t, 0, 0)
        r1 = ram(h)
        ch = [classify(h, a, n) for a, n in runs(r0, r1)]
        pat = [c for c in ch if c.startswith("note track")]
        other = [c for c in ch if not c.startswith("note track") and "edit store" not in c]
        print(f"  {label}: pattern bytes changed by the 4 commits: {pat or 'none'}; outside patterns and the stores: "
              f"{other[:10] or 'none'}{' ...' if len(other) > 10 else ''}")
        print(f"     stores' word 0 bytes 2-3 now: {[hexs(store_bytes(h, h.r32(h.neditor(t) + 0x20), 0, 4)[2:]) for t in range(4)]}")
        if stale:
            t, p, s, img = stale
            now = bytes(h.uc.mem_read(PATTERN_BASE[t] + 0xCA8 * p + 28 * s, 28))
            print(f"     the stale step (track {t} pattern {p} step {s}): raw edit kept {now[4:8] == img[4:8]} "
                  f"(unit 0 {hexs(img[4:8])} -> {hexs(now[4:8])}; [0] {img[0]:#x} -> {now[0]:#x})")
