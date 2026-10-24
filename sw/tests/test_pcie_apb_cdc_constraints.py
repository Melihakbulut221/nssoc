# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bound actual mapped register identities; reject clock and synchronizer drift."""

import gzip
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "cdc_constraints", ROOT / "scripts/pcie_apb_cdc_constraints.py"
)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def mapped():
    path = ROOT / "sw/tests/fixtures/pcie_apb_cdc/mapped.json.gz"
    return json.loads(gzip.decompress(path.read_bytes()))["modules"]["soc_pcie_apb_cdc"]


def test_actual_mapped_pin_inventory():
    sdc, pins = CHECK.constraints(mapped())
    assert len(pins["request"]) == len(pins["destination"]) == 49
    assert len(pins["response"]) == len(pins["source"]) == 33
    assert "set_max_delay 16.000000" in sdc and "set_max_delay 3.200000" in sdc
    assert "set_clock_groups" not in sdc
    assert sdc.count("set_false_path -to") == 1
    assert sdc.count("set_false_path -hold") == 2
    assert len(pins["request_sync"]) == len(pins["acknowledgement_sync"]) == 2


@pytest.mark.parametrize(
    "fault",
    ["missing_ff", "wrong_clock", "broken_sync", "aliased_payload", "wrong_cell"],
)
def test_mapped_faults_rejected(fault):
    module = mapped()
    _, pins = CHECK.constraints(module)
    cell = pins["request"][0]["cell"]
    if fault == "missing_ff":
        del module["cells"][cell]
    elif fault == "wrong_clock":
        module["cells"][cell]["connections"]["CLK"] = module["ports"][
            "destination_clk_i"
        ]["bits"]
    elif fault == "broken_sync":
        second = pins["request_sync"][1]["cell"]
        module["cells"][second]["connections"]["D"] = ["0"]
    elif fault == "aliased_payload":
        module["netnames"]["request_payload"]["bits"][1] = module["netnames"][
            "request_payload"
        ]["bits"][0]
    else:
        module["cells"][cell]["type"] = "sg13g2_buf_1"
    with pytest.raises(ValueError):
        CHECK.constraints(module)
