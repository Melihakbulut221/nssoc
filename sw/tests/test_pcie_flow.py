# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual native port benches must reject four credit-accounting defects."""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from cocotb_results import count_results  # noqa: E402


@pytest.mark.parametrize('before,after', [
    ("+12'd3", "+12'd0"),
    ('reserve_valid_i && reserve_ready_o && !reserve_replay_i', 'reserve_valid_i && !reserve_replay_i'),
    ('reserve_valid_i && reserve_ready_o && !reserve_replay_i', 'reserve_valid_i && reserve_ready_o'),
    ('if (h_update_ok && d_update_ok)', "if (1'b1)"),
])
def test_native_credit_port_checks_reject_real_faults(tmp_path, before, after):
    if not shutil.which('iverilog') or not (Path(sys.executable).parent / 'cocotb-config').is_file():
        pytest.skip('Actual Icarus and cocotb interpreter required')
    source = ROOT / 'hw/soc/rtl/pcie/soc_pcie_credit_tx.v'
    text = source.read_text()
    assert text.count(before) == 1
    rtl = tmp_path / 'rtl'
    rtl.mkdir()
    (rtl / source.name).write_text(text.replace(before, after))
    out = tmp_path / 'run'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/check_pcie_flow.py'),
                             '--out', str(out), '--rtl-dir', str(rtl)],
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 1
    passed, failed, skipped = count_results([out / 'results.xml'])
    assert passed + failed == 4 and failed > 0 and skipped == 0
