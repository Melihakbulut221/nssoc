#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read existing native geometry. Point matches are not resistor footprints."""
import argparse,collections,hashlib,json,re,shlex,traceback
from pathlib import Path
import cloud_cdr_current_access_overlay as host
require=host.require
TOP="nssoc_cdr_pd500_resistor_v59"
METALS=(8,10,30,50,67,126,134)
VIAS=(19,29,49,66,125,133)
LAYERS=METALS+VIAS
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

def point_rows(target):
    nodes=target["nodes"];mapping={r["native"]:r["loaded"]for r in nodes}
    require(len(nodes)==len(mapping)==102 and len(set(mapping.values()))==102,"complete distinct 102 nodes")
    result=[];seen=set()
    for row in target["native_primitive_records"]:
        tokens=shlex.split(row["raw"])
        require(tokens==row["tokens"],"raw primitive tokens")
        if tokens[0]!="rnode":continue
        require(len(tokens)==7 and tokens[1]in mapping and tokens[1]not in seen,"unique current rnode")
        require(tokens[-1]=="0","literal hardcoded type zero")
        require(all(re.fullmatch("[+-]?[0-9]+",v)is not None for v in tokens[4:6]),"integer raw coordinates")
        point=[int(v)*5 for v in tokens[4:6]];seen.add(tokens[1])
        result.append(dict(native_node=tokens[1],loaded_node=mapping[tokens[1]],source_record=row,
          point_dbu=point,coordinate_nm_per_raw_unit=5,coordinate_frame="top-level pump_wires",
          native_type_token=tokens[-1],type_token_is_layer=False,second_transform_applied=False))
    require(seen==set(mapping),"complete rnode coordinate census")
    return result

def candidates(pya,point,polygons):
    require(len(point)==2 and all(type(v)is int for v in point),"integer point")
    p=pya.Point(*point);box=pya.Region(pya.Box(point[0]-2,point[1]-2,point[0]+2,point[1]+2))
    exact=[];near=[]
    for ident,poly in polygons:
        if poly.inside(p):exact.append(ident)
        if not(pya.Region(poly)&box).is_empty():near.append(ident)
    return dict(point_dbu=point,contains_or_boundary=exact,quantization_box_positive_area_overlap=near,
      search_halfwidth_dbu=2,search_box_is_not_footprint=True,
      disposition="NO_MATCH"if not exact else "ONE_POINT_MATCH_NOT_OWNERSHIP"if len(exact)==1 else "MULTIPLE_POINT_MATCHES",
      resistor_layer_assigned=False,resistor_footprint_assigned=False)

def polygon_record(poly,ident,layer,component,owner):
    return dict(id=ident,gds_layer=layer,gds_datatype=0,kind="metal"if layer in METALS else"via",
      component=component,native_cluster=owner["native_cluster"],native_name=owner["native_name"],
      hull_dbu=[[p.x,p.y]for p in poly.each_point_hull()],
      holes_dbu=[[[p.x,p.y]for p in poly.each_point_hole(i)]for i in range(poly.holes())],
      native_polygon=poly.to_s(),bbox_dbu=str(poly.bbox()),area_dbu2=poly.area())

def raw_geometry(layout):
    # Complete raw conductor cell records and hierarchy, retaining order/multiplicity.
    cells=[]
    for cell in layout.each_cell():
        rows=[]
        for index in layout.layer_indexes():
            info=layout.get_info(index)
            if info.layer not in LAYERS or info.datatype!=0:continue
            for ordinal,shape in enumerate(cell.shapes(index).each()):
                rows.append(dict(gds_layer=info.layer,gds_datatype=info.datatype,ordinal=ordinal,
                  native_shape=shape.to_s(),is_text=shape.is_text(),properties=properties(shape)))
        instances=[dict(ordinal=i,child_index=inst.cell_index,child_cell=inst.cell.name,
          cplx_trans_dbu=str(inst.cplx_trans),dcplx_trans_um=str(inst.dcplx_trans),na=inst.na,nb=inst.nb,
          a=str(inst.a),b=str(inst.b),size=inst.size(),properties=properties(inst))
          for i,inst in enumerate(cell.each_inst())]
        cells.append(dict(cell=cell.name,cell_index=cell.cell_index(),records=rows,instances=instances))
    return dict(cells=cells,datatype=0,layers=list(LAYERS),multiplicity_preserved=True,
      merged_polygon_to_single_raw_shape_attribution=False)

def observe(pya,selected,config,root,persist=lambda name,value:None):
    files=config["paths"]
    before={n:host.pin(host.frozen.regular(selected,n))for n in config["selected"]}
    require(all(v["sha256"]==config["selected"][n]for n,v in before.items()),"selected native input bytes")
    def read(key):return host.decode(host.frozen.regular(selected,files[key]).read_bytes())
    graph=read("graph");geo=read("locations");anchors=read("anchors");precise=read("precise_anchors")
    incidence=host.decode(host.frozen.regular(root,config["incidence"]).read_bytes())
    source_pins=read("pins");inventory=read("inventory")
    require((graph["native_device_count"],graph["native_terminal_count"],graph["wire_component_count"],graph["native_net_count"])==(500,1446,113,238),"current full graph census")
    g=pya.Layout();g.read(str(selected/files["gds"]));require(g.dbu==0.001,"one nm layout DBU")
    top=g.cell(TOP);require(top is not None and top.cell_index()in[c.cell_index()for c in g.top_cells()],"exact top")
    wire_gds=pya.Layout();wire_gds.read(str(selected/files["wire_gds"]))
    require(wire_gds.dbu==g.dbu and len(list(wire_gds.top_cells()))==1,"wire flat layout DBU/top")
    wire_top=list(wire_gds.top_cells())[0]
    lvs=pya.LayoutVsSchematic();lvs.read(str(selected/files["lvs"]));c=lvs.netlist().top_circuit()
    devices={d.id():d for d in c.each_device()}
    require(len(devices)==500 and c.pin_count()==25 and len(list(c.each_net()))==238,"native full census")
    require(sum(len(list(d.device_class().terminal_definitions()))for d in devices.values())==1446,"native terminal census")
    require(dict(collections.Counter(d.device_class().name for d in devices.values()))==graph["native_devices"],"native device models")
    w=pya.LayoutToNetlist();w.read(str(selected/files["wires"]));nets={n.cluster_id:n for n in w.netlist().top_circuit().each_net()}
    owners={r["component"]:r for r in graph["wire_components"]}
    require(len(owners)==113 and set(nets)==set(owners),"all wire component IDs")
    require(len({r["native_cluster"]for r in owners.values()})==113,"no split native partition")
    native={n.cluster_id:n for n in c.each_net()}
    for owner in owners.values():
        require(native[owner["native_cluster"]].name==owner["native_name"],"complete native names")
    regions={};layerproof={};polygons=[];records={};selected_ids=[]
    target_components={r["component"]for r in config["targets"].values()}
    for layer in LAYERS:
        full=pya.Region(top.begin_shapes_rec(g.layer(layer,0))).merged()
        flat=pya.Region(wire_top.begin_shapes_rec(wire_gds.layer(layer,0))).merged()
        require((full^flat).is_empty(),"GDS/wire full layer union")
        if full.is_empty():
            layerproof[str(layer)]=dict(empty=True,polygons=0,area_dbu2=0);continue
        layer_object=w.layer_by_name("gds_"+str(layer))
        require(layer_object is not None and (full^layer_object).is_empty(),"wire database/full GDS layer union")
        expected=graph["layers"][str(layer)]
        require(full.area()==expected["area_dbu2"]and full.count()==expected["polygons"],"saved complete layer census")
        require(hashlib.sha256("\n".join(sorted(p.to_s()for p in full.each())).encode()).hexdigest()==expected["source_union_sha256"],"saved layer geometry digest")
        collected=pya.Region()
        for component,n in sorted(nets.items()):
            piece=w.shapes_of_net(n,layer_object,True);collected+=piece
            if layer in METALS:
                nr=lvs.shapes_of_net(native[owners[component]["native_cluster"]],lvs.layer_by_index(graph["native_layer_mapping"][str(layer)]),True)
                require((piece-nr).is_empty(),"wire crosses native partition")
                row=owners[component]["layers"][str(layer)]
                require(piece.area()==row["area_dbu2"]and piece.count()==row["polygons"],"component layer census")
            for ordinal,poly in enumerate(sorted(piece.each(),key=lambda p:p.to_s())):
                ident=str(component)+":"+str(layer)+":"+str(ordinal)
                polygons.append((ident,poly));records[ident]=polygon_record(poly,ident,layer,component,owners[component])
                if component in target_components:selected_ids.append(ident)
        require((collected.merged()^full).is_empty(),"complete component layer cover")
        regions[layer]=layer_object
        layerproof[str(layer)]=dict(empty=False,polygons=full.count(),area_dbu2=full.area(),
          full_GDS_wire_database_union_equal=True,metal_native_partition_checked=layer in METALS)
    persist("verified-target-polygons.json",dict(layer_checks=layerproof,polygons=[records[i]for i in selected_ids],scope=host.FLAGS))
    bylocation={row["native_id"]:row for row in geo["devices"]}
    require(len(bylocation)==500,"complete location census")
    ext=host.frozen.native_rows(host.frozen.regular(selected,files["ext"]).read_text())
    replacement=host.frozen.native_rows(host.frozen.regular(selected,files["res_ext"]).read_text())
    require([r["tokens"][1:]for r in ext if r["tokens"][0]=="scale"]==[r["tokens"][1:]for r in replacement if r["tokens"][0]=="scale"]==[["1000","1","0.5"]],"authenticated ext scale")
    primitive_lines=host.frozen.regular(selected,files["res_ext"]).read_text().splitlines()
    result={};candidate_ids=set()
    for key,identity in config["targets"].items():
        target=incidence["targets"][key];nid=int(key);component=identity["component"]
        require((target["native_cluster"],target["native_net"],target["component"])==(nid,identity["native_name"],component),"current incidence target")
        require(owners[component]["native_cluster"]==nid and owners[component]["native_name"]==identity["native_name"],"target ownership")
        require(all(primitive_lines[r["line"]-1]==r["raw"]for r in target["native_primitive_records"]),"actual raw primitive line joins")
        points=[]
        for row in point_rows(target):
            match=candidates(pya,row["point_dbu"],polygons);row["candidates"]=match;points.append(row)
            candidate_ids.update(match["contains_or_boundary"]);candidate_ids.update(match["quantization_box_positive_area_overlap"])
        contacts=[]
        for contact in target["contacts"]:
            anchor=contact["anchor"];label=anchor["label"]
            current=[a for a in anchors["anchors"]if a["label"]==label]
            precise_current=[a for a in precise["anchors"]if a["label"]==label]
            require(len(current)==len(precise_current)==1,"unique actual contact label")
            for actual in (current[0],precise_current[0]):
                require(all(actual[k]==anchor[k]for k in ("label","metal","point_dbu","wire_component","native_cluster")),"current precise/canonical contact")
            location=bylocation[contact["device"]];path=stable_path(pya,g,location)
            device=devices[contact["device"]];terminal=anchor["detail"]["terminal"]
            td=next(td for td in device.device_class().terminal_definitions()if td.name==terminal)
            require(device.net_for_terminal(td.id()).cluster_id==nid,"native device terminal owner")
            p=pya.Point(*anchor["point_dbu"]);metal=anchor["metal"]
            require(w.probe_net(regions[metal],p).cluster_id==component and
              lvs.probe_net(lvs.layer_by_index(graph["native_layer_mapping"][str(metal)]),p).cluster_id==nid,"contact point ownership")
            dt=pya.DCplxTrans.from_s(location["pcell"]["transform"])
            tr=pya.ICplxTrans(dt.mag,dt.angle,dt.is_mirror(),round(dt.disp.x/g.dbu),round(dt.disp.y/g.dbu))
            local=source_pins["cells"].get(location["pcell"]["cell"],{}).get("pins",[])
            transformed=[dict(metal=m,local_box_dbu=b,top_box_dbu=str(pya.Box(*b).transformed(tr)))for m,b in local]
            matches=candidates(pya,anchor["point_dbu"],polygons)
            candidate_ids.update(matches["contains_or_boundary"]);candidate_ids.update(matches["quantization_box_positive_area_overlap"])
            raw=next(p for p in points if p["native_node"]==label)
            contacts.append(dict(original=contact,location=location,resolved_hierarchy=path,
              transformed_source_pin_boxes=transformed,point_candidates=matches,
              rnode_minus_anchor_dbu=[a-b for a,b in zip(raw["point_dbu"],anchor["point_dbu"])],
              terminal_geometry={str(i):[p.to_s()for p in r.each()]for i,r in lvs.shapes_of_terminal(device.terminal_ref(td.id())).items()}))
        require(len(contacts)==8,"eight complete target contacts")
        result[key]=dict(native_cluster=nid,native_name=identity["native_name"],component=component,
          points=points,contacts=contacts,incidence=target["incidence"],native_primitive_records=target["native_primitive_records"],
          all_target_polygon_ids=[i for i in selected_ids if records[i]["component"]==component],
          resistor_physical_layer_or_footprint_proven=False,transient_current_or_recovery_proven=False)
        persist("target-"+key+".json",dict(target=result[key],polygons=[records[i]for i in sorted(candidate_ids)],scope=host.FLAGS))
    require(before=={n:host.pin(host.frozen.regular(selected,n))for n in config["selected"]},"native inputs changed")
    return dict(status="PASS_CURRENT_ACCESS_GEOMETRIC_OBSERVATION_NOT_EDGE_ATTRIBUTION",scope=host.FLAGS,
      source_inputs=before,coordinate_policy=config["coordinate_policy"],native_counts=dict(devices=500,terminals=1446,wire_components=113,native_nets=238,ports=25),
      layer_checks=layerproof,targets=result,polygons=[records[i]for i in sorted(set(selected_ids)|candidate_ids)],
      raw_conductor_hierarchy=raw_geometry(g),polygon_export_complete_for_selected_components=True,
      foreign_point_overlap_polygons_included=True,contacts_top_level_transforms_verified=True,
      raw_rnode_type_zero_not_layer=True,missing=["per-resistor footprint and material generation record",
        "per-resistor authoritative layer/type and access contact ownership","transient currents and causality"])

def native_controls(pya):
    # Actual pinned geometry API, synthetic shapes only; no real device claims.
    a=pya.Polygon(pya.Box(0,0,10,10));b=pya.Polygon(pya.Box(0,0,10,10))
    hole=pya.Polygon(pya.Box(-10,-10,20,20));hole.insert_hole(pya.Box(-2,-2,12,12))
    polys=[("a",a),("coincident_other_layer",b),("hole",hole)]
    require(candidates(pya,[5,5],polys)["contains_or_boundary"]==["a","coincident_other_layer"],"actual coincident layers")
    require(candidates(pya,[0,5],polys)["contains_or_boundary"]==["a","coincident_other_layer"],"actual polygon boundary")
    require(candidates(pya,[100,100],polys)["disposition"]=="NO_MATCH","actual no match")
    require("hole"not in candidates(pya,[5,5],polys)["contains_or_boundary"],"actual hole")
    require(candidates(pya,[11,5],[("a",a)])["contains_or_boundary"]==[] and
      candidates(pya,[11,5],[("a",a)])["quantization_box_positive_area_overlap"]==["a"],"actual quantization search")
    return dict(status="PASS_PINNED_PYA_SYNTHETIC_POINT_CONTROLS",positive=5,synthetic_geometry=True,real_target_geometry_qualified=False)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--selected",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True);parser.add_argument("--pins-sha256",required=True)
    args=parser.parse_args();config=host.source_guard(args.pins_sha256)[0]
    require(not args.output.exists(),"native output no overwrite")
    import pya
    controls=native_controls(pya)
    host.write(args.output.with_name("native-api-controls.json"),host.encode(controls))
    try:
        result=observe(pya,args.selected,config,host.ROOT,lambda name,value:host.write(args.output.with_name(name),host.encode(value)));host.source_guard(args.pins_sha256)
        host.write(args.output,host.encode(result))
    except BaseException:
        try:host.write(args.output.with_name("native-observation-failure.json"),host.encode(dict(error=traceback.format_exc(),scope=host.FLAGS)))
        except BaseException:pass
        raise
if __name__=="__main__":main()
