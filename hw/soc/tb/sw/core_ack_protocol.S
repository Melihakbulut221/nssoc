// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0
// Directed actual-core protocol workload. No replacement of the LSU or PMP.
  .option norvc
  .section .text.start,"ax"
  .global _start
_start:
  j main

  .section .text,"ax"
  .macro check reg, value
    li t3, \value
    bne \reg, t3, fail
  .endm
  .macro fault operation, address, cause, badaddr
    li t0, \address
    li s0, 0
    li s1, \cause
    li s2, \badaddr
    la s3, fault_pc\@
fault_pc\@:
    \operation t2, 1(t0)
    check s0, 1
  .endm
main:
  li sp, 0x2ff0
  la t0, trap_vectors
  csrw mtvec, t0
  li s4, 0
  li s5, 0
  li t0, 0x2000
  li t1, 0x11223344
  sw t1, 0(t0)
  li t1, 0x55667788
  sw t1, 4(t0)
  lw t2, 0(t0)
  check t2, 0x11223344
  lw t2, 1(t0)
  check t2, 0x88112233
  lw t2, 2(t0)
  check t2, 0x77881122
  lw t2, 3(t0)
  check t2, 0x66778811
  lhu t2, 3(t0)
  check t2, 0x8811
  // Misaligned stores, byte enables and immediate load-use/branch hazards.
  sw zero, 16(t0)
  sw zero, 20(t0)
  li t1, 0xa1b2c3d4
  sw t1, 17(t0)
  lw t2, 16(t0)
  check t2, 0xb2c3d400
  lw t2, 20(t0)
  check t2, 0xa1
  li t1, 0x7e81
  sh t1, 23(t0)
  lhu t2, 23(t0)
  check t2, 0x7e81
  li t1, 0x80
  sb t1, 28(t0)
  lbu t2, 28(t0)
  check t2, 0x80
  lb t2, 28(t0)
  check t2, -128
  li t1, 0x12345678
  sw t1, 32(t0)
  lw t2, 32(t0)
  bne t1, t2, fail
  addi t2, t2, 1
  check t2, 0x12345679

  // Locked NAPOT 8-byte denied regions. M-mode must really be denied.
  li t0, 0xc00
  csrw pmpaddr0, t0
  li t0, 0xc42
  csrw pmpaddr1, t0
  li t0, 0x9898
  csrw pmpcfg0, t0
  li t2, 0xa5a55a5a
  fault lw, 0x3004, 5, 0x3005
  fault lw, 0x3104, 5, 0x3108
  fault sw, 0x3004, 7, 0x3005
  fault sw, 0x3104, 7, 0x3108
  // The bus model faults only 0x3204 and 0x3308; other split beats proceed.
  fault lw, 0x3204, 5, 0x3205
  fault lw, 0x3304, 5, 0x3308
  fault sw, 0x3204, 7, 0x3205
  fault sw, 0x3304, 7, 0x3308
  check s4, 8

  // Exercise the actual Ibex clock gate, then a machine-software interrupt.
  li t0, 0x3fe8
  li t1, 1
  sw t1, 0(t0)
  li t0, 8
  csrw mie, t0
  csrs mstatus, t0
  wfi
wait_irq:
  beqz s5, wait_irq
  check s5, 1
  li t0, 0x3fe0
  sw s4, 0(t0)
  sw s5, 4(t0)
  li t0, 0x3ff0
  li t1, 0x600dc0de
  sw t1, 0(t0)
finished:
  wfi
  j finished
fail:
  li t0, 0x3ff0
  li t1, 0xbad0bad0
  sw t1, 0(t0)
  j finished

  .section .trapvec,"ax"
  .balign 256
  .global trap_vectors
trap_vectors:
  .rept 32
    j trap_handler
  .endr
trap_handler:
  csrr t4, mcause
  bltz t4, interrupt
  bne t4, s1, fail
  csrr t5, mtval
  bne t5, s2, fail
  csrr t6, mepc
  bne t6, s3, fail
  addi s0, s0, 1
  addi s4, s4, 1
  addi t6, t6, 4
  csrw mepc, t6
  mret
interrupt:
  li t5, 0x80000003
  bne t4, t5, fail
  csrw mie, zero
  addi s5, s5, 1
  mret
