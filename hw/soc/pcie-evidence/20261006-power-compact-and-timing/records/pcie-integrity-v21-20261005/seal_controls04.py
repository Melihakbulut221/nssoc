"""Merge exact unchanged controls with a targeted actual stage-witness correction."""
from pathlib import Path
import ast,hashlib,io,json,re,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v21-public-controls01');D2=Path('/dev/shm/nssoc-integrity-v21-public-controls02')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def count(p):
 cs=list(ET.parse(p).getroot().iter('testcase'))
 return cs,dict(passed=sum(not any(c.find(k)is not None for k in ('failure','error','skipped'))for c in cs),failed=sum(any(c.find(k)is not None for k in ('failure','error'))for c in cs),skipped=sum(c.find('skipped')is not None for c in cs))
f=json.loads((B/'source-freeze04.json').read_text());old=json.loads((B/'source-freeze03.json').read_text())
for n,v in f['sources'].items():assert pin(R/n)==v
for n,v in old['sources'].items():assert pin(B/'source-candidate03'/n)==v
changed=[n for n in f['sources']if f['sources'][n]!=old['sources'][n]]
bench='hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v21.py';helper='sw/tests/test_pcie_gen3_continuous_rx_integrity_v21.py'
assert set(changed)=={bench,helper}
assert (B/'source-candidate03'/bench).read_text().replace('raw = wire_dllp(items[0][0]) + bytes(32)','raw = wire_dllp(items[0][0]) + bytes(128)')==(R/bench).read_text()
assert (R/helper).read_text().startswith((B/'source-candidate03'/helper).read_text())
# All earlier selected test bodies and the complete Ports/encoding oracle remain exact.
def bodies(p):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
a,b=bodies(B/'source-candidate03'/bench),bodies(R/bench)
assert {n for n in a if a[n]!=b[n]}=={'descriptor_parser_fault_cancels_queue_after_sampling_edge'}
peer=json.loads((B/'source-only-peer-rx04.json').read_text());assert peer['status']=='PASS_SOURCE_ONLY_V21_REGISTERED_RETIRE' and peer['freeze']==pin(B/'source-freeze04.json') and not peer['findings']
pytest=[]
for label,wanted in [('01',dict(passed=26,failed=1,skipped=0)),('02',dict(passed=6,failed=0,skipped=0))]:
 cs,actual=count(B/f'controls{label}.xml');assert actual==wanted
 status=json.loads((B/f'controls-status{label}.json').read_text());assert status['returncode']==(1 if label=='01' else 0)
 assert status['status']==('FAILED_CONTROLS_RETAINED' if label=='01'else 'COMPLETE_PENDING_INDEPENDENT_CONTROL_RECOUNT')
 pytest.append(dict(path=str(B/f'controls{label}.xml'),**pin(B/f'controls{label}.xml'),**actual))
 if label=='02':assert {c.get('name')for c in cs}=={'test_changed_fault_epoch_positive','test_exact_v17_inverse_and_single_writers',*[f'test_actual_wide_rx_fault_rejected[{x}]'for x in ('fault_descriptor_survives','restart_descriptor_survives','empty_descriptor_blocks','full_descriptor_overwrite')]}
all_helpers=[]
for root,revision in [(D,'03'),(D2,'04')]:
 for p in sorted(root.glob('*/capture/result.json')):
  if p.parent.parent.is_symlink():continue
  result=json.loads(p.read_text());assert result['status']!='RUNNING'
  for name,value in result['inputs'].items():
   original=Path(name)
   if revision=='03' and original.is_relative_to(R) and str(original.relative_to(R))in old['sources']:original=B/'source-candidate03'/original.relative_to(R)
   assert pin(original)==value,str(original)
  for name,value in result['outputs'].items():assert pin(p.parent/name)==value
  cases,counts=count(p.parent/'results.xml')
  all_helpers.append(dict(path=str(p),**pin(p),revision=revision,status=result['status'],selected=[c.get('name')for c in cases if c.find('skipped')is None],counts=counts))
positive=D/'test_actual_wide_rx_full_posit0/capture';cs,counts=count(positive/'results.xml');assert counts==dict(passed=15,failed=1,skipped=0)
assert all(c.find('failure')is None for c in cs[:15]) and cs[-1].get('name')=='descriptor_parser_fault_cancels_queue_after_sampling_edge'
newpositive=next(Path(r['path']).parent for r in all_helpers if r['revision']=='04'and r['status']=='PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX')
assert count(newpositive/'results.xml')[1]==dict(passed=1,failed=0,skipped=15)
log=(newpositive/'simulation.log').read_text();match=re.search(r'V21_PARSER_FAULT_EPOCHS (\[.*\])',log);assert match
witnesses=ast.literal_eval(match[1]);assert len(witnesses)==4
assert [(x[0],x[1])for x in witnesses]==[(0,False),(0,True),(1,False),(1,True)]
assert all((x[2]>0)==x[1] for x in witnesses)
oldlog=(positive/'simulation.log').read_text();match=re.search(r'V21_EMPTY_DRAIN held=(\d+) empty_pops=(\d+) simultaneous=(\d+)',oldlog);assert match
empty=list(map(int,match.groups()));assert min(empty)>=8
match=re.search(r'V21_CONTROL_EPOCHS (\[.*\])',oldlog);assert match
controls=ast.literal_eval(match[1]);assert controls==[(k,c)for k in (0,1)for c in ('reset','flush','start','abort')]
# Every final new full-DUT mutant now fails exactly its semantic diagnostic.
mutants=[]
for r in all_helpers:
 if r['revision']!='04' or r['status']!='FAIL':continue
 p=Path(r['path']).parent;log=(p/'simulation.log').read_text()
 wanted=next((m for m in ('AssertionError: V21_OLD_DESCRIPTOR_OWNERSHIP','AssertionError: V21_EMPTY_DRAIN_FAULT','AssertionError: real finite ring overflow required')if m in log),None)
 assert wanted and 'AssertionError: V21_FAULT_STAGE_WITNESS'not in log
 mutants.append(dict(path=str(p/'simulation.log'),**pin(p/'simulation.log'),diagnostic=wanted))
assert len(mutants)==4
literal=[]
for p in D.glob('*/simulation.log'):
 if p.parent.is_symlink():continue
 s=p.read_text();literal.append(dict(path=str(p),**pin(p),positive='PIPELINE_QUEUE_PASS'in s))
assert len(literal)==10 and sum(x['positive']for x in literal)==1
assert 'PIPELINE_QUEUE_PASS cases=4096 literal=14'in next(Path(x['path']).read_text()for x in literal if x['positive'])
nominal=[]
for r in all_helpers:
 if r['revision']=='03' and r['status']=='PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX':
  p=Path(r['path']).parent/'simulation.log';match=re.search(r'V21_NOMINAL_ONE_CYCLE_COMPARE (\d+)',p.read_text());assert match
  nominal.append(dict(path=str(p),**pin(p),cycles=int(match[1])));assert int(match[1])>=100
assert len(nominal)==2
entries={}
for root,label in [(D,'initial'),(D2,'targeted')]:
 for p in root.rglob('*'):
  if p.is_file() and not p.is_symlink() and not any(q.is_symlink()for q in p.parents if q!=root.parent):entries['raw/'+label+'/'+str(p.relative_to(root))]=p
for n in f['sources']:entries['sources/'+n]=R/n
for p in B.rglob('*'):
 if p.name=='seal-controls04.log':continue
 if p.is_file() and not p.is_symlink() and p.suffix not in ('.xz','.gz') and not p.name.startswith('native-') and 'release'in p.name:continue
 if p.is_file() and not p.is_symlink() and p.suffix not in ('.xz','.gz'):entries['evidence/'+str(p.relative_to(B))]=p
manifest={name:dict(original=str(p),**pin(p))for name,p in sorted(entries.items())}
archive=B/'pcie-integrity-v21-controls-20261006.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=3)as tar:
 for name,p in sorted(entries.items()):tar.add(p,arcname=name,recursive=False)
 raw=(json.dumps(manifest,indent=2)+'\n').encode();info=tarfile.TarInfo('members.json');info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
seen=set()
with tarfile.open(archive,'r:xz')as tar:
 for item in tar:
  assert item.isfile()and item.name not in seen;seen.add(item.name);raw=tar.extractfile(item).read()
  if item.name=='members.json':assert json.loads(raw)==manifest
  else:assert len(raw)==manifest[item.name]['bytes']and hashlib.sha256(raw).hexdigest()==manifest[item.name]['sha256']
assert len(seen)==len(manifest)+1
for name,p in entries.items():assert pin(p)=={k:manifest[name][k]for k in ('bytes','sha256')}
r=dict(status='PASS_REGISTERED_RETIRE_COMPOSITE_PUBLIC_AND_LITERAL_CONTROLS',source_freeze=pin(B/'source-freeze04.json'),source_peer=pin(B/'source-only-peer-rx04.json'),pytest_executions=33,pytest_passed_executions=32,historical_failed_executions=1,original_same_assertion_negative_excluded=True,public_positive_composite=dict(original_unchanged_cases=15,targeted_corrected_case=1,complete_profile_rerun=False),pytest_recounts=pytest,xml_recount=[dict(path=str(p),**pin(p))for p in [B/'controls01.xml',B/'controls02.xml',positive/'results.xml',newpositive/'results.xml']],actual_fault_boundary_witnesses=witnesses,actual_empty_drain_witnesses=empty,actual_control_epoch_witnesses=controls,strict_new_whole_product_mutants=mutants,literal_controls=literal,nominal_one_cycle_relations=nominal,helper_recounts=all_helpers,archive=dict(path=str(archive),**pin(archive)),members=len(seen),full_member_readback=True,all_original_pins_rechecked=True,MAX4118_profile_excluded=True,physical_acceptance=False,scope='Composite immutable15unchanged public cases plus corrected16th and4strict meaningful product negatives. Actual +one-cycle ready1 relation only; no cycle equality under stalls/faults. Historical26PASS1FAIL includes one unqualified negative retained, never relabeled. No timing or fullPHY acceptance.')
(B/'pcie-integrity-v21-controls-validation-20261006.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(archive),len(seen))
