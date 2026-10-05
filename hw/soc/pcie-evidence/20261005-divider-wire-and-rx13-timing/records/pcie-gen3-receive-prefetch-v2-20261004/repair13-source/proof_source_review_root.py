# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read-only complete source bridge check for new RX13 proof/port execution."""
import ast
import gzip
import hashlib
import json
from pathlib import Path

B = Path('hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004')
S = B / 'repair13-source'


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


freeze = json.loads((S/'proof-source-freeze.json').read_text())
bridge = json.loads((S/'proof-source-bridge.json').read_text())
assert pin(S/'proof-source-bridge.json') == freeze['bridge']
for path, expected in freeze['files'].items():
    assert pin(path) == expected
candidate = freeze['candidate']
assert pin(candidate['path']) == {k: candidate[k] for k in ('bytes', 'sha256')}
candidate_result = Path(candidate['path']).parent/'result.json'
assert pin(candidate_result) == freeze['candidate_result']
result = json.loads(candidate_result.read_text())
assert result['status'] == 'COMPLETE_CANDIDATE_REQUIRES_EQUIVALENCE_ROUTE_RC'
assert result['returncode'] == 0
replacements = [('repair12','repair13'), ('repair-12','repair-13'),
                ('RX12','RX13'), ('rx12','rx13'),
                ("'bytes': 2092773, 'sha256': 'ce021e9eaba2d4db461cf5207a86a0ded9790830000248b6ec4eb0984b43a9a4'",
                 "'bytes': 2093617, 'sha256': '533ecba38bc02e0f08cf96e9aef1e71682141de26dd772bc965abe9619c6ab34'")]
checks = []
for item in bridge:
    before = Path(item['before']['path']).read_text()
    after = Path(item['after']['path']).read_text()
    assert pin(item['before']['path']) == {k: item['before'][k] for k in ('bytes','sha256')}
    assert pin(item['after']['path']) == {k: item['after'][k] for k in ('bytes','sha256')}
    assert ''.join(o['before'] for o in item['opcodes']) == before
    assert ''.join(o['after'] for o in item['opcodes']) == after
    expected = before
    for old, new in replacements:
        expected = expected.replace(old, new)
    assert expected == after
    inverse = after
    for old, new in reversed(replacements):
        inverse = inverse.replace(new, old)
    assert inverse == before
    assert ast.dump(ast.parse(expected), include_attributes=False) == ast.dump(ast.parse(after), include_attributes=False)
    checks.append({'source': item['after'], 'whole_source_reversible_allowed_substitutions': True})
gold = freeze['reused_original_gold']
assert pin(gold['path']) == {k: gold[k] for k in ('bytes','sha256')}
gr = json.loads(Path(gold['path']).read_text())
for name, expected in gr['inputs'].items():
    assert pin(name) == expected
g = gr['runs'][0]
assert g['name'] == 'gold' and g['returncode'] == 0
base = Path(gold['path']).parent
assert pin(base/'gold.ys')['sha256'] == g['script_sha256']
assert pin(base/'gold.log')['sha256'] == g['log_sha256']
assert pin(base/'gold.json.gz')['sha256'] == g['expanded_json']['lossless_gzip_sha256']
h = hashlib.sha256()
size = 0
with gzip.open(base/'gold.json.gz','rb') as f:
    while data := f.read(1048576):
        h.update(data)
        size += len(data)
assert {'bytes':size, 'sha256':h.hexdigest()} == {k:g['expanded_json'][k] for k in ('bytes','sha256')}
out = {'status':'PASS_SOURCE_ONLY_RX13_PROOF_AND_SIX_PORT_BINDING', 'findings':[],
       'method':pin(__file__), 'source_freeze':pin(S/'proof-source-freeze.json'),
       'bridge':pin(S/'proof-source-bridge.json'), 'candidate':candidate,
       'allowed_substitutions':replacements, 'sources':checks,
       'original_gold_complete_decompressed_readback':{'bytes':size,'sha256':h.hexdigest()},
       'scope':'All three complete method bodies unchanged except exact version/output paths and new candidate pin. Fresh native gate expansion, canonical comparison with ten faults and six actual ports remain mandatory; no native result claimed by this source review.'}
(S/'proof-source-only-peer-root.json').write_text(json.dumps(out,indent=2)+'\n')
print(out['status'])
