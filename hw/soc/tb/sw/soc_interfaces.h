// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0
#ifndef SOC_INTERFACES_H
#define SOC_INTERFACES_H
#include <stdint.h>
#include "soc_memmap.h"
#include "soc_reg_offsets.h"
#include "soc_can_regs.h"
#include "lib/soc_hal.h"

/* Project register maps, not GRLIB-compatible. See docs/88. */
static inline uint32_t soc_if_read(uint32_t base, uint32_t offset) {
    return soc_read32((uintptr_t)(base + offset));
}
static inline void soc_if_write(uint32_t base, uint32_t offset, uint32_t value) {
    soc_write32((uintptr_t)(base + offset), value);
}
static inline int soc_if_wait(uint32_t base, uint32_t offset,
                              uint32_t mask, uint32_t value, unsigned limit) {
    return soc_wait32((uintptr_t)(base + offset), mask, value, limit);
}
static inline int soc_spi_byte(uint8_t tx, uint8_t *rx, unsigned limit) {
    if (soc_if_read(SOC_SPI_BASE, SOC_SPI_STATUS_OFF) & 1) return -1;
    soc_if_write(SOC_SPI_BASE, SOC_SPI_DATA_OFF, tx);
    if (soc_if_wait(SOC_SPI_BASE, SOC_SPI_STATUS_OFF, 1, 0, limit)) return -1;
    *rx = (uint8_t)soc_if_read(SOC_SPI_BASE, SOC_SPI_DATA_OFF);
    return 0;
}
static inline int soc_spw_put(uint16_t character, unsigned limit) {
    if (soc_if_wait(SOC_SPW_BASE, SOC_SPW_STATUS_OFF, 8, 8, limit)) return -1;
    soc_if_write(SOC_SPW_BASE, SOC_SPW_TX_OFF, character & 0x1ff);
    return 0;
}
static inline int soc_spw_get(uint16_t *character, unsigned limit) {
    if (soc_if_wait(SOC_SPW_BASE, SOC_SPW_STATUS_OFF, 16, 16, limit)) return -1;
    *character = (uint16_t)soc_if_read(SOC_SPW_BASE, SOC_SPW_RX_OFF);
    return 0;
}
/* One byte, START or repeated START, optionally STOP. The caller must
 * serialize access; no hidden retry after NACK or a hardware timeout. */
static inline int soc_i2c_byte(uint8_t address, int read, int stop,
                              uint8_t *data, unsigned limit) {
    if (soc_if_read(SOC_I2C_BASE, SOC_I2C_STATUS_OFF) & 17) return -1;
    soc_if_write(SOC_I2C_BASE, SOC_I2C_ADDRESS_OFF, address & 127);
    soc_if_write(SOC_I2C_BASE, SOC_I2C_EVENTS_OFF, 15);
    if (!read) soc_if_write(SOC_I2C_BASE, SOC_I2C_DATA_OFF, *data);
    soc_if_write(SOC_I2C_BASE, SOC_I2C_COMMAND_OFF, 4 | (stop ? 8 : 0) | (read ? 1 : 2));
    if (soc_if_wait(SOC_I2C_BASE, SOC_I2C_STATUS_OFF, 1, 0, limit)) {
        soc_if_write(SOC_I2C_BASE, SOC_I2C_COMMAND_OFF, 16);  /* release pins on software timeout */
        return -1;
    }
    if (soc_if_read(SOC_I2C_BASE, SOC_I2C_EVENTS_OFF) & 10) return -2;
    if (read) {
        if (!(soc_if_read(SOC_I2C_BASE, SOC_I2C_STATUS_OFF) & 16)) return -1;
        *data = (uint8_t)soc_if_read(SOC_I2C_BASE, SOC_I2C_DATA_OFF);
    }
    return 0;
}
/* SJA1000 byte registers; word accesses deliberately fault. */
static inline uint8_t soc_can_read(unsigned offset) {
    return soc_read8((uintptr_t)(SOC_CAN_BASE + offset));
}
static inline void soc_can_write(unsigned offset, uint8_t data) {
    soc_write8((uintptr_t)(SOC_CAN_BASE + offset), data);
}
#endif
