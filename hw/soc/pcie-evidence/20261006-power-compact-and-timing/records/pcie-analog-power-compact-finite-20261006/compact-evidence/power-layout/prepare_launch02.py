from pathlib import Path
import hashlib,json,os,shutil
R=Path.cwd();B=Path(__file__).resolve().parent;D=R/'hw/soc/out/pcie-divider-v7-layout-20261005'
def pin(p):
 with Path(p).open('rb') as f:return {'bytes':Path(p).stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
f=json.loads((B/'source-freeze02.json').read_text());peerpath=B/'source-only-peer02-rx.json';peer=json.loads(peerpath.read_text())
assert peer['status']=='PASS_SOURCE_ONLY_DIVIDER_V7_POWER_V2' and peer['findings']==[]
assert peer['source_pins']==f['product_sources'] and peer['launcher']==pin(B/'launch02.py')
assert f['inputs']=={p:pin(p) for p in f['inputs']}
inputs=dict(f['inputs']);inputs.update({str(p):pin(p) for p in [B/'source-freeze02.json',peerpath,Path(__file__),B/'source-only-peer-rx-candidate01-findings.json']})
runtime=json.loads((B/'launch-runtime-freeze02.json').read_text());assert runtime['source_freeze']==pin(B/'source-freeze02.json');assert runtime['inputs']=={p:pin(p) for p in runtime['inputs']};assert runtime['PDK_files_already_in_source_freeze']=={p:w for p,w in f['inputs'].items() if p.startswith(runtime['selected_pdk_input_prefix'])};old=json.loads(Path(runtime['prior_manifest']).read_text());assert old['python']==runtime['selected_python'] and old['pdk']==runtime['selected_pdk'];inputs.update(runtime['inputs']);inputs[str(B/'launch-runtime-freeze02.json')]=pin(B/'launch-runtime-freeze02.json');roots={'layout':'/dev/shm/nssoc-div4-v7-power-v2-layout-01','checks':'/dev/shm/nssoc-div4-v7-power-v2-checks-01'}
assert not any(Path(p).exists() for p in roots.values()) and shutil.disk_usage('/dev/shm').free>=1024**3
j={'status':'PEER_PASSED_FRESH_POWER_V2_LAYOUT_NATIVE_LAUNCH','inputs':inputs,'product_sources':f['product_sources'],'source_peer':str(peerpath),'python':old['python'],'pdk':old['pdk'],**roots,'cpu':10,'native_address_space':2*1024**3,'own_scratch_limit':80*1024**2,'shared_continuous_floor':512*1024**2,'entry_floor':1024**3,'launch_reserve':24*1024**2,'healthy_elapsed_watchdog':None,'failure_cleanup_grace_seconds':5,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'native_status':'not_started','qualified_pex':False}
p=B/'launch-manifest02.json';assert not p.exists();p.write_text(json.dumps(j,indent=2)+'\n');print(pin(p))
