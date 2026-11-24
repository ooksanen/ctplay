/* pstrum (PL19): pattern strum, Played: a pattern's chords strum as the sequencer plays them.
 * Spec: docs/specs/2026-10-28-playback-strum-design.md ("How stock plays a step", "Played: playback", "Where it
 * hooks"); stock's player as the spike read it: docs/investigations/2026-10-31-pattern-strum-spike.md, section 4.
 *
 * Active on track t only with its pattern strum on Played and its strum speed on. At the entry of the player's
 * seq_play_step(player, pattern, step, micro) the marked units ([player + 0x13C + micro], bit u = unit u of the step)
 * that would sound (the note's bit not set in the held-tie mask [player + 0x128 ..]) are taken in strum order: by pitch,
 * rising lowest first, falling highest first. Two or more: the first keeps its mark, so stock plays it at its tick as
 * it would; the others' marks are cleared (stock then skips them whole: no note-off of their pitch, no length-list
 * entry, no note-on) and they are queued with their velocity, stock's length in ticks and their tie, and `at` = arp_tick at the hook.
 * One: stock's.
 * A step with any unit that sounds first drops the track's waiting notes (a strum is cut short by the track's next
 * notes; an empty step or a held tie carrying on does not cut it).
 *
 * Late notes: the heartbeat (chord_on_ms, Main task) sends one queued note per due wait, STRUM_GAP ms apart, the first
 * one gap after stock's, doing around it what seq_play_step does around one unit: it ends the pitch's entry if the
 * pitch still sounds (else that older entry's end would end the new note), frees the used head (the soonest to end)
 * when no entry is free (stock's allocator takes the free head unchecked), then seq_note_on(player, note, vel, length,
 * tie). The length (PL20, played strums release at once): each late note ends where stock would end it in a block
 * chord, its own length counted from the step, not from its late start: length - (arp_tick - at) ticks; with equal
 * gates all notes end together. A note that starts within one tick of its block-chord end lasts 2 ticks instead: its
 * off is on the second tick after its send, so it never shares the on's tick (stock's own gate-1 note always has a
 * full tick between on and off; a send and an off in one ms would break the one-message-per-voice-per-2-ms rule).
 * arp_tick is the sequencer's tick counter (seq_tick bumps it before the step plays). Play resets it to 0 (arp_start);
 * `now >= at ? now - at : now` is a guard only for that reset (pstrum_gen already drops stale queues on Stop).
 * Late notes never touch the batch flag 0x20006A50: nothing reads what it gates (spike).
 *
 * Queue (ITCM, RAM only, cleared by chord_init), per note track, one writer per field (as held[] in chord.c):
 * - pstrum_q[t]: note, vel, len (ticks | LEN_TIE), n, gap, gen, seq. Written only by the seq_play_step hook (the
 *   player's task: Main in emulation, tick 0 included; context any). It makes `seq` odd before it writes and stores the
 *   next even `seq` last, each behind a barrier. The heartbeat takes a queue only at an even `seq` it has not seen and
 *   reads `seq` again before each send, so it never sends from a queue half written or replaced. (Between that
 *   check and the note-on, a hook running in another task could still replace the queue: then one note of the old
 *   strum sounds, ended by its own length. Only possible if seq_play_step ever runs outside Main: never seen.)
 * - pstrum_beat[t]: seen (the `seq` taken), sent, wait. Written only by the heartbeat.
 * - pstrum_gen[t]: the player's resets (seq_end_all: Stop, the Mixer's mute; UI task), incremented by that hook only.
 *   The play-step hook reads it first and tags its queue with it; the heartbeat drops a queue whose tag is not the
 *   current value, so a reset drops every note queued before it.
 * Exact guarantee (as the live strum's, chord.c): the heartbeat cannot check "not reset" and send as one step (the
 * synth note-on takes the DSP lock: no masking around it). It reads the generation before each send and again after:
 * a reset in between (Stop's end-all in the UI task) and the note's entry still there ([player + 0x9B + note]: the
 * note-on came after the reset) -> the heartbeat ends it at once; none (the reset ended it) -> nothing to do. A late
 * note can blip at Stop; nothing sticks (as far as stock's own length list holds against Stop's reset: the races
 * between them are stock's).
 * A track not Played-and-active: the hook writes nothing (but drops a queue still holding notes, at a step that
 * sounds) and the heartbeat drops its queue (a mode or speed change mid-strum): the next step plays as stock. */
#include "slim.h"
#include "stock.h"
#include "chord_held.h"
#include "roll_math.h"

#define SEQ_PLAYERS   0x20040200u   /* stock.h seq_players; a fixed address, as the header declares it one byte long */
#define PLAYER_SIZE   0x184u        /* SEQ_PLAYERS + 0x184 t: note track t's player */
#define P_RATE_STORE  0x10u         /* player + 0x10: the track's sync rate store, parameter 1 */
#define P_PATTERNS    0x48u         /* player + 0x48: the track's 8 patterns */
#define P_FREE        0x78u         /* player + 0x78: the length list's free head, 0xFF = none */
#define P_USED        0x7Au         /* player + 0x7A: its used head (the entry that ends soonest) */
#define P_NOTE_ENTRY  0x9Bu         /* player + 0x9B + note: the note's entry, 0xFF = not sounding */
#define P_HELD_TIES   0x128u        /* player + 0x128 + 4 (note >> 5): bit note & 31 = a held tie this tick */
#define P_MARKS       0x13Cu        /* player + 0x13C + micro: the units that start now (bit u = unit u) */
#define PATTERN_SIZE  0xCA8u
#define PATTERNS      8u
#define STEPS         32u
#define STEP_SIZE     28u
#define UNITS         6u
#define UNIT(u)       (4u + 4u * (u))   /* step + UNIT(u): note, gate | tie << 7, microstep, velocity */
#define NOTES         128u
#define ENTRIES       8u            /* the length list's entries */
#define LATE_MAX      (UNITS - 1u)  /* a step's units but stock's first */
#define LEN_TIE       0x8000u       /* pq_t.len: the note starts a tie */
#define RATE_MAX      7u
#define GATE_MAX      96u
#define BARRIER()     __asm__ volatile("" ::: "memory")

typedef struct {                    /* the seq_play_step hook's */
    uint32_t at;                    /* arp_tick at the hook (PL20) */
    uint16_t len[LATE_MAX];         /* stock's ticks | LEN_TIE */
    uint8_t note[LATE_MAX], vel[LATE_MAX];
    uint8_t n;                      /* late notes queued */
    uint8_t gap;                    /* ms between them (STRUM_GAP) */
    uint8_t gen;                    /* pstrum_gen[t] when queued */
    volatile uint8_t seq;           /* odd while the hook writes; stored last */
} pq_t;

typedef struct {                    /* the heartbeat's */
    uint8_t seen;                   /* the queue's seq it took */
    uint8_t sent;                   /* late notes sent (LATE_MAX: dropped) */
    uint8_t wait;                   /* heartbeats until the next */
} pb_t;

pq_t pstrum_q[TRACKS] SLIM_ITCM(pstrum_q);
pb_t pstrum_beat[TRACKS] SLIM_ITCM(pstrum_beat);
volatile uint8_t pstrum_gen[TRACKS] SLIM_ITCM(pstrum_gen);

void pstrum_init(void)
{
    memset(pstrum_q, 0, sizeof pstrum_q);
    memset(pstrum_beat, 0, sizeof pstrum_beat);
    memset((void *)pstrum_gen, 0, sizeof pstrum_gen);
}

/* The note track of a player (exactly one of the four), else TRACKS. */
static uint32_t track_of_player(const void *player)
{
    uint32_t off = (uint32_t)player - SEQ_PLAYERS, t = off / PLAYER_SIZE;
    return t < TRACKS && off == t * PLAYER_SIZE ? t : TRACKS;
}

static int active(uint32_t t)
{
    return PSTRUM_OF(t) == PSTRUM_PLAYED && STRUM_OF(t) != 0u;
}

/* The hook's write of its queue: `seq` odd, then the fields, then the next even `seq`, each store behind a barrier. */
static void write_begin(pq_t *q)
{
    uint32_t primask = slim_irq_save();
    q->seq = (uint8_t)(q->seq | 1u);
    slim_irq_restore(primask);
}

static void write_end(pq_t *q)
{
    uint32_t primask = slim_irq_save();
    q->seq = (uint8_t)((q->seq | 1u) + 1u);
    slim_irq_restore(primask);
}

int pstrum_on_play_step(void *player, uint32_t pattern, uint32_t step, uint32_t micro, uint32_t *ret)
{
    (void)ret;
    uint32_t t = track_of_player(player);
    if (t >= TRACKS || pattern >= PATTERNS || step >= STEPS || micro >= UNITS)
        return SLIM_PASS;
    uint8_t gen = pstrum_gen[t];                    /* first: a reset from here on drops what this call queues */
    uint8_t *p = player;
    uint32_t mark = p[P_MARKS + micro];
    if (!mark)
        return SLIM_PASS;
    const uint8_t *s = *(uint8_t *const *)(p + P_PATTERNS) + PATTERN_SIZE * pattern + STEP_SIZE * step;
    uint8_t notes[UNITS];
    uint32_t sound = 0, n = 0, odd = 0;
    for (uint32_t u = 0; u < UNITS; u++) {
        uint32_t note = s[UNIT(u)];
        if (!(mark >> u & 1u))
            continue;
        if (!note || note >= NOTES) {               /* [player + 0x9B + 0] is entry 7's last byte (stock's layout); */
                                                    /* >= 128: no such note. Stock's step, whatever it does */
            odd = 1;
            continue;
        }
        if (*(const volatile uint32_t *)(p + P_HELD_TIES + 4u * (note >> 5)) >> (note & 31u) & 1u)
            continue;                               /* a held tie carries on: it does not sound */
        sound |= 1u << u;
        notes[n++] = (uint8_t)note;
    }
    if (!n && !odd)
        return SLIM_PASS;
    pq_t *q = &pstrum_q[t];
    if (n < 2u || odd || !active(t)) {
        if (q->n) {                                 /* the track's next notes cut its waiting strum short */
            write_begin(q);
            q->n = 0;
            write_end(q);
        }
        return SLIM_PASS;
    }
    roll_order(notes, n, STRUM_DOWN(t));
    uint32_t rate = *param_get(*(void **)(p + P_RATE_STORE), 1u);   /* stock's length, 0x08040F02-0x08040F58 */
    if (rate > RATE_MAX)
        rate = RATE_MAX;
    uint32_t per = step_ticks[rate], late = 0;
    write_begin(q);
    for (uint32_t k = 0; k < n; k++) {
        uint32_t u = 0;
        while (u < UNITS && !((sound >> u & 1u) && s[UNIT(u)] == notes[k]))
            u++;                                    /* the unit of notes[k] (each sounding unit once) */
        if (u == UNITS)
            break;                                  /* cannot happen: notes[] are the sounding units' */
        sound &= ~(1u << u);
        if (!k)
            continue;                               /* the first in strum order: stock's, its mark stays */
        late |= 1u << u;
        uint32_t gate = s[UNIT(u) + 1u], g = gate & 0x7Fu;
        if (!g)
            g = 1u;
        if (g > GATE_MAX)
            g = GATE_MAX;
        uint32_t ticks = g * per / 6u;
        if (!ticks)
            ticks = 1u;
        q->note[k - 1u] = notes[k];
        q->vel[k - 1u] = s[UNIT(u) + 3u];
        q->len[k - 1u] = (uint16_t)(ticks | ((gate & 0x80u) ? LEN_TIE : 0u));
    }
    q->n = (uint8_t)(n - 1u);
    q->gap = STRUM_GAP[STRUM_OF(t)];
    q->gen = gen;
    q->at = arp_tick;
    write_end(q);
    p[P_MARKS + micro] = (uint8_t)(mark & ~late);   /* stock plays the first alone */
    return SLIM_PASS;
}

int pstrum_on_reset(void *player, uint32_t *ret)
{
    (void)ret;
    uint32_t t = track_of_player(player);
    if (t < TRACKS)
        pstrum_gen[t] = (uint8_t)(pstrum_gen[t] + 1u);
    return SLIM_PASS;
}

/* One late note, as seq_play_step plays one unit. */
static void send(uint8_t *p, uint32_t note, uint32_t vel, uint32_t len, uint32_t tie)
{
    uint32_t e = p[P_NOTE_ENTRY + note];
    if (e < ENTRIES)
        seq_end_entry(p, e);                        /* its pitch still sounds: end that entry first */
    if (p[P_FREE] == 0xFFu) {                       /* no free entry: end the one that ends soonest, as stock does */
        e = p[P_USED];
        if (e >= ENTRIES)
            return;                                 /* cannot happen: every entry is free or used */
        seq_end_entry(p, e);
    }
    seq_note_on(p, note, vel, len, tie);
}

void pstrum_on_ms(void)
{
    for (uint32_t t = 0; t < TRACKS; t++) {
        pq_t *q = &pstrum_q[t];
        pb_t *b = &pstrum_beat[t];
        uint8_t seq = q->seq;
        BARRIER();
        if (seq & 1u)
            continue;                               /* the hook is writing it (another task): next heartbeat */
        if (seq != b->seen) {                       /* a new queue (or a drop): from its start */
            b->seen = seq;
            b->sent = 0;
            b->wait = q->gap;
        }
        uint32_t k = b->sent;
        if (k >= q->n)
            continue;
        uint8_t gen = pstrum_gen[t];
        if (q->gen != gen || !active(t)) {          /* reset since it was queued, or the track is no longer Played */
            b->sent = LATE_MAX;
            continue;
        }
        if (b->wait && --b->wait)
            continue;
        uint32_t note = q->note[k], vel = q->vel[k], len = q->len[k], at = q->at;
        BARRIER();
        if (q->seq != seq)
            continue;                               /* replaced while read: the next heartbeat takes the new one */
        b->sent = (uint8_t)(k + 1u);
        b->wait = q->gap;
        uint32_t now = arp_tick, elapsed = now >= at ? now - at : now, own = len & ~LEN_TIE;   /* Play reset the tick */
        len = (len & LEN_TIE) | (own > elapsed + 1u ? own - elapsed : 2u);
        uint8_t *p = (uint8_t *)(SEQ_PLAYERS + PLAYER_SIZE * t);
        send(p, note, vel, len & ~LEN_TIE, (len & LEN_TIE) ? 1u : 0u);
        if (pstrum_gen[t] != gen) {                 /* a reset during the send: end the note if the reset did not */
            uint32_t e = p[P_NOTE_ENTRY + note];
            if (e < ENTRIES)
                seq_end_entry(p, e);
            b->sent = LATE_MAX;
        }
    }
}
