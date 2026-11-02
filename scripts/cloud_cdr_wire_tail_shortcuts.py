#!/usr/bin/env python3
"""Generate four physical clock-selector shortcuts from measured same-net voltage loss."""
import ast,hashlib,importlib.metadata,json,os,re,subprocess,sys,tarfile,traceback
from pathlib import Path
import klayout.db as pya
import cloud_cdr_wire_geometry_acquire as prior
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"wire-tail-shortcuts";NATIVE=ROOT/"wire-tail-shortcuts-native"
MANIFEST="scripts/cdr-wire-tail-shortcuts-pins.json";INPUT="scripts/cdr-wire-tail-shortcuts-inputs.json"
BRANCH="codex/cdr-drain-m23-critical-access";TOP="nssoc_cdr_pd500_resistor_v59"
LAYERS=(8,19,10,29)
TARGETS=(("D_collector","T061_C","T056_E"),("D_emitter","T061_E","T005_D"),("C_collector","T115_C","T108_E"),("C_emitter","T115_E","T034_D"))
need=prior.need
def encode(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def pin(p):return dict(bytes=p.stat().st_size,sha256=prior.digest(p))
def save(n,v):
    p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("xb")as f:f.write(encode(v))
def gate():
    e=os.environ
    need(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted","hosted only")
    need(e["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"and e["GITHUB_REF"]=="refs/heads/"+BRANCH,"repository branch")
    need(e["GITHUB_EVENT_NAME"]=="workflow_dispatch"and e["GITHUB_RUN_ATTEMPT"]=="1","first dispatch")
    need(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==e["GITHUB_SHA"],"source")
    need(importlib.metadata.version("klayout")=="0.30.4.post1","KLayout runtime")
    m=json.loads((ROOT/MANIFEST).read_bytes())
    for n,p in m["files"].items():need(pin(ROOT/n)==p and not(ROOT/n).is_symlink(),"source "+n)
    reference=ast.parse((ROOT/"scripts/cloud_cdr_wire_shortcuts.py").read_text())
    candidate=ast.parse(Path(__file__).read_text())
    for name in ("box","bounds","conductor_guard","wire","reuse_access","access","controls","region_snapshot"):
        a=next(n for n in reference.body if isinstance(n,ast.FunctionDef)and n.name==name)
        b=next(n for n in candidate.body if isinstance(n,ast.FunctionDef)and n.name==name)
        need(ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False),"unchanged original geometry guard "+name)
    prior.OUT=OUT
    cfg=json.loads((ROOT/INPUT).read_bytes())
    for n in("binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds","binding/inputs/wire/native05/wires.l2n","binding/inputs/wire/native05/wires.gds"):
        need(n in cfg["complete_members"],"selected native geometry in authenticated inventory: "+n)
    return cfg
def box(x,y,half):return pya.Region(pya.Box(x-half,y-half,x+half,y+half))
def bounds(region):
    b=region.bbox();return [b.left,b.bottom,b.right,b.top]if not region.is_empty()else None
def conductor_guard(metal,cuts,owned,full,other):
    tests={
      "lower_via_enclosure":(cuts.sized(50)-owned[8]).is_empty(),
      "upper_via_enclosure":(cuts.sized(50)-metal).is_empty(),
      "via_existing_clearance":cuts.sized(295).interacting(full[19]).is_empty(),
      "foreign_lower_metal":cuts.sized(5).interacting(full[8]-owned[8]).is_empty(),
      "foreign_m2_clearance":metal.sized(605).interacting(full[10]-owned[10]).is_empty(),
      "foreign_via1":metal.sized(5).interacting(full[19]-owned[19]).is_empty(),
      "foreign_via2":metal.sized(5).interacting(full[29]-owned[29]).is_empty(),
      "no_unclassified_m2_or_via_drawing":all((metal.sized(605)if layer==10 else cuts.sized(295)).interacting(reg).is_empty()for(layer,dt),reg in other.items()),
      "new_m2_material":not(metal-full[10]).is_empty()}
    return tests
def wire(points,width=600):
    r=pya.Region()
    for (x,y),(xx,yy)in zip(points,points[1:]):
        need(x==xx or y==yy,"Manhattan segment")
        r.insert(pya.Box(min(x,xx)-width//2,min(y,yy)-width//2,max(x,xx)+width//2,max(y,yy)+width//2))
    return r.merged()
def reuse_access(anchor,owned,full,other):
    x,y=anchor["point_dbu"];touch=box(x,y,1)
    landing=owned[10].interacting(touch).merged()
    if landing.is_empty()or not(touch-owned[8]).is_empty():return None
    cuts=owned[19].interacting(landing).merged()
    if cuts.count()<2:return None
    records=[]
    for poly in cuts.each():
        rect=poly.bbox();cut=pya.Region(poly)
        if rect.width()!=190 or rect.height()!=190 or poly.area()!=190*190:return None
        if not(cut.sized(50)-owned[8]).is_empty()or not(cut.sized(50)-landing).is_empty():return None
        records.append([rect.left,rect.bottom,rect.right,rect.top])
    tests=conductor_guard(landing,pya.Region(),owned,full,other)
    if not all(v for k,v in tests.items()if k!="new_m2_material"):return None
    # Existing cuts are not added or exempted: no new via geometry is generated.
    # Their exact same-net M1/M2 enclosure is established above.
    return dict(cuts=pya.Region(),pad=landing,center=[x,y]),dict(
      reason=None,reused_existing_stack=True,reused_via1_boxes_dbu=records,
      reused_via1_count=len(records),new_via1_count=0,landing_bbox=bounds(landing),
      anchor_point_dbu=[x,y],admitted_sites=[[x,y]],attempted_sites=[],array_trials=[],
      original_m1_m2_and_via1_ownership_checked=True,original_lower_upper_enclosures_checked=True,
      guards=tests)

def access(anchor,owned,full,other):
    x,y=anchor["point_dbu"];need(anchor["metal"]==8 and x%5==0 and y%5==0,"M1 anchor on original grid")
    reused=reuse_access(anchor,owned,full,other)
    if reused is not None:return reused
    cache={};array_trials=[]
    def site(point):
        key=tuple(point)
        if key not in cache:
            xx,yy=point;cut=box(xx,yy,95);landing=box(xx,yy,300)
            tests=conductor_guard(landing,cut,owned,full,other)
            cache[key]=dict(point=list(point),guards=tests,admitted=all(v for k,v in tests.items()if k!="new_m2_material"))
        return cache[key]
    seeds=[[x,y]]
    for delta in range(500,10001,500):
        seeds.extend([[x,y-delta],[x,y+delta],[x-delta,y],[x+delta,y]])
    def report(reason=None,points=None,pad=None):
        value=dict(attempted_sites=list(cache.values()),array_trials=array_trials,
          clipped_local_owned_layer_boxes={str(n):[bounds(pya.Region(poly))for poly in(owned[n]&box(x,y,12000)).merged().each()]for n in LAYERS},
          search_radius_dbu=10000,anchor_point_dbu=[x,y],reason=reason,admitted_sites=points or[])
        if points:value.update(cut_count=len(points),landing_bbox=bounds(pad))
        return value
    for seed in seeds:
        if not site(seed)["admitted"]:continue
        sx,sy=seed;candidates=[]
        for dx,dy in[(0,0),(0,-500),(0,500),(-500,0),(500,0),(0,-1000),(0,1000),(-1000,0),(1000,0)]:
            point=[sx+dx,sy+dy]
            if max(abs(point[0]-x),abs(point[1]-y))>10000:continue
            if site(point)["admitted"]:
                cut=box(*point,95)
                if all(cut.sized(295).interacting(c["cut"]).is_empty()for c in candidates):candidates.append(dict(point=point,cut=cut))
            if len(candidates)==4:break
        if len(candidates)<2:continue
        points=[c["point"]for c in candidates];cuts=pya.Region()
        for c in candidates:cuts+=c["cut"]
        xs=[p[0]for p in points];ys=[p[1]for p in points]
        pad=pya.Region(pya.Box(min(xs)-300,min(ys)-300,max(xs)+300,max(ys)+300))
        tests=conductor_guard(pad,cuts,owned,full,other)
        array_trials.append(dict(seed=seed,points=points,tests=tests))
        if all(v for k,v in tests.items()if k!="new_m2_material"):
            return dict(cuts=cuts,pad=pad,center=seed),report(points=points,pad=pad)
    return None,report(reason="no guarded two-to-four-via array in bounded actual same-net M1 search")

def controls():
    passed=prior.controls()+prior.coordinate_controls()
    empty={n:pya.Region()for n in LAYERS}
    own={n:pya.Region()for n in LAYERS};own[8]=box(0,0,2000)
    cut=box(0,0,95);metal=box(0,0,300)
    full={n:r.dup()for n,r in own.items()}
    t=conductor_guard(metal,cut,own,full,{})
    need(all(t.values()),"valid isolated guarded stack");passed.append("guard isolated legal stack")
    for name,layer,shape,key in[
      ("foreign M2",10,box(500,0,100),"foreign_m2_clearance"),
      ("foreign Via1",19,box(0,0,95),"foreign_via1"),
      ("foreign Via2",29,box(0,0,95),"foreign_via2")]:
        bad={n:r.dup()for n,r in full.items()};bad[layer]+=shape
        need(not conductor_guard(metal,cut,own,bad,{})[key],name);passed.append("reject "+name)
    small={n:r.dup()for n,r in own.items()};small[8]=box(0,0,100)
    need(not conductor_guard(metal,cut,small,full,{})["lower_via_enclosure"],"lower enclosure");passed.append("reject lower enclosure")
    need(not conductor_guard(box(0,0,100),cut,own,full,{})["upper_via_enclosure"],"upper enclosure");passed.append("reject upper enclosure")
    need(not conductor_guard(metal,cut,own,full,{(10,24):box(0,0,50)})["no_unclassified_m2_or_via_drawing"],"unclassified mask");passed.append("reject unclassified mask")
    r=wire([[0,0],[1000,0],[1000,1000]])
    need(r.count()==1 and (box(0,0,300)-r).is_empty()and(box(1000,1000,300)-r).is_empty(),"Manhattan connected endpoints");passed.append("Manhattan endpoints connected")
    synthetic=dict(point_dbu=[0,0],metal=8)
    access_row,details=access(synthetic,own,full,{})
    need(access_row is not None and len(details["admitted_sites"])>=2 and(box(*access_row["center"],1)-access_row["pad"]).is_empty(),"bounded access with connected route landing");passed.append("bounded original metal access and route landing")
    blocked={n:r.dup()for n,r in full.items()};blocked[10]=box(0,0,20000)
    access_row,details=access(synthetic,own,blocked,{})
    need(access_row is None and details["attempted_sites"]and all(not x["admitted"]for x in details["attempted_sites"]),"full access blockers retained");passed.append("all rejected access guards retained")
    stacked={n:pya.Region()for n in LAYERS}
    stacked[8]=pya.Region(pya.Box(-1000,-150,1000,150));stacked[10]=pya.Region(pya.Box(-1000,-145,1000,145))
    for xx in(-720,-240,240,720):stacked[19]+=box(xx,0,95)
    got=reuse_access(synthetic,stacked,stacked,{})
    need(got is not None and got[0]["cuts"].is_empty()and got[1]["reused_via1_count"]==4,"real stack reused without duplicate cuts");passed.append("reuse four enclosed same-net vias without new cuts")
    bad={n:r.dup()for n,r in stacked.items()};bad[8]=pya.Region()
    need(reuse_access(synthetic,bad,stacked,{})is None,"reject unowned lower metal");passed.append("reject reused stack without lower same-net metal")
    need(len(passed)==31,"19 unchanged plus12 geometry controls");return passed


def refined_m1_access(anchor,owned,full,other):
    x,y=anchor["point_dbu"]
    need(anchor["metal"]==8 and (box(x,y,1)-owned[8]).is_empty(),"actual M1 reference belongs to extracted net")
    # Erode the ORIGINAL same-net metal by the exact 95nm cut half-width
    # plus 50nm lower enclosure. This proposes centres, not new M1 geometry.
    centres=(owned[8].sized(-145)&box(x,y,10000)).merged()
    seeds=set()
    for poly in centres.each():
        b=poly.bbox()
        for xx in(b.left+1,(b.left+b.right)//2,b.right-1):
            for yy in(b.bottom+1,(b.bottom+b.top)//2,b.top-1):
                for px in(xx//5*5,(xx//5+1)*5):
                    for py in(yy//5*5,(yy//5+1)*5):
                        if (box(px,py,1)-centres).is_empty():seeds.add((px,py))
    ordered=sorted(seeds,key=lambda p:((p[0]-x)**2+(p[1]-y)**2,p))[:24]
    attempts=[]
    for point in ordered:
        search_anchor=dict(anchor,point_dbu=list(point))
        got,report=access(search_anchor,owned,full,other)
        attempts.append(dict(search_center=list(point),report=report))
        if got is not None:
            return got,dict(reason=None,original_anchor_point_dbu=[x,y],anchor_reference_not_moved=True,search_seed_only=True,
                geometric_m1_refinement=True,lower_enclosure_erosion_dbu=145,
                candidate_centres=len(seeds),attempted_refinements=attempts,
                admitted_sites=report["admitted_sites"],landing_bbox=report["landing_bbox"])
    return None,dict(reason="no legal original-guard access after exact M1 enclosure refinement",original_anchor_point_dbu=[x,y],anchor_reference_not_moved=True,candidate_centres=len(seeds),attempted_refinements=attempts,admitted_sites=[])
def refined_m1_controls():
    own={n:pya.Region()for n in LAYERS}
    own[8]=pya.Region(pya.Box(-3000,-130,3000,170))
    a=dict(metal=8,point_dbu=[0,0]);before=encode(a)
    got,_=access(a,own,own,{})
    need(got is None,"coarse original seeds cannot enclose the offset narrow strip")
    got,report=refined_m1_access(a,own,own,{})
    need(got is not None and len(report["admitted_sites"])>=2,"exact original metal permits refined via array")
    need(encode(a)==before and report["anchor_reference_not_moved"],"original reference and metal not moved")
    checks=["refine offset narrow M1 strip with unchanged original guards","original M1 reference unchanged"]
    narrow={n:r.dup()for n,r in own.items()};narrow[8]=box(0,0,100)
    got,report=refined_m1_access(a,narrow,narrow,{})
    need(got is None and report["candidate_centres"]==0,"reject metal too narrow for original enclosure");checks.append("reject insufficient real M1 enclosure")
    full={n:r.dup()for n,r in own.items()};full[10]=box(0,0,20000)
    got,report=refined_m1_access(a,own,full,{})
    need(got is None,"refinement cannot bypass foreign M2 guard");checks.append("refined sites still reject foreign M2")
    return checks

def terminal_access(anchor,owned,full,other):
    if anchor["metal"]==8:
        got,report=access(anchor,owned,full,other)
        if got is not None:return got,report
        new,refinement=refined_m1_access(anchor,owned,full,other)
        refinement["original_bounded_search"]=report
        return new,refinement
    need(anchor["metal"]==10,"supported actual terminal metal M1 or M2")
    x,y=anchor["point_dbu"];touch=box(x,y,1)
    need((touch-owned[10]).is_empty(),"actual M2 terminal reference lies in its extracted own net")
    # The reference point can be a sub-grid polygon midpoint. Only the new
    # route centre is chosen on 5nm grid; no original polygon/anchor is moved.
    seeds=[]
    for xx in (x//5*5,(x//5+1)*5):
        for yy in(y//5*5,(y//5+1)*5):
            seeds.append([xx,yy])
    start=list(seeds)
    for delta in range(500,10001,500):
        for xx,yy in start:seeds.extend([[xx,yy-delta],[xx,yy+delta],[xx-delta,yy],[xx+delta,yy]])
    attempts=[];seen=set()
    for point in seeds:
        if tuple(point)in seen:continue
        seen.add(tuple(point));xx,yy=point;pad=box(xx,yy,300)
        tests=conductor_guard(pad,pya.Region(),owned,full,other)
        tests["grid5_new_route_center"]=xx%5==0 and yy%5==0
        tests["new_center_within_existing_same_net_M2"]=(box(xx,yy,1)-owned[10]).is_empty()
        admitted=all(v for k,v in tests.items()if k!="new_m2_material")
        attempts.append(dict(point=point,guards=tests,admitted=admitted))
        if admitted:
            return dict(cuts=pya.Region(),pad=pad,center=point),dict(reason=None,direct_existing_m2=True,new_via1_count=0,anchor_point_dbu=[x,y],anchor_reference_not_moved=True,admitted_sites=[point],attempted_sites=attempts,landing_bbox=bounds(pad),guards=tests)
    return None,dict(reason="no guarded direct M2 access on existing same-net metal within 10um",anchor_point_dbu=[x,y],anchor_reference_not_moved=True,attempted_sites=attempts,admitted_sites=[],clipped_owned_m2_bbox=bounds(owned[10]&box(x,y,12000)))
def direct_m2_controls():
    passed=[]
    own={n:pya.Region()for n in LAYERS};own[10]=box(0,0,2000)
    a=dict(metal=10,point_dbu=[0,2]);before=encode(a)
    got,report=terminal_access(a,own,own,{})
    need(got is not None and got["cuts"].is_empty()and got["center"][0]%5==0 and got["center"][1]%5==0,"direct M2 sub-grid reference to grid route")
    need(encode(a)==before and report["anchor_reference_not_moved"],"original reference unchanged")
    passed+=["direct owned M2 access without vias","sub-grid reference unchanged and new route grid"]
    missing={n:pya.Region()for n in LAYERS}
    try:terminal_access(a,missing,own,{})
    except AssertionError:passed.append("reject unowned M2 reference")
    else:raise AssertionError("unowned M2 accepted")
    for label,layer in[("foreign M2",10),("foreign Via1",19),("foreign Via2",29)]:
        full={n:r.dup()for n,r in own.items()};full[layer]+=box(0,0,20000)
        # The M2 foreign test uses the shell around the owned metal. Its
        # 605nm expansion blocks every 600nm landing near the 4um own pad edge,
        # while interior pads are covered by foreign via controls separately.
        if layer==10:full[layer]=box(0,0,20000);small={n:r.dup()for n,r in own.items()};small[10]=box(0,0,100)
        else:small=own
        got,report=terminal_access(a,small,full,{})
        need(got is None and report["attempted_sites"],"reject blocked direct "+label);passed.append("reject direct "+label)
    try:terminal_access(dict(metal=30,point_dbu=[0,0]),own,own,{})
    except AssertionError:passed.append("reject unsupported terminal metal")
    else:raise AssertionError("unknown metal accepted")
    need(len(passed)==7,"seven direct M2 controls")
    return passed

def region_snapshot(layout,top):
    return {(layout.get_info(li).layer,layout.get_info(li).datatype):pya.Region(top.begin_shapes_rec(li)).merged()for li in layout.layer_indexes()}
def generate(base,cfg):
    gpath=base/"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds"
    wpath=base/"binding/inputs/wire/native05/wires.l2n"
    g=pya.Layout();g.read(str(gpath));need(g.dbu==.001,"original GDS DBU")
    top=g.cell(TOP);need(top is not None,"original top")
    before=region_snapshot(g,top)
    w=pya.LayoutToNetlist();w.read(str(wpath))
    need(w.internal_layout().dbu==.001,"wire L2N DBU")
    nets={n.cluster_id:n for n in w.netlist().top_circuit().each_net()}
    objects={n:w.layer_by_name("gds_"+str(n))for n in LAYERS}
    need(all(r is not None for r in objects.values()),"all required wire layers")
    full={n:before.get((n,0),pya.Region())for n in LAYERS}
    for n in LAYERS:need((full[n]^objects[n]).is_empty(),"GDS/L2N full layer union "+str(n))
    other={k:r for k,r in before.items()if k[0]in(10,19)and k[1]!=0 and not r.is_empty()}
    anchors=json.loads((base/"binding/inputs/wire/anchors08.json").read_bytes())
    physical={a["label"]:a for a in anchors["anchors"]}
    proposals=[];inserted=[];additions={n:pya.Region()for n in(10,19)}
    for label,source_label,sink_label in TARGETS:
        a=physical[source_label];b=physical[sink_label]
        verify_target(base,source_label,a,sink_label,b)
        need(a["wire_component"]==b["wire_component"]and a["native_cluster"]==b["native_cluster"],"same native conductor")
        component=a["wire_component"];need(component in nets,"actual L2N component")
        owned={n:w.shapes_of_net(nets[component],objects[n],True).merged()for n in LAYERS}
        current={n:(full[n]+additions.get(n,pya.Region())).merged()for n in LAYERS}
        save("target-input-"+label+".json",dict(source_anchor=a,sink_anchor=b,component=component))
        aa,ar=terminal_access(a,owned,current,other);bb,br=terminal_access(b,owned,current,other)
        result=dict(label=label,source_anchor=a,sink_anchor=b,component=component,source_access=ar,sink_access=br,candidates=[],selected=None)
        if aa is not None and bb is not None:
            x,y=aa["center"];xx,yy=bb["center"]
            routes=[[[x,y],[xx,y],[xx,yy]],[[x,y],[x,yy],[xx,yy]]]
            # Bounded explicit horizontal detours; preserve every rejected guard.
            for delta in(-2000,2000,-5000,5000,-10000,10000):
                for yroute in (y+delta,yy+delta):routes.append([[x,y],[x,yroute],[xx,yroute],[xx,yy]])
            for points in routes:
                metal=(wire(points)+aa["pad"]+bb["pad"]).merged();cuts=(aa["cuts"]+bb["cuts"]).merged()
                tests=conductor_guard(metal,cuts,owned,current,other)
                tests["two_distinct_access_arrays"]=aa["cuts"].sized(295).interacting(bb["cuts"]).is_empty()
                tests["single_continuous_new_m2"]=metal.count()==1
                tests["new_route_within_existing_die_bbox"]=(metal-pya.Region(top.bbox())).is_empty()
                row=dict(points_dbu=points,guards=tests,metal_bbox=bounds(metal),cut_bbox=bounds(cuts))
                result["candidates"].append(row)
                if all(tests.values()):
                    result["selected"]=row
                    for n,region in ((10,metal),(19,cuts)):
                        for poly in region.each():
                            shape=top.shapes(g.layer(n,0)).insert(poly);inserted.append(shape)
                        additions[n]+=region
                    result["added_material_dbu2"]={str(n):(r-full[n]).area()for n,r in((10,metal),(19,cuts))}
                    break
        proposals.append(result);save("target-"+label+".json",result)
    adopted=[p["label"]for p in proposals if p["selected"]is not None]
    save("generation-summary.json",dict(source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),input_gds=pin(gpath),input_l2n=pin(wpath),
      targets=len(TARGETS),generated_targets=adopted,unrouted_targets=[p["label"]for p in proposals if p["selected"]is None],
      existing_m1_and_devices_unchanged=True,metal2_width_dbu=600,via1_size_dbu=190,
      physical_acceptance=False,fresh_RC=False,DRC=False,LVS=False,full_phy_accepted=False))
    need(adopted,"no legal candidate under conservative guards; preserve blockers")
    NATIVE.mkdir();candidate=NATIVE/"nssoc_cdr_pd500_wire_tail_shortcuts.gds";g.write(str(candidate))
    loaded=pya.Layout();loaded.read(str(candidate));after=region_snapshot(loaded,loaded.cell(TOP))
    need(loaded.dbu==g.dbu and {c.name for c in loaded.each_cell()}=={c.name for c in g.each_cell()},"serialized hierarchy cell set")
    for layer in set(before)|set(after):
        expected=before.get(layer,pya.Region())
        if layer in((10,0),(19,0)):expected=(expected+additions[layer[0]]).merged()
        need((expected^after.get(layer,pya.Region())).is_empty(),"exact serialized geometry delta "+str(layer))
    for shape in reversed(inserted):shape.delete()
    reverted=region_snapshot(g,top)
    need(set(before)==set(reverted),"reversed layer inventory")
    for layer in before:need((before[layer]^reverted[layer]).is_empty(),"exact reversible material "+str(layer))
    need(pin(gpath)==cfg["complete_members"]["binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds"],"original GDS unchanged")
    save("generation-proof.json",dict(candidate=pin(candidate),generated_targets=adopted,exact_serialized_delta=True,original_material_roundtrip=True,
      scope="Physical interconnect candidate only. Requires native DRC/LVS, fresh RC and unchanged loaded-wave/device gates.",
      original_devices_unchanged=True,physical_acceptance=False,full_phy_accepted=False))
    need(len(adopted)==len(TARGETS),"partial physical candidate preserved; not all four paths routed")
def publish():
    cfg=gate();e=os.environ;tag="cloud-results-"+e["GITHUB_RUN_ID"]+"-1-cdr-wire-tail-shortcuts"
    release=prior.api("releases/tags/"+tag)
    need(release["target_commitish"]==e["GITHUB_SHA"]and not release["assets"],"empty exact-source reservation")
    need(prior.api("git/ref/tags/"+tag)["object"]["sha"]==e["GITHUB_SHA"],"reserved tag")
    source=OUT/"source";source.mkdir()
    for name in sorted(set(json.loads((ROOT/MANIFEST).read_bytes())["files"])|{MANIFEST}):
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/name).read_bytes())
    files={}
    for root,prefix in ((OUT,"derived"),(NATIVE,"native")):
        if root.exists():
            for p in sorted(root.rglob("*")):
                need(not p.is_symlink(),"regular output")
                if p.is_file():files[prefix+"/"+str(p.relative_to(root))]=p
    need(files,"success/failure evidence")
    pub=ROOT/"wire-tail-shortcuts-publication";pub.mkdir()
    index=dict(context=dict(run=int(e["GITHUB_RUN_ID"]),attempt=1,source=e["GITHUB_SHA"]),files={n:pin(p)for n,p in files.items()})
    (pub/"complete-output-index.json").write_bytes(encode(index))
    archive=pub/"native-candidate.tar.gz"
    with tarfile.open(archive,"w:gz")as tar:
        for n,p in files.items():tar.add(p,arcname="wire-tail-shortcuts/"+n,recursive=False)
    subprocess.run(["gh","release","upload",tag,str(pub/"complete-output-index.json"),str(archive),"--repo","Melihakbulut221/nssoc"],check=True)
    assets=prior.api("releases/"+str(release["id"]))["assets"]
    for p in (pub/"complete-output-index.json",archive):
        a=next(a for a in assets if a["name"]==p.name);need(a["size"]==p.stat().st_size and a["digest"]=="sha256:"+prior.digest(p),"published exact digest")
    save("publication.json",dict(tag=tag,release=release["id"],assets=assets,original_inputs_remain_in_release=cfg["release_id"]))

def reserve(wait=False):
    import time
    tag="cloud-results-"+os.environ["GITHUB_RUN_ID"]+"-1-cdr-wire-tail-shortcuts"
    for i in range(90 if wait else 1):
        try:r=prior.api("releases/tags/"+tag)
        except subprocess.CalledProcessError:
            if wait and i<89:time.sleep(2);continue
            raise
        need(r["target_commitish"]==os.environ["GITHUB_SHA"]and not r["assets"],"empty independently reserved current release")
        need(prior.api("git/ref/tags/"+tag)["object"]["sha"]==os.environ["GITHUB_SHA"],"exact current tag")
        return r
def acquire_current(cfg):
    p=cfg["producer"];r=prior.api("actions/runs/"+str(p["run"]));rel=prior.api("releases/"+str(p["release"]))
    need(r["status"]=="completed"and r["conclusion"]=="success"and r["head_sha"]==p["source"]and r["run_attempt"]==1,"actual successful current RC")
    need(rel["tag_name"]==p["tag"]and rel["target_commitish"]==p["source"]and prior.api("git/ref/tags/"+p["tag"])["object"]["sha"]==p["source"],"actual RC release binding")
    assets={a["name"]:a for a in rel["assets"]};need(set(assets)==set(p["assets"]),"complete current RC release")
    work=ROOT/"wire-tail-shortcuts-inputs";work.mkdir()
    for name,a in p["assets"].items():
        live=assets[name];need(live["id"]==a["id"]and live["size"]==a["bytes"]and live["digest"]=="sha256:"+a["sha256"],"current RC asset identity")
        path=work/name;need(path.parent==work,"flat asset name")
        with path.open("xb")as f:subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True,timeout=600)
        need(pin(path)=={k:a[k]for k in("bytes","sha256")},"actual full RC asset bytes")
    index=json.loads((work/"complete-output-index.json").read_bytes())
    need(index["files"]==cfg["complete_members"]and index["context"]==dict(run=p["run"],source=p["source"],attempt=1),"actual full RC index")
    selected={"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds","binding/inputs/wire/native05/wires.l2n","binding/inputs/wire/native05/wires.gds","binding/inputs/wire/anchors08.json","mim/composition/composition.json","fresh-rc-qualification.json","binding/inputs/native-planes.json","mim/precise/wire/rc03/pump_wires.ext","mim/precise/wire/rc03/pump_wires.res.ext","mim/precise/wire/rc03/wires.spice","mim/precise/wire/anchors08.json"}
    target=work/"selected";seen=set()
    with tarfile.open(work/"native-fresh-rc.tar.gz","r|gz")as tar:
        for m in tar:
            n=prior.relative(m.name,p["archive_root"])
            need(m.isfile()and n in index["files"]and n not in seen,"unique actual regular member")
            expected=index["files"][n];need(m.size==expected["bytes"],"member size")
            h=hashlib.sha256();size=0;out=None
            if n in selected:
                path=target/n;path.parent.mkdir(parents=True,exist_ok=True);out=path.open("xb")
            try:
                with tar.extractfile(m)as f:
                    while b:=f.read(1024*1024):
                        size+=len(b);h.update(b)
                        if out is not None:out.write(b)
            finally:
                if out is not None:out.close()
            need(dict(bytes=size,sha256=h.hexdigest())==expected,"member digest "+n);seen.add(n)
    need(seen==set(index["files"])and selected<=seen,"all current RC members authenticated")
    q=json.loads((target/"fresh-rc-qualification.json").read_bytes())
    need(q["status"]=="PASS_DRAIN_M23_FRESH_RC_NUMERICAL_QUALIFICATION_REQUIRES_LOADED_WAVES"and q["fresh_RC_executed"],"actual current RC qualification")
    need(pin(target/"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds")==dict(bytes=1075316,sha256="5e5ef3940bb0e410af8bbb92376e2c1cb60e3c520e37b65c7e675af41e58603f"),"actual current four-path GDS baseline")
    save("acquisition.json",dict(run=r,release=rel,authenticated_members=len(seen),selected=sorted(selected),all_current_members_authenticated=True,native_payloads_cloud_only=True))
    return target
def verify_target(base,source_label,a,sink_label,b):
    comp=json.loads((base/"mim/composition/composition.json").read_bytes())
    records={int(d["native_id"]):d for d in comp["device_records"]}
    terms=[]
    for label,anchor in[(source_label,a),(sink_label,b)]:
        match=re.fullmatch(r"T(\d+)_(C|E|D)",label);need(match is not None,"explicit transistor terminal")
        record=records[int(match[1])]
        term=next(t for t in record["terminals"]if t["terminal"]==match[2])
        need(record["model"]in("npn13g2","sg13_lv_nmos"),"actual transistor origin")
        need(term["native_cluster"]==anchor["native_cluster"],"actual model and geometry terminal cluster")
        terms.append(term)
    need(terms[0]["native_net"]==terms[1]["native_net"]and terms[0]["native_cluster"]==terms[1]["native_cluster"],"same native conductor before adding metal")


def inspect_access(base,cfg):
    gpath=base/"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds"
    wpath=base/"binding/inputs/wire/native05/wires.l2n"
    g=pya.Layout();g.read(str(gpath));top=g.cell(TOP)
    need(top is not None and g.dbu==.001,"original physical layout")
    before=region_snapshot(g,top)
    w=pya.LayoutToNetlist();w.read(str(wpath));need(w.internal_layout().dbu==.001,"original wire DBU")
    layers=(8,19,10,29,30,49)
    objects={n:w.layer_by_name("gds_"+str(n))for n in layers}
    available={n:r is not None for n,r in objects.items()}
    save("access-layer-inventory.json",dict(native_layers=available,gds_nonempty_layers=[list(k)for k,r in before.items()if not r.is_empty()]))
    need(all(available.values()),"all M1/Via1/M2/Via2/M3/Via3 ownership layers required")
    full={n:before.get((n,0),pya.Region())for n in layers}
    for n in layers:need((full[n]^objects[n]).is_empty(),"exact GDS/L2N union "+str(n))
    nets={n.cluster_id:n for n in w.netlist().top_circuit().each_net()}
    physical={a["label"]:a for a in json.loads((base/"binding/inputs/wire/anchors08.json").read_bytes())["anchors"]}
    for label,aa,bb in TARGETS:verify_target(base,aa,physical[aa],bb,physical[bb])
    other_m2={k:r for k,r in before.items()if k[0]in(10,19)and k[1]!=0 and not r.is_empty()}
    other_m3={k:r for k,r in before.items()if k[0]in(30,29,49)and k[1]!=0 and not r.is_empty()}
    summary=[]
    for label in sorted({x for _,a,b in TARGETS for x in(a,b)}):
        a=physical[label];x,y=a["point_dbu"];touch=box(x,y,1);component=a["wire_component"]
        need(component in nets,"actual component")
        owned={n:w.shapes_of_net(nets[component],objects[n],True).merged()for n in layers}
        need((touch-owned[a["metal"]]).is_empty(),"original anchor belongs to exact component")
        landing=owned[10].interacting(touch).merged();cuts=owned[19].interacting(landing).merged()
        old=dict(m1_at_reference=(touch-owned[8]).is_empty(),m2_at_reference=(touch-owned[10]).is_empty(),
          full_m2_landing_bbox=bounds(landing),full_m2_landing_polygon_count=landing.count(),via1_count=cuts.count(),
          guards=conductor_guard(landing,pya.Region(),owned,full,other_m2),cut_failures=[])
        for poly in cuts.each():
            b=poly.bbox();cut=pya.Region(poly)
            checks=dict(exact_190nm=b.width()==190 and b.height()==190 and poly.area()==36100,
              lower_enclosed=(cut.sized(50)-owned[8]).is_empty(),upper_enclosed=(cut.sized(50)-landing).is_empty())
            if not all(checks.values()):old["cut_failures"].append(dict(box=bounds(cut),checks=checks))
        local={}
        for lower,via,upper in[(8,19,10),(10,29,30)]:
            records=[]
            for poly in owned[via].interacting(box(x,y,10000)).each():
                b=poly.bbox();cut=pya.Region(poly)
                records.append(dict(box=bounds(cut),center=[(b.left+b.right)//2,(b.bottom+b.top)//2],
                  exact_190nm=b.width()==190 and b.height()==190 and poly.area()==36100,
                  lower_enclosed=(cut.sized(50)-owned[lower]).is_empty(),
                  upper_enclosed=(cut.sized(50)-owned[upper]).is_empty()))
            local[str(via)]=records
        m3=[]
        for row in local["29"]:
            xx,yy=row["center"];pad=box(xx,yy,300)
            checks=dict(existing_via_exact=row["exact_190nm"],existing_via_lower_enclosed=row["lower_enclosed"],
              existing_via_upper_enclosed=row["upper_enclosed"],grid5=xx%5==0 and yy%5==0,
              route_center_owned_m3=(box(xx,yy,1)-owned[30]).is_empty(),
              foreign_m3_clearance=pad.sized(605).interacting(full[30]-owned[30]).is_empty(),
              foreign_via2=pad.sized(5).interacting(full[29]-owned[29]).is_empty(),
              foreign_via3=pad.sized(5).interacting(full[49]-owned[49]).is_empty(),
              no_unclassified_drawing=all(pad.sized(605 if layer==30 else 5).interacting(r).is_empty()for(layer,dt),r in other_m3.items()))
            m3.append(dict(center=[xx,yy],pad_bbox=bounds(pad),checks=checks,admitted=all(checks.values())))
        result=dict(anchor=a,component=component,original_m2_reuse=old,local_vias=local,m3_landing_candidates=m3,
          original_geometry_unchanged=True,physical_acceptance=False,full_phy_accepted=False)
        save("access-stack-"+label+".json",result)
        summary.append(dict(label=label,old_m2_guard_failures=[k for k,v in old["guards"].items()if not v and k!="new_m2_material"],
          old_stack_cut_failures=len(old["cut_failures"]),local_via1=len(local["19"]),local_via2=len(local["29"]),
          guarded_m3_landings=sum(r["admitted"]for r in m3)))
    need(pin(gpath)==cfg["complete_members"]["binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds"],"read-only original GDS")
    save("access-stack-summary.json",dict(terminals=summary,input_gds=pin(gpath),input_l2n=pin(wpath),native_geometry_unchanged=True,
      new_geometry_generated=False,physical_acceptance=False,full_phy_accepted=False))


def mixed_m3_guard(metal,cuts,lower,owned,full,other):
    return dict(
      lower_via2_enclosure=(cuts.sized(50)-lower).is_empty(),
      upper_via2_enclosure=(cuts.sized(50)-metal).is_empty(),
      via2_existing_clearance=cuts.sized(295).interacting(full[29]).is_empty(),
      foreign_m2_at_new_vias=cuts.sized(5).interacting(full[10]-owned[10]).is_empty(),
      foreign_m3_clearance=metal.sized(605).interacting(full[30]-owned[30]).is_empty(),
      foreign_via2=metal.sized(5).interacting(full[29]-owned[29]).is_empty(),
      foreign_via3=metal.sized(5).interacting(full[49]-owned[49]).is_empty(),
      no_unclassified_m3_or_via=all((metal.sized(605)if layer==30 else cuts.sized(295)if layer==29 else metal.sized(5)).interacting(r).is_empty()for(layer,dt),r in other.items()),
      new_m3_material=not(metal-full[30]).is_empty())
def mixed_controls():
    layers=(8,19,10,29,30,49);own={n:pya.Region()for n in layers};full={n:pya.Region()for n in layers}
    cut=box(0,0,95);metal=box(0,0,300);lower=box(0,0,300)
    need(all(mixed_m3_guard(metal,cut,lower,own,full,{}).values()),"isolated mixed legal via2")
    passed=["isolated enclosed new Via2"]
    for name,layer,shape,key in[
      ("foreign Metal3",30,box(500,0,100),"foreign_m3_clearance"),
      ("foreign Via2",29,box(0,0,95),"foreign_via2"),
      ("foreign Via3",49,box(0,0,95),"foreign_via3"),
      ("foreign Metal2 at cut",10,box(0,0,100),"foreign_m2_at_new_vias")]:
        bad={n:r.dup()for n,r in full.items()};bad[layer]+=shape
        need(not mixed_m3_guard(metal,cut,lower,own,bad,{})[key],name);passed.append("reject "+name)
    bad={n:r.dup()for n,r in full.items()};bad[29]=box(450,0,95)
    need(not mixed_m3_guard(metal,cut,lower,own,bad,{})["via2_existing_clearance"],"near existing Via2");passed.append("reject existing Via2 spacing")
    need(not mixed_m3_guard(metal,cut,box(0,0,100),own,full,{})["lower_via2_enclosure"],"lower enclosure");passed.append("reject insufficient lower Via2 enclosure")
    need(not mixed_m3_guard(box(0,0,100),cut,lower,own,full,{})["upper_via2_enclosure"],"upper enclosure");passed.append("reject insufficient upper Via2 enclosure")
    need(not mixed_m3_guard(metal,cut,lower,own,full,{(30,24):box(0,0,10)})["no_unclassified_m3_or_via"],"unclassified Metal3");passed.append("reject unclassified Metal3 drawing")
    a=box(-250,0,95);b=box(250,0,95)
    need(a.sized(295).interacting(b).is_empty(),"two separated actual 190nm cuts");passed.append("two Via2 cuts retain original spacing")
    need(len(passed)==10,"mixed ten controls")
    return passed
def existing_m3_landings(anchor,owned,full,other):
    x,y=anchor["point_dbu"];need(anchor["metal"]==8 and(box(x,y,1)-owned[8]).is_empty(),"actual M1 anchor")
    lower_vias=[]
    for poly in owned[19].interacting(box(x,y,10000)).each():
        r=pya.Region(poly);b=poly.bbox()
        if b.width()==190 and b.height()==190 and poly.area()==36100 and(r.sized(50)-owned[8]).is_empty()and(r.sized(50)-owned[10]).is_empty():lower_vias.append(bounds(r))
    need(lower_vias,"original same-component local M1/Via1/M2 path")
    results=[];trials=[]
    for poly in owned[29].interacting(box(x,y,10000)).each():
        r=pya.Region(poly);b=poly.bbox();xx=(b.left+b.right)//2;yy=(b.bottom+b.top)//2;pad=box(xx,yy,300)
        t=mixed_m3_guard(pad,pya.Region(),owned[10],owned,full,other)
        t.update(original_cut_190nm=b.width()==190 and b.height()==190 and poly.area()==36100,
          original_cut_lower_enclosure=(r.sized(50)-owned[10]).is_empty(),original_cut_upper_enclosure=(r.sized(50)-owned[30]).is_empty(),
          grid5=xx%5==0 and yy%5==0,center_in_original_m3=(box(xx,yy,1)-owned[30]).is_empty())
        admitted=all(v for k,v in t.items()if k!="new_m3_material")
        row=dict(center=[xx,yy],existing_via2_box=bounds(r),checks=t,admitted=admitted);trials.append(row)
        if admitted:results.append(dict(center=[xx,yy],pad=pad,record=row))
    results.sort(key=lambda row:((row["center"][0]-x)**2+(row["center"][1]-y)**2,row["center"]))
    return results[:4],dict(original_anchor=anchor,original_via1_boxes=lower_vias,trials=trials,selected_search_limit=4,new_via1_count=0,existing_vias_unchanged=True)

def rectilinear_search(starts,goals,obstacles,window,max_expanded=100000,seconds=120):
    import heapq,time
    started=time.monotonic();left,bottom,right,top=window
    need(all(type(v)is int for v in window)and left<right and bottom<top,"bounded integer search window")
    starts=[tuple(p)for p in starts];goals=[tuple(p)for p in goals]
    need(starts and goals and all(x%5==0 and y%5==0 for x,y in starts+goals),"nonempty grid5 endpoints")
    def inside(p):return left<p[0]<right and bottom<p[1]<top
    clipped=(obstacles&pya.Region(pya.Box(left,bottom,right,top))).merged()
    xs={p[0]for p in starts+goals};ys={p[1]for p in starts+goals}
    for poly in clipped.each():
        vertices=list(poly.each_point_hull())
        for hole in range(poly.holes()):vertices.extend(poly.each_point_hole(hole))
        for p in vertices:
            xs.update([p.x//5*5-5,(p.x//5+1)*5+5])
            ys.update([p.y//5*5-5,(p.y//5+1)*5+5])
    xs.update(range((left//10000+1)*10000,right,10000));ys.update(range((bottom//10000+1)*10000,top,10000))
    xs=sorted(x for x in xs if left<x<right);ys=sorted(y for y in ys if bottom<y<top)
    report=dict(x_coordinates=len(xs),y_coordinates=len(ys),expanded=0,edge_checks=0,seconds_limit=seconds,node_limit=max_expanded,window=window,reason=None)
    if len(xs)>4000 or len(ys)>4000:report["reason"]="bounded coordinate count";return None,report
    xi={x:i for i,x in enumerate(xs)};yi={y:i for i,y in enumerate(ys)}
    node_cache={};edge_cache={}
    def clear(node):
        if node not in node_cache:node_cache[node]=box(xs[node[0]],ys[node[1]],1).interacting(clipped).is_empty()
        return node_cache[node]
    def edge(a,b):
        key=tuple(sorted((a,b)))
        if key not in edge_cache:
            edge_cache[key]=wire([[xs[a[0]],ys[a[1]]],[xs[b[0]],ys[b[1]]]],width=2).interacting(clipped).is_empty()
            report["edge_checks"]+=1
        return edge_cache[key]
    target={(xi[x],yi[y])for x,y in goals if inside((x,y))and x in xi and y in yi}
    target={n for n in target if clear(n)}
    if not target:report["reason"]="no clear target";return None,report
    def heuristic(n):return min(abs(xs[n[0]]-xs[g[0]])+abs(ys[n[1]]-ys[g[1]])for g in target)
    heap=[];dist={};parents={}
    for x,y in starts:
        if not inside((x,y))or x not in xi or y not in yi:continue
        n=(xi[x],yi[y])
        if not clear(n):continue
        dist[n]=0;parents[n]=None;heapq.heappush(heap,(heuristic(n),0,n))
    if not heap:report["reason"]="no clear source";return None,report
    while heap:
        _,cost,node=heapq.heappop(heap)
        if dist.get(node)!=cost:continue
        if node in target:
            chain=[];cursor=node
            while cursor is not None:
                chain.append([xs[cursor[0]],ys[cursor[1]]]);cursor=parents[cursor]
            chain.reverse();compact=[]
            for point in chain:
                while len(compact)>=2 and((compact[-2][0]==compact[-1][0]==point[0])or(compact[-2][1]==compact[-1][1]==point[1])):compact.pop()
                compact.append(point)
            report.update(reason="found",path_length_dbu=cost,elapsed_seconds=time.monotonic()-started,visited=len(dist))
            return compact,report
        report["expanded"]+=1
        if report["expanded"]>max_expanded or time.monotonic()-started>seconds:
            report.update(reason="bounded search budget",elapsed_seconds=time.monotonic()-started,visited=len(dist));return None,report
        i,j=node
        for other in((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
            ii,jj=other
            if not(0<=ii<len(xs)and 0<=jj<len(ys))or not clear(other):continue
            new=cost+abs(xs[i]-xs[ii])+abs(ys[j]-ys[jj])
            if new>=dist.get(other,float("inf"))or not edge(node,other):continue
            dist[other]=new;parents[other]=node;heapq.heappush(heap,(new+heuristic(other),new,other))
    report.update(reason="no path in bounded exact obstacle graph",elapsed_seconds=time.monotonic()-started,visited=len(dist))
    return None,report
def maze_controls():
    window=[-2000,-2000,2000,2000];empty=pya.Region()
    p,r=rectilinear_search([[-1000,0]],[[1000,0]],empty,window)
    need(p==[[-1000,0],[1000,0]]and r["path_length_dbu"]==2000,"empty exact Manhattan path")
    checks=["straight empty graph"]
    obstacle=box(0,0,300);before=bounds(obstacle)
    p,r=rectilinear_search([[-1000,0]],[[1000,0]],obstacle,window)
    need(p is not None and len(p)>2 and r["path_length_dbu"]>2000 and wire(p,width=2).interacting(obstacle).is_empty(),"actual obstacle detour")
    need(bounds(obstacle)==before,"input obstacle untouched");checks.append("detour exact obstacle without mutation")
    wall=pya.Region(pya.Box(-100,-3000,100,3000))
    p,r=rectilinear_search([[-1000,0]],[[1000,0]],wall,window)
    need(p is None,"closed wall has no accepted path");checks.append("reject closed wall")
    p,r=rectilinear_search([[0,0]],[[1000,0]],obstacle,window);need(p is None and r["reason"]=="no clear source","blocked source");checks.append("reject blocked source")
    p,r=rectilinear_search([[-1000,0]],[[0,0]],obstacle,window);need(p is None and r["reason"]=="no clear target","blocked target");checks.append("reject blocked target")
    p,r=rectilinear_search([[-1000,0],[500,0]],[[1000,0]],empty,window)
    need(p==[[500,0],[1000,0]],"native multiple access alternatives");checks.append("select shorter valid access")
    p,r=rectilinear_search([[-1000,0]],[[1000,0]],obstacle,window,max_expanded=0)
    need(p is None and r["reason"]=="bounded search budget","budget is not acceptance");checks.append("budget refusal")
    try:rectilinear_search([[-1001,0]],[[1000,0]],empty,window)
    except AssertionError:checks.append("reject off-grid new path")
    else:raise AssertionError("off-grid accepted")
    need(len(checks)==8,"eight maze controls");return checks
def mixed_maze(access3,bridges,owned,current,other3,top):
    if not access3 or not bridges:return None,dict(reason="no admitted endpoints")
    obstacles=(current[30]-owned[30]).sized(910)+(current[29]-owned[29]).sized(310)+(current[49]-owned[49]).sized(310)
    for(layer,dt),r in other3.items():obstacles+=r.sized(910 if layer==30 else 310)
    obstacles=obstacles.merged()
    points=[q["center"]for q in access3+bridges];b=top.bbox()
    window=[max(b.left+300,min(p[0]for p in points)-100000),max(b.bottom+300,min(p[1]for p in points)-100000),
      min(b.right-300,max(p[0]for p in points)+100000),min(b.top-300,max(p[1]for p in points)+100000)]
    path,report=rectilinear_search([q["center"]for q in access3],[q["center"]for q in bridges],obstacles,window)
    report.update(m3_center_clearance_dbu=910,via_center_clearance_dbu=310,original_geometry_unchanged=True,physical_acceptance=False)
    if path is None:return None,report
    start=next(q for q in access3 if q["center"]==path[0]);bridge=next(q for q in bridges if q["center"]==path[-1])
    metal3=(wire(path)+start["pad"]+bridge["pad"]).merged()
    checks=mixed_m3_guard(metal3,bridge["cuts"],(owned[10]+bridge["metal2"]).merged(),owned,current,other3)
    checks.update(single_new_m3=metal3.count()==1,inside_original_bbox=((metal3+bridge["metal2"])-pya.Region(top.bbox())).is_empty(),
      connects_existing_m3=(box(*start["center"],1)-metal3).is_empty(),
      all_unknown_via_drawings_clear=all(metal3.sized(5).interacting(r).is_empty()for(layer,dt),r in other3.items()if layer in(29,49)))
    report.update(points=path,final_original_guards=checks)
    if not all(checks.values()):report["reason"]="final native guards refused maze result";return None,report
    return dict(start=start,bridge=bridge,metal3=metal3,path=path,checks=checks),report

def mixed_generate(base,cfg):
    gpath=base/"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds";wpath=base/"binding/inputs/wire/native05/wires.l2n"
    g=pya.Layout();g.read(str(gpath));top=g.cell(TOP);need(top is not None and g.dbu==.001,"original GDS")
    before=region_snapshot(g,top);w=pya.LayoutToNetlist();w.read(str(wpath));need(w.internal_layout().dbu==.001,"wire DBU")
    layers=(8,19,10,29,30,49);objects={n:w.layer_by_name("gds_"+str(n))for n in layers}
    need(all(r is not None for r in objects.values()),"six ownership layers")
    full={n:before.get((n,0),pya.Region())for n in layers}
    for n in layers:need((full[n]^objects[n]).is_empty(),"native union "+str(n))
    nets={n.cluster_id:n for n in w.netlist().top_circuit().each_net()}
    physical={a["label"]:a for a in json.loads((base/"binding/inputs/wire/anchors08.json").read_bytes())["anchors"]}
    other2={k:r for k,r in before.items()if k[0]in(10,19)and k[1]!=0 and not r.is_empty()}
    other3={k:r for k,r in before.items()if k[0]in(30,29,49)and k[1]!=0 and not r.is_empty()}
    additions={n:pya.Region()for n in(10,29,30)};inserted=[];proposals=[]
    for label,aa,bb in TARGETS:
        a=physical[aa];b=physical[bb];verify_target(base,aa,a,bb,b)
        need(a["wire_component"]==b["wire_component"]and a["native_cluster"]==b["native_cluster"],"original same conductor")
        m1,m2=(a,b)if a["metal"]==8 else(b,a);need(m1["metal"]==8 and m2["metal"]==10,"actual mixed terminal pair")
        owned={n:w.shapes_of_net(nets[a["wire_component"]],objects[n],True).merged()for n in layers}
        current={n:(full[n]+additions.get(n,pya.Region())).merged()for n in layers}
        access3,proof3=existing_m3_landings(m1,owned,current,other3)
        access2,proof2=terminal_access(m2,owned,current,other2)
        row=dict(label=label,source_anchor=a,sink_anchor=b,m1_to_m3_access=proof3,m2_access=proof2,bridge_trials=[],route_trials=[],selected=None)
        if access3 and access2 is not None:
            x,y=access2["center"];bridges=[]
            for delta in(2500,-2500,5000,-5000,7500,-7500,10000,-10000):
                for dx,dy in((delta,0),(0,delta)):
                    for orientation in("horizontal","vertical"):
                        cx,cy=x+dx,y+dy
                        points=[[cx-250,cy],[cx+250,cy]]if orientation=="horizontal"else[[cx,cy-250],[cx,cy+250]]
                        c0=box(*points[0],95);c1=box(*points[1],95);cuts=(c0+c1).merged()
                        pad=pya.Region(pya.Box(min(p[0]for p in points)-300,min(p[1]for p in points)-300,max(p[0]for p in points)+300,max(p[1]for p in points)+300))
                        metal2=(wire([[x,y],[cx,cy]])+access2["pad"]+pad).merged()
                        t2=conductor_guard(metal2,pya.Region(),owned,current,other2)
                        t3=mixed_m3_guard(pad,cuts,(owned[10]+metal2).merged(),owned,current,other3)
                        t3.update(two_new_cuts=cuts.count()==2,new_cuts_spacing=c0.sized(295).interacting(c1).is_empty(),
                          lower_m2_connected=metal2.count()==1,original_m2_anchor_connected=(box(*m2["point_dbu"],1)-metal2).is_empty())
                        admitted=all(t2.values())and all(v for k,v in t3.items()if k!="new_m3_material")
                        br=dict(center=[cx,cy],via2_centers=points,m2_guards=t2,m3_guards=t3,admitted=admitted)
                        row["bridge_trials"].append(br)
                        if admitted:bridges.append(dict(center=[cx,cy],cuts=cuts,pad=pad,metal2=metal2,record=br))
            bridges.sort(key=lambda q:abs(q["center"][0]-x)+abs(q["center"][1]-y))
            for bridge in bridges:
                if row["selected"]is not None:break
                xx,yy=bridge["center"]
                for start in access3:
                    sx,sy=start["center"]
                    routes=[[[sx,sy],[xx,sy],[xx,yy]],[[sx,sy],[sx,yy],[xx,yy]]]
                    for delta in(-2000,2000,-5000,5000,-10000,10000,-20000,20000):
                        routes.extend([[[sx,sy],[sx,sy+delta],[xx,sy+delta],[xx,yy]],[[sx,sy],[sx+delta,sy],[sx+delta,yy],[xx,yy]]])
                    for points in routes:
                        metal3=(wire(points)+start["pad"]+bridge["pad"]).merged()
                        checks=mixed_m3_guard(metal3,bridge["cuts"],(owned[10]+bridge["metal2"]).merged(),owned,current,other3)
                        checks.update(single_new_m3=metal3.count()==1,inside_original_bbox=((metal3+bridge["metal2"])-pya.Region(top.bbox())).is_empty(),
                          connects_existing_m3=(box(*start["center"],1)-metal3).is_empty())
                        trial=dict(points=points,bridge_center=bridge["center"],source_center=start["center"],guards=checks)
                        row["route_trials"].append(trial)
                        if all(checks.values()):
                            row["selected"]=dict(route=trial,bridge=bridge["record"],existing_m3_access=start["record"],new_via2_count=2,new_via1_count=0)
                            for n,r in((10,bridge["metal2"]),(29,bridge["cuts"]),(30,metal3)):
                                for poly in r.each():inserted.append(top.shapes(g.layer(n,0)).insert(poly))
                                additions[n]+=r
                            break
                    if row["selected"]is not None:break
        if row["selected"]is None and access3 and access2 is not None:
            found,maze_report=mixed_maze(access3,bridges,owned,current,other3,top);row["maze_search"]=maze_report
            if found is not None:
                bridge=found["bridge"];start=found["start"]
                row["selected"]=dict(route=dict(points=found["path"],guards=found["checks"],maze_search=True),bridge=bridge["record"],
                  existing_m3_access=start["record"],new_via2_count=2,new_via1_count=0)
                for n,r in((10,bridge["metal2"]),(29,bridge["cuts"]),(30,found["metal3"])):
                    for poly in r.each():inserted.append(top.shapes(g.layer(n,0)).insert(poly))
                    additions[n]+=r
        proposals.append(row);save("mixed-target-"+label+".json",row)
    adopted=[r["label"]for r in proposals if r["selected"]is not None]
    save("mixed-generation-summary.json",dict(generated_targets=adopted,unrouted_targets=[r["label"]for r in proposals if r["selected"]is None],
      input_gds=pin(gpath),input_l2n=pin(wpath),only_added_layers=[10,29,30],original_devices_m1_via1_unchanged=True,
      physical_acceptance=False,fresh_RC=False,DRC=False,LVS=False,full_phy_accepted=False))
    need(adopted,"no mixed-layer candidate passed original conservative spacing and enclosure guards")
    NATIVE.mkdir();candidate=NATIVE/"nssoc_cdr_pd500_wire_tail_shortcuts.gds";g.write(str(candidate))
    loaded=pya.Layout();loaded.read(str(candidate));after=region_snapshot(loaded,loaded.cell(TOP))
    need(loaded.dbu==g.dbu and{c.name for c in loaded.each_cell()}=={c.name for c in g.each_cell()},"serialized hierarchy")
    for layer in set(before)|set(after):
        expected=before.get(layer,pya.Region())
        if layer in((10,0),(29,0),(30,0)):expected=(expected+additions[layer[0]]).merged()
        need((expected^after.get(layer,pya.Region())).is_empty(),"exact mixed layer delta "+str(layer))
    for shape in reversed(inserted):shape.delete()
    reverted=region_snapshot(g,top);need(set(before)==set(reverted),"reversed layers")
    for layer in before:need((before[layer]^reverted[layer]).is_empty(),"exact original geometry reversal")
    need(pin(gpath)==cfg["complete_members"]["binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds"],"original GDS bytes")
    save("mixed-generation-proof.json",dict(candidate=pin(candidate),generated_targets=adopted,exact_serialized_delta=True,original_material_roundtrip=True,
      original_devices_m1_via1_unchanged=True,physical_acceptance=False,full_phy_accepted=False,
      scope="Physical candidate only; requires strict native DRC/LVS, canonical binding, fresh RC and original loaded electrical gates"))
    need(len(adopted)==4,"partial mixed-layer candidate preserved; not all four paths routed")

def inspect_current_rails(base,cfg):
    """Read actual current native rail topology; no synthetic rail or geometry edit."""
    diagnosis=cfg["diagnosis"]
    run=prior.api("actions/runs/"+str(diagnosis["run"]))
    need(run["status"]=="completed"and run["conclusion"]=="success"and run["head_sha"]==diagnosis["source"],"current completed full-wave diagnosis")
    artifacts=prior.api("actions/runs/"+str(diagnosis["run"])+"/artifacts")["artifacts"]
    artifact=next(a for a in artifacts if a["id"]==diagnosis["artifact"])
    need(artifact["digest"]=="sha256:"+diagnosis["artifact_sha256"],"exact current diagnosis proof")
    comp=json.loads((base/"mim/composition/composition.json").read_bytes())
    planes=json.loads((base/"binding/inputs/native-planes.json").read_bytes())
    avss={(a["native_cluster"],a["native_name"])for a in planes["anchors"]if a["logical_net"]=="avss"}
    need(len(avss)==1,"one actual canonical avss net")
    key=next(iter(avss))
    records={int(d["native_id"]):d for d in comp["device_records"]}
    anchors=json.loads((base/"binding/inputs/wire/anchors08.json").read_bytes())["anchors"]
    physical={a["label"]:a for a in anchors}
    targets=[3,4,5,6,32,33,34,35]
    gpath=base/"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds"
    wpath=base/"binding/inputs/wire/native05/wires.l2n"
    before_pin=pin(gpath);wire_pin=pin(wpath)
    g=pya.Layout();g.read(str(gpath));top=g.cell(TOP)
    need(top is not None and g.dbu==.001,"actual current top and DBU")
    before=region_snapshot(g,top)
    w=pya.LayoutToNetlist();w.read(str(wpath));need(w.internal_layout().dbu==.001,"actual wire DBU")
    layers=(8,19,10,29,30,49)
    objects={n:w.layer_by_name("gds_"+str(n))for n in layers}
    need(all(r is not None for r in objects.values()),"all six original conductor layers")
    full={n:before.get((n,0),pya.Region())for n in layers}
    for n in layers:need((full[n]^objects[n]).is_empty(),"actual full GDS/L2N union "+str(n))
    nets={n.cluster_id:n for n in w.netlist().top_circuit().each_net()}
    other2={k:r for k,r in before.items()if k[0]in(10,19)and k[1]!=0 and not r.is_empty()}
    other3={k:r for k,r in before.items()if k[0]in(30,29,49)and k[1]!=0 and not r.is_empty()}
    entries=[];components=set()
    for number in targets:
        record=records[number];need(record["model"]=="sg13_lv_nmos","measured tail MOS")
        term=next(t for t in record["terminals"]if t["terminal"]=="S")
        need((term["native_cluster"],term["native_net"])==key,"tail source connected to actual canonical avss")
        label="T%03d_S"%number;anchor=physical[label]
        need(anchor["native_cluster"]==key[0],"actual source anchor cluster")
        component=anchor["wire_component"];components.add(component);need(component in nets,"existing wire component")
        owned={n:w.shapes_of_net(nets[component],objects[n],True).merged()for n in layers}
        need(anchor["metal"]in layers and(box(*anchor["point_dbu"],1)-owned[anchor["metal"]]).is_empty(),"actual source anchor on owned metal")
        access2,proof2=terminal_access(anchor,owned,full,other2)
        landings=[];proof3={}
        if anchor["metal"]==8:
            try:landings,proof3=existing_m3_landings(anchor,owned,full,other3)
            except AssertionError as exc:proof3=dict(refusal=str(exc))
        entry=dict(label=label,record=record,anchor=anchor,component=component,
            existing_m2_access=proof2,admitted_m2_access=access2 is not None,
            existing_m3_access=proof3,admitted_m3_access=len(landings),
            owned_layer_geometry={str(n):dict(bbox=bounds(r),polygons=r.count(),area_dbu2=r.area())for n,r in owned.items()},
            original_geometry_unchanged=True,physical_acceptance=False)
        save("current-rail-"+label+".json",entry)
        entries.append(dict(label=label,component=component,metal=anchor["metal"],admitted_m2_access=access2 is not None,admitted_m3_access=len(landings)))
    need(len(components)==1,"all measured tail-source rails same actual extracted component")
    rail_anchors=[a for a in anchors if a["native_cluster"]==key[0]]
    need(rail_anchors and all(a["wire_component"]in components for a in rail_anchors),"complete canonical rail anchors share actual wire component")
    save("current-avss-anchors.json",dict(native_net=dict(cluster=key[0],name=key[1]),anchors=rail_anchors,
        canonical_anchors=[a for a in planes["anchors"]if(a["native_cluster"],a["native_name"])==key],source_binding_exact=True))
    after=region_snapshot(g,top);need(set(before)==set(after),"unchanged layer set")
    for layer in before:need((before[layer]^after[layer]).is_empty(),"no geometry mutation")
    need(pin(gpath)==before_pin and pin(wpath)==wire_pin,"original native bytes unchanged")
    save("current-rail-access-summary.json",dict(status="COMPLETE_CURRENT_NATIVE_AVSS_ACCESS_INSPECTION",
        input_gds=before_pin,input_l2n=wire_pin,diagnosis=diagnosis,targets=entries,
        rail_anchor_count=len(rail_anchors),canonical_avss=dict(cluster=key[0],name=key[1]),all_sources_same_actual_rail=True,
        new_geometry_generated=False,original_geometry_unchanged=True,physical_acceptance=False,
        full_phy_accepted=False,final_timing_complete=False))

def ground_strap_guard(strap,core,owned,full,other,outline):
    return dict(
        original_continuous_same_net_core=(core-owned[67]).is_empty(),
        connects_original_core=(core-strap).is_empty(),
        new_metal=not(strap-full[67]).is_empty(),
        single_rectangle=strap.count()==1 and all(p.area()==p.bbox().area()for p in strap.each()),
        inside_original_bbox=(strap-outline).is_empty(),
        foreign_metal5_clearance_5um=strap.sized(5005).interacting(full[67]-owned[67]).is_empty(),
        foreign_via4=strap.sized(5).interacting(full[66]-owned[66]).is_empty(),
        foreign_topvia1=strap.sized(5).interacting(full[125]-owned[125]).is_empty(),
        unknown_drawing_clear=all(strap.sized(5005 if k[0]==67 else 5).interacting(r).is_empty()for k,r in other.items()))
def ground_strap_controls():
    own={n:pya.Region()for n in(66,67,125)}
    core=pya.Region(pya.Box(-5,-10000,5,10000));own[67]=pya.Region(pya.Box(-300,-10000,300,10000))
    strap=pya.Region(pya.Box(-3000,-10000,3000,10000));outline=box(0,0,20000)
    full={n:r.dup()for n,r in own.items()};checks=[]
    need(all(ground_strap_guard(strap,core,own,full,{},outline).values()),"positive real-owned vertical strap")
    checks.append("add strap on continuous owned original rail")
    for label,layer,key in[("foreign M5",67,"foreign_metal5_clearance_5um"),("foreign Via4",66,"foreign_via4"),("foreign TopVia1",125,"foreign_topvia1")]:
        f={n:r.dup()for n,r in full.items()};f[layer]+=box(1000,0,100)
        need(not ground_strap_guard(strap,core,own,f,{},outline)[key],"reject "+label);checks.append("reject "+label)
    missing={n:r.dup()for n,r in own.items()};missing[67]-=box(0,0,100)
    need(not ground_strap_guard(strap,core,missing,full,{},outline)["original_continuous_same_net_core"],"reject broken core");checks.append("reject broken owned core")
    need(not ground_strap_guard(strap,core,own,full,{(67,24):box(4000,0,100)},outline)["unknown_drawing_clear"],"reject unknown mask");checks.append("reject unknown mask")
    need(not ground_strap_guard(strap,core,own,full,{},box(0,0,100))["inside_original_bbox"],"reject outside");checks.append("reject outside layout")
    need(not ground_strap_guard(own[67],core,own,full,{},outline)["new_metal"],"reject no-op");checks.append("reject no new geometry")
    need(len(checks)==8,"eight actual strap guards")
    return checks
def generate_ground_strap(base,cfg):
    # First repeat the actual source/avss ownership audit, retaining inaccessible
    # local M1 accesses. The repair below is on the EXISTING Metal5 backbone.
    inspect_current_rails(base,cfg)
    report=json.loads((OUT/"current-avss-anchors.json").read_bytes())
    anchors=[a for a in report["canonical_anchors"]if a["metal"]==67]
    need(len(anchors)==16 and len({a["point_dbu"][0]for a in anchors})==1,"sixteen actual M5 ground-spine anchors")
    x=anchors[0]["point_dbu"][0];ys=[a["point_dbu"][1]for a in anchors]
    need(x%5==0 and all(y%5==0 for y in ys),"original spine reference grid")
    physical=report["anchors"];components={a["wire_component"]for a in physical}
    need(len(components)==1,"one actual ground conductor");component=next(iter(components))
    gpath=base/"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds";wpath=base/"binding/inputs/wire/native05/wires.l2n"
    g=pya.Layout();g.read(str(gpath));top=g.cell(TOP);need(top is not None and g.dbu==.001,"actual original layout")
    before=region_snapshot(g,top);outline=pya.Region(top.bbox())
    w=pya.LayoutToNetlist();w.read(str(wpath));need(w.internal_layout().dbu==.001,"original wire DBU")
    layers=(66,67,125);objects={n:w.layer_by_name("gds_"+str(n))for n in layers}
    need(all(r is not None for r in objects.values()),"actual Via4 Metal5 TopVia1")
    full={n:before.get((n,0),pya.Region())for n in layers}
    for n in layers:need((full[n]^objects[n]).is_empty(),"complete current physical layer union "+str(n))
    nets={n.cluster_id:n for n in w.netlist().top_circuit().each_net()};need(component in nets,"actual ground component")
    owned={n:w.shapes_of_net(nets[component],objects[n],True).merged()for n in layers}
    for a in anchors:need((box(*a["point_dbu"],1)-owned[67]).is_empty(),"each canonical anchor lies on actual owned Metal5")
    b=top.bbox();strip=(owned[67]&pya.Region(pya.Box(x-5,b.bottom,x+5,b.top))).merged()
    candidates=[]
    for poly in strip.each():
        q=poly.bbox()
        core=pya.Region(pya.Box(x-5,q.bottom,x+5,q.top))
        if q.bottom<min(ys)and q.top>max(ys)and(core-owned[67]).is_empty():candidates.append((q.bottom,q.top))
    save("ground-spine-proposal.json",dict(x_dbu=x,anchor_y_dbu=ys,continuous_original_spans=candidates,
        component=component,layer=67,proposed_width_dbu=6000,foreign_metal_clearance_dbu=5005,
        original_devices_and_vias_unchanged=True,physical_acceptance=False))
    need(len(candidates)==1,"unique continuous original M5 spine spanning every actual ground anchor")
    low,high=candidates[0];need(low%5==0 and high%5==0,"original spine ends on grid")
    core=pya.Region(pya.Box(x-5,low,x+5,high))
    strap=pya.Region(pya.Box(x-3000,low,x+3000,high))
    other={k:r for k,r in before.items()if k[0]in layers and k[1]!=0 and not r.is_empty()}
    checks=ground_strap_guard(strap,core,owned,full,other,outline)
    save("ground-spine-guards.json",dict(checks=checks,strap_bbox=bounds(strap),added_area_dbu2=(strap-full[67]).area(),physical_acceptance=False))
    need(all(checks.values()),"real ground-spine addition rejected by conservative native guards")
    handle=top.shapes(g.layer(67,0)).insert(next(strap.each()))
    NATIVE.mkdir();candidate=NATIVE/"nssoc_cdr_pd500_wire_ground_strap.gds";g.write(str(candidate))
    after_layout=pya.Layout();after_layout.read(str(candidate));after=region_snapshot(after_layout,after_layout.cell(TOP))
    need(after_layout.dbu==g.dbu and{c.name for c in after_layout.each_cell()}=={c.name for c in g.each_cell()},"serialized original hierarchy")
    for layer in set(before)|set(after):
        expected=before.get(layer,pya.Region())
        if layer==(67,0):expected=(expected+strap).merged()
        need((expected^after.get(layer,pya.Region())).is_empty(),"exact sole M5 material delta "+str(layer))
    handle.delete();reverted=region_snapshot(g,top);need(set(before)==set(reverted),"original layer set after removal")
    for layer in before:need((before[layer]^reverted[layer]).is_empty(),"exact material reversal "+str(layer))
    need(pin(gpath)==cfg["complete_members"]["binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds"],"original GDS unchanged")
    save("ground-spine-generation-proof.json",dict(candidate=pin(candidate),input_gds=pin(gpath),input_l2n=pin(wpath),
        only_added_layer=[67,0],width_dbu=6000,span_dbu=[low,high],component=component,canonical_anchors=anchors,
        exact_serialized_delta=True,original_material_roundtrip=True,original_devices_and_vias_unchanged=True,
        physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False,
        requires=["full560DRC","deep_flat_LVS13","current_canonical_binding","fresh_RC","unchanged_loaded_wave_gates"]))

def inspect_ground_topology(base,cfg):
    inspect_current_rails(base,cfg)
    report=json.loads((OUT/"current-avss-anchors.json").read_bytes())
    components={a["wire_component"]for a in report["anchors"]};need(len(components)==1,"one current native avss component")
    component=next(iter(components))
    gp=base/"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds";wp=base/"binding/inputs/wire/native05/wires.l2n"
    g=pya.Layout();g.read(str(gp));top=g.cell(TOP);need(top is not None and g.dbu==.001,"current physical top")
    before=region_snapshot(g,top);w=pya.LayoutToNetlist();w.read(str(wp));need(w.internal_layout().dbu==.001,"actual wire DBU")
    nets={n.cluster_id:n for n in w.netlist().top_circuit().each_net()};need(component in nets,"actual native ground")
    layers=(8,19,10,29,30,49,50,66,67,125,126,133,134)
    records={};owned={}
    for n in layers:
        layer=w.layer_by_name("gds_"+str(n));need(layer is not None,"complete original conductor stack")
        full=before.get((n,0),pya.Region());need((full^layer).is_empty(),"complete physical union "+str(n))
        region=w.shapes_of_net(nets[component],layer,True).merged();owned[n]=region
        need((region-full).is_empty(),"actual owned subset")
        polys=[dict(bbox=bounds(pya.Region(p)),area_dbu2=p.area(),rectangle=p.area()==p.bbox().area())for p in region.each()]
        records[str(n)]=dict(bbox=bounds(region),polygons=len(polys),area_dbu2=region.area(),members=polys)
    rows=[]
    for anchor in report["canonical_anchors"]:
        metal=anchor["metal"];point=anchor["point_dbu"];touch=box(*point,1)
        need(metal in owned and(touch-owned[metal]).is_empty(),"canonical avss anchor on extracted owned stack")
        rows.append(dict(anchor=anchor,containing_original_polygon_bboxes=[bounds(pya.Region(p))for p in owned[metal].interacting(touch).each()],
            local_stack={str(n):dict(bbox=bounds(owned[n]&box(*point,20000)),polygons=(owned[n]&box(*point,20000)).merged().count())for n in layers}))
    need(pin(gp)==cfg["complete_members"]["binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds"]and pin(wp)==cfg["complete_members"]["binding/inputs/wire/native05/wires.l2n"],"native inputs unchanged")
    after=region_snapshot(g,top);need(set(before)==set(after),"unchanged layers")
    for k in before:need((before[k]^after[k]).is_empty(),"unchanged actual geometry")
    save("current-ground-stack-topology.json",dict(status="COMPLETE_CURRENT_NATIVE_GROUND_STACK_TOPOLOGY",
        input_gds=pin(gp),input_l2n=pin(wp),component=component,canonical_net=report["native_net"],
        layers=records,anchors=rows,all13native_unions_verified=True,original_geometry_unchanged=True,
        no_continuous_M5_spine_assumed=True,new_geometry_generated=False,physical_acceptance=False,
        full_phy_accepted=False,final_timing_complete=False))

def horizontal_ground_guard(original,widened,owned,full,other,outline):
    a=original.bbox();b=widened.bbox()
    foreign=(full[134]-owned[134]).merged()
    conservative_wide=pya.Region()
    for poly in foreign.each():
        if poly.bbox().height()>5000:conservative_wide.insert(poly)
    return dict(
        original_owned=(original-owned[134]).is_empty(),
        original_preserved=(original-widened).is_empty(),
        same_longitudinal_span=a.left==b.left and a.right==b.right,
        exact_width_change=a.height()==3200 and b.height()==4600,
        new_metal=not(widened-full[134]).is_empty(),
        foreign_topmetal2_standard_2um=widened.sized(2005).interacting(foreign).is_empty(),
        wide_foreign_topmetal2_clearance_5um=widened.sized(5005).interacting(conservative_wide).is_empty(),
        foreign_topvia2=widened.sized(5).interacting(full[133]-owned[133]).is_empty(),
        unclassified_drawing_clear=all(widened.sized(5005 if k[0]==134 else 5).interacting(r).is_empty()for k,r in other.items()),
        inside_original_bbox=(widened-outline).is_empty())
def horizontal_ground_options(original,owned,full,other,outline):
    options=[]
    centered=original.sized(0,700,2).merged()
    for strategy,dy in (("centered",0),("upper_only",700),("lower_only",-700)):
        widened=centered.moved(0,dy).merged()
        checks=horizontal_ground_guard(original,widened,owned,full,other,outline)
        options.append(dict(strategy=strategy,widened=widened,guards=checks,admitted=all(checks.values())))
    return options

def horizontal_clearance_probe(region,foreign):
    result={}
    for clearance in (1999,2000,2005,5000,5005):
        expanded=region.sized(clearance)
        touched=expanded.interacting(foreign)
        overlap=(expanded&foreign).merged()
        offenders=foreign.interacting(expanded)
        result[str(clearance)]=dict(interacting=not touched.is_empty(),overlap_area_dbu2=overlap.area(),
            overlap_bbox=None if overlap.is_empty()else bounds(overlap),
            foreign_bboxes=[bounds(pya.Region(p))for p in offenders.each()])
    return result

def horizontal_clearance_controls():
    original=pya.Region(pya.Box(0,0,100000,3200))
    foreign=pya.Region(pya.Box(0,5200,100000,8400))
    q=horizontal_clearance_probe(original,foreign)
    need(q["1999"]["overlap_area_dbu2"]==0 and q["2000"]["overlap_area_dbu2"]==0 and q["2005"]["overlap_area_dbu2"]==500000,"exact independent 2000nm gap area")
    candidate=original.sized(0,900,2)
    q=horizontal_clearance_probe(candidate,foreign)
    need(q["2000"]["overlap_area_dbu2"]==90000000,"actual widened spacing loss area")
    lower=original.sized(0,900,2).moved(0,-900)
    need(horizontal_clearance_probe(lower-original,foreign)["2005"]["overlap_area_dbu2"]==0,"new material clear while original exact minimum persists")
    return ["diagnose exact original 2000nm gap independently","diagnose added 900nm spacing loss independently","separate clear additions from unchanged minimum gap"]

def horizontal_ground_controls():
    original=pya.Region(pya.Box(-100000,-1600,100000,1600))
    widened=original.sized(0,700,2).merged();outline=box(0,0,200000)
    need(bounds(widened)==[-100000,-2300,100000,2300],"explicit anisotropic coordinates")
    own={134:original,133:pya.Region()};full={n:r.dup()for n,r in own.items()};checks=[]
    need(all(horizontal_ground_guard(original,widened,own,full,{},outline).values()),"positive owned horizontal widening")
    checks.append("widen real original horizontal branch without changing ends")
    for label,n,key in[("foreign TopMetal2",134,"foreign_topmetal2_standard_2um"),("foreign TopVia2",133,"foreign_topvia2")]:
        bad={k:r.dup()for k,r in full.items()};bad[n]+=box(0,2000,100)
        need(not horizontal_ground_guard(original,widened,own,bad,{},outline)[key],"reject "+label);checks.append("reject "+label)
    need(not horizontal_ground_guard(original,widened,own,full,{(134,24):box(0,4000,10)},outline)["unclassified_drawing_clear"],"unknown mask");checks.append("reject unknown drawing")
    need(not horizontal_ground_guard(original,widened,own,full,{},box(0,0,100))["inside_original_bbox"],"outside");checks.append("reject outside boundary")
    missing={134:pya.Region(),133:pya.Region()}
    need(not horizontal_ground_guard(original,widened,missing,full,{},outline)["original_owned"],"unowned");checks.append("reject unowned branch")
    shorter=pya.Region(pya.Box(-90000,-5000,100000,5000))
    need(not horizontal_ground_guard(original,shorter,own,full,{},outline)["same_longitudinal_span"],"changed endpoint");checks.append("reject changed original ends")
    need(not horizontal_ground_guard(original,original.sized(0,1000,2),own,full,{},outline)["exact_width_change"],"wrong width");checks.append("reject incorrect width")
    need(not horizontal_ground_guard(original,original,own,full,{},outline)["new_metal"],"no-op");checks.append("reject no new material")
    narrow={n:r.dup()for n,r in full.items()};narrow[134]+=pya.Region(pya.Box(-100000,4900,100000,8100))
    need(all(horizontal_ground_guard(original,widened,own,narrow,{},outline).values()),"two narrow parallel lines with actual2.6umspace")
    checks.append("two at-most5umlines retain standard2umspacing")
    broad={n:r.dup()for n,r in full.items()};broad[134]+=pya.Region(pya.Box(-100000,6000,100000,16000))
    broad_check=horizontal_ground_guard(original,widened,own,broad,{},outline)
    need(broad_check["foreign_topmetal2_standard_2um"]and not broad_check["wide_foreign_topmetal2_clearance_5um"],"wide neighboring line still requires5um")
    checks.append("wide foreign line retains5umspacing")
    choices=horizontal_ground_options(original,own,full,{},outline)
    need([bounds(v["widened"])for v in choices]==[[-100000,-2300,100000,2300],[-100000,-1600,100000,3000],[-100000,-3000,100000,1600]],"exact native asymmetric rectangles")
    checks.append("exact added-only centered upper and lower widths")
    above={n:r.dup()for n,r in full.items()};above[134]+=pya.Region(pya.Box(-100000,4000,100000,7200))
    choices=horizontal_ground_options(original,own,above,{},outline)
    need([v["strategy"]for v in choices if v["admitted"]]==["lower_only"],"choose actual clear side without weaker guards")
    checks.append("choose clear side next to blocked rail")
    both={n:r.dup()for n,r in above.items()};both[134]+=pya.Region(pya.Box(-100000,-7200,100000,-4000))
    need(not any(v["admitted"]for v in horizontal_ground_options(original,own,both,{},outline)),"reject both blocked sides")
    checks.append("reject when both sides blocked")
    need(len(checks)==14,"fourteen horizontal guard controls")
    return checks
def generate_horizontal_ground(base,cfg):
    inspect_ground_topology(base,cfg)
    topology=json.loads((OUT/"current-ground-stack-topology.json").read_bytes())
    need(topology["all13native_unions_verified"]and topology["component"]==14,"actual complete ground topology")
    gp=base/"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds";wp=base/"binding/inputs/wire/native05/wires.l2n"
    g=pya.Layout();g.read(str(gp));top=g.cell(TOP);need(top is not None and g.dbu==.001,"actual input")
    before=region_snapshot(g,top);outline=pya.Region(top.bbox())
    w=pya.LayoutToNetlist();w.read(str(wp));need(w.internal_layout().dbu==.001,"current wire DBU")
    nets={n.cluster_id:n for n in w.netlist().top_circuit().each_net()}
    layers=(133,134);objects={n:w.layer_by_name("gds_"+str(n))for n in layers}
    need(all(r is not None for r in objects.values()),"actual TopMetal2 and TopVia2")
    full={n:before.get((n,0),pya.Region())for n in layers}
    for n in layers:need((full[n]^objects[n]).is_empty(),"actual complete layer union")
    owned={n:w.shapes_of_net(nets[topology["component"]],objects[n],True).merged()for n in layers}
    candidates=[];retained=[]
    for poly in owned[134].each():
        b=poly.bbox()
        if b.height()==3200 and b.width()>=200000:candidates.append(poly)
        else:retained.append(dict(bbox=bounds(pya.Region(poly)),area_dbu2=poly.area()))
    need(len(candidates)==32 and len(retained)==1 and retained[0]["bbox"]==[0,80000,308800,144000],"all32observed branches and unchanged public pad")
    other={k:r for k,r in before.items()if k[0]in layers and k[1]!=0 and not r.is_empty()}
    additions=pya.Region();rows=[];diagnosis=[]
    for index,poly in enumerate(sorted(candidates,key=lambda p:(p.bbox().bottom,p.bbox().left))):
        original=pya.Region(poly);options=horizontal_ground_options(original,owned,full,other,outline)
        selected=next((v for v in options if v["admitted"]),None)
        foreign=(full[134]-owned[134]).merged()
        diagnosis.append(dict(index=index,original_bbox=bounds(original),
            baseline=horizontal_clearance_probe(original,foreign),
            variants=[dict(strategy=v["strategy"],admitted=v["admitted"],
                whole=horizontal_clearance_probe(v["widened"],foreign),
                additions=horizontal_clearance_probe(v["widened"]-original,foreign))for v in options]))

        rows.append(dict(index=index,original_bbox=bounds(original),old_area_dbu2=original.area(),
            variants=[dict(strategy=v["strategy"],widened_bbox=bounds(v["widened"]),new_area_dbu2=v["widened"].area(),guards=v["guards"],admitted=v["admitted"])for v in options],
            selected_strategy=None if selected is None else selected["strategy"],admitted=selected is not None))
        if selected is not None:additions+=selected["widened"]
    save("horizontal-ground-proposal.json",dict(branches=rows,unchanged_public_pad=retained[0],
        accepted_branches=sum(r["admitted"]for r in rows),requested_branches=32,
        original_width_dbu=3200,candidate_width_dbu=4600,only_added_layer=[134,0],
        physical_acceptance=False,full_phy_accepted=False))
    save("horizontal-ground-clearance-diagnosis.json",dict(branches=diagnosis,
        exact_input_gds=pin(gp),exact_input_wire_l2n=pin(wp),
        diagnostic_only=True,original_guards_unchanged=True,physical_acceptance=False,full_phy_accepted=False))
    need(all(r["admitted"]for r in rows),"all actual ground branch widths must pass original owned-stack guards")
    additions=additions.merged();handles=[]
    for poly in additions.each():handles.append(top.shapes(g.layer(134,0)).insert(poly))
    NATIVE.mkdir();candidate=NATIVE/"nssoc_cdr_pd500_wire_ground_branches.gds";g.write(str(candidate))
    readback=pya.Layout();readback.read(str(candidate));after=region_snapshot(readback,readback.cell(TOP))
    need(readback.dbu==g.dbu and{c.name for c in readback.each_cell()}=={c.name for c in g.each_cell()},"exact serialized original hierarchy")
    for layer in set(before)|set(after):
        expected=before.get(layer,pya.Region())
        if layer==(134,0):expected=(expected+additions).merged()
        need((expected^after.get(layer,pya.Region())).is_empty(),"exact sole TopMetal2 delta "+str(layer))
    for h in reversed(handles):h.delete()
    reverted=region_snapshot(g,top);need(set(before)==set(reverted),"original layer set")
    for layer in before:need((before[layer]^reverted[layer]).is_empty(),"exact original material after reversal")
    need(pin(gp)==cfg["complete_members"]["binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds"],"original source GDS unchanged")
    save("horizontal-ground-generation-proof.json",dict(candidate=pin(candidate),input_gds=pin(gp),input_l2n=pin(wp),
        branch_count=32,original_width_dbu=3200,candidate_width_dbu=4600,only_added_layer=[134,0],
        exact_serialized_delta=True,original_material_roundtrip=True,original_devices_and_vias_unchanged=True,
        original_port_pad_unchanged=True,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False,
        requires=["full560DRC","deep_flat_LVS13","current_canonical_binding","fresh_RC","unchanged_loaded_wave_gates"]))

def inspect_critical_access(base,cfg):
    import shlex
    from collections import Counter,defaultdict
    from decimal import Decimal
    root=base/"mim/precise/wire/rc03"
    parse=lambda p:[shlex.split(line,comments=False)for line in p.read_text().splitlines()if line.strip()and not line.lstrip().startswith("*")]
    raw=parse(root/"pump_wires.ext");distributed=parse(root/"pump_wires.res.ext")
    import copy
    original={a["label"]:a for a in json.loads((base/"binding/inputs/wire/anchors08.json").read_bytes())["anchors"]}
    extraction=json.loads((base/"mim/precise/wire/anchors08.json").read_bytes())
    anchors={a["label"]:a for a in extraction["anchors"]}
    need(set(original)==set(anchors)and len(anchors)==978,"exact original and extraction anchor census")
    changes={r["label"]:r for r in extraction["mim_bottom_point_changes"]}
    wanted={"T"+str(n)+"_mim_btm"for n in range(273,280)}
    need(set(changes)==wanted and len(extraction["mim_bottom_point_changes"])==7,"exact documented seven MIM access references")
    def relocate(v,old,new):
        if isinstance(v,dict):return {k:(new if k=="point_dbu"and val==old else relocate(val,old,new))for k,val in v.items()}
        if isinstance(v,list):return [relocate(x,old,new)for x in v]
        return v
    for name,anchor in anchors.items():
        expected=original[name]
        if name in changes:
            c=changes[name]
            need(c["old_point_dbu"]==expected["point_dbu"]and c["new_point_dbu"]==anchor["point_dbu"]and c["old_point_dbu"]!=c["new_point_dbu"],"documented actual MIM relocation")
            need(expected["metal"]==67 and expected["detail"]["model"]=="cap_cmim"and c["native_id"]==expected["detail"]["device"],"original MIM owner")
            expected=relocate(expected,c["old_point_dbu"],c["new_point_dbu"])
        need(anchor==expected,"only authenticated seven MIM coordinate changes; all other metadata exact")
    comp=json.loads((base/"mim/composition/composition.json").read_bytes())
    proof=json.loads((ROOT/"scripts/cdr-critical-resistance-inputs.json").read_bytes())
    need(proof["run"]==41430503141 and proof["source"]=="3d2601040c26b9e10443f674e6d2c211f8d14546","actual sensitivity producer")
    queries=proof["queries"];need(len(queries)==32,"all measured queries")
    public={r[1]:r for r in raw if r[0]=="port"}
    need(len(public)==978 and set(public)==set(anchors),"full native port coordinate census")
    deltas=[]
    for name,row in public.items():
        need(row[3:5]==row[5:7],"actual point port")
        xy=[int(v)*5 for v in row[3:5]];expected=anchors[name]["point_dbu"]
        delta=[a-b for a,b in zip(xy,expected)]
        deltas.append(dict(label=name,raw_port=row,actual_grid5_point=xy,anchor=anchors[name],delta_dbu=delta,within2nm=all(abs(v)<=2 for v in delta)))
    save("port-coordinate-diagnosis.json",dict(expected_grid_nm=5,expected_tolerance_nm=2,ports=deltas,
        mismatch_count=sum(not r["within2nm"]for r in deltas),native_headers=[r for r in raw if r[0]in("scale","resistclasses","tech","timestamp")],
        original_geometry_unchanged=True,physical_acceptance=False))
    need(all(r["within2nm"]for r in deltas),"actual 5nm native grid against every geometric anchor")
    inverse={v.lower():k for k,v in comp["wire_node_map"].items()}
    need(len(inverse)==len(comp["wire_node_map"]),"unique native-to-composed mapping")
    def value(s):
        m=re.fullmatch(r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)([numkpf]?)",s.lower())
        need(m is not None,"original native numeric token")
        return Decimal(m[1])*{"":Decimal(1),"n":Decimal("1e-9"),"u":Decimal("1e-6"),"m":Decimal("1e-3"),"k":Decimal("1e3"),"p":Decimal("1e-12"),"f":Decimal("1e-15")}[m[2]]
    key=lambda a,b,v:(tuple(sorted((a.lower(),b.lower()))),value(v))
    wire=[r for r in parse(root/"wires.spice")if r[0].lower().startswith("r")]
    need(len(wire)==26218 and all(len(r)==4 for r in wire),"actual complete wire resistor census")
    by={r[0].lower():r for r in wire};need(len(by)==26218,"unique native resistor names")
    physical_r=[r for r in distributed if r[0]=="resist"]
    need(Counter(key(*r[1:4])for r in physical_r)==Counter(key(*r[1:4])for r in wire),"all native and exported R endpoints/values/multiplicity equal")
    points=defaultdict(list)
    for row in distributed:
        if row[0]=="rnode":
            need(len(row)==7 and value(row[2])==0 and value(row[3])>=0,"native distributed node record")
            points[row[1].lower()].append(dict(raw_record=row,point_dbu=[int(row[4])*5,int(row[5])*5],type_token=row[6]))
    targets={}
    for query in queries:
        nid,term=query["source_terminal"];label="T"+str(nid).zfill(3)+"_"+term
        anchor=anchors[label];record=next(t for d in comp["device_records"]if int(d["native_id"])==nid for t in d["terminals"]if t["terminal"]==term)
        need(record["anchor"]==label and record["native_cluster"]==anchor["native_cluster"]and record["native_net"]==query["native_net"],"current physical source ownership")
        for edge in query["top_edges"][:3]:
            name=edge["element"];row=by[name]
            mapped=[inverse[edge[x]].lower()for x in("a","b")]
            need(sorted(mapped)==sorted(v.lower()for v in row[1:3])and abs(float(value(row[3]))-edge["resistance_ohm"])<=1e-12*max(1.,edge["resistance_ohm"]),"actual critical resistor binding")
            item=targets.setdefault(name,dict(edge=edge,component=anchor["wire_component"],native_cluster=anchor["native_cluster"],native_net=query["native_net"],queries=[]))
            need(item["component"]==anchor["wire_component"] and item["native_cluster"]==anchor["native_cluster"] and item["native_net"]==query["native_net"],"one physical owner for critical R")
            item["queries"].append(query["label"])
    gp=base/"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds";wp=base/"binding/inputs/wire/native05/wires.l2n"
    g=pya.Layout();g.read(str(gp));top=g.cell(TOP);need(top is not None and g.dbu==.001,"current GDS")
    before=region_snapshot(g,top);w=pya.LayoutToNetlist();w.read(str(wp));need(w.internal_layout().dbu==.001,"wire DBU")
    nets={n.cluster_id:n for n in w.netlist().top_circuit().each_net()}
    layers=(8,19,10,29,30,49,50,66,67,125,126,133,134)
    objects={n:w.layer_by_name("gds_"+str(n))for n in layers}
    for n,layer in objects.items():need(layer is not None and(before.get((n,0),pya.Region())^layer).is_empty(),"all13native conductor unions")
    cache={}
    def owned(component):
        if component not in cache:cache[component]={n:w.shapes_of_net(nets[component],layer,True).merged()for n,layer in objects.items()}
        return cache[component]
    for name,anchor in anchors.items():
        shapes=owned(anchor["wire_component"])
        for kind,ref in (("original",original[name]),("actual_extraction",anchor)):
            x,y=ref["point_dbu"]
            need((box(x,y,1)-shapes[ref["metal"]]).is_empty(),"all actual and original port points on same native owned metal "+name+" "+kind)
    def members(region):
        return [dict(bbox=bounds(pya.Region(p)),area_dbu2=p.area(),hull=[[pt.x,pt.y]for pt in p.each_point_hull()],holes=[[[pt.x,pt.y]for pt in p.each_point_hole(i)]for i in range(p.holes())])for p in region.each()]
    rows=[];corridors=[]
    for name,item in sorted(targets.items()):
        shapes=owned(item["component"]);endpoints=[]
        for role in("a","b"):
            native=inverse[item["edge"][role]];records=points[native.lower()]
            need(records,"native coordinate record for every critical endpoint")
            at=[]
            for r in records:
                x,y=r["point_dbu"];near=box(x,y,2000)
                at.append(dict(**r,layers={str(n):dict(contains_2nm_box=(box(x,y,1)-region).is_empty(),
                    intersects_20nm_box=not region.interacting(box(x,y,10)).is_empty(),
                    owned_local_polygons=members(region&near),
                    foreign_local_polygons=members((objects[n]-region)&near))for n,region in shapes.items()if not(objects[n]&near).is_empty()}))
            endpoints.append(dict(role=role,model_node=item["edge"][role],native_node=native,records=at,original_anchor=original.get(native),extraction_anchor=anchors.get(native)))
        if item["native_net"]=="avss":
            coordinates=[r["point_dbu"]for e in endpoints for r in e["records"]]
            need(len(coordinates)>=2,"all ground resistor endpoint coordinates")
            xs,ys=zip(*coordinates);window=pya.Region(pya.Box(min(xs)-5000,min(ys)-5000,max(xs)+5000,max(ys)+5000))
            corridors.append(dict(element=name,queries=item["queries"],resistance_ohm=item["edge"]["resistance_ohm"],
                component=item["component"],native_cluster=item["native_cluster"],window_bbox=bounds(window),
                endpoint_coordinates=coordinates,
                layers={str(n):dict(owned=members(region&window),foreign=members((objects[n]-region)&window))for n,region in shapes.items()},
                same_net_m1_m2_overlap=members(shapes[8]&shapes[10]&window),
                same_net_m2_m3_overlap=members(shapes[10]&shapes[30]&window),
                no_new_geometry=True,no_via_sizing_or_drc_acceptance=True))
        rows.append(dict(element=name,**item,endpoints=endpoints))
    need(corridors and all(r["queries"]for r in corridors),"all actual ground critical access corridors")
    save("ground-access-corridors.json",dict(status="COMPLETE_CURRENT_SOURCE_AND_SHARED_GROUND_ACCESS_SURVEY",
        input_gds=pin(gp),sensitivity_producer=cfg["critical_resistance_diagnosis"],corridors=corridors,
        all13layers_in_each_window=True,original_geometry_unchanged=True,new_geometry_generated=False,
        physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False,
        limits="Actual same-net overlaps and foreign geometry only. Via dimensions, enclosure, spacing and current density still require separately validated design; no aggregate extracted resistor is assigned to one layer."))
    after=region_snapshot(g,top);need(set(before)==set(after),"same GDS layers")
    for n in before:need((before[n]^after[n]).is_empty(),"unchanged physical material")
    for n in("binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds","binding/inputs/wire/native05/wires.l2n","mim/precise/wire/rc03/pump_wires.ext","mim/precise/wire/rc03/pump_wires.res.ext","mim/precise/wire/rc03/wires.spice","mim/composition/composition.json","mim/precise/wire/anchors08.json"):
        need(pin(base/n)==cfg["complete_members"][n],"actual input unchanged "+n)
    save("critical-access-map.json",dict(status="COMPLETE_ACTUAL_CRITICAL_RESISTOR_COORDINATE_AND_OWNERSHIP_MAP",
        input_gds=pin(gp),sensitivity_proof=pin(ROOT/"scripts/cdr-critical-resistance-inputs.json"),all978port_coordinate_checks=True,all978original_and_extraction_ownership_checks=True,documented_mim_access_relocations=list(changes.values()),
        all26218native_exported_resistors_equal=True,all13native_unions_verified=True,critical_resistors=rows,
        coordinate_interpretation="Original Magic internal5nm coordinate grid independently checked against all978actual extraction anchors; seven previously documented MIM bottom access relocations authenticated and both point sets physically owned. rnode type_token is retained without treating it as a GDS layer; physical layer evidence comes only from native owned geometry.",
        original_geometry_unchanged=True,new_geometry_generated=False,fresh_RC=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False))


def via1_reinforcement_guard(cut,m1,m2,old_vias,new_vias,extent):
    b=bounds(cut);rect=not cut.is_empty()and cut.count()==1 and b[2]-b[0]==190 and b[3]-b[1]==190 and cut.area()==36100
    return dict(square190=rect,grid5=rect and all(v%5==0 for v in b),
        enclosed_m1_50=(cut.sized(50,50,2)-m1).is_empty(),
        enclosed_m2_50=(cut.sized(50,50,2)-m2).is_empty(),
        existing_via_clearance240=(cut&old_vias.sized(240,240,2)).is_empty(),
        new_via_clearance240=(cut&new_vias.sized(240,240,2)).is_empty(),
        within_original_extent=(cut-extent).is_empty())

def via1_reinforcement_controls():
    extent=pya.Region(pya.Box(0,0,4000,4000));metal=pya.Region(pya.Box(500,0,1500,3000));cut=box(1000,1000,95);empty=pya.Region()
    need(all(via1_reinforcement_guard(cut,metal,metal,empty,empty,extent).values()),"valid via1 reinforcement")
    narrow=pya.Region(pya.Box(855,0,1145,3000))
    need(all(via1_reinforcement_guard(cut,narrow,narrow,empty,empty,extent).values()),"exact290nm existing overlap allowed")
    cases=[
        ("wrong-size",box(1000,1000,90),metal,metal,empty,empty,extent),
        ("off-grid",box(1001,1000,95),metal,metal,empty,empty,extent),
        ("missing-m1",cut,empty,metal,empty,empty,extent),
        ("missing-m2",cut,metal,empty,empty,empty,extent),
        ("short-enclosure",cut,pya.Region(pya.Box(856,0,1145,3000)),metal,empty,empty,extent),
        ("old-via-spacing",cut,metal,metal,box(1410,1000,95),empty,extent),
        ("new-via-spacing",cut,metal,metal,empty,box(1410,1000,95),extent),
        ("outside-layout",cut,metal,metal,empty,empty,pya.Region(pya.Box(0,0,900,4000)))]
    passed=["valid190nm via","exact existing290nm overlap"]
    for name,*args in cases:
        need(not all(via1_reinforcement_guard(*args).values()),"reject "+name)
        passed.append("reject "+name)
    return passed

def generate_via1_reinforcement(base,cfg):
    proof=json.loads((ROOT/"scripts/cdr-critical-resistance-inputs.json").read_bytes())
    need(proof["run"]==41407813062 and proof["source"]=="fafb2d0be139a44b3c70b449dfc182c5b9f171b0","actual current32query diagnosis")
    targets={}
    for q in proof["queries"]:
        for key in("source_terminal","sink_terminal"):
            pair=q[key]
            if pair=="public_avss":continue
            i,t=pair;label="T"+str(i).zfill(3)+"_"+t
            record=dict(device=i,terminal=t,native_net=q["native_net"])
            need(label not in targets or targets[label]==record,"consistent terminal net identity")
            targets[label]=record
    need(len(targets)==28,"all28critical native terminals")
    gp=base/"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds";wp=base/"binding/inputs/wire/native05/wires.l2n"
    need(pin(gp)==dict(bytes=1003860,sha256="4ccf1212d4b98046b1b56037bb1b76c53477777b08ee9cba5053c8e6323203e8"),"current actually measured layout")
    g=pya.Layout();g.read(str(gp));top=g.cell(TOP);need(g.dbu==.001 and top is not None,"actual current layout")
    before=region_snapshot(g,top);extent=pya.Region(top.bbox())
    w=pya.LayoutToNetlist();w.read(str(wp));need(w.internal_layout().dbu==.001,"actual native wire DBU")
    layers=(8,19,10,29,30,49,50,66,67,125,126,133,134)
    objects={n:w.layer_by_name("gds_"+str(n))for n in layers}
    for n,r in objects.items():need(r is not None and(before.get((n,0),pya.Region())^r).is_empty(),"all13actual native conductor unions")
    nets={n.cluster_id:n for n in w.netlist().top_circuit().each_net()}
    anchors={a["label"]:a for a in json.loads((base/"mim/precise/wire/anchors08.json").read_bytes())["anchors"]}
    old_vias=pya.Region()
    for (layer,datatype),r in before.items():
        if layer==19:old_vias+=r
    old_vias=old_vias.merged()
    cache={}
    def owned(component):
        if component not in cache:cache[component]={n:w.shapes_of_net(nets[component],r,True).merged()for n,r in objects.items()}
        return cache[component]
    additions=pya.Region();sites=[];rows=[];positions=set()
    for label,expected in sorted(targets.items()):
        a=anchors[label]
        need(a["detail"]["device"]==expected["device"]and a["detail"]["native_net"]==expected["native_net"],"actual critical terminal owner")
        shapes=owned(a["wire_component"]);x,y=a["point_dbu"]
        need((box(x,y,1)-shapes[a["metal"]]).is_empty(),"actual port inside its own physical conductor")
        window=box(x,y,25000);overlap=(shapes[8]&shapes[10]&window).merged()
        ox,oy=((x+2)//5)*5,((y+2)//5)*5
        need(abs(ox-x)<=2 and abs(oy-y)<=2,"placement grid reference only; original anchor unchanged")
        tested=0;admitted=0
        for polygon in overlap.each():
            b=polygon.bbox();lo_x,hi_x=b.left+145,b.right-145;lo_y,hi_y=b.bottom+145,b.top-145
            first_x=ox+((lo_x-ox+479)//480)*480
            first_y=oy+((lo_y-oy+479)//480)*480
            for cx in range(first_x,hi_x+1,480):
                for cy in range(first_y,hi_y+1,480):
                    if (cx,cy)in positions:continue
                    tested+=1;cut=box(cx,cy,95)
                    guards=via1_reinforcement_guard(cut,shapes[8],shapes[10],old_vias,additions,extent)
                    if not all(guards.values()):continue
                    additions+=cut;positions.add((cx,cy));admitted+=1
                    sites.append(dict(center_dbu=[cx,cy],bbox=bounds(cut),component=a["wire_component"],native_cluster=a["native_cluster"],
                        native_net=a["detail"]["native_net"],selected_by=label,guards=guards))
        rows.append(dict(label=label,original_anchor=a,window_bbox=bounds(window),grid_reference_dbu=[ox,oy],
            same_net_overlap_area_dbu2=overlap.area(),tested_sites=tested,added_in_this_pass=admitted))
    additions=additions.merged()
    for row in rows:
        b=row["window_bbox"];component=row["original_anchor"]["wire_component"]
        row["all_new_sites_in_window"]=[s["center_dbu"]for s in sites if s["component"]==component and b[0]+145<=s["center_dbu"][0]<=b[2]-145 and b[1]+145<=s["center_dbu"][1]<=b[3]-145]
    drains={"T"+str(i).zfill(3)+"_D"for i in(3,4,5,6,32,33,34,35)}
    coverage={r["label"]:len(r["all_new_sites_in_window"])for r in rows if r["label"]in drains}
    save("via1-reinforcement-proposal.json",dict(targets=rows,sites=sites,requested_terminals=28,
        cut_nm=190,pitch_nm=480,metal_enclosure_nm=50,minimum_existing_new_spacing_nm=240,
        required_drain_coverage=coverage,only_added_layer=[19,0],physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False))
    need(set(coverage)==drains and all(n>=4 for n in coverage.values()),"at least four additional local same-net vias for each of eight actual MOS drains")
    need(len(sites)>0 and additions.count()==len(sites)and additions.area()==len(sites)*36100,"all exact disjoint190nm cuts")
    need((additions&old_vias.sized(240,240,2)).is_empty(),"whole candidate original via spacing")
    handles=[top.shapes(g.layer(19,0)).insert(poly)for poly in additions.each()]
    NATIVE.mkdir();candidate=NATIVE/"nssoc_cdr_pd500_via1_reinforced.gds";g.write(str(candidate))
    readback=pya.Layout();readback.read(str(candidate));after=region_snapshot(readback,readback.cell(TOP))
    need(readback.dbu==g.dbu and{c.name for c in readback.each_cell()}=={c.name for c in g.each_cell()},"serialized original hierarchy")
    for layer in set(before)|set(after):
        expected=before.get(layer,pya.Region())
        if layer==(19,0):expected=(expected+additions).merged()
        need((expected^after.get(layer,pya.Region())).is_empty(),"exact sole Via1 delta "+str(layer))
    for handle in reversed(handles):handle.delete()
    reverted=region_snapshot(g,top);need(set(before)==set(reverted),"original layer set after reversal")
    for layer in before:need((before[layer]^reverted[layer]).is_empty(),"exact original geometry after reversal")
    need(pin(gp)==cfg["complete_members"]["binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds"],"unchanged source GDS bytes")
    save("via1-reinforcement-generation-proof.json",dict(candidate=pin(candidate),input_gds=pin(gp),input_l2n=pin(wp),
        terminal_count=28,new_via1_count=len(sites),only_added_layer=[19,0],total_added_area_dbu2=additions.area(),
        exact_serialized_delta=True,original_material_roundtrip=True,new_devices=False,new_metal=False,
        all_new_cuts_on_same_owned_m1_m2=True,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False,
        current_density_acceptance=False,requires=["full560DRC","deep_flat_LVS13","current_canonical_binding","fresh_RC","unchanged_loaded_wave_gates","actual_via_current_distribution"]))

def source_m2_guard(metal,owned_m2,foreign_m2,foreign_via1,foreign_via2,extent):
    return dict(nonempty=not metal.is_empty(),
        grid5=all(v%5==0 for poly in metal.each()for point in poly.each_point_hull()for v in(point.x,point.y)),
        connected_existing_m2=not(metal&owned_m2).is_empty(),
        foreign_m2_clearance240=(metal&foreign_m2.sized(240,240,2)).is_empty(),
        foreign_via1_clearance50=(metal&foreign_via1.sized(50,50,2)).is_empty(),
        foreign_via2_clearance50=(metal&foreign_via2.sized(50,50,2)).is_empty(),
        within_original_extent=(metal-extent).is_empty())

def source_m2_controls():
    metal=pya.Region(pya.Box(0,0,1400,20000))
    owned=pya.Region(pya.Box(0,0,300,300));empty=pya.Region();extent=pya.Region(pya.Box(-1000,-1000,4000,22000))
    args=[metal,owned,empty,empty,empty,extent]
    need(all(source_m2_guard(*args).values()),"valid attached source M2 bypass")
    passed=["valid source M2 attachment"]
    tests=[("no-metal",0,empty),("no-attachment",1,empty),
      ("off-grid",0,pya.Region(pya.Box(1,0,1400,20000))),
      ("foreign-metal",2,pya.Region(pya.Box(1600,0,1900,20000))),
      ("foreign-via1",3,box(1400,10000,95)),
      ("foreign-via2",4,box(1400,10000,95)),
      ("outside-original-extent",5,pya.Region(pya.Box(0,0,1000,20000)))]
    for name,index,value in tests:
        changed=list(args);changed[index]=value
        need(not all(source_m2_guard(*changed).values()),"refuse "+name)
        passed.append("refuse "+name)
    return passed

def generate_source_m2_bypass(base,cfg):
    gp=base/"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds"
    wp=base/"binding/inputs/wire/native05/wires.l2n"
    need(pin(gp)==dict(bytes=1003860,sha256="4ccf1212d4b98046b1b56037bb1b76c53477777b08ee9cba5053c8e6323203e8"),"actual loaded rejected source-M1 input")
    g=pya.Layout();g.read(str(gp));top=g.cell(TOP)
    need(g.dbu==.001 and top is not None,"actual GDS1nm database")
    before=region_snapshot(g,top);extent=pya.Region(top.bbox())
    w=pya.LayoutToNetlist();w.read(str(wp));need(w.internal_layout().dbu==.001,"actual native wire1nm database")
    layers=(8,19,10,29,30,49,50,66,67,125,126,133,134)
    objects={n:w.layer_by_name("gds_"+str(n))for n in layers}
    for n,r in objects.items():
        need(r is not None and(before.get((n,0),pya.Region())^r).is_empty(),"all13native input conductor unions")
    nets={n.cluster_id:n for n in w.netlist().top_circuit().each_net()}
    anchors={a["label"]:a for a in json.loads((base/"mim/precise/wire/anchors08.json").read_bytes())["anchors"]}
    proof=json.loads((ROOT/"scripts/cdr-critical-resistance-inputs.json").read_bytes())
    need(proof["run"]==41407813062 and proof["source"]=="fafb2d0be139a44b3c70b449dfc182c5b9f171b0","actual current32query resistance diagnosis")
    queries={tuple(q["source_terminal"]):q for q in proof["queries"]if q["sink_terminal"]=="public_avss"}
    need(set(queries)=={(i,"S")for i in(3,4,5,6,32,33,34,35)},"all8actual source ground queries")
    components={anchors["T"+str(i).zfill(3)+"_S"]["wire_component"]for i,_ in queries}
    need(len(components)==1,"one original ground wire component")
    component=next(iter(components))
    own={n:w.shapes_of_net(nets[component],r,True).merged()for n,r in objects.items()}
    all_vias={n:pya.Region()for n in(19,29)}
    for (layer,datatype),r in before.items():
        if layer in all_vias:all_vias[layer]+=r
    all_vias={n:r.merged()for n,r in all_vias.items()}
    additions={n:pya.Region()for n in(10,19,29)};rows=[]
    for i,t in sorted(queries):
        label="T"+str(i).zfill(3)+"_S";a=anchors[label];x,y=a["point_dbu"]
        need(a["metal"]==8 and a["detail"]["device"]==i and a["detail"]["native_net"]=="avss"
             and queries[(i,t)]["native_net"]=="avss","actual native source ground identity")
        need((box(x,y,1)-own[8]).is_empty(),"original source anchor physically owned")
        top_patch=pya.Region(pya.Box(x-1645,y-2000,x-145,y+2000))
        need((top_patch-own[8]).is_empty(),"entire actual prior1500x4000nm source-M1 landing")
        # The landing exactly joins the existing original290nm M2/M3 access.
        column=pya.Region(pya.Box(x-1595,y-17800,x-195,y+2000))
        landing=pya.Region(pya.Box(x-1595,y-17745,x+145,y-17455))
        metal=(column+landing).merged()
        guards=source_m2_guard(metal,own[10],objects[10]-own[10],all_vias[19]-own[19],all_vias[29]-own[29],extent)
        row=dict(label=label,original_anchor=a,metal_bbox=bounds(metal),metal_polygons=[
            [[p.x,p.y]for p in poly.each_point_hull()]for poly in metal.each()],
            metal_guards=guards,via1=[],via2=[])
        rows.append(row)
        save("source-m2-bypass-progress/"+label+"-metal.json",dict(input_gds=pin(gp),target=row,complete=False,physical_acceptance=False,full_phy_accepted=False))
        need(all(guards.values()),"source M2 full same-net attachment/foreign-spacing guards "+label)
        future_m2=(own[10]+additions[10]+metal).merged()
        for layer,ys,lower,upper in (
            (19,range(y-1680,y+1681,480),own[8],future_m2),
            (29,[y-17600],future_m2,own[30])):
            for cx in (x-1450,x-970,x-490):
                for cy in ys:
                    cut=box(cx,cy,95)
                    checks=via1_reinforcement_guard(cut,lower,upper,all_vias[layer],additions[layer],extent)
                    record=dict(center_dbu=[cx,cy],bbox=bounds(cut),guards=checks,
                        lower_owned_layer=8 if layer==19 else 10,upper_owned_layer=10 if layer==19 else 30,
                        original_wire_component=component,native_net="avss")
                    row["via1"if layer==19 else"via2"].append(record)
                    save("source-m2-bypass-progress/"+label+"-"+str(layer)+"-"+str(cx)+"-"+str(cy)+".json",dict(input_gds=pin(gp),label=label,cut=record,complete=False,physical_acceptance=False,full_phy_accepted=False))
                    need(all(checks.values()),"same-net enclosed190nm cut/240nm spacing "+label+" layer"+str(layer))
                    additions[layer]+=cut
        need(len(row["via1"])==24 and len(row["via2"])==3,"all24source and3ground access cuts")
        additions[10]+=metal
    for n in additions:additions[n]=additions[n].merged()-before.get((n,0),pya.Region())
    need(additions[19].count()==192 and additions[29].count()==24,"all8actual new via arrays")
    need(additions[19].area()==192*36100 and additions[29].area()==24*36100,"exact disjoint190nm cuts")
    handles=[]
    for n,r in additions.items():
        need(not r.is_empty(),"actual nonempty layer addition")
        for poly in r.each():handles.append(top.shapes(g.layer(n,0)).insert(poly))
    NATIVE.mkdir();candidate=NATIVE/"nssoc_cdr_pd500_source_m2_bypass.gds";g.write(str(candidate))
    readback=pya.Layout();readback.read(str(candidate));after=region_snapshot(readback,readback.cell(TOP))
    need(readback.dbu==g.dbu and{c.name for c in readback.each_cell()}=={c.name for c in g.each_cell()},"serialized original hierarchy")
    for key in set(before)|set(after):
        expected=before.get(key,pya.Region())
        if key[1]==0 and key[0]in additions:expected=(expected+additions[key[0]]).merged()
        need((expected^after.get(key,pya.Region())).is_empty(),"only exact newM2/Via1/Via2 material "+str(key))
    for handle in reversed(handles):handle.delete()
    reverted=region_snapshot(g,top);need(set(before)==set(reverted),"original layer set after reversal")
    for key in before:need((before[key]^reverted[key]).is_empty(),"exact original material reversal")
    need(pin(gp)==cfg["complete_members"]["binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds"],"source GDS bytes unchanged")
    save("source-m2-bypass-proposal.json",dict(input_gds=pin(gp),targets=rows,complete=True,
        new_via1_count=192,new_via2_count=24,metal_width_nm=1400,metal_foreign_clearance_nm=240,
        via_cut_nm=190,via_pitch_nm=480,via_metal_enclosure_nm=50,via_spacing_nm=240,
        physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False))
    save("source-m2-bypass-generation-proof.json",dict(candidate=pin(candidate),input_gds=pin(gp),input_l2n=pin(wp),
        all8actual_source_ground_accesses=True,all13native_unions_verified=True,
        added_area_dbu2={str(n):r.area()for n,r in additions.items()},
        only_added_layers=[[10,0],[19,0],[29,0]],exact_serialized_delta=True,original_material_roundtrip=True,
        new_devices=False,all_new_access_owned_by_original_avss=True,physical_acceptance=False,
        full_phy_accepted=False,final_timing_complete=False,current_density_acceptance=False,
        electrical_improvement_claimed=False,requires=["full560DRC","deep_flat_LVS13","current_canonical_binding",
          "fresh_RC","unchanged_loaded_wave_gates","actual_via_current_distribution","bias_headroom_review"]))

def main():
    if sys.argv[1:]==["--publish"]:publish();return
    try:
        cfg=gate();passed=controls()+direct_m2_controls()+refined_m1_controls()+mixed_controls()+maze_controls()+ground_strap_controls()+horizontal_ground_controls()+horizontal_clearance_controls()+via1_reinforcement_controls()+source_m2_controls();save("controls.json",dict(count=len(passed),passed=passed))
        if sys.argv[1:]==["--controls"]:return
        need(sys.argv[1:]in(["--generate"],["--inspect-access"],["--generate-mixed"],["--inspect-current-rails"],["--generate-ground-strap"],["--inspect-ground-topology"],["--generate-horizontal-ground"],["--inspect-critical-access"],["--generate-via1-reinforcement"],["--generate-source-m2-bypass"]),"explicit native operation")
        reserve(wait=True)
        base=acquire_current(cfg)
        if sys.argv[1:]==["--generate-source-m2-bypass"]:
            generate_source_m2_bypass(base,cfg)
            save("result.json",dict(status="GENERATED_ACTUAL_SOURCE_M2_BYPASS_REQUIRES_FULL_QUALIFICATION",physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False))
            return
        if sys.argv[1:]==["--generate-via1-reinforcement"]:
            generate_via1_reinforcement(base,cfg)
            save("result.json",dict(status="GENERATED_ACTUAL_SAME_NET_VIA1_REINFORCEMENT_REQUIRES_FULL_QUALIFICATION",physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False))
            return
        if sys.argv[1:]==["--inspect-critical-access"]:
            inspect_critical_access(base,cfg)
            save("result.json",dict(status="COMPLETE_CURRENT_CRITICAL_ACCESS_MAP",read_only=True,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False))
            return
        if sys.argv[1:]==["--generate-horizontal-ground"]:
            generate_horizontal_ground(base,cfg)
            save("result.json",dict(status="GENERATED_ACTUAL_HORIZONTAL_GROUND_BRANCHES_REQUIRES_NATIVE_QUALIFICATION",physical_acceptance=False,full_phy_accepted=False))
            return
        if sys.argv[1:]==["--inspect-ground-topology"]:
            inspect_ground_topology(base,cfg)
            save("result.json",dict(status="COMPLETE_CURRENT_NATIVE_GROUND_STACK_TOPOLOGY",physical_acceptance=False,full_phy_accepted=False))
            return
        if sys.argv[1:]==["--generate-ground-strap"]:
            generate_ground_strap(base,cfg)
            save("result.json",dict(status="GENERATED_ACTUAL_M5_GROUND_STRAP_REQUIRES_NATIVE_QUALIFICATION",physical_acceptance=False,full_phy_accepted=False))
            return
        if sys.argv[1:]==["--inspect-current-rails"]:
            inspect_current_rails(base,cfg)
            save("result.json",dict(status="COMPLETE_CURRENT_NATIVE_AVSS_ACCESS_INSPECTION",physical_acceptance=False,full_phy_accepted=False))
            return
        if sys.argv[1:]==["--inspect-access"]:
            inspect_access(base,cfg)
            save("result.json",dict(status="NATIVE_EXISTING_STACK_INSPECTION_ONLY",physical_acceptance=False,full_phy_accepted=False))
            return
        if sys.argv[1:]==["--generate-mixed"]:
            mixed_generate(base,cfg)
            save("result.json",dict(status="GENERATED_FOUR_MIXED_LAYER_SHORTCUTS_REQUIRES_NATIVE_QUALIFICATION",physical_acceptance=False,full_phy_accepted=False))
            return
        generate(base,cfg)
        save("result.json",dict(status="GENERATED_FOUR_CLOCK_SELECTOR_SHORTCUTS_REQUIRES_DRC_LVS_RC_WAVES",physical_acceptance=False,full_phy_accepted=False))
    except Exception as exc:
        save("failure.json",dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc(),physical_acceptance=False));raise
if __name__=="__main__":main()
