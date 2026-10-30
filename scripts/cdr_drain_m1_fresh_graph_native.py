#!/usr/bin/env python3
"""Fresh immutable graph; exact original identity gates and two declared M1 union changes."""
import argparse,collections,importlib.util,json,shutil,sys,traceback
from pathlib import Path
import cloud_cdr_drain_m1_fresh_graph as h
import cdr_v59_selector_column_width_graph as original
import cdr_v59_tail_saved_identity_native as identities
import cdr_v59_tail_access_topology as topology
import generate_cdr_v59_tail_access_wire as material
TOP="nssoc_cdr_pd500_resistor_v59"
require=h.require
parse_path=identities.parse_path
BASE="canonical-current-view/"
PHYS="hw/soc/out/cloud-cdr-drain-m1-trial/"
WIRE=original.WIRE

def copy_exact(source,target):
    require(source.is_file()and not source.is_symlink()and not target.exists(),"exact new copy")
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    require(h.pin(source)==h.pin(target),"copy changed bytes")

def prepare(selected,physical,out,config):
    view=out/"candidate";require(not view.exists(),"fresh candidate projection")
    view.mkdir()
    for name in config["selected"]:
        if name.startswith(BASE+"parent/"):copy_exact(selected/name,view/name.removeprefix(BASE))
    # Retain immutable source metadata outside candidate before explicit derived metadata replacement.
    oldmeta=h.decode((view/"parent/layout/result.json").read_bytes())
    require(len(oldmeta["placements"])==16 and sum(oldmeta["primitive_census"].values())==500,"original parent metadata")
    h.write(out/"original-parent-metadata.json",h.encode(oldmeta))
    for path in (physical/PHYS/"physical/lvs_flat").iterdir():
        dest=view/"parent/physical/lvs_flat"/path.name
        require(dest.is_file()and not dest.is_symlink(),"same full flat-LVS member set")
        dest.unlink();copy_exact(path,dest)
    require({p.name for p in (physical/PHYS/"physical/lvs_flat").iterdir()}==
      {p.name for p in (view/"parent/physical/lvs_flat").iterdir()},"full current flat LVS projection")
    for name in (TOP+".gds",TOP+".lef","schematic.cir"):
        dest=view/"parent/layout"/name;require(dest.is_file()and not dest.is_symlink(),"known layout member")
        dest.unlink();copy_exact(physical/PHYS/"layout"/name,dest)
    current=h.decode((physical/PHYS/"layout/result.json").read_bytes())
    require(oldmeta["ports"]==current["ports"],"unchanged public port geometry")
    meta={k:oldmeta[k]for k in ("source_plan","placements","primitive_census","ports")}
    meta.update(status="DERIVED_NEW_TWO_M1_PHYSICAL_METADATA_FOR_FRESH_GRAPH",
      inputs={str(selected/config["paths"]["layout_report"]):h.pin(selected/config["paths"]["layout_report"])["sha256"],
              str(physical/PHYS/"layout/result.json"):h.pin(physical/PHYS/"layout/result.json")["sha256"]},
      outputs={name:h.pin(view/"parent/layout"/name)["sha256"]for name in (TOP+".gds",TOP+".lef","schematic.cir")},
      original_metadata_retained=True,physical_accepted=False,electrical_accepted=False,qualified_pex=False)
    (view/"parent/layout/result.json").unlink();h.write(view/"parent/layout/result.json",h.encode(meta))
    texts,proof=original.derived_texts()
    (view/"methods").mkdir()
    for name,text in texts.items():h.write(view/"methods"/name,text.encode())
    h.write(out/"derived-methods.json",h.encode(proof))
    (view/"wire").mkdir()
    for name in WIRE:copy_exact(h.ROOT/original.WIRE_SOURCE/name,view/"wire"/name)
    h.write(out/"projection.json",h.encode(dict(
      old_reference_child_bytes_unmodified=True,new_parent_gds=h.pin(view/"parent/layout"/(TOP+".gds")),
      new_flat_lvs=h.pin(view/"parent/physical/lvs_flat/result.lvsdb"),
      original_parent_files={n:h.pin(selected/n)for n in config["selected"]if n.startswith(BASE+"parent/")},
      candidate_parent_files={p.relative_to(view).as_posix():h.pin(p)for p in (view/"parent").rglob("*")if p.is_file()},
      old26box_reprojection_executed=False,new_parent_as_own_child_reference=False)))
    verify_sources(out,config)

def verify_sources(out,config):
    view=out/"candidate";texts,proof=original.derived_texts()
    require(h.decode((out/"derived-methods.json").read_bytes())==proof,"exact original method derivation")
    for name,text in texts.items():require((view/"methods"/name).read_bytes()==text.encode(),"derived method bytes")
    for name in WIRE:require(h.pin(view/"wire"/name)==h.pin(h.ROOT/original.WIRE_SOURCE/name),"immutable graph worker")
    require(h.pin(view/"parent/layout"/(TOP+".gds"))==config["physical"]["gds"],"new GDS identity")
    require(h.pin(view/"parent/physical/lvs_flat/result.lvsdb")==config["physical"]["lvs"],"new LVS identity")
    return view

def derived(mode,out,config):
    view=verify_sources(out,config);directory=view/"methods";sys.path.insert(0,str(directory))
    name,entry={"planes":("width_planes","native"),"recover":("width_source_pins","recover")}[mode]
    spec=importlib.util.spec_from_file_location(name,directory/(name+".py"))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.ROOT=h.ROOT;module.OUT=view
    getattr(module,entry)();verify_sources(out,config)

def compare_witnesses(old,new):
    require(old["native_device_count"]==new["native_device_count"]==500,"Wrong witness device census")
    require(old["native_terminal_count"]==new["native_terminal_count"]==1446,"Wrong witness terminal census")
    oi=topology.graph_index(old["graph"]);ni=topology.graph_index(new["graph"])
    require(sorted(r["key"] for r in oi["nets"].values())==
      sorted(r["key"] for r in ni["nets"].values()),"Native terminal/public-port partitions changed")
    require(len(old["paths"])==len(new["paths"])==500,"Missing stable identity")
    for a,b in zip(old["paths"],new["paths"]):
        require(a["native_device"]==b["native_device"] and a["model"]==b["model"],"Device identity changed")
        parse_path(a["raw_path"]);parse_path(b["raw_path"])
        require(a["stable_path"]==b["stable_path"],"Stable instance path changed")
    op={p["name"]:p for p in old["native_pins"]};np={p["name"]:p for p in new["native_pins"]}
    require(len(op)==len(old["native_pins"])==len(np)==len(new["native_pins"])==25,"Duplicate/missing public identity")
    require(set(op)==set(np),"Public port names changed")
    for name in op:
        require(op[name]["full_partition"]==np[name]["full_partition"],"Public name/terminal partition changed")
        require(op[name]["full_anchor"]==np[name]["full_anchor"],"Public name/anchor binding changed")
    ol=topology.normalized_locations(old["locations"],oi);nl=topology.normalized_locations(new["locations"],ni)
    for rows,side in ((ol,old),(nl,new)):
        paths={r["native_device"]:r for r in side["paths"]}
        for row in rows["devices"]:
            witness=paths[row["native_id"]]
            require(row["pcell"]["path"]==witness["raw_path"],"Stable witness not bound to exact raw location")
            row["pcell"]["path"]=witness["stable_path"]
    require(ol==nl,"Full semantic device/parameter/location data changed")
    require(topology.normalized_anchors(old["anchors"],oi)==topology.normalized_anchors(new["anchors"],ni),
      "Complete original 978 anchors changed")
    return {"status":"PASS_READ_ONLY_SAVED_NATIVE_IDENTITIES_NO_TOPOLOGY_GATE_CHANGE",
      "devices":500,"terminals":1446,"ports":25,"anchors":978,"native_nets":238,
      "old_native_port_order":[p["name"] for p in old["native_pins"]],
      "new_native_port_order":[p["name"] for p in new["native_pins"]],
      "native_port_ids_preserved_as_evidence_not_assumed_equal":True,
      "all_levels_and_instance_ordinals_and_transforms_equal":True,
      "no_historical_failure_or_acceptance_transferred":True,"physical_accepted":False,"electrical_accepted":False,
      "qualified_pex":False,"topology_comparator_modified":False}

def selected_files(prefix=""):
    return dict(gds=prefix+"parent/layout/"+TOP+".gds",
      lvs=prefix+"parent/physical/lvs_flat/result.lvsdb",inventory=prefix+"wire/pcell-inventory01.json",
      graph=prefix+"wire/native05/result.json",locations=prefix+"wire/device-locations01.json",anchors=prefix+"wire/anchors08.json")

def partition_key(row):
    return json.dumps(dict(terminals=sorted((v["device"],v["model"],v["terminal"])for v in row["device_terminals"]),
      ports=sorted(row["public_ports"])),sort_keys=True,separators=(",",":"))


def component_keys(graph):
    # Frozen graph_index retains all238 partitions, including124 empty native partitions.
    # Only the114 electrical partitions have unique terminal/public identities;113 own conductor.
    index=topology.graph_index(graph)
    nets={row["native_cluster"]:partition_key(row)for row in graph["native_net_coverage"]}
    result={}
    for row in graph["wire_components"]:
        key=nets[row["native_cluster"]]
        require(key not in result,"one exact wire component per complete partition")
        result[key]=row
    require(len(result)==113 and len(index["terminals"])==1446,"complete113 conductor components")
    return nets,result

def target_keys(graph):
    result={}
    for label,device in (("T003_D",3),("T032_D",32)):
        hits=[row for row in graph["native_net_coverage"]if
          dict(device=device,model="sg13_lv_nmos",terminal="D")in row["device_terminals"]]
        require(len(hits)==1,"exact target terminal partition")
        result[label]=partition_key(hits[0])
    require(len(set(result.values()))==2,"two distinct target terminal partitions")
    return result

def exact_union(pya,before,after,box):
    expected=(before+pya.Region(pya.Box(*box))).merged()if box is not None else before
    require((expected^after).is_empty(),"full partition material differs beyond two M1 boxes")

def material_controls(pya):
    # Native Region algebra controls only; these are synthetic, not current layout qualification.
    before=pya.Region(pya.Box(0,0,160,36000));box=[-80,0,240,36000]
    after=pya.Region(pya.Box(*box));exact_union(pya,before,after,box)
    faults=[]
    cases=(("missing_widening",before,box),
           ("foreign_extra_rectangle",after+pya.Region(pya.Box(500,0,600,100)),box),
           ("endpoint_extension",pya.Region(pya.Box(-80,0,240,36005)),box),
           ("undeclared_other_layer",after,None))
    for name,bad,declared in cases:
        try:exact_union(pya,before,bad,declared)
        except AssertionError as exc:faults.append(dict(case=name,error=str(exc)))
        else:raise AssertionError("material fault accepted: "+name)
    return dict(status="PASS_SYNTHETIC_NATIVE_REGION_UNION_CONTROLS",positive=1,faults=faults,
      actual_layout_faults=False,physical_acceptance=False)

def prove_material(pya,selected,view,old,new,config):
    _,a=component_keys(old["graph"]);_,b=component_keys(new["graph"]);require(set(a)==set(b),"full conductor partition identity")
    keys=target_keys(old["graph"]);require(keys==target_keys(new["graph"]),"actual same target terminal identities")
    ow=pya.LayoutToNetlist();ow.read(str(selected/config["paths"]["wires"]))
    nw=pya.LayoutToNetlist();nw.read(str(view/"wire/native05/wires.l2n"))
    on={n.cluster_id:n for n in ow.netlist().top_circuit().each_net()}
    nn={n.cluster_id:n for n in nw.netlist().top_circuit().each_net()}
    require(set(on)=={r["component"]for r in a.values()}and set(nn)=={r["component"]for r in b.values()},"full native wire net census")
    boxes={keys["T003_D"]:config["rectangles"][0]["new"],keys["T032_D"]:config["rectangles"][1]["new"]}
    records=[]
    for key in sorted(a):
        before,after=a[key],b[key]
        for layer in (8,10,30,50,67,126,134,19,29,49,66,125,133):
            empty_old=old["graph"]["layers"][str(layer)]["explicitly_empty"]
            empty_new=new["graph"]["layers"][str(layer)]["explicitly_empty"]
            require(type(empty_old)is bool and empty_old==empty_new,"full conductor layer presence")
            ol=ow.layer_by_name("gds_"+str(layer));nl=nw.layer_by_name("gds_"+str(layer))
            if empty_old:
                require(ol is None and nl is None,"unregistered empty native layer")
                left=pya.Region();right=pya.Region()
            else:
                require(ol is not None and nl is not None,"all original conductor layers")
                left=ow.shapes_of_net(on[before["component"]],ol,True).merged()
                right=nw.shapes_of_net(nn[after["component"]],nl,True).merged()
            exact_union(pya,left,right,boxes.get(key)if layer==8 else None)
            records.append(dict(partition=json.loads(key),old_component=before["component"],new_component=after["component"],
              old_native_cluster=before["native_cluster"],new_native_cluster=after["native_cluster"],layer=layer,
              old_area_dbu2=left.area(),new_area_dbu2=right.area(),declared_addition=boxes.get(key)if layer==8 else None))
    return dict(status="PASS_ALL113_COMPONENTS_13LAYERS_EXACT_TWO_M1_UNIONS",records=records,
      targets={label:dict(full_partition=json.loads(key),old=a[key],new=b[key])for label,key in keys.items()},
      resistor_reduction_identity_assumed=False,transient_voltage_recovery_proved=False)

def verify(selected,physical,out,config):
    import pya
    view=verify_sources(out,config)
    planes=h.decode((view/"native-planes.json").read_bytes());recover=h.decode((view/"wire/source-pins.json").read_bytes())
    require(planes["status"]=="PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS"and len(planes["anchors"])==160 and len(planes["controls"])==19,"all native planes/faults")
    require(len(planes["parent_geometry"]["controls"])==5 and len(planes["parent_geometry"]["actual_placements"])==16 and len(planes["parent_geometry"]["checked_layers_by_kind"])==9,"original independent leaves/placements")
    require(recover["status"]=="PASS_RECOVERED_SOURCE_PIN_BOXES_ON_IDENTICAL_PRIMITIVE_DRAWING"and recover["target_gds_sha256"]==config["physical"]["gds"]["sha256"]and recover["target_geometry_edited"]is False,"source pin recovery")
    producer=h.ROOT/original.WIRE_SOURCE/"locate01.py"
    oldlayout,old=identities.read_side(pya,selected,selected_files(BASE),producer)
    newlayout,new=identities.read_side(pya,view,selected_files(),producer)
    h.write(out/"old-native-identity.json",h.encode(old));h.write(out/"new-native-identity.json",h.encode(new))
    comparison=compare_witnesses(old,new);h.write(out/"native-identity-comparison.json",h.encode(comparison))
    faults=identities.witness_controls(old,new);h.write(out/"actual-witness-faults.json",h.encode(faults))
    h.write(out/"native-material-controls.json",h.encode(material_controls(pya)))
    material_proof=prove_material(pya,selected,view,old,new,config)
    h.write(out/"full-partition-material.json",h.encode(material_proof))
    reports={"parent-geometry":planes["parent_geometry"],"planes":planes,"source-pins":recover,
      "graph":new["graph"],"locations":new["locations"],"anchors":new["anchors"]}
    bindings={name:original.report_inputs(report,view)for name,report in reports.items()}
    inventory={p.relative_to(view).as_posix():h.pin(p)for p in sorted(view.rglob("*"))if p.is_file()}
    require(len(inventory)==75 and "result.json"not in inventory,"fresh complete75 current view, no fabricated root result")
    h.write(out/"candidate-inventory.json",h.encode(inventory))
    result=dict(status="PASS_FRESH_TWO_M1_GRAPH_IDENTITIES_FULL_PARTITION_UNIONS_REQUIRES_RC",
      candidate_gds=config["physical"]["gds"],candidate_lvs=config["physical"]["lvs"],current_files=inventory,
      actual_native_identity=comparison,material= h.pin(out/"full-partition-material.json"),
      fresh_report_bindings=bindings,physical_producer=config["physical"]["producer"],
      fresh_RC_executed=False,electrical_acceptance=False,physical_acceptance=False,full_phy_accepted=False)
    h.write(out/"graph-qualification.json",h.encode(result));return result

def main():
    p=argparse.ArgumentParser();p.add_argument("--mode",required=True,choices=("prepare","planes","recover","verify"))
    for name in ("selected","physical","output"):p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--pins-sha256",required=True);a=p.parse_args();config,_,_=h.source_guard(a.pins_sha256)
    ctx=h.context(__import__("os").environ)
    require(h.decode((a.output/"preflight.json").read_bytes())["current_context"]==ctx,"same-source current preflight")
    require(all(h.pin(h.frozen.regular(a.selected,n))["sha256"]==v for n,v in config["selected"].items()),"selected old source")
    require(all(h.pin(h.frozen.regular(a.physical,n))["sha256"]==config["physical"]["full"][n]for n in config["physical"]["selected"]),"selected physical source")
    if a.mode=="prepare":prepare(a.selected,a.physical,a.output,config)
    elif a.mode in ("planes","recover"):derived(a.mode,a.output,config)
    else:verify(a.selected,a.physical,a.output,config)
    h.source_guard(a.pins_sha256)
if __name__=="__main__":main()
