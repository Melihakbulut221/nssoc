#!/usr/bin/env python3
"""Generate four physical clock-selector shortcuts from measured same-net voltage loss."""
import ast,hashlib,importlib.metadata,json,os,re,subprocess,sys,tarfile,traceback
from pathlib import Path
import klayout.db as pya
import cloud_cdr_wire_geometry_acquire as prior
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"wire-tail-shortcuts";NATIVE=ROOT/"wire-tail-shortcuts-native"
MANIFEST="scripts/cdr-wire-tail-shortcuts-pins.json";INPUT="scripts/cdr-wire-tail-shortcuts-inputs.json"
BRANCH="codex/cdr-wire-tail-shortcuts";TOP="nssoc_cdr_pd500_resistor_v59"
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
    selected={"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds","binding/inputs/wire/native05/wires.l2n","binding/inputs/wire/native05/wires.gds","binding/inputs/wire/anchors08.json","mim/composition/composition.json","fresh-rc-qualification.json"}
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
    need(q["status"]=="PASS_SIX_SHORTCUT_FRESH_RC_NUMERICAL_QUALIFICATION_REQUIRES_LOADED_WAVES"and q["fresh_RC_executed"],"actual current RC qualification")
    need(pin(target/"binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds")==dict(bytes=999700,sha256="244992e91350d3bcac15fd58c48cc5249ee615ffc21f30f539a0cbb6b42fc347"),"actual six-shortcut GDS baseline")
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

def main():
    if sys.argv[1:]==["--publish"]:publish();return
    try:
        cfg=gate();passed=controls()+direct_m2_controls()+refined_m1_controls()+mixed_controls();save("controls.json",dict(count=len(passed),passed=passed))
        if sys.argv[1:]==["--controls"]:return
        need(sys.argv[1:]in(["--generate"],["--inspect-access"],["--generate-mixed"]),"explicit native operation")
        reserve(wait=True)
        base=acquire_current(cfg)
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
