# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib,json,tarfile,io,subprocess
R=Path.cwd();B=Path(__file__).resolve().parent;D=B/'finite-capture01';D.mkdir(exist_ok=False)
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
files={}
for p in sorted(B.rglob('*')):
 if p.is_file() and D not in p.parents and '__pycache__' not in p.parts:
  files['capture/'+str(p.relative_to(B))]=dict(source=str(p),**pin(p))
sources=json.loads((R/'docs/evidence/npu-write-frontier-startup-20261005.json').read_text())['sources']
for n,h in sources.items():
 p=R/n;assert pin(p)==h;files['repo/'+n]=dict(source=str(p),**h)
for n in ['docs/135-npu-write-frontier-trace.md','docs/evidence/npu-write-frontier-startup-20261005.json']:
 p=R/n;files['repo/'+n]=dict(source=str(p),**pin(p))
mp=D/'members.json';mp.write_text(json.dumps(files,indent=2)+'\n')
archive=D/'npu-evq-write-frontier-review-20261005.tar.xz'
with tarfile.open(archive,'w:xz',preset=0) as t:
 for n,h in files.items():
  p=Path(h['source']);assert pin(p)=={k:h[k] for k in ('bytes','sha256')};t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
expected={**files,'members.json':pin(mp)};seen=set()
with tarfile.open(archive,'r:xz') as t:
 for member in t:
  assert member.isfile() and member.name not in seen and member.name in expected
  with t.extractfile(member) as f:
   digest=hashlib.sha256();size=0
   while data:=f.read(1024**2):digest.update(data);size+=len(data)
  assert dict(bytes=size,sha256=digest.hexdigest())=={k:expected[member.name][k] for k in ('bytes','sha256')};seen.add(member.name)
assert seen==set(expected)
for h in files.values():assert pin(h['source'])=={k:h[k] for k in ('bytes','sha256')}
review=json.loads((B/'evq37187157260/root-review02.json').read_text())
validation=dict(status='PASS_FINITE_NPU_CAPTURE_REVIEW_AND_NEW_DIAGNOSTIC_PREFLIGHT',source_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),archive=dict(path=str(archive),**pin(archive)),members_full_readback=len(seen),manifest=pin(mp),method=pin(__file__),historical_review=pin(B/'evq37187157260/root-review02.json'),source_peer=pin(B/'write-source-only-peer-rx.json'),focused_tests=115,docs_tests=179,reviews=review['reviews'],new_cloud_result_claimed=False,physical_acceptance=False,scope='Immutable original114+candidate114rawmembers/zipGitHubdigests and additive callback diagnosis; no priorreceipt rewritten. Actual original28PASS,candidate24FAIL; first observedcandidateX1569426. Expandedwriteboundary preflightonly. Sparse newboot result excluded.')
p=D/'npu-evq-write-frontier-validation-20261005.json';p.write_text(json.dumps(validation,indent=2)+'\n');print(json.dumps(validation['archive']));print('members',len(seen))
