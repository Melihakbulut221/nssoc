# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-only independent V9 RC derivative review; no reviewed imports."""
import ast
import datetime
import hashlib
import json
from pathlib import Path

B = Path(__file__).resolve().parent
G = B.parent / 'pcie-divider-v9-bias-v1-wire-v1-20261006'


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return {'bytes': p.stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}


def read(p):
    return json.loads(Path(p).read_text())


freeze_path = B / 'source-freeze.json'
assert pin(freeze_path) == {'bytes': 635169, 'sha256': '318db671d8832630cb7324df90e3dc63fffa0fc9d165f522af2ce3dff6a4ccc9'}
freeze = read(freeze_path)
assert len(freeze['inputs']) == 2872
for path, expected in freeze['inputs'].items():
    assert pin(path) == expected, path
assert freeze['producer_sources'] == {n: pin(B / n) for n in freeze['producer_sources']}
bridges = read(B / 'draft-source-bridge.json')
assert len(bridges) == 3
comparison = []
for bridge in bridges:
    p, c = Path(bridge['parent']), Path(bridge['new'])
    assert pin(p) == bridge['parent_pin'] and pin(c) == bridge['new_pin']
    assert bridge['substitutions'] == [['v8-cap-v1', 'v9-bias-v1'], ['V8_CAP24', 'V9_BIAS8']]
    before, after = p.read_text(), c.read_text()
    reconstructed = before.replace('v8-cap-v1', 'v9-bias-v1').replace('V8_CAP24', 'V9_BIAS8')
    inverse = after.replace('v9-bias-v1', 'v8-cap-v1').replace('V9_BIAS8', 'V8_CAP24')
    assert reconstructed == after and inverse == before
    assert ast.dump(ast.parse(inverse)) == ast.dump(ast.parse(before))
    comparison.append({'parent': str(p), 'parent_pin': pin(p), 'child': str(c), 'child_pin': pin(c), 'full_forward_inverse': True, 'full_normalized_AST_exact': True})
fb = read(B / 'freezer-source-bridge.json')
assert pin(fb['parent']) == fb['parent_pin'] and pin(fb['child']) == fb['child_pin']
assert ''.join(r['before'] for r in fb['full_opcodes']) == Path(fb['parent']).read_text()
assert ''.join(r['after'] for r in fb['full_opcodes']) == Path(fb['child']).read_text()
assert all(r['before'] == r['after'] for r in fb['full_opcodes'] if r['tag'] == 'equal')
ge = read(G / 'geometry-execution.json')
bc = read(G / 'binding-controls01/result.json')
saved = read(G / 'saved-geometry-peer.json')
assert ge['status'] == 'PASS_DIVIDER_V9_BIAS8_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
assert bc['status'] == 'PASS_BASELINE_AND_FOUR_ACTUAL_COPIED_INPUT_BINDING_CONTROLS'
assert saved['status'] == 'PASS_DIVIDER_V9_BIAS8_SAVED_GEOMETRY_AND_BINDING_CONTROLS' and saved['findings'] == []
assert saved['geometry_execution'] == pin(G / 'geometry-execution.json')
assert saved['binding_controls'] == pin(G / 'binding-controls01/result.json')
assert len(ge['steps']) == 7 and all(r['execution']['returncode'] == 0 for r in ge['steps'])
assert len(bc['cases']) == 5 and all(r['status'].startswith('PASS_') for r in bc['cases'])
anchors = read(G / 'anchors.json')
assert len(anchors['anchors']) == 205
assert anchors['actual_metal_terminals'] == 198 and anchors['body_well_terminals'] == 85
assert anchors['source_geometry'] == pin('/dev/shm/nssoc-div4-v9-bias-v1-wire-geometry-01/wires.gds')
assert not Path('/dev/shm/nssoc-div4-v9-bias-v1-wire-rc-01').exists()
assert not (B / 'native-execution.json').exists()
record = {
    'status': 'PASS_SOURCE_ONLY_DIVIDER_V9_BIAS8_WIRE_RC', 'freeze': pin(freeze_path), 'findings': [],
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_comparison': comparison, 'frozen_inputs_independently_rehashed': len(freeze['inputs']),
    'freezer_bridge': pin(B / 'freezer-source-bridge.json'),
    'geometry_saved_peer': {'path': str(G / 'saved-geometry-peer.json'), **pin(G / 'saved-geometry-peer.json')},
    'read_scope': [
        'Read all7859-byte runner,12305-byte audit and6775-byte13-control method. Three complete independent byte inverses and normalized ASTs prove changes limited to named V9 roots/status; no extraction, numeric tolerance or graph criterion changed.',
        'Runner rebinds all2872 prerequisites, seven completed geometry stages, five real copied-input controls and independent saved peer.205 anchors retain198 metal and85 separate body terminals; native Tcl generation remains the exact four AST nodes from frozen VCO ancestor.',
        'Ownership remains exact seven frozen checker function ASTs with private CPU10/2GiB/80MiB+24MiB/1GiB-entry/512MiB-floor globals, terminal resource and signal guards, fresh roots and no healthy elapsed deadline.',
        'Audit preserves raw37 wire networks/205 ports, exact positive R edge/value multiset, all anchored connected components without alias edges, native point-C/mutual attachment, complete38x38 collapsed matrix and independent body/reference boundary. It does not qualify RF, substrate resistance or full PEX.',
        'All13 actual raw corruption controls retain exact diagnostics, including genuine unique-resistor bridge removal splitting real probes, cross-conductor short, same-total ground redistribution and mutual reattachment. They remain unexecuted for V9 until native production succeeds.'
    ],
    'method': {'path': str(Path(__file__)), **pin(__file__)},
    'no_reviewed_execution': True, 'no_new_native_or_controls': True,
}
out = B / 'source-only-peer.json'
assert not out.exists()
out.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'path': str(out), **pin(out), 'inputs': len(freeze['inputs'])}))
