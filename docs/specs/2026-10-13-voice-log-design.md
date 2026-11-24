# Voice log (PL03D) — design

Date: 2026-10-13 · Branch: `slim` · Version: `PL03D` (diagnostic) · Status: design approved in chat 2026-10-13, spec under
review

## Purpose

A diagnostic build that records, for every synth note-on, how stock chose the voice. It is meant to explain on the
device why a 5-note chord loses a note (PL03 step 7: rootless 9th, slow strum, the bass drops). The result decides the
next CTPlay build:
- the DSP steal is avoidable → keep the full 9th on one synth;
- the spare-time reading is per synth → spread a chord across Synth 1 and Synth 2;
- it is a real limit → the 4-note rootless 9th (bass + 3rd, 7th, 9th) as the fallback.

Success: one device session gives a log that can be read without listening for single notes. For each note-on it
shows the time, synth, note, the spare-time reading against stock's threshold, the path that picked the voice, the
voice, what that voice was doing (free, releasing, held), and the state of the synth's six voices just before.

## Decisions

- **Watch only.** No stock behaviour changes; the hooks read RAM and call nothing of stock's.
- **Pull, not push.** The log stays in RAM; a PC page asks for it over USB SysEx (upstream's request / reply scheme,
  device-proven since SC35D8). Nothing is sent while playing, so the log does not disturb the timing it measures.
  Rejected: a MIDI message per note (sent from inside the note-on with the DSP lock held, skews the timing); pad LEDs
  (too many fields to read).
- **`PL03D` = `chord` + `voice_log`**, so step 7 plays exactly as on PL03. "PL03D" and "PL03" differ in their first 6
  characters, so each installs over the other.
- **Emulation models the DSP mailbox** (approved by the user 2026-10-13): the note-on waits for the DSP to acknowledge
  a request; the test harness answers at once and serves `X:$35` / `X:$36 + synth` from values each test sets.

## Findings this design rests on

From the stock listing (`re/app.asm`) and the voice-dropout investigation
(`docs/investigations/2026-10-12-chord-voice-dropouts.md`):

- Synth note-on `0x0803BD58` → `0x080497CA` → `0x08021D86(a, note, vel)`, which stores its arguments in the voice
  state block **`S = 0x200067FC`** (`[S+0xA]` = note, `[S+0xB]` = velocity, `[S+8]` = the third argument; confirmed in
  emulation 2026-10-13: a pad note 36 at velocity 96 leaves `24 60` there) and calls the picker `0x080219E8`. All three literals that load `S`
  (`0x080217B6`, `0x080219EC`, `0x08021D8A`) hold `0x200067FC`.
- The picker calls **`0x080217B4`** (at `0x080219F0`, its only caller), which decides the voice:
  - `[S+4]` = synth (0 / 1); sends a sync request (`X:$1B`), waits, then reads **`X:$36 + synth`** with
    `dsp_read` at **`0x080217EA`**;
  - `< 0x14000`: the DSP picks (`X:$1B` = synth + 1, the answer from `X:$35`), the voice goes to `[S+5]` and
    **`[S+0xE]` = 1**; the ARM then fast-kills the voice (`0x08021246` / `0x08021272`);
  - `>= 0x14000`: the ARM picks by the polyphony mode (`0x08036188(synth, 2)`, `[S+7]`), `[S+0xE]` = 0, `[S+5]` = the
    voice; a picker answer of 1 takes the same kill path.
  - After it returns, `0x080219E8` uses `[S+5]` as the voice in both paths.
- Voice slots: 12 × 16 B at `0x20005F64` (Synth 1 owns 0–5, Synth 2 owns 6–11), state word at `+4`: a new voice gets
  `0x8000FFFF`, a note-off clears its top bits.
- The whole decision runs inside the synth note-on, which holds the DSP lock; it is reached from the UI task (pads)
  and the Main task (strum heartbeat, sequencer), so two decisions never overlap.
- Incoming SysEx: stock's dispatcher **`0x0801EB30(port, msg = {buf, len}, x)`** starts with a 4-byte
  `push.w {r4-r8, lr}`; its result is not used. Replies go through stock's SysEx output **`0x08020C90(router, port
  mask, &{buf, len})`**, with the router at `[[0x0801EDD0]]`, as stock's identity responder `0x0801EC54` does. Upstream
  builds each reply inside the request buffer, which the PC pads to 232 bytes (device-proven).

## 1. Architecture

**Foundation extension: `call` hooks on non-void functions.** Today a `call` hook runs stock's callee and then the
handlers, for `void` callees only. Extended: for a callee that returns a value, the generated wrapper keeps the result,
passes it to each handler as a last argument `uint32_t result` (read-only), and returns it to the call site unchanged.
`void` call hooks generate exactly the code they do now, so `SL00D` and `PL03` stay byte-identical
(`test_published_versions_rebuild_identically`).

**New hook points in `stock/symbols.toml`:**

| Hook point | Kind | Where | Handler gets |
|---|---|---|---|
| `voice_headroom` | call, target `dsp_read` | site `0x080217EA` only | `(core, addr, result)`: `result` = the spare-time reading |
| `voice_picked` | call, target `voice_decide` (`0x080217B4`, new `void voice_decide(void)`) | site `0x080219F0` | nothing; reads `S` |
| `sysex_in` | entry, `0x0801EB30`, displace 4 | — | `(port, msg, x)`, may return `HANDLED` |

The two voice hooks are reached with the DSP lock held: the build must refuse any call from their handlers to a
function tagged `takes_dsp_lock`, as it does for `dsp_tick` (the plan picks between declaring them `dsp_tick` and a
new context with the same rule). `voice_log` also adds a handler to the existing `main_ms` hook for its time base.

**Feature `features/voice_log/`:**
- `voice_headroom` handler: if `addr == 0x36 + [S+4]` (the spare-time read), keep `result` and a snapshot of the
  synth's six voice states in a pending slot.
- `voice_picked` handler: read `[S+4]`, `[S+5]`, `[S+7]`, `[S+0xA]`, `[S+0xE]`, combine with the pending slot and the
  millisecond counter, and append one record to the ring.
- `main_ms` handler: count milliseconds (slot 0).
- `sysex_in` handler: a message that starts with the signature is answered and swallowed (`HANDLED`); anything else
  passes to stock untouched.

## 2. The record and the ring

One record, 10 bytes:

| Field | Size | Contents |
|---|---|---|
| `t` | 2 B | milliseconds from the `main_ms` counter (wraps after 65 s) |
| `seq` | 1 B | running count of decisions (shows overwritten or missing records) |
| `flags` | 1 B | bit 0 synth, bit 1 DSP path (`[S+0xE]`), bits 2–4 polyphony mode (`[S+7]`, set by the ARM path only) |
| `note` | 1 B | the note (`[S+0xA]`) |
| `voice` | 1 B | `[S+5]` |
| `before` | 2 B | the synth's 6 voices before the decision, 2 bits each: 0 free (high half 0, as stock's pickers test it at `0x080216F0`), 1 released (high half non-zero, bit 31 clear), 2 held (bit 31 set) |
| `headroom` | 2 B | the reading `>> 4`, saturated at `0xFFFF` (threshold `0x14000` = `0x1400`) |

What the chosen voice was doing is derived on the PC from `before`: free, releasing (a fading voice cut short, which
stock's own picker does routinely) or held (a note still sounding: the loss that matters).

The ring keeps the **last 12 records** (120 B) plus its index, the counter and the pending slot (about 8 B): about
128 B. PL03 uses 88 of slim's 240 B, so PL03D uses about 216 B. A decision while the PC reads can tear one record;
acceptable for a diagnostic read after playing.

## 3. The SysEx protocol

Signature `F0 7D 53 4C` (`7D` = non-commercial id, "SL"); upstream's tools use `F0 7D 43 54`, so the two never
collide. Every request is padded with zeros to 232 bytes; the reply is built in the request buffer and sent to the
port the request came from. Numbers travel as nibbles (one 4-bit value per byte), as in upstream's protocol.

| Request | Reply |
|---|---|
| `1` ping | version, ring capacity, `seq` of the newest record |
| `2` read `start` `count` (`count` ≤ 8) | `count` records, oldest first from `start` (8 × 10 B × 2 nibbles = 160 B) |
| `3` clear | the ring emptied, `seq` kept |

A request shorter than the padded length gets no reply, so nothing is written past its buffer.

## 4. The page

`slim/pages/voice_log.html`, a static page opened straight from the repository (nothing in it depends on a build):
- connects to the Circuit Tracks over Web MIDI with SysEx (Chrome / Edge), pings, and shows the version;
- **Read** asks for the whole ring (two requests) and shows a table: time (ms, relative to the first row), synth,
  note (name and number), reading and its ratio to the threshold, path (ARM / DSP), voice, took (free / releasing / held), and
  the six voices before (free / released / held);
- **Clear** and **Copy as text** (a tab-separated copy to paste into the conversation);
- every value goes into the page as text (`textContent`), never as HTML.

## 5. Testing

- **Build:** the foundation extension changes nothing for `void` call hooks (`SL00D`, `PL03` rebuild identically);
  the new hook points' expected bytes are checked against the stock image; the voice handlers cannot reach a
  `takes_dsp_lock` function.
- **Emulation**, with the DSP mailbox model (sync and pick requests acknowledged at once; `X:$36 + synth` and `X:$35`
  from the test):
  - a pad note-on through the real route: one record with the note, synth and the ARM path; `before` matches the voice
    table;
  - a reading below `0x14000`: the DSP path, the voice from `X:$35`, shown as taken while held;
  - step 7 (rootless 9th, slow strum) with the reading dropping at the 5th note: five records in order, the steal on the
    5th;
  - the ring wraps after 12, `seq` keeps counting;
  - SysEx: ping, read (both halves), clear, a short request (no reply, nothing written past it), and a message without
    the signature reaching stock unchanged;
  - transparency: with the reading always high, PL03D sends the same notes and LEDs as PL03.
- **Page:** a unit test feeds it recorded replies and checks the table and the text copy.
- **Device:** `firmware/PL03D/TEST.md`: step 7 vs step 5 at slow and fast strum; a simple vs a rich patch; a held
  Synth 2 note from the sequencer under a Synth 1 chord (is the reading per synth or shared?); read, copy and paste the
  log after each.

## Not in scope

- Changing which voice is taken or forcing the ARM path: that is the next build, chosen from this log.
- Decoding the DSP picker's scoring (`P:$1BB3`) or the DSP side of `X:$36`.
- A general USB SysEx channel for slim: the protocol here is the voice log's own; a shared one can grow from it later.
