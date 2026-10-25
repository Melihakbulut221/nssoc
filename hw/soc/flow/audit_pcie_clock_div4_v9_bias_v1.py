#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Strict saved-GDS two-pull-down resistor geometry delta and unchanged intrinsic audit.

No full-route identity claim: every changed route requires fresh DRC/LVS/RC.
"""
import argparse
from collections import Counter
from decimal import Decimal, ROUND_FLOOR
import hashlib
import json
from pathlib import Path
import pya
import audit_pcie_clock_div4_v7_power_v3 as parent

OLD_TOP = "nssoc_clock_div4_v8_cap_v1_layout"
NEW_TOP = "nssoc_clock_div4_v9_bias_v1_layout"
BASE_GDS_SHA = "4361db967f0df1d340360f6b50461274b8a36cb49d208072a911cfd2077c78c1"
BASE_RESULT_SHA = "0e6e0ed365a2c4373ef85dc9236be3f59639472a785b3165e38c077f0702966d"
PARENT_SHA = "a1a1e4deaf92e48baa55a6e7d6393e6eef2c0627b68ab4b4daf464746a7def2b"
pin, require = parent.pin, parent.require


def geometry_key(geometry):
    return tuple((k, tuple(sorted(p.to_s() for p in r.merged().each()))) for k, r in sorted(geometry.items()))


def primitive_matches(instances, declared, translation, dbu):
    selected = {}
    used = set()
    for device in declared:
        category = {"hbt": "npn13G2", "resistor": "rppd", "capacitor": "cmim", "substrate_tap": "ptap1"}[device["kind"]]
        point = [round((v + translation[i]) / dbu) for i, v in enumerate(device["placement_um"])]
        trans = pya.ICplxTrans(1, 0, False, *point)
        found = [i for i, row in enumerate(instances) if row["cell"].split("$")[0] == category and row["transform"] == trans]
        require(len(found) == 1 and found[0] not in used, "Each original intrinsic exists at its exact declared new placement")
        i = found[0]
        used.add(i)
        selected[device["name"]] = instances[i]
    require(len(selected) == len(used) == 91, "Exact 91 intrinsic identities")
    other = [r for i, r in enumerate(instances) if i not in used]
    require(len(other) == 634 and all(r["cell"].split("$")[0] == "via_stack" for r in other), "All 634 remaining native leaves are via arrays")
    return selected, other


CAPS = {"DIV__XCP", "DIV__XCN"}
PULLDOWNS = {"DIV__XDP", "DIV__XDN"}


def mim_template(width, length, tech, dbu):
    """Independent Decimal rectangles from frozen SG13 cmim rules, no PCell call."""
    D = lambda value: Decimal(str(value))
    w, length, unit = D(width), D(length), D(dbu)
    grid, epsilon = D("0.005"), D(tech["epsilon1"])
    cut, over, enclosure = (D(tech[k]) for k in ("TV1_a", "Mim_d", "TV1_d"))
    spacing, bottom = D("0.84"), D(tech["Mim_c"])
    require((cut, over, enclosure, bottom, epsilon) == tuple(map(D, ["0.42", "0.36", "0.42", "0.6", "0.001"])), "Frozen native MIM technology constants")
    require(w in (D(20), D(24)) and length == w and unit == D("0.001"), "Only declared old/new square MIM at actual DBU")
    def axis(size):
        count = int(((size - 2 * over + spacing) / (cut + spacing) + epsilon).to_integral_value(rounding=ROUND_FLOOR))
        span = count * (cut + spacing) - spacing + 2 * over
        offset = (((size - span) / 2 / grid + epsilon).to_integral_value(rounding=ROUND_FLOOR)) * grid
        points = []
        at = over + offset
        while at + cut + over <= size + epsilon:
            points.append(at)
            at += cut + spacing
        require(len(points) == count, "Independent native MIM cut count")
        return points, over - enclosure + offset, at + enclosure - spacing
    xs, left, right = axis(w)
    ys, lower, upper = axis(length)
    regions = {}
    def box(layer, coordinates):
        integer = [v / unit for v in coordinates]
        require(all(v == v.to_integral_value() for v in integer), "All native MIM coordinates lie on exact DBU")
        regions.setdefault((layer, 0), pya.Region()).insert(pya.Box(*map(int, integer)))
    for x in xs:
        for y in ys:
            box(129, (x, y, x + cut, y + cut))
    box(36, (D(0), D(0), w, length))
    box(67, (-bottom, -bottom, w + bottom, length + bottom))
    box(126, (left, lower, right, upper))
    return {key: region.merged() for key, region in regions.items()}


def rppd_template(width, length, tech, dbu):
    """Independent Decimal geometry of only the frozen straight W1/L7-or8 PCell.

    SG13G2 rppd_code.py rules: one unbent stripe with bar contacts, no dogbone.
    Actual native polygons must equal all nine drawing/pin layer rectangles.
    """
    D = lambda value: Decimal(str(value))
    w, length, unit = D(width), D(length), D(dbu)
    require(w == D(1) and length in (D(7), D(8)) and unit == D("0.001"), "Only declared straight pull-down geometry and exact DBU")
    keys = ("grid", "M1_c1", "Cnt_a", "Cnt_b", "Cnt_d", "Rppd_b", "Sal_e", "Sal_c", "CntB_a1", "CntB_d", "rppd_met_over_cont", "epsilon1")
    values = tuple(D(tech[k]) for k in keys)
    require(values == tuple(map(D,[".005", ".05", ".16", ".18", ".07", ".18", ".2", ".2", ".34", ".07", ".07", ".001"])), "Exact frozen native straight resistor constants")
    grid, endcap, cut, spacing, polyover, psdover, salgap, salover, barmin, barover, metover, epsilon = values
    require(w - 2 * barover + epsilon >= barmin, "Actual W1 resistor uses native bar contacts")
    polyend = cut + polyover
    regions = {}
    def box(layer, datatype, coords):
        integer = [v / unit for v in coords]
        require(all(v == v.to_integral_value() for v in integer), "All independent resistor rectangles use exact DBU")
        regions.setdefault((layer, datatype), pya.Region()).insert(pya.Box(*map(int,integer)))
    # Body layers and both end enclosures are merged, just like native regions.
    for layer in (128,52): box(layer,0,(D(0),D(0),w,length))
    for layer in (28,111): box(layer,0,(-salover,D(0),w+salover,length))
    box(14,0,(-psdover,D(0),w+psdover,length))
    for y0,y1 in ((-salgap-polyend,D(0)),(length,length+salgap+polyend)):
        box(5,0,(D(0),y0,w,y1))
    for y0,y1 in ((-salgap-psdover-polyend,D(0)),(length,length+salgap+psdover+polyend)):
        for layer in (14,111): box(layer,0,(-psdover,y0,w+psdover,y1))
    for y0,y1 in ((-salgap-cut,-salgap),(length+salgap,length+salgap+cut)):
        box(6,0,(barover,y0,w-barover,y1))
        for datatype in (0,2): box(8,datatype,(barover-endcap,y0-metover,w-barover+endcap,y1+metover))
    return {key:region.merged() for key,region in regions.items()}


def compare_intrinsics(old_instances, new_instances, before, after, dbu, tech):
    ignored = {"placement_um", "bbox_um"}
    a = {r["name"]: {k: v for k, v in r.items() if k not in ignored} for r in before["instances"]}
    b = {r["name"]: {k: v for k, v in r.items() if k not in ignored} for r in after["instances"]}
    require(set(a) == set(b) and len(a) == 91, "Exact 91 original intrinsic identities")
    for name, old_metadata in a.items():
        expected = dict(old_metadata)
        if expected.get("source_subcircuit") == "NSSOC_CLOCK_DIV4_HBT_V8":
            expected["source_subcircuit"] = "NSSOC_CLOCK_DIV4_HBT_V9"
        if name in PULLDOWNS:
            require(expected["kind"] == "resistor" and expected["width_um"] == 1 and expected["length_um"] == 7, "Exact two original second-stage W1/L7 pull-downs")
            expected.update(length_um=8.0)
        require(b[name] == expected, "Only two declared pull-down lengths change; all 91-device connections and other bias retained")
    old, oldvias = primitive_matches(old_instances, before["instances"], before["origin_translation_um"], dbu)
    new, newvias = primitive_matches(new_instances, after["instances"], after["origin_translation_um"], dbu)
    for name in old:
        if name in PULLDOWNS:
            require(geometry_key(old[name]["geometry"]) == geometry_key(rppd_template(1,7,tech,dbu)), "Exact original pull-down equals independent native resistor rectangle formula")
            require(geometry_key(new[name]["geometry"]) == geometry_key(rppd_template(1,8,tech,dbu)), "Exact changed pull-down equals independent native resistor rectangle formula")
        elif name in CAPS:
            require(geometry_key(old[name]["geometry"]) == geometry_key(mim_template(24,24,tech,dbu)), "Exact original Cap24 MIM equals independent native rectangle formula")
            require(geometry_key(new[name]["geometry"]) == geometry_key(mim_template(24,24,tech,dbu)), "Exact retained Cap24 MIM equals independent native rectangle formula")
        else:
            require(geometry_key(old[name]["geometry"]) == geometry_key(new[name]["geometry"]), "Exact unchanged intrinsic native geometry")
    require(Counter(geometry_key(v["geometry"]) for v in oldvias) == Counter(geometry_key(v["geometry"]) for v in newvias), "Exact unchanged native via geometry multiset")
    return newvias

def power_arrays(vias, declared, translation, dbu, tech):
    require(len(declared) == 47, "All 47 power arrays declared")
    used = set()
    actual = []
    for row in declared:
        point = [round((v + translation[i]) / dbu) for i, v in enumerate(row["center_um"])]
        trans = pya.ICplxTrans(1, 0, False, *point)
        candidates = [i for i, v in enumerate(vias) if v["transform"] == trans and (134, 0) in v["geometry"]]
        require(len(candidates) == 1 and candidates[0] not in used, "Unique actual power array at declared center")
        i = candidates[0]
        used.add(i)
        require(geometry_key(vias[i]["geometry"]) == geometry_key(parent.via_template(row["parameters"], tech, dbu)), "Exact native power cut and enclosure geometry")
        actual.append(vias[i])
    return actual


def drawing_contract(regions, after, dbu):
    dx, dy = after["origin_translation_um"]
    def exists(layer, coordinates, message):
        box = pya.DBox(*coordinates).to_itype(dbu)
        box.move(round(dx / dbu), round(dy / dbu))
        require((pya.Region(box) - regions.get((layer, 0), pya.Region())).is_empty(), message)
    expected = []
    for net, x in (("DIV_AVDD", 96.0), ("AVSS", 112.0)):
        buses = [r for r in after["local_buses"] if r["net"] == net]
        require([r["row"] for r in buses] == [0, 1, 2], "All compact power rows")
        expected.append(dict(net=net, layer="TopMetal1", role="cross_row_trunk", rect_um=[x-3,buses[0]["y_um"]-3,x+3,buses[-1]["y_um"]+3]))
        for r in buses:
            expected.append(dict(net=net, layer="TopMetal2", role="row_bus", rect_um=[r["left_um"],r["y_um"]-3,r["right_um"],r["y_um"]+3]))
    require(after["additive_power_straps"] == expected, "Exact compact power topology")
    for r in expected:
        exists(126 if r["layer"] == "TopMetal1" else 134, r["rect_um"], "Entire compact power strap exists in actual GDS")
    require(len(after["local_buses"]) == 47, "All 47 declared local buses")
    for r in after["local_buses"]:
        exists(67,[r["left_um"],r["y_um"]-1,r["right_um"],r["y_um"]+1], "Entire declared local signal bus exists in actual GDS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "layout", "out", "pdk"):
        parser.add_argument("--"+name,type=Path,required=True)
    args = parser.parse_args()
    oldg, newg = args.baseline/(OLD_TOP+".gds"),args.layout/(NEW_TOP+".gds")
    oldr,newr=args.baseline/"result.json",args.layout/"result.json"
    require(pin(oldg)["sha256"]==BASE_GDS_SHA and pin(oldr)["sha256"]==BASE_RESULT_SHA,"Exact frozen Cap24 baseline")
    require(pin(parent.__file__)["sha256"]==PARENT_SHA,"Exact retained-layout geometry reader and independent via formulas")
    require(not args.out.exists(),"Fresh compact audit output")
    techpath=args.pdk/"libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json"
    inputs={str(p):pin(p) for p in [oldg,newg,oldr,newr,Path(__file__),Path(parent.__file__),techpath]}
    before,after=json.loads(oldr.read_text()),json.loads(newr.read_text())
    expected_sources = dict(before["source_circuit_sha256"])
    require(expected_sources.pop("hw/soc/analog/pcie/clock_div4_hbt_v8.spice") == "87a9c9af0df878208e644987b3318f715d1c54e4b60bbce6944a6af21c2c86dc", "Exact prior top circuit")
    expected_sources["hw/soc/analog/pcie/clock_div4_hbt_v9.spice"] = "5fc944cb5683dda328e6b3aedd21b2e206f03575a232394e8cb528d280e69c9a"
    require(expected_sources == after["source_circuit_sha256"] and before["primitive_counts"]==after["primitive_counts"],"Exact separately frozen two-pull-down source graph and primitive counts")
    old_layout,old_instances=parent.top_instances(oldg,OLD_TOP)
    new_layout,new_instances=parent.top_instances(newg,NEW_TOP)
    region_layout,box,regions,texts=parent.read_layout(newg,NEW_TOP)
    require(old_layout.dbu==new_layout.dbu==region_layout.dbu,"Exact actual DBU")
    dbu=new_layout.dbu
    require(len(old_instances)==len(new_instances)==725,"All actual 725 native leaves")
    require(box.to_dtype(dbu).to_s()==pya.DBox(*after["bbox_um"]).to_s(),"Actual compact bbox equals generated metadata")
    require(box.left==0 and box.bottom==0 and box.width()*dbu==960 and box.height()*dbu<600,"Compact physical dimensions")
    require(Counter(t[0] for t in texts[(67,25)])==Counter(["CLKP","CLKN","QP","QN","DIV_AVDD","AVSS","SUB"]),"Seven actual top port labels")
    tech=json.loads(techpath.read_text())["techParams"]
    vias=compare_intrinsics(old_instances,new_instances,before,after,dbu,tech)
    power=power_arrays(vias,after["additive_power_vias"],after["origin_translation_um"],dbu,tech)
    raw=parent.raw_gds_regions(newg,{v["cell"] for v in power})
    for row in power:require(geometry_key(row["geometry"])==geometry_key(raw[row["cell"]]),"All47 power via regions equal independent raw GDS boundaries")
    drawing_contract(regions,after,dbu)
    controls=[]
    def reject(fault,reason,fn):
        try:fn()
        except ValueError as error:
            require(str(error)==reason,"Actual compact corruption rejected for declared cause")
            controls.append(dict(fault=fault,status="EXPECTED_REJECTION",diagnostic=str(error)))
        else:raise ValueError("Actual compact corruption accepted")
    primitive=next(r for r in new_instances if r["cell"].split("$")[0]=="npn13G2")
    bad=[r for r in new_instances if r is not primitive]
    reject("remove_actual_hbt","Each original intrinsic exists at its exact declared new placement",lambda:compare_intrinsics(old_instances,bad,before,after,dbu,tech))
    bad=[dict(r,geometry=dict(r["geometry"])) for r in new_instances]
    bad[next(i for i,r in enumerate(new_instances) if r is primitive)]["geometry"][(8,0)]=pya.Region()
    reject("remove_hbt_metal1","Exact unchanged intrinsic native geometry",lambda:compare_intrinsics(old_instances,bad,before,after,dbu,tech))
    bad=[dict(r,geometry=dict(r["geometry"])) for r in vias]
    index=next(i for i,r in enumerate(vias) if r in power and (66,0) in r["geometry"])
    del bad[index]["geometry"][(66,0)]
    reject("remove_power_via4","Exact native power cut and enclosure geometry",lambda:power_arrays(bad,after["additive_power_vias"],after["origin_translation_um"],dbu,tech))
    bad=dict(regions);bad[(134,0)]=pya.Region()
    reject("remove_power_straps","Entire compact power strap exists in actual GDS",lambda:drawing_contract(bad,after,dbu))
    selected,_=primitive_matches(new_instances,after["instances"],after["origin_translation_um"],dbu)
    for fault,geometry in (("remove_actual_changed_mim_plate", dict(selected["DIV__XCP"]["geometry"], **{})), ("restore_undersized_actual_mim", mim_template(20,20,tech,dbu))):
        if fault == "remove_actual_changed_mim_plate":
            geometry[(36,0)] = pya.Region()
        bad=[dict(r,geometry=geometry) if r is selected["DIV__XCP"] else r for r in new_instances]
        reject(fault,"Exact retained Cap24 MIM equals independent native rectangle formula",lambda:compare_intrinsics(old_instances,bad,before,after,dbu,tech))
    for fault,geometry in (("remove_actual_changed_resistor_body", dict(selected["DIV__XDP"]["geometry"])), ("restore_shorter_actual_pulldown", rppd_template(1,7,tech,dbu))):
        if fault == "remove_actual_changed_resistor_body":
            geometry[(128,0)] = pya.Region()
        bad=[dict(r,geometry=geometry) if r is selected["DIV__XDP"] else r for r in new_instances]
        reject(fault,"Exact changed pull-down equals independent native resistor rectangle formula",lambda:compare_intrinsics(old_instances,bad,before,after,dbu,tech))
    require(inputs=={p:pin(p) for p in inputs},"Saved actual input bytes unchanged")
    args.out.write_text(json.dumps(dict(status="PASS_ACTUAL_BIAS8_TWO_RPPD_DELTA_CAP24_POWER_AND_EIGHT_GEOMETRY_CONTROLS",inputs=inputs,changed_pulldown_length_um={n:[7,8] for n in sorted(PULLDOWNS)},retained_cap24_mim_names=sorted(CAPS),unchanged_intrinsics=89,physical_primitives=91,native_instances=725,native_vias=634,power_arrays=47,power_straps=8,local_buses=47,controls=controls,retained_layout_owners=True,full_route_identity_claim=False,qualified_pex=False,scope=__doc__),indent=2)+"\n")


if __name__=="__main__":main()
