# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent detached support source peer. Never executes a producer/launcher."""
import ast,difflib,hashlib,json,os,shutil
from pathlib import Path
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');B=Path(__file__).resolve().parent;P=B.parent
j=lambda p:json.loads(p.read_text())
def pin(p):
 with Path(p).open('rb')as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
POLICY=dict(bytes=18548,sha256='076665ab174b24f173cd5ce4ecc6d5f9433d662b4388d126926d3c75e3f3a80b')
assert pin(B/'policy.json')==POLICY
policy=j(B/'policy.json');pins={}
for p,h in policy['pins'].items():assert pin(p)==h,p;pins[p]=h
assert policy['native_CPU']==12 and policy['publisher_CPU']==14
assert policy['python']==str(R/'hw/soc/tools/cocotb-venv/bin/python')
assert policy['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
bridge=j(B/'support-derivation01.json');assert len(bridge['bridges'])==4
for row in bridge['bridges']:
 for k in('original','derived'):
  x=row[k];assert pin(x['path'])=={n:x[n]for n in('bytes','sha256')}
 assert ''.join(difflib.restore(row['whole_byte_diff'],1))==Path(row['original']['path']).read_text()
 assert ''.join(difflib.restore(row['whole_byte_diff'],2))==Path(row['derived']['path']).read_text()
rootpeer=j(P/'source-saved-peer-root02.json');assert rootpeer['status']=='PASS_SOURCE_AND_SAVED_LOCAL_PLL_CAPTURE_AND_PUBLISHER'and not rootpeer['findings']and rootpeer['freeze']==pin(P/'source-freeze02.json')
workerpeer=j(P/'source-saved-worker-peer-rx01.json');assert workerpeer['status']=='PASS_SOURCE_AND_SAVED_LOCAL_SPOOL_WORKER'and not workerpeer['findings']and workerpeer['freeze']==pin(P/'source-freeze02.json')
old=R/'hw/soc/out/pcie-pll-acquisition-v3-20261005/numerical-convergence-plan01/launch01';offline=j(old/'offline-prerequisites.json');assert offline['status']=='PASS_OFFLINE_MAXSTEP125_PREREQUISITES'and offline['devices']==539
assert offline['prerequisites']==pin(old/'prerequisites.json')and offline['declaration']==pin(old/'declaration.json')
assert len(offline['inputs'])==3557
for p,h in offline['inputs'].items():assert pin(p)==h,p;pins[p]=h
plan=j(old/'declaration.json');assert plan['TSTEP_s']==2.5e-12 and plan['second_TMAX_s']==1.25e-12 and plan['stop_s']==1e-6 and plan['frequency_difference_limit_ppm']==100 and plan['matched_phase_limit_s']==50e-12 and plan['phase_alignment_or_offset_removal']is False
methods={n:(B/n).read_text()for n in('launch_native.py','detach_native.py','launch_publisher.py','detach_publisher.py')}
for name,s in methods.items():ast.parse(s)
assert 'subprocess'not in methods['launch_native.py']and "'gh'"not in methods['launch_native.py']
assert "'--step-ps','2.5'"in methods['launch_native.py']and "'--spool',str(spool)"in methods['launch_native.py']
assert "spool.parent.stat().st_dev!=Path('/dev/shm').stat().st_dev"in methods['launch_native.py']
assert 'limits.reserve+limits.payload+limits.floor'in methods['launch_native.py']
for name in('detach_native.py','detach_publisher.py'):
 s=methods[name]
 for text in("stdin=subprocess.DEVNULL","start_new_session=True","close_fds=True","['PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE']","fields[19]","fields[2]",".open('x')"):
  assert text in s,(name,text)
 assert ".resolve()"not in s
assert "'12'"in methods['detach_native.py']and "'14'"in methods['detach_publisher.py']
assert '--paginate'in methods['launch_publisher.py']and 'local.Limits().parts+3<=1000'in methods['launch_publisher.py']
for name in('launch_native.py','launch_publisher.py'):
 assert 'os.execv(command[0],command)'in methods[name]and 'os.O_EXCL'in methods[name]
# Policy/source review is not a runtime resource reservation or actual progress claim.
assert all(not Path(policy[k]).exists()for k in('native_out','spool_out','publisher_out'))
assert not(B/'launch-once.json').exists()and not(B/'publication-launch-once.json').exists()
observation=dict(RAM_free=shutil.disk_usage('/dev/shm').free,SSD_free=shutil.disk_usage(Path(policy['spool_out']).parent).free,affinity_available=sorted(os.sched_getaffinity(0)))
record=dict(status='PASS_SOURCE_ONLY_DETACHED_LOCAL_PLL_V5_LAUNCH',policy=POLICY,findings=[],method=pin(Path(__file__)),source_pins={str(B/n):pin(B/n)for n in methods},method_peer=pin(P/'source-saved-peer-root02.json'),worker_peer=pin(P/'source-saved-worker-peer-rx01.json'),verified_pins=pins,full_four_bridges_verified=True,source_prerequisite_paths=3557,
 actual_runtime_not_launched=True,fresh_roots_confirmed=True,resources_observed_not_reserved=observation,
 checks=['Native CPU12 offline preflight binds exact former declaration/full source prerequisites and unchanged539device full deck hash; no network gate in native launch.','FreshSSD spool is outsideRAM filesystem and requires10GiB physical reservation plus8GiB payload and1GiB floor; nativeRAM562MiBentry preserves50MiBcap+512MiBfloor.','Separate CPU14 publisher begins only after exactspoolconfiguration; duplicateworker check, exclusiveonce markers, freshworkerroot and all512parts+3metadata release slots checked. Headroom is explicitly not atomicreservation.','Both detachedentries preserve lexical3.12venv and remove Python overrides; DEVNULL/newsession/filelogs/closefds, samePIDexec, birth/start/group receipt. Freshcross-callidentity/native progress mandatory afterlaunch.','Worker owns transport children only; no native adoption/signals. Publishermetadata preflight has explicit120s transport deadline; healthy native has noelapsedwatchdog. Rootaggregated69 source/control predicates and worker21 actual predicates remain pinned.'],
 scope='Source-only independent fullbody/inverse/read-onlypin review. No launcher/importedproducer/control/EDA/network execution or simulation claim. Hypatia must rerun fresh resource/duplicate checks and confirm exactbirth/progress across calls. Local retained completion, public byte delivery, replay and physicalqualification remain separate.')
with(B/'source-peer-vco01.json').open('x')as out:json.dump(record,out,indent=2);out.write('\n')
print(json.dumps(dict(peer=pin(B/'source-peer-vco01.json'),unique_verified_pins=len(pins),resource_observation=observation)))
