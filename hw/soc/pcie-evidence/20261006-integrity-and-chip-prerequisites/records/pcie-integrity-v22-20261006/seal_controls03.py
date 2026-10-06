"""Recount and retain both actual V22 campaigns without rerunning hardware."""
from pathlib import Path
import ast,hashlib,io,json,re,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v22-public-controls01');D3=Path('/dev/shm/nssoc-integrity-v22-public-controls03')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def count(p):
 cs=list(ET.parse(p).getroot().iter('testcase'))
 return cs,dict(passed=sum(not any(c.find(k)is not None for k in ('failure','error','skipped'))for c in cs),failed=sum(any(c.find(k)is not None for k in ('failure','error'))for c in cs),skipped=sum(c.find('skipped')is not None for c in cs))
f=json.loads((B/'source-freeze03.json').read_text());old=json.loads((B/'source-freeze02.json').read_text())
for n,v in f['sources'].items():assert pin(R/n)==v,n
for n,v in old['sources'].items():assert pin(B/'pre-execution-source02'/n)==v,n
changed={n for n in f['sources']if f['sources'][n]!=old['sources'][n]}
bench='hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v22.py';miter='sw/tests/test_pcie_gen3_integrity_v22_miter.py'
assert changed=={bench,miter}
def bodies(p):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
a,b=bodies(B/'pre-execution-source02'/bench),bodies(R/bench)
assert {n for n in a if a[n]!=b[n]}=={'cache_fault_write_and_new_epoch_reuse'}
peer=json.loads((B/'source-only-peer-vco03.json').read_text());assert peer['freeze']==pin(B/'source-freeze03.json')and not peer['findings']
pytest=[]
for label,wanted in [('01',dict(passed=26,failed=3,skipped=0)),('03',dict(passed=9,failed=0,skipped=0))]:
 cs,actual=count(B/f'controls{label}.xml');assert actual==wanted
 status=json.loads((B/f'controls-status{label}.json').read_text());assert status['returncode']==(1 if label=='01'else 0)
 assert status['status']==('FAILED_CONTROLS_RETAINED'if label=='01'else'COMPLETE_PENDING_INDEPENDENT_CONTROL_RECOUNT')
 pytest.append(dict(path=str(B/f'controls{label}.xml'),**pin(B/f'controls{label}.xml'),**actual))
helpers=[]
for root,revision in [(D,'02'),(D3,'03')]:
 for p in sorted(root.glob('*/capture/result.json')):
  if p.parent.parent.is_symlink():continue
  result=json.loads(p.read_text());assert result['status']!='RUNNING'
  for name,value in result['inputs'].items():
   original=Path(name)
   if revision=='02'and original.is_relative_to(R)and str(original.relative_to(R))in old['sources']:original=B/'pre-execution-source02'/original.relative_to(R)
   assert pin(original)==value,str(original)
  for name,value in result['outputs'].items():assert pin(p.parent/name)==value,str(p.parent/name)
  cs,c=count(p.parent/'results.xml');helpers.append(dict(path=str(p),**pin(p),revision=revision,status=result['status'],counts=c,selected=[x.get('name')for x in cs if x.find('skipped')is None]))
old_direct=D/'test_actual_wide_rx_full_posit0/capture';assert count(old_direct/'results.xml')[1]==dict(passed=17,failed=0,skipped=0)
old_miter=D/'test_v21_v22_cycle_exact_all_p0/capture';assert count(old_miter/'results.xml')[1]==dict(passed=16,failed=1,skipped=0)
new_direct=D3/'test_changed_cache_epoch_direc0/capture';assert count(new_direct/'results.xml')[1]==dict(passed=1,failed=0,skipped=16)
new_miter=D3/'test_v21_v22_cycle_exact_all_p0/capture';assert count(new_miter/'results.xml')[1]==dict(passed=17,failed=0,skipped=0)
scope=json.loads((new_miter/'miter-scope.json').read_text());assert scope['status']=='PASS_SEVENTEEN_CYCLE_EXACT_PUBLIC_PORT_CASES'and scope['maximum']==150
log=(new_miter/'simulation.log').read_text();match=re.search(r'V22_CACHE_QUARANTINE epochs=(\d+) actual_fault_steps=(\d+) invalid_cache_changes=(\d+)',log);assert match
witness=list(map(int,match.groups()));assert witness==[8,8,8]
mutants=[]
expected=['PCIE_CYCLE_MITER_OUTPUT_MISMATCH','PCIE_RING_CONTROL_MISMATCH','V22_OCCUPIED_SLOT_VERDICT_MISMATCH','V22_OCCUPIED_SLOT_VERDICT_MISMATCH','V22_OCCUPIED_SLOT_VERDICT_MISMATCH','V22_FAULT_QUARANTINE_NOT_ATOMIC']
for i,wanted in enumerate(expected):
 p=D3/f'test_actual_miter_fault_is_obs{i}/capture';s=(p/'simulation.log').read_text()
 assert wanted in s and 'AssertionError: V22_ACTUAL_INVALID_CACHE_WRITE_WITNESS'not in s
 assert json.loads((p/'result.json').read_text())['status']=='FAIL'
 mutants.append(dict(path=str(p/'simulation.log'),**pin(p/'simulation.log'),diagnostic=wanted))
literal=[]
for p in sorted(D.glob('test_actual_cache_body_literal*/run.log')):
 if p.parent.is_symlink():continue
 s=p.read_text();literal.append(dict(path=str(p),**pin(p),positive='PASS_V22_CACHE_LITERAL'in s))
assert len(literal)==7 and sum(x['positive']for x in literal)==1
positive_literal=next(Path(x['path']).read_text()for x in literal if x['positive']);assert 'cases4096'in positive_literal
entries={}
for root,label in [(D,'initial'),(D3,'targeted')]:
 for p in root.rglob('*'):
  if p.is_file()and not p.is_symlink()and not any(q.is_symlink()for q in p.parents if q!=root.parent):entries['raw/'+label+'/'+str(p.relative_to(root))]=p
for n in f['sources']:entries['sources/'+n]=R/n
for p in B.rglob('*'):
 if p.is_file()and not p.is_symlink()and p.suffix not in ('.xz','.gz')and p.name not in ['seal-controls03.log','active-checkpoint.json']:
  entries['evidence/'+str(p.relative_to(B))]=p
manifest={name:dict(original=str(p),**pin(p))for name,p in sorted(entries.items())}
archive=B/'pcie-integrity-v22-controls-20261006.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=1)as tar:
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
receipt=dict(status='PASS_V22_CACHE_QUARANTINE_COMPOSITE_CONTROLS',source_freeze=pin(B/'source-freeze03.json'),source_peer=pin(B/'source-only-peer-vco03.json'),pytest_executions=38,pytest_passed_executions=35,historical_failed_executions=3,pytest_recounts=pytest,public_positive_composite=dict(original_unchanged_cases=16,targeted_corrected_case=1,complete_direct_profile_rerun=False,complete_cycle_miter_cases=17),actual_cache_witness=dict(epochs=witness[0],fault_steps=witness[1],invalid_cache_changes=witness[2]),meaningful_miter_mutants=mutants,literal_controls=literal,helper_recounts=helpers,xml_recount=[dict(path=str(p),**pin(p))for p in [B/'controls01.xml',B/'controls03.xml',old_direct/'results.xml',old_miter/'results.xml',new_direct/'results.xml',new_miter/'results.xml']],archive=dict(path=str(archive),**pin(archive)),members=len(seen),full_member_readback=True,all_original_pins_rechecked=True,MAX4118_profile_excluded=True,physical_acceptance=False,scope='Actual cycle-exact17case miter, eight fault-causes-invalid-cache-write epochs, six real miter mutants; unchanged literal4096/four-state and12 original productfault tests reused. Original26PASS3FAIL remain historical, no masking, no exhaustive formal/timing/fullPHY acceptance.')
(B/'pcie-integrity-v22-controls-validation-20261006.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'],pin(archive),len(seen))
