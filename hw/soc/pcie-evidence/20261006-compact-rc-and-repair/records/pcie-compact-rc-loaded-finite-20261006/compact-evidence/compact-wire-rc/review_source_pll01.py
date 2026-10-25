"""Independent read-only derivative/source binding review; no producer imports."""
from pathlib import Path
import ast
import hashlib
import json

B = Path(__file__).resolve().parent
OLD = B.parent / 'pcie-divider-v7-power-v2-wire-rc-v1-20261006'
G = B.parent / 'pcie-divider-v7-compact-v2-wire-v1-20261006'

def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f,'sha256').hexdigest())

freeze = B / 'source-freeze.json'
assert pin(freeze) == dict(bytes=471810, sha256='22dc7f36eabb8cd7acd2ba75f33546c87e879af315969ff318a425644be85d0b')
f = json.loads(freeze.read_text())
assert len(f['inputs']) == 2121
for p, v in f['inputs'].items():
    assert pin(p) == v, p
for p, v in f['producer_sources'].items():
    assert pin(B/p) == v
bridges = json.loads((B/'draft-source-bridge.json').read_text())
assert len(bridges) == 3
accepted = {
 'run_native_rc.py': [
  ("pcie-divider-v7-power-v2-wire-v2-20261006", "pcie-divider-v7-compact-v2-wire-v1-20261006"),
  ("nssoc-div4-v7-power-v2-wire-rc-01", "nssoc-div4-v7-compact-v2-wire-rc-01"),
  ("nssoc-div4-v7-power-v2-wire-geometry-02", "nssoc-div4-v7-compact-v2-wire-geometry-01")],
 'audit_wire_rc.py': [("pcie-divider-v7-power-v2-wire-v2-20261006", "pcie-divider-v7-compact-v2-wire-v1-20261006")],
 'check_native_mutations_v2.py': [("nssoc-div4-v7-power-v2-wire-rc-01", "nssoc-div4-v7-compact-v2-wire-rc-01")],
}
records = []
for row in bridges:
    before, after = Path(row['before']['path']), Path(row['after']['path'])
    for side, p in [('before', before), ('after', after)]:
        assert pin(p) == {k: row[side][k] for k in ('bytes','sha256')}
    assert before.parent == OLD and after.parent == B
    a, b = before.read_text(), after.read_text()
    assert ''.join(x['before'] for x in row['opcodes']) == a
    assert ''.join(x['after'] for x in row['opcodes']) == b
    transformed = a
    for old, new in accepted[after.name]:
        assert transformed.count(old) == 1
        transformed = transformed.replace(old, new)
    assert transformed == b
    assert ast.dump(ast.parse(transformed)) == ast.dump(ast.parse(b))
    records.append(dict(name=after.name, previous=pin(before), current=pin(after), replacements=accepted[after.name]))
oldpeer = json.loads((OLD/'source-only-peer.json').read_text())
assert oldpeer['status'] == 'PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_RC' and not oldpeer['findings']
assert oldpeer['freeze'] == pin(OLD/'source-freeze.json')
geometry = json.loads((G/'geometry-execution.json').read_text())
peer = json.loads((G/'saved-geometry-peer.json').read_text())
controls = json.loads((G/'binding-controls01/result.json').read_text())
assert geometry['status'] == 'PASS_DIVIDER_V7_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
assert peer['status'] == 'PASS_DIVIDER_V7_SAVED_GEOMETRY_AND_BINDING_CONTROLS' and not peer['findings']
assert peer['geometry_execution'] == pin(G/'geometry-execution.json')
assert peer['binding_controls'] == pin(G/'binding-controls01/result.json')
assert controls['status'] == 'PASS_BASELINE_AND_FOUR_ACTUAL_COPIED_INPUT_BINDING_CONTROLS'
for p, v in geometry['outputs'].items():
    assert pin(p) == v
anchor = json.loads((G/'anchors.json').read_text())
assert len(anchor['anchors']) == 205
assert len(set(x['label'] for x in anchor['anchors'])) == 205
assert set(x['wire_component'] for x in anchor['anchors']) == set(range(1,38))
assert anchor['source_geometry'] == pin('/dev/shm/nssoc-div4-v7-compact-v2-wire-geometry-01/wires.gds')
assert anchor['actual_metal_terminals'] == 198 and anchor['body_well_terminals'] == 85
assert len(anchor['unmodeled_body_well_terminals']) == 85
assert geometry['resource_contract'] == dict(cpu=10,native_AS=2147483648,own_scratch=83886080,
 reserve=25165824,entry=1073741824,continuous=536870912,healthy_elapsed_watchdog_seconds=None,failure_cleanup_grace_seconds=5)
run = (B/'run_native_rc.py').read_text()
assert "assert not O.exists() and not (B / 'native-execution.json').exists()" in run
assert "saved_peer['geometry_execution'] == pin(GEOMETRY / 'geometry-execution.json')" in run
assert "saved_peer['binding_controls'] == pin(GEOMETRY / 'binding-controls01/result.json')" in run
mut = (B/'check_native_mutations_v2.py').read_text()
assert 'nx.number_connected_components(trial)==38' in mut
assert 'left&set(anchor) and right&set(anchor)' in mut
assert "anchor['P004']!=anchor['P005']" in mut
assert "owner[cf[1]]!=owner[cf[2]]" in mut
assert 'assert observed==wanted' in mut
for p, v in f['inputs'].items():
    assert pin(p) == v, p
receipt = dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_RC',freeze=pin(freeze),findings=[],
 source_pins_rehashed=2121,source_pins=f['producer_sources'],full_inverse_bridges=records,
 prior_source_peer=pin(OLD/'source-only-peer.json'),prior_saved_RC_peer=pin(OLD/'saved-rc-peer-pll.json'),
 current_saved_geometry_peer=pin(G/'saved-geometry-peer.json'),
 inspected=[
  'Complete native runner, full distributed-R/point-C/mutual-C auditor,13actual corruption harness and freeze builder read; three entire method bodies differ only listed geometry/output paths.',
  'Same inherited4Tcl ASTs and Magic/PDK/private-runtime closure; no extraction settings or generated alias graph edges changed.',
  'New compact geometry205probes/198metal+7public ports/85body and37conductors, exact saved native geometry/bijection plus5binder outcomes are source-bound; no assumed geometrical equality withPowerV2.',
  'Same graph excludes aliases, validates all native resistor multiset, full38x38 capacitance collapse plus point/mutual attachment, exact native completion and205port topology; body-R and qualified RFPEX explicitly not claimed.',
  'Same13 negatives include actualunique resistor bridge with probes onboth sides,37→38components, realmutualC anddistinctP004/P005 conductors; new native topology must provide these witnesses orfail.',
  'SameCPU10/2GiB/80MiB/512MiBguards and5second failurecleanup, allstage pre/post pins, no healthytimeout; no RC producer/tests/signal executed by peer.'
 ],method=pin(Path(__file__)),native_reexecution=False,scope='Source-only approval for fresh compact wire-RC extraction and unchanged controls; not an RC result or loaded-division/qualification claim.')
out=B/'source-only-peer.json';assert not out.exists()
out.write_text(json.dumps(receipt,indent=2)+'\n')
print(receipt['status'],pin(out))
