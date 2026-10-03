#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded physical supply extraction with overlapping native geometry tiles.

Each tile extracts all seven metals and six vias. Adjacent tiles are joined
only through identical conductor geometry and identical interior witnesses in
their overlap, never through supply names or unrelated native cluster numbers.
All geometry, including the core, is included. This is not transistor LVS.
"""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import tempfile

from audit_supply_checkpoint import validate_plan
from check_chip_supply_connectivity import GDS_SHA256, sha, validate_native
from extract_supply_checkpoint import METALS, VIAS
from plan_chip_supply_probes import SUPPLIES
from probe_supply_components import probe_window
from supply_checkpoint import load
from supply_checkpoint_staged import prepare

PLAN_SHA256 = "340047aaf8cdc30d00d4af3489759187d1a78366846f2030238d62d32136a109"
LAYERS = ["metal" + str(v) for v in METALS] + ["via" + str(v) for v in VIAS]
METHODS = ["cloud_supply_tiles.py", "audit_supply_checkpoint.py",
           "check_chip_supply_connectivity.py", "extract_supply_checkpoint.py",
           "plan_chip_supply_probes.py", "probe_supply_components.py",
           "supply_checkpoint.py", "supply_checkpoint_staged.py"]


def digest_object(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write_new(path, value):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, prefix=".supply-", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Exclusive atomic publication; neither a partial JSON nor replacement
        # of an accepted checkpoint is exposed at the final path.
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def method_pins():
    return {n: sha(Path(__file__).with_name(n)) for n in METHODS}


def overlap(a, b):
    c = [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]
    return c if c[0] < c[2] and c[1] < c[3] else None


def tile_grid(bounds, columns, rows, halo=2):
    if (len(bounds) != 4 or any(type(x) is not int for x in bounds)
            or not 1 <= columns <= 16 or not 1 <= rows <= 16 or halo != 2):
        raise ValueError("Integer bounds, 1..16 grid and exact two-DBU halo required")
    x0, y0, x1, y1 = bounds
    if x1-x0 < columns*2*halo or y1-y0 < rows*2*halo:
        raise ValueError("Tiles must be wider than the overlap halo")
    xs = [x0+(x1-x0)*i//columns for i in range(columns+1)]
    ys = [y0+(y1-y0)*i//rows for i in range(rows+1)]
    tiles = []
    for y in range(rows):
        for x in range(columns):
            core = [xs[x], ys[y], xs[x+1], ys[y+1]]
            tiles.append(dict(id=len(tiles), core=core,
                              box=[max(x0, core[0]-halo), max(y0, core[1]-halo),
                                   min(x1, core[2]+halo), min(y1, core[3]+halo)]))
    seams = []
    for a in tiles:
        for b in tiles[a["id"]+1:]:
            shared = overlap(a["box"], b["box"])
            if shared:
                seams.append(dict(id=len(seams), tiles=[a["id"], b["id"]], box=shared))
    return dict(bounds=bounds, columns=columns, rows=rows, halo_dbu=halo,
                tiles=tiles, seams=seams)


def validate_grid(grid):
    expected = tile_grid(grid["bounds"], grid["columns"], grid["rows"], grid["halo_dbu"])
    if grid != expected:
        raise ValueError("Tile/overlap coverage differs from complete deterministic grid")


def queries(grid, tile_id, plan):
    tile = grid["tiles"][tile_id]
    answer = []
    for index, window in enumerate(plan["windows"]):
        box = overlap(window["box_nm"], tile["core"])
        if box:
            answer.append(dict(kind="window", index=index,
                               layer="metal"+str(window["gds_layer"]), box_dbu=box))
    for seam in grid["seams"]:
        if tile_id in seam["tiles"]:
            for layer in LAYERS:
                answer.append(dict(kind="seam", index=seam["id"],
                                   layer=layer, box_dbu=seam["box"]))
    if not answer:
        raise ValueError("Every tile must contain a query or overlap")
    return answer


def validate_bundle(directory, expected):
    path = Path(directory)/"bundle.json"
    if sha(path) != expected:
        raise ValueError("Bundle manifest hash mismatch")
    manifest = json.loads(path.read_text())
    if (manifest["status"] != "PREPARED_COMPLETE_PHYSICAL_TILES_ONLY"
            or manifest["methods"] != method_pins() or manifest["dbu"] != .001):
        raise ValueError("Unverified bundle or changed method")
    validate_grid(manifest["grid"])
    plan_path = Path(directory)/"plan.json"
    if sha(plan_path) != manifest["plan_sha256"]:
        raise ValueError("Window plan hash mismatch")
    plan = json.loads(plan_path.read_text())
    validate_plan(plan, dict(input_sha256={"chip.gds": manifest["source_gds_sha256"]},
                             dbu=.001, floating_subcircuits_retained=True))
    if manifest["production"] and (manifest["source_gds_sha256"] != GDS_SHA256
                                  or sha(plan_path) != PLAN_SHA256
                                  or plan["io_instances"] != 314
                                  or plan["port_windows"] != 10526):
        raise ValueError("Wrong production GDS or complete IO inventory")
    for window in plan["windows"]:
        if overlap(window["box_nm"], manifest["grid"]["bounds"]) != window["box_nm"]:
            raise ValueError("Required IO window lies outside tile coverage")
    if set(manifest["tile_files"]) != {str(t["id"]) for t in manifest["grid"]["tiles"]}:
        raise ValueError("Incomplete tile file inventory")
    return manifest, plan


def clipped_layers(db, layout, top, box):
    """Flatten only shapes overlapping this tile; intersect before native cuts.

    Region(RecursiveShapeIterator) applies actual hierarchy transforms. Set
    algebra distributes over the common clip rectangle; there is no name join.
    """
    clip = db.Region(db.Box(*box))
    cache = {}

    def raw(number, datatype=0):
        key = number, datatype
        if key not in cache:
            index = layout.find_layer(number, datatype)
            source = (db.Region() if index is None else
                      db.Region(top.begin_shapes_rec_overlapping(index, db.Box(*box))))
            # Axis-aligned tile lines intersect integer Manhattan/45-degree
            # edges on integer DBU coordinates. Arbitrary slopes may need
            # rational coordinates: fail closed rather than round an open
            # gap into a connection at the outer edge of an overlap tile.
            for polygon in source.each():
                if polygon.is_box():
                    continue
                for edge in polygon.each_edge():
                    dx, dy = abs(edge.p2.x-edge.p1.x), abs(edge.p2.y-edge.p1.y)
                    if dx and dy and dx != dy:
                        raise ValueError("Non-Manhattan/non-45 source edge requires exact rational clipping")
            cache[key] = source & clip
        return cache[key]

    layers = {}
    for number in METALS:
        region = (raw(number)+raw(number, 22))-raw(number, 24)-raw(number, 29)
        if number in (126, 134):
            region -= raw(27)
        layers["metal"+str(number)] = region.merged()
    for number in VIAS:
        layers["via"+str(number)] = (raw(number)-raw(36) if number == 125 else raw(number)).merged()
    return layers


def geometry_key(region):
    # Normalized merged polygon strings include every hull/hole vertex. Sorting
    # removes iterator order; native replay below also checks actual witnesses.
    return digest_object(sorted(str(p) for p in region.merged().each()))


def make_bundle(db, gds, plan_path, output, columns=8, rows=8, references=None, production=True):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    plan = json.loads(Path(plan_path).read_text())
    original_methods = method_pins()
    source_pins = {str(Path(p).resolve()): sha(p) for p in [gds, plan_path]}
    if production and (sha(gds) != GDS_SHA256 or sha(plan_path) != PLAN_SHA256):
        raise ValueError("Unexpected production GDS or IO window plan")
    if production:
        if references is None:
            raise ValueError("Native reference derivations are mandatory")
        source_pins.update({str(p.resolve()): sha(p) for p in validate_native(Path(references))})
    validate_plan(plan, dict(input_sha256=source_pins, dbu=.001, floating_subcircuits_retained=True))
    if production and (plan["io_instances"] != 314 or plan["port_windows"] != 10526):
        raise ValueError("Incomplete production IO plan")
    layout = db.Layout()
    options = db.LoadLayoutOptions()
    mapping = db.LayerMap()
    pairs = [(n, dt) for n in METALS for dt in (0, 22, 24, 29)] + [(n, 0) for n in VIAS+[27, 36]]
    for i, (number, datatype) in enumerate(pairs):
        mapping.map(f"{number}/{datatype}", i)
    options.set_layer_map(mapping, False)
    layout.read(str(gds), options)
    top_name = "nssoc_chip" if production else "TOP"
    top = layout.cell(top_name)
    if layout.dbu != .001 or top is None:
        raise ValueError("Expected nanometre units and exact top")
    bounds = top.bbox()
    grid = tile_grid([bounds.left, bounds.bottom, bounds.right, bounds.top], columns, rows)
    for w in plan["windows"]:
        if overlap(w["box_nm"], grid["bounds"]) != w["box_nm"]:
            raise ValueError("Window extends beyond complete geometry coverage")
    tile_files = {}
    for tile in grid["tiles"]:
        regions = clipped_layers(db, layout, top, tile["box"])
        tile_layout = db.Layout()
        tile_layout.dbu = .001
        cell = tile_layout.create_cell("TOP")
        for index, name in enumerate(LAYERS):
            cell.shapes(tile_layout.layer(index+1, 0)).insert(regions[name])
        path = output/f"tile-{tile['id']:03d}.gds"
        tile_layout.write(str(path))
        # Verify the serialized tile geometry before publishing its hash.
        restored = db.Layout()
        restored.read(str(path))
        if restored.dbu != .001 or restored.cell("TOP") is None:
            raise ValueError("Tile serialization changed units/top")
        for index, name in enumerate(LAYERS):
            actual = db.Region(restored.cell("TOP").shapes(restored.layer(index+1, 0)))
            if not (actual ^ regions[name]).is_empty():
                raise ValueError("Serialized tile geometry differs")
        tile_files[str(tile["id"])] = dict(file=path.name, bytes=path.stat().st_size,
                                           sha256=sha(path),
                                           geometry={n: geometry_key(r) for n, r in regions.items()})
        write_new(output/f"tile-{tile['id']:03d}.prepared.json", tile_files[str(tile["id"])])
        print("PREPARED_TILE", tile["id"], path.stat().st_size, flush=True)
    if any(sha(p) != h for p, h in source_pins.items()):
        raise ValueError("Source changed during preparation")
    if method_pins() != original_methods:
        raise ValueError("Preparation method changed while running")
    (output/"plan.json").write_bytes(Path(plan_path).read_bytes())
    manifest = dict(status="PREPARED_COMPLETE_PHYSICAL_TILES_ONLY", production=production,
                    source_gds_sha256=sha(gds), plan_sha256=sha(plan_path),
                    source_sha256=source_pins, methods=original_methods, dbu=.001,
                    klayout_version=db.__version__, grid=grid, tile_files=tile_files,
                    derivation="All native drawing+fill minus slit/resistor/inductor cuts; TopVia1 minus MIM; no labels or virtual joins",
                    full_chip_lvs_accepted=False, manufacturing_approval=False)
    write_new(output/"bundle.json", manifest)
    return manifest


def tile_extractor(db, path):
    layout = db.Layout()
    layout.read(str(path))
    if layout.dbu != .001 or layout.cell("TOP") is None:
        raise ValueError("Invalid native tile geometry")
    native = db.LayoutToNetlist("TOP", .001)
    native.threads = 1
    native.include_floating_subcircuits = True
    regions = {}
    for index, name in enumerate(LAYERS):
        region = db.Region(layout.cell("TOP").shapes(layout.layer(index+1, 0))).merged()
        native.register(region, name)
        native.connect(region)
        regions[name] = region
    for i, v in enumerate(VIAS):
        native.connect(regions["metal"+str(METALS[i])], regions["via"+str(v)])
        native.connect(regions["via"+str(v)], regions["metal"+str(METALS[i+1])])
    native.extract_netlist()
    return native, regions


def extract_tile(db, directory, bundle_sha256, tile_id, output):
    manifest, plan = validate_bundle(directory, bundle_sha256)
    if manifest["klayout_version"] != db.__version__:
        raise ValueError("Native tool version changed")
    if not 0 <= tile_id < len(manifest["grid"]["tiles"]):
        raise ValueError("Unknown tile ID")
    entry = manifest["tile_files"][str(tile_id)]
    expected_file = f"tile-{tile_id:03d}.gds"
    if entry["file"] != expected_file:
        raise ValueError("Unexpected tile path")
    path = Path(directory)/entry["file"]
    if sha(path) != entry["sha256"] or path.stat().st_size != entry["bytes"]:
        raise ValueError("Tile geometry hash/size mismatch")
    native, regions = tile_extractor(db, path)
    if {n: geometry_key(r) for n, r in regions.items()} != entry["geometry"]:
        raise ValueError("Tile native geometry differs from preparation")
    specs = queries(manifest["grid"], tile_id, plan)
    pins = {str(p.resolve()): sha(p) for p in [path, Path(directory)/"bundle.json", Path(directory)/"plan.json"]}
    pins.update({str(Path(__file__).with_name(n).resolve()): h for n, h in method_pins().items()})
    prepare(db, native, output, specs, "TOP", pins, checkpoint_layers=LAYERS)


def measure_tile(db, directory, bundle_sha256, tile_id, checkpoint, manifest_sha256, output):
    manifest, plan = validate_bundle(directory, bundle_sha256)
    native, checkpoint_manifest = load(db, checkpoint, manifest_sha256)
    expected = queries(manifest["grid"], tile_id, plan)
    if checkpoint_manifest["probes"] != expected or checkpoint_manifest["top"] != "TOP":
        raise ValueError("Checkpoint query coverage differs")
    bound = checkpoint_manifest["input_sha256"]
    if (bound.get(str((Path(directory)/"bundle.json").resolve())) != bundle_sha256
            or bound.get(str((Path(directory)/f"tile-{tile_id:03d}.gds").resolve()))
            != manifest["tile_files"][str(tile_id)]["sha256"]):
        raise ValueError("Checkpoint belongs to another tile or bundle")
    measurements = []
    for spec in expected:
        region = native.layer_by_name(spec["layer"])
        clipped = (region & db.Region(db.Box(*spec["box_dbu"]))).merged()
        result = probe_window(db, native, region, db.Box(*spec["box_dbu"]), .001, "TOP")
        if any(s["circuit"] != "TOP" or type(s["cluster"]) is not int for s in result["samples"]):
            raise ValueError("Tile contains unresolved physical witness")
        samples = sorted(result["samples"], key=lambda s: (s["point_um"], s["cluster"]))
        measurements.append(dict(query=spec, geometry_sha256=geometry_key(clipped), samples=samples))
    result = dict(status="VERIFIED_TILE_MEASUREMENTS_ONLY", tile_id=tile_id,
                  bundle_sha256=bundle_sha256, plan_sha256=manifest["plan_sha256"],
                  checkpoint_manifest_sha256=manifest_sha256,
                  checkpoint_database_sha256=checkpoint_manifest["database_sha256"],
                  methods=method_pins(), measurements=measurements,
                  full_chip_lvs_accepted=False, manufacturing_approval=False)
    if sha(Path(directory)/"bundle.json") != bundle_sha256:
        raise ValueError("Bundle changed during checkpoint measurement")
    if sha(Path(checkpoint)/"manifest.json") != manifest_sha256:
        raise ValueError("Checkpoint manifest changed during measurement")
    validate_bundle(directory, bundle_sha256)
    write_new(output, result)
    return result


def validate_result_chain(directory, result, bundle, bundle_sha256):
    """Tie measurements to the actual uploaded staged-checkpoint bytes.

    Native extraction is not repeated here. Producer/reloader equivalence is
    verified against the retained canonical witness snapshot and input pins.
    """
    checkpoint = Path(directory)/"checkpoint"
    path = checkpoint/"manifest.json"
    if sha(path) != result["checkpoint_manifest_sha256"]:
        raise ValueError("Measurement/checkpoint manifest hash mismatch")
    manifest = json.loads(path.read_text())
    prepared = checkpoint/"prepared.json"
    if sha(prepared) != manifest["prepared_sha256"]:
        raise ValueError("Prepared checkpoint hash mismatch")
    earlier = json.loads(prepared.read_text())
    promoted = {**earlier, "status": "PASS_CHECKPOINT_ROUNDTRIP_ONLY",
                "prepared_sha256": manifest["prepared_sha256"], "verifier": manifest["verifier"]}
    if promoted != manifest or earlier["status"] != "PREPARED_NOT_VERIFIED":
        raise ValueError("Checkpoint promotion changed prepared content")
    if (manifest["status"] != "PASS_CHECKPOINT_ROUNDTRIP_ONLY"
            or manifest["method_sha256"] != bundle["methods"]["supply_checkpoint.py"]
            or manifest["staged_method_sha256"] != bundle["methods"]["supply_checkpoint_staged.py"]
            or manifest["probe_method_sha256"] != bundle["methods"]["probe_supply_components.py"]
            or manifest["klayout_version"] != bundle["klayout_version"]
            or manifest["layers"] != LAYERS or manifest["top"] != "TOP"
            or manifest["dbu"] != .001 or not manifest["floating_subcircuits_retained"]):
        raise ValueError("Incomplete native checkpoint contract")
    if manifest["producer"] == manifest["verifier"]:
        raise ValueError("Checkpoint producer did not exit for separate replay")
    database = checkpoint/"connectivity.l2n.gz"
    if (manifest["database"] != database.name
            or database.stat().st_size != manifest["database_bytes"]
            or sha(database) != manifest["database_sha256"]
            or manifest["database_sha256"] != result["checkpoint_database_sha256"]):
        raise ValueError("Retained checkpoint database hash/size mismatch")
    source_pins = manifest["input_sha256"]
    required = {"bundle.json": bundle_sha256, "plan.json": bundle["plan_sha256"],
                f"tile-{result['tile_id']:03d}.gds": bundle["tile_files"][str(result["tile_id"])]["sha256"],
                **bundle["methods"]}
    for name, digest in required.items():
        if [h for p, h in source_pins.items() if Path(p).name == name] != [digest]:
            raise ValueError("Checkpoint source provenance mismatch: "+name)
    if manifest["probes"] != [r["query"] for r in result["measurements"]]:
        raise ValueError("Checkpoint measurement coverage differs")
    classes = {}
    actual = []
    for row in result["measurements"]:
        samples = []
        for s in sorted(row["samples"], key=lambda sample: sample["point_um"]):
            key = s["circuit"], s["cluster"]
            classes.setdefault(key, len(classes))
            samples.append(dict(point_um=s["point_um"], circuit=s["circuit"],
                                equivalence_class=classes[key]))
        actual.append(dict(probe=row["query"], samples=samples))
    expected = [{"probe": r["probe"], "samples": r["samples"]} for r in manifest["probe_snapshot"]]
    if actual != expected:
        raise ValueError("Measurement witnesses differ from replayed native checkpoint")


def combine(manifest, bundle_sha256, plan, results):
    """Union only proven identical seam witnesses; fail closed on missing data."""
    validate_grid(manifest["grid"])
    count = len(manifest["grid"]["tiles"])
    if len(results) != count or {r["tile_id"] for r in results} != set(range(count)):
        raise ValueError("Missing or duplicate tile results")
    records = {}
    parents = {}

    def find(key):
        parents.setdefault(key, key)
        while key != parents[key]:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parents[max(a, b)] = min(a, b)

    for result in results:
        tile = result["tile_id"]
        if (result["status"] != "VERIFIED_TILE_MEASUREMENTS_ONLY"
                or result["bundle_sha256"] != bundle_sha256
                or result["plan_sha256"] != manifest["plan_sha256"]
                or result["methods"] != manifest["methods"]):
            raise ValueError("Unverified or unrelated tile result")
        expected = queries(manifest["grid"], tile, plan)
        measurements = result["measurements"]
        if [r["query"] for r in measurements] != expected:
            raise ValueError("Tile query/window/seam coverage changed")
        for row in measurements:
            q = row["query"]
            key = tile, q["kind"], q["index"], q["layer"]
            if key in records:
                raise ValueError("Duplicate measurement")
            records[key] = row
            for s in row["samples"]:
                if s["circuit"] != "TOP" or type(s["cluster"]) is not int:
                    raise ValueError("Unresolved native witness")
                find((tile, s["cluster"]))
    seam_witnesses = 0
    for seam in manifest["grid"]["seams"]:
        a, b = seam["tiles"]
        for layer in LAYERS:
            left = records[a, "seam", seam["id"], layer]
            right = records[b, "seam", seam["id"], layer]
            if (left["geometry_sha256"] != right["geometry_sha256"]
                    or [s["point_um"] for s in left["samples"]]
                    != [s["point_um"] for s in right["samples"]]):
                raise ValueError("Adjacent tiles disagree on actual overlap conductor/witnesses")
            for x, y in zip(left["samples"], right["samples"]):
                union((a, x["cluster"]), (b, y["cluster"]))
                seam_witnesses += 1
    windows = []
    rails = {pin: set() for pin in SUPPLIES}
    bad = []
    for index, window in enumerate(plan["windows"]):
        ids = set()
        parts = 0
        for tile in manifest["grid"]["tiles"]:
            key = tile["id"], "window", index, "metal"+str(window["gds_layer"])
            if key in records:
                parts += 1
                ids.update(find((tile["id"], s["cluster"])) for s in records[key]["samples"])
        if not parts:
            raise ValueError("Window not assigned to any tile")
        if len(ids) != 1:
            bad.append(index)
        rails[window["pin"]].update(ids)
        windows.append(dict(index=index, pieces=parts, physical_components=sorted(ids)))
    errors = []
    for pin, identities in rails.items():
        if len(identities) != 1:
            errors.append(f"{pin} has {len(identities)} distinct physical components")
    if len(set().union(*rails.values())) != sum(len(v) for v in rails.values()):
        errors.append("Different supply rails share a physical component")
    if bad:
        errors.append(f"{len(bad)} required windows contain zero/multiple components")
    return dict(status="FAIL_OR_UNRESOLVED_TILED_IO_SUPPLY_WINDOWS" if errors else
                "PASS_ALL_DECLARED_IO_SUPPLY_WINDOWS_TILED_ONLY", errors=errors,
                io_instances=plan["io_instances"], checked_windows=len(windows),
                tiles=count, seams=len(manifest["grid"]["seams"]), seam_witnesses=seam_witnesses,
                bad_window_indices=bad, windows=windows,
                rails={k: sorted(v) for k, v in rails.items()},
                scope="All source geometry tiled; native overlapping conductor witnesses only; no label/rail-name joins. Complete IO-window metal connectivity, not transistor LVS, RC or timing.",
                full_chip_lvs_accepted=False, manufacturing_approval=False)


def memory_guard(gib):
    text = Path("/proc/meminfo").read_text()
    available = int(dict(line.split(":", 1) for line in text.splitlines())["MemAvailable"].split()[0])*1024
    cap = gib*1024**3
    if available < cap+1024**3:
        raise ValueError("Requested address-space cap plus 1 GiB available reserve required")
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    return dict(available_memory_bytes=available, address_space_limit_bytes=cap)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "extract", "measure", "combine"])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--gds", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--references", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--bundle-sha256")
    parser.add_argument("--tile", type=int)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--results", type=Path)
    parser.add_argument("--memory-gib", type=int, choices=range(2, 13), default=4)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be fresh")
    resources = memory_guard(args.memory_gib)
    print(json.dumps(dict(stage=args.mode, recorded=datetime.now().astimezone().isoformat(),
                          resources=resources, methods=method_pins())), flush=True)
    import klayout.db as db

    if args.mode == "prepare":
        if not all((args.gds, args.plan, args.references)):
            parser.error("prepare requires GDS, plan and native references")
        make_bundle(db, args.gds, args.plan, args.output, references=args.references)
    elif args.mode in ("extract", "measure"):
        if not args.bundle or not args.bundle_sha256 or args.tile is None:
            parser.error("tile stages require pinned bundle and tile ID")
        if args.mode == "extract":
            extract_tile(db, args.bundle, args.bundle_sha256, args.tile, args.output)
        else:
            if not args.checkpoint or not args.manifest_sha256:
                parser.error("measure requires verified checkpoint manifest")
            measure_tile(db, args.bundle, args.bundle_sha256, args.tile, args.checkpoint,
                         args.manifest_sha256, args.output)
    else:
        if not args.bundle or not args.bundle_sha256 or not args.results:
            parser.error("combine requires pinned bundle and all tile results")
        manifest, plan = validate_bundle(args.bundle, args.bundle_sha256)
        paths = sorted(args.results.glob("*/measurement.json"))
        results = [json.loads(p.read_text()) for p in paths]
        for path, result in zip(paths, results):
            validate_result_chain(path.parent, result, manifest, args.bundle_sha256)
        result = combine(manifest, args.bundle_sha256, plan, results)
        validate_bundle(args.bundle, args.bundle_sha256)
        result.update(bundle_sha256=args.bundle_sha256,
                      source_gds_sha256=manifest["source_gds_sha256"],
                      plan_sha256=manifest["plan_sha256"], production=manifest["production"],
                      result_sha256={str(p): sha(p) for p in paths}, resources=resources,
                      methods=method_pins(), recorded=datetime.now().astimezone().isoformat())
        write_new(args.output, result)
        print(result["status"], flush=True)
        return 1 if result["errors"] else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
