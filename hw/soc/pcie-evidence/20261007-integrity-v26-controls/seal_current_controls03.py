"""Seal fresh complete V26 controls and retain the actual earlier host failure."""
from pathlib import Path
import ast,collections,hashlib,io,json,lzma,os,re,resource,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v26-full-controls03')
os.sched_setaffinity(0,{6});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
freeze=B/'source-freeze03.json';f=read(freeze)
for p,v in f['sources'].items():assert pin(R/p)==v,p
status=read(B/'status03.json');assert status['status']=='COMPLETE_PENDING_INDEPENDENT_CONTROL_RECOUNT' and status['returncode']==0 and status['stop_reason'] is None
for row in (status['controller'],status['pytest']):
 p=Path('/proc')/str(row['pid'])/'stat';assert not p.exists() or p.read_text().rsplit(') ',1)[1].split()[19]!=row['start_ticks']
cases=list(ET.parse(B/'controls03.xml').getroot().iter('testcase'))
assert len(cases)==45 and len({c.get('name') for c in cases})==45
assert all(c.find('failure') is None and c.find('error') is None and c.find('skipped') is None for c in cases)
assert '45 passed, 1 deselected' in (B/'controls03.log').read_text()
oldcases=list(ET.parse(B/'controls01.xml').getroot().iter('testcase'));assert len(oldcases)==45 and sum(c.find('failure') is not None for c in oldcases)==1
receipts=[];helper=[]
for p in sorted(D.rglob('result.json')):
 if any(x.endswith('current') for x in p.parts):continue
 j=read(p)
 for n,v in j.get('inputs',{}).items():assert pin(n)==v,n
 for n,v in j.get('outputs',{}).items():assert pin(p.parent/n)==v,n
 row=dict(path=str(p),**pin(p));receipts.append(row)
 if 'tests' in j:helper.append(dict(**row,status=j['status'],tests=j['tests']))
assert len(helper)==4
assert len([r for r in receipts if Path(r['path']).parent.name=='capture'])==26
for key in ('test_actual_wide_rx_full_posit0','test_actual_all_public_transac0'):
 j=read(D/key/'capture/result.json');assert j['status']=='PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX' and j['tests']==dict(passed=19,failed=0,skipped=0)
for i in (0,1):
 d=D/f'test_actual_nominal_ready_one_{i}'/'capture';j=read(d/'result.json');assert j['tests']==dict(passed=1,failed=0,skipped=18)
 assert 'V25_NOMINAL_PLUS_ONE_PASS' in (d/'simulation.log').read_text()
witness=read(D/'test_actual_all_public_transac0/capture/v25-command-witnesses.json');assert witness['cache_quarantine_counts']==[8,8,8]
assert min(witness['counts'])>0 and min(witness['epoch_counts'])>0
assert witness['canonical_quarantine_counts'][0]>100 and min(witness['canonical_quarantine_counts'][1:])>=8
leak=(D/'test_actual_wide_rx_fault_reje12/capture/simulation.log').read_text()
assert 'AssertionError: V26_EXACT_REJECTED_PACKET_ESCAPED actual=a35c96e1deb6' in leak
restored=list(D.glob('test_actual_restored_fault_qua*/capture/simulation.log'));assert len(restored)==1
assert 'V26_CANONICAL_OLD_COMMAND_WRITE' in restored[0].read_text()
ct=R/'sw/tests/test_pcie_gen3_integrity_v26_command.py';tree=ast.parse(ct.read_text())
node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FAULTS' for t in n.targets));faults=ast.literal_eval(node.value);assert len(faults)==12
log=(D/'test_actual_command_temporal_r0/simulation.log').read_text()
m=re.search(r'V25_COMMAND_RELATION_PASS comparisons=(\d+) bubbles=(\d+) replace=(\d+) ending=(\d+) epochs=(\d+) previous_verdict=(\d+) duplicate=(\d+) wraps=(\d+) unknown_holds=(\d+) unknown_fault_applies=(\d+)',log);assert m
values=list(map(int,m.groups()));assert values[0]==4102 and values[3:7]==[1,5,4,1] and values[8:]==[10,2] and values[7]>=400
component=dict(zip(('comparisons','bubbles','replacements','ending','epochs','previous_verdict','duplicate','wraps','unknown_holds','unknown_fault_applies'),values));component['actual_faults']=12
negatives=[]
for i,fault in enumerate(faults,1):
 d=D/f'test_actual_command_temporal_r{i}';text=(d/'simulation.log').read_text();assert 'FATAL:' in text and fault[3] in text and 'V25_COMMAND_RELATION_PASS' not in text
 assert (d/'command.vvp').is_file();negatives.append(dict(name=fault[0],diagnostic=fault[3],log=pin(d/'simulation.log'),image=pin(d/'command.vvp')))
assert next(x for x in negatives if x['name']=='reset_apply_guard_removed')['diagnostic']=='V25_COMMAND_UNKNOWN_CONTROL_WRITES'
pending=D/'test_actual_pending_badblock_f0/fault_epochs';text=(pending/'simulation.log').read_text()
assert 'V25_PENDING_FAULTS_PASS badblocks=2 overflow=1 recoveries=3' in text and 'ending=4' in text and 'V25_REAL_LINE_RATE' in text
for p in D.glob('test_actual_accepted_block_tr*/burst/simulation.log'):assert 'PASS_V25_FRAMER_BURST' in p.read_text() and 'V25_REAL_LINE_RATE' in p.read_text()
mutants=dict(public=sum(c.get('name').startswith('test_actual_wide_rx_fault_rejected[') for c in cases),architecture=sum(c.get('name').startswith('test_actual_full_dut_command_fault_rejected[') for c in cases),block=sum(c.get('name').startswith('test_actual_block_contract_fault_rejected[') for c in cases),canonical_observer=sum(c.get('name')=='test_actual_restored_fault_qualification_rejected_by_canonical_witness' for c in cases));assert mutants==dict(public=13,architecture=8,block=2,canonical_observer=1),mutants
paths={}
for top in D.iterdir():
 if not top.is_dir() or top.is_symlink():continue
 for p in top.rglob('*'):
  assert not p.is_symlink(),p
  if p.is_file():paths['native03/'+str(p.relative_to(D))]=p
for name in f['sources']:
 p=R/name
 if p.is_relative_to(B):paths['prior-evidence/'+str(p.relative_to(B))]=p
 elif p.is_relative_to(R) and (p.is_relative_to(R/'scripts') or p.is_relative_to(R/'sw/tests') or p.is_relative_to(R/'hw/soc/rtl') or p.is_relative_to(R/'hw/soc/tb')):paths['sources/'+str(p.relative_to(R))]=p
for name in f['product_sources']:paths['sources/'+name]=R/name
extras=['source-freeze03.json','source-only-peer-root03.json','launch_controls03.py','launch-source-bridges02.json','status03.json','owner03.json','controls03.log','controls03.xml','detached-receipt03.json','launch03.log','source-only-peer-vco01.json','source-bridges02.json']
for n in extras:paths['current-evidence/'+n]=B/n
paths['current-evidence/'+Path(__file__).name]=Path(__file__)
for p in B.glob('additive02-reviewer-attempt*/*'):
 if p.is_file():paths['current-evidence/'+str(p.relative_to(B))]=p
manifest={n:dict(original=str(p.resolve()),**pin(p)) for n,p in sorted(paths.items())};encoded=(json.dumps(manifest,indent=2)+'\n').encode()
mp=B/'current-controls03-members.json';assert not mp.exists();mp.write_bytes(encoded)
archive=B/'pcie-integrity-v26-current-controls03-20261007.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=1) as t:
 for n,p in sorted(paths.items()):t.add(p,arcname=n,recursive=False)
 i=tarfile.TarInfo('members.json');i.size=len(encoded);t.addfile(i,io.BytesIO(encoded))
seen=set()
with lzma.open(archive,'rb') as decoded:
 with tarfile.open(fileobj=decoded,mode='r|',bufsize=1024**2) as t:
  for member in t:
   assert member.isfile() and member.name not in seen
   expected=pin(mp) if member.name=='members.json' else {k:manifest[member.name][k]for k in ('bytes','sha256')}
   with t.extractfile(member) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected['sha256']
   assert member.size==expected['bytes'];seen.add(member.name)
 while tail:=decoded.read(1024**2):assert tail==bytes(len(tail))
assert seen==set(manifest)|{'members.json'}
for n,p in paths.items():assert pin(p)=={k:manifest[n][k]for k in ('bytes','sha256')}
receipts +=[dict(path=str(B/n),**pin(B/n))for n in ('controls01.xml','controls03.xml','status01.json','status03.json','controls01.log','controls03.log')]
result=dict(status='PASS_V26_COMPLETE_45_CURRENT_FUNCTIONAL_PREDICATES',source_freeze=pin(freeze),source_peer=pin(B/'source-only-peer-root03.json'),current_pytest=dict(passed=45,failed=0,skipped=0,deselected_MAX4118=1),historical_pytest=dict(passed=44,failed=1,skipped=0),all_executions=90,all_passed_executions=89,all_retained_failed_executions=1,public_profiles=dict(direct=19,instrumented_transactions=19,nominal_plus_one_cases=2,general_cycle_equivalence=False),component=component,component_negatives=negatives,cache_quarantine_counts=witness['cache_quarantine_counts'],canonical_quarantine_counts=witness['canonical_quarantine_counts'],command_and_epoch_counts=witness,whole_dut_mutants=mutants,pending_faults=dict(badblocks=2,overflow=1,recoveries=3),control_receipts=receipts,helper_receipts=helper,archive=dict(path=str(archive),**pin(archive),members=len(seen)),manifest=pin(mp),method=pin(__file__),historical_failure_archive=read(B/'failed-controls01/validation.json')['archive'],physical_acceptance=False,reviewer='root',external_independent_review=False,scope='Fresh all45 current predicates pass after exact rejected-payload observer correction; all RTL/generator bytes unchanged. Historical44PASS1hostFAIL retained. Full19-case known-control V25 public-cycle relation plus eight actual canonical0-to1/refheld fault writes and fresh-owner byte quarantine; literal10 X/Z holds remain component-only. Explicit ring16/MAX18 stress override, not automatic minimum. OneMAX4118 excluded; original4ns native mapping remains separately gated.')
p=B/'pcie-integrity-v26-current-controls03-validation-20261007.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(archive=result['archive'],validation=pin(p),component=component)))
