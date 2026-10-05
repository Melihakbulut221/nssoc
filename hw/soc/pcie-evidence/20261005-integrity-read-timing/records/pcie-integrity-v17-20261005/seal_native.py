"""Seal finite native V17 measurements without claiming timing closure."""
from pathlib import Path
import json,hashlib,tarfile
R=Path.cwd();B=Path(__file__).resolve().parent
D={k:Path('/dev/shm')/('nssoc-integrity-v17-balanced-'+k+'-01') for k in ['map','import','sta']}
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert json.loads((B/'continuation-status03.json').read_text())['status']=='COMPLETE_NATIVE_SCREEN_FINITE_REVIEW_AND_PUBLICATION_REQUIRED'
files={};records={}
for k,status in [('map','COMPLETE_NATIVE_MAP_FUNCTIONAL_REPLAY_REQUIRED'),('import','PASS_GRAPH_METADATA_AND_LITERAL_TIE_IMPORT'),('sta','COMPLETE_PREPLACEMENT_SCREEN_REVIEW_REQUIRED')]:
 d=D[k];q=json.loads((d/'result.json').read_text());assert q['status']==status;records[k]=dict(path=str(d/'result.json'),**pin(d/'result.json'))
 ins=q['inputs'] if k!='sta' else q['cases'][0]['source_pins']
 for p,v in ins.items():assert pin(p)==v
 outs=q['outputs'] if k!='sta' else q['cases'][0]['outputs'];base=d if k!='sta' else d/'rx'
 for name,v in outs.items():assert pin(base/name)==v
 for p in d.rglob('*'):
  if p.is_file() and not p.is_symlink():files[k+'/'+str(p.relative_to(d))]=p
# All completed methods, lifecycle failures/peers, and predecessor preservation
# capsules are included. This cutoff precedes publication and ready receipt.
for p in B.rglob('*'):
 if p.is_file() and not p.is_symlink():files['method/'+str(p.relative_to(B))]=p
ca=Path('/dev/shm/pcie-integrity-v17-default-controls-20261005.tar.xz');files['controls/'+ca.name]=ca
f=json.loads((B/'source-freeze.json').read_text())
for n,v in f['files'].items():assert pin(R/n)==v;files['source/'+n]=R/n
manifest={n:dict(original_path=str(p),**pin(p)) for n,p in sorted(files.items())};mp=B/'native-members.json';assert not mp.exists();mp.write_text(json.dumps(manifest,indent=2)+'\n')
a=Path('/dev/shm/pcie-integrity-v17-native-preplacement-20261005.tar.xz');assert not a.exists()
with tarfile.open(a,'w:xz',preset=3) as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz') as t:
 assert set(t.getnames())==set(manifest)|{'members.json'}
 for m in t.getmembers():
  expected=pin(mp) if m.name=='members.json' else manifest[m.name];assert m.isfile() and m.size==expected['bytes']
  with t.extractfile(m) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected['sha256']
proof=json.loads((B/'balanced-import-graph-proof.json').read_text());assert proof['status']=='PASS_COMPLETE_NATIVE_CELL_PIN_AND_PORT_DRIVER_GRAPH'
timing=json.loads((B/'timing-comparison.json').read_text());assert not timing['acceptance']
x=dict(status='SEALED_ACTUAL_4NS_PREPLACEMENT_GAIN_WITH_RESIDUAL_SETUP',source_freeze=pin(B/'source-freeze.json'),source_peer=pin(B/'source-only-peer-rx.json'),lifecycle_peer=pin(B/'continuation-source-only-peer-root03.json'),native_results=records,timing_comparison=timing,native_import_full_pin_proof=proof,native_read_depth=pin(B/'native-read-depth-comparison.json'),critical_path=pin(B/'critical-path-attribution.json'),archive=dict(path=str(a),**pin(a),members=len(manifest)+1),full_readback=True,scope='V17 fromfrozenV11 uses staticbalanced knowneligibility/payloadmux withcompleteconstant-word eventlist. Native100817cells/9410FF, read_pointer tooutput D31/32cells versusrejectedV14 62. Same4ns repairedsetupSS−3.336283,TT−0.611557,FF+0.943533ns; gains0.215728/0.147133/0.087128ns vsV11 butareaincreased17039cells. Holdspositive. V11 remainsbaseline; noadoption orwholechipclosure. Controls39executions/38distinct and2MAX4118excluded, source/lifecyclepeers, actualnativegraphproof6mutants preserved. OriginalV16incomplete andactualteardownrace retained; no rerun ofcompletedcontrols/native. NoMAX4118/fullformal/mappedfunctionalreplay/place/CTS/route/RC/PHY/productionacceptance.',physical_acceptance=False)
p=B/'pcie-integrity-v17-native-validation-20261005.json';assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({'archive':x['archive'],'validation':pin(p)}))
