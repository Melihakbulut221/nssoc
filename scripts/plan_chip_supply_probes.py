#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Inventory every native IO supply port before a whole-ring connectivity audit.

This produces search windows, not proof of physical metal or connectivity.
An extractor must intersect each window with native conductor geometry and
resolve every resulting component. A window centre alone is not sufficient.
"""

import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import re
import resource

from check_chip_supply_connectivity import GDS_SHA256, LEF_SHA256, sha

LAYERS = {
    "Metal1": 8,
    "Metal2": 10,
    "Metal3": 30,
    "Metal4": 50,
    "Metal5": 67,
    "TopMetal1": 126,
    "TopMetal2": 134,
}
SUPPLIES = {"vdd": "POWER", "vss": "GROUND", "iovdd": "POWER", "iovss": "GROUND"}


def rectangle(text):
    values = [Decimal(v) * 1000 for v in text.split()]
    if len(values) != 4 or any(
        not v.is_finite() or v != v.to_integral_value() for v in values
    ):
        raise ValueError("Port coordinates must be four finite integer nanometres")
    box = [int(v) for v in values]
    if box[0] >= box[2] or box[1] >= box[3]:
        raise ValueError("Empty or inverted port rectangle")
    return box


def parse_lef(source):
    """Strict subset for the pinned IO LEF; never silently drop port geometry."""
    macros = {}
    for master, body in re.findall(
        r"^MACRO (\S+)\n(.*?)^END \1\s*$", source, re.M | re.S
    ):
        if master in macros:
            raise ValueError("Duplicate LEF macro")
        pins = {}
        blocks = re.findall(r"^  PIN (\S+)\n(.*?)^  END \1\s*$", body, re.M | re.S)
        if len(blocks) != len(re.findall(r"^  PIN ", body, re.M)):
            raise ValueError("Incomplete LEF pin coverage")
        for pin, block in blocks:
            uses = re.findall(r"\bUSE (\w+)\s*;", block)
            if pin not in SUPPLIES and not set(uses) & {"POWER", "GROUND"}:
                continue
            if pin in pins or pin not in SUPPLIES or uses != [SUPPLIES[pin]]:
                raise ValueError("Duplicate, unknown or incorrectly typed supply pin")
            shapes = []
            in_port = False
            layer = None
            for line in block.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line == "PORT":
                    if in_port:
                        raise ValueError("Nested PORT")
                    in_port, layer = True, None
                elif line == "END":
                    if not in_port:
                        raise ValueError("Unexpected PORT end")
                    in_port, layer = False, None
                elif in_port:
                    match = re.fullmatch(r"LAYER (\w+)\s*;", line)
                    rect = re.fullmatch(r"RECT\s+(.+?)\s*;", line)
                    if match and match[1] in LAYERS:
                        layer = match[1]
                    elif rect and layer:
                        shapes.append(dict(layer=layer, box_nm=rectangle(rect[1])))
                    else:
                        raise ValueError("Unsupported supply port geometry: " + line)
                elif re.match(r"(?:RECT|POLYGON|PATH|VIA|LAYER)\b", line):
                    raise ValueError("Geometry outside PORT")
            if in_port or not shapes:
                raise ValueError("Unterminated or empty supply PORT")
            pins[pin] = shapes
        macros[master] = pins
    if not macros or len(macros) != len(re.findall(r"^MACRO ", source, re.M)):
        raise ValueError("Incomplete LEF macro coverage")
    return macros


def transform_box(box, rotation, x, y):
    if rotation % 90 != 0:
        raise ValueError("Only orthogonal, unmirrored placements supported")
    rotation %= 360
    points = []
    for a, b in [
        (box[0], box[1]),
        (box[0], box[3]),
        (box[2], box[1]),
        (box[2], box[3]),
    ]:
        if rotation == 90:
            a, b = -b, a
        elif rotation == 180:
            a, b = -a, -b
        elif rotation == 270:
            a, b = b, -a
        points.append((a + x, b + y))
    return [
        min(a for a, b in points),
        min(b for a, b in points),
        max(a for a, b in points),
        max(b for a, b in points),
    ]


def rotation_degrees(code):
    """placements.json uses KLayout Trans quarter-turn codes, not degrees."""
    if type(code) is not int or code not in range(4):
        raise ValueError("Placement rotation must be a quarter-turn code 0..3")
    return 90 * code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["gds", "lef", "placements", "output"]:
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new")
    pins = {
        str(p.resolve()): sha(p)
        for p in [args.gds, args.lef, args.placements, Path(__file__)]
    }
    assert sha(args.gds) == GDS_SHA256 and sha(args.lef) == LEF_SHA256
    ports = parse_lef(args.lef.read_text())
    placements = json.loads(args.placements.read_text())
    selected = [p for p in placements if p["master"] in ports]
    assert len(selected) == 314 and len({p["instance"] for p in selected}) == 314
    assert all(ports[p["master"]] for p in selected)
    resource.setrlimit(resource.RLIMIT_AS, (1024**3,) * 2)
    import klayout.db as db

    layout = db.Layout()
    options = db.LoadLayoutOptions()
    # Read the complete instance hierarchy without allocating millions of polygons.
    options.set_layer_map(db.LayerMap(), False)
    layout.read(str(args.gds), options)
    assert layout.dbu == 0.001
    top = layout.cell("nssoc_chip")
    assert top is not None
    actual = Counter()
    for inst in top.each_inst():
        if inst.cell.name not in ports:
            continue
        for trans in inst.cell_inst.each_cplx_trans():
            actual[(inst.cell.name, str(trans))] += 1
    expected = Counter()
    windows = []
    for p in selected:
        angle = rotation_degrees(p["rotation"])
        trans = db.ICplxTrans(1, angle, False, p["x_nm"], p["y_nm"])
        expected[(p["master"], str(trans))] += 1
        for pin, shapes in ports[p["master"]].items():
            for shape in shapes:
                box = transform_box(shape["box_nm"], angle, p["x_nm"], p["y_nm"])
                native = db.Box(*shape["box_nm"]).transformed(trans)
                assert box == [native.left, native.bottom, native.right, native.top]
                windows.append(
                    dict(
                        instance=p["instance"],
                        master=p["master"],
                        pin=pin,
                        layer=shape["layer"],
                        gds_layer=LAYERS[shape["layer"]],
                        box_nm=box,
                        local_box_nm=shape["box_nm"],
                    )
                )
    assert actual == expected, "IO placement multiplicity or transform mismatch"
    assert all(sha(Path(p)) == h for p, h in pins.items())
    result = dict(
        status="PASS_IO_PORT_WINDOW_COVERAGE_ONLY",
        input_sha256=pins,
        io_instances=len(selected),
        io_masters=dict(Counter(p["master"] for p in selected)),
        port_windows=len(windows),
        windows_by_rail=dict(Counter(w["pin"] for w in windows)),
        windows_by_layer=dict(Counter(w["layer"] for w in windows)),
        windows=windows,
        scope=__doc__,
        physical_conductor_coverage_accepted=False,
        supply_connectivity_accepted=False,
        full_chip_lvs_accepted=False,
        manufacturing_approval=False,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as f:
        f.write(json.dumps(result, indent=2) + "\n")
    print(result["status"], len(selected), len(windows), result["windows_by_rail"])


if __name__ == "__main__":
    main()
