#!/usr/bin/env python3
"""Generate actual same-net low-resistance upper-metal clock interconnect."""
import hashlib,json,math,os,subprocess,sys,tarfile,time,traceback
from pathlib import Path,PurePosixPath
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"cloud-clock-metal";NATIVE=OUT/"native";DERIVED=OUT/"derived"
CFG="scripts/cdr-clock-direct-metal-inputs.json"
METHOD="scripts/cdr-clock-direct-metal-methods.json"
BRANCH="codex/cdr-clock-direct-metal"
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
    ctx=gate();tag="cloud-results-"+str(ctx["run"])+"-1-cdr-clock-direct-metal"
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

def stack_geometry(db,x,y):
    def rect(dx,dy):return db.Region(db.Box(x-dx,y-dy,x+dx,y+dy))
    result={30:rect(625,385),50:rect(625,385),67:rect(730,730),126:rect(1050,1050)}
    for layer in (49,66):
        result[layer]=db.Region()
        for dx in (-480,0,480):
            for dy in (-240,240):result[layer].insert(db.Box(x+dx-95,y+dy-95,x+dx+95,y+dy+95))
    result[125]=db.Region()
    for dx in (-420,420):
        for dy in (-420,420):result[125].insert(db.Box(x+dx-210,y+dy-210,x+dx+210,y+dy+210))
    return result

def check_stack(db,stack,rules):
    needed={30,49,50,66,67,125,126}
    need(set(stack)==needed,"all seven actual stack layers")
    for r in stack.values():
        for p in r.each():
            need(p.holes()==0 and all(q.x%5==q.y%5==0 for q in p.each_point_hull()),"stack5nm geometry")
    for lower,via,upper,cut,count,low,high in ((30,49,50,190,6,50,50),(50,66,67,190,6,50,50),(67,125,126,420,4,100,420)):
        r=stack[via]
        need(r.count()==count and all(p.bbox().width()==p.bbox().height()==cut and p.area()==cut*cut for p in r.each()),"exact square cut census")
        spacing=220 if via!=125 else 420
        need(r.space_check(spacing).is_empty(),"actual intra-array via spacing")
        need((r.sized(low,low,2)-stack[lower]).is_empty()and(r.sized(high,high,2)-stack[upper]).is_empty(),"both stack metal enclosures")
    for n in (30,50,67,126):
        need(stack[n].width_check(1640 if n==126 else 200).is_empty(),"actual stack minimum width")
    need(rules['Vn_a']==.19 and rules['Vn_b']==.22 and rules['Vn_c']<=.05 and rules['Mn_c']<=.05,"pinned normal via rules")
    need(rules['TV1_a']==.42 and rules['TV1_b']==.42 and rules['TV1_c']==.1 and rules['TV1_d']==.42,"pinned top via rules")
    need(rules['TM1_a']==rules['TM1_b']==1.64 and rules['Mn_f']==.6,"pinned metal width and spacing")

def rectilinear(db,points,half=2000):
    need(len(points)>=2,"route endpoints")
    region=db.Region()
    for (x,y),(u,v) in zip(points,points[1:]):
        need(x==u or y==v,"Manhattan path")
        region.insert(db.Box(min(x,u)-half,min(y,v)-half,max(x,u)+half,max(y,v)+half))
    return region.merged()

def admissible_route(region,foreign,extent):
    return not region.is_empty()and(region&foreign.sized(1650,1650,2)).is_empty()and(region-extent).is_empty()

def route_link(db,start,end,foreign,extent):
    # Full geometry collision checks, never merely bounding-box acceptance.
    # Search direct L routes, then all one-detour routes adjacent to actual obstacles.
    sx,sy=start;tx,ty=end
    candidates=[[start,(tx,sy),end],[start,(sx,ty),end]]
    box=db.Box(min(sx,tx)-100000,min(sy,ty)-100000,max(sx,tx)+100000,max(sy,ty)+100000)
    near=foreign.interacting(db.Region(box)).merged()
    xs={sx,tx,box.left+4000,box.right-4000};ys={sy,ty,box.bottom+4000,box.top-4000}
    for p in near.each():
        for q in p.each_point_hull():
            xs.update((5*((q.x-3660)//5),5*((q.x+3664)//5)))
            ys.update((5*((q.y-3660)//5),5*((q.y+3664)//5)))
    candidates.extend([start,(x,sy),(x,ty),end]for x in sorted(xs))
    candidates.extend([start,(sx,y),(tx,y),end]for y in sorted(ys))
    candidates=sorted(candidates,key=lambda p:(sum(abs(a[0]-b[0])+abs(a[1]-b[1])for a,b in zip(p,p[1:])),len(p),p))
    tested=0
    for points in candidates:
        tested+=1;r=rectilinear(db,points)
        if admissible_route(r,foreign,extent):return r,dict(points=points,length_dbu=sum(abs(a[0]-b[0])+abs(a[1]-b[1])for a,b in zip(points,points[1:])),tested=tested,width_dbu=4000)
    return None,dict(start=start,end=end,tested=tested,reason="No collision-free direct or one-detour4um route",obstacle_bounds=[list(p.bbox().to_s().replace('(','').replace(')','').replace(';',',').split(','))for p in near.each()])

def metal_controls():
    import klayout.db as db
    rules=json.loads((ROOT/"docs/evidence/cdr-clock-metal-pdk-default.json").read_bytes())['drc_rules']
    st=stack_geometry(db,10000,10000);check_stack(db,st,rules)
    passed=["seven-layer stack actual width/cut/spacing/enclosures"]
    for label,mutate in (
        ("missing Via4",lambda s:s.__setitem__(66,db.Region())),
        ("too small TopMetal1 enclosure",lambda s:s.__setitem__(126,db.Region(db.Box(9500,9500,10500,10500)))),
        ("offgrid Via3",lambda s:s.__setitem__(49,s[49].transformed(db.Trans(1,0)))),
        ("missing M5",lambda s:s.__setitem__(67,db.Region()))):
        bad={n:db.Region(list(r.each()))for n,r in st.items()};mutate(bad)
        try:check_stack(db,bad,rules)
        except ValueError:passed.append(label+" refused")
        else:raise ValueError("stack fault missed "+label)
    extent=db.Region(db.Box(-20000,-20000,120000,120000))
    crossing=db.Region(db.Box(40000,-5000,60000,5000))
    direct=rectilinear(db,[(0,0),(100000,0)])
    need(not admissible_route(direct,crossing,extent),"cross-net shortcut refusal");passed.append("foreign crossing refused")
    near=db.Region(db.Box(10000,3000,90000,5000))
    need(not admissible_route(direct,near,extent),"sub-rule gap refusal");passed.append("foreign clearance refused")
    detour,record=route_link(db,(0,0),(100000,0),crossing,extent)
    need(detour is not None and admissible_route(detour,crossing,extent),"actual obstacle detour")
    passed.append("blocked straight path rerouted around actual obstacle")
    blocked=db.Region(db.Box(40000,-30000,60000,130000))
    fail,_=route_link(db,(0,0),(100000,0),blocked,extent)
    need(fail is None,"sealed obstacle cannot escape extent");passed.append("sealed obstacle refused")
    longwall=db.Region(db.Box(40000,-110000,60000,110000))
    wide_extent=db.Region(db.Box(-200000,-200000,200000,200000))
    around,_=route_link(db,(0,0),(100000,0),longwall,wide_extent)
    need(around is not None and admissible_route(around,longwall,wide_extent),"unclipped obstacle extent regression")
    passed.append("actual obstacle beyond search window detoured using full polygon")
    return dict(passed=passed,count=len(passed),physical_acceptance=False)

def generate_metal(db,layout,top,before,objects,owned,target_anchors):
    rules=json.loads((ROOT/"docs/evidence/cdr-clock-metal-pdk-default.json").read_bytes())['drc_rules']
    def box(r):
        b=r.bbox();return[b.left,b.bottom,b.right,b.top]
    def polygons(r):
        return[dict(hull=[[q.x,q.y]for q in p.each_point_hull()],holes=[[[q.x,q.y]for q in p.each_point_hole(i)]for i in range(p.holes())])for p in r.each()]
    layers=(30,49,50,66,67,125,126)
    extent=db.Region(top.bbox());groups={}
    for label,a in sorted(target_anchors.items()):
        groups.setdefault(a['wire_component'],[]).append((label,a))
    need(len(groups)==2 and sorted(len(v)for v in groups.values())==[4,4],"both complete four-terminal clock networks")
    total={n:db.Region()for n in layers};by_component={};proposals=[];failures=[]
    for component,terminals in sorted(groups.items()):
        own=owned(component);adds={n:db.Region()for n in layers};landings=[]
        foreign={n:(objects[n]-own[n]+total[n]).merged()for n in layers}
        for label,a in terminals:
            ax,ay=a['point_dbu'];x=5*round(ax/5)-100;y=5*round(ay/5)
            st=stack_geometry(db,x,y);check_stack(db,st,rules)
            checks={"original_M3_landing":(st[30]-own[30]).is_empty(),"all_inside_extent":all((r-extent).is_empty()for r in st.values())}
            for n,r in st.items():
                clearance=1650 if n==126 else 430 if n==125 else 300 if n in (49,66)else 610
                # Lower landing is wholly inside original owned M3; preserve its existing spacing.
                checks["foreign_layer_"+str(n)]=(r&foreign[n].sized(clearance,clearance,2)).is_empty()if n!=30 else(r&foreign[n]).is_empty()
                if n in (49,66,125):
                    checks["existing_via_separation_"+str(n)]=(r&(objects[n]+adds[n]).sized(clearance,clearance,2)).is_empty()
            record=dict(label=label,component=component,anchor=a,center_dbu=[x,y],checks=checks,stack={str(n):polygons(r)for n,r in st.items()})
            landings.append(record)
            if not all(checks.values()):failures.append(dict(kind="landing",record=record));continue
            for n,r in st.items():adds[n]+=r
        if any(not all(a['checks'].values())for a in landings):
            proposals.append(dict(component=component,landings=landings,routes=[],accepted_for_candidate=False));continue
        # Build a complete connected tree using physically routable links.
        # Preserve every refused edge; do not force a blocked shortest-Manhattan edge.
        connected={0};links=[];rejected_links=[]
        while len(connected)<len(landings):
            pairs=sorted((sum(abs(a-b)for a,b in zip(landings[i]['center_dbu'],landings[j]['center_dbu'])),i,j)for i in connected for j in range(len(landings))if j not in connected)
            for distance,i,j in pairs:
                r,record=route_link(db,tuple(landings[i]['center_dbu']),tuple(landings[j]['center_dbu']),foreign[126],extent)
                record.update(source=landings[i]['label'],sink=landings[j]['label'],component=component)
                if r is None:rejected_links.append(record);continue
                links.append(record);adds[126]+=r;connected.add(j);break
            else:
                record=dict(reason="No remaining terminal can connect without crossing actual obstacles",component=component,connected=sorted(connected),rejected_links=rejected_links)
                failures.append(dict(kind="route",record=record));links.append(record);break
        save(DERIVED/("rejected-route-links-"+str(component)+".json"),dict(rejected_links=rejected_links))
        if any('reason'in r for r in links):
            proposals.append(dict(component=component,landings=landings,routes=links,accepted_for_candidate=False));continue
        adds={n:r.merged()for n,r in adds.items()}
        need(adds[126].count()==1,"all four new landings connected by actual single TM1 polygon")
        need(admissible_route(adds[126],foreign[126],extent),"whole TM1 same-net geometry clearance")
        need(adds[126].width_check(1640).is_empty(),"whole routed TM1 min width")
        by_component[component]=adds
        for n,r in adds.items():total[n]+=r
        proposals.append(dict(component=component,landings=landings,routes=links,accepted_for_candidate=True,added_layer_areas_dbu2={str(n):(r-before.get((n,0),db.Region())).area()for n,r in adds.items()}))
    save(DERIVED/"metal-route-proposal.json",dict(proposals=proposals,failures=failures,physical_acceptance=False,route_width_dbu=4000,pdk_commit="5e6d592e4002946a4616f798c357f0f3c06cf3b6"))
    need(not failures and len(by_component)==2,"all eight landings and both complete metal networks required")
    for n,r in total.items():
        for p in r.each():top.shapes(layout.layer(n,0)).insert(p)
    target=NATIVE/"candidate-clock-metal.gds";layout.write(str(target))
    read=db.Layout();read.read(str(target));rt=read.cell(TOP)
    after={(read.get_info(li).layer,read.get_info(li).datatype):db.Region(rt.begin_shapes_rec(li)).merged()for li in read.layer_indexes()}
    need(read.dbu==layout.dbu and rt is not None,"serialized DBU/top")
    for k in set(before)|set(after):
        expected=before.get(k,db.Region())
        if k[1]==0 and k[0]in total:expected=(expected+total[k[0]]).merged()
        need((expected^after.get(k,db.Region())).is_empty(),"exact additive seven-layer serialized delta")
        need((before.get(k,db.Region())-after.get(k,db.Region())).is_empty(),"no original geometry removed")
    save(DERIVED/"metal-additions.json",dict(by_component={str(c):{str(n):polygons(r)for n,r in v.items()}for c,v in by_component.items()},all_other_layers_unchanged=True))
    return dict(candidate=pin(target),status="GENERATED_DIRECT_CLOCK_TOPMETAL1_REQUIRES_FULL_DRC_LVS_AND_FRESH_RC",landings=8,networks=2,
      new_vias=dict(Via3=48,Via4=48,TopVia1=32),route_width_dbu=4000,physical_acceptance=False,electrical_improvement_proven=False,fresh_RC=False,full_phy_accepted=False,final_timing_complete=False)

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
    need(len(exported)==26218 and all(len(r)==4 for r in exported),"all26218 actual wire resistors")
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

    result=generate_metal(db,layout,top,before,objects,owned,target_anchors)
    result.update(run=int(os.environ['GITHUB_RUN_ID']),source=os.environ['GITHUB_SHA'],original_gds=pin(gp),original_wire_l2n=pin(wp))
    for n,p in paths.items():need(pin(p)==json.loads((ROOT/CFG).read_bytes())['index']['files'][n],'original authenticated input unchanged')
    return result

def execute():
    ctx=gate();OUT.mkdir();NATIVE.mkdir();DERIVED.mkdir()
    save(DERIVED/"context.json",ctx);save(DERIVED/"controls.json",dict(network=controls(),metal=metal_controls()));save(DERIVED/"reservation.json",reservation(True))
    try:
        paths=acquire(json.loads((ROOT/CFG).read_bytes()));result=inspect(paths)
        gate();save(DERIVED/"result.json",result)
        print(json.dumps({k:result[k]for k in ("status","run","landings","networks")}),flush=True)
    except BaseException as e:
        save(DERIVED/"failure.json",dict(error=repr(e),traceback=traceback.format_exc(),full_phy_accepted=False));raise
def publish():
    ctx=gate();rel=reservation();files={str(p.relative_to(OUT)):p for p in OUT.rglob("*")if p.is_file()}
    need(files and all(not p.is_symlink()for p in files.values()),"owned complete result")
    pub=ROOT/"clock-metal-publication";pub.mkdir()
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
