# Spike: Components' project validator under Node.js (2026-11-11)

## Answer: it works
Node 24 runs `ext/circuittracksreverseengineering/Assets/Novation-Components/circuit-tracks-project-validator-*.wasm`
with a 101-line import shim (`validator.mjs`), without Novation's JS and without downloading anything. The wasm is a
plain Emscripten command-line build (`basic-cmd-line -i <session_file_path>`), no embind. About 10 ms per validation
quiet (70 ms with the log), 3 ms to instantiate; one instance validates 1,300 records in a row.

## The wasm
Imports `a.a`–`a.o` (minified), mapped from their call sites: `a` abort, `b` fd_write, `c` fd_close, `d` fcntl64,
`e` __cxa_throw, `f` __cxa_allocate_exception, `g` environ_sizes_get, `h` fd_read, `i` ioctl, `j` open(path, flags,
va), `k` fd_seek(fd, lo, hi, whence, pnew), `l` memcpy_big, `m` resize_heap, `n` strftime_l, `o` environ_get. Only
`b` (the log), `l`, `m` do real work, plus `c` / `h` / `j` / `k` in file mode (`open` served from Node's `fs`).

Exports: `p` memory, `q` __wasm_call_ctors, `r` main, `s`, `t` (below), `u` table, `v` __errno_location, `w` malloc,
`x` stackSave, `y` stackRestore, `z` stackAlloc.

## Entry points (call `q()` once first)
- `s(path, quiet)` → 1 valid / 0 invalid; `path` a C string in wasm memory (`w`), read through the file imports.
- `t(vec, quiet)` → 1 / 0; `vec` = a 12-byte `std::vector<uint8_t>` (begin, end, end_cap) over the 0x2740C-byte record
  in wasm memory. Not a raw pointer (that reads every field as 0).
- `quiet = 0` logs to fd 1 with ANSI colours, e.g. `Error @ validator::Session::validateHeader() : var
  (sessionData.header.featureFlags.reserved) == 128 : Some reserved feature flags are set`.

## Results (records dumped through stock's real save route in emulation, `dump_records.py`)
| Record | Result |
|---|---|
| stock 4486, new project, saved | VALID |
| same, `header.featureFlags.reserved` set (byte 0x09 = 0x01 or 0x0B = 0x80) | INVALID, "Some reserved feature flags are set" |
| same, signature `XSER` | INVALID, "Session has unrecognised signature" |
| same, tail (0x27024, 1000 B) all 0xA5 or all 0xFF | VALID |
| PL21, every CTPlay setting set (`DISTINCT`, the CTPL block at tail + 0) | VALID |

Byte-flip sweep (`sweep.mjs`, each byte XOR 0xFF): header, timing (`spare1` 0x38, `spare2` 0x3C), scene chains
(start / end / padding) trip it; the session patch data is checked up to 0x27023; **no byte from 0x27024 to 0x2740B
changes the result** (the tail is unchecked). The project name (0x10–0x34) and some pattern bytes are not checked.

## As a pytest check
- `validator.mjs` (the shim only; the wasm stays in `ext/`, never copied) moves to `slim/tests/`; a helper
  `tests/components.py: validate(record) -> (ok, log)` runs Node on a temp file (a batch mode keeps it to a few ms per
  record) and skips when `node` or the wasm is missing.
- Tests after `save(h)`: stock; PL21 with `DISTINCT`; PL21 defaults; a project heavy on drums, chords, rolls, recfix
  ties and trig conditions; plus a negative control (the reserved flag) so a broken shim cannot pass.
- Limits: it checks the record in RAM as the save leaves it (FatFs is not emulated; the same 0x2740C bytes as the
  .ncs, `totalSessionSize`); it checks stock's fields only (a guard against CTPlay's stray writes into patterns,
  chains, scale or patches), never CTPlay's tail; the import mapping is inferred (the controls show the checks run).

## Files
The spike's own scripts were not kept (removed 2026-11-21). What carries on is in the tests: the shim
`slim/tests/validator.mjs`, the helper `slim/tests/components.py` and `slim/tests/test_components_validator.py`. The
dumped records (`stock.rec`, `pl21.rec`) held stock's factory patch data: they were never committed, and the tests
make their own.
