/* Note repeat maths: pure functions (plan 2026-10-25-drums-pl16, Global Constraints). Model: tests/repeat_model.py. */
#pragma once
#include <stdint.h>

/* Ticks (24 per quarter note) between the hits of rate 1-8: 1/4 1/8 1/16 1/32 = 24 12 6 3, then the triplets
 * 1/4T 1/8T 1/16T 1/32T = 16 8 4 2. Rate 0 (off), or out of range: 0. */
uint32_t repeat_ticks(uint32_t rate);

/* The velocity of the hit `e` ticks after the press, struck at v (1-127). shape 0 as struck, 1 fade
 * (v - 3v/4 * min(e,24)/24), 2 swell (v/4 + 3v/4 * min(e,24)/24), 3 accent (v on a beat, else 2v/3: `beat` is
 * the caller's flag). Integer maths, rounded down, at least 1. */
uint32_t repeat_vel(uint32_t shape, uint32_t v, uint32_t e, uint32_t beat);

/* 1 when `tick` is a hit. e = (uint32_t)(tick - press_tick), unsigned (wraps); e == 0 is never due (the press hit
 * stands in for it); `ticks` == 0 (rate off) is never due. Playing: tick % ticks == 0 and 2e >= ticks (a grid point
 * less than ticks / 2 after the press is skipped). Stopped: e % ticks == 0. */
uint32_t repeat_due(uint32_t tick, uint32_t press_tick, uint32_t ticks, uint32_t playing);
