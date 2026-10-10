# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Own only a finite sealer/completer child; never touch the live570 native group."""
from pathlib import Path
import hashlib,json,os,resource,shutil,stat,subprocess,sys,time
F=Path(__file__).resolve().parent;R=Path.cwd();T=F.parent/'pcie-tail115-connected570-tuning-20261006'
sys.path.insert(0,str(T))
import characterize_clamped570_03 as m
AS=2*1024**3;CAP=256*1024**2;FLOOR=512*1024**2;SSD=1024**3

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def guard(*,entry=False):
 assert os.sched_getaffinity(0)=={10}
 shared=shutil.disk_usage('/dev/shm').free;ssd=shutil.disk_usage(F).free
 assert shared>=(1024**3 if entry else FLOOR),'Finite shared floor'
 assert ssd>=SSD+(CAP if entry else 0),'Finite SSD floor'
 total=0
 for p in F.rglob('*'):
  mode=p.lstat().st_mode
  if stat.S_ISDIR(mode):continue
  assert stat.S_ISREG(mode),'No special finite package entries'
  total+=p.stat().st_size
 assert total<=CAP,'Finite256MiB folder cap'
 return dict(shared_free_bytes=shared,ssd_free_bytes=ssd,finite_bytes=total)
def limit():
 resource.setrlimit(resource.RLIMIT_AS,(AS,AS));resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{10})
def main():
 assert len(sys.argv)==2 and sys.argv[1]in ('seal','complete');mode=sys.argv[1];limit();start=time.monotonic();entry=guard(entry=True)
 source=F/('seal_finite01.py'if mode=='seal'else'complete_finite01.py');snap=F/'snapshot-inputs01.json';selection=json.loads(snap.read_text());assert pin(source)==selection['files'][str(source)]
 peerpath=F/'sealer-source-peer-pll01.json';peer=json.loads(peerpath.read_text());assert peer['findings']==[]
 supplement=F/'wrapper-source-peer-pll01.json';p=json.loads(supplement.read_text());assert p['status']=='PASS_SOURCE_ONLY_CLOSED570_FINITE_RESOURCE_WRAPPER'and p['wrapper']==pin(Path(__file__))and p['sealer_peer']==pin(peerpath)and p['snapshot']==pin(snap)and p['findings']==[]
 freeze=T/'source-freeze03.json';assert pin(freeze)==selection['files'][str(freeze)];f=json.loads(freeze.read_text());assert pin(Path(m.__file__))==f['products']['characterize_clamped570_03.py']
 for path in [m.life.__file__,m.life.tiny.__file__]:assert pin(path)==f['pins'][str(Path(path))]
 if mode=='seal':assert not(F/'finite-snapshot01.json').exists()
 else:assert not(F/'ready-finite01.json').exists()
 receipt=F/f'{mode}-execution01.json';assert not receipt.exists();record=dict(status='RUNNING_FINITE_RESOURCE_WRAPPER',mode=mode,source=pin(source),snapshot=pin(snap),wrapper=pin(Path(__file__)),source_peer=pin(peerpath),wrapper_peer=pin(supplement),owner_source=pin(m.life.__file__),entry=entry,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),CPU=10,AS=AS,folder_cap=CAP,elapsed_watchdog=None,live_native_touched=False)
 m.n.common.atomic(receipt,record)
 try:
  env={k:v for k,v in os.environ.items()if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE','PYTHONOPTIMIZE','LD_PRELOAD','GH_TOKEN','GITHUB_TOKEN')};env.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
  logpath=F.parent/f'pcie-570-finite-{mode}01.log'
  with m.life.ProcessOwner(F/f'{mode}-owned01.json')as owner:
   with logpath.open('x')as log:
    child=owner.launch('finite_'+mode,[str(R/'hw/soc/tools/cocotb-venv/bin/python'),str(source)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit)
    while child.poll()is None:owner.check();guard();owner.cancelled.wait(.05)
    rc=owner.complete(child);owner.check();guard();assert rc==0,rc
  owner.check();terminal=guard()
  assert pin(source)==record['source']and pin(snap)==record['snapshot']and pin(Path(__file__))==record['wrapper']
  record.update(status='PASS_CLOSED_FINITE_RESOURCE_WRAPPER',returncode=rc,terminal=terminal,log=pin(logpath),owner=pin(F/f'{mode}-owned01.json'))
 except BaseException as error:record.update(status='FAILED_FINITE_RESOURCE_WRAPPER_RETAINED',error=repr(error));raise
 finally:
  record['elapsed_s']=time.monotonic()-start;m.n.common.atomic(receipt,record)
 guard();print(json.dumps(dict(status=record['status'],receipt=pin(receipt))))
if __name__=='__main__':main()
