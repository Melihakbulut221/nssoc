#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reuse the exact qualified 13 ownership and 11 launcher persistence controls."""
import json
from pathlib import Path
import tempfile
import types
import cdr_v59_tail_saved_identity as s
import cdr_v59_tail_access_runtime as runtime

FROZEN="scripts/check_cdr_v59_tail_access_physical.py"

def controls():
    scope={"json":json,"Path":Path,"tempfile":tempfile,"gate":s.methods,
      "c":types.SimpleNamespace(runtime=runtime,ROOT=s.ROOT,sha=s.sha)}
    selected=s.load_definitions(s.ROOT/FROZEN,["runtime_controls"],scope)
    result=selected["runtime_controls"]()
    assert result["status"]=="PASS_QUALIFIED_RUNTIME_AND_WRITER_DEPENDENCY_CONTROLS"
    assert len(result["supervisor"]["controls"])==13
    assert len(result["all11_launcher_results_saved"])==11
    assert result["corrected_exit127_saved"]["accepted"] is False
    assert result["actual_appimage_executed"] is result["native_executed"] is False
    return result

def main():
    assert s.methods()["source_controls_authorized"] is True
    out=s.ROOT/"hw/soc/out/cdr-v59-tail-saved-identity-runtime-controls";out.mkdir(parents=True,exist_ok=False)
    result={"status":"RUNNING_QUALIFIED_RUNTIME_CONTROLS"}
    s.write(out/"result.json",result)
    try:result=controls()
    except BaseException as error:
        result.update(status="FAIL_QUALIFIED_RUNTIME_CONTROLS",error=repr(error));raise
    finally:s.write(out/"result.json",result);print(json.dumps(result,indent=2))

if __name__=="__main__":main()
