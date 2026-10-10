# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual variable_tx port counterexamples to feedback, seed, control masks, stalls and flush."""

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from cocotb_results import count_results  # noqa: E402
from check_pcie_gen3_variable_tx import execute_command  # noqa: E402


def test_optional_watchdog_terminates_descendant_writer(tmp_path):
    marker = tmp_path / "late-child-output"
    code = (
        "import subprocess,sys,time; "
        "subprocess.Popen([sys.executable,'-c',"
        + repr(
            "import time,pathlib; time.sleep(.25); pathlib.Path("
            + repr(str(marker))
            + ").write_text('late')"
        )
        + "]); time.sleep(2)"
    )
    with pytest.raises(subprocess.TimeoutExpired):
        execute_command(
            [sys.executable, "-c", code], tmp_path / "watchdog.log", None, 0.1
        )
    time.sleep(0.3)
    assert not marker.exists(), "Descendant wrote after the rejected execution"


def test_default_waits_for_child_completion(tmp_path):
    code = "import time; time.sleep(.1); print('NATIVE_DONE')"
    path = tmp_path / "complete.log"
    assert execute_command([sys.executable, "-c", code], path, None, None) == 0
    assert path.read_text().strip() == "NATIVE_DONE"


def test_watchdog_kills_ignoring_child_after_leader_exits(tmp_path):
    ready, late = tmp_path / "ready", tmp_path / "late"
    child = (
        "import signal,time,pathlib; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        + "pathlib.Path("
        + repr(str(ready))
        + ").write_text('ready'); "
        + "time.sleep(.8); pathlib.Path("
        + repr(str(late))
        + ").write_text('late')"
    )
    parent = (
        "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',"
        + repr(child)
        + "]); time.sleep(2)"
    )
    with pytest.raises(subprocess.TimeoutExpired):
        execute_command(
            [sys.executable, "-c", parent], tmp_path / "ignoring-child.log", None, 0.4
        )
    assert ready.is_file(), "The real descendant must have installed its signal handler"
    time.sleep(0.5)
    assert not late.exists(), "Exited leader must not hide a surviving writer"


MUTANTS = [
    ("block_bits=9'd194", "block_bits=9'd162"),
    ("&mask", "|mask"),
    ("count>=9'd32", "count>=9'd30"),
    ("10'd256", "10'd280"),
    ("length_code_i<=3'd4", "length_code_i<=3'd7"),
    ("else if(flush_i)", "else if(1'b0)"),
    ("bits[lane]>>32", "bits[lane]>>31"),
    ("lane*192+:192", "0+:192"),
]


@pytest.mark.parametrize("before,after", MUTANTS)
def test_real_port_counterexample_rejects_variable_tx_fault(tmp_path, before, after):
    if (
        not shutil.which("iverilog")
        or not (Path(sys.executable).parent / "cocotb-config").is_file()
    ):
        pytest.skip("Real Icarus/cocotb required")
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    source = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_variable_tx.v"
    original = source.read_text()
    assert original.count(before) == 1
    (rtl / source.name).write_text(original.replace(before, after))
    out = tmp_path / "run"
    run = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_pcie_gen3_variable_tx.py"),
            "--out",
            str(out),
            "--rtl-dir",
            str(rtl),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    (tmp_path / "mutation.log").write_text(run.stdout + run.stderr)
    assert run.returncode == 1
    record = json.loads((out / "result.json").read_text())
    assert record["status"] == "FAIL"
    passed, failed, skipped = count_results([out / "results.xml"])
    assert passed + failed == 4 and failed > 0 and skipped == 0
    assert "AssertionError" in (out / "simulation.log").read_text()
