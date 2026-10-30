#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only source/metadata and synthetic lifecycle controls. No simulator."""
import argparse,ast,contextlib,copy,hashlib,json,os,tempfile,traceback,types
from pathlib import Path
from unittest.mock import patch
import cdr_drain_m1_loaded_admission as a
import cdr_drain_m1_loaded_result as g
import cloud_cdr_drain_m1_loaded_stage as s
import check_cdr_width_loaded_worker as historical
import check_cdr_width_loaded_publication as publication_controls

REVIEW="docs/evidence/cdr-drain-m1-loaded-source-review-20261030.json"
STATUS="PASS_DRAIN_M1_LOADED_SOURCE_CONTROLS"

def env():
    return {"GITHUB_ACTIONS":"true","RUNNER_ENVIRONMENT":"github-hosted","RUNNER_OS":"Linux",
      "GITHUB_REPOSITORY":"Melihakbulut221/nssoc","GITHUB_EVENT_NAME":"workflow_dispatch",
      "GITHUB_RUN_ATTEMPT":"1","GITHUB_REF":"refs/heads/"+a.BRANCH,"GITHUB_SHA":"a"*40,"GITHUB_RUN_ID":"12345"}

def refused(rows,name,call):
    try:call()
    except (AssertionError,ValueError,KeyError,FileNotFoundError)as error:
        rows.append({"name":name,"type":type(error).__name__,"reason":str(error)})
    else:raise AssertionError("Accepted changed evidence: "+name)

def changed(value,mutate):
    result=copy.deepcopy(value);before=a.encoded(result);mutate(result)
    a.require(a.encoded(result)!=before,"Mutation fixture did not change input")
    return result

def derivation_controls():
    review=json.loads(a.regular(a.ROOT,REVIEW).read_bytes());out={}
    for name,row in review["derivations"].items():
        before=a.regular(a.ROOT,row["baseline"]["path"]).read_bytes()
        after=a.regular(a.ROOT,row["generated"]["path"]).read_bytes()
        a.require(hashlib.sha256(before).hexdigest()==row["baseline"]["sha256"]
          and hashlib.sha256(after).hexdigest()==row["generated"]["sha256"],"Derived source bytes changed")
        text=before.decode()
        for rule in row["edits"]:
            a.require(text.count(rule["before"])==rule["occurrences"],"Derivation occurrence count")
            text=text.replace(rule["before"],rule["after"])
        a.require(text.encode()==after,"Forward source derivation differs")
        for rule in reversed(row["edits"]):
            a.require(text.count(rule["after"])==rule["occurrences"],"Reverse derivation occurrence count")
            text=text.replace(rule["after"],rule["before"])
        a.require(text.encode()==before,"Reverse source derivation differs")
        out[name]={"exact_forward_reverse":True,"edits":len(row["edits"])}
    coordinate=review["frozen_numerical_block_coordinate_source"]
    raw=a.regular(a.ROOT,coordinate["path"]).read_bytes()
    a.require(hashlib.sha256(raw).hexdigest()==coordinate["sha256"],"Numerical coordinate source")
    before=a.regular(a.ROOT,review["derivations"]["worker"]["baseline"]["path"]).read_bytes()
    after=a.regular(a.ROOT,review["derivations"]["worker"]["generated"]["path"]).read_bytes()
    for row in review["unchanged_numerical_blocks"]:
        block=b"".join(raw.splitlines(keepends=True)[row["start_line"]-1:row["end_line"]])
        a.require(len(block)==row["bytes"]and hashlib.sha256(block).hexdigest()==row["sha256"]
          and before.count(block)==after.count(block)==1,"Original numerical block changed: "+row["name"])
    a.require(sum(r["bytes"]for r in review["unchanged_numerical_blocks"])==24133,"Numerical block bytes")
    funcs=lambda t:{n.name:ast.get_source_segment(t,n)for n in ast.parse(t).body if isinstance(n,ast.FunctionDef)}
    bs=funcs(a.regular(a.ROOT,review["derivations"]["stage"]["baseline"]["path"]).read_text())
    ns=funcs(a.regular(a.ROOT,review["derivations"]["stage"]["generated"]["path"]).read_text())
    for name in review["unchanged_stage_functions"]:a.require(ns[name]==bs[name],"Lifecycle body changed: "+name)
    return {"units":out,"numerical_blocks":6,"numerical_bytes":24133,"unchanged_stage_functions":review["unchanged_stage_functions"]}

def baseline(method,on):
    m=copy.deepcopy(method)
    for key in a.AUTH:m[key]=on
    m["controller_readiness"]=on
    for key in a.ALWAYS_FALSE:m[key]=False
    return m

def authority_controls(method,prior,electrical):
    rows=[];positive=0
    for on in (False,True):
        m=baseline(method,on);a.validate_method(m,prior,electrical);positive+=1
        for key in a.AUTH+a.ALWAYS_FALSE+("controller_readiness",):
            bad=changed(m,lambda v,k=key:v.__setitem__(k,1))
            refused(rows,"typed_"+str(on)+"_"+key,lambda v=bad:a.validate_method(v,prior,electrical))
        if not on:
            with patch.dict(os.environ,env(),clear=True),patch.object(a,"methods",return_value=m):
                for prep in (True,False):refused(rows,"disabled_"+str(prep),lambda p=prep:a.authorize(p))
        else:
            with patch.dict(os.environ,env(),clear=True),patch.object(a,"methods",return_value=m):
                a.authorize(True);a.authorize(False);positive+=2
    m=baseline(method,True)
    faults=[("producer_run",lambda v:v.__setitem__("producer_run",40830441311)),
      ("producer_source",lambda v:v.__setitem__("producer_source","0"*40)),
      ("wrong_branch",lambda v:v.__setitem__("branch","codex/cdr-width-loaded-execution-unit")),
      ("old_source_binding",lambda v:v.__setitem__("original_executed_source","0"*40)),
      ("receipt_binding",lambda v:v.__setitem__("current_RC_receipt_sha256","0"*64)),
      ("old_budget",lambda v:v["execution_policy"].__setitem__("each_loaded_case_seconds",3600)),
      ("parallelism",lambda v:v["execution_policy"].__setitem__("max_parallel",3)),
      ("missing_inherited",lambda v:v["protected_sha256"].pop(next(iter(prior["protected_sha256"])))),
      ("missing_receipt",lambda v:v["protected_sha256"].pop(a.RECEIPT)),
      ("missing_new_source",lambda v:v["protected_sha256"].pop("scripts/cloud_cdr_drain_m1_loaded.py"))]
    faults += [(key,lambda v,k=key:v.__setitem__(k,True))for key in a.ALWAYS_FALSE]
    for name,mutate in faults:
        bad=changed(m,mutate);refused(rows,name,lambda v=bad:a.validate_method(v,prior,electrical))
    for key,value in (("GITHUB_REF","refs/heads/main"),("GITHUB_RUN_ATTEMPT","2"),("GITHUB_EVENT_NAME","push"),
      ("RUNNER_ENVIRONMENT","self-hosted"),("GITHUB_SHA","bad")):
        e=env();e[key]=value;refused(rows,"context_"+key,lambda v=e:a.context(v))
    a.context(env());positive+=1
    return {"positive":positive,"refusal":len(rows),"cases":rows,"native_authority_granted_by_test":False}

def report_controls(d):
    rows=[];a.validate_reports(d)
    # Every complete immutable required JSON is checked, not merely a success label.
    for name in a.REQUIRED:
        bad=changed(d,lambda v,n=name:v[n].__setitem__("synthetic_tamper",True))
        refused(rows,"authenticated_report_"+name,lambda v=bad:a.validate_reports(v))
    cfg=a.descriptor();co=d["direct/composition.json"]
    a.validate_targets(co,cfg)
    for label,mutate in (
      ("wrong_node",lambda v:v["device_records"][2]["terminals"][0].__setitem__("node","w_stale")),
      ("wrong_partition",lambda v:v["device_records"][2]["terminals"][0].__setitem__("native_cluster",999)),
      ("missing_device",lambda v:v["device_records"].pop(2)),
      ("changed_parameter",lambda v:v["device_records"][2]["parameters"].__setitem__("w","64u")),
      ("extra_target",lambda v:v["device_records"].append(copy.deepcopy(v["device_records"][2])))):
        bad=changed(co,mutate);refused(rows,label,lambda v=bad:a.validate_targets(v,cfg))
    return {"positive":2,"refusal":len(rows),"cases":rows,"native_payload_acquired":False}

def live_controls(d):
    values=[d[n]for n in ("run.json","jobs.json","release.json","tag-ref.json")]
    a.validate_live(*values,d);rows=[]
    faults=[
      ("run_source",lambda v:v[0].__setitem__("head_sha","0"*40)),
      ("run_old",lambda v:v[0].__setitem__("id",40830441311)),
      ("run_failure",lambda v:v[0].__setitem__("conclusion","failure")),
      ("run_attempt",lambda v:v[0].__setitem__("run_attempt",2)),
      ("job_missing",lambda v:v[1]["jobs"].pop()),
      ("job_failed",lambda v:v[1]["jobs"][0].__setitem__("conclusion","failure")),
      ("step_failed",lambda v:v[1]["jobs"][0]["steps"][0].__setitem__("conclusion","failure")),
      ("asset_missing",lambda v:v[2]["assets"].pop()),
      ("asset_digest",lambda v:v[2]["assets"][0].__setitem__("digest","sha256:"+"0"*64)),
      ("asset_size",lambda v:v[2]["assets"][0].__setitem__("size",1)),
      ("release_source",lambda v:v[2].__setitem__("target_commitish","0"*40)),
      ("tag_source",lambda v:v[3]["object"].__setitem__("sha","0"*40))]
    for name,mutate in faults:
        bad=changed(values,mutate);refused(rows,name,lambda v=bad:a.validate_live(*v,d))
    return {"positive":1,"refusal":len(rows),"cases":rows,"assets":19,"jobs":4}

def restored_controls(method,prior,electrical,d):
    full=a.full_map(d);archive={"regular_members":2680,"full_inventory_verified":True,
      "complete_member_hashes":{n:{"sha256":h}for n,h in full.items()}}
    live={"actions/runs/"+str(a.RUN):d["run.json"],"actions/runs/"+str(a.RUN)+"/attempts/1/jobs?per_page=100":d["jobs.json"],
      "releases/"+str(a.RELEASE):d["release.json"],"git/ref/tags/"+a.TAG:d["tag-ref.json"]}
    rows=[];positive=[]
    def reserve(group,e):
        tag,head=a.release.context(group,e)
        return {"tag":tag,"tested_source":head,"release_id":100+a.POLICY["groups"].index(group),
          "externally_reserved":True,"creation_attempted":False,"target_verified":True,"assets_overwritten":False}
    for prep in (True,False):
        calls=[];m=baseline(method,True)
        def methods():calls.append("methods");return a.validate_method(m,prior,electrical)
        def guard():calls.append("source");return d
        def waiting(group,e):calls.append("reserve:"+group);return reserve(group,e)
        def api(path):calls.append("api:"+path);return copy.deepcopy(live[path])
        def acquire(out,docs,info):
            calls.append("acquire");a.require(docs is d and info==d["release.json"],"Acquisition wrong metadata")
            return copy.deepcopy(archive)
        def verify(bundle,docs):calls.append("verify");return {"explicit_synthetic_planes":True},{"synthetic":True}
        with tempfile.TemporaryDirectory()as temp,patch.dict(os.environ,env(),clear=True),patch.object(a,"methods",methods),           patch.object(a,"source_guard",guard),patch.object(a,"wait",waiting),patch.object(a.release,"api",api),           patch.object(a,"acquire_and_extract",acquire),patch.object(a,"verify_bundle",verify):
            out=Path(temp);view=a.restore(out,prep)
            a.require(len(view)==6 and view[0]==d["direct/MIM-precision-result.json"]
              and view[2]==out/"current-mim-bundle"/a.MODEL_MEMBER and view[3]==d["direct/composition.json"]
              and view[4]=={"explicit_synthetic_planes":True}and view[5]==a.plane_proof(d),"Six-tuple changed")
            a.require(calls==["methods","source"]+["reserve:"+n for n in a.POLICY["groups"]]+
              ["api:"+n for n in live]+["acquire","verify","methods"],"Actual restore order changed")
            positive.append({"prepare":prep,"actual_restore":True,"full_metadata_members":2680,"native_payload_I_O":"synthetic acquisition and bundle verification only"})
            primary=OSError("synthetic transport primary")
            with patch.object(a,"acquire_and_extract",side_effect=primary):
                try:a.restore(out,prep)
                except OSError as error:a.require(error is primary,"Transport primary replaced")
                else:raise AssertionError("Transport failure lost")
            rows.append({"name":"transport_"+str(prep),"primary_preserved":True})
            with patch.object(a,"wait",side_effect=AssertionError("synthetic missing reservation")),patch.object(a,"acquire_and_extract")as acquisition:
                refused(rows,"missing_reservation_"+str(prep),lambda:a.restore(out,prep));a.require(not acquisition.called,"Acquired before reservations")
            bad_live=copy.deepcopy(live);bad_live["actions/runs/"+str(a.RUN)]["head_sha"]="0"*40
            with patch.object(a.release,"api",lambda p:bad_live[p]),patch.object(a,"acquire_and_extract")as acquisition:
                refused(rows,"live_source_"+str(prep),lambda:a.restore(out,prep));a.require(not acquisition.called,"Acquired bad producer")
            (out/"current-mim-bundle").mkdir()
            refused(rows,"occupied_"+str(prep),lambda:a.restore(out,prep))
    remote=a.validate_live(*[d[n]for n in ("run.json","jobs.json","release.json","tag-ref.json")],d)
    for name,mutate in (("old6647",lambda v:v.__setitem__("regular_members",6647)),
      ("missing_member",lambda v:v["complete_member_hashes"].pop(a.MODEL_MEMBER)),
      ("raw_as_summary",lambda v:v["complete_member_hashes"]["result.json"].__setitem__("sha256",a.SUMMARY_SHA))):
        bad=changed(archive,mutate);refused(rows,name,lambda v=bad:a.loaded_view(Path("/synthetic"),d,v,remote,None))
    # Actual finalizer API root convention; these THREE bytes are synthetic,
    # never asserted to be a real2680-member restoration.
    with tempfile.TemporaryDirectory()as temp:
        root=Path(temp);bundle=root/"current-mim-bundle";bundle.mkdir()
        expected={}
        for name,raw in {"a.json":b"{}\n","empty.stderr":b"","sub/file":b"synthetic"}.items():
            p=bundle/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);expected[name]=hashlib.sha256(raw).hexdigest()
        with patch.object(a,"expected_files",return_value=expected):
            a.require(a.verify_restored(root)=={"files":3,"all_hashes_unchanged":True,"exact_inventory":True},"Finalizer bundle path")
            (bundle/"extra").write_bytes(b"x");refused(rows,"extra_synthetic_member",lambda:a.verify_restored(root))
    return {"positive":3,"refusal":len(rows),"cases":positive+rows,"authentic_metadata_members":2680,"native_restore_qualified":False}

def result_controls(d):
    import cdr_width_loaded_admission as prior_a
    import cdr_width_loaded_result as prior_g
    historical_report,fault=historical.historical_controls(prior_a,prior_g)
    fault=copy.deepcopy(fault);fault["source_head"]=os.environ["GITHUB_SHA"]
    fault["current_saved_input_integrity"]={"files":2680,"all_hashes_unchanged":True,"exact_inventory":True}
    fault.update(terminal_finalization_complete=True,terminal_inventory_complete=True,terminal_save_attempted=True,
      terminal_errors=[],active_primary_exception_before_terminal=None)
    fault["terminal_actions"]=[{"action":n,"completed":True}for n in("protected_sources","complete_saved_inputs","preserve_preexisting_atomic_fragment","complete_output_inventory")]
    full=a.full_map(d);archive={"regular_members":2680,"full_inventory_verified":True,"complete_member_hashes":{n:{"sha256":h}for n,h in full.items()}}
    remote=a.validate_live(*[d[n]for n in("run.json","jobs.json","release.json","tag-ref.json")],d)
    view=a.loaded_view(Path("/synthetic-not-restored"),d,archive,remote,None)
    fault["composition_source"]=view[1];fault["native_plane_source"]=view[5]
    interface=d["direct/composition.json"]["interface"];external={n:"0"if n in("avss","sub","wire_cref")else n for n in interface}
    fault["binding"]["interface"]=external;fault["binding"]["ports"]=[external[n]for n in interface]
    prep=copy.deepcopy(fault);prep.update(case="nominal_early",status=g.PREPARATION_PASS,transient_executed=False)
    rows=[]
    with patch.object(a,"source_guard",return_value=d):
        g.validate(prep,"nominal_early",True,0);g.validate(fault,"clock_stopped",False,0,prep)
        faults=[
          ("old_RC",lambda v:v["composition_source"].__setitem__("run",40830441311)),
          ("old_full_count",lambda v:v["composition_source"]["full_archive"].__setitem__("regular_members",6647)),
          ("raw_summary",lambda v:v["composition_source"].__setitem__("raw_result_sha256",a.SUMMARY_SHA)),
          ("old_graph",lambda v:v["composition_source"].__setitem__("current_graph_run",40808550817)),
          ("wrong_drain",lambda v:v["composition_source"]["fresh_target_terminal_bindings"]["T003_D"]["terminals"][0].__setitem__("node","w_stale")),
          ("old_planes",lambda v:v["native_plane_source"].__setitem__("native_planes_sha256","0"*64)),
          ("lost_fault",lambda v:v.__setitem__("actual_fault_detected",False)),
          ("OFF_flags",lambda v:v.__setitem__("native_flags_verified",123)),
          ("OP_limit",lambda v:v.__setitem__("zero_source_op_maximum",1e-9)),
          ("failed_terminal",lambda v:v.__setitem__("terminal_finalization_complete",False)),
          ("port_order",lambda v:v["binding"]["ports"].reverse())]
        for name,mutate in faults:
            bad=changed(fault,mutate);refused(rows,name,lambda v=bad:g.validate(v,"clock_stopped",False,0,prep))
        refused(rows,"missing_same_run_preparation",lambda:g.validate(fault,"clock_stopped",False,0,None))
    return {"positive":2,"refusal":len(rows),"cases":rows,"historical":historical_report,
      "synthetic_current_report":True,"actual_current_simulation_claimed":False}

def actual_publication_controls():
    # Reuse unchanged fixture CODE; only module namespaces and test context differ.
    # Real new stage/publisher/pack/finalizer run. Child/cloud/storage inputs remain
    # the existing explicitly synthetic fixture. No production globals are patched.
    names=("records","archive_check","fixture","controls")
    scope=dict(publication_controls.__dict__)
    scope.update(a=a,s=s,execution=types.SimpleNamespace(env=env))
    for name in names:
        fn=getattr(publication_controls,name)
        scope[name]=types.FunctionType(fn.__code__,scope,fn.__name__,fn.__defaults__,fn.__closure__)
        a.require(scope[name].__code__ is fn.__code__,"Publication fixture code changed")
    report=scope["controls"]()
    a.require(report["publication_cases"]==15 and report["actual_lifecycle_cases"]==2
      and report["actual_pack_and_publisher"]is True,"Inherited production publication coverage")
    return report

def controls():
    m=a.methods();d=a.source_guard()
    prior=json.loads(a.regular(a.ROOT,a.PRIOR).read_bytes());electrical=json.loads(a.regular(a.ROOT,a.ELECTRICAL_PRIOR).read_bytes())
    return {"status":STATUS,"derivation":derivation_controls(),"authority":authority_controls(m,prior,electrical),
      "reports":report_controls(d),"live":live_controls(d),"restore":restored_controls(m,prior,electrical,d),
      "result":result_controls(d),"publication":actual_publication_controls(),
      "source_controls_only":True,"native_executed":False,"native_acquisition_performed":False,
      "numerical_worker_imported":False,"numerical_worker_executed":False,"simulator_executed":False,
      "electrical_accepted":False,"physical_accepted":False,"full_phy_accepted":False}

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);args=p.parse_args()
    report={"status":"FAIL_DRAIN_M1_LOADED_SOURCE_CONTROLS","source_controls_only":True,"native_executed":False,
      "electrical_accepted":False,"physical_accepted":False,"full_phy_accepted":False}
    primary=None
    try:
        ctx=a.context();m=a.methods();a.require(m["source_controls_authorized"]is True,"New loaded source controls disabled")
        report=controls();report["current_context"]={**ctx,"source_controls_only":True,"native_executed":False}
    except BaseException as error:primary=error;report.update(error=repr(error),traceback=traceback.format_exc())
    finally:
        raw=a.encoded(report)
        try:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(raw)
        except BaseException as error:
            if primary is None:primary=error
        try:print(raw.decode(),end="",flush=True)
        except BaseException as error:
            if primary is None:primary=error
    if primary is not None:raise primary

if __name__=="__main__":main()
