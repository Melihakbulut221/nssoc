#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Witness-bound copies for the unchanged topology gate; no CAD or extraction."""
import copy
import hashlib
import json
from pathlib import Path
import cdr_v59_tail_access_topology as topology
import cdr_v59_tail_saved_identity_native as acquired

TOPOLOGY_SHA="df8b0e712cd224c6af66d88e91242d4e5b5d8b75a96ebf81179cb740c06c3a37"
ACQUIRED_SHA="4eab1f31c2414b6061c72096405f9688d8c1f03c6f31cb0fd505c17bd0523510"
FIELDS=("graph","locations","anchors")

def require(value,message):
    if not value:raise AssertionError(message)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def source_guard():
    for module,expected in ((topology,TOPOLOGY_SHA),(acquired,ACQUIRED_SHA)):
        path=Path(module.__file__)
        require(path.is_file() and not path.is_symlink(),"Topology dependency is not a regular file")
        require(hashlib.sha256(path.read_bytes()).hexdigest()==expected,"Topology dependency bytes changed")

def differences(before,after,path=()):
    if canonical(before)==canonical(after):return []
    if type(before) is type(after) is dict and set(before)==set(after):
        return [row for key in sorted(before) for row in differences(before[key],after[key],path+(key,))]
    if type(before) is type(after) is list and len(before)==len(after):
        return [row for i,(a,b) in enumerate(zip(before,after)) for row in differences(a,b,path+(i,))]
    return [{"path":list(path),"before":copy.deepcopy(before),"after":copy.deepcopy(after)}]

def original_rejection(old,new):
    try:topology.compare([old[k] for k in FIELDS],[new[k] for k in FIELDS],True)
    except AssertionError as error:
        tb=error.__traceback__
        while tb.tb_next:tb=tb.tb_next
        require(Path(tb.tb_frame.f_code.co_filename).resolve()==Path(topology.__file__).resolve()
          and tb.tb_frame.f_code.co_name=="compare" and tb.tb_lineno==107 and error.args==(),
          "Original comparison did not reproduce the exact saved native_ports failure")
        return {"error":repr(error),"function":"compare","line":107,"source_sha256":TOPOLOGY_SHA}
    raise AssertionError("Original comparator unexpectedly accepted")

def own_witness(value):
    index=topology.graph_index(value["graph"])
    paths=value["paths"]
    require(len(paths)==500 and all(type(r["native_device"]) is int for r in paths)
      and {r["native_device"] for r in paths}==set(range(1,501)),
      "Acquired path IDs are not the exact unique500")
    pins=value["native_pins"]
    require(len(pins)==25 and all(type(r["native_pin_id"]) is int and r["native_pin_id"]>=0 for r in pins)
      and len({r["native_pin_id"] for r in pins})==25,"Acquired pin IDs are not unique25")
    require([r["iteration_index"] for r in pins]==list(range(25))
      and all(type(r["iteration_index"]) is int for r in pins),"Acquired pin iteration indices changed")
    anchors={a["detail"]["public_port"]:a for a in value["anchors"]["anchors"] if "public_port" in a["detail"]}
    require(len(anchors)==25,"Acquired public anchor census changed")
    require(value["graph"]["native_ports"]==[r["name"] for r in pins],
      "Raw graph port order does not match acquired pin iteration")
    for pin in pins:
        cluster=pin["native_cluster"]
        require(cluster in index["nets"] and pin["name"] in index["nets"][cluster]["row"]["public_ports"],
          "Acquired pin name/cluster join changed")
        require(pin["name"] in anchors and anchors[pin["name"]]["native_cluster"]==cluster,
          "Acquired pin anchor/cluster join changed")
        require(pin["full_partition"]==json.loads(index["nets"][cluster]["key"]),
          "Acquired full partition does not match raw graph")
        require(pin["full_anchor"]==topology.normalize(anchors[pin["name"]],index),
          "Acquired full anchor does not match raw anchors")

def project_pair(old,new):
    source_guard()
    originals={"old":old,"new":new}
    original_hashes={side:digest(value) for side,value in originals.items()}
    comparison=acquired.compare_witnesses(old,new)
    for value in originals.values():own_witness(value)
    rejection=original_rejection(old,new)
    projected={side:{k:copy.deepcopy(value[k]) for k in FIELDS} for side,value in originals.items()}
    reference_order=list(old["graph"]["native_ports"])
    planned={"old":[],"new":[]}
    for side,value in originals.items():
        view=projected[side]
        paths={row["native_device"]:row for row in value["paths"]}
        require(len(paths)==len(value["paths"])==500,"Duplicate or missing acquired path")
        for i,row in enumerate(view["locations"]["devices"]):
            witness=paths[row["native_id"]]
            require(row["model"]==witness["model"] and row["pcell"]["path"]==witness["raw_path"],
              "Projection path is not bound to exact acquired device")
            stable=canonical(witness["stable_path"])
            require(isinstance(witness["stable_path"],dict) and isinstance(witness["stable_path"].get("levels"),list) and len(witness["stable_path"]["levels"])>0,
              "Empty stable native path")
            planned[side].append({"path":["locations","devices",i,"pcell","path"],
              "before":row["pcell"]["path"],"after":stable})
            row["pcell"]["path"]=stable
        before=view["graph"]["native_ports"]
        for i,(a,b) in enumerate(zip(before,reference_order)):
            if a!=b:planned[side].append({"path":["graph","native_ports",i],"before":a,"after":b})
        view["graph"]["native_ports"]=list(reference_order)
        actual=differences({k:value[k] for k in FIELDS},view)
        order=lambda row:canonical(row["path"])
        require(sorted(actual,key=order)==sorted(planned[side],key=order),
          "Projection changed an unapproved field")
    require({side:digest(value) for side,value in originals.items()}==original_hashes,
      "Projection mutated an original acquired witness")
    return {"original_sha256":original_hashes,
      "projected_sha256":{side:digest(value) for side,value in projected.items()},
      "deltas":planned,"comparison":comparison,"original_rejection":rejection,
      "views":projected,"reference_order_use":"Comparator equality/set checks only; never SPICE order"}

def compare_pair(old,new):
    projected=project_pair(old,new)
    views=projected.pop("views")
    late=topology.compare([views["old"][k] for k in FIELDS],
                          [views["new"][k] for k in FIELDS],True)
    require(late["added_material_required"] is True,"Added-material gate was disabled")
    require(late["physical_accepted"] is late["electrical_accepted"] is late["qualified_pex"] is False,
      "Topology comparator acceptance scope changed")
    return {"status":"PASS_WITNESS_BOUND_TOPOLOGY_PROJECTION_ALL_ORIGINAL_LATE_GATES",
      **projected,"unchanged_comparator_result":late,
      "supplemental_identity_projection_policy":"Only the fully acquired native_ports name order and full stable_path JSON text are substituted in copies; the original comparator policy alone does not describe these two supplementary identity projections.",
      "source_equality_claimed":False,"original_physical_failure_preserved":True,
      "typed_raw_material_proof_required_separately":True,
      "fresh_RC_executed":False,"physical_accepted":False,"electrical_accepted":False,
      "qualified_pex":False,"full_phy_accepted":False}
