"""Pad layout mockups (a rough guide, 2026-10-25): after PL17 (with the stock views PL20 adds to), and where PL18+ candidates could go. Run with the repo's .venv: writes two HTML files beside this script."""
from pathlib import Path
import html

C = dict(G="#37c84a", B="#3a8cff", M="#e04ad8", O="#ff9a1f", Y="#f2e33a", C="#2fd6d6", W="#f2f2f2",
         V="#9a5cff", R="#ff4040", S="#6b6b6b", D1="#ff9a1f", D2="#f2e33a", D3="#9a5cff", D4="#2fd6d6",   # drums 1-4: stock's expanded-view colours (PL16, measured)
         GT="#c87070")   # the drum roll pad: stock's Gate view 1/6 colour (0x68, one hit, the default; 0x66 / 0x63 for 2 / 3 hits), lightened to read

def page(name, sub, rows, notes, fut=()):
    """rows: list of 32 (label, colour key or None for dark/free, kind) entries built by P()."""
    return dict(name=name, sub=sub, pads=rows, notes=notes)

def P(spec):
    pads = [("", None, "free")] * 32
    for rng, labels, col, *kind in spec:
        a, b = rng
        for i, n in enumerate(range(a, b + 1)):
            lab = labels[i] if isinstance(labels, list) else labels
            pads[n - 1] = (lab, col, kind[0] if kind else "on")
    return pads

ACT = [((29, 29), "Dice R", "W"), ((30, 30), "Dice N", "W"), ((31, 31), "Undo", "B"), ((32, 32), "Write", "O")]
ACT_DRUM = [((29, 29), "Dice R", "W"), ((30, 30), "", None, "dark"), ((31, 31), "Undo", "B"), ((32, 32), "Write", "O")]
HITS = [((1, 16), [str(k) for k in range(1, 17)], "O")]
HITS2 = [((1, 16), [str(k) for k in range(1, 17)], "W")]
ROT = [((17, 19), ["◀", "▶", "⟲"], "W")]

chords = P([((1, 8), ["off", "triad", "7th", "9th", "sus2", "sus4", "add9", "6th"], "G"),
            ((9, 13), ["power", "shell7", "4ths", "7sus4", "6/9"], "G"),
            ((17, 20), ["inv0", "inv1", "inv2", "inv3"], "B"), ((21, 23), ["close", "drop2", "wide"], "M"),
            ((24, 24), "bass", "O"), ((25, 27), ["lead C", "lead T", "lead B"], "B"),
            ((28, 30), ["slow", "med", "fast"], "W"), ((31, 32), ["rise", "fall"], "W")])
arp = P([((1, 8), ["off", "up", "down", "u-d", "d-u", "rand", "played", "chord"], "G"),
         ((9, 12), ["1/4", "1/8", "1/16", "1/32"], "B"), ((13, 14), ["trip", "dot"], "M"), ((16, 16), "latch", "O"),
         ((17, 20), ["oct1", "oct2", "oct3", "oct4"], "M"), ((21, 21), "gate", "W")])
pt = P(HITS + ROT + [((20, 20), "src", "W"), ((21, 21), "gate", "W"), ((22, 24), ["soft", "med", "hard"], "M"),
                     ((25, 28), ["cyc3", "cyc5", "cyc6", "cyc7"], "C")] + ACT)
pt2 = P(HITS2 + ROT + [((20, 24), ["both", "either", "xor", "1not2", "accent"], "V"),
                       ((25, 27), ["thin¼", "thin⅓", "thin½"], "C")] + ACT)
melody = P([((1, 8), ["same", "up", "down", "u-d", "climb", "walk", "rand", "bass"], "Y"),
            ((9, 10), ["chord", "scale"], "G"), ((11, 13), ["1 oct", "2 oct", "3 oct"], "M"), ((14, 14), "accent", "Y"),
            ((17, 17), "last", "W"), ((18, 24), ["deg1", "deg2", "deg3", "deg4", "deg5", "deg6", "deg7"], "B"),
            ((25, 28), ["−2", "−1", "0", "+1"], "M")] + ACT)
phrasing = P([((1, 3), ["tie¼", "tie⅓", "tie½"], "C"), ((5, 7), ["jmp¼", "jmp⅓", "jmp½"], "M")] + ACT)
keys = P([((1, 1), "mono", "M"), ((2, 2), "stepchd", "G"), ((3, 4), ["played", "written"], "W")])   # PL18: one toggle per setting; PL19: pattern strum
quick = P([((1, 16), "stock", "S", "stock"),
           ((17, 24), ["off", "triad", "7th", "9th", "sus2", "sus4", "add9", "6th"], "G"),
           ((25, 29), ["power", "shell7", "4ths", "7sus4", "6/9"], "G"), ((30, 32), "", None, "dark")])
toc_n = P([((1, 24), "", None, "dark"), ((25, 25), "Chords", "G"), ((26, 26), "Arp", "B"), ((27, 27), "Ptools", "O"),
           ((28, 28), "Melody", "Y"), ((29, 31), "", None, "dark"), ((32, 32), "Keys", "M")])

DRUMS = [((29, 29), "Drum1", "D1"), ((30, 30), "Drum2", "D2"), ((31, 31), "Drum3", "D3"), ((32, 32), "Drum4", "D4")]
repeat = P([((1, 4), ["1/4", "1/8", "1/16", "1/32"], "B"), ((5, 8), ["1/4T", "1/8T", "1/16T", "1/32T"], "M"),
            ((9, 12), ["struck", "fade", "swell", "accent"], "W"), ((15, 15), "unquant", "C"), ((16, 16), "latch", "O")]
           + DRUMS)
dpt = P(HITS + ROT + [((20, 20), "src", "W"), ((21, 21), "roll", "GT"), ((22, 24), ["soft", "med", "hard"], "M"),
                      ((25, 28), ["cyc3", "cyc5", "cyc6", "cyc7"], "C")] + ACT_DRUM)
dpt2 = P(HITS2 + ROT + [((20, 24), ["both", "either", "xor", "1not2", "accent"], "V"),
                        ((25, 27), ["thin¼", "thin⅓", "thin½"], "C"), ((28, 28), "accent", "Y")] + ACT_DRUM)
toc_d = P([((1, 24), "", None, "dark"), ((25, 25), "Repeat", "B"), ((26, 26), "", None, "dark"),
           ((27, 27), "Ptools", "O"), ((28, 32), "", None, "dark")])

# PL20: trig conditions in stock's views (spec 2026-10-28-trig-conditions-design.md)
PROB_STOCK = [((1, 16), "steps", "S", "stock"), ((17, 24), "prob", "S", "stock")]
prob = P(PROB_STOCK + [((25, 32), ["pass1", "pass2", "pass3", "pass4", "pass5", "pass6", "pass7", "pass8"], "C")])
prob_s = P(PROB_STOCK + [((25, 26), ["FIRST", "!FIRST"], "G"), ((27, 28), ["FILL", "!FILL"], "O"),
                         ((29, 30), ["PRE", "!PRE"], "V"), ((31, 32), ["LAST", "!LAST"], "Y")])
wide = P([((1, 20), "", None, "dark"), ((21, 24), ["FILL1", "FILL2", "FILL3", "FILL4"], "O"),
          ((25, 28), "", None, "dark")] + DRUMS)

AFTER = [
    ("Synth and MIDI tracks (Shift + Synth 1 / 2, MIDI 1 / 2)", [
        page("Chords", "pad 25 · green · quick half = rows 1–2", chords,
             "Rows 1–2 shapes (one choice) · row 3 inversion, spread, bass · row 4 voice leading close / top / bottom, strum speed, direction. 14–16 free."),
        page("Arp", "pad 26 · blue · quick half = rows 1–2", arp,
             "Pattern · rate, triplet / dotted, latch · octaves, gate. 15, 22–32 free."),
        page("Pattern tools", "pad 27 · orange", pt,
             "Hits + preview · rotate, rhythm source, gate, velocity · cycle · dice, Undo, Write."),
        page("Pattern tools 2", "pad 27 again", pt2,
             "Second rhythm + its preview · rotate, combine · thinning · actions. 28 free."),
        page("Melody", "pad 28 · yellow", melody, "Order · pool, range, accent · root · octave · actions. 15–16 free."),
        page("Phrasing", "pad 28 again", phrasing, "Ties, octave jumps · 9–28 free (reserved: transforms, contours) · actions."),
        page("Keys", "pad 32 · magenta (setup)", keys, "One toggle per setting, lit = on: mono record (magenta), chords in step entry (green); pattern strum played · written (white, PL19; none lit = off). 5–32 free. Built in PL18 (PL08–PL17: poly · mono on pads 1–2)."),
        page("Quick view", "Shift held in the Note view", quick, "Pads 1–16 stay stock's. 17–29 = all 13 shapes."),
        page("Table of contents", "Shift held on any page", toc_n, "One pad per feature; tap to open. 29–31 dark."),
    ]),
    ("Drum tracks (Shift + Drum 1–4) — PL16 + PL17", [
        page("Repeat (PL16)", "pad 25 · blue · one setting for the whole kit", repeat,
             "Rates 1/4–1/32 · triplets (one rate across 1–8, again = off) · velocity shape · unquantized repeats, latch · rows 3–4: free, drums 1–4 on 29–32 in stock's expanded-view colours (white while sounding, pulsing white while latched)."),
        page("Pattern tools (PL17)", "pad 27 · orange", dpt,
             "As the note tracks' page: pad 21 = roll (1 · 2 · 3 hits per step, in stock's Gate view colours 1/6 · 3/6 · 6/6) instead of gate; dice notes dark. Built in PL17."),
        page("Pattern tools 2 (PL17)", "pad 27 again", dpt2,
             "As the note tracks' page, plus accent cycle on 28 (off · first hit · on the beat · every 3rd, Melody's accent colours). Built in PL17."),
        page("Table of contents", "Shift held on a drum page", toc_d, "26 is held for Levels; 28–32 dark."),
    ]),
    ("Stock views with CTPlay pads (PL20: trig conditions)", [
        page("Probability view", "Shift + Pattern Settings · any track · row 4 = the pass grid", prob,
             "Rows 1–3 stay stock's (steps, the selected step's probability). Row 4: passes 1–8 of the step row 3 shows. Hold ½ s = a cycle of that many passes, pass 1 ticked; tap = tick / untick a pass (bright = ticked, dim = in the cycle, dark = past it). Written on the release."),
        page("Probability view, Shift held", "the special conditions", prob_s,
             "FIRST / NOT FIRST, FILL / NOT FILL (drums only: dark on a note track), PRE / NOT PRE, LAST / NOT LAST. Bright = the step's, dim = the others; the lit one again clears. Plain row 4 with a special: all 8 dim in its colour."),
        page("Drum expanded view", "Drum N, then Note · no drum page open", wide,
             "21–24 = FILL for drums 1–4 (dim off, bright on, yellow armed): hold = on, tap = the drum's next whole pass. 29–32 play the drums (stock). 17–20 and 25 kept for a note-track and an every-track FILL."),
    ]),
]

# ---- PL18+ candidates: changed pads marked future ----
def fut(pads, spec):
    pads = list(pads)
    for rng, labels, col in spec:
        a, b = rng
        for i, n in enumerate(range(a, b + 1)):
            lab = labels[i] if isinstance(labels, list) else labels
            pads[n - 1] = (lab, col, "future")
    return pads

chords_f = fut(chords, [((14, 16), ["maj", "min", "dom"], "G")])
chords2_f = fut(P([]), [((1, 8), ["off", "S1", "S2", "M1", "M2", "drums", "all", "hold"], "G"),
                        ((9, 12), ["root", "3rd", "5th", "7th"], "B"),
                        ((17, 28), ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"], "W"),
                        ((31, 31), "clear", "B"), ((32, 32), "save", "O")])
vary_f = fut(P([]), [((1, 3), ["vel¼", "vel⅓", "vel½"], "M"), ((5, 7), ["time¼", "time⅓", "time½"], "C"),
                     ((9, 11), ["rat2", "rat3", "rat6"], "W"), ((13, 15), ["mut¼", "mut⅓", "mut½"], "Y"),
                     ((29, 29), "Dice", "W"), ((31, 31), "Undo", "B"), ((32, 32), "Write", "O")])
phrasing_f = fut(phrasing, [((9, 11), ["shuf", "rev", "mirror"], "V"), ((17, 22), ["rise", "fall", "arch", "valley", "zig", "flat"], "Y")])
keys_f = fut(keys, [((9, 11), ["scale", "4ths", "chr4"], "B")])
project_f = fut(P([]), [((1, 13), ["−6", "−5", "−4", "−3", "−2", "−1", "0", "+1", "+2", "+3", "+4", "+5", "+6"], "B"),
                        ((17, 17), "MIDIlock", "G"), ((18, 18), "split", "M"),
                        ((25, 25), "keep", "W"), ((26, 26), "reset", "R"), ((29, 32), ["chd", "arp", "eucl", "mel"], "S")])
wide_f = fut(wide, [((17, 20), ["S1", "S2", "M1", "M2"], "O"), ((25, 25), "all", "O")])
toc_nf = fut(toc_n, [((29, 29), "Vary", "M")])
repeat_f = fut(repeat, [((17, 24), ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"], "W")])
levels_f = fut(P(DRUMS), [((1, 16), [str(k) for k in range(1, 17)], "Y"), ((17, 19), ["vel", "pitch", "decay"], "B")])
dpt_f = fut(dpt, [((30, 30), "avoid", "R")])
toc_df = fut(toc_d, [((26, 26), "Levels", "Y"), ((29, 29), "Vary", "M")])

LATER = [
    ("Synth and MIDI tracks — candidates (★ = new; everything else as after PL17)", [
        page("Chords", "pad 25 · semitone shapes on 14–16, if a spike gets past the scale snap", chords_f,
             "Major / minor / dominant on any degree (Orchid-style). Only if the router's scale snapping can be passed."),
        page("Chords 2", "pad 25 again · harmonizer + custom chord (sketch)", chords2_f,
             "Row 1: which tracks follow the chord (harmonizer). Row 2: what they follow. Rows 3–4: build your own chord from 12 semitones; clear on 31, save on 32 (the Undo / Write places)."),
        page("Vary", "new main page, pad 29 · both track kinds (sketch)", vary_f,
             "Humanize velocity / timing (small changes around each step), ratchets (notes), mutate in key. Draft, Undo, Write as Pattern tools."),
        page("Phrasing", "pad 28 again · reserved rows filled (sketch)", phrasing_f,
             "Transforms (shuffle pitches, reverse, mirror) on row 2; contour shapes on row 3."),
        page("Keys", "pad 32 · fourths layouts", keys_f,
             "Row 2: pad layout scale (stock) · in-key fourths · chromatic fourths. Pads 1–4 as built in PL18 / PL19."),
        page("Project", "Shift + Mixer · one page (sketch)", project_f,
             "Live transpose · scale lock on MIDI in, split keyboard · keep / reset CTPlay settings (two presses) · build info (one pad per feature)."),
        page("Table of contents", "notes", toc_nf, "Vary takes 29."),
    ]),
    ("Drum tracks — candidates", [
        page("Repeat", "row 3: fixed velocity levels (sketch)", repeat_f,
             "Eight fixed velocities for repeat, MPC-style: hold a level and the repeats play at it."),
        page("Levels", "pad 26 · yellow · 16 levels (sketch)", levels_f,
             "One drum over pads 1–16 by velocity, pitch or decay; pick the drum on 29–32."),
        page("Pattern tools", "pad 30: avoid (interlock)", dpt_f,
             "Avoid cycle: off · drum 1 · 2 · 3 · 4: the hits skip steps where that drum hits (hats avoid the kick)."),
        page("Table of contents", "drums", toc_df, "Levels on 26, Vary on 29 (shared with note tracks)."),
        page("Drum expanded view", "FILL for the note tracks (planned in PL20's spec)", wide_f,
             "17–20: FILL for Synth 1 / 2, MIDI 1 / 2 (the track buttons' order); 25: every track at once. Built in PL20: 21–24 for the drums."),
    ]),
]

# ---- The beta layout pass (2026-11-10, layouts/beta-layout-pass.md): one slot = one kind of page on every track ----
toc_nb = fut(toc_n, [((29, 29), "Vary", "M")])
toc_db = fut(P([((1, 24), "", None, "dark"), ((27, 27), "Ptools", "O"), ((28, 28), "", None, "dark"),
                ((30, 31), "", None, "dark")]),
             [((25, 25), "Levels", "Y"), ((26, 26), "Repeat", "B"), ((29, 29), "Vary", "M"), ((32, 32), "Setup", "M")])
vary_b = fut(P([]), [((1, 3), ["vel¼", "vel⅓", "vel½"], "M"), ((5, 7), ["time¼", "time⅓", "time½"], "C"),
                     ((9, 11), ["rat2", "rat3", "rat6"], "W"), ((13, 15), ["mut¼", "mut⅓", "mut½"], "Y"),
                     ((17, 20), ["quant", "rev", "nudge◀", "nudge▶"], "B"),
                     ((29, 29), "Dice", "W"), ((31, 31), "Undo", "B"), ((32, 32), "Write", "O")])
keys_b = fut(keys, [((5, 5), "strumrel", "W"), ((6, 6), "MIDIlock", "G"), ((7, 8), ["MIDIchd", "MIDIstep"], "C"),
                    ((9, 12), ["scale", "4ths", "chr4", "Janko"], "B")])
project_b = fut(P([]), [((1, 13), ["−6", "−5", "−4", "−3", "−2", "−1", "0", "+1", "+2", "+3", "+4", "+5", "+6"], "B"),
                        ((17, 17), "split", "M"), ((18, 18), "USBmerge", "C"),
                        ((25, 25), "keep", "W"), ((26, 26), "reset", "R"), ((29, 32), ["chd", "arp", "eucl", "mel"], "S")])
dsetup_b = fut(P(DRUMS), [((1, 2), ["stock", "GM"], "W")])

BETA = [
    ("Table of contents: the same slot means the same kind of page on every track", [
        page("Synth and MIDI tracks", "Shift held on a page", toc_nb,
             "25 Chords (what a pad plays) · 26 Arp (repeats in time while held) · 27 Pattern tools (write a rhythm) · 28 Melody (write notes) · ★ 29 Vary (rework the pattern) · 30–31 free · 32 Keys (set once)."),
        page("Drum tracks", "Shift held on a drum page", toc_db,
             "★ 25 Levels (what a pad plays; later) · ★ 26 Repeat (moved from 25: the drums' arpeggiator) · 27 Pattern tools · 28 none (drums have no notes) · ★ 29 Vary · 30–31 free · ★ 32 Setup (set once)."),
    ]),
    ("New or changed pages (sketches; nothing designed)", [
        page("Vary", "pad 29 · both track kinds · actions with Draft / Undo / Write", vary_b,
             "Humanize velocity and timing (small changes around each step's own value), ratchets, mutate in key, quantize, reverse, nudge. On a drum, what means nothing stays dark (ratchets: the roll is on Pattern tools; mutate: notes)."),
        page("Keys", "pad 32 · set once", keys_b,
             "As built (1–4) + ★ 5 strummed release, ★ 6 scale lock on MIDI in (per track: MIDI in arrives per channel), ★ 7 MIDI in through chords and arp, ★ 8 MIDI in into a held step · ★ row 2: pad layout scale · in-key fourths · chromatic fourths · Jankó."),
        page("Drum setup", "drum pad 32 · set once, for the kit", dsetup_b,
             "★ MIDI out notes: stock's (60 / 62 / 64 / 65) · GM (36 / 38 / 42 / 46). Per-drum notes later if asked."),
        page("Project", "Shift + Mixer · one page, no table of contents", project_b,
             "Live transpose · split keyboard, ★ USB merge (later also the pad velocity curve and save-waits-for-Stop) · keep / reset CTPlay settings (two presses) · build info."),
        page("Levels", "drum pad 25 · 16 levels", levels_f,
             "One drum over pads 1–16 by velocity, pitch or decay; pick the drum on 29–32."),
    ]),
]

CSS = """
:root{--bg:#121212;--fg:#eee;--mut:#9a9a9a;--card:#1c1c1c;--line:#333}
:root[data-theme=light]{--bg:#f4f4f4;--fg:#111;--mut:#555;--card:#fff;--line:#ccc}
@media (prefers-color-scheme: light){:root:not([data-theme=dark]){--bg:#f4f4f4;--fg:#111;--mut:#555;--card:#fff;--line:#ccc}}
*{box-sizing:border-box}body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.4 system-ui,sans-serif}
h1{font-size:20px;margin:0 0 4px}h2{font-size:16px;margin:24px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}
.lead{color:var(--mut);margin:0 0 8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px;margin:10px 0;max-width:640px}
.card h3{margin:0;font-size:15px}.sub{color:var(--mut);font-size:12px;margin:2px 0 8px}
.grid{display:grid;grid-template-columns:repeat(8,1fr);gap:3px;background:#000;padding:4px;border-radius:6px}
.pad{aspect-ratio:1;border-radius:4px;display:flex;align-items:center;justify-content:center;text-align:center;
 font-size:clamp(7px,2.1vw,11px);line-height:1.05;font-weight:600;color:#111;overflow:hidden;word-break:break-all;padding:1px;position:relative}
.free{background:#1a1a1a;border:1px dashed #444}.dark{background:#0c0c0c}
.stock{color:#ddd}.future{outline:2px dashed #fff;outline-offset:-2px}
.future::after{content:"★";position:absolute;top:0;right:1px;font-size:8px;color:#000}
.notes{font-size:12px;color:var(--mut);margin:6px 0 0}
.legend{display:flex;flex-wrap:wrap;gap:8px;font-size:12px;color:var(--mut);margin:8px 0}
.legend span{display:inline-flex;align-items:center;gap:4px}.sw{width:14px;height:14px;border-radius:3px;display:inline-block}
"""

def render(title, lead, sections, path):
    out = [f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body><h1>{html.escape(title)}</h1><p class=lead>{lead}</p>"
           "<div class=legend><span><i class='sw free'></i>free</span><span><i class='sw dark'></i>dark</span>"
           "<span><i class=sw style='background:#6b6b6b'></i>stock's</span><span><i class='sw future' style='background:#888'></i>★ candidate</span></div>"]
    for sec, pages in sections:
        out.append(f"<h2>{html.escape(sec)}</h2>")
        for p in pages:
            out.append(f"<div class=card><h3>{html.escape(p['name'])}</h3><div class=sub>{html.escape(p['sub'])}</div><div class=grid>")
            for lab, col, kind in p["pads"]:
                if col is None:
                    cls = "dark" if kind == "dark" else "free"
                    out.append(f"<div class='pad {cls}'></div>")
                else:
                    cls = "pad " + ("stock" if kind == "stock" else "future" if kind == "future" else "")
                    out.append(f"<div class='{cls}' style='background:{C[col]}'>{html.escape(lab)}</div>")
            out.append(f"</div><p class=notes>{html.escape(p['notes'])}</p></div>")
    out.append("</body></html>")
    Path(path).write_text("".join(out))

here = Path(__file__).parent
render("Pad layouts after PL17", "Every CTPlay page as it would be once PL16 and PL17 are built. Pads 1–32 from the top left, 8 per row. Colours approximate the device's.",
       AFTER, here / "layouts-after-pl17.html")
render("Pad layouts: PL18+ candidates", "Where the remaining candidates could go (★, sketches only; nothing designed yet). Unchanged pages are left out.",
       LATER, here / "layouts-pl18-candidates.html")
render("Pad layouts: the beta pass", "The page slots fixed at the beta (2026-11-10, beta-layout-pass.md): ★ = moved or new. Pages not shown are as built (layouts-after-pl17.html).",
       BETA, here / "layouts-beta-pass.html")
print("ok")
