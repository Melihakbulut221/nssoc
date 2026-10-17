# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""TX candidate02 isolates six measured slow drivers, upsizes nine measured buffers and delays one measured hold endpoint; baseline01 immutable."""
from pathlib import Path
import hashlib,json,resource,os,signal,subprocess,time,shutil
R=Path.cwd();B=Path('/dev/shm/nssoc-tx-path-v4-repair01-drt-01');RC=Path('/dev/shm/nssoc-tx-path-v4-repair01-detailed-rc-01');O=Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-02');
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
EXACT_BASELINE_PINS = {'/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/postroute_repair11.py': {'bytes': 10349, 'sha256': '023363f510e35b116b0c2ad1581bb50ae5a42ada2a6afcfbc2cc509b33ce7302'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/postroute_repair01.py': {'bytes': 6055, 'sha256': 'ecfcd81bbad08f34ce14c7dcff4cfef4d5eaa61a62c2ee8de5f5bce1de22b194'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair02-source/target-census.json': {'bytes': 4574, 'sha256': '21ebc025080e5f80a967d0e8b8af01d984cae51781739225652530c4c361fa76'}, '/dev/shm/nssoc-tx-path-v4-repair01-drt-01/routed.odb': {'bytes': 53123981, 'sha256': '46057f29e462ded4dc4e992a661187a06f081699cda9863a0678d9ec9a42259f'}, '/dev/shm/nssoc-tx-path-v4-repair01-drt-01/routed.v': {'bytes': 4173293, 'sha256': 'f132e259fa4143ba7d47ef4bd411803af95bb378044a64d69c9726a4f42bcbc3'}, '/dev/shm/nssoc-tx-path-v4-repair01-drt-01/routed.sdc': {'bytes': 124170, 'sha256': 'b7cd1bb0e20031a8ac6e08c12a164da23e4c2aa8f50166d79c1101bdc2e6e408'}, '/dev/shm/nssoc-tx-path-v4-repair01-drt-01/result.json': {'bytes': 4686, 'sha256': '5795bd33d90c1e2962c40696918c826d9ebcb743e675d4d8964ed39cb0c0d2c1'}, '/dev/shm/nssoc-tx-path-v4-repair01-detailed-rc-01/routed.spef': {'bytes': 58412255, 'sha256': '85b60dbba5cac9c982b2b61097257edd0e3979eebce2ae98e40c8311138c59e3'}, '/dev/shm/nssoc-tx-path-v4-repair01-detailed-rc-01/result.json': {'bytes': 4178, 'sha256': '568f25f7e927afe9282148c6fcdd752fccda50ca782a2c8ba07a5cb221588280'}, '/dev/shm/nssoc-tx-path-v4-repair01-detailed-rc-01/native.log': {'bytes': 96306, 'sha256': 'c211f556403e5012c10dbda210a0bfcdf00382e8cdb3dcfeb2ea97ab81a3b941'}}
assert EXACT_BASELINE_PINS == {p:pin(Path(p)) for p in EXACT_BASELINE_PINS}
libs=[x for x in (B/'route.tcl').read_text().splitlines() if x.startswith('read_liberty ')]
lines=['set_thread_count 1','define_corners slow typical fast',*libs,f'read_db {{{B/"routed.odb"}}}',f'read_sdc {{{B/"routed.sdc"}}}','set_propagated_clock [all_clocks]','set_wire_rc -signal -layer Metal2','set_wire_rc -clock -layer Metal4','set_routing_layers -signal Metal2-Metal5 -clock Metal2-Metal5','set_global_routing_layer_adjustment Metal2-Metal5 0.30']
lines += [f'read_spef -corner {c} {{{RC/"routed.spef"}}}' for c in ('slow','typical','fast')]
lines += ['puts UNCHANGED_SOURCE_ACTUAL_RC_WORST','report_worst_slack -max','report_worst_slack -min']
lines += [f'write_verilog {{{O/"before_clear.v"}}}', 'set cleared_wire_count 0', 'foreach net [[ord::get_db_block] getNets] {', '  if {[$net getSigType] in {POWER GROUND}} {continue}', '  set wire [$net getWire]', '  if {$wire != "NULL"} {odb::dbWire_destroy $wire; incr cleared_wire_count}', '  $net clearGuides', '}', 'puts "REMOVED_CANDIDATE_SIGNAL_WIRES $cleared_wire_count"', f'write_verilog {{{O/"after_clear.v"}}}']
lines += [f'set before_file [open {{{O/"before_clear.v"}}} r]', 'set before_netlist [read $before_file]', 'close $before_file', f'set after_file [open {{{O/"after_clear.v"}}} r]', 'set after_netlist [read $after_file]', 'close $after_file', 'if {$before_netlist ne $after_netlist} {error "Signal-wire removal changed logical netlist"}', 'puts EXACT_LOGICAL_NETLIST_UNCHANGED_AFTER_CLEAR']
lines += [f'global_route -congestion_iterations 100 -guide_file {{{O/"initial.guide"}}}']
lines += ['estimate_parasitics -global_routing', 'puts INITIAL_GLOBAL_ROUTE_PARASITIC_CONTEXT_READY']
# Baseline is immutable TX routed01; after geometry clear use new global-route estimates, never reuse old actual SPEF on changed cells/nets.
lines += ['detailed_placement', 'check_placement -verbose', 'global_route -start_incremental']
def report(tag):
 z=[f'puts {tag}','report_worst_slack -max','report_worst_slack -min','report_tns','report_check_types -max_slew -max_capacitance -violators']
 for c in ('slow','typical','fast'):
  for d in ('max','min'):z.extend([f'puts {tag}_{c}_{d}',f'report_checks -corner {c} -path_delay {d} -group_path_count 1 -fields {{slew cap fanout}} -digits 6'])
 return z
lines += report('TX01_GRT_BEFORE_EXPLICIT_LOAD_ISOLATION')
targets = [('_29730_', 'sg13g2_o21ai_1', 'Y', ['_29731_/A1', 'place11418/A']), ('_29996_', 'sg13g2_o21ai_1', 'Y', ['_29997_/A1', 'place11151/A']), ('_33951_', 'sg13g2_xor2_1', 'X', ['_43097_/B', '_51162_/A', 'place14970/A', 'place14971/A']), ('_33955_', 'sg13g2_xnor2_1', 'Y', ['_34027_/B', '_43476_/B', '_50651_/A', 'place13121/A']), ('_50651_', 'sg13g2_xor2_1', 'X', ['_50654_/A1', '_50655_/A1', '_51063_/A', 'rebuffer18175/A']), ('_51063_', 'sg13g2_xnor2_1', 'Y', ['_51064_/A2'])]
lines += ['set eco_block [ord::get_db_block]', 'set eco_scale [$eco_block getDbUnitsPerMicron]']
for number,(name,master,port,expected_loads) in enumerate(targets):
 lines += [f'set driver [$eco_block findInst {name}]', f'if {{$driver == "NULL" || [[$driver getMaster] getName] != "{master}"}} {{error "Unexpected measured driver {name}"}}', f'set driver_pin [$driver findITerm {port}]', 'set net [$driver_pin getNet]', 'set loads {}', 'foreach term [$net getITerms] {if {[$term getIoType] == "INPUT"} {lappend loads "[[$term getInst] getName]/[[$term getMTerm] getName]"}}', f'if {{[lsort $loads] ne [lsort {{{" ".join(expected_loads)}}}] || [llength [$net getBTerms]] != 0}} {{error "Measured load census changed {name}"}}', 'set xy [$driver getLocation]', 'set x [expr {double([lindex $xy 0])/$eco_scale}]', 'set y [expr {double([lindex $xy 1])/$eco_scale}]', f'puts "MEASURED_CRITICAL_BUFFER {name}/{port} [$net getName] $loads at $x $y"', f'insert_buffer -buffer_cell sg13g2_buf_4 -load_pins [get_pins $loads] -location [list $x $y] -buffer_name eco02_wire_{number} -net_name eco02_sink_{number}']
for measured_buffer in ('place14971','fanout10982','fanout10930','fanout10927','fanout10925','fanout10731','fanout10681','fanout10668','fanout10667'):
 lines += [f'set driver [$eco_block findInst {measured_buffer}]', 'if {$driver == "NULL" || [[$driver getMaster] getName] != "sg13g2_buf_1"} {error "Unexpected measured buffer"}', f'replace_cell {measured_buffer} sg13g2_buf_4']
lines += ['set load [$eco_block findInst _55164_]', 'if {$load == "NULL" || [[$load getMaster] getName] != "sg13g2_dfrbpq_1" || [[[$load findITerm D] getNet] getName] != "_00520_"} {error "Measured hold endpoint changed"}', 'set xy [$load getLocation]', 'set x [expr {double([lindex $xy 0])/$eco_scale}]', 'set y [expr {double([lindex $xy 1])/$eco_scale}]', 'insert_buffer -buffer_cell sg13g2_buf_1 -load_pins [get_pins _55164_/D] -location [list $x $y] -buffer_name eco02_hold_0 -net_name eco02_hold_sink_0']
lines += ['detailed_placement', 'check_placement -verbose']
# Do not report stale parasitics after inserting nets; reroute and reestimate first.
# Initialize and finish the global-router incremental context before changing its database.
lines += [f'global_route -end_incremental -congestion_iterations 100 -guide_file {{{O/"repaired.guide"}}}', 'estimate_parasitics -global_routing']
lines += report('CANDIDATE_GLOBAL_ROUTE_ESTIMATES_ONLY')
lines += [f'write_db {{{O/"repaired.odb"}}}',f'write_verilog {{{O/"repaired.v"}}}',f'write_sdc {{{O/"repaired.sdc"}}}','puts NATIVE_POSTROUTE_REPAIR_CANDIDATE_COMPLETE']
(O/'repair.tcl').write_text('\n'.join(lines)+'\n')
files=[Path(p) for p in EXACT_BASELINE_PINS]+[Path(__file__),A,R/'hw/soc/tools/openroad-26Q2-1164/root/usr/bin/openroad',R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/newtool-readonly-comparison.json',B/'routed.odb',B/'routed.sdc',B/'routed.v',B/'result.json',RC/'routed.spef',RC/'result.json',RC/'native.log',O/'repair.tcl']+[Path(x.split('{')[1].split('}')[0]) for x in libs]
r={'status':'RUNNING','inputs':{str(p):pin(p) for p in files},'route_reset':'Only copied signal-wire geometry and guides are cleared; original routed DB/SPEF immutable; exact before/after exported netlist asserted. BaselineTX01 actualRC is reported before changes; then freshGRT estimates. Six exact measured driver-load sets gain buf4 at driver location; nine measured buf1 become buf4; measured _55164_/D gains buf1 at load location. No actualRC claimed for changed circuit.', 'scope':'Separate TX candidate02 starts from actual01 detailed geometry and unchanged4nsIOconstraints; six driver buffers/nine upsizes/one hold buffer only. Candidate changes physical cells; sourceDRT remainsimmutable. New global-route estimates are NOT finaltiming; freshDRT/nominalRC/equivalence/physicalportreplay required.','elapsed_watchdog_seconds':None,'address_space_limit_bytes':int(2.5*1024**3),'single_cpu':True,'qualified_rc':False,'physical_acceptance':False,'minimum_shared_free':shutil.disk_usage('/dev/shm').free}
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
