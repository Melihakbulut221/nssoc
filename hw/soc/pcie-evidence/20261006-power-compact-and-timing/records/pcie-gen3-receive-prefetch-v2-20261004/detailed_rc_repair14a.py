# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact detailed wires and nominal unqualified OpenRCX model; no signoff claim."""
from pathlib import Path
import datetime,hashlib,json,resource,subprocess,time,os,signal,shutil,ast
def interrupted(signum,frame):raise InterruptedError(f'Signal{signum}')
for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,interrupted)
ROOT=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');B=Path('/dev/shm/nssoc-rx-prefetch-v2-repair14a-drt-01');OUT=Path('/dev/shm/nssoc-rx-prefetch-v2-repair14a-detailed-rc-01');assert shutil.disk_usage('/dev/shm').free>=1024**3;OUT.mkdir()
PDK=Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2')
APP=ROOT/'hw/soc/tools/openroad-26Q2-1164/run-openroad';RULES=PDK/'libs.tech/librelane/IHP_rcx_patterns.rules'
def pin(p):
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def limit():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(int(2.5*1024**3),int(2.5*1024**3)))
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
assert (B/'router-drc.rpt').stat().st_size==0
assert (B/'routed.v').read_bytes()==Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-14a/repaired.v').read_bytes()
old=json.loads((B/'result.json').read_text())
assert old['status']=='COMPLETE_RX14A_SIGNAL_DRT_ZERO_ROUTER_DRC_SAME_NETLIST__RC_REQUIRED' and old['returncode']==0
for name,h in old['outputs'].items(): assert pin(B/name)==h
assert old['inputs']=={p:pin(Path(p)) for p in old['inputs']}
libs=[x for x in (B/'route.tcl').read_text().splitlines() if x.startswith('read_liberty ')]
lines=['set_thread_count 1','define_corners slow typical fast',*libs,f'read_db {{{B/"routed.odb"}}}',f'read_sdc {{{B/"routed.sdc"}}}', 'set_propagated_clock [all_clocks]','define_process_corner -ext_model_index 0 typical',f'extract_parasitics -ext_model_file {{{RULES}}} -coupling_threshold 0 -cc_model 10 -context_depth 5 -no_merge_via_res',f'write_spef {{{OUT/"routed.spef"}}}']
for corner in ('slow','typical','fast'):lines += [f'read_spef -corner {corner} {{{OUT/"routed.spef"}}}']
lines += ['report_parasitic_annotation -report_unannotated','report_worst_slack -max','report_worst_slack -min','report_tns','report_check_types -max_slew -max_capacitance -violators']
for corner in ('slow','typical','fast'):
 for direction in ('max','min'):lines += [f'puts EXTRACTED_NOMINAL_RC_{corner}_{direction}',f'report_checks -corner {corner} -path_delay {direction} -group_path_count 3 -fields {{slew cap fanout}} -digits 6']
lines+=['puts NATIVE_NOMINAL_RC_SCREEN_COMPLETE']
(OUT/'extract.tcl').write_text('\n'.join(lines)+'\n')
files=[Path(__file__),Path(__file__).resolve().parent/'postroute_repair14a.py',APP,APP.parent/'root/usr/bin/openroad',RULES,OUT/'extract.tcl',B/'routed.odb',B/'routed.v',B/'routed.sdc',B/'native.log',B/'router-drc.rpt',B/'result.json']+[Path(x.split('{')[1].split('}')[0]) for x in libs]
r={'status':'RUNNING','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inputs':{str(p):pin(p) for p in files},'command':[str(APP),'-exit',str(OUT/'extract.tcl')],'full_physical_acceptance':False,'qualified_rc':False,'scope':'Detailed signal wires, nominal PDK RC reused across three cell corners, no RC process corners/PDN or signoff','source_netlist_byte_identical_to_previously_port_replayed_and_binary_proved':True,'elapsed_watchdog_seconds':None,'address_space_limit_bytes':int(2.5*1024**3)}
def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
tree=ast.parse((Path(__file__).resolve().parent/'postroute_repair14a.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='stop_failed_group')
ns={'os':os,'signal':signal,'time':time};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(Path(__file__).resolve().parent/'postroute_repair14a.py'),'exec'),ns)
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
    time.sleep(.2)
   r['returncode']=p.wait()
   if r['returncode']!=0:raise RuntimeError(f"Native RC exit {r['returncode']}")
   complete=True
  finally:
   if p is not None and not complete:ns['stop_failed_group'](p)
 r['elapsed_seconds']=time.monotonic()-t
 assert r['inputs']=={str(p):pin(p) for p in files}
 assert 'NATIVE_NOMINAL_RC_SCREEN_COMPLETE' in (OUT/'native.log').read_text()
 r['status']='COMPLETE_UNQUALIFIED_NOMINAL_RC_REVIEW_REQUIRED'
except BaseException as e:r.update(status='FAILED_RETAINED',error=repr(e));raise
finally:
 r['outputs']={p.name:pin(p) for p in OUT.iterdir() if p.is_file() and p.name!='result.json'};save()
