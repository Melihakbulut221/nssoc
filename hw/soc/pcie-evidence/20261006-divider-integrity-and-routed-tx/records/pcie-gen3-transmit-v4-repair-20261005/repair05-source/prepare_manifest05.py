# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind only the existing TX05 route; no native/controller execution."""
from pathlib import Path
import ast,datetime,hashlib,json,os,re
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');B=R/'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005';S=B/'repair05-source';Q=B/'repair05-peer';C=B/'repair05-continuation01';RB=R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def save(p,v):
 assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
def named(path,name):return next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n,(ast.FunctionDef,ast.ClassDef))and n.name==name)
old=B/'repair03-continuation02/run.py';new=C/'run.py'
for name in ['pin','require','atomic','limits','read_live_result']:
 assert ast.dump(named(old,name),include_attributes=False)==ast.dump(named(new,name),include_attributes=False)
a=named(old,'run_stage');b=named(new,'run_stage')
for n in ast.walk(b):
 if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='launch':
  k=next(k for k in n.keywords if k.arg=='env');assert ast.unparse(k.value)=="{k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONEXECUTABLE')}";n.keywords.remove(k)
assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
reuse=json.loads((RB/'repair16one-continuation01/lifecycle-controls-reuse.json').read_text());assert reuse['inputs']=={p:pin(p)for p in reuse['inputs']}
assert (B/'owned_lifecycle05.py').read_bytes()==(RB/'owned_lifecycle16.py').read_bytes()
reuse.update(status='REUSED_EXACT_TX03_STAGE_AND_RX16ONE_NESTED_CLEANUP_WITH_SANITIZED_ENV',old_controller=pin(old),new_controller=pin(new),inner_helper=pin(B/'owned_lifecycle05.py'),inner_helper_byte_equal_RX16=True,scope='Exact prior three outer terminal/failure controls and current RX16 actual two-tier signal control with byte-identical WNOWAIT helper. Sole stage AST delta sanitizes Python env. No rerun.')
save(C/'lifecycle-controls-reuse.json',reuse)
def identity(pid,expected):
 p=Path('/proc')/str(pid);a=(p/'stat').read_text().rsplit(')',1)[1].split();assert int(a[19])==expected and a[0]!='Z' and os.sched_getaffinity(pid)=={4};return dict(pid=pid,start_ticks=int(a[19]),process_group=int(a[2]),ppid=int(a[1]),state=a[0],argv=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),affinity=[4])
o=identity(225863,4263948);n=identity(225869,4263984);assert o['ppid']==1 and n['ppid']==o['pid']
D=Path('/dev/shm/nssoc-tx-path-v4-repair05-drt-01');d=json.loads((D/'result.json').read_text());assert d['status']=='RUNNING' and d['pid']==n['pid'] and d['inputs']=={p:pin(p)for p in d['inputs']}
net=Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-05/repaired.v');text=net.read_text();loads={}
for match in re.finditer(r'\b(sg13g2_(?:inv|buf)_\d+)\s+(clkload\d+)\s*\((.*?)\);',text,re.S):
 connections=re.findall(r'\.(\w+)\(([^()]*)\)',match[3]);assert len(connections)==1 and connections[0][0]=='A';loads[match[2]]=dict(master=match[1],clock_input_net=connections[0][1])
assert set(loads)=={f'clkload{i}'for i in range(150)}
save(C/'candidate-cts-load-source-check.json',dict(status='EXACT150INPUT_ONLY_CTS_LOADS_IN_PROVED_CANDIDATE',candidate=pin(net),loads=loads,scope='Source-only. Future actual unannotated/SPEF150 clock input binding remains mandatory.'))
files=[C/'run.py',C/'source-bridge.json',C/'lifecycle-controls-reuse.json',C/'candidate-cts-load-source-check.json',Q/'review.py',Q/'seal.py',Q/'source-freeze.json',Q/'source-derivation.json',Q/'metadata-name-correction01.json',B/'detailed_rc_repair05.py',B/'owned_lifecycle05.py',S/'prepare_continuation05.py',Path(__file__),R/'scripts/publish_pcie_native_capture_v3.py',R/'scripts/publish_pcie_native_capture_v2.py',R/'scripts/characterize_pcie_clock_trim_stream_v2.py',R/'hw/soc/out/pcie-agent-resume-second-20261005/publisher-v3-source-freeze04.json',R/'hw/soc/out/pcie-agent-resume-second-20261005/publisher-v3-source-only-peer04.json',R/'hw/soc/tools/cocotb-venv/bin/python3',Path('/usr/bin/python3.12')]
files += [S/x for x in ['drt-launch01.json','pre-drt-proof-port-review.json','source-only-peer-rx.json','proof-source-only-peer-rx02.json','ports02-source-only-peer-rx.json','route-rc-source-only-peer-rx.json','route-rc-source-freeze.json','route-rc-source-bridge.json','test_owned_lifecycle05.py','lifecycle-controls02.log','binding-controls02.log']]
files += [RB/'repair16-source/proof16one-lifecycle-control.json',RB/'repair16-source/control_proof_pipeline16one.py',RB/'repair16-source/launcher-source-only-peer-root16one.json']
files += [Path(p)for p in reuse['inputs']]
files += [p for p in Path('/dev/shm/nssoc-rx16one-pipeline-lifecycle01').rglob('*')if p.is_file()]
files += [B/'repair05-preroute-preservation'/x for x in ['package.json','pcie-tx-repair05-preroute-validation-20261006.json','release01.json']]
m=dict(status='FROZEN_TX05_DEPENDENT_CHAIN_SOURCE_AND_EXISTING_ROUTE',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),python=str(R/'hw/soc/tools/cocotb-venv/bin/python3'),lifecycle_source=str(R/'scripts/characterize_pcie_clock_trim_stream_v2.py'),inputs={str(p):pin(p)for p in dict.fromkeys(files)},route_owner=o,route_native=n,route_inputs=d['inputs'],candidate_netlist=str(net),stages=['existing exact TX05 DRT01','fresh TX05 nominal RC01','four-class three-corner saved review vs actual TX03','full finite capsule/member readback','three unique assets V3 dual public readback'],cpu=4,AS_bytes=int(2.5*1024**3),scratch_entry_bytes=1024**3,scratch_continuous_floor_bytes=528*1024**2,healthy_elapsed_watchdog_seconds=None,outer_failure_grace_seconds=15,inner_RC_failure_grace_seconds=2,inner_publisher_failure_grace_seconds=1,no_existing_DRT_ownership_or_signals=True,qualified_rc=False,physical_acceptance=False)
save(C/'manifest.json',m);print(json.dumps(dict(manifest=pin(C/'manifest.json'),inputs=len(m['inputs']),route_inputs=len(m['route_inputs']),owner=o,native=n),indent=2))
