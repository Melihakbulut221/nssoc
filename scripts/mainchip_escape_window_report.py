#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only complete archive verification and exact derived window projection."""
import argparse,base64,copy,hashlib,io,json,os,re,subprocess,tarfile,traceback
from pathlib import Path,PurePosixPath
import wait_cloud_tested_source_release as reservation
ROOT=Path(__file__).resolve().parents[1]
PREFIX="docs/evidence/mainchip-antenna-escape-window-terminal-41009878507/"
PRODUCER=41009878507
SOURCE="bf0aff5864426372775cadc0fdf16118cae19d68"
RELEASE=428690818
GROUP="mainchip-escape-window-report"
BRANCH="codex/mainchip-net459-diode-prune"
ARCHIVE=691119098
ARCHIVE_BYTES=43869939
ARCHIVE_SHA="ea3f02e646e8f1a83b08539d8719b738a032636cf022fbd3504cfdd5afef1db5"
WINDOW="antenna-escape-window/ownership-window.json"
TECH="antenna-escape-window/technology.lef"
def sha(b):return hashlib.sha256(b).hexdigest()
def encoded(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def api(path,raw=False):
    cmd=["gh","api","repos/Melihakbulut221/nssoc/"+path]
    if raw:cmd+=["--allow-escape-sequences","-H","Accept: application/octet-stream"]
    b=subprocess.check_output(cmd)
    return b if raw else json.loads(b)
def guard():
    e=os.environ
    assert e.get("GITHUB_ACTIONS")=="true" and e.get("RUNNER_ENVIRONMENT")=="github-hosted"
    assert e.get("RUNNER_OS")=="Linux" and e.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"
    assert e.get("GITHUB_EVENT_NAME")=="workflow_dispatch" and e.get("GITHUB_RUN_ATTEMPT")=="1"
    assert e.get("GITHUB_REF")=="refs/heads/"+BRANCH and re.fullmatch("[0-9a-f]{40}",e["GITHUB_SHA"])
    assert subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==e["GITHUB_SHA"]
    m=json.loads((ROOT/"scripts/mainchip-escape-window-report-pins.json").read_bytes())
    for p,h in m["protected_sha256"].items():
        f=ROOT/p
        assert f.is_file() and not f.is_symlink() and sha(f.read_bytes())==h,p
    assert m["readback_authorized"] is True and m["native_design_execution_authorized"] is False
    return m
def scan(raw,expected,selection,limit):
    """Hash every regular member; retain selected bytes without extracting any paths."""
    found={};selected={};total=0
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz") as t:
        for member in t:
            name=member.name;p=PurePosixPath(name)
            assert str(p)==name and not p.is_absolute() and ".." not in p.parts and name
            assert not any(c in name for c in ("\\",":","\x00"))
            assert member.isfile() and member.sparse is None and name not in found and name in expected
            spec=expected[name];assert member.size==spec["bytes"] and member.size>=0
            total+=member.size;assert total<=limit
            digest=hashlib.sha256();size=0;keep=[]
            with t.extractfile(member) as f:
                while True:
                    b=f.read(1024**2)
                    if not b:break
                    size+=len(b);digest.update(b)
                    if name in selection:keep.append(b)
            observed=dict(bytes=size,sha256=digest.hexdigest())
            assert observed==spec,name
            found[name]=observed
            if name in selection:selected[name]=b"".join(keep)
    assert found==expected and set(selected)==set(selection)
    return selected,found
def fixture(entries):
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode="w:gz") as t:
        for name,body,kind in entries:
            item=tarfile.TarInfo(name);item.type=kind;item.size=len(body) if kind==tarfile.REGTYPE else 0
            if kind==tarfile.SYMTYPE:item.linkname="a"
            t.addfile(item,io.BytesIO(body) if item.isfile() else None)
    return out.getvalue()
def controls():
    data={"a":b"a","b":b""};spec={n:dict(bytes=len(b),sha256=sha(b))for n,b in data.items()}
    good=fixture([(n,b,tarfile.REGTYPE)for n,b in data.items()])
    selected,found=scan(good,spec,{"a"},1);assert selected=={"a":b"a"} and found==spec
    failures=[]
    def refuse(name,raw,expected=spec,limit=1):
        try:scan(raw,expected,{"a"},limit)
        except(AssertionError,tarfile.TarError):failures.append(name)
        else:raise AssertionError("Accepted archive mutation "+name)
    for name,entries in [
      ("duplicate",[("a",b"a",tarfile.REGTYPE),("a",b"a",tarfile.REGTYPE)]),
      ("parent",[("../a",b"a",tarfile.REGTYPE)]),
      ("absolute",[("/a",b"a",tarfile.REGTYPE)]),
      ("symlink",[("a",b"",tarfile.SYMTYPE)]),
      ("directory",[("a",b"",tarfile.DIRTYPE)]),
      ("missing",[("a",b"a",tarfile.REGTYPE)]),
      ("extra",[("a",b"a",tarfile.REGTYPE),("b",b"",tarfile.REGTYPE),("x",b"",tarfile.REGTYPE)]),
      ("hash",[("a",b"x",tarfile.REGTYPE),("b",b"",tarfile.REGTYPE)])]:
        refuse(name,fixture(entries))
    refuse("limit",good,limit=0)
    changed=copy.deepcopy(spec);changed["b"]["bytes"]=1;refuse("size",good,changed)
    assert len(failures)==10
    return dict(status="PASS_COMPLETE_ARCHIVE_READBACK_CONTROLS",positive=1,refusal=10,cases=failures,
      native_payload_acquired=False,native_design_executed=False)
def project(selected):
    w=json.loads(selected[WINDOW])
    assert w["status"]=="COMPLETE_NATIVE_ALL_LAYER_WINDOW_DIAGNOSTIC_ONLY"
    assert w["window_DBU"]==[95000,501000,102000,512500] and w["read_only"] is True
    assert w["all_net_count"]==143820 and w["instance_count"]==153129
    assert w["every_block_terminal_reconciled_with_connected_net_census"] is True
    assert len(w["unclipped_intersecting_geometry"])==249
    assert len({r["record_id"]for r in w["unclipped_intersecting_geometry"]})==249
    removed={"full_source_material","via_definitions"}
    out={k:v for k,v in w.items()if k not in removed}
    out["excluded_complete_sections"]={k:dict(canonical_sha256=sha(encoded(w[k])),
      scope="Complete section remains in the immutable original report; no source bytes discarded") for k in sorted(removed)}
    # Tokenized layer declarations, never a DRC/clearance interpretation.
    layers={};name=None;lines=[]
    for line in selected[TECH].decode().splitlines():
        tokens=line.strip().split()
        if name is None and len(tokens)==2 and tokens[0]=="LAYER":
            name=tokens[1];lines=[]
        elif name is not None and tokens==["END",name]:
            assert name not in layers;layers[name]=lines;name=None
        elif name is not None:lines.append(tokens)
    assert name is None and layers
    out["native_technology_layer_tokens"]=layers
    out["layer_token_scope"]="Exact whitespace tokenization of complete LAYER declarations; no LEF semantic parser or clearance proof."
    out["original_window_report"]=dict(bytes=len(selected[WINDOW]),sha256=sha(selected[WINDOW]))
    out["original_technology_lef"]=dict(bytes=len(selected[TECH]),sha256=sha(selected[TECH]))
    out["source_geometry_mutated"]=False
    out["native_design_executed"]=False
    out["route_generated"]=False
    assert all(out[k] is False for k in ("physical_acceptance","timing_accepted","full_phy_accepted"))
    return out
def readback():
    proof=reservation.wait(GROUP,os.environ)
    assert proof["externally_reserved"] is True and proof["creation_attempted"] is False
    assert not proof["existing_assets"],"Fresh output reservation is not empty"
    run=api("actions/runs/"+str(PRODUCER));jobs=api("actions/runs/"+str(PRODUCER)+"/attempts/1/jobs?per_page=100")
    assert run["head_sha"]==SOURCE and run["status"]=="completed" and run["conclusion"]=="success" and run["run_attempt"]==1
    expected={"source-controls":"success","preserve-job-log":"success","window":"success","preserve-antenna-job-logs":"success",
      "ownership":"skipped","antenna-readback":"skipped","trial":"skipped","candidate":"skipped"}
    assert jobs["total_count"]==8 and {j["name"]:j["conclusion"]for j in jobs["jobs"]}==expected
    assert all(j["status"]=="completed" and j["head_sha"]==SOURCE for j in jobs["jobs"])
    receipt=json.loads((ROOT/(PREFIX+"receipt.json")).read_bytes())
    rel=api("releases/"+str(RELEASE));tag=api("git/ref/tags/"+rel["tag_name"])
    assert rel["target_commitish"]==SOURCE and tag["object"]["sha"]==SOURCE and not rel["draft"] and rel["prerelease"]
    pins={x["id"]:x for x in receipt["native_assets"]};assets={x["id"]:x for x in rel["assets"]}
    assert set(pins)==set(assets)
    for aid,pin in pins.items():
        a=assets[aid];assert a["name"]==pin["name"] and a["size"]==pin["bytes"] and a["digest"]=="sha256:"+pin["sha256"]
    inventory=json.loads((ROOT/(PREFIX+"capsule-index/candidate-outputs.json")).read_bytes())
    assert inventory["source"]==SOURCE and inventory["run"]==PRODUCER and inventory["attempt"]==1 and len(inventory["files"])==15
    raw=api("releases/assets/"+str(ARCHIVE),raw=True)
    assert len(raw)==ARCHIVE_BYTES and sha(raw)==ARCHIVE_SHA
    selected,found=scan(raw,inventory["files"],{WINDOW,TECH},400*1024**2)
    result=project(selected)
    result.update(readback_source=os.environ["GITHUB_SHA"],readback_run=int(os.environ["GITHUB_RUN_ID"]),
      producer=PRODUCER,producer_source=SOURCE,reservation=proof,complete_archive=dict(bytes=len(raw),sha256=sha(raw)),
      complete_native_members=found,all_original_members_stream_hashed=True)
    return result
def emit(path):
    raw=path.read_bytes()
    print("ESCAPE_WINDOW_REPORT_INDEX "+json.dumps(dict(path=path.name,bytes=len(raw),sha256=sha(raw),
      chunks=(len(raw)+5999)//6000)),flush=True)
    for i in range(0,len(raw),6000):
        print("ESCAPE_WINDOW_REPORT_CHUNK "+json.dumps(dict(path=path.name,index=i//6000,base64=base64.b64encode(raw[i:i+6000]).decode())),flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--controls",action="store_true");parser.add_argument("--readback",action="store_true");args=parser.parse_args()
    assert args.controls != args.readback
    folder=ROOT/"cloud-window-report";folder.mkdir(exist_ok=True)
    name="controls.json" if args.controls else "result.json";path=folder/name
    assert not path.exists()
    result=dict(status="FAIL_ESCAPE_WINDOW_REPORT",native_design_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
    primary=None
    try:
        guard();result=controls() if args.controls else readback()
    except BaseException as error:
        primary=error;result.update(error=repr(error),traceback=traceback.format_exc())
    finally:
        try:path.write_bytes(encoded(result));emit(path)
        except BaseException as error:
            if primary is None:primary=error
    if primary is not None:raise primary
if __name__=="__main__":main()
