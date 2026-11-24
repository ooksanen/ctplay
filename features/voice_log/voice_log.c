/* voice_log: records how stock picks each synth voice. Spec: docs/specs/2026-10-13-voice-log-design.md.
 *
 * voice_decide (0x080217B4) reads the spare time X:$36 + synth (hook voice_headroom: the reading and a snapshot of the
 * synth's voices, before anything is picked), then picks (hook voice_picked: one record from voice_state). Both run
 * inside the synth note-on, with the DSP lock held (context dsp_locked): read RAM only, call nothing of stock's. */
#include "slim.h"
#include "stock.h"
#include "voice_log.h"

#define VS            0x200067FCu  /* stock.h voice_state; a fixed address, as the header declares it one byte long */
#define VS_SYNTH      0x04u
#define VS_VOICE      0x05u
#define VS_MODE       0x07u
#define VS_NOTE       0x0Au
#define VS_DSP        0x0Eu
#define VS_FIRST      0x10u        /* the synth's first voice */
#define VS_LAST       0x11u
#define SLOTS         0x20005F64u  /* stock.h voice_slots: 12 x 16 B */
#define SLOT_STATE    4u           /* the state word: 0x8000FFFF allocated, top bits cleared at note-off */
#define VOICES        12u
#define READ_ADDR     0x36u        /* X:$36 + synth */

vl_rec_t vl_ring[VL_CAP];
uint8_t vl_head, vl_stored, vl_seq;
uint16_t vl_now;
static uint16_t pend_before, pend_headroom;
static uint8_t pend_ok;

void vl_init(void)
{
    memset(vl_ring, 0, sizeof vl_ring);
    vl_head = vl_stored = vl_seq = 0u;
    vl_now = 0u;
    pend_before = pend_headroom = 0u;
    pend_ok = 0u;
}

static uint32_t vs(uint32_t off)
{
    return *(volatile uint8_t *)(VS + off);
}

void vl_on_headroom(uint32_t core, uint32_t addr, uint32_t result)
{
    if (core != 0u || addr != READ_ADDR + vs(VS_SYNTH))
        return;
    uint32_t first = vs(VS_FIRST), last = vs(VS_LAST), before = 0u;
    for (uint32_t v = first; v <= last && v < VOICES && v - first < 8u; v++) {
        uint32_t w = *(volatile uint32_t *)(SLOTS + 16u * v + SLOT_STATE);
        uint32_t cls = !(w >> 16) ? 0u : (w & 0x80000000u) ? 2u : 1u;   /* free as stock's pickers test it (0x080216F0) */
        before |= cls << (2u * (v - first));
    }
    pend_before = (uint16_t)before;
    pend_headroom = (uint16_t)((result >> 4) > 0xFFFFu ? 0xFFFFu : (result >> 4));
    pend_ok = 1u;
}

void vl_on_picked(void)
{
    vl_rec_t *r = &vl_ring[vl_head];
    r->t = vl_now;
    r->seq = vl_seq++;
    r->flags = (uint8_t)((vs(VS_SYNTH) & 1u) | (vs(VS_DSP) ? 2u : 0u) | (vs(VS_MODE) & 7u) << 2);
    r->note = (uint8_t)vs(VS_NOTE);
    r->voice = (uint8_t)vs(VS_VOICE);
    r->before = pend_ok ? pend_before : 0xFFFFu;
    r->headroom = pend_ok ? pend_headroom : 0u;
    pend_ok = 0u;
    vl_head = (uint8_t)((vl_head + 1u) % VL_CAP);
    if (vl_stored < VL_CAP)
        vl_stored++;
}

/* main_ms (Main task), slot 0 every 1 ms: the records' time base. */
int vl_on_ms(uint32_t slot, uint32_t *ret)
{
    (void)ret;
    if (slot == 0u)
        vl_now++;
    return SLIM_PASS;
}

/* ---- USB SysEx (spec section 3): F0 7D 53 4C cmd seq payload.. F7, padded to VL_PAD; the reply is built in the
 * request buffer (the caller owns it during the call), as upstream's rdiag does, and sent to the port it came from. */
#define VL_PAD        232u
#define CMD_PING      1u
#define CMD_READ      2u
#define CMD_CLEAR     3u
#define READ_MAX      8u
#define MIDI_ROUTER   0x200069F4u  /* stock.h midi_router: the router object's address */

typedef struct {
    uint8_t *buf;
    uint32_t len;
} vl_msg_t;

static const uint8_t SIG[4] = {0xF0u, 0x7Du, 0x53u, 0x4Cu};

/* `bytes` bytes of v, big-endian, as nibbles at p + n; returns the new n. */
static uint32_t put(uint8_t *p, uint32_t n, uint32_t v, uint32_t bytes)
{
    while (bytes--) {
        uint32_t b = (v >> (8u * bytes)) & 0xFFu;
        p[n++] = (uint8_t)(b >> 4);
        p[n++] = (uint8_t)(b & 0x0Fu);
    }
    return n;
}

int vl_on_sysex(uint32_t port, void *msg, uint32_t x, uint32_t *ret)
{
    (void)x;
    (void)ret;
    vl_msg_t *m = msg;
    if (!m || !m->buf || m->len < sizeof SIG)
        return SLIM_PASS;
    uint8_t *b = m->buf;
    for (uint32_t k = 0; k < sizeof SIG; k++)
        if (b[k] != SIG[k])
            return SLIM_PASS;
    if (m->len < VL_PAD)
        return SLIM_HANDLED;                        /* ours but too short to hold a reply: swallowed, nothing written */
    uint32_t cmd = b[4], start = b[6], count = b[7], status = 0u, n = 8u;
    if (cmd == CMD_PING) {
        n = put(b, n, VL_VERSION, 2u);
        n = put(b, n, VL_CAP, 1u);
        n = put(b, n, vl_stored, 1u);
        n = put(b, n, vl_seq, 1u);
    } else if (cmd == CMD_READ) {
        if (count > READ_MAX || start + count > vl_stored) {
            status = 2u;
        } else {
            uint32_t oldest = (vl_head + VL_CAP - vl_stored) % VL_CAP;
            n = put(b, n, count, 1u);
            for (uint32_t i = 0; i < count; i++) {
                const uint8_t *r = (const uint8_t *)&vl_ring[(oldest + start + i) % VL_CAP];
                for (uint32_t k = 0; k < sizeof(vl_rec_t); k++)
                    n = put(b, n, r[k], 1u);
            }
        }
    } else if (cmd == CMD_CLEAR) {
        vl_head = 0u;
        vl_stored = 0u;
    } else {
        status = 1u;
    }
    b[4] = (uint8_t)(cmd | 0x40u);                  /* b[5] = seq, kept */
    put(b, 6u, status, 1u);
    b[n++] = 0xF7u;
    vl_msg_t out = {b, n};
    sysex_out((void *)*(volatile uint32_t *)MIDI_ROUTER, 1u << port, &out);
    return SLIM_HANDLED;
}
