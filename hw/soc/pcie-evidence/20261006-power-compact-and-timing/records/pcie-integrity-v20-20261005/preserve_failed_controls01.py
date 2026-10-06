from pathlib import Path
import hashlib,json,shutil,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v20-public-controls01')
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze02.json').read_text());status=json.loads((B/'controls-status01.json').read_text());assert status['status']=='FAILED_CONTROLS_RETAINED'and status['returncode']==1
cases=ET.parse(B/'controls01.xml').findall('.//testcase');failed=[c for c in cases if c.find('failure')is not None];assert len(cases)==35 and len(failed)==1 and failed[0].get('name')=='test_actual_miter_fault_is_observed[retire_never_empty]'
files={}
for n,v in f['files'].items():
 p=R/n;assert pin(p)==v;q=B/'freeze02-sources'/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);files['source02/'+n]=q
for p in D.rglob('*'):
 if p.is_file()and not p.is_symlink()and not any(q.is_symlink()for q in p.parents if q!=D):files['controls01/'+str(p.relative_to(D))]=p
for n in ['source-freeze01.json','source-freeze02.json','source-only-peer-rx.json','source_review_rx.py','source-review-rx.log','negative-dispatch-correction02.json','controls01.log','controls01.xml','controls-status01.json','controls-owner01.json','launch_controls02.py','detach_controls02.py','preserve_failed_controls01.py']:
 p=B/n
 if p.exists():files['method/'+n]=p
manifest={n:dict(original_path=str(p),**pin(p))for n,p in sorted(files.items())};mp=B/'controls01-failure-members.json';assert not mp.exists();mp.write_text(json.dumps(manifest,indent=2)+'\n');a=B/'pcie-integrity-v20-initial-undetected-retire-fault-20261005.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=3)as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz')as t:
 assert set(t.getnames())==set(manifest)|{'members.json'}
 for m in t.getmembers():
  v=pin(mp)if m.name=='members.json'else manifest[m.name];assert m.isfile()and m.size==v['bytes']
  with t.extractfile(m)as f:assert hashlib.file_digest(f,'sha256').hexdigest()==v['sha256']
for n,p in files.items():assert pin(p)=={k:manifest[n][k]for k in ['bytes','sha256']}
r=dict(status='RETAINED_V20_ACTUAL_UNDETECTED_RETIRE_NEVER_EMPTY_MUTANT',pytest=dict(passed=34,failed=1,deselected=2),failure=failed[0].get('name'),archive=dict(path=str(a),**pin(a),members=len(manifest)+1),full_readback=True,source_freeze=pin(B/'source-freeze02.json'),scope='Positive literal/4state/miter14/direct14 allpassed;24actualmutants detected,retire_never_empty notdetectedbyexistingfault-epochcase. No mapping. Complete35executionhistory retainedbeforeminimalnewstalledzero-keepdrainpubliccase correction; noDUTchangeorassertionweakening.')
(B/'controls01-failure.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
