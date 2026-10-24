#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind four already-qualified p4 master replacements; no native acceptance."""
import copy,hashlib,json,traceback
from pathlib import Path
import observe_tx_native_clock_role_parameters as old
ROOT=Path(__file__).resolve().parents[1]
P4=tuple("p4_"+str(i)for i in range(4))
PINS={
 "docs/evidence/tx-p4-drive3-physical-pass-20261020.json":"67a8fa0c3a0ac53c73cfdfdd328134ee725ac315e62b28927583a6e46232057e",
 "scripts/generate_tx_p4_drive3.py":"9d9c9c0da3b3dc949bb36235c0e067269ddb702d7dfe43c0403896a89309da21",
 "docs/evidence/tx-v5-timing-priority-physical-pass-20261019.json":"2e78b68f71b4b95b354544b3d5b089dd64aee6d6fdc918d1b1def825164289c4",
 "scripts/observe_tx_native_clock_role_parameters.py":"03fc06ae693924f63f5b3c4f758d43926df66fc166050a0776b1a8729ab4f7c4"}
KINDS={**old.KINDS,**dict.fromkeys(P4,"pre")}
EXPECTED_EMITTERS=863
def sha(b):return hashlib.sha256(b).hexdigest()
def evidence():
    for p,h in PINS.items():assert sha((ROOT/p).read_bytes())==h,p
    old.source_catalog()
    r=json.loads((ROOT/"docs/evidence/tx-p4-drive3-physical-pass-20261020.json").read_text())
    h=json.loads((ROOT/"docs/evidence/tx-v5-timing-priority-physical-pass-20261019.json").read_text())
    validate_receipt(r)
    return r,h
def validate_receipt(r):
    assert r["run"]==39447746971 and r["source_head"]=="4e9d1b6ecca60dd61b808a9d54de185f190f827c"
    assert r["summary_asset"]==659699817 and r["summary_sha256"]=="f351c3ab008b764155594fe395f83b319ca384c32073c1106d7bebbb508319cc"
    a=r["report"];assert a["source_head"]==r["source_head"]
    assert a["status"]==r["status"]=="PASS_TX_FOUR_P4_NATIVE_DRIVE3_PHYSICAL_REQUIRES_FRESH_RC_AND_LOADED_GATES"
    assert a["outputs"]["layout/result.json"]=="b6a29ebb58dd4ef4127a69d94974676421ca9005d8076bf6c727e0a19bd3e621"
    assert a["outputs"]["layout/schematic.cir"]=="d74032f0032125223708b04ceef3f7ed38c49f7624c10966c89c229974c699b6"
    d=a["geometry_delta"];assert d["reference_hbts"]==589 and d["reference_emitters"]==EXPECTED_EMITTERS
    assert all(d[k]is True for k in ("original_master_drawings_unchanged","parent_drawings_routes_and_pins_unchanged","lef_byte_identical","serialized_gds_verified"))
    assert all(d[k]is False for k in ("electrical_accepted","qualified_pex","full_phy_accepted"))
    assert len(d["controls"])==3 and all(x["rejected"]for x in d["controls"])
    assert len(d["changes"])==len(d["circuit_changes"])==4
    assert [x["tag"]for x in d["changes"]]==list(P4)==[x["tag"]for x in d["circuit_changes"]]
    assert {k:v["kind"]for k,v in a["layout"]["placements"].items()}==KINDS
    for change,card in zip(d["changes"],d["circuit_changes"],strict=True):
        tag=change["tag"];p=a["layout"]["placements"][tag]
        assert change["original_kind"]=="pre_low"and change["candidate_kind"]=="pre"
        assert change["original_emitters"]==19 and change["candidate_emitters"]==55 and change["public_pin_rectangles_identical"]is True
        assert p["kind"]=="pre"and p["transform"]==change["after_transform"]and p["bbox_um"]==change["after_bbox"]
        assert card["source_master"]=="a"and len(card["original_cards"])==len(card["candidate_cards"])==54
        for key,nx in (("original_cards",1),("candidate_cards",3)):
            q=[x for x in card[key]if x[0].startswith("Q")]
            assert len(q)==19 and [x[0]for x in q]==["Q"+tag+"_D"+str(i)for i in range(19)]
            for i,row in enumerate(q):
                assert row[5]=="npn13G2"and row[6:]==["Nx="+str(1 if i==0 else nx),"we=0.07u","le=0.9u","m=1"]
            assert sum(float(x[6].split("=")[1])for x in q)==(19 if nx==1 else 55)
    p=a["physical"];assert p["status"]=="PASS_NATIVE_PDK_TX_TREE1674_DRC_LVS_AND_FAULT_CONTROLS"
    assert p["steps"]["drc"]["measurement"]["category_count"]==560 and p["steps"]["drc"]["measurement"]["markers"]==0
def normalize_plan(plan,cm,receipt,historical):
    validate_receipt(receipt)
    assert plan==historical["report"]["plan"],"Not the exact independently pinned historical topology"
    assert cm==receipt["report"]["layout"],"Not the independently pinned actual physical metadata"
    nodes=plan["nodes"]
    assert len(nodes)==31 and {n["label"]:n["kind"]for n in nodes}==old.KINDS
    assert len({n["label"]for n in nodes})==31
    result=copy.deepcopy(plan)
    for n in result["nodes"]:
        if n["label"]in P4:
            assert n["kind"]=="pre_low";n["kind"]="pre"
    assert {n["label"]:n["kind"]for n in result["nodes"]}==KINDS
    restored=copy.deepcopy(result)
    for n in restored["nodes"]:
        if n["label"]in P4:n["kind"]="pre_low"
    assert restored==plan,"Unplanned topology or clock/input/output change"
    return result
def failure_identity(w):
    assert w["type"]=="AssertionError"and w["message"]=="Native child kind disagrees with pinned plan"
    assert w["frame"]==dict(file="observe_tx_native_clock_role_parameters.py",function="inspect_native",line=142)
    assert w["label"]=="p4_0"and w["plan_kind"]==w["catalog_kind"]=="pre_low"and w["physical_kind"]=="pre"
def bind(g):
    receipt,history=evidence()
    original=copy.deepcopy(g["plan"]);mapped=normalize_plan(original,g["cm"],receipt,history)
    # Re-evaluate the exact rejected observer before any metadata adaptation.
    try:old.inspect_native(g)
    except AssertionError as e:
        tb=e.__traceback__
        while tb.tb_next is not None:tb=tb.tb_next
        f=tb.tb_frame
        w={"type":type(e).__name__,"message":str(e),"frame":{"file":Path(f.f_code.co_filename).name,"function":f.f_code.co_name,"line":tb.tb_lineno},
         "label":f.f_locals["label"],"plan_kind":f.f_locals["kind"],
         "catalog_kind":old.KINDS[f.f_locals["label"]],"physical_kind":f.f_locals["placement"]["kind"],
         "traceback":traceback.format_exc()}
        failure_identity(w)
    else:raise AssertionError("Original exact kind rejection did not reproduce")
    assert g["plan"]==original
    adapted=dict(g);adapted["plan"]=mapped
    return adapted,{"original_failure":w,"only_changed_kind_labels":list(P4),
     "all_other_topology_fields_unchanged":True,"actual_layout_metadata_unchanged":True,
     "expected_emitters":EXPECTED_EMITTERS,"physical_run":receipt["run"],"physical_source":receipt["source_head"],
     "actual_layout_metadata_sha256":receipt["report"]["outputs"]["layout/result.json"],
     "independent_source_pins":PINS,"role_accepted":False,"electrical_accepted":False,"full_phy_accepted":False}
def controls():
    r,h=evidence();p=h["report"]["plan"];cm=r["report"]["layout"]
    good=normalize_plan(p,cm,r,h);assert sum(old.SPECS[k]["emitters"]for k in KINDS.values())==863
    faults=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError):faults.append(dict(name=name,rejected=True))
        else:raise AssertionError("Accepted corrupt p4 provenance "+name)
    for name in ("wrong_run","wrong_source","wrong_summary","wrong_layout_hash","missing_replacement","wrong_tag","wrong_master","wrong_before_kind","wrong_after_kind","changed_pin","wrong_selector_Nx","wrong_reference_Nx","wrong_source_card_endpoint","physical_kind","wrong_emitters","missing_physical_control"):
        bad=copy.deepcopy(r);d=bad["report"]["geometry_delta"]
        if name=="wrong_run":bad["run"]+=1
        elif name=="wrong_source":bad["source_head"]="0"*40
        elif name=="wrong_summary":bad["summary_sha256"]="0"*64
        elif name=="wrong_layout_hash":bad["report"]["outputs"]["layout/result.json"]="0"*64
        elif name=="missing_replacement":d["changes"].pop()
        elif name=="wrong_tag":d["changes"][0]["tag"]="a"
        elif name=="wrong_master":d["circuit_changes"][0]["source_master"]="p8_0"
        elif name=="wrong_before_kind":d["changes"][0]["original_kind"]="pre"
        elif name=="wrong_after_kind":d["changes"][0]["candidate_kind"]="pre_low"
        elif name=="changed_pin":d["changes"][0]["public_pin_rectangles_identical"]=False
        elif name=="wrong_selector_Nx":
            next(x for x in d["circuit_changes"][0]["candidate_cards"]if x[0]=="Qp4_0_D13")[6]="Nx=1"
        elif name=="wrong_reference_Nx":d["circuit_changes"][0]["candidate_cards"][0][6]="Nx=3"
        elif name=="wrong_source_card_endpoint":
            # Receipt itself is immutable; require the independent complete card inventory too.
            d["circuit_changes"][0]["candidate_cards"][0][1]="other"
        elif name=="physical_kind":bad["report"]["layout"]["placements"]["p4_0"]["kind"]="pre_low"
        elif name=="wrong_emitters":d["reference_emitters"]=719
        else:d["controls"].pop()
        reject(name,lambda bad=bad:validate_bound_receipt(bad,r))
    for name in ("clock","input","output","p4kind","extra_field","physical_bbox"):
        q=copy.deepcopy(p);c=copy.deepcopy(cm)
        if name=="clock":q["nodes"][0]["clock"]="swapped"
        elif name=="input":q["nodes"][0]["inputs"][0]="other"
        elif name=="output":q["nodes"][0]["output"]="other"
        elif name=="p4kind":next(n for n in q["nodes"]if n["label"]=="p4_0")["kind"]="pre"
        elif name=="extra_field":q["new"]="other"
        else:c["placements"]["p4_0"]["bbox_um"]="(0,0;1,1)"
        reject("plan_"+name,lambda q=q,c=c:normalize_plan(q,c,r,h))
    w=dict(type="AssertionError",message="Native child kind disagrees with pinned plan",
      frame=dict(file="observe_tx_native_clock_role_parameters.py",function="inspect_native",line=142),
      label="p4_0",plan_kind="pre_low",catalog_kind="pre_low",physical_kind="pre")
    failure_identity(w)
    for name in ("type","message","frame","label","plan_kind","physical_kind"):
        bad=copy.deepcopy(w);bad[name]="changed"
        reject("original_"+name,lambda bad=bad:failure_identity(bad))
    assert len(faults)==28
    return dict(status="PASS_EXACT_FOUR_P4_HISTORY_AND28_FAULTS_NOT_NATIVE_ROLES",faults=faults,native_execution=False)
def validate_bound_receipt(candidate,expected):
    # Entire exact old producer receipt is independently hash-pinned in evidence().
    # The semantic assertions above supplement rather than replace byte identity.
    assert candidate==expected,"Changed complete independently pinned producer receipt"
    validate_receipt(candidate)
