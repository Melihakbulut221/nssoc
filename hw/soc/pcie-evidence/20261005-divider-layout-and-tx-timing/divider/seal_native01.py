# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal the unchanged first real divider run, including auxiliary parser failure."""
from pathlib import Path
import hashlib,json,tarfile,sys
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'hw/soc/flow')); import check_pcie_clock_div4_v7 as c
ns=c.lifecycle()
def pin(p):
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
manifest=json.loads((B/'launch-manifest01.json').read_text()); identity=json.loads((B/'identity-checkpoint01.json').read_text())['identity']
live=ns['process_identity'](identity['pid']);assert live is None or live['state']=='Z' or live['start_ticks']!=identity['start_ticks']
files={}
for label in ('layout','checks'):
 root=Path(manifest[label])
 for p in sorted(root.rglob('*')):
  if p.is_file(): files['native/'+label+'/'+str(p.relative_to(root))]=p
  if p.name.endswith('.owned.json'):
   for entry in json.loads(p.read_text())['processes']:
    assert not any(x['state']!='Z' for x in ns['group_members'](entry['process_group']))
result=json.loads(Path(manifest['checks'],'result.json').read_text());assert result['status']=='FAILED_OR_INCOMPLETE' and result['error']=="ValueError('Exact unmultiplied straight native passive device')"
assert result['steps'][0]['measurement']['status']=='PASS' and result['steps'][-1]['audit']['status']=='PASS within comparison scope'
excluded={}
for name,expected in manifest['inputs'].items():
 p=Path(name);assert pin(p)==expected
 if p.stat().st_size>2*1024**2: excluded[name]=expected;continue
 rel='project/'+str(p.relative_to(R)) if p.is_relative_to(R) else 'external/'+str(p).lstrip('/')
 files[rel]=p
for name in ('launch-manifest01.json','identity-checkpoint01.json','launch-dispatch01.json','native01.log','source-only-peer01-circuit-and-findings.json','source_peer_circuit01.py','source-peer-boundary-findings01.json','source-controls01.log','source-controls02.log','source-controls03.log','source-controls04.log','source-only-peer03-rx.json','seal_native01.py'):
 files['review/'+name]=B/name
(B/'native01-preservation.json').write_text(json.dumps(dict(status='PRESERVED_ACTUAL_MAIN_DRC_ZERO_DEEP_LVS_MATCH_AUXILIARY_PARSER_FAIL',native_sources_unchanged=True,error=result['error'],not_yet_run=['flat LVS','8reference faults','6physical faults','native LEF and2faults'],excluded_large_runtime_binaries_still_pinned=excluded,physical_acceptance=False),indent=2)+'\n')
files['review/native01-preservation.json']=B/'native01-preservation.json'
members={n:pin(p) for n,p in files.items()}; cap=B/'pcie-divider-v7-native-01-parser-failure.tar.xz';assert not cap.exists()
with tarfile.open(cap,'w:xz',preset=1) as arc:
 for n,p in files.items(): arc.add(p,arcname=n,recursive=False)
seen={}
with tarfile.open(cap,'r|xz') as arc:
 for p in arc:
  assert p.isfile() and p.name not in seen
  seen[p.name]=dict(bytes=p.size,sha256=hashlib.file_digest(arc.extractfile(p),'sha256').hexdigest())
assert seen==members and all(pin(p)==members[n] for n,p in files.items())
(B/'native01-members.json').write_text(json.dumps(members,indent=2)+'\n')
receipt=dict(status='SEALED_ALL_MEMBER_HASHES_VERIFIED_FAILURE_RETAINED',archive=dict(path=str(cap),**pin(cap)),members=len(members),physical_acceptance=False)
(B/'native01-validation.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
