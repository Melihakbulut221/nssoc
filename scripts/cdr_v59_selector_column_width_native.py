#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Separate, disabled geometry admission over unchanged qualified restore/generator code."""
import argparse, hashlib, json, os, re, secrets, types
from pathlib import Path
import cdr_v59_tail_loaded_admission as loaded
import generate_cdr_v59_selector_column_width as generator

ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/"scripts/cdr-v59-selector-column-width-native-methods.json"
OLD_METHOD="scripts/cdr-v59-selector-column-width-methods.json"
OLD_METHOD_SHA="6c21be6812b515275a94cf64448c736aa78b90ec0725204c963c9c3b047fe535"
OUT=ROOT/"hw/soc/out/cloud-cdr-v59-selector-column-width-native"
GROUP="cdr-v59-selector-column-width-native"
VIEW="current-mim-bundle/canonical-current-view"
APP_SHA="d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"
NATIVE=("native_execution_authorized","geometry_generation_authorized")
FALSE=("physical_qualification_authorized","extraction_authorized","simulation_authorized",
       "physical_accepted","electrical_accepted","qualified_pex","full_phy_accepted","automatic_retry")
require=loaded.require
sha=loaded.sha
regular=loaded.regular

def read(path):
    require(path.is_file()and not path.is_symlink(),"Invalid JSON file")
    return json.loads(path.read_bytes())

def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    require(not any(p.is_symlink()for p in (path,*path.parents)),"Symlink in atomic path")
    temp=path.with_name(path.name+"."+secrets.token_hex(12)+".incomplete")
    with temp.open("x")as f:
        json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write("\n")
        f.flush();os.fsync(f.fileno())
    os.replace(temp,path)

def validate_authorizations(m):
    require(m["schema"]=="cdr-v59-selector-column-width-native-v1","Wrong geometry method")
    for k in NATIVE+FALSE+("source_controls_authorized",):
        require(type(m[k])is bool,"Authorization must be boolean: "+k)
    require(m["source_controls_authorized"]is True,"Source controls disabled")
    require(all(m[k]is False for k in FALSE),"Forbidden qualification or electrical flag")
    require(m[NATIVE[0]]is m[NATIVE[1]],"Split geometry authorization")
    require(m["inherited_width_method"]==OLD_METHOD and m["inherited_width_method_sha256"]==OLD_METHOD_SHA,
            "Tested width method identity changed")
    require(m["scope"]=="GENERATION_AND_SERIALIZED_REREAD_ONLY","Geometry scope changed")
    return m

def methods():
    m=validate_authorizations(read(METHOD))
    pins=m["protected_sha256"]
    require(type(pins)is dict and pins.get(OLD_METHOD)==OLD_METHOD_SHA,"Missing tested width method pin")
    old=read(regular(ROOT,OLD_METHOD))
    require(len(old["protected_sha256"])==960 and sha(ROOT/OLD_METHOD)==OLD_METHOD_SHA,"Tested 960-pin method changed")
    require(all(pins.get(n)==h for n,h in old["protected_sha256"].items()),"Inherited protected map changed")
    for n,h in pins.items():
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h),"Invalid protected digest")
        require(sha(regular(ROOT,n))==h,"Protected source changed: "+n)
    return m

def execution_context(m):
    require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
        and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc","Hosted repository required")
    require(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","First attempt required")
    require(all(m[k]is True for k in NATIVE),"Geometry stage disabled")
    return m

def authorize():
    return execution_context(methods())

def publication_authorize():
    # Evidence-only publication must still work after a protected-input failure.
    # This path cannot restore, load native code, generate geometry, or qualify success.
    return execution_context(validate_authorizations(read(METHOD)))

def width_contract():
    return read(generator.CONTRACT)

def validate_view(out):
    loaded.verify_restored(out)
    c=width_contract();expected=c["baseline_inventory"]
    projection={n[len("canonical-current-view/"):]:h for n,h in loaded.expected_files().items()
                if n.startswith("canonical-current-view/")}
    require(len(expected)==605 and projection==expected,"Full605 view differs from complete3823 capsule")
    proof=loaded.verify_exact_files(Path(out)/VIEW,expected)
    graph=read(regular(ROOT,c["qualified_graph_path"]))
    require(sha(ROOT/c["qualified_graph_path"])==c["qualified_graph_sha256"],"Original graph changed")
    generator.validate_graph(c,graph["geometry"])
    return dict(full_capsule_members=3823,consumed_view=VIEW,view=proof,
      original_graph_reference_only=True,candidate_graph_qualified=False)

def restore(out):
    authorize()
    # A fresh function namespace replaces only the authority callback. Original
    # snapshots, live run/tag/assets, exact_extract and all return checks remain.
    def geometry_gate(prepare_only):
        require(prepare_only is True,"Unexpected historical restore mode")
        return authorize()
    scope=dict(loaded.restore.__globals__);scope["authorize"]=geometry_gate
    fn=types.FunctionType(loaded.restore.__code__,scope,loaded.restore.__name__,
                          loaded.restore.__defaults__,loaded.restore.__closure__)
    fn.__kwdefaults__=loaded.restore.__kwdefaults__
    require(fn.__code__ is loaded.restore.__code__,"Restore algorithm changed")
    report,proof,model,composition,planes,plane_proof=fn(Path(out),True)
    view=validate_view(out)
    result=dict(saved_input=proof,view=view,plane_proof=plane_proof,
      inherited_restore_code_unchanged=True,historical_authorization_borrowed=False,
      baseline_model_sha256=sha(model),original_reports_retained=True)
    atomic(Path(out)/"restore.json",result)
    return result

def generate(out):
    authorize();out=Path(out);validate_view(out)
    previous=generator.METHOD
    try:
        generator.METHOD=METHOD
        result=generator.run(out/VIEW,out/"candidate")
    finally:
        generator.METHOD=previous
    validate_view(out)
    return result

def validate_candidate(out):
    out=Path(out);p=out/"candidate";r=read(regular(p,"result.json"));c=width_contract()
    require(r["status"]=="GENERATED_UNQUALIFIED_ADDITIVE_COLUMN_WIDTH","Generation or reread rejected")
    require(r["input_gds_sha256"]==c["baseline_inventory"][generator.GDS],"Wrong source GDS")
    require(r["candidate_gds_sha256"]==sha(regular(p,generator.TOP+".gds")),"Candidate GDS changed")
    require(r["proposal"]==c["declared_rectangles"]and len(r["added_raw_records"])==26,"Exact26 additions changed")
    ownership=r["actual_original_native_ownership_and_clearance"]
    expected={(tag,row["device"],row["net"],row["layer"]):c["owner_partitions"][tag][row["net"]]["native_cluster"]
              for tag in c["placements"]for row in c["declared_rectangles"]}
    require(len(ownership)==len(expected)==52,"Complete52 ownership checks missing")
    found={}
    for row in ownership:
        key=tuple(row[k]for k in ("placement","device","net","layer"))
        require(key not in found and key in expected and row["native_cluster"]==expected[key],"Native ownership identity changed")
        require(type(row["old_component_area_dbu2"])is int and row["old_component_area_dbu2"]>0
            and type(row["added_area_dbu2"])is int and row["added_area_dbu2"]>0
            and row["clearance_dbu"]==c["clearance_dbu"][str(row["layer"])],"Native clearance evidence changed")
        found[key]=row

    require(r["all_original_material_raw_text_properties_hierarchy_preserved"]is True,"Original material lost")
    require(r["original_500_devices_1446_terminals_978_anchors_reference_only"]is True,"Reference scope changed")
    for k in ("native_DRC_executed","native_LVS_executed","fresh_RC_executed","simulation_executed",
              "physical_accepted","electrical_accepted","full_phy_accepted"):
        require(r[k]is False,"Unexpected candidate qualification: "+k)
    require(not r.get("terminal_errors"),"Generator terminal failure")
    require(r["outputs"]=={n:h for n,h in generator.frozen.files(p).items()if n!="result.json"},
            "Complete candidate inventory changed")
    require(set(r["outputs"])=={generator.TOP+".gds"},"Unexpected candidate files")
    validate_view(out)
    return dict(result_sha256=sha(p/"result.json"),gds_sha256=r["candidate_gds_sha256"],
                generation_and_serialized_reread_complete=True,physical_accepted=False)

def main():
    p=argparse.ArgumentParser();p.add_argument("mode",choices=("source-preflight","restore","generate"))
    args=p.parse_args()
    if args.mode=="source-preflight":
        m=methods();print(json.dumps(dict(protected_files=len(m["protected_sha256"]),native_enabled=m[NATIVE[0]])));return
    authorize()
    if args.mode=="restore":restore(OUT)
    else:generate(OUT)

if __name__=="__main__":main()
