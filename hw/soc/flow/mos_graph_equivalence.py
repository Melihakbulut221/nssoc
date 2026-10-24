# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove a complete MOS4 net bijection and exact device-edge multiset.

Refinement finds a candidate mapping; matching color counts alone never pass.
Every net and named port must map uniquely, and every MOS device must preserve
model, W/L, gate and bulk. Only drain/source interchange is allowed. Ambiguous
mapping is inconclusive and raises ValueError. Junction parasitics and RC/power
models are outside this connectivity proof.
"""

from collections import Counter, defaultdict
import math


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def load_mos_netlist(path):
    import klayout.db as db

    netlist = db.Netlist()
    netlist.read(str(path), db.NetlistSpiceReader())
    netlist.flatten()
    c = netlist.top_circuit()
    _require(c is not None, "Missing top circuit")
    nets = {n.expanded_name(): n.name for n in c.each_net()}
    pins = {c.net_for_pin(p.id()).expanded_name(): p.name() for p in c.each_pin()}
    devices = []
    maxerr = 0
    _require(
        len(nets) == sum(1 for _ in c.each_net())
        and len(pins) == sum(1 for _ in c.each_pin()),
        "Duplicate net or port identity",
    )
    for dev in c.each_device():
        cls = dev.device_class()
        _require(isinstance(cls, db.DeviceClassMOS4Transistor), "Non-MOS4 device")
        w, l = dev.parameter("W"), dev.parameter("L")
        _require(
            all(math.isfinite(x) and x > 0 for x in [w, l]), "Invalid MOS dimensions"
        )
        rw, rl = round(w, 12), round(l, 12)
        _require(rw > 0 and rl > 0, "Dimensions lost during normalization")
        maxerr = max(maxerr, abs(w - rw), abs(l - rl))
        _require(maxerr < 1e-12, "Excessive floating normalization")
        nodes = {
            t: dev.net_for_terminal(cls.terminal_id(t)).expanded_name()
            for t in ["D", "G", "S", "B"]
        }
        devices.append(dict(name=dev.name, model=cls.name, w=rw, l=rl, **nodes))
    return dict(
        nets=nets, pins=pins, devices=devices, maximum_float_normalization_um=maxerr
    )


def _graph(c):
    keys = [("n", n) for n in c["nets"]] + [("d", i) for i in range(len(c["devices"]))]
    indices = {k: i for i, k in enumerate(keys)}
    adj = [[] for k in keys]
    labels = []
    for kind, value in keys:
        if kind == "n":
            labels.append(("net", c["pins"].get(value, "")))
        else:
            dev = c["devices"][value]
            labels.append(("device", dev["model"], dev["w"], dev["l"]))
            for terminal in ["D", "G", "S", "B"]:
                a = indices[("d", value)]
                b = indices[("n", dev[terminal])]
                edge = "DS" if terminal in ["D", "S"] else terminal
                adj[a].append((edge, b))
                adj[b].append((edge, a))
    return keys, adj, labels


def prove_mos_graph(a, b):
    _require(a["devices"] and b["devices"], "No MOS devices")
    if (
        len(a["devices"]) != len(b["devices"])
        or len(a["nets"]) != len(b["nets"])
        or set(a["pins"].values()) != set(b["pins"].values())
    ):
        raise ValueError("Graph/pin inventory differs")
    graphs = [_graph(c) for c in [a, b]]

    def recolor(keys):
        ids = {}
        result = []
        for labels in keys:
            colors = []
            for label in labels:
                if label not in ids:
                    ids[label] = len(ids)
                colors.append(ids[label])
            result.append(colors)
        return result, len(ids)

    colors, classes = recolor([g[2] for g in graphs])
    iterations = 0
    for iterations in range(1, 121):
        if Counter(colors[0]) != Counter(colors[1]):
            raise ValueError("Refined graph classes differ")
        labels = [
            [
                (
                    colors[j][i],
                    tuple(
                        sorted((edge, colors[j][neighbor]) for edge, neighbor in adj[i])
                    ),
                )
                for i in range(len(adj))
            ]
            for j, (_, adj, _) in enumerate(graphs)
        ]
        colors, nextclasses = recolor(labels)
        if nextclasses == classes:
            break
        classes = nextclasses
    else:
        raise ValueError("Refinement iteration bound reached")
    if Counter(colors[0]) != Counter(colors[1]):
        raise ValueError("Final graph classes differ")
    maps = []
    for (keys, _, _), color in zip(graphs, colors):
        by = defaultdict(list)
        for (kind, n), v in zip(keys, color):
            if kind == "n":
                by[v].append(n)
        maps.append(by)
    ambiguous = [len(v) for v in maps[0].values() if len(v) != 1]
    if ambiguous:
        raise ValueError(
            "Cannot prove unique net bijection: " + str(Counter(ambiguous))
        )
    mapping = {nets[0]: maps[1][key][0] for key, nets in maps[0].items()}
    _require(
        len(mapping) == len(a["nets"]) and len(set(mapping.values())) == len(b["nets"]),
        "Incomplete net bijection",
    )
    _require(
        {mapping[n]: p for n, p in a["pins"].items()} == b["pins"], "Named ports moved"
    )

    def device_rows(c, m):
        return Counter(
            (
                x["model"],
                x["w"],
                x["l"],
                tuple(sorted([m[x["D"]], m[x["S"]]])),
                m[x["G"]],
                m[x["B"]],
            )
            for x in c["devices"]
        )

    if device_rows(a, mapping) != device_rows(b, {n: n for n in b["nets"]}):
        raise ValueError("Exact MOS edge multiset differs after mapping")
    return dict(
        status="EXACT_NET_BIJECTION_AND_MOS_EDGE_MULTISET",
        devices=len(a["devices"]),
        nets=len(mapping),
        ports=len(a["pins"]),
        iterations=iterations,
        maximum_float_normalization_um=max(
            a["maximum_float_normalization_um"], b["maximum_float_normalization_um"]
        ),
        mapping=mapping,
    )
