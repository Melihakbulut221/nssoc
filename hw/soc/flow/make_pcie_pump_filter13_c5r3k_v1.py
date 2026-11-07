#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""c5r3k pump/filter macro: the unchanged pump13 generator on the c5r3k netlist.

Reference is the RHI120/C8 pump (pll_pump_filter_hv_rhi120_c8_v1.spice).
The only core change is xloop.xdet.xcp.xpsource (extracted XD0375) width
6.4 um to 8 um, L2 unchanged. Placement, routing, contacts, ports and LEF come
from make_pcie_pump_filter13_v1.py unchanged. The new vctrl integrator is a
separate macro (make_pcie_pll_integrator_c5r3k_v1.py). Generation alone does
not establish DRC/LVS, PEX or loop behaviour.
"""

import argparse
import copy
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_pcie_pump_filter13_v1 as base  # noqa: E402

TOP = "nssoc_pump_filter13_c5r3k_v1"
CP = "pll_pfd_charge_pump_hv_v1.spice"
REFERENCE = ("pll_pump_filter_hv_rhi120_c8_v1.spice",
             "88c72dc6de79d598548e3eba833f832bf02501c126f75e2f2e9435fcd207fc55")
CANDIDATE = ("pll_pump_filter_hv_c5r3k_v1.spice",
             "240b21c42e857c6ae89cf555285e6a216c39fe8abded3c05f8acf5f4105a2d6f")
CP_SHA256 = "194a50048f88614b3f3c0bbbac88cdf8be7f71a8cd62eac3f14914b652d865fc"
CHANGED = "xloop.xdet.xcp.xpsource"


def rows(root, name, digest):
    source = Path(root) / "hw/soc/analog/pcie"
    text = (source / name).read_text()
    if hashlib.sha256(text.encode()).hexdigest() != digest:
        raise ValueError("Pinned pump source changed: " + name)
    if hashlib.sha256((source / CP).read_bytes()).hexdigest() != CP_SHA256:
        raise ValueError("Frozen PFD/charge-pump library changed")
    d = base.definitions({"filter": text, CP: (source / CP).read_text()})
    result, wires = base.expand(d, ["nssoc_tail115_pump_filter13_v1", "xloop", base.PORTS])
    if wires or len(result) != 13:
        raise ValueError("Unexpected pump/filter core")
    return result


def exact_delta(root):
    before = rows(root, *REFERENCE)
    expected = copy.deepcopy(before)
    hit = [r for r in expected if r["path"] == CHANGED]
    if len(hit) != 1 or hit[0]["model"] != "sg13_hv_pmos":
        raise ValueError("XPSOURCE must bind exactly once")
    if hit[0]["nets"] != ["xloop.xdet.xcp.source", "xloop.xdet.xcp.pb", "div_avdd", "div_avdd"]:
        raise ValueError("XPSOURCE connectivity differs")
    if hit[0]["params"] != {"w": "6.4u", "l": "2u", "ng": "1", "m": "1"}:
        raise ValueError("XPSOURCE reference geometry differs")
    hit[0]["params"]["w"] = "8u"
    after = rows(root, *CANDIDATE)
    if after != expected or after == before:
        raise ValueError("c5r3k pump differs from the single declared change")
    return dict(path=CHANGED, old_width_um=6.4, new_width_um=8, unchanged_length_um=2,
                other12core_devices_unchanged=True)


def configure(*modules):
    for module in (base, *modules):
        module.TOP = TOP
    base.SOURCES = {CANDIDATE[0]: CANDIDATE[1], CP: CP_SHA256}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    exact_delta(root)
    configure()
    base.build(args.pdk, args.out)


if __name__ == "__main__":
    main()
