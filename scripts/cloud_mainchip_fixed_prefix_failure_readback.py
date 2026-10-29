#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only full archive authentication and selected failed-prefix text readback."""
import base64,hashlib,json,os,posixpath,subprocess,tarfile,tempfile,traceback
from pathlib import Path
import wait_cloud_tested_source_release as reservation
ROOT=Path(__file__).resolve().parent.parent
GROUP="mainchip-fixed-prefix-failure-readback"
BRANCH="codex/mainchip-fixed-prefix-failure-readback"
OLD=ROOT/"docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40863684870"
RECEIPT_SHA="ba1c13a40eb4e593b7b12cbc4d42d5f95260b789d76ff3f949c98220551ce2ec"
SELECTED=("cgroup-samples.jsonl","shared-prefix.stdout","shared-prefix.stderr",
 "supervision/events.jsonl","supervision/latest.json","supervision/ownership.command.json",
 "supervision/ownership.stdout","supervision/ownership.stderr","work/ownership-result.json",
 "work/ownership.json","work/original-gate-before-two-net-repair/result.json","work/source-markers.rpt")
def digest(b):return hashlib.sha256(b).hexdigest()
def fp(p):
 with p.open("rb")as f:h=hashlib.file_digest(f,"sha256").hexdigest()
 return dict(bytes=p.stat().st_size,sha256=h)
def read(p):return json.loads(p.read_bytes())
def save(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n")
def run():
 assert os.environ["GITHUB_ACTIONS"]=="true"and os.environ["RUNNER_ENVIRONMENT"]=="github-hosted"
 assert os.environ["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"
 assert os.environ["GITHUB_EVENT_NAME"]=="workflow_dispatch"and os.environ["GITHUB_RUN_ATTEMPT"]=="1"
 assert os.environ["GITHUB_REF"]=="refs/heads/"+BRANCH
 source=os.environ["GITHUB_SHA"];rid=int(os.environ["GITHUB_RUN_ID"])
 assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==source
 out=ROOT/"fixed-prefix-failure-readback";out.mkdir()
 result=dict(schema="fixed-prefix-failure-text-readback-v1",source=source,run_id=rid,attempt=1,
  status="FAIL_CLOUD_READBACK",native_executed=False,physical_acceptance=False,prefix_qualified=False,
  original_failed_run=40863684870,native_archive_acquired_locally=False,records={})
 primary=None;proof=None
 try:
  receipt_raw=(OLD/"receipt.json").read_bytes();assert digest(receipt_raw)==RECEIPT_SHA
  receipt=json.loads(receipt_raw)
  assert receipt["terminal"]=="failure"and receipt["prefix_qualified"]is False
  for path,row in receipt["files"].items():assert fp(ROOT/path)==row,path
  result["full_failure_proof_files"]=len(receipt["files"])+1
  oldrun=read(OLD/"run.json");oldjobs=read(OLD/"jobs.json");oldrel=read(OLD/"release.json");oldtag=read(OLD/"tag-ref.json")
  readapi=reservation.release.api
  live=readapi("actions/runs/40863684870")
  assert (live["head_sha"],live["run_attempt"],live["status"],live["conclusion"])==(oldrun["head_sha"],1,"completed","failure")
  livejobs=readapi("actions/runs/40863684870/attempts/1/jobs?per_page=100")
  assert {(j["id"],j["name"],j["status"],j["conclusion"])for j in livejobs["jobs"]}=={(j["id"],j["name"],j["status"],j["conclusion"])for j in oldjobs["jobs"]}
  live_rel=readapi("releases/427769567");live_tag=readapi("git/ref/tags/"+oldrel["tag_name"])
  reservation.release.validate_release(live_rel,live_tag,oldrel["tag_name"],oldrun["head_sha"])
  projection=lambda r:{a["name"]:(a["id"],a["size"],a["digest"])for a in r["assets"]}
  assert live_rel["id"]==oldrel["id"]and projection(live_rel)==projection(oldrel)
  assert live_tag["object"]==oldtag["object"]
  # Exact current-source reserved destination exists BEFORE archive acquisition.
  proof=reservation.wait(GROUP,os.environ)
  assert proof["existing_assets"]==[]and proof["externally_reserved"]is True and proof["creation_attempted"]is False
  result["reservation"]=proof
  expected=read(OLD/"complete-native-restore-map.json");parts=read(OLD/"direct/parts.json")
  assert len(expected)==67 and len(parts["parts"])==1
  part=parts["parts"][0];assert part["name"]=="route-prefix-evidence.tar.gz.part000"
  assert parts["archive"]=={k:part[k]for k in ("bytes","sha256")}
  assert parts["archive"]==dict(bytes=78585139,sha256="fe08a442a5c59ffc3c1046714617ec55a22d5201517b026ed3b5f2212e1fb54a")
  asset=next(a for a in live_rel["assets"]if a["name"]==part["name"])
  assert asset["id"]==688359292 and asset["size"]==part["bytes"]and asset["digest"]=="sha256:"+part["sha256"]
  selected={};seen={}
  with tempfile.TemporaryDirectory(prefix="prefix-text-readback-",dir=os.environ["RUNNER_TEMP"])as td:
   archive=Path(td)/"failed-prefix.tar.gz"
   subprocess.run(["curl","--fail","--location","--silent","--show-error","--max-time","600",asset["browser_download_url"],"-o",str(archive)],check=True)
   assert fp(archive)==parts["archive"]
   with tarfile.open(archive,"r|gz")as tar:
    for member in tar:
     name=member.name
     assert not name.startswith("/")and posixpath.normpath(name)==name and ".."not in name.split("/")
     assert member.isdir()or member.isfile()
     if member.isdir():continue
     assert name in expected and name not in seen and member.size==expected[name]["bytes"]
     keep=name in SELECTED
     if keep:assert member.size<=1024**2
     h=hashlib.sha256();total=0;chunks=[]
     with tar.extractfile(member)as stream:
      while True:
       b=stream.read(1024**2)
       if not b:break
       h.update(b);total+=len(b)
       if keep:chunks.append(b)
     row=dict(bytes=total,sha256=h.hexdigest());assert row==expected[name],name
     seen[name]=row
     if keep:
      raw=b"".join(chunks);raw.decode("utf-8")
      selected[name]=dict(**row,base64=base64.b64encode(raw).decode())
   assert seen==expected and set(selected)==set(SELECTED)
  result.update(status="PASS_COMPLETE_ARCHIVE_SELECTED_TEXT_READBACK",archive=parts["archive"],
    all_archive_members=len(seen),full_original_member_map_verified=True,records=selected,
    archive_acquired_only_on_GitHub_hosted_runner=True)
 except BaseException as exc:
  primary=exc;result.update(error=repr(exc),traceback=traceback.format_exc())
 finally:
  path=out/"readback-result.json";save(path,result)
  try:
   if proof is None:proof=reservation.wait(GROUP,os.environ)
   tag=proof["tag"];readapi=reservation.release.api
   rel=readapi("releases/tags/"+tag);ref=readapi("git/ref/tags/"+tag)
   reservation.release.validate_release(rel,ref,tag,source)
   assert rel["id"]==proof["release_id"]and rel["assets"]==[]
   subprocess.run(["gh","release","upload",tag,str(path),"--repo","Melihakbulut221/nssoc"],check=True,timeout=300)
   rel=readapi("releases/tags/"+tag);assets=rel["assets"]
   assert len(assets)==1 and assets[0]["name"]==path.name
   row=fp(path);assert assets[0]["size"]==row["bytes"]and assets[0]["digest"]=="sha256:"+row["sha256"]
   print(json.dumps(dict(status=result["status"],release_id=rel["id"],asset=assets[0]["id"],**row)))
  except BaseException as exc:
   save(out/"publication-error.json",dict(error=repr(exc),primary_error=None if primary is None else repr(primary),physical_acceptance=False))
   if primary is None:primary=exc
 if primary is not None:raise primary
if __name__=="__main__":run()
