# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from audit_supply_checkpoint import validate_plan


def fixture():
    windows = [
        dict(
            instance="p0",
            master="PAD",
            pin=pin,
            layer="Metal1",
            gds_layer=8,
            box_nm=[0, i * 40, 20, i * 40 + 20],
        )
        for i, pin in enumerate(["vdd", "vss", "iovdd", "iovss"])
    ]
    plan = dict(
        status="PASS_IO_PORT_WINDOW_COVERAGE_ONLY",
        input_sha256={"chip.gds": "a" * 64},
        io_instances=1,
        io_masters={"PAD": 1},
        port_windows=4,
        windows=windows,
        windows_by_rail={w["pin"]: 1 for w in windows},
        windows_by_layer={"Metal1": 4},
    )
    manifest = dict(
        input_sha256={"moved/chip.gds": "a" * 64},
        dbu=0.001,
        floating_subcircuits_retained=True,
    )
    return plan, manifest


def test_same_gds_all_declared_windows():
    validate_plan(*fixture())


@pytest.mark.parametrize(
    "defect",
    [
        "gds",
        "units",
        "floating",
        "count",
        "missing_rail",
        "layer",
        "box",
        "master",
        "instances",
    ],
)
def test_bad_provenance_or_incomplete_inventory_rejected(defect):
    plan, manifest = copy.deepcopy(fixture())
    if defect == "gds":
        manifest["input_sha256"]["moved/chip.gds"] = "b" * 64
    elif defect == "units":
        manifest["dbu"] = 1
    elif defect == "floating":
        manifest["floating_subcircuits_retained"] = False
    elif defect == "count":
        plan["port_windows"] += 1
    elif defect == "missing_rail":
        del plan["windows_by_rail"]["vdd"]
    elif defect == "layer":
        plan["windows"][0]["gds_layer"] = 999
    elif defect == "box":
        plan["windows"][0]["box_nm"] = [0, 0, 0, 1]
    elif defect == "master":
        plan["windows"][0]["master"] = "DIFFERENT"
    elif defect == "instances":
        plan["io_instances"] += 1
    with pytest.raises(ValueError):
        validate_plan(plan, manifest)
