#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed audit of flat, uncoupled, cscale=1 native RC conservation.

This limited audit is not qualified PEX. It compares native source extraction,
replacement-network records and exported SPICE, without modifying any of them.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import shlex


def require(value, message):
    if not value:
        raise ValueError(message)


def close(a, b):
    # Native rnode %g has six significant digits; the reader stores floats.
    return math.isclose(a, b, rel_tol=3e-6, abs_tol=1e-4)


def records(path):
    return [
        shlex.split(line)
        for line in Path(path).read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def extraction(path, *, allow_coupling=False):
    rows = records(path)
    allowed = {
        "timestamp",
        "version",
        "tech",
        "style",
        "scale",
        "resistclasses",
        "port",
        "node",
        "equiv",
        "substrate",
        "cap",
    }
    require(
        all(r[0] in allowed for r in rows),
        "Noncanonical/hierarchical/device extraction",
    )
    scales = [r[1:] for r in rows if r[0] == "scale"]
    require(
        scales == [["1000", "1", "0.5"]],
        "Only exact source cscale=1 and flat native units supported",
    )
    require(
        [r[1:] for r in rows if r[0] == "style"] == [["ngspice()"]],
        "Wrong extraction style",
    )
    require(
        [r[1:] for r in rows if r[0] == "tech"] == [["ihp-sg13g2"]], "Wrong technology"
    )
    nodes = [r for r in rows if r[0] == "node"]
    require(
        nodes and len({r[1] for r in nodes}) == len(nodes),
        "Ambiguous/repeated original node names",
    )
    caps = {r[1]: float(r[3]) for r in nodes}
    require(
        all(math.isfinite(v) and v >= 0 for v in caps.values()), "Invalid intrinsic cap"
    )
    owner = {n: n for n in caps}
    for r in rows:
        if r[0] == "equiv":
            require(
                len(r) == 3 and r[1] in caps and r[2] not in owner,
                "Noncanonical original alias",
            )
            owner[r[2]] = r[1]
    ports = [
        r[1]
        for r in sorted((r for r in rows if r[0] == "port"), key=lambda r: int(r[2]))
    ]
    require(
        len(ports) == len(set(ports)) and set(ports) == set(owner),
        "Original ports/nodes do not close",
    )
    coupling = []
    for r in rows:
        if r[0] == "cap":
            require(
                len(r) == 4 and r[1] in owner and r[2] in owner,
                "Unknown coupling endpoint",
            )
            value = float(r[3])
            require(math.isfinite(value) and value >= 0, "Invalid coupling")
            if value:
                coupling.append((owner[r[1]], owner[r[2]], value))
    require(
        allow_coupling or not coupling,
        "Unsupported nonzero inter-conductor coupling: matrix not qualified",
    )
    return dict(caps=caps, owner=owner, ports=ports, coupling=coupling)


def spice(path, *, inspect_negative_control=False):
    ports = None
    block_name = None
    ended = False
    names = set()
    resistors, capacitors = [], []
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.startswith("*"):
            continue
        row = line.split()
        if row[0].lower() == ".subckt":
            require(
                ports is None and not ended and len(row) >= 3,
                "Multiple or invalid subcircuits",
            )
            block_name = row[1]
            ports = row[2:]
            require(len(ports) == len(set(ports)), "Duplicate port identity")
        elif row[0].lower() == ".ends":
            require(
                ports is not None
                and not ended
                and (len(row) == 1 or (len(row) == 2 and row[1] == block_name)),
                "Invalid or duplicate .ends",
            )
            ended = True
            continue
        else:
            require(ports is not None and not ended, "Element outside subcircuit")
            require(
                len(row) == 4 and row[0][0] in "RC", "Unexpected native SPICE element"
            )
            require(row[0].lower() not in names, "Duplicate native SPICE element ID")
            names.add(row[0].lower())
            value = float(row[3])
            require(
                math.isfinite(value)
                and (value >= 0 or (inspect_negative_control and row[0][0] == "C")),
                "Negative/nonfinite native element",
            )
            (resistors if row[0][0] == "R" else capacitors).append(
                (row[1], row[2], value)
            )
    require(ports is not None and ended, "Missing subcircuit/.ends")
    return dict(ports=ports, resistors=resistors, capacitors=capacitors)


def matrix(source, netlist):
    """Collapse only physically resistively connected original conductors."""
    owner = source["owner"]
    names = sorted(source["caps"])
    result = {a: {b: 0.0 for b in names} for a in names}
    for a, b, value in netlist["capacitors"]:
        if b == "sub":
            require(a in owner, "Unknown capacitor endpoint")
            result[owner[a]][owner[a]] += value * 1e18
        elif a == "sub":
            require(b in owner, "Unknown capacitor endpoint")
            result[owner[b]][owner[b]] += value * 1e18
        else:
            require(
                a in owner and b in owner and owner[a] != owner[b],
                "Unknown or internal capacitor",
            )
            x, y = owner[a], owner[b]
            result[x][x] += value * 1e18
            result[y][y] += value * 1e18
            result[x][y] -= value * 1e18
            result[y][x] -= value * 1e18
    return result


def expected_matrix(source):
    names = sorted(source["caps"])
    result = {
        a: {b: (source["caps"][a] if a == b else 0.0) for b in names} for a in names
    }
    for a, b, value in source["coupling"]:
        result[a][a] += value
        result[b][b] += value
        result[a][b] -= value
        result[b][a] -= value
    return result


def audit(ext, replacement, exported, baseline_spice=None):
    source = extraction(ext)
    out = spice(exported)
    require(out["ports"] == source["ports"], "Exported port order/identity changed")
    rows = records(replacement)
    require(
        [r[1:] for r in rows if r[0] == "scale"] == [["1000", "1", "0.5"]],
        "Replacement cscale/units changed",
    )
    require(
        all(r[0] in {"scale", "subcap", "rnode", "resist"} for r in rows),
        "Unsupported orphan/kill/device replacement",
    )
    arities = {"scale": 4, "subcap": 3, "rnode": 7, "resist": 4}
    require(
        all(len(r) == arities[r[0]] for r in rows),
        "Invalid native replacement record arity",
    )
    subcaps = [r for r in rows if r[0] == "subcap"]
    require(
        len(subcaps) == len(source["caps"])
        and {r[1] for r in subcaps} == set(source["caps"]),
        "Each retained canonical node needs exactly one retirement",
    )
    for r in subcaps:
        require(
            close(-float(r[2]), source["caps"][r[1]]),
            "Wrong intrinsic retirement amount",
        )
    distributed = {n: 0.0 for n in source["caps"]}
    rnodes = [r for r in rows if r[0] == "rnode"]
    require(
        {r[1] for r in rnodes} == set(source["owner"]),
        "Replacement terminal set changed",
    )
    point_caps = {n: 0.0 for n in source["owner"]}
    for r in rnodes:
        require(
            r[1] in source["owner"] and float(r[2]) == 0, "Invalid replacement node"
        )
        require(
            math.isfinite(float(r[3])) and float(r[3]) >= 0,
            "Invalid replacement node capacitance",
        )
        require(
            all(str(int(v)) == v for v in r[4:]) and r[6] == "0",
            "Invalid replacement node location/type",
        )
        distributed[source["owner"][r[1]]] += float(r[3])
        point_caps[r[1]] += float(r[3])
    require(
        all(close(distributed[n], c) for n, c in source["caps"].items()),
        "Distributed intrinsic C not conserved",
    )
    native_r = [(r[1], r[2], float(r[3])) for r in rows if r[0] == "resist"]
    canonical = lambda rs: sorted((tuple(sorted((a, b))), v) for a, b, v in rs)
    require(
        canonical(native_r) == canonical(out["resistors"]),
        "Exported resistance/topology differs",
    )
    for a, b, value in native_r:
        require(
            a in source["owner"]
            and b in source["owner"]
            and source["owner"][a] == source["owner"][b]
            and value > 0,
            "Wrong resistor connectivity",
        )
    for original in source["caps"]:
        members = {n for n, owner in source["owner"].items() if owner == original}
        reached = {original}
        while True:
            previous = reached.copy()
            for a, b, _ in native_r:
                if a in reached or b in reached:
                    reached.update((a, b))
            if previous == reached:
                break
        require(reached == members, "Disconnected replacement conductor")
    expected, actual = expected_matrix(source), matrix(source, out)
    exported_points = {n: 0.0 for n in source["owner"]}
    for a, b, value in out["capacitors"]:
        require(
            b == "sub" and a in exported_points,
            "Unexpected capacitor in uncoupled export",
        )
        exported_points[a] += value * 1e18
    require(
        all(close(point_caps[n], exported_points[n]) for n in point_caps),
        "Per-node distributed ground C differs from native rnode",
    )
    require(
        all(close(expected[a][b], actual[a][b]) for a in expected for b in expected),
        "Exported capacitance matrix not conserved",
    )
    if baseline_spice is not None:
        before = spice(baseline_spice)
        require(
            before["ports"] == out["ports"]
            and canonical(before["resistors"]) == canonical(out["resistors"]),
            "Baseline port/resistance changed",
        )
    return dict(
        status="PASS_UNCOUPLED_CANONICAL_FLAT_CSCALE1_ONLY",
        expected_matrix_af=expected,
        actual_matrix_af=actual,
        distributed_intrinsic_af=distributed,
        ports=out["ports"],
        resistors_ohm=out["resistors"],
        qualified_pex=False,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("ext", "replacement", "exported", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    ap.add_argument("--baseline-spice", type=Path)
    args = ap.parse_args()
    require(not args.out.exists(), "Fresh receipt required")
    result = audit(args.ext, args.replacement, args.exported, args.baseline_spice)
    result["inputs"] = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path(__file__), args.ext, args.replacement, args.exported]
        + ([args.baseline_spice] if args.baseline_spice else [])
    }
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
