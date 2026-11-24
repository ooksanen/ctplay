/* Trig conditions (PL20): conditions stay with their steps through stock's own edits. Plan
 * 2026-11-07-trig-conditions.md, Task 8; evidence docs/investigations/2026-11-01-trig-conditions-spike/A-storage.md
 * (Q1, Q2: what stock does to the bytes) and 2026-11-07-trig-conditions-spike.md (Q1: each hook's arguments, Q2:
 * Mutate's site).
 *
 * A drum's conditions are its pattern's settings bytes + 0x84 .. + 0xA7 (code byte + 0x88 + s, bit 8 in + 0x84 ..
 * + 0x87), which stock copies only in Duplicate's whole-pattern memcpy and otherwise never clears or moves: so Duplicate,
 * Clear step, Clear pattern, copy 1-16 -> 17-32, paste step and Mutate get a hook each. A note step's [2] / [3] travel
 * with stock's copies and moves already; only stock's empty-step fill (Clear step, Clear pattern) must zero them.
 * Task 9: a drum step's condition goes with its hit (a step pad tapped off, a step held + the lower pad of its flip
 * sample, the micro-step view's last micro bit off: 2026-11-07 spike Q5), so a hit added later never inherits it.
 *
 * Every handler acts only in a marked project (trig_mark == 1; unmarked, it returns before reading anything) and runs
 * in the UI task inside stock's own press-time handler, which writes the pattern itself: a few dozen raw byte stores,
 * unmasked, nothing slow (stock's parameter getter at most). */
#include "slim.h"
#include "stock.h"
#include "chord_held.h"
#include "trig_math.h"

#define PATTERNS_N    8u
#define STEPS         32u
#define HALF          16u
#define DRUM_PATTERN  0x6A8u        /* a drum pattern: velocity [32] at + 0, ...; the conditions at + 0x84 .. + 0xA7 */
#define CODES         0x84u
#define CODES_N       0x24u
#define CODE_BITS     0x84u         /* + 0x84 .. + 0x87: bit 8 of step s's code = bit s & 7 of byte s >> 3 */
#define CODE_LOW      0x88u         /* + 0x88 + s: bits 0-7 of step s's code */
#define ED_PATTERNS   0x04u         /* drum editor + 4: its 8 patterns */
#define ED_POS        0x20u         /* drum editor + 0x20: its position store, p0 = the shown pattern, p1 = the step */
#define ED_COPY       0x54u         /* drum editor + 0x54: the shared copy record (byte 1 = source track, 3 = step) */
#define COPY_TRACK    1u            /* the copy record's byte 1 = the source track, 4 + d */
#define COPY_STEP     3u
#define DRUM_TRACK0   4u
#define DRUMS_N       4u
#define LANES         0xA8u         /* paste's stack argument 6 = the source pattern + 0xA8 */
#define ENTRY_SP      32u           /* an entry stub's slim_args_t + 32 = the caller's sp (checks.ENTRY_STUB_STACK) */
#define PASTE_SRC     4u            /* [caller's sp + 4] = paste's stack argument 6 */
#define DRUM_EDITORS  0x20039D04u   /* [+ 4 d]: drum d's editor ([0x20039C5C + 0xA8 + 4 d], symbols.toml drum_duplicate) */
#define ED_STORE      0x18u         /* drum editor + 0x18: its step store */
#define VIEW_STORE    0x0Cu         /* the drum step view + 0x0C, the micro-step view + 0x0C: the drum's step store */
#define LISTENER_STORE 0x08u        /* the drum's flip listener + 0x08: its step store */

static int marked(void)
{
    return trig_mark == 1u;
}

/* Drum editor `editor`'s pattern p (p < 8 checked by the callers). */
static uint8_t *pattern_of(const uint8_t *editor, uint32_t p)
{
    return *(uint8_t *const *)(editor + ED_PATTERNS) + DRUM_PATTERN * p;
}

/* The editor's position store: p0 = the shown pattern, p1 = the selected step (stock reads both as bytes). */
static uint32_t pos(const uint8_t *editor, uint32_t k)
{
    return *param_get(*(void *const *)(editor + ED_POS), k);
}

/* drum_duplicate (UI): the source's 36 bytes to the target, at the entry, in every case (Task 1 Q1: stock's own memcpy,
 * when it runs, copies the same bytes again; onto itself: no change). */
int trig_on_drum_duplicate(void *editor, const uint8_t *src, uint32_t pattern, uint32_t *ret)
{
    (void)ret;
    if (!marked() || pattern >= PATTERNS_N)
        return SLIM_PASS;
    uint8_t *dst = pattern_of(editor, pattern);
    for (uint32_t i = 0; i < CODES_N; i++)
        dst[CODES + i] = src[CODES + i];
    return SLIM_PASS;
}

/* drum_clear_step (UI): the shown pattern's selected step (the pad's) loses its condition. */
int trig_on_drum_clear_step(void *editor, uint32_t *ret)
{
    (void)ret;
    if (!marked())
        return SLIM_PASS;
    uint32_t p = pos(editor, 0), s = pos(editor, 1);
    if (p < PATTERNS_N && s < STEPS)
        trig_drum_set(pattern_of(editor, p), s, 0);
    return SLIM_PASS;
}

/* drum_clear_pattern (UI): every condition of the cleared pattern. */
int trig_on_drum_clear_pattern(void *editor, uint32_t pattern, uint32_t *ret)
{
    (void)ret;
    if (marked() && pattern < PATTERNS_N)
        memset(pattern_of(editor, pattern) + CODES, 0, CODES_N);
    return SLIM_PASS;
}

/* drum_copy_half (UI): stock copies the shown pattern's steps 0-15 to 16-31 (always that way round): their codes too. */
int trig_on_drum_copy_half(void *editor, uint32_t *ret)
{
    (void)ret;
    if (!marked())
        return SLIM_PASS;
    uint32_t p = pos(editor, 0);
    if (p >= PATTERNS_N)
        return SLIM_PASS;
    uint8_t *pat = pattern_of(editor, p);
    for (uint32_t s = 0; s < HALF; s++)
        pat[CODE_LOW + HALF + s] = pat[CODE_LOW + s];
    pat[CODE_BITS + 2] = pat[CODE_BITS];        /* bit 8 of steps 16-23, 24-31 = of 0-7, 8-15 */
    pat[CODE_BITS + 3] = pat[CODE_BITS + 1];
    return SLIM_PASS;
}

/* drum_paste_step (UI): the target ([editor + 0x20] p0 / p1) gets the source step's code, 0 for an empty source (a
 * removal). The source is read as stock reads it: its pattern from the caller's stack argument 6 (any drum's: the
 * caller found it, so no track is indexed here), its step from the copy record's byte 3. Code 0 too unless the record's
 * track (byte 1) is a drum, 4-7: stock's caller indexes it unchecked (0x0802E12C-0x0802E13E) and only the drum copy
 * writes it (0x0802E11C-0x0802E11E: drum index + 4), so a note track there would make the source note bytes. No route
 * of presses reaches that; the bound keeps a code from being read out of anything but a drum pattern. */
int trig_on_drum_paste_step(void *editor, uint32_t vel, uint32_t flip, uint32_t micro, uint32_t *ret)
{
    (void)flip;
    (void)micro;
    if (!marked())
        return SLIM_PASS;
    uint32_t p = pos(editor, 0), s = pos(editor, 1);
    if (p >= PATTERNS_N || s >= STEPS)
        return SLIM_PASS;
    const uint8_t *sp = (const uint8_t *)ret - offsetof(slim_args_t, ret) + ENTRY_SP;
    const uint8_t *src = *(const uint8_t *const *)(sp + PASTE_SRC) - LANES;
    const uint8_t *copy = *(const uint8_t *const *)((const uint8_t *)editor + ED_COPY);
    uint32_t from = copy[COPY_STEP], drum = copy[COPY_TRACK] - DRUM_TRACK0;
    uint32_t code = vel && from < STEPS && drum < DRUMS_N ? trig_drum_get(src, from) : 0u;
    trig_drum_set(pattern_of(editor, p), s, code);
    return SLIM_PASS;
}

/* drum_mutate (UI, a mid hook, once per swap): r4 / r3 = the two steps, r1 = the pattern: their codes swap too. */
void trig_on_drum_mutate(slim_regs_t *regs)
{
    uint32_t a = regs->r[4], b = regs->r[3];
    if (!marked() || a >= STEPS || b >= STEPS)
        return;
    uint8_t *pat = (uint8_t *)regs->r[1];
    uint32_t ca = trig_drum_get(pat, a);
    trig_drum_set(pat, a, trig_drum_get(pat, b));
    trig_drum_set(pat, b, ca);
}

/* note_step_fill (UI): stock empties a note step (Clear step: the edit store's write buffer; Clear pattern: each step):
 * its condition too. */
int trig_on_note_step_fill(void *editor, uint8_t *step, uint32_t *ret)
{
    (void)editor;
    (void)ret;
    if (marked())
        trig_note_set(step, 0);
    return SLIM_PASS;
}

/* The drum whose editor's step store is `store` (stock removes step s's hit through it): step s of its shown pattern
 * loses its condition. A few raw stores, inside stock's own handler (the callers check the mark first). */
static void hit_gone(const void *store, uint32_t s)
{
    if (s >= STEPS)
        return;
    for (uint32_t d = 0; d < DRUMS; d++) {
        const uint8_t *ed = *(const uint8_t *const volatile *)(DRUM_EDITORS + 4u * d);
        if (ed && *(const void *const *)(ed + ED_STORE) == store) {
            uint32_t p = pos(ed, 0);
            if (p < PATTERNS_N)
                trig_drum_set(pattern_of(ed, p), s, 0);
            return;
        }
    }
}

/* drum_step_off (UI): the drum step view's toggle takes step `step`'s hit off (a step pad's release). */
int trig_on_drum_step_off(void *view, uint32_t step, uint32_t *ret)
{
    (void)ret;
    if (marked())
        hit_gone(*(void *const *)((const uint8_t *)view + VIEW_STORE), step);
    return SLIM_PASS;
}

/* drum_remove (UI): a step held + the lower pad of its flip sample removes the hit (r0 = the drum's flip listener). */
int trig_on_drum_remove(void *listener, uint32_t step, uint32_t *ret)
{
    (void)ret;
    if (marked())
        hit_gone(*(void *const *)((const uint8_t *)listener + LISTENER_STORE), step);
    return SLIM_PASS;
}

/* drum_micro_off (UI, a mid hook on the path where the micro-step view's press turned off the step's last micro bit;
 * stock then clears its velocity): r7 = the view, sl = the step. */
void trig_on_drum_micro_off(slim_regs_t *regs)
{
    if (marked())
        hit_gone(*(void *const *)((const uint8_t *)regs->r[7] + VIEW_STORE), regs->r[10]);
}
