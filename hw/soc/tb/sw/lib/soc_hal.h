// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0
#ifndef SOC_HAL_H
#define SOC_HAL_H
#include <stdint.h>

/* Exact-width volatile transfers. No retry, fault suppression or interrupt
 * ownership is implied. The caller supplies an address aligned to its width.
 * Byte accesses are necessary for the CAN register bank. */
#ifdef SOC_HAL_TEST_IO
uint32_t soc_read32(uintptr_t address);
void soc_write32(uintptr_t address, uint32_t value);
uint8_t soc_read8(uintptr_t address);
void soc_write8(uintptr_t address, uint8_t value);
#else
static inline uint32_t soc_read32(uintptr_t address) {
    return *(volatile uint32_t *)address;
}
static inline void soc_write32(uintptr_t address, uint32_t value) {
    *(volatile uint32_t *)address = value;
}
static inline uint8_t soc_read8(uintptr_t address) {
    return *(volatile uint8_t *)address;
}
static inline void soc_write8(uintptr_t address, uint8_t value) {
    *(volatile uint8_t *)address = value;
}
#endif

/* At most polls reads, including the successful one; zero performs no I/O.
 * Use only on registers whose reads have no side effects. 0 = ready, -1 =
 * timeout. A bus error still reaches the platform trap handler. */
int soc_wait32(uintptr_t address, uint32_t mask, uint32_t expected, unsigned polls);
void soc_uart_init(uint32_t scaler, uint32_t control);
int soc_uart_try_putc(uint8_t value, unsigned polls);
/* A null destination returns -2 without I/O. A timeout never pops DATA. */
int soc_uart_try_getc(uint8_t *value, unsigned polls);

/* Legacy console behavior: wait until the transmitter accepts each byte.
 * Existing boot/FI callers retain their watchdog and interrupt policies.
 * Applications needing a software bound use try_putc instead. Calls must be
 * serialized with any interrupt handler that also owns the UART. */
void soc_uart_putc(char value);
void soc_uart_puts(const char *text);
void soc_uart_hex32(uint32_t value, int prefix);
#endif
