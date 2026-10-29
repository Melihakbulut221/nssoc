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
B="codex/cdr-current-dc-contact-screen";head="8dbc4bab41994e03bebf6fca40d13228c6494ada";run=40945858067
prefix="docs/evidence/cdr-current-dc-contact-screen-terminal-"+str(run)+"/"
enc=lambda v:(json.dumps(v,sort_keys=True,indent=2)+"\n").encode()
assert api("git/ref/heads/"+B)["object"]["sha"]==head
r=api("actions/runs/"+str(run));jobs=api("actions/runs/"+str(run)+"/attempts/1/jobs?per_page=100")
assert (r["head_sha"],r["head_branch"],r["run_attempt"],r["status"],r["event"],r["workflow_id"])==(head,B,1,"completed","workflow_dispatch",401046335)
assert r["path"]==".github/workflows/cdr-current-dc-contact-screen.yml"
assert len(jobs["jobs"])==3 and {j["name"]for j in jobs["jobs"]}=={"source-controls","preserve-job-log","screen"}
files={prefix+"run.json":enc(r),prefix+"jobs.json":enc(jobs),prefix+"artifacts.json":enc(api("actions/runs/"+str(run)+"/artifacts?per_page=100"))}
logs={}
for j in jobs["jobs"]:
 assert api("actions/jobs/"+str(j["id"]))==j and j["status"]=="completed"and j["head_sha"]==head
 files[prefix+"jobs/"+str(j["id"])+".json"]=enc(j)
 if j["conclusion"]=="skipped":continue
 raw=subprocess.check_output(["gh","api",R+"actions/jobs/"+str(j["id"])+"/logs"]);assert raw
 files[prefix+"jobs/"+str(j["id"])+".log"]=raw;logs[j["name"]]=raw
idx={};chunks={}
for line in logs["source-controls"].decode().splitlines():
 if "CURRENT_DC_CONTROL_INDEX {"in line:
  d=json.loads(line.split("CURRENT_DC_CONTROL_INDEX ",1)[1]);assert d["path"]not in idx;idx[d["path"]]=d
 if "CURRENT_DC_CONTROL_CHUNK {"in line:
  d=json.loads(line.split("CURRENT_DC_CONTROL_CHUNK ",1)[1]);c=chunks.setdefault(d["path"],{});assert d["index"]not in c
  c[d["index"]]=base64.b64decode(d["base64"],validate=True)
assert set(idx)=={"context.json","controls.json","controls.stdout","controls.stderr"}
controls={}
for name,d in idx.items():
 c=chunks.get(name,{});assert sorted(c)==list(range(d["chunks"]))
 raw=b"".join(c[i]for i in range(d["chunks"]));assert len(raw)==d["bytes"]and sha(raw)==d["sha256"]
 if d["present"]:files[prefix+"controls/"+name]=raw;controls[name]=raw
 else:assert not raw
files[prefix+"controls/index.json"]=enc(idx)
report=json.loads(controls["controls.json"])if controls.get("controls.json")else None
source_ok=next(j for j in jobs["jobs"]if j["name"]=="source-controls")["conclusion"]=="success"
if source_ok:
 assert report["status"]=="PASS_CURRENT_DC_CONTACT_SOURCE_CONTROLS"and report["counts"]==dict(positive=10,refusal=52,lifecycle=5)
 assert (report["current_context"]["source"],report["current_context"]["run_id"],report["current_context"]["attempt"])==(head,run,1)
 assert report["all_computed_networks_synthetic"]is True and report["authentic_network_solve_executed"]is False
 assert all(report[k]is False for k in("physical_acceptance","electrical_acceptance","full_phy_accepted","native_archive_acquired","native_CAD_executed"))
 assert json.loads(controls["controls.stdout"])==report and not controls["controls.stderr"]
aggregate=None;parts={};selected={}
for line in logs.get("screen",b"").decode().splitlines():
 if "CURRENT_DC_CONTACT_INDEX {"in line:
  assert aggregate is None;aggregate=json.loads(line.split("CURRENT_DC_CONTACT_INDEX ",1)[1])
 if "CURRENT_DC_CONTACT_CHUNK {"in line:
  d=json.loads(line.split("CURRENT_DC_CONTACT_CHUNK ",1)[1]);assert d["encoding"]=="zlib-base64"
  group=parts.setdefault(d["name"],{});assert d["index"]not in group;group[d["index"]]=d
if aggregate is not None:
 assert set(parts)==set(aggregate)
 for name,pin in aggregate.items():
  path=PurePosixPath(name)
  assert path.as_posix()==name and not path.is_absolute()and ".."not in path.parts and "\\"not in name and path.suffix==".json","non-derived payload refused"
  group=parts[name];count=next(iter(group.values()))["chunks"]
  assert sorted(group)==list(range(count))
  assert all(d["chunks"]==count and d["bytes"]==pin["bytes"]and d["sha256"]==pin["sha256"]for d in group.values())
  raw=zlib.decompress(b"".join(base64.b64decode(group[i]["base64"],validate=True)for i in range(count)))
  assert len(raw)==pin["bytes"]and sha(raw)==pin["sha256"];json.loads(raw)
  files[prefix+"screen/"+name]=raw;selected[name]=raw
 files[prefix+"screen-index.json"]=enc(aggregate)
result=json.loads(selected["result.json"])if "result.json"in selected else None
if r["conclusion"]=="success":
 assert result["status"]=="PASS_CURRENT_DC_CONTACT_SCREEN_NOT_ELECTRICAL_ACCEPTANCE"
 assert (result["context"]["source"],result["context"]["run_id"],result["context"]["attempt"])==(head,run,1)
 assert set(result["networks"])=={"28","124"}and result["DC_analysis_only"]is True
 assert all(result[k]is False for k in("native_archive_acquired","native_CAD_executed","geometry_changed","transient_recovery_proven","geometric_bridge_attribution_proven","physical_acceptance","electrical_acceptance","full_phy_accepted"))
 assert sha(selected["inputs/incidence-and-technology.json"])=="c5d764256c577b2fc14dac22de72144c38049f85f20a20038e9a81fa4d8af110"
 assert sha(selected["inputs/receipt.json"])=="dbd561e3eb1082a4b24552c7b72a32ab28fb6830a052e6ee172b7f07e93fa5ba"
 original=json.loads(selected["inputs/incidence-and-technology.json"])
 for key,pin in result["networks"].items():
  raw=selected[pin["file"]];n=json.loads(raw)
  assert len(raw)==pin["bytes"]and sha(raw)==pin["sha256"]
  assert (pin["node_count"],pin["contact_count"],pin["basis_count"],pin["pair_count"])==(102,8,7,28)
  assert n["original_target"]==original["targets"][key]
  assert n["omitted_capacitor_count"]==114 and n["capacitor_omission_is_not_valid_for_original_transient"]is True
  assert len(n["contact_impedance_ohm"])==8 and len(n["effective_resistance_ohm"])==8
  assert len(n["reciprocity_checks"])==28 and len(n["multi_terminal_pair_checks"])==28
  for case in n["reference_unit_injections"]+n["pair_unit_injections"]:
   assert len(case["node_voltages_V"])==102 and len(case["edge_responses"])==145 and len(case["checks"]["KCL_residual_A"])==102
 for name,pin in result["available_outputs"].items():
  raw=selected[name];assert pin==dict(bytes=len(raw),sha256=sha(raw))
receipt=dict(schema="current-dc-contact-cloud-terminal-v1",source=head,run=run,attempt=1,terminal=r["conclusion"],
 source_controls_qualified=source_ok,source_controls=report,screen=result,complete_raw_job_logs=True,
 local_native_payload_acquisition=False,local_authored_computation=False,
 physical_acceptance=False,electrical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
 files={n:dict(bytes=len(b),sha256=sha(b))for n,b in files.items()})
files[prefix+"receipt.json"]=enc(receipt)
new=publish(head,files,"Preserve complete hosted DC contact matrices and all original edge responses [skip ci]")
tree=api("git/trees/"+new+"?recursive=1");assert not tree["truncated"]
by={x["path"]:x["sha"]for x in tree["tree"]if x["type"]=="blob"}
assert all(by[n]==hashlib.sha1(("blob "+str(len(b))+"\0").encode()+b).hexdigest()for n,b in files.items())
print(json.dumps(dict(head=new,run=run,terminal=r["conclusion"],files=len(files),bytes=sum(map(len,files.values())),receipt_sha256=sha(files[prefix+"receipt.json"]),source_controls_qualified=source_ok,screen_status=result.get("status")if result else None)))
