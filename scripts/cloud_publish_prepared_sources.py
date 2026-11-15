# SPDX-License-Identifier: Apache-2.0
"""Publish authenticated replay output as a new immutable evidence release."""
import os,subprocess,json,hashlib,zipfile,tarfile,traceback
from pathlib import Path
REPO='Melihakbulut221/nssoc';P='repos/'+REPO+'/'
OUT=Path('prepared-source-publication');OUT.mkdir();D=OUT/'derived';D.mkdir()
SOURCE='589540e861dbd006d98f1de7622c0079ebd921ad';TAG='prepared-sources-20261115-43716663208'
def api(p):return json.loads(subprocess.check_output(['gh','api',P+p]))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=dict(status='RUNNING',accepted=False,full_phy_accepted=False)
try:
 assert os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 run=api('actions/runs/43716663208');assert run['head_sha']==SOURCE and run['conclusion']=='success' and run['run_attempt']==1
 m=api('actions/artifacts/14162773969');digest='19e58df2882a35c686342d2f1938ff061424f2917885c6ddb1adefb3a72ac809'
 assert m['workflow_run']['id']==run['id'] and m['workflow_run']['head_sha']==SOURCE and m['digest']=='sha256:'+digest and not m['expired']
 archive=OUT/'producer.zip'
 with archive.open('xb')as f:subprocess.run(['gh','api',P+'actions/artifacts/14162773969/zip'],stdout=f,check=True,timeout=600)
 assert sha(archive)==digest
 with zipfile.ZipFile(archive)as z:
  raw=z.read('package/prepared-sources-current-20261115.json');assert hashlib.sha256(raw).hexdigest()=='768a29aebfade4d3fde252644dbaa99b2f876aeb4bafc5d816730fb726fec3ff'
  record=json.loads(raw);assert record['replays_byte_identical'] and len(record['files'])==38
  for item in [record['archive'],record['component_notices']]:
   name=item['file'];assert Path(name).name==name
   data=z.read('package/'+name);assert hashlib.sha256(data).hexdigest()==item['sha256']
   if 'bytes'in item:assert len(data)==item['bytes']
   (OUT/name).write_bytes(data)
 tar=OUT/record['archive']['file']
 with tarfile.open(tar)as t:
  members=t.getmembers();assert len(members)==38 and {x.name for x in members}==set(record['files'])
  for x in members:
   assert x.isfile() and not Path(x.name).is_absolute() and '..'not in Path(x.name).parts
   b=t.extractfile(x).read();assert hashlib.sha256(b).hexdigest()==record['files'][x.name]['sha256'] and len(b)==record['files'][x.name]['bytes']
 # New immutable evidence publication, never overwrite historical releases/assets.
 query=subprocess.run(['gh','api',P+'releases/tags/'+TAG],capture_output=True,text=True)
 if query.returncode:
  assert 'HTTP 404'in query.stderr,query.stderr
  subprocess.run(['gh','release','create',TAG,'--repo',REPO,'--target',SOURCE,'--title','Prepared dependency source replay 2026-11-15','--notes','38 independently replayed dependency files. Evidence only; not chip or PHY production acceptance.','--latest=false'],check=True)
 release=api('releases/tags/'+TAG);assert release['target_commitish']==SOURCE
 for item in [record['archive'],record['component_notices']]:
  entries=[x for x in api('releases/'+str(release['id'])+'/assets')if x['name']==item['file']]
  if not entries:subprocess.run(['gh','release','upload',TAG,str(OUT/item['file']),'--repo',REPO],check=True)
  entries=[x for x in api('releases/'+str(release['id'])+'/assets')if x['name']==item['file']];assert len(entries)==1
  asset=entries[0];verify=OUT/('verify-'+item['file'])
  with verify.open('xb')as f:subprocess.run(['gh','api',P+'releases/assets/'+str(asset['id']),'-H','Accept: application/octet-stream'],stdout=f,check=True)
  assert sha(verify)==item['sha256'] and asset['size']==(OUT/item['file']).stat().st_size
  if item is record['archive']:
   record['release_assets']=dict(release_tag=TAG,assets=[dict(name=item['file'],bytes=item['bytes'],sha256=item['sha256'],url=asset['browser_download_url'])])
 (D/'prepared-sources-current-20261115.json').write_text(json.dumps(record,indent=2)+'\n')
 notice=record['component_notices']['file'];(D/notice).write_bytes((OUT/notice).read_bytes())
 r.update(status='PUBLISHED_AND_REDOWNLOADED_HASH_VERIFIED_NOT_YET_CI_INTEGRATED',producer_run=run['id'],producer_head=SOURCE,release=release['html_url'],release_id=release['id'],archive=record['archive'],metadata_sha256=sha(D/'prepared-sources-current-20261115.json'))
except BaseException:r.update(status='FAIL_OR_ERROR',traceback=traceback.format_exc());raise
finally:(D/'result.json').write_text(json.dumps(r,indent=2)+'\n')
