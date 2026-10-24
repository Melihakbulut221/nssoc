/* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
 * SPDX-License-Identifier: Apache-2.0 */
#include "soc_mdio.h"
#include "soc_hal.h"
#include "soc_eth.h"

static int valid(const soc_mdio *bus, unsigned phy, unsigned reg) {
    return bus && bus->delay_us && phy < 32 && reg < 32;
}
static void drive(unsigned clock, unsigned enable, unsigned data) {
    soc_write32(ETH_MDIO, clock | (data << 1) | (enable << 2));
}
static void pause_half(const soc_mdio *bus) { bus->delay_us(bus->context, 1); }
static void send_bit(const soc_mdio *bus, unsigned bit) {
    drive(0, 1, bit); pause_half(bus);
    drive(1, 1, bit); pause_half(bus);
    drive(0, 1, bit);
}
static unsigned get_bit(const soc_mdio *bus) {
    drive(0, 0, 1); pause_half(bus);
    drive(1, 0, 1); pause_half(bus);
    unsigned bit = (soc_read32(ETH_MDIO) >> 8) & 1u;
    drive(0, 0, 1);
    return bit;
}
static void send_bits(const soc_mdio *bus, uint32_t value, unsigned count) {
    while (count--) send_bit(bus, (value >> count) & 1u);
}
static void header(const soc_mdio *bus, unsigned phy, unsigned reg, unsigned op) {
    drive(0, 0, 1); pause_half(bus);
    send_bits(bus, UINT32_MAX, 32);
    send_bits(bus, 1, 2); /* Clause 22 start = 01 */
    send_bits(bus, op, 2);
    send_bits(bus, phy, 5); send_bits(bus, reg, 5);
}
static void idle(const soc_mdio *bus) {
    drive(0, 0, 1); pause_half(bus);
}
int soc_mdio_read(const soc_mdio *bus, unsigned phy, unsigned reg, uint16_t *value) {
    if (!valid(bus, phy, reg) || !value) return SOC_MDIO_INVALID;
    header(bus, phy, reg, 2);
    unsigned z = get_bit(bus);
    unsigned ack = get_bit(bus);
    uint16_t data = 0;
    for (unsigned i = 0; i < 16; ++i) data = (uint16_t)((data << 1) | get_bit(bus));
    idle(bus);
    if (z != 1 || ack != 0) return SOC_MDIO_NO_ACK;
    *value = data;
    return SOC_MDIO_OK;
}
int soc_mdio_write(const soc_mdio *bus, unsigned phy, unsigned reg, uint16_t value) {
    if (!valid(bus, phy, reg)) return SOC_MDIO_INVALID;
    header(bus, phy, reg, 1); send_bits(bus, 2, 2); /* write turnaround = 10 */
    send_bits(bus, value, 16); idle(bus);
    return SOC_MDIO_OK;
}
static int configured(const soc_mdio *bus, unsigned phy) {
    uint16_t control, advert, gigabit;
    int rc = soc_mdio_read(bus, phy, 0, &control);
    if (rc) return rc;
    rc = soc_mdio_read(bus, phy, 4, &advert); if (rc) return rc;
    rc = soc_mdio_read(bus, phy, 9, &gigabit); if (rc) return rc;
    /* Forbid reset, loopback, powerdown and isolate. Speed/duplex fields are
     * ignored while AN is enabled. Reserved bits are not compared. */
    if ((control & 0xdc00u) != 0x1000u || (advert & 0xbfffu) != 1u ||
            (gigabit & 0xfb00u) != 0x0200u) return SOC_MDIO_CONFIG;
    return SOC_MDIO_OK;
}
int soc_eth_phy_start_1000fd(const soc_mdio *bus, unsigned phy) {
    uint16_t status, ext;
    int rc = soc_mdio_read(bus, phy, 1, &status); if (rc) return rc;
    rc = soc_mdio_read(bus, phy, 1, &status); if (rc) return rc;
    if ((status & 0x0108u) != 0x0108u) return SOC_MDIO_UNSUPPORTED;
    rc = soc_mdio_read(bus, phy, 15, &ext); if (rc) return rc;
    if (!(ext & 0x2000u)) return SOC_MDIO_UNSUPPORTED;
    rc = soc_mdio_write(bus, phy, 4, 0x0001); if (rc) return rc;
    rc = soc_mdio_write(bus, phy, 9, 0x0200); if (rc) return rc;
    rc = soc_mdio_write(bus, phy, 0, 0x1340); if (rc) return rc;
    return configured(bus, phy);
}
int soc_eth_phy_wait_1000fd(const soc_mdio *bus, unsigned phy, unsigned polls) {
    if (!valid(bus, phy, 0)) return SOC_MDIO_INVALID;
    if (!polls) return SOC_MDIO_TIMEOUT;
    for (unsigned i = 0; i < polls; ++i) {
        int rc = configured(bus, phy); if (rc) return rc;
        uint16_t status, gigabit;
        rc = soc_mdio_read(bus, phy, 1, &status); if (rc) return rc;
        rc = soc_mdio_read(bus, phy, 1, &status); if (rc) return rc;
        if (status & 0x0010u) return SOC_MDIO_PHY_FAULT;
        if ((status & 0x0024u) == 0x0024u) {
            rc = soc_mdio_read(bus, phy, 10, &gigabit); if (rc) return rc;
            if (gigabit & 0x8000u) return SOC_MDIO_PHY_FAULT;
            /* Partner advertises FD; both receivers report OK. */
            if ((gigabit & 0x3800u) == 0x3800u) return SOC_MDIO_OK;
        }
        if (i + 1 < polls) bus->delay_us(bus->context, 1000);
    }
    return SOC_MDIO_TIMEOUT;
}
