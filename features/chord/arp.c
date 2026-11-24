/* arp: the arpeggiator (spec 2026-10-14-arpeggiator-design.md section 3). Main task only: the heartbeat (arp_on_ms,
 * from chord_on_ms) and, while playing, the sequencer tick (Task 6) step the arpeggios and send every arpeggio note.
 * The UI task fills and frees HELD_ARP entries and writes the settings one byte at a time; this file only reads them.
 * Notes are ended from the sounding set, never recomputed from the list (it may have changed): nothing can stick. */
#include "slim.h"
#include "stock.h"
#include "chord_held.h"
#include "arp_math.h"

#define TEMPO_STORE  0x20011404u    /* stock.h tempo_store: param 0 BPM, 2 swing */
#define PLAY_STORE   0x20011034u    /* stock.h play_store: param 0 != 0 while playing */
#define PROJECT_ROOT 0x2003FA94u    /* stock.h project_root */
#define ARP_SOUND    5u             /* notes sounding at once: the chord pattern's most */
#define ARP_LIST     16u            /* distinct notes an arpeggio takes */
#define TOP          139u           /* stock plays a keyboard pitch when pitch + key is within 12-139 */
#define BOTTOM       12u
#define GATE_TICKS   0x8000u        /* run.gate counts sequencer ticks (playing), else ms (stopped) */

typedef struct {
    uint16_t gate;                  /* ticks (GATE_TICKS) or ms until the sounding notes end; 0 = at the next step */
    uint16_t pos;                   /* steps since the arpeggio started */
    uint8_t last;                   /* the list index played last (random) */
    uint8_t n;                      /* notes sounding */
    uint8_t note[ARP_SOUND], pad[ARP_SOUND];
} arp_run_t;

typedef struct {
    uint8_t note, pad, vel;
} arp_note_t;

static arp_run_t run[TRACKS] SLIM_ITCM(run);     /* ITCM (PL09) */
uint32_t arp_tick;                  /* ticks (24 per quarter note) since the last start, or since power-on */
uint16_t arp_acc;                   /* the stopped clock: + BPM per ms, a tick at 50 x swing */
static uint16_t arp_rng;
uint8_t arp_start;                  /* seq_start (UI task) sets it; the heartbeat takes it */
static uint8_t due;                 /* playing: bit t = track t's step, bit 4 + t = its gate end, for the next
                                     * heartbeat (after stock has counted the tick: the recorder gets every tick) */

void arp_init(void)
{
    memset(run, 0, sizeof run);
    arp_tick = 0;
    arp_acc = 0;
    arp_rng = 0xACE1u;
    arp_start = 0;
    due = 0;
}

static uint32_t bpm(void)
{
    uint32_t b = *param_get((void *)TEMPO_STORE, 0u);
    return b ? b : 120u;
}

/* Add `note` (with its pad and velocity) to the list: rising and the lowest ARP_LIST, or in arrival order. */
static uint32_t add(arp_note_t *l, uint32_t n, uint32_t note, const held_t *h, uint32_t rising)
{
    for (uint32_t k = 0; k < n; k++)
        if (l[k].note == note)
            return n;               /* the first entry wins */
    uint32_t at = n;
    if (rising)
        while (at && l[at - 1u].note > note)
            at--;
    if (at >= ARP_LIST)
        return n;
    if (n == ARP_LIST)
        n--;                        /* rising: the highest falls off */
    for (uint32_t k = n; k > at; k--)
        l[k] = l[k - 1u];
    l[at].note = (uint8_t)note;
    l[at].pad = h->pad;
    l[at].vel = h->vel;
    return n + 1u;
}

/* The track's arpeggio notes: every live HELD_ARP entry's own note and chord notes; "as played" walks the entries
 * oldest first (an entry's root, then its notes rising). */
static uint32_t list(uint32_t t, uint32_t played, arp_note_t *l)
{
    uint32_t n = 0, done = 0;
    for (uint32_t round = 0; round < HELD; round++) {
        uint32_t pick = HELD, age = 0;
        for (uint32_t i = 0; i < HELD; i++) {
            const held_t *h = &held[i];
            if (done & 1u << i || !h->count || !(h->flags & HELD_ARP) || h->track != t)
                continue;
            uint32_t a = (uint8_t)(chord_order[t] - h->order);
            if (pick == HELD || a > age) {
                pick = i;
                age = a;
            }
        }
        if (pick == HELD)
            break;
        done |= 1u << pick;
        const held_t *h = &held[pick];
        n = add(l, n, h->root, h, !played);
        for (uint32_t k = 0; k < (h->count & ~ARP_LIVE) && k < CHORD_MAX_OTHER; k++)
            n = add(l, n, h->notes[k], h, !played);
    }
    return n;
}

/* End the sounding notes, except the `keep` ones (a note sounding again in legato). */
static void end(uint32_t t, uint8_t *sink, const uint8_t *keep_note, const uint8_t *keep_pad, uint32_t keep)
{
    arp_run_t *r = &run[t];
    for (uint32_t i = 0; i < r->n; i++) {
        uint32_t again = 0;
        for (uint32_t k = 0; k < keep; k++)
            again |= keep_note[k] == r->note[i] && keep_pad[k] == r->pad[i];
        if (!again && sink)
            note_sink_off(sink, r->note[i], r->pad[i]);
    }
    r->n = 0;
}

static void step(uint32_t t)
{
    arp_run_t *r = &run[t];
    uint32_t a0 = chord_arp[t][0], a1 = chord_arp[t][1], pat = ARP_PATTERN(a0);
    uint8_t *sink = chord_track_sink(t);
    arp_note_t l[ARP_LIST];
    uint32_t n = sink ? list(t, pat == ARP_PLAYED, l) : 0u;
    if (!n) {
        end(t, sink, 0, 0, 0u);
        r->pos = 0;
        return;
    }
    uint32_t key = *(volatile uint8_t *)PROJECT_ROOT, oct = ARP_OCT(a1);
    uint8_t x[ARP_LIST * 4u];       /* the list over the octaves: index | octave << 5, playable notes only */
    uint32_t m = 0;
    for (uint32_t o = 0; o < oct; o++)
        for (uint32_t i = 0; i < n; i++)
            if (l[i].note + 12u * o + key <= TOP && l[i].note + 12u * o + key >= BOTTOM)
                x[m++] = (uint8_t)(i | o << 5);
    if (!m) {                       /* the key moved every note out of range: nothing to play */
        end(t, sink, 0, 0, 0u);
        return;
    }
    uint8_t note[ARP_SOUND], pad[ARP_SOUND], vel[ARP_SOUND];
    uint32_t k = 0;
    if (pat == ARP_CHORD) {
        uint32_t o = r->pos % oct;
        for (uint32_t pass = 0; pass < 2u && !k; pass++, o = 0)       /* an octave out of range: the first one */
            for (uint32_t j = 0; j < m && k < ARP_SOUND; j++)
                if ((uint32_t)(x[j] >> 5) == o) {
                    const arp_note_t *e = &l[x[j] & 31u];
                    note[k] = (uint8_t)(e->note + 12u * o);
                    pad[k] = e->pad;
                    vel[k++] = e->vel;
                }
    } else {
        uint32_t j = arp_index(pat, r->pos, m | (uint32_t)r->last << 8, &arp_rng);
        r->last = (uint8_t)j;
        const arp_note_t *e = &l[x[j] & 31u];
        note[0] = (uint8_t)(e->note + 12u * (x[j] >> 5));
        pad[0] = e->pad;
        vel[0] = e->vel;
        k = 1;
    }
    uint32_t legato = ARP_GATE(a1) == GATE_LEGATO;
    if (!legato)
        end(t, sink, 0, 0, 0u);     /* a gate longer than the step (the tempo changed): end it now */
    for (uint32_t i = 0; i < k; i++)
        chord_send_on(sink, t, note[i], vel[i], pad[i]);
    if (legato)
        end(t, sink, note, pad, k);
    for (uint32_t i = 0; i < k; i++) {
        r->note[i] = note[i];
        r->pad[i] = pad[i];
    }
    r->n = (uint8_t)k;
    uint32_t ticks = arp_gate_ticks(a0, a1);
    r->gate = (uint16_t)(*param_get((void *)PLAY_STORE, 0u) ? (ticks ? ticks | GATE_TICKS : 0u)
                                                          : arp_gate_ms(a0, a1, bpm()));
    r->pos++;
}

/* A tick: tick-counted gates count down and every track with a pattern on steps on its rate's grid. With `defer`
 * (the sequencer's tick, before stock counts it) both wait for the next heartbeat. */
void arp_on_tick(uint32_t defer)
{
    for (uint32_t t = 0; t < TRACKS; t++) {
        arp_run_t *r = &run[t];
        uint32_t a0 = chord_arp[t][0];
        if (r->n && r->gate & GATE_TICKS) {
            uint32_t g = (r->gate & ~GATE_TICKS) - 1u;
            r->gate = (uint16_t)(g ? g | GATE_TICKS : 0u);
            if (!g) {
                if (defer)
                    due |= (uint8_t)(0x10u << t);
                else
                    end(t, chord_track_sink(t), 0, 0, 0u);
            }
        }
        if (ARP_PATTERN(a0) && arp_tick % arp_rate_ticks(a0) == 0u) {
            if (defer)
                due |= (uint8_t)(1u << t);
            else
                step(t);
        }
    }
    repeat_on_tick(defer);          /* the drums' note repeat (repeat.c), on the same clock */
}

/* main_ms slot 0 (Main task, every ms): what the last tick left due, then gates, then the clock. */
void arp_on_ms(void)
{
    repeat_on_ms();                 /* the drums' new presses and due hits (repeat.c), before this clock ticks */
    uint32_t d = due;
    due = 0;
    for (uint32_t t = 0; t < TRACKS; t++)
        if (d & 0x10u << t)
            end(t, chord_track_sink(t), 0, 0, 0u);
    for (uint32_t t = 0; t < TRACKS; t++)
        if (d & 1u << t && ARP_PATTERN(chord_arp[t][0]))
            step(t);
    for (uint32_t t = 0; t < TRACKS; t++) {
        arp_run_t *r = &run[t];
        if (r->n && (!ARP_PATTERN(chord_arp[t][0]) || (r->gate && !(r->gate & GATE_TICKS) && !--r->gate)))
            end(t, chord_track_sink(t), 0, 0, 0u);
    }
    if (arp_start) {                /* tick 0 of a start (stock plays it from the Play handler) */
        arp_start = 0u;
        arp_tick = 0;
        arp_acc = 0;
        arp_on_tick(0u);
        return;
    }
    if (*param_get((void *)PLAY_STORE, 0u))
        return;                     /* playing: the sequencer's ticks (seq_tick) */
    uint32_t s = *param_get((void *)TEMPO_STORE, 2u);
    s = s < 1u ? 1u : s > 99u ? 99u : s;
    uint32_t thr = 50u * ((arp_tick / 6u) & 1u ? 100u - s : s);
    arp_acc = (uint16_t)(arp_acc + bpm());
    if (arp_acc >= thr) {
        arp_acc = (uint16_t)(arp_acc - thr);
        arp_tick++;
        arp_on_tick(0u);
    }
}

uint32_t arp_sounding(uint32_t t, uint8_t *notes)
{
    uint32_t n = run[t].n;
    for (uint32_t i = 0; i < n; i++)
        notes[i] = run[t].note[i];
    return n;
}

/* seq_start (UI task): Play started the sequencer; the heartbeat makes it tick 0. */
int arp_on_seq_start(void *engine, uint32_t *ret)
{
    (void)engine;
    (void)ret;
    arp_start = 1u;
    return SLIM_PASS;
}

/* seq_tick (Main task, while playing): the sequencer's tick, swing included. */
int arp_on_seq_tick(void *engine, uint32_t *ret)
{
    (void)engine;
    (void)ret;
    arp_tick++;
    arp_on_tick(1u);
    return SLIM_PASS;
}
