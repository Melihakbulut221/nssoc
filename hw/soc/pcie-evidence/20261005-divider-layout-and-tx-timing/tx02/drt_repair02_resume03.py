# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact detailed wires and nominal unqualified OpenRCX model; no signoff claim."""
from pathlib import Path
import datetime,hashlib,json,resource,subprocess,time,os,signal,shutil,ast,importlib.util
ROOT=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');B=Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-02');OUT=Path('/dev/shm/nssoc-tx-path-v4-repair02-drt-03')
APP=ROOT/'hw/soc/tools/openroad-26Q2-1164/run-openroad'
def on_signal(n,f):raise InterruptedError(f'Parent signal{n}')
for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,on_signal)
while shutil.disk_usage('/dev/shm').free<1024**3:time.sleep(5)
PORT=Path('/dev/shm/nssoc-tx-path-v4-repair02-physical-replay-01/result.json')
assert json.loads(PORT.read_text())['status']=='PASS_EXACT_BOUND_TX02_PHYSICAL_NETLIST_PORT_REPLAY'
e=json.loads(Path('/dev/shm/nssoc-tx-path-v4-repair02-equivalence/equivalence.json').read_text()); assert e['states']==3850 and e['matched']==e['targets']==11680 and not e['mismatches']
f=json.loads(Path('/dev/shm/nssoc-tx-path-v4-repair02-equivalence/mutation-controls.json').read_text()); assert len(f['controls'])==10
assert json.loads(PORT.read_text())['tests']=={'passed':3,'failed':0,'skipped':0}
def pin(p):
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
gate_path=Path(__file__).resolve().parent/'proof_gate_repair02.py'
gate_spec=importlib.util.spec_from_file_location('tx02_drt_proof_gate',gate_path)
gate=importlib.util.module_from_spec(gate_spec);gate_spec.loader.exec_module(gate)
binding=gate.verify_binding()
assert json.loads(PORT.read_text())['inputs']=={p:pin(Path(p)) for p in json.loads(PORT.read_text())['inputs']}
OUT.mkdir()
def limit():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(int(2.5*1024**3),int(2.5*1024**3)))
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
libs=[x for x in (B/'repair.tcl').read_text().splitlines() if x.startswith('read_liberty ')]
lines=['set_thread_count 1','define_corners slow typical fast',*libs,f'read_db {{{B/"repaired.odb"}}}',f'read_sdc {{{B/"repaired.sdc"}}}', 'set_propagated_clock [all_clocks]','set_wire_rc -signal -layer Metal2','set_wire_rc -clock -layer Metal4','set_routing_layers -signal Metal2-Metal5 -clock Metal2-Metal5','set_global_routing_layer_adjustment Metal2-Metal5 0.30', 'set b [ord::get_db_block]', 'foreach name {zero_ one_} { set n [$b findNet $name]; if {$n != "NULL"} { if {[llength [$n getITerms]] || [llength [$n getBTerms]]} { error "Unexpected used supply constant alias $name" }; puts "PRUNE_VERIFIED_EMPTY_ALIAS $name"; odb::dbNet_destroy $n } }',f'detailed_route -output_drc {{{OUT/"router-drc.rpt"}}} -output_guide_coverage {{{OUT/"coverage.csv"}}} -verbose 1',f'write_db {{{OUT/"routed.odb"}}}',f'write_def {{{OUT/"routed.def"}}}',f'write_verilog {{{OUT/"routed.v"}}}',f'write_sdc {{{OUT/"routed.sdc"}}}','puts NATIVE_DETAILED_ROUTING_COMPLETE']
(OUT/'route.tcl').write_text('\n'.join(lines)+'\n')
files=[Path(__file__),PORT,gate_path,gate.E/'proof-execution-binding.json',*gate.input_paths(),APP,ROOT/'hw/soc/tools/openroad-26Q2-1164/root/usr/bin/openroad',Path('/dev/shm/nssoc-tx-path-v4-repair02-equivalence/equivalence.json'),Path('/dev/shm/nssoc-tx-path-v4-repair02-equivalence/mutation-controls.json'),OUT/'route.tcl',B/'repaired.odb',B/'repaired.v',B/'repaired.sdc']+[Path(x.split('{')[1].split('}')[0]) for x in libs]
r={'status':'RUNNING','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inputs':{str(p):pin(p) for p in files},'command':[str(APP),'-exit',str(OUT/'route.tcl')],'full_physical_acceptance':False,'qualified_rc':False,'scope':'TX candidate02: six measured driver-load isolations, nine buf1->buf4, one hold buffer following actualTX01 nominalRC. Fullnative3850state/11680function binaryproof+10kernel+10bindingcontrols+3physicalportsPASS. Fresh26Q2DRT;actualnominalRCstillrequired;GRTsetup+.684261 recovery+.149536 hold+.065914. InheritedGPIinterpreterpathwarningpreserved;nocleanlogclaim;noqualifiedRC/PDN/fullchip.','elapsed_watchdog_seconds':None,'address_space_limit_bytes':int(2.5*1024**3),'allowed_cpu_affinity':sorted(os.sched_getaffinity(0))}
def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
# Exact failure-only helper already exercised by the TX02 preflight.
tree=ast.parse((Path(__file__).resolve().parent/'postroute_repair02.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='stop_failed_group')
ns={'os':os,'signal':signal,'time':time};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(Path(__file__).resolve().parent/'postroute_repair02.py'),'exec'),ns)
save();t=time.monotonic();p=None;complete=False
try:
 with (OUT/'native.log').open('x') as log:
  try:
   old_mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM,signal.SIGINT})
   try:p=subprocess.Popen(r['command'],stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit,start_new_session=True)
   finally:signal.pthread_sigmask(signal.SIG_SETMASK,old_mask)
   r['pid']=p.pid;save()
   while p.poll() is None:
    if shutil.disk_usage('/dev/shm').free<528*1024**2:raise RuntimeError('Shared scratch floor')
    time.sleep(.25)
   r['returncode']=p.wait()
   if r['returncode']!=0:raise RuntimeError(f"Native DRT exit {r['returncode']}")
   complete=True
  finally:
   if p is not None and not complete:ns['stop_failed_group'](p)
 r['elapsed_seconds']=time.monotonic()-t
 assert r['inputs']=={str(p):pin(p) for p in files}
 assert gate.verify_binding()==binding
 assert 'NATIVE_DETAILED_ROUTING_COMPLETE' in (OUT/'native.log').read_text()
 assert (OUT/'router-drc.rpt').stat().st_size==0
 assert (OUT/'routed.v').read_bytes()==(B/'repaired.v').read_bytes()
 r['status']='COMPLETE_TX02_SIGNAL_DRT_ZERO_ROUTER_DRC_SAME_NETLIST__RC_REQUIRED'
except BaseException as e:r.update(status='FAILED_RETAINED',error=repr(e));raise
finally:
 r['outputs']={p.name:pin(p) for p in OUT.iterdir() if p.is_file() and p.name!='result.json'};save()
