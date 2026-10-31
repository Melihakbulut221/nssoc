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
B="codex/cdr-drain-m1-loaded-electrical";RUN=41197248029;SOURCE="06a7360e86d97f432e104be4276d5fdf993eb737"
PREFIX="docs/evidence/cdr-current-wire-ownership-execution-41197248029/"
files={};pins={}
def keep(name,raw):
 assert name not in pins
 files[PREFIX+name]=raw;pins[name]=dict(bytes=len(raw),sha256=sha(raw))
def enc(v):return(json.dumps(v,sort_keys=True,indent=2)+"\n").encode()
def get(path,name):
 raw=subprocess.check_output(["gh","api",R+path]);keep(name,raw);return json.loads(raw)
r=get("actions/runs/"+str(RUN),"run.json")
assert r["status"]=="completed"and r["head_sha"]==SOURCE and r["run_attempt"]==1 and r["workflow_id"]==401118236
jobs=get("actions/runs/"+str(RUN)+"/attempts/1/jobs?per_page=100","jobs.json")["jobs"]
assert len(jobs)==4 and {x["name"]for x in jobs}=={"source-controls","preserve-job-log","ownership","preserve-ownership-job-logs"}
logs={}
for listed in jobs:
 j=get("actions/jobs/"+str(listed["id"]),"jobs/"+str(listed["id"])+".json")
 assert j["status"]=="completed"and j["head_sha"]==SOURCE and j["run_id"]==RUN
 raw=subprocess.check_output(["gh","api",R+"actions/jobs/"+str(j["id"])+"/logs"]);assert raw
 keep("logs/"+str(j["id"])+".log",raw);logs[j["name"]]=raw
expected={"context.json","controls.json","controls.stdout","controls.stderr","publication-controls.json",
 "publication-controls.stdout","publication-controls.stderr","ownership-manifest.json","ownership-controls.json",
 "ownership-controls.stdout","ownership-controls.stderr","execution-manifest.json","execution-controls.json","execution-controls.stdout","execution-controls.stderr"}
index={};chunks={}
for line in logs["source-controls"].decode().splitlines():
 for marker,isindex in(("CDR_DRAIN_WAVE_SOURCE_INDEX ",True),("CDR_DRAIN_WAVE_SOURCE_CHUNK ",False)):
  if marker not in line:continue
  text=line.split(marker,1)[1]
  if not text.startswith("{"):continue
  d=json.loads(text);name=d["path"];assert name in expected
  if isindex:assert name not in index;index[name]=d
  else:
   group=chunks.setdefault(name,{});assert type(d["index"])is int and d["index"]not in group;group[d["index"]]=d
assert set(index)==expected
records={}
for name,pin in index.items():
 parts=chunks.get(name,{})
 assert set(parts)==set(range(pin["chunks"]))
 raw=b"".join(base64.b64decode(parts[i]["base64"],validate=True)for i in range(pin["chunks"]))
 assert len(raw)==pin["bytes"]and sha(raw)==pin["sha256"]
 if pin["present"]:keep("source-records/"+name,raw);records[name]=raw
keep("source-index.json",enc(index))
context=json.loads(records["context.json"]);assert context["source"]==SOURCE and context["run_id"]==RUN and context["attempt"]==1
controls=json.loads(records["controls.json"]);pub=json.loads(records["publication-controls.json"])
assert controls["status"]=="PASS_DRAIN_M1_WAVE_REPLAY_SOURCE_CONTROLS"and controls["passed"]is True
assert controls["counts"]==dict(groups=8,refusals=47,lifecycle=4)
assert pub["status"]=="PASS_COMPLETE_REPLAY_PUBLICATION_CONTROLS"and pub["passed"]is True
assert pub["counts"]==dict(positive=7,refusals=33,lifecycle=4)
own=json.loads(records.get("ownership-controls.json",b"null"))
passed=next(x["conclusion"]for x in jobs if x["name"]=="source-controls")=="success"
if passed:
 assert own["status"]=="PASS_CURRENT_CDR_WIRE_OWNERSHIP_SOURCE_CONTROLS"and own["count"]==33 and len(set(own["passed_cases"]))==33
 assert own["source"]==SOURCE and own["run_id"]==RUN and own["attempt"]==1
 assert own["actual_native_inputs_acquired"]is False and own["actual_model_analyzed"]is False
import zlib
from pathlib import PurePosixPath
execution=json.loads(records["execution-controls.json"])
assert execution["count"]==29 and execution["source"]==SOURCE and execution["run_id"]==RUN and execution["attempt"]==1
native_index=None;chunks={};ends={};publication=None
for line in logs["ownership"].decode().splitlines():
 for marker,kind in (("CDR_DRAIN_REPLAY_INDEX ","index"),("CDR_DRAIN_REPLAY_CHUNK ","chunk"),("CDR_DRAIN_REPLAY_END ","end"),("CDR_OWNERSHIP_PUBLICATION ","publication")):
  if marker not in line:continue
  t=line.split(marker,1)[1]
  if not t.startswith("{"):continue
  d=json.loads(t)
  if kind=="index":assert native_index is None;native_index=d
  elif kind=="end":assert d["name"]not in ends;ends[d["name"]]=d
  elif kind=="publication":assert publication is None;publication=d
  else:
   g=chunks.setdefault(d["name"],{})
   assert d["encoding"]=="zlib+base64"and type(d["index"])is int and d["index"]not in g
   g[d["index"]]=d
assert native_index is not None and set(native_index)==set(chunks)==set(ends)
native_records={}
for name,pin in native_index.items():
 p=PurePosixPath(name);assert not p.is_absolute()and str(p)==name and ".."not in p.parts and p.suffix==".json"
 end=ends[name];g=chunks[name];assert set(g)==set(range(end["chunks"]))
 raw=zlib.decompress(b"".join(base64.b64decode(g[i]["data"],validate=True)for i in range(end["chunks"])))
 assert dict(bytes=len(raw),sha256=sha(raw))==pin=={k:end[k]for k in ("bytes","sha256")}
 keep("native-derived/"+name,raw);native_records[name]=raw
keep("native-index.json",enc(native_index));keep("native-publication.json",enc(publication))
result=json.loads(native_records["result.json"]);analysis=json.loads(native_records["current-wire-ownership-analysis.json"])
assert r["conclusion"]=="success"and all(j["conclusion"]=="success"for j in jobs)
assert result["status"]=="COMPLETE_CURRENT_CDR_WIRE_OWNERSHIP_DIAGNOSIS_ONLY"and result["completed_pairs"]==34
assert result["actual_model_analyzed"]is True and result["actual_native_inputs_acquired"]is True
assert result["original_electrical_rejection_preserved"]is True and result["terminal_errors"]==[]
assert result["original_electrical_status"]=="REJECTED_WHOLE_MIM_PD500_LOADED"
assert result["input_census"]==dict(full_members=2797,selected=36,native_inputs_retained_in_bundle=True)
assert len(analysis["evaluations"])==34 and len([p for p in native_records if p.startswith("wire-solve-")])==34
assert all(result[k]is False for k in ("physical_acceptance","timing_accepted","full_phy_accepted","electrical_accepted","qualified_pex","causality_proven","geometry_changed","new_simulation"))
integrity=json.loads(native_records["terminal-integrity.json"]);assert all(x["complete"]for x in integrity.values())
release=get("releases/429895559","release.json")
tag="cloud-results-41197248029-1-cdr-current-wire-ownership-nominal_early"
ref=get("git/ref/tags/"+tag,"tag-ref.json")
assert release["tag_name"]==tag and release["target_commitish"]==SOURCE and release["draft"]is False and release["prerelease"]is True
assert ref["object"]["type"]=="commit"and ref["object"]["sha"]==SOURCE
assets={a["name"]:a for a in release["assets"]};assert len(assets)==len(release["assets"])
stem="cdr-current-wire-ownership-nominal_early-41197248029-1"
metadata={}
for name in ("complete-output-index.json",stem+".parts.json"):
 a=assets[name];raw=subprocess.check_output(["gh","api",R+"releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"])
 assert a["state"]=="uploaded"and a["size"]==len(raw)and a["digest"]=="sha256:"+sha(raw)
 keep("capsule-metadata/"+name,raw);metadata[name]=json.loads(raw)
output=metadata["complete-output-index.json"];parts=metadata[stem+".parts.json"]
assert output["schema"]=="complete-current-cdr-wire-ownership-output-index-v1"
assert output["context"]["source"]==SOURCE and output["context"]["run"]==RUN and output["context"]["attempt"]==1
assert output["actual_capture_replayed"]is False and output["read_only_wire_diagnosis_is_not_electrical_acceptance"]is True
assert publication["receipt"]["complete"]is True and publication["receipt"]["creation_attempted"]is False and publication["receipt"]["overwrites"]is False
assert publication["complete_files"]==len(output["files"])and publication["archive"]=={k:parts[k]for k in("bytes","sha256")}
assert sum(p["bytes"]for p in parts["parts"])==parts["bytes"]
assert set(assets)=={p["name"]for p in parts["parts"]}|set(metadata)
for p in parts["parts"]:
 a=assets[p["name"]];assert a["state"]=="uploaded"and a["size"]==p["bytes"]and a["digest"]=="sha256:"+p["sha256"]
for name,pin in native_index.items():assert output["files"]["evidence/"+name]==pin
census=json.loads(native_records["complete-input-census.json"])
assert census["full_member_count"]==2797 and census["every_member_authenticated"]is True and len(census["selected"])==36
for name,pin in census["selected"].items():assert output["files"]["native-inputs/"+name]==pin
paths=["scripts/cloud_cdr_current_wire_ownership.py","scripts/check_cdr_current_wire_ownership_execution.py",
 "scripts/cdr-current-wire-ownership-execution-pins.json","scripts/analyze_cdr_current_wire_ownership.py","scripts/check_cdr_current_wire_ownership.py",
 "scripts/cdr-current-wire-ownership-inputs.json","scripts/cdr-current-wire-ownership-source-pins.json",
 "scripts/analyze_cdr_wire_resistance.py","scripts/cloud_cdr_drain_m1_fresh_mim_precision.py",
 ".github/workflows/cdr-current-access-overlay.yml"]
with ThreadPoolExecutor(max_workers=4)as pool:sources=dict(zip(paths,pool.map(lambda p:remote(p,SOURCE),paths)))
manifest=json.loads(sources["scripts/cdr-current-wire-ownership-source-pins.json"])
assert len(manifest["files"])==80 and manifest["native_acquisition_authorized"]is False
for path,raw in sources.items():
 if path in manifest["files"]:assert dict(bytes=len(raw),sha256=sha(raw))==manifest["files"][path]
 keep("tested-source/"+path,raw)
receipt=dict(schema="cdr-current-wire-ownership-actual-cloud-diagnosis-terminal-v1",run=RUN,source=SOURCE,attempt=1,
 workflow_conclusion=r["conclusion"],source_controls_passed=passed,original_replay_controls=59,
 original_publication_controls=44,new_ownership_result=own,execution_controls=execution,source_control_total=165,raw_job_logs=len(logs),source_records=len(records),
 actual_native_inputs_acquired=True,actual_model_analyzed=True,completed_pairs=34,actual_result=result,
 complete_native_capsule_preserved=True,capsule_files=len(output["files"]),capsule_archive=publication["archive"],
 native_payload_downloaded_locally=False,independent_output_archive_reextraction=False,
 physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,files=pins.copy())
keep("receipt.json",enc(receipt))
head=api("git/ref/heads/"+B)["object"]["sha"];assert head==SOURCE
tree=api("git/trees/"+head+"?recursive=1");assert not tree["truncated"]and not any(x["path"].startswith(PREFIX)for x in tree["tree"])
commit=publish(head,files,"Preserve complete actual precise CDR wire ownership diagnosis and authentic native capsule [skip ci]")
summary=dict(proof=commit,prefix=PREFIX,run=RUN,source=SOURCE,files=len(files),bytes=sum(map(len,files.values())),
 receipt_sha256=sha(files[PREFIX+"receipt.json"]),source_controls_passed=passed,
 original_controls_passed=103,total_controls=165,actual_model_analyzed=True,completed_pairs=34,
 native_records=len(native_records),capsule_files=len(output["files"]),capsule_archive=publication["archive"],workflow_conclusion=r["conclusion"],raw_job_logs=len(logs),source_records=len(records))
print("RESULT_JSON:"+json.dumps(dict(summary,phase="published")),flush=True)
with ThreadPoolExecutor(max_workers=4)as pool:
 for path,raw in zip(files,pool.map(lambda p:remote(p,commit),files)):assert raw==files[path],path
print("RESULT_JSON:"+json.dumps(dict(summary,phase="readback_verified",all_files_verified=True)),flush=True)
