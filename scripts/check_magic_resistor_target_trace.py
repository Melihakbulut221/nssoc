#!/usr/bin/env python3
"""Hosted source/synthetic tests only; never downloads an actual trace or executes CAD."""
import argparse,copy,json,os,tempfile,traceback
from pathlib import Path
from unittest.mock import patch
import magic_resistor_target_trace as t
b=t.b

def fixture():
    node=lambda n:dict(address="0x"+n,xy=[1,2],name_hex=n.encode().hex())
    r=dict(resistor_address="0x123",rr_value_milliohms_hex="0x1p+0",rr_tt=4,rr_width_raw=2,rr_cl_raw=3,
      resist_scale=1,material_name_hex="746d32",is_contact=False,sheet_resist_raw=1,via_resist_raw=0,
      node1=node("a"),node2=node("b"),ext_value_token="1")
    rows=[dict(event="net_begin"),dict(r,event="create_tile"),dict(event="net_end")]
    for phase in ("before_simplify","after_simplify"):
        rows += [dict(event="snapshot_begin",phase=phase),dict(r,event="snapshot_resistor",phase=phase,index=0),
                 dict(event="snapshot_end",phase=phase,count=1)]
    rows.append(dict(r,event="emitted_resistor"))
    for i,x in enumerate(rows):x.update(epoch=1,seq=i+1)
    target=dict(component=17,native_net="$131",native_cluster=28,contacts=[],nodes=[dict(native=n)for n in ("a","b")],
      native_primitive_records=[dict(raw='resist "a" "b" 1',tokens=["resist","a","b","1"])],
      canonical_incidence=[dict(kind="R",a="a",b="b",token="1",name="R1")])
    dc=dict(pair_unit_injections=[dict(positive_contact="a",negative_contact="b",
      effective_resistance_ohm="1",edge_responses=[dict(name="R1",power_W="1")])])
    return rows,target,dc

def controls(expected):
    ctx=b.context(os.environ);b.source_guard(expected)
    c,p,inc,dc=t.proof();positive=["authentic_current500_trace_source_and_DC_proof"];refused=[];life=[]
    live=[copy.deepcopy(p[n])for n in ("run.json","jobs.json","release.json","tag-ref.json")]
    t.live_binding(c,p,*live);positive.append("authentic_successful_four_job_seventeen_asset_projection")
    def reject(label,fn):
        try:fn()
        except (AssertionError,ValueError,KeyError):refused.append(label)
        else:raise AssertionError("accepted refusal: "+label)
    rows,target,d=fixture();r=t.analyze_epoch(rows,target,d)
    assert r["counts"]["unchanged_snapshot"]==1 and r["physical_acceptance"]is False
    assert not r["all_edges"][0]["physical_ownership_proved"]
    positive.append("complete_synthetic_epoch_and_existing_DC_join")
    changed=copy.deepcopy(rows);changed[1]["rr_value_milliohms_hex"]="0x1p-1"
    r=t.analyze_epoch(changed,target,d)
    assert r["counts"]["changed_from_every_observed_constructor"]==1
    positive.append("surviving_address_changed_value_is_not_ownership")
    repeated=copy.deepcopy(rows);repeated.insert(2,copy.deepcopy(repeated[1]))
    for i,x in enumerate(repeated):x["seq"]=i+1
    r=t.analyze_epoch(repeated,target,d);assert r["counts"]["repeated_constructor_address"]==1
    positive.append("same_address_recreation_explicitly_ambiguous")
    absent=[x for x in rows if x["event"]!="create_tile"]
    assert t.analyze_epoch(absent,target,d)["counts"]["missing_constructor"]==1
    positive.append("unobserved_constructor_retained_as_unknown")
    for key,value in [("head_sha","0"*40),("conclusion","failure"),("id",1)]:
        a=copy.deepcopy(live);a[0][key]=value;reject("live_run_"+key,lambda a=a:t.live_binding(c,p,*a))
    for kind in ("job","step","asset","digest","tag"):
        a=copy.deepcopy(live)
        if kind=="job":a[1]["jobs"][0]["conclusion"]="failure"
        elif kind=="step":a[1]["jobs"][0]["steps"][0]["conclusion"]="failure"
        elif kind=="asset":a[2]["assets"].pop()
        elif kind=="digest":a[2]["assets"][0]["digest"]="sha256:"+"0"*64
        else:a[3]["object"]["sha"]="0"*40
        reject("live_"+kind,lambda a=a:t.live_binding(c,p,*a))
    for label,mut in [
      ("emission_token",lambda x:x[-1].update(ext_value_token="2")),
      ("missing_end",lambda x:x.pop(2)),
      ("wrong_epoch",lambda x:x[-1].update(epoch=2)),
      ("snapshot_count",lambda x:x[5].update(count=2)),
      ("snapshot_index",lambda x:x[4].update(index=1)),
      ("emission_name",lambda x:x[-1]["node1"].update(name_hex="63")),
      ("snapshot_missing",lambda x:x.pop(4)),
      ("duplicated_snapshot",lambda x:x.insert(5,copy.deepcopy(x[4])))]:
        bad=copy.deepcopy(rows);mut(bad);reject(label,lambda bad=bad:t.analyze_epoch(bad,target,d))
    bad=copy.deepcopy(target);bad["canonical_incidence"][0]["token"]="NaN"
    reject("nonfinite_incidence",lambda:t.analyze_epoch(rows,bad,d))
    bad_dc=copy.deepcopy(d);bad_dc["pair_unit_injections"][0]["edge_responses"]=[]
    reject("missing_DC_edge",lambda:t.analyze_epoch(rows,target,bad_dc))
    with tempfile.TemporaryDirectory()as temp:
        root=Path(temp);trace=root/"synthetic-trace.jsonl"
        trace.write_bytes(b"".join(b.encode(x)for x in rows))
        out=root/"selected";out.mkdir()
        got=t.select_epochs(trace,{"28":target},out)
        assert got=={"28":rows}and b.decode((out/"target-28-events.json").read_bytes())==rows
        life.append("actual_complete_selected_epoch_bytes_preserved")
        primary=OSError("synthetic transport failure")
        def fail(*a):
            b.write(a[-1]/"partial.bin",b"exact available bytes")
            raise primary
        with patch.object(b,"preserve_current_source",lambda *args:None):
            try:b.run(ctx,{},b"",expected,root/"failure",fail)
            except OSError as exc:assert exc is primary
            else:raise AssertionError("primary missing")
        assert (root/"failure/partial.bin").read_bytes()==b"exact available bytes"
        assert b.decode((root/"failure/result.json").read_bytes())["error"]["message"]==str(primary)
        life.append("real_result_wrapper_preserves_transport_and_partial")
        def broken(*a):raise OSError("secondary encode/write")
        with patch.object(b,"preserve_current_source",lambda *a:None),patch.object(b,"write",broken):
            try:b.run(ctx,{},b"",expected,root/"dual",lambda *a:(_ for _ in ()).throw(primary))
            except OSError as exc:assert exc is primary
            else:raise AssertionError("primary replaced")
        life.append("real_result_wrapper_secondary_save_does_not_replace_primary")
    assert (len(positive),len(refused),len(life))==(6,18,3),(positive,refused,life)
    return dict(status="PASS_MAGIC_TARGET_TRACE_SOURCE_CONTROLS",passed=True,
      counts=dict(positive=len(positive),refusal=len(refused),lifecycle=len(life)),
      positive=positive,refusals=refused,lifecycle=life,native_executed=False,physical_acceptance=False,
      synthetic_trace_only=True,current_context=dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,
      source_controls_only=True,native_executed=False))

def main():
    p=argparse.ArgumentParser();p.add_argument("--pins-sha256",required=True)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args();primary=None
    try:r=controls(a.pins_sha256)
    except BaseException as exc:
        primary=exc;r=dict(status="FAIL_MAGIC_TARGET_TRACE_SOURCE_CONTROLS",error=repr(exc),
          traceback=traceback.format_exc(),native_executed=False,physical_acceptance=False)
    raw=b.encode(r);print(raw.decode(),end="",flush=True)
    try:b.write(a.output,raw)
    except BaseException:
        if primary is None:raise
    if primary is not None:raise primary
if __name__=="__main__":main()
