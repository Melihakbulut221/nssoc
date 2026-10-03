/* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef BOOT_GEOMETRY_H
#define BOOT_GEOMETRY_H

#include <stdint.h>

/* Validate untrusted header fields before copying any flash payload.
 * The exclusive RAM limit is the start of the loader's private area.
 * RV32IMC permits halfword entry alignment; payload stores are words.
 * Subtractions are guarded before evaluation so even a corrupt header
 * cannot wrap a bound. This pure predicate is also checked by CBMC.
 */
static inline int boot_geometry_valid(uint32_t load, uint32_t bytes,
                                      uint32_t entry, uint32_t ram_base,
                                      uint32_t private_start,
                                      uint32_t slot_bytes,
                                      uint32_t header_bytes) {
  return private_start >= ram_base
      && slot_bytes >= header_bytes
      && load >= ram_base
      && (load & 3u) == 0u
      && (bytes & 3u) == 0u
      && bytes != 0u
      && bytes <= 0xFFFFu /* QSPI_CMD_LEN is sixteen bits. */
      && bytes <= slot_bytes - header_bytes
      && bytes <= private_start - ram_base
      && load <= private_start - bytes
      && (entry & 1u) == 0u
      && entry >= load
      && entry < load + bytes;
}

#endif
