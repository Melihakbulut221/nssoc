# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind reviewed dependent bodies to one existing native route birth."""
import ast, datetime, hashlib, json, os
from pathlib import Path
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B=R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004';S=B/'repair16-source';C=B/'repair16one-continuation01';Q=B/'repair16one-peer'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def save(p,v):
 assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
def named_ast(path,name):
 return next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
old=B/'repair14a-continuation01/run.py';new=C/'run.py'
for name in ['pin','require','atomic','limits','read_live_result']:
 assert ast.dump(named_ast(old,name),include_attributes=False)==ast.dump(named_ast(new,name),include_attributes=False)
o=named_ast(old,'run_stage');n=named_ast(new,'run_stage')
# The sole stage-body delta sanitizes inherited Python variables.
for call in ast.walk(n):
 if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='launch':
  kw=next(x for x in call.keywords if x.arg=='env');assert ast.unparse(kw.value)=="{k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONEXECUTABLE')}";call.keywords.remove(kw)
assert ast.dump(o,include_attributes=False)==ast.dump(n,include_attributes=False)
reuse=json.loads((B/'repair14a-continuation01/lifecycle-controls-reuse.json').read_text())
assert reuse['inputs']=={p:pin(p) for p in reuse['inputs']}
reuse.update(status='REUSED_SAME_NATIVE_STAGE_LIFECYCLE_WITH_SANITIZED_ENV',old_controller=pin(old),new_controller=pin(new),exact_stage_AST_after_removing_only_env_sanitizer=True,scope='Prior three actual failure/complete/teardown controls retained unchanged. Only stage environment sanitizer added. Current RC inner WNOWAIT helper has separate actual two-level cleanup evidence; no healthy timeout.')
save(C/'lifecycle-controls-reuse.json',reuse)
active=json.loads((S/'active-drt16one.json').read_text())
for key in ['route_owner','route_native']:
 row=active[key];a=(Path('/proc')/str(row['pid'])/'stat').read_text().rsplit(')',1)[1].split();assert int(a[19])==int(row['start_ticks']) and int(a[2])==row['process_group'] and a[0]!='Z' and os.sched_getaffinity(row['pid'])=={8}
paths=[C/'run.py',C/'source-bridge.json',C/'lifecycle-controls-reuse.json',Q/'review.py',Q/'seal.py',Q/'source-bridge.json',Q/'source-freeze.json',B/'detailed_rc_repair16one.py',B/'owned_lifecycle16.py',Path(__file__),R/'scripts/publish_pcie_native_capture_v3.py',R/'scripts/publish_pcie_native_capture_v2.py',R/'scripts/characterize_pcie_clock_trim_stream_v2.py',R/'hw/soc/out/pcie-agent-resume-second-20261005/publisher-v3-source-freeze04.json',R/'hw/soc/out/pcie-agent-resume-second-20261005/publisher-v3-source-only-peer04.json',R/'hw/soc/tools/cocotb-venv/bin/python3',Path('/usr/bin/python3.12')]
paths += [S/x for x in ['active-drt16one.json','active-drt16one-launch.json','launch_drt16one.py','pre-drt-proof-port-review16one.json','source-only-peer04-vco.json','proof-source-only-peer-root16one.json','launcher-source-only-peer-root16one.json','route-rc-source-only-peer-root16one.json','route-rc-source-freeze16one.json','route-rc-source-bridge16one.json','prepare_continuation16one.py','route-trial-selection16one.json','proof16one-lifecycle-control.json','control_proof_pipeline16one.py','launcher-source-freeze16one.json']]
paths += [Path(p) for p in reuse['inputs']]
paths += [p for p in Path('/dev/shm/nssoc-rx16one-pipeline-lifecycle01').rglob('*') if p.is_file()]
route=json.loads(Path('/dev/shm/nssoc-rx-prefetch-v2-repair16one-drt-01/result.json').read_text())
assert route['inputs']==active['route_inputs']=={p:pin(p) for p in route['inputs']}
manifest=dict(status='FROZEN_DEPENDENT_CONTINUATION_BEFORE_EXECUTION',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),boot_id=active['boot_id'],python=str(R/'hw/soc/tools/cocotb-venv/bin/python3'),lifecycle_source=str(R/'scripts/characterize_pcie_clock_trim_stream_v2.py'),inputs={str(p):pin(p) for p in dict.fromkeys(paths)},route_owner=active['route_owner'],route_native=active['route_native'],route_inputs=route['inputs'],candidate_netlist='/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-one-repair-04/repaired.v',stages=['exact existing RX16one DRT01 completion','fresh RX16one RC01','frozen saved-output review vs published RX14A','complete finite capsule and full member manifest','immutable three-asset dual roundtrip publication V3'],cpu=8,AS_bytes=int(2.5*1024**3),scratch_entry_bytes=1024**3,scratch_continuous_floor_bytes=528*1024**2,healthy_elapsed_watchdog_seconds=None,outer_failure_grace_seconds=15,inner_RC_failure_grace_seconds=2,inner_publisher_failure_grace_seconds=1,publisher_transport_attempts=4,publisher_transport_deadline_seconds=120,no_existing_DRT_ownership_or_signals=True,qualified_rc=False,physical_acceptance=False)
save(C/'manifest.json',manifest)
print(json.dumps(dict(manifest=pin(C/'manifest.json'),source_pins=len(manifest['inputs']),route_input_pins=len(route['inputs']),route_owner=active['route_owner'],route_native=active['route_native']),indent=2))
