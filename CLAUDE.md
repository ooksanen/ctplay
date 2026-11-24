# CTPlay — context for Claude Code

CTPlay is a modified firmware for the Novation Circuit Tracks (official firmware 1.2.1, build 4486), built on
CIRCUIT-HACKS-RC. Features are C units that `playbuild` places in free flash and RAM and hooks into the official
firmware. This repository never holds Novation's firmware: `tools/setup_dev.py` downloads it to `stock/`.

## Layout
- `playbuild/` the build tool, `features/<name>/` the features (`feature.toml` + C), `versions/<MARKER>.toml` the
  builds, `stock/symbols.toml` / `memory.toml` what is known about stock and where CTPlay may live, `runtime/` what
  every build carries, `save_layout.lock` the saved fields' offsets, `tests/`, `firmware/<MARKER>/` each build's
  manifest and device test plan, `docs/` (user guide, recipes, `ui-map.md`, `resources.md`, `hacking.md`, specs,
  investigations).
- `tools/`, `stock/SHA256SUMS.txt`: from CIRCUIT-HACKS-RC, unchanged; `fork/ct_uploader.en.html`: an English
  translation of upstream's `tools/ct_uploader.html`. Do not edit them.
- Ignored setup: `.venv/`, `ext/` (dumps, toolchain), `ctre` (link to the dumps), `re/` (the listing), `stock/*.bin|syx`.

## Commands
- Python is always `.venv/bin/python`, run from the repository's root. Setup: `README.md`.
- Build `.venv/bin/python -m playbuild versions/<MARKER>.toml` (→ `build/<MARKER>/`); fast tests
  `.venv/bin/python -m pytest -m "not emu"`; all tests `.venv/bin/python -m pytest` (about an hour); the docs
  `.venv/bin/python -m playbuild.guide --docs`; a new saved field `... -m playbuild versions/<MARKER>.toml --update-lock`.

## Device rules
Read [`docs/hacking.md`](docs/hacking.md) before changing code that runs on the device. In short:
- **Never write the internal flash or the option bytes. Never touch the bootloader** (`0x08000000–0x0800FFFF`).
- Never take the DSP-service lock (`takes_dsp_lock` in `symbols.toml`) from the DSP service tick: the device hangs.
- No long or interrupt-masked work while a pad is pressed: do it on the pad's release.
- Published builds must rebuild byte for byte (`tests/test_build.py`). `save_layout.lock` is append-only.
- Tests go through stock's real routes, not the presumed handler. Emulation passing is not device passing.
- Identify views and buttons by what the code does with them, not by assumption.

## Writing
Docs are short plain sentences: what a thing does, what the LEDs show, how to check it. The master effects view is
"Master FX". Every claimed control goes in `docs/ui-map.md`.
