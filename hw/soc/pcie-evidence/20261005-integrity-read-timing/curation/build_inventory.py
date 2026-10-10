# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite V15/V16/V17 delivery: saved bytes only; never executes captures."""
from pathlib import Path, PurePosixPath
import datetime, gzip, hashlib, json, tarfile
R=Path.cwd();HERE=Path(__file__).resolve().parent
DEST=R/'hw/soc/pcie-evidence/20261005-integrity-read-timing'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def hp(x):return {k:x[k] for k in ('bytes','sha256')}
def read(p):return json.loads(Path(p).read_text())
def stream_pin(f):
 h=hashlib.sha256();n=0
 while chunk:=f.read(1024**2):h.update(chunk);n+=len(chunk)
 return dict(bytes=n,sha256=h.hexdigest())
config=read(HERE/'configuration.json');assert not (HERE/'inventory-final.json').exists()
copies={};sidecars={};sources={};historical={};assets={};capsules=[];transport=[]
def copy_exact(p,dest,want):
 p=Path(p);assert p.is_file() and not p.is_symlink() and pin(p)==hp(want),p
 dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():assert pin(dest)==hp(want),dest
 else:
  with dest.open('xb') as f:f.write(p.read_bytes())
 assert pin(p)==pin(dest)==hp(want)
 rel=str(dest.relative_to(R));row=dict(original_path=str(p.resolve()),**pin(dest))
 assert rel not in copies or copies[rel]==row;copies[rel]=row
 # Preserve source SPDX headers exactly. Generated metadata receives a sidecar,
 # with no edits to the original evidence bytes.
 if b'SPDX-License-Identifier:' not in p.read_bytes()[:4096]:
  sp=dest.with_name(dest.name+'.license');data=b'SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n'
  if sp.exists():assert sp.read_bytes()==data
  else:
   with sp.open('xb') as f:f.write(data)
  sidecars[str(sp.relative_to(R))]=pin(sp)
for version,decl in config['components'].items():
 ready=Path(decl['ready']['path']);assert pin(ready)==hp(decl['ready']);r=read(ready)
 for s in r['source_allowlist']:
  path=R/s['repository_path'];assert pin(path)==hp(s)
  if version=='17':sources[s['repository_path']]=hp(s)
  else:
   target=DEST/'historical'/('v'+version)/s['repository_path'];copy_exact(path,target,s)
   historical[s['repository_path']]=dict(evidence_path=str(target.relative_to(R)),**hp(s))
 for path,h in r['evidence'].items():
  path=Path(path);assert pin(path)==hp(h)
  if path.name.endswith('.tar.xz'):continue # existing public capsule, not a git blob
  copy_exact(path,DEST/'records'/path.relative_to('hw/soc/out'),h)
 copy_exact(ready,DEST/'records'/ready.relative_to('hw/soc/out'),decl['ready'])
 for path,h in decl.get('additional_compact',{}).items():copy_exact(path,DEST/'records'/Path(path).relative_to('hw/soc/out'),h)
 for a in r['assets']:
  assert a['authenticated_roundtrip'] and a['anonymous_roundtrip']
  assert a['name'] not in assets or assets[a['name']]==a;assets[a['name']]=a
 assert pin(ready)==hp(decl['ready'])
for row in config['releases']:
 path=Path(row['path']);assert pin(path)==hp(row);release=read(path)
 assert release['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and not release['explicit_stop']
 for f,a in zip(release['files'],release['assets']):
  assert Path(f['path']).name==a['name']==f['name']
  assert pin(f['path'])==hp(f)==hp(a)==hp(assets[a['name']])
 journal=release['transport_journal'];assert pin(journal['path'])==hp(journal)
 attempts=read(journal['path']);streams=0;owners=[]
 for a in attempts:
  assert a['status']=='PASS' and a['returncode']==0
  for kind in ('stdout','stderr'):
   z=a[kind];assert pin(z['path'])==hp(z)
   with gzip.open(z['path'],'rb') as stream:assert stream_pin(stream)==z['uncompressed']
   assert a[kind+'_capture_complete'];streams+=1
  owner=read(a['owned_processes']);assert owner['cleanup'] is None
  assert all(p['status']=='REAPED_NO_LIVE_MEMBERS' and p['returncode']==0 and not p['members_at_leader_exit'] for p in owner['processes'])
  owners.append(dict(path=a['owned_processes'],**pin(a['owned_processes'])))
  if 'response' in a:assert pin(a['response']['path'])==hp(a['response'])
  if a['kind'] in ('authenticated','anonymous'):
   d=a['observed_download'];assert d['mismatching_chunk'] is None
   assert any(d['bytes']==x['bytes'] and d['sha256']==x['sha256'] for x in release['assets'])
 transport.append(dict(release=row,attempts=len(attempts),gzip_streams_fully_read=streams,closed_owner_receipts=owners))
for c in config['capsules']:
 archive=Path(c['path']);manifest=Path(c['manifest']['path']);assert pin(archive)==hp(c)
 assert pin(manifest)==hp(c['manifest']);members=read(manifest)
 assert 'members.json' not in members;members=dict(members,members_json_placeholder={})
 del members['members_json_placeholder'];members['members.json']=pin(manifest)
 assert hp(assets[archive.name])==pin(archive)
 observed={};expanded=0
 with tarfile.open(archive,'r|xz') as tar:
  for m in tar:
   rel=PurePosixPath(m.name);assert m.isfile() and not rel.is_absolute() and '..' not in rel.parts and m.name not in observed
   assert m.name in members and m.size==members[m.name]['bytes']
   with tar.extractfile(m) as f:h=stream_pin(f)
   assert h==hp(members[m.name]),m.name
   observed[m.name]=h;expanded+=m.size
 assert set(observed)==set(members) and pin(archive)==hp(c)
 capsules.append(dict(archive=dict(path=str(archive),**pin(archive)),manifest=c['manifest'],member_count=len(observed),expanded_bytes=expanded,full_member_readback=True,public_asset=assets[archive.name]))
assert len(sources)==9 and len(historical)==18 and len(capsules)==6 and len(assets)==12
for path,h in sources.items():assert pin(R/path)==h
for path,h in copies.items():assert pin(R/path)==hp(h)
for path,h in sidecars.items():assert pin(R/path)==h
assert sum(h['bytes'] for h in copies.values())<8*1024**2
record=dict(status='READY_FINITE_V15_V16_HISTORY_AND_V17_READ_TIMING_EVIDENCE',utc=datetime.datetime.now(datetime.UTC).isoformat(),method=dict(path=str(Path(__file__)),**pin(__file__)),configuration=dict(path=str(HERE/'configuration.json'),**pin(HERE/'configuration.json')),component_ready=config['components'],active_source_allowlist=sources,historical_source_copies=historical,evidence=copies,license_sidecars=sidecars,evidence_file_count=len(copies),evidence_bytes=sum(h['bytes'] for h in copies.values()),sidecar_count=len(sidecars),capsules=capsules,full_capsule_readback_count=6,full_capsule_member_count=sum(c['member_count'] for c in capsules),public_assets=list(assets.values()),transport_reviews=transport,native_runs_executed=False,controls_rerun=False,public_downloads_repeated=False,original_frozen_sources_edited=False,stable_baseline='V11',V17_adopted=False,physical_acceptance=False,limits='V15 actual std::bad_alloc retained; V16 incomplete compilation and supersession retained. V17 preplacement SS/TT setup remains negative. Two MAX4118 ids not run. No new physical route, extractedRC, fullPHY or production acceptance. Native archive self-stdout empty-at-cut distinction retained explicitly.')
out=HERE/'inventory-final.json';out.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(path=str(out),**pin(out),active_sources=9,historical_sources=18,evidence_files=len(copies),sidecars=len(sidecars),evidence_bytes=record['evidence_bytes'],capsules=6,capsule_members=record['full_capsule_member_count'])))
