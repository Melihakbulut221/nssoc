# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real CPU/packet regressions reject wrong decode and ignored byte enables."""

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "name,old,new",
    [
        ("wrong_slot", "{SOC_APBSLOT_GPIO,ep_paddr}", "{SOC_APBSLOT_UART0,ep_paddr}"),
        (
            "partial_write",
            "wire ep_bad_strobe=ep_pwrite && ep_pstrb!=4'hf;",
            "wire ep_bad_strobe=1'b0;",
        ),
    ],
)
def test_actual_soc_counterexample(tmp_path, name, old, new):
    iverilog = shutil.which("iverilog")
    if not iverilog or not (ROOT / "hw/soc/genp/ibex_top.v").is_file():
        pytest.skip(
            "Prepared SoC and Icarus required; dedicated PCIe workflow runs both"
        )
    rtl = (ROOT / "hw/soc/rtl/soc_top.v").read_text()
    assert rtl.count(old) == 1
    mutant = tmp_path / (name + ".v")
    mutant.write_text(rtl.replace(old, new))
    out = tmp_path / "run"
    command = [
        sys.executable,
        str(ROOT / "scripts/check_pcie_soc.py"),
        "--out",
        str(out),
        "--iverilog-dir",
        str(Path(iverilog).parent),
        "--top-override",
        str(mutant),
    ]
    with (tmp_path / "command.log").open("w") as log:
        result = subprocess.run(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=120,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
    record = json.loads((out / "result.json").read_text())
    assert result.returncode == 1 and record["status"] == "FAIL"
    assert record["tests"]["failed"] > 0 and record["tests"]["skipped"] == 0
    assert "AssertionError" in (out / "run.log").read_text()
