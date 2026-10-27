#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reuse exact qualified ownership and launcher controls with the current source gate."""
import argparse
import json
from pathlib import Path
import tempfile
import types
from unittest.mock import patch
import cdr_v59_tail_fresh_rc_admission as s
import cdr_v59_tail_access_runtime as runtime
import cloud_cdr_v59_tail_fresh_rc as driver

FROZEN="scripts/check_cdr_v59_tail_access_physical.py"


def loader_controls():
    """Call the actual five frozen loaders against exact copied source bytes; launch nothing."""
    m=s.methods()
    paths=(runtime.SUPERVISOR,runtime.SAMPLER,runtime.PROBE,runtime.WRITER,driver.PIPELINE_SOURCE)
    originals={path:(s.ROOT/path).read_bytes()for path in paths}
    assert all(s.sha(s.ROOT/path)==m["protected_sha256"][path]for path in paths)
    positives=[];refusals=[]
    for changed,kind in [(None,None)]+[(path,kind)for path in paths for kind in ("missing","tampered")]:
        with tempfile.TemporaryDirectory(prefix="cdr-tail-frozen-loaders-")as folder:
            root=Path(folder)
            for path,body in originals.items():
                target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
            if kind=="missing":(root/changed).unlink()
            elif kind=="tampered":(root/changed).write_bytes(originals[changed]+b"\n# changed frozen source\n")
            def load():
                # Metadata transport is synthetic; every actual loader reads and hashes its own copied file.
                gate=lambda:m
                if changed in (None,runtime.SUPERVISOR,runtime.SAMPLER):
                    owned=runtime.supervisor(root,root/"out",root/"trace",gate,m["protected_sha256"][runtime.SAMPLER])
                    assert owned.memory_snapshot.bounded_fresh_rss_adapter is True
                if changed in (None,runtime.PROBE,runtime.WRITER):
                    probe=runtime.launcher(root,gate,m["protected_sha256"][runtime.PROBE])
                    assert callable(probe.probe)and callable(probe.admission.write)
                if changed in (None,driver.PIPELINE_SOURCE):
                    with patch.object(driver,"ROOT",root):
                        validator=driver.pipeline_validator()
                        assert validator.__name__=="validate_pipeline"
            try:load()
            except AssertionError as error:
                assert changed is not None,(kind,repr(error))
                if changed==driver.PIPELINE_SOURCE:
                    expected="Missing regular protected file"if kind=="missing"else"Frozen MIM pipeline validator changed"
                    assert error.args==(expected,),(changed,kind,repr(error))
                    frame=driver.pipeline_validator.__code__
                else:
                    assert error.args==(()if kind=="missing"else(changed,)),(changed,kind,repr(error))
                    frame=runtime.raw.__code__
                tb=error.__traceback__;frames=[]
                while tb is not None:frames.append(tb.tb_frame.f_code);tb=tb.tb_next
                assert frame in frames,(changed,kind,repr(error))
                refusals.append({"path":changed,"mutation":kind,"error":repr(error),"actual_loader_frame_verified":True})
            else:
                assert changed is None,("Accepted changed frozen loader",changed,kind)
                positives.append({"five_exact_sources_loaded":list(paths),"native_or_subprocess_launched":False})
    assert len(positives)==1 and len(refusals)==10
    return {"positive":positives,"refusals":refusals,"scope":"Actual copied-source loader calls only; numerical/native functions are not called."}

def controls():
    scope={"json":json,"Path":Path,"tempfile":tempfile,"gate":s.methods,
      "c":types.SimpleNamespace(runtime=runtime,ROOT=s.ROOT,sha=s.sha)}
    selected=s.frozen.load_definitions(s.ROOT/FROZEN,["runtime_controls"],scope)
    result=selected["runtime_controls"]()
    assert result["status"]=="PASS_QUALIFIED_RUNTIME_AND_WRITER_DEPENDENCY_CONTROLS"
    assert len(result["supervisor"]["controls"])==13
    assert len(result["all11_launcher_results_saved"])==11
    assert result["corrected_exit127_saved"]["accepted"]is False
    assert result["actual_appimage_executed"]is result["native_executed"]is False
    result["frozen_loader_controls"]=loader_controls()
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);args=p.parse_args()
    assert s.methods()["source_controls_authorized"]is True
    result={"status":"RUNNING_QUALIFIED_RUNTIME_CONTROLS"};s.write(args.out,result)
    try:result=controls()
    except BaseException as error:result.update(status="FAIL_QUALIFIED_RUNTIME_CONTROLS",error=repr(error));raise
    finally:s.write(args.out,result)

if __name__=="__main__":main()
