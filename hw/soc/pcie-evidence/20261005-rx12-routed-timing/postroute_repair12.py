# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Candidate12 isolates eight measured critical loads and upsizes two weak buffers; original11 immutable; fresh GRT after changes."""
from pathlib import Path
import hashlib,json,resource,os,signal,subprocess,time,shutil
R=Path.cwd();B=Path('/dev/shm/nssoc-rx-prefetch-v2-repair11-drt-02');RC=Path('/dev/shm/nssoc-rx-prefetch-v2-repair11-detailed-rc-02');O=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-12');
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
EXACT_BASELINE_PINS = {'/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/postroute_repair11.py': {'bytes': 10349, 'sha256': '023363f510e35b116b0c2ad1581bb50ae5a42ada2a6afcfbc2cc509b33ce7302'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair11-peer02/review.json': {'bytes': 35708, 'sha256': '034c7c86c0e6a11a3c081b9a034976270f7ab182034b12ce4708055f22eb5288'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair11-peer02/release.json': {'bytes': 2592, 'sha256': 'd1322be9bec52081fd61c4d5f4c0c1f0250e90d1805921f596ff47481c899809'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair12-source/target-census.json': {'bytes': 16192, 'sha256': '045446ce75d87d1d06116778cbb8b9c0fbaa318090510557e2ec0f9c9f780658'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair12-source/selected-targets.json': {'bytes': 11917, 'sha256': '4b694cbf18f99349900665e96883ae4193293770754f6d17c7c229c018954ecf'}, '/dev/shm/nssoc-rx-prefetch-v2-repair11-drt-02/routed.odb': {'bytes': 28002614, 'sha256': 'ea33bcf5ba7471d7152e65ea7c482c33938e536645a74fb48171a76725d0de01'}, '/dev/shm/nssoc-rx-prefetch-v2-repair11-drt-02/routed.v': {'bytes': 2091901, 'sha256': '5043dd664e699c56120673f5dde8e990f804cffa40c9b604034cc57026a1e3fc'}, '/dev/shm/nssoc-rx-prefetch-v2-repair11-drt-02/routed.sdc': {'bytes': 89666, 'sha256': 'e5795537706fbddfb10f5d8aa9bbbc8d3524f7abb3ae19d94960d5fe05d90463'}, '/dev/shm/nssoc-rx-prefetch-v2-repair11-detailed-rc-02/routed.spef': {'bytes': 29141126, 'sha256': 'bfb0504484d1802cd868b22145dfe0bacb8c15f58f25eb1a9eaf3c1ead78ad51'}, '/dev/shm/nssoc-rx-prefetch-v2-repair11-detailed-rc-02/result.json': {'bytes': 4452, 'sha256': 'ce729785bf71ebbef253e404fb807fd894c5f97fb2e01eda6ce821da60e93876'}}
assert EXACT_BASELINE_PINS == {p:pin(Path(p)) for p in EXACT_BASELINE_PINS}
libs=[x for x in (B/'route.tcl').read_text().splitlines() if x.startswith('read_liberty ')]
lines=['set_thread_count 1','define_corners slow typical fast',*libs,f'read_db {{{B/"routed.odb"}}}',f'read_sdc {{{B/"routed.sdc"}}}','set_propagated_clock [all_clocks]','set_wire_rc -signal -layer Metal2','set_wire_rc -clock -layer Metal4','set_routing_layers -signal Metal2-Metal5 -clock Metal2-Metal5','set_global_routing_layer_adjustment Metal2-Metal5 0.30']
lines += [f'read_spef -corner {c} {{{RC/"routed.spef"}}}' for c in ('slow','typical','fast')]
lines += ['puts UNCHANGED_SOURCE_ACTUAL_RC_WORST','report_worst_slack -max','report_worst_slack -min']
lines += [f'write_verilog {{{O/"before_clear.v"}}}', 'set cleared_wire_count 0', 'foreach net [[ord::get_db_block] getNets] {', '  if {[$net getSigType] in {POWER GROUND}} {continue}', '  set wire [$net getWire]', '  if {$wire != "NULL"} {odb::dbWire_destroy $wire; incr cleared_wire_count}', '  $net clearGuides', '}', 'puts "REMOVED_CANDIDATE_SIGNAL_WIRES $cleared_wire_count"', f'write_verilog {{{O/"after_clear.v"}}}']
lines += [f'set before_file [open {{{O/"before_clear.v"}}} r]', 'set before_netlist [read $before_file]', 'close $before_file', f'set after_file [open {{{O/"after_clear.v"}}} r]', 'set after_netlist [read $after_file]', 'close $after_file', 'if {$before_netlist ne $after_netlist} {error "Signal-wire removal changed logical netlist"}', 'puts EXACT_LOGICAL_NETLIST_UNCHANGED_AFTER_CLEAR']
lines += [f'global_route -congestion_iterations 100 -guide_file {{{O/"initial.guide"}}}']
lines += ['estimate_parasitics -global_routing', 'puts INITIAL_GLOBAL_ROUTE_PARASITIC_CONTEXT_READY']
# Baseline is immutable routed11; after geometry clear use new global-route estimates, never reuse old actual SPEF on changed cells/nets.
lines += ['detailed_placement', 'check_placement -verbose', 'global_route -start_incremental']
def report(tag):
 z=[f'puts {tag}','report_worst_slack -max','report_worst_slack -min','report_tns','report_check_types -max_slew -max_capacitance -violators']
 for c in ('slow','typical','fast'):
  for d in ('max','min'):z.extend([f'puts {tag}_{c}_{d}',f'report_checks -corner {c} -path_delay {d} -group_path_count 1 -fields {{slew cap fanout}} -digits 6'])
 return z
lines += report('CANDIDATE11_GRT_BEFORE_EXPLICIT_LOAD_ISOLATION')
targets = [('_20220_', 'sg13g2_a22oi_1'), ('_20223_', 'sg13g2_nand4_1'), ('_20286_', 'sg13g2_nand4_1'), ('_19846_', 'sg13g2_nand4_1'), ('_19968_', 'sg13g2_nand4_1'), ('_19989_', 'sg13g2_a22oi_1'), ('_19990_', 'sg13g2_nand4_1'), ('_20002_', 'sg13g2_nand4_1')]
lines += ['set eco_block [ord::get_db_block]', 'set eco_scale [$eco_block getDbUnitsPerMicron]']
for number,(name,master) in enumerate(targets):
 lines += [f'set driver [$eco_block findInst {name}]', f'if {{$driver == "NULL" || [[$driver getMaster] getName] != "{master}"}} {{error "Unexpected measured driver {name}"}}', 'set driver_pin [$driver findITerm Y]', 'set net [$driver_pin getNet]', 'set loads {}', 'foreach term [$net getITerms] {if {[$term getIoType] == "INPUT"} {lappend loads "[[$term getInst] getName]/[[$term getMTerm] getName]"}}', f'if {{[llength $loads] != 1}} {{error "Expected measured single load {name}"}}', 'set xy [$driver getLocation]', 'set x [expr {double([lindex $xy 0])/$eco_scale}]', 'set y [expr {double([lindex $xy 1])/$eco_scale}]', f'puts "MEASURED_CRITICAL_BUFFER {name}/Y [$net getName] $loads at $x $y"', f'insert_buffer -buffer_cell sg13g2_buf_4 -load_pins [get_pins $loads] -location [list $x $y] -buffer_name eco12_wire_{number} -net_name eco12_sink_{number}']
for measured_buffer in ('rebuffer11628', 'place9444'):
 lines += [f'set driver [$eco_block findInst {measured_buffer}]', 'if {$driver == "NULL" || [[$driver getMaster] getName] != "sg13g2_buf_1"} {error "Unexpected measured buffer"}', f'replace_cell {measured_buffer} sg13g2_buf_4']
lines += ['detailed_placement', 'check_placement -verbose']
# Do not report stale parasitics after inserting nets; reroute and reestimate first.
# Initialize and finish the global-router incremental context before changing its database.
lines += [f'global_route -end_incremental -congestion_iterations 100 -guide_file {{{O/"repaired.guide"}}}', 'estimate_parasitics -global_routing']
lines += report('CANDIDATE_GLOBAL_ROUTE_ESTIMATES_ONLY')
lines += [f'write_db {{{O/"repaired.odb"}}}',f'write_verilog {{{O/"repaired.v"}}}',f'write_sdc {{{O/"repaired.sdc"}}}','puts NATIVE_POSTROUTE_REPAIR_CANDIDATE_COMPLETE']
(O/'repair.tcl').write_text('\n'.join(lines)+'\n')
files=[Path(p) for p in EXACT_BASELINE_PINS]+[Path(__file__),A,R/'hw/soc/tools/openroad-26Q2-1164/root/usr/bin/openroad',R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/newtool-readonly-comparison.json',B/'routed.odb',B/'routed.sdc',B/'routed.v',B/'result.json',RC/'routed.spef',RC/'result.json',RC/'native.log',O/'repair.tcl']+[Path(x.split('{')[1].split('}')[0]) for x in libs]
r={'status':'RUNNING','inputs':{str(p):pin(p) for p in files},'route_reset':'Only copied signal-wire geometry and guides are cleared; original routed DB/SPEF immutable; exact before/after exported netlist asserted. Baseline11 actualRC is reported before changes; then freshGRT estimates. Eight single-load weak drivers gain buf4 at actual driver location and two measured buf1 become buf4. No actualRC claimed for changed circuit.', 'scope':'Separate candidate12 starts from actual11 detailed geometry and unchanged4nsIOconstraints; eight local critical-wire buffers/two upsizes only. Candidate changes physical cells; sourceDRT remainsimmutable. New global-route estimates are NOT finaltiming; freshDRT/nominalRC/equivalence/physicalportreplay required.','elapsed_watchdog_seconds':None,'address_space_limit_bytes':int(2.5*1024**3),'single_cpu':True,'qualified_rc':False,'physical_acceptance':False,'minimum_shared_free':shutil.disk_usage('/dev/shm').free}
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
