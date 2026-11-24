/* The Melody page (page 3 of a synth or MIDI track, PL13; spec 2026-10-19-melodic-generator-design.md, "UI"): the
 * settings of the melodic generator, per track, saved with the project (features/saved). UI task only; this file only
 * holds the settings and the dice, the maths is melody_math.c and the Write is euclid.c's.
 *
 * Pads 1-8 the note order (same, up, down, up-down, climb, walk, random, bass), 9-10 the pool (chord, scale), 11-13 the
 * range in octaves, 14 the accent (a cycle), 17 the root "last pad played", 18-24 the root as scale degree 1-7, 25-28
 * the octave of a degree root, 29 dice rhythm, 30 dice notes, 31 Undo, 32 Write (the last two as Pattern tools'). The
 * dice pads are also on Pattern tools. */
#include "slim.h"
#include "chord_held.h"
#include "melody_math.h"

#define PAD_ORDER     0u            /* 0-7 */
#define PAD_POOL      8u            /* 8-9 */
#define PAD_RANGE     10u           /* 10-12 */
#define PAD_ACCENT    13u
#define PAD_ROOT_LAST 16u           /* 16 last pad; 17-23: degree = pad - 16 */
#define PAD_OCTAVE    24u           /* 24-27: octave -2 ... +1 */
#define PAD_ACTIONS   30u           /* 30 Undo, 31 Write: Pattern tools' */

#define CFG1_DEFAULT  0x10u         /* root: last pad; octave 0 (field 2) */
#define DICE_TRIES    16u           /* a dice press steps its seed until the result changes, at most 16 times (Euclid: n) */
#define LINE_MAX      32u           /* a pattern's steps: at most one line note per step */

uint8_t melody_cfg[TRACKS][2];      /* see chord_held.h */
uint8_t melody_seed[TRACKS][2];
uint8_t melody_draft;               /* track + 1 while that track's draft is on, else 0 */

const uint8_t melody_accent_col[4] = {COL_YELLOW_DIM, COL_YELLOW, COL_WHITE, COL_MAGENTA};   /* off, first, beat, 3rd */

void melody_init(void)
{
    for (uint32_t t = 0; t < TRACKS; t++) {
        melody_cfg[t][0] = 0;
        melody_cfg[t][1] = CFG1_DEFAULT;
        melody_seed[t][0] = melody_seed[t][1] = 1;
    }
    melody_draft = 0;
}

/* Something beyond plain Euclid is on: the order, the groove, a root other than the last pad, an accent, or the gate
 * "to the next hit"; PL14: a combine, the thinning, a cycle, ties or octave jumps (the second rhythm alone does
 * nothing while the combine is off). A drum (PL17): the groove, a combine, the thinning, a cycle or its accent (the
 * roll is not one, as the gate is not). */
int melody_new_in_use(uint32_t t)
{
    const uint8_t *e = tools_euclid(t), *r = tools_rhythm(t);
    if ((e[0] & EUCLID_GROOVE) || R2_COMBINE(r[0]) || R2_THIN(r[1]) || R2_CYCLE(r[2]))
        return 1;
    if (t >= TRACKS)
        return drum_accent[t - DRUM_FIRST] != 0;
    const uint8_t *m = melody_cfg[t];
    return MEL_ORDER(m[0]) != MEL_SAME || MEL_ROOT(m[1]) || MEL_ACCENT(m[0]) || GATE(e[1]) == GATE_NEXT
        || melody_vary[t];
}

/* The draft (spec "Draft: hearing it while you shape it"): after a Write's second press with a new setting in use, every
 * pick re-writes the same pattern at once. It lives while melody_draft names the track and the Undo copy is the track's
 * (the copy's pattern is the draft's: the Write may have been on a chain's pattern that is not the current one). A drum
 * (PL17) has its own copy (drum_undo_at). */
void melody_draft_start(uint32_t t)
{
    melody_draft = (uint8_t)(t + 1u);
}

void melody_draft_end(void)
{
    melody_draft = 0;
}

int melody_in_draft(uint32_t t)
{
    if (melody_draft != t + 1u)
        return 0;
    if (t >= TRACKS)
        return drum_undo_at[t - DRUM_FIRST] != 0;
    return euclid_undo_at && (uint32_t)(euclid_undo_at - 1u) >> 3 == t;
}

/* 1 when the line as written (notes, ties, jumps: euclid_line) of `pool` over `hits` differs from the one in was[] with
 * the ties `was_ties` (into now[]); cnt = the hits. */
static int written_differs(uint32_t t, const melody_pool_t *pool, uint32_t hits, const uint8_t *was, uint32_t was_ties,
                           uint8_t *now, uint32_t cnt)
{
    if (euclid_line(t, pool, hits, now) != was_ties)
        return 1;
    if (MEL_ORDER(pool->cfg0) == MEL_SAME)
        return 0;
    for (uint32_t j = 0; j < cnt; j++)
        if (now[j] != was[j])
            return 1;
    return 0;
}

/* A dice press always changes something (final review): the seed steps until the rhythm (Euclid: rotation = seed % c,
 * c = the cycle's steps, n without one; at most n tries; groove: at most DICE_TRIES) or the written line (notes, ties,
 * jumps; at most DICE_TRIES) differs from the current one. When nothing can change (no hits, every hit, every
 * rotation alike, one note in the pool and no ties or jumps), the last step stays. Notes dice in order "same" rolls
 * only with ties on (it re-draws them). */
uint32_t melody_dice(uint32_t t, uint32_t which)
{
    if (which && t >= TRACKS)
        return 0;                                   /* a drum has no notes to roll (its pad 30 is dark) */
    uint32_t n = 16u, first;
    euclid_target(t, &n, &first);
    if (!n)
        return 0;                                   /* a drum with no target: no steps to roll over */
    uint32_t hits = euclid_hits(t, n), tries;
    if (which == 0u) {
        uint8_t *s0 = tools_seed(t), *c = tools_euclid(t);
        uint32_t groove = c[0] & EUCLID_GROOVE, cy = euclid_cycle(t, n);
        tries = groove ? DICE_TRIES : n;
        do {
            *s0 = (uint8_t)melody_seed_next(*s0);
            if (!groove)                                    /* Euclid: the new seed turns the rhythm, within the cycle */
                c[1] = (uint8_t)((c[1] & ~0x1Fu) | *s0 % cy);
        } while (--tries && euclid_hits(t, n) == hits);
        return 1;
    }
    uint8_t *seed = melody_seed[t];
    uint32_t same = MEL_ORDER(melody_cfg[t][0]) == MEL_SAME;
    if (same && !VARY_TIES(melody_vary[t]))
        return 0;                                   /* notes dice with order "same", no ties: nothing rolled, nothing to write */
    melody_pool_t pool;
    uint8_t was[LINE_MAX], now[LINE_MAX];
    pool.cfg0 = melody_cfg[t][0];
    if (!same)
        euclid_pool(t, &pool);
    pool.n = (uint8_t)n;
    pool.seed = seed[1];
    uint32_t can = same || pool.pn, cnt = 0, ties = can ? euclid_line(t, &pool, hits, was) : 0u;
    for (uint32_t i = 0; i < n; i++)
        cnt += hits >> i & 1u;
    tries = DICE_TRIES;
    do {
        seed[1] = (uint8_t)melody_seed_next(seed[1]);
        pool.seed = seed[1];
    } while (--tries && !(can && written_differs(t, &pool, hits, was, ties, now, cnt)));
    return 1;
}

void melody_pick(uint32_t t, uint32_t pad)
{
    uint8_t *m = melody_cfg[t];
    if (pad >= PAD_ACTIONS) {                       /* Undo, Write: Pattern tools' own (Write keeps its arming) */
        euclid_pick(t, pad);
        return;
    }
    euclid_unarm();
    if (pad == PAD_DICE_R || pad == PAD_DICE_N) {
        if (!melody_dice(t, pad - PAD_DICE_R))
            return;
    } else if (pad < PAD_POOL)
        m[0] = (uint8_t)((m[0] & ~7u) | pad);
    else if (pad < PAD_RANGE)
        m[0] = (uint8_t)((m[0] & ~8u) | (pad - PAD_POOL) << 3);
    else if (pad < PAD_ACCENT)
        m[0] = (uint8_t)((m[0] & ~(3u << 4)) | (pad - PAD_RANGE) << 4);
    else if (pad == PAD_ACCENT)
        m[0] = (uint8_t)((m[0] & ~(3u << 6)) | ((MEL_ACCENT(m[0]) + 1u) & 3u) << 6);
    else if (pad >= PAD_ROOT_LAST && pad < PAD_OCTAVE)
        m[1] = (uint8_t)((m[1] & ~7u) | (pad - PAD_ROOT_LAST));            /* 16: last pad; 17-23: degree 1-7 */
    else if (pad >= PAD_OCTAVE && pad < PAD_DICE_R) {
        if (!MEL_ROOT(m[1]))                                                /* ignored while the root is the last pad */
            return;
        m[1] = (uint8_t)((m[1] & ~(3u << 3)) | (pad - PAD_OCTAVE) << 3);
    } else
        return;                                     /* pads 15-16 (1-based) are unused */
    melody_after_pick(t);
}

/* Pads 29-32 on every page of Pattern tools and Melody: the dice (white, notes dark with order "same" and no ties:
 * nothing to roll; always dark for a drum) and Undo / Write. */
void melody_draw_actions(uint32_t t, uint16_t *out)
{
    out[PAD_DICE_R] = COL_WHITE_DIM;
    out[PAD_DICE_N] = (uint16_t)(t >= TRACKS || (MEL_ORDER(melody_cfg[t][0]) == MEL_SAME && !VARY_TIES(melody_vary[t]))
                                 ? COL_OFF : COL_WHITE_DIM);
    euclid_draw_actions(t, out);
}

void melody_page_draw(uint32_t t, uint16_t *out)
{
    const uint8_t *m = melody_cfg[t];
    for (uint32_t c = 0; c < PADS; c++)
        out[c] = COL_OFF;
    for (uint32_t c = 0; c < 8u; c++)
        out[PAD_ORDER + c] = (uint16_t)(c == MEL_ORDER(m[0]) ? COL_YELLOW : COL_YELLOW_DIM);
    for (uint32_t c = 0; c < 2u; c++)
        out[PAD_POOL + c] = (uint16_t)(c == MEL_POOL(m[0]) ? COL_GREEN : COL_GREEN_DIM);
    for (uint32_t c = 0; c < 3u; c++)
        out[PAD_RANGE + c] = (uint16_t)(c + 1u == MEL_RANGE(m[0]) ? COL_MAGENTA : COL_MAGENTA_DIM);
    out[PAD_ACCENT] = melody_accent_col[MEL_ACCENT(m[0])];
    uint32_t root = MEL_ROOT(m[1]);
    out[PAD_ROOT_LAST] = (uint16_t)(root == 0u ? COL_WHITE : COL_WHITE_DIM);
    for (uint32_t d = 1u; d < 8u; d++)
        out[PAD_ROOT_LAST + d] = (uint16_t)(d == root ? COL_BLUE : COL_BLUE_DIM);
    for (uint32_t o = 0; o < 4u; o++)               /* all dim while the root is the last pad */
        out[PAD_OCTAVE + o] = (uint16_t)(root && o == (uint32_t)(MEL_OCTAVE(m[1]) + 2) ? COL_MAGENTA : COL_MAGENTA_DIM);
    melody_draw_actions(t, out);
}

/* After a project load wrote melody_cfg and melody_seed (features/saved, from chord_saved_fix): each field alone. A
 * draft ends here too. */
void melody_saved_fix(void)
{
    melody_draft_end();
    euclid_disarm();                                /* and a pending write / Undo */
    for (uint32_t t = 0; t < TRACKS; t++) {
        uint8_t *m = melody_cfg[t];
        if (((m[0] >> 4) & 3u) == 3u)               /* range - 1 = 3 (MEL_RANGE clamps it) */
            m[0] = (uint8_t)(m[0] & ~(3u << 4));
        m[1] &= 0x1Fu;
        for (uint32_t k = 0; k < 2u; k++)
            if (!melody_seed[t][k])
                melody_seed[t][k] = 1;
    }
}

/* CTCtrl link, on the 8 bytes of melody_cfg in a candidate payload and before it: a byte the write changed holds a
 * value the pads make. */
int melody_link_valid(const uint8_t *cfg, const uint8_t *old)
{
    for (uint32_t t = 0; t < TRACKS; t++) {
        uint32_t c0 = cfg[2u * t], c1 = cfg[2u * t + 1u];
        if (c0 != old[2u * t] && ((c0 >> 4) & 3u) == 3u)
            return 0;
        if (c1 != old[2u * t + 1u] && (c1 & 0xE0u))
            return 0;
    }
    return 1;
}

/* After a link write (UI task), `old` = melody_cfg before it: as a pick on the page, a change disarms Write. */
void melody_link_apply(const uint8_t *old)
{
    for (uint32_t t = 0; t < TRACKS; t++)
        if (melody_cfg[t][0] != old[2u * t] || melody_cfg[t][1] != old[2u * t + 1u]) {
            euclid_disarm();
            melody_draft_end();
            return;
        }
}
