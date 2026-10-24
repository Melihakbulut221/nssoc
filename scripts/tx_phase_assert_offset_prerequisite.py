#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind offset244 preparation and preserve the exact original electrical rejection."""
import copy,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PREP=ROOT/"docs/evidence/tx-phase-assert-offset-preparation-pass-20261024.json"
PREP_SHA="af7db2f182cf1e73dab50c029854c7a171678cecb9c40878ca75e2ee17de5be3"
PREP_RUN=40110198744
PREP_HEAD="3e335947e42c562763ffd1c569e86942c047f0fa"
OLD_RUN=40098170615
OLD_HEAD="324b7b477b8b282099eb79d6d72b3f8bf87ca806"
OLD_ASSET=672365442
OLD_SHA="3ad8114c2f3a0f84fd7eb986b0846b98ad0027e977ba62737a019e2c3e28d9fa"
def api(path):return json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/"+path]))
def validate_prepared(p,r):
    assert r["id"]==PREP_RUN and r["head_sha"]==PREP_HEAD and r["run_attempt"]==1
    assert r["status"]=="completed"and r["conclusion"]=="success"
    assert r["path"]==".github/workflows/tx-phase-assert-offset-preparation-cloud.yml"
    assert p["run"]==PREP_RUN and p["source_head"]==PREP_HEAD and p["run_attempt"]==1
    assert p["status"]=="PASS_ASSERT_OFFSET244_FOUR_PREPARED_UNCHANGED_ORACLE_NOT_NATIVE"
    assert p["job"]["id"]==120920134925 and p["job"]["conclusion"]=="success"
    assert p["job_log"]=={"bytes":46890,"sha256":"7f8b15eed4f902795ae81880bb4395c510aab28a02120d5ef1a2935ab2542f6b"}
    assert all(p[k]is False for k in ("native_execution","reset_hardware_qualified","layout_RC_included","PLL_connected","full_PHY_accepted"))
    source,prepared=p["reports"]
    assert source["status"]=="PASS_ASSERT_OFFSET244_SOURCE_ONLY_NOT_ELECTRICAL"
    assert source["candidate_sha256"]=="3b4aa82387b5e532437dc592feceea699b4d283570751d6e983f0949fe7095f4"
    assert len(source["negative_controls"])==14 and len(set(source["negative_controls"]))==14
    assert source["exact_single_resistor_delta"]and source["original244_byte_exact_after_declared_reversal"]
    assert prepared["status"]=="PASS_ASSERT_OFFSET244_FOUR_PREPARED_UNCHANGED_ORACLE_NOT_NATIVE"
    assert len(prepared["negative_controls"])==8 and len(set(prepared["negative_controls"]))==8
    assert set(prepared["positive_cases"])=={s+"-"+str(h)for s in ("p","n")for h in (True,False)}
    for c in prepared["positive_cases"].values():
        assert c["prepared"]and c["exact_old_deck"]and c["exact_old_vectors_HBT_oracle_limits"]
        assert (c["primitive_count"],c["hbt_count"],c["vector_count"],c["thermal_vectors"])==(244,106,358,130)
        assert c["one_real_device_parameter_delta"]==[[
         {"instance":"xdut.xrun.xand_skew","model":"rppd","nodes":["xdut.xrun.bip","0","0"],"parameters":["w=1u","l=32u","b=0","sw_et=1"]},
         {"instance":"xdut.xrun.xand_skew","model":"rppd","nodes":["xdut.xrun.bip","0","0"],"parameters":["w=1u","l=20u","b=0","sw_et=1"]}]]
def validate_rejected(d,r):
    assert r["id"]==OLD_RUN and r["head_sha"]==OLD_HEAD and r["run_attempt"]==1
    assert r["status"]=="completed"and r["conclusion"]=="failure"
    assert r["path"]==".github/workflows/tx-phase-fast-assert-intrinsic-cloud.yml"
    assert int(d["run_id"])==OLD_RUN and d["source_head"]==OLD_HEAD
    assert d["status"]=="REJECTED_FAST_ASSERT244_PRESERVE_COMPLETE_FAILURE_EVIDENCE"
    assert d["sources_and_models_unchanged"]and d["all_four_diagnostic_screens_passed"]is False
    assert all(d[k]is False for k in ("reset_hardware_qualified","all31_clock_tree_accepted","layout_RC_included","PLL_connected","full_PHY_accepted"))
    assert set(d["native_cases"])=={s+"-initial-"+h for s in ("p","n")for h in ("high","low")}
    for name,c in d["native_cases"].items():
        assert c["complete"]and c["returncode"]==0 and c["diagnostics"]==[]and c["errors"]==[]
        assert c["capture"]["complete_unmodified_rows"]and c["vector_count"]==358 and c["hbt_count"]==106
        expected=name=="p-initial-high"
        assert c["diagnostic_screen_passed"]is expected and c["acceptance_gate"]["passed"]is expected
        checks=c["acceptance_gate"]["checks"]
        assert checks["original_phase_and_safety"]is expected
        assert all(v is True for k,v in checks.items()if k!="original_phase_and_safety")
def load():
    raw=PREP.read_bytes();assert hashlib.sha256(raw).hexdigest()==PREP_SHA
    p=json.loads(raw);r=api("actions/runs/"+str(PREP_RUN));validate_prepared(p,r)
    b=subprocess.check_output(["gh","api",f"repos/Melihakbulut221/nssoc/releases/assets/{OLD_ASSET}","-H","Accept: application/octet-stream"])
    assert hashlib.sha256(b).hexdigest()==OLD_SHA
    d=json.loads(b);oldrun=api("actions/runs/"+str(OLD_RUN));validate_rejected(d,oldrun)
    return {"preparation_run":PREP_RUN,"preparation_source":PREP_HEAD,"preparation_receipt_sha256":PREP_SHA,
     "original_rejected_run":OLD_RUN,"original_rejected_source":OLD_HEAD,"original_summary_asset":OLD_ASSET,"original_summary_sha256":OLD_SHA,
     "original_three_case_rejection_preserved":True,"scope":"Preparation/source prerequisite only; new numerical/fullwave/fixedphase/106HBT safety gates remain mandatory."},p,r,d,oldrun
def controls():
    receipt,p,r,d,oldrun=load();faults=[]
    for name in ("prep_source","prep_run_live","prep_false_execution","prep_vector_count","prep_wrong_resistor","prep_missing_case","old_accepted","old_source","old_hidden_failure","old_numerical_failure"):
        a,b,c,e=copy.deepcopy((p,r,d,oldrun))
        if name=="prep_source":b["head_sha"]="0"*40
        elif name=="prep_run_live":b["status"]="in_progress"
        elif name=="prep_false_execution":a["native_execution"]=True
        elif name=="prep_vector_count":a["reports"][1]["positive_cases"]["p-True"]["vector_count"]-=1
        elif name=="prep_wrong_resistor":a["reports"][1]["positive_cases"]["p-True"]["one_real_device_parameter_delta"][0][1]["parameters"][1]="l=19u"
        elif name=="prep_missing_case":a["reports"][1]["positive_cases"].pop("n-False")
        elif name=="old_accepted":c["all_four_diagnostic_screens_passed"]=True
        elif name=="old_source":e["head_sha"]="0"*40
        elif name=="old_hidden_failure":c["native_cases"]["n-initial-low"]["diagnostic_screen_passed"]=True
        else:c["native_cases"]["n-initial-low"]["diagnostics"]=["NaN"]
        try:validate_prepared(a,b);validate_rejected(c,e)
        except (AssertionError,KeyError,ValueError):faults.append({"name":name,"rejected":True})
        else:raise AssertionError("Accepted "+name)
    return {"status":"PASS_EXACT_OFFSET_PREPARATION_OLD_REJECTION_AND10_FAULTS_NO_DUT_TRANSIENT","receipt":receipt,"faults":faults}
