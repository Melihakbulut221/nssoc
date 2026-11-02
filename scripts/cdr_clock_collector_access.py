#!/usr/bin/env python3
"""Rank actual collector access resistance and generate redundant same-net vias."""
import hashlib,json,math,os,subprocess,sys,tarfile,time,traceback
from pathlib import Path,PurePosixPath
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"cloud-clock-access";NATIVE=OUT/"native";DERIVED=OUT/"derived"
CFG="scripts/cdr-clock-collector-access-inputs.json"
METHOD="scripts/cdr-clock-collector-access-methods.json"
BRANCH="codex/cdr-clock-collector-access"
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
    ctx=gate();tag="cloud-results-"+str(ctx["run"])+"-1-cdr-clock-collector-access"
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
    need(not p.is_absolute()and ".."not in p.parts and str(p)==name and p.parts[0]=="wire-shortcuts-fresh-rc"and len(p.parts)>1,"safe exact archive path")
    return str(PurePosixPath(*p.parts[1:]))

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
    with tarfile.open(NATIVE/"native-fresh-rc.tar.gz","r|gz")as tar:
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

def number(token):
    import re
    from decimal import Decimal
    m=re.fullmatch(r"([-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?)([numkpf]?)",token.lower())
    need(m is not None,"finite supported resistance token")
    v=Decimal(m[1])*{"":Decimal(1),"n":Decimal("1e-9"),"u":Decimal("1e-6"),"m":Decimal("1e-3"),"k":Decimal("1e3"),"p":Decimal("1e-12"),"f":Decimal("1e-15")}[m[2]]
    need(v.is_finite()and v>0,"positive physical resistance")
    return v
def solve(edges,source,sink):
    import numpy as np
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    adjacency={}
    for name,a,b,r in edges:
        need(a!=b and math.isfinite(r)and r>0,"valid resistor")
        adjacency.setdefault(a,set()).add(b);adjacency.setdefault(b,set()).add(a)
    need(source!=sink and source in adjacency and sink in adjacency,"distinct original ports")
    seen={source};todo=[source]
    while todo:
        for n in adjacency[todo.pop()]:
            if n not in seen:seen.add(n);todo.append(n)
    need(sink in seen,"same connected native resistor component")
    selected=[e for e in edges if e[1]in seen]
    names=sorted(seen-{sink});idx={n:i for i,n in enumerate(names)}
    rr=[];cc=[];vv=[]
    for _,a,b,r in selected:
        for n,other in ((a,b),(b,a)):
            if n==sink:continue
            rr.append(idx[n]);cc.append(idx[n]);vv.append(1/r)
            if other!=sink:rr.append(idx[n]);cc.append(idx[other]);vv.append(-1/r)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(names),len(names))).tocsc()
    rhs=np.zeros(len(names));rhs[idx[source]]=1
    volt=spsolve(matrix,rhs)
    need(np.isfinite(volt).all(),"finite connected solve")
    residual=float(np.max(np.abs(matrix@volt-rhs)))
    need(residual<1e-8,"unit injection KCL")
    potentials={n:float(volt[i])for n,i in idx.items()};potentials[sink]=0.
    ranked=[]
    for name,a,b,r in selected:
        current=(potentials[a]-potentials[b])/r
        ranked.append(dict(element=name,a=a,b=b,resistance_ohm=r,unit_current_a=current,power_at_1a_w=current*current*r))
    resistance=potentials[source];energy=sum(e["power_at_1a_w"]for e in ranked)
    need(resistance>0 and math.isclose(resistance,energy,rel_tol=1e-8,abs_tol=1e-9),"positive effective resistance equals full network power")
    for e in ranked:e["fraction_of_effective_resistance"]=e["power_at_1a_w"]/resistance
    return dict(source=source,sink=sink,effective_resistance_ohm=resistance,kcl_max_residual_a=residual,
                nodes=len(seen),edges=len(selected),all_edges=sorted(ranked,key=lambda x:-x["power_at_1a_w"]))
def controls():
    a=solve([("r1","a","b",2.),("r2","b","c",3.),("r3","a","c",5.)],"a","c")
    need(math.isclose(a["effective_resistance_ohm"],2.5),"parallel-series analytic control")
    reverse=solve([("r1","a","b",2.),("r2","b","c",3.),("r3","a","c",5.)],"c","a")
    need(math.isclose(a["effective_resistance_ohm"],reverse["effective_resistance_ohm"]),"reciprocity")
    rejected=[]
    for label,edges,s,t in [
      ("disconnected",[("r","a","b",1.),("q","c","d",2.)],"a","c"),
      ("negative",[("r","a","b",-1.)],"a","b"),
      ("nan",[("r","a","b",float("nan"))],"a","b"),
      ("same_port",[("r","a","b",1.)],"a","a")]:
        try:solve(edges,s,t)
        except ValueError:rejected.append(label)
        else:raise ValueError("missed resistance refusal")
    return dict(analytic_resistance_ohm=2.5,reciprocity=True,rejected=rejected,physical_acceptance=False)
def inspect(paths):
    import klayout.db as db,shlex
    from collections import Counter,defaultdict
    parse=lambda p:[shlex.split(s,comments=False)for s in p.read_text().splitlines()if s.strip()and not s.lstrip().startswith("*")]
    parent="binding/inputs/parent/layout/"+TOP+".gds"
    gp=paths[parent];wp=paths["binding/inputs/wire/native05/wires.l2n"]
    comp=json.loads(paths["mim/composition/composition.json"].read_bytes())
    anchors={a["label"]:a for a in json.loads(paths["mim/precise/wire/anchors08.json"].read_bytes())["anchors"]}
    need(len(anchors)==978,"actual full anchor census")
    raw=parse(paths["mim/precise/wire/rc03/pump_wires.ext"])
    distributed=parse(paths["mim/precise/wire/rc03/pump_wires.res.ext"])
    exported=[r for r in parse(paths["mim/precise/wire/rc03/wires.spice"])if r[0].lower().startswith("r")]
    need(len(exported)==26222 and all(len(r)==4 for r in exported),"all26222 actual wire resistors")
    key=lambda a,b,r:(tuple(sorted((a.lower(),b.lower()))),number(r))
    need(Counter(key(*r[1:4])for r in exported)==Counter(key(*r[1:4])for r in distributed if r[0]=="resist"),"all distributed/exported R values and endpoints agree")
    edges=[(r[0].lower(),r[1].lower(),r[2].lower(),float(number(r[3])))for r in exported]
    need(len({e[0]for e in edges})==len(edges),"unique resistor names")
    ports={r[1]:r for r in raw if r[0]=="port"}
    need(set(ports)==set(anchors),"all native ports")
    for name,r in ports.items():
        need(r[3:5]==r[5:7]and all(abs(int(v)*5-p)<=2 for v,p in zip(r[3:5],anchors[name]["point_dbu"])),"actual5nm extraction coordinate grid")
    points=defaultdict(list)
    for r in distributed:
        if r[0]=="rnode":
            need(len(r)==7,"original rnode record")
            points[r[1].lower()].append(dict(point_dbu=[int(r[4])*5,int(r[5])*5],raw=r))
    layout=db.Layout();layout.read(str(gp));top=layout.cell(TOP)
    need(top is not None and layout.dbu==.001,"current exact top and1nm grid")
    snapshot=lambda:{(layout.get_info(li).layer,layout.get_info(li).datatype):db.Region(top.begin_shapes_rec(li)).merged()for li in layout.layer_indexes()}
    before=snapshot()
    wires=db.LayoutToNetlist();wires.read(str(wp));need(wires.internal_layout().dbu==.001,"native conductor DBU")
    layers=(8,19,10,29,30,49,50,66,67,125,126,133,134)
    objects={n:wires.layer_by_name("gds_"+str(n))for n in layers}
    for n,r in objects.items():need(r is not None and(before.get((n,0),db.Region())^r).is_empty(),"all13 original GDS/native conductor unions")
    nets={n.cluster_id:n for n in wires.netlist().top_circuit().each_net()}
    cache={}
    def owned(component):
        if component not in cache:cache[component]={n:wires.shapes_of_net(nets[component],r,True).merged()for n,r in objects.items()}
        return cache[component]
    def bbox(r):
        b=r.bbox();return[b.left,b.bottom,b.right,b.top]
    def polygons(r):
        return [dict(bbox=bbox(db.Region(p)),hull=[[q.x,q.y]for q in p.each_point_hull()],
                     holes=[[[q.x,q.y]for q in p.each_point_hole(i)]for i in range(p.holes())],area_dbu2=p.area())for p in r.each()]
    def small(x,y,d):return db.Region(db.Box(x-d,y-d,x+d,y+d))
    target_anchors={};queries=[]
    for upper,clock in [(u,c)for us,cs in [((54,56),(61,62)),((106,108),(115,116))]for u in us for c in cs]:
        pair=[]
        for ident,terminal in ((upper,"E"),(clock,"C")):
            label="T"+str(ident).zfill(3)+"_"+terminal;a=anchors[label]
            need(a["detail"]["device"]==ident and a["detail"]["terminal"]==terminal and a["detail"]["model"].lower()=="npn13g2","actual HBT terminal")
            record=next(t for d in comp["device_records"]if int(d["native_id"])==ident for t in d["terminals"]if t["terminal"]==terminal)
            need(record["anchor"]==label and record["native_cluster"]==a["native_cluster"]and record["native_net"]==a["detail"]["native_net"],"composition terminal provenance")
            shapes=owned(a["wire_component"]);x,y=a["point_dbu"]
            need((small(x,y,1)-shapes[a["metal"]]).is_empty(),"actual terminal owned metal")
            pair.append(a);target_anchors[label]=a
        need(pair[0]["wire_component"]==pair[1]["wire_component"],"original same-net path")
        q=solve(edges,pair[0]["label"].lower(),pair[1]["label"].lower())
        q.update(native_net=pair[0]["detail"]["native_net"],wire_component=pair[0]["wire_component"])
        for edge in q["all_edges"]:
            edge["native_coordinates"]={k:points[edge[k]]for k in ("a","b")}
        queries.append(q)
    save(DERIVED/"all-eight-resistance-queries.json",dict(queries=queries,original_RC_unchanged=True,unit_injection_is_diagnostic_not_waveform=True))
    survey=[];additions={19:db.Region(),29:db.Region()};admitted=[];counts=Counter();extent=db.Region(top.bbox())
    # Only add redundant vias inside existing SAME-NET metals. No metal widening or device alteration.
    for label,a in sorted(target_anchors.items()):
        own=owned(a["wire_component"]);x,y=a["point_dbu"];window=small(x,y,4000)
        survey.append(dict(label=label,anchor=a,layers={str(n):dict(owned=polygons(r&window),foreign=polygons((objects[n]-r)&window))for n,r in own.items()}))
        for lower,via,upper in ((8,19,10),(10,29,30)):
            sites=(own[lower]&own[upper]&window).merged().sized(-145,-145,2)
            for poly in sites.each():
                b=poly.bbox()
                for xx in range(((b.left+4)//5)*5,b.right+1,480):
                    for yy in range(((b.bottom+4)//5)*5,b.top+1,480):
                        cut=small(xx,yy,95)
                        checks=dict(
                            lower_enclosure=(cut.sized(50,50,2)-own[lower]).is_empty(),
                            upper_enclosure=(cut.sized(50,50,2)-own[upper]).is_empty(),
                            original_via_spacing=(cut&objects[via].sized(240,240,2)).is_empty(),
                            new_via_spacing=(cut&additions[via].sized(240,240,2)).is_empty(),
                            foreign_lower=(cut.sized(50,50,2)&(objects[lower]-own[lower])).is_empty(),
                            foreign_upper=(cut.sized(50,50,2)&(objects[upper]-own[upper])).is_empty(),
                            in_extent=(cut-extent).is_empty())
                        for k,v in checks.items():
                            if not v:counts[k]+=1
                        if all(checks.values()):
                            additions[via]+=cut
                            admitted.append(dict(label=label,component=a["wire_component"],via_layer=via,lower=lower,upper=upper,bbox=bbox(cut),guards=checks))
    save(DERIVED/"actual-access-geometry.json",dict(targets=survey,all13native_unions_verified=True,all978native_coordinates_verified=True))
    save(DERIVED/"redundant-via-proposal.json",dict(admitted=admitted,refusals=dict(counts),within_existing_same_net_metals_only=True,physical_acceptance=False))
    candidate=None
    if admitted:
        for n,r in additions.items():
            need(r.count()==sum(a["via_layer"]==n for a in admitted),"unique disjoint new cuts")
            for p in r.each():top.shapes(layout.layer(n,0)).insert(p)
        target=NATIVE/"candidate-clock-access.gds";layout.write(str(target));candidate=pin(target)
        read=db.Layout();read.read(str(target));rt=read.cell(TOP)
        after={(read.get_info(li).layer,read.get_info(li).datatype):db.Region(rt.begin_shapes_rec(li)).merged()for li in read.layer_indexes()}
        for k in set(before)|set(after):
            expected=before.get(k,db.Region())
            if k[1]==0 and k[0]in additions:expected=(expected+additions[k[0]]).merged()
            need((expected^after.get(k,db.Region())).is_empty(),"exact serialized via-only delta")
    for n,p in paths.items():need(pin(p)==json.loads((ROOT/CFG).read_bytes())["index"]["files"][n],"original authenticated input unchanged")
    return dict(status="GENERATED_REDUNDANT_CLOCK_ACCESS_VIAS_REQUIRES_FULL_PHYSICAL_AND_RC"if admitted else"NO_ADMISSIBLE_REDUNDANT_VIA_WITHIN_EXISTING_METALS",
                run=int(os.environ["GITHUB_RUN_ID"]),source=os.environ["GITHUB_SHA"],candidate=candidate,
                new_via_count=len(admitted),via_layers=dict(Counter(str(a["via_layer"])for a in admitted)),
                query_effective_resistance_ohm={q["source"]+"->"+q["sink"]:q["effective_resistance_ohm"]for q in queries},
                original_gds=pin(gp),original_wire_l2n=pin(wp),physical_acceptance=False,electrical_improvement_proven=False,
                fresh_RC=False,full_phy_accepted=False,final_timing_complete=False)

def execute():
    ctx=gate();OUT.mkdir();NATIVE.mkdir();DERIVED.mkdir()
    save(DERIVED/"context.json",ctx);save(DERIVED/"controls.json",controls());save(DERIVED/"reservation.json",reservation(True))
    try:
        paths=acquire(json.loads((ROOT/CFG).read_bytes()));result=inspect(paths)
        gate();save(DERIVED/"result.json",result)
        print(json.dumps({k:result[k]for k in ("status","run","new_via_count")}),flush=True)
    except BaseException as e:
        save(DERIVED/"failure.json",dict(error=repr(e),traceback=traceback.format_exc(),full_phy_accepted=False));raise
def publish():
    ctx=gate();rel=reservation();files={str(p.relative_to(OUT)):p for p in OUT.rglob("*")if p.is_file()}
    need(files and all(not p.is_symlink()for p in files.values()),"owned complete result")
    pub=ROOT/"clock-access-publication";pub.mkdir()
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
