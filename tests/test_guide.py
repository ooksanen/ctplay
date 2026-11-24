import base64
import re

import pytest

from playbuild import guide, uploader
from playbuild.errors import BuildError

V = "1.0 beta 2"


def test_repo_links_point_at_the_public_main():
    assert guide.REPO_URL == "https://github.com/ooksanen/ctplay/blob/main/"


def test_slug_matches_github():
    seen = {}
    assert guide.slug("CTPlay's own limitations", seen) == "ctplays-own-limitations"
    assert guide.slug("Polyphony: how many notes a synth holds", seen) == "polyphony-how-many-notes-a-synth-holds"
    assert guide.slug("Count-in", seen) == "count-in"
    assert guide.slug("Count-in", seen) == "count-in-1"
    assert guide.slug("Count-in", seen) == "count-in-2"


def test_slug_of_inline_markup():
    r = guide.render("# T\n\n## Using `playbuild` and [links](#x) <sup>1</sup>\n")
    assert r.toc == [(2, "using-playbuild-and-links-1", "Using playbuild and links 1")]


def test_every_in_page_link_has_its_target():
    r = guide.render(guide.GUIDE.read_text(encoding="utf-8"))
    ids = set(re.findall(r'\bid="([^"]+)"', r.body))
    for want in ("ctplays-own-limitations", "going-back-to-the-official-firmware", "chords"):
        assert want in ids
    missing = {h for h in re.findall(r'href="#([^"]+)"', r.body) if h not in ids}
    assert not missing


def test_menu():
    r = guide.render(guide.GUIDE.read_text(encoding="utf-8"))
    assert (2, "installing", "Installing") in r.toc and (3, "bass-modes", "Bass modes") in r.toc
    assert all(level in (2, 3) for level, _, _ in r.toc)


def test_no_relative_repository_link_is_left():
    r = guide.render(guide.GUIDE.read_text(encoding="utf-8"))
    hrefs = re.findall(r'href="([^"]+)"', r.body)
    assert all(h.startswith(("#", "/", "https://", "http://", "mailto:")) for h in hrefs)    # "/": a site page
    assert 'href="https://github.com/ooksanen/ctplay/blob/main/README.md"' in r.body


def test_headings_get_a_link_icon_and_sections_are_panels():
    r = guide.render("# T\n\nintro\n\n## A\n\ntext\n\n### B\n\n## C\n")
    assert '<h2 id="a"><span>A</span><a class="hlink" href="#a"' in r.body
    assert r.body.count('<section class="panel">') == 2 and "intro" not in r.body.split('<section')[1]


PAD_TABLE = "| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |\n|---|---|---|---|---|---|---|---|---|\n| a | x | x | x | x | x | x | x | · |\n"


def test_the_pad_tables():
    md = guide.GUIDE.read_text(encoding="utf-8")
    body = guide.render(md).body
    assert body.count('<div class="pads">') == md.count("<!-- pads:") >= 6 and "<!-- pads:" not in body
    chords = body.split('<div class="pads">')[1]
    rows = re.findall(r"<tr>(.*?)</tr>", chords, re.S)
    assert '<td class="pad b on">root pos.</td>' in rows[3]
    assert '<td class="pad o"><a href="#bass-modes">bass</a></td>' in rows[3]
    assert rows[2].count('<td class="pad free" aria-label="free pad"></td>') == 3 and "<small>4+ notes</small>" in rows[3]
    assert ">·<" not in "".join(rows)                   # square pads: a free one is blank (2026-10-25)
    voicing = next(t for t in body.split('<div class="pads">') if '<td>E G B C</td>' in t)
    assert '<td class="pad b on">root pos.</td>' in voicing and "<td>C E G B</td>" in voicing
    shapes = next(t for t in body.split('<div class="pads">') if '<td>C G C</td>' in t)
    assert "<td>·</td>" in shapes                       # an example row is not pads: its · stays


def test_parse_hint():
    assert guide.parse_hint("<!-- pads: W w · · · · · o -->") == [[("w", True), ("w", False)] + [(None, False)] * 5 + [("o", False)]]


@pytest.mark.parametrize("md", [
    PAD_TABLE,                                                   # no hint
    "<!-- pads: w w w w w w w -->\n" + PAD_TABLE,                # 7 tokens
    "<!-- pads: w w w w w w w w -->\n" + PAD_TABLE,              # last pad is free in the table, not in the hint
    "<!-- pads: w w w w w w w · / w w w w w w w · -->\n" + PAD_TABLE,   # more rows than the table
    "<!-- pads: w w w w w w w · -->\n| a | b |\n|---|---|\n| 1 | 2 |\n",  # hint on a table that is not a pad table
])
def test_bad_hints_fail_the_build(md):
    with pytest.raises(BuildError):
        guide.render(md)


def test_write_builds_the_page():
    html = guide.render_pages(V)["index.html"]
    assert html.startswith("<!doctype html>") and f"USER GUIDE · {V}" in html and "{{" not in html
    assert 'href="#bass-modes"' in html and '<nav id="toc"' in html and 'href="https://ctctrl.com"' in html
    assert re.findall(r'(?:src|href)="(https?://[^"]+)"', html.split("<body")[0]) == [
        "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap"]


def test_a_template_without_a_placeholder_fails(tmp_path, monkeypatch):
    t = tmp_path / "t.html"
    t.write_text("<!doctype html>{{title}}{{version}}{{body}}", encoding="utf-8")
    monkeypatch.setattr(guide, "TEMPLATE", t)
    with pytest.raises(BuildError):
        guide.render_pages(V)


def test_a_hint_can_carry_its_own_key():
    md = "<!-- pads: w w w w w w w · ; key: Bright: an <example> -->\n" + PAD_TABLE
    body = guide.render(md).body
    assert '<p class="padkey">Bright: an &lt;example&gt;</p>' in body and guide.PAD_KEY not in body
    assert guide.parse_hint("<!-- pads: W w · · · · · o ; key: x -->")[0][0] == ("w", True)
    with pytest.raises(BuildError):
        guide.render("<!-- pads: w w w w w w w · ; key: -->\n" + PAD_TABLE)


def test_the_pattern_tools_map_says_its_bright_pads_are_an_example():
    body = guide.render(guide.GUIDE.read_text(encoding="utf-8")).body
    tools = next(t for t in body.split('<div class="pads">') if ">Write</td>" in t)
    assert '<p class="padkey">Bright: an example' in tools


# ---- Images (2026-10-19): screenshots in docs/images/, embedded so the page stays one file ----

WEBP = b"RIFF\x0c\x00\x00\x00WEBPVP8 " + bytes(8)


def test_a_local_image_is_embedded_at_2x(tmp_path):
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "a.webp").write_bytes(WEBP)
    r = guide.render("# T\n\n![The panel](images/a.webp)\n", base=tmp_path)
    data = "data:image/webp;base64," + base64.b64encode(WEBP).decode()
    assert f'srcset="{data} 2x"' in r.body and 'alt="The panel"' in r.body
    assert " src=" not in r.body                # the 2x descriptor sizes it: shown at half its pixels


def test_a_missing_image_fails_the_build(tmp_path):
    with pytest.raises(BuildError, match="images/none.webp"):
        guide.render("# T\n\n![x](images/none.webp)\n", base=tmp_path)


def test_an_unknown_image_type_fails_the_build(tmp_path):
    (tmp_path / "a.bmp").write_bytes(b"BM")
    with pytest.raises(BuildError, match="a.bmp"):
        guide.render("# T\n\n![x](a.bmp)\n", base=tmp_path)


def test_a_remote_image_is_left_alone(tmp_path):
    r = guide.render("# T\n\n![x](https://example.com/a.png)\n", base=tmp_path)
    assert 'src="https://example.com/a.png"' in r.body


def test_the_guide_images_exist_and_are_small():
    md = guide.GUIDE.read_text(encoding="utf-8")
    for src in re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", md):
        p = guide.GUIDE.parent / src
        assert p.exists() and p.stat().st_size < 60_000, src


# ---- final review fixes (2026-10-21) ----

def test_slug_skips_slugs_already_taken():
    seen = {}
    assert [guide.slug(t, seen) for t in ("Bass", "Bass", "Bass 1", "Bass 1")] == ["bass", "bass-1", "bass-1-1",
                                                                                   "bass-1-2"]


@pytest.mark.parametrize("text, want", [
    ("Strum ½ speed", "strum--speed"),            # ½ ² are numbers, not digits: github-slugger drops them
    ("x² and y", "x-and-y"),
    ("Cafe\u0301 mode", "cafe\u0301-mode"),        # a combining mark stays (Python's \\w would drop it)
    ("Ⓐ and ①", "ⓐ-and-"),                        # circled letters are letters; circled digits are not
    ("snake_case & more", "snake_case--more"),
])
def test_slug_follows_github_slugger_on_unicode(text, want):
    """Checked against github-slugger 2.0.0 itself over every code point to U+2FFFF (2026-10-21): it keeps letters,
    marks, Nd, Nl, Pc and the circled / squared Latin letters; only characters newer than its Unicode tables differ."""
    assert guide.slug(text, {}) == want


def test_a_heading_with_markup_is_one_flex_item():
    r = guide.render("# T\n\n## Using `playbuild` <sup>1</sup>\n")
    assert ('<h2 id="using-playbuild-1"><span>Using <code>playbuild</code> <sup>1</sup></span><a class="hlink"'
            in r.body)


def test_raw_html_links_are_rewritten_like_markdown_links():
    r = guide.render('# T\n\nSee <a href="../README.md#setup">the README</a> or <a href="#t">top</a>.\n\n'
                     '<p><a class="x" href="specs/a&amp;b.md">block</a></p>\n')
    assert 'href="https://github.com/ooksanen/ctplay/blob/main/README.md#setup"' in r.body
    assert 'href="#t"' in r.body
    assert 'href="https://github.com/ooksanen/ctplay/blob/main/docs/specs/a&amp;b.md"' in r.body


def test_a_local_raw_html_image_fails_the_build():
    with pytest.raises(BuildError, match="write a local image as Markdown"):
        guide.render('# T\n\n<img src="images/x.png" alt="x">\n')
    assert "https://x/y.png" in guide.render('# T\n\n<img src="https://x/y.png" alt="x">\n').body


def test_a_link_outside_the_repository_fails_the_build():
    with pytest.raises(BuildError, match="outside the repository"):
        guide.render("# T\n\n[x](../../../../outside.md)\n")


def test_storage_and_clipboard_are_guarded():
    """Private windows and blocked storage throw on localStorage; the clipboard needs a secure context: the guide must
    still work (artifact rules; final review 2026-10-18)."""
    try:
        from playbuild import vote
    except ImportError:                           # the public tree has no vote page
        vote = None
    for template in [guide.TEMPLATE] + ([vote.TEMPLATE] if vote else []):
        src = template.read_text(encoding="utf-8")
        for m in re.finditer(r"localStorage\.", src):
            before = src[:m.start()]
            assert before.rfind("try {") > before.rfind("catch"), f"{template.name}: localStorage outside a try"
    src = guide.TEMPLATE.read_text(encoding="utf-8")
    assert "if (!a || !navigator.clipboard || !window.isSecureContext) return;" in src
    write = src.index("navigator.clipboard.writeText")
    assert src[:write].rfind("try {") > src[:write].rfind("catch")


def test_theme_color_follows_the_theme():
    vote = pytest.importorskip("playbuild.vote")
    head = vote._shared_head()                    # the vote page shares it
    assert '<meta name="theme-color" content="#14141a" media="(prefers-color-scheme: dark)">' in head
    assert '<meta name="theme-color" content="#f5f5f7" media="(prefers-color-scheme: light)">' in head
    assert "paintTheme(t)" in head and "paintTheme(next)" in guide.TEMPLATE.read_text(encoding="utf-8")


def _contrast(a: str, b: str) -> float:
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_link_coloured_code_reaches_aa_contrast_in_both_themes():
    src = guide.TEMPLATE.read_text(encoding="utf-8")
    blocks = re.findall(r"--bg-code: (#[0-9a-f]{6});.*?--accent-text: (#[0-9a-f]{6});", src, re.S)
    assert len(blocks) == 3                      # dark, light by the system, light picked
    assert all(_contrast(fg, bg) >= 4.5 for bg, fg in blocks), blocks


def test_cyan_and_violet_pads():
    rows = guide.parse_hint("<!-- pads: C c V v · · · · -->")[0]
    assert rows[:4] == [("c", True), ("c", False), ("v", True), ("v", False)]
    body = guide.render("<!-- pads: C v w w w w w · -->\n" + PAD_TABLE).body
    assert '<td class="pad c on">' in body and '<td class="pad v">' in body
    with pytest.raises(guide.BuildError):
        guide.parse_hint("<!-- pads: x w w w w w w w -->")


# ---- the launch site (2026-11-22) ----

def test_a_link_to_a_site_page_becomes_its_path():
    r = guide.render("[a](recipes.md#x) [b](user-guide.md) [c](user-guide.md#y) [d](../README.md)")
    hrefs = re.findall(r'href="([^"]+)"', r.body)
    assert hrefs == ["/recipes/#x", "/", "/#y", guide.REPO_URL + "README.md"]


def test_site_version_is_the_newest_release(monkeypatch):
    monkeypatch.setattr(uploader, "releases", lambda: [{"release": "1.0 beta 2"}, {"release": "1.0 beta 1"}])
    assert guide.site_version() == "1.0 beta 2"
    monkeypatch.setattr(uploader, "releases", lambda: [])
    with pytest.raises(BuildError):
        guide.site_version()


def test_each_page_has_its_title_subtitle_and_source():
    pages = guide.render_pages(V)
    assert set(pages) == {"index.html", "recipes/index.html"}
    g, r = pages["index.html"], pages["recipes/index.html"]
    assert "<title>CTPlay user guide</title>" in g and f"USER GUIDE · {V}" in g and "docs/user-guide.md" in g
    assert "<title>CTPlay recipes</title>" in r and f"RECIPES · {V}" in r and "docs/recipes.md" in r
    assert all("{{" not in html for html in pages.values())


def test_every_page_links_the_others_and_never_the_vote():
    for html in guide.render_pages(V).values():
        for href in ('href="/"', 'href="/recipes/"', 'href="/uploader/"', 'href="https://ctctrl.com"'):
            assert href in html
        assert "/vote" not in html


def test_the_footer_links_discussions_and_issues():
    html = guide.render_pages(V)["index.html"]
    footer = html.split("<footer>")[1]
    assert f'href="{guide.PUBLIC_REPO}/discussions"' in footer and f'href="{guide.PUBLIC_REPO}/issues"' in footer


def test_the_menu_skips_a_pages_toc_skip():
    html = guide.render_pages(V)["index.html"]
    nav = html.split('<nav id="toc"')[1].split("</nav>")[0]
    assert 'href="#changes-by-feature"' not in nav and 'href="#installing"' in nav


def test_check_links_accepts_good_links():
    pages = {"index.html": '<h2 id="a">A</h2><a href="#a">x</a><a href="/recipes/index.html#r">y</a>',
             "recipes/index.html": '<h3 id="r">R</h3><a href="/#a">x</a><a href="/">y</a><a href="/?q=1&amp;z=2#a">z</a>',
             "uploader/index.html": '<a href="../#a">x</a>',
             "uploader/PL22/index.html": '<a href="../../#a">x</a><a href="../">y</a>'}
    assert guide.check_links(pages) == []


def test_check_links_names_every_broken_link():
    pages = {"index.html": '<h2 id="a">A</h2><a href="/#nope">x</a><a href="/nowhere/">y</a>',
             "recipes/index.html": '<a href="/#a">ok</a><a href="#gone">z</a>'}
    with pytest.raises(BuildError) as e:
        guide.check_links(pages)
    msg = str(e.value)
    assert "index.html: /#nope" in msg and "index.html: /nowhere/" in msg and "recipes/index.html: #gone" in msg


def test_check_links_skips_external_links():
    assert guide.check_links({"index.html": '<a href="https://x.org/#y">a</a><a href="mailto:a@example.com">b</a>'}) == []


def test_check_links_unquotes_fragments():
    assert guide.check_links({"index.html": '<h2 id="b♭">B</h2><a href="#b%E2%99%AD">x</a>'}) == []


def test_check_links_missing_ok():
    pages = {"index.html": '<a href="/uploader/">u</a>'}
    assert guide.check_links(pages, missing_ok=("uploader/",)) == ["/uploader/"]
    with pytest.raises(BuildError):
        guide.check_links(pages)


def test_the_real_docs_link_up():
    guide.check_links(guide.render_pages(V), missing_ok=("uploader/",))


def test_write_site_docs_only(tmp_path):
    root = tmp_path / "site"
    (root / "public" / "vote").mkdir(parents=True)
    (root / "public" / "vote" / "index.html").write_text("old")
    (root / ".wrangler").mkdir()
    (root / ".wrangler" / "keep").write_text("x")
    guide.write_site(root, docs_only=True)
    files = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    assert files == [".wrangler/keep", "public/index.html", "public/recipes/index.html"]


def test_a_broken_link_writes_nothing(tmp_path, monkeypatch):
    root = tmp_path / "site"
    (root / "public").mkdir(parents=True)
    (root / "public" / "index.html").write_text("previous")
    monkeypatch.setattr(guide, "render_pages", lambda v: {"index.html": '<a href="#gone">x</a>'})
    with pytest.raises(BuildError):
        guide.write_site(root, docs_only=True)
    assert (root / "public" / "index.html").read_text() == "previous"


# ---- the recipes page (2026-11-22) ----

RECIPE_TITLES = ["A chord progression that moves smoothly", "Off-beat chord stabs", "An arpeggio you can play over",
                 "A melody from a 9th chord", "A bass line", "A riff that drifts against the beat",
                 "A beat from four drums", "Hi-hats played live",
                 "A snare roll every 4th bar, and a fill when you want it"]
TRY_IT = {"voice-leading": ["A chord progression that moves smoothly"],
          "chords-in-step-entry": ["Off-beat chord stabs"], "pattern-strum": ["Off-beat chord stabs"],
          "arpeggiator": ["An arpeggio you can play over"], "drum-pattern-tools": ["A beat from four drums"],
          "the-repeat-page": ["Hi-hats played live"], "euclidean-fills": ["A riff that drifts against the beat"],
          "melodic-generator": ["A melody from a 9th chord", "A bass line"],
          "trig-conditions": ["A snare roll every 4th bar, and a fill when you want it"]}


def section(md: str, sid: str) -> str:
    """The Markdown from the heading whose slug is `sid` to the next heading of the same or a higher level."""
    lines, seen, start, level = md.splitlines(), {}, None, 0
    for i, line in enumerate(lines):
        m = re.match(r"(#{1,6}) (.+)$", line)
        if not m:
            continue
        if start is not None and len(m.group(1)) <= level:
            return "\n".join(lines[start:i])
        if start is None and guide.slug(m.group(2), seen) == sid:
            start, level = i, len(m.group(1))
    assert start is not None, sid
    return "\n".join(lines[start:])


def test_the_recipes_page_holds_every_recipe():
    md = guide.RECIPES.read_text(encoding="utf-8")
    assert sorted(re.findall(r"^### (.+)$", md, re.M)) == sorted(RECIPE_TITLES)
    assert "DRAFT" not in md and "](user-guide.md)" in md.split("\n## ")[0]   # the back link, above the first section


def test_the_guide_keeps_no_recipe_of_its_own():
    md = guide.GUIDE.read_text(encoding="utf-8")
    assert not any(f"### {t}" in md for t in RECIPE_TITLES)
    assert "](recipes.md)" in section(md, "recipes")


def test_each_feature_section_ends_with_try_it():
    md = guide.GUIDE.read_text(encoding="utf-8")
    for sid, titles in TRY_IT.items():
        lines = [l for l in section(md, sid).splitlines() if l.startswith("Try it:")]
        assert len(lines) == 1, sid
        for t in titles:
            assert f"(recipes.md#{guide.slug(t, {})})" in lines[0], (sid, t)


# ---- the guide for a published beta (2026-11-22) ----

def test_the_guide_has_no_version_history():
    md = guide.GUIDE.read_text(encoding="utf-8")
    assert "<sup>" not in md and "## Versions" not in md and not re.search(r"\bPL\d", md)
    changes = section(md, "changes-by-feature")
    assert "\n### " not in changes and len(changes.strip().splitlines()) <= 3
    assert "#changes-by-feature" not in md                     # not in the intro or the Contents line


def test_the_guide_reads_as_published():
    md = guide.GUIDE.read_text(encoding="utf-8")
    inst = section(md, "installing")
    assert "ctplay.ctctrl.com/uploader/" in inst and "will be at" not in inst and "1.2.1" in inst
    assert "Components" in inst                                # the stay-on-1.2.1 warning names where updates come from
    back = section(md, "going-back-to-the-official-firmware")
    assert "back up" in back.lower() and "SD card" in back
    assert f"({guide.PUBLIC_REPO}/releases)" in md
    assert "not published yet" not in section(md, "building-from-source")


def test_the_recipes_name_no_build():
    assert not re.search(r"\bPL\d", guide.RECIPES.read_text(encoding="utf-8"))


def test_the_site_docs_mention_no_vote():
    from playbuild import paths
    if not (paths.ROOT / "site" / "README.md").is_file():
        pytest.skip("the public tree has no site/")
    for p in (paths.ROOT / "README.md", paths.ROOT / "site" / "README.md", guide.TEMPLATE, guide.GUIDE, guide.RECIPES):
        assert "vote" not in p.read_text(encoding="utf-8").lower(), p
    assert "ctplay.ctctrl.com" in (paths.ROOT / "site" / "README.md").read_text(encoding="utf-8")


def test_docs_only_never_touches_the_deployable_site(tmp_path, monkeypatch):
    """--docs builds no uploader, so it writes its own folder: build/site/ is always a whole site to deploy."""
    monkeypatch.setattr(guide, "BUILD", tmp_path)
    (tmp_path / "site" / "public" / "uploader").mkdir(parents=True)
    (tmp_path / "site" / "public" / "uploader" / "index.html").write_text("the uploader")
    guide.write_site(docs_only=True)
    assert (tmp_path / "site" / "public" / "uploader" / "index.html").read_text() == "the uploader"
    assert (tmp_path / "site-docs" / "public" / "recipes" / "index.html").exists()
