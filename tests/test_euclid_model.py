"""The Euclidean rhythm's Python model (spec 2026-10-17-euclidean-design.md, "The rhythm"): hit at step i when
((i + r) * k) mod n < k."""
import euclid_model


def test_model_known_rhythms():
    assert euclid_model.mask(3, 8, 0) == 0b01001001        # tresillo x..x..x. (steps 0, 3, 6)
    assert bin(euclid_model.mask(5, 16, 0)).count("1") == 5 and euclid_model.mask(5, 16, 0) & 1
    assert euclid_model.mask(0, 16, 0) == 0 and euclid_model.mask(16, 16, 3) == 0xFFFF
    assert euclid_model.mask(40, 32, 0) == 0xFFFFFFFF
    assert euclid_model.mask(3, 8, 1) == 0b10100100        # one step earlier (steps 2, 5, 7)
