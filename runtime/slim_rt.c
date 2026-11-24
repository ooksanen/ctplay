/* slim runtime: RAM reservation on the first hook call, C start-up, the features' init(). With a feature that asks for
 * ITCM (SLIM_USE_ITCM), also the power-on write test of slim's ITCM span (spec 2026-10-17-itcm-opt-in-design.md). */
#include "slim.h"
#include "stock.h"

extern uint8_t __slim_ram_start[], __slim_ram_top[];
extern uint8_t __slim_data_start[], __slim_data_end[], __slim_bss_start[], __slim_bss_end[];
extern const uint8_t __slim_data_load[];
void slim_features_init(void);   /* generated in dispatch.c */

static volatile uint8_t slim_inited;   /* .bss: valid only once the RAM is reserved */

#if SLIM_USE_ITCM
extern uint32_t __slim_itcm_start[], __slim_itcm_end[];
#define MPU_CTRL (*(volatile uint32_t *)0xE000ED94u)

static uint32_t itcm_pattern(uint32_t pass, volatile uint32_t *w)
{
    uint32_t p = (uint32_t)w ^ 0x5A5AA5A5u;     /* address-dependent: catches aliasing as well as stuck bits */
    return pass == 0u ? p : pass == 1u ? ~p : 0u;
}

/* Write-test slim's ITCM span and leave it zero: 1 = usable. With the MPU on it is never written (a read-only region
 * would fault), and slim stays off instead. */
static int itcm_ok(void)
{
    if (MPU_CTRL & 1u)
        return 0;
    volatile uint32_t *lo = __slim_itcm_start, *hi = __slim_itcm_end;
    for (uint32_t pass = 0; pass < 3u; pass++) {
        for (volatile uint32_t *w = lo; w < hi; w++)
            *w = itcm_pattern(pass, w);
        __asm volatile("dsb" : : : "memory");    /* the reads below must come from the RAM, not the store buffer */
        for (volatile uint32_t *w = lo; w < hi; w++)
            if (*w != itcm_pattern(pass, w))
                return 0;
    }
    return 1;
}
#endif

uint32_t slim_irq_save(void)
{
    uint32_t primask;
    __asm volatile("mrs %0, primask\n\tcpsid i" : "=r"(primask) : : "memory");
    return primask;
}

void slim_irq_restore(uint32_t primask)
{
    __asm volatile("msr primask, %0" : : "r"(primask) : "memory");
}

void *memset(void *dst, int c, size_t n)
{
    uint8_t *d = dst;
    while (n--)
        *d++ = (uint8_t)c;
    return dst;
}

void *memcpy(void *dst, const void *src, size_t n)
{
    uint8_t *d = dst;
    const uint8_t *s = src;
    while (n--)
        *d++ = *s++;
    return dst;
}

int slim_ready(void)
{
    uint32_t start = (uint32_t)__slim_ram_start;
    if (heap_limit == start)
        return slim_inited;               /* reserved: ready once every init() has run */
    /* Unlocked early-out: the bump allocator only grows, so once the heap has reached slim's RAM it never
     * will again. The re-check under the lock below stays. */
    if (heap_limit != (uint32_t)__slim_ram_top || heap_cur > start)
        return 0;
    uint32_t primask = slim_irq_save();
    int claim = heap_limit == (uint32_t)__slim_ram_top && heap_cur <= start;
    if (claim) {
        heap_limit = start;               /* stock can no longer allocate slim's RAM */
        memcpy(__slim_data_start, __slim_data_load, (size_t)(__slim_data_end - __slim_data_start));
        memset(__slim_bss_start, 0, (size_t)(__slim_bss_end - __slim_bss_start));
#if SLIM_USE_ITCM
        if (!itcm_ok())
            claim = 0;                    /* the RAM stays claimed and slim_inited 0: off for the whole boot */
#endif
    }
    slim_irq_restore(primask);
    if (!claim)
        return 0;                         /* the heap already reaches slim's RAM (or the ITCM failed): run as stock */
    slim_features_init();
    slim_inited = 1;
    return 1;
}
