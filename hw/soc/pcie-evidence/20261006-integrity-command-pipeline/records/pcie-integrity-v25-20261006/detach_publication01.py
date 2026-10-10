"""Publish only five sealed V25 assets via unchanged frozen publisherV4."""
from pathlib import Path
import hashlib,json,os,subprocess
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
package_path=B/'pcie-integrity-v25-finite-package-20261006.json'
assert pin(package_path)==dict(bytes=66810,sha256='4eeef2b972e70521161814c96a0c893387d54285bdbc0aaee1febd17e87b2ea6')
package=json.loads(package_path.read_text());assert not package['adopted']
publisher=R/'scripts/publish_pcie_native_capture_v4.py'
assert pin(publisher)==dict(bytes=6585,sha256='1b73bd49b86090a6eeff1cf16af36a2a17a4885bb748ecc301435ee796b3b585')
pf=R/'hw/soc/out/publisher-reconciliation-20261006/source-freeze01.json'
assert pin(pf)==dict(bytes=64049,sha256='7bc519c0fa66900a7b366fe71bb1a3d5c28b6ba93bdb303ed16dd30b20177c64')
freeze=json.loads(pf.read_text())
for field in ('sources','inputs'):
 for p,h in freeze[field].items():assert pin(p)==h,p
paths=[Path(package['archives'][k]['path'])for k in ('historical_failed','current_functional','native','peer_supplement')]+[package_path]
for p in paths[:-1]:
 entry=next(v for v in package['archives'].values()if v['path']==str(p));assert pin(p)=={k:entry[k]for k in ('bytes','sha256')}
assert len({p.name for p in paths})==5 and not(B/'publication-release01.json').exists()
with(B/'publication-once01.json').open('x')as f:json.dump(dict(files={str(p):pin(p)for p in paths},publisher=pin(publisher),publisher_freeze=pin(pf),tag='evidence-20261006-pcie-closure'),f,indent=2)
env=os.environ.copy()
for k in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE','PYTHONOPTIMIZE','LD_PRELOAD'):env.pop(k,None)
cmd=['/usr/bin/taskset','-c','2','/usr/bin/python3',str(publisher),'--tag','evidence-20261006-pcie-closure','--out',str(B/'publication-release01.json'),*map(str,paths)]
with(B/'publication01.log').open('xb')as log:
 p=subprocess.Popen(cmd,cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True,close_fds=True)
 fields=Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()
 receipt=dict(pid=p.pid,start_ticks=fields[19],ppid=int(fields[1]),pgid=int(fields[2]),session=int(fields[3]),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=cmd,method=pin(__file__))
 with(B/'publication-detached01.json').open('x')as f:json.dump(receipt,f,indent=2)
 print(json.dumps(receipt))
