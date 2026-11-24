import inspect

import pytest

from helpers import write_feature, write_version
from playbuild import build, checks, features, paths, symbols
from playbuild.errors import BuildError

SYM = symbols.load(paths.SYMBOLS)
HEAD = '#include "slim.h"\n#include "stock.h"\n'


def one(tmp_path, c_source, *, hooks=(("button_press", "t_btn", 50),), ram=64, stack=256, symbols_path=paths.SYMBOLS):
    fd = tmp_path / "f"
    write_feature(fd, "t", c_source=HEAD + c_source, hooks=hooks, ram=ram, stack=stack)
    v = write_version(tmp_path, "v", "SLX1", ["t"], fd)
    return build.build_once(v, tmp_path / "work", symbols_path)


BTN = "int t_btn(void *c, uint32_t id, uint32_t *r)\n{\n    (void)c; (void)r;\n"


def test_a_clean_feature_passes(tmp_path):
    img, _, man = one(tmp_path, BTN + "    return id == 99u ? SLIM_HANDLED : SLIM_PASS;\n}\n")
    assert man["stack"]["t_btn"] >= 0
    assert man["entry_stub_stack"] == 32
    assert "t_btn" in man["stack_uncounted_callees"]


def test_uncounted_stock_callees_are_reported(tmp_path):
    src = BTN + "    return *param_get(c, 0u) == id ? SLIM_HANDLED : SLIM_PASS;\n}\n"
    _, _, man = one(tmp_path, src)
    assert "param_get" in man["stack_uncounted_callees"]["t_btn"]


def test_hook_stack_counts_the_stub_dispatcher_and_inits(tmp_path):
    # The first hook call runs slim_ready() -> every init(): on that hook's stack, before any handler.
    fd = tmp_path / "f"
    src = (HEAD + "void t_init(void)\n{\n    volatile uint8_t buf[200];\n    buf[0] = 1u;\n    (void)buf;\n}\n"
           + BTN + "    return id == 99u ? SLIM_HANDLED : SLIM_PASS;\n}\n")
    write_feature(fd, "t", c_source=src, init="t_init", hooks=[("button_press", "t_btn", 50)])
    _, _, man = build.build_once(write_version(tmp_path, "v", "SLX1", ["t"], fd), tmp_path / "work")
    hook = man["hook_stack"]["button_press"]
    assert hook["bytes"] > checks.ENTRY_STUB_STACK + man["stack"]["t_init"] >= checks.ENTRY_STUB_STACK + 200
    assert hook["bytes"] > checks.ENTRY_STUB_STACK + man["stack"]["t_btn"]


def test_call_hook_stack_names_the_stock_target(tmp_path):
    src = "void t_leds(void *ctrl, uint16_t *out)\n{\n    (void)ctrl;\n    out[0] = 1u;\n}\n"
    _, _, man = one(tmp_path, src, hooks=(("led_task", "t_leds", 50),))
    hook = man["hook_stack"]["led_task"]
    assert hook["bytes"] >= man["stack"]["t_leds"] and "led_task" in hook["uncounted"]


def test_libgcc_helpers_are_reported(tmp_path):
    src = ("static volatile uint64_t num = 1000u;\n"
           + BTN + "    return num / id == 7u ? SLIM_HANDLED : SLIM_PASS;\n}\n")
    _, _, man = one(tmp_path, src)
    assert "__aeabi_uldivmod" in man["stack_uncounted_libgcc"]


def test_indirect_call_is_rejected(tmp_path):
    src = "static void (*volatile fp)(void);\n" + BTN + "    (void)id;\n    if (fp) fp();\n    return SLIM_PASS;\n}\n"
    with pytest.raises(BuildError, match="indirect calls"):
        one(tmp_path, src)


def test_stack_budget_is_enforced(tmp_path):
    src = BTN + "    volatile uint8_t buf[300];\n    buf[0] = (uint8_t)id;\n    return buf[0] == 255u ? SLIM_HANDLED : SLIM_PASS;\n}\n"
    with pytest.raises(BuildError, match=r"t_btn needs .* B of stack \(slim code only; not counted: .*\), budget 128 B"):
        one(tmp_path, src, stack=128)


def test_vla_is_rejected(tmp_path):
    src = BTN + "    volatile uint8_t buf[id & 15u];\n    buf[0] = 1u;\n    (void)buf;\n    return SLIM_PASS;\n}\n"
    with pytest.raises(BuildError, match="dynamic stack"):
        one(tmp_path, src)


def test_recursion_is_rejected(tmp_path):
    src = ("static __attribute__((noinline)) uint32_t f(uint32_t n)\n{\n    return n ? f(n - 1u) + f(n >> 1) + 1u : 0u;\n}\n"
           + BTN + "    return f(id) == 99u ? SLIM_HANDLED : SLIM_PASS;\n}\n")
    with pytest.raises(BuildError, match="recursion"):
        one(tmp_path, src)


def test_date_time_is_rejected(tmp_path):
    src = BTN + "    (void)id;\n    return __DATE__[0] == 'X' ? SLIM_HANDLED : SLIM_PASS;\n}\n"
    with pytest.raises(BuildError, match="date-time"):
        one(tmp_path, src)


def test_ram_budget_is_enforced(tmp_path):
    src = "static volatile uint8_t big[64];\n" + BTN + "    big[id & 63u] = 1u;\n    return SLIM_PASS;\n}\n"
    with pytest.raises(BuildError, match="t uses 64 B of RAM, budget 16 B"):
        one(tmp_path, src, ram=16)


def test_section_outside_the_linker_script_is_rejected(tmp_path):
    src = ('static volatile uint32_t keep __attribute__((section(".noinit")));\n'
           + BTN + "    keep = id;\n    return SLIM_PASS;\n}\n")
    with pytest.raises(BuildError, match=r"orphan section `\.noinit'"):
        one(tmp_path, src)


def test_flash_register_literal_is_rejected(tmp_path):
    src = BTN + "    (void)id;\n    *(volatile uint32_t *)0x40023C04u = 0x45670123u;\n    return SLIM_PASS;\n}\n"
    with pytest.raises(BuildError, match="flash interface"):
        one(tmp_path, src)


def test_flash_unlock_key_is_rejected(tmp_path):
    src = BTN + "    (void)id;\n    *(volatile uint32_t *)0x2006E000u = 0xCDEF89ABu;\n    return SLIM_PASS;\n}\n"
    with pytest.raises(BuildError, match="flash unlock key 2"):
        one(tmp_path, src)


def test_dsp_lock_from_the_dsp_tick_is_rejected(tmp_path):
    fixture = tmp_path / "symbols.toml"
    fixture.write_text("""
[function.mark_dirty]
addr = 0x0803BDCC
expect = "38b50d46"
proto = "void mark_dirty(void *obj, uint32_t what)"
tags = ["takes_dsp_lock"]

[data.heap_limit]
addr = 0x20002B44
ctype = "uint32_t"

[data.heap_cur]
addr = 0x20002B48
ctype = "uint32_t"

[hook.test_tick]
kind = "entry"
addr = 0x08029344
expect = "38b50446"
displace = 4
args = ["uint32_t core", "uint32_t addr"]
ret = "uint32_t"
context = "dsp_tick"
""")
    src = ("int t_tick(uint32_t core, uint32_t addr, uint32_t *r)\n{\n    (void)r;\n"
           "    if (core == 7u)\n        mark_dirty((void *)0, addr);\n    return SLIM_PASS;\n}\n")
    with pytest.raises(BuildError, match="slim_dispatch_test_tick -> t_tick -> mark_dirty"):
        one(tmp_path, src, hooks=(("test_tick", "t_tick", 50),), symbols_path=fixture)


def test_marker_clash_is_rejected(tmp_path):
    fd = tmp_path / "f"
    write_feature(fd, "a")
    v = features.load_version(write_version(tmp_path, "v", "SLX1", ["a"], fd), SYM)
    others = tmp_path / "versions"
    others.mkdir()
    (others / "older.toml").write_text('marker = "SLX1"\nfeatures = []\n')
    with pytest.raises(BuildError, match="marker SLX1 is already used by slim older.toml"):
        checks.check_marker(v, others)


def test_check_marker_has_no_upstream_parameter():
    assert list(inspect.signature(checks.check_marker).parameters) == ["version", "versions"]


def test_dsp_lock_from_the_main_task_is_allowed(tmp_path):
    """Main's soft timers run before Main takes the DSP lock, and stock sends its playback notes from there."""
    fixture = tmp_path / "symbols.toml"
    fixture.write_text("""
[function.mark_dirty]
addr = 0x0803BDCC
expect = "38b50d46"
proto = "void mark_dirty(void *obj, uint32_t what)"
tags = ["takes_dsp_lock"]

[data.heap_limit]
addr = 0x20002B44
ctype = "uint32_t"

[data.heap_cur]
addr = 0x20002B48
ctype = "uint32_t"

[hook.test_ms]
kind = "entry"
addr = 0x0803C410
expect = "10b50446"
displace = 4
args = ["uint32_t slot"]
ret = "void"
context = "main"
""")
    src = ("int t_ms(uint32_t slot, uint32_t *r)\n{\n    (void)r;\n"
           "    if (slot == 7u)\n        mark_dirty((void *)0, slot);\n    return SLIM_PASS;\n}\n")
    one(tmp_path, src, hooks=(("test_ms", "t_ms", 50),), symbols_path=fixture)


def test_dsp_lock_from_a_dsp_locked_hook_is_rejected(tmp_path):
    fixture = tmp_path / "symbols.toml"
    fixture.write_text("""
[function.mark_dirty]
addr = 0x0803BDCC
expect = "38b50d46"
proto = "void mark_dirty(void *obj, uint32_t what)"
tags = ["takes_dsp_lock"]

[function.dsp_read]
addr = 0x08029344
expect = "38b50446"
proto = "uint32_t dsp_read(uint32_t core, uint32_t addr)"

[data.heap_limit]
addr = 0x20002B44
ctype = "uint32_t"

[data.heap_cur]
addr = 0x20002B48
ctype = "uint32_t"

[hook.test_locked]
kind = "call"
target = "dsp_read"
sites = [0x080217EA]
args = ["uint32_t core", "uint32_t addr"]
ret = "uint32_t"
context = "dsp_locked"
""")
    src = ("void t_locked(uint32_t core, uint32_t addr, uint32_t result)\n{\n"
           "    if (core == 7u)\n        mark_dirty((void *)0, addr + result);\n}\n")
    with pytest.raises(BuildError, match="slim_call_test_locked -> t_locked -> mark_dirty takes the DSP-service lock "
                                         "while the synth note-on holds it"):
        one(tmp_path, src, hooks=(("test_locked", "t_locked", 50),), symbols_path=fixture)


ANY_FIXTURE = """
[function.mark_dirty]
addr = 0x0803BDCC
expect = "38b50d46"
proto = "void mark_dirty(void *obj, uint32_t what)"
tags = ["takes_dsp_lock"]

[function.session_refresh]
addr = 0x08029A00
expect = "08461146"
proto = "void session_refresh(void *obj, uint32_t what, uint32_t arg)"
tags = ["takes_dsp_lock"]

[data.heap_limit]
addr = 0x20002B44
ctype = "uint32_t"

[data.heap_cur]
addr = 0x20002B48
ctype = "uint32_t"

[hook.test_any]
kind = "call"
target = "session_refresh"
sites = [0x0802F5B4]
args = ["void *obj", "uint32_t what", "uint32_t arg"]
ret = "void"
context = "any"
"""


def test_dsp_lock_from_an_unidentified_task_is_rejected(tmp_path):
    fixture = tmp_path / "symbols.toml"
    fixture.write_text(ANY_FIXTURE)
    src = ("void t_any(void *obj, uint32_t what, uint32_t arg)\n{\n"
           "    if (what == 7u)\n        mark_dirty(obj, arg);\n}\n")
    with pytest.raises(BuildError, match="slim_call_test_any -> t_any -> mark_dirty takes the DSP-service lock "
                                         "from a task slim has not identified"):
        one(tmp_path, src, hooks=(("test_any", "t_any", 50),), symbols_path=fixture)


def test_a_call_hooks_own_target_is_not_counted(tmp_path):
    """Stock makes the hooked call whatever slim does: the wrapper calling it is not slim taking the lock."""
    fixture = tmp_path / "symbols.toml"
    fixture.write_text(ANY_FIXTURE)
    src = "void t_any(void *obj, uint32_t what, uint32_t arg)\n{\n    (void)obj; (void)what; (void)arg;\n}\n"
    one(tmp_path, src, hooks=(("test_any", "t_any", 50),), symbols_path=fixture)
