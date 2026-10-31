import subprocess,json,hashlib,base64
R='repos/Melihakbulut221/nssoc/'
B='codex/complete-open-work'
def api(path,data=None,method=None):
 c=['gh','api',R+path]
 if data is not None:c+=['--method',method or 'POST','--input','-']
 r=subprocess.run(c,input=json.dumps(data)if data is not None else None,text=True,capture_output=True)
 if r.returncode:raise RuntimeError('GitHub API '+path+': '+r.stderr[:2000])
 return json.loads(r.stdout)if r.stdout.strip()else {}
def remote(path,ref):
 d=api('contents/'+path+'?ref='+ref)
 if d.get('content'):return base64.b64decode(d['content'])
 return base64.b64decode(api('git/blobs/'+d['sha'])['content'])
def asset(aid):
 return subprocess.check_output(['gh','api',R+'releases/assets/'+str(aid),'-H','Accept: application/octet-stream'])
def sha(b):return hashlib.sha256(b).hexdigest()
def publish(head,files,msg):
 parent=api('git/commits/'+head)
 entries=[]
 for p,d in files.items():
  if isinstance(d,str):d=d.encode()
  blob=api('git/blobs',{'encoding':'base64','content':base64.b64encode(d).decode()})
  entries.append({'path':p,'mode':'100644','type':'blob','sha':blob['sha']})
 tree=api('git/trees',{'base_tree':parent['tree']['sha'],'tree':entries})
 commit=api('git/commits',{'message':msg,'tree':tree['sha'],'parents':[head]})
 assert api('git/ref/heads/'+B)['object']['sha']==head
 api('git/refs/heads/'+B,{'sha':commit['sha'],'force':False},'PATCH')
 return commit['sha']

import time
_api_once=api
def api(path,data=None,method=None):
 for attempt in range(4):
  try:return _api_once(path,data,method)
  except RuntimeError as exc:
   transient=any(x in str(exc) for x in ('TLS handshake timeout','connection reset','unexpected EOF','HTTP 502','HTTP 503','HTTP 504','i/o timeout'))
   if data is not None or method not in (None,'GET') or not transient or attempt==3:raise
   time.sleep(2+attempt)

from concurrent.futures import ThreadPoolExecutor
from pathlib import PurePosixPath
import zlib
RUN=41163081445;SOURCE='cb1d9d19fa9ee1e18d944733f08e7be44a373d28'
B='codex/mainchip-net459-diode-prune'
PREFIX='docs/evidence/mainchip-bulk-postdrt-native-terminal-41163081445/'
files={};pins={};errors=[]
def keep(name,b):
 assert name not in pins
 pins[name]=dict(bytes=len(b),sha256=sha(b));files[PREFIX+name]=b
def getraw(path):
 for attempt in range(4):
  r=subprocess.run(['gh','api',R+path],capture_output=True)
  if r.returncode==0:return r.stdout
  error=r.stderr.decode()
  if attempt==3 or not any(x in error for x in('HTTP 502','HTTP 503','HTTP 504','TLS handshake','connection reset','unexpected EOF')):raise RuntimeError(error[:1500])
  time.sleep(2+attempt)
def metadata(path,name):
 b=getraw(path);keep(name,b);return json.loads(b)
r=metadata('actions/runs/'+str(RUN),'run.json')
assert r['status']=='completed'and r['head_sha']==SOURCE and r['run_attempt']==1 and r['workflow_id']==401215446
jobs=metadata('actions/runs/'+str(RUN)+'/attempts/1/jobs?per_page=100','jobs.json')['jobs']
assert len(jobs)==4 and {x['name']for x in jobs}=={'source-controls','preserve-job-log','trial','preserve-antenna-job-logs'}
rawlogs={}
for listed in jobs:
 j=metadata('actions/jobs/'+str(listed['id']),'jobs/'+str(listed['id'])+'.json')
 assert j['head_sha']==SOURCE and j['run_id']==RUN and j['status']=='completed'
 assert j['conclusion']!='skipped'
 raw=getraw('actions/jobs/'+str(j['id'])+'/logs');assert raw
 keep('logs/'+str(j['id'])+'.log',raw);rawlogs[j['name']]=raw
index={};chunks={};decoded={}
expected={'context.json','manifest.json','bulk-manifest.json','controls.json','controls.stdout','controls.stderr','execution.json'}
for line in rawlogs['source-controls'].decode().splitlines():
 for marker,isindex in(('BULK_POSTDRT_CONTROL_INDEX ',True),('BULK_POSTDRT_CONTROL_CHUNK ',False)):
  if marker not in line:continue
  text=line.split(marker,1)[1]
  if not text.startswith('{'):continue
  d=json.loads(text);name=d['path'];assert name in expected
  if isindex:assert name not in index;index[name]=d
  else:
   part=chunks.setdefault(name,{})
   assert type(d['index'])is int and d['index']not in part;part[d['index']]=d
assert set(index)==expected
for name,pin in index.items():
 part=chunks.get(name,{})
 assert set(part)==set(range(pin['chunks']))and pin['present']is True
 b=b''.join(base64.b64decode(part[i]['base64'],validate=True)for i in range(pin['chunks']))
 assert len(b)==pin['bytes']and sha(b)==pin['sha256']
 keep('source-records/'+name,b)
 if name.endswith('.json'):decoded[name]=json.loads(b)
keep('source-index.json',(json.dumps(index,sort_keys=True,indent=2)+'\n').encode())
ctx=decoded['context.json'];control=decoded['controls.json'];execution=decoded['execution.json']
assert ctx['source']==SOURCE and ctx['run_id']==RUN and ctx['attempt']==1 and ctx['native_enabled_in_manifest']is True
assert control['status']=='PASS_BULK_POSTDRT_INTEGRATION_SOURCE_CONTROLS'and execution['returncode']==0
assert control['counts']==dict(inherited=dict(positive=10,refusal=49,lifecycle=20,rendered_tcl=9),projection=3,supervisor=2,shutdown=4,acquisition=4,native_audit=12,bound_cycle=21,publication=3)
assert control['current_context']==dict(source=SOURCE,run_id=RUN,attempt=1,source_controls_only=True,native_executed=False)
native_index=None;native_chunks={};records={}
for line in rawlogs['trial'].decode().splitlines():
 for marker,kind in (('BULK_POSTDRT_INDEX ','index'),('BULK_POSTDRT_CHUNK ','chunk')):
  if marker not in line:continue
  text=line.split(marker,1)[1]
  if not text.startswith('{'):continue
  d=json.loads(text)
  if kind=='index':assert native_index is None;native_index=d
  else:
   name=d['name'];ps=native_chunks.setdefault(name,{})
   assert d['encoding']=='zlib-base64'and type(d['index'])is int and d['index']not in ps
   ps[d['index']]=d
assert native_index and set(native_chunks)==set(native_index)
for name,pin in native_index.items():
 path=PurePosixPath(name);assert not path.is_absolute()and str(path)==name and '..'not in path.parts and '\\'not in name
 assert path.suffix in ('.json','.jsonl','.log','.txt','.tcl','.py','.stdout','.stderr'),name
 ps=native_chunks[name];n=ps[0]['chunks'];assert set(ps)==set(range(n))
 assert all(d['chunks']==n and d['bytes']==pin['bytes']and d['sha256']==pin['sha256']for d in ps.values())
 raw=zlib.decompress(b''.join(base64.b64decode(ps[i]['base64'],validate=True)for i in range(n)))
 assert len(raw)==pin['bytes']and sha(raw)==pin['sha256']
 keep('native-records/'+name,raw);records[name]=raw
keep('native-index.json',(json.dumps(native_index,sort_keys=True,indent=2)+'\n').encode())
release=metadata('releases/429687481','release.json')
tag='cloud-results-41163081445-1-mainchip-bulk-postdrt-antenna'
ref=metadata('git/ref/tags/'+tag,'tag-ref.json')
assert release['tag_name']==tag and release['target_commitish']==SOURCE and release['draft']is False and release['prerelease']is True
assert ref['object']['type']=='commit'and ref['object']['sha']==SOURCE
assets={a['name']:a for a in release['assets']};assert len(assets)==len(release['assets'])
derived={}
for name in ('candidate-outputs.json','candidate-parts.json'):
 a=assets[name];raw=asset(a['id'])
 assert len(raw)==a['size']and 'sha256:'+sha(raw)==a['digest']and a['state']=='uploaded'
 keep('capsule-metadata/'+name,raw);derived[name]=json.loads(raw)
output=derived['candidate-outputs.json'];parts=derived['candidate-parts.json']
assert output['source']==SOURCE and output['run']==RUN and output['attempt']==1
assert output['input']==dict(bytes=213429050,sha256='3f422f7c92b9395f3678e1bf065fe790478b1c424c5b7bae39060095b23c3d53')
assert sum(x['bytes']for x in parts['parts'])==parts['archive']['bytes']
assert {x['name']for x in parts['parts']}|{'candidate-outputs.json','candidate-parts.json'}==set(assets)
for row in parts['parts']:
 a=assets[row['name']]
 assert a['size']==row['bytes']and a['digest']=='sha256:'+row['sha256']and a['state']=='uploaded'
result=json.loads(records['result.json']);inner=json.loads(records['native/bulk-postdrt-inner-result.json'])
publication=json.loads(records['native-capsule-publication.json'])
assert publication['status']=='COMPLETE_PERMANENT_NATIVE_CAPSULE'and publication['files']==output['files']and publication['archive']==parts['archive']
assert result['output_preservation']['complete']is True
for name,pin in result['output_preservation']['copied'].items():assert native_index['native/'+name]==pin
for name,pin in result['output_preservation']['complete_large_outputs_in_native_capsule'].items():assert output['files'][name]==pin
for path,pin in output['files'].items():
 if 'native/'+path in native_index:assert native_index['native/'+path]==pin
native_pass=result['status']=='COMPLETE_BULK_POSTDRT_CLOUD_EXPERIMENT'
commands=[dict(label=x['label'],returncode=x.get('returncode'),seconds=x.get('supervision_record',{}).get('elapsed_seconds',x.get('elapsed_seconds')))for x in inner['commands']]
repair=[x for x in commands if x['label']=='bulk-postdrt-repair'];route=[x for x in commands if x['label']=='bulk-postdrt-route']
base_drc=json.loads(records['native/bulk-postdrt-antenna/baseline-drc.json'])
base_ant=json.loads(records['native/bulk-postdrt-antenna/baseline-antenna-summary.json'])
paths=['scripts/check_mainchip_bulk_postdrt_integration.py','scripts/cloud_mainchip_bulk_postdrt_antenna.py','scripts/mainchip_bulk_postdrt_antenna_inner.py','scripts/mainchip_bulk_postdrt_antenna_native.py','scripts/mainchip_bulk_postdrt_antenna.py','scripts/mainchip-bulk-postdrt-integration-pins.json','scripts/mainchip-bulk-postdrt-antenna-pins.json','.github/workflows/mainchip-net459-diode-prune.yml']
with ThreadPoolExecutor(max_workers=4)as pool:sources=dict(zip(paths,pool.map(lambda p:remote(p,SOURCE),paths)))
manifest=json.loads(sources['scripts/mainchip-bulk-postdrt-integration-pins.json'])
assert manifest['native_execution_enabled']is True and len(manifest['files'])==1555
assert sources['scripts/mainchip-bulk-postdrt-integration-pins.json']==files[PREFIX+'source-records/manifest.json']
for p,b in sources.items():
 keep('tested-source/'+p,b)
 if p in manifest['files']:assert sha(b)==manifest['files'][p]
receipt=dict(schema='bulk-postdrt-native-terminal-v1',run=RUN,source=SOURCE,attempt=1,workflow_conclusion=r['conclusion'],
 source_controls_passed=True,source_counts=control['counts'],raw_job_logs=len(rawlogs),full_source_records=7,full_native_records=len(native_index),
 tested_sources=len(sources),native_executed=True,native_passed=native_pass,native_status=result['status'],inner_status=inner['status'],
 native_commands=commands,repair_calls=len(repair),route_calls=len(route),complete_native_capsule_preserved=True,capsule_files=len(output['files']),capsule_archive=parts['archive'],
 large_native_bytes_remain_in_cloud=True,independent_output_archive_reextraction=False,native_payload_downloaded_locally=False,
 baseline=dict(drc=base_drc,antenna=base_ant),collection_errors=errors,files=pins.copy(),physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
keep('receipt.json',(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode())
head=api('git/ref/heads/'+B)['object']['sha'];assert head==SOURCE
tree=api('git/trees/'+head+'?recursive=1');assert not tree['truncated']and not any(x['path'].startswith(PREFIX)for x in tree['tree'])
commit=publish(head,files,'Preserve complete bulk native SIGSEGV failure and all available outputs [skip ci]')
summary=dict(proof=commit,prefix=PREFIX,files=len(files),bytes=sum(map(len,files.values())),receipt_sha256=sha(files[PREFIX+'receipt.json']),run=RUN,source=SOURCE,
 workflow_conclusion=r['conclusion'],native_passed=native_pass,source_controls_passed=True,raw_job_logs=len(rawlogs),full_native_records=len(native_index),
 capsule_files=len(output['files']),capsule_archive=parts['archive'],commands=commands,repair_calls=len(repair),route_calls=len(route),collection_errors=errors)
print(json.dumps(dict(summary,phase='published')),flush=True)
with ThreadPoolExecutor(max_workers=4)as pool:
 for p,b in zip(files,pool.map(lambda p:remote(p,commit),files)):assert b==files[p],p
print(json.dumps(dict(summary,phase='readback_verified',all_files_verified=True)),flush=True)
