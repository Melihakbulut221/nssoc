#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bounded cloud-only artifact readback; emits only authenticated strict UTF-8 diagnostics."""
import argparse,base64,hashlib,io,json,os,re,stat,subprocess,unittest,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/mainchip-obstacle-failure-readback"
SPEC="scripts/mainchip-obstacle-failure-readback-inputs.json"
PINS="scripts/mainchip-obstacle-failure-readback-source.json"
OUT=ROOT/"obstacle-failure-evidence"
FLAGS=dict(native_tools_executed=False,routing_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
PRODUCER=41236517605
SOURCE="65e620dc413389fffaa8389e4abdfc17cfbf4ecf"
WORKERS={"nssoc/nssoc/obstacle-worker.stdout","nssoc/nssoc/obstacle-worker.stderr"}
PREFIXES=("nssoc/nssoc/obstacle-readback/","_temp/mainchip-drt-obstacle-readback-41236517605-1/out/")
def require(value,message):
    if not value:raise AssertionError(message)
def encode(v):return(json.dumps(v,sort_keys=True,indent=2)+"\n").encode()
def pin(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def api(path,binary=False):
    args=["gh","api","--allow-escape-sequences","repos/Melihakbulut221/nssoc/"+path]
    if binary:args+=["-H","Accept: application/octet-stream"]
    raw=subprocess.check_output(args,stderr=subprocess.PIPE,timeout=180)
    return raw if binary else json.loads(raw)
def safe(name):
    p=PurePosixPath(name)
    require(bool(name)and str(p)==name and not p.is_absolute()and".."not in p.parts and"\\"not in name and"\x00"not in name,"canonical member path")
    return p
def selected(name):
    p=safe(name)
    if name in WORKERS:return True
    if not any(name.startswith(prefix)for prefix in PREFIXES):return False
    if name.startswith(PREFIXES[1]+"work/"):return False
    suffixes=[s.lower()for s in p.suffixes]
    if set(suffixes)&{".odb",".gds",".gds2",".oas",".def",".lef",".spef",".spice",".sp",".l2n",".bin",".tar",".gz",".zip",".7z"}:return False
    return bool(suffixes)and(suffixes[-1]in(".json",".jsonl",".stdout",".stderr",".log")or suffixes[-2:]in([".json",".partial"],[".jsonl",".partial"]))
def read_archive(raw,expected,count,required):
    require(pin(raw)==expected,"exact entire artifact ZIP")
    members={};texts={};total=0
    with zipfile.ZipFile(io.BytesIO(raw))as z:
        rows=z.infolist();require(len(rows)==count,"complete uploaded regular member census")
        for row in rows:
            name=row.filename;safe(name);require(name not in members,"duplicate member")
            mode=(row.external_attr>>16)&0xffff
            require(not row.is_dir()and stat.S_IFMT(mode)in(0,stat.S_IFREG)and not(row.flag_bits&1),"regular unencrypted artifact file")
            require(0<=row.file_size<=16*1024**2,"bounded member")
            total+=row.file_size;require(total<=64*1024**2,"bounded full expanded artifact")
            chosen=selected(name);digest=hashlib.sha256();chunks=[];size=0
            with z.open(row)as stream:
                while True:
                    block=stream.read(1024**2)
                    if not block:break
                    size+=len(block);require(size<=row.file_size,"bounded actual member")
                    digest.update(block)
                    if chosen:chunks.append(block)
            require(size==row.file_size,"complete CRC-checked member")
            members[name]=dict(bytes=size,sha256=digest.hexdigest(),crc32=row.CRC,derived_text_selected=chosen)
            if chosen:
                data=b"".join(chunks);data.decode("utf-8","strict");texts[name]=data
    require(set(required)<=set(texts),"required complete worker streams")
    return dict(archive=expected,member_count=len(members),expanded_bytes=total,files=members,
      every_member_authenticated=True,unknown_native_bytes_retained_only_in_cloud=True),texts
def context():
    e=os.environ
    require(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted"and e.get("RUNNER_OS")=="Linux","hosted Linux")
    require(e.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"and e.get("GITHUB_EVENT_NAME")=="workflow_dispatch","manual repository")
    require(e.get("GITHUB_REF")=="refs/heads/"+BRANCH and e.get("GITHUB_JOB")=="readback"and e.get("GITHUB_RUN_ATTEMPT")=="1","dedicated actual branch/job/attempt")
    require(e.get("GITHUB_WORKFLOW_REF")=="Melihakbulut221/nssoc/.github/workflows/cloud-evidence-summary.yml@refs/heads/"+BRANCH,"actual workflow")
    source=e.get("GITHUB_SHA","");require(re.fullmatch("[0-9a-f]{40}",source)and e.get("APPROVED_SOURCE")==source,"explicit exact source")
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==source,"actual checkout")
    raw=(ROOT/PINS).read_bytes();require(raw==subprocess.check_output(["git","show",source+":"+PINS],cwd=ROOT),"immutable manifest")
    m=json.loads(raw)
    require(m["native_execution_authorized"]is False and m["artifact_readback_authorized"]is True,"readback only")
    for name,p in m["files"].items():
        safe(name);path=ROOT/name;require(path.is_file()and not path.is_symlink()and pin(path.read_bytes())==p,"exact protected source "+name)
    return dict(source=source,run=int(e["GITHUB_RUN_ID"]),attempt=1)
def producer(spec):
    run=api("actions/runs/"+str(PRODUCER));job=api("actions/jobs/124641511122")
    a=api("actions/artifacts/"+str(spec["artifact"]["id"]))
    require((run["id"],run["head_sha"],run["head_branch"],run["run_attempt"],run["status"],run["conclusion"])==
      (PRODUCER,SOURCE,"codex/mainchip-drt-obstacle-readback",1,"completed","failure"),"exact failed producer")
    require((job["id"],job["run_id"],job["head_sha"],job["run_attempt"],job["status"],job["conclusion"],job["name"])==
      (124641511122,PRODUCER,SOURCE,1,"completed","failure","observation"),"exact failed observer job")
    p=spec["artifact"];require((a["id"],a["name"],a["size_in_bytes"],a["digest"],a["expired"])==
      (p["id"],p["name"],p["bytes"],"sha256:"+p["sha256"],False),"exact uploaded artifact")
    w=a["workflow_run"];require((w["id"],w["head_sha"],w["head_branch"],w["repository_id"],w["head_repository_id"])==
      (PRODUCER,SOURCE,"codex/mainchip-drt-obstacle-readback",1364721142,1364721142),"artifact producer identity")
    return dict(run=run,job=job,artifact=a)
def artifact_identity(a):return{k:a[k]for k in("id","name","size_in_bytes","digest","expired","workflow_run")}
def emit(name,raw):
    raw.decode("utf-8","strict");parts=[raw[i:i+24000]for i in range(0,len(raw),24000)]or[b""]
    print("OBSTACLE_FAILURE_INDEX "+json.dumps(dict(path=name,**pin(raw),chunks=len(parts)),sort_keys=True),flush=True)
    for i,b in enumerate(parts):print("OBSTACLE_FAILURE_CHUNK "+json.dumps(dict(path=name,index=i,base64=base64.b64encode(b).decode()),sort_keys=True),flush=True)
def main():
    ctx=context();spec=json.loads((ROOT/SPEC).read_bytes())
    require(spec["producer_run"]==PRODUCER and spec["producer_source"]==SOURCE and spec["member_count"]==68,"exact configured producer")
    require(spec["artifact"]==dict(id=13056264389,name="mainchip-drt-obstacle-observation-41236517605-1",bytes=494882,sha256="e8de490cadbad36c2a969acc5e50f454fd63b2dbd05cb2550ab337fad133725a"),"exact small authenticated artifact")
    require(not OUT.exists(),"exclusive readback output");OUT.mkdir()
    before=producer(spec);(OUT/"producer-before.json").write_bytes(encode(before))
    raw=api("actions/artifacts/13056264389/zip",True)
    index,texts=read_archive(raw,{k:spec["artifact"][k]for k in("bytes","sha256")},68,WORKERS)
    after=producer(spec);require(artifact_identity(before["artifact"])==artifact_identity(after["artifact"]),"unchanged authentic artifact")
    (OUT/"producer-after.json").write_bytes(encode(after))
    (OUT/"complete-member-index.json").write_bytes(encode(index))
    for name,data in texts.items():
        path=OUT/"derived"/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    result=dict(status="COMPLETE_CLOUD_ONLY_FAILED_OBSERVER_DIAGNOSTIC_READBACK",**ctx,producer_source=SOURCE,producer_run=PRODUCER,
      artifact_id=13056264389,archive=index["archive"],members=68,derived_text_files=len(texts),unknown_native_files=68-len(texts),
      complete_archive_authenticated=True,selected_worker_streams_complete=True,**FLAGS)
    (OUT/"result.json").write_bytes(encode(result))
    print(json.dumps(result,sort_keys=True))
    context()
class Controls(unittest.TestCase):
    def archive(self,rows):
        out=io.BytesIO()
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED)as z:
            for n,b in rows:z.writestr(n,b)
        return out.getvalue()
    def runrows(self,rows,required=()):
        raw=self.archive(rows);return read_archive(raw,pin(raw),len(rows),set(required))
    def test_complete_selected_unknown(self):
        rows=[("nssoc/nssoc/obstacle-worker.stderr",b"actual failure\n"),("nssoc/nssoc/obstacle-readback/result.json",b'{"status":"FAIL"}'),("nssoc/nssoc/obstacle-readback/native/unexpected.odb.partial",b"\x00\xff")]
        index,texts=self.runrows(rows,{rows[0][0]})
        self.assertEqual(len(index["files"]),3);self.assertEqual(set(texts),{rows[0][0],rows[1][0]})
        self.assertFalse(index["files"][rows[2][0]]["derived_text_selected"])
    def test_wrong_archive_digest(self):
        raw=self.archive([("a",b"x")]);bad=dict(pin(raw),sha256="0"*64)
        with self.assertRaisesRegex(AssertionError,"artifact ZIP"):read_archive(raw,bad,1,set())
    def test_wrong_member_census(self):
        raw=self.archive([("a",b"x")])
        with self.assertRaisesRegex(AssertionError,"member census"):read_archive(raw,pin(raw),2,set())
    def test_path_and_duplicate(self):
        for name in("../x","/x","x\\y","x/../y"):
            with self.subTest(name=name),self.assertRaisesRegex(AssertionError,"canonical"):self.runrows([(name,b"x")])
        with self.assertRaisesRegex(AssertionError,"duplicate"):self.runrows([("x",b"a"),("x",b"b")])
    def test_strict_utf8_and_known_kind(self):
        with self.assertRaises(UnicodeError):self.runrows([("nssoc/nssoc/obstacle-worker.stderr",b"\xff")])
        _,texts=self.runrows([("nssoc/nssoc/obstacle-readback/binary.partial",b"\xff"),("nssoc/nssoc/obstacle-readback/result.jsonl.partial",b'{"partial":')])
        self.assertEqual(list(texts),["nssoc/nssoc/obstacle-readback/result.jsonl.partial"])
    def test_missing_required_stream(self):
        with self.assertRaisesRegex(AssertionError,"required"):self.runrows([("a",b"x")],WORKERS)
    def test_symlink_refused(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w")as z:
            i=zipfile.ZipInfo("link");i.create_system=3;i.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(i,b"target")
        raw=b.getvalue()
        with self.assertRaisesRegex(AssertionError,"regular"):read_archive(raw,pin(raw),1,set())
    def test_all_expected_native_exclusions(self):
        for ext in(".odb",".gds",".def",".lef",".spef",".spice",".l2n",".bin",".zip",".gz"):
            self.assertFalse(selected("nssoc/nssoc/obstacle-readback/native/x"+ext+".json"))
        self.assertFalse(selected("unowned/result.json"))
        self.assertFalse(selected(PREFIXES[1]+"work/frozen-input.json"))
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--controls",action="store_true");args=parser.parse_args()
    if args.controls:
        ctx=context();suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls);result=unittest.TextTestRunner(verbosity=2).run(suite)
        require(result.testsRun==8 and result.wasSuccessful()and not result.skipped,"all eight bounded archive controls")
        print(json.dumps(dict(status="PASS_EIGHT_ARTIFACT_READBACK_CONTROLS",**ctx,tests=8,skips=0,artifact_acquired=False,**FLAGS),sort_keys=True))
    else:main()
