# CTPlay patching uploader: notes for the design talk (research only, nothing changed in any repo)

## 1. How upstream's patching uploader works (tools/rc_uploader.html, made by tools/make_rc_uploader.py)

Pieces: `make_rc_uploader.py` (build step, run in a full checkout) writes one HTML file, 712 KB for 3 versions
(B5.41, R411, R411S). A README step 2 links a zip of it on GitHub Pages. A second, older page holds the old versions.

Steps on the page:
1. User downloads the official firmware from Novation Components (README gives the URL
   `components.novationmusic.com/api/v2/firmwares/168/file`, file `circuittracks-firmware-4486.syx`) and picks it in a
   file input (`accept=".syx,.bin"`).
2. The page hashes it (SHA-256 via `crypto.subtle`). A `.syx` is decoded first (7-bit packed 32-byte blocks, CRC-32/MPEG-2
   checked against the header), then the image's SHA-256 must equal the stock image hash. Anything else: red message
   "this is not the official 1.2.1 (build 4486) firmware, download it with the link above". Exactly one stock version is
   accepted.
3. User picks a version from a list (name + short description, also an "Official" entry = send stock unchanged, "to go back").
4. The patch is a list of ops per version: `COPY(offset, length)` from the user's official image, or `ADD(bytes, base64)`.
   The builder's matcher is greedy on 8-byte keys, so no ADD run holds 8+ bytes that also occur in stock: the page
   carries only the mod's own bytes. Ops are applied in the browser.
5. Checks: SHA-256 of the patched image must equal the published one, then the page encodes the `.syx` itself (a JS copy of
   `ct_fw.encode`: INIT 0x71, HEADER 0x7C, WRITE 0x72 blocks, FINISH 0x73 block 0 last) and checks the SHA-256 of that
   too. Any mismatch aborts, so a bad file or a bug never reaches the device.
6. Extras for newer builds: the DSP programs are packed in the image (LZSS, `dspz`), so the page unpacks via the patch
   and re-packs with a JS port of the packer (so packed Novation DSP code is never shipped); a "look for new versions"
   link fetches `builds/index.json` and `builds/<ver>.json` from the public Pages and adds them to the list (validated
   by shape, and still checked by SHA-256).
7. Sending (Web MIDI, `requestMIDIAccess({sysex:true})`, same code as `tools/ct_uploader.html`): user clicks
   "Allow MIDI", picks in/out ports (auto-scored by name "Circuit Tracks", not MIDI 2/3/DAW), "Identify the device"
   (Universal identity request `F0 7E 7F 06 01 F7`; reply byte **d[8]** = 1 firmware, 0x11 = 17 bootloader; d[9] = 0x64 is the product. Upstream's pages test d[9],
   which is never 1 or 17: corrected 2026-11-11, see `tests/test_uploader_core.py`). Upstream's plain
   uploader only sends in bootloader mode (Scales + Preset + Note at power on), because a send to a running firmware
   once ended "success" while the unit kept the old build (Beta 5.39); a checkbox overrides.
   The transfer is Components' pull protocol: page sends INIT and HEADER, then the device asks for blocks (reply `0x72`
   with a counter) and the page answers each with the next message; device status `0x73`: 1 = press Play on the device,
   127 = received OK (device reboots and installs), 16/17/124/126 = rejected. Timers 10-30 s, abort button, progress bar,
   log. After success it drops the MIDI ports (the device re-enumerates).
8. Shown to the user: bilingual (ES/EN) steps; back up the SD card (even a tick box "I copied the microSD card"); close
   Components and DAWs (on Windows only one app can open a MIDI port); use Chrome or Edge; do not unplug during the send;
   brick recovery (unplug, hold power 15-30 s, Scales + Preset + Note, send the official firmware); press Play on the
   device to confirm.

Clever: the SHA-256 chain (input, patched image, .syx) makes the page self-verifying; the 8-byte rule keeps Novation bytes
out; COPY ops mean the page works with any byte-identical stock file whether `.syx` or `.bin`.
Fragile: only one stock hash; the page is one big generated HTML with huge string constants; "new versions" fetch depends on
a hosted JSON; the bootloader-mode rule exists because "success" can be a lie; Windows exclusive MIDI port; Chrome/Edge only;
the DSP packer must match Python's byte for byte; Web MIDI port names differ per OS (score heuristic).

## 2. What CTPlay would need

I measured PL20 against stock (`slim/build/PL20/*.bin` vs `stock/...STOCK.bin`):
- stock image 314,844 B (0x4CDDC); PL20 image 354,932 B (0x56A74). So the build = stock + 40,088 B appended + edits.
- Edits inside the stock part: 48 small regions, 191 changed bytes in all (hook branches). These are our bytes at
  stock addresses.
- Appended tail (compiled C feature code, data, entry stubs): 40,088 B; zlib 30,153 B; base64 of raw ≈ 54 KB. Within the
  tail, 88 short runs (786 B total) happen to equal stock byte runs of 8+ (common instruction patterns / padding); the upstream
  matcher would turn them into COPY ops, so no ADD data matches stock.
- Patch = ~48 ADD ops for the hook edits + 1 big ADD for the tail (+ the few COPYs). No full-image diff, no stock bytes. Page size
  well under 100 KB per release (compress the tail with `DecompressionStream("deflate")`, optional).
- CTPlay has no DSP changes today, so the whole DSP-packing complication of upstream's later builds does not apply.
  The image is not re-packed or relocated: tail is appended, ops are simple.
- Build step: new `slimbuild.patch_uploader` (or extend `slimbuild/uploader.py`): for the chosen version(s) take
  `build/<M>/*.bin`, produce ops vs stock, assert `apply(stock, ops) == img`, assert `sha256(ct_fw.encode(img))` equals the
  manifest's `syx_sha256`, embed ops + `image_sha256` + `syx_sha256` + marker + description. Template: the same page as
  today's dev uploader (already English, has KNOWN hashes, identify, link-hello for the installed marker), plus the file
  decode + patch + encode JS from `rc_uploader.html` (hash, decodeSyx, encodeSyx, apply).
- Release update: rebuild the page per release (version list is in the page); optional `builds/index.json` on the hosting
  site if "new versions without a new page" is wanted (upstream does it; it needs the page to validate remote ops by SHA-256,
  and it means patch data is fetched from the site, which is allowed by the viewer but needs CORS/same-origin hosting).
- Guard to add: a test that scans the patch's ADD bytes for any 8-byte substring of stock (must be none) and that the page
  contains no stock hash input longer than the hash itself. Today's emulation/tag tests already pin the image bytes.
- Note: the existing dev uploader's link-hello check ("PLxx is already installed, the device keeps it, same version") is worth
  keeping in the public page.

## 3. Decisions for the user

1. Accepted inputs. Options: (a) official `.syx` only; (b) `.syx` + `.bin` (upstream); (c) also a Components backup.
   Recommend (b): same code path, `.bin` is cheap to support; `.syx` is what Novation serves. Link the Components URL,
   read the SHA-256 not the name.
2. Version check strictness. Options: exactly 1.2.1 build 4486 (image SHA-256) / any 1.2.x. Recommend exact image hash:
   CTPlay's hook addresses are stock-specific. Message names the expected file and where to get it; says "if Components
   offered you a newer firmware, stay on 1.2.1 and do not update Components' firmware prompt".
3. One page per release vs one page with several releases. Options: one page, newest CTPlay only (+ "Official" to go
   back); a page with the last N; a page + `builds/index.json`. Recommend one page with the newest release plus the
   previous one (a beta needs a rollback), "Official" entry always; old pages stay at versioned URLs
   (`/uploader/PL21/`) if you want it simple. Skip the remote index until there are many releases.
4. Identify-the-device step. Options: required bootloader mode (upstream plain uploader) / optional / skip. Recommend keep
   the identity request, require or strongly nudge bootloader mode (upstream's Beta 5.39 lesson: success with the old
   build kept), and show the installed marker through the CTPlay hello (already in today's page) to warn "already installed".
5. Backup / recovery text. Recommend the upstream shape in plain English: back up projects and the SD card first (Components),
   tick box before Send is enabled, close Components/DAWs, do not unplug, press Play on the device when asked, how to go
   back ("Official" + send), brick recovery (unplug, hold power 15-30 s, Scales + Preset + Note, send stock). Link the guide.
6. Hosting and build. Options: `ctplay.ctctrl.com/uploader` (your CTCtrl site) / ctplay.pages.dev / GitHub Pages of the
   public repo. Page is static, one HTML file; built by `python -m slimbuild.uploader --public` (new flag) into
   `build/site/public/uploader/index.html` so it ships with the guide. Recommend the same site as the guide so install steps
   link to a stable URL, same-origin so no CORS surprises. Needs HTTPS (Web MIDI requires a secure context). Also
   decide if the dev `.syx`-only page remains (yes, local only, never hosted).
7. Future official firmware. Options: do nothing (page says it only accepts 1.2.1); a second hash when a port exists;
   detect the version of a dropped file and say "this is Novation X.Y: CTPlay does not support it yet". Recommend the last:
   cheap (parse the `.syx` header version/size), and the message helps users. A port to a new stock is a separate, large job.
8. Language: English only (matches the dev page) vs ES/EN toggle like upstream. Recommend English first.

## 4. Open risks

Legal
- The patch holds only CTPlay's bytes (compiled C and 191 bytes of hook edits at stock addresses). The COPY ranges
  are offsets into the user's file, not data. Risk: the 191 changed bytes sit in stock code positions and some tail runs equal
  stock runs; the 8-byte rule and a test remove the second; the first is branches we wrote. Counsel might still look at
  "derived from firmware" wording; the claim stays "no Novation code in the page".
- The page must not embed the stock SHA-256 plus anything that identifies Novation's code beyond the hash (a hash is fine).
- Do not host or mirror the official `.syx`; only link Novation's URL. If Novation changes or removes the URL or the 1.2.1
  file, new users can't get it (followups already notes this); a user's own backup (Components download folder) is the fix.
- Trademarks: "Circuit Tracks", "Novation", "Components" (already in README's Legal; copy to the page footer).
- The patched image is still a derivative the user makes for their own device: say so ("use only on a Circuit Tracks you own").

Technical
- Web MIDI with SysEx: Chrome/Edge (desktop) only; Firefox has partial/permission add-on support, Safari none. Say
  so up front and feature-detect `navigator.requestMIDIAccess`.
- Windows: one app per MIDI port, Components or a DAW blocks the page. macOS/Linux fine. Chrome keeps a tab's MIDI port
  until the tab closes (your 2026-10-25 note): tell users to close the tab and Components, not just refresh.
- Port auto-selection by name differs by OS; keep the manual selects.
- Same-version install rule: bootloader drops an image whose version block equals the installed one (markers are 6
  bytes): the page warns when the installed marker equals the chosen build (exists today).
- A failed or aborted transfer: the bootloader keeps the old firmware; a power loss mid-flash is the real brick risk.
  Upstream's recovery text covers it; test the recovery path once on a spare device state before launch.
- The page's JS must be tested with the real stock file (fixtures in a test: patch -> compare to manifest SHA). Node can
  run the page's JS headlessly; upstream uses the emulator for firmware, not for the page.
- Future saved-format/link changes do not affect the uploader, but each PL release needs its manifest hashes frozen
  before building the page (the page is a release artifact).
