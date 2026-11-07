#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""c5r3k first-divider macro: the unchanged load3p2 v2 generator on the c5r3k conditioner.

The PLL parent places nssoc_clock_div4_load3p2_v2_layout twice (div1 and div2).
The c5r3k what-if widens only the first divider's conditioner series
resistors (extracted XD0497/XD0498 = div1 DIV__XFIRST__XSN/XSP, 4u to 16u,
L3.6 unchanged), so this is a separate macro for div1 only; div2 keeps the
v2 macro. Only the conditioner source file and the macro name differ from
make_pcie_clock_div4_load3p2_v2.py: its placement, routing, power straps,
taps, restored first-toggle L2.8 loads and second-toggle L3.2 loads are reused
unchanged. Generation alone does not establish DRC/LVS, PEX or division.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_pcie_clock_div4_load3p2_v2 as base  # noqa: E402

TOP = "nssoc_clock_div4_load3p2_c5r3k_v1_layout"
FROZEN = "hw/soc/analog/pcie/clock_div2_conditioned_hbt_v3.spice"
CONDITIONER = "hw/soc/analog/pcie/clock_div2_conditioned_hbt_c5r3k_v1.spice"
CONDITIONER_SHA256 = "0348fbd79ade6525f9502e0f7acebb1cf51f968849a7cb1b6fb9929c1d5770cf"
SERIES = ("DIV__XFIRST__XSP", "DIV__XFIRST__XSN")
FROZEN_SOURCES = dict(base.SOURCES)
SOURCES = {
    (CONDITIONER if path == FROZEN else path): (
        CONDITIONER_SHA256 if path == FROZEN else digest
    )
    for path, digest in FROZEN_SOURCES.items()
}
assert len(SOURCES) == len(FROZEN_SOURCES) == 4 and CONDITIONER in SOURCES


def configure(*modules):
    """Point the frozen generator (and any checker that imported it) at c5r3k."""
    for module in (base, *modules):
        module.TOP, module.SOURCES = TOP, SOURCES


def exact_delta(root):
    """Flattened c5r3k rows differ from v2 only in the two first-stage series widths."""
    try:
        base.SOURCES = FROZEN_SOURCES
        before = base.devices(root)
    finally:
        configure()
    after = base.devices(root)
    if [r["name"] for r in before] != [r["name"] for r in after]:
        raise ValueError("Device identities changed")
    delta = []
    for a, b in zip(before, after):
        if a == b:
            continue
        if a["name"] not in SERIES or a["kind"] != "resistor":
            raise ValueError("Unexpected divider change: " + a["name"])
        if (a["width_um"], a["length_um"], b["width_um"], b["length_um"]) != (4, 3.6, 16, 3.6):
            raise ValueError("Unexpected conditioner geometry: " + a["name"])
        if {k: v for k, v in a.items() if k != "width_um"} != {
            k: v for k, v in b.items() if k != "width_um"
        }:
            raise ValueError("Conditioner connectivity changed: " + a["name"])
        delta.append(dict(name=a["name"], length_um=3.6, old_width_um=4, new_width_um=16))
    if sorted(d["name"] for d in delta) != sorted(SERIES):
        raise ValueError("Exactly the two first-stage series resistors must change")
    return delta


if __name__ == "__main__":
    configure()
    base.main()
