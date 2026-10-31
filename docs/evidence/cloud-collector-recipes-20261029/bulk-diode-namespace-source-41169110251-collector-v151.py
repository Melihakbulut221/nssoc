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
def collect_bulk_integration(RUN,SOURCE):
 global B
 B='codex/mainchip-net459-diode-prune'
 PREFIX='docs/evidence/mainchip-bulk-postdrt-integration-source-terminal-'+str(RUN)+'/'
 files={};pins={};errors=[];decoded={}
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
 assert len(jobs)==2 and {x['name']for x in jobs}=={'source-controls','preserve-job-log'}
 rawlogs={}
 for listed in jobs:
  j=metadata('actions/jobs/'+str(listed['id']),'jobs/'+str(listed['id'])+'.json')
  assert j['head_sha']==SOURCE and j['run_id']==RUN and j['status']=='completed'
  if j['conclusion']=='skipped':errors.append(dict(stage='job',name=j['name'],error='skipped'));continue
  raw=getraw('actions/jobs/'+str(j['id'])+'/logs');assert raw
  keep('logs/'+str(j['id'])+'.log',raw);rawlogs[j['name']]=raw
 index={};chunks={}
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
  assert set(part)==set(range(pin['chunks']))
  b=b''.join(base64.b64decode(part[i]['base64'],validate=True)for i in range(pin['chunks']))
  assert len(b)==pin['bytes']and sha(b)==pin['sha256']
  keep('records/'+name,b)
  if not pin['present']:errors.append(dict(stage='record',name=name,error='not present in hosted run'))
  elif name.endswith('.json'):decoded[name]=json.loads(b)
 keep('index.json',(json.dumps(index,sort_keys=True,indent=2)+'\n').encode())
 ctx=decoded.get('context.json')
 if ctx:
  assert ctx['source']==SOURCE and ctx['run_id']==RUN and ctx['attempt']==1
  assert all(ctx[k]is False for k in('native_authorized','native_acquisition','native_executed','physical_acceptance','timing_accepted','full_phy_accepted'))
 controls=decoded.get('controls.json',{});execution=decoded.get('execution.json',{})
 passed=controls.get('status')=='PASS_BULK_POSTDRT_INTEGRATION_SOURCE_CONTROLS'
 counts=dict(inherited=dict(positive=10,refusal=49,lifecycle=20,rendered_tcl=9),namespace=25,projection=3,supervisor=2,shutdown=4,acquisition=4,native_audit=12,bound_cycle=21,publication=3)
 if passed:
  assert controls['counts']==counts
  assert controls['current_context']==dict(source=SOURCE,run_id=RUN,attempt=1,source_controls_only=True,native_executed=False)
  assert all(controls[k]is False for k in('native_authorized','native_executed','physical_acceptance','timing_accepted','full_phy_accepted'))
  assert files[PREFIX+'records/controls.json']==files[PREFIX+'records/controls.stdout']
  assert execution['returncode']==0
 else:errors.append(dict(stage='source-controls',status=controls.get('status'),error=controls.get('error')))
 if execution:
  assert execution['source']==SOURCE and execution['run_id']==RUN and execution['attempt']==1 and execution['native_executed']is False
 paths=['scripts/check_mainchip_bulk_diode_namespace.py','scripts/check_mainchip_bulk_postdrt_antenna.py','scripts/check_mainchip_bulk_postdrt_integration.py','scripts/cloud_mainchip_bulk_postdrt_antenna.py','scripts/mainchip_bulk_postdrt_antenna_inner.py','scripts/mainchip_bulk_postdrt_antenna_native.py','scripts/mainchip-bulk-postdrt-integration-pins.json','scripts/mainchip-bulk-postdrt-antenna-pins.json','.github/workflows/mainchip-net459-diode-prune.yml']
 with ThreadPoolExecutor(max_workers=4)as pool:sources=dict(zip(paths,pool.map(lambda p:remote(p,SOURCE),paths)))
 manifest=json.loads(sources['scripts/mainchip-bulk-postdrt-integration-pins.json'])
 assert len(manifest['files'])==1707 and manifest['native_execution_enabled']is False and manifest['source_controls_authorized']is True
 assert sources['scripts/mainchip-bulk-postdrt-integration-pins.json']==files[PREFIX+'records/manifest.json']
 assert sources['scripts/mainchip-bulk-postdrt-antenna-pins.json']==files[PREFIX+'records/bulk-manifest.json']
 source_pins={}
 for path,b in sources.items():
  keep('tested-source/'+path,b);source_pins[path]=dict(bytes=len(b),sha256=sha(b))
  if path in manifest['files']:assert sha(b)==manifest['files'][path]
 assert sha(sources['.github/workflows/mainchip-net459-diode-prune.yml'])==ctx['workflow']['sha256']
 keep('source-bindings.json',(json.dumps(source_pins,sort_keys=True,indent=2)+'\n').encode())
 receipt=dict(schema='bulk-postdrt-integration-source-terminal-v2',run=RUN,source=SOURCE,attempt=1,workflow_id=401215446,
  workflow_conclusion=r['conclusion'],source_controls_passed=passed,source_counts=controls.get('counts'),source_status=controls.get('status'),
  full_source_records=7,raw_job_logs=len(rawlogs),full_tested_sources=len(sources),all_source_pins_checked_by_hosted_source_step=True,
  locally_reverified_selected_source_pins=len(source_pins),all_transitive_source_pins_reverified_locally=False,
  errors=errors,files=pins.copy(),native_authorized=False,native_acquired_locally=False,native_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
 keep('receipt.json',(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode())
 head=api('git/ref/heads/'+B)['object']['sha']
 tree=api('git/trees/'+head+'?recursive=1');assert not tree['truncated']
 assert not any(x['path'].startswith(PREFIX)for x in tree['tree'])
 ref=publish(head,files,'Preserve complete bulk adapter source qualification '+str(RUN)+' [skip ci]')
 summary=dict(proof=ref,prefix=PREFIX,files=len(files),bytes=sum(map(len,files.values())),receipt_sha256=sha(files[PREFIX+'receipt.json']),run=RUN,source=SOURCE,workflow_conclusion=r['conclusion'],source_controls_passed=passed,counts=controls.get('counts'),errors=errors)
 print(json.dumps(dict(summary,phase='published')),flush=True)
 with ThreadPoolExecutor(max_workers=4)as pool:
  for p,b in zip(files,pool.map(lambda p:remote(p,ref),files)):assert b==files[p],p
 print(json.dumps(dict(summary,phase='readback_verified',all_files_verified=True)),flush=True)
 return summary

collect_bulk_integration(41169110251,'5256e147cfa2efed8602613a39dfe3eb569b4b7a')
