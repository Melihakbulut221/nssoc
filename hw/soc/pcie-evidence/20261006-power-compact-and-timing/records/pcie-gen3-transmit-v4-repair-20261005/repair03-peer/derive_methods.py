# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Add fresh TX03 dependent methods with full byte inverse ledgers."""
from pathlib import Path
import ast,difflib,hashlib,json
R=Path.cwd();B=R/'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005';O=B/'repair03-peer';C=B/'repair03-continuation01';RX=R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair13-continuation01'
def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
bridges=[]
def save(old,new,text,why):
 original=old.read_text();assert not new.exists();ast.parse(text)
 new.write_text(text);a=original.splitlines(True);z=text.splitlines(True)
 ops=[dict(tag=tag,before=''.join(a[i:j]),after=''.join(z[k:l])) for tag,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes()]
 assert ''.join(x['before'] for x in ops)==original and ''.join(x['after'] for x in ops)==text
 bridges.append(dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),why=why,opcodes=ops))
def versions(s):
 for a,z in [('TX02','TX03'),('tx02','tx03'),('repair02','repair03'),('repair-02','repair-03'),('proof02','proof03')]:s=s.replace(a,z)
 return s.replace('repair03-drt-03','repair03-drt-01').replace('repair03-detailed-rc-02','repair03-detailed-rc-01').replace('repair01-detailed-rc-01','repair02-detailed-rc-02')
old=B/'repair02-peer/review.py';s=versions(old.read_text());save(old,O/'review.py',s,'Only new TX03 roots/methods and actual completed TX02 RC02 as prior timing baseline; same saved data predicates/dynamic measurements.')
old=B/'repair02-peer/seal.py';s=versions(old.read_text())
s=s.replace('candidate/proof/ports/DRT03/RC02','candidate/proof/ports/DRT01/RC01')
s=s.replace('drt_repair03_resume03.py','drt_repair03.py').replace('detailed_rc_repair03_resume03.py','detailed_rc_repair03.py').replace('continue_tx03_v3.py','repair03-continuation01/run.py')
s=s.replace("['repair03-source', 'repair01-peer']","['repair03-source', 'repair02-peer']")
s=s.replace("'source-derivation.json', 'source-only-peer-rx.json', 'sealer-source-only-peer.json'","'source-derivation.json', 'source-freeze.json'")
needle="files['validation.json'] = V"
addition="""for name in ['run.py', 'manifest.json', 'source-only-peer-vco.json', 'launch-preflight.json', 'active-controller.json']:
    files['continuation/' + name] = B / 'repair03-continuation01' / name
files['validation.json'] = V"""
assert s.count(needle)==1;s=s.replace(needle,addition)
save(old,O/'seal.py',s,'TX03 five mandatory roots and methods; preserve prior published TX02 metadata/RC baseline; current reviewed single combined chain peer and sourcefreeze; unique TX03 archive/validation names. Full gzip/member checks and200MiB cap unchanged.')
old=RX/'run.py';s=old.read_text().replace('pcie-gen3-receive-prefetch-v2-20261004','pcie-gen3-transmit-v4-repair-20261005').replace('nssoc-rx-prefetch-v2','nssoc-tx-path-v4').replace('RX13','TX03').replace('repair13','repair03').replace('pcie-rx-repair03','pcie-tx-repair03').replace('CPU8','CPU4').replace('{8}','{4}').replace('[8]','[4]')
save(old,C/'run.py',s,'Corrected exact RX13 durable lifecycle, boot/PID/start/source/output gates and terminal signal guards reused. Only TX03 paths/status/unique asset names and CPU4 assignment; no lifecycle or timing predicate change.')
(O/'source-derivation.json').write_text(json.dumps(bridges,indent=2)+'\n')
freeze=dict(status='FROZEN_TX03_REVIEW_SEAL_DURABLE_CONTROLLER_BEFORE_EXECUTION',sources={str(p):pin(p) for p in [O/'review.py',O/'seal.py',C/'run.py',O/'source-derivation.json',Path(__file__)]},inherited_lifecycle_controls={str(p):pin(p) for p in [RX/'run.py',RX/'lifecycle-controls.json',RX/'check_lifecycle_boundaries.py',RX/'source-only-peer-vco.json']},native_executed=False)
(O/'source-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
print(json.dumps(freeze,indent=2))
