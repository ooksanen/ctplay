# Saved format 2 and link protocol 2 (the beta's saved settings)

**State:** built 2026-11-10 (plan `docs/plans/2026-11-10-saved-format-2.md`, working build PL21; device test comes with the beta build). Agreed in chat with the user (2026-11-10): the proposal below, alpha projects migrate
(read-only, until 1.0), link protocol 2 in the beta build. Part of the beta-prep build (`followups.md`, "CTPlay 1.0
beta: the checklist").

## Why
From the beta on, CTPlay is public and its saved settings become a promise: every later build reads what the beta
saves (CLAUDE.md, "slim / CTPlay is alpha until beta"). Today's container was shaped by the alpha's history: block 1
at tail + 768 is capped at 56 payload bytes so PL10–PL13 accept it, and block 2 at tail + 832 carries the rest with
a check that also covers block 1 (`features/saved/saved.c`; specs `2026-10-17-saved-settings-design.md` and
`2026-10-21-melody-variations-design.md`, "A second saved block"). None of that serves a public user, and the two
blocks hold at most 216 payload bytes. The CTCtrl link has a nearer limit: its offsets and lengths are single SysEx
bytes, so the payload must stay under 128 B (protocol 1, `link.c`'s static assert then); PL20's is 118 B. Protocol 2
(below) lifts that limit.

The checklist first said "layout 2: start the field offsets again". **Not done, on purpose:** the fields are already
packed (one 4 B hole at offset 16, the retired `page_last`), and the link's rule that an (`offset`, `size`, `rev`)
never changes meaning across layouts (spec `2026-10-18-ctctrl-link-design.md`) would make a repack a new map of every
field for CTCtrl. So the fields stay; the container changes. Call it **saved format 2**, not layout 2.

## Goals
- One block, room to grow for years, a plain header.
- A clear contract from the beta on, both ways between beta builds and dot releases:
  - **upgrading** (a newer build reads an older project): the fields it adds take their defaults;
  - **downgrading** (an older build reads a newer project): the fields it knows load, and a save keeps the newer
    fields' bytes (new: today a re-save on an older build drops them).
- The user's alpha projects keep their settings on the beta (read-only migration).
- An alpha build never loads stale settings from a project the beta saved.
- The link carries any payload length, and a state message never reaches stock's SysEx size limit.

## Non-goals
- No new setting, no change to any field's offset, size, meaning or `rev`. `save_layout.lock` keeps `layout_id = 1`
  and stays append-only.
- No change to when settings load or save (the pending byte, the UI task as every setting's single writer).
- No upstream compatibility (upstream's builds use the tail for their own data; as today, crossing between them costs
  defaults, never a crash).
- No device-wide settings (the `settings_tail` record): still later, if wanted.

## Anti-goals (a failure even if it works)
- Any change to stock's data in the record: only the tail is CTPlay's.
- A project that crashes or misbehaves on load, whatever bytes its tail holds.
- A CTCtrl that shows a wrong value: an (`offset`, `size`, `rev`) keeps its meaning.

## The block
- **Where:** the session record's tail (`record + 0x27024`, 1000 B), from **tail + 0**. Stock never reads or writes
  the tail and a new project zeroes it (saved-settings spec, "Where"; device: PL10 and PL20 round trips, Components
  included, with data at + 768 / + 832). The whole tail is CTPlay's from now on.
- **Header** (12 B, then the payload):

  | Offset | Bytes | Value |
  |---|---|---|
  | 0 | 4 | magic `CTPL` |
  | 4 | 1 | format = 2 |
  | 5 | 1 | layout ID (the lock's, 1) |
  | 6 | 2 | n = payload length, little-endian, 0 to 988 |
  | 8 | 2 | CRC-16/CCITT-FALSE (polynomial 0x1021, start value 0xFFFF), big-endian, over bytes 4 to 7 and the n payload bytes |
  | 10 | 1 | pending: `0xA5` = loaded, not applied yet (outside the CRC) |
  | 11 | 1 | reserved: written 0, not checked on load, not kept by a save |
  | 12 | n | the payload, at the lock's offsets |

  Room for the payload: 988 B.
- **Valid** = magic, format 2, layout ID equal to this build's, n at most 988, CRC matching. A block with another
  format or layout ID is not valid (a later format or layout bump is a new decision, as today).
- **Load** (the first LED frame after a load marks it pending, unchanged): a field whose bytes lie within n loads from
  the block; a field past n takes its default; bytes past this build's payload are ignored. Then the features'
  fix-ups, as today (they correct values a build cannot use).
- **Save** (`session_save`, UI task; unchanged: nothing when pending):
  - Write this build's fields at their offsets; tombstoned bytes and fields of features not in this build: 0.
  - **Keep newer bytes:** if the tail holds a valid format-2 block with n larger than this build's payload, keep its
    bytes from this build's length up to n untouched, write n as that length and recompute the CRC over all of it. So
    a project saved on a newer build and re-saved on an older one keeps the newer settings. (They belong to the same
    project: a load replaces the whole record, a new project zeroes the tail.)
  - Otherwise n = this build's payload length.
  - **Clear the alpha blocks:** when the block ends before tail + 768, zero the magic bytes of the old blocks at
    + 768 and + 832, so an alpha build finds no block and loads defaults (the block passes over them once it grows
    that far).

## Alpha migration (read-only, until 1.0)
- On load, when there is **no valid format-2 block**, read the alpha blocks with today's code (block 1 at + 768,
  block 2 at + 832, their checks): the fields keep the same offsets, so the payload image is the same.
- The first save on the beta writes a format-2 block. The alpha code is read-only and goes at 1.0 (a note in
  `followups.md`).
- An alpha project's settings that the beta's fix-ups reject take defaults, as any foreign value does.

## Link protocol 2
- **Framing:** `F0 7D 53 4C cmd ... F7`; a reply has the command or'd with `0x40`. A **two-byte value** is its low 7
  bits first, then its high 7 bits. A payload byte goes as two **nibbles**, high nibble first (each byte 0 to 15).
- **Messages** (the bytes after the command):

  | Message | Bytes |
  |---|---|
  | `10` hello, `11` read | none |
  | `12` write | offset (2), count (1, 1 to 8), 2 x count nibbles |
  | `50` hello reply | proto = 2, marker (6), layout ID, length (2), n fields, n x (offset (2), size, rev) |
  | `51` chunk | layout ID, length (2), offset (2), count (1, 1 to 64), 2 x count nibbles |

- **Hello** (`50`): the fields are the linked ones, in lock order; an (`offset`, `size`, `rev`) means what it did in
  protocol 1.
- **Chunks** (`51`): chunk k covers payload bytes 64 k to min(64 k + 63, length - 1), so every chunk but the last has
  count 64. The payload is complete when every chunk's range has arrived (each carries the length). A message is
  well under stock's 0x169 B limit (`sysex_out` `0x08020C90`). Bytes of fields that are not linked read 0.
- **The queue** (the LED task sends; one message per LED frame, the first that applies):
  1. a hello's reply;
  2. the lowest chunk that answers a write (`ack`);
  3. the lowest chunk that waits (`want`).
  - A **hello** is answered; the device then takes its current state as already sent, so nothing is pushed until
    something changes.
  - A **read** queues every chunk.
  - A **write** (offset (2), count, nibbles) is applied if every byte lies inside linked fields and the result is a
    value the device can hold; either way it queues the chunk(s) covering its range as `ack`. So a refused write, a
    write that changes nothing and a write undone by a fix-up are all answered, before any other chunk.
  - **One write in flight.** The device holds one write until its next LED frame. A second write that arrives before
    that frame is answered but **not applied**: its answer shows the bytes unchanged. So a client sends a write, waits
    for the chunk that answers it, then sends the next (a slider sends its latest value once the answer is in). As in
    protocol 1 (`2026-10-18-ctctrl-link-design.md`, "One request in flight").
  - A **malformed write** (count not 1 to 8, wrong length, a nibble over 15) is answered with chunk 0; a write past
    the payload with the last chunk.
  - After a hello, every frame compares the image with the last one sent and queues each chunk that differs (a pad
    press, a project load, a write's side effect): **pushes**. Sending chunk k records its bytes as sent and clears
    its bits.
  - **No pushes before a hello:** a write is answered, but its side effects in other chunks are not pushed.
  - Chunks go to the **newest hello's port**; a later hello from another port takes over. Before any hello they go to
    the latest requester's port.
  - Several chunks per frame is a later optimisation, after a device check (how many messages stock's `sysex_out`
    and the USB queue hold is unknown).
- **The test page `slim/pages/ctplay_link.html` moves to protocol 2 too** (my call, builder check): PL12 was first
  tested on it, before CTCtrl was ready, and the beta's TEST.md runs its link section on it, so it does not wait for
  CTCtrl's release. Its tests (`tests/test_link_page.py`) follow.
- The last-sent image (`link_sent`, ITCM) keeps one byte per payload byte.
- The hello reply also has a static assert under 0x169 B, as the chunk message has.
- Protocol 1 goes: only the user ran alpha builds. **CTCtrl** needs a release that speaks protocol 2 (and protocol 1
  for the alpha builds, if the user wants it), out with the beta. The CTCtrl side gets its own spec in
  `~/work/ctctrl`.

## Tests (emulation; `tests/test_saved.py`, `tests/test_link*.py`)
- A round trip through the real save and load routes; a save changes nothing in the record but the tail.
- A shorter payload (an older format-2 block): the missing fields take defaults.
- A longer payload (a newer build's): the known fields load; a save keeps the extra bytes and a valid CRC.
- No block, foreign bytes, a bad CRC, another format or layout ID: defaults, nothing else changes.
- Alpha migration: a PL20-style block 1 + 2 loads its settings; a block 1 alone (PL10–PL13 style) loads its fields;
  after a save the alpha magics are cleared and the format-2 block is there.
- A new project clears the block and loads the defaults; a save while pending keeps the loaded block (as today).
- Link: hello with two-byte offsets; a read in chunks covering the payload, one per frame; a write at an offset past
  127; every write answered (a no-op and a refused one too), its chunk first; a push of one changed chunk; every
  message under 0x169 B.
- **Deleted** (alpha policy: delete rather than fix): the tests that check what PL10–PL13 accept and the
  cross-version ones (`test_the_block_fits_the_64_bytes_older_builds_accept`, `test_a_pl14_project_loads_on_pl13`,
  `test_a_payload_of_56_bytes_or_less_is_block_1_alone`, `test_a_changed_block_1_drops_block_2`,
  `test_a_pl15_save_loads_on_pl18_without_harm` and their like). The alpha-block reading tests stay while migration
  stays.
- `resources.md` gets the new "Saved" row (one block, its room).

## Device test (in the beta's TEST.md)
- Settings survive a save, a power cycle and a load; through Components (the Components test).
- An alpha project (saved on PL20) loads its settings on the beta; after a save on the beta, PL20 loads that project
  with defaults (one round trip to an alpha build, allowed here: it checks the clearing, and compatibility starts now).
- The link, on `pages/ctplay_link.html`: hello, a read (every chunk arrives), a write answered at once (also a refused
  one), pad presses pushed. Then CTCtrl's protocol-2 release, when it is ready.

## Left to the builder
Where the format-2 code and the alpha reader
live in `saved.c`, the static asserts that replace today's (the payload fits the tail; a chunk message fits the
SysEx limit), and how the tests build an alpha block.
