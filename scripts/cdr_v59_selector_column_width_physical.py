#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only exact generated candidate restoration and fresh native physical admission."""
import argparse, json, os, re, shutil, types
from pathlib import Path
import cdr_v59_selector_column_width_native as inherited
import cdr_v59_binding_rc_source as extraction
import cloud_cdr_v59_tail_access_physical as physical
import ensure_cloud_tested_source_release as release
from run_cloud_tx_layout_repair import fetch
ROOT=inherited.ROOT
METHOD=ROOT/"scripts/cdr-v59-selector-column-width-physical-methods.json"
GROUP="cdr-v59-selector-column-width-physical"
OUT=ROOT/("hw/soc/out/cloud-"+GROUP)
VIEW="saved-input"
TOP="nssoc_cdr_pd500_resistor_v59"
APP_SHA=inherited.APP_SHA
PHASES=("drc","lvs","lvs_flat","v59_old_length","gain_gate_disconnected","gain_tail_width",
 "missing_gain_hbt","old_sampler_input_width","old_retime_width","wrong_follower_polarity",
 "old_data_header_length","wrong_finger_count","missing_hbt","q_open","rail_short","offgrid")
PREFIX="docs/evidence/cdr-selector-width-actual-geometry-terminal-20261029."
SUMMARY=PREFIX+"summary.json"
PARTS=PREFIX+"parts.json"
SUMMARY_SHA="3136ff955f69c37130d7d9e13fe15110f472f7e90fbb8d9e64654ba3b8455668"
PARTS_SHA="ab415918a13463ddd1cdcc334f6e7b11c9f5344d3dc3f528265a1353ac32e09e"
HEAD="a1707758a973d78bcd3c786b55810acb4d7d1168"
RUN=40796151572
TAG="cloud-results-40796151572-1-cdr-v59-selector-column-width-native"
GDS_SHA="fb8a0aea5b44627a513db62ed10fe87c66f30697930e1212d3689c7ae981c0c3"
NATIVE=("native_execution_authorized","physical_qualification_authorized")
FALSE=("geometry_generation_authorized","extraction_authorized","simulation_authorized",
       "accepted","electrical_accepted","qualified_pex","full_phy_accepted","automatic_retry")
require=inherited.require
sha=inherited.sha
regular=inherited.regular
read=inherited.read
atomic=inherited.atomic

def validate_authorizations(m):
    require(m["schema"]=="cdr-v59-selector-column-width-physical-v1","Wrong physical method")
    require(m["scope"]=="EXACT_GENERATED_CANDIDATE_DRC_LVS_AND13_FAULTS","Changed scope")
    for k in NATIVE+FALSE+("source_controls_authorized",):
        require(type(m[k])is bool,"Nonboolean authorization")
    require(m["source_controls_authorized"]is True and all(m[k]is False for k in FALSE),"Forbidden scope")
    require(m[NATIVE[0]]is m[NATIVE[1]],"Split physical authorization")
    return m

def methods():
    m=validate_authorizations(read(METHOD));old=inherited.methods()
    require(all(m["protected_sha256"].get(n)==h for n,h in old["protected_sha256"].items()),"Inherited source changed")
    for n,h in m["protected_sha256"].items():
        require(re.fullmatch("[0-9a-f]{64}",h)and sha(regular(ROOT,n))==h,"Protected source changed: "+n)
    return m

def execution_context(m):
    require(ROOT==Path("/home/runner/work/nssoc/nssoc"),"Canonical hosted root required")
    require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
        and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc","Hosted repository required")
    require(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","First attempt only")
    require(all(m[k]is True for k in NATIVE),"Physical execution disabled")
    return m

def authorize():
    return execution_context(methods())

def publication_authorize():
    return execution_context(validate_authorizations(read(METHOD)))

def expected_files():
    require(sha(ROOT/SUMMARY)==SUMMARY_SHA and sha(ROOT/PARTS)==PARTS_SHA,"Saved evidence changed")
    s=read(ROOT/SUMMARY)
    require((s["run_id"],s["source_head"],s["run_attempt"],s["status"])==
      (RUN,HEAD,1,"PASS_GENERATION_AND_SERIALIZED_REREAD_ONLY_UNQUALIFIED"),"Wrong generation")
    require(s["terminal_finalization_complete"]is s["generation_and_serialized_reread_complete"]is True,"Incomplete generation")
    require(all(s[k]is False for k in ("native_DRC_executed","native_LVS_executed","fresh_RC_executed",
      "simulation_executed","physical_accepted","electrical_accepted","full_phy_accepted","automatic_retry")),"Borrowed acceptance")
    require(s["outputs"]["candidate/"+TOP+".gds"]==GDS_SHA,"Wrong generated GDS")
    return {**s["outputs"],"result.json":SUMMARY_SHA}

def validate_live(run,jobs,info,ref):
    require((run["id"],run["head_sha"],run["run_attempt"],run["event"],run["status"],run["conclusion"])==
      (RUN,HEAD,1,"workflow_dispatch","completed","success"),"Producer run changed")
    require(run["path"]==".github/workflows/cdr-v59-selector-column-width-native-cloud.yml","Producer workflow changed")
    wanted={123193007134:"source-controls",123193372637:"geometry"}
    require(jobs["total_count"]==len(jobs["jobs"])==2 and {j["id"]for j in jobs["jobs"]}==set(wanted),"Producer jobs changed")
    for j in jobs["jobs"]:
        require(j["run_id"]==RUN and j["head_sha"]==HEAD and j["name"]==wanted[j["id"]]
          and j["status"]=="completed"and j["conclusion"]=="success","Producer job incomplete")
    proof=release.validate_release(info,ref,TAG,HEAD)
    require(info["id"]==427344642,"Producer release changed")
    original=read(ROOT/(PREFIX+"release.json"))
    projection=lambda rows:sorted([{k:r[k]for k in ("id","name","size","digest")}for r in rows],key=lambda r:r["id"])
    require(projection(info["assets"])==projection(original["assets"]),"Producer assets changed")
    return proof

def validate_view(out):
    out=Path(out);expected=expected_files();root=out/VIEW
    proof=inherited.loaded.verify_exact_files(root,expected)
    # The old qualification reports stay byte-identical and remain historical.
    inherited.validate_candidate(root)
    return dict(complete_input=proof,candidate_gds_sha256=GDS_SHA,
      historical_electrical_rejections_preserved=True,fresh_physical_result_required=True)

def restore(out):
    authorize();out=Path(out)
    proof=validate_live(release.api("actions/runs/"+str(RUN)),
      release.api("actions/runs/"+str(RUN)+"/attempts/1/jobs?per_page=100"),
      release.api("releases/tags/"+TAG),release.api("git/ref/tags/"+TAG))
    transport=out/"input-transport";transport.mkdir()
    base="https://github.com/Melihakbulut221/nssoc/releases/download/"+TAG+"/"
    stem="cdr-v59-selector-column-width-native-"+str(RUN)+"-1."
    for suffix,h in (("summary.json",SUMMARY_SHA),("parts.json",PARTS_SHA)):
        fetch(base+stem+suffix,h,transport/suffix)
        require((transport/suffix).read_bytes()==(ROOT/(PREFIX+suffix)).read_bytes(),"Direct evidence differs")
    manifest=read(transport/"parts.json")
    require(manifest["source_directory"]=="cloud-cdr-v59-selector-column-width-native"
      and manifest["bytes"]==377042664
      and manifest["sha256"]=="b89ecfe3a4d571e7a22e3f32daacaf628b6dc7a713b83e87a19c8b6c9315b399","Wrong archive")
    for row in manifest["parts"]:fetch(base+row["name"],row["sha256"],transport/row["name"])
    extracted=extraction.exact_extract(manifest,transport,out/VIEW,expected_files())
    atomic(out/"restore.json",dict(live=proof,extracted=extracted,view=validate_view(out)))

def runtime_worker():
    authorize()
    original=physical.runtime_worker
    scope=dict(original.__globals__);scope.update(authorize=authorize,methods=methods,OUT=OUT)
    fn=types.FunctionType(original.__code__,scope,original.__name__,original.__defaults__,original.__closure__)
    fn.__kwdefaults__=original.__kwdefaults__
    require(fn.__code__ is original.__code__,"Runtime restoration algorithm changed")
    fn()
    manifest=read(OUT/"runtime-source-manifest.json")
    require(all(sha(regular(ROOT,n))==v["sha256"]for n,v in manifest["files"].items()),"Frozen PDK changed")
    return manifest

def prepare_layout(out):
    out=Path(out);validate_view(out)
    saved=out/VIEW;base=saved/inherited.VIEW/"parent/layout"
    directory=out/"layout";directory.mkdir()
    mapping={TOP+".gds":saved/"candidate"/(TOP+".gds"),
             TOP+".lef":base/(TOP+".lef"),"schematic.cir":base/"schematic.cir"}
    for n,p in mapping.items():
        require(p.is_file()and not p.is_symlink(),"Nonregular layout source")
        shutil.copyfile(p,directory/n);require(sha(directory/n)==sha(p),"Layout copy changed")
    require(sha(directory/(TOP+".gds"))==GDS_SHA,"Wrong candidate")
    original=read(base/"result.json")
    require(type(original["ports"])is dict and len(original["ports"])==25,"Wrong original ports")
    metadata=dict(status="GENERATED_INPUT_VIEW_FOR_FRESH_PHYSICAL_CHECKS",ports=original["ports"],
      inputs={str(p):sha(p)for p in [*mapping.values(),base/"result.json",saved/"candidate/result.json"]},
      outputs={n:sha(directory/n)for n in mapping},
      source_run=RUN,source_head=HEAD,original_metadata_sha256=sha(base/"result.json"),
      generated_candidate_sha256=GDS_SHA,physical_accepted=False,electrical_accepted=False,
      qualified_pex=False,full_phy_accepted=False,original_metadata_unmodified=True)
    atomic(directory/"result.json",metadata)
    target=out/"methods";target.mkdir()
    name="hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py"
    text,changes=physical.frozen.physical_source((ROOT/name).read_text(),"cd_shunt")
    require(len(changes)==4,"Physical adaptations changed")
    (target/"check_physical.py").write_text(text)
    atomic(out/"derived-methods.json",dict(original=name,original_sha256=sha(ROOT/name),
      generated_sha256=sha(target/"check_physical.py"),exact_reversible_changes=changes))
    return metadata

def validate_candidate(out):
    out=Path(out);report=read(out/"physical/result.json")
    physical.validate_physical(report)
    expected=read(out/"layout/result.json")
    require(expected["generated_candidate_sha256"]==GDS_SHA and sha(out/"layout"/(TOP+".gds"))==GDS_SHA,"Candidate changed")
    require(set(report["steps"])==set(PHASES)and len(report["steps"])==16,"Missing physical or fault phase")
    expected_census=dict(npn13g2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)
    for mode in ("lvs","lvs_flat"):
        require(report["steps"][mode]["native_primitive_census"]==expected_census,"500-device primitive census changed")
    for n,h in report["inputs"].items():
        p=Path(n);require(p.is_absolute()and p.is_file()and not p.is_symlink()and sha(p)==h,"Physical input changed")
    require(report["inputs"][str(out/"layout"/(TOP+".gds"))]==GDS_SHA,"Physical report refers to another GDS")
    require(report["serial_phy_complete"]is report["main_chip_integrated"]is report["qualified_pex"]is False,"Scope exceeded")
    derived=read(out/"derived-methods.json")
    require(sha(out/"methods/check_physical.py")==derived["generated_sha256"],"Derived checker changed")
    validate_view(out);methods()
    manifest=read(out/"runtime-source-manifest.json")
    require(all(sha(regular(ROOT,n))==v["sha256"]for n,v in manifest["files"].items()),"PDK changed")
    return dict(result_sha256=sha(out/"physical/result.json"),gds_sha256=GDS_SHA,
      native_physical_qualification_passed=True,drc_categories=560,drc_markers=0,
      hierarchical_and_flat_lvs_500_devices=True,expected_faults_rejected=13,
      electrical_accepted=False,qualified_pex=False,full_phy_accepted=False)

def main():
    p=argparse.ArgumentParser();p.add_argument("mode",choices=("restore","runtime"))
    a=p.parse_args()
    if a.mode=="restore":restore(OUT)
    else:runtime_worker()

if __name__=="__main__":main()
