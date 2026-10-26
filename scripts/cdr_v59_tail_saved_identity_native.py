#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read existing GDS/LVS databases; never generate, extract, route, or write CAD."""
import collections
import copy
import json
import re
from pathlib import Path
import cdr_v59_tail_saved_identity as source
import cdr_v59_tail_access_topology as topology

TOP="nssoc_cdr_pd500_resistor_v59"
CHILD="pd_child_sampler_cd"
MODELS={"npn13G2":"npn13G2","rppd":"rppd","ptap1":"ptap1","cmim":"cap_cmim","nmos":"sg13_lv_nmos"}

def require(value,message):
    if not value:raise AssertionError(message)

def parse_path(value):
    require(isinstance(value,str),"Path is not text")
    pieces=value.split("/")
    require(pieces[0]==TOP and len(pieces)>1,"Wrong root or empty instance path")
    result=[]
    for piece in pieces[1:]:
        match=re.fullmatch(r"(0|[1-9][0-9]*)_(0|[1-9][0-9]*)",piece)
        require(match is not None,"Malformed cell-index/instance-ordinal token")
        result.append(tuple(map(int,match.groups())))
    return result

def stable_path(pya,layout,row):
    path=parse_path(row["pcell"]["path"])
    cell=layout.cell(TOP);require(cell is not None,"Missing top cell")
    transform=pya.DCplxTrans();levels=[]
    for child_index,ordinal in path:
        instances=list(cell.each_inst())
        require(ordinal<len(instances),"Instance ordinal is absent")
        inst=instances[ordinal]
        require(not inst.is_regular_array(),"Regular array is outside exact original producer scope")
        require(inst.cell_index==child_index,"Recorded child cell index does not resolve")
        child=layout.cell(child_index);require(child is not None,"Missing child cell")
        levels.append({"parent_cell":cell.name,"child_cell":child.name,
          "instance_ordinal":ordinal,"cplx_trans_dbu":str(inst.cplx_trans),
          "dcplx_trans_um":str(inst.dcplx_trans),"na":inst.na,"nb":inst.nb,
          "array_vector_a_dbu":str(inst.a),"array_vector_b_dbu":str(inst.b),
          "is_regular_array":False,"array_element":None})
        transform=transform*inst.dcplx_trans
        cell=child
    require(not list(cell.each_inst()),"Recorded primitive is not a leaf")
    require(cell.name==row["pcell"]["cell"],"Resolved primitive cell name changed")
    require(str(transform)==row["pcell"]["transform"],"Resolved full transform changed")
    require(str(cell.dbbox().transformed(transform))==row["pcell"]["bbox"],"Resolved primitive bbox changed")
    return {"root":TOP,"levels":levels,"leaf_cell":cell.name,
      "full_transform_um":str(transform),"leaf_bbox_um":str(cell.dbbox().transformed(transform))}

def inventory(pya,layout,producer):
    """Execute only the byte-pinned original visit() definition, never its main."""
    namespace={"g":layout,"leaves":[]}
    source.load_definitions(producer,["visit"],namespace)
    namespace["visit"](layout.cell(TOP),pya.DCplxTrans(),TOP)
    return namespace["leaves"]

def read_side(pya,root,files,producer):
    layout=pya.Layout();layout.read(str(root/files["gds"]))
    require(layout.dbu==0.001,"Changed DBU")
    require(layout.cell(TOP) is not None and layout.cell(TOP).cell_index() in
      [c.cell_index() for c in layout.top_cells()],"Wrong top")
    saved_inventory=source.read_json(root/files["inventory"])
    actual_inventory=inventory(pya,layout,producer)
    require(actual_inventory==saved_inventory,"Full saved primitive inventory does not reproduce")
    locations=source.read_json(root/files["locations"])
    graph=source.read_json(root/files["graph"]);anchors=source.read_json(root/files["anchors"])
    index=topology.graph_index(graph)
    topology.normalized_locations(locations,index);topology.normalized_anchors(anchors,index)
    physical=[r for r in actual_inventory if r["cell"].split("$")[0] in MODELS]
    require(len(physical)==500,"Wrong native primitive inventory census")
    by_path={r["path"]:r for r in physical}
    require(len(by_path)==500,"Duplicate physical primitive paths")
    lvs=pya.LayoutVsSchematic();lvs.read(str(root/files["lvs"]))
    circuit=lvs.netlist().top_circuit()
    devices={d.id():d for d in circuit.each_device()}
    require(set(devices)==set(range(1,501)),"Changed saved native device IDs")
    native_partitions=collections.defaultdict(list)
    witnesses=[];used=set()
    for row in locations["devices"]:
        ident=row["native_id"];device=devices[ident];cls=device.device_class()
        require(cls.name==row["model"],"Native device model changed")
        require({p.name:device.parameter(p.id()) for p in cls.parameter_definitions()}==row["parameters"],
          "Native device parameters changed")
        require(by_path.get(row["pcell"]["path"])==row["pcell"],"Location does not bind exact full inventory row")
        require(row["pcell"]["path"] not in used,"Primitive reused")
        used.add(row["pcell"]["path"])
        native_terminals=[]
        for td in cls.terminal_definitions():
            net=device.net_for_terminal(td.id())
            native_partitions[net.cluster_id].append((ident,cls.name,td.name))
            shapes=lvs.shapes_of_terminal(device.terminal_ref(td.id()))
            require(bool(shapes),"Missing native terminal geometry")
            native_terminals.append({"name":td.name,"net":net.name,"native_cluster":net.cluster_id,
              "native_layers":[{"layer":i,"bbox_dbu":str(r.bbox()),"area_dbu2":r.area(),"polygons":r.count()}
                for i,r in shapes.items()]})
        require(native_terminals==row["terminals"],"Native terminal shape/name binding changed")
        witnesses.append({"native_device":ident,"model":row["model"],
          "raw_path":row["pcell"]["path"],"stable_path":stable_path(pya,layout,row)})
    require(len(used)==500,"Incomplete physical identity coverage")
    pins=[{"iteration_index":i,"native_pin_id":p.id(),"name":p.name(),
      "native_cluster":circuit.net_for_pin(p.id()).cluster_id}
      for i,p in enumerate(circuit.each_pin())]
    require(len(pins)==25 and len({p["native_pin_id"] for p in pins})==25,"Native pin identity census changed")
    require([p["name"] for p in pins]==graph["native_ports"],"Saved native pin iteration order does not reproduce")
    port_anchors={a["detail"]["public_port"]:a for a in anchors["anchors"] if "public_port" in a["detail"]}
    require(len(port_anchors)==25,"Public anchor census changed")
    for pin in pins:
        cluster=pin["native_cluster"];net=index["nets"][cluster]
        require(pin["name"] in net["row"]["public_ports"],"Native pin name/cluster membership changed")
        require(port_anchors[pin["name"]]["native_cluster"]==cluster,"Public anchor native cluster changed")
        pin["full_partition"]=json.loads(net["key"])
        pin["full_anchor"]=topology.normalize(port_anchors[pin["name"]],index)
    for cluster,row in index["nets"].items():
        require(sorted(native_partitions.get(cluster,[]))==
          sorted((x["device"],x["model"],x["terminal"]) for x in row["row"]["device_terminals"]),
          "Saved native terminal partition does not reproduce")
    return layout,{"graph":graph,"locations":locations,"anchors":anchors,
      "full_inventory":saved_inventory,"paths":sorted(witnesses,key=lambda r:r["native_device"]),
      "native_pins":pins,"native_device_count":500,"native_terminal_count":1446}

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
      "original_native_failure_preserved":True,"physical_accepted":False,"electrical_accepted":False,
      "qualified_pex":False,"topology_comparator_modified":False}

def raw_hierarchy_proof(old_layout,new_layout,generation,generator):
    scope={"json":json}
    source.load_definitions(generator,["raw_records","hierarchy"],scope)
    names={c.name for c in old_layout.each_cell()}
    require(names=={c.name for c in new_layout.each_cell()},"Cell-name inventory changed")
    require(old_layout.cell(TOP).bbox()==new_layout.cell(TOP).bbox(),"Top bbox changed")
    added=collections.Counter(tuple(v) for v in generation["added_raw_records"])
    require(bool(added),"Missing original generation additive records")
    proof=[]
    for name in sorted(names):
        old=old_layout.cell(name);new=new_layout.cell(name)
        a=scope["raw_records"](old_layout,old);b=scope["raw_records"](new_layout,new)
        ha=scope["hierarchy"](old);hb=scope["hierarchy"](new)
        require(ha==hb,"Original named hierarchy changed")
        require(collections.Counter(b)==collections.Counter(a)+(added if name==CHILD else collections.Counter()),
          "Original shape/text/properties or exact added records changed")
        proof.append({"cell":name,"original_raw_records":len(a),"current_raw_records":len(b),
          "original_raw_sha256":source.value_hash(a),"current_raw_sha256":source.value_hash(b),
          "exact_named_hierarchy":ha,"hierarchy_sha256":source.value_hash(ha),
          "original_raw_preserved":True,"exact_added_records_only":name==CHILD})
    return {"all_original_cell_names_preserved":True,"full_raw_shape_text_properties_preserved":True,
      "exact_original_named_hierarchy_preserved":True,"cells":proof,"added_raw_records":generation["added_raw_records"]}

def run(root,out):
    import pya
    source.authorize()
    manifest=source.expected_files();source.verify_inputs(root,manifest)
    producer=source.ROOT/source.LOCATE
    old_layout,old=read_side(pya,root,source.SIDES["old"],producer)
    source.write(out/"original-identity.json",old)
    new_layout,new=read_side(pya,root,source.SIDES["new"],producer)
    source.write(out/"current-identity.json",new)
    generation=source.read_json(root/source.GENERATION)
    rawproof=raw_hierarchy_proof(old_layout,new_layout,generation,source.ROOT/source.GENERATOR)
    source.write(out/"raw-hierarchy-proof.json",rawproof)
    # Reproduce the actual unmodified first failure at its exact original source assertion.
    try:topology.compare([old[k] for k in ("graph","locations","anchors")],
                         [new[k] for k in ("graph","locations","anchors")],True)
    except AssertionError as error:
        tb=error.__traceback__
        while tb.tb_next:tb=tb.tb_next
        require(Path(tb.tb_frame.f_code.co_filename).resolve()==Path(topology.__file__).resolve()
          and tb.tb_frame.f_code.co_name=="compare" and tb.tb_lineno==107 and not error.args,
          "Original failure was not reproduced at exact native_ports equality")
        rejection={"error":repr(error),"file":str(Path(topology.__file__).relative_to(source.ROOT)),
          "function":"compare","line":107,"original_comparator_sha256":source.sha(Path(topology.__file__))}
    else:raise AssertionError("Original comparator unexpectedly accepted")
    source.write(out/"original-comparator-rejection.json",rejection)
    comparison=compare_witnesses(old,new)
    source.write(out/"identity-comparison.json",comparison)
    source.verify_inputs(root,manifest)
    return comparison

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();require(a.out.is_dir() and not a.out.is_symlink(),"Missing dedicated report directory")
    run(a.root,a.out)
