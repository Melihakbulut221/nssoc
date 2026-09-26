#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Adapt a compared CML TX device netlist to ngspice; no wire/substrate RC extraction."""

import math
import re

PORTS = ("INP", "INN", "OUTP", "OUTN", "AVDD", "AVSS", "SUB", "IREF")
SCALE = {"": 1.0, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3}


def number(text):
    match = re.fullmatch(
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([pnum]?)", text
    )
    if match is None:
        raise ValueError("Unsupported numeric parameter: " + text)
    result = float(match[1]) * SCALE[match[2]]
    if not math.isfinite(result) or result <= 0:
        raise ValueError("Nonpositive or nonfinite device parameter")
    return result


def translate(text, tap_area_resistivity, tap_perimeter_resistivity):
    """Keep all extracted nodes/terminals; add only three zero-volt current probes.

    Tap conductance A/raspec + P/rpspec follows native CbTapCalc. This lumped
    contact model is not a spatial substrate network or qualified PEX model.
    """
    for value in (tap_area_resistivity, tap_perimeter_resistivity):
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Invalid native tap coefficient")
    lines = [
        line.split()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("*")
    ]
    if (
        len(lines) != 9
        or lines[0][:2] != [".SUBCKT", "nssoc_tx_cml_layout"]
        or len(lines[0][2:]) != 8
        or set(lines[0][2:]) != set(PORTS)
        or lines[-1] != [".ENDS", "nssoc_tx_cml_layout"]
    ):
        raise ValueError("Unexpected extracted circuit, ports or device inventory")
    devices = []
    ids = set()
    for row in lines[1:-1]:
        if row[0] in ids:
            raise ValueError("Duplicate device")
        ids.add(row[0])
        if row[0].startswith("Q"):
            terminals, model, fields = row[1:5], row[5], row[6:]
            expected = {"we", "le", "Nx", "m"}
            if model != "npn13G2":
                raise ValueError("Unsupported HBT")
        elif row[0].startswith("R") and row[3] == "ptap1":
            terminals, model, fields = row[1:3], row[3], row[4:]
            expected = {"A", "P"}
        elif row[0].startswith("R") and row[4] == "rsil":
            terminals, model, fields = row[1:4], row[4], row[5:]
            expected = {"w", "l", "ps", "b", "m"}
        else:
            raise ValueError("Unsupported extracted device")
        params = dict(field.split("=", 1) for field in fields)
        if len(params) != len(fields) or set(params) != expected:
            raise ValueError("Unexpected device parameters")
        if model == "rsil" and (params.pop("ps") != "0u" or params.pop("b") != "0"):
            raise ValueError("Only straight rsil geometry is supported")
        values = {key: number(value) for key, value in params.items()}
        devices.append(dict(id=row[0], nodes=terminals, model=model, values=values))
    if (
        sorted(d["model"] for d in devices)
        != ["npn13G2"] * 4 + ["ptap1"] + ["rsil"] * 2
    ):
        raise ValueError("Unexpected device classes/counts")
    tails = [
        d
        for d in devices
        if d["model"] == "npn13G2"
        and d["nodes"][1:3] == ["IREF", "AVSS"]
        and d["nodes"][0] != "IREF"
    ]
    if len(tails) != 1:
        raise ValueError("Ambiguous tail-current monitor attachment")
    tail = tails[0]
    nodes = sorted({node for d in devices for node in d["nodes"]} - set(PORTS))
    if len(nodes) != 2 or tail["nodes"][0] not in nodes:
        raise ValueError("Unexpected internal connectivity")
    mapping = {node: f"n{i}" for i, node in enumerate(nodes)} | {
        p: p.lower() for p in PORTS
    }
    mapping[tail["nodes"][0]] = "tail"
    out = [
        "* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut",
        "* SPDX-" + "License-Identifier: CERN-OHL-W-2.0",
        "* Device connectivity from compared GDS; interconnect RC NOT included.",
        ".subckt nssoc_tx_cml_rsil " + " ".join(p.lower() for p in PORTS),
    ]
    tap_resistance = None
    for index, d in enumerate(devices):
        ns = [mapping[n] for n in d["nodes"]]
        v = d["values"]
        model = d["model"]
        if model == "ptap1":
            tap_resistance = 1 / (
                v["A"] / tap_area_resistivity + v["P"] / tap_perimeter_resistivity
            )
            out.append(f"RTAP {' '.join(ns)} {tap_resistance:.16g}")
        elif model == "npn13G2":
            if d is tail:
                out.append(f"VTAIL tailmon {ns[2]} 0")
                ns[2] = "tailmon"
            out.append(
                f"XQ{index} {' '.join(ns)} {model} "
                + " ".join(f"{k}={value:.16g}" for k, value in v.items())
            )
        else:
            # Preserve extracted orientation and parameters, including SUB.
            if set(ns[:2]) not in ({"outp", "avdd"}, {"outn", "avdd"}):
                raise ValueError("Unexpected load connection")
            branch = "p" if "outp" in ns else "n"
            pos = ns.index("avdd")
            ns[pos] = "load" + branch
            out.append(f"VR{branch.upper()} avdd load{branch} 0")
            out.append(
                f"XR{branch.upper()} {' '.join(ns)} {model} "
                + " ".join(f"{k}={value:.16g}" for k, value in v.items())
                + " sw_et=1"
            )
    out.append(".ends nssoc_tx_cml_rsil")
    return "\n".join(out) + "\n", dict(
        node_mapping=mapping,
        tap_resistance_ohm=tap_resistance,
        source_devices=devices,
        qualified_pex=False,
        interconnect_parasitics_included=False,
        substrate_spatial_parasitics_included=False,
    )
