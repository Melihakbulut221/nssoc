#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual qualified FIXED-guard ELF prefix; unchanged original clock/target gates."""
import os
from pathlib import Path
import re
import mainchip_fixed_engine_runtime_contract as previous
import mainchip_built_engine_route_prefix_contract as original
from mainchip_fixed_engine_runtime_contract import (
 require,secure_file,digest,decode,atomic_record,attempt,finish_record,error_record,
 IMAGE,IMAGE_ID,MEMORY,CPUS,PIDS,create_argv,validate_image,validate_container,
 expected_engine,engine_envelope,engine_extract,runtime_match,ENGINE,INPUT,INPUT_MEMBER,PREFIX,REPOSITORY,
 ENGINE_RUN,ENGINE_RELEASE,ENGINE_TAG,RUNTIME_SOURCE,direct_plan)
ROOT=Path(__file__).resolve().parent.parent
METHOD="scripts/mainchip-fixed-engine-route-prefix-methods.json"
GROUP="mainchip-fixed-engine-route-prefix"
BRANCH="codex/mainchip-fixed-engine-route-prefix"
SCHEMA="mainchip-fixed-engine-route-prefix-v1"
PRIOR="scripts/mainchip-fixed-engine-runtime-probe-methods.json"
PRIOR_SHA="f8609a955031737a851237e44b8f453249aa50fdaa143af2cfdfb4e8e275b33d"
SOURCE_ADMISSION="docs/evidence/mainchip-fixed-engine-route-prefix-source-admission-20261029.json"
LIMITS=original.LIMITS
PHASES=original.PHASES
PASS_STATUSES=original.PASS_STATUSES
CANONICAL_OUT=original.CANONICAL_OUT
RUNTIME_PREFIX="docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/"
RUNTIME_RUN=40858216637
RUNTIME_SOURCE_SHA="1812666a357bb8aca75bcfc5e1c523106ad7b08e"
RUNTIME_RELEASE=427727176
RUNTIME_RECEIPT_SHA="d7a4bccbf2437eaa836955c77cb1013e0ea2e701c01c922e13217ddc701dd10a"
RUNTIME_BINDING=dict(run=RUNTIME_RUN,source=RUNTIME_SOURCE_SHA,release_id=RUNTIME_RELEASE,receipt_sha256=RUNTIME_RECEIPT_SHA)
RUNTIME_REQUIRED={"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/123394514595.job.json":{"bytes":2967,"sha256":"6eb0d3489451e5f46cbb4272520a601c2decc880979c4760d7ddf08d61e41869"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/123394514595.job.log":{"bytes":85369,"sha256":"3b5d53ce43a6007b0deb8ef669f7e9ecd0390c8bbee55a9e6490d2e640f880aa"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/123394742379.job.json":{"bytes":1992,"sha256":"7b4927c857363ccc014c15f7b521198c2cbe7b6663e03229ea511047ebde3929"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/123394742379.job.log":{"bytes":9022,"sha256":"966086361c2fe25ba292588dfd6c44d65e0db83ea93c8288d12bab9a06ac344f"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/123394818085.job.json":{"bytes":3726,"sha256":"a8eb72d2fa0a8dc2e70bf4bcf973de8b97f271ec2862c8ffa480eda87260b26f"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/123394818085.job.log":{"bytes":93296,"sha256":"2345afef6dec7822fa48fe9499a010060024aa1d091ab7fc6bb36bd5bb026dad"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/artifacts.json":{"bytes":3705,"sha256":"096e5050b7548936f16292196ded61ff51b02e599ef7db13bc252661277f4e4e"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/complete-native-restore-map.json":{"bytes":6058,"sha256":"de9d4f3d62acefe0354f0962f81ab2aca3654998f8483c1a2d3efabb7cad7a21"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/native-probe/index.json":{"bytes":1551,"sha256":"fb80395b86f429a9de176bb1b389ebd092235bd2642490e138a740a227e1b425"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/native-probe/runtime-control-context.json":{"bytes":247,"sha256":"a1cacb33a73b269d804ce9bc5d768082ad9997372298a3d9081e32b3cfb0a89f"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/native-probe/runtime-host-controls.json":{"bytes":14712,"sha256":"0c084cd12e25102697a7e26cfb915a119bd30eaa1abf49aac81dfd427e1f83d0"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/native-probe/runtime-host-controls.stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/native-probe/runtime-host-controls.stdout":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/native-probe/runtime-probe-controls.json":{"bytes":29412,"sha256":"1ae43304e870bf4b0aae04865f603f404cf55c92936a6e427475f96254858903"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/native-probe/runtime-probe-controls.stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/native-probe/runtime-probe-controls.stdout":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/source-controls/index.json":{"bytes":1551,"sha256":"fb80395b86f429a9de176bb1b389ebd092235bd2642490e138a740a227e1b425"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/source-controls/runtime-control-context.json":{"bytes":247,"sha256":"a1cacb33a73b269d804ce9bc5d768082ad9997372298a3d9081e32b3cfb0a89f"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/source-controls/runtime-host-controls.json":{"bytes":14712,"sha256":"0c084cd12e25102697a7e26cfb915a119bd30eaa1abf49aac81dfd427e1f83d0"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/source-controls/runtime-host-controls.stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/source-controls/runtime-host-controls.stdout":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/source-controls/runtime-probe-controls.json":{"bytes":29412,"sha256":"1ae43304e870bf4b0aae04865f603f404cf55c92936a6e427475f96254858903"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/source-controls/runtime-probe-controls.stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/controls/source-controls/runtime-probe-controls.stdout":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/api-identity-census.json":{"bytes":83214,"sha256":"6cfbfb655a152619ee031d358179fbf15283fb1037389028b45e0c048eb687c7"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/container-initial.json":{"bytes":6301,"sha256":"854c4d3598c08b39ad42c288f7f67e9b1d9cd0485c37a645517765d0f43baa95"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/container-terminal.json":{"bytes":6862,"sha256":"7d289da1f122fca65476fee2dd1c15b0c8b2d620ac3003163bd42b0d1ca4c295"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/current-source-controls.json":{"bytes":284,"sha256":"c3b6c5bb9faf0f2d82e42267cab7060b02c2090eb5d458178ae5075a5001203d"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/direct-publication-plan.json":{"bytes":4377,"sha256":"cb32a1c94ba14ec9d6b139347e36634e579d2d5462adc09bc4d886e6c52de761"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/engine-restoration.json":{"bytes":14357,"sha256":"c291f43ffa1cb03b0a1a6a706189bd8ca481b3c36eb88eda216a5ace0d457ee0"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/engine-source-envelope.json":{"bytes":361,"sha256":"80d8df02aa043aca8e8a50ff2b36362646137612428e54fbb5e6ede8f8ca3afd"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/host-result.json":{"bytes":18050,"sha256":"1df63ebe41bd18ee588d5c67a9f0a9fa52e90247cc7f95bcc474700b5abf3d15"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/inner-result.json":{"bytes":9705,"sha256":"53aab43b9d257de82442918150f56e9d0ba8f49d7ae992a3d3b85601a44f1880"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/input-restoration.json":{"bytes":24377,"sha256":"38fd8b7d7280fe5851270c2a4770000b82727dc631a34c36ddf101a1fc22e596"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/method.json":{"bytes":159374,"sha256":"f8609a955031737a851237e44b8f453249aa50fdaa143af2cfdfb4e8e275b33d"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/outputs.json":{"bytes":6390,"sha256":"5f17b4f85e0731d2afb4e47ba2d45878979d674ae3eb367077eddb3519f3846b"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/parts.json":{"bytes":316,"sha256":"d991a63f73838ca48a861840151d6680e6088e16b64f4a6e25c1296daf2a38e0"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/publication-availability.json":{"bytes":785,"sha256":"dc99a78a671adb656dc9a2b2939c9dd8f48f08647b477b6aa6548abbaae87158"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/release-reservation.json":{"bytes":336,"sha256":"59ded5ea9d413c826f828a352cd6e2b8aafa208e89b19395bc7e6ee3d9f5e5fe"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/runtime-dependencies.json":{"bytes":16940,"sha256":"6651a9b0b0059ed4b6ebfa5cb016a2ce08c146196d357fa1283ebf57eb6619a0"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/runtime-host-controls.json":{"bytes":14712,"sha256":"0c084cd12e25102697a7e26cfb915a119bd30eaa1abf49aac81dfd427e1f83d0"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/runtime-observed.json":{"bytes":16940,"sha256":"6651a9b0b0059ed4b6ebfa5cb016a2ce08c146196d357fa1283ebf57eb6619a0"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/direct/runtime-probe-controls.json":{"bytes":29412,"sha256":"1ae43304e870bf4b0aae04865f603f404cf55c92936a6e427475f96254858903"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/jobs.json":{"bytes":9799,"sha256":"282d2c31420376af3b27c06a19b06222a7c3c0f7202d2950c39c7a07118d40a1"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/release.json":{"bytes":42992,"sha256":"9b17dde2778ab382ba94b234f7c215117f0865000a5a36406c97729704dda326"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/run.json":{"bytes":14407,"sha256":"fa7d5db4f31a261978c2be7f0d19aef55d9f2a97214f3947dae2b944367267a1"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/tag-ref.json":{"bytes":575,"sha256":"b89ddb05b057dd8ff71c098cf7ba6e8822cba51e5d0bd1400de61efd4416d091"},"docs/evidence/mainchip-fixed-engine-runtime-native-terminal-20261029/receipt.json":{"bytes":13519,"sha256":"d7a4bccbf2437eaa836955c77cb1013e0ea2e701c01c922e13217ddc701dd10a"}}
NEW_FILES=(
 "scripts/mainchip_fixed_engine_route_prefix_contract.py",
 "scripts/cloud_mainchip_fixed_engine_route_prefix.py",
 "scripts/mainchip_fixed_engine_route_prefix_inner.py",
 "scripts/mainchip_fixed_engine_route_prefix_driver.py",
 "scripts/mainchip_fixed_engine_route_prefix_native.py",
 "scripts/check_mainchip_fixed_engine_route_prefix.py",
 "scripts/mainchip_exit_checked_supervision.py",
 "scripts/check_mainchip_exit_checked_supervision.py",
 ".github/workflows/mainchip-fixed-engine-route-prefix.yml",SOURCE_ADMISSION)
AUTH_FALSE=("native_routing_authorized","engine_build_authorized","native_probe_authorized",
 "rc_sta_execution_authorized","physical_acceptance","timing_accepted","full_phy_accepted",
 "observer_equivalence_qualified")

def context(env):
    require(env.get("GITHUB_ACTIONS")=="true" and env.get("RUNNER_OS")=="Linux"
            and env.get("RUNNER_ENVIRONMENT")=="github-hosted","hosted Linux only")
    require(env.get("GITHUB_REPOSITORY")==REPOSITORY,"repository identity")
    require(env.get("GITHUB_EVENT_NAME")=="workflow_dispatch","manual prefix only")
    require(env.get("GITHUB_RUN_ATTEMPT")=="1","no retry")
    require(re.fullmatch("[1-9][0-9]*",env.get("GITHUB_RUN_ID",""))is not None,"run identity")
    require(re.fullmatch("[0-9a-f]{40}",env.get("GITHUB_SHA",""))is not None,"source identity")
    require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"route prefix branch")
    token=env["GITHUB_RUN_ID"]+"-1"
    # Inherited Docker ownership name only; this job performs no compilation.
    return dict(name="nssoc-witness-build-"+token,source=env["GITHUB_SHA"],token=token)



def validate_method(m,prior):
    require(m["schema"]==SCHEMA and m["branch"]==BRANCH and m["group"]==GROUP,"prefix method identity")
    require(m["limits"]==LIMITS and m["image"]==IMAGE and m["image_id"]==IMAGE_ID,"prefix limits/image")
    require(m["engine"]==ENGINE and m["input"]==INPUT,"prefix immutable input identities")
    require(m["phases"]==list(PHASES),"only exact shared prefix")
    for key in ("source_controls_authorized","native_prefix_authorized","controller_ready"):
        require(type(m[key])is bool,"typed prefix authority: "+key)
    require(m["controller_ready"]==m["native_prefix_authorized"],"prefix native/controller agreement")
    require(not m["native_prefix_authorized"]or m["source_controls_authorized"],"prefix native requires source controls")
    require(all(m[k]is False for k in AUTH_FALSE),"prefix scope")
    require(m["qualified_routing_engine"]is None,"prefix cannot qualify routing")
    require(m["runtime_qualified"]is True and m["qualified_runtime"]==RUNTIME_BINDING,"actual new runtime binding")
    require(m["prior_method_sha256"]==PRIOR_SHA and m["protected"].get(PRIOR)==PRIOR_SHA,"prior runtime method binding")
    require(len(prior["protected"])==1022 and m["inherited_protected_count"]==1022,"inherited 1022 runtime sources")
    require(all(m["protected"].get(p)==h for p,h in prior["protected"].items()),"inherited runtime source protection removed")
    require(set(NEW_FILES)<=set(m["protected"]),"required new prefix source pins")
    for path,row in RUNTIME_REQUIRED.items():
        require(m["protected"].get(path)==row["sha256"],"protected actual runtime proof: "+path)
    return m

def method(root):
    raw=secure_file(root,PRIOR).read_bytes()
    require(digest(raw)==PRIOR_SHA,"immutable qualified runtime method")
    prior=previous.method(root)
    m=validate_method(decode(secure_file(root,METHOD).read_bytes()),prior)
    for p,h in m["protected"].items():
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h)is not None and
          digest(secure_file(root,p).read_bytes())==h,"protected prefix source: "+p)
    runtime_qualification(root)
    return m

def authorize_prefix(m):
    require(m["source_controls_authorized"]is True and m["native_prefix_authorized"]is True
      and m["controller_ready"]is True,"native prefix not authorized")
    require(all(m[k]is False for k in AUTH_FALSE),"prefix scope")
    return m

def runtime_qualification(root=ROOT):
    raw={}
    require(len(RUNTIME_REQUIRED)==48,"complete runtime proof census")
    for path,row in RUNTIME_REQUIRED.items():
        b=secure_file(root,path).read_bytes()
        require(dict(bytes=len(b),sha256=digest(b))==row,"runtime proof bytes: "+path)
        require(path.startswith(RUNTIME_PREFIX),"runtime proof namespace")
        raw[path[len(RUNTIME_PREFIX):]]=b
    docs={p:decode(b)for p,b in raw.items()if p.endswith(".json")}
    receipt=docs["receipt.json"];run=docs["run.json"];jobs=docs["jobs.json"]["jobs"]
    require(receipt["files"]=={p:r for p,r in RUNTIME_REQUIRED.items()if p!=RUNTIME_PREFIX+"receipt.json"},"complete actual runtime receipt")
    require((receipt["run"],receipt["source"],receipt["attempt"],receipt["terminal"],receipt["release_id"])==
      (RUNTIME_RUN,RUNTIME_SOURCE_SHA,1,"success",RUNTIME_RELEASE),"runtime receipt identity")
    require(receipt["runtime_qualified"]is True and receipt["protected_source_files"]==1022
      and receipt["method_sha256"]==PRIOR_SHA,"runtime receipt scope")
    require((run["id"],run["head_sha"],run["run_attempt"],run["status"],run["conclusion"])==
      (RUNTIME_RUN,RUNTIME_SOURCE_SHA,1,"completed","success"),"actual runtime run")
    require(run["workflow_id"]==400465702 and run["path"]==".github/workflows/mainchip-fixed-engine-runtime-probe.yml"
      and run["event"]=="workflow_dispatch"and run["head_branch"]==previous.BRANCH,"actual runtime workflow")
    expected_jobs={123394514595:"source-controls",123394742379:"preserve-source-job-log",123394818085:"native-probe"}
    require(len(jobs)==3 and {j["id"]:j["name"]for j in jobs}==expected_jobs,"actual runtime full jobs")
    for j in jobs:
        require(j==docs[str(j["id"])+".job.json"]and j["status"]=="completed"and j["conclusion"]=="success","runtime job terminal")
        require(j["head_sha"]==RUNTIME_SOURCE_SHA and j["run_attempt"]==1 and j["run_id"]==RUNTIME_RUN,"runtime job identity")
        require(all(s["status"]=="completed"and s["conclusion"]in ("success","skipped")for s in j["steps"]),"runtime job step failure")
    direct={p.removeprefix("direct/"):b for p,b in raw.items()if p.startswith("direct/")}
    require(len(direct)==19 and all(p.endswith(".json")for p in direct),"runtime full direct JSON census")
    records={p:decode(b)for p,b in direct.items()}
    release=docs["release.json"];tag=docs["tag-ref.json"]
    name="cloud-results-"+str(RUNTIME_RUN)+"-1-"+previous.GROUP
    require(release["id"]==RUNTIME_RELEASE and release["tag_name"]==name
      and release["target_commitish"]==RUNTIME_SOURCE_SHA and release["draft"]is False and release["prerelease"]is True,"actual runtime release")
    require(tag["ref"]=="refs/tags/"+name and tag["object"]["type"]=="commit"and tag["object"]["sha"]==RUNTIME_SOURCE_SHA,"actual runtime tag")
    assets={a["name"]:a for a in release["assets"]}
    require(len(assets)==len(release["assets"])==20,"runtime exact release census")
    for p,b in direct.items():
        a=assets[p]
        require(a["state"]=="uploaded"and a["size"]==len(b)and a["digest"]=="sha256:"+digest(b),"runtime direct asset: "+p)
    expected_context=dict(source=RUNTIME_SOURCE_SHA,run_id=RUNTIME_RUN,attempt=1,source_controls_only=True,native_executed=False)
    for job in ("source-controls","native-probe"):
        index=docs["controls/"+job+"/index.json"]
        require(len(index)==7,"runtime complete source index")
        for p,v in index.items():
            b=raw["controls/"+job+"/"+p]
            require(v["present"]is True and v["path"]==p and v["bytes"]==len(b)and v["sha256"]==digest(b),"runtime indexed source bytes")
        for p in ("runtime-probe-controls.json","runtime-host-controls.json"):
            value=docs["controls/"+job+"/"+p]
            require(value["current_context"]==expected_context and all(value[k]is False for k in ("native_executed","runtime_qualified","physical_acceptance")),"runtime repeated control context")
        runtime=docs["controls/"+job+"/runtime-probe-controls.json"]
        host_control=docs["controls/"+job+"/runtime-host-controls.json"]
        require(runtime["status"]=="PASS_FIXED_ENGINE_RUNTIME_SOURCE_CONTROLS"and
          (runtime["positive_count"],runtime["refusal_count"],runtime["process_lifecycle_count"],runtime["inner_main_lifecycle_count"])==(4,48,6,7),"runtime actual source controls")
        require(host_control["status"]=="PASS_FIXED_ENGINE_RUNTIME_HOST_SOURCE_CONTROLS"and
          (host_control["publication"]["count"],host_control["source_records"]["positive_count"],host_control["source_records"]["refusal_count"])==(7,1,13),"runtime actual host controls")
    for p in ("runtime-probe-controls.json","runtime-host-controls.json"):
        require(raw["controls/native-probe/"+p]==direct[p],"runtime native repeated source bytes")
    bound={p:dict(bytes=len(direct[p]),sha256=digest(direct[p]))for p in ("runtime-probe-controls.json","runtime-host-controls.json")}
    host=records["host-result.json"];inner=records["inner-result.json"];census=records["api-identity-census.json"]
    require(records["current-source-controls.json"]==host["current_source_controls"]==bound,"runtime current control join")
    require(digest(direct["method.json"])==PRIOR_SHA and direct["method.json"]==secure_file(root,PRIOR).read_bytes(),"actual runtime method bytes")
    require(host["source"]==RUNTIME_SOURCE_SHA and host["status"]=="PASS_BUILT_ENGINE_READ_ONLY_NATIVE_PROBE","actual runtime host pass")
    require(inner["status"]=="PASS_BUILT_ELF_RUNTIME_AND_ACTUAL_CHIP_READ_ONLY_CENSUS"and inner["complete_actual_native_probe"]is True,"actual runtime inner pass")
    require(census["status"]=="PASS_ACTUAL_DATABASE_LIFECYCLE_AND_FULL_READ_ONLY_CENSUS"
      and all(census[k]is True for k in ("database_created","database_read","database_destroyed","complete_census")),"actual database lifecycle")
    for value in (host,inner,census):
        require(not value["terminal_errors"]and all(a["completed"]is True for a in value["terminal_actions"]),"runtime complete cleanup")
        require(value["physical_acceptance"]is False and value["observer_equivalence_qualified"]is False,"runtime is not physical acceptance")
    require(all(x["returncode"]==0 and "error"not in x and not x.get("timed_out",False)for x in host["commands"]),"runtime host commands")
    require([x["label"]for x in inner["commands"]]==["version","ldd","tcl-smoke","actual-chip-census"]
      and all(x["returncode"]==0 and x["timed_out"]is False for x in inner["commands"]),"runtime native commands")
    actual=census["census"]
    require((actual["all_net_count"],actual["all_instance_count"],actual["complete_raw_opcode_data_pairs"])==
      (143820,153130,13905578),"runtime full original chip census")
    require(len(actual["complete_census_counts"])==len(actual["complete_census_sha256"])==14
      and actual["every_block_terminal_reconciled_with_connected_net_census"]is True
      and actual["every_raw_terminal_lookup_reconciled_with_both_censuses"]is True,"runtime full census categories")
    require(actual["ownership_eligible"]is False and actual["accepted"]is False and census["source_geometry_mutated"]is False,"runtime census scope")
    expected=expected_engine(root)
    require(records["runtime-dependencies.json"]==records["runtime-observed.json"]==expected["runtime"]
      and len(expected["runtime"])==104,"actual 104 runtime library identities")
    require(inner["runtime_before"]==inner["runtime_after"]==dict(count=104,exact_paths_sizes_hashes=True),"runtime before/after")
    for g in (inner["cgroup_initial"],inner["cgroup_terminal"]):
        require((g["memory.max"],g["memory.swap.max"],g["pids.max"],g["cpu.max"])==
          (str(MEMORY),"0",str(PIDS),"200000 100000"),"runtime unchanged resources")
        require(all(g["memory.events"].get(k,0)==0 for k in ("oom","oom_kill","oom_group_kill")),"runtime OOM")
    require(int(inner["cgroup_terminal"]["memory.peak"])<=MEMORY,"runtime peak memory")
    terminal=records["container-terminal.json"];state=terminal["State"]
    require(host["container_terminal"]==terminal and state["Running"]is False and state["Pid"]==0
      and state["OOMKilled"]is False and state["ExitCode"]==0 and state["Error"]=="","runtime stopped container")
    require(terminal["Image"]==IMAGE_ID and terminal["Config"]["Labels"]["nssoc.build.source"]==RUNTIME_SOURCE_SHA,"runtime actual container identity")
    restored=records["engine-restoration.json"]
    require(restored["all_regular_members_verified"]is True and len(restored["all_files"])==100
      and restored["all_files"]==expected["files"]and restored["all_files"]["openroad"]==ENGINE,"runtime complete new engine restoration")
    inp=records["input-restoration.json"];inventory=inp["inventory"]
    require(inp["original_failed_result_preserved"]is True and inp["envelope"]["run"]==40344497930
      and inp["envelope"]["original_conclusion"]=="failure","original failed input retained")
    require(inventory["complete_original_inventory_verified_before_analysis"]is True and len(inventory["all_original_files"])==94
      and inventory["selected_files"][INPUT_MEMBER]==INPUT,"runtime complete original ODB restoration")
    outputs=records["outputs.json"]
    require(outputs["source"]==RUNTIME_SOURCE_SHA and outputs["physical_acceptance"]is False and len(outputs["files"])==44,"runtime output map")
    for p,b in direct.items():
        if p not in ("outputs.json","parts.json"):
            require(outputs["files"][p]==dict(bytes=len(b),sha256=digest(b)),"runtime direct/output join: "+p)
    full=dict(outputs["files"]);full["outputs.json"]=dict(bytes=len(direct["outputs.json"]),sha256=digest(direct["outputs.json"]))
    require(docs["complete-native-restore-map.json"]==full and len(full)==45,"runtime full archive map")
    parts=records["parts.json"];require(len(parts["parts"])==1,"runtime archive part census")
    part=parts["parts"][0];a=assets[part["name"]]
    require(parts["archive"]==dict(bytes=part["bytes"],sha256=part["sha256"])
      and a["size"]==part["bytes"]and a["digest"]=="sha256:"+part["sha256"]and a["state"]=="uploaded","runtime immutable archive metadata")
    require(set(assets)==set(direct)|{part["name"]},"runtime no unexpected release assets")
    for k in ("native_routing_executed","observer_equivalence_qualified","physical_acceptance","timing_accepted","full_phy_accepted"):
        require(receipt[k]is False,"runtime proof cannot accept later stages")
    return dict(**RUNTIME_BINDING,runtime_qualified=True,proof_files=48,engine=ENGINE,input=INPUT,
      runtime_dependency_files=104,all_net_count=143820,all_instance_count=153130,
      native_routing_executed=False,physical_acceptance=False,observer_equivalence_qualified=False)

def validate_reservation(proof,ctx,empty):
    require(type(proof["release_id"])is int and proof["release_id"]>0 and
      proof["externally_reserved"]is True and proof["creation_attempted"]is False and
      proof["assets_overwritten"]is False and proof["target_verified"]is True,"reserved-only build publication")
    require(proof["tested_source"]==ctx["source"]and
      proof["tag"]=="cloud-results-"+ctx["token"]+"-"+GROUP,"new source/tag reservation")
    require(type(proof["existing_assets"])is list and(not empty or proof["existing_assets"]==[]),
      "release must be empty before acquisition")
    return proof


def command(phase,executable,out=CANONICAL_OUT):
    require(type(phase) is str and phase in PHASES,"unapproved prefix phase")
    require(executable=="/work/engine/openroad" and out==CANONICAL_OUT,"canonical native paths")
    if phase=="paired-all-nontarget-fixed-import":
        return [executable,"-no_init","-exit",out+"/fixed.tcl"]
    return [executable,"-no_init","-exit","-python","/work/source/scripts/mainchip_fixed_engine_route_prefix_native.py"]

def prefix_complete(records,ownership):
    import mainchip_two_signal_repair as repair
    require(set(records)==set(PASS_STATUSES),"prefix result census")
    for phase,status in PASS_STATUSES.items():
        row=records[phase]
        require(row["status"]==status and row["accepted"] is False and row["timing_accepted"] is False
                and row["full_phy_accepted"] is False,"prefix phase status/scope")
    repair.require_actionable(ownership)
    first=records["ownership"]
    require(first["original_gate"]["result"]["clock_or_fixed_nets"]==1691
            and first["original_gate"]["result"]["all_source_clock_and_fixed_records_preserved"] is True,"original clock gate")
    fixed=records["fixed-audit"]
    require(fixed["router_census"]["two_routed_nonfixed_guided_names"]==list(repair.TARGETS),"two-target routing boundary")
    return dict(status="PASS_PREPARED_SHARED_PREFIX_NOT_ROUTING_ACCEPTANCE",
                original_clock_count=1691,only_mutable=list(repair.TARGETS),
                native_routing_executed=False,physical_acceptance=False,observer_equivalence_qualified=False)


def control_evidence(root,ctx):
    name="fixed-route-prefix-controls.json"
    raw=secure_file(root,name).read_bytes();r=decode(raw)
    expected=dict(source=ctx["source"],run_id=int(ctx["token"].split("-")[0]),attempt=1,
      source_controls_only=True,native_executed=False)
    require(r["status"]=="PASS_FIXED_ENGINE_ROUTE_PREFIX_SOURCE_CONTROLS"
      and r["current_context"]==expected,"current prefix source context/status")
    require(all(r[k]is False for k in ("native_executed","native_prefix_executed","native_routing_executed",
      "actual_runtime_probe_executed","prefix_qualified","observer_equivalence_qualified","physical_acceptance")),"current prefix control scope")
    for key,positive,refusal in (("context_controls",1,11),("authority_controls",3,54)):
        require(r[key]["positive_count"]==positive and r[key]["refusal_count"]==refusal,"current prefix "+key)
    driver=r["actual_driver_controls"]
    require(driver["sequencing_count"]==6 and driver["lifecycle_count"]==8
      and driver["path_controls"]["positive_paths"]==3 and driver["path_controls"]["refused_paths"]==13
      and driver["path_controls"]["actual_native_executed"]is False and driver["native_executed"]is False,"current actual driver controls")
    proof=r["runtime_proof_controls"]
    require((proof["positive_count"],proof["proof_file_count"],proof["refusal_count"],proof["source_refusal_count"])==(1,48,50,5)
      and proof["actual_native_archive_acquired"]is False,"current runtime proof controls")
    publication=r["publication_controls"]
    require(publication["status"]=="PASS_ACTUAL_FAILURE_AND_EMPTY_PUBLICATION_CONTROLS"
      and publication["count"]==7 and publication["actual_new_prefix_publish_and_pack"]is True,"current prefix publication controls")
    old=r["original_prefix_controls"]
    require(old["status"]=="PASS_SHARED_PREFIX_SOURCE_CONTROLS"
      and(old["positive_count"],old["refusal_count"],len(old["sequencing_cases"]),old["lifecycle_count"])==(4,23,6,8)
      and all(old[k]is False for k in ("native_prefix_executed","native_routing_executed","physical_acceptance")),"original prefix controls")
    extra="exit-supervision-controls.json"
    eraw=secure_file(root,extra).read_bytes();e=decode(eraw)
    require(e["status"]=="PASS_EXIT_CHECKED_SUPERVISION_SOURCE_CONTROLS"
      and e["current_context"]==expected,"exit supervision exact source context/status")
    require(all(e[k]is False for k in ("native_executed","engine_executed","routing_accepted",
      "physical_acceptance","actual_failed_prefix_reclassified")),"exit supervision source-only scope")
    require((e["source"]["positive"],e["source"]["refusals"],e["source"]["authenticated_source_files"])==(2,9,6),
      "exit supervision source authentication controls")
    require((e["derivation"]["positive"],e["derivation"]["refusals"])==(7,2),
      "exit supervision exact source derivation controls")
    require(e["snapshot"]["positive"]==5,"original snapshot behavior controls")
    require(e["terminal"]["cases"]==41 and e["terminal"]["old_body_regressions"]==1
      and len(e["terminal"]["rows"])==41 and e["terminal"]["command_budget_boundary_cases"]==6
      and e["terminal"]["command_budget_error_cases"]==3 and e["terminal"]["pre_fix_command_deadline_regressions"]==1,
      "actual terminal and independent command deadline controls")
    require((e["real_python"]["positive"],e["real_python"]["refusals"],
      e["real_python"]["real_short_python_children"])==(2,1,3),"real short Python process controls")
    original=e["original_supervisor"]
    require(original["status"]=="PASS_RECORD_TELEMETRY_SOURCE_AND_SUPERVISION_CONTROLS_NO_RTL"
      and len(original["controls"])==13 and all(v is True for v in original["controls"].values())
      and original["engineering_accepted"]is False,"unchanged original supervision controls")
    return {name:dict(bytes=len(raw),sha256=digest(raw)),extra:dict(bytes=len(eraw),sha256=digest(eraw))}
