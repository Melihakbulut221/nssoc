# Already executed: proof87a5c5d82deed5f0bc651e30b83362dbd38ced98. Retained as provenance; do not rerun.
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
B="codex/cdr-current-access-overlay";head="f8d467382abef9a8180f04b233f93b181cdf88a3";run=40960276845
prefix="docs/evidence/cdr-current-access-overlay-terminal-"+str(run)+"/"
enc=lambda d:(json.dumps(d,sort_keys=True,indent=2)+"\n").encode()
assert api("git/ref/heads/"+B)["object"]["sha"]==head
r=api("actions/runs/"+str(run));jobs=api("actions/runs/"+str(run)+"/attempts/1/jobs?per_page=100")
assert (r["head_sha"],r["head_branch"],r["event"],r["run_attempt"],r["workflow_id"],r["status"])==(head,B,"workflow_dispatch",1,401118236,"completed")
assert len(jobs["jobs"])==3 and {j["name"]for j in jobs["jobs"]}=={"source-controls","preserve-job-log","readback"}
files={prefix+"run.json":enc(r),prefix+"jobs.json":enc(jobs),prefix+"artifacts.json":enc(api("actions/runs/"+str(run)+"/artifacts?per_page=100"))}
logs={}
for j in jobs["jobs"]:
 assert api("actions/jobs/"+str(j["id"]))==j and j["head_sha"]==head and j["status"]=="completed"
 files[prefix+"jobs/"+str(j["id"])+".json"]=enc(j)
 if j["conclusion"]=="skipped":continue
 raw=subprocess.check_output(["gh","api",R+"actions/jobs/"+str(j["id"])+"/logs"]);assert raw
 files[prefix+"jobs/"+str(j["id"])+".log"]=raw;logs[j["name"]]=raw
idx={};pieces={};controls={}
for line in logs["source-controls"].decode().splitlines():
 if "CDR_ACCESS_OVERLAY_CONTROL_INDEX {"in line:
  d=json.loads(line.split("CDR_ACCESS_OVERLAY_CONTROL_INDEX ",1)[1]);assert d["path"]not in idx;idx[d["path"]]=d
 if "CDR_ACCESS_OVERLAY_CONTROL_CHUNK {"in line:
  d=json.loads(line.split("CDR_ACCESS_OVERLAY_CONTROL_CHUNK ",1)[1]);c=pieces.setdefault(d["path"],{});assert d["index"]not in c;c[d["index"]]=base64.b64decode(d["base64"],validate=True)
assert set(idx)=={"context.json","controls.json","controls.stdout","controls.stderr"}
for name,pin in idx.items():
 c=pieces.get(name,{});assert sorted(c)==list(range(pin["chunks"]))
 raw=b"".join(c[i]for i in range(pin["chunks"]));assert len(raw)==pin["bytes"]and sha(raw)==pin["sha256"]
 if pin["present"]:files[prefix+"controls/"+name]=raw;controls[name]=raw
 else:assert not raw
files[prefix+"controls/index.json"]=enc(idx)
source_ok=next(j for j in jobs["jobs"]if j["name"]=="source-controls")["conclusion"]=="success"
report=json.loads(controls["controls.json"])if controls.get("controls.json")else None
if source_ok:
 assert report["status"]=="PASS_CURRENT_ACCESS_OVERLAY_SOURCE_CONTROLS"and report["passed"]is True
 assert report["counts"]==dict(positive=11,refusal=33,lifecycle=11)
 assert report["checker_finalization_count"]==5 and len(report["checker_finalization_cases"])==5
 assert report["original_archive_controls"]["counts"]==dict(positive=14,refusal=80,lifecycle=5)
 assert report["original_archive_controls"]["passed"]is True
 assert report["current_context"]==dict(source=head,run_id=run,attempt=1,source_controls_only=True,native_executed=False)
 assert report["native_executed"]is False and report["physical_acceptance"]is False
 assert controls["controls.stderr"]==b""
complete={};parts={};selected={}
for line in logs.get("readback",b"").decode().splitlines():
 if "CDR_ACCESS_COMPLETE_INDEX {"in line:
  d=json.loads(line.split("CDR_ACCESS_COMPLETE_INDEX ",1)[1]);assert d["name"]not in complete;complete[d["name"]]=d
 if "CDR_ACCESS_COMPLETE_CHUNK {"in line:
  d=json.loads(line.split("CDR_ACCESS_COMPLETE_CHUNK ",1)[1]);c=parts.setdefault(d["name"],{});assert d["index"]not in c;c[d["index"]]=d
assert set(complete)==set(parts)
for name,pin in complete.items():
 path=PurePosixPath(name)
 assert not path.is_absolute()and ".."not in path.parts and path.as_posix()==name and "\\"not in name
 assert path.suffix.lower()not in(".gds",".odb",".def",".lvsdb",".l2n",".gz",".zip",".appimage",".raw",".vcd")
 c=parts[name];assert sorted(c)==list(range(pin["chunks"]))
 assert all(d["encoding"]=="zlib-base64"and all(d[k]==pin[k]for k in("name","bytes","sha256","chunks"))for d in c.values())
 raw=zlib.decompress(b"".join(base64.b64decode(c[i]["base64"],validate=True)for i in range(pin["chunks"])))
 assert len(raw)==pin["bytes"]and sha(raw)==pin["sha256"]
 files[prefix+"readback/"+name]=raw;selected[name]=raw
files[prefix+"complete-readback-index.json"]=enc(complete)
tag="cloud-results-"+str(run)+"-1-cdr-current-access-overlay"
rel=api("releases/tags/"+tag);ref=api("git/ref/tags/"+tag)
assert rel["id"]==428427733 and rel["target_commitish"]==head and rel["draft"]is False and rel["prerelease"]is True and not rel["assets"]
assert ref["object"]["type"]=="commit"and ref["object"]["sha"]==head
files[prefix+"release.json"]=enc(rel);files[prefix+"ref.json"]=enc(ref)
summary=None
if r["conclusion"]=="success":
 result=json.loads(selected["cloud-cdr-access-overlay/readback-result.json"])
 overlay=json.loads(selected["cloud-cdr-access-overlay/overlay.json"])
 lifecycle=json.loads(selected["cloud-cdr-access-overlay/native-lifecycle.json"])
 census=json.loads(selected["cloud-cdr-access-overlay/complete-input-census.json"])
 assert result["status"]=="PASS_CURRENT_ACCESS_OVERLAY_READBACK_NOT_ACCEPTANCE"and result["complete_input_members"]==6647
 assert result["current_context"]==dict(source=head,run_id=run,attempt=1,group="cdr-current-access-overlay",token=str(run)+"-1")
 assert result["source_manifest_sha256"]=="7ea9306c6037396140c2994efc127cfc58192befd6e79f72fb6a56dd04bf4522"
 assert overlay["status"]=="PASS_CURRENT_ACCESS_GEOMETRIC_OBSERVATION_NOT_EDGE_ATTRIBUTION"
 assert overlay["native_counts"]==dict(devices=500,terminals=1446,wire_components=113,native_nets=238,ports=25)
 assert set(overlay["targets"])=={"28","124"}and all(len(t["points"])==102 and len(t["contacts"])==8 for t in overlay["targets"].values())
 assert all(v is False for v in overlay["scope"].values())and result["scope"]==overlay["scope"]
 assert not lifecycle["errors"]and lifecycle["primary_error"]is None and all(x["completed"]is True for x in lifecycle["actions"])
 assert json.loads(selected["cloud-cdr-access-overlay/native-api-controls.json"])==dict(status="PASS_PINNED_PYA_SYNTHETIC_POINT_CONTROLS",positive=5,synthetic_geometry=True,real_target_geometry_qualified=False)
 assert result["overlay"]==dict(bytes=len(selected["cloud-cdr-access-overlay/overlay.json"]),sha256=sha(selected["cloud-cdr-access-overlay/overlay.json"]))
 summary=dict(status=result["status"],source=head,run=run,complete_input_members=6647,native_counts=overlay["native_counts"],targets={k:dict(points=len(t["points"]),contacts=len(t["contacts"]),component=t["component"],native_name=t["native_name"])for k,t in overlay["targets"].items()},scope=overlay["scope"],missing=overlay["missing"])
 files[prefix+"summary.json"]=enc(summary)
receipt=dict(schema="cdr-current-access-overlay-complete-terminal-v1",run=run,source=head,attempt=1,terminal=r["conclusion"],source_controls_qualified=source_ok,source_report=report,summary=summary,complete_raw_job_logs=True,complete_derived_output_chunks=True,local_native_acquisition=False,physical_acceptance=False,full_phy_accepted=False,files={p:dict(bytes=len(b),sha256=sha(b))for p,b in files.items()})
files[prefix+"receipt.json"]=enc(receipt)
new=publish(head,files,"Preserve full current CDR access overlay hosted evidence [skip ci]")
tree=api("git/trees/"+new+"?recursive=1");assert not tree["truncated"];by={x["path"]:x["sha"]for x in tree["tree"]if x["type"]=="blob"}
assert all(by[p]==hashlib.sha1(("blob "+str(len(b))+"\0").encode()+b).hexdigest()for p,b in files.items())
print(json.dumps(dict(head=new,run=run,terminal=r["conclusion"],files=len(files),bytes=sum(map(len,files.values())),receipt_sha256=sha(files[prefix+"receipt.json"]),source_controls_qualified=source_ok,summary=summary)))
