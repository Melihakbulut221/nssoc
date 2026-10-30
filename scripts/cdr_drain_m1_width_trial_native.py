#!/usr/bin/env python3
"""Exactly two top-level M1 rectangles; serialized equality, never an electrical verdict."""
import argparse,collections,copy,json,shutil,traceback
from pathlib import Path
import cloud_cdr_drain_m1_width_trial as h
import generate_cdr_v59_tail_access_wire as frozen
import cdr_drain_access_feasibility_native as observed
TOP="nssoc_cdr_pd500_resistor_v59"
KEY=(8,0)
require=h.require

def snapshot(pya,layout):
    return {cell.name:dict(material=frozen.material(pya,layout,cell),
      raw=frozen.raw_records(layout,cell),hierarchy=frozen.hierarchy(cell),
      instance_properties=[observed.properties(i)for i in cell.each_inst()])
      for cell in layout.each_cell()}

def validate_snapshot(pya,layout,before,expected_raw,expected_material,bbox):
    require(layout.dbu==.001 and {c.name for c in layout.each_cell()}==set(before),"full cell census/DBU")
    require(layout.cell(TOP).bbox()==bbox,"full parent bounding box")
    for cell in layout.each_cell():
        old=before[cell.name];top=cell.name==TOP
        require(frozen.raw_records(layout,cell)==(expected_raw if top else old["raw"]),"exact original raw records plus only two boxes")
        require(frozen.hierarchy(cell)==old["hierarchy"],"original hierarchy")
        require([observed.properties(i)for i in cell.each_inst()]==old["instance_properties"],"instance properties")
        frozen.same_material(pya,expected_material if top else old["material"],frozen.material(pya,layout,cell))

def insert_and_verify(pya,layout,rows,path):
    require(layout.dbu==.001 and layout.cell(TOP)is not None,"exact parent layout")
    before=snapshot(pya,layout);top=layout.cell(TOP);bbox=top.bbox()
    full=frozen.material(pya,layout,top,True)
    expected_material=dict(before[TOP]["material"])
    addition=pya.Region()
    for row in rows:addition.insert(pya.Box(*row["new"]))
    require(addition.count()==2,"two separated M1 additions")
    expected_material[KEY]=(expected_material.get(KEY,pya.Region())+addition).merged()
    # Independent scratch layer records, not accepting whatever mutation produced.
    scratch=pya.Layout();scratch.dbu=.001;cell=scratch.create_cell("exact_additions")
    for row in rows:cell.shapes(scratch.layer(*KEY)).insert(pya.Box(*row["new"]))
    additions=frozen.raw_records(scratch,cell)
    require(len(additions)==2 and all(r[:2]==KEY and r[3]=="{}"and r[4]is False for r in additions),"exact declared rectangle records")
    expected_raw=sorted(before[TOP]["raw"]+additions)
    for row in rows:top.shapes(layout.layer(*KEY)).insert(pya.Box(*row["new"]))
    validate_snapshot(pya,layout,before,expected_raw,expected_material,bbox)
    target_full=dict(full);target_full[KEY]=(full[KEY]+addition).merged()
    frozen.same_material(pya,target_full,frozen.material(pya,layout,top,True))
    layout.write(str(path))
    reread=pya.Layout();reread.read(str(path))
    validate_snapshot(pya,reread,before,expected_raw,expected_material,bbox)
    frozen.same_material(pya,target_full,frozen.material(pya,reread,reread.cell(TOP),True))
    return dict(cell_count=len(before),original_raw_shapes=sum(len(v["raw"])for v in before.values()),
      added_raw_records=additions,all_original_cells_instances_and_shape_properties_unchanged=True,
      full_recursive_material_exact_original_union_two_rectangles=True),before,expected_raw,expected_material,bbox

def native_controls(pya,out):
    base=pya.Layout();base.dbu=.001;top=base.create_cell(TOP);child=base.create_cell("shared")
    child.shapes(base.layer(8,0)).insert(pya.Box(0,0,160,1000))
    top.insert(pya.CellInstArray(child.cell_index(),pya.Trans(1000,0)))
    top.insert(pya.CellInstArray(child.cell_index(),pya.Trans(3000,0)))
    rows=[dict(new=[1000,0,1160,1000]),dict(new=[3000,0,3160,1000])]
    info,before,raw,material,bbox=insert_and_verify(pya,base,rows,out/"synthetic-control.gds")
    faults=[]
    for name in ("child_shape","third_box","hierarchy","raw_duplicate","shape_property"):
        changed=pya.Layout();changed.read(str(out/"synthetic-control.gds"))
        t=changed.cell(TOP);c=changed.cell("shared")
        if name=="child_shape":c.shapes(changed.layer(8,0)).insert(pya.Box(0,0,5,1000))
        elif name=="third_box":t.shapes(changed.layer(8,0)).insert(pya.Box(1010,0,1015,1000))
        elif name=="hierarchy":t.insert(pya.CellInstArray(c.cell_index(),pya.Trans(1000,0)))
        elif name=="raw_duplicate":t.shapes(changed.layer(8,0)).insert(pya.Box(*rows[0]["new"]))
        else:next(t.shapes(changed.layer(8,0)).each()).set_property(99,"changed")
        try:validate_snapshot(pya,changed,before,raw,material,bbox)
        except AssertionError as exc:faults.append(dict(name=name,rejected=True,error=repr(exc)))
        else:raise AssertionError("Actual native mutation accepted: "+name)
    return dict(status="PASS_ACTUAL_PYA_TWO_BOX_SERIALIZATION_AND_FAULTS",positive=1,refusal=5,
      synthetic_geometry=True,real_candidate_qualified=False,faults=faults)

def original_rails(pya,layout,rows):
    require(layout.cell("nmos$2$1")is not None,"shared PCell")
    def count(cell,ancestry=()):
        require(cell.name not in ancestry,"acyclic hierarchy")
        return sum(i.size()*((1 if i.cell.name=="nmos$2$1"else 0)+count(i.cell,ancestry+(cell.name,)))for i in cell.each_inst())
    require(count(layout.cell(TOP))==16,"shared PCell occurrence count")
    evidence=[]
    for row in rows:
        cell=layout.cell(TOP);trans=pya.ICplxTrans()
        for index,ordinal in observed.parse_path(row["path"]):
            found=list(cell.each_inst())
            require(ordinal<len(found),"instance path ordinal")
            inst=found[ordinal]
            require(inst.cell_index==index and inst.size()==1,"exact instance path")
            trans=trans*inst.cplx_trans;cell=inst.cell
        require(cell.name=="nmos$2$1","exact target PCell")
        matches=[s for s in cell.shapes(layout.layer(8,0)).each()if s.is_box()and
          s.box==pya.Box(750,0,910,36000)and s.properties()=={}]
        require(len(matches)==1,"exact original local160nm rail")
        require(matches[0].box.transformed(trans)==pya.Box(*row["old"]),"exact current top-level rail")
        evidence.append(dict(**row,transform=str(trans),local_box=[750,0,910,36000],shared_cell_unchanged=True))
    return evidence

def run(selected,out,expected):
    config,_,_=h.source_guard(expected);h.context(__import__("os").environ)
    require(not out.exists()and out.is_relative_to(h.ROOT/"hw/soc/out"),"fresh owned candidate output")
    require(h.decode(h.frozen.regular(out.parent,"preflight.json").read_bytes())["source_manifest_sha256"]==expected,"child current preflight")
    require(all(h.pin(h.frozen.regular(selected,n))["sha256"]==v for n,v in config["selected"].items()),"authentic selected input")
    out.mkdir();primary=None
    result=dict(status="FAIL_OR_INCOMPLETE_TWO_M1_RECTANGLES",physical_acceptance=False,electrical_acceptance=False,full_phy_accepted=False)
    try:
        import pya
        result["native_controls"]=native_controls(pya,out)
        layout=pya.Layout();layout.read(str(selected/config["paths"]["gds"]))
        rows=h.validate_rectangles(config["rectangles"])
        result["actual_instance_rails"]=original_rails(pya,layout,rows)
        generated,before,raw,material,bbox=insert_and_verify(pya,layout,rows,out/(TOP+".gds"))
        result.update(generated,status="PASS_EXACT_TWO_TOPCELL_ADDITIONS_NOT_PHYSICAL_ACCEPTANCE",
          serialized_full_raw_and_material_unchanged_except_two_rectangles=True,input_gds=h.pin(selected/config["paths"]["gds"]),
          candidate_gds=h.pin(out/(TOP+".gds")),declared_layer=[8,0],declared_additions=rows,
          no_device_or_via_count_changes=True,DRC_executed=False,LVS_executed=False,fresh_RC_executed=False)
        for key,name in (("lef",TOP+".lef"),("schematic","schematic.cir")):
            shutil.copyfile(selected/config["paths"][key],out/name)
            require(h.pin(out/name)==h.pin(selected/config["paths"][key]),"unchanged LEF/schematic")
        old=h.decode(h.frozen.regular(selected,config["paths"]["layout_report"]).read_bytes())
        require(type(old["ports"])is dict and len(old["ports"])==25,"authentic original25ports")
        record=dict(status="GENERATED_UNQUALIFIED_TWO_M1_RAIL_OVERLAYS",ports=old["ports"],
          inputs={str(selected/n):v for n,v in config["selected"].items()},
          outputs={name:h.pin(out/name)["sha256"]for name in (TOP+".gds",TOP+".lef","schematic.cir")},
          original_input_report=h.pin(selected/config["paths"]["layout_report"]),physical_accepted=False,electrical_accepted=False)
        h.write(out/"result.json",h.encode(record))
    except BaseException as exc:
        primary=exc;result.update(error=repr(exc),traceback=traceback.format_exc())
    for label,fn in (
      ("source_integrity",lambda:h.source_guard(expected)),
      ("input_integrity",lambda:require(all(h.pin(h.frozen.regular(selected,n))["sha256"]==v for n,v in config["selected"].items()),"selected input changed"))):
        try:fn()
        except BaseException as exc:
            result["status"]="FAIL_TERMINAL";result.setdefault("terminal_errors",[]).append(dict(action=label,error=repr(exc)))
            if primary is None:primary=exc
    try:h.write(out/"generation.json",h.encode(result))
    except BaseException as exc:
        if primary is None:primary=exc
        try:print("CDR_DRAIN_M1_GENERATION_UNSAVED "+h.encode(result).decode(),flush=True)
        except BaseException:pass
    if primary is not None:raise primary
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument("--selected",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);p.add_argument("--pins-sha256",required=True)
    a=p.parse_args();print(json.dumps(run(a.selected,a.output,a.pins_sha256),sort_keys=True))
if __name__=="__main__":main()
