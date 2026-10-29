#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted controls only; synthetic archives/wires are never native evidence."""
import ast
import argparse
import contextlib
import traceback
from types import SimpleNamespace
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
import mainchip_fixed_engine_route_tail_contract as c
import mainchip_fixed_engine_route_tail_driver as driver
import cloud_mainchip_fixed_engine_route_tail as host
import mainchip_fixed_engine_route_tail_handoff as handoff
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
    # Full c.FROZEN_COUNT-member synthetic projection with explicit synthetic bytes, not an ODB/ELF.
    members={"source/synthetic.txt":b"synthetic source","engine/openroad":b"not ELF",
        "input.odb":b"not ODB","runtime-dependencies.json":b"{}","out/work/fixed.odb":b"synthetic fixed",
        "out/work/repair.tcl":b"synthetic Tcl","routing-inputs/global/synthetic.txt":b"synthetic global",
        "routing-inputs/clock/selected/synthetic.txt":b"synthetic clock",
        "input-transport/selected/synthetic.txt":b"synthetic failed input"}
    for i in range(c.FROZEN_COUNT-len(members)):members["source/fixture-%04d.txt"%i]=str(i).encode()
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
            srcroot=root/"source";(srcroot/Path(c.saved_path("outputs")).parent).mkdir(parents=True)
            (srcroot/c.saved_path("outputs")).write_bytes(outputraw)
            (srcroot/c.saved_path("frozen-prefix-inventory")).write_bytes(invraw)
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
                (srcroot/c.saved_path("outputs")).write_bytes(files["outputs.json"])
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
                    assert c.frozen_unchanged(work,inv)["files"]==c.FROZEN_COUNT
                    proof=c.decode((out/"prefix-restoration.json").read_bytes())
                    assert proof["nested"]["all_files"]==inv["files"]
                    result=dict(complete=True,synthetic_files=c.FROZEN_COUNT)
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
    rows=gate_records();events=[];got={}
    for stage in ('route','audit'):
        got.update(driver.execute_tail(lambda p,a:events.append((p,a)),lambda p:copy.deepcopy(rows[p]),stage))
    assert [p for p,a in events]==list(c.PHASES) and got==rows
    assert [a for p,a in events]==[c.command(p) for p in c.PHASES]
    gate=c.complete(got);assert gate['original_gate']['DRT_markers']==3
    assert gate['original_gate']['eligible_for_separately_reviewed_RC_STA'] is False
    failures=[]
    for phase in c.PHASES:
        stage='route' if phase==c.PHASES[0] else 'audit'
        phases=c.PHASES[:1] if stage=='route' else c.PHASES[1:]
        seen=[];sentinel=RuntimeError('phase sentinel')
        def execute(p,a):
            seen.append(p)
            if p==phase:raise sentinel
        try:driver.execute_tail(execute,lambda p:copy.deepcopy(rows[p]),stage)
        except RuntimeError as exc:assert exc is sentinel
        else:raise AssertionError('lost primary')
        assert seen==list(phases[:phases.index(phase)+1]);failures.append(phase)
    refused(lambda:c.command('ownership'),'unapproved tail phase')
    for key in ('original1691_clock_gate_passed','native_invariants_passed'):
        changed=copy.deepcopy(rows);changed['drc-audit'][key]=False
        refused(lambda:c.complete(changed),'')
    changed=copy.deepcopy(rows);changed['drc-audit']['routing_delta']['changed_signal_names']=['clock']
    refused(lambda:c.complete(changed),'')
    return dict(original_three_shorts_retained=True,sequence=events,stops=failures,gate_refusals=4,
        independent_route_seconds=14400,independent_audit_seconds=[1200]*5)

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
    path=ROOT/"scripts/mainchip_fixed_engine_route_tail_native.py";tree=ast.parse(path.read_bytes())
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
    row=dict(schema="built-engine-route-tail-case-v1",mode=mode,stage="audit",
        route_lineage=dict(authenticated_complete_route=True),status="PASS_COMPLETE_ROUTE_TAIL_DIAGNOSTIC",
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

def lifecycle_controls(method,stage="audit"):
    outputs=[]
    for mode in ("complete","body","stop","join","body_stop_join","save","body_save","heartbeat_set"):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d);(work/"out/work").mkdir(parents=True);(work/"tail-source").mkdir()
            (work/"source").mkdir();(work/"input.txt").write_bytes(b"frozen")
            inv=dict(files={"input.txt":fingerprint(work/"input.txt")})
            c.atomic_record(work/"frozen-manifest.json",inv)
            c.atomic_record(work/"request.json",dict(mode="off",stage=stage,source="a"*40,run_id=1,engine=c.ENGINE))
            c.atomic_record(work/'route-projection.json',inv)
            c.atomic_record(work/'route-lineage.json',dict(authenticated_complete_route=True,source='a'*40,mode='off',run_id=1))
            c.atomic_record(work/'out/route-case-result.json',dict(route_log={'synthetic':True},commands=[{'synthetic':True}]))
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
            def heartbeat_set():
                events.append("beat-stop")
                if mode=="heartbeat_set":raise RuntimeError("heartbeat set sentinel")
            sup=types.SimpleNamespace(SECONDS=1200,MAX_GROUP_RSS_KIB=c.LIMITS["max_group_rss_kib"],
                MIN_AVAILABLE_KIB=c.LIMITS["min_available_kib"],ACTIVE=None,
                stop_process=stop_process,STOP=types.SimpleNamespace(set=heartbeat_set),
                interrupted=lambda *a:None,heartbeat=lambda:None)
            def command(s,argv,phase):
                events.append(phase)
                assert c.WITNESS_ENV not in os.environ
                if phase==(c.PHASES[0] if stage=="route" else c.PHASES[1]) and "body" in mode:raise body
                if phase==c.PHASES[0]:
                    (work/"out/supervision/one-two-signal-routing-attempt.stdout").write_bytes(
                        b"NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_BEGIN\nNSSOC_FIXED_CLOCK_SIGNAL_REPAIR_RETURNED\n")
                if phase in rows:actual_atomic(work/"out/work"/(phase+"-result.json"),rows[phase])
                return dict(label=phase,returncode=0,requested_timeout_seconds=14400 if phase==c.PHASES[0] else 1200)
            def observer(w,m):return dict(enabled=False,witness_files=0)
            for name in (*c.COMPARE_FILES,"fixed-routing.drc"):(work/"out/work"/name).write_bytes(b"synthetic")
            def replace(a,b):
                if "save" in mode and Path(b).name=="case-result.json":raise save
                return original_replace(a,b)
            original_replace=os.replace
            capture=io.StringIO()
            with ExitStack() as stack:
                stack.enter_context(patch.object(driver,"WORK",work))
                stack.enter_context(patch.object(c,"method",return_value=native_baseline(method)))
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
                assert result["status"]==("PASS_ROUTE_ONLY_AWAITING_ORIGINAL_AUDITS" if mode=="complete" and stage=="route" else "PASS_COMPLETE_ROUTE_TAIL_DIAGNOSTIC" if mode=="complete" else "FAIL_ROUTE_TAIL_DIAGNOSTIC")
            if mode=="heartbeat_set":
                assert any(x["action"]=="heartbeat-stop" and x["completed"]is False for x in result["terminal_actions"])
                assert events.index("beat-stop")<events.index("beat-join")
            assert c.frozen_unchanged(work,inv)["files"]==1
            assert any(x["action"]=="frozen-input-terminal" for x in result["terminal_actions"])
            outputs.append(dict(case=mode,stage=stage,events=events,status=result["status"],same_primary=("body" in mode)))
    return outputs

def publication_controls():
    ctx=dict(source="a"*40,token="1-1",mode="off",stage="audit");tag="cloud-results-1-1-"+c.group("off","audit")
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

def split_publication_controls(fixture):
    results=[]
    for mode in ('missing_terminal','empty_terminal','malformed_terminal','upload_failure'):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d);out=work/'out';out.mkdir();(out/'work').mkdir()
            (out/'work/partial-route.txt').write_bytes(b'complete synthetic partial route evidence')
            (out/'route-handoff.tar.gz').write_bytes(b'opaque incomplete synthetic archive; never accepted')
            if mode=='malformed_terminal':(out/'host-result.json').write_bytes(b'{"status":')
            if mode=='empty_terminal':(out/'host-result.json').write_bytes(b'')
            original_bytes={p.relative_to(out).as_posix():p.read_bytes() for p in out.rglob('*') if p.is_file()}
            ctx=dict(source='a'*40,token='123-1',mode='off',stage='route')
            tag='cloud-results-123-1-'+c.group('off','route')
            release=dict(id=3,tag_name=tag,target_commitish=ctx['source'],draft=False,prerelease=True,assets=[])
            ref=dict(ref='refs/tags/'+tag,object=dict(type='commit',sha=ctx['source']))
            uploaded={};sentinel=OSError('upload sentinel')
            def read(endpoint):
                if endpoint.startswith('git/'):return copy.deepcopy(ref)
                assert endpoint in ('releases/tags/'+tag,'releases/3');return copy.deepcopy(release)
            def upload(argv,**kwargs):
                assert argv[:3]==['gh','release','upload'] and argv[3]==tag and argv[-2:]==['--repo',c.REPOSITORY]
                path=Path(argv[4])
                if mode=='upload_failure':raise sentinel
                uploaded[path.name]=path.read_bytes()
                receipt=fingerprint(path)
                release['assets'].append(dict(id=len(release['assets'])+1,name=path.name,size=receipt['bytes'],digest='sha256:'+receipt['sha256']))
            caught=None
            with ExitStack() as stack:
                stack.enter_context(patch.object(c,'context',return_value=ctx));stack.enter_context(patch.object(host,'ROOT',fixture))
                stack.enter_context(patch.object(host,'owned_work',return_value=work))
                stack.enter_context(patch.object(host.reservation,'wait',return_value={**reservation(ctx),"release_id":3}))
                stack.enter_context(patch.object(host.reservation.release,'api',side_effect=read))
                stack.enter_context(patch.object(host.subprocess,'run',side_effect=upload))
                stack.enter_context(patch.object(host.shutil,'disk_usage',return_value=types.SimpleNamespace(free=64*1024**3)))
                try:assert host.publish()==0
                except BaseException as exc:caught=exc
            if mode=='upload_failure':assert caught is sentinel and not (out/'publication.json').exists()
            else:assert caught is None and c.decode((out/'publication.json').read_bytes())['native_accepted'] is False
            available=c.decode((out/'publication-availability.json').read_bytes())
            assert available['source_records']['inner-result.json']['present'] is False
            if mode in ('malformed_terminal','empty_terminal'):assert 'parse_error' in available['source_records']['host-result.json']
            else:assert available['source_records']['host-result.json']['present'] is False
            output=c.decode((out/'outputs.json').read_bytes());parts=c.decode((out/'parts.json').read_bytes())
            archive=b''.join((work/p['name']).read_bytes() for p in parts['parts'])
            assert dict(bytes=len(archive),sha256=c.digest(archive))==parts['archive']
            with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
                saved={m.name:tar.extractfile(m).read() for m in tar if m.isfile()}
            assert set(saved)==set(output['files'])|{'outputs.json'}
            for p,row in output['files'].items():assert dict(bytes=len(saved[p]),sha256=c.digest(saved[p]))==row
            for p,raw in original_bytes.items():assert saved[p]==raw and (out/p).read_bytes()==raw
            if caught is None:assert uploaded['outputs.json']==(out/'outputs.json').read_bytes()
            results.append(dict(case=mode,full_partial_output_archive=True,missing_terminal_not_accepted=True,same_upload_exception=mode=='upload_failure'))
    return results





DERIVATION_SOURCES = {'scripts/cloud_mainchip_built_engine_route_tail.py': {'bytes': 19116, 'sha256': '6a88f0da614a727e8255a89b6379b03f064b92425dd9651cba3d2f1d9dbdc21c'}, 'scripts/mainchip_built_engine_route_tail_driver.py': {'bytes': 9162, 'sha256': '72ae99009eeedf52d3c7edc109044d39446d18751298b8dae34de67f8fc06f8f'}, 'scripts/mainchip_built_engine_route_tail_native.py': {'bytes': 2244, 'sha256': 'cb9bed6aa19765a61109354e9ebe787c6be1682f7232f8eb06bfc4c50c71d20e'}, 'scripts/mainchip_built_engine_route_tail_inner.py': {'bytes': 8187, 'sha256': '0cc8512cf09d25a43795553efee89d178f1ed7e29386881985a4b06c492984df'}, 'scripts/mainchip_built_engine_route_tail_handoff.py': {'bytes': 16860, 'sha256': '89cf916a172f3fb099f2716f1e47f2948e08ce679e969cb4e4d34cb3f3e04066'}, 'scripts/mainchip_built_engine_route_tail_contract.py': {'bytes': 11931, 'sha256': '4e254ade05e9f1dc4787a0e15191caae08f3db7708d2995e6a77dd4fd7ea4f2c'}, 'scripts/cloud_mainchip_fixed_engine_route_prefix.py': {'bytes': 20322, 'sha256': 'f7b43c87dc5b90f52a96009ba390b0b6d6b96645c8d856664956fd4c169b9988'}, 'scripts/mainchip_fixed_engine_build_contract.py': {'bytes': 9057, 'sha256': 'b065245c7782651dd5716eea1442c41228c3dff60ddcaecffa94fd20d0740e04'}, 'scripts/cloud_mainchip_fixed_engine_route_tail.py': {'bytes': 22331, 'sha256': '868eb6c24157768f38336d3f68c78184266d04c727f56fe45768d22dae316715'}, 'scripts/mainchip_fixed_engine_route_tail_native.py': {'bytes': 2271, 'sha256': '2457356cf87b8ca6c14387900b8880a72a24ec60bb9cc25cd47d79f5b3d7c558'}, 'scripts/mainchip_fixed_engine_route_tail_inner.py': {'bytes': 8234, 'sha256': '486219cc47edc2b77e9efcd0ff62dfdff594746c7d81541afd3074d5de2d4615'}, 'docs/evidence/mainchip-fixed-engine-route-tail-wrapper-derivation-review-20261029.json': {'bytes': 47171, 'sha256': '7d410371df149994c37a0d028ab34259050a9a2dfbb5b102d1495c8c38b81869'}, 'scripts/check_mainchip_built_engine_route_tail.py': {'bytes': 28192, 'sha256': '500bb2596a8a8188191053088a294a0bf384ca19e95c4eb974f0f60a7d95da31'}, 'scripts/check_mainchip_built_engine_route_tail_handoff.py': {'bytes': 16020, 'sha256': 'd9f6bca6f5c29b71ac6343e1b82d66711c8ad276814265bb4e127e0beabc1c26'}, 'scripts/check_mainchip_fixed_engine_runtime_host.py': {'bytes': 15404, 'sha256': '2fdd0a6adf698deb2ebb279985379901de96a05bd4fb371004b63c88d2adcb59'}, 'scripts/mainchip_exit_checked_command_evidence.py': {'bytes': 14874, 'sha256': '059e3e4edde4a63997cc841728f02d5b6a2aaf77335cb7d1b8dba70ed7d2e321'}, 'scripts/check_mainchip_exit_checked_command_evidence.py': {'bytes': 17650, 'sha256': '07d6a89d41f32d295da5d00b2fe1b6c2b6345a90b8ffff339ca4344aa00e9388'}}


def function(text,name):
    tree=ast.parse(text)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    start=min([node.lineno]+[d.lineno for d in node.decorator_list])-1
    return '\n'.join(text.splitlines()[start:node.end_lineno])+'\n'


def environment(run='781',mode='off',stage='route'):
    return dict(GITHUB_ACTIONS='true',RUNNER_ENVIRONMENT='github-hosted',RUNNER_OS='Linux',
        GITHUB_REPOSITORY=c.REPOSITORY,GITHUB_EVENT_NAME='workflow_dispatch',GITHUB_RUN_ATTEMPT='1',
        GITHUB_SHA='a'*40,GITHUB_RUN_ID=run,GITHUB_REF='refs/heads/'+c.BRANCH,
        **{c.MODE_ENV:mode,c.STAGE_ENV:stage})


def reservation(ctx,assets=()):
    return dict(release_id=19,externally_reserved=True,creation_attempted=False,assets_overwritten=False,
        target_verified=True,tested_source=ctx['source'],tag='cloud-results-'+ctx['token']+'-'+c.group(ctx['mode'],ctx['stage']),
        existing_assets=list(assets))


def native_baseline(method):
    result=copy.deepcopy(method)
    for key in ('source_controls_authorized','native_tail_authorized','native_route_authorized','native_audit_authorized','controller_ready'):
        result[key]=True
    for key in c.AUTH_FALSE:result[key]=False
    return result


def context_controls():
    cases=[];positives=[];base=environment()
    for mode,stage in (('off','route'),('on','route'),('off','audit'),('on','audit'),('compare','compare')):
        env=environment(mode=mode,stage=stage);ctx=c.context(env)
        assert ctx['source']==env['GITHUB_SHA'] and ctx['token']=='781-1'
        assert (ctx['mode'],ctx['stage'])==(mode,stage)
        positives.append(dict(mode=mode,stage=stage,group=c.group(mode,stage)))
    changes=(('GITHUB_ACTIONS','false'),('RUNNER_OS','Windows'),('RUNNER_ENVIRONMENT','self-hosted'),
        ('GITHUB_REPOSITORY','foreign/repo'),('GITHUB_EVENT_NAME','push'),('GITHUB_RUN_ATTEMPT','2'),
        ('GITHUB_RUN_ID','0'),('GITHUB_SHA','main'),('GITHUB_REF','refs/heads/'+c.previous.BRANCH),
        ('GITHUB_REF','refs/heads/main'),('GITHUB_RUN_ATTEMPT',1),
        (c.MODE_ENV,'foreign'),(c.STAGE_ENV,'foreign'),(c.MODE_ENV,'compare'))
    for key,value in changes:
        cases.append(dict(key=key,error=refused(lambda key=key,value=value:c.context({**base,key:value}),'')))
    assert len(positives)==5 and len(cases)==14
    return dict(positive_count=5,refusal_count=14,positives=positives,cases=cases)


def authority_controls(root,method):
    prior=c.decode(c.secure_file(root,c.PRIOR).read_bytes());cases=[];positives=[]
    flags=('source_controls_authorized','native_tail_authorized','native_route_authorized','native_audit_authorized','controller_ready')
    assert len(c.AUTH_FALSE)==8 and c.NEW_FILES and c.PREFIX_REQUIRED
    for label,controls,native in (('disabled',False,False),('controls',True,False),('native',True,True)):
        baseline=copy.deepcopy(method);baseline['source_controls_authorized']=controls
        for key in flags[1:]:baseline[key]=native
        for key in c.AUTH_FALSE:baseline[key]=False
        assert c.validate_method(baseline,prior)==baseline
        positives.append(dict(mode=label,typed_baseline=True))
        mutations=[]
        for key in flags:mutations.append((key+':type',lambda r,key=key:r.update({key:1})))
        for key in c.AUTH_FALSE:mutations.append((key,lambda r,key=key:r.update({key:True})))
        for key in ('source_unit_complete','native_handoff_split_complete'):
            mutations.append((key,lambda r,key=key:r.update({key:False})))
        for key in flags[1:]:mutations.append((key+':split',lambda r,key=key:r.update({key:not native})))
        mutations.extend((('prior_method_sha256',lambda r:r.update(prior_method_sha256='0'*64)),
            ('inherited_count',lambda r:r.update(inherited_protected_count=len(prior['protected'])-1)),
            ('qualified_prefix',lambda r:r['qualified_prefix'].update(source='0'*40)),
            ('new_source_pin',lambda r:r['protected'].pop(c.NEW_FILES[0])),
            ('prefix_proof_pin',lambda r:r['protected'].pop(sorted(c.PREFIX_REQUIRED)[0]))))
        assert len(mutations)==24
        for name,mutate in mutations:
            bad=copy.deepcopy(baseline);mutate(bad)
            assert json.dumps(bad,sort_keys=True)!=json.dumps(baseline,sort_keys=True),(label,name)
            cases.append(dict(mode=label,name=name,error=refused(lambda:c.validate_method(bad,prior),'')))
        for stage in ('route','audit','compare'):
            if native:
                assert c.authorize_stage(baseline,stage)==baseline
                positives.append(dict(mode=label,stage=stage,actual_authorize_stage=True))
            else:
                cases.append(dict(mode=label,stage=stage,error=refused(lambda:c.authorize_stage(baseline,stage),'native tail not authorized')))
    bad=native_baseline(method);bad['source_controls_authorized']=False
    cases.append(dict(mode='native_without_source',error=refused(lambda:c.validate_method(bad,prior),'split authorization')))
    assert len(positives)==6 and len(cases)==79
    return dict(positive_count=6,refusal_count=79,positives=positives,cases=cases,
        controls_execute_no_native=True,both_typed_native_states=True)


def copied_projection(method,base):
    root=base/'projected';root.mkdir()
    for name in [*method['protected'],c.METHOD]:
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(c.secure_file(ROOT,name),target)
    assert c.method(root)==method
    actual=c.prefix_contract(root)
    assert len(actual['files'])==c.FROZEN_COUNT and sum(r['bytes']for r in actual['files'].values())==c.FROZEN_BYTES
    cases=[]
    for name in sorted(c.PREFIX_REQUIRED):
        path=root/name;raw=path.read_bytes()
        try:
            path.write_bytes(raw+b'\n')
            cases.append(dict(path=name,error=refused(lambda:c.prefix_contract(root),'prefix proof bytes: '+name)))
        finally:path.write_bytes(raw)
    receipt=c.saved_path('receipt');path=root/receipt;raw=path.read_bytes()
    for mode in ('missing','symlink'):
        try:
            path.unlink()
            if mode=='symlink':path.symlink_to(root/c.PRIOR)
            cases.append(dict(path=receipt,mode=mode,error=refused(lambda:c.prefix_contract(root),
                'path symlink' if mode=='symlink' else 'missing regular file')))
        finally:
            if path.is_symlink():path.unlink()
            path.write_bytes(raw)
    source_cases=[]
    for name,mode in (('scripts/cloud_mainchip_fixed_engine_route_tail.py','tampered'),
            ('scripts/cloud_mainchip_fixed_engine_route_tail.py','missing'),(c.PRIOR,'tampered'),
            (c.PRIOR,'missing'),('scripts/mainchip_fixed_engine_route_tail_driver.py','symlink')):
        path=root/name;raw=path.read_bytes()
        try:
            if mode=='tampered':path.write_bytes(raw+b'\n')
            else:
                path.unlink()
                if mode=='symlink':path.symlink_to(root/c.PRIOR)
            source_cases.append(dict(path=name,mode=mode,error=refused(lambda:c.method(root),'')))
        finally:
            if path.is_symlink():path.unlink()
            path.write_bytes(raw)
    names=('mainchip_fixed_engine_route_tail_contract','mainchip_fixed_engine_route_tail_driver',
        'mainchip_fixed_engine_route_tail_inner','mainchip_fixed_engine_route_tail_handoff',
        'cloud_mainchip_fixed_engine_route_tail','check_mainchip_fixed_engine_route_tail')
    code='import sys;sys.path.insert(0,sys.argv[1]);'+ ';'.join('import '+x for x in names)+";print('FIXED_TAIL_IMPORT_PASS')"
    child=subprocess.run([sys.executable,'-I','-B','-c',code,str(root/'scripts')],capture_output=True,text=True,timeout=120)
    assert child.returncode==0 and child.stdout.strip()=='FIXED_TAIL_IMPORT_PASS',(child.stdout,child.stderr)
    assert c.method(root)==method and c.prefix_contract(root)==actual
    assert len(cases)==len(c.PREFIX_REQUIRED)+2 and len(source_cases)==5
    return root,dict(positive_count=1,proof_file_count=len(c.PREFIX_REQUIRED),refusal_count=len(cases),
        cases=cases,source_refusal_count=5,source_cases=source_cases,actual_isolated_imports=list(names),
        copied_protected_only=True,recursive_prior_methods_validated=True,
        actual_native_archive_acquired=False,frozen_files=c.FROZEN_COUNT)


def handoff_fixture():
    path='scripts/check_mainchip_built_engine_route_tail_handoff.py'
    raw=c.secure_file(ROOT,path).read_bytes()
    assert c.digest(raw)=='d9f6bca6f5c29b71ac6343e1b82d66711c8ad276814265bb4e127e0beabc1c26'
    original=raw.decode();text=original
    edits=(('import mainchip_built_engine_route_tail_contract as c','import mainchip_fixed_engine_route_tail_contract as c'),
        ('import mainchip_built_engine_route_tail_handoff as h','import mainchip_fixed_engine_route_tail_handoff as h'),
        ('process_group_cleanup=dict(remaining_live=[])',
         'memory_terminal_resolution=None,pid=123,elapsed_seconds=.01,last_memory_sentinel_sample=None,process_group_cleanup=dict(remaining_live=[],remaining_nonrunning=[],signals=[])'))
    for before,after in edits:
        assert text.count(before)==1;text=text.replace(before,after,1)
    assert text.count('746')==4
    text=text.replace('746','c.FROZEN_COUNT')
    reverse=text.replace('c.FROZEN_COUNT','746')
    for before,after in reversed(edits):reverse=reverse.replace(after,before,1)
    assert reverse==original
    namespace={'__file__':str(ROOT/path),'__name__':'fixed_tail_handoff_fixture'}
    exec(compile(text,str(ROOT/path),'exec'),namespace)
    return namespace


def handoff_controls():
    result=handoff_fixture()['controls']()
    assert len(result['positive'])==2 and len(result['refusals'])==12 and len(result['terminal'])==4
    result.update(actual_new_handoff=True,cardinality=c.FROZEN_COUNT,
        namespace_cardinality_and_explicit_synthetic_command_schema_only=True)
    return result


def command_consumer_controls():
    import check_mainchip_exit_checked_supervision as producer
    import check_mainchip_exit_checked_command_evidence as command_fixture
    producer.candidate.source_guard()
    authentic=c.saved(ROOT,'native-prefix-result');before=json.dumps(authentic,sort_keys=True)
    actual=c.validate_prefix_commands(authentic)
    assert len(actual)==4 and all(not x['command_evidence']['terminal_resolution_validated'] for x in actual)
    assert json.dumps(authentic,sort_keys=True)==before
    positives=[dict(case='authentic-prefix-four-ordinary',commands=4,source_bytes_authenticated_by_prefix_contract=True)]
    phase_record,phase_proof=command_fixture.capture(producer,'consumer-resolved-prefix',seconds=1200)
    route_record,route_proof=command_fixture.capture(producer,'consumer-resolved-route',seconds=14400)
    ordinary,ordinary_proof=command_fixture.capture(producer,'consumer-ordinary-route',seconds=14400,exit_at=0)
    child,child_proof=command_fixture.capture(producer,'consumer-known-child-route',seconds=14400,known_child=True)
    phase=copy.deepcopy(authentic)
    phase['commands'][0]=copy.deepcopy(phase_record)
    phase['commands'][0].update(label=authentic['commands'][0]['label'],argv=authentic['commands'][0]['argv'],requested_timeout_seconds=1200)
    memory_before=copy.deepcopy(phase['commands'][0]['memory_terminal_resolution'])
    result=c.validate_prefix_commands(phase)
    assert result[0]['command_evidence']['terminal_resolution_validated']is True
    assert phase['commands'][0]['memory_terminal_resolution']==memory_before and phase['commands'][0]['memory_read_error']
    positives.append(dict(case='actual-resolved-prefix-consumer',producer=phase_proof,diagnostic_retained=True))
    namespace=handoff_fixture();refusals=[]
    with namespace['fixture']('off')as f:
        def framed(record):
            case=copy.deepcopy(f['case']);command=copy.deepcopy(record)
            original=case['commands'][0]
            for key in ('label','argv','requested_timeout_seconds','stdout_sha256','stdout_bytes'):
                command[key]=copy.deepcopy(original[key])
            case['commands']=[command];return case
        route=framed(route_record)
        for name,record,proof in (('ordinary-route',ordinary,ordinary_proof),('resolved-route',route_record,route_proof),
                                 ('resolved-known-child-route',child,child_proof)):
            case=framed(record);before=json.dumps(case,sort_keys=True)
            assert handoff.route_records(f['host'],f['inner'],case,f['request'])is True
            assert before==json.dumps(case,sort_keys=True)
            positives.append(dict(case=name,producer=proof,actual_route_records=True,
                synthetic_route_framing=['label','argv','requested_timeout_seconds','stdout_sha256','stdout_bytes']))
        mutations=(
          ('wrong-error',lambda x:x.update(memory_read_error="CounterError('Persistent unavailable live VmRSS')")),
          ('missing-resolution',lambda x:x.update(memory_terminal_resolution=None)),
          ('cleanup-signal',lambda x:x['process_group_cleanup']['signals'].append('SIGTERM')),
          ('resource-relaxation',lambda x:x.update(minimum_available_kib=1)),
          ('missing-history',lambda x:x['memory_terminal_resolution']['attempts'].pop()),
          ('unknown-identity',lambda x:x['memory_terminal_resolution']['polls'][-1]['census']['scans'][0]['unknown'].append({'pid':999})),
          ('late-command-budget',lambda x:x['memory_terminal_resolution']['command_budget_decision'].update(within_limit=False)),
          ('nonfinite-command-budget',lambda x:x['memory_terminal_resolution']['command_budget_decision'].update(observed_at=float('nan'))))
        for name,base,validate in (('prefix',phase,c.validate_prefix_commands),
                ('route',route,lambda r:handoff.route_records(f['host'],f['inner'],r,f['request']))):
            for fault,edit in mutations:
                bad=copy.deepcopy(base);edit(bad['commands'][0])
                refusals.append(dict(consumer=name,case=fault,error=refused(lambda:validate(bad),'')))
            for fault in ('label','argv','timeout','extra-command'):
                bad=copy.deepcopy(base)
                if fault=='label':bad['commands'][0]['label']='unapproved'
                elif fault=='argv':bad['commands'][0]['argv']=['unapproved']
                elif fault=='timeout':bad['commands'][0]['requested_timeout_seconds']+=1
                else:bad['commands'].append(copy.deepcopy(bad['commands'][0]))
                refusals.append(dict(consumer=name,case=fault,error=refused(lambda:validate(bad),'')))
    assert len(positives)==5 and len(refusals)==24
    return dict(positive_count=5,refusal_count=24,positives=positives,cases=refusals,
        actual_supervised_record_cases=4,actual_prefix_command_consumer=True,actual_route_records=True,
        synthetic_process_proc_clock_io=True,diagnostics_never_cleared=True,native_executed=False,
        physical_acceptance=False)


def current_publication_controls(root,base):
    assert c.method(root)
    path='scripts/check_mainchip_fixed_engine_runtime_host.py'
    raw=c.secure_file(ROOT,path).read_bytes()
    assert c.digest(raw)=='2fdd0a6adf698deb2ebb279985379901de96a05bd4fb371004b63c88d2adcb59'
    body=function(raw.decode(),'publication_controls')
    assert body.count('runtime-probe-evidence.tar.gz')==1
    body=body.replace('runtime-probe-evidence.tar.gz','route-tail-evidence.tar.gz',1)
    groups=[]
    for mode,stage in (('off','route'),('on','route'),('off','audit'),('on','audit')):
        directory=base/(mode+'-'+stage);directory.mkdir()
        def env(run='781',mode=mode,stage=stage):return environment(run,mode,stage)
        ns={**globals(),'h':host,'environment':env,'reservation':reservation}
        exec(compile(body,'<actual-fixed-tail-publication-fixtures>','exec'),ns)
        result=ns['publication_controls'](root,directory)
        assert result['status']=='PASS_ACTUAL_FAILURE_AND_EMPTY_PUBLICATION_CONTROLS' and result['count']==7
        groups.append(dict(mode=mode,stage=stage,group=c.group(mode,stage),result=result))
    assert c.method(root)
    return dict(group_count=4,case_count=28,groups=groups,actual_new_publish_and_pack=True,
        seven_original_fixture_bodies_except_archive_name=True,native_payloads_synthetic=True)


def nested_publication_controls(root,base):
    cases=[]
    for i,mode in enumerate(('nested_bytes','basename_collision','directory_symlink')):
        env=environment(str(950+i),'on','route');env['RUNNER_TEMP']=str(base);ctx=c.context(env)
        assets=[];uploaded={};proof=reservation(ctx);tag=proof['tag'];caught=None
        def read(endpoint):
            if endpoint=='git/ref/tags/'+tag:return dict(ref='refs/tags/'+tag,object=dict(type='commit',sha=ctx['source']))
            assert endpoint=='releases/tags/'+tag
            return dict(id=19,tag_name=tag,target_commitish=ctx['source'],draft=False,prerelease=True,assets=copy.deepcopy(assets))
        def upload(argv,**kwargs):
            assert argv[:4]==['gh','release','upload',tag]
            path=Path(argv[4]);raw=path.read_bytes();assert raw,'zero-byte direct upload'
            uploaded[path.name]=raw
            assets.append(dict(id=100+len(assets),name=path.name,size=len(raw),digest='sha256:'+c.digest(raw)))
            return SimpleNamespace(returncode=0)
        with patch.dict(os.environ,env,clear=False),patch.object(host,'ROOT',root):
            work=host.owned_work(ctx,True);out=work/'out';out.mkdir()
            (out/'host-result.json').write_bytes(b'{"explicit_synthetic_record":true}')
            (out/'supervision').mkdir();(out/'witness').mkdir()
            (out/'supervision/route.stdout').write_bytes(b'synthetic complete route stdout\n')
            (out/'supervision/route.stderr').write_bytes(b'')
            (out/'witness/before_dr.jsonl').write_bytes(b'{"synthetic":true}\n')
            originals={p.relative_to(out).as_posix():p.read_bytes()for p in out.rglob('*')if p.is_file()}
            if mode=='basename_collision':(out/'supervision/host-result.json').write_bytes(b'collision')
            elif mode=='directory_symlink':
                shutil.rmtree(out/'witness');(out/'witness').symlink_to(out/'supervision',target_is_directory=True)
            with patch.object(host.reservation,'wait',return_value=proof),patch.object(host.reservation.release,'api',side_effect=read),patch.object(host.subprocess,'run',side_effect=upload):
                try:assert host.publish()==0
                except BaseException as exc:caught=exc
            if mode=='nested_bytes':
                assert caught is None,repr(caught)
                plan=c.decode((out/'direct-publication-plan.json').read_bytes())
                rows={x['name']:x for x in plan['files']}
                assert rows['supervision/route.stderr']['disposition']=='archive_only_empty'
                for path in ('supervision/route.stdout','witness/before_dr.jsonl'):
                    assert rows[path]['disposition']=='direct' and rows[path]['asset_name']==Path(path).name
                    assert uploaded[Path(path).name]==originals[path]
                assert 'route.stderr'not in uploaded
                with tarfile.open(work/'route-tail-evidence.tar.gz','r:gz')as tar:
                    for name,raw in originals.items():assert tar.extractfile(name).read()==raw
                output=c.decode((out/'outputs.json').read_bytes())
                assert (output['mode'],output['stage'],output['source'])==('on','route',ctx['source'])
                for name,raw in originals.items():assert output['files'][name]==dict(bytes=len(raw),sha256=c.digest(raw))
            else:
                reason='duplicate direct asset basename'if mode=='basename_collision'else'direct publication directory symlink'
                assert caught is not None and reason in str(caught),(mode,repr(caught))
                assert uploaded=={} and not(out/'publication.json').exists()
            cases.append(dict(case=mode,error=None if caught is None else repr(caught),synthetic_transport=True))
    return dict(positive_count=1,refusal_count=2,case_count=3,cases=cases,
        relative_archive_path_and_direct_basename_join=True)


def derivation_controls():
    for path,expected in DERIVATION_SOURCES.items():
        raw=c.secure_file(ROOT,path).read_bytes()
        assert dict(bytes=len(raw),sha256=c.digest(raw))==expected,path
    pairs={role:(("scripts/cloud_mainchip_built_engine_route_tail.py"if role=='host'else
        'scripts/mainchip_built_engine_route_tail_'+role+'.py'),
        ("scripts/cloud_mainchip_fixed_engine_route_tail.py"if role=='host'else
        'scripts/mainchip_fixed_engine_route_tail_'+role+'.py'))for role in ('host','driver','native','inner','handoff')}
    preserved={'host':('comparison_body','comparison','publish_asset'),
        'driver':('execute_tail','observer_result'),'native':('raw_pairs',),
        'inner':('write','cgroup','stop_child','run','finish_cgroup','dependencies')}
    checked=[]
    for role,(before,after)in pairs.items():
        old=c.secure_file(ROOT,before).read_text();new=c.secure_file(ROOT,after).read_text()
        for name in preserved.get(role,()):
            assert function(old,name)==function(new,name),(role,name);checked.append(role+'.'+name)
        if role=='driver':
            edits=(('import mainchip_built_engine_route_tail_contract as c','import mainchip_fixed_engine_route_tail_contract as c'),
                ('import cloud_mainchip_original_clock_restoration as old','import mainchip_exit_checked_supervision as old'),
                ('c.require(c.method(WORK/"tail-source")["native_"+stage+"_authorized"],"stage not authorized")',
                 'c.authorize_stage(c.method(WORK/"tail-source"),stage)'))
            expected=old
            for before,after in edits:
                assert expected.count(before)==1;expected=expected.replace(before,after,1)
            assert new==expected,'driver exact import/authority derivation'
        if role=='handoff':
            before_import='import mainchip_built_engine_route_tail_contract as c'
            after_import='import mainchip_fixed_engine_route_tail_contract as c'
            expected=old.replace(before_import,after_import,1)
            before_guard='    c.require(command["supervision_failure"] is None and command["memory_read_error"] is None\n        and command["process_group_cleanup"]["remaining_live"]==[],"route owned process completion")'
            after_guard='    qualification=c.command_evidence.validate(command,14400)\n    c.require(qualification["requested_timeout_bound"]is True,"route declared command timeout")'
            assert expected.count(before_guard)==1
            assert new==expected.replace(before_guard,after_guard,1),'handoff exact command consumer derivation'
            checked.extend('handoff.'+x for x in ('validate_manifest','freeze','restore','route_projection','part_manifest','live_route'))
    old=c.secure_file(ROOT,'scripts/mainchip_built_engine_route_tail_contract.py').read_text()
    new=c.secure_file(ROOT,'scripts/mainchip_fixed_engine_route_tail_contract.py').read_text()
    for name in ('complete','compare_cases','frozen_unchanged','stage_limits'):
        assert function(old,name)==function(new,name),name;checked.append('contract.'+name)
    assert function(new,'command')==function(old,'command').replace('mainchip_built_engine_route_tail_native.py','mainchip_fixed_engine_route_tail_native.py')
    def value(text,name):
        return next(n.value for n in ast.parse(text).body if isinstance(n,ast.Assign)and
            any(isinstance(t,ast.Name)and t.id==name for t in n.targets))
    for name in ('LIMITS','PHASES','STATUSES','COMPARE_FILES'):
        assert ast.dump(value(old,name),include_attributes=False)==ast.dump(value(new,name),include_attributes=False),name
    return dict(wrapper_count=5,exact_source_count=len(DERIVATION_SOURCES),preserved_functions=checked,
        handoff_only_contract_import_and_command_evidence_changed=True,original_limits_and_comparison_preserved=True,
        actual_native_executed=False)


def controls(method):
    result=dict(status='PASS_FIXED_ENGINE_ROUTE_TAIL_SOURCE_CONTROLS',protected_count=len(method['protected']),
        source_only=True,native_executed=False,native_routing_executed=False,physical_acceptance=False,
        complete_native_qualification=False,observer_equivalence_qualified=False)
    result['derivation']=derivation_controls()
    result['context_controls']=context_controls()
    result['authority_controls']=authority_controls(ROOT,method)
    result['envelope']=envelope_controls()
    result['restore']=restore_controls()
    result['sequence']=sequence_controls()
    result['observer']=observer_controls()
    result['comparison']=comparison_controls()
    result['lifecycle']=lifecycle_controls(method,'audit')+lifecycle_controls(method,'route')
    result['handoff']=handoff_controls()
    result['command_consumers']=command_consumer_controls()
    result['asset_publication']=publication_controls()
    with tempfile.TemporaryDirectory()as d:
        base=Path(d);fixture,projection=copied_projection(method,base)
        result['source_projection']=projection
        result['publication']=current_publication_controls(fixture,base)
        result['split_publication']=split_publication_controls(fixture)
        result['nested_publication']=nested_publication_controls(fixture,base)
        assert c.method(fixture)==method
    assert len(result['envelope']['refusals'])==10 and len(result['restore'])==4
    assert len(result['sequence']['stops'])==6 and result['sequence']['gate_refusals']==4
    assert result['observer']['positive']==3 and len(result['observer']['refusals'])==3
    assert len(result['lifecycle'])==16 and len(result['comparison']['geometry_mismatches'])==10
    assert len(result['split_publication'])==4 and result['nested_publication']['case_count']==3
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    result=dict(status='FAIL_FIXED_ENGINE_ROUTE_TAIL_SOURCE_CONTROLS',source_only=True,
        native_executed=False,native_routing_executed=False,physical_acceptance=False,
        complete_native_qualification=False,observer_equivalence_qualified=False)
    primary=None
    try:
        ctx=c.context(os.environ);method=c.method(ROOT)
        c.require(method['source_controls_authorized']is True,'current tail source controls not authorized')
        result=controls(method)
        result['current_context']=dict(source=ctx['source'],run_id=int(os.environ['GITHUB_RUN_ID']),attempt=1,
            mode=ctx['mode'],stage=ctx['stage'],source_controls_only=True,native_executed=False)
    except BaseException as exc:
        primary=exc;result['status']='FAIL_FIXED_ENGINE_ROUTE_TAIL_SOURCE_CONTROLS'
        result['failure']=dict(type=type(exc).__name__,error=repr(exc),traceback=traceback.format_exc())
    finally:
        save_error=None;emit_error=None
        try:
            raw=(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
            output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(raw)
        except BaseException as exc:
            save_error=exc;result['status']='FAIL_FIXED_ENGINE_ROUTE_TAIL_SOURCE_CONTROLS'
            result['report_write_error']=dict(type=type(exc).__name__,error=repr(exc))
        try:print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
        except BaseException as exc:emit_error=exc
        if primary is not None:raise primary
        if save_error is not None:raise save_error
        if emit_error is not None:raise emit_error
    if primary is not None:raise primary
    return 0

if __name__=='__main__':raise SystemExit(main())
