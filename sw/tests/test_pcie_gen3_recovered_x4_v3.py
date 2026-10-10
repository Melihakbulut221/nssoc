# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Raw x4 serialized inputs, actual clock crossings, observable wiring faults."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_pcie_gen3_recovered_x4_v3.py"
RTL = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_recovered_x4_v3.v"


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
    result = json.loads((tmp_path / "capture/result.json").read_text())
    return done.returncode, result, (tmp_path / "capture/simulation.log").read_text()


def test_four_recovered_clocks_full_raw_port_suite(tmp_path):
    code, result, log = run(tmp_path)
    assert code == 0, log
    assert result["status"] == "PASS_ACTUAL_RECOVERED_X4_RTL"
    assert result["tests"] == {"passed": 11, "failed": 0, "skipped": 0}


PHASE_CASE = "independent_clocks_all_bit_phases_and_skp_lengths"
FAULTS = {
    "reversed_raw_lanes": ("raw_i[lane*32 +: 32]", "raw_i[(3-lane)*32 +: 32]", PHASE_CASE, "Unexpected raw x4 epoch fault"),
    "truncated_blocks": (".wr_block_i(block_data)", ".wr_block_i({64'd0,block_data[129:0]})", PHASE_CASE, "Unexpected raw x4 epoch fault"),
    "lost_skp_length": (".wr_length_code_i(block_length)", ".wr_length_code_i(3'd2)", PHASE_CASE, "Unexpected raw x4 epoch fault"),
    "lost_skp_metadata": (".wr_skp_i(skp)", ".wr_skp_i(1'b0)", PHASE_CASE, "Unexpected raw x4 epoch fault"),
    "ignored_cohort_ready": (".rd_ready_i(front_ready && raw_ready[lane])", ".rd_ready_i(front_ready)", "independent_skp_and_atomic_data_stalls", "Unexpected SKP parity or LFSR diagnostic"),
    "lost_raw_loss": (".wr_loss_i(loss)", ".wr_loss_i(1'b0)", "raw_loss_aborts_common_epoch_and_reset_recovers", "Bounded raw x4 deskew scenario did not complete"),
    "lost_force": (".force_realign_i(force_realign_i[lane])", ".force_realign_i(1'b0)", "forced_realign_aborts_the_locked_epoch", "Bounded raw x4 deskew scenario did not complete"),
    "early_arm_accepted": ("front_fault || (arm_i && !front_ready)", "front_fault", "early_arm_fails_and_clean_reset_recovers", "Bounded raw x4 deskew scenario did not complete"),
    "some_lanes_ready": ("(&common_running)", "(|common_running)", "stopped_recovered_clock_prevents_cohort_start", "AssertionError"),
    "wrong_logical_lane_seed": (".LANE_ID(lane)", ".LANE_ID(0)", PHASE_CASE, "Raw serialized DATA ordinal/lane mismatch"),
    "parity_retrains_epoch": ("(|decode_fault)", "((|decode_fault) || (|lane_error_o))", "parity_error_reports_lane_without_retrain", "Unexpected raw x4 epoch fault"),
    "reseed_on_sds": (".flush_i(1'b0)", ".flush_i(stream_start_o)", PHASE_CASE, "Unexpected raw x4 epoch fault"),
}


@pytest.mark.parametrize("fault", list(FAULTS))
def test_actual_x4_deskew_wire_fault_is_rejected(tmp_path, fault):
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
def test_invalid_per_lane_capacity_fails_elaboration(tmp_path, depth):
    code, result, log = run(tmp_path, depth=depth)
    assert code != 0 and result["status"] == "FAIL"
    assert "ERROR_block_cdc_DEPTH_must_be_power_of_two_ge_4" in log
    assert "Running tests" not in log
