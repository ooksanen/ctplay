"""Q1 (drums): the arguments of drum_duplicate 0x0803E2AA, drum_clear_step 0x0803E18A, drum_clear_pattern 0x0803E3B0,
drum_copy_half 0x0803E93A and drum_paste_step 0x0803DFAE, each reached through its real route (A-storage.md), and
how an entry handler finds the drum, the pattern (address) and the step(s). For Duplicate and paste a simulated entry
handler (Python, at the function's first instruction) copies the condition bytes as Task 8 would, then stock runs; the
result is checked against the source. Every step of drum 1's patterns has a distinct code (a_lib.dtag)."""
from q_lib import *

SRC_HITS = {0: (100, 1, 7, 0xFF), 3: (90, 3, 5, 2), 6: (80, 0x21, 7, 0xFF), 12: (70, 1, 2, 0xFF), 20: (65, 1, 7, 0xFF)}
DST_HITS = {1: (60, 1, 7, 0xFF), 9: (50, 1, 7, 0xFF), 17: (45, 1, 7, 0xFF)}
FN = {0x0803E2AA: "drum_duplicate", 0x0803E18A: "drum_clear_step", 0x0803E3B0: "drum_clear_pattern",
      0x0803E93A: "drum_copy_half", 0x0803DFAE: "drum_paste_step", 0x0803DF72: "drum_copy_step(source)"}


def editor_fields(h, r, sp):
    """What an entry handler can read from r0 (the drum editor): its drum, [r0 + 4] patterns, [r0 + 0x20] p0 / p1,
    [r0 + 0x10] p0 (transport), [r0 + 0x54] -> the copy-step record."""
    ed = r[0]
    d = h.drum_of_editor(ed)
    st20 = h.r32(ed + 0x20)
    clip = h.r32(ed + 0x54)
    return dict(drum=d, base_ok=(d is not None and h.r32(ed + 4) == h.dbase(d)),
                p0_20=h.store_p(st20, 0, 1)[0], p1_20=h.store_p(st20, 1, 1)[0],
                playing=h.store_p(h.r32(ed + 0x10), 0, 1)[0], clip=bytes(h.uc.mem_read(clip, 4)), clip_addr=clip)


def fresh(chains=None, both=False):
    h = Q()
    h.leds()
    set_tempo(h, bpm=240)
    for t, c in (chains or {}).items():
        h.set_chain(t, c, c)
    for d in range(4 if both else 1):
        for p in range(8):
            h.set_dcond(d, p, dtag(d, p))
    h.set_dhits(0, 0, SRC_HITS, load=False)
    h.set_dhits(0, 1, DST_HITS, load=False)
    for d in range(4):
        h.dload(d)
    for a, n in FN.items():
        h.log_at(a, n, editor_fields)
    # the dispatcher's editor table
    h.log_at(DISPATCH, "dispatch")
    return h


def show_entry(e, extra=""):
    r = e["r"]
    print(f"   {e['name']} [{e['ctx']}] r0={r[0]:#x} (drum {e['drum']}, [r0+4]=patterns {e['base_ok']}) r1={r[1]:#x} "
          f"r2={r[2]:#x} r3={r[3]:#x} stack={[hex(x) for x in e['stack'][:2]]}; [r0+0x20] p0={e['p0_20']} "
          f"p1={e['p1_20']}; [r0+0x10] p0 (playing)={e['playing']}; [[r0+0x54]]={hexs(e['clip'])}{extra}")


def check_table(h):
    e = h.entries("dispatch")
    if not e:
        return
    ip = e[0]["r"][0] - 4
    ok_d = all(h.r32(ip + 0xA8 + 4 * d) == h.deditor(d) for d in range(4))
    ok_n = all(h.r32(ip + 0x98 + 4 * t) == h.neditor(t) for t in range(4))
    clip = [h.r32(h.deditor(d) + 0x54) for d in range(4)]
    print(f"[editor table] dispatcher ip={ip:#x}: [ip+0xA8+4d] = drum d's editor {ok_d}; [ip+0x98+4t] = note editor t "
          f"{ok_n}; drum editors' [+0x54] = {[hex(c) for c in clip]} (ip+0x30 = {ip + 0x30:#x})")


# ---- Duplicate ------------------------------------------------------------------------------------------------
def dup_handler(h, r, sp):
    """Task 8's entry handler: copy the source's 36 bytes (r1 + 0x84) to the target ([r0 + 4] + 0x6A8 r2 + 0x84)."""
    src = r[1]
    dst = h.r32(r[0] + 4) + DPAT * r[2]
    h.dup_seen.append((src, dst))
    h.uc.mem_write(dst + 0x84, bytes(h.uc.mem_read(src + 0x84, 0x24)))


def dup_case(label, stopped, chains, src, dst, sim=True):
    """src / dst = (track, pattern)."""
    h = fresh(chains, both=True)
    h.dup_seen = []
    if sim:
        h.handler_at(0x0803E2AA, dup_handler)
    if not stopped:
        h.play(True)
        h.heartbeat(30)
    sd, dd = src[0] - 4, dst[0] - 4
    before = dict(shown_src=h.dshown(sd), shown_dst=h.dshown(dd), playing_dst=h.track_playing(dst[0]))
    src_img = h.dpattern(sd, src[1])
    h.elog.clear()
    h.patterns_view()
    h.hold(BTN["dup"])
    h.pad(h.pv_pad(*src))
    h.pad(h.pv_pad(*dst))
    h.let_go(BTN["dup"])
    if not stopped:
        h.heartbeat(5)
    tgt = h.dpattern(dd, dst[1])
    print(f"[Duplicate {label}] {'stopped' if stopped else 'playing'}, before {before}")
    for e in h.entries("drum_duplicate"):
        sp_ = h.drum_of_pattern(e["r"][1])
        show_entry(e, f"; r1 = drum {sp_[0]} pattern {sp_[1]} + {sp_[2]:#x}; r2 = target pattern index {e['r'][2]}")
    print(f"   handler saw (src, dst) {[(hex(a), h.drum_of_pattern(a), hex(b), h.drum_of_pattern(b)) for a, b in h.dup_seen]}")
    print(f"   target: arrays = source {tgt[:0x84] == src_img[:0x84]}; lanes = source {tgt[0xA8:] == src_img[0xA8:]}; "
          f"+0x84..+0xA7 = source's {tgt[0x84:0xA8] == src_img[0x84:0xA8]} "
          f"(target's own {tgt[0x84:0xA8] == dtag(dd, dst[1])}); source unchanged {h.dpattern(sd, src[1]) == src_img}")
    others = [(d, p) for d in range(4) for p in range(8) if (d, p) != (dd, dst[1]) and h.dcond(d, p) != dtag(d, p)]
    print(f"   other patterns' condition bytes changed: {others or 'none'}")


# ---- Clear step / pattern, copy half, paste ------------------------------------------------------------------
def changed_steps(before, after):
    return [s for s in range(32) if before[s] != after[s] or before[0x20 + s] != after[0x20 + s]
            or before[0x40 + s] != after[0x40 + s] or before[0x60 + s] != after[0x60 + s]]


def clear_step_case(label, page2=False, playing=False, pad=3):
    h = fresh({4: 0} if playing else None)
    step_view(h, 4)
    if page2:
        h.press(BTN["half"])
    if playing:
        h.play(True)
        h.heartbeat(30)
    b = h.dpattern(0, h.dshown(0))
    p_before = h.dshown(0)
    h.elog.clear()
    h.hold(BTN["clear"])
    h.pad(pad)
    h.let_go(BTN["clear"])
    a = h.dpattern(0, p_before)
    print(f"[Clear step: {label}] pad {pad}; shown {p_before}, selected now {h.dselected(0)}")
    for e in h.entries("drum_clear_step"):
        show_entry(e)
    print(f"   steps whose arrays changed in pattern {p_before}: {changed_steps(b, a)}")


def clear_pattern_case(label, chains, track, pat, stopped=True):
    h = fresh(chains, both=True)
    d = track - 4
    if not stopped:
        h.play(True)
        h.heartbeat(30)
    shown = h.dshown(d)
    hits = {p: [s for s in range(32) if h.dpattern(d, p)[s]] for p in range(8)}
    h.elog.clear()
    h.clear_pattern_pv(track, pat)
    print(f"[Clear pattern: {label}] {'stopped' if stopped else 'playing'}, drum {d} pattern {pat}, shown {shown}")
    for e in h.entries("drum_clear_pattern"):
        tgt = h.r32(e["r"][0] + 4) + DPAT * e["r"][1]
        show_entry(e, f"; [r0+4] + 0x6A8 r1 = drum {h.drum_of_pattern(tgt)[:2]}")
    after = {p: [s for s in range(32) if h.dpattern(d, p)[s]] for p in range(8)}
    print(f"   patterns whose hits changed: {[p for p in range(8) if after[p] != hits[p]]}")


def copy_half_case(label, page2):
    h = fresh()
    step_view(h, 4)
    if page2:
        h.press(BTN["half"])
    b = h.dpattern(0, h.dshown(0))
    h.elog.clear()
    h.hold(BTN["dup"])
    h.press(BTN["half"])
    h.let_go(BTN["dup"])
    a = h.dpattern(0, h.dshown(0))
    print(f"[copy half: {label}] shown {h.dshown(0)}")
    for e in h.entries("drum_copy_half"):
        show_entry(e)
    ch = changed_steps(b, a)
    print(f"   steps changed: {ch}; 16-31 = 0-15 of before: "
          f"{all(a[16 + s] == b[s] and a[0x20 + 16 + s] == b[0x20 + s] for s in range(16))}; "
          f"0-15 unchanged {all(a[s] == b[s] for s in range(16))}")


def paste_handler(h, r, sp):
    """Task 8's entry handler for paste: source from the copy-step record [[r0 + 0x54]] (track, pattern, step),
    target = [r0 + 0x20] p0 / p1."""
    ed = r[0]
    clip = bytes(h.uc.mem_read(h.r32(ed + 0x54), 4))
    sd, sp_, ss = clip[1] - 4, clip[2], clip[3]
    st = h.r32(ed + 0x20)
    tp, ts = h.store_p(st, 0, 1)[0], h.store_p(st, 1, 1)[0]
    td = h.drum_of_editor(ed)
    stack_src = h.r32(sp + 4) - 0xA8                      # the caller's [sp + 4]: source pattern + 0xA8
    h.paste_seen.append(dict(src=(sd, sp_, ss), dst=(td, tp, ts), stack_src=h.drum_of_pattern(stack_src),
                             vel_arg=r[1], src_vel=h.dpattern(sd, sp_)[ss]))
    code = code_of(h, sd, sp_, ss)
    base = h.dpat(td, tp)
    h.uc.mem_write(base + 0x88 + ts, bytes([code & 0xFF]))
    bb = h.r8(base + 0x84 + (ts >> 3))
    bb = (bb & ~(1 << (ts & 7))) | ((code >> 8) << (ts & 7))
    h.uc.mem_write(base + 0x84 + (ts >> 3), bytes([bb]))


def paste_case(label, a, b, page_between=False, drum_between=None, page2=False):
    h = fresh(both=True)
    h.paste_seen = []
    h.handler_at(0x0803DFAE, paste_handler)
    step_view(h, 4)
    if page2:
        h.press(BTN["half"])
    before = {d: [code_of(h, d, p, s) for p in range(8) for s in range(32)] for d in range(4)}
    h.elog.clear()
    h.hold(BTN["dup"])
    h.pad(a)
    if page_between:
        h.press(BTN["half"])
    if drum_between is not None:
        h.press(4 + drum_between)
    h.pad(b)
    h.let_go(BTN["dup"])
    print(f"[paste step: {label}] pads {a} then {b}")
    for e in h.entries("drum_copy_step(source)", "drum_paste_step"):
        show_entry(e)
    for s in h.paste_seen:
        print(f"   handler: source {s['src']} (stack [sp+4]-0xA8 = {s['stack_src']}), target {s['dst']}; r1 (vel) "
              f"{s['vel_arg']} = source's velocity {s['src_vel']}")
        sd, sp_, ss = s["src"]
        td, tp, ts = s["dst"]
        print(f"   target code now = source's code: {code_of(h, td, tp, ts) == before[sd][32 * sp_ + ss]}; target "
              f"velocity = source's {h.dpattern(td, tp)[ts] == h.dpattern(sd, sp_)[ss]}")
    if not h.paste_seen:
        print("   no paste")


if __name__ == "__main__":
    h = fresh()
    h.clear_pattern_pv(4, 3)
    check_table(h)

    print("\n== drum_duplicate (Patterns view, Duplicate + source pad + target pad)")
    dup_case("A: drum 1 P1 -> P2, shown P1", True, None, (4, 0), (4, 1))
    dup_case("B: drum 1 P1 -> P2, chain P3", True, {4: 2}, (4, 0), (4, 1))
    dup_case("C: source shown (playing P1)", False, {4: 0}, (4, 0), (4, 1))
    dup_case("D: target shown (playing P2)", False, {4: 1}, (4, 0), (4, 1))
    dup_case("E: neither shown (playing P3)", False, {4: 2}, (4, 0), (4, 1))
    dup_case("F: drum 1 P1 -> drum 2 P2", True, None, (4, 0), (5, 1))
    dup_case("G: drum 1 P1 -> drum 2 P2 (drum 2 playing P3)", False, {5: 2}, (4, 0), (5, 1))
    dup_case("H: drum 1 P1 -> drum 2 P2 (drum 2 playing P2: target shown)", False, {5: 1}, (4, 0), (5, 1))
    dup_case("I: a pattern onto itself (P1 -> P1)", True, None, (4, 0), (4, 0))

    print("\n== drum_clear_step (step view, Clear held + step pad)")
    clear_step_case("1-16 shown, stopped", pad=3)
    clear_step_case("17-32 shown, stopped", page2=True, pad=4)
    clear_step_case("1-16, playing (follow)", playing=True, pad=6)

    print("\n== drum_clear_pattern (Patterns view, Clear held + pattern pad)")
    clear_pattern_case("shown, stopped", None, 4, 0)
    clear_pattern_case("not shown, playing P3", {4: 2}, 4, 1, stopped=False)
    clear_pattern_case("shown = playing", {4: 1}, 4, 1, stopped=False)
    clear_pattern_case("drum 2's column", None, 5, 2)

    print("\n== drum_copy_half (step view, Duplicate held + 1-16/17-32)")
    copy_half_case("1-16 shown", False)
    copy_half_case("17-32 shown", True)

    print("\n== drum_paste_step (step view, Duplicate held + step A, step B)")
    paste_case("same page, 4 -> 8", 3, 7)
    paste_case("17-32 page, 21 -> 26", 4, 9, page2=True)
    paste_case("page switched between: 4 (1-16) -> 26 (17-32)", 3, 9, page_between=True)
    paste_case("drum switched between: drum 1 step 4 -> drum 2 step 8", 3, 7, drum_between=1)
    paste_case("an empty step onto a hit: 3 -> 1", 2, 0)
