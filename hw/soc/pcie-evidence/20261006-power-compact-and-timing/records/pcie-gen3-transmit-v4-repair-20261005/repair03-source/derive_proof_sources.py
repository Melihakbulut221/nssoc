# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Freeze TX03 proof methods; reuse the identical completed original graph."""
from pathlib import Path
import difflib
import hashlib
import json

B=Path('hw/soc/out/pcie-gen3-transmit-v4-repair-20261005').resolve()
S=B/'repair03-source'
C=Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-03')


def pin(path):
    path=Path(path)
    with path.open('rb') as f:
        return {'bytes':path.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}


result=json.loads((C/'result.json').read_text())
assert result['status']=='COMPLETE_CANDIDATE_REQUIRES_EQUIVALENCE_ROUTE_RC' and result['returncode']==0
assert result['inputs']=={p:pin(p) for p in result['inputs']}
assert result['outputs']=={p.name:pin(p) for p in C.iterdir() if p.is_file() and p.name!='result.json'}
new_pin=pin(C/'repaired.v')
old_pin={'bytes':4174181,'sha256':'5e964dabf6aa8a0d8a42a8ac9adbd0320b668ab350bf3a3ad9f9bd0402f62c90'}
bridges=[]
sources={}


def save(oldpath,newpath,after):
    before=oldpath.read_text()
    assert not newpath.exists()
    newpath.parent.mkdir(exist_ok=True)
    newpath.write_text(after)
    a=before.splitlines(True);z=after.splitlines(True)
    ops=[{'tag':tag,'before':''.join(a[i:j]),'after':''.join(z[k:l])}
         for tag,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes()]
    assert ''.join(x['before'] for x in ops)==before
    assert ''.join(x['after'] for x in ops)==after
    bridges.append({'before':{'path':str(oldpath),**pin(oldpath)},
                    'after':{'path':str(newpath),**pin(newpath)},'opcodes':ops})
    sources[str(newpath)]=pin(newpath)


def changed(text):
    return text.replace('repair02','repair03').replace('repair-02','repair-03').replace('proof02','proof03').replace('TX02','TX03').replace('tx02','tx03').replace('candidate02','candidate03').replace(repr(old_pin),repr(new_pin))


norm=(B/'normalize_repair02.py').read_text()
after=changed(norm)
reuse_template=Path('hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/normalize_repair13.py').read_text()
start=reuse_template.index('# Reuse identical completed originalgold')
end=reuse_template.index('\ndef limits():',start)
reuse=reuse_template[start:end].replace('/dev/shm/nssoc-rx-prefetch-v2-repair11-equivalence','/dev/shm/nssoc-tx-path-v4-repair02-equivalence')
old="pins={str(p):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in inputs}\nrecord={'inputs':pins,'scope':'Native Liberty functional expansion, no blackboxes or assumptions','runs':[]}"
assert after.count(old)==1
after=after.replace(old,reuse)
oldloop="for name,net in [('gold',inputs[-2]),('gate',inputs[-1])]:"
assert after.count(oldloop)==1
after=after.replace(oldloop,"for name,net in [('gate',pathlib.Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-03/repaired.v'))]:")
save(B/'normalize_repair02.py',B/'normalize_repair03.py',after)
for oldname,newname in [('proof_gate_repair02.py','proof_gate_repair03.py'),('replay_repair02.py','replay_repair03.py'),('proof02/compare.py','proof03/compare.py'),('proof02/mutations.py','proof03/mutations.py'),('repair02-source/test_proof_binding.py','repair03-source/test_proof_binding.py')]:
    oldpath=B/oldname
    save(oldpath,B/newname,changed(oldpath.read_text()))
(S/'proof-source-bridge.json').write_text(json.dumps(bridges,indent=2)+'\n')
freeze={'status':'FROZEN_TX03_NEW_GATE_AND_PROOF_PORT_METHODS_NO_NATIVE_EXECUTION',
        'method':pin(__file__),'candidate':{'path':str(C/'repaired.v'),**new_pin},
        'candidate_result':pin(C/'result.json'),'files':sources,
        'bridge':pin(S/'proof-source-bridge.json'),
        'gold_reuse_template':{'path':str(Path('hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/normalize_repair13.py').resolve()),**pin('hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/normalize_repair13.py')},
        'original_gold':{'path':'/dev/shm/nssoc-tx-path-v4-repair02-equivalence/normalization.json',**pin('/dev/shm/nssoc-tx-path-v4-repair02-equivalence/normalization.json')},
        'scope':'Six methods changed only versions/paths/new candidate pin, plus exact reviewed originalgold reuse block from RX13 with TX02 completed gold directory. New gate normalization,3850state11680function proof,tenkernel+tenbinding controls andthreeactualports required. No timing/physical claim.'}
(S/'proof-source-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
print(json.dumps(freeze,indent=2))
