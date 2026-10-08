# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual HDL clock-ratio, stall, reset, payload and duplicate-access checks."""

from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie/soc_pcie_apb_cdc.v"
BENCH = ROOT / "hw/soc/tb/tb_pcie_apb_cdc.v"


def run(tmp_path, source, sh=2, dh=10):
    rtl = tmp_path / "bridge.v"
    rtl.write_text(source)
    binary = tmp_path / "sim.vvp"
    build = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb_pcie_apb_cdc",
            f"-Ptb_pcie_apb_cdc.SOURCE_HALF={sh}",
            f"-Ptb_pcie_apb_cdc.DESTINATION_HALF={dh}",
            "-o",
            str(binary),
            str(rtl),
            str(BENCH),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    (tmp_path / "compile.log").write_text(build.stdout + build.stderr)
    result = subprocess.run(
        ["vvp", str(binary)], capture_output=True, text=True, timeout=60
    )
    (tmp_path / "run.log").write_text(result.stdout + result.stderr)
    return result


@pytest.mark.parametrize("sh,dh", [(2, 10), (11, 3), (5, 7)])
def test_real_clock_ratios(tmp_path, sh, dh):
    result = run(tmp_path, RTL.read_text(), sh, dh)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS_PCIE_APB_CDC transfers=97" in result.stdout


@pytest.mark.parametrize(
    "old,new",
    [
        ("s_pstrb_i};", "4'b0};"),
        (
            "response_payload<={m_pslverr_i,m_prdata_i};",
            "response_payload<={1'b0,m_prdata_i};",
        ),
        ("&& !served)", ")"),
        ("request<=0;request_payload<=0;", "request<=1;request_payload<=0;"),
    ],
)
def test_actual_rtl_fault_rejected(tmp_path, old, new):
    source = RTL.read_text()
    assert source.count(old) == 1
    result = run(tmp_path, source.replace(old, new))
    assert result.returncode != 0 and "FATAL" in result.stdout, result.stdout
