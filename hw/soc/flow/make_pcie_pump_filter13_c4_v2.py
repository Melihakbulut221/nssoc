#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate an isolated four-times-area pump capacitor layout candidate.

Uses the unchanged native placement/routing generator in this process only.
The alternative has the same macro boundary; do not load both same-named
variants into one physical library. Native checks and feedback remain required.
"""
import argparse
import json
from pathlib import Path
import make_pcie_pump_filter13_v1 as base

SOURCES = {
    "pll_pump_filter_hv_c4_v2.spice": "4c33a926a9d388deee496a9a3cb761101759e667867ab557636cfd5a5ef27794",
    "pll_pfd_charge_pump_hv_v1.spice": base.SOURCES["pll_pfd_charge_pump_hv_v1.spice"],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    wrapper = Path(__file__).resolve()
    before = base.pin(wrapper)
    original_sources = base.SOURCES
    try:
        base.SOURCES = SOURCES
        base.build(args.pdk, args.out)
    finally:
        base.SOURCES = original_sources
    result_path = args.out.resolve() / "result.json"
    result = json.loads(result_path.read_text())
    assert base.pin(wrapper) == before
    result["inputs"][str(wrapper)] = before
    result["filter_capacitor_um"] = [20, 20]
    result["filter_capacitor_area_ratio"] = 4
    result["closed_loop_accepted"] = False
    result_path.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
