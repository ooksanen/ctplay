/* Notes held past 16 steps while recording (PL15, spec 2026-10-23-chords-page-design.md, "The three fixes", item 3;
 * upstream SC45.3 / RC2.04 tools/recfix.py, the same behaviour through slim's hooks).
 *
 * Stock's commit 0x0803F7BE(rec, note, end) writes a note held 16 steps or more with a flat gate of 96 sixths
 * (0x0803F85A) and the rest is lost. Here the written unit gets the tie bit and the same note (microstep, velocity) is
 * written 16 steps later with what is left (at most 96, tied again while more is left), wrapping within the pattern's
 * first .. last step; a unit of that note there is reused, else a free one. None free, or back at the start step:
 * it stops, the last one untied. Patterns of 16 steps or less: nothing changes (a continuation would land on the
 * start step). A continuation is the held note going on: mono record's clearing (mono.c) never sees it.
 *
 * Two hooks on the commit: its entry (rec_commit, after mono's handler) latches the pending word, which the commit
 * then marks "nothing pending"; its call sites (rec_committed) act after it, before the caller's store touch, which
 * every caller makes when the commit returns non-zero (as it does for a note it wrote). A call with nothing pending
 * (the flush of notes 1-139 at Stop, stale words) latches nothing and writes nothing. RAM and stock's pattern memory
 * only, no stock calls. */
#include "slim.h"
#include "stock.h"

#define TRACKS        4u
#define RECORDERS     0x2003C174u   /* [RECORDERS + 4 t]: track t's recorder */
#define REC_PATTERNS  0x48u         /* rec + 0x48: -> the track's 8 patterns */
#define REC_PENDING   0x9Cu         /* rec + 0x9C + 4 note: the pending word (notes 1-139) */
#define REC_CLAIMS    0x9Du         /* rec + 0x9D: units claimed since the recorder's last tick pass */
#define NOTES         140u
#define PATTERN_SIZE  0xCA8u
#define PATTERN_LAST  0x380u        /* pattern + 0x380: the last step, + 0x381 the first, + 0x382 the sync rate */
#define PATTERN_FIRST 0x381u
#define PATTERN_RATE  0x382u
#define RATES         8u            /* step_ticks' words */
#define STEP_SIZE     28u           /* [0] unit mask, [1] probability, 6 units of 4 B from + 4: note, gate, microstep, vel */
#define UNITS         6u
#define STEPS         32u
#define SPAN          16u           /* the steps a gate of 96 covers */
#define GATE_MAX      96u
#define TIE           0x80u
#define PROBABILITY   7u            /* what stock's commit writes into a step's byte 1 */
#define W_NONE(w)     (((w) & 7u) == 7u)
#define W_STEP(w)     (((w) >> 3) & 31u)
#define W_PATTERN(w)  (((w) >> 8) & 7u)
#define W_START(w)    (((w) >> 18) & 0x7FFu)
#define W_MICRO(w)    ((w) >> 29)
#define W_PATTERN_BITS 0x700u
#define W_PLACE       0x7F8u        /* pattern and step */
#define LATCHED       0x80000000u
#define KEY(note, end) (LATCHED | ((end) & 0x7FFu) << 8 | (note))

/* ITCM; per track: [0] KEY(note, end) of the commit in progress (0 = none), [1] its pending word. */
static uint32_t recfix_latch[TRACKS][2] SLIM_ITCM(recfix_latch);
/* PL19: 1 while carry_on picks units and sets their mask bits on track t (in any task, interrupts on): the pattern
 * strum's recording (features/chord/pstrum_rec.c) leaves a note where stock placed it rather than pick a unit then. */
volatile uint8_t recfix_picking[TRACKS] SLIM_ITCM(recfix_picking);

static uint32_t rec_track(void *rec)
{
    uint32_t t = 0;
    while (t < TRACKS && *(void *volatile *)(RECORDERS + 4u * t) != rec)
        t++;
    return t;
}

int recfix_on_commit(void *rec, uint32_t note, uint32_t end, uint32_t *ret)
{
    (void)ret;
    uint32_t t = rec_track(rec);
    if (t >= TRACKS || note == 0u || note >= NOTES)
        return SLIM_PASS;                           /* [rec + 0x9C] is the claims / index word, not a note's */
    uint32_t w = *(volatile uint32_t *)((uint8_t *)rec + REC_PENDING + 4u * note);
    if (W_NONE(w))
        return SLIM_PASS;                           /* nothing pending: stock writes nothing */
    uint32_t primask = slim_irq_save();
    recfix_latch[t][0] = KEY(note, end);
    recfix_latch[t][1] = w;
    slim_irq_restore(primask);
    return SLIM_PASS;
}

/* Units of the step that notes still pending have claimed: stock's note-on placement (0x0803F38C) takes a unit free in
 * the step's mask | [rec + 0x9D] and sets its mask bit only at the note's commit. Claims live in [rec + 0x9D] until the
 * recorder's next tick pass (its step not kept there: taken as any step's; cleared at 0x0803F7A8), then in the
 * note's pending word (bits 0-2, with its pattern and step; notes 1-139: [rec + 0x9C] is the list's index and that
 * mask). A committed note's word reads "nothing pending". */
static uint32_t claimed(const uint8_t *rec, uint32_t w_place)
{
    uint32_t mask = *(const volatile uint8_t *)(rec + REC_CLAIMS);
    const volatile uint32_t *pending = (const volatile uint32_t *)(rec + REC_PENDING);
    for (uint32_t n = 1; n < NOTES; n++) {
        uint32_t w = pending[n];
        if (!W_NONE(w) && (w & W_PLACE) == w_place)
            mask |= 1u << (w & 7u);
    }
    return mask;
}

/* The unit of `note` on the step, else one free and not claimed; UNITS when neither. */
static uint32_t unit_for(const volatile uint8_t *step, uint32_t note, uint32_t taken)
{
    for (uint32_t u = 0; u < UNITS; u++)
        if ((step[0] >> u & 1u) && step[4u + 4u * u] == note)
            return u;
    taken |= step[0];
    for (uint32_t u = 0; u < UNITS; u++)
        if (!(taken >> u & 1u))
            return u;
    return UNITS;
}

/* Writes pattern memory with interrupts on, as stock's commit does. The latch is one per track: if a second task's
 * commit on the same track runs between another's entry and its call site (Main's tick vs the note-off path or the
 * flush, whose tasks are not identified), the first note's key no longer matches and its continuation is lost; never
 * written wrong, since only a matching key writes. Upstream's single scratch (SC45.3) has the same race. */
static void carry_on(const uint8_t *rec, uint32_t w, uint32_t note, uint32_t end)
{
    uint8_t *pattern = *(uint8_t *const *)(rec + REC_PATTERNS) + PATTERN_SIZE * W_PATTERN(w);
    uint32_t rate = pattern[PATTERN_RATE];
    if (rate >= RATES)
        return;
    uint32_t per = step_ticks[rate];
    uint32_t held = (end - W_START(w)) & 0x7FFu;
    if (!per || held / per < SPAN)
        return;                                     /* stock wrote the whole note */
    uint32_t left = held * 6u / per;                /* sixths held */
    uint32_t last = pattern[PATTERN_LAST], first = pattern[PATTERN_FIRST], s0 = W_STEP(w);
    if (left <= GATE_MAX || last >= STEPS || last < first || s0 < first || s0 > last || last - first + 1u <= SPAN)
        return;
    left -= GATE_MAX;
    uint32_t len = last - first + 1u;
    volatile uint8_t *step = pattern + STEP_SIZE * s0, *prev = 0;
    for (uint32_t u = 0; u < UNITS; u++)            /* the unit stock wrote: its search's first match, gate 96 */
        if ((step[0] >> u & 1u) && step[4u + 4u * u] == note && step[6u + 4u * u] == W_MICRO(w)) {
            prev = step + 4u + 4u * u;
            break;
        }
    if (!prev || prev[1] != GATE_MAX)
        return;
    uint8_t micro = prev[2], vel = prev[3];
    for (uint32_t s = s0;;) {
        s += SPAN;
        if (s > last)
            s -= len;
        if (s == s0)
            return;                                 /* back at the start: the last one stays untied */
        step = pattern + STEP_SIZE * s;
        uint32_t u = unit_for(step, note, claimed(rec, (w & W_PATTERN_BITS) | s << 3));
        if (u >= UNITS)
            return;                                 /* none free: the last one stays untied */
        prev[1] |= TIE;
        prev = step + 4u + 4u * u;
        prev[0] = (uint8_t)note;
        prev[1] = (uint8_t)(left < GATE_MAX ? left : GATE_MAX);
        prev[2] = micro;
        prev[3] = vel;
        step[0] |= (uint8_t)(1u << u);
        step[1] = PROBABILITY;
        if (left <= GATE_MAX)
            return;
        left -= GATE_MAX;
    }
}

void recfix_after_commit(void *rec, uint32_t note, uint32_t end, uint32_t result)
{
    (void)result;                                   /* the caller gets it unchanged: its store touch follows */
    uint32_t t = rec_track(rec);
    if (t >= TRACKS)
        return;
    uint32_t primask = slim_irq_save();
    uint32_t key = recfix_latch[t][0], w = recfix_latch[t][1];
    if (key == KEY(note, end))
        recfix_latch[t][0] = 0;
    slim_irq_restore(primask);
    if (key != KEY(note, end))
        return;                                     /* nothing pending at its entry */
    recfix_picking[t] = 1;
    carry_on(rec, w, note, end);
    recfix_picking[t] = 0;
}
