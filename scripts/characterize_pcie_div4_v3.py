#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate /4 experiment: four actual second-stage collector loads, L2.4um.

The first stage, interstage conditioner, native models, startup, measurements
and limits remain frozen. This is finite schematic evidence, not a PLL/CDR.
"""

from pathlib import Path
import re
import types

import characterize_pcie_div4_v2 as prior

BASE = prior.prior
OLD = BASE.old
CIRCUIT = BASE.ROOT / "hw/soc/analog/pcie/clock_div4_hbt_v3.spice"
TOP = "nssoc_clock_div4_hbt_v3"
CORE = "nssoc_clock_div2_stage2_v3"
LATCH = "nssoc_cml_latch_div4_v3"
FROZEN = {
    **prior.FROZEN,
    Path(
        prior.__file__
    ): "f7cd2bb64ff76f4c9ed1459133706d48b42cc138019ec7b6f95f601c23f10954",
    prior.CIRCUIT: "35cbe9704c05b152e9913c0494f94075d569f71bcbd1aef05acd7e2ea8374baa",
}


def second_core(case):
    fault = case["fault"]
    BASE.require(
        fault
        in (
            "",
            "second_no_toggle",
            "second_same_phase",
            "second_no_bias",
            "second_same_clock",
        ),
        "Exact second-stage physical fault",
    )
    changed = fault in ("second_no_toggle", "second_same_phase", "second_no_bias")
    text = (
        OLD.circuit(dict(case, fault=fault.removeprefix("second_")))
        if changed
        else OLD.CIRCUIT.read_text()
    )
    name = CORE + "_fault" if changed else CORE
    return text.replace("nssoc_clock_div2_hbt", name).replace(
        "nssoc_cml_latch", LATCH
    ), name


def expected_circuit():
    text = prior.CIRCUIT.read_text().replace("nssoc_clock_div4_hbt_v2", TOP)
    anchor = "XSECOND ckp ckn qp qn avdd avss sub nssoc_clock_div2_hbt"
    BASE.require(text.count(anchor) == 1, "Exact second-stage anchor")
    text = text.replace(anchor, anchor.replace("nssoc_clock_div2_hbt", CORE))
    text = text.replace(
        "* Separate v2: lower DC loading, stronger real MIM interstage AC coupling.",
        "* Separate v3: four second-stage collector loads L2.12->2.4um.",
    )
    blocks = re.findall(
        r"(?ms)^\.subckt nssoc_cml_latch .*?^\.ends nssoc_cml_latch\s*$",
        OLD.LATCH.read_text(),
    )
    BASE.require(len(blocks) == 1, "One literal frozen latch body")
    latch = blocks[0].strip()
    BASE.require(latch.count("w=8u l=2.12u") == 2, "Exactly two loads per reused latch")
    latch = latch.replace("nssoc_cml_latch", LATCH).replace(
        "w=8u l=2.12u", "w=8u l=2.4u"
    )
    core, _ = second_core(OLD.BASE)
    return text.rstrip() + "\n\n" + core.rstrip() + "\n\n" + latch + "\n"


def verify_sources():
    prior.verify_sources()
    for path, digest in FROZEN.items():
        BASE.require(OLD.sha(path) == digest, "Frozen source changed: " + str(path))
    BASE.require(
        CIRCUIT.read_text() == expected_circuit(), "Exact four native load changes"
    )


def source_texts(case):
    top = CIRCUIT.read_text()
    core, name = second_core(case)
    if name != CORE:
        anchor = "XSECOND ckp ckn qp qn avdd avss sub " + CORE
        BASE.require(top.count(anchor) == 1, "Exact selected fault anchor")
        top = top.replace(anchor, anchor.removesuffix(CORE) + name) + "\n" + core
    if case["fault"] == "second_same_clock":
        BASE.require(top.count("XSECOND ckp ckn") == 1, "Exact selected clock anchor")
        top = top.replace("XSECOND ckp ckn", "XSECOND ckp ckp")
    return {
        BASE.VCO.name: BASE.VCO.read_text(),
        OLD.LATCH.name: OLD.LATCH.read_text(),
        OLD.CIRCUIT.name: OLD.CIRCUIT.read_text(),
        BASE.CONDITIONER.name: BASE.CONDITIONER.read_text(),
        CIRCUIT.name: top,
    }


def cases(suite):
    if suite == "pilot":
        table = {c["name"]: c for c in prior.cases("finite")}
        return [table["hot_slow"], table["nominal"]]
    return prior.cases(suite)


# Clone the inherited functions into a separate namespace. No imported module
# globals change, and all native execution/metrology bytecode is preserved.
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
_scope.update(verify_sources=verify_sources, source_texts=source_texts, cases=cases)
_scope["_read"] = types.FunctionType(
    OLD.read_wave.__code__, {**OLD.read_wave.__globals__, "vectors": _scope["vectors"]}
)
run = _scope["run"]
main = _scope["main"]
device_contract = _scope["device_contract"]
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
