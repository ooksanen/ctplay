/* Pattern strum maths (roll_math.h). Tests: tests/roll_model.py is the reference, test_roll_model.py compares. */
#include "roll_math.h"

const uint8_t WRITTEN_GAP[4] = {0u, 4u, 2u, 1u};

uint32_t roll_sixths(uint32_t ticks, uint32_t step_ticks)
{
    if (!step_ticks)
        return 0u;
    return (ticks * 6u + step_ticks / 2u) / step_ticks;
}

uint32_t roll_step(uint32_t step, uint32_t add, uint32_t first, uint32_t last)
{
    if (last < first)
        return first;
    if (step < first || step > last)
        return step + add;                          /* outside the loop: straight on; >= 32 the callers drop (beta 2) */
    uint32_t len = last - first + 1u;
    return first + ((step - first) % len + add % len) % len;
}

static void sort_rising(uint8_t *n, uint32_t count)
{
    for (uint32_t i = 1; i < count; i++)
        for (uint32_t j = i; j && n[j - 1u] > n[j]; j--) {
            uint8_t t = n[j];
            n[j] = n[j - 1u];
            n[j - 1u] = t;
        }
}

static void reverse(uint8_t *n, uint32_t count)
{
    for (uint32_t i = 0, j = count - 1u; i < j; i++, j--) {
        uint8_t t = n[i];
        n[i] = n[j];
        n[j] = t;
    }
}

void roll_order(uint8_t *notes, uint32_t n, uint32_t falling)
{
    if (!n)
        return;
    sort_rising(notes, n);
    if (falling)
        reverse(notes, n);
}
