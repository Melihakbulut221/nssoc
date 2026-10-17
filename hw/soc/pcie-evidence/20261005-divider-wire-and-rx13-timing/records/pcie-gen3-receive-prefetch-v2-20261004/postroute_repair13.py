# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Candidate13 isolates six measured RX12 critical nets and upsizes four weak cells; original12 immutable; fresh GRT after changes."""
from pathlib import Path
import hashlib,json,resource,os,signal,subprocess,time,shutil
R=Path.cwd();B=Path('/dev/shm/nssoc-rx-prefetch-v2-repair12-drt-01');RC=Path('/dev/shm/nssoc-rx-prefetch-v2-repair12-detailed-rc-01');O=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-13');
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
EXACT_BASELINE_PINS = {'/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/postroute_repair12.py': {'bytes': 10763, 'sha256': '3a62ada772697e80e20a38421b44644af1494f36f5879b1d0a3b6bedfbf62fc8'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair12-peer/review.json': {'bytes': 36922, 'sha256': '85ea32c49e3d5db8a4dafdb6b74d326b6a9025525c791cad4bf319b2c98bb161'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair12-peer/release.json': {'bytes': 3530, 'sha256': '3b87bb5f52425373d30df2dc0fd7a536722dbe6f19733b2ff73ab3819398c16a'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair12-peer/publication-review.json': {'bytes': 7901, 'sha256': '38b32d79fc142612a3c729bf8f98bb134c993962ff208b1ca9c9a429ca76b31b'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair13-source/selected-targets.json': {'bytes': 17769, 'sha256': '219e0305b71378382d1d1ac2093ea1171a5120f62745b78f59dd09ef2b501a8c'}, '/dev/shm/nssoc-rx-prefetch-v2-repair12-drt-01/routed.odb': {'bytes': 28038567, 'sha256': 'de8f43e5d8eadd3600268e7704b3144450b20a8e633149ae12ae6edbf174e787'}, '/dev/shm/nssoc-rx-prefetch-v2-repair12-drt-01/routed.v': {'bytes': 2092773, 'sha256': 'ce021e9eaba2d4db461cf5207a86a0ded9790830000248b6ec4eb0984b43a9a4'}, '/dev/shm/nssoc-rx-prefetch-v2-repair12-drt-01/routed.sdc': {'bytes': 89666, 'sha256': '16df28ef11616fbafd617dcba135dfca7eda403e5f23ca5de244ccbc9b2fb59e'}, '/dev/shm/nssoc-rx-prefetch-v2-repair12-detailed-rc-01/routed.spef': {'bytes': 29126708, 'sha256': '504d52cdae0ce3172179b8107a9377efa6a8ce4e0cdf159fb147f6494787f4ab'}, '/dev/shm/nssoc-rx-prefetch-v2-repair12-detailed-rc-01/result.json': {'bytes': 4443, 'sha256': '0c595324a6fc5964c7da01057a78ae31059eb587dd138dee86b352198fc661d7'}}
assert EXACT_BASELINE_PINS == {p:pin(Path(p)) for p in EXACT_BASELINE_PINS}
libs=[x for x in (B/'route.tcl').read_text().splitlines() if x.startswith('read_liberty ')]
lines=['set_thread_count 1','define_corners slow typical fast',*libs,f'read_db {{{B/"routed.odb"}}}',f'read_sdc {{{B/"routed.sdc"}}}','set_propagated_clock [all_clocks]','set_wire_rc -signal -layer Metal2','set_wire_rc -clock -layer Metal4','set_routing_layers -signal Metal2-Metal5 -clock Metal2-Metal5','set_global_routing_layer_adjustment Metal2-Metal5 0.30']
lines += [f'read_spef -corner {c} {{{RC/"routed.spef"}}}' for c in ('slow','typical','fast')]
lines += ['puts UNCHANGED_SOURCE_ACTUAL_RC_WORST','report_worst_slack -max','report_worst_slack -min']
lines += [f'write_verilog {{{O/"before_clear.v"}}}', 'set cleared_wire_count 0', 'foreach net [[ord::get_db_block] getNets] {', '  if {[$net getSigType] in {POWER GROUND}} {continue}', '  set wire [$net getWire]', '  if {$wire != "NULL"} {odb::dbWire_destroy $wire; incr cleared_wire_count}', '  $net clearGuides', '}', 'puts "REMOVED_CANDIDATE_SIGNAL_WIRES $cleared_wire_count"', f'write_verilog {{{O/"after_clear.v"}}}']
lines += [f'set before_file [open {{{O/"before_clear.v"}}} r]', 'set before_netlist [read $before_file]', 'close $before_file', f'set after_file [open {{{O/"after_clear.v"}}} r]', 'set after_netlist [read $after_file]', 'close $after_file', 'if {$before_netlist ne $after_netlist} {error "Signal-wire removal changed logical netlist"}', 'puts EXACT_LOGICAL_NETLIST_UNCHANGED_AFTER_CLEAR']
lines += [f'global_route -congestion_iterations 100 -guide_file {{{O/"initial.guide"}}}']
lines += ['estimate_parasitics -global_routing', 'puts INITIAL_GLOBAL_ROUTE_PARASITIC_CONTEXT_READY']
# Baseline is immutable routed12; after geometry clear use new global-route estimates, never reuse old actual SPEF on changed cells/nets.
lines += ['detailed_placement', 'check_placement -verbose', 'global_route -start_incremental']
def report(tag):
 z=[f'puts {tag}','report_worst_slack -max','report_worst_slack -min','report_tns','report_check_types -max_slew -max_capacitance -violators']
 for c in ('slow','typical','fast'):
  for d in ('max','min'):z.extend([f'puts {tag}_{c}_{d}',f'report_checks -corner {c} -path_delay {d} -group_path_count 1 -fields {{slew cap fanout}} -digits 6'])
 return z
lines += report('CANDIDATE12_GRT_BEFORE_EXPLICIT_LOAD_ISOLATION')
targets = [{'name': '_19674_', 'master': 'sg13g2_nand3_1', 'output_pin': 'Y', 'net': '_02738_', 'loads': ['_19675_/A', '_19719_/B', '_19720_/B', '_19829_/A', '_19884_/B', '_19948_/B', 'place9604/A'], 'buffer': 'sg13g2_buf_8'}, {'name': '_19783_', 'master': 'sg13g2_nor2_2', 'output_pin': 'Y', 'net': '_02847_', 'loads': ['_19784_/B1', '_19993_/A2', '_20171_/B', '_20195_/A2', '_20294_/B1', '_20467_/B1', '_20577_/A2', '_24539_/B'], 'buffer': 'sg13g2_buf_8'}, {'name': '_19786_', 'master': 'sg13g2_or2_2', 'output_pin': 'X', 'net': '_02850_', 'loads': ['_19787_/B', '_19827_/B', '_19869_/B', '_19873_/B', '_19897_/B', '_19905_/A', 'place9590/A'], 'buffer': 'sg13g2_buf_8'}, {'name': '_20546_', 'master': 'sg13g2_nand4_1', 'output_pin': 'Y', 'net': '_03604_', 'loads': ['_20552_/D'], 'buffer': 'sg13g2_buf_4'}, {'name': '_19774_', 'master': 'sg13g2_nand4_1', 'output_pin': 'Y', 'net': '_02838_', 'loads': ['_19814_/D'], 'buffer': 'sg13g2_buf_4'}, {'name': '_20604_', 'master': 'sg13g2_nand4_1', 'output_pin': 'Y', 'net': '_03662_', 'loads': ['_20605_/A'], 'buffer': 'sg13g2_buf_4'}]
lines += ['set eco_block [ord::get_db_block]', 'set eco_scale [$eco_block getDbUnitsPerMicron]']
for number,target in enumerate(targets):
 name,master,output_pin,netname,expected,buffer = (target[k] for k in ('name','master','output_pin','net','loads','buffer'))
 expected_tcl=' '.join(expected)
 lines += [f'set driver [$eco_block findInst {name}]', f'if {{$driver == "NULL" || [[$driver getMaster] getName] != "{master}"}} {{error "Unexpected measured driver {name}"}}', f'set driver_pin [$driver findITerm {output_pin}]', 'set net [$driver_pin getNet]', f'if {{[$net getName] != "{netname}"}} {{error "Measured net changed {name}"}}', 'set loads {}', 'foreach term [$net getITerms] {if {[$term getIoType] == "INPUT"} {lappend loads "[[$term getInst] getName]/[[$term getMTerm] getName]"}}', f'if {{[lsort $loads] ne [lsort {{{expected_tcl}}}]}} {{error "Exact measured load set changed {name}"}}', 'set xy [$driver getLocation]', 'set x [expr {double([lindex $xy 0])/$eco_scale}]', 'set y [expr {double([lindex $xy 1])/$eco_scale}]', f'puts "MEASURED_CRITICAL_BUFFER {name}/{output_pin} [$net getName] $loads at $x $y"', f'insert_buffer -buffer_cell {buffer} -load_pins [get_pins $loads] -location [list $x $y] -buffer_name eco13_wire_{number} -net_name eco13_sink_{number}']
upsizes = [('place9604', 'sg13g2_buf_1', 'sg13g2_buf_4'), ('rebuffer11537', 'sg13g2_buf_1', 'sg13g2_buf_4'), ('_24539_', 'sg13g2_nand2_1', 'sg13g2_nand2_2'), ('_19892_', 'sg13g2_nor2_1', 'sg13g2_nor2_2')]
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
r={'status':'RUNNING','inputs':{str(p):pin(p) for p in files},'route_reset':'Only copied signal-wire geometry and guides are cleared; original routed DB/SPEF immutable; exact before/after exported netlist asserted. Baseline12 actualRC is reported before changes; then freshGRT estimates. Six measured drivers gain exact-load buffer isolation at actual driver location and four measured weak cells are upsized with unchanged Boolean functions. No actualRC claimed for changed circuit.', 'scope':'Separate candidate13 starts from actual12 detailed geometry and unchanged4nsIOconstraints; six local critical-wire buffers/four upsizes only. Candidate changes physical cells; sourceDRT remainsimmutable. New global-route estimates are NOT finaltiming; freshDRT/nominalRC/equivalence/physicalportreplay required.','elapsed_watchdog_seconds':None,'address_space_limit_bytes':int(2.5*1024**3),'single_cpu':True,'qualified_rc':False,'physical_acceptance':False,'minimum_shared_free':shutil.disk_usage('/dev/shm').free}
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
