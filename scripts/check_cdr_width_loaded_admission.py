#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-only authentic JSON controls; native I/O is explicitly doubled, never acquired."""
import argparse,copy,hashlib,json,os,tempfile,traceback
from pathlib import Path
from unittest.mock import patch
import cdr_width_loaded_admission as a

PROGRESS={"status":"RUNNING","native_acquisition":False,"simulation_executed":False,"electrical_accepted":False}

def refuse(name,call,rows,reason=None):
    try:call()
    except (AssertionError,ValueError,KeyError,TypeError)as error:
        if reason is not None:assert reason in str(error),(name,repr(error),reason)
        rows.append({"case":name,"error":repr(error)})
    else:raise AssertionError("Accepted corruption: "+name)

def changed(d,path,value,delete=False):
    out=copy.deepcopy(d);target=out
    for key in path[:-1]:target=target[key]
    if delete:del target[path[-1]]
    else:target[path[-1]]=value
    assert json.dumps(out,sort_keys=True)!=json.dumps(d,sort_keys=True)
    return out

def report_controls(d):
    good=a.validate_reports(d);rows=[]
    mutations=[
      ("wrong producer",["direct/summary.json","source_head"],"0"*40,False),
      ("raw-summary substitution",["complete-native-restore-map.json","result.json"],a.SUMMARY_SHA,False),
      ("missing complete member",["complete-native-restore-map.json",a.MODEL_MEMBER],None,True),
      ("terminal failure",["direct/summary.json","terminal_finalization_complete"],False,False),
      ("phase returncode",["direct/summary.json","commands",1,"returncode"],1,False),
      ("old RC count",["direct/composition.json","counts","R"],24616,False),
      ("old capacitance count",["direct/composition.json","counts","C"],15722,False),
      ("native public order",["direct/composition.json","interface",0],"wrong",False),
      ("binding identity",["direct/binding.json","devices",0,"native_id"],-1,False),
      ("native MIM old source",["direct/MIM-precision-result.json","source_head"],"0"*40,False),
      ("MIM two orders",["direct/MIM-precision-result.json","both_native_orders_verified"],False,False),
      ("current75 missing member",["direct/canonical-candidate.json","files","native-planes.json"],None,True),
      ("current root fabricated",["direct/canonical-candidate.json","current_root_result_fabricated"],True,False),
      ("graph lineage",["direct/joint-admission.json","original_graph_run"],1,False),
      ("historical handoff census",["direct/MIM-precision-result.json","current_input_restoration","historical763_1136_1127_counts_reused"],True,False),
      ("missing nested binding member",["direct/binding-result.json","outputs","binding.json"],None,True),
      ("publication incomplete",[a.PUBLICATION,"status"],"RUNNING_PUBLICATION",False),
      ("empty streams replaced",["direct/direct-publication-plan.json","empty_bytes_replaced"],True,False)]
    for name,path,value,delete in mutations:
        bad=changed(d,path,value,delete);refuse(name,lambda bad=bad:a.validate_reports(bad),rows)
    full=d["complete-native-restore-map.json"];selected=a.selected_members(full)
    historic=[n for n,h in full.items()if n.endswith("native-planes.json")and h!=a.PLANES_SHA]
    assert historic and a.PLANES_MEMBER in selected and selected[a.MODEL_MEMBER]==a.MODEL_SHA
    for name,change in (("historical plane suffix",lambda m:m.__setitem__(a.PLANES_MEMBER,full[historic[0]])),
      ("current plane missing despite historical suffix",lambda m:m.pop(a.PLANES_MEMBER)),
      ("wrong selected model",lambda m:m.__setitem__(a.MODEL_MEMBER,"0"*64))):
        bad=dict(full);change(bad);refuse(name,lambda bad=bad:a.selected_members(bad),rows)
    return {"positive":2,"refusals":rows,"authentic_complete_JSON":True,"original_pipeline_validator_called":True,"proof":good}

def live_controls(d):
    actual=[d[n]for n in ("run.json","jobs.json","release.json","tag-ref.json")]
    proof=a.validate_live(*actual,docs=d);rows=[]
    mutations=[
      ("run source",0,["head_sha"],"0"*40),
      ("run retry",0,["run_attempt"],2),
      ("run failure",0,["conclusion"],"failure"),
      ("job failure",1,["jobs",1,"conclusion"],"failure"),
      ("job step skipped",1,["jobs",1,"steps",5,"conclusion"],"skipped"),
      ("duplicate job",1,["jobs",1,"id"],actual[1]["jobs"][0]["id"]),
      ("release identity",2,["id"],1),
      ("asset size",2,["assets",0,"size"],1),
      ("asset digest",2,["assets",0,"digest"],"sha256:"+"0"*64),
      ("asset missing id",2,["assets",0,"id"],False),
      ("tag source",3,["object","sha"],"0"*40)]
    for name,index,path,value in mutations:
        bad=copy.deepcopy(actual);bad[index]=changed(bad[index],path,value)
        refuse(name,lambda bad=bad:a.validate_live(*bad,docs=d),rows)
    bad=copy.deepcopy(actual);bad[2]["assets"].pop();refuse("missing release member",lambda:a.validate_live(*bad,docs=d),rows)
    return {"positive":1,"refusals":rows,"actual_saved_live_metadata":True,"proof":proof}

def source_controls():
    rows=[];m=a.methods();disabled=copy.deepcopy(m)
    for k in a.old.AUTH+("controller_readiness",):disabled[k]=False
    a.old.validate_authorizations(disabled)
    enabled=copy.deepcopy(disabled)
    for k in a.old.AUTH+("controller_readiness",):enabled[k]=True
    a.old.validate_authorizations(enabled)
    for mode,base in (("disabled",disabled),("enabled",enabled)):
        for key in ("source_controls_authorized","simulation_authorized","preparation_authorized"):
            bad=copy.deepcopy(base);bad[key]=1
            refuse(mode+" typed "+key,lambda bad=bad:a.old.validate_authorizations(bad),rows)
    bad=copy.deepcopy(enabled);bad["simulation_authorized"]=False
    refuse("split native/simulation",lambda:a.old.validate_authorizations(bad),rows)
    env=dict(GITHUB_ACTIONS="true",RUNNER_ENVIRONMENT="github-hosted",GITHUB_REPOSITORY="Melihakbulut221/nssoc",GITHUB_EVENT_NAME="workflow_dispatch",GITHUB_RUN_ATTEMPT="1",GITHUB_SHA="a"*40,GITHUB_RUN_ID="902",GITHUB_REF="refs/heads/"+a.BRANCH)
    with patch.dict(os.environ,env,clear=False),patch.object(a,"methods",return_value=disabled):
        for mode in (True,False):refuse("disabled actual authorize "+str(mode),lambda mode=mode:a.authorize(mode),rows)
    with patch.dict(os.environ,env,clear=False),patch.object(a,"methods",return_value=enabled):
        assert a.authorize(True)==a.authorize(False)==enabled
        refuse("nonboolean preparation",lambda:a.authorize(1),rows)
        with patch.dict(os.environ,{"GITHUB_RUN_ATTEMPT":"2"}):refuse("actual retry context",lambda:a.authorize(True),rows)
    # Real malformed report bytes; only protected path lookup is redirected to a temporary copy.
    with tempfile.TemporaryDirectory()as td:
        wrong=Path(td)/"receipt.json";wrong.write_bytes(b'{"not":"the original receipt"}\n');original=a.regular
        def lookup(root,name):return wrong if name==a.RECEIPT else original(root,name)
        with patch.object(a,"regular",side_effect=lookup):refuse("actual protected receipt corruption",a.source_guard,rows,"Protected loaded source changed")
    return {"positive":2,"refusals":rows,"both_typed_modes":True,"real_report_bytes_corrupted":True}

def restore_controls(d):
    cases=[];full=d["complete-native-restore-map.json"]
    archive={"regular_members":6647,"full_inventory_verified":True,"complete_member_hashes":{n:{"sha256":h,"bytes":0}for n,h in full.items()},"synthetic_fixture_not_actual_archive":True}
    synthetic_planes={"synthetic_fixture_only":True}
    endpoints={"actions/runs/"+str(a.RUN):d["run.json"],"actions/runs/"+str(a.RUN)+"/attempts/1/jobs?per_page=100":d["jobs.json"],"releases/"+str(a.RELEASE):d["release.json"],"git/ref/tags/"+a.TAG:d["tag-ref.json"]}
    method=a.methods();enabled=copy.deepcopy(method)
    for k in a.old.AUTH+("controller_readiness",):enabled[k]=True
    env=dict(GITHUB_ACTIONS="true",RUNNER_ENVIRONMENT="github-hosted",GITHUB_REPOSITORY="Melihakbulut221/nssoc",GITHUB_EVENT_NAME="workflow_dispatch",GITHUB_RUN_ATTEMPT="1",GITHUB_SHA="a"*40,GITHUB_RUN_ID="902",GITHUB_REF="refs/heads/"+a.BRANCH)
    for mode in ("preparation","simulation","transport_failure","verification_failure","occupied"):
        calls=[];failure=OSError("explicit synthetic "+mode)
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)
            if mode=="occupied":(out/"current-mim-bundle").mkdir()
            def read(endpoint):calls.append(("read",endpoint));return copy.deepcopy(endpoints[endpoint])
            def extract(actual_out,actual_docs,info):
                assert actual_out==out and actual_docs is d and info==d["release.json"]
                calls.append(("synthetic_extract",6647))
                if mode=="transport_failure":raise failure
                return copy.deepcopy(archive)
            def verify(bundle,docs):
                assert bundle==out/"current-mim-bundle"and docs is d;calls.append(("synthetic_verify",6647))
                if mode=="verification_failure":raise failure
                return synthetic_planes,{"synthetic":True}
            caught=None;result=None
            with patch.dict(os.environ,env,clear=False),patch.object(a,"methods",return_value=enabled),patch.object(a,"source_guard",return_value=d),patch.object(a.release,"api",side_effect=read),patch.object(a,"acquire_and_extract",side_effect=extract),patch.object(a,"verify_bundle",side_effect=verify):
                try:result=a.restore(out,mode!="simulation")
                except BaseException as error:caught=error
            if mode in ("transport_failure","verification_failure"):
                assert caught is failure
                if mode=="transport_failure":assert not any(x[0]=="synthetic_verify"for x in calls)
            elif mode=="occupied":assert isinstance(caught,AssertionError)and not calls
            else:
                assert caught is None and len(result)==6
                mim,proof,model,contract,planes,plane_proof=result
                assert mim is d["direct/MIM-precision-result.json"]and contract is d["direct/composition.json"]
                assert model==out/"current-mim-bundle"/a.MODEL_MEMBER and planes is synthetic_planes
                assert proof["raw_result_sha256"]!=proof["summary_sha256"]and proof["simulation_preaccepted"]is False
                assert plane_proof["native_planes_sha256"]==a.PLANES_SHA
                assert calls[-2:]==[("synthetic_extract",6647),("synthetic_verify",6647)]
            cases.append({"case":mode,"six_tuple_or_exact_failure_checked":True,"native_transport_and_file_verification_are_synthetic":True,"calls":calls,"error":None if caught is None else repr(caught)})
    return {"cases":cases,"count":len(cases),"real_archive_restoration_qualified":False}

def controls():
    d=a.source_guard()
    PROGRESS["source_guard"]={"protected_full_proof":True,"required_parsed_reports":len(a.REQUIRED)}
    PROGRESS["reports"]=report_controls(d)
    PROGRESS["live"]=live_controls(d)
    PROGRESS["authority_and_integrity"]=source_controls()
    PROGRESS["restore_interface"]=restore_controls(d)
    PROGRESS.update(status="PASS_CURRENT_WIDTH_LOADED_INPUT_SOURCE_CONTROLS",positive_count=5,
      refusal_count=sum(len(PROGRESS[k]["refusals"])for k in ("reports","live","authority_and_integrity")),
      original_electrical_worker_modified=False,actual_native_restore_executed=False)
    return PROGRESS

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);args=p.parse_args();primary=None
    try:controls()
    except BaseException as error:
        primary=error;PROGRESS.update(status="FAIL_CURRENT_WIDTH_LOADED_INPUT_SOURCE_CONTROLS",error=repr(error),traceback=traceback.format_exc())
    try:a.write(args.output,PROGRESS)
    except BaseException:
        if primary is None:raise
        try:print(json.dumps(PROGRESS,sort_keys=True),flush=True)
        except BaseException:pass
    if primary is not None:raise primary
    print(json.dumps(PROGRESS,sort_keys=True))

if __name__=="__main__":main()
