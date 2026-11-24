/* The play pages (spec 2026-10-17-play-pages-design.md section 1): Shift + Synth 1 / 2 or MIDI 1 / 2 opens the track's
 * last page (switching to its Note view first, as stock's track button does); ▲ ▼ step pages; Shift held on a page
 * shows the table of contents on row 4; the track's button alone, Note, Mixer, FX or Preset close it. UI task only.
 * Pages: Chords, Arp, Keys (PL08, spec 2026-10-17-small-features-design.md section 4), Pattern tools (PL11, euclid.c),
 * Melody (PL13, melody.c). PL14 (spec 2026-10-21-melody-variations-design.md, "Pages that span two screens"): Pattern
 * tools and Melody have a second page each (Pattern tools 2, Phrasing; vary.c). A page is (slot, sub): the slot is
 * page_slot[t] (0-7, the table of contents' pad, as before), the sub of a two-page slot its page_sub[t] bit (the page
 * of it used last).
 * PL16 (spec 2026-10-25-drums-design.md, "The drum page frame"): Shift + Drum 1-4 opens the drum's page the same way;
 * drums (tracks 4-7) have their own page list, kept in drum_page[t - 4]: Repeat (repeat.c) and, PL17 (spec "Pattern
 * tools for drums"), Pattern tools on the note tracks' pad with its two pages (euclid.c, vary.c on the drum's own
 * settings; drum_page bit 3 = the second used last). The note tracks' arrays are only ever indexed by a note track:
 * every entry below picks the kind first. */
#include "slim.h"
#include "stock.h"
#include "chord_math.h"
#include "chord_held.h"

#define PAGE_CLOSED   0xFFu
#define CTRL_CONT     0x2Cu         /* controller + 0x2C: the track container (0x20040DB8) */
#define CTRL_ACTIVE   0x6Cu         /* controller + 0x6C: the active view */
#define CONT_MODE     0x18Cu        /* track container + 0x18C: the views' mode; a drum's: 1 steps and samples, 6 expanded */
#define MODE_DRUM     1u
#define MODE_DRUM_WIDE 6u
#define SINK_TRACK    0x0Cu
#define BTN_PRESET    8u
#define BTN_NOTE      9u
#define BTN_MIXER     14u
#define BTN_FX        15u
#define BTN_DOWN      19u           /* Octave ▼: the next page */
#define BTN_UP        20u           /* Octave ▲: the previous page */
#define LED_DOWN      51u
#define LED_UP        52u
#define TOC_FIRST     24u           /* the table of contents: pad 25 = page 0 */
#define BTN_FLIP      21u           /* 1-16/17-32: with Shift in the Note view, the next quick view */
#define LED_FLIP      53u
#define LED_TRACKS    32u           /* panel LEDs 32-35: Synth 1, Synth 2, MIDI 1, MIDI 2; 36-39: Drum 1-4 */
#define COL_SHIFT_FN  0x2Cu         /* stock's colour for a button with a Shift function (Note, Gate, Microstep) */
#define QUICK_FIRST   16u           /* the quick view: pads 17-32 */

#define COL_SHAPE        COL_GREEN
#define COL_SHAPE_DIM    COL_GREEN_DIM
#define COL_INV          COL_BLUE
#define COL_INV_DIM      COL_BLUE_DIM
#define COL_SPREAD       COL_MAGENTA
#define COL_SPREAD_DIM   COL_MAGENTA_DIM
#define COL_BASS         COL_ORANGE
#define COL_BASS_DIM     COL_ORANGE_DIM
#define COL_ROOTLESS     COL_WHITE

/* The Chords page (PL15, spec 2026-10-23-chords-page-design.md): pads 0-7 shapes, 8-12 the row-2 shapes (13-15 dark),
 * 16-19 inversion, 20-22 spread, 23 bass, 24-26 voice leading, 27-29 strum speed, 30-31 strum direction. */
#define CP_SHAPE2     8u
#define CP_INV        16u
#define CP_SPREAD     20u
#define CP_BASS       23u
#define CP_LEAD       24u
#define CP_SPEED      27u
#define CP_DIR        30u

#define QUICK_NONE    0xFFu         /* QUICK_ROW: the page has no quick half (the flip skips it) */

static const uint8_t PAGE_COL[PAGE_SLOTS][2] = {{COL_GREEN, COL_GREEN_DIM}, {COL_BLUE, COL_BLUE_DIM},
                                                {COL_ORANGE, COL_ORANGE_DIM}, {COL_YELLOW, COL_YELLOW_DIM},
                                                {COL_OFF, COL_OFF}, {COL_OFF, COL_OFF}, {COL_OFF, COL_OFF},
                                                {COL_MAGENTA, COL_MAGENTA_DIM}};   /* COL_OFF: no page on that pad */
/* The drums' page list, the slots as the note tracks' (a feature keeps its pad): the colours, and which slots hold a
 * page (COL_OFF: none). Beta (layouts/beta-layout-pass.md, one slot = one kind of page): Repeat on pad 26, as the
 * note tracks' Arp; PL17: Pattern tools on 27. Pad 25 is for Levels (later). */
static const uint8_t DRUM_COL[PAGE_SLOTS][2] = {{COL_OFF, COL_OFF}, {COL_BLUE, COL_BLUE_DIM},
                                                {COL_ORANGE, COL_ORANGE_DIM}};
/* Each page's quick half: its first row (two rows on pads 17-32). Change here to change what quick access shows. */
static const uint8_t QUICK_ROW[PAGE_SLOTS] = {0u, 0u, QUICK_NONE, QUICK_NONE, QUICK_NONE, QUICK_NONE, QUICK_NONE,
                                              QUICK_NONE};   /* Chords: the shapes (rows 1-2); Arp: pattern,
                                                                 * rate, latch; Keys: none (set-once settings) */

uint8_t chord_page;                 /* the track whose page is open, PAGE_CLOSED when none */
uint8_t page_slot[TRACKS];
uint8_t page_quick[TRACKS];
static uint32_t page_taken;         /* pads whose press the page took: their release is the page's too */

/* Every way a page closes (a draft lives only while its pages are open). */
static void page_close(void)
{
    chord_page = PAGE_CLOSED;
    repeat_release_all();            /* a drum pad held now never sends its release here */
    melody_draft_end();
    euclid_disarm();                 /* and an armed Write or a pending action */
}

void page_init(void)
{
    page_close();
    memset(page_slot, PAGE_CHORDS, sizeof page_slot);
    memset(page_quick, PAGE_CHORDS, sizeof page_quick);
    page_taken = 0;
}

int page_exists(uint32_t p)
{
    return p < PAGE_SLOTS && PAGE_COL[p][0] != COL_OFF;
}

int drum_slot_exists(uint32_t p)
{
    return p < PAGE_SLOTS && DRUM_COL[p][0] != COL_OFF;
}

static uint32_t is_drum(uint32_t t)
{
    return t >= DRUM_FIRST;
}

/* Slot p of the page list of a drum's or a note track's holds a page. */
static int slot_exists(uint32_t drum, uint32_t p)
{
    return drum ? drum_slot_exists(p) : page_exists(p);
}

/* Slot p's bit when it has two pages, else 0: a note track's page_sub bit (Pattern tools, Melody), a drum's drum_page
 * bit (Pattern tools: DRUM_SUB). */
static uint32_t sub_bit(uint32_t drum, uint32_t p)
{
    if (drum)
        return p == PAGE_TOOLS ? DRUM_SUB : 0u;
    return p == PAGE_TOOLS || p == PAGE_MELODY ? 1u << (p - PAGE_TOOLS) : 0u;
}

/* Track t's page of slot p used last: 1 for the second page of a two-page slot. */
static uint32_t sub_of(uint32_t t, uint32_t p)
{
    uint32_t drum = is_drum(t);
    return ((drum ? drum_page[t - DRUM_FIRST] : page_sub[t]) & sub_bit(drum, p)) != 0u;
}

/* Track t's page: slot << 1 | sub. A drum whose stored slot holds no page is on Repeat. */
static uint32_t page_of(uint32_t t)
{
    uint32_t p;
    if (is_drum(t)) {
        p = DRUM_SLOT(drum_page[t - DRUM_FIRST]);
        if (!drum_slot_exists(p))
            p = PAGE_REPEAT;
    } else
        p = page_slot[t];
    return p << 1 | sub_of(t, p);
}

/* The page after pg (slot << 1 | sub) forward or before it in the drum or note page list: a two-page slot's other
 * page, else the next slot in pad order, skipping empty pads (forward: its first page, back: its last); pg itself when
 * there is none. */
static uint32_t page_step(uint32_t drum, uint32_t pg, uint32_t forward)
{
    uint32_t p = pg >> 1;
    if (sub_bit(drum, p) && (pg & 1u) != forward)
        return p << 1 | forward;
    for (uint32_t q = p; forward ? q + 1u < PAGE_SLOTS : q > 0u;) {
        q = forward ? q + 1u : q - 1u;
        if (slot_exists(drum, q))
            return q << 1 | (sub_bit(drum, q) && !forward);
    }
    return pg;
}

/* Track t goes to page pg: its slot, and for a two-page slot its bit (page_sub's, a drum's DRUM_SUB); a one-page slot
 * keeps the bits. A drum: both in drum_page. */
static void page_go(uint32_t t, uint32_t pg)
{
    uint32_t p = pg >> 1, drum = is_drum(t), bit = sub_bit(drum, p), on = pg & 1u ? bit : 0u;
    if (drum) {
        uint8_t *b = &drum_page[t - DRUM_FIRST];
        *b = (uint8_t)((*b & ~(7u | bit)) | p | on);
        return;
    }
    page_slot[t] = (uint8_t)p;
    page_sub[t] = (uint8_t)((page_sub[t] & ~bit) | on);
}

/* Drum track t is on screen: the container active, on t, in the steps-and-samples or the expanded view. */
static int drum_visible(void *ctrl, uint32_t t)
{
    uint8_t *cont = *(uint8_t **)((uint8_t *)ctrl + CTRL_CONT);
    if (*(void **)((uint8_t *)ctrl + CTRL_ACTIVE) != cont)
        return 0;
    uint32_t mode = cont[CONT_MODE];
    return (mode == MODE_DRUM || mode == MODE_DRUM_WIDE) && track_of(cont) == t;
}

/* Track t's pages can show: a note track in its Note view, a drum in its drum views. */
static int track_visible(void *ctrl, uint32_t t)
{
    if (is_drum(t))
        return drum_visible(ctrl, t);
    uint32_t mode;
    void *view = chord_visible_view(ctrl, &mode);
    return view && chord_note_sink(view)[SINK_TRACK] == t;
}

/* The page's track is on screen. */
static int page_visible(void *ctrl)
{
    return track_visible(ctrl, chord_page);
}

static void page_open(void *ctrl, uint32_t track)
{
    if (melody_draft != track + 1u)  /* another track's pages: the draft goes */
        melody_draft_end();
    if (!track_visible(ctrl, track)) {   /* stock's track-button case 0x08033400 */
        void *cont = *(void **)((uint8_t *)ctrl + CTRL_CONT);
        cont_select_track(cont, track);
        ctrl_set_view(ctrl, cont_track_view(cont, 1u), track);
    }
    chord_page = (uint8_t)track;
    page_taken = 0;                  /* a release lost to a view switch left its bit; a fresh open starts clean */
    repeat_release_all();            /* so a drum pad held across it is up (its release goes to stock) */
    if (!page_visible(ctrl))
        page_close();    /* the track's view is not a Note view (a drum's: its drum views): no page */
}

/* button_press, from chord_on_button: Shift + Synth 1 / 2, MIDI 1 / 2 or Drum 1-4 opens; ▲ ▼ step pages while one
 * is open (with or without Shift: a paging press never reaches stock's Octave or Shift + Octave); the view buttons
 * close. */
int page_on_button(void *ctrl, uint32_t id)
{
    euclid_unarm();                  /* an armed Write takes its second press only: any button ends it */
    if (id < TRACKS + DRUMS && chord_shift_held()) {
        page_open(ctrl, id);
        return SLIM_HANDLED;         /* stock drops this press anyway (its Shift mask) */
    }
    if (id == BTN_FLIP && chord_shift_held() && chord_page == PAGE_CLOSED) {
        uint32_t mode;
        void *view = chord_visible_view(ctrl, &mode);
        if (!view)
            return SLIM_PASS;        /* not the Note view: stock (nothing) */
        uint8_t *q = &page_quick[chord_note_sink(view)[SINK_TRACK]];
        do
            *q = (uint8_t)((*q + 1u) % PAGE_SLOTS);
        while (QUICK_ROW[*q] == QUICK_NONE);
        return SLIM_HANDLED;
    }
    if (chord_page != PAGE_CLOSED && (id == BTN_DOWN || id == BTN_UP)) {
        if (!page_visible(ctrl)) {
            page_close();
            return SLIM_PASS;
        }
        page_go(chord_page, page_step(is_drum(chord_page), page_of(chord_page), id == BTN_DOWN));
        return SLIM_HANDLED;
    }
    if (chord_page != PAGE_CLOSED && !chord_shift_held()
        && (id < 8u || id == BTN_PRESET || id == BTN_NOTE || id == BTN_MIXER || id == BTN_FX))
        page_close();                /* and stock does what the button does */
    return SLIM_PASS;
}

/* One pick for the Chords page and its Quick view (page pads 0-15), so the two cannot disagree. */
static void pick_chords(uint32_t t, uint32_t pad)
{
    uint32_t s = chord_settings[t], bit = 1u << t;
    if (pad < CP_INV) {
        if (pad < CP_SHAPE2 + 5u)
            chord_pick_shape(t, pad);               /* 13-15: dark, nothing */
    } else if (pad < CP_SPREAD) {
        chord_voice[t] &= (uint8_t)~(3u << 4);      /* an inversion ends voice leading, which chooses its own */
        chord_settings[t] = (uint8_t)((s & ~(3u << 3)) | (pad - CP_INV) << 3);
    } else if (pad < CP_BASS) {
        chord_settings[t] = (uint8_t)((s & ~(3u << 5)) | (pad - CP_SPREAD) << 5);
    } else if (pad == CP_BASS) {                    /* bass: off -> below -> rootless over bass -> off */
        if (!CHORD_BASS(s))
            s |= 1u << 7;
        else if (!(chord_rootless & bit))
            chord_rootless |= (uint8_t)bit;
        else {
            s &= ~(1u << 7);
            chord_rootless &= (uint8_t)~bit;
        }
        chord_settings[t] = (uint8_t)s;
    } else if (pad < CP_SPEED) {                    /* voice leading: one at a time, the lit one again = off */
        uint32_t n = pad - CP_LEAD + 1u;
        chord_voice[t] = (uint8_t)((chord_voice[t] & ~(3u << 4)) | (VOICE_LEAD(chord_voice[t]) == n ? 0u : n << 4));
    } else if (pad < CP_DIR) {                      /* strum speed 1-3, the lit one again = off */
        uint32_t n = pad - CP_SPEED + 1u;
        chord_strum = (uint8_t)((chord_strum & ~(3u << 2u * t)) | (STRUM_OF(t) == n ? 0u : n) << 2u * t);
    } else {                                        /* rising, falling */
        chord_strum_down = (uint8_t)((chord_strum_down & ~bit) | (pad - CP_DIR) << t);
    }
}

static void pick_arp(uint32_t t, uint32_t pad)
{
    uint8_t *a = chord_arp[t];
    uint32_t row = pad / 8u, col = pad % 8u, a0 = a[0];
    if (row == 0u) {
        a[0] = (uint8_t)((a0 & ~7u) | col);
        if (col == ARP_OFF)
            arp_free(t, 0);         /* pattern off: the track's arpeggio entries go (pads held send nothing on release) */
    } else if (row == 1u) {
        if (col < 4u) {
            a0 = (a0 & ~(3u << 3)) | col << 3;
            if (col == 3u && ARP_MOD(a0) == MOD_DOTTED)
                a0 &= ~(3u << 5);    /* dotted 1/32 is off the grid */
            a[0] = (uint8_t)a0;
        } else if (col == 4u) {
            a[0] = (uint8_t)((a0 & ~(3u << 5)) | (ARP_MOD(a0) == MOD_TRIPLET ? 0u : MOD_TRIPLET << 5));
        } else if (col == 5u) {
            if (ARP_RATE(a0) != 3u)
                a[0] = (uint8_t)((a0 & ~(3u << 5)) | (ARP_MOD(a0) == MOD_DOTTED ? 0u : MOD_DOTTED << 5));
        } else if (col == 7u) {
            a[0] = (uint8_t)(a0 ^ ARP_LATCH);
            if (a0 & ARP_LATCH)
                arp_free(t, 1);     /* latch off: the latched notes go, once no pad of the track is held */
        }
    } else if (row == 2u) {
        if (col < 4u)
            a[1] = (uint8_t)((a[1] & ~3u) | col);
        else if (col == 4u) {               /* the gate, as stock's Gate view: one sixth down, 1/6 -> 6/6 */
            uint32_t g = ARP_GATE(a[1]);
            a[1] = (uint8_t)((a[1] & ~(7u << 2)) | (g ? g - 1u : GATE_LEGATO) << 2);
        }
    }
}

static void pick_keys(uint32_t t, uint32_t pad)
{
    if (pad == 0u)                                  /* pad 1: mono record, a toggle */
        chord_mono ^= (uint8_t)(1u << t);
    else if (pad == 1u)                             /* pad 2: chords in step entry (PL18), a toggle */
        chord_step ^= (uint8_t)(1u << t);
    else if (pad == 2u || pad == 3u) {              /* pads 3-4: pattern strum played / written (PL19), one of two */
        uint32_t mode = pad - 1u;                   /* PSTRUM_PLAYED, PSTRUM_WRITTEN */
        uint32_t now = PSTRUM_OF(t);
        chord_pstrum = (uint8_t)((chord_pstrum & ~(3u << (2u * t))) | (now == mode ? 0u : mode) << (2u * t));
    }
}

/* pg = slot << 1 | sub. */
static void pick(uint32_t t, uint32_t pg, uint32_t pad)
{
    uint32_t p = pg >> 1, sub = pg & 1u;
    if (p == PAGE_ARP)
        pick_arp(t, pad);
    else if (p == PAGE_KEYS)
        pick_keys(t, pad);
    else if (p == PAGE_TOOLS)
        sub ? tools2_pick(t, pad) : euclid_pick(t, pad);
    else if (p == PAGE_MELODY)
        sub ? phrasing_pick(t, pad) : melody_pick(t, pad);
    else
        pick_chords(t, pad);
}

/* From chord_on_pad (Shift held in the Note view, pads 16-31): the track's quick view. */
void page_quick_pad(uint32_t track, uint32_t pad)
{
    uint32_t p = page_quick[track], q = 8u * QUICK_ROW[p] + pad - QUICK_FIRST;
    if (p == PAGE_ARP)                              /* only the pages with a quick half: no Write is reachable from here */
        pick_arp(track, q);
    else
        pick_chords(track, q);
}

/* ctrl_pad_press: with the page open and on screen, every pad goes to it (Shift held: the table of contents). */
int page_on_pad(void *ctrl, uint32_t pad, uint32_t vel, uint32_t *ret)
{
    (void)ret;
    if (pad >= PADS)
        return SLIM_PASS;
    if (chord_page == PAGE_CLOSED || !page_visible(ctrl)) {
        page_close();
        page_taken &= ~(1u << pad);  /* a release lost to a view switch cannot swallow this press's */
        return SLIM_PASS;
    }
    uint32_t t = chord_page, drum = is_drum(t), pg = page_of(t);
    if (chord_shift_held()) {                         /* the table of contents, of the drums' or the note tracks' list */
        euclid_unarm();
        uint32_t p = pad - TOC_FIRST;
        if (pad >= TOC_FIRST && slot_exists(drum, p))   /* the open feature's pad: its other page; another's: on the
                                                         * page of it used last */
            page_go(t, p == pg >> 1 ? pg ^ (sub_bit(drum, p) != 0u) : p << 1 | sub_of(t, p));
    } else if (drum && pg >> 1 == PAGE_REPEAT) {
        if (pad >= REPEAT_DRUM_PAD)
            repeat_press(pad - REPEAT_DRUM_PAD, vel); /* the drums: flags only, the heartbeat sends */
        else
            repeat_pick(pad);
    } else {
        pick(t, pg, pad);                             /* a drum's Pattern tools: as a note track's (PAGE_TOOLS) */
        euclid_stamp(pad);
    }
    page_taken |= 1u << pad;
    return SLIM_HANDLED;
}

/* ctrl_pad_release: the release of a pad the page took is the page's (stock would skip it too: it never saw the press). */
int page_on_release(void *ctrl, uint32_t pad, uint32_t *ret)
{
    (void)ctrl;
    (void)ret;
    if (pad >= PADS || !(page_taken & 1u << pad))
        return SLIM_PASS;
    page_taken &= ~(1u << pad);
    if (pad >= REPEAT_DRUM_PAD)
        repeat_release(pad - REPEAT_DRUM_PAD);   /* a drum's, even after its page closed (a note page's, or a drum's action
                                                  * pad on Pattern tools: a no-op, that pad holds no drum) */
    if (chord_page != PAGE_CLOSED && page_taken == 0)
        euclid_release(chord_page);   /* a write waits until every finger is up (see euclid.c) */
    return SLIM_HANDLED;
}

static uint16_t lit(uint32_t on, uint32_t bright, uint32_t dim)
{
    return (uint16_t)(on ? bright : dim);
}

static void draw_chords(uint32_t t, uint16_t *out)
{
    uint32_t s = chord_track_settings(t), lead = VOICE_LEAD(chord_voice[t]), strum = STRUM_OF(t);
    uint32_t arp_on = ARP_PATTERN(chord_arp[t][0]) != ARP_OFF, shape = chord_shape_index(s);
    for (uint32_t c = 0; c < PADS; c++)
        out[c] = COL_OFF;
    for (uint32_t c = 0; c < CP_SHAPE2 + 5u; c++)
        out[c] = lit(c == shape, COL_SHAPE, COL_SHAPE_DIM);
    for (uint32_t c = 0; c < 4u; c++)
        out[CP_INV + c] = lead ? (uint16_t)(c == CHORD_INV(s) ? COL_INV_DIM : COL_OFF)
                               : lit(c == CHORD_INV(s), COL_INV, COL_INV_DIM);
    for (uint32_t c = 0; c < 3u; c++)
        out[CP_SPREAD + c] = lit(c == CHORD_SPREAD(s), COL_SPREAD, COL_SPREAD_DIM);
    out[CP_BASS] = (uint16_t)(!CHORD_BASS(s) ? COL_BASS_DIM : CHORD_ROOTLESS(s) ? COL_ROOTLESS : COL_BASS);
    for (uint32_t c = 0; c < 3u; c++)
        out[CP_LEAD + c] = lit(c + 1u == lead, COL_INV, COL_INV_DIM);
    for (uint32_t c = 0; c < 3u; c++)               /* with a pattern on strum is ignored: its stored value dim (D9) */
        out[CP_SPEED + c] = arp_on ? lit(c + 1u == strum, COL_WHITE_DIM, COL_OFF)
                                   : lit(c + 1u == strum, COL_WHITE, COL_WHITE_DIM);
    for (uint32_t c = 0; c < 2u; c++)               /* the direction, as the speeds */
        out[CP_DIR + c] = arp_on ? lit(c == STRUM_DOWN(t), COL_WHITE_DIM, COL_OFF)
                                 : lit(c == STRUM_DOWN(t), COL_WHITE, COL_WHITE_DIM);
}

static void draw_arp(uint32_t t, uint16_t *out)
{
    uint32_t a0 = chord_arp[t][0], a1 = chord_arp[t][1];
    for (uint32_t c = 0; c < 8u; c++) {
        out[c] = lit(c == ARP_PATTERN(a0), COL_GREEN, COL_GREEN_DIM);
        out[16u + c] = c < 4u ? lit(c + 1u == ARP_OCT(a1), COL_MAGENTA, COL_MAGENTA_DIM)
                     : c == 4u ? (uint16_t)(COL_GATE_1_6 - ARP_GATE(a1)) : (uint16_t)COL_OFF;
        out[24u + c] = COL_OFF;
    }
    for (uint32_t c = 0; c < 4u; c++)
        out[8u + c] = lit(c == ARP_RATE(a0), COL_BLUE, COL_BLUE_DIM);
    out[12] = lit(ARP_MOD(a0) == MOD_TRIPLET, COL_MAGENTA, COL_MAGENTA_DIM);
    out[13] = ARP_RATE(a0) == 3u ? (uint16_t)COL_OFF : lit(ARP_MOD(a0) == MOD_DOTTED, COL_MAGENTA, COL_MAGENTA_DIM);
    out[14] = COL_OFF;
    out[15] = lit(a0 & ARP_LATCH, COL_ORANGE, COL_ORANGE_DIM);
}

static void draw_keys(uint32_t t, uint16_t *out)
{
    for (uint32_t c = 0; c < PADS; c++)
        out[c] = COL_OFF;
    out[0] = lit((chord_mono >> t) & 1u, COL_MAGENTA, COL_MAGENTA_DIM);
    out[1] = lit((chord_step >> t) & 1u, COL_GREEN, COL_GREEN_DIM);
    out[2] = lit(PSTRUM_OF(t) == PSTRUM_PLAYED, COL_WHITE, COL_WHITE_DIM);      /* PL19 */
    out[3] = lit(PSTRUM_OF(t) == PSTRUM_WRITTEN, COL_WHITE, COL_WHITE_DIM);
}

/* pg = slot << 1 | sub. */
static void draw(uint32_t t, uint32_t pg, uint16_t *out)
{
    uint32_t p = pg >> 1, sub = pg & 1u;
    if (p == PAGE_ARP)
        draw_arp(t, out);
    else if (p == PAGE_KEYS)
        draw_keys(t, out);
    else if (p == PAGE_TOOLS)
        sub ? tools2_draw(t, out) : euclid_draw(t, out);
    else if (p == PAGE_MELODY)
        sub ? phrasing_draw(t, out) : melody_page_draw(t, out);
    else
        draw_chords(t, out);
}

/* From chord_on_leds (Shift held in the Note view): the quick view on pads 16-31; pads 0-15 stay stock's. */
void page_quick_draw(uint32_t track, uint16_t *out)
{
    uint16_t page[PADS];
    uint32_t p = page_quick[track];
    draw(track, p << 1, page);                      /* the quick pages have one page each */
    for (uint32_t c = 0; c < 16u; c++)
        out[QUICK_FIRST + c] = page[8u * QUICK_ROW[p] + c];
}

/* From chord_on_leds, every view: with Shift held the tracks and drums with pages light as stock's Shift-function
 * buttons (where stock left them off); in the Note view with no page open, LED 53 shows the quick view's page. */
void page_shift_leds(void *ctrl, uint16_t *out)
{
    if (!chord_shift_held())
        return;
    for (uint32_t i = 0; i < TRACKS + DRUMS; i++)
        if (!out[LED_TRACKS + i])
            out[LED_TRACKS + i] = COL_SHIFT_FN;
    uint32_t mode;
    void *view = chord_page == PAGE_CLOSED ? chord_visible_view(ctrl, &mode) : 0;
    if (view)
        out[LED_FLIP] = PAGE_COL[page_quick[chord_note_sink(view)[SINK_TRACK]]][0];
}

/* led_task, from chord_on_leds: the page over the 32 pads and ▲ ▼; 1 when drawn. */
int page_draw(void *ctrl, uint16_t *out)
{
    if (chord_page == PAGE_CLOSED || !page_visible(ctrl)) {
        page_close();
        euclid_disarm();             /* the page went away another way (a view change stock made) */
        return 0;
    }
    uint32_t t = chord_page, drum = is_drum(t), pg = page_of(t), p = pg >> 1;
    const uint8_t (*col)[2] = drum ? DRUM_COL : PAGE_COL;
    if (chord_shift_held()) {
        for (uint32_t c = 0; c < PADS; c++)
            out[c] = COL_OFF;
        for (uint32_t i = 0; i < PAGE_SLOTS; i++)
            out[TOC_FIRST + i] = lit(i == p, col[i][0], col[i][1]);   /* COL_OFF where there is none */
    } else if (drum && p == PAGE_REPEAT)
        repeat_draw(out);
    else
        draw(t, pg, out);             /* a drum's Pattern tools: as a note track's */
    uint32_t down = page_step(drum, pg, 1), up = page_step(drum, pg, 0);   /* a feature's both pages: its colour */
    out[LED_DOWN] = down != pg ? col[down >> 1][0] : COL_OFF;
    out[LED_UP] = up != pg ? col[up >> 1][0] : COL_OFF;
    return 1;
}
