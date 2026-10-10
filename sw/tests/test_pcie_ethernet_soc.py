# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject actual main-chip Ethernet corruption and a missing link-reset CDC wire."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "name,old,new",
    [
        ("corrupt_gmii", ".rxd_i(eth_rxd_i),", ".rxd_i(eth_rxd_i ^ 8'h01),"),
        (
            "stale_cdc",
            ".reset_ni(rst_sys_n && pcie_link_up_i && !pcie_retrain_done_i),",
            ".reset_ni(rst_sys_n),",
        ),
    ],
)
def test_real_main_chip_fault(tmp_path, name, old, new):
    compiler = shutil.which("iverilog")
    assert compiler, "Dedicated integration validation requires Icarus"
    source = (ROOT / "hw/soc/rtl/soc_top.v").read_text()
    assert source.count(old) == 1
    mutant = tmp_path / (name + ".v")
    mutant.write_text(source.replace(old, new))
    out = tmp_path / "capture"
    with (tmp_path / "driver.log").open("w") as log:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/check_pcie_ethernet_soc.py"),
                "--out",
                str(out),
                "--iverilog-dir",
                str(Path(compiler).parent),
                "--async-pcie",
                "--top-override",
                str(mutant),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
    record = json.loads((out / "result.json").read_text())
    assert result.returncode == 1 and record["status"] == "FAIL"
    assert record["tests"]["failed"] > 0 and record["tests"]["skipped"] == 0
    assert record["unchanged"] and record["runtime_unchanged"]
    log = (out / "run.log").read_text()
    assert "AssertionError" in log
    if name == "stale_cdc":
        assert "Stale CDC write survived link loss" in log
