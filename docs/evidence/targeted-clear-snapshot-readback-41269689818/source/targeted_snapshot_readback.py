#!/usr/bin/env python3
"""Cloud-only readback of the failed clear's two complete saved snapshots.
No native geometry mutation or router execution. Original strict delta retained.
"""
import base64,hashlib,importlib.util,json,os,pathlib,subprocess,tarfile,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=pathlib.Path("cloud-targeted-snapshot-readback")
def require(ok,msg):
    if not ok:raise ValueError(msg)
def sha(path):
    with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def save(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")
def api(path):
    p=subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/"+path],capture_output=True,text=True,timeout=180)
    require(p.returncode==0,p.stderr[:2000]);return json.loads(p.stdout)
def get(asset,path):
    live=api("releases/assets/"+str(asset["id"]))
    require(live["name"]==asset["name"] and live["size"]==asset["bytes"] and live["digest"]=="sha256:"+asset["sha256"],"exact original asset")
    with path.open("xb") as f:
        p=subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/releases/assets/"+str(asset["id"]),"-H","Accept: application/octet-stream"],stdout=f,stderr=subprocess.PIPE,timeout=900)
    require(p.returncode==0,p.stderr.decode()[:2000]);require(path.stat().st_size==asset["bytes"] and sha(path)==asset["sha256"],"downloaded asset bytes")
def main():
    require(os.environ.get("GITHUB_ACTIONS")=="true" and os.environ["GITHUB_RUN_ATTEMPT"]=="1","cloud first attempt only")
    cfg=json.loads((ROOT/"scripts/targeted-snapshot-readback-inputs.json").read_bytes())
    OUT.mkdir(exist_ok=False)
    native=pathlib.Path(os.environ["RUNNER_TEMP"])/("targeted-readback-"+os.environ["GITHUB_RUN_ID"]);native.mkdir(exist_ok=False)
    run=api("actions/runs/41266854050");release=api("releases/430325810");tag=api("git/ref/tags/cloud-results-41266854050-1-mainchip-bulk-postdrt-antenna")
    require(run["head_sha"]==cfg["source"] and run["status"]=="completed" and run["conclusion"]=="failure" and run["run_attempt"]==1,"exact failed native run")
    require(release["target_commitish"]==cfg["source"] and tag["object"]["sha"]==cfg["source"],"exact native publication source")
    save("producer.json",dict(run=run,release=release,tag=tag))
    assets={a["name"]:a for a in cfg["assets"]}
    for name in ("candidate-outputs.json","candidate-parts.json"):get(assets[name],native/name)
    index=json.loads((native/"candidate-outputs.json").read_bytes());parts=json.loads((native/"candidate-parts.json").read_bytes())
    require(index["run"]==41266854050 and index["source"]==cfg["source"],"original complete index")
    save("candidate-outputs.json",index);save("candidate-parts.json",parts)
    archive=native/"candidate.tar.gz"
    with archive.open("xb") as out:
        for part in parts["parts"]:
            a=assets[part["name"]];require(all(a[k]==part[k] for k in ("name","bytes","sha256")),"original part pin")
            path=native/part["name"];get(a,path)
            with path.open("rb") as f:
                while True:
                    b=f.read(1024**2)
                    if not b:break
                    out.write(b)
            path.unlink()
    require(archive.stat().st_size==parts["archive"]["bytes"] and sha(archive)==parts["archive"]["sha256"],"complete original archive")
    selected=set(cfg["selected"]);require(selected<=set(index["files"]),"selected original records")
    records=native/"records";records.mkdir()
    seen={}
    with tarfile.open(archive,"r:gz") as tar:
        for member in tar:
            name=member.name
            require(member.isfile() and name in index["files"] and name not in seen,"exact original regular member")
            require(not name.startswith("/") and all(x not in ("",".","..") for x in name.split("/")),"canonical member")
            pin=index["files"][name];require(member.size==pin["bytes"],"original member size")
            h=hashlib.sha256();n=0;dest=None
            try:
                if name in selected:
                    path=records/name;path.parent.mkdir(parents=True,exist_ok=True);dest=path.open("xb")
                stream=tar.extractfile(member)
                while True:
                    b=stream.read(1024**2)
                    if not b:break
                    n+=len(b);h.update(b)
                    if dest:dest.write(b)
            finally:
                if dest:dest.close()
            require(dict(bytes=n,sha256=h.hexdigest())==pin,"every original member digest")
            seen[name]=pin
    require(seen==index["files"],"complete original native member census")
    save("archive-readback.json",dict(archive=parts["archive"],all_members_verified=len(seen),selected={n:seen[n] for n in sorted(selected)},native_payloads_remain_cloud=True))
    corepin=cfg["core"];value=api("contents/"+corepin["path"]+"?ref="+cfg["source"])
    if not value.get("content"):value=api("git/blobs/"+value["sha"])
    raw=base64.b64decode(value["content"]);require(len(raw)==corepin["bytes"] and hashlib.sha256(raw).hexdigest()==corepin["sha256"],"unchanged strict delta code")
    path=OUT/"original-strict-core.py";path.write_bytes(raw)
    spec=importlib.util.spec_from_file_location("original_strict_core",path);core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    def read(name):
        with (records/"bulk-postdrt-antenna"/name).open() as f:return json.load(f)
    before=read("fixed-snapshot.json");after=read("stale-wire-cleared-snapshot.json")
    plan=read("insertion-plan.json");scope=read("targeted-routing-scope.json")
    failure=read("stale-wire-clear-failure.json")
    save("original-clear-failure.json",failure);save("scope.json",scope)
    same=before["masters"]==after["masters"]
    save("master-comparison.json",dict(exact_serialized_master_equality=same,before_count=len(before["masters"]),after_count=len(after["masters"]),
        different_keys=[k for k in sorted(set(before["masters"])|set(after["masters"])) if before["masters"].get(k)!=after["masters"].get(k)]))
    require(same,"actual saved master geometry differs")
    empty=dict(bytes=5,sha256=hashlib.sha256(b"null\n").hexdigest())
    delta=core.clear_delta(before,after,plan,scope,empty)
    save("strict-saved-delta.json",delta)
    # Demonstrate the Python tuple/list boundary from the original native
    # master_pin_boxes API without changing a coordinate or list order.
    witness=None
    for master,m in after["masters"].items():
        for terminal,t in m["pins"].items():
            for group in t["boxes"]:
                if group:
                    old=group[0];group[0]=tuple(old)
                    try:
                        require(json.loads(json.dumps(after["masters"]))==before["masters"],"same serialized geometry")
                        try:core.clear_delta(before,after,plan,scope,empty)
                        except AssertionError as exc:
                            require(str(exc)=="unchanged snapshot masters","same original failure")
                            witness=dict(master=master,terminal=terminal,box=old,error=str(exc))
                        else:raise ValueError("original typed comparison accepted tuple/list boundary")
                    finally:group[0]=old
                    break
            if witness:break
        if witness:break
    require(witness is not None,"real nonempty original master pin witness")
    save("result.json",dict(status="PASS_COMPLETE_SAVED_CLEAR_DELTA_TYPED_BOUNDARY_REPRODUCED",original_run=41266854050,source=cfg["source"],
        exact_serialized_master_equality=True,strict_delta=delta,typed_boundary_witness=witness,
        routing_executed_by_this_job=False,native_geometry_changed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
    print(json.dumps(dict(status="PASS_COMPLETE_SAVED_CLEAR_DELTA_TYPED_BOUNDARY_REPRODUCED",witness=witness,masters=len(before["masters"]),all_original_members=len(seen)),sort_keys=True))
if __name__=="__main__":
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);(OUT/"failure.txt").write_text(traceback.format_exc());raise
