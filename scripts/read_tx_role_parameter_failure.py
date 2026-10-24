#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only authentication of one rejected observer's small artifact; no native work."""
import argparse,base64,copy,hashlib,io,json,os,re,stat,subprocess,traceback,zipfile
from pathlib import Path,PurePosixPath
REPO="Melihakbulut221/nssoc"
RUN=40113558341
HEAD="363b5a863a4db52b2f364110eef229a02f2742b1"
JOB=120932026993
ARTIFACT=12568236017
ARTIFACT_BYTES=24447
ARTIFACT_SHA="782d01e15a26bf35abe00d1b9b2e2b44112c7fcac0398c3b441e06ed1dfa213f"
LOG_BYTES=46758
LOG_SHA="becf5a45b1f121af2f8b4662a75f82f4addb6bcad2dbdce7f535ce5baea000bc"
RESULT_BYTES=7386
RESULT_SHA="a89611df3c48af78133f22b988a3be7ff61f62081bb850be050bdf66f8c753bb"
FILES={
 "result.json":RESULT_SHA,
 "native-parameter-observer.log":"5f27de711304b10f35b78ecf1d262ab0f428917b6e166688347a4fa379375124",
 "tx-output8088-branchtailfeed-interfaces-source/parts.json":"278156444c2bd2159f6f029f8f3a9d51ad156d1a84a751ea41e4e75e6b5b6a51",
 "tx-output8088-branchtailfeed-interfaces-source/summary.json":"e872278654de17a300e5004c463a1ad37b5c9e1116ed7d8720e2872f8124c2b9",
 "native/original-interfaces.json":"13bfff54e68a5355547fc64e4ebdd64e347c5b54a43b8c924b9ece724b009aaf"}
OUT=Path("cloud-tx-role-parameter-failure-readback")
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/"scripts/tx-role-parameter-failure-readback-methods.json"
def sha(b):return hashlib.sha256(b).hexdigest()
def api(path,raw=False):
    args=["gh","api","--allow-escape-sequences","repos/"+REPO+"/"+path]
    p=subprocess.run(args,capture_output=True);assert p.returncode==0,(path,p.stderr.decode(errors="replace"))
    return p.stdout if raw else json.loads(p.stdout)
def host():
    assert os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    assert os.environ.get("GITHUB_REPOSITORY")==REPO
def pins():
    m=json.loads(METHOD.read_text())
    for p,h in m["protected"].items():assert sha((ROOT/p).read_bytes())==h,p
    return m
def run_identity(r,j,a):
    assert r["id"]==RUN and r["head_sha"]==HEAD and r["run_attempt"]==1
    assert r["head_branch"]=="codex/tx-clock-phase-parent"
    assert r["path"]==".github/workflows/tx-native-clock-role-parameters-cloud.yml"
    assert r["status"]=="completed"and r["conclusion"]=="failure"
    assert j["id"]==JOB and j["run_id"]==RUN and j["head_sha"]==HEAD and j["run_attempt"]==1
    assert j["name"]=="exact-native-role-parameters"and j["status"]=="completed"and j["conclusion"]=="failure"
    assert a["id"]==ARTIFACT and a["name"]=="tx-native-role-parameters-"+str(RUN)
    assert a["size_in_bytes"]==ARTIFACT_BYTES and a["digest"]=="sha256:"+ARTIFACT_SHA and a["expired"]is False
    ar=a["workflow_run"];assert ar["id"]==RUN and ar["head_sha"]==HEAD
    assert ar["head_branch"]=="codex/tx-clock-phase-parent"and ar["repository_id"]==1364721142 and ar["head_repository_id"]==1364721142
def report_identity(r):
    assert r["status"]=="FAIL_OR_ERROR"and r["source_head"]==HEAD and r["run_id"]==str(RUN)
    assert r["native_returncode"]==1 and "diagnosis"not in r
    assert r["error"]=="AssertionError('Actual role/source comparison or original rejection reproduction failed')"
    assert r["outputs"]=={k:v for k,v in FILES.items()if k!="result.json"}
    assert all(r[k]is False for k in ("native_role_accepted","electrical_accepted","full_phy_accepted"))
    assert r["no_new_extraction_or_simulation"]is True
def result_from_log(b):
    assert len(b)==LOG_BYTES and sha(b)==LOG_SHA
    chunks=[];sizes=[];hashes=[]
    for line in b.decode("utf-8").splitlines():
        m=re.fullmatch(r"\d{4}-\d\d-\d\dT\S+Z RESULT_BASE64 (\d+)/(\d+) ([A-Za-z0-9+/=]+)",line)
        if m:chunks.append((int(m[1]),int(m[2]),m[3]))
        m=re.fullmatch(r"\d{4}-\d\d-\d\dT\S+Z RESULT_BYTES (\d+)",line)
        if m:sizes.append(int(m[1]))
        m=re.fullmatch(r"\d{4}-\d\d-\d\dT\S+Z RESULT_SHA256 ([a-f0-9]{64})",line)
        if m:hashes.append(m[1])
    assert chunks and sizes==[RESULT_BYTES]and hashes==[RESULT_SHA]
    assert [x[0]for x in chunks]==list(range(len(chunks)))and all(x[1]==len(chunks)for x in chunks)
    result=base64.b64decode("".join(x[2]for x in chunks),validate=True)
    assert len(result)==RESULT_BYTES and sha(result)==RESULT_SHA
    report_identity(json.loads(result));return result
def zip_files(b,expected,byte_count,digest):
    assert len(b)==byte_count and sha(b)==digest
    parents={str(p) for n in expected for p in PurePosixPath(n).parents if str(p)!="."}
    files={};seen=set();total=0
    with zipfile.ZipFile(io.BytesIO(b))as z:
        assert z.comment==b""and len(z.infolist())<=len(expected)+len(parents)
        for i in z.infolist():
            n=i.filename
            assert n and "\\"not in n and "\0"not in n and not n.startswith("/")
            pure=PurePosixPath(n);assert ".."not in pure.parts and "."not in pure.parts and str(pure)==n.rstrip("/")
            assert n not in seen;seen.add(n)
            mode=i.external_attr>>16
            assert stat.S_IFMT(mode)in(0,stat.S_IFREG,stat.S_IFDIR)
            assert not(i.flag_bits&1)and i.compress_type in(zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED)
            if i.is_dir():
                assert n[:-1]in parents and i.file_size==0;continue
            assert n in expected and i.file_size<=300000
            total+=i.file_size;assert total<=400000
            data=z.read(i);assert len(data)==i.file_size and sha(data)==expected[n]
            files[n]=data
        assert set(files)==set(expected)
    return files
def controls():
    base=b"opaque\x1b[31m bytes\x00\xff"
    def packed(entries,comment=b""):
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w",compression=zipfile.ZIP_DEFLATED)as z:
            for n,d in entries:z.writestr(n,d)
            z.comment=comment
        return b.getvalue()
    positive=packed([("a.txt",base),("nested/b.txt",b"second")]);expected={"a.txt":sha(base),"nested/b.txt":sha(b"second")}
    assert zip_files(positive,expected,len(positive),sha(positive))=={"a.txt":base,"nested/b.txt":b"second"}
    tests=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,zipfile.BadZipFile,KeyError,ValueError,UnicodeError):tests.append({"name":name,"rejected":True})
        else:raise AssertionError("Accepted corruption "+name)
    reject("transport_truncated",lambda:zip_files(positive[:-1],expected,len(positive),sha(positive)))
    reject("transport_byte",lambda:zip_files(b"x"+positive[1:],expected,len(positive),sha(positive)))
    reject("wrong_expected_hash",lambda:zip_files(positive,{**expected,"a.txt":"0"*64},len(positive),sha(positive)))
    for name,entries in [
      ("missing",[("a.txt",base)]),("extra",[("a.txt",base),("nested/b.txt",b"second"),("extra",b"x")]),
      ("duplicate",[("a.txt",base),("a.txt",base)]),("traversal",[("../a.txt",base)]),
      ("absolute",[("/a.txt",base)]),("backslash",[("a\\b.txt",base)]),("empty_directory",[("unused/",b"")]),
      ("changed_member",[("a.txt",b"changed"),("nested/b.txt",b"second")])]:
        data=packed(entries);reject(name,lambda data=data:zip_files(data,expected,len(data),sha(data)))
    sy=zipfile.ZipInfo("a.txt");sy.external_attr=(stat.S_IFLNK|0o777)<<16
    data=packed([(sy,base)]);reject("symlink",lambda:zip_files(data,{"a.txt":sha(base)},len(data),sha(data)))
    data=packed([("a.txt",base),("nested/b.txt",b"second")],b"extra");reject("zip_comment",lambda:zip_files(data,expected,len(data),sha(data)))
    r={"id":RUN,"head_sha":HEAD,"run_attempt":1,"head_branch":"codex/tx-clock-phase-parent","path":".github/workflows/tx-native-clock-role-parameters-cloud.yml","status":"completed","conclusion":"failure"}
    j={"id":JOB,"run_id":RUN,"head_sha":HEAD,"run_attempt":1,"name":"exact-native-role-parameters","status":"completed","conclusion":"failure"}
    a={"id":ARTIFACT,"name":"tx-native-role-parameters-"+str(RUN),"size_in_bytes":ARTIFACT_BYTES,"digest":"sha256:"+ARTIFACT_SHA,"expired":False,"workflow_run":{"id":RUN,"head_sha":HEAD,"head_branch":"codex/tx-clock-phase-parent","repository_id":1364721142,"head_repository_id":1364721142}}
    run_identity(r,j,a)
    for key,val in [("head_sha","0"*40),("conclusion","success"),("run_attempt",2)]:
        bad=copy.deepcopy(r);bad[key]=val;reject("run_"+key,lambda bad=bad:run_identity(bad,j,a))
    for key,val in [("run_id",RUN+1),("name","controls")]:
        bad=copy.deepcopy(j);bad[key]=val;reject("job_"+key,lambda bad=bad:run_identity(r,bad,a))
    for key,val in [("expired",True),("digest","sha256:"+"0"*64),("size_in_bytes",ARTIFACT_BYTES+1)]:
        bad=copy.deepcopy(a);bad[key]=val;reject("artifact_"+key,lambda bad=bad:run_identity(r,j,bad))
    native=api("actions/jobs/"+str(JOB)+"/logs",raw=True);result=result_from_log(native)
    reject("original_log_strip_ANSI",lambda:result_from_log(re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]",b"",native)))
    reject("original_log_truncated",lambda:result_from_log(native[:-1]))
    rr=json.loads(result)
    for key,val in [("native_role_accepted",True),("native_returncode",0),("status","PASS"),("diagnosis",{})]:
        bad=copy.deepcopy(rr);bad[key]=val;reject("rejection_"+key,lambda bad=bad:report_identity(bad))
    assert len(tests)==27,len(tests)
    return {"status":"PASS_EXACT_FAILED_METADATA_AND27_CORRUPTIONS","faults":tests,"native_execution":False}
def main():
    p=argparse.ArgumentParser();p.add_argument("--controls",action="store_true");a=p.parse_args()
    host();m=pins();OUT.mkdir(exist_ok=False)
    result={"status":"RUNNING","source_head":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"method":m,"native_execution":False,"native_role_accepted":False,"electrical_accepted":False,"full_phy_accepted":False}
    try:
        if a.controls:result.update(controls())
        else:
            r=api("actions/runs/"+str(RUN));j=api("actions/jobs/"+str(JOB));ar=api("actions/artifacts/"+str(ARTIFACT));run_identity(r,j,ar)
            original=result_from_log(api("actions/jobs/"+str(JOB)+"/logs",raw=True))
            raw=api("actions/artifacts/"+str(ARTIFACT)+"/zip",raw=True)
            files=zip_files(raw,FILES,ARTIFACT_BYTES,ARTIFACT_SHA);assert files["result.json"]==original
            rr=json.loads(original);report_identity(rr)
            inner=files["native-parameter-observer.log"]
            result.update(status="PASS_EXACT_REJECTED_OBSERVER_LOG_READBACK_NOT_ROLE_ACCEPTANCE",original_run=r,original_job=j,artifact=ar,
              original_result=rr,original_result_sha256=RESULT_SHA,artifact_sha256=sha(raw),
              members={n:{"bytes":len(b),"sha256":sha(b)}for n,b in files.items()},
              inner_log_utf8=inner.decode("utf-8"),inner_log_sha256=sha(inner),original_rejection_unchanged=True)
            (OUT/"original-artifact.zip").write_bytes(raw)
            for n,b in files.items():
                f=OUT/"original"/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b)
        pins()
    except BaseException as e:
        result.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
    finally:
        b=(json.dumps(result,indent=2)+"\n").encode();(OUT/"result.json").write_bytes(b)
        print("READBACK_RESULT_SHA256",sha(b));print("READBACK_RESULT_BYTES",len(b))
        s=base64.b64encode(b).decode();chunks=[s[i:i+4096]for i in range(0,len(s),4096)]
        for i,c in enumerate(chunks):print(f"READBACK_RESULT_BASE64 {i}/{len(chunks)} {c}")
if __name__=="__main__":main()
