"""build/site/public/: the public site for ctplay.ctctrl.com, in the CTCtrl family look, for Cloudflare Pages:
the user guide (docs/user-guide.md -> /), the recipes (docs/recipes.md -> /recipes/), each one self-contained page
from guide_template.html. The Markdown stays the only source; section ids match GitHub's, and a link to the other
page's file becomes that page's path, so the links work in both.

    .venv/bin/python -m playbuild.guide         (from the repo root)
"""
from __future__ import annotations

import base64
import html
import re
import shutil
import sys
import unicodedata
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token

from .errors import BuildError
from .paths import BUILD, ROOT

GUIDE = ROOT / "docs" / "user-guide.md"
RECIPES = ROOT / "docs" / "recipes.md"
TEMPLATE = Path(__file__).with_name("guide_template.html")
PLACEHOLDERS = ("{{title}}", "{{subtitle}}", "{{version}}", "{{toc}}", "{{body}}", "{{source}}", "{{repo}}")
REPO_URL = "https://github.com/ooksanen/ctplay/blob/main/"     # file links into the tree
PUBLIC_REPO = "https://github.com/ooksanen/ctplay"           # Releases, Discussions, Issues
LINK_ICON = ('<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" '
             'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
             '<path d="M10 13a5 5 0 0 0 7.07 0l3-3a5 5 0 0 0-7.07-7.07l-1.5 1.5"/>'
             '<path d="M14 11a5 5 0 0 0-7.07 0l-3 3a5 5 0 0 0 7.07 7.07l1.5-1.5"/></svg>')
HINT = re.compile(r"^<!--\s*pads:(.*?)-->\s*$", re.S)
PAD_COLOURS = "wbgmoycv"     # white, blue, green, magenta, orange, yellow (the gate), cyan, violet
FREE = "·"
PAD_KEY = '<p class="padkey">Bright: the default for a new project.</p>\n'


@dataclass
class Rendered:
    body: str
    toc: list[tuple[int, str, str]]     # (level 2 or 3, id, plain text), in page order


@dataclass(frozen=True)
class Page:
    src: Path                           # the Markdown
    out: str                            # its file in the site, e.g. "recipes/index.html"
    url: str                            # its path on the site, e.g. "/recipes/"
    title: str                          # <title>
    subtitle: str                       # the header's line beside CTPLAY
    toc_skip: frozenset[str] = frozenset()      # heading ids left out of the menu


PAGES: tuple[Page, ...] = (
    Page(GUIDE, "index.html", "/", "CTPlay user guide", "USER GUIDE", frozenset({"changes-by-feature"})),
    Page(RECIPES, "recipes/index.html", "/recipes/", "CTPlay recipes", "RECIPES"),
)


# Symbols github-slugger keeps: the circled and squared Latin letters (Unicode's Alphabetic, category So).
SLUG_LETTER_SYMBOLS = ((0x24B6, 0x24E9), (0x1F130, 0x1F149), (0x1F150, 0x1F169), (0x1F170, 0x1F189))


def _slug_keeps(ch: str) -> bool:
    cat = unicodedata.category(ch)
    return (ch in "- " or cat[0] in "LM" or cat in ("Nd", "Nl", "Pc")
            or cat == "So" and any(a <= ord(ch) <= b for a, b in SLUG_LETTER_SYMBOLS))


def slug(text: str, seen: dict[str, int]) -> str:
    """GitHub's anchor for a heading's plain text, as github-slugger 2.0 makes it: letters, marks, digits, _ and -
    kept (not ½ or ²), spaces to -; a repeat gets -1, -2, ..., skipping any slug already taken ("Bass", "Bass",
    "Bass 1" → bass, bass-1, bass-1-1). Characters newer than the slugger's Unicode tables may differ."""
    base = "".join(c for c in text.lower() if _slug_keeps(c)).replace(" ", "-")
    s = base
    while s in seen:
        seen[base] += 1
        s = f"{base}-{seen[base]}"
    seen[s] = 0
    return s


def _plain(inline: Token) -> str:
    return "".join(c.content for c in inline.children or [] if c.type in ("text", "code_inline")).strip()


def _html(content: str) -> Token:
    t = Token("html_block", "", 0)
    t.content = content
    return t


def _inline(content: str) -> Token:
    t = Token("html_inline", "", 0)
    t.content = content
    return t


def parse_hint(comment: str) -> list[list[tuple[str | None, bool]]]:
    """A pad hint, `<!-- pads: R / R ... [; key: text] -->`: per row 8 tokens, a colour letter (uppercase = bright) or
    · (free); the optional key replaces PAD_KEY under the table."""
    m = HINT.match(comment.strip())
    if not m:
        raise BuildError(f"not a pad hint: {comment.strip()!r}")
    rows = []
    for row in m.group(1).split(";", 1)[0].split("/"):
        tokens = row.split()
        if len(tokens) != 8 or any(t != FREE and (len(t) != 1 or t.lower() not in PAD_COLOURS) for t in tokens):
            raise BuildError(f"pad hint row {row.strip()!r}: needs 8 tokens, each one of {PAD_COLOURS} "
                             f"(uppercase = bright) or {FREE}")
        rows.append([(None, False) if t == FREE else (t.lower(), t.isupper()) for t in tokens])
    return rows


def hint_key(comment: str) -> str | None:
    """The hint's own key line (`; key: text`), or None for PAD_KEY."""
    m = HINT.match(comment.strip())
    rest = m.group(1).split(";", 1)[1].strip() if m and ";" in m.group(1) else None
    if rest is None:
        return None
    if not rest.startswith("key:") or not rest[4:].strip():
        raise BuildError(f"pad hint {comment.strip()!r}: after ';' write 'key: <the line under the table>'")
    return rest[4:].strip()


def _rows(tokens: list[Token], start: int, end: int) -> list[tuple[str, list[tuple[Token, Token]]]]:
    """The table's rows between its open and close tokens: (thead / tbody, [(cell open, cell inline)])."""
    rows, part = [], ""
    for i in range(start, end):
        t = tokens[i]
        if t.type in ("thead_open", "tbody_open"):
            part = t.type[:5]
        elif t.type == "tr_open":
            rows.append((part, []))
        elif t.type in ("th_open", "td_open"):
            rows[-1][1].append((t, tokens[i + 1]))
    return rows


def _is_pad_table(rows) -> bool:
    head = [inline.content.strip() for _, inline in rows[0][1]] if rows and rows[0][0] == "thead" else []
    return len(head) >= 9 and all(h.isdigit() for h in head[-8:])


def _pad_tables(tokens: list[Token]) -> list[Token]:
    """Drop the pad hints and mark their tables (meta["pads"]), with each pad cell's class set from its hint."""
    out: list[Token] = []
    hint = None
    for i, tok in enumerate(tokens):
        if tok.type == "html_block" and HINT.match(tok.content.strip()):
            hint, key = parse_hint(tok.content), hint_key(tok.content)
            if i + 1 >= len(tokens) or tokens[i + 1].type != "table_open":
                raise BuildError(f"pad hint {tok.content.strip()!r} is not directly above a table")
            continue
        if tok.type == "table_open":
            end = next(j for j in range(i, len(tokens)) if tokens[j].type == "table_close")
            rows = _rows(tokens, i, end)
            name = " | ".join(inline.content.strip() for _, inline in rows[0][1])
            if _is_pad_table(rows) != (hint is not None):
                raise BuildError(f"table '| {name} |': " + ("a pad table needs a pad hint directly above it"
                                                           if hint is None else "a pad hint on a table that is not a pad table"))
            if hint is not None:
                body = [cells for part, cells in rows if part == "tbody"]
                if len(hint) > len(body):
                    raise BuildError(f"table '| {name} |': the pad hint has {len(hint)} rows, the table {len(body)}")
                for hrow, cells in zip(hint, body):
                    if len(cells) != 9:
                        raise BuildError(f"table '| {name} |': a pad row needs a label and 8 pads")
                    cells[0][0].attrSet("class", "rl")
                    for (colour, bright), (cell, inline) in zip(hrow, cells[1:]):
                        if (colour is None) != (inline.content.strip() == FREE):
                            raise BuildError(f"table '| {name} |': pad {inline.content.strip()!r} and its hint disagree "
                                             f"on a free pad ({FREE})")
                        cell.attrSet("class", "pad free" if colour is None else f"pad {colour}" + (" on" if bright else ""))
                        if colour is None:          # a blank square reads as a free pad; · stays in the Markdown
                            cell.attrSet("aria-label", "free pad")
                            inline.content, inline.children = "", []
                tok.meta = {"pads": True, "key": key}
                hint = None
        out.append(tok)
    return out


def _link(href: str, base: Path) -> str:
    """A link as the site writes it: a site page's file -> that page's path, any other file -> its page on GitHub."""
    if href.startswith("#") or re.match(r"[a-z][a-z0-9+.-]*:", href):
        return href
    path, _, frag = href.partition("#")
    target = (base / path).resolve()
    for pg in PAGES:
        if target == pg.src.resolve():
            return pg.url + ("#" + frag if frag else "")
    try:
        rel = target.relative_to(ROOT)
    except ValueError:
        raise BuildError(f"link {href!r}: outside the repository (the page links files on GitHub)") from None
    return REPO_URL + rel.as_posix() + ("#" + frag if frag else "")


RAW_HREF = re.compile(r'(<a\s[^>]*?\bhref=")([^"]*)(")', re.I)
RAW_IMG = re.compile(r'<img\s[^>]*?\bsrc="(?![a-z][a-z0-9+.-]*:)([^"]*)"', re.I)


def _raw_html(content: str, base: Path) -> str:
    """Raw HTML in the Markdown: its links are rewritten as Markdown's are; a local <img> cannot be embedded."""
    m = RAW_IMG.search(content)
    if m:
        raise BuildError(f"<img src=\"{m.group(1)}\">: write a local image as Markdown (![text](path)) so it is embedded")
    return RAW_HREF.sub(lambda m: m.group(1) + html.escape(_link(html.unescape(m.group(2)), base)) + m.group(3), content)


IMAGE_TYPES = {".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".svg": "image/svg+xml"}


def _embed_image(img: Token, base: Path) -> None:
    """A local image (screenshots in docs/images/, taken at 2x) into the page itself: a data URI with a 2x descriptor,
    so the browser shows it at half its pixels and the page stays one file. Remote images are left alone."""
    src = str(img.attrGet("src"))
    if re.match(r"[a-z][a-z0-9+.-]*:", src):
        return
    path = base / src
    mime = IMAGE_TYPES.get(path.suffix.lower())
    if mime is None:
        raise BuildError(f"{src}: not an image type the guide embeds ({', '.join(IMAGE_TYPES)})")
    if not path.is_file():
        raise BuildError(f"{src}: image not found (from {base})")
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    img.attrs.pop("src", None)
    img.attrSet("srcset", f"data:{mime};base64,{data} 2x")


def render(md: str, base: Path = GUIDE.parent) -> Rendered:
    parser = MarkdownIt("commonmark", {"html": True}).enable("table")
    tokens = _pad_tables(parser.parse(md))
    seen: dict[str, int] = {}
    toc: list[tuple[int, str, str]] = []
    out: list[Token] = []
    in_section = False
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open":
            inline = tokens[i + 1]
            level, text = int(tok.tag[1]), _plain(inline)
            hid = slug(text, seen)
            tok.attrSet("id", hid)
            if level in (2, 3):
                toc.append((level, hid, text))
                # One flex item for the text (h2 / h3 are flex rows), whatever inline markup it holds.
                inline.children[:0] = [_inline("<span>")]
                inline.children += [_inline("</span>"), _inline(
                    f'<a class="hlink" href="#{hid}" aria-label="Link to this section">{LINK_ICON}</a>')]
            if level == 2:
                if in_section:
                    out.append(_html("</section>\n"))
                out.append(_html('<section class="panel">\n'))
                in_section = True
        elif tok.type == "inline":
            for c in tok.children or []:
                if c.type == "link_open":
                    c.attrSet("href", _link(str(c.attrGet("href")), base))
                elif c.type == "image":
                    _embed_image(c, base)
                elif c.type == "html_inline":
                    c.content = _raw_html(c.content, base)
        elif tok.type == "html_block":
            tok.content = _raw_html(tok.content, base)
        if tok.type == "table_open":
            pads, key = bool(tok.meta.get("pads")), tok.meta.get("key")
            out.append(_html('<div class="pads">\n' if pads else '<div class="table">\n'))
        out.append(tok)
        if tok.type == "table_close":
            out.append(_html("</div>\n" + (f'<p class="padkey">{html.escape(key)}</p>\n' if key else PAD_KEY if pads else "")))
    if in_section:
        out.append(_html("</section>\n"))
    return Rendered(parser.renderer.render(out, parser.options, {}), toc)


def site_version() -> str:
    """The header's version: the newest published release ("1.0 beta 2"), the one the uploader lists first."""
    from . import uploader
    rel = uploader.releases()
    if not rel:
        raise BuildError("no published manifest has a release: the header shows the newest release")
    return rel[0]["release"]


def page(r: Rendered, pg: Page, version: str) -> str:
    """One whole page: the template (read from TEMPLATE when called) with the page's title, the version, menu and body."""
    template = TEMPLATE.read_text(encoding="utf-8")
    missing = [p for p in PLACEHOLDERS if p not in template]
    if missing:
        raise BuildError(f"{TEMPLATE}: placeholder(s) {', '.join(missing)} not found")
    toc = "".join(f'<li class="l{level}"><a href="#{hid}">{html.escape(text)}</a></li>'
                  for level, hid, text in r.toc if hid not in pg.toc_skip)
    for key, value in (("{{title}}", html.escape(pg.title)), ("{{subtitle}}", html.escape(pg.subtitle)),
                       ("{{version}}", html.escape(version)), ("{{toc}}", toc), ("{{source}}", pg.src.name),
                       ("{{repo}}", PUBLIC_REPO), ("{{body}}", r.body)):
        template = template.replace(key, value)
    return template


def render_pages(version: str) -> dict[str, str]:
    """Every page of the site's Markdown, {site file: html}."""
    return {pg.out: page(render(pg.src.read_text(encoding="utf-8"), pg.src.parent), pg, version) for pg in PAGES}


HREF = re.compile(r'\bhref="([^"]*)"')
ID = re.compile(r'\bid="([^"]*)"')
SITE = "https://site/"          # a stand-in origin: links are resolved as a browser would, then mapped back to files


def _site_file(path: str) -> str:
    """A path on the site -> its file in the site folder: "/" -> "index.html", "/recipes/" -> "recipes/index.html"."""
    path = urllib.parse.unquote(path).lstrip("/")
    return path + "index.html" if path == "" or path.endswith("/") else path


def check_links(pages: dict[str, str], missing_ok: tuple[str, ...] = ()) -> list[str]:
    """Every link from a page to the site itself (another page, or an #id in one) must find its page and the element
    with that id. Links to other sites are not fetched. A target page under a `missing_ok` prefix that is not in
    `pages` is accepted unchecked: those links are returned (once each). Any other miss: BuildError naming them all."""
    ids = {key: {html.unescape(i) for i in ID.findall(text)} for key, text in pages.items()}
    broken: list[str] = []
    unchecked: list[str] = []
    for key, text in pages.items():
        for raw in HREF.findall(text):
            href = html.unescape(raw)
            url = urllib.parse.urlsplit(urllib.parse.urljoin(SITE + key, href))
            if f"{url.scheme}://{url.netloc}/" != SITE:
                continue
            target = _site_file(url.path)
            if target not in pages:
                if missing_ok and target.startswith(missing_ok):
                    if href not in unchecked:
                        unchecked.append(href)
                else:
                    broken.append(f"{key}: {href}")
            elif url.fragment and urllib.parse.unquote(url.fragment) not in ids[target]:
                broken.append(f"{key}: {href}")
    if broken:
        raise BuildError("links that point nowhere:\n  " + "\n  ".join(broken))
    return unchecked


def write_site(root: Path | None = None, bins: dict[str, Path] | None = None, docs_only: bool = False) -> list[Path]:
    """The whole site in root/public/: the Markdown pages and (unless docs_only) the public uploader's pages, checked
    together before anything is written. Then everything in root but dot-files (wrangler's local state) is replaced.
    The default root is build/site/, the folder to deploy, always a whole site; docs_only builds no uploader, so its
    default is build/site-docs/ (a deploy from there would drop /uploader/)."""
    from . import uploader
    pages = render_pages(site_version())
    if not docs_only:
        pages.update({"uploader/" + k: v for k, v in uploader.public_pages(bins).items()})
    for href in check_links(pages, ("uploader/",) if docs_only else ()):
        print(f"note: {href} not checked (--docs builds no uploader: never deploy this folder)")
    root = Path(root) if root is not None else BUILD / ("site-docs" if docs_only else "site")
    for old in root.iterdir() if root.exists() else ():
        if old.name.startswith("."):
            continue
        if old.is_dir() and not old.is_symlink():
            shutil.rmtree(old)
        else:
            old.unlink()
    written = []
    for key, text in pages.items():
        path = root / "public" / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--docs"]):
        sys.exit("usage: python -m playbuild.guide [--docs]   (--docs: the guide and recipes only, no firmware needed)")
    for p in write_site(docs_only=sys.argv[1:] == ["--docs"]):
        print(p)
