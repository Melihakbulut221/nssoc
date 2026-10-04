# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Execute real port scoreboards against concrete ownership/FC wiring faults."""

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from cocotb_results import count_results  # noqa: E402


MUTANTS = [
    (
        "soc_pcie_rx_credit",
        "if(packet_accepted_i) begin",
        "if(packet_accepted_i || packet_duplicate_i) begin",
    ),
    (
        "soc_pcie_rx_credit",
        "localparam [7:0] H_INIT=SLOTS_PER_CLASS;",
        "localparam [7:0] H_INIT=SLOTS_PER_CLASS+1;",
    ),
    (
        "soc_pcie_rx_credit",
        "wire select_dllp=output_active ? output_dllp : dllp_pending;",
        "wire select_dllp=output_active ? output_dllp : 1'b0;",
    ),
    ("soc_pcie_fc_tx", "if(tx_valid_o && tx_ready_i) begin", "if(tx_valid_o) begin"),
    (
        "soc_pcie_fc_tx",
        "2: octet={header[1:0],2'b00,data_credit[11:8]};",
        "2: octet={header[0],header[1],2'b00,data_credit[11:8]};",
    ),
    (
        "soc_pcie_buffered_flow_packets",
        ".local_init_done_i(local_init_done_o)",
        ".local_init_done_i(1'b1)",
    ),
    ("soc_pcie_buffered_flow_packets", ".COMPLETER_ONLY(1)", ".COMPLETER_ONLY(0)"),
    (
        "soc_pcie_buffered_flow_packets",
        ".packet_accepted_i(packet_accepted_o)",
        ".packet_accepted_i(packet_accepted_o || packet_duplicate_o)",
    ),
    (
        "soc_pcie_buffered_flow_packets",
        ".header_limit_i(rx_header_limit_o)",
        ".header_limit_i(24'h000303)",
    ),
    (
        "soc_pcie_buffered_flow_packets",
        ".initialized_i(peer_init1_done_o && local_init2_sent_o)",
        ".initialized_i(initialized_o)",
    ),
]


@pytest.mark.parametrize("top,before,after", MUTANTS)
def test_actual_port_suite_rejects_ownership_or_wire_fault(
    tmp_path, top, before, after
):
    if (
        not shutil.which("iverilog")
        or not (Path(sys.executable).parent / "cocotb-config").is_file()
    ):
        pytest.skip("Real Icarus and cocotb interpreter required")
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    for source in (ROOT / "hw/soc/rtl/pcie").glob("*.v"):
        shutil.copy2(source, rtl / source.name)
    target = rtl / (top + ".v")
    source = target.read_text()
    assert source.count(before) == 1
    target.write_text(source.replace(before, after))
    out = tmp_path / "run"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_pcie_rx_flow.py"),
            "--top",
            top,
            "--out",
            str(out),
            "--rtl-dir",
            str(rtl),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=180,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    (tmp_path / "mutation.log").write_text(completed.stdout)
    assert completed.returncode == 1, completed.stdout
    receipt = json.loads((out / "result.json").read_text())
    assert receipt["status"] == "FAIL"
    passed, failed, skipped = count_results([out / "results.xml"])
    assert passed + failed == (3 if top == "soc_pcie_fc_tx" else 5)
    assert failed > 0 and skipped == 0
    assert "AssertionError" in (out / "simulation.log").read_text()


@pytest.mark.parametrize(
    "options,message",
    [
        (["--native"], "requires explicit tools"),
        (["--native", "--rtl-dir", "."], "forbids mutated RTL"),
        (["--top", "soc_top"], "invalid choice"),
    ],
)
def test_runner_rejects_incomplete_or_unsafe_profile(tmp_path, options, message):
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_pcie_rx_flow.py"),
            "--out",
            str(tmp_path / "out"),
            *options,
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert completed.returncode == 2 and message in completed.stderr
    assert not (tmp_path / "out").exists()
