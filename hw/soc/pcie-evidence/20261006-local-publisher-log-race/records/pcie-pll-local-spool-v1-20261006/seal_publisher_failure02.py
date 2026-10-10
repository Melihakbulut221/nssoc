from pathlib import Path
import datetime,hashlib,json,tarfile,io
R=Path.cwd();B=Path(__file__).resolve().parent;D=B/'publisher-failure01';D.mkdir(exist_ok=True)
P=B/'publication01';state=json.loads((P/'publication.json').read_text())
assert state['status']=='ERROR_INDEPENDENT_PUBLICATION_LOCAL_SOURCE_RETAINED' and state['explicit_stop'] is False
assert 'FileNotFoundError' in state['error'] and len(state['assets'])==61 and len(state['attempts'])==62
assert not Path('/proc/350582').exists() and not Path('/proc/369540').exists()
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
failed=P/'attempt-00061-part00061.json';f=json.loads(failed.read_text());part=Path(f['files'][0]['path']);assert pin(part)=={k:f['files'][0][k] for k in ('bytes','sha256')}
paths=[p for p in P.rglob('*')if p.is_file()]+[B/'launch01/publication-supervisor.log',B/'launch01/publication.log',B/'launch01/publication-detached-receipt.json',B/'launch01/publication-command-runtime.json',R/'scripts/publish_pcie_local_spool_v1.py',R/'scripts/durable_pcie_spool_v1.py',R/'scripts/publish_pcie_native_capture_v4.py',R/'scripts/publish_pcie_native_capture_v3.py',R/'scripts/characterize_pcie_clock_trim_stream_v2.py',part,Path(__file__),B/'seal_publisher_failure01.py',D/'sealer-attempt01-note.json']
paths=list(dict.fromkeys(paths));rows=[]
for i,p in enumerate(paths):rows.append(dict(archive_path=f'files/{i:05d}/{p.name}',source_path=str(p),**pin(p)))
manifest=dict(status='IMMUTABLE_CLOSED_PUBLISHER_ONLY_HOST_RACE_FAILURE',files=rows,primary_error=state['error'],outer_explicit_stop=False,child_explicit_stop_secondary_cleanup=True,native_restarted=False,native_untouched=True,complete_public_parts=61,partial_attempt=61,part61_actual_uploaded_asset=614811208,scope='Temporary metadata-file move raced outer worker size scan. Native continues to independent local SSD spool. Failed child stop is owned error cleanup, not user cancellation. No part61 public-readback PASS claimed.')
manifest_bytes=(json.dumps(manifest,indent=2)+'\n').encode();(D/'members.json').write_bytes(manifest_bytes)
archive=D/'pcie-pll-v5-local-publisher-host-race-failure-20261006.tar.xz'
with tarfile.open(archive,'x:xz',preset=3)as tar:
 for row,p in zip(rows,paths):tar.add(p,arcname=row['archive_path'],recursive=False)
 info=tarfile.TarInfo('members.json');info.size=len(manifest_bytes);tar.addfile(info,io.BytesIO(manifest_bytes))
expected={x['archive_path']:x for x in rows};seen=[]
with tarfile.open(archive,'r|xz')as tar:
 for member in tar:
  source=tar.extractfile(member);digest=hashlib.sha256();count=0
  while True:
   block=source.read(1024*1024)
   if not block:break
   count+=len(block);digest.update(block)
  actual=dict(bytes=count,sha256=digest.hexdigest())
  if member.name=='members.json':assert actual==dict(bytes=len(manifest_bytes),sha256=hashlib.sha256(manifest_bytes).hexdigest())
  else:assert actual=={k:expected[member.name][k]for k in ('bytes','sha256')}
  seen.append(member.name)
assert len(seen)==len(rows)+1
for row,p in zip(rows,paths):assert pin(p)=={k:row[k]for k in ('bytes','sha256')}
record=dict(status='PASS_CLOSED_PUBLISHER_FAILURE_FULL_ARCHIVE_READBACK_NATIVE_UNTOUCHED',utc=datetime.datetime.now(datetime.UTC).isoformat(),archive=dict(path=str(archive),**pin(archive)),manifest=dict(path=str(D/'members.json'),**pin(D/'members.json')),members=len(seen),logical_bytes=sum(x['bytes']for x in rows),all_original_closed_files_rechecked=True,failure_classification=manifest['scope'])
(D/'validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
