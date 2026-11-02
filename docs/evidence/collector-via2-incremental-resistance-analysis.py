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
 (41430503141,"3d2601040c26b9e10443f674e6d2c211f8d14546",13134345896,2150347,"1cbfc4bbced4d9686bdbfc64d5f0f39e104f4e03981c82e760ead030bfb340f8"),
 (41441842390,"d9bd6e108d890fcfbab5d77d85535a49d2092b88",13140841659,2152067,"1fc0b6b2bff3d421cbf90411e2afcd5af57dc4b6e6568274d717e5b88d78ac07")]:
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

co=[x for x in rows if "_collector_"in x["label"]];other=[x for x in rows if "_collector_"not in x["label"]]
assert len(co)==8 and len(other)==24
print(json.dumps(dict(status="COMPLETE_INCREMENTAL_COLLECTOR_VIA2_VERSUS_DRAIN_M23_DERIVED_RESISTANCE",parents=[r[1]for r in records],same_solver=True,common_reference=old["reference"],all32_semantic_queries=True,full_partition_count=114,rows=rows,collector_delta_range_ohm=[min(x["delta_ohm"]for x in co),max(x["delta_ohm"]for x in co)],collector_reduction_percent_range=[min(x["reduction_percent"]for x in co),max(x["reduction_percent"]for x in co)],other24_max_absolute_delta_ohm=max(abs(x["delta_ohm"])for x in other),native_acquired_locally=False,electrical_acceptance_inferred=False)),flush=True)
