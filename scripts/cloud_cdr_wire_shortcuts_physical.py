#!/usr/bin/env python3
"""Cloud-only full frozen DRC/LVS/fault verification of actual wire-shortcut GDS."""
import ast,contextlib,hashlib,importlib.util,json,os,shutil,signal,subprocess,sys,tarfile,threading,traceback,types
from pathlib import Path,PurePosixPath
import cloud_cdr_wire_geometry_acquire as acquire
import cloud_cdr_wire_shortcuts as geometry
import cdr_v59_tail_access_runtime as runtime
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"hw/soc/out/cloud-cdr-wire-shortcuts-physical"
MANIFEST="scripts/cdr-wire-shortcuts-physical-pins.json"
PARENT="scripts/cdr-wire-physical-parent.json"
CANDIDATE="scripts/cdr-wire-physical-candidate.json"
BRANCH="codex/cdr-clock-metal-physical"
APP_SHA="d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"
CHECKER_SHA="3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66"
TOP="nssoc_cdr_pd500_resistor_v59"
need=acquire.need;sha=acquire.sha if hasattr(acquire,"sha")else acquire.digest
def encode(v):return(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def pin(p):return dict(bytes=p.stat().st_size,sha256=sha(p))
def save(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("xb")as f:f.write(encode(value))
def gate():
    e=os.environ
    need(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted","hosted only")
    need(e["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"and e["GITHUB_REF"]=="refs/heads/"+BRANCH,"exact branch")
    need(e["GITHUB_EVENT_NAME"]=="workflow_dispatch"and e["GITHUB_RUN_ATTEMPT"]=="1","first dispatch")
    need(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==e["GITHUB_SHA"],"source checkout")
    pins=json.loads((ROOT/MANIFEST).read_bytes())
    for n,p in pins["files"].items():
        path=ROOT/n;need(path.is_file()and not path.is_symlink()and pin(path)=={k:p[k]for k in("bytes","sha256")},"protected source "+n)
        if "git_blob_sha1"in p:
            raw=path.read_bytes();need(hashlib.sha1(("blob "+str(len(raw))+"\0").encode()+raw).hexdigest()==p["git_blob_sha1"],"protected git blob "+n)
    acquire.OUT=OUT/"parent-acquisition"
    return pins
def pick_function(path,name,scope):
    t=ast.parse(path.read_bytes());nodes=[n for n in t.body if isinstance(n,ast.FunctionDef)and n.name==name]
    need(len(nodes)==1 and not nodes[0].decorator_list,"one frozen function")
    ns=dict(scope);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),ns);return ns[name]
def checker_text():
    original=(ROOT/"hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py").read_text()
    derive=pick_function(ROOT/"scripts/cloud_cdr500_input_access_v58_physical.py","derive",dict(ast=ast))
    physical=pick_function(ROOT/"scripts/cloud_cdr500_resistor_v59_physical.py","physical_source",dict(
      ARMS={"cd_shunt":dict(tags=["sc","sd"],names=["DN","DP"],new_length=5.,old_length=7.4)},TOP=TOP,derive=derive))
    text,changes=physical(original,"cd_shunt")
    need(len(changes)==4 and hashlib.sha256(text.encode()).hexdigest()==CHECKER_SHA,"unchanged full physical checker")
    return text,changes
def metadata(parent,gds,schematic,lef,inputs):
    need(isinstance(parent["ports"],dict)and len(parent["ports"])==25,"original public ports")
    need(pin(gds)==json.loads((ROOT/CANDIDATE).read_bytes())["candidate"],"exact actual new GDS")
    need(gds.name==TOP+".gds"and schematic.name=="schematic.cir","checker file names")
    return dict(status="GENERATED_PHYSICAL_WIRE_SHORTCUT_CANDIDATE_REQUIRES_FULL_VERIFICATION",
      source_head=os.environ["GITHUB_SHA"],generation_producer=json.loads((ROOT/CANDIDATE).read_bytes())["run"],top=TOP,
      ports=parent["ports"],inputs={str(p.resolve()):sha(p)for p in inputs},
      outputs={p.name:sha(p)for p in(gds,schematic,lef)},
      original_devices_and_reference_unchanged=True,physical_acceptance=False,
      serial_phy_complete=False,qualified_pex=False)
def policy_branch_controls():
    import re,textwrap
    lines=(ROOT/".github/workflows/cloud-evidence-summary.yml").read_text().splitlines()
    step=next(i for i,line in enumerate(lines)if line.strip()=="- name: Admit only the pinned runtime to hosted AppArmor user namespaces")
    start=next(i for i in range(step+1,len(lines))if lines[i].strip()=="python3 -B - <<'PY'")
    end=next(i for i in range(start+1,len(lines))if lines[i].strip()=="PY")
    block=textwrap.dedent("\n".join(lines[start+1:end]))
    asserts=[n for n in ast.parse(block).body if isinstance(n,ast.Assert)][:3]
    need(len(asserts)==3,"actual workflow context guards")
    exprs=[compile(ast.Expression(a.test),"<actual-policy-context>","eval")for a in asserts]
    good=dict(GITHUB_ACTIONS="true",GITHUB_REPOSITORY="Melihakbulut221/nssoc",GITHUB_REF="refs/heads/"+BRANCH,GITHUB_RUN_ATTEMPT="1",GITHUB_RUN_ID="1",GITHUB_SHA="a"*40)
    fixtures=[("current physical branch",{},True),
        ("old physical branch",dict(GITHUB_REF="refs/heads/codex/cdr-horizontal-ground-physical"),False),
        ("foreign repository",dict(GITHUB_REPOSITORY="other/repo"),False),
        ("rerun attempt",dict(GITHUB_RUN_ATTEMPT="2"),False),
        ("not hosted action",dict(GITHUB_ACTIONS="false"),False),
        ("invalid source",dict(GITHUB_SHA="wrong"),False),
        ("invalid run",dict(GITHUB_RUN_ID="0"),False)]
    passed=[]
    for name,delta,wanted in fixtures:
        observed=all(bool(eval(code,{"__builtins__":{},"re":re,"e":dict(good,**delta)}))for code in exprs)
        need(observed==wanted,"actual policy context regression "+name)
        passed.append("actual workflow policy "+name)
    return passed
def controls():
    gate();checks=geometry.controls();text,changes=checker_text()
    need(len(checks)==31,"all original generation controls")
    checks.append("frozen full560-category deep-flat500-device13-fault checker bytes")
    t=ast.parse(text);run=next(n for n in t.body if isinstance(n,ast.FunctionDef)and n.name=="run")
    literals={n.value for n in ast.walk(run)if isinstance(n,ast.Constant)and isinstance(n.value,str)}
    need({"drc","lvs","lvs_flat","v59_old_length","gain_gate_disconnected","gain_tail_width","missing_gain_hbt",
      "old_sampler_input_width","old_retime_width","wrong_follower_polarity","old_data_header_length",
      "wrong_finger_count","missing_hbt","q_open","rail_short","offgrid"}<=literals,"complete physical phase scope")
    checks.append("all16 original positive and fault phases retained")
    # Import the exact checker under its actual project paths before native acquisition.
    p=OUT/"methods/check_physical.py";p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    spec=importlib.util.spec_from_file_location("current_frozen_physical_checker",p)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    need(module.EXPECTED_CENSUS==dict(npn13g2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221),"native primitive census")
    checks.append("actual complete source import and500 primitive composition")
    need(len(module.PORTS)==25,"all25 original ports");checks.append("all25 original ports")
    # Construct existing frozen launcher/supervisor without starting a child.
    launcher=runtime.launcher(ROOT,gate,"501d4846603abd42b9efeaf515a5ad45f136d58997e37b16329003623b9f33ac")
    sup=runtime.supervisor(ROOT,OUT,OUT/"supervision",gate,runtime.SAMPLER_SHA)
    need(callable(launcher.probe)and sup.MIN_AVAILABLE_KIB==2097152 and sup.MAX_GROUP_RSS_KIB==10485760,"qualified runtime boundaries")
    checks.append("unchanged qualified launcher supervisor and resource limits")
    checks.extend(policy_branch_controls())
    save("controls.json",dict(count=len(checks),passed=checks,checker=dict(bytes=len(text.encode()),sha256=CHECKER_SHA),changes=changes))
    return p
def fetch_asset(asset,path):
    need(not path.exists(),"no overwrite download")
    with path.open("xb")as f:subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/releases/assets/"+str(asset["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True)
    need(pin(path)==dict(bytes=asset["bytes"],sha256=asset["sha256"]),"complete downloaded asset")

def validate_metal_candidate(target,cfg,proof):
    import klayout.db as db
    need(proof["status"]=="GENERATED_DIRECT_CLOCK_TOPMETAL1_REQUIRES_FULL_DRC_LVS_AND_FRESH_RC"and proof["candidate"]==cfg["candidate"],"actual direct metal candidate")
    need(proof["landings"]==8 and proof["networks"]==2 and proof["route_width_dbu"]==4000,"complete two clock networks")
    need(proof["new_vias"]==dict(Via3=48,Via4=48,TopVia1=32),"all actual new cuts")
    need(all(proof[k]is False for k in ("physical_acceptance","fresh_RC","electrical_improvement_proven","full_phy_accepted","final_timing_complete")),"unaccepted candidate")
    parent=target/"native/selected/binding/inputs/parent/layout"/(TOP+".gds")
    native=target/"native/selected/binding/inputs/wire/native05/wires.l2n"
    candidate=target/"native/candidate-clock-metal.gds"
    need(pin(parent)==proof["original_gds"]==dict(bytes=1079924,sha256="28eebb9f880648935a6368ada78a5e5666694ba98e073fbbac3f2e0c986339d6"),"actual latest baseline")
    need(pin(native)==proof["original_wire_l2n"]and pin(candidate)==cfg["candidate"],"independent input/output binding")
    old=db.Layout();old.read(str(parent));new=db.Layout();new.read(str(candidate))
    need(old.dbu==new.dbu==.001 and old.cell(TOP)is not None and new.cell(TOP)is not None,"actual top and DBU")
    snap=lambda ly:{(ly.get_info(i).layer,ly.get_info(i).datatype):db.Region(ly.cell(TOP).begin_shapes_rec(i)).merged()for i in ly.layer_indexes()}
    before=snap(old);after=snap(new)
    l2n=db.LayoutToNetlist();l2n.read(str(native))
    all_layers=(8,19,10,29,30,49,50,66,67,125,126,133,134)
    objects={n:l2n.layer_by_name("gds_"+str(n))for n in all_layers}
    for n,r in objects.items():need(r is not None and(r^before.get((n,0),db.Region())).is_empty(),"independent all13 conductor unions")
    nets={n.cluster_id:n for n in l2n.netlist().top_circuit().each_net()}
    anchors={a["label"]:a for a in json.loads((target/"native/selected/mim/precise/wire/anchors08.json").read_bytes())["anchors"]}
    need(len(anchors)==978,"all original anchors")
    groups=[["T054_E","T056_E","T061_C","T062_C"],["T106_E","T108_E","T115_C","T116_C"]]
    expected={}
    for labels in groups:
        components={anchors[n]["wire_component"]for n in labels};need(len(components)==1,"independent original same net")
        c=components.pop();need(c not in expected,"two distinct original nets");expected[c]=labels
    raw=json.loads((target/"derived/metal-additions.json").read_bytes())["by_component"]
    need(set(raw)=={str(c)for c in expected},"exact two declared original nets")
    def region(polys):
        r=db.Region()
        for item in polys:
            need(set(item)=={"hull","holes"}and len(item["hull"])>=4,"explicit polygon vertices")
            p=db.Polygon([db.Point(*q)for q in item["hull"]])
            for h in item["holes"]:p.insert_hole([db.Point(*q)for q in h])
            for points in [item["hull"],*item["holes"]]:
                need(all(len(q)==2 and all(type(v)is int and v%5==0 for v in q)for q in points),"actual5nm grid")
            r.insert(p)
        return r.merged()
    layers={30,49,50,66,67,125,126};adds={}
    for c,labels in expected.items():
        need(set(raw[str(c)])=={str(n)for n in layers},"exact seven additive layers")
        a={int(n):region(p)for n,p in raw[str(c)].items()};own={n:l2n.shapes_of_net(nets[c],objects[n],True).merged()for n in layers}
        need((a[30]-own[30]).is_empty(),"all M3 landing pads inside actual original same net")
        for n,r in a.items():
            need(not r.is_empty()and(r-db.Region(old.cell(TOP).bbox())).is_empty(),"nonempty within baseline extent")
            foreign=objects[n]-own[n]
            spacing=1650 if n==126 else 430 if n==125 else 300 if n in (49,66)else 610
            need((r&foreign.sized(spacing if n!=30 else 0,spacing if n!=30 else 0,2)).is_empty(),"independent no foreign conductor or insufficient clearance")
            if n in (49,66,125):need((r&objects[n].sized(spacing,spacing,2)).is_empty(),"new vs original via separation")
        for low,via,high,size,count,enc_lo,enc_hi in ((30,49,50,190,24,50,50),(50,66,67,190,24,50,50),(67,125,126,420,16,100,420)):
            need(a[via].count()==count and all(p.area()==size*size and p.bbox().width()==p.bbox().height()==size for p in a[via].each()),"exact cut count and dimensions")
            need(a[via].space_check(220 if via!=125 else 420).is_empty(),"all new cut spacing")
            need((a[via].sized(enc_lo,enc_lo,2)-a[low]).is_empty()and(a[via].sized(enc_hi,enc_hi,2)-a[high]).is_empty(),"both new via enclosures")
        need(a[126].count()==1 and a[126].width_check(1640).is_empty(),"one actual connected upper-metal network")
        for label in labels:
            point=anchors[label]["point_dbu"];x=5*round(point[0]/5)-100;y=5*round(point[1]/5)
            # Demand complete landing stack at each independently bound terminal,
            # not merely some nearby connected same-net shapes.
            for n,half_x,half_y in ((30,625,385),(50,625,385),(67,730,730),(126,1050,1050)):
                need((db.Region(db.Box(x-half_x,y-half_y,x+half_x,y+half_y))-a[n]).is_empty(),"every terminal has full landing metal")
            for n,offsets,half in ((49,[(-480,-240),(-480,240),(0,-240),(0,240),(480,-240),(480,240)],95),(66,[(-480,-240),(-480,240),(0,-240),(0,240),(480,-240),(480,240)],95),(125,[(-420,-420),(-420,420),(420,-420),(420,420)],210)):
                for dx,dy in offsets:need((db.Region(db.Box(x+dx-half,y+dy-half,x+dx+half,y+dy+half))-a[n]).is_empty(),"every terminal has every actual via")
        adds[c]=a
    c,d=sorted(adds)
    for n in layers:
        spacing=1650 if n==126 else 430 if n==125 else 300 if n in (49,66)else 610
        need((adds[c][n]&adds[d][n].sized(spacing,spacing,2)).is_empty(),"independent new-net separation on every layer")
    for key in set(before)|set(after):
        original=before.get(key,db.Region());wanted=original
        if key[1]==0 and key[0]in layers:wanted=(original+adds[c][key[0]]+adds[d][key[0]]).merged()
        need((wanted^after.get(key,db.Region())).is_empty(),"independent exact serialized additive delta")
        need((original-after.get(key,db.Region())).is_empty(),"no removal on any layer")
    return dict(eight_original_anchors_independently_bound=True,two_distinct_networks=True,all13_native_conductor_unions=True,all_other_layers_unchanged=True,all_new_cut_enclosures=True,physical_acceptance=False)

def candidate():
    import klayout.db as db
    cfg=json.loads((ROOT/CANDIDATE).read_bytes());api=acquire.api
    run=api("actions/runs/"+str(cfg["run"]))
    need(run["head_sha"]==cfg["source"]and run["run_attempt"]==1 and run["status"]=="completed"and run["conclusion"]=="success","actual candidate producer")
    rel=api("releases/"+str(cfg["release"]))
    need(rel["target_commitish"]==cfg["source"]and rel["tag_name"]==cfg["tag"]and api("git/ref/tags/"+cfg["tag"])["object"]["sha"]==cfg["source"],"candidate release/tag")
    assets={a["name"]:a for a in rel["assets"]};need(set(assets)==set(cfg["assets"]),"complete candidate assets")
    work=ROOT/"wire-physical-candidate-cache";work.mkdir()
    for n,p in cfg["assets"].items():
        need(PurePosixPath(n).name==n,"flat asset")
        a=assets[n];need(a["id"]==p["id"]and a["size"]==p["bytes"]and a["digest"]=="sha256:"+p["sha256"],"candidate asset metadata")
        fetch_asset(p,work/n)
    index=json.loads((work/"complete-output-index.json").read_bytes());need(index==cfg["index"],"independent complete index")
    target=work/"selected";seen={}
    with tarfile.open(work/"native-geometry.tar.gz","r|gz")as tar:
        for m in tar:
            n=acquire.relative(m.name,"domain-geometry")
            need(m.isfile()and n in index["files"]and n not in seen,"known unique regular candidate member")
            p=target/n;p.parent.mkdir(parents=True,exist_ok=True)
            with p.open("xb")as f:shutil.copyfileobj(tar.extractfile(m),f)
            seen[n]=pin(p);need(seen[n]==index["files"][n],"every candidate member digest")
    need(seen==index["files"],"complete native candidate preservation")
    proof=json.loads((target/"derived/result.json").read_bytes())
    verified=validate_metal_candidate(target,cfg,proof)
    save("candidate-acquisition.json",dict(run=run,release=rel,authenticated_members=seen,independent_geometry_delta=verified,device_geometry_unchanged=True))
    return target
def restore_runtime():
    cfg=json.loads((ROOT/"docs/evidence/pcie-tx-layout-cloud-input-20261013.json").read_bytes())["receipt"]
    packed=OUT/"frozen-runtime.tar.gz";fetch_asset(cfg,packed)
    with tarfile.open(packed)as tar:
        members=tar.getmembers();names=[m.name for m in members]
        need(len(names)==len(set(names)),"unique runtime members")
        manifest=json.loads(tar.extractfile("manifest.json").read())
        for m in members:
            n=PurePosixPath(m.name);need(not n.is_absolute()and ".."not in n.parts and str(n)==m.name.rstrip("/"),"runtime path")
            if m.isdir():continue
            need(m.isfile()and(m.name=="manifest.json"or m.name in manifest["files"]),"known regular runtime member")
            p=ROOT/m.name;data=tar.extractfile(m).read()
            if m.name!="manifest.json":need(hashlib.sha256(data).hexdigest()==manifest["files"][m.name]["sha256"],"runtime member hash")
            if p.exists():need(not p.is_symlink()and p.read_bytes()==data,"runtime cannot overwrite changed source")
            else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    for n,p in manifest["files"].items():need(sha(ROOT/n)==p["sha256"],"restored frozen runtime")
    save("runtime-source-manifest.json",manifest);gate()
def prepare_layout(parent_base,new_base,checker):
    layout=OUT/"layout";layout.mkdir()
    old=parent_base/"binding/inputs/parent/layout";cfg=json.loads((ROOT/PARENT).read_bytes())
    for n in("schematic.cir",TOP+".lef","result.json",TOP+".gds"):
        need(pin(old/n)==cfg["complete_members"]["binding/inputs/parent/layout/"+n],"original parent "+n)
    shutil.copyfile(new_base/"native/candidate-clock-metal.gds",layout/(TOP+".gds"))
    for n in("schematic.cir",TOP+".lef"):shutil.copyfile(old/n,layout/n);need(pin(old/n)==pin(layout/n),"unchanged original reference")
    p=json.loads((old/"result.json").read_bytes())
    inputs=[old/n for n in("result.json","schematic.cir",TOP+".lef",TOP+".gds")]
    inputs.extend([new_base/"derived/result.json",new_base/"native/candidate-clock-metal.gds",ROOT/CANDIDATE,ROOT/PARENT,checker,ROOT/"scripts/cloud_cdr_wire_shortcuts_physical.py"])
    record=metadata(p,layout/(TOP+".gds"),layout/"schematic.cir",layout/(TOP+".lef"),inputs)
    (layout/"result.json").write_bytes(encode(record));save("candidate-layout-binding.json",record)
    return layout
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
    checker=controls();cfg=json.loads((ROOT/PARENT).read_bytes())
    base=acquire.acquire(cfg);new=candidate();layout=prepare_layout(base,new,checker)
    restore_runtime()
    app=Path(os.environ["RUNNER_TEMP"])/"current-tail-physical.AppImage"
    need(pin(app)["sha256"]==APP_SHA,"original pinned AppImage")
    policy=json.loads((ROOT/"current-cdr-runtime-policy.json").read_bytes())
    need(policy["source"]==os.environ["GITHUB_SHA"]and policy["run_id"]==int(os.environ["GITHUB_RUN_ID"])and policy["loaded"]and not policy["global_policy_changed"],"current scoped runtime policy")
    need(policy["attempt"]==1 and policy["appimage"]==str(app)and policy["appimage_sha256"]==APP_SHA,"exact runtime identity")
    need(policy["restriction_before"]==policy["restriction_after"],"unchanged namespace restriction")
    need(policy["profile"]=="/etc/apparmor.d/nssoc-cdr-runtime-"+os.environ["GITHUB_RUN_ID"]+"-1"and hashlib.sha256(policy["profile_text"].encode()).hexdigest()==policy["profile_sha256"],"run owned scoped runtime profile")
    save("runtime-policy.json",policy)
    launcher=runtime.launcher(ROOT,gate,"501d4846603abd42b9efeaf515a5ad45f136d58997e37b16329003623b9f33ac")
    with tokenless():smoke=launcher.probe(app,APP_SHA,OUT/"runtime-smoke")
    need(smoke["accepted"]is True,"native runtime smoke")
    sup=runtime.supervisor(ROOT,OUT,OUT/"supervision",gate,runtime.SAMPLER_SHA);sup.TRACE.mkdir()
    beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start();previous={}
    for sig in(signal.SIGINT,signal.SIGTERM):previous[sig]=signal.getsignal(sig);signal.signal(sig,sup.interrupted)
    error=None;cleanup=[]
    try:
        with tokenless():sup.supervised([sys.executable,str(checker),"--layout",str(layout),"--out",str(OUT/"physical"),"--app",str(app)],"full560-DRC-deep-flat-LVS13",seconds=7200,cwd=ROOT)
        command=json.loads((sup.TRACE/"full560-DRC-deep-flat-LVS13.command.json").read_bytes())
        need(command["argv"]==[sys.executable,str(checker),"--layout",str(layout),"--out",str(OUT/"physical"),"--app",str(app)],"exact executed command")
        need(command["minimum_available_kib"]==2097152 and command["maximum_group_rss_kib"]==10485760,"unchanged actual resource bounds")
        need(command["returncode"]==0 and command["supervision_failure"]is None and not command["process_group_cleanup"]["remaining_live"],"actual completion and child cleanup")
        for stream in("stdout","stderr"):
            need(pin(sup.TRACE/("full560-DRC-deep-flat-LVS13."+stream))==dict(bytes=command[stream+"_bytes"],sha256=command[stream+"_sha256"]),"whole native command stream")
        events=[json.loads(b)for b in(sup.TRACE/"events.jsonl").read_bytes().splitlines()if b.strip()]
        starts=[e for e in events if e.get("event")=="command_start"and e.get("label")=="full560-DRC-deep-flat-LVS13"]
        need(len(starts)==1 and starts[0]["timeout_seconds"]==7200,"exact native timeout")
        record=json.loads((OUT/"physical/result.json").read_bytes())
        need(record["status"]=="PASS_NATIVE_PDK_CDR_PD500_DRC_LVS_AND_FAULT_CONTROLS","complete original physical checker pass")
        need(len(record["steps"])==16,"all16 original phases")
        for n,s in record["steps"].items():
            need(s["status"]==("PASS"if n in("drc","lvs","lvs_flat")else"REJECTED_EXPECTED_FAULT"),"original phase outcome")
        need(record["steps"]["drc"]["measurement"]["category_count"]==560,"all560 DRC categories")
        for n in("lvs","lvs_flat"):
            need(record["steps"][n]["native_primitive_census"]==dict(npn13g2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221),"500 transistor-level primitives")
        for p,h in record["inputs"].items():need(sha(Path(p))==h,"actual final physical input "+p)
        need(record["inputs"][str(layout/(TOP+".gds"))]==json.loads((ROOT/CANDIDATE).read_bytes())["candidate"]["sha256"],"actual new candidate verified")
        gate()
        save("physical-qualification.json",dict(status="PASS_DIRECT_CLOCK_METAL_GDS_FULL560_DRC_DEEP_FLAT_LVS13",gds=pin(layout/(TOP+".gds")),record=pin(OUT/"physical/result.json"),new_RC_executed=False,electrical_accepted=False,full_phy_accepted=False,final_timing_complete=False))
    except BaseException as exc:error=exc
    finally:
        try:cleanup.append(dict(process_group=sup.stop_process(sup.ACTIVE)))
        except BaseException as exc:cleanup.append(dict(error=repr(exc)));error=error or exc
        sup.STOP.set();beat.join(timeout=20)
        if beat.is_alive():error=error or RuntimeError("heartbeat did not stop")
        for sig,handler in previous.items():signal.signal(sig,handler)
        save("native-lifecycle.json",dict(primary_error=None if error is None else repr(error),cleanup=cleanup,heartbeat_stopped=not beat.is_alive()))
    if error is not None:raise error
def publish():
    gate();e=os.environ;tag="cloud-results-"+e["GITHUB_RUN_ID"]+"-1-cdr-wire-shortcuts-physical"
    rel=acquire.api("releases/tags/"+tag)
    need(rel["target_commitish"]==e["GITHUB_SHA"]and not rel["assets"],"empty current-source reserved release")
    need(acquire.api("git/ref/tags/"+tag)["object"]["sha"]==e["GITHUB_SHA"],"reserved tag")
    files={str(p.relative_to(OUT)):p for p in sorted(OUT.rglob("*"))if p.is_file()}
    need(files and all(not p.is_symlink()for p in files.values()),"all regular result files")
    pub=ROOT/"wire-physical-publication";pub.mkdir()
    index=dict(context=dict(run=int(e["GITHUB_RUN_ID"]),attempt=1,source=e["GITHUB_SHA"]),files={n:pin(p)for n,p in files.items()})
    (pub/"complete-output-index.json").write_bytes(encode(index));archive=pub/"native-physical.tar.gz"
    with tarfile.open(archive,"w:gz")as tar:
        for n,p in files.items():tar.add(p,arcname="wire-shortcuts-physical/"+n,recursive=False)
    need(archive.stat().st_size<1500*1024*1024,"single native result asset below limit")
    subprocess.run(["gh","release","upload",tag,str(pub/"complete-output-index.json"),str(archive),"--repo","Melihakbulut221/nssoc"],check=True)
    assets=acquire.api("releases/"+str(rel["id"]))["assets"]
    for p in(pub/"complete-output-index.json",archive):
        a=next(a for a in assets if a["name"]==p.name);need(a["size"]==p.stat().st_size and a["digest"]=="sha256:"+sha(p),"exact uploaded result")
    save("publication.json",dict(tag=tag,release=rel["id"],assets=assets))
def derived():
    dest=ROOT/"wire-physical-derived";dest.mkdir()
    copied={}
    for p in sorted(OUT.rglob("*")):
        if p.is_file()and p.suffix in(".json",".jsonl",".log",".stdout",".stderr")and p.stat().st_size<=32*1024*1024:
            n=p.relative_to(OUT);q=dest/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);copied[str(n)]=pin(q)
    (dest/"derived-index.json").write_bytes(encode(copied))
def main():
    mode=sys.argv[1:]
    if mode==["--publish"]:publish();return
    if mode==["--derived"]:derived();return
    try:
        need(mode in(["--controls"],["--verify"]),"explicit mode")
        if mode==["--controls"]:controls()
        else:verify()
    except Exception as exc:save("failure.json",dict(error=repr(exc),traceback=traceback.format_exc(),full_phy_accepted=False));raise
if __name__=="__main__":main()
