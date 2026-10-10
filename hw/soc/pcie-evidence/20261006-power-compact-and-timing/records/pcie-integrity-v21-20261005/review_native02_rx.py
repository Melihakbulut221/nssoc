# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,hashlib,json,tarfile,xml.etree.ElementTree as ET
B=Path(__file__).resolve().parent;R=Path.cwd()
def pin(p):
 p=Path(p);return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
policy=B/'continuation-policy02.json';j=json.loads(policy.read_text());assert pin(policy)==dict(bytes=7537,sha256='688adf4334d92975f11255ea8a0219456ba970e8304e89bb660b8a3ff2234faa')
for k in ('method_pins','source_pins'):assert j[k]=={p:pin(p)for p in j[k]}
bridge_count=0
for filename in ('native-source-bridges01.json','native-source-supplement02.json'):
 for row in json.loads((B/filename).read_text()):
  a=Path(row['before']['path']).read_text();z=Path(row['after']['path']).read_text()
  assert a==''.join(x['before']for x in row['opcodes'])and z==''.join(x['after']for x in row['opcodes']);bridge_count+=1
  n=Path(row['after']['path']).name
  if n in ('balanced_import.py','balanced_preplacement.py','prove_balanced_import.py','review_timing.py','analyze_critical_path.py'):assert a.replace('v20','v21').replace('V20','V21')==z
fun=lambda s:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
a=fun((B.parent/'pcie-integrity-v20-20261005/continue_native04.py').read_text());z=fun((B/'continue_native02.py').read_text())
assert all(a[n]==z[n]for n in ('pin','explicit_stop','verify_sources','stage'))
a=(B.parent/'pcie-integrity-v20-20261005/run_balanced_map04.py').read_text();z=(B/'run_balanced_map.py').read_text();assert a[a.index('def save():'):].replace('v20','v21')==z[z.index('def save():'):]
vpath=Path(j['controls']['validation']['path']);v=json.loads(vpath.read_text());assert pin(vpath)=={k:j['controls']['validation'][k]for k in ('bytes','sha256')}
archive=Path(v['archive']['path']);assert pin(archive)=={k:v['archive'][k]for k in ('bytes','sha256')}
with tarfile.open(archive,'r:xz')as t:
 members=t.getmembers();assert len(members)==345 and len({m.name for m in members})==345 and all(m.isfile()for m in members)
 manifest=json.load(t.extractfile('members.json'));assert len(manifest)==344
 for m in members:
  raw=t.extractfile(m).read()
  if m.name=='members.json':continue
  assert len(raw)==manifest[m.name]['bytes']and hashlib.sha256(raw).hexdigest()==manifest[m.name]['sha256'],m.name
recounts=[]
for row in v['pytest_recounts']:
 p=Path(row['path']);assert pin(p)=={k:row[k]for k in ('bytes','sha256')};cs=list(ET.parse(p).getroot().iter('testcase'))
 r=dict(passed=sum(not any(c.find(k)is not None for k in('failure','error','skipped'))for c in cs),failed=sum(any(c.find(k)is not None for k in('failure','error'))for c in cs),skipped=sum(c.find('skipped')is not None for c in cs))
 assert r=={k:row[k]for k in r};recounts.append(r)
assert recounts==[dict(passed=26,failed=1,skipped=0),dict(passed=6,failed=0,skipped=0)]
for row in v['helper_recounts']:
 p=Path(row['path']);assert pin(p)=={k:row[k]for k in ('bytes','sha256')};cs=list(ET.parse(p.parent/'results.xml').getroot().iter('testcase'))
 actual=dict(passed=sum(not any(c.find(k)is not None for k in('failure','error','skipped'))for c in cs),failed=sum(any(c.find(k)is not None for k in('failure','error'))for c in cs),skipped=sum(c.find('skipped')is not None for c in cs));assert actual==row['counts']
for row in v['strict_new_whole_product_mutants']:
 p=Path(row['path']);assert pin(p)=={k:row[k]for k in ('bytes','sha256')};text=p.read_text();assert row['diagnostic']in text and 'AssertionError: V21_FAULT_STAGE_WITNESS'not in text
assert len(v['strict_new_whole_product_mutants'])==4
assert v['actual_fault_boundary_witnesses']==[(0,False,0,0),(0,True,6,1),(1,False,0,0),(1,True,16,0)] or all((x[2]>0)==x[1]for x in v['actual_fault_boundary_witnesses'])
assert len(v['actual_fault_boundary_witnesses'])==4 and v['original_same_assertion_negative_excluded']
assert not Path('/dev/shm/nssoc-integrity-v21-balanced-map-01').exists()
r=dict(status='PASS_SOURCE_ONLY_V21_MERGED_NATIVE_CONTINUATION',policy=pin(policy),findings=[],method=pin(__file__),detacher=pin(B/'detach_native02.py'),verified_whole_source_bridges=bridge_count,verified_method_pins=len(j['method_pins']),verified_sources=len(j['source_pins']),all_capsule_members_read=345,pytest_recounts=recounts,raw_helper_recount_count=len(v['helper_recounts']),actual_fault_boundary_witnesses=v['actual_fault_boundary_witnesses'],original_negative_invalidated=True,registered_boundary_review='Original01 descriptorQ membership alone did not exclude extra direct payload bypass. Additive02 now requires no original ring content FFQ in every output D support, while allowing pointer/control ancestry through legitimate fault enables. Corresponding descriptor Q/actualFF and flags and no descriptor payload Q availability remain strict. Requires original slot_data labels/FFQ nonempty; actual emitted graph still pending.',lifecycle='Four continuation functions and complete map native tail exact inherited V20 after version substitution; helpers whole-byte version-only. SameCPU6/2GiB/original4ns/max150/ring64. New immutable policy02/controller02/boundary02 preserves all01 sources and complete control capsule. Detached exclusive marker, exactpeer/policy/source gates; no native executed by reviewer.',scope='Finite source and saved functional review only.33 executions32pytestPASS/1historicalFAIL retained; one old assertion-only negative explicitly not semantic evidence.15 unchanged+corrected16th public cases composite, no fullprofile rerun. Actual map, graph boundary, import pin proof and timing pending; no physical/fullPHY closure.')
(B/'native-source-only-peer02.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
