#!/usr/bin/env python3
"""Read actual current GDS/LVS to bind each model-range proposal to its old PCell."""
import hashlib,json,math,os,subprocess,sys,tarfile,time,traceback
from pathlib import Path,PurePosixPath
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"cloud-domain-geometry";NATIVE=OUT/"native";DERIVED=OUT/"derived"
CFG="scripts/cdr-current-domain-geometry-inputs.json"
METHOD="scripts/cdr-current-domain-geometry-methods.json"
BRANCH="codex/cdr-current-domain-geometry"
REPO="Melihakbulut221/nssoc"
TOP="nssoc_cdr_pd500_resistor_v59"
def need(v,m):
    if not v:raise ValueError(m)
def enc(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def sha(p):
    with Path(p).open("rb")as stream:return hashlib.file_digest(stream,"sha256").hexdigest()
def pin(p):return dict(bytes=Path(p).stat().st_size,sha256=sha(p))
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("xb")as f:f.write(enc(v))
def api(p):return json.loads(subprocess.check_output(["gh","api","repos/"+REPO+"/"+p],timeout=180))
def get(o,n):
    v=getattr(o,n)
    return v()if callable(v)else v
def gate():
    e=os.environ
    need(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted","hosted only")
    need(e["GITHUB_REPOSITORY"]==REPO and e["GITHUB_REF"]=="refs/heads/"+BRANCH,"exact branch")
    need(e["GITHUB_EVENT_NAME"]=="workflow_dispatch"and e["GITHUB_RUN_ATTEMPT"]=="1","first explicit attempt")
    need(e["APPROVED_SOURCE"]==e["GITHUB_SHA"]==subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"exact approved source")
    for p,v in json.loads((ROOT/METHOD).read_bytes())["files"].items():need(pin(ROOT/p)==v,"protected source "+p)
    return dict(source=e["GITHUB_SHA"],run=int(e["GITHUB_RUN_ID"]),attempt=1)
def reservation(wait=False):
    ctx=gate();tag="cloud-results-"+str(ctx["run"])+"-1-cdr-current-domain-geometry"
    for i in range(120 if wait else 1):
        p=subprocess.run(["gh","api","repos/"+REPO+"/releases/tags/"+tag],text=True,capture_output=True)
        if p.returncode==0:break
        need(wait and "HTTP 404"in p.stderr,"missing output reservation");time.sleep(2)
    else:raise ValueError("missing output reservation")
    r=json.loads(p.stdout)
    need(r["target_commitish"]==ctx["source"]and r["tag_name"]==tag and r["prerelease"]and not r["draft"],"exact output release")
    need(api("git/ref/tags/"+tag)["object"]["sha"]==ctx["source"],"exact output tag")
    need(not r["assets"],"empty output reservation")
    return r
def relative(name):
    p=PurePosixPath(name)
    need(not p.is_absolute()and ".."not in p.parts and str(p)==name and p.parts[0]=="wire-shortcuts-physical"and len(p.parts)>1,"safe exact archive path")
    return str(PurePosixPath(*p.parts[1:]))
def controls():
    need(relative("wire-shortcuts-physical/layout/a.gds")=="layout/a.gds","positive archive path")
    bad=["/wire-shortcuts-physical/a","wire-shortcuts-physical/../a","wire-shortcuts-physical//a","wrong/a","wire-shortcuts-physical","wire-shortcuts-physical/./a"]
    for p in bad:
        try:relative(p)
        except ValueError:pass
        else:raise ValueError("accepted unsafe archive path")
    mapping=json.loads((ROOT/"docs/evidence/cdr-current-domain-parent-map.json").read_bytes())
    need(len(mapping["pairs"])==500 and len({p["layout"]["id"]for p in mapping["pairs"]})==500,"unique actual500 map")
    need(all(p["status"]=="Match"for p in mapping["pairs"]),"all mapped devices matched")
    return dict(path_refusals=len(bad),mapped_parent_devices=500,native_executed=False)
def acquire(cfg):
    r=api("actions/runs/"+str(cfg["run"]));rel=api("releases/"+str(cfg["release"]))
    need(r["head_sha"]==cfg["source"]and r["status"]=="completed"and r["conclusion"]=="success"and r["run_attempt"]==1,"actual qualified physical producer")
    need(rel["target_commitish"]==cfg["source"]and rel["tag_name"]==cfg["tag"]and api("git/ref/tags/"+cfg["tag"])["object"]["sha"]==cfg["source"],"physical release identity")
    assets={a["name"]:a for a in rel["assets"]}
    need(set(assets)==set(cfg["assets"]),"complete physical assets")
    for name,want in cfg["assets"].items():
        a=assets[name]
        need(a["id"]==want["id"]and a["size"]==want["bytes"]and a["digest"]=="sha256:"+want["sha256"],"physical asset metadata")
        target=NATIVE/name
        with target.open("xb")as f:subprocess.run(["gh","api","repos/"+REPO+"/releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True,timeout=600)
        need(pin(target)=={k:want[k]for k in ("bytes","sha256")},"full physical asset bytes")
    index=json.loads((NATIVE/"complete-output-index.json").read_bytes())
    need(index==cfg["index"],"complete pinned physical member index")
    seen={};selected={}
    with tarfile.open(NATIVE/"native-physical.tar.gz","r|gz")as tar:
        for m in tar:
            n=relative(m.name);need(m.isfile()and n not in seen and n in index["files"],"unique regular known member")
            data=tar.extractfile(m).read()
            observed=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
            need(observed==index["files"][n],"complete member digest "+n);seen[n]=observed
            if n in cfg["selected"]:
                p=NATIVE/"selected"/n;p.parent.mkdir(parents=True,exist_ok=True)
                with p.open("xb")as f:f.write(data)
                selected[n]=p
    need(seen==index["files"]and set(selected)==set(cfg["selected"]),"every archive member authenticated")
    save(DERIVED/"acquisition.json",dict(run=r,release=rel,all_members=seen,selected={k:pin(p)for k,p in selected.items()}))
    return selected
def inspect(paths):
    import klayout.db as db
    mapping=json.loads((ROOT/"docs/evidence/cdr-current-domain-parent-map.json").read_bytes())
    expected={p["layout"]["id"]:p for p in mapping["pairs"]}
    lvs=db.LayoutVsSchematic();lvs.read(str(paths["physical/lvs_flat/result.lvsdb"]))
    xref=lvs.xref();pairs=list(xref.each_circuit_pair())
    need(pairs and all(str(p.status())=="Match"for p in pairs),"actual original LVS all circuit pairs matched")
    pair=next(p for p in pairs if p.first().name==TOP);circuit=pair.first()
    devices=list(xref.each_device_pair(pair))
    need(len(devices)==500 and all(str(p.status())=="Match"and p.first()is not None and p.second()is not None for p in devices),"all actual500 layout/schematic pairs")
    native_pairs=[]
    for row in devices:
        sides={}
        for label,d in (("layout",row.first()),("schematic",row.second())):
            dc=d.device_class()
            sides[label]=dict(id=int(get(d,"id")),name=get(d,"name"),expanded_name=get(d,"expanded_name"),model=get(dc,"name"),
                parameters={get(q,"name"):d.parameter(get(q,"id"))for q in dc.parameter_definitions()},
                terminals={get(t,"name"):dict(cluster=get(d.net_for_terminal(get(t,"id")),"cluster_id"),name=get(d.net_for_terminal(get(t,"id")),"name"))for t in dc.terminal_definitions()})
        native_pairs.append(dict(status=str(row.status()),**sides))
    save(DERIVED/"actual-native-pairs.json",dict(pairs=native_pairs,original_flat_lvs=pin(paths["physical/lvs_flat/result.lvsdb"])))
    layout=db.Layout();layout.read(str(paths["layout/"+TOP+".gds"]))
    top=layout.cell(TOP)
    save(DERIVED/"actual-layout-roots.json",dict(expected_top=TOP,matched_lvs_top=circuit.name,
        roots=[dict(name=c.name,bbox_dbu=str(c.bbox()))for c in layout.top_cells()],
        actual_gds=pin(paths["layout/"+TOP+".gds"])))
    need(top is not None and top.name==circuit.name==TOP,"exact named GDS top matched by original full LVS")
    need(math.isclose(lvs.internal_layout().dbu,layout.dbu),"same native LVS/GDS coordinate units")
    dbu=layout.dbu;need(math.isclose(dbu,.001),"actual nanometre GDS units")
    pcells=[]
    def walk(cell,trans,path,ancestors):
        idx=cell.cell_index();need(idx not in ancestors,"acyclic native hierarchy")
        if cell.name.startswith("nmos"):
            box=cell.bbox().transformed(trans)
            pins=[]
            for li in layout.layer_indexes():
                info=layout.get_info(li)
                if info.datatype!=2:continue
                for shape in cell.shapes(li).each():
                    pins.append(dict(layer=info.to_s(),bbox_dbu=str(shape.bbox().transformed(trans))))
            pcells.append(dict(cell=cell.name,path=path,transform=str(trans),bbox_dbu=str(box),bbox=[box.left,box.bottom,box.right,box.top],pin_shapes=pins))
            return
        for i,inst in enumerate(cell.each_inst()):
            need(not inst.is_regular_array(),"explicit individual instance expected; arrays require explicit expansion")
            walk(layout.cell(inst.cell_index),trans*inst.cplx_trans,path+"/"+str(i)+"_"+str(inst.cell_index),ancestors|{idx})
    walk(top,db.ICplxTrans(),TOP,set())
    need(len(pcells)==50 and len({p["path"]for p in pcells})==50,"all50 independent original nmos PCells")
    save(DERIVED/"native-nmos-pcell-inventory.json",dict(dbu=dbu,pcells=pcells))
    records=[];mos=[];used=set()
    for pair in devices:
        d,reference=pair.first(),pair.second();ident=int(get(d,"id"));p=expected[ident]
        dc=d.device_class();model=get(dc,"name").lower()
        need(model==p["layout"]["model"].lower()==p["schematic"]["model"].lower(),"actual mapped primitive model")
        need(get(reference,"name")==p["schematic"]["name"],"actual mapped schematic identity")
        parameters={get(q,"name"):d.parameter(get(q,"id"))for q in dc.parameter_definitions()}
        for k,v in p["layout"]["parameters"].items():
            need(k in parameters and math.isclose(parameters[k],v,rel_tol=1e-9,abs_tol=1e-9),"actual extracted parameter "+k)
        terminals={}
        for t in dc.terminal_definitions():
            name=get(t,"name");net=d.net_for_terminal(get(t,"id"));want=p["layout"]["terminals"][name]
            need(get(net,"cluster_id")==want["cluster"]and get(net,"name")==want["name"],"actual mapped terminal owner "+str((ident,name,get(net,"cluster_id"),get(net,"name"),want)))
            terminals[name]=dict(native_cluster=get(net,"cluster_id"),native_net=get(net,"name"))
            if model=="sg13_lv_nmos":
                refs=[r for r in net.each_terminal()if get(r.device(),"id")==ident and get(r,"terminal_id")==get(t,"id")]
                need(len(refs)==1,"exact terminal reference")
                regions=lvs.shapes_of_terminal(refs[0])
                terminals[name]["layers"]=[dict(layer=int(li),bbox_dbu=str(region.bbox()),bbox=[region.bbox().left,region.bbox().bottom,region.bbox().right,region.bbox().top],area_dbu2=region.area(),polygons=region.count())for li,region in sorted(regions.items())if not region.is_empty()]
                need(terminals[name]["layers"],"actual nonempty terminal geometry")
        record=dict(native_id=ident,model=model,schematic_name=get(reference,"name"),parameters=parameters,terminals=terminals)
        records.append(record)
        if model=="sg13_lv_nmos":
            gates=terminals["G"]["layers"];need(len(gates)==1 and gates[0]["polygons"]==1,"single original gate polygon")
            b=gates[0]["bbox"];need((b[2]-b[0])*(b[3]-b[1])==gates[0]["area_dbu2"],"original rectangular gate")
            matches=[q for q in pcells if q["bbox"][0]<=b[0]and q["bbox"][1]<=b[1]and q["bbox"][2]>=b[2]and q["bbox"][3]>=b[3]]
            need(len(matches)==1 and matches[0]["path"]not in used,"unique actual MOS gate PCell enclosure")
            used.add(matches[0]["path"]);record["pcell"]=matches[0]
            width=max(b[2]-b[0],b[3]-b[1])*dbu;length=min(b[2]-b[0],b[3]-b[1])*dbu
            need(math.isclose(width,parameters["W"],abs_tol=1e-8)and math.isclose(length,parameters["L"],abs_tol=1e-8),"actual gate dimensions match extracted W/L")
            mos.append(record)
    need(len(mos)==len(used)==50 and {r["native_id"]for r in records}==set(expected),"complete physical original mapping")
    return dict(status="PASS_CURRENT50_MOS_ACTUAL_GEOMETRY_AND500_NATIVE_MAPPING_NOT_NEW_LAYOUT",
                source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),devices=records,mos_devices=mos,
                original_gds=pin(paths["layout/"+TOP+".gds"]),original_flat_lvs=pin(paths["physical/lvs_flat/result.lvsdb"]),
                original_widths_um=dict(Counter(str(r["parameters"]["W"])for r in mos)),
                candidate_layout_generated=False,new650_device_lvs_passed=False,new650_device_drc_passed=False,
                qualified_pex=False,full_phy_accepted=False,final_timing_complete=False)
def execute():
    ctx=gate();OUT.mkdir();NATIVE.mkdir();DERIVED.mkdir()
    save(DERIVED/"context.json",ctx);save(DERIVED/"controls.json",controls());save(DERIVED/"reservation.json",reservation(True))
    try:
        paths=acquire(json.loads((ROOT/CFG).read_bytes()));result=inspect(paths)
        gate();save(DERIVED/"result.json",result)
        print(json.dumps({k:result[k]for k in ("status","run","original_widths_um")}),flush=True)
    except BaseException as e:
        save(DERIVED/"failure.json",dict(error=repr(e),traceback=traceback.format_exc(),full_phy_accepted=False));raise
def publish():
    ctx=gate();rel=reservation();files={str(p.relative_to(OUT)):p for p in OUT.rglob("*")if p.is_file()}
    need(files and all(not p.is_symlink()for p in files.values()),"owned complete result")
    pub=ROOT/"domain-geometry-publication";pub.mkdir()
    save(pub/"complete-output-index.json",dict(context=ctx,files={n:pin(p)for n,p in files.items()}))
    archive=pub/"native-geometry.tar.gz"
    with tarfile.open(archive,"w:gz")as tar:
        for n,p in sorted(files.items()):tar.add(p,arcname="domain-geometry/"+n,recursive=False)
    need(archive.stat().st_size<256*1024**2,"bounded complete geometry result")
    for p in pub.iterdir():subprocess.run(["gh","release","upload",rel["tag_name"],str(p),"--repo",REPO],check=True,timeout=600)
    observed=api("releases/"+str(rel["id"]));assets={a["name"]:a for a in observed["assets"]}
    need(set(assets)=={p.name for p in pub.iterdir()},"complete publication")
    for p in pub.iterdir():need(assets[p.name]["size"]==p.stat().st_size and assets[p.name]["digest"]=="sha256:"+sha(p),"publication readback")
    save(DERIVED/"publication.json",dict(release=rel["id"],assets=assets,context=ctx))
if __name__=="__main__":
    if sys.argv[1:]==["--execute"]:execute()
    elif sys.argv[1:]==["--publish"]:publish()
    else:raise SystemExit("explicit mode required")
