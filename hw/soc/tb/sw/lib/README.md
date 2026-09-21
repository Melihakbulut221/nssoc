# SoC bare-metal HAL
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

Include `lib/soc_hal.h` and link `lib/soc_hal.c` with the existing SoC include
path. The bootloader, SoC test program and three FI workloads share the console
implementation. The minimal non-SoC test program retains its testbench character
port. Interface helpers use the same MMIO and bounded polling functions.

| API | Contract |
|---|---|
| `soc_read32`, `soc_write32` | One volatile word transfer at the caller's aligned address |
| `soc_read8`, `soc_write8` | One volatile byte transfer, including CAN's byte register bank |
| `soc_wait32` | At most `polls` side-effect-free reads; success is `(read & mask) == expected` |
| `soc_uart_init` | Write SCALER, then CTRL, with the caller's values |
| `soc_uart_try_putc` | Poll TE; write DATA once on success; no write on timeout |
| `soc_uart_try_getc` | Poll DR; pop DATA once on success; leave the destination unchanged on timeout |
| `soc_uart_putc`, `soc_uart_puts` | Existing blocking boot/FI console policy |
| `soc_uart_hex32` | Eight lowercase hexadecimal digits; optional `0x` prefix |

Bounded calls return zero on success and `-1` on timeout. A zero polling budget
performs no I/O. `try_getc` returns `-2` for a null destination without touching
hardware. Poll budgets count register reads, not elapsed clock cycles. UART
framing/overrun reporting and clearing remain in the caller's status policy;
receiving a byte does not clear those sticky errors.

The caller serializes register ownership, including against interrupts. The
HAL does not retry a transfer, suppress a bus fault, feed the watchdog, change
interrupt masking, or claim a shared resource. `soc_wait32` must not be used on
read-to-pop registers. Existing blocking console users still rely on their
existing watchdog policy; new time-bounded users can select the `try_` APIs.

`SOC_HAL_TEST_IO` replaces only the primitive I/O definitions with host-provided
hooks for tests. Production builds omit that define and use direct volatile
access. The tests compile the actual library, check transfer counts and widths,
and reject compiled mutations that overrun a budget, pop on timeout or write
after failed polling:

```sh
python3 -m pytest -q sw/tests/test_soc_hal.py
```

This HAL supplies common access and console operations. It does not by itself
close CAN/GPTIMER register-generation work, firmware stack protection, fault
qualification or the product's remaining acceptance gates.
