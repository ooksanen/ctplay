import pytest
from capstone import CS_ARCH_ARM, CS_MODE_MCLASS, CS_MODE_THUMB, Cs

from playbuild import features, hooks, paths, symbols
from playbuild.errors import BuildError

STOCK = paths.STOCK_BIN.read_bytes()
SYM = symbols.load(paths.SYMBOLS)
TARGETS = hooks.branch_targets(paths.LISTING)
MD = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)


def entry(addr, expect, displace):
    return symbols.HookPoint("t", "entry", "ui", (), "void", addr=addr, expect=bytes.fromhex(expect), displace=displace)


def test_listing_branch_targets_are_parsed():
    assert 0x0803334A in TARGETS            # bpl at 0x08033332
    assert 0x08034196 in TARGETS            # bl led_task


def test_button_press_entry_is_movable():
    hooks.check_entry(SYM.hooks["button_press"], STOCK, TARGETS)


def test_pc_relative_instruction_is_refused():
    with pytest.raises(BuildError, match="depends on the program counter"):
        hooks.check_entry(entry(0x0801D7D8, "084a0146", 4), STOCK, TARGETS)     # ldr r2, [pc, #0x20]


def test_partial_instruction_is_refused():
    with pytest.raises(BuildError, match="instruction boundary"):
        hooks.check_entry(entry(0x080292F8, "f8b50d46dff8", 6), STOCK, TARGETS)  # push; mov; ldr.w (4 B) cut


def test_branch_into_displaced_bytes_is_refused():
    with pytest.raises(BuildError, match="branches into the displaced bytes"):
        hooks.check_entry(SYM.hooks["button_press"], STOCK, TARGETS | {0x08033322})


def test_patch_encodings_decode_to_the_targets():
    addr, data = hooks.patch_entry(SYM.hooks["button_press"], 0x0805CE00)
    ins = next(MD.disasm(data, addr))
    assert (addr, ins.mnemonic, ins.op_str) == (0x08033320, "b.w", "#0x805ce00")
    for site, data in hooks.patch_calls(SYM.hooks["led_task"], 0x0805CE40):
        ins = next(MD.disasm(data, site))
        assert (ins.mnemonic, ins.op_str) == ("bl", "#0x805ce40")


def test_main_ms_entry_is_movable():
    hooks.check_entry(SYM.hooks["main_ms"], STOCK, TARGETS)


@pytest.mark.parametrize("name", ["seq_tick", "seq_start", "ctrl_pad_press", "ctrl_pad_release", "rec_commit"])
def test_arpeggiator_entries_are_movable(name):
    hooks.check_entry(SYM.hooks[name], STOCK, TARGETS)


@pytest.mark.parametrize("name", ["session_save", "session_applied"])
def test_saved_settings_call_sites_retarget(name):
    for site, data in hooks.patch_calls(SYM.hooks[name], 0x0805CE40):
        ins = next(MD.disasm(data, site))
        assert (ins.mnemonic, ins.op_str) == ("bl", "#0x805ce40")


def test_entry_and_call_hooks_on_one_function():
    """PL15 recfix: rec_commit (the commit's entry) and rec_committed (its three callers) on one stock function. The
    patches touch different bytes, and the call wrapper's rec_write() goes through the veneer to the entry, which the
    entry patch sends through its stub: the entry handlers, stock's commit, then the call handlers."""
    from playbuild import codegen
    entry, call = SYM.hooks["rec_commit"], SYM.hooks["rec_committed"]
    assert SYM.functions[call.target].addr == entry.addr == 0x0803F7BE
    assert SYM.functions[call.target].expect == entry.expect
    hooks.check_entry(entry, STOCK, TARGETS)
    symbols.verify(SYM, STOCK)                                    # each site is `bl 0x803f7be` in stock
    ea, eb = hooks.patch_entry(entry, 0x0805CE00)
    spans = [(ea, ea + len(eb))] + [(s, s + len(b)) for s, b in hooks.patch_calls(call, 0x0805CE40)]
    assert all(e1 <= a2 or e2 <= a1 for i, (a1, e1) in enumerate(spans) for a2, e2 in spans[i + 1:]), spans
    for site, data in hooks.patch_calls(call, 0x0805CE40):
        ins = next(MD.disasm(data, site))
        assert (ins.mnemonic, ins.op_str) == ("bl", "#0x805ce40")
    assert "rec_write:\n    ldr.w pc, 1f\n    .p2align 2\n1:  .word 0x0803f7bf" in codegen.veneers_s(SYM)


# Byte patches (beta 2): checked against the official image and the version's hook sites.
CC27 = features.BytePatch(0x080215B2, b"\xea\xd4", b"\xef\xd4", "CC 27")


def test_the_cc27_patch_matches_stock():
    hooks.check_patches([("stockfix", CC27)], STOCK, [SYM.hooks["button_press"], SYM.hooks["main_ms"]])


@pytest.mark.parametrize("patch, match", [
    (features.BytePatch(0x080215B2, b"\xef\xd4", b"\xea\xd4", "x"), "stock has ea d4"),
    (features.BytePatch(0x0800FFFE, b"\x00\x00", b"\x01\x00", "x"), "outside the stock image"),
    (features.BytePatch(0x08010000 + len(STOCK), b"\xff\xff", b"\x00\x00", "x"), "outside the stock image"),
])
def test_a_byte_patch_off_stock_is_refused(patch, match):
    with pytest.raises(BuildError, match=match):
        hooks.check_patches([("f", patch)], STOCK, [])


def test_a_byte_patch_over_a_hook_site_is_refused():
    hp = SYM.hooks["button_press"]                                      # an entry hook: [addr, addr + displace)
    inside = features.BytePatch(hp.addr + 2, STOCK[hp.addr + 2 - 0x08010000:hp.addr + 4 - 0x08010000],
                                b"\x00\xbf", "x")
    with pytest.raises(BuildError, match="overlaps hook button_press"):
        hooks.check_patches([("f", inside)], STOCK, [hp])
    hooks.check_patches([("f", inside)], STOCK, [])                    # fine when the version does not use the hook
    call = next(h for h in SYM.hooks.values() if h.kind == "call" and h.sites)
    site = call.sites[0]
    on_call = features.BytePatch(site, STOCK[site - 0x08010000:site + 2 - 0x08010000], b"\x00\xbf", "x")
    with pytest.raises(BuildError, match=f"overlaps hook {call.name}"):
        hooks.check_patches([("f", on_call)], STOCK, [call])


def test_overlapping_byte_patches_are_refused():
    wide = features.BytePatch(0x080215B0, STOCK[0x115B0:0x115B4], b"\0\0\0\0", "x")       # covers 0x080215B2 too
    with pytest.raises(BuildError, match="overlaps patch a"):
        hooks.check_patches([("a", CC27), ("b", wide)], STOCK, [])
