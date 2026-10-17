"""Read-only effective-R diagnostic on actual exported resistor multigraphs.

This solves a one-amp small-signal mathematical test between each real rail
anchor and its public port. It does not assert a real operating current,
voltage droop, RF impedance, substrate model or transient acceptance.
"""
from pathlib import Path
import hashlib
import json
import math
import os
import numpy as np

B = Path(__file__).resolve().parent

def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())

def analyze(geometry, raw):
    anchors = json.loads((geometry / 'anchors.json').read_text())['anchors']
    resistors = []
    neighbors = {}
    for line in raw.read_text().splitlines():
        f = line.split()
        if not f or not f[0].startswith('R'):
            continue
        assert len(f) == 4
        x, y, r = f[1], f[2], float(f[3])
        assert x != y and math.isfinite(r) and r > 0
        resistors.append((x, y, r))
        neighbors.setdefault(x, set()).add(y)
        neighbors.setdefault(y, set()).add(x)
    result = {}
    for name in ['AVSS', 'DIV_AVDD']:
        public = [a for a in anchors if a['kind'] == 'PUBLIC_PORT_REFERENCE' and a['detail']['name'] == name]
        assert len(public) == 1
        source = public[0]['label']
        component = public[0]['wire_component']
        seen, pending = {source}, [source]
        while pending:
            for node in neighbors[pending.pop()]:
                if node not in seen:
                    seen.add(node)
                    pending.append(node)
        witnesses = [a for a in anchors if a['wire_component'] == component]
        assert {a['label'] for a in witnesses} <= seen
        assert not {a['label'] for a in anchors if a['wire_component'] != component} & seen
        nodes = sorted(seen - {source})
        index = {n: i for i, n in enumerate(nodes)}
        matrix = np.zeros((len(nodes), len(nodes)))
        for x, y, r in resistors:
            if x not in seen:
                continue
            assert y in seen
            conductance = 1 / r
            for node in [x, y]:
                if node != source:
                    matrix[index[node], index[node]] += conductance
            if source not in [x, y]:
                matrix[index[x], index[y]] -= conductance
                matrix[index[y], index[x]] -= conductance
        inverse = np.linalg.solve(matrix, np.eye(len(nodes)))
        residual = float(np.max(np.abs(matrix @ inverse - np.eye(len(nodes)))))
        assert np.isfinite(inverse).all() and residual < 1e-6
        diagonal = np.diag(inverse)
        assert (diagonal > 0).all()
        values = [dict(label=a['label'], kind=a['kind'], detail=a['detail'],
                       effective_R_ohm=0.0 if a['label'] == source else float(diagonal[index[a['label']]]))
                  for a in witnesses]
        result[name] = dict(public_anchor=source, component=component,
                            resistor_nodes=len(seen), solve_residual=residual,
                            max_anchor_effective_R_ohm=max(v['effective_R_ohm'] for v in values),
                            actual_anchor_values=values)
    return result

assert os.sched_getaffinity(0) == {10}
cases = {
    'original': (B.parent / 'pcie-divider-v7-wire-v5-20261005',
                 Path('/dev/shm/nssoc-div4-v7-wire-rc-01/wires.spice')),
    'power_v2': (B.parent / 'pcie-divider-v7-power-v2-wire-v2-20261006',
                 Path('/dev/shm/nssoc-div4-v7-power-v2-wire-rc-01/wires.spice')),
}
inputs = {str(p): pin(p) for geometry, raw in cases.values() for p in [geometry / 'anchors.json', raw]}
result = dict(status='READ_ONLY_EFFECTIVE_RESISTANCE_DIAGNOSTIC',
              inputs=inputs, method=pin(__file__),
              cases={name: analyze(*args) for name, args in cases.items()},
              native_simulation=False, operating_voltage_or_current_predicted=False,
              scope=__doc__)
assert inputs == {p: pin(p) for p in inputs}
out = B / 'rail-resistance-comparison.json'
assert not out.exists()
out.write_text(json.dumps(result, indent=2) + '\n')
print({name: {rail: r['max_anchor_effective_R_ohm'] for rail, r in values.items()}
       for name, values in result['cases'].items()})
