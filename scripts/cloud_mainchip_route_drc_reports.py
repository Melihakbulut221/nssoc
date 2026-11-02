"""Cloud-only authentication and classification of retained actual router DRC reports."""
import hashlib,json,os,re,shutil,subprocess,sys,tarfile,traceback
from collections import Counter
from pathlib import Path
from mainchip_snapshot_reload_contract import validate_archive_member
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"route-drc-diagnosis"
WORK=Path(os.environ.get("RUNNER_TEMP","/nonexistent"))/("nssoc-route-drc-"+os.environ.get("GITHUB_RUN_ID","missing"))
REPO="repos/Melihakbulut221/nssoc/"
PINS="scripts/mainchip-route-drc-report-pins.json"
CFG="scripts/mainchip-route-drc-report-inputs.json"
BRANCH="codex/mainchip-route-drc-diagnosis"
def need(v,msg):
    if not v:raise AssertionError(msg)
def fp(p):
    with p.open("rb")as f:h=hashlib.file_digest(f,"sha256").hexdigest()
    return dict(bytes=p.stat().st_size,sha256=h)
def api(path):return json.loads(subprocess.check_output(["gh","api",REPO+path],timeout=180))
def save(n,v):
    p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x")as f:json.dump(v,f,sort_keys=True,indent=2,allow_nan=False);f.write("\n")
def gate():
    e=os.environ
    need(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted","hosted only")
    need(e["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"and e["GITHUB_REF"]=="refs/heads/"+BRANCH,"exact repository branch")
    need(e["GITHUB_EVENT_NAME"]=="workflow_dispatch"and e["GITHUB_RUN_ATTEMPT"]=="1","explicit first attempt")
    need(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==e["GITHUB_SHA"],"actual checkout")
    for n,p in json.loads((ROOT/PINS).read_bytes())["files"].items():need(fp(ROOT/n)==p,"exact source "+n)
    return json.loads((ROOT/CFG).read_bytes())
def parse_report(text):
    rows=[];current=None
    for line in text.splitlines():
        line=line.strip()
        if not line:continue
        if line.startswith("violation type:"):
            need(current is None or set(current)=={"type","sources","bbox_line","layer"},"complete previous violation")
            current={"type":line.partition(":")[2].strip()};need(current["type"],"nonempty violation");rows.append(current)
        elif line.startswith("srcs:"):
            need(current is not None and "sources"not in current,"unique source record");current["sources"]=line.partition(":")[2].strip()
        elif line.startswith("bbox"):
            need(current is not None and "bbox_line"not in current,"unique geometry record")
            match=re.search(r"\bon Layer\s+(\S+)\s*$",line);need(match is not None,"actual layer in bounding record")
            current["bbox_line"]=line;current["layer"]=match[1]
        else:raise AssertionError("unrecognized original report line: "+line[:160])
    need(rows and all(set(r)=={"type","sources","bbox_line","layer"}for r in rows),"complete nonempty retained violations")
    return rows
def controls():
    valid="violation type: Metal Spacing\n srcs: net:a net:b\n bbox = ( 0, 0 ) - ( 1, 1 ) on Layer Metal2\n"
    rows=parse_report(valid);need(len(rows)==1 and rows[0]["layer"]=="Metal2","positive original format")
    bad=[valid.replace("srcs: net:a net:b\n",""),valid+"noise\n",valid.replace("on Layer Metal2",""),valid.replace("srcs:","srcs: x\n srcs:"),"",valid.replace("violation type: Metal Spacing","violation type:")]
    for s in bad:
        try:parse_report(s)
        except AssertionError:pass
        else:raise AssertionError("malformed report accepted")
    expected={"ok":dict(bytes=3,sha256="0"*64)}
    validate_archive_member("ok",True,3,expected,set())
    for name,regular,size,seen in [("/ok",True,3,set()),("../ok",True,3,set()),("x/../ok",True,3,set()),("ok",False,3,set()),("ok",True,2,set()),("missing",True,3,set()),("ok",True,3,{"ok"})]:
        try:validate_archive_member(name,regular,size,expected,seen)
        except (ValueError,AssertionError):pass
        else:raise AssertionError("unsafe archive member accepted")
    save("controls.json",dict(status="PASS_REPORT_PARSER_AND_ORIGINAL_ARCHIVE_REFUSALS",positive_cases=2,refusal_cases=13,physical_acceptance=False))
def diagnose():
    c=gate();p=c["producer"];r=api("actions/runs/"+str(p["run"]));rel=api("releases/"+str(p["release"]))
    need(r["status"]=="completed"and r["conclusion"]=="failure"and r["head_sha"]==p["source"]and r["run_attempt"]==1,"original failed route producer")
    need(rel["target_commitish"]==p["source"]and rel["tag_name"]==p["tag"]and api("git/ref/tags/"+p["tag"])["object"]["sha"]==p["source"],"original immutable route release")
    live={a["name"]:a for a in rel["assets"]};need(set(live)==set(c["assets"]),"all original release assets")
    need(not WORK.exists()and shutil.disk_usage(WORK.parent).free>=8*1024**3,"owned available transport")
    WORK.mkdir();save("producer.json",dict(run=r,release=rel))
    for name,pin in c["assets"].items():
        a=live[name];need(a["id"]==pin["id"]and a["size"]==pin["bytes"]and a["digest"]=="sha256:"+pin["sha256"],"exact asset")
        target=WORK/name;need(target.parent==WORK,"flat asset")
        with target.open("xb")as f:subprocess.run(["gh","api",REPO+"releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True,timeout=900)
        need(fp(target)=={k:pin[k]for k in ("bytes","sha256")},"download hash")
    index=json.loads((WORK/"candidate-outputs.json").read_bytes());parts=json.loads((WORK/"candidate-parts.json").read_bytes())
    need(index==c["index"]and parts==c["parts"],"complete original metadata")
    need(index["run"]==p["run"]and index["source"]==p["source"]and index["attempt"]==1,"complete index context")
    arc=WORK/"joined.tar.gz"
    with arc.open("xb")as f:
        for part in parts["parts"]:
            q=WORK/part["name"];need(fp(q)=={k:part[k]for k in ("bytes","sha256")},"ordered original part")
            with q.open("rb")as inp:shutil.copyfileobj(inp,f,4*1024**2)
            q.unlink()
    need(fp(arc)==parts["archive"],"complete reconstructed archive")
    expected=index["files"];need(len(expected)==738,"original complete inventory");seen=set();observed={};selected=set(c["selected"])
    need(selected<=set(expected),"known original reports")
    target=OUT/"original-reports";target.mkdir()
    with tarfile.open(arc,"r|gz")as tar:
        for member in tar:
            n=member.name;validate_archive_member(n,member.isfile(),member.size,expected,seen)
            inp=tar.extractfile(member);h=hashlib.sha256();size=0;out=(target/Path(n).name).open("xb")if n in selected else None
            try:
                for data in iter(lambda:inp.read(4*1024**2),b""):
                    size+=len(data);h.update(data)
                    if out is not None:out.write(data)
            finally:
                inp.close()
                if out is not None:out.close()
            observed[n]=dict(bytes=size,sha256=h.hexdigest());need(observed[n]==expected[n],"every original member hash")
    need(observed==expected,"full archive census")
    save("acquisition.json",dict(producer=p,authenticated_members=len(observed),archive=parts["archive"],
        selected={n:expected[n]for n in selected},native_archive_stays_cloud=True))
    summaries={}
    for n in sorted(selected):
        path=target/Path(n).name;need(fp(path)==expected[n],"retained report exact")
        rows=parse_report(path.read_text());iteration=int(re.search(r"-(\d+)\.rpt$",n)[1])
        summaries[str(iteration)]=dict(report=expected[n],violations=len(rows),
            by_type=dict(Counter(v["type"]for v in rows)),by_layer=dict(Counter(v["layer"]for v in rows)),
            by_type_layer=dict(Counter(v["type"]+" / "+v["layer"]for v in rows)),records=rows)
    need(set(summaries)=={"5","10","15","20","25"},"five original reported iterations")
    save("classified-original-reports.json",dict(iterations=summaries,matching_snapshot_pins=c["snapshot_pins"],physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
    gate()
    save("result.json",dict(status="COMPLETE_ACTUAL_RETAINED_ROUTER_REPORT_CLASSIFICATION",source=os.environ["GITHUB_SHA"],
        run=int(os.environ["GITHUB_RUN_ID"]),producer=p,counts={k:v["violations"]for k,v in summaries.items()},
        original_route_failure_preserved=True,new_route_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
    shutil.rmtree(WORK)
if __name__=="__main__":
    OUT.mkdir(exist_ok=False)
    try:gate();controls();diagnose()
    except BaseException as exc:
        save("failure.json",dict(error=repr(exc),traceback=traceback.format_exc(),physical_acceptance=False));raise
