#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Same frozen prefix and built ELF; two diagnostic tails, never physical acceptance."""
import os
import re
from pathlib import Path
import mainchip_fixed_engine_route_prefix_contract as previous
from mainchip_fixed_engine_route_prefix_contract import (
 require, secure_file, digest, decode, atomic_record, attempt, finish_record, error_record,
 IMAGE, IMAGE_ID, MEMORY, CPUS, PIDS, create_argv, validate_image, validate_container,
 engine_extract, runtime_match, ENGINE, INPUT, REPOSITORY)
from mainchip_witness_engine_build import fingerprint
from ensure_cloud_tested_source_release import validate_release
METHOD="scripts/mainchip-fixed-engine-route-tail-methods.json"
BRANCH="codex/mainchip-fixed-engine-route-tail"
BASE_GROUP="mainchip-fixed-engine-route-tail"
MODE_ENV="NSSOC_ROUTE_TAIL_MODE"
STAGE_ENV="NSSOC_ROUTE_TAIL_STAGE"
MODES=("off","on")
PREFIX="docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40863684870/"
PREFIX_RUN=40863684870
PREFIX_SOURCE="8d4b99992e0fbce6a0d4a53b33cbb053e2a7f6e0"
PREFIX_RELEASE=427769567
PREFIX_TAG="cloud-results-40863684870-1-mainchip-fixed-engine-route-prefix"
FROZEN_COUNT=0 # Pending actual fresh prefix result; never old746.
FROZEN_BYTES=0
PREFIX_REQUIRED={}
FROZEN_FIXED_SHA="PENDING_ACTUAL_FIXED_ODB"
FROZEN_REPAIR_SHA="PENDING_ACTUAL_REPAIR_TCL"
PREFIX_RECEIPT_SHA="PENDING_ACTUAL_PREFIX_TERMINAL"
PRIOR=previous.METHOD
PRIOR_SHA="0dd3c47a54f421987533ffad16b535b119ddd06757413c5dd1bf0cb7faffd23d"
SOURCE_ADMISSION="docs/evidence/mainchip-fixed-engine-route-tail-source-admission-20261029.json"
SCHEMA="mainchip-fixed-engine-route-tail-v1"
ROOT=Path(__file__).resolve().parent.parent
NEW_FILES=()
AUTH_FALSE=("rc_sta_execution_authorized","physical_acceptance","timing_accepted","full_phy_accepted","observer_equivalence_qualified","automatic_retry_authorized","engine_build_authorized","native_probe_authorized")
LIMITS=dict(memory_bytes=MEMORY,nano_cpus=CPUS,pids=PIDS,
 route_seconds=14400,phase_seconds=1200,min_free_disk_bytes=32*1024**3,
 archive_expanded_limit=8*1024**3,max_group_rss_kib=10485760,min_available_kib=2097152,
 route=dict(driver_seconds=14700,inner_seconds=15000,container_seconds=15180),
 audit=dict(driver_seconds=6300,inner_seconds=6600,container_seconds=6780))
PHASES=("one-two-signal-routing-attempt","route-audit","paired-original-class-return",
        "unfix-audit","full-original-class-read-only-DRT","drc-audit")
STATUSES={"route-audit":"PASS_ONLY_TWO_SIGNAL_DELTA_ALL_OTHERS_FIXED",
 "unfix-audit":"PASS_ORIGINAL_CLASS_TWO_SIGNAL_REPAIR_REQUIRES_DRC",
 "drc-audit":"COMPLETE_TWO_SIGNAL_ATTEMPT_ORIGINAL_CLASS_DRC_NOT_ACCEPTANCE"}
COMPARE_FILES=("routed-fixed.odb","routed-fixed.def","routed-audit.def",
 "repaired.odb","expected-original-class.def","repaired-audit.def",
 "drc-before.def","drc-after.def","drc-observed.odb","measured-audit.def")
WITNESS_ENV="NNSOC_DRT_INTERNAL_WITNESS_DIR"

def mode(env):
    value=env.get(MODE_ENV)
    require(value in (*MODES,"compare"),"tail mode")
    return value

def stage(env):
    value=env.get(STAGE_ENV)
    require(value in ("route","audit","compare"),"tail stage")
    require((mode(env)=="compare")== (value=="compare"),"mode/stage pair")
    return value

def group(value,stage):
    require(value in (*MODES,"compare"),"tail group mode")
    require(stage in ("route","audit","compare") and ((value=="compare")== (stage=="compare")),"tail group stage")
    return BASE_GROUP+"-compare" if value=="compare" else BASE_GROUP+"-"+value+"-"+stage

def stage_limits(value):
    require(value in ("route","audit"),"native stage limits")
    return LIMITS[value]


def context(env):
    # Same qualified container name/token syntax; matrix jobs have independent hosts.
    other=dict(env);other["GITHUB_REF"]="refs/heads/"+previous.BRANCH
    require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"tail branch")
    ctx=previous.context(other);ctx["mode"]=mode(env);ctx["stage"]=stage(env)
    return ctx

def validate_method(m,prior):
    require(m["schema"]==SCHEMA and m["branch"]==BRANCH and m["group"]==BASE_GROUP,"tail method identity")
    require(m["source_unit_complete"] is True,"incomplete split source unit")
    require(m["limits"]==LIMITS and m["engine"]==ENGINE and m["input"]==INPUT
        and m["image"]==IMAGE and m["image_id"]==IMAGE_ID,"tail identities/limits")
    require(m["phases"]==list(PHASES) and m["modes"]==list(MODES),"tail scope")
    for k in ("source_controls_authorized","native_tail_authorized","native_route_authorized","native_audit_authorized","controller_ready"):
        require(type(m[k]) is bool,"authorization type")
    require(not m["native_tail_authorized"] or m["source_controls_authorized"],"split authorization")
    require(m["native_handoff_split_complete"] is True,"route/audit handoff split required")
    require(m["native_tail_authorized"]==m["native_route_authorized"]==m["native_audit_authorized"]==m["controller_ready"],
        "inconsistent stage authorizations")
    require(all(m[k] is False for k in AUTH_FALSE),"no acceptance or continuation")
    require(m["prior_method_sha256"]==PRIOR_SHA and m["protected"].get(PRIOR)==PRIOR_SHA,"actual prefix method binding")
    require(len(prior["protected"])==1098 and m["inherited_protected_count"]==1098,"prefix pin count")
    require(all(m["protected"].get(p)==h for p,h in prior["protected"].items()),"prefix pin changed")
    require(set(NEW_FILES)<=set(m["protected"]),"new tail source protection")
    require(m["qualified_prefix"]==dict(run=PREFIX_RUN,source=PREFIX_SOURCE,release_id=PREFIX_RELEASE,
        receipt_sha256=PREFIX_RECEIPT_SHA),"actual fresh prefix binding")
    for path,row in PREFIX_REQUIRED.items():
        require(m["protected"].get(path)==row["sha256"],"protected prefix proof: "+path)
    return m

def method(root):
    require(digest(secure_file(root,PRIOR).read_bytes())==PRIOR_SHA,"immutable actual prefix method")
    m=validate_method(decode(secure_file(root,METHOD).read_bytes()),previous.method(root))
    for p,h in m["protected"].items():
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h) is not None
            and digest(secure_file(root,p).read_bytes())==h,"protected tail source: "+p)
    prefix_contract(root)
    return m

def authorize_stage(m,value):
    require(value in ("route","audit","compare"),"authorized stage")
    require(m["source_controls_authorized"] is True and m["native_tail_authorized"] is True
        and m["native_route_authorized"] is True and m["native_audit_authorized"] is True
        and m["controller_ready"] is True,"native tail not authorized")
    require(all(m[k] is False for k in AUTH_FALSE),"no acceptance or continuation")
    return m

def saved_path(name):
    names={"tag":"tag-ref.json","run":"run.json","jobs":"jobs.json","release":"release.json",
           "receipt":"receipt.json","complete-native-restore-map":"complete-native-restore-map.json"}
    return PREFIX+names.get(name,"direct/"+name+".json")

def saved(root,suffix):
    return decode(secure_file(root,saved_path(suffix)).read_bytes())

def authenticate_prefix_proof(root):
    require(bool(PREFIX_REQUIRED) and FROZEN_COUNT>0 and FROZEN_BYTES>0,"actual fresh prefix proof required")
    require(PREFIX_REQUIRED[PREFIX+"receipt.json"]["sha256"]==PREFIX_RECEIPT_SHA,"actual prefix receipt hash")
    for path,row in PREFIX_REQUIRED.items():
        raw=secure_file(root,path).read_bytes()
        require(dict(bytes=len(raw),sha256=digest(raw))==row,"prefix proof bytes: "+path)
    receipt=saved(root,"receipt")
    require(receipt["files"]=={p:r for p,r in PREFIX_REQUIRED.items()if p!=PREFIX+"receipt.json"},"complete prefix proof receipt")
    require((receipt["run"],receipt["source"],receipt["attempt"],receipt["terminal"],receipt["release_id"])==
        (PREFIX_RUN,PREFIX_SOURCE,1,"success",PREFIX_RELEASE),"actual prefix receipt identity")
    require(receipt["prefix_qualified"] is True and receipt["native_archive_acquired_locally"] is False,"prefix proof scope")
    return receipt

def prefix_contract(root):
    authenticate_prefix_proof(root)
    run=saved(root,"run");jobs=saved(root,"jobs");rel=saved(root,"release");tag=saved(root,"tag")
    envelope(root,run,jobs,rel,tag)
    host=saved(root,"host-result");inner=saved(root,"inner-result");native=saved(root,"native-prefix-result")
    require(host["status"]=="PASS_ACTUAL_ROUTING_PREFIX_READY_NO_ROUTING"
        and inner["status"]=="PASS_BUILT_ELF_ACTUAL_SHARED_PREFIX"
        and native["status"]=="PASS_ACTUAL_BUILT_ENGINE_SHARED_PREFIX","prefix terminal status")
    require(all(not x["terminal_errors"] for x in (host,inner,native)),"prefix terminal errors")
    require(host["source"]==PREFIX_SOURCE and native["complete_shared_prefix"],"prefix actual body")
    require(all(x["returncode"]==0 and not x["timed_out"] for x in inner["commands"]),"prefix inner commands")
    state=host["container_terminal"]["State"]
    require(not state["Running"] and not state["OOMKilled"] and state["ExitCode"]==0 and not state["Error"],"prefix container")
    previous.prefix_complete(native["phase_results"],native["phase_results"]["ownership"]["native_ownership"])
    require(native["phase_results"]["fixed-audit"]["timing_contract"]==dict(
        accepted=False,clock_periods_ns=[20,4,8,8],derating_percent=5,new_RC_STA_required=True),
        "original timing contract")
    require(native["phase_results"]["ownership"]["initial_original_class_DRT"]["marker_count"]==3,
        "original three-short input")
    frozen=saved(root,"frozen-prefix");inv=saved(root,"frozen-prefix-inventory")
    require(frozen["files"]==FROZEN_COUNT and frozen["unpacked_bytes"]==FROZEN_BYTES
        and len(inv["files"])==FROZEN_COUNT and sum(x["bytes"] for x in inv["files"].values())==FROZEN_BYTES,"full frozen census")
    require(inv["canonical_root"]=="/work" and inv["original_engine"]==ENGINE and inv["original_input"]==INPUT,"frozen identity")
    require(inv["files"]["out/work/fixed.odb"]["sha256"]==FROZEN_FIXED_SHA
        and inv["files"]["out/work/repair.tcl"]["sha256"]==FROZEN_REPAIR_SHA,"frozen prepared identities")
    validate_prefix_joins(root,host,inner,native,frozen,inv)
    return inv

def envelope(root,run,jobs,release,tag):
    require(run["id"]==PREFIX_RUN and run["head_sha"]==PREFIX_SOURCE and run["run_attempt"]==1
        and run["status"]=="completed" and run["conclusion"]=="success"
        and run["head_branch"]==previous.BRANCH and run["event"]=="workflow_dispatch"
        and run["workflow_id"]==400507406
        and run["path"]==".github/workflows/mainchip-fixed-engine-route-prefix.yml","prefix run")
    expected_jobs={123412973909:"source-controls",123413211875:"preserve-source-job-log",123413288178:"native-prefix"}
    require(len(jobs["jobs"])==3 and {j["id"]:j["name"]for j in jobs["jobs"]}==expected_jobs
        and all(j["conclusion"]=="success" and j["status"]=="completed"for j in jobs["jobs"]),"prefix jobs")
    for j in jobs["jobs"]:
        record=decode(secure_file(root,PREFIX+str(j["id"])+".job.json").read_bytes())
        require(j==record and j["head_sha"]==PREFIX_SOURCE and j["run_id"]==PREFIX_RUN
            and j["run_attempt"]==1,"prefix full job identity")
        require(all(s["status"]=="completed"and s["conclusion"]in ("success","skipped")for s in j["steps"]),"prefix job step failure")
    require(release["id"]==PREFIX_RELEASE and release["tag_name"]==PREFIX_TAG
        and release["draft"] is False and release["prerelease"] is True,"prefix release")
    require(tag["object"]["type"]=="commit" and tag["object"]["sha"]==PREFIX_SOURCE,"prefix lightweight tag")
    validate_release(release,tag,PREFIX_TAG,PREFIX_SOURCE)
    expected=saved(root,"release")
    project=lambda r:{a["name"]:(a["id"],a["size"],a["digest"]) for a in r["assets"]}
    require(len(release["assets"])==len(expected["assets"])==len(project(release))
        and project(release)==project(expected),"complete prefix assets")
    return dict(run=PREFIX_RUN,source=PREFIX_SOURCE,release=PREFIX_RELEASE,tag=PREFIX_TAG,all_assets=project(release))

def frozen_unchanged(work,inv):
    for p,row in inv["files"].items():
        require(fingerprint(secure_file(work,p))==row,"frozen input changed: "+p)
    return dict(files=len(inv["files"]),bytes=sum(x["bytes"] for x in inv["files"].values()))

def command(phase):
    require(phase in PHASES,"unapproved tail phase")
    root="/work/out/work";elf="/work/engine/openroad"
    scripts={"one-two-signal-routing-attempt":"repair.tcl",
       "paired-original-class-return":"unfix.tcl","full-original-class-read-only-DRT":"final-drc.tcl"}
    if phase in scripts:return [elf,"-no_init","-exit",root+"/"+scripts[phase]]
    return [elf,"-no_init","-exit","-python","/work/tail-source/scripts/mainchip_fixed_engine_route_tail_native.py"]

def complete(records):
    import mainchip_two_signal_repair as repair
    require(set(records)==set(STATUSES),"tail result census")
    for phase,status in STATUSES.items():
        r=records[phase]
        require(r["status"]==status and r["accepted"] is False
            and r["timing_accepted"] is False and r["full_phy_accepted"] is False,"tail original status/scope")
    gate=repair.require_complete(records["drc-audit"])
    return dict(original_audits_complete=True,original_gate=gate,
        physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)

def compare_cases(off,on):
    for value,case in (("off",off),("on",on)):
        require(case["schema"]=="built-engine-route-tail-case-v1" and case["mode"]==value
            and case["status"]=="PASS_COMPLETE_ROUTE_TAIL_DIAGNOSTIC" and not case["terminal_errors"],"complete tail case")
        require(case["stage"]=="audit" and case["route_lineage"]["authenticated_complete_route"] is True,
            "audited route lineage")
        require(case["engine"]==ENGINE and case["frozen_input"]==off["frozen_input"],"same frozen input and ELF")
        require(case["prefix_source"]==PREFIX_SOURCE and case["prefix_run"]==PREFIX_RUN,"same prefix")
        require(case["original_audits"]["original_audits_complete"] is True,"original audits")
        require(case["physical_acceptance"] is False and case["timing_accepted"] is False
            and case["full_phy_accepted"] is False,"comparison acceptance scope")
        require(set(case["geometry_files"])==set(COMPARE_FILES),"complete geometry projection")
    require(off["source"]==on["source"] and off["run_id"]==on["run_id"],"same successor source/run")
    require(off["observer"]=={"enabled":False,"witness_files":0},"off environment")
    require(on["observer"]["enabled"] is True and on["observer"]["writer_raw_join"] is True
        and on["observer"]["diagnosis"]["status"]=="COMPLETE_DIAGNOSTIC_ONLY"
        and len(on["observer"]["diagnosis"]["stages"])==4,"on complete witness")
    geometry_equal=off["geometry_files"]==on["geometry_files"]
    drc_equal=off["complete_drc"]==on["complete_drc"]
    return dict(schema="built-engine-route-tail-comparison-v1",
        status="PASS_OBSERVER_OFF_ON_OUTPUT_EQUIVALENCE_ONLY" if geometry_equal and drc_equal
            else "FAIL_OBSERVER_OFF_ON_OUTPUT_EQUIVALENCE",
        source=off["source"],run_id=off["run_id"],engine=ENGINE,
        frozen_input=off["frozen_input"],geometry_files_equal=geometry_equal,
        complete_original_class_DRC_equal=drc_equal,
        actual_off_DRC=off["complete_drc"],actual_on_DRC=on["complete_drc"],
        observed_equivalence=geometry_equal and drc_equal,
        physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
        root_cause_established=False,automatic_continuation_authorized=False)


def validate_reservation(proof,ctx,empty):
    require(type(proof["release_id"])is int and proof["release_id"]>0 and
        proof["externally_reserved"]is True and proof["creation_attempted"]is False and
        proof["assets_overwritten"]is False and proof["target_verified"]is True,"reserved-only tail publication")
    require(proof["tested_source"]==ctx["source"]and
        proof["tag"]=="cloud-results-"+ctx["token"]+"-"+group(ctx["mode"],ctx["stage"]),"new source/tag reservation")
    require(type(proof["existing_assets"])is list and(not empty or proof["existing_assets"]==[]),
        "release must be empty before acquisition")
    return proof

def direct_plan(out,optional):
    plan=previous.direct_plan(out,optional)
    names=set()
    for row in plan["files"]:
        row["asset_name"]=Path(row["name"]).name
        if row["disposition"]=="direct":
            require(row["asset_name"]not in names,"duplicate direct asset basename")
            names.add(row["asset_name"])
    return plan


def validate_prefix_joins(root,host,inner,native,frozen,inv):
    receipt=saved(root,"receipt")
    direct={p[len(PREFIX+"direct/"):]:secure_file(root,p).read_bytes()
        for p in PREFIX_REQUIRED if p.startswith(PREFIX+"direct/")}
    require(all(p.endswith(".json")for p in direct),"prefix direct JSON only")
    release=saved(root,"release");assets={a["name"]:a for a in release["assets"]}
    for p,raw in direct.items():
        a=assets[p]
        require(a["state"]=="uploaded"and a["size"]==len(raw)and a["digest"]=="sha256:"+digest(raw),"prefix direct release join: "+p)
    require(digest(direct["method.json"])==PRIOR_SHA and direct["method.json"]==secure_file(root,PRIOR).read_bytes(),"prefix actual method bytes")
    m=decode(direct["method.json"])
    require(m["native_prefix_authorized"]is True and m["controller_ready"]is True
        and len(m["protected"])==1098,"prefix actual native authority")
    context=dict(source=PREFIX_SOURCE,token=str(PREFIX_RUN)+"-1")
    bounds={}
    for job in ("source-controls","native-prefix"):
        directory=Path(root)/PREFIX/"controls"/job
        index=decode(secure_file(directory,"index.json").read_bytes())
        require(len(index)==4,"prefix complete control index")
        for name,row in index.items():
            raw=secure_file(directory,name).read_bytes()
            require(row["present"]is True and row["path"]==name
                and row["bytes"]==len(raw)and row["sha256"]==digest(raw),"prefix indexed control bytes")
        ctx=decode(secure_file(directory,"fixed-prefix-control-context.json").read_bytes())
        require((ctx["source"],ctx["run_id"],ctx["attempt"],ctx["method_sha256"])==
            (PREFIX_SOURCE,PREFIX_RUN,1,PRIOR_SHA)and ctx["source_controls_only"]is True
            and ctx["native_executed"]is False,"prefix exact source control context")
        bounds[job]=previous.control_evidence(directory,context)
    require(bounds["native-prefix"]==saved(root,"current-source-controls")==host["current_source_controls"],
        "prefix native repeated control join")
    # Separate hosted jobs may record different temporary-path exception text.
    # Each complete report is authenticated and validated above in its own context.
    for name,row in bounds["native-prefix"].items():
        require(direct[name]==secure_file(Path(root)/PREFIX/"controls/native-prefix",name).read_bytes(),"prefix copied control bytes")
    for record in (host,inner,native):
        require(all(a["completed"]is True for a in record["terminal_actions"]),"prefix complete cleanup")
        require(all(record[k]is False for k in ("physical_acceptance","observer_equivalence_qualified","native_routing_executed")),"prefix terminal scope")
    require(all(x["returncode"]==0 and "error"not in x and not x.get("timed_out",False)for x in host["commands"]),"prefix host commands")
    require([x["label"]for x in inner["commands"]]==["version","ldd","tcl-smoke","shared-prefix"],"prefix actual inner commands")
    require([x["label"]for x in native["commands"]]==list(previous.PHASES),"prefix actual phase ordering")
    for x in native["commands"]:
        require(x["returncode"]==0 and x["requested_timeout_seconds"]==1200
            and x["supervision_failure"]is None and x["memory_read_error"]is None
            and not x["process_group_cleanup"]["remaining_live"],"prefix original phase guard")
    runtime=saved(root,"runtime-dependencies")
    require(runtime==saved(root,"runtime-observed")==previous.expected_engine(root)["runtime"]and len(runtime)==104,"prefix actual runtime")
    require(inner["runtime_before"]==inner["runtime_after"]==dict(count=104,exact_paths_sizes_hashes=True),"prefix unchanged runtime")
    require(saved(root,"runtime-qualification")==host["runtime_qualification"]==previous.runtime_qualification(root),"prefix qualified new engine runtime")
    for g in (inner["cgroup_initial"],inner["cgroup_terminal"]):
        require((g["memory.max"],g["memory.swap.max"],g["pids.max"],g["cpu.max"])==
            (str(MEMORY),"0",str(PIDS),"200000 100000"),"prefix resource limits")
        require(all(g["memory.events"].get(k,0)==0 for k in ("oom","oom_kill","oom_group_kill")),"prefix OOM")
    require(int(inner["cgroup_terminal"]["memory.peak"])<=MEMORY,"prefix peak memory")
    terminal=saved(root,"container-terminal")
    require(host["container_terminal"]==terminal and terminal["Image"]==IMAGE_ID
        and terminal["Config"]["Labels"]["nssoc.build.source"]==PREFIX_SOURCE
        and terminal["State"]["Pid"]==0,"prefix actual container identity")
    engine=saved(root,"engine-restoration")
    require(engine["all_regular_members_verified"]is True and engine["all_files"]==previous.expected_engine(root)["files"]
        and len(engine["all_files"])==100 and engine["all_files"]["openroad"]==ENGINE,"prefix full engine restoration")
    inp=saved(root,"input-restoration");ii=inp["inventory"]
    require(inp["original_failed_result_preserved"]is True and inp["envelope"]["run"]==40344497930
        and inp["envelope"]["original_conclusion"]=="failure","prefix original failure retained")
    require(ii["complete_original_inventory_verified_before_analysis"]is True and len(ii["all_original_files"])==94
        and ii["selected_files"]["work/drc-observed.odb"]==INPUT,"prefix full original input")
    require(frozen==host["frozen_native_workspace"]
        and frozen["status"]=="PASS_FROZEN_PREPARED_NATIVE_WORKSPACE_NOT_ROUTING_ACCEPTANCE","prefix complete freeze")
    require(frozen["inventory"]==dict(bytes=len(direct["frozen-prefix-inventory.json"]),
        sha256=digest(direct["frozen-prefix-inventory.json"])),"prefix full frozen inventory bytes")
    require(inv["files"]["engine/openroad"]==ENGINE and inv["files"]["input.odb"]==INPUT,"prefix frozen native identity")
    require(inv["source_inventory_method"]==inv["files"]["source/"+PRIOR]==
        dict(bytes=len(direct["method.json"]),sha256=PRIOR_SHA),"prefix frozen source method")
    require({p.removeprefix("source/")for p in inv["files"]if p.startswith("source/")}==
        set(m["protected"])|{PRIOR},"complete frozen source projection")
    require(all(inv["files"]["source/"+p]["sha256"]==h for p,h in m["protected"].items()),"prefix frozen protected source bytes")
    require(all(inv[k]is False for k in ("native_routing_executed","physical_acceptance","observer_equivalence_qualified"))
        and frozen["native_routing_executed"]is False and frozen["physical_acceptance"]is False,"prefix frozen scope")
    reservation=saved(root,"release-reservation")
    require(reservation["release_id"]==PREFIX_RELEASE and reservation["tag"]==PREFIX_TAG
        and reservation["tested_source"]==PREFIX_SOURCE and reservation["existing_assets"]==[]
        and reservation["externally_reserved"]is True and reservation["target_verified"]is True
        and reservation["creation_attempted"]is False and reservation["assets_overwritten"]is False,"prefix reserved before acquisition")
    outputs=saved(root,"outputs")
    require(outputs["source"]==PREFIX_SOURCE and outputs["physical_acceptance"]is False,"prefix output scope")
    for name,raw in direct.items():
        if name not in ("outputs.json","parts.json"):
            require(outputs["files"][name]==dict(bytes=len(raw),sha256=digest(raw)),"prefix output/direct join: "+name)
    full=dict(outputs["files"]);full["outputs.json"]=dict(bytes=len(direct["outputs.json"]),sha256=digest(direct["outputs.json"]))
    require(saved(root,"complete-native-restore-map")==full
        and full["frozen-native-workspace.tar.gz"]==frozen["archive"],"prefix complete archive map")
    parts=saved(root,"parts");names=set();total=0
    require(1<=len(parts["parts"])<=32,"prefix part census")
    for i,part in enumerate(parts["parts"]):
        name="route-prefix-evidence.tar.gz.part%03d"%i
        require(part["name"]==name and type(part["bytes"])is int and 0<part["bytes"]<=512*1024**2
            and(i==len(parts["parts"])-1 or part["bytes"]==512*1024**2),"prefix ordered parts")
        a=assets[name];require(a["size"]==part["bytes"]and a["digest"]=="sha256:"+part["sha256"]
            and a["state"]=="uploaded","prefix immutable part metadata")
        names.add(name);total+=part["bytes"]
    require(parts["archive"]["bytes"]==total and set(assets)==set(direct)|names,"prefix complete assets")
    for key in ("native_routing_executed","observer_equivalence_qualified","physical_acceptance","timing_accepted","full_phy_accepted"):
        require(receipt[key]is False,"prefix cannot accept later stages")
    return dict(run=PREFIX_RUN,source=PREFIX_SOURCE,release_id=PREFIX_RELEASE,
        frozen_files=FROZEN_COUNT,frozen_unpacked_bytes=FROZEN_BYTES,prefix_qualified=True,
        native_routing_executed=False,physical_acceptance=False)

def control_evidence(root,ctx):
    require(False,"pending actual successor source control binding")
