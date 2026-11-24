from helpers import write_feature, write_version
from playbuild import codegen, features, memory, paths, symbols

SYM = symbols.load(paths.SYMBOLS)
FLASH = memory.pick(memory.load(paths.MEMORY), "flash")


def version(tmp_path):
    fd = tmp_path / "f"
    write_feature(fd, "a", init="a_init", hooks=[("button_press", "a_btn", 50), ("led_task", "a_leds", 50)])
    write_feature(fd, "b", hooks=[("button_press", "b_btn", 10)])
    return features.load_version(write_version(tmp_path, "v", "SLX1", ["a", "b"], fd), SYM)


def test_split_decl():
    assert codegen.split_decl("void *ctrl") == ("void *", "ctrl")
    assert codegen.split_decl("uint32_t id") == ("uint32_t", "id")
    assert codegen.split_decl("uint16_t *out") == ("uint16_t *", "out")


def test_stock_header_declares_functions_and_data():
    h = codegen.stock_h(SYM)
    assert "volatile uint8_t *param_get(void *store, uint32_t index); /* 0x0803542C */" in h
    assert "extern volatile uint32_t heap_limit; /* 0x20002B44 */" in h
    assert "extern volatile uint32_t step_ticks[]; /* 0x0805B8B8 */" in h   # ctype "uint32_t[]": an array
    assert "mark_dirty" in h and "mark_dirty(" not in h            # tagged, no prototype: not callable


def test_veneers_jump_to_thumb_addresses():
    s = codegen.veneers_s(SYM)
    assert "param_get:\n    ldr.w pc, 1f" in s and ".word 0x0803542d" in s
    assert "mark_dirty:" not in s


def test_entry_stub_reruns_displaced_instructions(tmp_path):
    s = codegen.entry_stubs_s(SYM, version(tmp_path))
    assert "slim_entry_button_press:" in s and "bl      slim_dispatch_button_press" in s
    assert ".inst.n 0xb538" in s and ".inst.n 0x4604" in s
    assert ".word   0x08033325" in s


def test_dispatch_calls_handlers_in_priority_order(tmp_path):
    c = codegen.dispatch_c(SYM, version(tmp_path))
    assert c.index("b_btn((void *)a->r[0], (uint32_t)a->r[1], &a->ret)") < c.index("a_btn((void *)")
    assert "void slim_call_led_task(void *ctrl, uint16_t *out)" in c
    assert c.index("led_task(ctrl, out);") < c.index("a_leds(ctrl, out);")
    assert "void slim_features_init(void)\n{\n    a_init();\n}" in c


def test_linker_script_regions_and_symbols():
    ld = codegen.linker_script(SYM, FLASH, 0x20044DF0, 0x68, 0x20044E58)
    assert "FLASH (rx) : ORIGIN = 0x0805cde0, LENGTH = 0x23220" in ld
    assert "RAM (rw) : ORIGIN = 0x20044df0, LENGTH = 0x68" in ld
    assert "__slim_ram_top = 0x20044e58;" in ld and "heap_limit = 0x20002b44;" in ld


def test_linker_script_without_itcm_is_unchanged():
    ld = codegen.linker_script(SYM, FLASH, 0x20044DF0, 0x68, 0x20044E58)
    assert "ITCM" not in ld and ".itcm" not in ld
    assert ld == codegen.linker_script(SYM, FLASH, 0x20044DF0, 0x68, 0x20044E58, itcm=None)


def test_linker_script_with_itcm():
    ld = codegen.linker_script(SYM, FLASH, 0x20044DF0, 0x68, 0x20044E58, itcm=(0x3FF8, 8))
    assert "ITCM (rw) : ORIGIN = 0x00003ff8, LENGTH = 0x8" in ld
    itcm, data = ld.index(".itcm (NOLOAD)"), ld.index(".data :")
    assert itcm < data                                   # before .bss's *(.bss.*) could take the sections
    block = ld[itcm:data]
    assert "*(.bss.itcm.*)" in block and "__slim_itcm_start = .;" in block and "__slim_itcm_end = .;" in block
    assert "> ITCM" in block


def test_call_hook_with_a_result_passes_it_to_the_handlers_and_returns_it(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text((paths.SYMBOLS).read_text() +
                 '\n[hook.t_read]\nkind = "call"\ntarget = "dsp_read"\nsites = [0x080217EA]\n'
                 'args = ["uint32_t core", "uint32_t addr"]\nret = "uint32_t"\ncontext = "ui"\n')
    sym = symbols.load(p)
    fd = tmp_path / "f"
    write_feature(fd, "a", hooks=[("t_read", "a_read", 50)])
    v = features.load_version(write_version(tmp_path, "v", "SLX1", ["a"], fd), sym)
    c = codegen.dispatch_c(sym, v)
    assert "void a_read(uint32_t core, uint32_t addr, uint32_t result);" in c
    assert "uint32_t slim_call_t_read(uint32_t core, uint32_t addr)\n{\n    uint32_t result = dsp_read(core, addr);\n" in c
    assert "    if (!slim_ready())\n        return result;\n    a_read(core, addr, (uint32_t)result);\n    return result;\n}" in c


def test_void_call_hook_text_is_unchanged(tmp_path):
    c = codegen.dispatch_c(SYM, version(tmp_path))
    assert ("void slim_call_led_task(void *ctrl, uint16_t *out)\n{\n    led_task(ctrl, out);\n"
            "    if (!slim_ready())\n        return;\n    a_leds(ctrl, out);\n}\n") in c


def test_filters_change_the_result_and_observers_see_it_in_priority_order(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text((paths.SYMBOLS).read_text() +
                 '\n[hook.t_read]\nkind = "call"\ntarget = "dsp_read"\nsites = [0x080217EA]\n'
                 'args = ["uint32_t core", "uint32_t addr"]\nret = "uint32_t"\ncontext = "ui"\n')
    sym = symbols.load(p)
    fd = tmp_path / "f"
    write_feature(fd, "a", hooks=[("t_read", "a_watch", 40)])
    write_feature(fd, "b", hooks=[("t_read", "b_filter", 60, True)])
    v = features.load_version(write_version(tmp_path, "v", "SLX1", ["a", "b"], fd), sym)
    c = codegen.dispatch_c(sym, v)
    assert "void a_watch(uint32_t core, uint32_t addr, uint32_t result);" in c
    assert "uint32_t b_filter(uint32_t core, uint32_t addr, uint32_t result);" in c
    assert ("    a_watch(core, addr, (uint32_t)result);\n"
            "    result = (uint32_t)b_filter(core, addr, (uint32_t)result);\n    return result;\n}") in c


def test_saved_table_follows_the_lock(tmp_path):
    from playbuild.lock import Lock, LockEntry
    fd = tmp_path / "f"
    d = write_feature(fd, "a")
    (d / "feature.toml").write_text('saved_fix = "a_fix"\n' + (d / "feature.toml").read_text() +
                                    '\n[[saved]]\nsymbol = "a_y"\nbytes = 2\ndefault = "0108"\n'
                                    '\n[[saved]]\nsymbol = "a_x"\nbytes = 1\n')
    v = features.load_version(write_version(tmp_path, "v", "SLX1", ["a"], fd), SYM)
    lk = Lock(3, (LockEntry("a", "a_x", 0, 1), LockEntry("gone", "g", 1, 2, True, 1), LockEntry("a", "a_y", 3, 2)))
    h, c = codegen.saved_h(lk, 2), codegen.saved_c(v, lk)
    assert "#define SLIM_SAVED_LAYOUT 3u" in h and "#define SLIM_SAVED_LEN 5u" in h and "#define SLIM_SAVED_N 2u" in h
    assert c.index("{a_x, 1u, 0u, def_a_x}") < c.index("{a_y, 2u, 3u, def_a_y}")
    assert "static const uint8_t def_a_y[2] = {0x01, 0x08};" in c
    assert "void slim_saved_fix(void)\n{\n    a_fix();\n}" in c


# ---- the CTCtrl link's field table (PL12, spec 2026-10-18-ctctrl-link-design.md)

def link_version(tmp_path, features_=("chord", "countin", "saved", "link"), marker="PL12"):
    """A version over the real features and lock."""
    from playbuild import lock
    p = tmp_path / "v.toml"
    p.write_text(f'marker = "{marker}"\nfeatures = {list(features_)!r}\n'.replace("'", '"'))
    return features.load_version(p, SYM), lock.load(paths.SAVE_LOCK)


def test_link_table_lists_linked_live_fields_only(tmp_path):
    v, lk = link_version(tmp_path)
    h, c = codegen.link_h(v, lk), codegen.link_c(v, lk)
    assert "#define SLIM_LINK_N 18u" in h
    rows = [(0, 4), (4, 1), (5, 1), (6, 1), (7, 1), (8, 8), (24, 1), (25, 8), (37, 8),
            (53, 12), (65, 4), (77, 4), (81, 2), (87, 8), (95, 12), (107, 4), (115, 1), (116, 1)]   # page_quick 20, page_slot 33, tombstone 16, melody_seed 45, page_sub 69, euclid_last 73, drum_page 83, drum_seed 111: out
    assert "".join(f"    {{{o}u, {s}u, 1u}},\n" for o, s in rows) in c
    assert "#define SLIM_OFF_chord_settings 0u" in h and "#define SLIM_OFF_euclid_cfg 25u" in h
    assert "#define SLIM_OFF_page_slot 33u" in h and "#define SLIM_OFF_melody_seed 45u" in h                     # every saved field has its offset, linked or not


def test_link_field_offsets_are_16_bit(tmp_path):
    """saved2: link protocol 2 sends offsets in two bytes, and the payload may pass 255 B (format 2's room is 988)."""
    v, lk = link_version(tmp_path)
    assert "typedef struct {\n    uint16_t offset;\n    uint8_t size, rev;\n} slim_link_field_t;" in codegen.link_h(v, lk)


def test_link_marker_is_space_padded(tmp_path):
    v, lk = link_version(tmp_path)
    assert '#define SLIM_LINK_MARKER "PL12  "' in codegen.link_h(v, lk)


def test_link_functions_and_the_features_calls(tmp_path):
    from playbuild.lock import Lock
    fd = tmp_path / "f"
    for name, extra in (("a", 'link_valid = "a_valid"\nlink_apply = "a_apply"\n'), ("b", 'link_valid = "b_valid"\n'),
                        ("link", "")):
        d = write_feature(fd, name)
        (d / "feature.toml").write_text(extra + (d / "feature.toml").read_text())
    c = codegen.link_c(features.load_version(write_version(tmp_path, "v", "SLX1", ["a", "b", "link"], fd), SYM),
                       Lock(1, ()))
    assert ("int slim_link_valid(const uint8_t *cand, const uint8_t *old)\n{\n"
            "    return 1 && a_valid(cand, old) && b_valid(cand, old);\n}") in c
    assert "void slim_link_apply(const uint8_t *old)\n{\n    a_apply(old);\n}" in c
    c = codegen.link_c(features.load_version(write_version(tmp_path, "w", "SLX2", ["link"], fd), SYM), Lock(1, ()))
    assert "{\n    (void)cand;\n    (void)old;\n    return 1;\n}" in c and "{\n    (void)old;\n}" in c


def test_link_header_is_empty_without_the_link_feature(tmp_path):
    v, lk = link_version(tmp_path, ("chord", "countin", "saved"), "SLX1")
    h = codegen.link_h(v, lk)
    assert "#define SLIM_LINK_N 0u" in h and "slim_link_fields" not in h and "SLIM_LINK_MARKER" not in h
    assert "#define SLIM_OFF_chord_settings 0u" in h
    v, lk = link_version(tmp_path, ("chord",), "SLX2")              # chord without saved: still its offsets
    assert "#define SLIM_OFF_chord_settings 0u" in codegen.link_h(v, lk)
