/* Melodic generator maths: pure functions, no stock calls (spec 2026-10-19-melodic-generator-design.md, "What gets
 * written"). Model: tests/melody_model.py. */
#pragma once
#include <stdint.h>

#define MELODY_POOL_MAX 24u
#define MELODY_NEXT_MAX 96u            /* "to the next hit": stock's longest note in sixths (stock clamps 1-96) */

/* Settings melody_cfg[t][0] (c0) and [1] (c1). */
#define MEL_SAME   0u                  /* order: the chord on every hit (the caller's own path) */
#define MEL_UP     1u
#define MEL_DOWN   2u
#define MEL_UPDN   3u
#define MEL_CLIMB  4u
#define MEL_WALK   5u
#define MEL_RANDOM 6u
#define MEL_BASS   7u
#define MEL_ORDER(c0)  ((c0) & 7u)
#define MEL_POOL(c0)   (((c0) >> 3) & 1u)                       /* 0 chord, 1 scale */
#define MEL_RANGE(c0)  ((((c0) >> 4) & 3u) > 2u ? 3u : (((c0) >> 4) & 3u) + 1u)   /* octaves 1-3 */
#define MEL_ACCENT(c0) (((c0) >> 6) & 3u)                       /* 0 off, 1 first hit, 2 on the beat, 3 every 3rd */
#define MEL_ROOT(c1)   ((c1) & 7u)                              /* 0 last pad, 1-7 scale degree */
#define MEL_OCTAVE(c1) ((int32_t)(((c1) >> 3) & 3u) - 2)        /* -2 ... +1 */

/* The note pool of a line; the tests write it raw (cfg0 at 0, pool at 5, fifth at 5 + MELODY_POOL_MAX). */
typedef struct {
    uint8_t cfg0;           /* melody_cfg[t][0] */
    uint8_t seed;           /* the notes seed 1-255 */
    uint8_t n;              /* steps in the pattern (1-32) */
    uint8_t pn;             /* notes in the pool (1-MELODY_POOL_MAX) */
    uint8_t root_at;        /* index of the lowest pool note with the root's pitch class */
    uint8_t pool[MELODY_POOL_MAX];   /* keyboard pitches, sorted, no duplicates */
    uint8_t fifth;          /* the bass's fifth (pitch class): the perfect fifth if in the scale, else the 5th degree */
} melody_pool_t;

/* 8-bit Galois LFSR, period 255 over 1-255. */
uint32_t melody_seed_next(uint32_t s);

/* A rhythm of k hits over n steps (bit i = a hit on step i): the k steps of the highest metric weight plus a jitter
 * from `seed`, then rotated: hit(i) = base((i + r) mod n). k >= n fills every step, k = 0 none; n 1-32. */
uint32_t melody_groove(uint32_t k, uint32_t n, uint32_t r, uint32_t seed);

/* The line's root pitch from melody_cfg[t][1] `cfg1`: the last pad `last` when the root field is 0, else scale degree
 * d 1-7 counted up from 72 + 12 * (octave field - 2) in the scale `mask` (0 = major), octaves included: in a 5-note
 * scale degree 6 is the root an octave up. */
uint32_t melody_root(uint32_t cfg1, uint32_t last, uint32_t mask);

/* Fills p->pool, pn, root_at and fifth from p->cfg0 around `root`. `settings` as chord_notes' with the project root in
 * bits 16-23; the chord pool uses the track's chord settings, a triad when the shape is off; the scale pool holds the
 * root even outside the scale. Order bass adds the fifth when no pool note has its pitch class. */
void melody_pool(melody_pool_t *p, uint32_t root, uint32_t mask, uint32_t settings);

/* Writes the note of every hit of `hits` (steps 0 .. p->n - 1) in order to out[j] and returns the hit count. Order
 * "same" writes nothing (the caller plays the chord). Reads p->cfg0, n, seed, pn, root_at, pool. */
uint32_t melody_line(const melody_pool_t *p, uint32_t hits, uint8_t *out);

/* 1 when hit j (on step i) is accented under the accent setting. */
uint32_t melody_accent(uint32_t accent, uint32_t j, uint32_t i);

/* "To the next hit": sixths of a step from step i to the next hit (wrapping to the first), at most MELODY_NEXT_MAX. */
uint32_t melody_next_len(uint32_t hits, uint32_t n, uint32_t i);

/* PL14 variations (spec 2026-10-21-melody-variations-design.md). Draws: item i = the step index 0-31, 0-255. */
uint32_t melody_draw(uint32_t seed, uint32_t salt, uint32_t i);
/* The draws' salts: thinning 1 (rhythm seed), ties 2 and jumps 3 (notes seed). */
#define MEL_SALT_THIN  1u
#define MEL_SALT_TIES  2u
#define MEL_SALT_JUMPS 3u
/* Amount a 0-3 (off, 1/4, 1/3, 1/2) -> the draw limit 0, 64, 85, 128. */
uint32_t melody_amount_limit(uint32_t a);
/* Cycle code 0-4 -> steps 0 (the whole pattern), 3, 5, 6, 7. */
uint32_t melody_cycle_len(uint32_t code);
/* Bit i (i < n) = base bit (i % c); c = 0 or c >= n leaves the base unchanged. */
uint32_t melody_repeat(uint32_t base, uint32_t c, uint32_t n);
/* The hits of two rhythms: mode 1 both, 2 either, 3 one-not-both, 4 first-without-second, else (accent) the first. */
uint32_t melody_combine(uint32_t a, uint32_t b, uint32_t mode);
/* `hits` without the thinned ones (never the lowest hit), salt 1. */
uint32_t melody_thin(uint32_t hits, uint32_t amount, uint32_t seed);
/* The tied hits among `hits` (never the lowest), salt 2. */
uint32_t melody_ties(uint32_t hits, uint32_t amount, uint32_t seed);
/* The struck hits among `struck` that jump an octave (never the lowest), salt 3. */
uint32_t melody_jumps(uint32_t struck, uint32_t amount, uint32_t seed);
/* An octave up when note + 12 + key <= 139, else down when note - 12 + key >= 12, else unchanged. */
uint32_t melody_jump(uint32_t note, uint32_t key);
