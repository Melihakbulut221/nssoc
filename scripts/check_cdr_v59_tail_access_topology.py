#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted controls of complete saved JSON topology; no native work."""
import copy
import hashlib
import json
import os
from pathlib import Path
import cdr_v59_tail_access_topology as topology

ROOT=Path(__file__).resolve().parents[1]
FIXTURE="docs/evidence/cdr-v59-tail-original-wire-fixture-20261026"
HASHES={"graph.json":"2141727fa6bfdc46ed2ab79176180752de8c7612f8b8ed9423ab629fb80500af",
 "locations.json":"79ebadf8a36a2be02be680e6d276abbd67c9ddf0bd784a069fa27b96d034e066",
 "anchors.json":"2cf0762a1fe8be50e749266bdaa09c4d10de4a17e8151986bf3356949972a4b2"}

def controls():
    assert os.environ.get("GITHUB_ACTIONS")=="true"
    method=json.loads((ROOT/"scripts/cdr-v59-tail-access-wire-methods.json").read_text())
    assert method["source_controls_authorized"] is True
    for path,want in method["protected_sha256"].items():
        p=ROOT/path;assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==want,path
    original=[]
    for name,want in HASHES.items():
        raw=(ROOT/FIXTURE/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==want
        original.append(json.loads(raw))
    baseline=topology.compare(original,copy.deepcopy(original),False)
    renamed=topology.compare(original,topology.renumber_fixture(original),False)
    assert baseline["added_material_required"] is renamed["added_material_required"] is False
    faults=[]
    def reject(name,change,added=False):
        candidate=copy.deepcopy(original);change(candidate)
        try:topology.compare(original,candidate,added)
        except AssertionError as e:faults.append({"case":name,"rejected":True,"error":repr(e)})
        else:raise AssertionError("Accepted full topology fault "+name)
    reject("changed_device_parameter",lambda x:x[1]["devices"][0]["parameters"].update(W=54))
    reject("changed_device_transform",lambda x:x[1]["devices"][0]["pcell"].update(transform="r0 *1 1083.605,298.03"))
    reject("changed_native_terminal_geometry",lambda x:x[1]["devices"][0]["terminals"][0]["native_layers"][0].update(area_dbu2=1))
    reject("omitted_device",lambda x:x[1]["devices"].pop())
    reject("duplicated_device",lambda x:x[1]["devices"].__setitem__(1,copy.deepcopy(x[1]["devices"][0])))
    reject("omitted_terminal",lambda x:x[1]["devices"][0]["terminals"].pop())
    reject("shifted_actual_anchor",lambda x:x[2]["rows"][0]["point_dbu"].__setitem__(0,x[2]["rows"][0]["point_dbu"][0]+1))
    reject("omitted_actual_anchor",lambda x:x[2]["anchors"].pop())
    reject("changed_public_port_point",lambda x:next(a for a in x[2]["anchors"] if a["label"].startswith("P_"))["point_dbu"].__setitem__(0,1201))
    reject("changed_alias",lambda x:x[2]["logical_anchor_aliases"].update(T001_S="T001_G"))
    reject("changed_native_model_census",lambda x:x[0]["native_devices"].update(npn13G2=123))
    reject("changed_native_terminal_partition",lambda x:next(r for r in x[0]["native_net_coverage"] if r["device_terminals"])["device_terminals"][0].update(terminal="WRONG"))
    reject("changed_component_owner",lambda x:x[0]["wire_components"][0].update(native_cluster=x[0]["wire_components"][1]["native_cluster"]))
    reject("changed_lower_metal",lambda x:x[0]["layers"]["8"].update(area_dbu2=1))
    reject("boolean_device_identifier",lambda x:x[1]["devices"][0].update(native_id=True))
    reject("unmodified_source_is_not_added_material",lambda x:None,True)
    assert len(faults)==16
    return {"status":"PASS_FULL_SAVED_TOPOLOGY_SOURCE_CONTROLS_ONLY","positives":2,"refusals":16,
      "actual_original_JSON_hashes":HASHES,"identity_positive":baseline,
      "explicit_synthetic_identifier_renumber_positive":renamed,"faults":faults,
      "fresh_native_extraction_executed":False,"candidate_geometry_loaded":False,
      "physical_accepted":False,"electrical_accepted":False}

if __name__=="__main__":print(json.dumps(controls(),sort_keys=True))
