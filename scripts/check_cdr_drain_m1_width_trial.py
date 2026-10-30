#!/usr/bin/env python3
"""Actual source/lifecycle controls; synthetic I/O and deferred native geometry identified."""
import argparse,ast,copy,json,os,tempfile,traceback,types
from pathlib import Path
from unittest.mock import patch
import cloud_cdr_drain_m1_width_trial as h
import check_cdr_drain_access_feasibility as old

def controls(expected):
    positives=[];refusals=[];lifecycle=[]
    def yes(name,fn):
        value=fn();positives.append(dict(name=name,evidence=value));return value
    def no(name,fn):
        try:fn()
        except Exception as exc:refusals.append(dict(name=name,error=repr(exc)));return
        raise AssertionError("Missing refusal: "+name)
    config,_,data=h.source_guard(expected)
    yes("real_current6647_source_and_inputs",lambda:dict(full_members=len(data["full"]),selected=len(config["selected"])))
    yes("exact_two_320nm_topcell_rectangles",lambda:h.validate_rectangles(config["rectangles"]))
    with tempfile.TemporaryDirectory()as tmp:
        root=Path(tmp)
        derived=yes("actual_unchanged_physical_derivation",lambda:str(h.derive_physical(root)))
        record=h.decode((root/"physical-derivation.json").read_bytes())
        assert len(record["changes"])==4 and record["all_numerical_and560_13_gates_unchanged"]is True
        yes("real_output_inventory_keeps_empty_and_binary",lambda:output_fixture(root))
    before=ast.parse((h.ROOT/"scripts/cloud_cdr_drain_access_feasibility.py").read_text())
    after=ast.parse((h.ROOT/"scripts/cloud_cdr_drain_m1_width_trial.py").read_text())
    funcs=lambda tree:{n.name:ast.dump(n,include_attributes=False)for n in tree.body if isinstance(n,ast.FunctionDef)}
    a,b=funcs(before),funcs(after)
    yes("unchanged_preflight_cleanup_and_full_archive_acquisition",lambda:bool(all(a[k]==b[k]for k in ("preflight","finish","tokenless"))))
    assert all(a[k]==b[k]for k in ("preflight","finish","tokenless"))
    # perform differs only result status; all acquisition, census and cleanup statements are identical.
    oldtext=ast.get_source_segment((h.ROOT/"scripts/cloud_cdr_drain_access_feasibility.py").read_text(),next(n for n in before.body if isinstance(n,ast.FunctionDef)and n.name=="perform"))
    newtext=ast.get_source_segment((h.ROOT/"scripts/cloud_cdr_drain_m1_width_trial.py").read_text(),next(n for n in after.body if isinstance(n,ast.FunctionDef)and n.name=="perform"))
    assert oldtext.replace("PASS_CURRENT_ACCESS_OVERLAY_READBACK_NOT_ACCEPTANCE","PASS_TWO_M1_RECTANGLE_PHYSICAL_TRIAL_REQUIRES_FRESH_RC")==newtext
    for name,mut in (
      ("width",lambda x:x[0]["new"].__setitem__(0,1885080)),
      ("endpoint",lambda x:x[0]["new"].__setitem__(3,424035)),
      ("other_instance",lambda x:x[0].update(path="nssoc_cdr_pd500_resistor_v59/134_4/120_13")),
      ("component",lambda x:x[0].update(component=61)),
      ("device",lambda x:x[0].update(device=32)),
      ("third_rectangle",lambda x:x.append(copy.deepcopy(x[0]))),
      ("missing_rectangle",lambda x:x.pop()),
      ("bool_coordinate",lambda x:x[0]["new"].__setitem__(0,True)),
      ("old_rail",lambda x:x[0]["old"].__setitem__(0,1885160)),
      ("target_order",lambda x:x.reverse())):
        bad=copy.deepcopy(config["rectangles"]);mut(bad)
        no(name,lambda bad=bad:h.validate_rectangles(bad))
    for failed in ("cleanup","stop","join","restore"):
        actions=[];error=OSError("synthetic-"+failed)
        def act(name):
            actions.append(name)
            if name==failed:raise error
        supervisor=types.SimpleNamespace(ACTIVE=None,stop_process=lambda _:act("cleanup"),STOP=types.SimpleNamespace(set=lambda:act("stop")))
        heartbeat=types.SimpleNamespace(join=lambda timeout:act("join"),is_alive=lambda:False)
        with patch.object(h.signal,"signal",lambda s,v:act("restore")):
            rows,errors=h.finish(supervisor,heartbeat,{2:lambda *_:None})
        assert actions==["cleanup","stop","join","restore"]and errors==[error]
        h.encode(rows)
        lifecycle.append(dict(failure=failed,actual_finish=True,all_actions_attempted=True,serializable=True))
    inherited=old.controls("faaa3d6485c64ec4b2111b2faca3f8cd9b680597239d83136830656887ade1d1")
    result=dict(status="PASS_DRAIN_M1_WIDTH_SOURCE_CONTROLS",passed=True,
      counts=dict(positive=len(positives),refusal=len(refusals),lifecycle=len(lifecycle)),
      positives=positives,refusals=refusals,lifecycle=lifecycle,inherited=inherited,
      native_executed=False,physical_acceptance=False,native_serialization_faults_deferred=True)
    assert result["counts"]==dict(positive=5,refusal=10,lifecycle=4)
    return result

def output_fixture(root):
    out=root/"outputs";out.mkdir();(out/"zero.stderr").write_bytes(b"");(out/"synthetic.gds").write_bytes(b"\x00\x01")
    lines=[];files=h.emit(out,lambda line,**kw:lines.append(line))
    assert set(files)=={"zero.stderr","synthetic.gds"}and files["zero.stderr"]["bytes"]==0
    assert len(lines)==1 and "COMPLETE_INVENTORY"in lines[0]
    return dict(complete_files=files,native_payload_emitted=False,synthetic_binary=True)

def main():
    p=argparse.ArgumentParser();p.add_argument("--pins-sha256",required=True);p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();ctx=h.context(os.environ);primary=None
    current=dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False)
    try:result=controls(args.pins_sha256);result["current_context"]=current
    except BaseException as exc:
        primary=exc;result=dict(status="FAIL_DRAIN_M1_WIDTH_SOURCE_CONTROLS",passed=False,error=repr(exc),
          traceback=traceback.format_exc(),current_context=current,native_executed=False,physical_acceptance=False)
    old.finish_report(args.output,result,primary)
if __name__=="__main__":main()
