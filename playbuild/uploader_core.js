// CTPlay uploader core: pure JavaScript, no DOM, no Web MIDI, no crypto. A plain script (no import / export):
// Node `require`s it for the tests and the page inlines it as it is.
// Format reference: tools/ct_fw.py. Ported from CIRCUIT-HACKS-RC's uploader by Ghillermo (MIT licence).
//
// Contract for checking a user's file, so that no exception escapes:
//   1. The caller tries `img = imageOf(name, u8)` (it throws an Error with a plain message on a bad file),
//   2. and hashes the image (SHA-256, lowercase hex) -> `sha`; if `imageOf` threw, it passes `sha = null`,
//   3. then calls `checkFirmware(name, u8, sha)`, which never throws: it returns { ok, image?, message }.
//      The message of a bad file is the decode error's plain text.

var NOVATION_HEADER = [0xF0, 0x00, 0x20, 0x29, 0x00];
var STOCK_IMAGE_SHA256 = "b897e0f01c403974eafae32074876234f2da7ef834796a485993acf01423f8da";
var STOCK_HEADER_VERSION = 0x572;     // protocol number, 1.2.1 build 4486
var MAX_IMAGE_SIZE = 0x70000;

var CRC_TABLE = (function () {
  var t = new Uint32Array(256);
  for (var i = 0; i < 256; i++) {
    var c = i << 24;
    for (var k = 0; k < 8; k++) c = (c & 0x80000000) ? ((c << 1) ^ 0x04C11DB7) : (c << 1);
    t[i] = c >>> 0;
  }
  return t;
})();

// CRC-32/MPEG-2 (poly 0x04C11DB7, init 0xFFFFFFFF, no reflection, no final xor).
function crc32mpeg(u8) {
  var c = 0xFFFFFFFF;
  for (var i = 0; i < u8.length; i++) c = ((c << 8) ^ CRC_TABLE[((c >>> 24) ^ u8[i]) & 0xFF]) >>> 0;
  return c >>> 0;
}

function nibblesToNumber(arr) {
  var v = 0;
  for (var i = 0; i < arr.length; i++) {
    if (arr[i] > 15) throw new Error("The file has a bad number in its header.");
    v = v * 16 + arr[i];
  }
  return v;
}

function numberToNibbles(v, n) {
  var o = [];
  for (var i = n - 1; i >= 0; i--) o.push(Math.floor(v / Math.pow(16, i)) % 16);
  return o;
}

// 37 bytes of 7 bits = 32 bytes + 3 zero bits.
function unpackBlock(p) {
  if (p.length !== 37) throw new Error("The file has a data block of the wrong length (" + p.length + ").");
  var bits = 0n;
  for (var i = 0; i < p.length; i++) {
    if (p[i] & 0x80) throw new Error("The file has a byte that MIDI cannot carry.");
    bits = (bits << 7n) | BigInt(p[i]);
  }
  bits >>= 3n;
  var out = new Uint8Array(32);
  for (var j = 31; j >= 0; j--) { out[j] = Number(bits & 0xFFn); bits >>= 8n; }
  return out;
}

function packBlock(b) {
  var bits = 0n;
  for (var i = 0; i < b.length; i++) bits = (bits << 8n) | BigInt(b[i]);
  bits <<= 3n;
  var o = new Array(37);
  for (var j = 36; j >= 0; j--) { o[j] = Number(bits & 0x7Fn); bits >>= 7n; }
  return o;
}

function splitSyx(u8) {
  var msgs = [];
  for (var i = 0; i < u8.length;) {
    var s = u8.indexOf(0xF0, i);
    if (s < 0) break;
    var e = u8.indexOf(0xF7, s);
    if (e < 0) throw new Error("The file ends in the middle of a message. It looks cut short.");
    var m = u8.slice(s, e + 1);
    for (var k = 0; k < 5; k++) if (m[k] !== NOVATION_HEADER[k]) throw new Error("This is not a Novation firmware file.");
    msgs.push(m);
    i = e + 1;
  }
  return msgs;
}

// Decode a .syx: { image, headerVersion }. Throws Error with a plain message.
function parseSyx(u8) {
  var msgs = splitSyx(u8);
  if (msgs.length < 3) throw new Error("This is not a firmware file, or it is too short.");
  var cmd = msgs.map(function (m) { return m[5]; });
  var inner = cmd.slice(2, -1);
  if (cmd[0] !== 0x71 || cmd[1] !== 0x7C || cmd[cmd.length - 1] !== 0x73 || inner.some(function (c) { return c !== 0x72; }))
    throw new Error("The messages in this file are not in the order of a firmware update. The file may be cut short.");
  var init = msgs[0].slice(6, -1);
  if (init[0] !== 0x01 || init[1] !== 0x64) throw new Error("This is not a Circuit Tracks firmware file.");
  var hdr = msgs[1].slice(6, -1);
  if (hdr.length < 23) throw new Error("The file's header is too short.");
  var headerVersion = nibblesToNumber(hdr.slice(1, 7));
  var size = nibblesToNumber(hdr.slice(7, 15)), crc = nibblesToNumber(hdr.slice(15, 23));
  var blocks = [unpackBlock(msgs[msgs.length - 1].slice(6, -1))];
  for (var i = 2; i < msgs.length - 1; i++) blocks.push(unpackBlock(msgs[i].slice(6, -1)));
  var all = new Uint8Array(blocks.length * 32);
  blocks.forEach(function (b, n) { all.set(b, n * 32); });
  if (size > all.length) throw new Error("The file holds less data than its header says. It looks cut short.");
  if (size > MAX_IMAGE_SIZE) throw new Error("The file's size is not valid.");
  var image = all.slice(0, size);
  if (crc32mpeg(image) !== crc) throw new Error("The file's checksum does not match. The file is damaged.");
  return { image: image, headerVersion: headerVersion };
}

function decodeSyx(u8) { return parseSyx(u8).image; }

// = ct_fw.encode(image): protocol 0x572, product 0x64. Returns the whole .syx as one Uint8Array.
function encodeSyx(img) {
  var pad = new Uint8Array(Math.ceil(img.length / 32) * 32).fill(0xFF);
  pad.set(img);
  var H = NOVATION_HEADER, msgs = [];
  msgs.push([].concat(H, [0x71, 0x01, 0x64, 0x00, 0x00], numberToNibbles(STOCK_HEADER_VERSION, 4), [0xF7]));
  msgs.push([].concat(H, [0x7C, 0x00], numberToNibbles(STOCK_HEADER_VERSION, 6), numberToNibbles(img.length, 8),
                      numberToNibbles(crc32mpeg(img), 8), [0xF7]));
  for (var i = 32; i < pad.length; i += 32) msgs.push([].concat(H, [0x72], packBlock(pad.subarray(i, i + 32)), [0xF7]));
  msgs.push([].concat(H, [0x73], packBlock(pad.subarray(0, 32)), [0xF7]));
  var n = 0, p = 0;
  msgs.forEach(function (m) { n += m.length; });
  var out = new Uint8Array(n);
  msgs.forEach(function (m) { out.set(m, p); p += m.length; });
  return out;
}

// Ops: [0, offset, length] copies from src; [1, base64] adds bytes.
function applyPatch(src, ops) {
  var n = 0, i, o;
  for (i = 0; i < ops.length; i++) {
    o = ops[i];
    n += o[0] === 0 ? o[2] : atob(o[1]).length;
  }
  var out = new Uint8Array(n), p = 0;
  for (i = 0; i < ops.length; i++) {
    o = ops[i];
    if (o[0] === 0) {
      if (o[1] < 0 || o[2] < 0 || o[1] + o[2] > src.length) throw new Error("The patch does not fit this firmware.");
      out.set(src.subarray(o[1], o[1] + o[2]), p);
      p += o[2];
    } else {
      var s = atob(o[1]);
      for (var k = 0; k < s.length; k++) out[p++] = s.charCodeAt(k);
    }
  }
  return out;
}

function isSyxName(name) { return /\.syx$/i.test(String(name)); }

// The image of a user's file: decoded for a .syx, the bytes themselves for anything else. Throws on a bad .syx.
function imageOf(name, u8) { return isSyxName(name) ? decodeSyx(u8) : u8; }

function hex(v) { return "0x" + v.toString(16); }

// See the contract at the top. `imageSha` = SHA-256 (lowercase hex) of imageOf(name, u8), or null if imageOf threw.
function checkFirmware(name, u8, imageSha) {
  var NOT_STOCK = "This is not the official 1.2.1 (build 4486) firmware.";
  var image, version = null;
  try {
    if (isSyxName(name)) { var d = parseSyx(u8); image = d.image; version = d.headerVersion; }
    else image = u8;
  } catch (e) {
    return { ok: false, message: String(e && e.message ? e.message : e) };
  }
  var headerOk = version === null || version === STOCK_HEADER_VERSION;   // a .syx with another header is refused even if the image is stock
  if (imageSha === STOCK_IMAGE_SHA256 && headerOk) return { ok: true, image: image, message: "This is the official 1.2.1 (build 4486) firmware." };
  var msg = NOT_STOCK;
  if (!headerOk)
    msg += " It is Novation firmware with header version " + hex(version) + " (1.2.1 build 4486 has " + hex(STOCK_HEADER_VERSION) + ").";
  return { ok: false, message: msg };
}

// The Send gate. s = { fileOk, built, port, mode: "bootloader"|"firmware"|null, runningOverride, backup, risk, official, busy }
// Stock's reply to the Universal identity request (F0 7E 7F 06 01 F7): F0 7E dev 06 02, Novation 00 20 29, then
// d[8] = mode (0x01 firmware, 0x11 bootloader), d[9] = 0x64 Circuit Tracks, 00 00, the build in d[14..15]. Upstream's
// pages read the mode from d[9] (the product byte), so they never saw either mode. Null when it is no identity reply.
function parseIdentity(d) {
  if (d.length !== 17 || d[0] !== 0xF0 || d[1] !== 0x7E || d[3] !== 0x06 || d[4] !== 0x02 || d[16] !== 0xF7) return null;
  var tracks = d[5] === 0x00 && d[6] === 0x20 && d[7] === 0x29 && d[9] === 0x64 && d[10] === 0 && d[11] === 0;
  return { tracks: tracks, mode: d[8] === 0x01 ? "firmware" : d[8] === 0x11 ? "bootloader" : null,
           build: d[14] * 128 + d[15] };
}

function canSend(s) {
  return !!(s.fileOk && s.built && s.port && !s.busy && s.backup && (s.official || s.risk) &&
            (s.mode === "bootloader" || (s.mode === "firmware" && s.runningOverride)));
}

if (typeof module !== "undefined") {
  module.exports = { crc32mpeg: crc32mpeg, decodeSyx: decodeSyx, encodeSyx: encodeSyx, applyPatch: applyPatch,
                     imageOf: imageOf, checkFirmware: checkFirmware, parseIdentity: parseIdentity, canSend: canSend,
                     STOCK_IMAGE_SHA256: STOCK_IMAGE_SHA256 };
}
