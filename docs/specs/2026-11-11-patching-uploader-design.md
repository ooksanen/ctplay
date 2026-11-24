# The patching uploader ("bring your own firmware")

**State:** built 2026-11-11 (branch `uploader`; device test `firmware/PL21/TEST-uploader.md` not run yet). Approved by the user, 2026-11-11 (with a risk tick box added). Plan: `slim/docs/plans/2026-11-11-patching-uploader.md`. The user decided on 2026-11-07: "bring your own firmware". CTPlay
is never distributed as a finished `.syx`, and the uploader goes at `ctplay.ctctrl.com/uploader` or similar. On
2026-11-11 the user skipped the design questions, so the calls below marked **(my call)** are the controller's. They
come from the research notes, `docs/investigations/2026-11-11-patching-uploader.md`, which also explain how upstream's
uploader works. Part of the beta checklist (`followups.md`, "Installing without building").

## Why
A public user can't build CTPlay: the build needs the Arm toolchain, Python and this repo. And we can't hand them a
finished firmware file, because it would carry Novation's code. So the user brings the official firmware file, and a
web page turns it into CTPlay on their own computer and installs it. Upstream (CIRCUIT-HACKS-RC, MIT) has shipped this
for months (`tools/rc_uploader.html`, built by `tools/make_rc_uploader.py`): the page carries only the mod's own bytes
and a recipe, and it rebuilds the image from the user's file.

## Goals
- A user with a Circuit Tracks, desktop Chrome or Edge and the official firmware file installs CTPlay in a few minutes,
  without a terminal.
- **No Novation bytes on the page or in anything we host.** The page carries CTPlay's bytes, offsets into the user's
  file, and SHA-256 hashes.
- **The page checks itself:** the user's file, the rebuilt image and the encoded `.syx` must each match a published
  SHA-256 before anything is sent. A wrong file or a bug in the page never reaches the device.
- Going back is as easy as going forward: the official firmware is always one choice away.
- Plain English, short sentences; the backup and recovery steps are on the page.

## Non-goals
- No server: one static HTML file.
- No firmware other than official 1.2.1 build 4486 (a port to a newer official firmware is its own large job).
- No editing or saving of projects, patches or samples (that is Components' job).
- The dev uploader (`slimbuild/uploader.py` → `build/ct_uploader.html`, which sends a locally built `.syx`) stays as it
  is, local only, never hosted.

## Anti-goals (a failure even if it works)
- Any stock byte, or any 8-byte run equal to stock, inside the page's patch data.
- A send that can start before every check has passed.
- Hosting or mirroring Novation's firmware file.
- A page that reports success while the device kept its old firmware (upstream's Beta 5.39 lesson, below).

## What the user does (the page's steps, top to bottom)
1. **Before you start** (always visible): back up your projects and samples with Components, and copy the microSD
   card. Use desktop Chrome or Edge. Close Components, any DAW and other MIDI pages (on Windows only one app can use a
   MIDI port, and Chrome keeps a tab's port until the tab is closed). Use only on a Circuit Tracks you own.
2. **Get the official firmware:** a link to Novation's own download (the URL upstream uses, from Components' API) for
   `circuittracks-firmware-4486.syx` (1.2.1, build 4486). The user picks the file. **(my call: accept the `.syx` and a
   `.bin` image, as upstream)**. The page reads the file in the browser only.
3. **The check:** a `.syx` is decoded (the 7-bit packed blocks, its CRC-32 checked against the header). Then the image's
   SHA-256 must equal stock 1.2.1 build 4486's. **(my call: the exact image hash, nothing looser:** CTPlay's hooks sit at
   stock addresses). If it doesn't match, the page says what it found in plain words: a different Novation version
   ("this is Novation firmware X.Y; CTPlay needs 1.2.1 build 4486", read from the `.syx` header), or not a Circuit Tracks
   firmware at all, and where to get the right file.
4. **Choose what to install** **(my call: the newest CTPlay release, the one before it, and "Official 1.2.1")**. Each
   entry shows the public version, the marker and one line of what it is: "CTPlay 1.0 beta 1 (PL21)". "Official" sends
   the user's own file unchanged: the way back. Older releases stay available at a versioned address (below).
5. **Build:** the page applies the release's patch to the user's image, checks the result's SHA-256 against the
   release's published image hash, encodes the `.syx` (the same format as `tools/ct_fw.py`) and checks its SHA-256
   against the release's `syx_sha256`. Any mismatch stops here with a clear message ("this page or your file is not
   what we expected; nothing was sent").
6. **Connect:** "Allow MIDI" (the browser asks), then the input and output ports (picked by name, "Circuit Tracks";
   the user can change them). **Identify the device** sends the Universal identity request and shows whether the unit
   runs its firmware or is in bootloader mode, and, if CTPlay answers its link hello, which CTPlay build is installed.
   **(my call: bootloader mode required by default,** as upstream's plain uploader does: a send to a running firmware
   once reported success while the unit kept the old build. The page tells how: switch off, hold Scales + Preset + Note,
   switch on. An "I know what I'm doing" box allows a send to running firmware.)
7. **Two tick boxes**, both needed before Send is enabled (the user, 2026-11-11: a risk acknowledgement):
   - "I have backed up my projects and my SD card."
   - "I understand that CTPlay is unofficial firmware and I install it at my own risk. If something goes wrong, my
     Circuit Tracks may need the recovery steps below, and Novation does not support CTPlay."
   The second box is honest about the size of the risk: the bootloader is never touched and a failed send keeps the
   old firmware, but a power loss during the install can leave the unit needing recovery. "Official" (going back)
   needs the backup box only.
8. **Send:** Components' transfer protocol (the page sends INIT and HEADER, the device asks for each block). A progress
   bar, a log, an Abort button. When the device asks, the page says "press Play on the Circuit Tracks". On "received"
   the device restarts and installs; the page says so and releases the MIDI ports.
9. **If the chosen build is already installed** (the same 6-byte marker), the page warns before Send: the device
   ignores an image whose version block equals the installed one (exists in today's dev page).
10. **If it goes wrong:** recovery steps on the page: the device keeps its old firmware after a failed or aborted
    transfer; if it doesn't start, unplug it, hold power 15–30 s, start in bootloader mode (Scales + Preset + Note) and
    send "Official". A link to the guide's "Going back to the official firmware".
11. A footer: CTPlay is not affiliated with Novation; trademarks belong to their owners (the README's notice); the
    page's licence and upstream's credit (MIT).

## The patch (what a release carries)
- A list of operations, applied in order to an empty output: **COPY(offset, length)** from the user's stock image,
  or **ADD(bytes)** of CTPlay's own bytes. For CTPlay's builds this is the stock image copied around the hook edits
  (48 small regions, 191 B for PL20), the edits as ADDs, and the appended code (about 40 KB) as one ADD with the few
  runs that equal stock turned into COPYs.
- **The 8-byte rule** (upstream's): the builder matches greedily on 8-byte keys, so no ADD holds 8 or more bytes that
  also occur in stock. A test checks it (below).
- Per release: the marker, the public version, the description, the patch, `image_sha256` and `syx_sha256` (both
  from the release's committed `firmware/<MARKER>/manifest.json`), and the stock image's SHA-256 (one hash, shared).
- **(my call:** the patch is stored as base64 of the raw ops, about 54 KB per release, and compressed only if the page
  grows past ~250 KB: `DecompressionStream` works in every browser that has Web MIDI with SysEx.)
- CTPlay doesn't touch the DSP programs, so upstream's DSP repacking does not apply. If a future build does, that's a
  new decision.

## The public version (decided 2026-11-11)
The marker keeps counting (PL21, PL22 …); each build gets a public version. `versions/<MARKER>.toml` gains
`release = "1.0 beta 1"` (absent = not a public release); the build carries it into the manifest; the page and the
guide show "CTPlay 1.0 beta 1 (PL21)"; GitHub Releases tag `v1.0.0-beta.1`. The page lists only manifests that have a
`release`.

## How it is built and hosted
- **`python -m slimbuild.uploader --public`** (my call: a flag on the existing module, sharing its MIDI code) writes
  `build/site/public/uploader/index.html` beside the guide. For each listed release it builds the patch from
  `build/<MARKER>/*.bin` against stock, asserts `apply(stock, ops) == image`, asserts the image's and the encoded
  `.syx`'s SHA-256 equal the committed manifest, and embeds the ops and hashes. It needs the stock firmware locally
  (as every build does); the output holds none of it.
- **The page's template** (my call): a new English template in `slimbuild/` adapted from upstream's `rc_uploader.html`
  (MIT: keep the notice and credit), with today's dev page's additions (the CTPlay hello for the installed build, the
  same-marker warning). Bilingual text: no (my call: English first).
- **Hosting** (my call): the same site and origin as the guide (`ctplay.ctctrl.com`), HTTPS (Web MIDI needs a secure
  context). The newest page at `/uploader/`; each release's page also at `/uploader/<MARKER>/`, frozen, so an old
  release stays installable. No remote "new versions" index (upstream has one; not needed while releases are few).
- The guide's "Installing" section points to `/uploader/` and keeps the build-from-source path for developers.

## Tests
- **Patch builder** (Python): for the newest release, `apply(stock, ops)` equals the image byte for byte; no ADD run of
  8+ bytes occurs in stock; the page holds no 8-byte run of stock anywhere (scan the whole HTML's decoded data); the
  hashes equal the manifest's.
- **The page's JS** (Node, as `tests/test_link_page.py` runs the link page's decoder): the decode, apply and encode
  functions on the real stock `.syx` and `.bin` give the release's `syx_sha256`; a wrong file, a different version's
  header and a corrupted block give the right messages; "Official" re-encodes to stock's own `.syx` SHA-256.
- The transfer code is upstream's and the dev page's, already used on the device for every build since PL01: no new
  emulation; the device test below covers it.
- Skipped when the stock firmware or Node is missing (a fresh clone).

## Device test (the beta's launch check, its own short TEST)
Each on a real Circuit Tracks, from the hosted page (or a local copy served over `http://localhost`):
- The official `.syx` from Novation's link → CTPlay 1.0 beta 1 installs; Identify shows it.
- The same with a `.bin`; a wrong file is refused before anything is sent.
- "Official" goes back to stock; CTPlay again; the same build again is warned about.
- An aborted send leaves the old firmware running; the recovery steps work (bootloader mode, send "Official").
- Windows with Components open: the page explains the busy port.

## Left to the builder
The exact page layout and wording (plain English, short sentences), the op encoding inside the page, how the
template is split between the dev page and the public page, the identity-reply parsing details (upstream's, already
working), port auto-selection, and the test fixture layout.

## Open risks
- Novation could move or remove the 1.2.1 download. The page then says to use a file the user kept (Components keeps
  downloads); we never host it.
- Web MIDI with SysEx is desktop Chrome and Edge only: the page detects it and says so.
- A power loss during the install is the real brick risk; the recovery text covers it. Test recovery once on the device
  before launch.
- Legal wording: the page says "no Novation code is included; your own firmware file is changed on your computer, for
  a device you own". Tell upstream before the launch (followups, "License").
