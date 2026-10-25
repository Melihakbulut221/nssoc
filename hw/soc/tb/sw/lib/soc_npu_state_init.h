// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0
#ifndef SOC_NPU_STATE_INIT_H
#define SOC_NPU_STATE_INIT_H

#include <stdint.h>
#include "npu_regs.h"

/* Initialize through the real serial register window, while the node is idle
 * and disabled. Some mapped implementations retain X in refractory/check
 * feedback after STATE_CLR or a zero-only debug write. Writing all 20 payload
 * bits high first breaks that feedback; then zero and verify every neuron.
 * This is a destructive startup sequence, never a live-state repair. It does
 * not clear fault counters or preload simulation memory. The caller enables
 * the node only after this returns success. */
static inline int soc_npu_state_init(
    unsigned neurons,
    void (*write_reg)(uint32_t offset, uint32_t value),
    uint32_t (*read_reg)(uint32_t offset)) {
  const uint32_t pattern = 0x000fffffu; /* N_DATA: R[19:16], V[15:0]. */
  if (neurons == 0u || neurons > 512u) return 0;
  for (unsigned n = 0; n < neurons; n++) {
    write_reg(NPU_N_ADDR, n);
    if (read_reg(NPU_N_ADDR) != n) return 0;
    write_reg(NPU_N_DATA, pattern);
    if (read_reg(NPU_N_DATA) != pattern) return 0;
    write_reg(NPU_N_DATA, 0u);
    if (read_reg(NPU_N_DATA) != 0u) return 0;
  }
  return 1;
}
#endif
