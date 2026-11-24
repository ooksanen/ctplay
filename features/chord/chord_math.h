/* Chord maths: pure functions, no stock calls (spec section 2). */
#pragma once
#include <stdint.h>

#define CHORD_MAX_OTHER   4u           /* room for the other notes: a 9th has 4, and the bass modes keep a chord to 5 notes
                                          * with the pad's own (a bass below leaves out the 5th), as the synth holds 4-5 */

/* Settings byte, one per track. */
#define CHORD_SHAPE(s)    ((s) & 7u)           /* 0 single, 1 triad, 2 7th, 3 9th, 4 sus2, 5 sus4, 6 add9, 7 6th */
#define CHORD_INV(s)      (((s) >> 3) & 3u)    /* inversion 0-3 */
#define CHORD_SPREAD(s)   (((s) >> 5) & 3u)    /* SPREAD_* */
#define CHORD_BASS(s)     (((s) >> 7) & 1u)    /* add the root an octave below */
#define CHORD_ROOTLESS(s) (((s) >> 8) & 1u)    /* with bass: the pad is the bass, the chord an octave up without its root */
#define CHORD_SHAPE2(s)   (((s) >> 9) & 0xFu)  /* PL15: the row-2 shape 0-5, used only while CHORD_SHAPE is 0 (single) */
#define CHORD_KEY(s)      (((s) >> 16) & 0xFFu) /* the project root 0-11: a note plays when pitch + key is within 12-139 */
#define CHORD_SHAPES      13u          /* 0-7 row 1, 8-12 the row-2 shapes: power, shell 7, quartal, 7sus4, 6/9 */
#define CHORD_HAS_SHAPE(s) (chord_shape_index(s) != 0u)
#define SPREAD_CLOSE      0u
#define SPREAD_DROP2      1u
#define SPREAD_WIDE       2u

/* The effective shape 0-12: row 1 wins; with row 1 on single, row-2 shape r (1-5) is shape 7 + r. */
uint32_t chord_shape_index(uint32_t settings);
/* Its tone count (the pad's own note included). */
uint32_t chord_shape_tones(uint32_t settings);

/* Voice leading: the inversion 0-3 of the chord on `root` that moves least from the previous chord `prev` (prev_n
 * notes). Candidates are inversions 0 .. min(tones, 4) - 1 (`settings` as for chord_notes); only those with the most
 * notes compete. kind 1 close: least summed distance of the candidate's notes to the nearest previous note; 2 top line:
 * least move of the highest note; 3 bottom line: of the lowest; ties go to the close measure, then the lowest
 * inversion. No previous chord (prev_n 0): the stored inversion CHORD_INV(settings). */
uint32_t chord_lead(uint32_t root, uint32_t mask, uint32_t settings, const uint8_t *prev, uint32_t prev_n,
                    uint32_t kind);

/* The chord's notes other than `root` (a keyboard pitch, root-relative +12) in the scale `mask` (2 bits per semitone
 * from the project root, 0 = in the scale; 0 = Chromatic, which uses the major scale). Writes at most
 * CHORD_MAX_OTHER notes to `out` and returns how many. `settings` is the settings byte plus CHORD_ROOTLESS in bit 8 and
 * the project root in bits 16-23 (CHORD_KEY): notes outside stock's playable range (as its pad check 0x080523E8) are
 * left out.
 * Bass modes: bass below adds root - 12 and leaves out the 5th when that would make 6 notes; rootless over bass
 * (bass + rootless) adds no bass: the chord's other notes move up an octave and none has the root's note name.
 * In both, every other note sits above the bass (raised by octaves if inversion + drop-2 put it below). */
uint32_t chord_notes(uint32_t root, uint32_t mask, uint32_t settings, uint8_t *out);

/* Pitch class (0-11, keyboard-pitch space) of the scale degree `degree` above `root` (0 = the root itself). */
uint32_t chord_degree_class(uint32_t root, uint32_t mask, uint32_t degree);
