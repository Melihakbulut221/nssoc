#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Small native tiled-versus-unsplit connectivity controls, with fresh replay."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import resource
import subprocess
import sys

resource.setrlimit(resource.RLIMIT_AS, (384*1024**2,)*2)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"scripts"))
import klayout.db as db  # noqa: E402
import cloud_supply_tiles as tiled  # noqa: E402
from audit_supply_checkpoint import audit  # noqa: E402
from extract_supply_checkpoint import derive  # noqa: E402
from check_chip_supply_connectivity import sha  # noqa: E402


def fixture(directory, case):
    layout = db.Layout()
    layout.dbu = .001
    top = layout.create_cell("TOP")
    m1 = layout.layer(8, 0)
    # Native cut marker fixes a rectangular source bbox but is not a conductor.
    top.shapes(layout.layer(27, 0)).insert(db.Box(0, 0, 1, 1))
    top.shapes(layout.layer(27, 0)).insert(db.Box(199, 199, 200, 200))
    windows = []
    for j, pin in enumerate(["vdd", "vss", "iovdd", "iovss"]):
        y = 10+j*40
        region = db.Region(db.Box(0, y, 200, y+20))
        if case == "open" and j == 0:
            region -= db.Region(db.Box(99, y, 101, y+20))
        if case == "missing" and j == 0:
            region -= db.Region(db.Box(180, y, 200, y+20))
        if case in ("multiple_crossing", "corner", "corner_open") and j == 0:
            # Two pieces in a single LEF window join outside that window and
            # pass through different seams. Window-centre inference is wrong.
            region -= db.Region(db.Box(2, y+5, 18, y+15))
        if case in ("corner", "corner_open") and j == 2:
            region = db.Region(db.Box(0, 90, 80, 110)) + db.Region(db.Box(80, 80, 100, 100))
            region += db.Region(db.Box(100 if case == "corner" else 101, 100, 200, 110))
        top.shapes(m1).insert(region)
        for index, x in enumerate((4, 186)):
            windows.append(dict(instance="pad"+str(index), master="CONTROL_PAD",
                                pin=pin, layer="Metal1", gds_layer=8,
                                box_nm=[x, y, x+10, y+20]))
    if case == "short":
        top.shapes(m1).insert(db.Box(90, 20, 110, 60))
    if case in ("corner", "corner_open"):
        # A route turns on the intersection of four tiles. In the open case
        # a one-DBU gap must not be bridged by overlap matching.
        windows += [dict(instance="pad0", master="CONTROL_PAD", pin="iovdd",
                         layer="Metal1", gds_layer=8, box_nm=[65, 90, 75, 95])]
    if case == "via":
        # Route vdd across a tile seam on Metal2; disconnect its Metal1 bridge.
        top.shapes(layout.layer(8, 24)).insert(db.Box(70, 10, 130, 30))
        top.shapes(layout.layer(10, 0)).insert(db.Box(60, 10, 140, 30))
        for x in (60, 130):
            top.shapes(layout.layer(19, 0)).insert(db.Box(x, 12, x+10, 28))
    if case in ("via_stack", "mim_cut", "via_open"):
        # The only left/right connection ascends all six via levels, crosses
        # the tile line on TopMetal2, and descends all six levels again.
        top.shapes(layout.layer(8, 24)).insert(db.Box(70, 10, 130, 30))
        for number in tiled.METALS[1:]:
            for x in (60, 130):
                top.shapes(layout.layer(number, 0)).insert(db.Box(x, 12, x+10, 28))
        top.shapes(layout.layer(134, 0)).insert(db.Box(60, 12, 140, 28))
        for number in tiled.VIAS:
            for x in (60, 130):
                if not (case == "via_open" and number == 49 and x == 60):
                    top.shapes(layout.layer(number, 0)).insert(db.Box(x, 12, x+10, 28))
        if case == "mim_cut":
            top.shapes(layout.layer(36, 0)).insert(db.Box(60, 12, 70, 28))
    if case == "resistor_cut":
        top.shapes(layout.layer(8, 29)).insert(db.Box(99, 10, 101, 30))
    if case == "floating_alias":
        child = layout.create_cell("FLOATING_COLUMN")
        child.shapes(m1).insert(db.Box(0, 0, 5, 5))
        for x in (20, 170):
            top.insert(db.CellInstArray(child.cell_index(), db.Trans(x, 180)))
            windows.append(dict(instance="pad0", master="CONTROL_PAD", pin="iovss",
                                layer="Metal1", gds_layer=8, box_nm=[x, 180, x+5, 185]))
    gds = directory/"source.gds"
    layout.write(str(gds))
    plan = dict(status="PASS_IO_PORT_WINDOW_COVERAGE_ONLY", input_sha256={str(gds): sha(gds)},
                io_instances=2, io_masters={"CONTROL_PAD": 2}, port_windows=len(windows),
                windows_by_rail=dict(Counter(w["pin"] for w in windows)),
                windows_by_layer=dict(Counter(w["layer"] for w in windows)), windows=windows)
    path = directory/"plan.json"
    path.write_text(json.dumps(plan, indent=2)+"\n")
    return gds, path, plan


def partitions(windows, tiled_result=False):
    classes = {}
    result = []
    for row in windows:
        identities = row["physical_components"] if tiled_result else row["measurement"]["identities"]
        ids = []
        for identity in identities:
            key = tuple(identity)
            if key not in classes:
                classes[key] = len(classes)
            ids.append(classes[key])
        result.append(sorted(ids))
    return result


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    cases = {}
    layout = db.Layout()
    layout.dbu = .001
    top = layout.create_cell("TOP")
    top.shapes(layout.layer(8, 0)).insert(db.Polygon([db.Point(0, 0), db.Point(11, 7), db.Point(0, 20)]))
    try:
        tiled.clipped_layers(db, layout, top, [0, 0, 5, 20])
    except ValueError as error:
        assert "exact rational clipping" in str(error)
        cases["unsupported_rational_clip"] = dict(status="REJECTED_UNSAFE_ROUNDING", error=str(error))
    else:
        raise AssertionError("Arbitrary slope silently clipped with integer rounding")
    for case in ("connected", "open", "short", "missing", "multiple_crossing", "corner",
                 "corner_open", "via", "via_stack", "via_open", "mim_cut", "resistor_cut", "floating_alias"):
        directory = output/case
        directory.mkdir()
        gds, plan_path, plan = fixture(directory, case)
        bundle = directory/"bundle"
        manifest = tiled.make_bundle(db, gds, plan_path, bundle, columns=2, rows=2, production=False)
        pin = sha(bundle/"bundle.json")
        # Independent unsplit native derivation. Flatten GDS hierarchy first to
        # make every distinct child instance a real top-level physical component.
        original = db.Layout()
        original.read(str(gds))
        original.cell("TOP").flatten(True)
        flat = directory/"flat.gds"
        original.write(str(flat))
        native = derive(db, flat, "TOP")
        native.extract_netlist()
        expected = audit(db, native, dict(input_sha256={str(gds): sha(gds)}, dbu=.001,
                         floating_subcircuits_retained=True, top="TOP"), plan)
        del native
        measurements = []
        for tile in manifest["grid"]["tiles"]:
            tile_dir = directory/f"tile-{tile['id']}"
            tile_dir.mkdir()
            checkpoint = tile_dir/"checkpoint"
            with (directory/f"tile-{tile['id']}.log").open("x") as log:
                subprocess.run([sys.executable, __file__, str(checkpoint), "--produce",
                                str(bundle), "--bundle-sha256", pin, "--tile", str(tile["id"])],
                               stdout=log, stderr=subprocess.STDOUT, check=True)
                subprocess.run([sys.executable, str(ROOT/"scripts/supply_checkpoint_staged.py"),
                                "--checkpoint", str(checkpoint), "--prepared-sha256", sha(checkpoint/"prepared.json")],
                               stdout=log, stderr=subprocess.STDOUT, check=True)
            measurements.append(tiled.measure_tile(db, bundle, pin, tile["id"], checkpoint,
                                                    sha(checkpoint/"manifest.json"), tile_dir/"measurement.json"))
            tiled.validate_result_chain(tile_dir, measurements[-1], manifest, pin)
        actual = tiled.combine(manifest, pin, plan, measurements)
        assert bool(actual["errors"]) == bool(expected["errors"]), (case, expected, actual)
        assert partitions(actual["windows"], True) == partitions(expected["windows"]), (case, expected, actual)
        if case in ("connected", "multiple_crossing", "corner", "via", "via_stack"):
            assert not actual["errors"], (case, actual)
        if case in ("open", "short", "missing", "resistor_cut", "floating_alias",
                    "corner_open", "via_open", "mim_cut"):
            assert actual["errors"], (case, actual)
        negatives = []
        if case == "connected":
            for mutation in ("checkpoint_hash", "database_hash", "replayed_partition"):
                broken = copy.deepcopy(measurements[0])
                if mutation == "checkpoint_hash":
                    broken["checkpoint_manifest_sha256"] = "0"*64
                elif mutation == "database_hash":
                    broken["checkpoint_database_sha256"] = "0"*64
                else:
                    row = next(m for m in broken["measurements"] if m["samples"])
                    row["samples"][0]["cluster"] = 987654
                try:
                    tiled.validate_result_chain(directory/"tile-0", broken, manifest, pin)
                except ValueError:
                    negatives.append(mutation)
                else:
                    raise AssertionError("Broken native checkpoint chain accepted")
            for mutation in ("missing_tile", "duplicate_tile", "missing_seam", "wrong_hash",
                             "seam_geometry", "seam_point", "child_identity", "missing_window"):
                broken = copy.deepcopy(measurements)
                if mutation == "missing_tile":
                    broken.pop()
                elif mutation == "duplicate_tile":
                    broken[1] = copy.deepcopy(broken[0])
                elif mutation == "wrong_hash":
                    broken[0]["bundle_sha256"] = "0"*64
                elif mutation == "missing_window":
                    broken[0]["measurements"] = [m for m in broken[0]["measurements"] if m["query"]["kind"] != "window"]
                else:
                    row = next(m for m in broken[0]["measurements"] if m["query"]["kind"] == "seam" and m["samples"])
                    if mutation == "missing_seam":
                        broken[0]["measurements"].remove(row)
                    elif mutation == "seam_geometry":
                        row["geometry_sha256"] = "0"*64
                    elif mutation == "seam_point":
                        row["samples"][0]["point_um"][0] += .001
                    elif mutation == "child_identity":
                        row["samples"][0]["circuit"] = "CHILD"
                try:
                    tiled.combine(manifest, pin, plan, broken)
                except ValueError:
                    negatives.append(mutation)
                else:
                    raise AssertionError("Corrupted coverage accepted: "+mutation)
        cases[case] = dict(status=actual["status"], errors=actual["errors"],
                           matched_unsplit_native_partitions=True,
                           rejected_mutations=negatives, seam_witnesses=actual["seam_witnesses"])
        tiled.write_new(directory/"audit.json", actual)
        print("CONTROL", case, actual["status"], flush=True)
    result = dict(status="PASS_NATIVE_TILED_CONNECTIVITY_CONTROLS_ONLY", cases=cases,
                  methods=tiled.method_pins(), native_version=db.__version__,
                  fixture_sha256=sha(Path(__file__)), peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  full_chip_lvs_accepted=False, manufacturing_approval=False)
    tiled.write_new(output/"result.json", result)
    print(result["status"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--produce", type=Path)
    parser.add_argument("--bundle-sha256")
    parser.add_argument("--tile", type=int)
    args = parser.parse_args()
    if args.produce:
        tiled.extract_tile(db, args.produce, args.bundle_sha256, args.tile, args.output)
    else:
        run(args.output)
