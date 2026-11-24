# Who points at the editor's flag stores (RAM search for the pointer values) and what the stores look like.
import struct
from drumlib import *
h = harness()
ram = bytes(h.uc.mem_read(0x20000000, 0x50000))
def refs(v):
    return [0x20000000 + i for i in range(0, len(ram) - 3, 4) if struct.unpack_from('<I', ram, i)[0] == v]
for d in range(4):
    D = Drum(h, d)
    s24 = h.r32(D.editor + 0x24)
    print(f'drum {d} editor {D.editor:#x}: +0x24 store {s24:#x} refs {[hex(r) for r in refs(s24)]}')
    print('   editor words', ' '.join(f'{h.r32(D.editor + 4*i):08x}' for i in range(0x18)))
s = 0x20039DE0
print('0x20039DE0 refs', [hex(r) for r in refs(s)])
print('0x20039DE0 header', bytes(h.uc.mem_read(s, 0x18)).hex(), 'p0', pget(h, s, 0), 'p1', pget(h, s, 1))
for r in refs(s):
    base = r - 0x40
    print(f'  around {r:#x}:', ' '.join(f'{h.r32(base + 4*i):08x}' for i in range(0x20)))
