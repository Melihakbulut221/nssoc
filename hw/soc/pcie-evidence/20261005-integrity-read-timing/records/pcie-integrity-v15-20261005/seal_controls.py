# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve full V15 literalread and V11/V15 cyclemiter evidence."""
from pathlib import Path
import json,hashlib,tarfile
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v15-controls01')
def pin(p):
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
f=json.loads((B/'source-freeze.json').read_text());assert '13 passed, 2 deselected' in (B/'controls01.log').read_text();assert '16 passed' in (B/'read01.log').read_text()
for n,v in f['files'].items():assert pin(R/n)==v
for name in ['test_v11_v15_cycle_exact_all_p0','test_actual_wide_rx_full_posit0']:
 q=json.loads((D/name/'capture/result.json').read_text());assert q['status']=='PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX' and q['tests']=={'passed':13,'failed':0,'skipped':0}
files={'method/source-freeze.json':B/'source-freeze.json','method/controls01.log':B/'controls01.log','method/seal_controls.py':Path(__file__)}
for n in f['files']:files['source/'+n]=R/n
for root in [D,Path('/dev/shm/nssoc-integrity-v15-read01')]:
 for d in root.iterdir():
  if d.is_symlink():continue
  for p in d.rglob('*'):
   if p.is_file() and not p.is_symlink():files['controls/'+root.name+'/'+str(p.relative_to(root))]=p
for n in ['read01.log','read01-log-provenance.txt','source-only-peer-rx.json','design-decision.json','source_only_peer_rx.py','source-only-peer-rx.log']:
 if (B/n).is_file():files['method/'+n]=B/n
m={n:{'original_path':str(p),**pin(p)} for n,p in sorted(files.items())};mp=B/'controls-members.json';assert not mp.exists();mp.write_text(json.dumps(m,indent=2)+'\n')
a=Path('/dev/shm/pcie-integrity-v15-default-controls-20261005.tar.xz');assert not a.exists()
with tarfile.open(a,'w:xz',preset=3) as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz') as t:
 assert set(t.getnames())==set(m)|{'members.json'}
 for member in t.getmembers():
  v=pin(mp) if member.name=='members.json' else m[member.name];assert member.isfile() and member.size==v['bytes']
  with t.extractfile(member) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==v['sha256']
x={'status':'PASS_BALANCED_PAYLOAD_TREE_AND_ACTUAL_PUBLIC_FAULT_CONTROLS','source_freeze':pin(B/'source-freeze.json'),'pytest_executions':29,'distinct_predicates':28,'duplicate_predicate':'Literal inverse executed standalone and throughmiter module','positive_public_cases':26,'actual_RTL_mutants':21,'literal_read_cases':12288,'directed_fourstate_cases':59,'literal_ring_sizes':[16,64,128],'literal_read_output_bits':243,'default_whole_DUT_MAX_ENCODED_BYTES':150,'default_ring_dwords':64,'excluded_MAX4118_test_ids':2,'archive':{'path':str(a),**pin(a),'members':len(m)+1},'full_readback':True,'scope':'V15 balanced known-eligibility and payload-mux tree from frozenV11. Original dynamic read versus actual candidate across4096states each at rings16/64/128;59 directed selected X/Z cases for everyfield/fourlanes and unknown ptr/count/keep/verdict plus unselected X/Z isolation. Ten select/mask/tree mutants and one payloadOR Z-conversion mutant fail actualHDL comparisons. Serial oracle13 and V11/V15 public cyclemiter13 include occupiedslot metadata and committedverdict;2miter faults and8parser/CRC faults detected. Exactinverse preserves allV11writers/control. Sourcepeer PASS. No fullformal/MAX4118, mappedfunctional replay or physicaltimingclaim.'}
p=B/'pcie-integrity-v15-core-controls-validation-20261005.json';assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({'archive':x['archive'],'validation':pin(p)}))
