/* countin: one bar of stock's click before recording (PL08, spec 2026-10-17-small-features-design.md section 1, D1-D3;
 * as upstream's SC41.8 / SC42.3, tools/countin.py).
 *
 * Shift + Clear steps four states: 0 off, 1 click, 2 count-in, 3 both. The click is stock's metronome: set through
 * stock's setter and read from its parameter every time, so it follows a change made elsewhere and saves as stock saves
 * it. The count-in bit (ci_on) is saved with the project from PL10 (features/saved).
 *
 * The count: with the count-in on, Record armed and the transport stopped, Play is taken and the count starts. The Main
 * task's 1 ms service counts the bar and sends stock's click at the press and on each beat (60000 / BPM ms), from the
 * task stock's clock sends it from. At the bar's end it marks the count done; the next LED frame (UI task) presses Play
 * through the controller with ci_pass set, so that press goes to stock. Play during the count cancels it; so do Record
 * disarmed and a transport started otherwise (the Main task stops clicking at once, the next LED frame cancels).
 *
 * Tasks: the UI task writes ci_on, ci_pass, ci_count (1 last, behind a barrier, after zeroing the rest) and cancels
 * (ci_count, ci_done = 0); the Main task writes ci_ms, ci_beat and sets ci_done. */
#include "slim.h"
#include "stock.h"
#include "slim_link.h"

#define BTN_PLAY         17u
#define BTN_CLEAR        23u
#define LED_REC          48u
#define LED_CLEAR        55u
#define COL_REC          0x53u      /* stock's Record red */
#define BEATS            4u
#define CLICK_GROUP      0xFFu      /* synth_note_on(0xFF, 0, 0x60): stock's click */
#define CLICK_VEL        0x60u
#define METRO_ID         0x64u
#define METRO_PARAM      3u
#define METRO_STORE      0x38u      /* metro_obj + 0x38: -> the store holding the metronome */
#define METRO_OBJ        0x200109D8u   /* stock.h metro_obj (fixed addresses: the header declares them one byte long) */
#define CONTROLLER       0x20040B10u   /* stock.h controller */
#define TEMPO_STORE      0x20011404u   /* stock.h tempo_store: param 0 BPM */
#define PLAY_STORE       0x20011034u   /* stock.h play_store: param 0 playing, 1 Record armed */
#define CTRL_SHIFT_STORE 0x0Cu

static const uint8_t COL_STATE[4] = {0x53u, 0x17u, 0x32u, 0x4Du};   /* red, green, magenta, cyan (upstream SC42.3) */

uint8_t ci_on;                      /* the count-in bit (state bit 1) */
static volatile uint8_t ci_count;   /* UI task: 1 while counting */
static volatile uint8_t ci_done;    /* Main task: the bar is over */
static volatile uint8_t ci_beat;    /* Main task: clicks sent */
static volatile uint8_t ci_pass;    /* UI task: our own Play press, to stock */
static volatile uint16_t ci_ms;     /* Main task: heartbeats since the press */

void ci_init(void)
{
    ci_on = 0;
    ci_count = 0;
    ci_done = 0;
    ci_beat = 0;
    ci_pass = 0;
    ci_ms = 0;
}

static uint32_t p(uint32_t store, uint32_t i)
{
    return *param_get((void *)store, i);
}

static int shift_held(void)
{
    return *param_get(*(void **)(CONTROLLER + CTRL_SHIFT_STORE), 0u) != 0u;
}

static uint32_t state(void)
{
    uint32_t click = *param_get(*(void **)(METRO_OBJ + METRO_STORE), METRO_PARAM) != 0u;
    return click | (uint32_t)ci_on << 1;
}

static int stopped_and_armed(void)
{
    return !p(PLAY_STORE, 0u) && p(PLAY_STORE, 1u);
}

static uint32_t beat_ms(void)
{
    uint32_t bpm = p(TEMPO_STORE, 0u);
    return 60000u / (bpm >= 30u ? bpm : 120u);
}

static void cancel(void)
{
    ci_count = 0;
    ci_done = 0;
}

/* After a project load wrote ci_on (features/saved, UI task): out of range = off; a count in progress is cancelled. */
void ci_saved_fix(void)
{
    if (ci_on > 1u)
        ci_on = 0;
    cancel();
}

#if SLIM_LINK_N
/* CTCtrl link (features/link): a written count-in bit is 0 or 1. */
int ci_link_valid(const uint8_t *cand, const uint8_t *old)
{
    return cand[SLIM_OFF_ci_on] == old[SLIM_OFF_ci_on] || cand[SLIM_OFF_ci_on] <= 1u;
}
#endif

/* button_press (UI task), before the chord feature's. */
int ci_on_button(void *ctrl, uint32_t id, uint32_t *ret)
{
    (void)ctrl;
    (void)ret;
    if (ci_pass)
        return SLIM_PASS;                           /* our own Play press */
    if (id == BTN_CLEAR && shift_held()) {
        uint32_t next = (state() + 1u) & 3u;
        ci_on = (uint8_t)(next >> 1);
        metro_set((void *)METRO_OBJ, METRO_ID, next & 1u);
        return SLIM_HANDLED;                        /* stock's own toggle would undo the click bit */
    }
    if (id != BTN_PLAY)
        return SLIM_PASS;
    if (ci_count) {
        cancel();                                   /* Play during the count: nothing starts */
        return SLIM_HANDLED;
    }
    if (!ci_on || shift_held() || !stopped_and_armed())
        return SLIM_PASS;
    ci_ms = 0;
    ci_beat = 0;
    ci_done = 0;
    uint32_t primask = slim_irq_save();             /* the Main task sees the count only now, zeroed */
    ci_count = 1;
    slim_irq_restore(primask);
    return SLIM_HANDLED;
}

/* main_ms slot 0 (Main task, every ms): the bar's clicks, then its end. */
int ci_on_ms(uint32_t slot, uint32_t *ret)
{
    (void)ret;
    if (slot != 0u || !ci_count || ci_done || !stopped_and_armed())
        return SLIM_PASS;                           /* cancelled or overtaken: the next LED frame tidies up */
    uint32_t b = beat_ms(), ms = ci_ms;
    if (ms >= BEATS * b) {
        ci_done = 1;                                /* the downbeat: the next LED frame presses Play */
        return SLIM_PASS;
    }
    if (ci_beat < BEATS && ms >= ci_beat * b) {
        ci_beat = (uint8_t)(ci_beat + 1u);
        synth_note_on(CLICK_GROUP, 0u, CLICK_VEL);
    }
    ci_ms = (uint16_t)(ms + 1u);
    return SLIM_PASS;
}

/* led_task (UI task): the count's end (Play), the Record LED while counting, Clear with Shift = the state. */
void ci_on_leds(void *ctrl, uint16_t *out)
{
    if (ci_count) {
        if (!stopped_and_armed()) {
            cancel();                               /* Record disarmed, or the transport started otherwise */
        } else if (ci_done) {
            cancel();
            ci_pass = 1;
            ctrl_press(ctrl, BTN_PLAY);
            ctrl_release(ctrl, BTN_PLAY);
            ci_pass = 0;
        } else {
            uint32_t b = beat_ms(), ms = ci_ms ? ci_ms - 1u : 0u;   /* since the first click */
            out[LED_REC] = (uint16_t)(ms % b < b / 2u ? COL_REC : 0u);
        }
    }
    if (shift_held())
        out[LED_CLEAR] = COL_STATE[state()];
}
