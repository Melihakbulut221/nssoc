"""Recount and archive completed V19 HDL controls without rerunning them."""
from pathlib import Path
import hashlib,json,tarfile,re,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v19-public-controls01')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
status=json.loads((B/'controls-status04.json').read_text());assert status['status']=='COMPLETE_PENDING_INDEPENDENT_CONTROL_RECOUNT' and status['returncode']==0
assert '2 passed' in (B/'controls04.log').read_text()
oldstatus=json.loads((B/'controls-status01.json').read_text());assert oldstatus['status']=='FAILED_CONTROLS_RETAINED' and oldstatus['returncode']!=0
assert '26 passed' in (B/'controls01.log').read_text() and '1 failed' in (B/'controls01.log').read_text()
f=json.loads((B/'source-freeze04.json').read_text());oldf=json.loads((B/'source-freeze03.json').read_text())
for n,v in f['files'].items():assert pin(R/n)==v
for n,v in oldf['files'].items():assert pin(B/'freeze03-sources'/n)==v
changed=[n for n in f['files'] if f['files'][n]!=oldf['files'][n]]
assert changed==['hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v19.py']
peer=json.loads((B/'source-only-peer-rx04.json').read_text());assert peer['status']=='PASS_SOURCE_ONLY_V19_QUARANTINED_SLOTS' and not peer['findings'] and peer['freeze']==pin(B/'source-freeze04.json')
# Only new public prefill was inserted; every old strict assertion/body remains.
oldbench=(B/'freeze03-sources'/changed[0]).read_text();newbench=(R/changed[0]).read_text()
import difflib
ops=difflib.SequenceMatcher(a=oldbench.splitlines(True),b=newbench.splitlines(True),autojunk=False).get_opcodes()
assert [(tag,i2-i1,j2-j1) for tag,i1,i2,j1,j2 in ops if tag!='equal']==[('insert',0,11)]
def xmlcount(p):
 cases=ET.parse(p).findall('.//testcase');return cases,dict(passed=sum(not any(c.find(t)is not None for t in ['failure','error','skipped']) for c in cases),failed=sum(any(c.find(t)is not None for t in ['failure','error']) for c in cases),skipped=sum(c.find('skipped')is not None for c in cases))
oldcases,oldcounts=xmlcount(B/'controls01.xml');assert oldcounts==dict(passed=26,failed=1,skipped=0)
failed=[c for c in oldcases if c.find('failure')is not None];assert len(failed)==1 and failed[0].get('name')=='test_v17_v19_cycle_exact_all_public_outputs[150]'
newcases,newcounts=xmlcount(B/'controls04.xml');assert newcounts==dict(passed=2,failed=0,skipped=0)
assert {c.get('name') for c in newcases}=={'test_v17_v19_cycle_exact_all_public_outputs[150]','test_changed_epoch_case_direct'}
rows=[];epoch_witnesses=[];D4=Path('/dev/shm/nssoc-integrity-v19-public-controls04')
profiles=[(D/'test_actual_wide_rx_full_posit0/capture',dict(passed=14,failed=0,skipped=0),True),(D4/'test_v17_v19_cycle_exact_all_p0/capture',dict(passed=14,failed=0,skipped=0),False),(D4/'test_changed_epoch_case_direct0/capture',dict(passed=1,failed=0,skipped=13),False)]
for directory,expected,historical in profiles:
 p=directory/'results.xml';cases,counts=xmlcount(p);assert counts==expected
 result=json.loads((directory/'result.json').read_text());assert result['status']=='PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX' and result['tests']==expected
 for source,value in result['inputs'].items():
  source=Path(source)
  if historical and source.is_relative_to(R) and str(source.relative_to(R))in oldf['files']:source=B/'freeze03-sources'/source.relative_to(R)
  assert pin(source)==value,str(source)
 for file,value in result['outputs'].items():assert pin(directory/file)==value
 text=(directory/'simulation.log').read_text();matches=re.findall(r'V19_EPOCH_QUARANTINE epochs=(\d+) held_faults=(\d+) extra_fault_steps=(\d+) invalid_differences=(\d+)',text);assert len(matches)==1
 epochs,held,extra,different=map(int,matches[0]);assert epochs==16 and held==16
 if directory.parent.name.startswith('test_v17_'):assert extra==16 and different==16
 epoch_witnesses.append(dict(path=str(directory/'simulation.log'),epochs=epochs,held_faults=held,extra_fault_steps=extra,invalid_differences=different,historical_stimulus=historical))
 rows.append(dict(path=str(p),**pin(p),**expected,historical_stimulus=historical))
# Initial failed miter remains failed; its first thirteen cases alone passed.
p=D/'test_v17_v19_cycle_exact_all_p0/capture/results.xml';_,counts=xmlcount(p);assert counts==dict(passed=13,failed=1,skipped=0)
oldfailure=json.loads((B/'controls01-failure.json').read_text());assert pin(Path(oldfailure['archive']['path']))=={k:oldfailure['archive'][k]for k in ['bytes','sha256']}
literal=[]
for p in sorted(D.glob('*/run.log')):
 if p.parent.is_symlink():continue
 text=p.read_text();ispass='PASS_V19_LITERAL_SEVEN_FIELDS cases4096 updates1024 unknownholds2048 wraps48' in text;isfault='V19_LITERAL_FIELD' in text
 assert ispass or isfault and 'FATAL:' in text
 assert (p.parent/'sim.vvp').stat().st_size>0
 literal.append(dict(path=str(p),**pin(p),positive=ispass,detected_fault=isfault))
assert len(literal)==10 and sum(x['positive'] for x in literal)==1 and sum(x['detected_fault'] for x in literal)==9
miter=[]
for root in sorted(D.glob('test_actual_miter_fault_is_obs*')):
 if root.is_symlink():continue
 p=root/'capture/simulation.log';text=p.read_text();assert any(n in text for n in ['PCIE_CYCLE_MITER_OUTPUT_MISMATCH','PCIE_RING_CONTROL_MISMATCH','PCIE_OCCUPIED_SLOT_MISMATCH','V19_FAULT_QUARANTINE_NOT_ATOMIC'])
 assert (p.parent/'sim/sim.vvp').stat().st_size>0;miter.append(dict(path=str(p),**pin(p)))
assert len(miter)==5
crc=[]
for root in sorted(D.glob('test_actual_wide_rx_fault_reje*')):
 if root.is_symlink():continue
 p=root/'capture/simulation.log';assert 'AssertionError' in p.read_text();crc.append(dict(path=str(p),**pin(p)))
assert len(crc)==8
files={}
for directory,label in [(D,'historical-controls01'),(D4,'corrected-controls04')]:
 for p in directory.rglob('*'):
  if p.is_file() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents if q!=directory):files[label+'/'+str(p.relative_to(directory))]=p
for n in oldf['files']:files['historical-source03/'+n]=B/'freeze03-sources'/n
for n in f['files']:files['source/'+n]=R/n
for name in ['source-freeze01.json','source-freeze02.json','source-freeze03.json','source-only-peer-rx.json','quarantine-relation01.json','negative-stimulus-correction02.json','stimulus-strengthening03.json','freeze01-miter-original.py','freeze02-public-bench-original.py','controls01.log','controls01.xml','controls-status01.json','controls-owner01.json','controls-launch01.log','launch_controls01.py','seal_controls.py','seal_controls02.py','source-freeze04.json','source-only-peer-rx04.json','controls04.log','controls04.xml','controls-status04.json','controls-owner04.json','controls-launch04.log','launch_controls04.py','targeted_controls04.py','detached-controls04-launch.json','controls01-failure.json','controls01-failure-members.json']:
 files['method/'+name]=B/name
# Preserve the independent peer method/log if provided, with no live files.
for p in B.glob('*peer*'):
 if p.is_file():files['method/'+p.name]=p
manifest={n:dict(original_path=str(p),**pin(p)) for n,p in sorted(files.items())};mp=B/'controls-members.json';assert not mp.exists();mp.write_text(json.dumps(manifest,indent=2)+'\n')
a=B/'pcie-integrity-v19-functional-controls-20261005.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=3) as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz') as t:
 assert set(t.getnames())==set(manifest)|{'members.json'}
 for m in t.getmembers():
  expect=pin(mp) if m.name=='members.json' else manifest[m.name];assert m.isfile() and m.size==expect['bytes']
  with t.extractfile(m) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expect['sha256']
for n,p in files.items():assert pin(p)=={k:manifest[n][k] for k in ['bytes','sha256']}
r=dict(status='PASS_SEVEN_SLOT_QUARANTINE_AND_ACTUAL_PUBLIC_FAULT_CONTROLS',source_freeze=pin(B/'source-freeze04.json'),source_peer=pin(B/'source-only-peer-rx04.json'),pytest_executions=29,pytest_passed_executions=28,historical_failed_executions=1,original_selected_tests_covered=27,distinct_original_predicates=26,positive_public_case_executions=29,actual_RTL_mutants=22,literal_cases=4096,literal_unknown_step_holds=2048,literal_wrap_writes=48,excluded_MAX4118_ids=2,pytest_skipped=0,targeted_cocotb_intentionally_unselected=13,historical_failure=oldfailure,source_changes=changed,merged_basis='Initial26PASS retained; failed fullmiter rerun passes all14; changed direct14th case separately passes. Only eleven prefill lines changed, all other eight files and strict assertions identical. Initial failure remains failure.',xml_recount=rows,epoch_quarantine_witnesses=epoch_witnesses,literal_controls=literal,actual_miter_faults=miter,actual_parser_CRC_faults=crc,archive=dict(path=str(a),**pin(a),members=len(manifest)+1),full_readback=True,scope='Exactsevencontentwriter relocation frombestV17. Public+occupied-slot+committed-verdict miter, invalidcontents deliberately maydiffer. New16fault epochs preserve heldoutputs/faultatomicity/restart/flush/reset/abort/stall/wrap/EDS semantics. All actualcoveragewitnesses required. Initial actual failed witness and all source/stimulus corrections preserved; no native timing, exhaustiveformal, MAX4118 or production acceptance.')
p=B/'pcie-integrity-v19-core-controls-validation-20261005.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(archive=r['archive'],validation=pin(p))))
