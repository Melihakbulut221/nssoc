#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source controls only. Native geometry faults execute separately."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import cdr_v59_tail_access_plan as plan

ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/"scripts/cdr-v59-tail-access-wire-methods.json"

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def controls():
    assert os.environ.get("GITHUB_ACTIONS")=="true"
    method=json.loads(METHOD.read_text())
    assert method["source_controls_authorized"] is True
    for key in ("native_execution_authorized","geometry_generation_authorized","extraction_authorized","simulation_authorized"):
        assert type(method[key]) is bool
    for path,want in method["protected_sha256"].items():
        p=ROOT/path
        assert p.is_file() and not p.is_symlink() and digest(p)==want,("Changed protected source",path)
    h=json.loads((ROOT/"docs/evidence/cdr-v59-master-tail-source-routing-handoff-20261026.json").read_text())
    actual=plan.candidate_plan(h)
    assert actual["new_bus_dbu"]==[370000,174430,1041525,177630]
    assert actual["native_via_parameters"]==plan.PARAMETERS
    assert len(actual["local_taps"])==8 and len(actual["placements"])==2
    assert actual["placements"][0]["bus_dbu"]==[1363600,446430,2035125,449630]
    assert actual["placements"][1]["bus_dbu"]==[1363600,1635950,2035125,1639150]
    assert actual["devices_changed"]==0 and actual["old_routes_preserved"] is True
    assert all(actual[k] is False for k in ("reference_changed","physical_accepted","electrical_improvement_proven","simulation_authorized","native_execution_authorized"))
    cases=[]
    def reject(name,change):
        x=copy.deepcopy(h);change(x)
        try:plan.candidate_plan(x)
        except (AssertionError,KeyError) as e:cases.append({"case":name,"rejected":True,"error":repr(e)})
        else:raise AssertionError("Accepted source mapping fault: "+name)
    reject("wrong_original_GDS",lambda x:x.update(current_candidate_GDS_sha256="0"*64))
    reject("wrong_leaf_origin",lambda x:x.update(source_leaf_origin_translation_um=[0,-3.965]))
    reject("wrong_coordinate_frame",lambda x:x.update(route_coordinates_before_origin_translation=False))
    reject("reordered_routes",lambda x:x["actual_M_TE_routes"].reverse())
    reject("wrong_route_net",lambda x:x["actual_M_TE_routes"][0].update(net="S_TE"))
    reject("shifted_lane",lambda x:x["actual_M_TE_routes"][0].update(escape_lane_um=371.005))
    reject("shifted_escape_y",lambda x:x["actual_M_TE_routes"][0].update(escape_y_um=119.995))
    reject("changed_escape_width",lambda x:x["actual_M_TE_routes"][0].update(escape_width_um=.405))
    reject("wrong_pin_layer",lambda x:x["actual_M_TE_routes"][0].update(source_layer=1))
    reject("wrong_pin_via_columns",lambda x:x["actual_M_TE_routes"][0].update(pin_via_columns=3))
    reject("wrong_lane_via_columns",lambda x:x["actual_M_TE_routes"][0].update(lane_via_columns=4))
    reject("omitted_anchor",lambda x:x["native_terminal_rows"].pop())
    reject("duplicate_anchor",lambda x:x["native_terminal_rows"].__setitem__(0,copy.deepcopy(x["native_terminal_rows"][1])))
    reject("shifted_actual_anchor",lambda x:x["native_terminal_rows"][0].update(point_dbu=[1885246,406030]))
    reject("wrong_actual_native_cluster",lambda x:x["native_terminal_rows"][0].update(native_cluster=124))
    reject("wrong_actual_wire_component",lambda x:x["native_terminal_rows"][0].update(wire_component=61))
    reject("changed_device_model",lambda x:x["native_terminal_rows"][0].update(model="rppd"))
    reject("wrong_parent_translation",lambda x:x["target_native_nodes"]["D"].update(parent_translation_um=[993.605,272]))
    reject("wrong_parent_tag",lambda x:x["target_native_nodes"]["D"].update(parent="sc"))
    assert len(cases)==19
    runtime=json.loads((ROOT/"docs/evidence/cdr-v59-tail-native-runtime-source-20261026.json").read_text())
    assert len(runtime["relative_runtime_sha256"])==88
    assert runtime["relative_runtime_sha256"]["sg13g2_pycell_lib/ihp/via_stack_code.py"]=="185f6d3bea6ef9a4960817d189e099057242e1cca73f6ab31c08298c2d64cc61"
    assert runtime["relative_runtime_sha256"]["sg13g2_pycell_lib/sg13g2_tech.json"]=="dce023dcf8dca1a7d875b6f71b5ce651b42f2dc3e9a21abb6de3997262273142"
    summary=json.loads((ROOT/"docs/evidence/cdr-v59-tail-current-font-physical-summary-20261026.json").read_text())
    selected={k[len("analysis-capsule/"):]:v for k,v in summary["outputs"].items() if k.startswith("analysis-capsule/")}
    assert len(summary["outputs"])==705 and len(selected)==349
    assert selected["parent/layout/"+plan.TOP+".gds"]==h["current_candidate_GDS_sha256"]
    # Run the actual import statement in an isolated fresh interpreter. No pya,
    # geometry input or hosted engine is imported by the native module at import.
    with tempfile.TemporaryDirectory(prefix="cdr-tail-import-") as tmp:
        root=Path(tmp)
        for name in ("cdr_v59_tail_access_plan.py","generate_cdr_v59_tail_access_wire.py"):
            b=(ROOT/"scripts"/name).read_bytes()
            (root/name).write_bytes(b)
            assert digest(root/name)==hashlib.sha256(b).hexdigest()
        code="import sys;sys.path.insert(0,sys.argv[1]);import generate_cdr_v59_tail_access_wire;print('TAIL_NATIVE_SOURCE_IMPORT_ONLY')"
        good=subprocess.run([sys.executable,"-I","-B","-c",code,str(root)],capture_output=True,text=True,timeout=30)
        assert good.returncode==0 and good.stdout=="TAIL_NATIVE_SOURCE_IMPORT_ONLY\n" and good.stderr=="",vars(good)
        (root/"cdr_v59_tail_access_plan.py").unlink()
        bad=subprocess.run([sys.executable,"-I","-B","-c",code,str(root)],capture_output=True,text=True,timeout=30)
        assert bad.returncode==1 and bad.stdout==""
        assert bad.stderr.splitlines()[-1]=="ModuleNotFoundError: No module named 'cdr_v59_tail_access_plan'"
    return {"status":"PASS_TAIL_ACCESS_SOURCE_CONTROLS_ONLY","metadata_positive":1,
      "metadata_faults_rejected":19,"actual_import_positive":1,"actual_missing_dependency_rejected":1,
      "protected_files_verified":len(method["protected_sha256"]),"cases":cases,
      "native_geometry_controls_executed":False,"physical_accepted":False,"electrical_accepted":False}

def main():
    print(json.dumps(controls(),sort_keys=True))
if __name__=="__main__":main()
