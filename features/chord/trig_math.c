/* Trig conditions' maths (trig_math.h). Tests: tests/trig_model.py is the reference, test_trig_model.py compares. */
#include "trig_math.h"
#include "chord_held.h"             /* COL_* */

/* The link drops what nothing calls (--gc-sections); until the playback and the row-4 code call these, only the
 * emulation tests do: this section name is KEPT by the linker script (as melody_math.c's KEEP_UNTIL_USED). */
#define KEEP_UNTIL_USED(name) __attribute__((section(".text.slim_call_keep_" #name)))

const uint16_t TRIG_SPECIAL[8] = {1u, 2u, 3u, 4u, 8u, 16u, 32u, 64u};

/* Per special: bright, dim. */
static const uint8_t SPECIAL_COL[8][2] = {
    {COL_GREEN, COL_GREEN_DIM}, {COL_GREEN, COL_GREEN_DIM}, {COL_ORANGE, COL_ORANGE_DIM}, {COL_ORANGE, COL_ORANGE_DIM},
    {COL_VIOLET, COL_VIOLET_DIM}, {COL_VIOLET, COL_VIOLET_DIM}, {COL_YELLOW, COL_YELLOW_DIM}, {COL_YELLOW, COL_YELLOW_DIM}};

KEEP_UNTIL_USED(trig_special) uint32_t trig_special(uint32_t code)
{
    for (uint32_t i = 0; i < TRIG_SPECIALS; i++)
        if (code == TRIG_SPECIAL[i])
            return i;
    return TRIG_SPECIALS;
}

/* A cycle's length (2-8), 0 when the code is none, a special or an empty cycle. */
KEEP_UNTIL_USED(trig_len) uint32_t trig_len(uint32_t code)
{
    if (code < 4u || code > 511u || trig_special(code) < TRIG_SPECIALS)
        return 0u;
    uint32_t len = 8u;
    while (!(code >> len))
        len--;
    return (code & ((1u << len) - 1u)) ? len : 0u;
}

KEEP_UNTIL_USED(trig_mask) uint32_t trig_mask(uint32_t code)
{
    uint32_t len = trig_len(code);
    return len ? code & ((1u << len) - 1u) : 0u;
}

KEEP_UNTIL_USED(trig_kind) uint32_t trig_kind(uint32_t code)
{
    if (trig_special(code) < TRIG_SPECIALS)
        return TRIG_SPECIAL_KIND;
    return trig_len(code) ? TRIG_CYCLE : TRIG_NONE;
}

KEEP_UNTIL_USED(trig_cycle) uint32_t trig_cycle(uint32_t len, uint32_t mask)
{
    if (len < 2u || len > 8u || !mask || mask >= (1u << len))
        return 0u;
    return (1u << len) | mask;
}

uint32_t trig_plays(uint32_t code, const trig_ctx_t *c)
{
    uint32_t kind = trig_kind(code);
    if (kind == TRIG_CYCLE)
        return (trig_mask(code) >> (c->count % trig_len(code))) & 1u;
    if (kind != TRIG_SPECIAL_KIND)
        return 1u;
    switch (trig_special(code)) {
    case TRIG_FIRST:     return c->count == 0u;
    case TRIG_NOT_FIRST: return c->count != 0u;
    case TRIG_FILL:      return c->fill != 0u;
    case TRIG_NOT_FILL:  return c->fill == 0u;
    case TRIG_PRE:       return c->pre != 0u;
    case TRIG_NOT_PRE:   return c->pre == 0u;
    case TRIG_LAST:      return c->last != 0u;
    default:             return c->last == 0u;
    }
}

uint32_t trig_conditional(uint32_t code, uint32_t prob)
{
    uint32_t kind = trig_kind(code);
    if (kind == TRIG_SPECIAL_KIND) {
        uint32_t s = trig_special(code);
        return s != TRIG_PRE && s != TRIG_NOT_PRE;
    }
    return kind != TRIG_NONE || prob < 7u;
}

uint32_t trig_edit(uint32_t code, uint32_t pad, uint32_t gesture, uint32_t drum)
{
    if (pad > 7u)
        return code;
    if (gesture == TRIG_SHIFT) {
        if (!drum && (pad == TRIG_FILL || pad == TRIG_NOT_FILL))
            return code;
        return code == TRIG_SPECIAL[pad] ? 0u : TRIG_SPECIAL[pad];
    }
    uint32_t len = pad + 1u, kind = trig_kind(code);
    if (gesture == TRIG_HOLD) {
        if (!pad)
            return 0u;
        if (kind != TRIG_CYCLE)
            return trig_cycle(len, 1u);
        if (trig_len(code) == len)
            return 0u;
        uint32_t kept = trig_mask(code) & ((1u << len) - 1u);
        return trig_cycle(len, kept ? kept : 1u);
    }
    if (kind == TRIG_CYCLE && pad < trig_len(code)) {
        uint32_t mask = trig_mask(code) ^ (1u << pad);
        return mask ? trig_cycle(trig_len(code), mask) : 0u;
    }
    return code;
}

void trig_row4(uint32_t code, uint32_t shift, uint32_t drum, uint16_t *out)
{
    uint32_t kind = trig_kind(code), special = trig_special(code);
    for (uint32_t i = 0; i < 8u; i++) {
        uint32_t col = COL_OFF;
        if (shift) {
            if (drum || (i != TRIG_FILL && i != TRIG_NOT_FILL))
                col = SPECIAL_COL[i][special == i ? 0 : 1];
        } else if (kind == TRIG_CYCLE) {
            if (i < trig_len(code))
                col = (trig_mask(code) >> i) & 1u ? COL_CYAN : COL_CYAN_DIM;
        } else if (kind == TRIG_SPECIAL_KIND) {
            col = SPECIAL_COL[special][1];
        }
        out[i] = (uint16_t)col;
    }
}

uint32_t trig_drum_get(const uint8_t *pattern, uint32_t step)
{
    return pattern[0x88u + step] | (uint32_t)((pattern[0x84u + (step >> 3)] >> (step & 7u)) & 1u) << 8;
}

void trig_drum_set(uint8_t *pattern, uint32_t step, uint32_t code)
{
    uint8_t bit = (uint8_t)(1u << (step & 7u));
    pattern[0x88u + step] = (uint8_t)code;
    pattern[0x84u + (step >> 3)] = (uint8_t)((pattern[0x84u + (step >> 3)] & ~bit) | (code & 0x100u ? bit : 0u));
}

uint32_t trig_note_get(const uint8_t *step)
{
    return step[2] | (uint32_t)(step[3] & 1u) << 8;
}

void trig_note_set(uint8_t *step, uint32_t code)
{
    step[2] = (uint8_t)code;
    step[3] = (uint8_t)((code >> 8) & 1u);
}
