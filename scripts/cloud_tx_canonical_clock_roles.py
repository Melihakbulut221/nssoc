#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One exact existing native database proof; no extraction or simulation."""
import argparse,copy,hashlib,json,os,subprocess,traceback
from pathlib import Path
import cloud_tx_native_clock_role_p4_parameters as parent
import bind_tx_output8088_canonical_clock_roles as roles
prior=parent.prior
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"hw/soc/out/cloud-tx-canonical-clock-roles"
WORK=ROOT/"hw/soc/out/cloud-tx-canonical-clock-roles-restored"
METHOD=ROOT/"scripts/tx-canonical-clock-roles-methods.json"
PREVIOUS_RUN=40119049907
PREVIOUS_SOURCE="18e3fa347adc688482ff158aa797aed35ea3d364"
PREVIOUS_JOB=120946523543
PREVIOUS_LOG="a707b8d99edb6a24e0bd59866538ffda9548a5b92a1179976b0295b6526858ce"
PREVIOUS_RESULT="docs/evidence/tx-native-clock-role-p4-parameters-full-result-20261024.json"
PREVIOUS_SHA="55306fa1acd6e22dd0c81af17b8de3bf55c4013a06f12a4fa8cbffba25f8b3c3"
def pins():
    m=json.loads(METHOD.read_text())
    for p,h in m["protected"].items():assert prior.roles.sha(ROOT/p)==h,p
    return m
def validate_previous(run,job,result):
    assert run["id"]==PREVIOUS_RUN and run["head_sha"]==PREVIOUS_SOURCE
    assert run["run_attempt"]==1 and run["status"]=="completed"and run["conclusion"]=="success"
    assert run["event"]=="workflow_dispatch"and run["path"]==".github/workflows/tx-native-clock-role-p4-parameters-cloud.yml"
    assert job["id"]==PREVIOUS_JOB and job["run_id"]==PREVIOUS_RUN and job["head_sha"]==PREVIOUS_SOURCE
    assert job["status"]=="completed"and job["conclusion"]=="success"and job["run_attempt"]==1
    assert result["source_head"]==PREVIOUS_SOURCE and int(result["run_id"])==PREVIOUS_RUN
    assert result["status"]=="PASS_EXACT_STAGE_ROLE_PARAMETER_DIAGNOSIS_ORIGINAL_BINDER_REJECTION_REMAINS"
    assert result["native_returncode"]==0 and result["sources_unchanged"]
    d=result["diagnosis"]
    assert d["counts"]=={"muxes":31,"HBTs":589,"emitters":863.0}and not d["mismatches"]
    assert not roles.observer.mismatches(d["blocks"])
    roles.observer.verify_original_failure(d["original_failure"],d["first_legacy_selector_rejection"])
    k=d["kind_transition"];roles.history.failure_identity(k["original_failure"])
    assert k["only_changed_kind_labels"]==list(roles.history.P4)and k["expected_emitters"]==863
    assert k["all_other_topology_fields_unchanged"]is k["actual_layout_metadata_unchanged"]is True
    assert d["qualified_inputs_unchanged"]and d["original_binder_unchanged"]
    assert d["original_interfaces_sha256"]==prior.roles.PIN["interfaces.json"]
    assert all(d[k]is False for k in ("native_role_accepted","electrical_accepted","full_phy_accepted"))
def previous():
    assert prior.roles.sha(ROOT/PREVIOUS_RESULT)==PREVIOUS_SHA
    result=json.loads((ROOT/PREVIOUS_RESULT).read_text())
    run=prior.api("actions/runs/"+str(PREVIOUS_RUN))
    job=prior.api("actions/jobs/"+str(PREVIOUS_JOB))
    validate_previous(run,job,result)
    log=subprocess.check_output(["gh","api","--allow-escape-sequences","repos/Melihakbulut221/nssoc/actions/jobs/"+str(PREVIOUS_JOB)+"/logs"])
    assert len(log)==1392755 and hashlib.sha256(log).hexdigest()==PREVIOUS_LOG
    return run,job,result
def controls():
    prior.host();m=pins();old=parent.controls();new=roles.controls()
    run,job,result=previous();faults=[]
    for name in ("run_source","job_source","run_conclusion","job_conclusion","run_attempt","job_identity","counts","mismatch","old_accepted","source_mutation"):
        r=copy.deepcopy(run);j=copy.deepcopy(job);d=copy.deepcopy(result)
        if name=="run_source":r["head_sha"]="0"*40
        elif name=="job_source":j["head_sha"]="0"*40
        elif name=="run_conclusion":r["conclusion"]="failure"
        elif name=="job_conclusion":j["conclusion"]="failure"
        elif name=="run_attempt":r["run_attempt"]=2
        elif name=="job_identity":j["id"]+=1
        elif name=="counts":d["diagnosis"]["counts"]["emitters"]=719.
        elif name=="mismatch":d["diagnosis"]["mismatches"]=[{"wrong":True}]
        elif name=="old_accepted":d["diagnosis"]["native_role_accepted"]=True
        else:d["sources_unchanged"]=False
        try:validate_previous(r,j,d)
        except AssertionError:faults.append(name)
        else:raise AssertionError("Accepted prerequisite corruption "+name)
    assert len(faults)==10 and len(new["stage_parameter_faults"])==48
    pins()
    return {"status":"PASS_CORRECTED_NATIVE_ROLE_SOURCE_AND_PREREQUISITE_CONTROLS_NO_NATIVE",
      "original_metadata_archive_catalog_and_history_controls":old,"corrected_binder_controls":new,
      "previous_proof":{"run":PREVIOUS_RUN,"source":PREVIOUS_SOURCE,"job":PREVIOUS_JOB,
        "job_log_sha256":PREVIOUS_LOG,"result_sha256":PREVIOUS_SHA},
      "prerequisite_faults":faults,"method":m,"native_role_accepted":False,
      "electrical_accepted":False,"full_phy_accepted":False}
def main():
    prior.host();m=pins();OUT.mkdir(parents=True,exist_ok=False);assert not WORK.exists()
    report={"status":"RUNNING","source_head":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],
      "method":m,"native_role_accepted":False,"electrical_accepted":False,
      "full_phy_accepted":False,"no_new_extraction_or_simulation":True}
    def save():(OUT/"result.json").write_text(json.dumps(report,indent=2)+"\n")
    save()
    try:
        previous();report["qualified_stage_proof"]={"run":PREVIOUS_RUN,"source":PREVIOUS_SOURCE,"sha256":PREVIOUS_SHA}
        prior.validate_run(prior.api("actions/runs/"+str(prior.roles.SOURCE_RUN)));pinned=prior.summary()
        prior.restore.OUT=OUT
        restored,proof=prior.restore.restore_report(prior.GROUP,prior.roles.SOURCE_RUN,
          prior.roles.SUMMARY,prior.roles.PARTS,WORK,list(prior.roles.PIN))
        assert restored==pinned and prior.roles.sha(WORK/"result.json")==prior.roles.SUMMARY
        prior.validate_summary(restored);report["restore"]=proof;save()
        app=Path(os.environ["CLOUD_APPIMAGE"]);assert prior.roles.sha(app)==prior.APP_SHA
        with(OUT/"native-canonical-role-binder.log").open("w")as log:
            p=subprocess.run([str(app),"python",str(ROOT/"scripts/bind_tx_output8088_canonical_clock_roles.py"),
              str(WORK),str(WORK/"result.json"),str(OUT/"native")],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        report["native_returncode"]=p.returncode
        f=OUT/"native/clock-roles.json"
        if f.exists():report["binding"]=json.loads(f.read_text())
        save();assert p.returncode==0,"Actual canonical role binding or original failure reproduction failed"
        d=report["binding"]
        assert d["status"]==roles.STATUS and d["native_role_accepted"]is True
        assert d["canonical_counts"]=={"muxes":31,"HBTs":589,"emitters":863}and not d["canonical_mismatches"]
        assert not roles.observer.mismatches(d["all589_actual_devices"])
        assert roles.compare_projection(d,d["all589_actual_devices"])==d["canonical_projection"]
        roles.observer.verify_original_failure(d["original_failure"],d["first_legacy_selector_rejection"])
        roles.history.failure_identity(d["kind_transition"]["original_failure"])
        assert len(d["role_controls"])==14 and all(x["rejected"]for x in d["role_controls"])
        assert len(d["actual_polarity_faults"])==31 and all(x["wrong_p_to_n_rejected"]and x["wrong_n_to_p_rejected"]for x in d["actual_polarity_faults"])
        assert d["original_binder_unchanged"]and d["qualified_inputs_unchanged"]
        assert d["original_interfaces_sha256"]==prior.roles.PIN["interfaces.json"]
        assert all(d[k]is False for k in ("real_clock_drivers_implemented","electrical_accepted",
          "reset_distribution_accepted","full31_tree_accepted","PLL_connected","full_phy_accepted","mainchip_integrated"))
        pins();roles.observer.source_catalog()
        assert all(prior.roles.sha(WORK/p)==h for p,h in prior.roles.PIN.items())
        report.update(status=d["status"],native_role_accepted=True,sources_unchanged=True,
          qualified_input_hashes=prior.roles.PIN,
          next="Actual clock driver/load and31-tree reset/phase/layout closure remain open; this proof binds existing physical selector loads only.")
    except BaseException as e:
        report.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
    finally:
        log=OUT/"native-canonical-role-binder.log"
        if log.exists():
            b=log.read_bytes();assert len(b)<=1_000_000
            report["native_log_readback"]={"bytes":len(b),"sha256":prior.roles.sha(log),"text":b.decode("utf-8",errors="strict")}
        report["outputs"]={str(p.relative_to(OUT)):prior.roles.sha(p)for p in OUT.rglob("*")if p.is_file()and p!=OUT/"result.json"}
        save()
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--controls",action="store_true");args=p.parse_args()
    if args.controls:print(json.dumps(controls(),indent=2))
    else:main()
