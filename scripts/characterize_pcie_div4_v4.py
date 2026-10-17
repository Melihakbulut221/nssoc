#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite /4 trial with a genuine native HBT interstage clock limiter.

The frozen /4v2 latch cores and VCO remain unchanged. Four additional HBTs
and seven real resistors provide gain; the MIM/resistor network sets the
second clock common mode. No ideal gain, clock, injected state or PLL exists.
"""

from pathlib import Path
import ast
import inspect
import types

import characterize_pcie_div4_v2 as prior

BASE = prior.prior
OLD = BASE.old
TOP = "nssoc_clock_div4_hbt_v4"
CIRCUIT = BASE.ROOT / "hw/soc/analog/pcie/clock_div4_hbt_v4.spice"
FROZEN = {
    **prior.FROZEN,
    Path(
        prior.__file__
    ): "f7cd2bb64ff76f4c9ed1459133706d48b42cc138019ec7b6f95f601c23f10954",
    prior.CIRCUIT: "35cbe9704c05b152e9913c0494f94075d569f71bcbd1aef05acd7e2ea8374baa",
}
CONDITIONERS = tuple(
    "xdiv." + n
    for n in (
        "xlsp",
        "xlsn",
        "xldp",
        "xldn",
        "xlb",
        "xlrp",
        "xlrn",
        "xsp",
        "xsn",
        "xdp",
        "xdn",
    )
)
SECOND_CLOCK_MIN_PEAK_V = 0.30
TRANSFORMED_SOURCE = {}


def expected_circuit():
    text = prior.CIRCUIT.read_text().replace("nssoc_clock_div4_hbt_v2", TOP)
    anchor = "XSP s1p ckp sub rppd w=2u l=8u b=0 sw_et=1"
    BASE.require(text.count(anchor) == 1, "Exact frozen interstage anchor")
    stage = """* Real input bias, limiter reference and differential pair; no ideal gain.
XLSP s1p bip sub rppd w=2u l=3.6u b=0 sw_et=1
XLSN s1n bin sub rppd w=2u l=3.6u b=0 sw_et=1
XLDP bip avss sub rppd w=1u l=16u b=0 sw_et=1
XLDN bin avss sub rppd w=1u l=16u b=0 sw_et=1
XLB avdd lref sub rppd w=1u l=9u b=0 sw_et=1
XLREF lref lref avss sub npn13G2 Nx=1
XLP ln bip lt sub npn13G2 Nx=2
XLN lp bin lt sub npn13G2 Nx=2
XLT lt lref avss sub npn13G2 Nx=4
XLRP avdd lp sub rppd w=8u l=4u b=0 sw_et=1
XLRN avdd ln sub rppd w=8u l=4u b=0 sw_et=1
* The unchanged real MIM feed-forward topology preserves clock swing.
XSP lp ckp sub rppd w=2u l=8u b=0 sw_et=1"""
    text = text.replace(anchor, stage)
    for before, after in (
        ("XSN s1n ckn", "XSN ln ckn"),
        ("XCP s1p ckp", "XCP lp ckp"),
        ("XCN s1n ckn", "XCN ln ckn"),
    ):
        BASE.require(text.count(before) == 1, "Exact two-sided connection anchor")
        text = text.replace(before, after)
    BASE.require(text.count("w=1u l=6u") == 2, "Exact two output bias resistors")
    return text.replace("w=1u l=6u", "w=1u l=7u").replace(
        "* Separate v2: lower DC loading, stronger real MIM interstage AC coupling.",
        "* Separate v4: real four-HBT interstage limiter and measured clock bias.",
    )


def verify_sources():
    prior.verify_sources()
    for p, digest in FROZEN.items():
        BASE.require(OLD.sha(p) == digest, "Frozen source changed: " + str(p))
    BASE.require(
        CIRCUIT.read_text() == expected_circuit(), "Exact native limiter topology"
    )


def cases(suite):
    if suite == "pilot":
        c = {r["name"]: r for r in prior.cases("finite")}
        return [c["hot_slow"], c["nominal"]]
    return prior.cases(suite)


_scope = {
    **prior._scope,
    "__file__": __file__,
    "__doc__": __doc__,
    "TOP": TOP,
    "CIRCUIT": CIRCUIT,
    "FROZEN": FROZEN,
    "CONDITIONERS": CONDITIONERS,
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


def install_with_census(name):
    # The exact native tree and pin derivation is unchanged. Only its required
    # concrete census/metadata changes from60/35 to64/42 for the new topology.
    # Parse the pinned source instead of relying on Python-version-specific
    # bytecode encoding of small integer constants.
    tree = ast.parse(inspect.getsource(getattr(BASE, name)))
    replacements = {60: 64, 35: 42}
    if name == "run":
        replacements[220] = 600  # Larger exact vector census; stricter storage floor.
    counts = dict.fromkeys(replacements, 0)

    class Census(ast.NodeTransformer):
        def visit_Constant(self, node):
            if type(node.value) is int and node.value in counts:
                counts[node.value] += 1
                node.value = replacements[node.value]
            elif isinstance(node.value, str):
                node.value = (
                    node.value.replace("all60", "all64")
                    .replace("Two native10x10um", "Two native20x20um")
                    .replace("Need220MiB", "Need600MiB")
                )
            return node

    tree = Census().visit(tree)
    BASE.require(
        all(v == 1 for v in counts.values()), "Exact census/resource replacements"
    )
    TRANSFORMED_SOURCE[name] = ast.unparse(tree)
    exec(compile(ast.fix_missing_locations(tree), __file__, "exec"), _scope)


for _name in ("device_contract", "run"):
    install_with_census(_name)
_flags = _scope["read_flags"].__code__
_scope["read_flags"] = types.FunctionType(
    _flags.replace(
        co_consts=tuple(
            c.replace("Exact60", "Exact64") if isinstance(c, str) else c
            for c in _flags.co_consts
        )
    ),
    _scope,
    "read_flags",
)
_scope.update(verify_sources=verify_sources, cases=cases)
_scope["_read"] = types.FunctionType(
    OLD.read_wave.__code__, {**OLD.read_wave.__globals__, "vectors": _scope["vectors"]}
)
_base_measure = _scope["measure"]


def measure(data, case):
    result = _base_measure(data, case)
    start = next(
        i for i, t in enumerate(data["time"]) if t >= OLD.LIMITS["observation_begin_s"]
    )
    for name, p, n in (("limiter_input", "bip", "bin"), ("limiter_output", "lp", "ln")):
        ps, ns = data[f"v(xdiv.{p})"][start:], data[f"v(xdiv.{n})"][start:]
        diff = [a - b for a, b in zip(ps, ns)]
        cm = [(a + b) / 2 for a, b in zip(ps, ns)]
        result["interfaces"][name] = dict(
            diff_range_v=[min(diff), max(diff)], common_mode_range_v=[min(cm), max(cm)]
        )
    low, high = result["interfaces"]["second_input"]["diff_range_v"]
    result["checks"]["second_clock_target_0p30_v"] = (
        min(-low, high) >= SECOND_CLOCK_MIN_PEAK_V
    )
    result["screen_pass"] = all(result["checks"].values())
    result["second_clock_target_v"] = SECOND_CLOCK_MIN_PEAK_V
    return result


_scope["measure"] = measure
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
