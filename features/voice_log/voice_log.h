/* voice_log: the record layout, shared by the hooks and the SysEx replies (spec 2026-10-13-voice-log-design.md). */
#pragma once
#include <stdint.h>

#define VL_CAP      12u
#define VL_VERSION  1u

typedef struct {
    uint16_t t;           /* milliseconds, the main_ms counter (wraps after 65 s) */
    uint8_t seq;          /* decisions so far, mod 256 */
    uint8_t flags;        /* bit 0 synth, bit 1 DSP path, bits 2-4 polyphony mode (ARM path only) */
    uint8_t note;
    uint8_t voice;        /* as stock left it in voice_state[5] */
    uint16_t before;      /* the synth's voices before, 2 bits each: 0 free (high half 0), 1 released, 2 held; 0xFFFF = none */
    uint16_t headroom;    /* the X:$36 + synth reading >> 4, saturated (stock's threshold 0x14000 = 0x1400) */
} vl_rec_t;

_Static_assert(sizeof(vl_rec_t) == 10, "the page and the tests read 10-byte records");

extern vl_rec_t vl_ring[VL_CAP];
extern uint8_t vl_head, vl_stored, vl_seq;
extern uint16_t vl_now;
