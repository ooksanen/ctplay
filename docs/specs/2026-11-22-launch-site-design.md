# The launch site: one site at ctplay.ctctrl.com (design)

2026-11-22. Part of `followups.md`, "CTPlay 1.0 beta: the checklist": the "Docs and site", "Feedback and the site"
and "Installing" items that need no public repo. The public repo, its publish script, Discussions and the deploy itself
are later steps (non-goals below).

## Why

At launch a new user meets the guide, the recipes and the uploader. Today they are pre-launch: the guide carries the
PL01–PL21 history no public user ever had, says builds are not published, and links to the private repo; the recipes
are split between the guide and an unbuilt draft; the site build still makes the vote page (decided against on
2026-11-07); and the guide and the uploader are built by two commands that must run in a set order. The goal: one
command builds the whole public site, current for the beta, and the build itself checks that the pages link up.

## Decided (user, 2026-11-22)

- **Everything CTPlay lives under `ctplay.ctctrl.com`**, one site: `/` the guide, `/recipes/` the recipes,
  `/uploader/` the patching uploader (and `/uploader/<MARKER>/` per release, as built today).
- **All recipes move to `/recipes/`**, the guide links there. Eight recipes (three in the guide today, five in
  `docs/recipes.md`) were run on the device in PL21's TEST.md (section L) and work. The ninth, "A snare roll every 4th
  bar, and a fill when you want it", was not: it gets rows in **PL22's TEST.md** (a new section, run with PL22's device
  test) and ships with the others.
- **The recipes get text-only additions**, from the PL21 L result: every page named with its pad ("the Melody page
  (Shift + pad 28)"), the ▼ ▲ buttons mentioned in parentheses where a page can also be reached with them, and long
  steps broken into smaller ones. No images or diagrams in this pass. The notes each step says you hear do not change.
- **Every mention of the vote leaves the docs and pages**: the template's two vote links, `slim/README.md`,
  `site/README.md` and the repo's `CLAUDE.md`. (The vote's design spec and code stay as the record.)
- **Approach A:** one build command renders every page with the one template and writes the uploader into the same
  folder; a link check runs over the finished folder.

## Approaches considered

- **A. One build for the whole site (picked).** `slimbuild.guide` renders a list of Markdown pages with
  `guide_template.html` and then writes the public uploader into the same output. One command, no order rule, and the
  link check sees every page.
- **B. Separate commands, a third for recipes.** Less code, but three commands in a set order, and no natural home for
  a check of links between pages.
- **C. A site generator (MkDocs or similar).** Dropped: it would replace `guide.py`'s pad tables, layout hints and
  embedded images and add dependencies, for two pages.

## Goals

1. `../.venv/bin/python -m slimbuild.guide` (from `slim/`) writes the whole site to `build/site/public/`:
   - `index.html` from `docs/user-guide.md`;
   - `recipes/index.html` from `docs/recipes.md`;
   - `uploader/index.html` and `uploader/<MARKER>/index.html` (today's `uploader.write_public`).
   Nothing else: no `vote/`, no `functions/`, `lib/` or `schema.sql` (they only served the vote).
2. **Every page from the one template** (`guide_template.html`), each with its own side menu (its own h2 / h3), its own
   `<title>` and header subtitle ("USER GUIDE" / "RECIPES"), and the same header version.
3. **Navigation between the pages:** the header or menu links the guide, Recipes and the uploader on every rendered
   page; the vote link goes. The recipes page has a "back to the guide" link at the top.
4. **Links between pages.** The Markdown keeps file-relative links so it reads on GitHub: `recipes.md#x` in the guide,
   `user-guide.md#x` in the recipes. The build maps a link to a file that is a site page to that page's path
   (`/recipes/#x`, `/#x`); any other relative link still becomes a repo link (`_repo_link`, as today). Site paths are
   written root-relative (`/recipes/`), since the site sits at the domain's root.
5. **A link check over the finished folder.** For every rendered page and the uploader pages: each link to a site path
   or an in-page `#id` must find the page and an element with that id; otherwise the build fails and names the link
   and the page. External links (`https:`, `mailto:`) are not fetched.
6. **The header version comes from the release, not the guide.** It is the `release` of the newest published manifest
   that has one (`uploader.releases()[0]`, the same source the uploader lists), shown as e.g. "1.0 BETA 2". **My
   call:** a committed `firmware/<MARKER>/manifest.json` with a `release` counts as published, the rule the uploader
   already uses; no git tag lookup (the build must work in a clone without tags). PL22's manifest is committed, so the
   site says beta 2 today; it is deployed only at launch, after PL22's device run. The `PLnn` version-row parsing and
   its error go.
7. **The recipes page.** The three guide recipes ("A melody from a 9th chord", "A bass line", "A riff that drifts
   against the beat") move into `docs/recipes.md` under a "Melodies and bass lines" section; the two intros merge into
   one (start state, Pages, Write / the draft, Undo: the guide's wording on the draft is the current behaviour). The
   DRAFT comment at the top of `recipes.md` goes; the section-to-recipe table moves out of the page (into this spec's
   "Try it" list below, or a comment that is not rendered).
8. **The guide links its recipes.** The guide's Recipes section shrinks to two lines linking `/recipes/`. Each feature
   section in the table below ends with one line, `Try it: [recipe](recipes.md#…)`:

   | Guide section | Recipe |
   |---|---|
   | Voice leading | A chord progression that moves smoothly |
   | Chords in step entry, Pattern strum | Off-beat chord stabs |
   | Arpeggiator | An arpeggio you can play over |
   | Drum Pattern tools | A beat from four drums |
   | The Repeat page | Hi-hats played live |
   | Euclidean fills | A riff that drifts against the beat |
   | Melodic generator | A melody from a 9th chord, A bass line |
   | Trig conditions | A snare roll every 4th bar, and a fill when you want it |

   One "Try it" per top feature section (or the subsection named), not on every subsection.
9. **The guide's text, current for a published beta:**
   - **No version history:** the intro's paragraph on versions, the Versions table and every
     `<sup>[n](#h-…)</sup>` (53 today) go. "Changes by feature" stays as a heading with one sentence (what a later
     release changes in a section is noted here, numbered from 1), so the system restarts at beta; the menu and the
     intro's Contents line drop it until it has a note. A "Releases" line links the public repo's GitHub Releases.
   - **Installing:** the uploader is at `ctplay.ctctrl.com/uploader/` (drop "will be … until then you build it").
     Add the **stay on 1.2.1** warning: Novation Components may offer a newer official firmware; CTPlay installs only
     over 1.2.1 build 4486, so a user who updates can't install CTPlay until CTPlay supports that build.
   - **Back up and go back:** `#going-back-to-the-official-firmware` keeps its id (the uploader links it). It gains a
     short "back up first" paragraph (Components for projects / samples, copy the SD card), so the one section a
     worried user looks for has both.
   - **Building from source:** for developers only. Builds are published (the uploader); the version file is the
     newest release's, not a hard-coded `PL21`; the "try the public uploader locally" note drops the order rule.
   - **Feedback:** the footer links GitHub Discussions (Ideas, Q&A) and Issues on the public repo.
10. **One setting for the public repo.** `PUBLIC_REPO = "https://github.com/ooksanen/ctplay"` (the name decided on
    2026-11-07). Releases, Discussions and Issues links derive from it. `REPO_URL` (file links into the tree) stays a
    separate setting with today's value: its branch and paths depend on the open "what the public tree holds"
    decision, and is changed in that step.
11. **Docs about the site:** `site/README.md` rewritten for one static site at `ctplay.ctctrl.com` (build, try
    locally with `python3 -m http.server`, first deploy with `wrangler pages deploy public --project-name ctplay`,
    the custom domain); the vote's sections go. `slim/README.md`, the repo's `CLAUDE.md` (the commands line: the site
    build, no order rule, no vote) and the uploader module's docstring updated to match. The guide-structure memory
    updated once done.
12. **The vote code stays, out of the site.** **My call:** `vote.write_site` keeps working but writes to
    `build/vote/` instead of `build/site/`, so it can never empty or add to the public site; it takes its header
    version from the same release source as the guide (`VERSION_ROW` is gone). `python -m slimbuild.guide` no longer
    calls it. `test_vote.py` and `test_vote_site.py` keep passing with the path change; `test_guide.py`'s checks of
    the vote template stay if they still hold, and its "links to the vote page" test is inverted (no page links
    `/vote/`).
13. **The trig-conditions recipe in PL22's TEST.md:** a new section (after the existing ones, before Results) with
    rows for each step of the recipe, written as section L's rows are (start: a new empty project, Play; one to three
    presses per row; what you hear). The time estimate at the top of the plan grows to match.

## Non-goals

- The public repo, its publish script and pre-push hook, the issue template, turning on Discussions.
- Deploying the site or setting up the domain (launch day; the README carries the steps).
- Publishing PL22 or changing the uploader page itself (its UI, its release list rule of "newest two").
- Hosting older releases' `/uploader/<MARKER>/` pages once they drop out of the newest two (the multi-page site work
  noted in followups; at launch both beta 1 and beta 2 are among the newest two).
- New recipes, images or diagrams in the recipes, or changing what a recipe plays.

## Anti-goals

- A page that names a PL build as something a user had: the public pages speak of releases ("1.0 beta 2"); markers
  appear only where the device shows them (the uploader's "Identify the device").
- The old name of the Master FX view anywhere on the site.
- Novation's bytes in the site output (the uploader already holds only CTPlay's).
- A link in the built site that points nowhere.

## Constraints

- The Markdown stays the only source and stays readable on GitHub (file-relative links, GitHub-compatible heading ids:
  `slug` is unchanged).
- The uploader part needs `stock/` and each listed release's `.bin` built from its tag (`build/<MARKER>/…bin`), as
  `write_public` does today. **My call:** the full site build requires them and fails clearly without them; a
  `--docs` flag builds only the Markdown pages (for doc edits without firmware), and then the link check accepts links
  to `/uploader/` without the page (it says so in its output).
- `slimbuild.guide` keeps its name (the command is referenced in CLAUDE.md, READMEs and specs); `uploader --public`
  keeps working on its own.
- Existing tests in `tests/test_guide.py` change where they assert removed things (the version row, the vote link);
  every rule they check that stays (slugs, pad tables, images, guarded storage, contrast) keeps its test.

## Left to the builder

- The exact header / menu markup for the page links, and where "back to the guide" sits, in the template's style.
- How the page list is declared (a small table in `guide.py`), and how `Rendered` carries a page's title.
- The wording of the new guide paragraphs (plain short sentences, per the guide's style), and of the merged recipe
  intro.
- Test names and the split between unit tests (link mapping, the check, the version source) and one build test.
