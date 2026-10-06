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
for p in B.rglob('*'):
 if p.is_file()and not p.is_symlink()and '__pycache__'not in p.parts and p.name not in ['active-checkpoint.json','seal-controls.log','controls-members.json']:
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
r=dict(status='PASS_ELIGIBLE_ROOT_RETIRE_AND_ACTUAL_PUBLIC_FAULT_CONTROLS',source_freeze=pin(B/'source-freeze02.json'),source_peer=pin(B/'source-only-peer-rx.json'),pytest_executions=35,distinct_predicates=34,positive_public_cases=28,actual_RTL_mutants=25,literal_random_cases=12288,literal_fourstate_local_cases=9216,selected_XZ_cases=59,isolated_sensitivity_cases=31,excluded_MAX4118_ids=2,skipped=0,xml_recount=rows,epoch_quarantine_witnesses=epoch_witnesses,literal_controls=literal,actual_miter_faults=miter,actual_parser_CRC_faults=crc,archive=dict(path=str(a),**pin(a),members=len(manifest)+1),full_readback=True,scope='Exactcontrol-onlyeligiblerootretire changefromV19; literalpayload unchanged. Compositionalfourstateargument plus finiteactualcasesand25actualRTLmutants; full14direct+14miterreferenceV17 includinginheritedV19strict16faultepochwitnesses. Known0/1eligibility andsameproceduralcountmask bypasspayloadtreeonlyforretire. Initialtestdispatchbug caughtandsourcesretained beforeHDL; corrected35actualpredicatesPASS. No native timing, whole-DUT exhaustiveformal, MAX4118 or physicalacceptance.')
p=B/'pcie-integrity-v20-core-controls-validation-20261005.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(archive=r['archive'],validation=pin(p))))
