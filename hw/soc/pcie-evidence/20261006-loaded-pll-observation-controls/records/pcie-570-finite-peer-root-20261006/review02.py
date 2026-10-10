# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded full saved570 source/control archive and publication review."""
import gzip,hashlib,json,lzma,os,resource,tarfile
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));assert os.sched_getaffinity(0)=={2}
R=Path.cwd();O=R/'hw/soc/out';B=O/'pcie-tail115-connected570-controls-finite-20261006';S=Path(__file__).resolve().parent;checked={}
def digest(f):
 h=hashlib.sha256();n=0
 while b:=f.read(1024*1024):h.update(b);n+=len(b)
 return dict(bytes=n,sha256=h.hexdigest())
def pin(p):
 p=Path(p)
 with p.open('rb') as f:v=digest(f)
 checked[str(p)]=v;return v
def check(p,w):
 a=pin(p);assert a=={k:w[k] for k in ('bytes','sha256')},str(p);return a
def read(p,w=None):
 (pin(p) if w is None else check(p,w));return json.loads(Path(p).read_text())
ready=read(B/'ready-finite02.json',dict(bytes=262628,sha256='984a42f5ce014cca9d91e8ccf9375a78dabc19a2f36123b4c6bfeda00218b58c'))
assert ready['active_native_excluded'] and not ready['physics_acceptance'] and not ready['polarity_selected']
for field in ['method_allowlist','compact_evidence','original_evidence','public_receipts']:
 for p,w in ready[field].items():check(p,w)
assert len(ready['method_allowlist'])==82 and len(ready['compact_evidence'])==418 and len(ready['original_evidence'])==410
archive=ready['archives'][0];check(archive['path'],archive);mp=Path(archive['manifest']);members=read(mp,archive['manifest_pin']);seen=set();total=0
with lzma.open(archive['path'],'rb') as payload,tarfile.open(fileobj=payload,mode='r|',bufsize=1024*1024) as t:
 for m in t:
  assert m.isfile() and m.name not in seen and not m.name.startswith('/') and '..' not in Path(m.name).parts
  seen.add(m.name);a=digest(t.extractfile(m));assert a['bytes']==m.size;total+=m.size
  if m.name in members:assert a==members[m.name];check(B/m.name,a)
  else:assert m.name=='members01.json' and a==pin(mp),m.name
 assert not payload.read().strip(b'\0')
assert seen==set(members) and len(seen)==archive['members']==380
T=O/'pcie-tail115-connected570-tuning-20261006';C=O/'pcie-tail115-connected570-save-batches-20261006'
counts={}
for path,count in [(T/'finite-controls05/result.json',11),(T/'storage-controls04/result.json',23),(T/'lifecycle-controls04/result.json',7),(C/'native-control01/result.json',8)]:
 j=read(path);assert j['status'].startswith('PASS') and j['cases']==count and len(j['outcomes'])==count
 assert all(x['passed'] for x in j['outcomes']);counts[str(path)]=count
assert sum(counts.values())==49
positive=j['outcomes'][0];assert positive['rows']==19 and positive['raw_columns']==1134 and positive['commands']==9
assert positive['arguments']==[128]*8+[109] and len(positive['actual_raw_order'])==1134
assert not j['full34ns_tuning_executed'] and not j['physics_acceptance']
old=read(T/'native02/v050-01/result.json');assert old['status']=='ERROR_NATIVE_OR_CAPTURE'
sc=read(O/'pcie-tail115-connected570-source-20261006/source-controls01.json')
assert sc['cases']==12 and all(x['passed'] for x in sc['outcomes'])
release=read(B/'release01.json');assert release['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and release['assets']==ready['assets'] and not release['physical_acceptance']
journal=read(release['transport_journal']['path'],release['transport_journal']);assert len(journal)==5
roundtrips=[];closed=[]
for a in journal:
 assert a['status']=='PASS' and a['returncode']==0 and not a['deadline_triggered'] and not a['stderr_limit_triggered']
 assert a['stdout_capture_complete'] and a['stderr_capture_complete']
 for channel in ['stdout','stderr']:
  rec=a[channel];check(rec['path'],rec)
  with gzip.open(rec['path'],'rb') as f:assert digest(f)==rec['uncompressed']
 owner=read(a['owned_processes'])
 for p in owner['processes']:
  assert p['status']=='REAPED_NO_LIVE_MEMBERS' and p['returncode']==0 and not p['members_at_leader_exit']
  i=p['identity'];stat=Path(f'/proc/{i["pid"]}/stat');assert not stat.exists() or stat.read_text().rsplit(')',1)[1].split()[19]!=i['start_ticks'];closed.append(i)
 if a['kind'] not in ['authenticated','anonymous']:continue
 asset=ready['assets'][0];actual=check(a['retained_local_source']['path'],asset);v=a['observed_download']
 assert {k:v[k] for k in ['bytes','sha256']}==actual and v['matched_local_prefix_bytes']==actual['bytes'] and v['mismatching_chunk'] is None
 assert a['asset']['id']==asset['asset_id'] and a['asset']['digest']=='sha256:'+asset['sha256']
 if a['kind']=='anonymous':
  q=read(a['response']['path'],a['response']);assert q['status']=='COMPLETE_HTTP_STREAM' and q['http_status']==200
 roundtrips.append(dict(kind=a['kind'],asset_id=asset['asset_id'],full_prefix=actual))
assert len(roundtrips)==2 and len(closed)==5
result=dict(status='PASS_INDEPENDENT570_FINITE_SAVED_REVIEW',findings=[],ready=pin(B/'ready-finite02.json'),method=pin(__file__),checked_inputs=checked,methods=82,compact=418,originals=410,archive=archive,members=380,logical_bytes=total,current_controls=counts,current_controls_total=49,composition_controls_separate=12,full34ns_failure_retained=True,positive_native_duration_ps=2,positive_rows=19,full34ns_physics_acceptance=False,roundtrips=roundtrips,closed_transports=closed,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,scope='Complete saved hashes/archive EOF and exact original copies;49 actual saved outcomes separately recounted from12 source composition controls. Five closed publication transports and two complete saved readbacks verified; no fresh network/native, no loaded570 physics acceptance.')
p=S/'result01.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],pins=len(checked),members=380,controls=49,result=pin(p),peak_rss_bytes=result['peak_rss_bytes'])))
