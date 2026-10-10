#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate two-load limiter revision; all v4 measurement gates stay mandatory.

The actual hot pilot needs at least4.50% more second-clock swing. Increasing
only two native limiter collector resistors from L4.0 to4.4um provides a
bounded physical gain experiment, not a threshold adjustment or ideal driver.
"""

from pathlib import Path
import types

import characterize_pcie_div4_v4 as prior

BASE = prior.BASE
OLD = prior.OLD
TOP = "nssoc_clock_div4_hbt_v5"
CIRCUIT = BASE.ROOT / "hw/soc/analog/pcie/clock_div4_hbt_v5.spice"
FROZEN = {
    **prior.FROZEN,
    Path(
        prior.__file__
    ): "ce9ce96ff0844a8c5f87f377c097b422c4bcc70e76156b7413168fda6a1c3395",
    prior.CIRCUIT: "8ef81ef1d8227f2271d6e4d3414811702df0517a713e7b18444e1e54fc2374b1",
}


def expected_circuit():
    text = prior.CIRCUIT.read_text().replace(prior.TOP, TOP)
    for name, node in (("XLRP", "lp"), ("XLRN", "ln")):
        before = f"{name} avdd {node} sub rppd w=8u l=4u b=0 sw_et=1"
        BASE.require(text.count(before) == 1, "Exactly two native collector loads")
        text = text.replace(before, before.replace("l=4u", "l=4.4u"))
    return text.replace(
        "* Separate v4: real four-HBT interstage limiter and measured clock bias.",
        "* Separate v5: two limiter collector loads L4.0 to4.4um; all guards unchanged.",
    )


def verify_sources():
    prior.verify_sources()
    for path, digest in FROZEN.items():
        BASE.require(OLD.sha(path) == digest, "Frozen source changed: " + str(path))
    BASE.require(CIRCUIT.read_text() == expected_circuit(), "Exact two-load revision")


# An independent namespace keeps every old producer and capture immutable.
_scope = {
    **prior._scope,
    "__file__": __file__,
    "__doc__": __doc__,
    "TOP": TOP,
    "CIRCUIT": CIRCUIT,
    "FROZEN": FROZEN,
}
for _name, _value in prior._scope.items():
    if isinstance(_value, types.FunctionType) and _value.__globals__ is prior._scope:
        _scope[_name] = types.FunctionType(
            _value.__code__,
            _scope,
            _value.__name__,
            _value.__defaults__,
            _value.__closure__,
        )
_scope["verify_sources"] = verify_sources
_scope["_read"] = types.FunctionType(
    OLD.read_wave.__code__, {**OLD.read_wave.__globals__, "vectors": _scope["vectors"]}
)
_base_measure = types.FunctionType(prior._base_measure.__code__, _scope)
measure = types.FunctionType(
    prior.measure.__code__,
    {**prior.measure.__globals__, "_base_measure": _base_measure},
)
_scope["measure"] = measure
cases = prior.cases
run = _scope["run"]
main = _scope["main"]
source_texts = _scope["source_texts"]
device_contract = _scope["device_contract"]
deck = _scope["deck"]
vectors = _scope["vectors"]
electrical_vectors = _scope["electrical_vectors"]
read_wave = _scope["read_wave"]
read_flags = _scope["read_flags"]
initial_op = _scope["initial_op"]
accepted = _scope["accepted"]


if __name__ == "__main__":
    raise SystemExit(main())
