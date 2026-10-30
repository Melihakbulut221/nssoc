#!/usr/bin/env python3
"""Hosted source controls; no native imports, CAD, archive acquisition or geometry execution."""
import argparse,ast,copy,json,os,tempfile,traceback,types
from pathlib import Path
from unittest.mock import patch
import cloud_cdr_drain_m1_fresh_graph as h
import cdr_drain_m1_fresh_graph_native as n
import check_cdr_drain_m1_width_trial as previous

def source_derivation():
    old=(h.ROOT/"scripts/cdr_v59_tail_saved_identity_native.py").read_text()
    new=(h.ROOT/"scripts/cdr_drain_m1_fresh_graph_native.py").read_text()
    segment=lambda t,name:ast.get_source_segment(t,next(v for v in ast.parse(t).body if isinstance(v,ast.FunctionDef)and v.name==name))
    assert segment(old,"compare_witnesses").replace('"original_native_failure_preserved":True','"no_historical_failure_or_acceptance_transferred":True')==segment(new,"compare_witnesses")
    oldhost=(h.ROOT/"scripts/cloud_cdr_drain_m1_width_trial.py").read_text()
    newhost=(h.ROOT/"scripts/cloud_cdr_drain_m1_fresh_graph.py").read_text()
    for name in ("context","tokenless","finish","runtime_restore","emit"):
        assert segment(oldhost,name)==segment(newhost,name),name
    texts,proof=n.original.derived_texts()
    assert len(texts)==3 and len(n.WIRE)==4
    return dict(original_identity_body_one_historical_return_label_change=True,
      unchanged_host_functions=["context","tokenless","finish","runtime_restore","emit"],
      original_plane_method_derivations=proof,unchanged_wire_workers=list(n.WIRE))

def alpha_graph(graph):
    result=copy.deepcopy(graph)
    for row in result["native_net_coverage"]:
        row["native_cluster"]+=7000
        row["wire_components"]=[v+9000 for v in row["wire_components"]]
    for row in result["wire_components"]:
        row["native_cluster"]+=7000;row["component"]+=9000
    return result

def lifecycle_fixture(case,config):
    # Real new perform()/run() paths; synthetic transport, census and native boundaries.
    primary=OSError("synthetic "+case);calls=[];tmpobjects=[]
    actual_temp=tempfile.TemporaryDirectory
    class Temp:
        def __init__(self,*a,**kw):
            self.inner=actual_temp(*a,**kw);self.name=self.inner.name;tmpobjects.append(self)
        def cleanup(self):
            self.inner.cleanup();calls.append("cleanup")
            if case=="cleanup":raise primary
    ctx=dict(source="1"*40,run_id=1,attempt=1,group=h.GROUP,token="1-1")
    data=dict(parts=dict(bytes=0,source_directory="synthetic-old"),full={})
    c=copy.deepcopy(config);c["selected"]={};c["physical"]["selected"]=[];c["physical"]["full"]={}
    old={};proof=dict(current_context=ctx)
    def acquire(*args):
        calls.append("old-acquire");p=Path(args[2])/"synthetic.tar";p.write_bytes(b"fixture")
        return p,dict(synthetic=True)
    def fetch(asset,path):
        calls.append("physical-fetch")
        if case=="physical-transport":raise primary
        path.write_bytes(b"fixture")
    def select(*args):
        calls.append("select");args[-1].mkdir()
        if case=="physical-census"and calls.count("select")==2:raise primary
        return dict(full_member_count=0,selected={})
    def native(*a,**kw):
        calls.append("native");(a[2]/"partial.stdout").write_bytes(b"retained synthetic worker bytes\n")
        (a[2]/"zero.stderr").write_bytes(b"")
        if case in ("native","native-plus-emit"):raise primary
        return dict(synthetic=True)
    with actual_temp()as t:
        root=Path(t);out=root/"out"
        original_emit=h.emit
        def emitter(path):
            calls.append("emit")
            original_emit(path,lambda *a,**kw:None)
            if case=="native-plus-emit":raise RuntimeError("synthetic secondary emit")
        with patch.object(h,"preflight",return_value=(c,old,data,proof)),patch.object(h,"source_guard",return_value=(c,old,data)),\
             patch.object(h.frozen,"acquire",acquire),patch.object(h.frozen,"select_archive",select),\
             patch.object(h,"native_readback",native),patch.object(h.tempfile,"TemporaryDirectory",Temp),patch.object(h,"emit",emitter):
            try:h.run(ctx,{},b"{}",out,"0"*64,root/"app",root,fetch=fetch)
            except BaseException as exc:assert exc is primary,(case,repr(exc))
            else:raise AssertionError("Missing actual lifecycle refusal: "+case)
        assert (out/"readback-failure.json").is_file()and "cleanup"in calls and "emit"in calls
        if case in ("native","native-plus-emit","cleanup"):
            assert (out/"partial.stdout").read_bytes()==b"retained synthetic worker bytes\n"
            assert (out/"zero.stderr").read_bytes()==b""
        return dict(case=case,calls=calls,actual_run_and_perform=True,synthetic_transport_native=True,
          full_partial_outputs_preserved=True,original_primary_preserved=True)

def controls(expected):
    positives=[];refusals=[];lifecycle=[]
    def yes(name,fn):
        value=fn();positives.append(dict(name=name,evidence=value));return value
    def no(name,fn):
        try:fn()
        except Exception as exc:refusals.append(dict(name=name,error=repr(exc)));return
        raise AssertionError("Missing refusal: "+name)
    config,_,data=h.source_guard(expected)
    yes("actual_dual_source_census",lambda:dict(old=len(data["full"]),physical=len(config["physical"]["full"]),
      selected_old=len(config["selected"]),selected_physical=len(config["physical"]["selected"])))
    assert len(data["full"])==6647 and len(config["physical"]["full"])==154
    yes("exact_immutable_derivations",source_derivation)
    graph=h.decode((h.ROOT/config["geometry"]).read_bytes())
    index,components=n.component_keys(graph);keys=n.target_keys(graph)
    yes("actual_old_full_graph_partitions",lambda:dict(native=len(index),components=len(components),targets=keys))
    assert len(index)==238 and len(components)==113
    changed=alpha_graph(graph)
    ni,nc=n.component_keys(changed);nk=n.target_keys(changed)
    assert set(components)==set(nc)and keys==nk
    yes("renumbered_partition_component_identity",lambda:dict(same_full_keys=True,new_ids_used=True))
    with tempfile.TemporaryDirectory()as t:
        yes("full_empty_and_binary_output_inventory",lambda:previous.output_fixture(Path(t)))
    mutations=(
      ("wrong_device_census",lambda x:x.update(native_device_count=499)),
      ("missing_partition",lambda x:x["native_net_coverage"].pop()),
      ("missing_component",lambda x:x["wire_components"].pop()),
      ("duplicate_component",lambda x:x["wire_components"].append(copy.deepcopy(x["wire_components"][0]))),
      ("unknown_component_owner",lambda x:x["wire_components"][0].update(native_cluster=-1)),
      ("renamed_without_join",lambda x:x["wire_components"][0].update(native_name="forged")),
      ("duplicate_terminal",lambda x:next(r for r in x["native_net_coverage"]if r["device_terminals"])["device_terminals"].append(copy.deepcopy(next(r for r in x["native_net_coverage"]if r["device_terminals"])["device_terminals"][0]))),
      ("foreign_public_pin",lambda x:x["native_ports"].__setitem__(0,"forged")),
      ("RC_flag",lambda x:x.update(wire_rc_extracted=True)),
      ("graph_union_flag",lambda x:x.update(no_component_union_by_native_label=False)),
      ("empty_partition_material",lambda x:next(r for r in x["native_net_coverage"]if not r["device_terminals"]).update(metal_area_dbu2=1)),
      ("target_terminal_lost",lambda x:next(r for r in x["native_net_coverage"]if dict(device=3,model="sg13_lv_nmos",terminal="D")in r["device_terminals"])["device_terminals"].remove(dict(device=3,model="sg13_lv_nmos",terminal="D"))))
    for name,mut in mutations:
        bad=copy.deepcopy(graph);mut(bad)
        no(name,lambda bad=bad:(n.component_keys(bad),n.target_keys(bad)))
    for case in ("physical-transport","physical-census","native","native-plus-emit","cleanup"):
        lifecycle.append(lifecycle_fixture(case,config))
    inherited=previous.controls("d5d040630ca41d4e8f2815a090a468a96a46a655b9b3c7158013a10692921c2d")
    result=dict(status="PASS_DRAIN_M1_FRESH_GRAPH_SOURCE_CONTROLS",passed=True,
      counts=dict(positive=len(positives),refusal=len(refusals),lifecycle=len(lifecycle)),
      positives=positives,refusals=refusals,lifecycle=lifecycle,inherited=inherited,
      native_executed=False,physical_acceptance=False,electrical_acceptance=False,
      native_region_controls_deferred=True)
    assert result["counts"]==dict(positive=5,refusal=12,lifecycle=5)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument("--pins-sha256",required=True);p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();ctx=h.context(os.environ);primary=None
    current=dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False)
    try:result=controls(args.pins_sha256);result["current_context"]=current
    except BaseException as exc:
        primary=exc;result=dict(status="FAIL_DRAIN_M1_FRESH_GRAPH_SOURCE_CONTROLS",passed=False,error=repr(exc),
          traceback=traceback.format_exc(),current_context=current,native_executed=False,physical_acceptance=False)
    previous.old.finish_report(args.output,result,primary)
if __name__=="__main__":main()
