/* Pattern strum maths (PL19): pure functions, no stock calls (spec 2026-10-28-playback-strum-design.md). Model:
 * tests/roll_model.py. */
#pragma once
#include <stdint.h>

/* Written: ticks (24 per quarter note) between the notes of a rolled chord, by the strum speed 0-3 (off, slow,
 * medium, fast). */
extern const uint8_t WRITTEN_GAP[4];

/* `ticks` after a roll's first note as sixths of a step of `step_ticks` ticks, rounded; 0 when step_ticks is 0. */
uint32_t roll_sixths(uint32_t ticks, uint32_t step_ticks);

/* `step` + `add` steps, wrapping within first..last (a step past `last` continues from `first`); from a step outside
 * first..last straight on, and a result >= 32 is the callers' to drop (beta 2). */
uint32_t roll_step(uint32_t step, uint32_t add, uint32_t first, uint32_t last);

/* Sorts n notes by pitch: rising (lowest first), or falling (highest first) when `falling` is not 0. */
void roll_order(uint8_t *notes, uint32_t n, uint32_t falling);
