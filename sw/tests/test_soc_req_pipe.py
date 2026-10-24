# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exercise the real request-register RTL under stalls, resets and corruption."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / 'hw/soc/rtl/soc_req_pipe.v'
TB = ROOT / 'hw/soc/tb/tb_soc_req_pipe.v'
MUTATIONS = {
    'payload': ('{addr_i, we_i, be_i, wdata_i}',
                '{(addr_i ^ 32\'h1), we_i, be_i, wdata_i}'),
    'early_release': ('else if (req_o && gnt_i)', 'else if (req_o)'),
    'overwrite': ('rst_ni && req_i && !valid_q', 'rst_ni && req_i'),
    'bypass': ('assign req_o = rst_ni && valid_q;', 'assign req_o = rst_ni && req_i;'),
}


@pytest.mark.parametrize('mutation', ['original', *MUTATIONS])
def test_real_rtl_and_detected_faults(tmp_path, mutation):
    iverilog, vvp = shutil.which('iverilog'), shutil.which('vvp')
    if not iverilog or not vvp:
        pytest.skip('Icarus Verilog is required for RTL execution')
    text = RTL.read_text()
    if mutation != 'original':
        old, new = MUTATIONS[mutation]
        assert text.count(old) == 1
        text = text.replace(old, new)
    source = tmp_path / 'soc_req_pipe.v'
    source.write_text(text)
    binary = tmp_path / 'test.vvp'
    compiled = subprocess.run([iverilog, '-g2012', '-s', 'tb_soc_req_pipe',
                               '-o', str(binary), str(source), str(TB)],
                              capture_output=True, text=True, timeout=30)
    assert compiled.returncode == 0, compiled.stderr
    result = subprocess.run([vvp, str(binary)], capture_output=True, text=True, timeout=30)
    if mutation == 'original':
        assert result.returncode == 0 and 'PASS accepted=' in result.stdout, result.stdout
    else:
        assert result.returncode != 0 and 'FATAL:' in result.stdout, result.stdout
