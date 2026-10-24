"""Independent read-only complete derivative and immutable-input review."""
import ast
import hashlib
import json
from pathlib import Path

B = Path(__file__).resolve().parent
P = B.parent / 'pcie-divider-v9-bias-v1-wire-v1-20261006'

def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())

freeze = B / 'geometry-source-freeze.json'
assert pin(freeze) == dict(bytes=420163, sha256='db4f8fb7f83901ec1c9f73e6d792000ba6307b35dc6b120e90b68f07988a4aac')
f = json.loads(freeze.read_text())
for p, expected in f['inputs'].items():
    assert pin(p) == expected, p
assert len(f['inputs']) == 1883
assert f['source_expected_census'] == dict(devices=91, terminals=283, metal_terminals=198, body_terminals=85, anchors=205, ports=7, conductors=37)
assert f['actual_prior_hierarchy_census'] == dict(devices=91, via_stack=634, all_leaves=725)
assert f['complete_native_cluster_partition_expected'] == dict(raw=72, electrical=38, body_only=1, auxiliary=34)
bridge = json.loads((B / 'source-bridge01.json').read_text())
assert len(bridge['rows']) == 7
reviewed = []
for row in bridge['rows']:
    old, new = Path(row['before']['path']), Path(row['after']['path'])
    assert old.parent == P and new.parent == B and old.name == new.name
    assert pin(old) == {k: row['before'][k] for k in ('bytes', 'sha256')}
    assert pin(new) == {k: row['after'][k] for k in ('bytes', 'sha256')}
    old_text, new_text = old.read_text(), new.read_text()
    assert ''.join(x['before'] for x in row['opcodes']) == old_text
    assert ''.join(x['after'] for x in row['opcodes']) == new_text
    transformed = old_text
    for before, after in bridge['substitutions']:
        transformed = transformed.replace(before, after)
    assert transformed == new_text, new
    ast.parse(new_text)
    assert f['producer_sources'][str(new)] == pin(new)
    assert f['inputs'][str(new)] == pin(new)
    reviewed.append(dict(path=str(new), **pin(new)))
assert (B / 'native_unsimplified.lvs').read_bytes() == (P / 'native_unsimplified.lvs').read_bytes()
assert pin(B / 'native_unsimplified.lvs') == bridge['deck_unchanged']
native = B.parent / 'pcie-divider-v10-tail-v1-20261006/native-saved-peer-rx.json'
np = json.loads(native.read_text())
assert np['status'] == 'PASS_INDEPENDENT_SAVED_TAIL115_V1_NATIVE_RESULT' and not np['findings']
gds = Path('/dev/shm/nssoc-div4-v10-tail-v1-layout-01/nssoc_clock_div4_v10_tail_v1_layout.gds')
assert np['GDS'] == pin(gds)
assert pin(gds)['sha256'] == '72b1d7794218744fc50fa3b28430e229a70d37ce4cc952d551219c871476cfee'
for s in ('/dev/shm/nssoc-div4-v10-tail-v1-wire-geometry-01', '/dev/shm/nssoc-div4-v10-tail-v1-wire-native-01'):
    assert not Path(s).exists()
assert not (B / 'geometry-execution.json').exists()
r = dict(status='PASS_SOURCE_ONLY_DIVIDER_V10_TAIL115_WIRE_GEOMETRY', reviewer='PLL/integrity agent',
         freeze=pin(freeze), findings=[], method=pin(__file__),
         bridge=pin(B / 'source-bridge01.json'), input_count=len(f['inputs']), methods=reviewed,
         deck=pin(B / 'native_unsimplified.lvs'), prior_saved_native_peer=pin(native),
         independent_checks=[
             'Rehashed all 1883 input files and exact seven full-body forward/inverse bridge segments.',
             'Read all seven complete methods and unchanged extraction deck: all graph, parameter, point attachment and body-disposition checks remain exact.',
             'Only paths/top name/GDS pin and native-result status plus ten-geometry-control gate changed from completed V9 ancestry.',
             'All 91 devices/283 terminals/198 metal/85 body/205 anchors/37 conductors/72 cluster and 725 leaf/634 via requirements retained.',
             'All six explicit launched helper basenames exist and are frozen. Original AST-owned resource/terminal lifecycle and seven native stage order unchanged.',
             'Actual V10 standalone peer and new GDS are bound; fresh outputs absent. No producer import, extraction, control or native rerun.'
         ], scope='Source-only derivative review; new geometry/RC/loaded function remain pending. No PEX, main-chip or production approval.')
(B / 'geometry-source-only-peer.json').write_text(json.dumps(r, indent=2) + '\n')
print(json.dumps(dict(status=r['status'], receipt=pin(B / 'geometry-source-only-peer.json'), inputs=len(f['inputs'])), indent=2))
