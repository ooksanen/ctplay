"""python -m playbuild VERSION.toml [-o OUTDIR]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import features, lock, paths, symbols
from . import build as _build
from .errors import BuildError


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="playbuild", description="Build a slim firmware version.")
    ap.add_argument("version", type=Path, help="versions/<NAME>.toml")
    ap.add_argument("-o", "--outdir", type=Path, help="default: build/<NAME>/")
    ap.add_argument("--update-lock", action="store_true",
                    help="first append the version's new saved fields to save_layout.lock")
    args = ap.parse_args(argv)
    try:
        if args.update_lock:
            v = features.load_version(args.version, symbols.load(paths.SYMBOLS))
            lk = lock.update(paths.SAVE_LOCK, {f.name: f.saved for f in v.features})
            print(f"{paths.SAVE_LOCK.name}: layout {lk.layout_id}, {len(lk.entries)} fields, {lk.length} B")
        m = _build.build(args.version, args.outdir)
    except BuildError as e:
        print(f"playbuild: {e}", file=sys.stderr)
        return 1
    print(f"{m['marker']}: image {m['image_size']}, syx sha256 {m['syx_sha256']}, "
          f"flash {m['flash']['used']} B, RAM {m['ram']['used']} B at {m['ram']['start']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
