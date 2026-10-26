#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-only plan for an additive CDR500 master-tail wire experiment.

This does not generate geometry or accept electrical behavior. Native ownership,
full parent clearance, unchanged device/terminal topology, DRC/LVS, fresh wire/MIM
RC and the original electrical gates remain mandatory.
"""
import copy
from decimal import Decimal

TOP = "nssoc_cdr_pd500_resistor_v59"
CHILD = "pd_child_sampler_cd"
LEAF = "nssoc_rx_sampler_active_input_layout_v57"
LANES_DBU = (371000,439805,636555,686205,878815,925320,990875,1040525)
NAMES = ("M_CS0","M_CS1","M_CH0","M_CH1","M_T3","M_T0","M_T1","M_T2")
ORIGIN_DBU = (0,-3970)
BUS_PRE_ORIGIN_DBU = (370000,178400,1041525,181600)
BUS_DBU = (370000,174430,1041525,177630)
CENTER_Y_DBU = 176030
PARAMETERS = dict(b_layer="TopMetal1",t_layer="TopMetal2",
                  vn_columns=2,vn_rows=2,vt1_columns=1,vt1_rows=1,
                  vt2_columns=1,vt2_rows=1)
PLACEMENTS = {"sd":(993600,272000,28,17), "sc":(993600,1461520,124,61)}
ALLOWED_LAYERS = ((126,0),(133,0),(134,0))
CLEARANCE_DBU = {126:1640,133:1060,134:2000}
EXPECTED_ANCHORS = {
  "T003_D": [
    3,
    "sg13_lv_nmos",
    "D",
    28,
    "$131",
    8,
    1885245,
    406030,
    17
  ],
  "T004_D": [
    4,
    "sg13_lv_nmos",
    "D",
    28,
    "$131",
    8,
    1931750,
    406030,
    17
  ],
  "T005_D": [
    5,
    "sg13_lv_nmos",
    "D",
    28,
    "$131",
    8,
    1997305,
    406030,
    17
  ],
  "T006_D": [
    6,
    "sg13_lv_nmos",
    "D",
    28,
    "$131",
    8,
    2046955,
    406030,
    17
  ],
  "T032_D": [
    32,
    "sg13_lv_nmos",
    "D",
    124,
    "$680",
    8,
    1885245,
    1595550,
    61
  ],
  "T033_D": [
    33,
    "sg13_lv_nmos",
    "D",
    124,
    "$680",
    8,
    1931750,
    1595550,
    61
  ],
  "T034_D": [
    34,
    "sg13_lv_nmos",
    "D",
    124,
    "$680",
    8,
    1997305,
    1595550,
    61
  ],
  "T035_D": [
    35,
    "sg13_lv_nmos",
    "D",
    124,
    "$680",
    8,
    2046955,
    1595550,
    61
  ],
  "T061_E": [
    61,
    "npn13G2",
    "E",
    28,
    "$131",
    10,
    1371525,
    388022,
    17
  ],
  "T062_E": [
    62,
    "npn13G2",
    "E",
    28,
    "$131",
    10,
    1440330,
    388022,
    17
  ],
  "T064_E": [
    64,
    "npn13G2",
    "E",
    28,
    "$131",
    10,
    1637080,
    388022,
    17
  ],
  "T065_E": [
    65,
    "npn13G2",
    "E",
    28,
    "$131",
    10,
    1686730,
    388022,
    17
  ],
  "T115_E": [
    115,
    "npn13G2",
    "E",
    124,
    "$680",
    10,
    1371525,
    1577542,
    61
  ],
  "T116_E": [
    116,
    "npn13G2",
    "E",
    124,
    "$680",
    10,
    1440330,
    1577542,
    61
  ],
  "T118_E": [
    118,
    "npn13G2",
    "E",
    124,
    "$680",
    10,
    1637080,
    1577542,
    61
  ],
  "T119_E": [
    119,
    "npn13G2",
    "E",
    124,
    "$680",
    10,
    1686730,
    1577542,
    61
  ]
}

def dbu(value):
    # Historical JSON contains harmless binary float spellings, but no rounding
    # can hide a location off the actual 1 nm database grid.
    x=Decimal(str(value))*1000
    n=int(x.to_integral_value())
    assert abs(x-n)<Decimal("0.000001"), ("Off-database-grid coordinate",value)
    return n

def validate_mapping(handoff):
    assert handoff["current_candidate_GDS_sha256"]=="fb2a773c4d3a3ffab6acfe7718a55fa5db0c2621a6c75377940c95a7989b70b5"
    assert handoff["source_leaf_origin_translation_um"]==[0,-3.97]
    assert handoff["route_coordinates_before_origin_translation"] is True
    rows=handoff["actual_M_TE_routes"]
    assert len(rows)==8 and tuple(x["device"] for x in rows)==NAMES
    for i,r in enumerate(rows):
        assert r["net"]=="M_TE" and dbu(r["escape_lane_um"])==LANES_DBU[i]
        assert dbu(r["escape_y_um"])==(119990 if i<4 else 155600)
        assert dbu(r["escape_width_um"])==400
        assert r["source_layer"]==(2 if i<4 else 1)
        assert r["pin_via_columns"]==(4 if i<4 else 1) and r["lane_via_columns"]==8
    anchors=handoff["native_terminal_rows"]
    assert len(anchors)==16 and len({r["wire_anchor"] for r in anchors})==16
    assert {r["wire_anchor"]:[r["device"],r["model"],r["terminal"],r["native_cluster"],r["native_net"],r["metal"],*r["point_dbu"],r["wire_component"]] for r in anchors}==EXPECTED_ANCHORS
    for label,tag in (("D","sd"),("C","sc")):
        rec=handoff["target_native_nodes"][label]
        dx,dy,cluster,component=PLACEMENTS[tag]
        assert rec["parent"]==tag and rec["source_net"]=="M_TE"
        assert [dbu(x) for x in rec["parent_translation_um"]]==[dx,dy]
        assert rec["native_cluster"]==cluster and rec["wire_component"]==component
    expected={
      28:({"T061_E","T062_E","T064_E","T065_E"},{"T003_D","T004_D","T005_D","T006_D"},17),
      124:({"T115_E","T116_E","T118_E","T119_E"},{"T032_D","T033_D","T034_D","T035_D"},61)}
    for cluster,(es,ds,component) in expected.items():
        subset=[r for r in anchors if r["native_cluster"]==cluster]
        assert {r["wire_anchor"] for r in subset}==es|ds and len(subset)==8
        assert all(r["wire_component"]==component for r in subset)
        for r in subset:
            assert r["terminal"]==("E" if r["wire_anchor"] in es else "D")
            assert r["model"]==("npn13G2" if r["terminal"]=="E" else "sg13_lv_nmos")
            assert r["metal"]==(10 if r["terminal"]=="E" else 8)
    return True

def candidate_plan(handoff):
    validate_mapping(handoff)
    # Preserve the old 20 um device-to-bus planning margin and 6 um grid.
    assert 180000-155600>=20000 and 180000%6000==0
    assert BUS_PRE_ORIGIN_DBU[3]-BUS_PRE_ORIGIN_DBU[1]==3200
    assert tuple(v+(ORIGIN_DBU[0] if i%2==0 else ORIGIN_DBU[1])
                 for i,v in enumerate(BUS_PRE_ORIGIN_DBU))==BUS_DBU
    taps=[{"device":name,"center_dbu":[x,CENTER_Y_DBU]} for name,x in zip(NAMES,LANES_DBU)]
    placed=[]
    for tag,(dx,dy,cluster,component) in PLACEMENTS.items():
        placed.append({"tag":tag,"translation_dbu":[dx,dy],
          "old_native_cluster":cluster,"old_wire_component":component,
          "bus_dbu":[v+(dx if i%2==0 else dy) for i,v in enumerate(BUS_DBU)],
          "tap_centers_dbu":[[x, y] for x,y in ([t["center_dbu"][0]+dx,t["center_dbu"][1]+dy] for t in taps)]})
    return {"status":"UNEXECUTED_ADDITIVE_WIRE_CANDIDATE","top":TOP,"child":CHILD,
      "leaf":LEAF,"dbu_um":0.001,"old_bus_center_pre_origin_um":240,
      "new_bus_pre_origin_dbu":list(BUS_PRE_ORIGIN_DBU),"new_bus_dbu":list(BUS_DBU),
      "native_via_parameters":copy.deepcopy(PARAMETERS),"local_taps":taps,
      "placements":placed,"allowed_added_layers":[list(x) for x in ALLOWED_LAYERS],
      "minimum_planning_clearance_dbu":copy.deepcopy(CLEARANCE_DBU),
      "devices_changed":0,"reference_changed":False,"old_routes_preserved":True,
      "electrical_improvement_proven":False,"physical_accepted":False,
      "simulation_authorized":False,"native_execution_authorized":False}
