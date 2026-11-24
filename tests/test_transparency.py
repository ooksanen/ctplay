"""A build with every SL00D hook installed and handlers that change nothing must behave exactly like stock.

Note: the DSP-write comparison is vacuous in these scripts (no step writes to the DSP); LEDs, controller state and
events are the effective comparison."""
import random

import pytest

from harness import Harness

pytestmark = pytest.mark.emu
SAFE_BUTTONS = [0, 1, 2, 4, 7, 8, 13, 14, 15, 24]     # upstream's fuzz set + Drum 4


def script(seed: int, n: int) -> list[tuple]:
    rnd = random.Random(seed)
    steps = []
    for _ in range(n):
        r = rnd.random()
        if r < 0.5:
            steps.append(("press", rnd.choice(SAFE_BUTTONS), rnd.random() < 0.25))
        elif r < 0.8:
            steps.append(("pad", rnd.randrange(32)))
        else:
            steps.append(("knob", rnd.randrange(8), rnd.choice([-3, -1, 1, 3])))
    return steps


def page_free(steps: list[tuple]) -> list[tuple]:
    """The script without Shift + Synth 1 / 2, MIDI 1 / 2 (from PL06 they open the play pages), Shift + Drum 1-4 (from
    PL16 the drum pages) and Shift + 1-16/17-32 (from PL07 it flips the quick view); stock: nothing."""
    return [s for s in steps if not (s[0] == "press" and (s[1] < 8 or s[1] == 21) and s[2])]


def run(h: Harness, step: tuple) -> None:
    if step[0] == "press":
        h.press(step[1], shift=step[2])
    elif step[0] == "pad":
        h.pad(step[1])
    else:
        h.knob(step[1], step[2])


def test_led_refresh_is_identical_at_start(stock_image, null_image):
    assert Harness(stock_image).leds() == Harness(null_image).leds()


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_null_hooks_are_invisible(seed, stock_image, null_image):
    a, b = Harness(stock_image), Harness(null_image)
    for i, step in enumerate(script(seed, 10)):
        run(a, step)
        run(b, step)
        oa, ob = a.outputs(), b.outputs()
        assert oa == ob, f"seed {seed}, step {i} {step}: stock and slim differ"
    assert a.forbidden_writes == [], f"stock touched flash/option-byte ranges: {a.forbidden_writes}"
    assert b.forbidden_writes == []
