/* Note repeat maths (repeat_math.h). Tests: tests/repeat_model.py is the reference, test_repeat.py compares. */
#include "repeat_math.h"

static const uint8_t TICKS[9] = {0u, 24u, 12u, 6u, 3u, 16u, 8u, 4u, 2u};

uint32_t repeat_ticks(uint32_t rate)
{
    return rate <= 8u ? TICKS[rate] : 0u;
}

uint32_t repeat_vel(uint32_t shape, uint32_t v, uint32_t e, uint32_t beat)
{
    uint32_t m = e < 24u ? e : 24u, r = v;
    if (shape == 1u)
        r = v * (32u - m) / 32u;        /* v - (3v/4) m/24 */
    else if (shape == 2u)
        r = v * (8u + m) / 32u;         /* v/4 + (3v/4) m/24 */
    else if (shape == 3u && !beat)
        r = 2u * v / 3u;
    return r ? r : 1u;
}

uint32_t repeat_due(uint32_t tick, uint32_t press_tick, uint32_t ticks, uint32_t playing)
{
    uint32_t e = tick - press_tick;
    if (ticks == 0u || e == 0u)
        return 0u;
    if (playing)
        return tick % ticks == 0u && 2u * e >= ticks;
    return e % ticks == 0u;
}
