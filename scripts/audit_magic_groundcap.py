#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check a native Magic intrinsic-C reader A/B experiment, not RC qualification.

Preserve repeated rnode records: EFbuild adds their capacitances. Establish an
explicit bijection from unchanged physical MOS instances and terminal roles,
then compare every weighted resistor and MOS record. No resistor is collapsed
for this topology check. Only the subsequent per-net capacitance accounting
contracts resistor connectivity. Arbitrary spatial coupling is not verified.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import shlex

TERMINALS = (7, 8, 11, 14)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def rows(text):
    return [a for line in text.splitlines() if (a := shlex.split(line))]


def number(value):
    x = float(value)
    require(math.isfinite(x) and x >= 0, "Invalid native R/C value")
    return x


def source_inventory(records):
    result = Counter()
    for a in records:
        b = a.copy()
        if a[0] == "cap":
            b[1:3] = sorted(a[1:3])
            number(a[3])
        if a[0] in ("node", "substrate"):
            number(a[3])
        result[tuple(b)] += 1
    return result


def devices(records):
    result = {}
    for a in records:
        if a[0] != "device":
            continue
        require(len(a) == 17 and a[1] == "msubckt", "Unsupported MOS record")
        key = tuple(a[:7])
        require(key not in result, "Repeated physical MOS instance")
        result[key] = a
    require(bool(result), "No MOS instances")
    return result


def node_records(records):
    result = defaultdict(list)
    for a in records:
        if a[0] == "rnode":
            require(len(a) == 7, "Unsupported rnode record")
            number(a[3])
            result[a[1]].append(a)
    require(bool(result), "No distributed nodes")
    return result


def topology(records, mapping):
    result = Counter()
    for a in records:
        b = a.copy()
        if a[0] == "device":
            for k in TERMINALS:
                b[k] = mapping.get(a[k], a[k])
        elif a[0] == "resist":
            require(len(a) == 4 and number(a[3]) > 0, "Invalid resistor")
            b[1:3] = sorted(mapping.get(n, n) for n in a[1:3])
        elif a[0] == "killnode":
            require(len(a) == 2, "Invalid killnode")
        elif a[0] in ("rnode", "scale"):
            continue
        else:
            raise ValueError("Unsupported resistance record: " + a[0])
        result[tuple(b)] += 1
    return result


def bijection(before, after):
    old, new = devices(before), devices(after)
    require(old.keys() == new.keys(), "Physical MOS inventory changed")
    mapping = {}
    for key, a in old.items():
        b = new[key]
        for k in TERMINALS:
            require(
                b[k] not in mapping or mapping[b[k]] == a[k],
                "Inconsistent MOS terminal mapping",
            )
            mapping[b[k]] = a[k]
    old_nodes, new_nodes = node_records(before), node_records(after)
    for n in new_nodes:
        mapping.setdefault(n, n)
    require(len(set(mapping.values())) == len(mapping), "Non-bijective mapping")
    require({mapping[n] for n in new_nodes} == set(old_nodes), "Node set changed")
    for b, a in mapping.items():
        if a != b:
            aa = re.fullmatch(r"(.*)\.([nt])[0-9]+", a)
            bb = re.fullmatch(r"(.*)\.([nt])[0-9]+", b)
            require(
                aa is not None and bb is not None and aa.groups() == bb.groups(),
                "Named node or logical-net prefix changed",
            )
    require(
        topology(before, {}) == topology(after, mapping),
        "Exact weighted R/MOS/kill topology changed",
    )
    return mapping


def audit(source_before, rc_before, source_after, rc_after):
    src, new_src = rows(source_before), rows(source_after)
    before, after = rows(rc_before), rows(rc_after)
    require(
        source_inventory(src) == source_inventory(new_src),
        "Source geometry or capacitance inventory changed",
    )
    require(
        [a for a in before if a[0] == "scale"]
        == [a for a in after if a[0] == "scale"]
        == [["scale", "1000", "1", "0.5"]],
        "Unsupported or changed extraction scale",
    )
    mapping = bijection(before, after)
    old_nodes, new_nodes = node_records(before), node_records(after)
    intrinsic = {}
    for a in src:
        if a[0] in ("node", "substrate"):
            require(a[1] not in intrinsic, "Repeated source node")
            intrinsic[a[1]] = number(a[3])
    parent = {}

    def find(n):
        parent.setdefault(n, n)
        if parent[n] != n:
            parent[n] = find(parent[n])
        return parent[n]

    def union(a, b):
        parent[find(a)] = find(b)

    for a in src:
        if a[0] == "equiv":
            require(len(a) == 3, "Unsupported equivalence")
            union(a[1], a[2])
    for a in before:
        if a[0] == "resist":
            union(a[1], a[2])
    # Native generated suffixes identify their source net. Still require the
    # complete weighted topology above before using this naming convention.
    for n in old_nodes:
        stem = re.sub(r"\.[nt][0-9]+$", "", n)
        candidates = [s for s in (stem, stem + "#") if s in intrinsic]
        if candidates:
            require(len(candidates) == 1, "Ambiguous original net")
            union(n, candidates[0])
    expected = defaultdict(float)
    for n, cap in intrinsic.items():
        expected[find(n)] += cap
    sums = []
    for ns, mp in ((old_nodes, {}), (new_nodes, mapping)):
        groups = defaultdict(list)
        for n, records in ns.items():
            groups[find(mp.get(n, n))].extend(number(a[3]) for a in records)
        sums.append({k: math.fsum(v) for k, v in groups.items()})
    require(
        set(sums[0]) == set(sums[1]) and set(sums[0]) <= set(expected),
        "Distributed/source component correspondence incomplete",
    )
    undistributed = set(expected) - set(sums[0])
    killed = {find(a[1]) for a in before if a[0] == "killnode"}
    require(
        all(expected[n] == 0 and n not in killed for n in undistributed),
        "Nonzero or killed source node has no distribution",
    )
    for n in undistributed:
        sums[0][n] = sums[1][n] = 0.0
    checks = []
    for n in sorted(expected):
        delta = sums[1][n] - sums[0][n]
        error = delta - expected[n]
        require(
            abs(error) <= 0.01 + 1e-5 * expected[n],
            f"Ground-C increment not conserved for {n}: {error} aF",
        )
        checks.append(
            dict(
                node=n,
                original_ground_af=expected[n],
                baseline_af=sums[0][n],
                patched_af=sums[1][n],
                difference_error_af=error,
            )
        )
    geometry_changes = []
    for b, a in mapping.items():
        if b not in new_nodes:
            continue
        old_locations = sorted(tuple(x[4:]) for x in old_nodes[a])
        new_locations = sorted(tuple(x[4:]) for x in new_nodes[b])
        if old_locations != new_locations:
            geometry_changes.append(
                dict(
                    baseline_node=a,
                    patched_node=b,
                    baseline=old_locations,
                    patched=new_locations,
                )
            )
    return dict(
        status="PASS_NATIVE_INTRINSIC_C_READER_ACCOUNTING_ONLY",
        qualified_pex=False,
        spatial_capacitance_preservation_proven=False,
        manufacturing_approval=False,
        source_records_preserved=True,
        weighted_r_mos_topology_preserved=True,
        mapped_nodes=len(old_nodes),
        renamed_nodes=sum(a != b for b, a in mapping.items()),
        rnode_records=sum(map(len, old_nodes.values())),
        duplicate_rnode_names=[n for n, a in old_nodes.items() if len(a) > 1],
        changed_rnode_coordinate_records=geometry_changes,
        original_ground_total_af=math.fsum(expected.values()),
        distributed_increment_af=math.fsum(sums[1].values())
        - math.fsum(sums[0].values()),
        retained_zero_cap_nodes_without_distribution=sorted(undistributed),
        components=checks,
        scope="Exact source record inventory and weighted topology; per-net intrinsic C "
        "increment only. Does not prove coupled/spatial RC, corner accuracy or signoff.",
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for arg in ("source-before", "rc-before", "source-after", "rc-after"):
        ap.add_argument("--" + arg, type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    paths = [args.source_before, args.rc_before, args.source_after, args.rc_after]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    result = audit(*(p.read_text() for p in paths))
    require(
        all(
            hashlib.sha256(p.read_bytes()).hexdigest() == hashes[str(p)] for p in paths
        ),
        "Inputs changed during audit",
    )
    result["input_sha256"] = hashes
    with args.output.open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(result["status"])


if __name__ == "__main__":
    main()
