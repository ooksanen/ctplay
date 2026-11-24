# CTPlay

CTPlay is a modified firmware for the **Novation Circuit Tracks** that adds playing features to the official firmware
1.2.1 (build 4486): chords, strum, an arpeggiator, Euclidean fills, a melodic generator, note repeat, trig conditions
and more. Everything else works as on the official firmware, and the changes only take effect when you use them.

CTPlay is unofficial and not supported by Novation. Use it at your own risk; you can always go back to the official
firmware.

## Use it

The site is [ctplay.ctctrl.com](https://ctplay.ctctrl.com): the user guide, the recipes and the uploader. The uploader
is a web page that turns your copy of the official firmware into CTPlay on your computer and sends it to the Circuit
Tracks. The same guide is in this repository: [`docs/user-guide.md`](docs/user-guide.md).

**Bring your own firmware.** This repository and the site never hold Novation's firmware, nor any file built from it.
You download the official firmware from Novation; the uploader and the build here change your copy.

## Built on

- [CIRCUIT-HACKS-RC](https://github.com/Ghillermo/CIRCUIT-HACKS-RC) by Ghillermo: the base. Its tools build and check
  the firmware, and most of what is known about the device was found there.
- [userx14/circuittracksreverseengineering](https://github.com/userx14/circuittracksreverseengineering): the device
  dumps the emulators run on.

[`NOTICE.md`](NOTICE.md) has the full credits and licences. [`docs/hacking.md`](docs/hacking.md) collects
what is known about the device, with who found each thing.

## Set up

You need Linux on x86-64, or WSL on Windows, with Python 3.11 or newer and git. On Ubuntu:

    sudo apt install git python3-venv
    git clone https://github.com/ooksanen/ctplay.git
    cd ctplay
    python3 -m venv .venv
    .venv/bin/python tools/setup_dev.py --no-dsptool         # Python packages, the official firmware, dumps, listing
    .venv/bin/python -m pip install -r requirements.txt
    .venv/bin/python setup_toolchain.py                      # the Arm GNU Toolchain into ext/

`setup_dev.py` downloads the official firmware from Novation to your machine (into `stock/`, checked against
`stock/SHA256SUMS.txt`). It also clones userx14's dumps into `ext/` and writes a listing of the firmware into `re/`.
Git ignores all three. `--no-dsptool` skips building the DSP emulator: CTPlay's build and tests do not need the DSP
emulator. Leave the option out to build it anyway (this needs cmake and a C++17 compiler).

`setup_dev.py`'s last line names upstream's checks (`tools/verify_builds.py`, `tools/run_tests.sh`): they check
upstream's own builds, which this repository does not hold. CTPlay's checks are the commands under "Build and test".

## Build and test

From the repository's root:

    .venv/bin/python -m playbuild versions/PL22.toml   # -> build/PL22/circuittracks-4486-PL22.syx
    .venv/bin/python -m pytest -m "not emu"            # the fast tests (a few minutes)
    .venv/bin/python -m pytest                         # everything, with the emulation tests (about an hour)

The build prints the `.syx` file's SHA-256. For the release this commit holds, it equals `syx_sha256` in
`firmware/<MARKER>/manifest.json`. Each release is one commit in this repository, tagged `v<version>`
(CTPlay 1.0 beta 2 = `v1.0.0-beta.2`, marker `PL22`). Older version files build today's sources under an old
marker, not the published build: check out a release's tag to build it.

The guide and the recipes as a site:

    .venv/bin/python -m playbuild.guide --docs         # -> build/site-docs/public/

To send a build to the device, see the guide's [Building from source](docs/user-guide.md#building-from-source). How a
feature is made, and the rules every change keeps: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Layout

    README.md, LICENSE, NOTICE.md, CONTRIBUTING.md, CLAUDE.md
    playbuild/              the build tool
    features/<name>/        one feature: feature.toml (hooks, budgets, saved fields, byte patches) + C sources
    versions/<MARKER>.toml  a build: a marker + a list of features (+ `release`, the public name, for a release)
    runtime/                what every build carries: C start-up, the RAM reservation, the ITCM write test
    stock/                  symbols.toml and memory.toml (what is known about the official firmware and where CTPlay
                            may live), SHA256SUMS.txt (the official firmware's checksums)
    save_layout.lock        the offset of every saved field, append-only
    firmware/<MARKER>/      each published build's manifest and device test plan (TEST.md) with its results
    tests/                  unit, build-check, emulation and comparison tests
    pages/                  test pages for the CTCtrl link and the voice log
    docs/                   the guide, the recipes, hacking.md, ui-map.md, resources.md, the specs, the investigations
    tools/                  from CIRCUIT-HACKS-RC, unchanged: firmware format, Thumb assembler, emulation, setup
    fork/ct_uploader.en.html  the English uploader page the development uploader is made from

## Feedback

Questions and ideas: [Discussions](https://github.com/ooksanen/ctplay/discussions). Bugs:
[Issues](https://github.com/ooksanen/ctplay/issues). Pull requests are welcome: read
[`CONTRIBUTING.md`](CONTRIBUTING.md) first.

## Licence

MIT: [`LICENSE`](LICENSE). Third-party parts keep their own licences: [`NOTICE.md`](NOTICE.md).

CTPlay is not affiliated with Novation or Focusrite. Novation, Circuit Tracks and Components are trademarks of
Focusrite Audio Engineering Ltd.
