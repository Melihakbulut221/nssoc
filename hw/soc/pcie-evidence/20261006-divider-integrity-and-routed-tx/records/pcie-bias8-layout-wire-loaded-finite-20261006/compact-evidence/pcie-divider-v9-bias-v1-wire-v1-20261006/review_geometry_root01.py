# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-only independent full-byte inverse and actual input binding review."""
from pathlib import Path
import ast
import hashlib
import json

W = Path(__file__).absolute().parent
P = W.with_name('pcie-divider-v9-bias-v1-20261006')
O = W.with_name('pcie-divider-v8-cap-v1-wire-v1-20261006')
G = Path('/dev/shm/nssoc-div4-v9-bias-v1-layout-01')
C = Path('/dev/shm/nssoc-div4-v9-bias-v1-checks-01')


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def load(path):
    return json.loads(Path(path).read_text())


freeze = load(W / 'geometry-source-freeze.json')
assert len(freeze['inputs']) == 1607
for path, expected in freeze['inputs'].items():
    assert pin(path) == expected, path
for path, expected in freeze['producer_sources'].items():
    assert expected == freeze['inputs'][path]
old_gds = Path('/dev/shm/nssoc-div4-v8-cap-v1-layout-01/nssoc_clock_div4_v8_cap_v1_layout.gds')
new_gds = G / 'nssoc_clock_div4_v9_bias_v1_layout.gds'
replacements = [
    ('v8-cap-v1', 'v9-bias-v1'), ('v8_cap_v1', 'v9_bias_v1'),
    ('V8_CAP24', 'V9_BIAS8'), ('V8_CAP_V1', 'V9_BIAS_V1'),
    ('PASS_ACTUAL_CAP24_TWO_MIM_DELTA_POWER_AND_SIX_GEOMETRY_CONTROLS',
     'PASS_ACTUAL_BIAS8_TWO_RPPD_DELTA_CAP24_POWER_AND_EIGHT_GEOMETRY_CONTROLS'),
    ('PASS_INDEPENDENT_SAVED_CAP24_V1_NATIVE_RESULT',
     'PASS_INDEPENDENT_SAVED_BIAS8_V1_NATIVE_RESULT'),
    (pin(old_gds)['sha256'], pin(new_gds)['sha256'])]
bridges = load(W / 'source-bridge01.json')
assert len(bridges) == 7
checked = {}
for bridge in bridges:
    before = Path(bridge['before']['path'])
    after = Path(bridge['after']['path'])
    assert before.parent == O and after.parent == W and before.name == after.name
    for name, path in [('before', before), ('after', after)]:
        assert pin(path) == {k: bridge[name][k] for k in ('bytes', 'sha256')}
    left, right = before.read_text(), after.read_text()
    assert ''.join(op['before'] for op in bridge['opcodes']) == left
    assert ''.join(op['after'] for op in bridge['opcodes']) == right
    # Reconstruct independently of the producer's stored diff opcodes.
    transformed = left
    for old, new in replacements:
        transformed = transformed.replace(old, new)
    assert transformed == right, after
    ast.parse(right)
    checked[after.name] = pin(after)
assert (W / 'native_unsimplified.lvs').read_bytes() == (O / 'native_unsimplified.lvs').read_bytes()
assert len(checked) == 7
peer = load(P / 'native-saved-peer-rx.json')
assert peer['status'] == 'PASS_INDEPENDENT_SAVED_BIAS8_V1_NATIVE_RESULT' and peer['findings'] == []
for field, path in [('checks', C / 'result.json'), ('geometry', C / 'power-geometry.json'),
                    ('GDS', new_gds), ('ready', P / 'native-finite-review-ready01.json')]:
    assert peer[field] == pin(path)
native = load(C / 'result.json')
assert len(native['steps']) == 21
assert native['outputs'] == {n: pin(C / n)['sha256'] for n in native['outputs']}
assert freeze['source_expected_census'] == dict(devices=91, terminals=283, metal_terminals=198,
                                               body_terminals=85, anchors=205, ports=7, conductors=37)
assert freeze['actual_prior_hierarchy_census'] == dict(devices=91, via_stack=634, all_leaves=725)
assert freeze['complete_native_cluster_partition_expected'] == dict(raw=72, electrical=38, body_only=1, auxiliary=34)
assert not Path('/dev/shm/nssoc-div4-v9-bias-v1-wire-geometry-01').exists()
assert not Path('/dev/shm/nssoc-div4-v9-bias-v1-wire-native-01').exists()
assert not (W / 'geometry-execution.json').exists()
result = dict(status='PASS_SOURCE_ONLY_DIVIDER_V9_BIAS8_WIRE_GEOMETRY',
              freeze=pin(W / 'geometry-source-freeze.json'), findings=[],
              rehashed_inputs=len(freeze['inputs']), complete_inverses=checked,
              unchanged_extraction_deck=pin(W / 'native_unsimplified.lvs'),
              declared_replacements=replacements,
              independent_native_peer=pin(P / 'native-saved-peer-rx.json'),
              actual_native_checks=pin(C / 'result.json'), GDS=pin(new_gds),
              method=pin(__file__),
              scope='Source-only review: seven complete byte inverses, all1607pins, actual prior21stage result and independent geometry peer rebound. Strict91devices/283terminals/205anchors/37conductors/72clusters and allbody/auxiliary accounting unchanged. Fresh native geometry, RC and loaded function not yet executed. No qualified PEX or PHY acceptance.')
out = W / 'geometry-source-only-peer.json'
assert not out.exists()
out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(status=result['status'], result=pin(out), inputs=1607, bridges=7)))
