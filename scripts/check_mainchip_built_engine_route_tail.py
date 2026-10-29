#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted controls only; synthetic archives/wires are never native evidence."""
import ast
from contextlib import ExitStack
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import types
from unittest.mock import patch
import mainchip_built_engine_route_tail_contract as c
import mainchip_built_engine_route_tail_driver as driver
import cloud_mainchip_built_engine_route_tail as host
import mainchip_two_signal_repair as repair
import mainchip_two_signal_internal_witness as witness
import check_mainchip_two_signal_internal_witness as witness_fixture
from mainchip_witness_engine_build import fingerprint
ROOT=Path(__file__).resolve().parent.parent

def refused(fn,reason):
    try:fn()
    except (ValueError,AssertionError,RuntimeError,KeyError,OSError) as exc:
        assert reason in str(exc),(reason,repr(exc))
        return dict(type=type(exc).__name__,error=str(exc))
    raise AssertionError("Refusal was not reached: "+reason)

def tar_bytes(files):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode="w:gz") as tar:
        for name,raw in files:
            info=tarfile.TarInfo(name);info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
    return stream.getvalue()

def envelope_controls():
    c.prefix_contract(ROOT)
    originals=[c.saved(ROOT,x) for x in ("run","jobs","release","tag")]
    out=[]
    mutations=[
      (0,lambda x:x.update(head_sha="0"*40),"prefix run"),
      (0,lambda x:x.update(conclusion="failure"),"prefix run"),
      (0,lambda x:x.update(run_attempt=2),"prefix run"),
      (1,lambda x:x["jobs"][0].update(conclusion="failure"),"prefix jobs"),
      (2,lambda x:x.update(id=1),"prefix release"),
      (2,lambda x:x.update(draft=True),"prefix release"),
      (2,lambda x:x["assets"].pop(),"complete prefix assets"),
      (2,lambda x:x["assets"][0].update(digest="sha256:"+"0"*64),"complete prefix assets"),
      (3,lambda x:x["object"].update(type="tag"),"prefix lightweight tag"),
      (3,lambda x:x["object"].update(sha="0"*40),"prefix lightweight tag")]
    for index,mutate,reason in mutations:
        changed=copy.deepcopy(originals);mutate(changed[index]);assert changed!=originals
        out.append(refused(lambda:c.envelope(ROOT,*changed),reason))
    return dict(actual_saved_terminal=True,refusals=out)

def restore_controls():
    import route_cloud_newer_postcts as transport
    results=[]
    # Full 746-member synthetic projection with explicit synthetic bytes, not an ODB/ELF.
    members={"source/synthetic.txt":b"synthetic source","engine/openroad":b"not ELF",
        "input.odb":b"not ODB","runtime-dependencies.json":b"{}","out/work/fixed.odb":b"synthetic fixed",
        "out/work/repair.tcl":b"synthetic Tcl","routing-inputs/global/synthetic.txt":b"synthetic global",
        "routing-inputs/clock/selected/synthetic.txt":b"synthetic clock",
        "input-transport/selected/synthetic.txt":b"synthetic failed input"}
    for i in range(746-len(members)):members["source/fixture-%04d.txt"%i]=str(i).encode()
    inv={"files":{p:dict(bytes=len(b),sha256=c.digest(b)) for p,b in members.items()}}
    invraw=(json.dumps(inv,sort_keys=True,indent=2)+"\n").encode()
    nested=tar_bytes(sorted(members.items()))
    frozen=dict(archive=dict(bytes=len(nested),sha256=c.digest(nested)),
        inventory=dict(bytes=len(invraw),sha256=c.digest(invraw)))
    base={"frozen-native-workspace.tar.gz":nested,"frozen-prefix-inventory.json":invraw,"diagnostic.txt":b"synthetic"}
    outputraw=(json.dumps(dict(files={p:dict(bytes=len(b),sha256=c.digest(b)) for p,b in base.items()}))+"\n").encode()
    for mode in ("complete","outer_missing","outer_extra","nested_changed"):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);work=root/"work";work.mkdir();out=work/"out";out.mkdir()
            srcroot=root/"source";(srcroot/"docs/evidence").mkdir(parents=True)
            (srcroot/(c.PREFIX+".outputs.json")).write_bytes(outputraw)
            (srcroot/(c.PREFIX+".frozen-prefix-inventory.json")).write_bytes(invraw)
            files=dict(base);files["outputs.json"]=outputraw
            if mode=="outer_missing":files.pop("diagnostic.txt")
            if mode=="outer_extra":files["unexpected.txt"]=b"unexpected"
            if mode=="nested_changed":
                changed=dict(members);changed["input.odb"]=b"changed"
                files["frozen-native-workspace.tar.gz"]=tar_bytes(sorted(changed.items()))
                # Outer map/hash is internally consistent; the independently frozen nested binding must reject.
                bad=dict(c.decode(outputraw))
                raw=files["frozen-native-workspace.tar.gz"]
                bad["files"]["frozen-native-workspace.tar.gz"]=dict(bytes=len(raw),sha256=c.digest(raw))
                files["outputs.json"]=(json.dumps(bad)+"\n").encode()
                (srcroot/(c.PREFIX+".outputs.json")).write_bytes(files["outputs.json"])
            outer=tar_bytes(sorted(files.items()))
            part=dict(name="synthetic.part000",bytes=len(outer),sha256=c.digest(outer))
            data={"parts":dict(archive=dict(bytes=len(outer),sha256=c.digest(outer)),parts=[part]),
                  "outputs":c.decode(files["outputs.json"]),"frozen-prefix":frozen}
            def fetch(url,expected,path):
                assert expected==part["sha256"];Path(path).write_bytes(outer)
            with ExitStack() as stack:
                stack.enter_context(patch.object(host,"ROOT",srcroot))
                stack.enter_context(patch.object(c,"prefix_contract",return_value=inv))
                stack.enter_context(patch.object(c,"envelope",return_value={"synthetic":True}))
                stack.enter_context(patch.object(c,"saved",side_effect=lambda root,key:data[key]))
                stack.enter_context(patch.object(c,"FROZEN_BYTES",sum(x["bytes"] for x in inv["files"].values())))
                stack.enter_context(patch.object(host.reservation.release,"api",return_value={}))
                stack.enter_context(patch.object(transport,"fetch",side_effect=fetch))
                if mode=="complete":
                    assert host.restore_prefix(work,out)==inv
                    assert c.frozen_unchanged(work,inv)["files"]==746
                    proof=c.decode((out/"prefix-restoration.json").read_bytes())
                    assert proof["nested"]["all_files"]==inv["files"]
                    result=dict(complete=True,synthetic_files=746)
                else:
                    reason={"outer_missing":"missing archive member","outer_extra":"archive member identity/size",
                            "nested_changed":"nested frozen archive identities"}[mode]
                    result=refused(lambda:host.restore_prefix(work,out),reason)
            results.append(dict(case=mode,result=result))
    return results

def gate_records():
    # Reuse the full authentic original three-short measurement in a synthetic phase envelope.
    old=repair.readback()["saved_final_native_audit"]
    rows={p:dict(status=s,accepted=False,timing_accepted=False,full_phy_accepted=False) for p,s in c.STATUSES.items()}
    final=copy.deepcopy(old);final.update(rows["drc-audit"]);rows["drc-audit"]=final
    rows["drc-audit"]["routing_delta"]["changed_signal_names"]=[]
    return rows

def sequence_controls():
    rows=gate_records();events=[]
    got=driver.execute_tail(lambda p,a:events.append((p,a)),lambda p:copy.deepcopy(rows[p]))
    assert [p for p,a in events]==list(c.PHASES) and got==rows
    assert [a for p,a in events]==[c.command(p) for p in c.PHASES]
    gate=c.complete(got);assert gate["original_gate"]["DRT_markers"]==3
    assert gate["original_gate"]["eligible_for_separately_reviewed_RC_STA"] is False
    failures=[]
    for phase in c.PHASES:
        seen=[];sentinel=RuntimeError("phase sentinel")
        def execute(p,a):
            seen.append(p)
            if p==phase:raise sentinel
        try:driver.execute_tail(execute,lambda p:copy.deepcopy(rows[p]))
        except RuntimeError as exc:assert exc is sentinel
        else:raise AssertionError("lost primary")
        assert seen==list(c.PHASES[:c.PHASES.index(phase)+1]);failures.append(phase)
    refused(lambda:c.command("ownership"),"unapproved tail phase")
    for key in ("original1691_clock_gate_passed","native_invariants_passed"):
        changed=copy.deepcopy(rows);changed["drc-audit"][key]=False
        refused(lambda:c.complete(changed),"")
    changed=copy.deepcopy(rows);changed["drc-audit"]["routing_delta"]["changed_signal_names"]=["clock"]
    refused(lambda:c.complete(changed),"")
    return dict(original_three_shorts_retained=True,sequence=events,stops=failures,gate_refusals=4)

def observer_controls():
    baseline=witness_fixture.fixture();results=[]
    with tempfile.TemporaryDirectory() as d:
        work=Path(d);(work/"out/work").mkdir(parents=True)
        (work/"out/work/routed-fixed.odb").write_bytes(b"explicitly synthetic writer file")
        after=witness.parse_stage(baseline["after_writer"],"after_writer")
        pairs={name:[[r["opcode"],r["data"]] for r in after["nets"][name]["raw"]] for name in witness.NAMES}
        raw=dict(status="PASS_READ_ONLY_SAVED_WRITER_RAW",
            routed_odb=fingerprint(work/"out/work/routed-fixed.odb"),raw_pairs=pairs)
        c.atomic_record(work/"out/writer-raw.json",raw)
        assert driver.observer_result(work,"off")==dict(enabled=False,witness_files=0)
        (work/"out/witness").mkdir()
        for stage,b in baseline.items():(work/"out/witness"/(stage+".jsonl")).write_bytes(b)
        on=driver.observer_result(work,"on");assert on["writer_raw_join"] and not on["diagnosis"]["physical_acceptance"]
        results.append(refused(lambda:driver.observer_result(work,"off"),"off case wrote witness"))
        changed=copy.deepcopy(raw);changed["raw_pairs"][witness.NAMES[0]][0][1]+=1
        c.atomic_record(work/"out/writer-raw.json",changed)
        results.append(refused(lambda:driver.observer_result(work,"on"),"after-writer raw opcodes"))
        c.atomic_record(work/"out/writer-raw.json",raw)
        (work/"out/witness/after_writer.jsonl").unlink()
        results.append(refused(lambda:driver.observer_result(work,"on"),"exact four witness"))
    # Actual native raw_pairs function body with synthetic public API objects, no odb import.
    path=ROOT/"scripts/mainchip_built_engine_route_tail_native.py";tree=ast.parse(path.read_bytes())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="raw_pairs")
    ns={"c":c,"witness":witness};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),"exec"),ns)
    class Wire:
        def __init__(self,rows):self.rows=rows
        def length(self):return len(self.rows)
        def getOpcode(self,i):return self.rows[i][0]
        def getData(self,i):return self.rows[i][1]
    class Block:
        def findNet(self,name):return types.SimpleNamespace(getWire=lambda:Wire(pairs[name]))
    assert ns["raw_pairs"](Block())==pairs
    return dict(positive=3,refusals=results,synthetic_only=True)

def fixture_case(mode):
    row=dict(schema="built-engine-route-tail-case-v1",mode=mode,status="PASS_COMPLETE_ROUTE_TAIL_DIAGNOSTIC",
        terminal_errors=[],source="a"*40,run_id=1,engine=c.ENGINE,frozen_input={"sha256":"f"*64},
        prefix_source=c.PREFIX_SOURCE,prefix_run=c.PREFIX_RUN,
        original_audits={"original_audits_complete":True},physical_acceptance=False,
        timing_accepted=False,full_phy_accepted=False,
        geometry_files={p:dict(bytes=1,sha256="e"*64) for p in c.COMPARE_FILES},complete_drc={"marker_count":3})
    row["observer"]=(dict(enabled=False,witness_files=0) if mode=="off" else
        dict(enabled=True,writer_raw_join=True,diagnosis=dict(status="COMPLETE_DIAGNOSTIC_ONLY",stages={x:{} for x in witness.STAGES})))
    return row

def comparison_controls():
    off,on=fixture_case("off"),fixture_case("on");r=c.compare_cases(off,on)
    assert r["observed_equivalence"] and not r["physical_acceptance"] and r["actual_on_DRC"]["marker_count"]==3
    changes=[]
    for name in c.COMPARE_FILES:
        bad=copy.deepcopy(on);bad["geometry_files"][name]["sha256"]="b"*64
        assert c.compare_cases(off,bad)["observed_equivalence"] is False;changes.append(name)
    bad=copy.deepcopy(on);bad["complete_drc"]["marker_count"]=0
    assert c.compare_cases(off,bad)["observed_equivalence"] is False
    for field,value,reason in (("source","b"*40,"same successor"),("engine",{},"same frozen"),
            ("frozen_input",{},"same frozen"),("physical_acceptance",True,"comparison acceptance"),
            ("terminal_errors",[{}],"complete tail case")):
        bad=copy.deepcopy(on);bad[field]=value;refused(lambda:c.compare_cases(off,bad),reason)
    return dict(positive=1,geometry_mismatches=changes,marker_mismatch=True,refusals=5)

def lifecycle_controls():
    outputs=[]
    for mode in ("complete","body","stop","join","body_stop_join","save","body_save"):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d);(work/"out/work").mkdir(parents=True);(work/"tail-source").mkdir()
            (work/"source").mkdir();(work/"input.txt").write_bytes(b"frozen")
            inv=dict(files={"input.txt":fingerprint(work/"input.txt")})
            c.atomic_record(work/"frozen-manifest.json",inv)
            c.atomic_record(work/"request.json",dict(mode="off",source="a"*40,run_id=1,engine=c.ENGINE))
            rows=gate_records()
            body=RuntimeError("body sentinel");stop=RuntimeError("stop sentinel");join=RuntimeError("join sentinel")
            save=OSError("atomic replace sentinel");events=[];actual_atomic=c.atomic_record
            class Beat:
                def __init__(self,*a,**kw):pass
                def start(self):events.append("beat-start")
                def join(self,timeout):
                    events.append("beat-join")
                    if "join" in mode:raise join
                def is_alive(self):return False
            def stop_process(active):
                events.append("process-stop")
                if "stop" in mode:raise stop
            sup=types.SimpleNamespace(SECONDS=1200,MAX_GROUP_RSS_KIB=c.LIMITS["max_group_rss_kib"],
                MIN_AVAILABLE_KIB=c.LIMITS["min_available_kib"],ACTIVE=None,
                stop_process=stop_process,STOP=types.SimpleNamespace(set=lambda:events.append("beat-stop")),
                interrupted=lambda *a:None,heartbeat=lambda:None)
            def command(s,argv,phase):
                events.append(phase)
                assert c.WITNESS_ENV not in os.environ
                if phase==c.PHASES[0] and "body" in mode:raise body
                if phase==c.PHASES[0]:
                    (work/"out/supervision/one-two-signal-routing-attempt.stdout").write_bytes(
                        b"NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_BEGIN\nNSSOC_FIXED_CLOCK_SIGNAL_REPAIR_RETURNED\n")
                if phase in rows:actual_atomic(work/"out/work"/(phase+"-result.json"),rows[phase])
                return dict(label=phase,returncode=0,requested_timeout_seconds=14400 if phase==c.PHASES[0] else 1200)
            def observer(w,m):return dict(enabled=False,witness_files=0)
            for name in c.COMPARE_FILES:(work/"out/work"/name).write_bytes(b"synthetic")
            def replace(a,b):
                if "save" in mode and Path(b).name=="case-result.json":raise save
                return original_replace(a,b)
            original_replace=os.replace
            capture=io.StringIO()
            with ExitStack() as stack:
                stack.enter_context(patch.object(driver,"WORK",work))
                stack.enter_context(patch.object(c,"method",return_value={"native_tail_authorized":True}))
                stack.enter_context(patch.object(c.previous,"method",return_value={}))
                stack.enter_context(patch.object(driver.old,"supervisor",return_value=sup))
                stack.enter_context(patch.object(driver.threading,"Thread",Beat))
                stack.enter_context(patch.object(driver.controller,"execute_command",side_effect=command))
                stack.enter_context(patch.object(driver,"observer_result",side_effect=observer))
                stack.enter_context(patch.dict(os.environ,{},clear=True))
                stack.enter_context(patch.object(os,"replace",side_effect=replace))
                stack.enter_context(patch("sys.stdout",capture))
                caught=None
                try:code=driver.main()
                except BaseException as exc:caught=exc
            if "body" in mode:assert caught is body
            elif "save" in mode:assert caught is save
            else:assert caught is None
            assert "process-stop" in events and "beat-stop" in events and "beat-join" in events
            if "save" in mode:
                line=next(x for x in capture.getvalue().splitlines() if x.startswith("ENGINE_BUILD_TERMINAL_FALLBACK "))
                result=json.loads(line.split(" ",1)[1])["complete_unsaved_record"]
                assert any(k.startswith("case-result.json.") and k.endswith(".tmp") for k in result["available_outputs_after_save_failure"])
                assert result["status"]=="FAIL_ROUTE_TAIL_DIAGNOSTIC"
            else:
                result=c.decode((work/"out/case-result.json").read_bytes())
                assert result["status"]==("PASS_COMPLETE_ROUTE_TAIL_DIAGNOSTIC" if mode=="complete" else "FAIL_ROUTE_TAIL_DIAGNOSTIC")
            assert c.frozen_unchanged(work,inv)["files"]==1
            assert any(x["action"]=="frozen-input-terminal" for x in result["terminal_actions"])
            outputs.append(dict(case=mode,events=events,status=result["status"],same_primary=("body" in mode)))
    return outputs

def publication_controls():
    ctx=dict(source="a"*40,token="1-1",mode="off");tag="cloud-results-1-1-"+c.group("off")
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/"case-result.json";path.write_bytes(b"synthetic")
        receipt=fingerprint(path)
        release=dict(id=1,tag_name=tag,target_commitish=ctx["source"],draft=False,prerelease=True,assets=[])
        ref={"ref":"refs/tags/"+tag,"object":{"type":"commit","sha":ctx["source"]}}
        def read(endpoint):return copy.deepcopy(ref if endpoint.startswith("git/") else release)
        def upload(t,p):
            assert t==tag
            release["assets"].append(dict(id=3,name=p.name,size=receipt["bytes"],digest="sha256:"+receipt["sha256"]))
        host.publish_asset(path,ctx,1,read,upload);assert len(release["assets"])==1
        assert host.publish_asset(path,ctx,1,read,lambda *a:(_ for _ in ()).throw(AssertionError("upload reused")))["reused_identical"]
        release["assets"][0]["digest"]="sha256:"+"0"*64
        refused(lambda:host.publish_asset(path,ctx,1,read,upload),"existing asset conflict")
    return dict(positive=2,refusals=1)

def isolated_controls(m):
    with tempfile.TemporaryDirectory() as d:
        root=Path(d)
        for p in [*m["protected"],c.METHOD]:
            q=root/p;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(c.secure_file(ROOT,p),q)
        names=("mainchip_built_engine_route_tail_contract","mainchip_built_engine_route_tail_driver",
            "mainchip_built_engine_route_tail_inner","cloud_mainchip_built_engine_route_tail")
        auth=[]
        for enabled in (False,True):
            baseline=copy.deepcopy(m);baseline["source_controls_authorized"]=enabled;baseline["native_tail_authorized"]=False
            c.atomic_record(root/c.METHOD,baseline);assert c.method(root)==baseline
            for label,key,value,reason in (
                ("native type","native_tail_authorized",1,"authorization type"),
                ("control type","source_controls_authorized","true","authorization type"),
                ("physical claim","physical_acceptance",True,"no acceptance"),
                ("retry","automatic_retry_authorized",True,"no acceptance"),
                ("false equivalence","observer_equivalence_qualified",True,"no acceptance")):
                changed=copy.deepcopy(baseline);changed[key]=value
                assert json.dumps(changed,sort_keys=True)!=json.dumps(baseline,sort_keys=True)
                c.atomic_record(root/c.METHOD,changed)
                auth.append(dict(mode=enabled,label=label,error=refused(lambda:c.method(root),reason)))
        pending=copy.deepcopy(m);pending["source_controls_authorized"]=True;pending["native_tail_authorized"]=True
        c.atomic_record(root/c.METHOD,pending)
        auth.append(dict(mode="native-pending-split",error=refused(lambda:c.method(root),"route/audit handoff split required")))
        c.atomic_record(root/c.METHOD,m)
        code="import sys;sys.path.insert(0,sys.argv[1]);"+ ";".join("import "+x for x in names)+";print('TAIL_IMPORT_PASS')"
        p=subprocess.run([sys.executable,"-I","-B","-c",code,str(root/"scripts")],
            capture_output=True,text=True,timeout=120)
        assert p.returncode==0 and p.stdout.strip()=="TAIL_IMPORT_PASS",(p.stdout,p.stderr)
    return dict(actual_isolated_imports=list(names),native_odb_module_imported=False,actual_source_control_modes=2,native_enable_refused_until_split=True,authorization_refusals=auth)

def main():
    m=c.method(ROOT)
    result=dict(status="PASS_ROUTE_TAIL_SOURCE_CONTROLS",protected_count=len(m["protected"]),
        source_only=True,native_routing_executed=False,physical_acceptance=False,
        complete_native_qualification=False)
    result["envelope"]=envelope_controls()
    result["restore"]=restore_controls()
    result["sequence"]=sequence_controls()
    result["observer"]=observer_controls()
    result["comparison"]=comparison_controls()
    result["lifecycle"]=lifecycle_controls()
    result["publication"]=publication_controls()
    result["isolated_imports"]=isolated_controls(m)
    assert len(result["envelope"]["refusals"])==10 and len(result["restore"])==4
    assert len(result["lifecycle"])==7 and len(result["comparison"]["geometry_mismatches"])==10
    print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
if __name__=="__main__":main()
