# The public CTPlay repo: what it holds and how it is made (design)

Status: approved by the user, 2026-11-23 (after a builder check). Checklist: `docs/followups.md`, "CTPlay 1.0 beta: the checklist", "The public repo".

## Why
CTPlay goes public with 1.0 beta 2 (PL22). The dev repo (`ooksanen/ctplay`, to become `ctplay-dev`) cannot go public
as it is: `slim`'s history holds the old `main` (tag `main-pre-rc0.5`, through the bridge merge `ca812d1`), and with it
the old name of the Master FX view, which upstream removed from its history. So the public repo starts from one fresh
commit of a chosen tree, and each later release adds one more commit (as upstream does with its `publish_rc.py`).

The user wants the public repo to be **readable and focused** (CTPlay, not upstream's 264 builds) and **open**: it
honours the work of Ghillermo's CIRCUIT-HACKS-RC and the projects under it, and gives others what could help them
(the stock firmware map, the device rules learnt the hard way, the research, the interfaces).

## Goals
- A public tree that builds and tests CTPlay on its own, after `tools/setup_dev.py`.
- What goes public is decided by one include list in the dev repo, and reviewed by the user in a staging folder before
  anything is pushed.
- No dev commit ever reaches the public repo; one public commit per release.
- Clear credit: upstream's code stays upstream's, unchanged, under its licence and notice.

## Non-goals
- Publishing upstream's builds, its notes (`docs/NOTAS.md`) or its 264 build scripts. They stay in upstream's repo and
  in the English fork (`ooksanen/CIRCUITS-HACKS-RC`), which the public README links.
- Rebuilding older PL builds in the public repo (they rebuild from their tags, in dev only).
- The site's deploy, GitHub Discussions, Releases and the issue template (their own checklist items). The script only
  prepares the commit and, when told, pushes it.

## Anti-goals (a failure even if it works)
- The old name anywhere in the public tree or its history.
- Any Novation code or binary in the tree: the official firmware, a `.syx`, a `.bin`, device dumps, the listing
  `re/app.asm`. (They are fetched to the user's machine by `setup_dev.py`, never stored.)
- A public commit made by hand, or one whose tree came from anything but the include list.
- A merged public pull request silently undone by the next release.

## Approaches considered
1. **A staging folder filled by the publish script (chosen).** The script builds the public tree from the dev tree and
   an include list into `~/work/ctplay` (its own git repo, later the public repo's clone), commits, and pushes
   nothing. The user reviews it there; fixes go into dev and the script runs again. The review sees exactly what will
   be published, and every release is made the same way.
2. **Hand-assembled folder, tweaked in place, the script carrying edits back.** Easier first review, but two sources
   of truth; a later release would have to merge the folder's edits. Rejected.
3. **The whole upstream tree + `slim/`.** Easiest upstream merges, but the repo is mostly upstream's builds and
   Spanish notes, and it duplicates upstream's own public repo. Rejected (user, 2026-11-23: `slim/` and the build tools).

Docs: of three scopes (users only / users + research / everything) the user chose **users + research** (2026-11-23).

## The public tree
The layout is dev's own, so the build needs no changes and a public pull request applies to dev unchanged:

    README.md  LICENSE  NOTICE.md  CONTRIBUTING.md  CLAUDE.md  .gitignore   (from slim/public/, see below)
    tools/     upstream's files the build needs, unchanged
    stock/SHA256SUMS.txt
    slim/      CTPlay

**From upstream (unchanged, at their upstream paths):** `tools/ct_fw.py`, `thumb.py`, `emu_sc05.py`, `emu_sc08.py`,
`gen_listing.py`, `setup_dev.py`, and what `setup_dev.py` imports: `patch_official.py`, `verify_builds.py`; also
`tools/requirements.txt`, `tools/dsptool/` (`setup_dev.py` builds it unless `--no-dsptool`) and `stock/SHA256SUMS.txt`.
The list is the import closure of slim's code into `tools/`; the script recomputes it and fails if a needed module is
not listed (so a new import cannot break the public build unnoticed). `NOTICE.md` names the upstream commit they came
from.

**From `slim/`:**
- Included: `slimbuild/` (but not the vote: `vote.py`, `vote_template.html` and whatever else only the vote uses),
  `features/`, `runtime/`, `stock/` (`symbols.toml`, `memory.toml`), `site/`, `pages/`, `tests/` (but not
  `test_vote*.py`, `test_tags.py`), `save_layout.lock`, `pytest.ini`, `requirements.txt`, `setup_toolchain.py`,
  `.gitignore`, `README.md`.
- `versions/`: every version file. The tests build PL05–PL21 from the current sources as feature sets (16
  fixtures in `tests/conftest.py`), so they stay; each one's guard comment already says it is not the published build.
  The released bytes of every build are in its `firmware/<MARKER>/manifest.json`.
- `fork/ct_uploader.en.html`: the dev uploader's template (`slimbuild.uploader` without `--public`, which flashes
  finished `.syx` files: contributors need it to try their own builds). The fork's English translation of upstream's
  `tools/ct_uploader.html`, credited in `NOTICE.md`. The closure check covers it (a file `slimbuild` reads, not imports).
- `firmware/<MARKER>/`: every build's `manifest.json` and test plans (`TEST*.md`, with their results): the device
  history is part of the research.
- `docs/`: `user-guide.md`, `recipes.md`, `ui-map.md`, `resources.md`, `images/`, `layouts/`, `specs/`,
  `investigations/`, `research/`.
- Left out: `docs/plans/` (step-by-step build scripts the code supersedes), `docs/followups.md`, `docs/candidates.md`
  (the roadmap moves to GitHub Discussions), `docs/vote.toml`, the vote's design and mockup and the first guide
  design (the launch-site design replaces it), `spike/`, `build/`.

**New files, kept in dev under `slim/public/` and copied to the public tree's top level:**
- `README.md`: what CTPlay is, a link to the site (guide, recipes, uploader), "Built on" (upstream, the English fork,
  userx14's reverse engineering), how to set up, build and test, the layout, the notice that CTPlay is not affiliated
  with Novation and that trademarks belong to Focusrite Audio Engineering, and "never a finished firmware file:
  bring your own".
- `LICENSE`: MIT, upstream's text, with Ghillermo's copyright line kept and ours added.
- `NOTICE.md`: credits. Ghillermo / CIRCUIT-HACKS-RC (the base, the tools under `tools/`, the uploader's patching
  method, the device rules found there); userx14 / circuittracksreverseengineering (the device dumps the emulators run
  on, the Components validator the tests use); capstone, unicorn, dsp56300 (fetched, their licences); the Arm GNU
  Toolchain (fetched). Which upstream commit `tools/` came from.
- `CONTRIBUTING.md`: how a feature is made (`feature.toml`, hooks, `[[saved]]` fields and the lock, byte patches),
  the device rules every change keeps, the tests to run, "emulation passing is not device passing", what a bug report
  needs, and that a merged pull request is brought into dev before the next release.
- `slim/docs/hacking.md` (in `slim/docs/`, not `slim/public/`, so the guide's link check sees it): **Hacking the
  Circuit Tracks**, the device knowledge in one place, each item crediting who found it: the platform (STM32F745,
  DSP56724), the controller and its routes, the LED palette and the animated codes, the DSP service tick and the
  semaphore hang, the free RAM above the heap (SL01D), the phantom pad press through the 74HC4051 mux, the
  DSP56300 assembler traps, the rate limits, the bootloader and the version marker rule; pointers to
  `stock/symbols.toml` and `memory.toml`. Most of it is in this repo's `CLAUDE.md` today; the doc is written for people.
- `CLAUDE.md`: a short public one for contributors who use Claude Code: the layout, the commands, the device rules
  (pointing at `hacking.md`), no private remotes or dev workflow.

`slim/README.md` becomes public-ready in dev: setup and commands for the public layout; the long version history
moves out (the dev-only parts, such as "rebuild from git tag", go to this repo's `CLAUDE.md`).

## The publish script
`slim/publish/publish.py` (dev only; run from `slim/` as `../.venv/bin/python -m publish …` or similar, builder's
call), with its include list `slim/publish/include.toml`. Two commands:

**`stage <MARKER>`** builds the release's tree into the staging folder and commits it there.
1. Takes a dev commit (default HEAD). Refuses if the dev working tree is dirty (the tree must be a commit); if that
   commit has a version file numbered above the release (work on the next build has started: unreleased features
   would go public early; publish at the release's own commit, or an image-neutral commit after it, as now for PL22,
   whose public-ready commits follow its tag); or if the staging folder has uncommitted changes or commits not made by
   the script (a hand edit would be lost). `<MARKER>` must have a `release` and a `firmware/<MARKER>/manifest.json`.
2. Takes files from the dev commit (`git archive` / `git show`), never from the working directory, so nothing
   ignored or untracked can slip in.
3. Checks the tree (any failure stops the stage):
   - **The old name:** the old name is never written in the dev or public repo. The script holds the SHA-256 of its
     normalised spelling (lower case, letters and digits only; 6 characters):
     `f9f439d35d1e2af9654e5c1a282ecd1a6af0cf1bfc80f8bd08ecaefbdee56263`, and compares every 6-character window of
     each file's normalised text, and of each path, against it. The same check runs as a dev test over every file git
     tracks in the dev tree (`slim/`, `tools/`, `docs/`, top level), so the name cannot creep in between releases.
   - **No Novation bytes:** no `.syx`, `.bin`, `.ncs`, `.ncsp`, `.asm` dumps; no file over a size limit (e.g. 1 MB)
     unless listed; no file whose 32-byte windows occur in the stock image (the uploader's ADD check, applied to
     binaries).
   - **Private details:** no home-folder paths (Linux or Windows user folders), no e-mail addresses but the ones allowed (the
     public identity below, `noreply@anthropic.com` in co-author lines, upstream's noreply address).
   - **The upstream import closure** as above.
   - **Links:** relative markdown links into files left out are listed for the user (a report, not a failure).
4. Proves the tree works: in a temporary copy with the ignored setup linked in (`ext`, `re`, `.venv`, `ctre`,
   `stock/*.bin|syx`, as for a dev worktree), builds the release and checks it against `firmware/<MARKER>/manifest.json`
   (byte-identical), then runs the fast tests (`-m "not emu"`). Optionally (`--full`) the emulation tests.
5. **The public identity (user, 2026-11-23):** author and committer `ooksanen
   <1029398+ooksanen@users.noreply.github.com>`, set by the script (`GIT_AUTHOR_*` / `GIT_COMMITTER_*`), never the dev
   clone's identity, which holds a personal address. `LICENSE`'s added line: `Copyright (c) 2026 ooksanen`.
   Commits the tree in the staging repo with `git commit-tree`: parent = the public `main`'s tip (none for the first
   release), message `CTPlay <release> (<MARKER>)` plus a trailer `Dev-Commit: <sha>`. Tags it `v<semver>` (from
   `release`: "1.0 beta 2" → `v1.0.0-beta.2`). The staging repo's `main` points at it. Nothing is pushed.

**`push <MARKER>`** pushes the staged commit and tag to the public repo, after:
- the remote check: `origin` of the dev clone is not the public repo (the rename has happened) and the staging
  repo's `public` remote is;
- **public changes are in dev:** for every public commit after the last release commit (a merged pull request), its
  diff must reverse-apply to the staged tree (`git apply --reverse --check`): its changes are already there. If not,
  the push stops and names the commits to bring into dev first.
- the user's confirmation on the terminal.

**A `pre-push` hook** in the dev clone (installed by `fork/setup.sh`) refuses any push whose remote URL is the public
repo. The script pushes from the staging repo, so the hook never stands in its way.

## The site
The deployed site (guide, recipes, uploader with `/uploader/<MARKER>/` for the newest two releases) is built **in dev**,
where the release tags are: the uploader patches from each release's tag build. The public tree builds the guide and
the recipes (`slimbuild.guide --docs`), so a doc pull request can be checked there; site tests that need a release's
tag build skip without it.

## Changes in dev
- `slimbuild/guide.py` `REPO_URL` → `https://github.com/ooksanen/ctplay/blob/main/` (the public repo; paths are the
  same), and its 3 asserts in `tests/test_guide.py`.
- `checks.check_marker` treats a missing upstream `firmware/` as "no upstream markers" (the public tree has none;
  slim's markers are `SL` / `PL` only, so no clash is possible).
- Tests that need dev-only things (tags, upstream's `firmware/`, the vote) skip cleanly without them.
- `fork/setup.sh` installs the `pre-push` hook; `CLAUDE.md` names `ctplay-dev`, the public repo and the publish flow.

## Order at launch
1. Build the script; `stage PL22`; the user reviews `~/work/ctplay`; fixes in dev; stage again until it is right.
2. Rename `ctplay` → `ctplay-dev` on GitHub; `git remote set-url origin …/ctplay-dev.git` (covers every worktree);
   `fork/setup.sh` again for the hook.
3. **The branches** (before the folder renames; from the flatten spec, `2026-11-23-flatten-design.md`): dev's `main`
   (upstream + the English translations) moves out and `slim` becomes `main`.
   - Clone the public fork into its own folder, `~/work/circuit-hacks-rc` (remotes `fork` and `upstream`; `bash
     fork/setup.sh` there, `main`'s own copy), then `git worktree remove` the old worktree `~/work/circuit-hacks-oo-main`.
   - In dev: keep a copy, `git update-ref refs/archive/main main`; on GitHub make `slim` the default branch of
     `ctplay-dev` (GitHub refuses to delete the default branch); delete `main` (`git branch -D main`,
     `git push origin :main`), once `git -C ~/work/circuit-hacks-rc rev-parse main` equals dev's `git rev-parse main`.
   - Rename: `git branch -m slim main`, `git push origin -u main`; on GitHub make `main` the default branch; then
     `git push origin :slim`.
   - The PL tags, the staging folder and the publish script are unaffected (they use commits, not branch names).
4. **Rename the local folders the same day** (between Claude Code sessions, not from one running inside them), so
   local and GitHub names match:
   - `~/work/circuit-hacks-oo` → `~/work/ctplay-dev` (the dev clone, on `main` after step 3); `~/work/ctplay` stays
     the staging folder (the public repo's clone). `~/work/circuit-hacks-oo-main` is gone (step 3).
   - What holds the old path: the worktree record (`git worktree repair` / `remove`), the absolute `ctre` link
     (→ `ext/circuittracksreverseengineering`), `.venv`'s script headers (recreate the venv: `python3 -m venv .venv`,
     `tools/setup_dev.py` skips finished steps), the main worktree's `.venv` / `ext` / `re` / `ctre` links.
   - Claude Code keeps this project's memory in its project memory folder, named after the folder's path: copy it
     to the new path's folder.
   - Paths written in docs: this repo's `CLAUDE.md` and the memory files.
5. Create the empty public `ooksanen/ctplay`; `push PL22`.
6. Then the other launch items (site, Discussions, Releases, CTCtrl).

`tools/` is identical to upstream R2.02 (`ec56599`, an ancestor of `upstream/main`): `NOTICE.md` names that commit.

## Left to the builder
The script's module layout and CLI shape, the include list's format, the size limit, how the temporary test copy is
made, the wording of the new docs (plain short sentences, as the guide), and the exact set of `slimbuild` files only
the vote uses.
