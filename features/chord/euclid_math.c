#include "euclid_math.h"

uint32_t euclid_mask(uint32_t k, uint32_t n, uint32_t r)
{
    if (n == 0u || n > 32u)
        return 0;
    if (k >= n)
        return n == 32u ? 0xFFFFFFFFu : (1u << n) - 1u;
    uint32_t mask = 0, acc = (r % n) * k % n;       /* ((i + r) * k) mod n, stepped by k */
    for (uint32_t i = 0; i < n; i++) {
        if (acc < k)
            mask |= 1u << i;
        acc += k;
        if (acc >= n)
            acc -= n;
    }
    return mask;
}
