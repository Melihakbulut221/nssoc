#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One reviewed additive tail-wire physical qualification; no RC or simulation."""
import argparse
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import tarfile
import threading
import traceback

import cdr_v59_binding_rc_source as source
import cdr_v59_tail_access_runtime as runtime
import cdr_v59_tail_access_topology as topology
import cdr_v59_tail_access_plan as plan
import cloud_cdr_v59_binding_rc as publication
import cloud_cdr500_resistor_v59_physical as frozen
import ensure_cloud_tested_source_release as release
import migrate_outputs_to_cloud as publisher
from run_cloud_tx_layout_repair import fetch,sha

ROOT=source.ROOT
METHOD=ROOT/"scripts/cdr-v59-tail-access-wire-methods.json"
GROUP="cdr-v59-tail-access-physical"
OUT=ROOT/"hw/soc/out/cloud-cdr-v59-tail-access-physical"
WORK=OUT/"candidate"
TRANSPORT=ROOT/"hw/soc/out/cloud-cdr-v59-tail-access-physical-publication"
APP_SHA="d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"
WIRE=("probe01.py","locate01.py","anchors01.py","dedup01.py")
WIRE_SOURCE=ROOT/"docs/evidence/cdr-v59-tail-exact-wire-methods-20261026"
PHASE_SECONDS={"restore-complete-original-capsule":1200,"restore-frozen-pdk-runtime":1200,
 "native-additive-generation":1800,"full-physical-and13-faults":7200,
 "fresh-native-planes":1200,"source-annotation-recovery":1200,
 "probe01.py":1200,"locate01.py":1200,"anchors01.py":1200,"dedup01.py":1200}
PASS="PASS_ADDITIVE_TAIL_WIRE_FULL_PHYSICAL_TOPOLOGY_REQUIRES_FRESH_BINDING_RC_MIM_AND_ELECTRICAL_REVIEW"

def write(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")

def methods():
    assert ROOT==source.CANONICAL_ROOT
    m=json.loads(METHOD.read_text())
    assert m["schema"]=="cdr-v59-tail-access-wire-methods-v1"
    for name,h in m["protected_sha256"].items():
        p=ROOT/name;assert p.is_file() and not p.is_symlink() and sha(p)==h,name
    assert m["accepted"] is m["qualified_pex"] is m["full_phy_accepted"] is False
    assert m["simulation_authorized"] is m["extraction_authorized"] is False
    return m

def authorize():
    m=methods()
    assert os.environ.get("GITHUB_ACTIONS")=="true"
    assert os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    assert os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"
    assert os.environ.get("GITHUB_RUN_ATTEMPT")=="1"
    for key in ("native_execution_authorized","geometry_generation_authorized","physical_qualification_authorized"):
        assert m[key] is True
    return m

def storage(phase):
    total=0
    if phase=="publication" and OUT.exists():
        for p in OUT.rglob("*"):
            assert not p.is_symlink() and (p.is_dir() or p.is_file())
            if p.is_file():total+=p.stat().st_size
    needed=max(4*1024**3,total+1024**3) if phase=="publication" else 8*1024**3 if phase=="initial" else 4*1024**3
    free=shutil.disk_usage(ROOT).free
    assert free>=needed,("Insufficient evidence/working space",phase,free,needed)
    return {"phase":phase,"free_bytes":free,"required_bytes":needed,"evidence_bytes":total}

def restore_worker():
    authorize()
    assert OUT.is_dir() and not source.CAPSULE.exists()
    pin=json.loads(source.PIN.read_text())
    proof=source.restore_saved(pin,OUT)
    assert source.verify_saved_inputs(pin)=={"files":706,"all_hashes_unchanged":True}
    write(OUT/"source-restoration.json",proof)
    methods()

def runtime_worker():
    authorize()
    spec=json.loads((ROOT/"docs/evidence/pcie-tx-layout-cloud-input-20261013.json").read_text())
    packed=OUT/"frozen-runtime.tar.gz"
    fetch(spec["receipt"]["url"],spec["receipt"]["sha256"],packed)
    assert packed.stat().st_size==spec["receipt"]["bytes"]
    with tarfile.open(packed) as tar:tar.extractall(ROOT,filter="data")
    packed.unlink()
    manifest=json.loads((ROOT/"manifest.json").read_text())
    assert all(sha(ROOT/n)==v["sha256"] for n,v in manifest["files"].items())
    methods()
    write(OUT/"runtime-source-manifest.json",manifest)

def derive_methods():
    dest=WORK/"methods";dest.mkdir(exist_ok=False)
    records={}
    original="hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py"
    text,changes=frozen.physical_source((ROOT/original).read_text(),"cd_shunt")
    assert len(changes)==4
    (dest/"check_physical.py").write_text(text)
    records["check_physical.py"]={"original":original,"original_sha256":sha(ROOT/original),
      "generated_sha256":sha(dest/"check_physical.py"),"exact_qualified_reversible_changes":changes}
    items={
     "cdr_tail_geometry.py":("scripts/check_cdr_sampler_active_input_v57_parent_geometry.py",[("nssoc_cdr_pd500_active_input_v57",plan.TOP)]),
     "cdr_tail_planes.py":("scripts/cloud_cdr_sampler_active_input_v57_planes.py",[("nssoc_cdr_pd500_active_input_v57",plan.TOP),
         ("from check_cdr_sampler_active_input_v57_parent_geometry import check","from cdr_tail_geometry import check")]),
     "cdr_tail_recover.py":("scripts/cloud_cdr_sampler_active_input_v57_wire_inputs.py",[("nssoc_cdr_pd500_active_input_v57",plan.TOP)]),
    }
    for name,(original,edits) in items.items():
        text,changes=frozen.derive((ROOT/original).read_text(),edits)
        (dest/name).write_text(text)
        records[name]={"original":original,"original_sha256":sha(ROOT/original),
          "generated_sha256":sha(dest/name),"exact_qualified_reversible_changes":changes}
    write(OUT/"derived-methods.json",records)
    return records

def native_worker(which):
    authorize()
    assert which in ("planes","recover")
    path=WORK/"methods"/("cdr_tail_"+which+".py")
    recorded=json.loads((OUT/"derived-methods.json").read_text())
    for name,row in recorded.items():assert sha(WORK/"methods"/name)==row["generated_sha256"]
    sys.dont_write_bytecode=True;sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location("cdr_tail_"+which,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.OUT=WORK;module.ROOT=ROOT
    getattr(module,"native" if which=="planes" else "recover")()
    for name,row in recorded.items():assert sha(WORK/"methods"/name)==row["generated_sha256"]

def validate_physical(report):
    assert report["status"]=="PASS_NATIVE_PDK_CDR_PD500_DRC_LVS_AND_FAULT_CONTROLS"
    steps=report["steps"];assert len(steps)==16
    drc=steps["drc"]["measurement"]
    assert drc["category_count"]==560 and drc["markers"]==0 and drc["status"]=="PASS"
    assert steps["v59_old_length"]["status"]=="REJECTED_EXPECTED_FAULT"
    assert all(v["status"]=="REJECTED_EXPECTED_FAULT" for n,v in steps.items() if n not in ("drc","lvs","lvs_flat"))
    for mode in ("lvs","lvs_flat"):
        audit=steps[mode]["audit"]
        assert audit["status"]=="PASS within comparison scope"
        assert audit["circuit_status_counts"]=={"Match":1} and not audit["extraction_diagnostics"]
        assert len(audit["circuits"])==1
        assert audit["circuits"][0]["layout_devices_recursive"]==audit["circuits"][0]["schematic_devices_recursive"]==500
    return True

def wire_inputs(old,new):
    """Every report must point at and hash this fresh stage, never the old capsule."""
    mapped={}
    for name in old["inputs"]:
        path=Path(name);rel=path.relative_to(source.ANALYSIS)
        assert ".." not in rel.parts
        mapped[str(WORK/rel)]=rel
    assert set(mapped)==set(new["inputs"])
    for name,rel in mapped.items():
        path=WORK/rel;assert path.is_file() and not path.is_symlink()
        value=new["inputs"][name]
        if isinstance(value,dict):
            assert value=={"bytes":path.stat().st_size,"sha256":sha(path)}
        else:assert value==sha(path)
    return {n:sha(WORK/p) for n,p in mapped.items()}

@contextlib.contextmanager
def native_environment():
    keys=("GH_TOKEN","GITHUB_TOKEN")
    previous={key:os.environ.get(key) for key in keys}
    try:
        for key in keys:os.environ.pop(key,None)
        yield
    finally:
        for key,value in previous.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value

def execute(supervisor,result,argv,label,tokenless=False):
    assert label in PHASE_SECONDS,"Unknown physical command label"
    result["storage"].append(storage(label));write(OUT/"result.json",result)
    with native_environment() if tokenless else contextlib.nullcontext():
        supervisor.supervised(argv,label,seconds=PHASE_SECONDS[label],cwd=ROOT)
    record=json.loads((supervisor.TRACE/(label+".command.json")).read_text())
    assert record["returncode"]==0 and record["supervision_failure"] is None
    assert not record["process_group_cleanup"]["remaining_live"]
    for stream in ("stdout","stderr"):
        path=supervisor.TRACE/(label+"."+stream)
        assert path.stat().st_size==record[stream+"_bytes"] and sha(path)==record[stream+"_sha256"]
    result["commands"].append(record);write(OUT/"result.json",result)
    return record

def qualify(result,supervisor,m):
    execute(supervisor,result,[sys.executable,__file__,"--worker","restore"],"restore-complete-original-capsule")
    result["source_restoration"]=json.loads((OUT/"source-restoration.json").read_text())
    execute(supervisor,result,[sys.executable,__file__,"--worker","runtime"],"restore-frozen-pdk-runtime")
    app=Path(os.environ["CLOUD_APPIMAGE"]).resolve();assert app.is_file() and sha(app)==APP_SHA
    launcher=runtime.launcher(ROOT,methods,m["protected_sha256"][runtime.PROBE])
    with native_environment():smoke=launcher.probe(app,APP_SHA,OUT/"runtime-smoke")
    result["runtime_smoke"]=smoke;write(OUT/"result.json",result)
    assert smoke["accepted"] is True
    execute(supervisor,result,[app,"python",ROOT/"scripts/generate_cdr_v59_tail_access_wire.py",
       "--source",source.ANALYSIS,"--out",WORK,"--pdk",ROOT/"pdk"],"native-additive-generation",True)
    generation=json.loads((WORK/"result.json").read_text())
    assert generation["status"]=="GENERATED_UNQUALIFIED_ADDITIVE_TAIL_ACCESS_WIRE"
    assert generation["original349_files_and88_runtime_sources_unchanged"] is True
    assert generation["serialized_full_parent_verified"] is generation["serialized_child_material_raw_and_hierarchy_verified"] is True
    controls=generation["native_geometry_controls"]
    assert controls["status"]=="PASS_ACTUAL_SERIALIZED_GEOMETRY_CONTROLS"
    assert controls["positive_before_each_fault"]==controls["faults_rejected"]==11
    assert len(controls["cases"])==11 and all(row["fresh_actual_baseline_passed"] is True and row["actual_geometry_mutated"] is True and row["rejected"] is True for row in controls["cases"])
    assert generation["physical_accepted"] is generation["electrical_accepted"] is False
    result["generation_result_sha256"]=sha(WORK/"result.json")
    adaptations=derive_methods()
    execute(supervisor,result,[sys.executable,WORK/"methods/check_physical.py","--layout",WORK/"parent/layout",
       "--out",WORK/"parent/physical","--app",app],"full-physical-and13-faults",True)
    physical=json.loads((WORK/"parent/physical/result.json").read_text());validate_physical(physical)
    result["physical_result_sha256"]=sha(WORK/"parent/physical/result.json")
    execute(supervisor,result,[app,"python",__file__,"--native","planes"],"fresh-native-planes",True)
    planes=json.loads((WORK/"native-planes.json").read_text())
    assert planes["status"]=="PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS"
    assert len(planes["controls"])==19 and len(planes["parent_geometry"]["controls"])==5
    wire=WORK/"wire";wire.mkdir(exist_ok=False)
    for name in WIRE:
        saved=source.ANALYSIS/"wire"/name
        assert sha(saved)==sha(WIRE_SOURCE/name)
        shutil.copyfile(saved,wire/name);assert sha(wire/name)==sha(saved)
    execute(supervisor,result,[app,"python",__file__,"--native","recover"],"source-annotation-recovery",True)
    for name in WIRE:execute(supervisor,result,[app,"python",wire/name],name,True)
    original=[];fresh=[];inputs={}
    for name in ("native05/result.json","device-locations01.json","anchors08.json"):
        old=json.loads((source.ANALYSIS/"wire"/name).read_text())
        new=json.loads((wire/name).read_text())
        inputs[name]=wire_inputs(old,new);original.append(old);fresh.append(new)
    comparison=topology.compare(original,fresh,True)
    write(OUT/"full-topology-comparison.json",comparison)
    result["fresh_report_inputs"]=inputs;result["topology"]=comparison
    for name in WIRE:assert sha(wire/name)==sha(WIRE_SOURCE/name)
    for name,row in adaptations.items():assert sha(WORK/"methods"/name)==row["generated_sha256"]
    for name in ("schematic.cir",plan.TOP+".lef"):assert sha(WORK/"parent/layout"/name)==sha(source.ANALYSIS/"parent/layout"/name)
    result["saved_capsule_integrity"]=source.verify_saved_inputs(json.loads(source.PIN.read_text()))
    manifest=json.loads((OUT/"runtime-source-manifest.json").read_text())
    assert all(sha(ROOT/n)==v["sha256"] for n,v in manifest["files"].items())
    methods()
    result.update(status=PASS,native_physical_qualification_passed=True)

def publish(result):
    assert OUT.is_dir() and not OUT.is_symlink() and not TRANSPORT.exists()
    storage("publication");TRANSPORT.mkdir()
    stem=GROUP+"-"+os.environ["GITHUB_RUN_ID"]+"-"+os.environ["GITHUB_RUN_ATTEMPT"]
    summary=TRANSPORT/(stem+".summary.json");shutil.copyfile(OUT/"result.json",summary)
    assert sha(summary)==sha(OUT/"result.json")
    packed=publication.pack(OUT,stem,TRANSPORT,512*1024**2)
    manifest=TRANSPORT/(stem+".parts.json")
    files=publication.publication_files(TRANSPORT,summary,manifest,packed)
    for name,path in [
        ("generation",WORK/"result.json"),("physical",WORK/"parent/physical/result.json"),
        ("planes",WORK/"native-planes.json"),("topology",OUT/"full-topology-comparison.json"),
        ("strict-wires",WORK/"wire/native05/result.json"),("locations",WORK/"wire/device-locations01.json"),
        ("anchors",WORK/"wire/anchors08.json")]:
        if path.exists():
            assert path.is_file() and not path.is_symlink()
            dest=TRANSPORT/(stem+"."+name+".json");shutil.copyfile(path,dest);assert sha(dest)==sha(path)
            files.append(dest)
    proof={"status":"RUNNING_PUBLICATION","summary_sha256":sha(summary),"assets":[]}
    write(TRANSPORT/"publication.json",proof)
    tag,_=release.context(GROUP,os.environ)
    previous=publisher.release
    publisher.release=publication.only_reserved(GROUP,os.environ,release.api)
    try:
        for path in files:
            proof["assets"].append(publisher.publish(path,tag));write(TRANSPORT/"publication.json",proof)
        proof["status"]="PASS_FULL_PHYSICAL_EVIDENCE_PUBLISHED"
    except BaseException as error:
        proof.update(status="FAIL_PUBLICATION",error=repr(error));raise
    finally:
        publisher.release=previous;write(TRANSPORT/"publication.json",proof)
    return proof

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--worker",choices=("restore","runtime"))
    parser.add_argument("--native",choices=("planes","recover"))
    parser.add_argument("--preflight",action="store_true")
    args=parser.parse_args();m=authorize()
    assert sum((args.worker is not None,args.native is not None,args.preflight))<=1
    if args.worker:
        (restore_worker if args.worker=="restore" else runtime_worker)();return
    if args.native:native_worker(args.native);return
    reservation=frozen.precreated(GROUP,wait=True)
    if args.preflight:print(json.dumps(reservation,sort_keys=True));return
    initial=storage("initial")
    assert not OUT.exists() and not TRANSPORT.exists() and not source.CAPSULE.exists()
    OUT.mkdir(parents=True)
    supervisor=runtime.supervisor(ROOT,OUT,OUT/"supervision",methods,m["protected_sha256"][runtime.SAMPLER])
    supervisor.TRACE.mkdir()
    result={"status":"RUNNING_ADDITIVE_TAIL_WIRE_PHYSICAL","source_head":os.environ["GITHUB_SHA"],
      "run_id":int(os.environ["GITHUB_RUN_ID"]),"run_attempt":1,"reservation":reservation,
      "commands":[],"storage":[initial],"native_physical_qualification_passed":False,
      "automatic_retry":False,"accepted":False,"electrical_accepted":False,"qualified_pex":False,
      "full_phy_accepted":False,"wire_rc_extracted":False,"simulation_executed":False,
      "original_ten_electrical_cases_remain_required":True}
    write(OUT/"result.json",result)
    previous={sig:signal.signal(sig,supervisor.interrupted) for sig in (signal.SIGINT,signal.SIGTERM)}
    heartbeat=threading.Thread(target=supervisor.heartbeat,daemon=True);heartbeat.start()
    try:qualify(result,supervisor,m)
    except BaseException as error:
        result.update(status="FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL",error=repr(error),traceback=traceback.format_exc(),native_physical_qualification_passed=False)
    finally:
        try:result["terminal_cleanup"]=supervisor.stop_process(supervisor.ACTIVE)
        except BaseException as error:result.update(status="FAIL_TERMINAL_PROCESS_CLEANUP",cleanup_error=repr(error),native_physical_qualification_passed=False)
        supervisor.STOP.set();heartbeat.join(timeout=5)
        for sig,handler in previous.items():signal.signal(sig,handler)
        if source.CAPSULE.exists():
            try:result["saved_capsule_integrity"]=source.verify_saved_inputs(json.loads(source.PIN.read_text()))
            except BaseException as error:result.update(status="FAIL_ORIGINAL_CAPSULE_INTEGRITY",integrity_error=repr(error),native_physical_qualification_passed=False)
            try:result["complete_or_partial_original_capsule_copy"]=publication.copy_tree(source.CAPSULE,OUT/"source-capsule")
            except BaseException as error:result.update(status="FAIL_ORIGINAL_EVIDENCE_COPY",copy_error=repr(error),native_physical_qualification_passed=False)
        result["outputs"]={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob("*") if p.is_file() and p!=OUT/"result.json"}
        write(OUT/"result.json",result)
    full=OUT/"result.json"
    if full.stat().st_size<=4*1024**2:publication.emit(full,"CDR_TAIL_PHYSICAL_RESULT")
    else:print("CDR_TAIL_FULL_RESULT_SAVED "+json.dumps({"bytes":full.stat().st_size,"sha256":sha(full),"full_release_summary_required":True}),flush=True)
    publish(result)
    assert result["native_physical_qualification_passed"] is True,result["status"]

if __name__=="__main__":main()
