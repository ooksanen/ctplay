// Minimal Emscripten shim for Novation Components' Circuit Tracks project validator (spike, 2026-11-11).
// The wasm stays in ext/ (Novation's file): loaded by path, never copied.
// Usage (from the repo root): node tests/validator.mjs <record file> ...
// Prints one JSON line per file: {"file", "ok", "errors": [log lines, ANSI stripped]}. Exit 0 always (see "ok").
import fs from 'node:fs';

// The wasm is found by glob under ext/ (the repo root is one level up from this file); never copied into the repo.
const DIR = new URL('../ext/circuittracksreverseengineering/Assets/Novation-Components/', import.meta.url);
const WASM = new URL(fs.readdirSync(DIR).filter((f) => /^circuit-tracks-project-validator-.*\.wasm$/.test(f))
  .sort()[0], DIR);

export async function load() {
  let mem, ex;
  const u8 = () => new Uint8Array(mem.buffer);
  const dv = () => new DataView(mem.buffer);
  const cstr = (p) => { const b = u8(); let e = p; while (b[e]) e++; return Buffer.from(b.subarray(p, e)).toString(); };
  let out = [];
  const fds = new Map();                       // fd -> {data, pos}
  let nextFd = 3;
  const EBADF = 8, ENOENT = 44;
  const imports = { a: {
    a: () => { throw new Error('abort'); },
    b: (fd, iov, cnt, pnum) => {               // fd_write
      let n = 0; const v = dv();
      for (let i = 0; i < cnt; i++) {
        const p = v.getUint32(iov + 8 * i, true), l = v.getUint32(iov + 8 * i + 4, true);
        if (fd === 1 || fd === 2) out.push(Buffer.from(u8().subarray(p, p + l)).toString());
        n += l;
      }
      v.setUint32(pnum, n, true); return 0;
    },
    c: (fd) => { fds.delete(fd); return 0; },  // fd_close
    d: () => 0,                                // __syscall_fcntl64
    e: (ptr, type, destr) => { throw new Error(`c++ exception ptr=${ptr} type=${type}`); },  // __cxa_throw
    f: (size) => ex.w(size),                   // __cxa_allocate_exception (malloc)
    g: (pc, psz) => { dv().setUint32(pc, 0, true); dv().setUint32(psz, 0, true); return 0; },  // environ_sizes_get
    h: (fd, iov, cnt, pnum) => {               // fd_read
      const f = fds.get(fd); if (!f) return EBADF;
      let n = 0; const v = dv();
      for (let i = 0; i < cnt; i++) {
        const p = v.getUint32(iov + 8 * i, true), l = v.getUint32(iov + 8 * i + 4, true);
        const chunk = f.data.subarray(f.pos, f.pos + l);
        u8().set(chunk, p); f.pos += chunk.length; n += chunk.length;
        if (chunk.length < l) break;
      }
      v.setUint32(pnum, n, true); return 0;
    },
    i: () => 0,                                // __syscall_ioctl (not a tty: fine either way)
    j: (path, flags, va) => {                  // __syscall_open
      const p = cstr(path);
      try { fds.set(nextFd, { data: fs.readFileSync(p), pos: 0 }); } catch { return -ENOENT; }
      return nextFd++;
    },
    k: (fd, lo, hi, whence, pnew) => {         // fd_seek (i64 legalised to lo / hi)
      const f = fds.get(fd); if (!f) return EBADF;
      const off = hi * 0x100000000 + (lo >>> 0);
      f.pos = whence === 0 ? off : whence === 1 ? f.pos + off : f.data.length + off;
      dv().setBigInt64(pnew, BigInt(f.pos), true); return 0;
    },
    l: (d, s, n) => { u8().copyWithin(d, s, s + n); },   // emscripten_memcpy_big
    m: (size) => {                             // emscripten_resize_heap
      const need = Math.ceil((size - mem.buffer.byteLength) / 65536);
      try { mem.grow(need); return 1; } catch { return 0; }
    },
    n: () => 0,                                // strftime_l (unused)
    o: () => 0,                                // environ_get
  } };
  const { instance } = await WebAssembly.instantiate(fs.readFileSync(WASM), imports);
  ex = instance.exports; mem = ex.p;
  ex.q();                                      // __wasm_call_ctors
  const take = () => { const s = out.join(''); out = []; return s; };
  const str = (s) => { const b = Buffer.from(s + '\0'); const p = ex.w(b.length); u8().set(b, p); return p; };
  return {
    ex, take,
    // s(path, quiet): validate the file at path; returns 1 if it is valid.
    file(path, quiet = false) { const ok = ex.s(str(path), quiet ? 1 : 0); return { ok: !!ok, log: take() }; },
    // t(vec, quiet): validate a record in wasm memory; vec -> std::vector<uint8_t> {begin, end, end_cap}.
    buf(data, quiet = false) {
      const p = ex.w(data.length); u8().set(data, p);
      const vec = ex.w(12); const v = new DataView(mem.buffer);
      v.setUint32(vec, p, true); v.setUint32(vec + 4, p + data.length, true); v.setUint32(vec + 8, p + data.length, true);
      const ok = ex.t(vec, quiet ? 1 : 0); return { ok: !!ok, log: take() };
    },
  };
}

const ANSI = /\x1b\[[0-9;]*m/g;
if (import.meta.url === `file://${process.argv[1]}`) {
  for (const f of process.argv.slice(2)) {
    const v = await load();                    // fresh instance per record: validator state never leaks between files
    const r = v.buf(fs.readFileSync(f), false);
    const errors = r.log.replace(ANSI, '').split('\n').map((l) => l.trim()).filter(Boolean);
    process.stdout.write(JSON.stringify({ file: f, ok: r.ok, errors }) + '\n');
  }
}
