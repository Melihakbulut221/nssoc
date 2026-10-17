#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read actual GDS regions and prove the power overlay retains original geometry.

This read-only check does not run extraction or electrical comparison. Four
in-memory geometry corruptions exercise this gate; native DRC/LVS remains separate.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import pya

OLD_TOP = "nssoc_clock_div4_v7_layout"
NEW_TOP = "nssoc_clock_div4_v7_power_v2_layout"
OLD_GDS_SHA = "8484a6f3db8e91923ec6e5d2184bf6ba80570b2c894b5e4f563b637e0165ee3f"
OLD_RESULT_SHA = "4aebd43e3ab0cc849a5045536eb183301766fa251b1d1a08f46627a4a7ae20d1"
# Native layer numbers, independently checked against the frozen SG13G2 lyp.
ALLOWED = {(50, 0), (67, 0), (126, 0), (134, 0), (66, 0), (125, 0), (133, 0)}


def pin(path):
    path = Path(path)
    with path.open("rb") as f:
        return dict(
            bytes=path.stat().st_size,
            sha256=hashlib.file_digest(f, "sha256").hexdigest(),
        )


def require(value, reason):
    if not value:
        raise ValueError(reason)


def read_layout(path, topname):
    layout = pya.Layout()
    layout.read(str(path))
    cell = layout.cell(topname)
    require(cell is not None and len(layout.top_cells()) == 1, "One exact GDS top")
    regions, texts = {}, {}
    for index in layout.layer_indexes():
        info = layout.get_info(index)
        key = (info.layer, info.datatype)
        region = pya.Region(cell.begin_shapes_rec(index)).merged()
        if not region.is_empty():
            regions[key] = region
        rows = []
        iterator = cell.begin_shapes_rec(index)
        while not iterator.at_end():
            shape = iterator.shape()
            if shape.is_text():
                t = shape.text.transformed(iterator.trans())
                rows.append((t.string, t.x, t.y))
            iterator.next()
        if rows:
            texts[key] = sorted(rows)
    return layout.dbu, cell.bbox(), regions, texts


def compare_regions(old, new):
    differences = {}
    for layer in sorted(set(old) | set(new)):
        before = old.get(layer, pya.Region())
        after = new.get(layer, pya.Region())
        removed = before - after
        require(removed.is_empty(), "Original GDS drawing removed")
        added = after - before
        if layer not in ALLOWED:
            require(added.is_empty(), "Geometry added outside allowed power layers")
        differences[str(layer)] = dict(
            old_area_dbu2=before.area(),
            new_area_dbu2=after.area(),
            added_area_dbu2=added.area(),
        )
    for layer in ((126, 0), (134, 0), (125, 0), (133, 0)):
        require(
            not (
                new.get(layer, pya.Region()) - old.get(layer, pya.Region())
            ).is_empty(),
            "Required upper power geometry absent",
        )
    return differences


def via_template(parameters, tech, dbu):
    """Independent layer/cut rectangles for only the declared 2x3/2x2 stacks."""
    bottom = parameters["b_layer"]
    require(
        parameters
        == dict(
            b_layer=bottom,
            t_layer="TopMetal2",
            vn_columns=2,
            vn_rows=3,
            vt1_columns=2,
            vt1_rows=2,
            vt2_columns=2,
            vt2_rows=2,
        ),
        "Exact declared native power via parameters",
    )
    require(bottom in ("Metal4", "Metal5", "TopMetal1"), "Supported power via bottom")
    regions = {}

    def rectangle(layer, box):
        regions.setdefault((layer, 0), pya.Region()).insert(
            pya.DBox(*box).to_itype(dbu)
        )

    def array(layer, nx, ny, size, space):
        wx, wy = nx * size + (nx - 1) * space, ny * size + (ny - 1) * space
        for i in range(nx):
            for j in range(ny):
                x, y = i * (size + space) - wx / 2, j * (size + space) - wy / 2
                rectangle(layer, (x, y, x + size, y + size))
        return wx, wy

    if bottom == "Metal4":
        wx, wy = array(66, 2, 3, tech["Vn_a"], tech["Vn_b"])
        enc = tech["Vn_c1"]
        rectangle(50, (-wx / 2 - enc, -wy / 2 - enc, wx / 2 + enc, wy / 2 + enc))
    if bottom in ("Metal4", "Metal5"):
        wx, wy = array(125, 2, 2, tech["TV1_a"], tech["TV1_b"])
        enc = tech["TV1_c"]
        rectangle(67, (-wx / 2 - enc, -wy / 2 - enc, wx / 2 + enc, wy / 2 + enc))
        # The inner generic M5 rectangle and the Top1 lower-via enclosure
        # are wholly covered by these larger declared outer enclosures.
    wx, wy = array(133, 2, 2, tech["TV2_a"], tech["TV2_b"])
    for layer, enc in ((126, tech["TV2_c"]), (134, tech["TV2_d"])):
        rectangle(layer, (-wx / 2 - enc, -wy / 2 - enc, wx / 2 + enc, wy / 2 + enc))
    return {k: v.merged() for k, v in regions.items()}


def top_instances(path, topname):
    layout = pya.Layout()
    layout.read(str(path))
    top = layout.cell(topname)
    result = []
    for instance in top.each_inst():
        require(
            not instance.is_regular_array(), "Only original explicit native instances"
        )
        cell = layout.cell(instance.cell_index)
        require(not list(cell.each_inst()), "All original native cells are leaves")
        shapes = {}
        for index in layout.layer_indexes():
            info = layout.get_info(index)
            region = pya.Region(cell.begin_shapes_rec(index)).merged()
            if not region.is_empty():
                shapes[(info.layer, info.datatype)] = region
        result.append(
            dict(
                key=(cell.name, instance.cplx_trans.to_s()),
                cell=cell.name,
                transform=instance.cplx_trans,
                geometry=shapes,
            )
        )
    return layout.dbu, result


def compare_instances(oldrows, newrows, declared, translation, dbu, tech):
    old = Counter(row["key"] for row in oldrows)
    new = Counter(row["key"] for row in newrows)
    require(
        sum(old.values()) == 678 and sum(new.values()) == 725,
        "Exact original 678 and new 725 native instances",
    )
    require(not (old - new), "Every original native instance retained")
    oldmap = {row["key"]: row["geometry"] for row in oldrows}
    remaining = Counter(old)
    extras = []
    for row in newrows:
        if remaining[row["key"]]:
            before = oldmap[row["key"]]
            require(
                set(before) == set(row["geometry"])
                and all((before[k] ^ row["geometry"][k]).is_empty() for k in before),
                "Every original native cell geometry unchanged",
            )
            remaining[row["key"]] -= 1
        else:
            extras.append(row)
    require(len(extras) == len(declared) == 47, "Exact 47 added via instances")
    used = set()
    for target in declared:
        x, y = [target["center_um"][i] + translation[i] for i in (0, 1)]
        trans = pya.ICplxTrans(1.0, 0.0, False, round(x / dbu), round(y / dbu))
        found = [i for i, row in enumerate(extras) if row["transform"] == trans]
        require(
            len(found) == 1 and found[0] not in used,
            "Unique actual power via at every declared center",
        )
        index = found[0]
        used.add(index)
        row = extras[index]
        require(
            row["cell"].split("$")[0] == "via_stack", "Actual native via cell class"
        )
        expected = via_template(target["parameters"], tech, dbu)
        require(
            set(row["geometry"]) == set(expected)
            and all((row["geometry"][k] ^ expected[k]).is_empty() for k in expected),
            "Actual native power via cut/enclosure geometry differs",
        )
    require(len(used) == 47, "Every new native via instance bound")
    return extras


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pdk", type=Path, required=True)
    args = parser.parse_args()
    oldg = args.baseline / (OLD_TOP + ".gds")
    oldr = args.baseline / "result.json"
    newg = args.layout / (NEW_TOP + ".gds")
    newr = args.layout / "result.json"
    require(
        pin(oldg)["sha256"] == OLD_GDS_SHA and pin(oldr)["sha256"] == OLD_RESULT_SHA,
        "Exact original native GDS and metadata",
    )
    require(not args.out.exists(), "Fresh geometry audit receipt")
    inputs = {str(p): pin(p) for p in (oldg, oldr, newg, newr, Path(__file__))}
    techpath = args.pdk / "libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json"
    inputs[str(techpath)] = pin(techpath)
    tech = json.loads(techpath.read_text())["techParams"]
    before = json.loads(oldr.read_text())
    after = json.loads(newr.read_text())
    for name in (
        "instances",
        "row_starts_um",
        "local_buses",
        "peripheral_trunks",
        "routes",
        "vias",
        "origin_translation_um",
        "ports",
        "bbox_um",
        "primitive_counts",
        "source_circuit_sha256",
    ):
        require(
            before[name] == after[name],
            "Original primitive/placement/routing/port metadata exact: " + name,
        )
    require(len(after["instances"]) == 91, "All 91 original physical primitives")
    require(
        Counter((x["net"], x["role"]) for x in after["additive_power_straps"])
        == Counter(
            {
                ("DIV_AVDD", "row_bus"): 3,
                ("AVSS", "row_bus"): 3,
                ("DIV_AVDD", "cross_row_trunk"): 1,
                ("AVSS", "cross_row_trunk"): 1,
            }
        ),
        "Exact eight power straps",
    )
    expected = Counter(
        {
            ("DIV_AVDD", "actual_branch"): 15,
            ("AVSS", "actual_branch"): 24,
            ("DIV_AVDD", "trunk_join"): 3,
            ("AVSS", "trunk_join"): 3,
            ("DIV_AVDD", "public_port"): 1,
            ("AVSS", "public_port"): 1,
        }
    )
    require(
        Counter((x["net"], x["role"]) for x in after["additive_power_vias"])
        == expected,
        "All 39 real power terminals and eight joins",
    )
    olddbu, oldbox, old, oldtexts = read_layout(oldg, OLD_TOP)
    newdbu, newbox, new, newtexts = read_layout(newg, NEW_TOP)
    require(
        olddbu == newdbu and oldbox == newbox and oldtexts == newtexts,
        "Actual bbox, grid and every text/pin label unchanged",
    )
    positive = compare_regions(old, new)
    for row in after["additive_power_straps"]:
        layer = (126 if row["layer"] == "TopMetal1" else 134, 0)
        box = pya.DBox(*row["rect_um"]).to_itype(newdbu)
        box.move(
            round(after["origin_translation_um"][0] / newdbu),
            round(after["origin_translation_um"][1] / newdbu),
        )
        require(
            (pya.Region(box) - new[layer]).is_empty(),
            "Declared entire power strap exists in actual GDS",
        )
    idbu, old_instances = top_instances(oldg, OLD_TOP)
    jdbu, new_instances = top_instances(newg, NEW_TOP)
    require(idbu == jdbu == newdbu, "Actual instance and drawing grids equal")
    extras = compare_instances(
        old_instances,
        new_instances,
        after["additive_power_vias"],
        after["origin_translation_um"],
        newdbu,
        tech,
    )
    controls = []
    for fault, diagnostic in (
        ("remove_old_metal1", "Original GDS drawing removed"),
        ("add_forbidden_metal1", "Geometry added outside allowed power layers"),
        ("remove_power_overlay", "Required upper power geometry absent"),
    ):
        mutated = dict(new)
        if fault == "remove_old_metal1":
            polygon = next(old[(8, 0)].each())
            mutated[(8, 0)] = new[(8, 0)] - pya.Region(polygon)
        elif fault == "add_forbidden_metal1":
            b = pya.Box(
                oldbox.right + 10000,
                oldbox.top + 10000,
                oldbox.right + 12000,
                oldbox.top + 12000,
            )
            mutated[(8, 0)] = new[(8, 0)] + pya.Region(b)
        else:
            mutated[(134, 0)] = old.get((134, 0), pya.Region())
        try:
            compare_regions(old, mutated)
        except ValueError as error:
            require(
                str(error) == diagnostic,
                "Geometry control rejected for exact intended cause",
            )
            controls.append(
                dict(fault=fault, status="EXPECTED_REJECTION", diagnostic=str(error))
            )
        else:
            raise ValueError("Actual geometry corruption was accepted")
    # Drop only one added branch's actual Via4 geometry, keeping all original
    # instances and every upper strap. Broad region/subset or LVS can miss this;
    # the exact added instance binding must reject it for the declared cause.
    victim = next(row for row in extras if (66, 0) in row["geometry"])
    bad_instances = [dict(row, geometry=dict(row["geometry"])) for row in new_instances]
    matching = [row for row in bad_instances if row["key"] == victim["key"]]
    require(len(matching) == 1, "Unique actual Via4 corruption target")
    del matching[0]["geometry"][(66, 0)]
    try:
        compare_instances(
            old_instances,
            bad_instances,
            after["additive_power_vias"],
            after["origin_translation_um"],
            newdbu,
            tech,
        )
    except ValueError as error:
        require(
            str(error) == "Actual native power via cut/enclosure geometry differs",
            "Via4 corruption rejected for exact intended cause",
        )
        controls.append(
            dict(
                fault="remove_one_added_via4_array",
                status="EXPECTED_REJECTION",
                diagnostic=str(error),
                instance=list(victim["key"]),
            )
        )
    else:
        raise ValueError("Actual added Via4 removal was accepted")
    require(inputs == {p: pin(p) for p in inputs}, "Saved native input bytes unchanged")
    result = dict(
        status="PASS_ACTUAL_GDS_POWER_ONLY_ADDITION_AND_FOUR_GEOMETRY_CONTROLS",
        inputs=inputs,
        layer_area_comparison=positive,
        original_primitives=91,
        actual_power_terminals=39,
        native_via_arrays=47,
        original_native_instances=678,
        added_native_instances=47,
        exact_native_cut_and_enclosure_geometry=True,
        power_straps=8,
        controls=controls,
        no_extraction_rerun=True,
        qualified_pex=False,
        scope="Read actual old/new GDS regions and metadata. Four actual in-memory geometry mutations; no new DRC/LVS/RC or divided-clock acceptance inferred.",
    )
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], flush=True)


if __name__ == "__main__":
    main()
