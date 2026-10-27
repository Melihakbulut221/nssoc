#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual qualified ownership controls and exact loaded budgets; no numerical worker."""
import argparse,json,sys,tempfile,traceback
from pathlib import Path
from unittest.mock import patch
import cdr_v59_tail_loaded_admission as a
import cdr_v59_tail_loaded_result as result_gate
import cdr_v59_tail_access_runtime as runtime

def loader_controls():
    m=a.methods()
    paths=(runtime.SUPERVISOR,runtime.SAMPLER,result_gate.ORIGINAL)
    originals={name:a.regular(a.ROOT,name).read_bytes()for name in paths}
    assert all(a.sha(a.ROOT/name)==m["protected_sha256"][name]for name in paths)
    positive=[];refused=[]
    for changed,kind in [(None,None)]+[(name,kind)for name in paths for kind in ("missing","tampered")]:
        with tempfile.TemporaryDirectory(prefix="loaded-exact-loaders-")as folder:
            root=Path(folder)
            for name,value in originals.items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
            if kind=="missing":(root/changed).unlink()
            elif kind=="tampered":(root/changed).write_bytes(originals[changed]+b"\n# changed protected loader\n")
            try:
                if changed in (None,runtime.SUPERVISOR,runtime.SAMPLER):
                    owned=runtime.supervisor(root,root/"out",root/"trace",lambda:m,m["protected_sha256"][runtime.SAMPLER])
                    assert owned.memory_snapshot.bounded_fresh_rss_adapter is True
                if changed in (None,result_gate.ORIGINAL):
                    with patch.object(a,"ROOT",root):
                        validator,proof=result_gate.validator()
                        assert validator.__name__=="validate_result"
                        assert proof["original_source_sha256"]==result_gate.ORIGINAL_SHA
            except AssertionError as error:
                assert changed is not None
                if changed==result_gate.ORIGINAL:
                    expected=("Missing protected regular file"if kind=="missing"else"Original loaded stage changed",)
                    assert error.args==expected,(changed,kind,error.args)
                    frame=result_gate.validator.__code__
                else:
                    assert error.args==(()if kind=="missing"else(changed,)),(changed,kind,error.args)
                    frame=runtime.raw.__code__
                tb=error.__traceback__;frames=[]
                while tb is not None:frames.append(tb.tb_frame.f_code);tb=tb.tb_next
                assert frame in frames
                refused.append({"source":changed,"mutation":kind,"reason":repr(error),"actual_loader_frame":True})
            else:
                assert changed is None,("Accepted loader mutation",changed,kind)
                positive.append({"exact_sources":list(paths),"subprocess_or_numerical_function_called":False})
    assert len(positive)==1 and len(refused)==6
    return {"positive":positive,"refused":refused}

def controls():
    m=a.methods();assert m["source_controls_authorized"]is True
    with tempfile.TemporaryDirectory(prefix="loaded-owned-controls-")as folder:
        root=Path(folder)
        owned=runtime.supervisor(a.ROOT,root/"out",root/"trace",a.methods,m["protected_sha256"][runtime.SAMPLER])
        owned.controls()
        inherited=json.loads((owned.TRACE/"controls.json").read_bytes())
        assert inherited["status"]=="PASS_RECORD_TELEMETRY_SOURCE_AND_SUPERVISION_CONTROLS_NO_RTL"
        assert len(inherited["controls"])==13 and all(value is True for value in inherited["controls"].values())
        budgets=[]
        for mode,seconds in (("preparation",1200),("loaded_case",7200)):
            label="loaded-budget-"+mode
            argv=[sys.executable,"-c","import sys;print('"+mode+"');print('exact-stderr',file=sys.stderr)"]
            result=owned.supervised(argv,label,seconds=seconds,cwd=owned.TRACE)
            record=json.loads((owned.TRACE/(label+".command.json")).read_bytes())
            assert result.returncode==record["returncode"]==0
            assert result.stdout==mode+"\n"and result.stderr=="exact-stderr\n"
            assert record["argv"]==argv and record["supervision_failure"]is None
            assert record["process_group_cleanup"]["remaining_live"]==[]and owned.ACTIVE is None
            assert record["minimum_available_kib"]==2097152 and record["maximum_group_rss_kib"]==10485760
            for stream in ("stdout","stderr"):
                path=owned.TRACE/(label+"."+stream)
                assert path.stat().st_size==record[stream+"_bytes"]and a.sha(path)==record[stream+"_sha256"]
            starts=[json.loads(line)for line in(owned.TRACE/"events.jsonl").read_text().splitlines()
              if json.loads(line).get("event")=="command_start"and json.loads(line).get("label")==label]
            assert len(starts)==1 and starts[0]["timeout_seconds"]==seconds
            assert starts[0]["output_limit_per_stream_bytes"]==16777216
            budgets.append({"mode":mode,"seconds":seconds,"actual_command":record,"actual_start_event":starts[0]})
        assert len(budgets)==2
    return {"status":"PASS_LOADED_QUALIFIED_SUPERVISOR_AND_EXACT_BUDGET_CONTROLS",
      "inherited":inherited,"loaded_budgets":budgets,"frozen_loaders":loader_controls(),
      "actual_short_python_children_only":True,"numerical_worker_executed":False,"simulator_executed":False,
      "native_archive_accessed":False,"memory_limits_or_sampling_relaxed":False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--out",type=Path,required=True);args=parser.parse_args()
    result={"status":"RUNNING_LOADED_RUNTIME_CONTROLS"};a.write(args.out,result)
    try:result=controls()
    except BaseException as error:
        result.update(status="FAIL_LOADED_RUNTIME_CONTROLS",error=repr(error),traceback=traceback.format_exc());raise
    finally:a.write(args.out,result)

if __name__=="__main__":main()
