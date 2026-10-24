# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""An initial solver retry cannot conceal an incomplete or failed transient."""
import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    "ngspice_completion", Path(__file__).resolve().parents[2]
    / "hw/soc/flow/check_ngspice_transient.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

WARNING = "Warning: singular matrix:  check node 0\n"
RECOVERY = ("Note: Starting dynamic gmin stepping\n"
            "Note: Dynamic gmin stepping completed\n")
TRANSIENT = ("Initial Transient Solution\nNode Voltage\nvdd 0\n"
             "Reference value : 1e-9\nNo. of Data Rows : 12\nngspice-42 done\n")


@pytest.mark.parametrize("prefix", ["", RECOVERY, WARNING + RECOVERY])
def test_completed_transient_retains_recovery_record(prefix):
    result = gate.check(prefix + TRANSIENT, 0, 12)
    assert result["recovered_startup_warnings"] == ([WARNING.strip()] if WARNING in prefix else [])
    assert not result["timing_accepted"]


@pytest.mark.parametrize("text", [
    WARNING + TRANSIENT,
    WARNING + RECOVERY.replace("completed", "failed") + TRANSIENT,
    WARNING + RECOVERY.replace("Note: Starting dynamic gmin stepping\n", "") + TRANSIENT,
    RECOVERY + TRANSIENT.replace("Reference value", WARNING + "Reference value"),
    WARNING * 2 + RECOVERY + TRANSIENT,
    RECOVERY * 2 + TRANSIENT,
    "Warning: model outside valid range\n" + TRANSIENT,
    TRANSIENT.replace("ngspice-42 done", ""),
    TRANSIENT.replace("No. of Data Rows : 12", "No. of Data Rows : 0"),
    TRANSIENT.replace("No. of Data Rows : 12", "No. of Data Rows : 12\nNo. of Data Rows : 12"),
    TRANSIENT.replace("Initial Transient Solution", ""),
    TRANSIENT.replace("Reference value", "Error: timestep too small\nReference value"),
    TRANSIENT + "Fatal: failed to write waveform\n",
    TRANSIENT.replace("ngspice-42 done", "Reference value : 2e-9\nngspice-42 done"),
])
def test_incomplete_failed_or_unexpected_diagnostics_rejected(text):
    with pytest.raises(ValueError):
        gate.check(text, 0, 12)


@pytest.mark.parametrize("code,rows", [(-15, 12), (1, 12), (124, 12), (0, 11),
                                      (0, True), (0, 0), (0, 12.0)])
def test_process_and_waveform_count_must_match(code, rows):
    with pytest.raises(ValueError):
        gate.check(TRANSIENT, code, rows)
