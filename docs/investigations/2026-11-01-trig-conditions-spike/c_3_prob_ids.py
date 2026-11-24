"""Q1c: what identifies "a probability view is the bottom view", and what stock draws for row 4 (pads 24-31).

Every track: [ctrl + 0x6C], [cont + 0x18C], track_of, [ctrl + 0x152], the bottom view through stock's lookup
0x08043B6E(cont, 16) and its class, against the container slots ([cont + 0x68 + 4t] notes, [cont + 0xE0 + 4d] drums);
the view's LED buffer [[view + 4]] (16 halfwords: 0-7 row 3, 8-15 row 4) and led_task's pads 16-31, stopped, playing,
with Shift held, with 0x20039DE0 p0 = 1, and after a row-3 press (stock's listener redraws the buffer)."""
import struct

from c_lib import BTN_PATTERNS, CONT, MGR, H, hexrow


def buf(h):
    v = h.view_for(16)
    return struct.unpack("<16H", bytes(h.uc.mem_read(h.r32(h.r32(v + 4)), 32)))


def main():
    for t in range(8):
        h = H()
        h.open_prob(t)
        v = h.view_for(16)
        slot = CONT + (0x68 + 4 * t if t < 4 else 0xE0 + 4 * (t - 4))
        ids = h.ids()
        frames = {"stopped": h.leds()[16:32]}
        h.shift(True)
        frames["shift"] = h.leds()[16:32]
        h.shift(False)
        h.down(19)
        h.up(19)
        frames["row3 pressed"] = h.leds()[16:32]
        b = buf(h)
        h.press(BTN_PATTERNS, shift=True)
        h.open_prob(t)
        frames["0x20039DE0=1"] = h.leds()[16:32]
        h.play(200)
        frames["playing"] = h.leds()[16:32]
        print(f"track {t}: active {ids['active']} mode {ids['mode']} track_of {ids['track']} [ctrl+0x152] {ids['sub152']} "
              f"bottom view {hex(v)} class {ids['bottom_class']} top class {ids['top_class']}; "
              f"= container slot {hex(slot)}: {h.r32(slot) == v}")
        print(f"   LED buffer [[view+4]] = {hex(h.r32(h.r32(v + 4)))} (after the row-3 press): {hexrow(b)}")
        for k, f in frames.items():
            print(f"   led_task pads 16-31 {k:13s}: {hexrow(f)}")
        h.press(BTN_PATTERNS, shift=True)


if __name__ == "__main__":
    main()
