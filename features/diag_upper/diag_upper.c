/* diag_upper: the SL01D diagnostic. Is the RAM above stock's heap free? Shift + Drum 4 toggles a page on the pads.
 *
 * Filled part 0x20044E58-0x2004F000 (41,384 B): at the first hook call a pattern (each word = its address XOR KEY) is
 * written to every word. Chunks 0-19 are 2 KB each from 0x20045000 (chunk c = 0x20045000 + 0x800 * c);
 * chunk 20 is 0x20044E58-0x20045000 (424 B).
 * Watched part 0x2004F000-0x20050000 (4 KB, where the main stack lives): 8 blocks of 512 B, checksummed (FNV-1a) at the
 * first hook call and never written.
 * Each LED refresh re-checks one chunk and one block in turn; a change is latched until power-off.
 *   pads 1-20 = chunks 0-19 (pads 15-20 = SRAM2), pad 21 = chunk 20:
 *                green    pattern intact all session
 *                magenta  changed (something else wrote it)
 *                red      did not read back right after the fill
 *   pad 23    = carried over: cyan = every chunk already held the pattern at power-on, dim white = some did, off = none
 *   pad 24    = slim runtime alive (white)
 *   pads 25-32 = watched blocks 0-7: green = unchanged since boot, magenta = changed (the main stack reached it).
 * Nothing is ever written at or above 0x2004F000. */
#include "slim.h"
#include "stock.h"

#define FILL_LO          0x20044E58u
#define FILL_HI          0x2004F000u
#define WATCH_LO         0x2004F000u
#define CHUNK_BYTES      0x800u
#define CHUNK0_END       0x20045000u         /* chunk 20 is the short one, FILL_LO..CHUNK0_END */
#define CHUNKS           21u
#define BLOCK_BYTES      512u
#define BLOCKS           8u
#define KEY              0x5A1A0B5Eu
#define BTN_DRUM4        7u
#define CTRL_SHIFT_STORE 0x0Cu

#define COL_OFF          0x00u
#define COL_GREEN        0x17u
#define COL_MAGENTA      0x32u
#define COL_RED          0x53u
#define COL_WHITE        0x01u
#define COL_DIM_WHITE    0x02u
#define COL_CYAN         0x4Du
#define PAD_CARRIED      22u                 /* out[] index of pad 23 */
#define PAD_ALIVE        23u                 /* pad 24 */
#define PAD_BLOCK0       24u                 /* pad 25 */

static uint32_t chunk_failed;                    /* bit c: chunk c did not read back after the fill */
static uint32_t chunk_changed;    /* bit c: chunk c changed since the fill */
static uint8_t block_changed;     /* bit b: watched block b changed since boot */
static uint32_t block_sum_boot[BLOCKS];
static uint8_t carried;                          /* chunks already holding the pattern at power-on, 0-21 */
static uint8_t chunk_cursor, block_cursor;
static volatile uint8_t page_on;

static uint32_t pattern(uint32_t addr)
{
    return addr ^ KEY;
}

static uint32_t chunk_lo(uint32_t c)
{
    return c == CHUNKS - 1u ? FILL_LO : CHUNK0_END + c * CHUNK_BYTES;
}

static uint32_t chunk_hi(uint32_t c)
{
    return c == CHUNKS - 1u ? CHUNK0_END : CHUNK0_END + (c + 1u) * CHUNK_BYTES;
}

static int chunk_intact(uint32_t c)
{
    for (uint32_t a = chunk_lo(c); a < chunk_hi(c); a += 4u)
        if (*(const volatile uint32_t *)a != pattern(a))
            return 0;
    return 1;
}

static uint32_t block_sum(uint32_t b)
{
    const volatile uint32_t *w = (const volatile uint32_t *)(WATCH_LO + b * BLOCK_BYTES);
    uint32_t sum = 0x811C9DC5u;                  /* FNV-1a over the words */
    for (uint32_t i = 0; i < BLOCK_BYTES / 4u; i++)
        sum = (sum ^ w[i]) * 0x01000193u;
    return sum;
}

static int shift_held(void *ctrl)
{
    void *store = *(void **)((uint8_t *)ctrl + CTRL_SHIFT_STORE);
    return *param_get(store, 0u) != 0u;
}

void diag_upper_init(void)
{
    uint32_t n = 0;
    for (uint32_t c = 0; c < CHUNKS; c++)        /* 1. carried over from an earlier session? */
        n += (uint32_t)chunk_intact(c);
    carried = (uint8_t)n;
    for (uint32_t a = FILL_LO; a < FILL_HI; a += 4u)   /* 2. fill */
        *(volatile uint32_t *)a = pattern(a);
    for (uint32_t c = 0; c < CHUNKS; c++)        /* 3. read back */
        if (!chunk_intact(c))
            chunk_failed |= 1u << c;
    for (uint32_t b = 0; b < BLOCKS; b++)        /* 4. checksum the watched part */
        block_sum_boot[b] = block_sum(b);
}

static void recheck_all(void)
{
    for (uint32_t c = 0; c < CHUNKS; c++)
        if (!chunk_intact(c))
            chunk_changed |= 1u << c;
    for (uint32_t b = 0; b < BLOCKS; b++)
        if (block_sum(b) != block_sum_boot[b])
            block_changed |= (uint8_t)(1u << b);
}

int diag_upper_on_button(void *ctrl, uint32_t id, uint32_t *ret)
{
    (void)ret;
    if (id != BTN_DRUM4 || !shift_held(ctrl))
        return SLIM_PASS;
    if (page_on) {
        page_on = 0;
    } else {
        recheck_all();
        __asm__ volatile("" ::: "memory");
        page_on = 1;
    }
    return SLIM_HANDLED;
}

void diag_upper_on_leds(void *ctrl, uint16_t *out)
{
    (void)ctrl;
    if (!chunk_intact(chunk_cursor))             /* one chunk and one block per refresh, page on or off; bits only set */
        chunk_changed |= 1u << chunk_cursor;
    chunk_cursor = (uint8_t)((chunk_cursor + 1u) % CHUNKS);
    if (block_sum(block_cursor) != block_sum_boot[block_cursor])
        block_changed |= (uint8_t)(1u << block_cursor);
    block_cursor = (uint8_t)((block_cursor + 1u) % BLOCKS);
    if (!page_on)
        return;
    for (uint32_t i = 0; i < 32u; i++)
        out[i] = COL_OFF;
    for (uint32_t c = 0; c < CHUNKS; c++)
        out[c] = (chunk_failed >> c) & 1u ? COL_RED : (chunk_changed >> c) & 1u ? COL_MAGENTA : COL_GREEN;
    out[PAD_CARRIED] = carried >= CHUNKS ? COL_CYAN : carried > 0u ? COL_DIM_WHITE : COL_OFF;
    out[PAD_ALIVE] = COL_WHITE;
    for (uint32_t b = 0; b < BLOCKS; b++)
        out[PAD_BLOCK0 + b] = (block_changed >> b) & 1u ? COL_MAGENTA : COL_GREEN;
}
