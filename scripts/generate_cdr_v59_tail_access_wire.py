#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Unexecuted, additive native geometry proposal. No physical acceptance here."""
import argparse
import collections
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
import cdr_v59_tail_access_plan as plan

ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/"scripts/cdr-v59-tail-access-wire-methods.json"
HANDOFF=ROOT/"docs/evidence/cdr-v59-master-tail-source-routing-handoff-20261026.json"
RUNTIME=ROOT/"docs/evidence/cdr-v59-tail-native-runtime-source-20261026.json"
SUMMARY=ROOT/"docs/evidence/cdr-v59-tail-current-font-physical-summary-20261026.json"
GDS="parent/layout/"+plan.TOP+".gds"
LVS="parent/physical/lvs_flat/result.lvsdb"
CANONICAL=Path("/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-v59-font-recovery/analysis-capsule")
SUMMARY_SHA="da0ea575f0950c765714f831786ca325cab597dad2df1ed6d65785b1688595f0"

def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

def files(root):
    assert root.is_dir() and not root.is_symlink()
    result={}
    for p in root.rglob("*"):
        assert not p.is_symlink(),("Symlink in input tree",str(p))
        if p.is_dir():continue
        assert p.is_file(),("Nonregular input",str(p))
        result[str(p.relative_to(root))]=sha(p)
    return result

def source_gate(source,pdk):
    assert os.environ.get("GITHUB_ACTIONS")=="true"
    assert source==CANONICAL and source.resolve()==CANONICAL
    method=json.loads(METHOD.read_text())
    assert method["native_execution_authorized"] is True
    assert method["geometry_generation_authorized"] is True
    for p,digest in method["protected_sha256"].items():
        q=ROOT/p
        assert q.is_file() and not q.is_symlink() and sha(q)==digest,("Changed source",p)
    assert sha(SUMMARY)==SUMMARY_SHA
    summary=json.loads(SUMMARY.read_text())
    assert summary["status"]=="PASS_EXACT_SAVED_FONT_ROUNDTRIP_AND_STRICT_WIRES_REQUIRES_MIM_RC"
    assert summary["source_head"]=="0af252ad92d21799295406ddadde0121bdd5b2fe"
    assert summary["run_id"]==40188489346 and summary["strict_wires_executed"] is True
    assert summary["all339_analysis_originals_unchanged"] is True
    expected={k[len("analysis-capsule/"):]:v for k,v in summary["outputs"].items() if k.startswith("analysis-capsule/")}
    assert len(expected)==349 and files(source)==expected
    assert expected[GDS]==summary["preserved_candidate_gds_sha256"]
    assert expected["parent/layout/schematic.cir"]==summary["preserved_candidate_reference_sha256"]
    runtime=json.loads(RUNTIME.read_text())["relative_runtime_sha256"]
    lib=pdk/"libs.tech/klayout/python"
    actual={str(p.relative_to(lib)):sha(p) for p in lib.rglob("*")
            if p.is_file() and p.suffix in (".py",".json")}
    assert len(runtime)==88 and actual==runtime,("Frozen native runtime differs",set(actual)^set(runtime))
    assert all(not p.is_symlink() for p in lib.rglob("*"))
    handoff=json.loads(HANDOFF.read_text())
    proposal=plan.candidate_plan(handoff)
    return expected,runtime,lib,handoff,proposal

def material(pya,layout,cell,recursive=False):
    out={}
    for li in layout.layer_indexes():
        info=layout.get_info(li);key=(info.layer,info.datatype)
        it=cell.begin_shapes_rec(li) if recursive else cell.shapes(li)
        r=pya.Region(it).flatten().merged()
        if not r.is_empty():out[key]=r
    return out

def raw_records(layout,cell):
    rows=[]
    for li in layout.layer_indexes():
        info=layout.get_info(li)
        for shape in cell.shapes(li).each():
            rows.append((info.layer,info.datatype,shape.to_s(),
                         json.dumps(shape.properties(),sort_keys=True,separators=(",",":")),shape.is_text()))
    return sorted(rows)

def hierarchy(cell):
    return sorted((i.cell.name,str(i.cplx_trans),i.na,i.nb,str(i.a),str(i.b)) for i in cell.each_inst())

def same_material(pya,expected,actual):
    assert set(expected)==set(actual),("Changed material layer census",set(expected)^set(actual))
    for key in expected:
        assert (expected[key]^actual[key]).is_empty(),("Changed material",key)

def native_stack(pya,lib):
    sys.dont_write_bytecode=True
    sys.path[:0]=[str(lib),str(lib/"pycell4klayout-api/source/python")]
    import sg13g2_pycell_lib  # Native frozen registration, never a replacement renderer.
    n=pya.Layout()
    cell=n.create_cell("via_stack","SG13_dev",dict(plan.PARAMETERS))
    assert n.dbu==.001 and cell is not None and not cell.is_empty()
    assert not list(cell.each_inst())
    params=cell.pcell_parameters_by_name()
    assert all(params[k]==v for k,v in plan.PARAMETERS.items()),params
    shapes=material(pya,n,cell,True)
    assert set(shapes)==set(plan.ALLOWED_LAYERS)
    for li in n.layer_indexes():
        for s in cell.shapes(li).each():
            assert not s.is_text() and s.properties()=={}
    # Keep the native coordinates, not a guessed centered or rescaled via.
    # This frozen renderer draws exactly around the database origin.
    for key,r in shapes.items():
        assert r.count()==1 and r.bbox().center()==pya.Point(0,0),("Unexpected native landing",key)
    low,cut,high=(shapes[k] for k in plan.ALLOWED_LAYERS)
    assert cut.count()==1 and cut.area()>0
    assert (cut-low).is_empty() and (cut-high).is_empty()
    assert low.bbox().width()>=1640 and low.bbox().height()>=1640
    assert high.bbox().height()<=3200 and high.bbox().width()<=3200
    assert all(v%5==0 for r in shapes.values() for b in [r.bbox()] for v in (b.left,b.bottom,b.right,b.top))
    return n,cell,shapes,params

def add_plan(pya,stack):
    result={k:pya.Region() for k in plan.ALLOWED_LAYERS}
    taps=[]
    for x in plan.LANES_DBU:
        tr=pya.Trans(x,plan.CENTER_Y_DBU)
        rows={k:r.transformed(tr) for k,r in stack.items()}
        for k,r in rows.items():result[k]+=r
        taps.append(rows)
    result[(134,0)]+=pya.Region(pya.Box(*plan.BUS_DBU))
    result={k:r.merged() for k,r in result.items()}
    assert len(taps)==8 and result[(133,0)].count()==8
    assert result[(134,0)].count()==1
    return result,taps

def placement_matches(inst,dx,dy):
    tr=inst.cplx_trans
    return tr.mag==1 and tr.angle==0 and not tr.is_mirror() and tr.disp.x==dx and tr.disp.y==dy

def owned_clearance(pya,layout,top,db,placements,additions,taps):
    full=material(pya,layout,top,True)
    native={}
    for metal in (126,134):
        r=full[(metal,0)]
        matches=[i for i in db.layer_indexes() if (db.layer_by_index(i).merged()^r).is_empty()]
        assert len(matches)==1,("Native layer not uniquely equal to actual full parent",metal)
        native[metal]=db.layer_by_index(matches[0])
    proof=[]
    for tag,inst in placements.items():
        dx,dy,cluster,component=plan.PLACEMENTS[tag]
        assert placement_matches(inst,dx,dy)
        tr=inst.cplx_trans
        owned_low=pya.Region()
        tap_rows=[]
        for i,tap in enumerate(taps):
            low=tap[(126,0)].transformed(tr)
            center=pya.Point(plan.LANES_DBU[i]+dx,plan.CENTER_Y_DBU+dy)
            net=db.probe_net(native[126],center)
            assert net is not None and net.cluster_id==cluster,("TM1 tap has wrong actual owner",tag,i)
            old=full[(126,0)].interacting(pya.Region(pya.Box(center.x-1,center.y-1,center.x+1,center.y+1)))
            assert old.count()==1 and not (old&low).is_empty()
            owned_low+=old
            tap_rows.append({"lane":i,"center_dbu":[center.x,center.y],
                "actual_native_cluster":net.cluster_id,"old_component_area_dbu2":old.area()})
        owned_low=owned_low.merged()
        # The old full y240 bus identifies ownership of the new parallel bus.
        buspoint=pya.Point(700000+dx,240000-3970+dy)
        net=db.probe_net(native[134],buspoint)
        assert net is not None and net.cluster_id==cluster,("Old TM2 bus has wrong owner",tag)
        old_bus=full[(134,0)].interacting(pya.Region(pya.Box(buspoint.x-1,buspoint.y-1,buspoint.x+1,buspoint.y+1)))
        assert old_bus.count()==1
        assert old_bus.area()==2148880000,("Unexpected original M_TE bus material",tag)
        actual={k:r.transformed(tr) for k,r in additions.items()}
        for metal,owned in ((126,owned_low),(134,old_bus)):
            foreign=(full[(metal,0)]-owned).merged()
            assert actual[(metal,0)].sized(plan.CLEARANCE_DBU[metal]).interacting(foreign).is_empty(),("Foreign metal clearance",tag,metal)
        # New taps are at previously via-free positions; reject contact to any
        # existing adjacent via rather than infer its owner from its name.
        old125=full.get((125,0),pya.Region())
        old133=full.get((133,0),pya.Region())
        assert actual[(126,0)].interacting(old125+old133).is_empty(),("Existing adjacent via touches new TM1 landing",tag)
        assert actual[(134,0)].interacting(old133).is_empty(),("Existing TopVia2 touches new TM2 bus",tag)
        assert actual[(133,0)].sized(plan.CLEARANCE_DBU[133]).interacting(old133).is_empty(),("TopVia2 spacing",tag)
        for tap in taps:
            low=tap[(126,0)].transformed(tr);cut=tap[(133,0)].transformed(tr);high=tap[(134,0)].transformed(tr)
            assert (cut-(owned_low+actual[(126,0)])).is_empty()
            assert (cut-actual[(134,0)]).is_empty()
            assert (high-actual[(134,0)]).is_empty() and not (low&owned_low).is_empty()
        proof.append({"placement":tag,"old_native_cluster":cluster,"old_wire_component":component,
                      "old_TM2_area_dbu2":old_bus.area(),"taps":tap_rows,
                      "full_parent_metal_clearance_dbu":dict(plan.CLEARANCE_DBU),
                      "adjacent_existing_via_contacts":0})
    assert len(proof)==2 and sum(len(x["taps"]) for x in proof)==16
    return proof

def verify_snapshot(pya,layout,before,expected_child,old_top_bbox):
    assert {c.name for c in layout.each_cell()}==set(before)
    assert layout.cell(plan.TOP).bbox()==old_top_bbox
    for name,(old_mat,old_raw,old_inst) in before.items():
        cell=layout.cell(name);assert cell is not None
        same_material(pya,expected_child if name==plan.CHILD else old_mat,material(pya,layout,cell))
        actual_raw=raw_records(layout,cell)
        if name==plan.CHILD:
            old_counter=collections.Counter(old_raw);new_counter=collections.Counter(actual_raw)
            assert not (old_counter-new_counter),("Changed original raw shape/text/property records",name)
            extra=list((new_counter-old_counter).elements())
            assert extra and all((r[0],r[1]) in plan.ALLOWED_LAYERS and r[3]=="{}" and r[4] is False for r in extra)
        else:
            assert actual_raw==old_raw,("Changed raw shape/text/property records",name)
        assert hierarchy(cell)==old_inst,("Changed primitive placement or hierarchy",name)

def native_controls(pya,candidate,before,expected_child,old_bbox,additions):
    """Actual fresh serialized candidate for every positive and geometry fault."""
    results=[]
    def read():
        l=pya.Layout();l.read(str(candidate))
        assert l.dbu==.001
        verify_snapshot(pya,l,before,expected_child,old_bbox)
        return l,l.cell(plan.CHILD)
    def replace_layer(l,c,key,r):
        li=l.layer(*key);c.shapes(li).clear();c.shapes(li).insert(r)
    def missing_via(l,c):
        key=(133,0);polys=list(additions[key].each())
        assert len(polys)==8
        r=expected_child[key]-pya.Region(polys[-1])
        assert r.area()<expected_child[key].area()
        replace_layer(l,c,key,r)
    def translated_bus(l,c):
        key=(134,0)
        r=(before[plan.CHILD][0].get(key,pya.Region())+additions[key].transformed(pya.Trans(0,5))).merged()
        assert not (r^expected_child[key]).is_empty()
        replace_layer(l,c,key,r)
    def remove_original_m3(l,c):
        key=(30,0);old=before[plan.CHILD][0][key]
        poly=next(old.each());r=expected_child[key]-pya.Region(poly)
        assert r.area()<expected_child[key].area()
        replace_layer(l,c,key,r)
    def foreign_metal(l,c):
        c.shapes(l.layer(8,0)).insert(pya.Box(0,0,5,5))
    def forbidden_annotation(l,c):
        c.shapes(l.layer(134,2)).insert(pya.Box(*plan.BUS_DBU))
    def added_text(l,c):
        c.shapes(l.layer(126,0)).insert(pya.Text("UNAUTHORIZED_CONTROL",pya.Trans(500000,plan.CENTER_Y_DBU)))
    def changed_property(l,c):
        shapes=[q for li in l.layer_indexes() for q in c.shapes(li).each()]
        assert shapes
        shapes[0].set_property("tail-wire-control","changed")
    def changed_label(l,c):
        labels=[q for cell in l.each_cell() for li in l.layer_indexes() for q in cell.shapes(li).each() if q.is_text()]
        assert labels
        shape=labels[0];value=shape.text
        value.string=value.string+"__CONTROL"
        shape.text=value
    def extra_cell(l,c):
        assert l.cell("UNAUTHORIZED_CONTROL_CELL") is None
        l.create_cell("UNAUTHORIZED_CONTROL_CELL")
    def extra_child_instance(l,c):
        l.cell(plan.TOP).insert(pya.CellInstArray(c.cell_index(),pya.Trans(0,0)))
    def missing_landing(l,c):
        key=(126,0);poly=next(additions[key].each())
        r=expected_child[key]-pya.Region(poly)
        assert r.area()<expected_child[key].area()
        replace_layer(l,c,key,r)
    mutations=(("missing_actual_via",missing_via),("translated_new_bus",translated_bus),
      ("removed_original_M3",remove_original_m3),("foreign_M1",foreign_metal),
      ("forbidden_pin_annotation",forbidden_annotation),("added_text_on_allowed_layer",added_text),
      ("changed_original_property",changed_property),("changed_original_label",changed_label),
      ("extra_cell",extra_cell),("extra_shared_child_instance",extra_child_instance),
      ("missing_native_landing",missing_landing))
    for name,mutate in mutations:
        l,c=read()
        mutate(l,c)
        try:verify_snapshot(pya,l,before,expected_child,old_bbox)
        except AssertionError as e:
            results.append({"case":name,"fresh_actual_baseline_passed":True,
                            "actual_geometry_mutated":True,"rejected":True,"error":repr(e)})
        else:raise AssertionError("Accepted actual geometry fault: "+name)
    assert len(results)==11 and all(r["rejected"] for r in results)
    return {"status":"PASS_ACTUAL_SERIALIZED_GEOMETRY_CONTROLS","positive_before_each_fault":11,
            "faults_rejected":11,"cases":results,"physical_or_electrical_acceptance":False}

def generate_admitted(source,out,pdk,admission):
    expected,runtime,lib,handoff,proposal=admission
    assert out.is_absolute() and out.resolve()==out and not out.exists() and out.is_relative_to(ROOT/"hw/soc/out")
    assert not out.is_relative_to(source) and not source.is_relative_to(out)
    import pya
    layout=pya.Layout();layout.read(str(source/GDS))
    top=layout.cell(plan.TOP);child=layout.cell(plan.CHILD)
    assert top is not None and child is not None and layout.dbu==.001
    parents=[(c.name,i) for c in layout.each_cell() for i in c.each_inst() if i.cell_index==child.cell_index()]
    assert len(parents)==2 and all(name==plan.TOP and i.size()==1 for name,i in parents)
    placements={}
    for tag,(dx,dy,cluster,component) in plan.PLACEMENTS.items():
        found=[i for _,i in parents if placement_matches(i,dx,dy)]
        assert len(found)==1
        placements[tag]=found[0]
    meta=json.loads((source/"parent/layout/result.json").read_text())
    for tag,inst in placements.items():
        assert str(inst.dbbox())==meta["placements"][tag]["bbox_um"]
    anchors=json.loads((source/"wire/anchors08.json").read_text())
    assert len(anchors["rows"])==1446 and anchors["logical_anchor_count"]==978 and anchors["public_ports"]==25
    for row in handoff["native_terminal_rows"]:
        assert [r for r in anchors["rows"] if r.get("wire_anchor")==row["wire_anchor"]]==[row]
    db=pya.LayoutVsSchematic();db.read(str(source/LVS))
    circuit=db.netlist().top_circuit()
    assert circuit.name==plan.TOP and circuit.pin_count()==25 and len(list(circuit.each_device()))==500
    before={c.name:(material(pya,layout,c),raw_records(layout,c),hierarchy(c)) for c in layout.each_cell()}
    old_bbox=top.bbox()
    native_layout,native_cell,stack,params=native_stack(pya,lib)
    additions,taps=add_plan(pya,stack)
    ownership=owned_clearance(pya,layout,top,db,placements,additions,taps)
    expected_child=dict(before[plan.CHILD][0])
    for key,r in additions.items():
        assert key in plan.ALLOWED_LAYERS
        expected_child[key]=(expected_child.get(key,pya.Region())+r).merged()
        child.shapes(layout.layer(*key)).insert(r)
    expected_raw=raw_records(layout,child)
    prior=collections.Counter(before[plan.CHILD][1]);now=collections.Counter(expected_raw)
    assert not (prior-now), "An original raw record was removed"
    added_records=list((now-prior).elements())
    assert added_records and all((r[0],r[1]) in plan.ALLOWED_LAYERS and r[3]=="{}" and r[4] is False for r in added_records)
    verify_snapshot(pya,layout,before,expected_child,old_bbox)
    parent=out/"parent";parent.mkdir(parents=True)
    shutil.copytree(source/"parent/inputs",parent/"inputs")
    shutil.copyfile(source/"parent/children.json",parent/"children.json")
    dest=parent/"layout";dest.mkdir()
    for name in ("schematic.cir",plan.TOP+".lef"):
        shutil.copyfile(source/"parent/layout"/name,dest/name)
    layout.write(str(dest/(plan.TOP+".gds")))
    reread=pya.Layout();reread.read(str(dest/(plan.TOP+".gds")))
    assert reread.dbu==.001
    verify_snapshot(pya,reread,before,expected_child,old_bbox)
    controls=native_controls(pya,dest/(plan.TOP+".gds"),before,expected_child,old_bbox,additions)
    (out/"native-geometry-controls.json").write_text(json.dumps(controls,indent=2)+"\n")
    manifest=json.loads((parent/"children.json").read_text())
    directory=parent/manifest["children"]["sampler_cd"]["directory"]
    assert directory.resolve()==(parent/"inputs/sampler_cd/layout").resolve()
    assert meta["source_plan"]["types"]["sampler_cd"]["top"]==plan.LEAF
    leaf=pya.Layout();leaf_top=leaf.create_cell(plan.LEAF);leaf_top.copy_tree(reread.cell(plan.CHILD))
    old_leaf=directory/(plan.LEAF+".gds")
    shutil.copyfile(old_leaf,directory/"pre-tail-access-wire.gds")
    leaf.write(str(old_leaf))
    leaf_read=pya.Layout();leaf_read.read(str(old_leaf))
    assert leaf_read.dbu==.001
    for c in leaf_read.each_cell():
        original=reread.cell(plan.CHILD if c.name==plan.LEAF else c.name)
        assert original is not None
        same_material(pya,material(pya,reread,original),material(pya,leaf_read,c))
        assert raw_records(leaf_read,c)==raw_records(reread,original),("Copied child raw record changed",c.name)
        assert hierarchy(c)==hierarchy(original),("Copied child hierarchy changed",c.name)
    same_material(pya,material(pya,reread,reread.cell(plan.CHILD),True),material(pya,leaf_read,leaf_read.cell(plan.LEAF),True))
    child_meta=json.loads((directory/"result.json").read_text())
    assert child_meta["origin_translation_um"]==[0,-3.97]
    old_routes=child_meta["routes"]
    assert [r for r in old_routes if r["net"]=="M_TE"]==handoff["actual_M_TE_routes"]
    shutil.copyfile(directory/"result.json",directory/"pre-tail-access-wire-result.json")
    proof={"status":"GENERATED_UNQUALIFIED_ADDITIVE_TAIL_ACCESS_WIRE",
      "proposal":proposal,"ownership_and_clearance":ownership,"native_parameters":params,"native_geometry_controls":controls,
      "native_stack_raw":raw_records(native_layout,native_cell),
      "native_stack_layers":{str(k):{"bbox_dbu":str(r.bbox()),"area_dbu2":r.area()} for k,r in stack.items()},
      "added_local_material":{str(k):{"polygons":[str(p) for p in r.each()],"area_dbu2":r.area()} for k,r in additions.items()},
      "added_raw_records":added_records,"all_existing_cell_material_text_properties_hierarchy_preserved":True,
      "serialized_full_parent_verified":True,"serialized_child_material_raw_and_hierarchy_verified":True,
      "original_device_count":500,"original_terminal_count":1446,"original_anchor_count":978,
      "post_layout_LVS_executed":False,"DRC_executed":False,"fresh_RC_executed":False,
      "simulation_executed":False,"physical_accepted":False,"electrical_accepted":False}
    child_meta["status"]=proof["status"]
    child_meta["tail_access_wire"]=proof
    child_meta["output_sha256"]={p.name:sha(p) for p in directory.iterdir() if p.is_file() and p.name!="result.json"}
    assert child_meta["routes"]==old_routes
    (directory/"result.json").write_text(json.dumps(child_meta,indent=2)+"\n")
    meta["status"]=proof["status"];meta["tail_access_wire"]=proof
    meta["output_sha256"]={p.name:sha(p) for p in dest.iterdir() if p.is_file()}
    (dest/"result.json").write_text(json.dumps(meta,indent=2)+"\n")
    assert sha(dest/"schematic.cir")==expected["parent/layout/schematic.cir"]
    assert sha(dest/(plan.TOP+".lef"))==expected["parent/layout/"+plan.TOP+".lef"]
    assert files(source)==expected
    assert {str(p.relative_to(lib)):sha(p) for p in lib.rglob("*") if p.is_file() and p.suffix in (".py",".json")}==runtime
    proof["original349_files_and88_runtime_sources_unchanged"]=True
    proof["outputs"]=files(out)
    (out/"result.json").write_text(json.dumps(proof,indent=2)+"\n")
    return proof

def generate(source,out,pdk):
    admission=source_gate(source,pdk)
    expected,runtime,lib,_,_=admission
    try:
        return generate_admitted(source,out,pdk,admission)
    finally:
        assert files(source)==expected,"Original source changed, including on a failed generation"
        assert {str(p.relative_to(lib)):sha(p) for p in lib.rglob("*") if p.is_file() and p.suffix in (".py",".json")}==runtime,"Frozen runtime changed"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--pdk",type=Path,required=True)
    a=p.parse_args()
    result=generate(a.source,a.out,a.pdk)
    print(json.dumps({"status":result["status"],"physical_accepted":False,"electrical_accepted":False}))
if __name__=="__main__":main()
