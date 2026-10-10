#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Strict saved-GDS compact placement, intrinsic geometry and power-via audit.

No full-route identity claim: every changed route requires fresh DRC/LVS/RC.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import pya
import audit_pcie_clock_div4_v7_power_v3 as parent

OLD_TOP = "nssoc_clock_div4_v7_power_v2_layout"
NEW_TOP = "nssoc_clock_div4_v7_compact_v2_layout"
BASE_GDS_SHA = "663b60fc14cc9c8e2b4d9a5a758aee6bcd61bdf307c6b3a69a28e63bc470340c"
BASE_RESULT_SHA = "bf34cad3dbdee3f443c275f50fb7008d612f1f970b6c3c63abd51df2582513be"
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


def compare_intrinsics(old_instances, new_instances, before, after, dbu):
    ignored = {"placement_um", "bbox_um"}
    a = {r["name"]: {k: v for k, v in r.items() if k not in ignored} for r in before["instances"]}
    b = {r["name"]: {k: v for k, v in r.items() if k not in ignored} for r in after["instances"]}
    require(a == b and len(a) == 91, "Exact unchanged 91-device topology and bias metadata")
    old, oldvias = primitive_matches(old_instances, before["instances"], before["origin_translation_um"], dbu)
    new, newvias = primitive_matches(new_instances, after["instances"], after["origin_translation_um"], dbu)
    for name in old:
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
    require(pin(oldg)["sha256"]==BASE_GDS_SHA and pin(oldr)["sha256"]==BASE_RESULT_SHA,"Exact frozen PowerV2 baseline")
    require(pin(parent.__file__)["sha256"]==PARENT_SHA,"Exact retained-layout geometry reader and independent via formulas")
    require(not args.out.exists(),"Fresh compact audit output")
    techpath=args.pdk/"libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json"
    inputs={str(p):pin(p) for p in [oldg,newg,oldr,newr,Path(__file__),Path(parent.__file__),techpath]}
    before,after=json.loads(oldr.read_text()),json.loads(newr.read_text())
    require(before["source_circuit_sha256"]==after["source_circuit_sha256"] and before["primitive_counts"]==after["primitive_counts"],"Exact frozen source graph and primitive counts")
    old_layout,old_instances=parent.top_instances(oldg,OLD_TOP)
    new_layout,new_instances=parent.top_instances(newg,NEW_TOP)
    region_layout,box,regions,texts=parent.read_layout(newg,NEW_TOP)
    require(old_layout.dbu==new_layout.dbu==region_layout.dbu,"Exact actual DBU")
    dbu=new_layout.dbu
    require(len(old_instances)==len(new_instances)==725,"All actual 725 native leaves")
    require(box.to_dtype(dbu).to_s()==pya.DBox(*after["bbox_um"]).to_s(),"Actual compact bbox equals generated metadata")
    require(box.left==0 and box.bottom==0 and box.width()*dbu==960 and box.height()*dbu<600,"Compact physical dimensions")
    require(Counter(t[0] for t in texts[(67,25)])==Counter(["CLKP","CLKN","QP","QN","DIV_AVDD","AVSS","SUB"]),"Seven actual top port labels")
    vias=compare_intrinsics(old_instances,new_instances,before,after,dbu)
    tech=json.loads(techpath.read_text())["techParams"]
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
    reject("remove_actual_hbt","Each original intrinsic exists at its exact declared new placement",lambda:compare_intrinsics(old_instances,bad,before,after,dbu))
    bad=[dict(r,geometry=dict(r["geometry"])) for r in new_instances]
    bad[next(i for i,r in enumerate(new_instances) if r is primitive)]["geometry"][(8,0)]=pya.Region()
    reject("remove_hbt_metal1","Exact unchanged intrinsic native geometry",lambda:compare_intrinsics(old_instances,bad,before,after,dbu))
    bad=[dict(r,geometry=dict(r["geometry"])) for r in vias]
    index=next(i for i,r in enumerate(vias) if r in power and (66,0) in r["geometry"])
    del bad[index]["geometry"][(66,0)]
    reject("remove_power_via4","Exact native power cut and enclosure geometry",lambda:power_arrays(bad,after["additive_power_vias"],after["origin_translation_um"],dbu,tech))
    bad=dict(regions);bad[(134,0)]=pya.Region()
    reject("remove_power_straps","Entire compact power strap exists in actual GDS",lambda:drawing_contract(bad,after,dbu))
    require(inputs=={p:pin(p) for p in inputs},"Saved actual input bytes unchanged")
    args.out.write_text(json.dumps(dict(status="PASS_ACTUAL_COMPACT_INTRINSICS_POWER_AND_FOUR_GEOMETRY_CONTROLS",inputs=inputs,physical_primitives=91,native_instances=725,native_vias=634,power_arrays=47,power_straps=8,local_buses=47,controls=controls,retained_layout_owners=True,full_route_identity_claim=False,qualified_pex=False,scope=__doc__),indent=2)+"\n")


if __name__=="__main__":main()
