"""Reverify closed archive and original failure classification; no live capture imports."""
from pathlib import Path
import hashlib,json,tarfile
B=Path(__file__).resolve().parent

def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
v=json.loads((B/'validation.json').read_text());archive=Path(v['archive']['path'])
assert pin(archive)=={k:v['archive'][k]for k in ('bytes','sha256')}
manifest_path=B/'members.json';manifest_bytes=manifest_path.read_bytes();m=json.loads(manifest_bytes)
expected={x['archive_path']:x for x in m['files']};saved={};seen=[]
with tarfile.open(archive,'r|xz')as tar:
 for member in tar:
  assert member.isfile() and member.name not in seen;seen.append(member.name)
  f=tar.extractfile(member);h=hashlib.sha256();count=0;pieces=[]
  capture=member.name=='members.json' or member.name.endswith('.json')
  while True:
   chunk=f.read(1024*1024)
   if not chunk:break
   h.update(chunk);count+=len(chunk)
   if capture:pieces.append(chunk)
  actual=dict(bytes=count,sha256=h.hexdigest())
  if member.name=='members.json':assert b''.join(pieces)==manifest_bytes
  else:
   row=expected[member.name];assert actual=={k:row[k]for k in ('bytes','sha256')}
   assert pin(Path(row['source_path']))==actual
   if capture:saved[row['source_path']]=json.loads(b''.join(pieces))
assert len(seen)==1313==len(expected)+1==v['members']
state_path=next(p for p in saved if p.endswith('/publication01/publication.json'))
state=saved[state_path];assert state['status']=='ERROR_INDEPENDENT_PUBLICATION_LOCAL_SOURCE_RETAINED'
assert state['explicit_stop'] is False and state['error']=="FileNotFoundError(2, 'No such file or directory')"
assert len(state['assets'])==61 and len(state['attempts'])==62
for i,asset in enumerate(state['assets']):
 receipt=saved[asset['receipt']];row=next(x for x in expected.values()if x['source_path']==asset['receipt'])
 assert asset['receipt_pin']=={k:row[k]for k in ('bytes','sha256')}
 assert receipt['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and len(receipt['assets'])==1
 assert receipt['assets'][0]==asset['asset'] and asset['row']['index']==i
 assert asset['asset']['authenticated_roundtrip'] is True and asset['asset']['anonymous_roundtrip'] is True
failed_path=str(Path(state_path).parent/'attempt-00061-part00061.json');failed=saved[failed_path]
assert failed['status']=='FAIL' and failed['explicit_stop'] is True
assert failed['error']=="Cancelled('Explicit publisher stop')"
assert failed['upload_reconciliations']==[{'name':failed['files'][0]['name'],'attempt':1,'status':'RESOLVED_AFTER_UPLOAD','successful_upload_previously_observed':False,'upload':'SUCCESS','asset_id':614811208}]
owner=saved[str(Path(state_path).parent/'attempt-00061-part00061.owner.json')]
assert owner['status']=='CANCELLED' and '0003-metadata-attempt1/stdout.bin' in owner['reason'] and 'No such file or directory' in owner['reason']
assert owner['cleanup']['groups'][0]['term_sent'] is True and owner['cleanup']['groups'][0]['kill_sent'] is True
part=failed['files'][0];row=next(x for x in expected.values()if x['source_path']==part['path'])
assert {k:row[k]for k in ('bytes','sha256')}=={k:part[k]for k in ('bytes','sha256')}
assert part['bytes']==13807516 and part['sha256']=='a7b7bbd3a4e2883ba23920514cc71d6a9f82abc7b961070c2abcacf3f1f5f77a'
record=dict(status='PASS_REVERIFIED_CLOSED_V1_PUBLISHER_FAILURE_ARCHIVE',archive=v['archive'],manifest=dict(path=str(manifest_path),**pin(manifest_path)),validation=pin(B/'validation.json'),members=1313,all_original_closed_paths_rehashed=True,completed_dual_readback_assets=61,failed_part=part,uploaded_asset=614811208,primary_error='Host worker guard FileNotFoundError while V4 moved temporary metadata stdout; outer explicit_stop false.',child_error='Secondary ProcessOwner cleanup sent TERM/KILL after host error. Child receipt explicit_stop true does not establish user stop.',cutoff='At this V1 snapshot, part61 was uploaded but did not complete authenticated+anonymous verification. Later V2 evidence is a separate cutoff.',no_native_or_network_or_test_execution=True,method=pin(Path(__file__)),findings=[])
(B/'reverified-failure-pll01.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
