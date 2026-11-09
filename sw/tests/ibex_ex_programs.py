# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Directed and random programs for hw/soc/tb/tb_ibex_ex_stage.v.

Every program is wrapped in the same frame: trap vectors, a reset entry
that enables the external interrupt, an interrupt handler and a debug
handler that are transparent to the main program (they use only x28-x31
and handler-owned memory), an exception handler that is part of the main
program (x26, x27), and an epilogue that stores x1-x25 to 0x3000 and
writes the exit code. The main program uses x1-x25 only. A self-check
failure exits with a nonzero code.

Layout: vectors 0x0, reset 0x80, exception handler 0x500, interrupt
handler 0x400, debug handler 0x800, main program 0x1000, data 0x2800,
register dump 0x3000, exception log 0x3100, fetch-error region 0x3800.
"""
import random

FRAME_HEAD = """
.org 0x0
    j exc_handler
.org 0x2c
    j irq_handler
.org 0x80
reset:
    li x5, 0x800
    csrs mie, x5
    csrsi mstatus, 8
    j main

.org 0x400
irq_handler:
    lui x28, 0x100
    sw x0, 8(x28)
    csrr x29, mepc
    sw x29, 16(x28)
    mret

.org 0x500
exc_handler:
    li x27, 0x3100
    csrr x26, mcause
    sw x26, 0(x27)
    csrr x26, mepc
    sw x26, 4(x27)
    csrr x26, mtval
    sw x26, 8(x27)
    csrr x26, mcause
    li x27, 1
    beq x26, x27, exc_ret_link
    csrr x26, mepc
    lhu x27, 0(x26)
    andi x27, x27, 3
    addi x27, x27, -3
    beqz x27, exc_plus4
    addi x26, x26, 2
    j exc_set
exc_plus4:
    addi x26, x26, 4
exc_set:
    csrw mepc, x26
    mret
exc_ret_link:
    csrw mepc, x24
    mret

.org 0x800
    j dbg_main
.org 0x808
    j dbg_exc
.org 0x810
dbg_main:
    li x30, 0x3f00
    lw x31, 0(x30)
    beqz x31, dbg_nostep
    addi x31, x31, -1
    sw x31, 0(x30)
    csrr x31, dcsr
    ori x31, x31, 4
    csrw dcsr, x31
    dret
dbg_nostep:
    csrr x31, dcsr
    andi x31, x31, -5
    csrw dcsr, x31
    dret
dbg_exc:
    lui x30, 0x100
    li x31, 0xdead
    sw x31, 4(x30)
    j dbg_exc

.org 0x1000
main:
"""

FRAME_TAIL = """
done:
    li x27, 0x3000
""" + "".join("    sw x%d, %d(x27)\n" % (r, 4 * r) for r in range(1, 26)) + """
    lui x27, 0x100
    sw x0, 4(x27)
hang:
    j hang
fail:
    lui x27, 0x100
    li x26, 1
    sw x26, 4(x27)
fail_hang:
    j fail_hang
"""


def framed(body):
    return FRAME_HEAD + body + FRAME_TAIL


ALU = """
    li x1, 5
    addi x2, x1, 3
    add x3, x2, x1
    sub x4, x3, x2
    sll x5, x4, x1
    addi x0, x5, 7
    add x6, x0, x5
    xor x7, x6, x5
    bnez x7, fail
    addi x0, x0, 1
    addi x8, x0, 0
    bnez x8, fail
    lui x8, 0x12345
    addi x8, x8, 0x678
    auipc x9, 0
    srai x10, x8, 3
    srl x11, x8, x1
    slt x12, x10, x11
    sltu x13, x11, x10
    or x14, x12, x13
    and x15, x14, x8
    addi x15, x15, 1
    addi x15, x15, 1
    addi x15, x15, 1
    slli x16, x15, 4
    srli x17, x16, 2
    sra x18, x16, x1
    sltiu x19, x18, 100
    slti x20, x18, -1
    xori x21, x20, -1
    ori x22, x21, 0x55
    andi x23, x22, 0x7f0
    c.mv x9, x15
    c.add x9, x9
    c.addi x9, -3
    c.slli x9, 2
    c.lui x10, 5
    c.li x11, -7
    c.sub x10, x11
    c.add x10, x9
    c.nop
    li x12, 0
    li x13, 100
sum_loop:
    add x12, x12, x13
    addi x13, x13, -1
    bnez x13, sum_loop
    li x14, 5050
    bne x12, x14, fail
    li x1, 1
    add x1, x1, x1
    add x1, x1, x1
    add x1, x1, x1
    add x1, x1, x1
    li x2, 16
    bne x1, x2, fail
    add x3, x1, x2
    sub x3, x3, x3
    bnez x3, fail
"""

LOAD = """
    li x1, 0x2800
    li x2, 0x11223344
    sw x2, 0(x1)
    lw x3, 0(x1)
    addi x4, x3, 1
    sw x4, 4(x1)
    lw x5, 4(x1)
    sw x5, 8(x1)
    lw x6, 8(x1)
    beq x6, x4, ld_ok1
    j fail
ld_ok1:
    li x7, 0x2820
    sw x7, 16(x1)
    li x8, 0x2830
    sw x8, 0(x7)
    li x9, 0x1234
    sw x9, 0(x8)
    lw x9, 16(x1)
    lw x10, 0(x9)
    lw x11, 0(x10)
    li x12, 0x1234
    bne x11, x12, fail
    lb x13, 3(x1)
    lbu x14, 0(x1)
    lh x15, 2(x1)
    lhu x16, 0(x1)
    li x17, -1
    sw x17, 12(x1)
    lb x18, 12(x1)
    lbu x19, 12(x1)
    add x20, x18, x19
    li x21, 254
    bne x20, x21, fail
    lw x21, 1(x1)
    addi x22, x21, 0
    sw x22, 33(x1)
    lw x23, 33(x1)
    bne x23, x22, fail
    sh x2, 51(x1)
    lhu x23, 51(x1)
    li x22, 0x3344
    bne x23, x22, fail
    la x5, ld_tgt
    sw x5, 40(x1)
    lw x6, 40(x1)
    jalr x7, 0(x6)
    j fail
ld_tgt:
    lw x8, 0(x1)
    beq x8, x2, ld_ok2
    j fail
ld_ok2:
    lw x9, 0(x1)
    lw x9, 4(x1)
    addi x10, x9, 0
    bne x10, x4, fail
    lw x11, 0(x1)
    sw x11, 0(x1)
    lw x12, 0(x1)
    bne x12, x2, fail
    li x8, 0x2900
    li x9, 0x5a5a1234
    c.sw x9, 4(x8)
    c.lw x10, 4(x8)
    c.add x10, x10
    lw x11, 4(x8)
    add x11, x11, x11
    bne x10, x11, fail
    lw x12, 0(x1)
    lw x13, 0(x12)
"""

MULDIV = """
    li x1, 12345
    li x2, -678
    mul x3, x1, x2
    add x4, x3, x3
    mulh x5, x3, x1
    mulhsu x6, x2, x1
    mulhu x7, x2, x2
    div x8, x3, x2
    bne x8, x1, fail
    rem x9, x3, x1
    bnez x9, fail
    divu x10, x2, x1
    remu x11, x2, x1
    div x12, x1, x0
    rem x13, x1, x0
    li x14, 0x80000000
    li x15, -1
    div x16, x14, x15
    rem x17, x14, x15
    bne x16, x14, fail
    bnez x17, fail
    li x18, 3
    mul x18, x18, x18
    mul x18, x18, x18
    mul x18, x18, x18
    li x19, 6561
    bne x18, x19, fail
    li x20, 0x5000
    li x21, 2
    divu x21, x20, x21
    lw x22, 0(x21)
    mul x23, x1, x1
    sw x23, 0(x21)
    lw x22, 0(x21)
    bne x22, x23, fail
    li x24, 777
    sw x24, 4(x21)
    lw x5, 4(x21)
    mul x6, x5, x5
    div x7, x6, x5
    bne x7, x5, fail
    mul x8, x1, x0
    beqz x8, md_ok
    j fail
md_ok:
    li x9, 7
    div x10, x1, x9
    rem x11, x1, x9
    mul x12, x10, x9
    add x12, x12, x11
    bne x12, x1, fail
    mulhu x13, x14, x14
    mulh x14, x14, x14
"""

CSR = """
    li x1, 0xabcd
    csrw mscratch, x1
    csrr x2, mscratch
    bne x2, x1, fail
    addi x3, x2, 1
    csrrw x4, mscratch, x3
    csrrs x5, mscratch, x0
    csrrw x5, mscratch, x5
    csrrc x6, mscratch, x1
    csrrwi x7, mscratch, 17
    csrrsi x8, mscratch, 6
    csrrci x9, mscratch, 1
    csrr x10, mscratch
    addi x11, x10, 0
    csrrw x11, mscratch, x11
    csrr x12, mscratch
    bne x12, x10, fail
    csrr x13, mtvec
    csrw mtvec, x13
    csrr x14, mtvec
    bne x14, x13, fail
    csrci mstatus, 8
    addi x15, x0, 3
    csrsi mstatus, 8
    addi x15, x15, 1
    csrc mie, x0
    li x17, 0x800
    csrc mie, x17
    addi x18, x0, 1
    csrs mie, x17
    addi x18, x18, 1
    csrr x19, mie
    lw x20, 0(x0)
    csrw mscratch, x20
    csrr x21, mscratch
    bne x21, x20, fail
    mul x22, x21, x21
    csrw mscratch, x22
    csrr x23, mscratch
    bne x23, x22, fail
"""

# minstret is read here; this program is not run under interrupt or debug
# sweeps (handler instructions retire too). mcycle is never read: its
# value depends on timing and would differ between configurations.
COUNTERS = """
    csrr x1, minstret
    addi x2, x0, 1
    addi x2, x2, 1
    addi x2, x2, 1
    csrr x3, minstret
    sub x4, x3, x1
    li x5, 4
    bne x4, x5, fail
    li x6, 10
cnt_loop:
    addi x6, x6, -1
    bnez x6, cnt_loop
    csrr x7, minstret
    sub x8, x7, x3
    li x9, 25
    bne x8, x9, fail
"""

BRANCH = """
    li x1, 1
    li x2, 2
    beq x1, x2, fail
    addi x3, x1, 1
    beq x3, x2, br1
    j fail
    addi x4, x0, 99
br1:
    bne x3, x2, fail
    blt x2, x1, fail
    bge x1, x2, fail
    bltu x2, x1, fail
    bgeu x1, x2, fail
    blt x1, x2, br2
    j fail
br2:
    li x5, -1
    bltu x1, x5, br3
    j fail
br3:
    bge x1, x5, br4
    j fail
br4:
    li x6, 0
    beq x0, x0, br5
    addi x6, x6, 1
    addi x6, x6, 1
br5:
    bnez x6, fail
    jal x7, br6
br6a:
    j fail
br6:
    la x8, br6a
    bne x7, x8, fail
    la x9, br7
    jalr x9, 0(x9)
br7a:
    j fail
br7:
    la x10, br7a
    bne x9, x10, fail
    la x11, br8
    addi x11, x11, 0
    jalr x0, 0(x11)
    j fail
br8:
    li x12, 0
    li x13, 0
br_loop:
    addi x12, x12, 1
    addi x13, x13, 3
    blt x12, x2, br_loop
    li x14, 6
    bne x13, x14, fail
    li x8, 0
    c.beqz x8, br9
    j fail
br9:
    c.addi x8, 1
    c.bnez x8, br10
    j fail
br10:
    c.j br11
    j fail
br11:
    c.jal br12
    j br13
br12:
    c.mv x15, x1
    la x16, br11
    addi x16, x16, 2
    bne x1, x16, fail
    c.jr x1
    j fail
br13:
    la x17, br14
    c.jalr x17
    j br15
br14:
    ret
br15:
    c.nop
    addi x18, x0, 5
    addi x18, x18, 5
    c.nop
    beq x18, x18, br16
    j fail
    c.nop
br16:
    addi x19, x0, 1
    c.nop
    jal x20, br17
    j fail
    c.nop
br17:
    addi x21, x20, 0
    sub x22, x21, x20
    bnez x22, fail
    li x23, 3
br_dec:
    addi x23, x23, -1
    bnez x23, br_dec
    bnez x23, fail
"""

EXCEPT = """
    li x24, 0
    ecall
    addi x1, x0, 1
    ebreak
    addi x2, x0, 2
    .word 0x00000000
    addi x3, x0, 3
    c.ebreak
    addi x3, x3, 1
    li x4, 0x200000
    li x5, 77
    lw x5, 0(x4)
    addi x6, x5, 1
    li x7, 77
    bne x5, x7, fail
    sw x6, 4(x4)
    la x24, ex_after_ferr
    li x7, 0x3800
    jalr x0, 0(x7)
    j fail
ex_after_ferr:
    addi x8, x0, 5
    ecall
    add x9, x8, x8
    csrr x10, 0x7ff
    addi x11, x10, 1
    beq x0, x0, ex_skip
    ecall
    .word 0x00000000
ex_skip:
    addi x12, x0, 12
    li x13, 0x3100
    lw x14, 0(x13)
    lw x15, 4(x13)
    lw x16, 8(x13)
    li x17, 0x200000
    li x18, 9
    sw x18, 0(x17)
    addi x19, x18, 1
    lb x20, 3(x17)
    beq x1, x1, ex_br
    j fail
ex_br:
    .word 0xffffffff
    addi x21, x0, 21
"""

FENCE = """
    la x1, fi_site
    li x2, 0x00700593
    sw x2, 0(x1)
    fence.i
fi_site:
    addi x11, x0, 1
    li x3, 7
    bne x11, x3, fail
    la x4, fi_site2
    li x5, 0x00900613
    sw x5, 0(x4)
    fence.i
    nop
fi_site2:
    addi x12, x0, 2
    li x6, 9
    bne x12, x6, fail
    fence
    li x7, 3
    la x8, fi_loop_site
    li x9, 0x00168693
fi_loop:
    sw x9, 0(x8)
    fence.i
fi_loop_site:
    addi x13, x13, 100
    addi x7, x7, -1
    bnez x7, fi_loop
    li x10, 3
    bne x13, x10, fail
"""

# Needs a periodic interrupt (the testbench re-raises it after each
# acknowledge); without one it sleeps forever.
WFI = """
    li x1, 0
    wfi
    addi x1, x1, 1
    wfi
    addi x1, x1, 1
    csrci mstatus, 8
    wfi
    addi x1, x1, 1
    csrr x2, mip
    srli x2, x2, 11
    andi x2, x2, 1
    li x3, 1
    bne x2, x3, fail
    lui x4, 0x100
    sw x0, 8(x4)
    csrsi mstatus, 8
    addi x5, x1, 1
    wfi
    add x6, x5, x5
    li x7, 3
    bne x1, x7, fail
"""

DIRECTED = {"alu": ALU, "load": LOAD, "muldiv": MULDIV, "csr": CSR,
            "counters": COUNTERS, "branch": BRANCH, "except": EXCEPT,
            "fence": FENCE, "wfi": WFI}


def random_body(seed, n=220):
    """A random straight-line-with-forward-branches program.

    Registers x1-x23 are data, x25 holds the data base 0x2800 and is never
    written. Destination and source registers are biased toward the most
    recently written ones so that distance-1 and distance-2 read-after-
    write hazards are frequent. Every branch and jump goes forward, so the
    program always terminates.
    """
    rnd = random.Random(seed)
    out = ["    li x25, 0x2800"]
    for r in range(1, 24):
        out.append("    li x%d, %d" % (r, rnd.randrange(-2048, 2048)))
    recent = [1, 2, 3]

    def src():
        if rnd.random() < 0.6:
            return rnd.choice(recent[-3:])
        return rnd.randrange(0, 24)

    def dst():
        r = rnd.randrange(1, 24)
        recent.append(r)
        return r
    labels = 0
    pending = []
    for i in range(n):
        while pending and pending[0][0] <= i:
            out.append("%s:" % pending.pop(0)[1])
        k = rnd.random()
        if k < 0.30:
            op = rnd.choice(["add", "sub", "xor", "or", "and", "sll", "srl", "sra", "slt", "sltu"])
            out.append("    %s x%d, x%d, x%d" % (op, dst(), src(), src()))
        elif k < 0.42:
            op = rnd.choice(["addi", "xori", "ori", "andi", "slti", "sltiu"])
            out.append("    %s x%d, x%d, %d" % (op, dst(), src(), rnd.randrange(-2048, 2048)))
        elif k < 0.46:
            op = rnd.choice(["slli", "srli", "srai"])
            out.append("    %s x%d, x%d, %d" % (op, dst(), src(), rnd.randrange(32)))
        elif k < 0.54:
            op = rnd.choice(["mul", "mulh", "mulhsu", "mulhu", "div", "divu", "rem", "remu"])
            out.append("    %s x%d, x%d, x%d" % (op, dst(), src(), src()))
        elif k < 0.66:
            op, align = rnd.choice([("lw", 4), ("lh", 2), ("lhu", 2), ("lb", 1), ("lbu", 1),
                                    ("lw", 1)])
            off = rnd.randrange(0, 1020 // align) * align
            out.append("    %s x%d, %d(x25)" % (op, dst(), off))
        elif k < 0.76:
            op, align = rnd.choice([("sw", 4), ("sh", 2), ("sb", 1), ("sw", 1)])
            off = rnd.randrange(0, 1020 // align) * align
            out.append("    %s x%d, %d(x25)" % (op, src(), off))
        elif k < 0.86:
            op = rnd.choice(["beq", "bne", "blt", "bge", "bltu", "bgeu"])
            lab = "rb%d" % labels
            labels += 1
            pending.append((i + rnd.randrange(1, 5), lab))
            pending.sort()
            out.append("    %s x%d, x%d, %s" % (op, src(), src(), lab))
        elif k < 0.89:
            lab = "rj%d" % labels
            labels += 1
            pending.append((i + rnd.randrange(1, 4), lab))
            pending.sort()
            out.append("    jal x%d, %s" % (dst(), lab))
        elif k < 0.92:
            r = rnd.randrange(1, 24)
            out.append("    csrrw x%d, mscratch, x%d" % (dst(), r))
        elif k < 0.97:
            r = rnd.randrange(8, 16)
            recent.append(r)
            c = rnd.choice(["c.addi x%d, %d" % (r, rnd.choice([-5, -1, 1, 7, 31])),
                            "c.mv x%d, x%d" % (r, rnd.randrange(1, 24)),
                            "c.add x%d, x%d" % (r, rnd.randrange(1, 24)),
                            "c.slli x%d, %d" % (r, rnd.randrange(1, 32)),
                            "c.sub x%d, x%d" % (r, rnd.randrange(8, 16))])
            out.append("    " + c)
        elif k < 0.985:
            out.append("    ecall")
        else:
            out.append("    lw x%d, 0(x25)" % dst())
            out.append("    add x%d, x%d, x%d" % (dst(), recent[-2], recent[-2]))
    for _, lab in pending:
        out.append("%s:" % lab)
    return "\n".join(out) + "\n    li x24, 0\n"
