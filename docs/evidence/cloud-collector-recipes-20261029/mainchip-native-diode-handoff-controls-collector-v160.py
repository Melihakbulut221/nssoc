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
RUN=41192394563;SOURCE='0292d62f4c1e459598b0b1a1c4d500db61d68cd2'
B='codex/mainchip-net459-diode-prune'
PREFIX='docs/evidence/mainchip-diode-reconstruction-handoff-controls-41192394563/'
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
names={j['name']for j in jobs}
assert {'source-controls','preserve-job-log'}<=names<= {'source-controls','preserve-job-log','diode-reconstruction','preserve-antenna-job-logs'}
assert all(j['conclusion']=='skipped' for j in jobs if j['name']in('diode-reconstruction','preserve-antenna-job-logs'))
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
context=json.loads(source_records.get('context.json',b'null'))
if context is not None:assert context['source']==SOURCE and context['run_id']==RUN and context['attempt']==1
controls=json.loads(source_records.get('controls.json',b'null'))
audit_controls=json.loads(source_records.get('audit-controls.json',b'null'))
source_pass=next(j['conclusion']for j in jobs if j['name']=='source-controls')=='success'
if source_pass:
 assert set(source_records)==expected
 assert controls['status']=='PASS_BULK_POSTDRT_INTEGRATION_SOURCE_CONTROLS'
 assert controls['counts']==dict(inherited=dict(positive=10,refusal=49,lifecycle=20,rendered_tcl=9),namespace=25,
  projection=3,supervisor=2,shutdown=4,acquisition=4,native_audit=12,bound_cycle=21,publication=3)
 assert json.loads(source_records['execution.json'])['returncode']==0
 assert audit_controls['status']=='PASS_SAVED_DIODE_RECONSTRUCTION_SOURCE_CONTROLS'and audit_controls['count']==62 and len(set(audit_controls['passed_cases']))==62
 assert audit_controls['source']==SOURCE and audit_controls['run_id']==RUN and audit_controls['attempt']==1
 assert json.loads(source_records['audit-execution.json'])['returncode']==0

paths=['scripts/mainchip_saved_diode_reconstruction.py','scripts/cloud_mainchip_saved_diode_reconstruction.py',
 'scripts/check_mainchip_saved_diode_reconstruction.py','scripts/mainchip_saved_diode_reconstruction_native.py',
 'scripts/mainchip_saved_diode_reconstruction_inner.py','scripts/mainchip-saved-diode-reconstruction-pins.json',
 '.github/workflows/mainchip-net459-diode-prune.yml','docs/evidence/mainchip-diode-reconstruction-host-transfer-fix-20261031.json']
with ThreadPoolExecutor(max_workers=4)as pool:sources=dict(zip(paths,pool.map(lambda p:remote(p,SOURCE),paths)))
manifest=json.loads(sources['scripts/mainchip-saved-diode-reconstruction-pins.json'])
assert len(manifest['files'])==2294
for path,raw in sources.items():
 if path in manifest['files']:assert sha(raw)==manifest['files'][path]
 keep('tested-source/'+path,raw)
if source_pass:
 assert run['conclusion']=='success'
 assert audit_controls['handoff_controls']==10 and audit_controls['reconstruction_controls']==22 and audit_controls['inherited_observer_controls']==30
 assert audit_controls['source_pin']==sha(sources['scripts/mainchip_saved_diode_reconstruction_native.py'])
 assert source_records['qualification-manifest.json']==sources['scripts/mainchip-saved-diode-reconstruction-pins.json']
receipt=dict(schema='native-diode-handoff-source-controls-terminal-v1',run=RUN,source=SOURCE,attempt=1,
 workflow_conclusion=run['conclusion'],source_controls_passed=source_pass,
 source_counts=None if controls is None else controls['counts'],
 source_control_count=None if audit_controls is None else audit_controls['count'],
 passed_cases=[]if audit_controls is None else audit_controls['passed_cases'],
 raw_job_logs=len(logs),source_records=len(source_records),no_native_job_executed=True,
 native_payload_downloaded_locally=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,files=pins.copy())
keep('receipt.json',encode(receipt))
head=api('git/ref/heads/'+B)['object']['sha'];assert head==SOURCE
tree=api('git/trees/'+head+'?recursive=1');assert not tree['truncated']and not any(x['path'].startswith(PREFIX)for x in tree['tree'])
commit=publish(head,files,'Preserve actual source-only native-result handoff regression and complete logs [skip ci]')
summary=dict(proof=commit,prefix=PREFIX,files=len(files),bytes=sum(map(len,files.values())),receipt_sha256=sha(files[PREFIX+'receipt.json']),
 run=RUN,source=SOURCE,workflow_conclusion=run['conclusion'],source_controls_passed=source_pass,
 raw_job_logs=len(logs),source_records=len(source_records),source_control_count=receipt['source_control_count'],native_executed=False)
print(json.dumps(dict(summary,phase='published')),flush=True)
with ThreadPoolExecutor(max_workers=4)as pool:
 for path,raw in zip(files,pool.map(lambda p:remote(p,commit),files)):assert raw==files[path],path
print(json.dumps(dict(summary,phase='readback_verified',all_files_verified=True)),flush=True)
