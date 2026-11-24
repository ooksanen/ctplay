# Flatten the dev tree: CTPlay at the repo root (design)

Status: approved by the user, 2026-11-23 (after a builder check). Follows `2026-11-23-public-repo-design.md` (the publish script, merged).

## Why
The public repo's paths become permanent with its first commit: links from the guide, Reddit, issues and pull
requests point at them. Today every CTPlay path starts with `slim/`, a name from the start of the project ("the slim
build" next to upstream's 264 builds) that no longer describes CTPlay. The user (2026-11-23): remove `slim/`, flatten
it to the repo root, before the launch; rename the build package `slimbuild` to `playbuild`; at the launch, rename the
dev branch `slim` to `main`.

## Goals
- The dev tree and the public tree have CTPlay at the root: `playbuild/`, `features/`, `runtime/`, `docs/`, `tests/`,
  `versions/`, `firmware/`, `stock/`, `tools/` (upstream's 8 files), …
- Every published build still builds byte-identical: the pins in `tests/test_build.py` (SL00D, SL01D, PL22), every PL
  tag through `tests/test_tags.py` (from its own tree, old layout), and `publish stage PL22`.
- The publish script and its include list work on the new layout; PL22 is staged again for the user's review.

## Non-goals
- Renaming C names (`slim_*`, `SLIM_*`, `slim.h`, `slim_rt.c`) or the `SL` markers: internal, and the markers are
  history (user, 2026-11-23).
- Renaming the manifest field `slim_version`: data in published manifests; a new build keeps writing it.
- Rewriting history: old commits and tags keep `slim/`. Old specs, plans and investigations keep their text (they are
  records); only their links are checked (below).
- The branch rename `slim` → `main`: a launch step (below), not part of this change.

## Anti-goals
- A published build's bytes change.
- A file of upstream's that the build or tests need goes missing (the setup, the emulators, the listing, the
  uploader template).
- Dev and public layouts diverge again (a public pull request must apply to dev unchanged).

## Approaches considered
1. **Flatten to the root, upstream's tree dropped from dev (chosen, user 2026-11-23).** The cleanest public repo; dev =
   public layout + dev-only files. Needs upstream's tree out first (`docs/`, `firmware/`, `stock/`, `README.md`,
   `.gitignore` clash).
2. **Rename `slim/` to `ctplay/`.** Smaller change, but `ctplay/ctplay/…` in the public repo and upstream's clutter
   stays at dev's root. Rejected.
3. **Flatten only in the public tree** (the publish script's `moves`). Two layouts forever, every public pull request
   needs a path rewrite to come into dev. Rejected.

## The change
**1. Upstream's tree leaves dev.** One commit removes every tracked file of upstream's and of the English fork except:
`tools/` = the 8 files and `tools/requirements.txt` and `tools/dsptool/` (the include list's `upstream` entries),
`stock/SHA256SUMS.txt`, `fork/ct_uploader.en.html`, `fork/setup.sh`, `fork/pre-push`. Gone: upstream's `README.md`,
`LEEME.md`, `CHANGELOG.md`, `FORK.md`, `LICENSE`, `.gitattributes`, `docs/`, `firmware/`, the rest of `tools/` and
`fork/`. Upstream's history stays reachable (tags, `refs/archive/*`, `main`); its notes and tests live on in
upstream's repo and in the English fork's clone (`circuit-hacks-rc` after the launch).

**2. `slim/*` moves to the root** (`git mv`, so history follows): `slim/stock/*.toml` joins `stock/`, `slim/.gitignore`
merges into the root `.gitignore` (keep the root's ignores of `ext/`, `re/`, `ctre`, `.venv/`, `stock/*.bin|syx`,
`firmware/*/*.bin|syx`, `build/`), `slim/README.md` and `slim/public/README.md` become one root `README.md` (the
public one; the dev-only setup facts go to `CLAUDE.md`). `slim/public/LICENSE`, `NOTICE.md` and `CONTRIBUTING.md` move
to the root too (dev and public then hold the same files; upstream's `LICENSE` is replaced by ours, which keeps
Ghillermo's line). Only `CLAUDE.md` differs between dev and public: the root `CLAUDE.md` is dev's, the public one is
`public/CLAUDE.md`, which the include list's `moves` maps to the root (`public/` holds nothing else).

**3. `slimbuild` becomes `playbuild`** (the package, `python -m playbuild …`, every import, test, doc and command
line). `paths.py`: one root (the package's parent) — `ROOT` = the repo root; `TOOLS`, `EXT`, `STOCK_BIN`, `LISTING`
under it as today; `SYMBOLS`, `MEMORY` = `stock/*.toml`; `BUILD` = `build/`. `pytest.ini`: `pythonpath = . tests tools`.
`UPSTREAM_FIRMWARE` goes: `firmware/` is now CTPlay's own (PL manifests), so `check_marker`'s upstream-manifest scan
would report every published build as a clash with itself. `check_marker` keeps the versions-folder check only; the
`SL` / `PL` prefix rule (`features.py`) already keeps CTPlay's markers apart from upstream's `SC` / `RC` (no 6-byte
clash is possible). The test of the upstream clash (`test_checks.py`, `test_upstream_marker_clash_is_rejected` and the
`UPSTREAM_FIRMWARE` line) is deleted, not ported.

**Before the deletion:** `publish`'s import-closure test (`test_closure_missing_on_the_real_tree`) already proves
the build and tests need no other upstream module; run it first. Investigation scripts and test comments that name
upstream tools no longer in the tree are records: left as they are.

**4. Old tags keep building from their own layout.** `tests/helpers.py` `build_tag` (and `test_tags.py`) export a tag
and build it with that tag's own build tool: a tag whose tree has `slim/` builds as today (`slim/`, `tools/`,
`firmware/`, `cd slim`, `python -m slimbuild`); a tag without it builds from the root with `python -m playbuild`. Every
tag that exists today has `slim/`; only tags made after this change are flat.

**5. The publish script follows** (`publish/` at the root, run from the root as `.venv/bin/python -m publish …`): the
include list's paths lose `slim/`; `verify_tree` builds in the copy's root with `-m playbuild`; the closure check
scans `playbuild/`, `tests/`, `features/`, `runtime/`, `setup_toolchain.py`; the dev test for the old name scans the
whole dev tree as before.

**6. Paths in the docs.** Current docs (the root `README.md`, `public/*`, `docs/user-guide.md`, `recipes.md`,
`hacking.md`, `ui-map.md`, `resources.md`, `layouts/`, the site's templates) and `CLAUDE.md` lose `slim/` and say
`playbuild`. The guide's `REPO_URL` links resolve from the root (`README.md`, `docs/…`). Records (specs, plans,
investigations, research, `firmware/*/TEST*.md`) keep their text; their relative links among themselves still work
(they move together); links that left `slim/` (to upstream's `docs/`, `tools/` …) show up in the publish link report.

**7. `CLAUDE.md` (dev) is rewritten for the new layout:** the CTPlay docs map, commands from the root, the rules and the
platform summary kept; upstream's commands (`verify_builds.py`, `run_tests.sh`, `translation_status.py`), its docs
map (`NOTAS`, `RECURSOS`, `VERSIONS.en.md`) and the `main`-branch workflow move out (they belong to the English fork's
own clone). `fork/setup.sh` keeps the remotes it needs and the hook; the `CLAUDE.md merge=ours` driver goes (dev no
longer merges `main`).

**8. Restage.** After the change: the fast suite, `test_tags`, then `publish stage PL22` (byte-identical, fast tests
in the copy) and once `--full`. The commit staged before (47fc624, `slim/` layout) was never pushed; with no
`public/main` the new stage is parentless and replaces it (`stage` resets the staging `main`), so the public history
starts flat. The plan checks this (`git -C ~/work/ctplay rev-list --count main` = 1).

**9. Outside this repo.** CTCtrl's docs cite `slim/…` paths of the dev repo (`~/work/ctctrl`: `CLAUDE.md`, 3 specs);
they are already on the launch checklist ("References to update") and change with it, not here. The memory notes are
updated at the end of this change. No other worktree or branch is in flight.

## The launch order (update to the public-repo spec's "Order at launch")
Before the folder renames (step 3 there), add: move dev's `main` (upstream + English translations) to its own clone
`~/work/circuit-hacks-rc` (remotes `fork`, `upstream`), keep a copy in dev as `refs/archive/main`, delete dev's `main`
branch (local and on `ctplay-dev`), rename `slim` → `main` (local and on GitHub, `git push origin -u main`, delete
`origin/slim`), and set `ctplay-dev`'s default branch to `main`. Then the PL tags, the staging folder and the publish
script are unaffected (they use commits, not branch names).

## Left to the builder
The commit split (at least: drop upstream / move / rename package / follow-ups), how `build_tag` detects the layout,
the wording of the merged README and the rewritten `CLAUDE.md`, and whether a byte difference caused by a path inside
the image (e.g. a file name the compiler embeds) is fixed with a prefix map or a relative path (the build must stay
byte-identical either way; stop and report if it cannot).
