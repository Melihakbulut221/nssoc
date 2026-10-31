#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read current GDS/L2N ownership. Never assign a resistor footprint from points."""
import argparse,collections,hashlib,json,re,shlex,traceback
from fractions import Fraction
from pathlib import Path
import cloud_cdr_current_access_geometry as host
require=host.require
TOP="nssoc_cdr_pd500_resistor_v59"
METALS=(8,10,30,50,67,126,134)
VIAS=(19,29,49,66,125,133)
LAYERS=METALS+VIAS

def point_rows(target):
    nodes=target["nodes"];mapping={r["native"]:r["loaded"]for r in nodes}
    count=target["node_count"]
    require(type(count)is int and count>0 and len(nodes)==len(mapping)==len(set(mapping.values()))==count,"complete distinct actual node census")
    factor=Fraction(target["coordinate_dbu_per_raw_unit"])
    require(factor==5,"authenticated current 0.5 centimicron / 0.001um DBU")
    result=[];seen=set()
    for row in target["native_primitive_records"]:
        tokens=shlex.split(row["raw"])
        require(tokens==row["tokens"],"raw primitive tokens")
        require(tokens[0]=="rnode"and len(tokens)==7 and tokens[1]in mapping and tokens[1]not in seen,"unique current rnode")
        require(tokens[-1]=="0","literal provisional type zero")
        require(all(re.fullmatch("[+-]?[0-9]+",v)is not None for v in tokens[4:6]),"integer raw coordinates")
        point=[int(v)*factor for v in tokens[4:6]]
        require(all(v.denominator==1 for v in point),"exact integer layout point")
        seen.add(tokens[1])
        result.append(dict(native_node=tokens[1],loaded_node=mapping[tokens[1]],source_record=row,
          point_dbu=[int(v)for v in point],coordinate_nm_per_raw_unit=str(factor),coordinate_frame="top-level pump_wires",
          native_type_token=tokens[-1],type_token_is_layer=False,second_transform_applied=False))
    require(seen==set(mapping),"complete rnode coordinate census")
    return result

def unit_binding(pya,selected,c,incidence):
    def text(k):return host.frozen.regular(selected,c['paths'][k]).read_text()
    ext=text('ext');res=text('res_ext');tcl=text('native_tcl');generator=text('export_source')
    g=pya.Layout();g.read(str(selected/c['paths']['gds']))
    scale=[]
    for value in (ext,res):
        rows=[shlex.split(line)[1:]for line in value.splitlines()if line.startswith('scale ')]
        require(rows==[['1000','1','0.5']],'exact unambiguous native ext scale');scale.append(rows[0])
    factor=Fraction(scale[0][2])*Fraction(1,100)/Fraction(str(g.dbu))
    require(g.dbu==0.001 and factor==5,'centimicron to actual GDS DBU conversion')
    require('gds read'in tcl and 'pump_wires'in tcl and 'extract'in tcl,'authentic top-level native export commands')
    ports={}
    for line in ext.splitlines():
        t=shlex.split(line)
        if t and t[0]=='port':
            require(len(t)==8 and t[1]not in ports,'unique native port coordinate');ports[t[1]]=(t,line)
    checked=[]
    for target in incidence['targets'].values():
        for contact in target['contacts']:
            a=contact['anchor'];label=a['label'];require(label in ports,'actual contact port exists')
            t,line=ports[label];raw=[int(v)for v in t[3:5]]
            require(t[3:5]==t[5:7],'point-sized original exported port')
            expected=[round(Fraction(v,1)/factor)for v in a['point_dbu']]
            require(raw==expected,'original port equals nearest native-grid anchor')
            point=[int(factor*v)for v in raw]
            require(all(abs(x-y)<=2 for x,y in zip(point,a['point_dbu'])),'actual integer quantization residual bound')
            checked.append(dict(label=label,anchor_point_dbu=a['point_dbu'],native_port_raw=line,
              port_point_dbu=point,residual_dbu=[x-y for x,y in zip(point,a['point_dbu'])]))
    require(len(checked)==26 and len({r['label']for r in checked})==26,'all actual four-net contacts bound')
    return dict(ext_scale_tokens=scale,layout_dbu_um=str(g.dbu),ext_length_unit_um='1/100',dbu_per_raw_unit=str(factor),
      formula='ext scale L centimicrons * (1/100 micrometre) / GDS DBU micrometres',
      top_level_frame='pump_wires',all26_port_anchor_quantizations_checked=checked,
      export_generator=dict(path=c['paths']['export_source'],sha256=host.pin(selected/c['paths']['export_source'])['sha256'],text=generator),
      native_tcl=dict(path=c['paths']['native_tcl'],sha256=host.pin(selected/c['paths']['native_tcl'])['sha256'],text=tcl),
      reference='https://github.com/RTimothyEdwards/magic/blob/master/doc/man/ext.5',
      layer_zero_is_provisional=True,point_is_not_edge_footprint=True,physical_route_inferred=False)


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

def integer_box(value):
    require(isinstance(value,(list,tuple))and len(value)==4 and all(type(x)is int for x in value),"four integer box coordinates")
    require(value[0]<value[2]and value[1]<value[3],"positive box")
    return list(value)

def parallel_edge_measurements(first,second):
    # Integer differences only. These are parallel-edge observations, not a DRC or
    # Euclidean clearance verdict. Keep every matching edge and its interval.
    def edges(contours):
        result=[]
        for ci,pts in enumerate(contours):
            require(len(pts)>=3 and all(len(p)==2 and all(type(v)is int for v in p)for p in pts),"integer polygon contour")
            for i,a in enumerate(pts):
                b=pts[(i+1)%len(pts)]
                require(a!=b,"zero length polygon edge")
                if a[0]==b[0]:result.append(("vertical",a[0],min(a[1],b[1]),max(a[1],b[1]),ci,i))
                elif a[1]==b[1]:result.append(("horizontal",a[1],min(a[0],b[0]),max(a[0],b[0]),ci,i))
        return result
    result=[]
    for a in edges(first):
        for b in edges(second):
            if a[0]!=b[0]:continue
            lo=max(a[2],b[2]);hi=min(a[3],b[3])
            if lo<hi:result.append(dict(axis=a[0],gap_dbu=abs(a[1]-b[1]),parallel_run_dbu=hi-lo,
              overlap_interval_dbu=[lo,hi],first_edge=[a[4],a[5]],second_edge=[b[4],b[5]]))
    return result

def bounding_enclosure(outer,inner):
    outer=integer_box(outer);inner=integer_box(inner)
    return dict(left=inner[0]-outer[0],bottom=inner[1]-outer[1],right=outer[2]-inner[2],top=outer[3]-inner[3],
      bounding_boxes_only=True,legal_enclosure_proved=False)

def poly_data(poly):
    return dict(hull_dbu=[[p.x,p.y]for p in poly.each_point_hull()],
      holes_dbu=[[[p.x,p.y]for p in poly.each_point_hole(i)]for i in range(poly.holes())],
      native_polygon=poly.to_s(),bbox_dbu=[poly.bbox().left,poly.bbox().bottom,poly.bbox().right,poly.bbox().top],
      area_dbu2=poly.area())

def raw_window(pya,layout,window):
    """Every layer/datatype and raw occurrence. No flattening or duplicate collapse."""
    rows=[];occurrences=[];layers=list(layout.layer_indexes())
    def walk(cell,tr,path,indices):
        require(cell.cell_index()not in indices,"cyclic cell hierarchy")
        if not cell.bbox().transformed(tr).touches(window):return
        occurrences.append(dict(path=path,cell=cell.name,cell_index=cell.cell_index(),transform_dbu=str(tr)))
        for li in layers:
            info=layout.get_info(li)
            for ordinal,shape in enumerate(cell.shapes(li).each()):
                if not shape.bbox().transformed(tr).touches(window):continue
                poly=shape.polygon
                if poly is not None:
                    top=poly.transformed(tr)
                    if not top.touches(window):continue
                else:top=None
                rows.append(dict(id=path+"|"+str(info.layer)+"/"+str(info.datatype)+"|"+str(ordinal),
                  path=path,cell=cell.name,cell_index=cell.cell_index(),shape_ordinal=ordinal,
                  gds_layer=info.layer,gds_datatype=info.datatype,transform_dbu=str(tr),native_shape=shape.to_s(),
                  properties=properties(shape),is_text=shape.is_text(),
                  top_bbox_dbu=[shape.bbox().transformed(tr).left,shape.bbox().transformed(tr).bottom,
                    shape.bbox().transformed(tr).right,shape.bbox().transformed(tr).top],
                  polygon=None if top is None else poly_data(top),local_polygon=None if poly is None else poly_data(poly)))
        for ordinal,inst in enumerate(cell.each_inst()):
            transforms=list(inst.cell_inst.each_cplx_trans())
            require(len(transforms)==inst.size(),"complete array elements")
            for element,it in enumerate(transforms):
                child_path=path+"/"+str(inst.cell_index)+"_"+str(ordinal)
                if len(transforms)>1:child_path+="@"+str(element)
                walk(inst.cell,tr*it,child_path,indices+[cell.cell_index()])
    walk(layout.cell(TOP),pya.ICplxTrans(),TOP,[])
    require(len({r["id"]for r in rows})==len(rows),"unique raw occurrences")
    return rows,occurrences

def region_owner_rows(pya,poly,layer,component_regions,owners):
    shape=pya.Region(poly);hits=[];cover=pya.Region()
    for comp,region in component_regions.get(layer,{}).items():
        overlap=shape&region
        if overlap.is_empty():continue
        cover+=overlap
        hits.append(dict(component=comp,native_cluster=owners[comp]["native_cluster"],native_name=owners[comp]["native_name"],
          overlap_area_dbu2=overlap.area(),complete_shape_within_component=(shape-region).is_empty()))
    return dict(candidates=hits,whole_shape_covered=(shape-cover).is_empty(),
      electrical_owner_proved=len(hits)==1 and hits[0]["complete_shape_within_component"],
      overlapping_candidates_not_discarded=True)

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

def feasibility_native_controls(pya):
    layout=pya.Layout();layout.dbu=0.001
    top=layout.create_cell(TOP);leaf=layout.create_cell("synthetic_leaf")
    leaf.shapes(layout.layer(8,0)).insert(pya.Box(0,0,100,400))
    leaf.shapes(layout.layer(5,7)).insert(pya.Box(-20,0,20,400))
    top.insert(pya.CellInstArray(leaf.cell_index(),pya.Trans(1000,2000),pya.Vector(1000,0),pya.Vector(0,0),2,1))
    rows,occurrences=raw_window(pya,layout,pya.Box(900,1900,2200,2500))
    require(len(rows)==4 and len(occurrences)==3,"actual array raw multiplicity")
    require({tuple(r["top_bbox_dbu"])for r in rows if r["gds_layer"]==8}=={(1000,2000,1100,2400),(2000,2000,2100,2400)},"actual array transform")
    require(len({r["id"]for r in rows})==4 and any(r["gds_datatype"]==7 for r in rows),"all datatypes/raw identities")
    poly=pya.Polygon(pya.Box(0,0,100,100))
    owners={1:dict(native_cluster=28,native_name="$131"),2:dict(native_cluster=124,native_name="$680")}
    overlap=region_owner_rows(pya,poly,8,{8:{1:pya.Region(poly),2:pya.Region(poly)}},owners)
    require(len(overlap["candidates"])==2 and not overlap["electrical_owner_proved"],"coincident owners preserved")
    single=region_owner_rows(pya,poly,8,{8:{1:pya.Region(poly)}},owners)
    require(single["electrical_owner_proved"]and single["whole_shape_covered"],"single full raw owner")
    empty=region_owner_rows(pya,poly,8,{8:{1:pya.Region(pya.Box(500,500,600,600))}},owners)
    require(not empty["candidates"]and not empty["whole_shape_covered"],"unowned retained")
    return dict(status="PASS_DRAIN_ACCESS_PINNED_PYA_SYNTHETIC_CONTROLS",positive=6,synthetic_geometry=True,real_geometry_feasible=False)


def access_windows(pya,g,w,nets,owners,regions,c,root,incidence,selected):
    focus=host.decode(host.frozen.regular(root,c['focus']).read_bytes())
    wire_lines=host.frozen.regular(selected,c['paths']['wires_spice']).read_text().splitlines()
    component_regions={layer:{component:w.shapes_of_net(n,region,True)for component,n in nets.items()}for layer,region in regions.items()}
    bynode={r['native_node']:(target['component'],r)for target in incidence['targets'].values()for r in point_rows(target)}
    result=[]
    for edge in focus['dominant_edges']:
        require(len(edge['source'])==1 and wire_lines[edge['source'][0]['line']-1]==edge['source'][0]['text'],'exact original resistor card')
        require(all(n in bynode for n in edge['nodes']),'both actual endpoints retained')
        components={bynode[n][0]for n in edge['nodes']};require(len(components)==1,'same true-R component')
        component=next(iter(components));points=[bynode[n][1]['point_dbu']for n in edge['nodes']]
        window=pya.Box(min(p[0]for p in points)-2000,min(p[1]for p in points)-2000,max(p[0]for p in points)+2000,max(p[1]for p in points)+2000)
        rows,occurrences=raw_window(pya,g,window)
        for row in rows:
            if row['polygon']is not None and row['gds_datatype']==0 and row['gds_layer']in LAYERS:
                poly=pya.Polygon.from_s(row['polygon']['native_polygon'])
                row['ownership']=region_owner_rows(pya,poly,row['gds_layer'],component_regions,owners)
            else:row['ownership']=dict(electrical_owner_proved=False,reason='nonconductor or no polygon')
        gaps=[]
        for first in rows:
            if first['gds_layer']not in METALS or first['polygon']is None:continue
            own=first['ownership'];hits=own.get('candidates',[])
            if not(own.get('electrical_owner_proved')and hits[0]['component']==component):continue
            for second in rows:
                if second['gds_layer']!=first['gds_layer']or second['gds_datatype']!=0 or second['polygon']is None:continue
                foreign=second['ownership'].get('candidates',[])
                if not any(x['component']!=component for x in foreign):continue
                a=first['polygon'];b=second['polygon'];measures=parallel_edge_measurements([a['hull_dbu']]+a['holes_dbu'],[b['hull_dbu']]+b['holes_dbu'])
                if measures:gaps.append(dict(first_raw_shape=first['id'],second_raw_shape=second['id'],gds_layer=first['gds_layer'],measurements=measures))
        result.append(dict(edge=edge,component=component,endpoints=[bynode[n][1]for n in edge['nodes']],
          observation_envelope_dbu=[window.left,window.bottom,window.right,window.top],envelope_is_not_resistor_footprint=True,
          raw_occurrences=occurrences,raw_shapes=rows,parallel_edge_observations=gaps,
          all_layers_and_datatypes_preserved=True,resistor_layer_assigned=False,DRC_acceptance=False))
    require(len(result)==32,'complete selected dominant-edge census')
    return dict(edges=result,edge_count=len(result),geometries_modified=False,clearance_observations_are_not_DRC=True)

def full_rail_coverage(pya,g,w,nets,regions,contacts):
    selected={row['original']['device']:row for row in contacts if row['original']['device']in(3,4,5,6,32,33,34,35)}
    require(set(selected)=={3,4,5,6,32,33,34,35},'all current eight drain primitives')
    result=[]
    for ident,row in sorted(selected.items()):
        a=row['original']['anchor'];component=a['wire_component'];location=row['location']
        dt=pya.DCplxTrans.from_s(location['pcell']['transform'])
        require(dt.mag==1 and dt.angle in(0,90,180,270),'unscaled orthogonal primitive')
        tr=pya.ICplxTrans(dt.mag,dt.angle,dt.is_mirror(),round(dt.disp.x/g.dbu),round(dt.disp.y/g.dbu))
        boxes={'original_M1_160nm_x36um':(8,[750,0,910,36000]),'existing_M1_320nm_x36um':(8,[670,0,990,36000]),'existing_M2_300nm_x35_6um':(10,[680,200,980,35800])}
        checks={}
        for key,(layer,coords)in boxes.items():
            box=pya.Box(*coords).transformed(tr);netregion=w.shapes_of_net(nets[component],regions[layer],True)
            covered=(pya.Region(box)-netregion).is_empty();require(covered,'actual complete existing rail coverage: '+str(ident)+'/'+key)
            checks[key]=dict(layer=layer,local_box_dbu=coords,top_box_dbu=[box.left,box.bottom,box.right,box.top],whole_box_in_actual_owned_component=covered)
        result.append(dict(device=ident,component=component,native_cluster=a['native_cluster'],actual_anchor=a,
          resolved_hierarchy=row['resolved_hierarchy'],coverage=checks,new_overlay_generated=False))
    return dict(rails=result,all_eight_full_length_rails_verified=True,geometry_changed=False)


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
        require(len(contacts)==identity["contact_count"],"complete actual target contacts")
        result[key]=dict(native_cluster=nid,native_name=identity["native_name"],component=component,
          points=points,contacts=contacts,incidence=target["incidence"],native_primitive_records=target["native_primitive_records"],
          all_target_polygon_ids=[i for i in selected_ids if records[i]["component"]==component],
          resistor_physical_layer_or_footprint_proven=False,transient_current_or_recovery_proven=False)
        persist("target-"+key+".json",dict(target=result[key],polygons=[records[i]for i in sorted(candidate_ids)],scope=host.FLAGS))
    windows=access_windows(pya,g,w,nets,owners,regions,config,root,incidence,selected)
    persist("dominant-access-windows.json",windows)
    rails=full_rail_coverage(pya,g,w,nets,regions,[row for v in result.values()for row in v["contacts"]])
    persist("existing-full-drain-rails.json",rails)
    require(before=={n:host.pin(host.frozen.regular(selected,n))for n in config["selected"]},"native inputs changed")
    return dict(status="PASS_CURRENT_ACCESS_GEOMETRIC_OBSERVATION_NOT_EDGE_ATTRIBUTION",scope=host.FLAGS,
      source_inputs=before,coordinate_policy=config["coordinate_policy"],native_counts=dict(devices=500,terminals=1446,wire_components=113,native_nets=238,ports=25),
      layer_checks=layerproof,targets=result,polygons=[records[i]for i in sorted(set(selected_ids)|candidate_ids)],
      raw_conductor_hierarchy_exported=False,polygon_export_complete_for_selected_components=True,
      foreign_point_overlap_polygons_included=True,contacts_top_level_transforms_verified=True,
      raw_rnode_type_zero_not_layer=True,missing=["per-resistor footprint and material generation record",
        "per-resistor authoritative layer/type and access contact ownership","transient currents and causality"])


def main():
    p=argparse.ArgumentParser();p.add_argument('--selected',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--controls',action='store_true');a=p.parse_args()
    import pya
    a.output.mkdir(parents=True,exist_ok=False)
    def save(name,value):host.q.write_new(a.output/name,host.encode(value))
    try:
        if a.controls:
            values=dict(point=native_controls(pya),ownership=feasibility_native_controls(pya),units=unit_controls())
            save('controls.json',dict(status='PASS_CURRENT_ACCESS_GEOMETRY_NATIVE_FIXTURES',counts=dict(point=5,ownership=6,units=5),fixtures=values,actual_geometry_acquired=False,**host.FLAGS));return
        c=host.source_guard();host.checkout_binding(host.context(__import__('os').environ),c)
        require(c['readback_authorized']is True,'native readback disabled')
        incidence=host.decode(host.frozen.regular(host.ROOT,c['incidence']).read_bytes())
        save('coordinate-source-binding.json',unit_binding(pya,a.selected,c,incidence))
        report=observe(pya,a.selected,c,host.ROOT,save)
        save('geometry-observation.json',report)
    except BaseException as error:
        save('native-failure.json',dict(error=repr(error),traceback=traceback.format_exc(),**host.FLAGS));raise

def unit_controls():
    baseline=dict(node_count=1,coordinate_dbu_per_raw_unit='5',nodes=[dict(native='A',loaded='w_A')],native_primitive_records=[dict(line=1,raw='rnode "A" 0 0 -1 2 0',tokens=['rnode','A','0','0','-1','2','0'])])
    require(point_rows(baseline)[0]['point_dbu']==[-5,10],'signed exact units')
    import copy
    tests=[]
    for key,value in [('node_count',2),('coordinate_dbu_per_raw_unit','1'),('coordinate_dbu_per_raw_unit','1/2')]:
        bad=copy.deepcopy(baseline);bad[key]=value
        try:point_rows(bad)
        except AssertionError:tests.append(key+str(value))
        else:raise AssertionError('changed units/census accepted')
    bad=copy.deepcopy(baseline);bad['native_primitive_records'][0]['raw']='rnode "A" 0 0 -1 2 8'
    try:point_rows(bad)
    except AssertionError:tests.append('changed raw line')
    else:raise AssertionError('changed raw accepted')
    return dict(positive=1,refusals=tests)
if __name__=='__main__':main()
