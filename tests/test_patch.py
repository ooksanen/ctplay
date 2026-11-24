import random

import pytest

from playbuild import paths
from playbuild.patch import apply_patch, make_patch, own_bytes, stock_runs


def _synthetic():
    rnd = random.Random(7)
    src = bytes(rnd.randrange(256) for _ in range(6000))
    dst = bytearray(src)
    for pos in (100, 900, 2500, 5000):
        dst[pos:pos + 5] = bytes(rnd.randrange(256) for _ in range(5))
    del dst[3000:3040]
    dst += bytes(rnd.randrange(256) for _ in range(500))
    return src, bytes(dst)


def test_round_trip_on_synthetic_bytes():
    src, dst = _synthetic()
    assert apply_patch(src, make_patch(src, dst)) == dst


def test_no_add_holds_a_run_of_the_source():
    src, dst = _synthetic()
    assert stock_runs(own_bytes(make_patch(src, dst)), src) == []
    # 7 equal bytes are below the rule: an ADD may hold them
    short = bytes(range(100, 107))
    src2 = bytes(range(0, 100)) + short + bytes(range(200, 250))
    dst2 = b"\xf0\xf1" + short + b"\xf2\xf3"
    ops = make_patch(src2, dst2)
    assert apply_patch(src2, ops) == dst2
    assert all(op[0] == 1 for op in ops)


def test_pl21_patch_against_stock(pl21_image):
    if not paths.STOCK_BIN.exists():
        pytest.skip("stock firmware image missing")
    stock = paths.STOCK_BIN.read_bytes()
    ops = make_patch(stock, pl21_image)
    assert apply_patch(stock, ops) == pl21_image
    own = own_bytes(ops)
    assert stock_runs(own, stock) == []
    assert 30_000 <= len(own) <= 60_000, len(own)   # a sanity band: PL21 measures 40,199
