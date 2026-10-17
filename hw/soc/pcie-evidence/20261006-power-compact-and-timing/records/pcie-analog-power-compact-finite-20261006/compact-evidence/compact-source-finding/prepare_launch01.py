"""Prepare exact current boot manifest after independent source peer; no launch."""
from pathlib import Path
import hashlib,json,shutil
B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())

fpath=B/'source-freeze01.json';peerpath=B/'source-only-peer01-rx.json'
f=json.loads(fpath.read_text());peer=json.loads(peerpath.read_text())
assert peer['status']=='PASS_SOURCE_ONLY_DIVIDER_V7_COMPACT_V1' and peer['findings']==[]
assert peer['source_pins']==f['product_sources'] and peer['launcher']==pin(B/'launch01.py')
assert f['inputs']=={p:pin(p) for p in f['inputs']}
assert f['python'] in f['inputs'] and f['pdk'].endswith('/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2')
assert len([p for p in f['inputs'] if p.startswith(f['pdk']+'/')])>=90
assert all(not Path(f[n]).exists() for n in ('layout','checks'))
assert shutil.disk_usage('/dev/shm').free>=1024**3
inputs=dict(f['inputs']);inputs.update({str(p):pin(p) for p in [fpath,peerpath,Path(__file__)]})
out=dict(status='PEER_PASSED_FRESH_COMPACT_GENERATION_AND_NATIVE_CHECKS',inputs=inputs,product_sources=f['product_sources'],source_peer=str(peerpath),python=f['python'],pdk=f['pdk'],layout=f['layout'],checks=f['checks'],cpu=10,native_address_space=2*1024**3,own_scratch_limit=80*1024**2,shared_continuous_floor=512*1024**2,entry_floor=1024**3,launch_reserve=24*1024**2,healthy_elapsed_watchdog=None,failure_cleanup_grace_seconds=5,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),native_status='not_started',qualified_pex=False)
p=B/'launch-manifest01.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(pin(p))
