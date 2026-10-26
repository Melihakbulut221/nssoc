#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual isolated imports of the declared initialization closure; no CAD imports."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import cdr_v59_tail_saved_identity as s

ENTRIES=("cloud_cdr_v59_tail_saved_identity","cdr_v59_tail_saved_identity_native",
 "check_cdr_v59_tail_saved_identity","check_cdr_v59_tail_saved_identity_transport",
 "check_cdr_v59_tail_saved_identity_runtime")
DECLARED=["cdr_v59_tail_access_runtime","cdr_v59_tail_access_topology","cdr_v59_tail_saved_identity","cdr_v59_tail_saved_identity_native","check_cdr_v59_tail_saved_identity","check_cdr_v59_tail_saved_identity_runtime","check_cdr_v59_tail_saved_identity_transport","cloud_cdr_v59_tail_saved_identity","cloud_chunked_results","cloud_verified_parts","ensure_cloud_tested_source_release","migrate_outputs_to_cloud","run_cloud_tx_layout_repair","wait_cloud_tested_source_release"]

def require(value,message):
    if not value:raise AssertionError(message)

class InitialImports(ast.NodeVisitor):
    def __init__(self):self.rows=[]
    def visit_FunctionDef(self,node):pass
    def visit_AsyncFunctionDef(self,node):pass
    def visit_Import(self,node):
        self.rows.extend((a.name.split(".")[0],node.lineno) for a in node.names)
    def visit_ImportFrom(self,node):
        require(node.level==0,"Relative import outside declared closure")
        self.rows.append((node.module.split(".")[0],node.lineno))
    def visit_If(self,node):
        if ast.unparse(node.test)=="__name__ == '__main__'":return
        self.generic_visit(node)

def closure(root,pins):
    queue=list(ENTRIES);found={};edges=[];externals=set()
    while queue:
        name=queue.pop()
        if name in found:continue
        require(name in DECLARED,"Undeclared repository module")
        rel="scripts/"+name+".py";path=root/rel
        require(rel in pins,"Unprotected repository module")
        require(path.is_file() and not path.is_symlink() and not path.parent.is_symlink(),
          "Missing or nonregular repository module")
        require(s.sha(path)==pins[rel],"Changed repository module")
        text=path.read_text();tree=ast.parse(text)
        found[name]=pins[rel]
        visitor=InitialImports();visitor.visit(tree)
        for dep,line in visitor.rows:
            local=root/"scripts"/(dep+".py")
            if dep in sys.stdlib_module_names:
                require(not local.exists() and not local.is_symlink(),"Standard-library shadow")
                externals.add(dep)
            elif dep in DECLARED:
                queue.append(dep);edges.append({"from":name,"line":line,"to":dep})
            elif local.exists() or local.is_symlink():
                raise AssertionError("Undeclared repository module")
            else:raise AssertionError("Undeclared external dependency")
    require(set(found)==set(DECLARED),"Changed exact initialization inventory")
    return {"modules":found,"repository_edges":edges,"stdlib_externals":sorted(externals),
      "deferred_function_and_CAD_imports_outside_scope":True,"initialization_data_reads":[]}

def copy_modules(root):
    (root/"scripts").mkdir()
    for name in DECLARED:shutil.copyfile(s.ROOT/"scripts"/(name+".py"),root/"scripts"/(name+".py"))

def isolated(root,entries):
    program="import importlib,json,sys;sys.path.insert(0,"+repr(str(root/"scripts"))+");names="+repr(list(entries))+";[importlib.import_module(n) for n in names];print(json.dumps(names))"
    return subprocess.run([sys.executable,"-I","-B","-c",program],cwd=root,
      text=True,capture_output=True,timeout=45,check=False)

def controls():
    pins=s.methods()["protected_sha256"]
    proof=closure(s.ROOT,pins);records=[];positives=[]
    with tempfile.TemporaryDirectory(prefix="cdr-identity-imports-") as temp:
        base=Path(temp)
        good=base/"good";good.mkdir();copy_modules(good)
        actual=isolated(good,ENTRIES)
        require(actual.returncode==0 and actual.stderr=="" and json.loads(actual.stdout)==list(ENTRIES),
          "Actual isolated full imports failed")
        positives.extend(("exact_source_initialization_closure","actual_fresh_isolated_full_imports"))
        for missing in ("cdr_v59_tail_saved_identity","wait_cloud_tested_source_release"):
            root=base/("missing-"+missing);root.mkdir();copy_modules(root)
            (root/"scripts"/(missing+".py")).unlink()
            failed=isolated(root,("cloud_cdr_v59_tail_saved_identity",))
            require(failed.returncode==1 and failed.stdout=="","Missing-module fixture setup failure")
            require(failed.stderr.rstrip().endswith("ModuleNotFoundError: No module named '"+missing+"'"),
              "Wrong missing-module exception")
            driver=root/"scripts/cloud_cdr_v59_tail_saved_identity.py"
            require(str(driver) in failed.stderr and "import "+missing in failed.stderr or
              (str(driver) in failed.stderr and "from "+missing in failed.stderr),"Wrong missing-module frame")
            records.append({"case":"actual_absent_"+missing,"returncode":failed.returncode,
              "stdout":failed.stdout,"stderr":failed.stderr})
        def refuse(name,mutate,message):
            root=base/name;root.mkdir();copy_modules(root);mapping=copy.deepcopy(pins)
            mutate(root,mapping)
            try:closure(root,mapping)
            except AssertionError as error:require(str(error)==message,"Wrong import guard refusal")
            else:raise AssertionError("Accepted "+name)
            records.append({"case":name,"error":message})
        rel="scripts/cdr_v59_tail_saved_identity.py"
        refuse("missing_source",lambda r,p:(r/rel).unlink(),"Missing or nonregular repository module")
        refuse("changed_source",lambda r,p:(r/rel).write_text((r/rel).read_text()+"\n# changed\n"),"Changed repository module")
        def link(root,pins):
            (root/rel).unlink();(root/rel).symlink_to(s.ROOT/rel)
        refuse("source_symlink",link,"Missing or nonregular repository module")
        refuse("unprotected_source",lambda r,p:p.pop(rel),"Unprotected repository module")
        def add_import(root,pins,module,local):
            path=root/"scripts/cloud_cdr_v59_tail_saved_identity.py"
            path.write_text("import "+module+"\n"+path.read_text())
            pins[path.relative_to(root).as_posix()]=s.sha(path)
            if local:(root/"scripts"/(module+".py")).write_text("# deliberately undeclared\n")
        refuse("undeclared_local",lambda r,p:add_import(r,p,"fixture_repository",True),"Undeclared repository module")
        refuse("unknown_external",lambda r,p:add_import(r,p,"fixture_external",False),"Undeclared external dependency")
        refuse("stdlib_shadow",lambda r,p:(r/"scripts/json.py").write_text("# shadow\n"),"Standard-library shadow")
    require(len(positives)==2 and len(records)==9,"Incomplete isolated import controls")
    return {"status":"PASS_SAVED_IDENTITY_INITIAL_IMPORT_CONTROLS","positives":positives,"refusals":records,
      "positive_count":2,"refusal_count":9,"closure":proof,"native_or_CAD_imported":False}

def main():
    assert s.methods()["source_controls_authorized"] is True
    out=s.ROOT/"hw/soc/out/cdr-v59-tail-saved-identity-import-controls";out.mkdir(parents=True,exist_ok=False)
    result={"status":"RUNNING_INITIAL_IMPORT_CONTROLS"}
    s.write(out/"result.json",result)
    try:result=controls()
    except BaseException as error:
        result.update(status="FAIL_INITIAL_IMPORT_CONTROLS",error=repr(error));raise
    finally:s.write(out/"result.json",result);print(json.dumps(result,indent=2))

if __name__=="__main__":main()
