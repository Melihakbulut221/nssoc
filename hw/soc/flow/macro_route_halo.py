# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prepare a routing keep-out experiment without changing macro LEFs or cells.

Run with OpenROAD's Python interpreter. Output is a new ODB, not a routed
design. Pin corridors preserve geometric access, not a guarantee of routing.
"""
import argparse
import hashlib
import json
from pathlib import Path


def area(rect):
    x0, y0, x1, y1 = rect
    return (x1 - x0) * (y1 - y0)


def intersection(a, b):
    rect = (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))
    return rect if rect[0] < rect[2] and rect[1] < rect[3] else None


def subtract(rect, cut):
    """Disjoint rectangular pieces of rect minus cut, in integer DB units."""
    overlap = intersection(rect, cut)
    if overlap is None:
        return [rect]
    x0, y0, x1, y1 = rect
    a, b, c, d = overlap
    pieces = [(x0, y0, a, y1), (c, y0, x1, y1), (a, y0, c, b), (a, d, c, y1)]
    return [p for p in pieces if p[0] < p[2] and p[1] < p[3]]


def halo_rectangles(bounds, width, pins, pin_clearance):
    if width <= 0 or pin_clearance < 0 or bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
        raise ValueError("Invalid halo dimensions")
    x0, y0, x1, y1 = bounds
    outer = (x0 - width, y0 - width, x1 + width, y1 + width)
    pieces = subtract(outer, bounds)
    # A corridor crosses the entire strip only for pins whose geometry touches
    # that macro edge. Interior pins remain accessible through other layers;
    # they do not need a hole in the outside ring.
    corridors = []
    for a, b, c, d in pins:
        if a <= x0:
            corridors.append((x0 - width, b - pin_clearance, x0, d + pin_clearance))
        if c >= x1:
            corridors.append((x1, b - pin_clearance, x1 + width, d + pin_clearance))
        if b <= y0:
            corridors.append((a - pin_clearance, y0 - width, c + pin_clearance, y0))
        if d >= y1:
            corridors.append((a - pin_clearance, y1, c + pin_clearance, y1 + width))
    for corridor in corridors:
        pieces = [part for piece in pieces for part in subtract(piece, corridor)]
    return pieces, corridors


def prepare(source, destination, report, width_um=0.6, pin_clearance_um=0.45):
    import odb
    if destination.exists() or report.exists() or source.resolve() == destination.resolve():
        raise ValueError("Use new output paths; input and prior experiments are retained")
    db = odb.dbDatabase.create()
    odb.read_db(db, str(source))
    block = db.getChip().getBlock()
    units = block.getDbUnitsPerMicron()
    width = round(width_um * units)
    clearance = round(pin_clearance_um * units)
    if width <= 0 or clearance < 0:
        raise ValueError("Invalid halo dimensions")
    layers = {name: db.getTech().findLayer(name) for name in ("Metal2", "Metal3", "Metal4")}
    if not all(layers.values()):
        raise ValueError("Expected IHP Metal2/Metal3/Metal4 layers")
    coord = lambda box: (box.xMin(), box.yMin(), box.xMax(), box.yMax())
    die = coord(block.getDieArea())
    macros = []
    itr = odb.dbITermShapeItr()
    shape = odb.dbShape()
    for inst in block.getInsts():
        if inst.getMaster().getType() != "BLOCK":
            continue
        bounds = coord(inst.getBBox())
        pins = {name: [] for name in layers}
        for pin in inst.getITerms():
            if str(pin.getSigType()) in ("POWER", "GROUND"):
                continue
            itr.begin(pin)
            while itr.next(shape):
                layer = shape.getTechLayer().getName()
                if layer in pins:
                    pins[layer].append(coord(shape))
        for layer in layers:
            pieces, corridors = halo_rectangles(bounds, width, pins[layer], clearance)
            if any(intersection(piece, die) != piece for piece in pieces):
                raise ValueError(f"Halo extends beyond die at {inst.getName()}")
            macros.append({"instance": inst.getName(), "orientation": str(inst.getOrient()),
                           "bounds_dbu": bounds, "layer": layer, "rectangles_dbu": pieces,
                           "pin_corridors_dbu": corridors, "reserved_area_um2": sum(map(area, pieces)) / units**2})
    if not macros:
        raise ValueError("No macros found")
    # Validate all geometry before modifying the in-memory database.
    before_count = len(block.getObstructions())
    for item in macros:
        for rect in item["rectangles_dbu"]:
            obstruction = odb.dbObstruction_create(block, layers[item["layer"]], *rect)
            if not obstruction:
                raise RuntimeError("OpenDB refused routing obstruction")
    created = len(block.getObstructions()) - before_count
    if created != sum(len(item["rectangles_dbu"]) for item in macros):
        raise RuntimeError("Routing obstruction count mismatch")
    odb.write_db(db, str(destination))
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    result = {"status": "PREPARED_NOT_ROUTED", "scope": "Routing obstructions outside macro footprints with same-layer pin corridors; no LEF, cell, connection, power route, clock or constraint changes. Needs fresh GRT, detailed routing and unchanged DRC decks.",
              "source": str(source), "source_sha256": digest(source),
              "destination": str(destination), "destination_sha256": digest(destination),
              "db_units_per_micron": units, "width_um": width / units,
              "pin_clearance_um": clearance / units, "added_obstructions": created,
              "reserved_area_per_layer_um2": {name: sum(m["reserved_area_um2"] for m in macros if m["layer"] == name) for name in layers},
              "macros": macros}
    report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "macros"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--width-um", type=float, default=0.6)
    parser.add_argument("--pin-clearance-um", type=float, default=0.45)
    args = parser.parse_args()
    prepare(args.source, args.destination, args.report, args.width_um, args.pin_clearance_um)
