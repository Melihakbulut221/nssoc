#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Full flat-device-bank C accounting only; no resistance or RF qualification."""
import argparse
from collections import Counter
import hashlib
import math
from pathlib import Path
import shlex

import check_magic_hbt_multiplicity_v3 as h
from check_magic_coupled_cap_v2 import old_method

MODELS = {'npn13g2': 122, 'ptap1': 108, 'ntap1': 1, 'rppd': 57, 'rsil': 24,
          'cap_cmim': 6, 'sg13_hv_pmos': 1, 'diodevdd_2kv': 16, 'diodevss_2kv': 16}


def audit(ext_text, spice_text):
    old = old_method()
    require, close = old.require, old.close
    records = [shlex.split(line) for line in ext_text.splitlines() if line.strip()]
    require(all(row[0] in {'timestamp', 'version', 'tech', 'style', 'scale', 'resistclasses',
                          'parameters', 'port', 'node', 'substrate', 'device', 'equiv', 'cap'}
                for row in records), 'Unknown or hierarchical native extraction record')
    require([row[1:] for row in records if row[0] == 'scale'] == [['1000', '1', '0.5']],
            'Unchanged native cscale1 required')
    require([row[1:] for row in records if row[0] == 'style'] == [['ngspice()']], 'Wrong native style')
    require([row[1:] for row in records if row[0] == 'tech'] == [['ihp-sg13g2']], 'Wrong native technology')
    substrate = [row for row in records if row[0] == 'substrate']
    require(len(substrate) == 1 and substrate[0][1] == 'ESD_RETURN' and float(substrate[0][3]) == 0,
            'Exact separately named native substrate reference required')
    nodes = [row for row in records if row[0] in ('node', 'substrate')]
    caps = {row[1]: float(row[3]) for row in nodes}
    require(len(caps) == len(nodes) == 210 and all(math.isfinite(v) and v >= 0 for v in caps.values()),
            'Duplicate/nonfinite/negative source node')
    owner = {name: name for name in caps}
    for row in records:
        if row[0] == 'equiv':
            require(len(row) == 3 and row[1] in caps and row[2] not in owner, 'Ambiguous source alias')
            owner[row[2]] = row[1]
    port_rows = [row for row in records if row[0] == 'port']
    require(len({row[2] for row in port_rows}) == len(port_rows), 'Duplicate native port ordinal')
    ports = [row[1] for row in sorted(port_rows, key=lambda row: int(row[2]))]
    require(len(ports) == len(set(ports)) == 56 and set(ports) <= set(owner), 'Exact56 source ports required')
    edges = {}

    def accumulate(target, a, b, value):
        require(a in owner and b in owner and math.isfinite(value) and value >= 0,
                'Invalid capacitance endpoint/value')
        a, b = owner[a], owner[b]
        require(a != b or value == 0, 'Unsupported nonzero same-conductor capacitance')
        if value:
            pair = tuple(sorted((a, b)))
            target[pair] = target.get(pair, 0.0) + value

    for name, value in caps.items():
        accumulate(edges, name, 'ESD_RETURN', value)
    for row in records:
        if row[0] == 'cap':
            require(len(row) == 4, 'Malformed source mutual capacitor')
            accumulate(edges, row[1], row[2], float(row[3]))
    actual, models, seen, floating = {}, Counter(), set(), []
    lines = [line.split() for line in h.spice_lines(spice_text)]
    require(lines[0][0].lower() == '.subckt' and lines[-1][0].lower() == '.ends', 'Single native subcircuit required')
    require(len(lines[-1]) in (1, 2) and (len(lines[-1]) == 1 or lines[-1][1] == lines[0][1]), 'Wrong native .ends name')
    require(lines[0][2:] == ports, 'Native port order or identity changed')
    for row in lines[1:-1]:
        require(row[0].lower() not in seen, 'Duplicate native element name')
        seen.add(row[0].lower())
        if len(row) == 6 and row[0].startswith('C') and row[4:] == ['$', '**FLOATING']:
            floating.append(row[0])
            row = row[:4]
        if row[0].startswith('C') and len(row) == 4:
            accumulate(actual, row[1], row[2], float(row[3]) * 1e18)
        else:
            require(row[0][0] in 'XQRMDC' and any('=' in token for token in row), 'Unsupported native element')
            index = next(i for i, token in enumerate(row) if '=' in token)
            require(all(name in owner for name in row[1:index-1]), 'Unknown native device terminal')
            models[row[index-1].lower()] += 1
    require(dict(models) == MODELS, 'All351 original modeled devices required')
    require(set(actual) == set(edges) and all(close(value, actual[key]) for key, value in edges.items()),
            'Complete native capacitance edge accounting mismatch')
    names = sorted(caps)
    wanted = {name: {other: 0.0 for other in names} for name in names}
    measured = {name: {other: 0.0 for other in names} for name in names}
    for target, network in ((wanted, edges), (measured, actual)):
        for (a, b), value in network.items():
            target[a][a] += value
            target[b][b] += value
            target[a][b] -= value
            target[b][a] -= value
    require(all(close(wanted[a][b], measured[a][b]) for a in names for b in names),
            'Full210-node capacitance matrix differs')
    return dict(status='PASS_COMPLETE_BANK_BASELINE_CAPACITANCE_ACCOUNTING_ONLY',
                native_floating_capacitor_annotations=floating, native_reference='ESD_RETURN', nodes=len(names), ports=ports, device_models=dict(models),
                matrix_entries_compared=len(names)**2, source_intrinsic_af=caps,
                source_edges_af=[dict(a=a, b=b, value=value) for (a, b), value in sorted(edges.items())],
                exported_edges_af=[dict(a=a, b=b, value=value) for (a, b), value in sorted(actual.items())],
                tolerance='Frozen native six-significant-digit serialization guard: rel3e-6/abs1e-4 aF; no new tolerance.',
                reference_node_not_short_to_avss=True, unreduced_resistance_qualified=False,
                requires_independent_device_graph_audit=True, qualified_pex=False)


def main():
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('ext', 'spice', 'out'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    inputs = [args.ext, args.spice, Path(__file__), Path(h.__file__),
              Path(__file__).with_name('check_magic_coupled_cap_v2.py'),
              Path(__file__).with_name('check_magic_intrinsic_cap_retirement.py')]
    pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    result = audit(args.ext.read_text(), args.spice.read_text())
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != value for p, value in pins.items()):
        raise ValueError('Inputs changed during raw audit')
    result['inputs'] = pins
    with args.out.open('x') as f:
        f.write(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
