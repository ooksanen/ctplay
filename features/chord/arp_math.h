/* Arpeggio maths: pure functions (spec 2026-10-14-arpeggiator-design.md section 3). Model: tests/arp_model.py. */
#pragma once
#include <stdint.h>

/* Ticks (24 per quarter note) between the notes of the rate in settings byte a0: 1/4 1/8 1/16 1/32 = 24 12 6 3,
 * triplet x 2/3, dotted x 3/2 (none for 1/32). */
uint32_t arp_rate_ticks(uint32_t a0);

/* Playing: the ticks a note of the gate in settings byte a1 (sixths - 1) sounds at the rate in a0: k sixths of the
 * step, rounded, at least 1 and less than the step; 0 for legato (6/6). */
uint32_t arp_gate_ticks(uint32_t a0, uint32_t a1);

/* Stopped: the same fraction of the step in ms at `bpm` (> 0), at least 1; 0 for legato. */
uint32_t arp_gate_ms(uint32_t a0, uint32_t a1, uint32_t bpm);

/* The list index the pattern plays at step `pos` over `n` notes (n >= 1): bits 0-7 of `n_last` = n, bits 8-15 = the
 * last index played (random avoids repeating it). Random advances *rng (16-bit Galois LFSR, taps 0xB400). Not for the
 * chord pattern. */
uint32_t arp_index(uint32_t pattern, uint32_t pos, uint32_t n_last, uint16_t *rng);
