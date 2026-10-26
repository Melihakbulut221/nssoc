#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Disabled, isolated four-tail Metal4 width hypothesis on current AVSS18."""
import copy, hashlib, json, os, sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_pcie_tx_phase_reset244_avss18_v1 as avss
q = avss.q
METHOD = "scripts/tx-phase-reset334-tail-m4-source-methods.json"
BASELINE = "docs/evidence/tx-phase-reset244-avss18-physical-native-result-20261025.json"
BASELINE_SHA = "6d1cc609af69edd9e1c34558b67f976997afd950b27c90db158652d369ce9d17"
BASELINE_STATUS = "PASS_BOTH_AVSS18_EXACT_MATERIAL_334_PHYSICAL_1010_TERMINALS_REQUIRES_FRESH_MIM_RC_LOADED"
TAIL_NETS = ("PHASE__XM__XDATA__TAIL", "PHASE__XM__XHOLD__TAIL",
             "PHASE__XS__XDATA__TAIL", "PHASE__XS__XHOLD__TAIL")
OLD_HALF = 0.6
NEW_HALF = 1.2
OLD_CALL = "                rect(4, x - 0.6, start - 0.2, x + 0.6, y + 0.2)"
NEW_CALL = ("                tail_half_width = 1.2 if net in " + repr(TAIL_NETS) + " else 0.6\n"
            "                rect(4, x - tail_half_width, start - 0.2, x + tail_half_width, y + 0.2)")
TAIL_EDITS = [(OLD_CALL, NEW_CALL)]
ORIGINAL_EDITS = copy.deepcopy(q.MAIN_EDITS)
SCALAR = {"device","net","source_layer","actual_pin_um","escape_lane_um","escape_y_um"}
MIM = {"device","plus_net","minus_net","plus_native_plate_um","minus_native_plate_um",
       "plus_contact_outside_native_mim","plus_escape_um","minus_escape_um"}
REPORT_CHANGED = {"input_sha256","output_sha256","scope","avss18_report_comparison","avss18_derivation"}
ADDITIONS = {"tail_m4_plan","tail_m4_derivation","tail_m4_scope"}
AUTH_FLAGS = ("native_generation_authorized","native_material_authorized","simulation_authorized",
              "extraction_authorized","continuation_authorized")

def digest(value):
    return hashlib.sha256(value).hexdigest()

def host():
    avss.host()

def methods():
    m=json.loads((ROOT/METHOD).read_text())
    for p,h in m["protected"].items():
        assert digest((ROOT/p).read_bytes())==h,p
    assert m["simulation_authorized"] is m["extraction_authorized"] is m["continuation_authorized"] is False
    return m

def baseline():
    raw=(ROOT/BASELINE).read_bytes();assert digest(raw)==BASELINE_SHA
    r=json.loads(raw)
    assert r["status"]==BASELINE_STATUS and r["validation_errors"]==[]
    assert r["source_head"]=="5ddb5be6843a967305dbb5a45b426070c0f8fabd"
    reservation=r["release_prerequisite"]
    assert reservation["tag"]=="cloud-results-40211309923-1-tx-phase-reset244-avss18-physical"
    assert reservation["tested_source"]==r["source_head"] and reservation["release_id"]==423515853
    assert reservation["target_verified"]is True and reservation["assets_overwritten"]is False
    assert r["exact_one_native_rectangle_per_polarity_proved"] is True
    assert r["original_baseline_byte_unchanged"] is True
    assert set(r["variants"])=={"p","n"}
    for p in ("p","n"):
        v=r["variants"][p];g=v["generation"]
        assert v["sources_unchanged"] is True
        assert g["primitive_counts"]==dict(hbt=106,rppd=130,cmim=8,physical_ptap=90)
        assert len(g["instances"])==334 and len(g["routes"])==586
        assert g["origin_translation_um"]==[-0.0,-3.97]
        assert g["bbox_um"]==[0,0,1440.0,2413.03]
        assert g["preset_polarity"]==p
        assert g["input_sha256"][str(ROOT/"hw/soc/flow/make_pcie_tx_phase_reset244_avss18_v1.py")]==digest((ROOT/"hw/soc/flow/make_pcie_tx_phase_reset244_avss18_v1.py").read_bytes())
    return r

def grid_dbu(value):
    assert type(value)in (int,float),"A source coordinate must be a real numeric JSON scalar"
    d=Decimal(str(value))*1000
    assert d.is_finite() and d==d.to_integral_value(),("Source coordinate is off the native1nm grid",value)
    return int(d)

def target_plan(report):
    assert report["origin_translation_um"]==[-0.0,-3.97]
    devices={d["name"]:d for d in report["instances"]}
    assert len(devices)==334 and len(report["routes"])==586
    counts=Counter();selected=[]
    for route in report["routes"]:
        if set(route)==SCALAR:
            counts["scalar"]+=1
            if route["net"] not in TAIL_NETS:continue
            d=devices[route["device"]];role=route["device"].rsplit("__",1)[1]
            assert role in ("XSA","XSB","XT") and d["kind"]=="hbt" and d["nx"]==4
            assert route["device"]==route["net"][:-4]+role
            terminal=2 if role in ("XSA","XSB")else 0
            assert d["nets"][terminal]==route["net"]
            assert route["source_layer"]==(2 if terminal==2 else 1)
            buses=[b for b in report["local_buses"]if b["net"]==route["net"]]
            assert len(buses)==1 and buses[0]["row"]==d["placement_row"]
            bus=buses[0];x=route["escape_lane_um"];start=route["escape_y_um"];y=bus["y_um"]
            assert bus["left_um"]==460.0 and bus["right_um"]==504.0
            assert x=={"XSA":461.0,"XSB":485.0,"XT":503.0}[role]
            assert start<y
            # Recorded source decimals are exactly on-grid. Convert before
            # arithmetic, then perform all expected geometry in integer DBU.
            xd,sd,yd=grid_dbu(x),grid_dbu(start),grid_dbu(y)
            boxes=[]
            for half in (600,1200):
                source=[xd-half,sd-200,xd+half,yd+200]
                native=[v+(0 if i%2==0 else -3970)for i,v in enumerate(source)]
                boxes.append((source,native))
            selected.append(dict(net=route["net"],device=route["device"],role=role,
                terminal="E" if terminal==2 else "C",placement_row=d["placement_row"],
                escape_lane_um=x,escape_y_um=start,bus_y_um=y,layer=[50,0],
                old_source_box_dbu=boxes[0][0],new_source_box_dbu=boxes[1][0],
                old_native_box_dbu=boxes[0][1],new_native_box_dbu=boxes[1][1]))
        else:
            assert set(route)==MIM and devices[route["device"]]["kind"]=="capacitor"
            counts["mim"]+=1
    assert counts==dict(scalar=578,mim=8)
    assert Counter(x["net"]for x in selected)==dict.fromkeys(TAIL_NETS,3)
    assert Counter((x["net"],x["role"])for x in selected)==Counter((n,r)for n in TAIL_NETS for r in ("XSA","XSB","XT"))
    assert len({tuple(x["old_native_box_dbu"])for x in selected})==12
    return sorted(selected,key=lambda x:(x["placement_row"],x["escape_lane_um"]))

def derivations():
    assert q.MAIN_EDITS==ORIGINAL_EDITS
    flat,base,current,proof=avss.derivations()
    changed=q.exact_replace(current,TAIL_EDITS)
    result=dict(current_AVSS18_main_sha256=digest(current.encode()),
        candidate_main_sha256=digest(changed.encode()),flatten_sha256=digest(flat.encode()),
        edits=TAIL_EDITS,exact_reversal=True,prior_AVSS18_derivation=proof)
    # The persisted contract uses JSON arrays, including nested reversible edits.
    return flat,current,changed,json.loads(json.dumps(result,allow_nan=False))

def validate_generation(before,after,polarity):
    assert polarity in ("p","n")
    assert before["preset_polarity"]==after["preset_polarity"]==polarity
    assert set(after)==(set(before)-{"avss18_report_comparison","avss18_derivation"})|ADDITIONS
    for key in set(before)-REPORT_CHANGED:
        assert before[key]==after[key],("Changed qualified generation field",key)
    want=target_plan(before)
    assert target_plan(after)==want and after["tail_m4_plan"]==want
    assert after["tail_m4_derivation"]==derivations()[3]
    assert before["bbox_um"]==after["bbox_um"] and before["origin_translation_um"]==after["origin_translation_um"]
    return dict(status="PASS_SOURCE_PLAN_AND_REPORT_ONLY_NOT_MATERIAL",
        changed_M4_rectangles=12,all_other_report_fields_equal=True,
        expected_native_box_deltas=want,native_material_proved=False,
        native_net_ownership_proved=False,DRC_LVS_RC_or_electrical_accepted=False)

def main():
    host();m=methods()
    assert m["native_generation_authorized"] is True,"Disabled source-only candidate"
    baseline_result=baseline()
    flat,current,changed,proof=derivations()
    assert proof==m["source_derivation"]
    saved=copy.deepcopy(q.MAIN_EDITS)
    try:
        q.MAIN_EDITS=saved+copy.deepcopy(avss.TRUNK_EDITS)+copy.deepcopy(TAIL_EDITS)
        assert q.derivations()==(flat,changed)
        q.main()
    finally:
        q.MAIN_EDITS=saved
    out=Path(sys.argv[sys.argv.index("--out")+1]);path=out/"result.json"
    report=json.loads(path.read_text());polarity=report["preset_polarity"]
    report["tail_m4_plan"]=target_plan(report)
    report["tail_m4_derivation"]=proof
    report["tail_m4_scope"]="Only12 exact main-latch TAIL Metal4 widths1.2to2.4um; no electrical claim."
    report["input_sha256"].update({str(Path(__file__).resolve()):digest(Path(__file__).read_bytes()),
        str(ROOT/BASELINE):BASELINE_SHA})
    validate_generation(baseline_result["variants"][polarity]["generation"],report,polarity)
    path.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    methods()

if __name__=="__main__":main()
