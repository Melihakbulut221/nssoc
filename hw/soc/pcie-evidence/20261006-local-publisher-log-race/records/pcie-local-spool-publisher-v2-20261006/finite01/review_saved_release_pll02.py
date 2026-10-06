"""Bind closed finite validation and four actual release roundtrips, saved only."""
from pathlib import Path
import gzip,hashlib,json
F=Path(__file__).resolve().parent;B=F.parent

def pin(p):
 p=Path(p)
 with p.open('rb') as s:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(s,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
prior=F/'saved-finite-peer-pll01.json';assert pin(prior)==dict(bytes=16139,sha256='69713634501a47f3b0cf438f78dade5cb20657dd565b384fa1e3e0b6e8609db3')
p=read(prior);vpath=F/'pcie-local-spool-publisher-v2-controls-validation-20261006.json';v=read(vpath)
assert v['status']=='PASS_FINITE_PUBLISHER_V2_ARCHIVE_FULL_READBACK' and v['archive']==p['archive'] and v['members']==p['members'] and v['full_logical_bytes']==p['logical_bytes']
assert {k:v['manifest'][k] for k in ('bytes','sha256')}==p['manifest']
assert v['freeze']==p['freeze'] and v['current_predicates']==31
rpath=F/'release01.json';r=read(rpath);assert r['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and not r['explicit_stop']
assert r['tag']=='evidence-20261006-pcie-closure' and len(r['files'])==len(r['assets'])==4
jp=Path(r['transport_journal']['path']);assert pin(jp)=={k:r['transport_journal'][k] for k in ('bytes','sha256')}
journal=read(jp);assert len(journal)==20
for row in journal:
 assert row['status']=='PASS' and row['returncode']==0 and not row['deadline_triggered']
 assert row['stdout_capture_complete'] and row['stderr_capture_complete']
 for key in ('stdout','stderr'):
  q=row[key];assert pin(q['path'])=={k:q[k] for k in ('bytes','sha256')}
  with gzip.open(q['path'],'rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
  assert h==q['uncompressed']['sha256']
rows=[]
for f,a in zip(r['files'],r['assets']):
 expected={k:f[k] for k in ('bytes','sha256')};assert pin(f['path'])==expected
 assert f['name']==a['name'] and {k:a[k] for k in expected}==expected and a['authenticated_roundtrip'] and a['anonymous_roundtrip']
 matching=[x for x in journal if x['kind'] in ('authenticated','anonymous') and x['asset']['id']==a['asset_id']]
 assert [x['kind'] for x in matching]==['authenticated','anonymous']
 for x in matching:
  d=x['observed_download'];assert {k:d[k] for k in expected}==expected and d['matched_local_prefix_bytes']==expected['bytes'] and d['mismatching_chunk'] is None
  assert x['retained_local_source']==dict(path=f['path'],**expected)
  assert x['asset']['digest']=='sha256:'+expected['sha256'] and x['asset']['size']==expected['bytes'] and x['asset']['state']=='uploaded'
 rows.append(dict(name=a['name'],asset_id=a['asset_id'],**expected,authenticated_and_anonymous_saved_prefix_byte_match=True))
transport={str(p.relative_to(F)):pin(p) for p in (F/'release01.transport').rglob('*') if p.is_file()}
result=dict(status='PASS_INDEPENDENT_SAVED_PUBLISHER_V2_AND_V1_FAILURE_FINITE_PUBLICATION',findings=[],finite_saved_peer=pin(prior),closed_sealer_validation=pin(vpath),release=pin(rpath),journal=pin(jp),assets=rows,transport_files=transport,method=pin(__file__),scope='Saved-byte and receipt review only; all20 actual transport stages closed with4 authenticated+4 anonymous full matched-prefix hash records and unchanged local source bytes. No network/download/test/native rerun. Live spool/native/V2 publication progress excluded. Old V1 primary host ENOENT and incomplete part61 old cutoff remain unchanged. No PLL completion/physical adoption.')
(F/'saved-release-peer-pll02.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],assets=len(rows),transport_files=len(transport),receipt=pin(F/'saved-release-peer-pll02.json'))))
