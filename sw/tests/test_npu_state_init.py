# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exercise the actual C startup helper against an undefined-state register model."""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def executable(tmp_path_factory):
    cc = shutil.which('cc')
    if cc is None:
        pytest.skip('C compiler unavailable; install gcc or clang')
    out = tmp_path_factory.mktemp('npu-state-init')
    subprocess.run([sys.executable, str(ROOT / 'hw/soc/flow/gen_npu_vectors.py'),
                    str(out)], check=True, capture_output=True, text=True)
    source = out / 'test.c'
    source.write_text(r'''
#include <assert.h>
#include <stdlib.h>
#include "soc_npu_state_init.h"
static uint32_t words[512];
static unsigned known[512], selected, calls, reads, fault_at;
static void wr(uint32_t offset, uint32_t value) {
  calls++;
  if (offset == NPU_N_ADDR) { assert(value < 512); selected=value; return; }
  assert(offset == NPU_N_DATA);
  if (value == 0x000fffff) known[selected]=1;
  /* A zero-only write does not initialize this pessimistic mapped-state model. */
  words[selected]=known[selected] ? value : 0xdeadbeef;
}
static uint32_t rd(uint32_t offset) {
  calls++; reads++;
  assert(offset==NPU_N_DATA || offset==NPU_N_ADDR);
  uint32_t value=offset==NPU_N_ADDR ? selected : words[selected];
  return reads==fault_at ? value^1u : value;
}
int main(int argc, char **argv) {
  assert(argc==3);
  unsigned count=(unsigned)strtoul(argv[1],0,10);
  fault_at=(unsigned)strtoul(argv[2],0,10);
  int ok=soc_npu_state_init(count,wr,rd);
  if (count==0 || count>512) { assert(!ok && calls==0); return 0; }
  if(fault_at && fault_at<=count*3) {
    assert(!ok && reads==fault_at); /* Fail immediately; no later register access. */
    return 0;
  }
  assert(ok && calls==count*6);
  for(unsigned n=0;n<count;n++) assert(known[n] && words[n]==0);
  return 0;
}
''')
    binary = out / 'test'
    subprocess.run([cc, '-std=c99', '-Wall', '-Wextra', '-Werror', '-I', str(out),
                    '-I', str(ROOT / 'hw/soc/tb/sw/lib'), str(source), '-o', str(binary)],
                   check=True, capture_output=True, text=True)
    return binary


@pytest.mark.parametrize('neurons', [0, 1, 8, 512, 513])
def test_actual_helper_initializes_every_state_and_rejects_invalid_geometry(executable, neurons):
    subprocess.run([str(executable), str(neurons), '0'], check=True)


@pytest.mark.parametrize('fault_at', [1, 2, 3, 10, 11, 12, 24])
def test_address_pattern_and_zero_readback_errors_stop_bringup(executable, fault_at):
    subprocess.run([str(executable), '8', str(fault_at)], check=True)
