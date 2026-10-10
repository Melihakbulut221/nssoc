"""Seal one completed V18 native screen and preserve all failed harness evidence."""
from pathlib import Path
import datetime,json,hashlib,tarfile,collections
R=Path.cwd();B=Path(__file__).resolve().parent
D={k:Path('/dev/shm')/('nssoc-integrity-v18-balanced-'+k+'-01') for k in ['map','import','sta']}
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def dump(name,obj):
 with (B/name).open('x') as f:json.dump(obj,f,indent=2);f.write('\n')
assert json.loads((B/'continuation-status01.json').read_text())['status']=='COMPLETE_NATIVE_SCREEN_FINITE_REVIEW_AND_PUBLICATION_REQUIRED'
assert json.loads((B/'controls-release01.json').read_text())['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
files={};records={}
for k,status in [('map','COMPLETE_NATIVE_MAP_FUNCTIONAL_REPLAY_REQUIRED'),('import','PASS_GRAPH_METADATA_AND_LITERAL_TIE_IMPORT'),('sta','COMPLETE_PREPLACEMENT_SCREEN_REVIEW_REQUIRED')]:
 d=D[k];q=json.loads((d/'result.json').read_text());assert q['status']==status;records[k]=dict(path=str(d/'result.json'),**pin(d/'result.json'))
 ins=q['inputs'] if k!='sta' else q['cases'][0]['source_pins']
 for p,v in ins.items():assert pin(p)==v
 outs=q['outputs'] if k!='sta' else q['cases'][0]['outputs'];base=d if k!='sta' else d/'rx'
 for name,v in outs.items():assert pin(base/name)==v
 for p in d.rglob('*'):
  if p.is_file() and not p.is_symlink():files[k+'/'+str(p.relative_to(d))]=p
proof=json.loads((B/'balanced-import-graph-proof.json').read_text());assert proof['status']=='PASS_COMPLETE_NATIVE_CELL_PIN_AND_PORT_DRIVER_GRAPH'
timing=json.loads((B/'timing-comparison.json').read_text());assert not timing['acceptance']
freeze=json.loads((B/'source-freeze.json').read_text())
for n,v in freeze['files'].items():assert pin(R/n)==v;files['source/'+n]=R/n
cells=json.loads((D['map']/'mapped.json').read_text())['modules']['soc_pcie_gen3_continuous_rx_integrity_v18']['cells'];counts=collections.Counter(c['type'] for c in cells.values());flops=sum(v for k,v in counts.items() if 'df' in k)
repaired=[x for x in timing['groups'] if x['stage']=='PREPLACEMENT_REPAIRED'];setup={x['corner']:x['worst_slack_ns'] for x in repaired if x['direction']=='max'};hold={x['corner']:x['worst_slack_ns'] for x in repaired if x['direction']=='min'}
prior_cells=json.loads((D['map'].parent/'nssoc-integrity-v17-balanced-map-01/result.json').read_text())['cells']
decision=dict(status='FINITE_NATIVE_SCREEN_COMPLETE_NOT_ADOPTED',native_cells=len(cells),flops=flops,cell_delta_vs_V17=len(cells)-prior_cells,setup_ns=setup,hold_ns=hold,delta_vs_V17=timing['delta_vs_v17'],delta_vs_V11=timing['delta_vs_v11'],stable_baseline='V11',adopted=False,physical_acceptance=False,scope='Same original4ns three-corner preplacement. Residual setup cannot be waived; no mapped functional replay, full route/RC or physical signoff. Actual gate and critical-path evidence determines next experiment.')
dump('candidate-decision.json',decision)
# Snapshot only closed evidence. The sealer stdout is intentionally excluded,
# avoiding the previous V17 empty-self-log cutoff; final summary is separate.
for p in B.rglob('*'):
 if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and p.name not in ['seal-native.log','active-checkpoint.json']:
  files['method/'+str(p.relative_to(B))]=p
manifest={n:dict(original_path=str(p),**pin(p)) for n,p in sorted(files.items())};mp=B/'native-members.json';dump(mp.name,manifest)
a=B/'pcie-integrity-v18-native-preplacement-20261005.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=3) as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz') as t:
 assert set(t.getnames())==set(manifest)|{'members.json'}
 for m in t.getmembers():
  expected=pin(mp) if m.name=='members.json' else manifest[m.name];assert m.isfile() and m.size==expected['bytes']
  with t.extractfile(m) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected['sha256']
# Ensure closed originals did not change while creating or reading archive.
for n,p in files.items():assert pin(p)=={k:manifest[n][k] for k in ['bytes','sha256']}
x=dict(status='SEALED_ACTUAL_4NS_PREPLACEMENT_RESIDUAL_SETUP_NOT_ADOPTED',source_freeze=pin(B/'source-freeze.json'),source_peer=pin(B/'source-only-peer-pll02.json'),native_lifecycle_bridge=pin(B/'native-source-bridge01.json'),native_results=records,native_cell_count=len(cells),flops=flops,timing_comparison=timing,native_import_full_pin_proof=proof,native_read_depth=pin(B/'native-read-depth-comparison.json'),critical_path=pin(B/'critical-path-attribution.json'),candidate_decision=decision,archive=dict(path=str(a),**pin(a),members=len(manifest)+1),full_readback=True,scope='Completed21 functional executions/20distinct,32768 full-parser cases,26publiccases,16actualRTLfaults and6actualnativegraphfaults;2MAX4118excluded. Corrected stimulus/fallbackZ evidence and superseded initial campaign retained. Same2GiB CPU6 original4ns/SS/TT/FF preplacement screen only. V11 stable baseline; no adoption or wholechip closure. No MAX4118/fullformal/mappedfunctionalreplay/place/CTS/route/RC/PHY/productionacceptance. Selfstdout log and mutable operational checkpoint excluded from archive cutoff; final summary separately pinned.',physical_acceptance=False)
p=B/'pcie-integrity-v18-native-validation-20261005.json';dump(p.name,x);print(json.dumps({'archive':x['archive'],'validation':pin(p),'decision':decision}))
