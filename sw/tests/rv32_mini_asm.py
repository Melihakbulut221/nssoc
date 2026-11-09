# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A two-pass RV32IMC + Zicsr assembler for core-level directed tests.

Only what the Ibex execute-stage tests need, so that they run without a
cross compiler. Syntax is the GNU assembler's for the supported subset:

    label:
    .org 0x80        absolute placement (pads with zero)
    .word 0x12345678 / .half 0x1234
    addi a0, a0, 1   lw a1, 4(a0)   beq a0, a1, label   csrrw t0, mscratch, t1
    li / la / mv / nop / j / jr / ret / beqz / bnez / csrr / csrw / csrs / csrc
    c.addi c.li c.lui c.mv c.add c.sub c.slli c.j c.jal c.jr c.jalr c.beqz
    c.bnez c.lw c.sw c.nop c.ebreak

`li` always takes 8 bytes (lui + addi) unless the value fits 12 bits, so a
program's layout does not depend on symbol values. `la` is always 8 bytes.
"""
import re

REGS = {f"x{i}": i for i in range(32)}
REGS.update({n: i for i, n in enumerate(
    "zero ra sp gp tp t0 t1 t2 s0 s1 a0 a1 a2 a3 a4 a5 a6 a7 "
    "s2 s3 s4 s5 s6 s7 s8 s9 s10 s11 t3 t4 t5 t6".split())})
REGS["fp"] = 8
CSRS = {"mstatus": 0x300, "misa": 0x301, "mie": 0x304, "mtvec": 0x305,
        "mscratch": 0x340, "mepc": 0x341, "mcause": 0x342, "mtval": 0x343,
        "mip": 0x344, "dcsr": 0x7B0, "dpc": 0x7B1, "dscratch0": 0x7B2,
        "dscratch1": 0x7B3, "mcycle": 0xB00, "minstret": 0xB02,
        "cycle": 0xC00, "instret": 0xC02, "mcountinhibit": 0x320,
        "pmpcfg0": 0x3A0, "pmpaddr0": 0x3B0, "pmpaddr1": 0x3B1,
        "cpuctrlsts": 0x7C0}

R_OPS = {  # funct7, funct3
    "add": (0, 0), "sub": (0x20, 0), "sll": (0, 1), "slt": (0, 2), "sltu": (0, 3),
    "xor": (0, 4), "srl": (0, 5), "sra": (0x20, 5), "or": (0, 6), "and": (0, 7),
    "mul": (1, 0), "mulh": (1, 1), "mulhsu": (1, 2), "mulhu": (1, 3),
    "div": (1, 4), "divu": (1, 5), "rem": (1, 6), "remu": (1, 7)}
I_OPS = {"addi": 0, "slti": 2, "sltiu": 3, "xori": 4, "ori": 6, "andi": 7}
SH_OPS = {"slli": (0, 1), "srli": (0, 5), "srai": (0x20, 5)}
L_OPS = {"lb": 0, "lh": 1, "lw": 2, "lbu": 4, "lhu": 5}
S_OPS = {"sb": 0, "sh": 1, "sw": 2}
B_OPS = {"beq": 0, "bne": 1, "blt": 4, "bge": 5, "bltu": 6, "bgeu": 7}
CSR_OPS = {"csrrw": 1, "csrrs": 2, "csrrc": 3, "csrrwi": 5, "csrrsi": 6, "csrrci": 7}


class AsmError(Exception):
    pass


def _reg(s):
    s = s.strip()
    if s not in REGS:
        raise AsmError("bad register %r" % s)
    return REGS[s]


def _creg(s):
    r = _reg(s)
    if not 8 <= r <= 15:
        raise AsmError("compressed register out of x8-x15: %r" % s)
    return r - 8


def _num(s, syms):
    s = s.strip()
    m = re.fullmatch(r"%(hi|lo)\((.+)\)", s)
    if m:
        v = _num(m.group(2), syms)
        lo = ((v & 0xFFF) ^ 0x800) - 0x800
        return ((v - lo) >> 12) & 0xFFFFF if m.group(1) == "hi" else lo
    if s in syms:
        return syms[s]
    if s in CSRS:
        return CSRS[s]
    try:
        return int(s, 0)
    except ValueError:
        raise AsmError("bad number or unknown symbol %r" % s) from None


def _mem(s, syms):
    m = re.fullmatch(r"(.*)\((\w+)\)", s.strip())
    if not m:
        raise AsmError("bad memory operand %r" % s)
    off = _num(m.group(1) or "0", syms)
    return off, _reg(m.group(2))


def _chk(v, bits, signed=True, what="immediate"):
    lo, hi = (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if signed else (0, (1 << bits) - 1)
    if not lo <= v <= hi:
        raise AsmError("%s %d does not fit %d bits" % (what, v, bits))
    return v & ((1 << bits) - 1)


def enc_r(f7, rs2, rs1, f3, rd, op=0x33):
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def enc_i(imm, rs1, f3, rd, op):
    return (_chk(imm, 12) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def enc_s(imm, rs2, rs1, f3):
    imm = _chk(imm, 12)
    return ((imm >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | ((imm & 31) << 7) | 0x23


def enc_b(off, rs2, rs1, f3):
    if off & 1:
        raise AsmError("odd branch offset")
    o = _chk(off, 13, what="branch offset")
    return (((o >> 12) & 1) << 31) | (((o >> 5) & 63) << 25) | (rs2 << 20) | (rs1 << 15) | \
        (f3 << 12) | (((o >> 1) & 15) << 8) | (((o >> 11) & 1) << 7) | 0x63


def enc_j(off, rd):
    if off & 1:
        raise AsmError("odd jump offset")
    o = _chk(off, 21, what="jump offset")
    return (((o >> 20) & 1) << 31) | (((o >> 1) & 0x3FF) << 21) | (((o >> 11) & 1) << 20) | \
        (((o >> 12) & 0xFF) << 12) | (rd << 7) | 0x6F


def enc_u(imm20, rd, op):
    return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | op


def _cj(off):
    o = _chk(off, 12, what="c.j offset")
    b = lambda i: (o >> i) & 1
    return (b(11) << 12) | (b(4) << 11) | (b(9) << 10) | (b(8) << 9) | (b(10) << 8) | \
        (b(6) << 7) | (b(7) << 6) | (b(3) << 5) | (b(2) << 4) | (b(1) << 3) | (b(5) << 2)


def _cb(off):
    o = _chk(off, 9, what="c.b offset")
    b = lambda i: (o >> i) & 1
    return (b(8) << 12) | (b(4) << 11) | (b(3) << 10) | (b(7) << 6) | (b(6) << 5) | \
        (b(2) << 4) | (b(1) << 3) | (b(5) << 2)


def _split(args):
    return [a.strip() for a in args.split(",")] if args.strip() else []


def _short_li(s):
    return _is_num(s) and -2048 <= int(s.strip(), 0) <= 2047


def _size(mn, ops):
    if mn.startswith("c."):
        return 2
    if mn == "li":
        return 4 if _short_li(ops[1]) else 8
    if mn == "la":
        return 8
    return 4


def _encode(mn, ops, pc, syms):
    """Return a list of (value, nbytes)."""
    n = len(ops)
    w = lambda v: [(v & 0xFFFFFFFF, 4)]
    h = lambda v: [(v & 0xFFFF, 2)]
    if mn in R_OPS:
        f7, f3 = R_OPS[mn]
        return w(enc_r(f7, _reg(ops[2]), _reg(ops[1]), f3, _reg(ops[0])))
    if mn in I_OPS:
        return w(enc_i(_num(ops[2], syms), _reg(ops[1]), I_OPS[mn], _reg(ops[0]), 0x13))
    if mn in SH_OPS:
        f7, f3 = SH_OPS[mn]
        return w(enc_r(f7, _chk(_num(ops[2], syms), 5, False), _reg(ops[1]), f3, _reg(ops[0]), 0x13))
    if mn in L_OPS:
        off, rs1 = _mem(ops[1], syms)
        return w(enc_i(off, rs1, L_OPS[mn], _reg(ops[0]), 0x03))
    if mn in S_OPS:
        off, rs1 = _mem(ops[1], syms)
        return w(enc_s(off, _reg(ops[0]), rs1, S_OPS[mn]))
    if mn in B_OPS:
        return w(enc_b(_num(ops[2], syms) - pc, _reg(ops[1]), _reg(ops[0]), B_OPS[mn]))
    if mn in ("beqz", "bnez"):
        return w(enc_b(_num(ops[1], syms) - pc, 0, _reg(ops[0]), 0 if mn == "beqz" else 1))
    if mn == "lui":
        return w(enc_u(_num(ops[1], syms), _reg(ops[0]), 0x37))
    if mn == "auipc":
        return w(enc_u(_num(ops[1], syms), _reg(ops[0]), 0x17))
    if mn == "jal":
        rd, tgt = (_reg(ops[0]), ops[1]) if n == 2 else (1, ops[0])
        return w(enc_j(_num(tgt, syms) - pc, rd))
    if mn == "j":
        return w(enc_j(_num(ops[0], syms) - pc, 0))
    if mn == "jalr":
        if n == 1:
            return w(enc_i(0, _reg(ops[0]), 0, 1, 0x67))
        if n == 2:
            off, rs1 = _mem(ops[1], syms)
            return w(enc_i(off, rs1, 0, _reg(ops[0]), 0x67))
        return w(enc_i(_num(ops[2], syms), _reg(ops[1]), 0, _reg(ops[0]), 0x67))
    if mn == "jr":
        return w(enc_i(0, _reg(ops[0]), 0, 0, 0x67))
    if mn == "ret":
        return w(enc_i(0, 1, 0, 0, 0x67))
    if mn in CSR_OPS:
        f3 = CSR_OPS[mn]
        src = _chk(_num(ops[2], syms), 5, False) if f3 >= 5 else _reg(ops[2])
        return w((_chk(_num(ops[1], syms), 12, False) << 20) | (src << 15) | (f3 << 12) |
                 (_reg(ops[0]) << 7) | 0x73)
    if mn == "csrr":
        return _encode("csrrs", [ops[0], ops[1], "x0"], pc, syms)
    if mn in ("csrw", "csrs", "csrc"):
        return _encode({"csrw": "csrrw", "csrs": "csrrs", "csrc": "csrrc"}[mn],
                       ["x0", ops[0], ops[1]], pc, syms)
    if mn in ("csrwi", "csrsi", "csrci"):
        return _encode(mn[:-1].replace("csr", "csrr") + "i", ["x0", ops[0], ops[1]], pc, syms)
    if mn == "li":
        v = _num(ops[1], syms)
        rd = _reg(ops[0])
        if _short_li(ops[1]):
            return w(enc_i(v, 0, 0, rd, 0x13))
        v &= 0xFFFFFFFF
        lo = ((v & 0xFFF) ^ 0x800) - 0x800
        return w(enc_u(((v - lo) >> 12) & 0xFFFFF, rd, 0x37)) + w(enc_i(lo, rd, 0, rd, 0x13))
    if mn == "la":
        v = _num(ops[1], syms) & 0xFFFFFFFF
        rd = _reg(ops[0])
        lo = ((v & 0xFFF) ^ 0x800) - 0x800
        return w(enc_u(((v - lo) >> 12) & 0xFFFFF, rd, 0x37)) + w(enc_i(lo, rd, 0, rd, 0x13))
    if mn == "mv":
        return w(enc_i(0, _reg(ops[1]), 0, _reg(ops[0]), 0x13))
    if mn == "nop":
        return w(0x13)
    if mn == "ecall":
        return w(0x73)
    if mn == "ebreak":
        return w(0x00100073)
    if mn == "mret":
        return w(0x30200073)
    if mn == "dret":
        return w(0x7B200073)
    if mn == "wfi":
        return w(0x10500073)
    if mn == "fence":
        return w(0x0FF0000F)
    if mn == "fence.i":
        return w(0x0000100F)
    # compressed
    if mn == "c.nop":
        return h(0x0001)
    if mn == "c.ebreak":
        return h(0x9002)
    if mn in ("c.addi", "c.li"):
        rd, imm = _reg(ops[0]), _chk(_num(ops[1], syms), 6)
        f3 = 0 if mn == "c.addi" else 2
        return h((f3 << 13) | (((imm >> 5) & 1) << 12) | (rd << 7) | ((imm & 31) << 2) | 1)
    if mn == "c.lui":
        rd, imm = _reg(ops[0]), _chk(_num(ops[1], syms), 6)
        return h((3 << 13) | (((imm >> 5) & 1) << 12) | (rd << 7) | ((imm & 31) << 2) | 1)
    if mn == "c.slli":
        rd, sh = _reg(ops[0]), _chk(_num(ops[1], syms), 5, False)
        return h((rd << 7) | (sh << 2) | 2)
    if mn in ("c.mv", "c.add"):
        return h((4 << 13) | ((mn == "c.add") << 12) | (_reg(ops[0]) << 7) | (_reg(ops[1]) << 2) | 2)
    if mn in ("c.jr", "c.jalr"):
        return h((4 << 13) | ((mn == "c.jalr") << 12) | (_reg(ops[0]) << 7) | 2)
    if mn == "c.sub":
        return h(0x8C01 | (_creg(ops[0]) << 7) | (_creg(ops[1]) << 2))
    if mn in ("c.j", "c.jal"):
        return h(((5 if mn == "c.j" else 1) << 13) | _cj(_num(ops[0], syms) - pc) | 1)
    if mn in ("c.beqz", "c.bnez"):
        return h(((6 if mn == "c.beqz" else 7) << 13) | (_creg(ops[0]) << 7) |
                 _cb(_num(ops[1], syms) - pc) | 1)
    if mn in ("c.lw", "c.sw"):
        off, rs1 = _mem(ops[1], syms)
        off = _chk(off, 7, False)
        if off & 3:
            raise AsmError("c.lw/c.sw offset must be a multiple of 4")
        rs1 -= 8
        if not 0 <= rs1 <= 7:
            raise AsmError("compressed base register out of x8-x15")
        f3 = 2 if mn == "c.lw" else 6
        return h((f3 << 13) | (((off >> 3) & 7) << 10) | (rs1 << 7) | (((off >> 2) & 1) << 6) |
                 (((off >> 6) & 1) << 5) | (_creg(ops[0]) << 2))
    raise AsmError("unknown mnemonic %r" % mn)


def assemble(source, size_bytes=16384):
    """Assemble `source`; return (bytearray image, symbol table)."""
    lines = []
    for ln, raw in enumerate(source.splitlines(), 1):
        s = raw.split("#")[0].strip()
        while s:
            m = re.match(r"([A-Za-z_.][\w.]*):\s*(.*)", s)
            if m and not m.group(1).startswith("c."):
                lines.append((ln, "label", m.group(1), []))
                s = m.group(2).strip()
                continue
            parts = s.split(None, 1)
            lines.append((ln, "op", parts[0].lower(), _split(parts[1] if len(parts) > 1 else "")))
            break
    syms = {}
    for pass_no in (1, 2):
        pc = 0
        image = bytearray(size_bytes)
        for ln, kind, name, ops in lines:
            try:
                if kind == "label":
                    if pass_no == 1:
                        if name in syms:
                            raise AsmError("duplicate label %r" % name)
                        syms[name] = pc
                    continue
                if name == ".org":
                    new = _num(ops[0], syms)
                    if new < pc:
                        raise AsmError(".org 0x%x moves backwards from 0x%x" % (new, pc))
                    pc = new
                    continue
                if name == ".word":
                    out = [(_num(ops[0], syms) if pass_no == 2 else 0, 4)]
                elif name == ".half":
                    out = [(_num(ops[0], syms) if pass_no == 2 else 0, 2)]
                elif pass_no == 1:
                    out = [(0, _size(name, ops))]
                else:
                    out = _encode(name, ops, pc, syms)
                for val, nb in out:
                    if pc + nb > size_bytes:
                        raise AsmError("image overflow at 0x%x" % pc)
                    image[pc:pc + nb] = (val & ((1 << (8 * nb)) - 1)).to_bytes(nb, "little")
                    pc += nb
            except AsmError as e:
                raise AsmError("line %d: %s" % (ln, e)) from None
    return image, syms


def _is_num(s):
    try:
        int(s.strip(), 0)
        return True
    except ValueError:
        return False


def to_readmemh(image):
    words = [int.from_bytes(image[i:i + 4], "little") for i in range(0, len(image), 4)]
    return "".join("%08x\n" % w for w in words)
