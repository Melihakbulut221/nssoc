#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact fresh-tail RC admission; preserves failed physical and old electrical evidence."""
import ast,hashlib,json,os,re,types
from collections import Counter
from pathlib import Path,PurePosixPath
import cdr_v59_binding_rc_source as saved
import ensure_cloud_tested_source_release as release
from run_cloud_tx_layout_repair import fetch

ROOT=Path(__file__).resolve().parents[1]
METHOD="scripts/cdr-v59-tail-loaded-methods.json"
PIN="scripts/cdr-v59-tail-loaded-contract.json"
MODEL="nssoc_cdr_pd500_resistor_mim_wire_v59"
PREFIX="docs/evidence/cdr-v59-tail-fresh-RC-native-terminal-20261027"
SUMMARY=PREFIX+"-native-summary.json"
STAGE=PREFIX+"-native-MIM-precision-result.json"
PIPELINE_SOURCE="scripts/cloud_cdr_v59_mim_stage.py"
PIPELINE_SHA="15c6d6f6399f28a211ad0ea86a385d4400ab43aab6b0109214240b6eca935372"
PIPELINE_PASS="PASS_PD500_MIM_NATIVE_DOUBLE_TOTALS_TWO_ORDERS_22_CONTROLS_EACH_AND21_COMPOSITION_CONTROLS_REQUIRES_LOADED_WAVES"
OUTER_PASS="PASS_FRESH_TAIL500_BINDING_WIRE_RC_SEVEN_MIM_TWO_ORDERS_REQUIRES_ORIGINAL_ELECTRICAL_MATRIX"
CASES=("nominal_early","nominal_late","hot_early","hot_late","cold_early","cold_late","constant_zero","constant_one","clock_stopped","vi_bias_off")
ALWAYS_FALSE=("geometry_generation_authorized","native_extraction_authorized","accepted","electrical_accepted","physical_accepted","cdr_accepted","qualified_pex","full_phy_accepted","automatic_retry")
AUTH=("source_controls_authorized","workflow_dispatch_authorized","preparation_authorized","native_execution_authorized","simulation_authorized")

def require(value,reason):
    if not value:raise AssertionError(reason)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb")as f:
        while b:=f.read(4*1024**2):h.update(b)
    return h.hexdigest()

def relative(name):
    require(type(name)is str and name and "\\"not in name,"Invalid relative path")
    p=PurePosixPath(name)
    require(not p.is_absolute()and str(p)==name and all(x not in ("",".","..")for x in p.parts),"Invalid relative path")
    return p

def regular(root,name):
    p=Path(root);require(p.is_dir()and not p.is_symlink(),"Invalid protected root")
    for part in relative(name).parts:
        p=p/part;require(not p.is_symlink(),"Symlink in protected path")
    require(p.is_file(),"Missing protected regular file")
    return p

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n")
    temporary.replace(path)

def validate_authorizations(m):
    require(all(type(m[k])is bool for k in AUTH+ALWAYS_FALSE+("controller_readiness",)),"Authorization fields must be strict booleans")
    require(all(m[k]is False for k in ALWAYS_FALSE),"Forbidden geometry/extraction/acceptance authorization")
    require(m["native_execution_authorized"]is m["simulation_authorized"],"Split simulator authorization")
    require(not m["simulation_authorized"]or m["preparation_authorized"],"Simulation requires preparation authorization")
    if m["preparation_authorized"]or m["simulation_authorized"]:
        require(m["source_controls_authorized"]and m["workflow_dispatch_authorized"]and m["controller_readiness"],"Execution requires source controls, dispatch and readiness")
    require(m["cases"]==list(CASES),"Original ten cases changed")
    return True

def methods():
    m=json.loads(regular(ROOT,METHOD).read_bytes());validate_authorizations(m)
    for name,digest in m["protected_sha256"].items():
        require(re.fullmatch("[0-9a-f]{64}",digest)is not None,"Invalid protected digest")
        require(sha(regular(ROOT,name))==digest,"Protected source or evidence changed: "+name)
    require(m["contract"]==PIN,"Contract path changed")
    return m

def descriptor():
    return json.loads(regular(ROOT,PIN).read_bytes())

def frozen_pipeline_validator(producer_source):
    path=regular(ROOT,PIPELINE_SOURCE)
    require(sha(path)==PIPELINE_SHA,"Frozen pipeline validator changed")
    nodes=[n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=="validate_pipeline"]
    require(len(nodes)==1,"Frozen pipeline validator missing")
    # This is a saved producer report. Bind the original source comparison to its
    # authenticated producer; do not rewrite that report to the consuming job.
    scope={"os":types.SimpleNamespace(environ={"GITHUB_SHA":producer_source}),"PASS":PIPELINE_PASS}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),scope)
    return scope["validate_pipeline"]

def validate_reports(c,s):
    p=c["actual_fresh_RC"];r=s["summary.json"];mim=s["MIM-precision-result.json"];b=s["binding-result.json"];contract=s["composition.json"]
    producer=p["run"]["head_sha"]
    require(p["run"]["id"]==40576801174 and p["run"]["run_attempt"]==1,"Wrong fresh RC producer")
    require(r["status"]==OUTER_PASS and r["source_head"]==producer and r["run_id"]==p["run"]["id"]and r["run_attempt"]==1,"Fresh RC terminal identity changed")
    require(all(r[k]is True for k in ("binding_executed","extraction_executed","fresh_RC_pipeline_complete","terminal_finalization_complete","original_failure_preserved")),"Fresh RC completion missing")
    require(all(r[k]is False for k in ("simulation_executed","physical_geometry_regenerated","physical_accepted","electrical_accepted","qualified_pex","full_phy_accepted","automatic_retry")),"Fresh RC scope changed")
    require(r["original_physical_run"]==40369539200 and r["original_physical_status"]=="FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL","Original physical failure lost")
    require(len(r["commands"])==4 and all(x["returncode"]==0 and x["supervision_failure"]is None and not x["process_group_cleanup"]["remaining_live"]for x in r["commands"]),"Fresh RC owned command failed")
    expected={**r["outputs"],"result.json":p["snapshots"]["summary.json"]["sha256"]}
    require(expected==p["expected_files"]and len(expected)==3823,"Complete fresh RC member map changed")
    require(s["parts.json"]==p["complete_archive"],"Fresh RC parts changed")
    for name,suffix in (("binding","binding-result.json"),("mim","MIM-precision-result.json")):
        report=s[suffix];full={**report["outputs"],"result.json":p["snapshots"][suffix]["sha256"]}
        require(len(full)==(53 if name=="binding"else 2181),"Complete nested output count changed")
        require(all(expected.get(name+"/"+n)==h for n,h in full.items()),"Complete nested output join changed")
    require(mim["source_head"]==producer and b["source_head"]==producer,"Nested producer source changed")
    require(r["binding_result_sha256"]==p["snapshots"]["binding-result.json"]["sha256"],"Binding summary hash changed")
    require(r["wire_RC_result_sha256"]==p["snapshots"]["wire-RC-result.json"]["sha256"],"Wire RC summary hash changed")
    require(r["completed_pipeline"]["summary_sha256"]==p["snapshots"]["MIM-precision-result.json"]["sha256"],"MIM summary hash changed")
    require(mim["composition"]["contract"]==contract,"Composition report differs")
    require(contract["counts"]==p["counts"]=={"devices":500,"R":24616,"C":15722},"Current model census changed")
    require(contract["interface"]==p["interface"]and contract["interface"]==s["binding.json"]["native_ports"]+["wire_cref"],"Current ordered native ports changed")
    require(len(contract["interface"])==len(set(contract["interface"]))==26,"Current interface is not unique")
    require(b["binding"]==s["binding.json"],"Current complete binding differs")
    require(s["binding.json"]["census"]=={"npn13G2":124,"sg13_lv_nmos":50,"rppd":98,"cap_cmim":7,"ptap1":221},"Current device classes changed")
    require(len(s["binding.json"]["devices"])==len({d["native_id"]for d in s["binding.json"]["devices"]})==500,"Current device identities changed")
    require(len(contract["device_records"])==500 and {d["native_id"]for d in contract["device_records"]}=={d["native_id"]for d in s["binding.json"]["devices"]},"Composition device identities changed")
    require(mim["current_input_integrity"]==p["same_run_current_input_integrity"],"Same-run input integrity changed")
    require(mim["current_input_integrity"]["all_fresh_source_inputs_unchanged"]is True,"Fresh inputs changed")
    for order in ("precise","precise_reversed"):
        pair=mim["variants"][order]
        require(len(pair["audit"]["wire_controls"]["cases"])==13 and len(pair["audit"]["intrinsic_controls"])==9,"Original MIM audit controls changed")
    require(len(mim["composition"]["controls"])==21,"Original composition controls changed")
    projected=contract["native_extracted_mim_cards_projected_once"]
    cap_ids={d["native_id"]for d in contract["device_records"]if d["model"]=="cap_cmim"}
    require(contract["intrinsic_mim_models_in_final_netlist"]==7 and contract["all_raw_wire_tokens_preserved"]is True
      and type(projected)is list and len(projected)==7 and len({x["native_id"]for x in projected})==7
      and {x["native_id"]for x in projected}==cap_ids,"Intrinsic versus wire composition changed")
    frozen_pipeline_validator(producer)(mim,0)
    require(c["original_electrical"]["cases"]==list(CASES)and c["proposed_execution"]["all_original_cases"]==list(CASES),"Original electrical cases changed")
    return True

def snapshots():
    methods();c=descriptor();s={}
    for name,spec in c["actual_fresh_RC"]["snapshots"].items():
        f=regular(ROOT,spec["path"])
        require(f.stat().st_size==spec["bytes"]and sha(f)==spec["sha256"],"Saved fresh RC JSON changed")
        s[name]=json.loads(f.read_bytes())
    validate_reports(c,s)
    return s

def validate_remote(c,run,jobs,info,ref):
    p=c["actual_fresh_RC"]
    require(all(run.get(k)==v for k,v in p["run"].items()),"Live producer run changed")
    expected={j["id"]:j for j in p["jobs"]}
    require(jobs["total_count"]==len(jobs["jobs"])==len(expected),"Live producer job count changed")
    require(len({j["id"]for j in jobs["jobs"]})==len(expected),"Duplicate live producer job")
    for j in jobs["jobs"]:
        require(j["id"]in expected and all(j.get(k)==v for k,v in expected[j["id"]].items()),"Live producer job changed")
    require(info["id"]==p["release"]["id"],"Live producer release changed")
    proof=release.validate_release(info,ref,p["release"]["tag_name"],p["run"]["head_sha"])
    fields=("id","name","size","digest","state")
    actual=sorted([{k:a[k]for k in fields}for a in info["assets"]],key=lambda a:a["id"])
    require(actual==sorted(p["assets"],key=lambda a:a["id"]),"Live producer assets changed")
    return proof

def expected_files():
    return descriptor()["actual_fresh_RC"]["expected_files"]

def verify_exact_files(root,expected):
    require(root.is_dir()and not root.is_symlink(),"Invalid restored root")
    found={}
    for path in root.rglob("*"):
        require(not path.is_symlink(),"Symlink in restored inventory")
        if path.is_dir():continue
        require(path.is_file(),"Nonregular restored member")
        found[str(path.relative_to(root))]=sha(path)
    require(found==expected,"Complete restored member map changed")
    return {"files":len(found),"all_hashes_unchanged":True,"exact_inventory":True}

def verify_restored(out):
    return verify_exact_files(Path(out)/"current-mim-bundle",expected_files())

def authorize(prepare_only):
    require(type(prepare_only)is bool,"Preparation mode must be a boolean")
    m=methods()
    require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc","Hosted repository execution required")
    require(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","First attempt required")
    require(m["preparation_authorized"if prepare_only else"simulation_authorized"]is True,"Requested loaded mode is disabled")
    return m

def restore(out,prepare_only):
    authorize(prepare_only);c=descriptor();s=snapshots();p=c["actual_fresh_RC"];out=Path(out)
    require(out.is_dir()and not out.is_symlink(),"Invalid loaded output root")
    runid=p["run"]["id"];tag=p["release"]["tag_name"]
    run=release.api("actions/runs/"+str(runid));jobs=release.api("actions/runs/"+str(runid)+"/attempts/1/jobs?per_page=100")
    info=release.api("releases/tags/"+tag);ref=release.api("git/ref/tags/"+tag)
    remote=validate_remote(c,run,jobs,info,ref)
    transport=out/"current-mim-transport";transport.mkdir(exist_ok=False)
    actual={a["id"]:a for a in info["assets"]}
    for a in p["assets"]:
        relative(a["name"]);require("/"not in a["name"],"Invalid asset basename")
        target=transport/a["name"];digest=a["digest"].removeprefix("sha256:")
        fetch(actual[a["id"]]["browser_download_url"],digest,target)
        require(target.stat().st_size==a["size"]and sha(target)==digest,"Downloaded producer asset changed")
    for name,spec in p["snapshots"].items():
        matches=[a for a in p["assets"]if a["name"].endswith("."+name)]
        require(len(matches)==1,"Direct snapshot asset missing or ambiguous")
        require((transport/matches[0]["name"]).read_bytes()==regular(ROOT,spec["path"]).read_bytes(),"Direct producer JSON bytes changed")
    bundle=out/"current-mim-bundle"
    archive=saved.exact_extract(s["parts.json"],transport,bundle,p["expected_files"])
    require(archive["regular_members"]==3823,"Current archive member count changed")
    for member,suffix in (("result.json","summary.json"),("mim/result.json","MIM-precision-result.json"),("binding/result.json","binding-result.json"),("binding/binding.json","binding.json"),("mim/composition/composition.json","composition.json")):
        require(regular(bundle,member).read_bytes()==regular(ROOT,p["snapshots"][suffix]["path"]).read_bytes(),"Restored report bytes differ")
    model=regular(bundle,"mim/composition/pd500-mim-wire.spice")
    contract=json.loads(regular(bundle,"mim/composition/composition.json").read_bytes())
    plane_path=regular(bundle,"mim/precise/source/native-planes.json");planes=json.loads(plane_path.read_bytes())
    require(planes["status"]=="PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS"and len(planes["anchors"])==160 and len({a["logical_net"]for a in planes["anchors"]})==51,"Current native plane qualification changed")
    layouts=[h for n,h in planes["inputs"].items()if n.endswith("/layout/result.json")]
    require(layouts==[sha(regular(bundle,"mim/precise/source/parent/layout/result.json"))],"Current planes/layout join changed")
    require(regular(bundle,"mim/precise/model-binding/binding.json").read_bytes()==regular(bundle,"binding/binding.json").read_bytes(),"Current binding view changed")
    for order in ("precise","precise_reversed"):
        require(regular(bundle,"mim/"+order+"/source/native-planes.json").read_bytes()==plane_path.read_bytes(),"Order plane identity changed")
    verify_restored(out)
    proof={"run":runid,"source_head":p["run"]["head_sha"],"reservation":remote,"full_archive":archive,
      "summary_sha256":p["snapshots"]["summary.json"]["sha256"],"stage_sha256":p["snapshots"]["MIM-precision-result.json"]["sha256"],
      "original_physical_run":40369539200,"original_physical_status":"FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL",
      "original_eight_electrical_rejections_and_two_fault_detections_preserved":True,
      "geometry_regenerated":False,"extraction_rerun":False,"simulation_preaccepted":False}
    plane_proof={"current_mim_source":proof["stage_sha256"],"native_planes_sha256":sha(plane_path),
      "fresh_layout_sha256":layouts[0],"native_binding_sha256":sha(regular(bundle,"binding/binding.json"))}
    return s["MIM-precision-result.json"],proof,model,contract,planes,plane_proof
