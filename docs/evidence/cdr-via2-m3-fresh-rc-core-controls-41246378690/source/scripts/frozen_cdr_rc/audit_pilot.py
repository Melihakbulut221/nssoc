# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Raw diagnostic R-component/device contraction and full C accounting.

Ownership comes from actual resistor edges plus original extraction nodes,
never from a generated-name prefix. No RF or process-corner qualification.
"""
from pathlib import Path
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
import math
import re
import shlex
import sys
import networkx as nx

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'scripts'))
import check_magic_hbt_multiplicity_v3 as h
from check_magic_coupled_cap_v2 import old_method


def require(ok, message):
    if not ok:
        raise ValueError(message)


def number(text):
    match = re.fullmatch(r'([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)([numkpf]?)', text.lower())
    require(match is not None, 'Unsupported native number')
    value = Decimal(match[1]) * dict(n=Decimal('1e-9'), u=Decimal('1e-6'), m=Decimal('1e-3'),
                                    k=Decimal('1e3'), p=Decimal('1e-12'), f=Decimal('1e-15'), **{'': Decimal(1)})[match[2]]
    require(value.is_finite(), 'Nonfinite number')
    return value


def parse_spice(text):
    rows = [row.split() for row in h.spice_lines(text)]
    require(rows[0][0].lower() == '.subckt' and rows[-1][0].lower() == '.ends', 'Single top required')
    rs, cs, ds, seen = [], [], [], set()
    for row in rows[1:-1]:
        require(row[0] not in seen, 'Duplicate element')
        seen.add(row[0])
        if row[0].startswith('C') and len(row) == 6 and row[-2:] == ['$', '**FLOATING']:
            row = row[:4]
        if row[0][0] in ('R', 'C') and len(row) == 4:
            (rs if row[0][0] == 'R' else cs).append((row[1], row[2], number(row[3])))
        else:
            require(row[0][0] in 'XQMDRC' and any('=' in token for token in row), 'Unknown native device')
            i = next(i for i, token in enumerate(row) if '=' in token)
            params = [token.split('=') for token in row[i:]]
            require(len({p[0] for p in params}) == len(params), 'Duplicate device parameter')
            ds.append((tuple(row[1:i-1]), row[i-1].lower(), tuple(sorted((k.lower(), number(v)) for k, v in params))))
    return dict(ports=rows[0][2:], resistors=rs, capacitors=cs, devices=ds)


def audit(root):
    root = Path(root)
    ext = next(root.glob('*.ext'))
    if ext.name.endswith('.res.ext'):
        ext = next(p for p in root.glob('*.ext') if not p.name.endswith('.res.ext'))
    replacement = ext.with_name(ext.stem + '.res.ext')
    inputs = [ext, replacement, root / 'baseline.spice', root / 'unreduced.spice', root / 'native.log']
    raw = [shlex.split(row) for row in ext.read_text().splitlines() if row.strip()]
    source_nodes = {row[1]: float(row[3]) for row in raw if row[0] in ('node', 'substrate')}
    substrate = [row[1] for row in raw if row[0] == 'substrate']
    require(len(substrate) == 1, 'Single actual substrate reference required')
    native_owners = dict((name, name) for name in source_nodes)
    for row in raw:
        if row[0] == 'equiv':
            require(row[1] in source_nodes and row[2] not in native_owners, 'Invalid intrinsic alias')
            native_owners[row[2]] = row[1]
    log = (root / 'native.log').read_text()
    require(not re.search(r'Missing (?:gate|substrate|terminal|source|drain)|Orphaned node|Error in extracting node|Error: Node with no area', log), 'Native terminal/resistance failure')
    for label in ('Total Nets', 'Nets extracted', 'Nets output'):
        values = re.findall(r'^' + re.escape(label) + r': (\d+)(?: .*)?$', log, re.M)
        require(values == [str(len(source_nodes))], 'Incomplete native conductor census')
    require(len(re.findall(r'^NSSOC_\S*UNREDUCED_COMPLETE$', log, re.M)) == 1,
            'Native unreduced completion marker missing or repeated')
    before = parse_spice((root / 'baseline.spice').read_text())
    after = parse_spice((root / 'unreduced.spice').read_text())
    source_ports = [row[1] for row in sorted((row for row in raw if row[0] == 'port'),
                                           key=lambda row: int(row[2]))]
    require(before['ports'] == after['ports'] == source_ports, 'Ports changed')
    require(not before['resistors'], 'Only modeled intrinsic resistors allowed in baseline')
    require(after['resistors'], 'No distributed resistance')
    graph = nx.Graph()
    graph.add_nodes_from(source_nodes)
    for alias, owner in native_owners.items():
        if alias != owner:
            graph.add_edge(alias, owner)
    for a, b, value in after['resistors']:
        require(a != b and value.is_finite() and value > 0, 'Invalid distributed resistor')
        graph.add_edge(a, b)
    for nodes, _, _ in after['devices']:
        graph.add_nodes_from(nodes)
    for a, b, _ in after['capacitors']:
        graph.add_nodes_from((a, b))
    owners = {}
    components = []
    for component in nx.connected_components(graph):
        anchors = component & set(source_nodes)
        require(len(anchors) == 1, 'Conductor open or short after native R extraction')
        owner = next(iter(anchors))
        owners.update(dict((node, owner) for node in component))
        components.append(dict(owner=owner, nodes=len(component)))
    expected = Counter((tuple(native_owners[n] for n in ns), model, params) for ns, model, params in before['devices'])
    actual = Counter((tuple(owners[n] for n in ns), model, params) for ns, model, params in after['devices'])
    require(expected == actual, 'Complete exact modeled-device contraction differs')
    replacement_rows = [shlex.split(row) for row in replacement.read_text().splitlines() if row.strip()]
    native_r = Counter((tuple(sorted(row[1:3])), number(row[3])) for row in replacement_rows if row[0] == 'resist')
    exported_r = Counter((tuple(sorted((a, b))), value) for a, b, value in after['resistors'])
    require(native_r == exported_r, 'Native/export resistor edge-value multiset differs')
    source_caps = defaultdict(float)
    for name, value in source_nodes.items():
        require(math.isfinite(value) and value >= 0, 'Invalid source cap')
        if value:
            require(name != substrate[0], 'Nonzero substrate intrinsic cap')
            source_caps[tuple(sorted((name, substrate[0])))] += value
    for row in raw:
        if row[0] == 'cap' and float(row[3]):
            source_caps[tuple(sorted((native_owners[row[1]], native_owners[row[2]])))] += float(row[3])
    actual_caps = defaultdict(float)
    for a, b, value in after['capacitors']:
        require(value >= 0, 'Negative exported cap')
        if value:
            require(owners[a] != owners[b], 'Nonzero same-conductor capacitor')
            actual_caps[tuple(sorted((owners[a], owners[b])))] += float(value) * 1e18
    close = old_method().close
    require(source_caps.keys() == actual_caps.keys(), 'Collapsed capacitance edge set differs')
    require(all(close(v, actual_caps[k]) for k, v in source_caps.items()), 'Collapsed capacitance value differs')
    return dict(status='PASS_DIAGNOSTIC_EXACT_DEVICE_R_CONTRACTION_AND_COLLAPSED_C_ONLY',
                ports=before['ports'], modeled_devices=sum(expected.values()),
                source_nodes=len(source_nodes), distributed_resistors=len(after['resistors']),
                components=sorted(components, key=lambda item: item['owner']),
                capacitance_edges=len(source_caps), matrix_entries=len(source_nodes)**2,
                substrate=substrate[0], ownership_from_actual_resistor_edges=True,
                all_device_terminals_and_values_exact=True, native_r_edges_and_values_exact=True,
                inputs={str(p): h.pin(p) for p in [*inputs, Path(__file__)]},
                raw_source_caps_af=[dict(a=k[0], b=k[1], value=v) for k, v in source_caps.items()],
                raw_collapsed_caps_af=[dict(a=k[0], b=k[1], value=v) for k, v in actual_caps.items()],
                point_of_attachment_or_rf_accuracy_qualified=False, full_bank_pex_qualified=False)


if __name__ == '__main__':
    result = audit(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'], result['modeled_devices'], result['distributed_resistors'])
