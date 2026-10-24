"""Independent source/saved-evidence audit; no production imports or signals."""
from pathlib import Path
import ast,hashlib,json,os
R=Path.cwd();B=R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004';C=Path(__file__).resolve().parent;Q=B/'repair16one-peer'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def node(p,name):return next(n for n in ast.walk(ast.parse(p.read_text()))if isinstance(n,(ast.FunctionDef,ast.ClassDef))and n.name==name)
def dump(n):return ast.dump(n,include_attributes=False)
m=json.loads((C/'manifest.json').read_text());assert pin(C/'manifest.json')==dict(bytes=19752,sha256='c0f42c8660c7dba409764f20a0104a6b584544b69026adb6674c0379db9dbed3')
for category in ['inputs','route_inputs']:
 for p,v in m[category].items():assert pin(p)==v,p
bridges=[]
for source in [C/'source-bridge.json',Q/'source-bridge.json']:
 for row in json.loads(source.read_text()):
  for side in ['before','after']:
   p=Path(row[side]['path']);assert pin(p)=={k:row[side][k]for k in['bytes','sha256']}
   assert ''.join(x[side]for x in row['opcodes'])==p.read_text()
  for op in row['opcodes']:
   if op['tag']=='equal':assert op['before']==op['after']
  bridges.append(dict(path=str(source),before=row['before'],after=row['after']))
# Production stage logic exact after only declared environment sanitization.
a=node(C/'run.py','run_stage');old=node(B/'repair13-continuation01/run.py','run_stage')
for n in ast.walk(a):
 if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='launch':
  env=next(k for k in n.keywords if k.arg=='env');assert isinstance(env.value,ast.DictComp);n.keywords.remove(env)
assert dump(a)==dump(old)
reuse=json.loads((C/'lifecycle-controls-reuse.json').read_text())
for p,v in reuse['inputs'].items():assert pin(p)==v,p
controls=json.loads((B/'repair13-continuation01/lifecycle-controls.json').read_text());assert len(controls['results'])==3
for row in controls['results']:assert row['terminal_guard_or_error_seen']and not row['remaining_members']
inner=json.loads((B/'repair16-source/proof16one-lifecycle-control.json').read_text());assert inner['status']=='PASS_ACTUAL_NESTED_STAGE_NATIVE_SIGNAL_CLEANUP'and inner['all_three_groups_no_live_members']and inner['native_ignored_SIGTERM']
assert inner['elapsed_seconds']<15 and inner['helper']==pin(B/'owned_lifecycle16.py')
rootpeer=json.loads((B/'repair16-source/route-rc-source-only-peer-root16one.json').read_text());assert rootpeer['status']=='PASS_SOURCE_ONLY_RX16ONE_ROUTE_RC_AND_SAVED_NATIVE_PROOF_PORTS'and not rootpeer['findings']
assert m['outer_failure_grace_seconds']==15 and m['inner_RC_failure_grace_seconds']==2 and m['healthy_elapsed_watchdog_seconds']is None
assert m['no_existing_DRT_ownership_or_signals']and not m['qualified_rc']and not m['physical_acceptance']
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==m['boot_id']
observed={}
for key in ['route_owner','route_native']:
 birth=m[key];p=Path('/proc')/str(birth['pid']);s=(p/'stat').read_text().rsplit(') ',1)[1].split()
 assert int(s[19])==int(birth['start_ticks'])and int(s[2])==birth['process_group']and s[0]!='Z'
 assert sorted(os.sched_getaffinity(birth['pid']))==[8]
 observed[key]=dict(pid=birth['pid'],start_ticks=s[19],group=int(s[2]),state=s[0])
assert not(C/'result.json').exists()and not Path('/dev/shm/nssoc-rx-prefetch-v2-repair16one-detailed-rc-01').exists()
methods=[C/'run.py',C/'launch.py',Q/'review.py',Q/'seal.py',B/'detailed_rc_repair16one.py',B/'owned_lifecycle16.py']
for p in methods:ast.parse(p.read_text())
q=dict(status='PASS_SOURCE_ONLY_RX16ONE_ROUTE_RC_CONTINUATION',manifest=pin(C/'manifest.json'),launcher=pin(C/'launch.py'),findings=[],method=pin(Path(__file__)),method_pins={str(p):pin(p)for p in methods},input_pins_rehashed=len(m['inputs']),route_input_pins_rehashed=len(m['route_inputs']),whole_body_bridge_records=len(bridges),existing_births_observed_read_only=observed,reviewer_initial_env_normalization_corrected=True,saved_outer_lifecycle_controls=3,saved_inner_two_level_control=True,scope='Full controller, detacher, reviewer and sealer plus current innerRC/owned lifecycle read. Passive observation only of exactboot/birth existingDRT; no adoption, signals or duplicated route. Fresh dependentRC guard, terminal source/output/zeroDRC/same netlist gates; sanitized lexical interpreter; exclusive launch marker/newsession/closedstdio. Current ownedRC WNOWAIT2s cleanup fits tested15s outergrace; terminal floor and postcomplete/postcontext cancellation preserved. Recounted saved controls only. Review retains all36 setup/hold/recovery/removal paths,78dummyCTS input bindings, six portcases and canonical savedproof; nominal unqualifiedRC and failure signs remain explicit. Sealer retains full native captures and immutable fullmember readback, external execution binding follows closure. No producer/EDA/proof/tests/network run or claimed route/RC completion by peer.')
(C/'source-only-peer-pll.json').write_text(json.dumps(q,indent=2)+'\n');print(q['status'],pin(C/'source-only-peer-pll.json'))
