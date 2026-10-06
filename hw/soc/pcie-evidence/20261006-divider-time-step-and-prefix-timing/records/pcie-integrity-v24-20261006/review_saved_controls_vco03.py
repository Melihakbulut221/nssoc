"""Independent archive/XML/helper/log recount; no producer or HDL execution."""
from pathlib import Path
import ast,hashlib,json,re,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;V=B/'pcie-integrity-v24-composite-controls-validation-20261006.json'
D=Path('/dev/shm/nssoc-integrity-v24-full-controls01');T=Path('/dev/shm/nssoc-integrity-v24-diagnostic-controls03')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
def bound(row):
 p=Path(row['path']);assert pin(p)=={k:row[k]for k in ('bytes','sha256')};return p
def census(p):
 cs=list(ET.parse(p).getroot().iter('testcase'));d=dict(passed=0,failed=0,skipped=0)
 for x in cs:
  bad=any(x.find(k)is not None for k in ('failure','error'));skip=x.find('skipped')is not None;assert not(bad and skip)
  d['failed'if bad else 'skipped'if skip else 'passed']+=1
 return cs,d
j=read(V);assert j['status']=='PASS_V24_PREFIX_CONTEXT_COMPOSITE_CONTROLS';arc=bound(j['archive']);seen=set()
with tarfile.open(arc,'r:xz') as t:
 manifest=json.loads(t.extractfile('members.json').read())
 for member in t:
  assert member.isfile() and member.name not in seen;seen.add(member.name);raw=t.extractfile(member).read()
  if member.name!='members.json':assert dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())=={k:manifest[member.name][k]for k in ('bytes','sha256')}
assert len(seen)==j['members']==463 and set(manifest)==seen-{'members.json'}
f2=read(B/'source-freeze02.json');f3=read(B/'source-freeze03.json');miter=R/'sw/tests/test_pcie_gen3_integrity_v24_miter.py'
for n,h in f3['sources'].items():assert pin(R/n)==h
for n,h in f2['product_sources'].items():assert pin(B/'source-before-diagnostic03'/n)==h
assert j['source_freeze']==pin(B/'source-freeze03.json') and j['source_peer']==pin(B/'source-only-peer-vco03.json')
counts=[];passing=set();original=set()
for index,row in enumerate(j['campaigns']):
 cases,count=census(bound(row));assert count=={k:row[k]for k in ('passed','failed','skipped')};assert [c.attrib for c in cases]==row['cases'];counts.append(count)
 for c in cases:
  key=(c.get('classname'),c.get('name'))
  if index==0:original.add(key)
  if not any(c.find(k)is not None for k in ('failure','error','skipped')):passing.add(key)
assert counts==[dict(passed=41,failed=1,skipped=0),dict(passed=2,failed=0,skipped=0)]
assert original==passing and len(passing)==42 and j['pytest_executions']==44 and j['historical_failed_executions']==1
helper_count=0
for row in j['helper_receipts']:
 p=bound(row);h=read(p);assert h.get('status')==row['status']
 for name,value in h['inputs'].items():
  q=Path(name)
  if row['revision']==2 and q==miter:q=B/'source-before-diagnostic03'/q.relative_to(R)
  assert pin(q)==value,name
 for name,value in h['outputs'].items():assert pin(p.parent/name)==value
 if row['counts']is not None:assert census(p.parent/'results.xml')[1]==row['counts'];assert (p.parent/'sim/sim.vvp').is_file()
 else:assert h['returncode']==(0 if h['fault']is None else 1)
 helper_count+=1
for n in ('test_actual_wide_rx_full_posit0','test_v23_v24_cycle_exact_all_p0'):
 p=D/n/'capture';assert census(p/'results.xml')[1]==dict(passed=18,failed=0,skipped=0)
 assert read(p/'result.json')['status']=='PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX'
 for c in census(p/'results.xml')[0]:assert c.find('skipped')is None
full=(D/'test_v23_v24_cycle_exact_all_p0/capture/simulation.log').read_text()
cache=list(map(int,re.search(r'V24_CACHE_QUARANTINE epochs=(\d+) actual_fault_steps=(\d+) invalid_cache_changes=(\d+)',full).groups()));assert cache==[8,8,8]
context=r'V24_CONTEXT_WITNESSES current=(\d+) next=(\d+) shifts=(\d+) promotions=(\d+) changed=(\d+) concurrent=(\d+) modes=(\d+) carry=(\d+)/(\d+)/(\d+)/(\d+) eds=(\d+)'
public=list(map(int,re.search(context,full).groups()));assert public==j['context_public_witness']
# Wrapper cadence does not exercise next-bank promotion; real burst below must do so.
assert public[1]==public[3]==public[4]==public[5]==0 and public[0]>0 and min(public[6:])>0
expected=['PCIE_CYCLE_MITER_OUTPUT_MISMATCH','PCIE_RING_CONTROL_MISMATCH','V24_OCCUPIED_SLOT_VERDICT_MISMATCH','V24_OCCUPIED_SLOT_VERDICT_MISMATCH','V24_OCCUPIED_SLOT_VERDICT_MISMATCH','V24_FAULT_QUARANTINE_NOT_ATOMIC','V24_HEADER_BANK_RELATION current','V24_HEADER_BANK_RELATION current','V24_HEADER_BANK_RELATION current','V24_FRAMER_PROMOTION_RELATION','V24_CARRIED_HEADER_RELATION','V24_CONTEXT_CONSUMED_MODE word=1']
for row,diagnostic in zip(j['meaningful_miter_mutants'],expected):
 p=bound(row);text=p.read_text();assert re.search(r'FATAL: [^\n]+: '+re.escape(diagnostic),text)
 h=read(p.parent/'result.json')
 if row['index']==9:assert h['returncode']==1
 else:assert h['status']=='FAIL' and census(p.parent/'results.xml')[1]==dict(passed=0,failed=1,skipped=17)
 assert 'Cannot convert Logic'not in text
repeat=bound(j['targeted_same_mutant_rejection']);text=repeat.read_text();assert 'V24_CONTEXT_CONSUMED_MODE word=1' in text and 'Time: 50000' in text
assert census(repeat.parent/'results.xml')[1]==dict(passed=0,failed=1,skipped=17)
for name in ('soc_pcie_gen3_framer_rx_integrity_v24.v','soc_pcie_gen3_continuous_rx_integrity_v24.v'):
 assert (D/'test_actual_miter_fault_is_obs11/fault-rtl'/name).read_bytes()==(T/'test_actual_miter_fault_is_obs0/fault-rtl'/name).read_bytes()
for i in range(12):
 p=D/f'test_actual_wide_rx_fault_reje{i}'/'capture';assert census(p/'results.xml')[1]==dict(passed=0,failed=1,skipped=17)
 assert 'AssertionError' in (p/'simulation.log').read_text()
assert 'V24_OBSERVER_OLD_PREDECESSOR' in (D/'test_actual_old_predecessor_ob0/observer-capture/simulation.log').read_text()
burst=D/'test_actual_block_burst_scoreb0/burst';text=(burst/'simulation.log').read_text()
bw=list(map(int,re.search(r'PASS_V24_FRAMER_BURST blocks=(\d+) bytes=(\d+) packets=(\d+) promotions=(\d+) changed=(\d+) concurrent=(\d+) inputstall=(\d+) outputstall=(\d+)',text).groups()));assert bw==j['burst_witness']==[15,786,25,14,13,13,38,6]
bc=list(map(int,re.search(context,text).groups()));assert bc==j['context_burst_witness'] and min(bc)>0
source=(R/'sw/tests/test_pcie_gen3_integrity_v24_block_burst.py').read_text();mutations=ast.literal_eval(next(n.value for n in ast.parse(source).body if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Name)and n.targets[0].id=='CONTEXT_FAULTS'))
nominal=(burst/'soc_pcie_gen3_framer_rx_integrity_v24.v').read_text()
for row in j['context_bank_mutants']:
 p=bound(row);h=read(p);assert h['fault']==row['fault'] and h['returncode']==1
 assert re.search(r'FATAL: [^\n]+: V24_CONTEXT_BANK (current|next)\n', (p.parent/'simulation.log').read_text())
 before,after=mutations[h['fault']];actual=(p.parent/'soc_pcie_gen3_framer_rx_integrity_v24.v').read_text();assert nominal.count(before)==1 and nominal.replace(before,after)==actual
 assert (p.parent/'tb.v').read_bytes()==(burst/'tb.v').read_bytes()
for i in range(5):
 p=D/f'test_actual_finite_matrix_alph{i}'/'run.log';text=p.read_text()
 assert 'V24_ALPHABET vectors=16384 token_matrices=13 carry_columns=4 initial_modes=9 complete_matrices=52' in text
 assert ('V24_PREFIX_RELATION_PASS matrices=140608 comparisons=3796416' in text) if i==0 else bool(re.search(r'FATAL: [^\n]+: V24_PREFIX_RELATION word=[123] ',text))
assert 52**3==140608 and 52**3*9*3==3796416
for i in range(3):
 text=(D/f'test_actual_block_context_pack{i}'/'run.log').read_text()
 assert ('PASS_V24_BLOCK_CONTEXT_PACK vectors=672 positions=16 binary=512 XZ=160 filler=exact' in text)if i==0 else bool(re.search(r'FATAL: [^\n]+: V24_BLOCK_CONTEXT_PACK case=0 position=0',text))
for rev in ('01','03'):
 s=read(B/f'status{rev}.json');assert s['returncode']==(1 if rev=='01' else 0) and s['stop_reason'] is None
 for who in ('controller','pytest'):
  birth=s[who];p=Path('/proc')/str(birth['pid'])/'stat';assert not p.exists()or p.read_text().rsplit(') ',1)[1].split()[19]!=birth['start_ticks']
assert j['MAX4118_excluded'] and not j['physical_acceptance']
out=dict(status='PASS_INDEPENDENT_SAVED_V24_COMPOSITE_FUNCTIONAL_CONTROLS',validation=pin(V),findings=[],method=pin(__file__),archive=j['archive'],all_archive_members_rehashed=463,frozen_sources_rehashed=193,helper_receipts_rehashed=helper_count,campaign_counts=counts,current_distinct_passing_predicates=42,historical_host_failure_retained=1,full_public_profile_counts=[18,18],cache_fault_epochs=cache,public_context_witness=public,burst_witness=bw,burst_context_witness=bc,meaningful_miter_mutants=12,context_bank_mutants=4,context_bank_one_edit_inverses=True,product_mutants=12,matrix_classifications=16384,matrix_comparisons=3796416,matrix_mutants=4,packing_vectors=672,packing_mutants=2,repeat_same_mutant_RTL_byte_identical=True,repeat_native_failure_ps=50000,MAX4118_excluded=True,no_producer_imports_or_native_tests_rerun=True,physical_acceptance=False,scope='All463 saved members, raw XML and every helper input/output rechecked. Original41PASS/1hostFAIL retained; exact same named native fault repeats at50ns and host diagnostic-only fix supplies current42-predicate coverage. Wrapper next/promote context counters are zero under its cadence; independently checked real block burst covers all twelve counters including next/promotion/concurrent. No formal exhaustiveness, mapping/timing/fullPHY or fabrication acceptance.')
(B/'saved-controls-peer-vco03.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'receipt':pin(B/'saved-controls-peer-vco03.json')}))
