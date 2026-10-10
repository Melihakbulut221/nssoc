# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""TX candidate03 isolates seven measured complex/XOR drivers and upsizes three buffers; completed TX02 hold/recovery repairs remain in immutable baseline."""
from pathlib import Path
import hashlib,json,resource,os,signal,subprocess,time,shutil
R=Path.cwd();B=Path('/dev/shm/nssoc-tx-path-v4-repair02-drt-03');RC=Path('/dev/shm/nssoc-tx-path-v4-repair02-detailed-rc-02');O=Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-03');
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
EXACT_BASELINE_PINS = {'/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/postroute_repair02.py': {'bytes': 11580, 'sha256': '4ab98f2e372e6913626988e5d84c402efbffc704b244ac47aa43ae8a003ed698'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair02-peer/review.json': {'bytes': 45876, 'sha256': 'ab349eee3c51ee50f2383d2416f4fd0160db1f20d2eb7d6e5760dd9528478ccf'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair02-peer/release02.json': {'bytes': 3430, 'sha256': '2fd0d4cd61514b48ae26cbec0ce098f7fef01f7857df9bcf54c781b221525ab9'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair02-peer/package.json': {'bytes': 16136, 'sha256': '34f5eb088ca2657c92bd296c94d6110df07dd1673d10e66b9d9619c37223fa62'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair03-source/selected-targets.json': {'bytes': 16881, 'sha256': '94cbc8b39f678c7cc10aaec4906d37dbb98b87943466f6350c4cbb0febce5a2f'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair03-source/measure_saved_targets.py': {'bytes': 4683, 'sha256': '5443aa1fca072b95b16e8764022c22be20b1e054c8537524aa6163a8b5862a98'}, '/dev/shm/nssoc-tx-path-v4-repair02-drt-03/routed.odb': {'bytes': 53173033, 'sha256': 'b754d43a2b5c8bc8a5a3cc6d85f5790d53b502135a28a5af46caf64857c5f7a4'}, '/dev/shm/nssoc-tx-path-v4-repair02-drt-03/routed.v': {'bytes': 4174181, 'sha256': '5e964dabf6aa8a0d8a42a8ac9adbd0320b668ab350bf3a3ad9f9bd0402f62c90'}, '/dev/shm/nssoc-tx-path-v4-repair02-drt-03/routed.sdc': {'bytes': 124170, 'sha256': 'f6970ab837aa97eb05867ca80ce46c018286779c67126ea0a90546a9542623b3'}, '/dev/shm/nssoc-tx-path-v4-repair02-drt-03/routed.def': {'bytes': 40271385, 'sha256': '73d8d41ddc1c751cbaccc3790320133a71f53c62ef764ab84ae8c0b884aa0c47'}, '/dev/shm/nssoc-tx-path-v4-repair02-drt-03/result.json': {'bytes': 7237, 'sha256': '8aedd0d4f379009390b02ab93b5b39bc45a729665a2a6dd9c0ea60fe0e35a121'}, '/dev/shm/nssoc-tx-path-v4-repair02-detailed-rc-02/routed.spef': {'bytes': 58467514, 'sha256': 'f1163ef379e0f13a3f81a47a9f0a374e3259b336f18ee97934a2c430aab83539'}, '/dev/shm/nssoc-tx-path-v4-repair02-detailed-rc-02/result.json': {'bytes': 4457, 'sha256': '663a51b010dd92f3ff81eae80b607cd64fad0daaa6a116922ab633fc703b00a4'}, '/dev/shm/nssoc-tx-path-v4-repair02-detailed-rc-02/native.log': {'bytes': 93414, 'sha256': '7a3364639794c257e797ab342de47ea80faf2f9e12b0ae261d06ea1d3d723373'}}
assert EXACT_BASELINE_PINS == {p:pin(Path(p)) for p in EXACT_BASELINE_PINS}
libs=[x for x in (B/'route.tcl').read_text().splitlines() if x.startswith('read_liberty ')]
lines=['set_thread_count 1','define_corners slow typical fast',*libs,f'read_db {{{B/"routed.odb"}}}',f'read_sdc {{{B/"routed.sdc"}}}','set_propagated_clock [all_clocks]','set_wire_rc -signal -layer Metal2','set_wire_rc -clock -layer Metal4','set_routing_layers -signal Metal2-Metal5 -clock Metal2-Metal5','set_global_routing_layer_adjustment Metal2-Metal5 0.30']
lines += [f'read_spef -corner {c} {{{RC/"routed.spef"}}}' for c in ('slow','typical','fast')]
lines += ['puts UNCHANGED_SOURCE_ACTUAL_RC_WORST','report_worst_slack -max','report_worst_slack -min']
lines += [f'write_verilog {{{O/"before_clear.v"}}}', 'set cleared_wire_count 0', 'foreach net [[ord::get_db_block] getNets] {', '  if {[$net getSigType] in {POWER GROUND}} {continue}', '  set wire [$net getWire]', '  if {$wire != "NULL"} {odb::dbWire_destroy $wire; incr cleared_wire_count}', '  $net clearGuides', '}', 'puts "REMOVED_CANDIDATE_SIGNAL_WIRES $cleared_wire_count"', f'write_verilog {{{O/"after_clear.v"}}}']
lines += [f'set before_file [open {{{O/"before_clear.v"}}} r]', 'set before_netlist [read $before_file]', 'close $before_file', f'set after_file [open {{{O/"after_clear.v"}}} r]', 'set after_netlist [read $after_file]', 'close $after_file', 'if {$before_netlist ne $after_netlist} {error "Signal-wire removal changed logical netlist"}', 'puts EXACT_LOGICAL_NETLIST_UNCHANGED_AFTER_CLEAR']
lines += [f'global_route -congestion_iterations 100 -guide_file {{{O/"initial.guide"}}}']
lines += ['estimate_parasitics -global_routing', 'puts INITIAL_GLOBAL_ROUTE_PARASITIC_CONTEXT_READY']
# Baseline is immutable TX routed02; after geometry clear use new global-route estimates, never reuse old actual SPEF on changed cells/nets.
lines += ['detailed_placement', 'check_placement -verbose', 'global_route -start_incremental']
def report(tag):
 z=[f'puts {tag}','report_worst_slack -max','report_worst_slack -min','report_tns','report_check_types -max_slew -max_capacitance -violators']
 for c in ('slow','typical','fast'):
  for d in ('max','min'):z.extend([f'puts {tag}_{c}_{d}',f'report_checks -corner {c} -path_delay {d} -group_path_count 1 -fields {{slew cap fanout}} -digits 6'])
 return z
lines += report('TX02_GRT_BEFORE_EXPLICIT_LOAD_ISOLATION')
targets = [{'name': '_26905_', 'master': 'sg13g2_a221oi_1', 'output_pin': 'Y', 'net': '_25378_', 'loads': ['_26907_/A2'], 'buffer': 'sg13g2_buf_4'}, {'name': '_46080_', 'master': 'sg13g2_xnor2_1', 'output_pin': 'Y', 'net': '_19762_', 'loads': ['_46081_/A', '_46096_/A', '_46825_/B'], 'buffer': 'sg13g2_buf_4'}, {'name': '_46081_', 'master': 'sg13g2_xnor2_1', 'output_pin': 'Y', 'net': '_19763_', 'loads': ['_46082_/A', '_46747_/B', '_46932_/A'], 'buffer': 'sg13g2_buf_4'}, {'name': '_46082_', 'master': 'sg13g2_xor2_1', 'output_pin': 'X', 'net': '_19764_', 'loads': ['_46083_/B', '_47648_/B'], 'buffer': 'sg13g2_buf_4'}, {'name': '_47648_', 'master': 'sg13g2_xnor2_1', 'output_pin': 'Y', 'net': '_21030_', 'loads': ['_47650_/A2'], 'buffer': 'sg13g2_buf_4'}, {'name': '_43580_', 'master': 'sg13g2_xnor2_1', 'output_pin': 'Y', 'net': '_17759_', 'loads': ['_43581_/B', '_44021_/A', '_44027_/A', '_44119_/B', '_44834_/A', 'place14891/A'], 'buffer': 'sg13g2_buf_8'}, {'name': '_44119_', 'master': 'sg13g2_xnor2_1', 'output_pin': 'Y', 'net': '_18207_', 'loads': ['_44120_/B', '_45182_/B', '_45231_/A1', '_45232_/A1'], 'buffer': 'sg13g2_buf_4'}]
lines += ['set eco_block [ord::get_db_block]', 'set eco_scale [$eco_block getDbUnitsPerMicron]']
for number,target in enumerate(targets):
 name,master,port,netname,expected_loads,buffer = (target[k] for k in ('name','master','output_pin','net','loads','buffer'))
 lines += [f'set driver [$eco_block findInst {name}]', f'if {{$driver == "NULL" || [[$driver getMaster] getName] != "{master}"}} {{error "Unexpected measured driver {name}"}}', f'set driver_pin [$driver findITerm {port}]', 'set net [$driver_pin getNet]', f'if {{[$net getName] != "{netname}"}} {{error "Measured net changed {name}"}}', 'set loads {}', 'foreach term [$net getITerms] {if {[$term getIoType] == "INPUT"} {lappend loads "[[$term getInst] getName]/[[$term getMTerm] getName]"}}', f'if {{[lsort $loads] ne [lsort {{{" ".join(expected_loads)}}}] || [llength [$net getBTerms]] != 0}} {{error "Measured load census changed {name}"}}', 'set xy [$driver getLocation]', 'set x [expr {double([lindex $xy 0])/$eco_scale}]', 'set y [expr {double([lindex $xy 1])/$eco_scale}]', f'puts "MEASURED_CRITICAL_BUFFER {name}/{port} [$net getName] $loads at $x $y"', f'insert_buffer -buffer_cell {buffer} -load_pins [get_pins $loads] -location [list $x $y] -buffer_name eco03_wire_{number} -net_name eco03_sink_{number}']
upsizes = [('place16128', 'sg13g2_buf_1', 'sg13g2_buf_8'), ('place16147', 'sg13g2_buf_1', 'sg13g2_buf_8'), ('rebuffer18281', 'sg13g2_buf_1', 'sg13g2_buf_4')]
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
r={'status':'RUNNING','inputs':{str(p):pin(p) for p in files},'route_reset':'Only copied signal-wire geometry and guides are cleared; original routed DB/SPEF immutable; exact before/after exported netlist asserted. BaselineTX02 actualRC is reported before changes; then freshGRT estimates. Seven exact measured complex/XOR driver-load sets gain buf4 or buf8 at driver location and three measured buffers are upsized. Existing TX02 hold buffer remains untouched; no new hold insertion is made. No actualRC claimed for changed circuit.', 'scope':'Separate TX candidate03 starts from actual02 detailed geometry and unchanged4nsIOconstraints; seven exact load isolations/three buffer upsizes only. Candidate changes physical cells; sourceDRT remainsimmutable. New global-route estimates are NOT finaltiming; freshDRT/nominalRC/equivalence/physicalportreplay required.','elapsed_watchdog_seconds':None,'address_space_limit_bytes':int(2.5*1024**3),'single_cpu':True,'qualified_rc':False,'physical_acceptance':False,'minimum_shared_free':shutil.disk_usage('/dev/shm').free}
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
