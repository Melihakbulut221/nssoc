#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact existing TX archive; parameter observer only, no extraction/simulation."""
import argparse,json,os,subprocess,traceback
from pathlib import Path
import cloud_tx_output8088_native_clock_roles as prior
import observe_tx_native_clock_role_p4_parameters as observer
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"hw/soc/out/cloud-tx-native-clock-role-p4-parameters"
WORK=ROOT/"hw/soc/out/cloud-tx-native-clock-role-p4-parameters-restored"
METHOD=ROOT/"scripts/tx-native-clock-role-p4-parameters-methods.json"
def pins():
    m=json.loads(METHOD.read_text())
    for p,h in m["protected"].items():assert prior.roles.sha(ROOT/p)==h,(p,"Protected source changed")
    return m
def controls():
    prior.host();m=pins();old=prior.controls();new=observer.controls();pins()
    assert old["status"]=="PASS_EXACT_PARENT_METADATA_AND_ARCHIVE_CONTROLS_NOT_NATIVE_ROLES"
    assert len(old["controls"])==12 and len(old["archive_controls"]["negative_controls"])==8
    assert len(new["faults"])==16 and all(x["rejected"]for x in new["faults"])
    assert len(new["original_failure_faults"])==6 and all(x["rejected"]for x in new["original_failure_faults"])
    assert len(new["p4_history_controls"]["faults"])==28 and all(x["rejected"]for x in new["p4_history_controls"]["faults"])
    return {"status":"PASS_PINNED_PARENT_AND_STAGE_PARAMETER_CONTROLS_NOT_NATIVE_PROOF",
     "original_parent_controls":old,"stage_catalog_controls":new,"method":m,
     "native_execution":False,"native_role_accepted":False,"electrical_accepted":False,"full_phy_accepted":False}
def main():
    prior.host();m=pins();OUT.mkdir(parents=True,exist_ok=False);assert not WORK.exists()
    report={"status":"RUNNING","source_head":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"method":m,
     "native_role_accepted":False,"electrical_accepted":False,"full_phy_accepted":False,"no_new_extraction_or_simulation":True}
    def save():(OUT/"result.json").write_text(json.dumps(report,indent=2)+"\n")
    save()
    try:
        prior.validate_run(prior.api("actions/runs/"+str(prior.roles.SOURCE_RUN)));pinned=prior.summary()
        prior.restore.OUT=OUT
        restored,proof=prior.restore.restore_report(prior.GROUP,prior.roles.SOURCE_RUN,prior.roles.SUMMARY,prior.roles.PARTS,WORK,list(prior.roles.PIN))
        assert restored==pinned and prior.roles.sha(WORK/"result.json")==prior.roles.SUMMARY
        prior.validate_summary(restored);report["restore"]=proof;save()
        app=Path(os.environ["CLOUD_APPIMAGE"]);assert prior.roles.sha(app)==prior.APP_SHA
        with(OUT/"native-parameter-observer.log").open("w")as log:
            p=subprocess.run([str(app),"python",str(ROOT/"scripts/observe_tx_native_clock_role_p4_parameters.py"),
                 str(WORK),str(WORK/"result.json"),str(OUT/"native")],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        report["native_returncode"]=p.returncode
        f=OUT/"native/parameter-diagnosis.json"
        if f.exists():report["diagnosis"]=json.loads(f.read_text())
        save();assert p.returncode==0,"Actual role/source comparison or original rejection reproduction failed"
        d=report["diagnosis"]
        assert d["status"]=="PASS_EXACT_STAGE_ROLE_PARAMETER_DIAGNOSIS_ORIGINAL_BINDER_REJECTION_REMAINS"
        assert d["counts"]=={"muxes":31,"HBTs":589,"emitters":863.0}and not d["mismatches"]
        assert not observer.mismatches(d["blocks"])
        k=d["kind_transition"];observer.p4.failure_identity(k["original_failure"])
        assert k["only_changed_kind_labels"]==list(observer.p4.P4) and k["expected_emitters"]==863
        assert k["all_other_topology_fields_unchanged"] is k["actual_layout_metadata_unchanged"] is True
        assert all(k[x]is False for x in ("role_accepted","electrical_accepted","full_phy_accepted"))
        observer.verify_original_failure(d["original_failure"],d["first_legacy_selector_rejection"])
        assert d["original_binder_unchanged"]and d["qualified_inputs_unchanged"]and d["no_new_extraction_or_simulation"]
        assert d["original_interfaces_sha256"]==prior.roles.PIN["interfaces.json"]
        assert all(d[k]is False for k in ("native_role_accepted","electrical_accepted","full_phy_accepted"))
        pins();observer.source_catalog();assert all(prior.roles.sha(WORK/p)==h for p,h in prior.roles.PIN.items())
        report.update(status=d["status"],sources_unchanged=True,qualified_input_hashes=prior.roles.PIN,
         next="Independent review of actual source/device-role mismatch before any binder repair. No changed circuit, driver/load, phase, electrical, PHY or mainchip acceptance.")
    except BaseException as e:
        report.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
    finally:
        log=OUT/"native-parameter-observer.log"
        if log.exists():
            b=log.read_bytes();assert len(b)<=1_000_000
            report["native_log_readback"]={"bytes":len(b),"sha256":prior.roles.sha(log),"text":b.decode("utf-8",errors="strict")}
        report["outputs"]={str(p.relative_to(OUT)):prior.roles.sha(p)for p in OUT.rglob("*")if p.is_file()and p!=OUT/"result.json"}
        save()
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--controls",action="store_true");args=p.parse_args()
    if args.controls:print(json.dumps(controls(),indent=2))
    else:main()
