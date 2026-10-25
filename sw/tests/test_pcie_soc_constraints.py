# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Mutate actual mapped whole-chip register connections, not a synthetic graph."""

import gzip
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from pcie_soc_constraints import bind, render


def fixture():
    return json.loads(gzip.decompress((ROOT / "sw/tests/fixtures/pcie_apb_cdc/soc-registers.json.gz").read_bytes()))


def test_actual_four_clock_register_inventory():
    m = fixture()
    sdc, inv = render(m, (ROOT / "hw/soc/sta/ibex.sdc.in").read_text())
    assert {k: len(v) for k, v in inv.items()} == dict(
        request=49, response=33, destination=49, source=33,
        request_sync=2, acknowledgement_sync=2)
    assert "set_clock_groups" not in sdc
    assert "set_max_delay -ignore_clock_latency 16.0 -from $packet_request_launch" in sdc
    assert "set_max_delay -ignore_clock_latency 3.2 -from $packet_response_launch" in sdc


@pytest.mark.parametrize("fault", ["clock_alias", "wrong_launch_clock", "broken_sync", "missing_driver", "aliased_payload"])
def test_actual_chip_pin_faults_are_rejected(fault):
    m = fixture()
    inv = bind(m)
    if fault == "clock_alias":
        m["ports"]["pcie_clk_i"]["bits"] = m["ports"]["clk_i"]["bits"]
    elif fault == "wrong_launch_clock":
        m["cells"][inv["request"][0]["cell"]]["connections"]["CLK"] = m["ports"]["clk_i"]["bits"]
    elif fault == "broken_sync":
        m["cells"][inv["request_sync"][1]["cell"]]["connections"]["D"] = ["0"]
    elif fault == "missing_driver":
        del m["cells"][inv["response"][0]["cell"]]
    else:
        bits = m["netnames"]["u_pcie_cdc.request_payload"]["bits"]
        bits[1] = bits[0]
    with pytest.raises(ValueError):
        bind(m)


def test_legacy_sta_rejects_packet_clock_before_loading_tools(tmp_path):
    (tmp_path / "soc_top.sta.v").write_text("module soc_top(pcie_clk_i);\n  input pcie_clk_i;\nendmodule\n")
    result = subprocess.run(["bash", str(ROOT / "hw/soc/flow/sta_soc_top.sh"), "20", str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 2
    assert "legacy single-clock STA refused" in result.stderr


def test_invalid_packet_synthesis_profile_fails_before_output_creation(tmp_path):
    import os

    env = dict(os.environ, SOC_PCIE_PROFILE="serial-phy-is-not-implemented")
    out = tmp_path / "must-not-exist"
    result = subprocess.run(["bash", str(ROOT / "hw/soc/flow/syn_soc_top.sh"), "4", str(out)], env=env, capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 2
    assert "SOC_PCIE_PROFILE must be" in result.stderr
    assert not out.exists()
