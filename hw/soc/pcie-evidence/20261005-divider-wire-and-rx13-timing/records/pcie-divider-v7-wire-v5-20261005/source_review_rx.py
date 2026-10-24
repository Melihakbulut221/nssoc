# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source and saved-byte review; never imports EDA or the producer."""
import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

B = Path(__file__).resolve().parent
OLD = B.parent / 'pcie-divider-v7-wire-v4-20261005'
N = Path('/dev/shm/nssoc-div4-v7-wire-native-02')


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def read(path):
    return json.loads(Path(path).read_text())


freeze_pin = pin(B / 'geometry-source-freeze.json')
assert freeze_pin == dict(bytes=29425, sha256='779c81aa060df308487b80b317dbc89727c6716ba346b6816a1d994c7bfef199')
f = read(B / 'geometry-source-freeze.json')
assert len(f['inputs']) == 110
assert {p: pin(p) for p in f['inputs']} == f['inputs']
assert {p: pin(p) for p in f['producer_sources']} == f['producer_sources']
old_peer = read(OLD / 'geometry-source-only-peer.json')
assert old_peer['status'] == 'PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_GEOMETRY'
assert old_peer['findings'] == []
assert old_peer['freeze'] == pin(OLD / 'geometry-source-freeze.json')
bridges = read(B / 'geometry-source-bridge.json')
assert len(bridges) == 7
bridge_notes = []
for item in bridges:
    before, after = Path(item['before']['path']), Path(item['after']['path'])
    assert before.parent == OLD and after.parent == B
    assert before.name == after.name
    for key, path in [('before', before), ('after', after)]:
        assert pin(path) == {k: item[key][k] for k in ['bytes', 'sha256']}
        assert ''.join(op[key] for op in item['opcodes']).encode() == path.read_bytes()
    for op in item['opcodes']:
        assert op['tag'] in {'equal', 'replace', 'insert', 'delete'}
        if op['tag'] == 'equal':
            assert op['before'] == op['after']
    normalized = after.read_text().replace('nssoc-div4-v7-wire-geometry-05',
                                           'nssoc-div4-v7-wire-geometry-04')
    if after.name not in {'probe_wire_components.py', 'run_geometry.py'}:
        assert normalized == before.read_text()
        classification = 'Whole-byte identical except fresh scratch version, if present'
    else:
        classification = ('Only explicit unpurged cluster partition/output fields'
                          if after.name == 'probe_wire_components.py'
                          else 'Only fresh scratch and exact completed extraction/reader reuse gate')
    ast.parse(after.read_text())
    bridge_notes.append(dict(name=after.name, forward_inverse_full_bytes=True,
                             reviewed_change=classification))

# Inspect the actual saved ASCII native database, without invoking KLayout.
raw = (N / 'result.l2n').read_text()
assert raw.startswith('#%l2n-klayout\n')
raw_nets = [(int(i), name) for i, name in re.findall(r'^ N\((\d+) I\(([^)]+)\)', raw, re.M)]
assert len(raw_nets) == 72 and len(dict(raw_nets)) == 72
raw_ports = [(int(i), name) for i, name in re.findall(r'^ P\((\d+) I\(([^)]+)\)\)', raw, re.M)]
assert len(raw_ports) == 7 and len(dict(raw_ports)) == 7
raw_devices = re.findall(r'^ D\((\d+) D\$([^\s]+)\n(.*?)^ \)\n', raw, re.M | re.S)
assert len(raw_devices) == 91
native = {}
terminals = defaultdict(list)
for ident, cls, body in raw_devices:
    ident = int(ident)
    assert ident not in native
    model = cls.split('$')[0]
    terms = [(name, int(net)) for name, net in re.findall(r'^  T\((\S+) (\d+)\)$', body, re.M)]
    assert terms and len(dict(terms)) == len(terms)
    native[ident] = dict(model=model, terminals=terms)
    for name, net in terms:
        assert net in dict(raw_nets)
        terminals[net].append((ident, model, name))
assert Counter(v['model'] for v in native.values()) == dict(npn13G2=34, rppd=33, cap_cmim=6, ptap1=18)
assert sum(map(len, terminals.values())) == 283 and len(terminals) == 38
assert set(dict(raw_ports)) <= set(terminals)

# The reused inventories must be exact completed native outputs, with original
# method/input provenance retained rather than relabelled as freshly generated.
for name in ['native-pcell-inventory.json', 'device-location-geometry.json']:
    assert pin(B / name) == pin(OLD / name)
geo = read(B / 'device-location-geometry.json')
assert geo['method_sha256'] == pin(OLD / 'probe_device_locations.py')['sha256']
assert geo['inputs_sha256'] == {str(OLD / 'native-pcell-inventory.json'): pin(OLD / 'native-pcell-inventory.json')['sha256'],
                              str(N / 'result.l2n'): pin(N / 'result.l2n')['sha256']}
assert len(geo['devices']) == 91
assert len({d['pcell']['path'] for d in geo['devices']}) == 91
for device in geo['devices']:
    observed = native[device['native_id']]
    assert observed['model'] == device['model']
    assert observed['terminals'] == [(t['name'], t['native_cluster']) for t in device['terminals']]
inventory = read(B / 'native-pcell-inventory.json')
assert len(inventory) == 678
assert Counter(v['cell'].split('$')[0] for v in inventory) == dict(via_stack=587, npn13G2=34, rppd=33, cmim=6, ptap1=18)
assert {d['pcell']['path'] for d in geo['devices']} <= {v['path'] for v in inventory}

# Recount the diagnostic saved geometry against raw database terminals. This is
# a diagnostic cross-check, not retrospective acceptance of the failed V4 run.
diag = read(OLD / 'wire-component-geometry-diagnostic.json')
assert diag['status'] == 'DIAGNOSTIC_ONLY_NO_GEOMETRY_ACCEPTANCE'
assert diag['inputs'] == {p: pin(p) for p in diag['inputs']}
coverage = diag['native_net_coverage']
assert len(coverage) == 72
assert {r['native_cluster']: r['name'] for r in coverage} == dict(raw_nets)
assert len(diag['wire_components']) == 37
metal = {r['native_cluster'] for r in coverage if r['metal_area_dbu2']}
assert len(metal) == 37
assert metal == {r['native_cluster'] for r in diag['wire_components']}
aux = set(dict(raw_nets)) - set(terminals)
assert len(aux) == 34
assert not (aux & metal) and not (aux & set(dict(raw_ports)))
assert all(not r['wire_components'] for r in coverage if r['native_cluster'] in aux)
body = set(terminals) - metal
assert len(body) == 1
body_id = next(iter(body))
assert len(terminals[body_id]) == 85 and body_id not in dict(raw_ports)
assert Counter((model, name) for _, model, name in terminals[body_id]) == {
    ('npn13G2', 'S'): 34, ('rppd', 'rppd_sub'): 33, ('ptap1', 'WELL'): 18}
assert all(len(r['wire_components']) == 1 for r in coverage if r['native_cluster'] in metal)
for r in diag['wire_components']:
    area = sum(v['area_dbu2'] for v in r['layers'].values())
    matching = next(v for v in coverage if v['native_cluster'] == r['native_cluster'])
    assert area == matching['metal_area_dbu2']
assert diag['layers']['134']['explicitly_empty'] and diag['layers']['133']['explicitly_empty']

previous = read(OLD / 'geometry-execution.json')
assert previous['status'] == 'FAIL_GEOMETRY_RETAINED'
assert [(s['name'], s['execution']['returncode']) for s in previous['steps']] == [
    ('native_unsimplified_extraction', 0), ('probe_native_cells', 0),
    ('probe_device_locations', 0), ('probe_wire_components', 1)]
closed = []
for stage in previous['steps'][:3]:
    p = OLD / (stage['name'] + '.owned.json')
    receipt = read(p)
    assert receipt['status'] == 'HEALTHY'
    assert len(receipt['processes']) == 1
    proc = receipt['processes'][0]
    assert proc['status'] == 'REAPED_NO_LIVE_MEMBERS' and proc['returncode'] == 0
    assert not proc['members_at_leader_exit']
    assert pin(p)['sha256'] == stage['execution']['process_owner_sha256']
    assert pin(OLD / (stage['name'] + '.log'))['sha256'] == stage['execution']['log_sha256']
    closed.append(dict(name=stage['name'], owner=pin(p), identity=proc['identity']))
deck = (N / 'deck.log').read_text()
for phrase in ['NET_ONLY enabled: apply extraction netlist options and skip comparison.',
               'simplify: SKIPPED', 'combine_devices: SKIPPED', 'purge: SKIPPED',
               'purge_nets: SKIPPED', 'purge_devices: SKIPPED',
               'NSSOC_UNSIMPLIFIED_GEOMETRY_L2N_EXPORT_REQUESTED']:
    assert phrase in deck
assert previous['native_comparison_executed'] is False
assert not Path('/dev/shm/nssoc-div4-v7-wire-geometry-05').exists()
assert not (B / 'geometry-execution.json').exists()

result = dict(
    status='PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_GEOMETRY', findings=[],
    freeze=freeze_pin, method=pin(__file__), source_pins=f['producer_sources'],
    all_frozen_inputs_rehashed=110, full_forward_inverse_bridges=bridge_notes,
    parent_peer=pin(OLD / 'geometry-source-only-peer.json'),
    saved_native_inputs={str(p): pin(p) for p in [N / 'result.l2n', N / 'extracted.cir', N / 'deck.log']},
    independently_recounted_from_ascii_native_database=dict(
        raw_clusters=72, primitive_devices=91, terminals=283, public_ports=7,
        device_terminal_clusters=38, actual_metal_components=37,
        body_only_clusters=1, body_terminals=85,
        auxiliary_clusters_without_metal_device_terminals_or_public_ports=sorted(aux),
        all_auxiliary_native_clusters_retained=True),
    closed_reused_stages=closed,
    source_review=[
        'Every raw native net is visited and retained in coverage; no purge or device deletion.',
        'Auxiliary classification requires no terminal, metal area, wire owner, or public pin; all seven ports remain on terminal-connected clusters.',
        'All 283 native terminals, all 91 physical devices and 18 finite taps remain mandatory; source/native net maps are bijective over 38 electrical nets.',
        'All nonempty source metal/via regions remain union-equal, uniquely bound to native conductors. TopMetal2/TopVia2 are explicitly measured empty.',
        'Full terminal, public pin, parameter, source-ID and coordinate checks remain byte-identical apart from fresh output path.',
        'Runner reuses only exactly pinned completed N2 extraction and identical completed inventories, keeping original method/input provenance and failed V4 receipt.',
        'Private checker function AST cloning, CPU10, 2GiB AS, 80MiB own cap, 24MiB reserve, 1GiB entry, 512MiB continuous floor and complete/teardown stop guards remain unchanged.',
        'Fresh remaining geometry stages still execute under the frozen ProcessOwner. No healthy elapsed timeout; five-second failure cleanup.',
    ],
    reviewed_producer_or_native_execution=False,
    limitations='Source-only review plus independent saved ASCII/JSON cross-check; V4 remains failed. V5 geometry, terminal contact anchors and complete source bijection must actually pass before acceptance. No RC, distributed terminal model, substrate R, extracted timing, qualified PEX, main-chip or PHY closure is claimed.',
)
out = B / 'geometry-source-only-peer.json'
assert not out.exists()
out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(status=result['status'], receipt=str(out), **pin(out)), indent=2))
