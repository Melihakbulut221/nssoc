#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source controls on the complete actual acquired JSON pair; no CAD."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import traceback
import cdr_v59_tail_fresh_rc_semantic as gate

ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/"scripts/cdr-v59-tail-fresh-rc-methods.json"
PREFIX="docs/evidence/cdr-v59-tail-typed-serialization-readback-terminal-20261027"
PAIR={"old":(PREFIX+"-original-identity.json","846a805862b16e4312c163acb80b5351928823f42155a4eb9834444f19982e83"),
      "new":(PREFIX+"-current-identity.json","13a0fc6b0fd2d3ea5afc2ad8328e12eed64d87c7d40fc6ee4d080cc6e8702d37")}

def inputs():
    method=json.loads(METHOD.read_bytes())
    pair={}
    for side,(name,expected) in PAIR.items():
        path=ROOT/name
        assert path.is_file() and not path.is_symlink()
        raw=path.read_bytes()
        assert method["protected_sha256"][name]==hashlib.sha256(raw).hexdigest()==expected
        pair[side]=json.loads(raw)
    gate.source_guard()
    return pair["old"],pair["new"]

def controls():
    old,new=inputs();before=(gate.digest(old),gate.digest(new))
    result=gate.compare_pair(old,new)
    assert result["status"]=="PASS_WITNESS_BOUND_TOPOLOGY_PROJECTION_ALL_ORIGINAL_LATE_GATES"
    assert result["original_rejection"]["line"]==107
    assert len(result["deltas"]["old"])==500 and len(result["deltas"]["new"])==502
    assert len(result["unchanged_comparator_result"]["changed_owned_component_layers"])==4
    assert before==(gate.digest(old),gate.digest(new))
    projected=gate.project_pair(old,new)
    restored=copy.deepcopy(projected["views"])
    for side,rows in projected["deltas"].items():
        for row in rows:
            parent=restored[side]
            for part in row["path"][:-1]:parent=parent[part]
            assert parent[row["path"][-1]]==row["after"]
            parent[row["path"][-1]]=copy.deepcopy(row["before"])
        assert restored[side]=={k:{"old":old,"new":new}[side][k] for k in gate.FIELDS}
    positives=["complete_actual_pair_all_late_gates","exact_original_line107_reproduced",
      "complete1002_field_projection_reversed_and_originals_unchanged"]
    refused=[]
    def reject(name,call,expected,frame):
        try:call()
        except AssertionError as error:
            tb=error.__traceback__
            while tb.tb_next:tb=tb.tb_next
            assert error.args==expected,(name,error.args,expected)
            assert tb.tb_frame.f_code.co_name==frame,(name,tb.tb_frame.f_code.co_name,frame)
            refused.append({"name":name,"error":repr(error),"frame":frame,"line":tb.tb_lineno})
        else:raise AssertionError("Accepted "+name)
    def witness_mutation(name,change,message):
        altered=copy.deepcopy(new);change(altered)
        assert gate.canonical(altered)!=gate.canonical(new),"No-op witness mutation"
        reject(name,lambda:gate.compare_pair(old,altered),(message,),"require")
    witness_mutation("wrong_device_census",lambda x:x.__setitem__("native_device_count",499),"Wrong witness device census")
    witness_mutation("wrong_terminal_census",lambda x:x.__setitem__("native_terminal_count",1445),"Wrong witness terminal census")
    witness_mutation("missing_stable_path",lambda x:x["paths"].pop(),"Missing stable identity")
    witness_mutation("stable_path_change",lambda x:x["paths"][0]["stable_path"]["levels"][0].__setitem__("unexpected_property",1),"Stable instance path changed")
    witness_mutation("wrong_acquired_device",lambda x:x["paths"][0].__setitem__("native_device",501),"Device identity changed")
    witness_mutation("malformed_raw_path",lambda x:x["paths"][0].__setitem__("raw_path","not-a-native-path"),"Wrong root or empty instance path")
    witness_mutation("wrong_public_partition",lambda x:x["native_pins"][0]["full_partition"].__setitem__("unexpected",1),"Public name/terminal partition changed")
    witness_mutation("wrong_public_anchor",lambda x:x["native_pins"][0]["full_anchor"].__setitem__("unexpected",1),"Public name/anchor binding changed")
    witness_mutation("duplicate_public_name",lambda x:x["native_pins"][1].__setitem__("name",x["native_pins"][0]["name"]),"Duplicate/missing public identity")
    witness_mutation("duplicate_native_pin_ID",lambda x:x["native_pins"][1].__setitem__("native_pin_id",x["native_pins"][0]["native_pin_id"]),"Acquired pin IDs are not unique25")
    witness_mutation("wrong_pin_iteration_index",lambda x:x["native_pins"][0].__setitem__("iteration_index",1),"Acquired pin iteration indices changed")
    # Mutations below operate on fully acquired/proven projection copies and call the
    # actual unchanged comparator; no file/hash rejection can satisfy these controls.
    views=projected["views"]
    old_index=gate.topology.graph_index(views["old"]["graph"])
    target_keys={old_index["nets"][old_index["terminals"][(d,"npn13G2","E")]]["key"] for d in (61,115)}
    target=next(r["component"] for r in views["new"]["graph"]["wire_components"]
      if gate.topology.graph_index(views["new"]["graph"])["component_keys"][r["component"]] in target_keys)
    foreign=next(r["component"] for r in views["new"]["graph"]["wire_components"]
      if gate.topology.graph_index(views["new"]["graph"])["component_keys"][r["component"]] not in target_keys)
    def row(view,component):return next(r for r in view["graph"]["wire_components"] if r["component"]==component)
    def late(name,change,expected):
        changed=copy.deepcopy(views["new"]);change(changed)
        assert gate.canonical(changed)!=gate.canonical(views["new"]),"No-op late-gate mutation"
        reject(name,lambda:gate.topology.compare([views["old"][k] for k in gate.FIELDS],
          [changed[k] for k in gate.FIELDS],True),expected,"compare")
    foreign_layer=next(iter(row(views["new"],foreign)["layers"]))
    late("foreign_component_area",lambda x:row(x,foreign)["layers"][foreign_layer].__setitem__("area_dbu2",
      row(x,foreign)["layers"][foreign_layer]["area_dbu2"]+1),("Foreign or lower-metal component changed",))
    lower=next(k for k in row(views["new"],target)["layers"] if k not in ("126","134"))
    late("target_lower_metal",lambda x:row(x,target)["layers"][lower].__setitem__("area_dbu2",
      row(x,target)["layers"][lower]["area_dbu2"]+1),("Foreign or lower-metal component changed",))
    old_target=next(r for r in views["old"]["graph"]["wire_components"]
      if old_index["component_keys"][r["component"]]==gate.topology.graph_index(views["new"]["graph"])["component_keys"][target])
    late("missing_target_TM2_growth",lambda x:row(x,target)["layers"].__setitem__("134",copy.deepcopy(old_target["layers"]["134"])),
      ("No added owned TM2 bus",))
    late("target_TM1_shrink",lambda x:row(x,target)["layers"]["126"].__setitem__("area_dbu2",old_target["layers"]["126"]["area_dbu2"]-1),())
    late("target_component_layer_set",lambda x:row(x,target)["layers"].__setitem__("unapproved",{"area_dbu2":1}),())
    global_foreign=next(k for k in views["new"]["graph"]["layers"] if k not in ("126","133","134"))
    late("global_foreign_layer",lambda x:x["graph"]["layers"][global_foreign].__setitem__("area_dbu2",
      x["graph"]["layers"][global_foreign]["area_dbu2"]+1),(("Unapproved layer changed",global_foreign),))
    late("global_via_growth_missing",lambda x:x["graph"]["layers"].__setitem__("133",copy.deepcopy(views["old"]["graph"]["layers"]["133"])),())
    late("global_TM2_growth_missing",lambda x:x["graph"]["layers"].__setitem__("134",copy.deepcopy(views["old"]["graph"]["layers"]["134"])),())
    late("global_TM1_shrink",lambda x:x["graph"]["layers"]["126"].__setitem__("area_dbu2",views["old"]["graph"]["layers"]["126"]["area_dbu2"]-1),())
    late("global_layer_set",lambda x:x["graph"]["layers"].__setitem__("unapproved",{"area_dbu2":1}),())
    assert len(positives)==3 and len(refused)==21
    assert before==(gate.digest(old),gate.digest(new))
    return {"status":"PASS_COMPLETE_ACTUAL_PAIR_SEMANTIC_PROJECTION_SOURCE_CONTROLS",
      "positives":positives,"refusals":refused,"projection":result,
      "all_source_inputs_unchanged":True,"CAD_or_extraction_executed":False,
      "physical_accepted":False,"electrical_accepted":False,"qualified_pex":False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True);args=parser.parse_args()
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    result={"status":"RUNNING"}
    try:result=controls()
    except BaseException as error:
        result={"status":"FAIL","error":repr(error),"traceback":traceback.format_exc()}
        raise
    finally:
        out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
        print(out.read_text(),end="")

if __name__=="__main__":main()
