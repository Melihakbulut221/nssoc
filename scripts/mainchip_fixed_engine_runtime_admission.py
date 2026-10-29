#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only admission of the actual FIXED-guard engine build; no runtime authority."""
import hashlib
import json
import os
import subprocess
from pathlib import Path
import re
import mainchip_built_engine_runtime_contract as frozen
import mainchip_fixed_engine_build_contract as build
import mainchip_witness_engine_build_contract as core
import ensure_cloud_tested_source_release as release_guard

ROOT = Path(__file__).resolve().parent.parent
BRANCH = 'codex/mainchip-fixed-engine-runtime-preparation'
METHOD = 'scripts/mainchip-fixed-engine-runtime-admission-methods.json'
PRIOR = "scripts/mainchip-fixed-engine-build-methods.json"
PRIOR_SHA = 'd9929b5d7e64d06ee241096b216dd1065113880bd16f4c503b625cbefe66a1fb'
PREFIX = 'docs/evidence/mainchip-fixed-engine-native-terminal-20261029/'
RUN = 40837855489
SOURCE = "bfb75d24515a566262bfb8b2e8b681dd2774cec6"
RELEASE = 427584078
TAG = "cloud-results-40837855489-1-mainchip-fixed-neardrc-engine-build"
ENGINE = dict(bytes=108939848, sha256="2a343c7491353a60e7b06aa134d4b67e3ef2e846a8341164dacffe88f5f7ec2f")
INPUT = dict(bytes=213740873, sha256="444f75328e4065ae1fd1fdf1b872980931fcbae8ec8a62182a833e48230bf9b1")
REQUIRED = {'complete-native-restore-map.json': {'bytes': 13429, 'sha256': '2d854504346666bc50ce780372b0f2ff174e9c31260cafe031e7a82e4269339f'}, 'direct/build-configuration.json': {'bytes': 398, 'sha256': 'db70175fafb919c0f9794bc56415051c0dc671380aeb71f3c4ec5cecfcab8479'}, 'direct/container-initial.json': {'bytes': 6302, 'sha256': '4af8b1b5f9485f9afed46ac25730a70abc756cb4d0e08162fe4852112376629f'}, 'direct/container-terminal.json': {'bytes': 6863, 'sha256': '161afe78436ca541af085290fb67957fb87aba5d085dc970ab6efb5f83d5f66c'}, 'direct/current-source-controls.json': {'bytes': 425, 'sha256': '3bc3890c9e88332480832cc6348e0bd58647cfbb0df0a3354b65f91ee7e36871'}, 'direct/direct-publication-plan.json': {'bytes': 4625, 'sha256': '528a25b8ff3b9d2fa843c1bc19c9bac3b95c3e6e815b1a196bca9e89098ac615'}, 'direct/engine-build-controls.json': {'bytes': 3045, 'sha256': '40d871dacd6103f0da1407d2a6e8ce9ee2c97a390a23519d19a758f8d6a66319'}, 'direct/fixed-engine-controls.json': {'bytes': 24407, 'sha256': '2b38a3a39ef28a4a13f271a913e3d5f0a7ab3ddda29aa5bc3600dac5c88f4f19'}, 'direct/host-result.json': {'bytes': 32538, 'sha256': '5bbd3b9d74489db473441637209626baafdd864499a679ced0a9932df3013571'}, 'direct/inner-result.json': {'bytes': 19883, 'sha256': '5e4e6cf4602665929607511812b3b29255c9430c2a1700b444df2663e84a0f30'}, 'direct/internal-witness-controls.json': {'bytes': 1133, 'sha256': 'a5685ad91793240a318f79785f64df6c7979c062430bd63cf9aaae0bb362bc3b'}, 'direct/method.json': {'bytes': 143409, 'sha256': 'd9929b5d7e64d06ee241096b216dd1065113880bd16f4c503b625cbefe66a1fb'}, 'direct/outputs.json': {'bytes': 14200, 'sha256': '1a747364dd1d0bcb2dd9f20947f59e5db9945fbee688285b5b68e59f96b554e8'}, 'direct/parts.json': {'bytes': 313, 'sha256': 'c5803b2d770d411bca71cc0daf7152448c025118ef23275413e452a4588df1a1'}, 'direct/publication-availability.json': {'bytes': 779, 'sha256': 'd03b5d1b1cf849e3c8be7a5cbb78d13d77b5c9a473c6a11f0308328d13155306'}, 'direct/release-reservation.json': {'bytes': 336, 'sha256': '3beaa305319124e8f8f8c0c6871b569da911160a91e17926852b69faba66138b'}, 'direct/runtime-dependencies.json': {'bytes': 16940, 'sha256': '6651a9b0b0059ed4b6ebfa5cb016a2ce08c146196d357fa1283ebf57eb6619a0'}, 'direct/source-after.json': {'bytes': 1492875, 'sha256': '7ce0633b77851a1f07d28eb08ac49d37e025b76c83ada4acf451c04c3bbeedf4'}, 'direct/source-before.json': {'bytes': 1492875, 'sha256': '7ce0633b77851a1f07d28eb08ac49d37e025b76c83ada4acf451c04c3bbeedf4'}, 'direct/source-derivation.json': {'bytes': 1194, 'sha256': '3b1af6382f55c3df09f14547d7befd2be32596ec17e2d899432d440486efafd6'}, 'direct/source-upstream.json': {'bytes': 1492875, 'sha256': '276210879ed81fee1cd9d86023eb1f2b8316a43c15f30f3e90615be0071b39de'}, 'jobs.json': {'bytes': 8951, 'sha256': '45498d0f0f16040c922a842e4a7b37d776881402f497012d49e2c3f021304958'}, 'receipt.json': {'bytes': 9928, 'sha256': '7b153bf7f624d10797fd204d13d80770948f2ad83cfd3134e6947d7bf769a447'}, 'release.json': {'bytes': 45106, 'sha256': '56354066614d92ea0680ebb8e234c5e30883a9b2fe0ce32c8ccdb6b747e4132b'}, 'run.json': {'bytes': 14413, 'sha256': 'c01e378fdca48f8dc83bde387509b6302f5768745873dfb506ff85cc57ed3425'}, 'tag-ref.json': {'bytes': 575, 'sha256': '9742a2a8b081e9df3b90d55e1bd1c5df5da01d36f1d12205a117bc1ecde5c5c6'}}
ASSETS = {'687863354': {'name': 'build-configuration.json', 'size': 398, 'digest': 'sha256:db70175fafb919c0f9794bc56415051c0dc671380aeb71f3c4ec5cecfcab8479', 'state': 'uploaded'}, '687863043': {'name': 'container-initial.json', 'size': 6302, 'digest': 'sha256:4af8b1b5f9485f9afed46ac25730a70abc756cb4d0e08162fe4852112376629f', 'state': 'uploaded'}, '687863133': {'name': 'container-terminal.json', 'size': 6863, 'digest': 'sha256:161afe78436ca541af085290fb67957fb87aba5d085dc970ab6efb5f83d5f66c', 'state': 'uploaded'}, '687863268': {'name': 'current-source-controls.json', 'size': 425, 'digest': 'sha256:3bc3890c9e88332480832cc6348e0bd58647cfbb0df0a3354b65f91ee7e36871', 'state': 'uploaded'}, '687863939': {'name': 'direct-publication-plan.json', 'size': 4625, 'digest': 'sha256:528a25b8ff3b9d2fa843c1bc19c9bac3b95c3e6e815b1a196bca9e89098ac615', 'state': 'uploaded'}, '687862676': {'name': 'engine-build-controls.json', 'size': 3045, 'digest': 'sha256:40d871dacd6103f0da1407d2a6e8ce9ee2c97a390a23519d19a758f8d6a66319', 'state': 'uploaded'}, '687863984': {'name': 'engine-evidence.tar.gz.part000', 'size': 41360067, 'digest': 'sha256:5e38e0f86a07f3d2e7567d4b592051baeb66cf07fcc2c36db0138c372e31dd25', 'state': 'uploaded'}, '687862836': {'name': 'fixed-engine-controls.json', 'size': 24407, 'digest': 'sha256:2b38a3a39ef28a4a13f271a913e3d5f0a7ab3ddda29aa5bc3600dac5c88f4f19', 'state': 'uploaded'}, '687862426': {'name': 'host-result.json', 'size': 32538, 'digest': 'sha256:5bbd3b9d74489db473441637209626baafdd864499a679ced0a9932df3013571', 'state': 'uploaded'}, '687862510': {'name': 'inner-result.json', 'size': 19883, 'digest': 'sha256:5e4e6cf4602665929607511812b3b29255c9430c2a1700b444df2663e84a0f30', 'state': 'uploaded'}, '687862766': {'name': 'internal-witness-controls.json', 'size': 1133, 'digest': 'sha256:a5685ad91793240a318f79785f64df6c7979c062430bd63cf9aaae0bb362bc3b', 'state': 'uploaded'}, '687862582': {'name': 'method.json', 'size': 143409, 'digest': 'sha256:d9929b5d7e64d06ee241096b216dd1065113880bd16f4c503b625cbefe66a1fb', 'state': 'uploaded'}, '687863775': {'name': 'outputs.json', 'size': 14200, 'digest': 'sha256:1a747364dd1d0bcb2dd9f20947f59e5db9945fbee688285b5b68e59f96b554e8', 'state': 'uploaded'}, '687863858': {'name': 'parts.json', 'size': 313, 'digest': 'sha256:c5803b2d770d411bca71cc0daf7152448c025118ef23275413e452a4588df1a1', 'state': 'uploaded'}, '687863440': {'name': 'publication-availability.json', 'size': 779, 'digest': 'sha256:d03b5d1b1cf849e3c8be7a5cbb78d13d77b5c9a473c6a11f0308328d13155306', 'state': 'uploaded'}, '687862966': {'name': 'release-reservation.json', 'size': 336, 'digest': 'sha256:3beaa305319124e8f8f8c0c6871b569da911160a91e17926852b69faba66138b', 'state': 'uploaded'}, '687863199': {'name': 'runtime-dependencies.json', 'size': 16940, 'digest': 'sha256:6651a9b0b0059ed4b6ebfa5cb016a2ce08c146196d357fa1283ebf57eb6619a0', 'state': 'uploaded'}, '687863672': {'name': 'source-after.json', 'size': 1492875, 'digest': 'sha256:7ce0633b77851a1f07d28eb08ac49d37e025b76c83ada4acf451c04c3bbeedf4', 'state': 'uploaded'}, '687863583': {'name': 'source-before.json', 'size': 1492875, 'digest': 'sha256:7ce0633b77851a1f07d28eb08ac49d37e025b76c83ada4acf451c04c3bbeedf4', 'state': 'uploaded'}, '687863728': {'name': 'source-derivation.json', 'size': 1194, 'digest': 'sha256:3b1af6382f55c3df09f14547d7befd2be32596ec17e2d899432d440486efafd6', 'state': 'uploaded'}, '687863511': {'name': 'source-upstream.json', 'size': 1492875, 'digest': 'sha256:276210879ed81fee1cd9d86023eb1f2b8316a43c15f30f3e90615be0071b39de', 'state': 'uploaded'}}
JOBS = {'123326797726': {'name': 'source-controls', 'steps': [[1, 'Set up job', 'completed', 'success'], [2, 'Run actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683', 'completed', 'success'], [3, 'Exact first manual hosted source', 'completed', 'success'], [4, 'Actual new host lifecycle and source publication controls', 'completed', 'success'], [5, 'Always emit exact complete source controls', 'completed', 'success'], [6, 'Preserve all source control reports', 'completed', 'success'], [12, 'Post Run actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683', 'completed', 'success'], [13, 'Complete job', 'completed', 'success']]}, '123327073555': {'name': 'preserve-source-job-log', 'steps': [[1, 'Set up job', 'completed', 'success'], [2, 'Preserve the completed source job full raw log and provenance', 'completed', 'success'], [3, 'Preserve full completed source job log', 'completed', 'success'], [4, 'Complete job', 'completed', 'success']]}, '123327074155': {'name': 'engine-build', 'steps': [[1, 'Set up job', 'completed', 'success'], [2, 'Run actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683', 'completed', 'success'], [3, 'Repeat exact new source controls before transport', 'completed', 'success'], [4, 'New reserved-source build only', 'completed', 'success'], [5, 'Permanently retain complete success or failure evidence', 'completed', 'success'], [6, 'Full cloud-only build evidence fallback', 'completed', 'success'], [12, 'Post Run actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683', 'completed', 'success'], [13, 'Complete job', 'completed', 'success']]}}
MAP_SHA = '20ee31367153fceed2ff44e63ddebd1e94f8cc84307b569434329731129dd363'
RUNTIME_SHA = '85beab7cb7f7878a8bfeb710f96e10720205dfebd4cbd495acfd56766cbc07a4'
COMMAND_ID_SHA = {'host': '2d95c9a1f479ba3e810fe9443201f2e90062c1131c1f3a37cfc42f3437ecb3b3', 'inner': '2b431b7007248d4d7b7a46f31ed6dfcd24e7477119168215c06e914bf482d615'}
INNER_PROGRESS = {'bytes': 9491, 'sha256': 'b4253fdca43e9b6db48de34ebb2b844c9cc7810754e13941254a9f9bbcd195b4'}
DIRECT_NAMES = ('build-configuration.json', 'container-initial.json', 'container-terminal.json', 'current-source-controls.json', 'direct-publication-plan.json', 'engine-build-controls.json', 'fixed-engine-controls.json', 'host-result.json', 'inner-result.json', 'internal-witness-controls.json', 'method.json', 'outputs.json', 'parts.json', 'publication-availability.json', 'release-reservation.json', 'runtime-dependencies.json', 'source-after.json', 'source-before.json', 'source-derivation.json', 'source-upstream.json')
AUTH_FALSE = ("native_probe_authorized", "native_routing_authorized", "engine_build_authorized",
              "controller_ready", "rc_sta_execution_authorized", "observer_equivalence_qualified",
              "runtime_qualified", "physical_acceptance", "timing_accepted", "full_phy_accepted")
NEW_FILES = ('scripts/mainchip_fixed_engine_runtime_admission.py', 'scripts/check_mainchip_fixed_engine_runtime_admission.py', 'docs/evidence/mainchip-fixed-engine-runtime-admission-source-review-20261029.json')
require = core.require
engine_extract = frozen.engine_extract
runtime_match = frozen.runtime_match


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_method(m, prior):
    require(m["schema"] == "mainchip-fixed-engine-runtime-input-admission-v1", "admission method schema")
    require(type(m["source_controls_authorized"]) is bool, "typed source controls authority")
    require(all(m[k] is False for k in AUTH_FALSE), "read-only admission has no execution or acceptance authority")
    require(m["qualified_engine"] is None and m["qualified_routing_engine"] is None, "no qualified engine transfer")
    require(m["producer_run"] == RUN and m["producer_source"] == SOURCE and m["engine"] == ENGINE and m["input"] == INPUT, "method producer/input binding")
    old = prior["protected"]
    require(len(old) == 920 and m["inherited_protected_count"] == 920, "inherited source count")
    require(set(old) | set(NEW_FILES) <= set(m["protected"]), "required new admission source pins")
    require(all(m["protected"][p] == h for p, h in old.items()), "inherited source pin changed")
    return m


def methods(root=ROOT):
    root = Path(root)
    previous = core.secure_file(root, PRIOR).read_bytes()
    require(core.digest(previous) == PRIOR_SHA, "original build method changed")
    m = validate_method(core.decode(core.secure_file(root, METHOD).read_bytes()), core.decode(previous))
    for path, digest in m["protected"].items():
        require(type(digest) is str and re.fullmatch("[0-9a-f]{64}", digest) is not None
                and core.digest(core.secure_file(root, path).read_bytes()) == digest, "protected source: " + path)
    return m


def validate_context(env, method, checkout_head):
    require(env.get("GITHUB_ACTIONS")=="true" and env.get("RUNNER_ENVIRONMENT")=="github-hosted"
            and env.get("RUNNER_OS")=="Linux" and env.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc", "hosted source-only repository context")
    require(env.get("GITHUB_EVENT_NAME")=="workflow_dispatch" and env.get("GITHUB_RUN_ATTEMPT")=="1"
            and env.get("GITHUB_REF")=="refs/heads/"+BRANCH, "exact first-manual admission branch")
    require(re.fullmatch("[0-9a-f]{40}",env.get("GITHUB_SHA",""))is not None
            and re.fullmatch("[1-9][0-9]*",env.get("GITHUB_RUN_ID",""))is not None
            and checkout_head==env["GITHUB_SHA"], "exact admission source/run")
    require(method["source_controls_authorized"]is True and all(method[k]is False for k in AUTH_FALSE), "source controls enabled and native disabled")
    return dict(source=env["GITHUB_SHA"],run_id=int(env["GITHUB_RUN_ID"]),attempt=1,
                source_controls_only=True,native_authorized=False)


def authorize(env=None, root=ROOT):
    env=os.environ if env is None else env
    method=methods(root)
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
    return validate_context(env,method,head)


def read_reports(root=ROOT):
    reports = {}
    for name, expected in REQUIRED.items():
        raw = core.secure_file(Path(root), PREFIX + name).read_bytes()
        require(dict(bytes=len(raw), sha256=core.digest(raw)) == expected, "immutable producer report: " + name)
        reports[name] = core.decode(raw)
    return reports


def asset_census(value):
    rows = value["assets"]
    require(type(rows) is list and len(rows) == 21, "complete21 build assets")
    require(all(type(a.get("id")) is int and a["id"] > 0 for a in rows), "typed asset identity")
    require(len({a["id"] for a in rows}) == len(rows) == len({a["name"] for a in rows}), "duplicate build asset")
    return {str(a["id"]): {k:a[k] for k in ("name", "size", "digest", "state")} for a in rows}


def engine_envelope(run, jobs, release, tag, expected_release):
    require((run["id"], run["run_attempt"], run["head_sha"], run["status"], run["conclusion"])
            == (RUN, 1, SOURCE, "completed", "success"), "actual new build run")
    require(run["event"] == "workflow_dispatch" and run["workflow_id"] == 400307682
            and run["path"] == ".github/workflows/mainchip-fixed-engine-build.yml"
            and run["head_branch"] == "codex/mainchip-fixed-engine-build", "actual new build workflow")
    rows = jobs["jobs"]
    require(type(rows) is list and len(rows) == 3 and len({j["id"] for j in rows}) == 3, "complete3 build jobs")
    require({str(j["id"]): {"name":j["name"], "steps":[[s[k] for k in ("number", "name", "status", "conclusion")] for s in j["steps"]]} for j in rows} == JOBS,
            "exact successful build job/step identities")
    require(all(j["status"] == "completed" and j["conclusion"] == "success" for j in rows), "failed build job")
    require(expected_release["id"] == RELEASE and asset_census(expected_release) == ASSETS, "saved actual release identity")
    actual_assets = asset_census(release)
    release_guard.validate_release(release, tag, TAG, SOURCE)
    require(release["id"] == RELEASE and actual_assets == ASSETS, "live actual build release assets")
    return dict(run=RUN, attempt=1, source=SOURCE, release=RELEASE, tag=TAG,
                original_build_conclusion="success", build_only=True, runtime_qualified=False,
                native_routing_authorized=False, physical_acceptance=False)


def validate_inventory(outputs, complete):
    require(outputs["source"] == SOURCE and outputs["physical_acceptance"] is False, "output producer scope")
    require(type(outputs["files"]) is dict and len(outputs["files"]) == 99 and len(complete) == 100, "exact99plus1 engine inventory")
    require(complete == dict(outputs["files"], **{"outputs.json":REQUIRED["direct/outputs.json"]}), "raw outputs.json full-member join")
    require(canonical_sha(complete) == MAP_SHA and complete["openroad"] == ENGINE, "exact current engine member identities")
    for name, row in complete.items():
        frozen.canonical(name)
        require(set(row) == {"bytes", "sha256"} and type(row["bytes"]) is int and row["bytes"] >= 0
                and type(row["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", row["sha256"]), "regular engine member identity")
    return complete


def validate_reports(d):
    require(set(d) == set(REQUIRED), "complete required producer reports")
    receipt = d["receipt.json"]
    require((receipt["run"],receipt["source"],receipt["terminal"],receipt["release_id"])
            == (RUN,SOURCE,"success",RELEASE), "terminal receipt producer")
    for name, expected in REQUIRED.items():
        if name != "receipt.json":
            require(receipt["files"][PREFIX+name] == expected, "receipt report binding: " + name)
    require(receipt["complete_native_archive_members"] == 100 and receipt["archive_manifest_outputs"] == 99
            and receipt["binary"] == ENGINE and receipt["runtime_dependency_files"] == 104, "terminal receipt inventory")
    require(all(receipt[k] is False for k in ("actual_ODB_runtime_qualified", "actual_native_archive_restore_qualified",
            "observer_equivalence_qualified", "physical_acceptance", "routing_executed", "timing_accepted", "full_phy_accepted")), "build receipt cannot transfer runtime acceptance")
    full = validate_inventory(d["direct/outputs.json"], d["complete-native-restore-map.json"])
    for name in DIRECT_NAMES:
        if name not in ("parts.json", "outputs.json"):
            require(full[name] == REQUIRED["direct/"+name], "direct report archive-member join: " + name)
    parts = d["direct/parts.json"]
    require(len(parts["parts"]) == 1 and parts["parts"][0]["name"] == "engine-evidence.tar.gz.part000"
            and {k:parts["parts"][0][k] for k in ("bytes","sha256")} == parts["archive"]
            == dict(bytes=41360067, sha256="5e38e0f86a07f3d2e7567d4b592051baeb66cf07fcc2c36db0138c372e31dd25"), "exact current engine archive")
    byname = {a["name"]:a for a in d["release.json"]["assets"]}
    require(set(byname) == set(DIRECT_NAMES) | {parts["parts"][0]["name"]}, "direct20 and archive asset set")
    for name in DIRECT_NAMES:
        expected=REQUIRED["direct/"+name]; asset=byname[name]
        require((asset["size"],asset["digest"]) == (expected["bytes"],"sha256:"+expected["sha256"]), "direct asset report join: "+name)
    part=byname[parts["parts"][0]["name"]]
    require((part["size"],part["digest"]) == (parts["archive"]["bytes"],"sha256:"+parts["archive"]["sha256"]), "archive asset join")
    runtime=d["direct/runtime-dependencies.json"]
    require(len(runtime) == 104 and canonical_sha(runtime) == RUNTIME_SHA, "exact104 runtime library records")
    frozen.runtime_match(runtime, runtime)
    for path,row in runtime.items():
        require(Path(path).is_absolute() and set(row)=={"bytes","sha256"} and type(row["bytes"])is int
                and row["bytes"]>0 and re.fullmatch("[0-9a-f]{64}",row["sha256"]), "runtime regular library identity")
    host,inner=d["direct/host-result.json"],d["direct/inner-result.json"]
    require(host["source"]==SOURCE and host["status"]=="PASS_COMPILED_ENGINE_INTERFACE_ONLY"
            and not host["terminal_errors"] and inner["binary"]==ENGINE, "actual complete build result")
    require(all(host[k]is False for k in ("historical_build_acceptance_reused","native_routing_executed",
            "observer_equivalence_qualified","physical_acceptance","runtime_qualified")) and host["qualified_engine"]is None, "new build scope only")
    for kind,result in (("host",host),("inner",inner)):
        require(result["commands"] and all(type(x["returncode"])is int and x["returncode"]==0
                and ("timed_out" not in x if kind=="host" else x.get("timed_out")is False)
                for x in result["commands"]), "actual build command failure")
        require(canonical_sha([[x["label"],x["argv"]]for x in result["commands"]])==COMMAND_ID_SHA[kind], "exact build command identity")
        require(result["terminal_actions"] and all(x["completed"]is True for x in result["terminal_actions"]), "actual build cleanup failure")
        # The inner result precedes final host cleanup. Only this one observed
        # progress snapshot legitimately differs; neither report is rewritten.
        for name,row in result["available_outputs"].items():
            expected=INNER_PROGRESS if kind=="inner" and name=="host-progress.json" else full.get(name)
            require(row==expected, "partial result output inventory join")
    require(inner["available_outputs"]["host-progress.json"]==INNER_PROGRESS
            and full["host-progress.json"]!=INNER_PROGRESS, "exact earlier/final host progress distinction")
    initial,terminal=d["direct/container-initial.json"],d["direct/container-terminal.json"]
    require(host["container_terminal"]==terminal and initial["Id"]==terminal["Id"], "actual container joins")
    ctx=dict(name="nssoc-witness-build-40837855489-1",source=SOURCE,token="40837855489-1")
    work=Path("/home/runner/work/_temp/mainchip-fixed-neardrc-engine-build-40837855489-1")
    core.validate_container(initial,ctx,work)
    core.validate_container(terminal,ctx,work,True)
    core.validate_terminal(terminal,inner)
    require(d["direct/build-configuration.json"]==inner["actual_build_configuration"]
            and inner["actual_build_configuration"]["cache_flags"] == {"BUILD_GUI":["BOOL","OFF"],"BUILD_PYTHON":["BOOL","ON"],
            "CMAKE_INTERPROCEDURAL_OPTIMIZATION":["BOOL","OFF"],"ENABLE_TESTS":["BOOL","OFF"],"LINK_TIME_OPTIMIZATION":["BOOL","OFF"]}
            and inner["actual_build_configuration"]["compile_command_count"]==3671
            and inner["actual_build_configuration"]["compile_commands_no_flto"]is True, "actual full engine build configuration")
    before,after,upstream=(d["direct/source-"+n+".json"] for n in ("before","after","upstream"))
    require(before==after and len(before)==10271, "complete unchanged compiled source census")
    derivation=build.source_delta(upstream,before); recorded=dict(d["direct/source-derivation.json"])
    require(recorded.pop("upstream_commit")=="dcf36133a369abc8f3c5e5738cd4d82e4903c0e0"
            and recorded.pop("fixed_guard_reverse_byte_exact")is True
            and recorded.pop("original_observer_derivation_unchanged")is True
            and recorded==derivation, "exact observer plus3-line FIXED patch lineage")
    require(host["new_fixed_guard_sha256"]==before["src/drt/src/dr/FlexDR_init.cpp"]["sha256"], "host FIXED patch binding")
    controls=d["direct/current-source-controls.json"]
    require(host["current_source_controls"]==controls, "host repeated source controls join")
    for name in ("fixed-engine-controls.json","engine-build-controls.json","internal-witness-controls.json"):
        require(controls[name]==REQUIRED["direct/"+name]
                ==receipt["files"][PREFIX+"controls/"+name], "original and repeated source controls byte identity")
    current=d["direct/fixed-engine-controls.json"];old=d["direct/engine-build-controls.json"];observer=d["direct/internal-witness-controls.json"]
    require(current["status"]=="PASS_FIXED_ENGINE_BUILD_SOURCE_CONTROLS" and current["current_source"]==SOURCE
            and current["current_token"]=="40837855489-1" and current["unchanged_build_controls"]==old, "actual source controls producer")
    require(all(current[k]is False for k in ("actual_engine_compilation","native_payload_acquired","runtime_qualified","routing_qualified","physical_acceptance")), "synthetic source controls scope")
    require((len(current["authority"]["refusals"]),len(current["derivation"]["refusals"]),current["lifecycle"]["count"],current["publication"]["count"])==(28,7,10,7)
            and (old["positive_count"],old["refusal_count"],old["lifecycle"]["count"])==(7,45,25)
            and observer["status"]=="PASS" and (observer["positive_count"],observer["refusal_count"])==(4,29), "source controls counts")
    reservation=d["direct/release-reservation.json"]
    build.validate_reservation(reservation,ctx,True)
    require(reservation["release_id"]==RELEASE, "producer reserved release ID")
    availability=d["direct/publication-availability.json"]
    require(availability["source_integrity_validated"]is True and availability["source_integrity_error"]is None
            and availability["native_accepted"]is False, "publication source/scope")
    for name in ("host-result.json","inner-result.json"):
        row=availability["source_records"][name]
        require(row["present"]is True and row["parsed_object"]is True and row["status"]==d["direct/"+name]["status"]
                and {k:row[k]for k in ("bytes","sha256")}==REQUIRED["direct/"+name], "publication terminal byte joins")
    plan=d["direct/direct-publication-plan.json"]
    require(plan["empty_files_retained_in_full_archive"]is True and plan["missing_terminal_is_not_acceptance"]is True, "publication empty/failure policy")
    require(len({x["name"]for x in plan["files"]})==len(plan["files"]), "duplicate direct publication plan")
    for row in plan["files"]:
        require(row["present"]is True and row["archive_member"]==row["name"] and full[row["name"]]=={k:row[k]for k in ("bytes","sha256")}
                and row["disposition"]==("direct"if row["bytes"]else"archive_only_empty"), "publication plan member join")
    require(d["direct/method.json"]["protected"] and len(d["direct/method.json"]["protected"])==920
            and d["direct/method.json"]["native_probe_authorized"]is False
            and d["direct/method.json"]["runtime_qualified"]is False, "original build method is not runtime authority")
    envelope=engine_envelope(d["run.json"],d["jobs.json"],d["release.json"],d["tag-ref.json"],d["release.json"])
    return dict(files=full,parts=parts,runtime=runtime,release=d["release.json"],producer=envelope,
                native_archive_restored=False,runtime_qualified=False,physical_acceptance=False,
                host_progress_snapshots=dict(inner_earlier=INNER_PROGRESS,archive_final=full["host-progress.json"]))


def source_guard(root=ROOT):
    methods(root)
    reports=read_reports(root)
    expected=validate_reports(reports)
    return dict(status="PASS_FIXED_ENGINE_INPUT_METADATA_ONLY",producer=expected["producer"],
                exact_report_count=len(REQUIRED),direct_JSON_count=20,complete_members=len(expected["files"]),
                runtime_library_records=len(expected["runtime"]),native_assets_acquired=False,
                runtime_qualified=False,physical_acceptance=False)


def expected_engine(root=ROOT):
    methods(root)
    return validate_reports(read_reports(root))
