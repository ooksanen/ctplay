"""The generated entry stub, run in Unicorn: what stock's caller gets back."""
import pytest
from unicorn import UC_ARCH_ARM, UC_MODE_MCLASS, UC_MODE_THUMB, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

from helpers import write_feature, write_version
from playbuild import build

HEAD = '#include "slim.h"\n#include "stock.h"\n'
SYMBOLS = """
[data.heap_limit]
addr = 0x20002B44
ctype = "uint32_t"

[data.heap_cur]
addr = 0x20002B48
ctype = "uint32_t"

[hook.test_read]
kind = "entry"
addr = 0x08029344
expect = "38b50446"
displace = 4
args = ["uint32_t core", "uint32_t addr"]
ret = "uint32_t"
context = "ui"
"""
RETURN = 0x08000100          # stock's caller, as far as the stub knows
SP = 0x2004F000


def run_stub(tmp_path, body: str) -> int:
    fixture = tmp_path / "symbols.toml"
    fixture.write_text(SYMBOLS)
    fd = tmp_path / "f"
    src = HEAD + "int t_read(uint32_t core, uint32_t addr, uint32_t *r)\n{\n    (void)core; (void)addr; (void)r;\n" + body + "}\n"
    write_feature(fd, "t", c_source=src, hooks=[("test_read", "t_read", 50)])
    img, _, man = build.build_once(write_version(tmp_path, "v", "SLX1", ["t"], fd), tmp_path / "work", fixture)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    uc.mem_map(0x08000000, 0x80000)
    uc.mem_write(0x08010000, img)
    uc.mem_map(0x20000000, 0x50000)
    uc.mem_write(0x20002B44, (0x20044E58).to_bytes(4, "little") + (0x20044D68).to_bytes(4, "little"))  # heap free
    uc.mem_write(SP - 0x400, b"\xA5" * 0x400)                     # garbage where the stub builds slim_args_t
    uc.reg_write(UC_ARM_REG_SP, SP)
    uc.reg_write(UC_ARM_REG_R0, 1)
    uc.reg_write(UC_ARM_REG_R1, 0x1234)
    uc.reg_write(UC_ARM_REG_LR, RETURN | 1)
    uc.emu_start(int(man["symbols"]["slim_entry_test_read"], 16) | 1, RETURN, count=10_000)
    return uc.reg_read(UC_ARM_REG_R0)


@pytest.mark.parametrize("body, expected", [
    ("    return SLIM_HANDLED;\n", 0),                         # no result written: 0, not stack garbage
    ("    *r = 0xBEEFu;\n    return SLIM_HANDLED;\n", 0xBEEF),
])
def test_handled_returns_the_result_slot(tmp_path, body, expected):
    assert run_stub(tmp_path, body) == expected
