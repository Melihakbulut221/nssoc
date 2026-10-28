#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only controls of prefix ordering, original gates and zero router dispatch."""
import ast
import copy
from contextlib import ExitStack
import json
from pathlib import Path
import signal
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import mainchip_built_engine_route_prefix_contract as c
import mainchip_built_engine_route_prefix_driver as driver
import mainchip_two_signal_repair as repair
from mainchip_witness_engine_build_contract import inventory
ROOT=Path(__file__).resolve().parent.parent

def lifecycle_controls(records):
    """Actual driver main/finally and qualified writer; synthetic native/thread/signal collaborators."""
    results=[]
    old_cleanup='            def heartbeat_stop():\n                sup.STOP.set()\n                if beat is not None:\n                    beat.join(timeout=5)\n                    c.require(not beat.is_alive(),"heartbeat remained live")\n            c.attempt(report,"heartbeat-stop",heartbeat_stop)\n'
    new_cleanup='            c.attempt(report,"heartbeat-stop",lambda:sup.STOP.set())\n            def heartbeat_join():\n                if beat is not None:\n                    beat.join(timeout=5)\n                    c.require(not beat.is_alive(),"heartbeat remained live")\n            c.attempt(report,"heartbeat-join",heartbeat_join)\n'
    original_main_sha="316293dbf737eefd8fbf6b90385537e0d32732961b1d87513ffb5a29587dbb5d"
    def one(name,faults=(),body_failure=False,original=False):
        with tempfile.TemporaryDirectory(prefix="prefix-main-controls-") as temporary:
            root=Path(temporary);out=root/"out";out.mkdir();work=out/"work";source=root/"source"
            events=[];method_calls=[];seen_commands=[]
            primary=RuntimeError("injected native body failure: "+name)
            failures={key:RuntimeError("injected "+key+": "+name) for key in faults}
            interrupted_handlers={signal.SIGINT:object(),signal.SIGTERM:object()}
            original_handlers=dict(interrupted_handlers)
            thread_instances=[]
            def fail(key):
                events.append(key)
                if key in failures:raise failures[key]
            def stop_process(active):
                assert active is supervisor.ACTIVE
                fail("owned-native-process-cleanup")
            def stop_event():fail("heartbeat-stop")
            class Thread:
                def __init__(self,*,target,daemon):
                    assert target==supervisor.heartbeat and daemon is True
                    thread_instances.append(self);self.started=False;self.joined=False
                def start(self):self.started=True;events.append("heartbeat-start")
                def join(self,timeout):
                    assert self.started and timeout==5
                    self.joined=True;fail("heartbeat-join")
                def is_alive(self):
                    events.append("heartbeat-is-alive")
                    return "heartbeat-remains-live" in faults
            supervisor=SimpleNamespace(
                SECONDS=1200,MAX_GROUP_RSS_KIB=10485760,MIN_AVAILABLE_KIB=2097152,
                ACTIVE=object(),STOP=SimpleNamespace(set=stop_event),
                stop_process=stop_process,heartbeat=lambda:None,interrupted=lambda *args:None)
            def paths(value):
                return {"/work/out":out,"/work/out/work":work,"/work/source":source}[str(value)]
            def method(root):
                assert root==source
                method_calls.append(str(root));events.append("method:"+str(len(method_calls)))
                return {"native_prefix_authorized":True}
            def signal_call(sig,handler):
                prior=interrupted_handlers[sig];interrupted_handlers[sig]=handler
                events.append(("install-signal:" if handler is supervisor.interrupted else "restore-signal:")+str(sig))
                return prior
            def command(sup,argv,phase):
                assert sup is supervisor and argv==c.command(phase,"/work/engine/openroad")
                assert driver.os.environ["NSSOC_TWO_SIGNAL_OUT"]==c.CANONICAL_OUT
                assert driver.os.environ["NSSOC_TWO_SIGNAL_FAILED_SOURCE"]=="/work/input-transport/selected"
                if phase=="paired-all-nontarget-fixed-import":
                    assert "NSSOC_TWO_SIGNAL_PHASE" not in driver.os.environ
                else:assert driver.os.environ["NSSOC_TWO_SIGNAL_PHASE"]==phase
                seen_commands.append(phase)
                (work/"partial.native-bytes").write_bytes(b"synthetic native partial\x00\xff")
                if body_failure:raise primary
                if phase=="ownership":c.atomic_record(work/"ownership.json",{"synthetic_boundary":True})
                if phase in records:c.atomic_record(work/(phase+"-result.json"),records[phase])
                return dict(label=phase,returncode=0,synthetic_native_command=True)
            caught=None;code=None
            env_before=dict(driver.os.environ)
            with ExitStack() as stack:
                stack.enter_context(patch.object(driver,"Path",side_effect=paths))
                stack.enter_context(patch.object(c,"method",side_effect=method))
                stack.enter_context(patch.object(driver.old,"supervisor",return_value=supervisor))
                stack.enter_context(patch.object(driver.threading,"Thread",Thread))
                stack.enter_context(patch.object(driver.signal,"signal",side_effect=signal_call))
                stack.enter_context(patch.object(driver.controller,"execute_command",side_effect=command))
                stack.enter_context(patch.object(repair,"require_actionable",return_value=True))
                stack.enter_context(patch.dict(driver.os.environ,{},clear=True))
                fn=driver.main
                if original:
                    raw=(ROOT/"scripts/mainchip_built_engine_route_prefix_driver.py").read_text()
                    node=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=="main")
                    current=ast.get_source_segment(raw,node)
                    assert current.count(new_cleanup.rstrip("\n"))==1
                    frozen=current.replace(new_cleanup.rstrip("\n"),old_cleanup.rstrip("\n"))
                    assert c.digest(frozen.encode())==original_main_sha
                    namespace=dict(driver.__dict__)
                    exec(compile(frozen,"<frozen-route-prefix-main-31dd6f0d>","exec"),namespace)
                    fn=namespace["main"]
                try:code=fn()
                except BaseException as exc:caught=exc
            assert dict(driver.os.environ)==env_before
            assert interrupted_handlers==original_handlers
            assert len(method_calls)==2 and method_calls[0]==method_calls[1]
            assert len(thread_instances)==1 and thread_instances[0].started
            saved=json.loads((out/"native-prefix-result.json").read_bytes())
            assert c.decode((out/"native-prefix-result.json").read_bytes())==saved
            assert saved["available_outputs"]==inventory(out,("native-prefix-result.json",))
            assert saved["available_outputs"]["work/partial.native-bytes"]["sha256"]==c.digest(b"synthetic native partial\x00\xff")
            expected_actions=["owned-native-process-cleanup","heartbeat-stop"]
            if not original:expected_actions.append("heartbeat-join")
            expected_actions.extend(["restore-signal-"+str(signal.SIGINT),"restore-signal-"+str(signal.SIGTERM),"protected-source-terminal"])
            assert [a["action"] for a in saved["terminal_actions"]]==expected_actions
            expected_errors=[key for key in expected_actions if key in faults]
            if "heartbeat-remains-live" in faults:expected_errors.append("heartbeat-join")
            assert [row["action"] for row in saved["terminal_errors"]]==expected_errors
            for key in expected_errors:
                row=next(row for row in saved["terminal_errors"] if row["action"]==key)
                if key in failures:assert row["error"]==repr(failures[key])
                else:assert "heartbeat remained live" in row["error"]
            if original:
                assert "heartbeat-stop" in faults and thread_instances[0].joined is False
                assert "heartbeat-join" not in events
            else:assert thread_instances[0].joined is True
            failed=body_failure or bool(faults)
            assert saved["status"]==("FAIL_ACTUAL_BUILT_ENGINE_SHARED_PREFIX" if failed else "PASS_ACTUAL_BUILT_ENGINE_SHARED_PREFIX")
            assert saved["native_routing_executed"] is False
            assert saved["physical_acceptance"] is False and saved["observer_equivalence_qualified"] is False
            if body_failure:
                assert caught is primary and code is None
                assert saved["primary_exception"]["error"]==repr(primary)
                assert seen_commands==["ownership"] and not saved.get("complete_shared_prefix",False)
            else:
                assert caught is None and code==(1 if failed else 0)
                assert seen_commands==list(c.PHASES) and saved["complete_shared_prefix"] is True
            results.append(dict(case=name,actual_driver_main=True,original_regression=original,
                synthetic_native_thread_signal_and_admission=True,
                commands=seen_commands,terminal_actions=saved["terminal_actions"],
                terminal_errors=saved["terminal_errors"],status=saved["status"],
                original_primary_preserved=body_failure and caught is primary,
                heartbeat_join_attempted=thread_instances[0].joined,
                available_outputs=saved["available_outputs"]))
    one("exact-original-stop-failure-skips-join",("heartbeat-stop",),original=True)
    one("complete")
    one("body-only",body_failure=True)
    one("process-stop-failure",("owned-native-process-cleanup",))
    one("heartbeat-stop-failure",("heartbeat-stop",))
    one("heartbeat-join-failure",("heartbeat-join",))
    one("heartbeat-still-live",("heartbeat-remains-live",))
    one("body-and-independent-cleanup-failures",
        ("owned-native-process-cleanup","heartbeat-stop","heartbeat-join"),body_failure=True)
    assert len(results)==8
    return results

def main():
    method=c.method(ROOT);positive=[];refusals=[];sequences=[]
    def refuse(name,fn,reason):
        try:fn()
        except (AssertionError,ValueError)as exc:
            assert reason in str(exc),(name,str(exc),reason)
            refusals.append(dict(name=name,reason=str(exc)))
        else:raise AssertionError("unexpected acceptance: "+name)
    env=dict(GITHUB_ACTIONS="true",RUNNER_OS="Linux",GITHUB_REPOSITORY=c.REPOSITORY,
        GITHUB_RUN_ATTEMPT="1",GITHUB_RUN_ID="123",GITHUB_SHA="a"*40,GITHUB_REF="refs/heads/"+c.BRANCH)
    c.context(env);positive.append("exact hosted prefix context")
    for key,value,reason in [
        ("GITHUB_ACTIONS","false","hosted"),("RUNNER_OS","Windows","hosted"),
        ("GITHUB_REPOSITORY","foreign/repo","repository"),("GITHUB_RUN_ATTEMPT","2","no retry"),
        ("GITHUB_RUN_ID","0","run identity"),("GITHUB_SHA","main","source identity"),
        ("GITHUB_REF","refs/heads/"+c.previous.BRANCH,"route prefix branch")]:
        refuse(key,lambda key=key,value=value:c.context({**env,key:value}),reason)
    expected={
        "ownership":["/work/engine/openroad","-no_init","-exit","-python","/work/source/scripts/mainchip_two_signal_repair_native.py"],
        "prepare-fixed":["/work/engine/openroad","-no_init","-exit","-python","/work/source/scripts/mainchip_two_signal_repair_native.py"],
        "paired-all-nontarget-fixed-import":["/work/engine/openroad","-no_init","-exit","/work/out/work/fixed.tcl"],
        "fixed-audit":["/work/engine/openroad","-no_init","-exit","-python","/work/source/scripts/mainchip_two_signal_repair_native.py"]}
    assert {p:c.command(p,"/work/engine/openroad")for p in c.PHASES}==expected
    positive.append("exact four commands and canonical paths")
    for phase in ("one-two-signal-routing-attempt","route-audit","unfix-audit","drc-audit","../ownership",None):
        refuse("unapproved "+str(phase),lambda phase=phase:c.command(phase,"/work/engine/openroad"),"unapproved prefix phase")
    refuse("foreign engine",lambda:c.command("ownership","/tmp/openroad"),"canonical native paths")
    refuse("foreign workspace",lambda:c.command("ownership","/work/engine/openroad","/work/other"),"canonical native paths")
    records={phase:dict(status=status,accepted=False,timing_accepted=False,full_phy_accepted=False)
             for phase,status in c.PASS_STATUSES.items()}
    records["ownership"]["original_gate"]=dict(result=dict(clock_or_fixed_nets=1691,all_source_clock_and_fixed_records_preserved=True))
    records["fixed-audit"]["router_census"]=dict(two_routed_nonfixed_guided_names=list(repair.TARGETS))
    events=[]
    def read(phase):events.append("read:"+phase);return copy.deepcopy(records[phase])
    result=driver.execute_prefix(lambda phase,argv:events.append("execute:"+phase),read,lambda:events.append("actionable"))
    assert result==records
    assert events==["execute:ownership","read:ownership","actionable",
        "execute:prepare-fixed","read:prepare-fixed","execute:paired-all-nontarget-fixed-import",
        "execute:fixed-audit","read:fixed-audit"]
    sequences.append(dict(case="complete",events=events));positive.append("complete ordered shared prefix")
    for failed in c.PHASES:
        events=[]
        def execute(phase,argv):
            events.append("execute:"+phase)
            if phase==failed:raise RuntimeError("phase sentinel")
        try:driver.execute_prefix(execute,read,lambda:events.append("actionable"))
        except RuntimeError as exc:assert str(exc)=="phase sentinel"
        else:raise AssertionError("phase failure was lost")
        assert [x.removeprefix("execute:")for x in events if x.startswith("execute:")]==list(c.PHASES[:c.PHASES.index(failed)+1])
        sequences.append(dict(case="failure:"+failed,events=events))
    events=[]
    def denied():events.append("actionable-denied");raise AssertionError("ownership denied")
    refuse("ownership prevents mutation",lambda:driver.execute_prefix(
        lambda phase,argv:events.append("execute:"+phase),read,denied),"ownership denied")
    assert events==["execute:ownership","read:ownership","actionable-denied"]
    sequences.append(dict(case="ownership-denied",events=events))
    events=[]
    def wrong(phase):return dict(records[phase],status="FAIL")
    refuse("failed status stops next command",lambda:driver.execute_prefix(
        lambda phase,argv:events.append(phase),wrong,lambda:None),"native prefix phase did not pass")
    assert events==["ownership"]
    # The unchanged ownership solver is explicitly mocked in these boundary fixtures.
    # Real native ownership remains mandatory in the hosted prefix and is never synthesized.
    with patch.object(repair,"require_actionable",return_value=True)as ownership:
        summary=c.prefix_complete(records,{"synthetic_boundary":True})
        ownership.assert_called_once_with({"synthetic_boundary":True})
        assert summary["original_clock_count"]==1691 and summary["native_routing_executed"]is False
        positive.append("nested actual clock gate boundary")
        for name,mutate,reason in [
            ("missing phase",lambda r:r.pop("fixed-audit"),"prefix result census"),
            ("wrong phase status",lambda r:r["ownership"].update(status="FAIL"),"prefix phase status/scope"),
            ("false physical claim",lambda r:r["fixed-audit"].update(full_phy_accepted=True),"prefix phase status/scope"),
            ("lost clock",lambda r:r["ownership"]["original_gate"]["result"].update(clock_or_fixed_nets=1690),"original clock gate"),
            ("changed clock",lambda r:r["ownership"]["original_gate"]["result"].update(all_source_clock_and_fixed_records_preserved=False),"original clock gate"),
            ("extra mutable net",lambda r:r["fixed-audit"]["router_census"].update(two_routed_nonfixed_guided_names=[*repair.TARGETS,"clock"]),"two-target routing boundary")]:
            changed=copy.deepcopy(records);mutate(changed)
            refuse(name,lambda changed=changed:c.prefix_complete(changed,{}),reason)
    lifecycle=lifecycle_controls(records)
    assert (len(positive),len(refusals),len(sequences),len(lifecycle))==(4,23,6,8)
    print(json.dumps(dict(status="PASS_SHARED_PREFIX_SOURCE_CONTROLS",positive_count=4,refusal_count=23,
        sequencing_cases=sequences,lifecycle_cases=lifecycle,lifecycle_count=8,
        positive=positive,refusals=refusals,protected_count=len(method["protected"]),
        mocked_native_boundary=True,real_ownership_solver_requalified_by_fixtures=False,
        native_prefix_executed=False,native_routing_executed=False,physical_acceptance=False),sort_keys=True,indent=2))
if __name__=="__main__":main()
