"""Recount and archive completed V20 HDL controls without rerunning them."""
from pathlib import Path
import hashlib,json,tarfile,re,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v20-public-controls01')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
status=json.loads((B/'controls-status01.json').read_text());assert status['status']=='COMPLETE_PENDING_INDEPENDENT_CONTROL_RECOUNT' and status['returncode']==0
assert '35 passed, 2 deselected' in (B/'controls01.log').read_text()
f=json.loads((B/'source-freeze02.json').read_text())
for n,v in f['files'].items():assert pin(R/n)==v
peer=json.loads((B/'source-only-peer-rx.json').read_text());assert peer['status']=='PASS_SOURCE_ONLY_V20_ELIGIBLE_RETIRE' and not peer['findings'] and peer['freeze']==pin(B/'source-freeze02.json')
pytestcases=ET.parse(B/'controls01.xml').findall('.//testcase');assert len(pytestcases)==35 and all(not any(c.find(t) is not None for t in ['failure','error','skipped']) for c in pytestcases)
rows=[];epoch_witnesses=[]
for name in ['test_actual_wide_rx_full_posit0','test_v17_v20_cycle_exact_all_p0']:
 p=D/name/'capture/results.xml';cases=ET.parse(p).findall('.//testcase');assert len(cases)==14 and all(not any(c.find(t) is not None for t in ['failure','error','skipped']) for c in cases)
 result=json.loads((p.parent/'result.json').read_text());assert result['status']=='PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX' and result['tests']==dict(passed=14,failed=0,skipped=0)
 for source,value in result['inputs'].items():assert pin(source)==value
 for file,value in result['outputs'].items():assert pin(p.parent/file)==value
 text=(p.parent/'simulation.log').read_text();matches=re.findall(r'V19_EPOCH_QUARANTINE epochs=(\d+) held_faults=(\d+) extra_fault_steps=(\d+) invalid_differences=(\d+)',text);assert len(matches)==1
 epochs,held,extra,different=map(int,matches[0]);assert epochs==16 and held>0
 if name.startswith('test_v17_'):assert extra>=16 and different>=16
 epoch_witnesses.append(dict(path=str(p.parent/'simulation.log'),epochs=epochs,held_faults=held,extra_fault_steps=extra,invalid_differences=different))
 rows.append(dict(path=str(p),**pin(p),passed=14))
literal=[]
for p in sorted(D.glob('*/run.log')):
 if p.parent.is_symlink():continue
 text=p.read_text();kind=None
 for name,marker in [('literal4096','PASS_LITERAL_PARALLEL_READ4096'),('selected_XZ59','PASS_BALANCED_4STATE cases=59'),('isolated31','PASS_ISOLATED_SENSITIVITY cases=31'),('exhaustive9216','PASS_V20_EXHAUSTIVE_LOCAL_FOURSTATE cases9216'),('read_control_fault','PARALLEL_READ_MISMATCH'),('payload_Z_fault','BALANCED_4STATE_MISMATCH')]:
  if marker in text:assert kind is None;kind=name
 assert kind is not None
 if kind.endswith('fault'):assert 'FATAL:'in text
 assert (p.parent/'sim.vvp').stat().st_size>0
 literal.append(dict(path=str(p),**pin(p),kind=kind))
from collections import Counter
assert Counter(x['kind']for x in literal)==dict(literal4096=3,selected_XZ59=1,isolated31=1,exhaustive9216=1,read_control_fault=9,payload_Z_fault=1)
miter=[]
for root in sorted(D.glob('test_actual_miter_fault_is_obs*')):
 if root.is_symlink():continue
 p=root/'capture/simulation.log';text=p.read_text();assert any(n in text for n in ['PCIE_CYCLE_MITER_OUTPUT_MISMATCH','PCIE_RING_CONTROL_MISMATCH','PCIE_OCCUPIED_SLOT_MISMATCH','V19_FAULT_QUARANTINE_NOT_ATOMIC'])
 assert (p.parent/'sim/sim.vvp').stat().st_size>0;miter.append(dict(path=str(p),**pin(p)))
assert len(miter)==7
crc=[]
for root in sorted(D.glob('test_actual_wide_rx_fault_reje*')):
 if root.is_symlink():continue
 p=root/'capture/simulation.log';assert 'AssertionError' in p.read_text();crc.append(dict(path=str(p),**pin(p)))
assert len(crc)==8
files={}
for p in D.rglob('*'):
 if p.is_file() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents if q!=D):files['controls/'+str(p.relative_to(D))]=p
for n in f['files']:files['source/'+n]=R/n
# Only closed files; no continuation state or own live stdout in this cutoff.
for p in B.rglob('*'):
 if p.is_file()and not p.is_symlink()and '__pycache__'not in p.parts and p.name not in ['active-checkpoint.json','seal-controls.log','controls-members.json'] and not p.name.startswith(('continuation-status','continuation-owner','detached-native')):
  files['method/'+str(p.relative_to(B))]=p
# Preserve the independent peer method/log if provided, with no live files.
for p in B.glob('*peer*'):
 if p.is_file():files['method/'+p.name]=p
manifest={n:dict(original_path=str(p),**pin(p)) for n,p in sorted(files.items())};mp=B/'controls-members.json';assert not mp.exists();mp.write_text(json.dumps(manifest,indent=2)+'\n')
a=B/'pcie-integrity-v20-functional-controls-20261005.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=3) as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz') as t:
 assert set(t.getnames())==set(manifest)|{'members.json'}
 for m in t.getmembers():
  expect=pin(mp) if m.name=='members.json' else manifest[m.name];assert m.isfile() and m.size==expect['bytes']
  with t.extractfile(m) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expect['sha256']
for n,p in files.items():assert pin(p)=={k:manifest[n][k] for k in ['bytes','sha256']}
r=dict(status='PASS_ELIGIBLE_ROOT_RETIRE_AND_ACTUAL_PUBLIC_FAULT_CONTROLS',source_freeze=pin(B/'source-freeze02.json'),source_peer=pin(B/'source-only-peer-rx.json'),pytest_executions=35,distinct_predicates=34,positive_public_cases=28,actual_RTL_mutants=25,literal_random_cases=12288,literal_fourstate_local_cases=9216,selected_XZ_cases=59,isolated_sensitivity_cases=31,excluded_MAX4118_ids=2,skipped=0,xml_recount=rows,epoch_quarantine_witnesses=epoch_witnesses,literal_controls=literal,actual_miter_faults=miter,actual_parser_CRC_faults=crc,archive=dict(path=str(a),**pin(a),members=len(manifest)+1),full_readback=True,scope='Exactcontrol-onlyeligiblerootretire changefromV19; literalpayloadunchanged. Full14direct+14miteragainstV17 includinginherited16strictfaultepochwitnesses. Knowneligibility+samecountmaskcontrol; initialPythonfaultdispatchbugretainedbeforeHDL. Compositionalfourstateargumentandfiniteactualtests, not whole-DUTformal/native/physicalacceptance.')
p=B/'pcie-integrity-v20-core-controls-validation-20261005.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(archive=r['archive'],validation=pin(p))))
