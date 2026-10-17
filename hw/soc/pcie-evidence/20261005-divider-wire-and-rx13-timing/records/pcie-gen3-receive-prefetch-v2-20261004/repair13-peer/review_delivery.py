# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent completed RX13 raw result/archive/publication byte review."""
from pathlib import Path
from collections import Counter
import datetime,gzip,hashlib,json,re,tarfile,xml.etree.ElementTree as ET
B=Path(__file__).resolve().parent;ROOT=B.parents[4];C=B.parent/'repair13-continuation01';D=Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-drt-01');X=Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-detailed-rc-01');P=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-13');E=Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-equivalence');T=Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-physical-replay-01')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def digest(f,limit=None):
 h=hashlib.sha256();n=0
 while chunk:=f.read(min(1024**2,limit-n) if limit is not None else 1024**2):h.update(chunk);n+=len(chunk)
 return dict(bytes=n,sha256=h.hexdigest())
def j(p):return json.loads(Path(p).read_text())
def hashes(d):assert d=={p:pin(p) for p in d}
controller=j(C/'result.json');assert controller['status']=='COMPLETE_RX13_FINITE_ROUTE_RC_REVIEW_PUBLICATION';hashes(controller['inputs'])
for s in controller['stages']:assert s['returncode']==0 and s['source_pins_before']==s['source_pins_after'];hashes(s['source_pins_before'])
owner=j(C/'owned-processes.json');assert owner['status']=='HEALTHY' and len(owner['processes'])==4
for s in owner['processes']:assert s['status']=='REAPED_NO_LIVE_MEMBERS' and not s['members_at_leader_exit'] and s['returncode']==0
for directory in [D,X]:
 r=j(directory/'result.json');assert r['status'].startswith('COMPLETE_') and r['returncode']==0;hashes(r['inputs']);assert r['outputs']=={n:pin(directory/n) for n in r['outputs']}
assert (D/'routed.v').read_bytes()==(P/'repaired.v').read_bytes();assert (D/'router-drc.rpt').stat().st_size==0
assert re.findall(r'Number of violations = (\d+)',(D/'native.log').read_text())[-1]=='0'
log=(X/'native.log').read_text();assert 'NATIVE_NOMINAL_RC_SCREEN_COMPLETE' in log
measured={}
for corner in ['slow','typical','fast']:
 values={}
 for direction in ['max','min']:
  text=log.split(f'EXTRACTED_NOMINAL_RC_{corner}_{direction}\n')[1].split('EXTRACTED_NOMINAL_RC_',1)[0]
  cases=text.split('Startpoint:')[1:];assert len(cases)==6
  for case in cases:
   pair=re.findall(r'(-?\d+\.\d+)\s+slack \((MET|VIOLATED)\)',case);assert len(pair)==1;value=float(pair[0][0]);assert (value<0)==(pair[0][1]=='VIOLATED')
   kind=('recovery' if 'recovery check' in case else 'setup') if direction=='max' else ('removal' if 'removal check' in case else 'hold')
   values.setdefault(kind,[]).append(value)
 assert set(values)=={'setup','hold','recovery','removal'} and all(len(v)==3 for v in values.values());measured[corner]={k:min(v) for k,v in values.items()}
review=j(B/'review.json');validation=j(B/'pcie-rx-repair13-finite-physical-validation-20261005.json');assert measured==review['nominal_rc_cell_corner_slack_ns']==validation['nominal_rc_cell_corner_slack_ns']
assert measured['slow']['setup']==-.441603 and all(v[k]>0 for v in measured.values() for k in ['hold','recovery','removal'])
assert review['electrical_check_report']=='' and review['max_slew_cap_violations_reported']==0
assert validation['qualified_rc'] is False and validation['physical_acceptance'] is False and validation['all_nominal_cell_corner_timing_nonnegative'] is False
assert validation['router_drc_violations']==0 and validation['same_logical_netlist_after_detailed_route']
old=j(B.parent/'repair12-peer/review.json')['nominal_rc_cell_corner_slack_ns'];delta={corner:{kind:round(value-old[corner][kind],6) for kind,value in v.items()} for corner,v in measured.items()};assert delta['slow']['setup']==.080198
port_cases=list(ET.parse(T/'results.xml').iter('testcase'));assert len(port_cases)==6 and all(not any(c.find(k) is not None for k in ['failure','error','skipped']) for c in port_cases)
proof=j(E/'equivalence.json');assert proof['states']==1804 and proof['matched']==proof['targets']==5443 and not proof['mismatches'];faults=j(E/'mutation-controls.json')['controls'];assert len(faults)==10 and all(c['status'].startswith('REJECTED_') for c in faults)
package=j(B/'package.json');a=Path(package['archive']['path']);assert pin(a)=={k:package['archive'][k] for k in ['bytes','sha256']}
with tarfile.open(a,'r:xz') as tar:
 assert len(tar.getmembers())==len(package['members'])==127 and set(tar.getnames())==set(package['members'])
 for member in tar:
  assert member.isfile()
  with tar.extractfile(member) as f:assert digest(f)==package['members'][member.name]
release=j(B/'release.json');assert release['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and len(release['assets'])==3
assetpaths=[a,B/'pcie-rx-repair13-finite-physical-validation-20261005.json',B/'pcie-rx-repair13-continuation-binding-20261005.json'];assets={r['name']:r for r in release['assets']}
for p in assetpaths:
 r=assets[p.name];assert pin(p)=={k:r[k] for k in ['bytes','sha256']} and r['authenticated_roundtrip'] and r['anonymous_roundtrip']
rows=j(B/'release.transport/attempts.json');assert len(rows)==16;assert Counter(r['status'] for r in rows)==dict(PASS=15,TRANSPORT_FAILURE=1)
streamcount=0;failure=[]
for row in rows:
 for kind in ['stderr','stdout']:
  s=row[kind];assert pin(s['path'])=={k:s[k] for k in ['bytes','sha256']}
  with gzip.open(s['path'],'rb') as f:assert digest(f)==s['uncompressed']
  streamcount+=1
 o=j(row['owned_processes']);assert len(o['processes'])==1
 if row['status']=='PASS':
  assert row['returncode']==0 and o['cleanup'] is None
  for child in o['processes']:assert child['status']=='REAPED_NO_LIVE_MEMBERS' and not child['members_at_leader_exit']
 else:
  assert row['kind']=='anonymous' and row['deadline_triggered'] and row['error']=='Bounded transport deadline exceeded'
  assert o['status']=='CANCELLED' and o['processes'][0]['status']=='FAILURE_REAPED';assert not any(g['immediate_after_kill'] for g in o['cleanup']['groups'])
  d=row['observed_download'];assert d['mismatching_chunk'] is None and d['matched_local_prefix_bytes']==d['bytes']
  with a.open('rb') as f:assert digest(f,d['bytes'])=={k:d[k] for k in ['bytes','sha256']}
  failure.append(dict(kind=row['kind'],error=row['error'],observed_prefix_bytes=d['bytes'],observed_prefix_sha256=d['sha256'],owner=pin(row['owned_processes']),actual_cleanup_closed=True))
 if 'response' in row:
  s=row['response'];assert pin(s['path'])=={k:s[k] for k in ['bytes','sha256']}
 if row['status']=='PASS' and row['kind'] in ['authenticated','anonymous']:
  d=row['observed_download'];assert d['mismatching_chunk'] is None and any({k:d[k] for k in ['bytes','sha256']}=={k:a[k] for k in ['bytes','sha256']} for a in assets.values())
for identity in [controller['controller_identity'],*[s['identity'] for s in controller['stages']]]:
 p=Path('/proc')/str(identity['pid'])/'stat'
 if p.exists():
  fields=p.read_text().rsplit(') ',1)[1].split();assert fields[19]!=identity['start_ticks'] or fields[0]=='Z'
result=dict(status='PASS_RX13_COMPLETED_CAPTURE_AND_THREE_IMMUTABLE_PUBLIC_ASSETS_REVIEW',utc=datetime.datetime.now(datetime.UTC).isoformat(),method=pin(__file__),release=pin(B/'release.json'),controller=pin(C/'result.json'),controller_owner=pin(C/'owned-processes.json'),package=pin(B/'package.json'),archive=dict(path=str(a),**pin(a)),archive_full_readback_members=127,public_assets=release['assets'],transport_attempts=16,successful_transport_attempts=15,retained_actual_failed_transport=failure,full_gzip_stream_readbacks=streamcount,source_pins_rehashed=len(controller['inputs']),nominal_cell_corner_slacks_ns=measured,delta_vs_RX12_ns=delta,raw_timing_reports_independently_reparsed=36,saved_proof_states=1804,saved_proof_targets=5443,saved_fault_controls=10,saved_port_cases=6,physical_acceptance=False,qualified_rc=False,scope='Independent finite saved-result and complete127-member readback, actual16transport attempts including one deadline failure with exact33,947,648-byte reconstructed prefix,32gzip streams and terminal owners. No native EDA, proof, controls or network rerun. SS setup improves80.198ps but remains−0.441603ns; SS hold margin21.680ps remains positive. Same default150 standalone receiver and nominalRC reused across cell corners, not full-chip/qualifiedRC/fullPHY/signoff.')
p=B/'publication-review.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(result['status'],pin(p))
