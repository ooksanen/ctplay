/* chord: a Note-view pad (Synth 1 / 2, MIDI 1 / 2) plays a chord built in the project's scale.
 * Specs: docs/specs/2026-10-11-chord-v1-design.md, 2026-10-12-strum-design.md.
 *
 * Stock plays the pad's own note. This feature sends the chord's other notes through the view's sink with the pad as
 * their source, remembers them, and ends them at stock's release handler for the pad (pad release, or stock releasing
 * every held pad when the view is left), before it decides whether the pad still owns a note: it skips the note-off when
 * another pad took the same pitch or a held step owns it. The router owns each pitch by source pad, so overlapping chords
 * never leave a note on.
 *
 * Re-sound (PL05): the router owns each pitch by the pad that last sent it, so a chord's release ends the notes it shares
 * with a chord still held, if it took them. A release first asks the router which of its pitches it owns, ends its notes,
 * then sends each owned pitch another held chord of the track still sounds again from that chord's pad (resound()).
 *
 * Strum: with the track's strum on, the press only fills a held entry (the other notes sorted rising); the Main task's
 * 1 ms heartbeat (chord_on_ms) sends them one by one and ends them once the pad's release marked the entry. Only the
 * heartbeat calls the sink for a strummed entry's own notes. The UI task writes a free entry (count last) and the released
 * flag, the heartbeat `sent`, `wait`, `drop`, count = 0 and, when it leaves a tone out, `notes[sent ..]` and count - 1
 * (never to 0; the UI task reads only `notes[0 .. sent)` and count != 0): never the same field. The heartbeat never
 * writes `flags`. Either task may re-sound another entry's notes; only the UI task marks an entry released or frees a
 * one-burst entry (count = 0 before its note-offs), so resound() checks its owner again after each note-on.
 * Exact guarantee: the heartbeat reads `flags` once per entry. If the pad is released between that read and its
 * note_sink_on, one note-on can follow the release; the next heartbeat (<= 1 ms later) ends it. A note-on never follows
 * its own note-off, and nothing sticks.
 *
 * Falling strum (PL08): notes[] fall and the pad's own note sounds in its place among them, sent by the heartbeat too
 * (the press is taken: stock plays nothing); `sent` counts it, and its position is the number of notes[] above it
 * (derived, never stored: a left-out tone is never sent yet, so the derivation stays right while the heartbeat shifts
 * notes[]). The heartbeat ends it with the others.
 *
 * Pattern strum (PL19), on an active track (pstrum_mode: Played or Written with the strum on): a rising strum pressed
 * while recording (pstrum_recording, read once at the press) takes the press too (HELD_OWN_ROOT): the heartbeat sends
 * the pad's own note first, then notes[] rising, and ends the pad's note first, then the others, so every note of the
 * strum is the heartbeat's (at most 1 ms after stock's moment) and the recorder's own data can tell its notes
 * (pstrum_rec.c). `sent` counts the pad's note (position 0). Not recording, a rising strum keeps PL18's path (stock
 * sends the pad's note: its pitch held for pad-first step entry). Written (HELD_TICKS): `wait` counts the sequencer's
 * ticks (arp_tick, also stopped at the project's tempo), WRITTEN_GAP apart; a heartbeat takes the ticks since the last
 * one at once (several: one note a heartbeat); with stock's pad note at the press, the first wait also counts the
 * ticks the next heartbeat reads from before the press. Off tracks and falling strums take PL18's paths; too_tight
 * sees PL18's rising count (n - sent is the same with the pad's note counted). */
#include "slim.h"
#include "stock.h"
#include "chord_math.h"
#include "chord_held.h"
#include "roll_math.h"

#define NOTE_VIEW_VT  0x0805A064u   /* Note view vtable (all four tracks) */
#define SINK_VT       0x0805BF54u   /* its sink's vtable */
#define VIEW_SINK     0x18u         /* view + 0x18: sink */
#define VIEW_KBD      0x38u         /* view + 0x38: keyboard */
#define KBD_TABLE     0x14u         /* keyboard + 0x14 + idx: pitch (root-relative, +12) */
#define KBD_SCALE     0x0Cu         /* keyboard + 0x0C: scale object; its mask at + 4 */
#define KBD_KEY       0x10u         /* keyboard + 0x10: -> the project root byte (0-11) */
#define VIEW_PAD_HELD 0x40u         /* view + 0x40 + pad: 0 = stock's release will not end the pad's note (0x0804ACD4) */
#define SINK_TRACK    0x0Cu         /* sink + 0x0C: track 0-3 */
#define CONTROLLER       0x20040B10u   /* stock.h `controller`; a fixed address, as the header declares it one byte long */
#define TRACK_CONTAINER  0x20040DB8u   /* stock.h `track_container` */
#define CTRL_SHIFT_STORE 0x0Cu      /* controller + 0x0C: parameter store; parameter 0 = Shift held */
#define CTRL_ACTIVE      0x6Cu      /* controller + 0x6C: active view */
#define CONT_MODE        0x18Cu     /* track container + 0x18C: 1 Note view, 6 Note view expanded */
#define CONT_VIEWS       0x18u      /* track container + 0x18 + 4 t: Note view of track t */
#define MODE_NOTE        1u
#define MODE_NOTE_WIDE   6u
#define PALETTE_FIRST    16u        /* pads 17-32 (0-based 16-31): keys in both Note views */
#define VS               0x200067FCu /* stock.h voice_state: the voice decision's state (fixed address, one byte declared) */
#define VS_SYNTH         0x04u
#define VS_FIRST         0x10u      /* the synth's first / last voice */
#define VS_LAST          0x11u
#define SLOTS            0x20005F64u /* stock.h voice_slots: 12 x 16 B, state word at + 4 */
#define VOICES           12u
#define READ_ADDR        0x36u      /* X:$36 + synth: further voices of the patch that fit, 0x10000 per voice */
#define ROOM_FLOOR       0x10000u   /* one more voice fits */
#define STOCK_LIMIT      0x14000u   /* stock starts a voice only with 1.25 voices of room */
#define ROOM_FLOOR4      0x1000u    /* ROOM_FLOOR in the >> 4 units of chord_room_* */
#define ROOM_STEP_MIN    0x0800u    /* half a voice: a smaller drop between two notes is taken as this */
#define ROOM_STEP_ONE    0x1000u    /* one voice: the reading's own unit, when only one reading is in the chord */
#define ROUTER           0x2003ECDCu /* stock.h note_router: one owner pad per note and track */
#define ROUTER_VT        0x0805B840u
#define RT_FIRST         0x98u      /* router + 0x98 + 3 t: the first note of track t's table */
#define RT_TABLE         0xD58u     /* router + 0xD58 + 12 t: -> track t's pad notes, 2 B each {pitch that took it, pad} */
#define PREVIEW          0x20u      /* the Note view's step preview: its source pad (0x0804B4C8) */


const uint8_t STRUM_GAP[4] = {0u, 80u, 40u, 20u};   /* ms between strummed notes: off, slow, medium, fast (PL19: pstrum.c too) */

uint8_t chord_settings[TRACKS];     /* global: the tests set it directly */
uint8_t chord_voice[TRACKS] SLIM_ITCM(chord_voice);   /* PL15: row-2 shape | voice leading, see chord_held.h */
/* PL15: the latest chord pressed per track, for voice leading: the pad's pitch and the notes play() built (count 0 = none). */
uint8_t repeat_cfg[2] SLIM_ITCM(repeat_cfg);          /* PL16: the kit's note repeat, see chord_held.h */
uint8_t drum_page[4] SLIM_ITCM(drum_page);            /* PL16: per drum the last page */
uint8_t chord_prev[TRACKS][6] SLIM_ITCM(chord_prev);
uint8_t chord_prev_n[TRACKS] SLIM_ITCM(chord_prev_n);
uint8_t chord_rootless;             /* bit t: track t's bass is rootless over bass (with the settings' bass bit) */
uint8_t chord_strum;                /* global: 2 bits per track (0 off, 1-3 slow-fast); the tests set it directly */
uint8_t chord_strum_down;           /* bit t: track t strums falling */
uint8_t chord_mono;                 /* bit t: track t records mono */
uint8_t chord_step SLIM_ITCM(chord_step);   /* bit t: track t writes chords in step entry (PL18) */
uint8_t chord_pstrum SLIM_ITCM(chord_pstrum);   /* 2 bits per track: 0 off, 1 played, 2 written (PL19) */
uint8_t chord_order[TRACKS];        /* press counter per track: held_t.order ("as played") */
uint8_t chord_arp[TRACKS][2];       /* per track: the arpeggiator's settings (chord_held.h); the tests set it directly */
uint8_t chord_sending;              /* track + 1 while chord.c sends a chord note (the floor applies to it), else 0 */
uint16_t chord_room_last[2], chord_room_prev[2];   /* per synth: the last two readings >> 4, saturated (the fallback) */
uint8_t chord_room_n[2];            /* per synth: readings since the last strummed 5-note press (saturates at 255) */
held_t held[HELD] SLIM_ITCM(held);   /* ITCM (PL09) */
static uint32_t consumed;           /* pads whose press picked a palette option: their release sends nothing */
static uint32_t beat_tick SLIM_ITCM(beat_tick);   /* PL19: arp_tick at the last heartbeat (HELD_TICKS waits) */

void chord_init(void)
{
    memset(chord_settings, 0, sizeof chord_settings);
    memset(chord_voice, 0, sizeof chord_voice);
    memset(repeat_cfg, 0, sizeof repeat_cfg);
    memset(drum_page, 0, sizeof drum_page);
    memset(chord_prev, 0, sizeof chord_prev);
    memset(chord_prev_n, 0, sizeof chord_prev_n);
    chord_rootless = 0;
    chord_strum = 0;
    chord_strum_down = 0;
    chord_mono = 0;
    chord_step = 0;
    chord_pstrum = 0;
    trig_init();
    memset(chord_order, 0, sizeof chord_order);
    memset(chord_arp, 0, sizeof chord_arp);
    for (uint32_t t = 0; t < TRACKS; t++)
        chord_arp[t][1] = GATE_DEFAULT << 2;
    chord_sending = 0;
    memset(chord_room_last, 0, sizeof chord_room_last);
    memset(chord_room_prev, 0, sizeof chord_room_prev);
    memset(chord_room_n, 0, sizeof chord_room_n);
    memset(held, 0, sizeof held);
    consumed = 0;
    page_init();
    euclid_init();
    melody_init();
    vary_init();
    drum_tools_init();
    arp_init();
    mono_init();
    pstrum_init();
    pstrum_rec_init();
    step_entry_init();
    beat_tick = 0;
}

/* The view's sink, or 0 when `view` is not a Note view with the expected sink. */
uint8_t *chord_note_sink(void *view)
{
    if (*(volatile uint32_t *)view != NOTE_VIEW_VT)
        return 0;
    uint8_t *sink = *(uint8_t **)((uint8_t *)view + VIEW_SINK);
    if (!sink || *(volatile uint32_t *)sink != SINK_VT || sink[SINK_TRACK] >= TRACKS)
        return 0;
    return sink;
}

/* Track t's Note view's sink (the container keeps one Note view per track), or 0. */
uint8_t *chord_track_sink(uint32_t track)
{
    void *view = *(void **)((uint8_t *)TRACK_CONTAINER + CONT_VIEWS + 4u * track);
    uint8_t *sink = view ? chord_note_sink(view) : 0;
    return sink && sink[SINK_TRACK] == track ? sink : 0;
}

/* A chord note: marked, so the floor applies to its voice decision (synchronous inside note_sink_on). */
void chord_send_on(uint8_t *sink, uint32_t track, uint32_t note, uint32_t vel, uint32_t pad)
{
    chord_sending = (uint8_t)(track + 1u);
    note_sink_on(sink, note, vel, pad);
    chord_sending = 0u;
}

/* The router's entry for `pitch` on the track, 0 when the router is not the one we know. Chord notes and pad notes are
 * in the scale, so the router's scale snap (0x080408C6) leaves them as they are. */
static volatile uint8_t *rt_entry(uint32_t track, uint32_t pitch)
{
    if (*(volatile uint32_t *)ROUTER != ROUTER_VT)
        return 0;                                   /* not the router we know: no re-sound, as PL04 */
    uint32_t first = *(volatile uint8_t *)(ROUTER + RT_FIRST + 3u * track);
    if (pitch < first)
        return 0;
    return *(uint8_t **)(ROUTER + RT_TABLE + 12u * track) + 2u * (pitch - first);
}

/* Does `pad` own `pitch` on the track (the router ends a note only for the pad that last sent it)? */
static int owns(uint32_t track, uint32_t pitch, uint32_t pad)
{
    const volatile uint8_t *e = rt_entry(track, pitch);
    return e && e[0] == pitch && e[1] == pad;
}

/* A falling strum's notes[] above the pad's own note: the position of that note among the entry's. */
static uint32_t above_root(const held_t *h)
{
    uint32_t r = 0;
    for (uint32_t k = 0; k < h->count; k++)
        r += h->notes[k] > h->root;
    return r;
}

/* The entry's other notes sounding: notes[0 .. lit_others). */
static uint32_t lit_others(const held_t *h)
{
    if (!(h->flags & HELD_STRUM))
        return h->count;
    if (h->flags & HELD_OWN_ROOT)                   /* PL19: the pad's own note went first */
        return h->sent - (h->sent > 0u);
    if (!(h->flags & HELD_FALLING))
        return h->sent;
    return h->sent - (h->sent > above_root(h));
}

/* Has the entry's pad note sounded (always, but for a falling strum, or a PL19 one with its own note, before its turn)? */
static int root_lit(const held_t *h)
{
    if (h->flags & HELD_OWN_ROOT)
        return h->sent > 0u;
    return !(h->flags & HELD_FALLING) || h->sent > above_root(h);
}

/* Is the strum's next note the pad's own (a falling strum at its place; PL19, HELD_OWN_ROOT: first)? */
static int root_next(const held_t *h)
{
    if (h->flags & HELD_OWN_ROOT)
        return h->sent == 0u;
    return (h->flags & HELD_FALLING) && h->sent == above_root(h);
}

/* `gone` (being freed) owned `p`, which is ending: the first other held chord of the track still sounding it (its own
 * pad's note or one it sent) sends it again from its pad at its velocity, so the router hands the note to that pad. In
 * the Main task the UI task may release or free that chord meanwhile; its release has then passed, so the note is ended
 * here. */
static void resound(uint8_t *sink, const held_t *gone, uint32_t p)
{
    for (uint32_t i = 0; i < HELD; i++) {
        held_t *h = &held[i];
        if (h == gone || !h->count || h->track != gone->track || (h->flags & (HELD_RELEASED | HELD_ARP)))
            continue;
        uint32_t lit = lit_others(h), has = h->root == p && root_lit(h);
        for (uint32_t k = 0; k < lit; k++)
            has |= h->notes[k] == p;
        if (!has)
            continue;
        uint32_t pad = h->pad;
        chord_send_on(sink, h->track, p, h->vel, pad);
        if (!h->count || (h->flags & HELD_RELEASED) || h->pad != pad)
            note_sink_off(sink, p, pad);
        return;
    }
}

/* Bit k: `pad` owns notes[k] of the entry (asked before its note-offs, which clear the router's entries). */
static uint32_t owned(const held_t *h, uint32_t n)
{
    uint32_t own = 0;
    for (uint32_t k = 0; k < n; k++)
        own |= (uint32_t)owns(h->track, h->notes[k], h->pad) << k;
    return own;
}

/* Free the track's arpeggio entries (UI task): all, or with `released` only the released (latched) ones, and then
 * only when none of the track's arpeggio pads is still held. */
static void unlatch(uint32_t track, uint32_t released)
{
    for (uint32_t i = 0; i < HELD; i++)
        if (released && held[i].count && (held[i].flags & HELD_ARP) && held[i].track == track
            && !(held[i].flags & HELD_RELEASED))
            return;
    for (uint32_t i = 0; i < HELD; i++)
        if (held[i].count && (held[i].flags & HELD_ARP) && held[i].track == track
            && (!released || (held[i].flags & HELD_RELEASED)))
            held[i].count = 0;
}

void arp_free(uint32_t track, uint32_t released)
{
    unlatch(track, released);
}

/* After a project load wrote the saved settings (features/saved, UI task): a value no build of this layout writes
 * takes its default, track by track (so none is left for the CTCtrl link to refuse: chord_link.c); then the arpeggios end as their settings say (a pattern now off: all its entries;
 * every track: the latched notes of the previous project, once no pad of the track is held). Held entries keep their
 * own notes and flags, so releases end what they started. */
void chord_saved_fix(void)
{
    memset(chord_prev_n, 0, sizeof chord_prev_n);   /* PL15: a loaded project leads from nothing */
    if (REPEAT_RATE(repeat_cfg[0]) > REPEAT_RATE_MAX)   /* PL16: the rate has eight values */
        repeat_cfg[0] &= (uint8_t)~0xFu;
    repeat_cfg[1] = 0;
    for (uint32_t d = 0; d < 4; d++) {
        drum_page[d] &= 0xFu;
        if (!drum_slot_exists(DRUM_SLOT(drum_page[d])))
            drum_page[d] &= DRUM_SUB;   /* no page there (an alpha project's Repeat, slot 0): Repeat, the sub kept */
    }
    repeat_stop_all();                              /* a loaded project repeats nothing it did not save as held */
    if (chord_rootless & ~0xFu)
        chord_rootless = 0;
    if (chord_strum_down & ~0xFu)
        chord_strum_down = 0;
    if (chord_mono & ~0xFu)
        chord_mono = 0;
    if (chord_step & ~0xFu)
        chord_step = 0;
    for (uint32_t t = 0; t < TRACKS; t++)           /* PL19: a field of 3 means nothing: the whole byte takes its default */
        if (PSTRUM_OF(t) > PSTRUM_WRITTEN) {
            chord_pstrum = 0;
            break;
        }
    trig_saved_fix();                               /* PL20: trig_mark is 1 or 0 */
    for (uint32_t t = 0; t < TRACKS; t++) {
        if (CHORD_SPREAD(chord_settings[t]) > SPREAD_WIDE)
            chord_settings[t] = 0;
        if (VOICE_SHAPE2(chord_voice[t]) > 5u)      /* PL15: row-2 shape 6-15: no pad makes it */
            chord_voice[t] &= (uint8_t)~0xFu;
        chord_voice[t] &= VOICE_BITS;
        if (!CHORD_BASS(chord_settings[t]))         /* rootless is a bass mode: the bass cycle never sets it alone */
            chord_rootless &= (uint8_t)~(1u << t);
        uint8_t *a = chord_arp[t];
        if (ARP_MOD(a[0]) > MOD_DOTTED)             /* modifier 3: no pad sets it (it plays as none) */
            a[0] &= (uint8_t)~(3u << 5);
        if (ARP_RATE(a[0]) == 3u && ARP_MOD(a[0]) == MOD_DOTTED)
            a[0] = 0;                               /* dotted 1/32 is off the grid (page.c) */
        if ((a[1] & ~0x1Fu) || ARP_GATE(a[1]) > GATE_LEGATO)
            a[1] = GATE_DEFAULT << 2;
        if (!page_exists(page_slot[t]))
            page_slot[t] = PAGE_CHORDS;
        if (page_quick[t] > PAGE_ARP)               /* Keys has no quick half */
            page_quick[t] = PAGE_CHORDS;
        if (ARP_PATTERN(a[0]) == ARP_OFF)
            arp_free(t, 0);
        arp_free(t, 1);
    }
    euclid_saved_fix();
    melody_saved_fix();
    vary_saved_fix();
    drum_tools_saved_fix();
    step_entry_init();                              /* PL19: a load's patterns: pending step-entry spills dropped */
}

static void release(uint8_t *sink, uint32_t track, uint32_t pad)
{
    for (uint32_t i = 0; i < HELD; i++) {
        held_t *h = &held[i];
        if (!h->count || h->track != track || h->pad != pad)
            continue;
        if (h->flags & HELD_ARP) {                  /* nothing of its own sounds: the arpeggiator reads the entry */
            if (chord_arp[track][0] & ARP_LATCH) {
                uint32_t primask = slim_irq_save();
                h->flags |= HELD_RELEASED;          /* latched until the next press after every pad was let go */
                slim_irq_restore(primask);
            } else {
                h->count = 0;
                unlatch(track, 1);                  /* latch went off while a pad was held: the latched notes go now */
            }
            continue;
        }
        /* The pad's own note: stock ends it after this hook, unless it cleared the pad's slot (another pad took the
         * pitch; a re-sound gave it back). Owned, it is re-sounded now, so stock's late note-off finds another owner. */
        uint32_t root = !(h->flags & (HELD_FALLING | HELD_OWN_ROOT)) && owns(track, h->root, pad);   /* else the heartbeat's */
        uint8_t *view = *(uint8_t **)((uint8_t *)TRACK_CONTAINER + CONT_VIEWS + 4u * track);
        if (h->flags & HELD_STRUM) {                /* the entry's own flag, not the track's current setting */
            uint32_t primask = slim_irq_save();
            h->flags |= HELD_RELEASED;              /* the heartbeat ends what it sent */
            slim_irq_restore(primask);
        } else {
            uint32_t n = h->count, own = owned(h, n);
            h->count = 0;                           /* before the note-offs: resound() in the Main task checks it */
            for (uint32_t k = 0; k < n; k++)
                note_sink_off(sink, h->notes[k], pad);
            for (uint32_t k = 0; k < n; k++)
                if (own >> k & 1u)
                    resound(sink, h, h->notes[k]);
        }
        if (root) {
            if (view && !view[VIEW_PAD_HELD + pad])
                note_sink_off(sink, h->root, pad);
            resound(sink, h, h->root);
        }
    }
}

static held_t *free_entry(void)
{
    for (uint32_t i = 0; i < HELD; i++)
        if (!held[i].count)
            return &held[i];
    return 0;
}

/* Track t's settings as chord_notes() takes them: the settings byte plus CHORD_ROOTLESS in bit 8. */
uint32_t chord_track_settings(uint32_t t)
{
    return chord_settings[t] | ((uint32_t)(chord_rootless >> t) & 1u) << 8 | VOICE_SHAPE2(chord_voice[t]) << 9;
}

void chord_pick_shape(uint32_t t, uint32_t index)
{
    if (index < 8u) {
        chord_settings[t] = (uint8_t)((chord_settings[t] & ~7u) | index);
        chord_voice[t] &= (uint8_t)~0xFu;           /* any row-1 pick, off (0) included, ends the row-2 shape */
    } else {
        chord_settings[t] &= (uint8_t)~7u;
        chord_voice[t] = (uint8_t)((chord_voice[t] & ~0xFu) | (index - 7u));
    }
}

static uint32_t vs(uint32_t off)
{
    return *(volatile uint8_t *)(VS + off);
}

/* A voice of the deciding synth that stock's pickers call free (state word high half 0, as at 0x080216F0). */
static int has_free_voice(void)
{
    for (uint32_t v = vs(VS_FIRST); v <= vs(VS_LAST) && v < VOICES; v++)
        if (!(*(volatile uint32_t *)(SLOTS + 16u * v + 4u) >> 16))
            return 1;
    return 0;
}

/* Index + 1 of a 5-note chord's least needed tone among its other notes (rising): the tone with the 5th's pitch
 * class, else the 9th's; 0 = none (fewer notes, or neither found). */
static uint32_t droppable(const uint8_t *notes, uint32_t n, uint32_t root, uint32_t mask)
{
    if (n != 4u)
        return 0u;
    const uint32_t want[2] = {chord_degree_class(root, mask, 4u), chord_degree_class(root, mask, 8u)};
    for (uint32_t w = 0; w < 2u; w++)
        for (uint32_t k = 0; k < n; k++)
            if (notes[k] % 12u == want[w] && want[w] != root % 12u)
                return k + 1u;
    return 0u;
}

/* Would the chord's last note find under one voice of room? `remaining` = notes still to sound, this one included.
 * From the synth's readings since the press (the last taken before the previous note's voice started): two or more,
 * the drop between the last two (none: nothing to estimate from, no); only the pad note's, one voice per note; none
 * (no voice decision ran, e.g. a MIDI track), no. */
static int too_tight(uint32_t synth, uint32_t remaining)
{
    uint32_t n = chord_room_n[synth], last = chord_room_last[synth], prev = chord_room_prev[synth], step;
    if (!n)
        return 0;
    if (n == 1u) {
        step = ROOM_STEP_ONE;
    } else {
        if (prev <= last)
            return 0;
        step = prev - last;
        if (step < ROOM_STEP_MIN)
            step = ROOM_STEP_MIN;
    }
    return last < ROOM_FLOOR4 + remaining * step;   /* last - remaining x step < floor */
}

uint32_t chord_build(uint32_t track, uint32_t root, uint32_t mask, uint32_t key, uint8_t *out)
{
    uint32_t s = chord_track_settings(track) | key << 16, lead = VOICE_LEAD(chord_voice[track]);
    if (lead)                                       /* voice leading: the inversion that moves least from the last chord */
        s = (s & ~(3u << 3)) | chord_lead(root, mask, s, chord_prev[track], chord_prev_n[track], lead) << 3;
    uint32_t n = chord_notes(root, mask, s, out);
    chord_prev[track][0] = (uint8_t)root;           /* every press that builds a chord is the next one's "last chord" */
    for (uint32_t k = 0; k < n && k < 5u; k++)
        chord_prev[track][1u + k] = out[k];
    chord_prev_n[track] = (uint8_t)(1u + (n < 5u ? n : 5u));
    return n;
}

/* A press. Returns SLIM_HANDLED for an arpeggio, falling-strum or (PL19) HELD_OWN_ROOT press (stock plays nothing: the
 * arpeggiator or the heartbeat plays the pad's note). */
static int play(void *view, uint8_t *sink, uint32_t track, uint32_t pad, uint32_t vel)
{
    release(sink, track, pad);                      /* a pad pressed twice without a release: end the old chord */
    uint8_t *kbd = *(uint8_t **)((uint8_t *)view + VIEW_KBD);
    uint32_t idx = note_pad_index(view, pad);
    if (kbd_pad_ignored(kbd, idx))
        return SLIM_PASS;                           /* stock plays nothing for this pad: neither do we */
    uint32_t root = kbd[KBD_TABLE + idx];
    euclid_last[track] = (uint8_t)root;             /* the Pattern tools page writes the last played pad */
    uint32_t s = chord_track_settings(track), arp = ARP_PATTERN(chord_arp[track][0]) != ARP_OFF;
    if (!arp && !CHORD_HAS_SHAPE(s) && !CHORD_BASS(s))
        return SLIM_PASS;
    uint32_t mask = *(volatile uint32_t *)(*(uint8_t **)(kbd + KBD_SCALE) + 4u);
    uint32_t key = **(volatile uint8_t **)(kbd + KBD_KEY);
    if (arp)
        unlatch(track, 1);                          /* latch: a press after every pad was let go starts anew */
    held_t *h = free_entry();
    if (!h)
        return arp ? SLIM_HANDLED : SLIM_PASS;      /* table full: arpeggio presses sound nothing, chords the pad only */
    uint32_t n = 0;
    if (CHORD_HAS_SHAPE(s) || CHORD_BASS(s))
        n = chord_build(track, root, mask, key, h->notes);
    if (!n && !arp)
        return SLIM_PASS;
    h->track = (uint8_t)track;
    h->pad = (uint8_t)pad;
    h->root = (uint8_t)root;
    h->vel = (uint8_t)vel;
    h->order = ++chord_order[track];
    if (arp) {                                      /* the arpeggiator (Main task) sounds it */
        roll_order(h->notes, n, 0);
        h->flags = HELD_ARP;
        uint32_t primask = slim_irq_save();
        h->count = (uint8_t)(ARP_LIVE | n);
        slim_irq_restore(primask);
        return SLIM_HANDLED;
    }
    uint32_t speed = STRUM_OF(track), down = speed && STRUM_DOWN(track), mode = pstrum_mode(track);
    uint32_t own = mode && !down && pstrum_recording();   /* PL19: the heartbeat sends the pad's note too */
    if (speed) {                                    /* the heartbeat sends them */
        roll_order(h->notes, n, 0);                 /* rising: droppable() and h->drop count from the lowest */
        h->sent = 0;
        if (down || own)
            h->wait = 0u;                           /* falling, PL19 own root: the first note on the next heartbeat */
        else if (mode == PSTRUM_WRITTEN) {          /* ticks from the press: the next heartbeat also takes the earlier ones */
            uint32_t now = arp_tick, early = now >= beat_tick ? now - beat_tick : now;   /* Play resets the tick */
            h->wait = (uint8_t)(WRITTEN_GAP[speed] + (early < 8u ? early : 8u));
        } else
            h->wait = STRUM_GAP[speed];
        h->drop = (uint8_t)droppable(h->notes, n, root, mask);
        if (down) {
            roll_order(h->notes, n, 1);             /* the falling strum: highest first */
            if (h->drop)
                h->drop = (uint8_t)(n + 1u - h->drop);   /* the same tone, falling */
        }
        if (h->drop && track < 2u)
            chord_room_n[track] = 0u;               /* count this chord's readings: the next note's comes next */
        h->flags = (uint8_t)(HELD_STRUM | speed << 2 | (down ? HELD_FALLING : 0u) | (own ? HELD_OWN_ROOT : 0u)
                             | (mode == PSTRUM_WRITTEN ? HELD_TICKS : 0u));
    } else {
        h->flags = 0;
    }
    /* A freed entry keeps its stale flags (the heartbeat never writes them), and the compiler may reorder plain stores:
     * `count` must be the last store, behind a barrier, so the heartbeat sees the entry only now, complete. */
    uint32_t primask = slim_irq_save();
    h->count = (uint8_t)n;
    slim_irq_restore(primask);
    if (speed)
        return down || own ? SLIM_HANDLED : SLIM_PASS;
    for (uint32_t k = 0; k < n; k++)
        chord_send_on(sink, track, h->notes[k], vel, pad);
    return SLIM_PASS;
}

int chord_shift_held(void)
{
    void *store = *(void **)((uint8_t *)CONTROLLER + CTRL_SHIFT_STORE);
    return *param_get(store, 0u) != 0u;
}

int chord_on_pad(void *view, uint32_t pad, uint32_t vel, uint32_t *ret)
{
    (void)ret;
    uint8_t *sink = chord_note_sink(view);
    if (!sink || pad >= PADS)
        return SLIM_PASS;
    uint32_t bit = 1u << pad;
    if (pad >= PALETTE_FIRST && chord_shift_held()) {
        page_quick_pad(sink[SINK_TRACK], pad);      /* the quick view (by default the Chords page's shapes) */
        consumed |= bit;
        return SLIM_HANDLED;                        /* a quick-view press plays nothing */
    }
    consumed &= ~bit;                               /* a release lost to a view switch cannot swallow this one */
    return play(view, sink, sink[SINK_TRACK], pad, vel);   /* PASS: stock plays the pad's own note */
}

/* Stock's release handler 0x0804ACC4: every release of a Note-view pad, including the ones that never reach the
 * note-off (another pad took the pitch, or a held step owns it). The consumed bit is handled here only. */
int chord_on_release(void *view, uint32_t pad, uint32_t *ret)
{
    (void)ret;
    uint8_t *sink = chord_note_sink(view);
    if (!sink || pad >= PADS)
        return SLIM_PASS;
    step_spill_release(view, pad);                  /* PL19: a Written step entry's spill, on its pad's release */
    uint32_t bit = 1u << pad;
    if (consumed & bit) {
        consumed &= ~bit;
        return SLIM_HANDLED;                        /* its press sent nothing */
    }
    release(sink, sink[SINK_TRACK], pad);
    return SLIM_PASS;                               /* stock ends (or hands to the held step) the pad's own note */
}

/* Stock's end of the held step's preview 0x0804B00C (the step let go, hook preview_end): it ends the step's notes no pad
 * slot holds, from the preview's source 0x20. Match stock (user, 2026-10-29): stock keeps a held pad's own note, so a
 * note a still-held chord pad of the track sounds stays too, until that pad's release ends it. The router hands each
 * such note the preview owns back to the chord's pad (its owner byte, a few masked instructions, nothing called): stock's
 * note-off then finds another owner, and the pad's release (or the heartbeat's, a strum) ends it. A strum's notes not
 * sent yet are left to stock: the heartbeat sends them from the pad later. The chord is tested again in the masked
 * section (the listener's task is not settled for Play from external MIDI): release() frees or marks it before its
 * note-offs, so a hand-over before that is ended by them and none happens after it. */
int chord_on_preview_end(void *view, uint32_t *ret)
{
    (void)ret;
    uint8_t *sink = chord_note_sink(view);
    if (!sink)
        return SLIM_PASS;
    uint32_t track = sink[SINK_TRACK];
    for (uint32_t i = 0; i < HELD; i++) {
        const held_t *h = &held[i];
        if (!h->count || h->track != track || (h->flags & (HELD_RELEASED | HELD_ARP)))
            continue;
        uint32_t lit = lit_others(h);
        for (uint32_t k = 0; k <= lit; k++) {       /* k == lit: the pad's own note, when it has sounded */
            uint32_t p = k < lit ? h->notes[k] : root_lit(h) ? h->root : 0u;
            volatile uint8_t *e = p ? rt_entry(track, p) : 0;
            if (!e)
                continue;
            const volatile held_t *v = h;           /* read again: a release may have run since the test above */
            uint32_t primask = slim_irq_save();
            if (v->count && !(v->flags & (HELD_RELEASED | HELD_ARP)) && v->track == track && e[0] == p
                && e[1] == PREVIEW)
                e[1] = v->pad;
            slim_irq_restore(primask);
        }
    }
    return SLIM_PASS;
}

/* Stock's note-off 0x0804AF5A, reached only from the release handler: a safety net, it finds nothing after
 * chord_on_release. */
int chord_off_pad(void *view, uint32_t pad, uint32_t *ret)
{
    (void)ret;
    uint8_t *sink = chord_note_sink(view);
    if (!sink || pad >= PADS)
        return SLIM_PASS;
    release(sink, sink[SINK_TRACK], pad);
    return SLIM_PASS;                               /* stock ends the pad's own note */
}

/* A strum note's note-off by the heartbeat (PL19: the recorder may move it, pstrum_rec.c). */
static void strum_off(uint8_t *sink, uint32_t i, uint32_t note, uint32_t own)
{
    uint32_t token = pstrum_rec_off(i, note, own);
    note_sink_off(sink, note, held[i].pad);
    pstrum_rec_off_end(token);
}

/* main_ms (Main task): slot 0 every 1 ms. Each strummed entry sends its next due note, or, once its pad was released,
 * ends the notes it sent and frees the entry. Writes only `sent`, `wait` and `count` of strummed entries. */
int chord_on_ms(uint32_t slot, uint32_t *ret)
{
    (void)ret;
    if (slot != 0u)
        return SLIM_PASS;                           /* slot 1: every 333 ms */
    trig_on_ms();                                   /* PL20: first, so the posted start-overs precede this ms's ticks */
    uint32_t now = arp_tick, ticks = now >= beat_tick ? now - beat_tick : now;   /* PL19: the sequencer's ticks since the
                                                     * last heartbeat; Play resets arp_tick to 0 (arp.c): count from there */
    beat_tick = now;
    pstrum_rec_on_ms();
    for (uint32_t i = 0; i < HELD; i++) {
        held_t *h = &held[i];
        if (!h->count || !(h->flags & HELD_STRUM))
            continue;
        uint8_t *sink = chord_track_sink(h->track);
        if (!sink) {
            /* No sink: notes already sent are abandoned, they cannot be ended without one. Acceptable because the
             * container's per-track Note view slot is fixed, so this is a guard that should never run. */
            h->count = 0;
            continue;
        }
        uint32_t fall = h->flags & HELD_FALLING, first = h->flags & HELD_OWN_ROOT;
        if (h->flags & HELD_RELEASED) {             /* rising, its pad's own note was re-sounded at the release */
            uint32_t n = lit_others(h), own = owned(h, n), root = (fall || first) && root_lit(h);
            uint32_t root_own = root && owns(h->track, h->root, h->pad);
            if (first && root)                      /* PL19: the pad's own note, sent first, ends first */
                strum_off(sink, i, h->root, root_own);
            for (uint32_t k = 0; k < n; k++)
                strum_off(sink, i, h->notes[k], own >> k & 1u);
            if (fall && root)
                strum_off(sink, i, h->root, root_own);
            h->count = 0;
            for (uint32_t k = 0; k < n; k++)
                if (own >> k & 1u)
                    resound(sink, h, h->notes[k]);
            if (root_own)
                resound(sink, h, h->root);
            continue;
        }
        if (h->flags & HELD_TICKS) {                /* PL19, Written: the ticks since the last heartbeat at once */
            if (h->wait) {
                h->wait = (uint8_t)(h->wait > ticks ? h->wait - ticks : 0u);
                if (h->wait)
                    continue;
            }
        } else if (h->wait && --h->wait) {
            continue;
        }
        uint32_t n = h->count + (fall || first ? 1u : 0u);   /* notes to send: falling (PL19: own root), the pad's too */
        if (h->sent < n) {
            uint32_t o = lit_others(h), root = root_next(h);   /* next: notes[o] or the pad's */
            if (!root && h->drop == o + 1u && h->track < 2u && too_tight(h->track, n - h->sent)) {
                for (uint32_t k = o; k + 1u < h->count; k++)          /* leave the tone out: the rest move down */
                    h->notes[k] = h->notes[k + 1u];
                h->count--;                                           /* 4 -> 3: never 0 */
                h->drop = 0u;
                n--;
                root = root_next(h);
            }
            if (h->sent < n) {                                        /* the left-out tone may have been the last */
                uint32_t note = root ? h->root : h->notes[o], c = pstrum_rec_before(h->track);
                chord_send_on(sink, h->track, note, h->vel, h->pad);
                pstrum_rec_sent(i, note, c);                          /* PL19: the recorder's identity of this note */
                h->sent++;
                h->wait = (h->flags & HELD_TICKS) ? WRITTEN_GAP[HELD_SPEED(h->flags)] : STRUM_GAP[HELD_SPEED(h->flags)];
            }
        }
    }
    pstrum_on_ms();                                 /* PL19: a pattern's strummed chords, their late notes */
    arp_on_ms();
    return SLIM_PASS;
}

/* voice_headroom (filter, dsp_locked): inside stock's voice decision, with the DSP lock held. RAM only, no calls.
 * Keeps each synth's last two readings; lets a chord note take a free voice when one more voice fits. */
uint32_t chord_on_headroom(uint32_t core, uint32_t addr, uint32_t result)
{
    uint32_t synth = vs(VS_SYNTH);
    if (core != 0u || synth > 1u || addr != READ_ADDR + synth)
        return result;
    chord_room_prev[synth] = chord_room_last[synth];
    chord_room_last[synth] = (uint16_t)((result >> 4) > 0xFFFFu ? 0xFFFFu : (result >> 4));
    if (chord_room_n[synth] < 0xFFu)
        chord_room_n[synth]++;
    if (chord_sending == synth + 1u && result >= ROOM_FLOOR && result < STOCK_LIMIT && has_free_voice())
        return STOCK_LIMIT;                         /* stock's ARM picker takes the free voice */
    return result;
}

/* The Note view on screen, or 0; `*mode` = MODE_NOTE or MODE_NOTE_WIDE. */
void *chord_visible_view(void *ctrl, uint32_t *mode)
{
    uint8_t *cont = (uint8_t *)TRACK_CONTAINER;
    if (*(void **)((uint8_t *)ctrl + CTRL_ACTIVE) != (void *)cont)
        return 0;
    *mode = cont[CONT_MODE];
    if (*mode != MODE_NOTE && *mode != MODE_NOTE_WIDE)
        return 0;
    uint32_t track = track_of(cont);
    if (track >= TRACKS)
        return 0;
    void *view = *(void **)(cont + CONT_VIEWS + 4u * track);
    return chord_note_sink(view) ? view : 0;
}

/* button_press: the play page's buttons (page.c); everything else goes to stock. */
int chord_on_button(void *ctrl, uint32_t id, uint32_t *ret)
{
    (void)ret;
    return page_on_button(ctrl, id);
}

/* Key pads whose pitch is one of a held chord's other notes take the colour stock gives the chord's own pad. */
static void draw_chords(void *view, uint32_t track, uint32_t mode, uint16_t *out)
{
    uint16_t colour[HELD];                          /* each chord's own pad, as stock drew it */
    uint8_t arp_notes[5];
    uint32_t arp_n = arp_sounding(track, arp_notes), any = arp_n;
    for (uint32_t i = 0; i < HELD; i++) {
        colour[i] = out[held[i].pad];
        any |= held[i].count && held[i].track == track && !(held[i].flags & HELD_ARP);
    }
    if (!any)
        return;
    uint8_t *kbd = *(uint8_t **)((uint8_t *)view + VIEW_KBD);
    uint32_t first = mode == MODE_NOTE_WIDE ? 0u : PALETTE_FIRST;    /* the 2-row view: pads 1-16 are steps */
    for (uint32_t p = first; p < PADS; p++) {       /* each visible pad's pitch once, against every held chord */
        uint32_t idx = note_pad_index(view, p);
        if (kbd_pad_ignored(kbd, idx))
            continue;
        uint32_t pitch = kbd[KBD_TABLE + idx];
        for (uint32_t i = 0; i < HELD; i++) {
            held_t *h = &held[i];
            if (!h->count || h->track != track || (h->flags & HELD_ARP))
                continue;
            uint32_t lit = lit_others(h);
            for (uint32_t k = 0; k < lit; k++)
                if (h->notes[k] == pitch)
                    out[p] = colour[i];
        }
        for (uint32_t k = 0; k < arp_n; k++)       /* the arpeggio's sounding notes */
            if (arp_notes[k] == pitch)
                out[p] = COL_WHITE;
    }
}

void chord_on_leds(void *ctrl, uint16_t *out)
{
    trig_fill_stop();                               /* PL20: Stop disarms every FILL, a page open or not */
    page_shift_leds(ctrl, out);
    if (page_draw(ctrl, out))
        return;
    trig_draw(ctrl, out);                           /* PL20: row 4 of a probability view */
    uint32_t mode;
    void *view = chord_visible_view(ctrl, &mode);
    if (!view)
        return;
    uint32_t track = chord_note_sink(view)[SINK_TRACK];
    if (chord_shift_held())
        page_quick_draw(track, out);
    else
        draw_chords(view, track, mode, out);
}
