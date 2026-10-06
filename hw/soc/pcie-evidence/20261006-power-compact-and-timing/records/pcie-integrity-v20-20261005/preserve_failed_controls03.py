from pathlib import Path
import hashlib,json,shutil,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v20-public-controls03')
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze03.json').read_text());status=json.loads((B/'controls-status03.json').read_text());assert status['status']=='FAILED_CONTROLS_RETAINED'and status['returncode']==1
cases=ET.parse(B/'controls03.xml').findall('.//testcase');failed=[c for c in cases if c.find('failure')is not None];assert len(cases)==4 and len(failed)==2 and {c.get('name')for c in failed}=={'test_v17_v20_cycle_exact_all_public_outputs[150]','test_appended_stalled_empty_retire_case_direct'}
files={}
for n,v in f['files'].items():
 p=R/n;assert pin(p)==v;q=B/'freeze03-sources'/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);files['source03/'+n]=q
for p in D.rglob('*'):
 if p.is_file()and not p.is_symlink()and not any(q.is_symlink()for q in p.parents if q!=D):files['controls03/'+str(p.relative_to(D))]=p
for n in ['source-freeze02.json','source-freeze03.json','source-only-peer-rx03.json','source_review_rx03.py','source-review-rx03.log','stimulus-correction03.json','controls03.log','controls03.xml','controls-status03.json','controls-owner03.json','launch_controls03.py','detach_controls03.py','targeted_controls03.py','preserve_failed_controls03.py']:
 p=B/n
 if p.exists():files['method/'+n]=p
manifest={n:dict(original_path=str(p),**pin(p))for n,p in sorted(files.items())};mp=B/'controls03-failure-members.json';assert not mp.exists();mp.write_text(json.dumps(manifest,indent=2)+'\n');a=B/'pcie-integrity-v20-misaligned-eds-stimulus-20261005.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=3)as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz')as t:
 assert set(t.getnames())==set(manifest)|{'members.json'}
 for m in t.getmembers():
  v=pin(mp)if m.name=='members.json'else manifest[m.name];assert m.isfile()and m.size==v['bytes']
  with t.extractfile(m)as f:assert hashlib.file_digest(f,'sha256').hexdigest()==v['sha256']
for n,p in files.items():assert pin(p)=={k:manifest[n][k]for k in ['bytes','sha256']}
r=dict(status='RETAINED_V20_ACTUAL_MISALIGNED_EDS_STIMULUS_FAILURE',pytest=dict(passed=2,failed=2,deselected=0),failures=[c.get('name')for c in failed],archive=dict(path=str(a),**pin(a),members=len(manifest)+1),full_readback=True,source_freeze=pin(B/'source-freeze03.json'),scope='New retire_never_empty native mutant detected; exact inverse PASS. Original14 fullmiter cases PASS; appended positive stops on framing halt caused by EDS at byteoffset8 instead of required final DWORD at offset60 of64-byte block. No overflow or mappedrun. Complete four-execution history retained before additive alignment correction; no DUT or strict assertion changes.')
(B/'controls03-failure.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
