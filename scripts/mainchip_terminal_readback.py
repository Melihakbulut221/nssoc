#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read the exact rejected routing capsule on GitHub; never run native design tools."""
import argparse,hashlib,json,os,re,subprocess,tarfile,time
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
REPO="Melihakbulut221/nssoc"
BRANCH="codex/mainchip-stale-wire-terminal-readback"
GROUP="mainchip-stale-wire-terminal-readback"
CONFIG="scripts/mainchip-stale-wire-terminal-inputs.json"
MANIFEST="scripts/mainchip-stale-wire-terminal-source.json"
OUT=ROOT/"terminal-readback"
def require(ok,why):
    if not ok:raise ValueError(why)
def unique(pairs):
    out={}
    for k,v in pairs:
        require(k not in out,"duplicate JSON key");out[k]=v
    return out
def decode(raw):
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(ValueError("nonfinite JSON")))
def encode(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(path):
    with Path(path).open("rb")as f:return dict(bytes=Path(path).stat().st_size,sha256=hashlib.file_digest(f,"sha256").hexdigest())
def valid_name(n):
    require(type(n)is str and n and not n.startswith("/") and "\\"not in n and "\x00"not in n and "\n"not in n,"unsafe member")
    require(str(PurePosixPath(n))==n and all(x not in("..",".","")for x in n.split("/")),"noncanonical member")
    return n
def filepin(p):
    require(type(p)is dict and set(p)=={"bytes","sha256"},"file pin fields")
    require(type(p["bytes"])is int and p["bytes"]>=0 and type(p["sha256"])is str and re.fullmatch("[a-f0-9]{64}",p["sha256"])is not None,"file pin")
def checked(raw,p):
    filepin(p);require(len(raw)==p["bytes"] and sha(raw)==p["sha256"],"byte identity");return raw
def api(path,raw=False):
    cmd=["gh","api","repos/"+REPO+"/"+path]
    if raw:cmd+=["-H","Accept: application/octet-stream","--allow-escape-sequences"]
    b=subprocess.check_output(cmd,stderr=subprocess.PIPE)
    return b if raw else decode(b)
def source_gate():
    require(os.environ.get("GITHUB_ACTIONS")=="true" and os.environ.get("GITHUB_REPOSITORY")==REPO,"hosted only")
    require(os.environ.get("GITHUB_EVENT_NAME")=="workflow_dispatch" and os.environ.get("GITHUB_REF")=="refs/heads/"+BRANCH,"exact manual branch")
    head=os.environ["GITHUB_SHA"]
    require(re.fullmatch("[a-f0-9]{40}",head)is not None,"source SHA")
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==head,"checkout source")
    m=decode((ROOT/MANIFEST).read_bytes())
    for n,p in m["files"].items():
        valid_name(n);filepin(p);require(not(ROOT/n).is_symlink()and(ROOT/n).is_file(),"protected regular source")
        require(pin(ROOT/n)==p,"protected source "+n)
    c=decode((ROOT/CONFIG).read_bytes())
    require(c["producer_run"]==41211382427 and c["producer_source"]=="ddc1cbddf68096c5e976bf9acda5c5fb0168c5b9","producer source")
    require(c["read_only"]is True and c["physical_acceptance"]is False,"readonly source")
    return c,head
def immutable_release(r):
    return dict(id=r["id"],tag_name=r["tag_name"],target_commitish=r["target_commitish"],
      draft=r["draft"],prerelease=r["prerelease"],
      assets=sorted([dict(id=a["id"],name=a["name"],size=a["size"],digest=a["digest"])for a in r["assets"]],key=lambda a:a["name"]))
def producer(c):
    run=api("actions/runs/"+str(c["producer_run"]))
    require(run["head_sha"]==c["producer_source"]and run["status"]=="completed"and run["conclusion"]=="failure"and run["run_attempt"]==1,"original terminal failure")
    release=api("releases/"+str(c["release_id"]))
    ref=api("git/ref/tags/"+c["release_tag"])
    require(release["id"]==c["release_id"]and release["tag_name"]==c["release_tag"]and release["target_commitish"]==c["producer_source"]and release["draft"]is False and release["prerelease"]is True,"original release source")
    require(ref["object"]=={"type":"commit","sha":c["producer_source"],"url":ref["object"]["url"]},"original tag")
    assets={a["name"]:a for a in release["assets"]}
    require(len(assets)==len(release["assets"])and set(assets)==set(c["assets"]),"exact original assets")
    for n,p in c["assets"].items():
        a=assets[n];require(a["id"]==p["id"]and a["size"]==p["bytes"]and a["digest"]=="sha256:"+p["sha256"],"original asset identity")
    return dict(run=run,release=release,ref=ref)
def destination(head,empty,expected=None):
    tag="cloud-results-"+os.environ["GITHUB_RUN_ID"]+"-"+os.environ["GITHUB_RUN_ATTEMPT"]+"-"+GROUP
    release=api("releases/tags/"+tag);ref=api("git/ref/tags/"+tag)
    require(release["tag_name"]==tag and release["target_commitish"]==head and release["draft"]is False and release["prerelease"]is True,"independent destination")
    require(ref["object"]["type"]=="commit"and ref["object"]["sha"]==head,"destination tag source")
    require(str(release["id"])!="429993235","original release immutable")
    if empty:require(release["assets"]==[],"destination must start empty")
    if expected is not None:
        assets={a["name"]:a for a in release["assets"]}
        require(len(assets)==len(release["assets"])and set(assets)==set(expected),"complete exact published set")
        for n,p in expected.items():require(assets[n]["size"]==p["bytes"]and assets[n]["digest"]=="sha256:"+p["sha256"],"published bytes")
    return tag,release
def scan(archive,index,selected,out):
    """Authenticate every regular member; copy only exact pinned reports, never extractall."""
    require(type(index)is dict and index and set(selected)<=set(index),"selected indexed set")
    parents=set()
    for n,p in index.items():
        valid_name(n);filepin(p);parents.update(str(x)for x in PurePosixPath(n).parents if str(x)!=".")
    require(not out.exists(),"exclusive output root");out.mkdir()
    seen=set();dirs=set();observed={};captured={}
    with tarfile.open(archive,"r|gz")as tf:
        for m in tf:
            n=m.name
            if m.isdir():
                n=n.rstrip("/");valid_name(n);require(n in parents and n not in dirs,"exact parent directory");dirs.add(n);continue
            valid_name(n);require(m.isfile()and not m.issym()and not m.islnk(),"regular archive member only")
            require(n in index and n not in seen,"exact unique indexed member");seen.add(n)
            require(m.size==index[n]["bytes"],"native member size")
            h=hashlib.sha256();count=0;target=None
            if n in selected:
                require(n.endswith((".json",".jsonl",".stdout",".stderr",".log",".tcl")),"report whitelist")
                target=out/n;target.parent.mkdir(parents=True,exist_ok=True)
            stream=tf.extractfile(m);require(stream is not None,"regular stream")
            with stream:
                sink=target.open("xb")if target is not None else None
                try:
                    while True:
                        b=stream.read(1024*1024)
                        if not b:break
                        count+=len(b);h.update(b)
                        if sink:sink.write(b)
                finally:
                    if sink:sink.close()
            actual=dict(bytes=count,sha256=h.hexdigest());require(actual==index[n],"native member hash "+n);observed[n]=actual
            if target is not None:
                raw=target.read_bytes();checked(raw,actual)
                if n.endswith(".json"):decode(raw)
                else:raw.decode("utf-8")
                captured[n]=actual
    require(seen==set(index),"complete native member census")
    require(set(captured)==set(selected),"complete selected reports")
    return dict(all_members=observed,reports=captured)
def download(c,n,dest):
    a=c["assets"][n];require(not dest.exists(),"exclusive transport")
    cmd=["gh","api","repos/"+REPO+"/releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream","--allow-escape-sequences"]
    with dest.open("xb")as f:subprocess.run(cmd,stdout=f,check=True)
    require(pin(dest)==dict(bytes=a["bytes"],sha256=a["sha256"]),"asset transport bytes")
def run():
    c,head=source_gate()
    require(os.environ.get("GITHUB_JOB")=="readback"and os.environ.get("MODE")=="readback"and os.environ.get("APPROVED_SOURCE")==head,"reviewed exact source dispatch")
    require(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","one original attempt")
    before=producer(c)
    # Independent reservation is created by the coordinator, never by this worker.
    deadline=time.monotonic()+180
    while True:
        try:tag,reservation=destination(head,True);break
        except subprocess.CalledProcessError as exc:
            if b"HTTP 404"not in (exc.stderr or b"")or time.monotonic()>=deadline:raise
            time.sleep(2)
    require(not OUT.exists(),"exclusive evidence root");OUT.mkdir()
    work=ROOT/"terminal-inputs";work.mkdir(exist_ok=False)
    (OUT/"producer-before.json").write_bytes(encode(before))
    (OUT/"reservation-before.json").write_bytes(encode(reservation))
    try:
        for n in c["assets"]:download(c,n,work/n)
        index=decode((work/"candidate-outputs.json").read_bytes())
        parts=decode((work/"candidate-parts.json").read_bytes())
        require(index["run"]==c["producer_run"]and index["source"]==c["producer_source"]and index["attempt"]==1,"index producer")
        require(all(index[k]is False for k in("physical_acceptance","timing_accepted","full_phy_accepted")),"original rejection retained")
        require(index["files"]==c["members"],"frozen complete native index")
        require(parts==c["parts"],"frozen part manifest")
        archive=work/"native.tar.gz"
        with archive.open("xb")as f:
            for part in parts["parts"]:
                valid_name(part["name"])
                with(work/part["name"]).open("rb")as inp:
                    while True:
                        b=inp.read(1024*1024)
                        if not b:break
                        f.write(b)
        require(pin(archive)==parts["archive"],"complete native archive")
        report=scan(archive,index["files"],c["selected"],OUT/"reports")
        after=producer(c)
        require(immutable_release(before["release"])==immutable_release(after["release"])and before["ref"]==after["ref"],"producer publication unchanged")
        (OUT/"producer-after.json").write_bytes(encode(after))
        (OUT/"candidate-outputs.json").write_bytes((work/"candidate-outputs.json").read_bytes())
        (OUT/"candidate-parts.json").write_bytes((work/"candidate-parts.json").read_bytes())
        result=dict(status="PASS_AUTHENTICATED_REJECTED_ROUTING_REPORT_READBACK",producer_run=c["producer_run"],producer_source=c["producer_source"],source=head,run=int(os.environ["GITHUB_RUN_ID"]),archive=parts["archive"],all_members_authenticated=len(report["all_members"]),selected_reports=len(report["reports"]),report_pins=report["reports"],native_tools_executed=False,reroute_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
        (OUT/"result.json").write_bytes(encode(result))
        files=sorted(p for p in OUT.rglob("*")if p.is_file())
        # Preserve relative names in an explicit catalog; release asset names are unique path hashes.
        expected={};catalog={}
        pub=ROOT/"terminal-publication";pub.mkdir(exist_ok=False)
        for p in files:
            relative=p.relative_to(OUT).as_posix();name=sha(relative.encode())[:16]+"-"+p.name
            require(name not in expected,"unique report asset")
            actual=pin(p)
            if actual["bytes"]==0:
                catalog[relative]=dict(name=None,embedded_empty=True,**actual);continue
            dest=pub/name;dest.write_bytes(p.read_bytes());expected[name]=actual;catalog[relative]=dict(name=name,**actual)
        catalog_raw=encode(dict(source=head,run=int(os.environ["GITHUB_RUN_ID"]),files=catalog,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
        (pub/"readback-catalog.json").write_bytes(catalog_raw);expected["readback-catalog.json"]=pin(pub/"readback-catalog.json")
        destination(head,True)
        for n in expected:subprocess.run(["gh","release","upload",tag,str(pub/n),"--repo",REPO],check=True)
        _,published=destination(head,False,expected)
        receipt=dict(tag=tag,release_id=published["id"],source=head,files=dict(expected),receipt_self_not_in_files=True,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
        receipt_path=OUT/"publication-receipt.json";receipt_path.write_bytes(encode(receipt))
        subprocess.run(["gh","release","upload",tag,str(receipt_path),"--repo",REPO],check=True)
        expected["publication-receipt.json"]=pin(receipt_path)
        destination(head,False,expected)
        print(json.dumps(result),flush=True)
    except BaseException as exc:
        (OUT/"collector-failure.json").write_bytes(encode(dict(error_type=type(exc).__name__,error=str(exc),physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)))
        raise
def main():
    p=argparse.ArgumentParser();p.add_argument("--controls",action="store_true");a=p.parse_args()
    if a.controls:
        c,head=source_gate();print(json.dumps(dict(status="PASS_SOURCE_BINDING_ONLY",source=head,selected_reports=len(c["selected"]),native_members=len(c["members"]),native_executed=False)))
    else:run()
if __name__=="__main__":main()
