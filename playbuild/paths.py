"""Repository paths used by playbuild: one root, the package folder's parent."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
EXT = ROOT / "ext"
STOCK_BIN = ROOT / "stock" / "circuittracks-firmware-4486-STOCK.bin"
LISTING = ROOT / "re" / "app.asm"
SYMBOLS = ROOT / "stock" / "symbols.toml"
MEMORY = ROOT / "stock" / "memory.toml"
SAVE_LOCK = ROOT / "save_layout.lock"
FEATURES = ROOT / "features"
VERSIONS = ROOT / "versions"
RUNTIME = ROOT / "runtime"
BUILD = ROOT / "build"
VOTE_LIST = ROOT / "docs" / "vote.toml"
SITE_SRC = ROOT / "site"
