#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Keep real public observation ports even when a fault unloads a wire port.

The v1 disconnect capture failed before measurement because CLKN disappeared
from the intrinsic-terminal vector set. Its error and all positive captures
remain immutable. No circuit, threshold, sample, limit or native flag changes.
"""

import types

import characterize_pcie_vco_v6_feedback_v1 as previous

PREVIOUS_SHA = "0658aa499361c2eba01b3af7671cdb1b2e97da7f64e41d7afe72b4fd659a841a"


def config(vctrl=0.6, fault=""):
    previous.require(
        previous.n.common.sha(previous.__file__) == PREVIOUS_SHA,
        "Frozen v1 capture unchanged",
    )
    c, rows, texts = previous.config(vctrl, fault)
    declared = set(previous.n.vectors(rows, c["extra_vectors"]))
    for name in previous.OBS[1:]:
        if name not in declared:
            c["extra_vectors"].append(name)
            declared.add(name)
    previous.require(
        set(previous.OBS[1:]) <= declared, "Complete public observation boundary"
    )
    return c, rows, texts


# Exact code objects in an independent namespace; never mutate v1 globals.
_scope = dict(vars(previous), __file__=__file__, __name__=__name__, config=config)
for _name, _value in vars(previous).items():
    if isinstance(_value, types.FunctionType) and _value.__globals__ is vars(previous):
        if _name != "config":
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
