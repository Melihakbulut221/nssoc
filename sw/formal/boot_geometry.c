/* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
 * SPDX-License-Identifier: Apache-2.0
 * cbmc sw/formal/boot_geometry.c --function main --bounds-check
 *   --pointer-check --unsigned-overflow-check --signed-overflow-check
 *   --conversion-check --div-by-zero-check --unwinding-assertions
 */
#include <assert.h>
#include <stdint.h>
#include "../../hw/soc/tb/sw/boot_geometry.h"

uint32_t nondet_uint32_t(void);

int main(void) {
  uint32_t load = nondet_uint32_t(), bytes = nondet_uint32_t();
  uint32_t entry = nondet_uint32_t(), base = nondet_uint32_t();
  uint32_t priv = nondet_uint32_t(), slot = nondet_uint32_t();
  uint32_t header = nondet_uint32_t(), word = nondet_uint32_t();
  if (boot_geometry_valid(load, bytes, entry, base, priv, slot, header)) {
    assert(bytes != 0 && (bytes & 3u) == 0);
    assert((load & 3u) == 0 && (entry & 1u) == 0);
    assert(load >= base && load < priv);
    assert((uint64_t)load + bytes <= priv);
    assert(entry >= load && (uint64_t)entry < (uint64_t)load + bytes);
    assert((uint64_t)header + bytes <= slot);
    assert(bytes <= 0xFFFFu);
    /* An arbitrary iteration of the copy loop, without bounding length. */
    if (word < bytes / 4u) {
      uint32_t dst = load + 4u * word;
      uint32_t src = header + 4u * word;
      assert(dst >= base && (uint64_t)dst + 4u <= priv);
      assert((uint64_t)src + 4u <= slot);
    }
  }
  return 0;
}
