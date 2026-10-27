#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted joint-admission and actual184-file copy controls; never native CAD."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import traceback
import cdr_v59_tail_fresh_rc_admission as gate

def controls():
    c=gate.contract()
    summary=gate.read_json(gate.ROOT/c["transport"]["summary"]["path"])
    physical=gate.read_json(gate.ROOT/c["retained_physical_gates"]["native_physical_report"]["path"])
    generation=gate.read_json(gate.ROOT/c["retained_physical_gates"]["generation_report"]["path"])
    planes=gate.read_json(gate.ROOT/c["retained_physical_gates"]["planes_report"]["path"])
    gate.validate_maps(c);gate.validate_saved_summary(summary,c);gate.validate_physical(physical)
    gate.validate_geometry_metadata(generation,planes)
    positives=["actual955_nested931_candidate184_maps","actual_saved_native_summary",
      "actual_full560_DRC_deep_flat500_and13_faults","actual11_geometry160_planes19_faults"]
    refused=[]
    def reject(name,call,message):
        try:call()
        except AssertionError as error:
            tb=error.__traceback__
            while tb.tb_next:tb=tb.tb_next
            assert error.args==(message,),(name,error.args,message)
            assert Path(tb.tb_frame.f_code.co_filename).resolve()==Path(gate.__file__).resolve()
            assert tb.tb_frame.f_code.co_name=="require"
            refused.append({"name":name,"error":repr(error),"line":tb.tb_lineno})
        else:raise AssertionError("Accepted "+name)
    def mutated(name,base,change,call,message):
        bad=copy.deepcopy(base);change(bad)
        assert json.dumps(base,sort_keys=True)!=json.dumps(bad,sort_keys=True),"No-op admission mutation"
        reject(name,lambda:call(bad),message)
    m=gate.methods()
    for enabled in (False,True):
        base=copy.deepcopy(m)
        for key in gate.NATIVE_FLAGS:base[key]=enabled
        base["controller_readiness"]=enabled
        base["source_controls_authorized"]=enabled
        gate.validate_authorizations(base)
        positives.append("actual_authorization_mode_"+str(enabled))
        if enabled:
            mutated("native_without_source_controls",base,lambda x:x.__setitem__("source_controls_authorized",False),
              gate.validate_authorizations,"Native fresh RC requires source-controls authorization")
        mutated("split_authorization_"+str(enabled),base,lambda x:x.__setitem__(gate.NATIVE_FLAGS[0],not enabled),
          gate.validate_authorizations,"Split fresh RC authorization")
        mutated("integer_authorization_"+str(enabled),base,lambda x:x.__setitem__(gate.NATIVE_FLAGS[0],int(enabled)),
          gate.validate_authorizations,"Non-boolean authorization")
        mutated("geometry_authorization_"+str(enabled),base,lambda x:x.__setitem__("geometry_generation_authorized",True),
          gate.validate_authorizations,"Unsupported engineering authorization")
        mutated("simulation_authorization_"+str(enabled),base,lambda x:x.__setitem__("simulation_authorized",True),
          gate.validate_authorizations,"Unsupported engineering authorization")
    mutated("outer_missing",c,lambda x:x["transport"]["expected_sha256"].pop("result.json"),gate.validate_maps,
      "Wrong complete archive/view census")
    inner_name=next(n for n in c["original_physical"]["expected_sha256"] if n!="result.json")
    mutated("nested_hash",c,lambda x:x["original_physical"]["expected_sha256"].__setitem__(inner_name,"0"*64),
      gate.validate_maps,"Complete nested original physical manifest changed")
    candidate_name=next(iter(c["canonical_candidate"]["expected_sha256"]))
    mutated("candidate_hash",c,lambda x:x["canonical_candidate"]["expected_sha256"].__setitem__(candidate_name,"0"*64),
      gate.validate_maps,"Complete current candidate view changed")
    def escape(x):
        value=x["transport"]["expected_sha256"].pop("result.json")
        x["transport"]["expected_sha256"]["../result.json"]=value
    mutated("outer_path_escape",c,escape,gate.validate_maps,"Unsafe relative path")
    mutated("canonical_root",c,lambda x:x["canonical_candidate"].__setitem__("root","hw/soc/out/old-candidate"),
      gate.validate_maps,"Qualified candidate root changed")
    mutated("anchor_absolute_path",c,lambda x:x["canonical_candidate"]["anchor_consumed_paths"][0].__setitem__(
      "original_absolute_path","/unqualified/source"),gate.validate_maps,"Anchor original absolute path changed")
    mutated("saved_run_identity",summary,lambda x:x.__setitem__("run_id",1),
      lambda x:gate.validate_saved_summary(x,c),"Wrong saved readback identity/status")
    mutated("failed_physical_relabelled",summary,lambda x:x.__setitem__("original_status","PASS"),
      lambda x:gate.validate_saved_summary(x,c),"Original physical failure relabelled")
    mutated("saved_extraction_claim",summary,lambda x:x.__setitem__("extraction_executed",True),
      lambda x:gate.validate_saved_summary(x,c),"Saved readback claimed unsupported work or acceptance")
    mutated("saved_live_child",summary,lambda x:x["commands"][0]["process_group_cleanup"].__setitem__("remaining_live",[123]),
      lambda x:gate.validate_saved_summary(x,c),"Saved native command did not terminate cleanly")
    mutated("truncated_DRC_categories",physical,lambda x:x["steps"]["drc"]["measurement"].__setitem__("category_count",559),
      gate.validate_physical,"Original full560-category DRC gate changed")
    mutated("nonzero_DRC",physical,lambda x:x["steps"]["drc"]["measurement"].__setitem__("markers",1),
      gate.validate_physical,"Original full560-category DRC gate changed")
    mutated("missing_flat_device",physical,lambda x:x["steps"]["lvs_flat"]["audit"]["circuits"][0].__setitem__("layout_devices_recursive",499),
      gate.validate_physical,"Original complete500 LVS census changed")
    mutated("accepted_physical_fault",physical,lambda x:x["steps"]["q_open"].__setitem__("status","PASS"),
      gate.validate_physical,"Original native physical fault not rejected")
    mutated("accepted_geometry_fault",generation,lambda x:x["native_geometry_controls"]["cases"][0].__setitem__("rejected",False),
      lambda x:gate.validate_geometry_metadata(x,planes),"Original native geometry controls changed")
    mutated("accepted_plane_fault",planes,lambda x:x["controls"][0].__setitem__("rejected",False),
      lambda x:gate.validate_geometry_metadata(generation,x),"Original native planes/faults changed")
    # Actual filesystem copy, using clearly synthetic bytes and the complete184
    # source path set. This neither downloads nor substitutes a native capsule.
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary);saved=root/"saved";saved.mkdir()
        spec=copy.deepcopy(c);mapping={}
        names=list(c["canonical_candidate"]["expected_sha256"])
        for i,name in enumerate(names):
            payload=b"" if i==0 else ("SYNTHETIC MEMBER "+name+"\n").encode()
            path=saved/c["canonical_candidate"]["member_prefix"]/name
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
            mapping[name]=hashlib.sha256(payload).hexdigest()
        spec["canonical_candidate"]["expected_sha256"]=mapping
        destination=root/"view"
        proof=gate.materialize_candidate(saved,spec,destination)
        assert proof["files"]==184 and proof["all_original_candidate_bytes_unchanged"]
        assert {p.relative_to(destination).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
          for p in destination.rglob("*") if p.is_file()}==mapping
        positives.append("actual_complete184_file_copy_synthetic_bytes_including_empty")
        reject("existing_candidate",lambda:gate.materialize_candidate(saved,spec,destination),"Canonical candidate already exists")
        path=saved/c["canonical_candidate"]["member_prefix"]/names[0]
        previous=path.read_bytes();path.write_bytes(previous+b"changed")
        reject("changed_candidate_source",lambda:gate.materialize_candidate(saved,spec,root/"bad-digest"),
          "Candidate source digest changed")
        path.write_bytes(previous);path.unlink()
        target=saved/c["canonical_candidate"]["member_prefix"]/names[1]
        path.symlink_to(target)
        reject("candidate_source_symlink",lambda:gate.materialize_candidate(saved,spec,root/"bad-link"),
          "Symlink in protected path")
        path.unlink();path.write_bytes(previous)
        (root/"parent-link").symlink_to(root,target_is_directory=True)
        reject("candidate_destination_symlink",lambda:gate.materialize_candidate(saved,spec,root/"parent-link/new-view"),
          "Symlink in candidate destination ancestry")
    assert len(positives)==7 and len(refused)==29,(len(positives),len(refused))
    return {"status":"PASS_JOINT_SAVED_RC_ADMISSION_SOURCE_CONTROLS","positives":positives,
      "refusals":refused,"native_archives_or_CAD_accessed":False,"electrical_accepted":False,
      "physical_accepted":False,"qualified_pex":False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True);args=parser.parse_args()
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);result={"status":"RUNNING"}
    try:result=controls()
    except BaseException as error:
        result={"status":"FAIL","error":repr(error),"traceback":traceback.format_exc()};raise
    finally:
        output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
        print(output.read_text(),end="")

if __name__=="__main__":main()
