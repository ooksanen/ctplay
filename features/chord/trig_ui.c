/* Trig conditions (PL20): the user's control. Row 4 of stock's probability view (Shift + Pattern Settings) is the pass
 * grid, Shift + row 4 the eight special conditions; the LEDs come from chord_on_leds (trig_draw). Plan
 * 2026-11-07-trig-conditions.md, Task 6; evidence docs/investigations/2026-11-01-trig-conditions-spike/C-controls.md
 * (Q1 the view and stock's accept rule, Q2 the releases) and 2026-11-07-trig-conditions-spike.md Q4 (the edited step).
 *
 * The press (hooks prob_view_note / prob_view_drum, the view's pad handler, pads 8-15 = row 4) only latches: the pad,
 * the view, the step stock's row 3 would edit, Shift, trig_ms. Nothing is written on a press (the phantom-press rule,
 * CLAUDE.md). The release (hook cont_release, the container's pad release: also reached by stock's release-all when
 * the view changes, while the probability view is still set) applies the gesture: Shift, a hold of TRIG_HOLD_MS or a
 * tap. Every release of the latched pad clears the latch, written or not. UI task only.
 *
 * FILL (Task 7; C-controls.md Q2-Q4): the drum expanded view's pads 21-24 (20-23 here) = FILL for drums 1-4, through
 * the view's own press and release (hooks wide_drum_press / wide_drum_release: stock ignores pads < 28 there, and the
 * release comes exactly once per press, at a view change while the view is still set). A CTPlay page open over the
 * view takes the pads first (page_on_pad), so these never see them. The press only sets the drum's hold bit and its
 * time; the release clears the bit, and a tap (< TRIG_HOLD_MS) while playing arms the drum's next whole pass or, armed,
 * disarms it (trig_fill_arm[d]: odd = armed; Main fills one pass per arm value, trig.c). Stop disarms (trig_fill_stop).
 * The LEDs (trig_draw): bright orange on, yellow armed, dim orange otherwise. */
#include "slim.h"
#include "stock.h"
#include "chord_held.h"
#include "trig_math.h"

#define CTRL_ACTIVE    0x6Cu        /* [ctrl + 0x6C]: the active view */
#define CONTAINER      0x20040DB8u  /* stock.h `track_container` */
#define CONT_MODE      0x18Cu       /* [cont + 0x18C]: the views' mode, 5 = probability */
#define CONT_PADS      0x190u       /* [cont + 0x190]: bit per pad the container holds (its release tests it) */
#define CONT_NOTE_PROB 0x68u        /* [cont + 0x68 + 4 t]: note track t's probability view (class 0x0805ACD4) */
#define CONT_DRUM_PROB 0xE0u        /* [cont + 0xE0 + 4 d]: drum d's (class 0x0805AB14) */
#define MODE_PROB      5u
#define VIEW_EDIT      0x0Cu        /* [view + 0xC] = the track's editor + 0x18 (both classes) */
#define VIEW_PLAY      0x10u        /* [view + 0x10] p0: the play store, 0 = stopped */
#define VIEW_FOLLOW    0x14u        /* [view + 0x14] p0: 0x20039DE0, set = the editors do not follow the playhead */
#define EDIT_DELTA     0x18u
#define ED_STORE       0x20u        /* note editor + 0x20: its edit store, word 0 = the selected step's bytes 0-3;
                                     * drum editor + 0x20: its position store, p1 = the selected step */
#define ED_POS         0x24u        /* note editor + 0x24: its position store, p0 & 7 = pattern, p1 = step */
#define ED_HELD_NOTE   0x28u        /* note editor + 0x28 p0: a step pad held; drum editor + 0x24 */
#define ED_HELD_DRUM   0x24u
#define DRUM_RECS      0x2003C184u  /* [+ 4 d]: drum d's recorder; [rec + 0x14] p0 & 7 = the shown pattern */
#define REC_POS        0x14u
#define ROW4_VIEW      8u           /* the view's pads 8-15 = the controller's 24-31 */
#define ROW4_PAD       24u
#define NOTE_TRACKS    4u
#define PATTERNS_N     8u
#define STEPS          32u
#define DRUM_CODES     0x84u        /* a drum pattern's condition bytes: + 0x84 .. + 0xA7 */
#define DRUM_CODES_N   0x24u
#define MODE_WIDE      6u           /* [cont + 0x18C] on a drum track: the expanded view (one object, all four drums) */
#define FILL_PAD       20u          /* its pads 20-23 (the spec's 21-24) = FILL for drums 1-4 */
#define PLAY_STORE     0x20011034u  /* stock.h play_store: param 0 != 0 while playing */

/* The latched press (UI only). */
typedef struct {
    uint32_t ms;                    /* trig_ms at the press */
    uint8_t *view;                  /* the probability view that took it */
    uint8_t on, pad, track, pattern, step, shift;
} trig_latch_t;
static trig_latch_t latch SLIM_ITCM(trig_latch);
uint8_t trig_fill_arm[TRIG_DRUMS] SLIM_ITCM(trig_fill_arm);        /* UI: drum d's taps, odd = armed */
static uint32_t fill_ms[TRIG_DRUMS] SLIM_ITCM(trig_fill_ms);       /* UI: trig_ms at each FILL pad's press */

void trig_ui_init(void)
{
    memset(&latch, 0, sizeof latch);
    memset(trig_fill_arm, 0, sizeof trig_fill_arm);
    memset(fill_ms, 0, sizeof fill_ms);
}

static uint8_t *editor_of(const uint8_t *view)
{
    return *(uint8_t *const *)(view + VIEW_EDIT) - EDIT_DELTA;
}

/* Track t's probability view (whether shown or not); 0 for t >= 8. */
static uint8_t *prob_view(const uint8_t *cont, uint32_t t)
{
    if (t < NOTE_TRACKS)
        return *(uint8_t *const *)(cont + CONT_NOTE_PROB + 4u * t);
    if (t < TRIG_TRACKS)
        return *(uint8_t *const *)(cont + CONT_DRUM_PROB + 4u * (t - NOTE_TRACKS));
    return 0;
}

/* The probability view shown at the bottom (mode 5), with its track in *t; 0 when none. */
static uint8_t *shown_prob(uint32_t *t)
{
    const uint8_t *cont = (const uint8_t *)CONTAINER;
    *t = cont[CONT_MODE] == MODE_PROB ? track_of((void *)cont) : TRIG_TRACKS;
    return prob_view(cont, *t);
}

/* The step stock's row 3 edits (Q4): notes the editor's position store; drums the recorder's shown pattern and the
 * editor's selected step. */
static void edited_step(const uint8_t *view, uint32_t t, uint32_t *p, uint32_t *s)
{
    if (t < NOTE_TRACKS) {
        void *pos = *(void *const *)(editor_of(view) + ED_POS);
        *p = *param_get(pos, 0) & 7u;
        *s = *param_get(pos, 1);
        return;
    }
    const uint8_t *rec = *(const uint8_t *const *)(DRUM_RECS + 4u * (t - NOTE_TRACKS));
    *p = *param_get(*(void *const *)(rec + REC_POS), 0) & 7u;
    *s = *param_get(*(void *const *)(editor_of(view) + ED_STORE), 1);
}

/* Stock's row-3 accept rule, as stock tests it (0x0804D0C6, 0x0804F270): a step pad held, or stopped, or the editors
 * not following the playhead. */
static int accepted(const uint8_t *view, uint32_t t)
{
    const uint8_t *ed = editor_of(view);
    if (*param_get(*(void *const *)(ed + (t < NOTE_TRACKS ? ED_HELD_NOTE : ED_HELD_DRUM)), 0))
        return 1;
    if (!*param_get(*(void *const *)(view + VIEW_PLAY), 0))
        return 1;
    return *param_get(*(void *const *)(view + VIEW_FOLLOW), 0) != 0u;
}

/* A row-4 press in a probability view: latch it when stock would accept a row-3 press there (notes: with notes on the
 * step, as stock tests its edit store; drums: with a hit). Nothing written; stock returns at its bge. */
static void press(uint8_t *view, uint32_t pad)
{
    if (pad < ROW4_VIEW || pad >= ROW4_VIEW + 8u)
        return;
    uint32_t t, p, s;
    if (shown_prob(&t) != view || !accepted(view, t))
        return;
    if (t < NOTE_TRACKS && !*param_get(*(void *const *)(editor_of(view) + ED_STORE), 0))
        return;                                     /* no notes on the step (stock's own test) */
    edited_step(view, t, &p, &s);
    if (p >= PATTERNS_N || s >= STEPS)
        return;
    if (t >= NOTE_TRACKS && !trig_drum_pattern(t - NOTE_TRACKS, p)[s])
        return;                                     /* no hit: nothing (no hit made) */
    latch.view = view;
    latch.pad = (uint8_t)(ROW4_PAD + pad - ROW4_VIEW);
    latch.track = (uint8_t)t;
    latch.pattern = (uint8_t)p;
    latch.step = (uint8_t)s;
    latch.shift = (uint8_t)chord_shift_held();
    latch.ms = trig_ms;
    latch.on = 1;
}

int trig_on_note_view_pad(void *view, uint32_t pad, uint32_t *ret)
{
    (void)ret;
    press(view, pad);
    return SLIM_PASS;
}

int trig_on_drum_view_pad(void *view, uint32_t pad, uint32_t *ret)
{
    (void)ret;
    press(view, pad);
    return SLIM_PASS;
}

/* The first condition written in a project (trig_mark != 1): every condition byte to 0 (drum patterns' + 0x84 ..
 * + 0xA7, note steps' [2]-[3], raw), then each note editor's store: its word 0 = the pattern's [0], [1] at its
 * position, 0, 0, committed (Q4: a stale store's commit would put its old [0] / [1] back; no other byte changes); then
 * the mark. UI task, on a release. */
void trig_mark_project(void)
{
    for (uint32_t d = 0; d < TRIG_TRACKS - NOTE_TRACKS; d++)
        for (uint32_t p = 0; p < PATTERNS_N; p++)
            memset(trig_drum_pattern(d, p) + DRUM_CODES, 0, DRUM_CODES_N);
    for (uint32_t t = 0; t < NOTE_TRACKS; t++)
        for (uint32_t p = 0; p < PATTERNS_N; p++)
            for (uint32_t s = 0; s < STEPS; s++)
                trig_note_set(trig_note_step(t, p, s), 0);
    const uint8_t *cont = (const uint8_t *)CONTAINER;
    for (uint32_t t = 0; t < NOTE_TRACKS; t++) {
        const uint8_t *view = prob_view(cont, t);
        uint32_t p, s;
        edited_step(view, t, &p, &s);
        if (p >= PATTERNS_N || s >= STEPS)
            continue;
        const uint8_t *step = trig_note_step(t, p, s);
        void *store = *(void *const *)(editor_of(view) + ED_STORE);
        volatile uint8_t *w = param_wptr(store, 0);
        w[0] = step[0];
        w[1] = step[1];
        w[2] = 0;
        w[3] = 0;
        store_commit(store);
    }
    trig_mark = 1;
}

/* Write the latched step's new code. Notes: through the editor's store while its position is still the latched step
 * (word 0 whole: the pattern step's [0], [1] and the code), else raw (the selection moved: Q4). Drums: raw. */
static void write(uint32_t code)
{
    uint32_t t = latch.track, p = latch.pattern, s = latch.step;
    if (t >= NOTE_TRACKS) {
        trig_drum_set(trig_drum_pattern(t - NOTE_TRACKS, p), s, code);
        return;
    }
    uint8_t *step = trig_note_step(t, p, s);
    uint32_t ep, es;
    edited_step(latch.view, t, &ep, &es);
    if (ep != p || es != s) {
        trig_note_set(step, code);
        return;
    }
    void *store = *(void *const *)(editor_of(latch.view) + ED_STORE);
    volatile uint8_t *w = param_wptr(store, 0);
    w[0] = step[0];
    w[1] = step[1];
    w[2] = (uint8_t)code;
    w[3] = (uint8_t)((code >> 8) & 1u);
    store_commit(store);
}

/* cont_release (UI): the container's pad release, before its own bit test. The latched pad's release applies the
 * gesture while the container still holds the pad and the probability view that took the press is shown. */
int trig_on_cont_release(void *cont, uint32_t pad, uint32_t *ret)
{
    (void)ret;
    if (!latch.on || pad != latch.pad)
        return SLIM_PASS;
    latch.on = 0;
    const uint8_t *c = cont;
    if (!((*(const uint32_t *)(c + CONT_PADS) >> pad) & 1u) || c[CONT_MODE] != MODE_PROB
        || prob_view(c, track_of(cont)) != latch.view)
        return SLIM_PASS;
    uint32_t gesture = latch.shift ? TRIG_SHIFT : trig_ms - latch.ms >= TRIG_HOLD_MS ? TRIG_HOLD : TRIG_TAP;
    uint32_t drum = latch.track >= NOTE_TRACKS;
    uint32_t old = trig_code_at(latch.track, latch.pattern, latch.step);
    uint32_t code = trig_edit(old, latch.pad - ROW4_PAD, gesture, drum);
    if (code == old)
        return SLIM_PASS;
    if (trig_mark != 1u)
        trig_mark_project();
    write(code);
    return SLIM_PASS;
}

/* ---- FILL -------------------------------------------------------------------------------------------------------- */

static uint32_t playing(void)
{
    return *param_get((void *)PLAY_STORE, 0) != 0u;
}

/* Drum d's FILL is armed: an odd arm value whose pass Main has not finished. */
static uint32_t fill_armed(uint32_t d)
{
    uint32_t arm = trig_fill_arm[d];
    return (arm & 1u) && arm != trig_fill_done[d];
}

/* The drum expanded view is the container's view (mode 6 on a drum track). */
static uint32_t wide_shown(void)
{
    const uint8_t *cont = (const uint8_t *)CONTAINER;
    uint32_t t = cont[CONT_MODE] == MODE_WIDE ? track_of((void *)cont) : 0u;
    return t >= NOTE_TRACKS && t < TRIG_TRACKS;
}

/* wide_drum_press (UI): a FILL pad's press: its drum's hold bit and the time only. Stock returns at the blt. */
int trig_on_wide_press(void *view, uint32_t pad, uint32_t vel, uint32_t *ret)
{
    (void)view;
    (void)vel;
    (void)ret;
    uint32_t d = pad - FILL_PAD;
    if (d >= TRIG_DRUMS || !wide_shown())
        return SLIM_PASS;
    fill_ms[d] = trig_ms;
    trig_fill_hold = (uint8_t)(trig_fill_hold | 1u << d);
    return SLIM_PASS;
}

/* wide_drum_release (UI, once per press): the hold ends; a tap while playing arms the drum's next whole pass, or
 * disarms it while armed (its pass running or not). A tap after a finished fill arms again (the next odd value). */
int trig_on_wide_release(void *view, uint32_t pad, uint32_t *ret)
{
    (void)view;
    (void)ret;
    uint32_t d = pad - FILL_PAD;
    if (d >= TRIG_DRUMS || !((trig_fill_hold >> d) & 1u))
        return SLIM_PASS;                           /* not a press this hook took */
    trig_fill_hold = (uint8_t)(trig_fill_hold & ~(1u << d));
    if (trig_ms - fill_ms[d] < TRIG_HOLD_MS && playing()) {
        uint32_t arm = trig_fill_arm[d];
        trig_fill_arm[d] = (uint8_t)(fill_armed(d) ? arm + 1u : (arm + 1u) | 1u);
    }
    return SLIM_PASS;
}

/* chord_on_leds (UI), every frame: with the transport stopped every armed FILL disarms (odd → even). */
void trig_fill_stop(void)
{
    if (playing())
        return;
    for (uint32_t d = 0; d < TRIG_DRUMS; d++)
        if (trig_fill_arm[d] & 1u)
            trig_fill_arm[d]++;
}

/* Pads 20-23 of the drum expanded view: bright while the drum's FILL is on (held, or its fill pass while still armed:
 * dim at once on a disarm or Stop, before Main's next step turns the pass off), yellow while armed, dim otherwise. */
static void fill_draw(uint16_t *out)
{
    for (uint32_t d = 0; d < TRIG_DRUMS; d++) {
        uint32_t on = ((trig_fill_hold >> d) & 1u) || (((trig_fill_pass >> d) & 1u) && fill_armed(d));
        out[FILL_PAD + d] = (uint16_t)(on ? COL_ORANGE : fill_armed(d) ? COL_YELLOW : COL_ORANGE_DIM);
    }
}

/* chord_on_leds (UI), after page_draw drew nothing: the drum expanded view → its FILL pads; a probability view shown at
 * the bottom → row 4 = the condition of the step stock shows (its row 3's), the Shift layer while Shift is held; while
 * a latched plain press has been held TRIG_HOLD_MS, the row its hold will write. */
void trig_draw(void *ctrl, uint16_t *out)
{
    uint32_t t, p, s;
    if (*(void **)((uint8_t *)ctrl + CTRL_ACTIVE) != (void *)CONTAINER)
        return;
    if (wide_shown()) {
        fill_draw(out);
        return;
    }
    uint8_t *view = shown_prob(&t);
    if (!view)
        return;
    uint32_t drum = t >= NOTE_TRACKS, shift = (uint32_t)chord_shift_held(), code;
    if (latch.on && latch.view == view && !latch.shift && trig_ms - latch.ms >= TRIG_HOLD_MS) {
        code = trig_edit(trig_code_at(t, latch.pattern, latch.step), latch.pad - ROW4_PAD, TRIG_HOLD, drum);
        shift = 0;
    } else {
        edited_step(view, t, &p, &s);
        code = trig_code_at(t, p, s);
    }
    trig_row4(code, shift, drum, out + ROW4_PAD);
}
