# Already executed: proof7207dcb28bee4c764ec1ef3fb887d5f970e11434. Retained as provenance; do not rerun.
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

import zlib
from pathlib import PurePosixPath
B="codex/mainchip-net459-connectivity";head="b5fac41b5ae845af095b47c79195a209f1bd23d1";run=40956367145
prefix="docs/evidence/mainchip-net459-connectivity-terminal-"+str(run)+"/"
enc=lambda d:(json.dumps(d,sort_keys=True,indent=2)+"\n").encode()
assert api("git/ref/heads/"+B)["object"]["sha"]==head
r=api("actions/runs/"+str(run));jobs=api("actions/runs/"+str(run)+"/attempts/1/jobs?per_page=100")
assert (r["head_sha"],r["head_branch"],r["run_attempt"],r["workflow_id"],r["event"],r["status"])==(head,B,1,401101374,"workflow_dispatch","completed")
assert len(jobs["jobs"])==1 and jobs["jobs"][0]["name"]=="observe"
j=jobs["jobs"][0];assert j==api("actions/jobs/"+str(j["id"]))and j["head_sha"]==head and j["status"]=="completed"
rawlog=subprocess.check_output(["gh","api",R+"actions/jobs/"+str(j["id"])+"/logs"]);assert rawlog
files={prefix+"run.json":enc(r),prefix+"jobs.json":enc(jobs),prefix+"job.log":rawlog,prefix+"artifacts.json":enc(api("actions/runs/"+str(run)+"/artifacts?per_page=100"))}
index={};chunks={}
for line in rawlog.decode().splitlines():
 if "NET459_COMPLETE_INDEX {"in line:
  d=json.loads(line.split("NET459_COMPLETE_INDEX ",1)[1]);assert d["name"]not in index;index[d["name"]]=d
 if "NET459_COMPLETE_CHUNK {"in line:
  d=json.loads(line.split("NET459_COMPLETE_CHUNK ",1)[1]);group=chunks.setdefault(d["name"],{});assert d["index"]not in group;group[d["index"]]=d
assert set(index)==set(chunks)
selected={}
for name,pin in index.items():
 path=PurePosixPath(name);assert len(path.parts)==1 and path.suffix in (".json",".stdout",".stderr")
 group=chunks[name];assert sorted(group)==list(range(pin["chunks"]))
 assert all(d["encoding"]=="zlib-base64"and all(d[k]==pin[k]for k in ("name","bytes","sha256","chunks"))for d in group.values())
 raw=zlib.decompress(b"".join(base64.b64decode(group[i]["base64"],validate=True)for i in range(pin["chunks"])))
 assert len(raw)==pin["bytes"]and sha(raw)==pin["sha256"]
 files[prefix+"observation/"+name]=raw;selected[name]=raw
files[prefix+"complete-output-index.json"]=enc(index)
summary=None
if r["conclusion"]=="success":
 assert set(selected)=={"context.json","controls.json","controls.stdout","controls.stderr","observation.json","observation.stdout","observation.stderr"}
 control=json.loads(selected["controls.json"]);obs=json.loads(selected["observation.json"]);ctx=dict(source=head,run=run,attempt=1)
 assert control["status"]=="PASS_NET459_CONNECTIVITY_SOURCE_CONTROLS"and(control["positive_count"],control["refusal_count"])==(11,10)and control["context"]==ctx
 assert obs["status"]=="PASS_NET459_DERIVED_CONNECTIVITY_OBSERVATION_ONLY"and obs["context"]==ctx
 assert selected["controls.stderr"]==selected["observation.stderr"]==b""
 assert set(obs["cases"])=={"positive_area","closed_boundary"}
 summary=dict(finding=obs["finding"],cases={mode:{label:dict(component_count=len(c["wire_components"]),all_pins_share_one_wire_component=c["all_pins_share_one_wire_component"],all_wire_material_one_component=c["all_wire_material_one_component"],components=[dict(index=x["index"],shape_count=len(x["shape_indices"]))for x in c["wire_components"]],pins=[dict(identity=p["scoped_identity"],components=p["wire_components"],ambiguous=p["ambiguous_multiple_wire_components"],missing=p["no_wire_access"])for p in c["pins"]])for label,c in pair.items()}for mode,pair in obs["cases"].items()},physical_acceptance=False,geometry_changed=False)
 for mode,pair in obs["cases"].items():
  for label,c in pair.items():
   assert len(c["source_shapes"])==139 and len(c["source_pins"])==5 and c["removed_shape_indices"]==([]if label=="original"else[21])
   assert all(c[k]is False for k in ("physical_acceptance","timing_accepted","full_phy_accepted","geometry_changed","native_acquisition","native_executed","pin_internal_connectivity_inferred"))
 files[prefix+"summary.json"]=enc(summary)
receipt=dict(schema="net459-connectivity-complete-terminal-v1",source=head,run=run,attempt=1,terminal=r["conclusion"],complete_job_log=True,complete_output_chunks=True,local_authored_execution=False,local_native_acquisition=False,physical_acceptance=False,geometry_changed=False,files={p:dict(bytes=len(b),sha256=sha(b))for p,b in files.items()})
files[prefix+"receipt.json"]=enc(receipt)
new=publish(head,files,"Preserve complete current net459 connectivity observation [skip ci]")
tree=api("git/trees/"+new+"?recursive=1");assert not tree["truncated"];by={x["path"]:x["sha"]for x in tree["tree"]if x["type"]=="blob"}
assert all(by[p]==hashlib.sha1(("blob "+str(len(b))+"\0").encode()+b).hexdigest()for p,b in files.items())
print(json.dumps(dict(head=new,run=run,terminal=r["conclusion"],files=len(files),bytes=sum(map(len,files.values())),receipt_sha256=sha(files[prefix+"receipt.json"]),summary=summary)))
