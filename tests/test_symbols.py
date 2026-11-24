import pytest

from playbuild import paths, symbols
from playbuild.errors import BuildError

STOCK = paths.STOCK_BIN.read_bytes()


def test_real_symbols_match_stock():
    s = symbols.load(paths.SYMBOLS)
    symbols.verify(s, STOCK)
    assert s.hooks["button_press"].addr == 0x08033320
    assert s.hooks["led_task"].sites == (0x08033B46, 0x0803415A)
    assert "takes_dsp_lock" in s.functions["mark_dirty"].tags
    assert s.functions["mark_dirty"].proto is None


def test_wrong_bytes_are_reported(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text('[function.param_get]\naddr = 0x0803542C\nexpect = "00000000"\n'
                 'proto = "volatile uint8_t *param_get(void *store, uint32_t index)"\n')
    with pytest.raises(BuildError, match="param_get at 0x0803542c"):
        symbols.verify(symbols.load(p), STOCK)


def test_call_site_must_call_its_target(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text('[function.led_task]\naddr = 0x08034196\nexpect = "f0b589b0"\n'
                 'proto = "void led_task(void *ctrl, uint16_t *out)"\n\n'
                 '[hook.leds]\nkind = "call"\ntarget = "led_task"\nsites = [0x08033B4A]\n'
                 'args = []\nret = "void"\ncontext = "ui"\n')
    with pytest.raises(BuildError, match="is not `bl 0x8034196`"):
        symbols.verify(symbols.load(p), STOCK)


def test_proto_must_name_the_function(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text('[function.param_get]\naddr = 0x0803542C\nexpect = "4268ca40"\nproto = "int other(void)"\n')
    with pytest.raises(BuildError, match="must declare `param_get\\(`"):
        symbols.load(p)


def test_hook_context_is_checked(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text('[hook.x]\nkind = "entry"\naddr = 0x08033320\nexpect = "38b50446"\ndisplace = 4\n'
                 'args = []\nret = "void"\ncontext = "irq"\n')
    with pytest.raises(BuildError, match="context"):
        symbols.load(p)


def test_main_ms_is_the_1ms_dispatcher():
    s = symbols.load(paths.SYMBOLS)
    hp = s.hooks["main_ms"]
    assert (hp.kind, hp.addr, hp.context, hp.args, hp.ret) == ("entry", 0x0803C410, "main", ("uint32_t slot",), "void")
    symbols.verify(s, STOCK)


def test_call_hook_on_a_function_that_returns_a_value_loads(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text('[function.dsp_read]\naddr = 0x08029344\nexpect = "38b50446"\n'
                 'proto = "uint32_t dsp_read(uint32_t core, uint32_t addr)"\n\n'
                 '[hook.vh]\nkind = "call"\ntarget = "dsp_read"\nsites = [0x080217EA]\n'
                 'args = ["uint32_t core", "uint32_t addr"]\nret = "uint32_t"\ncontext = "ui"\n')
    s = symbols.load(p)
    symbols.verify(s, STOCK)
    assert (s.hooks["vh"].kind, s.hooks["vh"].ret, s.hooks["vh"].sites) == ("call", "uint32_t", (0x080217EA,))


def test_voice_log_symbols_match_stock():
    from playbuild import hooks
    s = symbols.load(paths.SYMBOLS)
    symbols.verify(s, STOCK)
    assert s.hooks["voice_headroom"].sites == (0x080217EA,) and s.hooks["voice_headroom"].ret == "uint32_t"
    assert s.hooks["voice_picked"].sites == (0x080219F0,) and s.hooks["voice_picked"].context == "dsp_locked"
    assert (s.hooks["sysex_in"].addr, s.hooks["sysex_in"].displace) == (0x0801EB30, 4)
    hooks.check_entry(s.hooks["sysex_in"], STOCK, hooks.branch_targets(paths.LISTING))
    assert s.data["midi_router"].addr == 0x200069F4 and s.data["voice_state"].addr == 0x200067FC


@pytest.mark.parametrize("name, kind, addr, context, args", [
    ("seq_tick", "entry", 0x0802C418, "main", ("void *engine",)),
    ("seq_start", "entry", 0x0802C008, "ui", ("void *engine",)),
    ("ctrl_pad_press", "entry", 0x08033282, "ui", ("void *ctrl", "uint32_t pad", "uint32_t vel")),
    ("ctrl_pad_release", "entry", 0x080332CE, "ui", ("void *ctrl", "uint32_t pad")),
])
def test_arpeggiator_hook_points(name, kind, addr, context, args):
    s = symbols.load(paths.SYMBOLS)
    hp = s.hooks[name]
    assert (hp.kind, hp.addr, hp.context, hp.args, hp.ret) == (kind, addr, context, args, "void")
    symbols.verify(s, paths.STOCK_BIN.read_bytes())


def test_mono_record_hook_point():
    """PL08: the recorder's commit, entered before stock writes the unit (after it a write and a no-op look the same).
    PL19: context any (the PL19 spike's q1_tasks: UI commits too, the pad note-off and the flush)."""
    s = symbols.load(paths.SYMBOLS)
    hp = s.hooks["rec_commit"]
    assert (hp.kind, hp.addr, hp.displace, hp.context, hp.args, hp.ret) == (
        "entry", 0x0803F7BE, 6, "any", ("void *rec", "uint32_t note", "uint32_t end"), "uint32_t")
    symbols.verify(s, paths.STOCK_BIN.read_bytes())


@pytest.mark.parametrize("name, addr", [("rec_off_commit", 0x0803F606), ("rec_pass_commit", 0x0803F786)])
def test_pattern_strum_record_hook_points(name, addr):
    """PL19: mid hooks on the instructions just before the recorder's two commit calls that move a note (the note-off
    path's, 0x0803F60C; the tick pass's, 0x0803F78C); either task."""
    s = symbols.load(paths.SYMBOLS)
    hp = s.hooks[name]
    assert (hp.kind, hp.addr, hp.displace, hp.context) == ("mid", addr, 4, "any")
    symbols.verify(s, paths.STOCK_BIN.read_bytes())


def test_track_switch_functions_and_stores():
    s = symbols.load(paths.SYMBOLS)
    assert {n: s.functions[n].addr for n in ("cont_select_track", "cont_track_view", "ctrl_set_view")} == {
        "cont_select_track": 0x08043448, "cont_track_view": 0x0804348C, "ctrl_set_view": 0x0803390C}
    assert {n: s.data[n].addr for n in ("tempo_store", "play_store", "project_root")} == {
        "tempo_store": 0x20011404, "play_store": 0x20011034, "project_root": 0x2003FA94}


def test_saved_settings_hook_points():
    """PL10: stock's save copies the live blobs into the session record (0x0802F63C, its only call), then posts the file
    write; the load's apply ends with a call that itself takes the DSP lock (0x08029A00 -> 0x0803BDF2 -> 0x08021064)."""
    s = symbols.load(paths.SYMBOLS)
    save, applied = s.hooks["session_save"], s.hooks["session_applied"]
    assert (save.kind, save.target, save.sites, save.context, save.args, save.ret) == (
        "call", "session_blobs", (0x0802FE5E,), "ui", ("void *obj",), "void")
    assert (applied.kind, applied.target, applied.sites, applied.context, applied.ret) == (
        "call", "session_refresh", (0x0802F5B4,), "any", "void")
    assert len(applied.args) == 3
    assert "takes_dsp_lock" in s.functions["session_refresh"].tags
    assert s.data["session"].addr == 0x2003D71C
    symbols.verify(s, STOCK)
