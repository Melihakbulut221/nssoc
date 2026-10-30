#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only complete archive verification and full-stream DEF byte-difference diagnosis."""
import argparse,base64,copy,hashlib,io,itertools,json,os,re,subprocess,tarfile,traceback
from pathlib import Path,PurePosixPath
import wait_cloud_tested_source_release as reservation
ROOT=Path(__file__).resolve().parents[1]
PREFIX="docs/evidence/mainchip-multilayer-native-terminal-41106623617/"
PRODUCER=41106623617
SOURCE="8bc13f792ef3bc1f02a88f0340180adff72f38cd"
RELEASE=429356704
GROUP="mainchip-multilayer-def-diff"
BRANCH="codex/mainchip-net459-diode-prune"
ARCHIVE=693041904
ARCHIVE_BYTES=188049577
ARCHIVE_SHA="d06588d9d0770aecc6ad507302224820b18b9e3eaa0128b17430da8e7c5ac104"
SINGLE="work/multilayer-antenna-trial/candidate-single.def"
DOUBLE="work/multilayer-antenna-trial/candidate-double.def"
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
    m=json.loads((ROOT/"scripts/mainchip-multilayer-def-diff-pins.json").read_bytes())
    assert m["schema"]=="mainchip-multilayer-def-diff-pins-v1"
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

def compare_defs(a,b,limit=4*1024**2):
    """Compare every line in order; never normalize or discard a geometry difference."""
    assert isinstance(a,bytes) and isinstance(b,bytes) and type(limit)is int and limit>=0
    left=dict(bytes=len(a),sha256=sha(a));right=dict(bytes=len(b),sha256=sha(b))
    rows=[];changed=0;used=0;total=0;d=hashlib.sha256();left_lines=0;right_lines=0
    for number,(x,y)in enumerate(itertools.zip_longest(io.BytesIO(a),io.BytesIO(b)),1):
        if x is not None:left_lines+=1
        if y is not None:right_lines+=1
        if x==y:continue
        changed+=1
        row=dict(line=number,left=None if x is None else x.decode("ascii"),
                 right=None if y is None else y.decode("ascii"))
        raw=encoded(row);d.update(len(raw).to_bytes(8,"big"));d.update(raw);total+=len(raw)
        if used+len(raw)<=limit:rows.append(row);used+=len(raw)
    return dict(left=left,right=right,identical_bytes=a==b,left_line_count=left_lines,
      right_line_count=right_lines,changed_line_pairs=changed,
      difference_rows=rows,difference_rows_complete=len(rows)==changed,
      all_difference_rows_framed_sha256=d.hexdigest(),all_difference_rows_encoded_bytes=total,
      retained_difference_rows_encoded_bytes=used,difference_byte_limit=limit)
def all_controls():
    old=controls();positive=[];refusal=[]
    for label,a,b,changes in (
      ("equal",b"a\nb\n",b"a\nb\n",0),
      ("changed",b"a\nb\n",b"a\nc\n",1),
      ("inserted",b"a\n",b"a\nb\n",1),
      ("removed",b"a\nb\n",b"a\n",1),
      ("newline",b"a\n",b"a",1),
      ("reordered",b"a\nb\n",b"b\na\n",2)):
        r=compare_defs(a,b)
        assert r["identical_bytes"]is(a==b)and r["changed_line_pairs"]==changes
        assert r["difference_rows_complete"]is True and len(r["difference_rows"])==changes
        assert r["left"]==dict(bytes=len(a),sha256=sha(a))
        assert r["right"]==dict(bytes=len(b),sha256=sha(b))
        positive.append(label)
    r=compare_defs(b"a\nb\n",b"x\ny\n",0)
    assert r["changed_line_pairs"]==2 and r["difference_rows"]==[]and r["difference_rows_complete"]is False
    assert r["all_difference_rows_framed_sha256"]==compare_defs(b"a\nb\n",b"x\ny\n")["all_difference_rows_framed_sha256"]
    positive.append("bounded-output-still-hashes-every-difference")
    for label,a,b,lim in (("nonascii",b"\xff",b"x",100),("negative-budget",b"a",b"b",-1)):
        try:compare_defs(a,b,lim)
        except (AssertionError,UnicodeDecodeError):refusal.append(label)
        else:raise AssertionError("Accepted invalid difference input "+label)
    assert len(positive)==7 and len(refusal)==2
    return dict(status="PASS_MULTILAYER_DEF_DIFF_SOURCE_CONTROLS",archive_controls=old,
      diff_positive=7,diff_refusal=2,diff_positive_cases=positive,diff_refusal_cases=refusal,
      native_payload_acquired=False,native_design_executed=False)

def readback():
    proof=reservation.wait(GROUP,os.environ)
    assert proof["externally_reserved"] is True and proof["creation_attempted"] is False
    assert not proof["existing_assets"],"Fresh output reservation is not empty"
    run=api("actions/runs/"+str(PRODUCER));jobs=api("actions/runs/"+str(PRODUCER)+"/attempts/1/jobs?per_page=100")
    assert run["head_sha"]==SOURCE and run["status"]=="completed" and run["conclusion"]=="failure" and run["run_attempt"]==1
    expected={"source-controls":"success","preserve-job-log":"success","trial":"failure","preserve-antenna-job-logs":"failure"}
    assert jobs["total_count"]==4 and {j["name"]:j["conclusion"]for j in jobs["jobs"]}==expected
    assert all(j["status"]=="completed" and j["head_sha"]==SOURCE for j in jobs["jobs"])
    receipt=json.loads((ROOT/(PREFIX+"receipt.json")).read_bytes())
    rel=api("releases/"+str(RELEASE));tag=api("git/ref/tags/"+rel["tag_name"])
    assert rel["id"]==RELEASE and rel["tag_name"]=="cloud-results-41106623617-1-mainchip-multilayer-antenna-trial"
    assert tag["object"]["type"]=="commit"
    assert rel["target_commitish"]==SOURCE and tag["object"]["sha"]==SOURCE and not rel["draft"] and rel["prerelease"]
    publication=json.loads((ROOT/(PREFIX+"native-records/native-capsule-publication.json")).read_bytes())
    assert publication["status"]=="COMPLETE_PERMANENT_NATIVE_CAPSULE" and publication["source"]==SOURCE and publication["release_id"]==RELEASE
    pins={x["id"]:x for x in publication["assets"]};assets={x["id"]:x for x in rel["assets"]}
    assert set(pins)==set(assets)
    for aid,pin in pins.items():
        a=assets[aid];assert a["name"]==pin["name"] and a["size"]==pin["bytes"] and a["digest"]=="sha256:"+pin["sha256"]
    inventory=json.loads((ROOT/(PREFIX+"release-derived/candidate-outputs.json")).read_bytes())
    assert inventory["source"]==SOURCE and inventory["run"]==PRODUCER and inventory["attempt"]==1 and len(inventory["files"])==38 and inventory["files"]==publication["files"]
    raw=api("releases/assets/"+str(ARCHIVE),raw=True)
    assert len(raw)==ARCHIVE_BYTES and sha(raw)==ARCHIVE_SHA
    selected,found=scan(raw,inventory["files"],{SINGLE,DOUBLE},4*1024**3)
    result=compare_defs(selected[SINGLE],selected[DOUBLE])
    assert result["left"]==inventory["files"][SINGLE] and result["right"]==inventory["files"][DOUBLE]
    result.update(status="COMPLETE_READ_ONLY_DEF_BYTE_DIFFERENCE_DIAGNOSIS",source_geometry_mutated=False,
      native_design_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
      scope="Byte differences only. No semantic equivalence, connectivity, DRC, timing or PHY acceptance.",
      producer_failure_preserved="idempotent actual DEF import",original_exact_idempotence_gate_unchanged=True)
    result.update(readback_source=os.environ["GITHUB_SHA"],readback_run=int(os.environ["GITHUB_RUN_ID"]),
      producer=PRODUCER,producer_source=SOURCE,reservation=proof,complete_archive=dict(bytes=len(raw),sha256=sha(raw)),
      complete_native_members=found,all_original_members_stream_hashed=True)
    return result
def emit(path):
    raw=path.read_bytes()
    print("MULTILAYER_DEF_DIFF_INDEX "+json.dumps(dict(path=path.name,bytes=len(raw),sha256=sha(raw),
      chunks=(len(raw)+5999)//6000)),flush=True)
    for i in range(0,len(raw),6000):
        print("MULTILAYER_DEF_DIFF_CHUNK "+json.dumps(dict(path=path.name,index=i//6000,base64=base64.b64encode(raw[i:i+6000]).decode())),flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--controls",action="store_true");parser.add_argument("--readback",action="store_true");args=parser.parse_args()
    assert args.controls != args.readback
    folder=ROOT/"cloud-multilayer-def-diff";folder.mkdir(exist_ok=True)
    name="controls.json" if args.controls else "result.json";path=folder/name
    assert not path.exists()
    result=dict(status="FAIL_MULTILAYER_DEF_DIFF",native_design_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
    primary=None
    try:
        guard();result=all_controls() if args.controls else readback()
    except BaseException as error:
        primary=error;result.update(error=repr(error),traceback=traceback.format_exc())
    finally:
        try:path.write_bytes(encoded(result));emit(path)
        except BaseException as error:
            if primary is None:primary=error
    if primary is not None:raise primary
if __name__=="__main__":main()
