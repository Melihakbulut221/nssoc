#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source fixtures only; synthetic DEF/decoded shapes are not native evidence."""
import argparse,contextlib,copy,hashlib,io,json,os,re,subprocess
from pathlib import Path
import mainchip_multilayer_antenna_trial as p

def controls():
    p.source_guard()
    assert os.environ["GITHUB_EVENT_NAME"]=="workflow_dispatch"
    assert os.environ["GITHUB_RUN_ATTEMPT"]=="1"
    assert os.environ["GITHUB_REF"]=="refs/heads/codex/mainchip-net459-diode-prune"
    source=os.environ["GITHUB_SHA"];assert re.fullmatch("[0-9a-f]{40}",source)
    assert subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==source
    ctx=dict(source=source,run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=1,
      source_controls_only=True,native_executed=False)
    assert ctx["run_id"]>0
    positive=["exact_source_and_frozen_helpers"];refused=[];lifecycle=[]
    def reject(name,fn):
        try:fn()
        except(AssertionError,ValueError,KeyError,TypeError):refused.append(name);return
        raise AssertionError("not refused: "+name)
    def same(a,b,reason="fixture mismatch"):p.exact(a,b,reason)
    assert p.run_phase is p.legacy.run_phase and p.patch_def is p.c.patch_def

    record=("- "+p.NET+" ( I0 X ) ( fanout36953 A ) ( "+p.NEW+" A )\n"
      " + ROUTED Metal2 ( 97440 504420 ) ( 97440 511140 ) ;\n").encode()
    patch=p.append_branch(record)
    expected=(" NEW Metal1 ( 99600 505680 ) ( 101280 505680 ) Via1_XY\n"
      " NEW Metal2 ( 101280 505680 ) ( 101280 506520 ) Via2_YX\n"
      " NEW Metal3 ( 101280 506520 ) ( 97440 506520 ) Via2_YX\n").encode()
    at=record.index(b";")
    assert patch==record[:at]+expected+record[at:]
    assert p.old.wire_head(patch)==p.old.wire_head(record)
    positive.append("exact_three_path_DEF_and_connection_prefix")
    for q in(b"    "+record,b"\t"+record,record.replace((p.NET+" ").encode(),(p.NET+"\n").encode(),1)):
        z=p.append_branch(q);i=q.index(b";");assert z==q[:i]+expected+q[i:]
    positive.append("qualified_indented_DEF_grammar")
    for name,q in[
      ("foreign_target",record.replace(p.NET.encode(),b"other")),
      ("duplicate_record",record+record),("unowned_blank",b"\n"+record),
      ("route_property",record.replace(b" ;",b" + PROPERTY BAD 1 ;")),
      ("CR_record",record.replace(b"\n",b"\r\n",1))]:
        reject(name,lambda q=q:p.append_branch(q))

    components=[("- I%d BUF + PLACED ( %d 0 ) N ;\n"%(i,i)).encode()for i in range(153128)]
    diode=("- "+p.NEW+" sg13g2_antennanp + PLACED ( 98880 502740 ) FS ;\n").encode()
    header=b'VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN top ;\nUNITS DISTANCE MICRONS 1000 ;\n'
    special=("SPECIALNETS 2 ;\n- VDD ( "+p.NEW+" VDD ) + USE POWER ;\n- VSS ( "+p.NEW+" VSS ) + USE GROUND ;\nEND SPECIALNETS\n").encode()
    fixed=b"- clk ( I0 A ) ( I1 X )\n + FIXED Metal1 ( 1 2 ) ( 2 2 ) ;\n"
    before=header+b"COMPONENTS 153129 ;\n"+b"".join(components)+diode+b"END COMPONENTS\n"+special+b"NETS 2 ;\n"+record+fixed+b"END NETS\nEND DESIGN\n"
    after=p.c.replace_records(before,{p.NET:patch})
    normal=p.normalized_def(before);same(normal,p.normalized_def(after))
    assert not normal["removed_components"]and not normal["removed_connection_counts"]
    positive.append("all153129_components_and_connections_retained")
    for name,q in[
      ("diode_location",after.replace(b"( 98880 502740 )",b"( 98885 502740 )")),
      ("diode_orientation",after.replace(b"502740 ) FS",b"502740 ) N")),
      ("diode_master",after.replace(b"sg13g2_antennanp",b"sg13g2_buf_1")),
      ("diode_removed",after.replace(diode,b"")),
      ("diode_A_removed",after.replace(("( "+p.NEW+" A )").encode(),b"")),
      ("diode_VDD_changed",after.replace(("( "+p.NEW+" VDD )").encode(),("( "+p.NEW+" VSS )").encode())),
      ("diode_VSS_removed",after.replace(("( "+p.NEW+" VSS )").encode(),b"")),
      ("other_placement",after.replace(b"- I0 BUF + PLACED ( 0 0 )",b"- I0 BUF + PLACED ( 5 0 )")),
      ("other_fixed_wire",after.replace(b"+ FIXED Metal1 ( 1 2 )",b"+ FIXED Metal1 ( 3 2 )")),
      ("target_connection",after.replace(b"( I0 X )",b"( I2 X )")),
      ("component_census",after.replace(b"COMPONENTS 153129",b"COMPONENTS 153128")),
      ("target_property",after.replace(b" Via1_XY\n",b" Via1_XY + PROPERTY BAD 1\n")),
      ("unterminated_quote",after.replace(b"END DESIGN",b'"unterminated\nEND DESIGN'))]:
        reject(name,lambda q=q:same(normal,p.normalized_def(q)))

    # Exact pure decoder is exercised. OIDs below are explicitly synthetic.
    layers={n:dict(name=n,width=w,wrong_way_width=w,direction=d)for n,w,d in[
      ("Metal1",160,"HORIZONTAL"),("Metal2",200,"VERTICAL"),("Metal3",200,"HORIZONTAL"),
      ("Via1",0,"NONE"),("Via2",190,"NONE")]}
    catalog=dict(layers=layers,path_layers={1:"Metal1",2:"Metal2",3:"Metal3"},rules={},
      vias=copy.deepcopy(p.VIA_DEFINITIONS))
    raw=[[0,1],[4,99600],[5,505680],[4,101280],[136,3],
         [0,2],[4,101280],[5,505680],[5,506520],[136,22],
         [0,3],[4,101280],[5,506520],[4,97440],[8,22]]
    decoded=p.geometry.project_wire(raw,catalog)
    same(p.material(decoded["shapes"]),p.expected_added_shapes(catalog))
    assert [r["box"]for r in decoded["shapes"]if r["kind"]=="wire"]==[
      [99520,505600,101360,505760],[101180,505580,101380,506620],[97340,506420,101380,506620]]
    assert len(decoded["shapes"])==12
    positive.append("actual_frozen_decoder_three_wires_nine_components")

    oldraw=[[0,2],[4,97440],[5,504420],[5,511140]]
    original=p.geometry.project_wire(oldraw,catalog)["shapes"][0]
    oldshapes=[]
    for i in range(40):
        row=copy.deepcopy(original);row["opcode_index"]=i;oldshapes.append(row)
    pins=[
      dict(kind="iterm",scoped_identity=["iterm",*p.SINK],instance=p.SINK[0],terminal=p.SINK[1],
        master=["synthetic","BUF"],geometries=[["Metal2",[97340,504320,97540,504520]]]),
      dict(kind="iterm",scoped_identity=["iterm",p.NEW,"A"],instance=p.NEW,terminal="A",
        master=["synthetic","sg13g2_antennanp"],geometries=[["Metal1",[99285,505360,99930,505950]]])]
    base=dict(scoped_identity=["net",p.NET],wire_identity=["net",p.NET,"wire"],
      metadata_class="ROUTED",sigtype="SIGNAL",pins=pins,
      projection=dict(shape_count=40,shapes=oldshapes,catalog=dict(
        layers=copy.deepcopy(layers),path_layers={2:"Metal2"},rules={},vias={})))
    candidate=copy.deepcopy(base);candidate["projection"]["catalog"]=copy.deepcopy(catalog)
    assert not base["projection"]["catalog"]["vias"],"synthetic baseline uses no vias"
    extra=copy.deepcopy(decoded["shapes"])
    for row in extra:row["opcode_index"]+=1000
    candidate["projection"]["shapes"]+=extra;candidate["projection"]["shape_count"]=52
    delta=p.validate_route_delta(base,candidate)
    assert delta["original_shapes"]==40 and delta["added_wires"]==3 and delta["added_via_components"]==9
    positive.append("actual_route_delta_preserves_multiplicity_and_all_pins")
    transported=json.loads(json.dumps(base))
    restored=p.restore_target_catalog(transported)
    same(p.validate_route_delta(restored,candidate),delta)
    positive.append("actual_JSON_baseline_layer_OID_roundtrip")
    for name,keys in (("zero_oid",{"0":"Metal2"}),("noncanonical_oid",{"01":"Metal2"}),("already_integer_oid",{1:"Metal2"})):
        bad=json.loads(json.dumps(base));bad["projection"]["catalog"]["path_layers"]=keys
        reject(name,lambda bad=bad:p.restore_target_catalog(bad))
    connectivity=p.validate_connectivity(candidate)
    assert set(connectivity)=={"positive_area","closed_boundary"}
    for mode in connectivity:
        original_graph=p.graph.observe(base["projection"]["shapes"],base["pins"],mode)
        assert original_graph["all_wire_material_one_component"]and not original_graph["all_pins_share_one_wire_component"]
    positive.append("actual_graph_baseline_unconnected_diode_final_connected_both_modes")

    mutations=[
      ("old_material",lambda q:q["projection"]["shapes"][0]["box"].__setitem__(0,97335)),
      ("old_pin",lambda q:q["pins"][0]["geometries"][0][1].__setitem__(0,97335)),
      ("existing_diode_pin",lambda q:q["pins"][1].__setitem__("terminal","B")),
      ("missing_shape",lambda q:q["projection"]["shapes"].pop()),
      ("extra_shape",lambda q:q["projection"]["shapes"].append(copy.deepcopy(q["projection"]["shapes"][-1]))),
      ("wrong_via_key",lambda q:q["projection"]["shapes"][41].__setitem__("via_key","tech:22")),
      ("wrong_via_component",lambda q:q["projection"]["shapes"][42].__setitem__("component_ordinal",0)),
      ("wrong_cut_box",lambda q:q["projection"]["shapes"][42]["box"].__setitem__(0,1)),
      ("wrong_layer",lambda q:q["projection"]["shapes"][44].__setitem__("layer","Metal1")),
      ("wrong_width",lambda q:q["projection"]["shapes"][40].__setitem__("half_width",100)),
      ("bool_geometry",lambda q:q["projection"]["shapes"][40]["from_xy"].__setitem__(0,True)),
      ("split_via_opcode",lambda q:q["projection"]["shapes"][42].__setitem__("opcode_index",9000)),
      ("old_opcode_reuse",lambda q:q["projection"]["shapes"][40].__setitem__("opcode_index",0)),
      ("path_opcode_reuse",lambda q:q["projection"]["shapes"][44].__setitem__("opcode_index",q["projection"]["shapes"][40]["opcode_index"])),
      ("metadata_class",lambda q:q.__setitem__("metadata_class","FIXED")),
    ]
    for name,mutate in mutations:
        q=copy.deepcopy(candidate);mutate(q)
        reject(name,lambda q=q:p.validate_route_delta(base,q))
    for name,key in(("default_width","width"),("wrongway_width","wrong_way_width")):
        q=copy.deepcopy(catalog);q["layers"]["Metal1"][key]=200
        reject(name,lambda q=q:p.expected_added_shapes(q))
    q=copy.deepcopy(catalog);q["vias"]["tech:3"]["components"][0]["box"][0]=-150
    reject("via_definition_changed",lambda:p.expected_added_shapes(q))
    q=copy.deepcopy(candidate);q["projection"]["shapes"]=q["projection"]["shapes"][:40]+q["projection"]["shapes"][44:]
    reject("disconnected_missing_M1_bridge",lambda:p.validate_connectivity(q))
    q=copy.deepcopy(candidate);q["pins"][1]["geometries"]=[["Metal1",[1,1,2,2]]]
    reject("disconnected_diode_pin",lambda:p.validate_connectivity(q))

    violation=lambda net:dict(net=net,pin="synthetic/A",violated=True,rule="Cumulative area",display_value="201.00",display_limit="200.00")
    historical=[violation("other"),violation(p.NET)]
    def report(target):
        return dict(counts=dict(target_count=target,target_violation=target,full_count=1+target),
          violations=[violation("other")]+([violation(p.NET)]if target else []))
    for baseline_target in(0,1):
        r=p.validate_antenna(report(baseline_target),report(0),historical,0)
        assert r["bounded_trial_passed"]and not r["physical_acceptance"]
    positive.append("actual_antenna_gate_accepts_truthful_zero_or_one_baseline")
    for cc,dd in((report(1),0),(report(0),1)):
        r=p.validate_antenna(report(0),cc,historical,dd)
        assert r["candidate_rejected"]and not r["bounded_trial_passed"]
    positive.append("actual_DRC_and_target_rejections_retained")
    q=report(0);q["violations"][0]["display_value"]="202.00"
    reject("baseline_other_antenna_changed",lambda:p.validate_antenna(q,report(0),historical,0))
    reject("candidate_other_antenna_changed",lambda:p.validate_antenna(report(0),q,historical,0))
    q2=report(0);q2["counts"]["full_count"]=0
    reject("full_report_count",lambda:p.validate_antenna(report(0),q2,historical,0))
    q3=report(0);q3["counts"]["target_count"]=1
    reject("target_full_report_disagreement",lambda:p.validate_antenna(report(0),q3,historical,0))
    reject("boolean_DRC_count",lambda:p.validate_antenna(report(0),report(0),historical,False))

    calls=[];written={}
    def okay():calls.append("action")
    def unchanged():calls.append("input")
    def writer(name,value):calls.append(name);written[name]=copy.deepcopy(value)
    p.run_phase("test",okay,unchanged,writer)
    assert calls==["action","input","test-terminal.json"]and written["test-terminal.json"]["complete"]
    lifecycle.append("unchanged_actual_success")
    primary=ValueError("primary");calls=[];stream=io.StringIO()
    def fail():calls.append("action");raise primary
    def badinput():calls.append("input");raise OSError("input")
    def badwrite(name,value):calls.append(name);raise OSError("write "+name)
    with contextlib.redirect_stderr(stream):
        try:p.run_phase("test",fail,badinput,badwrite)
        except ValueError as exc:assert exc is primary
        else:raise AssertionError("primary lost")
    assert len(json.loads(stream.getvalue())["terminal_errors"])==3
    assert calls==["action","test-failure.json","input","test-terminal.json"]
    lifecycle.append("unchanged_actual_primary_survives_three_failures")
    calls=[];written={};stream=io.StringIO()
    with contextlib.redirect_stderr(stream):
        try:p.run_phase("test",okay,badinput,writer)
        except RuntimeError:pass
        else:raise AssertionError("input failure accepted")
    assert not written["test-terminal.json"]["complete"]
    lifecycle.append("unchanged_actual_input_failure")
    stream=io.StringIO()
    with contextlib.redirect_stderr(stream):
        try:p.run_phase("test",okay,unchanged,badwrite)
        except RuntimeError:pass
        else:raise AssertionError("save failure accepted")
    assert json.loads(stream.getvalue())["terminal_errors"][0]["label"]=="terminal-record"
    lifecycle.append("unchanged_actual_save_failure")
    assert (len(positive),len(refused),len(lifecycle))==(10,46,4),"complete authored source suite"
    return dict(status="PASS_MULTILAYER_ANTENNA_TRIAL_SOURCE_CONTROLS",current_context=ctx,
      positive=positive,positive_count=len(positive),refusals=refused,refusal_count=len(refused),
      lifecycle=lifecycle,lifecycle_count=len(lifecycle),synthetic_geometry=True,native_executed=False,
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",type=Path,required=True);args=ap.parse_args()
    error=None
    try:result=controls()
    except BaseException as exc:
        error=exc;result=dict(status="FAIL_MULTILAYER_ANTENNA_TRIAL_SOURCE_CONTROLS",
          error=repr(exc),native_executed=False,physical_acceptance=False)
    failures=[]
    try:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(p.encode(result))
    except BaseException as exc:failures.append(dict(stage="report-write",error=repr(exc)))
    try:print(p.encode(dict(result=result,preservation_errors=failures)if failures else result).decode(),flush=True)
    except BaseException as exc:failures.append(dict(stage="stdout",error=repr(exc)))
    if error is not None:raise error
    if failures:raise RuntimeError("checker preservation failed: "+repr(failures))
if __name__=="__main__":main()
