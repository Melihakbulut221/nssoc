#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual full restore/return seam with synthetic payloads on all current member paths."""
import copy,hashlib,json,os,tempfile,traceback
from pathlib import Path
from unittest import mock
import cdr_v59_tail_loaded_admission as a
from cloud_chunked_results import pack

def encoded(value):
    return (json.dumps(value,indent=2,sort_keys=True)+"\n").encode()

def fixture(root,actual,original_raw,mode):
    c=copy.deepcopy(actual);p=c["actual_fresh_RC"]
    repository=root/"repository";repository.mkdir()
    source=root/"fixture-current-fresh-rc";source.mkdir()
    payloads={name:("EXPLICIT_SYNTHETIC_MEMBER "+name+"\n").encode()for name in p["expected_files"]}
    report_paths={"result.json":"summary.json","mim/result.json":"MIM-precision-result.json",
      "binding/result.json":"binding-result.json","binding/binding.json":"binding.json",
      "mim/composition/composition.json":"composition.json"}
    for path,name in report_paths.items():payloads[path]=original_raw[name]
    payloads["mim/precise/model-binding/binding.json"]=original_raw["binding.json"]
    layout_path="mim/precise/source/parent/layout/result.json"
    payloads[layout_path]=encoded({"synthetic_layout_metadata":True})
    planes={"status":"PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS",
      "anchors":[{"logical_net":"synthetic_net_"+str(i%51)}for i in range(160)],
      "inputs":{"synthetic/layout/result.json":hashlib.sha256(payloads[layout_path]).hexdigest()}}
    for order in ("precise","precise_reversed"):
        payloads["mim/"+order+"/source/native-planes.json"]=encoded(planes)
    model_path="mim/composition/pd500-mim-wire.spice"
    payloads[model_path]=b"* SYNTHETIC RESTORE FIXTURE; NEVER A SIMULATOR INPUT\n"
    reserved=set(report_paths)|{layout_path,model_path,"mim/precise/model-binding/binding.json",
      "mim/precise/source/native-planes.json","mim/precise_reversed/source/native-planes.json"}
    unselected=next(name for name in sorted(payloads)if name not in reserved)
    if mode=="plane_qualification":
        changed=copy.deepcopy(planes);changed["anchors"].pop()
        payloads["mim/precise/source/native-planes.json"]=encoded(changed)
    if mode=="plane_layout_join":payloads[layout_path]=encoded({"synthetic_layout_metadata":"changed"})
    if mode=="binding_view":payloads["mim/precise/model-binding/binding.json"]=encoded({"synthetic_wrong_binding":True})
    if mode=="order_plane_identity":
        changed=copy.deepcopy(planes);changed["synthetic_changed_order"]=True
        payloads["mim/precise_reversed/source/native-planes.json"]=encoded(changed)
    if mode=="restored_report":payloads["mim/result.json"]=encoded({"synthetic_wrong_original_report":True})
    expected={name:hashlib.sha256(value).hexdigest()for name,value in payloads.items()}
    assert set(expected)==set(actual["actual_fresh_RC"]["expected_files"])and len(expected)==3823
    for name,value in payloads.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
    if mode=="unselected_hash":(source/unselected).write_bytes(b"CHANGED_UNSELECTED_MEMBER")
    if mode=="missing_member":(source/unselected).unlink()
    if mode=="extra_member":(source/"unapproved-extra").write_bytes(b"EXTRA")
    if mode=="symlink_member":
        (source/unselected).unlink();(source/unselected).symlink_to(source/model_path)
    publication=root/"publication";publication.mkdir()
    manifest=pack(source,"synthetic-fresh-RC",publication,part_bytes=64*1024)
    raw=dict(original_raw);raw["parts.json"]=encoded(manifest)
    p["expected_files"]=expected;p["complete_archive"]=manifest
    assets=[];asset_bytes={};serial=0
    for name,value in raw.items():
        spec=p["snapshots"][name];target=repository/spec["path"]
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(value)
        spec.update(bytes=len(value),sha256=hashlib.sha256(value).hexdigest())
        asset_name="synthetic-fresh-RC."+name
        row={"id":900000+serial,"name":asset_name,"size":len(value),"digest":"sha256:"+hashlib.sha256(value).hexdigest(),"state":"uploaded"}
        assets.append(row);asset_bytes["fixture://"+str(row["id"])]=value;serial+=1
    for part in manifest["parts"]:
        value=(publication/part["name"]).read_bytes()
        row={"id":900000+serial,"name":part["name"],"size":len(value),"digest":"sha256:"+hashlib.sha256(value).hexdigest(),"state":"uploaded"}
        assets.append(row);asset_bytes["fixture://"+str(row["id"])]=value;serial+=1
    p["assets"]=assets
    run=copy.deepcopy(p["run"]);jobs={"total_count":len(p["jobs"]),"jobs":copy.deepcopy(p["jobs"])}
    info=copy.deepcopy(p["release"])
    info["assets"]=[dict(row,browser_download_url="fixture://"+str(row["id"]))for row in assets]
    ref={"ref":"refs/tags/"+info["tag_name"],"object":{"type":"commit","sha":run["head_sha"]}}
    responses={"actions/runs/"+str(run["id"]):run,
      "actions/runs/"+str(run["id"])+"/attempts/1/jobs?per_page=100":jobs,
      "releases/tags/"+info["tag_name"]:info,"git/ref/tags/"+info["tag_name"]:ref}
    return c,{name:json.loads(value)for name,value in raw.items()},repository,responses,asset_bytes,unselected,planes

def one_case(mode,actual,original_raw,enabled):
    with tempfile.TemporaryDirectory()as folder:
        root=Path(folder)
        c,s,repository,responses,asset_bytes,unselected,planes=fixture(root,actual,original_raw,mode)
        out=root/"out";out.mkdir();calls=[];downloads=[]
        def api(path):
            calls.append(path);assert path in responses,path
            return copy.deepcopy(responses[path])
        def fetch(url,digest,target):
            assert url in asset_bytes and target.name==next(x["name"]for x in c["actual_fresh_RC"]["assets"]if "fixture://"+str(x["id"])==url)
            value=asset_bytes[url];assert hashlib.sha256(value).hexdigest()==digest
            target.write_bytes(value);downloads.append(url)
        env={"GITHUB_ACTIONS":"true","RUNNER_ENVIRONMENT":"github-hosted","GITHUB_REPOSITORY":"Melihakbulut221/nssoc","GITHUB_RUN_ATTEMPT":"1"}
        error=None;returned=None
        with mock.patch.object(a,"ROOT",repository),mock.patch.object(a,"methods",return_value=enabled),\
             mock.patch.object(a,"descriptor",return_value=c),mock.patch.object(a,"snapshots",return_value=s),\
             mock.patch.object(a.release,"api",side_effect=api),mock.patch.object(a,"fetch",side_effect=fetch),\
             mock.patch.dict(os.environ,env):
            try:returned=a.restore(out,mode!="simulation_return")
            except BaseException as caught:error=caught
        assert len(calls)==4 and set(calls)==set(responses)
        assert len(downloads)==len(asset_bytes)and len(set(downloads))==len(downloads)
        expected_reasons={
          "unselected_hash":unselected,"missing_member":"Missing native member","extra_member":"Unexpected native member",
          "symlink_member":"Duplicate/nonregular native member","plane_qualification":"Current native plane qualification changed",
          "plane_layout_join":"Current planes/layout join changed","binding_view":"Current binding view changed",
          "order_plane_identity":"Order plane identity changed","restored_report":"Restored report bytes differ"}
        if mode in expected_reasons:
            assert type(error)is AssertionError and error.args==(expected_reasons[mode],),(mode,error)
            frames=[];tb=error.__traceback__
            while tb is not None:
                frames.append({"function":tb.tb_frame.f_code.co_name,"source":tb.tb_frame.f_code.co_filename,"line":tb.tb_lineno})
                tb=tb.tb_next
            expected_function="exact_extract"if mode in ("unselected_hash","missing_member","extra_member","symlink_member")else"restore"
            expected_source=a.saved.__file__ if expected_function=="exact_extract"else a.__file__
            assert any(x["function"]==expected_function and x["source"]==expected_source for x in frames),(mode,frames)
            return {"mode":mode,"reason":expected_reasons[mode],"actual_rejection_frames":frames,
              "all_transport_assets_acquired_before_extraction":True}
        assert error is None and type(returned)is tuple and len(returned)==6,(mode,error)
        report,proof,model,contract,actual_planes,plane_proof=returned
        assert report==s["MIM-precision-result.json"]and contract==s["composition.json"]and actual_planes==planes
        assert model==out/"current-mim-bundle/mim/composition/pd500-mim-wire.spice"
        assert model.read_bytes()==b"* SYNTHETIC RESTORE FIXTURE; NEVER A SIMULATOR INPUT\n"
        assert proof["full_archive"]["regular_members"]==3823 and proof["full_archive"]["full_inventory_verified"]is True
        assert set(proof["full_archive"]["complete_member_hashes"])==set(c["actual_fresh_RC"]["expected_files"])
        assert proof["original_physical_run"]==40369539200 and proof["original_physical_status"]=="FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL"
        assert proof["original_eight_electrical_rejections_and_two_fault_detections_preserved"]is True
        assert all(proof[k]is False for k in ("geometry_regenerated","extraction_rerun","simulation_preaccepted"))
        assert plane_proof["native_planes_sha256"]==a.sha(out/"current-mim-bundle/mim/precise/source/native-planes.json")
        assert plane_proof["native_binding_sha256"]==a.sha(out/"current-mim-bundle/binding/binding.json")
        assert plane_proof["fresh_layout_sha256"]==a.sha(out/"current-mim-bundle/mim/precise/source/parent/layout/result.json")
        assert a.verify_exact_files(out/"current-mim-bundle",c["actual_fresh_RC"]["expected_files"])["files"]==3823
        return {"mode":mode,"six_value_return_checked":True,"all3823_actual_member_names":True,
          "complete_regular_hash_inventory":True,"transport_assets":len(downloads),"explicit_synthetic_archive_payloads":True}

def controls():
    m=a.methods();assert m["source_controls_authorized"]is True
    actual=a.descriptor();a.snapshots()
    original_raw={name:a.regular(a.ROOT,spec["path"]).read_bytes()for name,spec in actual["actual_fresh_RC"]["snapshots"].items()}
    enabled=copy.deepcopy(m)
    for name in a.AUTH+("controller_readiness",):enabled[name]=True
    a.validate_authorizations(enabled)
    modes=("preparation_return","simulation_return","unselected_hash","missing_member","extra_member","symlink_member",
      "plane_qualification","plane_layout_join","binding_view","order_plane_identity","restored_report")
    rows=[one_case(mode,actual,original_raw,enabled)for mode in modes]
    assert len(rows)==11
    return {"status":"PASS_ACTUAL_LOADED_RESTORE_RETURN_AND_FULL_MEMBER_BOUNDARIES",
      "positive":rows[:2],"rejected":rows[2:],"actual_restore_exact_extract_pack_and_authorize_called":True,
      "real_current_reports_validated_before_synthetic_archive_cases":True,
      "explicit_fixture_boundary":"Synthetic payloads use every actual current member path; report admission is separately run on authentic saved JSON. Network/API/snapshot transport and enabled metadata are fixture collaborators.",
      "producer_archive_downloaded":False,"simulator_executed":False,"loaded_numerical_functions_executed":False}

def main():
    try:result=controls()
    except BaseException as error:
        result={"status":"FAIL_LOADED_RESTORE_RETURN_CONTROLS","error":repr(error),"traceback":traceback.format_exc()}
        print(json.dumps(result,indent=2,sort_keys=True));raise
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":main()
