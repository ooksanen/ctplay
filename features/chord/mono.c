/* Mono record (PL08, spec 2026-10-17-small-features-design.md section 3, D6, D7): on a track with its chord_mono bit, a
 * note stock's recorder writes into a step removes the step's other notes unless they were recorded together with it.
 *
 * Hook rec_commit: the entry of the recorder's commit 0x0803F7BE(rec, note, end), before stock writes the note's unit
 * (after it a write and a no-op look the same). Only live recording reaches it (step entry does not).
 *
 * Recorded together = recorded in the same visit of the step (the spec's section 3): the same pattern and step, starts
 * less than two steps apart (start: the note-on's tick, counted from Play mod 2048; with stock's record quantise off it
 * carries the note's offset in the step). So a chord's notes, an arpeggio's chord step and notes played into one step
 * keep each other; a pass later the start differs by the loop's length, so the step clears again (a loop of two steps
 * or fewer keeps stacking). The first commit of a visit clears the step's other units; stock then writes its own.
 * RAM and stock's pattern memory only, no calls; reached from the Main task and the UI task, so the body runs with
 * interrupts off.
 *
 * PL19, an active Written track only: a roll's notes commit in the heartbeat's note-off order, not by position (a
 * falling roll's root commits after its bass, one step back: spike q1_mono_order), so a roll's commit into a step that
 * roll already cleared counts as the same visit. A roll's commit = the word pstrum_rec.c's move just wrote
 * (pstrum_roll[t][0]); "already cleared by the roll" = one of the track's last MONO_PAST visits holds it (in_visit)
 * and started within the roll (its start at most ROLL_SPAN ticks after the roll's first note's). Off and Played: as
 * PL18 (mono_past is kept on every track but read only on an active Written track). */
#include "slim.h"
#include "chord_held.h"

#define RECORDERS     0x2003C174u   /* [RECORDERS + 4 t]: track t's recorder */
#define REC_PATTERNS  0x48u         /* rec + 0x48: -> the track's 8 patterns */
#define REC_PENDING   0x9Cu         /* rec + 0x9C + 4 note: the pending word */
#define NOTES         140u          /* the recorder's flush 0x0803F67C: notes 1-139 */
#define PATTERN_SIZE  0xCA8u
#define PATTERN_RATE  0x382u        /* pattern + 0x382: its sync rate, the index of STEP_TICKS */
#define STEP_TICKS    0x0805B8B8u   /* stock's ticks per step by rate: 2 3 4 6 8 12 16 24 (the commit's literal 0x0803F8D0) */
#define RATES         8u
#define STEP_SIZE     28u           /* [0] unit mask, [1] probability, 6 units of 4 B from + 4: note, length, microstep, vel */
#define UNITS         6u
#define W_NONE(w)     (((w) & 7u) == 7u)     /* bits 0-2: the unit, 7 = nothing pending */
#define W_STEP(w)     (((w) >> 3) & 31u)
#define W_PATTERN(w)  (((w) >> 8) & 7u)
#define W_START(w)    (((w) >> 18) & 0x7FFu)
#define W_PLACE       0x7F8u        /* pattern and step */
#define W_KEY         0x1FFC07F8u   /* start, pattern, step */
#define NO_VISIT      0xFFFFFFFFu   /* never w & W_KEY */
#define MONO_PAST     4u            /* PL19: the visits before the last one, kept for a roll's late commits */
#define ROLL_SPAN     16u           /* PL19: a roll's last note, ticks after its first (4 x WRITTEN_GAP slow) */

static uint32_t mono_visit[TRACKS] SLIM_ITCM(mono_visit);   /* ITCM (PL09); per track: the last visit (w & W_KEY of its first note), NO_VISIT when none */
static uint32_t mono_past[TRACKS][MONO_PAST] SLIM_ITCM(mono_past);   /* PL19: the visits before it, newest first */

void mono_init(void)
{
    for (uint32_t t = 0; t < TRACKS; t++) {
        mono_visit[t] = NO_VISIT;
        for (uint32_t j = 0; j < MONO_PAST; j++)
            mono_past[t][j] = NO_VISIT;
    }
}

/* Is w in the visit v: the same pattern and step, starts less than two steps apart (either way round mod 2048)? */
static int in_visit(uint32_t v, uint32_t w, const uint8_t *pattern)
{
    if (v == NO_VISIT || (v ^ w) & W_PLACE)
        return 0;
    uint32_t rate = pattern[PATTERN_RATE];
    uint32_t window = 2u * (rate < RATES ? ((const uint32_t *)STEP_TICKS)[rate] : 6u);
    uint32_t d = (W_START(w) - W_START(v)) & 0x7FFu;
    return d < window || 0x800u - d < window;
}

/* PL19: is w a Written roll's commit into a step the roll already cleared? (Interrupts off.) */
static int in_roll(uint32_t t, uint32_t w, const uint8_t *pattern)
{
    if (pstrum_mode(t) != PSTRUM_WRITTEN || pstrum_roll[t][0] != w)
        return 0;
    pstrum_roll[t][0] = 0;
    uint32_t first = pstrum_roll[t][1];
    for (uint32_t j = 0; j < MONO_PAST; j++) {
        uint32_t v = mono_past[t][j];
        if (in_visit(v, w, pattern) && ((W_START(v) - first) & 0x7FFu) <= ROLL_SPAN)
            return 1;
    }
    return 0;
}

int mono_on_commit(void *rec, uint32_t note, uint32_t end, uint32_t *ret)
{
    (void)end;
    (void)ret;
    uint32_t t = 0;
    while (t < TRACKS && *(void *volatile *)(RECORDERS + 4u * t) != rec)
        t++;
    if (t >= TRACKS || !((chord_mono >> t) & 1u) || note >= NOTES)
        return SLIM_PASS;
    uint8_t *r = rec;
    uint32_t w = *(volatile uint32_t *)(r + REC_PENDING + 4u * note);
    if (W_NONE(w))
        return SLIM_PASS;                           /* nothing pending: stock writes nothing */
    uint32_t primask = slim_irq_save();
    uint8_t *pattern = *(uint8_t **)(r + REC_PATTERNS) + PATTERN_SIZE * W_PATTERN(w);
    if (!in_visit(mono_visit[t], w, pattern) && !in_roll(t, w, pattern)) {
        volatile uint8_t *step = pattern + STEP_SIZE * W_STEP(w);
        uint32_t keep = 1u << (w & 7u);             /* the unit stock writes: the one with the note and microstep ... */
        for (uint32_t u = 0; u < UNITS; u++)
            if ((step[0] >> u & 1u) && step[4u + 4u * u] == note && step[6u + 4u * u] == w >> 29) {
                keep = 1u << u;                     /* ... (stock's search, first match), else bits 0-2 */
                break;
            }
        step[0] &= (uint8_t)keep;
        for (uint32_t j = MONO_PAST - 1u; j; j--)
            mono_past[t][j] = mono_past[t][j - 1u];
        mono_past[t][0] = mono_visit[t];
        mono_visit[t] = w & W_KEY;
    }
    slim_irq_restore(primask);
    return SLIM_PASS;
}
