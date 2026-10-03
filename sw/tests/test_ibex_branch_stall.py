# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Execute the pinned CPU's store/branch hazard and its failing configuration."""
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOC = ROOT / 'hw/soc'


def test_soc_writeback_selects_dedicated_branch_alu():
    source = (SOC / 'rtl/soc_top.v').read_text()
    assert re.search(r'\.BranchTargetALU\s*\(CORE_WB_STAGE\)', source)
    assert re.search(r'\.WritebackStage\s*\(CORE_WB_STAGE\)', source)


@pytest.mark.parametrize('delay', [1, 2, 3, 5, 8])
@pytest.mark.parametrize('writeback', [0, 1])
def test_branch_with_delayed_store_response(tmp_path, delay, writeback):
    run_cpu(tmp_path, delay, writeback, writeback, expect_pass=True)


@pytest.mark.parametrize('delay', [5, 8])
def test_unsupported_shared_alu_control_is_detected(tmp_path, delay):
    run_cpu(tmp_path, delay, 1, 0, expect_pass=False)


def run_cpu(tmp_path, delay, writeback, branch_alu, *, expect_pass):
    iverilog, vvp = shutil.which('iverilog'), shutil.which('vvp')
    generated = sorted((SOC / 'gen').glob('*.v'))
    if not iverilog or not vvp or not (SOC / 'gen/ibex_top.v').is_file():
        pytest.skip('Icarus and the pinned converted Ibex sources are required')
    binary = tmp_path / 'branch.vvp'
    command = [iverilog, '-g2005-sv', '-DSG13G2_ICG_BEHAVIOURAL',
               '-DIBEX_PMPENABLE=1', '-DIBEX_SECUREIBEX=0',
               '-s', 'tb_ibex_branch_stall', '-o', str(binary)]
    for name, value in [('WRITEBACK', writeback), ('BRANCH_ALU', branch_alu),
                        ('RESPONSE_CYCLES', delay)]:
        command.append(f'-Ptb_ibex_branch_stall.{name}={value}')
    command += [str(SOC / 'tb/tb_ibex_branch_stall.v'),
                str(SOC / 'tb/ibex_min_system.v'),
                str(SOC / 'rtl/prim_clock_gating.v'), *map(str, generated)]
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=60)
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    result = subprocess.run([vvp, str(binary)], capture_output=True, text=True, timeout=30)
    output = result.stdout + result.stderr
    if expect_pass:
        assert result.returncode == 0 and 'PASS branch after delayed store' in output, output
    else:
        assert result.returncode != 0 and 'Unexpected trap' in output, output
        assert 'pc=fffff926' in output, output
