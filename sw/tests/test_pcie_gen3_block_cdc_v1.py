# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual async port tests and functional RTL counterexamples; no CDC signoff."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_pcie_gen3_block_cdc_v1.py"
RTL = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_block_cdc_v1.v"


def run(tmp_path, *, rtl=None, case=None, depth=32):
    local = ROOT / "hw/soc/tools/oss-cad-suite/bin"
    found = shutil.which("iverilog")
    tools = local if (local / "iverilog").is_file() else Path(found).parent if found else None
    assert tools is not None, "Actual Icarus required; no skipped simulation"
    command = [sys.executable, str(SCRIPT), "--out", str(tmp_path / "capture"),
               "--iverilog-dir", str(tools), "--depth", str(depth)]
    if rtl:
        command += ["--rtl", str(rtl)]
    if case:
        command += ["--test", case]
    with (tmp_path / "producer.log").open("w") as log:
        done = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                              env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    record = json.loads((tmp_path / "capture/result.json").read_text())
    return done.returncode, record, (tmp_path / "capture/simulation.log").read_text()


@pytest.mark.parametrize("depth", [4, 8, 32])
def test_actual_async_all_cases_and_declared_capacity(tmp_path, depth):
    code, result, log = run(tmp_path, depth=depth)
    assert code == 0, log
    assert result["status"] == "PASS_ACTUAL_BLOCK_CDC_RTL"
    assert result["tests"] == {"passed": 7, "failed": 0, "skipped": 0}
    assert result["ram_entries"] == depth and result["prefetch_entries"] == 2


FAULTS = {
    "upper_bits_lost": (
        "wr_length_code_i,wr_block_i}", "wr_length_code_i,{64'd0,wr_block_i[129:0]}}",
        "asynchronous_metadata_and_drift", "Complete block/metadata ordering mismatch"),
    "length_lost": (
        "wr_skp_i,wr_length_code_i,wr_block_i", "wr_skp_i,3'd2,wr_block_i",
        "asynchronous_metadata_and_drift", "Complete block/metadata ordering mismatch"),
    "metadata_lost": (
        "{wr_realign_i,wr_eieos_i,wr_skp_i,", "{wr_realign_i,wr_eieos_i,1'b0,",
        "asynchronous_metadata_and_drift", "Complete block/metadata ordering mismatch"),
    "ignores_downstream_stall": (
        ".m_axis_tready(rd_running_o && rd_ready_i)", ".m_axis_tready(rd_running_o)",
        "held_output_and_bounded_pressure", "Held complete-block output changed"),
    "overflow_not_sticky": (
        "wr_fault_o <= 1'b1;\n                wr_overflow_o", "wr_fault_o <= 1'b0;\n                wr_overflow_o",
        "exact_ram_prefetch_capacity_overflow_and_restart", "Bounded digital scenario did not complete"),
    "fault_does_not_mask_output": (
        "wr_up_in_rd[1] && !rd_fault_o", "wr_up_in_rd[1]",
        "alignment_loss_and_illegal_length_fail_closed", "assert not int(d.rd_valid_o.value)"),
    "one_domain_reset_ignored": (
        "!por_ni || wr_reset_i || rd_reset_i", "!por_ni || wr_reset_i",
        "either_domain_reset_with_held_output", "assert not int(d.rd_valid_o.value)"),
    "peer_restart_barrier_omitted": (
        "rd_boot_q[3] && wr_up_in_rd[1] &&", "rd_boot_q[3] &&",
        "stopped_clock_reset_and_restart", "Stopped domain escaped restart barrier"),
    "alignment_loss_ignored": (
        "if (wr_loss_i || (wr_valid_i && !legal_length))", "if ((wr_valid_i && !legal_length))",
        "alignment_loss_and_illegal_length_fail_closed", "Bounded digital scenario did not complete"),
    "illegal_length_accepted": (
        "wr_length_code_i <= 3'd4", "wr_length_code_i <= 3'd7",
        "alignment_loss_and_illegal_length_fail_closed", "item[1] <= 4"),
}


@pytest.mark.parametrize("fault", list(FAULTS))
def test_actual_connection_and_protocol_fault_rejected(tmp_path, fault):
    old, new, case, diagnostic = FAULTS[fault]
    text = RTL.read_text()
    assert text.count(old) == 1
    mutant = tmp_path / "mutant.v"
    mutant.write_text(text.replace(old, new))
    code, result, log = run(tmp_path, rtl=mutant, case=case)
    assert code != 0 and result["status"] == "FAIL", fault
    assert "Running on Icarus Verilog" in log and "TESTS=1" in log, log
    assert diagnostic in log, log


@pytest.mark.parametrize("depth", [1, 3])
def test_invalid_ram_depth_is_actual_elaboration_failure(tmp_path, depth):
    code, result, log = run(tmp_path, depth=depth)
    assert code != 0 and result["status"] == "FAIL"
    assert "ERROR_block_cdc_DEPTH_must_be_power_of_two_ge_4" in log
    assert "Running tests" not in log


def test_selected_positive_preserves_exact_case_identity(tmp_path):
    code, result, log = run(tmp_path, case="held_output_and_bounded_pressure")
    assert code == 0, log
    assert result["status"] == "PASS_ACTUAL_BLOCK_CDC_RTL"
    assert result["tests"] == {"passed": 1, "failed": 0, "skipped": 6}
    assert result["exact_test"] == "held_output_and_bounded_pressure"
