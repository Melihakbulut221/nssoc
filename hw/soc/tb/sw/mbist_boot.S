# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Integration test ROM: real Ibex reads every RAM row after destructive MBIST,
# then writes/reads every row through ECC, including byte stores. No SRAM preload.
.section .text
.global _start
_start:
    li a0, 0xff908038
    li a1, 0xa51f0004
    li t0, 0
    li t1, 32768
zero_check:
    sw a1, 0(a0)
    lw t2, 0(t0)
    bnez t2, fail
    addi t0, t0, 4
    bltu t0, t1, zero_check
    li t0, 0
    li t3, 0x5aa50000
write_check:
    sw a1, 0(a0)
    xor t2, t0, t3
    sw t2, 0(t0)
    lw t4, 0(t0)
    bne t2, t4, fail
    li t5, 0x6d
    sb t5, 0(t0)
    lbu t4, 0(t0)
    bne t4, t5, fail
    addi t0, t0, 4
    bltu t0, t1, write_check
    li t0, 0x7ffc
    li t1, 0x600dc0de
    sw t1, 0(t0)
pass:
    j pass
fail:
    li t0, 0x7ffc
    li t1, 0xbad0bad0
    sw t1, 0(t0)
    j fail
