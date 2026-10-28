#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only controls of prefix ordering, original gates and zero router dispatch."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
import mainchip_built_engine_route_prefix_contract as c
import mainchip_built_engine_route_prefix_driver as driver
import mainchip_two_signal_repair as repair
ROOT=Path(__file__).resolve().parent.parent
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
    assert (len(positive),len(refusals),len(sequences))==(4,23,6)
    print(json.dumps(dict(status="PASS_SHARED_PREFIX_SOURCE_CONTROLS",positive_count=4,refusal_count=23,
        sequencing_cases=sequences,positive=positive,refusals=refusals,protected_count=len(method["protected"]),
        mocked_native_boundary=True,real_ownership_solver_requalified_by_fixtures=False,
        native_prefix_executed=False,native_routing_executed=False,physical_acceptance=False),sort_keys=True,indent=2))
if __name__=="__main__":main()
