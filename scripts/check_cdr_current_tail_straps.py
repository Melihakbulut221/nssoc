#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud source controls for exact current tail geometry and failure preservation."""
import ast,copy,json,os
from pathlib import Path
import cdr_current_tail_straps as plan
import cloud_cdr_current_tail_straps as host

def main():
    ctx=host.context(os.environ);rows=[]
    def eq(a,b):assert a==b,(a,b)
    def ok(name,fn):
        fn();assert name not in rows;rows.append(name)
    def refuse(name,fn):
        def test():
            try:fn()
            except (AssertionError,ValueError,KeyError):return
            raise AssertionError("accepted "+name)
        ok(name,test)
    def source():
        host.source_guard(ctx)
        for name in("scripts/cdr_current_tail_straps.py","scripts/cdr_current_tail_straps_native.py",
                    "scripts/cloud_cdr_current_tail_straps.py"):
            tree=ast.parse((host.ROOT/name).read_bytes())
            if "cloud_"in name:
                guards=[node for node in tree.body if isinstance(node,ast.If)and
                    isinstance(node.test,ast.Compare)and isinstance(node.test.left,ast.Name)and node.test.left.id=="__name__"]
                eq(len(guards),1)
    ok("tail exact current source and single entrypoint",source)
    ok("tail exact geometry plan survives JSON",lambda:eq(json.loads(json.dumps(plan.local_plan())),plan.local_plan()))
    def anchor(device):
        return dict(label="T%03d_D"%device,metal=8,native_cluster=plan.TARGETS[device][0],
                    detail=dict(terminal="D"),point_dbu=[1000,2000])
    ok("tail all eight native target identities",lambda:[plan.validate_target(n,anchor(n),"sg13_lv_nmos",*plan.TARGETS[n])for n in plan.TARGETS])
    for field,value,name in (("model","npn13g2","model"),("owner",999,"owner"),("terminal","G","terminal"),("metal",10,"metal"),("point",1.5,"coordinate")):
        def bad(field=field,value=value):
            a=anchor(3);model="sg13_lv_nmos";cluster,label=plan.TARGETS[3]
            if field=="model":model=value
            elif field=="owner":cluster=value
            elif field=="terminal":a["detail"]["terminal"]=value
            elif field=="metal":a["metal"]=value
            else:a["point_dbu"][0]=value
            plan.validate_target(3,a,model,cluster,label)
        refuse("tail rejects wrong "+name,bad)
    cfg=host.config();producer=host.r.source_guard()
    summary,parts,original=host.r.metadata(producer,"nominal_early")
    ok("tail selects all42 exact current input metadata",lambda:eq(len(plan.input_names(cfg,summary["outputs"])),42))
    for kind in("missing_member","wrong_hash","wrong_producer","old_gds","old_lvs","changed_plan"):
        def bad(kind=kind):
            c=copy.deepcopy(cfg)
            if kind=="missing_member":c["members"].pop(next(iter(c["members"])))
            elif kind=="wrong_hash":c["members"][next(iter(c["members"]))]["sha256"]="0"*64
            elif kind=="wrong_producer":c["producer_run"]=40830441311
            elif kind=="old_gds":c["current_geometry"]["gds_sha256"]="0"*64
            elif kind=="old_lvs":c["current_geometry"]["lvs_sha256"]="0"*64
            else:c["plan"]["metal2"][0]+=5
            plan.input_names(c,summary["outputs"])
        refuse("tail rejects "+kind,bad)
    for key,value in(("GITHUB_REF","refs/heads/unrelated"),("GITHUB_RUN_ATTEMPT","2")):
        refuse("tail rejects changed "+key,lambda key=key,value=value:host.context({**os.environ,key:value}))
    def lifecycle(primary_failure=False,integrity_failure=False,writer_failure=False):
        seen=[];sentinel=RuntimeError("actual-test-action-failure")
        report=dict(status="IN_PROGRESS",terminal_errors=[])
        def action():
            seen.append("action")
            if primary_failure:raise sentinel
            report["status"]="COMPLETE_SOURCE_ONLY"
        def integrity():
            seen.append("integrity")
            if integrity_failure:raise ValueError("intentional source integrity failure")
        def writer(value):
            seen.append("writer")
            if writer_failure:raise OSError("intentional write failure")
        error=None
        try:host.terminal_body(action,integrity,writer,report)
        except BaseException as exc:error=exc
        eq(seen,["action","integrity","writer"])
        if primary_failure:assert error is sentinel
        elif integrity_failure or writer_failure:assert error is not None
        else:assert error is None
        if primary_failure or integrity_failure or writer_failure:eq(report["status"],"FAIL_CURRENT_EIGHT_DRAIN_PHYSICAL_TRIAL")
        return report
    ok("tail primary survives independent integrity and writer failures",lambda:lifecycle(True,True,True))
    ok("tail integrity failure cannot become success",lambda:lifecycle(integrity_failure=True))
    ok("tail successful lifecycle retains all terminal actions",lambda:lifecycle())
    root=Path("cdr-drain-wave-source-controls")
    records={key:json.loads((root/name).read_bytes())for key,name in
      (("controls","controls.json"),("publication","publication-controls.json"),
       ("ownership","ownership-controls.json"),("execution","execution-controls.json"))}
    fixture=dict(status="PASS_CURRENT_EIGHT_DRAIN_SOURCE_CONTROLS",count=30,passed_cases=["fixture-%02d"%n for n in range(30)],
      source=ctx["source"],run_id=ctx["run_id"],attempt=1,native_executed=False,**plan.FLAGS)
    ok("tail binds all original165 and new source groups",lambda:host.bind_controls(ctx,{**records,"tail":fixture}))
    refuse("tail refuses stale source group",lambda:host.bind_controls(ctx,{**records,"tail":{**fixture,"source":"0"*40}}))
    assert len(rows)==22 and len(set(rows))==22
    ok("tail unblocked segment retains entire envelope",lambda:eq(plan.open_spans(200,35800,[]),[(200,35800)]))
    ok("tail crossing obstacle splits real route interval",lambda:eq(plan.open_spans(200,35800,[(15000,16000)]),[(200,15000),(16000,35800)]))
    ok("tail overlapping and touching blockers merge",lambda:eq(plan.open_spans(200,35800,[(9000,11000),(5000,8000),(7000,9000)]),[(200,5000),(11000,35800)]))
    def clipped():
        eq(plan.open_spans(200,35800,[(-1000,0),(36000,37000)]),[(200,35800)])
        eq(plan.open_spans(200,35800,[(-1000,37000)]),[])
    ok("tail outside and spanning blockers clipped conservatively",clipped)
    ok("tail undersized metal slivers are excluded",lambda:eq(plan.open_spans(200,35800,[(1100,35000)]),[]))
    refuse("tail reversed segment bounds refused",lambda:plan.open_spans(35800,200,[]))
    refuse("tail offgrid blocker refused",lambda:plan.open_spans(200,35800,[(5001,6000)]))
    refuse("tail reversed blocker refused",lambda:plan.open_spans(200,35800,[(8000,7000)]))
    assert len(rows)==30 and len(set(rows))==30
    result=dict(status="PASS_CURRENT_EIGHT_DRAIN_SOURCE_CONTROLS",count=30,passed_cases=rows,
      source=ctx["source"],run_id=ctx["run_id"],attempt=1,native_executed=False,
      synthetic_boundaries=["native target identity records","terminal lifecycle callbacks","new group binding fixture"],
      native_geometry_not_executed=True,**plan.FLAGS)
    host.write(root/"tail-controls.json",host.encode(result))
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
