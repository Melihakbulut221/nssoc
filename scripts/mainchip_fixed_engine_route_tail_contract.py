#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Same frozen prefix and built ELF; two diagnostic tails, never physical acceptance."""
import os
import re
from pathlib import Path
import mainchip_fixed_engine_route_prefix_contract as previous
import mainchip_exit_checked_command_evidence as command_evidence
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
PREFIX="docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/"
PREFIX_RUN=40878295979
PREFIX_SOURCE="a32414f76992f28c7d43794fac9680296f208eaf"
PREFIX_RELEASE=427875148
PREFIX_TAG="cloud-results-40878295979-1-mainchip-fixed-engine-route-prefix"
FROZEN_COUNT=1308
FROZEN_BYTES=4127248178
PREFIX_REQUIRED={'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/123462735615.job.json': {'bytes': 2980, 'sha256': 'aa8fc97950993d6a189d538957e26a708bc2cb5a0dad5fe71fadd4454c8c85c1'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/123462735615.job.log': {'bytes': 817718, 'sha256': '86078340dc69188c7b5a5e8bf188ef312479d7a7164fdb63b0d77277bbdeb515'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/123463296225.job.json': {'bytes': 1999, 'sha256': '912c8f3cc2a53b34d089210821cdd401f20d9b2d27e3715e686a5cdfe33c9700'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/123463296225.job.log': {'bytes': 9001, 'sha256': '39d79892172b9ad21cd337ce1f349578a7721ae7c510c7d9e7d01522b8729e95'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/123463392812.job.json': {'bytes': 3747, 'sha256': '80621737124605ecaf4025f2f1f77e0bd1c9d023204c2228c6a1bd9082c4a032'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/123463392812.job.log': {'bytes': 835803, 'sha256': 'ee484ce280b61c14dd20acd6464d0d53c32b542611d2a1b6d5e7b075acc0ec3c'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/artifacts.json': {'bytes': 3703, 'sha256': '6400b30010279b1af093a72ee7d27f6aeca2883daca4a4ad51071e4fb004ab94'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/complete-native-restore-map.json': {'bytes': 13225, 'sha256': '1666189512a98cf350ebe2348fe3527649e8acee6c3512a279582459727e951a'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/native-prefix/exit-supervision-controls.json': {'bytes': 18907, 'sha256': 'e100df1b145a3df409f2a927e04a127d4c1dbfc0a9e286096cd0153888af6437'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/native-prefix/exit-supervision-controls.stderr': {'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/native-prefix/exit-supervision-controls.stdout': {'bytes': 472613, 'sha256': 'fa3bf71f898c6ddd2fa2faa8d7a1f28121cc97bfb32079cc1f24b49ca49e397a'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/native-prefix/fixed-prefix-control-context.json': {'bytes': 247, 'sha256': '25e08808d2e1309d74da5a5ae5f02e734b298fda62af78cd768851346847c6ac'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/native-prefix/fixed-route-prefix-controls.json': {'bytes': 93258, 'sha256': '22528bf03ce10c97b9d14a64a2d4c84ef3f7336281978fd982fd8d27acbf81ef'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/native-prefix/fixed-route-prefix-controls.stderr': {'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/native-prefix/fixed-route-prefix-controls.stdout': {'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/native-prefix/index.json': {'bytes': 1622, 'sha256': 'e0ecbf64acd45d7c372bef8e25d0a8ceb75e8614e5b6990e9140681069fe62a8'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/source-controls/exit-supervision-controls.json': {'bytes': 18907, 'sha256': 'e100df1b145a3df409f2a927e04a127d4c1dbfc0a9e286096cd0153888af6437'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/source-controls/exit-supervision-controls.stderr': {'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/source-controls/exit-supervision-controls.stdout': {'bytes': 471754, 'sha256': '4b253e471ba09dfbd778a9cf5c99d2622ca143a8e3d9b0f2765f6ed90b42ce6d'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/source-controls/fixed-prefix-control-context.json': {'bytes': 247, 'sha256': '25e08808d2e1309d74da5a5ae5f02e734b298fda62af78cd768851346847c6ac'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/source-controls/fixed-route-prefix-controls.json': {'bytes': 93258, 'sha256': '22528bf03ce10c97b9d14a64a2d4c84ef3f7336281978fd982fd8d27acbf81ef'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/source-controls/fixed-route-prefix-controls.stderr': {'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/source-controls/fixed-route-prefix-controls.stdout': {'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/controls/source-controls/index.json': {'bytes': 1622, 'sha256': 'cf79fd35d75384fd83d3ea8bcd38e2b718a3cf1d423ed41f1fa08e55f45b459b'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/container-initial.json': {'bytes': 6300, 'sha256': '6608fa49abbdbc3da48632c7914b73b6e05081ea754263de204ed61d277e6df4'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/container-terminal.json': {'bytes': 6860, 'sha256': '1c080628422a0c3c87cb580287197651b97fa3b87c09b3be48ac09fb8698f360'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/current-source-controls.json': {'bytes': 293, 'sha256': '500e30519f3983154db70b666cf6d160969eb68d936450d0fb1f0300dba5a49e'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/direct-publication-plan.json': {'bytes': 6001, 'sha256': '324b08a24668a7e1e90ad0455c7d68f9189e47e96204b921e2e6778a4645b82d'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/engine-restoration.json': {'bytes': 14357, 'sha256': 'c291f43ffa1cb03b0a1a6a706189bd8ca481b3c36eb88eda216a5ace0d457ee0'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/engine-source-envelope.json': {'bytes': 361, 'sha256': '80d8df02aa043aca8e8a50ff2b36362646137612428e54fbb5e6ede8f8ca3afd'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/exit-supervision-controls.json': {'bytes': 18907, 'sha256': 'e100df1b145a3df409f2a927e04a127d4c1dbfc0a9e286096cd0153888af6437'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/fixed-route-prefix-controls.json': {'bytes': 93258, 'sha256': '22528bf03ce10c97b9d14a64a2d4c84ef3f7336281978fd982fd8d27acbf81ef'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/frozen-prefix-inventory.json': {'bytes': 270796, 'sha256': '3fb07de59166985e14f9ff9142e8a5072fa0234bbac8e1cf01b23263c60e6b06'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/frozen-prefix.json': {'bytes': 487, 'sha256': '1635885ce07755f7637dcacc7852ebb4b5d57d97738d014952ca70dc541327e5'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/host-result.json': {'bytes': 26941, 'sha256': '4cd9cac55b4a27d82e7c6eb4cb7d5537edb5f98af6266e91afb46129447af16a'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/inner-result.json': {'bytes': 16752, 'sha256': '8a2a3e8c62b40819082549be7a5fe9b03fdb59ba7ad2af5dc217443debfe66fd'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/input-restoration.json': {'bytes': 24377, 'sha256': '38fd8b7d7280fe5851270c2a4770000b82727dc631a34c36ddf101a1fc22e596'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/method.json': {'bytes': 191313, 'sha256': '2b2183f1bb009087a60449723c88b4e4ff9c37639a7da09e04ebca9ff69cb8f0'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/native-prefix-result.json': {'bytes': 682502, 'sha256': '6e92439c17f7704ac164ae87028ebe7ac493110ffd304792ad6ac6928b1e7038'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/outputs.json': {'bytes': 13956, 'sha256': '05982f8f4b0ac88cbc40cde85ba7264db547d4af146587360024756c08c07153'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/parts.json': {'bytes': 497, 'sha256': '2f989bca5cd081c81b0304b06916517adf8e6da80ad1612169bfcbedab405574'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/prefix-source-admission.json': {'bytes': 2251, 'sha256': '56bde8b8c8226e78388a6ffa02ffbfb90a51fc0be7f6e32d14f4620c98c908f4'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/publication-availability.json': {'bytes': 769, 'sha256': '68fbde0ea1fc2e10fa66c3cc11a73cab43826676ec69365c52bb353225a86c28'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/release-reservation.json': {'bytes': 335, 'sha256': 'f794d983bf190021e9b315198bc57251001f8ec5e23216f3645dd4b800bc3742'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/routing-source-envelope.json': {'bytes': 10055, 'sha256': 'b8cf135387c6cb5bdd813db5bf3ac8b75c82644fb23c7357d62dad6db2408c3a'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/runtime-dependencies.json': {'bytes': 16940, 'sha256': '6651a9b0b0059ed4b6ebfa5cb016a2ce08c146196d357fa1283ebf57eb6619a0'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/runtime-observed.json': {'bytes': 16940, 'sha256': '6651a9b0b0059ed4b6ebfa5cb016a2ce08c146196d357fa1283ebf57eb6619a0'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/runtime-qualification.json': {'bytes': 698, 'sha256': 'f507fb8033638fac1e1658ab1fd3373602db50326cb9e15c89391b43fddb032d'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/direct/source-admission.json': {'bytes': 25643, 'sha256': '0a5132913b8c87304a6b662b5b5fc848e206783b50aeef72af154de5be00ddc2'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/jobs.json': {'bytes': 9840, 'sha256': '6537ba32d47a138ff3708e7ba180fc042fec68c1f66f99562d242a876b692420'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/release.json': {'bytes': 57303, 'sha256': 'f048fb5ffe04f15a713f1a5f9efaeb2454e1ddb2bcd1b334975703ab0a414779'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/run.json': {'bytes': 14421, 'sha256': '61b2404783e03883a6cad56d16ba4d17c548fbd47e3530ef4b95cda535d2d329'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/tag-ref.json': {'bytes': 572, 'sha256': '517ab091e86b73a882de664e5bd76d04da5d28fa66d2be8073fcd39956de1620'}, 'docs/evidence/mainchip-fixed-engine-prefix-native-terminal-40878295979/receipt.json': {'bytes': 14781, 'sha256': 'aa994e691178fb7c56ea857315b373c107ad7339be889097620975f51d921a45'}}
FROZEN_FIXED_SHA="45dc1b634fafaba4dda8475430ea1a82a69a355dfac6a6b2bbdf63529777e431"
FROZEN_REPAIR_SHA="ea723ae478c019c45ce79f33c6a4abb65d298c053abd32c35c4376902be02c2d"
PREFIX_RECEIPT_SHA="aa994e691178fb7c56ea857315b373c107ad7339be889097620975f51d921a45"
PRIOR=previous.METHOD
PRIOR_SHA="2b2183f1bb009087a60449723c88b4e4ff9c37639a7da09e04ebca9ff69cb8f0"
SOURCE_ADMISSION="docs/evidence/mainchip-fixed-engine-route-tail-source-admission-20261029.json"
SCHEMA="mainchip-fixed-engine-route-tail-v1"
ROOT=Path(__file__).resolve().parent.parent
NEW_FILES=('scripts/mainchip_fixed_engine_route_tail_contract.py', 'scripts/mainchip_fixed_engine_route_tail_handoff.py', 'scripts/check_mainchip_fixed_engine_route_tail.py', 'scripts/cloud_mainchip_fixed_engine_route_tail.py', 'scripts/mainchip_fixed_engine_route_tail_driver.py', 'scripts/mainchip_fixed_engine_route_tail_inner.py', 'scripts/mainchip_fixed_engine_route_tail_native.py', 'scripts/mainchip_exit_checked_command_evidence.py', 'scripts/check_mainchip_exit_checked_command_evidence.py')
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
PREFIX_CONTROL_FILES=("fixed-prefix-control-context.json","fixed-route-prefix-controls.json",
 "fixed-route-prefix-controls.stdout","fixed-route-prefix-controls.stderr",
 "exit-supervision-controls.json","exit-supervision-controls.stdout","exit-supervision-controls.stderr")
FROZEN_ARCHIVE={'bytes': 609145089, 'sha256': 'c68efaf8bca2d42a12d454f07eec3ba996775a8c2cb8a30ce771b4ea34e3d1c2'}
FROZEN_INVENTORY={'bytes': 270796, 'sha256': '3fb07de59166985e14f9ff9142e8a5072fa0234bbac8e1cf01b23263c60e6b06'}
OUTER_ARCHIVE={'bytes': 875578560, 'sha256': 'a3133701299ef9b0ac3269a8dd6502f29699ec0f48d96e60ac6f23a15d109763'}

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
    require(len(prior["protected"])==1207 and m["inherited_protected_count"]==1207,"prefix pin count")
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
    require(frozen["archive"]==FROZEN_ARCHIVE and frozen["inventory"]==FROZEN_INVENTORY,"actual frozen archive/inventory identities")
    validate_prefix_joins(root,host,inner,native,frozen,inv)
    return inv

def envelope(root,run,jobs,release,tag):
    require(run["id"]==PREFIX_RUN and run["head_sha"]==PREFIX_SOURCE and run["run_attempt"]==1
        and run["status"]=="completed" and run["conclusion"]=="success"
        and run["head_branch"]==previous.BRANCH and run["event"]=="workflow_dispatch"
        and run["workflow_id"]==400507406
        and run["path"]==".github/workflows/mainchip-fixed-engine-route-prefix.yml","prefix run")
    expected_jobs={123462735615:"source-controls",123463296225:"preserve-source-job-log",123463392812:"native-prefix"}
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


def validate_prefix_commands(native):
    """Command-only seam; prefix_contract authenticates the unchanged enclosing proof bytes."""
    require([x["label"]for x in native["commands"]]==list(previous.PHASES),"prefix actual phase ordering")
    qualifications=[]
    for x in native["commands"]:
        require(x["returncode"]==0 and type(x["requested_timeout_seconds"])is int
            and x["requested_timeout_seconds"]==1200
            and x["argv"]==previous.command(x["label"],"/work/engine/openroad"),"prefix original phase guard")
        proof=command_evidence.validate(x,1200)
        require(proof["requested_timeout_bound"]is True,"prefix declared command timeout")
        qualifications.append(dict(label=x["label"],command_evidence=proof))
    return qualifications

def validate_frozen_source_projection(inv,method,native):
    """Authenticate the exact protected sources plus the four original supervised stdout logs."""
    validate_prefix_commands(native)
    expected={x["label"]+".log":dict(bytes=x["stdout_bytes"],sha256=x["stdout_sha256"])
        for x in native["commands"]}
    require(len(expected)==4 and set(expected)=={p+".log"for p in previous.PHASES},
        "frozen original phase log census")
    source={p.removeprefix("source/"):row for p,row in inv["files"].items()if p.startswith("source/")}
    require(set(source)==set(method["protected"])|{PRIOR}|set(expected),"complete frozen source projection")
    for name,row in expected.items():
        require(type(row["bytes"])is int and row["bytes"]>=0
            and type(row["sha256"])is str and re.fullmatch("[0-9a-f]{64}",row["sha256"])
            and source[name]==row,"frozen original phase stdout log binding")
    return dict(protected_source_files=len(method["protected"])+1,original_phase_logs=4,
        exact_phase_stdout_bindings=True,unexpected_source_members=0)

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
        and len(m["protected"])==1207,"prefix actual native authority")
    context=dict(source=PREFIX_SOURCE,token=str(PREFIX_RUN)+"-1")
    bounds={}
    for job in ("source-controls","native-prefix"):
        directory=Path(root)/PREFIX/"controls"/job
        index=decode(secure_file(directory,"index.json").read_bytes())
        require(set(index)==set(PREFIX_CONTROL_FILES),"prefix complete control index")
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
    validate_prefix_commands(native)
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
    validate_frozen_source_projection(inv,m,native)
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
    require(parts["archive"]==OUTER_ARCHIVE and parts["archive"]["bytes"]==total
        and len(full)==95 and set(assets)==set(direct)|names,"prefix complete assets")
    for key in ("native_routing_executed","observer_equivalence_qualified","physical_acceptance","timing_accepted","full_phy_accepted"):
        require(receipt[key]is False,"prefix cannot accept later stages")
    return dict(run=PREFIX_RUN,source=PREFIX_SOURCE,release_id=PREFIX_RELEASE,
        frozen_files=FROZEN_COUNT,frozen_unpacked_bytes=FROZEN_BYTES,prefix_qualified=True,
        native_routing_executed=False,physical_acceptance=False)

def control_evidence(root,ctx):
    name="fixed-route-tail-controls.json"
    raw=secure_file(root,name).read_bytes();r=decode(raw)
    common=dict(source=ctx["source"],run_id=int(ctx["token"].split("-")[0]),attempt=1,
        source_controls_only=True,native_executed=False)
    expected={**common,"mode":ctx["mode"],"stage":ctx["stage"]}
    require(r["status"]=="PASS_FIXED_ENGINE_ROUTE_TAIL_SOURCE_CONTROLS"
        and r["current_context"]==expected and r["source_only"]is True,"current tail source context/status")
    require(all(r[k]is False for k in ("native_executed","native_routing_executed","physical_acceptance",
        "complete_native_qualification","observer_equivalence_qualified")),"current tail source-only scope")
    for key,positive,refusal in (("context_controls",5,14),("authority_controls",6,79),("command_consumers",5,24)):
        require((r[key]["positive_count"],r[key]["refusal_count"])==(positive,refusal),"current tail "+key)
    require((r["frozen_source_projection"]["positive_count"],r["frozen_source_projection"]["refusal_count"])==(1,8)
        and r["frozen_source_projection"]["actual_saved_native_manifest"]is True,"frozen exact source/log projection controls")
    require(r["derivation"]["wrapper_count"]==5 and r["derivation"]["exact_source_count"]==17
        and r["derivation"]["actual_native_executed"]is False
        and r["derivation"]["original_limits_and_comparison_preserved"]is True,"tail exact wrapper derivation")
    require(len(r["envelope"]["refusals"])==10 and r["envelope"]["actual_saved_terminal"]is True
        and len(r["restore"])==4,"tail actual prefix and synthetic restore controls")
    require(len(r["sequence"]["stops"])==6 and r["sequence"]["gate_refusals"]==4
        and r["sequence"]["independent_route_seconds"]==14400
        and r["sequence"]["independent_audit_seconds"]==[1200]*5,"tail original phase controls")
    require(r["observer"]["positive"]==3 and len(r["observer"]["refusals"])==3,"tail observer controls")
    require(r["comparison"]["positive"]==1 and len(r["comparison"]["geometry_mismatches"])==10
        and r["comparison"]["marker_mismatch"]is True and r["comparison"]["refusals"]==5,"tail comparison controls")
    life=r["lifecycle"]
    expected_life={(stage,case)for stage in ("route","audit")for case in
        ("complete","body","stop","join","body_stop_join","save","body_save","heartbeat_set")}
    require(len(life)==16 and {(x["stage"],x["case"])for x in life}==expected_life,"tail actual driver lifecycle controls")
    handoff=r["handoff"]
    require((len(handoff["positive"]),len(handoff["refusals"]),len(handoff["terminal"]))==(2,12,4)
        and handoff["actual_new_handoff"]is True and handoff["cardinality"]==FROZEN_COUNT
        and handoff["synthetic_payloads_only"]is True and handoff["native_engine_executed"]is False,"tail actual handoff controls")
    consumers=r["command_consumers"]
    require(consumers["actual_supervised_record_cases"]==4 and consumers["diagnostics_never_cleared"]is True
        and consumers["actual_prefix_command_consumer"]is True and consumers["actual_route_records"]is True
        and consumers["native_executed"]is False and consumers["physical_acceptance"]is False,"tail command consumer controls")
    proof=r["source_projection"]
    require((proof["positive_count"],proof["proof_file_count"],proof["refusal_count"],proof["source_refusal_count"])
        ==(1,len(PREFIX_REQUIRED),len(PREFIX_REQUIRED)+2,5)
        and proof["copied_protected_only"]is True and proof["recursive_prior_methods_validated"]is True
        and proof["actual_native_archive_acquired"]is False and proof["frozen_files"]==FROZEN_COUNT,"tail full source/proof projection")
    pub=r["publication"]
    require(pub["group_count"]==4 and pub["case_count"]==28 and pub["actual_new_publish_and_pack"]is True
        and {(x["mode"],x["stage"])for x in pub["groups"]}=={(m,s)for m in MODES for s in ("route","audit")}
        and all(x["result"]["status"]=="PASS_ACTUAL_FAILURE_AND_EMPTY_PUBLICATION_CONTROLS"
            and x["result"]["count"]==7 for x in pub["groups"]),"tail actual publication controls")
    require(len(r["split_publication"])==4 and {x["case"]for x in r["split_publication"]}==
        {"missing_terminal","empty_terminal","malformed_terminal","upload_failure"},"tail partial publication controls")
    require((r["nested_publication"]["positive_count"],r["nested_publication"]["refusal_count"],
        r["nested_publication"]["case_count"])==(1,2,3)
        and (r["asset_publication"]["positive"],r["asset_publication"]["refusals"])==(2,1),"tail direct publication controls")
    expected=common
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
    command_name="exit-command-evidence-controls.json"
    craw=secure_file(root,command_name).read_bytes();command=decode(craw)
    require(command["status"]=="PASS_EXIT_CHECKED_COMMAND_EVIDENCE_SOURCE_CONTROLS"
        and command["current_context"]==common,"command evidence exact source context/status")
    require((command["positive"],command["refusal"],command["actual_old_regressions"],
        command["actual_supervised_record_cases"])==(9,70,2,9)
        and (len(command["positives"]),len(command["refusals"]),len(command["regressions"]),
            len(command["producer_records"]))==(9,70,2,7),"command evidence actual producer controls")
    require(command["source_controls_only"]is True and command["synthetic_process_proc_clock_io"]is True
        and all(command[k]is False for k in ("native_executed","physical_acceptance","full_phy_accepted")),
        "command evidence source-only scope")
    return {name:dict(bytes=len(raw),sha256=digest(raw)),extra:dict(bytes=len(eraw),sha256=digest(eraw)),
        command_name:dict(bytes=len(craw),sha256=digest(craw))}
