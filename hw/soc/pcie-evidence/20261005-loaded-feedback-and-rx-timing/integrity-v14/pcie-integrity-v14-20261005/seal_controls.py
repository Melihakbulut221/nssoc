# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve full V14 literalread and V11/V14 cyclemiter evidence."""
from pathlib import Path
import json,hashlib,tarfile
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v14-controls01')
def pin(p):
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
f=json.loads((B/'source-freeze.json').read_text());assert '24 passed, 2 deselected' in (B/'controls01.log').read_text()
for n,v in f['files'].items():assert pin(R/n)==v
for name in ['test_v11_v14_cycle_exact_all_p0','test_actual_wide_rx_full_posit0']:
 q=json.loads((D/name/'capture/result.json').read_text());assert q['status']=='PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX' and q['tests']=={'passed':13,'failed':0,'skipped':0}
files={'method/source-freeze.json':B/'source-freeze.json','method/controls01.log':B/'controls01.log','method/seal_controls.py':Path(__file__)}
for n in f['files']:files['source/'+n]=R/n
for d in D.iterdir():
 if d.is_symlink():continue
 for p in d.rglob('*'):
  if p.is_file() and not p.is_symlink():files['controls/'+str(p.relative_to(D))]=p
m={n:{'original_path':str(p),**pin(p)} for n,p in sorted(files.items())};mp=B/'controls-members.json';assert not mp.exists();mp.write_text(json.dumps(m,indent=2)+'\n')
a=Path('/dev/shm/pcie-integrity-v14-default-controls-20261005.tar.xz');assert not a.exists()
with tarfile.open(a,'w:xz',preset=3) as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz') as t:
 assert set(t.getnames())==set(m)|{'members.json'}
 for member in t.getmembers():
  v=pin(mp) if member.name=='members.json' else m[member.name];assert member.isfile() and member.size==v['bytes']
  with t.extractfile(member) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==v['sha256']
x={'status':'PASS_PARALLEL_RING_READ_AND_ACTUAL_PUBLIC_FAULT_CONTROLS','source_freeze':pin(B/'source-freeze.json'),'pytest_executions':24,'distinct_predicates':23,'duplicate_predicate':'Literal inverse executed standalone and throughmiter module','positive_public_cases':26,'actual_RTL_mutants':17,'literal_read_cases':12288,'literal_ring_sizes':[16,64,128],'literal_read_output_bits':243,'default_whole_DUT_MAX_ENCODED_BYTES':150,'default_ring_dwords':64,'excluded_MAX4118_test_ids':2,'archive':{'path':str(a),**pin(a),'members':len(m)+1},'full_readback':True,'scope':'V14onlyparallelconstant-slot read fromfrozenV11. Originaldynamicread versusactualcandidate across4096states each atthree ring sizes, pointerwrap andcount0..4+, plus selectedXdata/keep/verdict/pointer/count tests ofproceduralif masking. Sevenactualselection/maskfaults includeX-verdict leak. Originalserialoracle13cases andV11/V14publiccyclemiter13also compareeveryoccupiedslotmetadata andcommittedverdict, withtwoactualmiterfaultsand8CRC/parserfaults. EveryV11writer,enable,control,fault,commit,pointer/reset remainsunchangedbyliteralinverse. No arbitraryfourstate sequential/fullformal/MAX4118, mappednativefunctionalequivalence/portreplay orphysicaltimingclaim.'}
p=B/'pcie-integrity-v14-core-controls-validation-20261005.json';assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({'archive':x['archive'],'validation':pin(p)}))
