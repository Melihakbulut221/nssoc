# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent bounded source/saved-binding read; never launch reviewed methods."""
import ast
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

S = Path(__file__).resolve().parent
B = S.parent
E = Path('/dev/shm/nssoc-tx-path-v4-repair03-equivalence')
P = Path('/dev/shm/nssoc-tx-path-v4-repair03-physical-replay-01')


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def j(path):
    return json.loads(Path(path).read_text())


freeze = j(S / 'route-rc-source-freeze.json')
assert freeze['files'] == {p: pin(p) for p in freeze['files']}
assert freeze['method'] == pin(S / 'derive_route_sources.py')
assert freeze['bridge'] == pin(S / 'route-rc-source-bridge.json')
assert freeze['completed_proof_port_review'] == pin(S / 'pre-drt-proof-port-review.json')
bridges = j(S / 'route-rc-source-bridge.json')
assert len(bridges) == 2
old_scope = 'TX candidate02: six measured driver-load isolations, nine buf1->buf4, one hold buffer following actualTX01 nominalRC.'
new_scope = 'TX candidate03: seven measured complex/XOR driver-load isolations and three buffer upsizes following actualTX02 nominalRC. Existing hold repair preserved.'
changes = [('repair02', 'repair03'), ('repair-02', 'repair-03'), ('TX02', 'TX03'), ('tx02', 'tx03'),
           ('repair03-drt-03', 'repair03-drt-01'), ('repair03-detailed-rc-02', 'repair03-detailed-rc-01'),
           (old_scope, new_scope), ('GRTsetup+.684261 recovery+.149536 hold+.065914.', 'FreshGRT estimates retained separately; not routed timing.')]
verified = []
for row in bridges:
    for key in ('before', 'after'):
        assert pin(row[key]['path']) == {k: row[key][k] for k in ('bytes', 'sha256')}
    old, new = (Path(row[k]['path']).read_text() for k in ('before', 'after'))
    assert ''.join(o['before'] for o in row['opcodes']) == old
    assert ''.join(o['after'] for o in row['opcodes']) == new
    assert all(o['before'] == o['after'] for o in row['opcodes'] if o['tag'] == 'equal')
    predicted = old
    for a, z in changes:
        predicted = predicted.replace(a, z)
    assert predicted == new
    inverse = new
    for a, z in reversed(changes):
        inverse = inverse.replace(z, a)
    assert inverse == old
    ast.parse(new)
    verified.append(dict(before=row['before'], after=row['after'], entire_forward_inverse_exact=True))

saved = j(S / 'pre-drt-proof-port-review.json')
assert saved['binding'] == pin(E / 'proof-execution-binding.json')
assert saved['port_result'] == pin(P / 'result.json')
assert saved['candidate'] == pin('/dev/shm/nssoc-tx-path-v4-postroute-repair-03/repaired.v')
binding = j(E / 'proof-execution-binding.json')
assert binding['status'] == 'PASS_ACTUAL_TX03_PROOF_AND_MUTATION_EXECUTION_BOUND'
assert binding['before_inputs'] == binding['after_inputs'] == {p: pin(p) for p in binding['before_inputs']}
assert binding['outputs'] == {p: pin(E / p) for p in binding['outputs']}
assert binding['runtime_before'] == binding['runtime_after']
assert binding['runtime_before']['pin'] == pin(binding['runtime_before']['path'])
assert [(r['method'], r['returncode']) for r in binding['runs']] == [('compare.py', 0), ('mutations.py', 0)]
norm = j(E / 'normalization.json')
assert norm['inputs'] == {p: pin(p) for p in norm['inputs']}
graphs = {}
for row in norm['runs']:
    name = row['name']
    assert row['returncode'] == 0
    assert pin(E / (name + '.ys'))['sha256'] == row['script_sha256']
    assert pin(E / (name + '.log'))['sha256'] == row['log_sha256']
    compressed = E / (name + '.json.gz')
    assert pin(compressed)['sha256'] == row['expanded_json']['lossless_gzip_sha256']
    digest, size = hashlib.sha256(), 0
    with gzip.open(compressed, 'rb') as stream:
        while data := stream.read(1024**2):
            digest.update(data)
            size += len(data)
    expanded = dict(bytes=size, sha256=digest.hexdigest())
    assert expanded == {k: row['expanded_json'][k] for k in expanded}
    graphs[name] = dict(compressed=pin(compressed), expanded=expanded)
assert graphs == binding['expanded_graphs_before'] == binding['expanded_graphs_after']
equiv = j(E / 'equivalence.json')
assert equiv['status'] == 'PASS_COMPLETE_STATE_TRANSITION_AND_OUTPUT_FUNCTION_EQUALITY'
assert equiv['states'] == 3850 and equiv['targets'] == equiv['matched'] == 11680 and not equiv['mismatches']
faults = j(E / 'mutation-controls.json')
assert len(faults['controls']) == 10 and all(r['status'].startswith('REJECTED_') for r in faults['controls'])
ports = j(P / 'result.json')
assert ports['status'] == 'PASS_EXACT_BOUND_TX03_PHYSICAL_NETLIST_PORT_REPLAY'
assert ports['tests'] == dict(passed=3, failed=0, skipped=0)
assert ports['inputs'] == {p: pin(p) for p in ports['inputs']}
assert ports['outputs'] == {p: pin(P / p) for p in ports['outputs']}
cases = list(ET.parse(P / 'results.xml').iter('testcase'))
assert len(cases) == 3 and all(not list(c) for c in cases)
assert '10 passed' in (S / 'binding-controls.log').read_text()
assert not Path('/dev/shm/nssoc-tx-path-v4-repair03-drt-01').exists()
assert not Path('/dev/shm/nssoc-tx-path-v4-repair03-detailed-rc-01').exists()

record = dict(
    status='PASS_SOURCE_ONLY_TX03_FRESH_DRT_RC_METHODS', findings=[],
    method=pin(__file__), freeze=pin(S / 'route-rc-source-freeze.json'),
    files=freeze['files'], bridges=verified,
    completed_proof_port_review=freeze['completed_proof_port_review'],
    saved_binding=pin(E / 'proof-execution-binding.json'), graphs_full_readback=graphs,
    saved_kernel_controls=pin(E / 'mutation-controls.json'),
    saved_binding_controls_log=pin(S / 'binding-controls.log'),
    saved_port_result=pin(P / 'result.json'), saved_port_xml=pin(P / 'results.xml'),
    reviewed=[
        'Both complete sources independently reconstruct forward and inverse from frozen TX02 DRT03/RC02. Only fresh TX03-01 input/output paths, version/status strings and accurate candidate metadata differ; routing, extraction, constraints and failure lifecycle bodies are identical.',
        'DRT requires exact completed proof binding, 3850 states/11680 functions, ten actual kernel faults, three passing native ports and all port inputs unchanged. Rechecks proof binding after routing, asserts native completion, router DRC zero and byte-identical routed/proved netlist.',
        'Candidate repaired ODB/SDC and all tool/Liberty/native graph sources are pinned. Route uses unchanged propagated clock and signal/clock Metal2-Metal5 policy. Only verified empty zero_/one_ aliases may be removed.',
        'Fresh RC requires exact completed DRT inputs/outputs, zero DRC and same candidate bytes. Preserves coupling_threshold0, cc_model10, context_depth5 and no_merge_via_res; same nominal SPEF across slow/typical/fast cell libraries is explicitly unqualified RC.',
        'Inherited one-CPU process affinity, 2.5 GiB AS, shared 1 GiB entry/528 MiB floor, masked spawn registration and new session group with explicit 5-second failure cleanup retained. No healthy elapsed timeout; intended launch affinity CPU4 must be enforced by caller.',
        'Saved proof inputs/outputs/runtime and both complete expanded graphs independently rehashed without invoking the gate/kernel. Saved ten binding controls observed and three raw XML cases recounted; no proof/control/native rerun by reviewer.'
    ],
    limitations=['Prelaunch source/saved-output review only. Fresh detailed route and actual nominal RC remain unexecuted at this review.',
                 'No reviewed method, tool, test, simulation, route, extraction or publication was executed. No final timing, qualified RC, full-chip/foundry/PDN or PCIe PHY acceptance.'])
out = S / 'route-rc-source-only-peer-vco.json'
assert not out.exists()
out.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(dict(path=str(out), **pin(out), status=record['status'])))
