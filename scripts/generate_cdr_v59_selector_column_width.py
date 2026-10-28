#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Disabled additive selector-column proposal; never a DRC/LVS/RC verdict."""
import argparse
import collections
import copy
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path
import generate_cdr_v59_tail_access_wire as frozen

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "scripts/cdr-v59-selector-column-width-contract.json"
METHOD = ROOT / "scripts/cdr-v59-selector-column-width-methods.json"
KEYS = ((50, 0), (126, 0))
TOP = "nssoc_cdr_pd500_resistor_v59"
CHILD = "pd_child_sampler_cd"
GDS = "parent/layout/" + TOP + ".gds"
LVS = "parent/physical/lvs_flat/result.lvsdb"
CHILD_META = "parent/inputs/sampler_cd/layout/result.json"

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)

def exact(value, expected, reason):
    assert canonical(value) == canonical(expected), reason

def grid_um(value):
    assert type(value) in (int, float) and not isinstance(value, bool)
    scaled = value * 1000
    rounded = round(scaled)
    assert abs(scaled - rounded) < 1e-6 and rounded % 5 == 0, "Off-grid route coordinate"
    return rounded

def boxes(contract, routes):
    """Use original reported coordinates; width is the sole geometric parameter."""
    assert contract["width_dbu"] == 3200 and type(contract["width_dbu"]) is int
    exact(contract["origin_dbu"], [0, -3970], "Changed normalization")
    exact(contract["old_bus_dbu"], {"M_SE":150000, "M_TE":240000}, "Changed old buses")
    exact(contract["width_end_dbu"], {"M_SE":150000, "M_TE":180000}, "Changed width endpoints")
    exact(contract["clearance_dbu"], {"50":600, "126":1640}, "Changed clearance")
    selected = [r for r in routes if r["net"] in ("M_SE", "M_TE")]
    exact(selected, contract["selected_original_routes"], "Changed selected source routes")
    assert len(selected) == 13 and len({(r["device"],r["net"]) for r in selected}) == 13
    assert collections.Counter(r["net"] for r in selected) == {"M_SE":5, "M_TE":8}
    result = []
    for r in selected:
        x, y = grid_um(r["escape_lane_um"]), grid_um(r["escape_y_um"])
        end, old_end = contract["width_end_dbu"][r["net"]], contract["old_bus_dbu"][r["net"]]
        assert y < end <= old_end
        for metal, half, pad in ((50,600,200),(126,820,820)):
            old = [x-half, y-pad-3970, x+half, old_end+pad-3970]
            new = [x-1600, y-pad-3970, x+1600, end+pad-3970]
            assert all(type(v) is int and v % 5 == 0 for v in old+new)
            result.append(dict(device=r["device"], net=r["net"], layer=metal, old=old, new=new,
                               probe=[x,y+1000-3970]))
    assert len(result) == 26
    exact(result,contract["declared_rectangles"],"Declared coordinate plan differs")
    return result

def source_column_screen(contract):
    """Independent 1-D envelope screen, not full material or via clearance."""
    rows = contract["source_routes"]
    assert len(rows) == contract["source_route_count"] == 119
    proposal = boxes(contract, rows)
    checks = []
    for added in proposal:
        x = (added["new"][0] + added["new"][2]) // 2
        for row in rows:
            if row["net"] == added["net"]:
                continue
            foreign_x = grid_um(row["escape_lane_um"])
            gain = row["device"] in ("GP","GN","GT0","GT1","UP","UN","DP","DN")
            half = 2000 if gain else (600 if added["layer"] == 50 else 820)
            gap = abs(x-foreign_x)-1600-half
            assert gap > contract["clearance_dbu"][str(added["layer"])], "Source column clearance"
            checks.append(dict(device=added["device"], net=added["net"], layer=added["layer"],
                               foreign_device=row["device"], foreign_net=row["net"], gap_dbu=gap))
    return dict(checks=len(checks), minimum_gap_dbu=min(r["gap_dbu"] for r in checks),
                limiting=sorted(checks,key=lambda r:r["gap_dbu"])[:12],
                full_geometry_clearance=False, via_clearance=False)

def validate_graph(contract, graph):
    """Bind each complete terminal partition, not only its anonymous net name."""
    assert graph["native_device_count"] == 500 and graph["native_terminal_count"] == 1446
    assert graph["wire_component_count"] == 113 and len(graph["native_ports"]) == 25
    for tag in ("sd","sc"):
        for net in ("M_SE","M_TE"):
            owner = contract["owner_partitions"][tag][net]
            got = [r for r in graph["native_net_coverage"] if r["native_cluster"] == owner["native_cluster"]]
            exact(got, [owner], "Changed complete native owner partition")
    assert len({v["native_cluster"] for ns in contract["owner_partitions"].values() for v in ns.values()}) == 4

def owned_component(pya, full, native, probe_net, probe, cluster, addition, clearance, adjacent):
    """Actual full-parent Region clearance; a foreign or unknown owner refuses."""
    point = pya.Point(*probe)
    owner = probe_net(native, point)
    assert owner is not None and owner.cluster_id == cluster, "Wrong actual native owner"
    seed = pya.Region(pya.Box(point.x-1,point.y-1,point.x+1,point.y+1))
    owned = full.interacting(seed)
    assert owned.count() == 1 and not (owned & addition).is_empty(), "Missing unique old component"
    foreign = (full-owned).merged()
    assert addition.sized(clearance).interacting(foreign).is_empty(), "Foreign metal clearance"
    delta = (addition-full).merged()
    assert not delta.is_empty(), "No added width"
    # Existing vias/landings remain untouched; no previously untouched via may be contacted.
    assert delta.interacting(adjacent).is_empty(), "New adjacent-via contact"
    return owned, dict(native_cluster=cluster, old_component_area_dbu2=owned.area(),
                       added_area_dbu2=delta.area(), clearance_dbu=clearance)

def native_plan(pya, layout, db, contract, proposal):
    top, child = layout.cell(TOP), layout.cell(CHILD)
    assert layout.dbu == .001 and top is not None and child is not None
    circuit = db.netlist().top_circuit()
    assert circuit.name == TOP and circuit.pin_count() == 25 and len(list(circuit.each_device())) == 500
    parents = [(c.name,i) for c in layout.each_cell() for i in c.each_inst()
               if i.cell_index == child.cell_index()]
    assert len(parents) == 2 and all(n == TOP and i.size() == 1 for n,i in parents)
    placements = {}
    exact(contract["placements"], {"sd":[993600,272000],"sc":[993600,1461520]}, "Changed placement contract")
    for tag,(dx,dy) in contract["placements"].items():
        found = [i for _,i in parents if frozen.placement_matches(i,dx,dy)]
        assert len(found) == 1, "Changed actual shared-child placement"
        placements[tag] = found[0]
    full = frozen.material(pya,layout,top,True)
    native = {}
    for key in KEYS:
        matches = [i for i in db.layer_indexes() if (db.layer_by_index(i).merged() ^ full[key]).is_empty()]
        assert len(matches) == 1, "Native layer not exactly equal to actual full parent"
        native[key] = db.layer_by_index(matches[0])
    additions = {key:pya.Region() for key in KEYS}
    for row in proposal:
        key = (row["layer"],0)
        old_box = pya.Box(*row["old"])
        original = [s for s in child.shapes(layout.layer(*key)).each()
                    if s.is_box() and s.box == old_box and s.properties() == {}]
        assert len(original) == 1, ("Original exact rectangle absent or ambiguous",row)
        additions[key].insert(pya.Box(*row["new"]))
    proofs, placed = [], []
    for tag,inst in placements.items():
        for row in proposal:
            key = (row["layer"],0)
            dx,dy = contract["placements"][tag]
            region = pya.Region(pya.Box(*row["new"])).transformed(inst.cplx_trans)
            cluster = contract["owner_partitions"][tag][row["net"]]["native_cluster"]
            adjacent_layers = (49,66) if row["layer"] == 50 else (125,133)
            adjacent = pya.Region()
            for layer in adjacent_layers:
                adjacent += full.get((layer,0),pya.Region())
            _, proof = owned_component(pya, full[key], native[key], db.probe_net,
                [row["probe"][0]+dx,row["probe"][1]+dy],cluster,region,
                contract["clearance_dbu"][str(row["layer"])],adjacent)
            proofs.append(dict(placement=tag,device=row["device"],net=row["net"],layer=row["layer"],**proof))
            placed.append((key,cluster,region))
    for i,(key,cluster,region) in enumerate(placed):
        for other_key,other_cluster,other_region in placed[i+1:]:
            if key == other_key and cluster != other_cluster:
                assert region.sized(contract["clearance_dbu"][str(key[0])]).interacting(other_region).is_empty(), "New foreign-net additions collide"
    assert len(proofs) == 52
    return additions, proofs

def verify_snapshot(pya, layout, before, expected_material, expected_raw, bbox):
    assert {c.name for c in layout.each_cell()} == set(before), "Cell census changed"
    assert layout.cell(TOP).bbox() == bbox, "Parent bbox changed"
    for name,(material,raw,instances) in before.items():
        cell = layout.cell(name)
        frozen.same_material(pya,expected_material if name == CHILD else material,
                             frozen.material(pya,layout,cell))
        assert frozen.raw_records(layout,cell) == (expected_raw if name == CHILD else raw), "Raw shape/text/property changed"
        assert frozen.hierarchy(cell) == instances, "Hierarchy changed"

def atomic(path, value):
    raw = (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()
    tmp = path.with_name(path.name+"."+secrets.token_hex(8)+".incomplete")
    with tmp.open("xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp,path)

def admitted(source):
    assert os.environ.get("GITHUB_ACTIONS") == "true", "Hosted-only generation"
    method = json.loads(METHOD.read_text())
    assert method["geometry_generation_authorized"] is method["native_execution_authorized"] is True, "Disabled geometry candidate"
    assert method["simulation_authorized"] is method["electrical_accepted"] is False
    for path,digest in method["protected_sha256"].items():
        p = ROOT/path
        assert p.is_file() and not p.is_symlink() and frozen.sha(p) == digest, ("Changed protected source",path)
    contract = json.loads(CONTRACT.read_text())
    assert source.is_absolute() and source.resolve() == source
    assert not any(p.is_symlink() for p in (source,*source.parents))
    assert source.is_relative_to(ROOT/"hw/soc/out"), "Input outside hosted output"
    exact(frozen.files(source),contract["baseline_inventory"],"Incomplete current 605-file baseline")
    assert len(contract["baseline_inventory"]) == 605
    assert frozen.sha(ROOT/contract["qualified_graph_path"]) == contract["qualified_graph_sha256"]
    graph = json.loads((ROOT/contract["qualified_graph_path"]).read_text())["geometry"]
    validate_graph(contract,graph)
    meta = json.loads((source/CHILD_META).read_text())
    exact(meta["origin_translation_um"],[0,-3.97],"Changed child origin")
    proposal = boxes(contract,meta["routes"])
    screen = source_column_screen(contract)
    return contract,proposal,screen

def generate_admitted(pya, source, out, admission):
    contract,proposal,screen = admission
    layout = pya.Layout()
    layout.read(str(source/GDS))
    db = pya.LayoutVsSchematic()
    db.read(str(source/LVS))
    additions,ownership = native_plan(pya,layout,db,contract,proposal)
    before = {c.name:(frozen.material(pya,layout,c),frozen.raw_records(layout,c),frozen.hierarchy(c))
              for c in layout.each_cell()}
    bbox = layout.cell(TOP).bbox()
    child = layout.cell(CHILD)
    expected = dict(before[CHILD][0])
    for key,region in additions.items():
        expected[key] = (expected.get(key,pya.Region())+region).merged()
    # Insert the exact 26 declared boxes, not merged replacement material.
    for row in proposal:
        child.shapes(layout.layer(row["layer"],0)).insert(pya.Box(*row["new"]))
    expected_raw = frozen.raw_records(layout,child)
    prior,after = collections.Counter(before[CHILD][1]),collections.Counter(expected_raw)
    extras = list((after-prior).elements())
    assert not (prior-after) and len(extras) == 26
    assert all((r[0],r[1]) in KEYS and r[3] == "{}" and r[4] is False for r in extras)
    verify_snapshot(pya,layout,before,expected,expected_raw,bbox)
    destination = out/(TOP+".gds")
    layout.write(str(destination))
    reread = pya.Layout()
    reread.read(str(destination))
    assert reread.dbu == .001
    verify_snapshot(pya,reread,before,expected,expected_raw,bbox)
    return dict(status="GENERATED_UNQUALIFIED_ADDITIVE_COLUMN_WIDTH",
        input_gds_sha256=contract["baseline_inventory"][GDS],candidate_gds_sha256=frozen.sha(destination),
        proposal=proposal,source_column_screen=screen,actual_original_native_ownership_and_clearance=ownership,
        added_raw_records=extras,all_original_material_raw_text_properties_hierarchy_preserved=True,
        original_500_devices_1446_terminals_978_anchors_reference_only=True,
        native_DRC_executed=False,native_LVS_executed=False,fresh_RC_executed=False,
        simulation_executed=False,physical_accepted=False,electrical_accepted=False,full_phy_accepted=False)

def run(source,out):
    assert out.is_absolute() and out.resolve() == out and not out.exists()
    assert out.is_relative_to(ROOT/"hw/soc/out") and not out.is_relative_to(source) and not source.is_relative_to(out)
    assert not any(p.is_symlink() for p in out.parents)
    out.mkdir(parents=True)
    result = dict(status="FAIL_OR_INCOMPLETE",physical_accepted=False,electrical_accepted=False,
                  full_phy_accepted=False,simulation_executed=False)
    primary = None
    admission = None
    try:
        admission = admitted(source)
        import pya
        result.update(generate_admitted(pya,source,out,admission))
    except BaseException as error:
        primary = error
        result["error"] = repr(error)
    # Every terminal operation is attempted independently; no failure may mask the primary.
    for name,action in (
        ("original_baseline_recheck",lambda: exact(frozen.files(source),admission[0]["baseline_inventory"],"Baseline changed") if admission else None),
        ("protected_source_recheck",lambda: [exact(frozen.sha(ROOT/p),h,("Changed source",p)) for p,h in json.loads(METHOD.read_text())["protected_sha256"].items()]),
        ("complete_output_inventory",lambda: result.update(outputs=frozen.files(out)))):
        try:
            action()
        except BaseException as error:
            result["status"] = "FAIL_OR_INCOMPLETE"
            result.setdefault("terminal_errors",[]).append(dict(action=name,error=repr(error)))
            if primary is None:
                primary = error
    try:
        atomic(out/"result.json",result)
    except BaseException as error:
        result["status"] = "FAIL_OR_INCOMPLETE"
        result.setdefault("terminal_errors",[]).append(dict(action="atomic_save",error=repr(error)))
        if primary is None:
            primary = error
        try:
            result["outputs"] = frozen.files(out)
        except BaseException as refresh:
            result.setdefault("terminal_errors",[]).append(dict(action="inventory_refresh",error=repr(refresh)))
        try:
            print(json.dumps(result,sort_keys=True,allow_nan=False),file=sys.stderr,flush=True)
        except BaseException:
            pass
    if primary is not None:
        raise primary
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source,args.out),sort_keys=True,allow_nan=False))

if __name__ == "__main__":
    main()
