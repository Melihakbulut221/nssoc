#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native full collapsed-C-matrix audit for exact unreduced flat v2 exports.

Mutual capacitor endpoints remain at the original extraction anchors. Matching
this matrix is not validation of their spatial distribution or RF transient
accuracy, network simplification, Tdi, process corners, or qualified chip PEX.
"""

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re

V1 = Path(__file__).with_name("check_magic_intrinsic_cap_retirement.py")
V1_SHA = "3c1ff80133b3dc419a8e01536a2da0fc0d1d389f0fadb0842962214297053042"


def old_method():
    if hashlib.sha256(V1.read_bytes()).hexdigest() != V1_SHA:
        raise ValueError("Frozen v1 auditor changed")
    spec = importlib.util.spec_from_file_location("frozen_rc_auditor", V1)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit(ext, replacement, exported, native_log, baseline_ext, baseline_spice):
    old = old_method()
    require, close = old.require, old.close
    source = old.extraction(ext, allow_coupling=True)
    out = old.spice(exported)
    before = old.spice(baseline_spice)
    strip_timestamp = lambda p: [r for r in old.records(p) if r[0] != "timestamp"]
    require(strip_timestamp(ext) == strip_timestamp(baseline_ext), "Original intrinsic/coupling/geometry extraction changed")
    require(out["ports"] == before["ports"] == source["ports"], "Port order/identity changed")
    canonical = lambda rs: sorted((tuple(sorted((a, b))), v) for a, b, v in rs)
    require(canonical(out["resistors"]) == canonical(before["resistors"]), "Baseline resistance/topology changed")
    rows = old.records(replacement)
    arities = {"scale": 4, "subcap": 3, "rnode": 7, "resist": 4}
    require(all(r[0] in arities and len(r) == arities[r[0]] for r in rows), "Unsupported replacement record or arity")
    require([r[1:] for r in rows if r[0] == "scale"] == [["1000", "1", "0.5"]], "Only cscale=1 native units supported")
    subcaps = [r for r in rows if r[0] == "subcap"]
    require(len(subcaps) == len(source["caps"]) and {r[1] for r in subcaps} == set(source["caps"]), "Need exactly one retained-node retirement")
    require(all(close(-float(r[2]), source["caps"][r[1]]) for r in subcaps), "Wrong intrinsic retirement")
    points = {n: 0.0 for n in source["owner"]}
    rnodes = [r for r in rows if r[0] == "rnode"]
    require({r[1] for r in rnodes} == set(points), "Native replacement terminal set changed")
    for row in rnodes:
        require(float(row[2]) == 0 and math.isfinite(float(row[3])) and float(row[3]) >= 0,
                "Invalid native rnode ground C")
        require(all(str(int(v)) == v for v in row[4:]) and row[6] == "0", "Invalid rnode coordinates/type")
        points[row[1]] += float(row[3])
    for owner, value in source["caps"].items():
        require(close(sum(c for n, c in points.items() if source["owner"][n] == owner), value), "Distributed intrinsic ground C is not conserved")
    resistors = [(r[1], r[2], float(r[3])) for r in rows if r[0] == "resist"]
    require(canonical(resistors) == canonical(out["resistors"]), "Native/export resistor graph changed")
    for a, b, resistance in resistors:
        require(a in points and b in points and source["owner"][a] == source["owner"][b] and math.isfinite(resistance) and resistance > 0,
                "Wrong native resistor endpoint/value")
    for owner in source["caps"]:
        reached = {owner}
        while True:
            previous = reached.copy()
            for a, b, _ in resistors:
                if a in reached or b in reached:
                    reached.update((a, b))
            if reached == previous:
                break
        require(reached == {n for n, o in source["owner"].items() if o == owner}, "Disconnected native conductor")
    wanted_coupling, actual_coupling = {}, {}
    for row in old.records(ext):
        if row[0] == "cap" and float(row[3]):
            require(source["owner"][row[1]] != source["owner"][row[2]], "Unsupported same-conductor cap")
            key = tuple(sorted(row[1:3]))
            wanted_coupling[key] = wanted_coupling.get(key, 0.0) + float(row[3])
    actual_points = {n: 0.0 for n in points}
    for a, b, value in out["capacitors"]:
        if b == "sub":
            require(a in points, "Unknown ground capacitor endpoint")
            actual_points[a] += value * 1e18
        else:
            require(a in points and b in points and source["owner"][a] != source["owner"][b], "Unknown mutual capacitor endpoints")
            key = tuple(sorted((a, b)))
            actual_coupling[key] = actual_coupling.get(key, 0.0) + value * 1e18
    require(set(wanted_coupling) == set(actual_coupling) and all(close(value, actual_coupling[key]) for key, value in wanted_coupling.items()),
            "Original mutual capacitor anchor/value changed")
    require(all(close(value, actual_points[n]) for n, value in points.items()), "Per-node native ground C export mismatch")
    expected, actual = old.expected_matrix(source), old.matrix(source, out)
    require(all(close(expected[a][b], actual[a][b]) for a in expected for b in expected), "Full collapsed capacitance matrix mismatch")
    log = Path(native_log).read_text()
    require(not re.search(r"Orphaned node|Error in extracting node|Error: Node with no area", log), "Native extraction fallback/failure")
    markers = re.findall(r"^NSSOC_V2_INTRINSIC_DISTRIBUTION (\S+) total=(\S+) intrinsic=(\S+)$", log, re.M)
    # A log may also contain the independent uncoupled cell from a shared tiny
    # run. Only markers for this exact source's node identities are relevant;
    # duplicates for any relevant node remain invalid.
    markers = [r for r in markers if r[0] in source["caps"]]
    require(len(markers) == len(source["caps"]) and {r[0] for r in markers} == set(source["caps"]), "Missing/duplicate native unreduced branch witness")
    for name, total, intrinsic in markers:
        incident = sum(c for a, b, c in source["coupling"] if name in (a, b))
        require(close(float(intrinsic), source["caps"][name]) and close(float(total), source["caps"][name] + incident),
                "Native intrinsic/legacy-total component witness mismatch")
    return dict(status="PASS_CANONICAL_FLAT_CSCALE1_UNREDUCED_COUPLED_MATRIX_ONLY",
                expected_matrix_af=expected, actual_matrix_af=actual,
                native_ground_points_af=points, exported_ground_points_af=actual_points,
                retained_mutual_edges_af=[dict(a=k[0], b=k[1], capacitance=v) for k, v in sorted(actual_coupling.items())],
                ports=out["ports"], resistors_ohm=out["resistors"], native_component_witnesses=markers,
                qualified_pex=False, dynamic_rf_or_reduction_accuracy_validated=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("ext", "replacement", "exported", "native-log", "baseline-ext", "baseline-spice", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Fresh output receipt required")
    inputs = [args.ext, args.replacement, args.exported, args.native_log, args.baseline_ext, args.baseline_spice]
    result = audit(*inputs)
    result["inputs"] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs + [Path(__file__), V1]}
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
