/* Chord maths (spec section 2). Tests: tests/chord_model.py is the reference, test_chord.py compares. */
#include "chord_math.h"

#define MAJOR_MASK  0x00111044u      /* C#, D#, F#, G#, A# outside the scale: the major scale on the root */
#define WALK_LIMIT  (12u * 9u)       /* semitones walked at most: ends the walk even for a mask without notes */
#define MAX_TONES   6u               /* 5 shape tones + bass */

static const uint8_t SHAPES[13][6] = {     /* count, then degree offsets */
    {1, 0},                               /* single */
    {3, 0, 2, 4},                         /* triad */
    {4, 0, 2, 4, 6},                      /* 7th */
    {5, 0, 2, 4, 6, 8},                   /* 9th */
    {3, 0, 1, 4},                         /* sus2 */
    {3, 0, 3, 4},                         /* sus4 */
    {4, 0, 2, 4, 8},                      /* add9 */
    {4, 0, 2, 4, 5},                      /* 6th */
    {3, 0, 4, 7},                         /* power: root, 5th, octave */
    {3, 0, 2, 6},                         /* shell 7: root, 3rd, 7th */
    {4, 0, 3, 6, 9},                      /* quartal: stacked 4ths */
    {4, 0, 3, 4, 6},                      /* 7sus4 */
    {5, 0, 2, 4, 5, 8},                   /* 6/9 */
};

uint32_t chord_shape_index(uint32_t settings)
{
    uint32_t r = CHORD_SHAPE2(settings);
    return CHORD_SHAPE(settings) == 0u && r >= 1u && r <= 5u ? 7u + r : CHORD_SHAPE(settings);
}

uint32_t chord_shape_tones(uint32_t settings)
{
    return SHAPES[chord_shape_index(settings)][0];
}

static int in_scale(uint32_t mask, int32_t note)
{
    return ((mask >> (2u * ((uint32_t)note % 12u))) & 3u) == 0u;
}

static int32_t degrees_up(uint32_t mask, int32_t note, uint32_t steps)
{
    for (uint32_t n = 0; steps && n < WALK_LIMIT; n++) {
        note++;
        if (in_scale(mask, note))
            steps--;
    }
    return note;
}

/* Stock plays a keyboard pitch when pitch + key is within 12-139 (its pad check 0x080523E8). */
static int playable(int32_t v, uint32_t key)
{
    return v + (int32_t)key >= 12 && v + (int32_t)key <= 139;
}

/* v raised by octaves until it is above floor: with a bass, the bass stays the lowest note. */
static int32_t lift(int32_t v, int32_t floor)
{
    while (v <= floor)
        v += 12;
    return v;
}

uint32_t chord_notes(uint32_t root, uint32_t mask, uint32_t settings, uint8_t *out)
{
    const uint8_t *shape = SHAPES[chord_shape_index(settings)];
    uint32_t n = shape[0], inv = CHORD_INV(settings), spread = CHORD_SPREAD(settings), key = CHORD_KEY(settings);
    int32_t tones[MAX_TONES];

    if (mask == 0u)
        mask = MAJOR_MASK;
    for (uint32_t i = 0; i < n; i++)
        tones[i] = degrees_up(mask, (int32_t)root, shape[1u + i]);
    if (inv > 0u && inv < n)
        for (uint32_t i = inv; i < n; i++)
            tones[i] -= 12;
    if (spread == SPREAD_DROP2 && n >= 3u) {
        uint32_t top = 0, pick = n;      /* the highest tone, then the highest other tone that is not tone 0 */
        for (uint32_t i = 1; i < n; i++)
            if (tones[i] > tones[top])
                top = i;
        for (uint32_t i = 1; i < n; i++)
            if (i != top && (pick == n || tones[i] > tones[pick]))
                pick = i;
        tones[pick] -= 12;
    } else if (spread == SPREAD_WIDE) {
        if (n > 1u)
            tones[1] += 12;
        if (n > 3u)
            tones[3] += 12;
    }
    uint32_t rootless = CHORD_BASS(settings) && CHORD_ROOTLESS(settings), skip = MAX_TONES;   /* no tone left out */
    if (rootless)                        /* the pad is the bass: the chord an octave up, nothing below the pad */
        for (uint32_t i = 1; i < n; i++)
            tones[i] = lift(tones[i] + 12, (int32_t)root);
    else if (CHORD_BASS(settings)) {
        if (n >= 5u && playable((int32_t)root - 12, key))   /* 6 notes with the bass: leave out the 5th (degree 4) */
            for (uint32_t i = 1; i < n; i++)
                if (shape[1u + i] == 4u)
                    skip = i;
        for (uint32_t i = 1; i < n; i++) /* nothing below the bass (inversion + drop-2 can lower a tone twice) */
            tones[i] = lift(tones[i], (int32_t)root - 12);
        tones[n++] = (int32_t)root - 12;
    }

    uint32_t count = 0;
    for (uint32_t i = 1; i < n; i++) {
        int32_t v = tones[i];
        if (!playable(v, key) || v == (int32_t)root || i == skip)
            continue;
        if (rootless && (v - (int32_t)root) % 12 == 0)
            continue;                    /* rootless: no other note with the root's name */
        uint32_t dup = 0;
        for (uint32_t j = 0; j < count; j++)
            if (out[j] == (uint8_t)v)
                dup = 1;
        if (!dup && count < CHORD_MAX_OTHER)
            out[count++] = (uint8_t)v;
    }
    return count;
}

uint32_t chord_degree_class(uint32_t root, uint32_t mask, uint32_t degree)
{
    return (uint32_t)degrees_up(mask ? mask : MAJOR_MASK, (int32_t)root, degree) % 12u;
}

static uint32_t dist(uint32_t a, uint32_t b)
{
    return a > b ? a - b : b - a;
}

uint32_t chord_lead(uint32_t root, uint32_t mask, uint32_t settings, const uint8_t *prev, uint32_t prev_n,
                    uint32_t kind)
{
    if (prev_n == 0u)
        return CHORD_INV(settings);
    uint32_t cands = chord_shape_tones(settings), best = 0u, best_n = 0u, best_a = 0u, best_close = 0u;
    uint32_t pmin = prev[0], pmax = prev[0];
    for (uint32_t i = 1; i < prev_n; i++) {
        if (prev[i] < pmin)
            pmin = prev[i];
        if (prev[i] > pmax)
            pmax = prev[i];
    }
    if (cands > 4u)
        cands = 4u;
    for (uint32_t inv = 0; inv < cands; inv++) {
        uint8_t notes[6];
        notes[0] = (uint8_t)root;
        uint32_t n = 1u + chord_notes(root, mask, (settings & ~(3u << 3)) | inv << 3, notes + 1);
        uint32_t lo = notes[0], hi = notes[0], close = 0u;
        for (uint32_t i = 0; i < n; i++) {
            uint32_t near = 0xFFFFu;
            for (uint32_t j = 0; j < prev_n; j++)
                if (dist(notes[i], prev[j]) < near)
                    near = dist(notes[i], prev[j]);
            close += near;
            if (notes[i] < lo)
                lo = notes[i];
            if (notes[i] > hi)
                hi = notes[i];
        }
        uint32_t a = kind == 2u ? dist(hi, pmax) : kind == 3u ? dist(lo, pmin) : close;
        /* strict improvement only, so a tie keeps the lower inversion; fewer notes never compete */
        if (n > best_n || (n == best_n && (a < best_a || (a == best_a && close < best_close)))) {
            best = inv;
            best_n = n;
            best_a = a;
            best_close = close;
        }
    }
    return best;
}
