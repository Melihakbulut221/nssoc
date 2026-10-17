#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compose exact native intrinsic devices and distributed wires, with open body boundary.

BODY_SUBSTRATE is deliberately NOT joined to any distributed metal node. WIRE_CREF
is the extractor capacitance reference, not an inferred supply or substrate. This
interface is an auditable integration pilot, not a closed or qualified PEX model.
"""

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    "anchors": "9b248bf7aa947046e09a01f0b129bf415a3221e4c4d64a567595d971eed7e64f",
    "devices": "570cd17e26d1019b65b99f85a707a7bcf579429f1ef280f9c640f4cba4469aa1",
    "geometry": "11066e966fb2504a8d9e50866d94ddf5a4ee3f5fa96ae38bced66e248147e25f",
    "native": "d815c9a91be0164ad8adb71c3810d65c2c09eaa496f142e0fdcdc2b21ee137a9",
    "wires": "10348e053767d226314f652df36b8f0df546c3d8e355086413852e3a423ac9c4",
}

MODEL_PINS = {
    "libs.tech/ngspice/models/resistors_mod.lib": "98fa5436f6df86dc1dd35e9f16383c4eba4c36d478d7eec203a0295dc1259e51",
    "libs.tech/ngspice/models/sg13g2_esd.lib": "4a4fb26a87f64bc6ed807f161cc7b3afaeb8d5ca7230b08ebba728e805caa925",
    "libs.tech/ngspice/models/sg13g2_hbt_mod.lib": "ae9288f885dd30fab24b07ed1e7e02e69eac9154022a0a6da576985183b0bd79",
    "libs.tech/ngspice/models/sg13g2_moshv_mod.lib": "d4b348b494998d7057bdde6fb111c60153d8b86175fafcfc6de461737e7a644b",
    "libs.tech/ngspice/models/capacitors_mod.lib": "94b569e695fd8a223a5a49a5b5a6b0d8a62408820bf0c2ed9dbcb0a8ab7d957e",
    "libs.tech/klayout/python/sg13g2_pycell_lib/ihp/utility_functions.py": "131cad3e7c52a5427cbe74a19934b58ed008ab02bc2b3b20bbe060f0c563802e",
    "libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json": "dce023dcf8dca1a7d875b6f71b5ce651b42f2dc3e9a21abb6de3997262273142",
}
# Names and orders are native extractor terminal identities, not guessed SPICE order.
NATIVE_ORDER = {
    "sg13_hv_pmos": ["S", "G", "D", "B"],
    "npn13G2": ["C", "B", "E", "S"],
    "rsil": ["rsil_1", "rsil_2", "rsil_sub"],
    "rppd": ["rppd_1", "rppd_2", "rppd_sub"],
    "cap_cmim": ["mim_top", "mim_btm"],
    "ptap1": ["TIE", "WELL"],
    "ntap1": ["TIE", "WELL"],
    "diodevdd_2kv": ["C", "B", "E"],
    "diodevss_2kv": ["C", "B", "E"],
}
MODEL_ORDER = dict(
    NATIVE_ORDER,
    sg13_hv_pmos=["D", "G", "S", "B"],
    diodevdd_2kv=["B", "E", "C"],
    diodevss_2kv=["C", "E", "B"],
)
CENSUS = {
    "npn13G2": 34,
    "rppd": 33,
    "cap_cmim": 6,
    "ptap1": 18,
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def pin(path):
    p = Path(path)
    return dict(
        bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()
    )


def statements(text):
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        if line.startswith("+"):
            require(bool(lines), "Unattached continuation")
            lines[-1] += " " + line[1:].strip()
        else:
            lines.append(line)
    return [line.split() for line in lines]


def number(value):
    match = re.fullmatch(
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z]*)", str(value)
    )
    require(match is not None, "Unsupported numeric token")
    factors = {
        "": 0,
        "t": 12,
        "g": 9,
        "meg": 6,
        "k": 3,
        "m": -3,
        "u": -6,
        "n": -9,
        "p": -12,
        "f": -15,
        "a": -18,
    }
    suffix = match[2].lower()
    require(suffix in factors, "Unknown unit")
    result = Decimal(match[1]) * Decimal(10) ** factors[suffix]
    require(result.is_finite(), "Nonfinite value")
    return result


def geometry_decimal(value):
    # Only the two observed pinned-divider JSON binary-float serialization artifacts.
    # Native LVS SPICE and the GDS grid carry the exact decimal geometry.
    text = str(value)
    text = {
        "38.400000000000006": "38.4",
        "12.700000000000001": "12.7",
    }.get(text, text)
    return Decimal(text)


def raw_native(text, devices):
    rows = statements(text)
    require(
        rows[0][0].upper() == ".SUBCKT" and rows[-1] == [".ENDS", rows[0][1]],
        "Native subcircuit shape",
    )
    native = {}
    for row in rows[1:-1]:
        match = re.fullmatch(r"[QMRCXD]\$(\d+)", row[0])
        require(match is not None, "Unexpected native element")
        key = int(match[1])
        require(key not in native, "Duplicate native device")
        native[key] = row
    require(set(native) == set(range(1, 92)), "Native device ID census")
    for d in devices:
        row = native[d["native_id"]]
        model = d["model"]
        order = NATIVE_ORDER[model]
        require(row[1 + len(order)] == model, "Native model changed")
        by = {r["name"]: r for r in d["terminals"]}
        require(set(by) == set(order), "Native named terminal census")
        require(
            [s.removeprefix("\\") for s in row[1 : 1 + len(order)]]
            == [by[n]["net"] for n in order],
            "Native terminal identity/order changed",
        )
        params = dict(s.split("=", 1) for s in row[2 + len(order) :])
        expected = dict(d["parameters"])
        require(set(params) == set(expected), "Native parameter census changed")
        for name, value in expected.items():
            exponent = (
                -12
                if name in ("A", "AS", "AD")
                else -6
                if name in ("w", "l", "we", "le", "ps", "P", "L", "W", "PS", "PD")
                else 0
            )
            require(
                number(params[name])
                == geometry_decimal(value) * Decimal(10) ** exponent,
                "Native geometry/value changed",
            )
    return rows[0][2:]


def wire_records(text):
    rows = statements(text)
    require(
        rows[0][:2] == [".subckt", "bank_wires"] and rows[-1] == [".ends"],
        "Wire wrapper changed",
    )
    records = []
    ids = set()
    for row in rows[1:-1]:
        require(len(row) == 4 and row[0][0] in "RC", "Unexpected wire element")
        require(row[0].lower() not in ids, "Duplicate wire element")
        ids.add(row[0].lower())
        require(row[1] != row[2] and number(row[3]) > 0, "Invalid wire element")
        records.append(row)
    require(
        Counter(r[0][0] for r in records) == {"R": 384, "C": 657}, "Wire element census"
    )
    return rows[0][2:], records


class Union:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while x != root:
            x, self.parent[x] = self.parent[x], root
        return root

    def join(self, a, b):
        self.parent[self.find(a)] = self.find(b)


def bindings(anchors, devices, geometry, wire_text):
    require(Counter(d["model"] for d in devices) == CENSUS, "Intrinsic census changed")
    require(
        [d["native_id"] for d in devices] == list(range(1, 92)), "Device identity order"
    )
    ports, records = wire_records(wire_text)
    by_label = {a["label"]: a for a in anchors["anchors"]}
    require(
        len(by_label) == len(ports) == 205 and set(ports) == set(by_label),
        "Actual wire port census",
    )
    graph = Union()
    for name, a, b, _ in records:
        if name.startswith("R"):
            graph.join(a, b)
    owners = {}
    component_root = {}
    for label, a in by_label.items():
        root = graph.find(label)
        component = a["wire_component"]
        require(root not in owners or owners[root] == component, "Actual wire short")
        require(
            component not in component_root or component_root[component] == root,
            "Actual wire open",
        )
        owners[root] = component
        component_root[component] = root
    require(
        len(owners) == 37 and set(owners.values()) == set(range(1, 38)),
        "Wire ownership census",
    )
    require(
        all(graph.find(n) in owners for n in graph.parent), "Unanchored resistor node"
    )
    for row in records:
        require(
            all(n == "sub" or n in graph.parent for n in row[1:3]),
            "Unknown wire capacitor node",
        )
    metal, body = {}, {}
    component_native = {
        r["component"]: r["native_cluster"] for r in geometry["wire_components"]
    }
    for label, a in by_label.items():
        if a["kind"] == "INTRINSIC_DEVICE_TERMINAL_REFERENCE":
            d = a["detail"]
            key = (d["device"], d["terminal"])
            require(
                key not in metal and d["wire_component"] == a["wire_component"],
                "Duplicate/wrong device anchor",
            )
            require(
                d["native_cluster"] == component_native[a["wire_component"]],
                "Device anchor conductor mismatch",
            )
            metal[key] = (label, d)
    for d in anchors["unmodeled_body_well_terminals"]:
        key = (d["device"], d["terminal"])
        require(key not in body and key not in metal, "Duplicate body anchor")
        body[key] = d
    require(len(metal) == 198 and len(body) == 85, "Metal/body census")
    require(
        Counter(r["native_cluster"] for r in body.values()) == {1: 85},
        "Body equivalence changed",
    )
    seen = set()
    ordinal = -1
    for device in devices:
        for terminal in device["terminals"]:
            ordinal += 1
            key = (device["native_id"], terminal["name"])
            seen.add(key)
            require(
                (key in metal) != (key in body), "Missing/duplicate physical terminal"
            )
            row = metal[key][1] if key in metal else body[key]
            if key in metal:
                require(
                    metal[key][0] == f"T{ordinal:04d}",
                    "Physical terminal ordinal changed",
                )
                anchor = by_label[metal[key][0]]
                require(
                    anchor["point_dbu"] == row["point_dbu"]
                    and anchor["metal"] == row["metal"],
                    "Physical reference point changed",
                )
            else:
                require(
                    row["native_geometry"] == terminal, "Body native geometry changed"
                )
            require(
                row["model"] == device["model"]
                and row["native_net"] == terminal["net"]
                and row["native_cluster"] == terminal["native_cluster"],
                "Device anchor identity changed",
            )
    require(seen == set(metal) | set(body), "Extra terminal anchor")
    return metal, body, records


def model_params(d, tech):
    p = d["parameters"]
    model = d["model"]
    um = lambda v: format(geometry_decimal(v), "f") + "u"
    if model == "npn13G2":
        require(p["m"] == 1, "Unsupported HBT multiplier")
        return dict(Nx=str(int(p["Nx"])), we=um(p["we"]), le=um(p["le"]))
    if model in ("rsil", "rppd"):
        require(p["m"] == 1 and p["b"] == 0, "Unsupported resistor geometry")
        return dict(w=um(p["w"]), l=um(p["l"]), ps=um(p["ps"]), b="0", m="1", sw_et="1")
    if model == "cap_cmim":
        require(
            geometry_decimal(p["A"])
            == geometry_decimal(p["w"]) * geometry_decimal(p["l"])
            and geometry_decimal(p["P"])
            == 2 * (geometry_decimal(p["w"]) + geometry_decimal(p["l"]))
            and p["m"] == 1,
            "MIM geometry attributes disagree",
        )
        return dict(w=um(p["w"]), l=um(p["l"]))
    if model == "sg13_hv_pmos":
        return {
            k.lower(): format(geometry_decimal(v), "f")
            + ("p" if k in ("AS", "AD") else "u" if k in ("L", "W", "PS", "PD") else "")
            for k, v in p.items()
        } | dict(ng="1", m="1")
    if model in ("diodevdd_2kv", "diodevss_2kv"):
        require(p == {"m": 1.0}, "ESD multiplier changed")
        return dict(m="1")
    require(
        model in ("ptap1", "ntap1") and p == {"A": 4.0, "P": 8.0},
        "Contact geometry changed",
    )
    # Exact PDK CbTapCalc equation, units SI. This is a contact compact model,
    # not a guessed 3D substrate resistivity/depth or spreading resistor.
    area = Decimal(str(p["A"])) * Decimal("1e-12")
    perim = Decimal(str(p["P"])) * Decimal("1e-6")
    resistance = 1 / (
        area / number(tech[model + "_raspec"]) + perim / number(tech[model + "_rpspec"])
    )
    return dict(R=str(resistance), w="2u", l="2u")


def compose(anchors, device_record, geometry, native_text, wire_text, tech):
    devices = device_record["devices"]
    native_ports = raw_native(native_text, devices)
    metal, body, records = bindings(anchors, devices, geometry, wire_text)
    public = {
        a["label"]: a["detail"]["name"]
        for a in anchors["anchors"]
        if a["kind"] == "PUBLIC_PORT_REFERENCE"
    }
    require(
        len(public) == 7 and set(public.values()) == set(native_ports),
        "Public port identity changed",
    )
    native_names = {
        r["component"]: r["native_name"] for r in geometry["wire_components"]
    }
    for a in anchors["anchors"]:
        if a["kind"] == "PUBLIC_PORT_REFERENCE":
            require(
                native_names[a["wire_component"]] == a["detail"]["name"],
                "Public port physical anchor changed",
            )
    require(len(set(public.values())) == 7, "Duplicate public name")

    def node(n):
        if n == "sub":
            return "WIRE_CREF"
        if n in public:
            return public[n]
        require(
            re.fullmatch(r"[TP]\d+(?:\.n\d+)?", n) is not None,
            "Unexpected native wire node spelling",
        )
        return "w_" + n

    mapping = {n: node(n) for r in records for n in r[1:3]}
    require(
        len(set(v.lower() for v in mapping.values())) == len(mapping),
        "Case-insensitive node collision",
    )
    ports = sorted(public.values()) + ["BODY_SUBSTRATE", "WIRE_CREF"]
    out = [
        "* Exact 91-device / 205-anchor integration PILOT. NOT closed body PEX.",
        "* BODY_SUBSTRATE requires an explicit external boundary assumption.",
        "* WIRE_CREF is NOT mapped to an intrinsic body/supply.",
        ".subckt nssoc_clock_div4_v7_power_v2_hybrid_open_v1 " + " ".join(ports),
    ]
    converted = []
    for d in devices:
        nets, terminal_rows = [], []
        for terminal in MODEL_ORDER[d["model"]]:
            key = (d["native_id"], terminal)
            if key in metal:
                label, witness = metal[key]
                net = node(label)
            else:
                witness = body[key]
                label = None
                require(witness["native_cluster"] == 1, "Only actual native divider substrate")
                net = "BODY_SUBSTRATE"
            nets.append(net)
            terminal_rows.append(
                dict(
                    terminal=terminal,
                    node=net,
                    anchor=label,
                    native_cluster=witness["native_cluster"],
                )
            )
        params = model_params(d, tech)
        line = " ".join(
            [
                f"XD{d['native_id']:04d}",
                *nets,
                d["model"],
                *[k + "=" + v for k, v in params.items()],
            ]
        )
        out.append(line)
        converted.append(
            dict(
                native_id=d["native_id"],
                model=d["model"],
                terminals=terminal_rows,
                native_parameters=d["parameters"],
                simulator_parameters=params,
                line=line,
            )
        )
    out += [" ".join([row[0], node(row[1]), node(row[2]), row[3]]) for row in records]
    out += [".ends nssoc_clock_div4_v7_power_v2_hybrid_open_v1", ""]
    result = dict(
        status="COMPOSED_OPEN_BODY_INTERFACE_NOT_CLOSED_FULL_PEX",
        intrinsic_devices=91,
        metal_terminal_anchors=198,
        body_well_terminals=85,
        finite_contacts=18,
        wire_components=37,
        public_ports=7,
        additional_model_boundary_ports=["BODY_SUBSTRATE", "WIRE_CREF"],
        native_named_terminal_and_parameter_match=True,
        all_wire_R_C_records_retained_exactly=True,
        substrate_to_distributed_metal_attachment_proven=False,
        closed_native_graph_equivalent=False,
        full_pex_qualified=False,
        simulator_smoke_tested=False,
        records=converted,
        wire_node_map=mapping,
        ports=ports,
        scope="Named-terminal conversion and exact RC wiring only; no 3D body spreading, device-wire coupling, RF or ESD stress qualification.",
    )
    return "\n".join(out), result


def verify_output(text, expected):
    # Exact generated statement comparison catches changed anchors, missing/extra
    # devices or wire edges, altered parameters, and body/return shorting.
    actual, wanted = statements(text), statements(expected)
    require(actual == wanted, "Hybrid native device/anchor/RC/body contract changed")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in PINS:
        ap.add_argument("--" + name, type=Path, required=True)
    ap.add_argument("--pdk", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    inputs = {k: getattr(args, k) for k in PINS}
    for k, p in inputs.items():
        require(pin(p)["sha256"] == PINS[k], "Frozen " + k + " changed")
    for name, digest in MODEL_PINS.items():
        require(
            pin(args.pdk / name)["sha256"] == digest,
            "Frozen model contract changed: " + name,
        )
    tech = json.loads(
        (
            args.pdk / "libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json"
        ).read_text()
    )["techParams"]
    text, result = compose(
        json.loads(args.anchors.read_text()),
        json.loads(args.devices.read_text()),
        json.loads(args.geometry.read_text()),
        args.native.read_text(),
        args.wires.read_text(),
        tech,
    )
    args.out.mkdir(parents=True, exist_ok=False)
    output = args.out / "hybrid-open.spice"
    output.write_text(text)
    verify_output(output.read_text(), text)
    result["inputs"] = {
        str(p): pin(p)
        for p in [Path(__file__), *inputs.values(), *[args.pdk / p for p in MODEL_PINS]]
    }
    result["outputs"] = {output.name: pin(output)}
    (args.out / "composition.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
