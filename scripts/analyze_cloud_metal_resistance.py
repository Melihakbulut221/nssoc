#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measure DC resistance of source-bound native wire graphs on hosted runners.

Unit-current metal-only diagnosis; capacitors are open and semiconductor
devices are excluded. This does not predict loaded operation or qualify PEX.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import urllib.request

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def parse(text):
    edges, devices, ports, names = [], {}, None, set()
    counts = {'npn13g2': 4, 'rppd': 3, 'ptap1': 2}
    for line in text.splitlines():
        row = line.split()
        if not row or row[0].startswith('*'):
            continue
        if row[0].lower() == '.subckt':
            assert ports is None
            ports = row[2:]
        elif row[0][0].upper() in ('R', 'X'):
            assert row[0] not in names
            names.add(row[0])
            if row[0][0].upper() == 'R':
                assert len(row) == 4 and row[1] != row[2]
                value = float(row[3])
                assert np.isfinite(value) and value > 0
                edges.append((row[0], row[1], row[2], value))
            else:
                found = [(i, item.lower()) for i, item in enumerate(row) if item.lower() in counts]
                assert len(found) == 1
                i, model = found[0]
                assert i == counts[model] + 1
                devices[row[0]] = dict(model=model, nodes=row[1:i], parameters=row[i+1:])
    assert ports and len(ports) == len(set(ports))
    return ports, devices, edges


def reduce_conductor_class(compact_text, wire_text, category, factor=0.01):
    """Causal experiment only: reduce actual metal R in one verified net class.

    The original model must be retained by the caller. No C, device, terminal,
    topology or simulation oracle changes. These artificial values are never
    evidence of a physical implementation or acceptance.
    """
    assert category in ('all', 'supply', 'return', 'inputs', 'internal', 'bias', 'outputs')
    assert np.isfinite(factor) and 0 < factor < 1
    cp, cd, ce = parse(compact_text)
    wp, wd, edges = parse(wire_text)
    assert cp == wp and not ce and edges and set(cd) == set(wd)
    parent = {}
    def root(node):
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node
    for _, a, b, _ in edges:
        parent[root(a)] = root(b)
    owners = {}
    logical_components = {}
    def anchor(logical, node):
        assert node in parent, ('Missing metal terminal', logical, node)
        component = root(node)
        owners.setdefault(component, set()).add(logical)
        logical_components.setdefault(logical, set()).add(component)
    for port in cp:
        anchor(port, port)
    for name, original in cd.items():
        actual = wd[name]
        assert (original['model'], original['parameters']) == (actual['model'], actual['parameters'])
        n = {'npn13g2': 3, 'rppd': 2, 'ptap1': 1}[original['model']]
        # Body/well aliases are not metal terminals. They must remain identical.
        assert original['nodes'][n:] == actual['nodes'][n:]
        for logical, node in zip(original['nodes'][:n], actual['nodes'][:n], strict=True):
            anchor(logical, node)
    assert set(owners) == {root(node) for node in parent}, 'Unanchored metal component'
    assert all(len(v) == 1 for v in owners.values()), 'Cross-conductor short'
    assert all(len(v) == 1 for v in logical_components.values()), 'Open conductor'
    def classify(logical):
        if logical == 'avdd': return 'supply'
        if logical == 'avss': return 'return'
        if logical == 'iref': return 'bias'
        if logical in ('ap', 'an', 'bp', 'bn', 'sp', 'sn'): return 'inputs'
        if logical in ('op', 'on'): return 'outputs'
        if logical == 'sub': return 'substrate'
        assert logical not in cp, ('Unknown external port', logical)
        return 'internal'
    mapping = {}
    for name, a, b, value in edges:
        assert root(a) == root(b)
        logical = next(iter(owners[root(a)]))
        mapping[name] = dict(conductor=logical, category=classify(logical), original_ohms=value)
    lines, selected = [], {}
    for line in wire_text.splitlines(keepends=True):
        fields = line.split()
        if fields and fields[0] in mapping:
            item = mapping[fields[0]]
            if category == 'all' or item['category'] == category:
                value = item['original_ohms'] * factor
                assert np.isfinite(value) and 0 < value < item['original_ohms']
                selected[fields[0]] = dict(item, diagnostic_ohms=value)
                fields[3] = format(value, '.17g')
                line = ' '.join(fields) + ('\n' if line.endswith('\n') else '')
        lines.append(line)
    assert selected, 'No metal resistors selected'
    mutated = ''.join(lines)
    mp, md, me = parse(mutated)
    assert mp == wp and md == wd and [e[:3] for e in me] == [e[:3] for e in edges]
    # Exact preservation of C, native-device and other non-R lines.
    non_r = lambda text: [line for line in text.splitlines(keepends=True)
                          if not line.split() or line.split()[0] not in mapping]
    assert non_r(mutated) == non_r(wire_text)
    return mutated, dict(category=category, factor=factor,
        original_sha256=hashlib.sha256(wire_text.encode()).hexdigest(),
        mutated_sha256=hashlib.sha256(mutated.encode()).hexdigest(),
        resistors=len(edges), conductors=len(owners), selected_resistors=selected,
        scope='Artificial metal-R sensitivity only; actual geometry and native PDK coefficients unchanged. Not physical or PHY acceptance.')


def resistance(edges, reference, targets):
    """Solve one grounded component for all requested unit-current injections."""
    adjacency = {}
    for _, a, b, r in edges:
        assert a != b and np.isfinite(r) and r > 0
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    assert reference in adjacency and len(targets) == len(set(targets))
    reached, todo = {reference}, [reference]
    while todo:
        for n in adjacency[todo.pop()] - reached:
            reached.add(n)
            todo.append(n)
    assert set(targets) <= reached and reference not in targets
    nodes = sorted(reached - {reference})
    index = {n: i for i, n in enumerate(nodes)}
    matrix = np.zeros((len(nodes), len(nodes)))
    selected = [e for e in edges if e[1] in reached]
    for _, a, b, r in selected:
        g = 1 / r
        for n in (a, b):
            if n != reference:
                matrix[index[n], index[n]] += g
        if a != reference and b != reference:
            matrix[index[a], index[b]] -= g
            matrix[index[b], index[a]] -= g
    rhs = np.zeros((len(nodes), len(targets)))
    for column, target in enumerate(targets):
        rhs[index[target], column] = 1
    voltage = np.linalg.solve(matrix, rhs)
    assert np.isfinite(voltage).all()
    residual = float(np.max(np.abs(matrix @ voltage - rhs)))
    assert residual < 1e-7, residual
    reports = {}
    for column, target in enumerate(targets):
        value = float(voltage[index[target], column])
        energy = []
        for name, a, b, r in selected:
            va = 0 if a == reference else voltage[index[a], column]
            vb = 0 if b == reference else voltage[index[b], column]
            energy.append(dict(name=name, nodes=[a, b], ohms=r,
                               unit_current_power_w=float((va-vb)**2/r)))
        total = sum(e['unit_current_power_w'] for e in energy)
        assert value > 0 and np.isclose(total, value, rtol=1e-7, atol=1e-10)
        reports[target] = dict(effective_ohms=value, dissipated_w_at_1a=total,
            largest_power_edges=sorted(energy, key=lambda e: e['unit_current_power_w'], reverse=True)[:8])
    # The same inverse-Laplacian columns also measure resistance between
    # every terminal pair, without choosing an electrical reference for it.
    green = voltage[[index[n] for n in targets], :]
    assert np.allclose(green, green.T, rtol=1e-7, atol=1e-10)
    pairs = []
    for i, first in enumerate(targets):
        pairs.append(dict(nodes=[reference, first], effective_ohms=reports[first]['effective_ohms']))
        for j in range(i+1, len(targets)):
            value = float(green[i, i]+green[j, j]-green[i, j]-green[j, i])
            assert value > 0
            pairs.append(dict(nodes=[first, targets[j]], effective_ohms=value))
    return dict(nodes=len(nodes)+1, edges=len(selected), kcl_residual_a=residual, terminals=reports,
                terminal_pairs=sorted(pairs, key=lambda p: p['effective_ohms'], reverse=True))


def analyze(spec):
    receipt = spec['receipt']
    raw = urllib.request.urlopen(receipt['url'], timeout=120).read()
    assert len(raw) == receipt['bytes'] and hashlib.sha256(raw).hexdigest() == receipt['sha256']
    models = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        report = archive.extractfile('cloud-tx-layout-composition/result.json').read()
        assert hashlib.sha256(report).hexdigest() == spec['summary_sha256']
        report = json.loads(report)
        assert report['status'] == 'PASS_SOURCE_BOUND_NATIVE_DEVICE_WIRE_COMPOSITION_REQUIRES_TRANSIENT'
        assert report['outputs'] == spec['outputs'] and report['variant'] == spec['variant']
        for name, digest in spec['outputs'].items():
            data = archive.extractfile('cloud-tx-layout-composition/' + name).read()
            assert hashlib.sha256(data).hexdigest() == digest
            models[name] = parse(data.decode())
    cp, cd, ce = models['mux54-compact01.spice']
    wp, wd, edges = models['mux54-wire01.spice']
    assert not ce and len(edges) == spec['counts']['R'] and set(cd) == set(wd)
    assert len(cd) == spec['counts']['devices'] == 54
    groups = {}
    for name, device in cd.items():
        actual = wd[name]
        assert (device['model'], device['parameters']) == (actual['model'], actual['parameters'])
        # Intrinsic body/well aliases are explicitly outside metal-only graph.
        count = {'npn13g2': 3, 'rppd': 2, 'ptap1': 1}[device['model']]
        for pin, (logical, node) in enumerate(zip(device['nodes'][:count], actual['nodes'][:count], strict=True)):
            groups.setdefault(logical, {}).setdefault(node, []).append(dict(device=name, model=device['model'], pin=pin))
    measured, internal = {}, {}
    for port, terminals in groups.items():
        if port in cp:
            assert port in wp and port not in terminals
            measured[port] = resistance(edges, port, sorted(terminals))
            for node, labels in terminals.items():
                measured[port]['terminals'][node]['device_pins'] = labels
        else:
            ordered = sorted(terminals)
            assert len(ordered) >= 2
            internal[port] = resistance(edges, ordered[0], ordered[1:])
            internal[port]['device_pins'] = terminals
            internal[port]['grounded_calculation_node'] = ordered[0]
    assert {'avdd', 'avss', 'iref'} <= set(measured)
    return dict(source=spec, ports=measured, internal_conductors=internal)


def main():
    assert os.environ.get('GITHUB_ACTIONS') == 'true', 'Hosted analysis only'
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', choices=('kelvin', 'kelvin-short', 'kelvin-short-vias', 'kelvin-dense', 'kelvin-dense-wide'), required=True)
    args = parser.parse_args()
    path = ROOT / 'docs/evidence' / f'pcie-final-v5-{args.profile}-composition-20261013.json'
    output = Path('cloud-metal-resistance')
    output.mkdir(exist_ok=False)
    result = dict(status='RUNNING', profile=args.profile, adopted=False,
        scope='DC metal-only unit-current graph diagnosis. Capacitors open; devices excluded. No loaded waveform, RF/body or qualified PEX/PHY acceptance.')
    try:
        result['measurement'] = analyze(json.loads(path.read_text()))
        result['status'] = 'PASS_SOURCE_BOUND_METAL_DC_DIAGNOSIS_NOT_ACCEPTANCE'
    except BaseException as error:
        result.update(status='FAIL_DIAGNOSIS', error=repr(error))
        raise
    finally:
        (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
