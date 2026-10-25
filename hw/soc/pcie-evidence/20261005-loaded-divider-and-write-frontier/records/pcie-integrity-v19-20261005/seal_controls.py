"""Recount and archive completed V19 HDL controls without rerunning them."""
from pathlib import Path
import hashlib,json,tarfile,re,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v19-public-controls01')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
status=json.loads((B/'controls-status01.json').read_text());assert status['status']=='COMPLETE_PENDING_INDEPENDENT_CONTROL_RECOUNT' and status['returncode']==0
assert '27 passed, 2 deselected' in (B/'controls01.log').read_text()
f=json.loads((B/'source-freeze03.json').read_text())
for n,v in f['files'].items():assert pin(R/n)==v
peer=json.loads((B/'source-only-peer-rx.json').read_text());assert peer['status']=='PASS_SOURCE_ONLY_V19_QUARANTINED_SLOTS' and not peer['findings'] and peer['freeze']==pin(B/'source-freeze03.json')
pytestcases=ET.parse(B/'controls01.xml').findall('.//testcase');assert len(pytestcases)==27 and all(not any(c.find(t) is not None for t in ['failure','error','skipped']) for c in pytestcases)
rows=[];epoch_witnesses=[]
for name in ['test_actual_wide_rx_full_posit0','test_v17_v19_cycle_exact_all_p0']:
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
for p in D.rglob('*'):
 if p.is_file() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents if q!=D):files['controls/'+str(p.relative_to(D))]=p
for n in f['files']:files['source/'+n]=R/n
for name in ['source-freeze01.json','source-freeze02.json','source-freeze03.json','source-only-peer-rx.json','quarantine-relation01.json','negative-stimulus-correction02.json','stimulus-strengthening03.json','freeze01-miter-original.py','freeze02-public-bench-original.py','controls01.log','controls01.xml','controls-status01.json','controls-owner01.json','controls-launch01.log','launch_controls01.py','seal_controls.py']:
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
r=dict(status='PASS_SEVEN_SLOT_QUARANTINE_AND_ACTUAL_PUBLIC_FAULT_CONTROLS',source_freeze=pin(B/'source-freeze03.json'),source_peer=pin(B/'source-only-peer-rx.json'),pytest_executions=27,distinct_predicates=26,positive_public_cases=28,actual_RTL_mutants=22,literal_cases=4096,literal_unknown_step_holds=2048,literal_wrap_writes=48,excluded_MAX4118_ids=2,skipped=0,xml_recount=rows,epoch_quarantine_witnesses=epoch_witnesses,literal_controls=literal,actual_miter_faults=miter,actual_parser_CRC_faults=crc,archive=dict(path=str(a),**pin(a),members=len(manifest)+1),full_readback=True,scope='Exactsevencontentwriter relocation frombestV17. Public+occupied-slot+committed-verdict miter, invalidcontents deliberately maydiffer. New16fault epochs preserve heldoutputs/faultatomicity/restart/flush/reset/abort/stall/wrap/EDS semantics. All actualcoveragewitnesses required. Source-only corrections beforeanyHDL preserved; no native timing, exhaustiveformal, MAX4118 or production acceptance.')
p=B/'pcie-integrity-v19-core-controls-validation-20261005.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(archive=r['archive'],validation=pin(p))))
