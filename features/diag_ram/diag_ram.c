/* diag_ram: the SL00D diagnostic. Two pages on the pads, both toggled with Shift + a Drum button.
 *
 * ITCM page (Shift + Drum 4): decides whether the 16 KB ITCM (0x00000000-0x00003FFF) is free for slim.
 * At the first hook call after power-on (within milliseconds of boot) a checksum of each 1 KB block is stored;
 * afterwards one block is re-checksummed per LED refresh, and any change is latched. Switching the page on probes every block:
 *   pads 1-16 = blocks 0-15:  green    zero at every check, unchanged and writable (not observed in use)
 *                              yellow   non-zero (not write-tested: code, tables or never-initialised RAM)
 *                                       or the block that holds the vector table (SCB->VTOR)
 *                              magenta  changed at any time since boot (one block checked per LED refresh)
 *                              red      a zero block whose test word did not read back  (not RAM)
 *   pad 32 white = the slim runtime is initialised.
 * The write test touches one word per block with interrupts masked and always restores it; it is never run on a
 * non-zero block or on the vector-table block.
 *
 * Stack page (Shift + Drum 3): shows how much of eight RTOS task stacks is still unused. Stock fills each stack with
 * 0xA5A5A5A5 and only ever overwrites it, so the untouched fill is the headroom. Stock's boot layout is deterministic,
 * so each column is a fixed stack: column c counts consecutive fill words upward from stack_base[c] (the stack's bottom;
 * the stack grows down towards it), the same task in every photo:
 *   each green pad is up to 512 B, drawn from the bottom (1 pad = 128-512 B, 4 pads = 1.5-2 KB);
 *   a white top pad = more than 2 KB; a single red pad at the bottom = under 128 B;
 *   column off = the stack has used everything down to its bottom (no free stack left!);
 *   single magenta pad at the bottom = this device's memory layout differs from the RAM dump (the base is outside the
 *   heap or does not hold fill at the first hook call): that column is never measured.
 * The scan runs once when the page is switched on, is read-only and stays inside [heap start, heap current); a reading
 * is the high-water mark since boot (fill never returns). No "alive" pad on this page. */
#include "slim.h"
#include "stock.h"

#define ITCM_BASE        0x00000000u
#define BLOCK_BYTES      1024u
#define BLOCKS           16u
#define TEST_OFFSET      (BLOCK_BYTES / 2u)  /* 0x200 into block 0 = vector 128, past the STM32F745's vectors */
#define BTN_DRUM3        6u                  /* ids 0-7: Synth 1, Synth 2, MIDI 1, MIDI 2, Drum 1-4 */
#define BTN_DRUM4        7u
#define CTRL_SHIFT_STORE 0x0Cu               /* controller + 0x0C: parameter store; parameter 0 = Shift held */
#define PADS             32u
#define PAD_ALIVE        31u                 /* pad 32 */
#define COL_OFF          0x00u
#define COL_WHITE        0x01u
#define COL_GREEN        0x17u
#define COL_RED          0x53u
#define STACK_FILL       0xA5A5A5A5u         /* RTOS stack fill */
#define STACK_COLS       8u
#define MAX_RUN_WORDS    0x4000u             /* bound per column */
#define COL_MAGENTA      0x32u
#define RAM_LO           0x20000000u
#define RAM_HI           0x20050000u

enum { PAGE_OFF, PAGE_ITCM, PAGE_STACK };

enum { ST_FREE, ST_DATA, ST_CHANGED, ST_FAILED };

/* Stock palette codes, chosen from the device's RGB table (RAM 0x20003804, B G R per code). */
static const uint8_t state_colour[] = {
    [ST_FREE] = COL_GREEN,     /* green   (0, 255, 0) */
    [ST_DATA] = 0x2D,     /* yellow  (255, 255, 25) */
    [ST_CHANGED] = 0x32,  /* magenta (198, 58, 198) */
    [ST_FAILED] = COL_RED,   /* red     (255, 0, 0) */
};

static uint32_t boot_sum[BLOCKS];
static uint8_t state[BLOCKS];
static volatile uint8_t page;
static uint16_t run_bytes[STACK_COLS];
static uint8_t layout_bad;                       /* bit c: column c cannot be measured */

/* Task stack bottoms in stock's deterministic boot layout, from ram_dump_firmware_0x08037988.bin. */
static const uint32_t stack_base[STACK_COLS] = {
    0x20006A58u, 0x20006AA4u, 0x20006E70u, 0x2000775Cu, 0x200084DCu, 0x20008D44u, 0x200092B8u, 0x2000AD7Cu,
};
static uint8_t scan_block;
static volatile uint16_t changed_mask;

static const volatile uint32_t *block_words(uint32_t b)
{
    return (const volatile uint32_t *)(ITCM_BASE + b * BLOCK_BYTES);
}

static uint32_t block_sum(uint32_t b)
{
    const volatile uint32_t *w = block_words(b);
    uint32_t sum = 0x811C9DC5u;                 /* FNV-1a over the words */
    for (uint32_t i = 0; i < BLOCK_BYTES / 4u; i++)
        sum = (sum ^ w[i]) * 0x01000193u;
    return sum;
}

static int block_zero(uint32_t b)
{
    const volatile uint32_t *w = block_words(b);
    for (uint32_t i = 0; i < BLOCK_BYTES / 4u; i++)
        if (w[i] != 0u)
            return 0;
    return 1;
}

static int block_writable(uint32_t b)
{
    volatile uint32_t *w = (volatile uint32_t *)(ITCM_BASE + b * BLOCK_BYTES + TEST_OFFSET);
    uint32_t primask = slim_irq_save();
    uint32_t old = *w;
    uint32_t pattern = old ^ 0xA5A5A5A5u;
    *w = pattern;
    uint32_t back = *w;
    *w = old;
    uint32_t restored = *w;
    slim_irq_restore(primask);
    return back == pattern && restored == old;
}

static void probe(void)
{
    uint32_t vtor = scb_vtor;
    uint32_t vtor_block = BLOCKS;                /* none */
    if (vtor < BLOCKS * BLOCK_BYTES)
        vtor_block = vtor / BLOCK_BYTES;
    for (uint32_t b = 0; b < BLOCKS; b++) {
        if ((changed_mask & (1u << b)) || block_sum(b) != boot_sum[b])
            state[b] = ST_CHANGED;
        else if (b == vtor_block || !block_zero(b))
            state[b] = ST_DATA;
        else if (!block_writable(b))
            state[b] = ST_FAILED;
        else
            state[b] = ST_FREE;
    }
}

static int heap_ok(uint32_t hs, uint32_t hc)
{
    return hs >= RAM_LO && hs <= hc && hc <= RAM_HI;
}

static void check_layout(void)
{
    uint32_t hs = heap_start, hc = heap_cur & ~3u;
    layout_bad = 0;
    for (uint32_t c = 0; c < STACK_COLS; c++) {
        uint32_t base = stack_base[c];
        if (!heap_ok(hs, hc) || base < hs || base >= hc || *(const volatile uint32_t *)base != STACK_FILL)
            layout_bad |= (uint8_t)(1u << c);
    }
}

static void scan_stacks(void)
{
    uint32_t hs = heap_start, end = heap_cur & ~3u;
    int ok = heap_ok(hs, end);
    for (uint32_t c = 0; c < STACK_COLS; c++) {
        uint32_t words = 0;
        run_bytes[c] = 0;
        if (!ok || (layout_bad & (1u << c)))
            continue;
        for (uint32_t a = stack_base[c]; a < end && words < MAX_RUN_WORDS && *(const volatile uint32_t *)a == STACK_FILL;
             a += 4u)
            words++;
        run_bytes[c] = (uint16_t)(words * 4u > 0xFFFFu ? 0xFFFFu : words * 4u);
    }
}

static int shift_held(void *ctrl)
{
    void *store = *(void **)((uint8_t *)ctrl + CTRL_SHIFT_STORE);
    return *param_get(store, 0u) != 0u;
}

void diag_ram_init(void)
{
    for (uint32_t b = 0; b < BLOCKS; b++)
        boot_sum[b] = block_sum(b);
    check_layout();
}

int diag_ram_on_button(void *ctrl, uint32_t id, uint32_t *ret)
{
    (void)ret;
    if ((id != BTN_DRUM4 && id != BTN_DRUM3) || !shift_held(ctrl))
        return SLIM_PASS;
    if (id == BTN_DRUM4) {
        if (page == PAGE_ITCM) {
            page = PAGE_OFF;
        } else {
            probe();
            __asm__ volatile("" ::: "memory");
            page = PAGE_ITCM;
        }
    } else {
        if (page == PAGE_STACK) {
            page = PAGE_OFF;
        } else {
            scan_stacks();
            __asm__ volatile("" ::: "memory");
            page = PAGE_STACK;
        }
    }
    /* Stock's handler does some work before its Shift filter (it notifies the store at [ctrl+0x3C] and, in a modal
     * state where [ctrl+0x14] p0 == 8, forwards buttons); for Shift + Drum 3 / 4 that work is skipped: harmless here. */
    return SLIM_HANDLED;
}

void diag_ram_on_leds(void *ctrl, uint16_t *out)
{
    (void)ctrl;
    if (block_sum(scan_block) != boot_sum[scan_block])
        changed_mask |= (uint16_t)(1u << scan_block);
    scan_block = (uint8_t)((scan_block + 1u) % BLOCKS);
    uint32_t p = page;
    if (p == PAGE_OFF)
        return;
    for (uint32_t i = 0; i < PADS; i++)
        out[i] = COL_OFF;
    if (p == PAGE_ITCM) {
        for (uint32_t b = 0; b < BLOCKS; b++)
            out[b] = state_colour[state[b]];
        out[PAD_ALIVE] = COL_WHITE;
        return;
    }
    for (uint32_t c = 0; c < STACK_COLS; c++) {
        uint32_t size = run_bytes[c];
        if (layout_bad & (1u << c)) {
            out[24u + c] = COL_MAGENTA;
            continue;
        }
        if (size == 0u)
            continue;
        if (size < 128u) {
            out[24u + c] = COL_RED;
            continue;
        }
        uint32_t h = (size + 511u) / 512u;
        if (h > 4u)
            h = 4u;
        for (uint32_t r = 4u - h; r < 4u; r++)
            out[r * 8u + c] = COL_GREEN;
        if (size > 2048u)
            out[c] = COL_WHITE;
    }
}
