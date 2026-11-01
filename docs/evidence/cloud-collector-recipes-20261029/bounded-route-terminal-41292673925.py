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

import io,zipfile,zlib
from concurrent.futures import ThreadPoolExecutor
RUN=41292673925;SOURCE='7a0776718ec37a106b7dfde0cbd477c6a2a5522f';RELEASE=430474717
run=api('actions/runs/'+str(RUN));assert run['status']=='completed' and run['conclusion']=='failure' and run['head_sha']==SOURCE and run['run_attempt']==1
jobs=api('actions/runs/'+str(RUN)+'/jobs?per_page=100');assert jobs['total_count']==len(jobs['jobs'])==4
arts=api('actions/runs/'+str(RUN)+'/artifacts?per_page=100');assert arts['total_count']==len(arts['artifacts'])==6
release=api('releases/'+str(RELEASE));tag=api('git/ref/tags/'+release['tag_name'])
assert release['target_commitish']==SOURCE and tag['object']['type']=='commit' and tag['object']['sha']==SOURCE
selected={13080578763:'full-job-logs',13078205793:'source-job-logs',13077688979:'integration-controls',13077679234:'targeted-controls',13077659231:'bounded-controls'}
files={};receipts=[]
for a in arts['artifacts']:
 if a['id']not in selected:continue
 assert not a['expired'] and a['size_in_bytes']<10000000
 raw=subprocess.check_output(['gh','api',R+'actions/artifacts/'+str(a['id'])+'/zip'])
 assert a['digest']=='sha256:'+sha(raw)
 z=zipfile.ZipFile(io.BytesIO(raw))
 assert len(z.namelist())==len(set(z.namelist())) and sum(x.file_size for x in z.infolist())<150000000
 for x in z.infolist():
  n=x.filename
  if x.is_dir():continue
  assert not n.startswith('/') and '..'not in n.split('/') and n.endswith(('.json','.log','.txt','.py','.md','.yml','.stdout','.stderr','.tcl')),n
  assert ((x.external_attr>>16)&0o170000)!=0o120000
  b=z.read(n);b.decode()
  if n.endswith('.json'):json.loads(b)
  files[selected[a['id']]+'/'+n]=b
 receipts.append(dict(id=a['id'],name=a['name'],bytes=len(raw),sha256=sha(raw),files=len(z.namelist())))
assert len(receipts)==5
for name in ['candidate-outputs.json','candidate-parts.json']:
 a=next(a for a in release['assets']if a['name']==name);assert a['size']<1000000
 b=subprocess.check_output(['gh','api',R+'releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'])
 assert len(b)==a['size'] and a['digest']=='sha256:'+sha(b)
 json.loads(b);files['publication/'+name]=b
outputs=json.loads(files['publication/candidate-outputs.json'])
assert outputs['run']==str(RUN) or outputs['run']==RUN
assert outputs['source']==SOURCE and str(outputs['attempt'])=='1'
assert not any(outputs[k] for k in ['full_phy_accepted','physical_acceptance','timing_accepted'])
parts=json.loads(files['publication/candidate-parts.json'])
print(json.dumps({'publication_keys':list(parts),'files':len(files),'bytes':sum(map(len,files.values()))}),flush=True)
for part in parts['parts']:
 a=next(a for a in release['assets']if a['name']==part['name'])
 assert a['size']==part['bytes'] and a['digest']=='sha256:'+part['sha256']
assert {a['name']for a in release['assets']}=={'candidate-outputs.json','candidate-parts.json'}|{p['name']for p in parts['parts']}
raw=subprocess.check_output(['gh','api',R+'actions/jobs/124807477628/logs'])
files['jobs/124807477628.log']=raw
wanted={'native/bulk-postdrt-antenna/bounded-route-stage.json','native/bulk-postdrt-antenna/restore-plan-failure.json','native/bulk-postdrt-antenna/failure-restore-plan-failure.json','native/bulk-postdrt-inner-result.json','native/bulk-postdrt-route-cycle-terminal.json','native/bulk-postdrt-supervision/bulk-postdrt-route.stdout'}
index={};chunks={}
for line in raw.decode().splitlines():
 for marker,kind in [('BULK_POSTDRT_INDEX ',True),('BULK_POSTDRT_CHUNK ',False)]:
  if marker not in line:continue
  s=line.split(marker,1)[1]
  if not s.startswith('{'):continue
  row=json.loads(s)
  if kind:
   for n,p in row.items():
    if n in wanted:
     if n in index:assert index[n]==p
     index[n]=p
  elif row['name']in wanted:
   bucket=chunks.setdefault(row['name'],{})
   if row['index']in bucket:assert bucket[row['index']]==row
   bucket[row['index']]=row
assert wanted==set(index)==set(chunks)
for n,p in index.items():
 pieces=chunks[n];assert set(pieces)==set(range(next(iter(pieces.values()))['chunks']))
 b=zlib.decompress(base64.b64decode(''.join(pieces[i]['base64']for i in range(len(pieces))),validate=True))
 assert len(b)==p['bytes']and sha(b)==p['sha256']
 assert outputs['files'][n.removeprefix('native/')]==p
 if n.endswith('.json'):json.loads(b)
 files['decoded/'+n.removeprefix('native/')]=b
stage=json.loads(files['decoded/bulk-postdrt-antenna/bounded-route-stage.json'])
assert stage['route_returned']and stage['complete']and stage['iterations']==8
for k in ['route-partial.odb','routed-fixed.odb']:
 assert stage['checkpoints'][k]['sha256']=='b87a2d43fe33dd8ca99f0faa2bdf38337ae30d6c5b72a337472919ac57f64e63'
fault=json.loads(files['decoded/bulk-postdrt-antenna/restore-plan-failure.json'])
assert "assert classes(p['records'][n])=='FIXED'"in fault['traceback']
route=files['decoded/bulk-postdrt-supervision/bulk-postdrt-route.stdout'].decode()
assert 'Number of violations = 397.'in route and 'NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_RETURNED'in route
observation=dict(run=RUN,source=SOURCE,conclusion='failure',route_returned=True,original_raw_checkpoints_saved=True,raw_odb_sha256=stage['checkpoints']['routed-fixed.odb']['sha256'],router_last_drc_violations=397,restoration_failed=True,failure_site='mainchip_original_clock_restoration.py:215',failure='Expected FIXED encoded class before restoration',restored_candidate_accepted=False,final_audit_started=False,native_payload_acquired_locally=False,all_acceptance_gates_retained=True)
for n,d in [('run',run),('jobs',jobs),('artifacts',arts),('release',release),('tag-ref',tag),('archive-receipts',receipts),('observation',observation)]:
 files[n+'.json']=(json.dumps(d,sort_keys=True,indent=2)+chr(10)).encode()
receipt=dict(**observation,release=RELEASE,all_selected_text_artifacts_complete=True,mixed_native_artifact_downloaded=False,native_release_parts_downloaded=False,files={n:dict(bytes=len(b),sha256=sha(b))for n,b in files.items()})
files['receipt.json']=(json.dumps(receipt,sort_keys=True,indent=2)+chr(10)).encode()
PREFIX='docs/evidence/bounded-route-native-terminal-'+str(RUN);B='codex/bounded-route-native-proof-'+str(RUN)
assert api('git/matching-refs/heads/'+B)==[]
entries=[]
for n,b in files.items():
 assert len(b)<90000000
 blob=api('git/blobs',dict(encoding='base64',content=base64.b64encode(b).decode()))
 entries.append(dict(path=PREFIX+'/'+n,mode='100644',type='blob',sha=blob['sha']))
tree=api('git/trees',dict(base_tree=api('git/commits/'+SOURCE)['tree']['sha'],tree=entries))
commit=api('git/commits',dict(message='Preserve bounded route checkpoint and class-restoration failure [skip ci]',tree=tree['sha'],parents=[SOURCE]))
assert api('git/matching-refs/heads/'+B)==[]
api('git/refs',dict(ref='refs/heads/'+B,sha=commit['sha']))
head=commit['sha']
print(json.dumps({'published':head,'prefix':PREFIX,'files':len(files)}),flush=True)
def verify(item):
 n,b=item;assert remote(PREFIX+'/'+n,head)==b,n
list(ThreadPoolExecutor(3).map(verify,files.items()))
print(json.dumps(dict(head=head,prefix=PREFIX,files=len(files),bytes=sum(map(len,files.values())),receipt_sha256=sha(files['receipt.json']),run=RUN,source=SOURCE,conclusion=run['conclusion'])),flush=True)
