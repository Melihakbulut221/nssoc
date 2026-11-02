#!/usr/bin/env python3
"""Cloud-only extraction of full failed engine build logs; original release is read-only."""
import hashlib,io,json,os,subprocess,tarfile
from pathlib import Path,PurePosixPath
REPO="repos/Melihakbulut221/nssoc/"
SOURCE="5a82cbd4068411de19acc73605ebb64250b010fc"
ASSETS={
"outputs.json":(701976392,12275,"02ba8a4ab008f5aa8c6dc44335f67582aabaff1e06eeff801cd10ea1e2a6922f"),
"engine-evidence.tar.gz.part000":(701976876,1542715,"2782573db9c591615665e42d587c9cdefc1ece79d88c65366e87d06171bf8599")}
def sha(b):return hashlib.sha256(b).hexdigest()
def api(path):return json.loads(subprocess.check_output(["gh","api",REPO+path],timeout=180))
def save(p,q):p.write_text(json.dumps(q,sort_keys=True,indent=2)+"\n")
def main():
 assert os.environ["GITHUB_ACTIONS"]=="true"and os.environ["RUNNER_ENVIRONMENT"]=="github-hosted"
 assert os.environ["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"and os.environ["GITHUB_REF"]=="refs/heads/codex/mainchip-guide-build-diagnosis"
 assert os.environ["GITHUB_EVENT_NAME"]=="workflow_dispatch"and os.environ["GITHUB_RUN_ATTEMPT"]=="1"
 assert subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==os.environ["GITHUB_SHA"]
 out=Path("engine-build-derived");out.mkdir()
 run=api("actions/runs/41453866417");rel=api("releases/431499827")
 assert run["head_sha"]==SOURCE and run["status"]=="completed"and run["conclusion"]=="failure"and run["run_attempt"]==1
 assert rel["target_commitish"]==SOURCE and rel["tag_name"]=="cloud-results-41453866417-1-mainchip-guide-batch-engine-build"
 assert api("git/ref/tags/"+rel["tag_name"])["object"]["sha"]==SOURCE
 assets={a["name"]:a for a in rel["assets"]};payload={}
 for name,(ident,size,digest)in ASSETS.items():
  a=assets[name];assert a["id"]==ident and a["size"]==size and a["digest"]=="sha256:"+digest
  b=subprocess.check_output(["gh","api",REPO+"releases/assets/"+str(ident),"-H","Accept: application/octet-stream"],timeout=180)
  assert len(b)==size and sha(b)==digest;payload[name]=b
 index=json.loads(payload["outputs.json"]);assert index["source"]==SOURCE
 expected=dict(index["files"]);expected["outputs.json"]=dict(bytes=len(payload["outputs.json"]),sha256=sha(payload["outputs.json"]))
 selected={"complete-build.stdout","complete-build.stderr","openroad_build.log","inner-result.json","host-result.json","cgroup-samples.jsonl","container-terminal.json","guide-batch-derivation.json","guide-batch-controls.json"}
 seen=set();retained={}
 with tarfile.open(fileobj=io.BytesIO(payload["engine-evidence.tar.gz.part000"]),mode="r:gz")as tar:
  for member in tar:
   name=member.name;p=PurePosixPath(name)
   assert member.isfile()and not p.is_absolute()and ".."not in p.parts and name not in seen and name in expected
   seen.add(name);b=tar.extractfile(member).read()
   assert len(b)==member.size==expected[name]["bytes"]and sha(b)==expected[name]["sha256"]
   if name in selected:
    assert p.suffix in (".json",".jsonl",".log",".stdout",".stderr")
    b.decode("utf-8");(out/name).write_bytes(b);retained[name]=expected[name]
 assert seen==set(expected)and selected<=seen
 save(out/"acquisition.json",dict(source_run=41453866417,source=SOURCE,release=431499827,assets=ASSETS,complete_census=len(seen),selected=retained,native_execution=False,original_failure_preserved=True))
 log=(out/"complete-build.stdout").read_text().splitlines()
 relevant=set()
 for i,line in enumerate(log):
  if "error:"in line.lower()or "fatal error"in line.lower():
   relevant.update(range(max(0,i-5),min(len(log),i+12)))
 excerpt=[dict(line=i+1,text=log[i])for i in sorted(relevant)]
 save(out/"compiler-errors.json",dict(lines=excerpt,complete_log=retained["complete-build.stdout"],last_lines=log[-30:]))
 print(json.dumps(dict(status="PASS_COMPLETE_BUILD_LOG_EXTRACTION",census=len(seen),error_lines=excerpt),indent=2))
if __name__=="__main__":main()
