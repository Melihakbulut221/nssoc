#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted, derived-only net459 connectivity observation; never mutates layout."""
import argparse,base64,copy,hashlib,json,os,re,sys,zlib
from pathlib import Path
import mainchip_two_signal_geometry as g
ROOT=Path(__file__).resolve().parent.parent
BRANCH="codex/mainchip-net459-connectivity"
INPUT="docs/evidence/mainchip-southern-neighborhood-readback-terminal-40944948451/readback/native/southern-neighborhood/neighborhood.json"
INPUT_SHA="c99dddfd6d7968e87caef77ad2e0e666b085635a5f3fc5ce8232540041210fd3"
METALS=("Metal1","Metal2","Metal3","Metal4","Metal5","TopMetal1","TopMetal2")
FLAGS=dict(physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
    geometry_changed=False,native_acquisition=False,native_executed=False,
    pin_internal_connectivity_inferred=False,repair_authorized_by_this_observation=False)
def require(v,message):
    if not v:raise ValueError(message)
def encode(d):return (json.dumps(d,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def digest(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def context():
    e=os.environ
    require(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_OS")=="Linux","hosted Linux only")
    require(e.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"and e.get("GITHUB_EVENT_NAME")=="workflow_dispatch","repository/event")
    require(e.get("GITHUB_REF")=="refs/heads/"+BRANCH and e.get("GITHUB_RUN_ATTEMPT")=="1","branch/attempt")
    require(re.fullmatch("[0-9a-f]{40}",e.get("GITHUB_SHA",""))and re.fullmatch("[1-9][0-9]*",e.get("GITHUB_RUN_ID","")),"source/run")
    return dict(source=e["GITHUB_SHA"],run=int(e["GITHUB_RUN_ID"]),attempt=1)
def box(value):
    require(type(value)is list and len(value)==4 and all(type(x)is int for x in value),"integer box")
    require(value[0]<value[2]and value[1]<value[3],"positive area box")
    return value
def overlap(a,b,mode):
    require(mode in("positive_area","closed_boundary"),"intersection mode")
    dx=min(a[2],b[2])-max(a[0],b[0]);dy=min(a[3],b[3])-max(a[1],b[1])
    return dx>0 and dy>0 if mode=="positive_area"else dx>=0 and dy>=0
def observe(shapes,pins,mode,removed=()):
    require(type(shapes)is list and 0<len(shapes)<=4096,"shape count")
    require(type(pins)is list and 0<len(pins)<=128,"pin count")
    removed=set(removed)
    require(all(type(i)is int and 0<=i<len(shapes)for i in removed),"removed identities")
    require(all(shapes[i]["kind"]=="wire"for i in removed),"only a complete wire rectangle may be excluded")
    active={};vias={};ignored=[]
    for i,s in enumerate(shapes):
        require(s["kind"]in("wire","wire-rect","via"),"supported shape kind")
        box(s["box"]);require(type(s["layer"])is str,"layer name")
        if s["kind"]=="via":
            require(type(s["opcode_index"])is int and s["opcode_index"]>=0,"via opcode")
            require(type(s["via_key"])is str and s["via_key"],"via key")
            require(type(s["origin_xy"])is list and len(s["origin_xy"])==2 and all(type(v)is int for v in s["origin_xy"]),"via origin")
            key=s["opcode_index"];signature=(s["via_key"],tuple(s["origin_xy"]))
            row=vias.setdefault(key,dict(signature=signature,indices=[],ordinals=[]))
            require(row["signature"]==signature,"mixed via identity at one opcode")
            require(type(s["component_ordinal"])is int and s["component_ordinal"]>=0 and s["component_ordinal"]not in row["ordinals"],"unique via component")
            row["indices"].append(i);row["ordinals"].append(s["component_ordinal"])
        require(s["layer"]in METALS or s["kind"]=="via","nonmetal wire refused")
        if i in removed:continue
        if s["layer"]in METALS:active[i]=s
        else:ignored.append(i)
    adjacency={i:set()for i in active};edges=[]
    ids=sorted(active)
    for n,i in enumerate(ids):
        for j in ids[n+1:]:
            if active[i]["layer"]==active[j]["layer"]and overlap(active[i]["box"],active[j]["box"],mode):
                adjacency[i].add(j);adjacency[j].add(i)
                edges.append(dict(a=i,b=j,reason=mode,layer=active[i]["layer"]))
    for opcode,row in sorted(vias.items()):
        require(sorted(row["ordinals"])==list(range(len(row["ordinals"]))),"complete via component ordinal sequence")
        metal=[i for i in row["indices"]if i in active]
        require(len(metal)>=2 and len({active[i]["layer"]for i in metal})>=2,"via must join at least two conductor layers")
        for i in metal:
            for j in metal:
                if i<j:
                    adjacency[i].add(j);adjacency[j].add(i)
                    edges.append(dict(a=i,b=j,reason="same_native_via_opcode",opcode_index=opcode))
    components=[];membership={}
    for i in ids:
        if i in membership:continue
        number=len(components);todo=[i];members=[]
        membership[i]=number
        while todo:
            current=todo.pop();members.append(current)
            for adjacent in sorted(adjacency[current]):
                if adjacent not in membership:membership[adjacent]=number;todo.append(adjacent)
        components.append(dict(index=number,shape_indices=sorted(members)))
    pin_rows=[];pin_ids=set()
    for pin in pins:
        require(pin["kind"]=="iterm","only fully observed ITerm records admitted")
        identity=pin["scoped_identity"];name=json.dumps(identity,separators=(",",":"))
        require(type(identity)is list and len(identity)==3 and identity[0]=="iterm"
          and all(type(v)is str and v for v in identity)and name not in pin_ids,"unique scoped pin")
        pin_ids.add(name)
        geometries=pin["geometries"];require(type(geometries)is list and geometries,"complete pin geometries")
        matches=[]
        for ordinal,pair in enumerate(geometries):
            require(type(pair)is list and len(pair)==2 and pair[0]in METALS,"metal pin geometry")
            layer,rect=pair;box(rect)
            hits=[i for i in ids if active[i]["layer"]==layer and overlap(active[i]["box"],rect,mode)]
            matches.append(dict(geometry_index=ordinal,layer=layer,box=rect,shape_indices=hits,
              components=sorted({membership[i]for i in hits})))
        found=sorted({c for m in matches for c in m["components"]})
        pin_rows.append(dict(scoped_identity=identity,geometries=matches,wire_components=found,
          ambiguous_multiple_wire_components=len(found)>1,no_wire_access=not found))
    single=all(len(p["wire_components"])==1 for p in pin_rows)
    shared=single and len({p["wire_components"][0]for p in pin_rows})==1
    return dict(mode=mode,removed_shape_indices=sorted(removed),wire_components=components,
      conductor_shape_count=len(active),ignored_cut_component_indices=ignored,edges=edges,
      pins=pin_rows,all_pins_share_one_wire_component=shared,
      all_wire_material_one_component=len(components)==1,
      source_shapes=shapes,source_pins=pins,**FLAGS)
def source_guard():
    path=ROOT/INPUT;require(path.is_file()and not path.is_symlink(),"derived input")
    raw=path.read_bytes();require(len(raw)==1240336 and hashlib.sha256(raw).hexdigest()==INPUT_SHA,"complete actual neighborhood bytes")
    d=json.loads(raw)
    require(d["status"]=="PASS_SOUTHERN_SERIALIZED_NEIGHBORHOOD_OBSERVATION_ONLY"and d["read_only"]is True,"actual readback status")
    require(d["source_database"]==dict(bytes=213429713,sha256="47d657f41565f5c379a9152672eac824a5d296043c3726527031452ad2097677"),"current database")
    require((d["all_net_count"],d["instance_count"])==(143820,153130),"full actual census")
    n=d["full_source_material"]["net459"];p=n["projection"]
    require(n["scoped_identity"]==["net","net459"]and n["wire_identity"]==["net","net459","wire"]
      and n["metadata_class"]=="ROUTED"and n["sigtype"]=="SIGNAL","actual net")
    require(p["native_coordinate_checks_passed"]is True and (p["shape_count"],p["raw_count"],len(n["pins"]))==(139,375,5),"full projection count")
    catalog=copy.deepcopy(p["catalog"])
    require(all(re.fullmatch("[1-9][0-9]*",key)for key in catalog["path_layers"]),"raw layer IDs")
    catalog["path_layers"]={int(k):v for k,v in catalog["path_layers"].items()}
    replay=g.project_wire(p["raw"],catalog)
    require(all(replay[k]==p[k]for k in replay),"full actual raw projection replay")
    selected=p["shapes"][21]
    require(selected==dict(box=[947420,1789520,947620,1790560],current_extension=None,
      default_extension=100,from_xy=[947520,1789620],half_width=100,kind="wire",
      layer="Metal5",layer_key="Metal5",opcode_index=108,previous_extension=None,
      to_xy=[947520,1790460]),"exact short-bearing complete wire rectangle")
    return n,dict(input=digest(raw),current_database=d["source_database"],source_algorithm=p["source_algorithm"],
      complete_source_projection_replayed=True,removed_candidate_shape=selected,
      interpretation="Exclude this complete rectangle from the graph only. No native wire opcode, database, pin or physical geometry is changed.")
def controls():
    positive=[];refusals=[]
    def wire(layer,r):return dict(kind="wire",layer=layer,box=r)
    def pin(name,layer,r):return dict(kind="iterm",scoped_identity=["iterm",name,"P"],geometries=[[layer,r]])
    def reject(label,action):
        try:action()
        except (ValueError,KeyError,TypeError):refusals.append(label)
        else:raise AssertionError("did not refuse "+label)
    shapes=[wire("Metal1",[0,0,4,2]),wire("Metal1",[3,0,7,2]),wire("Metal1",[6,0,10,2])]
    pins=[pin("A","Metal1",[0,0,1,1]),pin("B","Metal1",[9,0,10,1])]
    require(observe(shapes,pins,"positive_area")["all_pins_share_one_wire_component"],"series")
    positive.append("positive-area series route")
    require(not observe(shapes,pins,"positive_area",[1])["all_pins_share_one_wire_component"],"bridge deletion")
    positive.append("bridge deletion disconnects opposite pins")
    loop=shapes+[wire("Metal1",[0,0,10,2])]
    require(observe(loop,pins,"positive_area",[1])["all_pins_share_one_wire_component"],"redundant path")
    positive.append("independent overlapping route preserves connectivity")
    touching=[wire("Metal1",[0,0,5,2]),wire("Metal1",[5,0,10,2])]
    require(not observe(touching,pins,"positive_area")["all_pins_share_one_wire_component"]
      and observe(touching,pins,"closed_boundary")["all_pins_share_one_wire_component"],"boundary distinction")
    positive.append("edge touching remains a separately reported weaker mode")
    cross=[wire("Metal1",[0,0,10,2]),wire("Metal2",[4,-5,6,5])]
    cp=[pins[0],pin("B","Metal2",[4,4,5,5])]
    require(not observe(cross,cp,"positive_area")["all_pins_share_one_wire_component"],"layer separation")
    positive.append("same XY on distinct layers does not connect")
    via=[dict(kind="via",layer=layer,box=r,opcode_index=10,via_key="tech:1",
       origin_xy=[5,1],component_ordinal=i)for i,(layer,r)in enumerate([
         ("Metal1",[4,0,6,2]),("Via1",[4,0,6,2]),("Metal2",[4,0,6,2])])]
    require(observe(cross+via,cp,"positive_area")["all_pins_share_one_wire_component"],"via bridge")
    positive.append("same native via joins its conductor layers")
    require(observe(cross+via,cp,"positive_area")["ignored_cut_component_indices"]==[3],"cut exclusion")
    positive.append("cut rectangles do not become independent planar conductors")
    islands=[wire("Metal1",[0,0,2,2]),wire("Metal1",[8,0,10,2])]
    wide=pin("X","Metal1",[0,0,10,2])
    result=observe(islands,[wide],"positive_area")
    require(len(result["wire_components"])==2 and result["pins"][0]["ambiguous_multiple_wire_components"],"no pin bridge")
    positive.append("a logical pin never bridges separate wire islands")
    result=observe(shapes,[pin("Z","Metal1",[20,20,21,21])],"positive_area")
    require(result["pins"][0]["no_wire_access"]and not result["all_pins_share_one_wire_component"],"unaccessed pin")
    positive.append("missing pin access is explicit")
    require(observe(list(reversed(shapes)),pins,"positive_area")["all_pins_share_one_wire_component"],"order")
    positive.append("shape order does not change connectivity")
    source_guard();positive.append("complete authentic input and raw shape replay")
    reject("unknown mode",lambda:observe(shapes,pins,"guess"))
    reject("invalid removed identity",lambda:observe(shapes,pins,"positive_area",[99]))
    reject("remove via",lambda:observe(cross+via,cp,"positive_area",[2]))
    reject("duplicate scoped pin",lambda:observe(shapes,pins+pins[:1],"positive_area"))
    bad=copy.deepcopy(shapes);bad[0]["box"]=[0,0,0,2]
    reject("zero width shape",lambda:observe(bad,pins,"positive_area"))
    bad=copy.deepcopy(shapes);bad[0]["box"][0]=False
    reject("boolean coordinate",lambda:observe(bad,pins,"positive_area"))
    bad=copy.deepcopy(cross+via);bad[-1]["origin_xy"]=[6,1]
    reject("mixed via opcode origins",lambda:observe(bad,cp,"positive_area"))
    bad=copy.deepcopy(cross+via);bad[-1]["component_ordinal"]=1
    reject("duplicate via component ordinal",lambda:observe(bad,cp,"positive_area"))
    bad=copy.deepcopy(cross+via);bad.pop(3)
    reject("missing via component ordinal",lambda:observe(bad,cp,"positive_area"))
    bad=copy.deepcopy(shapes);bad[0]["layer"]="Via1"
    reject("nonmetal ordinary wire",lambda:observe(bad,pins,"positive_area"))
    require(len(positive)==11 and len(refusals)==10,"control counts")
    return dict(status="PASS_NET459_CONNECTIVITY_SOURCE_CONTROLS",positive=positive,refusals=refusals,
      positive_count=len(positive),refusal_count=len(refusals),computed_control_networks_synthetic=True,
      actual_source_replayed_only=True,**FLAGS)
def inspect():
    n,proof=source_guard();cases={}
    for mode in("positive_area","closed_boundary"):
        cases[mode]=dict(original=observe(n["projection"]["shapes"],n["pins"],mode),
          exclude_short_rectangle=observe(n["projection"]["shapes"],n["pins"],mode,[21]))
    baseline=all(c["original"]["all_pins_share_one_wire_component"]for c in cases.values())
    after=[c["exclude_short_rectangle"]["all_pins_share_one_wire_component"]for c in cases.values()]
    status="BASELINE_CONNECTIVITY_UNQUALIFIED"if not baseline else(
      "NO_SINGLE_SHARED_WIRE_COMPONENT_AFTER_EXCLUSION_IN_BOTH_MODELS"if not any(after)else(
      "OBSERVED_PIN_CONNECTIVITY_SURVIVES_RECTANGLE_EXCLUSION_NOT_REPAIR"if all(after)else
      "MODE_DEPENDENT_CONNECTIVITY_UNQUALIFIED"))
    return dict(status="PASS_NET459_DERIVED_CONNECTIVITY_OBSERVATION_ONLY",finding=status,input_proof=proof,cases=cases,
      closed_boundary_mode_is_not_physical_acceptance=True,**FLAGS)
def emit(path):
    raw=path.read_bytes();pin=digest(raw);packed=zlib.compress(raw,9)
    pieces=[packed[i:i+12000]for i in range(0,len(packed),12000)]
    print("NET459_CONNECTIVITY_INDEX "+json.dumps(dict(name=path.name,chunks=len(pieces),**pin),sort_keys=True),flush=True)
    for i,b in enumerate(pieces):
        print("NET459_CONNECTIVITY_CHUNK "+json.dumps(dict(name=path.name,index=i,chunks=len(pieces),encoding="zlib-base64",base64=base64.b64encode(b).decode(),**pin),sort_keys=True),flush=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--mode",choices=("controls","inspect"),required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    require(not a.output.exists()and not a.output.is_symlink(),"new output path")
    a.output.parent.mkdir(parents=True,exist_ok=True);report=dict(status="FAIL_NET459_CONNECTIVITY",mode=a.mode,**FLAGS);primary=None
    try:
        ctx=context();report.update(controls()if a.mode=="controls"else inspect());report["context"]=ctx
    except BaseException as exc:primary=exc;report["error"]=dict(type=type(exc).__name__,message=str(exc))
    try:
        with a.output.open("xb")as stream:stream.write(encode(report))
        emit(a.output)
    except BaseException:
        if primary is None:raise
        try:
            print("NET459_CONNECTIVITY_FALLBACK "+json.dumps(report,sort_keys=True),flush=True)
        except BaseException:pass
    if primary is not None:raise primary
if __name__=="__main__":main()
