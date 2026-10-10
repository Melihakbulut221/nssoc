"""Merge only unchanged completed controls with additive aligned public witnesses."""
from pathlib import Path
import hashlib,json,tarfile,re,xml.etree.ElementTree as ET
from collections import Counter
R=Path.cwd();B=Path(__file__).resolve().parent
D=Path('/dev/shm/nssoc-integrity-v20-public-controls01');D3=Path('/dev/shm/nssoc-integrity-v20-public-controls03');D4=Path('/dev/shm/nssoc-integrity-v20-public-controls04')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def xmlcount(p):
 cases=ET.parse(p).findall('.//testcase');return cases,dict(passed=sum(not any(c.find(t)is not None for t in ['failure','error','skipped'])for c in cases),failed=sum(any(c.find(t)is not None for t in ['failure','error'])for c in cases),skipped=sum(c.find('skipped')is not None for c in cases))
f=json.loads((B/'source-freeze04.json').read_text());f2=json.loads((B/'source-freeze02.json').read_text());f3=json.loads((B/'source-freeze03.json').read_text())
for n,v in f['files'].items():assert pin(R/n)==v
for old,label in [(f2,'freeze02-sources'),(f3,'freeze03-sources')]:
 for n,v in old['files'].items():assert pin(B/label/n)==v
peer=json.loads((B/'source-only-peer-rx04.json').read_text());assert peer['status']=='PASS_SOURCE_ONLY_V20_ELIGIBLE_RETIRE'and not peer['findings']and peer['freeze']==pin(B/'source-freeze04.json')
for n,v in peer['supporting_methods'].items():assert pin(n)==v
p3=json.loads((B/'source-only-peer-rx03.json').read_text())
for n,v in p3['supporting_methods'].items():assert pin(n)==v
# The whole first14 public case source remains byte-identical; the final fix is
# only two aligned-EDS lines in the appended15th body.
bench='hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v20.py';assert (R/bench).read_bytes().startswith((B/'freeze02-sources'/bench).read_bytes())
old='    raw = wire_dllp(packet) + bytes(16 * RING) + bytes.fromhex("1f809000")\n'
new='    raw = wire_dllp(packet) + bytes(16 * RING)\n    raw += bytes((60 - len(raw)) % 64) + bytes.fromhex("1f809000")\n'
assert (B/'freeze03-sources'/bench).read_text().replace(old,new)==(R/bench).read_text()
assert [n for n in f['files']if f['files'][n]!=f3['files'][n]]==[bench]
pytest_counts={};cases_by={}
for campaign,counts,expected in [('01',dict(passed=34,failed=1,skipped=0),'FAILED_CONTROLS_RETAINED'),('03',dict(passed=2,failed=2,skipped=0),'FAILED_CONTROLS_RETAINED'),('04',dict(passed=4,failed=0,skipped=0),'COMPLETE_PENDING_INDEPENDENT_CONTROL_RECOUNT')]:
 status=json.loads((B/f'controls-status{campaign}.json').read_text());assert status['status']==expected and status['returncode']==(0 if campaign=='04' else 1)
 cases,actual=xmlcount(B/f'controls{campaign}.xml');assert actual==counts;pytest_counts[campaign]=actual;cases_by[campaign]=cases
assert {c.get('name')for c in cases_by['04']}=={'test_exact_generated_inverse_and_wrapper_bridge','test_actual_miter_fault_is_observed[retire_never_empty]','test_appended_stalled_empty_retire_case_direct','test_appended_stalled_empty_retire_case_miter'}
rows=[];epochs=[];stalled=[]
profiles=[(D/'test_actual_wide_rx_full_posit0/capture',dict(passed=14,failed=0,skipped=0),'02'),(D3/'test_v17_v20_cycle_exact_all_p0/capture',dict(passed=14,failed=1,skipped=0),'03'),(D4/'test_appended_stalled_empty_re0/capture',dict(passed=1,failed=0,skipped=14),'04'),(D4/'test_appended_stalled_empty_re1/capture',dict(passed=1,failed=0,skipped=14),'04')]
for directory,expected,revision in profiles:
 p=directory/'results.xml';cases,counts=xmlcount(p);assert counts==expected
 # Filtered cocotb XML explicitly records14 unselected cases as skipped;
 # these are retained separately from zero skipped pytest predicates.
 result=json.loads((directory/'result.json').read_text())
 if revision!='03':assert result['tests']==expected and result['status']=='PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX'
 else:assert result['status']=='FAIL' and result['commands'][0]['returncode']==2 and 'tests'not in result
 for source,value in result['inputs'].items():
  source=Path(source)
  if revision!='04'and source.is_relative_to(R)and str(source.relative_to(R))in f['files']:source=B/f'freeze{revision}-sources'/source.relative_to(R)
  assert pin(source)==value,str(source)
 for file,value in result['outputs'].items():assert pin(directory/file)==value
 log=(directory/'simulation.log').read_text()
 if revision in ['02','03']:
  matches=re.findall(r'V19_EPOCH_QUARANTINE epochs=(\d+) held_faults=(\d+) extra_fault_steps=(\d+) invalid_differences=(\d+)',log);assert len(matches)==1
  e,h,x,d=map(int,matches[0]);assert e==h==16
  if revision=='03':assert x==d==16
  epochs.append(dict(path=str(directory/'simulation.log'),epochs=e,held_faults=h,extra_fault_steps=x,invalid_differences=d))
  if revision=='03':assert cases[-1].get('name')=='stalled_output_retires_committed_zero_keep_words'and cases[-1].find('failure')is not None and all(c.find('failure')is None for c in cases[:-1])
 else:
  matches=re.findall(r'V20_STALLED_EMPTY_RETIRE held_cycles=(\d+) actual_reference_retires=(\d+) ring=(\d+)',log);assert len(matches)==1
  h,e,ring=map(int,matches[0]);assert ring==64 and h>=32
  if directory.name=='capture'and directory.parent.name.endswith('1'):assert e>=16
  stalled.append(dict(path=str(directory/'simulation.log'),held_cycles=h,actual_reference_retires=e,ring=ring))
 rows.append(dict(path=str(p),**pin(p),helper_counts=expected,source_revision=revision))
literal=[]
for p in sorted(D.glob('*/run.log')):
 if p.parent.is_symlink():continue
 log=p.read_text();kind=None
 for name,marker in [('literal4096','PASS_LITERAL_PARALLEL_READ4096'),('selected_XZ59','PASS_BALANCED_4STATE cases=59'),('isolated31','PASS_ISOLATED_SENSITIVITY cases=31'),('exhaustive9216','PASS_V20_EXHAUSTIVE_LOCAL_FOURSTATE cases9216'),('read_control_fault','PARALLEL_READ_MISMATCH'),('payload_Z_fault','BALANCED_4STATE_MISMATCH')]:
  if marker in log:assert kind is None;kind=name
 assert kind is not None
 if kind.endswith('fault'):assert 'FATAL:'in log
 assert (p.parent/'sim.vvp').stat().st_size>0;literal.append(dict(path=str(p),**pin(p),kind=kind))
assert Counter(x['kind']for x in literal)==dict(literal4096=3,selected_XZ59=1,isolated31=1,exhaustive9216=1,read_control_fault=9,payload_Z_fault=1)
miter=[];old_undetected=[]
for root in sorted(D.glob('test_actual_miter_fault_is_obs*')):
 if root.is_symlink():continue
 p=root/'capture/simulation.log';log=p.read_text()
 if not any(n in log for n in ['PCIE_CYCLE_MITER_OUTPUT_MISMATCH','PCIE_RING_CONTROL_MISMATCH','PCIE_OCCUPIED_SLOT_MISMATCH','V19_FAULT_QUARANTINE_NOT_ATOMIC']):old_undetected.append(str(p));continue
 assert (p.parent/'sim/sim.vvp').stat().st_size>0;miter.append(dict(path=str(p),**pin(p)))
assert len(miter)==6 and len(old_undetected)==1
p=D4/'test_actual_miter_fault_is_obs0/capture/simulation.log';log=p.read_text();assert 'PCIE_RING_CONTROL_MISMATCH'in log and 'FATAL:'in log
assert '48.00ns'in log and 'AssertionError'not in log and 'V20_STALLED_EMPTY_RETIRE'not in log
miter.append(dict(path=str(p),**pin(p),reason='Actual ring pointer divergence at48ns from sole !read_any to0 mutation; aligned identical positive stream PASS withzero-keep retirement witness. Not generic malformedEDS/framinghalt.'))
crc=[]
for root in sorted(D.glob('test_actual_wide_rx_fault_reje*')):
 if root.is_symlink():continue
 p=root/'capture/simulation.log';assert 'AssertionError'in p.read_text();crc.append(dict(path=str(p),**pin(p)))
assert len(crc)==8
files={}
for directory,label in [(D,'historical-controls01'),(D3,'historical-controls03'),(D4,'aligned-controls04')]:
 for p in directory.rglob('*'):
  if p.is_file()and not p.is_symlink()and not any(q.is_symlink()for q in p.parents if q!=directory):files[label+'/'+str(p.relative_to(directory))]=p
for old,label in [(f2,'freeze02-sources'),(f3,'freeze03-sources')]:
 for n in old['files']:files[label+'/'+n]=B/label/n
for n in f['files']:files['source/'+n]=R/n
# Frozen, closed top-level methods and receipts only, no running capture files,
# publication journals, operational checkpoint, or recursive prior archives.
for p in B.iterdir():
 if p.is_file()and p.suffix in ['.py','.json','.log','.xml']and p.name not in ['active-checkpoint.json','seal-controls04.log','controls-members.json']and not p.name.startswith(('native-source-only-peer','continuation-','detached-native','initial-failure-release','controls04-publication','seal-native')):
  files['method/'+p.name]=p
manifest={n:dict(original_path=str(p),**pin(p))for n,p in sorted(files.items())};mp=B/'controls-members.json';assert not mp.exists();mp.write_text(json.dumps(manifest,indent=2)+'\n')
a=B/'pcie-integrity-v20-functional-controls-20261005.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=3)as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz')as t:
 assert set(t.getnames())==set(manifest)|{'members.json'}
 for m in t.getmembers():
  v=pin(mp)if m.name=='members.json'else manifest[m.name];assert m.isfile()and m.size==v['bytes']
  with t.extractfile(m)as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==v['sha256']
for n,p in files.items():assert pin(p)=={k:manifest[n][k]for k in ['bytes','sha256']}
r=dict(status='PASS_ELIGIBLE_ROOT_RETIRE_AND_ACTUAL_PUBLIC_FAULT_CONTROLS',source_freeze=pin(B/'source-freeze04.json'),source_peer=pin(B/'source-only-peer-rx04.json'),pytest_executions=43,pytest_passed_executions=40,historical_failed_executions=3,original_selected_tests_covered=35,distinct_original_predicates=34,positive_public_cases_current_coverage=30,pytest_campaigns=pytest_counts,actual_RTL_mutants=25,literal_random_cases=12288,literal_fourstate_local_cases=9216,selected_XZ_cases=59,isolated_sensitivity_cases=31,excluded_MAX4118_ids=2,pytest_skipped=0,targeted_cocotb_intentionally_unselected=28,xml_recount=rows,epoch_quarantine_witnesses=epochs,stalled_zero_keep_witnesses=stalled,literal_controls=literal,actual_miter_faults=miter,actual_parser_CRC_faults=crc,historical_failures=[json.loads((B/n).read_text())for n in ['controls01-failure.json','controls03-failure.json']],archive=dict(path=str(a),**pin(a),members=len(manifest)+1),full_readback=True,merged_basis='Original34PASS retained. Initial undetectedmutant trulyredetected on final alignedstream. Fullnew15-case campaign had original14PASS+appendedEDSfailure; original14sourceexactunchanged, appended15th now separatelyPASS direct+cyclemiter. Both failurecampaigns retained; no fabricated whole15 rerun.',scope='Same V19 toV20 control-only read_any change; payload/parsers/writers unchanged. Compositional fourstate+finite literal/native controls, not exhaustivewhole-DUTformal/MAX4118/timing/physicalacceptance.')
p=B/'pcie-integrity-v20-core-controls-validation-20261005.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(archive=r['archive'],validation=pin(p))))
