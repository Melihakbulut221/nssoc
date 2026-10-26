#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source controls only. Native geometry faults execute separately."""
import ast
import copy
import inspect
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import cdr_v59_tail_access_plan as plan
import generate_cdr_v59_tail_access_wire as native

ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/"scripts/cdr-v59-tail-access-wire-methods.json"

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def actual_snapshot_call_signatures(text):
    tree=ast.parse(text)
    signature=inspect.signature(native.verify_snapshot)
    rows=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Name) or node.func.id!="verify_snapshot":
            continue
        assert not any(isinstance(a,ast.Starred) for a in node.args)
        assert all(k.arg is not None for k in node.keywords)
        signature.bind(*[object() for _ in node.args],**{k.arg:object() for k in node.keywords})
        rows.append(node.lineno)
    assert len(rows)==4,rows
    return sorted(rows)


def actual_output_metadata(text):
    """Execute the real two metadata assignments and the unchanged probe guard."""
    function=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=="generate_admitted")
    assignments=[]
    for n in ast.walk(function):
        if not isinstance(n,ast.Assign) or len(n.targets)!=1:continue
        target=n.targets[0]
        if isinstance(target,ast.Subscript) and isinstance(target.value,ast.Name) and target.value.id in ("meta","child_meta") and isinstance(target.slice,ast.Constant) and target.slice.value in ("outputs","output_sha256"):
            assignments.append(n)
    assert len(assignments)==2
    original=json.loads((ROOT/"docs/evidence/cdr-v4-rc-inputs-20261017.json").read_text())["report"]["original_extraction_methods"]["probe01.py"]
    assert hashlib.sha256(original["text"].encode()).hexdigest()==original["sha256"]
    guard=[n for n in ast.parse(original["text"]).body if isinstance(n,ast.Assert) and "pin(GDS)" in ast.unparse(n) and "['outputs']" in ast.unparse(n)]
    assert len(guard)==1
    rows=[]
    with tempfile.TemporaryDirectory(prefix="cdr-tail-output-fields-") as tmp:
        root=Path(tmp)
        for assignment in assignments:
            name=assignment.targets[0].value.id
            parent=root/name;directory=parent/"layout91";directory.mkdir(parents=True)
            gds=directory/"fixture.gds";gds.write_bytes(b"explicit synthetic geometry bytes, no CAD")
            metadata={"outputs":{"fixture.gds":"0"*64}}
            # The child source result already exists; the new parent destination does not.
            if name=="child_meta":(directory/"result.json").write_text("{}\n")
            scope={"sha":native.sha,name:metadata,"directory":directory,"dest":directory}
            exec(compile(ast.Module(body=[assignment],type_ignores=[]),native.__file__,"exec"),scope)
            (directory/"result.json").write_text(json.dumps(metadata)+"\n")
            probe={"pin":lambda p:{"sha256":native.sha(p)},"GDS":gds,"P":parent,"json":json}
            exec(compile(ast.Module(body=guard,type_ignores=[]),"unchanged-original-probe-guard","exec"),probe)
            assert metadata["outputs"]["fixture.gds"]==native.sha(gds)
            assert "result.json" not in metadata["outputs"]
            rows.append({"metadata_variable":name,"field":assignment.targets[0].slice.value,
                         "actual_assignment_line":assignment.lineno,"actual_probe_guard_passed":True})
    return rows


def actual_input_relocation_controls(text):
    """Actual metadata assignment and frozen checker loops; files here are synthetic."""
    original=json.loads((ROOT/"docs/evidence/cdr-v59-cd-shunt-first-physical-result-20261025.json").read_text())["layout"]
    serialized=(json.dumps(original,indent=2)+"\n").encode()
    summary=json.loads(native.SUMMARY.read_text())
    expected_actual={k[len("analysis-capsule/"):]:v for k,v in summary["outputs"].items() if k.startswith("analysis-capsule/")}
    assert hashlib.sha256(serialized).hexdigest()==expected_actual["parent/layout/result.json"]=="4b36c9731972d2bb1f1035ae780fdb2c5692bb32a767dc8369dc1f1fa84cde5b"
    runtime_actual=json.loads(native.RUNTIME.read_text())["relative_runtime_sha256"]
    canonical=Path("/home/runner/work/nssoc/nssoc")
    historical=canonical/"hw/soc/out/cloud-cdr500-resistor-v59-cd_shunt"
    lib_actual=canonical/"pdk/libs.tech/klayout/python"
    classifications=[]
    for name,h in original["inputs"].items():
        path=Path(name)
        if path.is_relative_to(historical):
            assert expected_actual[str(path.relative_to(historical))]==h
            classifications.append("historical")
        elif path.is_relative_to(lib_actual):
            assert runtime_actual[str(path.relative_to(lib_actual))]==h
            classifications.append("runtime")
        else:
            assert path==canonical/"scripts/generate_cdr500_resistor_v59.py"
            assert digest(ROOT/path.relative_to(canonical))==h
            classifications.append("generator")
    assert len(classifications)==243
    assert {n:classifications.count(n) for n in set(classifications)}=={"historical":154,"runtime":88,"generator":1}
    function=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=="generate_admitted")
    assignment=[n for n in function.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call)
                and isinstance(n.value.func,ast.Name) and n.value.func.id=="relocate_physical_inputs"]
    assert len(assignment)==1
    assert ast.unparse(assignment[0].targets[0])=="(meta['inputs'], meta['tail_access_input_relocation'])"
    checker=ROOT/"hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py"
    checker_text=checker.read_text()
    assert hashlib.sha256(checker_text.encode()).hexdigest()=="46c2673bd3262998639ac47c465f14c24c90a1b494e7fd6dfe852e1af670886b"
    run=next(n for n in ast.parse(checker_text).body if isinstance(n,ast.FunctionDef) and n.name=="run")
    pins=[n for n in run.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="pins" for t in n.targets)]
    update=[n for n in run.body if isinstance(n,ast.Expr) and "pins.update" in ast.unparse(n) and 'generated["outputs"]' in ast.get_source_segment(checker_text,n)]
    pre=[n for n in run.body if isinstance(n,ast.If) and "Layout source changed" in ast.unparse(n)]
    terminal=[n for n in ast.walk(run) if isinstance(n,ast.If) and "Inputs changed during verification" in ast.unparse(n)]
    assert len(pins)==len(update)==len(pre)==len(terminal)==1
    def compiled(nodes):return compile(ast.Module(body=nodes,type_ignores=[]),str(checker),"exec")
    preflight=compiled(pins+update+pre);final=compiled(terminal)
    positives=[{"case":"actual_complete243_input_manifest_join","historical":154,"runtime":88,"generator":1,
                "original_parent_bytes":len(serialized),"original_parent_sha256":hashlib.sha256(serialized).hexdigest(),
                "archive_read":False}]
    failures=[]
    with tempfile.TemporaryDirectory(prefix="cdr-tail-all-inputs-") as temp:
        base=Path(temp)
        def fixture(label):
            root=base/label;root.mkdir()
            source=root/"hw/soc/out/cloud-cdr-v59-font-recovery/analysis-capsule"
            source.mkdir(parents=True)
            lib=root/"pdk/libs.tech/klayout/python"
            metadata=copy.deepcopy(original);metadata["inputs"]={}
            expected=dict(expected_actual);runtime=dict(runtime_actual)
            for name,h in original["inputs"].items():
                old=Path(name);local=root/old.relative_to(canonical)
                if old.is_relative_to(historical):
                    relative=old.relative_to(historical);target=source/relative
                    body=("explicit synthetic restored bytes:"+str(relative)).encode()
                    h=hashlib.sha256(body).hexdigest();expected[str(relative)]=h
                elif old.is_relative_to(lib_actual):
                    relative=old.relative_to(lib_actual);target=lib/relative
                    body=("explicit synthetic runtime bytes:"+str(relative)).encode()
                    h=hashlib.sha256(body).hexdigest();runtime[str(relative)]=h
                else:
                    target=local;body=(ROOT/old.relative_to(canonical)).read_bytes()
                    assert hashlib.sha256(body).hexdigest()==h
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
                metadata["inputs"][str(local)]=h
            (source/"parent/layout").mkdir(parents=True,exist_ok=True)
            (source/"parent/layout/result.json").write_bytes(serialized)
            layout=root/"candidate/parent/layout";layout.mkdir(parents=True)
            (layout/"fixture.gds").write_bytes(b"explicit synthetic current GDS output; no CAD")
            metadata["outputs"]={"fixture.gds":digest(layout/"fixture.gds")}
            return dict(root=root,source=source,lib=lib,meta=metadata,expected=expected,runtime=runtime,
                        layout=layout,proof={},relocate_physical_inputs=native.relocate_physical_inputs)
        def bind(f):
            from unittest import mock
            with mock.patch.object(native,"ROOT",f["root"]),mock.patch.object(native,"CANONICAL",f["source"]):
                exec(compile(ast.Module(body=assignment,type_ignores=[]),native.__file__,"exec"),f)
            f["generated"]=f["meta"];f["Path"]=Path;f["digest"]=native.sha
            return f["meta"]["tail_access_input_relocation"]
        def check(f):exec(preflight,f)
        f=fixture("positive")
        old=copy.deepcopy(f["meta"]["inputs"]);proof=bind(f);check(f);exec(final,f)
        assert proof["original_inputs"]==old and len(f["pins"])==244
        assert (f["source"]/"parent/layout/result.json").read_bytes()==serialized
        positives.append({"case":"actual_assignment_to_frozen_initial_and_terminal_digest_loops",
          "input_pins":243,"current_output_pins":1,"old_metadata_unchanged":True,
          "all_file_bytes_explicitly_synthetic_except_original_source_and_metadata":True})
        def refuse(label,mutate,stage,kind,reason):
            f=fixture(label)
            if stage in ("checker","terminal"):bind(f)
            if stage=="terminal":check(f)
            mutate(f)
            try:
                if stage=="bind":bind(f)
                elif stage=="original":f.update(generated=f["meta"],Path=Path,digest=native.sha);check(f)
                elif stage=="checker":check(f)
                else:exec(final,f)
            except Exception as error:
                assert type(error) is kind,(label,type(error),repr(error))
                if kind is FileNotFoundError:
                    assert error.filename==str(f["root"]/"hw/soc/out/cloud-cdr500-resistor-v59-cd_shunt/source/result.json")
                else:
                    actual=error.args[0][0] if isinstance(error.args[0],tuple) else error.args[0]
                    assert actual==reason,(label,repr(error))
                failures.append({"case":label,"error":repr(error),"actual_phase":stage})
            else:raise AssertionError("Accepted input relocation fault "+label)
        first=lambda f:str(f["root"]/"hw/soc/out/cloud-cdr500-resistor-v59-cd_shunt/source/result.json")
        runtime_key=lambda f:next(k for k in f["meta"]["inputs"] if Path(k).is_relative_to(f["lib"]))
        source_file=lambda f:f["source"]/"source/result.json"
        def rename(f,name):
            h=f["meta"]["inputs"].pop(first(f));f["meta"]["inputs"][name(f)]=h
        refuse("original_missing_historical_path",lambda f:None,"original",FileNotFoundError,None)
        refuse("omitted_inherited_input",lambda f:f["meta"]["inputs"].pop(first(f)),"bind",AssertionError,"Changed complete inherited input census")
        refuse("changed_historical_digest",lambda f:f["meta"]["inputs"].__setitem__(first(f),"0"*64),"bind",AssertionError,"Historical input not bound by restored capsule")
        refuse("changed_runtime_digest",lambda f:f["meta"]["inputs"].__setitem__(runtime_key(f),"0"*64),"bind",AssertionError,"Changed frozen runtime input")
        refuse("changed_generator_digest",lambda f:f["meta"]["inputs"].__setitem__(str(f["root"]/"scripts/generate_cdr500_resistor_v59.py"),"0"*64),"bind",AssertionError,"Changed original generator input")
        refuse("undeclared_repository_input",lambda f:rename(f,lambda z:str(z["root"]/"scripts/unprotected.py")),"bind",AssertionError,"Unexpected inherited repository input")
        refuse("escaping_historical_path",lambda f:rename(f,lambda z:first(z).replace("/source/result.json","/source/../result.json")),"bind",AssertionError,"Noncanonical inherited input path")
        refuse("noncanonical_historical_path",lambda f:rename(f,lambda z:first(z).replace("/source/result.json","/source/./result.json")),"bind",AssertionError,"Noncanonical inherited input path")
        refuse("missing_capsule_member",lambda f:f["expected"].pop("source/result.json"),"bind",AssertionError,"Historical input not bound by restored capsule")
        refuse("changed_capsule_member_hash",lambda f:f["expected"].__setitem__("source/result.json","0"*64),"bind",AssertionError,"Historical input not bound by restored capsule")
        refuse("missing_restored_file",lambda f:source_file(f).unlink(),"bind",AssertionError,"Missing or changed physical input")
        refuse("tampered_restored_file",lambda f:source_file(f).write_bytes(b"changed"),"bind",AssertionError,"Missing or changed physical input")
        def link_file(f):
            p=source_file(f);target=p.with_name("original-bytes.json");p.rename(target);p.symlink_to(target)
        refuse("symlink_restored_file",link_file,"bind",AssertionError,"Symlink in physical input")
        def link_parent(f):
            p=f["source"]/"source";target=p.with_name("source-real");p.rename(target);p.symlink_to(target,target_is_directory=True)
        refuse("symlink_restored_ancestor",link_parent,"bind",AssertionError,"Symlink in physical input")
        def directory(f):
            p=source_file(f);p.unlink();p.mkdir()
        refuse("directory_instead_of_restored_file",directory,"bind",AssertionError,"Missing or changed physical input")
        refuse("tampered_metadata_after_binding",lambda f:f["meta"]["inputs"].__setitem__(str(source_file(f)),"0"*64),"checker",ValueError,"Layout source changed")
        refuse("tampered_current_output",lambda f:(f["layout"]/"fixture.gds").write_bytes(b"changed"),"checker",ValueError,"Layout source changed")
        refuse("restored_input_changed_after_preflight",lambda f:source_file(f).write_bytes(b"changed"),"terminal",ValueError,"Inputs changed during verification")
        refuse("missing_frozen_runtime",lambda f:Path(runtime_key(f)).unlink(),"bind",AssertionError,"Missing or changed physical input")
    assert len(positives)==2 and len(failures)==19
    return {"status":"PASS_ACTUAL_ALL_INPUT_RELOCATION_AND_FROZEN_DIGEST_LOOPS",
      "positives":positives,"refusals":failures,"positive_count":2,"refusal_count":19,
      "actual_parent_metadata_census":243,"historical_relocated":154,"runtime_unchanged":88,"generator_unchanged":1,
      "checker_source_sha256":"46c2673bd3262998639ac47c465f14c24c90a1b494e7fd6dfe852e1af670886b",
      "all_actual_archive_file_hashes_joined_without_archive_access":True,
      "filesystem_fixtures_synthetic":True,"CAD_executed":False}

def controls():
    assert os.environ.get("GITHUB_ACTIONS")=="true"
    method=json.loads(METHOD.read_text())
    assert method["source_controls_authorized"] is True
    for key in ("native_execution_authorized","geometry_generation_authorized","extraction_authorized","simulation_authorized"):
        assert type(method[key]) is bool
    for path,want in method["protected_sha256"].items():
        p=ROOT/path
        assert p.is_file() and not p.is_symlink() and digest(p)==want,("Changed protected source",path)
    h=json.loads((ROOT/"docs/evidence/cdr-v59-master-tail-source-routing-handoff-20261026.json").read_text())
    actual=plan.candidate_plan(h)
    assert actual["new_bus_dbu"]==[370000,174430,1041525,177630]
    assert actual["native_via_parameters"]==plan.PARAMETERS
    assert len(actual["local_taps"])==8 and len(actual["placements"])==2
    assert actual["placements"][0]["bus_dbu"]==[1363600,446430,2035125,449630]
    assert actual["placements"][1]["bus_dbu"]==[1363600,1635950,2035125,1639150]
    assert actual["devices_changed"]==0 and actual["old_routes_preserved"] is True
    assert all(actual[k] is False for k in ("reference_changed","physical_accepted","electrical_improvement_proven","simulation_authorized","native_execution_authorized"))
    cases=[]
    def reject(name,change):
        x=copy.deepcopy(h);change(x)
        try:plan.candidate_plan(x)
        except (AssertionError,KeyError) as e:cases.append({"case":name,"rejected":True,"error":repr(e)})
        else:raise AssertionError("Accepted source mapping fault: "+name)
    reject("wrong_original_GDS",lambda x:x.update(current_candidate_GDS_sha256="0"*64))
    reject("wrong_leaf_origin",lambda x:x.update(source_leaf_origin_translation_um=[0,-3.965]))
    reject("wrong_coordinate_frame",lambda x:x.update(route_coordinates_before_origin_translation=False))
    reject("reordered_routes",lambda x:x["actual_M_TE_routes"].reverse())
    reject("wrong_route_net",lambda x:x["actual_M_TE_routes"][0].update(net="S_TE"))
    reject("shifted_lane",lambda x:x["actual_M_TE_routes"][0].update(escape_lane_um=371.005))
    reject("shifted_escape_y",lambda x:x["actual_M_TE_routes"][0].update(escape_y_um=119.995))
    reject("changed_escape_width",lambda x:x["actual_M_TE_routes"][0].update(escape_width_um=.405))
    reject("wrong_pin_layer",lambda x:x["actual_M_TE_routes"][0].update(source_layer=1))
    reject("wrong_pin_via_columns",lambda x:x["actual_M_TE_routes"][0].update(pin_via_columns=3))
    reject("wrong_lane_via_columns",lambda x:x["actual_M_TE_routes"][0].update(lane_via_columns=4))
    reject("omitted_anchor",lambda x:x["native_terminal_rows"].pop())
    reject("duplicate_anchor",lambda x:x["native_terminal_rows"].__setitem__(0,copy.deepcopy(x["native_terminal_rows"][1])))
    reject("shifted_actual_anchor",lambda x:x["native_terminal_rows"][0].update(point_dbu=[1885246,406030]))
    reject("wrong_actual_native_cluster",lambda x:x["native_terminal_rows"][0].update(native_cluster=124))
    reject("wrong_actual_wire_component",lambda x:x["native_terminal_rows"][0].update(wire_component=61))
    reject("changed_device_model",lambda x:x["native_terminal_rows"][0].update(model="rppd"))
    reject("wrong_parent_translation",lambda x:x["target_native_nodes"]["D"].update(parent_translation_um=[993.605,272]))
    reject("wrong_parent_tag",lambda x:x["target_native_nodes"]["D"].update(parent="sc"))
    assert len(cases)==19
    call_lines=actual_snapshot_call_signatures((ROOT/"scripts/generate_cdr_v59_tail_access_wire.py").read_text())
    old=(ROOT/"docs/evidence/cdr-v59-tail-native-generator-first-draft-20261026.py").read_text()
    assert hashlib.sha256(old.encode()).hexdigest()=="565e70daad68d58e974c203b2e4957cb98a826e4534b718522aed20a9d25cf15"
    try:actual_snapshot_call_signatures(old)
    except TypeError as e:
        assert str(e)=="too many positional arguments"
        signature_failure={"actual_first_draft_source":"565e70daad68d58e974c203b2e4957cb98a826e4534b718522aed20a9d25cf15",
          "actual_current_function_signature":str(inspect.signature(native.verify_snapshot)),"error":repr(e)}
    else:raise AssertionError("Accepted first-draft extra serialized-reread argument")
    current=(ROOT/"scripts/generate_cdr_v59_tail_access_wire.py").read_text()
    input_relocation=actual_input_relocation_controls(current)
    output_rows=actual_output_metadata(current)
    assert len(output_rows)==2 and all(r["field"]=="outputs" for r in output_rows)
    output_refusals=[]
    for label,bad in [
        ("previous_wrong_field",current.replace('["outputs"]={p.name:sha(p)', '["output_sha256"]={p.name:sha(p)')),
        ("wrong_actual_digest",current.replace('["outputs"]={p.name:sha(p)', '["outputs"]={p.name:"0"*64')),
        ("wrong_actual_filename",current.replace('["outputs"]={p.name:sha(p)', '["outputs"]={p.name+"_wrong":sha(p)')),
    ]:
        assert bad!=current
        try:actual_output_metadata(bad)
        except (AssertionError,KeyError) as error:
            if label=="wrong_actual_filename":assert type(error) is KeyError and error.args==("fixture.gds",)
            else:assert type(error) is AssertionError
            output_refusals.append({"case":label,"error":repr(error)})
        else:raise AssertionError("Accepted output metadata fault "+label)
    assert len(output_refusals)==3
    runtime=json.loads((ROOT/"docs/evidence/cdr-v59-tail-native-runtime-source-20261026.json").read_text())
    assert len(runtime["relative_runtime_sha256"])==88
    assert runtime["relative_runtime_sha256"]["sg13g2_pycell_lib/ihp/via_stack_code.py"]=="185f6d3bea6ef9a4960817d189e099057242e1cca73f6ab31c08298c2d64cc61"
    assert runtime["relative_runtime_sha256"]["sg13g2_pycell_lib/sg13g2_tech.json"]=="dce023dcf8dca1a7d875b6f71b5ce651b42f2dc3e9a21abb6de3997262273142"
    summary=json.loads((ROOT/"docs/evidence/cdr-v59-tail-current-font-physical-summary-20261026.json").read_text())
    selected={k[len("analysis-capsule/"):]:v for k,v in summary["outputs"].items() if k.startswith("analysis-capsule/")}
    assert len(summary["outputs"])==705 and len(selected)==349
    assert selected["parent/layout/"+plan.TOP+".gds"]==h["current_candidate_GDS_sha256"]
    # Run the actual import statement in an isolated fresh interpreter. No pya,
    # geometry input or hosted engine is imported by the native module at import.
    with tempfile.TemporaryDirectory(prefix="cdr-tail-import-") as tmp:
        root=Path(tmp)
        for name in ("cdr_v59_tail_access_plan.py","generate_cdr_v59_tail_access_wire.py"):
            b=(ROOT/"scripts"/name).read_bytes()
            (root/name).write_bytes(b)
            assert digest(root/name)==hashlib.sha256(b).hexdigest()
        code="import sys;sys.path.insert(0,sys.argv[1]);import generate_cdr_v59_tail_access_wire;print('TAIL_NATIVE_SOURCE_IMPORT_ONLY')"
        good=subprocess.run([sys.executable,"-I","-B","-c",code,str(root)],capture_output=True,text=True,timeout=30)
        assert good.returncode==0 and good.stdout=="TAIL_NATIVE_SOURCE_IMPORT_ONLY\n" and good.stderr=="",vars(good)
        (root/"cdr_v59_tail_access_plan.py").unlink()
        bad=subprocess.run([sys.executable,"-I","-B","-c",code,str(root)],capture_output=True,text=True,timeout=30)
        assert bad.returncode==1 and bad.stdout==""
        assert bad.stderr.splitlines()[-1]=="ModuleNotFoundError: No module named 'cdr_v59_tail_access_plan'"
    return {"status":"PASS_TAIL_ACCESS_SOURCE_CONTROLS_ONLY","metadata_positive":1,
      "metadata_faults_rejected":19,"actual_import_positive":1,"actual_snapshot_call_signatures_positive":1,
      "actual_snapshot_call_lines":call_lines,"actual_first_draft_signature_refusal":signature_failure,"actual_missing_dependency_rejected":1,
      "actual_output_assignment_probe_positives":output_rows,"output_metadata_faults":output_refusals,
      "input_relocation_controls":input_relocation,
      "protected_files_verified":len(method["protected_sha256"]),"cases":cases,
      "native_geometry_controls_executed":False,"physical_accepted":False,"electrical_accepted":False}

def main():
    print(json.dumps(controls(),sort_keys=True))
if __name__=="__main__":main()
