#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Two physical first-stage pull-ups: L6.4 to4um; all finite screens unchanged.

Predeclared sequence: actual disconnect at0.6V first, then0.85V/0.6V nominal
and actual wrong-modulus if the nominal and device limits are compatible.
The unchanged62-record VCO retains889R765C and genuine feedback loading.
No closed-loop, PVT, physical-divider or main-chip acceptance is implied.
"""

from pathlib import Path
import types

import characterize_pcie_vco_v6_feedback_bias_v1 as previous

core = previous.core
ROOT = core.ROOT
ANALOG = ROOT / "hw/soc/analog/pcie"
TOP = "nssoc_pll_feedback_vco_v6_wire_v3"
CHAIN = ANALOG / "pll_feedback_vco_v6_wire_v3.spice"
DIVIDER = ANALOG / "clock_div4_hbt_v7.spice"
CONDITIONER = ANALOG / "clock_div2_conditioned_hbt_v3.spice"
PREVIOUS_SHA = "56bd41ef4d8840a5a5344fc8a2e27fcd555126ec08eddab15a251e21a9e33405"
SOURCE_PINS = {
    "clock_div2_conditioned_hbt_v2.spice": "4d66ab2d298dc80dfd588ff71dfe7da6457316fd9645fe24228ee4399e44a77b",
    "clock_div4_hbt_v6.spice": "da930f276ceca44341476fd47e84c9fcc427fdfa6c0917693530e16f159e977f",
    "pll_feedback_vco_v6_wire_v2.spice": "0efb2161450fedfd0475db6df1748a275d1a2587e0e02cc041c7dc916eab5aa8",
}
BRIDGES = {
    "clock_div2_conditioned_hbt_v2.spice": (
        CONDITIONER,
        [
            (
                "nssoc_clock_div2_conditioned_hbt_v2",
                "nssoc_clock_div2_conditioned_hbt_v3",
                2,
            ),
            (
                "XUP avdd ckp sub rppd w=1u l=6.4u b=0 sw_et=1",
                "XUP avdd ckp sub rppd w=1u l=4u b=0 sw_et=1",
                1,
            ),
            (
                "XUN avdd ckn sub rppd w=1u l=6.4u b=0 sw_et=1",
                "XUN avdd ckn sub rppd w=1u l=4u b=0 sw_et=1",
                1,
            ),
            (
                "* Separate v2: both native upward-bias rppd lengths8 to6.4um; all other devices unchanged.",
                "* Separate v3: both physical pull-up lengths6.4 to4um; all other devices unchanged.",
                1,
            ),
        ],
    ),
    "clock_div4_hbt_v6.spice": (
        DIVIDER,
        [
            ("nssoc_clock_div4_hbt_v6", "nssoc_clock_div4_hbt_v7", 2),
            (
                "nssoc_clock_div2_conditioned_hbt_v2",
                "nssoc_clock_div2_conditioned_hbt_v3",
                1,
            ),
            (
                "* Separate v6: first conditioner uses L6.4 pull-ups; limiter and sampler remain unchanged.",
                "* Separate v7: first conditioner uses L4 pull-ups; limiter and sampler remain unchanged.",
                1,
            ),
        ],
    ),
    "pll_feedback_vco_v6_wire_v2.spice": (
        CHAIN,
        [
            (
                "nssoc_pll_feedback_vco_v6_wire_v2",
                "nssoc_pll_feedback_vco_v6_wire_v3",
                2,
            ),
            ("nssoc_clock_div4_hbt_v6", "nssoc_clock_div4_hbt_v7", 1),
            (
                "* Physical VCOv6; first divider pull-ups L6.4um, other native /4 and /20 unchanged.",
                "* Physical VCOv6; first divider pull-ups L4um, other native /4 and /20 unchanged.",
                1,
            ),
        ],
    ),
}


def sources():
    core.require(core.n.common.sha(previous.__file__) == PREVIOUS_SHA, "Frozen biasV1")
    result = {}
    for old, (new, changes) in BRIDGES.items():
        before = (ANALOG / old).read_text()
        core.require(
            core.n.common.sha(ANALOG / old) == SOURCE_PINS[old],
            "Frozen predecessor " + old,
        )
        expected = before
        for a, b, count in changes:
            core.require(expected.count(a) == count, "Exact source bridge census")
            expected = expected.replace(a, b)
        actual = new.read_text()
        core.require(actual == expected, "Only declared two-rppd change " + new.name)
        inverse = actual
        for a, b, count in reversed(changes):
            core.require(inverse.count(b) == count, "Unique inverse bridge")
            inverse = inverse.replace(b, a)
        core.require(inverse == before, "Byte-exact predecessor reconstructed")
        result[new.name] = actual
    return result


def config(vctrl=0.6, fault=""):
    c, before, old_texts = previous.config(vctrl, fault)
    text = sources()
    changed = {k: v for k, v in old_texts.items() if k not in BRIDGES}
    changed.update(text)
    if fault == "disconnect_divider_clock":
        old, new = core.FAULTS[fault]
        core.require(
            changed[CHAIN.name].count(old) == 1, "Actual divider-input fault retained"
        )
        changed[CHAIN.name] = changed[CHAIN.name].replace(old, new)
    rows = core.n.graph(
        {
            k: v
            for k, v in changed.items()
            if k not in ("hybrid-open.spice", CHAIN.name)
        },
        [
            (
                "nssoc_clock_div4_hbt_v7",
                "xchain.xdiv",
                [
                    "clkp",
                    "clkp" if fault == "disconnect_divider_clock" else "clkn",
                    "qp",
                    "qn",
                    "dvdd",
                    "0",
                    "0",
                ],
            ),
            (
                core.old.counter.TOP,
                "xchain.xfb",
                ["qp", "qn", "clearb", "fb", "fbbar", "dvdd", "cvdd", "0", "0"],
            ),
        ],
    )
    core.require(len(rows) == 375, "All original divider and CMOS feedback devices")
    rows += [row for row in before if row["path"].startswith("xchain.xosc.")]
    old_by = {row["path"]: row for row in before}
    actual_by = {row["path"]: row for row in rows}
    core.require(
        len(actual_by) == len(rows) == 437 and set(actual_by) == set(old_by),
        "All437 native identities retained",
    )
    deltas = [path for path in actual_by if actual_by[path] != old_by[path]]
    core.require(
        set(deltas) == {"xchain.xdiv.xfirst.xup", "xchain.xdiv.xfirst.xun"},
        "Only two declared physical resistors change",
    )
    for path in deltas:
        expected = dict(old_by[path], params=dict(old_by[path]["params"], l="4u"))
        core.require(
            old_by[path]["params"]["l"] == "6.4u" and actual_by[path] == expected,
            "Only L6.4 to4, all other terminal/geometry parameters exact",
        )
    core.require(
        changed["hybrid-open.spice"] == old_texts["hybrid-open.spice"],
        "Exact VCO wire model",
    )
    core.require(
        core.n.vectors(rows, c["extra_vectors"])
        == core.n.vectors(before, c["extra_vectors"]),
        "Every original observed vector retained in order",
    )
    model, name, ports = c["roots"][0]
    core.require(model == previous.TOP, "Unchanged chain root interface")
    c["roots"] = [(TOP, name, ports)]
    c["sources"] += [str(CONDITIONER), str(DIVIDER), str(CHAIN)]
    c["case"] = "loaded_physical_vco_v6_div80_first_pullups_L4"
    c["conditioner_change"] = dict(
        paths=sorted(deltas),
        old_l_um=6.4,
        new_l_um=4.0,
        w_um=1.0,
        measured_improvement=False,
    )
    return c, rows, changed


# Exact inherited execution, collection, screens and measurement code in a
# private namespace. V1/V2 globals and every predecessor file remain unchanged.
_scope = dict(
    previous._scope,
    __file__=__file__,
    __name__=__name__,
    SOURCE=CHAIN,
    TOP=TOP,
    config=config,
)
for _name, _value in previous._scope.items():
    if (
        isinstance(_value, types.FunctionType)
        and _value.__globals__ is previous._scope
        and _name != "config"
    ):
        _scope[_name] = types.FunctionType(
            _value.__code__,
            _scope,
            _value.__name__,
            _value.__defaults__,
            _value.__closure__,
        )
run, main = _scope["run"], _scope["main"]

if __name__ == "__main__":
    raise SystemExit(main())
