#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source controls. Native acquisition/simulation boundaries are synthetic."""
import argparse,ast,copy,hashlib,json,os,tempfile,traceback
from pathlib import Path
from unittest.mock import patch
import cdr_width_loaded_execution_admission as a
import cloud_cdr_width_loaded_stage as stage

STAGE_ORIGINAL="scripts/cloud_cdr_v59_tail_loaded_stage.py"
STAGE_ORIGINAL_SHA="6e142135ba350c427cf888a409ed44d664ac8c79d6e673ee1afe2e358f71fe2f"
STAGE_EDITS=[('import cdr_v59_tail_loaded_admission as a', 'import cdr_width_loaded_execution_admission as a'), ('import cdr_v59_tail_loaded_result as result_gate', 'import cdr_width_loaded_result as result_gate'), ('scripts/cloud_cdr_v59_tail_loaded.py', 'scripts/cloud_cdr_width_loaded.py'), ('cdr-v59-tail-loaded-', 'cdr-width-loaded-'), ('40576801174', '40830441311'), ('"original_physical_status":"FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL",', '"original_physical_status":"FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL",\n      "original_physical_historical_only":True,\n      "current_width_run":40815684037,"current_width_source":"214ec651fd501de7e2f49a38509b184a1fd66f8d",\n      "current_graph_run":40808550817,"current_graph_source":"97705f184239c0c522582b9d8e82c542bd902b65",'), ('and result["original_physical_status"]=="FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL"', 'and result["original_physical_status"]=="FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL"\n      and result["original_physical_historical_only"]is True\n      and (result["current_width_run"],result["current_width_source"])==(40815684037,"214ec651fd501de7e2f49a38509b184a1fd66f8d")\n      and (result["current_graph_run"],result["current_graph_source"])==(40808550817,"97705f184239c0c522582b9d8e82c542bd902b65")')]
STAGE_COUNTS=[1, 1, 1, 7, 2, 1, 1]
FROZEN={"scripts/cdr_width_loaded_admission.py":"45f5beecc013eeeb839214888b427745910b04bed3bb9d111c3ea5d56c32eb63",
 "scripts/cdr_width_loaded_result.py":"468dd60192add0313bd64bef27a0829e6aa0bc15381e9f81b051048681dbb00f",
 "scripts/cdr_v59_tail_loaded_terminal.py":"b98959e391a614f10969a2430f89d9ee6379e7e0f4a968846ae420c89a210e90"}
STATUS="PASS_WIDTH_LOADED_EXECUTION_SOURCE_CONTROLS"

def refused(label,call,reason,rows):
    try:call()
    except (AssertionError,KeyError,ValueError,FileNotFoundError)as error:
        a.require(reason in str(error),"Unexpected refusal "+label+": "+repr(error))
        rows.append({"name":label,"reason":str(error)})
    else:raise AssertionError("Accepted mutation: "+label)

def env():
    return {"GITHUB_ACTIONS":"true","RUNNER_ENVIRONMENT":"github-hosted","RUNNER_OS":"Linux",
      "GITHUB_REPOSITORY":"Melihakbulut221/nssoc","GITHUB_EVENT_NAME":"workflow_dispatch",
      "GITHUB_RUN_ATTEMPT":"1","GITHUB_REF":"refs/heads/"+a.BRANCH,
      "GITHUB_SHA":"a"*40,"GITHUB_RUN_ID":"123456789"}

def baseline(prior,native=False,prepare=False):
    protected=copy.deepcopy(prior["protected_sha256"])
    protected[a.QUALIFIED_METHOD]=a.QUALIFIED_METHOD_SHA
    protected.update({n:s["sha256"]for n,s in a.SOURCE_REQUIRED.items()})
    protected.update({n:a.sha(a.regular(a.ROOT,n))for n in a.NEW_REQUIRED})
    active=native or prepare
    if active:protected[a.WORKER]=a.EXECUTION_WORKER_SHA
    m={"schema":"cdr-width-loaded-execution-v1","branch":a.BRANCH,
      "producer_run":a.RUN,"producer_source":a.HEAD,"cases":list(a.CASES),
      "execution_policy":copy.deepcopy(a.POLICY),"qualified_worker_method":a.QUALIFIED_METHOD,
      "qualified_worker_method_sha256":a.QUALIFIED_METHOD_SHA,
      "qualified_worker_source_run":a.SOURCE_RUN,
      "qualified_worker_source_receipt_sha256":a.SOURCE_RECEIPT_SHA,
      "protected_sha256":protected,"controller_readiness":active}
    m.update({k:False for k in a.AUTH+a.ALWAYS_FALSE})
    m.update(source_controls_authorized=True,workflow_dispatch_authorized=active,
      preparation_authorized=active,native_execution_authorized=native,simulation_authorized=native)
    return m

def derivation_controls():
    for n,h in FROZEN.items():a.require(a.sha(a.regular(a.ROOT,n))==h,"Frozen input/result/terminal changed")
    raw=a.regular(a.ROOT,STAGE_ORIGINAL).read_bytes()
    a.require(hashlib.sha256(raw).hexdigest()==STAGE_ORIGINAL_SHA,"Original stage bytes changed")
    original=raw.decode();derived=original
    for (before,after),count in zip(STAGE_EDITS,STAGE_COUNTS):
        a.require(derived.count(before)==count,"Stage derivation occurrence changed")
        derived=derived.replace(before,after)
    actual=a.regular(a.ROOT,"scripts/cloud_cdr_width_loaded_stage.py").read_text()
    a.require(actual==derived,"Stage differs beyond declared literal substitutions")
    reverse=actual
    for (before,after),count in reversed(list(zip(STAGE_EDITS,STAGE_COUNTS))):
        a.require(reverse.count(after)==count,"Stage reverse occurrence changed")
        reverse=reverse.replace(after,before)
    a.require(reverse==original,"Stage reverse proof changed")
    funcs=lambda t:{n.name:ast.get_source_segment(t,n)for n in ast.parse(t).body if isinstance(n,ast.FunctionDef)}
    old,new=funcs(original),funcs(actual)
    changed=sorted(n for n in old if old[n]!=new[n])
    a.require(changed==["context","fetch_preparation","initial_result","preflight","validate_publication"],
      "Stage control/function boundary changed")
    a.require(all(old[n]==new[n]for n in ("execute","copy_worker","qualify_native","finalize","publish","run_case")),
      "Original worker/failure/publication bodies changed")
    worker=a.regular(a.ROOT,a.WORKER).read_bytes()
    derivation=a.worker_derivation(worker)
    if derivation["execution_adapter_installed"]:
        for before,after in reversed(a.WORKER_EDITS):worker=worker.replace(after.encode(),before.encode())
    a.require(hashlib.sha256(worker).hexdigest()==a.QUALIFIED_WORKER_SHA,"Original worker bytes missing")
    future=worker.decode()
    for before,after in a.WORKER_EDITS:
        a.require(future.count(before)==1,"Worker derivation occurrence changed")
        future=future.replace(before,after)
    a.require(a.worker_derivation(future.encode())["execution_adapter_installed"],"Future worker not admitted")
    rows=[]
    refused("worker_unrelated_change",lambda:a.worker_derivation(future.encode()+b"\n"),"differs beyond",rows)
    # The adapter is an explicit restore copy, with just reservation receipt insertion.
    old_restore=ast.get_source_segment(a.regular(a.ROOT,"scripts/cdr_width_loaded_admission.py").read_text(),
      next(n for n in ast.parse(a.regular(a.ROOT,"scripts/cdr_width_loaded_admission.py").read_text()).body
        if isinstance(n,ast.FunctionDef)and n.name=="restore"))
    adapter_text=a.regular(a.ROOT,"scripts/cdr_width_loaded_execution_admission.py").read_text()
    new_restore=ast.get_source_segment(adapter_text,next(n for n in ast.parse(adapter_text).body
      if isinstance(n,ast.FunctionDef)and n.name=="restore"))
    insertion='    reservations=reservation_gate()\n    write(out/"current-execution-admission.json",reservations)\n'
    a.require(new_restore.count(insertion)==1 and new_restore.replace(insertion,"")==old_restore,
      "Restore sequence changed beyond explicit execution reservation")
    delegates=("validate_live","acquire_and_extract","verify_bundle","loaded_view","expected_files","verify_restored")
    a.require(all(getattr(a,n)is getattr(a.inputs,n)for n in delegates),"Frozen input helper delegation changed")
    return {"exact_forward_reverse":True,"stage_literal_rules":len(STAGE_EDITS),
      "stage_occurrences":sum(STAGE_COUNTS),"changed_stage_functions":changed,"worker_literal_rules":2,
      "native_helpers_delegated":len(delegates),"terminal_unchanged":True,"refusal":len(rows),"cases":rows}

def authority_controls(prior):
    rows=[];positive=0
    for native,prep in ((False,False),(False,True),(True,False)):
        a.validate_method(baseline(prior,native,prep),prior);positive+=1
    m=baseline(prior);m["source_controls_authorized"]=False
    a.validate_method(m,prior);positive+=1
    cases=[]
    for key in a.AUTH+a.ALWAYS_FALSE+("controller_readiness",):
        cases.append(("nonboolean_"+key,lambda m,k=key:m.__setitem__(k,1),"strict booleans"))
    for key in a.ALWAYS_FALSE:
        cases.append(("forbidden_"+key,lambda m,k=key:m.__setitem__(k,True),"Forbidden"))
    cases.extend([
      ("branch",lambda m:m.__setitem__("branch","codex/old"),"identity"),
      ("schema",lambda m:m.__setitem__("schema","cdr-width-loaded-worker-source-controls-v1"),"identity"),
      ("producer_run",lambda m:m.__setitem__("producer_run",40576801174),"producer"),
      ("producer_source",lambda m:m.__setitem__("producer_source","b"*40),"producer"),
      ("cases",lambda m:m["cases"].pop(),"ten cases"),
      ("parallel",lambda m:m["execution_policy"].__setitem__("max_parallel",3),"execution policy"),
      ("timeout",lambda m:m["execution_policy"].__setitem__("each_loaded_case_seconds",7199),"execution policy"),
      ("preparation_last",lambda m:m["execution_policy"]["groups"].reverse(),"execution policy"),
      ("proof",lambda m:m.__setitem__("qualified_worker_source_receipt_sha256","0"*64),"source proof"),
      ("removed_inherited",lambda m:m["protected_sha256"].pop("scripts/cdr_width_loaded_admission.py"),"Inherited"),
      ("removed_new",lambda m:m["protected_sha256"].pop("scripts/cloud_cdr_width_loaded_stage.py"),"source pins"),
      ("changed_worker",lambda m:m["protected_sha256"].__setitem__(a.WORKER,"0"*64),"worker pin"),
      ("old_worker_native",lambda m:m["protected_sha256"].__setitem__(a.WORKER,a.QUALIFIED_WORKER_SHA),"exact worker adapter"),
      ("controller_off",lambda m:m.__setitem__("controller_readiness",False),"Execution requires"),
      ("source_off",lambda m:m.__setitem__("source_controls_authorized",False),"Execution requires"),
      ("dispatch_off",lambda m:m.__setitem__("workflow_dispatch_authorized",False),"Execution requires"),
      ("split_sim",lambda m:m.__setitem__("native_execution_authorized",False),"Split simulator"),
      ("missing_preparation",lambda m:m.__setitem__("preparation_authorized",False),"requires preparation"),
      ("missing_source_proof",lambda m:m["protected_sha256"].pop(a.SOURCE_RECEIPT),"unprotected")
    ])
    for name,mutate,reason in cases:
        m=baseline(prior,True);mutate(m)
        refused(name,lambda m=m:a.validate_method(m,prior),reason,rows)
    with patch.dict(os.environ,env(),clear=True):
        disabled=baseline(prior)
        with patch.object(a,"methods",lambda:a.validate_method(disabled,prior)):
            refused("disabled_preparation",lambda:a.authorize(True),"execution disabled",rows)
            refused("disabled_simulation",lambda:a.authorize(False),"execution disabled",rows)
            refused("nonboolean_mode",lambda:a.authorize(1),"boolean",rows)
    return {"positive":positive,"refusal":len(rows),"cases":rows}

def context_controls():
    e=env();a.context(e);rows=[]
    mutations={"GITHUB_ACTIONS":"false","RUNNER_ENVIRONMENT":"self-hosted","RUNNER_OS":"Windows",
      "GITHUB_REPOSITORY":"other/repo","GITHUB_EVENT_NAME":"push","GITHUB_RUN_ATTEMPT":"2",
      "GITHUB_REF":"refs/heads/codex/cdr-width-loaded-worker","GITHUB_SHA":"bad","GITHUB_RUN_ID":"0"}
    for key,value in mutations.items():
        bad=dict(e);bad[key]=value
        refused(key,lambda bad=bad:a.context(bad),"Current width",rows)
    return {"positive":1,"refusal":len(rows),"cases":rows}

def reserve(group,e):
    tag,source=a.release.context(group,e)
    return {"tag":tag,"tested_source":source,"release_id":100+a.POLICY["groups"].index(group),
      "externally_reserved":True,"creation_attempted":False,"target_verified":True,
      "assets_overwritten":False,"existing_assets":0,"read_attempts":1}

def reservation_controls():
    calls=[];rows=[]
    with patch.dict(os.environ,env(),clear=True),patch.object(a,"wait",lambda g,e:(calls.append(g),reserve(g,e))[1]):
        good=a.reservation_gate()
        a.require(calls==a.POLICY["groups"]and len(good["groups"])==11
          and calls[-1]=="cdr-width-loaded-preparation","Reservation order/complete set changed")
        for key,value in (("tested_source","b"*40),("release_id",True),("creation_attempted",True),("target_verified",False)):
            def bad(g,e,k=key,v=value):
                p=reserve(g,e);p[k]=v;return p
            with patch.object(a,"wait",bad):
                refused("reservation_"+key,a.reservation_gate,"reservation changed",rows)
        def collide(g,e):
            p=reserve(g,e);p["release_id"]=100;return p
        with patch.object(a,"wait",collide):
            refused("release_collision",a.reservation_gate,"release collision",rows)
    return {"positive":1,"refusal":len(rows),"groups":11,"cases":rows}

def restore_controls(prior,d):
    """Real authority/restore/live/loaded_view. Only acquisition/native files are synthetic."""
    full=d["complete-native-restore-map.json"]
    archive={"regular_members":6647,"full_inventory_verified":True,
      "complete_member_hashes":{n:{"sha256":h}for n,h in full.items()}}
    live={"actions/runs/"+str(a.RUN):d["run.json"],
      "actions/runs/"+str(a.RUN)+"/attempts/1/jobs?per_page=100":d["jobs.json"],
      "releases/"+str(a.RELEASE):d["release.json"],"git/ref/tags/"+a.TAG:d["tag-ref.json"]}
    results=[];rows=[]
    for prepare in (True,False):
        calls=[];method=baseline(prior,True)
        def methods():
            calls.append("methods")
            return a.validate_method(method,prior)
        def guard():
            calls.append("source_guard")
            return d
        def waiting(group,e):
            calls.append("reserve:"+group);return reserve(group,e)
        def api(path):
            calls.append("api:"+path);return copy.deepcopy(live[path])
        def acquired(out,docs,info):
            calls.append("acquire")
            a.require(docs is d and info==d["release.json"],"Synthetic I/O received wrong real metadata")
            return copy.deepcopy(archive)
        def verified(bundle,docs):
            calls.append("verify_bundle")
            a.require(bundle.name=="current-mim-bundle"and docs is d,"Wrong real restore root")
            return {"explicit_synthetic_native_planes":True},{"synthetic":True}
        with tempfile.TemporaryDirectory()as temp,patch.dict(os.environ,env(),clear=True),          patch.object(a,"methods",methods),patch.object(a,"source_guard",guard),          patch.object(a,"wait",waiting),patch.object(a.release,"api",api),          patch.object(a,"acquire_and_extract",acquired),patch.object(a,"verify_bundle",verified):
            out=Path(temp);result=a.restore(out,prepare)
            a.require(len(result)==6 and result[0]==d["direct/MIM-precision-result.json"]
              and result[1]["run"]==a.RUN and result[1]["source_head"]==a.HEAD
              and result[2]==out/"current-mim-bundle"/a.inputs.MODEL_MEMBER
              and result[3]==d["direct/composition.json"]
              and result[4]=={"explicit_synthetic_native_planes":True}
              and result[5]["native_planes_sha256"]==a.inputs.PLANES_SHA,"Six-tuple provenance changed")
            a.require(set(result[1])=={"run","source_head","reservation","live_producer","full_archive",
              "summary_sha256","raw_result_sha256","stage_sha256","original_graph_run","original_width_run",
              "complete_graph_members","current_members","historical_failed_geometry_and_electrical_reports_retained",
              "geometry_regenerated","extraction_rerun","simulation_preaccepted"},"Historical producer context restamped")
            receipt=json.loads((out/"current-execution-admission.json").read_bytes())
            a.require(receipt["current_context"]==a.context()and len(receipt["groups"])==11,
              "New execution context missing or mixed with saved producer")
            a.require(calls==["methods","source_guard"]+["reserve:"+g for g in a.POLICY["groups"]]+
              ["api:"+n for n in live]+["acquire","verify_bundle","methods"],"Actual restore order changed")
            results.append({"prepare_only":prepare,"full_metadata_members":len(full),"six_tuple":True})
            sentinel=OSError("synthetic transport interrupted")
            with patch.object(a,"acquire_and_extract",side_effect=sentinel):
                try:a.restore(out,prepare)
                except OSError as error:a.require(error is sentinel,"Transport primary was replaced")
                else:raise AssertionError("Lost transport failure")
            rows.append({"name":"transport_"+str(prepare),"reason":"exact primary preserved"})
            with patch.object(a,"wait",side_effect=AssertionError("synthetic reservation missing")),              patch.object(a,"acquire_and_extract")as acquisition:
                refused("missing_reservation_"+str(prepare),lambda:a.restore(out,prepare),"reservation missing",rows)
                a.require(not acquisition.called,"Acquired native bytes before all reservations")
            bad_live=copy.deepcopy(live);bad_live["actions/runs/"+str(a.RUN)]["head_sha"]="b"*40
            with patch.object(a.release,"api",lambda n:bad_live[n]),patch.object(a,"acquire_and_extract")as acquisition:
                refused("wrong_live_source_"+str(prepare),lambda:a.restore(out,prepare),"Live RC run changed",rows)
                a.require(not acquisition.called,"Acquired after failed live source")
            (out/"current-mim-bundle").mkdir()
            refused("occupied_"+str(prepare),lambda:a.restore(out,prepare),"destination occupied",rows)
    return {"positive":len(results),"refusal":len(rows),"cases":results+rows,
      "actual_restore_function_exercised":True,"actual_authority_and_live_validation":True,
      "native_payload_I_O":"explicitly synthetic acquisition and verify_bundle only",
      "authentic_metadata_members":6647,"native_restore_qualified":False}

def stage_controls(prior):
    rows=[];m=baseline(prior,True)
    with patch.dict(os.environ,env(),clear=True),patch.object(a,"methods",lambda:a.validate_method(m,prior)),      patch.object(stage,"wait",reserve):
        for case in a.CASES:
            c=stage.context(case,False)
            a.require(c["seconds"]==7200 and c["worker"]==a.ROOT/("cloud-cdr-width-loaded-"+case),
              "Actual stage case/path changed")
        c=stage.context("nominal_early",True)
        a.require(c["seconds"]==1200,"Preparation budget changed")
        r=stage.preflight(c)
        a.require(list(r["groups"])==a.POLICY["groups"],"Stage preflight reservation changed")
        with tempfile.TemporaryDirectory()as temp:
            c=dict(c,output=Path(temp))
            result=stage.initial_result(c,r,{"fixture":True})
            result["outputs"]={}
            a.require(stage.validate_publication(c,result)is False,"Unexecuted stage became success")
            for key,value in (("current_width_run",0),("current_graph_run",0),
              ("original_physical_historical_only",False),("fresh_RC_run",40576801174)):
                bad=copy.deepcopy(result);bad[key]=value
                refused("stage_"+key,lambda bad=bad:stage.validate_publication(c,bad),"prior evidence",rows)
    return {"positive":12,"refusal":len(rows),"cases":rows,"preparation_seconds":1200,
      "case_seconds":7200,"maximum_parallel_policy":2,"stage_native_executed":False}

def proof_controls():
    proof=a.worker_proof();rows=[];original=a.regular
    class Altered:
        def __init__(self,b):self.b=b
        def read_bytes(self):return self.b
    for suffix in ("run.json","controls/result.json","controls/stderr.log"):
        target=a.SOURCE_PREFIX+suffix
        def changed(root,name,target=target):
            p=original(root,name)
            return Altered(p.read_bytes()+b"x")if name==target else p
        with patch.object(a,"regular",changed):
            refused("proof_bytes_"+suffix,a.worker_proof,"proof bytes changed",rows)
    def missing(root,name):
        if name==a.SOURCE_RECEIPT:raise FileNotFoundError("synthetic missing proof receipt")
        return original(root,name)
    with patch.object(a,"regular",missing):
        refused("proof_receipt_missing",a.worker_proof,"missing proof receipt",rows)
    return {"positive":1,"refusal":len(rows),"cases":rows,"authentic_source_receipt":proof}

def controls():
    prior=json.loads(a.regular(a.ROOT,a.QUALIFIED_METHOD).read_bytes())
    a.require(a.sha(a.regular(a.ROOT,a.QUALIFIED_METHOD))==a.QUALIFIED_METHOD_SHA,"Qualified method bytes changed")
    proof=a.worker_proof()
    # Authentic source/JSON guard; no input restore, download or native payload is invoked.
    d=a.inputs.source_guard()
    report={"status":STATUS,"qualified_worker_proof":proof,
      "proof":proof_controls(),"derivation":derivation_controls(),"authority":authority_controls(prior),
      "context":context_controls(),"reservations":reservation_controls(),
      "restore":restore_controls(prior,d),"stage":stage_controls(prior),
      "native_acquisition_performed":False,"native_restore_qualified":False,
      "numerical_worker_imported":False,"numerical_worker_executed":False,"simulator_executed":False,
      "electrical_accepted":False,"full_phy_accepted":False,"source_controls_only":True}
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);args=p.parse_args()
    report={"status":"FAIL_WIDTH_LOADED_EXECUTION_SOURCE_CONTROLS","source_controls_only":True,
      "native_acquisition_performed":False,"numerical_worker_executed":False,
      "electrical_accepted":False,"full_phy_accepted":False}
    primary=None
    try:
        ctx=a.context();m=a.methods()
        a.require(m["source_controls_authorized"]is True,"Current execution source controls disabled")
        report=controls()
        report["current_context"]={**ctx,"source_controls_only":True,"native_executed":False}
    except BaseException as error:
        primary=error;report.update(error=repr(error),traceback=traceback.format_exc())
    finally:
        raw=(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
        try:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(raw)
        except BaseException as error:
            if primary is None:primary=error
        try:print(raw.decode(),end="",flush=True)
        except BaseException as error:
            if primary is None:primary=error
    if primary is not None:raise primary

if __name__=="__main__":main()
