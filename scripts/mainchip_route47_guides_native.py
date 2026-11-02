"""Read-only guide extents for the exact recovered92 DRT markers."""
import json,sys,gc,hashlib
from decimal import Decimal
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_bulk_postdrt_antenna_native as native
import mainchip_saved_diode_routing_native as saved
from mainchip_snapshot_reload_contract import need
ROOT=Path("/work/recovery-inputs")
OUT=Path("/work/out/bulk-postdrt-antenna")
def coordinate(value,units):
    need(type(value)is str and type(units)is int and units>0,"exact displayed coordinate and native units")
    x=Decimal(value)*units
    need(x.is_finite()and x==x.to_integral_value(),"lossless displayed coordinate toDBU")
    return int(x)
def intersects(a,b):
    need(len(a)==len(b)==4 and all(type(v)is int for v in a+b),"integer rectangles")
    need(a[0]<=a[2]and a[1]<=a[3]and b[0]<=b[2]and b[1]<=b[3],"ordered rectangles")
    return a[0]<=b[2]and b[0]<=a[2]and a[1]<=b[3]and b[1]<=a[3]
def validate_scope(result,delta,selection):
    need(result["temporary47_protection_restored"]is True and result["all_nonselected_wires_and_clocks_unchanged"]is True,"actual recovered fullscope proof")
    need(delta["mode"]=="route"and delta["all_clocks_unchanged"]is True and delta["all_other_wires_unchanged"]is True,"original native clock and other-wire invariants")
    need(type(selection)is list and len(selection)==len(set(selection))==47 and all(type(n)is str for n in selection),"exact47 unique selected names")
    need(delta["selected"]==sorted(selection),"native route delta selected identity")
    changed=delta["changed"]
    need(type(changed)is list and len(changed)==len(set(changed))==46 and all(type(n)is str for n in changed),"actual46 unique changed names")
    need(changed==sorted(changed)and set(changed)<=set(selection),"only selected wires changed")
    proof=delta["complete_DEF"]
    need(proof["other_records_byte_exact"]is True and proof["non_NETS_bytes_exact"]is True,"complete DEF protected records and non-NETS bytes")
    names=proof["changed_signal_names"]
    need(type(names)is list and len(names)==len(set(names))==46 and sorted(names)==changed and type(proof["changed_signal_count"])is int and proof["changed_signal_count"]==46,"native and full DEF changed owner agreement")
    digest=hashlib.sha256(json.dumps(names,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    need(proof["changed_signal_names_sha256"]==digest,"exact full DEF changed-order digest")
    need(proof["accepted"]is False,"scope audit does not grant production acceptance")
    for record in (result,delta):
        need(all(record[k]is False for k in ("physical_acceptance","timing_accepted","full_phy_accepted")),"all final acceptance gates remain open")
    return dict(native_clock_and_other_wires_unchanged=True,complete_DEF_scope_verified=True,changed_signal_count=46,selected_signal_count=47,production_accepted=False)
def native_intersects(a_box,b_box):
    # Use the Point overload. The Rect overload rejects Rect proxy inputs in
    # the frozen embedded Python build; do not omit the native cross-check.
    a=odb.Rect(*a_box);b=odb.Rect(*b_box)
    need([a.xMin(),a.yMin(),a.xMax(),a.yMax()]==a_box and [b.xMin(),b.yMin(),b.xMax(),b.yMax()]==b_box,"native rectangle coordinates")
    point=odb.Point(max(a_box[0],b_box[0]),max(a_box[1],b_box[1]))
    first=a.intersects(point);second=b.intersects(point)
    need(type(first)is bool and type(second)is bool,"native closed point containment booleans")
    return first and second
def native_rectangle_controls():
    cases=[([0,0,10,10],[10,0,20,10],True),([0,0,10,10],[11,0,20,10],False),
        ([0,0,10,10],[5,5,5,5],True),([0,0,10,10],[0,11,10,20],False),
        ([-20,-20,-10,-10],[-15,-15,-5,-5],True),([0,0,0,0],[0,0,0,0],True)]
    for a,b,want in cases:need(native_intersects(a,b)is want and intersects(a,b)is want,"native rectangle closed-boundary control")
    return len(cases)
def main():
    pins=json.loads(Path("/work/recovery-selected-pins.json").read_bytes())
    for name,pin in pins.items():need(native.fp(ROOT/name)==pin,"authenticated recovered member")
    path=ROOT/"work/bulk-postdrt-antenna/final-measured.odb"
    need(native.fp(path)==dict(bytes=214402279,sha256="53b42f42c244af7416a78c0cc04cc897f99b114c892c6bc86ecc60affa3e05af"),"actual measured recovered19ODB")
    result=json.loads((ROOT/"bulk-postdrt-antenna/narrow47-result.json").read_bytes())
    delta=json.loads((ROOT/"bulk-postdrt-antenna/narrow47-route-delta.json").read_bytes())
    need(result["drc"]["marker_count"]==92 and result["antenna"]["design_is_routed"]==1,"actual reported routed92marker candidate")
    selection=json.loads((ROOT/"bulk-postdrt-antenna/narrow47-native-selection.json").read_bytes())
    selected=set(selection["selected"]);need(len(selected)==47,"actual47selection")
    scope_proof=validate_scope(result,delta,selection["selected"])
    scope=json.loads(Path("/work/reload-inputs/bulk-postdrt-antenna/targeted-routing-scope.json").read_bytes())
    clocks=set(scope["protected_nets"]);need(len(clocks)==1691 and not selected&clocks,"exact1691protected clocks")
    classes=json.loads((ROOT/"bulk-postdrt-antenna/narrow47-original-classes.json").read_bytes())
    raw=json.loads((ROOT/"bulk-postdrt-antenna/final-drc-markers.json").read_bytes())
    root=raw[native.CATEGORY];need(root["source"]=="DRT"and set(root["category"])=={"Short","Metal Spacing"},"actual complete marker categories")
    native_control_count=native_rectangle_controls()
    db,block=native.n.load(path)
    try:
        need(len(list(block.getNets()))==143820 and len(list(block.getInsts()))==154480,"actual native census")
        units=block.getDbUnitsPerMicron();need(type(units)is int and units>0,"native DBU")
        rows=[]
        for category,body in root["category"].items():
            need(body["source"]=="DRT"and len(body["violations"])==(64 if category=="Short"else 28),"complete actual category")
            for i,m in enumerate(body["violations"]):
                need(m["waived"]=="false"and len(m["shape"])==1 and m["shape"][0]["type"]=="box","all unwaived native box markers")
                points=m["shape"][0]["points"];need(len(points)==2,"actual two marker corners")
                box=[coordinate(points[0]["x"],units),coordinate(points[0]["y"],units),coordinate(points[1]["x"],units),coordinate(points[1]["y"],units)]
                need(intersects(box,box),"noninverted actual marker")
                sources=[]
                for source in m["sources"]:
                    need(source["type"]=="net","actual named native net sources")
                    name=source["name"];net=block.findNet(name);need(net is not None and net.getName()==name,"literal native owner resolution")
                    sources.append(name)
                need(sources and len(sources)==len(set(sources)),"all unique source owners")
                rows.append(dict(category=category,ordinal=i,layer=m["layer"],bbox_dbu=box,sources=sources))
        need(len(rows)==92,"every actual marker")
        owners=sorted({n for r in rows for n in r["sources"]})
        guide_map=saved.guides(block,owners)
        net_rows={}
        for name in owners:
            net=block.findNet(name)
            net_rows[name]=dict(sigtype=str(net.getSigType()),special=net.isSpecial(),native_wire_type=str(net.getWireType()),
                selected47=name in selected,protected_clock=name in clocks,temporarily_fixed_in_route47=name not in selected and classes.get(name)is not None,
                original_guide_count=len(guide_map[name]),guides=guide_map[name])
        hits=[]
        for ordinal,r in enumerate(rows):
            for name in r["sources"]:
                for gi,g in enumerate(guide_map[name]):
                    hit=intersects(r["bbox_dbu"],g["box"])
                    need(hit==native_intersects(r["bbox_dbu"],g["box"]),"independent native rectangle intersection")
                    if hit:
                        b=g["box"];meta=net_rows[name]
                        hits.append(dict(marker=ordinal,owner=name,guide=gi,bbox_dbu=b,width_um=(b[2]-b[0])/units,height_um=(b[3]-b[1])/units,
                            area_um2=(b[2]-b[0])*(b[3]-b[1])/(units*units),selected47=meta["selected47"],protected_clock=meta["protected_clock"],temporarily_fixed_in_route47=meta["temporarily_fixed_in_route47"]))
        ranked=sorted(hits,key=lambda r:(-r["area_um2"],r["owner"],r["guide"],r["marker"]))
        summary=dict(status="OBSERVED_ACTUAL92_MARKERS_AND_NATIVE_GUIDE_EXTENTS",source_run=41440285882,input=native.fp(path),
            native_rectangle_controls=native_control_count,recovered_scope_proof=scope_proof,native_units=units,marker_count=92,source_net_count=len(owners),guide_count=sum(len(v)for v in guide_map.values()),
            marker_guide_intersections=len(hits),protected_clock_source_count=sum(v["protected_clock"]for v in net_rows.values()),
            selected_source_count=sum(v["selected47"]for v in net_rows.values()),fixed_overlay_source_count=sum(v["temporarily_fixed_in_route47"]for v in net_rows.values()),
            largest_intersections=ranked[:20],current_route_calls=0,current_repair_calls=0,geometry_changed=False,
            router_internal_guide_mapping_equivalence_proven=False,memory_cause_proven=False,**native.p.FLAGS)
        native.save(OUT/"guide-observation.json",dict(summary=summary,markers=rows,nets=net_rows,intersections=hits))
        native.save(OUT/"guide-summary.json",dict(**summary,full_observation=native.fp(OUT/"guide-observation.json")))
    finally:odb.dbDatabase.destroy(db)
    for name,pin in pins.items():need(native.fp(ROOT/name)==pin,"recovered inputs remain byte-identical")
    for name,pin in json.loads(Path("/work/snapshot-selected-pins.json").read_bytes()).items():
        need(native.fp(Path("/work/reload-inputs")/name)==pin,"original scope inputs unchanged")
if __name__=="__main__":main()
