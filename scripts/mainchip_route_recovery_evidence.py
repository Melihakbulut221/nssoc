#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticate saved route handoffs while preserving failed publication status.

Read-only source/derived-evidence API. No transport, restore, runtime, mutation,
new authorization, or claim that either failed original job succeeded.
"""
import hashlib
import importlib
import json
import re
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
SOURCE="dd2115212b8ccd1176a2e67995d3e54b0a4248dc"
RUN=40808800489
BRANCH="codex/mainchip-built-engine-route-tail-observer"
WORKFLOW=".github/workflows/mainchip-built-engine-route-tail.yml"
METHOD="scripts/mainchip-built-engine-route-tail-methods.json"
METHOD_SHA="d6e9d562f31b99d5559c722a0a5a1c0f845ef4197b80fef17569bca4a24201a4"
METHOD_BYTES=104882
PREFIX="docs/evidence/mainchip-route-{mode}-publication-failure-20261029."
EMPTY="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
REQUIRED_DOCS={
  "docs/evidence/mainchip-route-off-publication-failure-20261029.case-result.json": {
    "bytes": 13454,
    "sha256": "a2d765a96f8ec23f9275db9041bba275ff259331b338d7dd25a2237625541bc1"
  },
  "docs/evidence/mainchip-route-off-publication-failure-20261029.host-result.json": {
    "bytes": 23055,
    "sha256": "a683b83b9da77b9155a659b50fa9146efacd2af13ee49be4b6faf075f32114f2"
  },
  "docs/evidence/mainchip-route-off-publication-failure-20261029.inner-result.json": {
    "bytes": 14900,
    "sha256": "302a7fc7d4278c87dc6d47a880307872aee2ac962ba3ebe2c077e7fa3b2fa17f"
  },
  "docs/evidence/mainchip-route-off-publication-failure-20261029.job.json": {
    "bytes": 3788,
    "sha256": "3f65630fd625426ad2ab6b51c90ae4df3247afe101b0cf7485da3c4712aafe9a"
  },
  "docs/evidence/mainchip-route-off-publication-failure-20261029.job.log": {
    "bytes": 914630,
    "sha256": "079ded87be003cc0f2612d96a2da5d6ad65228b483fcfb80c3d5e5c13858d611"
  },
  "docs/evidence/mainchip-route-off-publication-failure-20261029.outputs.json": {
    "bytes": 12246,
    "sha256": "65ed426d12a10eff1107a8d8076e23953b89a5ac5aaae79b322979bf89f631f8"
  },
  "docs/evidence/mainchip-route-off-publication-failure-20261029.parts.json": {
    "bytes": 494,
    "sha256": "d83b329d9b36dfdfc651c245697b0a9017c4988daf0cf1b49bc29f5f13955683"
  },
  "docs/evidence/mainchip-route-off-publication-failure-20261029.receipt.json": {
    "bytes": 4332,
    "sha256": "459c868ff1572fbf78c106164cbb8ab6b7a63a8913c5730541e2bcbecc2c6fbf"
  },
  "docs/evidence/mainchip-route-off-publication-failure-20261029.release-snapshot.json": {
    "bytes": 45177,
    "sha256": "d7be374c3d7727d6deda870562161b6f766f600afb2a3e651a1512eca6a2e704"
  },
  "docs/evidence/mainchip-route-off-publication-failure-20261029.route-handoff-inventory.json": {
    "bytes": 299819,
    "sha256": "7067da200583ee0930e739a783f469d43dcfc2acc1595ed48e06dca6f56bdaa0"
  },
  "docs/evidence/mainchip-route-off-publication-failure-20261029.route-handoff.json": {
    "bytes": 598,
    "sha256": "b418235c99e1a19ad8e0e6494840ccc536e71385d561cc488170a88b96bb5588"
  },
  "docs/evidence/mainchip-route-off-publication-failure-20261029.run-snapshot.json": {
    "bytes": 14446,
    "sha256": "2069101c9740c927e0a42d4921edc61afa3c6ed960c1a2c43beda2f8a9fabc32"
  },
  "docs/evidence/mainchip-route-off-publication-failure-20261029.tag.json": {
    "bytes": 598,
    "sha256": "380228e7b27bcfc20958830ea399a13bd0ebb99211117788e8154bb62c37e7fb"
  },
  "docs/evidence/mainchip-route-on-publication-failure-20261029.case-result.json": {
    "bytes": 14736,
    "sha256": "561bf9960e3c4acdfcdfa48e8c71603ea454298700a0170993eca9b49375885f"
  },
  "docs/evidence/mainchip-route-on-publication-failure-20261029.host-result.json": {
    "bytes": 23642,
    "sha256": "d1f41b9e936b3cd787717bc7b699d5ec77becc65629c0ef63a3fe36cd2f82ba7"
  },
  "docs/evidence/mainchip-route-on-publication-failure-20261029.inner-result.json": {
    "bytes": 15486,
    "sha256": "e1242b94596a05037861efb39ef06218946bb226116060ad864013efff64e261"
  },
  "docs/evidence/mainchip-route-on-publication-failure-20261029.job.json": {
    "bytes": 3787,
    "sha256": "edc14fcf5c2242878adbea651640a06fd7a68d9a0619af1d299435b9a2777323"
  },
  "docs/evidence/mainchip-route-on-publication-failure-20261029.job.log": {
    "bytes": 917658,
    "sha256": "713215bec497f53a172f3a4d63226bcd2c680b5397cdab53eb14f704fae1575f"
  },
  "docs/evidence/mainchip-route-on-publication-failure-20261029.outputs.json": {
    "bytes": 12829,
    "sha256": "624e442921dbb7ee3e868a959eb67370228039bad3c693d71b084c1f7579994c"
  },
  "docs/evidence/mainchip-route-on-publication-failure-20261029.parts.json": {
    "bytes": 494,
    "sha256": "4752f8ac18adf7fe1c61b5d9e9f3816d6ee3988cb29deb2d604c8f2b5763592e"
  },
  "docs/evidence/mainchip-route-on-publication-failure-20261029.receipt.json": {
    "bytes": 4354,
    "sha256": "a45eb03568ae835b5bbbffab589d28495dbdd43e76360af25b2be8a99d5818d4"
  },
  "docs/evidence/mainchip-route-on-publication-failure-20261029.release-snapshot.json": {
    "bytes": 45151,
    "sha256": "7efe50c613dbb5ffbee3678fe16a49faa73cd6f754b2ba2cd068f646158b9d82"
  },
  "docs/evidence/mainchip-route-on-publication-failure-20261029.route-handoff-inventory.json": {
    "bytes": 300418,
    "sha256": "d665d3d65564fb531db6355c5c9b64df01c46a657080b726a07fd3312f378b48"
  },
  "docs/evidence/mainchip-route-on-publication-failure-20261029.route-handoff.json": {
    "bytes": 597,
    "sha256": "aade770ad6b51c77ac3594f7efe4d6723b90a99c5acda83515b4b0bcccce7111"
  },
  "docs/evidence/mainchip-route-on-publication-failure-20261029.run-snapshot.json": {
    "bytes": 14446,
    "sha256": "2069101c9740c927e0a42d4921edc61afa3c6ed960c1a2c43beda2f8a9fabc32"
  },
  "docs/evidence/mainchip-route-on-publication-failure-20261029.tag.json": {
    "bytes": 595,
    "sha256": "9bfa197a3d0bb3bf2d94237b45b33a08067ce65ff9cd30f0ce80841e30b7262e"
  }
}
CASES={'off': {'release': 427414385, 'job': 123234175763, 'outer_files': 84, 'handoff_files': 1488, 'projection_files': 1442, 'unpacked_bytes': 4538732410}, 'on': {'release': 427414407, 'job': 123234175740, 'outer_files': 88, 'handoff_files': 1492, 'projection_files': 1446, 'unpacked_bytes': 4539631340}}
JOBS={123233983394: {'name': 'source-controls', 'status': 'completed', 'conclusion': 'success'}, 123234175740: {'name': 'route-only (on)', 'status': 'completed', 'conclusion': 'failure'}, 123234175763: {'name': 'route-only (off)', 'status': 'completed', 'conclusion': 'failure'}, 123250210123: {'name': 'audit-only', 'status': 'completed', 'conclusion': 'skipped'}, 123250210166: {'name': 'comparison', 'status': 'completed', 'conclusion': 'skipped'}}
DIRECT=("host-result.json","inner-result.json","case-result.json","outputs.json",
        "parts.json","method.json","route-handoff.json","route-handoff-inventory.json")
HOST_ACTIONS=("recover-owned-container","owned-stop","post-stop-inspect","owned-kill-if-running",
 "terminal-inspect","stopped-container-contract","owned-container-removal","owned-removal-confirmation",
 "checkout-source-unchanged","projected-tail-source-unchanged","frozen-prefix-unchanged",
 "actual-tail-terminal","restore-signal-2","restore-signal-15")
CASE_ACTIONS=("owned-native-process-cleanup","heartbeat-stop","heartbeat-join","restore-signal-2",
 "restore-signal-15","tail-source-terminal","frozen-input-terminal")
INNER_ACTIONS=("child-terminate","child-wait-after-terminate","child-kill-if-live","child-final-wait")*4+(
 "runtime-identity-after","ELF-unchanged","input-unchanged","source-unchanged","terminal-cgroup")


def require(ok,reason):
    if not ok:raise AssertionError(reason)


def member(value):
    require(type(value)is str and value and value!="." and chr(92)not in value
      and not PurePosixPath(value).is_absolute()and ".."not in PurePosixPath(value).parts
      and PurePosixPath(value).as_posix()==value,"Unsafe evidence path")
    return value


def regular(name):
    path=ROOT/member(name)
    require(path.is_file()and not any(p.is_symlink()for p in (path,*path.parents)),
      "Nonregular source evidence")
    return path


def sha(path):
    with Path(path).open("rb")as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def record(raw):
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def select(mode):
    require(type(mode)is str and mode in CASES,"Unknown original route mode")
    return CASES[mode]


def doc_name(mode,name):
    select(mode)
    return PREFIX.format(mode=mode)+name


def source_guard():
    """Authenticate historical authority as data; it grants no new permission."""
    raw=regular(METHOD).read_bytes()
    require(record(raw)==dict(bytes=METHOD_BYTES,sha256=METHOD_SHA),"Changed original route method")
    method=json.loads(raw)
    require(method["schema"]=="mainchip-built-engine-route-tail-v1"
      and len(method["protected"])==687 and method["inherited_protected_count"]==645,
      "Wrong frozen source projection")
    for name,h in method["protected"].items():
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h)
          and sha(regular(name))==h,"Changed original protected source: "+name)
    cases={mode:{}for mode in CASES}
    for name,expected in REQUIRED_DOCS.items():
        raw=regular(name).read_bytes()
        require(record(raw)==expected,"Changed preserved failure evidence: "+name)
        for mode in CASES:
            prefix=PREFIX.format(mode=mode)
            if name.startswith(prefix):
                short=name[len(prefix):]
                cases[mode][short]=raw.decode("utf-8")if short=="job.log"else json.loads(raw)
                break
        else:raise AssertionError("Unclassified proof document")
    require(all(len(rows)==13 for rows in cases.values()),"Incomplete failure document set")
    return dict(old_method=method,cases=cases,source=SOURCE,run_id=RUN,
      old_method_sha256=METHOD_SHA,historical_method_authorizations_reusable=False,
      execution_authorized=False)


def helpers():
    # All these source bytes/dependencies were verified by source_guard first.
    # Only the listed read-only metadata functions are called below.
    c=importlib.import_module("mainchip_built_engine_route_tail_contract")
    h=importlib.import_module("mainchip_built_engine_route_tail_handoff")
    for module,name in ((c,"mainchip_built_engine_route_tail_contract.py"),
                        (h,"mainchip_built_engine_route_tail_handoff.py")):
        require(Path(module.__file__).resolve()==ROOT/"scripts"/name,"Wrong metadata helper module")
    return c,h


def asset_map(release):
    rows=release["assets"]
    require(type(rows)is list and len(rows)==21
      and len({r["id"]for r in rows})==len({r["name"]for r in rows})==21,
      "Incomplete or duplicate retained release assets")
    result={}
    for row in rows:
        require(type(row["id"])is int and type(row["size"])is int and row["size"]>0
          and row["state"]=="uploaded"and re.fullmatch("sha256:[0-9a-f]{64}",row["digest"]),
          "Malformed retained asset identity")
        result[member(row["name"])]=dict(id=row["id"],bytes=row["size"],sha256=row["digest"][7:])
    require("one-two-signal-routing-attempt.stderr"not in result,"Unexpected direct empty upload")
    return result


def job_projection(job):
    return [dict(number=s["number"],name=s["name"],status=s["status"],conclusion=s["conclusion"])
      for s in job["steps"]]


def failed_route_job(mode,job,saved):
    case=select(mode)
    require(type(job["id"])is int and type(job["run_id"])is int
      and type(job["run_attempt"])is int,"Untyped original job identity")
    require((job["id"],job["run_id"],job["run_attempt"],job["head_sha"],job["head_branch"],
      job["name"],job["status"],job["conclusion"])==
      (case["job"],RUN,1,SOURCE,BRANCH,"route-only ("+mode+")","completed","failure"),
      "Original route job must remain failed")
    rows=job_projection(job)
    require(rows==job_projection(saved),"Original route steps changed")
    by_number={r["number"]:r for r in rows}
    require(len(by_number)==len(rows)and all(type(r["number"])is int for r in rows),
      "Duplicate or untyped original steps")
    require([r["number"]for r in rows if r["conclusion"]!="success"]==[7]
      and all(r["status"]=="completed"for r in rows),"Failure was not solely publication")
    required={3:"Repeat exact controls before transport or native work",
      4:"Require all five independently reserved releases before downloads",
      5:"Execute one separately owned route stage",
      6:"Freeze the full route workspace after successful owned cleanup",
      7:"Permanently preserve complete success or failure evidence",
      8:"Always emit exact terminal and repeated-control records",
      9:"Complete native output artifact fallback"}
    require(all(by_number[n]["name"]==name for n,name in required.items()),"Changed route/freeze/publication steps")
    return rows


def failed_run(run):
    require(type(run["id"])is int and type(run["run_attempt"])is int,"Untyped original run identity")
    require((run["id"],run["head_sha"],run["head_branch"],run["run_attempt"],run["event"],
      run["path"],run["status"],run["conclusion"])==
      (RUN,SOURCE,BRANCH,1,"workflow_dispatch",WORKFLOW,"completed","failure"),
      "Original run must remain terminal failure")


def release_binding(mode,release,ref,saved):
    case=select(mode);tag="cloud-results-40808800489-1-mainchip-built-engine-route-tail-"+mode+"-route"
    require(type(release["id"])is int and release["id"]==case["release"]
      and release["tag_name"]==tag and release["target_commitish"]==SOURCE
      and release["draft"]is False and release["prerelease"]is True,"Wrong historical route release")
    require(ref["ref"]=="refs/tags/"+tag and ref["object"]["type"]=="commit"
      and ref["object"]["sha"]==SOURCE,"Wrong historical lightweight source tag")
    assets=asset_map(release)
    require(assets==asset_map(saved),"Historical retained asset set changed")
    return dict(release_id=case["release"],tag=tag,source=SOURCE,assets=assets)


def validate_live(mode,run,jobs,release,ref):
    """Check supplied live metadata; never fetch or reinterpret a failed job as PASS."""
    select(mode);d=source_guard();rows=d["cases"][mode]
    failed_run(run)
    require(type(jobs["total_count"])is int and jobs["total_count"]==len(jobs["jobs"])==5
      and {j["id"]for j in jobs["jobs"]}==set(JOBS),"Wrong complete original job set")
    for job in jobs["jobs"]:
        require(type(job["id"])is int and type(job["run_id"])is int and type(job["run_attempt"])is int
          and job["run_id"]==RUN and job["run_attempt"]==1 and job["head_sha"]==SOURCE,
          "Wrong original job source/attempt")
        require({k:job[k]for k in ("name","status","conclusion")}==JOBS[job["id"]],
          "Original failed/skipped job outcome changed")
        if job["id"]in (CASES["off"]["job"],CASES["on"]["job"]):
            side="off"if job["id"]==CASES["off"]["job"]else"on"
            failed_route_job(side,job,d["cases"][side]["job.json"])
    binding=release_binding(mode,release,ref,rows["release-snapshot.json"])
    # Pinning the original full log, job-step projections and empty stream hash
    # distinguishes this concrete publication failure from a general failed job.
    saved=_validate_saved(mode,d)
    return dict(status="PASS_LIVE_METADATA_FOR_FAILED_PUBLICATION_RECOVERY_ONLY",
      original_run_conclusion="failure",original_job_conclusion="failure",
      original_audits_skipped=True,release=binding,saved_case=saved,
      execution_authorized=False,reroute_authorized=False,physical_acceptance=False,
      observer_equivalence_qualified=False)


def file_map(files):
    require(type(files)is dict and files,"Missing complete file map")
    for name,row in files.items():
        member(name)
        require(type(row)is dict and set(row)=={"bytes","sha256"}
          and type(row["bytes"])is int and row["bytes"]>=0
          and type(row["sha256"])is str and re.fullmatch("[0-9a-f]{64}",row["sha256"]),
          "Malformed full member receipt")
    return files


def actions(row,expected,label):
    require(not row["terminal_errors"]and [r["action"]for r in row["terminal_actions"]]==list(expected)
      and all(r["completed"]is True for r in row["terminal_actions"]),"Incomplete "+label+" cleanup")


def _validate_saved(mode,data):
    case=select(mode);d=data["cases"][mode];m=data["old_method"];c,h=helpers()
    failed_run(d["run-snapshot.json"]);steps=failed_route_job(mode,d["job.json"],d["job.json"])
    binding=release_binding(mode,d["release-snapshot.json"],d["tag.json"],d["release-snapshot.json"])
    receipt=d["receipt.json"]
    require(receipt["source"]==SOURCE and receipt["run"]==RUN and receipt["release"]==case["release"]
      and receipt[mode+"_job"]==case["job"]and receipt["whole_job_conclusion"]=="failure"
      and receipt["whole_job_must_not_be_called_success"]is True
      and receipt["native_route_and_full_freeze_steps_success"]is True
      and receipt["native_reroute_authorized_by_this_note"]is False,"Failure receipt scope changed")
    require(receipt["failed_step"]==next(s for s in d["job.json"]["steps"]if s["number"]==7),
      "Receipt failure step mismatch")
    expected_docs={p:v for p,v in REQUIRED_DOCS.items()
      if p.startswith(PREFIX.format(mode=mode))and not p.endswith("receipt.json")}
    require(receipt["files"]==expected_docs,"Incomplete exact failure proof document map")
    error="HTTP 400: Bad Content-Length (https://uploads.github.com/repos/Melihakbulut221/nssoc/releases/"+str(case["release"])+"/assets?label=&name=one-two-signal-routing-attempt.stderr)"
    require(error in d["job.log"]and "returned non-zero exit status 1"in d["job.log"],
      "Missing original exact empty-upload failure")
    request=dict(source=SOURCE,mode=mode,stage="route",run_id=RUN,engine=m["engine"])
    host=d["host-result.json"];inner=d["inner-result.json"];native=d["case-result.json"]
    require(m["engine"]==c.ENGINE and m["input"]==c.INPUT,"Original engine/input constants changed")
    h.route_records(host,inner,native,request)
    actions(host,HOST_ACTIONS,"host");actions(inner,INNER_ACTIONS,"inner");actions(native,CASE_ACTIONS,"route")
    require(host["creation_attempted"]is True and inner["complete_actual_native_probe"]is True,
      "Original native route was not completed")
    require(host["observer_equivalence_qualified"]is inner["observer_equivalence_qualified"]is
      native["observer_equivalence_qualified"]is False,"Borrowed observer equivalence")
    first,last=inner["cgroup_initial"],inner["cgroup_terminal"]
    require(last["memory.max"]==str(c.MEMORY)and last["memory.swap.max"]=="0"
      and last["pids.max"]==str(c.PIDS),"Original cgroup resource boundary changed")
    for key in ("oom","oom_kill","oom_group_kill"):
        require(last["memory.events"].get(key,0)==first["memory.events"].get(key,0),"Original route OOM")
    quota,period=last["cpu.max"].split()
    require(quota!="max"and int(quota)==2*int(period),"Original route CPU quota changed")
    require(inner["runtime_before"]==inner["runtime_after"],"Original runtime changed")
    inv=d["route-handoff-inventory.json"];proof=d["route-handoff.json"]
    files=file_map(h.validate_manifest(inv,proof,native,request))
    require(inv["canonical_root"]=="/work"and inv["native_input_projection_complete"]is True
      and inv["physical_acceptance"]is False and proof["observer_equivalence_qualified"]is False,
      "Incomplete handoff scope")
    require(len(files)==case["handoff_files"]and sum(r["bytes"]for r in files.values())==case["unpacked_bytes"],
      "Changed complete handoff census")
    projection=h.route_projection(files)
    require(len(projection)==case["projection_files"],"Changed canonical native projection")
    original=c.prefix_contract(ROOT)
    require(len(original["files"])==746 and sum(r["bytes"]for r in original["files"].values())==4096412802,
      "Wrong original746 frozen census")
    require(all(files.get(p)==row for p,row in original["files"].items()),"Original frozen input changed")
    frozen_name=c.PREFIX+".frozen-prefix-inventory.json"
    frozen_record=record(regular(frozen_name).read_bytes())
    require(inv["original_frozen_inventory"]==files["out/frozen-prefix-inventory.json"]==frozen_record,
      "Original frozen inventory hash differs")
    expected_source={p:dict(bytes=regular(p).stat().st_size,sha256=v)for p,v in m["protected"].items()}
    expected_source[METHOD]=dict(bytes=METHOD_BYTES,sha256=METHOD_SHA)
    actual_source={p[len("tail-source/"):]:row for p,row in files.items()if p.startswith("tail-source/")}
    require(actual_source==expected_source,"Frozen687 source/method projection is incomplete or changed")
    require(inv["roots"]==[r for r in original["roots"]if r!="out/work"]+["tail-source","out"],
      "Full route handoff roots changed")
    output=d["outputs.json"]
    require(output["source"]==SOURCE and output["mode"]==mode and output["stage"]=="route"
      and output["physical_acceptance"]is False,"Original output map lineage changed")
    outer=dict(file_map(output["files"]));outer["outputs.json"]=REQUIRED_DOCS[doc_name(mode,"outputs.json")]
    require(len(outer)==case["outer_files"],"Incomplete original outer archive map")
    records={}
    for name in DIRECT:
        expected=(dict(bytes=METHOD_BYTES,sha256=METHOD_SHA)if name=="method.json"
          else REQUIRED_DOCS[doc_name(mode,name)])
        require(binding["assets"][name]["bytes"]==expected["bytes"]
          and binding["assets"][name]["sha256"]==expected["sha256"],"Retained direct record asset mismatch")
        records[name]=dict(expected,repository_path=METHOD if name=="method.json"else doc_name(mode,name))
        if name not in ("outputs.json","parts.json"):
            require(outer[name]==expected,"Direct record/full outer member mismatch")
    require(proof["inventory"]==REQUIRED_DOCS[doc_name(mode,"route-handoff-inventory.json")]
      and outer["route-handoff.tar.gz"]==proof["archive"],"Nested archive/inventory receipt mismatch")
    # The full nested workspace freezes files before later host packing. Its
    # original core reports and empty stream must join the independently saved records.
    for name in ("host-result.json","inner-result.json","case-result.json","method.json"):
        require(files["out/"+name]==outer[name],"Nested original record differs")
    require(files["out/route-request.json"]==outer["route-request.json"],"Original request record differs")
    empty=dict(bytes=0,sha256=EMPTY)
    require(outer["supervision/one-two-signal-routing-attempt.stderr"]==
      files["out/supervision/one-two-signal-routing-attempt.stderr"]==empty
      and native["commands"][0]["stderr_bytes"]==0
      and native["commands"][0]["stderr_sha256"]==EMPTY,"Failed upload was not the exact empty stream")
    command=native["commands"][0]
    for stream in ("stdout","stderr"):
        name="supervision/one-two-signal-routing-attempt."+stream
        require(outer[name]==files["out/"+name]==dict(bytes=command[stream+"_bytes"],sha256=command[stream+"_sha256"]),
          "Complete actual route stream mismatch")
    retained={a["name"]:a for a in d["release-snapshot.json"]["assets"]}
    h.part_manifest(d["parts.json"],retained)
    for name,asset in binding["assets"].items():
        if name.startswith("route-tail-evidence.tar.gz.part")or name=="parts.json":continue
        path="supervision/"+name if name in ("events.jsonl","latest.json","one-two-signal-routing-attempt.command.json")else name
        require(path in outer and outer[path]==dict(bytes=asset["bytes"],sha256=asset["sha256"]),
          "Retained asset/full outer output mismatch")
    return dict(status="PASS_SAVED_ROUTE_HANDOFF_METADATA_PUBLICATION_REMAINS_FAILED",mode=mode,
      old_context=request,old_audit_context={**request,"stage":"audit"},
      original_run=dict(id=RUN,source=SOURCE,attempt=1,conclusion="failure"),
      original_job=dict(id=case["job"],conclusion="failure",failed_step=7,steps=steps),
      original_publication_failure="HTTP400_Bad_Content_Length_zero_byte_stderr",
      original_audits_executed=False,release=binding,records=records,
      old_method=dict(path=METHOD,bytes=METHOD_BYTES,sha256=METHOD_SHA,protected_count=687,
        protected_sha256=m["protected"],authorizations_are_historical_only=True),
      historical_limits=m["limits"],original_engine=m["engine"],original_input=m["input"],
      original_runtime_image=dict(reference=m["image"],image_id=m["image_id"]),
      required_original_audit_phases=m["phases"][1:],
      outer_expected_files=outer,outer_archive_manifest=d["parts.json"],
      handoff=proof,handoff_inventory=inv,canonical_projection=projection,
      original_frozen_inventory=original,empty_stream=empty,
      metadata_only=True,native_archive_acquired=False,native_member_bytes_reacquired=False,
      new_execution_identity_must_be_separate=True,execution_authorized=False,
      reroute_authorized=False,audit_authorized=False,observer_equivalence_qualified=False,
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)


def validate_saved_case(mode):
    """Authenticate complete saved metadata; this is not archive/ODB verification."""
    select(mode)
    return _validate_saved(mode,source_guard())


def expected_case(mode):
    """Exact historical input to a separately authorized future audit adapter."""
    return validate_saved_case(mode)
