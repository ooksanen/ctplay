/* The Pattern tools page (page 4 of a synth or MIDI track): Euclidean fills (PL11, spec
 * docs/specs/2026-10-17-euclidean-design.md, "Decided at planning"). UI task only.
 *
 * Pads 1-16 pick k hits (pad k) and preview the rhythm over the steps of the track's current pattern: hit bright, no
 * hit dim, past the pattern's length dark (a pattern longer than 16 steps: its first 16). 17 / 18 rotate the hits one
 * step earlier / later, 19 back to rotation 0; 20 the rhythm source (Euclid / groove, PL13), 21 the gate (as the Arp
 * page's, plus "to the next hit"), 22-24 velocity; 25-28 the cycle (PL14: 3, 5, 6, 7 steps; the lit pad turns it off;
 * the preview is the final rhythm, the rotate pads wrap at the cycle); 29 / 30 the dice (melody.c); 31 Undo, 32 Write.
 * The target is read at every use: the pattern the track plays now and its first / last step, so the preview follows
 * a pattern change or a new length at once.
 *
 * Write: the first press arms (pad 32 blinks), the second calls euclid_write_to, which rewrites all 32 steps of the
 * target: the hits on its steps first .. last, the rhythm from Euclid or the groove (melody_groove), the notes from
 * the Melody settings (melody.c: the root, and the chord on it for order "same", else one note of the line per hit),
 * velocity and length per hit (accent, gate or "to the next hit"); every other step empty; settings and automation
 * stay. Any other press disarms. Undo keeps the replaced steps (ITCM) and where they came
 * from; it swaps them back, so pressing it again redoes. A project load drops it. A Write that used a new setting starts a draft (melody.c): later picks re-write
 * that pattern at once (Write 0x45) until Undo, the pages closing or a link write. The sequencer (Main task) reads the
 * steps while it plays: the copy and the rewrite run with interrupts masked, so it never sees half a pattern.
 * PL17: the drums (t = 4-7) have the same pages on their own settings (tools_euclid / tools_rhythm / tools_seed), the
 * roll on pad 21 and dice notes dark; their target is the shown pattern, their Write and Undo drum_tools.c's (with no
 * drum recorder there is no target: n = 0, no preview, Write dark, nothing written). */
#include "slim.h"
#include "stock.h"
#include "chord_held.h"
#include "euclid_math.h"
#include "melody_math.h"

#define SESSION       0x2003D71Cu   /* stock.h session: [+ 0x14] = the session record */
#define REC_PTR       0x14u
#define ENGINE        0x20038EC0u   /* the sequencer engine: [+ 0x30 + 4 t] = track t's pattern store, param 0 = pattern */
#define ENG_PATTERN   0x30u
#define REC_SYNTH     0x2E4u        /* record + 0x2E4: Synth 1 / 2's 8 patterns each */
#define REC_MIDI      0x1A27Cu      /* record + 0x1A27C: MIDI 1 / 2's */
#define PATTERN_SIZE  0xCA8u
#define RECORDERS     0x2003C174u   /* stock.h recorders: [+ 4 t] = track t's recorder (rec_touch tells stock a pattern changed) */
#define KEYBOARD      0x20041044u   /* stock.h keyboard: the Note views' keyboard, one for all four tracks */
#define KBD_SCALE     0x0Cu         /* keyboard + 0x0C: scale object; its mask at + 4 */
#define KBD_KEY       0x10u         /* keyboard + 0x10: -> the project root byte (0-11) */
#define SETTINGS      0x380u        /* pattern + 0x380: [0] last step, [1] first step */
#define STEPS         32u
#define STEP_SIZE     28u
#define STEPS_SIZE    (STEPS * STEP_SIZE)   /* 0x380: what a Write replaces and Undo keeps */
#define UNITS         6u
#define PROB_DEFAULT  7u            /* stock's probability byte of an empty step */
#define UNIT_EMPTY_VEL 0x60u        /* an unused unit: 00 00 00 60 */
#define TIE_BIT       0x80u         /* a unit's length byte, bit 7: stock holds the note into the next unit of its pitch
                                     * when the length reaches that unit's step (stock's tie, Micro Step view's Tie pad) */
#define COL_ARMED     0x47u         /* orange, animated (blink): the Write waits for its second press */

#define PAD_EARLIER   16u
#define PAD_LATER     17u
#define PAD_ROT0      18u
#define PAD_SOURCE    19u            /* Euclid / groove (PL13) */
#define PAD_GATE      20u
#define PAD_VEL       21u           /* 21-23 soft, medium, hard */
#define PAD_CYCLE     24u           /* 24-27: cycle 1-4 (3, 5, 6, 7 steps), PL14 */
#define PAD_UNDO      30u
#define PAD_WRITE     31u

#define COL_NEXT_HIT  COL_WHITE
#define CFG0_DEFAULT  (VEL_MEDIUM << 5)
#define CFG1_DEFAULT  (GATE_DEFAULT << 5)
#define LAST_MAX      139u          /* a note plays when pitch + key is within 12-139 (CHORD_KEY): no pad pitch is above */

uint8_t euclid_cfg[TRACKS][2];      /* saved: [0] hits | velocity << 5, [1] rotation | gate << 5 */
uint8_t euclid_last[TRACKS];        /* the track's last played pad (keyboard pitch); 72 before any; saved (PL14) */
static uint8_t armed;               /* track + 1 whose Write waits for its second press, 0 = none */
/* The pending action: a write runs on the release of the pad that asked for it, never during the press (a long write
 * with the finger down made the pad scan read the pressure into the next pad's slot: a phantom press, device 2026-10-20). */
#define ACT_NONE      0u
#define ACT_WRITE     1u
#define ACT_UNDO      2u
#define ACT_REWRITE   3u
#define ACT_UNSTAMPED 0x3Fu
#define ACT_PAD       5u            /* the pad's field: bits 5-10 (the track's: bits 2-4, tracks 0-7) */
static uint16_t act;                /* kind (bits 0-1) | track << 2 | pad << 5; the pad is ACT_UNSTAMPED until page_on_pad stamps it */
const uint8_t euclid_velocity[3] = {48u, 96u, 127u};   /* soft, medium (stock's fixed velocity), hard */
/* The roll's LED, 1 / 2 / 3 hits a step (PL17): stock's Gate view colours for 1/6, 3/6, 6/6 (steady codes). */
static const uint8_t ROLL_COL[ROLL_MAX + 1u] = {COL_GATE_1_6, COL_GATE_1_6 - 2u, COL_GATE_1_6 - 5u};
uint8_t euclid_undo_steps[STEPS_SIZE] SLIM_ITCM(euclid_undo_steps);   /* the steps the last Write replaced */
uint8_t euclid_undo_at SLIM_ITCM(euclid_undo_at);      /* 1 + (track << 3 | pattern) they came from, 0 = none */

void euclid_init(void)
{
    for (uint32_t t = 0; t < TRACKS; t++) {
        euclid_cfg[t][0] = CFG0_DEFAULT;
        euclid_cfg[t][1] = CFG1_DEFAULT;
        euclid_last[t] = EUCLID_NOTE_DEFAULT;
    }
}

/* Track t's pattern p (the record checked by the caller). */
static uint8_t *pattern(uint8_t *rec, uint32_t t, uint32_t p)
{
    return rec + (t < 2u ? REC_SYNTH + (8u * t + p) * PATTERN_SIZE : REC_MIDI + (8u * (t - 2u) + p) * PATTERN_SIZE);
}

static uint32_t current(uint32_t t)
{
    return *param_get(*(void **)(ENGINE + ENG_PATTERN + 4u * t), 0u) & 7u;
}

/* Pattern p of track t with its range (the record checked by the caller). */
static uint8_t *range_of(uint8_t *rec, uint32_t t, uint32_t p, uint32_t *n, uint32_t *first)
{
    uint8_t *pat = pattern(rec, t, p);
    uint32_t last = pat[SETTINGS] % STEPS, lo = pat[SETTINGS + 1u] % STEPS;
    if (lo > last) {
        uint32_t x = lo;
        lo = last;
        last = x;
    }
    *first = lo;
    *n = last - lo + 1u;
    return pat;
}

/* The target with its pattern number, read once (a Write takes both inside its masked section). */
static uint8_t *target(uint32_t t, uint32_t *n, uint32_t *first, uint32_t *p)
{
    uint8_t *rec = *(uint8_t *volatile *)(SESSION + REC_PTR);
    if (!rec || t >= TRACKS)
        return 0;
    *p = current(t);
    return range_of(rec, t, *p, n, first);
}

/* The draft's pattern, the one the Undo copy came from: a note track's (euclid_undo_at) or a drum's (drum_undo_at). */
static uint32_t undo_pattern(uint32_t t)
{
    return t >= TRACKS ? drum_undo_at[t - DRUM_FIRST] - 1u : (euclid_undo_at - 1u) & 7u;
}

/* The pattern the page works on: the track's current one, or while a draft is live the draft's (its length, its steps).
 * A drum (PL17): its shown pattern or its draft's (drum_tools.c); with none, n = 0 (no steps to preview or write). */
uint8_t *euclid_target(uint32_t t, uint32_t *n, uint32_t *first)
{
    uint32_t p;
    if (t >= TRACKS) {
        uint8_t *pat = drum_target(t - DRUM_FIRST, n, first);
        if (!pat)
            *n = *first = 0;
        return pat;
    }
    uint8_t *rec = *(uint8_t *volatile *)(SESSION + REC_PTR);
    if (rec && melody_in_draft(t))
        return range_of(rec, t, undo_pattern(t), n, first);
    return target(t, n, first, &p);
}

/* Drops the armed Write and any pending action (every way the pages or the pick context change). */
void euclid_disarm(void)
{
    armed = 0;
    act = ACT_NONE;
}

/* Any press but the Write's second, before it is known to change anything: the armed Write and a pending Write / Undo
 * go; a draft's pending re-write stays, so a press that changes nothing (an unused pad, ▲ ▼, dice notes with order
 * "same") cannot leave the pattern behind its settings. A press that changes something asks for its own. */
void euclid_unarm(void)
{
    armed = 0;
    if ((act & 3u) != ACT_REWRITE)
        act = ACT_NONE;
}

/* The press that is being handled asks for `kind` on its release (the latest press wins). */
static void act_set(uint32_t kind, uint32_t t)
{
    act = (uint16_t)(kind | t << 2 | ACT_UNSTAMPED << ACT_PAD);
}

/* page_on_pad, after a pick: the action that pick asked for (if any) belongs to this pad's release. */
void euclid_stamp(uint32_t pad)
{
    if (act >> ACT_PAD == ACT_UNSTAMPED)
        act = (uint16_t)((act & 0x1Fu) | pad << ACT_PAD);
}

/* A draft's pick: the setting is changed; the re-write waits for the pad's release. */
void melody_after_pick(uint32_t t)
{
    if (melody_in_draft(t))
        act_set(ACT_REWRITE, t);
}

/* The Note view keeps its own copy of which steps hold notes: refresh it as the recorder does after a commit. */
static void tell_stock(uint32_t t)
{
    void *rec = *(void *volatile *)(RECORDERS + 4u * t);
    if (rec)
        rec_touch(rec);
}

static void swap_undo(uint8_t *steps)
{
    for (uint32_t i = 0; i < STEPS_SIZE; i++) {
        uint8_t x = steps[i];
        steps[i] = euclid_undo_steps[i];
        euclid_undo_steps[i] = x;
    }
}

/* The project's scale mask (2 bits per semitone, 0 = Chromatic) and root 0-11, as the Note views use them. */
static uint32_t scale_mask(void)
{
    return *(volatile uint32_t *)(*(uint8_t **)(KEYBOARD + KBD_SCALE) + 4u);
}

static uint32_t project_key(void)
{
    return **(volatile uint8_t **)(KEYBOARD + KBD_KEY);
}

uint32_t euclid_cycle(uint32_t t, uint32_t n)
{
    uint32_t c = melody_cycle_len(R2_CYCLE(tools_rhythm(t)[2]));
    return c && c < n ? c : n;
}

uint32_t euclid_second(uint32_t t, uint32_t n)
{
    const uint8_t *r = tools_rhythm(t);
    return n ? euclid_mask(R2_HITS(r[0]), n, R2_ROT(r[1]) % n) : 0u;
}

/* The final rhythm (spec 2026-10-21-melody-variations-design.md, "Rhythm"): the first rhythm (Euclid or groove) over
 * the cycle, rotated within it and repeated over the pattern; combined with the second; thinned (never the first hit). */
uint32_t euclid_hits(uint32_t t, uint32_t n)
{
    const uint8_t *c = tools_euclid(t), *r = tools_rhythm(t);
    uint32_t k = HITS(c[0]), cy = euclid_cycle(t, n), rot = cy ? ROT(c[1]) % cy : 0u, mode = R2_COMBINE(r[0]);
    uint32_t seed = *tools_seed(t);
    uint32_t hits = c[0] & EUCLID_GROOVE ? melody_groove(k, cy, rot, seed) : euclid_mask(k, cy, rot);
    hits = melody_repeat(hits, cy, n);
    if (mode)
        hits = melody_combine(hits, euclid_second(t, n), mode);
    return melody_thin(hits, R2_THIN(r[1]), seed);
}

/* A Write has something to write: the final rhythm over the page's pattern has a hit. */
static int has_hits(uint32_t t)
{
    uint32_t n = 16u, first;
    euclid_target(t, &n, &first);
    return euclid_hits(t, n) != 0;
}

/* Inlined into the Write as well: a frame of its own there would deepen the pad press's worst stack path. */
static inline __attribute__((always_inline)) void pool_of(uint32_t t, melody_pool_t *pool)
{
    uint32_t mask = scale_mask();
    pool->cfg0 = melody_cfg[t][0];
    pool->seed = melody_seed[t][1];
    pool->n = 1;                                    /* melody_pool does not read it; the caller sets it for the line */
    melody_pool(pool, melody_root(melody_cfg[t][1], euclid_last[t], mask), mask,
                chord_track_settings(t) | project_key() << 16);
}

void euclid_pool(uint32_t t, melody_pool_t *pool)
{
    pool_of(t, pool);
}

/* Pattern `want` of track t (EUCLID_CURRENT: the one it plays) with its number and range; 0 without a record. */
static uint8_t *pattern_for(uint32_t t, uint32_t want, uint32_t *n, uint32_t *first, uint32_t *p)
{
    if (want == EUCLID_CURRENT)
        return target(t, n, first, p);
    uint8_t *rec = *(uint8_t *volatile *)(SESSION + REC_PTR);
    *p = want;
    return rec && t < TRACKS && want < 8u ? range_of(rec, t, want, n, first) : 0;
}

/* The line as written (spec "The line"): out[h] = the note of hit h, over every hit of `hits` in order; returns the tied
 * hits (never the first). The line walks the struck hits only; a struck hit may jump an octave; a tied hit repeats the
 * struck note before it. Order "same": only the ties (out untouched). Reads pool->cfg0, seed (the notes seed), n and,
 * for a line, the pool (pn > 0). */
uint32_t euclid_line(uint32_t t, const melody_pool_t *pool, uint32_t hits, uint8_t *out)
{
    uint32_t v = melody_vary[t], ties = melody_ties(hits, VARY_TIES(v), pool->seed);
    if (MEL_ORDER(pool->cfg0) == MEL_SAME)
        return ties;
    uint32_t struck = hits & ~ties, jumps = melody_jumps(struck, VARY_JUMPS(v), pool->seed), key = project_key();
    uint32_t h = 0, j = 0;
    melody_line(pool, struck, out);                 /* out[j]: the struck notes */
    for (uint32_t i = 0; i < pool->n; i++)          /* the jumps, in place; h = the hits, j = the struck ones */
        if (hits >> i & 1u) {
            h++;
            if (!(ties >> i & 1u)) {
                if (jumps >> i & 1u)
                    out[j] = (uint8_t)melody_jump(out[j], key);
                j++;
            }
        }
    for (uint32_t i = pool->n; i-- > 0;)            /* spread over every hit from the top: a read is never above its write */
        if (hits >> i & 1u) {
            h--;
            if (ties >> i & 1u)
                out[h] = out[j - 1u];               /* the struck note before (the first hit is never tied: j >= 1) */
            else
                out[h] = out[--j];
        }
    return ties;
}

/* What a Write writes over n steps, worked out before interrupts are masked. */
typedef struct {
    uint32_t hits;      /* the final hits */
    uint32_t into;      /* hits whose unit ties into the next hit: tie bit, length up to it (stock holds the note on) */
    uint32_t hard;      /* hits written at 127: struck, under the Melody accent (j = the struck index) or combine accent */
} plan_t;

/* The final hits, the line's note per hit in line[] (order "same": the caller's chord), the ties and the accents. A tie
 * more than 96 sixths (16 steps) away cannot be reached by stock's longest note: that unit keeps its own length and
 * the tied hit is struck again. */
static void plan(uint32_t t, uint32_t n, melody_pool_t *pool, uint8_t *line, plan_t *w)
{
    uint32_t hits = euclid_hits(t, n), acc = MEL_ACCENT(pool->cfg0), prev = 0, j = 0;
    uint32_t second = R2_COMBINE(rhythm_cfg[t][0]) == COMBINE_ACCENT ? euclid_second(t, n) : 0u;
    pool->n = (uint8_t)n;
    uint32_t ties = euclid_line(t, pool, hits, line);
    w->hits = hits;
    w->into = w->hard = 0;
    for (uint32_t i = 0; i < n; i++) {
        if (!(hits >> i & 1u))
            continue;
        if (ties >> i & 1u) {
            if (6u * (i - prev) <= MELODY_NEXT_MAX)
                w->into |= 1u << prev;
        } else if (melody_accent(acc, j++, i) || (second >> i & 1u))
            w->hard |= 1u << i;
        prev = i;
    }
}

/* Rewrites pattern p of track t (EUCLID_CURRENT = the one it plays) from the settings: the final rhythm, the notes of
 * PL11's Write (the root and its chord) or the melodic line, one unit per hit, a tied hit held from the hit before by
 * stock's tie bit. keep_undo 0 copies the old steps and names the pattern in euclid_undo_at, 1 leaves the copy as it
 * is. No final hits (k = 0 with no combine to add any, or none left after combine / thinning): nothing written. */
uint32_t euclid_write_to(uint32_t t, uint32_t want, uint32_t keep_undo)
{
    const uint8_t *c = euclid_cfg[t], *m = melody_cfg[t];
    uint32_t n, first, p;
    uint8_t notes[1u + CHORD_MAX_OTHER], line[STEPS];
    uint32_t same = MEL_ORDER(m[0]) == MEL_SAME, gate = GATE(c[1]), vel = euclid_velocity[VEL(c[0])], count = 1u;
    melody_pool_t pool;
    plan_t w;
    pool.cfg0 = m[0];
    pool.seed = melody_seed[t][1];                    /* the ties' seed in order "same" (pool_of sets it for a line) */
    if (same) {
        uint32_t mask = scale_mask(), s = chord_track_settings(t);
        notes[0] = (uint8_t)melody_root(m[1], euclid_last[t], mask);
        if (CHORD_HAS_SHAPE(s) || CHORD_BASS(s))
            count += chord_notes(notes[0], mask, s | project_key() << 16, notes + 1);
    } else {
        pool_of(t, &pool);
        if (!pool.pn)
            return 0;                                 /* an unplayable root: nothing to write, as k = 0 */
    }
    /* The rhythm and the line are worked out before interrupts are masked, for the target as read now. The sequencer
     * (Main task, time-sliced) may move a chain on at any moment, and the pattern written and the one Undo names must
     * be the same: inside, the target is read again, and the plan made again if it moved (rare). */
    uint8_t *pat = pattern_for(t, want, &n, &first, &p);
    if (!pat)
        return 0;
    plan(t, n, &pool, line, &w);
    if (!w.hits)
        return 0;
    uint32_t was_n = n, was_first = first, was_p = p;
    uint32_t primask = slim_irq_save();
    pat = pattern_for(t, want, &n, &first, &p);
    if (pat && (n != was_n || first != was_first || p != was_p))
        plan(t, n, &pool, line, &w);
    if (!pat || !w.hits) {
        slim_irq_restore(primask);
        return 0;
    }
    uint32_t hits = w.hits;
    if (!keep_undo) {
        for (uint32_t i = 0; i < STEPS_SIZE; i++)
            euclid_undo_steps[i] = pat[i];
        euclid_undo_at = (uint8_t)(1u + (t << 3 | p));
    }
    uint32_t j = 0;
    for (uint32_t st = 0; st < STEPS; st++) {
        uint8_t *step = pat + st * STEP_SIZE;
        uint32_t i = st - first, hit = st >= first && i < n && (hits >> i & 1u);
        uint32_t units = hit ? (same ? count : 1u) : 0u;
        uint32_t len = !hit ? 0u : w.into >> i & 1u ? melody_next_len(hits, n, i) | TIE_BIT
                       : gate == GATE_NEXT ? melody_next_len(hits, n, i) : gate + 1u;
        uint32_t v = hit && (w.hard >> i & 1u) ? 127u : vel;
        step[0] = 0;
        step[1] = PROB_DEFAULT;
        step[2] = step[3] = 0;
        for (uint32_t u = 0; u < UNITS; u++) {
            uint8_t *unit = step + 4u + 4u * u;
            uint32_t on = u < units;
            unit[0] = on ? same ? notes[u] : line[j] : 0u;
            unit[1] = (uint8_t)(on ? len : 0u);
            unit[2] = 0;
            unit[3] = (uint8_t)(on ? v : UNIT_EMPTY_VEL);
        }
        if (hit) {
            step[0] = (uint8_t)((1u << units) - 1u);    /* last: the units are in place before the step plays */
            j++;
        }
    }
    slim_irq_restore(primask);
    tell_stock(t);
    return 1;
}

/* Undo on track t's page: only its own track's copy, back into the pattern it came from. */
static void undo(uint32_t t)
{
    uint8_t *rec = *(uint8_t *volatile *)(SESSION + REC_PTR);
    uint32_t at = euclid_undo_at;
    if (!rec || !at || (at - 1u) >> 3 != t)
        return;
    uint32_t primask = slim_irq_save();
    swap_undo(pattern(rec, t, (at - 1u) & 7u));
    slim_irq_restore(primask);
    tell_stock(t);
}

static int has_undo(uint32_t t)
{
    return euclid_undo_at && (euclid_undo_at - 1u) >> 3 == t;
}

/* A drum (PL17): the same pads, the roll on the gate's pad 20; dice notes (pad 29) rolls nothing (melody_dice). */
void euclid_pick(uint32_t t, uint32_t pad)
{
    uint8_t *c = tools_euclid(t);
    if (pad == PAD_WRITE) {
        if (melody_in_draft(t))                     /* in a draft: no arming, a re-write on the release */
            melody_after_pick(t);
        else if (armed == t + 1u) {
            armed = 0;
            act_set(ACT_WRITE, t);                  /* the write runs on the release */
        } else if (has_hits(t))
            armed = (uint8_t)(t + 1u);
        return;
    }
    euclid_unarm();
    if (pad == PAD_UNDO) {
        act_set(ACT_UNDO, t);                       /* on the release; the swap is the pre-draft pattern, Undo again is PL11's redo */
        return;
    }
    if (pad == PAD_DICE_R || pad == PAD_DICE_N) {
        if (!melody_dice(t, pad - PAD_DICE_R))      /* order "same", or a drum: notes dice rolls nothing */
            return;
    } else if (pad < 16u)
        c[0] = (uint8_t)((c[0] & ~0x1Fu) | (pad + 1u));
    else if (pad == PAD_EARLIER || pad == PAD_LATER) {   /* within the cycle (n without one), from the rotation mod c */
        uint32_t n = 16u, first;
        euclid_target(t, &n, &first);
        if (!n)
            return;                                 /* a drum with no target: no steps to rotate over */
        uint32_t cy = euclid_cycle(t, n), r = ROT(c[1]) % cy;
        c[1] = (uint8_t)((c[1] & ~0x1Fu) | (pad == PAD_EARLIER ? r + 1u : r + cy - 1u) % cy);
    } else if (pad == PAD_ROT0)
        c[1] = (uint8_t)(c[1] & ~0x1Fu);
    else if (pad == PAD_SOURCE)
        c[0] ^= EUCLID_GROOVE;
    else if (pad == PAD_GATE && t >= TRACKS) {      /* a drum's roll: 1 -> 2 -> 3 hits a step -> 1 */
        uint32_t r = ROLL(c[1]);
        c[1] = (uint8_t)(ROT(c[1]) | (r < ROLL_MAX ? r + 1u : 0u) << 5);
    } else if (pad == PAD_GATE) {                   /* as stock's Gate view: one sixth down, 1/6 -> to the next hit -> 6/6 */
        uint32_t g = GATE(c[1]);
        c[1] = (uint8_t)(ROT(c[1]) | (g == GATE_NEXT ? GATE_LEGATO : g ? g - 1u : GATE_NEXT) << 5);
    } else if (pad >= PAD_VEL && pad < PAD_VEL + 3u)
        c[0] = (uint8_t)((c[0] & ~VEL_BITS) | (pad - PAD_VEL) << 5);
    else if (pad >= PAD_CYCLE && pad < PAD_CYCLE + 4u) {
        uint8_t *r2 = &tools_rhythm(t)[2];
        uint32_t v = pad - PAD_CYCLE + 1u;
        *r2 = (uint8_t)((*r2 & ~7u) | (R2_CYCLE(*r2) == v ? 0u : v));
    } else
        return;
    melody_after_pick(t);
}

/* ctrl_pad_release (page_on_release), when no page pad is left down: the pending action (the latest press's) runs. */
void euclid_release(uint32_t t)
{
    uint32_t kind = act & 3u;
    if (kind == ACT_NONE || (act >> 2 & 7u) != t)
        return;
    act = ACT_NONE;
    uint32_t drum = t >= TRACKS, d = t - DRUM_FIRST;  /* a drum (PL17): drum_tools.c's writer and Undo */
    if (kind == ACT_WRITE) {
        if ((drum ? drum_write_to(d, EUCLID_CURRENT, 0) : euclid_write_to(t, EUCLID_CURRENT, 0)) && melody_new_in_use(t))
            melody_draft_start(t);
    } else if (kind == ACT_UNDO) {
        if (drum)
            drum_undo(d);
        else
            undo(t);
        melody_draft_end();
    } else if (melody_in_draft(t)) {                /* the draft's re-write, if it is still live */
        if (drum)
            drum_write_to(d, undo_pattern(t), 1u);
        else
            euclid_write_to(t, undo_pattern(t), 1u);
    }
}

void euclid_draw(uint32_t t, uint16_t *out)
{
    const uint8_t *c = tools_euclid(t);
    uint32_t n = 16u, first;
    euclid_target(t, &n, &first);
    uint32_t mask = euclid_hits(t, n);
    for (uint32_t s = 0; s < 16u; s++)
        out[s] = (uint16_t)(s >= n ? COL_OFF : mask >> s & 1u ? COL_ORANGE : COL_ORANGE_DIM);
    for (uint32_t s = 16u; s < PADS; s++)
        out[s] = COL_OFF;
    out[PAD_EARLIER] = out[PAD_LATER] = out[PAD_ROT0] = COL_WHITE_DIM;
    out[PAD_SOURCE] = (uint16_t)(c[0] & EUCLID_GROOVE ? COL_WHITE : COL_WHITE_DIM);
    out[PAD_GATE] = (uint16_t)(t >= TRACKS ? ROLL_COL[ROLL(c[1])] : GATE(c[1]) == GATE_NEXT ? COL_NEXT_HIT
                               : COL_GATE_1_6 - GATE(c[1]));
    for (uint32_t v = 0; v < 3u; v++)
        out[PAD_VEL + v] = (uint16_t)(v == VEL(c[0]) ? COL_MAGENTA : COL_MAGENTA_DIM);
    for (uint32_t v = 0; v < 4u; v++)
        out[PAD_CYCLE + v] = (uint16_t)(v + 1u == R2_CYCLE(tools_rhythm(t)[2]) ? COL_CYAN : COL_CYAN_DIM);
    melody_draw_actions(t, out);
}

/* Pads 30 / 31 on every page of Pattern tools and Melody: Undo (blue when it holds this track's copy), Write (dark with no
 * final hits, dim ready, blinking armed, bright in a draft). */
void euclid_draw_actions(uint32_t t, uint16_t *out)
{
    out[PAD_UNDO] = (uint16_t)((t >= TRACKS ? drum_has_undo(t - DRUM_FIRST) : has_undo(t)) ? COL_BLUE : COL_OFF);
    out[PAD_WRITE] = (uint16_t)(!has_hits(t) ? COL_OFF : melody_in_draft(t) ? COL_ORANGE
                                : armed == t + 1u ? COL_ARMED : COL_ORANGE_DIM);
}

/* CTCtrl link (features/chord/chord_link.c), on the 8 bytes of euclid_cfg in a candidate payload and before it:
 * a byte the write changed holds a value the pads make, or the default. */
int euclid_link_valid(const uint8_t *cfg, const uint8_t *old)
{
    for (uint32_t t = 0; t < TRACKS; t++) {
        uint32_t c0 = cfg[2u * t], c1 = cfg[2u * t + 1u];
        if (c0 != old[2u * t] && (HITS(c0) > 16u || VEL(c0) == 3u))
            return 0;
        if (c1 != old[2u * t + 1u] && GATE(c1) > GATE_NEXT)
            return 0;
    }
    return 1;
}

/* After a link write (UI task), `old` = euclid_cfg before it: as a pick on the page, a change disarms Write; a rotation
 * written is kept below the target pattern's length, as the rotate pads keep it. */
void euclid_link_apply(const uint8_t *old)
{
    for (uint32_t t = 0; t < TRACKS; t++) {
        uint8_t *c = euclid_cfg[t];
        if (c[0] == old[2u * t] && c[1] == old[2u * t + 1u])
            continue;
        euclid_disarm();
        melody_draft_end();
        if (ROT(c[1]) != ROT(old[2u * t + 1u])) {     /* the gate pad leaves a stale rotation alone */
            uint32_t n = 16u, first;
            euclid_target(t, &n, &first);
            if (n)
                c[1] = (uint8_t)((c[1] & ~0x1Fu) | ROT(c[1]) % n);
        }
    }
}

/* After a project load wrote euclid_cfg and euclid_last (features/saved, from chord_saved_fix): each field alone. */
void euclid_saved_fix(void)
{
    for (uint32_t t = 0; t < TRACKS; t++) {
        uint8_t *c = euclid_cfg[t];
        if (HITS(c[0]) > 16u)
            c[0] = (uint8_t)(c[0] & ~0x1Fu);
        if (VEL(c[0]) == 3u)
            c[0] = (uint8_t)((c[0] & ~VEL_BITS) | VEL_MEDIUM << 5);
        if (GATE(c[1]) > GATE_NEXT)
            c[1] = (uint8_t)(ROT(c[1]) | GATE_DEFAULT << 5);
        if (euclid_last[t] > LAST_MAX)              /* saved from PL14: no keyboard pitch plays above 139 */
            euclid_last[t] = EUCLID_NOTE_DEFAULT;
    }
    euclid_undo_at = 0;                             /* the copy belongs to the project that was replaced */
    euclid_disarm();
}
