# CTCtrl link — design

Status: built as `PL12` (2026-10-19; plan `docs/plans/2026-10-19-ctctrl-link.md`); passed on the device 2026-10-19
(`firmware/PL12/TEST.md`, with the test page and CTCtrl's CTPlay panel). The CTCtrl side (its panel, store, parsers) has
its own spec in the CTCtrl repo: `docs/superpowers/specs/2026-10-18-ctplay-panel-design.md`. This document owns the
protocol; CTCtrl follows it.

## Intent

The user's CTCtrl web app (phone, tablet, computer) already mirrors stock state over MIDI: it follows the selected
track, re-reads a patch when the device changes it, lists the loaded packs. This feature lets it do the same for
CTPlay: recognise a CTPlay build, show controls for the settings that build has, and keep them in sync both ways. A
"performance helper": set a chord shape or an arp rate from the phone while playing, and see on the phone what was
changed on the Circuit.

**Goals**
- CTCtrl can tell a CTPlay build from stock or upstream firmware, and learn which settings it has, from one request.
- CTCtrl can read every CTPlay setting and change any one of them. A change from the phone takes effect at once and
  shows on the device's Play pages exactly as if made with the pads.
- A change on the device (a pad press, a project load, a phone write) reaches CTCtrl without CTCtrl asking.
- Firmware and CTCtrl can be updated separately: a newer build never breaks an older CTCtrl's understanding of the
  settings it already knows, and CTCtrl hides what it does not know.

**Non-goals (first version; user, 2026-10-18: settings only)**
- Actions: Euclid's Write / Undo, starting a count-in, anything that is not a stored setting.
- Reporting which Play page is open, or following it in CTCtrl (user, 2026-10-18: CTCtrl must not jump between its
  tabs when a page opens on the device).
- Device pages, pad numbers or the page layout in the protocol. Pages and pads may still be reshuffled (Euclid's
  place is one candidate); none of that may reach the protocol.
- A self-describing settings table that CTCtrl builds its controls from (user: hand-made CTCtrl updates for now; an
  automatic build is a later option if the feature set grows, see "Later").
- Changing stock's identity reply (Components and the uploaders parse it), or anything else stock sends.

**Anti-goals**
- A phone write that has a side effect the same pad press would not have (the obvious trap: `chord_saved_fix` frees
  every track's latched arpeggio, see "Applying a write").
- Any traffic from the device before CTCtrl has said hello: a Circuit with no app attached sends exactly what stock
  sends.

## Protocol

All messages: `F0 7D 53 4C <cmd> … F7` (`7D` = the non-commercial manufacturer ID, `53 4C` = "SL", the header PL03D's
voice log already uses; its commands are 1–3, and this protocol's commands start at 0x10 so the two never mean the same
bytes). The link and the diagnostic `voice_log` are not built together: `vl_on_sysex` claims the whole header (it
drops short messages and answers unknown commands), and the RAM pool cannot hold both (voice log 136 B). Builder: make
the build refuse that combination (my call; no such build is planned). Every
data byte is 7-bit; the settings payload goes as nibbles, high first (as the voice log does). A reply is the request's
`cmd | 0x40`.

| cmd | Direction | Body | Meaning |
|---|---|---|---|
| `10` hello | phone → device | none | Is this CTPlay, and what does it have? |
| `50` hello reply | device → phone | `proto` (1), `marker` (6 ASCII, space-padded), `layout_id`, `len` (payload bytes), `n`, then `n` × (`offset`, `size`, `rev`) | One entry per settings field **this build has**, in lock order. |
| `11` read | phone → device | none | Send the state now. |
| `51` state | device → phone | `layout_id`, `len`, `2·len` nibbles | The whole settings payload. The answer to a read, to a write, and the unsolicited push. |
| `12` write | phone → device | `offset`, `count`, `2·count` nibbles | Set payload bytes `offset … offset + count − 1`. |

- **No reply to hello = not CTPlay** (stock, upstream, an older PL build). CTCtrl decides by timeout.
- **The payload is the saved block's payload**, the byte image `saved_on_save` builds (`features/saved/saved.c`), at
  the offsets `slim/save_layout.lock` fixes: 37 B in PL11 (chord settings 0, rootless 4, strum 5, strum direction 6,
  mono 7, arp 8, retired `page_last` 16, page_quick 20, count-in 24, euclid 25, page_slot 33). Fields this build
  lacks and tombstones read 0.
- **Device navigation stays out.** `page_quick` (20–23) and `page_slot` (33–36; PL11 replaced `page_last` with it when
  Keys moved to pad 32, so the saved page is now the page's pad in the page list) are saved but are not settings: they
  are not listed in the hello reply, always read 0 in a state, are left out of the change check (a page step on the
  device sends nothing), and a write touching them is invalid. Builder: a per-field "linked" flag in `feature.toml`
  (default on, off for these two), or a list in the link feature.
- **Field entries are how CTCtrl knows what a build has** (no separate feature bits: a field is present or not, and
  its `rev` says what its bits mean). CTCtrl shows a control only for an (`offset`, `size`, `rev`) it knows, and
  ignores `layout_id` for this.
- **`rev` is new**: each `[[saved]]` entry in a `feature.toml` gets `rev` (default 1), bumped whenever the meaning of
  the field's bits changes (a new arp pattern value, a repacked field). The lock file only guards offsets and sizes;
  `rev` guards meaning. **An (`offset`, `size`, `rev`) is never reused for another meaning, across layouts too**: a
  field that reuses a retired offset (lock: `layout_id` + 1) starts at the retired field's highest `rev` + 1. So an
  older CTCtrl keeps working on every field it knows after a layout bump. A test pins every field's `rev` and the
  history of retired offsets so a meaning change cannot ship without a bump (builder: how, e.g. `rev` and
  `retired_rev` in the lock, compared in a test). (My calls, so CTCtrl can be updated by hand without guessing which
  builds it understands.)
- **A write is answered with a state**, always, valid or not. That is the acknowledgement: the phone shows what the
  device has, including the device's own corrections (picking 1/32 clears dotted). An invalid write (a range that
  touches a byte of no present field, wrong length, bad nibbles) changes nothing and is still answered. A range may
  span adjacent fields: the bass mode is two of them (bit 7 of `chord_settings[t]` and bit `t` of `chord_rootless`),
  so the phone sets it with one write of offsets `t … 4`, applied as one change.
- **One request in flight** (final review, 2026-10-19). The device answers once per LED frame: every request that
  arrived since the last frame is answered by **one** state, and it holds **one** pending write; a write that arrives
  while another is still pending is dropped (that frame's state still follows). So the phone sends a write, waits for
  a `51` (any `51` acknowledges everything outstanding), then sends the next; it re-sends a write whose value the
  state does not show only after that state. A hello and a read can share a frame with a write.
- **Writes are whole bytes.** Several fields pack all four tracks into one byte (`chord_rootless`, `chord_strum`,
  `chord_strum_down`, `chord_mono`). The phone sends the byte from its own copy. A pad press on the device in the
  same instant as a phone write to the same byte can lose one of the two; the next state shows the phone the result.
  Accepted (my call; per-bit writes would cost protocol and code for a race a person cannot really produce).

## Firmware

A new feature, `link` (name the builder's call), `depends = ["saved"]` (it reads and writes through
`slim_saved_fields[]`). Always on in the versions that include it; nothing on the device to configure.

### Who does what

| Context | Does | Never does |
|---|---|---|
| `sysex_in` hook (task **not identified**; possibly the Content task with 128–512 B of stack, SL00D TEST.md) | Recognise the header; copy a write into the mailbox; set a "hello" / "state wanted" flag with the port; return `HANDLED` for our commands, `PASS` for everything else | Touch a setting, call `sysex_out`, call `arp_free`, use more than a few dozen bytes of stack |
| `led_task` hook (UI task, the settings' single writer since PL10) | Apply a pending write; send the hello reply or a state when asked; compare the payload with the last one sent and push a state when it differs | — |

Everything that changes a setting or sends a message runs in the UI task, as every setting change does today
(`saved.c` header: "every setting keeps a single writer, the UI task"). The hand-off between the two contexts must be
safe against the UI task running in the middle of a `sysex_in` copy (builder: e.g. a ready flag written last, or
`slim_irq_save`).

### Sending from the UI task (to confirm first)

`sysex_out` (`0x08020C90`) is proven only from `sysex_in`'s own context (stock's identity responder, PL03D's voice
log). Stock does send unsolicited SysEx: the track-select message `F0 00 20 29 01 64 04 03 <index> 00 F7` that CTCtrl
follows, and the settings-store listener upstream found (`docs/NOTAS.md:984`, `0x0802A094` → `0x0803BEFA`, "probably for
Components"). The track-select one most likely goes out from the UI task when a track button is pressed. **First
task: find in emulation which function sends it and from which task, and whether it is `sysex_out`.** If the UI task
sends through `sysex_out`, this design stands. If not, the builder brings back what stock does instead before going
on (the fallback is sending from `sysex_in`'s context, which cannot push unasked).

**Confirmed in emulation 2026-10-19** (`tests/test_link.py::test_stock_sends_track_select_through_sysex_out_from_the_ui_task`):
a track press through the controller route sends the track-select message through `sysex_out`, router
`[0x200069F4]`, port mask 1 (USB). The design stands.

`sysex_out` copies the message (up to 360 B, `docs/NOTAS.md:1696`), so the outgoing message can be built on the UI task's
stack (≥ 1.5 KB free; the largest message is the hello reply or a state, under 100 B).

### Applying a write

A write must have **exactly** the effect of the same change made with pads, no more (my call on the rule):
- **Validity: the new bytes must be values the device itself can hold** (a pad result or a field's default). Anything else (spread 3, arp gate > 5, dotted at
  1/32, Euclid velocity 3, Euclid gate > 5, Euclid hits > 16, `ci_on` > 1, a rootless bit without its bass bit,
  bits 4–7 set in a per-track bitmask byte, …) makes the **whole write a no-op**, still answered with a state. Not
  corrected to a default as `chord_saved_fix` does (it zeroes a whole settings or arp byte, which is right for a bad
  project file and wrong here). The phone encodes as the pads do (picking 1/32 also clears dotted), so a CTCtrl tap
  is always valid.
- **Euclid rotation** is reduced modulo the target pattern's length `n` when applied (`ROT % n`; the pads keep it
  below `n`), so the state echo shows the device's value. `n` is not sent (it is
  pattern state, not a setting).
- **Transitions, part by part**: compare old and new per field part (pattern, rate, modifier, latch, …) and run, for
  each part that changed, the transition (`page.c` `pick_arp`, `euclid.c` `euclid_pick`): arp pattern to off →
  `arp_free(t, 0)`; latch on → off → `arp_free(t, 1)`; any Euclid setting change disarms an armed Write; the count-in
  as Shift + Clear changes it (only `ci_on`; the metronome is stock's and not in the payload).
- **not** `chord_saved_fix` as it stands: it calls `arp_free(t, 1)` for every track, which drops latched arpeggios.
  That is right after a project load and wrong after a phone write.

How (builder's call): e.g. the pad handlers' transitions moved into small per-field setters that the pads and the
link both call, or a per-feature "apply (old, new)" next to `saved_fix`. Either way there is one place per setting
that knows its side effects.

### Pushing changes

- Every LED frame, once a hello has been seen: build the payload image of the linked fields, compare it with the
  copy last sent, send a state on the hello's port when it differs. This catches pad presses, project loads (after `saved_on_leds` applies
  them) and phone writes alike, without each pad handler having to notify.
- At most one state per frame; a burst of changes coalesces into one (a project load is one state). Builder: whether
  frames need further spacing for USB; the CLAUDE.md limit is 64 MIDI messages per press from the UI task.
- After a write, a state goes out even if nothing changed (see Protocol).
- "Hello seen" is RAM only and starts cleared at power-on. It is never cleared by the device (USB MIDI has no
  port-close signal); the cost is a state on USB after a pad press when the app has gone, which stock ignores
  (Components ignores SysEx it does not know; builder: check it does not show an error).

### Resources

RAM (slim pool, PL11: 88 of 240 B used): the last-sent copy (37 B, or only the linked bytes), the write mailbox (offset, count, 8 B data, flags),
the hello port and flags: about 50 B. ITCM (about 15 KB unused, opt-in region) is the alternative if the pool is
wanted for something else (builder's call; ITCM writes follow the PL09 rules). Flash: the hello reply is a build-time
constant (marker, layout id, field entries); a few hundred bytes of code. No DSP, no stock parameter, no
`MARK_DIRTY` (the settings are slim's own RAM).

## Testing

- **Emulation, through the real route**: messages enter at the `sysex_in` hook with a stock-shaped `{buf, len}`;
  replies are caught at `sysex_out`. Cover: hello reply bytes (golden, per version); read; each field's write with its
  side effects (latched arp survives a strum write; pattern → off frees; Euclid write disarms); invalid writes answered
  and ignored; a pad press pushes one state; a project load pushes one state; no traffic before hello; stock's
  identity reply unchanged; a build with both `voice_log` and the link is refused; page steps send nothing; a
  write touching the page fields or the retired `page_last` is invalid; Euclid rotation above `n` is reduced.
- **Field `rev` pin**: as above.
- **Device**: `firmware/<MARKER>/TEST.md`, run first with a small test page under `slim/pages/` (as PL03D's
  `voice_log.html`: hello, read, a few writes, a log of pushes), so the firmware can pass on the device before CTCtrl's
  panel is done; then once with CTCtrl. Include: the Play page shows a phone write at once; a pad press shows on the
  phone; a project load shows on the phone; Components still connects and syncs with the link in the build; the
  packs read and track follow in CTCtrl still work.

## Decisions

| Decision | By |
|---|---|
| Settings only in the first version; no actions | user |
| CTCtrl does not follow the open Play page; it shows a dot on a tab whose values changed on the device | user |
| CTCtrl is updated by hand for new settings; an automatic build is a later option | user |
| Protocol speaks settings (payload offsets), never pages or pads | user (pages may be reshuffled) / mine |
| The payload is the saved block's payload; writes are byte ranges at lock offsets | mine |
| Field entries with a per-field `rev` instead of feature bits | mine |
| Every write is answered with a state (one per frame, one write in flight); whole-byte writes, a pad press and a phone write to the same byte in the same instant: whichever lands last | mine |
| Commands from 0x10, sharing the voice log's header | mine |
| All setting changes and all sends in the UI task; `sysex_in` only hands over | mine |
| Pushes only after a hello, to the hello's port | mine |
| Page state (`page_quick`, `page_slot`) not linked: not listed, read 0, not pushed, not writable | mine (follows the user's "no pages") |
| An (`offset`, `size`, `rev`) never reused across layouts; CTCtrl ignores `layout_id` | mine |
| Invalid write = whole write a no-op (not corrected); validity = what the device itself can hold | mine |
| Euclid rotation reduced mod the pattern length on apply; the length is not sent | mine |
| No build with both `voice_log` and the link | mine |
| A device test page under `slim/pages/` before CTCtrl | mine |

## Left to the builder

The feature's name; mailbox and hand-off details; where the last-sent copy lives (pool or ITCM); how `rev` is pinned;
the shape of the shared per-field setters; frame spacing for pushes; the test page's look.

## Later

- An exported settings description (names, ranges, value labels) generated by slimbuild for CTCtrl to build controls
  from, if the feature set grows.
- Actions over the link (Euclid Write / Undo, count-in).
- The quick reference / guide in CTCtrl showing only the build's features (`candidates.md`, "Companion app").
