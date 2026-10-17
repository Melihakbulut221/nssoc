#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Build an isolated pump/filter candidate with a longer upper bias resistor.

The native PCell geometry and reference both use RHI L=140 um, W=1 um.
All other core devices and connections retain the baseline values. This is
a hypothesis for the observed low VCO frequency, not a loop or PHY approval.
"""
import argparse
import json
from pathlib import Path

import make_pcie_pump_filter13_v1 as base

TOP = "nssoc_pump_filter13_rhi140_v1"
SOURCE = "pll_pump_filter_hv_rhi140_v1.spice"
SOURCE_SHA = "74ff41874333ea58362338efb9f81fdf5b8d9f6e601e7cde27ed0b0c22104a3c"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    source_dir = root / "hw/soc/analog/pcie"
    baseline = {name: (source_dir / name).read_text() for name in base.SOURCES}
    original_rows = base.devices(baseline)
    candidate = (source_dir / SOURCE).read_text()
    defs = base.definitions({SOURCE: candidate, **{
        name: text for name, text in baseline.items()
        if name != "pll_pump_filter_hv_v1.spice"
    }})
    rows, wires = base.expand(
        defs, ["nssoc_tail115_pump_filter13_v1", "xloop", base.PORTS]
    )
    expected = json.loads(json.dumps(original_rows))
    changed = [row for row in expected if row["path"] == "xloop.xrhi"]
    if len(changed) != 1 or changed[0]["params"]["l"] != "80u":
        raise ValueError("The baseline upper-bias resistor must bind exactly once")
    changed[0]["params"]["l"] = "140u"
    if rows != expected or wires:
        raise ValueError("Only the intended resistor length may change")
    wrapper = Path(__file__).resolve()
    before = base.pin(wrapper)
    original_sources, original_top = base.SOURCES, base.TOP
    try:
        base.TOP = TOP
        base.SOURCES = {
            SOURCE: SOURCE_SHA,
            "pll_pfd_charge_pump_hv_v1.spice":
                original_sources["pll_pfd_charge_pump_hv_v1.spice"],
        }
        base.build(args.pdk, args.out)
    finally:
        base.SOURCES, base.TOP = original_sources, original_top
    result_path = args.out.resolve() / "result.json"
    result = json.loads(result_path.read_text())
    if base.pin(wrapper) != before:
        raise ValueError("Generator changed while executing")
    result["inputs"][str(wrapper)] = before
    result["inputs"][str(source_dir / "pll_pump_filter_hv_v1.spice")] = (
        original_sources["pll_pump_filter_hv_v1.spice"]
    )
    result["only_core_change"] = {
        "path": "xloop.xrhi", "width_um": 1,
        "old_length_um": 80, "new_length_um": 140,
    }
    result["closed_loop_accepted"] = False
    result_path.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
