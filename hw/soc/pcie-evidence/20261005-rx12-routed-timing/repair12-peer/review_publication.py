# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Rehash completed publication/capture; no native work or network rerun."""
from pathlib import Path
import datetime,gzip,hashlib,json,tarfile
B=Path(__file__).resolve().parent
C=B.parent/'repair12-continuation01'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def digest_stream(f):
 h=hashlib.sha256();n=0
 while chunk:=f.read(1024*1024):h.update(chunk);n+=len(chunk)
 return dict(bytes=n,sha256=h.hexdigest())
def record(p):return json.loads(Path(p).read_text())
r=record(B/'release.json');assert r['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and len(r['assets'])==3
package=record(B/'package.json');a=Path(package['archive']['path']);assert pin(a)=={k:package['archive'][k] for k in ['bytes','sha256']}
with tarfile.open(a,'r:xz') as t:
 assert set(t.getnames())==set(package['members']) and len(t.getmembers())==len(package['members'])
 for m in t.getmembers():
  expected=package['members'][m.name];assert m.isfile() and m.size==expected['bytes']
  with t.extractfile(m) as f:assert digest_stream(f)==expected
sources=[a,B/'pcie-rx-repair12-finite-physical-validation-20261005.json',B/'pcie-rx-repair12-continuation-binding-20261005.json']
for asset,p in zip(r['assets'],sources):
 assert asset['name']==p.name and pin(p)=={k:asset[k] for k in ['bytes','sha256']}
 assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip']
rows=record(B/'release.transport/attempts.json');compressed=0;owners=[]
for row in rows:
 assert row['status']=='PASS' and row['returncode']==0
 for kind in ['stderr','stdout']:
  x=row[kind];assert pin(x['path'])=={k:x[k] for k in ['bytes','sha256']}
  with gzip.open(x['path'],'rb') as f:assert digest_stream(f)==x['uncompressed']
  compressed+=1
 owner=record(row['owned_processes']);assert owner['cleanup'] is None
 for entry in owner['processes']:
  assert entry['status']=='REAPED_NO_LIVE_MEMBERS' and entry['returncode']==0 and not entry['members_at_leader_exit']
 owners.append(dict(path=row['owned_processes'],**pin(row['owned_processes'])))
 if 'response' in row:
  x=row['response'];assert pin(x['path'])=={k:x[k] for k in ['bytes','sha256']}
 if row['kind'] in ['authenticated','anonymous']:
  d=row['observed_download'];assert d['mismatching_chunk'] is None and any(d['bytes']==x['bytes'] and d['sha256']==x['sha256'] for x in r['assets'])
controller=record(C/'result.json');assert controller['status']=='COMPLETE_RX12_FINITE_ROUTE_RC_REVIEW_PUBLICATION'
for x in controller['stages']:assert x['returncode']==0 and x['source_pins_before']==x['source_pins_after']
for n,p in controller['inputs'].items():assert pin(n)==p
owner=record(C/'owned-processes.json');assert all(x['status']=='REAPED_NO_LIVE_MEMBERS' and not x['members_at_leader_exit'] for x in owner['processes'])
validation=record(sources[1]);assert validation['all_nominal_cell_corner_timing_nonnegative'] is False and validation['physical_acceptance'] is False
result=dict(status='PASS_RX12_COMPLETED_CAPTURE_AND_THREE_IMMUTABLE_PUBLIC_ASSETS_REVIEW',utc=datetime.datetime.now(datetime.UTC).isoformat(),method=pin(__file__),release=pin(B/'release.json'),controller=pin(C/'result.json'),controller_owner=pin(C/'owned-processes.json'),package=pin(B/'package.json'),archive=dict(path=str(a),**pin(a)),archive_full_readback_members=len(package['members']),public_assets=r['assets'],transport_attempts=len(rows),full_gzip_stream_readbacks=compressed,transport_owner_pins=owners,source_pins_rehashed=len(controller['inputs']),nominal_cell_corner_slacks_ns=validation['nominal_rc_cell_corner_slack_ns'],physical_acceptance=False,qualified_rc=False,scope='Preserved completed candidate12 proof/ports/zeroDRT/nominalRC finite capsule and actual three-asset authenticated+anonymous publication. All115 archive members,15 saved transport attempts/30 compressed streams and owned terminal receipts rehashed. No proof, native EDA, controls or network rerun; no input deletion. Slow setup remains−0.521801ns; no signoff claim.')
p=B/'publication-review.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
