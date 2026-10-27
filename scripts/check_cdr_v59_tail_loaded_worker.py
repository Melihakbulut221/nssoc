#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact worker derivation and actual pre-restoration/finally controls; no simulation."""
import argparse,ast,contextlib,copy,io,json,os,sys,tempfile,traceback,types
from pathlib import Path
from unittest import mock
import cdr_v59_tail_loaded_admission as a
import cdr_v59_tail_loaded_terminal as terminal
AUDIT="docs/evidence/cdr-v59-tail-loaded-worker-derivation-20261028.json"
WORKER="scripts/cloud_cdr_v59_tail_loaded.py"
FROZEN_TERMINAL="docs/evidence/cdr-v59-tail-loaded-terminal-before-atomic-fragment-fix-20261028.py"

def derivation():
    audit=json.loads(a.regular(a.ROOT,AUDIT).read_bytes())
    old=a.regular(a.ROOT,audit["baseline"]["path"]).read_bytes();new=a.regular(a.ROOT,WORKER).read_bytes()
    assert a.sha(a.ROOT/audit["baseline"]["path"])==audit["baseline"]["sha256"]
    assert a.sha(a.ROOT/WORKER)==audit["generated"]["sha256"]
    text=old.decode()
    for row in audit["exact_reversible_edits"]:
        assert text.count(row["before"])==1
        text=text.replace(row["before"],row["after"])
    assert text.encode()==new
    for row in reversed(audit["exact_reversible_edits"]):
        assert text.count(row["after"])==1
        text=text.replace(row["after"],row["before"])
    assert text.encode()==old
    coordinate=audit["frozen_numerical_block_coordinate_source"]
    baseline=a.regular(a.ROOT,coordinate["path"]).read_bytes()
    assert a.sha(a.ROOT/coordinate["path"])==coordinate["sha256"]
    for row in audit["unchanged_numerical_blocks"]:
        block=b"".join(baseline.splitlines(keepends=True)[row["start_line"]-1:row["end_line"]])
        import hashlib
        assert len(block)==row["bytes"]and hashlib.sha256(block).hexdigest()==row["sha256"]
        assert old.count(block)==new.count(block)==1
    functions=lambda raw:{n.name:ast.dump(n)for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
    before,after=functions(old),functions(new)
    assert before.keys()==after.keys()and[k for k in before if before[k]!=after[k]]==["main"]
    return {"edits":6,"numerical_blocks":6,"exact_reverse":True,"non_main_functions_identical":True}

def main_entry_controls():
    """Run both exact complete mains with explicit stubs stopping before restore."""
    audit=json.loads(a.regular(a.ROOT,AUDIT).read_bytes())
    old=a.regular(a.ROOT,audit["baseline"]["path"]).read_bytes();new=a.regular(a.ROOT,WORKER).read_bytes()
    results=[]
    for label,raw in (("original",old),("corrected",new)):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);(root/"scripts").mkdir();(root/"docs/evidence").mkdir(parents=True)
            names=["scripts/cloud_cdr_pd_vi.py","scripts/cloud_tx_stream.py","scripts/cloud_cdr_xor.py",
              "scripts/run_cloud_tx_mux4.py","docs/evidence/cdr-via-rich-stream-transport-pass-20261019.json"]
            pins={}
            for name in names:
                data=a.regular(a.ROOT,name).read_bytes();(root/name).write_bytes(data);pins[name]=a.sha(root/name)
            method_path="scripts/cdr-v59-loaded-methods.json"if label=="original"else a.METHOD
            (root/method_path).write_text(json.dumps({"protected"if label=="original"else"protected_sha256":pins}))
            prefix="cloud-cdr-v59-loaded-"if label=="original"else"cloud-cdr-v59-tail-loaded-"
            out=root/(prefix+"nominal_early");calls=[]
            primary=RuntimeError("EXACT_PRE_RESTORE_BODY_FAILURE")
            secondary=OSError("EXACT_COMPLETE_INPUT_INTEGRITY_FAILURE")
            def restore(path,prepare):
                assert path==out and prepare is True
                calls.append("restore_boundary");(path/"current-mim-bundle").mkdir()
                (path/"partial.json").write_bytes(b'{"incomplete":')
                raise primary
            def verify(path):
                assert path==out
                calls.append("saved_input_guard");raise secondary
            def methods():
                calls.append("source_guard");return {"protected_sha256":pins}
            admission=types.SimpleNamespace(SUMMARY=a.SUMMARY,STAGE=a.STAGE,restore=restore,
              verify_restored=verify,methods=methods,require=a.require,sha=a.sha,write=a.write)
            def prbs(seed):
                assert seed==0x7f
                return [0,1]*128
            scope=dict(argparse=argparse,json=json,os=os,Path=Path,traceback=traceback,ROOT=root,
              UI=125e-12,START=2e-9,STOP=2e-9+258*125e-12,STEP=.3125e-12,
              CASES=list(a.CASES),sha=a.sha,reports=types.SimpleNamespace(),
              pump=types.SimpleNamespace(CORNERS={"nominal":{"scale":1.0}}),
              primitive=types.SimpleNamespace(prbs=prbs),
              legacy=types.SimpleNamespace(__file__=str(root/"scripts/cloud_cdr_pd_vi.py")),
              stream=types.SimpleNamespace(__file__=str(root/"scripts/cloud_tx_stream.py")),
              readback_controls=lambda:{"explicit_entry_stub":True},
              current_inputs=admission,loaded_terminal=terminal)
            nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name=="main"];assert len(nodes)==1
            exec(compile(ast.Module(body=nodes,type_ignores=[]),"actual-"+label+"-loaded-main","exec"),scope)
            captured=None
            with mock.patch.object(sys,"argv",["entry","--case","nominal_early","--prepare-only"]),contextlib.redirect_stdout(io.StringIO()):
                try:scope["main"]()
                except BaseException as error:captured=error
            saved=json.loads((out/"result.json").read_bytes())
            assert saved["error"]==repr(primary)and saved["outputs"]["partial.json"]==a.sha(out/"partial.json")
            assert not(out/"native").exists()and (out/"partial.json").read_bytes()==b'{"incomplete":'
            if label=="original":
                assert captured is secondary and saved["status"]=="FAIL_CURRENT_SAVED_INPUT_INTEGRITY"
                assert calls==["restore_boundary","saved_input_guard"]
            else:
                assert captured is primary and saved["status"]=="FAIL_TAIL_LOADED_TERMINAL_INTEGRITY"
                assert calls==["restore_boundary","source_guard","saved_input_guard"]
                assert saved["status_before_terminal"]=="FAIL_OR_ERROR"
                assert [x["action"]for x in saved["terminal_actions"]]==["protected_sources","complete_saved_inputs","preserve_preexisting_atomic_fragment","complete_output_inventory"]
                assert saved["terminal_errors"][0]["error"]==repr(secondary)
                assert saved["active_primary_exception_before_terminal"]["error"]==repr(primary)
            results.append({"mode":label,"saved_status":saved["status"],"raised_exact_object":"secondary"if captured is secondary else"primary",
              "calls":calls,"partial_bytes_preserved":True,"full_actual_main_compiled":True})
    return {"old_primary_masking_reproduced":True,"corrected_primary_identity_preserved":True,
      "cases":results,"restoration_and_native_never_reached":True,"entry_collaborators_explicitly_synthetic":True}

def terminal_controls():
    cases=[]
    for mode in ("complete","saved_input_failure","source_failure","inventory_failure","save_failure","body_and_save_failure","body_and_integrity_failure"):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td);(out/"current-mim-bundle").mkdir();(out/".partial").write_bytes(b"raw\x00evidence")
            result={"status":"PASS_SYNTHETIC_NUMERICAL_BODY","accepted":False}
            a.write(out/"result.json",{"status":"RUNNING_SYNTHETIC"})
            primary=RuntimeError("EXACT_ACTIVE_PRIMARY");failure=OSError("EXACT_"+mode);calls=[]
            def methods():
                calls.append("sources")
                if mode=="source_failure":raise failure
            def verify(path):
                assert path==out;calls.append("inputs")
                if mode in ("saved_input_failure","body_and_integrity_failure"):raise failure
                return {"synthetic_regular_files_only":True}
            def save():
                calls.append("save")
                if mode in ("save_failure","body_and_save_failure"):raise failure
                a.write(out/"result.json",result)
            admission=types.SimpleNamespace(methods=methods,verify_restored=verify,require=a.require,sha=a.sha)
            real_inventory=terminal.inventory
            def inventory(path,source):
                calls.append("inventory")
                if mode=="inventory_failure":raise failure
                return real_inventory(path,source)
            caught=None;output=io.StringIO()
            with mock.patch.object(terminal,"inventory",side_effect=inventory),contextlib.redirect_stdout(output):
                try:
                    if mode.startswith("body_and"):
                        try:raise primary
                        finally:terminal.finalize(out,result,save,admission)
                    else:terminal.finalize(out,result,save,admission)
                except BaseException as error:caught=error
            assert calls==(["sources","inputs","inventory","save","inventory"]if mode in ("save_failure","body_and_save_failure")else["sources","inputs","inventory","save"]),(mode,calls)
            assert caught is (primary if mode.startswith("body_and")else None if mode=="complete"else failure)
            assert (out/".partial").read_bytes()==b"raw\x00evidence"
            if mode in ("save_failure","body_and_save_failure"):
                emitted=json.loads(output.getvalue())["unsaved_terminal_loaded_result"]
                assert emitted==result and emitted["status"]=="FAIL_TAIL_LOADED_TERMINAL_SAVE"
                assert emitted["outputs"][".partial"]==a.sha(out/".partial")
                assert len(emitted["terminal_actions"])==6 and emitted["terminal_errors"][-1]["error"]==repr(failure)
                assert json.loads((out/"result.json").read_bytes())=={"status":"RUNNING_SYNTHETIC"}
            else:
                saved=json.loads((out/"result.json").read_bytes());assert saved==result
                assert saved["terminal_finalization_complete"]is(mode=="complete")
                assert saved["status"]==("PASS_SYNTHETIC_NUMERICAL_BODY"if mode=="complete"else"FAIL_TAIL_LOADED_TERMINAL_INTEGRITY")
                if mode!="inventory_failure":assert saved["outputs"][".partial"]==a.sha(out/".partial")
            cases.append({"mode":mode,"all_four_actions_attempted":True,"exception_identity_checked":True,
              "complete_unsaved_JSON_preserved":mode in ("save_failure","body_and_save_failure")})
    return {"cases":cases,"positive":1,"failure_paths":6,"actual_finalizer_called":True}

def atomic_fragment_controls():
    """Exercise the actual fixed-name writer and real terminal inventories."""
    frozen=a.regular(a.ROOT,FROZEN_TERMINAL).read_bytes()
    assert a.sha(a.ROOT/FROZEN_TERMINAL)==a.methods()["protected_sha256"][FROZEN_TERMINAL]
    definitions=[n for n in ast.parse(frozen).body if isinstance(n,ast.FunctionDef)]
    scope={"json":json,"sys":sys,"traceback":traceback}
    exec(compile(ast.Module(body=definitions,type_ignores=[]),"frozen-pre-fragment-terminal","exec"),scope)
    cases=[]
    for mode in ("frozen_preexisting","frozen_replace_failure","preserved_preexisting","replace_failure","body_and_replace_failure",
                 "replace_and_retention_failure","replace_and_inventory_failure","preexisting_retention_failure"):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td);(out/"available.raw").write_bytes(b"original-evidence")
            a.write(out/"result.json",{"status":"RUNNING_SYNTHETIC"})
            original=b'{"partial_original":\x00'
            if mode in ("frozen_preexisting","preserved_preexisting","preexisting_retention_failure"):
                (out/"result.json.tmp").write_bytes(original)
            if mode=="preserved_preexisting":
                folder=out/"terminal-save-fragments";folder.mkdir()
                (folder/"result.json.tmp.000000").write_bytes(b"prior-unique-fragment")
            result={"status":"PASS_SYNTHETIC_NUMERICAL_BODY","accepted":False}
            primary=RuntimeError("EXACT_ATOMIC_BODY_FAILURE")
            save_error=OSError("EXACT_ATOMIC_REPLACE_FAILURE")
            retention_error=OSError("EXACT_ATOMIC_LINK_FAILURE")
            inventory_error=OSError("EXACT_ATOMIC_REFRESH_FAILURE")
            calls=[];write_payload=[];replace_calls=[];inventory_calls=[];output=io.StringIO()
            admission=types.SimpleNamespace(methods=lambda:None,verify_restored=lambda path:{},
              require=a.require,sha=a.sha)
            real_replace=Path.replace;real_link=os.link;real_inventory=terminal.inventory
            def replace(path,target):
                assert path==out/"result.json.tmp"and Path(target)==out/"result.json"
                replace_calls.append(str(path))
                if mode in ("frozen_replace_failure","replace_failure","body_and_replace_failure","replace_and_retention_failure","replace_and_inventory_failure"):
                    raise save_error
                return real_replace(path,target)
            def link(source,target,**kwargs):
                if mode in ("replace_and_retention_failure","preexisting_retention_failure"):raise retention_error
                return real_link(source,target,**kwargs)
            def inventory(path,source):
                inventory_calls.append(str(path))
                if mode=="replace_and_inventory_failure"and len(inventory_calls)==2:raise inventory_error
                return real_inventory(path,source)
            def save():
                calls.append("save")
                write_payload.append((json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n").encode())
                a.write(out/"result.json",result)
            selected=scope["finalize"]if mode.startswith("frozen_")else terminal.finalize
            caught=None
            with mock.patch.object(Path,"replace",replace),mock.patch.object(terminal.os,"link",side_effect=link),\
                 mock.patch.object(terminal,"inventory",side_effect=inventory),contextlib.redirect_stdout(output):
                try:
                    if mode=="body_and_replace_failure":
                        try:raise primary
                        finally:selected(out,result,save,admission)
                    else:selected(out,result,save,admission)
                except BaseException as error:caught=error
            actual=real_inventory(out,admission)
            if mode=="frozen_preexisting":
                assert caught is None and calls==["save"]and not(out/"result.json.tmp").exists()
                saved=json.loads((out/"result.json").read_bytes())
                import hashlib
                assert saved["outputs"]["result.json.tmp"]==hashlib.sha256(original).hexdigest()
                assert saved["outputs"]!=actual and all(p.read_bytes()!=original for p in out.rglob("*")if p.is_file())
                cases.append({"mode":mode,"exact_old_fragment_loss_and_stale_inventory_reproduced":True})
                continue
            if mode=="frozen_replace_failure":
                assert caught is save_error and calls==["save"]and len(replace_calls)==1
                emitted=json.loads(output.getvalue())["unsaved_terminal_loaded_result"]
                assert emitted["outputs"]!=actual and "result.json.tmp"not in emitted["outputs"]
                assert (out/"result.json.tmp").read_bytes()==write_payload[0]
                assert json.loads((out/"result.json").read_bytes())=={"status":"RUNNING_SYNTHETIC"}
                cases.append({"mode":mode,"exact_old_failed_save_missing_fragment_inventory_reproduced":True})
                continue
            if mode=="preserved_preexisting":
                assert caught is None and calls==["save"]
                saved=json.loads((out/"result.json").read_bytes())
                row=saved["retained_atomic_fragments"][0]
                assert row["stage"]=="before_final_save"and row["source_name_removed"]is True
                assert row["retained"]=="terminal-save-fragments/result.json.tmp.000001"
                assert (out/row["retained"]).read_bytes()==original
                assert (out/"terminal-save-fragments/result.json.tmp.000000").read_bytes()==b"prior-unique-fragment"
                assert saved["outputs"]==actual and saved["terminal_inventory_complete"]is True
            else:
                emitted=json.loads(output.getvalue())["unsaved_terminal_loaded_result"];assert emitted==result
                assert emitted["status"]=="FAIL_TAIL_LOADED_TERMINAL_SAVE"
                assert json.loads((out/"result.json").read_bytes())=={"status":"RUNNING_SYNTHETIC"}
                expected=primary if mode=="body_and_replace_failure"else retention_error if mode=="preexisting_retention_failure"else save_error
                assert caught is expected,(mode,caught)
                if mode=="preexisting_retention_failure":
                    assert calls==[]and replace_calls==[]and emitted["terminal_save_attempted"]is False
                    assert (out/"result.json.tmp").read_bytes()==original
                    assert [x["action"]for x in emitted["terminal_errors"]]==[
                      "preserve_preexisting_atomic_fragment","save_result","preserve_failed_save_fragment"]
                    assert emitted["terminal_errors"][0]["error"]==repr(retention_error)
                else:
                    assert calls==["save"]and len(replace_calls)==1 and emitted["terminal_save_attempted"]is True
                    assert emitted["terminal_errors"][0]["error"]==repr(save_error)
                    if mode=="replace_and_retention_failure":
                        assert (out/"result.json.tmp").read_bytes()==write_payload[0]
                        assert emitted["terminal_errors"][1]["error"]==repr(retention_error)
                    else:
                        row=emitted["retained_atomic_fragments"][0]
                        assert row["stage"]=="after_failed_save"and row["source_name_removed"]is True
                        assert (out/row["retained"]).read_bytes()==write_payload[0]
                        assert a.sha(out/row["retained"])==row["sha256"]and len(write_payload[0])==row["bytes"]
                        assert not(out/"result.json.tmp").exists()
                if mode=="replace_and_inventory_failure":
                    assert emitted["terminal_inventory_complete"]is False
                    assert emitted["terminal_errors"][-1]["error"]==repr(inventory_error)
                else:assert emitted["outputs"]==actual and emitted["terminal_inventory_complete"]is True
                assert [x["action"]for x in emitted["terminal_actions"]][-2:]==[
                  "preserve_failed_save_fragment","refresh_failed_save_inventory"]
            cases.append({"mode":mode,"actual_atomic_writer_used":bool(calls),
              "complete_available_inventory_checked":mode!="replace_and_inventory_failure",
              "original_exception_identity_preserved":True,"fragment_bytes_retained":True})
    return {"cases":cases,"old_regressions":2,"corrected_cases":6,"actual_atomic_writer_replace_boundary":True}

def controls():
    assert a.methods()["source_controls_authorized"]is True
    return {"status":"PASS_EXACT_NUMERICAL_WORKER_DERIVATION_AND_TERMINAL_SOURCE_CONTROLS",
      "derivation":derivation(),"actual_main":main_entry_controls(),"terminal":terminal_controls(),
      "atomic_fragments":atomic_fragment_controls(),
      "original_numerical_functions_executed":False,"archive_accessed":False,"simulator_executed":False,
      "full_outer_and_import_readiness":False}

def main():
    try:result=controls()
    except BaseException as error:
        result={"status":"FAIL_LOADED_WORKER_SOURCE_CONTROLS","error":repr(error),"traceback":traceback.format_exc()}
        print(json.dumps(result,indent=2));raise
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
