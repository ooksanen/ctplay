/* The melody variations' settings (PL14, spec docs/specs/2026-10-21-melody-variations-design.md, "Settings and
 * saving"): per track the second rhythm, its combine, the thinning and the cycle (rhythm_cfg), the ties and octave
 * jumps (melody_vary), and which page of the two-page features the track used last (page_sub). All saved with the
 * project; rhythm_cfg and melody_vary over the CTCtrl link too. In ITCM: the heap tail is nearly full (PL13: 68 B).
 * UI task. */
#include "slim.h"
#include "stock.h"
#include "chord_held.h"
#include "slim_link.h"

uint8_t rhythm_cfg[TRACKS][3] SLIM_ITCM(rhythm_cfg);   /* see chord_held.h */
uint8_t melody_vary[TRACKS] SLIM_ITCM(melody_vary);
uint8_t page_sub[TRACKS] SLIM_ITCM(page_sub);

void vary_init(void)
{
    memset(rhythm_cfg, 0, sizeof rhythm_cfg);
    memset(melody_vary, 0, sizeof melody_vary);
    memset(page_sub, 0, sizeof page_sub);
}

/* After a project load wrote the fields (features/saved, from chord_saved_fix): each sub-field alone back to 0 when no
 * pad makes it, spare bits cleared, the rest of the byte kept. */
void vary_saved_fix(void)
{
    for (uint32_t t = 0; t < TRACKS; t++) {
        uint8_t *r = rhythm_cfg[t];
        if (R2_HITS(r[0]) > 16u)
            r[0] &= (uint8_t)~R2_HITS_BITS;
        if (R2_COMBINE(r[0]) > COMBINE_ACCENT)
            r[0] &= (uint8_t)~R2_COMBINE_BITS;
        r[1] &= (uint8_t)~R2_SPARE1;
        if (R2_CYCLE(r[2]) > 4u)
            r[2] = 0;
        r[2] &= (uint8_t)~R2_SPARE2;
        melody_vary[t] &= (uint8_t)~VARY_SPARE;
        page_sub[t] &= (uint8_t)(PAGE_SUB_TOOLS | PAGE_SUB_MELODY);
    }
}

/* Pattern tools 2 (pad 27 again; spec "UI"): pads 1-16 the second rhythm's hits (pad k = k hits) and its own preview
 * in white, 17-19 rotate it (earlier, later, back to the start), 20-24 combine (both, either, one not both, first
 * without second, accent), 25-27 thinning (1/4, 1/3, 1/2), 28 free (a drum's accent, PL17), 29-32 the actions.
 * Phrasing (pad 28 again): 1-3 ties, 5-7 octave jumps (1/4, 1/3, 1/2), 29-32 the actions; the rest free. One pad per
 * value, the lit pad turns its row off. A pick that changes a setting re-writes a draft on the pad's release, as every pick does. */
#define PAD_R2_EARLIER  16u
#define PAD_R2_LATER    17u
#define PAD_R2_ROT0     18u
#define PAD_COMBINE     19u         /* 19-23: combine 1-5 */
#define PAD_THIN        24u         /* 24-26: thinning 1-3 */
#define PAD_ACCENT      27u         /* a drum's accent (PL17); free on a note track's page */
#define PAD_TIES        0u          /* 0-2: ties 1-3 */
#define PAD_JUMPS       4u          /* 4-6: jumps 1-3 */

/* The row's value v (1-based) in field (mask, shift) of *b: set, or off when it is already v. */
static void row_pick(uint8_t *b, uint32_t mask, uint32_t shift, uint32_t v)
{
    *b = (uint8_t)((*b & ~mask) | ((*b & mask) >> shift == v ? 0u : v << shift));
}

/* Pads 1-28 of Pattern tools 2; a frame of its own, so the dice's deep path from tools2_pick carries none of it. A
 * drum's (PL17): its own settings, and pad 28 its accent (off -> first hit -> on the beat -> every 3rd -> off). */
static __attribute__((noinline)) void tools2_set(uint32_t t, uint32_t pad)
{
    euclid_unarm();
    if (pad == PAD_ACCENT && t >= TRACKS) {
        uint8_t *a = &drum_accent[t - DRUM_FIRST];
        *a = (uint8_t)((*a + 1u) & ACCENT_BITS);   /* always a change */
        melody_after_pick(t);
        return;
    }
    uint8_t *r = tools_rhythm(t);
    uint32_t was0 = r[0], was1 = r[1], n = 16u, first;
    euclid_target(t, &n, &first);
    if (!n && pad >= PAD_R2_EARLIER && pad <= PAD_R2_LATER)
        return;                                     /* a drum with no target: no steps to rotate over */
    uint32_t rot = n ? R2_ROT(r[1]) % n : 0u;       /* a rotation stored past a shortened pattern: from rot mod n */
    if (pad < 16u)
        r[0] = (uint8_t)((r[0] & ~R2_HITS_BITS) | (pad + 1u));
    else if (pad == PAD_R2_EARLIER)
        r[1] = (uint8_t)((r[1] & ~R2_ROT_BITS) | (rot + 1u) % n);
    else if (pad == PAD_R2_LATER)
        r[1] = (uint8_t)((r[1] & ~R2_ROT_BITS) | (rot + n - 1u) % n);
    else if (pad == PAD_R2_ROT0)
        r[1] &= (uint8_t)~R2_ROT_BITS;
    else if (pad < PAD_THIN)
        row_pick(&r[0], R2_COMBINE_BITS, 5u, pad - PAD_COMBINE + 1u);
    else if (pad < PAD_THIN + 3u)
        row_pick(&r[1], 3u << 5, 5u, pad - PAD_THIN + 1u);
    if (r[0] != was0 || r[1] != was1)
        melody_after_pick(t);
}

void tools2_pick(uint32_t t, uint32_t pad)
{
    if (pad >= PAD_DICE_R)
        euclid_pick(t, pad);                        /* the actions: Pattern tools' own (Write keeps its arming) */
    else
        tools2_set(t, pad);
}

void tools2_draw(uint32_t t, uint16_t *out)
{
    const uint8_t *r = tools_rhythm(t);
    uint32_t n = 16u, first;
    euclid_target(t, &n, &first);
    uint32_t mask = euclid_second(t, n);
    for (uint32_t s = 0; s < 16u; s++)
        out[s] = (uint16_t)(s >= n ? COL_OFF : mask >> s & 1u ? COL_WHITE : COL_WHITE_DIM);
    out[PAD_R2_EARLIER] = out[PAD_R2_LATER] = out[PAD_R2_ROT0] = COL_WHITE_DIM;
    for (uint32_t v = 0; v < 5u; v++)
        out[PAD_COMBINE + v] = (uint16_t)(v + 1u == R2_COMBINE(r[0]) ? COL_VIOLET : COL_VIOLET_DIM);
    for (uint32_t v = 0; v < 3u; v++)
        out[PAD_THIN + v] = (uint16_t)(v + 1u == R2_THIN(r[1]) ? COL_CYAN : COL_CYAN_DIM);
    out[PAD_ACCENT] = t >= TRACKS ? melody_accent_col[drum_accent[t - DRUM_FIRST]] : COL_OFF;
    melody_draw_actions(t, out);
}

void phrasing_pick(uint32_t t, uint32_t pad)
{
    if (pad >= PAD_DICE_R) {
        euclid_pick(t, pad);
        return;
    }
    euclid_unarm();
    uint8_t *v = &melody_vary[t], was = *v;
    if (pad < PAD_TIES + 3u)                        /* PAD_TIES = 0 */
        row_pick(v, 3u, 0u, pad - PAD_TIES + 1u);
    else if (pad >= PAD_JUMPS && pad < PAD_JUMPS + 3u)
        row_pick(v, 3u << 2, 2u, pad - PAD_JUMPS + 1u);
    if (*v != was)
        melody_after_pick(t);
}

void phrasing_draw(uint32_t t, uint16_t *out)
{
    uint32_t v = melody_vary[t];
    for (uint32_t c = 0; c < PADS; c++)
        out[c] = COL_OFF;
    for (uint32_t a = 0; a < 3u; a++) {
        out[PAD_TIES + a] = (uint16_t)(a + 1u == VARY_TIES(v) ? COL_CYAN : COL_CYAN_DIM);
        out[PAD_JUMPS + a] = (uint16_t)(a + 1u == VARY_JUMPS(v) ? COL_MAGENTA : COL_MAGENTA_DIM);
    }
    melody_draw_actions(t, out);
}

#if SLIM_LINK_N

/* CTCtrl link (chord_link.c), on whole payloads: a byte the write changed holds a value the pads make. page_sub is not
 * linked. */
int vary_link_valid(const uint8_t *cand, const uint8_t *old)
{
    const uint8_t *r = cand + SLIM_OFF_rhythm_cfg, *r0 = old + SLIM_OFF_rhythm_cfg;
    const uint8_t *v = cand + SLIM_OFF_melody_vary, *v0 = old + SLIM_OFF_melody_vary;
    for (uint32_t t = 0; t < TRACKS; t++) {
        uint32_t a = r[3u * t], b = r[3u * t + 1u], c = r[3u * t + 2u];
        if (a != r0[3u * t] && (R2_HITS(a) > 16u || R2_COMBINE(a) > COMBINE_ACCENT))
            return 0;
        if (b != r0[3u * t + 1u] && (b & R2_SPARE1))
            return 0;
        if (c != r0[3u * t + 2u] && (R2_CYCLE(c) > 4u || (c & R2_SPARE2)))
            return 0;
        if (v[t] != v0[t] && (v[t] & VARY_SPARE))
            return 0;
    }
    return 1;
}

/* After a link write (UI task), `old` = the payload before it: as a pick on the page, a change disarms Write and ends a
 * draft; a second rotation written is kept below the target pattern's length, as euclid_link_apply keeps the first. */
void vary_link_apply(const uint8_t *old)
{
    const uint8_t *r0 = old + SLIM_OFF_rhythm_cfg, *v0 = old + SLIM_OFF_melody_vary;
    for (uint32_t t = 0; t < TRACKS; t++) {
        uint8_t *r = rhythm_cfg[t];
        if (r[0] == r0[3u * t] && r[1] == r0[3u * t + 1u] && r[2] == r0[3u * t + 2u] && melody_vary[t] == v0[t])
            continue;
        euclid_disarm();
        melody_draft_end();
        if (R2_ROT(r[1]) != R2_ROT(r0[3u * t + 1u])) {   /* the thinning alone leaves a stale rotation alone */
            uint32_t n = 16u, first;
            euclid_target(t, &n, &first);
            if (n)
                r[1] = (uint8_t)((r[1] & ~R2_ROT_BITS) | R2_ROT(r[1]) % n);
        }
    }
}

#endif
