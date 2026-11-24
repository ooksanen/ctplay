"""Q1: Duplicate of pattern 1 -> pattern 2 (0-based 0 -> 1) through the Patterns view (Duplicate held + source pad +
target pad), drum 1 and Synth 1, stopped and playing, with pattern 1 / pattern 2 / neither the track's shown pattern.
Reads the target's condition bytes: copied from the source, the target's own kept, or zeroed."""
from a_lib import *

SRC_HITS = {0: (100, 1, 7, 0xFF), 3: (90, 3, 5, 2), 6: (80, 0x21, 7, 0xFF), 12: (70, 1, 2, 0xFF)}
DST_HITS = {1: (60, 1, 7, 0xFF), 9: (50, 1, 7, 0xFF)}


def verdict(got, src, dst):
    if got == src:
        return "COPIED (= source)"
    if got == dst:
        return "NOT COPIED (target's own bytes kept)"
    if got == bytes(len(got)):
        return "ZEROED"
    return "JUNK/partial: " + hexs(got)


def drum_case(stopped, chain, label):
    h = H()
    h.leds()
    set_tempo(h, bpm=240)
    d, t = 0, 4
    if chain is not None:
        h.set_chain(t, chain, chain)
    for p in range(8):
        h.set_dcond(d, p, dtag(d, p))
    h.set_dhits(d, 0, SRC_HITS, load=False)
    h.set_dhits(d, 1, DST_HITS, load=False)
    h.dload(d)
    if not stopped:
        h.play(True)
        h.heartbeat(30)
    before = dict(playing=h.track_playing(t), shown=h.dshown(d))
    src_img = h.dpattern(d, 0)
    h.calls.clear()
    h.duplicate(t, 0, 1)
    if not stopped:
        h.heartbeat(5)
    after = dict(playing=h.track_playing(t), shown=h.dshown(d))
    tgt = h.dpattern(d, 1)
    paste = [c for c in h.fcalls("drum Duplicate paste")]
    print(f"[drum {label}] {'stopped' if stopped else 'playing'} before {before} after {after}")
    print(f"   paste calls: {[(c[1], hex(c[2][1]), c[2][2]) for c in paste]}")
    print(f"   arrays 0..0x83 copied: {tgt[:0x84] == src_img[:0x84]}; lanes 0xA8.. copied: {tgt[0xA8:] == src_img[0xA8:]}")
    print(f"   +0x84..+0xA7: {verdict(tgt[0x84:0xA8], dtag(d, 0), dtag(d, 1))}")
    print(f"   source unchanged: {h.dpattern(d, 0) == src_img}; other patterns' bytes kept: "
          f"{all(h.dcond(d, p) == dtag(d, p) for p in range(2, 8))}")
    return tgt[0x84:0xA8] == dtag(d, 0)


def note_case(stopped, chain, label):
    h = H()
    h.leds()
    set_tempo(h, bpm=240)
    t = 0
    if chain is not None:
        h.set_chain(t, chain, chain)
    for p in range(8):
        h.set_nb23(t, p, ntag(t, p))
    from notes import fill
    for s in (0, 4, 8):
        fill(h, t, 0, s, [60 + s])
    fill(h, t, 1, 2, [50])
    h.set_nb23(t, 0, ntag(t, 0))       # fill() writes [2] / [3] = 0; put the tags back
    h.set_nb23(t, 1, ntag(t, 1))
    if h.nshown(t) in (0, 1):
        h.sync_nstore(t)
    if not stopped:
        h.play(True)
        h.heartbeat(30)
    before = dict(playing=h.track_playing(t), shown=h.nshown(t), sel=h.nselected(t))
    src_img = bytes(h.uc.mem_read(h.npat(t, 0), NPAT))
    h.calls.clear()
    h.duplicate(t, 0, 1)
    if not stopped:
        h.heartbeat(5)
    after = dict(playing=h.track_playing(t), shown=h.nshown(t), sel=h.nselected(t))
    tgt = bytes(h.uc.mem_read(h.npat(t, 1), NPAT))
    print(f"[Synth 1 {label}] {'stopped' if stopped else 'playing'} before {before} after {after}")
    print(f"   paste calls: {[(c[1], hex(c[2][1]), c[2][2]) for c in h.fcalls('note Duplicate paste')]}")
    print(f"   whole pattern copied: {tgt == src_img}")
    print(f"   steps [2]/[3]: {verdict(h.nb23(t, 1), ntag(t, 0), ntag(t, 1))}; store word 0 {hexs(h.nstore_word0(t))}"
          f" = shown step {hexs(h.nstep(t, h.nshown(t), h.nselected(t))[:4])}")
    return h.nb23(t, 1) == ntag(t, 0)


if __name__ == "__main__":
    print("== drums (drum 1, track 4)")
    drum_case(True, None, "A: snapshot's shown pattern")
    drum_case(True, 2, "B: chain 3 (pattern 3 shown before)")
    drum_case(False, 0, "C: chain 1 (source shown, playing)")
    drum_case(False, 1, "D: chain 2 (target shown, playing)")
    drum_case(False, 2, "E: chain 3 (neither shown)")
    print("== note tracks (Synth 1)")
    note_case(True, None, "A: snapshot's shown pattern")
    note_case(True, 2, "B: chain 3")
    note_case(False, 0, "C: chain 1 (source shown)")
    note_case(False, 1, "D: chain 2 (target shown)")
    note_case(False, 2, "E: chain 3 (neither shown)")

    print("== across tracks (Patterns view: source pad in one column, target pad in another)")
    for stopped in (True, False):
        h = H(); h.leds(); set_tempo(h, bpm=240)
        h.set_chain(5, 2, 2)                     # drum 2 plays / shows pattern 3 when playing
        for d in range(4):
            for p in range(8):
                h.set_dcond(d, p, dtag(d, p))
        h.set_dhits(0, 0, SRC_HITS)
        for d in range(4):
            h.dload(d)
        if not stopped:
            h.play(True); h.heartbeat(30)
        shown = h.dshown(1)
        h.patterns_view(); h.hold(BTN["dup"]); h.pad(h.pv_pad(4, 0)); h.pad(h.pv_pad(5, 1)); h.let_go(BTN["dup"])
        tgt = h.dpattern(1, 1)
        print(f"[drum 1 P1 -> drum 2 P2, {'stopped' if stopped else 'playing'}; drum 2 showed {shown}, now {h.dshown(1)}] "
              f"paste {[(c[1], hex(c[2][0])) for c in h.fcalls('drum Duplicate paste')]}; arrays copied "
              f"{tgt[:0x80] == h.dpattern(0, 0)[:0x80]}; +0x84..: {verdict(tgt[0x84:0xA8], dtag(0, 0), dtag(1, 1))}")
    h = H(); h.leds()
    for t in range(2):
        for p in range(8):
            h.set_nb23(t, p, ntag(t, p))
    h.patterns_view(); h.hold(BTN["dup"]); h.pad(h.pv_pad(0, 0)); h.pad(h.pv_pad(1, 1)); h.let_go(BTN["dup"])
    print(f"[Synth 1 P1 -> Synth 2 P2, stopped] paste {[c[1] for c in h.fcalls('note Duplicate paste')]}; "
          f"[2]/[3]: {verdict(h.nb23(1, 1), ntag(0, 0), ntag(1, 1))}")
