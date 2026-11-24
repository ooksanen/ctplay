"""Write throwaway features and versions for tests."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

TAG_EXPORT = ["slim", "tools", "firmware"]       # an old-layout tag (CTPlay in slim/): what its slimbuild reads, its
                                                 # tree, tools/ (thumb.py, ct_fw.py) and firmware/ (upstream's
                                                 # manifests: its check_marker refuses their markers). A flat tag
                                                 # (CTPlay at the root) is exported whole.


def write_feature(root: Path, name: str, *, c_source: str = "", hooks=(), depends=(), init=None,
                  ram: int = 64, stack: int = 256) -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    lines = [f'name = "{name}"', f'description = "test feature {name}"',
             f"depends = {json.dumps(list(depends))}", f'sources = ["{name}.c"]']
    if init:
        lines.append(f'init = "{init}"')
    lines += ["", "[budget]", f"ram = {ram}", f"stack = {stack}"]
    for hook in hooks:
        point, handler, priority = hook[:3]
        lines += ["", "[[hook]]", f'point = "{point}"', f'handler = "{handler}"', f"priority = {priority}"]
        if len(hook) > 3 and hook[3]:
            lines.append("filter = true")
    (d / "feature.toml").write_text("\n".join(lines) + "\n")
    (d / f"{name}.c").write_text(c_source)
    return d


def write_version(root: Path, stem: str, marker: str, features: list[str], feature_dir: Path) -> Path:
    p = root / f"{stem}.toml"
    p.write_text(f'marker = "{marker}"\ndescription = "test version {stem}"\n'
                 f'feature_dirs = ["{Path(feature_dir).resolve()}"]\nfeatures = {json.dumps(features)}\n')
    return p


def build_tag(marker: str, tmp_path: Path) -> Path:
    """Build `versions/<marker>.toml` as git tag <marker> has it, by that tag's own build tool: the tree exported with
    `git archive`, the ignored setup linked in as in a worktree (CLAUDE.md, setup). A tag whose tree has `slim/` (every
    tag before the flat layout) builds there with `-m slimbuild`; a flat tag builds at its root with the current
    package. Returns the output directory (the .bin, .syx and manifest.json)."""
    from playbuild import paths
    tree = Path(tmp_path) / "tree"
    ref = f"refs/tags/{marker}"
    old = not subprocess.run(["git", "cat-file", "-e", f"{ref}:slim"], cwd=paths.ROOT, capture_output=True).returncode
    tar = subprocess.run(["git", "archive", ref, *(TAG_EXPORT if old else [])], cwd=paths.ROOT, capture_output=True,
                         check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        t.extractall(tree, filter="data")
    for name in ("ext", "re"):
        (tree / name).symlink_to(paths.ROOT / name)
    (tree / "stock").mkdir(exist_ok=True)
    (tree / "stock" / paths.STOCK_BIN.name).symlink_to(paths.STOCK_BIN)
    out = Path(tmp_path) / "out"
    package, cwd = ("slimbuild", tree / "slim") if old else (paths.__name__.split(".")[0], tree)
    r = subprocess.run([sys.executable, "-m", package, f"versions/{marker}.toml", "-o", str(out)],
                       cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise AssertionError(f"tag {marker} did not build:\n" + r.stdout[-2000:] + r.stderr[-2000:])
    return out
