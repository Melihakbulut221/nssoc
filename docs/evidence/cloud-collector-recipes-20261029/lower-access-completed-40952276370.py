# Already executed: proof24cfcd885c43458cebdbfba0362aefa48f27a064. Retained as provenance; do not rerun.
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
from concurrent.futures import ThreadPoolExecutor
from pathlib import PurePosixPath
B="codex/mainchip-lower-access-neighborhood-readback"
head="f85b2a8d8c21ec4cce35bb25bd5780ebe646022f"
run=40952276370
mode="readback"
prefix="docs/evidence/mainchip-lower-access-neighborhood-"+mode+"-terminal-"+str(run)+"/"
enc=lambda v:(json.dumps(v,sort_keys=True,indent=2)+"\n").encode()
assert api("git/ref/heads/"+B)["object"]["sha"]==head
r=api("actions/runs/"+str(run));jobs=api("actions/runs/"+str(run)+"/attempts/1/jobs?per_page=100")
assert (r["head_sha"],r["head_branch"],r["run_attempt"],r["status"],r["event"],r["workflow_id"])==(head,B,1,"completed","workflow_dispatch",401087037)
assert r["path"]==".github/workflows/mainchip-lower-access-neighborhood.yml"
assert len(jobs["jobs"])==3 and {j["name"]for j in jobs["jobs"]}=={"source-controls","preserve-job-log","readback"}
files={prefix+"run.json":enc(r),prefix+"jobs.json":enc(jobs),prefix+"artifacts.json":enc(api("actions/runs/"+str(run)+"/artifacts?per_page=100"))}
logs={}
for j in jobs["jobs"]:
 d=api("actions/jobs/"+str(j["id"]));assert d==j and j["status"]=="completed" and j["head_sha"]==head
 files[prefix+"jobs/"+str(j["id"])+".json"]=enc(j)
 if j["conclusion"]=="skipped":continue
 raw=subprocess.check_output(["gh","api",R+"actions/jobs/"+str(j["id"])+"/logs"]);assert raw
 files[prefix+"jobs/"+str(j["id"])+".log"]=raw;logs[j["name"]]=raw
idx={};chunks={}
for line in logs["source-controls"].decode().splitlines():
 if "LOWER_ACCESS_NEIGHBORHOOD_CONTROL_INDEX {"in line:
  d=json.loads(line.split("LOWER_ACCESS_NEIGHBORHOOD_CONTROL_INDEX ",1)[1]);assert d["path"]not in idx;idx[d["path"]]=d
 if "LOWER_ACCESS_NEIGHBORHOOD_CONTROL_CHUNK {"in line:
  d=json.loads(line.split("LOWER_ACCESS_NEIGHBORHOOD_CONTROL_CHUNK ",1)[1]);c=chunks.setdefault(d["path"],{});assert d["index"]not in c
  c[d["index"]]=base64.b64decode(d["base64"],validate=True)
assert set(idx)=={"context.json","controls.json","controls.stdout","controls.stderr"}
controls={}
for name,d in idx.items():
 c=chunks.get(name,{});assert sorted(c)==list(range(d["chunks"]))
 raw=b"".join(c[i]for i in range(d["chunks"]));assert len(raw)==d["bytes"]and sha(raw)==d["sha256"]
 if d["present"]:files[prefix+"controls/"+name]=raw;controls[name]=raw
 else:assert not raw
files[prefix+"controls/index.json"]=enc(idx)
source_ok=next(j for j in jobs["jobs"]if j["name"]=="source-controls")["conclusion"]=="success"
report=json.loads(controls["controls.json"])if controls.get("controls.json")else None
if source_ok:
 assert report["status"]=="PASS_LOWER_ACCESS_NEIGHBORHOOD_SOURCE_CONTROLS"
 assert (report["positive_count"],report["refusal_count"],report["lifecycle_count"])==(3,17,13)
 assert (report["lower_access"]["positive_count"],report["lower_access"]["refusal_count"])==(9,18)
 assert report["lower_access"]["actual_native_function_bodies"]is True and report["lower_access"]["all_track_objects_synthetic"]is True
 assert report["lower_access"]["native_imports_executed"]is False and report["lower_access"]["native_track_api_qualified"]is False
 ctx=report["current_context"]
 assert (ctx["source"],ctx["run_id"],ctx["attempt"],ctx["group"])==(head,run,1,"mainchip-lower-access-neighborhood")
 assert report["native_archive_acquired"]is False and report["native_executed"]is False and report["physical_acceptance"]is False
 assert json.loads(controls["controls.stdout"])==report and controls["controls.stderr"]==b""
selected={};readback=None
if mode=="controls":
 assert next(j for j in jobs["jobs"]if j["name"]=="readback")["conclusion"]=="skipped"


else:
 aggregate=None;parts={}
 for line in logs.get("readback",b"").decode().splitlines():
  if "LOWER_ACCESS_NEIGHBORHOOD_INDEX {"in line:
   assert aggregate is None;aggregate=json.loads(line.split("LOWER_ACCESS_NEIGHBORHOOD_INDEX ",1)[1])
  if "LOWER_ACCESS_NEIGHBORHOOD_CHUNK {"in line:
   d=json.loads(line.split("LOWER_ACCESS_NEIGHBORHOOD_CHUNK ",1)[1])
   assert d["encoding"]=="zlib-base64"
   group=parts.setdefault(d["name"],{});assert d["index"]not in group;group[d["index"]]=d
 if aggregate is not None:
  assert set(parts)==set(aggregate)
  for name,pin in aggregate.items():
   path=PurePosixPath(name)
   assert not path.is_absolute()and ".."not in path.parts and path.as_posix()==name and "\\"not in name
   assert path.suffix in (".json",".jsonl",".stdout",".stderr",".lef")or(".json."in path.name and path.name.endswith(".tmp")),"native payload refused"
   group=parts[name];count=next(iter(group.values()))["chunks"]
   assert sorted(group)==list(range(count))
   assert all(x["chunks"]==count and x["bytes"]==pin["bytes"]and x["sha256"]==pin["sha256"]for x in group.values())
   raw=zlib.decompress(b"".join(base64.b64decode(group[i]["base64"],validate=True)for i in range(count)))
   assert len(raw)==pin["bytes"]and sha(raw)==pin["sha256"];raw.decode()
   files[prefix+"readback/"+name]=raw;selected[name]=raw
  files[prefix+"readback-index.json"]=enc(aggregate)
 if "result.json"in selected:readback=json.loads(selected["result.json"])
 tag="cloud-results-"+str(run)+"-1-mainchip-lower-access-neighborhood"
 rel=api("releases/tags/"+tag);ref=api("git/ref/tags/"+tag)
 assert rel["id"]==428379831 and rel["tag_name"]==tag and rel["target_commitish"]==head
 assert rel["draft"]is False and rel["prerelease"]is True and not rel["assets"]
 assert ref["object"]["type"]=="commit"and ref["object"]["sha"]==head
 files[prefix+"release.json"]=enc(rel);files[prefix+"ref.json"]=enc(ref)
 if r["conclusion"]=="success":
  assert readback["status"]=="PASS_LOWER_ACCESS_SERIALIZED_NEIGHBORHOOD_READBACK_ONLY"and not readback["terminal_errors"]
  assert (readback["source"],readback["run_id"])==(head,run)
  assert readback["native_readback_complete"]and readback["output_preservation"]["complete"]
  assert all(readback[k]is False for k in ("physical_acceptance","timing_accepted","full_phy_accepted"))
  input_proof=json.loads(selected["current-input-restoration.json"])
  assert input_proof["full_archive_verified"]and len(input_proof["full_members"])==145
  assert sum(x["bytes"]for x in input_proof["full_members"].values())==5763445029
  current=dict(bytes=213429713,sha256="47d657f41565f5c379a9152672eac824a5d296043c3726527031452ad2097677")
  assert input_proof["current_input"]==current
  native=json.loads(selected["native/lower-access-neighborhood/result.json"])
  assert native["status"]=="PASS_LOWER_ACCESS_SERIALIZED_NEIGHBORHOOD_OBSERVATION_ONLY"and native["input"]==current
  assert native["unchanged_source"]and native["database_destroyed"]
  assert all(native[k]is False for k in ("physical_acceptance","timing_accepted","full_phy_accepted","geometry_changed","routing_started","clearance_qualified"))
  neighborhood=json.loads(selected["native/lower-access-neighborhood/neighborhood.json"])
  assert neighborhood["source_database"]==current and neighborhood["read_only"]is True
  assert neighborhood["all_net_count"]==143820 and neighborhood["instance_count"]==153130
  assert neighborhood["observation_window_dbu"]==[937420,1713500,957620,1800560]
  assert neighborhood["all_layers_observed"]is True and neighborhood["rule_expanded_window_qualified"]is False
  assert set(neighborhood["full_source_material"])=={"net459","net36993","clknet_5_29__leaf_u_ibex.clk"}
  tech=selected["native/lower-access-neighborhood/current-tech.lef"]
  assert neighborhood["embedded_technology_lef"]==dict(bytes=len(tech),sha256=sha(tech))
  tracks_raw=selected["native/lower-access-neighborhood/track-grids.json"]
  tracks=json.loads(tracks_raw)
  assert neighborhood["track_grid_observation"]["file"]==dict(bytes=len(tracks_raw),sha256=sha(tracks_raw))
  assert tracks["source_database"]==current and tracks["observation_window_dbu"]==[937420,1713500,957620,1800560]
  assert tracks["read_only"]is True and tracks["clearance_qualified"]is False and tracks["off_track_routing_qualified"]is False
  if tracks["complete"]:
   assert tracks["status"]=="TRACK_GRID_PATTERNS_OBSERVED_NOT_CLEARANCE"and tracks["numeric_tracks_exported"]is True
   assert len(tracks["grids"])==tracks["grid_count"]and not tracks["errors"]
  else:
   assert tracks["status"]=="TRACK_GRID_API_AVAILABILITY_ONLY"and tracks["numeric_tracks_exported"]is False and not tracks["grids"]
  prior_raw=remote("docs/evidence/mainchip-current-neighborhood-readback-terminal-40930102746/readback/native/current-neighborhood/neighborhood.json","f9d2b1b1378c33f1281f6bd0ca582cac07c1ba2b")
  prior=json.loads(prior_raw)
  keys=("source_database","current_source_identities","full_source_material","native_geometry_census","native_geometry_sha256","complete_raw_opcode_data_pairs","complete_raw_wire_sha256","all_net_count","instance_count","embedded_technology_lef")
  assert all(neighborhood[k]==prior[k]for k in keys)
  files[prefix+"prior-current-readback-comparison.json"]=enc(dict(prior_run=40930102746,prior_sha256=sha(prior_raw),equal_keys=list(keys),prior_window=prior["observation_window_dbu"],current_window=neighborhood["observation_window_dbu"],current_records=len(neighborhood["records"]),tracks_status=tracks["status"],geometry_changed=False,physical_acceptance=False,timing_accepted=False))
  for name,pin in readback["output_preservation"]["copied"].items():
   raw=selected["native/"+name];assert pin==dict(bytes=len(raw),sha256=sha(raw))
  assert '"removed_owned_workspace": true'in logs["readback"].decode()

receipt=dict(schema="lower-access-neighborhood-cloud-terminal-v1",source=head,run=run,attempt=1,mode=mode,terminal=r["conclusion"],
 source_controls_qualified=source_ok,source_report=report,readback=readback,complete_raw_job_logs=True,
 local_native_payload_acquisition=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
 files={n:dict(bytes=len(b),sha256=sha(b))for n,b in files.items()})
files[prefix+"receipt.json"]=enc(receipt)
new=publish(head,files,"Preserve lower-access-neighborhood "+mode+" complete hosted terminal evidence [skip ci]")
tree=api("git/trees/"+new+"?recursive=1");assert not tree["truncated"]
by={x["path"]:x["sha"]for x in tree["tree"]if x["type"]=="blob"}
assert all(by[n]==hashlib.sha1(("blob "+str(len(b))+"\0").encode()+b).hexdigest()for n,b in files.items())
print(json.dumps(dict(head=new,run=run,mode=mode,terminal=r["conclusion"],files=len(files),bytes=sum(map(len,files.values())),receipt_sha256=sha(files[prefix+"receipt.json"]),source_controls_qualified=source_ok,readback_status=readback.get("status")if readback else None)))
