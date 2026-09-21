/* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
 * SPDX-License-Identifier: Apache-2.0 */
#ifndef SOC_ETH_H
#define SOC_ETH_H
#include "soc_memmap.h"
#include "soc_reg_offsets.h"
#define ETH_CTRL   (SOC_ETH_BASE + SOC_ETH_CTRL_OFF)
#define ETH_STATUS (SOC_ETH_BASE + SOC_ETH_STATUS_OFF)
#define ETH_TX     (SOC_ETH_BASE + SOC_ETH_TX_OFF)
#define ETH_RX     (SOC_ETH_BASE + SOC_ETH_RX_OFF)
#define ETH_EVENTS (SOC_ETH_BASE + SOC_ETH_EVENTS_OFF)
#define ETH_IRQEN  (SOC_ETH_BASE + SOC_ETH_IRQEN_OFF)
#define ETH_MDIO   (SOC_ETH_BASE + SOC_ETH_MDIO_OFF)
#define ETH_ID     (SOC_ETH_BASE + SOC_ETH_ID_OFF)
#define ETH_ENABLE 3u
#define ETH_FLUSH  4u
#define ETH_TX_READY 1u
#define ETH_RX_READY 2u
#define ETH_LAST   (1u << 8)
#define ETH_ABORT  (1u << 9)
#define ETH_RX_VALID (1u << 31)
#define ETH_IRQ_RX_READY (1u << 9)
#endif
