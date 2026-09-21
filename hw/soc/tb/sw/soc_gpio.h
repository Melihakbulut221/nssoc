// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0

/* Register offsets and fields for the GPIO port docs/65 adds,
 * hw/soc/rtl/soc_gpio.v.
 *
 * Slot bases come from generated soc_memmap.h; the implemented GPIO
 * offsets come from regmap/peripherals/gpio.yaml via soc_reg_offsets.h.
 * Fields below describe this implementation of GRLIB's GRGPIO map.
 *
 * What the block implements of that map, and what it leaves out, is in
 * soc_gpio.v's header; CAP reports it and check 28 reads CAP.
 */
#ifndef SOC_GPIO_H
#define SOC_GPIO_H

#include "soc_memmap.h"
#include "soc_reg_offsets.h"

#define GPIO_NBITS      16u
#define GPIO_PINS       ((1u << GPIO_NBITS) - 1u)

/* grip.pdf table 923 */
#define GPIO_DATA       (SOC_GPIO_BASE + SOC_GPIO_DATA_OFF)   /* r   synchronised pins */
#define GPIO_OUTPUT     (SOC_GPIO_BASE + SOC_GPIO_OUTPUT_OFF)   /* rw                    */
#define GPIO_DIR        (SOC_GPIO_BASE + SOC_GPIO_DIR_OFF)   /* rw  1 = output        */
#define GPIO_IMASK      (SOC_GPIO_BASE + SOC_GPIO_IMASK_OFF)   /* rw  1 = may interrupt */
#define GPIO_IPOL       (SOC_GPIO_BASE + SOC_GPIO_IPOL_OFF)   /* rw  level: 1 = high; edge: 1 = rising */
#define GPIO_IEDGE      (SOC_GPIO_BASE + SOC_GPIO_IEDGE_OFF)   /* rw  1 = edge          */
#define GPIO_BYPASS     (SOC_GPIO_BASE + SOC_GPIO_BYPASS_OFF)   /* r   reads zero        */
#define GPIO_CAP        (SOC_GPIO_BASE + SOC_GPIO_CAP_OFF)   /* r                     */
#define GPIO_IAVAIL     (SOC_GPIO_BASE + SOC_GPIO_IAVAIL_OFF)   /* r   every line        */
#define GPIO_IFLAG      (SOC_GPIO_BASE + SOC_GPIO_IFLAG_OFF)   /* wc  write 1 to clear  */
#define GPIO_OUTPUT_OR  (SOC_GPIO_BASE + SOC_GPIO_OUTPUT_OR_OFF)   /* w   OUTPUT |= wdata   */
#define GPIO_DIR_OR     (SOC_GPIO_BASE + SOC_GPIO_DIR_OR_OFF)
#define GPIO_IMASK_OR   (SOC_GPIO_BASE + SOC_GPIO_IMASK_OR_OFF)
#define GPIO_OUTPUT_AND (SOC_GPIO_BASE + SOC_GPIO_OUTPUT_AND_OFF)   /* w   OUTPUT &= wdata   */
#define GPIO_DIR_AND    (SOC_GPIO_BASE + SOC_GPIO_DIR_AND_OFF)
#define GPIO_IMASK_AND  (SOC_GPIO_BASE + SOC_GPIO_IMASK_AND_OFF)
#define GPIO_OUTPUT_XOR (SOC_GPIO_BASE + SOC_GPIO_OUTPUT_XOR_OFF)   /* w   OUTPUT ^= wdata   */
#define GPIO_DIR_XOR    (SOC_GPIO_BASE + SOC_GPIO_DIR_XOR_OFF)
#define GPIO_IMASK_XOR  (SOC_GPIO_BASE + SOC_GPIO_IMASK_XOR_OFF)

/* grip.pdf table 931, the capability register. */
#define GPIO_CAP_PU         (1u << 18)   /* pulse register present         */
#define GPIO_CAP_IER        (1u << 17)   /* input enable register present  */
#define GPIO_CAP_IFL        (1u << 16)   /* interrupt flag register present */
#define GPIO_CAP_IRQGEN(v)  (((v) >> 8) & 0x1Fu)
#define GPIO_CAP_NLINES(v)  ((v) & 0x1Fu)

#endif /* SOC_GPIO_H */
