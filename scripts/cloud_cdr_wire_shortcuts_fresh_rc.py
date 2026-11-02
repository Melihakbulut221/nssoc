#!/usr/bin/env python3
"""Execute frozen full numerical RC methods on the new physically qualified four-mixed-shortcut view."""
import argparse,ast,contextlib,copy,hashlib,json,os,shutil,signal,subprocess,sys,tarfile,threading,traceback,types
from pathlib import Path,PurePosixPath
import cdr_via2_m3_fresh_rc_core as core
import cdr_v59_tail_access_runtime as supervisor_runtime
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"hw/soc/out/cloud-cdr-via2-m3-fresh-rc"
CURRENT=ROOT/"hw/soc/out/cloud-cdr-wire-shortcuts-canonical/view/candidate"
COUT=ROOT/"wire-rc-controls"
BRANCH="codex/cdr-collector-via2-fresh-rc"
MANIFEST="scripts/cdr-wire-shortcuts-fresh-rc-pins.json"
BASIS="scripts/cdr-wire-shortcuts-fresh-rc-basis.json"
PARENT="scripts/cdr-wire-physical-parent.json"
HOST="scripts/cloud_cdr_wire_shortcuts_fresh_rc.py"
NATIVE="scripts/cdr_via2_m3_fresh_rc_native.py"
RUNTIME="scripts/cdr_via2_m3_fresh_rc_runtime.py"
APP_SHA="d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"
FLAGS=dict(electrical_accepted=False,full_phy_accepted=False,qualified_pex=False,final_timing_complete=False,loaded_simulation_passed=False)
def need(ok,msg):
    if not ok:raise AssertionError(msg)
def sha(path):
    with Path(path).open("rb")as f:return hashlib.file_digest(f,"sha256").hexdigest()
def pin(p):
    p=Path(p);need(p.is_file()and not p.is_symlink(),"regular pinned file")
    return dict(bytes=p.stat().st_size,sha256=sha(p))
def encode(v):return(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def save(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("xb")as f:f.write(encode(value))
def context(e=None,native=False):
    e=os.environ if e is None else e
    need(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted","hosted only")
    need(e["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"and e["GITHUB_REF"]=="refs/heads/"+BRANCH,"current exact branch")
    need(e["GITHUB_EVENT_NAME"]=="workflow_dispatch"and e["GITHUB_RUN_ATTEMPT"]=="1","first explicit dispatch")
    need(e["GITHUB_JOB"]in("source-controls","native-rc"),"bounded current job")
    if native:need(e["GITHUB_JOB"]=="native-rc","current native job required")
    return dict(source=e["GITHUB_SHA"],run_id=int(e["GITHUB_RUN_ID"]),attempt=1)
def verify_source(path,expected):
    need("sha256"in expected and set(expected)<={"bytes","sha256","git_blob_sha1"},"declared source pin schema")
    actual=pin(path);need(actual["sha256"]==expected["sha256"],"protected source digest "+str(path))
    if "bytes"in expected:need(actual["bytes"]==expected["bytes"],"protected source size")
    if "git_blob_sha1"in expected:
        b=path.read_bytes();need(hashlib.sha1(("blob "+str(len(b))+"\0").encode()+b).hexdigest()==expected["git_blob_sha1"],"source git blob")
def gate():
    ctx=context();need(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"exact checkout")
    pins=json.loads((ROOT/MANIFEST).read_bytes())
    for n,p in pins["files"].items():
        verify_source(ROOT/n,p)
    return pins
def basis():
    b=json.loads((ROOT/BASIS).read_bytes())
    need(b["schema"]=="nssoc.collector-via2.fresh-rc-basis.v1"and b["source_preparation_only"]and not b["native_RC_execution_authorized"],"basis is evidence not authority")
    need(b["producer"]["run"]==41438707959 and b["producer"]["source"]=="6ecc4bac9ac806babd879413cd6d7230e70b826d"and b["producer"]["release"]==431392541,"actual canonical producer")
    need(b["candidate"]==dict(bytes=1078900,sha256="c0d420cdbc31863bf21086e88c12f494779961225031c261d6b05fe07e7585a7"),"actual new layout")
    cfg=json.loads((ROOT/core.CONFIG).read_bytes())["canonical_view"]
    need(cfg["current_files"]==b["current_view_files"]and cfg["port_order"]==b["actual_semantic_port_order"]and ROOT/cfg["root"]==CURRENT,"current numerical input binding")
    need(len(cfg["current_files"])==78 and len(cfg["port_order"])==25 and cfg["port_order"]==["avdd","avss","sub","ird","cn","cp","dn","dp","irb","ira","irc","ibda","ibdc","ibs0","irx","xp","xn","ibs1","iry","yp","yn","irvx","irvy","vin","vip"],"actual port order and view census")
    return b
def definitions(path,scope,exclude=(),assignments=False):
    """Only frozen pure functions/constants; never historical imports, main or native admission."""
    tree=ast.parse(path.read_bytes());nodes=[]
    for n in tree.body:
        if isinstance(n,ast.FunctionDef)and n.name not in exclude:
            need(not n.decorator_list,"undecorated frozen definition");nodes.append(n)
        elif assignments and isinstance(n,ast.Assign):
            names={t.id for t in n.targets if isinstance(t,ast.Name)}
            if names and not names&{"ROOT","require","encode"}:nodes.append(n)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),scope)
    return scope
def frozen():
    gate()
    q=types.SimpleNamespace(regular=core.regular,decode=core.binding_namespace.decode,
      fingerprint=lambda b:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
    rs=dict(__file__=str(ROOT/RUNTIME),ROOT=ROOT,a=types.SimpleNamespace(ROOT=ROOT),q=q,
      CONFIG="scripts/cdr-via2-m3-fresh-rc-runtime-inputs.json",Path=Path,json=json,hashlib=hashlib,shutil=shutil,
      require=need,encode=encode,pin=pin)
    wanted={"records","validate_precise_live","verify_manifest","copy_owned"}
    tree=ast.parse((ROOT/RUNTIME).read_bytes());allnames={n.name for n in tree.body if isinstance(n,ast.FunctionDef)}
    definitions(ROOT/RUNTIME,rs,allnames-wanted)
    rt=types.SimpleNamespace(**{n:rs[n]for n in wanted})
    ns=dict(__file__=str(ROOT/NATIVE),ROOT=ROOT,Path=Path,core=core,runtime=rt,
      a=types.SimpleNamespace(producer=types.SimpleNamespace(CURRENT_ROOT=str(CURRENT))),
      copy=copy,hashlib=hashlib,json=json,os=os,subprocess=subprocess,traceback=traceback,require=need,encode=encode)
    definitions(ROOT/NATIVE,ns,{"authorized","validate_complete","run_phase","main"},True)
    ns["SOURCE_PATHS"]=tuple(ns["SOURCE_PATHS"])+(HOST,RUNTIME,BASIS,core.CONFIG,MANIFEST)
    need("authorized"not in ns and "run_phase"not in ns and "main"not in ns,"no historical execution entry")
    return types.SimpleNamespace(**ns),rt
def command_plan(app,python):
    legacy=ROOT/NATIVE
    plan=core.command_plan(ROOT,OUT,app,python,legacy)
    need(plan["native_authority"]is False and len(plan["commands"])==13,"unchanged numerical argument contract")
    adapted=copy.deepcopy(plan);changes=[]
    for item in adapted["commands"]:
        argv=item["argv"]
        if str(legacy)in argv:
            need(argv.count(str(legacy))==1 and "--phase"in argv,"one declared phase entry")
            index=argv.index(str(legacy));argv[index]=str(ROOT/HOST);changes.append(dict(label=item["label"],argument=index))
    need(len(changes)==10,"ten phase entry substitutions; three extraction commands unchanged")
    reversed_plan=copy.deepcopy(adapted)
    for row in changes:next(x for x in reversed_plan["commands"]if x["label"]==row["label"])["argv"][row["argument"]]=str(legacy)
    need(reversed_plan==plan,"exact reversible command wrapper substitution")
    return dict(original=plan,adapted=adapted,changes=changes)
def controls():
    gate();b=basis();need(not OUT.exists(),"source controls precede native output")
    COUT.mkdir()
    testpin=COUT/"source-pin-fixture.txt";testpin.write_bytes(b"explicit synthetic pin fixture\n")
    expected=pin(testpin);checks=[]
    for label,value in[("historical hash-only",dict(sha256=expected["sha256"])),("complete size-hash",expected)]:
        verify_source(testpin,value);checks.append(label)
    for label,value in[("wrong digest",dict(sha256="0"*64)),("wrong size",dict(expected,bytes=1)),
      ("wrong git identity",dict(expected,git_blob_sha1="0"*40)),("missing digest",dict(bytes=expected["bytes"])),("unknown schema field",dict(expected,unknown=True))]:
        try:verify_source(testpin,value)
        except AssertionError:checks.append("reject "+label)
        else:raise AssertionError(label)
    import check_cdr_via2_m3_fresh_rc_core as k
    import check_cdr_via2_m3_fresh_rc_native as tests
    k.RECORDS.clear();k.definition_controls()
    copydir=COUT/"copy-command";copydir.mkdir();k.copy_and_command_controls(copydir)
    phase=tests.controls(context(),COUT/"phase-fixtures")
    need(phase["status"]=="PASS_SOURCE_ONLY_PHASE_CONTROLS"and phase["failed"]==0 and not phase["native_executed"],"all frozen numerical and lifecycle controls")
    n,rt=frozen();cfg,records=rt.records()
    plan=command_plan(Path("/fixture/runtime.AppImage"),Path("/usr/bin/python3"))
    tests_current=list(checks)
    need(set(n.PHASES)=={"prepare","binding-export","binding-validate","wire-audit","mim-generate","mim-finish","mim-audit","compose"}and len(n.LABELS)==11,"all original phase receipts")
    tests_current.append("all frozen phase methods with historical native entries excluded")
    tests_current.append("reversible exact13-command adaptation changes only ten entry paths")
    for key,value in[("GITHUB_JOB","source-controls"),("GITHUB_REF","refs/heads/main"),("GITHUB_RUN_ATTEMPT","2")]:
        env=dict(os.environ);env[key]=value
        try:context(env,native=True)
        except AssertionError:tests_current.append("reject native context "+key)
        else:raise AssertionError("accepted altered "+key)
    need(n.core is core and nsame(n.verify_runtime_cache,ROOT/NATIVE),"actual frozen function origin")
    tests_current.append("original runtime validator and all current source provenance bound")
    output=dict(status="PASS_COLLECTOR_VIA2_RC_SOURCE_CONTROLS",current=tests_current,core_control_count=len(k.RECORDS),
      core_controls=k.RECORDS,phase_controls=phase,command_adaptation=plan,actual_port_order=b["actual_semantic_port_order"],
      runtime_producer=cfg["precise"]["run_id"],native_executed=False,**FLAGS)
    (COUT/"result.json").write_bytes(encode(output))
    return output
def nsame(fn,path):return Path(fn.__code__.co_filename)==path
def api(path):return json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/"+path]))
def acquire_view():
    b=basis();p=b["producer"];run=api("actions/runs/"+str(p["run"]));rel=api("releases/"+str(p["release"]))
    need(run["head_sha"]==p["source"]and run["run_attempt"]==1 and run["status"]=="completed"and run["conclusion"]=="success","actual qualified canonical run")
    need(rel["target_commitish"]==p["source"]and rel["tag_name"]==p["tag"]and api("git/ref/tags/"+p["tag"])["object"]["sha"]==p["source"],"canonical release tag")
    assets={a["name"]:a for a in rel["assets"]};need(set(assets)==set(p["assets"]),"complete canonical asset set")
    cache=ROOT/"wire-rc-canonical-cache";cache.mkdir()
    for name,expected in p["assets"].items():
        actual=assets[name];need(actual["id"]==expected["id"]and actual["size"]==expected["bytes"]and actual["digest"]=="sha256:"+expected["sha256"],"canonical asset metadata")
        fetch_asset(expected,cache/name)
    index=json.loads((cache/"complete-output-index.json").read_bytes())
    need(index["context"]==dict(run=p["run"],attempt=1,source=p["source"])and index["files"]==p["complete_members"],"full independent canonical index")
    destination=CURRENT.parents[1];need(not destination.exists(),"fresh canonical restore namespace")
    names=set();seen={}
    with tarfile.open(cache/"native-canonical.tar.gz","r|gz")as tar:
        for m in tar:
            need(m.name not in names,"unique canonical member");names.add(m.name)
            q=PurePosixPath(m.name);need(not q.is_absolute()and ".."not in q.parts and str(q)==m.name and q.parts[0]==p["archive_root"],"canonical archive path")
            name=str(PurePosixPath(*q.parts[1:]));need(m.isfile()and name in p["complete_members"],"known regular canonical member")
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open("xb")as f:shutil.copyfileobj(tar.extractfile(m),f)
            seen[name]=pin(target);need(seen[name]==p["complete_members"][name],"canonical member digest")
    need(seen==p["complete_members"],"all133 actual canonical members")
    q=json.loads((destination/"view/canonical-view-qualification.json").read_bytes())
    need(q["status"]=="PASS_COLLECTOR_VIA2_NATIVE_CANONICAL_VIEW_REQUIRES_FRESH_RC"and q["current_files"]==b["current_view_files"]and q["native_identity"]==b["native_identity"],"actual canonical qualification")
    core.current_view_proof(ROOT,CURRENT)
    save("canonical-acquisition.json",dict(run=run,release=rel,authenticated_members=seen))
def restore_runtime(selected):
    n,rt=frozen();b=basis();expected=b["original_runtime"]["cache_members"]
    source=selected/"runtime-inputs";members={name.removeprefix("runtime-inputs/"):value for name,value in expected.items()}
    need(n.inventory(source)==members and len(members)==658,"complete authentic original runtime cache")
    rt.copy_owned(source,OUT/"runtime-inputs",members)
    cached=OUT/"runtime-inputs";cfg,records=rt.records()
    p=cfg["precise"];observed=[]
    for name,path in[("run","actions/runs/"+str(p["run_id"])),("jobs","actions/runs/"+str(p["run_id"])+"/attempts/1/jobs?per_page=100"),
      ("release","releases/"+str(p["release_id"])),("tag","git/ref/tags/"+p["tag"])]:
        value=api(path);observed.append(value);save("runtime-live-"+name+".json",value)
    original=rt.validate_precise_live(cfg,records,*observed)
    manifest=json.loads((cached/"frozen_layout/manifest.json").read_bytes())
    need(len(manifest["files"])==197,"all original frozen PDK runtime members")
    for name,expected in manifest["files"].items():
        source=cached/"frozen_layout"/name;target=ROOT/name
        need(pin(source)==expected,"original runtime member")
        if target.exists():need(pin(target)==expected,"no changed source overwrite")
        else:target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target,follow_symlinks=False)
    models=cached/"models/models"
    rt.copy_owned(models,ROOT/"pdk/libs.tech/ngspice/models",n.inventory(models))
    n.verify_runtime_cache(OUT);gate()
    save("runtime-restoration.json",dict(current_context=context(),original_acquisition_run=b["original_runtime"]["producer_run"],
      complete_cache_members=members,original_precise_binding=original,all_current_runtime_bytes_verified=True,
      cached_runtime_acquisition_is_not_current_RC_execution=True))
def phase(name,variant,out):
    context(native=True);gate();need(out.resolve()==OUT and out==OUT,"exact original numerical output namespace")
    n,rt=frozen();ctx=context();label=n.label(name,variant);pins=n.source_pins(ROOT);index=n.LABELS.index(label)
    def guard():
        context(native=True);gate();core.current_view_proof(ROOT,CURRENT)
        for previous in n.LABELS[:index]:n.verify_receipt(OUT,previous,ctx,pins,n.ACTUAL)
        n.verify_runtime_cache(OUT)
    return n.lifecycle(OUT,label,ctx,pins,n.ACTUAL,lambda:n.operate(name,variant,OUT,ctx),guard,guard)
def fetch_asset(asset,path):
    need(not path.exists(),"no overwrite download")
    with path.open("xb")as f:subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/releases/assets/"+str(asset["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True)
    need(pin(path)==dict(bytes=asset["bytes"],sha256=asset["sha256"]),"complete downloaded asset")
@contextlib.contextmanager
def tokenless():
    saved={k:os.environ.get(k)for k in("GH_TOKEN","GITHUB_TOKEN")}
    try:
        for k in saved:os.environ.pop(k,None)
        yield
    finally:
        for k,v in saved.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v


def verify():
    context(native=True);proof=controls();OUT.mkdir(parents=True)
    shutil.copytree(COUT,OUT/"source-control-fixtures")
    save("same-source-controls.json",proof)
    import cloud_cdr_wire_geometry_acquire as acquire
    acquire.OUT=OUT/"runtime-parent-acquisition"
    selected=acquire.acquire(json.loads((ROOT/PARENT).read_bytes()))
    acquire_view();restore_runtime(selected)
    app=Path(os.environ["RUNNER_TEMP"])/"current-tail-physical.AppImage";need(sha(app)==APP_SHA,"pinned AppImage")
    policy=json.loads((ROOT/"current-cdr-runtime-policy.json").read_bytes())
    need(policy["source"]==context()["source"]and policy["run_id"]==context()["run_id"]and policy["attempt"]==1,"current scoped runtime")
    need(policy["appimage"]==str(app)and policy["appimage_sha256"]==APP_SHA and policy["loaded"]and not policy["global_policy_changed"]and policy["restriction_before"]==policy["restriction_after"],"unchanged runtime policy")
    need(policy["profile"]=="/etc/apparmor.d/nssoc-cdr-runtime-"+os.environ["GITHUB_RUN_ID"]+"-1"and hashlib.sha256(policy["profile_text"].encode()).hexdigest()==policy["profile_sha256"],"run owned profile")
    save("runtime-policy.json",policy)
    launcher=supervisor_runtime.launcher(ROOT,gate,"501d4846603abd42b9efeaf515a5ad45f136d58997e37b16329003623b9f33ac")
    with tokenless():smoke=launcher.probe(app,APP_SHA,OUT/"runtime-smoke")
    need(smoke["accepted"]is True,"native runtime smoke")
    sup=supervisor_runtime.supervisor(ROOT,OUT,OUT/"supervision",gate,supervisor_runtime.SAMPLER_SHA);sup.TRACE.mkdir()
    beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start();previous={};commands=[]
    for sig in(signal.SIGINT,signal.SIGTERM):previous[sig]=signal.getsignal(sig);signal.signal(sig,sup.interrupted)
    def execute(argv,label):
        argv=list(map(str,argv));error=None
        scripts={v:pin(Path(v))for v in argv if v.endswith(".py")and Path(v).is_absolute()}
        try:
            with tokenless():sup.supervised(argv,label,seconds=1200,cwd=ROOT)
        except BaseException as exc:error=exc
        try:
            r=json.loads((sup.TRACE/(label+".command.json")).read_bytes());commands.append(r)
            need(r["argv"]==argv and r["minimum_available_kib"]==2097152 and r["maximum_group_rss_kib"]==10485760,"unchanged actual resource bounds")
            for stream in("stdout","stderr"):need(pin(sup.TRACE/(label+"."+stream))==dict(bytes=r[stream+"_bytes"],sha256=r[stream+"_sha256"]),"complete phase stream")
            events=[json.loads(line)for line in(sup.TRACE/"events.jsonl").read_bytes().splitlines()if line.strip()]
            starts=[e for e in events if e.get("event")=="command_start"and e.get("label")==label]
            need(len(starts)==1 and starts[0]["timeout_seconds"]==1200,"original phase duration bound")
            need(r["returncode"]==0 and r["supervision_failure"]is None and not r["process_group_cleanup"]["remaining_live"],"actual native phase completion")
            need(all(pin(Path(v))==p for v,p in scripts.items()),"executed numerical and wrapper scripts unchanged");gate()
        except BaseException as exc:error=error or exc
        if error is not None:raise error
    error=None;cleanup=[]
    try:
        execute([sys.executable,"-B",ROOT/HOST,"--phase","prepare","--out",OUT],"prepare")
        plan=command_plan(app,Path(sys.executable).resolve());save("native-command-plan.json",plan)
        for item in plan["adapted"]["commands"]:execute(item["argv"],item["label"])
        n,rt=frozen();q=n.validate_complete_files(OUT,context(),n.source_pins(ROOT),basis()["actual_semantic_port_order"],n.ACTUAL)
        need(q["status"]==n.STATUS and q["fresh_RC_pipeline_complete"]and not q["qualified_pex"],"original complete numerical qualification")
        save("fresh-rc-original-qualification.json",q)
        save("fresh-rc-qualification.json",dict(status="PASS_COLLECTOR_VIA2_FRESH_RC_NUMERICAL_QUALIFICATION_REQUIRES_LOADED_WAVES",
          current_context=context(),candidate=basis()["candidate"],canonical_run=41438707959,
          original_qualification=pin(OUT/"fresh-rc-original-qualification.json"),counts=q["counts"],
          semantic_port_order=basis()["actual_semantic_port_order"],model=pin(OUT/"mim/composition/pd500-mim-wire.spice"),
          composition=pin(OUT/"mim/composition/composition.json"),fresh_RC_executed=True,**FLAGS))
    except BaseException as exc:error=exc
    finally:
        try:cleanup.append(dict(process_group=sup.stop_process(sup.ACTIVE)))
        except BaseException as exc:cleanup.append(dict(error=repr(exc)));error=error or exc
        sup.STOP.set();beat.join(timeout=20)
        if beat.is_alive():error=error or RuntimeError("heartbeat did not stop")
        for sig,handler in previous.items():signal.signal(sig,handler)
        save("native-lifecycle.json",dict(primary_error=None if error is None else repr(error),cleanup=cleanup,commands=commands,heartbeat_stopped=not beat.is_alive(),**FLAGS))
    if error is not None:raise error
def publish():
    gate();e=os.environ;tag="cloud-results-"+e["GITHUB_RUN_ID"]+"-1-cdr-wire-shortcuts-fresh-rc"
    rel=api("releases/tags/"+tag)
    need(rel["target_commitish"]==e["GITHUB_SHA"]and not rel["assets"],"empty current-source reserved release")
    need(api("git/ref/tags/"+tag)["object"]["sha"]==e["GITHUB_SHA"],"reserved tag")
    files={str(p.relative_to(OUT)):p for p in sorted(OUT.rglob("*"))if p.is_file()}
    need(files and all(not p.is_symlink()for p in files.values()),"all regular result files")
    pub=ROOT/"wire-rc-publication";pub.mkdir()
    index=dict(context=dict(run=int(e["GITHUB_RUN_ID"]),attempt=1,source=e["GITHUB_SHA"]),files={n:pin(p)for n,p in files.items()})
    (pub/"complete-output-index.json").write_bytes(encode(index));archive=pub/"native-fresh-rc.tar.gz"
    with tarfile.open(archive,"w:gz")as tar:
        for n,p in files.items():tar.add(p,arcname="wire-shortcuts-fresh-rc/"+n,recursive=False)
    need(archive.stat().st_size<1500*1024*1024,"single native result asset below limit")
    subprocess.run(["gh","release","upload",tag,str(pub/"complete-output-index.json"),str(archive),"--repo","Melihakbulut221/nssoc"],check=True)
    assets=api("releases/"+str(rel["id"]))["assets"]
    for p in(pub/"complete-output-index.json",archive):
        a=next(a for a in assets if a["name"]==p.name);need(a["size"]==p.stat().st_size and a["digest"]=="sha256:"+sha(p),"exact uploaded result")
    save("publication.json",dict(tag=tag,release=rel["id"],assets=assets))

def derived(root,dest,extra=None):
    dest.mkdir();copied={}
    if root.exists():
        for p in sorted(root.rglob("*")):
            if p.is_file()and p.suffix in(".json",".jsonl",".log",".stdout",".stderr")and p.stat().st_size<=32*1024*1024:
                name=p.relative_to(root);q=dest/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);copied[str(name)]=pin(q)
    for name,p in (extra or {}).items():
        if p.is_file():
            q=dest/name;shutil.copyfile(p,q);copied[name]=pin(q)
    (dest/"derived-index.json").write_bytes(encode(copied))
def main():
    args=sys.argv[1:]
    if args==["--publish"]:publish();return
    if args==["--derived"]:derived(OUT,ROOT/"wire-rc-derived");return
    if args==["--derived-controls"]:derived(COUT,ROOT/"wire-rc-controls-derived",{"host-failure.json":OUT/"failure.json"});return
    try:
        if args==["--controls"]:controls()
        elif args==["--verify"]:verify()
        else:
            p=argparse.ArgumentParser();p.add_argument("--phase",required=True);p.add_argument("--variant");p.add_argument("--out",type=Path,required=True)
            a=p.parse_args();phase(a.phase,a.variant,a.out)
    except BaseException as exc:
        try:save("failure"+("-"+args[1]if args and args[0]=="--phase"else"")+".json",dict(error=repr(exc),traceback=traceback.format_exc(),**FLAGS))
        except BaseException as secondary:print("UNSAVED_FAILURE",repr(exc),repr(secondary),flush=True)
        raise
if __name__=="__main__":main()
