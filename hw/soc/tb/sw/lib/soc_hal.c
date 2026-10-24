// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0
#include "soc_hal.h"
#include "soc_memmap.h"
#include "soc_reg_offsets.h"

#define UART_DATA (SOC_UART0_BASE + SOC_UART_DATA_OFF)
#define UART_STATUS (SOC_UART0_BASE + SOC_UART_STATUS_OFF)
#define UART_CTRL (SOC_UART0_BASE + SOC_UART_CTRL_OFF)
#define UART_SCALER (SOC_UART0_BASE + SOC_UART_SCALER_OFF)
#define UART_TE (1u << 2)
#define UART_DR (1u << 0)

int soc_wait32(uintptr_t address, uint32_t mask, uint32_t expected, unsigned polls) {
    while (polls--) if ((soc_read32(address) & mask) == expected) return 0;
    return -1;
}

void soc_uart_init(uint32_t scaler, uint32_t control) {
    soc_write32(UART_SCALER, scaler);
    soc_write32(UART_CTRL, control);
}

int soc_uart_try_putc(uint8_t value, unsigned polls) {
    if (soc_wait32(UART_STATUS, UART_TE, UART_TE, polls)) return -1;
    soc_write32(UART_DATA, value);
    return 0;
}

int soc_uart_try_getc(uint8_t *value, unsigned polls) {
    if (!value) return -2;
    if (soc_wait32(UART_STATUS, UART_DR, UART_DR, polls)) return -1;
    *value = (uint8_t)soc_read32(UART_DATA);
    return 0;
}

void soc_uart_putc(char value) {
    while (!(soc_read32(UART_STATUS) & UART_TE)) { }
    soc_write32(UART_DATA, (uint32_t)value);
}

void soc_uart_puts(const char *text) {
    while (*text) soc_uart_putc(*text++);
}

void soc_uart_hex32(uint32_t value, int prefix) {
    const char *digits = "0123456789abcdef";
    if (prefix) { soc_uart_putc('0'); soc_uart_putc('x'); }
    for (int shift = 28; shift >= 0; shift -= 4)
        soc_uart_putc(digits[(value >> shift) & 15u]);
}
