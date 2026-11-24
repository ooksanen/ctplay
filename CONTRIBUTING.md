# Contributing

Thank you for helping. Ideas and questions go to [Discussions](https://github.com/ooksanen/ctplay/discussions), bugs to
[Issues](https://github.com/ooksanen/ctplay/issues), changes to pull requests. Set up first: [`README.md`](README.md).

## How a feature is made

A feature is a folder `features/<name>/`: a `feature.toml` and its C sources. A version file
`versions/<MARKER>.toml` lists the features of a build. `playbuild` compiles the C, places it in free flash and
RAM, and hooks it into the official firmware. Read an existing feature first: `features/countin/` is small.

`feature.toml` says:
- `sources`, `init`, and the `[budget]`: RAM, stack and (when asked for) ITCM bytes. The build refuses a feature that
  goes over its budget.
- `[[hook]]` entries: a `point` (a hook named in `stock/symbols.toml`), the `handler` (your C function) and a
  `priority` (lower runs first). Hook kinds: `entry` (a function's start), `call` (a call site), `mid` (an instruction
  inside a function; the handler gets every register).
- `[[saved]]` fields: the variables saved with the project. Each field keeps its offset in `save_layout.lock`
  forever. New fields are appended with `.venv/bin/python -m playbuild versions/<MARKER>.toml --update-lock`.
  Never reorder or reuse a field: projects saved by older builds must load.
- `[[patch]]` entries: a few bytes of stock's own code replaced (`addr`, `stock`, `new`, `why`), for a stock bug.
  The build checks the old bytes against the official image and against every hook site. See `features/stockfix/`.

A new stock address goes in `stock/symbols.toml` with the bytes expected there (checked on every build), a note
and its source. Memory regions are in `stock/memory.toml`.

Every control a feature claims (a button, a pad, a page) is in [`docs/ui-map.md`](docs/ui-map.md). Check
that a new one is free, and add it there.

## The device rules

Every change keeps these. [`docs/hacking.md`](docs/hacking.md) explains each one.
- Never write the internal flash or the option bytes. Never touch the bootloader. The build refuses code that reaches
  the flash controller.
- Never take the DSP-service lock from a hook that runs in the DSP service tick. The device hangs at power-on. The
  build refuses a path to any stock function tagged `takes_dsp_lock`.
- No long or interrupt-masked work while a pad is pressed: change the setting and its LED on the press, do the slow
  work on the pad's release.
- A build must not change the published ones: the tests rebuild them byte for byte.
- Markers are `PL` (CTPlay builds) or `SL` (foundation diagnostics), at most 6 bytes. A diagnostic build ends in `D`.

## Tests

From the repository's root:

    .venv/bin/python -m pytest -m "not emu"     # the fast tests: build checks, models, the docs (a few minutes)
    .venv/bin/python -m pytest                  # everything, with the emulation tests (about an hour)

Delete any temporary `firmware/<MARKER>/` of your own build (the guide's "To install a build you made") before you run
the tests or open a pull request. Run the fast tests before every pull request. Run the emulation tests when you
change code that runs on the device. Emulation tests go through stock's real routes (a button press through the
controller), not straight to a handler.

**Emulation passing is not device passing.** Several features worked in emulation and failed on the device: the
emulator has no pad scanner and its clock does not advance. A change to the firmware needs a device run. Each
build's device test plan is `firmware/<MARKER>/TEST.md`, with its results; a new feature brings its own steps.

## Docs

Docs are short and plain: say what a thing does, what the LEDs show, and how to check it. The guide and the recipes
build with `.venv/bin/python -m playbuild.guide --docs`, which checks every link. Name the master effects view
"Master FX".

## A bug report

Say:
- the CTPlay version (the uploader's **Identify the device** shows its marker, e.g. `PL22`);
- what you did, press by press, from a new empty project if you can;
- what you expected, and what happened (sound, LEDs);
- whether it happens on the official firmware too.

## What happens to a pull request

CTPlay is developed in a private repository; this public one gets one commit per release. A merged pull request is
brought into development before the next release, so it is in that release and in every one after it.

By sending a pull request you agree that it is published under this repository's MIT licence.
