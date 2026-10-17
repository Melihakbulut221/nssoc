"""Bind completed V25 immutable release and finite Git allowlist, no network."""
from pathlib import Path
import collections,datetime,gzip,hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
def save(p,r):
 with Path(p).open('x')as f:json.dump(r,f,indent=2);f.write('\n')
package=read(B/'pcie-integrity-v25-finite-package-20261006.json');release=read(B/'publication-release01.json')
assert release['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'and release['publisher_revision']==4 and release['tag']=='evidence-20261006-pcie-closure'
assert len(release['files'])==len(release['assets'])==5 and not release['explicit_stop']
assets={x['name']:x for x in release['assets']}
for row in release['files']:
 h={k:row[k]for k in ('bytes','sha256')};assert pin(row['path'])==h
 asset=assets[row['name']];assert {k:asset[k]for k in h}==h and asset['authenticated_roundtrip']is True and asset['anonymous_roundtrip']is True
birth=read(B/'publication-detached01.json');p=Path('/proc',str(birth['pid']),'stat')
if p.exists():
 fields=p.read_text().rsplit(') ',1)[1].split();assert fields[19]!=str(birth['start_ticks'])or fields[0]=='Z'
journal=release['transport_journal'];assert pin(journal['path'])=={k:journal[k]for k in ('bytes','sha256')}
attempts=read(journal['path']);assert len(attempts)==25
assert collections.Counter((x['kind'],x['status'])for x in attempts)==collections.Counter({('metadata','PASS'):10,('upload','PASS'):5,('authenticated','PASS'):5,('anonymous','PASS'):5})
closed={};readbacks=[]
for a in attempts:
 assert a['returncode']==0 and not a['deadline_triggered'] and a['stdout_capture_complete']and a['stderr_capture_complete']
 for key in ['stdout','stderr']:
  rec=a[key];assert pin(rec['path'])=={k:rec[k]for k in ('bytes','sha256')}
  total=0;digest=hashlib.sha256()
  with gzip.open(rec['path'],'rb')as f:
   while data:=f.read(1024**2):total+=len(data);digest.update(data)
  assert dict(bytes=total,sha256=digest.hexdigest())==rec['uncompressed']
  closed[rec['path']]=pin(rec['path'])
 own=read(a['owned_processes']);assert own['cleanup']is None and own['status']=='HEALTHY'
 for x in own['processes']:
  assert x['status']=='REAPED_NO_LIVE_MEMBERS'and x['returncode']==0 and x['members_at_leader_exit']==[]
  proc=Path('/proc',str(x['identity']['pid']),'stat')
  if proc.exists():assert proc.read_text().rsplit(') ',1)[1].split()[19]!=str(x['identity']['start_ticks'])
 closed[a['owned_processes']]=pin(a['owned_processes'])
 if a['kind']in ('authenticated','anonymous'):
  src=a['retained_local_source'];expected={k:src[k]for k in ('bytes','sha256')};assert pin(src['path'])==expected
  observed=a['observed_download'];assert {k:observed[k]for k in expected}==expected and observed['matched_local_prefix_bytes']==expected['bytes']and observed['mismatching_chunk']is None
  name=Path(src['path']).name;assert a['asset']['id']==assets[name]['asset_id']and a['asset']['size']==expected['bytes']
  readbacks.append(dict(kind=a['kind'],name=name,asset_id=a['asset']['id'],**expected))
  if a['kind']=='anonymous':
   response=a['response'];assert pin(response['path'])=={k:response[k]for k in ('bytes','sha256')}
   response_data=read(response['path']);assert response_data['status']=='COMPLETE_HTTP_STREAM'and response_data['http_status']==200
   closed[response['path']]=pin(response['path'])
for collection in ['source_allowlist','evidence']:
 for p,h in package[collection].items():assert pin(R/p)==h,p
audit=dict(status='PASS_SAVED_V25_FIVE_ASSET_TEN_ROUNDTRIP_TRANSPORT_RECOUNT',release=pin(B/'publication-release01.json'),journal=journal,closed_transport_pins=closed,attempts=25,failed_attempts=0,roundtrips=readbacks,scope='Saved exact source-prefix reconstruction and journal/owner/HTTP/raw capture rehash; no fresh download. Allfiveassets bothauth/anon complete and all25owned children closed.',method=pin(__file__))
save(B/'publication-saved-recount01.json',audit)
evidence=package['evidence'].copy()
for name in ['delivery-supplement-members01.json','pcie-integrity-v25-finite-package-20261006.json','prepare-delivery01.log','detach_publication01.py','publication-once01.json','publication-detached01.json','publication-release01.json','publication01.log','publication-saved-recount01.json','finalize_delivery01.py']:
 p=B/name;evidence[str(p.relative_to(R))]=pin(p)
for p in sorted((B/'publication-release01.transport').rglob('*.json')):
 assert p.stat().st_size<=128*1024;evidence[str(p.relative_to(R))]=pin(p)
for p in evidence:assert 'checkpoint'not in Path(p).name and not Path(p).name.startswith('observation-')
record=dict(status='READY_V25_CURRENT43_NATIVE_TIMING_REJECTED_NOT_ADOPTED',utc=datetime.datetime.now(datetime.UTC).isoformat(),source_freeze=package['source_freeze'],source_allowlist=package['source_allowlist'],controls=package['functional'],archives=package['archives'],archive_total_members=package['archive_total_members'],finite_package=pin(B/'pcie-integrity-v25-finite-package-20261006.json'),functional_validation=package['functional_validation'],native_validation=package['native_validation'],saved_controls_peer=package['saved_controls_peer'],native_saved_peer=package['native_saved_peer'],releases={'publication-release01.json':pin(B/'publication-release01.json')},assets=release['assets'],native=package['native'],evidence=evidence,evidence_original_relative_paths=True,publication_saved_recount=pin(B/'publication-saved-recount01.json'),adopted=False,stable_baseline='V11',physical_acceptance=False,scope=package['scope'])
save(B/'ready-finite.json',record)
print(json.dumps(dict(ready=pin(B/'ready-finite.json'),sources=len(record['source_allowlist']),compact_records=len(evidence),archives=len(record['archives']),members=record['archive_total_members'],assets=[x['asset_id']for x in release['assets']])) )
