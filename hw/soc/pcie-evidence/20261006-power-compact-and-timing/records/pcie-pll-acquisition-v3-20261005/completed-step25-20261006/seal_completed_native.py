"""Preserve completed solver bytes and exact public-part receipts; no native rerun."""
from pathlib import Path
import json,hashlib,tarfile
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-pll-acquisition-v3-step25-detached-02')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
r=json.loads((D/'result.json').read_text());e=json.loads((D/'execution.json').read_text());assert r['status']=='PASS_NATIVE_STREAM_FINITE_SCREEN'and e['returncode']==0
assert r['unchanged_physical_devices']==539 and r['rows']==401607 and r['config']['step_s']==2.5e-12 and r['config']['stop_s']==1e-6
for n,v in r['inputs'].items():assert pin(n)==v
for n,v in r['outputs'].items():assert pin(D/n)==v
assert r['strict_numerical_diagnostics_pass']and r['clean_diagnostics']and r['zero_source_op']
assert r['time_grid']['last_s']==1e-6 and r['time_grid']['endpoint_ulp_distance']==0 and not r['time_grid']['raw_samples_changed']
a=r['measurement']['acquisition'];assert a['passed']and a['final_two_windows_no_slip']and not a['ordinal_discontinuities']and not a['ambiguous_pairings']
assert [v['interval_s']for v in a['fixed_acceptance_windows']]==[[8e-7,9e-7],[9e-7,1e-6]]
assert all(v['passed']and all(v['checks'].values())and abs(v['frequency_error_ppm'])<=100 and v['phase_span_s']<=50e-12 for v in a['fixed_acceptance_windows'])
parts=json.loads((D/'capture/parts/parts.json').read_text());assert parts['status']=='PASS_PUBLISHED_PARTS'and len(parts['parts'])==159 and parts['rows']==r['rows']and parts['no_decimation']
rows=0;assets=[];receipts=[]
for index,item in enumerate(parts['parts']):
 assert item['index']==index and item['first_row']==rows and item['status']=='PUBLIC_VERIFIED'and item['local_state']=='REMOVED_EXACT_PUBLIC_DUPLICATE';rows+=item['rows']
 p=D/'capture/parts'/f'publication-{index:05d}.json';assert pin(p)['sha256']==item['receipt_sha256'];j=json.loads(p.read_text());assert j['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'and len(j['assets'])==1
 asset=j['assets'][0];assert asset==item['asset']and asset['authenticated_roundtrip']and asset['anonymous_roundtrip']
 assert all(asset[k]==item[k]for k in ['name','bytes','sha256']);assert item['uncompressed_bytes']==item['rows']*len(r['columns'])*8
 assets.append(asset);receipts.append(dict(path=str(p),**pin(p)))
assert rows==r['rows']and parts['payload_sha256']==r['payload_sha256']
files={}
for p in D.rglob('*'):
 if p.is_file()and not p.is_symlink():files['native/'+str(p.relative_to(D))]=p
for name in ['launch_acquisition25.py','policy.json','source-peer-vco.json','native-start-receipt.json','command-runtime.json','detach_launch.py']:
 p=B.parent/'launch02'/name;assert p.is_file();files['launch02/'+name]=p
files['method/seal_completed_native.py']=Path(__file__)
mp=B/'members.json';assert not mp.exists();manifest={n:dict(original_path=str(p),**pin(p))for n,p in sorted(files.items())};mp.write_text(json.dumps(manifest,indent=2)+'\n')
archive=B/'pcie-pll-acquisition-v3-step25-completed-native-20261006.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=3)as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(archive,'r:xz')as t:
 assert set(t.getnames())==set(manifest)|{'members.json'}
 for m in t.getmembers():
  v=pin(mp)if m.name=='members.json'else manifest[m.name];assert m.isfile()and m.size==v['bytes']
  with t.extractfile(m)as f:assert hashlib.file_digest(f,'sha256').hexdigest()==v['sha256']
for n,p in files.items():assert pin(p)=={k:manifest[n][k]for k in ['bytes','sha256']}
v=dict(status='PRESERVED_COMPLETED_NATIVE_PLL_FINITE_SCREEN_PUBLIC_REPLAY_REQUIRED',native_result=dict(path=str(D/'result.json'),**pin(D/'result.json')),execution=dict(path=str(D/'execution.json'),**pin(D/'execution.json')),inputs_checked=len(r['inputs']),outputs_checked=len(r['outputs']),row_count=r['rows'],column_count=len(r['columns']),unchanged_devices=539,step_s=2.5e-12,stop_s=1e-6,elapsed_seconds=e['elapsed_seconds'],peak_own_bytes=e['max_own_artifact_bytes'],fixed_windows=a['fixed_acceptance_windows'],sustained_window_start_s=a['sustained_window_start_s'],sustained_confirmation_s=a['sustained_confirmation_s'],strict_numerical_diagnostics_pass=True,raw_sha256=r['raw_sha256'],payload_sha256=r['payload_sha256'],canonical_payload_sha256=r['canonical_payload_sha256'],public_parts=assets,publication_receipts=receipts,archive=dict(path=str(archive),**pin(archive),members=len(manifest)+1),full_readback=True,whole_public_raw_replayed=False,paired_step_convergence_checked=False,lock_demonstrated=False,scope='Finite nominal schematic100ppm/50ps acquisition screen only. Native completed with exact539devices/time0to1us/2.5ps and159 public parts, all source/output hashes and publication receipts rechecked. This sealer does not download/replay whole public waveform or compare5ps pair. No PVT/phase noise/jitter/thermal/extracted-layout/foundry/fullPHY acceptance.')
p=B/'pcie-pll-acquisition-v3-step25-completed-native-validation-20261006.json';assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(dict(archive=v['archive'],validation=pin(p),public_parts=len(assets))))
