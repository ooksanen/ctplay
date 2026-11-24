"""Row-4 mockups for PL20 trig conditions (2026-10-28): three options; the user picked C. Run with the repo's .venv: writes trig-row4.html beside this script."""
import html
from pathlib import Path

COL = dict(step="#5d5f63", sel="#f2f2f2", prob="#5d5f63", probon="#b9bcc2",
           pass_on="#2fd6d6", pass_off="#155e5e", first="#37c84a", first_d="#1a5e23",
           fill="#ff9a1f", fill_d="#6e430e", pre="#9a5cff", pre_d="#3f2669", last="#f2e33a", last_d="#6a6419",
           div="#2fd6d6", div_d="#155e5e", neg="#ff4040", neg_d="#6b1b1b", dark="#0b0b0c")
DARK_TEXT = {"step", "prob", "pass_off", "first_d", "fill_d", "pre_d", "last_d", "div_d", "neg_d"}


def pad(label, col, extra=""):
    if col is None:
        return '<div class="pad off"></div>'
    fg = "#e8e8e8" if col in DARK_TEXT else "#101010"
    return f'<div class="pad {extra}" style="background:{COL[col]};color:{fg}">{html.escape(label)}</div>'


def base_rows(sel=5, prob=8):
    out = []
    for s in range(1, 17):
        out.append(pad(str(s), "sel" if s == sel else "step", "stock"))
    for p in range(1, 9):
        out.append(pad(f"{p * 12.5:g}%" if p < 8 else "100%", "probon" if p == prob else "prob", "stock"))
    return out


def grid(row4, **kw):
    cells = base_rows(**kw) + [pad(*c) if c else pad("", None) for c in row4]
    return '<div class="grid">' + "".join(cells) + "</div>"


def strip(row4, caption):
    cells = "".join(pad(*c) if c else pad("", None) for c in row4)
    return f'<figure class="step"><div class="strip">{cells}</div><figcaption>{caption}</figcaption></figure>'


N = None
# ---- Option A: divider pads (Elektron set)
A_plain = [("÷2", "div_d"), ("1:4", "div"), ("÷4", "div_d"), ("÷8", "div_d"),
           ("1st", "first_d"), ("fill", "fill_d"), ("pre", "pre_d"), N]
A_plain[1] = ("÷3", "div_d"); A_plain[2] = ("1:4", "div")
A_steps = [
    strip([("÷2", "div_d"), ("÷3", "div_d"), ("÷4", "div_d"), ("÷8", "div_d"), ("1st", "first_d"), ("fill", "fill_d"), ("pre", "pre_d"), N],
          "A step with no condition: every pad dim (available)."),
    strip([("÷2", "div_d"), ("÷3", "div_d"), ("1:4", "div"), ("÷8", "div_d"), ("1st", "first_d"), ("fill", "fill_d"), ("pre", "pre_d"), N],
          "Tap <b>÷4</b> once: <b>1:4</b>, the first of every 4 passes. Hold it to see which pass (below)."),
    strip([("1", "pass_on"), ("2", "pass_off"), ("3", "pass_off"), ("4", "pass_off"), N, N, N, N],
          "While ÷4 is held, rows 1–2 show the cycle: pass 1 bright, 2–4 dim."),
    strip([("2:2", "div"), ("÷3", "div_d"), ("÷4", "div_d"), ("÷8", "div_d"), ("1st", "first_d"), ("fill", "fill_d"), ("pre", "pre_d"), N],
          "<b>2:2</b> (every second pass): tap <b>÷2</b> twice. A third tap clears it."),
    strip([("÷2", "div_d"), ("÷3", "div_d"), ("÷4", "div_d"), ("÷8", "div_d"), ("!1st", "neg"), ("fill", "fill_d"), ("pre", "pre_d"), N],
          "<b>Shift + 1st</b>: “not first” (red). Shift + a ÷ pad gives “not A:B”."),
]

# ---- Option B: pass grid only
B_plain = [("1", "pass_on"), ("2", "pass_off"), ("3", "pass_off"), ("4", "pass_off"), N, N, N, N]
B_steps = [
    strip([N] * 8, "No condition: row 4 dark. The step plays every pass."),
    strip([("1", "pass_off"), ("2", "pass_off"), ("3", "pass_off"), ("4", "pass_off"), N, N, N, N],
          "<b>Shift + pad 4</b>: a cycle of 4 passes. Pads 1–4 light dim, ready to pick."),
    strip([("1", "pass_on"), ("2", "pass_off"), ("3", "pass_off"), ("4", "pass_off"), N, N, N, N],
          "Tap <b>1</b>: plays on pass 1 of every 4 (1:4). What you see is what plays."),
    strip([("1", "pass_on"), ("2", "pass_on"), ("3", "pass_on"), ("4", "pass_off"), N, N, N, N],
          "Tap <b>2</b> and <b>3</b> too: every pass but the 4th (“not 4:4”). Any mix works."),
    strip([("1", "pass_on"), ("2", "pass_off"), ("3", "pass_on"), ("4", "pass_off"), ("5", "pass_on"), ("6", "pass_off"), ("7", "pass_off"), ("8", "pass_on")],
          "Up to 8 passes: an 8-bar figure on a 1-bar pattern."),
]

# ---- Option C: pass grid + Shift layer of special conditions
C_plain = B_plain
C_shift = [("1st", "first_d"), ("!1st", "first_d"), ("fill", "fill"), ("!fill", "fill_d"),
           ("pre", "pre_d"), ("!pre", "pre_d"), ("last", "last_d"), ("!last", "last_d")]
C_steps = [
    strip([("1", "pass_off"), ("2", "pass_off"), ("3", "pass_off"), ("4", "pass_off"), N, N, N, N],
          "<b>Hold pad 4 for ½ s</b>: a cycle of 4 passes (pads 1–4 dim)."),
    strip([("1", "pass_on"), ("2", "pass_off"), ("3", "pass_off"), ("4", "pass_off"), N, N, N, N],
          "Tap <b>1</b>: 1:4. Tapping passes works exactly as in option B."),
    strip([("1st", "first_d"), ("!1st", "first_d"), ("fill", "fill_d"), ("!fill", "fill_d"),
           ("pre", "pre_d"), ("!pre", "pre_d"), ("last", "last_d"), ("!last", "last_d")],
          "<b>Hold Shift</b>: row 4 turns into the special conditions, one pad each, dim = available."),
    strip([("1st", "first_d"), ("!1st", "first_d"), ("fill", "fill"), ("!fill", "fill_d"),
           ("pre", "pre_d"), ("!pre", "pre_d"), ("last", "last_d"), ("!last", "last_d")],
          "<b>Shift + fill</b>: the step plays only while FILL is on. It replaces a pass cycle (one or the other)."),
]

OPTIONS = [
    dict(key="A", name="Divider pads", tag="closest to Elektron",
         pitch="Four pads choose the cycle (÷2, ÷3, ÷4, ÷8); tapping again steps through which pass plays. "
               "Three pads for the special conditions. Shift turns any of them into its “not”.",
         grids=[("Row 4 with a 1:4 step", grid(A_plain))], steps=A_steps,
         good=["Covers the conditions musicians use most (1:2 … 4:4, 8:8, FIRST, FILL, PRE) with their negations.",
               "Every condition is one or two taps away.", "Leaves pad 32 free (LAST later)."],
         bad=["No cycles of 5, 6 or 7.", "Which pass a ÷ pad plays is hidden until you hold the pad.",
              "Only fixed “A of B” values, not “passes 1 and 3 of 4”."],
         fits="Drums: 8 bits (one byte per step). Notes: 8 of their 16 bits."),
    dict(key="B", name="Pass grid", tag="most visual, fewest features",
         pitch="Row 4 is the passes themselves. Shift + a pad sets the cycle length; a tap ticks the passes the step plays on. "
               "Nothing else on the row.",
         grids=[("Row 4 with a 1:4 step", grid(B_plain))], steps=B_steps,
         good=["What you see is what plays: the lit passes are the ones that sound.",
               "Any mix of passes, cycles 2–8 (covers A:B and “not A:B” without extra values).",
               "One idea to learn."],
         bad=["No FILL, FIRST or PRE: they would need a home somewhere else, later.",
              "Shift is spent on the cycle length, so it can't be a modifier for anything else here."],
         fits="Drums: 9 bits (the byte plus one shared bit). Notes: 11 of 16 bits."),
    dict(key="C", name="Pass grid + Shift layer", tag="recommended",
         pitch="Option B's pass grid, with the cycle length set by holding a pass pad for ½ s. "
               "Holding Shift swaps row 4 for the special conditions: FIRST, FILL, PRE, LAST and their “not”s, one pad each.",
         grids=[("Row 4 with a 1:4 step", grid(C_plain)), ("Shift held: a FILL step", grid(C_shift))], steps=C_steps,
         good=["Everything from A and B: any pass mix, cycles 2–8, and all the special conditions.",
               "Both layers are one pad per value, as every CTPlay page.",
               "Shift as a layer switch matches CTPlay's Quick view habit."],
         bad=["A step has a pass cycle <i>or</i> a special condition, not both (the drums' 9 bits).",
              "The ½ s hold is a new gesture in CTPlay.",
              "LAST needs the next pattern known in advance: may stay dark at first."],
         fits="Drums: 9 bits (pass masks use most codes, the 8 specials fit in the rest). Notes: 16 bits, room left."),
]

CSS = """
:root{
  /* Layout: a column of option panels; each panel = device grid(s) on the left, the walkthrough on the right. */
  --paper:#eef0f2; --panel:#ffffff; --ink:#16181b; --mute:#5c6168; --rule:#d4d8dd; --accent:#127c7c;
  --device:#000000; --chip:#e2f3f3;
  --f-display:"Barlow Semi Condensed","Arial Narrow",sans-serif; --f-body:"Source Sans 3","Segoe UI",sans-serif;
  --f-mono:"JetBrains Mono",ui-monospace,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --paper:#121417; --panel:#1b1e22; --ink:#e9ecef; --mute:#9aa1a9; --rule:#2e3339; --accent:#4fd1d1; --chip:#173436;
  color-scheme:dark}}
:root[data-theme="dark"]{--paper:#121417; --panel:#1b1e22; --ink:#e9ecef; --mute:#9aa1a9; --rule:#2e3339;
  --accent:#4fd1d1; --chip:#173436; color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font:16px/1.5 var(--f-body);margin:0;
  padding-block:24px 48px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.wrap{max-width:1080px;margin:0 auto;display:grid;gap:28px}
header{display:grid;gap:8px;max-width:72ch}
h1{font:600 2.1rem/1.1 var(--f-display);margin:0;text-wrap:balance;letter-spacing:.01em}
.eyebrow{font:600 .78rem var(--f-display);text-transform:uppercase;letter-spacing:.12em;color:var(--accent)}
p{margin:0}
.lead{color:var(--mute)}
.common{display:grid;gap:6px;font-size:.95rem;color:var(--mute);border-left:3px solid var(--rule);padding-left:12px;max-width:80ch}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:.85rem;color:var(--mute)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{width:14px;height:14px;border-radius:3px;display:inline-block}
section.opt{background:var(--panel);border:1px solid var(--rule);border-radius:12px;padding:20px;display:grid;gap:16px}
section.opt.rec{border-color:var(--accent)}
.head{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 14px}
.key{font:600 1.6rem/1 var(--f-display);color:var(--accent)}
h2{font:600 1.45rem/1.15 var(--f-display);margin:0;text-wrap:balance}
.tag{font:600 .72rem var(--f-display);text-transform:uppercase;letter-spacing:.1em;background:var(--chip);color:var(--accent);
  padding:3px 8px;border-radius:999px}
.pitch{max-width:75ch}
.body{display:grid;grid-template-columns:minmax(0,340px) minmax(0,1fr);gap:20px 28px;align-items:start}
@media (max-width:760px){.body{grid-template-columns:1fr}}
.grids{display:grid;gap:14px}
.gcap{font:600 .78rem var(--f-display);text-transform:uppercase;letter-spacing:.08em;color:var(--mute);margin-bottom:6px}
.grid,.strip{display:grid;grid-template-columns:repeat(8,1fr);gap:4px;background:var(--device);padding:6px;border-radius:8px}
.strip{max-width:340px}
.pad{aspect-ratio:1;border-radius:4px;display:flex;align-items:center;justify-content:center;text-align:center;
  font:600 clamp(9px,2.4vw,12px)/1 var(--f-mono);overflow:hidden;padding:1px}
.pad.off{background:#0b0b0c;outline:1px solid #1f1f22;outline-offset:-1px}
.pad.stock{font-weight:500;font-size:clamp(7px,1.8vw,9.5px)}
.walk{display:grid;gap:12px;margin:0;padding:0}
figure.step{margin:0;display:grid;gap:6px}
figcaption{font-size:.92rem;max-width:60ch}
figcaption b{font-family:var(--f-mono);font-weight:600;font-size:.88em}
.pc{display:grid;grid-template-columns:1fr 1fr;gap:12px 24px}
@media (max-width:760px){.pc{grid-template-columns:1fr}}
.pc h3{font:600 .8rem var(--f-display);text-transform:uppercase;letter-spacing:.1em;margin:0 0 4px;color:var(--mute)}
.pc ul{margin:0;padding-left:18px;display:grid;gap:4px;font-size:.95rem}
.fits{font:500 .85rem var(--f-mono);color:var(--mute)}
"""


def option(o):
    rec = " rec" if o["tag"] == "recommended" else ""
    g = "".join(f'<div><div class="gcap">{html.escape(c)}</div>{gr}</div>' for c, gr in o["grids"])
    good = "".join(f"<li>{x}</li>" for x in o["good"])
    bad = "".join(f"<li>{x}</li>" for x in o["bad"])
    return (f'<section class="opt{rec}"><div class="head"><span class="key">{o["key"]}</span><h2>{o["name"]}</h2>'
            f'<span class="tag">{o["tag"]}</span></div><p class="pitch">{o["pitch"]}</p>'
            f'<div class="body"><div class="grids">{g}</div><div class="walk">{"".join(o["steps"])}</div></div>'
            f'<div class="pc"><div><h3>Good</h3><ul>{good}</ul></div><div><h3>Costs</h3><ul>{bad}</ul></div></div>'
            f'<p class="fits">Storage · {o["fits"]}</p></section>')


def legend():
    items = [("#f2f2f2", "selected step"), ("#5d5f63", "stock (steps, probability)"), ("#2fd6d6", "pass plays"),
             ("#155e5e", "pass skipped / available"), ("#37c84a", "FIRST"), ("#ff9a1f", "FILL"), ("#9a5cff", "PRE"),
             ("#f2e33a", "LAST"), ("#ff4040", "“not” (option A)")]
    return '<div class="legend">' + "".join(f'<span><i class="sw" style="background:{c}"></i>{t}</span>' for c, t in items) + "</div>"


page = f"""<title>Trig Condition Row</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@600&family=JetBrains+Mono:wght@500;600&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header><span class="eyebrow">CTPlay PL20 · trig conditions · sketch</span>
<h1>Three ways to fill row 4 of the probability view</h1>
<p class="lead">Shift + Pattern Settings opens stock's probability view. Rows 1–2 pick the step, row 3 is stock's probability.
Row 4 is ignored by stock: the condition goes there. Pads are drawn as on the device, 8 per row; colours are rough.</p></header>
<div class="common"><p><b>Same in every option.</b> One condition per step, on drums and on Synth / MIDI tracks.
Stock's probability still applies, so “1:4 at 50 %” works. Each pattern counts its own passes; the count starts over when you
press Play, pick a pattern, chain or scene, or load a project, and keeps counting while a chain plays itself.</p></div>
{legend()}
{"".join(option(o) for o in OPTIONS)}
</div>
"""
out = Path(__file__).with_name("trig-row4.html")
out.write_text(page)
print(out)
