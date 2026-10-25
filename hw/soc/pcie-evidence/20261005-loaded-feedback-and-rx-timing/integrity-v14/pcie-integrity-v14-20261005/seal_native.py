# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal completed rejected V14 native screen and selected-Z counterexamples."""
from pathlib import Path
import json,hashlib,tarfile
R=Path.cwd();B=Path(__file__).resolve().parent
D={k:Path('/dev/shm')/('nssoc-integrity-v14-balanced-'+k+'-01') for k in ['map','import','sta']}
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
files={};records={}
for k,status in [('map','COMPLETE_NATIVE_MAP_FUNCTIONAL_REPLAY_REQUIRED'),('import','PASS_GRAPH_METADATA_AND_LITERAL_TIE_IMPORT'),('sta','COMPLETE_PREPLACEMENT_SCREEN_REVIEW_REQUIRED')]:
 d=D[k];q=json.loads((d/'result.json').read_text());assert q['status']==status;records[k]={'path':str(d/'result.json'),**pin(d/'result.json')}
 ins=q['inputs'] if k!='sta' else q['cases'][0]['source_pins']
 for p,v in ins.items():assert pin(p)==v
 outs=q['outputs'] if k!='sta' else q['cases'][0]['outputs'];base=d if k!='sta' else d/'rx'
 for name,v in outs.items():assert pin(base/name)==v
 for p in d.rglob('*'):
  if p.is_file() and not p.is_symlink():files[k+'/'+str(p.relative_to(d))]=p
names=['run_balanced_map.py','balanced_import.py','balanced_preplacement.py','prove_balanced_import.py','analyze_critical_path.py','review_timing.py','seal_native.py','balanced-map.log','import01.log','preplacement01.log','import-proof01.log','critical-path-attribution.log','timing-review.log','source-freeze.json','signed-wire-census.json','balanced-import-graph-proof.json','timing-comparison.json','critical-path-attribution.json','slow-critical-path.txt','controls-members.json','controls-release.json','controls-validation-release-retry01.json','controls-archive-release-retry01.json','candidate-decision.json','pcie-integrity-v14-core-controls-validation-20261005.json','source-peer.json','design-decision.json','controls01.log']
for name in names:files['method/'+name]=B/name
for p in sorted((B/'peer-selected-z-01').rglob('*')):
 if p.is_file():files['peer-selected-z-01/'+str(p.relative_to(B/'peer-selected-z-01'))]=p
ca=Path('/dev/shm/pcie-integrity-v14-default-controls-20261005.tar.xz');files['controls/'+ca.name]=ca
f=json.loads((B/'source-freeze.json').read_text())
for n,v in f['files'].items():assert pin(R/n)==v;files['source/'+n]=R/n
m={n:{'original_path':str(p),**pin(p)} for n,p in sorted(files.items())};mp=B/'native-members.json';assert not mp.exists();mp.write_text(json.dumps(m,indent=2)+'\n')
a=Path('/dev/shm/pcie-integrity-v14-native-preplacement-20261005.tar.xz');assert not a.exists()
with tarfile.open(a,'w:xz',preset=3) as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz') as t:
 assert set(t.getnames())==set(m)|{'members.json'}
 for member in t.getmembers():
  v=pin(mp) if member.name=='members.json' else m[member.name];assert member.isfile() and member.size==v['bytes']
  with t.extractfile(member) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==v['sha256']
proof=json.loads((B/'balanced-import-graph-proof.json').read_text());assert proof['status']=='PASS_COMPLETE_NATIVE_CELL_PIN_AND_PORT_DRIVER_GRAPH'
timing=json.loads((B/'timing-comparison.json').read_text());assert not timing['acceptance']
controls=json.loads((B/'pcie-integrity-v14-core-controls-validation-20261005.json').read_text())
x={'status':'SEALED_ACTUAL_4NS_PREPLACEMENT_SCREEN','source_freeze':pin(B/'source-freeze.json'),'source_only_peer':pin(B/'source-peer.json'),'native_results':records,'timing_comparison':timing,'native_import_full_pin_proof':proof,'critical_path':pin(B/'critical-path-attribution.json'),'archive':{'path':str(a),**pin(a),'members':len(m)+1},'controls':{'receipt':pin(B/'pcie-integrity-v14-core-controls-validation-20261005.json'),'scope':controls['scope']},'scope':'Rejected V14 constant-slot read experiment directly from frozen V11. Actual SG13 native map, exact all-cell/pin/public-port metadata/tie import with six negative graph controls, unchanged4ns three-corner preplacement compared with stable V11. Setup regresses at all corners. Existing finite inverse/public/occupied/committed and selected-X controls remain bounded passes. Peer produced six actual selected-Z component counterexamples: V11 direct assignment retains Z whereas V14 OR accumulation converts Z to X. These are component counterexamples, not established whole-DUT reachable states. No unrestricted four-state equivalence, MAX4118, mapped functional replay, placement/CTS/route/extracted RC, PHY or timing acceptance. Native work was completed before shutdown and has not been rerun.'}
p=B/'pcie-integrity-v14-native-validation-20261005.json';assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({'archive':x['archive'],'validation':pin(p)}))
