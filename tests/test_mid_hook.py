"""The `mid` hook kind (PL16, foundation spec section 2, "Hook kinds"): a branch on an instruction inside a stock
function to a stub that runs the displaced instructions, then the handlers with every register (r0-r12, lr, the APSR
flags) readable and writable, and goes on in stock with the registers as the handlers left them."""
import pytest
from unicorn import UC_ARCH_ARM, UC_MODE_MCLASS, UC_MODE_THUMB, Uc
from unicorn.arm_const import UC_ARM_REG_APSR, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

from helpers import write_feature, write_version
from playbuild import build, checks, codegen, features, hooks, paths, symbols
from playbuild.errors import BuildError

STOCK = paths.STOCK_BIN.read_bytes()
TARGETS = hooks.branch_targets(paths.LISTING)
HEAD = '#include "slim.h"\n#include "stock.h"\n'
SITE = 0x0803FE8C                    # eor.w r0, r0, #1: the drum / note recorders' quantise refresh (rec_quant)
MID = """
[data.heap_limit]
addr = 0x20002B44
ctype = "uint32_t"

[data.heap_cur]
addr = 0x20002B48
ctype = "uint32_t"

[function.dsp_lock_take]
addr = 0x08021064
expect = "10b50446"
proto = "void dsp_lock_take(void *obj)"
tags = ["takes_dsp_lock"]

[hook.t_mid]
kind = "mid"
addr = 0x0803FE8C
expect = "80f00100"
displace = 4
context = "any"
"""


def mid(addr, expect, displace):
    return symbols.HookPoint("t", "mid", "any", (), "void", addr=addr, expect=bytes.fromhex(expect), displace=displace)


def fixture(tmp_path, extra=""):
    p = tmp_path / "symbols.toml"
    p.write_text(MID + extra)
    return p


def build_mid(tmp_path, body, sym_path=None):
    fd = tmp_path / "f"
    src = HEAD + "void t_on(slim_regs_t *regs)\n{\n" + body + "}\n"
    write_feature(fd, "t", c_source=src, hooks=[("t_mid", "t_on", 50)])
    return build.build_once(write_version(tmp_path, "v", "SLX1", ["t"], fd), tmp_path / "work",
                            sym_path or fixture(tmp_path))


def test_mid_hook_loads_and_matches_stock(tmp_path):
    s = symbols.load(fixture(tmp_path))
    hp = s.hooks["t_mid"]
    assert (hp.kind, hp.addr, hp.displace, hp.args, hp.ret, hp.context) == ("mid", SITE, 4, (), "void", "any")
    symbols.verify(s, STOCK)


def test_mid_hook_bytes_are_verified(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text('[hook.x]\nkind = "mid"\naddr = 0x0803FE8C\nexpect = "00000000"\ndisplace = 4\ncontext = "any"\n')
    with pytest.raises(BuildError, match="hook x at 0x0803fe8c"):
        symbols.verify(symbols.load(p), STOCK)


@pytest.mark.parametrize("extra", ['args = ["uint32_t a"]\n', 'ret = "uint32_t"\n'])
def test_mid_hook_takes_the_registers_only(tmp_path, extra):
    p = tmp_path / "s.toml"
    p.write_text('[hook.x]\nkind = "mid"\naddr = 0x0803FE8C\nexpect = "80f00100"\ndisplace = 4\ncontext = "any"\n'
                 + extra)
    with pytest.raises(BuildError, match="mid hook: the handlers get the registers"):
        symbols.load(p)


def test_the_listing_marks_it_blocks():
    covered = hooks.it_covered(paths.LISTING)
    assert {0x080107F6, 0x080107FA, 0x080107FC, 0x08010800} <= covered   # ittee ne at 0x080107F4: its 4 instructions
    assert 0x080107F4 not in covered


def test_mid_hook_inside_an_it_block_is_refused():
    covered = hooks.it_covered(paths.LISTING)
    inside = min(covered)
    with pytest.raises(BuildError, match="inside an IT block"):
        hooks.check_mid(mid(inside, "0000", 4), STOCK, TARGETS, covered)


def test_mid_hook_rules_of_entry_hooks_apply():
    covered = hooks.it_covered(paths.LISTING)
    hooks.check_mid(mid(SITE, "80f00100", 4), STOCK, TARGETS, covered)
    with pytest.raises(BuildError, match="branches into the displaced bytes"):
        hooks.check_mid(mid(0x0803FE8C, "80f001007870", 6), STOCK, TARGETS | {0x0803FE90}, covered)
    with pytest.raises(BuildError, match="depends on the program counter"):
        hooks.check_mid(mid(0x0803FE52, "cb4b53f820a0", 6), STOCK, TARGETS, covered)   # ldr r3, [pc, #0x32c]


def test_mid_stub_and_dispatcher_text(tmp_path):
    sym = symbols.load(fixture(tmp_path))
    fd = tmp_path / "f"
    write_feature(fd, "a", hooks=[("t_mid", "a_on", 60)])
    write_feature(fd, "b", hooks=[("t_mid", "b_on", 40)])
    v = features.load_version(write_version(tmp_path, "v", "SLX1", ["a", "b"], fd), sym)
    s = codegen.entry_stubs_s(sym, v)
    stub = s[s.index("slim_entry_t_mid:"):]
    assert stub.index(".inst.n 0xf080") < stub.index("push    {r0-r12, lr}") < stub.index("bl      slim_dispatch_t_mid")
    assert "msr     APSR_nzcvqg, r0" in stub and ".word   0x0803fe91" in stub
    c = codegen.dispatch_c(sym, v)
    assert "void a_on(slim_regs_t *regs);" in c and "void b_on(slim_regs_t *regs);" in c
    assert ("void slim_dispatch_t_mid(slim_regs_t *regs)\n{\n    if (!slim_ready())\n        return;\n"
            "    b_on(regs);\n    a_on(regs);\n}\n") in c


def test_mid_hook_patch_branches_to_its_stub(tmp_path):
    img, _, man = build_mid(tmp_path, "    (void)regs;\n")
    assert man["patches"] == [dict(addr=hex(SITE), bytes=hooks.patch_entry(mid(SITE, "80f00100", 4),
                                                                          int(man["symbols"]["slim_entry_t_mid"], 16) & ~1)[1].hex())]
    assert man["hook_stack"]["t_mid"]["bytes"] >= checks.MID_STUB_STACK


def test_mid_hook_cannot_reach_the_dsp_lock(tmp_path):
    with pytest.raises(BuildError, match="slim_dispatch_t_mid -> t_on -> dsp_lock_take takes the DSP-service lock"):
        build_mid(tmp_path, "    dsp_lock_take((void *)regs->r[0]);\n")


SP = 0x2004F000
REGS = [0x1000 + 0x11 * k for k in range(13)]


def run_stub(tmp_path, body, apsr=0xF8000000):
    """The stub of t_mid run from stock's site to where it goes on (SITE + 4): every register as it comes out."""
    img, _, man = build_mid(tmp_path, body)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    uc.mem_map(0x08000000, 0x80000)
    uc.mem_write(0x08010000, img)
    uc.mem_map(0x20000000, 0x50000)
    uc.mem_write(0x20002B44, (0x20044E58).to_bytes(4, "little") + (0x20044D68).to_bytes(4, "little"))  # heap free
    uc.mem_write(SP - 0x400, b"\xA5" * 0x400)
    uc.reg_write(UC_ARM_REG_SP, SP)
    for k, v in enumerate(REGS):
        uc.reg_write(UC_ARM_REG_R0 + k, v)
    uc.reg_write(UC_ARM_REG_LR, 0x08000101)
    uc.reg_write(UC_ARM_REG_APSR, apsr)
    uc.emu_start(SITE | 1, SITE + 4, count=20_000)
    assert uc.reg_read(UC_ARM_REG_PC) == SITE + 4
    return ([uc.reg_read(UC_ARM_REG_R0 + k) for k in range(13)], uc.reg_read(UC_ARM_REG_LR),
            uc.reg_read(UC_ARM_REG_APSR) & 0xF8000000, uc.reg_read(UC_ARM_REG_SP))


def test_mid_stub_runs_the_displaced_instruction_first_and_keeps_every_register(tmp_path):
    regs, lr, apsr, sp = run_stub(tmp_path, "    (void)regs;\n")
    assert regs == [REGS[0] ^ 1] + REGS[1:]                        # eor.w r0, r0, #1 ran; nothing else changed
    assert (lr, apsr, sp) == (0x08000101, 0xF8000000, SP)


def test_mid_handler_reads_and_changes_registers(tmp_path):
    body = "    regs->r[1] = regs->r[0];\n    regs->r[0] = regs->r[5] + 1u;\n    regs->r[12] = 7u;\n"
    regs, lr, apsr, sp = run_stub(tmp_path, body, apsr=0x40000000)
    assert regs[:2] == [REGS[5] + 1, REGS[0] ^ 1] and regs[12] == 7 and regs[2:12] == REGS[2:12]
    assert (lr, apsr, sp) == (0x08000101, 0x40000000, SP)          # Z kept through the handler's own compares
