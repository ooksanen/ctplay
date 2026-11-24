# Notice

CTPlay stands on other people's work. This file says whose, and under which licence.

## CIRCUIT-HACKS-RC

[Ghillermo/CIRCUIT-HACKS-RC](https://github.com/Ghillermo/CIRCUIT-HACKS-RC) by Ghillermo is the base of CTPlay. It
gave CTPlay:
- the tools under `tools/`: the firmware file format and its checks (`ct_fw.py`), the Thumb assembler (`thumb.py`),
  the ARM emulation the tests build on (`emu_sc05.py`, `emu_sc08.py`), the listing (`gen_listing.py`), the setup (`setup_dev.py`) and
  what they import;
- the way the uploader patches your own copy of the official firmware in the browser;
- most of what is known about the device: the controller, the LEDs, the DSP, the free memory, and the rules that keep
  a patch from hanging or bricking it. [`docs/hacking.md`](docs/hacking.md) credits each finding.

Licence: MIT ([`LICENSE`](LICENSE) keeps Ghillermo's copyright line).

**Files copied unchanged.** `tools/` and `stock/SHA256SUMS.txt` come from CIRCUIT-HACKS-RC at R2.02 (`ec56599`),
unchanged. `fork/ct_uploader.en.html` is an English translation of upstream's `tools/ct_uploader.html`.

## circuittracksreverseengineering

[userx14/circuittracksreverseengineering](https://github.com/userx14/circuittracksreverseengineering) by userx14:
the device's RAM and flash dumps the ARM emulators run on, the board's documentation, and the copy of Novation
Components' project validator that `tests/test_components_validator.py` runs. `tools/setup_dev.py` clones it at a
pinned commit into `ext/` (linked as `ctre`). It declares no licence, so this repository holds none of it.

## Fetched by the setup, never stored here

| What | From | Licence |
|---|---|---|
| capstone 5.0.7 (Thumb disassembly) | [PyPI](https://pypi.org/project/capstone/), [capstone-engine/capstone](https://github.com/capstone-engine/capstone) | BSD-3-Clause |
| unicorn 2.1.4 (ARM emulation) | [PyPI](https://pypi.org/project/unicorn/), [unicorn-engine/unicorn](https://github.com/unicorn-engine/unicorn) | GPL-2.0 |
| dsp56300 / dsp56kEmu (DSP emulator, only without `--no-dsptool`) | [dsp56300/dsp56300](https://github.com/dsp56300/dsp56300) | GPL-3.0 (its submodule asmjit: Zlib) |
| Arm GNU Toolchain 14.2.rel1 (the C compiler) | [developer.arm.com](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads), by `setup_toolchain.py` | GPL-3.0 with the GCC runtime exception, and others |
| pytest, markdown-it-py | PyPI (`requirements.txt`) | MIT |

`tools/dsptool/*.patch` apply to dsp56300 and are GPL-3.0 like it. A `dsptool` binary built against it is GPL-3.0.

## Novation's firmware

The official Circuit Tracks firmware is Novation's proprietary code. This repository never holds it, nor any file
built from it. `tools/setup_dev.py` downloads it from Novation to your machine (checked against
`stock/SHA256SUMS.txt`), and the uploader patches your own copy. Install it, and CTPlay built on it, only on a
Circuit Tracks.

## Trademarks

CTPlay is not affiliated with, endorsed by or supported by Novation or Focusrite. Novation, Circuit Tracks and
Components are trademarks of Focusrite Audio Engineering Ltd.
