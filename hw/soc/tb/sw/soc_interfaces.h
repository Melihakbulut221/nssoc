// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0
#ifndef SOC_INTERFACES_H
#define SOC_INTERFACES_H
#include <stdint.h>
#include "soc_memmap.h"

/* Project register maps, not GRLIB-compatible. See docs/88. */
static inline uint32_t soc_if_read(uint32_t base, uint32_t offset) {
    return *(volatile uint32_t *)(uintptr_t)(base + offset);
}
static inline void soc_if_write(uint32_t base, uint32_t offset, uint32_t value) {
    *(volatile uint32_t *)(uintptr_t)(base + offset) = value;
}
static inline int soc_if_wait(uint32_t base, uint32_t offset,
                              uint32_t mask, uint32_t value, unsigned limit) {
    while (limit--) if ((soc_if_read(base, offset) & mask) == value) return 0;
    return -1;
}
static inline int soc_spi_byte(uint8_t tx, uint8_t *rx, unsigned limit) {
    if (soc_if_read(SOC_SPI_BASE, 12) & 1) return -1;
    soc_if_write(SOC_SPI_BASE, 8, tx);
    if (soc_if_wait(SOC_SPI_BASE, 12, 1, 0, limit)) return -1;
    *rx = (uint8_t)soc_if_read(SOC_SPI_BASE, 8);
    return 0;
}
static inline int soc_spw_put(uint16_t character, unsigned limit) {
    if (soc_if_wait(SOC_SPW_BASE, 4, 8, 8, limit)) return -1;
    soc_if_write(SOC_SPW_BASE, 12, character & 0x1ff);
    return 0;
}
static inline int soc_spw_get(uint16_t *character, unsigned limit) {
    if (soc_if_wait(SOC_SPW_BASE, 4, 16, 16, limit)) return -1;
    *character = (uint16_t)soc_if_read(SOC_SPW_BASE, 16);
    return 0;
}
/* One byte, START or repeated START, optionally STOP. The caller must
 * serialize access; no hidden retry after NACK or a hardware timeout. */
static inline int soc_i2c_byte(uint8_t address, int read, int stop,
                              uint8_t *data, unsigned limit) {
    if (soc_if_read(SOC_I2C_BASE, 0) & 17) return -1;
    soc_if_write(SOC_I2C_BASE, 8, address & 127);
    soc_if_write(SOC_I2C_BASE, 24, 15);
    if (!read) soc_if_write(SOC_I2C_BASE, 16, *data);
    soc_if_write(SOC_I2C_BASE, 12, 4 | (stop ? 8 : 0) | (read ? 1 : 2));
    if (soc_if_wait(SOC_I2C_BASE, 0, 1, 0, limit)) {
        soc_if_write(SOC_I2C_BASE, 12, 16);  /* release pins on software timeout */
        return -1;
    }
    if (soc_if_read(SOC_I2C_BASE, 24) & 10) return -2;
    if (read) {
        if (!(soc_if_read(SOC_I2C_BASE, 0) & 16)) return -1;
        *data = (uint8_t)soc_if_read(SOC_I2C_BASE, 16);
    }
    return 0;
}
/* SJA1000 byte registers; word accesses deliberately fault. */
static inline uint8_t soc_can_read(unsigned offset) {
    return *(volatile uint8_t *)(uintptr_t)(SOC_CAN_BASE + offset);
}
static inline void soc_can_write(unsigned offset, uint8_t data) {
    *(volatile uint8_t *)(uintptr_t)(SOC_CAN_BASE + offset) = data;
}
#endif
