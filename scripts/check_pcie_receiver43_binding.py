#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check compact feedback LV receiver terminals and geometry against native LVS device identities.

This verifies a component model translation, not wire extraction or PHY compliance.
The checker derives its expected values from native records, independently of the
generator's binding manifest. It preserves finite body contacts and separate rails.
"""

import argparse
from collections import Counter
from decimal import Decimal
import json
import math
from pathlib import Path

from build_pcie_local_vco_hybrid_v6 import number, pin, require, statements

CENSUS = {"sg13_lv_nmos": 7, "sg13_lv_pmos": 5, "rppd": 6, "cap_cmim": 1, "ptap1": 19, "ntap1": 5}

ORDER = {
    "sg13_lv_nmos": ["D", "G", "S", "B"],
    "sg13_lv_pmos": ["D", "G", "S", "B"],
    "rppd": ["rppd_1", "rppd_2", "rppd_sub"],
    "cap_cmim": ["mim_top", "mim_btm"],
    "ptap1": ["TIE", "WELL"],
    "ntap1": ["TIE", "WELL"],
}
PORTS = {"cp", "cn", "clk", "cvdd", "avss", "sub"}



def native_geometry(value, name):
    """Round only binary-float noise on the pinned 1 nm layout grid.

    Lengths/perimeters have 0.001 um units; areas have 0.000001 um2 units.
    A change larger than two binary ULPs is rejected, not rounded away.
    """
    exact = Decimal(str(value))
    if name not in {"L", "W", "AS", "AD", "PS", "PD"}:
        return exact
    quantum = Decimal("0.000001" if name in {"AS", "AD"} else "0.001")
    rounded = exact.quantize(quantum)
    require(abs(exact - rounded) <= 2 * Decimal(str(math.ulp(float(value)))),
            "Native geometry is off the pinned layout grid")
    return rounded


def parameters(device, tech):
    model = device["model"]
    p = {k: native_geometry(v, k) for k, v in device["parameters"].items()}
    if model.startswith("sg13_lv_"):
        require(
            set(p) == {"L", "W", "AS", "AD", "PS", "PD", "rfmode"},
            "Native MOS parameter census",
        )
        return {
            k.lower(): v
            * (
                Decimal("1e-12")
                if k in ("AS", "AD")
                else Decimal(1)
                if k == "rfmode"
                else Decimal("1e-6")
            )
            for k, v in p.items()
        } | {"m": Decimal(1), "ng": Decimal(1)}
    if model == "rppd":
        require(
            set(p) == {"w", "l", "ps", "b", "m"} and p["b"] == 0 and p["m"] == 1,
            "Native resistor attributes",
        )
        return {
            k: v * (Decimal("1e-6") if k in ("w", "l", "ps") else 1)
            for k, v in p.items()
        } | {"sw_et": Decimal(1)}
    if model == "cap_cmim":
        require(
            set(p) == {"w", "l", "A", "P", "m"}
            and p["m"] == 1
            and p["A"] == p["w"] * p["l"]
            and p["P"] == 2 * (p["w"] + p["l"]),
            "Native capacitor geometry",
        )
        return {k: p[k] * Decimal("1e-6") for k in ("w", "l")}
    require(
        model in ("ptap1", "ntap1") and p == {"A": 4, "P": 8}, "Native contact geometry"
    )
    # Pinned PDK CbTapCalc, area/perimeter conductances in SI units.
    conductance = p["A"] * Decimal("1e-12") / number(tech[model + "_raspec"]) + p[
        "P"
    ] * Decimal("1e-6") / number(tech[model + "_rpspec"])
    return {"r": 1 / conductance, "w": Decimal("2e-6"), "l": Decimal("2e-6")}


def check(record, text, tech, native_ports):
    devices = record["devices"]
    require(Counter(d["model"] for d in devices) == CENSUS, "Native device census")
    require(
        [d["native_id"] for d in devices] == list(range(1, 44)), "Native identities"
    )
    rows = statements(text)
    require(
        rows[0] == [".subckt", "nssoc_receiver43_compact_v1", *native_ports]
        and len(native_ports) == 6
        and set(native_ports) == PORTS,
        "Public port identity/order",
    )
    require(
        rows[-1] == [".ends", "nssoc_receiver43_compact_v1"] and len(rows) == 45,
        "Exact compact device census",
    )
    mapping = {
        n: n if n in PORTS else "n_" + n.removeprefix("$")
        for d in devices
        for n in d["terminals"].values()
    }
    require(len(set(mapping.values())) == len(mapping), "Injective native net naming")
    for d, row in zip(devices, rows[1:-1], strict=True):
        order = ORDER[d["model"]]
        require(set(d["terminals"]) == set(order), "Named terminal census")
        expected = [
            f"XD{d['native_id']:04d}",
            *[mapping[d["terminals"][n]] for n in order],
            d["model"],
        ]
        require(row[: len(expected)] == expected, "Compact terminal identity/order")
        actual = {}
        for field in row[len(expected) :]:
            pair = field.split("=")
            require(
                len(pair) == 2 and pair[0].lower() not in actual,
                "Unique compact parameter",
            )
            actual[pair[0].lower()] = number(pair[1])
        require(actual == parameters(d, tech), "Compact physical parameter mismatch")
    return {
        "status": "PASS_NATIVE43_TERMINALS_AND_PARAMETERS",
        "devices": 43,
        "contacts": 24,
        "wire_parasitics_included": False,
        "serial_phy_complete": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--devices", type=Path, required=True)
    p.add_argument("--native", type=Path, required=True)
    p.add_argument("--compact", type=Path, required=True)
    p.add_argument("--technology", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    record = json.loads(args.devices.read_text())
    for name, expected in record["inputs"].items():
        require(pin(name)["sha256"] == expected, "Native export input changed: " + name)
    require(str(args.native.resolve()) in record["inputs"], "Bound native extraction")
    native_ports = statements(args.native.read_text())[0][2:]
    result = check(
        record,
        args.compact.read_text(),
        json.loads(args.technology.read_text())["techParams"],
        native_ports,
    )
    result["inputs"] = {
        str(path.resolve()): pin(path)
        for path in [
            args.devices,
            args.native,
            args.compact,
            args.technology,
            Path(__file__),
        ]
    }
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
