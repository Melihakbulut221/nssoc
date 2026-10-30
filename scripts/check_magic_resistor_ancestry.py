#!/usr/bin/env python3
"""Hosted synthetic ancestry replay and actual preservation paths; no native acquisition."""
import argparse,copy,json,os,tempfile,traceback
from pathlib import Path
from unittest.mock import patch
import cloud_magic_resistor_ancestry as a
b=a.b

def fixture(kind="series",reuse=False):
    def item(address,value):
        return dict(resistor_address=address,rr_value_milliohms_hex=value,
          node1=dict(name_hex=(address[2:]+"x").encode().hex()),node2=dict(name_hex=(address[2:]+"y").encode().hex()))
    first=item("0xa","0x1.8p+1");second=item("0xb","0x1p+1");third=item("0xc","0x1p+2")
    rows=[dict(event="net_begin"),dict(first,event="create_tile")]
    final=[dict(first)]
    if kind!="plain":
        rows.append(dict(second,event="create_contact"));members=[first,second]
        if kind=="triangle":rows.append(dict(third,event="create_tile"));members.append(third)
        rows.append(dict(event="reduction",kind=kind,phase="before",members=[dict(x,slot=i)for i,x in enumerate(members)]))
        final=[dict(first,rr_value_milliohms_hex="0x1.4p+2")]
        if kind=="parallel":final=[dict(first,rr_value_milliohms_hex="0x1.2p+0")]
        if kind=="triangle":final=[dict(x,rr_value_milliohms_hex="0x1p+0")for x in members]
        rows.append(dict(event="reduction",kind=kind,phase="after",members=[dict(x,slot=i)for i,x in enumerate(final)]))
        if kind!="triangle":
            rows.append(dict(event="delete_resistor",resistor_address="0xb",deleted_value_milliohms_hex=second["rr_value_milliohms_hex"]))
            if reuse:
                fresh=item("0xb","0x1.cp+2");rows.append(dict(fresh,event="create_tile"));final.append(fresh)
    rows.append(dict(event="net_end"))
    for i,row in enumerate(final):
        rows.append(dict(row,event="snapshot_resistor"))
        rows.append(dict(row,event="emitted_resistor",ext_value_token=str(i+1)))
    for i,row in enumerate(rows):row.update(epoch=1,seq=i+1)
    emitted=[r for r in rows if r["event"]=="emitted_resistor"]
    target=dict(component=17,native_net="$131",native_cluster=28,
      native_primitive_records=[dict(raw=a.t.emitted_line(r),tokens=["resist"])for r in emitted],
      canonical_incidence=[dict(kind="R",name="R"+str(i),a=a.t.name(r["node1"]["name_hex"]),
        b=a.t.name(r["node2"]["name_hex"]),token=r["ext_value_token"])for i,r in enumerate(emitted)])
    return rows,target

def controls(expected):
    ctx=b.context(os.environ);a.source_guard(expected)
    spec=b.decode(b.frozen.regular(b.ROOT,a.SPEC).read_bytes())
    text=b.decode(b.frozen.regular(b.ROOT,a.SOURCE_TEXT).read_bytes())
    sources={n:text[n]["text"].encode()for n in spec["before"]}
    after,rules=a.derive(sources)
    assert len(after)==6 and len(rules)==19
    positive=["actual_qualified_six_source_reversible_derivation"];refusals=[];life=[]
    for kind in ("plain","series","parallel","triangle"):
        rows,target=fixture(kind);r=a.replay(rows,target)
        assert r["all_observed_target_value_ancestry_complete"]and r["physical_acceptance"]is False
        assert all(not x["physical_ownership_proved"]for x in r["emitted"])
        positive.append("actual_replay_synthetic_"+kind)
    rows,target=fixture(reuse=True);r=a.replay(rows,target)
    assert len([n for n,x in r["nodes"].items()if not x["parents"]and x["record"]["resistor_address"]=="0xb"])==2
    positive.append("address_reuse_requires_observed_retirement")
    def reject(label,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError,TypeError):refusals.append(label)
        else:raise AssertionError("accepted "+label)
    for label in ("missing_creator","stale_operand","missing_before","missing_after","wrong_survivor","wrong_kind",
                  "duplicate_operand","wrong_slot","live_recreation","retired_emission","missing_retirement",
                  "sequence_gap","unobserved_value","canonical_drift"):
        rows,target=fixture(reuse=label=="missing_retirement")
        before=next(x for x in rows if x["event"]=="reduction"and x["phase"]=="before")
        end=next(x for x in rows if x["event"]=="reduction"and x["phase"]=="after")
        if label=="missing_creator":rows.pop(1)
        elif label=="stale_operand":before["members"][0]["rr_value_milliohms_hex"]="0x1p+9"
        elif label=="missing_before":rows.remove(before)
        elif label=="missing_after":rows.remove(end)
        elif label=="wrong_survivor":end["members"][0]["resistor_address"]="0xb"
        elif label=="wrong_kind":end["kind"]="unobserved"
        elif label=="duplicate_operand":before["members"][1]["resistor_address"]="0xa"
        elif label=="wrong_slot":before["members"][0]["slot"]=9
        elif label=="live_recreation":rows.insert(2,copy.deepcopy(rows[1]))
        elif label=="retired_emission":rows[-1]["resistor_address"]="0xb"
        elif label=="missing_retirement":rows=[x for x in rows if x["event"]!="delete_resistor"]
        elif label=="unobserved_value":rows[-1]["rr_value_milliohms_hex"]="0x1p+9"
        elif label=="canonical_drift":target["canonical_incidence"][0]["token"]="999"
        for i,x in enumerate(rows):x["seq"]=i+1
        if label=="sequence_gap":rows[-1]["seq"]+=1
        reject(label,lambda rows=rows,target=target:a.replay(rows,target))
    for label in ("missing_source","changed_source","extra_source","changed_expected_output"):
        bad=dict(sources)
        if label=="missing_source":bad.pop("resis/ResMerge.c")
        elif label=="changed_source":bad["resis/ResMerge.c"]+=b"\n"
        elif label=="extra_source":bad["resis/extra.c"]=b"synthetic"
        if label=="changed_expected_output":
            payload,changed=a.qualified_payload();changed=copy.deepcopy(changed)
            changed["after"]["resis/ResMerge.c"]["sha256"]="0"*64
            with patch.object(a,"qualified_payload",lambda root=b.ROOT:(payload,changed)):
                reject(label,lambda:a.derive(bad))
        else:reject(label,lambda bad=bad:a.derive(bad))
    with tempfile.TemporaryDirectory(prefix="ancestry-preservation-")as temp:
        root=Path(temp);primary=OSError("synthetic ancestry failure")
        def failed(*args):
            b.write(args[-1]/"target-events.json",b.encode(fixture()[0]))
            raise primary
        with patch.object(b,"preserve_current_source",lambda *x:None):
            try:b.run(ctx,{},b"",expected,root/"partial",failed)
            except OSError as exc:assert exc is primary
            else:raise AssertionError("missing primary")
        assert b.decode((root/"partial/target-events.json").read_bytes())==fixture()[0]
        life.append("actual_run_preserves_complete_available_events")
        with patch.object(b,"preserve_current_source",lambda *x:None),patch.object(a,"source_guard",side_effect=primary):
            try:b.run(ctx,{},b"",expected,root/"refusal",
              lambda *x:a.perform(*x,ancestry_controls=b"",coefficient_controls=b""))
            except OSError as exc:assert exc is primary
            else:raise AssertionError("source refusal lost")
        life.append("actual_production_perform_source_refusal_no_acquisition")
        def broken(*x):raise OSError("secondary write")
        with patch.object(b,"preserve_current_source",lambda *x:None),patch.object(b,"write",broken):
            try:b.run(ctx,{},b"",expected,root/"double",lambda *x:(_ for _ in ()).throw(primary))
            except OSError as exc:assert exc is primary
            else:raise AssertionError("primary replaced")
        life.append("actual_run_secondary_write_preserves_primary")
    assert(len(positive),len(refusals),len(life))==(6,18,3)
    return dict(status="PASS_MAGIC_ANCESTRY_SOURCE_CONTROLS",passed=True,
      counts=dict(positive=6,refusal=18,lifecycle=3),positive=positive,refusals=refusals,lifecycle=life,
      synthetic_ancestry_only=True,native_executed=False,physical_acceptance=False,
      current_context=dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False))

def main():
    p=argparse.ArgumentParser();p.add_argument("--pins-sha256",required=True);p.add_argument("--output",type=Path,required=True)
    x=p.parse_args();primary=None
    try:r=controls(x.pins_sha256)
    except BaseException as exc:
        primary=exc;r=dict(status="FAIL_MAGIC_ANCESTRY_SOURCE_CONTROLS",error=repr(exc),
          traceback=traceback.format_exc(),native_executed=False,physical_acceptance=False)
    raw=b.encode(r);print(raw.decode(),end="",flush=True)
    try:b.write(x.output,raw)
    except BaseException:
        if primary is None:raise
    if primary is not None:raise primary
if __name__=="__main__":main()
