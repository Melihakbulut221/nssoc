"""Independent archive/XML/control recount; no producer imports or HDL reruns."""
from pathlib import Path
import ast,hashlib,json,tarfile,xml.etree.ElementTree as ET,re
R=Path.cwd();B=Path(__file__).resolve().parent;V=B/'pcie-integrity-v22-controls-validation-20261006.json'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def census(p):
 cs=list(ET.parse(p).getroot().iter('testcase'));return cs,dict(passed=sum(all(c.find(x)is None for x in ['failure','error','skipped'])for c in cs),failed=sum(any(c.find(x)is not None for x in ['failure','error'])for c in cs),skipped=sum(c.find('skipped')is not None for c in cs))
j=json.loads(V.read_text());assert pin(j['archive']['path'])=={k:j['archive'][k]for k in ['bytes','sha256']}
with tarfile.open(j['archive']['path'])as t:
 manifest=json.loads(t.extractfile('members.json').read());seen=set()
 for m in t:
  assert m.isfile()and m.name not in seen;seen.add(m.name);data=t.extractfile(m).read()
  if m.name=='members.json':continue
  v=manifest[m.name];assert dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())=={k:v[k]for k in ['bytes','sha256']}
assert len(seen)==j['members']==374 and set(manifest)==seen-{'members.json'}
f=json.loads((B/'source-freeze03.json').read_text());old=json.loads((B/'source-freeze02.json').read_text())
for p,v in f['sources'].items():assert pin(R/p)==v
for p,v in old['sources'].items():assert pin(B/'pre-execution-source02'/p)==v
counts=[]
for row in j['pytest_recounts']:
 p=Path(row['path']);assert pin(p)=={k:row[k]for k in ['bytes','sha256']};cs,c=census(p);assert c=={k:row[k]for k in ['passed','failed','skipped']};counts.append(c)
assert counts==[dict(passed=26,failed=3,skipped=0),dict(passed=9,failed=0,skipped=0)]
helpers=[]
for row in j['helper_recounts']:
 p=Path(row['path']);assert pin(p)=={k:row[k]for k in ['bytes','sha256']};r=json.loads(p.read_text());assert r['status']==row['status']
 for name,value in r['inputs'].items():
  source=Path(name)
  if row['revision']=='02'and source.is_relative_to(R)and str(source.relative_to(R))in old['sources']:source=B/'pre-execution-source02'/source.relative_to(R)
  assert pin(source)==value
 for name,value in r['outputs'].items():assert pin(p.parent/name)==value
 cs,c=census(p.parent/'results.xml');assert c==row['counts'];assert [x.get('name')for x in cs if x.find('skipped')is None]==row['selected'];helpers.append(dict(path=str(p),counts=c))
D=Path('/dev/shm/nssoc-integrity-v22-public-controls03');miter=D/'test_v21_v22_cycle_exact_all_p0/capture';assert census(miter/'results.xml')[1]==dict(passed=17,failed=0,skipped=0)
s=(miter/'simulation.log').read_text();match=re.search(r'V22_CACHE_QUARANTINE epochs=(\d+) actual_fault_steps=(\d+) invalid_cache_changes=(\d+)',s);assert match and list(map(int,match.groups()))==[8,8,8]
for row in j['meaningful_miter_mutants']:
 p=Path(row['path']);assert pin(p)=={k:row[k]for k in ['bytes','sha256']};s=p.read_text();assert row['diagnostic']in s and 'AssertionError: V22_ACTUAL_INVALID_CACHE_WRITE_WITNESS'not in s;assert (p.parent/'sim/sim.vvp').is_file()
for row in j['literal_controls']:
 p=Path(row['path']);assert pin(p)=={k:row[k]for k in ['bytes','sha256']};s=p.read_text();assert ('PASS_V22_CACHE_LITERAL cases4096'in s)if row['positive']else ('V22_CACHE_LITERAL trial='in s)
assert len(j['literal_controls'])==7 and sum(r['positive']for r in j['literal_controls'])==1
# The reused directfirst16 predicates and all product source binaries are unchanged.
name='hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v22.py';a=ast.parse((B/'pre-execution-source02'/name).read_text());b=ast.parse((R/name).read_text());defs=lambda t:{n.name:ast.dump(n,include_attributes=False)for n in t.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))};da,db=defs(a),defs(b);assert {n for n in da if da[n]!=db[n]}=={'cache_fault_write_and_new_epoch_reuse'}
assert j['public_positive_composite']==dict(original_unchanged_cases=16,targeted_corrected_case=1,complete_direct_profile_rerun=False,complete_cycle_miter_cases=17)
for i in range(12):
 p=Path('/dev/shm/nssoc-integrity-v22-public-controls01')/f'test_actual_wide_rx_fault_reje{i}/capture';assert census(p/'results.xml')[1]==dict(passed=0,failed=1,skipped=16);assert 'AssertionError'in(p/'simulation.log').read_text()and(p/'sim/sim.vvp').is_file()
r=dict(status='PASS_INDEPENDENT_SAVED_V22_COMPOSITE_FUNCTIONAL_CONTROLS',findings=[],validation=dict(path=str(V),**pin(V)),source_freeze=pin(B/'source-freeze03.json'),method=pin(__file__),archive=j['archive'],all_archive_members_rehashed=374,all_helper_inputs_outputs_rehashed=len(helpers),pytest=counts,strict_corrected_full_miter_cases=17,actual_cache_witness=[8,8,8],literal_cases=4096,literal_faults=6,actual_semantic_miter_faults=6,unchanged_product_faults=12,source_body_reuse_checked=True,original_failed_executions_retained=3,MAX4118_still_excluded=True,complete_direct_profile_rerun=False,no_native_or_control_rerun=True,scope='Independent all-member archive readback, source/whole-body reuse, saved XML/log/compiled artifact and helper input/output checks. Actual old26PASS3FAIL and new9PASS remain distinct. No producer imported; no exhaustive formal, native mapping, timing or fullPHY acceptance.')
(B/'saved-controls-peer-vco.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(B/'saved-controls-peer-vco.json'))
