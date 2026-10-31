#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual hosted source controls for the distinct VI-only execution adapter."""
import ast,base64,copy,hashlib,inspect,json,os,traceback,types
from pathlib import Path
from unittest.mock import patch
import cdr_eight_drain_vi_bias_off_admission_v1 as a
import cloud_cdr_eight_drain_vi_bias_off_stage_v1 as stage
import check_cdr_eight_drain_storage_v1 as proven
ROOT=a.ROOT
QUALIFIED=("context","method","reservations","source_prerequisite","derivation","source_integrity","storage_regression")
def require(v,msg):
    if not v:raise AssertionError(msg)
def encoded(x):return(json.dumps(x,sort_keys=True,indent=2)+"\n").encode()
def digest(b):return hashlib.sha256(b).hexdigest()
def refused(fn,label):
    try:fn()
    except (AssertionError,KeyError,ValueError,TypeError):return label
    raise AssertionError("Accepted refusal fixture: "+label)
def env(prepare=False):
    return dict(GITHUB_ACTIONS="true",RUNNER_ENVIRONMENT="github-hosted",RUNNER_OS="Linux",
      GITHUB_REPOSITORY="Melihakbulut221/nssoc",GITHUB_REF="refs/heads/"+a.BRANCH,
      GITHUB_WORKFLOW_REF="Melihakbulut221/nssoc/.github/workflows/cloud-evidence-summary.yml@refs/heads/"+a.BRANCH,
      GITHUB_EVENT_NAME="workflow_dispatch",GITHUB_RUN_ATTEMPT="1",GITHUB_SHA="a"*40,GITHUB_RUN_ID="12345",
      APPROVED_SOURCE="a"*40,REQUESTED_MODE="vi-bias-off",REQUESTED_CASE="vi_bias_off",
      GITHUB_JOB="prepare"if prepare else"vi-bias-off",LOADED_CASE="nominal_early"if prepare else"vi_bias_off",
      PREPARE_ONLY="true"if prepare else"false")
def context_controls():
    rows=[];positive=[]
    for prepare in (False,True):
        e=env(prepare);case=e["LOADED_CASE"]
        positive.append(a.execution_context(case,prepare,e))
        changes={"GITHUB_ACTIONS":"false","RUNNER_ENVIRONMENT":"self-hosted","RUNNER_OS":"Windows",
          "GITHUB_REPOSITORY":"other/repo","GITHUB_REF":"refs/heads/main","GITHUB_WORKFLOW_REF":"other",
          "GITHUB_EVENT_NAME":"push","GITHUB_RUN_ATTEMPT":"2","GITHUB_SHA":"b"*40,"GITHUB_RUN_ID":"0",
          "APPROVED_SOURCE":"b"*40,"REQUESTED_MODE":"controls","REQUESTED_CASE":"nominal_early",
          "GITHUB_JOB":"source-controls","LOADED_CASE":"constant_one","PREPARE_ONLY":"false"if prepare else"true"}
        for k,v in changes.items():
            wrong={**e,k:v};rows.append(refused(lambda:a.execution_context(case,prepare,wrong),str(prepare)+":"+k))
        for wrongcase in a.CASES:
            if wrongcase!=case:rows.append(refused(lambda:a.execution_context(wrongcase,prepare,e),str(prepare)+":"+wrongcase))
        rows.append(refused(lambda:a.execution_context(case,1,e),"nonboolean preparation"))
    return dict(positive=positive,refusals=rows)
def method_controls(m):
    prior=json.loads((ROOT/a.PRIOR).read_bytes());electrical=json.loads((ROOT/a.ELECTRICAL_PRIOR).read_bytes())
    a.validate_method(m,prior,electrical);rows=[]
    alterations=[("native_cases",["vi_bias_off","constant_one"]),("preparation_case","vi_bias_off"),
      ("branch","codex/cdr-drain-m1-loaded-electrical"),("schema","old"),("cases",["vi_bias_off"])]
    for k,v in alterations:
        wrong=copy.deepcopy(m);wrong[k]=v
        rows.append(refused(lambda:a.validate_method(wrong,prior,electrical),k))
    wrong=copy.deepcopy(m);wrong["execution_policy"]["groups"].append("cdr-current-eight-drain-loaded-constant_one")
    rows.append(refused(lambda:a.validate_method(wrong,prior,electrical),"third reservation"))
    wrong=copy.deepcopy(m);wrong["execution_policy"]["each_loaded_case_seconds"]=7201
    rows.append(refused(lambda:a.validate_method(wrong,prior,electrical),"extended budget"))
    for name in a.VI_REQUIRED:
        wrong=copy.deepcopy(m);wrong["protected_sha256"].pop(name)
        rows.append(refused(lambda:a.validate_method(wrong,prior,electrical),"omitted "+name))
    disabled=copy.deepcopy(m)
    for k in("preparation_authorized","simulation_authorized","native_execution_authorized","controller_readiness","workflow_dispatch_authorized"):disabled[k]=False
    enabled=copy.deepcopy(m)
    for k in("preparation_authorized","simulation_authorized","native_execution_authorized","controller_readiness","workflow_dispatch_authorized"):enabled[k]=True
    for candidate in (disabled,enabled):a.validate_method(candidate,prior,electrical)
    with patch.object(a,"execution_context",return_value={}),patch.object(a,"methods",return_value=disabled):
        for phase in(False,True):rows.append(refused(lambda:a.authorize(phase),"disabled native "+str(phase)))
    with patch.object(a,"execution_context",return_value={}),patch.object(a,"methods",return_value=enabled):
        require(a.authorize(False)==enabled and a.authorize(True)==enabled,"Positive explicit authority failed")
    return dict(refusals=rows,disabled_and_enabled_method_fixtures=True,native_called=False)
def reservation_controls():
    ctx=a.context(env());receipts={}
    for i,g in enumerate(a.POLICY["groups"]):
        receipts[g]=dict(tag="cloud-results-12345-1-"+g,tested_source="a"*40,release_id=i+11,
          externally_reserved=True,creation_attempted=False,target_verified=True,assets_overwritten=False,existing_assets=[])
    a.validate_reservations(ctx,True,receipts);a.validate_reservations(ctx,False,receipts);rows=[]
    for g in receipts:
        for k,v in (("tested_source","b"*40),("tag","cloud-results-old"),("release_id",True),
          ("externally_reserved",False),("creation_attempted",True),("target_verified",False),("assets_overwritten",True)):
            bad=copy.deepcopy(receipts);bad[g][k]=v
            rows.append(refused(lambda:a.validate_reservations(ctx,True,bad),g+":"+k))
        bad=copy.deepcopy(receipts);bad[g]["existing_assets"]=[{"id":999}]
        rows.append(refused(lambda:a.validate_reservations(ctx,True,bad),g+":nonempty initial"))
    bad=copy.deepcopy(receipts);bad[a.POLICY["groups"][1]]["release_id"]=11
    rows.append(refused(lambda:a.validate_reservations(ctx,True,bad),"duplicate release"))
    bad=copy.deepcopy(receipts);bad.pop(a.POLICY["groups"][1])
    rows.append(refused(lambda:a.validate_reservations(ctx,True,bad),"missing preparation"))
    bad=copy.deepcopy(receipts);bad["extra"]=copy.deepcopy(next(iter(receipts.values())))
    rows.append(refused(lambda:a.validate_reservations(ctx,True,bad),"third release"))
    bad=copy.deepcopy(receipts);bad[a.POLICY["groups"][0]]["existing_assets"]=[{"id":999}]
    rows.append(refused(lambda:a.validate_reservations(ctx,False,bad),"VI overwrite"))
    usedprep=copy.deepcopy(receipts);usedprep[a.POLICY["groups"][1]]["existing_assets"]=[{"id":999}]
    require(a.validate_reservations(ctx,False,usedprep)["own_empty_release"]==a.POLICY["groups"][0],"Published preparation should remain usable")
    return dict(refusals=rows,positive=3,release_creation_attempted=False)
def prerequisite_controls():
    ctx=a.context(env());run=dict(id=12345,head_sha="a"*40,run_attempt=1,event="workflow_dispatch",
      workflow_id=382556685,path=".github/workflows/cloud-evidence-summary.yml")
    job=dict(id=777,name="source-controls",head_sha="a"*40,status="completed",conclusion="success",steps=[dict(conclusion="success")])
    jobs=dict(total_count=1,jobs=[job])
    report=dict(status="PASS_SINGLE_VI_SOURCE_CONTROLS_NO_NATIVE_EXECUTION",current_context=ctx,
      method_sha256=a.sha(ROOT/a.METHOD),source_controls_only=True,qualified_controls={k:True for k in QUALIFIED},
      native_executed=False,native_acquisition=False,electrical_accepted=False,physical_accepted=False,full_phy_accepted=False)
    storage=dict(status="PASS_STORAGE_SOURCE_CONTROLS_NOT_NATIVE_OR_ELECTRICAL_ACCEPTANCE",
      source="a"*40,storage=dict(count=13),native_executed=False,native_acquisition=False)
    outputs={"vi.json":encoded(report),"storage.json":encoded(storage),"vi.stdout":b"full stdout\n",
      "vi.stderr":b"","storage.stdout":b"full storage stdout\n","storage.stderr":b"",
      "checkout.json":encoded(dict(source="a"*40)),"before-checkout.json":encoded(dict(free_bytes=999))}
    def emit(records):
        lines=[]
        for n,raw in records.items():
            chunks=[raw[i:i+6000]for i in range(0,len(raw),6000)]
            lines.append("time VI_SOURCE_INDEX "+json.dumps(dict(path=n,present=True,bytes=len(raw),sha256=digest(raw),chunks=len(chunks))))
            for i,b in enumerate(chunks):lines.append("time VI_SOURCE_CHUNK "+json.dumps(dict(path=n,index=i,base64=base64.b64encode(b).decode())))
        return("\n".join(lines)+"\n").encode()
    log=emit(outputs);a.validate_source_controls(ctx,run,jobs,log);rows=[]
    for k,v in(("head_sha","b"*40),("id",12346),("run_attempt",2),("event","push"),("workflow_id",1),("path","wrong.yml")):
        bad={**run,k:v};rows.append(refused(lambda:a.validate_source_controls(ctx,bad,jobs,log),"run "+k))
    for k,v in(("head_sha","b"*40),("status","in_progress"),("conclusion","failure"),("steps",[dict(conclusion="skipped")])):
        bad=copy.deepcopy(jobs);bad["jobs"][0][k]=v
        rows.append(refused(lambda:a.validate_source_controls(ctx,run,bad,log),"job "+k))
    bad=copy.deepcopy(jobs);bad["total_count"]=2
    rows.append(refused(lambda:a.validate_source_controls(ctx,run,bad,log),"truncated job inventory"))
    for name in outputs:
        bad={n:b for n,b in outputs.items()if n!=name}
        rows.append(refused(lambda:a.validate_source_controls(ctx,run,jobs,emit(bad)),"missing "+name))
    for k,v in(("current_context",{**ctx,"source":"b"*40}),("method_sha256","0"*64),("native_executed",True),("source_controls_only",False)):
        bad={**outputs,"vi.json":encoded({**report,k:v})}
        rows.append(refused(lambda:a.validate_source_controls(ctx,run,jobs,emit(bad)),"report "+k))
    for k in QUALIFIED:
        bad=copy.deepcopy(report);bad["qualified_controls"][k]=1
        records={**outputs,"vi.json":encoded(bad)}
        rows.append(refused(lambda:a.validate_source_controls(ctx,run,jobs,emit(records)),"nonboolean "+k))
    corrupt=log.replace(digest(outputs["vi.json"]).encode(),b"0"*64)
    rows.append(refused(lambda:a.validate_source_controls(ctx,run,jobs,corrupt),"bad stream SHA"))
    rows.append(refused(lambda:a.validate_source_controls(ctx,run,jobs,log+log),"duplicate stream"))
    return dict(refusals=rows,full_stream_provenance=True,native_called=False)
def derivation_controls():
    original=(ROOT/"scripts/cloud_cdr_current_eight_drain_loaded.py").read_text()
    expected=original.replace("import cdr_current_eight_drain_loaded_admission as current_inputs",
      "import cdr_eight_drain_vi_bias_off_admission_v1 as current_inputs")
    expected=expected.replace("scripts/cdr-current-eight-drain-loaded-methods.json",a.METHOD)
    needle="    assert os.environ.get('GITHUB_ACTIONS')=='true'\n"
    require(expected.count(needle)==1,"Original worker insertion point changed")
    expected=expected.replace(needle,"    current_inputs.authorize_case(args.case,args.prepare_only)\n"+needle)
    require((ROOT/stage.WORKER).read_text()==expected,"Unexpected worker/numerical change")
    original_result=(ROOT/"scripts/cdr_current_eight_drain_loaded_result.py").read_text()
    require((ROOT/"scripts/cdr_eight_drain_vi_bias_off_result_v1.py").read_text()==original_result.replace(
      "import cdr_current_eight_drain_loaded_admission as a","import cdr_eight_drain_vi_bias_off_admission_v1 as a"),"Original electrical result gates changed")
    def functions(path):
        s=(ROOT/path).read_text();lines=s.splitlines(keepends=True)
        return{n.name:"".join(lines[n.lineno-1:n.end_lineno])for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    old=functions("scripts/cloud_cdr_eight_drain_storage_stage_v1.py");new=functions("scripts/cloud_cdr_eight_drain_vi_bias_off_stage_v1.py")
    require(set(old)==set(new),"Stage function inventory changed")
    unchanged=[]
    for name in old:
        if name in("context","preflight","main"):continue
        expected=old[name]
        if name=="storage":expected=expected.replace('"native_execution_authorized":False','"storage_measurement_only":True,"native_authorization_asserted_by_this_record":False')
        require(new[name]==expected,"Proven storage/finalizer changed: "+name);unchanged.append(name)
    olda=functions("scripts/cdr_current_eight_drain_loaded_admission.py");newa=functions("scripts/cdr_eight_drain_vi_bias_off_admission_v1.py")
    for name in olda:
        if name in("context","validate_method","authorize","reservation_gate"):continue
        require(olda[name]==newa[name],"Native admission/model/target function changed: "+name)
    review=json.loads((ROOT/"docs/evidence/cdr-current-eight-drain-loaded-source-review-20261031.json").read_bytes())
    actual=(ROOT/stage.WORKER).read_bytes();source=original.encode();rows=[]
    for block in review["unchanged_numerical_blocks"]:
        # Frozen block coordinates describe the historical electrical worker,
        # so locate its exact authenticated span in the existing current worker.
        pin=block["sha256"];size=block["bytes"]
        lines=source.splitlines(keepends=True);matches=[]
        for i in range(len(lines)):
            b=b""
            for line in lines[i:]:
                b+=line
                if len(b)>=size:break
            if len(b)==size and digest(b)==pin:matches.append(b)
        require(len(matches)==1 and actual.count(matches[0])==1,"Frozen numerical block changed: "+block["name"])
        rows.append(dict(name=block["name"],bytes=size,sha256=pin))
    require(sum(r["bytes"]for r in rows)==24133 and len(rows)==6,"Numerical block census changed")
    original_publication=(ROOT/"scripts/cdr_width_loaded_publication.py").read_text()
    require((ROOT/"scripts/cdr_eight_drain_vi_bias_off_publication_v1.py").read_text()==original_publication.replace(
      '    summary["outputs"]=s.inventory(out)\n    s.storage(ctx,"publication")\n',
      '    s.storage(ctx,"publication")\n    summary["outputs"]=s.inventory(out)\n'),"Unexpected publication predicate change")
    return dict(worker_exact_transform=True,result_exact_transform=True,proven_stage_functions=unchanged,numerical_blocks=rows)
def new_stage_storage_controls():
    text=inspect.getsource(proven.storage_controls)
    start=text.index("    try:stage.main()\n");end=text.index("    return dict(",start)
    text=text[:start]+text[end:]
    scope={**proven.storage_controls.__globals__,"stage":stage}
    exec(compile(text,"<hosted-derived-storage-fixtures>","exec"),scope)
    report=scope["storage_controls"]()
    require(report["count"]==12,"Complete storage/lifecycle controls absent")
    return report

def real_journal_publication_controls():
    original=proven.frozen.publication_controls
    text=inspect.getsource(original.fixture)
    old='        stack.enter_context(patch.object(s,"storage",lambda ctx,label:\n          {"checkpoint":label,"free_bytes":64*1024**3,"required_bytes":16*1024**3}))\n'
    require(text.count(old)==1,"Original mocked storage fixture changed")
    text=text.replace(old,'        stack.enter_context(patch.object(s.shutil,"disk_usage",return_value=types.SimpleNamespace(free=64*1024**3)))\n')
    broad='                stack.enter_context(patch("builtins.print",side_effect=OSError("synthetic fallback emission failure")))\n'
    require(text.count(broad)==1,"Original final-fallback fixture changed")
    narrow='''                real_print=print
                def fail_only_receipt_fallback(*args,**kwargs):
                    if args and isinstance(args[0],str)and '"unsaved_loaded_publication_receipt"'in args[0]:
                        raise OSError("synthetic fallback emission failure")
                    return real_print(*args,**kwargs)
                stack.enter_context(patch("builtins.print",side_effect=fail_only_receipt_fallback))
'''
    text=text.replace(broad,narrow)
    scope={**original.__dict__,"a":a,"s":stage,"p":stage.publication,"types":types,
      "execution":types.SimpleNamespace(env=lambda:env(True))}
    for name in("records","archive_check","controls"):
        fn=getattr(original,name);scope[name]=types.FunctionType(fn.__code__,scope,fn.__name__,fn.__defaults__,fn.__closure__)
    exec(compile(text,"<hosted-real-storage-publication-fixtures>","exec"),scope)
    archive=scope["archive_check"];seen=[]
    def check(ctx,proof):
        summary,manifest=archive(ctx,proof)
        name="storage-checks/publication.json"
        require(name in proof["complete_outputs"],"Real publication journal omitted from archive")
        row=json.loads((ctx["output"]/name).read_bytes())
        require(row["checkpoint"]=="publication"and row["free_bytes"]==64*1024**3
          and row["storage_measurement_only"]is True and row["native_authorization_asserted_by_this_record"]is False,"Actual journal scope changed")
        seen.append(name);return summary,manifest
    scope["archive_check"]=check
    actual_context=a.context
    with patch.object(a,"context",lambda env=None:actual_context(os.environ if env is None else env)):
        report=scope["controls"]()
    require((report["publication_cases"],report["actual_lifecycle_cases"])==(15,2)and len(seen)>=14,"Real journal production coverage incomplete")
    return dict(report=report,full_journal_archive_checks=len(seen),native_payload_synthetic=True,storage_function_mocked=False)

def main():
    out=ROOT/"hw/soc/out/cdr-eight-drain-single-vi-source-controls";out.mkdir(parents=True,exist_ok=False)
    report=dict(status="FAIL_SINGLE_VI_SOURCE_CONTROLS",current_context=None,source_controls_only=True,
      native_executed=False,native_acquisition=False,electrical_accepted=False,physical_accepted=False,full_phy_accepted=False,
      qualified_controls={k:False for k in QUALIFIED})
    primary=None
    try:
        report["current_context"]=a.context()
        require(os.environ["GITHUB_JOB"]=="source-controls","Actual source job required")
        m=a.methods();report["method_sha256"]=a.sha(ROOT/a.METHOD)
        report["source_integrity"]=dict(protected_files=len(m["protected_sha256"]),source=os.environ["GITHUB_SHA"])
        report["qualified_controls"]["source_integrity"]=True
        for name,fn in(("context",context_controls),("method",lambda:method_controls(m)),("reservations",reservation_controls),
          ("source_prerequisite",prerequisite_controls),("derivation",derivation_controls)):
            report[name]=fn();report["qualified_controls"][name]=True
        existing=json.loads((ROOT/"hw/soc/out/cdr-eight-drain-storage-source-controls/result.json").read_bytes())
        require(existing["status"]=="PASS_STORAGE_SOURCE_CONTROLS_NOT_NATIVE_OR_ELECTRICAL_ACCEPTANCE"
          and existing["source"]==os.environ["GITHUB_SHA"]and existing["storage"]["count"]==13
          and existing["native_executed"]is False and existing["native_acquisition"]is False,"Frozen storage regression absent")
        report["storage_regression"]=dict(frozen_report_sha256=a.sha(ROOT/"hw/soc/out/cdr-eight-drain-storage-source-controls/result.json"))
        report["storage_regression"]["candidate"]=new_stage_storage_controls()
        report["storage_regression"]["publication"]=real_journal_publication_controls()
        report["qualified_controls"]["storage_regression"]=True
        report["status"]="PASS_SINGLE_VI_SOURCE_CONTROLS_NO_NATIVE_EXECUTION"
    except BaseException as error:
        primary=error;report.update(error=repr(error),traceback=traceback.format_exc())
    finally:
        raw=encoded(report);(out/"result.json").write_bytes(raw);print(raw.decode(),end="",flush=True)
    if primary is not None:raise primary
if __name__=="__main__":main()
