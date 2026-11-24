/* Trig conditions (PL20): state, the passes' counts and the saved byte. The maths is trig_math.c.
 *
 * Counts (plan 2026-11-07-trig-conditions.md, "Counting"; evidence docs/investigations/2026-11-01-trig-conditions-spike/
 * B-counting.md, 2026-11-07-trig-conditions-spike.md Q1 / Q3): trig_count[t][p] = the passes of track t's pattern p
 * completed since the track last started over (from 2 x TRIG_COUNT_MOD on, back to TRIG_COUNT_MOD: FIRST once), so a
 * step reads its pass number - 1. Counted in marked and unmarked projects alike (the evaluation checks the mark).
 * - The track advance (hook track_advance, Main), stock's own call (fp == 0) where the pattern ends (r4) or a scene
 *   changes: a pick by hand taking over (hand, no scene) or a scene recalled by hand (hand, scene, the scene chain's
 *   "picked by hand, waiting" latched at seq_tick's entry) starts the track over; anything else counts a pass of the
 *   pattern that ends (sb), a pass an advancing scene chain cuts short too. Step boundaries inside a pattern reach the
 *   hook too (a waiting pick's hand flag reads 1 there): they do nothing.
 * - seq_place (any task: Play from stop through seq_start, Shift + a Patterns pad, a pick while stopped, a load) and a
 *   project load (trig_saved_fix) post a start-over; Main takes it at the heartbeat's start and in the pass handler.
 *   Shift + Play (continue) and a chain advancing by itself reach neither: the counts go on.
 * Two-task rule: Main alone writes trig_count, trig_ms, trig_scene_wait, trig_pre, trig_silent and FILL's pass state
 * (trig_fill_pass, trig_fill_started, trig_fill_done); any task posts into trig_restart with interrupts off for three
 * instructions; the UI task alone writes trig_fill_hold and trig_fill_arm (trig_ui.c).
 *
 * FILL (per drum; plan Task 7): on while its pad is held (trig_fill_hold) or for a whole pass a tap armed
 * (trig_fill_pass). The UI counts taps in trig_fill_arm[d] (odd = armed); Main remembers which arm value's pass it
 * started (trig_fill_started) and which one it finished (trig_fill_done), so an arm value fills one pass and no more.
 * At drum d's pass end (counted or started over): armed and started → done, off; armed, not started → started, on;
 * not armed → off. At each tick 0 of the drum: not armed → off (a disarm ends a running fill at the next step). A
 * start-over posted (Play from stop, a pick, a load) turns the pass off.
 *
 * Playback (plan "Evaluation"; B-counting.md 4-5): each step is evaluated once, at its tick 0 (hook player_tick, Main,
 * before any probability test of that step at every rate, muted tracks too). A marked project's step with notes / a
 * hit gets trig_silent's bit = not its condition; a conditional step (a condition but PRE / NOT PRE, or a probability
 * below 7) sets PRE's state = its condition and its roll (stock's: probability >= [player + 4] & 7, the word stock drew
 * at this tick 0). Stock's three probability tests (prob_note, prob_drum, prob_drum_first) then fail for a silenced
 * track's step: the handler clears APSR's C bit before stock's `blo`, so the step behaves exactly as a failed roll
 * (no mark, no hit, no flip sample; a waiting PL19 strum plays out). */
#include "slim.h"
#include "stock.h"
#include "chord_held.h"
#include "trig_math.h"

#define PATTERNS_N    8u
#define SCENE_CHAIN   0xA0u         /* [engine + 0xA0]: the scene chain's store; parameter 1 != 0 = a scene picked by
                                     * hand, waiting (cleared in seq_tick at its takeover) */
#define MID_SP        64u           /* a mid hook's stub: the original sp = regs + 64 (checks.MID_STUB_STACK) */
#define ADV_TRACK     0x0Cu         /* track_advance: [sp + 0xC] = the track (word) */
#define ADV_HAND      0x18u         /* [sp + 0x18] = the caller's hand flag (byte) */
#define ENGINE        0x20038EC0u   /* the sequencer engine (stock.h seq_tick's notes) */
#define CHAINS        0x9Cu         /* [engine + 0x9C]: the chain store; parameter 8 + t != 0 = track t's pick by hand
                                     * waits for its pattern end */
#define NOTE_PLAYERS  0x20040200u   /* stock.h seq_players: note track t's player at + 0x184 t (t 0-3) */
#define NOTE_PLAYER   0x184u
#define DRUM_PLAYERS  0x20040810u   /* drum d's player at + 0x90 d (track 4 + d) */
#define DRUM_PLAYER   0x90u
#define RECORDERS     0x2003C174u   /* stock.h recorders: [+ 4 t] = track t's recorder; [rec + 0x48] = its 8 patterns */
#define DRUM_PATTERN  0x6A8u        /* a drum pattern: velocity [32] at + 0, probability [32] at + 0x20, ... */
#define DRUM_PROB     0x20u
#define NOTE_PATTERN  0xCA8u        /* a note pattern: 32 steps of 28 B: [0] unit mask (bits 0-5), [1] probability */
#define NOTE_STEP     28u
#define STEPS         32u
#define NOTE_TRACKS   4u
#define APSR_C        (1u << 29)

uint8_t trig_mark SLIM_ITCM(trig_mark);     /* 1 = this project's condition bytes are CTPlay's; anything else loads as 0 */
uint16_t trig_count[TRIG_TRACKS][PATTERNS_N] SLIM_ITCM(trig_count);    /* Main */
volatile uint8_t trig_restart SLIM_ITCM(trig_restart);  /* bit t: track t starts over (any task posts, Main takes) */
volatile uint32_t trig_ms SLIM_ITCM(trig_ms);           /* Main: the heartbeat's ms count */
uint8_t trig_scene_wait SLIM_ITCM(trig_scene_wait);     /* Main: the scene chain's parameter 1 at seq_tick's entry */
uint8_t trig_pre SLIM_ITCM(trig_pre);                   /* Main: bit t = PRE's state of track t (1 = played) */
uint8_t trig_silent SLIM_ITCM(trig_silent);             /* Main: bit t = track t's current step is silenced */
volatile uint8_t trig_fill_hold SLIM_ITCM(trig_fill_hold);  /* UI: bit d = drum d's FILL pad held */
uint8_t trig_fill_pass SLIM_ITCM(trig_fill_pass);       /* Main: bit d = drum d's FILL on for this pass */
uint8_t trig_fill_started[TRIG_DRUMS] SLIM_ITCM(trig_fill_started);    /* Main: the arm value whose pass started */
uint8_t trig_fill_done[TRIG_DRUMS] SLIM_ITCM(trig_fill_done);          /* Main: the arm value whose pass ended */

void trig_init(void)
{
    trig_mark = 0;
    memset(trig_count, 0, sizeof trig_count);
    trig_restart = 0;
    trig_ms = 0;
    trig_scene_wait = 0;
    trig_pre = 0;
    trig_silent = 0;
    trig_fill_hold = 0;
    trig_fill_pass = 0;
    memset(trig_fill_started, 0, sizeof trig_fill_started);
    memset(trig_fill_done, 0, sizeof trig_fill_done);
    trig_ui_init();
}

/* After a project load (the UI task's LED frame, features/saved): every track starts over. */
void trig_saved_fix(void)
{
    if (trig_mark != 1u)
        trig_mark = 0;
    trig_post_restart(0xFFu);
}

/* Any task: tracks (bit t = track 0-7) start over at Main's next heartbeat or pass. */
void trig_post_restart(uint32_t tracks)
{
    uint32_t pm = slim_irq_save();
    trig_restart = (uint8_t)(trig_restart | tracks);
    slim_irq_restore(pm);
}

/* Main: the posted start-overs: those tracks' counts to 0, PRE's state "did not play", a drum's FILL pass off (a
 * waited hand change does the first two in trig_on_pass, at a pass end, where fill_step ends a running fill). */
void trig_take_restarts(void)
{
    uint32_t pm = slim_irq_save();
    uint32_t bits = trig_restart;
    trig_restart = 0;
    slim_irq_restore(pm);
    if (!bits)
        return;
    trig_pre = (uint8_t)(trig_pre & ~bits);
    trig_fill_pass = (uint8_t)(trig_fill_pass & ~(bits >> NOTE_TRACKS));
    for (uint32_t t = 0; bits; t++, bits >>= 1)
        if (bits & 1u)
            for (uint32_t p = 0; p < PATTERNS_N; p++)
                trig_count[t][p] = 0;
}

/* main_ms slot 0 (Main, every 1 ms, before the sequencer's clock): the ms count, then the start-overs, so a Play from
 * stop has them before its first step's tick 0. */
void trig_on_ms(void)
{
    trig_ms++;
    trig_take_restarts();
}

/* seq_tick (Main, while playing): latch "a scene picked by hand, waiting" before the tick's takeover clears it. */
int trig_on_seq_tick(void *engine, uint32_t *ret)
{
    (void)ret;
    void *chain = *(void **)((uint8_t *)engine + SCENE_CHAIN);
    trig_scene_wait = *param_get(chain, 1) != 0u;
    return SLIM_PASS;
}

/* seq_place (any task): the track is placed anew: it starts over. */
int trig_on_place(void *engine, uint32_t track, uint32_t tick, uint32_t from_start, uint32_t *ret)
{
    (void)engine;
    (void)tick;
    (void)from_start;
    (void)ret;
    if (track < TRIG_TRACKS)
        trig_post_restart(1u << track);
    return SLIM_PASS;
}

/* Main: drum d's FILL pass at its pass end (end) or a tick 0 of its steps. armed = an odd arm value not done yet; the
 * pass stays on only for the arm value it started with (a disarm, or a disarm and a new arm, ends it). */
static void fill_step(uint32_t d, uint32_t end)
{
    uint32_t arm = trig_fill_arm[d], bit = 1u << d;
    uint32_t armed = (arm & 1u) && arm != trig_fill_done[d];
    if (armed && end) {
        if (trig_fill_started[d] != arm) {      /* the armed pass starts */
            trig_fill_started[d] = (uint8_t)arm;
            trig_fill_pass = (uint8_t)(trig_fill_pass | bit);
            return;
        }
        trig_fill_done[d] = (uint8_t)arm;       /* the armed pass ended */
        armed = 0;
    }
    if (!armed || trig_fill_started[d] != arm)
        trig_fill_pass = (uint8_t)(trig_fill_pass & ~bit);
}

/* track_advance (Main): stock's call (fp == 0) where a pattern ends or a scene changes. */
void trig_on_pass(slim_regs_t *regs)
{
    if (regs->r[11] != 0u)
        return;                                 /* fp: the look-ahead's call */
    uint32_t end = regs->r[4] & 0xFFu, scene = regs->r[1] & 0xFFu;
    if (!end && !scene)
        return;                                 /* a step boundary inside the pattern */
    const uint8_t *sp = (const uint8_t *)regs + MID_SP;
    uint32_t t = *(const uint32_t *)(sp + ADV_TRACK), p = regs->r[9] & 0xFFu, hand = sp[ADV_HAND];
    if (t >= TRIG_TRACKS || p >= PATTERNS_N)
        return;
    trig_take_restarts();                       /* after the filters: nothing is written on a filtered call, and the
                                                 * heartbeat takes them every ms anyway */
    if (t >= NOTE_TRACKS)
        fill_step(t - NOTE_TRACKS, 1);          /* a drum's pass end, counted or started over: it ends a running fill
                                                 * here, as a posted start-over would (its pass bit is not cleared
                                                 * again: a fill armed for the next pass starts with the new pattern) */
    if (hand && (!scene || trig_scene_wait)) {  /* a pick by hand takes over, or a scene recalled by hand */
        for (uint32_t k = 0; k < PATTERNS_N; k++)
            trig_count[t][k] = 0;
        trig_pre = (uint8_t)(trig_pre & ~(1u << t));    /* PRE's state "did not play", as trig_take_restarts */
        return;
    }
    uint32_t c = trig_count[t][p] + 1u;         /* a pass ended, or an advancing scene chain cut it short. Past
                                                 * 2 x TRIG_COUNT_MOD - 1 it wraps to TRIG_COUNT_MOD, not 0: every cycle
                                                 * stays exact (840 is a multiple of 2-8) and count 0 (FIRST) comes only
                                                 * once per start-over */
    trig_count[t][p] = (uint16_t)(c >= 2u * TRIG_COUNT_MOD ? c - TRIG_COUNT_MOD : c);
}

/* ---- Playback ---------------------------------------------------------------------------------------------------- */

/* Drum d's FILL: its pad held (UI) or on for this pass (Main). */
uint32_t trig_fill_on(uint32_t d)
{
    return ((uint32_t)(trig_fill_hold | trig_fill_pass) >> d) & 1u;
}

/* Drum d's pattern p (its recorder's patterns, as the player's). */
uint8_t *trig_drum_pattern(uint32_t d, uint32_t p)
{
    uint8_t *rec = *(uint8_t **)(RECORDERS + 4u * (NOTE_TRACKS + d));
    return *(uint8_t **)(rec + 0x48) + DRUM_PATTERN * p;
}

/* Note track t's step s of pattern p (28 B), through its player. */
uint8_t *trig_note_step(uint32_t t, uint32_t p, uint32_t s)
{
    uint8_t *player = (uint8_t *)(NOTE_PLAYERS + NOTE_PLAYER * t);
    return *(uint8_t **)(player + 0x48) + NOTE_PATTERN * p + NOTE_STEP * s;
}

/* Track t's step s of pattern p: its condition; 0 in an unmarked project. */
uint32_t trig_code_at(uint32_t t, uint32_t p, uint32_t s)
{
    if (trig_mark != 1u || t >= TRIG_TRACKS || p >= PATTERNS_N || s >= STEPS)
        return 0u;
    if (t < NOTE_TRACKS)
        return trig_note_get(trig_note_step(t, p, s));
    return trig_drum_get(trig_drum_pattern(t - NOTE_TRACKS, p), s);
}

/* The track (0-7) of a player, TRIG_TRACKS for anything else. */
static uint32_t player_track(uint32_t player)
{
    uint32_t off = player - NOTE_PLAYERS;
    if (off < NOTE_TRACKS * NOTE_PLAYER && off % NOTE_PLAYER == 0u)
        return off / NOTE_PLAYER;
    off = player - DRUM_PLAYERS;
    if (off < (TRIG_TRACKS - NOTE_TRACKS) * DRUM_PLAYER && off % DRUM_PLAYER == 0u)
        return NOTE_TRACKS + off / DRUM_PLAYER;
    return TRIG_TRACKS;
}

/* LAST, read at tick 0: track t's pick by hand waits (the chain store's parameter 8 + t) or a scene picked by hand
 * waits (the scene chain's parameter 1). Both are cleared in seq_tick before the takeover's first tick 0. */
static uint32_t last_pass(uint32_t t)
{
    const uint8_t *engine = (const uint8_t *)ENGINE;
    return *param_get(*(void *const *)(engine + CHAINS), 8u + t) != 0u
        || *param_get(*(void *const *)(engine + SCENE_CHAIN), 1) != 0u;
}

/* player_tick (Main, every tick of every player's play pass): at tick 0 (r5 == 0) the step's evaluation. r7 = the
 * player, sb = its pattern, r8 = its step; [player + 4] = the random word stock drew for this step. */
void trig_on_step(slim_regs_t *regs)
{
    if (regs->r[5] != 0u)
        return;
    uint32_t t = player_track(regs->r[7]);
    if (t >= TRIG_TRACKS)
        return;
    trig_take_restarts();
    if (t >= NOTE_TRACKS)
        fill_step(t - NOTE_TRACKS, 0);          /* a disarm ends a running fill pass here */
    uint32_t bit = 1u << t, p = regs->r[9] & 0xFFu, s = regs->r[8] & 0xFFu;
    trig_silent = (uint8_t)(trig_silent & ~bit);
    if (trig_mark != 1u || p >= PATTERNS_N || s >= STEPS)
        return;
    uint32_t code, prob, fill = 0;
    if (t < NOTE_TRACKS) {
        const uint8_t *step = trig_note_step(t, p, s);
        if (!(step[0] & 0x3Fu))
            return;                             /* no notes: not evaluated */
        code = trig_note_get(step);
        prob = step[1];
    } else {
        const uint8_t *pat = trig_drum_pattern(t - NOTE_TRACKS, p);
        if (!pat[s])
            return;                             /* no hit (velocity 0): not evaluated */
        code = trig_drum_get(pat, s);
        prob = pat[DRUM_PROB + s];
        fill = trig_fill_on(t - NOTE_TRACKS);
    }
    trig_ctx_t c = {(uint16_t)trig_count[t][p], (uint8_t)((trig_pre >> t) & 1u), (uint8_t)fill, (uint8_t)last_pass(t)};
    uint32_t plays = trig_plays(code, &c);
    if (!plays)
        trig_silent = (uint8_t)(trig_silent | bit);
    if (trig_conditional(code, prob)) {
        uint32_t roll = prob >= (*(const uint32_t *)(regs->r[7] + 4u) & 7u);
        trig_pre = (uint8_t)(plays && roll ? trig_pre | bit : trig_pre & ~bit);
    }
}

/* A probability test of the player's step: a silenced step fails it (C clear: stock's `blo` to "fails" is taken). */
static void fail_if_silent(slim_regs_t *regs, uint32_t player)
{
    uint32_t t = player_track(player);
    if (t < TRIG_TRACKS && (trig_silent >> t) & 1u)
        regs->apsr &= ~APSR_C;
}

/* prob_note (Main): seq_units_start's test, once per used unit per microstep; sb = the note player. */
void trig_on_prob_note(slim_regs_t *regs)
{
    fail_if_silent(regs, regs->r[9]);
}

/* prob_drum (Main): the drum hit test, once per microstep; the player at the original sp + 4. */
void trig_on_prob_drum(slim_regs_t *regs)
{
    fail_if_silent(regs, *(const uint32_t *)((const uint8_t *)regs + MID_SP + 4u));
}

/* prob_drum_first (Main): slot 4's test at tick 0 (the flip sample's); r4 = the drum player. */
void trig_on_prob_first(slim_regs_t *regs)
{
    fail_if_silent(regs, regs->r[4]);
}
