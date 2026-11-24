/* Melodic generator maths (melody_math.h). Tests: tests/melody_model.py is the reference, test_melody.py compares. */
#include "melody_math.h"
#include "chord_math.h"
#include "arp_math.h"

#define MAJOR_MASK   0x00111044u     /* as chord_math.c */
#define ARP_UPDOWN_P 3u              /* arp_index patterns (chord_held.h, which holds the engine's state declarations) */
#define ARP_RANDOM_P 5u
#define LFSR16_START 0xA5u
#define CAND_MAX     48u
#define WALK_LIMIT   (12u * 9u)      /* semitones walked at most, as chord_math.c */

uint32_t melody_seed_next(uint32_t s)
{
    return (s >> 1) ^ ((s & 1u) ? 0xB8u : 0u);
}

static uint32_t lfsr16(uint32_t r)
{
    return (r >> 1) ^ ((r & 1u) ? 0xB400u : 0u);
}

static uint32_t weight(uint32_t i)
{
    uint32_t q = i % 16u;
    if (q == 0u)
        return i == 0u ? 20u : 16u;
    if ((q & 3u) == 0u)
        return 12u;
    if ((q & 3u) == 3u)
        return 9u;
    if ((q & 3u) == 2u)
        return 6u;
    return 3u;
}

uint32_t melody_groove(uint32_t k, uint32_t n, uint32_t r, uint32_t seed)
{
    if (n == 0u || n > 32u || k == 0u)
        return 0;
    if (k >= n)
        return n == 32u ? 0xFFFFFFFFu : (1u << n) - 1u;
    uint8_t score[32];
    uint32_t state = ((seed & 0xFFu) << 8) | LFSR16_START, base = 0, out = 0;
    for (uint32_t i = 0; i < n; i++) {
        state = lfsr16(state);
        score[i] = (uint8_t)(weight(i) + state % 5u);
    }
    for (uint32_t i = 0; i < n; i++) {          /* rank = steps that beat this one (higher score, or equal and lower i) */
        uint32_t rank = 0;
        for (uint32_t j = 0; j < n; j++)
            if (score[j] > score[i] || (score[j] == score[i] && j < i))
                rank++;
        if (rank < k)
            base |= 1u << i;
    }
    for (uint32_t i = 0; i < n; i++)
        if ((base >> ((i + r) % n)) & 1u)
            out |= 1u << i;
    return out;
}

static int in_scale(uint32_t mask, uint32_t v)
{
    return ((mask >> (2u * (v % 12u))) & 3u) == 0u;
}

/* The pitch `steps` scale notes above `note`, octaves included (as chord_math.c's degrees_up). */
static uint32_t degrees_up(uint32_t mask, uint32_t note, uint32_t steps)
{
    for (uint32_t w = 0; steps && w < WALK_LIMIT; w++)
        if (in_scale(mask, ++note))
            steps--;
    return note;
}

uint32_t melody_root(uint32_t cfg1, uint32_t last, uint32_t mask)
{
    uint32_t d = MEL_ROOT(cfg1);
    if (d == 0u)
        return last;
    return (uint32_t)(12 * MEL_OCTAVE(cfg1) + (int32_t)degrees_up(mask ? mask : MAJOR_MASK, 72u, d - 1u));
}

/* Insert v into the sorted candidate list c (n entries) unless it is there already or outside 12 <= v + key <= 139. */
static uint32_t add(uint8_t *c, uint32_t n, int32_t v, uint32_t key)
{
    if (v + (int32_t)key < 12 || v + (int32_t)key > 139 || n >= CAND_MAX)
        return n;
    uint32_t i = 0;
    while (i < n && (int32_t)c[i] < v)
        i++;
    if (i < n && (int32_t)c[i] == v)
        return n;
    for (uint32_t j = n; j > i; j--)
        c[j] = c[j - 1u];
    c[i] = (uint8_t)v;
    return n + 1u;
}

void melody_pool(melody_pool_t *p, uint32_t root, uint32_t mask, uint32_t settings)
{
    uint8_t c[CAND_MAX];
    uint32_t n = 0, range = MEL_RANGE(p->cfg0), key = CHORD_KEY(settings), m = mask ? mask : MAJOR_MASK;
    uint32_t fifth = in_scale(m, root + 7u) ? (root + 7u) % 12u : chord_degree_class(root, mask, 4u);
    if (MEL_POOL(p->cfg0)) {
        n = add(c, n, (int32_t)root, key);                 /* the root, even outside the scale */
        for (uint32_t v = root; v <= root + 12u * range; v++)
            if (in_scale(m, v))
                n = add(c, n, (int32_t)v, key);
    } else {
        uint8_t other[CHORD_MAX_OTHER];
        if (!CHORD_HAS_SHAPE(settings))
            settings = (settings & ~7u) | 1u;
        uint32_t no = chord_notes(root, mask, settings, other);
        for (uint32_t o = 0; o < range; o++) {
            n = add(c, n, (int32_t)(root + 12u * o), key);
            for (uint32_t i = 0; i < no; i++)
                n = add(c, n, (int32_t)other[i] + 12 * (int32_t)o, key);
        }
    }
    if (MEL_ORDER(p->cfg0) == MEL_BASS) {         /* the root's fifth, when no note of the pool has its pitch class */
        uint32_t have = 0;
        for (uint32_t i = 0; i < n; i++)
            if (c[i] % 12u == fifth)
                have = 1;
        if (!have)
            n = add(c, n, (int32_t)(root + (fifth + 12u - root % 12u) % 12u), key);
    }
    if (n > MELODY_POOL_MAX)
        n = MELODY_POOL_MAX;
    p->pn = (uint8_t)n;
    p->fifth = (uint8_t)fifth;
    p->root_at = 0;
    for (uint32_t i = n; i-- > 0;) {              /* ends on the lowest note with the root's pitch class */
        p->pool[i] = c[i];
        if (c[i] % 12u == root % 12u)
            p->root_at = (uint8_t)i;
    }
}

static const int8_t WALK[10] = {-2, -1, -1, -1, 0, 0, 1, 1, 1, 2};

/* Bass, a hit off the quarters: the pool note picked by weight 4 (root's pitch class), 2 (fifth's), 1 (others). */
static uint32_t bass_weighted(const melody_pool_t *p, uint32_t r, uint32_t rc, uint32_t fc)
{
    uint32_t total = 0, w;
    for (uint32_t q = 0; q < p->pn; q++) {
        uint32_t c = p->pool[q] % 12u;
        total += c == rc ? 4u : c == fc ? 2u : 1u;
    }
    r %= total;
    for (uint32_t q = 0; q < p->pn; q++) {
        uint32_t c = p->pool[q] % 12u;
        w = c == rc ? 4u : c == fc ? 2u : 1u;
        if (r < w)
            return q;
        r -= w;
    }
    return p->root_at;
}

/* Bass, a hit on a quarter: the root note, or one time in four another pool note with its pitch class. */
static uint32_t bass_quarter(const melody_pool_t *p, uint16_t *rng, uint32_t rc)
{
    if (*rng % 4u != 0u)
        return p->root_at;
    uint32_t cnt = 0;
    for (uint32_t q = 0; q < p->pn; q++)
        if (q != p->root_at && p->pool[q] % 12u == rc)
            cnt++;
    if (!cnt)
        return p->root_at;
    *rng = (uint16_t)lfsr16(*rng);
    uint32_t pick = *rng % cnt;
    for (uint32_t q = 0; q < p->pn; q++)
        if (q != p->root_at && p->pool[q] % 12u == rc && pick-- == 0u)
            return q;
    return p->root_at;
}

uint32_t melody_line(const melody_pool_t *p, uint32_t hits, uint8_t *out)
{
    uint32_t order = MEL_ORDER(p->cfg0), pn = p->pn, s = (uint32_t)p->seed - 1u, j = 0, last = 0xFFu;
    uint16_t rng = (uint16_t)(((uint32_t)p->seed << 8) | LFSR16_START);
    int32_t pos = p->root_at;
    uint32_t rc = pn ? p->pool[p->root_at] % 12u : 0u, fc = p->fifth;
    if (order == MEL_SAME) {                      /* the caller plays the chord: only count */
        for (uint32_t i = 0; i < p->n && i < 32u; i++)
            j += (hits >> i) & 1u;
        return j;
    }
    for (uint32_t i = 0; i < p->n && i < 32u; i++) {
        if (!((hits >> i) & 1u))
            continue;
        uint32_t idx = 0;
        switch (order) {
        case MEL_UP:
            idx = (s + j) % pn;
            break;
        case MEL_DOWN:
            idx = pn - 1u - (s + j) % pn;
            break;
        case MEL_UPDN:
            idx = arp_index(ARP_UPDOWN_P, s + j, pn, 0);
            break;
        case MEL_CLIMB:
            idx = (s + j / 3u + j % 3u) % pn;
            break;
        case MEL_WALK:
            if (j) {
                rng = (uint16_t)lfsr16(rng);
                pos += WALK[rng % 10u];
                if (pos < 0)
                    pos = -pos;
                if (pos > (int32_t)pn - 1)
                    pos = 2 * ((int32_t)pn - 1) - pos;
                if (pos < 0)
                    pos = 0;
            }
            idx = (uint32_t)pos;
            break;
        case MEL_RANDOM:
            idx = arp_index(ARP_RANDOM_P, j, pn | last << 8, &rng);
            last = idx;
            break;
        default:                                  /* MEL_BASS: hit 0 on the root */
            idx = p->root_at;
            if (j) {
                rng = (uint16_t)lfsr16(rng);
                idx = i % 4u == 0u ? bass_quarter(p, &rng, rc) : bass_weighted(p, rng, rc, fc);
            }
            break;
        }
        out[j++] = p->pool[idx];
    }
    return j;
}

uint32_t melody_accent(uint32_t accent, uint32_t j, uint32_t i)
{
    switch (accent) {
    case 1u:
        return j == 0u;
    case 2u:
        return i % 4u == 0u;
    case 3u:
        return j % 3u == 0u;
    default:
        return 0;
    }
}

uint32_t melody_next_len(uint32_t hits, uint32_t n, uint32_t i)
{
    uint32_t d = 1;
    while (d < n && !((hits >> ((i + d) % n)) & 1u))
        d++;
    d *= 6u;
    return d > MELODY_NEXT_MAX ? MELODY_NEXT_MAX : d;
}

/* --- PL14 variations --- */
/* The link drops what nothing calls (--gc-sections), and pick() inlines melody_amount_limit, so its own copy is called by
 * nothing but the emulation tests: this section name is KEEPed by the linker script. */
#define KEEP_UNTIL_USED(name) __attribute__((section(".text.slim_call_keep_" #name)))
static const uint8_t AMOUNT_LIMIT[4] = {0, 64, 85, 128};
static const uint8_t CYCLE_LEN[5] = {0, 3, 5, 6, 7};

uint32_t melody_draw(uint32_t seed, uint32_t salt, uint32_t i)
{
    uint32_t x = (seed << 16 | salt << 8 | i) * 0x9E3779B1u;
    x ^= x >> 15;
    x *= 0x85EBCA6Bu;
    x ^= x >> 13;
    return x >> 24;
}

KEEP_UNTIL_USED(melody_amount_limit) uint32_t melody_amount_limit(uint32_t a)
{
    return AMOUNT_LIMIT[a & 3u];
}

uint32_t melody_cycle_len(uint32_t code)
{
    return code < 5u ? CYCLE_LEN[code] : 0u;
}

uint32_t melody_repeat(uint32_t base, uint32_t c, uint32_t n)
{
    if (c == 0u || c >= n)
        return base;
    uint32_t out = 0;
    for (uint32_t i = 0; i < n; i++)
        out |= ((base >> (i % c)) & 1u) << i;
    return out;
}

uint32_t melody_combine(uint32_t a, uint32_t b, uint32_t mode)
{
    switch (mode) {
    case 1u:
        return a & b;
    case 2u:
        return a | b;
    case 3u:
        return a ^ b;
    case 4u:
        return a & ~b;
    default:
        return a;
    }
}

/* The items of `set` (not its lowest) whose draw under `salt` is below the amount's limit. */
static uint32_t pick(uint32_t set, uint32_t amount, uint32_t seed, uint32_t salt)
{
    uint32_t out = 0, limit = melody_amount_limit(amount);
    for (uint32_t i = 0; i < 32u; i++)
        if (((set >> i) & 1u) && melody_draw(seed, salt, i) < limit)
            out |= 1u << i;
    return out & ~(set & (0u - set));
}

uint32_t melody_thin(uint32_t hits, uint32_t amount, uint32_t seed)
{
    return hits & ~pick(hits, amount, seed, MEL_SALT_THIN);
}

uint32_t melody_ties(uint32_t hits, uint32_t amount, uint32_t seed)
{
    return pick(hits, amount, seed, MEL_SALT_TIES);
}

uint32_t melody_jumps(uint32_t struck, uint32_t amount, uint32_t seed)
{
    return pick(struck, amount, seed, MEL_SALT_JUMPS);
}

uint32_t melody_jump(uint32_t note, uint32_t key)
{
    if (note + 12u + key <= 139u)
        return note + 12u;
    if (note >= 12u && note - 12u + key >= 12u)
        return note - 12u;
    return note;
}
