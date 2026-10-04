# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Standalone Make dispatch must preserve real checker failures and fresh XML."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("mode", ["success", "failure_with_xml", "missing_xml"])
def test_standalone_checker_exit_and_fresh_xml(tmp_path, mode):
    bench = tmp_path / "hw/soc/tb/cocotb"
    bench.mkdir(parents=True)
    shutil.copyfile(ROOT / "hw/soc/tb/cocotb/Makefile.soc_pcie_soc", bench / "Makefile.soc_pcie_soc")
    generated = tmp_path / "hw/soc/gen"
    generated.mkdir()
    for name in ("ibex_top.v", "interfaces.bundle.vh"):
        (generated / name).write_text("// Preparation already present for dispatch-only control.\n")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    # This is a subprocess/Make contract control, not an HDL success claim.
    (scripts / "check_pcie_soc.py").write_text(
        "import argparse,pathlib,sys\n"
        "p=argparse.ArgumentParser();p.add_argument('--out');p.add_argument('--iverilog-dir');a=p.parse_args()\n"
        "d=pathlib.Path(a.out);assert not d.exists();d.mkdir()\n"
        + ("(d/'results.xml').write_text('<testsuites><testcase name=\"fresh\"/></testsuites>')\n"
           if mode != "missing_xml" else "")
        + f"sys.exit({0 if mode == 'success' else 1})\n"
    )
    binary = tmp_path / "bin"
    binary.mkdir()
    (binary / "iverilog").write_text("#!/bin/sh\nexit 90\n")
    (binary / "iverilog").chmod(0o755)
    output = bench / "results_soc_pcie_soc.xml"
    output.write_text('<testsuites><testcase name="stale"/></testsuites>')
    process = subprocess.run(
        ["make", "-f", "Makefile.soc_pcie_soc", f"SOC_PCIE_PYTHON={sys.executable}"],
        cwd=bench,
        env={**os.environ, "PATH": str(binary) + os.pathsep + os.environ["PATH"]},
        capture_output=True, text=True, timeout=20,
    )
    assert (process.returncode == 0) == (mode == "success"), process.stdout + process.stderr
    assert "stale" not in (output.read_text() if output.exists() else "")
    if mode == "failure_with_xml":
        assert output.is_file() and "fresh" in output.read_text()
    if mode == "missing_xml":
        assert not output.exists()


def test_partial_prepared_invocation_is_rejected(tmp_path):
    process = subprocess.run(
        ["make", "-f", str(ROOT / "hw/soc/tb/cocotb/Makefile.soc_pcie_soc"),
         "PCIE_ROOT=/incomplete/prepared/fixture"],
        cwd=tmp_path, capture_output=True, text=True, timeout=10,
    )
    assert process.returncode != 0
    assert "Prepared invocation requires PCIE_ROM" in process.stderr
