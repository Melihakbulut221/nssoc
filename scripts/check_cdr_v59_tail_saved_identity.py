#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted structural/actual-file controls; synthetic native objects are labeled."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import types
from unittest import mock
import cdr_v59_tail_saved_identity as s
import cdr_v59_tail_saved_identity_native as n
import cdr_v59_tail_access_topology as topology
import cloud_cdr_v59_tail_saved_identity as driver

OLD="docs/evidence/cdr-v59-tail-original-wire-fixture-20261026"
NEW="docs/evidence/cdr-v59-tail-physical-corrected-result-20261026"

def full_structural_pair():
    data={}
    for side,prefix,names in (("old",OLD,("graph.json","locations.json","anchors.json")),
      ("new",NEW,("-strict-wires.json","-locations.json","-anchors.json"))):
        rows=[s.read_json(s.ROOT/(prefix+("/" if side=="old" else "")+name)) for name in names]
        data[side]=dict(zip(("graph","locations","anchors"),rows))
    # Explicitly synthetic stable-name bindings: native proof must resolve the real GDS.
    oldpaths={r["native_id"]:r for r in data["old"]["locations"]["devices"]}
    for side,v in data.items():
        index=topology.graph_index(v["graph"]);paths=[]
        for r in v["locations"]["devices"]:
            expected=oldpaths[r["native_id"]]
            tokens=n.parse_path(expected["pcell"]["path"])
            path={"root":n.TOP,"levels":[{"parent_cell":"synthetic-parent-"+str(i),
              "child_cell":"synthetic-cell-"+str(cell),"instance_ordinal":ordinal,
              "cplx_trans_dbu":"synthetic","dcplx_trans_um":"synthetic","na":0,"nb":0,
              "array_vector_a_dbu":"0,0","array_vector_b_dbu":"0,0","is_regular_array":False,
              "array_element":0,"single_instance_count":1,"instance_properties":[]} for i,(cell,ordinal) in enumerate(tokens)],
              "leaf_cell":r["pcell"]["cell"],"full_transform_um":r["pcell"]["transform"],
              "leaf_bbox_um":r["pcell"]["bbox"]}
            paths.append({"native_device":r["native_id"],"model":r["model"],
              "raw_path":r["pcell"]["path"],"stable_path":path})
        anchors={a["detail"]["public_port"]:a for a in v["anchors"]["anchors"] if "public_port" in a["detail"]}
        pins=[]
        for i,name in enumerate(v["graph"]["native_ports"]):
            cluster=index["ports"][name]
            pins.append({"iteration_index":i,"native_pin_id":i,"name":name,"native_cluster":cluster,
              "full_partition":json.loads(index["nets"][cluster]["key"]),
              "full_anchor":topology.normalize(anchors[name],index)})
        v.update(paths=sorted(paths,key=lambda r:r["native_device"]),native_pins=pins,
          native_device_count=500,native_terminal_count=1446)
    return data["old"],data["new"]

class Transform:
    def __init__(self,value="identity"):self.value=value
    def __mul__(self,other):return Transform(self.value+"/"+other.value)
    def __str__(self):return self.value

class Box:
    def transformed(self,t):return self
    def __str__(self):return "fixture-bbox"

def api_fixture():
    leaf=types.SimpleNamespace(name="fixture-leaf",each_inst=lambda:iter([]),dbbox=lambda:Box())
    inst=types.SimpleNamespace(cell_index=7,is_regular_array=lambda:False,
      cplx_trans="fixture-dbu",dcplx_trans=Transform("translation"),na=0,nb=0,a="0,0",b="0,0",
      size=lambda:1,properties=lambda:{})
    top=types.SimpleNamespace(name=n.TOP,each_inst=lambda:iter([inst]))
    cells={n.TOP:top,7:leaf}
    layout=types.SimpleNamespace(cell=lambda key:cells.get(key))
    pya=types.SimpleNamespace(DCplxTrans=Transform)
    row={"pcell":{"path":n.TOP+"/7_0","cell":"fixture-leaf",
      "transform":"identity/translation","bbox":"fixture-bbox"}}
    return pya,layout,row,inst,leaf

def controls():
    positives=[];refusals=[]
    def reject(label,call,message):
        try:call()
        except AssertionError as error:
            assert str(error)==message,(label,type(error).__name__,str(error),message)
            refusals.append({"case":label,"actual_exception":str(error)})
        else:raise AssertionError("Accepted "+label)
    old,new=full_structural_pair()
    assert n.compare_witnesses(old,new)["devices"]==500
    positives.append("complete_actual_JSON_with_explicit_synthetic_stable_identity")
    try:topology.compare([old[k] for k in ("graph","locations","anchors")],[new[k] for k in ("graph","locations","anchors")],True)
    except AssertionError as e:
        t=e.__traceback__
        while t.tb_next:t=t.tb_next
        assert t.tb_frame.f_code.co_name=="compare" and t.tb_lineno==107 and not e.args
    else:raise AssertionError("Actual original rejection missing")
    positives.append("exact_actual_original_native_ports_failure_line107")
    altered=copy.deepcopy(new);altered["graph"]["native_ports"]=old["graph"]["native_ports"]
    reject("latent_all500_raw_path_rejection",
      lambda:topology.compare([old[k] for k in ("graph","locations","anchors")],[altered[k] for k in ("graph","locations","anchors")],True),
      "Original device geometry, parameters, identity or terminals changed")
    pya,layout,row,inst,leaf=api_fixture()
    baseline=n.stable_path(pya,layout,row)
    assert baseline["levels"][0]["child_cell"]=="fixture-leaf"
    positives.append("actual_path_walker_API_shaped_fixture")
    for label,path,message in (
      ("wrong_root","wrong/7_0","Wrong root or empty instance path"),
      ("empty_path",n.TOP,"Wrong root or empty instance path"),
      ("malformed_index",n.TOP+"/07_0","Malformed cell-index/instance-ordinal token"),
      ("negative_index",n.TOP+"/-1_0","Malformed cell-index/instance-ordinal token"),
      ("missing_ordinal",n.TOP+"/7_1","Instance ordinal is absent"),
      ("wrong_cell_index",n.TOP+"/8_0","Recorded child cell index does not resolve")):
        bad=copy.deepcopy(row);bad["pcell"]["path"]=path
        reject(label,lambda bad=bad:n.stable_path(pya,layout,bad),message)
    for label,key,value,message in (
      ("leaf_name","cell","wrong","Resolved primitive cell name changed"),
      ("leaf_transform","transform","changed","Resolved full transform changed"),
      ("leaf_bbox","bbox","changed","Resolved primitive bbox changed")):
        bad=copy.deepcopy(row);bad["pcell"][key]=value
        reject(label,lambda bad=bad:n.stable_path(pya,layout,bad),message)
    with mock.patch.object(inst,"is_regular_array",lambda:True):
        reject("regular_array",lambda:n.stable_path(pya,layout,row),"Regular array is outside exact original producer scope")
    with mock.patch.object(inst,"size",lambda:2):
        reject("nonregular_iterated_array",lambda:n.stable_path(pya,layout,row),
          "Iterated or multiple instance elements are outside exact original producer scope")
    with mock.patch.object(leaf,"each_inst",lambda:iter([inst])):
        reject("nonleaf",lambda:n.stable_path(pya,layout,row),"Recorded primitive is not a leaf")
    # Every semantic negative starts from the same complete positive pair.
    def mutation(label,change,message):
        bad=copy.deepcopy(new);change(bad)
        reject(label,lambda:n.compare_witnesses(old,bad),message)
    mutations=[
      ("missing_device_count",lambda b:b.update(native_device_count=499),"Wrong witness device census"),
      ("missing_terminal_count",lambda b:b.update(native_terminal_count=1445),"Wrong witness terminal census"),
      ("missing_path",lambda b:b["paths"].pop(),"Missing stable identity"),
      ("device_id",lambda b:b["paths"][0].update(native_device=2),"Device identity changed"),
      ("device_model",lambda b:b["paths"][0].update(model="wrong"),"Device identity changed"),
      ("level_cell",lambda b:b["paths"][0]["stable_path"]["levels"][0].update(child_cell="other"),"Stable instance path changed"),
      ("level_parent",lambda b:b["paths"][0]["stable_path"]["levels"][0].update(parent_cell="other"),"Stable instance path changed"),
      ("level_ordinal",lambda b:b["paths"][0]["stable_path"]["levels"][0].update(instance_ordinal=999),"Stable instance path changed"),
      ("level_transform",lambda b:b["paths"][0]["stable_path"]["levels"][0].update(cplx_trans_dbu="changed"),"Stable instance path changed"),
      ("level_array",lambda b:b["paths"][0]["stable_path"]["levels"][0].update(array_element=[1,0]),"Stable instance path changed"),
      ("level_depth",lambda b:b["paths"][0]["stable_path"]["levels"].pop(),"Stable instance path changed"),
      ("duplicate_port",lambda b:b["native_pins"].append(copy.deepcopy(b["native_pins"][0])),"Duplicate/missing public identity"),
      ("missing_port",lambda b:b["native_pins"].pop(),"Duplicate/missing public identity"),
      ("port_rename",lambda b:b["native_pins"][0].update(name="foreign"),"Public port names changed"),
      ("port_partition",lambda b:b["native_pins"][0]["full_partition"]["terminals"].pop(),"Public name/terminal partition changed"),
      ("port_anchor",lambda b:b["native_pins"][0]["full_anchor"].update(point_dbu=[1,2]),"Public name/anchor binding changed"),
      ("unbound_raw_path",lambda b:b["paths"][0].update(raw_path=n.TOP+"/999_0"),"Stable witness not bound to exact raw location"),
      ("device_parameter",lambda b:b["locations"]["devices"][0]["parameters"].update(W=-1.0),"Full semantic device/parameter/location data changed"),
      ("anchor_coordinate",lambda b:b["anchors"]["anchors"][0].update(point_dbu=[1,2]),"Complete original 978 anchors changed")]
    for label,change,message in mutations:mutation(label,change,message)
    # Renumbering is retained as raw evidence and cannot hide a semantic swap.
    reordered=copy.deepcopy(new);reordered["native_pins"].reverse()
    assert n.compare_witnesses(old,reordered)["ports"]==25
    positives.append("port_enumeration_order_only_with_full_binding_retained")
    require_total=1+6+3+3+len(mutations)
    assert len(positives)==4 and len(refusals)==require_total==32
    return {"status":"PASS_SAVED_IDENTITY_SOURCE_CONTROLS","positives":positives,"refusals":refusals,
      "positive_count":4,"refusal_count":32,"synthetic_native_identity_only":True,
      "actual_original_and_current_JSON_used":True,"native_or_CAD_executed":False}

def admission_controls():
    good=s.read_json(s.ROOT/s.SUMMARY);assert s.validate_summary(good) is good
    assert len(s.expected_files())==931
    positive=2;bad=[]
    variants=[("status",lambda x:x.update(status="PASS")),
      ("source",lambda x:x.update(source_head="0"*40)),("run",lambda x:x.update(run_id=1)),
      ("attempt",lambda x:x.update(run_attempt=2)),("original_error",lambda x:x.update(error="ValueError()")),
      ("failure_site",lambda x:x.update(traceback="elsewhere")),
      ("native_return",lambda x:x["commands"][0].update(returncode=1)),
      ("missing_command",lambda x:x["commands"].pop()),
      ("unexpected_member",lambda x:x["outputs"].update(extra="0"*64)),
      ("missing_member",lambda x:x["outputs"].pop(next(iter(x["outputs"])))),
      ("acceptance",lambda x:x.update(accepted=True)),("saved_integrity",lambda x:x["saved_capsule_integrity"].update(files=705))]
    for name,change in variants:
        v=copy.deepcopy(good);change(v)
        try:s.validate_summary(v)
        except AssertionError:bad.append(name)
        else:raise AssertionError("Accepted "+name)
    assert len(bad)==12
    return {"status":"PASS_SAVED_IDENTITY_ADMISSION_CONTROLS","positives":positive,"refusals":bad}

FROZEN_NATIVE="docs/evidence/cdr-v59-tail-saved-identity-pre-diagnostic-native-20261026.py"

def raw_diagnostic_fixture():
    # API-shaped objects only: these strings are never parsed as CAD geometry.
    base=(126,0,"polygon (0,0;20,0;20,20;0,20)","{}",False)
    added=(134,0,"polygon (100,100;120,100;120,120;100,120)","{}",False)
    original={n.TOP:[],n.CHILD:[base,base],
      "other":[(8,0,"box (1,2;3,4)",'{"1":"original"}',False),
               (8,1,"text ('kept',r0 1,2)","{}",True)]}
    current=copy.deepcopy(original);current[n.CHILD].append(added)
    generation={"added_raw_records":[list(added)],"added_local_material":{
      "134":{"polygons":["synthetic-only-polygon"],"area_dbu2":400}},
      "proposal":{"allowed_added_layers":[[126,0],[133,0],[134,0]]},
      "synthetic_fixture_not_actual_GDS":True}
    return original,current,generation

def raw_fixture_layout(records,*,hierarchy_changed=False,property_changed=False,bbox="(0,0;200,200)"):
    keys=sorted({(r[0],r[1]) for rows in records.values() for r in rows})
    layers={i:types.SimpleNamespace(layer=v[0],datatype=v[1]) for i,v in enumerate(keys)}
    cells={}
    for index,(name,rows) in enumerate(records.items()):
        cell=types.SimpleNamespace(name=name,cell_index=lambda index=index:index,
          bbox=lambda bbox=bbox:bbox)
        def shapes(layer,rows=rows):
            info=layers[layer];selected=[]
            for r in rows:
                if r[:2]!=(info.layer,info.datatype):continue
                selected.append(types.SimpleNamespace(to_s=lambda r=r:r[2],
                  properties=lambda r=r:json.loads(r[3]),is_text=lambda r=r:r[4]))
            return types.SimpleNamespace(each=lambda:iter(selected))
        cell.shapes=shapes;cell.each_inst=lambda:iter([])
        cells[name]=cell
    if n.TOP in cells and n.CHILD in cells:
        inst=types.SimpleNamespace(cell=cells[n.CHILD],
          cplx_trans="changed" if hierarchy_changed else "r0 *1 0,0",
          na=0,nb=0,a="0,0",b="0,0",
          properties=lambda:{1:"changed"} if property_changed else {})
        cells[n.TOP].each_inst=lambda:iter([inst])
    return types.SimpleNamespace(dbu=0.001,each_cell=lambda:iter(cells.values()),
      cell=lambda name:cells.get(name),layer_indexes=lambda:list(layers),get_info=lambda i:layers[i])

def raw_diagnostic_controls():
    # The prior failing function is byte-identical; only an earlier diagnostic call is new.
    import ast
    def function_text(text,name):
        node=next(x for x in ast.parse(text).body if isinstance(x,ast.FunctionDef) and x.name==name)
        return ast.get_source_segment(text,node)
    frozen=s.ROOT/FROZEN_NATIVE
    pins=s.methods()["protected_sha256"]
    assert s.sha(frozen)==pins[FROZEN_NATIVE]
    assert function_text(frozen.read_text(),"raw_hierarchy_proof")==function_text(
      Path(n.__file__).read_text(),"raw_hierarchy_proof")
    positives=["unchanged_complete_raw_hierarchy_function_byte_exact"]
    refusals=[]
    def acquire(label,change=None,expected_error=None,layout_options=None,inspect=None):
        original,current,generation=raw_diagnostic_fixture()
        if change:change(original,current,generation)
        old=raw_fixture_layout(original);new=raw_fixture_layout(current,**(layout_options or {}))
        with tempfile.TemporaryDirectory(prefix="cdr-raw-diagnostic-") as td:
            path=Path(td)/"raw-hierarchy-diagnostic.json"
            context={"synthetic_API_only":True,"case":label}
            proof=n.emit_raw_hierarchy_diagnostic(old,new,generation,s.ROOT/s.GENERATOR,path,context)
            saved=s.read_json(path)
            assert saved==json.loads(json.dumps(proof))
            assert saved["source_identity"]==context and saved["qualified"] is False
            assert saved["counter_records_are_complete"] is True
            assert saved["representation_normalization_applied"] is False
            assert saved["original_generation_report"]==generation
            assert saved["generator_sha256"]==pins[s.GENERATOR]
            assert saved["original_cell_names"]==sorted(original)
            assert saved["current_cell_names"]==sorted(current)
            byname={r["cell"]:r for r in saved["cells"]}
            assert set(byname)==set(original)|set(current)
            for name,row in byname.items():
                # Re-expand every multiplicity to the exact synthetic source rows.
                expand=lambda rows:sorted(tuple(x["record"]) for x in rows for _ in range(x["multiplicity"]))
                assert expand(row["original_raw_counter"])==sorted(original.get(name,[]))
                assert expand(row["current_raw_counter"])==sorted(current.get(name,[]))
                expected=list(original.get(name,[]))
                if name==n.CHILD:expected+=list(map(tuple,generation["added_raw_records"]))
                assert expand(row["expected_raw_counter"])==sorted(expected)
            if inspect:inspect(saved,byname)
            before=path.read_bytes()
            try:n.raw_hierarchy_proof(old,new,generation,s.ROOT/s.GENERATOR)
            except AssertionError as error:
                assert expected_error is not None and str(error)==expected_error,(label,str(error))
                assert path.read_bytes()==before,"Original refusal changed the prior complete diagnostic"
                refusals.append({"case":label,"exact_original_error":str(error),
                  "diagnostic_saved_before_refusal":True,"diagnostic_sha256":s.sha(path),
                  "complete_cells":len(saved["cells"])})
            else:
                assert expected_error is None,label
                assert saved["raw_counter_mismatch_cells"]==[]
                assert byname[n.CHILD]["original_raw_counter"][0]["multiplicity"]==2
                positives.append("complete_exact_addition_and_duplicate_original_multiplicity")
    acquire("exact")
    raw_error="Original shape/text/properties or exact added records changed"
    def replace_added(index,value):
        def change(a,b,g):
            r=list(b[n.CHILD][-1]);r[index]=value;b[n.CHILD][-1]=tuple(r)
        return change
    def mismatch(saved,rows):
        row=rows[n.CHILD]
        assert row["expected_record_deficits"] and row["unexpected_record_counter"]
        assert row["original_record_deficits"]==[]
        assert sum(x["multiplicity"] for x in row["expected_record_deficits"])==1
        assert sum(x["multiplicity"] for x in row["unexpected_record_counter"])==1
    acquire("same_count_changed_added_representation",
      replace_added(2,"box (100,100;120,120)"),raw_error,inspect=mismatch)
    acquire("target_original_record_deficit",lambda a,b,g:b[n.CHILD].pop(0),raw_error)
    def non_target(saved,rows):
        assert saved["non_target_original_deficit_cells"]==["other"]
        assert rows["other"]["original_record_deficits"]
        assert rows[n.CHILD]["raw_counter_equal_expected"] is True
    acquire("non_target_original_deficit",lambda a,b,g:b["other"].pop(0),raw_error,inspect=non_target)
    acquire("non_target_addition",lambda a,b,g:b["other"].append(b["other"][0]),raw_error)
    acquire("added_property",replace_added(3,'{"1":"new-property"}'),raw_error,inspect=mismatch)
    acquire("added_text_state",replace_added(4,True),raw_error,inspect=mismatch)
    acquire("added_layer",replace_added(0,135),raw_error,inspect=mismatch)
    acquire("added_datatype",replace_added(1,1),raw_error,inspect=mismatch)
    acquire("duplicate_addition",lambda a,b,g:b[n.CHILD].append(b[n.CHILD][-1]),raw_error)
    acquire("missing_addition",lambda a,b,g:b[n.CHILD].pop(),raw_error)
    acquire("named_hierarchy",expected_error="Original named hierarchy changed",
      layout_options={"hierarchy_changed":True})
    acquire("instance_property",expected_error="Complete instance property/order binding changed",
      layout_options={"property_changed":True})
    acquire("top_bbox",expected_error="Top bbox changed",layout_options={"bbox":"(0,0;201,200)"})
    acquire("cell_inventory",lambda a,b,g:b.update(renamed=b.pop("other")),
      "Cell-name inventory changed")
    acquire("missing_expected_addition",lambda a,b,g:g.update(added_raw_records=[]),
      "Missing original generation additive records")
    assert len(positives)==2 and len(refusals)==15
    return {"status":"PASS_COMPLETE_RAW_DIAGNOSTIC_BEFORE_UNCHANGED_GUARD",
      "positive_count":2,"refusal_count":15,"positives":positives,"refusals":refusals,
      "actual_frozen_raw_record_and_hierarchy_functions_used":True,
      "real_JSON_persistence_before_actual_guard":True,"native_GDS_or_CAD_executed":False,
      "actual_native_serialization_mismatch_explanation_proven":False}

def main():
    assert s.methods()["source_controls_authorized"] is True
    out=s.ROOT/"hw/soc/out/cdr-v59-tail-saved-identity-source-controls";out.mkdir(parents=True,exist_ok=False)
    result={"status":"RUNNING_SOURCE_AND_ADMISSION"}
    s.write(out/"result.json",result)
    try:
        result["source"]=controls();s.write(out/"result.json",result)
        result["raw_diagnostic"]=raw_diagnostic_controls();s.write(out/"result.json",result)
        import sys
        from check_cdr_v59_tail_serialized_additions import controls as serialization_controls
        result["serialization"]=serialization_controls(sys.modules[__name__]);s.write(out/"result.json",result)
        result["admission"]=admission_controls();result["status"]="PASS_SOURCE_AND_ADMISSION"
    except BaseException as error:
        result.update(status="FAIL_SOURCE_AND_ADMISSION",error=repr(error));raise
    finally:s.write(out/"result.json",result);print(json.dumps(result,indent=2))

if __name__=="__main__":main()
