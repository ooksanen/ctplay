/* Arpeggio maths (arp_math.h). Tests: tests/arp_model.py is the reference, test_arp.py compares. */
#include "arp_math.h"
#include "chord_held.h"

static const uint8_t BASE[4] = {24u, 12u, 6u, 3u};

uint32_t arp_rate_ticks(uint32_t a0)
{
    uint32_t base = BASE[ARP_RATE(a0)], mod = ARP_MOD(a0);
    if (mod == MOD_TRIPLET)
        return base * 2u / 3u;
    if (mod == MOD_DOTTED && base != 3u)
        return base * 3u / 2u;
    return base;
}

uint32_t arp_gate_ticks(uint32_t a0, uint32_t a1)
{
    uint32_t k = ARP_GATE(a1) + 1u, rt = arp_rate_ticks(a0);
    if (k >= 6u)
        return 0u;
    uint32_t t = (k * rt + 3u) / 6u;
    if (t > rt - 1u)
        t = rt - 1u;
    return t ? t : 1u;
}

uint32_t arp_gate_ms(uint32_t a0, uint32_t a1, uint32_t bpm)
{
    uint32_t k = ARP_GATE(a1) + 1u;
    if (k >= 6u)
        return 0u;
    uint32_t ms = k * arp_rate_ticks(a0) * 2500u / (6u * bpm);
    return ms ? ms : 1u;
}

static uint32_t bounce(uint32_t pos, uint32_t n)
{
    if (n == 1u)
        return 0u;
    uint32_t p = pos % (2u * n - 2u);
    return p < n ? p : 2u * n - 2u - p;
}

uint32_t arp_index(uint32_t pattern, uint32_t pos, uint32_t n_last, uint16_t *rng)
{
    uint32_t n = n_last & 0xFFu, last = (n_last >> 8) & 0xFFu;
    switch (pattern) {
    case ARP_UP:
    case ARP_PLAYED:
        return pos % n;
    case ARP_DOWN:
        return n - 1u - pos % n;
    case ARP_UPDOWN:
        return bounce(pos, n);
    case ARP_DOWNUP:
        return n - 1u - bounce(pos, n);
    default: {
        uint32_t r = *rng;
        r = (r >> 1) ^ (r & 1u ? 0xB400u : 0u);
        *rng = (uint16_t)r;
        uint32_t j = r % n;
        if (n > 1u && j == last)
            j = (j + 1u) % n;
        return j;
    }
    }
}
