/* Trig conditions' maths (PL20): pure functions, no stock calls. Model: tests/trig_model.py.
 *
 * The 9-bit code, one encoding for drums and note tracks: 0 = none. A cycle of length L (2-8) with ticked passes
 * `mask` (bit i = pass i + 1, never 0) is (1 << L) | mask; every pass ticked is a valid code and plays every pass. The
 * eight specials are TRIG_SPECIAL[] (4 ... 64 are the empty cycles of L = 2-6); 128 and 256 (the empty cycles of
 * L = 7, 8) and any other empty cycle read as none. */
#pragma once
#include <stdint.h>

#define TRIG_SPECIALS 8u
#define TRIG_FIRST     0u           /* the Shift layer's pads 25 ... 32, in this order */
#define TRIG_NOT_FIRST 1u
#define TRIG_FILL      2u
#define TRIG_NOT_FILL  3u
#define TRIG_PRE       4u
#define TRIG_NOT_PRE   5u
#define TRIG_LAST      6u
#define TRIG_NOT_LAST  7u
extern const uint16_t TRIG_SPECIAL[8];

#define TRIG_COUNT_MOD 840u         /* the least common multiple of 1 ... 8: a count reaching 2 x 840 goes back to 840
                                     * (every cycle stays exact; count 0, FIRST, only once per start-over) */

#define TRIG_TAP   0u               /* trig_edit's gestures */
#define TRIG_HOLD  1u
#define TRIG_SHIFT 2u

#define TRIG_NONE         0u        /* trig_kind */
#define TRIG_CYCLE        1u
#define TRIG_SPECIAL_KIND 2u

uint32_t trig_kind(uint32_t code);
uint32_t trig_len(uint32_t code);                       /* a cycle's length 2-8, else 0 */
uint32_t trig_mask(uint32_t code);                      /* a cycle's ticked passes, else 0 */
uint32_t trig_special(uint32_t code);                   /* 0-7, else TRIG_SPECIALS */
uint32_t trig_cycle(uint32_t len, uint32_t mask);       /* the code, 0 when len is not 2-8 or mask is 0 or too wide */

/* What a step's condition sees on one pass. `count` = the pattern's pass number - 1 (0 on the first pass), kept below
 * 2 x TRIG_COUNT_MOD. `fill`: a drum's FILL, always 0 on a note track. */
typedef struct { uint16_t count; uint8_t pre, fill, last; } trig_ctx_t;
uint32_t trig_plays(uint32_t code, const trig_ctx_t *c);    /* 1 = the condition lets the step play */
uint32_t trig_conditional(uint32_t code, uint32_t prob);    /* 1 = the step sets PRE's state (prob: its probability byte) */

/* Row 4's gestures. `pad` 0-7 of the row; `drum` 1 on a drum track (a note track has no FILL). Returns the new code. */
uint32_t trig_edit(uint32_t code, uint32_t pad, uint32_t gesture, uint32_t drum);
void trig_row4(uint32_t code, uint32_t shift, uint32_t drum, uint16_t *out);   /* the 8 pads' LED codes */

/* The code in the pattern bytes. Drum pattern: +0x88 + s = bits 0-7, bit 8 = bit (s & 7) of +0x84 + (s >> 3). Note
 * step (28 B): [2] = bits 0-7, [3] bit 0 = bit 8, [3] bits 1-7 written 0. */
uint32_t trig_drum_get(const uint8_t *pattern, uint32_t step);
void trig_drum_set(uint8_t *pattern, uint32_t step, uint32_t code);
uint32_t trig_note_get(const uint8_t *step);
void trig_note_set(uint8_t *step, uint32_t code);
