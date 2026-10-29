#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Width-specific read-only proof functions. No restore, authority, or execution CLI."""
import collections
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import cdr_v59_tail_saved_identity_native as identity
import cdr_v59_tail_fresh_rc_semantic as semantic
import cdr_v59_tail_access_topology as topology
import generate_cdr_v59_tail_access_wire as raw_source

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "scripts/cdr-v59-selector-column-width-contract.json"
CONTRACT_SHA = "cc92ad1c6368219f4df0faf4989e7b2a77a1dab92898f4c92c6a69e4ead67106"
PRODUCER = "docs/evidence/cdr-v59-tail-exact-wire-methods-20261026/locate01.py"
TOP = "nssoc_cdr_pd500_resistor_v59"
CHILD = "pd_child_sampler_cd"
METALS = (8,10,30,50,67,126,134)
VIAS = (19,29,49,66,125,133)
LAYERS = METALS + VIAS
KEYS = ((50,0),(126,0))
FILES = dict(gds="parent/layout/"+TOP+".gds", lvs="parent/physical/lvs_flat/result.lvsdb",
    inventory="wire/pcell-inventory01.json", locations="wire/device-locations01.json",
    graph="wire/native05/result.json", anchors="wire/anchors08.json",
    pins="wire/source-pins.json", wires="wire/native05/wires.l2n")
DEPENDENCIES = {
    "scripts/cdr_v59_tail_saved_identity_native.py":"4eab1f31c2414b6061c72096405f9688d8c1f03c6f31cb0fd505c17bd0523510",
    "scripts/cdr_v59_tail_fresh_rc_semantic.py":"a2f91abcaa0ea4004df822b99460027d3d416e10d546a079c5696d11e8b23f88",
    "scripts/cdr_v59_tail_access_topology.py":"df8b0e712cd224c6af66d88e91242d4e5b5d8b75a96ebf81179cb740c06c3a37",
    "scripts/cdr_v59_tail_saved_identity.py":"5b4cd8d7bf4a6c73df3b509f1d09cdf2029854c67431c4d70c5e0457c15f8568",
    "scripts/generate_cdr_v59_tail_access_wire.py":"4c9024bc04e818063b4a82f68fe6febffe94b9bcf7278fe58dc07029375f6a71",
}
FALSE = dict(physical_accepted=False,electrical_accepted=False,qualified_pex=False,
    full_phy_accepted=False,simulation_executed=False,automatic_retry=False)

def require(value, reason):
    if not value:
        raise AssertionError(reason)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def regular(root, name):
    root=Path(root)
    require(root.is_absolute() and root.resolve()==root and root.is_dir(),"Noncanonical input root")
    require(type(name)is str and name and PurePosixPath(name).as_posix()==name
      and not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts,
      "Unsafe input member")
    p=root/name
    require(p.is_file() and not any(x.is_symlink() for x in (p,*p.parents)),
      "Nonregular input member")
    return p

def inventory(root):
    root=Path(root)
    require(root.is_absolute() and root.resolve()==root and root.is_dir(),"Noncanonical input root")
    require(not any(p.is_symlink() for p in (root,*root.parents)),"Symlink input root")
    result={}
    for p in sorted(root.rglob("*")):
        require(not p.is_symlink(),"Symlink input member")
        if p.is_dir():
            continue
        require(p.is_file(),"Nonregular input member")
        result[p.relative_to(root).as_posix()]=sha(p)
    return result

def source_guard():
    for name,expected in DEPENDENCIES.items():
        require(sha(regular(ROOT,name))==expected,"Changed identity dependency: "+name)
    require(sha(regular(ROOT,CONTRACT))==CONTRACT_SHA,"Changed width contract")
    semantic.source_guard()
    return read(ROOT/CONTRACT)

def partition(row):
    return canonical(dict(terminals=sorted((v["device"],v["model"],v["terminal"])
        for v in row["device_terminals"]),public_ports=sorted(row["public_ports"])))

def expected_plan(contract, metadata):
    """Independent literal formula; does not call candidate generator.boxes()."""
    require(contract["dbu_um"]==.001 and contract["top"]==TOP and contract["child"]==CHILD,
      "Changed width coordinate scope")
    require(contract["origin_dbu"]==[0,-3970] and contract["width_dbu"]==3200
      and type(contract["width_dbu"])is int,"Changed width/origin")
    require(contract["old_bus_dbu"]=={"M_SE":150000,"M_TE":240000}
      and contract["width_end_dbu"]=={"M_SE":150000,"M_TE":180000},"Changed width endpoints")
    require(contract["placements"]=={"sd":[993600,272000],"sc":[993600,1461520]},
      "Changed declared placements")
    origin=metadata["origin_translation_um"]
    require(type(origin)is list and len(origin)==2 and all(type(v)in(int,float) for v in origin)
      and all(math.isfinite(v)for v in origin) and origin[0]==0 and origin[1]==-3.97,"Changed exact numeric child origin")
    selected=[r for r in metadata["routes"] if r["net"] in ("M_SE","M_TE")]
    require(canonical(selected)==canonical(contract["selected_original_routes"]),"Changed source route rows")
    require(len(selected)==13 and len({(r["device"],r["net"])for r in selected})==13
      and collections.Counter(r["net"]for r in selected)=={"M_SE":5,"M_TE":8},
      "Wrong selected route census")
    def grid(v):
        require(type(v)in(int,float) and math.isfinite(v),"Non-numeric route coordinate")
        n=round(v*1000)
        require(abs(v*1000-n)<1e-6 and n%5==0,"Off-grid original source coordinate")
        return n
    rows=[]
    for r in selected:
        x,y=grid(r["escape_lane_um"]),grid(r["escape_y_um"])
        old_end=240000 if r["net"]=="M_TE" else 150000
        end=180000 if r["net"]=="M_TE" else 150000
        require(y<end<=old_end,"Invalid width interval")
        for layer,half,pad in ((50,600,200),(126,820,820)):
            rows.append(dict(device=r["device"],net=r["net"],layer=layer,
              old=[x-half,y-pad-3970,x+half,old_end+pad-3970],
              new=[x-1600,y-pad-3970,x+1600,end+pad-3970],probe=[x,y+1000-3970]))
    require(canonical(rows)==canonical(contract["declared_rectangles"]),"Width literal/formula mismatch")
    return rows

def targets(contract, old_witness, new_witness):
    oi=topology.graph_index(old_witness["graph"]);ni=topology.graph_index(new_witness["graph"])
    result={}
    for tag,device in (("sd",61),("sc",115)):
        for net,terminal in (("M_SE","C"),("M_TE","E")):
            declared=contract["owner_partitions"][tag][net]
            old_cluster=oi["terminals"][(device,"npn13G2",terminal)]
            new_cluster=ni["terminals"][(device,"npn13G2",terminal)]
            key=partition(declared)
            require(key==oi["nets"][old_cluster]["key"]==ni["nets"][new_cluster]["key"],
              "Changed complete target partition")
            require(canonical(oi["nets"][old_cluster]["row"])==canonical(declared),
              "Changed original target provenance")
            result[(tag,net)]=key
    require(len(set(result.values()))==4,"Target partitions not unique four")
    return result

def region_record(region):
    region=region.merged()
    return dict(explicitly_empty=region.is_empty(),area_dbu2=region.area(),
      polygons=region.count(),bbox=str(region.bbox()),
      source_union_sha256=hashlib.sha256("\n".join(sorted(p.to_s()for p in region.each())).encode()).hexdigest())

def same_region(a,b,reason):
    require((a^b).is_empty(),reason)

def instance_rows(cell):
    return [dict(child=i.cell.name,ordinal=j,cplx=str(i.cplx_trans),dcplx=str(i.dcplx_trans),
      na=i.na,nb=i.nb,a=str(i.a),b=str(i.b),size=i.size(),regular_array=i.is_regular_array(),
      properties=identity.properties(i))for j,i in enumerate(cell.each_inst())]

def placed_additions(pya,layout,contract,plan):
    require(layout.dbu==.001,"Changed DBU")
    top=layout.cell(TOP);child=layout.cell(CHILD)
    require(top is not None and child is not None,"Missing width hierarchy")
    parents=[(c,i)for c in layout.each_cell()for i in c.each_inst()
      if i.cell_index==child.cell_index()]
    require(len(parents)==2 and all(c.name==TOP and i.size()==1 and not i.is_regular_array()
      for c,i in parents),"Changed shared-child multiplicity")
    placed={};proof=[]
    for tag,(dx,dy)in contract["placements"].items():
        found=[i for _,i in parents if raw_source.placement_matches(i,dx,dy)]
        require(len(found)==1,"Changed shared-child transform")
        for row in plan:
            key=(tag,row["net"],row["layer"])
            placed.setdefault(key,pya.Region())
            region=pya.Region(pya.Box(*row["new"])).transformed(found[0].cplx_trans)
            placed[key]+=region
            proof.append(dict(placement=tag,net=row["net"],device=row["device"],layer=row["layer"],
              child_box=row["new"],parent_box=str(region.bbox())))
    require(len(proof)==52 and len(placed)==8,"Incomplete placed addition census")
    return {k:v.merged()for k,v in placed.items()},proof

def geometry_proof(pya,old,new,contract,plan):
    """Exact raw and full-union proof, also used by hosted native controls."""
    require(old.dbu==new.dbu==.001,"Changed DBU")
    names=sorted(c.name for c in old.each_cell())
    require(names==sorted(c.name for c in new.each_cell()),"Changed complete cell census")
    require(str(old.cell(TOP).bbox())==str(new.cell(TOP).bbox()),"Changed parent bbox")
    old_placed,placement_proof=placed_additions(pya,old,contract,plan)
    new_placed,new_placement_proof=placed_additions(pya,new,contract,plan)
    require(placement_proof==new_placement_proof,"Changed placed additions")
    wanted=collections.Counter((r["layer"],0,*r["new"])for r in plan)
    require(len(wanted)==sum(wanted.values())==26,"Duplicate declared rectangle")
    cells=[];typed=[]
    for name in names:
        a=old.cell(name);b=new.cell(name)
        require(instance_rows(a)==instance_rows(b),"Changed hierarchy/order/properties")
        ca=collections.Counter(raw_source.raw_records(old,a))
        cb=collections.Counter(raw_source.raw_records(new,b))
        require(not(ca-cb),"Original raw record or multiplicity removed")
        added=cb-ca
        if name!=CHILD:
            require(not added,"Raw addition outside shared child")
        else:
            actual=collections.Counter();remaining=added.copy()
            for li in new.layer_indexes():
                info=new.get_info(li)
                for shape in b.shapes(li).each():
                    record=(info.layer,info.datatype,shape.to_s(),
                      canonical(shape.properties()),shape.is_text())
                    if remaining[record]<=0:
                        continue
                    require((info.layer,info.datatype)in KEYS and shape.properties()=={}
                      and not shape.is_text() and (shape.is_box()or shape.is_polygon()),
                      "Unauthorized raw addition type")
                    polygon=shape.polygon
                    require(polygon is not None and polygon.is_box() and polygon.holes()==0
                      and polygon.num_points_hull()==4,"Nonrectangular native addition")
                    box=polygon.bbox()
                    require(polygon==pya.Polygon(box),"Native rectangle differs from bounds")
                    key=(info.layer,info.datatype,box.left,box.bottom,box.right,box.top)
                    actual[key]+=1;remaining[record]-=1
                    typed.append(dict(cell=name,record=list(record),bounds=list(key),native_rectangle=True))
            require(not +remaining and actual==wanted,"Exact 26 addition coordinates/multiplicity changed")
        cells.append(dict(cell=name,original_records=sum(ca.values()),fresh_records=sum(cb.values()),
          original_raw_sha256=digest(sorted(ca.elements())),fresh_raw_sha256=digest(sorted(cb.elements())),
          additions=sum(added.values()),instance_rows=instance_rows(a)))
    require(len(typed)==26,"Incomplete typed addition proof")
    before=raw_source.material(pya,old,old.cell(TOP),True)
    after=raw_source.material(pya,new,new.cell(TOP),True)
    require(set(before)==set(after),"Changed full GDS layer/datatype census")
    layers=[]
    for key,region in before.items():
        add=pya.Region()
        for (_,_,layer),part in old_placed.items():
            if key==(layer,0):
                add+=part
        expected=(region+add).merged()
        same_region(expected,after[key],"Full GDS union differs from declared additions")
        layers.append(dict(layer=list(key),before=region_record(region),after=region_record(after[key]),
          expected_added=region_record((expected-region).merged())))
    return dict(cells=cells,typed_additions=typed,placed_additions=placement_proof,layers=layers,
      original_raw_multiplicity_text_properties_hierarchy_preserved=True),old_placed

def acquire_regions(pya,layout,root,witness):
    """Reconcile actual native LVS/wire shapes to every saved graph row."""
    graph=witness["graph"];index=topology.graph_index(graph)
    require(graph["status"]=="PASS_GEOMETRIC_PUMP_WIRE_COMPONENT_BINDING_NO_RC","Changed graph status")
    full=raw_source.material(pya,layout,layout.cell(TOP),True)
    regions={m:full.get((m,0),pya.Region()) for m in LAYERS}
    require(set(graph["layers"])=={str(m)for m in LAYERS},"Incomplete graph layer census")
    for m,r in regions.items():
        require(canonical(region_record(r))==canonical(graph["layers"][str(m)]),
          "Saved global region witness differs")
    lvs=pya.LayoutVsSchematic();lvs.read(str(regular(root,FILES["lvs"])))
    circuit=lvs.netlist().top_circuit()
    require(circuit is not None and circuit.name==TOP and circuit.pin_count()==25
      and len(list(circuit.each_device()))==500,"Wrong native LVS circuit")
    native={n.cluster_id:n for n in circuit.each_net()}
    require(set(native)==set(index["nets"]) and len(native)==len(list(circuit.each_net())),
      "Native LVS net census differs")
    active=[m for m in METALS if not regions[m].is_empty()]
    mapping={}
    for m in active:
        matches=[i for i in lvs.layer_indexes()
          if (lvs.layer_by_index(i).merged()^regions[m]).is_empty()]
        require(len(matches)==1,"Native metal mapping not uniquely exact")
        mapping[m]=matches[0]
    require({str(k):v for k,v in mapping.items()}==graph["native_layer_mapping"],
      "Saved native layer mapping differs")
    wires=pya.LayoutToNetlist();wires.read(str(regular(root,FILES["wires"])))
    wc=wires.netlist().top_circuit()
    require(wc is not None and not list(wc.each_device()),"Wire database contains devices")
    nets={n.cluster_id:n for n in wc.each_net()}
    require(set(nets)==set(index["component_rows"]) and len(nets)==len(list(wc.each_net()))==113,
      "Wire component census differs")
    wire_layers={}
    for m,r in regions.items():
        if not r.is_empty():
            wire_layers[m]=wires.layer_by_name("gds_"+str(m))
            same_region(wire_layers[m].merged(),r,"Wire layer differs from full GDS")
    owned={};reports=[]
    for component,row in index["component_rows"].items():
        key=index["component_keys"][component];require(key not in owned,"Duplicate component partition")
        cluster=row["native_cluster"];require(cluster in native,"Missing native component owner")
        pieces_raw={m:(wires.shapes_of_net(nets[component],wire_layers[m],True)
          if m in wire_layers else pya.Region())for m in LAYERS}
        pieces={m:r.merged()for m,r in pieces_raw.items()}
        require(set(row["layers"])=={str(m)for m in active},"Component layer census differs")
        for m in active:
            expected=lvs.shapes_of_net(native[cluster],lvs.layer_by_index(mapping[m]),True).merged()
            same_region(pieces[m],expected,"Wire/native complete owner region differs")
            require(row["layers"][str(m)]==dict(area_dbu2=pieces_raw[m].area(),polygons=pieces_raw[m].count()),
              "Saved component geometry differs")
        probe=pya.Point(*row["probe_dbu"]);metal=row["probe_metal"]
        require(metal in active,"Invalid saved component probe layer")
        wn=wires.probe_net(wire_layers[metal],probe)
        ln=lvs.probe_net(lvs.layer_by_index(mapping[metal]),probe)
        require(wn is not None and ln is not None and wn.cluster_id==component
          and ln.cluster_id==cluster,"Saved component probe owner differs")
        owned[key]=pieces
        reports.append(dict(partition_sha256=hashlib.sha256(key.encode()).hexdigest(),
          native_cluster=cluster,wire_component=component,layers={str(m):region_record(r)for m,r in pieces.items()}))
    for cluster,value in index["nets"].items():
        area=sum(lvs.shapes_of_net(native[cluster],lvs.layer_by_index(mapping[m]),True).area()
          for m in active)
        require(area==value["row"]["metal_area_dbu2"],"Saved native total metal area differs")
    for m,region in regions.items():
        combined=pya.Region()
        for value in owned.values():
            combined+=value[m]
        combined=combined.merged()
        same_region(combined,region,"Incomplete full component/layer coverage")
        require(sum(v[m].area()for v in owned.values())==combined.area(),
          "Overlapping component ownership")
    # Region objects retain database ownership until the caller finishes.
    return dict(owned=owned,regions=regions,report=reports,owners=(lvs,wires))

def owned_union(pya,before,after,target_keys,placed):
    """Exact 113-component × 13-layer comparison, no area-only admission."""
    require(len(before)==len(after)==113 and set(before)==set(after),"Changed complete component partition set")
    require(len(target_keys)==4 and len(set(target_keys.values()))==4
      and set(target_keys.values())<=set(before),"Wrong four owner partitions")
    additions={}
    for (tag,net,layer),r in placed.items():
        require((tag,net)in target_keys and layer in (50,126),"Undeclared owned addition")
        key=(target_keys[(tag,net)],layer)
        additions.setdefault(key,pya.Region());additions[key]+=r
    require(len(additions)==8,"Incomplete four-partition/two-layer plan")
    rows=[];changed=[]
    for key in sorted(before):
        require(set(before[key])==set(after[key])==set(LAYERS),"Incomplete owned layer census")
        for layer in LAYERS:
            a=before[key][layer];b=after[key][layer]
            add=additions.get((key,layer),pya.Region())
            expected=(a+add).merged()
            same_region(expected,b,"Owned full region differs from declared union")
            delta=(b-a).merged()
            if (key,layer)in additions:
                require(not delta.is_empty(),"Missing required owned width")
                changed.append((hashlib.sha256(key.encode()).hexdigest(),layer))
            else:
                require(delta.is_empty(),"Foreign component/layer changed")
            rows.append(dict(partition_sha256=hashlib.sha256(key.encode()).hexdigest(),layer=layer,
              before=region_record(a),after=region_record(b),added=region_record(delta)))
    require(len(changed)==8,"Changed owned layer census differs")
    return dict(component_count=113,checked_component_layers=len(rows),changed=changed,rows=rows)

def identity_proof(old,new):
    semantic.own_witness(old);semantic.own_witness(new)
    require(old["graph"]["status"]==new["graph"]["status"],"Changed graph status")
    return identity.compare_witnesses(old,new)

def compare(pya,old_root,new_root,expected):
    """Caller must supply authenticated complete root maps; this grants no authority."""
    contract=source_guard();old_root=Path(old_root);new_root=Path(new_root)
    require(old_root!=new_root and not old_root.is_relative_to(new_root)
      and not new_root.is_relative_to(old_root),"Overlapping witness roots")
    require(type(expected)is dict and set(expected)=={"old","fresh"},"Missing complete authenticated maps")
    require(expected["old"]==contract["baseline_inventory"] and len(expected["old"])==605,
      "Wrong complete original 605-member view")
    for side,root in (("old",old_root),("fresh",new_root)):
        require(inventory(root)==expected[side],"Complete authenticated input inventory differs")
        for name in FILES.values():
            regular(root,name)
    metadata=read(regular(old_root,"parent/inputs/sampler_cd/layout/result.json"))
    plan=expected_plan(contract,metadata)
    old_layout,old=identity.read_side(pya,old_root,FILES,ROOT/PRODUCER)
    new_layout,new=identity.read_side(pya,new_root,FILES,ROOT/PRODUCER)
    identity_result=identity_proof(old,new)
    target_keys=targets(contract,old,new)
    geometry,placed=geometry_proof(pya,old_layout,new_layout,contract,plan)
    original=acquire_regions(pya,old_layout,old_root,old)
    fresh=acquire_regions(pya,new_layout,new_root,new)
    owners=owned_union(pya,original["owned"],fresh["owned"],target_keys,placed)
    for side,root in (("old",old_root),("fresh",new_root)):
        require(inventory(root)==expected[side],"Input changed during native proof")
    source_guard()
    return dict(status="PASS_WIDTH_SPECIFIC_NATIVE_IDENTITY_EXACT_UNION_AND_OWNERSHIP",
      scope="READ_ONLY_WIDTH_COMPARISON_ONLY",identity=identity_result,geometry=geometry,
      owned_union=owners,original_native_regions=original["report"],fresh_native_regions=fresh["report"],
      original_acquired_witness=old,fresh_acquired_witness=new,
      inputs={side:dict(member_count=len(rows),inventory_sha256=digest(rows),files=rows)
        for side,rows in expected.items()},contract_sha256=CONTRACT_SHA,
      original_topology_comparator_modified=False,old_tail_bus_policy_used_for_acceptance=False,
      native_device_ids_not_remapped=True,raw_public_pin_order_retained=True,**FALSE)
