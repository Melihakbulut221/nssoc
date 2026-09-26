/* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
 * SPDX-License-Identifier: Apache-2.0 */
#ifndef SOC_MDIO_H
#define SOC_MDIO_H
#include <stdint.h>

/* Exclusive ownership of ETH_MDIO is required for the whole call. The caller
 * supplies a calibrated delay of AT LEAST the requested microseconds, including
 * across interrupt handling. Each MDC half-period is >=1us (<=500kHz); the read
 * sample also waits for the SoC's two-flop input synchronizer. No PHY-specific
 * strap, GMII mux, reset GPIO or board/pad setup is implied by this driver. */
typedef struct {
    void (*delay_us)(void *context, unsigned microseconds);
    void *context;
} soc_mdio;
enum {
    SOC_MDIO_OK = 0, SOC_MDIO_INVALID = -1, SOC_MDIO_NO_ACK = -2,
    SOC_MDIO_UNSUPPORTED = -3, SOC_MDIO_TIMEOUT = -4,
    SOC_MDIO_PHY_FAULT = -5, SOC_MDIO_CONFIG = -6
};
/* Clause 22, 32-bit preamble on EVERY transaction; phy/reg are 0..31.
 * Output is unchanged on failure. Valid transactions end with MDC low and MDIO released.
 * Writes have no protocol acknowledgement; management setup reads them back. */
int soc_mdio_read(const soc_mdio *bus, unsigned phy, unsigned reg, uint16_t *value);
int soc_mdio_write(const soc_mdio *bus, unsigned phy, unsigned reg, uint16_t value);
/* Configure standard 1000BASE-T-only full-duplex advertisement and restart AN.
 * Reject a PHY lacking AN/extended-status/1000BASE-T FD capability. Does not
 * enable the MAC. A partial configuration is possible if MDIO fails mid-call. */
int soc_eth_phy_start_1000fd(const soc_mdio *bus, unsigned phy);
/* At most polls link checks, 1ms between unsuccessful checks, zero = no I/O.
 * Recheck local advertisement/control; never accept 10/100 or half-duplex as a
 * ready link for the fixed 1Gb/s MAC. BMSR is read twice for latch-low status. */
int soc_eth_phy_wait_1000fd(const soc_mdio *bus, unsigned phy, unsigned polls);
#endif
