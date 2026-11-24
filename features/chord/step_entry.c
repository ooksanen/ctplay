/* Chords in step entry (PL18, spec docs/specs/2026-10-26-step-entry-chords-design.md).
 *
 * Stock's add 0x0804B094(view, note, vel) puts one note into the held step's edit store [view + 0x24]; both step-entry
 * routes reach it (step first: the Note view's pad press; pad first: the held-step listener). With the track's
 * chord_step bit and a chord to play, step_on_add does the whole add itself: the pad's note, then the chord's other
 * notes lowest first, each into the first free unit while one is left, notes already in the step skipped; stock's gate
 * (the longest of the step's units, tie bit stripped; 6 and the probability "always" on an empty step), microstep 0,
 * the hook's velocity; one commit, whose listeners write the pattern and preview the step as for stock's one note.
 * A pad stock ignores (kbd_pad_ignored: it plays nothing live) still adds its note step first (0x0804AC8C): with the
 * same test on the note, step_on_add leaves that to stock (its note alone), and the pad again is stock's too
 * (step_on_press passes for such a pad). Pad first never adds it: stock holds no pitch for the pad (0x0804AF06).
 * Only a few store parameters are touched: no interrupts masked, nothing pattern-wide. The removal ends sounds through
 * the sink, as stock's own removal does on the same task.
 *
 * The pad again (its own pitch in the step by stock's test) takes the chord out: step_on_press, at the Note view's pad
 * press 0x0804AB5A, clears the step's other units whose note name is one of the chord's, ends their sound and frees the
 * pads holding them as stock's own removal does for the pad's pitch, then lets stock remove the pad's own unit(s).
 *
 * PL19, Written (pstrum_mode(t) == PSTRUM_WRITTEN; spec 2026-10-28-playback-strum-design.md, "Written: step entry"):
 * the chord goes in as a roll from the held step's start, note k (strum order: roll_order, STRUM_DOWN) at
 * roll_sixths(k x WRITTEN_GAP, ticks a step) sixths. The notes that fall in the held step go in on the press through the
 * route above, each with its microstep. The others wait in a pending spill (spill[], ITCM, RAM only, one record per
 * track, pad that made the entry, pattern and held step, latched on the press from the recorder's position store
 * [rec + 0x14], p0 / p1, PL19 spike q3: a key pad held while several steps are tapped keeps one record per step; with
 * all SPILLS (16) records waiting, a further entry's spill is left out; a project load drops them) and every record of
 * the pad is written on its release (step_spill_release, from chord_on_release, either release order; stock releases
 * the held pads when the view is left): straight into the pattern, each into roll_step(held step, sixths / 6, first,
 * last), the same note at the same microstep already there or a full step skipped, PL18's gate rule for that step,
 * each unit's bytes and mask bit in a few masked instructions (re-checking that the unit is still free: a recorder
 * commit from the Main task may have taken it); then one rec_touch(rec), which shows them at once (spike q3_spill).
 * No pattern write, no store touch and nothing masked on a press (the phantom-press rule, CLAUDE.md). A spilled note
 * that would wrap back onto the held step itself (a roll longer than the pattern) is left out.
 * The pad again removes the roll: the pad's pitch in the held step (PL18's test), or, when a roll's pad note spilled out
 * of it (falling, or a fast rate), the pad's own roll there exactly: each note of the roll (the chord as chord_notes
 * builds it, with its stored inversion: a voice-led entry is not matched this way) at its exact pitch and microstep in
 * its step, the held step's or a spilled one's (read on the press, a plain loop: no write, nothing masked); a position
 * whose step is full of other units, or that the spill skips (the held step itself), is not required, at least one
 * must be there. Then CTPlay removes (HANDLED: stock adds nothing); otherwise the press adds as any.
 * Neighbour rolls share pitches (a roll's tail lands in the next step), so on a Written track a duplicate is the same
 * note at the same microstep, and CTPlay's removal touches only the roll's own positions with their exact notes: the
 * held step's on the press, the spilled steps' on the pad's release (a pending removal), when the pad's exact roll is
 * there. The pad's pitch in the held step without its exact roll (a block chord entered while the track was Off or
 * Played, a roll of another speed or direction): PL18's removal by note name in the held step, nothing pended. Stock's
 * own removal of the pad's pitch (every unit of the held step holding it, any microstep) stays stock's. Off and Played
 * keep PL18's rules (a duplicate by note, a removal by note name).
 * Step first, the entering pad comes from step_on_press (`entering`, consumed by the add that follows); pad first, it
 * is the key pad holding the added pitch (stock's [view + 0x40 + pad]).
 *
 * PL20 (trig conditions, a marked project only): a step's condition goes with its last note. When a removal on the
 * press (stock's, after CTPlay's chord removal, or CTPlay's roll removal) leaves the held step with no unit, its
 * parameter 0's bytes 2-3 are zeroed through the write pointer before the commit; on any Note view of a note track, the
 * feature active or not. A spilled step emptied on the release: its bytes 2-3 raw.
 */
#include "slim.h"
#include "stock.h"
#include "chord_math.h"
#include "chord_held.h"
#include "roll_math.h"
#include "trig_math.h"

#define VIEW_EDIT   0x24u           /* view + 0x24: the held step's edit store */
#define VIEW_HELD   0x2Cu           /* view + 0x2C: the held-step store; parameter 0 != 0 = a step held */
#define VIEW_KBD    0x38u           /* view + 0x38: keyboard */
#define VIEW_PITCH  0x40u           /* view + 0x40 + pad: the pitch the pad holds (0 = none); + 0x60 + pad: its velocity */
#define VIEW_VEL    0x60u
#define VIEW_SOURCE 0x80u           /* view + 0x80 + note: the source the note last sounded from (0x20 = the preview) */
#define KBD_TABLE   0x14u           /* keyboard + 0x14 + idx: pitch (root-relative, +12) */
#define KBD_SCALE   0x0Cu           /* keyboard + 0x0C: scale object; its mask at + 4 */
#define KBD_KEY     0x10u           /* keyboard + 0x10: -> the project root byte (0-11) */
#define KEY_LOW     12u             /* kbd_pad_ignored 0x080523E8: a pad plays when (pitch + root) & 0xFF is 12-139 */
#define KEY_HIGH    139u
#define SINK_TRACK  0x0Cu           /* sink + 0x0C: track 0-3 */
#define UNITS       6u              /* a step's note units: parameters 1-6 */
#define UNIT_BITS   0x3Fu           /* parameter 0 byte 0: the used units' mask */
#define U_NOTE      0u              /* a unit's bytes */
#define U_GATE      1u              /* gate (sixths of a step) | tie << 7 */
#define U_MICRO     2u
#define U_VEL       3u
#define GATE_BITS   0x7Fu
#define GATE_STEP   6u              /* one step: stock's gate on an empty step */
#define PROB_ALWAYS 7u              /* parameter 0 byte 1: the step's probability */
#define RECORDERS   0x2003C174u     /* stock.h recorders: [+ 4 t] = note track t's recorder */
#define REC_POS     0x14u           /* rec + 0x14: its position store: p0 the shown pattern, p1 the held step 0-31 */
#define REC_PATTERNS 0x48u          /* rec + 0x48: -> the track's 8 patterns */
#define PATTERNS    8u
#define PATTERN_SIZE 0xCA8u
#define PATTERN_LAST 0x380u         /* pattern + 0x380: its last step, + 0x381 its first, + 0x382 its sync rate */
#define PATTERN_FIRST 0x381u
#define PATTERN_RATE 0x382u
#define RATES       8u
#define STEPS       32u
#define STEP_SIZE   28u             /* [0] unit mask, [1] probability, 6 units of 4 B from + 4 (the U_* bytes) */
#define SIXTHS      6u              /* a step's microsteps */
#define NOTES_MAX   (1u + CHORD_MAX_OTHER)
#define SPILL_MAX   CHORD_MAX_OTHER /* a roll's notes after its first (which always sits in the held step) */
#define SPILLS      16u             /* pending spills: entries waiting for their pads' releases */
#define BARRIER()   __asm__ volatile("" ::: "memory")

typedef struct {                    /* a pending spill or removal (PL19, Written) */
    uint8_t track;                  /* track + 1, 0 = free */
    uint8_t pad;                    /* the pad whose release writes it */
    uint8_t pattern, step;          /* the held step, latched on the press */
    uint8_t vel;                    /* a spill: the press's velocity */
    uint8_t n;                      /* positions in note[] / six[] */
    uint8_t remove;                 /* 0: note[] go in; 1: note[] leave their positions */
    uint8_t spare;
    uint8_t note[SPILL_MAX];        /* the roll's notes at six[] */
    uint8_t six[SPILL_MAX];         /* sixths of a step from the held step's start (6 or more) */
} spill_t;

static spill_t spill[SPILLS] SLIM_ITCM(spill);
static uint32_t entering SLIM_ITCM(entering);   /* step_on_press -> step_on_add: 1 + pad | root << 8, 0 = none */

void step_entry_init(void)
{
    memset(spill, 0, sizeof spill);
    entering = 0;
}

static uint8_t *recorder(uint32_t t)
{
    return *(uint8_t *volatile *)(RECORDERS + 4u * t);
}

/* Track t's held step as its recorder knows it (PL19 spike q3): the pattern's address, its index and the step, and its
 * ticks a step; 0 when there is none. */
static uint8_t *held_at(uint32_t t, uint32_t *pattern, uint32_t *step, uint32_t *per)
{
    uint8_t *rec = recorder(t);
    void *pos = rec ? *(void **)(rec + REC_POS) : 0;
    uint8_t *pat = rec ? *(uint8_t **)(rec + REC_PATTERNS) : 0;
    if (!pos || !pat)
        return 0;
    uint32_t p = *param_get(pos, 0), s = *param_get(pos, 1);
    if (p >= PATTERNS || s >= STEPS)
        return 0;
    pat += PATTERN_SIZE * p;
    uint32_t rate = pat[PATTERN_RATE];
    if (rate >= RATES)
        return 0;
    *pattern = p;
    *step = s;
    *per = step_ticks[rate];
    return pat;
}

/* Keep x as the pending record of (track, pad, pattern, step): the one already there, else a free one; none free:
 * left out. */
static void pend(const spill_t *x)
{
    spill_t *to = 0;
    for (uint32_t i = 0; i < SPILLS && !to; i++)
        if (spill[i].track == x->track && spill[i].pad == x->pad && spill[i].pattern == x->pattern
            && spill[i].step == x->step)
            to = &spill[i];
    for (uint32_t i = 0; i < SPILLS && !to; i++)
        if (!spill[i].track)
            to = &spill[i];
    if (to)
        *to = *x;
}

/* The key pad holding `note` (stock's [view + 0x40 + pad]: pad first), PADS when none. */
static uint32_t pad_holding(void *view, uint32_t note)
{
    const uint8_t *v = view;
    for (uint32_t p = 0; p < PADS; p++)
        if (v[VIEW_PITCH + p] == note)
            return p;
    return PADS;
}

/* The feature acts for this view: a Note view of track t whose chord_step bit is set and whose pad plays a chord live
 * (s = its settings, as chord_track_settings). Returns the view's sink then, else 0. */
static uint8_t *active(void *view, uint32_t *t, uint32_t *s)
{
    uint8_t *sink = chord_note_sink(view);
    if (!sink)
        return 0;
    *t = sink[SINK_TRACK];
    *s = chord_track_settings(*t);
    return (chord_step >> *t & 1u) && (CHORD_HAS_SHAPE(*s) || CHORD_BASS(*s)) ? sink : 0;
}

/* The chord's other notes for `root` on track t (out, at most CHORD_MAX_OTHER): pad first, the pad's sounding chord
 * (a live entry of the track with that root); else built as a live press builds it (the next chord leads from it). */
static uint32_t others(void *view, uint32_t t, uint32_t root, uint8_t *out)
{
    for (uint32_t i = 0; i < HELD; i++) {
        const held_t *h = &held[i];
        uint32_t n = h->count;
        if (n && h->track == t && h->root == root && !(h->flags & (HELD_ARP | HELD_RELEASED))) {
            if (n > CHORD_MAX_OTHER)
                n = CHORD_MAX_OTHER;
            for (uint32_t k = 0; k < n; k++)
                out[k] = h->notes[k];
            return n;
        }
    }
    uint8_t *kbd = *(uint8_t **)((uint8_t *)view + VIEW_KBD);
    uint32_t mask = *(volatile uint32_t *)(*(uint8_t **)(kbd + KBD_SCALE) + 4u);
    uint32_t key = **(volatile uint8_t **)(kbd + KBD_KEY);
    return chord_build(t, root, mask, key, out);
}

int step_on_add(void *view, uint32_t note, uint32_t vel, uint32_t *ret)
{
    (void)ret;
    uint32_t latch = entering, t, s;
    entering = 0;                                   /* step first: the pad of this very add, never a later one */
    if (!active(view, &t, &s))
        return SLIM_PASS;
    uint8_t *kbd = *(uint8_t **)((uint8_t *)view + VIEW_KBD);
    uint32_t at = (note + **(volatile uint8_t **)(kbd + KBD_KEY)) & 0xFFu;
    if (at < KEY_LOW || at > KEY_HIGH)
        return SLIM_PASS;                           /* a pad stock ignores: stock adds its note alone */
    uint8_t notes[1u + CHORD_MAX_OTHER];
    uint32_t n = 1u + others(view, t, note, notes + 1);
    notes[0] = (uint8_t)note;                       /* the pad's own note first, as stock; then the others rising */
    for (uint32_t i = 2; i < n; i++)
        for (uint32_t j = i; j > 1u && notes[j - 1u] > notes[j]; j--) {
            uint8_t x = notes[j];
            notes[j] = notes[j - 1u];
            notes[j - 1u] = x;
        }
    uint8_t micro[NOTES_MAX] = {0};
    uint32_t pattern, step, per, written = 0;
    if (pstrum_mode(t) == PSTRUM_WRITTEN && held_at(t, &pattern, &step, &per)) {   /* PL19: a roll */
        written = 1;
        spill_t x = {0};
        uint32_t in = 0, gap = WRITTEN_GAP[STRUM_OF(t)];
        roll_order(notes, n, STRUM_DOWN(t));
        for (uint32_t k = 0; k < n; k++) {
            uint32_t six = roll_sixths(k * gap, per);
            if (six < SIXTHS) {                     /* in the held step: now */
                notes[in] = notes[k];
                micro[in++] = (uint8_t)six;
            } else if (x.n < SPILL_MAX) {           /* a later step: on the pad's release */
                x.note[x.n] = notes[k];
                x.six[x.n++] = (uint8_t)six;
            }
        }
        n = in;
        uint32_t pad = latch && latch >> 8 == note ? (latch & 0xFFu) - 1u : pad_holding(view, note);
        if (x.n && pad < PADS) {
            x.track = (uint8_t)(t + 1u);
            x.pad = (uint8_t)pad;
            x.pattern = (uint8_t)pattern;
            x.step = (uint8_t)step;
            x.vel = (uint8_t)vel;
            pend(&x);
        }
    }
    void *store = *(void **)((uint8_t *)view + VIEW_EDIT);
    uint32_t used = *param_get(store, 0), gate = 0;
    uint8_t have[UNITS], have_at[UNITS];            /* the used units' notes and microsteps */
    for (uint32_t u = 0; u < UNITS; u++) {
        if (!(used >> u & 1u))
            continue;
        const volatile uint8_t *p = param_get(store, 1u + u);
        have[u] = p[U_NOTE];
        have_at[u] = p[U_MICRO];
        if ((p[U_GATE] & GATE_BITS) > gate)
            gate = p[U_GATE] & GATE_BITS;
    }
    uint32_t empty = gate == 0u, before = used, u = 0;
    if (empty)
        gate = GATE_STEP;
    for (uint32_t k = 0; k < n; k++) {
        uint32_t dup = 0;
        for (uint32_t v = 0; v < UNITS; v++)        /* Written: the same note at the same microstep */
            dup |= (used >> v & 1u) && have[v] == notes[k] && (!written || have_at[v] == micro[k]);
        if (dup)
            continue;
        while (u < UNITS && (used >> u & 1u))
            u++;
        if (u == UNITS)
            break;                                  /* the step is full: the rest is left out */
        volatile uint8_t *p = param_wptr(store, 1u + u);
        p[U_NOTE] = notes[k];
        p[U_GATE] = (uint8_t)gate;
        p[U_MICRO] = micro[k];                      /* 0 but in a Written roll */
        p[U_VEL] = (uint8_t)vel;
        have[u] = notes[k];
        have_at[u] = micro[k];
        used |= 1u << u;
    }
    if (used == before)
        return SLIM_HANDLED;                        /* nothing to add: as stock with a full step, no commit */
    volatile uint8_t *p0 = param_wptr(store, 0);
    p0[0] = (uint8_t)(p0[0] | used);
    if (empty)
        p0[1] = PROB_ALWAYS;
    store_commit(store);
    return SLIM_HANDLED;
}

/* PL20: the held step is left with no unit: its trig condition (bytes 2-3 of parameter 0's write buffer p0) goes too,
 * so the commit that follows (CTPlay's or stock's) carries it into the pattern. A marked project only. */
static void cond_drop(volatile uint8_t *p0)
{
    if (trig_mark == 1u)
        p0[2] = p0[3] = 0;
}

/* Stock's removal (0x0804AB88-0x0804AC86) removes every used unit whose note, snapped into the scale, is the pad's
 * pitch, and adds the pitch when there is none. When the feature is active and stock will remove: the step's other units
 * whose note name (pitch class) is the root's or one of the chord's other notes' (the chord with its stored inversion:
 * voice leading does not change the names) lose their mask bit (their bytes stay, as stock's), one commit; then, as
 * stock for its unit when step_sounds(), each one's sound ends and a pad holding its pitch is freed. Stock's own unit(s)
 * are left to stock: cleared here, stock would find nothing and add the pitch back. */
int step_on_press(void *view, uint32_t pad, uint32_t vel, uint32_t *ret)
{
    (void)vel;
    (void)ret;
    uint32_t t, s, marked = trig_mark == 1u;
    uint8_t *sink = pad < PADS ? active(view, &t, &s) : 0;
    if (!sink && (pad >= PADS || !marked || !chord_note_sink(view)))
        return SLIM_PASS;                           /* PL20: marked, stock's removal is followed on any Note view */
    if (!*param_get(*(void **)((uint8_t *)view + VIEW_HELD), 0))
        return SLIM_PASS;
    uint8_t *kbd = *(uint8_t **)((uint8_t *)view + VIEW_KBD);
    uint32_t idx = note_pad_index(view, pad);
    if (kbd_pad_ignored(kbd, idx)) {
        if (!marked)
            return SLIM_PASS;
        sink = 0;                                   /* stock's pad: stock's own removal alone */
    }
    uint32_t root = kbd[KBD_TABLE + idx];
    void *scale = *(void **)(kbd + KBD_SCALE);
    void *store = *(void **)((uint8_t *)view + VIEW_EDIT);
    uint32_t used = *param_get(store, 0), own = 0;
    uint8_t note[UNITS] = {0}, at[UNITS] = {0};    /* the used units' notes and microsteps */
    for (uint32_t u = 0; u < UNITS; u++)
        if (used >> u & 1u) {
            const volatile uint8_t *q = param_get(store, 1u + u);
            note[u] = q[U_NOTE];
            at[u] = q[U_MICRO];
            if (scale_snap(scale, note[u]) == root)
                own |= 1u << u;
        }
    if (!sink) {                                    /* PL20: stock removes `own`; the step's last unit(s)? */
        if (own && !(used & ~own & UNIT_BITS))
            cond_drop(param_wptr(store, 0));
        return SLIM_PASS;
    }
    uint32_t mask = *(volatile uint32_t *)((uint8_t *)scale + 4u);
    uint32_t key = **(volatile uint8_t **)(kbd + KBD_KEY);
    uint8_t others[CHORD_MAX_OTHER];
    uint32_t n = chord_notes(root, mask, s | key << 16, others), names = 1u << root % 12u, gone = 0;
    for (uint32_t k = 0; k < n; k++)
        names |= 1u << others[k] % 12u;
    uint32_t pattern, step, per;                    /* PL19, Written: the roll's positions, k = 0 .. n */
    uint8_t *pat = pstrum_mode(t) == PSTRUM_WRITTEN ? held_at(t, &pattern, &step, &per) : 0;
    spill_t x = {0};
    uint8_t roll[NOTES_MAX], in_at[NOTES_MAX];      /* the roll; in_at[k] < SIXTHS: k's microstep in the held step */
    if (pat) {
        roll[0] = (uint8_t)root;
        for (uint32_t k = 0; k < n; k++)
            roll[1u + k] = others[k];
        roll_order(roll, n + 1u, STRUM_DOWN(t));
        uint32_t gap = WRITTEN_GAP[STRUM_OF(t)], first = pat[PATTERN_FIRST], last = pat[PATTERN_LAST];
        uint32_t there = 1, any = 0;
        for (uint32_t k = 0; k <= n; k++) {
            uint32_t six = roll_sixths(k * gap, per), micro = six % SIXTHS, hit = 0, full;
            in_at[k] = (uint8_t)(six < SIXTHS ? six : SIXTHS);
            if (six < SIXTHS) {                     /* the held step: its edit store */
                for (uint32_t u = 0; u < UNITS; u++)
                    hit |= (used >> u & 1u) && note[u] == roll[k] && at[u] == micro;
                full = (used & 0x3Fu) == 0x3Fu;
            } else {
                if (x.n < SPILL_MAX) {
                    x.note[x.n] = roll[k];
                    x.six[x.n++] = (uint8_t)six;
                }
                uint32_t to = roll_step(step, six / SIXTHS, first, last);
                if (to >= STEPS || to == step)
                    continue;                       /* the spill skips it: not required */
                const volatile uint8_t *st = pat + STEP_SIZE * to;
                uint32_t mask = st[0];
                for (uint32_t u = 0; u < UNITS; u++)
                    hit |= (mask >> u & 1u) && st[4u + 4u * u + U_NOTE] == roll[k]
                           && st[4u + 4u * u + U_MICRO] == micro;
                full = (mask & 0x3Fu) == 0x3Fu;
            }
            any |= hit;
            there &= hit | full;                    /* a full step left the note out: not required */
        }
        if (!(there && any))
            pat = 0;                                /* not its exact roll: own -> PL18's removal by name (a block chord,
                                                     * a roll of another speed or direction), else an add */
    }
    if (!own && !pat) {
        entering = (1u + pad) | root << 8;          /* stock adds it (step_add): this pad's entry */
        return SLIM_PASS;
    }
    if (pat && x.n) {                               /* the spilled positions, on this pad's release */
        x.track = (uint8_t)(t + 1u);
        x.pad = (uint8_t)pad;
        x.pattern = (uint8_t)pattern;
        x.step = (uint8_t)step;
        x.remove = 1u;
        pend(&x);
    }
    uint32_t done = own ? SLIM_PASS : SLIM_HANDLED; /* own: stock removes the pad's own unit(s); else nothing of stock's */
    for (uint32_t u = 0; u < UNITS; u++) {
        if (!((used & ~own) >> u & 1u))
            continue;
        if (!pat) {                                 /* PL18: by note name */
            gone |= (uint32_t)(names >> note[u] % 12u & 1u) << u;
            continue;
        }
        for (uint32_t k = 0; k <= n; k++)           /* Written: the roll's own in-step positions, exact notes */
            if (in_at[k] < SIXTHS && note[u] == roll[k] && at[u] == in_at[k])
                gone |= 1u << u;
    }
    if (!gone) {
        if (own && !(used & ~own & UNIT_BITS))
            cond_drop(param_wptr(store, 0));        /* PL20: stock's removal empties the step */
        return SLIM_PASS;
    }
    volatile uint8_t *p0 = param_wptr(store, 0);
    p0[0] = (uint8_t)(p0[0] & ~gone);
    if (!(used & ~gone & ~own & UNIT_BITS))         /* PL20: nothing left after CTPlay's removal and stock's (own) */
        cond_drop(p0);
    store_commit(store);
    if (!step_sounds(view))
        return (int)done;
    uint8_t *v = view;
    for (uint32_t u = 0; u < UNITS; u++)
        if (gone >> u & 1u)
            note_sink_off(sink, note[u], v[VIEW_SOURCE + note[u]]);
    for (uint32_t p = 0; p < PADS; p++) {           /* a pad holding a removed pitch: its release has nothing to end */
        uint32_t x = v[VIEW_PITCH + p];
        for (uint32_t u = 0; x && u < UNITS; u++)
            if (gone >> u & 1u && note[u] == x)
                v[VIEW_PITCH + p] = v[VIEW_VEL + p] = x = 0;
    }
    return (int)done;                               /* own: stock removes the pad's own unit and ends its sound */
}

/* Write a pending record into its pattern (UI task, the pad's release; the scan unmasked, each unit's write and mask bit
 * in a few masked instructions, nothing called there; no store calls but the touch). Returns non-zero when a step
 * changed. */
static uint32_t put(uint32_t t, const spill_t *x)
{
    uint8_t *rec = recorder(t), *pat = rec ? *(uint8_t **)(rec + REC_PATTERNS) : 0;
    if (!pat || x->pattern >= PATTERNS)
        return 0;
    pat += PATTERN_SIZE * x->pattern;
    uint32_t first = pat[PATTERN_FIRST], last = pat[PATTERN_LAST], changed = 0;
    for (uint32_t i = 0; i < x->n; i++) {
        uint32_t six = x->six[i], at = roll_step(x->step, six / SIXTHS, first, last), micro = six % SIXTHS;
        if (at >= STEPS || at == x->step)
            continue;                               /* a roll longer than the pattern: not back into the held step */
        volatile uint8_t *st = pat + STEP_SIZE * at;
        uint32_t mask = st[0], gate = 0, free = UNITS, dup = 0, gone = 0;
        for (uint32_t u = 0; u < UNITS; u++) {
            const volatile uint8_t *v = st + 4u + 4u * u;
            if (!(mask >> u & 1u)) {
                if (free == UNITS)
                    free = u;
            } else if (x->remove) {
                if (v[U_MICRO] == micro && v[U_NOTE] == x->note[i])
                    gone |= 1u << u;
            } else {
                dup |= v[U_NOTE] == x->note[i] && v[U_MICRO] == micro;
                if ((v[U_GATE] & GATE_BITS) > gate)
                    gate = v[U_GATE] & GATE_BITS;
            }
        }
        if (x->remove) {
            if (gone) {
                uint32_t primask = slim_irq_save();
                st[0] = (uint8_t)(st[0] & ~gone);   /* the bytes stay, as stock's removal */
                slim_irq_restore(primask);
                changed = 1;
                if (trig_mark == 1u && !(st[0] & UNIT_BITS))
                    trig_note_set((uint8_t *)st, 0);   /* PL20: the step's last note gone: its condition too */
            }
            continue;
        }
        if (dup || free == UNITS)
            continue;                               /* already there, or the step is full: left out */
        uint32_t g = gate ? gate : GATE_STEP, primask = slim_irq_save();
        uint32_t now = st[0], left = ~now & 0x3Fu;
        if (now >> free & 1u)                       /* a Main-task commit took it meanwhile: the next free one */
            free = left ? (uint32_t)__builtin_ctz(left) : UNITS;
        if (free < UNITS) {
            volatile uint8_t *v = st + 4u + 4u * free;
            v[U_NOTE] = x->note[i];
            v[U_GATE] = (uint8_t)g;
            v[U_MICRO] = (uint8_t)micro;
            v[U_VEL] = x->vel;
            if (!gate)
                st[1] = PROB_ALWAYS;                /* an empty step: one step, always, as stock's add */
            BARRIER();
            st[0] = (uint8_t)(now | 1u << free);    /* last: the unit is complete before the step plays it */
            changed = 1;
        }
        slim_irq_restore(primask);
    }
    return changed;
}

void step_spill_release(void *view, uint32_t pad)
{
    uint8_t *sink = chord_note_sink(view);
    if (!sink || pad >= PADS)
        return;
    uint32_t t = sink[SINK_TRACK], changed = 0;
    if ((entering & 0xFFu) == pad + 1u)
        entering = 0;                               /* a latch whose add never came */
    for (uint32_t i = 0; i < SPILLS; i++) {
        spill_t *x = &spill[i];
        if (x->track != t + 1u || x->pad != pad)
            continue;
        changed |= put(t, x);
        x->track = 0;
    }
    if (changed)
        rec_touch(recorder(t));                     /* once: the steps show at once (PL19 spike q3_spill) */
}
