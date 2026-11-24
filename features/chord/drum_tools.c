/* Pattern tools for the drums (PL17, spec docs/specs/2026-10-25-drums-design.md): the four drums' Euclid, second
 * rhythm, accent and seed settings (saved with the project, the first three over the CTCtrl link), the shown pattern of a
 * drum, the load / link checks, and the drum Write and Undo. Drum d is track DRUM_FIRST + d. In ITCM: the heap tail is
 * nearly full. UI task.
 *
 * The Write (spec "What a Write writes"; docs/investigations/2026-10-25-drums-pattern.md §2, spike 1): a drum pattern's
 * steps are 4 arrays of 32 B (velocity, probability, sample flip, microstep mask). The drum editor keeps an editing
 * copy of the pattern it shows, its step store, and any stock commit of that store writes all 128 B back: so a write
 * to the mirrored pattern goes into the pattern and both store buffers with interrupts masked, then (unmasked) the
 * store is touched and committed, which writes the same bytes and relights the views. Another pattern is written raw.
 * PL20: in a marked project (trig_mark == 1) a Write also zeroes the pattern's 36 trig-condition bytes (a generated
 * pattern starts clean); Undo swaps them back with the steps. Unmarked, they are not conditions and stay (as PL19). */
#include "slim.h"
#include "stock.h"
#include "chord_held.h"
#include "slim_link.h"

#define SESSION       0x2003D71Cu   /* stock.h session: [+ 0x14] = the session record */
#define REC_PTR       0x14u
#define RECORDERS     0x2003C174u   /* [+ 4 (DRUM_FIRST + d)]: drum d's recorder */
#define DRUM_REC_VT   0x0805A578u   /* a drum recorder's vtable */
#define REC_POS       0x14u         /* recorder + 0x14: the position store, param 0 = the pattern the editor shows */
#define REC_BASE      0x48u         /* recorder + 0x48: the drum's pattern 0 */
#define REC_STORE     0x4Cu         /* recorder + 0x4C: the drum editor's step store (its editing copy) */
#define ST_BUF0       0x0Cu         /* step store + 0x0C, + 0x10: its two buffers, 32 parameter words each */
#define ST_BUF1       0x10u
#define ST_MIRROR     0x18u         /* step store + 0x18: + LANES of the pattern it mirrors */
#define DPATTERN_SIZE 0x6A8u
#define D_VEL         0x00u         /* pattern + 0x00 + s: step s's velocity (0 = no hit), + 0x20 probability, + 0x40 */
#define D_PROB        0x20u         /* sample flip, + 0x60 microstep mask; what a Write replaces and Undo keeps */
#define D_FLIP        0x40u
#define D_MICRO       0x60u
#define DLAST         0x80u         /* pattern + 0x80 last step, + 0x81 first step */
#define LANES         0xA8u
#define D_CODES       0x84u         /* pattern + 0x84 .. + 0xA7: the steps' trig conditions (PL20, trig_math.h) */
#define STEPS         32u
#define PROB_ALWAYS   7u            /* stock's probability byte of an empty step: always plays */
#define FLIP_NONE     0xFFu         /* no sample flip: the drum's own sample */
#define HIT_HARD      127u

uint8_t drum_euclid[DRUMS][2] SLIM_ITCM(drum_euclid);     /* see chord_held.h */
uint8_t drum_rhythm[DRUMS][3] SLIM_ITCM(drum_rhythm);
uint8_t drum_accent[DRUMS] SLIM_ITCM(drum_accent);
uint8_t drum_seed[DRUMS] SLIM_ITCM(drum_seed);
uint8_t drum_undo_steps[DRUMS][DSTEPS_SIZE] SLIM_ITCM(drum_undo_steps);   /* per drum the 128 B its last Write replaced */
uint8_t drum_undo_at[DRUMS] SLIM_ITCM(drum_undo_at);                /* 1 + the pattern they came from, 0 = none */
uint8_t drum_undo_cond[DRUMS][DCOND_SIZE] SLIM_ITCM(drum_undo_cond); /* PL20: their conditions (0 when unmarked then) */

/* The roll's microstep mask, 1 / 2 / 3 hits a step: microsteps 0 · 0, 3 · 0, 2, 4 (sixths of the step). */
static const uint8_t ROLL_MICRO[ROLL_MAX + 1u] = {0x01u, 0x09u, 0x15u};
/* The step store's parameter k = 4 steps of one array: k / 8 = velocity, probability, micro, flip. */
static const uint8_t PARAM_ARRAY[4] = {D_VEL, D_PROB, D_MICRO, D_FLIP};

void drum_tools_init(void)
{
    for (uint32_t d = 0; d < DRUMS; d++) {
        drum_euclid[d][0] = VEL_MEDIUM << 5;
        drum_euclid[d][1] = 0;
        memset(drum_rhythm[d], 0, sizeof drum_rhythm[d]);
        drum_accent[d] = 0;
        drum_seed[d] = 1;
        drum_undo_at[d] = 0;
    }
}

/* Drum d's recorder, when there is a record and it is a drum recorder with its position store and patterns; else 0. */
static uint8_t *drum_rec(uint32_t d)
{
    uint8_t *rec = *(uint8_t *volatile *)(SESSION + REC_PTR);
    uint8_t *dr = d < DRUMS ? *(uint8_t *volatile *)(RECORDERS + 4u * (DRUM_FIRST + d)) : 0;
    if (!rec || !dr || *(volatile uint32_t *)dr != DRUM_REC_VT || !*(void *volatile *)(dr + REC_POS)
        || !*(void *volatile *)(dr + REC_BASE))
        return 0;
    return dr;
}

/* Pattern `want` of drum d (EUCLID_CURRENT: the shown one, the editor's position store) with its number and its steps
 * first .. first + n - 1 (swapped when first > last, as the note tracks' range_of); 0 without a drum recorder. */
static uint8_t *pattern_for(uint32_t d, uint32_t want, uint32_t *n, uint32_t *first, uint32_t *p)
{
    uint8_t *dr = drum_rec(d);
    if (!dr)
        return 0;
    *p = want == EUCLID_CURRENT ? *param_get(*(void **)(dr + REC_POS), 0u) & 7u : want;
    if (*p >= 8u)
        return 0;
    uint8_t *pat = *(uint8_t **)(dr + REC_BASE) + DPATTERN_SIZE * *p;
    uint32_t last = pat[DLAST] % STEPS, lo = pat[DLAST + 1u] % STEPS;
    if (lo > last) {
        uint32_t x = lo;
        lo = last;
        last = x;
    }
    *first = lo;
    *n = last - lo + 1u;
    return pat;
}

/* The pattern drum d's pages work on: its shown pattern, or while a draft is live the draft's (drum_undo_at's), with
 * its steps first .. first + n - 1. 0 when there is none (no record, no drum recorder, or its vtable is not a drum
 * recorder's): n is then left as it was. */
uint8_t *drum_target(uint32_t d, uint32_t *n, uint32_t *first)
{
    uint32_t p;
    return pattern_for(d, d < DRUMS && melody_in_draft(DRUM_FIRST + d) ? drum_undo_at[d] - 1u : EUCLID_CURRENT, n, first,
                       &p);
}

/* The step store of the drum recorder rec (checked by the caller: drum_rec's) when it mirrors pat, else 0. */
static uint8_t *mirror_of(const uint8_t *rec, const uint8_t *pat)
{
    uint8_t *s = *(uint8_t *volatile *)(rec + REC_STORE);
    return s && *(const uint8_t *volatile *)(s + ST_MIRROR) == pat + LANES ? s : 0;
}

/* The store s mirrors pat: both its buffers take pat's 32 parameter words (interrupts masked by the caller). */
static void store_put(uint8_t *s, const uint8_t *pat)
{
    uint32_t *b0 = *(uint32_t **)(s + ST_BUF0), *b1 = *(uint32_t **)(s + ST_BUF1);
    for (uint32_t k = 0; k < 32u; k++)
        b0[k] = b1[k] = *(const uint32_t *)(pat + PARAM_ARRAY[k >> 3] + 4u * (k & 7u));
}

/* The hits written at 127 (as the note tracks' plan, with no ties): hit j on step i under the accent, or under combine
 * accent where the second rhythm hits. */
static uint32_t hard_of(uint32_t d, uint32_t n, uint32_t hits)
{
    uint32_t acc = drum_accent[d] & ACCENT_BITS, hard = 0, j = 0;
    uint32_t second = R2_COMBINE(drum_rhythm[d][0]) == COMBINE_ACCENT ? euclid_second(DRUM_FIRST + d, n) : 0u;
    for (uint32_t i = 0; i < n; i++)
        if ((hits >> i & 1u) && (melody_accent(acc, j++, i) || (second >> i & 1u)))
            hard |= 1u << i;
    return hard;
}

/* Steps 1-2 of the Write: rewrites pattern `want` of drum d (EUCLID_CURRENT = the shown one) from the settings, the
 * final hits on its steps first .. last, every other step empty; keep_undo 0 copies the old 128 B and names the
 * pattern in drum_undo_at[d]. *store = the step store to refresh (it mirrors the pattern), else 0. Returns 1 when it
 * wrote: no target or no final hits, nothing. */
static __attribute__((noinline)) uint32_t put(uint32_t d, uint32_t want, uint32_t keep_undo, uint8_t **store)
{
    const uint8_t *c = drum_euclid[d];
    uint32_t t = DRUM_FIRST + d, vel = euclid_velocity[VEL(c[0])], micro = ROLL_MICRO[ROLL(c[1]) <= ROLL_MAX ? ROLL(c[1]) : 0u], n, first, p;
    *store = 0;
    /* The hits are worked out before interrupts are masked, for the target as read now; inside, the target is read
     * again (the shown pattern may follow a chain moved on by the Main task) and the hits worked out again if it moved.
     * That re-plan runs masked, as euclid_write_to's does (device-proven since PL13): it is rare (Main moves the shown
     * pattern between the two reads) and takes tens of µs, on a pad's release (no pad-scan risk). If it ever matters: plan
     * unmasked and retry (followups.md, PL17 task reviews). */
    uint8_t *pat = pattern_for(d, want, &n, &first, &p);
    if (!pat)
        return 0;
    uint32_t hits = euclid_hits(t, n), hard = hard_of(d, n, hits), was_n = n, was_first = first, was_p = p;
    if (!hits)
        return 0;
    uint32_t primask = slim_irq_save();
    pat = pattern_for(d, want, &n, &first, &p);
    if (pat && (n != was_n || first != was_first || p != was_p)) {
        hits = euclid_hits(t, n);
        hard = hard_of(d, n, hits);
    }
    if (!pat || !hits) {
        slim_irq_restore(primask);
        return 0;
    }
    uint32_t marked = trig_mark == 1u;
    if (!keep_undo) {
        memcpy(drum_undo_steps[d], pat, DSTEPS_SIZE);
        for (uint32_t i = 0; i < DCOND_SIZE; i++)       /* unmarked: none kept, so an Undo after a mark adds none */
            drum_undo_cond[d][i] = marked ? pat[D_CODES + i] : 0u;
        drum_undo_at[d] = (uint8_t)(1u + p);
    }
    if (marked)
        for (uint32_t i = 0; i < DCOND_SIZE; i++)
            pat[D_CODES + i] = 0;
    for (uint32_t s = 0; s < STEPS; s++) {
        uint32_t i = s - first, hit = s >= first && i < n && (hits >> i & 1u);
        pat[D_VEL + s] = (uint8_t)(!hit ? 0u : hard >> i & 1u ? HIT_HARD : vel);
        pat[D_PROB + s] = PROB_ALWAYS;
        pat[D_FLIP + s] = FLIP_NONE;
        pat[D_MICRO + s] = (uint8_t)(hit ? micro : 0u);
    }
    uint8_t *s = mirror_of(drum_rec(d), pat);
    if (s)
        store_put(s, pat);
    slim_irq_restore(primask);
    *store = s;
    return 1;
}

/* Steps 1-2 of the Write (put); the step store to refresh, or 0 (not mirrored, or nothing written). A seam for the
 * emulation tests (a recorder commit between it and drum_refresh): nothing calls it, so its section is one the linker
 * script keeps (as melody_math.c's KEEP_UNTIL_USED). */
__attribute__((noinline, section(".text.slim_call_keep_drum_put")))
uint8_t *drum_put(uint32_t d, uint32_t want, uint32_t keep_undo)
{
    uint8_t *s;
    put(d, want, keep_undo, &s);
    return s;
}

/* Step 3, unmasked: every parameter of the store marked written (each read buffer copied through the write pointer
 * first, so a recorder commit since step 2 is kept), then committed: the editor writes the same bytes back into the
 * pattern and the views relight. Nothing for 0. */
__attribute__((noinline)) void drum_refresh(uint8_t *store)
{
    if (!store)
        return;
    store_touch_all(store);
    store_commit(store);
}

uint32_t drum_write_to(uint32_t d, uint32_t want, uint32_t keep_undo)
{
    uint8_t *s;
    uint32_t wrote = put(d, want, keep_undo, &s);
    drum_refresh(s);
    return wrote;
}

/* Undo on drum d's page: its copy swapped back into the pattern it came from, by the Write's path; again = redo. */
void drum_undo(uint32_t d)
{
    uint32_t at = d < DRUMS ? drum_undo_at[d] : 0u, n, first, p;
    uint8_t *s = 0;
    if (!at)
        return;
    uint32_t primask = slim_irq_save();
    uint8_t *pat = pattern_for(d, at - 1u, &n, &first, &p);
    if (pat) {
        for (uint32_t i = 0; i < DSTEPS_SIZE; i++) {
            uint8_t x = pat[i];
            pat[i] = drum_undo_steps[d][i];
            drum_undo_steps[d][i] = x;
        }
        if (trig_mark == 1u)                        /* PL20: the conditions with them (unmarked: not conditions) */
            for (uint32_t i = 0; i < DCOND_SIZE; i++) {
                uint8_t x = pat[D_CODES + i];
                pat[D_CODES + i] = drum_undo_cond[d][i];
                drum_undo_cond[d][i] = x;
            }
        s = mirror_of(drum_rec(d), pat);
        if (s)
            store_put(s, pat);
    }
    slim_irq_restore(primask);
    drum_refresh(s);
}

int drum_has_undo(uint32_t d)
{
    return d < DRUMS && drum_undo_at[d] != 0;
}

/* After a project load wrote the fields (from chord_saved_fix): each sub-field alone back to its default when no pad
 * makes it, spare bits cleared, the rest of the byte kept (as euclid_saved_fix and vary_saved_fix). The Undo copies
 * belong to the project that was replaced. */
void drum_tools_saved_fix(void)
{
    for (uint32_t d = 0; d < DRUMS; d++) {
        uint8_t *c = drum_euclid[d];
        if (HITS(c[0]) > 16u)
            c[0] &= (uint8_t)~0x1Fu;
        if (VEL(c[0]) == 3u)
            c[0] = (uint8_t)((c[0] & ~VEL_BITS) | VEL_MEDIUM << 5);
        if (ROLL(c[1]) > ROLL_MAX)
            c[1] &= (uint8_t)~ROLL_BITS;
        uint8_t *r = drum_rhythm[d];
        if (R2_HITS(r[0]) > 16u)
            r[0] &= (uint8_t)~R2_HITS_BITS;
        if (R2_COMBINE(r[0]) > COMBINE_ACCENT)
            r[0] &= (uint8_t)~R2_COMBINE_BITS;
        r[1] &= (uint8_t)~R2_SPARE1;
        if (R2_CYCLE(r[2]) > 4u)
            r[2] = 0;
        r[2] &= (uint8_t)~R2_SPARE2;
        drum_accent[d] &= ACCENT_BITS;
        if (!drum_seed[d])
            drum_seed[d] = 1;
        drum_undo_at[d] = 0;
    }
}

#if SLIM_LINK_N

/* CTCtrl link (chord_link.c), on whole payloads: a byte the write changed holds a value the pads make. drum_seed is not
 * linked. */
int drum_link_valid(const uint8_t *cand, const uint8_t *old)
{
    const uint8_t *e = cand + SLIM_OFF_drum_euclid, *e0 = old + SLIM_OFF_drum_euclid;
    const uint8_t *r = cand + SLIM_OFF_drum_rhythm, *r0 = old + SLIM_OFF_drum_rhythm;
    const uint8_t *a = cand + SLIM_OFF_drum_accent, *a0 = old + SLIM_OFF_drum_accent;
    for (uint32_t d = 0; d < DRUMS; d++) {
        uint32_t c0 = e[2u * d], c1 = e[2u * d + 1u];
        if (c0 != e0[2u * d] && (HITS(c0) > 16u || VEL(c0) == 3u))
            return 0;
        if (c1 != e0[2u * d + 1u] && ROLL(c1) > ROLL_MAX)
            return 0;
        uint32_t x = r[3u * d], y = r[3u * d + 1u], z = r[3u * d + 2u];
        if (x != r0[3u * d] && (R2_HITS(x) > 16u || R2_COMBINE(x) > COMBINE_ACCENT))
            return 0;
        if (y != r0[3u * d + 1u] && (y & R2_SPARE1))
            return 0;
        if (z != r0[3u * d + 2u] && (R2_CYCLE(z) > 4u || (z & R2_SPARE2)))
            return 0;
        if (a[d] != a0[d] && (a[d] & ~ACCENT_BITS))
            return 0;
    }
    return 1;
}

/* After a link write (UI task), `old` = the payload before it: as a pick on the page, a change disarms Write and ends
 * that drum's draft (another track's stays); a rotation written is kept below the shown pattern's length (16 steps
 * without one), as euclid_link_apply and vary_link_apply keep theirs. */
void drum_link_apply(const uint8_t *old)
{
    const uint8_t *e0 = old + SLIM_OFF_drum_euclid, *r0 = old + SLIM_OFF_drum_rhythm, *a0 = old + SLIM_OFF_drum_accent;
    for (uint32_t d = 0; d < DRUMS; d++) {
        uint8_t *c = drum_euclid[d], *r = drum_rhythm[d];
        if (c[0] == e0[2u * d] && c[1] == e0[2u * d + 1u] && r[0] == r0[3u * d] && r[1] == r0[3u * d + 1u]
            && r[2] == r0[3u * d + 2u] && drum_accent[d] == a0[d])
            continue;
        euclid_disarm();
        if (melody_draft == DRUM_FIRST + d + 1u)
            melody_draft_end();
        uint32_t rot = ROT(c[1]) != ROT(e0[2u * d + 1u]), rot2 = R2_ROT(r[1]) != R2_ROT(r0[3u * d + 1u]);
        if (rot || rot2) {
            uint32_t n = 16u, first;
            drum_target(d, &n, &first);
            if (rot)
                c[1] = (uint8_t)((c[1] & ~0x1Fu) | ROT(c[1]) % n);
            if (rot2)
                r[1] = (uint8_t)((r[1] & ~R2_ROT_BITS) | R2_ROT(r[1]) % n);
        }
    }
}

#endif
