#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted metadata/refusal and actual helper controls; no native qualification claim."""
import argparse,ast,copy,json,os,traceback
from pathlib import Path
import mainchip_antenna_escape_window as p
import cloud_mainchip_antenna_escape_window as host
import mainchip_fixed_engine_route_tail_contract as c
ROOT=Path(__file__).resolve().parents[1]
PREFIX="docs/evidence/mainchip-single-antenna-trial-terminal-41001185417/"
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True,type=Path);args=parser.parse_args()
    ctx=host.context(os.environ);records=[];primary=None
    def positive(name,call):
        value=call();records.append(dict(case=name,kind="positive"));return value
    def refuse(name,call):
        try:call()
        except (AssertionError,KeyError,TypeError,ValueError)as exc:
            records.append(dict(case=name,kind="refusal",error=repr(exc)));return
        raise AssertionError("accepted invalid case "+name)
    try:
        host.source_gate()
        values=[json.loads((ROOT/(PREFIX+n)).read_bytes())for n in ("run.json","jobs.json","release.json","release-ref.json")]
        positive("actual rejected trial metadata is diagnostic only",lambda:p.producer_binding(*values))
        changes=[
          ("run source",0,lambda x:x.update(head_sha="0"*40)),
          ("attempt",0,lambda x:x.update(run_attempt=2)),
          ("conclusion",0,lambda x:x.update(conclusion="failure")),
          ("workflow",0,lambda x:x.update(workflow_id=1)),
          ("job missing",1,lambda x:x["jobs"].pop()),
          ("duplicate job",1,lambda x:x["jobs"].__setitem__(0,copy.deepcopy(x["jobs"][1]))),
          ("job source",1,lambda x:x["jobs"][0].update(head_sha="0"*40)),
          ("job conclusion",1,lambda x:x["jobs"][0].update(conclusion="failure")),
          ("release source",2,lambda x:x.update(target_commitish="0"*40)),
          ("release draft",2,lambda x:x.update(draft=True)),
          ("asset missing",2,lambda x:x["assets"].pop()),
          ("asset digest",2,lambda x:x["assets"][0].update(digest="sha256:"+"0"*64)),
          ("asset bytes",2,lambda x:x["assets"][0].update(size=0)),
          ("ref source",3,lambda x:x["object"].update(sha="0"*40)),
          ("ref type",3,lambda x:x["object"].update(type="tag"))]
        for label,index,mutate in changes:
            bad=copy.deepcopy(values);mutate(bad[index])
            refuse(label,lambda bad=bad:p.producer_binding(*bad))
        for label,a,b,want in [
          ("positive overlap",[0,0,10,10],[9,9,20,20],True),
          ("closed edge kept",[0,0,10,10],[10,0,20,10],True),
          ("closed corner kept",[0,0,10,10],[10,10,20,20],True),
          ("outside omitted",[0,0,10,10],[11,0,20,10],False),
          ("containing box unclipped",[-10,-10,30,30],[0,0,10,10],True)]:
            def check(a=a,b=b,want=want):
                before=copy.deepcopy((a,b));assert p.intersects(a,b)is want and p.intersects(b,a)is want
                assert (a,b)==before
            positive(label,check)
        for label,b in [("zero box",[0,0,0,10]),("inverted",[10,0,0,10]),("float",[0,0,10.0,10]),("bool",[False,0,10,10]),("dimension",[0,0,10])]:
            refuse(label,lambda b=b:p.intersects(b,[0,0,10,10]))
        def segments(path):
            raw=(ROOT/path).read_text()
            return {n.name:ast.get_source_segment(raw,n)for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
        a=segments("scripts/mainchip_single_antenna_trial_inner.py");b=segments("scripts/mainchip_antenna_escape_window_inner.py")
        assert a["run"].replace('"trial-','"window-')==b["run"],"qualified process finalizer changed"
        a=segments("scripts/cloud_mainchip_single_antenna_trial.py");b=segments("scripts/cloud_mainchip_antenna_escape_window.py")
        for name in ("derived_path","preserve_outputs","retained_workspace"):
            assert a[name]==b[name],"qualified preservation changed"
        records.append(dict(case="actual qualified child cleanup and output preservation unchanged",kind="positive"))
        report=dict(status="PASS_ANTENNA_ESCAPE_WINDOW_SOURCE_CONTROLS",records=records,
          positive_count=sum(r["kind"]=="positive"for r in records),
          refusal_count=sum(r["kind"]=="refusal"for r in records),
          context=ctx,native_executed=False,native_geometry_mocked_or_qualified=False,
          physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,terminal_errors=[])
    except BaseException as e:
        primary=e;report=dict(status="FAIL_ANTENNA_ESCAPE_WINDOW_SOURCE_CONTROLS",records=records,
          error=repr(e),traceback=traceback.format_exc(),context=ctx,terminal_errors=[],native_executed=False,
          physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
    c.finish_record(args.output,report,"FAIL_ANTENNA_ESCAPE_WINDOW_SOURCE_CONTROLS",primary)
    if primary is not None:raise primary
if __name__=="__main__":main()
