#!/usr/bin/env python3
"""Cloud-only fresh native canonical wire view for the physically verified current horizontal-ground GDS."""
import argparse,contextlib,hashlib,json,os,shutil,signal,subprocess,sys,tarfile,threading,traceback
from pathlib import Path,PurePosixPath
import cdr_via2_m3_canonical_core as core
import cdr_v59_tail_access_runtime as runtime
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"hw/soc/out/cloud-cdr-wire-shortcuts-canonical"
BRANCH="codex/cdr-clock-access-canonical"
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

def source_m2_variant(pya,original,row):
    a=row["original_anchor"]
    need(a["metal"]==8 and a["wire_component"]==14 and a["native_cluster"]==24
         and a["detail"]["native_net"]=="avss","actual original source ground owner")
    x,y=a["point_dbu"];need(type(x)is int and type(y)is int and x%5==0 and y%5==0,"actual source grid")
    box=lambda coords:pya.Region(pya.Box(*coords))
    need((box([x-1,y-1,x+1,y+1])-original[8]).is_empty(),"original source point on owned Metal1")
    need((box([x-1645,y-2000,x-145,y+2000])-original[8]).is_empty(),"actual entire M1 landing")
    metal=(box([x-1595,y-17800,x-195,y+2000])+box([x-1595,y-17745,x+145,y-17455])).merged()
    b=metal.bbox();need(row["metal_bbox"]==[b.left,b.bottom,b.right,b.top],"independently reconstructed M2 bounds")
    declared=pya.Region()
    for points in row["metal_polygons"]:
        need(len(points)>=4 and all(len(pt)==2 and all(type(v)is int and v%5==0 for v in pt)for pt in points),"exact grid polygon points")
        declared.insert(pya.Polygon([pya.Point(*pt)for pt in points]))
    need((declared^metal).is_empty(),"actual M2 polygon equals independent reconstruction")
    need(not(metal&original[10]).is_empty(),"new M2 joins actual same-net old M2")
    metal_keys={"nonempty","grid5","connected_existing_m2","foreign_m2_clearance240","foreign_via1_clearance50","foreign_via2_clearance50","within_original_extent"}
    need(set(row["metal_guards"])==metal_keys and all(v is True for v in row["metal_guards"].values()),"complete actual M2 admission")
    via_keys={"square190","grid5","enclosed_m1_50","enclosed_m2_50","existing_via_clearance240","new_via_clearance240","within_original_extent"}
    result={10:metal}
    for layer,name,ys,lower_layer,upper_layer in (
        (19,"via1",range(y-1680,y+1681,480),8,10),
        (29,"via2",[y-17600],10,30)):
        expected={(cx,cy)for cx in(x-1450,x-970,x-490)for cy in ys}
        records=row[name]
        need(len(records)==len(expected)and {tuple(v["center_dbu"])for v in records}==expected,"exact independently positioned via array")
        cuts=pya.Region()
        lower=(original[10]+metal).merged()if lower_layer==10 else original[lower_layer]
        upper=(original[10]+metal).merged()if upper_layer==10 else original[upper_layer]
        for v in records:
            cx,cy=v["center_dbu"]
            need(v["bbox"]==[cx-95,cy-95,cx+95,cy+95],"exact190nm cut bounds")
            need(v["lower_owned_layer"]==lower_layer and v["upper_owned_layer"]==upper_layer
                 and v["original_wire_component"]==14 and v["native_net"]=="avss","actual via joins only declared same-net adjacent metals")
            need(set(v["guards"])==via_keys and all(k is True for k in v["guards"].values()),"complete actual via admission")
            cut=box(v["bbox"]);enclosed=cut.sized(50,50,2)
            need((enclosed-lower).is_empty()and(enclosed-upper).is_empty(),"independent actual both-metal enclosure")
            need((cut&original[layer].sized(240,240,2)).is_empty()
                 and(cut&cuts.sized(240,240,2)).is_empty(),"independent old/new via spacing")
            cuts+=cut
        cuts=cuts.merged()
        need(cuts.count()==len(expected)and cuts.area()==len(expected)*36100,"exact disjoint via material")
        result[layer]=cuts
    return result

def source_m2_layers(pya,original,rows):
    need(len(rows)==8 and len({r["label"]for r in rows})==8,"all8unique M2 sources")
    result={n:pya.Region()for n in(10,19,29)}
    for row in rows:
        shapes=source_m2_variant(pya,original,row)
        for layer,region in shapes.items():result[layer]+=region
    for layer in result:result[layer]=result[layer].merged()-original[layer]
    need(result[19].count()==192 and result[29].count()==24,"all216actual cuts")
    need({str(n):r.area()for n,r in result.items()}=={"10":221876000,"19":6931200,"29":866400},"exact actual added areas")
    return result

def source_m2_delta_controls(pya):
    import copy
    x,y=10000,20000
    original={n:pya.Region()for n in(8,10,19,29,30)}
    original[8]=pya.Region(pya.Box(x-1645,y-2000,x+145,y+2000))
    original[10]=pya.Region(pya.Box(x-145,y-17745,x+145,y-17455))
    original[30]=pya.Region(pya.Box(x-20000,y-17800,x+200,y-17400))
    metal=(pya.Region(pya.Box(x-1595,y-17800,x-195,y+2000))+pya.Region(pya.Box(x-1595,y-17745,x+145,y-17455))).merged()
    row=dict(label="T003_S",original_anchor=dict(metal=8,wire_component=14,native_cluster=24,detail=dict(native_net="avss"),point_dbu=[x,y]),
        metal_bbox=[x-1595,y-17800,x+145,y+2000],
        metal_polygons=[[[p.x,p.y]for p in poly.each_point_hull()]for poly in metal.each()],
        metal_guards={k:True for k in("nonempty","grid5","connected_existing_m2","foreign_m2_clearance240","foreign_via1_clearance50","foreign_via2_clearance50","within_original_extent")})
    for layer,name,ys,lo,hi in((19,"via1",range(y-1680,y+1681,480),8,10),(29,"via2",[y-17600],10,30)):
        row[name]=[dict(center_dbu=[cx,cy],bbox=[cx-95,cy-95,cx+95,cy+95],
            lower_owned_layer=lo,upper_owned_layer=hi,original_wire_component=14,native_net="avss",
            guards={k:True for k in("square190","grid5","enclosed_m1_50","enclosed_m2_50","existing_via_clearance240","new_via_clearance240","within_original_extent")})
            for cx in(x-1450,x-970,x-490)for cy in ys]
    value=source_m2_variant(pya,original,row)
    need(value[19].count()==24 and value[29].count()==3,"independent27cut source reconstruction")
    cases=["independent owned M2 and27via reconstruction"]
    for name in("metal-box","metal-polygons","via-center","via-box","missing-via","duplicate-via",
                "failed-metal-guard","failed-via-guard","missing-via-guard","owner",
                "missing-M1","missing-M2","missing-M3","preexisting-via"):
        bad=copy.deepcopy(row);ref=dict(original)
        if name=="metal-box":bad["metal_bbox"][0]-=5
        elif name=="metal-polygons":bad["metal_polygons"][0][0][0]-=5
        elif name=="via-center":bad["via1"][0]["center_dbu"][0]+=5
        elif name=="via-box":bad["via1"][0]["bbox"][0]-=5
        elif name=="missing-via":bad["via1"].pop()
        elif name=="duplicate-via":bad["via2"][0]=copy.deepcopy(bad["via2"][1])
        elif name=="failed-metal-guard":bad["metal_guards"]["foreign_m2_clearance240"]=False
        elif name=="failed-via-guard":bad["via1"][0]["guards"]["square190"]=False
        elif name=="missing-via-guard":bad["via2"][0]["guards"].pop("enclosed_m2_50")
        elif name=="owner":bad["original_anchor"]["wire_component"]=13
        elif name=="missing-M1":ref[8]=pya.Region()
        elif name=="missing-M2":ref[10]=pya.Region()
        elif name=="missing-M3":ref[30]=pya.Region()
        elif name=="preexisting-via":ref[19]=pya.Region(pya.Box(*bad["via1"][0]["bbox"]))
        try:source_m2_variant(pya,ref,bad)
        except AssertionError:cases.append("reject sourceM2 "+name)
        else:raise AssertionError(name)
    need(len(cases)==15,"all15sourceM2 controls")
    return cases


def drain_m23_variant(pya,original,row):
    a=row["original_anchor"];detail=a["detail"];i=detail["device"]
    need(type(i)is int and i in(3,4,5,6,32,33,34,35),"actual eight native drain devices")
    need(row["label"]==a["label"]=="T"+str(i).zfill(3)+"_D"and detail["terminal"]=="D"and a["metal"]==8,"actual drain label terminal and layer")
    need(a["wire_component"]==row["wire_component"]and detail["native_net"]==row["native_net"]==("$159"if i<10 else"$700"),"actual original emitter net ownership")
    x,y=a["point_dbu"];need(type(x)is int and type(y)is int and x%5==0 and y%5==0,"actual original drain grid")
    box=lambda b:pya.Region(pya.Box(*b))
    need((box([x-1,y-1,x+1,y+1])-original[8]).is_empty(),"original drain on owned Metal1")
    for layer in(10,30):
        for cy in(y,y+17600):need((box([x-1,cy-1,x+1,cy+1])-original[layer]).is_empty(),"both original same-net lower and upper metal attachments")
    coords=[x-150,y-200,x+1250,y+17800]
    need(row["metal_bbox"]==coords,"independent actual M2 and M3 rectangle")
    metal=box(coords)
    metal_keys={"nonempty","grid5","connected_existing_m2","foreign_m2_clearance240","foreign_via1_clearance50","foreign_via2_clearance50","within_original_extent"}
    need(set(row["metal_guards"])=={"10","30"},"both actual metal admissions")
    for layer,lo,hi in(("10",19,29),("30",29,49)):
        m=row["metal_guards"][layer]
        need(m["lower_adjacent_via"]==lo and m["upper_adjacent_via"]==hi,"correct adjacent via layers")
        need(set(m["checks"])==metal_keys and all(v is True for v in m["checks"].values()),"complete actual metal admission")
    expected={(x+dx,y+dy)for dx in(0,480,960)for dy in range(0,17281,480)if(dx,dy)not in((0,0),(0,17280))}
    need(len(expected)==109 and len(row["cuts"])==109 and{tuple(v["center_dbu"])for v in row["cuts"]}==expected,"independent exact109cut array")
    via_keys={"square190","grid5","enclosed_m1_50","enclosed_m2_50","existing_via_clearance240","new_via_clearance240","within_original_extent"}
    cuts=pya.Region();lower=(original[10]+metal).merged();upper=(original[30]+metal).merged()
    for v in row["cuts"]:
        cx,cy=v["center_dbu"]
        need(v["bbox"]==[cx-95,cy-95,cx+95,cy+95],"exact190nm Via2 square")
        need(set(v["guards"])==via_keys and all(k is True for k in v["guards"].values()),"complete actual Via2 admission")
        cut=box(v["bbox"]);enclosure=cut.sized(50,50,2)
        need((enclosure-lower).is_empty()and(enclosure-upper).is_empty(),"independent both-metal50nm enclosure")
        need((cut&original[29].sized(240,240,2)).is_empty()and(cut&cuts.sized(240,240,2)).is_empty(),"independent original and new240nm via spacing")
        cuts+=cut
    cuts=cuts.merged();need(cuts.count()==109 and cuts.area()==109*36100,"exact disjoint Via2 material")
    return {10:metal,29:cuts,30:metal}

def drain_m23_delta_controls(pya):
    import copy
    x,y=10000,20000;box=lambda b:pya.Region(pya.Box(*b))
    original={n:pya.Region()for n in(8,10,19,29,30,49)}
    original[8]=box([x-160,y-18000,x+160,y+18000])
    original[10]=box([x-150,y-200,x+150,y+17800])
    original[30]=box([x-200,y-200,x+200,y+17800])
    original[29]=box([x-95,y-95,x+95,y+95])+box([x-95,y+17505,x+95,y+17695])
    keys=("nonempty","grid5","connected_existing_m2","foreign_m2_clearance240","foreign_via1_clearance50","foreign_via2_clearance50","within_original_extent")
    vk=("square190","grid5","enclosed_m1_50","enclosed_m2_50","existing_via_clearance240","new_via_clearance240","within_original_extent")
    row=dict(label="T003_D",native_net="$159",wire_component=18,original_anchor=dict(label="T003_D",metal=8,wire_component=18,native_cluster=40,
        detail=dict(device=3,terminal="D",native_net="$159"),point_dbu=[x,y]),metal_bbox=[x-150,y-200,x+1250,y+17800],
        metal_guards={layer:dict(lower_adjacent_via=lo,upper_adjacent_via=hi,checks={k:True for k in keys})for layer,lo,hi in(("10",19,29),("30",29,49))})
    row["cuts"]=[dict(center_dbu=[x+dx,y+dy],bbox=[x+dx-95,y+dy-95,x+dx+95,y+dy+95],guards={k:True for k in vk})
        for dx in(0,480,960)for dy in range(0,17281,480)if(dx,dy)not in((0,0),(0,17280))]
    result=drain_m23_variant(pya,original,row)
    need(result[29].count()==109 and result[29].area()==3934900,"independent complete109drain Via2 construction")
    cases=["independent original drain identity rectangle and109cuts"]
    for name in("device","terminal","label","owner","component","off-grid","metal-box","missing-metal-admission","wrong-via-layer",
                "failed-metal-guard","nonboolean-metal-guard","via-center","via-box","missing-via","duplicate-via",
                "failed-via-guard","missing-via-guard","missing-M1","missing-M2","missing-M3","missing-upper-attachment","preexisting-via"):
        bad=copy.deepcopy(row);ref=dict(original)
        if name=="device":bad["original_anchor"]["detail"]["device"]=7
        elif name=="terminal":bad["original_anchor"]["detail"]["terminal"]="S"
        elif name=="label":bad["label"]="T004_D"
        elif name=="owner":bad["native_net"]="avss"
        elif name=="component":bad["wire_component"]=14
        elif name=="off-grid":bad["original_anchor"]["point_dbu"][0]+=1
        elif name=="metal-box":bad["metal_bbox"][2]+=5
        elif name=="missing-metal-admission":bad["metal_guards"].pop("30")
        elif name=="wrong-via-layer":bad["metal_guards"]["30"]["upper_adjacent_via"]=29
        elif name=="failed-metal-guard":bad["metal_guards"]["30"]["checks"]["foreign_m2_clearance240"]=False
        elif name=="nonboolean-metal-guard":bad["metal_guards"]["10"]["checks"]["grid5"]=1
        elif name=="via-center":bad["cuts"][0]["center_dbu"][0]+=5
        elif name=="via-box":bad["cuts"][0]["bbox"][0]-=5
        elif name=="missing-via":bad["cuts"].pop()
        elif name=="duplicate-via":bad["cuts"][0]=copy.deepcopy(bad["cuts"][1])
        elif name=="failed-via-guard":bad["cuts"][0]["guards"]["square190"]=False
        elif name=="missing-via-guard":bad["cuts"][0]["guards"].pop("enclosed_m2_50")
        elif name=="missing-M1":ref[8]=pya.Region()
        elif name=="missing-M2":ref[10]=pya.Region()
        elif name=="missing-M3":ref[30]=pya.Region()
        elif name=="missing-upper-attachment":ref[30]=box([x-200,y-200,x+200,y+1000])
        elif name=="preexisting-via":ref[29]=original[29]+box(bad["cuts"][0]["bbox"])
        try:drain_m23_variant(pya,ref,bad)
        except AssertionError:cases.append("reject drainM23 "+name)
        else:raise AssertionError(name)
    need(len(cases)==23,"all23drainM23 controls")
    return cases


def collector_via2_variant(pya,original,row):
    a=row["original_anchor"];d=a["detail"];i=d["device"]
    need(type(i)is int and i in(54,56,106,108),"four actual collector driver HBTs")
    need(d["model"]=="npn13G2"and d["terminal"]=="E"and a["metal"]==10,"actual HBT emitter on Metal2")
    need(row["label"]==a["label"]=="T"+str(i).zfill(3)+"_E","exact original emitter label")
    need(row["wire_component"]==a["wire_component"]and row["native_net"]==d["native_net"]==("$44"if i<100 else"$598"),"actual collector ownership")
    x,ay=a["point_dbu"];need(type(x)is int and type(ay)is int and x%5==0 and ay%5==2,"original two-nm HBT reference offset")
    y=ay-2;need(row["grid_point_dbu"]==[x,y],"independent native five-nm point")
    box=lambda b:pya.Region(pya.Box(*b))
    need((box([x-1,ay-1,x+1,ay+1])-original[10]).is_empty(),"original emitter point on owned M2")
    need((box([x-1,y-1,x+1,y+1])-original[30]).is_empty(),"original same-net M3 attachment")
    oldcuts=pya.Region()
    for dx in(-720,-240,240,720):oldcuts+=box([x+dx-95,y-95,x+dx+95,y+95])
    need((oldcuts-original[29]).is_empty(),"all four original Via2 cuts retained")
    need(row["metal_bbox"]==[x-1825,y-650,x+1825,y+450],"independent exact collector M3 pad")
    mk={"nonempty","grid5","connected_existing_m2","foreign_m2_clearance240","foreign_via1_clearance50","foreign_via2_clearance50","within_original_extent"}
    vk={"square190","grid5","enclosed_m1_50","enclosed_m2_50","existing_via_clearance240","new_via_clearance240","within_original_extent"}
    need(set(row["metal_guards"])==mk and all(v is True for v in row["metal_guards"].values()),"complete literal-True M3 admission")
    expected={(x+dx,y+dy)for dx in(-1680,-1200,-720,-240,240,720,1200,1680)for dy in(-480,0)if not(dy==0 and dx in(-720,-240,240,720))}
    need(len(row["cuts"])==12 and{tuple(v["center_dbu"])for v in row["cuts"]}==expected,"independent twelve-cut pattern")
    metal=box(row["metal_bbox"]);upper=(original[30]+metal).merged();cuts=pya.Region()
    for v in row["cuts"]:
        cx,cy=v["center_dbu"]
        need(v["bbox"]==[cx-95,cy-95,cx+95,cy+95],"exact 190-nm new cut")
        need(set(v["guards"])==vk and all(k is True for k in v["guards"].values()),"complete literal-True Via2 admission")
        cut=box(v["bbox"]);enclosure=cut.sized(50,50,2)
        need((enclosure-original[10]).is_empty()and(enclosure-upper).is_empty(),"actual unchanged M2 and extended M3 enclosure")
        need((cut&original[29].sized(240,240,2)).is_empty()and(cut&cuts.sized(240,240,2)).is_empty(),"independent old/new Via2 spacing")
        cuts+=cut
    cuts=cuts.merged();need(cuts.count()==12 and cuts.area()==433200,"exact twelve disjoint Via2 cuts")
    return {29:cuts,30:metal}

def collector_via2_delta_controls(pya):
    import copy
    x,y=10000,20000;box=lambda b:pya.Region(pya.Box(*b))
    original={n:pya.Region()for n in(10,29,30)}
    original[10]=box([x-1900,y-775,x+1900,y+780])
    original[30]=box([x-3000,y-200,x+3000,y+200])
    for dx in(-720,-240,240,720):original[29]+=box([x+dx-95,y-95,x+dx+95,y+95])
    mk=("nonempty","grid5","connected_existing_m2","foreign_m2_clearance240","foreign_via1_clearance50","foreign_via2_clearance50","within_original_extent")
    vk=("square190","grid5","enclosed_m1_50","enclosed_m2_50","existing_via_clearance240","new_via_clearance240","within_original_extent")
    row=dict(label="T054_E",native_net="$44",wire_component=3,original_anchor=dict(label="T054_E",metal=10,wire_component=3,native_cluster=8,
        detail=dict(device=54,terminal="E",model="npn13G2",native_net="$44"),point_dbu=[x,y+2]),
        grid_point_dbu=[x,y],metal_bbox=[x-1825,y-650,x+1825,y+450],metal_guards={k:True for k in mk})
    row["cuts"]=[dict(center_dbu=[x+dx,y+dy],bbox=[x+dx-95,y+dy-95,x+dx+95,y+dy+95],guards={k:True for k in vk})
        for dx in(-1680,-1200,-720,-240,240,720,1200,1680)for dy in(-480,0)if not(dy==0 and dx in(-720,-240,240,720))]
    result=collector_via2_variant(pya,original,row)
    need(result[29].count()==12 and result[29].area()==433200,"independent collector twelve-cut construction")
    cases=["independent collector original ownership and twelve-cut construction"]
    names=("device","model","terminal","layer","label","owner","component","x-grid","offset","grid-point","metal-box",
        "missing-metal-guard","false-metal-guard","nonboolean-metal-guard","via-center","via-box","missing-via","duplicate-via",
        "missing-via-guard","false-via-guard","nonboolean-via-guard","missing-M2","missing-M3","missing-old-via","preexisting-new-via","M2-enclosure")
    for name in names:
        bad=copy.deepcopy(row);ref=dict(original)
        if name=="device":bad["original_anchor"]["detail"]["device"]=61
        elif name=="model":bad["original_anchor"]["detail"]["model"]="sg13_lv_nmos"
        elif name=="terminal":bad["original_anchor"]["detail"]["terminal"]="C"
        elif name=="layer":bad["original_anchor"]["metal"]=30
        elif name=="label":bad["label"]="T056_E"
        elif name=="owner":bad["native_net"]="$159"
        elif name=="component":bad["wire_component"]=18
        elif name=="x-grid":bad["original_anchor"]["point_dbu"][0]+=1
        elif name=="offset":bad["original_anchor"]["point_dbu"][1]-=2
        elif name=="grid-point":bad["grid_point_dbu"][1]+=5
        elif name=="metal-box":bad["metal_bbox"][2]+=5
        elif name=="missing-metal-guard":bad["metal_guards"].pop("grid5")
        elif name=="false-metal-guard":bad["metal_guards"]["foreign_m2_clearance240"]=False
        elif name=="nonboolean-metal-guard":bad["metal_guards"]["grid5"]=1
        elif name=="via-center":bad["cuts"][0]["center_dbu"][0]+=5
        elif name=="via-box":bad["cuts"][0]["bbox"][0]-=5
        elif name=="missing-via":bad["cuts"].pop()
        elif name=="duplicate-via":bad["cuts"][0]=copy.deepcopy(bad["cuts"][1])
        elif name=="missing-via-guard":bad["cuts"][0]["guards"].pop("enclosed_m2_50")
        elif name=="false-via-guard":bad["cuts"][0]["guards"]["square190"]=False
        elif name=="nonboolean-via-guard":bad["cuts"][0]["guards"]["square190"]=1
        elif name=="missing-M2":ref[10]=pya.Region()
        elif name=="missing-M3":ref[30]=pya.Region()
        elif name=="missing-old-via":ref[29]=original[29]-box([x-815,y-95,x-625,y+95])
        elif name=="preexisting-new-via":ref[29]=original[29]+box(bad["cuts"][0]["bbox"])
        elif name=="M2-enclosure":ref[10]=box([x-1800,y-600,x+1800,y+780])
        try:collector_via2_variant(pya,ref,bad)
        except AssertionError:cases.append("reject collector Via2 "+name)
        else:raise AssertionError(name)
    need(len(cases)==27,"all27collector Via2 controls")
    return cases


def access16_variant(pya,original,row):
    a=row["original_anchor"]
    need(a["detail"]["device"]in(54,56,106,108)and a["detail"]["terminal"]=="E"and a["metal"]==10,"actual upper emitter")
    need(row["label"]==a["label"]=="T"+str(a["detail"]["device"]).zfill(3)+"_E","exact terminal label")
    need(a["detail"]["native_net"]==("$44"if a["detail"]["device"]<100 else"$598"),"actual native net")
    need(len(row["cuts"])==4,"four actual extra cuts")
    addition=pya.Region()
    for entry in row["cuts"]:
        need(entry["component"]==a["wire_component"]and entry["label"]==a["label"]and entry["via_layer"]==29 and entry["lower"]==10 and entry["upper"]==30,"actual cut owner and layer")
        b=entry["bbox"];need(len(b)==4 and all(isinstance(x,int)and x%5==0 for x in b)and b[2]-b[0]==b[3]-b[1]==190,"190nm5nm-grid cut")
        cut=pya.Region(pya.Box(*b))
        need((cut.sized(50,50,2)-original[10]).is_empty()and(cut.sized(50,50,2)-original[30]).is_empty(),"same-net50nm enclosure")
        need((cut&(original[29]+addition).sized(240,240,2)).is_empty(),"original and new cut separation")
        addition+=cut
    need(addition.count()==4 and addition.area()==4*36100,"four disjoint actual cuts")
    return {29:addition}
def access16_controls(pya):
    import copy
    original={10:pya.Region(pya.Box(0,0,4000,4000)),30:pya.Region(pya.Box(0,0,4000,4000)),29:pya.Region()}
    anchor=dict(detail=dict(device=54,terminal="E",native_net="$44"),metal=10,label="T054_E",wire_component=3)
    row=dict(label="T054_E",original_anchor=anchor,cuts=[dict(component=3,label="T054_E",via_layer=29,lower=10,upper=30,bbox=[x,1000,x+190,1190])for x in (500,980,1460,1940)])
    need(access16_variant(pya,original,row)[29].area()==144400,"analytic exact four cuts")
    passed=["exact four redundant cuts"]
    for label in ("missing","duplicate","wrong-owner","wrong-layer","wrong-net","offgrid","size","lower-enclosure","upper-enclosure","old-via-collision"):
        r=copy.deepcopy(row);o={k:pya.Region(v)for k,v in original.items()}
        if label=="missing":r["cuts"].pop()
        elif label=="duplicate":r["cuts"][1]=copy.deepcopy(r["cuts"][0])
        elif label=="wrong-owner":r["cuts"][0]["component"]=4
        elif label=="wrong-layer":r["cuts"][0]["via_layer"]=19
        elif label=="wrong-net":r["original_anchor"]["detail"]["native_net"]="avss"
        elif label=="offgrid":r["cuts"][0]["bbox"][0]+=1
        elif label=="size":r["cuts"][0]["bbox"][2]+=5
        elif label=="lower-enclosure":o[10]=pya.Region()
        elif label=="upper-enclosure":o[30]=pya.Region()
        elif label=="old-via-collision":o[29]=pya.Region(pya.Box(*r["cuts"][0]["bbox"]))
        try:access16_variant(pya,o,r)
        except AssertionError:passed.append("reject "+label)
        else:raise AssertionError("missed access16 fault "+label)
    return passed
def config():
    c=json.loads((ROOT/CONFIG).read_bytes())
    need(c["schema"]=="nssoc.clock-access16.canonical.v1","actual access16 schema")
    need(c["candidate"]["gds"]==dict(bytes=1079924,sha256="28eebb9f880648935a6368ada78a5e5666694ba98e073fbbac3f2e0c986339d6"),"actual16via candidate")
    need(c["reference_prefix"]=="binding/inputs/"and c["original_reference_gds"]==dict(bytes=1078900,sha256="c0d420cdbc31863bf21086e88c12f494779961225031c261d6b05fe07e7585a7"),"actual current reference")
    p=c["physical"];need(p["run"]==41535701378 and p["source"]=="e00b2df77c4337940ec7db32159dacc260eb91ab"and p["release"]==432027578,"actual new physical producer")
    g=c["generation"];q=g["proof"]
    need(g["run"]==41535065105 and g["source"]=="381397901390b96a7609f6592918d685d104bfbd","actual16via producer")
    need(q["candidate"]==c["candidate"]["gds"]and q["original_gds"]==c["original_reference_gds"]and q["new_via_count"]==16 and q["via_layers"]=={"29":16},"exact actual16via proposal")
    need(all(q[k]is False for k in("physical_acceptance","fresh_RC","electrical_improvement_proven","full_phy_accepted","final_timing_complete")),"candidate not electrical acceptance")
    rows=g["targets"]
    need(len(rows)==4 and{r["label"]for r in rows}=={"T"+str(n).zfill(3)+"_E"for n in(54,56,106,108)},"all four actual upper-emitter declarations")
    need(len({r["original_anchor"]["wire_component"]for r in rows})==2,"two original partitions")
    return c
def prove_material(pya,reference,view,old,new,c):
    _,before=core.component_keys(old["graph"]);_,after=core.component_keys(new["graph"])
    need(set(before)==set(after)and len(before)==len(after)==113,"all113complete original partitions")
    original_wire=reference/(c["reference_prefix"]+"wire/native05/wires.l2n")
    need(pin(original_wire)==c["generation"]["proof"]["original_wire_l2n"],"actual current native wire ownership")
    ow=pya.LayoutToNetlist();ow.read(str(original_wire))
    nw=pya.LayoutToNetlist();nw.read(str(view/"wire/native05/wires.l2n"))
    on={n.cluster_id:n for n in ow.netlist().top_circuit().each_net()};nn={n.cluster_id:n for n in nw.netlist().top_circuit().each_net()}
    need(set(on)=={v["component"]for v in before.values()}and set(nn)=={v["component"]for v in after.values()},"complete original/new native net census")
    need(set(old["graph"]["layers"])==set(new["graph"]["layers"])=={str(n)for n in core.LAYERS},"all13 conductor layers")
    anchors={a["label"]:a for a in old["anchors"]["anchors"]}
    grouped={};labels={}
    for row in c["generation"]["targets"]:
        a=anchors[row["label"]];need(a==row["original_anchor"],"exact complete original anchor")
        matches=[(k,v)for k,v in before.items()if v["component"]==a["wire_component"]and v["native_cluster"]==a["native_cluster"]]
        need(len(matches)==1,"unique native original owner");key,owner=matches[0]
        shapes={n:core.layer_region(pya,ow,on[owner["component"]],old["graph"],n).merged()for n in core.LAYERS}
        add=access16_variant(pya,shapes,row)[29]
        grouped.setdefault(key,pya.Region());grouped[key]+=add;labels.setdefault(key,[]).append(row["label"])
    need(len(grouped)==2 and all(len(v)==2 for v in labels.values()),"two collectors with two emitter accesses each")
    need(all(v.count()==8 and v.area()==8*36100 for v in grouped.values()),"eight disjoint added vias per partition")
    records=[]
    for part in sorted(before):
        a=before[part];b=after[part]
        for layer in core.LAYERS:
            left=core.layer_region(pya,ow,on[a["component"]],old["graph"],layer)
            right=core.layer_region(pya,nw,nn[b["component"]],new["graph"],layer)
            addition=grouped.get(part,pya.Region())if layer==29 else pya.Region()
            material_union(pya,left,right,addition)
            records.append(dict(partition=json.loads(part),layer=layer,old_component=a["component"],new_component=b["component"],
                old_area_dbu2=left.area(),new_area_dbu2=right.area(),added_area_dbu2=(right-left).area(),declared_added_area_dbu2=(addition-left).area()))
    changed=[r for r in records if r["added_area_dbu2"]]
    need(len(changed)==2 and all(r["layer"]==29 and r["added_area_dbu2"]==r["declared_added_area_dbu2"]==8*36100 for r in changed),"only exact16vias on two native nets")
    need(len(records)==1469,"all113partitions x13layers")
    return dict(status="PASS_ALL113_NATIVE_PARTITIONS_ALL13LAYERS_EXACT16_VIA2",records=records,targets=labels,**FLAGS)

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
    checks.extend(source_m2_delta_controls(pya))
    checks.extend(drain_m23_delta_controls(pya))
    need(len(checks)==96,"all96 prior canonical controls")
    checks.extend(collector_via2_delta_controls(pya))
    need(len(checks)==123,"all123 prior and collector controls")
    checks.extend(access16_controls(pya))
    need(len(checks)==134,"all123 prior plus11 current via controls")
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
    need(q["status"]=="PASS_CLOCK_ACCESS16_GDS_FULL560_DRC_DEEP_FLAT_LVS13"and q["gds"]==config()["candidate"]["gds"],"actual candidate physical qualification")
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
    save("view/canonical-view-qualification.json",dict(status="PASS_CLOCK_ACCESS16_NATIVE_CANONICAL_VIEW_REQUIRES_FRESH_RC",
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
    need(p["run"]==41439516945 and p["source"]=="710869eb13082f3c3dc488159bf167d937294454"and p["release"]==431398178,"actual current drainM23 fresh-RC reference")
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
    need(seen==index["files"]and len(seen)==len(cfg["complete_members"]),"complete current current horizontal-ground native reference")
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
        need(q["status"]=="PASS_CLOCK_ACCESS16_NATIVE_CANONICAL_VIEW_REQUIRES_FRESH_RC","complete actual native view")
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
