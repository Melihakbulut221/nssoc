from pathlib import Path
import hashlib
import json

B = Path(__file__).resolve().parent
G = B.parent / 'pcie-divider-v9-bias-v1-wire-v1-20261006'
OLD = B.parent / 'pcie-divider-v8-cap-v1-wire-rc-v1-20261006'

def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())

assert not (B / 'source-freeze.json').exists()
g = json.loads((G / 'geometry-execution.json').read_text())
assert g['status'] == 'PASS_DIVIDER_V9_BIAS8_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
assert g['outputs'] == {p: pin(p) for p in g['outputs']}
c = json.loads((G / 'binding-controls01/result.json').read_text())
assert c['status'] == 'PASS_BASELINE_AND_FOUR_ACTUAL_COPIED_INPUT_BINDING_CONTROLS'
p = json.loads((G / 'saved-geometry-peer.json').read_text())
assert p['status'] == 'PASS_DIVIDER_V9_BIAS8_SAVED_GEOMETRY_AND_BINDING_CONTROLS' and p['findings'] == []
assert p['geometry_execution'] == pin(G / 'geometry-execution.json')
assert p['binding_controls'] == pin(G / 'binding-controls01/result.json')
previous = json.loads((OLD / 'source-freeze.json').read_text())
assert previous['inputs'] == {p: pin(p) for p in previous['inputs']}
inputs = {**previous['inputs'], **g['inputs'], **g['outputs'], **c['fixture_outputs']}
files = [*B.glob('*.py'), B / 'draft-source-bridge.json',
         OLD / 'source-freeze.json', OLD / 'source-only-peer.json',
         OLD / 'check_native_mutations_v2.py', OLD / 'saved-rc-peer-pll.json',
         G / 'geometry-source-freeze.json', G / 'geometry-source-only-peer.json',
         G / 'geometry-execution.json', G / 'saved-geometry-peer.json',
         *[q for q in (G / 'binding-controls01').rglob('*') if q.is_file()]]
for f in files:
    inputs[str(f)] = pin(f)
assert inputs == {p: pin(p) for p in inputs}
result = dict(status='FROZEN_DIVIDER_V9_BIAS8_WIRE_RC_SOURCE_PENDING_INDEPENDENT_PEER',
              inputs=inputs, producer_sources={p.name: pin(p) for p in B.glob('*.py')},
              full_previous_native_runtime_and_networkx_import_closure_rehashed=True,
              expected=dict(devices=91, metal_terminals=198, body_terminals=85,
                            public_ports=7, anchors=205, wire_components=37),
              actual_wire_rc_executed=False, qualified_pex=False,
              scope='Fresh bias8-divider wire RC; exact two L8 pull-downs and retained cap24 intrinsic models/body boundary retained. Same native extraction settings and strict distributed graph/capacitance audit. No qualified RF or substrate PEX claim.')
(B / 'source-freeze.json').write_text(json.dumps(result, indent=2) + '\n')
print(len(inputs), pin(B / 'source-freeze.json'))
