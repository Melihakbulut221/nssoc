# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Local matched SRAM mapping only; strict boot and physical acceptance separate."""
from pathlib import Path
import hashlib, json, os, resource, shutil, signal, subprocess, sys, time
R=Path.cwd(); B=Path(__file__).absolute().parent; O=B/'native01'
sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005'))
import run_cloud_alu_qualification as q
import prepare_npu_reconvergence_eco as eco
import check_npu_physical_eco_mapping as bridge
from owned_lifecycle05 import owned_popen, stop_failed_group

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def on_signal(n,f):raise InterruptedError(f'Signal {n}')
def limits():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3));os.sched_setaffinity(0,{0})
 signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGINT,signal.SIGTERM})
def run():
 for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,on_signal)
 frozen=json.loads((B/'source-freeze01.json').read_text())
 for p,h in frozen['inputs'].items():assert pin(p)==h,p
 O.mkdir(); lock=json.loads((R/q.LOCK).read_text());syn=q.alu.validate_lock(json.loads((R/q.alu.LOCK).read_text()))
 bundle=O/'inputs';snapshot=O/'snapshot';q.restore_inputs(lock,bundle);q.alu.restore(R/syn['archive']['path'],snapshot,syn)
 sources={name:Path(p) for name,p in frozen['netlists'].items()};assert eco.prepare(sources['candidate'].read_bytes())==sources['factored'].read_bytes()
 physical=json.loads((bundle/'physical-config.json').read_text());yosys=R/'hw/soc/tools/oss-cad-suite/bin/yosys';assert pin(yosys)['sha256']==syn['synthesis_yosys_sha256']
 r=dict(status='RUNNING_EXACT_SRAM_MAPPING',source_freeze=pin(B/'source-freeze01.json'),stages={},full_soc_functional_accepted=False,timing_accepted=False,healthy_elapsed_timeout=None,scope=__doc__)
 def save():(O/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  for name in ('original','candidate','factored'):
   assert shutil.disk_usage(O).free>2*1024**3
   for p,h in frozen['inputs'].items():assert pin(p)==h,p
   out=O/name;out.mkdir();script=out/'map.ys';script.write_text(q.mapping_recipe((bundle/'recipe/original-map.ys').read_text(),sources[name],out,bundle,snapshot,syn))
   command=[str(yosys),'-s',str(script)];stage=dict(command=command,recipe=pin(script),status='RUNNING');r['stages'][name]=stage;save();p=None;complete=False;t=time.monotonic()
   try:
    with (out/'native.log').open('x') as log:
     old=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
     try:p=owned_popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limits)
     finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)
     stage['identity']=p.nssoc_owned_identity;save()
     while p.poll() is None:
      if shutil.disk_usage(O).free<1024**3:raise RuntimeError('SSD floor')
      time.sleep(.2)
     stage['returncode']=p.wait();assert stage['returncode']==0
     assert shutil.disk_usage(O).free>=1024**3;complete=True
   finally:
    if p is not None and not complete:stop_failed_group(p)
   before=json.loads((out/'before.json').read_text())['modules']['soc_top'];after=json.loads((out/'after.json').read_text())['modules']['soc_top']
   stage['mapping_contract']=q.mapping_contract(before,after,physical);del before,after
   net=pin(out/'soc_top.netlist.v')
   if name in ('original','candidate'):assert net['sha256']==frozen['expected_mapping'][name]
   stage.update(status='PASS_MAPPING_CONTRACT',netlist=net,elapsed_seconds=time.monotonic()-t,outputs={p.name:pin(p) for p in out.iterdir() if p.is_file()});save()
  candidate=json.loads((O/'candidate/after.json').read_text())['modules']['soc_top'];factored=json.loads((O/'factored/after.json').read_text())['modules']['soc_top']
  r['exact_combinational_bridge']=bridge.check(candidate,factored);del candidate,factored
  for p,h in frozen['inputs'].items():assert pin(p)==h,p
  for root,files in [(bundle,lock['files']),(snapshot,syn['files'])]:
   for name,h in files.items():assert pin(root/name)=={k:h[k] for k in ('bytes','sha256')}
  r['status']='PASS_MATCHED32SRAM_MAPPING_AND_EXACT_ECO_BRIDGE_BOOT_PHYSICAL_PENDING'
 except BaseException as e:r.update(status='FAILED_PRESERVED',error=repr(e));raise
 finally:save()
if __name__=='__main__':run()
