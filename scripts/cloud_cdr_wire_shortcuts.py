#!/usr/bin/env python3
"""Generate conservative physical M2/Via1 shortcuts on six actual divider nets."""
import hashlib,importlib.metadata,json,os,re,subprocess,sys,tarfile,traceback
from pathlib import Path
import klayout.db as pya
import cloud_cdr_wire_geometry_acquire as prior
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"wire-shortcuts";NATIVE=ROOT/"wire-shortcuts-native"
MANIFEST="scripts/cdr-wire-shortcuts-pins.json";INPUT="scripts/cdr-wire-shortcuts-inputs.json"
BRANCH="codex/cdr-wire-shortcuts";TOP="nssoc_cdr_pd500_resistor_v59"
LAYERS=(8,19,10,29)
TARGETS=(("A_p",227,228),("A_n",229,230),("C_p",238,239),("C_n",240,241),("D_p",234,235),("D_n",236,237))
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
    anchors=json.loads((base/"mim/precise/wire/anchors08.json").read_bytes())
    physical={a["label"]:a for a in anchors["anchors"]}
    proposals=[];inserted=[];additions={n:pya.Region()for n in(10,19)}
    for label,series,shunt in TARGETS:
        a=physical["T%03d_rppd_2"%series];b=physical["T%03d_rppd_1"%shunt]
        need(a["wire_component"]==b["wire_component"]and a["native_cluster"]==b["native_cluster"],"same native conductor")
        component=a["wire_component"];need(component in nets,"actual L2N component")
        owned={n:w.shapes_of_net(nets[component],objects[n],True).merged()for n in LAYERS}
        current={n:(full[n]+additions.get(n,pya.Region())).merged()for n in LAYERS}
        aa,ar=access(a,owned,current,other);bb,br=access(b,owned,current,other)
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
    NATIVE.mkdir();candidate=NATIVE/"nssoc_cdr_pd500_wire_shortcuts.gds";g.write(str(candidate))
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
    need(len(adopted)==len(TARGETS),"partial physical candidate preserved; not all six paths routed")
def publish():
    cfg=gate();e=os.environ;tag="cloud-results-"+e["GITHUB_RUN_ID"]+"-1-cdr-wire-shortcuts"
    release=prior.api("releases/tags/"+tag)
    need(release["target_commitish"]==e["GITHUB_SHA"]and not release["assets"],"empty exact-source reservation")
    need(prior.api("git/ref/tags/"+tag)["object"]["sha"]==e["GITHUB_SHA"],"reserved tag")
    files={}
    for root,prefix in ((OUT,"derived"),(NATIVE,"native")):
        if root.exists():
            for p in sorted(root.rglob("*")):
                need(not p.is_symlink(),"regular output")
                if p.is_file():files[prefix+"/"+str(p.relative_to(root))]=p
    need(files,"success/failure evidence")
    pub=ROOT/"wire-shortcuts-publication";pub.mkdir()
    index=dict(context=dict(run=int(e["GITHUB_RUN_ID"]),attempt=1,source=e["GITHUB_SHA"]),files={n:pin(p)for n,p in files.items()})
    (pub/"complete-output-index.json").write_bytes(encode(index))
    archive=pub/"native-candidate.tar.gz"
    with tarfile.open(archive,"w:gz")as tar:
        for n,p in files.items():tar.add(p,arcname="wire-shortcuts/"+n,recursive=False)
    subprocess.run(["gh","release","upload",tag,str(pub/"complete-output-index.json"),str(archive),"--repo","Melihakbulut221/nssoc"],check=True)
    assets=prior.api("releases/"+str(release["id"]))["assets"]
    for p in (pub/"complete-output-index.json",archive):
        a=next(a for a in assets if a["name"]==p.name);need(a["size"]==p.stat().st_size and a["digest"]=="sha256:"+prior.digest(p),"published exact digest")
    save("publication.json",dict(tag=tag,release=release["id"],assets=assets,original_inputs_remain_in_release=cfg["release_id"]))
def main():
    if sys.argv[1:]==["--publish"]:publish();return
    try:
        cfg=gate();passed=controls();save("controls.json",dict(count=len(passed),passed=passed))
        if sys.argv[1:]==["--controls"]:return
        need(sys.argv[1:]==["--generate"],"explicit generation")
        base=prior.acquire(cfg);generate(base,cfg)
        save("result.json",dict(status="GENERATED_SIX_PHYSICAL_SHORTCUTS_REQUIRES_DRC_LVS_RC_WAVES",physical_acceptance=False,full_phy_accepted=False))
    except Exception as exc:
        save("failure.json",dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc(),physical_acceptance=False));raise
if __name__=="__main__":main()
