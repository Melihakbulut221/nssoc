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

def main():
    assert s.methods()["source_controls_authorized"] is True
    out=s.ROOT/"hw/soc/out/cdr-v59-tail-saved-identity-source-controls";out.mkdir(parents=True,exist_ok=False)
    result={"status":"RUNNING_SOURCE_AND_ADMISSION"}
    s.write(out/"result.json",result)
    try:
        result["source"]=controls();s.write(out/"result.json",result)
        result["admission"]=admission_controls();result["status"]="PASS_SOURCE_AND_ADMISSION"
    except BaseException as error:
        result.update(status="FAIL_SOURCE_AND_ADMISSION",error=repr(error));raise
    finally:s.write(out/"result.json",result);print(json.dumps(result,indent=2))

if __name__=="__main__":main()
