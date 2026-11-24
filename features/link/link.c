/* link: the CTCtrl link (PL12, spec docs/specs/2026-10-18-ctctrl-link-design.md), protocol 2 since saved2
 * (spec 2026-11-10-saved-format-2-design.md, "Link protocol 2").
 *
 * F0 7D 53 4C cmd .. F7, replies cmd | 0x40; a two-byte value is its low 7 bits, then its high 7 bits. Hello 10 -> 50
 * (protocol, marker, layout, payload length (2), the linked fields' offset (2) / size / rev); read 11 -> every chunk
 * 51 (layout, length (2), offset (2), count, the chunk's bytes as nibbles, high first); write 12 (offset (2), count,
 * nibbles) -> the chunks its range touches. A chunk is CHUNK payload bytes (the last one fewer). The payload is the
 * saved block's (features/saved), with the bytes of fields that are not linked (device navigation, tombstones) read 0.
 *
 * sysex_in (task not identified) only copies a request into the mailbox. The LED task (UI task, every setting's single
 * writer) applies a write and sends one message a frame: a hello's reply, else the lowest chunk answering a write
 * (ack), else the lowest chunk waiting (want: a read, or a change against the last-sent image once a hello came: a
 * pad press, a project load or a write alike). Every write is answered, refused, malformed or changing nothing. */
#include "slim.h"
#include "stock.h"
#include "slim_saved.h"
#include "slim_link.h"

#define MIDI_ROUTER  0x200069F4u    /* stock.h midi_router: the router object's address */
#define CMD_HELLO    0x10u
#define CMD_READ     0x11u
#define CMD_WRITE    0x12u
#define REPLY        0x40u
#define PROTO        2u
#define W_MAX        8u             /* bytes in one write */
#define REQ_HELLO    1u
#define REQ_READ     2u
#define REQ_WRITE    4u
#define HDR          5u             /* F0 7D 53 4C cmd */
#define CHUNK        64u
#define CHUNKS       ((SLIM_SAVED_LEN + CHUNK - 1u) / CHUNK)
#define LAST         (CHUNKS - 1u)
#define CHUNK_MSG    (HDR + 6u + 2u * CHUNK + 1u)            /* layout, len, off, count, nibbles, F7: 140 B */
#define HELLO_MSG    (HDR + 11u + 4u * SLIM_LINK_N + 1u)    /* proto, marker, layout, len, n, the fields, F7 */

/* The queues are uint16_t, a bit a chunk; stock's sysex_out (0x08020C90) drops a message of 0x169 B or more. */
_Static_assert(SLIM_SAVED_LEN <= 16u * CHUNK, "the saved payload outgrew the link's 16 chunks");
_Static_assert(CHUNK_MSG < 0x169u, "a chunk message outgrew stock's SysEx output");
_Static_assert(HELLO_MSG < 0x169u, "the hello reply outgrew stock's SysEx output");

typedef struct {
    uint8_t *buf;
    uint32_t len;
} link_msg_t;

static const uint8_t SIG[4] = {0xF0u, 0x7Du, 0x53u, 0x4Cu};

/* The mailbox: written by sysex_in, read and cleared by the LED task, both with interrupts masked. */
static volatile uint8_t req, req_port, w_cnt;
static volatile uint16_t w_off, req_ack;          /* req_ack: the chunks answering the writes since the last frame */
static volatile uint8_t w_data[W_MAX];

/* The LED task's alone (ITCM, saved2). */
static struct {
    uint16_t ack, want;                           /* bit k = chunk k: a write's answer; a read or a change */
    uint8_t port, hello;                          /* where chunks go: the newest hello's port, before one the requester's; 1 once a hello came */
} q SLIM_ITCM(link_queue);
static uint8_t sent[SLIM_SAVED_LEN] SLIM_ITCM(link_sent);   /* the image last sent (ITCM, PL16) */

/* req_port: the request's port, but a hello's while one waits (only a hello's port can take the link over). */
#define TAKE_PORT(flags, port) \
    do { if (!(req & REQ_HELLO) || ((flags) & REQ_HELLO)) req_port = (uint8_t)(port); } while (0)

static void post(uint32_t flags, uint32_t acks, uint32_t port)
{
    uint32_t pm = slim_irq_save();
    TAKE_PORT(flags, port);
    req |= (uint8_t)flags;
    req_ack |= (uint16_t)acks;
    slim_irq_restore(pm);
}

static uint32_t chunk_bit(uint32_t i)            /* the chunk holding payload byte i, past the payload the last */
{
    i /= CHUNK;
    return 1u << (i < LAST ? i : LAST);
}

/* A write's count, its bytes into data; 0 when it is malformed. */
static uint32_t parse_write(const uint8_t *b, uint32_t n, uint8_t *data)
{
    uint32_t cnt = n >= HDR + 4u ? b[HDR + 2u] : 0;
    if (cnt < 1u || cnt > W_MAX || n != HDR + 4u + 2u * cnt)
        return 0;
    for (uint32_t i = 0; i < cnt; i++) {
        uint32_t hi = b[HDR + 3u + 2u * i], lo = b[HDR + 4u + 2u * i];
        if (hi > 0xFu || lo > 0xFu)
            return 0;
        data[i] = (uint8_t)(hi << 4 | lo);
    }
    return cnt;
}

/* A write's body (offset, count, 2 * count nibbles) into the mailbox, one pending at a time (a second before the frame
 * is dropped); answered with the chunks its range touches, chunk 0 when it is malformed. */
static void take_write(const uint8_t *b, uint32_t n, uint32_t port)
{
    uint8_t data[W_MAX];
    uint32_t cnt = parse_write(b, n, data);
    if (!cnt) {
        post(0, 1u, port);
        return;
    }
    uint32_t off = b[HDR] | (uint32_t)b[HDR + 1u] << 7;
    uint32_t acks = chunk_bit(off) | chunk_bit(off + cnt - 1u);
    uint32_t pm = slim_irq_save();
    if (!(req & REQ_WRITE)) {
        w_off = (uint16_t)off;
        w_cnt = (uint8_t)cnt;
        for (uint32_t i = 0; i < cnt; i++)
            w_data[i] = data[i];
        req |= REQ_WRITE;                         /* in this section: a second sysex_in cannot see the mailbox half filled */
    }
    req_ack |= (uint16_t)acks;
    TAKE_PORT(0u, port);
    slim_irq_restore(pm);
}

/* sysex_in: ours = our header, a known command and F7 last; everything else goes on to stock. */
int link_on_sysex(uint32_t port, void *msg, uint32_t x, uint32_t *ret)
{
    (void)x;
    (void)ret;
    link_msg_t *m = msg;
    if (!m || !m->buf || m->len < HDR + 1u)
        return SLIM_PASS;
    const uint8_t *b = m->buf;
    uint32_t n = m->len;
    for (uint32_t k = 0; k < sizeof SIG; k++)
        if (b[k] != SIG[k])
            return SLIM_PASS;
    if (b[n - 1u] != 0xF7u)
        return SLIM_PASS;
    uint32_t cmd = b[4];
    if ((cmd == CMD_HELLO || cmd == CMD_READ) && n == HDR + 1u) {
        post(cmd == CMD_HELLO ? REQ_HELLO : REQ_READ, 0, port);
        return SLIM_HANDLED;
    }
    if (cmd == CMD_WRITE) {                     /* answered, valid or not */
        take_write(b, n, port);
        return SLIM_HANDLED;
    }
    return SLIM_PASS;
}

/* The state image: every linked field's bytes from its global, the rest 0. */
static void link_image(uint8_t *p)
{
    memset(p, 0, SLIM_SAVED_LEN);
    for (uint32_t i = 0; i < SLIM_LINK_N; i++)
        for (uint32_t k = 0; k < SLIM_SAVED_N; k++) {
            const slim_saved_field_t *f = &slim_saved_fields[k];
            if (f->offset == slim_link_fields[i].offset)
                memcpy(p + f->offset, f->addr, f->size);
        }
}

/* The linked field holding payload byte i, or 0. */
static const slim_link_field_t *linked_at(uint32_t i)
{
    for (uint32_t k = 0; k < SLIM_LINK_N; k++)
        if (i - slim_link_fields[k].offset < slim_link_fields[k].size)
            return &slim_link_fields[k];
    return 0;
}

/* A write: every byte inside linked fields, and no part it changes made a value the device cannot hold (oddities a
 * load left are not the write's), or nothing at all. Then the globals,
 * then each feature's link_apply: the side effects the same pad presses have. */
static void apply_write(uint32_t off, uint32_t cnt, const uint8_t *data)
{
    for (uint32_t i = off; i < off + cnt; i++)
        if (i >= SLIM_SAVED_LEN || !linked_at(i))
            return;
    uint8_t old[SLIM_SAVED_LEN], cand[SLIM_SAVED_LEN];
    link_image(old);
    memcpy(cand, old, SLIM_SAVED_LEN);
    memcpy(cand + off, data, cnt);
    if (!slim_link_valid(cand, old))
        return;
    for (uint32_t k = 0; k < SLIM_SAVED_N; k++) {
        const slim_saved_field_t *f = &slim_saved_fields[k];
        if (linked_at(f->offset))
            memcpy(f->addr, cand + f->offset, f->size);
    }
    slim_link_apply(old);
}

static uint32_t head(uint8_t *buf, uint32_t cmd)
{
    memcpy(buf, SIG, sizeof SIG);
    buf[4] = (uint8_t)(cmd | REPLY);
    return HDR;
}

static uint32_t two(uint8_t *buf, uint32_t n, uint32_t v)   /* a two-byte value at buf + n; the next n */
{
    buf[n] = (uint8_t)(v & 0x7Fu);
    buf[n + 1u] = (uint8_t)(v >> 7 & 0x7Fu);
    return n + 2u;
}

static void send(uint8_t *buf, uint32_t n)
{
    buf[n++] = 0xF7u;
    link_msg_t out = {buf, n};
    sysex_out((void *)*(volatile uint32_t *)MIDI_ROUTER, 1u << q.port, &out);
}

static void send_hello(void)
{
    uint8_t buf[HELLO_MSG];
    uint32_t n = head(buf, CMD_HELLO);
    buf[n++] = PROTO;
    memcpy(buf + n, SLIM_LINK_MARKER, 6u);
    n += 6u;
    buf[n++] = SLIM_SAVED_LAYOUT;
    n = two(buf, n, SLIM_SAVED_LEN);
    buf[n++] = SLIM_LINK_N;
    for (uint32_t i = 0; i < SLIM_LINK_N; i++) {
        n = two(buf, n, slim_link_fields[i].offset);
        buf[n++] = slim_link_fields[i].size;
        buf[n++] = slim_link_fields[i].rev;
    }
    send(buf, n);
}

/* Chunk k of the image; it is then in sync, and neither queue holds it. */
static void send_chunk(const uint8_t *img, uint32_t k)
{
    uint8_t buf[CHUNK_MSG];
    uint32_t o = k * CHUNK, c = SLIM_SAVED_LEN - o < CHUNK ? SLIM_SAVED_LEN - o : CHUNK;
    uint32_t n = head(buf, CMD_READ);
    buf[n++] = SLIM_SAVED_LAYOUT;
    n = two(buf, n, SLIM_SAVED_LEN);
    n = two(buf, n, o);
    buf[n++] = (uint8_t)c;
    for (uint32_t i = o; i < o + c; i++) {
        buf[n++] = img[i] >> 4;
        buf[n++] = img[i] & 0xFu;
    }
    send(buf, n);
    memcpy(sent + o, img + o, c);
    q.ack &= (uint16_t)~(1u << k);
    q.want &= (uint16_t)~(1u << k);
}

/* led_task (UI task), after saved's apply of a load: apply a write, then send one message. */
void link_on_leds(void *ctrl, uint16_t *out)
{
    (void)ctrl;
    (void)out;
    uint8_t data[W_MAX];
    uint32_t pm = slim_irq_save();
    uint32_t r = req, a = req_ack, port = req_port, off = w_off, cnt = w_cnt;
    for (uint32_t i = 0; i < W_MAX; i++)
        data[i] = w_data[i];
    req = 0;
    req_ack = 0;
    slim_irq_restore(pm);
    if (r & REQ_HELLO || ((r | a) && !q.hello))  /* PL12: after a hello every chunk goes to its port; a new hello takes over */
        q.port = (uint8_t)port;
    if (r & REQ_WRITE)
        apply_write(off, cnt, data);
    q.ack |= (uint16_t)a;
    if (r & REQ_READ)
        q.want = (uint16_t)((1u << CHUNKS) - 1u);
    uint8_t img[SLIM_SAVED_LEN];
    link_image(img);
    if (r & REQ_HELLO) {
        q.hello = 1;
        memcpy(sent, img, SLIM_SAVED_LEN);      /* the phone reads next: nothing to push until something changes */
        send_hello();
        return;
    }
    if (q.hello)
        for (uint32_t i = 0; i < SLIM_SAVED_LEN; i++)
            if (img[i] != sent[i])
                q.want |= (uint16_t)chunk_bit(i);
    uint32_t w = q.ack ? q.ack : q.want;
    if (w)
        send_chunk(img, (uint32_t)__builtin_ctz(w));
}
