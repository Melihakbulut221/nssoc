#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only read-only diagnosis of the preserved 41199907663 routing failure."""
import argparse,base64,hashlib,json,os,shutil,subprocess,sys,time,traceback
from collections import Counter
from pathlib import Path
import cloud_mainchip_full_antenna_readback as archive_reader

ROOT=Path(__file__).resolve().parents[1]
PREFIX="docs/evidence/mainchip-diode-routing-terminal-41199907663/"
PRODUCER=41199907663
SOURCE="6e4214259c4a260c8b612f2bc5bc1d0ea9dbe773"
RELEASE=429913592
GROUP="mainchip-saved-route-diagnosis"
SNAP="bulk-postdrt-antenna/insertion-snapshot.json"
PLAN="bulk-postdrt-antenna/insertion-plan.json"
LOG="bulk-postdrt-supervision/bulk-postdrt-route.stdout"
SELECTED={SNAP,PLAN,LOG,"bulk-postdrt-antenna/saved-construction-plan.json"}
SNAPSHOTS=("insertion-snapshot.json","guide-reloaded-snapshot.json","restored-snapshot.json","failure-restored-snapshot.json")
RECEIPT_SHA="150564342abbdca3de6d086865ff56160edd2c0e21626cd518606dcb3c966b72"
FLAGS=dict(physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def require(value,message):
    if not value:raise AssertionError(message)
def pin(path):
    with Path(path).open("rb")as f:
        return dict(bytes=Path(path).stat().st_size,sha256=hashlib.file_digest(f,"sha256").hexdigest())
def save(path,value):
    Path(path).write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")
def api(path):
    # No mutations or automatic retries. Complete raw bytes remain in upstream capsules.
    r=subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/"+path],capture_output=True,check=True)
    return json.loads(r.stdout)
def context():
    e=os.environ
    require(e.get("GITHUB_ACTIONS")=="true"and e["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc","hosted repository only")
    require(e["GITHUB_RUN_ATTEMPT"]=="1"and e["GITHUB_EVENT_NAME"]=="workflow_dispatch","first explicit attempt")
    require(e["GITHUB_REF"]=="refs/heads/codex/mainchip-net459-diode-prune","owned diagnosis branch")
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==e["GITHUB_SHA"],"exact checkout")
    return dict(source=e["GITHUB_SHA"],run=int(e["GITHUB_RUN_ID"]),attempt=1)
def proof_file(name,receipt):
    p=ROOT/PREFIX/name
    require(not p.is_symlink()and pin(p)==receipt["files"][name],"frozen proof bytes "+name)
    return json.loads(p.read_bytes())
def metadata():
    p=ROOT/PREFIX/"receipt.json"
    require(pin(p)["sha256"]==RECEIPT_SHA,"original failure receipt")
    receipt=json.loads(p.read_bytes())
    require(receipt["run"]==PRODUCER and receipt["source"]==SOURCE and receipt["workflow_conclusion"]=="failure","original failure identity")
    index=proof_file("capsule-metadata/candidate-outputs.json",receipt)
    parts=proof_file("capsule-metadata/candidate-parts.json",receipt)
    release=proof_file("release.json",receipt)
    require(index["run"]==PRODUCER and index["source"]==SOURCE and len(index["files"])==741,"complete741 original members")
    return index,parts,release
def reservation(ctx):
    tag="cloud-results-"+str(ctx["run"])+"-1-"+GROUP
    # The external coordinator creates the empty reservation, never this worker.
    for _ in range(60):
        r=subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/releases/tags/"+tag],capture_output=True)
        if r.returncode==0:
            rel=json.loads(r.stdout)
            require(rel["tag_name"]==tag and rel["target_commitish"]==ctx["source"]and
              rel["draft"]is False and rel["prerelease"]is True and rel["assets"]==[],"empty exact-source reservation")
            ref=api("git/ref/tags/"+tag)
            require(ref["object"]["type"]=="commit"and ref["object"]["sha"]==ctx["source"],"reservation tag")
            return dict(tag=tag,release_id=rel["id"],source=ctx["source"],run=ctx["run"])
        require(b"HTTP 404"in r.stderr,"reservation lookup failed")
        time.sleep(5)
    raise AssertionError("Independent release reservation absent")
def live_producer(saved):
    run=api("actions/runs/"+str(PRODUCER))
    jobs=api("actions/runs/"+str(PRODUCER)+"/attempts/1/jobs?per_page=100")
    release=api("releases/"+str(RELEASE))
    ref=api("git/ref/tags/"+saved["tag_name"])
    require(run["head_sha"]==SOURCE and run["run_attempt"]==1 and run["workflow_id"]==401215446
      and run["status"]=="completed"and run["conclusion"]=="failure","same failed producer")
    require(len(jobs["jobs"])==4 and {j["name"]:j["conclusion"]for j in jobs["jobs"]}==
      {"source-controls":"success","preserve-job-log":"success","diode-routing":"failure","preserve-antenna-job-logs":"success"},"original four jobs")
    require(all(j["head_sha"]==SOURCE and j["run_id"]==PRODUCER and j["status"]=="completed"for j in jobs["jobs"]),"producer job identities")
    require(release["id"]==RELEASE and release["target_commitish"]==SOURCE and release["tag_name"]==saved["tag_name"]
      and release["draft"]is False and release["prerelease"]is True,"producer release")
    fields=("id","name","size","digest")
    require(sorted(tuple(a[k]for k in fields)for a in release["assets"])==
      sorted(tuple(a[k]for k in fields)for a in saved["assets"]),"exact producer asset identities")
    require(ref["object"]["type"]=="commit"and ref["object"]["sha"]==SOURCE,"producer tag")
    return dict(run=run,jobs=jobs,release=release,ref=ref)
def acquire(index,parts,live,work,out):
    require(shutil.disk_usage(work).free>8*1024**3,"cloud diagnostic disk reserve")
    assets={a["name"]:a for a in live["release"]["assets"]}
    archive=work/"candidate-native.tar.gz"
    with archive.open("xb")as dst:
        for row in parts["parts"]:
            a=assets[row["name"]]
            require(a["size"]==row["bytes"]and a["digest"]=="sha256:"+row["sha256"],"native part pin")
            target=work/row["name"]
            with target.open("xb")as f:
                proc=subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/releases/assets/"+str(a["id"]),
                  "-H","Accept: application/octet-stream"],stdout=f,stderr=subprocess.PIPE,timeout=900)
            (out/(row["name"]+".stderr")).write_bytes(proc.stderr)
            require(proc.returncode==0 and pin(target)=={k:row[k]for k in("bytes","sha256")},"native part complete")
            with target.open("rb")as src:shutil.copyfileobj(src,dst,1024**2)
            target.unlink()
    require(pin(archive)==parts["archive"],"complete native archive hash")
    restored=work/"selected"
    observed=archive_reader.restore(archive,index["files"],SELECTED,restored)
    save(out/"complete-acquisition.json",dict(archive=parts["archive"],full_member_count=len(observed),
      all741_members_authenticated=observed==index["files"],selected={n:observed[n]for n in sorted(SELECTED)},
      native_payloads_remain_on_cloud=True))
    return restored
def classify(snapshot,plan):
    require(set(plan["attachments"])==set(plan["added_instances"]),"all new diode owners")
    require(set(plan["mutable_nets"])==set(plan["attachments"].values()),"all mutable owners")
    require(not(set(plan["mutable_nets"])&set(plan["protected_nets"])),"no protected mutation")
    records={}
    for name in plan["mutable_nets"]:
        row=snapshot["nets"][name]
        added=sorted(i for i,n in plan["attachments"].items()if n==name)
        for inst in added:
            require(snapshot["instances"][inst]["pins"]["A"]["net"]==name,"added A net")
            require(any(t[0]==inst and t[1]=="A"for t in row["identity"]["terminals"]),"added A native incidence")
        records[name]=dict(added_diodes=added,wire=row["wire"],encoded=row["encoded"],
          terminal_count=len(row["identity"]["terminals"]),signal_type=row["identity"]["sigtype"])
    return dict(instances=len(snapshot["instances"]),nets=len(snapshot["nets"]),added_diodes=len(plan["added_instances"]),
      original_instances=plan["original_instances_preserved"],mutable_nets=len(records),
      protected_nets=len(plan["protected_nets"]),
      mutable_metadata_counts=dict(Counter(r["encoded"]["metadata"]for r in records.values())),
      mutable_path_counts=dict(Counter(str(r["encoded"]["paths"])for r in records.values())),
      literal_mutable_records=records)
def diagnose(index,restored,out):
    snapshot_pins={n:index["files"]["bulk-postdrt-antenna/"+n]for n in SNAPSHOTS}
    same=len({(p["bytes"],p["sha256"])for p in snapshot_pins.values()})==1
    require(same,"This specific identical-snapshot diagnosis requires the exact saved equality; no assumption on another candidate")
    snap=json.loads((restored/SNAP).read_bytes())
    plan=json.loads((restored/PLAN).read_bytes())
    result=classify(snap,plan)
    require(result["instances"]==154480 and result["nets"]==143820 and result["added_diodes"]==1351
      and result["mutable_nets"]==608 and result["protected_nets"]==1691,"actual complete expected census")
    result.update(status="DIAGNOSED_IDENTICAL_INSERTION_AND_ROUTED_SNAPSHOTS",
      unchanged_mutable_nets=sorted(result["literal_mutable_records"]),changed_mutable_nets=[],
      snapshot_pins=snapshot_pins,full_saved_snapshots_identical=True,
      frozen_route_delta_failure_preserved=True,physical_connectivity_tested=False,
      claim="All saved snapshot bytes, including all instance pins and wire signatures, are identical. Native physical connectivity still requires direct ODB readback.",
      **FLAGS)
    # Complete route log and plan are retained, not only interpreted summaries.
    shutil.copyfile(restored/LOG,out/"original-route.stdout")
    shutil.copyfile(restored/PLAN,out/"original-insertion-plan.json")
    save(out/"diagnosis.json",result)
    return {k:v for k,v in result.items()if k not in("literal_mutable_records","unchanged_mutable_nets")}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",type=Path,required=True);args=ap.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    report=dict(status="IN_PROGRESS",**FLAGS);primary=None
    try:
        ctx=context();report["context"]=ctx
        save(out/"context.json",ctx)
        report["reservation"]=reservation(ctx);save(out/"reservation.json",report["reservation"])
        index,parts,saved=metadata();live=live_producer(saved);save(out/"live-producer.json",live)
        work=Path(os.environ["RUNNER_TEMP"])/(GROUP+"-"+str(ctx["run"]));work.mkdir(exist_ok=False)
        save(work/"owner.json",ctx)
        restored=acquire(index,parts,live,work,out)
        report["diagnosis"]=diagnose(index,restored,out)
        require(all(pin(restored/n)==index["files"][n]for n in SELECTED),"saved inputs unchanged")
        report["status"]="COMPLETE_READ_ONLY_SAVED_ROUTING_DIAGNOSIS"
    except BaseException as exc:
        primary=exc;report.update(status="FAIL_SAVED_ROUTING_DIAGNOSIS",error=repr(exc),traceback=traceback.format_exc())
    finally:
        report["outputs"]={str(p.relative_to(out)):pin(p)for p in out.rglob("*")if p.is_file()}
        save(out/"result.json",report)
        print("SAVED_ROUTE_DIAGNOSIS_RESULT "+json.dumps(report,sort_keys=True),flush=True)
    if primary:raise primary
if __name__=="__main__":main()
