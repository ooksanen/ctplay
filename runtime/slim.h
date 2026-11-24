/* slim runtime API, included by every feature. */
#pragma once
#include <stddef.h>
#include <stdint.h>

#define SLIM_PASS    0   /* continue into stock */
#define SLIM_HANDLED 1   /* return to stock's caller with *ret */

/* The arguments of an entry hook, as the stub saved them (r0-r3), and the result slot. */
typedef struct {
    uint32_t r[4];
    uint32_t ret;
    uint32_t pad;
} slim_args_t;

/* A mid hook's registers (PL16), as its stub saved them after the displaced instructions: r0-r12, lr, the APSR
 * flags. A handler may change any of them; stock goes on with them as the handlers left them. */
typedef struct {
    uint32_t r[13];
    uint32_t lr;
    uint32_t apsr;
    uint32_t pad;
} slim_regs_t;

/* 1 once slim's RAM is reserved and every feature's init() has run; 0 while that is not (yet) the case.
 * The first call reserves the RAM; when stock's heap already reaches it, slim stays off (the heap only grows, so that cannot change). */
int slim_ready(void);

/* Mask interrupts and return the previous PRIMASK; restore it with slim_irq_restore(). */
uint32_t slim_irq_save(void);
void slim_irq_restore(uint32_t primask);

/* Put a variable in ITCM (`[budget] itcm` in feature.toml): zero at the first hook call, no initialiser allowed.
 * Use after the declarator: `uint32_t x[2] SLIM_ITCM(x);`. */
#define SLIM_ITCM(name) __attribute__((section(".bss.itcm." #name)))

void *memset(void *dst, int c, size_t n);
void *memcpy(void *dst, const void *src, size_t n);
