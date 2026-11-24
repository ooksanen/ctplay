/* The chord feature's side of the CTCtrl link (PL12, spec docs/specs/2026-10-18-ctctrl-link-design.md "Applying
 * a write"): did a phone write make a value the pads never make, and the pads' side effects once it is in the globals.
 * Only what the write changed is checked: a project load may have left values the pads never make (saved_fix keeps
 * whatever it does not refuse), and those must not block other writes. Built in every version with chord (its sources
 * are fixed); the body only where the link is. UI task. */
#include "slim.h"
#include "stock.h"
#include "chord_math.h"
#include "chord_held.h"
#include "slim_link.h"

#if SLIM_LINK_N

/* The per-track bitmask bytes hold bits 0-3 only. */
static uint32_t mask_ok(const uint8_t *cand, const uint8_t *old, uint32_t off)
{
    return cand[off] == old[off] || !(cand[off] & ~0xFu);
}

int chord_link_valid(const uint8_t *cand, const uint8_t *old)
{
    if (!mask_ok(cand, old, SLIM_OFF_chord_rootless) || !mask_ok(cand, old, SLIM_OFF_chord_strum_down)
        || !mask_ok(cand, old, SLIM_OFF_chord_mono) || !mask_ok(cand, old, SLIM_OFF_chord_step))
        return 0;
    if (cand[SLIM_OFF_chord_pstrum] != old[SLIM_OFF_chord_pstrum]) {   /* PL19: 2 bits a track, 3 = nothing */
        for (uint32_t t = 0; t < TRACKS; t++)
            if (((cand[SLIM_OFF_chord_pstrum] >> (2u * t)) & 3u) == 3u)
                return 0;
    }
    const uint8_t *s = cand + SLIM_OFF_chord_settings, *s0 = old + SLIM_OFF_chord_settings;
    const uint8_t *a = cand + SLIM_OFF_chord_arp, *a0 = old + SLIM_OFF_chord_arp;
    uint32_t rl = cand[SLIM_OFF_chord_rootless], rl0 = old[SLIM_OFF_chord_rootless];
    for (uint32_t t = 0; t < TRACKS; t++) {
        uint32_t st = s[t] != s0[t], bit = 1u << t;
        if (st && CHORD_SPREAD(s[t]) > SPREAD_WIDE)
            return 0;
        if ((st || ((rl ^ rl0) & bit)) && (rl & bit) && !CHORD_BASS(s[t]))
            return 0;                               /* the bass cycle has rootless only over a bass */
        uint32_t p = a[2u * t], q = a[2u * t + 1u];
        if (p != a0[2u * t] && (ARP_MOD(p) > MOD_DOTTED || (ARP_RATE(p) == 3u && ARP_MOD(p) == MOD_DOTTED)))
            return 0;                               /* dotted 1/32 is off the grid (page.c) */
        if (q != a0[2u * t + 1u] && ((q & ~0x1Fu) || ARP_GATE(q) > GATE_LEGATO))
            return 0;
    }
    const uint8_t *v = cand + SLIM_OFF_chord_voice, *v0 = old + SLIM_OFF_chord_voice;
    for (uint32_t t = 0; t < TRACKS; t++)
        if (v[t] != v0[t] && (VOICE_SHAPE2(v[t]) > 5u || (v[t] & ~VOICE_BITS)))
            return 0;                               /* no pad makes a row-2 shape above 5; bits 6-7 are spare */
    const uint8_t *r = cand + SLIM_OFF_repeat_cfg, *r0 = old + SLIM_OFF_repeat_cfg;
    if ((r[0] != r0[0] || r[1] != r0[1]) && (REPEAT_RATE(r[0]) > REPEAT_RATE_MAX || r[1]))
        return 0;                                   /* PL16: eight rates; byte 1 is spare */
    return euclid_link_valid(cand + SLIM_OFF_euclid_cfg, old + SLIM_OFF_euclid_cfg)
        && melody_link_valid(cand + SLIM_OFF_melody_cfg, old + SLIM_OFF_melody_cfg) && vary_link_valid(cand, old)
        && drum_link_valid(cand, old);
}

/* As page.c's pick_arp: pattern to off frees the track's arpeggio, latch off frees the latched notes; as its
 * pick_chords: a shape on one row ends the other row's, an inversion ends voice leading. */
void chord_link_apply(const uint8_t *old)
{
    const uint8_t *a = old + SLIM_OFF_chord_arp;
    for (uint32_t t = 0; t < TRACKS; t++) {
        uint32_t was = a[2u * t], now = chord_arp[t][0];
        if (ARP_PATTERN(was) != ARP_OFF && ARP_PATTERN(now) == ARP_OFF)
            arp_free(t, 0);
        if ((was & ARP_LATCH) && !(now & ARP_LATCH))
            arp_free(t, 1);
    }
    const uint8_t *s0 = old + SLIM_OFF_chord_settings, *v0 = old + SLIM_OFF_chord_voice;
    for (uint32_t t = 0; t < TRACKS; t++) {         /* a shape on one row ends the other row's (chord_pick_shape) */
        if (CHORD_SHAPE(chord_settings[t]) && CHORD_SHAPE(s0[t]) != CHORD_SHAPE(chord_settings[t]))
            chord_pick_shape(t, CHORD_SHAPE(chord_settings[t]));
        else if (VOICE_SHAPE2(chord_voice[t]) && VOICE_SHAPE2(v0[t]) != VOICE_SHAPE2(chord_voice[t]))
            chord_pick_shape(t, 7u + VOICE_SHAPE2(chord_voice[t]));
        /* As page.c's inversion pads: a new inversion ends voice leading, unless this write set voice leading too. */
        if (CHORD_INV(chord_settings[t]) != CHORD_INV(s0[t]) && VOICE_LEAD(chord_voice[t]) == VOICE_LEAD(v0[t]))
            chord_voice[t] &= (uint8_t)~(3u << 4);
    }
    if (!(repeat_cfg[0] & REPEAT_LATCH) || !REPEAT_RATE(repeat_cfg[0]))
        repeat_stop_latched();                      /* PL16: latch off or no rate frees the latched drums (as pads) */
    euclid_link_apply(old + SLIM_OFF_euclid_cfg);
    melody_link_apply(old + SLIM_OFF_melody_cfg);
    vary_link_apply(old);
    drum_link_apply(old);
}

#endif
