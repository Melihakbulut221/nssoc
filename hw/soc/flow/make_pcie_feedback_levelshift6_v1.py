#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate a six-device feedback level shifter with explicit well contacts.

Reuses the frozen native pump routing generator only within this process.
This standalone macro has no inherited PLL, wire extraction or PHY acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import make_pcie_pump_filter13_v1 as base

TOP = "nssoc_feedback_levelshift6_drive8_layout_v1"
PORTS = ["d", "db", "q", "qb", "avdd", "avss", "sub"]
SOURCES = {"pll_feedback_levelshift_hv_drive8_v1.spice": "43f784920c3d9c8a281e979954d33f5aef0fccdc6209966a204c31c749480eae"}


def use_direction(name):
    if name == "avdd":
        return "POWER", "INOUT"
    if name in ("avss", "sub"):
        return "GROUND", "INOUT"
    return "SIGNAL", "OUTPUT" if name in ("q", "qb") else "INPUT"


def devices(texts):
    if set(texts) != set(SOURCES) or any(
        hashlib.sha256(texts[n].encode()).hexdigest() != h for n, h in SOURCES.items()
    ):
        raise ValueError("Frozen six-device source differs")
    rows, wires = base.expand(base.definitions(texts),
                              ["nssoc_pll_feedback_levelshift_hv_drive8_v1", "xlevel", PORTS])
    if len(rows) != 6 or wires:
        raise ValueError("Level-shifter device census differs")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    wrapper = Path(__file__).resolve()
    before = base.pin(wrapper)
    changes = dict(TOP=TOP, PORTS=PORTS, SOURCES=SOURCES,
                   devices=devices, use_direction=use_direction)
    original = {k: getattr(base, k) for k in changes}
    try:
        for k, v in changes.items():
            setattr(base, k, v)
        base.build(args.pdk, args.out)
    finally:
        for k, v in original.items():
            setattr(base, k, v)
    path = args.out.resolve() / "result.json"
    result = json.loads(path.read_text())
    assert base.pin(wrapper) == before
    result["inputs"][str(wrapper)] = before
    result["substrate_contacts"] = 6
    result["well_contacts"] = 3
    result["closed_loop_accepted"] = False
    path.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
