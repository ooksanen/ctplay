/* chord feature internals shared by chord.c, page.c and arp.c (not an interface for other features).
 * Spec: docs/specs/2026-10-14-arpeggiator-design.md. */
#pragma once
#include <stdint.h>
#include "chord_math.h"
#include "melody_math.h"

#define TRACKS        4u            /* note tracks 0-3: every array indexed by a track has TRACKS entries */
#define DRUMS         4u            /* PL16: drum d is track DRUM_FIRST + d (its button id, track_of, chord_page) */
#define DRUM_FIRST    4u
#define PADS          32u
#define HELD          6u            /* chords held at once, all tracks */
#define HELD_STRUM    0x01u         /* held_t.flags: the heartbeat drives this entry */
#define HELD_RELEASED 0x02u         /* its pad was released (strum: the heartbeat ends what it sent; arpeggio: latched) */
#define HELD_SPEED(f) (((f) >> 2) & 3u)
#define HELD_ARP      0x10u         /* an arpeggio's notes: only the arpeggiator (Main task) sounds them */
#define HELD_FALLING  0x20u         /* a falling strum: notes[] falling, the pad's own note sent in its place among them */
#define HELD_TICKS    0x40u         /* PL19, an active Written track: `wait` counts sequencer ticks (arp_tick), not ms */
#define HELD_OWN_ROOT 0x80u         /* PL19, a rising strum on an active track pressed while recording (pstrum_recording):
                                     * the heartbeat sends the pad's own note first (the press is taken: stock plays
                                     * nothing) and ends it with the others; else stock sends it, as PL18 */
#define ARP_LIVE      0x80u         /* an arpeggio entry's count: ARP_LIVE | its other notes (never 0 while live) */
#define STRUM_OF(t)   ((chord_strum >> (2u * (t))) & 3u)
#define STRUM_DOWN(t) ((chord_strum_down >> (t)) & 1u)
#define PSTRUM_OF(t)  ((chord_pstrum >> (2u * (t))) & 3u)   /* PL19: track t's pattern strum */
#define PSTRUM_PLAYED  1u           /* strummed on playback (the strum speed is the gap) */
#define PSTRUM_WRITTEN 2u           /* a roll written in the pattern */
extern const uint8_t STRUM_GAP[4];  /* ms between strummed notes: off, slow, medium, fast (chord.c) */

/* pstrum.c (PL19): Played, a pattern's chords strummed on playback. The seq_play_step hook (the player's task: Main,
 * context any) queues a chord's late notes; the seq_end_all hook (any task) drops them; the heartbeat (Main) sends
 * them through stock's player note-on. */
void pstrum_init(void);
int pstrum_on_play_step(void *player, uint32_t pattern, uint32_t step, uint32_t micro, uint32_t *ret);
int pstrum_on_reset(void *player, uint32_t *ret);
void pstrum_on_ms(void);

/* chord_arp[t][0]: pattern (bits 0-2), rate (3-4), modifier (5-6), latch (7); [1]: octaves - 1 (0-1), gate (2-4:
 * sixths of the step - 1, 5 = 6/6 = legato). */
#define ARP_PATTERN(a0) ((a0) & 7u)
#define ARP_RATE(a0)    (((a0) >> 3) & 3u)      /* 0 1/4, 1 1/8, 2 1/16, 3 1/32 */
#define ARP_MOD(a0)     (((a0) >> 5) & 3u)
#define ARP_LATCH       0x80u
#define ARP_OCT(a1)     (((a1) & 3u) + 1u)
#define ARP_GATE(a1)    (((a1) >> 2) & 7u)
#define ARP_OFF 0u
#define ARP_UP 1u
#define ARP_DOWN 2u
#define ARP_UPDOWN 3u
#define ARP_DOWNUP 4u
#define ARP_RANDOM 5u
#define ARP_PLAYED 6u
#define ARP_CHORD 7u
#define MOD_TRIPLET 1u
#define MOD_DOTTED 2u
#define GATE_LEGATO 5u
#define GATE_DEFAULT 2u            /* 3/6 */

/* Device RGB table codes, all steady (CLAUDE.md, LEDs). */
#define COL_OFF          0x00u
#define COL_WHITE        0x01u      /* stock's playhead white */
#define COL_WHITE_DIM    0x02u
#define COL_BLUE         0x07u      /* stock's Clear blue */
#define COL_BLUE_DIM     0x08u
#define COL_GREEN        0x17u
#define COL_GREEN_DIM    0x18u
#define COL_YELLOW       0x2Du      /* the 2D-30 family: steady, dim, blink, pulse; 0x2F / 0x30 animate */
#define COL_YELLOW_DIM   0x2Eu
#define COL_MAGENTA      0x32u
#define COL_MAGENTA_DIM  0x38u
#define COL_ORANGE       0x45u
#define COL_ORANGE_DIM   0x46u
#define COL_GATE_1_6     0x68u      /* stock's Gate view: 0x68 1/6 ... 0x63 6/6 (a partial last pad) */
#define COL_CYAN         0x4Du      /* the 4D-50 family (stock's count-in "both", PL08); 0x4F / 0x50 animate. PL14: the */
#define COL_CYAN_DIM     0x4Eu      /* cycle, the thinning, the ties */
#define COL_VIOLET       0x49u      /* the 49-4C family; 0x4B / 0x4C animate. PL14: the combine */
#define COL_VIOLET_DIM   0x4Au

typedef struct {
    uint8_t count;                  /* 0 = free; an arpeggio entry: ARP_LIVE | other notes */
    uint8_t track, pad;
    uint8_t notes[CHORD_MAX_OTHER]; /* strummed and arpeggio entries: rising (a falling strum: falling) */
    uint8_t sent;                   /* strummed: notes[0 .. sent) have sounded (falling: the pad's own note counts too) */
    uint8_t vel;                    /* the pad's velocity */
    uint8_t flags;                  /* HELD_STRUM, HELD_RELEASED, HELD_ARP, HELD_FALLING; strum speed in bits 2-3 */
    uint8_t wait;                   /* strummed: heartbeats until notes[sent] */
    uint8_t drop;                   /* strummed: index + 1 of the tone a tight strum leaves out, 0 = none */
    uint8_t root;                   /* the pad's own pitch */
    uint8_t order;                  /* chord_order[track] at the press ("as played") */
} held_t;

extern held_t held[HELD];
extern uint8_t chord_strum;         /* 2 bits per track (0 off, 1-3 slow-fast) */
extern uint8_t chord_strum_down;    /* bit t: track t strums falling */
extern uint8_t chord_rootless;      /* bit t: track t's bass is rootless over bass (with the settings' bass bit) */
extern uint8_t chord_order[TRACKS]; /* press counter per track: held_t.order (one per track, so presses on other
                                     * tracks never wrap it under a latched arpeggio) */
extern uint8_t chord_settings[TRACKS];   /* shape | inversion | spread | bass, see chord_math.h */
extern uint8_t chord_arp[TRACKS][2];

uint8_t *chord_note_sink(void *view);
/* step_entry.c (PL19, Written): the pending spills of step entries, written on the release of the pad that made them
 * (chord_on_release, UI task); chord_init clears them. */
void step_entry_init(void);
void step_spill_release(void *view, uint32_t pad);
uint8_t *chord_track_sink(uint32_t track);
void chord_send_on(uint8_t *sink, uint32_t track, uint32_t note, uint32_t vel, uint32_t pad);
void *chord_visible_view(void *ctrl, uint32_t *mode);
int chord_shift_held(void);


/* A page's number is its pad in the page list (row 4, Shift held on a page), fixed for good (ui-map.md, "Page slots"):
 * main pages fill it from the left, setup pages from the right; empty pads have no page. */
#define PAGE_CHORDS   0u
#define PAGE_ARP      1u
#define PAGE_TOOLS    2u            /* Pattern tools (PL11): Euclidean fills */
#define PAGE_MELODY   3u            /* Melody (PL13): the melodic generator's settings (melody.c) */
#define PAGE_KEYS     7u            /* setup: the keyboard (mono record) */
#define PAGE_SLOTS    8u
/* trig.c (PL20, trig conditions): trig_mark is saved (not linked); trig_init from chord_init, trig_saved_fix from
 * chord_saved_fix (it also starts every track over). The passes' counts: trig_count[t][p] (Main only) = the passes of
 * track t's pattern p completed since the track started over, counted by the track_advance hook (trig_on_pass);
 * trig_on_ms from chord_on_ms (slot 0, first) counts trig_ms and takes the posted start-overs. Playback: each step's
 * condition at its tick 0 (trig_on_step) sets trig_silent and trig_pre; a silenced step fails stock's probability
 * tests. FILL: trig_fill_hold (UI, bit d = drum d's pad held) | trig_fill_pass (Main, bit d = on for this pass); a
 * tap counts in trig_fill_arm[d] (UI, odd = armed), Main fills one whole pass per arm value (trig_fill_started /
 * trig_fill_done = the arm value whose pass started / ended). */
#define TRIG_TRACKS 8u              /* the sequencer's tracks: Synth 1, Synth 2, MIDI 1, MIDI 2, Drum 1-4 */
#define TRIG_DRUMS  4u
extern uint8_t trig_mark;
extern uint16_t trig_count[TRIG_TRACKS][8];
extern volatile uint8_t trig_restart;   /* bit t: track t starts over; any task posts (trig_post_restart), Main takes */
extern volatile uint32_t trig_ms;       /* Main: the heartbeat's ms count */
extern uint8_t trig_scene_wait;         /* Main: a scene picked by hand waits (latched at seq_tick's entry) */
void trig_init(void);
void trig_saved_fix(void);
void trig_post_restart(uint32_t tracks);   /* any task; bit t = track 0-7 */
void trig_take_restarts(void);             /* Main */
void trig_on_ms(void);                     /* Main */
extern uint8_t trig_pre;                   /* Main: bit t = PRE's state (1 = the last conditional step played) */
extern uint8_t trig_silent;                /* Main: bit t = track t's current step is silenced */
extern volatile uint8_t trig_fill_hold;    /* UI: bit d = drum d's FILL held */
extern uint8_t trig_fill_pass;             /* Main: bit d = drum d's FILL on for this pass */
extern uint8_t trig_fill_arm[TRIG_DRUMS];  /* UI: drum d's taps (odd = armed, unless trig_fill_done[d] holds it) */
extern uint8_t trig_fill_started[TRIG_DRUMS];  /* Main: the arm value whose fill pass started */
extern uint8_t trig_fill_done[TRIG_DRUMS];     /* Main: the arm value whose fill pass ended */
uint32_t trig_fill_on(uint32_t d);                              /* drum 0-3: (hold | pass) >> d & 1 */
uint32_t trig_code_at(uint32_t t, uint32_t p, uint32_t s);      /* track 0-7's step: its code, 0 when unmarked */
uint8_t *trig_drum_pattern(uint32_t d, uint32_t p);             /* drum 0-3's pattern p */
uint8_t *trig_note_step(uint32_t t, uint32_t p, uint32_t s);    /* note track 0-3's step s of pattern p (28 B) */
/* trig_ui.c (PL20, UI task): row 4 of stock's probability view. The press hooks (prob_view_note / prob_view_drum)
 * only latch {pad, view, track, the step, Shift, trig_ms}; the container's release (cont_release) writes the gesture's
 * code (trig_edit), marking the project first (trig_mark_project); trig_draw from chord_on_leds lights row 4. FILL on
 * the drum expanded view's pads 21-24 (wide_drum_press / wide_drum_release; trig_draw lights them); trig_fill_stop
 * from chord_on_leds' start disarms every FILL while the transport is stopped (a page may cover trig_draw). */
#define TRIG_HOLD_MS 500u           /* a press held this long (by trig_ms, at the press and the release) is a hold */
void trig_ui_init(void);            /* from trig_init */
int trig_on_note_view_pad(void *view, uint32_t pad, uint32_t *ret);
int trig_on_drum_view_pad(void *view, uint32_t pad, uint32_t *ret);
int trig_on_cont_release(void *cont, uint32_t pad, uint32_t *ret);
void trig_draw(void *ctrl, uint16_t *out);
void trig_mark_project(void);       /* the first condition written: every condition byte 0, the editors' stores, the mark */
int trig_on_wide_press(void *view, uint32_t pad, uint32_t vel, uint32_t *ret);
int trig_on_wide_release(void *view, uint32_t pad, uint32_t *ret);
void trig_fill_stop(void);
/* trig_keep.c (PL20, UI task): conditions follow stock's own edits in a marked project: a drum's through Duplicate,
 * Clear step, Clear pattern, copy 1-16 -> 17-32, paste step and Mutate, and go with its hit (step off, the flip
 * sample's removal; the micro-step view's last bit, a mid hook); a note step's are zeroed by stock's fill. */
int trig_on_drum_duplicate(void *editor, const uint8_t *src, uint32_t pattern, uint32_t *ret);
int trig_on_drum_clear_step(void *editor, uint32_t *ret);
int trig_on_drum_clear_pattern(void *editor, uint32_t pattern, uint32_t *ret);
int trig_on_drum_copy_half(void *editor, uint32_t *ret);
int trig_on_drum_paste_step(void *editor, uint32_t vel, uint32_t flip, uint32_t micro, uint32_t *ret);
int trig_on_note_step_fill(void *editor, uint8_t *step, uint32_t *ret);
int trig_on_drum_step_off(void *view, uint32_t step, uint32_t *ret);
int trig_on_drum_remove(void *listener, uint32_t step, uint32_t *ret);
extern uint8_t chord_pstrum;       /* 2 bits per track: 0 off, 1 played, 2 written (PL19, Keys pads 3-4) */
/* Track t's pattern strum where it acts (Global Constraints "Active"): PSTRUM_PLAYED or PSTRUM_WRITTEN with its strum
 * speed on, else 0. */
static inline uint32_t pstrum_mode(uint32_t t)
{
    uint32_t m = PSTRUM_OF(t);
    return STRUM_OF(t) && (m == PSTRUM_PLAYED || m == PSTRUM_WRITTEN) ? m : 0u;
}
/* pstrum_rec.c (PL19): recording a live strum on an active track (Played: a plain chord; Written: a roll). The
 * heartbeat (chord_on_ms, Main) calls pstrum_rec_on_ms once a beat, pstrum_rec_before / pstrum_rec_sent around each
 * strum send of held[i], pstrum_rec_off / pstrum_rec_off_end around each strum note-off of held[i] (`own`: the entry's
 * pad owns the pitch). The mid hooks rec_off_commit and rec_pass_commit (pstrum_on_off_commit, pstrum_on_pass_commit)
 * move the notes. */
void pstrum_rec_init(void);
void pstrum_rec_on_ms(void);
uint32_t pstrum_rec_before(uint32_t track);
void pstrum_rec_sent(uint32_t i, uint32_t note, uint32_t c);
uint32_t pstrum_rec_off(uint32_t i, uint32_t note, uint32_t own);
void pstrum_rec_off_end(uint32_t token);
uint32_t pstrum_recording(void);    /* stock's recording condition: playing, Record, p2 == 0 (any task) */
/* The latest Written move per track, for mono record (mono.c): [0] the word the move wrote (0 = none), [1] the roll's
 * first note's start. Written by a move (interrupts off), read and cleared by mono's commit handler (interrupts off). */
extern volatile uint32_t pstrum_roll[TRACKS][2];
extern uint8_t chord_step;          /* bit t: track t writes chords in step entry (PL18, Keys pad 2) */
extern uint8_t chord_mono;          /* bit t: track t records mono (mono.c); set on the Keys page */
extern uint8_t chord_page;          /* page.c: the track whose play page is open (0-3 notes, 4-7 drums), 0xFF when none */
extern uint8_t page_slot[TRACKS];   /* page.c: each track's last page (the one Shift + its button opens) */
int page_exists(uint32_t p);        /* page.c: a page sits on pad 25 + p */
extern uint8_t page_quick[TRACKS];  /* page.c: each track's quick view (a page), flipped with Shift + 1-16/17-32 */
void page_quick_pad(uint32_t track, uint32_t pad);
void page_quick_draw(uint32_t track, uint16_t *out);
void page_shift_leds(void *ctrl, uint16_t *out);
void page_init(void);
int page_on_button(void *ctrl, uint32_t id);
int page_draw(void *ctrl, uint16_t *out);

/* arp.c (Main task) */
void arp_init(void);
void mono_init(void);                  /* mono.c: the recorder commit hook's state */
void arp_on_ms(void);
void arp_on_tick(uint32_t defer);      /* defer: the sequencer's tick (sends wait for the next heartbeat) */
uint32_t arp_sounding(uint32_t t, uint8_t *notes);
/* chord.c, UI task: free the track's arpeggio entries (all, or with `released` only the latched ones, and then only
 * when none of the track's arpeggio pads is held). */
void arp_free(uint32_t track, uint32_t released);
uint32_t chord_track_settings(uint32_t t);   /* the settings byte plus CHORD_ROOTLESS in bit 8 and the row-2 shape in bits 9-12 */
/* The chord a live press of `root` (a keyboard pitch) on track t builds: its other notes in out (at most CHORD_MAX_OTHER),
 * from the track's settings, the scale `mask` and the project root `key`, with the track's voice leading from its last
 * chord; it becomes the track's last chord. Returns how many. The caller checks the track has a chord to play. */
uint32_t chord_build(uint32_t track, uint32_t root, uint32_t mask, uint32_t key, uint8_t *out);

/* chord_voice[t] (PL15, saved, linked, ITCM): bits 0-3 the row-2 shape (0 none, 1-5), bits 4-5 voice leading, 6-7 = 0.
 * Spec 2026-10-23-chords-page-design.md, "Settings and saving". */
#define VOICE_SHAPE2(v) ((v) & 0xFu)
#define VOICE_LEAD(v)   (((v) >> 4) & 3u)
#define LEAD_OFF        0u
#define LEAD_CLOSE      1u
#define LEAD_TOP        2u
#define LEAD_BOTTOM     3u
#define VOICE_BITS      0x3Fu       /* the bits that mean something; 6-7 are spare */
extern uint8_t chord_voice[TRACKS];
/* UI task: the Chords page's shape picks, index 0-12 (as chord_shape_index): 0-7 row 1 (clears the row-2 shape), 8-12
 * row 2 (the row-1 shape back to single); the voice leading and the rest of the settings stay. */
void chord_pick_shape(uint32_t t, uint32_t index);

/* repeat_cfg[2] (PL16, saved, linked, ITCM; one setting for the kit): [0] bits 0-3 the rate (0 off, 1-8), bits 4-5 the
 * velocity shape (0 as struck, 1 fade, 2 swell, 3 accent the beat), bit 6 latch, bit 7 unquantized repeats; [1] = 0.
 * drum_page[d] (PL16, saved, not linked, ITCM): drum d's last page: bits 0-2 the slot, bit 3 Pattern tools 2 (PL17),
 * bits 4-7 = 0. Spec 2026-10-25-drums-design.md. Beta: Repeat is slot 1 (it was 0); a slot with no page, an alpha
 * project's 0 included, opens Repeat (page.c page_of). */
#define REPEAT_RATE(r0)   ((r0) & 0xFu)
#define REPEAT_SHAPE(r0)  (((r0) >> 4) & 3u)
#define REPEAT_LATCH      0x40u
#define REPEAT_UNQUANT    0x80u
#define REPEAT_RATE_MAX   8u
#define DRUM_SLOT(b)      ((b) & 7u)
#define DRUM_SUB          0x08u
#define PAGE_REPEAT       1u        /* the drum page list: Repeat on the note tracks' Arp pad (beta); PL17: Pattern tools
                                     * at PAGE_TOOLS, as the note tracks' */
int drum_slot_exists(uint32_t p);   /* page.c: slot p of the drum page list holds a page */
extern uint8_t repeat_cfg[2];
extern uint8_t drum_page[4];
/* PL17, Pattern tools for the drums (drum_tools.c; spec 2026-10-25-drums-design.md), per drum, in ITCM: drum_euclid is
 * euclid_cfg's layout with the roll in rotation's byte (bits 5-7: 0 one hit, 1 two, 2 three), drum_rhythm rhythm_cfg's,
 * drum_accent bits 0-1 the accent (melody's: 0 off, 1 first hit, 2 on the beat, 3 every 3rd), drum_seed the rhythm
 * seed (never 0; saved, not linked). */
#define ROLL(c1)          (((c1) >> 5) & 7u)
#define ROLL_BITS         0xE0u
#define ROLL_MAX          2u
#define ACCENT_BITS       3u
extern uint8_t drum_euclid[DRUMS][2], drum_rhythm[DRUMS][3], drum_accent[DRUMS], drum_seed[DRUMS];
void drum_tools_init(void);
void drum_tools_saved_fix(void);
/* UI task: drum d's shown pattern (the editor's position store), in a draft the draft's, and its steps first .. first +
 * n - 1; 0 when there is none (no record, no drum recorder, or its vtable is not a drum recorder's; n unchanged). */
uint8_t *drum_target(uint32_t d, uint32_t *n, uint32_t *first);
/* The drum Write and Undo (drum_tools.c, UI task, on a pad's release): the 128 B of a pattern's step arrays, through
 * the drum editor's step store when it mirrors the pattern. drum_undo_at[d] = 1 + the pattern drum_undo_steps[d] came
 * from, 0 = none (ITCM; a project load drops them). PL20: drum_undo_cond[d] = that pattern's 36 condition bytes
 * (+ 0x84 .. + 0xA7) the Write zeroed in a marked project, swapped back with the steps by Undo. */
#define DSTEPS_SIZE       0x80u
#define DCOND_SIZE        0x24u
extern uint8_t drum_undo_steps[DRUMS][DSTEPS_SIZE], drum_undo_at[DRUMS], drum_undo_cond[DRUMS][DCOND_SIZE];
uint8_t *drum_put(uint32_t d, uint32_t want, uint32_t keep_undo);   /* the masked write; the store to refresh, or 0 */
void drum_refresh(uint8_t *store);                                  /* unmasked: touch all, commit; nothing for 0 */
uint32_t drum_write_to(uint32_t d, uint32_t want, uint32_t keep_undo);   /* put + refresh: 1 when it wrote */
void drum_undo(uint32_t d);
int drum_has_undo(uint32_t d);
int drum_link_valid(const uint8_t *cand, const uint8_t *old);   /* CTCtrl link: whole candidate / old payloads */
void drum_link_apply(const uint8_t *old);   /* CTCtrl link: after a write, old = the payload before it */
#define REPEAT_DRUM_PAD   28u       /* the Repeat page's pads 28-31: drums 1-4 (the expanded drum view's pads 29-32) */
/* repeat.c. UI task, flags only: drum d's pad down (its velocity) and up; every pad up (a page closed or opened: a
 * release may be lost); end every drum's repeat (a project load) or only the latched ones (the latch went off). The
 * stops may run in any task (single stores). The Repeat page (page.c draws it while a drum's page is open): a pad's
 * pick (pads 0-15), and its LEDs. Main task: a tick of the arpeggiator's clock (defer: the sequencer's tick) and the
 * heartbeat, which send every hit. */
void repeat_press(uint32_t d, uint32_t vel);
void repeat_release(uint32_t d);
void repeat_release_all(void);
void repeat_stop_all(void);
void repeat_stop_latched(void);
void repeat_pick(uint32_t pad);
void repeat_draw(uint16_t *out);
void repeat_on_tick(uint32_t defer);
void repeat_on_ms(void);
extern uint32_t arp_tick;           /* arp.c: ticks (24 per quarter note) since the last start, or since power-on */
extern uint8_t arp_start;           /* arp.c: Play started the sequencer; the next heartbeat makes it tick 0 */

/* euclid.c, UI task: the Pattern tools page (spec 2026-10-17-euclidean-design.md). */
#define EUCLID_NOTE_DEFAULT 72u        /* before any pad was played: the root, pad 24's octave */
extern uint8_t euclid_cfg[TRACKS][2]; /* saved: [0] hits (bits 0-4) | velocity (5-6), [1] rotation (0-4) | gate (5-7) */
#define HITS(c0)      ((c0) & 0x1Fu)  /* euclid_cfg's fields, drum_euclid's too (its gate's bits hold the roll) */
#define VEL(c0)       (((c0) >> 5) & 3u)
#define VEL_BITS      0x60u
#define VEL_MEDIUM    1u
#define ROT(c1)       ((c1) & 0x1Fu)
#define GATE(c1)      (((c1) >> 5) & 7u)      /* sixths of a step - 1; 6 = to the next hit (PL13) */
extern const uint8_t euclid_velocity[3];   /* soft, medium (stock's fixed velocity), hard */
extern uint8_t euclid_last[TRACKS];   /* saved (PL14): the track's last played pad, a keyboard pitch */
#define PAD_DICE_R    28u           /* every page of Pattern tools and Melody: dice rhythm / notes */
#define PAD_DICE_N    29u
#define EUCLID_GROOVE 0x80u         /* euclid_cfg[t][0] bit 7: the rhythm comes from melody_groove */
#define GATE_NEXT     6u            /* euclid_cfg[t][1] bits 5-7: "to the next hit" */
#define EUCLID_CURRENT 0xFFu        /* euclid_write_to: the pattern the track plays now */
void euclid_init(void);
uint32_t euclid_write_to(uint32_t t, uint32_t p, uint32_t keep_undo);   /* rewrite pattern p of track t from the settings; 1 when it wrote */
extern uint8_t euclid_undo_at;        /* 1 + (track << 3 | pattern) the Undo copy came from, 0 = none */
void euclid_pick(uint32_t t, uint32_t pad);
void euclid_draw(uint32_t t, uint16_t *out);
void euclid_disarm(void);                        /* also drops the pending action */
void euclid_unarm(void);                         /* a press: as disarm, but a draft's pending re-write stays */
void euclid_release(uint32_t t);                 /* the release that leaves no page pad down: runs the pending write / Undo / draft re-write */
void euclid_stamp(uint32_t pad);                 /* page_on_pad, after a pick: its pending action belongs to this pad's release */
void euclid_saved_fix(void);
int euclid_link_valid(const uint8_t *cfg, const uint8_t *old);   /* CTCtrl link: a candidate euclid_cfg */
void euclid_link_apply(const uint8_t *old);   /* CTCtrl link: after a write, old = euclid_cfg before it */
void euclid_draw_actions(uint32_t t, uint16_t *out);   /* pads 30 / 31: Undo, Write */

/* melody.c, UI task: the Melody page and the generator's settings (spec 2026-10-19-melodic-generator-design.md). */
extern uint8_t melody_cfg[TRACKS][2];   /* [0] order (0-2) | pool (3) | range - 1 (4-5) | accent (6-7); [1] root (0-2) | octave + 2 (3-4) */
extern uint8_t melody_seed[TRACKS][2];  /* [0] rhythm, [1] notes: 8-bit LFSR states, never 0 */
extern const uint8_t melody_accent_col[4];   /* the accent pad's colours: off, first hit, on the beat, every 3rd */
void melody_init(void);
void melody_pick(uint32_t t, uint32_t pad);
void melody_page_draw(uint32_t t, uint16_t *out);
uint32_t melody_dice(uint32_t t, uint32_t which);    /* 0 rhythm, 1 notes: rolls only; 0 when nothing was rolled */
void melody_draw_actions(uint32_t t, uint16_t *out); /* pads 28-31, on every page of Pattern tools and Melody */
void melody_saved_fix(void);
int melody_link_valid(const uint8_t *cfg, const uint8_t *old);   /* CTCtrl link: a candidate melody_cfg */
void melody_link_apply(const uint8_t *old);   /* CTCtrl link: after a write, old = melody_cfg before it */
extern uint8_t melody_draft;                          /* 0, or track + 1 while that track's draft is on (RAM only) */
void melody_draft_start(uint32_t t);                  /* the Write's second press wrote, with a new setting in use */
void melody_draft_end(void);
int melody_in_draft(uint32_t t);                      /* a draft of track t is live: its pattern is euclid_undo_at's */
void melody_after_pick(uint32_t t);                   /* in a draft: the re-write waits for the pad's release */
int melody_new_in_use(uint32_t t);                   /* a setting beyond plain Euclid is on (the Write's second press) */
/* vary.c, UI task: the melody variations' settings (PL14, spec 2026-10-21-melody-variations-design.md), all saved, ITCM.
 * rhythm_cfg[t][0]: second rhythm's hits 0-16 (bits 0-4) | combine (5-7); [1]: second rotation (0-4) | thinning (5-6) |
 * bit 7 spare; [2]: cycle (0-2: 0 whole, 1-4 = 3, 5, 6, 7 steps) | bits 3-7 spare. melody_vary[t]: ties (0-1) | octave
 * jumps (2-3), amounts 0 off, 1 1/4, 2 1/3, 3 1/2 | bits 4-7 spare. page_sub[t]: the two-page features' second page. */
#define R2_HITS(r0)     ((r0) & 0x1Fu)
#define R2_HITS_BITS    0x1Fu
#define R2_COMBINE(r0)  (((r0) >> 5) & 7u)
#define R2_COMBINE_BITS 0xE0u
#define R2_ROT(r1)      ((r1) & 0x1Fu)
#define R2_ROT_BITS     0x1Fu
#define R2_THIN(r1)     (((r1) >> 5) & 3u)
#define R2_SPARE1       0x80u
#define R2_CYCLE(r2)    ((r2) & 7u)
#define R2_SPARE2       0xF8u
#define VARY_TIES(v)    ((v) & 3u)
#define VARY_JUMPS(v)   (((v) >> 2) & 3u)
#define VARY_SPARE      0xF0u
#define COMBINE_OFF     0u
#define COMBINE_BOTH    1u          /* a & b */
#define COMBINE_EITHER  2u          /* a | b */
#define COMBINE_ONE     3u          /* a ^ b: one, not both */
#define COMBINE_FIRST   4u          /* a & ~b: the first without the second */
#define COMBINE_ACCENT  5u          /* a, accents on a & b */
#define PAGE_SUB_TOOLS  1u          /* page_sub bit 0: Pattern tools on its page 2 (page.c: bit = slot - PAGE_TOOLS) */
#define PAGE_SUB_MELODY 2u          /* bit 1: Melody on Phrasing */
extern uint8_t rhythm_cfg[TRACKS][3];
extern uint8_t melody_vary[TRACKS];
extern uint8_t page_sub[TRACKS];
void vary_init(void);
void vary_saved_fix(void);
int vary_link_valid(const uint8_t *cand, const uint8_t *old);   /* CTCtrl link: whole candidate / old payloads */
void vary_link_apply(const uint8_t *old);   /* CTCtrl link: after a write, old = the payload before it */
/* The second pages (PL14): Pattern tools 2 (the second rhythm, rotate, combine, thinning) and Phrasing (ties, octave
 * jumps); pads 29-32 are the shared actions (euclid_pick). */
void tools2_pick(uint32_t t, uint32_t pad);
void tools2_draw(uint32_t t, uint16_t *out);
void phrasing_pick(uint32_t t, uint32_t pad);
void phrasing_draw(uint32_t t, uint16_t *out);
/* Track t's current pattern (0 without a record) and the steps it plays: first .. first + n - 1. */
uint8_t *euclid_target(uint32_t t, uint32_t *n, uint32_t *first);
uint32_t euclid_hits(uint32_t t, uint32_t n);        /* track t's final rhythm over n steps (bit i: step i): first rhythm
                                                     * (Euclid or groove, over the cycle), combine, thinning (PL14) */
uint32_t euclid_second(uint32_t t, uint32_t n);      /* the second rhythm alone (Euclid, its own rotation mod n) */
uint32_t euclid_cycle(uint32_t t, uint32_t n);       /* the cycle's steps c: n when there is none or c >= n */
uint32_t euclid_line(uint32_t t, const melody_pool_t *pool, uint32_t hits, uint8_t *out);   /* the line as written:
                                                     * out[h] = hit h's note (ties, jumps); returns the tied hits */
void euclid_pool(uint32_t t, melody_pool_t *pool);  /* track t's line pool from its Melody settings (pn 0: unplayable root) */

/* The settings of track t (0-7): a note track's arrays, or the drum's at t - DRUM_FIRST (PL17). The rhythm code reaches
 * the settings only through these; the note-only arrays are never indexed with t >= TRACKS. */
static inline uint8_t *tools_euclid(uint32_t t) { return t < TRACKS ? euclid_cfg[t] : drum_euclid[t - DRUM_FIRST]; }
static inline uint8_t *tools_rhythm(uint32_t t) { return t < TRACKS ? rhythm_cfg[t] : drum_rhythm[t - DRUM_FIRST]; }
static inline uint8_t *tools_seed(uint32_t t) { return t < TRACKS ? &melody_seed[t][0] : &drum_seed[t - DRUM_FIRST]; }
