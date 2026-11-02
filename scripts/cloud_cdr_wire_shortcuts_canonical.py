#!/usr/bin/env python3
"""Cloud-only fresh native canonical wire view for the physically verified current horizontal-ground GDS."""
import argparse,contextlib,hashlib,json,os,shutil,signal,subprocess,sys,tarfile,threading,traceback
from pathlib import Path,PurePosixPath
import cdr_via2_m3_canonical_core as core
import cdr_v59_tail_access_runtime as runtime
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"hw/soc/out/cloud-cdr-wire-shortcuts-canonical"
BRANCH="codex/cdr-local-source-m1-canonical"
MANIFEST="scripts/cdr-wire-shortcuts-canonical-pins.json"
CONFIG="scripts/cdr-wire-shortcuts-canonical-inputs.json"
PARENT="scripts/cdr-wire-physical-parent.json"
APP_SHA="d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"
TOP="nssoc_cdr_pd500_resistor_v59"
LABELS=("avss",)
FLAGS=dict(fresh_RC_executed=False,electrical_accepted=False,full_phy_accepted=False,qualified_pex=False,final_timing_complete=False)
def need(ok,msg):
    if not ok:raise AssertionError(msg)
def sha(p):
    with p.open("rb")as f:return hashlib.file_digest(f,"sha256").hexdigest()
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
            b=path.read_bytes();need(hashlib.sha1(("blob "+str(len(b))+"\0").encode()+b).hexdigest()==p["git_blob_sha1"],"source git blob")
    return pins
def config():
    c=json.loads((ROOT/CONFIG).read_bytes())
    need(c["schema"]=="nssoc.local-source-m1.canonical.v1","actual local source canonical schema")
    need(c["candidate"]["gds"]==dict(bytes=1003860,sha256="4ccf1212d4b98046b1b56037bb1b76c53477777b08ee9cba5053c8e6323203e8"),"actual eight-source candidate")
    need(c["reference_prefix"]=="binding/inputs/"and c["original_reference_gds"]==dict(bytes=1003348,sha256="b9b92319590ecca1c9ce31dcf1cc31f4fdc1d468fc514585931671ed2f4fa492"),"actual current horizontal-ground reference")
    p=c["physical"];need(p["run"]==41401709497 and p["source"]=="a60c812f23d80ce7672a807f6392fa35cc440a32"and p["release"]==431142636,"actual passed physical producer")
    g=c["generation"];q=g["proof"];rows=g["targets"]
    need(g["run"]==41400908740 and g["source"]=="880dce57683ccb79f38ea43f3014bb90151329e1","actual generated source")
    need(q["candidate"]==c["candidate"]["gds"]and q["input_gds"]==c["original_reference_gds"]and q["exact_serialized_delta"]and q["original_material_roundtrip"],"actual serialized exact delta")
    need(q["source_count"]==8 and q["only_added_layer"]==[8,0]and q["total_added_area_dbu2"]==48000000,"exact source count layer and area")
    need(not q["new_devices"]and not q["new_vias"]and not q["physical_acceptance"],"original generation boundary")
    labels={"T"+str(n).zfill(3)+"_S"for n in(3,4,5,6,32,33,34,35)}
    need(len(rows)==8 and {r["label"]for r in rows}==labels and all(r["selected"]is not None for r in rows),"all eight source declarations")
    need(g["component"]==14 and g["native_cluster"]==24,"actual prior avss identity")
    return c
def ground_variant(pya,original,row):
    def bounds(region):
        b=region.bbox();return [b.left,b.bottom,b.right,b.top]
    need(bounds(original)==row["original_bbox"]and original.area()==row["old_area_dbu2"],"actual original polygon not bbox approximation")
    need(original.bbox().height()==3200,"original branch width")
    selected=[v for v in row["variants"]if v["strategy"]==row["selected_strategy"]]
    need(row["admitted"]and len(selected)==1 and selected[0]["admitted"]and all(selected[0]["guards"].values()),"one actual admitted ground variant")
    variant=selected[0];offset={"centered":0,"upper_only":700,"lower_only":-700}
    need(variant["strategy"]in offset,"declared exact addition position")
    result=original.sized(0,700,2).merged().moved(0,offset[variant["strategy"]]).merged()
    need((original-result).is_empty()and result.bbox().height()==4600,"preserve complete original polygon")
    need(bounds(result)==variant["widened_bbox"]and result.area()==variant["new_area_dbu2"],"actual serialized variant declaration")
    need(result.bbox().left==original.bbox().left and result.bbox().right==original.bbox().right,"unchanged longitudinal ends")
    return result
def source_m1_variant(pya,original,row):
    a=row["original_anchor"];selected=row["selected"]
    need(a["metal"]==8 and a["wire_component"]==14 and a["native_cluster"]==24 and a["detail"]["native_net"]=="avss","actual source M1 owner")
    need(selected is not None and selected in row["trials"]and selected["admitted"]and all(selected["guards"].values()),"actual selected guarded trial")
    need(selected["width_added_nm"]==1500 and selected["halfspan_nm"]==2000,"actual four-micron source rectangle")
    x,y=a["point_dbu"];need(x%5==0 and y%5==0,"source grid")
    source_box=[x-145,y-2000,x+145,y+2000]
    original_strip=pya.Region(pya.Box(*source_box))
    need(selected["original_strip_bbox"]==source_box and(original_strip-original).is_empty(),"exact source rectangle on original metal")
    added_box=[x-1645,y-2000,x-145,y+2000]
    addition=pya.Region(pya.Box(*added_box))
    need(selected["addition_bbox"]==added_box and selected["addition_area_dbu2"]==addition.area()==6000000,"independently reconstructed added rectangle")
    need((addition&original).is_empty(),"entire declared rectangle is new material")
    return addition
def declared_layers(pya,original,rows):
    need(len(rows)==8 and len({r["label"]for r in rows})==8,"all eight unique source targets")
    result=pya.Region()
    for row in rows:result+=source_m1_variant(pya,original,row)
    result=result.merged()
    need(result.count()==8 and result.area()==48000000,"eight disjoint exact new source rectangles")
    return {8:result}
def material_union(pya,before,after,declared):
    need(((before+declared).merged()^after.merged()).is_empty(),"exact owner and layer material union")
def source_m1_delta_controls(pya):
    import copy
    original=pya.Region(pya.Box(9855,18000,10145,22000))
    trial=dict(width_added_nm=1500,halfspan_nm=2000,original_strip_bbox=[9855,18000,10145,22000],addition_bbox=[8355,18000,9855,22000],addition_area_dbu2=6000000,admitted=True,guards=dict(exact=True))
    row=dict(label="T003_S",original_anchor=dict(metal=8,wire_component=14,native_cluster=24,detail=dict(native_net="avss"),point_dbu=[10000,20000]),selected=trial,trials=[trial])
    got=source_m1_variant(pya,original,row)
    need((got^pya.Region(pya.Box(8355,18000,9855,22000))).is_empty(),"independent exact source rectangle")
    passed=["independent local-source M1 rectangle reconstruction"]
    for label in("old-box","new-box","new-area","width","span","failed-guard","unadmitted","owner","missing-original"):
        bad=copy.deepcopy(row);sel=bad["selected"];ref=original
        if label=="old-box":sel["original_strip_bbox"][0]+=5
        elif label=="new-box":sel["addition_bbox"][0]+=5
        elif label=="new-area":sel["addition_area_dbu2"]+=1
        elif label=="width":sel["width_added_nm"]+=10
        elif label=="span":sel["halfspan_nm"]+=5
        elif label=="failed-guard":sel["guards"]["exact"]=False
        elif label=="unadmitted":sel["admitted"]=False
        elif label=="owner":bad["original_anchor"]["wire_component"]=13
        elif label=="missing-original":ref=pya.Region()
        try:source_m1_variant(pya,ref,bad)
        except AssertionError:passed.append("reject local-source "+label)
        else:raise AssertionError(label)
    return passed
def controls():
    gate();c=config()
    import cloud_cdr_wire_shortcuts as geometry
    checks=geometry.controls();need(len(checks)==31,"all original generation guards")
    pya=geometry.pya
    left=pya.Region(pya.Box(0,0,100,100));add=pya.Region(pya.Box(100,0,200,100));right=(left+add).merged()
    material_union(pya,left,right,add);checks.append("exact new conductor union")
    for label,old,new,decl in [
      ("deleted original",left,add,add),("undeclared material",left,right,pya.Region()),
      ("wrong owner",left,left,add),("missing original layer",left,pya.Region(),pya.Region())]:
        try:material_union(pya,old,new,decl)
        except AssertionError:checks.append("reject "+label)
        else:raise AssertionError(label)
    import copy
    original=pya.Region(pya.Box(-100000,-1600,100000,1600))
    fixtures=[]
    for name,bbox in [("centered",[-100000,-2300,100000,2300]),("upper_only",[-100000,-1600,100000,3000]),("lower_only",[-100000,-3000,100000,1600])]:
        row=dict(original_bbox=[-100000,-1600,100000,1600],old_area_dbu2=640000000,admitted=True,selected_strategy=name,
            variants=[dict(strategy=name,admitted=True,guards=dict(synthetic=True),widened_bbox=bbox,new_area_dbu2=920000000)])
        need(ground_variant(pya,original,row).area()==920000000,"independent added-area rectangle")
        fixtures.append(row);checks.append("independent "+name+"4600nm geometry")
    for label in ("old-box","old-area","new-box","new-area","failed-guard","unadmitted","unknown-strategy"):
        bad=copy.deepcopy(fixtures[0]);v=bad["variants"][0]
        if label=="old-box":bad["original_bbox"][0]+=5
        elif label=="old-area":bad["old_area_dbu2"]+=1
        elif label=="new-box":v["widened_bbox"][1]+=5
        elif label=="new-area":v["new_area_dbu2"]+=1
        elif label=="failed-guard":v["guards"]["synthetic"]=False
        elif label=="unadmitted":bad["admitted"]=False
        elif label=="unknown-strategy":v["strategy"]=bad["selected_strategy"]="other"
        try:ground_variant(pya,original,bad)
        except AssertionError:checks.append("reject "+label)
        else:raise AssertionError(label)
    text,records=core.derived_sources(ROOT,c)
    need(set(text)=={"check_width_parent_geometry.py","width_planes.py","width_source_pins.py"},"all original derived methods")
    for name,value in text.items():need(core.projection.fingerprint(value.encode())==records[name]["generated_pin"],"derived source receipt")
    checks.append("unchanged frozen planes recovery and parent geometry definitions")
    need(len(c["wire_workers"])==4 and set(c["wire_workers"])=={core.projection.WIRE_SOURCE+n for n in core.projection.WORKERS},"four original native workers")
    core.projection.wire_coverage(ROOT,c["wire_workers"]);checks.append("complete frozen worker dependency coverage")
    need(len(checks)==48,"all48 independent canonical controls")
    checks.extend(source_m1_delta_controls(pya))
    save("controls.json",dict(count=len(checks),passed=checks,**FLAGS))
def acquire_physical():
    import cloud_cdr_wire_geometry_acquire as a
    c=config()["physical"];run=a.api("actions/runs/"+str(c["run"]));rel=a.api("releases/"+str(c["release"]))
    need(run["head_sha"]==c["source"]and run["run_attempt"]==1 and run["status"]=="completed"and run["conclusion"]=="success","passed physical run")
    need(rel["tag_name"]==c["tag"]and rel["target_commitish"]==c["source"]and a.api("git/ref/tags/"+c["tag"])["object"]["sha"]==c["source"],"physical release tag")
    assets={x["name"]:x for x in rel["assets"]};need(set(assets)==set(c["assets"]),"complete physical asset set")
    work=ROOT/"canonical-physical-cache";work.mkdir()
    for n,p in c["assets"].items():
        x=assets[n];need(x["id"]==p["id"]and x["size"]==p["bytes"]and x["digest"]=="sha256:"+p["sha256"],"physical asset metadata")
        fetch_asset(p,work/n)
    need(json.loads((work/"complete-output-index.json").read_bytes())==c["index"],"independently pinned complete physical index")
    target=work/"selected";seen={};names=set()
    with tarfile.open(work/"native-physical.tar.gz","r|gz")as tar:
        for m in tar:
            need(m.name not in names,"unique physical member");names.add(m.name)
            n=a.relative(m.name,"wire-shortcuts-physical")
            need(m.isfile()and n in c["index"]["files"],"known regular physical member")
            p=target/n;p.parent.mkdir(parents=True,exist_ok=True)
            with p.open("xb")as f:shutil.copyfileobj(tar.extractfile(m),f)
            seen[n]=pin(p);need(seen[n]==c["index"]["files"][n],"exact physical member")
    need(seen==c["index"]["files"],"complete physical native capsule")
    q=json.loads((target/"physical-qualification.json").read_bytes());record=json.loads((target/"physical/result.json").read_bytes())
    need(q["status"]=="PASS_HORIZONTAL_GROUND_GDS_FULL560_DRC_DEEP_FLAT_LVS13"and q["gds"]==config()["candidate"]["gds"],"actual candidate physical qualification")
    need(record["status"]=="PASS_NATIVE_PDK_CDR_PD500_DRC_LVS_AND_FAULT_CONTROLS"and len(record["steps"])==16,"all original native physical gates")
    need(record["steps"]["drc"]["measurement"]["markers"]==0 and record["steps"]["drc"]["measurement"]["category_count"]==560,"actual complete clean DRC")
    need(all(v["status"]==("PASS"if n in("drc","lvs","lvs_flat")else"REJECTED_EXPECTED_FAULT")for n,v in record["steps"].items()),"all native fault controls")
    save("physical-acquisition.json",dict(run=run,release=rel,authenticated_members=seen))
    alias=OUT/"physical-alias"
    for n in seen:
        if n.startswith("layout/")or n.startswith("physical/lvs_flat/"):
            p=alias/"native"/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(target/n,p);need(pin(p)==seen[n],"unchanged physical alias")
    return alias
def prepare():
    c=config();reference=ROOT/"wire-native-cache/selected";physical=OUT/"physical-alias";workspace=OUT/"view";view=workspace/"candidate"
    rm=json.loads((OUT/"reference-selected-members.json").read_bytes());pm=core.projection.inventory(physical)
    original=json.loads((ROOT/PARENT).read_bytes())
    for n,p in rm.items():need(p==original["complete_members"][n],"authenticated original selected source")
    need(pin(reference/(c["reference_prefix"]+"parent/layout/"+TOP+".gds"))==c["original_reference_gds"],"actual original reference")
    core.projection.project_view(reference,physical,view,ROOT,rm,pm,c["reference_prefix"],c["candidate"]["gds"],c["wire_workers"])
    texts,records=core.derived_sources(ROOT,c)
    for name,text in texts.items():core.projection.write_new(view,"methods/"+name,text.encode())
    save("view/derived-methods.json",records);core.verify_prepared(view,ROOT,c)
def prove_material(pya,reference,view,old,new,c):
    _,before=core.component_keys(old["graph"]);_,after=core.component_keys(new["graph"])
    need(set(before)==set(after),"all complete conductor partitions preserved")
    original_wire=reference/(c["reference_prefix"]+"wire/native05/wires.l2n")
    need(pin(original_wire)==c["generation"]["proof"]["input_l2n"],"exact actual prior ground wire graph")
    ow=pya.LayoutToNetlist();ow.read(str(original_wire))
    nw=pya.LayoutToNetlist();nw.read(str(view/"wire/native05/wires.l2n"))
    on={n.cluster_id:n for n in ow.netlist().top_circuit().each_net()};nn={n.cluster_id:n for n in nw.netlist().top_circuit().each_net()}
    need(set(on)=={v["component"]for v in before.values()}and set(nn)=={v["component"]for v in after.values()},"complete old and new wire net census")
    need(set(old["graph"]["layers"])==set(new["graph"]["layers"])=={str(n)for n in core.LAYERS},"all13 conductor layers")
    matches=[(k,v)for k,v in before.items()if v["component"]==14 and v["native_cluster"]==24]
    need(len(matches)==1,"unique actual prior avss partition")
    key,owner=matches[0]
    original=core.layer_region(pya,ow,on[owner["component"]],old["graph"],8).merged()
    actual_anchors={a["label"]:a for a in old["anchors"]["anchors"]}
    for row in c["generation"]["targets"]:
        need(row["original_anchor"]==actual_anchors[row["label"]],"independent original source anchor identity")
    grouped={key:declared_layers(pya,original,c["generation"]["targets"])}
    records=[]
    for part in sorted(before):
        a=before[part];b=after[part]
        for layer in core.LAYERS:
            left=core.layer_region(pya,ow,on[a["component"]],old["graph"],layer)
            right=core.layer_region(pya,nw,nn[b["component"]],new["graph"],layer)
            addition=grouped.get(part,{}).get(layer,pya.Region())
            material_union(pya,left,right,addition)
            records.append(dict(partition=json.loads(part),layer=layer,old_component=a["component"],new_component=b["component"],
              old_area_dbu2=left.area(),new_area_dbu2=right.area(),added_area_dbu2=(right-left).area(),declared_added_area_dbu2=(addition-left).area()))
    changed=[r for r in records if r["added_area_dbu2"]]
    need(len(changed)==1 and changed[0]["partition"]==json.loads(key)and changed[0]["layer"]==8,"sole avss Metal1 material addition")
    need(changed[0]["added_area_dbu2"]==changed[0]["declared_added_area_dbu2"]==48000000,"exact native source M1 added area")
    need(len(records)==len(before)*13,"complete partition layer census")
    return dict(status="PASS_ALL_NATIVE_PARTITIONS_ALL13LAYERS_EXACT8_SOURCE_M1",records=records,targets={"avss":key},**FLAGS)
def qualify():
    import pya
    c=config();reference=ROOT/"wire-native-cache/selected";view=OUT/"view/candidate"
    core.verify_prepared(view,ROOT,c)
    planes=json.loads((view/"native-planes.json").read_bytes());recovery=json.loads((view/"wire/source-pins.json").read_bytes())
    need(planes["status"]=="PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS"and len(planes["anchors"])==160 and len(planes["controls"])==19,"all native planes and faults")
    parent=planes["parent_geometry"];need(len(parent["controls"])==5 and len(parent["actual_placements"])==16 and len(parent["checked_layers_by_kind"])==9,"all independent leaves and transforms")
    need(recovery["status"]=="PASS_RECOVERED_SOURCE_PIN_BOXES_ON_IDENTICAL_PRIMITIVE_DRAWING"and recovery["target_gds_sha256"]==c["candidate"]["gds"]["sha256"]and recovery["target_geometry_edited"]is False and recovery["missing_referenced_primitive_rejected"]is True,"actual recovered source pins")
    identities=core.identity_namespace(ROOT,c);producer=ROOT/(core.projection.WIRE_SOURCE+"locate01.py")
    old_layout,old=identities.read_side(pya,reference,core.selected_files(c["reference_prefix"]),producer)
    new_layout,new=identities.read_side(pya,view,core.selected_files(),producer)
    save("view/old-native-identity.json",old);save("view/new-native-identity.json",new)
    comparison=identities.compare_witnesses(old,new);save("view/native-identity-comparison.json",comparison)
    faults=identities.witness_controls(old,new);save("view/actual-witness-faults.json",faults)
    material=prove_material(pya,reference,view,old,new,c);save("view/full-partition-material.json",material)
    reports={"parent-geometry":parent,"planes":planes,"source-pins":recovery,"graph":new["graph"],"locations":new["locations"],"anchors":new["anchors"]}
    bindings={n:core.report_inputs(r,view)for n,r in reports.items()};save("view/fresh-report-bindings.json",bindings)
    files=core.projection.inventory(view);need(len(files)==78,"complete canonical file census")
    save("view/canonical-view-qualification.json",dict(status="PASS_LOCAL_SOURCE_M1_NATIVE_CANONICAL_VIEW_REQUIRES_FRESH_RC",
      candidate_gds=c["candidate"]["gds"],physical_producer=c["physical"]["run"],current_files=files,
      complete_current_file_count=len(files),native_identity=comparison,native_view_executed=True,
      material=pin(OUT/"view/full-partition-material.json"),fresh_report_bindings=bindings,**FLAGS))
def phase(mode):
    gate();c=config()
    if mode=="prepare":prepare()
    elif mode in("planes","recover"):core.derived(mode,OUT/"view/candidate",ROOT,c)
    elif mode=="verify":qualify()
    else:raise ValueError(mode)
    gate()
def fetch_asset(asset,path):
    need(not path.exists(),"no overwrite download")
    with path.open("xb")as f:subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/releases/assets/"+str(asset["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True)
    need(pin(path)==dict(bytes=asset["bytes"],sha256=asset["sha256"]),"complete downloaded asset")
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


def acquire_reference():
    import cloud_cdr_wire_geometry_acquire as a
    cfg=json.loads((ROOT/PARENT).read_bytes());p=cfg["producer"]
    need(p["run"]==41389957475 and p["source"]=="fe2ccfc1529b0e7507a585d3d8078e9d60af368d"and p["release"]==431078750,"actual current horizontal-ground fresh-RC reference")
    run=api("actions/runs/"+str(p["run"]));rel=api("releases/"+str(p["release"]))
    need(run["head_sha"]==p["source"]and run["conclusion"]=="success"and run["run_attempt"]==1,"successful actual reference")
    need(rel["target_commitish"]==p["source"]and rel["tag_name"]==p["tag"]and api("git/ref/tags/"+p["tag"])["object"]["sha"]==p["source"],"reference release")
    assets={x["name"]:x for x in rel["assets"]};need(set(assets)==set(p["assets"]),"all actual reference assets")
    work=ROOT/"wire-native-cache";work.mkdir()
    for name,expected in p["assets"].items():
        observed=assets[name];need(observed["id"]==expected["id"]and observed["size"]==expected["bytes"]and observed["digest"]=="sha256:"+expected["sha256"],"reference asset")
        need((work/name).parent==work,"flat reference asset name");fetch_asset(expected,work/name)
    index=json.loads((work/"complete-output-index.json").read_bytes())
    need(index["files"]==cfg["complete_members"]and index["context"]==dict(run=p["run"],source=p["source"],attempt=1),"actual reference index")
    target=work/"selected";seen={}
    with tarfile.open(work/"native-fresh-rc.tar.gz","r|gz")as tar:
        for m in tar:
            n=a.relative(m.name,p["archive_root"])
            need(m.isfile()and n in index["files"]and n not in seen and m.size==index["files"][n]["bytes"],"exact regular reference member")
            path=target/n;path.parent.mkdir(parents=True,exist_ok=True)
            with path.open("xb")as f:shutil.copyfileobj(tar.extractfile(m),f)
            seen[n]=pin(path);need(seen[n]==index["files"][n],"reference native bytes "+n)
    need(seen==index["files"]and len(seen)==3236,"complete current current horizontal-ground native reference")
    need(pin(target/"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds")==config()["original_reference_gds"],"actual before-reference GDS")
    save("reference-acquisition.json",dict(run=run,release=rel,authenticated_members=seen,native_payloads_cloud_only=True))
    return target

def verify():
    controls()
    import cloud_cdr_wire_geometry_acquire as acquire
    reference=acquire_reference()
    save("reference-selected-members.json",core.projection.inventory(reference))
    acquire_physical();restore_runtime()
    app=Path(os.environ["RUNNER_TEMP"])/"current-tail-physical.AppImage";need(sha(app)==APP_SHA,"pinned AppImage")
    policy=json.loads((ROOT/"current-cdr-runtime-policy.json").read_bytes())
    need(policy["source"]==os.environ["GITHUB_SHA"]and policy["run_id"]==int(os.environ["GITHUB_RUN_ID"])and policy["attempt"]==1,"current scoped runtime")
    need(policy["appimage"]==str(app)and policy["appimage_sha256"]==APP_SHA and policy["loaded"]and not policy["global_policy_changed"]and policy["restriction_before"]==policy["restriction_after"],"unchanged runtime policy")
    need(policy["profile"]=="/etc/apparmor.d/nssoc-cdr-runtime-"+os.environ["GITHUB_RUN_ID"]+"-1"and hashlib.sha256(policy["profile_text"].encode()).hexdigest()==policy["profile_sha256"],"run owned profile")
    save("runtime-policy.json",policy)
    launcher=runtime.launcher(ROOT,gate,"501d4846603abd42b9efeaf515a5ad45f136d58997e37b16329003623b9f33ac")
    with tokenless():smoke=launcher.probe(app,APP_SHA,OUT/"runtime-smoke")
    need(smoke["accepted"]is True,"native tool smoke")
    sup=runtime.supervisor(ROOT,OUT,OUT/"supervision",gate,runtime.SAMPLER_SHA);sup.TRACE.mkdir()
    beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start();previous={};commands=[]
    for sig in(signal.SIGINT,signal.SIGTERM):previous[sig]=signal.getsignal(sig);signal.signal(sig,sup.interrupted)
    def execute(argv,label):
        argv=list(map(str,argv))
        with tokenless():sup.supervised(argv,label,seconds=1200,cwd=ROOT)
        r=json.loads((sup.TRACE/(label+".command.json")).read_bytes())
        need(r["argv"]==argv and r["minimum_available_kib"]==2097152 and r["maximum_group_rss_kib"]==10485760,"unchanged execution boundaries")
        need(r["returncode"]==0 and r["supervision_failure"]is None and not r["process_group_cleanup"]["remaining_live"],"native phase and cleanup")
        for stream in("stdout","stderr"):need(pin(sup.TRACE/(label+"."+stream))==dict(bytes=r[stream+"_bytes"],sha256=r[stream+"_sha256"]),"whole phase stream")
        commands.append(r);gate()
    error=None;cleanup=[]
    try:
        script=ROOT/"scripts/cloud_cdr_wire_shortcuts_canonical.py"
        for mode in("prepare","planes","recover"):execute([app,"python",script,"--phase",mode],"canonical-"+mode)
        for worker in core.projection.WORKERS:execute([app,"python",OUT/"view/candidate/wire"/worker],"fresh-"+worker.removesuffix(".py"))
        execute([app,"python",script,"--phase","verify"],"canonical-verify")
        q=json.loads((OUT/"view/canonical-view-qualification.json").read_bytes())
        need(q["status"]=="PASS_LOCAL_SOURCE_M1_NATIVE_CANONICAL_VIEW_REQUIRES_FRESH_RC","complete actual native view")
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
    gate();e=os.environ;tag="cloud-results-"+e["GITHUB_RUN_ID"]+"-1-cdr-wire-shortcuts-canonical"
    rel=api("releases/tags/"+tag)
    need(rel["target_commitish"]==e["GITHUB_SHA"]and not rel["assets"],"empty current-source reserved release")
    need(api("git/ref/tags/"+tag)["object"]["sha"]==e["GITHUB_SHA"],"reserved tag")
    files={str(p.relative_to(OUT)):p for p in sorted(OUT.rglob("*"))if p.is_file()}
    need(files and all(not p.is_symlink()for p in files.values()),"all regular result files")
    pub=ROOT/"wire-canonical-publication";pub.mkdir()
    index=dict(context=dict(run=int(e["GITHUB_RUN_ID"]),attempt=1,source=e["GITHUB_SHA"]),files={n:pin(p)for n,p in files.items()})
    (pub/"complete-output-index.json").write_bytes(encode(index));archive=pub/"native-canonical.tar.gz"
    with tarfile.open(archive,"w:gz")as tar:
        for n,p in files.items():tar.add(p,arcname="wire-shortcuts-canonical/"+n,recursive=False)
    need(archive.stat().st_size<1500*1024*1024,"single native result asset below limit")
    subprocess.run(["gh","release","upload",tag,str(pub/"complete-output-index.json"),str(archive),"--repo","Melihakbulut221/nssoc"],check=True)
    assets=api("releases/"+str(rel["id"]))["assets"]
    for p in(pub/"complete-output-index.json",archive):
        a=next(a for a in assets if a["name"]==p.name);need(a["size"]==p.stat().st_size and a["digest"]=="sha256:"+sha(p),"exact uploaded result")
    save("publication.json",dict(tag=tag,release=rel["id"],assets=assets))
def derived():
    dest=ROOT/"wire-canonical-derived";dest.mkdir()
    copied={}
    for p in sorted(OUT.rglob("*")):
        if p.is_file()and p.suffix in(".json",".jsonl",".log",".stdout",".stderr")and p.stat().st_size<=32*1024*1024:
            n=p.relative_to(OUT);q=dest/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);copied[str(n)]=pin(q)
    (dest/"derived-index.json").write_bytes(encode(copied))

def api(path):return json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/"+path]))
def main():
    mode=sys.argv[1:]
    if mode==["--publish"]:publish();return
    if mode==["--derived"]:derived();return
    try:
        if mode==["--controls"]:controls()
        elif mode==["--verify"]:verify()
        elif len(mode)==2 and mode[0]=="--phase":phase(mode[1])
        else:raise ValueError(mode)
    except BaseException as exc:
        try:save("failure"+("-"+mode[-1]if mode and mode[0]=="--phase"else"")+".json",dict(error=repr(exc),traceback=traceback.format_exc(),**FLAGS))
        except BaseException as secondary:print("UNSAVED_FAILURE",repr(exc),repr(secondary),flush=True)
        raise
if __name__=="__main__":main()
