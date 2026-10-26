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

def properties(inst):
    rows=[{"key_type":type(k).__name__,"key":k,"value_type":type(v).__name__,"value":v}
      for k,v in inst.properties().items()]
    return sorted(rows,key=lambda r:json.dumps(r,sort_keys=True,separators=(",",":"),allow_nan=False))

def stable_path(pya,layout,row):
    path=parse_path(row["pcell"]["path"])
    cell=layout.cell(TOP);require(cell is not None,"Missing top cell")
    transform=pya.DCplxTrans();levels=[]
    for child_index,ordinal in path:
        instances=list(cell.each_inst())
        require(ordinal<len(instances),"Instance ordinal is absent")
        inst=instances[ordinal]
        require(not inst.is_regular_array(),"Regular array is outside exact original producer scope")
        require(inst.size()==1,"Iterated or multiple instance elements are outside exact original producer scope")
        require(inst.cell_index==child_index,"Recorded child cell index does not resolve")
        child=layout.cell(child_index);require(child is not None,"Missing child cell")
        levels.append({"parent_cell":cell.name,"child_cell":child.name,
          "instance_ordinal":ordinal,"cplx_trans_dbu":str(inst.cplx_trans),
          "dcplx_trans_um":str(inst.dcplx_trans),"na":inst.na,"nb":inst.nb,
          "array_vector_a_dbu":str(inst.a),"array_vector_b_dbu":str(inst.b),
          "is_regular_array":False,"single_instance_count":inst.size(),"array_element":0,
          "instance_properties":properties(inst)})
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
        native_terminals=[];box=pya.Box()
        body={("npn13G2","S"),("sg13_lv_nmos","B"),("sg13_hv_nmos","B"),("sg13_hv_pmos","B"),
          ("rppd","rppd_sub"),("ptap1","WELL"),("ntap1","WELL")}
        for td in cls.terminal_definitions():
            net=device.net_for_terminal(td.id())
            native_partitions[net.cluster_id].append((ident,cls.name,td.name))
            shapes=lvs.shapes_of_terminal(device.terminal_ref(td.id()))
            require(bool(shapes),"Missing native terminal geometry")
            terminal_box=pya.Box()
            for region in shapes.values():terminal_box+=region.bbox()
            if (cls.name,td.name) not in body:box+=terminal_box
            native_terminals.append({"name":td.name,"net":net.name,"native_cluster":net.cluster_id,
              "native_layers":[{"layer":i,"bbox_dbu":str(r.bbox()),"area_dbu2":r.area(),"polygons":r.count()}
                for i,r in shapes.items()]})
        require(native_terminals==row["terminals"],"Native terminal shape/name binding changed")
        candidates=[r for r in physical if MODELS[r["cell"].split("$")[0]]==cls.name and
          (pya.DBox.from_s(r["bbox"]).to_itype(layout.dbu)&box)==box]
        require(len(candidates)==1 and candidates[0]==row["pcell"],"Native primitive enclosure is not the exact unique saved leaf")
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

def witness_controls(old,new):
    """Mutate copies of the complete acquired witness; never touch saved native inputs."""
    cases=[
      ("primitive_model",lambda b:b["paths"][0].update(model="wrong"),"Device identity changed"),
      ("hierarchy_child_name",lambda b:b["paths"][0]["stable_path"]["levels"][0].update(child_cell="wrong"),"Stable instance path changed"),
      ("hierarchy_parent_name",lambda b:b["paths"][0]["stable_path"]["levels"][0].update(parent_cell="wrong"),"Stable instance path changed"),
      ("instance_ordinal",lambda b:b["paths"][0]["stable_path"]["levels"][0].update(instance_ordinal=-1),"Stable instance path changed"),
      ("instance_transform",lambda b:b["paths"][0]["stable_path"]["levels"][0].update(cplx_trans_dbu="wrong"),"Stable instance path changed"),
      ("instance_properties",lambda b:b["paths"][0]["stable_path"]["levels"][0].update(instance_properties=[{"unexpected":True}]),"Stable instance path changed"),
      ("array_element",lambda b:b["paths"][0]["stable_path"]["levels"][0].update(array_element=1),"Stable instance path changed"),
      ("path_depth",lambda b:b["paths"][0]["stable_path"]["levels"].pop(),"Stable instance path changed"),
      ("public_partition",lambda b:b["native_pins"][0]["full_partition"]["terminals"].pop(),"Public name/terminal partition changed"),
      ("public_anchor",lambda b:b["native_pins"][0]["full_anchor"].update(point_dbu=[-1,-1]),"Public name/anchor binding changed"),
      ("device_parameter",lambda b:b["locations"]["devices"][0]["parameters"].update(W=-1),"Full semantic device/parameter/location data changed"),
      ("terminal_anchor",lambda b:b["anchors"]["anchors"][0].update(point_dbu=[-1,-1]),"Complete original 978 anchors changed")]
    records=[]
    for name,change,message in cases:
        require(compare_witnesses(old,new)["devices"]==500,"Baseline identity failed before witness mutation")
        bad=copy.deepcopy(new);change(bad)
        try:compare_witnesses(old,bad)
        except AssertionError as error:
            require(str(error)==message,"Unqualified witness mutation rejection")
            records.append({"case":name,"complete_positive_before_fault":True,"error":str(error)})
        else:raise AssertionError("Accepted witness mutation "+name)
    require(len(records)==12,"Incomplete acquired-witness controls")
    return {"status":"PASS_COMPLETE_ACQUIRED_WITNESS_MUTATION_CONTROLS","positive_copies":12,
      "refusals":records,"saved_native_inputs_mutated":False}

def emit_raw_hierarchy_diagnostic(old_layout,new_layout,generation,generator,path,context):
    """Preserve complete raw representations before the unchanged admission guard."""
    scope={"json":json}
    source.load_definitions(generator,["raw_records","hierarchy"],scope)
    def rows(counter):
        return [{"record":list(record),"multiplicity":count}
          for record,count in sorted(counter.items())]
    def layers(layout):
        return [{"native_layer_index":i,"gds_layer":layout.get_info(i).layer,
          "gds_datatype":layout.get_info(i).datatype} for i in layout.layer_indexes()]
    old_names={c.name for c in old_layout.each_cell()}
    new_names={c.name for c in new_layout.each_cell()}
    added=collections.Counter(tuple(v) for v in generation["added_raw_records"])
    cells=[]
    for name in sorted(old_names|new_names):
        old=old_layout.cell(name);new=new_layout.cell(name)
        a=[] if old is None else scope["raw_records"](old_layout,old)
        b=[] if new is None else scope["raw_records"](new_layout,new)
        ca=collections.Counter(a);cb=collections.Counter(b)
        allowed=added if name==CHILD else collections.Counter()
        expected=ca+allowed
        ha=None if old is None else scope["hierarchy"](old)
        hb=None if new is None else scope["hierarchy"](new)
        def instances(cell):
            if cell is None:return None
            return [{"child":i.cell.name,"ordinal":j,"properties":properties(i)}
              for j,i in enumerate(cell.each_inst())]
        pa=instances(old);pb=instances(new)
        cells.append({"cell":name,"is_target_child":name==CHILD,
          "original_present":old is not None,"current_present":new is not None,
          "original_cell_index":None if old is None else old.cell_index(),
          "current_cell_index":None if new is None else new.cell_index(),
          "original_raw_counter":rows(ca),"current_raw_counter":rows(cb),
          "expected_raw_counter":rows(expected),"allowed_added_counter":rows(allowed),
          "original_record_deficits":rows(ca-cb),"actual_added_counter":rows(cb-ca),
          "expected_record_deficits":rows(expected-cb),"unexpected_record_counter":rows(cb-expected),
          "signed_current_minus_original":[{"record":list(r),"delta":cb[r]-ca[r]}
            for r in sorted(set(ca)|set(cb)) if cb[r]!=ca[r]],
          "original_raw_record_count":len(a),"current_raw_record_count":len(b),
          "original_raw_ordered_sha256":source.value_hash(a),
          "current_raw_ordered_sha256":source.value_hash(b),
          "original_named_hierarchy":ha,"current_named_hierarchy":hb,
          "original_instance_properties_and_order":pa,"current_instance_properties_and_order":pb,
          "raw_counter_equal_expected":cb==expected,
          "named_hierarchy_equal":ha==hb,"instance_properties_and_order_equal":pa==pb})
    diagnostic={"schema":"cdr-saved-raw-hierarchy-complete-diagnostic-v1",
      "status":"DIAGNOSTIC_ONLY_BEFORE_UNCHANGED_RAW_HIERARCHY_ASSERTIONS",
      "qualified":False,"physical_accepted":False,"original_failure_preserved":True,
      "counter_records_are_complete":True,"counter_multiplicity_retained":True,
      "representation_normalization_applied":False,"material_equivalence_inferred":False,
      "raw_record_schema":["gds_layer_integer","gds_datatype_integer","exact_shape_to_s",
        "exact_properties_json_string","is_text_boolean"],
      "source_identity":context,"generator_path":str(generator),"generator_sha256":source.sha(generator),
      "original_dbu_um":old_layout.dbu,"current_dbu_um":new_layout.dbu,
      "original_top_bbox_dbu":str(old_layout.cell(TOP).bbox()),
      "current_top_bbox_dbu":str(new_layout.cell(TOP).bbox()),
      "original_layer_inventory":layers(old_layout),"current_layer_inventory":layers(new_layout),
      "original_cell_names":sorted(old_names),"current_cell_names":sorted(new_names),
      "original_generation_report":generation,"prewrite_added_raw_counter":rows(added),"cells":cells,
      "raw_counter_mismatch_cells":[r["cell"] for r in cells if not r["raw_counter_equal_expected"]],
      "non_target_original_deficit_cells":[r["cell"] for r in cells
        if not r["is_target_child"] and r["original_record_deficits"]],
      "hierarchy_mismatch_cells":[r["cell"] for r in cells if not r["named_hierarchy_equal"]],
      "instance_property_mismatch_cells":[r["cell"] for r in cells
        if not r["instance_properties_and_order_equal"]]}
    source.write(path,diagnostic)
    return diagnostic

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
        old_props=[{"child":i.cell.name,"ordinal":j,"properties":properties(i)} for j,i in enumerate(old.each_inst())]
        new_props=[{"child":i.cell.name,"ordinal":j,"properties":properties(i)} for j,i in enumerate(new.each_inst())]
        require(old_props==new_props,"Complete instance property/order binding changed")
        require(collections.Counter(b)==collections.Counter(a)+(added if name==CHILD else collections.Counter()),
          "Original shape/text/properties or exact added records changed")
        proof.append({"cell":name,"original_raw_records":len(a),"current_raw_records":len(b),
          "original_raw_sha256":source.value_hash(a),"current_raw_sha256":source.value_hash(b),
          "exact_named_hierarchy":ha,"hierarchy_sha256":source.value_hash(ha),
          "exact_instance_property_and_order":old_props,
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
    # Diagnostic data is durable before any original raw/hierarchy assertion.
    # A diagnostic never changes the original guard or qualifies failed geometry.
    context={"saved_capsule_run":source.RUN,"saved_capsule_source":source.HEAD,
      "saved_manifest_sha256":source.value_hash(manifest),
      "generation_member":source.GENERATION,
      "saved_files":{member:{"expected_sha256":manifest[member],
        "actual_sha256":source.sha(root/member)}
        for member in [source.GENERATION]+[v for side in source.SIDES.values() for v in side.values()]},
      "programs":{p:source.sha(source.ROOT/p) for p in
        (source.GENERATOR,source.LOCATE,"scripts/cdr_v59_tail_saved_identity_native.py",
         "scripts/cdr_v59_tail_access_topology.py")},
      "methods_sha256":source.sha(source.METHOD)}
    emit_raw_hierarchy_diagnostic(old_layout,new_layout,generation,source.ROOT/source.GENERATOR,
      out/"raw-hierarchy-diagnostic.json",context)
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
    controls=witness_controls(old,new)
    source.write(out/"acquired-witness-controls.json",controls)
    source.verify_inputs(root,manifest)
    return comparison

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();require(a.out.is_dir() and not a.out.is_symlink(),"Missing dedicated report directory")
    run(a.root,a.out)
