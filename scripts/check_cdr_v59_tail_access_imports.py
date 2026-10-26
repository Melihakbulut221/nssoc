#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Initial import closure and isolated real import fixtures; deferred CAD calls excluded."""
import argparse
import ast
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/"scripts/cdr-v59-tail-access-wire-methods.json"
ENTRY="scripts/cloud_cdr_v59_tail_access_physical.py"
INITIAL=["scripts/audit_cloud_route_annotation.py","scripts/audit_cloud_routed_endpoints.py","scripts/audit_cloud_routed_hold_conflicts.py","scripts/branch_hold_targets.py","scripts/candidate_hold_conflicts.py","scripts/cdr_v59_binding_rc_source.py","scripts/cdr_v59_font_roundtrip_contract.py","scripts/cdr_v59_serialized_shape_diagnostic.py","scripts/cdr_v59_tail_access_plan.py","scripts/cdr_v59_tail_access_runtime.py","scripts/cdr_v59_tail_access_topology.py","scripts/cloud_cdr500_input_access_v58_physical.py","scripts/cloud_cdr500_resistor_v59_physical.py","scripts/cloud_cdr_v59_annotation_diagnostic.py","scripts/cloud_cdr_v59_binding_rc.py","scripts/cloud_cdr_v59_font_recovery.py","scripts/cloud_cdr_v59_serialized_shape_diagnostic.py","scripts/cloud_cdr_v59_static_source_recovery.py","scripts/cloud_cdr_v59_tail_access_physical.py","scripts/cloud_chunked_results.py","scripts/cloud_contact_release.py","scripts/cloud_verified_parts.py","scripts/compare_cloud_routed_endpoints.py","scripts/diagnose_cdr_v59_annotation_native.py","scripts/ensure_cloud_tested_source_release.py","scripts/expanded_load_targets.py","scripts/generate_cdr500_resistor_v59.py","scripts/materialize_cdr_v59_static_annotations.py","scripts/measured_hold_targets.py","scripts/migrate_outputs_to_cloud.py","scripts/read_opensta_phase_slacks.py","scripts/refined_hold_targets.py","scripts/refined_load_targets.py","scripts/route_cloud_newer_postcts.py","scripts/run_cloud_tx_layout_repair.py"]

# Exactly the three repository data reads evaluated while importing INITIAL.
# Other recipe/native/archive reads are deferred and are not copied here.
INITIAL_DATA={
    "docs/evidence/cloud-refined-load-hold-targets-20261016.json": {
        "module": "scripts/refined_hold_targets.py",
        "read_line": 31,
        "hash_line": 32,
        "bytes": 53179,
        "sha256": "8eabcf9f3e0ace7ec6240474f1a5a0758c31f0350d559c5ef70a64b43572342b"
    },
    "docs/evidence/route146-all-reachable-branch-recipe-20261016.json": {
        "module": "scripts/branch_hold_targets.py",
        "read_line": 32,
        "hash_line": 32,
        "bytes": 110689,
        "sha256": "12795513c5d9694eaae9daed4ca6b2c6209a42040c1ff8bdba9a23f249e8b31a"
    },
    "docs/evidence/cloud-measured-load-hold-conflicts-20261016.json": {
        "module": "scripts/measured_hold_targets.py",
        "read_line": 30,
        "hash_line": 31,
        "bytes": 382341,
        "sha256": "55046b17b57dc82eeecbd26783ac62241bde725fce3eab21f9f271dd9a76565b"
    }
}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def initial_nodes(tree):
    yield tree
    if isinstance(tree,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):return
    for child in ast.iter_child_nodes(tree):yield from initial_nodes(child)

def data_path(root,path):
    assert isinstance(path,str) and "\\" not in path,("Noncanonical initial data path",path)
    relative=PurePosixPath(path)
    assert not relative.is_absolute() and ".." not in relative.parts,("Escaping initial data path",path)
    assert relative.as_posix()==path and path.startswith("docs/evidence/") and path.endswith(".json"),("Noncanonical initial data path",path)
    assert root.is_dir() and not root.is_symlink(),("Nonregular isolated root",str(root))
    parent=root
    for part in relative.parts[:-1]:
        parent=parent/part
        assert parent.is_dir() and not parent.is_symlink(),("Missing/nonregular initial data parent",path)
    file=root/path
    assert file.is_file() and not file.is_symlink(),("Missing/nonregular initial data",path)
    assert file.resolve().is_relative_to(root.resolve()),("Escaping initial data target",path)
    return file

def data_closure(root,pins,inventory=None):
    inventory=INITIAL_DATA if inventory is None else inventory
    # Check spelling before the exact allowlist so path-escape fixtures test that guard.
    for path in inventory:
        assert isinstance(path,str) and "\\" not in path,("Noncanonical initial data path",path)
        relative=PurePosixPath(path)
        assert not relative.is_absolute() and ".." not in relative.parts,("Escaping initial data path",path)
        assert relative.as_posix()==path and path.startswith("docs/evidence/") and path.endswith(".json"),("Noncanonical initial data path",path)
    assert set(inventory)==set(INITIAL_DATA),("Initial data inventory changed",sorted(inventory))
    result={}
    for path,record in inventory.items():
        assert record==INITIAL_DATA[path],("Initial data metadata changed",path)
        assert pins.get(path)==record["sha256"],("Unprotected/changed initial data pin",path)
        module=root/record["module"]
        assert module.is_file() and not module.is_symlink() and sha(module)==pins[record["module"]],("Changed initial data reader",record["module"])
        tree=ast.parse(module.read_text())
        def same(node,source):
            return ast.dump(node,include_attributes=False)==ast.dump(ast.parse(source).body[0],include_attributes=False)
        reads=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="raw" for t in n.targets)]
        assert len(reads)==1 and reads[0].lineno==record["read_line"] and same(reads[0],"raw=(ROOT/"+repr(path)+").read_bytes()"),("Initial data read binding changed",path)
        hashes=[n for n in tree.body if isinstance(n,ast.Assert) and n.lineno==record["hash_line"]]
        assert len(hashes)==1 and same(hashes[0],"assert hashlib.sha256(raw).hexdigest()==RECIPE_SHA"),("Initial data hash guard changed",path)
        recipes=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="RECIPE_SHA" for t in n.targets)]
        assert len(recipes)==1 and ast.literal_eval(recipes[0].value)==record["sha256"],("Initial data reader digest changed",path)
        file=data_path(root,path)
        assert file.stat().st_size==record["bytes"],("Changed initial data size",path)
        assert sha(file)==record["sha256"],("Changed initial data bytes",path)
        result[path]=dict(record)
    return result

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
    return {"modules":seen,"edges":edges,"data":data_closure(root,pins),"initial_only":True,"deferred_CAD_and_function_imports_excluded":True}

def isolated(root,missing=None,data_error=None):
    code="import sys;sys.path.insert(0,sys.argv[1]);import cloud_cdr_v59_tail_access_physical;print('TAIL_DRIVER_IMPORT_ONLY')"
    proc=subprocess.run([sys.executable,"-I","-B","-c",code,str(root/"scripts")],
        cwd=root,capture_output=True,text=True,timeout=60)
    assert missing is None or data_error is None
    if data_error is not None:
        path,kind=data_error;record=INITIAL_DATA[path]
        assert proc.returncode==1 and proc.stdout=="" and proc.stderr.startswith("Traceback (most recent call last):\n"),vars(proc)
        frames=re.findall(r'^  File "([^"]+)", line ([0-9]+), in ([^\n]+)$',proc.stderr,re.MULTILINE)
        expected=(str(root/record["module"]),str(record["read_line"] if kind=="missing" else record["hash_line"]),"<module>")
        if kind=="missing":
            assert expected in frames,vars(proc)
            assert proc.stderr.splitlines()[-1]=="FileNotFoundError: [Errno 2] No such file or directory: "+repr(str(root/path)),vars(proc)
        else:
            assert kind=="tampered" and frames[-1]==expected,vars(proc)
            assert proc.stderr.splitlines()[-1]=="AssertionError" and "asserthashlib.sha256(raw).hexdigest()==RECIPE_SHA" in proc.stderr.replace(" ", ""),vars(proc)
    elif missing is None:
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
    positives=[{"case":"actual_repository_initial_closure","modules":len(audit["modules"])},
      {"case":"exact_repository_initial_data_reads","data":audit["data"]}];refusals=[]
    def copy(root):
        (root/"scripts").mkdir()
        for p in [*INITIAL,*INITIAL_DATA]:
            original=ROOT/p;body=original.read_bytes();assert hashlib.sha256(body).hexdigest()==pins[p]
            target=root/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
            assert sha(target)==pins[p] and sha(original)==pins[p]
        assert {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}==set(INITIAL)|set(INITIAL_DATA)
    def reject(name,change):
        with tempfile.TemporaryDirectory(prefix="cdr-tail-import-fault-") as folder:
            root=Path(folder);copy(root);local=dict(pins);change(root,local)
            try:closure(root,local)
            except AssertionError as error:refusals.append({"case":name,"error":repr(error),"rejected":True})
            else:raise AssertionError("Accepted import fault "+name)
    with tempfile.TemporaryDirectory(prefix="cdr-tail-import-") as folder:
        root=Path(folder);copy(root)
        assert closure(root,pins)==audit
        positives.append({"case":"exact_isolated_copy_closure","modules":len(INITIAL)})
        positives.append({"case":"actual_full_driver_import","proof":isolated(root)})
        positives.append({"case":"only35_modules_and3_data_files_copied","files":sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())})
        assert len(positives[-1]["files"])==38
        for path in INITIAL_DATA:
            p=root/path;body=p.read_bytes()
            for kind in ("missing","tampered"):
                if kind=="missing":p.unlink()
                else:p.write_bytes(body+b" ")
                try:proof=isolated(root,data_error=(path,kind))
                finally:p.write_bytes(body)
                refusals.append({"case":"actual_"+kind+"_data_"+Path(path).name,"proof":proof,"rejected":True})
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

    def reject_data(name,change,reason):
        with tempfile.TemporaryDirectory(prefix="cdr-tail-data-fault-") as folder:
            root=Path(folder);copy(root);local=dict(pins);inventory={p:dict(v) for p,v in INITIAL_DATA.items()}
            change(root,local,inventory)
            try:data_closure(root,local,inventory)
            except AssertionError as error:
                assert error.args and isinstance(error.args[0],tuple) and error.args[0][0]==reason,(name,repr(error))
                refusals.append({"case":name,"error":repr(error),"rejected":True})
            else:raise AssertionError("Accepted initial data fault "+name)
    path=next(iter(INITIAL_DATA))
    reject_data("missing_initial_data",lambda root,pins,inv:(root/path).unlink(),"Missing/nonregular initial data")
    reject_data("unprotected_initial_data",lambda root,pins,inv:pins.pop(path),"Unprotected/changed initial data pin")
    reject_data("changed_initial_data_pin",lambda root,pins,inv:pins.__setitem__(path,"0"*64),"Unprotected/changed initial data pin")
    reject_data("changed_initial_data_size",lambda root,pins,inv:(root/path).write_bytes((root/path).read_bytes()+b" "),"Changed initial data size")
    reject_data("changed_initial_data_bytes",lambda root,pins,inv:(root/path).write_bytes(b"X"+(root/path).read_bytes()[1:]),"Changed initial data bytes")
    def link_file(root,pins,inv):
        file=root/path;outside=root/"outside.json";file.rename(outside);file.symlink_to(outside)
    reject_data("symlink_initial_data",link_file,"Missing/nonregular initial data")
    def link_parent(root,pins,inv):
        parent=(root/path).parent;outside=root/"outside";parent.rename(outside);parent.symlink_to(outside,target_is_directory=True)
    reject_data("symlink_initial_data_parent",link_parent,"Missing/nonregular initial data parent")
    def directory(root,pins,inv):
        file=root/path;file.unlink();file.mkdir()
    reject_data("directory_initial_data",directory,"Missing/nonregular initial data")
    def replace_path(inv,bad):
        value=inv.pop(path);inv[bad]=value
    for name,bad,reason in (
      ("absolute_data_path","/tmp/escape.json","Escaping initial data path"),
      ("traversal_data_path","docs/evidence/../../escape.json","Escaping initial data path"),
      ("backslash_data_path","docs\\evidence\\escape.json","Noncanonical initial data path"),
      ("noncanonical_data_path","docs//evidence/escape.json","Noncanonical initial data path")):
        reject_data(name,lambda root,pins,inv,bad=bad:replace_path(inv,bad),reason)
    reject_data("undeclared_initial_data",lambda root,pins,inv:inv.__setitem__("docs/evidence/extra.json",dict(inv[path])),"Initial data inventory changed")
    reject_data("omitted_initial_data",lambda root,pins,inv:inv.pop(path),"Initial data inventory changed")
    reject_data("changed_initial_data_metadata",lambda root,pins,inv:inv[path].__setitem__("bytes",1),"Initial data metadata changed")
    def reader_path(root,pins,inv):
        module=root/INITIAL_DATA[path]["module"];body=module.read_text()
        assert body.count(path)==1
        module.write_text(body.replace(path,"docs/evidence/unreviewed.json"));pins[INITIAL_DATA[path]["module"]]=sha(module)
    reject_data("changed_initial_reader_path",reader_path,"Initial data read binding changed")
    def reader_digest(root,pins,inv):
        module=root/INITIAL_DATA[path]["module"];body=module.read_text();digest=INITIAL_DATA[path]["sha256"]
        assert body.count(digest)==1
        module.write_text(body.replace(digest,"0"*64));pins[INITIAL_DATA[path]["module"]]=sha(module)
    reject_data("changed_initial_reader_digest",reader_digest,"Initial data reader digest changed")
    assert len(positives)==5 and len(refusals)==32
    return {"status":"PASS_ACTUAL_TAIL_DRIVER_INITIAL_IMPORT_CONTROLS","positive_count":5,"refusal_count":32,
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
