# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json,os,pathlib,resource,subprocess,time,signal,gzip,shutil
def on_signal(signum,frame):raise InterruptedError(f'Parent signal {signum}')
for s in (signal.SIGTERM,signal.SIGINT):signal.signal(s,on_signal)
root=pathlib.Path.cwd()
out=pathlib.Path('/dev/shm/nssoc-tx-path-v4-repair03-equivalence')
while shutil.disk_usage('/dev/shm').free<1024**3:time.sleep(5)
out.mkdir(exist_ok=False)
lib=pathlib.Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib')
yosys=root/'hw/soc/tools/oss-cad-suite/bin/yosys'
inputs=[pathlib.Path(__file__).resolve(),lib,yosys,root/'hw/soc/tools/oss-cad-suite/libexec/yosys',pathlib.Path('/dev/shm/nssoc-tx-path-v4-drt-01/routed.v'),pathlib.Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-03/repaired.v')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert {'bytes':inputs[-1].stat().st_size,'sha256':sha(inputs[-1])} == {'bytes': 4175074, 'sha256': '6a284e00cc05f36537fd2b0abfe2854cab433fb41f634989d947a3d987a00c97'}
# Reuse identical completed originalgold native expansion; only new gate is run.
old_gold=pathlib.Path('/dev/shm/nssoc-tx-path-v4-repair02-equivalence')
old_normalization=json.loads((old_gold/'normalization.json').read_text())
assert old_normalization['inputs']=={p:{'bytes':pathlib.Path(p).stat().st_size,'sha256':sha(pathlib.Path(p))} for p in old_normalization['inputs']}
goldrow=old_normalization['runs'][0]
assert goldrow['name']=='gold' and goldrow['returncode']==0
assert sha(old_gold/'gold.ys')==goldrow['script_sha256']
assert sha(old_gold/'gold.log')==goldrow['log_sha256']
assert sha(old_gold/'gold.json.gz')==goldrow['expanded_json']['lossless_gzip_sha256']
with gzip.open(old_gold/'gold.json.gz','rb') as stream:
 h=hashlib.sha256();size=0
 while data:=stream.read(1024**2):h.update(data);size+=len(data)
assert {'bytes':size,'sha256':h.hexdigest()}=={k:goldrow['expanded_json'][k] for k in ('bytes','sha256')}
for suffix in ['.ys','.log','.json.gz']:
 source=old_gold/('gold'+suffix);target=out/('gold'+suffix)
 with source.open('rb') as a,target.open('xb') as z:shutil.copyfileobj(a,z,1024**2)
 assert sha(source)==sha(target)
inputs += [old_gold/'normalization.json',old_gold/'gold.ys',old_gold/'gold.log',old_gold/'gold.json.gz',*(pathlib.Path(p) for p in old_normalization['inputs'])]
pins={str(p):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in inputs}
record={'inputs':pins,'scope':'Originalgold is byte-verified reuse of previously completed native expansion; fresh gate native Liberty functional expansion, no blackboxes or assumptions','runs':[dict(goldrow, reused_from=str(old_gold), native_reexecuted=False)],'reused_gold_normalization_pin':{'bytes':(old_gold/'normalization.json').stat().st_size,'sha256':sha(old_gold/'normalization.json')}}
def limits():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGINT,signal.SIGTERM})
def stop_failed_group(process, grace_seconds=5.0):
    try:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + grace_seconds
        while time.monotonic() < deadline:
            time.sleep(min(0.05, max(0, deadline - time.monotonic())))
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        finally:
            process.wait()
for name,net in [('gate',pathlib.Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-03/repaired.v'))]:
 script=out/(name+'.ys')
 script.write_text(f'read_liberty -ignore_miss_func {lib}\nread_verilog {net}\nhierarchy -check -top soc_pcie_gen3_tx_path_v4\nflatten\nproc\nopt_clean\ncheck -assert\nstat\nwrite_json {out}/{name}.json\n')
 started=time.monotonic()
 with (out/(name+'.log')).open('w') as f:
  p=None;complete=False
  try:
   previous_mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
   try:p=subprocess.Popen([str(yosys),'-T','-s',str(script)],stdout=f,stderr=subprocess.STDOUT,preexec_fn=limits,start_new_session=True,env={**os.environ,'YOSYS_MAX_THREADS':'1'})
   finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous_mask)
   while p.poll() is None:
    if shutil.disk_usage('/dev/shm').free<528*1024**2:raise RuntimeError('Shared scratch floor')
    time.sleep(.2)
   p.wait()
   if p.returncode!=0:raise RuntimeError(f'Native normalization exit {p.returncode}')
   complete=True
  finally:
   if p is not None and not complete:stop_failed_group(p)
 record['runs'].append({'name':name,'returncode':p.returncode,'elapsed_seconds':time.monotonic()-started,'script_sha256':sha(script),'log_sha256':sha(out/(name+'.log'))})
 (out/'normalization.json').write_text(json.dumps(record,indent=2)+'\n')
 assert p.returncode==0
 plain=out/(name+'.json');compressed=out/(name+'.json.gz')
 digest=sha(plain)
 with plain.open('rb') as a,gzip.open(compressed,'wb',compresslevel=1) as z:shutil.copyfileobj(a,z)
 with gzip.open(compressed,'rb') as z:assert hashlib.file_digest(z,'sha256').hexdigest()==digest
 record['runs'][-1]['expanded_json']={'bytes':plain.stat().st_size,'sha256':digest,'lossless_gzip_sha256':sha(compressed)}
 (out/'normalization.json').write_text(json.dumps(record,indent=2)+'\n')
 plain.unlink()
 assert all(sha(pathlib.Path(p))==row['sha256'] for p,row in pins.items())
print(json.dumps(record,indent=2))
