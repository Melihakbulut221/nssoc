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
RUN=41203881385;SOURCE='39496d034c4c1f2c9bcc3a9fe70cb3d82823fb53'
B='codex/cdr-drain-m1-loaded-electrical';PREFIX='docs/evidence/cdr-current-eight-drain-physical-terminal-41203881385/'
files={};pins={}
def enc(value):return(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def keep(name,raw):
 assert name not in pins
 pins[name]=dict(bytes=len(raw),sha256=sha(raw));files[PREFIX+name]=raw
def raw_api(path,octet=False):
 extra=['--allow-escape-sequences']if '--allow-escape-sequences'in subprocess.check_output(['gh','api','--help'],text=True)else[]
 for attempt in range(4):
  r=subprocess.run(['gh','api',*extra,R+path]+(['-H','Accept: application/octet-stream']if octet else[]),capture_output=True)
  if r.returncode==0:return r.stdout
  error=r.stderr.decode()
  if attempt==3 or not any(x in error for x in ('HTTP 502','HTTP 503','HTTP 504','TLS handshake','connection reset','unexpected EOF')):raise RuntimeError(error[:2000])
  time.sleep(2+attempt)
def get(path,name):
 raw=raw_api(path);keep(name,raw);return json.loads(raw)
run=get('actions/runs/'+str(RUN),'run.json')
assert run['status']=='completed'and run['head_sha']==SOURCE and run['run_attempt']==1 and run['workflow_id']==401118236
jobs=get('actions/runs/'+str(RUN)+'/attempts/1/jobs?per_page=100','jobs.json')['jobs']
assert len(jobs)==4 and {j['name']for j in jobs}=={'source-controls','preserve-job-log','physical','preserve-physical-job-logs'}
logs={}
for listed in jobs:
 j=get('actions/jobs/'+str(listed['id']),'jobs/'+str(listed['id'])+'.json')
 assert j['status']=='completed'and j['head_sha']==SOURCE and j['run_id']==RUN
 if j['conclusion']=='skipped':continue
 raw=raw_api('actions/jobs/'+str(j['id'])+'/logs');assert raw
 keep('logs/'+str(j['id'])+'.log',raw);logs[j['name']]=raw
expected={'context.json','controls.json','controls.stdout','controls.stderr','publication-controls.json','publication-controls.stdout','publication-controls.stderr',
 'ownership-manifest.json','ownership-controls.json','ownership-controls.stdout','ownership-controls.stderr',
 'execution-manifest.json','execution-controls.json','execution-controls.stdout','execution-controls.stderr',
 'tail-manifest.json','tail-controls.json','tail-controls.stdout','tail-controls.stderr'}
index={};chunks={}
for line in logs['source-controls'].decode().splitlines():
 for marker,isindex in (('CDR_DRAIN_WAVE_SOURCE_INDEX ',True),('CDR_DRAIN_WAVE_SOURCE_CHUNK ',False)):
  if marker not in line:continue
  text=line.split(marker,1)[1]
  if not text.startswith('{'):continue
  d=json.loads(text);name=d['path'];assert name in expected
  if isindex:assert name not in index;index[name]=d
  else:
   group=chunks.setdefault(name,{});assert type(d['index'])is int and d['index']not in group;group[d['index']]=d
assert set(index)==expected
records={}
for name,pin in index.items():
 part=chunks.get(name,{})
 assert set(part)==set(range(pin['chunks']))
 raw=b''.join(base64.b64decode(part[i]['base64'],validate=True)for i in range(pin['chunks']))
 assert len(raw)==pin['bytes']and sha(raw)==pin['sha256']
 if pin['present']:records[name]=raw;keep('source-records/'+name,raw)
keep('source-index.json',enc(index))
source_pass=next(j['conclusion']for j in jobs if j['name']=='source-controls')=='success'
if source_pass:
 assert set(records)==expected
 controls=json.loads(records['controls.json']);pub=json.loads(records['publication-controls.json'])
 assert controls['status']=='PASS_DRAIN_M1_WAVE_REPLAY_SOURCE_CONTROLS'and controls['passed']is True and controls['counts']==dict(groups=8,refusals=47,lifecycle=4)
 assert pub['status']=='PASS_COMPLETE_REPLAY_PUBLICATION_CONTROLS'and pub['passed']is True and pub['counts']==dict(positive=7,refusals=33,lifecycle=4)
 for name,status,count in [('ownership-controls.json','PASS_CURRENT_CDR_WIRE_OWNERSHIP_SOURCE_CONTROLS',33),
   ('execution-controls.json','PASS_CURRENT_CDR_OWNERSHIP_EXECUTION_SOURCE_CONTROLS',29),('tail-controls.json','PASS_CURRENT_EIGHT_DRAIN_SOURCE_CONTROLS',30)]:
  row=json.loads(records[name]);assert row['status']==status and row['count']==count and len(set(row['passed_cases']))==count
  assert row['source']==SOURCE and row['run_id']==RUN and row['attempt']==1
 assert sha(records['tail-manifest.json'])=='c898d3f61c64f9dc621f0ee576c3987ee1f5a189f609b8ba7a7119b910111b43'
native_index=None;parts={};ends={};publication=None
for line in logs.get('physical',b'').decode().splitlines():
 for marker,kind in [('CDR_DRAIN_REPLAY_INDEX ','index'),('CDR_DRAIN_REPLAY_CHUNK ','chunk'),
  ('CDR_DRAIN_REPLAY_END ','end'),('CDR_TAIL_STRAPS_PUBLICATION ','publication')]:
  if marker not in line:continue
  value=line.split(marker,1)[1]
  if not value.startswith('{'):continue
  d=json.loads(value)
  if kind=='index':assert native_index is None;native_index=d
  elif kind=='end':assert d['name']not in ends;ends[d['name']]=d
  elif kind=='publication':assert publication is None;publication=d
  else:
   group=parts.setdefault(d['name'],{});assert d['encoding']=='zlib+base64'and type(d['index'])is int and d['index']not in group
   group[d['index']]=d
native_records={};transport_errors=[]
for name,pin in (native_index or{}).items():
 p=PurePosixPath(name)
 assert not p.is_absolute()and str(p)==name and '..'not in p.parts and '\\'not in name
 assert p.suffix in ('.json','.jsonl','.stdout','.stderr','.log','.txt','.tcl','.py','.rpt')
 try:
  end=ends[name];group=parts[name];assert set(group)==set(range(end['chunks']))
  assert {k:end[k]for k in('bytes','sha256')}==pin
  raw=zlib.decompress(b''.join(base64.b64decode(group[i]['data'],validate=True)for i in range(end['chunks'])))
  assert len(raw)==pin['bytes']and sha(raw)==pin['sha256']
  native_records[name]=raw
 except BaseException as exc:transport_errors.append(dict(name=name,error=repr(exc),raw_job_log_retained=True))
assert set(parts)<=set(native_index or{})and set(ends)<=set(native_index or{})
keep('native-index.json',enc(native_index or{}));keep('native-text-transport-errors.json',enc(transport_errors))
# Preserve complete verified derived records in lossless bounded shards; no native
# GDS/LEF/ODB/SPICE/archive payload is downloaded by this collector.
locations={};batch=[];size=0;shard=0
def flush():
 global batch,size,shard
 if not batch:return
 path='native-derived-shards/%04d.json'%shard
 keep(path,enc(dict(schema='lossless-derived-record-shard-v1',records=batch)))
 for item in batch:locations[item['name']]=dict(path=path,member=item['name'],bytes=item['bytes'],sha256=item['sha256'])
 batch=[];size=0;shard+=1
for name,raw in sorted(native_records.items()):
 if batch and size+len(raw)>750000:flush()
 batch.append(dict(name=name,encoding='base64',base64=base64.b64encode(raw).decode(),bytes=len(raw),sha256=sha(raw)));size+=len(raw)
flush();keep('native-record-locations.json',enc(locations))
readable={'runtime-policy.json','result.json','terminal-integrity.json','complete-input-census.json','complete-native-text-index.json',
 'native-records/layout/result.json','native-records/layout/generation.json','native-records/layout/generation-failure.json',
 'native-records/native-lifecycle.json','native-records/physical-qualification.json','native-records/physical/result.json'}
for name,raw in native_records.items():
 if name in readable or name.endswith('-failure.json')or name.startswith('native-records/layout/drain-'):keep('readable-records/'+name,raw)
release=get('releases/429942553','release.json');tag='cloud-results-41203881385-1-cdr-current-eight-drain-straps'
ref=get('git/ref/tags/'+tag,'tag-ref.json')
assert release['tag_name']==tag and release['target_commitish']==SOURCE and release['draft']is False and release['prerelease']is True
assert ref['object']['type']=='commit'and ref['object']['sha']==SOURCE
assets={x['name']:x for x in release['assets']};assert len(assets)==len(release['assets'])
output=None;manifest=None;capsule_complete=False
if assets:
 metadata_names=[name for name in assets if name=='complete-output-index.json'or name.endswith('.parts.json')]
 assert 1<=len(metadata_names)<=2
 for name in metadata_names:
  row=assets[name];raw=raw_api('releases/assets/'+str(row['id']),True)
  assert row['state']=='uploaded'and len(raw)==row['size']and row['digest']=='sha256:'+sha(raw)
  keep('capsule-metadata/'+name,raw)
  if name=='complete-output-index.json':output=json.loads(raw)
  else:manifest=json.loads(raw)
 if output is not None:
  assert output['schema']=='complete-current-eight-drain-physical-output-index-v1'
  assert output['context']['source']==SOURCE and output['context']['run']==RUN and output['context']['attempt']==1
  assert output['actual_capture_replayed']is False and output['physical_trial_is_not_electrical_or_full_PHY_acceptance']is True
 if manifest is not None:
  assert sum(x['bytes']for x in manifest['parts'])==manifest['bytes']
  declared={x['name']for x in manifest['parts']}|{'complete-output-index.json'}|{name for name in metadata_names if name.endswith('.parts.json')}
  assert set(assets)<=declared
  for part in manifest['parts']:
   if part['name']not in assets:continue
   a=assets[part['name']];assert a['state']=='uploaded'and a['size']==part['bytes']and a['digest']=='sha256:'+part['sha256']
  capsule_complete=set(assets)==declared and output is not None
 if publication is not None:
  assert capsule_complete and publication['receipt']['complete']is True
  assert publication['complete_files']==len(output['files'])
  assert publication['archive']=={k:manifest[k]for k in('bytes','sha256')}
 if output is not None:
  for name,raw in native_records.items():assert output['files']['evidence/'+name]==dict(bytes=len(raw),sha256=sha(raw))

result=json.loads(native_records.get('result.json',b'null'));generation=json.loads(native_records.get('native-records/layout/generation.json',b'null'))
physical=json.loads(native_records.get('native-records/physical-qualification.json',b'null'))
lifecycle=json.loads(native_records.get('native-records/native-lifecycle.json',b'null'))
completed=bool(result and result.get('status')=='COMPLETE_CURRENT_EIGHT_DRAIN_PHYSICAL_TRIAL_ONLY')
if completed:
 assert run['conclusion']=='success'and source_pass and capsule_complete and publication is not None and not transport_errors
 assert result['actual_native_inputs_acquired']is True and result['physical_trial_completed']is True and result['original_electrical_rejection_preserved']is True
 assert generation['status']=='PASS_EXACT_CURRENT_EIGHT_DRAIN_STRAP_GENERATION_ONLY'and generation['actual_devices']==8 and generation['declared_additions_only']is True
 assert len(generation['actual_candidate_mutation_controls'])==5 and all(x['rejected']is True for x in generation['actual_candidate_mutation_controls'])
 assert physical['full_DRC_categories']==560 and physical['markers']==0 and physical['deep_and_flat_devices']==500 and physical['fault_controls']==13
 assert lifecycle['primary_error']is None and lifecycle['errors']==[] and len(lifecycle['commands'])==3
 assert all(x['returncode']==0 and x['supervision_failure']is None for x in lifecycle['commands'])
 for key in ('physical_acceptance','electrical_acceptance','full_phy_accepted','timing_accepted','qualified_pex','new_simulation'):assert result[key]is False
paths=['scripts/cdr_current_tail_straps.py','scripts/cdr_current_tail_straps_native.py','scripts/cloud_cdr_current_tail_straps.py',
 'scripts/check_cdr_current_tail_straps.py','scripts/cdr-current-tail-straps-inputs.json','scripts/cdr-current-tail-straps-pins.json',
 '.github/workflows/cdr-current-access-overlay.yml','docs/evidence/cdr-current-eight-drain-cloud-physical-source-20261031.json','docs/evidence/cdr-current-eight-drain-runtime-namespace-source-20261031.json','docs/evidence/cdr-current-eight-drain-segmented-metal-source-20261031.json']
with ThreadPoolExecutor(max_workers=4)as pool:sources=dict(zip(paths,pool.map(lambda p:remote(p,SOURCE),paths)))
m=json.loads(sources['scripts/cdr-current-tail-straps-pins.json']);assert len(m['files'])==1190
for path,raw in sources.items():
 if path in m['files']:assert sha(raw)==m['files'][path]
 keep('tested-source/'+path,raw)
receipt=dict(schema='current-eight-drain-physical-terminal-v1',run=RUN,source=SOURCE,attempt=1,workflow_conclusion=run['conclusion'],
 source_controls_passed=source_pass,source_controls=195 if source_pass else None,raw_job_logs=len(logs),source_records=len(records),
 actual_native_inputs_acquired=bool(result and result.get('actual_native_inputs_acquired')),
 physical_trial_completed=completed,actual_result=result,generation=generation,physical=physical,
 complete_native_capsule_preserved=capsule_complete,native_records=len(native_records),native_transport_errors=transport_errors,
 capsule_files=0 if output is None else len(output['files']),capsule_archive=None if manifest is None else {k:manifest[k]for k in('bytes','sha256')},
 native_payload_downloaded_locally=False,independent_archive_reextraction=False,
 physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,electrical_acceptance=False,files=pins.copy())
keep('receipt.json',enc(receipt))
head=api('git/ref/heads/'+B)['object']['sha'];assert head==SOURCE
t=api('git/trees/'+head+'?recursive=1');assert not t['truncated']and not any(x['path'].startswith(PREFIX)for x in t['tree'])
commit=publish(head,files,'Preserve complete current CDR eight-drain physical trial results and failure evidence [skip ci]')
summary=dict(proof=commit,prefix=PREFIX,run=RUN,source=SOURCE,files=len(files),bytes=sum(map(len,files.values())),
 receipt_sha256=sha(files[PREFIX+'receipt.json']),workflow_conclusion=run['conclusion'],source_controls_passed=source_pass,
 physical_trial_completed=completed,actual_native_inputs_acquired=receipt['actual_native_inputs_acquired'],
 raw_job_logs=len(logs),native_records=len(native_records),capsule_files=receipt['capsule_files'],capsule_archive=receipt['capsule_archive'])
print('RESULT_JSON:'+json.dumps(dict(summary,phase='published')),flush=True)
with ThreadPoolExecutor(max_workers=4)as pool:
 for path,raw in zip(files,pool.map(lambda p:remote(p,commit),files)):assert raw==files[path],path
print('RESULT_JSON:'+json.dumps(dict(summary,phase='readback_verified',all_files_verified=True)),flush=True)
