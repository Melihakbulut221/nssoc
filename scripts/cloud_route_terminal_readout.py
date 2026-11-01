#!/usr/bin/env python3
"""Read complete stopped router output on GitHub; never rerun native CAD."""
import hashlib,json,os,subprocess,tarfile,traceback
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"cloud-route-terminal-readout"
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def api(path):
    return json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/"+path],text=True))
def asset(a,dest):
    with dest.open("wb") as f:subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True)
    assert dest.stat().st_size==a["size"] and "sha256:"+sha(dest)==a["digest"]
def main():
    assert os.environ.get("GITHUB_ACTIONS")=="true" and os.environ["GITHUB_RUN_ATTEMPT"]=="1"
    OUT.mkdir(exist_ok=False);work=Path(os.environ["RUNNER_TEMP"])/"stopped-route-readout";work.mkdir(exist_ok=False)
    source="2b8931b9c8988fc5dbf497a7b561db579e39f64c";run=api("actions/runs/41270471645")
    assert run["head_sha"]==source and run["status"]=="completed" and run["conclusion"]=="failure"
    release=api("releases/430345631");assert release["target_commitish"]==source
    assert api("git/ref/tags/"+release["tag_name"])["object"]["sha"]==source
    assets={a["name"]:a for a in release["assets"]}
    expected={"candidate-outputs.json":(165920,"e8804df8799bfe6efc4a532dec18b60d36185edd719e531831840cf3847a0231"),
      "candidate-parts.json":(487,"e65b66ffdc6adbb524237735516690e93393b5849611b55d5a7f82b79f8c8427"),
      "candidate-native.tar.gz.part000":(536870912,"d108d322461a09412be8ba09794f98d98bb730467dfaa8e673db39238f8d6903"),
      "candidate-native.tar.gz.part001":(335857697,"3ec1c1294472d997cb88e3160e20acf7d6ef42bd8bfe20df05b77d3d5cc113a1")}
    assert set(assets)==set(expected)
    for n,(size,h) in expected.items():
        assert assets[n]["size"]==size and assets[n]["digest"]=="sha256:"+h
        asset(assets[n],work/n)
    index=json.loads((work/"candidate-outputs.json").read_text())
    parts=json.loads((work/"candidate-parts.json").read_text())
    archive=work/"native.tar.gz"
    with archive.open("wb") as out:
        for n in ("candidate-native.tar.gz.part000","candidate-native.tar.gz.part001"):
            with (work/n).open("rb") as f:
                for b in iter(lambda:f.read(1024*1024),b""):out.write(b)
    assert archive.stat().st_size==parts["archive"]["bytes"] and sha(archive)==parts["archive"]["sha256"]
    selected={"bulk-postdrt-supervision/bulk-postdrt-route.stdout","bulk-postdrt-supervision/bulk-postdrt-route.stderr",
      "bulk-postdrt-supervision/bulk-postdrt-route.command.json","work/bulk-postdrt-antenna/route.tcl",
      "bulk-postdrt-antenna/route-before-stale-wire-clear.tcl","bulk-postdrt-antenna/route-after-stale-wire-clear.tcl"}
    assert selected<=set(index["files"])
    seen={};members=set()
    with tarfile.open(archive,mode="r|gz") as tar:
        for m in tar:
            p=PurePosixPath(m.name)
            assert not p.is_absolute() and ".." not in p.parts and m.name not in members
            members.add(m.name)
            if m.isdir():continue
            assert m.isfile() and m.name in index["files"],m.name
            h=hashlib.sha256();n=0;f=tar.extractfile(m)
            target=OUT/"readback"/m.name if m.name in selected else None
            if target:target.parent.mkdir(parents=True,exist_ok=True)
            dest=target.open("wb") if target else None
            try:
                for b in iter(lambda:f.read(1024*1024),b""):
                    h.update(b);n+=len(b)
                    if dest:dest.write(b)
            finally:
                if dest:dest.close()
            pin=dict(bytes=n,sha256=h.hexdigest());assert pin==index["files"][m.name],m.name;seen[m.name]=pin
    assert set(seen)==set(index["files"])
    stdout=(OUT/"readback/bulk-postdrt-supervision/bulk-postdrt-route.stdout").read_text()
    command=json.loads((OUT/"readback/bulk-postdrt-supervision/bulk-postdrt-route.command.json").read_text())
    assert command["supervision_failure"]=="elapsed_limit" and command["returncode"]==-15
    result=dict(status="PASS_COMPLETE_ARCHIVE_AUTHENTICATION_AND_ROUTER_READOUT_ONLY",
      source=os.environ["GITHUB_SHA"],producer=source,producer_run=41270471645,release=430345631,
      authenticated_members=len(seen),selected_files={n:seen[n]for n in sorted(selected)},archive=parts["archive"],
      actual_route_command=command,full_phy_accepted=False,timing_accepted=False,physical_acceptance=False,
      native_cad_rerun=False,native_payloads_remain_cloud=True,
      router_tail=stdout.splitlines()[-120:])
    for n,v in [("result",result),("producer-run",run),("producer-release",release),("native-output-index",index),("native-parts",parts)]:
        (OUT/(n+".json")).write_text(json.dumps(v,indent=2)+"\n")
if __name__=="__main__":
    try:main()
    except BaseException as e:
        OUT.mkdir(exist_ok=True)
        (OUT/"failure.json").write_text(json.dumps(dict(error=repr(e),traceback=traceback.format_exc(),native_cad_rerun=False),indent=2)+"\n")
        raise
