"""Reference model of features/chord/trig_math.c (trig conditions, PL20).

The 9-bit code, one encoding for drums and note tracks: 0 = none; a cycle of length L (2-8) with ticked passes `mask`
(bit i = pass i + 1, never 0) is (1 << L) | mask; the eight specials are TRIG_SPECIAL. The codes 4..64 that are not a
special (and 128, 256) are empty cycles: they read as none."""
TRIG_SPECIALS = 8
TRIG_FIRST, TRIG_NOT_FIRST, TRIG_FILL, TRIG_NOT_FILL, TRIG_PRE, TRIG_NOT_PRE, TRIG_LAST, TRIG_NOT_LAST = range(8)
TRIG_SPECIAL = [1, 2, 3, 4, 8, 16, 32, 64]
TRIG_COUNT_MOD = 840                    # the LCM of 1..8: a count reaching 2 x 840 goes back to 840 (trig_next_count)
TRIG_TAP, TRIG_HOLD, TRIG_SHIFT = 0, 1, 2
TRIG_NONE, TRIG_CYCLE, TRIG_SPECIAL_KIND = 0, 1, 2

COL_OFF, COL_GREEN, COL_GREEN_DIM, COL_YELLOW, COL_YELLOW_DIM = 0x00, 0x17, 0x18, 0x2D, 0x2E
COL_ORANGE, COL_ORANGE_DIM, COL_CYAN, COL_CYAN_DIM, COL_VIOLET, COL_VIOLET_DIM = 0x45, 0x46, 0x4D, 0x4E, 0x49, 0x4A
# per special: its colour (bright, dim): FIRST, FILL, PRE and LAST families, each with its NOT
SPECIAL_COL = [(COL_GREEN, COL_GREEN_DIM)] * 2 + [(COL_ORANGE, COL_ORANGE_DIM)] * 2 \
    + [(COL_VIOLET, COL_VIOLET_DIM)] * 2 + [(COL_YELLOW, COL_YELLOW_DIM)] * 2


def trig_special(code):
    return TRIG_SPECIAL.index(code) if code in TRIG_SPECIAL else TRIG_SPECIALS


def _cycle_parts(code):
    if code < 4 or code > 511 or code in TRIG_SPECIAL:
        return 0, 0
    L = code.bit_length() - 1
    mask = code & ((1 << L) - 1)
    return (L, mask) if 2 <= L <= 8 and mask else (0, 0)


def trig_len(code):
    return _cycle_parts(code)[0]


def trig_mask(code):
    return _cycle_parts(code)[1]


def trig_kind(code):
    if trig_special(code) < TRIG_SPECIALS:
        return TRIG_SPECIAL_KIND
    return TRIG_CYCLE if trig_len(code) else TRIG_NONE


def trig_cycle(length, mask):
    if not 2 <= length <= 8 or not 0 < mask < (1 << length):
        return 0
    return (1 << length) | mask


def trig_plays(code, count, pre, fill, last):
    """1 when the condition lets the step play on pass count + 1 (count 0-based)."""
    kind = trig_kind(code)
    if kind == TRIG_CYCLE:
        return (trig_mask(code) >> (count % trig_len(code))) & 1
    if kind == TRIG_SPECIAL_KIND:
        s = trig_special(code)
        return int([count == 0, count != 0, bool(fill), not fill, bool(pre), not pre, bool(last), not last][s])
    return 1


def trig_next_count(count):
    """A pass's count after one more pass (trig.c trig_on_pass): below 2 x 840, then back to 840, never to 0, so FIRST
    plays once per start-over and every cycle (L 2-8 divides 840) reads as an unwrapped count."""
    count += 1
    return count - TRIG_COUNT_MOD if count >= 2 * TRIG_COUNT_MOD else count


def trig_conditional(code, prob):
    """1 when the step sets PRE's state: not none and not PRE / NOT PRE, or a probability below 7."""
    kind = trig_kind(code)
    if kind == TRIG_SPECIAL_KIND and trig_special(code) in (TRIG_PRE, TRIG_NOT_PRE):
        return 0
    return int(kind != TRIG_NONE or prob < 7)


def trig_edit(code, pad, gesture, drum):
    if pad > 7:
        return code
    if gesture == TRIG_SHIFT:
        if not drum and pad in (TRIG_FILL, TRIG_NOT_FILL):
            return code
        return 0 if code == TRIG_SPECIAL[pad] else TRIG_SPECIAL[pad]
    length = pad + 1
    if gesture == TRIG_HOLD:
        if pad == 0:
            return 0
        if trig_kind(code) == TRIG_CYCLE:
            if trig_len(code) == length:
                return 0
            return trig_cycle(length, (trig_mask(code) & ((1 << length) - 1)) or 1)
        return trig_cycle(length, 1)
    if trig_kind(code) == TRIG_CYCLE and pad < trig_len(code):
        mask = trig_mask(code) ^ (1 << pad)
        return trig_cycle(trig_len(code), mask) if mask else 0
    return code


def trig_row4(code, shift, drum):
    out = [COL_OFF] * 8
    if shift:
        for i in range(8):
            if not drum and i in (TRIG_FILL, TRIG_NOT_FILL):
                continue
            bright, dim = SPECIAL_COL[i]
            out[i] = bright if code == TRIG_SPECIAL[i] else dim
        return out
    kind = trig_kind(code)
    if kind == TRIG_CYCLE:
        for i in range(trig_len(code)):
            out[i] = COL_CYAN if (trig_mask(code) >> i) & 1 else COL_CYAN_DIM
    elif kind == TRIG_SPECIAL_KIND:
        dim = SPECIAL_COL[trig_special(code)][1]
        out = [dim] * 8
    return out


def trig_drum_get(pattern, step):
    return pattern[0x88 + step] | (pattern[0x84 + (step >> 3)] >> (step & 7) & 1) << 8


def trig_drum_set(pattern, step, code):
    pattern[0x88 + step] = code & 0xFF
    bit = 1 << (step & 7)
    pattern[0x84 + (step >> 3)] = (pattern[0x84 + (step >> 3)] & ~bit) | (bit if code & 0x100 else 0)


def trig_note_get(step):
    return step[2] | (step[3] & 1) << 8


def trig_note_set(step, code):
    step[2] = code & 0xFF
    step[3] = code >> 8 & 1


plays = trig_plays                               # the plan's short name
