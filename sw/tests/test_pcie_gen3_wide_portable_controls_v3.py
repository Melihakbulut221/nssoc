# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Frozen wide oracle/faults through the corrected explicit runtime-v3 recipe."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "sw/tests/test_pcie_gen3_continuous_rx_wide.py"
assert (
    hashlib.sha256(OLD.read_bytes()).hexdigest()
    == "957fe99d513e7f3f0672fcbaa5ad6089c6cca3e44baff3c2a6a3b63894702c2e"
)
spec = importlib.util.spec_from_file_location("frozen_wide_fault_inventory", OLD)
frozen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frozen)
# The original source file, FAULTS tuple and bench remain byte-identical.
FAULTS = frozen.FAULTS
MODULES = frozen.MODULES


def run(tmp_path, maximum=150, rtl=None, case=None):
    tool = shutil.which("iverilog")
    assert tool and shutil.which("vvp"), "Actual Icarus required; never skip controls"
    out = tmp_path / "capture"
    command = [
        sys.executable,
        str(ROOT / "scripts/check_pcie_gen3_continuous_rx_wide_native_v3.py"),
        "--out",
        str(out),
        "--max-bytes",
        str(maximum),
        "--iverilog-dir",
        str(Path(tool).parent),
    ]
    if rtl:
        command += ["--rtl-dir", str(rtl)]
    if case:
        command += ["--test", case]
    with (tmp_path / "launch.log").open("w") as log:
        result = subprocess.run(
            command,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    record = json.loads((out / "result.json").read_text())
    cases = list(ET.parse(out / "results.xml").getroot().iter("testcase"))
    assert len(cases) == 9 and not any(c.find("error") is not None for c in cases)
    selected = [c for c in cases if c.find("skipped") is None]
    assert [c.attrib["name"] for c in selected] == (
        [case] if case else [c.attrib["name"] for c in cases]
    )
    assert record["mapping_strategy"] == "explicit_no_fsm_runtime_v3"
    assert record["mode"] == "rtl"
    return result, record, selected, out


@pytest.mark.parametrize("maximum", [150, 4118])
def test_actual_v3_wide_full_positive_profiles(tmp_path, maximum):
    result, record, cases, _ = run(tmp_path, maximum)
    assert result.returncode == 0, record
    assert record["status"] == "PASS_PORT_ONLY_PCIE_GEN3_WIDE_FIXED_DATA_RX"
    assert record["tests"] == dict(passed=9, failed=0, skipped=0)
    assert all(c.find("failure") is None for c in cases)


@pytest.mark.parametrize(
    "name,module,before,after,count,case", FAULTS, ids=[f[0] for f in FAULTS]
)
def test_actual_v3_wide_frozen_fault_rejected(
    tmp_path, name, module, before, after, count, case
):
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    for m in MODULES:
        shutil.copyfile(ROOT / "hw/soc/rtl/pcie" / (m + ".v"), rtl / (m + ".v"))
    path = rtl / (module + ".v")
    original = path.read_text()
    assert original.count(before) == count
    path.write_text(original.replace(before, after))
    result, record, selected, out = run(tmp_path, rtl=rtl, case=case)
    assert result.returncode != 0 and record["status"] == "FAIL"
    assert len(selected) == 1 and selected[0].find("failure") is not None
    assert "AssertionError" in (out / "simulation.log").read_text(), (
        "Tool/compile errors are not functional rejection"
    )
