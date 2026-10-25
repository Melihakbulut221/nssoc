#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate native /4 v2 circuit: reduced DC loading and real MIM AC coupling.

All prior failure records, source files and engineering predicates stay frozen.
Private function namespaces reuse the exact native bench/measurement bytecode;
only the source-bound new physical top and its inventory are substituted.
"""

from pathlib import Path
import types

import characterize_pcie_div4 as prior

CIRCUIT = prior.ROOT / "hw/soc/analog/pcie/clock_div4_hbt_v2.spice"
FROZEN = {
    **prior.FROZEN,
    Path(
        prior.__file__
    ): "d4aa14a731dd5219be816d654583a264becb30df78340c8df93e264f97f2db16",
    prior.CIRCUIT: "6cdeb6cea1177d4eec7db2a41f07a18d75c7145c58f5348fe05893bb4924ae8e",
}


def expected_circuit():
    text = prior.CIRCUIT.read_text()
    for before, after in (
        ("nssoc_clock_div4_hbt", "nssoc_clock_div4_hbt_v2"),
        ("w=2u l=4u", "w=2u l=8u"),
        ("w=1u l=3u", "w=1u l=6u"),
        ("w=10u l=10u", "w=20u l=20u"),
    ):
        prior.require(text.count(before) == 2, "Exact two-sided geometry anchor")
        text = text.replace(before, after)
    return text.replace(
        "* Two frozen native /2 cores with actual interstage resistive conditioning.",
        "* Separate v2: lower DC loading, stronger real MIM interstage AC coupling.",
    )


def verify_sources():
    prior.verify_sources()
    for p, digest in FROZEN.items():
        prior.require(
            prior.old.sha(p) == digest, "Frozen method or native cell changed"
        )
    prior.require(
        CIRCUIT.read_text() == expected_circuit(), "Exact v2 physical geometry"
    )


# None of the imported prior module's globals are changed. Every old method
# resolves its references through this new private namespace, including the
# actual top-level pin expansion and current source capture.
_scope = {
    **vars(prior),
    "__file__": __file__,
    "__doc__": __doc__,
    "CIRCUIT": CIRCUIT,
    "TOP": "nssoc_clock_div4_hbt_v2",
    "FROZEN": FROZEN,
}
_cloned = {}
for _name, _value in vars(prior).items():
    if isinstance(_value, types.FunctionType) and _value.__module__ == prior.__name__:
        _cloned[_name] = types.FunctionType(
            _value.__code__,
            _scope,
            _value.__name__,
            _value.__defaults__,
            _value.__closure__,
        )
_scope.update(_cloned)
_scope["verify_sources"] = verify_sources
# The prior run function embeds one descriptive limitation tuple. Correct only
# that geometry label in its private code constants; executable bytecode,
# numerical thresholds, native commands and all other constants stay identical.
_run_code = prior.run.__code__
_old_label = "Two native10x10um MIM feed-forward capacitors"
_tuples = [
    c
    for c in _run_code.co_consts
    if isinstance(c, tuple) and any(isinstance(s, str) and _old_label in s for s in c)
]
prior.require(len(_tuples) == 1, "Unique inherited physical limitation tuple")
_old_tuple = _tuples[0]
_new_tuple = tuple(
    s.replace(_old_label, "Two native20x20um MIM feed-forward capacitors")
    if isinstance(s, str)
    else s
    for s in _old_tuple
)
_new_code = _run_code.replace(
    co_consts=tuple(_new_tuple if c == _old_tuple else c for c in _run_code.co_consts)
)
_scope["run"] = types.FunctionType(_new_code, _scope, "run")
_scope["_read"] = types.FunctionType(
    prior.old.read_wave.__code__,
    {**prior.old.read_wave.__globals__, "vectors": _scope["vectors"]},
)
run = _scope["run"]
main = _scope["main"]
cases = _scope["cases"]
device_contract = _scope["device_contract"]
source_texts = _scope["source_texts"]
deck = _scope["deck"]
vectors = _scope["vectors"]
electrical_vectors = _scope["electrical_vectors"]
read_wave = _scope["read_wave"]
read_flags = _scope["read_flags"]
initial_op = _scope["initial_op"]
measure = _scope["measure"]
accepted = _scope["accepted"]


if __name__ == "__main__":
    raise SystemExit(main())
