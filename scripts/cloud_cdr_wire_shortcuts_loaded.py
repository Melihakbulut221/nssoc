#!/usr/bin/env python3
"""Provisional slave-drive trial with exact geometry binding and frozen electrical gates."""
import argparse,ast,copy,hashlib,json,os,platform,shutil,signal,subprocess,sys,tarfile,time,traceback,types
from pathlib import Path,PurePosixPath
import cdr_via2_m3_loaded_core as original
import cdr_sampler_bias_trial as trial
import cdr_slave_drive_binding as geometry_binding
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"cloud-wire-shortcuts-loaded"
NATIVE=OUT/"native";DERIVED=OUT/"derived";CONTROLS=ROOT/"wire-loaded-controls"
MANIFEST="scripts/cdr-wire-shortcuts-loaded-pins.json"
BASIS="scripts/cdr-wire-shortcuts-loaded-basis.json"
HOST="scripts/cloud_cdr_wire_shortcuts_loaded.py"
BRANCH="codex/cdr-slave-drive-trial"
REPO="Melihakbulut221/nssoc"
FLAGS=dict(trial.FLAGS)
STATE=None
TRIAL_BASIS=None
TRIAL_PROTECTED=None
def need(ok,msg):
    if not ok:raise AssertionError(msg)
def pin(p):return original.file_pin(p)
def encode(v):return(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def save(p,v):return original.write_exclusive(p,v)
def read(p):return json.loads(Path(p).read_bytes())
def api(path):return json.loads(subprocess.check_output(["gh","api","repos/"+REPO+"/"+path],timeout=180))
def context(e=None,native=False):
    e=os.environ if e is None else e
    need(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted","hosted execution only")
    need(e["GITHUB_REPOSITORY"]==REPO and e["GITHUB_REF"]=="refs/heads/"+BRANCH,"exact repository and branch")
    need(e["GITHUB_EVENT_NAME"]=="workflow_dispatch"and e["GITHUB_RUN_ATTEMPT"]=="1","first explicit dispatch")
    need(e["GITHUB_JOB"]in("source-controls","loaded-wave"),"current declared job")
    if native:need(e["GITHUB_JOB"]=="loaded-wave","native job required")
    return dict(source=e["GITHUB_SHA"],run_id=int(e["GITHUB_RUN_ID"]),attempt=1)
def gate():
    import numpy
    ctx=context()
    need(platform.python_version_tuple()[:2]==("3","12")and numpy.__version__=="2.3.3","frozen interpreter and numpy")
    need(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"exact source checkout")
    m=read(ROOT/MANIFEST)
    for name,expected in m["files"].items():need(pin(ROOT/name)==expected,"protected current source "+name)
    return ctx
def validate_assets(assets):
    need(set(assets)=={"native-fresh-rc.tar.gz","complete-output-index.json"},"exact RC asset names")
    for name,value in assets.items():
        need(set(value)=={"id","name","bytes","sha256"},"complete downloader asset schema")
        need(value["name"]==name and type(value["id"])is int and value["id"]>0 and type(value["bytes"])is int and value["bytes"]>0,"downloader asset identity")
        need(isinstance(value["sha256"],str)and len(value["sha256"])==64 and all(c in "0123456789abcdef"for c in value["sha256"]),"asset digest")
    return True
def basis():
    b=read(ROOT/BASIS)
    validate_assets(b["producer"]["assets"])
    need(b["schema"]=="nssoc.collector-via2.loaded-basis.v1"and b["source_preparation_only"]and not b["native_execution_authorized"]and not b["wave_execution_authorized"],"basis is input evidence not execution authority")
    need(b["producer"]["run"]==41439516945 and b["producer"]["source"]=="710869eb13082f3c3dc488159bf167d937294454"and b["producer"]["release"]==431398178,"actual new fresh RC producer")
    need(b["candidate"]==dict(bytes=1078900,sha256="c0d420cdbc31863bf21086e88c12f494779961225031c261d6b05fe07e7585a7"),"physically qualified actual layout")
    need(b["semantic_interface"]==["avdd","avss","sub","ird","cn","cp","dn","dp","irb","ira","irc","ibda","ibdc","ibs0","irx","xp","xn","ibs1","iry","yp","yn","irvx","irvy","vin","vip","wire_cref"],"actual new semantic order")
    need(b["loaded_numerical"]["source"]=="43fd3f71a289fef004aeb41cd2d0972d81f76f41","frozen loaded source")
    return b
def qualified_rc(q,oq,index,b):
    p=b["producer"];ctx=dict(source=p["source"],run_id=p["run"],attempt=1)
    need(index["context"]==dict(source=p["source"],run=p["run"],attempt=1)and index["files"]==p["complete_members"],"complete current RC index")
    need(q==b["qualification"],"exact current qualification")
    need(q["current_context"]==oq["context"]==ctx,"actual source/run qualification")
    need(q["status"]=="PASS_COLLECTOR_VIA2_FRESH_RC_NUMERICAL_QUALIFICATION_REQUIRES_LOADED_WAVES"and q["fresh_RC_executed"],"actual four-mixed-shortcut RC")
    need(oq["status"]=="PASS_CURRENT_VIA2_M3_FRESH_RC_NUMERICAL_QUALIFICATION_REQUIRES_LOADED_WAVES"and oq["fresh_RC_pipeline_complete"]and oq["execution_scope"]=="ACTUAL_AUTHORIZED_NATIVE_PHASE","complete original numerical qualification")
    need(q["counts"]==oq["counts"]==b["counts"]==dict(devices=500,R=26222,C=16798),"actual newly measured RC census")
    need(q["candidate"]==b["candidate"]and q["semantic_port_order"]+["wire_cref"]==b["semantic_interface"],"actual layout and interface")
    for record in(q,oq):
        need(all(record[k]is False for k in("electrical_accepted","full_phy_accepted","qualified_pex","loaded_simulation_passed")),"RC is not electrical acceptance")
    need(len(oq["phase_receipts"])==11,"all actual numerical receipts")
    for label,expected in oq["phase_receipts"].items():need(index["files"]["native-phase-reports/"+label+".json"]==expected,"actual phase receipt pin")
    for role in("model","composition"):
        path=b["inputs"][role]["path"]
        need(q[role]==index["files"][path]=={k:b["inputs"][role][k]for k in("bytes","sha256")},"actual current "+role)
    return ctx
def legacy():
    """Only named pure helpers; no historical acquisition, admission, simulation or candidate import."""
    scope=dict(ROOT=ROOT,OUT=OUT,NATIVE=NATIVE,DERIVED=DERIVED,REPO=REPO,core=original,api=api,
      require=need,save=save,hashlib=hashlib,json=json,os=os,signal=signal,subprocess=subprocess,
      tarfile=tarfile,time=time,traceback=traceback,Path=Path,PurePosixPath=PurePosixPath)
    names={"download_asset","restore","producer_gate","run_engine"}
    path=ROOT/"scripts/cloud_cdr_sampler_load.py";tree=ast.parse(path.read_bytes())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names]
    need({n.name for n in nodes}==names and all(not n.decorator_list for n in nodes),"exact isolated legacy helpers")
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),scope)
    return types.SimpleNamespace(**scope)
def current_configuration(root=ROOT):
    need(Path(root)==ROOT and STATE is not None,"explicit actual current loaded inputs")
    s=STATE
    for name,expected in s["protected"].items():need(pin(name)==expected,"unchanged actual configuration input "+name)
    return copy.deepcopy(s["configuration"]),copy.deepcopy(s["records"])
def numerical_namespace(root=ROOT,numpy=None):
    need(Path(root)==ROOT,"explicit current geometry binding root")
    return geometry_binding.numerical_namespace(original,Path(root),numpy)
def frozen():
    """Clone function globals explicitly; retain original numerical source and all acceptance limits."""
    ns=dict(original.__dict__)
    for name,fn in original.__dict__.items():
        if isinstance(fn,types.FunctionType)and fn.__globals__ is original.__dict__ and name not in("main","current_configuration"):
            ns[name]=types.FunctionType(fn.__code__,ns,fn.__name__,fn.__defaults__,fn.__closure__)
    ns.pop("main",None)
    ns.update(current_configuration=current_configuration,INPUTS=BASIS,numerical_namespace=numerical_namespace)
    need(ns["prepare_case"].__code__ is original.prepare_case.__code__ and ns["measure_case"].__code__ is original.measure_case.__code__,"unchanged complete preparation and measurement bodies")
    return types.SimpleNamespace(**ns)
def controls():
    gate();b=basis();CONTROLS.mkdir()
    c=original.catalog();need(len(c["files"])==9 and len(c["definitions"])==29,"all original loaded definitions")
    for record in c["definitions"].values():original.extract(record)
    for name in original.EXECUTABLE_BLOCKS:original.extract(c["blocks"][name],dedented=True)
    need(original.EXECUTABLE_BLOCKS=={"scenario","prerequisites","binding","deck","measurement"},"no historical executable acquisition")
    f=frozen();ns=f.numerical_namespace()
    need(not any(n in ns for n in("main","current_inputs","reports","fetch")),"isolated numerical methods")
    fixture=read(ROOT/"scripts/cdr-wire-shortcuts-loaded-qualification-fixture.json")
    q,oq,index=copy.deepcopy(fixture["q"]),copy.deepcopy(fixture["oq"]),dict(context=dict(source=b["producer"]["source"],run=b["producer"]["run"],attempt=1),files=b["producer"]["complete_members"])
    qualified_rc(q,oq,index,b)
    cases=[]
    for label in ("missing-asset-name","mismatched-asset-name"):
        altered=copy.deepcopy(b["producer"]["assets"])
        target=altered["native-fresh-rc.tar.gz"]
        if label=="missing-asset-name":target.pop("name")
        else:target["name"]="other.tar.gz"
        try:validate_assets(altered)
        except AssertionError:cases.append(label)
        else:raise AssertionError("accepted "+label)
    for label in("source","counts","scope","missing-phase","old-port-order","old-selector-port-order","electrical-claim","old-index"):
        x,y,z=copy.deepcopy(q),copy.deepcopy(oq),copy.deepcopy(index)
        if label=="source":y["context"]["source"]="0"*40
        elif label=="counts":y["counts"]["R"]+=1
        elif label=="scope":y["execution_scope"]="SOURCE_ONLY_SYNTHETIC_PHASE_FIXTURE"
        elif label=="missing-phase":y["phase_receipts"].pop("compose")
        elif label=="old-port-order":x["semantic_port_order"][19:21]=["yn","yp"]
        elif label=="old-selector-port-order":x["semantic_port_order"][15:17]=["xn","xp"]
        elif label=="electrical-claim":y["electrical_accepted"]=True
        elif label=="old-index":z["context"]["run"]=41251732540
        try:qualified_rc(x,y,z,b)
        except AssertionError:cases.append(label)
        else:raise AssertionError("accepted "+label)
    for key,value in[("GITHUB_REF","refs/heads/main"),("GITHUB_JOB","source-controls"),("GITHUB_RUN_ATTEMPT","2")]:
        env=dict(os.environ);env[key]=value
        try:context(env,native=True)
        except AssertionError:cases.append("reject "+key)
        else:raise AssertionError("accepted "+key)
    prefix=ast.parse(original.extract(c["blocks"]["deck"],dedented=True)[0]).body[:3]
    need(len(prefix)==3 and isinstance(prefix[0],ast.Assign)and prefix[0].targets[0].id=="nodes"and isinstance(prefix[1],ast.Expr)and isinstance(prefix[2],ast.Assign)and prefix[2].targets[0].id=="vectors","exact frozen vector prefix")
    need(STATE is None and not NATIVE.exists(),"no native input in source controls")
    trial_controls=trial.source_controls(ROOT)
    geometry_controls=geometry_binding.source_controls(ROOT)
    record=dict(trial_controls=trial_controls,geometry_controls=geometry_controls,status="PASS_PROVISIONAL_BIAS_TRIAL_FROZEN_LOADED_SOURCE_CONTROLS",definitions=29,executable_blocks=5,frozen_source_files=9,rejected=cases,
      frozen_complete_prepare_and_measure=True,original_13_binding_controls_required_in_actual_preparation=True,
      actual_port_order=b["semantic_interface"],native_acquired=False,transient_executed=False,**FLAGS)
    save(CONTROLS/"result.json",record)
    return record
def release_gate(empty=True,wait=False):
    ctx=context(native=True);tag="cloud-results-"+str(ctx["run_id"])+"-1-cdr-slave-drive-trial"
    for i in range(90 if wait else 1):
        p=subprocess.run(["gh","api","repos/"+REPO+"/releases/tags/"+tag],capture_output=True,text=True,timeout=180)
        if p.returncode==0:break
        need(wait and "HTTP 404"in p.stderr,"missing independent release")
        time.sleep(2)
    else:raise AssertionError("missing reserved current release")
    rel=json.loads(p.stdout)
    need(rel["target_commitish"]==ctx["source"]and rel["tag_name"]==tag and rel["prerelease"]and not rel["draft"],"exact current reserved release")
    need(api("git/ref/tags/"+tag)["object"]["sha"]==ctx["source"],"exact current reserved tag")
    if empty:need(not rel["assets"],"empty reserved release")
    return rel
def acquire_rc():
    b=basis();p=b["producer"];r=api("actions/runs/"+str(p["run"]));rel=api("releases/"+str(p["release"]));tag=api("git/ref/tags/"+p["tag"])
    need(r["status"]=="completed"and r["conclusion"]=="success"and r["head_sha"]==p["source"]and r["run_attempt"]==1,"actual successful new RC producer")
    need(rel["target_commitish"]==p["source"]and rel["tag_name"]==p["tag"]and tag["object"]["sha"]==p["source"],"RC release source")
    live={a["name"]:a for a in rel["assets"]};need(set(live)==set(p["assets"]),"complete RC release assets")
    for name,a in p["assets"].items():need(live[name]["id"]==a["id"]and live[name]["size"]==a["bytes"]and live[name]["digest"]=="sha256:"+a["sha256"],"RC release asset identity")
    save(DERIVED/"rc-producer.json",dict(run=r,release=rel,tag=tag))
    helpers=legacy()
    archive=NATIVE/"fresh-rc.tar.gz";helpers.download_asset(p["assets"]["native-fresh-rc.tar.gz"],archive)
    indexpath=NATIVE/"complete-output-index.json";helpers.download_asset(p["assets"]["complete-output-index.json"],indexpath)
    index=read(indexpath);need(index["files"]==p["complete_members"],"full producer output inventory")
    selected={v["path"]for v in b["inputs"].values()}|{"fresh-rc-qualification.json","fresh-rc-original-qualification.json","native-lifecycle.json"}
    selected|={n for n in index["files"]if n.startswith("native-phase-reports/")and n.endswith(".json")}
    destination=NATIVE/"rc"
    census=helpers.restore(archive,p["archive_root"],index["files"],selected,destination);save(DERIVED/"rc-census.json",census)
    q=read(destination/"fresh-rc-qualification.json");oq=read(destination/"fresh-rc-original-qualification.json")
    qualified_rc(q,oq,index,b)
    life=read(destination/"native-lifecycle.json")
    need(life["primary_error"]is None and life["heartbeat_stopped"]and len(life["commands"])==14,"actual complete RC lifecycle")
    need(all(c["returncode"]==0 and c["supervision_failure"]is None and not c["process_group_cleanup"]["remaining_live"]for c in life["commands"]),"all actual RC commands")
    for label,expected in oq["phase_receipts"].items():need(pin(destination/("native-phase-reports/"+label+".json"))==expected,"restored exact actual RC receipt")
    save(DERIVED/"rc-qualified.json",dict(qualification=q,original=oq,all_archive_members_authenticated=True))
    return {k:str(destination/v["path"])for k,v in b["inputs"].items()}
def acquire_runtime():
    cfg=read(ROOT/"scripts/cdr-via2-m3-loaded-runtime-inputs.json")
    need(cfg==basis()["runtime"],"frozen original runtime descriptor")
    for name,expected in cfg["records"].items():need(pin(ROOT/name)==expected,"all frozen runtime records")
    h=legacy();p=cfg["producer"];save(DERIVED/"runtime-producer.json",h.producer_gate(p))
    summary=read(ROOT/"docs/evidence/cdr-via2-m3-loaded-runtime-inputs/pump-summary.json")
    expected=dict(summary["outputs"]);expected["result.json"]=pin(ROOT/"docs/evidence/cdr-via2-m3-loaded-runtime-inputs/pump-summary.json")["sha256"]
    selected={n for n in expected if n.startswith("source/model-sources/")or n in("source-pin.json","source/runtime/patched-ngspice","result.json")}
    need(len(expected)==120 and len(selected)==40,"complete original runtime scope")
    a=next(a for a in p["assets"]if ".tar.gz.part"in a["name"]);archive=NATIVE/"runtime.tar.gz";h.download_asset(a,archive)
    dest=NATIVE/"runtime";save(DERIVED/"runtime-census.json",h.restore(archive,p["archive_root"],expected,selected,dest))
    engine=dest/"source/runtime/patched-ngspice";engine.chmod(0o755)
    return dict(lib=str(dest/"source/model-sources"),engine=str(engine),source_pin=str(dest/"source-pin.json"),models_summary=str(dest/"result.json"))
def configure(paths):
    global STATE
    need(STATE is None,"one actual configuration")
    need(TRIAL_BASIS is not None and TRIAL_PROTECTED is not None,"explicit provisional trial derivation")
    b=TRIAL_BASIS;contract=read(paths["composition"]);planes=read(paths["planes"]);ns=numerical_namespace()
    need(contract["counts"]==b["counts"]and contract["interface"]==b["semantic_interface"],"actual current numerical interface")
    need(len(contract["device_records"])==500 and sum(len(d["terminals"])for d in contract["device_records"])==1446,"all native devices and terminals")
    need(planes["status"]=="PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS"and len(planes["anchors"])==160 and len({p["logical_net"]for p in planes["anchors"]})==51,"complete current native plane binding")
    bound=ns["bind_native"](Path(paths["model"]).read_text(),contract,planes)
    save(DERIVED/"slave-geometry-binding-controls.json",geometry_binding.native_controls(ns,Path(paths["model"]).read_text(),contract,planes,ROOT))
    groups=bound["groups"]
    ns.update(bound=bound,ports=bound["ports"],devices=groups["npn13g2"],mos=groups["sg13_lv_nmos"],
      resistors=groups["rppd"],caps=groups["cap_cmim"],contacts=groups["ptap1"])
    record=original.catalog()["blocks"]["deck"];text,tree=original.extract(record,dedented=True);prefix=tree.body[:3]
    need(prefix[0].targets[0].id=="nodes"and prefix[2].targets[0].id=="vectors","frozen actual vector-selection prefix")
    exec(compile(ast.Module(body=prefix,type_ignores=[]),str(ROOT/record["file"])+":deck-vector-prefix","exec"),ns)
    vectors=ns["vectors"];need(len(vectors)==len(set(vectors)),"unique complete native selected vectors")
    projection=dict(source=b["producer"]["source"],run_id=b["producer"]["run"],current_loaded_context=context(),
      counts=dict(total=len(vectors),voltage_nodes=len(ns["nodes"]),hbt_currents=len(groups["npn13g2"]),mos_currents=len(groups["sg13_lv_nmos"])),
      vectors=vectors,aliases={name:dict(loaded_node=node)for name,node in bound["aliases"].items()},
      probe_witnesses=bound["probe_witnesses"],native_model_card_validation_executed=True,loaded_simulation_executed=False)
    projection_path=DERIVED/"actual-vector-projection.json";save(projection_path,projection)
    c=read(ROOT/"scripts/cdr-via2-m3-loaded-core-inputs.json")
    c.update(producer=dict(source=b["producer"]["source"],run=b["producer"]["run"],attempt=1,release=b["producer"]["release"]),
      model=b["inputs"]["model"],composition=b["inputs"]["composition"],planes=b["inputs"]["planes"],
      observed=dict(**b["counts"],terminals=1446,interface=b["semantic_interface"],selected_vectors=projection["counts"],
        selection_is_measured_not_general_invariant=True,native_card_validation_pending=False),
      records={},native_execution_authorized=False,wave_execution_authorized=False)
    c["scope"]=dict(scope=trial.SCOPE,closed_loop=False,external_clock=True,electrical_accepted=False,native_card_validation_executed=True,loaded_simulation_executed=False,**FLAGS)
    transport=c["transport_prerequisite"];t=original.pinned_json(ROOT/transport["path"],transport)
    records={"readback/actual/mim/composition/composition.json":contract,"readback/actual/binding/inputs/native-planes.json":planes,"derived-loaded-vector-projection.json":projection,"transport_prerequisite":t}
    protected={str(ROOT/BASIS):pin(ROOT/BASIS),str(projection_path):pin(projection_path),**{str(Path(p)):pin(p)for p in paths.values()}}
    protected.update(TRIAL_PROTECTED)
    STATE=dict(configuration=c,records=records,protected=protected)
    save(DERIVED/"actual-configuration.json",dict(configuration=c,protected=protected,actual_context=context()))
    return frozen()
def simulate():
    global TRIAL_BASIS,TRIAL_PROTECTED
    ctx=gate();context(native=True);control=controls()
    OUT.mkdir();NATIVE.mkdir();DERIVED.mkdir()
    save(DERIVED/"context.json",ctx);save(DERIVED/"same-source-controls.json",control)
    r=api("actions/runs/"+str(ctx["run_id"]));jobs=api("actions/runs/"+str(ctx["run_id"])+"/jobs?per_page=100")
    need(r["head_sha"]==ctx["source"]and r["run_attempt"]==1 and r["event"]=="workflow_dispatch","actual current run")
    checks=[j for j in jobs["jobs"]if j["name"]=="source-controls"]
    need(len(checks)==1 and checks[0]["conclusion"]=="success"and all(s["conclusion"]in("success","skipped")for s in checks[0]["steps"]),"own completed actual source controls")
    save(DERIVED/"admission.json",dict(run=r,jobs=jobs,release=release_gate(wait=True)))
    need(shutil.disk_usage(OUT).free>=8*1024**3,"original8GiB native workspace reserve")
    paths=acquire_rc();runtime=acquire_runtime()
    paths,TRIAL_BASIS,TRIAL_PROTECTED=trial.derive(sys.modules[__name__],paths)
    core=configure(paths)
    core.verify_current_inputs(paths);core.verify_runtime(runtime);gate()
    case=NATIVE/"nominal_late";prepared=core.prepare_case(case,paths,runtime,ctx)
    need(len(prepared["report"]["binding_controls"]["rejected"])==13 and prepared["report"]["binding_controls"]["equivalent_unit_spellings"]==2,"all actual binding controls")
    protected_before=pin(case/"prepared-state.json")
    need(protected_before==prepared["plan"]["prepared_state"],"exact current prepared state")
    gate();rc=legacy().run_engine(prepared["plan"])
    try:report=core.measure_case(case,ctx,rc,protected_before)
    finally:
        p=case/"measurement-result.json"
        if p.is_file():shutil.copyfile(p,DERIVED/"measurement-result.json")
        gate()
    save(DERIVED/"result.json",dict(status="PASS_PROVISIONAL_SLAVE_DRIVE_TRIAL_FROZEN_LOADED_MEASUREMENTS",
      context=ctx,model=pin(paths["model"]),measurement=report,loaded_simulation_passed=True,
      scope=trial.SCOPE,**FLAGS))
def publish():
    gate();ctx=context(native=True);rel=release_gate();need(OUT.is_dir(),"owned actual attempt")
    source=DERIVED/"source";source.mkdir(parents=True)
    names=set(read(ROOT/MANIFEST)["files"])|{MANIFEST}
    for name in sorted(names):
        p=source/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
    pub=OUT/"publication";pub.mkdir()
    rows={}
    for p in sorted(OUT.rglob("*")):
        need(not p.is_symlink(),"no aliased result payload")
        if p.is_file()and pub not in p.parents:rows[str(p.relative_to(OUT))]=pin(p)
    need(rows,"complete current result census")
    save(pub/"complete-output-index.json",dict(context=ctx,files=rows,**FLAGS))
    archive=pub/"native.tar.gz"
    with tarfile.open(archive,"w:gz",compresslevel=1)as tar:
        for name in rows:tar.add(OUT/name,arcname="wire-shortcuts-loaded/"+name,recursive=False)
    parts=[]
    with archive.open("rb")as stream:
        while True:
            b=stream.read(256*1024**2)
            if not b:break
            p=pub/("native.tar.gz.part"+format(len(parts),"04d"));p.write_bytes(b);parts.append(dict(name=p.name,index=len(parts),**pin(p)))
    save(pub/"parts.json",dict(context=ctx,archive_root="wire-shortcuts-loaded",archive=pin(archive),parts=parts))
    archive.unlink()
    for p in sorted(pub.iterdir()):
        subprocess.run(["gh","release","upload",rel["tag_name"],str(p),"--repo",REPO],check=True,timeout=900)
    final=release_gate(empty=False);expected={p.name:pin(p)for p in pub.iterdir()}
    need({a["name"]for a in final["assets"]}==set(expected),"all published native parts")
    for a in final["assets"]:need(a["size"]==expected[a["name"]]["bytes"]and a["digest"]=="sha256:"+expected[a["name"]]["sha256"],"exact published asset")
    save(DERIVED/"publication-result.json",dict(release=rel["id"],tag=rel["tag_name"],assets=expected,complete_native_preservation=True,**FLAGS))
def export(controls_only=False):
    dest=ROOT/("wire-loaded-controls-derived"if controls_only else"wire-loaded-derived");dest.mkdir();rows={}
    roots=[("controls",CONTROLS)]if controls_only else[("derived",DERIVED),("case",NATIVE/"nominal_late")]
    for label,root in roots:
        if root.exists():
            for p in sorted(root.rglob("*")):
                if p.is_file()and p.suffix in(".json",".jsonl",".log",".stdout",".stderr",".txt",".py",".yml")and p.stat().st_size<=32*1024**2:
                    name=label+"/"+str(p.relative_to(root));q=dest/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);rows[name]=pin(q)
    failure=OUT/"host-failure.json"
    if failure.is_file():shutil.copyfile(failure,dest/"host-failure.json");rows["host-failure.json"]=pin(dest/"host-failure.json")
    save(dest/"derived-index.json",rows)
def main():
    arg=sys.argv[1:]
    if arg==["--publish"]:publish();return
    if arg==["--derived"]:export();return
    if arg==["--derived-controls"]:export(True);return
    try:
        if arg==["--controls"]:controls()
        elif arg==["--simulate"]:simulate()
        else:raise AssertionError("explicit known entry only")
    except BaseException as exc:
        save(OUT/"host-failure.json",dict(error=repr(exc),traceback=traceback.format_exc(),loaded_simulation_passed=False,**FLAGS))
        raise
if __name__=="__main__":main()
