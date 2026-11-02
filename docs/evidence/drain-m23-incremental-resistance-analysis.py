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

import io,zipfile
records=[]
for rid,src,aid,nb,digest in [
 (41423647133,"a11002d7924f6649598fbec223eb830ed64402af",13131285945,1502833,"b37f734198ded94349ef247bb9c1b052e89b460de9c0092fea95f424db8ab036"),
 (41430503141,"3d2601040c26b9e10443f674e6d2c211f8d14546",13134345896,2150347,"1cbfc4bbced4d9686bdbfc64d5f0f39e104f4e03981c82e760ead030bfb340f8")]:
 r=api("actions/runs/"+str(rid));assert r["status"]=="completed"and r["conclusion"]=="success"and r["head_sha"]==src
 a=api("actions/artifacts/"+str(aid));b=subprocess.check_output(["gh","api",R+"actions/artifacts/"+str(aid)+"/zip"])
 assert a["workflow_run"]["id"]==rid and a["workflow_run"]["head_sha"]==src and len(b)==a["size_in_bytes"]==nb and sha(b)==digest and a["digest"]=="sha256:"+digest
 z=zipfile.ZipFile(io.BytesIO(b))
 assert len(z.namelist())==len(set(z.namelist()))and all(n.endswith((".json",".jsonl",".md",".py",".yml",".log",".rpt",".txt",".stdout",".stderr"))and not n.startswith("/")and ".."not in n.split("/")for n in z.namelist())
 q=json.loads(z.read("model-comparison.json"));part=json.loads(z.read("native-partition-comparison.json"))
 assert q["all32_actual_full_network_queries"]and q["same_frozen_solver"]and part["partition_count"]==114 and part["status"]=="PASS_ALL500_PRIMITIVES1446_TERMINALS_COMPLETE_PARTITIONS"
 records.append((q,dict(run=rid,source=src,artifact=aid,bytes=nb,sha256=digest)))
old,new=records[0][0],records[1][0];assert old["reference"]==new["reference"]
om={x["label"]:x for x in old["queries"]};nm={x["label"]:x for x in new["queries"]};assert len(om)==len(nm)==32 and set(om)==set(nm)
rows=[]
for label in sorted(om):
 a,b=om[label],nm[label]
 for key in ["source_terminal","sink_terminal","before_ohm"]:assert a[key]==b[key],(label,key)
 rows.append(dict(label=label,source_terminal=b["source_terminal"],sink_terminal=b["sink_terminal"],before_ohm=a["after_ohm"],after_ohm=b["after_ohm"],delta_ohm=b["after_ohm"]-a["after_ohm"],reduction_percent=100*(1-b["after_ohm"]/a["after_ohm"])))
em=[x for x in rows if "_emitter_"in x["label"]];other=[x for x in rows if "_emitter_"not in x["label"]]
assert len(em)==len(other)==16 and all(x["delta_ohm"]<0 for x in em)and max(abs(x["delta_ohm"])for x in other)<1e-8
print(json.dumps(dict(status="PASS_INCREMENTAL_DRAIN_M23_VERSUS_SOURCE_M2_DERIVED_RESISTANCE",parents=[r[1]for r in records],same_solver=True,common_reference=old["reference"],all32_semantic_queries=True,full_partition_count=114,rows=rows,emitter_delta_range_ohm=[min(x["delta_ohm"]for x in em),max(x["delta_ohm"]for x in em)],emitter_reduction_percent_range=[min(x["reduction_percent"]for x in em),max(x["reduction_percent"]for x in em)],other16_max_absolute_delta_ohm=max(abs(x["delta_ohm"])for x in other),native_acquired_locally=False,electrical_acceptance_inferred=False)),flush=True)
