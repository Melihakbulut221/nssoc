#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Separate, fail-closed current-width loaded execution admission.

No execution method ships in this unit. Immutable input admission and saved
source-control receipts qualify inputs/source only, never current execution.
"""
import copy,hashlib,json,os,re
from pathlib import Path
import cdr_width_loaded_admission as inputs
from wait_cloud_tested_source_release import wait

ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/cdr-width-loaded-execution-unit"
METHOD="scripts/cdr-width-loaded-execution-methods.json"
INPUT_METHOD="scripts/cdr-width-loaded-admission-methods.json"
INPUT_METHOD_SHA="1ae0bc1d2126d6310bbe6f27d7f424b8f8ac51989d9abcb5a99f5dbc968063b4"
QUALIFIED_METHOD="scripts/cdr-width-loaded-worker-source-methods.json"
QUALIFIED_METHOD_SHA="c9dd549439b98c69265f36ea419cf9d05fe67dba321ce69d60de73094dab2c3c"
QUALIFIED_COUNT=1264
WORKER="scripts/cloud_cdr_width_loaded.py"
QUALIFIED_WORKER_SHA="aa04bf95d55fb3b26945018278e060488183fdbd94997f971cb8562a9fc95b0c"
EXECUTION_WORKER_SHA="ebf92a9842280587a437de161425f49f6ce4a82c9d76a0ce2532075d0e309bf5"
WORKER_EDITS=[('import cdr_width_loaded_admission as current_inputs', 'import cdr_width_loaded_execution_admission as current_inputs'), ("ROOT/'scripts/cdr-width-loaded-methods.json'", "ROOT/'scripts/cdr-width-loaded-execution-methods.json'")]
SOURCE_RUN=40884116773
SOURCE_HEAD="c60f70029d57cb46365c54e7f4ccd428acc21d18"
SOURCE_PREFIX="docs/evidence/cdr-width-loaded-worker-source-terminal-40884116773/"
SOURCE_RECEIPT=SOURCE_PREFIX+"receipt.json"
SOURCE_RECEIPT_SHA="899dac1bd0a7926be3daaaa43cea50c883ea9b2c0091a72793395e4fa7d30389"
SOURCE_REQUIRED={'docs/evidence/cdr-width-loaded-worker-source-terminal-40884116773/123483140490.job.json': {'bytes': 3217, 'sha256': 'f79a334a5bf0bd104446ed78ee25f85ded435631b51d5f8573a5ebfc09aab798'}, 'docs/evidence/cdr-width-loaded-worker-source-terminal-40884116773/123483140490.job.log': {'bytes': 57881, 'sha256': '3153271500ca66f17526ec637963fc6538e2d27cf2cb68d9d42e4891cd80aab7'}, 'docs/evidence/cdr-width-loaded-worker-source-terminal-40884116773/123483490882.job.json': {'bytes': 1960, 'sha256': '3904ff3c1f3160c9f19bf174ac9ca2ee1af4b92f0ae34ea0c5aa69615fc712d1'}, 'docs/evidence/cdr-width-loaded-worker-source-terminal-40884116773/123483490882.job.log': {'bytes': 7522, 'sha256': '2b1a7d706d286dcdeea05b01bd52ce1cd3792aa0c7a48ba63f83777fe056f7f7'}, 'docs/evidence/cdr-width-loaded-worker-source-terminal-40884116773/artifacts.json': {'bytes': 1843, 'sha256': 'd333f0e1af7a84ca80788873e7e5d9b0d398c56f6fa32413110944ffe7febad9'}, 'docs/evidence/cdr-width-loaded-worker-source-terminal-40884116773/controls/context.json': {'bytes': 249, 'sha256': '36067a9729f7bbd702b6c64209eaf8025a053d8dc40c4e286efd89ff3598f751'}, 'docs/evidence/cdr-width-loaded-worker-source-terminal-40884116773/controls/index.json': {'bytes': 755, 'sha256': '018a5855c6171cb4bdc2f6cc2bf4985c106039b7df34bfdd474b20557e68e7f9'}, 'docs/evidence/cdr-width-loaded-worker-source-terminal-40884116773/controls/result.json': {'bytes': 10628, 'sha256': '0da7249d22ad2da488f7c5698dc235ac93b30a84c25e143b0f04bad55c0878f3'}, 'docs/evidence/cdr-width-loaded-worker-source-terminal-40884116773/controls/stderr.log': {'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'docs/evidence/cdr-width-loaded-worker-source-terminal-40884116773/controls/stdout.log': {'bytes': 10628, 'sha256': '0da7249d22ad2da488f7c5698dc235ac93b30a84c25e143b0f04bad55c0878f3'}, 'docs/evidence/cdr-width-loaded-worker-source-terminal-40884116773/jobs.json': {'bytes': 5858, 'sha256': '01a60f310303841fb7820cbb90def20cc467d0410509f0ae5c99fb0cba1dacd5'}, 'docs/evidence/cdr-width-loaded-worker-source-terminal-40884116773/run.json': {'bytes': 14408, 'sha256': '7f65da4c3d217f978eb05ff29aafd32314739c57cf1f3eae01f42c75b49cab87'}, 'docs/evidence/cdr-width-loaded-worker-source-terminal-40884116773/receipt.json': {'bytes': 14151, 'sha256': '899dac1bd0a7926be3daaaa43cea50c883ea9b2c0091a72793395e4fa7d30389'}}
NEW_REQUIRED=('scripts/cdr_width_loaded_execution_admission.py', 'scripts/cloud_cdr_width_loaded_stage.py', 'scripts/check_cdr_width_loaded_execution.py', 'docs/evidence/cdr-width-loaded-execution-unit-source-review-20261029.json')
AUTH=inputs.old.AUTH
ALWAYS_FALSE=inputs.old.ALWAYS_FALSE
CASES=inputs.CASES
MODEL=inputs.MODEL
SUMMARY=inputs.SUMMARY
STAGE=inputs.STAGE
RUN=inputs.RUN
HEAD=inputs.HEAD
RELEASE=inputs.RELEASE
TAG=inputs.TAG
require=inputs.require
sha=inputs.sha
regular=inputs.regular
relative=inputs.relative
write=inputs.write
fetch=inputs.fetch
release=inputs.release
exact=inputs.exact
validate_live=inputs.validate_live
acquire_and_extract=inputs.acquire_and_extract
verify_bundle=inputs.verify_bundle
loaded_view=inputs.loaded_view
expected_files=inputs.expected_files
verify_restored=inputs.verify_restored
verify_exact_files=inputs.old.verify_exact_files

POLICY={"groups":["cdr-width-loaded-"+n for n in CASES]+["cdr-width-loaded-preparation"],
 "reserve_all_eleven_before_any_native_dependencies":True,"create_preparation_reservation_last":True,
 "preparation_seconds":1200,"each_loaded_case_seconds":7200,"max_parallel":2,
 "fail_fast":False,"automatic_retry":False}

def descriptor():
    return {"proposed_execution":copy.deepcopy(POLICY)}

def context(env=None):
    e=os.environ if env is None else env
    require(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted"
      and e.get("RUNNER_OS")=="Linux"and e.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc",
      "Current width hosted Linux context required")
    require(e.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and e.get("GITHUB_RUN_ATTEMPT")=="1",
      "Current width manual first attempt required")
    require(e.get("GITHUB_REF")=="refs/heads/"+BRANCH,"Current width execution branch required")
    require(re.fullmatch("[0-9a-f]{40}",e.get("GITHUB_SHA",""))
      and re.fullmatch("[1-9][0-9]*",e.get("GITHUB_RUN_ID","")),"Current width source/run invalid")
    return {"source":e["GITHUB_SHA"],"run_id":int(e["GITHUB_RUN_ID"]),"attempt":1}

def worker_derivation(raw):
    h=hashlib.sha256(raw).hexdigest()
    if h==QUALIFIED_WORKER_SHA:
        return {"mode":"qualified_source_only","sha256":h,"execution_adapter_installed":False}
    require(h==EXECUTION_WORKER_SHA,"Execution worker differs beyond two declared substitutions")
    text=raw.decode()
    for before,after in reversed(WORKER_EDITS):
        require(text.count(after)==1,"Execution worker substitution ambiguous")
        text=text.replace(after,before)
    require(hashlib.sha256(text.encode()).hexdigest()==QUALIFIED_WORKER_SHA,"Execution worker reverse proof failed")
    return {"mode":"exact_execution_adapter","sha256":h,"execution_adapter_installed":True,
      "literal_substitutions":2,"numerical_functions_changed":False}

def validate_method(m,prior):
    require(m["schema"]=="cdr-width-loaded-execution-v1"and m["branch"]==BRANCH,
      "Current width execution method identity changed")
    inputs.old.validate_authorizations(m)
    require(m["controller_readiness"]is (m["preparation_authorized"]or m["simulation_authorized"]),
      "Current width controller readiness mismatch")
    require(not m["workflow_dispatch_authorized"]or m["source_controls_authorized"],
      "Dispatch requires current source controls")
    require(type(m["producer_run"])is int and m["producer_run"]==RUN and m["producer_source"]==HEAD,
      "Current width producer changed")
    exact(m["execution_policy"],POLICY,"Original ten-case execution policy changed")
    require(m["qualified_worker_method"]==QUALIFIED_METHOD
      and m["qualified_worker_method_sha256"]==QUALIFIED_METHOD_SHA
      and m["qualified_worker_source_run"]==SOURCE_RUN
      and m["qualified_worker_source_receipt_sha256"]==SOURCE_RECEIPT_SHA,
      "Qualified worker source proof changed")
    protected=m["protected_sha256"];old=prior["protected_sha256"]
    require(len(old)==QUALIFIED_COUNT,"Qualified worker source count changed")
    require(all(protected.get(n)==h for n,h in old.items()if n!=WORKER),
      "Inherited immutable loaded source protection removed")
    require(protected.get(WORKER)in (QUALIFIED_WORKER_SHA,EXECUTION_WORKER_SHA),
      "Unqualified loaded worker pin")
    if m["preparation_authorized"]or m["simulation_authorized"]:
        require(protected[WORKER]==EXECUTION_WORKER_SHA,"Native execution requires exact worker adapter")
    require(protected.get(INPUT_METHOD)==INPUT_METHOD_SHA
      and protected.get(QUALIFIED_METHOD)==QUALIFIED_METHOD_SHA,"Historical method pins omitted")
    require(all(protected.get(n)==s["sha256"]for n,s in SOURCE_REQUIRED.items()),
      "Complete worker source proof unprotected")
    require(all(n in protected for n in NEW_REQUIRED),"Execution source pins omitted")
    return m

def methods():
    # Authenticate disabled input authority unchanged; never override authorize().
    require(sha(regular(ROOT,INPUT_METHOD))==INPUT_METHOD_SHA,"Immutable input method changed")
    im=inputs.methods()
    require(all(im[k]is False for k in ("workflow_dispatch_authorized","preparation_authorized",
      "native_execution_authorized","simulation_authorized","controller_readiness")),
      "Historical input admission acquired execution authority")
    require(sha(regular(ROOT,QUALIFIED_METHOD))==QUALIFIED_METHOD_SHA,"Qualified worker method changed")
    prior=json.loads(regular(ROOT,QUALIFIED_METHOD).read_bytes())
    require(prior["schema"]=="cdr-width-loaded-worker-source-controls-v1"
      and prior["source_controls_authorized"]is True
      and all(prior[k]is False for k in ("controller_ready","native_authorized","simulation_authorized")),
      "Source-only worker authority changed")
    m=validate_method(json.loads(regular(ROOT,METHOD).read_bytes()),prior)
    for n,h in m["protected_sha256"].items():
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h)
          and sha(regular(ROOT,n))==h,"Protected execution source changed: "+n)
    worker_derivation(regular(ROOT,WORKER).read_bytes())
    return m

def worker_proof():
    raw={}
    for n,s in SOURCE_REQUIRED.items():
        b=regular(ROOT,n).read_bytes()
        require(len(b)==s["bytes"]and hashlib.sha256(b).hexdigest()==s["sha256"],
          "Qualified worker proof bytes changed: "+n)
        raw[n.removeprefix(SOURCE_PREFIX)]=b
    d={n:json.loads(b)for n,b in raw.items()if n.endswith(".json")}
    receipt=d["receipt.json"]
    require(receipt["run"]==SOURCE_RUN and receipt["source"]==SOURCE_HEAD
      and receipt["attempt"]==1 and receipt["terminal"]=="success"
      and receipt["source_controls_only"]is True and receipt["source_controls_qualified"]is True,
      "Qualified worker receipt identity changed")
    exact(receipt["files"],{n:s for n,s in SOURCE_REQUIRED.items()if n!=SOURCE_RECEIPT},
      "Qualified worker receipt inventory changed")
    run=d["run.json"]
    require((run["id"],run["head_sha"],run["head_branch"],run["run_attempt"],run["event"],
      run["status"],run["conclusion"],run["workflow_id"])==
      (SOURCE_RUN,SOURCE_HEAD,"codex/cdr-width-loaded-worker",1,"workflow_dispatch","completed","success",400655341),
      "Qualified worker source run changed")
    jobs=d["jobs.json"]["jobs"]
    require(d["jobs.json"]["total_count"]==len(jobs)==2
      and {(j["id"],j["name"])for j in jobs}=={(123483140490,"source-controls"),(123483490882,"preserve-job-log")},
      "Qualified worker source jobs changed")
    for j in jobs:
        require(j["run_id"]==SOURCE_RUN and j["head_sha"]==SOURCE_HEAD and j["run_attempt"]==1
          and j["status"]=="completed"and j["conclusion"]=="success","Qualified worker job failed")
        exact(j,d[str(j["id"])+".job.json"],"Qualified worker individual job changed")
    ctx=d["controls/context.json"]
    exact(ctx,{"attempt":1,"method_sha256":QUALIFIED_METHOD_SHA,"native_authorized":False,
      "run_id":SOURCE_RUN,"source":SOURCE_HEAD,"source_controls_only":True},"Qualified worker context changed")
    index=d["controls/index.json"]
    require(set(index)=={"context.json","result.json","stdout.log","stderr.log"},"Qualified source index changed")
    for name,s in index.items():
        b=raw["controls/"+name]
        require(s["path"]==name and s["present"]is True and s["bytes"]==len(b)
          and s["sha256"]==hashlib.sha256(b).hexdigest(),"Qualified indexed source bytes changed")
    require(raw["controls/stdout.log"]==raw["controls/result.json"]
      and raw["controls/stderr.log"]==b"","Qualified worker streams changed")
    r=d["controls/result.json"]
    require(r["status"]=="PASS_WIDTH_LOADED_WORKER_RESULT_SOURCE_CONTROLS"
      and (r["current"]["positive"],r["current"]["refusal"],r["current"]["complete_metadata_members"])==(2,32,6647)
      and (r["derivation"]["numerical_blocks"],r["derivation"]["numerical_bytes"])==(6,24133)
      and r["historical"]["eight_rejections_and_two_fault_detections_retained"]is True,
      "Qualified numerical/source controls changed")
    require(len(r["historical"]["cases"])==10 and sum(x["original_passed"]for x in r["historical"]["cases"])==2
      and all(r[k]is False for k in ("native_acquisition_performed","numerical_worker_executed",
      "numerical_worker_imported","simulator_executed","electrical_accepted","full_phy_accepted")),
      "Historical controls became native acceptance")
    exact(r,receipt["report"],"Qualified report/receipt differs")
    return {"run":SOURCE_RUN,"source":SOURCE_HEAD,"receipt_sha256":SOURCE_RECEIPT_SHA,
      "files":len(raw),"source_only":True,"native_acceptance_transferred":False}

def source_guard():
    methods()
    worker_proof()
    return inputs.source_guard()

def authorize(prepare_only):
    require(type(prepare_only)is bool,"Preparation mode must be boolean")
    m=methods();context()
    require(m["preparation_authorized"if prepare_only else"simulation_authorized"]is True
      and m["controller_readiness"]is True,"Current width loaded execution disabled")
    worker_proof()
    return m

def reservation_gate():
    ctx=context();receipts={}
    for group in POLICY["groups"]:
        proof=wait(group,os.environ)
        tag,head=release.context(group,os.environ)
        require(proof["tag"]==tag and proof["tested_source"]==head==ctx["source"]
          and type(proof["release_id"])is int and proof["release_id"]>0
          and proof["externally_reserved"]is True and proof["creation_attempted"]is False
          and proof["target_verified"]is True and proof["assets_overwritten"]is False,
          "Current execution reservation changed")
        receipts[group]=proof
    require(len({p["release_id"]for p in receipts.values()})==11,"Execution reservation release collision")
    return {"current_context":ctx,"groups":receipts,"all_eleven_reserved_before_acquisition":True,
      "historical_source_proof_is_not_execution_authority":True}

def restore(out,prepare_only):
    authorize(prepare_only);d=source_guard();out=Path(out)
    require(out.is_dir()and not out.is_symlink(),"Invalid loaded output root")
    require(all(not(out/n).exists()and not(out/n).is_symlink()for n in ("current-mim-transport","current-mim-bundle")),"Loaded restore destination occupied")
    reservations=reservation_gate()
    write(out/"current-execution-admission.json",reservations)
    run=release.api("actions/runs/"+str(RUN));jobs=release.api("actions/runs/"+str(RUN)+"/attempts/1/jobs?per_page=100")
    info=release.api("releases/"+str(RELEASE));ref=release.api("git/ref/tags/"+TAG)
    remote=validate_live(run,jobs,info,ref,d)
    archive=acquire_and_extract(out,d,info)
    planes,_=verify_bundle(out/"current-mim-bundle",d)
    methods()
    return loaded_view(out/"current-mim-bundle",d,archive,remote,planes)
