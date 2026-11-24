/* pstrum_rec (PL19): pattern strum, recording a live strum on an active track (pstrum_mode: Played or Written, strum
 * on). Played records the strum as a plain chord (every note at the first note's step, microstep and start); Written
 * as a roll (note k at the first's position + k x WRITTEN_GAP ticks, spilling into later steps, wrapping from the
 * pattern's last step to its first). Record quantise on or off: the first note goes where stock put it.
 * Spec: docs/specs/2026-10-28-playback-strum-design.md ("Played: recording", "Written: recording"); the route and
 * every stock reading: docs/investigations/2026-10-31-pattern-strum-spike.md (route (a), fix rounds 1-3; the rule
 * modelled in q1_scope.py).
 *
 * A note is moved only when the recorder's own data proves it is its own strum's pending note, and only at a commit's
 * call site, right before stock's commit (mid hooks: rec_off_commit, the note-off path; rec_pass_commit, the tick
 * pass). Everything else stays where stock placed it.
 * - Identity, at the send (the heartbeat, Main; pstrum_rec_before / pstrum_rec_sent around each strum send of
 *   held[i]): c = the recorder's list counter [rec + 0x9C] before it; after it the send placed the note afresh iff the
 *   note's pending word has bits 0-2 == c and the list entry c holds the note; then id = (note, the entry's start, its
 *   unit). The pass copies both into the word (0x0803F748, 0x0803F768). (start, unit) is unique among a pitch's pending
 *   placements. Every note of an active strum pressed while recording is a heartbeat send (chord.c, HELD_OWN_ROOT);
 *   a strum pressed before Record went on has no root identity (pstrum_rec_off passes: stock's place).
 * - The latch prec[i] (one per held entry): track, order, the notes in send order (k = the index) and their ids.
 *   Written and read only by the heartbeat; the first send of a strum (sent == 0) or another entry's press restarts it.
 * - At the heartbeat's own note-off of note k >= 1 (pstrum_rec_off / _end), recording (stock's own condition below),
 *   the entry's pad owning the pitch, ids for k and 0: the note's word converted with (start, unit) == id -> `inflight`
 *   is armed for that note_sink_off (cleared after it); in the list with (start, unit) == id -> after the note-off, a
 *   ticket on the track (word 1: id | the entry's end << 21, written last behind a barrier; word 2: k | the first's
 *   note << 3 | its start << 10 | the tick stamp << 21). Tickets are cleared while not recording and dropped 48 ticks
 *   after their stamp (pstrum_rec_on_ms); a full track drops its oldest.
 * - pstrum_on_off_commit: `inflight` armed, its recorder (r4) and note (r1) -> the move. pstrum_on_pass_commit (r8,
 *   r1, r2): an active track, recording (the flush's pass at Stop / Record off reads not recording and stops: the UI
 *   never reads a ticket), a ticket of that track whose word 1 equals (note, the word's start and unit, end) -> the
 *   ticket cleared, the move. Tickets and `inflight` carry their track; each hook compares its recorder register with
 *   [recorders + 4 t] and re-checks the track's mode (it may change between arming and the pass).
 * - The move: the first's word (not in the list, its start == the first's id start) gives the position: Played = its
 *   step, microstep and start; Written = sixths = its microstep + roll_sixths(k x gap, ticks a step), step + sixths / 6
 *   (roll_step), microstep sixths % 6, start + k x gap. Released before that start ((end - start) & 0x7FF >= 0x400):
 *   start = end - 1. Unit: unmasked, `scan` = [rec + 0x9D] | the units other pending words claim there (as recfix's
 *   claimed()); then, interrupts off for a few instructions: recording, the note's word still (start, unit) == id,
 *   `inflight` still armed (the note-off hook), recfix not inside its pick (below); unit = the first used one with this
 *   note and microstep (stock's own search, so the commit writes there), else the first free in mask | [rec + 0x9D] |
 *   scan, its mask bit set (the reservation; the commit right after writes its bytes and ORs the bit again: nothing
 *   clears a converted word without committing it, 0x0803F88A-0x0803F8C0); the word rewritten (velocity kept);
 *   `inflight` consumed; interrupts back on. None free: Written -> unit 7 (left out), Played -> stock's place.
 * - Transport: "recording" is stock's own flush condition (the play store's listener 0x0803FF94-0x0804001C flushes
 *   when it ends): p0 (playing) and p1 (Record) and p2 == 0 (p2 != 0: not recording, as the listener reads it).
 * - Who moves: the pass hook in Main only (the tick pass; the flush's pass stops at the transport). The note-off hook:
 *   inside the heartbeat's own note_sink_off (Main), or a UI router hand-over of that very pitch preempting it, which
 *   moves the same note to the same place and consumes `inflight` (the other then finds it gone, or the word changed).
 *   Stale scan: claims change only by a conversion (the tick pass: Main, not running while the heartbeat or the pass
 *   is; the flush: UI, transport off, so the masked check fails) and by placements ([rec + 0x9D], re-read masked).
 * - recfix (features/recfix): its carry_on picks a unit and sets its mask bit with interrupts on, after a commit. In
 *   Main (a pass commit, the heartbeat's note-offs) it runs between this file's moves, never inside one: `inflight` is
 *   consumed before that commit, and the pass hook runs only in Main. In the UI task (stock's pad note-off of a note
 *   held 16 steps) Main may preempt it between its pick and its mask bit; it publishes recfix_picking[t] for that
 *   window, and a move on that track then leaves the note where stock placed it (a weak reference: builds without
 *   recfix read nothing).
 * State (ITCM, RAM only, cleared by pstrum_rec_init): prec 192 B, tickets 128 B, inflight 8 B, the waiting ticket
 * 12 B, pstrum_roll 32 B. */
#include "slim.h"
#include "stock.h"
#include "chord_held.h"
#include "roll_math.h"

#define RECORDERS     0x2003C174u   /* stock.h recorders: [+ 4 t] = note track t's recorder */
#define REC_PATTERNS  0x48u         /* rec + 0x48: -> the track's 8 patterns */
#define REC_LIST      0x54u         /* rec + 0x54 + 12 i: list entry i: [0] note (0 = empty), [2] unit, [3] bit 0 released; */
#define LIST_SIZE     12u           /* word + 4: start bits 0-10, end 11-21 */
#define LIST_N        6u
#define REC_COUNT     0x9Cu         /* byte: the next list index (the placement's counter; the pass resets it) */
#define REC_CLAIMS    0x9Du         /* byte: units claimed since the recorder's last tick pass */
#define REC_PENDING   0x9Cu         /* rec + 0x9C + 4 note: the pending word (notes 1-139) */
#define NOTES         140u
#define ID_NOTES      128u          /* an id keeps 7 bits of note */
#define PATTERN_SIZE  0xCA8u
#define PATTERN_LAST  0x380u        /* pattern + 0x380: its last step, + 0x381 its first, + 0x382 its sync rate */
#define PATTERN_FIRST 0x381u
#define PATTERN_RATE  0x382u
#define RATES         8u
#define STEPS         32u
#define STEP_SIZE     28u           /* [0] unit mask, 6 units of 4 B from + 4: note, gate, microstep, velocity */
#define UNITS         6u
#define PLAY_STORE    0x20011034u   /* stock.h play_store */
#define W_NONE(w)     (((w) & 7u) == 7u)
#define W_STEP(w)     (((w) >> 3) & 31u)
#define W_PATTERN(w)  (((w) >> 8) & 7u)
#define W_VEL_BITS    0x3F800u      /* bits 11-17 */
#define W_START(w)    (((w) >> 18) & 0x7FFu)
#define W_MICRO(w)    ((w) >> 29)
#define W_PLACE       0x7F8u        /* pattern and step */
#define ID(note, start, unit) ((note) | ((start) & 0x7FFu) << 7 | ((unit) & 7u) << 18)   /* 21 bits, never 0 */
#define ID_NOTE(id)   ((id) & 0x7Fu)
#define ID_START(id)  (((id) >> 7) & 0x7FFu)
#define ID_BITS       0x1FFFFFu
#define INFO(k, f)    ((k) | ID_NOTE(f) << 3 | ID_START(f) << 10)   /* k, the first's note and start; bits 21-31 free */
#define INFO_K(x)     ((x) & 7u)
#define INFO_FNOTE(x) (((x) >> 3) & 0x7Fu)
#define INFO_FSTART(x) (((x) >> 10) & 0x7FFu)
#define INFO_HIGH(x)  ((x) >> 21)   /* a ticket's stamp, `inflight`'s track */
#define PREC_MAX      (CHORD_MAX_OTHER + 1u)   /* the pad's note and its others */
#define TICKETS       4u            /* per track: a strum's later notes */
#define TICKET_LIFE   48u           /* ticks: two steps at the slowest rate (a ticket's pass is due within one) */
#define TOKEN_INFLIGHT 1u
#define TOKEN_TICKET   2u
#define NO_COUNT      0xFFu
#define BARRIER()     __asm__ volatile("" ::: "memory")

typedef struct {                    /* the heartbeat's: one strum of held[i] */
    uint8_t track, order, n, spare;
    uint8_t notes[PREC_MAX];        /* send order: k = the index */
    uint8_t spare2[8u - PREC_MAX];
    uint32_t id[PREC_MAX];          /* ID(note, start, unit), 0 = none */
} prec_t;

static prec_t prec[HELD] SLIM_ITCM(prec);
static uint32_t tickets[TRACKS][TICKETS][2] SLIM_ITCM(tickets);   /* [0] id | end << 21 (0 = free), [1] INFO | stamp << 21 */
static volatile uint32_t inflight[2] SLIM_ITCM(inflight);          /* [0] the id (0 = none, stored last), [1] INFO | track << 21 */
static uint32_t waiting[3] SLIM_ITCM(waiting);                      /* the heartbeat's ticket in progress: track, id, INFO */
volatile uint32_t pstrum_roll[TRACKS][2] SLIM_ITCM(pstrum_roll);
extern volatile uint8_t recfix_picking[TRACKS] __attribute__((weak));   /* features/recfix: carry_on's pick in progress */

/* recfix_picking[t], 0 in a build without recfix (its weak address is 0: the asm keeps the compiler from assuming it). */
static uint32_t recfix_busy(uint32_t t)
{
    const volatile uint8_t *p = recfix_picking;
    __asm__("" : "+r"(p));
    return p ? p[t] : 0u;
}

void pstrum_rec_init(void)
{
    memset(prec, 0, sizeof prec);
    memset(tickets, 0, sizeof tickets);
    inflight[0] = 0;
    inflight[1] = 0;
    memset(waiting, 0, sizeof waiting);
    memset((void *)pstrum_roll, 0, sizeof pstrum_roll);
}

static uint8_t *recorder(uint32_t t)
{
    return *(uint8_t *volatile *)(RECORDERS + 4u * t);
}

static uint32_t rec_track(const void *rec)
{
    uint32_t t = 0;
    while (t < TRACKS && (const void *)recorder(t) != rec)
        t++;
    return t;
}

static volatile uint32_t *pending(uint8_t *rec)
{
    return (volatile uint32_t *)(rec + REC_PENDING);
}

static const volatile uint8_t *entry(const uint8_t *rec, uint32_t i)
{
    return rec + REC_LIST + LIST_SIZE * i;
}

static uint32_t entry_word(const volatile uint8_t *e)
{
    return *(const volatile uint32_t *)(e + 4);
}

/* Is the note's word still a list index (placed, not converted)? Stock's own test (0x0803F5BC-0x0803F5D6). */
static int in_list(const uint8_t *rec, uint32_t note, uint32_t w)
{
    return !W_NONE(w) && (w & 7u) < LIST_N && entry(rec, w & 7u)[0] == note;
}

/* Stock's own recording condition (the play store's listener, 0x0803FF94-0x0804001C). */
static int recording(void)
{
    return *param_get((void *)PLAY_STORE, 0u) && *param_get((void *)PLAY_STORE, 1u) && !*param_get((void *)PLAY_STORE, 2u);
}

uint32_t pstrum_recording(void)
{
    return (uint32_t)recording();
}

void pstrum_rec_on_ms(void)
{
    uint32_t any = 0;
    for (uint32_t t = 0; t < TRACKS; t++)
        for (uint32_t j = 0; j < TICKETS; j++)
            any |= tickets[t][j][0];
    if (!any)
        return;
    uint32_t on = recording(), now = arp_tick;
    for (uint32_t t = 0; t < TRACKS; t++)
        for (uint32_t j = 0; j < TICKETS; j++) {
            uint32_t *k = tickets[t][j];
            if (k[0] && (!on || ((now - INFO_HIGH(k[1])) & 0x7FFu) > TICKET_LIFE))
                k[0] = 0;
        }
}

uint32_t pstrum_rec_before(uint32_t track)
{
    uint8_t *rec = recorder(track);
    return rec ? rec[REC_COUNT] : NO_COUNT;
}

void pstrum_rec_sent(uint32_t i, uint32_t note, uint32_t c)
{
    const held_t *h = &held[i];
    prec_t *p = &prec[i];
    if (h->sent == 0u || p->track != h->track || p->order != h->order) {   /* a strum's first send starts anew */
        p->n = 0;
        p->track = h->track;
        p->order = h->order;
    }
    if (p->n >= PREC_MAX)
        return;
    uint32_t id = 0;
    uint8_t *rec = recorder(h->track);
    if (rec && c < LIST_N && note && note < ID_NOTES && pstrum_mode(h->track) && recording()) {
        const volatile uint8_t *e = entry(rec, c);
        if ((pending(rec)[note] & 7u) == c && e[0] == note)   /* placed afresh by this send */
            id = ID(note, entry_word(e), e[2]);
    }
    p->notes[p->n] = (uint8_t)note;
    p->id[p->n] = id;
    p->n++;
}

uint32_t pstrum_rec_off(uint32_t i, uint32_t note, uint32_t own)
{
    const held_t *h = &held[i];
    const prec_t *p = &prec[i];
    uint32_t t = h->track;
    if (!own || !(h->flags & (HELD_OWN_ROOT | HELD_FALLING)) || p->track != t || p->order != h->order
        || !pstrum_mode(t))
        return 0;                                   /* Off, a plain rising strum (stock sent its first), another strum */
    uint32_t k = 1;
    while (k < p->n && p->notes[k] != note)
        k++;
    if (k >= p->n || !p->id[k] || !p->id[0] || !recording())
        return 0;
    uint8_t *rec = recorder(t);
    uint32_t id = p->id[k], info = INFO(k, p->id[0]), w = pending(rec)[note];
    if (W_NONE(w))
        return 0;
    if (in_list(rec, note, w)) {                    /* the tick pass commits it: a ticket, after the note-off */
        const volatile uint8_t *e = entry(rec, w & 7u);
        if (ID(note, entry_word(e), e[2]) != id)
            return 0;
        waiting[0] = t;
        waiting[1] = id;
        waiting[2] = info;
        return TOKEN_TICKET;
    }
    if (ID(note, W_START(w), w) != id)
        return 0;
    inflight[1] = info | t << 21;
    BARRIER();
    inflight[0] = id;                               /* last: the note-off hook reads it first */
    return TOKEN_INFLIGHT;
}

void pstrum_rec_off_end(uint32_t token)
{
    if (token == TOKEN_INFLIGHT) {
        inflight[0] = 0;                            /* used or not, it was this note-off's */
        return;
    }
    if (token != TOKEN_TICKET)
        return;
    uint32_t t = waiting[0], id = waiting[1];
    uint8_t *rec = recorder(t);
    uint32_t note = ID_NOTE(id), w = pending(rec)[note];
    if (!in_list(rec, note, w))
        return;                                     /* converted meanwhile: its commit was not ours */
    const volatile uint8_t *e = entry(rec, w & 7u);
    uint32_t ew = entry_word(e);
    if (ID(note, ew, e[2]) != id || !(e[3] & 1u))
        return;                                     /* not released by this note-off (the router's owner moved on) */
    uint32_t (*slot)[2] = tickets[t], pick = 0;
    for (uint32_t j = 0; j < TICKETS; j++) {         /* a free one, else the oldest */
        if (!slot[j][0]) {
            pick = j;
            break;
        }
        if (((arp_tick - INFO_HIGH(slot[j][1])) & 0x7FFu) > ((arp_tick - INFO_HIGH(slot[pick][1])) & 0x7FFu))
            pick = j;
    }
    slot[pick][0] = 0;
    BARRIER();
    slot[pick][1] = waiting[2] | (arp_tick & 0x7FFu) << 21;
    BARRIER();
    slot[pick][0] = id | (ew >> 11 & 0x7FFu) << 21;   /* last */
}

/* The units other pending words claim on (pattern, step) (recfix.c claimed(): placements since the last pass in
 * [rec + 0x9D], converted notes in their words' bits 0-2), the note's own word left out. Unmasked: 139 words. */
static uint32_t claims(uint8_t *rec, uint32_t place, uint32_t note)
{
    uint32_t mask = rec[REC_CLAIMS];
    const volatile uint32_t *p = pending(rec);
    for (uint32_t n = 1; n < NOTES; n++) {
        uint32_t w = p[n];
        if (n != note && !W_NONE(w) && (w & W_PLACE) == place)
            mask |= 1u << (w & 7u);
    }
    return mask;
}

/* Move `note` (pending word id = (start, unit) proved its own) of track t to its place in the strum whose first
 * note is (fnote, fstart): k = its index. `armed`: the inflight id this move consumes (0 at the pass). */
static void move(uint8_t *rec, uint32_t t, uint32_t note, uint32_t end, uint32_t id, uint32_t k, uint32_t fnote,
                 uint32_t fstart, uint32_t armed)
{
    uint32_t mode = pstrum_mode(t);
    if (!mode || k == 0u || fnote == 0u)
        return;
    volatile uint32_t *pend = pending(rec);
    uint32_t f = pend[fnote];
    if (in_list(rec, fnote, f) || W_START(f) != fstart)
        return;                                     /* the first's word gone (cut, re-armed) or not converted yet */
    uint32_t pat = W_PATTERN(f), step = W_STEP(f), micro = W_MICRO(f), start = fstart;
    uint8_t *pattern = *(uint8_t **)(rec + REC_PATTERNS) + PATTERN_SIZE * pat;
    if (mode == PSTRUM_WRITTEN) {
        uint32_t rate = pattern[PATTERN_RATE];
        if (rate >= RATES)
            return;
        uint32_t ticks = k * WRITTEN_GAP[STRUM_OF(t)], six = micro + roll_sixths(ticks, step_ticks[rate]);
        step = roll_step(step, six / 6u, pattern[PATTERN_FIRST], pattern[PATTERN_LAST]);
        micro = six % 6u;
        start = (start + ticks) & 0x7FFu;
    }
    if (((end - start) & 0x7FFu) >= 0x400u)
        start = (end - 1u) & 0x7FFu;                /* let go before its own position: the shortest note */
    if (step >= STEPS || micro >= UNITS)
        return;
    volatile uint8_t *s = pattern + STEP_SIZE * step;
    uint32_t scan = claims(rec, pat << 8 | step << 3, note);
    uint32_t primask = slim_irq_save();
    uint32_t w = pend[note];
    if (!recording() || in_list(rec, note, w) || ID(note, W_START(w), w) != (id & ID_BITS)
        || (armed && inflight[0] != armed) || recfix_busy(t)) {
        slim_irq_restore(primask);
        return;                                     /* stock's place */
    }
    uint32_t mask = s[0], unit = UNITS;
    for (uint32_t u = 0; u < UNITS; u++)            /* stock's own search: the commit writes there */
        if ((mask >> u & 1u) && s[4u + 4u * u] == note && s[6u + 4u * u] == micro) {
            unit = u;
            break;
        }
    if (unit == UNITS) {
        uint32_t taken = mask | rec[REC_CLAIMS] | scan;
        for (uint32_t u = 0; u < UNITS; u++)
            if (!(taken >> u & 1u)) {
                unit = u;
                break;
            }
        if (unit < UNITS)
            s[0] = (uint8_t)(mask | 1u << unit);    /* the reservation */
        else if (mode == PSTRUM_PLAYED) {
            slim_irq_restore(primask);
            return;                                 /* a full step: Played keeps stock's place */
        } else
            unit = 7u;                              /* Written: left out */
    }
    w = unit | step << 3 | pat << 8 | (w & W_VEL_BITS) | start << 18 | micro << 29;
    pend[note] = w;
    if (armed)
        inflight[0] = 0;                            /* consumed, before the restore */
    if (mode == PSTRUM_WRITTEN && unit < UNITS) {   /* mono record: this commit is the roll's (mono.c) */
        pstrum_roll[t][1] = fstart;
        pstrum_roll[t][0] = w;
    }
    slim_irq_restore(primask);
}

/* rec_off_commit (mid, 0x0803F606): the recorder's note-off path commits a converted note; r4 = rec, r1 = note,
 * r2 = end. */
void pstrum_on_off_commit(slim_regs_t *regs)
{
    uint32_t id = inflight[0];
    if (!id || ID_NOTE(id) != regs->r[1])
        return;
    BARRIER();
    uint32_t info = inflight[1], t = INFO_HIGH(info);
    if (t >= TRACKS || regs->r[4] != (uint32_t)recorder(t))
        return;
    move((uint8_t *)regs->r[4], t, regs->r[1], regs->r[2] & 0x7FFu, id, INFO_K(info), INFO_FNOTE(info),
         INFO_FSTART(info), id);
}

/* rec_pass_commit (mid, 0x0803F786): the tick pass commits a released list entry it just converted; r8 = rec,
 * r1 = note, r2 = end. */
void pstrum_on_pass_commit(slim_regs_t *regs)
{
    uint8_t *rec = (uint8_t *)regs->r[8];
    uint32_t note = regs->r[1], end = regs->r[2] & 0x7FFu, t = rec_track(rec);
    if (t >= TRACKS || !pstrum_mode(t) || !note || note >= ID_NOTES || !recording())
        return;
    uint32_t w = pending(rec)[note], key = ID(note, W_START(w), w) | end << 21;
    for (uint32_t j = 0; j < TICKETS; j++) {
        uint32_t *k = tickets[t][j];
        if (k[0] == key) {
            uint32_t info = k[1];
            k[0] = 0;
            move(rec, t, note, end, key, INFO_K(info), INFO_FNOTE(info), INFO_FSTART(info), 0u);
            return;
        }
    }
}
