#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Distinct current-source VI-only admission; no prior run identity is reused.
Original electrical predicates and protected RC input capsule remain frozen.
"""
import base64,copy,hashlib,json,os,re,subprocess
from pathlib import Path
import cdr_v59_tail_loaded_admission as old
from wait_cloud_tested_source_release import wait

ROOT=Path(__file__).resolve().parents[1]
BRANCH='codex/cdr-eight-drain-storage-preflight-v1'
METHOD='scripts/cdr-eight-drain-vi-bias-off-methods-v1.json'
BASELINE_METHOD='scripts/cdr-eight-drain-storage-methods-v1.json'
VI_REQUIRED=('scripts/check_cdr_eight_drain_vi_source_closure_v1.py','scripts/cdr-eight-drain-vi-source-closure-v1.json','docs/evidence/cdr-via-rich-stream-transport-pass-20261019.json','scripts/cdr_eight_drain_vi_bias_off_publication_v1.py','scripts/cdr_eight_drain_vi_bias_off_admission_v1.py','scripts/cloud_cdr_eight_drain_vi_bias_off_worker_v1.py','scripts/cdr_eight_drain_vi_bias_off_result_v1.py','scripts/cloud_cdr_eight_drain_vi_bias_off_stage_v1.py','scripts/check_cdr_eight_drain_vi_bias_off_v1.py','scripts/cdr-eight-drain-storage-methods-v1.json','docs/cdr-eight-drain-single-vi-v1-20261031.md')
BASELINE_METHOD_SHA='2a39248cc08361a0ae99e0b117bd278e446e83a25830bce873c82fa5adaa4f67'
CONFIG='scripts/cdr-current-eight-drain-loaded-inputs.json'
CONFIG_SHA='e2fef82c019da0773bcc46c52143e1639f367820f5ac27ac9073338b26a2ee3a'
PRIOR='scripts/cdr-current-eight-drain-fresh-rc-methods.json'
PRIOR_SHA='bd9e67b47630538934b808e803e60fc72b0211bd3382786d4d1f527eb9cc65d6'
PRIOR_COUNT=1720
ELECTRICAL_PRIOR='scripts/cdr-width-loaded-execution-methods.json'
ELECTRICAL_PRIOR_SHA='119b7a2d35abb1163570d01b8af16d18c6d9401e839a38904863d8b42eecef67'
PREFIX='docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/'
RECEIPT='docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/receipt.json'
RECEIPT_SHA='7b83bc306552b43d75cc4cf31fa9656b32098ce6c7d7ecad0efdc95aab3078a2'
RUN=41213815773
HEAD='ebe4ebb3ca2aef7b23cfc68f4b17588c03cd84fb'
RELEASE=430009833
TAG='cloud-results-41213815773-1-cdr-current-eight-drain-fresh-rc'
MODEL_MEMBER='mim/composition/pd500-mim-wire.spice'
MODEL_SHA='acb76bac03d1217350e4928124e93e53ad6dbf2abd5b63c9b30f81057916abd5'
PLANES_MEMBER='mim/precise/source/native-planes.json'
PLANES_SHA='0dff90f1d32496937bc77b055a5a3bed1fd8c132155652d1ff3976a5f9137b07'
RAW_SHA='2136b4d57f0c381f8e6a4f84c6735eef052fd9d221c1068a8b478904c43f87f2'
SUMMARY_SHA='a770d850124e00a9fd426539380598ffbc99997ed1931956638418230b5b30fb'
PASS='PASS_CURRENT_EIGHT_DRAIN500_BINDING_WIRE_RC_SEVEN_MIM_TWO_ORDERS_REQUIRES_ORIGINAL_ELECTRICAL_MATRIX'
REQUIRED={'complete-native-members.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/complete-native-members.json', 'bytes': 992565, 'sha256': 'f382e31d69428a1d0f76f56562ce3768949609844dd3b7fa4f69c52625ec85d2', 'object_sha256': 'f382e31d69428a1d0f76f56562ce3768949609844dd3b7fa4f69c52625ec85d2'}, 'direct/MIM-precision-result.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.MIM-precision-result.json', 'bytes': 6380484, 'sha256': 'c18f8b76ff9a80d76190f804019c533b5dcf4cf4526abb69712ca9ea1792ae70', 'object_sha256': '6a98c0cb2e82a737062cdcc6d044968f2464d0c53ca50b508d20e6f8f918579e'}, 'direct/binding-result.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.binding-result.json', 'bytes': 551833, 'sha256': '7e09feebf684f668737cc0c18e5f5372795ff0970d810340d5b3d33d005744c1', 'object_sha256': '8025d60a4e3f062a2cf0b53fa08e5a86f16e1d12b09e960203440a873bb5435d'}, 'direct/binding.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.binding.json', 'bytes': 351751, 'sha256': '4b575d79cce5b875bdc060b37231a5a3e31f0bf917e2bfcc016dfaef7f561df8', 'object_sha256': 'ab4ddac84a41d23db15c63c92aa87cb70ed8f877610f70f7d3b337eaf1612698'}, 'direct/canonical-candidate.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.canonical-candidate.json', 'bytes': 9206, 'sha256': 'b3526c71a15af390c0eed837e8c794d0b78b8b8e46eeeeb7e66feb0243b463e0', 'object_sha256': 'b3526c71a15af390c0eed837e8c794d0b78b8b8e46eeeeb7e66feb0243b463e0'}, 'direct/composition.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.composition.json', 'bytes': 969974, 'sha256': '04eba6d0824c5fee79ad8098bcd985b56f255223edbfa495a5b6be3a2abbb3c5', 'object_sha256': 'ce9d28f9ab6713704ac33a76a679c952616f57f16b12dd1c38582850b16f92a9'}, 'direct/direct-publication-plan.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.direct-publication-plan.json', 'bytes': 4044, 'sha256': '3064ea71b3ca09bcb955eb5dc382535b239e1ae1f3426e8ae66626ce3b58dd37', 'object_sha256': '3064ea71b3ca09bcb955eb5dc382535b239e1ae1f3426e8ae66626ce3b58dd37'}, 'direct/graph-restore.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.graph-restore.json', 'bytes': 128408, 'sha256': '44de21eae61af30539c9c21dd74932257a33319f5363ac70098ac82b8828f3ae', 'object_sha256': '44de21eae61af30539c9c21dd74932257a33319f5363ac70098ac82b8828f3ae'}, 'direct/joint-admission.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.joint-admission.json', 'bytes': 57831, 'sha256': 'b671e2cac771f321edd5cb712a200bd62847acd66597d8a1c9d1ef20af262c9c', 'object_sha256': 'b671e2cac771f321edd5cb712a200bd62847acd66597d8a1c9d1ef20af262c9c'}, 'direct/live-graph-and-physical.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.live-graph-and-physical.json', 'bytes': 159, 'sha256': '63eeeea3e099cf1fd3c21259de84600ffa40cbc1748a75891ea5e5facdf6e889', 'object_sha256': '63eeeea3e099cf1fd3c21259de84600ffa40cbc1748a75891ea5e5facdf6e889'}, 'direct/parts.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.parts.json', 'bytes': 882, 'sha256': 'fd0191803248581ffc44706aa69e77b0fdf3be900179015f36c861351700978b', 'object_sha256': 'edc0f9fb3c1c6a1ac442ff3e358cd4ecc03fed1f35b22e47c2dbe7eac5196bc9'}, 'direct/precise-audit.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.precise-audit.json', 'bytes': 284679, 'sha256': 'c098dea1c5ff58f2a19fdc2fe0d0941eb9faaa8f3c6cb6d7acfae04045eed979', 'object_sha256': '09a427f947d9fc33c9e31345c594aada8db96731a80dd97196271fe72a58be12'}, 'direct/precise-capture.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.precise-capture.json', 'bytes': 195362, 'sha256': 'cfc27a609c16a4158344165d42cd2f62fe5c9187dc957641bdcd69b79d758320', 'object_sha256': '85f183a4c1872c2dc2130158715802f9e5bd68273cb4829cf182aa9fdd08669c'}, 'direct/reversed-audit.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.reversed-audit.json', 'bytes': 284799, 'sha256': '76467b157dc3a0ecf07d3cf5ee41c3eb24b3e6805b5e8a5f5460b679d0b4e2cb', 'object_sha256': '360c0f9d563e96a12d6207d609e9daca23ae37bd9c4c07f3c8b123c9d9483210'}, 'direct/reversed-capture.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.reversed-capture.json', 'bytes': 196602, 'sha256': '8b457b9b429c5776aeef8dcf2108e507a494688a5d583d531011f38763e36508', 'object_sha256': 'a47ca1e4a7ca16fa836d4e6155f7f595411409142e47f28955a220f5633c12be'}, 'direct/runtime-smoke.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.runtime-smoke.json', 'bytes': 3569, 'sha256': 'e4e86b9ec7294755126a335fef5ec99cef04431e96b603142ac6eab4078ff33d', 'object_sha256': 'c098d38842981e8697861b05e4e5dca5fae8ee29cc23ab5014f10c4ebc325737'}, 'direct/summary.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.summary.json', 'bytes': 481795, 'sha256': 'a770d850124e00a9fd426539380598ffbc99997ed1931956638418230b5b30fb', 'object_sha256': 'a770d850124e00a9fd426539380598ffbc99997ed1931956638418230b5b30fb'}, 'direct/wire-RC-result.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.wire-RC-result.json', 'bytes': 2448382, 'sha256': '5141ab7ed2e703b21ba0e242454223dfced8b4adb7cf076d25c58ccf6e5cad4f', 'object_sha256': '64171b2c1b4b1e0134647b2c063b3e38fa7ead2c61e64abbb519b9f1c9fbd40b'}, 'jobs.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/jobs.json', 'bytes': 13938, 'sha256': '87c18d7931760e3b233b06aa9915fb5ebcb4eaadb6f5d54712f12e23b15a2f8c', 'object_sha256': '0c18b193bd877ff13c118c49579ad5cc0b626d356c06152e003eb4b3d43ccd8e'}, 'publication.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/publication.json', 'bytes': 8670, 'sha256': 'c788057a15c20df434372a8ffef66e72a4b6011931a6a6abf0c1fa02a65133b8', 'object_sha256': 'c788057a15c20df434372a8ffef66e72a4b6011931a6a6abf0c1fa02a65133b8'}, 'raw-result.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/raw-result.json', 'bytes': 481697, 'sha256': '2136b4d57f0c381f8e6a4f84c6735eef052fd9d221c1068a8b478904c43f87f2', 'object_sha256': '2136b4d57f0c381f8e6a4f84c6735eef052fd9d221c1068a8b478904c43f87f2'}, 'release.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/release.json', 'bytes': 36464, 'sha256': '2195757fe78a50df13e680272fe13c8dd53763a448bb5d212db62f661d888d39', 'object_sha256': '707403e5b497d3e192f5792e23bd681915f69aa921d65e96fb81fd04edfa42aa'}, 'run.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/run.json', 'bytes': 13156, 'sha256': 'acbb2ddb23c8883246fc6af2d3a96c0e97c46c16fc8254887c57c7ae55beb598', 'object_sha256': '6fbb98db4b9895432fdf9b8c945e3a233badab87fafae7e25fdd3f9a22089b8f'}, 'tag-ref.json': {'path': 'docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/tag-ref.json', 'bytes': 526, 'sha256': '46ef467df896960721ae70b9cb770602a34926e7c32850ad43f2fe1b1e6b3a61', 'object_sha256': 'cc8a3dfa30c2e0a54e75fdca374e448c2b54055d3c8ba40d1f062a32b80324cd'}}
SUMMARY='docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.summary.json'
STAGE='docs/evidence/cdr-current-eight-drain-fresh-rc-terminal-41213815773/direct/cdr-current-eight-drain-fresh-rc-41213815773-1.MIM-precision-result.json'
POLICY={"automatic_retry":False,"create_preparation_reservation_last":True,"each_loaded_case_seconds":7200,"fail_fast":False,"groups":["cdr-current-eight-drain-loaded-vi_bias_off","cdr-current-eight-drain-loaded-preparation"],"max_parallel":1,"preparation_seconds":1200,"reserve_both_before_any_native_dependencies":True}
NEW_REQUIRED=('scripts/cdr_current_eight_drain_loaded_admission.py', 'scripts/cloud_cdr_current_eight_drain_loaded.py', 'scripts/cdr_current_eight_drain_loaded_result.py', 'scripts/cloud_cdr_current_eight_drain_loaded_stage.py', 'scripts/check_cdr_current_eight_drain_loaded.py', 'scripts/cdr-current-eight-drain-loaded-inputs.json', 'docs/evidence/cdr-current-eight-drain-loaded-source-review-20261031.json')
PHASES=('restore-complete-graph330-and-current75', 'fresh-current500-binding', 'fresh-current500-wire-RC', 'fresh-seven-MIM-both-native-orders')
NATIVE_MEMBERS=2874
SUMMARY_MEMBERS=2873
RAW_MEMBERS=2872
GRAPH_MEMBERS=330
GRAPH_RUN=41206809668
GRAPH_SOURCE='de79f76bc60b3ef2b06c88736f4f3d0ee3491257'
PHYSICAL_RUN=41203881385
PHYSICAL_SOURCE='39496d034c4c1f2c9bcc3a9fe70cb3d82823fb53'
ARCHIVE_DIRECTORY='cloud-cdr-current-eight-drain-fresh-rc'
ARCHIVE_BYTES=67570622
ARCHIVE_SHA='2c80117523e7bf666bb78d6ae3d48dd74f5d2511121550ba963f40d785567a60'
TARGET_ANCHORS=('T003_D', 'T004_D', 'T005_D', 'T006_D', 'T032_D', 'T033_D', 'T034_D', 'T035_D')
MODEL=old.MODEL
CASES=old.CASES
AUTH=old.AUTH
ALWAYS_FALSE=old.ALWAYS_FALSE
require=old.require
sha=old.sha
regular=old.regular
relative=old.relative
write=old.write
fetch=old.fetch
release=old.release
verify_exact_files=old.verify_exact_files

def exact(a,b,why):
    require(json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False),why)

def encoded(value):
    return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()

def descriptor():
    raw=regular(ROOT,CONFIG).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==CONFIG_SHA,"New RC input configuration changed")
    return json.loads(raw)

def validate_method(m,prior,electrical):
    require(m["schema"]=="cdr-eight-drain-single-vi-execution-v1"and m["branch"]==BRANCH,"Drain loaded method identity")
    old.validate_authorizations(m)
    require(m["native_cases"]==["vi_bias_off"]and m["preparation_case"]=="nominal_early","Only one native transient case")
    require(sha(regular(ROOT,BASELINE_METHOD))==BASELINE_METHOD_SHA,"Proven storage method changed")
    baseline=json.loads(regular(ROOT,BASELINE_METHOD).read_bytes())
    require(len(baseline["protected_sha256"])==1969 and all(m["protected_sha256"].get(n)==h for n,h in baseline["protected_sha256"].items()),"Proven storage source protection omitted")
    require(m["controller_readiness"]is(m["preparation_authorized"]or m["simulation_authorized"]),"Controller authority mismatch")
    require(not m["workflow_dispatch_authorized"]or m["source_controls_authorized"],"Dispatch requires source controls")
    require(type(m["producer_run"])is int and m["producer_run"]==RUN and m["producer_source"]==HEAD,"New RC producer identity")
    exact(m["execution_policy"],POLICY,"Exact VI-only execution policy changed")
    require(m["original_executed_source"]=="e191424507e67331b2e79800caece4a3f03a1cc0"
      and m["original_execution_method_sha256"]==ELECTRICAL_PRIOR_SHA
      and m["current_RC_receipt_sha256"]==RECEIPT_SHA,"Original electrical/new RC authority binding")
    require(len(prior["protected_sha256"])==PRIOR_COUNT,"Inherited RC source count")
    for parent in (prior,electrical):
        require(all(m["protected_sha256"].get(n)==h for n,h in parent["protected_sha256"].items()),"Inherited source protection removed")
    require(m["protected_sha256"].get(PRIOR)==PRIOR_SHA and m["protected_sha256"].get(ELECTRICAL_PRIOR)==ELECTRICAL_PRIOR_SHA,"Historical method source omitted")
    require(all(n in m["protected_sha256"]for n in NEW_REQUIRED+VI_REQUIRED),"New loaded source protection omitted")
    require(m["protected_sha256"].get(RECEIPT)==RECEIPT_SHA,"Fresh RC receipt protection omitted")
    return m

def methods():
    require(sha(regular(ROOT,PRIOR))==PRIOR_SHA and sha(regular(ROOT,ELECTRICAL_PRIOR))==ELECTRICAL_PRIOR_SHA,"Historical method changed")
    m=validate_method(json.loads(regular(ROOT,METHOD).read_bytes()),
      json.loads(regular(ROOT,PRIOR).read_bytes()),json.loads(regular(ROOT,ELECTRICAL_PRIOR).read_bytes()))
    for n,h in m["protected_sha256"].items():
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h)and sha(regular(ROOT,n))==h,"Protected execution source changed: "+n)
    descriptor()
    return m

def context(env=None):
    e=os.environ if env is None else env
    require(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted"
      and e.get("RUNNER_OS")=="Linux"and e.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc","Hosted Linux context required")
    require(e.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and e.get("GITHUB_RUN_ATTEMPT")=="1","Manual first attempt required")
    require(e.get("GITHUB_REF")=="refs/heads/"+BRANCH,"Single-case branch required")
    require(e.get("GITHUB_WORKFLOW_REF")=="Melihakbulut221/nssoc/.github/workflows/cloud-evidence-summary.yml@refs/heads/"+BRANCH,"Exact workflow required")
    require(re.fullmatch("[0-9a-f]{40}",e.get("GITHUB_SHA",""))and re.fullmatch("[1-9][0-9]*",e.get("GITHUB_RUN_ID","")),"Actual source/run required")
    require(e.get("APPROVED_SOURCE")==e["GITHUB_SHA"],"Explicit approved source differs")
    require(e.get("REQUESTED_MODE")in("controls","vi-bias-off")and e.get("REQUESTED_CASE")=="vi_bias_off","Exact manual mode/case required")
    require(e.get("GITHUB_JOB")in("source-controls","prepare","vi-bias-off"),"Unknown workflow job")
    if env is None:
        require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==e["GITHUB_SHA"],"Actual checkout HEAD differs")
    return {"source":e["GITHUB_SHA"],"run_id":int(e["GITHUB_RUN_ID"]),"attempt":1}

def execution_context(case,prepare,env=None):
    e=os.environ if env is None else env;ctx=context(env)
    require(type(prepare)is bool and e.get("REQUESTED_MODE")=="vi-bias-off","Single-case native mode required")
    require((prepare and case=="nominal_early")or(not prepare and case=="vi_bias_off"),"Only preparation or VI case authorized")
    require(e.get("GITHUB_JOB")==("prepare"if prepare else"vi-bias-off"),"Exact native job required")
    require(e.get("LOADED_CASE")==case and e.get("PREPARE_ONLY")==("true"if prepare else"false"),"Worker arguments differ from owned job")
    return ctx

def validate_reservations(ctx,prepare,receipts):
    require(type(prepare)is bool and set(receipts)==set(POLICY["groups"]),"Exactly two reservations required")
    own="cdr-current-eight-drain-loaded-"+("preparation"if prepare else"vi_bias_off")
    for group,proof in receipts.items():
        expected="cloud-results-"+str(ctx["run_id"])+"-1-"+group
        require(proof["tag"]==expected and proof["tested_source"]==ctx["source"]
          and type(proof["release_id"])is int and proof["release_id"]>0
          and proof["externally_reserved"]is True and proof["creation_attempted"]is False
          and proof["target_verified"]is True and proof["assets_overwritten"]is False,"Independent exact-source reservation changed")
    require(len({p["release_id"]for p in receipts.values()})==2,"Reservation release collision")
    require(receipts[own]["existing_assets"]==[],"Owned release is not empty; no retry/overwrite allowed")
    if prepare:require(all(p["existing_assets"]==[]for p in receipts.values()),"Both initial reservations must be empty")
    return {"current_context":ctx,"groups":receipts,"both_reserved_before_acquisition":True,"own_empty_release":own,"automatic_retry":False}

def validate_source_controls(ctx,run,jobs,log):
    require(run["id"]==ctx["run_id"]and run["head_sha"]==ctx["source"]and run["run_attempt"]==1
      and run["event"]=="workflow_dispatch"and run["workflow_id"]==382556685
      and run["path"]==".github/workflows/cloud-evidence-summary.yml","Actual producer workflow/source changed")
    require(jobs["total_count"]==len(jobs["jobs"])<=4,"Complete current job census required")
    selected=[j for j in jobs["jobs"]if j["name"]=="source-controls"]
    require(len(selected)==1,"Unique source-controls job required");job=selected[0]
    require(job["head_sha"]==ctx["source"]and job["status"]=="completed"and job["conclusion"]=="success"
      and all(s["conclusion"]=="success"for s in job["steps"]),"Source controls not wholly successful")
    indexes={};chunks={}
    for line in log.decode("utf-8-sig").splitlines():
        for marker,kind in(("VI_SOURCE_INDEX ","i"),("VI_SOURCE_CHUNK ","c")):
            if marker not in line or not line.split(marker,1)[1].startswith("{"):continue
            row=json.loads(line.split(marker,1)[1]);name=row["path"]
            if kind=="i":
                require(name not in indexes,"Duplicate source index");indexes[name]=row
            else:
                require(row["index"]not in chunks.setdefault(name,{}),"Duplicate source chunk")
                chunks[name][row["index"]]=base64.b64decode(row["base64"],validate=True)
    expected={"vi.json","vi.stdout","vi.stderr","storage.json","storage.stdout","storage.stderr","checkout.json","before-checkout.json"}
    require(set(indexes)==expected and set(chunks)<=expected,"Complete exact source streams required")
    outputs={}
    for name,pin in indexes.items():
        require(pin["present"]is True and set(chunks.get(name,{}))==set(range(pin["chunks"])),"Incomplete source stream")
        raw=b"".join(chunks[name][i]for i in range(pin["chunks"]))if pin["chunks"]else b""
        require(len(raw)==pin["bytes"]and hashlib.sha256(raw).hexdigest()==pin["sha256"],"Source stream bytes differ")
        outputs[name]=raw
    report=json.loads(outputs["vi.json"]);storage=json.loads(outputs["storage.json"])
    require(report["status"]=="PASS_SINGLE_VI_SOURCE_CONTROLS_NO_NATIVE_EXECUTION"and report["current_context"]==ctx,"Current source report identity")
    require(report["method_sha256"]==sha(regular(ROOT,METHOD))and report["source_controls_only"]is True,"Current method/source proof")
    require(all(report[k]is False for k in("native_executed","native_acquisition","electrical_accepted","physical_accepted","full_phy_accepted")),"Source test acceptance scope changed")
    require(all(v is True for v in report["qualified_controls"].values())and set(report["qualified_controls"])=={"context","method","reservations","source_prerequisite","derivation","source_integrity","storage_regression"},"Complete single-case controls required")
    require(storage["status"]=="PASS_STORAGE_SOURCE_CONTROLS_NOT_NATIVE_OR_ELECTRICAL_ACCEPTANCE"
      and storage["source"]==ctx["source"]and storage["storage"]["count"]==13
      and storage["native_executed"]is False and storage["native_acquisition"]is False,"Actual proven storage regression absent")
    return dict(current_context=ctx,job_id=job["id"],job_log_sha256=hashlib.sha256(log).hexdigest(),records=indexes,
      complete_source_controls_authenticated=True,native_execution_performed=False)

def read_source_api(path):
    # Hosted-only source/log metadata transport; preserve every response byte.
    allowed=r"actions/(?:runs/[1-9][0-9]*(?:/attempts/1/jobs[?]per_page=100)?|jobs/[1-9][0-9]*(?:/logs)?)"
    require(isinstance(path,str)and re.fullmatch(allowed,path),"Unexpected source API path")
    argv=["gh","api","repos/Melihakbulut221/nssoc/"+path]
    if re.fullmatch(r"actions/jobs/[1-9][0-9]*/logs",path):argv.append("--allow-escape-sequences")
    return subprocess.check_output(argv)

def authenticate_source_controls():
    ctx=context();read=read_source_api
    runraw=read("actions/runs/"+str(ctx["run_id"]));run=json.loads(runraw)
    jobsraw=read("actions/runs/"+str(ctx["run_id"])+"/attempts/1/jobs?per_page=100");jobs=json.loads(jobsraw)
    selected=[j for j in jobs["jobs"]if j["name"]=="source-controls"];require(len(selected)==1,"Unique source control job")
    log=read("actions/jobs/"+str(selected[0]["id"])+"/logs")
    root=ROOT/"hw/soc/out/cdr-eight-drain-vi-prerequisites"
    require(not root.is_symlink(),"Prerequisite preservation symlink refused")
    root.mkdir(parents=True,exist_ok=True)
    saved=root/(os.environ["GITHUB_JOB"]+"-"+str(len(list(root.iterdir()))))
    saved.mkdir()
    for name,raw in(("run.json",runraw),("jobs.json",jobsraw),("source-controls.log",log)):(saved/name).write_bytes(raw)
    result=validate_source_controls(ctx,run,jobs,log)
    result["full_prerequisite_records"]={str((saved/n).relative_to(ROOT)):sha(saved/n)for n in("run.json","jobs.json","source-controls.log")}
    write(saved/"admission.json",result)
    return result

def reservation_gate():
    ctx=context();prepare=os.environ.get("PREPARE_ONLY")=="true"
    execution_context(os.environ.get("LOADED_CASE"),prepare)
    controls=authenticate_source_controls()
    receipts={group:wait(group,os.environ)for group in POLICY["groups"]}
    result=validate_reservations(ctx,prepare,receipts);result["source_controls"]=controls
    return result

def source_guard():
    m=methods();raw=regular(ROOT,RECEIPT).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==RECEIPT_SHA,"Fresh RC terminal receipt changed")
    receipt=json.loads(raw)
    require(receipt["run_id"]==RUN and receipt["source"]==HEAD and receipt["attempt"]==1
      and receipt["release_id"]==RELEASE and receipt["complete_native_members"]==NATIVE_MEMBERS,"Fresh RC receipt identity")
    for name,spec in receipt["records"].items():
        path=PREFIX+name
        require(m["protected_sha256"].get(path)==spec["sha256"],"Complete producer proof unprotected: "+path)
        b=regular(ROOT,path).read_bytes()
        require(len(b)==spec["bytes"]and hashlib.sha256(b).hexdigest()==spec["sha256"],"Complete producer proof changed: "+path)
    d={}
    for name,spec in REQUIRED.items():
        b=regular(ROOT,spec["path"]).read_bytes()
        require(len(b)==spec["bytes"]and hashlib.sha256(b).hexdigest()==spec["sha256"],"Required producer report changed: "+name)
        d[name]=json.loads(b)
    validate_reports(d)
    return d

def full_map(d):
    return d["complete-native-members.json"]["sha256"]

def submap(full,prefix):
    return {n[len(prefix):]:h for n,h in full.items()if n.startswith(prefix)}

def validate_targets(composition,config):
    require(set(config["target_terminals"])==set(TARGET_ANCHORS)and len(TARGET_ANCHORS)==8,"All eight actual drain targets required")
    found={}
    for anchor,target in config["target_terminals"].items():
        identities={tuple(x)for x in target["graph_full_partition"]["terminals"]}
        require(len(identities)==8 and target["graph_full_partition"]["ports"]==[],"Target complete terminal partition")
        rows=[]
        for dev in composition["device_records"]:
            for term in dev["terminals"]:
                if any(dev["native_id"]==i and dev["model"].lower()==model.lower()and term["terminal"]==t for i,model,t in identities):
                    rows.append(dict(native_id=dev["native_id"],instance=dev["instance"],model=dev["model"],parameters=dev["parameters"],**term))
        exact(rows,target["terminals"],"Fresh target terminal/node mapping changed: "+anchor)
        require(len(rows)==8 and all(r["native_cluster"]==target["native_cluster"]and r["native_net"]==target["native_net"]for r in rows),"Target full partition disagrees")
        all_terms={(dev["native_id"],dev["model"].lower(),t["terminal"])for dev in composition["device_records"]for t in dev["terminals"]if(t["native_cluster"],t["native_net"])==(target["native_cluster"],target["native_net"])}
        require(all_terms=={(i,model.lower(),t)for i,model,t in identities},"Target gained or lost terminals")
        require(sum(r["anchor"]==anchor and r["node"]=="w_"+anchor for r in rows)==1,"Fresh requested drain anchor missing")
        found[anchor]={"component":target["component"],"native_cluster":target["native_cluster"],"native_net":target["native_net"],"terminals":rows,"reduced_resistor_identity_assumed":False}
    return found

def validate_reports(d):
    require(set(d)==set(REQUIRED),"Required producer report set changed")
    for name,spec in REQUIRED.items():
        require(hashlib.sha256(encoded(d[name])).hexdigest()==spec["object_sha256"],"Authenticated producer report contents changed: "+name)
    s=d["direct/summary.json"];raw=d["raw-result.json"];full=full_map(d);cfg=descriptor()
    require(len(full)==NATIVE_MEMBERS and len(s["outputs"])==SUMMARY_MEMBERS and len(raw["outputs"])==RAW_MEMBERS,"Complete new RC inventory changed")
    exact(full,{**s["outputs"],"result.json":RAW_SHA},"Raw result substituted by direct summary")
    exact(s["outputs"],{**raw["outputs"],**cfg["publication"]["only_output_addition"]},"Publication-only log delta")
    exact({k:v for k,v in s.items()if k!="outputs"},{k:v for k,v in raw.items()if k!="outputs"},"Raw/publication semantics differ")
    for n,h in full.items():relative(n);require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h),"Invalid native member")
    require(s["status"]==PASS and s["source_head"]==HEAD and s["run_id"]==RUN and s["run_attempt"]==1,"New RC producer identity")
    require(all(s[k]is True for k in ("binding_executed","extraction_executed","fresh_RC_pipeline_complete","terminal_finalization_complete")),"Incomplete fresh RC")
    require(all(s[k]is False for k in ("automatic_retry","physical_geometry_regenerated","simulation_executed","physical_accepted","electrical_accepted","qualified_pex","full_phy_accepted","original_electrical_rejection_overridden","historical_authority_reused")),"RC acceptance scope changed")
    require((s["graph_run"],s["graph_source"])==(cfg["graph"]["run"],cfg["graph"]["source"])
      and(s["physical_run"],s["physical_source"])==(cfg["physical"]["run"],cfg["physical"]["source"])
      and(s["complete_graph_members"],s["current_members"])==(GRAPH_MEMBERS,75),"New physical/graph lineage changed")
    require([r["label"]for r in s["commands"]]==list(PHASES),"Four original phases changed")
    for r in s["commands"]:
        require(r["returncode"]==0 and r["supervision_failure"]is None and r["memory_read_error"]is None
          and not r["process_group_cleanup"]["remaining_live"]and not r["process_group_cleanup"]["signals"],"Fresh RC phase failed")
    require(all(x["completed"]is True for x in s["terminal_actions"])and not s.get("terminal_errors"),"Producer finalization failed")
    b=d["direct/binding-result.json"];binding=d["direct/binding.json"];wire=d["direct/wire-RC-result.json"];mim=d["direct/MIM-precision-result.json"];co=d["direct/composition.json"]
    for prefix,name,report,count in (("binding/","binding-result.json",b,53),("wire-stage/","wire-RC-result.json",wire,5),("mim/","MIM-precision-result.json",mim,1963)):
        exact(submap(full,prefix),{**report["outputs"],"result.json":REQUIRED["direct/"+name]["sha256"]},"Nested complete output inventory differs")
        require(len(submap(full,prefix))==count and report["source_head"]==HEAD and report["sources_unchanged"]is True,"Nested source/census differs")
    exact(b["binding"],binding,"Binding bytes/report differ")
    exact(binding["census"],{"npn13G2":124,"sg13_lv_nmos":50,"rppd":98,"cap_cmim":7,"ptap1":221},"Original 500-device census changed")
    exact(mim["composition"]["contract"],co,"Fresh composition report differs")
    exact(co["counts"],{"devices":500,"R":24356,"C":15566},"Actual new composition census differs")
    require(co["interface"]==binding["native_ports"]+["wire_cref"]and len(set(co["interface"]))==26,"Current interface order")
    require(len(co["device_records"])==500 and {x["native_id"]for x in co["device_records"]}=={x["native_id"]for x in binding["devices"]},"Device identities differ")
    old.frozen_pipeline_validator(HEAD)(mim,0)
    canonical=d["direct/canonical-candidate.json"]
    require(canonical["complete_members"]==75 and canonical["current_root_result_fabricated"]is False and "result.json"not in canonical["files"],"Original current75 identity changed")
    handoff=mim["current_input_restoration"]
    require(handoff["source_head"]==HEAD and handoff["run"]==RUN and handoff["historical763_1136_1127_counts_reused"]is False,"Fresh MIM handoff context")
    exact(handoff["binding"]["report"],b,"MIM binding handoff");exact(handoff["rc"]["report"],wire,"MIM RC handoff")
    for key,prefix,count in (("complete_binding_files","binding/",53),("complete_RC_stage_files","wire-stage/",5),("complete_current_view_files","canonical-current-view/",496)):
        require(len(handoff[key])==count,"Fresh handoff count");exact(handoff[key],submap(full,prefix),"Full handoff inventory differs")
    require(all(handoff["complete_current_view_files"].get(n)==h for n,h in canonical["files"].items()),"Original75 changed in496 RC view")
    require(canonical["files"]["parent/layout/nssoc_cdr_pd500_resistor_v59.gds"]==cfg["physical"]["gds_sha256"],"New rail GDS missing")
    for order in ("precise","precise_reversed"):
        exact(submap(full,"mim/"+order+"/source/"),handoff["complete_current_view_files"],"Full native order source projection differs")
        exact(submap(full,"mim/"+order+"/model-binding/"),handoff["complete_binding_files"],"Full native order binding differs")
    targets=validate_targets(co,cfg);selected_members(full)
    return {"complete_members":NATIVE_MEMBERS,"canonical_members":496,"original_current_members":75,"graph_members":GRAPH_MEMBERS,
      "target_terminals":targets,"raw_result_sha256":RAW_SHA,"publication_summary_sha256":SUMMARY_SHA,
      "electrical_accepted":False,"new_electrical_execution_performed":False}

def selected_members(full):
    require(full[MODEL_MEMBER]==MODEL_SHA and full[PLANES_MEMBER]==PLANES_SHA and full["canonical-current-view/native-planes.json"]==PLANES_SHA and full["mim/precise_reversed/source/native-planes.json"]==PLANES_SHA,"Current model/plane exact path changed")
    return {n:full[n]for n in (MODEL_MEMBER,PLANES_MEMBER,"mim/composition/composition.json","binding/binding.json","mim/precise/source/parent/layout/result.json")}

def verify_bundle(bundle,d):
    full=full_map(d)
    proof=old.verify_exact_files(bundle,full)
    require(regular(bundle,"result.json").read_bytes()==regular(ROOT,REQUIRED["raw-result.json"]["path"]).read_bytes(),"Restored raw terminal differs")
    for row in d["direct/direct-publication-plan.json"]["files"]:
        name="direct/"+row["suffix"]
        if name in REQUIRED:require(regular(bundle,row["member"]).read_bytes()==regular(ROOT,REQUIRED[name]["path"]).read_bytes(),"Restored direct report differs")
    planes=json.loads(regular(bundle,PLANES_MEMBER).read_bytes())
    require(sha(regular(bundle,PLANES_MEMBER))==PLANES_SHA and sha(regular(bundle,MODEL_MEMBER))==MODEL_SHA,"Current exact model/planes missing")
    require(planes["status"]=="PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS"and len(planes["anchors"])==160 and len({a["logical_net"]for a in planes["anchors"]})==51,"Current native plane qualification changed")
    layouts=[h for n,h in planes["inputs"].items()if n.endswith("/layout/result.json")]
    require(layouts==[full["mim/precise/source/parent/layout/result.json"]],"Current planes/layout join changed")
    require(regular(bundle,"mim/precise/model-binding/binding.json").read_bytes()==regular(bundle,"binding/binding.json").read_bytes(),"Current plane binding differs")
    for order in ("precise","precise_reversed"):
        require(regular(bundle,"mim/"+order+"/source/native-planes.json").read_bytes()==regular(bundle,PLANES_MEMBER).read_bytes(),"Two-order native planes differ")
    return planes,proof

def validate_live(run,jobs,info,ref,docs=None):
    d=source_guard()if docs is None else docs
    expected=d["run.json"]
    keys=("id","run_attempt","head_sha","head_branch","event","status","conclusion","workflow_id")
    exact({k:run[k]for k in keys},{k:expected[k]for k in keys},"Live RC run changed")
    require(run["id"]==RUN and run["head_sha"]==HEAD and run["status"]=="completed"and run["conclusion"]=="success"and type(run["run_attempt"])is int and run["run_attempt"]==1,"RC run did not succeed")
    ej={j["id"]:j for j in d["jobs.json"]["jobs"]}
    require(jobs["total_count"]==len(jobs["jobs"])==len(ej)==4 and len({j["id"]for j in jobs["jobs"]})==4,"RC job census changed")
    for j in jobs["jobs"]:
        require(j["id"]in ej,"Unexpected RC job")
        keys=("id","name","head_sha","run_id","run_attempt","status","conclusion")
        exact({k:j[k]for k in keys},{k:ej[j["id"]][k]for k in keys},"RC job identity changed")
        require(j["status"]=="completed"and j["conclusion"]=="success","RC job failed")
        sk=("number","name","status","conclusion")
        exact([{k:s[k]for k in sk}for s in j["steps"]],[{k:s[k]for k in sk}for s in ej[j["id"]]["steps"]],"RC job steps changed")
    require(type(info["id"])is int and info["id"]==RELEASE,"RC release changed")
    proof=release.validate_release(info,ref,TAG,HEAD)
    keys=("id","name","size","digest","state")
    rows=lambda value:sorted([{k:a[k]for k in keys}for a in value["assets"]],key=lambda a:a["id"])
    require(len(info["assets"])==19 and all(type(a["id"])is int and type(a["size"])is int and a["size"]>0 and a["state"]=="uploaded"for a in info["assets"]),"RC asset census/state changed")
    exact(rows(info),rows(d["release.json"]),"Complete live RC assets changed")
    parts=d["direct/parts.json"];byname={a["name"]:a for a in info["assets"]}
    require(parts["format"]=="ordered-tar-gzip-parts-v1"and parts["source_directory"]==ARCHIVE_DIRECTORY and parts["bytes"]==ARCHIVE_BYTES and parts["sha256"]==ARCHIVE_SHA,"Current RC archive identity changed")
    require([p["index"]for p in parts["parts"]]==[0]and sum(p["bytes"]for p in parts["parts"])==parts["bytes"],"Ordered archive parts changed")
    for p in parts["parts"]:
        a=byname[p["name"]];require((a["size"],a["digest"])==(p["bytes"],"sha256:"+p["sha256"]),"Archive part/release join changed")
    for name,spec in REQUIRED.items():
        if not name.startswith("direct/"):continue
        suffix=name.split("/",1)[1];matches=[a for a in info["assets"]if a["name"]==parts["stem"]+"."+suffix]
        require(len(matches)==1 and(matches[0]["size"],matches[0]["digest"])==(spec["bytes"],"sha256:"+spec["sha256"]),"Direct asset/proof bytes differ")
    return {"run":RUN,"source_head":HEAD,"reservation":proof,"assets":19,"terminal_success":True,"native_acquisition_performed":False}

def acquire_and_extract(out,d,info):
    transport=Path(out)/"current-mim-transport";transport.mkdir(exist_ok=False)
    for a in info["assets"]:
        relative(a["name"]);require("/"not in a["name"],"Invalid producer asset basename")
        target=transport/a["name"];digest=a["digest"].removeprefix("sha256:")
        fetch(a["browser_download_url"],digest,target)
        require(target.stat().st_size==a["size"]and sha(target)==digest,"Downloaded current RC asset changed")
    for name,spec in REQUIRED.items():
        if name.startswith("direct/"):
            p=transport/(d["direct/parts.json"]["stem"]+"."+name.split("/",1)[1])
            require(p.read_bytes()==regular(ROOT,spec["path"]).read_bytes(),"Direct snapshot transport changed")
    bundle=Path(out)/"current-mim-bundle"
    return old.saved.exact_extract(d["direct/parts.json"],transport,bundle,full_map(d))

def expected_files():
    return full_map(source_guard())

def verify_restored(root):
    return verify_exact_files(Path(root)/"current-mim-bundle",expected_files())

def composition_proof(d,archive,remote):
    return {"run":RUN,"source_head":HEAD,"reservation":remote["reservation"],"live_producer":remote,"full_archive":archive,
      "summary_sha256":SUMMARY_SHA,"raw_result_sha256":RAW_SHA,"stage_sha256":REQUIRED["direct/MIM-precision-result.json"]["sha256"],
      "current_graph_run":GRAPH_RUN,"current_physical_run":PHYSICAL_RUN,"complete_graph_members":GRAPH_MEMBERS,"current_members":75,"canonical_members":496,
      "historical_failed_geometry_and_electrical_reports_retained":True,"geometry_regenerated":False,"extraction_rerun":False,"simulation_preaccepted":False,
      "fresh_target_terminal_bindings":validate_targets(d["direct/composition.json"],descriptor())}

def plane_proof(d):
    return {"current_mim_source":REQUIRED["direct/MIM-precision-result.json"]["sha256"],"native_planes_sha256":PLANES_SHA,
      "fresh_layout_sha256":full_map(d)["mim/precise/source/parent/layout/result.json"],"native_binding_sha256":REQUIRED["direct/binding.json"]["sha256"]}

def loaded_view(bundle,d,archive,remote,planes):
    require(archive["regular_members"]==NATIVE_MEMBERS and archive["full_inventory_verified"]is True,"Complete new restored archive missing")
    exact({n:r["sha256"]for n,r in archive["complete_member_hashes"].items()},full_map(d),"Restored full2680 inventory differs")
    return d["direct/MIM-precision-result.json"],composition_proof(d,archive,remote),Path(bundle)/MODEL_MEMBER,d["direct/composition.json"],planes,plane_proof(d)

def authorize(prepare_only):
    require(type(prepare_only)is bool,"Preparation mode must be boolean")
    case=os.environ.get("LOADED_CASE")
    execution_context(case,prepare_only)
    m=methods()
    require(m["workflow_dispatch_authorized"]is True and m["controller_readiness"]is True
      and m["preparation_authorized"if prepare_only else"simulation_authorized"]is True,"Single VI execution disabled")
    return m

def authorize_case(case,prepare_only):
    execution_context(case,prepare_only)
    return authorize(prepare_only)

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
