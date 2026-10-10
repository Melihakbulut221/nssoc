# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Freeze fresh RX12 proof/port producers only after successful candidate GRT."""
import ast
import hashlib
import json
from pathlib import Path

B = Path(__file__).resolve().parent.parent
O = Path(__file__).resolve().parent
N = Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-12')

def pin(p):
    with p.open('rb') as f:
        return {'bytes': p.stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}

capture = json.loads((N / 'result.json').read_text())
assert capture['status'] == 'COMPLETE_CANDIDATE_REQUIRES_EQUIVALENCE_ROUTE_RC'
assert capture['returncode'] == 0
assert capture['inputs'] == {p: pin(Path(p)) for p in capture['inputs']}
assert capture['outputs'] == {n: pin(N / n) for n in capture['outputs']}
net = pin(N / 'repaired.v')
prior = {'bytes': 2091901, 'sha256': '5043dd664e699c56120673f5dde8e990f804cffa40c9b604034cc57026a1e3fc'}
old_gold = Path('/dev/shm/nssoc-rx-prefetch-v2-repair11-equivalence')
normalization = json.loads((old_gold / 'normalization.json').read_text())
assert normalization['inputs'] == {p: pin(Path(p)) for p in normalization['inputs']}
assert normalization['runs'][0]['name'] == 'gold' and normalization['runs'][0]['returncode'] == 0
sources = {}
changes = {}
for oldname, newname in [('normalize_repair11.py', 'normalize_repair12.py'), ('proof_gate_repair11.py', 'proof_gate_repair12.py'), ('replay_repair11_v2.py', 'replay_repair12.py')]:
    old = B / oldname
    new = B / newname
    assert not new.exists()
    original = old.read_text()
    text = original.replace('repair11', 'repair12').replace('repair-11', 'repair-12').replace('RX11', 'RX12').replace('rx11_', 'rx12_')
    assert repr(prior) in text
    text = text.replace(repr(prior), repr(net))
    if oldname == 'normalize_repair11.py':
        insertion = '''# Reuse identical completed originalgold native expansion; only new gate is run.
old_gold=pathlib.Path('/dev/shm/nssoc-rx-prefetch-v2-repair11-equivalence')
old_normalization=json.loads((old_gold/'normalization.json').read_text())
assert old_normalization['inputs']=={p:{'bytes':pathlib.Path(p).stat().st_size,'sha256':sha(pathlib.Path(p))} for p in old_normalization['inputs']}
goldrow=old_normalization['runs'][0]
assert goldrow['name']=='gold' and goldrow['returncode']==0
assert sha(old_gold/'gold.ys')==goldrow['script_sha256']
assert sha(old_gold/'gold.log')==goldrow['log_sha256']
assert sha(old_gold/'gold.json.gz')==goldrow['expanded_json']['lossless_gzip_sha256']
with gzip.open(old_gold/'gold.json.gz','rb') as stream:
 h=hashlib.sha256();size=0
 while data:=stream.read(1024**2):h.update(data);size+=len(data)
assert {'bytes':size,'sha256':h.hexdigest()}=={k:goldrow['expanded_json'][k] for k in ('bytes','sha256')}
for suffix in ['.ys','.log','.json.gz']:
 source=old_gold/('gold'+suffix);target=out/('gold'+suffix)
 with source.open('rb') as a,target.open('xb') as z:shutil.copyfileobj(a,z,1024**2)
 assert sha(source)==sha(target)
inputs += [old_gold/'normalization.json',old_gold/'gold.ys',old_gold/'gold.log',old_gold/'gold.json.gz',*(pathlib.Path(p) for p in old_normalization['inputs'])]
'''
        text = text.replace('pins={str(p):', insertion+'pins={str(p):')
        text = text.replace("record={'inputs':pins,'scope':'Native Liberty functional expansion, no blackboxes or assumptions','runs':[]}", "record={'inputs':pins,'scope':'Originalgold is byte-verified reuse of previously completed native expansion; fresh gate native Liberty functional expansion, no blackboxes or assumptions','runs':[dict(goldrow, reused_from=str(old_gold), native_reexecuted=False)],'reused_gold_normalization_pin':{'bytes':(old_gold/'normalization.json').stat().st_size,'sha256':sha(old_gold/'normalization.json')}}")
        text = text.replace("for name,net in [('gold',inputs[-2]),('gate',inputs[-1])]:", "for name,net in [('gate',pathlib.Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-12/repaired.v'))]:")
    compile(text, str(new), 'exec')
    new.write_text(text)
    sources[str(new)] = pin(new)
    changes[newname] = {'source': {'path': str(old), **pin(old)}, 'new': {'path': str(new), **pin(new)}, 'change': 'Version/fresh paths and exact new candidate netlist pin only' if oldname != 'normalize_repair11.py' else 'Fresh paths/candidate pin, reuse exact originalgold native outputs with full source/expanded-byte verification, execute only new gate; same native commands and resource/lifecycle code'}
    # Safety-sensitive helper bodies remain exact across the version update.
    a = ast.parse(original); z = ast.parse(text)
    for name in ['limits', 'stop_failed_group', 'owned_execute']:
        before = [node for node in ast.walk(a) if isinstance(node, ast.FunctionDef) and node.name == name]
        after = [node for node in ast.walk(z) if isinstance(node, ast.FunctionDef) and node.name == name]
        if before:
            assert len(before) == len(after) == 1 and ast.dump(before[0]) == ast.dump(after[0]), name
record={'status':'FROZEN_RX12_NEW_GATE_PROOF_AND_PORT_SOURCES_NO_NATIVE_STARTED','generator':pin(Path(__file__)),'candidate':{'path':str(N/'repaired.v'),**net},'candidate_result':pin(N/'result.json'),'files':sources,'changes':changes,'originalgold_normalization':{'path':str(old_gold/'normalization.json'),**pin(old_gold/'normalization.json')},'new_native_required':'New gate normalization, actual canonical compare/mutation execution, and new physical six-port replay. Completed RX11 route/RC/proof are not rerun.','qualified_rc':False,'physical_acceptance':False}
(O/'proof-source-freeze.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
