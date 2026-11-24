import pytest

from playbuild import memory, paths
from playbuild.errors import BuildError


def test_real_map_picks_flash_and_heap_tail():
    r = memory.load(paths.MEMORY)
    assert memory.pick(r, "flash").size == 0x08080000 - 0x0805CDE0
    ram = memory.pick(r, "ram")
    assert ram.name == "heap_tail" and ram.size == 240      # itcm is opt-in (auto = false), backup SRAM excluded
    assert r["project_reserved"].size == 65


def test_place_top_down_aligns_below_the_end():
    ram = memory.pick(memory.load(paths.MEMORY), "ram")
    assert memory.place_top_down(ram, 100) == 0x20044DF0    # 0x20044E58 - 100 = ...DF4, aligned down to 8
    assert memory.place_top_down(ram, 240) == 0x20044D68


def test_place_top_down_refuses_overflow():
    ram = memory.pick(memory.load(paths.MEMORY), "ram")
    with pytest.raises(BuildError, match="241 B do not fit in heap_tail"):
        memory.place_top_down(ram, 241)


def test_static_regions_need_opt_in(tmp_path):
    p = tmp_path / "m.toml"
    p.write_text('[region.r]\nkind = "ram"\nstart = 0x100\nend = 0x200\nconfidence = "static"\nsource = "x"\n')
    regions = memory.load(p)
    with pytest.raises(BuildError, match="exactly one usable ram region"):
        memory.pick(regions, "ram")
    assert memory.pick(regions, "ram", allow_static=True).size == 0x100


def test_bad_confidence_is_rejected(tmp_path):
    p = tmp_path / "m.toml"
    p.write_text('[region.r]\nkind = "ram"\nstart = 0\nend = 4\nconfidence = "probably"\nsource = "x"\n')
    with pytest.raises(BuildError, match="confidence"):
        memory.load(p)


def test_itcm_record_from_the_sl00d_device_run():
    r = memory.load(paths.MEMORY)
    assert (r["itcm_block0"].confidence, r["itcm_block0"].start, r["itcm_block0"].end) == ("excluded", 0x0, 0x400)
    itcm = r["itcm"]
    assert (itcm.confidence, itcm.start, itcm.end, itcm.auto) == ("verified", 0x400, 0x4000, False)
    assert memory.pick(r, "ram").name == "heap_tail"        # opt-in regions are never picked automatically


def test_project_tail_region():
    r = memory.load(paths.MEMORY)["project_tail"]
    assert (r.kind, r.size, r.confidence) == ("saved", 1000, "verified")
