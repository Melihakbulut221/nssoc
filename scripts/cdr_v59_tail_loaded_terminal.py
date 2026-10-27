#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Orchestration-only finalization for the unchanged loaded numerical worker."""
import json,os,sys,traceback

def error_record(error):
    return {"type":type(error).__name__,"error":repr(error),
      "traceback":"".join(traceback.format_exception(type(error),error,error.__traceback__))}

def inventory(out,admission):
    result={}
    for path in out.rglob("*"):
        admission.require(not path.is_symlink(),"Symlink in loaded output inventory")
        if path.is_dir():continue
        admission.require(path.is_file(),"Nonregular loaded output")
        if path!=out/"result.json":result[str(path.relative_to(out))]=admission.sha(path)
    return result

def preserve_atomic_fragment(out,result,admission,stage):
    temporary=out/"result.json.tmp"
    if not(temporary.exists()or temporary.is_symlink()):return
    admission.require(not temporary.is_symlink()and temporary.is_file(),"Nonregular atomic result fragment")
    original_hash=admission.sha(temporary);original_size=temporary.stat().st_size
    directory=out/"terminal-save-fragments"
    admission.require(not directory.is_symlink(),"Symlink atomic fragment directory")
    directory.mkdir(exist_ok=True)
    admission.require(directory.is_dir(),"Non-directory atomic fragment destination")
    serial=0
    while True:
        retained=directory/("result.json.tmp.%06d"%serial)
        try:
            # Exclusive hard-link creation never overwrites a previous fragment.
            # Removing the old name then prevents the fixed writer from changing it.
            os.link(temporary,retained,follow_symlinks=False)
            break
        except FileExistsError:serial+=1
    record={"stage":stage,"source":"result.json.tmp","retained":str(retained.relative_to(out)),
      "bytes":original_size,"sha256":original_hash,"source_name_removed":False}
    result.setdefault("retained_atomic_fragments",[]).append(record)
    admission.require(admission.sha(temporary)==admission.sha(retained)==original_hash
      and temporary.stat().st_size==retained.stat().st_size==original_size,"Changed atomic result fragment")
    temporary.unlink();record["source_name_removed"]=True

def finalize(out,result,save,admission):
    primary=sys.exception();errors=[];actions=[]
    result["status_before_terminal"]=result["status"]
    result["terminal_finalization_complete"]=False
    result["active_primary_exception_before_terminal"]=None if primary is None else error_record(primary)
    def attempt(label,call):
        try:
            call();actions.append({"action":label,"completed":True})
        except BaseException as error:
            errors.append((label,error));actions.append({"action":label,"completed":False,**error_record(error)})
    def source_guard():
        admission.methods()
    def saved_guard():
        bundle=out/"current-mim-bundle"
        if bundle.exists()or bundle.is_symlink():
            result["current_saved_input_integrity"]=admission.verify_restored(out)
    def outputs():
        result["terminal_inventory_complete"]=False
        result["outputs"]=inventory(out,admission)
        result["terminal_inventory_complete"]=True
    def sync_errors():
        result["terminal_actions"]=actions
        result["terminal_errors"]=[{"action":label,**error_record(error)}for label,error in errors]
    # Every guard/inventory executes even if an earlier one fails. Never retain
    # arbitrary collaborator returns as JSON evidence.
    attempt("protected_sources",source_guard)
    attempt("complete_saved_inputs",saved_guard)
    attempt("preserve_preexisting_atomic_fragment",lambda:preserve_atomic_fragment(out,result,admission,"before_final_save"))
    attempt("complete_output_inventory",outputs)
    sync_errors()
    if errors:result["status"]="FAIL_TAIL_LOADED_TERMINAL_INTEGRITY"
    result["terminal_finalization_complete"]=not errors
    result["terminal_save_attempted"]=False
    try:
        # A failed fragment preservation must never permit the fixed writer to
        # overwrite the original bytes. The full report is emitted below instead.
        admission.require(not((out/"result.json.tmp").exists()or(out/"result.json.tmp").is_symlink()),
          "Unretained atomic result fragment prevents overwrite")
        result["terminal_save_attempted"]=True
        save()
    except BaseException as error:
        errors.append(("save_result",error))
        result["status"]="FAIL_TAIL_LOADED_TERMINAL_SAVE"
        result["terminal_finalization_complete"]=False
        attempt("preserve_failed_save_fragment",lambda:preserve_atomic_fragment(out,result,admission,"after_failed_save"))
        attempt("refresh_failed_save_inventory",outputs)
        sync_errors()
        try:
            print(json.dumps({"unsaved_terminal_loaded_result":result},sort_keys=True,allow_nan=False),flush=True)
        except BaseException as emission_error:
            # Preserve the primary exception even if both persistence channels
            # fail. A primitive emergency record makes that loss explicit.
            emergency={"status":"FAIL_UNSAVED_TERMINAL_REPORT_EMISSION","result_repr":repr(result),
              "save_error":error_record(error),"emission_error":error_record(emission_error)}
            try:print(json.dumps(emergency,sort_keys=True),flush=True)
            except BaseException:pass
    if errors and primary is None:raise errors[0][1]
    return {"completed":not errors,"primary_exception_preserved":primary is not None}
