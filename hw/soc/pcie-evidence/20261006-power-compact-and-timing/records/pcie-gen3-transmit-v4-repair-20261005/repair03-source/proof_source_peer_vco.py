# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent read-only review: never import/run the reviewed production methods."""
import ast
import gzip
import hashlib
import json
from pathlib import Path

S = Path(__file__).resolve().parent
B = S.parent


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size,
                'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def expect(path, row):
    actual = pin(path)
    assert actual == {k: row[k] for k in actual}, (str(path), actual, row)
    return actual


def load(path):
    return json.loads(Path(path).read_text())


freeze = load(S / 'proof-source-freeze.json')
expect(S / 'proof-source-bridge.json', freeze['bridge'])
expect(S / 'derive_proof_sources.py', freeze['method'])
for path, row in freeze['files'].items():
    expect(path, row)
    ast.parse(Path(path).read_text())
template = Path(freeze['gold_reuse_template']['path'])
expect(template, freeze['gold_reuse_template'])
candidate = Path(freeze['candidate']['path'])
expect(candidate, freeze['candidate'])
expect(candidate.parent / 'result.json', freeze['candidate_result'])
cresult = load(candidate.parent / 'result.json')
assert cresult['status'] == 'COMPLETE_CANDIDATE_REQUIRES_EQUIVALENCE_ROUTE_RC'
assert cresult['returncode'] == 0
assert cresult['inputs'] == {p: pin(p) for p in cresult['inputs']}
assert cresult['outputs'] == {p.name: pin(p) for p in candidate.parent.iterdir()
                              if p.is_file() and p.name != 'result.json'}

old_pin = {'bytes': 4174181, 'sha256': '5e964dabf6aa8a0d8a42a8ac9adbd0320b668ab350bf3a3ad9f9bd0402f62c90'}
changes = [('repair02', 'repair03'), ('repair-02', 'repair-03'),
           ('proof02', 'proof03'), ('TX02', 'TX03'), ('tx02', 'tx03'),
           ('candidate02', 'candidate03'), (repr(old_pin), repr(pin(candidate)))]
template_text = template.read_text()
reuse_start = template_text.index('# Reuse identical completed originalgold')
reuse_end = template_text.index('\ndef limits():', reuse_start)
reuse = template_text[reuse_start:reuse_end].replace(
    '/dev/shm/nssoc-rx-prefetch-v2-repair11-equivalence',
    '/dev/shm/nssoc-tx-path-v4-repair02-equivalence')
old_record = "pins={str(p):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in inputs}\nrecord={'inputs':pins,'scope':'Native Liberty functional expansion, no blackboxes or assumptions','runs':[]}"
old_loop = "for name,net in [('gold',inputs[-2]),('gate',inputs[-1])]:"
new_loop = "for name,net in [('gate',pathlib.Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-03/repaired.v'))]:"
bridge_records = []
bridges = load(S / 'proof-source-bridge.json')
assert len(bridges) == 6
for row in bridges:
    before_path, after_path = (Path(row[k]['path']) for k in ('before', 'after'))
    expect(before_path, row['before'])
    expect(after_path, row['after'])
    old, new = before_path.read_text(), after_path.read_text()
    assert ''.join(o['before'] for o in row['opcodes']) == old
    assert ''.join(o['after'] for o in row['opcodes']) == new
    assert all(o['before'] == o['after'] for o in row['opcodes'] if o['tag'] == 'equal')
    predicted = old
    for a, z in changes:
        predicted = predicted.replace(a, z)
    inverse = new
    if after_path.name == 'normalize_repair03.py':
        assert predicted.count(old_record) == predicted.count(old_loop) == 1
        predicted = predicted.replace(old_record, reuse).replace(old_loop, new_loop)
        assert inverse.count(reuse) == inverse.count(new_loop) == 1
        inverse = inverse.replace(reuse, old_record).replace(new_loop, old_loop)
    assert predicted == new, str(after_path)
    for a, z in reversed(changes):
        inverse = inverse.replace(z, a)
    assert inverse == old, str(after_path)
    bridge_records.append({'before': row['before'], 'after': row['after'],
                           'full_bridge_and_independent_inverse': True})

gold_path = Path(freeze['original_gold']['path'])
expect(gold_path, freeze['original_gold'])
gold_record = load(gold_path)
assert gold_record['inputs'] == {p: pin(p) for p in gold_record['inputs']}
gold = gold_record['runs'][0]
assert gold['name'] == 'gold' and gold['returncode'] == 0
for suffix, key in [('.ys', 'script_sha256'), ('.log', 'log_sha256')]:
    assert pin(gold_path.parent / ('gold' + suffix))['sha256'] == gold[key]
compressed = gold_path.parent / 'gold.json.gz'
assert pin(compressed)['sha256'] == gold['expanded_json']['lossless_gzip_sha256']
with gzip.open(compressed, 'rb') as stream:
    digest, size = hashlib.sha256(), 0
    while data := stream.read(1024**2):
        digest.update(data)
        size += len(data)
expanded = {'bytes': size, 'sha256': digest.hexdigest()}
assert expanded == {k: gold['expanded_json'][k] for k in expanded}
gold_script = (gold_path.parent / 'gold.ys').read_text()
assert 'read_verilog /dev/shm/nssoc-tx-path-v4-drt-01/routed.v\n' in gold_script
assert 'hierarchy -check -top soc_pcie_gen3_tx_path_v4\n' in gold_script
assert 'flatten\nproc\nopt_clean\ncheck -assert\nstat\n' in gold_script

record = {
    'status': 'PASS_SOURCE_ONLY_TX03_PROOF_PORT_METHODS', 'findings': [],
    'method': pin(__file__), 'freeze': pin(S / 'proof-source-freeze.json'),
    'bridge': pin(S / 'proof-source-bridge.json'), 'files': freeze['files'],
    'independent_full_forward_inverse_bridges': bridge_records,
    'candidate': freeze['candidate'], 'candidate_result': freeze['candidate_result'],
    'candidate_inputs_rehashed': len(cresult['inputs']),
    'candidate_outputs_rehashed': len(cresult['outputs']),
    'originalgold': {'receipt': freeze['original_gold'], 'inputs_rehashed': len(gold_record['inputs']),
                     'script': pin(gold_path.parent / 'gold.ys'),
                     'log': pin(gold_path.parent / 'gold.log'),
                     'gzip': pin(compressed), 'all_expanded_bytes': expanded,
                     'template': freeze['gold_reuse_template'],
                     'gold_native_execution_reused_not_rerun': True},
    'review': [
        'All six complete source bridges independently reconstructed forward and inverse; five methods differ only explicit version/path/candidate pin substitutions. Normalization additionally contains byte-exact reviewed RX13 reuse block with exact completed TX02 gold path and only one fresh gate loop.',
        'Gold source netlist, original normalization inputs including Liberty and executable, native script/log and entire compressed/expanded graph rehashed. New gate binds exact completed TX03 candidate. Reused gold retains native_reexecuted=False and receipt provenance.',
        'Proof gate binds exact before/after methods, native graphs, runtime, commands, outputs, expected 3850 states/11680 functions and ten genuine kernel controls. The separate ten binding controls are explicitly synthetic validator integrity cases, not DUT proof.',
        'Canonical proof traverses the complete binary primitive/state/output graph with fail-closed unsupported cells, duplicate drivers, cycles, port census and uninitialized boundary checks; no changed comparison semantics.',
        'Physical replay requires exact proof binding, native model hash and all three unchanged serial-word tests with failed/skipped counts zero. All compiled program bytes are gzip verified before removal. No SDF, parasitic, timing closure or full PHY acceptance asserted.',
        'Inherited runners retain one allowed CPU, 2 GiB address-space cap, shared scratch floor, masked spawn registration, new process groups, explicit failure cleanup and no healthy elapsed watchdog. No new runtime execution performed by this review.'
    ],
    'limitations': ['Source and saved-input review only. New gate normalization, actual complete proof, ten kernel controls, ten binding controls and three actual port cases remain required.',
                    'No reviewed producer method, proof/test suite, simulator or EDA executable was imported or executed. This review does not certify timing, routed geometry, analog behavior or PCIe compliance.']
}
output = S / 'proof-source-only-peer-vco.json'
assert not output.exists()
output.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'path': str(output), **pin(output), 'status': record['status']}))
