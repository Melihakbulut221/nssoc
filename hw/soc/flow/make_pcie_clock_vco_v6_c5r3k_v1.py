#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""c5r3k VCO macro: the unchanged v6 local generator on the c5r3k ring-load netlist.

Only the source circuit and the macro name differ from
make_pcie_clock_vco_v6_local_v1.py. The six ring loads XRP0-2/XRN0-2 are
4.93 um long instead of 4.4 um (W8 unchanged); placement, routing, taps and
every other device come from the frozen v6 generator code. Generation alone
does not establish DRC/LVS, PEX or oscillation.
"""

import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_pcie_clock_vco_v6_local_v1 as base  # noqa: E402

TOP = "nssoc_clock_vco_hbt_v6_c5r3k_v1_layout"
CIRCUIT = "hw/soc/analog/pcie/clock_vco_hbt_v6_c5r3k_v1.spice"
CIRCUIT_SHA256 = "4683a8157027498b703e1adade206814bea43fd4fc693ca86a2a2f78307b6378"
V6_SHA256 = "3ab8792997254a9292c2648a6b500714cc5428958700ba70dd6930bc37eeb2c6"
RING_LOADS = ("RP0", "RN0", "RP1", "RN1", "RP2", "RN2")


def configure(*modules):
    """Point the frozen generator (and any checker that imported it) at c5r3k."""
    for module in (base, *modules):
        module.TOP, module.CIRCUIT, module.CIRCUIT_SHA256 = TOP, CIRCUIT, CIRCUIT_SHA256


def exact_delta(root):
    """The c5r3k source differs from v6 only in the six ring-load lengths."""
    root = Path(root)
    old = (root / "hw/soc/analog/pcie/clock_vco_hbt_v6.spice").read_text()
    new = (root / CIRCUIT).read_text()
    if hashlib.sha256(new.encode()).hexdigest() != CIRCUIT_SHA256:
        raise ValueError("c5r3k VCO circuit differs from its pinned source")
    if hashlib.sha256(old.encode()).hexdigest() != V6_SHA256:
        raise ValueError("Frozen v6 VCO circuit changed")
    configure()
    try:
        base.CIRCUIT_SHA256 = V6_SHA256
        before = base.devices(old)
    finally:
        base.CIRCUIT_SHA256 = CIRCUIT_SHA256
    after = base.devices(new)
    if [r["name"] for r in before] != [r["name"] for r in after]:
        raise ValueError("Device identities changed")
    delta = []
    for a, b in zip(before, after):
        if a == b:
            continue
        if a["name"] not in RING_LOADS or a["kind"] != "resistor":
            raise ValueError("Unexpected VCO change: " + a["name"])
        if (a["width_um"], a["length_um"], b["width_um"], b["length_um"]) != (8, 4.4, 8, 4.93):
            raise ValueError("Unexpected ring-load geometry: " + a["name"])
        if {k: v for k, v in a.items() if k != "length_um"} != {
            k: v for k, v in b.items() if k != "length_um"
        }:
            raise ValueError("Ring-load connectivity changed: " + a["name"])
        delta.append(dict(name=a["name"], width_um=8, old_length_um=4.4, new_length_um=4.93))
    if [d["name"] for d in delta] != list(RING_LOADS):
        raise ValueError("Exactly the six ring loads must change")
    return delta


if __name__ == "__main__":
    configure()
    base.main()
