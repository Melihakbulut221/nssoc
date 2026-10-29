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

from concurrent.futures import ThreadPoolExecutor
from pathlib import PurePosixPath
RUN=40906725656
SOURCE="e191424507e67331b2e79800caece4a3f03a1cc0"
B="codex/cdr-width-loaded-execution-unit"
PREFIX="docs/evidence/cdr-width-loaded-native-terminal-40906725656/"
CASES=("nominal_early","nominal_late","hot_early","hot_late","cold_early","cold_late","constant_zero","constant_one","clock_stopped","vi_bias_off")
RELEASES=dict(zip(CASES+( "preparation",),(428084403,428084480,428084532,428084588,428084626,428084684,428084741,428084787,428084822,428084880,428084945)))
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
assert api("git/ref/heads/"+B)["object"]["sha"]==SOURCE
r=api(f"actions/runs/{RUN}")
jobs=api(f"actions/runs/{RUN}/attempts/1/jobs?per_page=100")
assert (r["head_sha"],r["head_branch"],r["run_attempt"],r["status"],r["event"],r["workflow_id"])==(SOURCE,B,1,"completed","workflow_dispatch",400799746)
assert r["path"]==".github/workflows/cdr-width-loaded-cloud.yml"
rows=jobs["jobs"]
expected_names={"source-controls","preserve-job-log","prepare"}|{"loaded ("+c+")"for c in CASES}
assert {j["name"]for j in rows}==expected_names and len(rows)==13
assert all(j["head_sha"]==SOURCE and j["run_attempt"]==1 and j["run_id"]==RUN and j["status"]=="completed"for j in rows)
files={PREFIX+"run.json":enc(r),PREFIX+"jobs.json":enc(jobs),PREFIX+"artifacts.json":enc(api(f"actions/runs/{RUN}/artifacts?per_page=100"))}
def read_job(j):
 d=api("actions/jobs/"+str(j["id"]));assert d==j
 raw=b""if j["conclusion"]=="skipped"else subprocess.check_output(["gh","api",R+"actions/jobs/"+str(j["id"])+"/logs"])
 if j["conclusion"]!="skipped":assert raw
 return j,raw
with ThreadPoolExecutor(4)as ex:jobdata=list(ex.map(read_job,rows))
def records(raw,mark,base):
 idx={};chunks={};result={}
 for line in raw.decode().splitlines():
  if mark+"_INDEX {"in line:
   d=json.loads(line.split(mark+"_INDEX ",1)[1]);assert d["path"]not in idx;idx[d["path"]]=d
  if mark+"_CHUNK {"in line:
   d=json.loads(line.split(mark+"_CHUNK ",1)[1]);v=chunks.setdefault(d["path"],{});assert d["index"]not in v
   v[d["index"]]=base64.b64decode(d["base64"],validate=True)
 for path,d in idx.items():
  p=PurePosixPath(path);assert not p.is_absolute()and ".."not in p.parts
  v=chunks.get(path,{});assert sorted(v)==list(range(d["chunks"]))
  b=b"".join(v[i]for i in range(d["chunks"]));assert len(b)==d["bytes"]and sha(b)==d["sha256"]
  if d["present"]:files[base+path]=b;result[path]=b
  else:assert not b
 if idx:files[base+"indexed-records.json"]=enc(idx)
 return idx,result
native={};source_values={}
for j,raw in jobdata:
 base=PREFIX+"jobs/"+str(j["id"])+"/"
 files[base+"job.json"]=enc(j)
 if not raw:continue
 files[base+"job.log"]=raw
 if j["name"]=="source-controls":
  source_index,source_values=records(raw,"WIDTH_CURRENT_LOADED",base+"records/")
 elif j["name"]!="preserve-job-log":
  idx,values=records(raw,"WIDTH_CURRENT_NATIVE",base+"records/")
  if j["conclusion"]=="success":assert len(idx)==len(values)==6
  suffix="preparation"if j["name"]=="prepare"else j["name"][8:-1]
  assert suffix in RELEASES;native[suffix]=(j,idx,values)
method_raw=remote("scripts/cdr-width-loaded-execution-methods.json",SOURCE)
assert sha(method_raw)=="119b7a2d35abb1163570d01b8af16d18c6d9401e839a38904863d8b42eecef67"
method=json.loads(method_raw)
source_ok=next(j for j in rows if j["name"]=="source-controls")["conclusion"]=="success"
if source_ok:
 assert set(source_values)=={"context.json","execution.json","execution.stdout","execution.stderr","publication.json","publication.stdout","publication.stderr","imports.json","imports.stdout","imports.stderr"}
 ctx=json.loads(source_values["context.json"])
 assert (ctx["source"],ctx["run_id"],ctx["attempt"],ctx["method_sha256"],ctx["requested_mode"],ctx["native_authorized"])==(SOURCE,RUN,1,sha(method_raw),"loaded",True)
 statuses={"execution":"PASS_WIDTH_LOADED_EXECUTION_SOURCE_CONTROLS","publication":"PASS_WIDTH_LOADED_FAILURE_PUBLICATION_SOURCE_CONTROLS","imports":"PASS_WIDTH_LOADED_ACTUAL_IMPORT_SOURCE_CONTROLS"}
 common=dict(source=SOURCE,run_id=RUN,attempt=1,source_controls_only=True,native_executed=False)
 for name,status in statuses.items():
  report=json.loads(source_values[name+".json"]);assert report["status"]==status and report["current_context"]==common
  assert source_values[name+".stdout"]==source_values[name+".json"] and source_values[name+".stderr"]==b""
release_reports={}
for suffix,rid in RELEASES.items():
 group="cdr-width-loaded-"+suffix;stem=group+"-"+str(RUN)+"-1";tag="cloud-results-"+str(RUN)+"-1-"+group
 release=api("releases/"+str(rid));ref=api("git/ref/tags/"+tag)
 assert release["tag_name"]==tag and release["target_commitish"]==SOURCE and release["draft"]is False and release["prerelease"]is True
 assert ref["object"]["type"]=="commit"and ref["object"]["sha"]==SOURCE
 base=PREFIX+"releases/"+suffix+"/";files[base+"release.json"]=enc(release);files[base+"tag-ref.json"]=enc(ref)
 assets={a["name"]:a for a in release["assets"]};assert len(assets)==len(release["assets"])
 allowed={"summary.json","parts.json","direct-publication-plan.json","publication-source-check.json","native-result.json","preparation-summary.json","preparation-native-result.json"}
 texts=[a for a in release["assets"]if a["name"].startswith(stem+".")and a["name"][len(stem)+1:]in allowed]
 archive=[a for a in release["assets"]if a["name"].startswith(stem+".tar.gz.part")]
 assert len(texts)+len(archive)==len(assets)
 def read_text(a):
  assert a["state"]=="uploaded"and 0<a["size"]<=64*1024**2
  b=asset(a["id"]);assert len(b)==a["size"]and a["digest"]=="sha256:"+sha(b);b.decode()
  return a["name"][len(stem)+1:],b
 with ThreadPoolExecutor(4)as ex:direct=dict(ex.map(read_text,texts))
 docs={};parse_errors={}
 for name,b in direct.items():
  files[base+"direct/"+name]=b
  try:docs[name]=json.loads(b)
  except(ValueError,UnicodeError)as error:parse_errors[name]=repr(error)
 j,idx,indexed=native.get(suffix,({}, {}, {}));good=j.get("conclusion")=="success"
 report=dict(release_id=rid,tag=tag,job_id=j.get("id"),job_conclusion=j.get("conclusion"),direct_assets=len(texts),archive_parts=len(archive),malformed_json=parse_errors,native_archive_acquired_locally=False)
 if good:assert not parse_errors and {"summary.json","parts.json","direct-publication-plan.json","publication-source-check.json","native-result.json"}<=set(docs)
 outroot="cloud-cdr-width-loaded-evidence-"+suffix
 transroot="hw/soc/out/cloud-cdr-width-loaded-"+suffix+"-publication"
 joins={"summary.json":transroot+"/"+stem+".summary.json","parts.json":transroot+"/"+stem+".parts.json","direct-publication-plan.json":outroot+"/direct-publication-plan.json","publication-source-check.json":outroot+"/publication-source-check.json"}
 for name,path in joins.items():
  if name in direct and path in indexed:assert direct[name]==indexed[path]
  elif good:raise AssertionError(("missing indexed/direct join",suffix,name))
 if "parts.json"in docs:
  parts=docs["parts.json"];assert parts["format"]=="ordered-tar-gzip-parts-v1"and parts["stem"]==stem
  missing=[]
  for i,p in enumerate(parts["parts"]):
   assert p["index"]==i and p["name"]==stem+".tar.gz.part%04d"%i
   a=assets.get(p["name"])
   if a is None:missing.append(p["name"]);continue
   assert a["state"]=="uploaded"and a["size"]==p["bytes"]and a["digest"]=="sha256:"+p["sha256"]
  assert sum(p["bytes"]for p in parts["parts"])==parts["bytes"]
  assert {a["name"]for a in archive}<={p["name"]for p in parts["parts"]}
  if good:assert not missing
  report.update(archive_bytes=parts["bytes"],archive_sha256=parts["sha256"],missing_archive_parts=missing,complete_published_part_digests=not missing)
 if "summary.json"in docs:
  summary=docs["summary.json"]
  assert (summary["source_head"],summary["run_id"],summary["run_attempt"],summary["group"])==(SOURCE,RUN,1,group)
  assert all(summary[k]is False for k in ("accepted","cdr_accepted","full_phy_accepted","physical_accepted","qualified_pex"))
  mapping=summary["outputs"];files[base+"complete-native-restore-map.json"]=enc(mapping)
  for name,member in {"direct-publication-plan.json":"direct-publication-plan.json","publication-source-check.json":"publication-source-check.json","native-result.json":"native/result.json","preparation-summary.json":"preparation-proof/summary.json","preparation-native-result.json":"preparation-proof/native-result.json"}.items():
   if name in direct:assert mapping[member]==sha(direct[name])
  outer=indexed.get(outroot+"/result.json")
  if outer is not None and summary.get("raw_terminal"):
   binding=summary["raw_terminal"];assert binding==dict(member="result.json",bytes=len(outer),sha256=sha(outer))and mapping["result.json"]==sha(outer)
  if good:
   status="PASS_CURRENT_TAIL_LOADED_PREPARATION_ORIGINAL_BINDING_GATES"if suffix=="preparation"else"PASS_CURRENT_TAIL_ORIGINAL_LOADED_CASE_NOT_PHY_ACCEPTANCE"
   assert summary["status"]==status and summary["publication_qualified_as_success"]is True and summary["native_case_passed"]is True
   assert summary["native_controller_result_sha256"]==sha(direct["native-result.json"])
  report.update(status=summary.get("status"),native_status=summary.get("native_status"),native_case_passed=summary.get("native_case_passed"),
    publication_qualified_as_success=summary.get("publication_qualified_as_success"),outputs=len(mapping),native_validation=summary.get("native_validation"),
    active_primary_exception_before_terminal=summary.get("active_primary_exception_before_terminal"),outer_terminal_errors=summary.get("outer_terminal_errors"))
 if "direct-publication-plan.json"in docs:
  for row in docs["direct-publication-plan.json"]["files"]:
   if row["disposition"]=="direct_and_archive"and row["asset_suffix"]in direct:
    b=direct[row["asset_suffix"]];assert len(b)==row["bytes"]and sha(b)==row["sha256"]
   elif row["disposition"]=="direct_and_archive"and good:raise AssertionError(("missing planned direct asset",suffix,row))
 release_reports[suffix]=report
receipt=dict(schema="current-width-loaded-native-terminal-v1",source=SOURCE,run=RUN,attempt=1,terminal=r["conclusion"],method_sha256=sha(method_raw),
 source_controls_qualified=source_ok,full_raw_job_logs=True,releases=release_reports,native_archive_acquired_locally=False,
 waveform_acquired_locally=False,native_execution_performed_locally=False,full_phy_accepted=False,cdr_accepted=False,physical_accepted=False,
 files={n:dict(bytes=len(b),sha256=sha(b))for n,b in files.items()})
files[PREFIX+"receipt.json"]=enc(receipt)
new=publish(SOURCE,files,"Preserve complete current-width loaded cloud terminal evidence [skip ci]")
tree=api("git/trees/"+new+"?recursive=1");assert not tree["truncated"]
by={x["path"]:x["sha"]for x in tree["tree"]if x["type"]=="blob"}
assert all(by[n]==hashlib.sha1(("blob "+str(len(b))+"\0").encode()+b).hexdigest()for n,b in files.items())
print(json.dumps(dict(head=new,run=RUN,terminal=r["conclusion"],files=len(files),bytes=sum(map(len,files.values())),receipt_sha256=sha(files[PREFIX+"receipt.json"]),
 cases={c:dict(status=v.get("status"),native_status=v.get("native_status"),native_case_passed=v.get("native_case_passed"))for c,v in release_reports.items()})))
