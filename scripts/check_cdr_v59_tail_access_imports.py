#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Initial import closure and isolated real import fixtures; deferred CAD calls excluded."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/"scripts/cdr-v59-tail-access-wire-methods.json"
ENTRY="scripts/cloud_cdr_v59_tail_access_physical.py"
INITIAL=["scripts/audit_cloud_route_annotation.py","scripts/audit_cloud_routed_endpoints.py","scripts/audit_cloud_routed_hold_conflicts.py","scripts/branch_hold_targets.py","scripts/candidate_hold_conflicts.py","scripts/cdr_v59_binding_rc_source.py","scripts/cdr_v59_font_roundtrip_contract.py","scripts/cdr_v59_serialized_shape_diagnostic.py","scripts/cdr_v59_tail_access_plan.py","scripts/cdr_v59_tail_access_runtime.py","scripts/cdr_v59_tail_access_topology.py","scripts/cloud_cdr500_input_access_v58_physical.py","scripts/cloud_cdr500_resistor_v59_physical.py","scripts/cloud_cdr_v59_annotation_diagnostic.py","scripts/cloud_cdr_v59_binding_rc.py","scripts/cloud_cdr_v59_font_recovery.py","scripts/cloud_cdr_v59_serialized_shape_diagnostic.py","scripts/cloud_cdr_v59_static_source_recovery.py","scripts/cloud_cdr_v59_tail_access_physical.py","scripts/cloud_chunked_results.py","scripts/cloud_contact_release.py","scripts/cloud_verified_parts.py","scripts/compare_cloud_routed_endpoints.py","scripts/diagnose_cdr_v59_annotation_native.py","scripts/ensure_cloud_tested_source_release.py","scripts/expanded_load_targets.py","scripts/generate_cdr500_resistor_v59.py","scripts/materialize_cdr_v59_static_annotations.py","scripts/measured_hold_targets.py","scripts/migrate_outputs_to_cloud.py","scripts/read_opensta_phase_slacks.py","scripts/refined_hold_targets.py","scripts/refined_load_targets.py","scripts/route_cloud_newer_postcts.py","scripts/run_cloud_tx_layout_repair.py"]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def initial_nodes(tree):
    yield tree
    if isinstance(tree,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):return
    for child in ast.iter_child_nodes(tree):yield from initial_nodes(child)

def closure(root,pins):
    scripts=root/"scripts"
    assert scripts.is_dir() and not scripts.is_symlink()
    expected=set(INITIAL);known={Path(p).stem:p for p in expected}
    assert len(known)==len(expected)
    # A repository file must never masquerade as an installed standard module.
    for p in scripts.iterdir():
        if p.suffix==".py" or p.is_dir():
            assert p.stem not in sys.stdlib_module_names,("Standard-library shadow",p.name)
    seen={};edges=[];todo=[ENTRY]
    while todo:
        path=todo.pop()
        if path in seen:continue
        assert path in expected and path in pins,("Unprotected repository import",path)
        file=root/path
        assert file.is_file() and not file.is_symlink(),("Missing/nonregular repository import",path)
        assert sha(file)==pins[path],("Changed repository import",path)
        seen[path]={"bytes":file.stat().st_size,"sha256":pins[path]}
        for node in initial_nodes(ast.parse(file.read_text())):
            if isinstance(node,ast.Import):names=[alias.name for alias in node.names]
            elif isinstance(node,ast.ImportFrom):
                assert node.level==0 and node.module,("Unsupported relative import",path)
                names=[node.module]
            else:continue
            for name in names:
                first=name.split(".")[0];candidate="scripts/"+first+".py"
                if first in known or (scripts/(first+".py")).exists() or (scripts/first).exists():
                    assert "." not in name and candidate in expected and candidate in pins,("Undeclared repository import",path,name)
                    assert first not in sys.stdlib_module_names
                    edges.append({"from":path,"to":candidate});todo.append(candidate)
                else:
                    assert first in sys.stdlib_module_names,("Unknown non-stdlib dependency",path,name)
    assert set(seen)==expected,("Initial dependency inventory changed",sorted(expected-set(seen)))
    return {"modules":seen,"edges":edges,"initial_only":True,"deferred_CAD_and_function_imports_excluded":True}

def isolated(root,missing=None):
    code="import sys;sys.path.insert(0,sys.argv[1]);import cloud_cdr_v59_tail_access_physical;print('TAIL_DRIVER_IMPORT_ONLY')"
    proc=subprocess.run([sys.executable,"-I","-B","-c",code,str(root/"scripts")],
        cwd=root,capture_output=True,text=True,timeout=60)
    if missing is None:
        assert proc.returncode==0 and proc.stdout=="TAIL_DRIVER_IMPORT_ONLY\n" and proc.stderr=="",vars(proc)
    else:
        assert proc.returncode==1 and proc.stdout==""
        assert proc.stderr.splitlines()[-1]=="ModuleNotFoundError: No module named '"+missing+"'",vars(proc)
    return {"returncode":proc.returncode,"stdout":proc.stdout,"stderr":proc.stderr}

def controls():
    assert os.environ.get("GITHUB_ACTIONS")=="true" and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    methods=json.loads(METHOD.read_text());assert methods["source_controls_authorized"] is True
    pins=methods["protected_sha256"]
    for p,h in pins.items():assert (ROOT/p).is_file() and not (ROOT/p).is_symlink() and sha(ROOT/p)==h,p
    audit=closure(ROOT,pins)
    positives=[{"case":"actual_repository_initial_closure","modules":len(audit["modules"])}];refusals=[]
    def copy(root):
        (root/"scripts").mkdir()
        for p in INITIAL:
            target=root/p;target.write_bytes((ROOT/p).read_bytes());assert sha(target)==pins[p]
    def reject(name,change):
        with tempfile.TemporaryDirectory(prefix="cdr-tail-import-fault-") as folder:
            root=Path(folder);copy(root);local=dict(pins);change(root,local)
            try:closure(root,local)
            except AssertionError as error:refusals.append({"case":name,"error":repr(error),"rejected":True})
            else:raise AssertionError("Accepted import fault "+name)
    with tempfile.TemporaryDirectory(prefix="cdr-tail-import-") as folder:
        root=Path(folder);copy(root)
        assert closure(root,pins)["modules"]==audit["modules"]
        positives.append({"case":"exact_isolated_copy_closure","modules":len(INITIAL)})
        positives.append({"case":"actual_full_driver_import","proof":isolated(root)})
        for missing in ("cdr_v59_tail_access_runtime","refined_hold_targets"):
            p=root/"scripts"/(missing+".py");body=p.read_bytes();p.unlink()
            proof=isolated(root,missing);p.write_bytes(body)
            refusals.append({"case":"actual_missing_"+missing,"proof":proof,"rejected":True})
    reject("missing_initial_dependency",lambda root,pins:(root/"scripts/cdr_v59_tail_access_runtime.py").unlink())
    reject("unprotected_initial_dependency",lambda root,pins:pins.pop("scripts/cdr_v59_tail_access_runtime.py"))
    reject("changed_initial_dependency",lambda root,pins:(root/ENTRY).write_text((root/ENTRY).read_text()+"\n# changed\n"))
    reject("standard_library_shadow",lambda root,pins:(root/"scripts/json.py").write_text("raise RuntimeError('shadow')\n"))
    def symlink(root,pins):
        p=root/"scripts/cdr_v59_tail_access_runtime.py";target=root/"outside.py";p.rename(target);p.symlink_to(target)
    reject("symlink_initial_dependency",symlink)
    def unknown(root,pins):
        p=root/ENTRY;p.write_text(p.read_text()+"\nimport explicit_unknown_repository_dependency\n");pins[ENTRY]=sha(p)
    reject("unknown_not_assumed_installed",unknown)
    def undeclared(root,pins):
        p=root/"scripts/explicit_extra_module.py";p.write_text("VALUE=1\n")
        entry=root/ENTRY;entry.write_text(entry.read_text()+"\nimport explicit_extra_module\n")
        pins[ENTRY]=sha(entry);pins["scripts/explicit_extra_module.py"]=sha(p)
    reject("undeclared_repository_module",undeclared)
    assert len(positives)==3 and len(refusals)==9
    return {"status":"PASS_ACTUAL_TAIL_DRIVER_INITIAL_IMPORT_CONTROLS","positive_count":3,"refusal_count":9,
      "positives":positives,"refusals":refusals,"closure":audit,
      "installed_external_allowlist":[],"native_executed":False,"deferred_native_imports_validated":False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    result={"status":"RUNNING_IMPORT_CONTROLS","native_executed":False}
    args.output.write_text(json.dumps(result)+"\n")
    try:result=controls()
    except BaseException as error:
        result.update(status="FAIL_IMPORT_CONTROLS",error=repr(error));args.output.write_text(json.dumps(result,indent=2)+"\n");raise
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True),flush=True)

if __name__=="__main__":main()
