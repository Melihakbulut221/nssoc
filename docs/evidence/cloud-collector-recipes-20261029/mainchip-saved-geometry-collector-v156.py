import subprocess,json,hashlib,base64,time
R='repos/Melihakbulut221/nssoc/'
B='codex/complete-open-work'
def api(path,data=None,method=None):
 for attempt in range(4):
  cmd=['gh','api',R+path]
  if data is not None:cmd+=['--method',method or 'POST','--input','-']
  p=subprocess.run(cmd,input=json.dumps(data)if data is not None else None,text=True,capture_output=True)
  if p.returncode==0:return json.loads(p.stdout)if p.stdout.strip()else {}
  if data is not None or method not in(None,'GET')or attempt==3 or not any(x in p.stderr for x in('HTTP 502','HTTP 503','HTTP 504','TLS handshake','connection reset','unexpected EOF','i/o timeout')):raise RuntimeError(path+': '+p.stderr[:2000])
  time.sleep(2+attempt)
def remote(path,ref):
 d=api('contents/'+path+'?ref='+ref)
 if d.get('content'):return base64.b64decode(d['content'])
 return base64.b64decode(api('git/blobs/'+d['sha'])['content'])
def sha(b):return hashlib.sha256(b).hexdigest()
def publish(head,files,msg):
 parent=api('git/commits/'+head);entries=[]
 for p,b in files.items():
  if isinstance(b,str):b=b.encode()
  blob=api('git/blobs',dict(encoding='base64',content=base64.b64encode(b).decode()))
  entries.append(dict(path=p,mode='100644',type='blob',sha=blob['sha']))
 tree=api('git/trees',dict(base_tree=parent['tree']['sha'],tree=entries))
 commit=api('git/commits',dict(message=msg,tree=tree['sha'],parents=[head]))
 assert api('git/ref/heads/'+B)['object']['sha']==head
 api('git/refs/heads/'+B,dict(sha=commit['sha'],force=False),'PATCH')
 return commit['sha']

from concurrent.futures import ThreadPoolExecutor
from pathlib import PurePosixPath
import zlib
RUN=41189662022;SOURCE='f45f2ba30eaf6bcf9ba0980f3388128febdcfbea'
B='codex/mainchip-net459-diode-prune'
PREFIX='docs/evidence/mainchip-saved-repair-audit-terminal-41189662022/'
files={};pins={}
def keep(name,raw):
 assert name not in pins
 pins[name]=dict(bytes=len(raw),sha256=sha(raw));files[PREFIX+name]=raw
def encode(v):return(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def raw_api(path,octet=False):
 for attempt in range(4):
  cmd=['gh','api',R+path]+(['-H','Accept: application/octet-stream']if octet else[])
  r=subprocess.run(cmd,capture_output=True)
  if r.returncode==0:return r.stdout
  error=r.stderr.decode()
  if attempt==3 or not any(t in error for t in('HTTP 502','HTTP 503','HTTP 504','TLS handshake','connection reset','unexpected EOF')):raise RuntimeError(error[:2000])
  time.sleep(2+attempt)
def metadata(path,name):
 raw=raw_api(path);keep(name,raw);return json.loads(raw)
run=metadata('actions/runs/'+str(RUN),'run.json')
assert run['status']=='completed'and run['head_sha']==SOURCE and run['run_attempt']==1 and run['workflow_id']==401215446
jobs=metadata('actions/runs/'+str(RUN)+'/attempts/1/jobs?per_page=100','jobs.json')['jobs']
assert len(jobs)==4 and {j['name']for j in jobs}=={'source-controls','preserve-job-log','saved-repair-audit','preserve-antenna-job-logs'}
logs={}
for listed in jobs:
 job=metadata('actions/jobs/'+str(listed['id']),'jobs/'+str(listed['id'])+'.json')
 assert job['run_id']==RUN and job['head_sha']==SOURCE and job['status']=='completed'
 if job['conclusion']!='skipped':
  raw=raw_api('actions/jobs/'+str(job['id'])+'/logs');assert raw
  keep('logs/'+str(job['id'])+'.log',raw);logs[job['name']]=raw
expected={'context.json','manifest.json','bulk-manifest.json','qualification-manifest.json','controls.json','controls.stdout','controls.stderr','execution.json',
 'audit-controls.json','audit-controls.stdout','audit-controls.stderr','audit-execution.json'}
index={};chunks={};source_records={}
for line in logs['source-controls'].decode().splitlines():
 for marker,isindex in(('BULK_POSTDRT_CONTROL_INDEX ',True),('BULK_POSTDRT_CONTROL_CHUNK ',False)):
  if marker not in line:continue
  t=line.split(marker,1)[1]
  if not t.startswith('{'):continue
  d=json.loads(t);name=d['path'];assert name in expected
  if isindex:assert name not in index;index[name]=d
  else:
   part=chunks.setdefault(name,{})
   assert type(d['index'])is int and d['index']not in part;part[d['index']]=d
assert set(index)==expected
for name,pin in index.items():
 part=chunks.get(name,{})
 assert set(part)==set(range(pin['chunks']))
 raw=b''.join(base64.b64decode(part[i]['base64'],validate=True)for i in range(pin['chunks']))
 assert len(raw)==pin['bytes']and sha(raw)==pin['sha256']
 if pin['present']:keep('source-records/'+name,raw);source_records[name]=raw
keep('source-index.json',encode(index))
context=json.loads(source_records['context.json'])
assert context['source']==SOURCE and context['run_id']==RUN and context['attempt']==1
controls=json.loads(source_records.get('controls.json',b'null'))
audit_controls=json.loads(source_records.get('audit-controls.json',b'null'))
source_pass=next(j['conclusion']for j in jobs if j['name']=='source-controls')=='success'
if source_pass:
 assert set(source_records)==expected
 assert controls['status']=='PASS_BULK_POSTDRT_INTEGRATION_SOURCE_CONTROLS'
 assert controls['counts']==dict(inherited=dict(positive=10,refusal=49,lifecycle=20,rendered_tcl=9),namespace=25,
  projection=3,supervisor=2,shutdown=4,acquisition=4,native_audit=12,bound_cycle=21,publication=3)
 assert json.loads(source_records['execution.json'])['returncode']==0
 assert audit_controls['status']=='PASS_SAVED_REPAIR_AUDIT_SOURCE_CONTROLS'and audit_controls['count']==30 and len(set(audit_controls['passed_cases']))==30
 assert audit_controls['source']==SOURCE and audit_controls['run_id']==RUN and audit_controls['attempt']==1
 assert json.loads(source_records['audit-execution.json'])['returncode']==0
native_index=None;parts={};records={}
for line in logs.get('saved-repair-audit',b'').decode().splitlines():
 for marker,kind in(('BULK_POSTDRT_INDEX ','index'),('BULK_POSTDRT_CHUNK ','chunk')):
  if marker not in line:continue
  t=line.split(marker,1)[1]
  if not t.startswith('{'):continue
  d=json.loads(t)
  if kind=='index':assert native_index is None;native_index=d
  else:
   name=d['name'];group=parts.setdefault(name,{})
   assert type(d['index'])is int and d['index']not in group and d['encoding']=='zlib-base64'
   group[d['index']]=d
if native_index is not None:
 assert set(parts)==set(native_index)
 for name,pin in native_index.items():
  p=PurePosixPath(name);assert not p.is_absolute()and str(p)==name and '..'not in p.parts and '\\'not in name
  assert p.suffix in('.json','.jsonl','.stdout','.stderr','.log','.txt','.tcl','.py','.rpt')or'.json.'in name
  group=parts[name];count=group[0]['chunks']
  assert set(group)==set(range(count))
  assert all(d['chunks']==count and d['bytes']==pin['bytes']and d['sha256']==pin['sha256']for d in group.values())
  raw=zlib.decompress(b''.join(base64.b64decode(group[i]['base64'],validate=True)for i in range(count)))
  assert len(raw)==pin['bytes']and sha(raw)==pin['sha256']
  records[name]=raw
else:assert not parts
keep('native-index.json',encode(native_index or {}))
# Lossless indexed text shards avoid thousands of Git files while preserving
# every available derived record byte-for-byte. Native payloads are never fetched.
locations={};batch=[];size=0;shard=0
def flush():
 global batch,size,shard
 if not batch:return
 path='native-derived-shards/%04d.json'%shard
 raw=encode(dict(schema='lossless-derived-record-shard-v1',records=batch))
 keep(path,raw)
 for item in batch:locations[item['name']]=dict(path=path,member=item['name'],bytes=item['bytes'],sha256=item['sha256'])
 batch=[];size=0;shard+=1
for name,raw in sorted(records.items()):
 if batch and size+len(raw)>750000:flush()
 batch.append(dict(name=name,encoding='base64',base64=base64.b64encode(raw).decode(),bytes=len(raw),sha256=sha(raw)));size+=len(raw)
flush()
assert set(locations)==set(records)
keep('native-record-locations.json',encode(locations))
readable=['result.json','failure.json','native/bulk-postdrt-inner-result.json',
 'native/bulk-postdrt-antenna/saved-audit-result.json','native/bulk-postdrt-antenna/saved-delta-summary.json',
 'native/bulk-postdrt-antenna/saved-native-master-identity.json','native/bulk-postdrt-antenna/saved-delta.json',
 'native/bulk-postdrt-antenna/saved-wire-comparison.json']
for name in readable:
 if name in records:keep('readable-records/'+name,records[name])
for name in records:
 if name.endswith('-failure.json')and name not in readable:keep('readable-records/'+name,records[name])
release=metadata('releases/429844778','release.json')
tag='cloud-results-41189662022-1-mainchip-bulk-postdrt-antenna'
ref=metadata('git/ref/tags/'+tag,'tag-ref.json')
assert release['tag_name']==tag and release['target_commitish']==SOURCE and release['draft']is False and release['prerelease']is True
assert ref['object']['type']=='commit'and ref['object']['sha']==SOURCE
assets={a['name']:a for a in release['assets']};assert len(assets)==len(release['assets'])
capsule=None;output=None
if assets:
 meta={}
 for name in('candidate-outputs.json','candidate-parts.json'):
  a=assets[name];raw=raw_api('releases/assets/'+str(a['id']),True)
  assert a['state']=='uploaded'and len(raw)==a['size']and a['digest']=='sha256:'+sha(raw)
  keep('capsule-metadata/'+name,raw);meta[name]=json.loads(raw)
 output=meta['candidate-outputs.json'];capsule=meta['candidate-parts.json']
 assert output['source']==SOURCE and output['run']==RUN and output['attempt']==1
 assert sum(x['bytes']for x in capsule['parts'])==capsule['archive']['bytes']
 assert {x['name']for x in capsule['parts']}|{'candidate-outputs.json','candidate-parts.json'}==set(assets)
 for row in capsule['parts']:
  a=assets[row['name']]
  assert a['state']=='uploaded'and a['size']==row['bytes']and a['digest']=='sha256:'+row['sha256']
 publication=json.loads(records['native-capsule-publication.json'])
 assert publication['status']=='COMPLETE_PERMANENT_NATIVE_CAPSULE'and publication['files']==output['files']and publication['archive']==capsule['archive']
result=json.loads(records.get('result.json',b'null'));inner=json.loads(records.get('native/bulk-postdrt-inner-result.json',b'null'))
audit=json.loads(records.get('native/bulk-postdrt-antenna/saved-audit-result.json',b'null'))
passed=bool(result and result['status']=='COMPLETE_SAVED_REPAIR_AUDIT_CLOUD_EXPERIMENT')
if passed:
 assert source_pass and run['conclusion']=='success'and capsule is not None
 assert inner['status']=='COMPLETE_SAVED_REPAIR_AUDIT_ENGINE'and inner['saved_repair_audit_complete']is True
 assert audit['status']=='COMPLETE_SAVED_BULK_REPAIR_DIAGNOSIS'and audit['read_only']is True
 assert audit['repair_calls']==audit['route_calls']==0
 assert audit['native_observations_reused_from']==41187928413 and audit['fresh_native_db_reads']==0
 assert audit['original_failed_run']==41172959321 and audit['prior_failure_remains_failure']is True and audit['no_candidate_promoted']is True
 assert all(audit[k]is False for k in('physical_acceptance','timing_accepted','full_phy_accepted'))
 assert result['output_preservation']['complete']is True
if result and output is not None:
 for name,pin in result['output_preservation'].get('complete_large_outputs_in_native_capsule',{}).items():assert output['files'][name]==pin
 for name,pin in result['output_preservation'].get('copied',{}).items():assert native_index['native/'+name]==pin
paths=['scripts/mainchip_saved_geometry_contract.py','scripts/mainchip_saved_repair_audit.py','scripts/mainchip_saved_repair_audit_inner.py','scripts/cloud_mainchip_saved_repair_audit.py',
 'scripts/check_mainchip_saved_repair_audit.py','scripts/mainchip-saved-repair-audit-pins.json','scripts/mainchip-bulk-postdrt-integration-pins.json',
 'scripts/cloud_mainchip_bulk_postdrt_antenna.py','scripts/mainchip_bulk_postdrt_antenna_inner.py','scripts/mainchip_bulk_postdrt_antenna_native.py',
 'scripts/mainchip_bulk_postdrt_antenna.py','scripts/check_mainchip_bulk_postdrt_integration.py','scripts/check_mainchip_bulk_diode_namespace.py',
 'scripts/cloud_mainchip_full_antenna_readback.py','.github/workflows/mainchip-net459-diode-prune.yml']
with ThreadPoolExecutor(max_workers=4)as pool:sources=dict(zip(paths,pool.map(lambda p:remote(p,SOURCE),paths)))
manifest=json.loads(sources['scripts/mainchip-saved-repair-audit-pins.json'])
assert len(manifest['files'])==2172 and manifest['native_repair_authorized']is False and manifest['routing_authorized']is False
for path,raw in sources.items():
 if path in manifest['files']:assert sha(raw)==manifest['files'][path],path
 keep('tested-source/'+path,raw)
commands=[dict(label=x['label'],returncode=x.get('returncode'),seconds=x.get('supervision_record',{}).get('elapsed_seconds',x.get('elapsed_seconds')))for x in(inner or{}).get('commands',[])]
receipt=dict(schema='saved-repair-native-terminal-v1',run=RUN,source=SOURCE,attempt=1,workflow_conclusion=run['conclusion'],
 source_controls_passed=source_pass,source_counts=None if controls is None else controls['counts'],
 observer_source_control_count=None if audit_controls is None else audit_controls['count'],
 raw_job_logs=len(logs),source_records=len(source_records),full_native_records=len(records),lossless_record_shards=shard,
 native_passed=passed,native_status=None if result is None else result['status'],native_commands=commands,
 actual_result=audit,complete_native_capsule_preserved=capsule is not None,
 capsule_archive=None if capsule is None else capsule['archive'],capsule_files=0 if output is None else len(output['files']),
 native_payload_downloaded_locally=False,independent_output_archive_reextraction=False,
 physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,files=pins.copy())
keep('receipt.json',encode(receipt))
head=api('git/ref/heads/'+B)['object']['sha'];assert head==SOURCE
tree=api('git/trees/'+head+'?recursive=1');assert not tree['truncated']and not any(x['path'].startswith(PREFIX)for x in tree['tree'])
commit=publish(head,files,'Preserve complete hosted saved-repair native diagnosis and lossless records [skip ci]')
summary=dict(proof=commit,prefix=PREFIX,files=len(files),bytes=sum(map(len,files.values())),receipt_sha256=sha(files[PREFIX+'receipt.json']),
 run=RUN,source=SOURCE,workflow_conclusion=run['conclusion'],source_controls_passed=source_pass,native_passed=passed,
 raw_job_logs=len(logs),full_native_records=len(records),lossless_record_shards=shard,actual_result=audit,
 capsule_archive=receipt['capsule_archive'],capsule_files=receipt['capsule_files'])
print(json.dumps(dict(summary,phase='published')),flush=True)
with ThreadPoolExecutor(max_workers=4)as pool:
 for path,raw in zip(files,pool.map(lambda p:remote(p,commit),files)):assert raw==files[path],path
print(json.dumps(dict(summary,phase='readback_verified',all_files_verified=True)),flush=True)
