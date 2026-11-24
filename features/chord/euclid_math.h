/* The Euclidean rhythm (spec docs/specs/2026-10-17-euclidean-design.md, "The rhythm"): pure, no stock calls. */
#pragma once
#include <stdint.h>

/* Bit i = a hit on step i (0 <= i < n), n 1-32: ((i + r) * k) mod n < k (the Bresenham form, Bjorklund's rhythms up to
 * rotation); r is used mod n; k >= n fills every step, k = 0 none. */
uint32_t euclid_mask(uint32_t k, uint32_t n, uint32_t r);
