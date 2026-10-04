# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual packet-port cases must reject broken credit/replay connections."""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from cocotb_results import count_results  # noqa: E402


@pytest.mark.parametrize('before,after', [
    ('.reserve_ready_i(reserve_ready_o)', ".reserve_ready_i(1'b1)"),
    ('.local_init_done_i(local_init_done_i)', ".local_init_done_i(1'b1)"),
    ('.reserve_payload_dw_i(reserve_payload_dw_o)', ".reserve_payload_dw_i(11'd0)"),
])
def test_real_packet_path_rejects_credit_wiring_faults(tmp_path, before, after):
    if not shutil.which('iverilog') or not (Path(sys.executable).parent / 'cocotb-config').is_file():
        pytest.skip('Actual Icarus and cocotb interpreter required')
    rtl = tmp_path / 'rtl'
    shutil.copytree(ROOT / 'hw/soc/rtl/pcie', rtl)
    source = rtl / 'soc_pcie_flow_packets.v'
    text = source.read_text()
    assert text.count(before) == 1
    source.write_text(text.replace(before, after))
    out = tmp_path / 'run'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/check_pcie_flow_packets.py'),
                             '--out', str(out), '--rtl-dir', str(rtl)],
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 1
    passed, failed, skipped = count_results([out / 'results.xml'])
    assert passed + failed == 3 and failed > 0 and skipped == 0
