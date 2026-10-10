# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate literal resistor reader/BFS; imports no producer or graph package."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json

B = Path(__file__).resolve().parent
N = Path('/dev/shm/nssoc-div4-v7-wire-rc-01/wires.spice')
A = B.parent.parent / 'pcie-divider-v7-wire-v5-20261005/anchors.json'


def pin(p):
    return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())


raw = N.read_text()
resistors = [row.split() for row in raw.splitlines() if row.startswith('R')]
assert len(resistors) == 312 and all(len(row) == 4 for row in resistors)
assert len({row[0] for row in resistors}) == len(resistors)
anchors = {r['label']: r for r in json.loads(A.read_text())['anchors']}
assert len(anchors) == 205


def components(edges):
    graph = defaultdict(set)
    for label in anchors:
        graph[label]
    for _, a, b, _ in edges:
        graph[a].add(b)
        graph[b].add(a)
    unseen = set(graph)
    result = []
    while unseen:
        pending = [min(unseen)]
        found = set()
        while pending:
            n = pending.pop()
            if n in found:
                continue
            found.add(n)
            pending.extend(graph[n] - found)
        unseen -= found
        result.append(found)
    return result


before = components(resistors)
after = components(resistors[1:])
first = resistors[0]
original = next(c for c in before if first[1] in c)
assert first[2] in original
split = [c for c in after if c & original]
assert len(split) == 2 and set.union(*split) == original
assert not set.intersection(*split)
assert all(set(c) & set(anchors) for c in split)
owner = {anchors[n]['wire_component'] for n in original if n in anchors}
assert len(owner) == 1
summary = dict(
    status='PASS_INDEPENDENT_LITERAL_BFS_FIRST_R_IS_A_PROBE_DISCONNECTING_BRIDGE',
    method=pin(Path(__file__)), inputs={str(p): pin(p) for p in [N, A]},
    removed_resistor=dict(name=first[0], a=first[1], b=first[2], ohms=first[3]),
    physical_wire_component=next(iter(owner)),
    original_component=sorted(original), after_split_components=[sorted(c) for c in split],
    affected_actual_anchors={n: anchors[n] for n in sorted(original & set(anchors))},
    total_resistor_components_before=len(before), total_resistor_components_after=len(after),
    connected_components_before=sum(len(c) > 1 for c in before),
    connected_components_after=sum(len(c) > 1 for c in after),
    isolated_actual_anchors_after=sorted(next(iter(c)) for c in after if len(c) == 1 and next(iter(c)) in anchors),
    expected_earlier_strict_rejection='Physical wire R graph open or incomplete',
    original_native_files_modified=False, native_executed=False,
)
(B / 'first-resistor-witness.json').write_text(json.dumps(summary, indent=2) + '\n')
print(summary['status'], first, summary['after_split_components'])
