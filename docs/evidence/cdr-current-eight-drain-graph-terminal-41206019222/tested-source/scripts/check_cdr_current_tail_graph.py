#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only source controls. Synthetic contracts do not qualify native graph or RC."""
import ast,copy,json,os
from pathlib import Path
import cdr_current_tail_graph as plan
import cloud_cdr_current_tail_graph as host
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
        for name in("scripts/cdr_current_tail_graph.py","scripts/cdr_current_tail_graph_native.py","scripts/cloud_cdr_current_tail_graph.py"):
            tree=ast.parse((host.ROOT/name).read_bytes())
            if "cloud_"in name:
                guards=[n for n in tree.body if isinstance(n,ast.If)and isinstance(n.test,ast.Compare)
                  and isinstance(n.test.left,ast.Name)and n.test.left.id=="__name__"]
                eq(len(guards),1)
    ok("graph exact inherited and new source with single entrypoint",source)
    cfg=host.config()
    ok("graph contract preserves exact physical identity through JSON",lambda:plan.contract(json.loads(json.dumps(cfg))))
    producer=host.r.source_guard();entry=producer["cases"]["nominal_early"]
    summary,parts,original=host.r.metadata(producer,"nominal_early")
    ok("graph all66 exact current reference and original failure members",lambda:eq(len(plan.input_names(cfg,summary["outputs"],entry)),66))
    for kind in("missing_selected","wrong_selected_hash","old_producer","wrong_gds","wrong_lvs","RC_authority"):
        def bad(kind=kind):
            c=copy.deepcopy(cfg)
            if kind=="missing_selected":c["selected"].pop(next(iter(c["selected"])))
            elif kind=="wrong_selected_hash":c["selected"][next(iter(c["selected"]))]="0"*64
            elif kind=="old_producer":c["old_producer_run"]=40830441311
            elif kind=="wrong_gds":c["physical"]["gds"]["sha256"]="0"*64
            elif kind=="wrong_lvs":c["physical"]["lvs"]["sha256"]="0"*64
            else:c["fresh_rc_authorized"]=True
            plan.input_names(c,summary["outputs"],entry)
        refuse("graph rejects "+kind,bad)
    p=cfg["physical"];producer=p["producer"]
    run={**producer,"status":"completed","conclusion":"success"}
    jobs=dict(jobs=[dict(name=name,status="completed",conclusion="success",head_sha=producer["head_sha"],run_id=producer["id"])
      for name in("source-controls","preserve-job-log","physical","preserve-physical-job-logs")])
    release=dict(id=p["release_id"],tag_name=p["tag"],target_commitish=producer["head_sha"],draft=False,prerelease=True,
      assets=[dict(name=name,state="uploaded",id=pin["id"],size=pin["bytes"],digest="sha256:"+pin["sha256"])for name,pin in p["assets"].items()])
    ref=dict(object=dict(type="commit",sha=producer["head_sha"]))
    ok("graph requires complete exact qualified physical producer",lambda:plan.physical_live(cfg,run,jobs,release,ref))
    for kind in("run_source","attempt","run_failure","workflow","job_failure","job_source","release_source","tag","missing_asset","asset_digest"):
        def bad(kind=kind):
            r,j,l,t=copy.deepcopy((run,jobs,release,ref))
            if kind=="run_source":r["head_sha"]="0"*40
            elif kind=="attempt":r["run_attempt"]=2
            elif kind=="run_failure":r["conclusion"]="failure"
            elif kind=="workflow":r["workflow_id"]=1
            elif kind=="job_failure":j["jobs"][2]["conclusion"]="failure"
            elif kind=="job_source":j["jobs"][2]["head_sha"]="0"*40
            elif kind=="release_source":l["target_commitish"]="0"*40
            elif kind=="tag":t["object"]["sha"]="0"*40
            elif kind=="missing_asset":l["assets"].pop()
            else:l["assets"][0]["digest"]="sha256:"+"0"*64
            plan.physical_live(cfg,r,j,l,t)
        refuse("graph rejects physical "+kind,bad)
    declared=dict(device_count=8,all_original_raw_records_preserved=True,records=[],**plan.FLAGS)
    for index,device in enumerate(plan.TARGETS):
        x=(index+1)*100000;cluster=28 if index<4 else 124
        def record(layer,box):
            declared["records"].append(dict(device=device,cluster=cluster,layer=layer,datatype=0,box_dbu=box))
        if device not in(3,32):record(8,[x,0,x+320,36000])
        record(10,[x,0,x+300,36000])
        for i in range(70):record(19,[x,500*i,x+190,500*i+190])
    ok("graph synthetic574 declared shapes preserve exact per-drain census",lambda:eq(len(plan.declarations(declared)),574))
    for kind in("missing_shape","wrong_layer","wrong_device","datatype","offgrid","duplicate","owner"):
        def bad(kind=kind):
            d=copy.deepcopy(declared)
            if kind=="missing_shape":d["records"].pop()
            elif kind=="wrong_layer":d["records"][0]["layer"]=30
            elif kind=="wrong_device":d["records"][0]["device"]=999
            elif kind=="datatype":d["records"][0]["datatype"]=1
            elif kind=="offgrid":d["records"][0]["box_dbu"][0]+=1
            elif kind=="duplicate":d["records"][2]=copy.deepcopy(d["records"][1])
            else:
                for r in d["records"]:
                    if r["device"]==3:r["cluster"]=999
            plan.declarations(d)
        refuse("graph refuses declared "+kind,bad)
    def lifecycle(fail=False):
        seen=[];sentinel=RuntimeError("primary-source-only-failure");report=dict(status="IN_PROGRESS",terminal_errors=[])
        def action():
            seen.append("action")
            if fail:raise sentinel
            report["status"]="SOURCE_ONLY_SUCCESS"
        def integrity():
            seen.append("integrity")
            if fail:raise ValueError("independent-integrity-failure")
        def writer(value):
            seen.append("writer")
            if fail:raise OSError("independent-writer-failure")
        error=None
        try:host.terminal_body(action,integrity,writer,report)
        except BaseException as exc:error=exc
        eq(seen,["action","integrity","writer"])
        if fail:assert error is sentinel;eq(report["status"],"FAIL_CURRENT_EIGHT_DRAIN_FRESH_GRAPH")
        else:eq(error,None)
    ok("graph primary failure survives independent integrity and writer errors",lambda:lifecycle(True))
    ok("graph success retains all terminal actions",lambda:lifecycle())
    root=Path("cdr-drain-wave-source-controls")
    records={key:json.loads((root/name).read_bytes())for key,name in
      (("controls","controls.json"),("publication","publication-controls.json"),("ownership","ownership-controls.json"),
       ("execution","execution-controls.json"),("tail","tail-controls.json"))}
    fixture=dict(status="PASS_CURRENT_EIGHT_DRAIN_GRAPH_SOURCE_CONTROLS",count=32,passed_cases=["fixture-%02d"%n for n in range(32)],
      source=ctx["source"],run_id=ctx["run_id"],attempt=1,native_executed=False,**plan.FLAGS)
    ok("graph binds original195 and new graph source groups",lambda:host.bind_controls(ctx,{**records,"graph":fixture}))
    refuse("graph rejects stale new source group",lambda:host.bind_controls(ctx,{**records,"graph":{**fixture,"source":"0"*40}}))
    assert len(rows)==32 and len(set(rows))==32
    result=dict(status="PASS_CURRENT_EIGHT_DRAIN_GRAPH_SOURCE_CONTROLS",count=32,passed_cases=rows,
      source=ctx["source"],run_id=ctx["run_id"],attempt=1,native_executed=False,
      synthetic_boundaries=["producer/job/release fixtures","574 shape declaration fixture","lifecycle callbacks","group binding fixture"],
      native_graph_not_executed=True,**plan.FLAGS)
    host.write(root/"graph-controls.json",host.encode(result))
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
