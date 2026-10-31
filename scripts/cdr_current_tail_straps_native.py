#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate eight bounded M1/M2/Via1 drain shunts on the actual current GDS."""
import argparse,collections,json,os,shutil,traceback
from pathlib import Path
import cdr_current_tail_straps as plan
import cloud_cdr_current_tail_straps as host
import cdr_drain_m1_width_trial_native as previous
import cdr_drain_access_feasibility_native as observation
import generate_cdr_v59_tail_access_wire as frozen
require=plan.require
BASE="native/current-mim-bundle/canonical-current-view/"
def box_record(box):return [box.left,box.bottom,box.right,box.top]
def read(root,name):return json.loads(host.r.regular(root,name).read_bytes())
def put(root,name,value):host.r.write_new(root/name,host.r.encode(value))
def validate_serialized(pya,layout,before,expected_raw,expected_material,bbox):
    require(layout.dbu==.001 and {c.name for c in layout.each_cell()}==set(before),"complete cell census and DBU")
    require(layout.cell(plan.TOP).bbox()==bbox,"complete original bbox")
    for cell in layout.each_cell():
        old=before[cell.name];top=cell.name==plan.TOP
        require(frozen.raw_records(layout,cell)==(expected_raw if top else old["raw"]),"exact original raw records and declared additions")
        require(frozen.hierarchy(cell)==old["hierarchy"],"unchanged original hierarchy")
        require([observation.properties(i)for i in cell.each_inst()]==old["instance_properties"],"unchanged instance properties")
        frozen.same_material(pya,expected_material if top else old["material"],frozen.material(pya,layout,cell))
def actual_controls(pya,candidate,out,before,raw,material,bbox,added):
    rows=[]
    for name in("missing_added_via","extra_metal","old_primitive_removed","duplicate_instance","changed_shape_property"):
        changed=pya.Layout();changed.read(str(candidate))
        validate_serialized(pya,changed,before,raw,material,bbox)
        top=changed.cell(plan.TOP)
        if name=="missing_added_via":
            box=next(x["box_dbu"]for x in added if x["layer"]==19)
            matches=[s for s in top.shapes(changed.layer(19,0)).each()if s.is_box()and box_record(s.box)==box]
            require(len(matches)==1,"unique new via control target");matches[0].delete()
        elif name=="extra_metal":top.shapes(changed.layer(10,0)).insert(pya.Box(0,0,5,5))
        elif name=="old_primitive_removed":
            leaf=changed.cell("nmos$2$1");next(leaf.shapes(changed.layer(8,0)).each()).delete()
        elif name=="duplicate_instance":
            inst=next(top.each_inst());top.insert(inst.cell_inst)
        else:next(top.shapes(changed.layer(10,0)).each()).set_property(999,"intentional-control")
        target=out/("control-"+name+".gds");changed.write(str(target))
        reread=pya.Layout();reread.read(str(target))
        try:validate_serialized(pya,reread,before,raw,material,bbox)
        except AssertionError as exc:rows.append(dict(name=name,rejected=True,positive_actual_baseline_passed=True,error=repr(exc),mutant=host.r.file_pin(target)))
        else:raise AssertionError("Accepted actual serialized fault: "+name)
    require(len(rows)==5,"complete actual native mutation controls")
    return rows
def generate(pya,selected,out,config):
    gp=BASE+"parent/layout/"+plan.TOP+".gds"
    layout=pya.Layout();layout.read(str(selected/gp))
    require(layout.dbu==.001 and layout.cell(plan.TOP)is not None,"current actual layout")
    top=layout.cell(plan.TOP)
    require(top.cell_index()in[c.cell_index()for c in layout.top_cells()],"actual top cell")
    graph=read(selected,BASE+"wire/native05/result.json")
    loc=read(selected,BASE+"wire/device-locations01.json")
    anchors=read(selected,"native/current-mim-bundle/mim/precise/wire/anchors08.json")
    require((graph["native_device_count"],graph["native_terminal_count"],graph["wire_component_count"],graph["native_net_count"])==(500,1446,113,238),"original full native graph census")
    lvs=pya.LayoutVsSchematic();lvs.read(str(selected/(BASE+"parent/physical/lvs_flat/result.lvsdb")))
    circuit=lvs.netlist().top_circuit();devices={d.id():d for d in circuit.each_device()}
    require(len(devices)==500 and circuit.pin_count()==25 and len(list(circuit.each_net()))==238,"complete original native netlist")
    require(dict(collections.Counter(d.device_class().name for d in devices.values()))==graph["native_devices"],"original native model census")
    w=pya.LayoutToNetlist();w.read(str(selected/(BASE+"wire/native05/wires.l2n")))
    nets={n.cluster_id:n for n in w.netlist().top_circuit().each_net()}
    owners={row["component"]:row for row in graph["wire_components"]}
    require(len(nets)==113 and set(nets)==set(owners),"complete wire owner census")
    locations={row["native_id"]:row for row in loc["devices"]};require(len(locations)==500,"complete original locations")
    full={};wire_layers={}
    for layer in(8,10,19,29):
        region=pya.Region(top.begin_shapes_rec(layout.layer(layer,0))).merged()
        obj=w.layer_by_name("gds_"+str(layer));require(obj is not None and (region^obj).is_empty(),"full actual GDS/wire layer union")
        full[layer]=region;wire_layers[layer]=obj
    before=previous.snapshot(pya,layout);bbox=top.bbox()
    planned=[];reports=[];same_owner={}
    for nid in sorted(plan.TARGETS):
        location=locations[nid];hierarchy=observation.stable_path(pya,layout,location)
        require(location["pcell"]["cell"]=="nmos$2$1","actual shared36um MOS primitive")
        dev=devices[nid];terminal=next(t for t in dev.device_class().terminal_definitions()if t.name=="D")
        net=dev.net_for_terminal(terminal.id());require(net is not None,"actual drain net")
        a=[x for x in anchors["anchors"]if x["label"]=="T%03d_D"%nid];require(len(a)==1,"one actual precise drain anchor");a=a[0]
        plan.validate_target(nid,a,dev.device_class().name,net.cluster_id,net.name)
        component=a["wire_component"]
        require(owners[component]["native_cluster"]==net.cluster_id and owners[component]["native_name"]==net.name,"wire/native owner")
        dt=pya.DCplxTrans.from_s(location["pcell"]["transform"])
        require(dt.mag==1 and dt.angle%90==0,"unscaled orthogonal native instance")
        tr=pya.ICplxTrans(dt.mag,dt.angle,dt.is_mirror(),round(dt.disp.x/layout.dbu),round(dt.disp.y/layout.dbu))
        cell=layout.cell(location["pcell"]["cell"])
        matches=[s for s in cell.shapes(layout.layer(8,0)).each()if s.is_box()and s.box==pya.Box(*plan.LOCAL_RAIL)and s.properties()=={}]
        require(len(matches)==1,"exact original160nm primitive drain rail")
        oldrail=pya.Region(matches[0].box.transformed(tr))
        owned={layer:w.shapes_of_net(nets[component],wire_layers[layer],True).merged()for layer in full}
        require((oldrail-owned[8]).is_empty(),"complete original rail electrical owner")
        point=pya.Point(*a["point_dbu"])
        require(oldrail.interacting(pya.Region(pya.Box(point.x-2,point.y-2,point.x+2,point.y+2))).count()==1,"actual anchor on intended primitive rail")
        require(w.probe_net(wire_layers[8],point).cluster_id==component,"actual wire anchor probe")
        native_layer=lvs.layer_by_index(graph["native_layer_mapping"]["8"])
        require(lvs.probe_net(native_layer,point).cluster_id==net.cluster_id,"actual LVS drain point owner")
        require((owned[8]-lvs.shapes_of_net(net,native_layer,True)).is_empty(),"complete M1 native partition")
        boxes={8:pya.Box(*plan.M1_BOX).transformed(tr),10:pya.Box(*plan.M2_BOX).transformed(tr)}
        add={layer:pya.Region(box)for layer,box in boxes.items()}
        record=dict(device=nid,native_cluster=net.cluster_id,native_name=net.name,wire_component=component,
          hierarchy=hierarchy,anchor=a,original_rail_dbu=box_record(matches[0].box.transformed(tr)),
          proposed_metal={str(k):box_record(v)for k,v in boxes.items()},cut_decisions=[],clearance_complete=False)
        reports.append(record)
        put(out,"drain-%03d-proposal.json"%nid,record)
        for layer in(8,10):
            foreign=(full[layer]-owned[layer]).merged()
            require(add[layer].sized(plan.CLEARANCE[layer]).interacting(foreign).is_empty(),"new M%d foreign metal clearance device%d"%(layer,nid))
            require(add[layer].interacting(full[19]-owned[19]).is_empty(),"foreign Via1 must not touch new metal")
        require(add[10].interacting(full[29]-owned[29]).is_empty(),"foreign Via2 must not touch new M2")
        cuts=[]
        for index,local in enumerate(plan.local_plan()["via1"]):
            box=pya.Box(*local).transformed(tr);cut=pya.Region(box)
            require((cut.sized(10)-(owned[8]+add[8])).is_empty(),"new V1 lower enclosure")
            require((cut.sized(50)-(owned[10]+add[10])).is_empty(),"new V1 upper enclosure")
            foreign=full[19]-owned[19]
            require(cut.sized(plan.CLEARANCE[19]).interacting(foreign).is_empty(),"new V1 foreign cut clearance")
            close=cut.sized(plan.CLEARANCE[19]).interacting(owned[19])
            decision=dict(index=index,box_dbu=box_record(box),insert=close.is_empty(),reason="new_owned_cut"if close.is_empty()else"spacing_to_existing_same_net_Via1")
            record["cut_decisions"].append(decision)
            if decision["insert"]:cuts.append(box)
        require(len(cuts)>=32,"at least32 new drain taps per device")
        region=pya.Region()
        for box in cuts:region.insert(box)
        require(region.count()==len(cuts),"distinct new cut geometry")
        record.update(clearance_complete=True,new_cuts=len(cuts),minimum_clearance_dbu=plan.CLEARANCE)
        put(out,"drain-%03d-admission.json"%nid,record)
        for layer,box in boxes.items():
            # Current3/32 already have exactly this M1 overlay; do not duplicate it.
            if not(pya.Region(box)-full[layer]).is_empty():
                planned.append(dict(device=nid,cluster=net.cluster_id,layer=layer,datatype=0,box_dbu=box_record(box)))
        planned.extend(dict(device=nid,cluster=net.cluster_id,layer=19,datatype=0,box_dbu=box_record(box))for box in cuts)
        for layer in(8,10,19):
            ownadd=region if layer==19 else add[layer]
            for other,reg in same_owner.get(layer,[]):
                if other!=net.cluster_id:require(ownadd.sized(plan.CLEARANCE[layer]).interacting(reg).is_empty(),"new-to-new foreign clearance")
            same_owner.setdefault(layer,[]).append((net.cluster_id,ownadd))
    require(len(reports)==8,"all eight actual drains admitted")
    require(len(planned)==len({(r["layer"],tuple(r["box_dbu"]))for r in planned}),"distinct declared raw additions")
    expected=dict(before[plan.TOP]["material"])
    scratch=pya.Layout();scratch.dbu=.001;s=scratch.create_cell("exact_declared_additions")
    for row in planned:
        key=(row["layer"],0);box=pya.Box(*row["box_dbu"])
        expected[key]=(expected.get(key,pya.Region())+pya.Region(box)).merged()
        s.shapes(scratch.layer(*key)).insert(box)
    extra=frozen.raw_records(scratch,s)
    require(len(extra)==len(planned)and all(r[:2]in plan.LAYERS and r[3]=="{}"and r[4]is False for r in extra),"exact allowed addition records")
    raw=sorted(before[plan.TOP]["raw"]+extra)
    put(out,"declared-additions.json",dict(records=planned,device_count=8,all_original_raw_records_preserved=True,**plan.FLAGS))
    for row in planned:top.shapes(layout.layer(row["layer"],0)).insert(pya.Box(*row["box_dbu"]))
    validate_serialized(pya,layout,before,raw,expected,bbox)
    candidate=out/(plan.TOP+".gds");layout.write(str(candidate))
    reread=pya.Layout();reread.read(str(candidate));validate_serialized(pya,reread,before,raw,expected,bbox)
    controls=actual_controls(pya,candidate,out,before,raw,expected,bbox,planned)
    for key,name in(("lef",plan.TOP+".lef"),("schematic","schematic.cir")):
        source=selected/(BASE+"parent/layout/"+name);shutil.copyfile(source,out/name)
        require(host.r.file_pin(source)==host.r.file_pin(out/name),"unchanged physical reference")
    old=read(selected,BASE+"parent/layout/result.json");require(len(old["ports"])==25,"actual25 original ports")
    result=dict(status="GENERATED_CURRENT_EIGHT_DRAIN_STRAPS_REQUIRES_FULL_DRC_LVS_RC_AND_WAVES",ports=old["ports"],
      inputs={str(selected/n):pin["sha256"]for n,pin in config["members"].items()},
      outputs={n:host.r.file_pin(out/n)["sha256"]for n in(plan.TOP+".gds",plan.TOP+".lef","schematic.cir")},**plan.FLAGS)
    put(out,"result.json",result)
    proof=dict(status="PASS_EXACT_CURRENT_EIGHT_DRAIN_STRAP_GENERATION_ONLY",actual_devices=8,added_records=len(planned),
      actual_candidate_mutation_controls=controls,actual_instance_reports=reports,input_gds=host.r.file_pin(selected/gp),
      candidate_gds=host.r.file_pin(candidate),all_original_cells_instances_properties_and_geometry_preserved=True,
      declared_additions_only=True,DRC_executed=False,LVS_executed=False,fresh_RC_executed=False,**plan.FLAGS)
    put(out,"generation.json",proof);return proof
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--selected",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--pins-sha256",required=True)
    args=parser.parse_args();ctx=host.context(os.environ);host.source_guard(ctx);host.source_guard(args.pins_sha256)
    config=host.config();require(not args.output.exists()and args.output.is_relative_to(host.ROOT/"hw/soc/out"),"new owned output")
    args.output.mkdir()
    try:
        import pya
        before={n:host.r.file_pin(host.r.regular(args.selected,n))for n in config["members"]}
        require(before==config["members"],"exact current input42")
        generate(pya,args.selected,args.output,config)
        require(before=={n:host.r.file_pin(host.r.regular(args.selected,n))for n in config["members"]},"selected inputs unchanged")
        host.source_guard(ctx)
    except BaseException as exc:
        try:put(args.output,"generation-failure.json",dict(error=repr(exc),traceback=traceback.format_exc(),**plan.FLAGS))
        except BaseException:print(traceback.format_exc(),flush=True)
        raise
if __name__=="__main__":main()
