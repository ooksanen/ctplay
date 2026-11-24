/* repeat: note repeat on the drums' Repeat page (spec docs/specs/2026-10-25-drums-design.md, "The Repeat page",
 * "How repeat plays", "The rules it keeps"). One setting for the kit, repeat_cfg (chord_held.h): the page shows the
 * same whichever drum opened it.
 *
 * The UI task (the page's pads, page.c) only sets flags, each change a few masked instructions: rep_vel[d], then
 * rep_held and rep_new (latch off, or no rate lit) or rep_latched (latch on and a rate lit: a tap toggles). Another
 * task may clear them with a single store (a project load, the CTCtrl link). The Main task sends every hit: the heartbeat (repeat_on_ms, from arp_on_ms)
 * takes the new presses and sends their first hit, and the arpeggiator's clock (repeat_on_tick, from arp_on_tick: the
 * sequencer's tick while playing, else the stopped 1 ms clock) marks the grid's hits, which the sequencer's tick leaves
 * for the next heartbeat as the arpeggiator does, so the recorder counts the tick first. Each hit goes through the
 * expanded drum view's live sink, as a finger on its pads 29-32 does, so stock sounds and records it as played. Main
 * alone writes rep_snd, rep_run, rep_press_tick, rep_hit_tick, rep_strike, rep_due_hits, rep_last and rep_playing. A drum is ended from
 * what is sounding (rep_snd), never recomputed: nothing can stick.
 *
 * Unquantized repeats (REPEAT_UNQUANT): while a drum repeats or sounds, the four drum recorders' record quantise is held
 * off (unquant, the heartbeat), so the hits keep their ticks whatever Shift + Record says; the user sees nothing (stock's
 * setting and the Record LED are never touched). Stock's byte [rec + 0x35] is a cache it refreshes at each step's tick
 * 0 (the mid hook rec_quant, repeat_on_quant): there the override keeps it 0 and keeps stock's value in rq_shadow, which
 * goes back into the byte when the override ends. */
#include "slim.h"
#include "stock.h"
#include "chord_held.h"
#include "repeat_math.h"

#define RP_SHAPE      8u            /* pads 0-7 the rates 1-8 (0-3 straight, 4-7 triplet), 8-11 the velocity shape */
#define RP_UNQUANT    14u
#define RP_LATCH      15u
#define TRACK_CONTAINER 0x20040DB8u /* stock.h track_container */
#define CONT_DRUM_VIEW 0xACu        /* + 0xAC: the expanded drum view, one for all four drums */
#define DRUM_VIEW_VT  0x0805AD44u   /* stock.h drum_expanded_vt */
#define VIEW_LIVE     0x10u         /* its live sink: a finger's route */
#define SINK_VT       0x0805BF54u   /* the sink's vtable (as the Note view's) */
#define SINK_TRACK    0x0Cu
#define SINK_DRUMS    0x10u         /* the drums' sink: its track byte */
#define PLAY_STORE    0x20011034u   /* stock.h play_store: param 0 != 0 while playing */
#define BEAT          24u           /* ticks a quarter note: accent's beat */
#define GRID          48u           /* a multiple of every rate's ticks (16 and 24 among them) */
#define PLAY_BACK     24u           /* Play: a repeating drum's press goes 24 ticks before tick 0 */
#define COL_LATCHED   0x04u         /* white, pulsing: an animated code on purpose */
#define RECORDERS     0x2003C174u   /* stock.h recorders: [+ 4 (DRUM_FIRST + d)] = drum d's recorder */
#define DRUM_REC_VT   0x0805A578u   /* a drum recorder's vtable */
#define REC_QUANT     0x35u         /* its record quantise byte: 1 = quantise (stock's cache, hook rec_quant) */

/* Measured on the stock image (2026-10-25): the expanded view's pads 29-32 are orange, yellow, violet, cyan (steady
 * codes), the same whichever drum is selected; a pad is white (0x01) while its note sounds. */
static const uint8_t COL_DRUM[DRUMS] = {0x45u, 0x2Du, 0x49u, 0x4Du};

static uint8_t rep_vel[DRUMS] SLIM_ITCM(rep_vel);         /* UI: the press's velocity, written before its flag */
static uint8_t rep_held SLIM_ITCM(rep_held);              /* UI: bit d = drum d's pad is down (latch off) */
static uint8_t rep_new SLIM_ITCM(rep_new);                /* UI sets, Main takes: a press whose first hit is due */
static uint8_t rep_latched SLIM_ITCM(rep_latched);        /* UI: bit d = drum d latched */
static uint8_t rep_snd SLIM_ITCM(rep_snd);                /* Main: bit d = drum d's last hit has had no note-off */
static uint8_t rep_run SLIM_ITCM(rep_run);                /* Main: bit d = drum d's press was taken, not yet ended */
static uint8_t rep_due_hits SLIM_ITCM(rep_due_hits);      /* Main: the sequencer's tick left these for the heartbeat */
static uint8_t rep_playing SLIM_ITCM(rep_playing);        /* Main: the last tick was a playing one */
static uint8_t rep_strike[DRUMS] SLIM_ITCM(rep_strike);   /* Main: the velocity drum d was struck at */
static uint32_t rep_press_tick[DRUMS] SLIM_ITCM(rep_press_tick);   /* Main: arp_tick at the press (moved at Play, Stop) */
static uint32_t rep_last SLIM_ITCM(rep_last);             /* Main: arp_tick at the heartbeat's start (Play resets it) */
static uint32_t rep_hit_tick[DRUMS] SLIM_ITCM(rep_hit_tick);       /* Main: arp_tick of drum d's last hit */
static uint8_t rq_over[DRUMS] SLIM_ITCM(rq_over);         /* Main (masked): 1 = drum d's quantise held off */
static uint8_t rq_shadow[DRUMS] SLIM_ITCM(rq_shadow);     /* stock's last value for drum d's byte (rec_quant, Main) */

/* ---- UI task (and the single-store stops from any task) ---- */

/* Drum d's pad (28 + d) down: one hit at the next heartbeat; with a rate, the repeats while held. Latch on and a rate
 * lit: a tap starts the drum or stops it. No rate lit: a one-shot, latch or not (nothing is latched then: picking no
 * rate stops the latched drums, repeat_pick / chord_link_apply). A press on a latched drum otherwise (the link turned
 * latch off first): nothing. */
void repeat_press(uint32_t d, uint32_t vel)
{
    uint32_t bit = 1u << d, r0 = repeat_cfg[0];
    rep_vel[d] = (uint8_t)vel;
    uint32_t pm = slim_irq_save();
    if ((r0 & REPEAT_LATCH) && REPEAT_RATE(r0)) {
        rep_latched ^= (uint8_t)bit;
        rep_new = (uint8_t)((rep_new & ~bit) | (rep_latched & bit));   /* off: the heartbeat ends it */
    } else if (!(rep_latched & bit)) {
        rep_held |= (uint8_t)bit;
        rep_new |= (uint8_t)bit;
    }
    slim_irq_restore(pm);
}

void repeat_release(uint32_t d)
{
    uint32_t pm = slim_irq_save();
    rep_held &= (uint8_t)~(1u << d);
    slim_irq_restore(pm);
}

/* Every pad up: the page closed or changed, so the pads' releases may never come here. */
void repeat_release_all(void)
{
    rep_held = 0;
}

void repeat_stop_latched(void)
{
    rep_latched = 0;
}

/* A project load: the heartbeat ends every drum. */
void repeat_stop_all(void)
{
    rep_held = 0;
    rep_latched = 0;
}

/* ---- Main task ---- */

/* The expanded drum view's live sink, found every time; 0 when it is not the one we know. */
static uint8_t *drum_sink(void)
{
    uint8_t *view = *(uint8_t **)(TRACK_CONTAINER + CONT_DRUM_VIEW);
    if (!view || *(volatile uint32_t *)view != DRUM_VIEW_VT)
        return 0;
    uint8_t *sink = *(uint8_t **)(view + VIEW_LIVE);
    if (!sink || *(volatile uint32_t *)sink != SINK_VT || sink[SINK_TRACK] != SINK_DRUMS)
        return 0;
    return sink;
}

static uint32_t playing(void)
{
    return *param_get((void *)PLAY_STORE, 0u) != 0u;
}

/* Drum d's hit at `tick`, its previous one ended first. `grid`: on the sequencer's grid (accent: its quarters), else
 * the stopped clock's from the press. */
static void hit(uint8_t *sink, uint32_t d, uint32_t tick, uint32_t grid)
{
    uint32_t bit = 1u << d, e = tick - rep_press_tick[d];
    uint32_t beat = (grid ? tick : e) % BEAT == 0u;
    uint32_t vel = repeat_vel(REPEAT_SHAPE(repeat_cfg[0]), rep_strike[d], e, beat);
    if (rep_snd & bit)
        note_sink_off(sink, d + 1u, REPEAT_DRUM_PAD + d);
    note_sink_on(sink, d + 1u, vel, REPEAT_DRUM_PAD + d);
    rep_snd |= (uint8_t)bit;
    rep_hit_tick[d] = tick;
}

/* Drum d's recorder, 0 when it is not the one we know. */
static volatile uint8_t *drum_rec(uint32_t d)
{
    volatile uint8_t *rec = *(volatile uint8_t **)(RECORDERS + 4u * (DRUM_FIRST + d));
    return rec && *(volatile uint32_t *)rec == DRUM_REC_VT ? rec : 0;
}

/* Stock's refresh of a recorder's quantise byte (mid hook rec_quant, inside its store listener: r5 = the recorder, r0 =
 * the value stock is about to store, 1 = quantise). A drum recorder's value is kept as stock's; while its override
 * runs, 0 is stored instead. A note recorder's goes through untouched. Calls nothing. */
void repeat_on_quant(slim_regs_t *regs)
{
    for (uint32_t d = 0; d < DRUMS; d++)
        if (regs->r[5] == (uint32_t)drum_rec(d)) {
            rq_shadow[d] = (uint8_t)regs->r[0];
            if (rq_over[d])
                regs->r[0] = 0;
            return;
        }
}

/* Once a heartbeat, before any hit: `active` = Unquantized repeats on and a drum repeats or sounds. Starting, each
 * drum recorder's byte is kept as stock's and set to 0; ending, stock's last value goes back (rq_shadow: the refresh
 * keeps it current, so a Shift + Record meanwhile is what comes back). Each drum masked for a few stores: the refresh
 * may run in another task. */
static void unquant(uint32_t active)
{
    for (uint32_t d = 0; d < DRUMS; d++) {
        volatile uint8_t *rec = drum_rec(d);
        if (!rec || rq_over[d] == active)
            continue;
        uint32_t pm = slim_irq_save();
        if (active) {
            rq_shadow[d] = rec[REC_QUANT];
            rq_over[d] = 1u;
            rec[REC_QUANT] = 0u;
        } else {
            rq_over[d] = 0u;
            rec[REC_QUANT] = rq_shadow[d];
        }
        slim_irq_restore(pm);
    }
}

/* Take the new presses (a masked swap) and send their first hits at `tick`; without a sink they are dropped. */
static uint32_t take(uint8_t *sink, uint32_t tick, uint32_t grid)
{
    uint32_t pm = slim_irq_save();
    uint32_t n = rep_new;
    rep_new = 0;
    slim_irq_restore(pm);
    if (!sink)
        return n;
    if (n && repeat_cfg[0] & REPEAT_UNQUANT)
        unquant(1u);            /* a press since the heartbeat's start (unquant there): before its first hit */
    for (uint32_t d = 0; d < DRUMS; d++)
        if (n & 1u << d) {
            rep_press_tick[d] = tick;
            rep_strike[d] = rep_vel[d];
            rep_run |= (uint8_t)(1u << d);
            hit(sink, d, tick, grid);
        }
    return n;
}

/* Heartbeat (arp_on_ms, before its clock): the new presses' first hits, then what the sequencer's last tick left due,
 * then the drums neither held nor latched end (note-off). In the heartbeat that makes Play tick 0 (arp_start), the
 * new presses wait for that tick (repeat_on_tick): their first hit is tick 0's. */
void repeat_on_ms(void)
{
    unquant((repeat_cfg[0] & REPEAT_UNQUANT) && (rep_new | rep_run | rep_snd));
    uint32_t tick = arp_tick;
    rep_last = tick;
    uint8_t *sink = drum_sink();
    uint32_t n = arp_start ? 0u : take(sink, tick, playing());
    uint32_t due = rep_due_hits & ~n;               /* a new press stands in for its drum's due hit */
    rep_due_hits = 0;
    if (!sink)
        return;     /* never on stock 4486 (the view is built at power-on); without it nothing can be sent or ended */
    uint32_t live = rep_held | rep_latched;
    for (uint32_t d = 0; d < DRUMS; d++) {
        uint32_t bit = 1u << d;
        if (due & live & rep_run & bit)
            hit(sink, d, tick, 1u);
        if (rep_run & bit && !(live & bit)) {
            if (rep_snd & bit)
                note_sink_off(sink, d + 1u, REPEAT_DRUM_PAD + d);
            rep_snd &= (uint8_t)~bit;
            rep_run &= (uint8_t)~bit;
        }
    }
}

/* Play (tick 0 of a start): the grid becomes the sequencer's. A drum whose last hit is less than half an interval
 * back (in the stopped clock's ticks up to this heartbeat) gets its press at tick 0, so tick 0 is skipped and no two
 * hits sound close together; every other repeating drum has its press PLAY_BACK ticks back, so tick 0 is a hit and
 * fade / swell sit at their settled value. */
static void on_start(uint32_t run, uint32_t ticks)
{
    for (uint32_t d = 0; d < DRUMS; d++)
        if (run & 1u << d)
            rep_press_tick[d] = 2u * (rep_last - rep_hit_tick[d]) < ticks ? 0u : (uint32_t)-PLAY_BACK;
}

/* Stop (the stopped clock's first tick): a drum that had a grid hit since its press, or was pressed an interval ago or
 * more, goes on on the same grid: its time since the press moves forward to the tick's phase in GRID, so
 * (tick - press) % ticks == 0 exactly where tick % ticks == 0, for every rate. A drum pressed since its last grid point
 * goes on from its press, as it would have. */
static void on_stop(uint32_t run, uint32_t tick, uint32_t ticks)
{
    for (uint32_t d = 0; d < DRUMS; d++) {
        if (!(run & 1u << d))
            continue;
        uint32_t e = tick - rep_press_tick[d];
        uint32_t k = e - 1u - (tick - 1u) % ticks;   /* the press to the last playing tick's grid point (wraps if before) */
        if (e >= ticks || (k < e && 2u * k >= ticks))
            rep_press_tick[d] = tick - (e + (tick % GRID + GRID - e % GRID) % GRID);
    }
}

/* A tick of the arpeggiator's clock: each repeating drum hits on its grid. With `defer` (the sequencer's tick, before
 * stock counts it) the hits wait for the next heartbeat. Tick 0 of a start also takes the presses its heartbeat held
 * back: their first hit is at tick 0, on the beat. */
void repeat_on_tick(uint32_t defer)
{
    uint32_t grid = playing(), was = rep_playing, tick = arp_tick;
    rep_playing = (uint8_t)grid;
    uint32_t run = rep_run & (rep_held | rep_latched);
    uint32_t ticks = repeat_ticks(REPEAT_RATE(repeat_cfg[0]));
    uint8_t *sink = defer ? 0 : drum_sink();
    if (grid && !defer && tick == 0u) {
        on_start(run, ticks);
        take(sink, 0u, 1u);                         /* their press is tick 0: not due again below */
    } else if (!grid && was && ticks && run)
        on_stop(run, tick, ticks);
    for (uint32_t d = 0; d < DRUMS; d++) {
        if (!(run & 1u << d) || !repeat_due(tick, rep_press_tick[d], ticks, grid))
            continue;
        if (defer)
            rep_due_hits |= (uint8_t)(1u << d);
        else if (sink)
            hit(sink, d, tick, grid);
    }
}

/* ---- The page (UI task) ---- */

/* Pads 0-15 (16-27 do nothing here; 28-31 are the drums, page.c sends them to repeat_press). A press only sets the
 * setting. */
void repeat_pick(uint32_t pad)
{
    uint32_t r0 = repeat_cfg[0];
    if (pad < RP_SHAPE) {                           /* one rate across pads 0-7; the lit one again = off */
        uint32_t n = pad + 1u, rate = REPEAT_RATE(r0) == n ? 0u : n;
        repeat_cfg[0] = (uint8_t)((r0 & ~0xFu) | rate);
        if (!rate)
            repeat_stop_latched();                  /* no rate: the pads only play once, so the latched drums stop */
    } else if (pad < RP_SHAPE + 4u) {
        repeat_cfg[0] = (uint8_t)((r0 & ~(3u << 4)) | (pad - RP_SHAPE) << 4);
    } else if (pad == RP_UNQUANT) {
        repeat_cfg[0] = (uint8_t)(r0 ^ REPEAT_UNQUANT);
    } else if (pad == RP_LATCH) {
        repeat_cfg[0] = (uint8_t)(r0 ^ REPEAT_LATCH);
        if (r0 & REPEAT_LATCH)
            repeat_stop_latched();                  /* latch off: the latched drums stop */
    }
}

/* Drum d's pad (28 + d): pulsing white while latched, white while its hit sounds, else stock's colour for it. The one
 * place their colour is chosen. */
static uint16_t repeat_pad_colour(uint32_t d)
{
    uint32_t bit = 1u << d;
    if (rep_latched & bit)
        return COL_LATCHED;
    return (uint16_t)(rep_snd & bit ? COL_WHITE : COL_DRUM[d]);
}

static uint16_t lit(uint32_t on, uint32_t bright, uint32_t dim)
{
    return (uint16_t)(on ? bright : dim);
}

void repeat_draw(uint16_t *out)
{
    uint32_t r0 = repeat_cfg[0], rate = REPEAT_RATE(r0);
    for (uint32_t c = 0; c < PADS; c++)
        out[c] = COL_OFF;
    for (uint32_t c = 0; c < 4u; c++) {
        out[c] = lit(rate == c + 1u, COL_BLUE, COL_BLUE_DIM);
        out[4u + c] = lit(rate == c + 5u, COL_MAGENTA, COL_MAGENTA_DIM);
        out[RP_SHAPE + c] = lit(REPEAT_SHAPE(r0) == c, COL_WHITE, COL_WHITE_DIM);
        out[REPEAT_DRUM_PAD + c] = repeat_pad_colour(c);
    }
    out[RP_UNQUANT] = lit(r0 & REPEAT_UNQUANT, COL_CYAN, COL_CYAN_DIM);
    out[RP_LATCH] = lit(r0 & REPEAT_LATCH, COL_ORANGE, COL_ORANGE_DIM);
}
