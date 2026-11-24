"""Download the pinned Arm GNU Toolchain into ext/ (checked against its SHA-256).

    .venv/bin/python setup_toolchain.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from playbuild import toolchain  # noqa: E402

if __name__ == "__main__":
    print("installed in", toolchain.install())
    print(toolchain.require())
