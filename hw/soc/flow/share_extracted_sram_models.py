#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Specialize the pinned single-finger PSP wrapper with explicit junctions.

This preserves the wrapper's AS-dependent fallback exactly, and records it.
pre_layout must be chosen explicitly; equivalence to the wrapper is distinct
from qualification of the extractor or the parasitic device models.
"""

import hashlib
import math
import re

from share_sram_psp_models import specialize

WRAPPER_SHA256 = "124c48af28aee8f4788170b50dbb4d798e7d830c6bb37516f749e16f676fa9db"
SUFFIXES = {"": 1, "t": 1e12, "g": 1e9, "meg": 1e6, "k": 1e3,
            "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15}


def numeric(token):
    match = re.fullmatch(
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(meg|[tgkmunpf])?",
        token, re.I,
    )
    if not match:
        raise ValueError("Unsupported literal: " + token)
    value = float(match[1]) * SUFFIXES[(match[2] or "").lower()]
    if not math.isfinite(value) or value < 0:
        raise ValueError("Negative or nonfinite dimension")
    return value


def specialize_extracted(circuit, parameters, wrapper, *, pre_layout):
    if type(pre_layout) is not int or pre_layout not in (0, 1):
        raise ValueError("Choose pre_layout=0 or 1 explicitly")
    if hashlib.sha256(wrapper.encode()).hexdigest() != WRAPPER_SHA256:
        raise ValueError("Unverified wrapper revision")
    lines = []
    for line in circuit.splitlines():
        if line.startswith("+"):
            if not lines:
                raise ValueError("Orphan continuation")
            lines[-1] += " " + line[1:]
        else:
            lines.append(line)
    profiles, models, output, devices, identifiers = {}, {}, [], [], set()
    for line in lines:
        fields = line.split()
        if not fields or fields[0].startswith(("*", ".")):
            output.append(line)
            continue
        key = fields[0].upper()
        if key in identifiers:
            raise ValueError("Duplicate instance")
        identifiers.add(key)
        if key[0] in "RC":
            if len(fields) != 4:
                raise ValueError("Unsupported passive syntax")
            numeric(fields[3])
            output.append(line)
            continue
        if key[0] != "X" or len(fields) != 12 or fields[5] not in (
                "sg13_lv_nmos", "sg13_lv_pmos"):
            raise ValueError("Unsupported extracted device")
        pairs = [field.split("=") for field in fields[6:]]
        if any(len(pair) != 2 for pair in pairs):
            raise ValueError("Malformed device parameters")
        values = {name.lower(): numeric(value) for name, value in pairs}
        if set(values) != {"w", "l", "as", "ad", "ps", "pd"}:
            raise ValueError("Missing or duplicate junction/dimension parameter")
        kind = fields[5]
        geometry = (kind, values["l"], values["w"])
        if geometry not in models:
            # Reuse the validated W/L domain and default-wrapper checks, then
            # bind the same original expressions to the explicit layout mode.
            _, _, rows = specialize(
                f"X0 d g s b {kind} l={values['l']:.17g} w={values['w']:.17g}",
                parameters, wrapper,
            )
            name = rows[0]["model"] + "_layout" + str(pre_layout)
            original = kind.replace("sg13_lv_", "sg13g2_lv_") + "_psp"
            parts = re.split(r"(?m)(?=^\.model )", parameters)[1:]
            matching = [part for part in parts if part.split()[1] == original]
            if len(matching) != 1:
                raise ValueError("Ambiguous original model")
            body = "\n".join(s for s in matching[0].splitlines()
                             if s.startswith((".model", "+")))
            body = body.replace(".model " + original + " ", ".model " + name + " ", 1)
            for symbol, value in {"w": values["w"], "l": values["l"], "ng": 1,
                                  "pre_layout": pre_layout}.items():
                body = re.sub(r"\b" + symbol + r"\b", format(value, ".17g"), body)
            models[geometry] = (name, body)
        name = models[geometry][0]
        junction = {k: values[k] for k in ("as", "ad", "ps", "pd")}
        fallback = values["as"] <= 1e-50
        if fallback:
            # Exact pinned wrapper behavior: AS selects all four defaults,
            # including when the caller supplied nonzero AD/PS/PD.
            junction = {"as": values["w"] * .34e-6, "ad": values["w"] * .34e-6,
                        "ps": 2 * (values["w"] + .34e-6),
                        "pd": 2 * (values["w"] + .34e-6)}
        params = {"l": values["l"], "w": values["w"], "nf": 1, "mult": 1,
                  **junction, "dta": 0, "ngcon": 2, "delvto": 0, "factuo": 1}
        output.append("N" + fields[0][1:] + " " + " ".join(fields[1:5]) + " " + name
                      + " " + " ".join(f"{k}={v:.17g}" for k, v in params.items()))
        profile = (kind, *values.items())
        if profile not in profiles:
            profiles[profile] = dict(primitive=kind, input=values, effective_junction=junction,
                                     wrapper_fallback=fallback, model=name)
        devices.append(dict(instance=fields[0], profile=list(profiles).index(profile)))
    if not devices:
        raise ValueError("No extracted transistors")
    return ("\n".join(output) + "\n", "\n\n".join(v[1] for v in models.values()) + "\n",
            dict(pre_layout=pre_layout, profiles=list(profiles.values()), devices=devices,
                 qualified_pex=False))
