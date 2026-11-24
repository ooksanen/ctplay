/* saved: the CTPlay settings saved with the project (PL10, spec docs/specs/2026-10-17-saved-settings-design.md).
 *
 * The block sits in the session record's tail (record + 0x27024, 1000 B stock saves and loads with the project but
 * never reads). Format 2 (spec docs/specs/2026-11-10-saved-format-2-design.md, "The block"), at tail + 0: "CTPL",
 * format 2, layout ID, payload length n (2 B, little-endian), a CRC-16/CCITT-FALSE (big-endian) over format, ID, n and
 * the n payload bytes, pending, 0, payload. The payload is a byte image of the features' [[saved]] globals, at the
 * offsets save_layout.lock gives them (the generated slim_saved_fields[]); a field past n takes its default.
 *
 * A save keeps a newer build's bytes: when the tail holds a valid block with n above this build's payload, the bytes
 * from this build's length up to n stay as they are, n stays, the CRC covers all of it. While the block ends before
 * tail + 768 a save zeroes the alpha blocks' magics there, so an alpha build finds no block and loads defaults.
 *
 * The alpha blocks (PL10-PL20) are read only when no format-2 block is valid (read-only, removed at 1.0, followups.md):
 * block 1 at tail + 768, "CTPS", layout ID, n, CRC-8 over (ID, n, payload), pending, payload (at most 56 B); PL14's block 2 at tail + 832, "CTP2", layout ID, n2,
 * a CRC-16/CCITT-FALSE (big-endian) over block 1's ID, n, check and 56 payload bytes and block 2's ID, n2 and payload;
 * then the payload from byte 56 on. Block 2 counts only when block 1 is valid with n = 56 and its own magic, ID, n2 and
 * check match. Same offsets: the payload image is the same.
 *
 * Stock's save (session_save, UI task) writes the block from the globals, unless a load is still pending: then the tail
 * holds the loaded block, which is the one to save. The end of stock's load (session_applied, task not identified) only
 * marks the tail pending, and so does init (a load before slim's first hook call). The next LED frame (UI task) clears
 * pending and copies the block into the globals, or the defaults when there is none, then runs the features' fix-ups.
 * So every setting keeps a single writer, the UI task. No RAM of its own. */
#include "slim.h"
#include "stock.h"
#include "slim_saved.h"

#define SESSION     0x2003D71Cu     /* stock.h session (a fixed address: the header declares it one byte long) */
#define REC_PTR     0x14u           /* session + 0x14: the session record, 0 before it exists */
#define TAIL        0x27024u        /* the record's tail */
#define TAIL_SIZE   1000u
#define F_FORMAT    4u              /* format 2 */
#define F_ID        5u
#define F_LEN       6u              /* little-endian */
#define F_CRC       8u              /* big-endian */
#define F_PENDING   10u
#define HDR2        12u
#define ROOM        (TAIL_SIZE - HDR2)
#define FORMAT      2u
#define PENDING     0xA5u           /* loaded, not applied yet */

/* The alpha blocks (read only). */
#define BLOCK       768u            /* block 1: tail + 768 */
#define BLOCK_MAX   64u
#define SPLIT       56u             /* block 1's payload bytes */
#define BLOCK2      64u             /* block 2: tail + 832, from block 1 */
#define BLOCK2_MAX  168u            /* the tail's last 168 B */
#define O_ID        4u
#define O_LEN       5u
#define O_CHECK     6u
#define HDR         8u

_Static_assert(HDR2 + SLIM_SAVED_LEN <= TAIL_SIZE, "the saved payload outgrew the tail");

static const uint8_t MAGIC_F2[4] = {'C', 'T', 'P', 'L'};
static const uint8_t MAGIC[4] = {'C', 'T', 'P', 'S'};
static const uint8_t MAGIC2[4] = {'C', 'T', 'P', '2'};

static uint8_t *tail(void)
{
    uint8_t *rec = *(uint8_t *volatile *)(SESSION + REC_PTR);
    return rec ? rec + TAIL : 0;
}

static int is(const uint8_t *p, const uint8_t *magic)
{
    for (uint32_t i = 0; i < 4u; i++)
        if (p[i] != magic[i])
            return 0;
    return 1;
}

/* CRC-16/CCITT-FALSE: polynomial 0x1021, from 0xFFFF. */
static uint32_t crc16(uint32_t crc, const uint8_t *p, uint32_t n)
{
    while (n--) {
        crc ^= (uint32_t)*p++ << 8;
        for (uint32_t k = 0; k < 8u; k++)
            crc = crc & 0x8000u ? (crc << 1 ^ 0x1021u) & 0xFFFFu : crc << 1 & 0xFFFFu;
    }
    return crc;
}

/* Format 2's check: format, ID, n and the n payload bytes. */
static uint32_t check_f2(const uint8_t *t, uint32_t n)
{
    return crc16(crc16(0xFFFFu, t + F_FORMAT, 4u), t + HDR2, n);
}

/* The payload length of a valid format-2 block, or 0. */
static uint32_t valid_f2(const uint8_t *t)
{
    uint32_t n = t[F_LEN] | (uint32_t)t[F_LEN + 1u] << 8;
    if (!is(t, MAGIC_F2) || t[F_FORMAT] != FORMAT || t[F_ID] != SLIM_SAVED_LAYOUT || n > ROOM)
        return 0;
    if ((uint32_t)(t[F_CRC] << 8 | t[F_CRC + 1u]) != check_f2(t, n))
        return 0;
    return n;
}

static uint32_t crc8(uint32_t crc, const uint8_t *p, uint32_t n)
{
    while (n--) {
        crc ^= *p++;
        for (uint32_t k = 0; k < 8u; k++)
            crc = crc & 0x80u ? (crc << 1 ^ 0x07u) & 0xFFu : crc << 1 & 0xFFu;
    }
    return crc;
}

/* The alpha block 1's payload length (b = block 1), or 0: CRC-8, polynomial 0x07, over (ID, n) and the payload. */
static uint32_t valid(const uint8_t *b)
{
    uint32_t n = b[O_LEN];
    if (!is(b, MAGIC) || b[O_ID] != SLIM_SAVED_LAYOUT || HDR + n > BLOCK_MAX)
        return 0;
    if (b[O_CHECK] != crc8(crc8(0, b + O_ID, 2u), b + HDR, n))
        return 0;
    return n;
}

/* The alpha block 2's payload length (b = block 1, valid with n1 payload bytes), or 0. Its check: block 1's ID, n,
 * check (not pending) and 56 payload bytes; block 2's ID, n2 and payload. */
static uint32_t valid2(const uint8_t *b, uint32_t n1)
{
    const uint8_t *b2 = b + BLOCK2;
    uint32_t n2 = b2[O_LEN];
    if (n1 != SPLIT || !is(b2, MAGIC2) || b2[O_ID] != SLIM_SAVED_LAYOUT || HDR + n2 > BLOCK2_MAX)
        return 0;
    uint32_t crc = crc16(0xFFFFu, b + O_ID, 3u);
    crc = crc16(crc, b + HDR, SPLIT);
    crc = crc16(crc, b2 + O_ID, 2u);
    if ((uint32_t)(b2[O_CHECK] << 8 | b2[O_CHECK + 1u]) != crc16(crc, b2 + HDR, n2))    /* big-endian */
        return 0;
    return n2;
}

/* The payload bytes the alpha blocks hold (b = block 1), or 0. Out of line, as load_fields. */
static __attribute__((noinline)) uint32_t alpha_len(const uint8_t *b)
{
    uint32_t n = valid(b);
    return n + valid2(b, n);
}

/* Payload byte i in the alpha blocks (b = block 1): block 1 up to SPLIT, block 2 after. */
static const uint8_t *alpha_at(const uint8_t *b, uint32_t i)
{
    return i < SPLIT ? b + HDR + i : b + BLOCK2 + HDR + (i - SPLIT);
}

static void mark_pending(void)
{
    uint8_t *t = tail();
    if (t)
        t[F_PENDING] = PENDING;
}

void saved_init(void)
{
    mark_pending();                             /* a load before slim's first hook call: the first frame applies it */
}

/* session_applied: the end of stock's load (task not identified): one byte store, nothing else. */
void saved_on_applied(void *obj, uint32_t what, uint32_t arg)
{
    (void)obj;
    (void)what;
    (void)arg;
    mark_pending();
}

/* session_save (UI task): the blobs are in the record, the file is written from it later. */
void saved_on_save(void *obj)
{
    (void)obj;
    uint8_t *t = tail();
    if (!t || t[F_PENDING] == PENDING)
        return;                                 /* loaded, not applied yet: the tail holds the block to save */
    uint32_t n = valid_f2(t);                   /* a newer build's block: its bytes past ours stay */
    if (n < SLIM_SAVED_LEN)
        n = SLIM_SAVED_LEN;
    memset(t, 0, HDR2 + SLIM_SAVED_LEN);        /* tombstones and fields of features not in this build: 0 */
    for (uint32_t i = 0; i < SLIM_SAVED_N; i++) {
        const slim_saved_field_t *f = &slim_saved_fields[i];
        memcpy(t + HDR2 + f->offset, f->addr, f->size);
    }
    memcpy(t, MAGIC_F2, sizeof MAGIC_F2);
    t[F_FORMAT] = FORMAT;
    t[F_ID] = SLIM_SAVED_LAYOUT;
    t[F_LEN] = (uint8_t)n;
    t[F_LEN + 1u] = (uint8_t)(n >> 8);
    uint32_t crc = check_f2(t, n);
    t[F_CRC] = (uint8_t)(crc >> 8);             /* big-endian */
    t[F_CRC + 1u] = (uint8_t)crc;
    if (HDR2 + n <= BLOCK) {                    /* the alpha blocks' magics: an alpha build loads defaults */
        memset(t + BLOCK, 0, sizeof MAGIC);
        memset(t + BLOCK + BLOCK2, 0, sizeof MAGIC2);
    }
}

/* The loaded fields into the globals: from the format-2 block, or (alpha) the alpha blocks; a field past n takes its
 * default (a shorter payload, an older layout's). Out of line: its frame and the fix-ups' never add up (the hook's
 * stack budget). */
static __attribute__((noinline)) void load_fields(const uint8_t *t, uint32_t n, uint32_t alpha)
{
    for (uint32_t i = 0; i < SLIM_SAVED_N; i++) {
        const slim_saved_field_t *f = &slim_saved_fields[i];
        uint32_t end = f->offset + f->size;
        for (uint32_t k = 0; k < f->size; k++) {
            uint32_t j = f->offset + k;
            f->addr[k] = end > n ? f->def[k] : alpha ? *alpha_at(t + BLOCK, j) : t[HDR2 + j];
        }
    }
}

/* led_task (UI task), before the features draw: a pending load's settings into the globals. */
void saved_on_leds(void *ctrl, uint16_t *out)
{
    (void)ctrl;
    (void)out;
    uint8_t *t = tail();
    if (!t || t[F_PENDING] != PENDING)
        return;
    t[F_PENDING] = 0;
    uint32_t n = valid_f2(t);                   /* the payload bytes the block holds */
    uint32_t alpha = !n;
    if (alpha)                                  /* no format-2 block: an alpha project's blocks, or none; the
                                                 * alpha reader is read-only, removed at 1.0 (followups.md) */
        n = alpha_len(t + BLOCK);
    load_fields(t, n, alpha);
    slim_saved_fix();
}
