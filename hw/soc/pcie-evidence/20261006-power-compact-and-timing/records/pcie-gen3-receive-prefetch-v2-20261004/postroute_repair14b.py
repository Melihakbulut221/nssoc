# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Candidate14b isolates eleven measured RX13 critical single loads using drive4; original13 immutable; fresh GRT comparison only."""
from pathlib import Path
import hashlib,json,resource,os,signal,subprocess,time,shutil
R=Path.cwd();B=Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-drt-01');RC=Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-detailed-rc-01');O=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-14b');
while shutil.disk_usage('/dev/shm').free<1024**3:time.sleep(5)
O.mkdir()
A=R/'hw/soc/tools/openroad-26Q2-1164/run-openroad'
def pin(p):
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def sig(n,f):raise InterruptedError(f'Signal{n}')
for s in (signal.SIGINT,signal.SIGTERM):signal.signal(s,sig)
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(int(2.5*1024**3),)*2)
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGINT,signal.SIGTERM})
EXACT_BASELINE_PINS = {'/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/postroute_repair13.py': {'bytes': 12102, 'sha256': '49d5abded5c93f0c30f95c1f724942e039a4777863a8fce5659815be454bbea2'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair13-peer/review.json': {'bytes': 37002, 'sha256': '8ea58558d70a9de902165c5d6d3470f462b137d35287d635d2376f55ebbcea30'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair13-peer/release.json': {'bytes': 3530, 'sha256': 'f17b1c0c5be7260a7be4eed09badc6f727fca83dd34e355f158e972317d669e7'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair13-peer/publication-review.json': {'bytes': 4518, 'sha256': '0d2879e719c524d371cfc316e69a4fbf6eda5209d39cb0def9eeaafef9b32081'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair14-source/selected-targets.json': {'bytes': 11850, 'sha256': '1d6d02521f8d3773510b02060283b5faae37a95c3e64dde672caae56ec54ef8e'}, '/dev/shm/nssoc-rx-prefetch-v2-repair13-drt-01/routed.odb': {'bytes': 28072177, 'sha256': '916d85fce520e5e1582b60dda20f3379f9305fed1d4caccd84912c93dba75c13'}, '/dev/shm/nssoc-rx-prefetch-v2-repair13-drt-01/routed.v': {'bytes': 2093617, 'sha256': '533ecba38bc02e0f08cf96e9aef1e71682141de26dd772bc965abe9619c6ab34'}, '/dev/shm/nssoc-rx-prefetch-v2-repair13-drt-01/routed.sdc': {'bytes': 89666, 'sha256': '1a897a5cd2a15590102e216904e62e86b9e22fbf96ea182628706b092520179c'}, '/dev/shm/nssoc-rx-prefetch-v2-repair13-detailed-rc-01/routed.spef': {'bytes': 29103110, 'sha256': 'a134582935e403354915162410a0ce560210264ba7290abe1767c8246df081dc'}, '/dev/shm/nssoc-rx-prefetch-v2-repair13-detailed-rc-01/result.json': {'bytes': 4443, 'sha256': '19d926ff53c96145b2af9ca10ba52fb493afa65063d20bf37c4a58d73c0a1b34'}}
assert EXACT_BASELINE_PINS == {p:pin(Path(p)) for p in EXACT_BASELINE_PINS}
libs=[x for x in (B/'route.tcl').read_text().splitlines() if x.startswith('read_liberty ')]
lines=['set_thread_count 1','define_corners slow typical fast',*libs,f'read_db {{{B/"routed.odb"}}}',f'read_sdc {{{B/"routed.sdc"}}}','set_propagated_clock [all_clocks]','set_wire_rc -signal -layer Metal2','set_wire_rc -clock -layer Metal4','set_routing_layers -signal Metal2-Metal5 -clock Metal2-Metal5','set_global_routing_layer_adjustment Metal2-Metal5 0.30']
lines += [f'read_spef -corner {c} {{{RC/"routed.spef"}}}' for c in ('slow','typical','fast')]
lines += ['puts UNCHANGED_SOURCE_ACTUAL_RC_WORST','report_worst_slack -max','report_worst_slack -min']
lines += [f'write_verilog {{{O/"before_clear.v"}}}', 'set cleared_wire_count 0', 'foreach net [[ord::get_db_block] getNets] {', '  if {[$net getSigType] in {POWER GROUND}} {continue}', '  set wire [$net getWire]', '  if {$wire != "NULL"} {odb::dbWire_destroy $wire; incr cleared_wire_count}', '  $net clearGuides', '}', 'puts "REMOVED_CANDIDATE_SIGNAL_WIRES $cleared_wire_count"', f'write_verilog {{{O/"after_clear.v"}}}']
lines += [f'set before_file [open {{{O/"before_clear.v"}}} r]', 'set before_netlist [read $before_file]', 'close $before_file', f'set after_file [open {{{O/"after_clear.v"}}} r]', 'set after_netlist [read $after_file]', 'close $after_file', 'if {$before_netlist ne $after_netlist} {error "Signal-wire removal changed logical netlist"}', 'puts EXACT_LOGICAL_NETLIST_UNCHANGED_AFTER_CLEAR']
lines += [f'global_route -congestion_iterations 100 -guide_file {{{O/"initial.guide"}}}']
lines += ['estimate_parasitics -global_routing', 'puts INITIAL_GLOBAL_ROUTE_PARASITIC_CONTEXT_READY']
# Baseline is immutable routed13; after geometry clear use new global-route estimates, never reuse old actual SPEF on changed cells/nets.
lines += ['detailed_placement', 'check_placement -verbose', 'global_route -start_incremental']
def report(tag):
 z=[f'puts {tag}','report_worst_slack -max','report_worst_slack -min','report_tns','report_check_types -max_slew -max_capacitance -violators']
 for c in ('slow','typical','fast'):
  for d in ('max','min'):z.extend([f'puts {tag}_{c}_{d}',f'report_checks -corner {c} -path_delay {d} -group_path_count 1 -fields {{slew cap fanout}} -digits 6'])
 return z
lines += report('CANDIDATE13_GRT_BEFORE_EXPLICIT_LOAD_ISOLATION')
targets = [{'name': '_20132_', 'master': 'sg13g2_a22oi_1', 'output_pin': 'Y', 'net': '_03194_', 'loads': ['_20136_/B'], 'buffer': 'sg13g2_buf_4'}, {'name': '_20136_', 'master': 'sg13g2_nand4_1', 'output_pin': 'Y', 'net': '_03198_', 'loads': ['_20147_/B'], 'buffer': 'sg13g2_buf_4'}, {'name': '_20147_', 'master': 'sg13g2_nor4_2', 'output_pin': 'Y', 'net': '_03209_', 'loads': ['_20180_/A'], 'buffer': 'sg13g2_buf_4'}, {'name': '_20180_', 'master': 'sg13g2_nand4_1', 'output_pin': 'Y', 'net': '_03242_', 'loads': ['_20181_/A'], 'buffer': 'sg13g2_buf_4'}, {'name': '_20517_', 'master': 'sg13g2_a22oi_1', 'output_pin': 'Y', 'net': '_03575_', 'loads': ['_20519_/A'], 'buffer': 'sg13g2_buf_4'}, {'name': '_20519_', 'master': 'sg13g2_nand4_1', 'output_pin': 'Y', 'net': '_03577_', 'loads': ['_20530_/A'], 'buffer': 'sg13g2_buf_4'}, {'name': '_20531_', 'master': 'sg13g2_nand4_1', 'output_pin': 'Y', 'net': '_03589_', 'loads': ['_20605_/B'], 'buffer': 'sg13g2_buf_4'}, {'name': '_20364_', 'master': 'sg13g2_a22oi_1', 'output_pin': 'Y', 'net': '_03424_', 'loads': ['_20365_/D'], 'buffer': 'sg13g2_buf_4'}, {'name': '_20365_', 'master': 'sg13g2_nand4_1', 'output_pin': 'Y', 'net': '_03425_', 'loads': ['_20371_/B'], 'buffer': 'sg13g2_buf_4'}, {'name': '_20371_', 'master': 'sg13g2_nor2_2', 'output_pin': 'Y', 'net': '_03431_', 'loads': ['_20393_/C'], 'buffer': 'sg13g2_buf_4'}, {'name': '_20393_', 'master': 'sg13g2_nand4_1', 'output_pin': 'Y', 'net': '_03453_', 'loads': ['_20394_/A'], 'buffer': 'sg13g2_buf_4'}]
lines += ['set eco_block [ord::get_db_block]', 'set eco_scale [$eco_block getDbUnitsPerMicron]']
for number,target in enumerate(targets):
 name,master,output_pin,netname,expected,buffer = (target[k] for k in ('name','master','output_pin','net','loads','buffer'))
 expected_tcl=' '.join(expected)
 lines += [f'set driver [$eco_block findInst {name}]', f'if {{$driver == "NULL" || [[$driver getMaster] getName] != "{master}"}} {{error "Unexpected measured driver {name}"}}', f'set driver_pin [$driver findITerm {output_pin}]', 'set net [$driver_pin getNet]', f'if {{[$net getName] != "{netname}"}} {{error "Measured net changed {name}"}}', 'set loads {}', 'foreach term [$net getITerms] {if {[$term getIoType] == "INPUT"} {lappend loads "[[$term getInst] getName]/[[$term getMTerm] getName]"}}', f'if {{[lsort $loads] ne [lsort {{{expected_tcl}}}]}} {{error "Exact measured load set changed {name}"}}', 'set xy [$driver getLocation]', 'set x [expr {double([lindex $xy 0])/$eco_scale}]', 'set y [expr {double([lindex $xy 1])/$eco_scale}]', f'puts "MEASURED_CRITICAL_BUFFER {name}/{output_pin} [$net getName] $loads at $x $y"', f'insert_buffer -buffer_cell {buffer} -load_pins [get_pins $loads] -location [list $x $y] -buffer_name eco14b_wire_{number} -net_name eco14b_sink_{number}']
upsizes = []
for name,old_master,new_master in upsizes:
 lines += [f'set driver [$eco_block findInst {name}]', f'if {{$driver == "NULL" || [[$driver getMaster] getName] != "{old_master}"}} {{error "Unexpected measured upsize source {name}"}}', f'replace_cell {name} {new_master}']
lines += ['detailed_placement', 'check_placement -verbose']
# Do not report stale parasitics after inserting nets; reroute and reestimate first.
# Initialize and finish the global-router incremental context before changing its database.
lines += [f'global_route -end_incremental -congestion_iterations 100 -guide_file {{{O/"repaired.guide"}}}', 'estimate_parasitics -global_routing']
lines += report('CANDIDATE_GLOBAL_ROUTE_ESTIMATES_ONLY')
lines += [f'write_db {{{O/"repaired.odb"}}}',f'write_verilog {{{O/"repaired.v"}}}',f'write_sdc {{{O/"repaired.sdc"}}}','puts NATIVE_POSTROUTE_REPAIR_CANDIDATE_COMPLETE']
(O/'repair.tcl').write_text('\n'.join(lines)+'\n')
files=[Path(p) for p in EXACT_BASELINE_PINS]+[Path(__file__),A,R/'hw/soc/tools/openroad-26Q2-1164/root/usr/bin/openroad',R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/newtool-readonly-comparison.json',B/'routed.odb',B/'routed.sdc',B/'routed.v',B/'result.json',RC/'routed.spef',RC/'result.json',RC/'native.log',O/'repair.tcl']+[Path(x.split('{')[1].split('}')[0]) for x in libs]
r={'status':'RUNNING','inputs':{str(p):pin(p) for p in files},'route_reset':'Only copied signal-wire geometry and guides are cleared; original routed DB/SPEF immutable; exact before/after exported netlist asserted. Baseline13 actualRC is reported before changes; then freshGRT estimates. Eleven measured single-load drivers gain drive4 buffer isolation at actual driver location; no cell function or clock/hold/constraint change. No actualRC claimed for changed circuit.', 'scope':'Separate candidate14b starts directly from actual13 detailed geometry and unchanged4nsIOconstraints; eleven drive4 local critical-wire buffers and no direct upsizes. Compare with independent drive2 alternative before selecting any new DRT. Candidate changes physical cells; sourceDRT remainsimmutable. New global-route estimates are NOT finaltiming; freshDRT/nominalRC/equivalence/physicalportreplay required.','elapsed_watchdog_seconds':None,'address_space_limit_bytes':int(2.5*1024**3),'single_cpu':True,'qualified_rc':False,'physical_acceptance':False,'minimum_shared_free':shutil.disk_usage('/dev/shm').free}
def save():(O/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def stop_failed_group(process, grace_seconds=5.0):
 # Error/interruption only; healthy child has no elapsed watchdog.
 try:
  try:os.killpg(process.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  deadline=time.monotonic()+grace_seconds
  while time.monotonic()<deadline:time.sleep(min(.05,max(0,deadline-time.monotonic())))
 finally:
  try:os.killpg(process.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  finally:process.wait()

save();t=time.monotonic();p=None;native_complete=False
try:
 assert shutil.disk_usage('/dev/shm').free>=1024**3
 with (O/'native.log').open('x') as log:
  try:
   previous_mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
   try:
    p=subprocess.Popen([str(A),'-exit',str(O/'repair.tcl')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limits)
   finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous_mask)
   r['pid']=p.pid;save()
   while p.poll() is None:
    free=shutil.disk_usage('/dev/shm').free;r['minimum_shared_free']=min(r['minimum_shared_free'],free)
    if free<528*1024**2:raise RuntimeError('Shared scratch floor')
    time.sleep(.25)
   r['returncode']=p.wait()
   if r['returncode']!=0:raise RuntimeError(f"Native exit {r['returncode']}")
   native_complete=True
  finally:
   if p is not None and not native_complete:stop_failed_group(p)
 assert r['inputs']=={str(p):pin(p) for p in files}
 r['status']='COMPLETE_CANDIDATE_REQUIRES_EQUIVALENCE_ROUTE_RC'
except BaseException as e:r.update(status='FAILED_RETAINED',error=repr(e));raise
finally:r['elapsed_seconds']=time.monotonic()-t;r['outputs']={p.name:pin(p) for p in O.iterdir() if p.is_file() and p.name!='result.json'};save()
