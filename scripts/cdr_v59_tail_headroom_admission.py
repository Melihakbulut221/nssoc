#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticate the six current PVT captures; never invoke a native engine."""
import ast, hashlib, json, os, re, subprocess, types
from pathlib import Path, PurePosixPath
import numpy as np
import cdr_v59_headroom_readback_admission as old
import cdr_v58_saved_rows as rows

ROOT = Path(__file__).resolve().parents[1]
METHOD = "scripts/cdr-v59-tail-headroom-methods.json"
RUN = 40737889314
HEAD = "5e373a9378b4a3c0fad51687a604a14668dba3ce"
CASES = ("nominal_early","nominal_late","hot_early","hot_late","cold_early","cold_late")
MODEL = "current-mim-bundle/mim/composition/pd500-mim-wire.spice"
CONTRACT = "current-mim-bundle/mim/composition/composition.json"
PLANES = "current-mim-bundle/mim/precise/source/native-planes.json"
SELECT = ("native/wave.raw","native/native.log","native/bench.cir",
          "native/original-bench.cir","native/op.dat",MODEL,CONTRACT,PLANES,
          "native-controller-result.json")
ALWAYS_FALSE = ("simulation_authorized","native_execution_authorized","extraction_authorized",
                "geometry_authorized","accepted","cdr_accepted","qualified_pex","full_phy_accepted",
                "electrical_acceptance","automatic_native_retry")
API = "repos/Melihakbulut221/nssoc/"

def need(ok, message):
    if not ok:
        raise AssertionError(message)

def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

def regular(root, name):
    need(type(name) is str and name and "\\" not in name and "\0" not in name, "bad path")
    p = PurePosixPath(name)
    need(str(p)==name and not p.is_absolute() and ".." not in p.parts, "path escape")
    target = Path(root)
    need(target.is_dir() and not target.is_symlink(), "invalid root")
    for part in p.parts:
        target /= part
        need(not target.is_symlink(), "linked path")
    need(target.is_file(), "missing regular file: "+name)
    return target

def read_json(path):
    def object_pairs(pairs):
        result={}
        for k,v in pairs:
            need(k not in result,"duplicate JSON key")
            result[k]=v
        return result
    return json.loads(Path(path).read_bytes(),object_pairs_hook=object_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))

def validate_method(m):
    need(m["schema"]=="cdr-current-tail-six-PVT-saved-row-readback-v1","method schema")
    need(m["original_run"]==RUN and m["original_source"]==HEAD,"wrong producer")
    need(m["case_order"]==list(CASES) and set(m["cases"])==set(CASES),"case census")
    need(m["source_controls_authorized"] is True,"source controls disabled")
    need(type(m["readback_authorized"]) is bool,"invalid readback authorization")
    need(all(m[k] is False for k in ALWAYS_FALSE),"scope widened")
    need(m["numerical_gates"]==dict(sampler_ps=37.5,comparator_ps=75,
        minimum_active_vce_v=.4,maximum_alltime_abs_vce_v=1.6,UI_ps=125),"numerical gates changed")
    need(type(m["protected_sha256"]) is dict and len(m["protected_sha256"])>=948,"source census")
    for path,digest in m["protected_sha256"].items():
        need(re.fullmatch(r"[0-9a-f]{64}",digest) is not None,"invalid source digest")
        need(path!=METHOD,"recursive method pin")
    return m

def methods(root=ROOT):
    m=validate_method(read_json(regular(root,METHOD)))
    for path,digest in m["protected_sha256"].items():
        need(sha(regular(root,path))==digest,"protected source changed: "+path)
    return m

def cloud_guard(m, env=None, readback=True):
    env=os.environ if env is None else env
    need(env.get("GITHUB_ACTIONS")=="true" and env.get("RUNNER_OS")=="Linux","GitHub Linux only")
    need(env.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc","wrong repository")
    need(env.get("GITHUB_RUN_ATTEMPT")=="1","no repeated attempt")
    need(re.fullmatch(r"[1-9][0-9]*",env.get("GITHUB_RUN_ID","")) is not None,"bad run")
    need(re.fullmatch(r"[0-9a-f]{40}",env.get("GITHUB_SHA","")) is not None,"bad source")
    need(env.get("GITHUB_REF","").startswith("refs/heads/codex/"),"unexpected ref")
    validate_method(m)
    if readback:
        need(m["readback_authorized"] is True,"readback not authorized")

def api(path):
    return json.loads(subprocess.check_output(["gh","api",API+path]))

def identity(run, job, release, tag, pin):
    need(run["id"]==RUN and run["head_sha"]==HEAD and run["run_attempt"]==1,"run identity")
    need(run["event"]=="workflow_dispatch" and run["workflow_id"]==398807429
        and run["path"]==".github/workflows/cdr-v59-tail-loaded-cloud.yml","producer workflow")
    need(job["id"]==pin["job_id"] and job["run_id"]==RUN and job["run_attempt"]==1
        and job["head_sha"]==HEAD and job["name"]=="loaded ("+pin["case"]+")","job identity")
    need(job["status"]=="completed" and job["conclusion"]=="failure","nonterminal/nonrejected producer")
    need(release["id"]==pin["release_id"] and release["tag_name"]==pin["tag"]
        and release["target_commitish"]==HEAD and release["draft"] is False
        and release["prerelease"] is True,"release identity")
    need(tag["object"]["type"]=="commit" and tag["object"]["sha"]==HEAD,"source tag")
    actual=[{k:a[k]for k in ("id","name","size","digest")}for a in release["assets"]]
    need(len(actual)==len({x["name"]for x in actual}),"duplicate hosted asset")
    need(sorted(actual,key=lambda x:x["name"])==sorted(pin["asset_census"],key=lambda x:x["name"]),
        "producer asset census changed")

def reference(case,m,root=ROOT):
    need(case in CASES,"unknown PVT case")
    pin=m["cases"][case]
    docs={}
    for role,entry in pin["documents"].items():
        path=regular(root,entry["path"])
        need(sha(path)==entry["sha256"],"changed reference "+role)
        docs[role]=read_json(path)
    validate_reports(case,pin,docs)
    return pin,docs

def validate_reports(case,pin,d):
    n,o,p,prepared=d["native"],d["summary"],d["manifest"],d["preparation_native"]
    need(pin["case"]==n["case"]==o["case"]==case,"case identity")
    need(n["source_head"]==o["source_head"]==prepared["source_head"]==HEAD,"source identity")
    need(o["run_id"]==RUN and o["run_attempt"]==1 and o["preparation_only"] is False,"outer identity")
    need(o["group"]=="cdr-v59-tail-loaded-"+case,"outer group")
    need(o["status"]=="FAIL_OR_REJECTED_CURRENT_TAIL_LOADED_CASE"
        and o["command"]["returncode"]==1,"original rejection missing")
    need(n["status"]=="REJECTED_WHOLE_MIM_PD500_LOADED" and n["returncode"]==0,"native status")
    need(n["error"]=="AssertionError('Actual whole-wire retimed sampling, loaded phase/current or device gate failed')",
        "different native failure")
    need(n["actual_fault_detected"] is False and n["devices_passed"] is False
        and n["data_passed"] is False,"original PVT failure changed")
    need(n["vi"]["passed"] is (case=="cold_late"),"original VI result changed")
    need(n["sources_unchanged"] is True and n["current_saved_input_integrity"]==
        dict(files=3823,all_hashes_unchanged=True,exact_inventory=True),"saved source inventory")
    need(n["native_flags_verified"]==124 and n["zero_source_op_maximum"]==0 and n["diagnostics"]==[],
        "native startup changed")
    for record in (n,o):
        need(all(record[k] is False for k in ("accepted","cdr_accepted","qualified_pex","full_phy_accepted")),
            "acceptance widened")
        need(record["terminal_finalization_complete"] is True
            and record["terminal_inventory_complete"] is True and record["terminal_errors"]==[],
            "incomplete original terminal")
    need(o["outer_terminal_finalization_complete"] is True and o["outer_terminal_errors"]==[],
        "incomplete original outer terminal")
    native_sha=pin["documents"]["native"]["sha256"]
    need(o["native_controller_result_sha256"]==o["outputs"]["native-controller-result.json"]==native_sha,
        "native summary join")
    need({k:o["outputs"][k]for k in n["outputs"]}==n["outputs"],"native output map differs")
    need(len(n["outputs"])==pin["native_outputs"] and len(o["outputs"])==pin["outer_outputs"],
        "original output census")
    need(len(n["vectors"])==len(set(n["vectors"]))==1151 and n["raw_capture"]["columns"]==1152,
        "vector census")
    need(n["raw_capture"]["raw_sha256"]==n["outputs"]["native/wave.raw"]==pin["wave_sha256"],
        "wave hash join")
    need(n["raw_capture"]["complete_unmodified_rows"] is True,"partial native capture")
    need(n["source_bits"]==old.original.primitive.prbs(0x7f)
        and hashlib.sha256(bytes(n["source_bits"])).hexdigest()==n["source_bits_sha256"],"source bits")
    need(n["data_offset_s"]==(-.15 if case.endswith("_early")else .15)*rows.UI,"input phase")
    need(n["vectors"]==prepared["vectors"] and n["vector_census"]==prepared["vector_census"]
        and n["native_save_commands"]==prepared["native_save_commands"],"preparation vector join")
    need(n["binding"]==prepared["binding"] and n["native_plane_source"]==prepared["native_plane_source"],
        "preparation model join")
    need(prepared["status"]=="PASS_PD500_LOADED_PREPARATION_AND13_BINDING_CONTROLS_NO_TRANSIENT"
        and prepared["transient_executed"] is False,"preparation status")
    need(p==pin["parts"] and p["source_directory"]=="cloud-cdr-v59-tail-loaded-"+case
        and p["stem"]=="cdr-v59-tail-loaded-"+case+"-"+str(RUN)+"-1","parts identity")
    need(p["verification"]["all_parts_and_combined_bytes_verified"] is True,"unverified parts")
    need([x["index"]for x in p["parts"]]==list(range(len(p["parts"])))
        and len({x["name"]for x in p["parts"]})==len(p["parts"])
        and sum(x["bytes"]for x in p["parts"])==p["bytes"],"parts census")
    for part in p["parts"]:
        asset=pin["assets"][part["name"]]
        need(asset["name"]==part["name"] and asset["size"]==part["bytes"]
            and asset["digest"]=="sha256:"+part["sha256"],"part metadata join")
    return dict(original_rejection=True,VI_only_passed=n["vi"]["passed"],accepted=False)

def download(pin,target,m):
    cloud_guard(m)
    old.asset_identity(api("releases/assets/"+str(pin["id"])),pin)
    need(not target.exists() and not target.is_symlink(),"download destination exists")
    with target.open("xb")as stream:
        p=subprocess.run(["gh","api",API+"releases/assets/"+str(pin["id"]),
                          "-H","Accept: application/octet-stream","--allow-escape-sequences"],
                         stdout=stream,timeout=900)
    need(p.returncode==0 and target.stat().st_size==pin["size"]
        and sha(target)==pin["digest"][7:],"download integrity")

def adapted_function(name, overrides):
    path=regular(ROOT,"scripts/cdr_v59_headroom_readback_admission.py")
    need(sha(path)=="38707c950e9a78c0d1429adda69c81299a0f290d925f9704432c8bde16947fd1",
        "original reader adapter source changed")
    text=path.read_text()
    nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name==name]
    need(len(nodes)==1,"missing immutable function")
    scope=dict(vars(old));scope.update(overrides)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path)+"::current-tail-adapter","exec"),scope)
    return scope[name],dict(original_file_sha256=sha(path),function=name,
        original_function_sha256=hashlib.sha256(ast.get_source_segment(text,nodes[0]).encode()).hexdigest(),
        function_AST_unchanged=True,overridden_globals=sorted(overrides))

def restore(case,work,m):
    cloud_guard(m)
    pin,docs=reference(case,m)
    run=api("actions/runs/"+str(RUN));job=api("actions/jobs/"+str(pin["job_id"]))
    rel=api("releases/"+str(pin["release_id"]));tag=api("git/ref/tags/"+pin["tag"])
    identity(run,job,rel,tag,pin)
    work.mkdir(parents=True,exist_ok=False)
    transport=work/"transport";transport.mkdir()
    for role in ("native","summary","manifest"):
        target=transport/(role+".json");download(pin["assets"][role],target,m)
        need(target.read_bytes()==regular(ROOT,pin["documents"][role]["path"]).read_bytes(),
            "remote reference bytes differ")
    for part in docs["manifest"]["parts"]:
        download(pin["assets"][part["name"]],transport/part["name"],m)
    extract,adaptation=adapted_function("extract",{"SELECT":SELECT})
    saved=work/"saved"
    proof=extract(docs["manifest"],transport,saved,docs["summary"],pin["documents"]["summary"]["sha256"])
    need((saved/"native-controller-result.json").read_bytes()==
        regular(ROOT,pin["documents"]["native"]["path"]).read_bytes(),"archived native record differs")
    need((saved/"result.json").read_bytes()==regular(ROOT,pin["documents"]["summary"]["path"]).read_bytes(),
        "archived outer record differs")
    proof.update(adapter=adaptation,original_run=RUN,case=case,source=HEAD,
                 release_id=pin["release_id"],tag=pin["tag"],source_job=pin["job_id"],
                 all_original_outputs_verified=True,local_execution=False)
    return saved,docs["native"],proof

def replay_all(source,t,d,capture,report):
    # Exactly the original 6722-byte six measurement blocks, including all gates.
    # The old diagnostic helper's additional "VI must fail" assertion is not a
    # measurement predicate and would incorrectly reject genuine cold_late VI.
    env=dict(np=np,UI=rows.UI,START=rows.START,STOP=rows.STOP,STEP=rows.STEP)
    exec(compile(rows.measurement_source(source),"<immutable-CDR-measurements>","exec"),env)
    r=env["replay"](t,d,capture,report["binding"],report["source_bits"],report["data_offset_s"],
                   False,report["devices"],report["mos_devices"],report["native_caps"])
    rows.compare_reproduction(r,report)
    need(report["case"]in CASES and not r["devices_passed"] and not r["data_passed"],
        "original PVT rejection missing")
    need(r["vi"]["passed"]is(report["case"]=="cold_late"),"original VI result differs")
    return r

def validate_native(saved,report):
    proxy=types.SimpleNamespace(STOP=rows.STOP,STEP=rows.STEP,replay=replay_all)
    reader,adaptation=adapted_function("validate_native",{
        "MODEL":MODEL,"CONTRACT":CONTRACT,"PLANES":PLANES,"rows":proxy})
    t,d,contract,replayed=reader(saved,report)
    need(sha(saved/PLANES)==report["native_plane_source"]["native_planes_sha256"],"native plane hash")
    return t,d,contract,dict(adapter=adaptation,complete_original_measurements=replayed,
        original_status=report["status"],readback_only=True,all_numerical_gates_unchanged=True,
        accepted=False,cdr_accepted=False,qualified_pex=False,full_phy_accepted=False)
