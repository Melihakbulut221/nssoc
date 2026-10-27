#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Orchestration-only finalization for the unchanged loaded numerical worker."""
import json,sys,traceback

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
        result["outputs"]=inventory(out,admission)
    # Every guard/inventory executes even if an earlier one fails. Never retain
    # arbitrary collaborator returns as JSON evidence.
    attempt("protected_sources",source_guard)
    attempt("complete_saved_inputs",saved_guard)
    attempt("complete_output_inventory",outputs)
    result["terminal_actions"]=actions
    result["terminal_errors"]=[{"action":label,**error_record(error)}for label,error in errors]
    if errors:result["status"]="FAIL_TAIL_LOADED_TERMINAL_INTEGRITY"
    result["terminal_finalization_complete"]=not errors
    try:save()
    except BaseException as error:
        errors.append(("save_result",error))
        result["status"]="FAIL_TAIL_LOADED_TERMINAL_SAVE"
        result["terminal_finalization_complete"]=False
        result["terminal_errors"].append({"action":"save_result",**error_record(error)})
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
