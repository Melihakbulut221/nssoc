# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Binary function preservation and full-boot source-selection boundaries."""
import itertools
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import prepare_npu_reconvergence_eco as eco
import run_cloud_npu_init_eco as cloud


@pytest.mark.parametrize('a,b,c,d', list(itertools.product((0, 1), repeat=4)))
def test_factoring_covers_all_binary_inputs(a, b, c, d):
    original = not ((a or b) and not (a and c and d))
    replacement = (c and d) if a else not b
    assert original == replacement
    assert eco.binary_truth_table()[a * 8 + b * 4 + c * 2 + d]['factored'] == int(original)


def test_preparation_rejects_unbound_source():
    with pytest.raises(ValueError, match='input differs'):
        eco.prepare((eco.PREDECESSOR + '\n' + eco.OLD).encode())


def test_compile_relocation_keeps_vendor_models_firmware_defines_and_workload():
    command = ['iverilog', '-o', 'old.vvp', '-DTIMEOUT_CYCLES=3000000', '-DFUNCTIONAL',
               'bench.v', 'source.v', 'native.v', 'vendor_sram.v']
    actual = cloud.compile_command(command, 'source.v', 'eco.v', 'new.vvp')
    assert actual == ['iverilog', '-o', 'new.vvp', '-DTIMEOUT_CYCLES=3000000', '-DFUNCTIONAL',
                      'bench.v', 'eco.v', 'native.v', 'vendor_sram.v']
    assert command[2] == 'old.vvp'


@pytest.mark.parametrize('command', [
    ['iverilog', '-o', 'old.vvp', '-DTIMEOUT_CYCLES=3000000', 'wrong.v'],
    ['iverilog', '-o', 'old.vvp', '-DTIMEOUT_CYCLES=3000000', 'source.v', 'source.v'],
    ['iverilog', '-o', 'old.vvp', '-o', 'other.vvp', '-DTIMEOUT_CYCLES=3000000', 'source.v'],
    ['iverilog', '-o', 'old.vvp', '-DTIMEOUT_CYCLES=3000001', 'source.v'],
])
def test_compile_rejects_ambiguous_or_changed_boot(command):
    with pytest.raises(ValueError, match='differs'):
        cloud.compile_command(command, 'source.v', 'eco.v', 'new.vvp')
