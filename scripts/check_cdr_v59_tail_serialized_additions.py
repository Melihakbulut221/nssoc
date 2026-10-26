#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted actual-JSON/raw-guard fixtures; native geometry API objects are synthetic."""
import ast
import collections
import copy
import json
from pathlib import Path
import re
import tempfile
import types
import cdr_v59_tail_saved_identity as s
import cdr_v59_tail_saved_identity_native as n
import cdr_v59_tail_serialized_additions as gate

PREFIX="docs/evidence/cdr-v59-tail-saved-identity-raw-diagnostic-native-terminal-20261026"
FROZEN="docs/evidence/cdr-v59-tail-saved-identity-pre-serialization-native-20261026.py"

class TypedBox:
    def __init__(self,*bounds):self.bounds=tuple(bounds)

class TypedPolygon:
    def __init__(self,box):
        self.bounds=box.bounds;self.holes_value=0;self.points_value=4;self.box_value=True
    def holes(self):return self.holes_value
    def num_points_hull(self):return self.points_value
    def is_box(self):return self.box_value
    def __eq__(self,other):
        return isinstance(other,TypedPolygon) and self.bounds==other.bounds and self.holes_value==other.holes_value and self.points_value==other.points_value

def typed_shape(shape,fault=None):
    text=shape.to_s()
    box=re.fullmatch(r"box \((-?\d+),(-?\d+);(-?\d+),(-?\d+)\)",text)
    polygon=re.fullmatch(r"polygon \((-?\d+),(-?\d+);(-?\d+),(-?\d+);(-?\d+),(-?\d+);(-?\d+),(-?\d+)\)",text)
    # This is explicitly an API-shaped stub, not native KLayout qualification.
    if box:bounds=tuple(map(int,box.groups()))
    elif polygon:
        q=tuple(map(int,polygon.groups()));bounds=(q[0],q[1],q[4],q[5])
    else:bounds=(0,0,0,0)
    p=TypedPolygon(TypedBox(*bounds))
    if fault=="geometry":p.bounds=(bounds[0]+1,)+bounds[1:]
    elif fault=="holes":p.holes_value=1
    elif fault=="hull":p.points_value=5
    elif fault=="nonrectangle":p.box_value=False
    shape.is_box=lambda:bool(box) and fault!="type"
    shape.is_polygon=lambda:bool(polygon) and fault!="type"
    shape.polygon=None if fault=="missing" else p
    return shape

def controls(base):
    pins=s.methods()["protected_sha256"]
    diagnostic_path=s.ROOT/(PREFIX+"-raw-hierarchy-diagnostic.json")
    assert s.sha(diagnostic_path)==pins[PREFIX+"-raw-hierarchy-diagnostic.json"]==gate.DIAGNOSTIC_SHA
    diagnostic=s.read_json(diagnostic_path)
    contract=s.read_json(s.ROOT/gate.CONTRACT)
    generation=diagnostic["original_generation_report"]
    old={c["cell"]:[tuple(row["record"]) for row in c["original_raw_counter"] for _ in range(row["multiplicity"])] for c in diagnostic["cells"]}
    current={c["cell"]:[tuple(row["record"]) for row in c["current_raw_counter"] for _ in range(row["multiplicity"])] for c in diagnostic["cells"]}
    assert len(old)==len(current)==140 and len(old[n.CHILD])==925 and len(current[n.CHILD])==942
    assert diagnostic["raw_counter_mismatch_cells"]==[n.CHILD]
    assert diagnostic["non_target_original_deficit_cells"]==diagnostic["hierarchy_mismatch_cells"]==diagnostic["instance_property_mismatch_cells"]==[]
    def function_text(text,name):
        node=next(x for x in ast.parse(text).body if isinstance(x,ast.FunctionDef) and x.name==name)
        return ast.get_source_segment(text,node)
    assert function_text((s.ROOT/FROZEN).read_text(),"raw_hierarchy_proof")==function_text(
      Path(n.__file__).read_text(),"raw_hierarchy_proof")
    positives=["original_exact_raw_guard_byte_identical_to_frozen_failed_source"]
    refusals=[]
    first=tuple(contract["pairs"][0]["serialized_record"])
    original_non_target=next(name for name in sorted(old) if name!=n.CHILD and old[name])
    def layouts(a,b,options=None,typed_fault=None):
        options=options or {}
        left=base.raw_fixture_layout(a,bbox=diagnostic["original_top_bbox_dbu"])
        right=base.raw_fixture_layout(b,bbox=diagnostic["current_top_bbox_dbu"],**options)
        for cell in right.each_cell():
            previous=cell.shapes
            def shapes(li,previous=previous,cell=cell):
                result=[]
                for shape in previous(li).each():
                    info=right.get_info(li)
                    record=(info.layer,info.datatype,shape.to_s(),json.dumps(shape.properties(),sort_keys=True,separators=(",",":")),shape.is_text())
                    result.append(typed_shape(shape,typed_fault if cell.name==n.CHILD and record==first else None))
                return types.SimpleNamespace(each=lambda:iter(result))
            cell.shapes=shapes
        return left,right
    pya=types.SimpleNamespace(Box=TypedBox,Polygon=TypedPolygon)
    def run(label,change=None,message=None,options=None,typed_fault=None):
        a=copy.deepcopy(old);b=copy.deepcopy(current)
        if change:change(a,b)
        left,right=layouts(a,b,options,typed_fault)
        with tempfile.TemporaryDirectory(prefix="cdr-serialized-additions-") as td:
            root=Path(td)
            # Real frozen original function and source-derived record helpers, no mocked guard.
            if message is None:
                rejected=gate.reproduce_original_failure(n.raw_hierarchy_proof,left,right,generation,s.ROOT/s.GENERATOR)
                s.write(root/"original-raw-guard-rejection.json",rejected)
                assert s.read_json(root/"original-raw-guard-rejection.json")==rejected
                assert rejected["original_guard_passed"] is False and rejected["original_failure_preserved"]
            try:proof=gate.verify(pya,n.properties,left,right,generation,s.ROOT/s.GENERATOR)
            except AssertionError as error:
                assert message is not None and str(error)==message,(label,str(error),message)
                refusals.append({"case":label,"reason":str(error)})
            else:
                assert message is None,label
                s.write(root/"raw-hierarchy-proof.json",proof)
                assert s.read_json(root/"raw-hierarchy-proof.json")==json.loads(json.dumps(proof))
                assert len(proof["cells"])==140 and len(proof["native_typed_additions"])==17
                assert proof["original_exact_guard_passed"] is False and proof["physical_accepted"] is False
                assert sum(v["authorized_addition_count"] for v in proof["cells"])==17
                positives.append({"case":label,"complete_actual_raw_cells":140,"original_records":sum(map(len,a.values())),
                  "typed_additions":17,"original_exact_failure_persisted":True,"real_proof_persisted":True})
    run("all_actual_140_cell_counters_with17_serialized_boxes")
    def one_polygon(a,b):
        index=b[n.CHILD].index(first);b[n.CHILD][index]=tuple(contract["pairs"][0]["prewrite_record"])
    run("one_exact_prewrite_polygon_and16_serialized_boxes",one_polygon)
    validated,expected=gate.validate_contract(contract,generation)
    assert validated==contract and len(expected)==17
    positives.append("actual_protected_generation_and_all17_contract_pairs")
    def replace_first(index,value):
        def change(a,b):
            at=b[n.CHILD].index(first);r=list(b[n.CHILD][at]);r[index]=value;b[n.CHILD][at]=tuple(r)
        return change
    run("target_original_deficit",lambda a,b:b[n.CHILD].remove(a[n.CHILD][0]),"Original raw record or multiplicity changed")
    run("non_target_original_deficit",lambda a,b:b[original_non_target].pop(),"Original raw record or multiplicity changed")
    run("non_target_added_record",lambda a,b:b[original_non_target].append(b[original_non_target][0]),"Addition outside authorized target child")
    run("duplicate_authorized_addition",lambda a,b:b[n.CHILD].append(first),"Exact authorized addition coordinates or multiplicities changed")
    run("missing_authorized_addition",lambda a,b:b[n.CHILD].remove(first),"Exact authorized addition coordinates or multiplicities changed")
    run("boolean_layer",replace_first(0,True),"Invalid raw record types")
    run("added_layer",replace_first(0,135),"Unapproved addition layer/datatype")
    run("added_datatype",replace_first(1,1),"Unapproved addition layer/datatype")
    run("added_property",replace_first(3,'{"1":"changed"}'),"Addition properties or text changed")
    run("added_text",replace_first(4,True),"Addition properties or text changed")
    run("added_coordinate",replace_first(2,"box (1,2;3,4)"),"Exact authorized addition coordinates or multiplicities changed")
    for label,text,message in [
      ("bow_tie","polygon (0,0;10,10;0,10;10,0)","Nonrectangular or self-intersecting polygon"),
      ("skew","polygon (0,0;1,10;10,10;10,0)","Nonrectangular or self-intersecting polygon"),
      ("extra_vertex","polygon (0,0;0,10;5,10;10,10;10,0)","Addition is not an exact box or four-corner polygon"),
      ("zero_width","box (0,0;0,10)","Degenerate or reversed rectangle"),
      ("reversed_box","box (10,0;0,10)","Degenerate or reversed rectangle"),
      ("path","path (0,0;10,10) w=10","Addition is not an exact box or four-corner polygon"),
      ("equal_area_wrong_bounds","box (1,0;1901,1900)","Exact authorized addition coordinates or multiplicities changed")]:
        run(label,replace_first(2,text),message)
    run("changed_named_hierarchy",message="Original named hierarchy changed",options={"hierarchy_changed":True})
    run("changed_instance_property",message="Original instance property/order changed",options={"property_changed":True})
    run("missing_cell",lambda a,b:b.pop(original_non_target),"Complete cell-name inventory changed")
    for fault,message in [("type","Native addition type disagrees with exact raw record"),
      ("holes","Native addition is not a simple rectangle"),("hull","Native addition is not a simple rectangle"),
      ("nonrectangle","Native addition is not a simple rectangle"),("missing","Native addition is not a simple rectangle"),
      ("geometry","Native typed rectangle geometry changed")]:
        run("native_"+fault,message=message,typed_fault=fault)
    def reject(label,call,message):
        try:call()
        except AssertionError as error:
            assert str(error)==message,(label,str(error),message)
            refusals.append({"case":label,"reason":str(error)})
        else:raise AssertionError("Accepted "+label)
    left,right=layouts(old,current);right.dbu=.002
    reject("dbu",lambda:gate.verify(pya,n.properties,left,right,generation,s.ROOT/s.GENERATOR),"Original DBU changed")
    left,right=layouts(old,current);right.cell(n.TOP).bbox=lambda:"changed"
    reject("top_bbox",lambda:gate.verify(pya,n.properties,left,right,generation,s.ROOT/s.GENERATOR),"Original top bbox changed")
    changed=copy.deepcopy(generation);changed["added_raw_records"].pop()
    reject("changed_generation",lambda:gate.validate_contract(contract,changed),"Original generation metadata changed")
    c=copy.deepcopy(contract);c["diagnostic_sha256"]="0"*64
    reject("wrong_acquired_diagnostic",lambda:gate.validate_contract(c,generation),"Wrong acquired rectangle contract")
    c=copy.deepcopy(contract);c["pairs"].pop()
    reject("missing_contract_pair",lambda:gate.validate_contract(c,generation),"Exact seventeen authorized additions required")
    c=copy.deepcopy(contract);c["pairs"][0]["serialized_record"][2]="box (1,2;3,4)"
    reject("wrong_pair_geometry",lambda:gate.validate_contract(c,generation),"Unqualified serialization pair")
    c=copy.deepcopy(contract);c["pairs"][0]["multiplicity"]=2
    reject("changed_pair_multiplicity",lambda:gate.validate_contract(c,generation),"Unqualified serialization pair")
    c=copy.deepcopy(contract);c["pairs"][0]["multiplicity"]=True
    reject("boolean_pair_multiplicity",lambda:gate.validate_contract(c,generation),"Unqualified serialization pair")
    c=copy.deepcopy(contract);c["pairs"][0]["exact_rectangle_bounds_dbu"][0]+=1
    reject("changed_contract_bounds",lambda:gate.validate_contract(c,generation),"Contract rectangle coordinates changed")
    c=copy.deepcopy(contract);c["pairs"][1]=copy.deepcopy(c["pairs"][0])
    reject("duplicate_contract_pair",lambda:gate.validate_contract(c,generation),"Duplicate authorized rectangle")
    b=copy.deepcopy(old);b[n.CHILD]+=list(map(tuple,generation["added_raw_records"]))
    left,right=layouts(old,b)
    reject("original_raw_guard_unexpected_pass",lambda:gate.reproduce_original_failure(
      n.raw_hierarchy_proof,left,right,generation,s.ROOT/s.GENERATOR),"Original exact raw guard unexpectedly passed")
    left,right=layouts(old,current);right.cell(n.TOP).bbox=lambda:"wrong"
    reject("unrelated_original_guard_failure",lambda:gate.reproduce_original_failure(
      n.raw_hierarchy_proof,left,right,generation,s.ROOT/s.GENERATOR),"Original exact raw rejection was not reproduced")
    assert len(positives)==4 and len(refusals)==39,(len(positives),len(refusals))
    return {"status":"PASS_SOURCE_BOUND17_SERIALIZATION_GUARD_CONTROLS",
      "positive_count":4,"refusal_count":39,"positives":positives,"refusals":refusals,
      "actual_140_cell_raw_counter_JSON_used":True,"actual_original_guard_invoked":True,
      "original_generation_and17_additions_bound":True,
      "native_geometry_API_explicitly_synthetic":True,"authored_native_or_CAD_executed":False,
      "actual_native_typed_geometry_validation_completed":False}
